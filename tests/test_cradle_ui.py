import heapq
import itertools
import os

import pytest
from dpeaDPi.errors import DPiCommunicationError
from hypothesis import given, settings, strategies as st
from kivy.vector import Vector

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO_ROOT)

import main  # noqa: E402
import stepper_hardware as hw  # noqa: E402

screen = main.sm.get_screen("main")
admin = main.sm.get_screen("admin")
admin_functions = main.sm.get_screen("adminFunctionsScreen")
cradle = screen.cradle
LEFT, RIGHT, DOWN = main.BallString.ROT_LEFT, main.BallString.ROT_RIGHT, main.BallString.ROT_DOWN
NAMES = ["left", "middle-left", "middle", "middle-right", "right"]
ACTIONS = {
    "tap": cradle.ball_touched,
    "left": cradle.ball_left,
    "right": cradle.ball_right,
    "down": cradle.ball_down,
}
GESTURES = st.lists(st.tuples(st.sampled_from(sorted(ACTIONS)), st.sampled_from(NAMES)), max_size=30)


def string(name):
    return next(ball_string for ball_string in cradle.get_balls() if ball_string.name == name)


def rotations():
    return [string(name).r for name in NAMES]


def counts():
    return cradle.num_left(), cradle.num_right()


@pytest.fixture(autouse=True)
def fresh_screen():
    for ball_string in cradle.get_balls():
        ball_string.r = DOWN
    main.Ball.down_exists = False
    main.Ball.interactive = True
    screen.is_paused = False
    main.sm.current = "main"


class FakeClock:
    """Runs Clock.schedule_once callbacks in time order without waiting."""

    def __init__(self):
        self.now = 0.0
        self._queue = []
        self._order = itertools.count()

    def schedule_once(self, callback, timeout=0):
        heapq.heappush(self._queue, (self.now + timeout, next(self._order), callback))

    def run(self):
        while self._queue:
            self.now, _, callback = heapq.heappop(self._queue)
            callback(0)


class Touch:
    def __init__(self, pos):
        self.pos = pos


def changer(name):
    return next(widget for widget in admin_functions.walk()
                if isinstance(widget, main.VariableChanger) and widget.name == name)


def swipe(name, dx):
    ball = string(name).ids.ball
    start = Vector(ball.center)
    ball.pushed(Touch(tuple(start)))
    ball.released(Touch((start.x + dx, start.y)))


@settings(max_examples=300, deadline=None)
@given(GESTURES)
def test_selection_is_a_left_prefix_and_a_right_suffix(gestures):
    for action, name in gestures:
        ACTIONS[action](string(name))
        state = rotations()
        num_left, num_right = counts()
        assert state[:num_left] == [LEFT] * num_left
        assert state[len(state) - num_right:] == [RIGHT] * num_right
        assert num_left + num_right <= 5
        assert num_left <= 4 and num_right <= 4


@settings(max_examples=100, deadline=None)
@given(GESTURES)
def test_reset_balls_lowers_every_ball(gestures):
    for action, name in gestures:
        ACTIONS[action](string(name))
    screen.is_paused = True
    cradle.reset_balls()
    assert rotations() == [DOWN] * 5


@pytest.mark.parametrize("name,expected", [
    ("left", (1, 0)),
    ("middle-left", (2, 0)),
    ("middle", (0, 3)),
    ("middle-right", (0, 2)),
    ("right", (0, 1)),
])
def test_tap_on_a_resting_ball_selects_it_and_its_outer_neighbours(name, expected):
    cradle.ball_touched(string(name))
    assert counts() == expected


@pytest.mark.parametrize("name,dx,expected", [
    ("middle", -40, (3, 0)),
    ("middle", 40, (0, 3)),
    ("middle-right", -40, (4, 0)),
    ("middle-left", 40, (0, 4)),
])
def test_short_swipe_selects_the_same_balls_as_ball_left_or_right(name, dx, expected):
    swipe(name, dx)
    assert counts() == expected


def test_touches_are_ignored_while_paused():
    screen.pause()
    swipe("middle", 40)
    assert counts() == (0, 0)


def test_back_to_game_clears_a_partial_password():
    main.sm.current = "admin"
    for digit in (1, 2):
        admin.add_num(digit)
    admin.ids.back.dispatch("on_press")
    main.sm.current = "admin"
    for digit in (7, 2, 6, 6):
        admin.add_num(digit)
    admin.check_pass()
    assert main.sm.current == "adminFunctionsScreen"


def test_cooldown_never_goes_below_zero(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(main, "COOLDOWN_SECS", 0)
    changer("COOLDOWN_SECS").dec_value()
    assert main.COOLDOWN_SECS == 0


def test_offset_changes_reach_the_hardware_and_variables_json(monkeypatch, tmp_path, boards):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(main, "variables_dict", {})
    changer("offset_right").inc_value()
    assert hw.OFFSET_RIGHT == main.offset_right
    assert '"offset_right"' in (tmp_path / "variables.json").read_text()


def test_admin_back_leaves_motors_disabled(boards):
    admin_functions.back_action()
    for board in boards:
        for stepperNum in (0, 1):
            assert not board.getStepperStatus(stepperNum).enabled
    assert main.sm.current == "main"


def run_scoop(monkeypatch, num_left, num_right):
    clock = FakeClock()
    monkeypatch.setattr(main, "Clock", clock)
    scooped = []
    monkeypatch.setattr(main, "scoop", lambda left, right: scooped.append((left, right)))
    cradle.ball_touched(string("middle"))
    if num_left:
        string("left").left()
    main.scoop_balls_thread()
    return clock, scooped


def test_scoop_sequence_scoops_the_selection_then_unlocks_after_cooldown(monkeypatch, boards, homings):
    clock, scooped = run_scoop(monkeypatch, 1, 3)
    assert screen.is_paused
    clock.run()
    assert scooped == [(1, 3)]
    assert homings == []
    assert not screen.is_paused
    assert clock.now >= main.COOLDOWN_SECS
    for board in boards:
        assert not board.getStepperStatus(0).enabled


def test_scoop_sequence_disables_motors_when_hardware_fails(monkeypatch, boards):
    clock, _ = run_scoop(monkeypatch, 0, 3)

    def fail(*args):
        raise DPiCommunicationError("stepper", 0, operation="moveToAbsolutePositionInSteps")

    monkeypatch.setattr(main, "stop_balls", fail)
    with pytest.raises(DPiCommunicationError):
        clock.run()
    for board in boards:
        for stepperNum in (0, 1):
            assert not board.getStepperStatus(stepperNum).enabled
