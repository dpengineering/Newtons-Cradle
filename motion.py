from dataclasses import dataclass, field
from typing import Callable, NamedTuple

from dpeaDPi import StepperDriver

from config import MOTION_TIMEOUT_S


class HomingError(RuntimeError):
    pass


class Axis(NamedTuple):
    board: StepperDriver
    stepper: int
    name: str


@dataclass(frozen=True)
class MoveTo:
    axis: Axis
    target: int

    def start(self, now):
        self.axis.board.moveToAbsolutePositionInSteps(self.axis.stepper, self.target, False)

    def done(self, now):
        # The position check keeps a status read that lands before the board starts moving from counting as done.
        board, stepper, _ = self.axis
        return board.getStepperStatus(stepper).stopped and board.getCurrentPositionInSteps(stepper) == self.target


@dataclass
class SeekSwitch:
    axis: Axis
    closed: bool
    distance: int
    _end: int | None = field(default=None, init=False)

    def start(self, now):
        board, stepper, _ = self.axis
        if board.getStepperStatus(stepper).at_home == self.closed:
            return
        self._end = board.getCurrentPositionInSteps(stepper) + self.distance
        board.moveToRelativePositionInSteps(stepper, self.distance, False)

    def done(self, now):
        board, stepper, name = self.axis
        status = board.getStepperStatus(stepper)
        if status.at_home == self.closed:
            if self._end is not None:
                board.emergencyStop(stepper)
            return True
        if status.stopped and board.getCurrentPositionInSteps(stepper) == self._end:
            raise HomingError("the %s axis ran %d steps without its home switch changing" % (name, abs(self.distance)))
        return False


@dataclass
class Settle:
    seconds: float
    _until: float = field(default=0.0, init=False)

    def start(self, now):
        self._until = now + self.seconds

    def done(self, now):
        return now >= self._until


@dataclass(frozen=True)
class Do:
    action: Callable[[], None]

    def start(self, now):
        self.action()

    def done(self, now):
        return True


class Step:
    def __init__(self, *parts, timeout=MOTION_TIMEOUT_S):
        self.parts = parts
        self.timeout = timeout


class MotionRunner:
    """Runs a plan one Step at a time without blocking.

    Each Step is a state whose moves are sent on entry. tick() polls the parts
    still running and enters the next Step once they are all done.
    """

    def __init__(self, clock):
        self._clock = clock
        self._steps = []
        self._pending = []
        self._deadline = 0.0
        self._timeout = 0.0

    @property
    def busy(self):
        return bool(self._pending or self._steps)

    def start(self, plan):
        self._steps = list(plan)
        self._pending = []
        self.tick()

    def clear(self):
        self._steps = []
        self._pending = []

    def tick(self):
        while True:
            now = self._clock()
            self._pending = [part for part in self._pending if not part.done(now)]
            if self._pending:
                if now > self._deadline:
                    raise TimeoutError("motion did not finish within %.0fs" % self._timeout)
                return
            if not self._steps:
                return
            step = self._steps.pop(0)
            self._timeout = step.timeout
            self._deadline = now + step.timeout
            for part in step.parts:
                part.start(now)
            self._pending = list(step.parts)
