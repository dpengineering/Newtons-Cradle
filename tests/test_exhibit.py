import time

import pytest
from dpeaDPi.errors import DPiCommunicationError

from arms import CradleArms
from config import Tuning
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
    states = {board.getStepperStatus(stepper).enabled for board in boards for stepper in (0, 1)}
    assert len(states) == 1
    return states.pop()


def test_startup_homes_arms_that_start_off_their_switches(boards, sim_state):
    for board in boards:
        for stepper in (0, 1):
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
    push_off_switch(boards[1], 0, 500)
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
        and right.getCurrentPositionInSteps(1) > 0 and not right.getStepperStatus(0).stopped)
    # The lifted scooper slips 200 steps, so lowering it to 0 leaves it short of its switch.
    right.setCurrentPositionInSteps(1, right.getCurrentPositionInSteps(1) - 200)
    assert homings == []
    run(sim_state, exhibit.tick, until(exhibit, Phase.CHECKING_HOME))
    assert homings == [1]
    run(sim_state, exhibit.tick, until(exhibit, Phase.COOLDOWN))
    assert exhibit.arms.is_home()


def test_admin_return_mid_scoop_stops_homes_and_unpowers(exhibit, boards, sim_state):
    exhibit.request_scoop(2, 3)
    run(sim_state, exhibit.tick, until(exhibit, Phase.SCOOPING))
    run(sim_state, exhibit.tick, lambda: any(board.getCurrentPositionInSteps(0) > 0 for board in boards))
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
