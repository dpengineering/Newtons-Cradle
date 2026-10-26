from dataclasses import dataclass

from dpeaDPi.simulation import HomeSwitchWindow, SimulatedDPiStepper

# Every axis homes toward negative steps onto a switch that stays closed up to the hard stop.
HOME_SWITCH = HomeSwitchWindow(start=-(2**31), end=0)
DISCONNECTED_SWITCH = HomeSwitchWindow(start=-(2**31), end=-(2**31))


@dataclass(frozen=True)
class MoveRecord:
    at: float
    stepper: int
    start: int
    target: int
    other_axis_moving: bool
    other_axis_position: int


class CradleStepper(SimulatedDPiStepper):
    """SimulatedDPiStepper with the exhibit's home switches mounted and a log of every move."""

    def __init__(self, state, boardNumber):
        super().__init__(state=state, boardNumber=boardNumber)
        self.moves = []
        self.stalled = set()
        for stepperNum in (0, 1):
            self.controls.set_home_switch_window(stepperNum, HOME_SWITCH)

    def disconnect_switch(self, stepperNum):
        self.controls.set_home_switch_window(stepperNum, DISCONNECTED_SWITCH)

    def getStepperStatus(self, stepperNum):
        status = super().getStepperStatus(stepperNum)
        if stepperNum in self.stalled:
            return status._replace(stopped=False)
        return status

    def _record_move(self, stepperNum, target):
        other = 1 - stepperNum
        self.moves.append(MoveRecord(
            at=self._state.clock.now(),
            stepper=stepperNum,
            start=self.getCurrentPositionInSteps(stepperNum),
            target=target,
            other_axis_moving=not self.getMotionComplete(other),
            other_axis_position=self.getCurrentPositionInSteps(other),
        ))

    def moveToAbsolutePositionInSteps(self, stepperNum, absolutePositionToMoveToInSteps, waitToFinishFlg):
        self._record_move(stepperNum, absolutePositionToMoveToInSteps)
        super().moveToAbsolutePositionInSteps(stepperNum, absolutePositionToMoveToInSteps, waitToFinishFlg)

    def moveToRelativePositionInSteps(self, stepperNum, distanceToMoveInSteps, waitToFinishFlg):
        self._record_move(stepperNum, self.getCurrentPositionInSteps(stepperNum) + distanceToMoveInSteps)
        super().moveToRelativePositionInSteps(stepperNum, distanceToMoveInSteps, waitToFinishFlg)
