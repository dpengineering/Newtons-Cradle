#!/usr/bin/python3
import subprocess
from time import sleep, time

from moveBothToHome import moveBothToHomeInSteps
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
    if not dpiStepper0.initialize():
        print("Communication with the DPiStepper board 0 failed.")
    sleep(1)
    if not dpiStepper1.initialize():
        print("Communication with the DPiStepper board 1     failed.")

    dpiStepper0.enableMotors(True)
    dpiStepper1.enableMotors(True)

    for board in [dpiStepper0, dpiStepper1]:
        board.setStepsPerMillimeter(0, 64)
        board.setStepsPerMillimeter(1, 64)
        board.setAccelerationInMillimetersPerSecondPerSecond(0, accel_in_mm_per_sec_per_sec)
        board.setAccelerationInMillimetersPerSecondPerSecond(1, accel_in_mm_per_sec_per_sec)
        board.setSpeedInMillimetersPerSecond(0, speed_in_mm_per_sec)
        board.setSpeedInMillimetersPerSecond(1, speed_in_mm_per_sec)

def disable_motors():
    dpiStepper0.enableMotors(False)
    dpiStepper1.enableMotors(False)

def enable_motors():
    dpiStepper0.enableMotors(True)
    dpiStepper1.enableMotors(True)


def speed_reset():
    for board in [dpiStepper0, dpiStepper1]:
        board.setSpeedInMillimetersPerSecond(0, speed_in_mm_per_sec)
        board.setSpeedInMillimetersPerSecond(1, speed_in_mm_per_sec)


def quit_all():
    home()
    disable_motors()
    quit()


def admin_quit_all():
    # Quits the app cleanly; the systemd service (Restart=always) brings it
    # back up. This is effectively a RESTART. (Previously wrote exit_key.txt to
    # signal Mother-Function.py to stop the supervisor loop, which no longer
    # exists.)
    home()
    disable_motors()
    quit()


def shutdown_service():
    # True quit: home, disable motors, then stop the systemd service so the app
    # does NOT auto-restart. Requires a sudoers rule allowing 'pi' to run
    # `systemctl stop newtons-cradle.service` without a password (see README).
    # systemd sends SIGTERM to this process as it stops the unit, which ends
    # the app.
    home()
    disable_motors()
    subprocess.Popen(["sudo", "systemctl", "stop", "newtons-cradle.service"])


def are_horizontal_busy():
    _, right_h_stopped, _, _ = dpiStepper0.getStepperStatus(0)
    _, left_h_stopped, _, _ = dpiStepper1.getStepperStatus(0)
    return not (left_h_stopped and right_h_stopped)


def are_vertical_busy():
    _, right_v_stopped, _, _ = dpiStepper0.getStepperStatus(1)
    _, left_v_stopped, _, _ = dpiStepper1.getStepperStatus(1)
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
            print("Warning: motion did not stop within %.0fs timeout." % timeout)
            break
        sleep(0.02)


def set_vertical_pos(mm):
    dpiStepper0.moveToAbsolutePositionInMillimeters(1, mm, False) # right side
    dpiStepper1.moveToAbsolutePositionInMillimeters(1, mm, True) # left side


def set_horizontal_pos(mm):
    dpiStepper0.moveToAbsolutePositionInMillimeters(0, mm + OFFSET_RIGHT, False)
    dpiStepper1.moveToAbsolutePositionInMillimeters(0, mm + OFFSET_LEFT, True)
    

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
    if board == 0:
        dpiStepper0.moveToHomeInSteps(0, directionToMoveTowardHome, homeSpeedInStepsPerSecond,
                                      homeMaxDistanceToMoveInSteps)
        dpiStepper0.moveToHomeInSteps(1, directionToMoveTowardHome, homeSpeedInStepsPerSecond,
                                      homeMaxDistanceToMoveInSteps)
    else:
        dpiStepper1.moveToHomeInSteps(0, directionToMoveTowardHome, homeSpeedInStepsPerSecond,
                                      homeMaxDistanceToMoveInSteps)
        dpiStepper1.moveToHomeInSteps(1, directionToMoveTowardHome, homeSpeedInStepsPerSecond,
                                      homeMaxDistanceToMoveInSteps)
    speed_reset()


