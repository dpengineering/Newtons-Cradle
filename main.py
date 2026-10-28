#!/usr/bin/python3
import os

os.environ.setdefault("KIVY_NO_CONSOLELOG", "1")

import subprocess
import time

from dpeaDPi.DPiStepper import DPiStepper
from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.properties import BooleanProperty, NumericProperty, ObjectProperty, StringProperty
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.widget import Widget
from kivy.vector import Vector
from pydantic import ValidationError

from arms import CradleArms
from config import Tuning
from exhibit import OUTPUTS, Exhibit, Phase
from Kivy.Scenes.AdminScreen import AdminScreen

GESTURE_MIN_DELTA = 25
GESTURE_MAX_DELTA = 75

Builder.load_file('Kivy/Scenes/main.kv')
Builder.load_file('Kivy/Libraries/DPEAButton.kv')
Builder.load_file('Kivy/Scenes/AdminScreen.kv')
Window.clearcolor = (.9, .9, .9, 1)


class Ball(Widget):
    down = ObjectProperty(None, allownone=True)

    @property
    def string(self):
        return self.parent

    @property
    def cradle(self):
        return self.parent.parent

    def transform_point(self, v):
        origin = Vector(self.string.pos)
        return (v - origin).rotate(-self.string.rotation) + origin

    def clear(self):
        self.down = None
        self.cradle.active_ball = None

    def pushed(self, touch):
        v = self.transform_point(Vector(touch.pos))
        cradle = self.cradle
        if cradle.interactive and cradle.active_ball is None and self.collide_point(v.x, v.y):
            self.down = v
            cradle.active_ball = self

    def moved(self, touch):
        if self.down is None:
            return
        d = self.transform_point(Vector(touch.pos)) - self.down
        if d.length() >= GESTURE_MAX_DELTA:
            self.swipe(d.x)

    def released(self, touch):
        if self.down is None:
            return
        d = self.transform_point(Vector(touch.pos)) - self.down
        if not self.swipe(d.x):
            self.cradle.ball_touched(self.string)
            self.clear()

    def swipe(self, dx):
        if dx >= GESTURE_MIN_DELTA:
            self.cradle.ball_right(self.string)
        elif dx <= -GESTURE_MIN_DELTA:
            self.cradle.ball_left(self.string)
        else:
            return False
        self.clear()
        return True


class BallString(Widget):
    rotation = NumericProperty(0)
    name = StringProperty("middle")
    ROT_LEFT = -35
    ROT_RIGHT = 35
    ROT_DOWN = 0
    r = NumericProperty(ROT_DOWN)

    def _swing(self, rotation):
        Animation.cancel_all(self)
        Animation(rotation=rotation, t="out_quad").start(self)
        self.r = rotation

    def down(self):
        self._swing(BallString.ROT_DOWN)

    def left(self):
        self._swing(BallString.ROT_LEFT)

    def right(self):
        self._swing(BallString.ROT_RIGHT)


# A tap on a resting ball pulls it toward the nearer side, the middle ball going right.
TAP_PULLS_LEFT = {"left": True, "middle-left": True, "middle": False, "middle-right": False, "right": False}


class Cradle(Widget):
    """The five strings, left to right. Left-pulled balls are always a prefix of that order and
    right-pulled balls a suffix, with the outermost ball on each side never pulled across."""

    interactive = BooleanProperty(True)
    active_ball = ObjectProperty(None, allownone=True)
    __events__ = ("on_selection",)

    def on_selection(self):
        pass

    def strings(self):
        return self.children[::-1]

    def num_left(self):
        return sum(string.r == BallString.ROT_LEFT for string in self.strings())

    def num_right(self):
        return sum(string.r == BallString.ROT_RIGHT for string in self.strings())

    def reset_balls(self):
        for string in self.strings():
            string.down()
        self.dispatch("on_selection")

    def ball_right(self, ball_string):
        if ball_string.r == BallString.ROT_LEFT:
            self.ball_down(ball_string)
            return
        strings = self.strings()
        for string in strings[strings.index(ball_string):]:
            string.down() if string.name == "left" else string.right()
        self.dispatch("on_selection")

    def ball_left(self, ball_string):
        if ball_string.r == BallString.ROT_RIGHT:
            self.ball_down(ball_string)
            return
        strings = self.strings()
        for string in strings[:strings.index(ball_string) + 1]:
            string.down() if string.name == "right" else string.left()
        self.dispatch("on_selection")

    def ball_down(self, ball_string):
        # Lowering a ball also lowers every pulled ball between it and the middle.
        strings = self.strings()
        i = strings.index(ball_string)
        side = ball_string.r
        if side == BallString.ROT_LEFT:
            inward = strings[i:]
        elif side == BallString.ROT_RIGHT:
            inward = strings[i::-1]
        else:
            inward = []
        for string in inward:
            if string.r != side:
                break
            string.down()
        self.dispatch("on_selection")

    def ball_touched(self, ball_string):
        if ball_string.r != BallString.ROT_DOWN:
            self.ball_down(ball_string)
        elif TAP_PULLS_LEFT[ball_string.name]:
            self.ball_left(ball_string)
        else:
            self.ball_right(ball_string)


