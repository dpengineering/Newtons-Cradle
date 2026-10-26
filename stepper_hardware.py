#!/usr/bin/python3
import subprocess
from time import sleep, time

from dpeaDPi.DPiStepper import *


RELEASE_ONE = 60
RELEASE_TWO = 150 # distance to release two balls without crashing into scooper on release
RELEASE_THREE = 300 
RELEASE_FOUR = 400
RELEASE_FIVE = 550
RELEASE_DISTANCES = [0, RELEASE_ONE, RELEASE_TWO, RELEASE_THREE, RELEASE_FOUR, RELEASE_FIVE]

DISTANCE_TO_FIRST_BALL = 120
BALL_DIAMETER = 110
OFFSET_RIGHT = 9 # empirically determined by testing against DISTANCE_TO_FIRST_BALL until contact is made
OFFSET_LEFT = -4
# Vertical lift trim per arm (mm added to LIFT_DISTANCE). 0 = no change.
OFFSET_V_RIGHT = 0
OFFSET_V_LEFT = 0

LIFT_DISTANCE = 50

AWAY_FROM_HOME = 1
BACK_TO_HOME = -1

dpiStepper0 = DPiStepper()
dpiStepper0.setBoardNumber(0)
dpiStepper1 = DPiStepper()
dpiStepper1.setBoardNumber(1)

speed_in_mm_per_sec = 200
accel_in_mm_per_sec_per_sec = 200


class HomingError(RuntimeError):
    pass


def set_offsets(offset_left=None, offset_right=None,
                offset_v_left=None, offset_v_right=None):
    # Bridge the admin-page tuning values (held as globals in main.py and
    # persisted to variables.json) into this module's offset constants, which
    # scoop()/set_horizontal_pos()/the lift moves actually read. Only non-None
    # values are applied, so a missing key leaves the current value untouched.
    global OFFSET_LEFT, OFFSET_RIGHT, OFFSET_V_LEFT, OFFSET_V_RIGHT
    if offset_left is not None:
        OFFSET_LEFT = offset_left
    if offset_right is not None:
        OFFSET_RIGHT = offset_right
    if offset_v_left is not None:
        OFFSET_V_LEFT = offset_v_left
    if offset_v_right is not None:
        OFFSET_V_RIGHT = offset_v_right


def init_hardware():
    """Initialize the DPiStepper boards and default motion settings."""
    dpiStepper0.initialize()
    sleep(1)
    dpiStepper1.initialize()

    dpiStepper0.enableMotors(True)
    dpiStepper1.enableMotors(True)

    for board in [dpiStepper0, dpiStepper1]:
        board.setStepsPerMillimeter(0, 64)
        board.setStepsPerMillimeter(1, 64)
    motion_reset()

def disable_motors():
    dpiStepper0.enableMotors(False)
    dpiStepper1.enableMotors(False)

def enable_motors():
    dpiStepper0.enableMotors(True)
    dpiStepper1.enableMotors(True)


def motion_reset():
    # Homing leaves both speed and acceleration at the homing rate.
    for board in [dpiStepper0, dpiStepper1]:
        for stepperNum in (0, 1):
            board.setSpeedInMillimetersPerSecond(stepperNum, speed_in_mm_per_sec)
            board.setAccelerationInMillimetersPerSecondPerSecond(stepperNum, accel_in_mm_per_sec_per_sec)


def quit_all():
    double_home()
    disable_motors()
    quit()


def admin_quit_all():
    # Quits the app cleanly; the systemd service (Restart=always) brings it
    # back up. This is effectively a RESTART. (Previously wrote exit_key.txt to
    # signal Mother-Function.py to stop the supervisor loop, which no longer
    # exists.)
    double_home()
    disable_motors()
    quit()


def shutdown_service():
    # True quit: home, disable motors, then stop the systemd service so the app
    # does NOT auto-restart. Requires a sudoers rule allowing 'pi' to run
    # `systemctl stop newtons-cradle.service` without a password (see README).
    # systemd sends SIGTERM to this process as it stops the unit, which ends
    # the app.
    double_home()
    disable_motors()
    subprocess.Popen(["sudo", "systemctl", "stop", "newtons-cradle.service"])


def are_horizontal_busy():
    right_h_stopped = dpiStepper0.getStepperStatus(0).stopped
    left_h_stopped = dpiStepper1.getStepperStatus(0).stopped
    return not (left_h_stopped and right_h_stopped)


def are_vertical_busy():
    right_v_stopped = dpiStepper0.getStepperStatus(1).stopped
    left_v_stopped = dpiStepper1.getStepperStatus(1).stopped
    return not (left_v_stopped and right_v_stopped)


def _wait_while_busy(busy_fn, timeout=15.0):
    # Block until motion on both boards has stopped. Used to synchronize moves
    # that were fired non-blocking (waitToFinish=False) on both arms so they run
    # simultaneously. The initial sleep lets the controllers register the move
    # before we poll (otherwise the status can still read "stopped" and we'd
    # return instantly). The timeout guards against ever hanging if a motor
    # stalls or a status never clears.
    sleep(0.1)
    start = time()
    while busy_fn():
        if time() - start > timeout:
            raise TimeoutError("motion did not stop within %.0fs" % timeout)
        sleep(0.02)


def _move_together(stepperNum, targets):
    for board, mm in targets:
        board.moveToAbsolutePositionInMillimeters(stepperNum, mm, False)
    _wait_while_busy(are_horizontal_busy if stepperNum == 0 else are_vertical_busy)


def set_vertical_pos(mm):
    _move_together(1, [(dpiStepper0, mm), (dpiStepper1, mm)])


