#!/usr/bin/env python3
"""Run the exhibit on a machine without the boards, against dpeaDPi's simulated steppers in real time."""
from dpeaDPi.simulation import HomeSwitchWindow, SimState, SimulatedDPiStepper, WallClock

from arms import CradleArms
from config import Tuning
from exhibit import Exhibit
from main import NewtonsCradleApp

HOME_SWITCH = HomeSwitchWindow(start=-(2**31), end=0)


def simulated_boards(state):
    boards = SimulatedDPiStepper(state, 0), SimulatedDPiStepper(state, 1)
    for board in boards:
        for stepper in (0, 1):
            board.controls.set_home_switch_window(stepper, HOME_SWITCH)
            # Start each axis off its switch, the way the arms sit after a power cut.
            board.moveToAbsolutePositionInSteps(stepper, 2000, False)
    state.run_until_idle()
    return boards


if __name__ == '__main__':
    state = SimState(WallClock())
    arms = CradleArms(*simulated_boards(state), Tuning(), state.clock.now)
    NewtonsCradleApp(Exhibit(arms, state.clock.now), shutdown=lambda: print("[simulated] systemctl stop")).run()
