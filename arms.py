from dpeaDPi import StepperDriver

from config import (
    ACCEL_MM_PER_S2,
    DISTANCE_TO_FIRST_BALL,
    HOME_MAX_STEPS,
    HOME_SETTLE_S,
    HOME_SLOW_SPEED_STEPS_PER_S,
    HOME_SPEED_STEPS_PER_S,
    LIFT_DISTANCE,
    MAX_BALLS,
    RELEASE_DISTANCES,
    SPEED_MM_PER_S,
    Tuning,
    mm_to_steps,
    pickup_mm,
)
from motion import Axis, Do, MotionRunner, MoveTo, SeekSwitch, Settle, Step

HORIZONTAL, VERTICAL = 0, 1
TOWARD_HOME = -1


def _seek_timeout(speed):
    return HOME_MAX_STEPS / speed + speed / HOME_SPEED_STEPS_PER_S + 1


class CradleArms:
    """The two scooper arms. Board 0 drives the right arm and board 1 the left, each with a
    horizontal (stepper 0) and vertical (stepper 1) axis homed toward negative steps.

    Every motion method starts a plan and returns at once. Call tick() until busy is False.
    """

    def __init__(self, right: StepperDriver, left: StepperDriver, tuning: Tuning, clock):
        self.right = right
        self.left = left
        self.tuning = tuning
        self._runner = MotionRunner(clock)
        self.axes = [Axis(board, stepper, "%s %s" % (side, direction))
                     for board, side in ((right, "right"), (left, "left"))
                     for stepper, direction in ((HORIZONTAL, "horizontal"), (VERTICAL, "vertical"))]

    @property
    def boards(self):
        return self.right, self.left

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

    def stop_balls(self, end_at_home):
        self._runner.start(self._stop_balls_plan(end_at_home))

    def scoop(self, num_left, num_right):
        self._runner.start(self._scoop_plan(num_left, num_right))

    def _set_rates(self, speed, acceleration=None):
        for board in self.boards:
            for stepper in (HORIZONTAL, VERTICAL):
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

    def _axis(self, board, stepper):
        return next(axis for axis in self.axes if axis.board is board and axis.stepper == stepper)

    def _move(self, stepper, targets_mm):
        return Step(*(MoveTo(self._axis(board, stepper), mm_to_steps(mm)) for board, mm in targets_mm))

    def _back_to_home_plan(self):
        # Verticals first so the scoopers can't hit the cradle on the way back.
        return [self._move(VERTICAL, [(board, 0) for board in self.boards]),
                self._move(HORIZONTAL, [(board, 0) for board in self.boards])]

    def _stop_balls_plan(self, end_at_home):
        arms = self._arm_offsets()
        plan = [*self._back_to_home_plan(),
                self._move(VERTICAL, [(board, LIFT_DISTANCE + offset_v) for board, _, offset_v in arms]),
                self._move(HORIZONTAL, [(board, DISTANCE_TO_FIRST_BALL + offset) for board, offset, _ in arms]),
                self._move(VERTICAL, [(board, 0) for board in self.boards])]
        if end_at_home:
            plan += self._back_to_home_plan()
        return plan

    def _scoop_plan(self, num_left, num_right):
        if num_left < 0 or num_right < 0 or not 0 < num_left + num_right <= MAX_BALLS:
            raise ValueError("can't scoop %d left and %d right" % (num_left, num_right))
        right, left = self._arm_offsets()
        arms = [(board, count, offset, offset_v)
                for (board, offset, offset_v), count in ((right, num_right), (left, num_left)) if count]

        # With every ball taken the arms would collide moving together, so the right arm goes first.
        groups = [[arm] for arm in arms] if num_left + num_right == MAX_BALLS else [arms]
        plan = []
        for group in groups:
            plan += [
                self._move(HORIZONTAL, [(board, pickup_mm(count, offset)) for board, count, offset, _ in group]),
                self._move(VERTICAL, [(board, LIFT_DISTANCE + offset_v) for board, _, _, offset_v in group]),
                self._move(HORIZONTAL, [(board, RELEASE_DISTANCES[count] + offset) for board, count, offset, _ in group]),
            ]
        # Lowering both scoopers together drops the balls together.
        return plan + [self._move(VERTICAL, [(board, 0) for board in self.boards]), *self._back_to_home_plan()]
