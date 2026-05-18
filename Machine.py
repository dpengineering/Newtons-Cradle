from time import sleep
# from DPIDigitalInWrapper import DPIDigitalInWrapper
from dpeaDPi.DPiStepper import DPiStepper
from dpeaDPi.DPiComputer import DPiComputer
from moveBothToHome import MoveBothToHomeInSteps
import threading

"""
Globals
"""
GESTURE_MIN_DELTA = 25
GESTURE_MAX_DELTA = 75

GRAB_ONE = -225
GRAB_TWO = -190
GRAB_THREE = -190
GRAB_FOUR = -160

RELEASE_ONE = 60
RELEASE_TWO = 150 # distance to release two balls without crashing into scooper on release
RELEASE_THREE = 300
RELEASE_FOUR = 400
RELEASE_FIVE = 550
RELEASE_DISTANCES = [0, RELEASE_ONE, RELEASE_TWO, RELEASE_THREE, RELEASE_FOUR, RELEASE_FIVE]


DISTANCE_TO_FIRST_BALL = 120
BALL_DIAMETER = 110
OFFSET_RIGHT = 4
OFFSET_LEFT = 0

LIFT_DISTANCE = 50

YELLOW = .180, 0.188, 0.980, 1
BLUE = 0.917, 0.796, 0.380, 1
AWAY_FROM_HOME = 1
BACK_TO_HOME = -1

MAIN_SCREEN_NAME = 'main'

MIXPANEL_TOKEN = "02f0373e5a3d6354fbc9d41d6b3a002a"

speed_in_mm_per_sec = 300
accel_in_mm_per_sec_per_sec = 300

