import pytest

from arms import HORIZONTAL as H, VERTICAL as V
from config import LIFT_DISTANCE, RELEASE_DISTANCES, mm_to_steps, pickup_mm
from cradle_sim import push_off_switch, run
from motion import HomingError

COMBOS = [(left, right) for left in range(6) for right in range(6) if 0 < left + right <= 5]


def finish(arms, sim_state):
    run(sim_state, arms.tick, lambda: not arms.busy)


def all_moves(boards):
    return [move for board in boards for move in board.moves]


def start_away_from_home(boards, sim_state):
    for board in boards:
        for stepper in (H, V):
            board.moveToAbsolutePositionInSteps(stepper, 3000, False)
    sim_state.run_until_idle()


def homed(board, stepper):
    return board.getCurrentPositionInSteps(stepper) == 0 and board.getStepperStatus(stepper).at_home


def timed_scoop(arms, sim_state, num_left, num_right):
    start = sim_state.clock.now()
    arms.scoop(num_left, num_right)
    finish(arms, sim_state)
    return sim_state.clock.now() - start


@pytest.mark.parametrize("num_left,num_right", COMBOS)
def test_scoop_never_moves_both_axes_of_an_arm_at_once(arms, boards, sim_state, num_left, num_right):
    arms.scoop(num_left, num_right)
    finish(arms, sim_state)
    overlapping = [move for move in all_moves(boards) if move.other_axis_moving]
    assert not overlapping, overlapping[0]


@pytest.mark.parametrize("end_at_home", [True, False])
def test_stop_balls_never_moves_both_axes_of_an_arm_at_once(arms, boards, sim_state, end_at_home):
    arms.stop_balls(end_at_home)
    finish(arms, sim_state)
    overlapping = [move for move in all_moves(boards) if move.other_axis_moving]
    assert not overlapping, overlapping[0]


@pytest.mark.parametrize("num_left,num_right", COMBOS)
def test_scoop_drops_balls_at_the_trimmed_release_point(arms, boards, sim_state, num_left, num_right):
    arms.scoop(num_left, num_right)
    finish(arms, sim_state)
    tuning = arms.tuning
    for board, count, offset in zip(boards, (num_right, num_left), (tuning.offset_right, tuning.offset_left)):
        if count:
            drop = next(move for move in board.moves if move.stepper == V and move.start > 0 and move.target == 0)
            assert not drop.other_axis_moving
            assert drop.other_axis_position == mm_to_steps(RELEASE_DISTANCES[count] + offset)


@pytest.mark.parametrize("num_left,num_right", COMBOS)
def test_scoop_ends_with_every_axis_home(arms, sim_state, num_left, num_right):
    arms.scoop(num_left, num_right)
    finish(arms, sim_state)
    assert arms.is_home()


@pytest.mark.parametrize("num_left,num_right", [(1, 0), (0, 1), (2, 3), (4, 1)])
def test_scoop_reaches_and_lifts_by_each_arms_trims(arms, boards, sim_state, num_left, num_right):
    arms.tuning.offset_left, arms.tuning.offset_right = -6, 11
    arms.tuning.offset_v_left, arms.tuning.offset_v_right = 7, -3
    arms.scoop(num_left, num_right)
    finish(arms, sim_state)
    for board, count, offset, offset_v in zip(boards, (num_right, num_left), (11, -6), (-3, 7)):
        reaches = [move.target for move in board.moves if move.stepper == H and move.target > 0]
        lifts = [move.target for move in board.moves if move.stepper == V and move.target > 0]
        assert max(reaches, default=None) == (mm_to_steps(pickup_mm(count, offset)) if count else None)
        assert lifts == ([mm_to_steps(LIFT_DISTANCE + offset_v)] if count else [])


@pytest.mark.parametrize("num_left,num_right", [(-1, 2), (0, 0), (3, 3)])
def test_scoop_rejects_impossible_counts_without_moving(arms, boards, num_left, num_right):
    with pytest.raises(ValueError):
        arms.scoop(num_left, num_right)
    assert not arms.busy and not all_moves(boards)


def test_stop_balls_lifts_by_each_arms_vertical_trim(arms, boards, sim_state):
    arms.tuning.offset_v_left, arms.tuning.offset_v_right = 7, -3
    arms.stop_balls(end_at_home=True)
    finish(arms, sim_state)
    for board, offset_v in zip(boards, (-3, 7)):
        assert [move.target for move in board.moves if move.stepper == V and move.target > 0] == [
            mm_to_steps(LIFT_DISTANCE + offset_v)]


def test_home_zeroes_every_axis_on_its_switch(arms, boards, sim_state):
    start_away_from_home(boards, sim_state)
    assert not arms.is_home()
    arms.home()
    finish(arms, sim_state)
    assert all(homed(board, stepper) for board in boards for stepper in (H, V))
    assert arms.is_home()


@pytest.mark.parametrize("num_left,num_right", [(1, 0), (2, 3)])
def test_scoop_after_homing_runs_as_fast_as_after_startup(arms, boards, sim_state, num_left, num_right):
    after_startup = timed_scoop(arms, sim_state, num_left, num_right)
    start_away_from_home(boards, sim_state)
    arms.home()
    finish(arms, sim_state)
    assert timed_scoop(arms, sim_state, num_left, num_right) == pytest.approx(after_startup)


def test_home_raises_when_a_switch_never_closes(arms, boards, sim_state):
    start_away_from_home(boards, sim_state)
    boards[1].disconnect_switch(H)
    arms.home()
    with pytest.raises(HomingError, match="left horizontal"):
        finish(arms, sim_state)


def test_motion_raises_when_a_motor_never_stops(arms, boards, sim_state):
    boards[0].stalled.add(H)
    arms.back_to_home()
    with pytest.raises(TimeoutError):
        finish(arms, sim_state)


@pytest.mark.parametrize("board_index,stepper", [(0, H), (0, V), (1, H), (1, V)])
def test_is_home_notices_an_axis_pushed_off_its_switch(arms, boards, sim_state, board_index, stepper):
    push_off_switch(boards[board_index], stepper, 400)
    assert not arms.is_home()
    arms.home()
    finish(arms, sim_state)
    assert arms.is_home()


def test_abort_stops_every_moving_axis(arms, boards, sim_state):
    arms.scoop(2, 3)
    for _ in range(20):
        arms.tick()
        sim_state.clock.advance(0.016)
    assert any(not board.getStepperStatus(stepper).stopped for board in boards for stepper in (H, V))
    arms.abort()
    assert not arms.busy
    assert all(board.getStepperStatus(stepper).stopped for board in boards for stepper in (H, V))
