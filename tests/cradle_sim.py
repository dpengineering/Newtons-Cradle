from dataclasses import dataclass

from dpeaDPi.simulation.stepper import SimulatedDPiStepper

STATUS_POLL_SECONDS = 0.001


@dataclass(frozen=True)
class MoveRecord:
    at: float
    board: int
    stepper: int
    start: int
    target: int
    wait: bool
    other_axis_moving: bool
    other_axis_position: int
    acceleration: float


class CradleStepper(SimulatedDPiStepper):
    """SimulatedDPiStepper with home switches that close at position <= 0, and a move log.

    Each status poll advances the shared clock, like the real I2C round trip,
    so polling loops make progress in simulated time.
    """

    def __init__(self, state, boardNumber):
        super().__init__(state=state, boardNumber=boardNumber, auto_complete=False)
        self.moves = []
        self.acceleration = {}
        self.stuck_open_switches = set()
        self.stalled = set()
        self._switch_closed = {}

    def _sync_home_switch(self, stepperNum):
        at_home = (stepperNum not in self.stuck_open_switches
                   and self.getCurrentPositionInSteps(stepperNum) <= 0)
        if at_home != self._switch_closed.get(stepperNum):
            self.controls.set_home_switch(stepperNum, at_home)
            self._switch_closed[stepperNum] = at_home

    def getStepperStatus(self, stepperNum):
        self._state.clock.advance(STATUS_POLL_SECONDS)
        self._sync_home_switch(stepperNum)
        status = super().getStepperStatus(stepperNum)
        if stepperNum in self.stalled:
            return status._replace(stopped=False)
        return status

    def setAccelerationInStepsPerSecondPerSecond(self, stepperNum, accelerationInStepsPerSecondPerSecond):
        super().setAccelerationInStepsPerSecondPerSecond(stepperNum, accelerationInStepsPerSecondPerSecond)
        self.acceleration[stepperNum] = accelerationInStepsPerSecondPerSecond

    def _record_move(self, stepperNum, target, wait):
        other = 1 - stepperNum
        self.moves.append(MoveRecord(
            at=self._state.clock.now(),
            board=self._boardNumber,
            stepper=stepperNum,
            start=self.getCurrentPositionInSteps(stepperNum),
            target=target,
            wait=wait,
            other_axis_moving=not self.getMotionComplete(other),
            other_axis_position=self.getCurrentPositionInSteps(other),
            acceleration=self.acceleration.get(stepperNum),
        ))

    def moveToAbsolutePositionInSteps(self, stepperNum, absolutePositionToMoveToInSteps, waitToFinishFlg):
        self._record_move(stepperNum, absolutePositionToMoveToInSteps, waitToFinishFlg)
        super().moveToAbsolutePositionInSteps(stepperNum, absolutePositionToMoveToInSteps, waitToFinishFlg)
        self._sync_home_switch(stepperNum)

    def moveToRelativePositionInSteps(self, stepperNum, distanceToMoveInSteps, waitToFinishFlg):
        target = self.getCurrentPositionInSteps(stepperNum) + distanceToMoveInSteps
        self._record_move(stepperNum, target, waitToFinishFlg)
        super().moveToRelativePositionInSteps(stepperNum, distanceToMoveInSteps, waitToFinishFlg)
        self._sync_home_switch(stepperNum)




def settle(*boards):
    for board in boards:
        for stepperNum in (0, 1):
            board.waitUntilMotorStops(stepperNum)
