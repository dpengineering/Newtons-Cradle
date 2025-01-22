#!/usr/bin/python3
import time
import os
os.environ["KIVY_NO_CONSOLELOG"] = "1" #Disables log in messaging on the console when booting up the project

import json
import logging
from kivy.app import App
from kivy.lang import Builder
from Kivy.Scenes import AdminScreen
from threading import Thread
from moveBothToHome import MoveBothToHomeInSteps
from kivy.core.window import Window
from kivy.properties import AliasProperty, ObjectProperty, NumericProperty
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import *
from kivy.uix.popup import Popup
from kivy.vector import Vector
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.slider import Slider
from kivy.uix.image import Image
from kivy.uix.behaviors import ButtonBehavior
from kivy.clock import Clock
from kivy.animation import Animation
from functools import partial
from kivy.config import Config
from kivy.core.window import Window
from pidev.kivy import DPEAButton
from pidev.kivy import PauseScreen
from pidev.MixPanel import MixPanel
from dpeaDPi.DPiStepper import *
from time import sleep
# from kivy.logger import Logger

#Logger.setLevel("DEBUG")
#logging.getLogger().setLevel(logging.DEBUG)

# os.environ["KIVY_LOG_LEVEL"] = "warning"
# Config.set("kivy", "log_level", "warning")
"""
Globals
"""
GESTURE_MIN_DELTA = 25
GESTURE_MAX_DELTA = 75

GRAB_ONE = -225
GRAB_TWO = -190
GRAB_THREE = -190
GRAB_FOUR = -160

DISTANCE_TO_FIRST_BALL = 120
BALL_DIAMETER = 110
OFFSET_RIGHT = 5
OFFSET_LEFT = 0

LIFT_DISTANCE = 50

YELLOW = .180, 0.188, 0.980, 1
BLUE = 0.917, 0.796, 0.380, 1
AWAY_FROM_HOME = 1
BACK_TO_HOME = -1

MAIN_SCREEN_NAME = 'main'

MIXPANEL_TOKEN = "02f0373e5a3d6354fbc9d41d6b3a002a"

"""
DECLARE APP CLASS AND SCREENMANAGER
LOAD KIVY FILE
"""


class MyApp(App):
    def build(self):
        """
        Called upon launching application
        :return: Screen Manager
        """
        return sm


Builder.load_file('Kivy/Scenes/main.kv')
Builder.load_file('Kivy/Libraries/DPEAButton.kv')
Builder.load_file('Kivy/Scenes/PauseScene.kv')
Builder.load_file('Kivy/Scenes/AdminScreen.kv')
Window.clearcolor = (.9, .9, .9, 1)  # (OFF WHITE)

"""
Hardware Setup
"""

dpiStepper0 = DPiStepper()
dpiStepper1 = DPiStepper()

dpiStepper0.setBoardNumber(0)
dpiStepper1.setBoardNumber(1)

if not dpiStepper1.initialize():
    print("Communication with the DPiStepper board 1 failed.")
sleep(1)
if not dpiStepper0.initialize():
    print("Communication with the DPiStepper board 0 failed.")

dpiStepper0.enableMotors(True)
dpiStepper1.enableMotors(True)

speed_in_mm_per_sec = 300
accel_in_mm_per_sec_per_sec = 300

"""
Initializing the speed, acceleration, and steps for each motor
"""
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

"""
Main functions
"""


def speed_reset():
    """Reset the speeds on each motor to original value"""
    dpiStepper0.setSpeedInMillimetersPerSecond(0, speed_in_mm_per_sec)
    dpiStepper0.setSpeedInMillimetersPerSecond(1, speed_in_mm_per_sec)
    dpiStepper1.setSpeedInMillimetersPerSecond(0, speed_in_mm_per_sec)
    dpiStepper1.setSpeedInMillimetersPerSecond(1, speed_in_mm_per_sec)


def quit_all():
    """Called upon exiting UI, frees all steppers"""
    home()
    dpiStepper1.enableMotors(False)
    dpiStepper0.enableMotors(False)
    # print("Exit")
    os.system("clear")
    quit()