class Machine:
    dpiStepper0 = DPiStepper()
    dpiStepper1 = DPiStepper()

    def __init__(self):
        self.dpiStepper0.setBoardNumber(0)
        self.dpiStepper1.setBoardNumber(1)

    """
    Hardware Setup/Shutdown
    """
    def startup(self):
        self.stepper_setup()
        self.double_Home()
        #self.stop_balls()

    def shutdown(self):
        #self.double_Home()
        self.dpiStepper0.enableMotors(False)
        self.dpiStepper1.enableMotors(False)

    def stepper_setup(self):
        if not self.dpiStepper1.initialize():
            print("Communication with the self.dpiStepper board 1 failed.")

        sleep(1)

        if not self.dpiStepper0.initialize():
            print("Communication with the self.dpiStepper board 0 failed.")

        self.dpiStepper0.enableMotors(True)
        self.dpiStepper1.enableMotors(True)

        """
        Initializing the speed, acceleration, and steps for each motor
        """
        self.dpiStepper0.setStepsPerMillimeter(0, 64)
        self.dpiStepper0.setStepsPerMillimeter(1, 64)
        self.dpiStepper1.setStepsPerMillimeter(0, 64)
        self.dpiStepper1.setStepsPerMillimeter(1, 64)

        self.dpiStepper0.setAccelerationInMillimetersPerSecondPerSecond(0, accel_in_mm_per_sec_per_sec)
        self.dpiStepper0.setAccelerationInMillimetersPerSecondPerSecond(1, accel_in_mm_per_sec_per_sec)
        self.dpiStepper1.setAccelerationInMillimetersPerSecondPerSecond(0, accel_in_mm_per_sec_per_sec)
        self.dpiStepper1.setAccelerationInMillimetersPerSecondPerSecond(1, accel_in_mm_per_sec_per_sec)

        self.dpiStepper0.setSpeedInMillimetersPerSecond(0, speed_in_mm_per_sec)
        self.dpiStepper0.setSpeedInMillimetersPerSecond(1, speed_in_mm_per_sec)
        self.dpiStepper1.setSpeedInMillimetersPerSecond(0, speed_in_mm_per_sec)
        self.dpiStepper1.setSpeedInMillimetersPerSecond(1, speed_in_mm_per_sec)

    """
    Main functions
    """

    def speed_reset(self):
        """Reset the speeds on each motor to original value"""
        self.dpiStepper0.setSpeedInMillimetersPerSecond(0, speed_in_mm_per_sec)
        self.dpiStepper0.setSpeedInMillimetersPerSecond(1, speed_in_mm_per_sec)
        self.dpiStepper1.setSpeedInMillimetersPerSecond(0, speed_in_mm_per_sec)
        self.dpiStepper1.setSpeedInMillimetersPerSecond(1, speed_in_mm_per_sec)

    def quit_all(self):
        """Called upon exiting UI, frees all steppers"""
        self.home()
        self.dpiStepper1.enableMotors(False)
        self.dpiStepper0.enableMotors(False)
        quit()

    def admin_quit_all(self):
        """Called upon exiting UI, frees all steppers"""
        self.home()
        self.dpiStepper1.enableMotors(False)
        self.dpiStepper0.enableMotors(False)
        with open("exit_key.txt", "w") as file:
            file.write("aMbRcPdZeMfAgDhEiMjEkAlDmDnToHpIqSr:s(t")
            file.close()
        quit()

    def are_horizontal_busy(self):
        """
        Check to see if the horizontal steppers are busy
        :return: True if busy, False if not
        """
        b1, rhs, b3, b4 = self.dpiStepper0.getStepperStatus(0)
        g1, lhs, g3, g4 = self.dpiStepper1.getStepperStatus(0)
        if lhs and rhs is True:
            return False
        else:
            return True

    def are_vertical_busy(self):
        """
        Check to see if the vertical steppers are busy
        :return: True if busy, False if not
        """
        b1, rhs, b3, b4 = self.dpiStepper0.getStepperStatus(1)
        g1, lhs, g3, g4 = self.dpiStepper1.getStepperStatus(1)
        if lhs and rhs is True:
            return False
        else:
            return True

    def set_vertical_speed(self, speed_mm_per_sec):
        """
        Set the speed of the vertical steppers
        :param speed_mm_per_sec: Speed to set the vertical steppers as
        :return: None
        *initialized at 300*
        """
        self.dpiStepper1.setSpeedInMillimetersPerSecond(1, speed_mm_per_sec)
        self.dpiStepper0.setSpeedInMillimetersPerSecond(1, speed_mm_per_sec)

    def set_horizontal_speed(self, speed_mm_per_sec):
        """
        Set the speed of the horizontal steppers
        :param speed_mm_per_sec: Speed to set the vertical steppers as
        :return: None
        *initialized at 300*
        """
        self.dpiStepper1.setSpeedInMillimetersPerSecond(0, speed_mm_per_sec)
        self.dpiStepper0.setSpeedInMillimetersPerSecond(0, speed_mm_per_sec)

    def set_vertical_pos(self, millimeters):
        """
        Set the vertical position of the vertical steppers
        :param millimeters: The position of the vertical steppers
        :return: None
        """
        self.dpiStepper1.moveToRelativePositionInMillimeters(1, millimeters, False)
        self.dpiStepper0.moveToRelativePositionInMillimeters(1, millimeters, True)

    def set_vertical_pos_right(self, millimeters):
        """
        Set the vertical position of the right vertical stepper
        :param millimeters: The position of the right vertical stepper
        :return: None
        """
        self.dpiStepper0.moveToRelativePositionInMillimeters(1, millimeters, True)

    def set_vertical_pos_left(self, millimeters):
        """
        Set the vertical position of the left vertical stepper
        :param millimeters: The position of the left vertical stepper
        :return: None
        """
        self.dpiStepper1.moveToRelativePositionInMillimeters(1, millimeters, True)

    def set_horizontal_pos(self, mm, left_offset=0, right_offset=0):
        """
        Set the horizontal position of the horizontal steppers
        :param mm: The position of the horizontal steppers
        :param left_offset: Any additional offset of the left horizontal steppers
        :param right_offset: Any additional offset of the right horizontal steppers
        :return: None
        """
        self.dpiStepper1.moveToRelativePositionInMillimeters(0, mm + left_offset, False)
        self.dpiStepper0.moveToRelativePositionInMillimeters(0, mm + right_offset, True)

    def set_absolute_horizontal_pos(self, mm, left_offset=0, right_offset=0):
        """
        Set the horizontal position of the horizontal steppers
        :param mm: The position of the horizontal steppers
        :param left_offset: Any additional offset of the left horizontal steppers
        :param right_offset: Any additional offset of the right horizontal steppers
        :return: None
        """
        self.dpiStepper1.moveToAbsolutePositionInMillimeters(0, mm + left_offset, False)
        self.dpiStepper0.moveToAbsolutePositionInMillimeters(0, mm + right_offset, True)

    def set_horizontal_pos_right(self, mm):
        """
        Set the horizontal position of the right horizontal stepper
        :param mm: The position of the right horizontal steppers
        :return: None
        """
        self.dpiStepper0.moveToRelativePositionInMillimeters(0, mm + 15, True)

    def set_horizontal_pos_left(self, mm):
        """
        Set the horizontal position of the left horizontal stepper
        :param mm: The position of the left horizontal steppers
        :return: None
        """
        self.dpiStepper1.moveToRelativePositionInMillimeters(0, mm - 3, True)

    def home(self):
        """
        Home all the steppers
        :return: None
        """
        microstepping = 8
        speed_steps_per_second = 200 * microstepping
        directionToMoveTowardHome = BACK_TO_HOME  # 1 Positive Direction -1 Negative Direction
        homeSpeedInStepsPerSecond = speed_steps_per_second * 2.5
        homeMaxDistanceToMoveInSteps = 28000
        self.dpiStepper1.moveToHomeInSteps(0, directionToMoveTowardHome, homeSpeedInStepsPerSecond,
                                      homeMaxDistanceToMoveInSteps)
        self.dpiStepper0.moveToHomeInSteps(0, directionToMoveTowardHome, homeSpeedInStepsPerSecond,
                                      homeMaxDistanceToMoveInSteps)
        self.dpiStepper1.moveToHomeInSteps(1, directionToMoveTowardHome, homeSpeedInStepsPerSecond,
                                      homeMaxDistanceToMoveInSteps)
        self.dpiStepper0.moveToHomeInSteps(1, directionToMoveTowardHome, homeSpeedInStepsPerSecond,
                                      homeMaxDistanceToMoveInSteps)
        self.speed_reset()

    def double_Home(self):
        microstepping = 8
        speed_steps_per_second = 200 * microstepping
        directionToMoveTowardHome = BACK_TO_HOME  # 1 Positive Direction -1 Negative Direction
        homeSpeedInStepsPerSecond = speed_steps_per_second * 2.5
        homeMaxDistanceToMoveInSteps = 28000

        MoveBothToHomeInSteps(0, 0, directionToMoveTowardHome, homeSpeedInStepsPerSecond,
                              homeMaxDistanceToMoveInSteps, 1, directionToMoveTowardHome, homeSpeedInStepsPerSecond,
                              homeMaxDistanceToMoveInSteps)

        MoveBothToHomeInSteps(1, 0, directionToMoveTowardHome, homeSpeedInStepsPerSecond,
                              homeMaxDistanceToMoveInSteps, 1, directionToMoveTowardHome, homeSpeedInStepsPerSecond,
                              homeMaxDistanceToMoveInSteps)

        self.dpiStepper0.setCurrentPositionInSteps(0, 0)
        self.dpiStepper0.setCurrentPositionInSteps(1, 0)
        self.dpiStepper1.setCurrentPositionInSteps(0, 0)
        self.dpiStepper0.setCurrentPositionInSteps(1, 0)

        self.speed_reset()

    def scoop_left(self, num):
        """
        Scoop the balls on the left, doesn't wait for the last move to complete
        :param num: Number of balls to scoop on the left
        :return: None
        """

        p = OFFSET_LEFT + DISTANCE_TO_FIRST_BALL + BALL_DIAMETER * num
        self.set_horizontal_speed(speed_in_mm_per_sec)
        self.dpiStepper1.moveToRelativePositionInMillimeters(0, p, True)

        while self.are_horizontal_busy():
            continue

        self.dpiStepper1.moveToRelativePositionInMillimeters(1, LIFT_DISTANCE, True)

        while self.are_vertical_busy():
            continue

        if num == 1:
            self.dpiStepper1.moveToRelativePositionInMillimeters(0, GRAB_ONE, True)
        elif num == 2:
            self.dpiStepper1.moveToRelativePositionInMillimeters(0, GRAB_TWO, True)
        elif num == 3:
            self.dpiStepper1.moveToRelativePositionInMillimeters(0, GRAB_THREE, True)
        else:
            self.dpiStepper1.moveToRelativePositionInMillimeters(0, GRAB_FOUR, True)

    def scoop_right(self, num):
        """
        Scoop the balls on the right, doesn't wait for the last move to complete
        :param num: Number of balls to scoop on the right
        :return: None
        """

        p = OFFSET_RIGHT + DISTANCE_TO_FIRST_BALL + BALL_DIAMETER * num
        self.set_horizontal_speed(speed_in_mm_per_sec)
        self.dpiStepper0.moveToRelativePositionInMillimeters(0, p, True)

        while self.are_horizontal_busy():
            continue

        self.dpiStepper0.moveToRelativePositionInMillimeters(1, LIFT_DISTANCE, True)

        while self.are_vertical_busy():
            continue

        if num == 1:
            self.dpiStepper0.moveToRelativePositionInMillimeters(0, GRAB_ONE + OFFSET_RIGHT, True)
        elif num == 2:
            self.dpiStepper0.moveToRelativePositionInMillimeters(0, GRAB_TWO + OFFSET_RIGHT, True)
        elif num == 3:
            self.dpiStepper0.moveToRelativePositionInMillimeters(0, GRAB_THREE + OFFSET_RIGHT, True)
        else:
            self.dpiStepper0.moveToRelativePositionInMillimeters(0, GRAB_FOUR + OFFSET_RIGHT, True)

    def scoopFiveBalls(self, num_left, num_right):
        """
        Scoop left side first, then right
        This is necessary to prevent a collision
        """
        p_r = DISTANCE_TO_FIRST_BALL + OFFSET_RIGHT + BALL_DIAMETER * num_right
        p_l = DISTANCE_TO_FIRST_BALL + BALL_DIAMETER * num_left

        self.set_horizontal_pos_left(p_l)

        sleep(5)

        self.set_vertical_pos_left(LIFT_DISTANCE)

        sleep(3)

        if num_left == 1:
            self.dpiStepper1.moveToRelativePositionInMillimeters(0, GRAB_ONE, True)
        elif num_left == 2:
            self.dpiStepper1.moveToRelativePositionInMillimeters(0, GRAB_TWO, True)
        elif num_left == 3:
            self.dpiStepper1.moveToRelativePositionInMillimeters(0, GRAB_THREE, True)
        else:
            self.dpiStepper1.moveToRelativePositionInMillimeters(0, GRAB_FOUR, True)

        self.set_horizontal_pos_right(p_r)

        sleep(5)

        self.set_vertical_pos_right(LIFT_DISTANCE)

        sleep(3)

        if num_right == 1:
            self.dpiStepper0.moveToRelativePositionInMillimeters(0, GRAB_ONE + OFFSET_RIGHT, True)
        elif num_right == 2:
            self.dpiStepper0.moveToRelativePositionInMillimeters(0, GRAB_TWO + OFFSET_RIGHT, True)
        elif num_right == 3:
            self.dpiStepper0.moveToRelativePositionInMillimeters(0, GRAB_THREE + OFFSET_RIGHT, True)
        else:
            self.dpiStepper0.moveToRelativePositionInMillimeters(0, GRAB_FOUR + OFFSET_RIGHT, True)

        sleep(5)




    def scoop_both(self, num_left, num_right):
        """
        Scoop both sides
        :param num_left: Number of balls on the left side to be scooped
        :param num_right: Number of balls on the right side to be scooped
        :return: None
        """
        p_r = DISTANCE_TO_FIRST_BALL + OFFSET_RIGHT + BALL_DIAMETER * num_right
        p_l = DISTANCE_TO_FIRST_BALL + BALL_DIAMETER * num_left

        self.dpiStepper1.moveToRelativePositionInMillimeters(0, p_l, False)
        self.dpiStepper0.moveToRelativePositionInMillimeters(0, p_r, True)

        while self.are_horizontal_busy():
            continue

        self.set_vertical_pos(LIFT_DISTANCE)

        while self.are_vertical_busy():
            continue

        if num_left == 1:
            self.dpiStepper1.moveToRelativePositionInMillimeters(0, GRAB_ONE, False)
        elif num_left == 2:
            self.dpiStepper1.moveToRelativePositionInMillimeters(0, GRAB_TWO, False)
        elif num_left == 3:
            self.dpiStepper1.moveToRelativePositionInMillimeters(0, GRAB_THREE, False)
        else:
            self.dpiStepper1.moveToRelativePositionInMillimeters(0, GRAB_FOUR, False)

        if num_right == 1:
            self.dpiStepper0.moveToRelativePositionInMillimeters(0, GRAB_ONE + OFFSET_RIGHT, True)
        elif num_right == 2:
            self.dpiStepper0.moveToRelativePositionInMillimeters(0, GRAB_TWO + OFFSET_RIGHT, True)
        elif num_right == 3:
            self.dpiStepper0.moveToRelativePositionInMillimeters(0, GRAB_THREE + OFFSET_RIGHT, True)
        else:
            self.dpiStepper0.moveToRelativePositionInMillimeters(0, GRAB_FOUR + OFFSET_RIGHT, True)

        sleep(3)

    def release_both(self):
        """
        Release both of the vertical steppers
        :return: None
        """
        self.set_vertical_speed(200)
        self.dpiStepper0.moveToRelativePositionInMillimeters(1, -1 * LIFT_DISTANCE, False)
        self.dpiStepper1.moveToRelativePositionInMillimeters(1, -1 * LIFT_DISTANCE, True)

        sleep(3)

        self.speed_reset()

    def release_right(self):
        """
        Release the right vertical stepper
        :return: None
        """
        self.set_vertical_speed(200)
        self.dpiStepper0.moveToRelativePositionInMillimeters(1, -1 * LIFT_DISTANCE, True)

        self.speed_reset()

    def release_left(self):
        """
        Release the left vertical stepper
        :return: None
        """
        self.set_vertical_speed(200)
        self.dpiStepper1.moveToRelativePositionInMillimeters(1, -1 * LIFT_DISTANCE, True)

        self.speed_reset()

    def stop_balls(self):
        """
        Stop the balls movement, by bringing vert. steppers up and horiz. steppers in
        :return: None
        """
        # move vertical steppers up
        self.set_vertical_pos(60)
        sleep(1)

        # slowly move the horizontal steppers into the middle/stopping positions
        self.set_horizontal_pos(125, -2, 3)
        sleep(3.5)

        # slowly move away from balls
        self.set_horizontal_pos(-20)

        self.set_vertical_pos(-60)
        sleep(0.9)

        self.set_absolute_horizontal_pos(0)
        sleep(2.5)

        #self.set_horizontal_pos(-95, 0, -20)
        # sleep(1)

        # reset all cradles
        #self.double_Home()

    def scoop_balls(self, left, right, dt=None, *largs):
        num_left = left
        num_right = right

        if num_right <= 0 and num_left <= 0:
            print(num_left, num_right)
            return

        self.stop_balls()

        if (num_left + num_right) == 5:
            self.scoopFiveBalls(num_left, num_right)
            self.release_both()
        else:
            if num_left == 0:
                self.scoop_right(num_right)

                while self.are_horizontal_busy():
                    continue

                self.release_right()

            elif num_right == 0:
                self.scoop_left(num_left)

                while self.are_horizontal_busy():
                    continue

                self.release_left()

            else:
                self.scoop_both(num_left, num_right)
                self.release_both()

        self.set_absolute_horizontal_pos(0)
        self.double_Home()

    def scoop(self, num_left, num_right):
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

        if (need_to_wait):
            # first right, then left
            if (num_right):
                self.dpiStepper0.moveToAbsolutePositionInMillimeters(0, right_mm, True)  # to ball
                self.dpiStepper0.moveToAbsolutePositionInMillimeters(1, LIFT_DISTANCE, True)  # lift
                self.dpiStepper0.moveToAbsolutePositionInMillimeters(0, RELEASE_DISTANCES[num_right],
                                                                False)  # get in release position

            if (num_left):
                self.dpiStepper1.moveToAbsolutePositionInMillimeters(0, left_mm, True)
                self.dpiStepper1.moveToAbsolutePositionInMillimeters(1, LIFT_DISTANCE, True)
                self.dpiStepper1.moveToAbsolutePositionInMillimeters(0, RELEASE_DISTANCES[num_left], True)
        else:
            if (num_right and num_left):
                self.dpiStepper0.moveToAbsolutePositionInMillimeters(0, right_mm, False)  # to ball same time
                self.dpiStepper1.moveToAbsolutePositionInMillimeters(0, left_mm, True)

                self.dpiStepper0.moveToAbsolutePositionInMillimeters(1, LIFT_DISTANCE, False)  # lift same time
                self.dpiStepper1.moveToAbsolutePositionInMillimeters(1, LIFT_DISTANCE, True)

                self.dpiStepper0.moveToAbsolutePositionInMillimeters(0, RELEASE_DISTANCES[num_right],
                                                                False)  # get in release position same time
                self.dpiStepper1.moveToAbsolutePositionInMillimeters(0, RELEASE_DISTANCES[num_left], True)
            elif (num_right):
                self.dpiStepper0.moveToAbsolutePositionInMillimeters(0, right_mm, True)  # to ball
                self.dpiStepper0.moveToAbsolutePositionInMillimeters(1, LIFT_DISTANCE, True)  # lift
                self.dpiStepper0.moveToAbsolutePositionInMillimeters(0, RELEASE_DISTANCES[num_right],
                                                                True)  # get in release position
            elif (num_left):
                self.dpiStepper1.moveToAbsolutePositionInMillimeters(0, left_mm, True)
                self.dpiStepper1.moveToAbsolutePositionInMillimeters(1, LIFT_DISTANCE, True)
                self.dpiStepper1.moveToAbsolutePositionInMillimeters(0, RELEASE_DISTANCES[num_left], True)

        # release
        self.dpiStepper0.moveToAbsolutePositionInMillimeters(1, 0, False)
        self.dpiStepper1.moveToAbsolutePositionInMillimeters(1, 0, True)

        self.set_absolute_horizontal_pos(0)
        self.double_Home()

if __name__ == "__main__": #run this file to test the machine setup on its own
    m = Machine()
    try:
        m.startup()
        m.scoop_balls(2, 3)
    finally:
        m.shutdown()
