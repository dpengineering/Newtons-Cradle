import itertools
import os

os.environ["KIVY_NO_ARGS"] = "1"
os.environ["KIVY_NO_CONSOLELOG"] = "1"

import dpeaDPi.DPiStepper
import pytest
from dpeaDPi.simulation import SimState

from cradle_sim import CradleStepper

_import_state = SimState()
_import_board_numbers = itertools.count()
dpeaDPi.DPiStepper.DPiStepper = lambda: CradleStepper(_import_state, next(_import_board_numbers))

import stepper_hardware as hw  # noqa: E402

DEFAULT_OFFSETS = dict(
    offset_left=hw.OFFSET_LEFT,
    offset_right=hw.OFFSET_RIGHT,
    offset_v_left=hw.OFFSET_V_LEFT,
    offset_v_right=hw.OFFSET_V_RIGHT,
)


@pytest.fixture
def sim_state():
    return SimState()


@pytest.fixture
def boards(monkeypatch, sim_state):
    """Fresh simulated right (board 0) and left (board 1) arms, initialized like the app does."""
    right, left = CradleStepper(sim_state, 0), CradleStepper(sim_state, 1)
    monkeypatch.setattr(hw, "dpiStepper0", right)
    monkeypatch.setattr(hw, "dpiStepper1", left)
    monkeypatch.setattr(hw, "sleep", sim_state.clock.advance)
    monkeypatch.setattr(hw, "time", sim_state.clock.now)
    hw.set_offsets(**DEFAULT_OFFSETS)
    hw.init_hardware()
    yield right, left
    hw.set_offsets(**DEFAULT_OFFSETS)



@pytest.fixture
def homings(monkeypatch):
    """Counts full homings, which verify_home should only run when an arm is off its switch."""
    calls = []
    double_home = hw.double_home
    monkeypatch.setattr(hw, "double_home", lambda: (calls.append(1), double_home()))
    return calls