def admin_quit_all():
    """Called upon exiting UI, frees all steppers"""
    home()
    dpiStepper1.enableMotors(False)
    dpiStepper0.enableMotors(False)
    os.system("clear")
    with open("exit_key.txt", "w") as file:
        file.write("aMbRcPdZeMfAgDhEiMjEkAlDmDnToHpIqSr:s(t")
        file.close()
        print("aMbRcPdZeMfAgDhEiMjEkAlDmDnToHpIqSr:s(t")
    quit()


def are_horizontal_busy():
    """
    Check to see if the horizontal steppers are busy
    :return: True if busy, False if not
    """
    b1, rhs, b3, b4 = dpiStepper0.getStepperStatus(0)
    g1, lhs, g3, g4 = dpiStepper1.getStepperStatus(0)
    if lhs and rhs is True:
        return False
    else:
        return True


def are_vertical_busy():
    """
    Check to see if the vertical steppers are busy
    :return: True if busy, False if not
    """
    b1, rhs, b3, b4 = dpiStepper0.getStepperStatus(1)
    g1, lhs, g3, g4 = dpiStepper1.getStepperStatus(1)
    if lhs and rhs is True:
        return False
    else:
        return True


def set_vertical_speed(speed_mm_per_sec):
    """
    Set the speed of the vertical steppers
    :param speed_mm_per_sec: Speed to set the vertical steppers as
    :return: None
    *initialized at 300*
    """
    dpiStepper1.setSpeedInMillimetersPerSecond(1, speed_mm_per_sec)
    dpiStepper0.setSpeedInMillimetersPerSecond(1, speed_mm_per_sec)


def set_horizontal_speed(speed_mm_per_sec):
    """
    Set the speed of the horizontal steppers
    :param speed_mm_per_sec: Speed to set the vertical steppers as
    :return: None
    *initialized at 300*
    """
    dpiStepper1.setSpeedInMillimetersPerSecond(0, speed_mm_per_sec)
    dpiStepper0.setSpeedInMillimetersPerSecond(0, speed_mm_per_sec)


def set_vertical_pos(millimeters):
    """
    Set the vertical position of the vertical steppers
    :param millimeters: The position of the vertical steppers
    :return: None
    """
    dpiStepper1.moveToRelativePositionInMillimeters(1, millimeters, False)
    dpiStepper0.moveToRelativePositionInMillimeters(1, millimeters, True)


def set_vertical_pos_right(millimeters):
    """
    Set the vertical position of the right vertical stepper
    :param millimeters: The position of the right vertical stepper
    :return: None
    """
    dpiStepper0.moveToRelativePositionInMillimeters(1, millimeters, True)


def set_vertical_pos_left(millimeters):
    """
    Set the vertical position of the left vertical stepper
    :param millimeters: The position of the left vertical stepper
    :return: None
    """
    dpiStepper1.moveToRelativePositionInMillimeters(1, millimeters, True)


def set_horizontal_pos(mm):
    """
    Set the horizontal position of the horizontal steppers
    :param mm: The position of the horizontal steppers
    :return: None
    """
    dpiStepper1.moveToRelativePositionInMillimeters(0, mm - 3, False)
    dpiStepper0.moveToRelativePositionInMillimeters(0, mm + 15, True)


def set_horizontal_pos_right(mm):
    """
    Set the horizontal position of the right horizontal stepper
    :param mm: The position of the right horizontal steppers
    :return: None
    """
    dpiStepper0.moveToRelativePositionInMillimeters(0, mm + 15, True)


def set_horizontal_pos_left(mm):
    """
    Set the horizontal position of the left horizontal stepper
    :param mm: The position of the left horizontal steppers
    :return: None
    """
    dpiStepper1.moveToRelativePositionInMillimeters(0, mm - 3, True)


def home():
    """
    Home all the steppers
    :return: None
    """
    microstepping = 8
    speed_steps_per_second = 200 * microstepping
    directionToMoveTowardHome = BACK_TO_HOME  # 1 Positive Direction -1 Negative Direction
    homeSpeedInStepsPerSecond = speed_steps_per_second * 2.5
    homeMaxDistanceToMoveInSteps = 28000
    dpiStepper1.moveToHomeInSteps(0, directionToMoveTowardHome, homeSpeedInStepsPerSecond,
                                  homeMaxDistanceToMoveInSteps)
    dpiStepper0.moveToHomeInSteps(0, directionToMoveTowardHome, homeSpeedInStepsPerSecond,
                                  homeMaxDistanceToMoveInSteps)
    dpiStepper1.moveToHomeInSteps(1, directionToMoveTowardHome, homeSpeedInStepsPerSecond,
                                  homeMaxDistanceToMoveInSteps)
    dpiStepper0.moveToHomeInSteps(1, directionToMoveTowardHome, homeSpeedInStepsPerSecond,
                                  homeMaxDistanceToMoveInSteps)
    speed_reset()

