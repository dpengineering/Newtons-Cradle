import os
import tempfile
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

STEPS_PER_MM = 64
SPEED_MM_PER_S = 200
ACCEL_MM_PER_S2 = 200

DISTANCE_TO_FIRST_BALL = 120
BALL_DIAMETER = 110
LIFT_DISTANCE = 50
# How far back each count of balls is carried before the drop, so the scooper clears the cradle.
RELEASE_DISTANCES = (0, 60, 150, 300, 400, 550)
MAX_BALLS = 5

HOME_SPEED_STEPS_PER_S = 4000
HOME_SLOW_SPEED_STEPS_PER_S = HOME_SPEED_STEPS_PER_S / 8
HOME_MAX_STEPS = 50000
HOME_SETTLE_S = 0.1
MOTION_TIMEOUT_S = 15.0

TUNING_PATH = Path("variables.json")


def mm_to_steps(mm):
    return round(mm * STEPS_PER_MM)


def pickup_mm(num_balls, offset):
    return DISTANCE_TO_FIRST_BALL + num_balls * BALL_DIAMETER + offset


# A trim may move the release point toward home but not behind it, and may lower the
# lift but not below the rest position.
HorizontalOffset = Annotated[int, Field(gt=-RELEASE_DISTANCES[1])]
VerticalOffset = Annotated[int, Field(gt=-LIFT_DISTANCE)]


class Tuning(BaseModel):
    """This exhibit's live trims, edited on the admin screen and kept in variables.json."""

    model_config = ConfigDict(validate_assignment=True, populate_by_name=True)

    offset_left: HorizontalOffset = -4
    offset_right: HorizontalOffset = 9
    offset_v_left: VerticalOffset = 0
    offset_v_right: VerticalOffset = 0
    cooldown_secs: int = Field(default=20, ge=0, alias="COOLDOWN_SECS")

    @classmethod
    def load(cls, path=TUNING_PATH):
        if not path.exists():
            return cls()
        return cls.model_validate_json(path.read_text())

    def save(self, path=TUNING_PATH):
        # Write beside the target and rename, so a power cut never leaves a half-written file.
        with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False) as tmp:
            tmp.write(self.model_dump_json(by_alias=True, indent=2))
        os.replace(tmp.name, path)