def set_horizontal_pos(mm):
    _move_together(0, [(dpiStepper0, mm + OFFSET_RIGHT), (dpiStepper1, mm + OFFSET_LEFT)])
    

def set_horizontal_pos_right(mm):
    dpiStepper0.moveToAbsolutePositionInMillimeters(0, mm + OFFSET_RIGHT, True)


def set_horizontal_pos_left(mm):
    dpiStepper1.moveToAbsolutePositionInMillimeters(0, mm + OFFSET_LEFT, True)

def back_to_home():
    # Both arms move together: fire each move non-blocking, then wait for both
    # to finish before continuing. Verticals first so the scoopers can't hit the
    # cradle on the way back, THEN horizontals. Waiting on both boards (rather
    # than relying on one board's blocking call) keeps motion synchronized and
    # complete no matter which arm moved. An arm already at 0 is an instant
    # no-op, so single-arm scoops see no extra delay.
    dpiStepper0.moveToAbsolutePositionInSteps(1, 0, False)
    dpiStepper1.moveToAbsolutePositionInSteps(1, 0, False)
    _wait_while_busy(are_vertical_busy)

    dpiStepper0.moveToAbsolutePositionInSteps(0, 0, False)
    dpiStepper1.moveToAbsolutePositionInSteps(0, 0, False)
    _wait_while_busy(are_horizontal_busy)


def home(board=0):
    microstepping = 8
    speed_steps_per_second = 200 * microstepping
    directionToMoveTowardHome = BACK_TO_HOME
    homeSpeedInStepsPerSecond = speed_steps_per_second * 2.5
    homeMaxDistanceToMoveInSteps = 50000
    dpiStepper = dpiStepper0 if board == 0 else dpiStepper1
    for stepperNum in (0, 1):
        if not dpiStepper.moveToHomeInSteps(stepperNum, directionToMoveTowardHome, homeSpeedInStepsPerSecond,
                                            homeMaxDistanceToMoveInSteps):
            raise HomingError("homing failed on board %d stepper %d" % (board, stepperNum))
    motion_reset()


def double_home():
    microstepping = 8
    speed_steps_per_second = 200 * microstepping
    directionToMoveTowardHome = BACK_TO_HOME
    homeSpeedInStepsPerSecond = speed_steps_per_second * 2.5
    homeMaxDistanceToMoveInSteps = 50000
    for board, dpiStepper in enumerate([dpiStepper0, dpiStepper1]):
        if not dpiStepper.moveBothToHomeInSteps(board, 0, directionToMoveTowardHome, homeSpeedInStepsPerSecond,
                                                homeMaxDistanceToMoveInSteps, 1, directionToMoveTowardHome,
                                                homeSpeedInStepsPerSecond, homeMaxDistanceToMoveInSteps):
            raise HomingError("homing failed on board %d" % board)
        # Unlike moveToHomeInSteps, the driver's dual homing leaves the counters where they were.
        dpiStepper.setCurrentPositionInSteps(0, 0)
        dpiStepper.setCurrentPositionInSteps(1, 0)

    motion_reset()


def _axis_is_home(board, stepperNum):
    status = board.getStepperStatus(stepperNum)
    return status.stopped and status.at_home and board.getCurrentPositionInSteps(stepperNum) == 0


def is_home():
    return all(_axis_is_home(board, stepperNum) for board in (dpiStepper0, dpiStepper1) for stepperNum in (0, 1))


def verify_home():
    # Homing zeroes each counter where its switch closes, so an arm at 0 on a closed
    # switch hasn't lost steps and homing it again would only cost time.
    if not is_home():
        double_home()


# ============================== Scoop Functions ==============================
def scoop(num_left, num_right):
    if num_left < 0 or num_right < 0:
        print("Number of balls to scoop must be positive.")
        return
    if (num_left + num_right) > 5:
        print("Invalid combination of balls to scoop. Total cannot exceed 5.")
        return
    if (num_left == 0 and num_right == 0):
        print("No balls to scoop.")
        return
    left_mm = DISTANCE_TO_FIRST_BALL + num_left * BALL_DIAMETER + OFFSET_LEFT
    right_mm = DISTANCE_TO_FIRST_BALL + num_right * BALL_DIAMETER + OFFSET_RIGHT
    # Per-arm lift height, trimmed by the vertical offsets.
    right_lift = LIFT_DISTANCE + OFFSET_V_RIGHT
    left_lift = LIFT_DISTANCE + OFFSET_V_LEFT

    arms = []
    if num_right:
        arms.append((dpiStepper0, right_mm, right_lift, RELEASE_DISTANCES[num_right]))
    if num_left:
        arms.append((dpiStepper1, left_mm, left_lift, RELEASE_DISTANCES[num_left]))

    # With all 5 balls the arms would collide moving together, so the right arm goes first.
    groups = [[arm] for arm in arms] if (num_left + num_right) == 5 else [arms]
    for group in groups:
        _move_together(0, [(board, reach) for board, reach, _, _ in group])
        _move_together(1, [(board, lift) for board, _, lift, _ in group])
        _move_together(0, [(board, release) for board, _, _, release in group])

    # release: lower both scoopers to 0 at the SAME TIME so the balls drop
    # together (an idle arm is already at 0, so it just returns instantly).
    set_vertical_pos(0)

    back_to_home()
    verify_home()

def stop_balls(end_at_home=True):
    set_vertical_pos(0)
    back_to_home()
    set_vertical_pos(LIFT_DISTANCE)
    set_horizontal_pos(DISTANCE_TO_FIRST_BALL)
    set_vertical_pos(0)
    
    if end_at_home:
        back_to_home()
