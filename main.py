import os
# os.environ["KIVY_NO_CONSOLELOG"] = "1" #Disables log in messaging on the console when booting up the project

import json
import logging
from kivy.app import App
from kivy.lang import Builder
# from Kivy.Scenes import AdminScreen JUST DELETED FOR EASIER IMPORTING
import AdminScreen
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
from pidev.MixPanel import MixPanel
from time import sleep

from Machine import Machine
from loading_screen import LoadingScreen
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

COOLDOWN_SECS = 10 # Time to wait in between starting scoops, originally 40

LIFT_DISTANCE = 50

YELLOW = .180, 0.188, 0.980, 1
BLUE = 0.917, 0.796, 0.380, 1
AWAY_FROM_HOME = 1
BACK_TO_HOME = -1

MAIN_SCREEN_NAME = 'main'

MIXPANEL_TOKEN = "02f0373e5a3d6354fbc9d41d6b3a002a"

machine = Machine()
sm = ScreenManager()


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
            machine.enable_motors()

            def step1(dt):
                main.wait.text = "Homing..."
                Clock.schedule_once(step2, 1)

            def step2(dt):
                machine.double_home()
                main.wait.text = "Resetting..."
                Clock.schedule_once(step3, 1)

            def step3(dt):
                machine.stop_balls(num_left == 0 or num_right == 0)
                main.wait.text = "Scooping..."
                Clock.schedule_once(step4, 1)

            def step4(dt):
                machine.scoop(num_left, num_right)
                main.wait.text = "Enjoying..."
                Clock.schedule_once(step5, 1)

            def step5(dt):
                machine.disable_motors()
                Clock.schedule_once(lambda dt: main.unpause(), COOLDOWN_SECS)

            Clock.schedule_once(step1, 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: main.unpause(), COOLDOWN_SECS)
            raise

    Clock.schedule_once(run_scoop_sequence, 1)

"""
DECLARE APP CLASS AND SCREENMANAGER
LOAD KIVY FILE
"""

class NewtonsCradleGUI(App):
    def build(self):
        """
        Called upon launching application
        :return: Screen Manager
        """
        # Builder.load_file('Kivy/Scenes/main.kv')
        # Builder.load_file('Kivy/Libraries/DPEAButton.kv')
        # Builder.load_file('Kivy/Scenes/PauseScene.kv')
        # Builder.load_file('Kivy/Scenes/AdminScreen.kv')
        # Builder.load_file('Kivy/Scenes/loading_screen.kv')

        Builder.load_file('main.kv')
        Builder.load_file('DPEAButton.kv')
        Builder.load_file('PauseScene.kv')
        Builder.load_file('AdminScreen.kv')
        Builder.load_file('loading_screen.kv')

        sm.add_widget(MainScreen(name='main'))
        sm.add_widget(LoadingScreen(name='loading'))
        sm.add_widget(AdminScreen.AdminScreen(name='admin'))
        sm.add_widget(adminFunctionsScreen(name='adminFunctionsScreen'))

        return sm

Window.clearcolor = (.9, .9, .9, 1)  # (OFF WHITE)

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

    def get_right_scoop(self):
        right = self.cradle.num_right()
        return right

    def get_left_scoop(self):
        left = self.cradle.num_left()
        return left

    def scoop_call_back(self):
        #self.switch_to_loading_screen()
        self.pause()
        Clock.schedule_once(self.unpause, 11)

    def scoop_balls_thread(self, *largs):
        num_left = self.cradle.num_left()
        num_right = self.cradle.num_right()

        if num_right == 0 and num_left == 0:
            return

        if self.is_paused:
            return
        else:
            self.pause()

        def run_scoop_sequence(*args):
            try:
                machine.enable_motors()

                def step1(dt):
                    self.wait.text = "Homing..."
                    Clock.schedule_once(step2, 1)

                def step2(dt):
                    machine.double_Home()
                    self.wait.text = "Resetting..."
                    Clock.schedule_once(step3, 1)

                def step3(dt):
                    machine.stop_balls(num_left == 0 or num_right == 0)
                    self.wait.text = "Scooping..."
                    Clock.schedule_once(step4, 1)

                def step4(dt):
                    machine.scoop(num_left, num_right)
                    self.wait.text = "Enjoying..."
                    Clock.schedule_once(step5, 1)

                def step5(dt):
                    machine.disable_motors()
                    Clock.schedule_once(lambda dt: self.unpause(), COOLDOWN_SECS)

                Clock.schedule_once(step1, 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: self.unpause(), COOLDOWN_SECS)
                raise

        Clock.schedule_once(run_scoop_sequence, 1)

    def set_visible(self, widget):
        if self.is_paused:
            return

        Animation.cancel_all(self.hint)
        Animation.cancel_all(self.execute)
        Animation.cancel_all(self.progress)
        Animation.cancel_all(self.wait)

        MainScreen.fade_out.start(self.hint)
        MainScreen.fade_out.start(self.execute)
        MainScreen.fade_out.start(self.progress)
        MainScreen.fade_out.start(self.wait)

        Animation.cancel_all(widget)
        MainScreen.fade_in.start(widget)

    def pause(self):
        Ball.interactive = False
        self.set_visible(self.progress)
        self.is_paused = True
        #self.progress.loading_animation()

    def unpause(self, dt=None):
        Ball.interactive = True
        self.cradle.reset_balls()
        self.is_paused = False
        self.set_visible(self.hint)

    def update_button(self):
        if self.cradle.num_left() == 0 and self.cradle.num_right() == 0:
            self.set_visible(self.hint)
        else:
            self.set_visible(self.execute)

    def switch_to_loading_screen(self, dt=None):
        sm.current = 'loading'

class MyProgressBar(Widget):
    def loading_animation(self):
        load = (Animation(size=(5, 20), duration=0.1) +
                Animation(size=(400, 20), duration=10))
        load.start(self.ids.progressBar)

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
        left = sum(ball.r == BallString.ROT_LEFT for ball in self.get_balls())
        sm.get_screen('loading').SCOOP_LEFT = left
        return left

    def num_right(self):
        right = sum(ball.r == BallString.ROT_RIGHT for ball in self.get_balls())
        sm.get_screen('loading').SCOOP_RIGHT = right
        return right

    def reset_balls(self, dt=None):
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
        machine.admin_quit_all()

    @staticmethod
    def back_action():
        machine.home()
        sm.current = 'main'

mixpanel = MixPanel("Newtons Cradle", MIXPANEL_TOKEN)
# ////////////////////////////////////////////////////////////////
# //                          RUN APP                           //
# ////////////////////////////////////////////////////////////////
if __name__ == "__main__":
    print("Running main...")
    try:
        print("Starting up")
        machine.startup()
        # Config.set('graphics', 'fullscreen', 'auto')
        # Config.set('graphics', 'window_state', 'maximized')
        # Config.write()
        NewtonsCradleGUI().run()
        print("Running GUI successfully(?)")
    except KeyboardInterrupt:
        machine.quit_all()