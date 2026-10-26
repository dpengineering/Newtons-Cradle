import json
from pathlib import Path

import pytest
from hypothesis import given, strategies as st
from pydantic import ValidationError

from config import LIFT_DISTANCE, MAX_BALLS, RELEASE_DISTANCES, Tuning, pickup_mm

REPO_ROOT = Path(__file__).resolve().parent.parent
FIELDS = ["offset_left", "offset_right", "offset_v_left", "offset_v_right", "cooldown_secs"]


def test_defaults_match_the_example_file():
    assert Tuning() == Tuning.model_validate_json((REPO_ROOT / "variables.example.json").read_text())


def test_a_missing_file_loads_the_defaults(tmp_path):
    assert Tuning.load(tmp_path / "variables.json") == Tuning()


def test_save_then_load_round_trips_with_the_existing_key_names(tmp_path):
    path = tmp_path / "variables.json"
    Tuning(offset_left=-2, offset_v_right=3, cooldown_secs=12).save(path)
    assert json.loads(path.read_text())["COOLDOWN_SECS"] == 12
    assert Tuning.load(path) == Tuning(offset_left=-2, offset_v_right=3, cooldown_secs=12)
    assert [p.name for p in tmp_path.iterdir()] == ["variables.json"]


@given(st.sampled_from(FIELDS), st.integers(min_value=-500, max_value=500))
def test_a_rejected_edit_leaves_the_old_value(field, value):
    tuning = Tuning()
    before = tuning.model_dump()
    try:
        setattr(tuning, field, value)
    except ValidationError:
        assert tuning.model_dump() == before


@given(st.integers(-500, 500), st.integers(-500, 500), st.integers(-500, 500), st.integers(-500, 500),
       st.integers(-500, 500))
def test_every_accepted_tuning_lifts_and_releases_in_front_of_home(left, right, v_left, v_right, cooldown):
    try:
        tuning = Tuning(offset_left=left, offset_right=right, offset_v_left=v_left, offset_v_right=v_right,
                        cooldown_secs=cooldown)
    except ValidationError:
        return
    assert tuning.cooldown_secs >= 0
    for offset_v in (v_left, v_right):
        assert LIFT_DISTANCE + offset_v > 0
    for offset in (left, right):
        for count in range(1, MAX_BALLS + 1):
            assert 0 < RELEASE_DISTANCES[count] + offset < pickup_mm(count, offset)


def test_a_corrupt_file_fails_loudly(tmp_path):
    path = tmp_path / "variables.json"
    path.write_text('{"offset_left": ')
    with pytest.raises(ValidationError):
        Tuning.load(path)
