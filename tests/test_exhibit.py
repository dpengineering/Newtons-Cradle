import time

import pytest
from dpeaDPi.errors import DPiCommunicationError

from arms import CradleArms, Position
from config import LIFT_DISTANCE, STOP_BALLS_BACK_OFF, Tuning, mm_to_steps
from cradle_sim import FRAME_SECONDS, push_off_switch, run
from exhibit import OUTPUTS, Exhibit, Phase

SCOOP_PHASES = [Phase.PREPARING, Phase.STOPPING_BALLS, Phase.SCOOPING, Phase.CHECKING_HOME, Phase.COOLDOWN,
                Phase.READY]


def record_phases(exhibit, sim_state):
    phases = []
    exhibit.on_phase = lambda phase: phases.append((phase, sim_state.clock.now()))
    return phases


def until(exhibit, phase):
    return lambda: exhibit.phase is phase


def motors_on(boards):
    states = {board.getStepperStatus(stepper).enabled for board in boards for stepper in (board.h, board.v)}
    assert len(states) == 1
    return states.pop()


def test_startup_homes_arms_that_start_off_their_switches(boards, sim_state):
    for board in boards:
        for stepper in (board.h, board.v):
            board.moveToAbsolutePositionInSteps(stepper, 2000, False)
    sim_state.run_until_idle()
    arms = CradleArms(*boards, Tuning(), sim_state.clock.now)
    exhibit = Exhibit(arms, sim_state.clock.now)
    exhibit.start()
    assert exhibit.phase is Phase.STARTING
    run(sim_state, exhibit.tick, until(exhibit, Phase.READY))
    assert arms.is_home()
    assert not motors_on(boards)


@pytest.mark.parametrize("num_left,num_right", [(1, 0), (0, 3), (2, 2), (1, 4)])
def test_scoop_runs_each_phase_in_order_without_rehoming(exhibit, sim_state, homings, num_left, num_right):
    phases = record_phases(exhibit, sim_state)
    exhibit.request_scoop(num_left, num_right)
    run(sim_state, exhibit.tick, until(exhibit, Phase.READY))
    assert [phase for phase, _ in phases] == SCOOP_PHASES
    assert homings == []


def test_motors_are_powered_exactly_when_the_phase_says(exhibit, boards, sim_state):
    exhibit.request_scoop(2, 1)
    seen = set()

    def tick_and_check():
        exhibit.tick()
        assert motors_on(boards) == OUTPUTS[exhibit.phase].motors_on
        seen.add(exhibit.phase)

    run(sim_state, tick_and_check, until(exhibit, Phase.READY))
    assert set(SCOOP_PHASES) <= seen | {Phase.PREPARING}


def test_cooldown_lasts_the_tuned_time(exhibit, sim_state):
    exhibit.arms.tuning.cooldown_secs = 7
    phases = record_phases(exhibit, sim_state)
    exhibit.request_scoop(0, 1)
    run(sim_state, exhibit.tick, until(exhibit, Phase.READY))
    started, ended = dict(phases)[Phase.COOLDOWN], dict(phases)[Phase.READY]
    assert ended - started == pytest.approx(7, abs=2 * FRAME_SECONDS)


@pytest.mark.parametrize("phase", [Phase.PREPARING, Phase.SCOOPING, Phase.COOLDOWN])
def test_scoop_requests_are_ignored_outside_ready(exhibit, sim_state, phase):
    exhibit.request_scoop(1, 0)
    run(sim_state, exhibit.tick, until(exhibit, phase))
    phases = record_phases(exhibit, sim_state)
    exhibit.request_scoop(0, 2)
    assert phases == []


def test_empty_scoop_requests_are_ignored(exhibit):
    exhibit.request_scoop(0, 0)
    assert exhibit.phase is Phase.READY


def test_an_arm_pushed_off_its_switch_while_ready_is_rehomed_before_the_scoop(exhibit, boards, sim_state, homings):
    push_off_switch(boards[1], boards[1].h, 500)
    exhibit.request_scoop(1, 1)
    assert exhibit.phase is Phase.PREPARING and homings == [1]
    run(sim_state, exhibit.tick, until(exhibit, Phase.READY))
    assert homings == [1]
    assert exhibit.arms.is_home()


