from enum import Enum, auto
from typing import NamedTuple

from arms import CradleArms


class Phase(Enum):
    STARTING = auto()
    READY = auto()
    PREPARING = auto()
    STOPPING_BALLS = auto()
    SCOOPING = auto()
    CHECKING_HOME = auto()
    COOLDOWN = auto()
    RETURNING = auto()
    SHUTTING_DOWN = auto()
    STOPPED = auto()


class Output(NamedTuple):
    label: str
    accepts_input: bool
    motors_on: bool


OUTPUTS = {
    Phase.STARTING: Output("Homing...", False, True),
    Phase.READY: Output("Tap or Swipe", True, False),
    Phase.PREPARING: Output("Homing...", False, True),
    Phase.STOPPING_BALLS: Output("Resetting...", False, True),
    Phase.SCOOPING: Output("Scooping...", False, True),
    Phase.CHECKING_HOME: Output("Enjoying...", False, True),
    Phase.COOLDOWN: Output("Enjoying...", False, False),
    Phase.RETURNING: Output("Homing...", False, True),
    Phase.SHUTTING_DOWN: Output("Homing...", False, True),
    Phase.STOPPED: Output("Please Wait", False, False),
}

# Where each phase goes once its arm motion has finished. COOLDOWN waits on the clock instead.
AFTER_MOTION = {
    Phase.STARTING: Phase.READY,
    Phase.PREPARING: Phase.STOPPING_BALLS,
    Phase.STOPPING_BALLS: Phase.SCOOPING,
    Phase.SCOOPING: Phase.CHECKING_HOME,
    Phase.CHECKING_HOME: Phase.COOLDOWN,
    Phase.RETURNING: Phase.READY,
    Phase.SHUTTING_DOWN: Phase.STOPPED,
}


class Exhibit:
    """The visitor-facing state machine. Its outputs depend only on the phase (see OUTPUTS);
    entering a phase starts that phase's arm motion, and tick() moves on when it finishes.

    Nothing here blocks. Call tick() every frame.
    """

    def __init__(self, arms: CradleArms, clock, on_phase=lambda phase: None):
        self.arms = arms
        self.on_phase = on_phase
        self._clock = clock
        self.phase = None
        self._motors_on = None
        self._selection = (0, 0)
        self._cooldown_ends = 0.0
        self._on_stopped = None

    def start(self):
        self.arms.initialize()
        self._enter(Phase.STARTING)

    def request_scoop(self, num_left, num_right):
        if self.phase is Phase.READY and num_left + num_right > 0:
            self._selection = (num_left, num_right)
            self._enter(Phase.PREPARING)

    def request_return(self):
        self.arms.abort()
        self._enter(Phase.RETURNING)

    def request_exit(self, on_stopped):
        self.arms.abort()
        self._on_stopped = on_stopped
        self._enter(Phase.SHUTTING_DOWN)

    def tick(self):
        try:
            self._tick()
        except BaseException:
            self.arms.enable_motors(False)
            raise

    def _tick(self):
        self.arms.tick()
        if self.arms.busy:
            return
        if self.phase is Phase.COOLDOWN:
            if self._clock() >= self._cooldown_ends:
                self._enter(Phase.READY)
        elif self.phase in AFTER_MOTION:
            self._enter(AFTER_MOTION[self.phase])

    def _enter(self, phase):
        self.phase = phase
        motors_on = OUTPUTS[phase].motors_on
        if motors_on != self._motors_on:
            self.arms.enable_motors(motors_on)
            self._motors_on = motors_on

        num_left, num_right = self._selection
        if phase in (Phase.STARTING, Phase.RETURNING, Phase.SHUTTING_DOWN):
            self.arms.home()
        elif phase in (Phase.PREPARING, Phase.CHECKING_HOME):
            if not self.arms.is_home():
                self.arms.home()
        elif phase is Phase.STOPPING_BALLS:
            self.arms.stop_balls(end_at_home=num_left == 0 or num_right == 0)
        elif phase is Phase.SCOOPING:
            self.arms.scoop(num_left, num_right)
        elif phase is Phase.COOLDOWN:
            self._cooldown_ends = self._clock() + self.arms.tuning.cooldown_secs
        elif phase is Phase.STOPPED:
            self._on_stopped()
        self.on_phase(phase)
