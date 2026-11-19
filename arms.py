from enum import Enum, auto

from dpeaDPi import StepperDriver

from config import (
    ACCEL_MM_PER_S2,
    DISTANCE_TO_FIRST_BALL,
    HOME_MAX_STEPS,
    HOME_SETTLE_S,
    HOME_SLOW_SPEED_STEPS_PER_S,
    HOME_SPEED_STEPS_PER_S,
    LEFT_STEPPERS,
    LIFT_DISTANCE,
    MAX_BALLS,
    RELEASE_DISTANCES,
    RIGHT_STEPPERS,
    SPEED_MM_PER_S,
    STOP_BALLS_BACK_OFF,
    STOP_BALLS_HOLD_S,
    Tuning,
    mm_to_steps,
    pickup_mm,
)
from motion import Axis, AwaitMove, Do, MotionRunner, MoveTo, SeekSwitch, Settle, StartMove, Step

# Each arm's axes, as indexes into RIGHT_STEPPERS and LEFT_STEPPERS.
HORIZONTAL, VERTICAL = 0, 1
TOWARD_HOME = -1


class Position(Enum):
    """Where the admin screen can hold the arms while tuning them."""

    HOME = auto()
    RAISED = auto()
    STOP = auto()


# The trim each arm's jog changes at a position. The switches set HOME, so it has none.
JOG_TRIMS = {
    Position.RAISED: {"left": "offset_v_left", "right": "offset_v_right"},
    Position.STOP: {"left": "stop_offset_left", "right": "stop_offset_right"},
}


def _seek_timeout(speed):
    return HOME_MAX_STEPS / speed + speed / HOME_SPEED_STEPS_PER_S + 1


