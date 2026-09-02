#!/usr/bin/python3
import time
import os
os.environ["KIVY_NO_CONSOLELOG"] = "1" #Disables log in messaging on the console when booting up the project

import json
import logging
from kivy.app import App
from kivy.lang import Builder
from Kivy.Scenes import AdminScreen
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
try:
    from pidev.kivy import DPEAButton
    from pidev.kivy import PauseScreen
    from pidev.MixPanel import MixPanel
except ImportError:
    DPEAButton = Button

    class PauseScreen(Widget):
        pass

    class MixPanel:
        def __init__(self, *args, **kwargs):
            pass

from stepper_hardware import *
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

YELLOW = .180, 0.188, 0.980, 1
BLUE = 0.917, 0.796, 0.380, 1
AWAY_FROM_HOME = 1
BACK_TO_HOME = -1

COOLDOWN_SECS = 10 # Time to wait in between starting scoops, originally 40

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

    if main.is_paused:
        return
    else:
        main.pause()

    def run_scoop_sequence(*args):
        try:
            enable_motors()
            
            def step1(dt):
                main.wait.text = "Homing..."
                Clock.schedule_once(step2, 1)
            
            def step2(dt):
                double_home()
                main.wait.text = "Resetting..."
                Clock.schedule_once(step3, 1)
            
            def step3(dt):
                stop_balls(num_left == 0 or num_right == 0)
                main.wait.text = "Scooping..."
                Clock.schedule_once(step4, 1)
            
            def step4(dt):
                scoop(num_left, num_right)
                main.wait.text = "Enjoying..."
                Clock.schedule_once(step5, 1)
            
            def step5(dt):
                disable_motors()
                Clock.schedule_once(lambda dt: main.unpause(), COOLDOWN_SECS)
            
            Clock.schedule_once(step1, 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: main.unpause(), COOLDOWN_SECS)
            raise

    Clock.schedule_once(run_scoop_sequence, 1) #wait a second to allow the wait widget to finish updating before starting the scoop sequence


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

    def pause(self):
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
        # "Restart": quits the app; the systemd service restarts it.
        admin_quit_all()

    @staticmethod
    def shutdown_action():
        # "Quit": truly stops the exhibit via `systemctl stop` (no restart).
        shutdown_service()

    @staticmethod
    def back_action():
        double_home()
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
        init_hardware()
        double_home()
        disable_motors()
        MyApp().run()
    except KeyboardInterrupt:
        quit_all()