def double_Home() :
    microstepping = 8
    speed_steps_per_second = 200 * microstepping
    directionToMoveTowardHome = BACK_TO_HOME  # 1 Positive Direction -1 Negative Direction
    homeSpeedInStepsPerSecond = speed_steps_per_second * 2.5
    homeMaxDistanceToMoveInSteps = 28000
    MoveBothToHomeInSteps(0, 0, directionToMoveTowardHome, homeSpeedInStepsPerSecond,
                                  homeMaxDistanceToMoveInSteps, 1, directionToMoveTowardHome, homeSpeedInStepsPerSecond, homeMaxDistanceToMoveInSteps)

    MoveBothToHomeInSteps(1, 0, directionToMoveTowardHome, homeSpeedInStepsPerSecond,
                          homeMaxDistanceToMoveInSteps, 1, directionToMoveTowardHome, homeSpeedInStepsPerSecond,
                          homeMaxDistanceToMoveInSteps)

    speed_reset()


def new_scoop():
    """
    New scooped initiated, gets the number of balls on each side and calls the perspective function to control pickups
    Only at the conclusion of this function is the UI is able to resolve interactions
    :return: None
    """
    Window.close()
    MyApp.get_running_app().stop()
    os.system("clear")

    # DO NOT EDIT
    print("""





                                          .-------------------------------------------------------------------------------.
                                          |  ____    _                                 __        __          _   _     _  |
                                          | |  _ \  | |   ___    __ _   ___    ___     \ \      / /   __ _  (_) | |_  | | |
                                          | | |_) | | |  / _ \  / _` | / __|  / _ \     \ \ /\ / /   / _` | | | | __| | | |
                                          | |  __/  | | |  __/ | (_| | \__ \ |  __/      \ V  V /   | (_| | | | | |_  |_| |
                                          | |_|     |_|  \___|  \__,_| |___/  \___|       \_/\_/     \__,_| |_|  \__| (_) |
                                          |                                                                               |
                                          '-------------------------------------------------------------------------------'
                                          
                                                                                      
                                                          _________________
                                                         /                /|
                                                        /                / |
                                                       /________________/ /|
                                                    ###|      ____      |//|
                                                   #   |     /   /|     |/.|
                                                  #  __|___ /   /.|     |  |_______________
                                                 #  /      /   //||     |  /              /|                  ___
                                                #  /      /___// ||     | /              / |                 / \ \*
                                                # /______/!   || ||_____|/              /  |                /   \ \*
                                                #| . . .  !   || ||                    /  _________________/     \ \*
                                                #|  . .   !   || //      ________     /  /\________________  {   /  }
                                                /|   .    !   ||//~~~~~~/9  ####/    /  / / ______________  {   /  /
                                               / |        !   |'/      /9  ####/    /  / / /             / {   /  /
                                              / #\________!___|/      /9  ####/    /  / / /_____________/___  /  /
                                             / #     /_____\/        /9  ####/    /  / / /_  /\_____________\/  /
                                            / #                      ``^^^^^^    /   \ \ . ./ / ____________   /
                                           +=#==================================/     \ \ ./ / /.  .  .  \ /  /
                                           |#                                   |      \ \/ / /___________/  /
                                           #                                    |_______\__/________________/
                                           |                                    |               |  |  / /       
                                           |                                    |               |  | / /       
                                           |                                    |       ________|  |/ /________       
                                           |                                    |      /_______/    \_________/\       
                                           |                                    |     /        /  /           \ )       
                                           |                                    |    /OO^^^^^^/  / /^^^^^^^^^OO\)       
                                           |                                    |            /  / /        
                                           |                                    |           /  / /
                                           |                                    |          /___\/
                                           |                                    |           oo
                                           |____________________________________|
      
      
        """)

    num_left = sm.get_screen('main').cradle.num_left()
    num_right = sm.get_screen('main').cradle.num_right()
    stop_balls()

    if (num_left + num_right) == 5:
        scoopFiveBalls(num_left, num_right)
        release_both()
        home()
        sleep(1)
        sm.get_screen('main').unpause()
    else:
        if num_left == 0:
            scoop_right(num_right)

            while are_horizontal_busy():
                continue

            release_right()

        elif num_right == 0:
            scoop_left(num_left)

            while are_horizontal_busy():
                continue

            release_left()

        else:
            scoop_both(num_left, num_right)
            release_both()

        home()
        sleep(1)
        #sm.get_screen('main').unpause()
        quit_all()