class MainScreen(Screen):
    exhibit = ObjectProperty(None)
    cradle = ObjectProperty(None)
    execute = ObjectProperty(None)
    hint = ObjectProperty(None)
    wait = ObjectProperty(None)

    def show(self, widget):
        for other in (self.hint, self.execute, self.wait):
            Animation.cancel_all(other)
            Animation(opacity=0, t="out_quad").start(other)
        Animation.cancel_all(widget)
        Animation(opacity=1, t="out_quad").start(widget)

    def show_phase(self, phase):
        self.cradle.interactive = OUTPUTS[phase].accepts_input
        if phase is Phase.READY:
            self.cradle.reset_balls()
        else:
            self.wait.text = OUTPUTS[phase].label
            self.show(self.wait)

    def update_button(self):
        if not self.cradle.interactive:
            return
        if self.cradle.num_left() or self.cradle.num_right():
            self.show(self.execute)
        else:
            self.show(self.hint)

    def start_pressed(self):
        self.exhibit.request_scoop(self.cradle.num_left(), self.cradle.num_right())


class VariableChanger(Widget):
    name = StringProperty("")
    tuning = ObjectProperty(None)
    value = NumericProperty(0)

    def on_tuning(self, *args):
        self.refresh()

    def on_name(self, *args):
        self.refresh()

    def refresh(self):
        if self.tuning is not None and self.name:
            self.value = getattr(self.tuning, self.name)

    def step(self, delta):
        try:
            setattr(self.tuning, self.name, self.value + delta)
        except ValidationError:
            return
        self.tuning.save()
        self.refresh()


class AdminFunctionsScreen(Screen):
    exhibit = ObjectProperty(None)
    tuning = ObjectProperty(None)
    restart = ObjectProperty(None)
    shutdown = ObjectProperty(None)

    def restart_action(self):
        self.exhibit.request_exit(self.restart)
        self.manager.current = 'main'

    def shutdown_action(self):
        self.exhibit.request_exit(self.shutdown)
        self.manager.current = 'main'

    def back_action(self):
        self.exhibit.request_return()
        self.manager.current = 'main'


def build_screens(exhibit, restart, shutdown):
    sm = ScreenManager()
    main_screen = MainScreen(name='main', exhibit=exhibit)
    sm.add_widget(main_screen)
    sm.add_widget(AdminScreen(name='admin'))
    sm.add_widget(AdminFunctionsScreen(name='adminFunctionsScreen', exhibit=exhibit, tuning=exhibit.arms.tuning,
                                       restart=restart, shutdown=shutdown))
    exhibit.on_phase = main_screen.show_phase
    return sm


def stop_service():
    # systemd stops this unit, so it doesn't restart. Needs the sudoers rule in the README.
    subprocess.Popen(["sudo", "systemctl", "stop", "newtons-cradle.service"])


class NewtonsCradleApp(App):
    def __init__(self, exhibit, shutdown=stop_service, **kwargs):
        super().__init__(**kwargs)
        self.exhibit = exhibit
        self.shutdown = shutdown

    def build(self):
        # Restart just ends the app, and systemd's Restart=on-success starts it again.
        sm = build_screens(self.exhibit, restart=self.stop, shutdown=self.shutdown)
        self.exhibit.start()
        Clock.schedule_interval(lambda dt: self.exhibit.tick(), 0)
        return sm


def open_boards():
    right, left = DPiStepper(), DPiStepper()
    right.setBoardNumber(0)
    left.setBoardNumber(1)
    return right, left


if __name__ == "__main__":
    right, left = open_boards()
    arms = CradleArms(right, left, Tuning.load(), time.monotonic)
    try:
        NewtonsCradleApp(Exhibit(arms, time.monotonic)).run()
    except KeyboardInterrupt:
        arms.enable_motors(False)