def test_an_arm_that_loses_steps_mid_scoop_is_rehomed_before_cooldown(exhibit, boards, sim_state, homings):
    right = boards[0]
    exhibit.request_scoop(0, 2)
    # Wait for the carry back to the release point, once the lift has finished.
    run(sim_state, exhibit.tick, lambda: exhibit.phase is Phase.SCOOPING
        and right.getCurrentPositionInSteps(right.v) > 0 and not right.getStepperStatus(right.h).stopped)
    # The lifted scooper slips 200 steps, so lowering it to 0 leaves it short of its switch.
    right.setCurrentPositionInSteps(right.v, right.getCurrentPositionInSteps(right.v) - 200)
    assert homings == []
    run(sim_state, exhibit.tick, until(exhibit, Phase.CHECKING_HOME))
    assert homings == [1]
    run(sim_state, exhibit.tick, until(exhibit, Phase.COOLDOWN))
    assert exhibit.arms.is_home()


def test_admin_return_mid_scoop_stops_homes_and_unpowers(exhibit, boards, sim_state):
    exhibit.request_scoop(2, 3)
    run(sim_state, exhibit.tick, until(exhibit, Phase.SCOOPING))
    run(sim_state, exhibit.tick, lambda: any(board.getCurrentPositionInSteps(board.h) > 0 for board in boards))
    exhibit.request_return()
    run(sim_state, exhibit.tick, until(exhibit, Phase.READY))
    assert exhibit.arms.is_home()
    assert not motors_on(boards)


def test_exit_mid_scoop_homes_unpowers_then_hands_off_once(exhibit, boards, sim_state):
    exited = []
    exhibit.request_scoop(1, 2)
    run(sim_state, exhibit.tick, until(exhibit, Phase.SCOOPING))
    exhibit.request_exit(lambda: exited.append(exhibit.arms.is_home()))
    run(sim_state, exhibit.tick, until(exhibit, Phase.STOPPED))
    for _ in range(10):
        exhibit.tick()
    assert exited == [True]
    assert not motors_on(boards)


def test_a_board_failure_unpowers_the_motors_and_propagates(exhibit, boards, sim_state):
    exhibit.request_scoop(0, 3)
    run(sim_state, exhibit.tick, until(exhibit, Phase.SCOOPING))
    sim_state.fail_next("stepper", "getStepperStatus")
    with pytest.raises(DPiCommunicationError):
        run(sim_state, exhibit.tick, until(exhibit, Phase.READY))
    assert not motors_on(boards)


def test_nothing_ever_sleeps(boards, sim_state, monkeypatch):
    def no_sleeping(seconds):
        raise AssertionError("slept for %ss" % seconds)

    monkeypatch.setattr(time, "sleep", no_sleeping)
    exhibit = Exhibit(CradleArms(*boards, Tuning(), sim_state.clock.now), sim_state.clock.now)
    exhibit.start()
    run(sim_state, exhibit.tick, until(exhibit, Phase.READY))
    exhibit.request_scoop(2, 3)
    run(sim_state, exhibit.tick, until(exhibit, Phase.READY))
    exhibit.request_exit(lambda: None)
    run(sim_state, exhibit.tick, until(exhibit, Phase.STOPPED))


def h_steps(boards):
    return [board.getCurrentPositionInSteps(board.h) for board in boards]


def sought_switches(boards):
    return any(move.relative for board in boards for move in board.moves)


def hold(exhibit, sim_state, position):
    exhibit.request_position(position)
    assert exhibit.phase is Phase.POSITIONING
    run(sim_state, exhibit.tick, until(exhibit, Phase.POSITIONED))


@pytest.mark.parametrize("position", list(Position))
def test_go_holds_the_arms_at_the_chosen_position_powered_and_shuts_out_visitors(exhibit, boards, sim_state,
                                                                                position):
    for board in boards:
        board.moves.clear()
    hold(exhibit, sim_state, position)
    assert exhibit.position is position and not sought_switches(boards)
    assert motors_on(boards)
    assert not OUTPUTS[Phase.POSITIONED].accepts_input
    for _ in range(100):
        exhibit.tick()
        sim_state.clock.advance(FRAME_SECONDS)
    assert exhibit.phase is Phase.POSITIONED


def test_go_mid_scoop_stops_the_scoop_and_still_arrives(exhibit, boards, sim_state):
    exhibit.request_scoop(0, 2)
    run(sim_state, exhibit.tick, lambda: exhibit.phase is Phase.SCOOPING and h_steps(boards)[0] > 0)
    hold(exhibit, sim_state, Position.RAISED)
    tuning = exhibit.arms.tuning
    assert [steps_of(board) for board in boards] == [(0, mm_to_steps(LIFT_DISTANCE + tuning.offset_v_right)),
                                                     (0, mm_to_steps(LIFT_DISTANCE + tuning.offset_v_left))]