def scoop_left(num):
    """
    Scoop the balls on the left, doesn't wait for the last move to complete
    :param num: Number of balls to scoop on the left
    :return: None
    """

    p = OFFSET_LEFT + DISTANCE_TO_FIRST_BALL + BALL_DIAMETER * num
    set_horizontal_speed(speed_in_mm_per_sec)
    dpiStepper1.moveToRelativePositionInMillimeters(0, p, True)

    while are_horizontal_busy():
        continue

    dpiStepper1.moveToRelativePositionInMillimeters(1, LIFT_DISTANCE, True)

    while are_vertical_busy():
        continue

    if num == 1:
        dpiStepper1.moveToRelativePositionInMillimeters(0, GRAB_ONE, True)
    elif num == 2:
        dpiStepper1.moveToRelativePositionInMillimeters(0, GRAB_TWO, True)
    elif num == 3:
        dpiStepper1.moveToRelativePositionInMillimeters(0, GRAB_THREE, True)
    else:
        dpiStepper1.moveToRelativePositionInMillimeters(0, GRAB_FOUR, True)


def scoop_right(num):
    """
    Scoop the balls on the right, doesn't wait for the last move to complete
    :param num: Number of balls to scoop on the right
    :return: None
    """

    p = OFFSET_RIGHT + DISTANCE_TO_FIRST_BALL + BALL_DIAMETER * num
    set_horizontal_speed(speed_in_mm_per_sec)
    dpiStepper0.moveToRelativePositionInMillimeters(0, p, True)

    while are_horizontal_busy():
        continue

    dpiStepper0.moveToRelativePositionInMillimeters(1, LIFT_DISTANCE, True)

    while are_vertical_busy():
        continue

    if num == 1:
        dpiStepper0.moveToRelativePositionInMillimeters(0, GRAB_ONE + OFFSET_RIGHT, True)
    elif num == 2:
        dpiStepper0.moveToRelativePositionInMillimeters(0, GRAB_TWO + OFFSET_RIGHT, True)
    elif num == 3:
        dpiStepper0.moveToRelativePositionInMillimeters(0, GRAB_THREE + OFFSET_RIGHT, True)
    else:
        dpiStepper0.moveToRelativePositionInMillimeters(0, GRAB_FOUR + OFFSET_RIGHT, True)


def scoopFiveBalls(num_left, num_right):
    """
    Scoop left side first, then right
    This is necessary to prevent a collision
    """
    p_r = DISTANCE_TO_FIRST_BALL + OFFSET_RIGHT + BALL_DIAMETER * num_right
    p_l = DISTANCE_TO_FIRST_BALL + BALL_DIAMETER * num_left

    set_horizontal_pos_left(p_l)

    set_vertical_pos_left(LIFT_DISTANCE)

    if num_left == 1:
        dpiStepper1.moveToRelativePositionInMillimeters(0, GRAB_ONE, False)
    elif num_left == 2:
        dpiStepper1.moveToRelativePositionInMillimeters(0, GRAB_TWO, False)
    elif num_left == 3:
        dpiStepper1.moveToRelativePositionInMillimeters(0, GRAB_THREE, False)
    else:
        dpiStepper1.moveToRelativePositionInMillimeters(0, GRAB_FOUR, False)

    set_horizontal_pos_right(p_r)

    set_vertical_pos_right(LIFT_DISTANCE)

    if num_right == 1:
        dpiStepper0.moveToRelativePositionInMillimeters(0, GRAB_ONE + OFFSET_RIGHT, True)
    elif num_right == 2:
        dpiStepper0.moveToRelativePositionInMillimeters(0, GRAB_TWO + OFFSET_RIGHT, True)
    elif num_right == 3:
        dpiStepper0.moveToRelativePositionInMillimeters(0, GRAB_THREE + OFFSET_RIGHT, True)
    else:
        dpiStepper0.moveToRelativePositionInMillimeters(0, GRAB_FOUR + OFFSET_RIGHT, True)


