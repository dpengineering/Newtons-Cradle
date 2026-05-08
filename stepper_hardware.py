#!/usr/bin/python3
from time import sleep

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

LIFT_DISTANCE = 50

AWAY_FROM_HOME = 1
BACK_TO_HOME = -1

dpiStepper0 = DPiStepper()
dpiStepper0.setBoardNumber(0)
dpiStepper1 = DPiStepper()
dpiStepper1.setBoardNumber(1)

speed_in_mm_per_sec = 200
accel_in_mm_per_sec_per_sec = 200


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


def speed_reset():
    for board in [dpiStepper0, dpiStepper1]:
        board.setSpeedInMillimetersPerSecond(0, speed_in_mm_per_sec)
        board.setSpeedInMillimetersPerSecond(1, speed_in_mm_per_sec)


def quit_all():
    home()
    dpiStepper1.enableMotors(False)
    dpiStepper0.enableMotors(False)
    quit()


def admin_quit_all():
    home()
    dpiStepper1.enableMotors(False)
    dpiStepper0.enableMotors(False)
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

    # if all 5 balls are being scooped, we need to stagger stepper movement to avoid collision
    need_to_wait = (num_left + num_right) == 5

    if(need_to_wait):
        #first right, then left
        if(num_right):
            dpiStepper0.moveToAbsolutePositionInMillimeters(0, right_mm, True) #to ball
            dpiStepper0.moveToAbsolutePositionInMillimeters(1, LIFT_DISTANCE, True) #lift
            dpiStepper0.moveToAbsolutePositionInMillimeters(0, RELEASE_DISTANCES[num_right], False) #get in release position

        if(num_left):
            dpiStepper1.moveToAbsolutePositionInMillimeters(0, left_mm, True)
            dpiStepper1.moveToAbsolutePositionInMillimeters(1, LIFT_DISTANCE, True)
            dpiStepper1.moveToAbsolutePositionInMillimeters(0, RELEASE_DISTANCES[num_left], True)
    else:
        if(num_right and num_left):
            dpiStepper0.moveToAbsolutePositionInMillimeters(0, right_mm, False) #to ball same time
            dpiStepper1.moveToAbsolutePositionInMillimeters(0, left_mm, True) 

            dpiStepper0.moveToAbsolutePositionInMillimeters(1, LIFT_DISTANCE, False) #lift same time
            dpiStepper1.moveToAbsolutePositionInMillimeters(1, LIFT_DISTANCE, True)

            dpiStepper0.moveToAbsolutePositionInMillimeters(0, RELEASE_DISTANCES[num_right], False) #get in release position same time
            dpiStepper1.moveToAbsolutePositionInMillimeters(0, RELEASE_DISTANCES[num_left], True)
        elif(num_right):
            dpiStepper0.moveToAbsolutePositionInMillimeters(0, right_mm, True) #to ball
            dpiStepper0.moveToAbsolutePositionInMillimeters(1, LIFT_DISTANCE, True) #lift
            dpiStepper0.moveToAbsolutePositionInMillimeters(0, RELEASE_DISTANCES[num_right], True) #get in release position
        elif(num_left):
            dpiStepper1.moveToAbsolutePositionInMillimeters(0, left_mm, True)
            dpiStepper1.moveToAbsolutePositionInMillimeters(1, LIFT_DISTANCE, True)
            dpiStepper1.moveToAbsolutePositionInMillimeters(0, RELEASE_DISTANCES[num_left], True)


    #release
    dpiStepper0.moveToAbsolutePositionInMillimeters(1, 0, False)
    dpiStepper1.moveToAbsolutePositionInMillimeters(1, 0, True)

    back_to_home()

def stop_balls(end_at_home=True):
    set_vertical_pos(0)
    back_to_home()
    set_vertical_pos(LIFT_DISTANCE)
    set_horizontal_pos(DISTANCE_TO_FIRST_BALL)
    set_vertical_pos(0)
    
    if end_at_home:
        back_to_home()