def test_go_rehomes_an_arm_pushed_off_its_switch_first(exhibit, boards, sim_state):
    push_off_switch(boards[1], boards[1].h, 500)
    for board in boards:
        board.moves.clear()
    hold(exhibit, sim_state, Position.HOME)
    assert sought_switches(boards) and exhibit.arms.is_home()


def test_go_from_one_held_position_to_another_moves_without_rehoming(exhibit, boards, sim_state):
    hold(exhibit, sim_state, Position.STOP)
    for board in boards:
        board.moves.clear()
    hold(exhibit, sim_state, Position.RAISED)
    assert not sought_switches(boards)
    assert h_steps(boards) == [0, 0]


@pytest.mark.parametrize("target", [Position.HOME, Position.RAISED])
def test_leaving_stop_backs_off_from_where_the_arms_are_even_after_a_trim_edit(exhibit, boards, sim_state, target):
    hold(exhibit, sim_state, Position.STOP)
    held = h_steps(boards)
    exhibit.arms.tuning.stop_offset_left += 30
    exhibit.arms.tuning.offset_right += 20
    for board in boards:
        board.moves.clear()
    hold(exhibit, sim_state, target)
    for board, start in zip(boards, held):
        raised_moves = [move.target for move in board.moves if move.stepper == board.h and move.other_axis_position > 0]
        lower = next(move for move in board.moves if move.stepper == board.v and move.target == 0)
        assert raised_moves == [start - mm_to_steps(STOP_BALLS_BACK_OFF)]
        assert lower.other_axis_position == start - mm_to_steps(STOP_BALLS_BACK_OFF)


@pytest.mark.parametrize("position,side,trim,board_index,axis", [
    (Position.STOP, "left", "stop_offset_left", 1, "h"),
    (Position.STOP, "right", "stop_offset_right", 0, "h"),
    (Position.RAISED, "left", "offset_v_left", 1, "v"),
    (Position.RAISED, "right", "offset_v_right", 0, "v"),
])
def test_a_jog_moves_that_arm_a_millimeter_and_saves_its_trim(exhibit, boards, sim_state, monkeypatch, tmp_path,
                                                              position, side, trim, board_index, axis):
    monkeypatch.chdir(tmp_path)
    hold(exhibit, sim_state, position)
    board = boards[board_index]
    other = boards[1 - board_index]
    before, other_before = board.getCurrentPositionInSteps(getattr(board, axis)), steps_of(other)
    exhibit.request_jog(side, -1)
    assert getattr(exhibit.arms.tuning, trim) == -1
    assert '"%s": -1' % trim in (tmp_path / "variables.json").read_text()
    run(sim_state, exhibit.tick, until(exhibit, Phase.POSITIONED))
    assert board.getCurrentPositionInSteps(getattr(board, axis)) == before - mm_to_steps(1)
    assert steps_of(other) == other_before


def steps_of(board):
    return board.getCurrentPositionInSteps(board.h), board.getCurrentPositionInSteps(board.v)


def test_jogs_are_ignored_unless_the_arms_are_held_at_a_trimmed_position(exhibit, sim_state, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    tuning = exhibit.arms.tuning
    before = tuning.model_dump()
    exhibit.request_jog("left", 1)
    hold(exhibit, sim_state, Position.HOME)
    exhibit.request_jog("left", 1)
    exhibit.request_position(Position.STOP)
    exhibit.request_jog("left", 1)
    assert tuning.model_dump() == before
    assert not (tmp_path / "variables.json").exists()


def test_a_jog_past_a_trim_limit_leaves_the_arm_and_the_trim(exhibit, boards, sim_state, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    exhibit.arms.tuning.stop_offset_left = -39
    hold(exhibit, sim_state, Position.STOP)
    exhibit.request_jog("left", -1)
    assert exhibit.phase is Phase.POSITIONED
    assert exhibit.arms.tuning.stop_offset_left == -39
    assert not (tmp_path / "variables.json").exists()


@pytest.mark.parametrize("position", [Position.RAISED, Position.STOP])
def test_admin_return_from_a_held_position_homes_and_unpowers(exhibit, boards, sim_state, position):
    hold(exhibit, sim_state, position)
    exhibit.request_return()
    run(sim_state, exhibit.tick, until(exhibit, Phase.READY))
    assert exhibit.arms.is_home()
    assert not motors_on(boards)