def scoop_both(num_left, num_right):
    """
    Scoop both sides
    :param num_left: Number of balls on the left side to be scooped
    :param num_right: Number of balls on the right side to be scooped
    :return: None
    """
    p_r = DISTANCE_TO_FIRST_BALL + OFFSET_RIGHT + BALL_DIAMETER * num_right
    p_l = DISTANCE_TO_FIRST_BALL + BALL_DIAMETER * num_left

    dpiStepper1.moveToRelativePositionInMillimeters(0, p_l, False)
    dpiStepper0.moveToRelativePositionInMillimeters(0, p_r, True)

    while are_horizontal_busy():
        continue

    set_vertical_pos(LIFT_DISTANCE)

    while are_vertical_busy():
        continue

    if num_left == 1:
        dpiStepper1.moveToRelativePositionInMillimeters(0, GRAB_ONE, False)
    elif num_left == 2:
        dpiStepper1.moveToRelativePositionInMillimeters(0, GRAB_TWO, False)
    elif num_left == 3:
        dpiStepper1.moveToRelativePositionInMillimeters(0, GRAB_THREE, False)
    else:
        dpiStepper1.moveToRelativePositionInMillimeters(0, GRAB_FOUR, False)

    if num_right == 1:
        dpiStepper0.moveToRelativePositionInMillimeters(0, GRAB_ONE + OFFSET_RIGHT, True)
    elif num_right == 2:
        dpiStepper0.moveToRelativePositionInMillimeters(0, GRAB_TWO + OFFSET_RIGHT, True)
    elif num_right == 3:
        dpiStepper0.moveToRelativePositionInMillimeters(0, GRAB_THREE + OFFSET_RIGHT, True)
    else:
        dpiStepper0.moveToRelativePositionInMillimeters(0, GRAB_FOUR + OFFSET_RIGHT, True)


def release_both():
    """
    Release both of the vertical steppers
    :return: None
    """
    set_vertical_speed(200)
    dpiStepper0.moveToRelativePositionInMillimeters(1, -1 * LIFT_DISTANCE, False)
    dpiStepper1.moveToRelativePositionInMillimeters(1, -1 * LIFT_DISTANCE, True)

    speed_reset()


def release_right():
    """
    Release the right vertical stepper
    :return: None
    """
    set_vertical_speed(200)
    dpiStepper0.moveToRelativePositionInMillimeters(1, -1 * LIFT_DISTANCE, True)

    speed_reset()


def release_left():
    """
    Release the left vertical stepper
    :return: None
    """
    set_vertical_speed(200)
    dpiStepper1.moveToRelativePositionInMillimeters(1, -1 * LIFT_DISTANCE, True)

    speed_reset()


def stop_balls():
    """
    Stop the balls movement, by bringing vert. steppers up and horiz. steppers in
    :return: None
    """
    # move vertical steppers up
    set_vertical_pos(60)
    sleep(1)

    # slowly move the horizontal steppers into the middle/stopping positions
    set_horizontal_pos(115)
    sleep(2)

    # slowly move away from balls
    set_horizontal_pos(-20)

    # reset all cradles
    double_Home()


"""
PauseScene functions
"""


def pause(text, sec):
    """
    Pause the screen for a set amount of time
    :param text: Text to display while the pause screen is visible
    :param sec: Number of seconds to pause the screen for
    :return: None
    """
    sm.transition.direction = 'left'
    sm.current = 'pauseScene'
    sm.current_screen.ids.pauseText.text = text
    load = Animation(size=(10, 10), duration=0) + \
           Animation(size=(150, 10), duration=sec)
    load.start(sm.current_screen.ids.progressBar)


def transition_back(original_scene):
    """
    Transition back to the previous scene
    :param original_scene: The previous scene to transition back to
    :return: None
    """
    sm.transition.direction = 'right'
    sm.current = original_scene


