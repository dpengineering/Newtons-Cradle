import os
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st
from kivy.vector import Vector

os.chdir(Path(__file__).resolve().parent.parent)

import main  # noqa: E402
from cradle_sim import run  # noqa: E402
from exhibit import Phase  # noqa: E402

LEFT, RIGHT, DOWN = main.BallString.ROT_LEFT, main.BallString.ROT_RIGHT, main.BallString.ROT_DOWN
NAMES = ["left", "middle-left", "middle", "middle-right", "right"]
ACTIONS = ["tap", "left", "right", "down"]
GESTURES = st.lists(st.tuples(st.sampled_from(ACTIONS), st.sampled_from(NAMES)), max_size=30)
# The cradle fixture is reset at the top of each example, so sharing it across examples is safe.
FIXTURE_REUSE = dict(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])


class Touch:
    def __init__(self, pos):
        self.pos = pos


@pytest.fixture
def ui(exhibit):
    exits = []
    sm = main.build_screens(exhibit, restart=lambda: exits.append("restart"), shutdown=lambda: exits.append("shutdown"))
    screen = sm.get_screen("main")
    screen.show_phase(exhibit.phase)
    return sm, screen, exits


@pytest.fixture
def cradle(ui):
    return ui[1].cradle


def string(cradle, name):
    return next(s for s in cradle.strings() if s.name == name)


def rotations(cradle):
    return [string(cradle, name).r for name in NAMES]


def counts(cradle):
    return cradle.num_left(), cradle.num_right()


def act(cradle, action, name):
    target = string(cradle, name)
    {"tap": cradle.ball_touched, "left": cradle.ball_left, "right": cradle.ball_right,
     "down": cradle.ball_down}[action](target)


def swipe(cradle, name, dx):
    ball = string(cradle, name).ids.ball
    start = Vector(ball.center)
    ball.pushed(Touch(tuple(start)))
    ball.released(Touch((start.x + dx, start.y)))


@settings(max_examples=300, **FIXTURE_REUSE)
@given(gestures=GESTURES)
def test_selection_is_a_left_prefix_and_a_right_suffix(cradle, gestures):
    cradle.reset_balls()
    for action, name in gestures:
        act(cradle, action, name)
        state = rotations(cradle)
        num_left, num_right = counts(cradle)
        assert state[:num_left] == [LEFT] * num_left
        assert state[len(state) - num_right:] == [RIGHT] * num_right
        assert num_left + num_right <= 5
        assert num_left <= 4 and num_right <= 4


@settings(max_examples=100, **FIXTURE_REUSE)
@given(gestures=GESTURES)
def test_reset_balls_lowers_every_ball(cradle, gestures):
    cradle.reset_balls()
    for action, name in gestures:
        act(cradle, action, name)
    cradle.reset_balls()
    assert rotations(cradle) == [DOWN] * 5


@pytest.mark.parametrize("name,expected", [
    ("left", (1, 0)), ("middle-left", (2, 0)), ("middle", (0, 3)), ("middle-right", (0, 2)), ("right", (0, 1)),
])
def test_tap_on_a_resting_ball_selects_it_and_its_outer_neighbours(cradle, name, expected):
    act(cradle, "tap", name)
    assert counts(cradle) == expected


@pytest.mark.parametrize("name,dx,expected", [
    ("middle", -40, (3, 0)), ("middle", 40, (0, 3)), ("middle-right", -40, (4, 0)), ("middle-left", 40, (0, 4)),
])
def test_short_swipe_selects_the_same_balls_as_ball_left_or_right(cradle, name, dx, expected):
    swipe(cradle, name, dx)
    assert counts(cradle) == expected


def test_start_hands_the_selection_to_the_exhibit_and_locks_the_balls(ui, exhibit):
    _, screen, _ = ui
    act(screen.cradle, "tap", "middle-left")
    screen.start_pressed()
    assert exhibit.phase is Phase.PREPARING
    swipe(screen.cradle, "middle", 40)
    assert counts(screen.cradle) == (2, 0)
    assert screen.wait.text == "Homing..."


def test_start_with_nothing_selected_does_nothing(ui, exhibit):
    ui[1].start_pressed()
    assert exhibit.phase is Phase.READY


def test_the_balls_unlock_and_lower_when_the_exhibit_is_ready_again(ui, exhibit, sim_state):
    _, screen, _ = ui
    act(screen.cradle, "tap", "right")
    screen.start_pressed()
    run(sim_state, exhibit.tick, lambda: exhibit.phase is Phase.READY)
    assert screen.cradle.interactive
    assert counts(screen.cradle) == (0, 0)


def test_back_to_game_clears_a_partial_password(ui):
    sm, _, _ = ui
    admin = sm.get_screen("admin")
    sm.current = "admin"
    for digit in (1, 2):
        admin.add_digit(digit)
    admin.ids.back.dispatch("on_press")
    assert sm.current == "main"
    sm.current = "admin"
    for digit in (7, 2, 6, 6):
        admin.add_digit(digit)
    admin.submit()
    assert sm.current == "adminFunctionsScreen"


def test_the_password_field_shows_one_star_per_digit(ui):
    admin = ui[0].get_screen("admin")
    for digit in (4, 2, 0):
        admin.add_digit(digit)
    admin.remove_digit()
    assert admin.ids.pw.text == "* * "


def changer(sm, name):
    screen = sm.get_screen("adminFunctionsScreen")
    return next(w for w in screen.walk() if isinstance(w, main.VariableChanger) and w.name == name)


def test_cooldown_never_goes_below_zero(ui, exhibit, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    exhibit.arms.tuning.cooldown_secs = 0
    cooldown = changer(ui[0], "cooldown_secs")
    cooldown.refresh()
    cooldown.step(-1)
    assert exhibit.arms.tuning.cooldown_secs == 0 and cooldown.value == 0


def test_offset_edits_reach_the_arms_and_variables_json(ui, exhibit, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    changer(ui[0], "offset_right").step(1)
    assert exhibit.arms.tuning.offset_right == 10
    assert '"offset_right": 10' in (tmp_path / "variables.json").read_text()


@pytest.mark.parametrize("action,expected", [("restart_action", "restart"), ("shutdown_action", "shutdown")])
def test_restart_and_quit_home_first_then_exit(ui, exhibit, sim_state, action, expected):
    sm, _, exits = ui
    getattr(sm.get_screen("adminFunctionsScreen"), action)()
    assert exits == []
    run(sim_state, exhibit.tick, lambda: exhibit.phase is Phase.STOPPED)
    assert exits == [expected]


def test_admin_back_returns_the_arms_home_and_shows_the_game(ui, exhibit, sim_state):
    sm = ui[0]
    sm.current = "adminFunctionsScreen"
    sm.get_screen("adminFunctionsScreen").back_action()
    assert exhibit.phase is Phase.RETURNING and sm.current == "main"
    run(sim_state, exhibit.tick, lambda: exhibit.phase is Phase.READY)