def double_home():
    microstepping = 8
    speed_steps_per_second = 200 * microstepping
    directionToMoveTowardHome = BACK_TO_HOME
    homeSpeedInStepsPerSecond = speed_steps_per_second * 2.5
    homeMaxDistanceToMoveInSteps = 50000
    moveBothToHomeInSteps(dpiStepper0, directionToMoveTowardHome, homeSpeedInStepsPerSecond,
                          homeMaxDistanceToMoveInSteps, directionToMoveTowardHome,
                          homeSpeedInStepsPerSecond, homeMaxDistanceToMoveInSteps)

    moveBothToHomeInSteps(dpiStepper1, directionToMoveTowardHome, homeSpeedInStepsPerSecond,
                          homeMaxDistanceToMoveInSteps, directionToMoveTowardHome,
                          homeSpeedInStepsPerSecond, homeMaxDistanceToMoveInSteps)

    speed_reset()



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

    # if all 5 balls are being scooped, we need to stagger stepper movement to avoid collision
    need_to_wait = (num_left + num_right) == 5

    if(need_to_wait):
        #first right, then left
        if(num_right):
            dpiStepper0.moveToAbsolutePositionInMillimeters(0, right_mm, True) #to ball
            dpiStepper0.moveToAbsolutePositionInMillimeters(1, right_lift, True) #lift
            dpiStepper0.moveToAbsolutePositionInMillimeters(0, RELEASE_DISTANCES[num_right], False) #get in release position

        if(num_left):
            dpiStepper1.moveToAbsolutePositionInMillimeters(0, left_mm, True)
            dpiStepper1.moveToAbsolutePositionInMillimeters(1, left_lift, True)
            dpiStepper1.moveToAbsolutePositionInMillimeters(0, RELEASE_DISTANCES[num_left], True)
    else:
        if(num_right and num_left):
            dpiStepper0.moveToAbsolutePositionInMillimeters(0, right_mm, False) #to ball same time
            dpiStepper1.moveToAbsolutePositionInMillimeters(0, left_mm, True) 

            dpiStepper0.moveToAbsolutePositionInMillimeters(1, right_lift, False) #lift same time
            dpiStepper1.moveToAbsolutePositionInMillimeters(1, left_lift, True)

            dpiStepper0.moveToAbsolutePositionInMillimeters(0, RELEASE_DISTANCES[num_right], False) #get in release position same time
            dpiStepper1.moveToAbsolutePositionInMillimeters(0, RELEASE_DISTANCES[num_left], True)
        elif(num_right):
            dpiStepper0.moveToAbsolutePositionInMillimeters(0, right_mm, True) #to ball
            dpiStepper0.moveToAbsolutePositionInMillimeters(1, right_lift, True) #lift
            dpiStepper0.moveToAbsolutePositionInMillimeters(0, RELEASE_DISTANCES[num_right], True) #get in release position
        elif(num_left):
            dpiStepper1.moveToAbsolutePositionInMillimeters(0, left_mm, True)
            dpiStepper1.moveToAbsolutePositionInMillimeters(1, left_lift, True)
            dpiStepper1.moveToAbsolutePositionInMillimeters(0, RELEASE_DISTANCES[num_left], True)


    # release: lower both scoopers to 0 at the SAME TIME so the balls drop
    # together. Fire both non-blocking, then wait for both to finish (an idle
    # arm is already at 0, so it just returns instantly).
    dpiStepper0.moveToAbsolutePositionInMillimeters(1, 0, False)
    dpiStepper1.moveToAbsolutePositionInMillimeters(1, 0, False)
    _wait_while_busy(are_vertical_busy)

    back_to_home()

def stop_balls(end_at_home=True):
    set_vertical_pos(0)
    back_to_home()
    set_vertical_pos(LIFT_DISTANCE)
    set_horizontal_pos(DISTANCE_TO_FIRST_BALL)
    set_vertical_pos(0)
    
    if end_at_home:
        back_to_home()