class CradleArms:
    """The two scooper arms. Board 0 drives the right arm and board 1 the left, each with a
    horizontal and vertical axis homed toward negative steps on the steppers in RIGHT_STEPPERS
    and LEFT_STEPPERS.

    Every motion method starts a plan and returns at once. Call tick() until busy is False.
    """

    def __init__(self, right: StepperDriver, left: StepperDriver, tuning: Tuning, clock):
        self.right = right
        self.left = left
        self.tuning = tuning
        self._runner = MotionRunner(clock)
        self.axes = [Axis(board, self.stepper(board, role), "%s %s" % (side, direction))
                     for board, side in ((right, "right"), (left, "left"))
                     for role, direction in ((HORIZONTAL, "horizontal"), (VERTICAL, "vertical"))]

    @property
    def boards(self):
        return self.right, self.left

    def stepper(self, board, role):
        """The stepper number on this board that drives its HORIZONTAL or VERTICAL axis."""
        return (RIGHT_STEPPERS if board is self.right else LEFT_STEPPERS)[role]

    @property
    def busy(self):
        return self._runner.busy

    def tick(self):
        self._runner.tick()

    def abort(self):
        self._runner.clear()
        for board, stepper, _ in self.axes:
            board.emergencyStop(stepper)

    def initialize(self):
        for board in self.boards:
            board.initialize()
        self._set_rates(mm_to_steps(SPEED_MM_PER_S), mm_to_steps(ACCEL_MM_PER_S2))

    def enable_motors(self, enabled):
        for board in self.boards:
            board.enableMotors(enabled)

    def is_home(self):
        # Homing zeroes each counter where its switch closes, so an axis stopped at 0 on a
        # closed switch hasn't lost steps.
        for board, stepper, _ in self.axes:
            status = board.getStepperStatus(stepper)
            if not (status.stopped and status.at_home and board.getCurrentPositionInSteps(stepper) == 0):
                return False
        return True

    def home(self):
        self._runner.start(self._home_plan())

    def back_to_home(self):
        self._runner.start(self._back_to_home_plan())

    def stop_balls(self):
        self._runner.start(self._stop_balls_plan())

    def scoop(self, num_left, num_right):
        self._runner.start(self._scoop_plan(num_left, num_right))

    def go_to(self, position, start):
        """Moves the arms from start to position. A start of None homes on the switches first."""
        self._runner.start(self._go_to_plan(position, start))

    def _set_rates(self, speed, acceleration=None):
        for board, stepper, _ in self.axes:
            board.setSpeedInStepsPerSecond(stepper, speed)
            if acceleration is not None:
                board.setAccelerationInStepsPerSecondPerSecond(stepper, acceleration)

    def _zero_counters(self):
        for board, stepper, _ in self.axes:
            board.setCurrentPositionInSteps(stepper, 0)

    def _arm_offsets(self):
        tuning = self.tuning
        return ((self.right, tuning.offset_right, tuning.offset_v_right),
                (self.left, tuning.offset_left, tuning.offset_v_left))

    def _home_plan(self):
        # The driver's three passes, on all four axes at once: fast onto the switch, off it,
        # then slowly back on so every axis zeroes at the same edge.
        toward = TOWARD_HOME * HOME_MAX_STEPS
        axes = self.axes
        return [
            Step(Do(lambda: self._set_rates(HOME_SPEED_STEPS_PER_S, HOME_SPEED_STEPS_PER_S))),
            Step(*(SeekSwitch(axis, True, toward) for axis in axes), timeout=_seek_timeout(HOME_SPEED_STEPS_PER_S)),
            Step(Settle(HOME_SETTLE_S)),
            Step(*(SeekSwitch(axis, False, -toward) for axis in axes), timeout=_seek_timeout(HOME_SPEED_STEPS_PER_S)),
            Step(Do(lambda: self._set_rates(HOME_SLOW_SPEED_STEPS_PER_S))),
            Step(*(SeekSwitch(axis, True, toward) for axis in axes),
                 timeout=_seek_timeout(HOME_SLOW_SPEED_STEPS_PER_S)),
            Step(Settle(HOME_SETTLE_S)),
            Step(Do(self._zero_counters),
                 Do(lambda: self._set_rates(mm_to_steps(SPEED_MM_PER_S), mm_to_steps(ACCEL_MM_PER_S2)))),
        ]

    def _axis(self, board, role):
        stepper = self.stepper(board, role)
        return next(axis for axis in self.axes if axis.board is board and axis.stepper == stepper)

    def _move(self, role, targets_mm):
        return Step(*(MoveTo(self._axis(board, role), mm_to_steps(mm)) for board, mm in targets_mm))

    def _back_to_home_plan(self):
        # Verticals first so the scoopers can't hit the cradle on the way back.
        return [self._move(VERTICAL, [(board, 0) for board in self.boards]),
                self._move(HORIZONTAL, [(board, 0) for board in self.boards])]

    def _lift(self):
        return self._move(VERTICAL, [(board, LIFT_DISTANCE + offset_v) for board, _, offset_v in self._arm_offsets()])

    def _stop_points(self):
        tuning = self.tuning
        return [(self.right, DISTANCE_TO_FIRST_BALL + tuning.offset_right + tuning.stop_offset_right),
                (self.left, DISTANCE_TO_FIRST_BALL + tuning.offset_left + tuning.stop_offset_left)]

    def _stop_balls_plan(self):
        stops = self._stop_points()
        return [*self._back_to_home_plan(), self._lift(), self._move(HORIZONTAL, stops),
                Step(Settle(STOP_BALLS_HOLD_S)),
                self._move(HORIZONTAL, [(board, mm - STOP_BALLS_BACK_OFF) for board, mm in stops]),
                self._move(VERTICAL, [(board, 0) for board in self.boards])]

    def _back_off_where_held(self):
        # Trim edits don't move held arms, so back off from where they are rather than from the trims.
        back_off = mm_to_steps(STOP_BALLS_BACK_OFF)
        return Step(*(MoveTo(axis, axis.board.getCurrentPositionInSteps(axis.stepper) - back_off)
                      for axis in (self._axis(board, HORIZONTAL) for board in self.boards)))

    def _go_to_plan(self, position, start):
        climb = {Position.HOME: [],
                 Position.RAISED: [self._lift()],
                 Position.STOP: [self._lift(), self._move(HORIZONTAL, self._stop_points())]}
        if position is start:
            # A jog changed this position's trim, so only its last move needs sending again.
            return climb[position][-1:]
        if start is None:
            leave = self._home_plan()
        elif start is Position.STOP:
            leave = [self._back_off_where_held(), *self._back_to_home_plan()]
        else:
            leave = self._back_to_home_plan()
        return leave + climb[position]

    def _scoop_plan(self, num_left, num_right):
        if num_left < 0 or num_right < 0 or not 0 < num_left + num_right <= MAX_BALLS:
            raise ValueError("can't scoop %d left and %d right" % (num_left, num_right))
        right, left = self._arm_offsets()
        arms = [(board, count, offset, offset_v)
                for (board, offset, offset_v), count in ((right, num_right), (left, num_left)) if count]
        # An arm with nothing to scoop heads home while the other scoops, and must be clear of the
        # balls that swing out on its side before the drop.
        idle = [self._axis(board, HORIZONTAL)
                for (board, _, _), count in ((right, num_right), (left, num_left)) if not count]

        # With every ball taken the arms would collide moving together, so the right arm goes first.
        groups = [[arm] for arm in arms] if num_left + num_right == MAX_BALLS else [arms]
        plan = [Step(*(StartMove(axis, 0) for axis in idle))]
        for group in groups:
            plan += [
                self._move(HORIZONTAL, [(board, pickup_mm(count, offset)) for board, count, offset, _ in group]),
                self._move(VERTICAL, [(board, LIFT_DISTANCE + offset_v) for board, _, _, offset_v in group]),
                self._move(HORIZONTAL, [(board, RELEASE_DISTANCES[count] + offset) for board, count, offset, _ in group]),
            ]
        # Lowering both scoopers together drops the balls together.
        return plan + [Step(*(AwaitMove(axis, 0) for axis in idle)),
                       self._move(VERTICAL, [(board, 0) for board in self.boards]),
                       *self._back_to_home_plan()]
