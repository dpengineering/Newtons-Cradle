import pytest
from hypothesis import given, strategies as st

import stepper_hardware as hw
from cradle_sim import settle

STEPS_PER_MM = 64
H, V = 0, 1
COMBOS = [(left, right) for left in range(6) for right in range(6) if 0 < left + right <= 5]


def known_bug(reason):
    return pytest.mark.xfail(strict=True, reason=reason)


RIGHT_ARM_NOT_AWAITED = known_bug("the right arm's moves are fired without waiting when the left arm or the release also moves")
SCOOP_COMBOS = [
    pytest.param(left, right, marks=RIGHT_ARM_NOT_AWAITED) if (left and right) or right == 5 else (left, right)
    for left, right in COMBOS
]
OFFSETS = st.integers(min_value=-30, max_value=30)


def arm_moves(boards):
    return [move for board in boards for move in board.moves]


def start_away_from_home(*boards):
    for board in boards:
        for stepperNum in (H, V):
            board.setCurrentPositionInSteps(stepperNum, 3000)


def homed(board, stepperNum):
    return board.getCurrentPositionInSteps(stepperNum) == 0 and board.getStepperStatus(stepperNum).at_home


@pytest.mark.parametrize("num_left,num_right", SCOOP_COMBOS)
def test_scoop_never_moves_both_axes_of_an_arm_at_once(boards, num_left, num_right):
    hw.scoop(num_left, num_right)
    overlapping = [move for move in arm_moves(boards) if move.other_axis_moving]
    assert not overlapping, overlapping[0]


@RIGHT_ARM_NOT_AWAITED
@pytest.mark.parametrize("end_at_home", [True, False])
def test_stop_balls_never_moves_both_axes_of_an_arm_at_once(boards, end_at_home):
    hw.stop_balls(end_at_home)
    overlapping = [move for move in arm_moves(boards) if move.other_axis_moving]
    assert not overlapping, overlapping[0]


@pytest.mark.parametrize("num_left,num_right", SCOOP_COMBOS)
def test_scoop_drops_balls_at_release_distance(boards, num_left, num_right):
    hw.scoop(num_left, num_right)
    for board, count in zip(boards, (num_right, num_left)):
        if not count:
            continue
        drop = next(move for move in board.moves if move.stepper == V and move.start > 0 and move.target == 0)
        assert not drop.other_axis_moving
        assert drop.other_axis_position == hw.RELEASE_DISTANCES[count] * STEPS_PER_MM


@pytest.mark.parametrize("num_left,num_right", COMBOS)
def test_scoop_ends_with_every_axis_home(boards, num_left, num_right):
    hw.scoop(num_left, num_right)
    for board in boards:
        for stepperNum in (H, V):
            assert board.getMotionComplete(stepperNum)
            assert board.getCurrentPositionInSteps(stepperNum) == 0


@given(num_balls=st.integers(min_value=1, max_value=5), offset_left=OFFSETS, offset_right=OFFSETS)
def test_release_point_is_between_home_and_pickup(num_balls, offset_left, offset_right):
    for offset in (offset_left, offset_right):
        pickup = hw.DISTANCE_TO_FIRST_BALL + num_balls * hw.BALL_DIAMETER + offset
        assert 0 < hw.RELEASE_DISTANCES[num_balls] < pickup


@pytest.mark.parametrize("num_left,num_right", [(1, 0), (0, 1), (2, 3), (4, 1)])
def test_scoop_lifts_to_lift_distance_plus_vertical_offset(boards, num_left, num_right):
    hw.set_offsets(offset_v_left=7, offset_v_right=-3)
    hw.scoop(num_left, num_right)
    for board, count, offset in zip(boards, (num_right, num_left), (-3, 7)):
        lifts = [move.target for move in board.moves if move.stepper == V and move.target > 0]
        assert lifts == ([(hw.LIFT_DISTANCE + offset) * STEPS_PER_MM] if count else [])


@pytest.mark.parametrize("num_left,num_right", [(1, 0), (0, 1), (2, 3), (4, 1)])
def test_scoop_reaches_balls_with_horizontal_offsets(boards, num_left, num_right):
    hw.set_offsets(offset_left=-6, offset_right=11)
    hw.scoop(num_left, num_right)
    for board, count, offset in zip(boards, (num_right, num_left), (11, -6)):
        if count:
            reach = max(move.target for move in board.moves if move.stepper == H)
            assert reach == (hw.DISTANCE_TO_FIRST_BALL + count * hw.BALL_DIAMETER + offset) * STEPS_PER_MM


def test_double_home_zeroes_every_axis_on_its_switch(boards):
    start_away_from_home(*boards)
    hw.double_home()
    for board in boards:
        for stepperNum in (H, V):
            assert homed(board, stepperNum)


@known_bug("homing sets acceleration to the homing speed and speed_reset() only restores speed")
@pytest.mark.parametrize("home", [hw.double_home, lambda: (hw.home(0), hw.home(1))], ids=["double_home", "home"])
@pytest.mark.parametrize("num_left,num_right", [(1, 0), (2, 3)])
def test_scoop_after_homing_uses_configured_acceleration(boards, home, num_left, num_right):
    start_away_from_home(*boards)
    home()
    for board in boards:
        board.moves.clear()
    hw.scoop(num_left, num_right)
    expected = hw.accel_in_mm_per_sec_per_sec * STEPS_PER_MM
    assert {move.acceleration for move in arm_moves(boards)} == {expected}


@known_bug("double_home() ignores the False that moveBothToHomeInSteps returns")
def test_double_home_raises_when_a_switch_never_closes(boards):
    start_away_from_home(*boards)
    boards[1].stuck_open_switches.add(H)
    with pytest.raises(RuntimeError, match="(?i)hom"):
        hw.double_home()


@known_bug("_wait_while_busy() prints a warning on timeout and carries on")
def test_wait_raises_when_a_motor_never_stops(boards):
    boards[0].stalled.add(H)
    with pytest.raises(TimeoutError):
        hw.back_to_home()


@known_bug("home() defaults to board 0, so the left arm is never homed")
@pytest.mark.parametrize("shutdown", ["quit_all", "admin_quit_all", "shutdown_service"])
def test_shutdown_paths_home_both_arms_and_disable_motors(boards, monkeypatch, shutdown):
    start_away_from_home(*boards)
    monkeypatch.setattr(hw.subprocess, "Popen", lambda *args, **kwargs: None)
    monkeypatch.setattr(hw, "quit", lambda: None, raising=False)
    getattr(hw, shutdown)()
    settle(*boards)
    for board in boards:
        for stepperNum in (H, V):
            assert board.getCurrentPositionInSteps(stepperNum) == 0
            assert not board.getStepperStatus(stepperNum).enabled
