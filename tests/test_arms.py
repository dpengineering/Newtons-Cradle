import pytest

from config import (
    DISTANCE_TO_FIRST_BALL,
    LIFT_DISTANCE,
    RELEASE_DISTANCES,
    STOP_BALLS_BACK_OFF,
    STOP_BALLS_HOLD_S,
    mm_to_steps,
    pickup_mm,
)
from cradle_sim import FRAME_SECONDS, push_off_switch, run
from motion import HomingError

COMBOS = [(left, right) for left in range(6) for right in range(6) if 0 < left + right <= 5]


def finish(arms, sim_state):
    run(sim_state, arms.tick, lambda: not arms.busy)


def all_moves(boards):
    return [move for board in boards for move in board.moves]


def start_away_from_home(boards, sim_state):
    for board in boards:
        for stepper in (board.h, board.v):
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


def test_stop_balls_never_moves_both_axes_of_an_arm_at_once(arms, boards, sim_state):
    arms.stop_balls()
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
            drop = next(move for move in board.moves if move.stepper == board.v and move.start > 0 and move.target == 0)
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
        reaches = [move.target for move in board.moves if move.stepper == board.h and move.target > 0]
        lifts = [move.target for move in board.moves if move.stepper == board.v and move.target > 0]
        assert max(reaches, default=None) == (mm_to_steps(pickup_mm(count, offset)) if count else None)
        assert lifts == ([mm_to_steps(LIFT_DISTANCE + offset_v)] if count else [])


@pytest.mark.parametrize("num_left,num_right", [(-1, 2), (0, 0), (3, 3)])
def test_scoop_rejects_impossible_counts_without_moving(arms, boards, num_left, num_right):
    with pytest.raises(ValueError):
        arms.scoop(num_left, num_right)
    assert not arms.busy and not all_moves(boards)


def test_stop_balls_lifts_by_each_arms_vertical_trim(arms, boards, sim_state):
    arms.tuning.offset_v_left, arms.tuning.offset_v_right = 7, -3
    arms.stop_balls()
    finish(arms, sim_state)
    for board, offset_v in zip(boards, (-3, 7)):
        assert [move.target for move in board.moves if move.stepper == board.v and move.target > 0] == [
            mm_to_steps(LIFT_DISTANCE + offset_v)]


def test_stop_balls_leaves_every_scooper_lowered_just_off_its_first_ball(arms, boards, sim_state):
    arms.stop_balls()
    finish(arms, sim_state)
    for board, offset in zip(boards, (arms.tuning.offset_right, arms.tuning.offset_left)):
        assert board.getCurrentPositionInSteps(board.v) == 0
        assert board.getCurrentPositionInSteps(board.h) == mm_to_steps(
            DISTANCE_TO_FIRST_BALL + offset - STOP_BALLS_BACK_OFF)


def test_stop_balls_holds_the_balls_then_backs_off_before_lowering(arms, boards, sim_state):
    arms.tuning.offset_left, arms.tuning.offset_right = -6, 11
    arms.tuning.offset_v_left, arms.tuning.offset_v_right = 7, -3
    clamps = [mm_to_steps(DISTANCE_TO_FIRST_BALL + offset) for offset in (11, -6)]
    clamped_at = [None, None]

    def tick():
        arms.tick()
        for i, (board, clamp) in enumerate(zip(boards, clamps)):
            if (clamped_at[i] is None and board.getMotionComplete(board.h)
                    and board.getCurrentPositionInSteps(board.h) == clamp):
                clamped_at[i] = sim_state.clock.now()

    arms.stop_balls()
    run(sim_state, tick, lambda: not arms.busy)
    for board, clamp, offset_v in zip(boards, clamps, (-3, 7)):
        back_off = next(move for move in board.moves if move.stepper == board.h and move.start == clamp)
        lower = next(move for move in board.moves if move.stepper == board.v and move.start > 0 and move.target == 0)
        assert back_off.at - max(clamped_at) == pytest.approx(STOP_BALLS_HOLD_S, abs=2 * FRAME_SECONDS)
        assert back_off.target == clamp - mm_to_steps(STOP_BALLS_BACK_OFF)
        assert back_off.other_axis_position == mm_to_steps(LIFT_DISTANCE + offset_v)
        assert lower.other_axis_position == back_off.target