def scoop_balls_thread(*largs):
    main = sm.get_screen('main')

    num_left = main.cradle.num_left()
    num_right = main.cradle.num_right()

    if num_right == 0 and num_left == 0:
        return

    pause_time = 5  # N/A

    if main.is_paused:
        return
    main.pause(pause_time)

    # Thread(target=new_scoop).start()
    new_scoop()


sm = ScreenManager()


class MainScreen(Screen):
    cradle = ObjectProperty(None)
    execute = ObjectProperty(None)
    hint = ObjectProperty(None)
    progress = ObjectProperty(None)
    wait = ObjectProperty(None)

    is_paused = False

    fade_out = Animation(opacity=0, t="out_quad")
    fade_in = Animation(opacity=1, t="out_quad")

    @staticmethod
    def admin_action():
        sm.current = 'admin'

    # def close_application(self):
    #     # closing application
    #     # App.get_running_app().stop()
    #     MyApp.
    #     # removing window
    #     Window.close()

    def scoop_call_back(self):
        Clock.schedule_once(scoop_balls_thread, 0)

    def set_visible(self, widget):
        if self.is_paused:
            return

        Animation.cancel_all(self.hint)
        Animation.cancel_all(self.execute)
        # Animation.cancel_all(self.progress)
        Animation.cancel_all(self.wait)

        MainScreen.fade_out.start(self.hint)
        MainScreen.fade_out.start(self.execute)
        # MainScreen.fade_out.start(self.progress)
        MainScreen.fade_out.start(self.wait)

        Animation.cancel_all(widget)
        MainScreen.fade_in.start(widget)

    def pause(self, delay):
        Ball.interactive = False
        self.set_visible(self.wait)
        self.is_paused = True

    def unpause(self):
        Ball.interactive = True
        self.cradle.reset_balls()
        self.is_paused = False
        self.set_visible(self.hint)

    def update_button(self):
        l = self.cradle.num_left()
        r = self.cradle.num_right()

        if l == 0 and r == 0:
            self.set_visible(self.hint)
        else:
            self.set_visible(self.execute)


class Ball(Widget):
    interactive = True
    down_exists = False
    down = ObjectProperty((0, 0))

    def transform_point(self, v):
        v -= Vector(self.parent.pos)
        v = v.rotate(-self.parent.rotation)
        v += Vector(self.parent.pos)
        return v

    def clear(self):
        self.down = (0, 0)
        Ball.down_exists = False

    def pushed(self, touch):
        pos = touch.pos
        v = self.transform_point(Vector(pos))
        if self.collide_point(v.x, v.y) and (not Ball.down_exists) and Ball.interactive:
            self.down = v
            Ball.down_exists = True

    def moved(self, touch):
        p = self.parent
        pos = touch.pos
        v = self.transform_point(Vector(pos))

        if self.down != (0, 0):
            d = v - Vector(self.down)
            if d.length() >= GESTURE_MAX_DELTA:
                if d.x >= GESTURE_MIN_DELTA:
                    self.parent.parent.ball_right(p)
                    self.clear()
                elif d.x <= -GESTURE_MIN_DELTA:
                    self.parent.parent.ball_left(p)
                    self.clear()

    def released(self, touch):
        p = self.parent
        pos = touch.pos
        v = self.transform_point(Vector(pos))

        if self.down != (0, 0):
            d = v - Vector(self.down)
            if d.x >= GESTURE_MIN_DELTA:
                self.parent.parent.ball_right(p)
                self.clear()
                return
            elif d.x <= -GESTURE_MIN_DELTA:
                self.parent.parent.ball_left(p)
                self.clear()
            self.parent.parent.ball_touched(p)
            self.clear()


class BallString(Widget):
    rotation = ObjectProperty(0)
    ball = ObjectProperty(None)
    name = ObjectProperty("middle")
    ROT_LEFT = -35
    ROT_RIGHT = 35
    ROT_DOWN = 0
    a_down = Animation(rotation=ROT_DOWN, t="out_quad")
    a_left = Animation(rotation=ROT_LEFT, t="out_quad")
    a_right = Animation(rotation=ROT_RIGHT, t="out_quad")
    r = ObjectProperty(ROT_DOWN)

    def down(self):
        Animation.cancel_all(self)
        BallString.a_down.start(self)
        self.r = BallString.ROT_DOWN

    def left(self):
        Animation.cancel_all(self)
        BallString.a_left.start(self)
        self.r = BallString.ROT_LEFT

    def right(self):
        Animation.cancel_all(self)
        BallString.a_right.start(self)
        self.r = BallString.ROT_RIGHT


