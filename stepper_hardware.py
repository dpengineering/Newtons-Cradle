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
OFFSET_RIGHT = 5
OFFSET_LEFT = 0

LIFT_DISTANCE = 50

AWAY_FROM_HOME = 1
BACK_TO_HOME = -1

dpiStepper0 = None
dpiStepper1 = None
speed_in_mm_per_sec = 300
accel_in_mm_per_sec_per_sec = 300


def init_hardware():
    """Initialize the DPiStepper boards and default motion settings."""
    global dpiStepper0, dpiStepper1, speed_in_mm_per_sec, accel_in_mm_per_sec_per_sec

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

    speed_in_mm_per_sec = 300
    accel_in_mm_per_sec_per_sec = 300

    dpiStepper0.setStepsPerMillimeter(0, 64)
    dpiStepper0.setStepsPerMillimeter(1, 64)
    dpiStepper1.setStepsPerMillimeter(0, 64)
    dpiStepper1.setStepsPerMillimeter(1, 64)
    dpiStepper0.setAccelerationInMillimetersPerSecondPerSecond(0, accel_in_mm_per_sec_per_sec)
    dpiStepper0.setAccelerationInMillimetersPerSecondPerSecond(1, accel_in_mm_per_sec_per_sec)
    dpiStepper1.setAccelerationInMillimetersPerSecondPerSecond(0, accel_in_mm_per_sec_per_sec)
    dpiStepper1.setAccelerationInMillimetersPerSecondPerSecond(1, accel_in_mm_per_sec_per_sec)
    dpiStepper0.setSpeedInMillimetersPerSecond(0, speed_in_mm_per_sec)
    dpiStepper0.setSpeedInMillimetersPerSecond(1, speed_in_mm_per_sec)
    dpiStepper1.setSpeedInMillimetersPerSecond(0, speed_in_mm_per_sec)
    dpiStepper1.setSpeedInMillimetersPerSecond(1, speed_in_mm_per_sec)


def speed_reset():
    dpiStepper0.setSpeedInMillimetersPerSecond(0, speed_in_mm_per_sec)
    dpiStepper0.setSpeedInMillimetersPerSecond(1, speed_in_mm_per_sec)
    dpiStepper1.setSpeedInMillimetersPerSecond(0, speed_in_mm_per_sec)
    dpiStepper1.setSpeedInMillimetersPerSecond(1, speed_in_mm_per_sec)


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
    b1, rhs, b3, b4 = dpiStepper0.getStepperStatus(0)
    g1, lhs, g3, g4 = dpiStepper1.getStepperStatus(0)
    if lhs and rhs is True:
        return False
    return True


def are_vertical_busy():
    b1, rhs, b3, b4 = dpiStepper0.getStepperStatus(1)
    g1, lhs, g3, g4 = dpiStepper1.getStepperStatus(1)
    if lhs and rhs is True:
        return False
    return True


def set_vertical_speed(speed_mm_per_sec):
    dpiStepper1.setSpeedInMillimetersPerSecond(1, speed_mm_per_sec)
    dpiStepper0.setSpeedInMillimetersPerSecond(1, speed_mm_per_sec)


def set_horizontal_speed(speed_mm_per_sec):
    dpiStepper1.setSpeedInMillimetersPerSecond(0, speed_mm_per_sec)
    dpiStepper0.setSpeedInMillimetersPerSecond(0, speed_mm_per_sec)


def set_vertical_pos(millimeters):
    dpiStepper1.moveToRelativePositionInMillimeters(1, millimeters, False)
    dpiStepper0.moveToRelativePositionInMillimeters(1, millimeters, True)


def set_vertical_pos_right(millimeters):
    dpiStepper0.moveToRelativePositionInMillimeters(1, millimeters, True)


def set_vertical_pos_left(millimeters):
    dpiStepper1.moveToRelativePositionInMillimeters(1, millimeters, True)


def set_horizontal_pos(mm):
    dpiStepper1.moveToRelativePositionInMillimeters(0, mm - 3, False)
    dpiStepper0.moveToRelativePositionInMillimeters(0, mm + 15, True)


def set_horizontal_pos_right(mm):
    dpiStepper0.moveToRelativePositionInMillimeters(0, mm + 15, True)


def set_horizontal_pos_left(mm):
    dpiStepper1.moveToRelativePositionInMillimeters(0, mm - 3, True)


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


def double_Home():
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
    dpiStepper0.moveToRelativePositionInMillimeters(1, -1 * LIFT_DISTANCE, False)
    dpiStepper1.moveToRelativePositionInMillimeters(1, -1 * LIFT_DISTANCE, True)
    speed_reset()


def release_right():
    set_vertical_speed(200)
    dpiStepper0.moveToRelativePositionInMillimeters(1, -1 * LIFT_DISTANCE, True)
    speed_reset()


def release_left():
    set_vertical_speed(200)
    dpiStepper1.moveToRelativePositionInMillimeters(1, -1 * LIFT_DISTANCE, True)
    speed_reset()


def stop_balls():
    set_vertical_pos(60)
    sleep(1)
    set_horizontal_pos(115)
    sleep(2)
    set_horizontal_pos(-20)
    double_Home()