@pytest.mark.parametrize("num_left,num_right", [(1, 0), (0, 2), (2, 3)])
def test_stop_trims_move_only_where_the_arms_stop_the_balls(arms, boards, sim_state, num_left, num_right):
    arms.tuning.offset_left, arms.tuning.offset_right = -6, 11
    arms.tuning.stop_offset_left, arms.tuning.stop_offset_right = 4, -3
    arms.stop_balls()
    finish(arms, sim_state)
    stop_moves = [[move.target for move in board.moves if move.stepper == board.h and move.target > 0]
                  for board in boards]
    for board in boards:
        board.moves.clear()
    arms.scoop(num_left, num_right)
    finish(arms, sim_state)
    for board, moves, count, offset, stop_offset in zip(boards, stop_moves, (num_right, num_left), (11, -6), (-3, 4)):
        clamp = DISTANCE_TO_FIRST_BALL + offset + stop_offset
        assert moves == [mm_to_steps(clamp), mm_to_steps(clamp - STOP_BALLS_BACK_OFF)]
        reaches = [move.target for move in board.moves if move.stepper == board.h and move.target > 0]
        assert reaches == ([mm_to_steps(pickup_mm(count, offset)), mm_to_steps(RELEASE_DISTANCES[count] + offset)]
                           if count else [])


@pytest.mark.parametrize("num_left,num_right", [(1, 0), (0, 2), (3, 0), (0, 5)])
def test_an_idle_arm_heads_home_during_the_scoop_and_is_home_before_the_drop(arms, boards, sim_state,
                                                                            num_left, num_right):
    arms.stop_balls()
    finish(arms, sim_state)
    active, idle = (boards[0], boards[1]) if num_right else (boards[1], boards[0])
    active.moves.clear()
    idle.moves.clear()
    # Slow enough that the scooping arm reaches its release point first.
    idle.setSpeedInStepsPerSecond(idle.h, 1000)
    idle_home_at = []

    def tick():
        arms.tick()
        if not idle_home_at and idle.getCurrentPositionInSteps(idle.h) == 0 and idle.getMotionComplete(idle.h):
            idle_home_at.append(sim_state.clock.now())

    arms.scoop(num_left, num_right)
    run(sim_state, tick, lambda: not arms.busy)
    reach = active.moves[0]
    heading_home = idle.moves[0]
    drop = next(move for move in active.moves if move.stepper == active.v and move.start > 0 and move.target == 0)
    assert (heading_home.stepper, heading_home.target, heading_home.at) == (idle.h, 0, reach.at)
    assert reach.at < idle_home_at[0] <= drop.at


def test_home_zeroes_every_axis_on_its_switch(arms, boards, sim_state):
    start_away_from_home(boards, sim_state)
    assert not arms.is_home()
    arms.home()
    finish(arms, sim_state)
    assert all(homed(board, stepper) for board in boards for stepper in (board.h, board.v))
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
    boards[1].disconnect_switch(boards[1].h)
    arms.home()
    with pytest.raises(HomingError, match="left horizontal"):
        finish(arms, sim_state)


def test_motion_raises_when_a_motor_never_stops(arms, boards, sim_state):
    boards[0].stalled.add(boards[0].h)
    arms.back_to_home()
    with pytest.raises(TimeoutError):
        finish(arms, sim_state)


@pytest.mark.parametrize("board_index,axis", [(0, "h"), (0, "v"), (1, "h"), (1, "v")])
def test_is_home_notices_an_axis_pushed_off_its_switch(arms, boards, sim_state, board_index, axis):
    board = boards[board_index]
    push_off_switch(board, getattr(board, axis), 400)
    assert not arms.is_home()
    arms.home()
    finish(arms, sim_state)
    assert arms.is_home()


def test_abort_stops_every_moving_axis(arms, boards, sim_state):
    arms.scoop(2, 3)
    for _ in range(20):
        arms.tick()
        sim_state.clock.advance(0.016)
    assert any(not board.getStepperStatus(stepper).stopped for board in boards for stepper in (board.h, board.v))
    arms.abort()
    assert not arms.busy
    assert all(board.getStepperStatus(stepper).stopped for board in boards for stepper in (board.h, board.v))