class Cradle(Widget):
    def num_left(self):
        return sum(ball.r == BallString.ROT_LEFT for ball in self.get_balls())

    def num_right(self):
        return sum(ball.r == BallString.ROT_RIGHT for ball in self.get_balls())

    def reset_balls(self):
        balls = self.get_balls()
        self.ball_down(balls[0])
        self.ball_down(balls[-1])

    def get_balls(self):
        return self.children

    def ball_right(self, ball_string):
        if ball_string.r == BallString.ROT_LEFT:
            self.ball_down(ball_string)
            return
        balls = self.get_balls()[::-1]
        i = balls.index(ball_string)
        for ball in balls[i:]:
            if ball.name == "left":
                ball.down()
            else:
                ball.right()
        sm.get_screen("main").update_button()

    def ball_left(self, ball_string):
        if ball_string.r == BallString.ROT_RIGHT:
            self.ball_down(ball_string)
            return
        balls = self.get_balls()
        i = balls.index(ball_string)
        for ball in balls[i:]:
            if ball.name == "right":
                ball.down()
            else:
                ball.left()
        sm.get_screen("main").update_button()

    def ball_down(self, ball_string):
        if ball_string.r == BallString.ROT_LEFT:
            balls = self.get_balls()[::-1]
            i = balls.index(ball_string)
            for ball in balls[i:]:
                if ball.r != BallString.ROT_LEFT:
                    break
                ball.down()
        elif ball_string.r == BallString.ROT_RIGHT:
            balls = self.get_balls()
            i = balls.index(ball_string)
            for ball in balls[i:]:
                if ball.r != BallString.ROT_RIGHT:
                    break
                ball.down()
        sm.get_screen("main").update_button()

    def ball_touched(self, ball_string):
        if ball_string.r == BallString.ROT_DOWN:
            if ball_string.name == "left":
                self.ball_left(ball_string)
            elif ball_string.name == "middle-left":
                self.ball_left(ball_string)
            elif ball_string.name == "middle":
                self.ball_right(ball_string)
            elif ball_string.name == "middle-right":
                self.ball_right(ball_string)
            elif ball_string.name == "right":
                self.ball_right(ball_string)
        else:
            self.ball_down(ball_string)
        sm.get_screen("main").update_button()


class MyProgressBar(Widget):
    value = NumericProperty(0)


variables_dict = {}
if os.path.exists("variables.json"):
    with open("variables.json") as o:
        variables_dict = json.loads(o.read())

    for v in variables_dict.keys():
        globals()[v] = variables_dict[v]


class VariableChanger(Widget):
    name = ObjectProperty(None)
    label = ObjectProperty(None)

    def get_value(self):
        return globals().get(self.name, None)

    def inc_value(self):
        self.set_value(self.get_value() + 1)

    def dec_value(self):
        self.set_value(self.get_value() - 1)

    def set_value(self, value):
        globals()[self.name] = value
        variables_dict[self.name] = value
        self.label.text = self.name + ": " + str(self.get_value())
        self.save_value()

    def save_value(self):
        with open("variables.json", "w+") as o:
            o.write(json.dumps(variables_dict))


class adminFunctionsScreen(Screen):
    @staticmethod
    def quit_action():
        admin_quit_all()

    @staticmethod
    def back_action():
        home()
        sm.current = 'main'


sm.add_widget(MainScreen(name='main'))
sm.add_widget(AdminScreen.AdminScreen(name='admin'))
sm.add_widget(adminFunctionsScreen(name='adminFunctionsScreen'))

mixpanel = MixPanel("Newtons Cradle", MIXPANEL_TOKEN)
# ////////////////////////////////////////////////////////////////
# //                          RUN APP                           //
# ////////////////////////////////////////////////////////////////
if __name__ == "__main__":
    try:
        home()
        MyApp().run()
    except KeyboardInterrupt:
        quit_all()


