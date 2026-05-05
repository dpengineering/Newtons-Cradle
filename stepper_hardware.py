#!/usr/bin/python3
import os
from time import sleep

from moveBothToHome import moveBothToHomeInSteps
from dpeaDPi.DPiStepper import *


GRAB_ONE = -225
GRAB_TWO = -190
GRAB_THREE = -190
GRAB_FOUR = -160

DISTANCE_TO_FIRST_BALL = 120
BALL_DIAMETER = 110
OFFSET_RIGHT = 9 # empirically determined by testing against DISTANCE_TO_FIRST_BALL until contact is made
OFFSET_LEFT = -4 

LIFT_DISTANCE = 50

AWAY_FROM_HOME = 1
BACK_TO_HOME = -1

dpiStepper0 = None
dpiStepper1 = None
speed_in_mm_per_sec = 400
accel_in_mm_per_sec_per_sec = 400


def init_hardware():
    """Initialize the DPiStepper boards and default motion settings."""
    global dpiStepper0, dpiStepper1

    dpiStepper0 = DPiStepper()
    dpiStepper1 = DPiStepper()

    dpiStepper0.setBoardNumber(0)
    dpiStepper1.setBoardNumber(1)

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


def speed_reset():
    for board in [dpiStepper0, dpiStepper1]:
        board.setSpeedInMillimetersPerSecond(0, speed_in_mm_per_sec)
        board.setSpeedInMillimetersPerSecond(1, speed_in_mm_per_sec)


def quit_all():
    home()
    dpiStepper1.enableMotors(False)
    dpiStepper0.enableMotors(False)
    os.system("clear")
    quit()


def admin_quit_all():
    home()
    dpiStepper1.enableMotors(False)
    dpiStepper0.enableMotors(False)
    os.system("clear")
    with open("exit_key.txt", "w") as file:
        file.write("aMbRcPdZeMfAgDhEiMjEkAlDmDnToHpIqSr:s(t")
        file.close()
    quit()


def are_horizontal_busy():
    _, right_h_stopped, _, _ = dpiStepper0.getStepperStatus(0)
    _, left_h_stopped, _, _ = dpiStepper1.getStepperStatus(0)
    return not (left_h_stopped and right_h_stopped)


def are_vertical_busy():
    _, right_v_stopped, _, _ = dpiStepper0.getStepperStatus(1)
    _, left_v_stopped, _, _ = dpiStepper1.getStepperStatus(1)
    return not (left_v_stopped and right_v_stopped)


def set_vertical_speed(speed_mm_per_sec):
    dpiStepper0.setSpeedInMillimetersPerSecond(1, speed_mm_per_sec)
    dpiStepper1.setSpeedInMillimetersPerSecond(1, speed_mm_per_sec)


def set_horizontal_speed(speed_mm_per_sec):
    dpiStepper0.setSpeedInMillimetersPerSecond(0, speed_mm_per_sec)
    dpiStepper1.setSpeedInMillimetersPerSecond(0, speed_mm_per_sec)


def set_vertical_pos(mm):
    dpiStepper0.moveToAbsolutePositionInMillimeters(1, mm, False)
    dpiStepper1.moveToAbsolutePositionInMillimeters(1, mm, True)


def set_vertical_pos_right(mm):
    dpiStepper0.moveToAbsolutePositionInMillimeters(1, mm, True)


def set_vertical_pos_left(mm):
    dpiStepper1.moveToAbsolutePositionInMillimeters(1, mm, True)


def set_horizontal_pos(mm):
    dpiStepper0.moveToAbsolutePositionInMillimeters(0, mm + OFFSET_RIGHT, False)
    dpiStepper1.moveToAbsolutePositionInMillimeters(0, mm + OFFSET_LEFT, True)
    

def set_horizontal_pos_right(mm):
    dpiStepper0.moveToAbsolutePositionInMillimeters(0, mm + OFFSET_RIGHT, True)


def set_horizontal_pos_left(mm):
    dpiStepper1.moveToAbsolutePositionInMillimeters(0, mm + OFFSET_LEFT, True)

def back_to_home():
    # Vertical first to avoid hitting the cradle on the way back
    dpiStepper0.moveToAbsolutePositionInSteps(1, 0, False)
    dpiStepper1.moveToAbsolutePositionInSteps(1, 0, True)

    dpiStepper0.moveToAbsolutePositionInSteps(0, 0, False)
    dpiStepper1.moveToAbsolutePositionInSteps(0, 0, True)


def home(board=0):
    microstepping = 8
    speed_steps_per_second = 200 * microstepping
    directionToMoveTowardHome = BACK_TO_HOME
    homeSpeedInStepsPerSecond = speed_steps_per_second * 2.5
    homeMaxDistanceToMoveInSteps = 28000
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
    homeMaxDistanceToMoveInSteps = 28000
    moveBothToHomeInSteps(dpiStepper0, directionToMoveTowardHome, homeSpeedInStepsPerSecond,
                          homeMaxDistanceToMoveInSteps, directionToMoveTowardHome,
                          homeSpeedInStepsPerSecond, homeMaxDistanceToMoveInSteps)

    moveBothToHomeInSteps(dpiStepper1, directionToMoveTowardHome, homeSpeedInStepsPerSecond,
                          homeMaxDistanceToMoveInSteps, directionToMoveTowardHome,
                          homeSpeedInStepsPerSecond, homeMaxDistanceToMoveInSteps)

    speed_reset()


def release_both():
    set_vertical_speed(200)
    set_vertical_pos(-1 * LIFT_DISTANCE)
    speed_reset()


def release_right():
    set_vertical_speed(200)
    set_vertical_pos_right(-1 * LIFT_DISTANCE)
    speed_reset()


def release_left():
    set_vertical_speed(200)
    set_vertical_pos_left(-1 * LIFT_DISTANCE)
    speed_reset()


# ============================== Scoop Functions ==============================
def scoop_both(num_left, num_right):
    if num_left > 5 or num_right > 5 or num_left < 0 or num_right < 0:
        print("Invalid number of balls to scoop. Must be between 0 and 5.")
        return
    if (num_left + num_right) > 5:
        print("Invalid combination of balls to scoop. Total cannot exceed 5.")
        return
    left_mm = DISTANCE_TO_FIRST_BALL + num_left * BALL_DIAMETER + OFFSET_LEFT
    right_mm = DISTANCE_TO_FIRST_BALL + num_right * BALL_DIAMETER + OFFSET_RIGHT

    #horizontal first 
    dpiStepper0.moveToAbsolutePositionInMillimeters(0, right_mm, False)
    dpiStepper1.moveToAbsolutePositionInMillimeters(0, left_mm, True)

    #then vertical
    dpiStepper0.moveToAbsolutePositionInMillimeters(1, LIFT_DISTANCE, False)
    dpiStepper1.moveToAbsolutePositionInMillimeters(1, LIFT_DISTANCE, True)

    #pull back
    dpiStepper0.moveToAbsolutePositionInMillimeters(0, DISTANCE_TO_FIRST_BALL, False)
    dpiStepper1.moveToAbsolutePositionInMillimeters(0, DISTANCE_TO_FIRST_BALL, True)

    #release
    dpiStepper0.moveToAbsolutePositionInMillimeters(1, 0, False)
    dpiStepper1.moveToAbsolutePositionInMillimeters(1, 0, True)

    back_to_home()

def stop_balls():
    set_vertical_pos(LIFT_DISTANCE)
    set_horizontal_pos(DISTANCE_TO_FIRST_BALL)
    set_vertical_pos(0)
