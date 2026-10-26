import os

os.environ["KIVY_NO_ARGS"] = "1"
os.environ["KIVY_NO_CONSOLELOG"] = "1"

import pytest
from dpeaDPi.simulation import SimState

from arms import CradleArms
from config import Tuning
from cradle_sim import CradleStepper, run
from exhibit import Exhibit, Phase


@pytest.fixture
def sim_state():
    return SimState()


@pytest.fixture
def boards(sim_state):
    """Simulated right (board 0) and left (board 1) arms with their home switches mounted at 0."""
    return CradleStepper(sim_state, 0), CradleStepper(sim_state, 1)


@pytest.fixture
def arms(boards, sim_state):
    arms = CradleArms(*boards, Tuning(), sim_state.clock.now)
    arms.initialize()
    arms.enable_motors(True)
    return arms


@pytest.fixture
def homings(arms, monkeypatch):
    """Counts full homings, which should only happen when an axis is off its switch."""
    calls = []
    home = arms.home
    monkeypatch.setattr(arms, "home", lambda: (calls.append(1), home()))
    return calls


@pytest.fixture
def exhibit(arms, sim_state):
    exhibit = Exhibit(arms, sim_state.clock.now)
    exhibit.start()
    run(sim_state, exhibit.tick, lambda: exhibit.phase is Phase.READY)
    return exhibit
