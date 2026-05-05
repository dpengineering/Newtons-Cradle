from dpeaDPi.DPiStepper import DPiStepper
from time import sleep


def _wait_for_home_state(dpiStepper: DPiStepper, stepperNum: int, target_home_state: bool):
    for _ in range(100000):
        results, stoppedFlg, __, homeAtHomeSwitchFlg = dpiStepper.getStepperStatus(stepperNum)
        if results != True:
            return False
        if stoppedFlg:
            return False
        if homeAtHomeSwitchFlg == target_home_state:
            return True

    return False


def _home_stepper_to_state(dpiStepper: DPiStepper, stepperNum: int, directionTowardHome: int,
                           maxDistanceToMoveInSteps: int, target_home_state: bool):
    if dpiStepper.moveToRelativePositionInSteps(
            stepperNum,
            maxDistanceToMoveInSteps * directionTowardHome * (1 if target_home_state else -1),
            False) != True:
        return False

    if not _wait_for_home_state(dpiStepper, stepperNum, target_home_state):
        return False

    dpiStepper.emergencyStop(stepperNum)
    sleep(.1)
    return True


def _home_steppers_to_state(dpiStepper: DPiStepper, steppers, target_home_state: bool):
    """Move the given steppers together and stop each one as soon as its own sensor matches."""

    # Set speeds and accelerations for both motors
    for stepperNum, directionTowardHome, speedInStepsPerSecond, maxDistanceToMoveInSteps in steppers:
        if dpiStepper.setSpeedInStepsPerSecond(stepperNum, speedInStepsPerSecond) != True:
            return False
        if dpiStepper.setAccelerationInStepsPerSecondPerSecond(stepperNum, speedInStepsPerSecond) != True:
            return False

    for stepperNum, directionTowardHome, _, maxDistanceToMoveInSteps in steppers:
        moveDistance = maxDistanceToMoveInSteps * directionTowardHome
        if not target_home_state:
            moveDistance = -moveDistance
        if dpiStepper.moveToRelativePositionInSteps(stepperNum, moveDistance, False) != True:
            return False

    stepper_done = {stepperNum: False for stepperNum, _, _, _ in steppers}
    for _ in range(100000):
        for stepperNum, _, _, _ in steppers:
            results, stoppedFlg, __, homeSwitchFlg = dpiStepper.getStepperStatus(stepperNum)
            if results != True:
                return False

            if not stepper_done[stepperNum]:
                if homeSwitchFlg == target_home_state:
                    dpiStepper.emergencyStop(stepperNum)
                    sleep(.1)
                    stepper_done[stepperNum] = True
                elif stoppedFlg:
                    return False

        if all(stepper_done.values()):
            return True

    return False


def moveToHomeInSteps(dpiStepper: DPiStepper, stepperNum: int, directionTowardHome: int,
                        speedInStepsPerSecond: float, maxDistanceToMoveInSteps: int):
    
    steppers_normal = [(stepperNum, directionTowardHome, speedInStepsPerSecond, maxDistanceToMoveInSteps)]
    steppers_slow = [(stepperNum, directionTowardHome, speedInStepsPerSecond / 8, maxDistanceToMoveInSteps)]

    if (stepperNum < 0) or (stepperNum > 1):
        return False

    if not ((directionTowardHome == 1) or (directionTowardHome == -1)):
        return False

    if dpiStepper.enableMotors(True) != True:
        return False

    results, _ , _, homeSwitchFlg = dpiStepper.getStepperStatus(stepperNum)
    if results != True:
        return False
    
    # Phase 1: move toward home until the motor hits its sensor.
    if homeSwitchFlg != True:
        if not _home_steppers_to_state(dpiStepper,steppers_normal,True):
            return False

    # Phase 2: move away from home until the motor leaves its sensor (False = not touching sensor, True = touching sensor).
    if not _home_steppers_to_state(dpiStepper,steppers_normal,False):
        return False

    # Phase 3: move slowly back toward home and stop on contact.
    if not _home_steppers_to_state(dpiStepper,steppers_slow,True):
        return False
    
    # reset speed and position
    for stepperNum, _, speed, _ in steppers_normal:
        if dpiStepper.setSpeedInStepsPerSecond(stepperNum, speed) != True:
            return False
        if dpiStepper.setAccelerationInStepsPerSecondPerSecond(stepperNum, speed) != True:
            return False
        if dpiStepper.setCurrentPositionInSteps(stepperNum, 0) != True:
            return False

    return True

def moveBothToHomeInSteps(dpiStepper: DPiStepper, directionTowardHome0: int,
                speedInStepsPerSecond0: float, maxDistanceToMoveInSteps0: int,
                directionTowardHome1: int, speedInStepsPerSecond1: float, maxDistanceToMoveInSteps1: int):
    """
    Home two steppers in parallel.
    """

    # Stepper lists to reference for each phase of the homing process.
    steppers_normal = [
                (0, directionTowardHome0, speedInStepsPerSecond0, maxDistanceToMoveInSteps0),
                (1, directionTowardHome1, speedInStepsPerSecond1, maxDistanceToMoveInSteps1)
                ]
    
    steppers_slow = [
                (0, directionTowardHome0, speedInStepsPerSecond0 / 8, maxDistanceToMoveInSteps0),
                (1, directionTowardHome1, speedInStepsPerSecond1 / 8, maxDistanceToMoveInSteps1)
                ]
    
    for _, directionTowardHome, _, _ in steppers_normal:
        if not ((directionTowardHome == 1) or (directionTowardHome == -1)):
            return False
    
    if dpiStepper.enableMotors(True) != True:
        return False
    
    results0, _, _, home0 = dpiStepper.getStepperStatus(0)
    results1, _, _, home1 = dpiStepper.getStepperStatus(1)
    if results0 != True or results1 != True:
        return False
    
    # Phase 1: move toward home until each motor individually hits its sensor.
    if home0 != True or home1 != True:
        if not _home_steppers_to_state(dpiStepper, steppers_normal, True):
            return False

    # Phase 2: move away from home until each motor individually leaves its sensor.
    if not _home_steppers_to_state(dpiStepper, steppers_normal, False):
        return False

    # Phase 3: move slowly back toward home and stop each motor on contact.
    if not _home_steppers_to_state(dpiStepper, steppers_slow, True):
        return False

    # reset speed and position
    for stepperNum, _, speed, _ in steppers_normal:
        if dpiStepper.setSpeedInStepsPerSecond(stepperNum, speed) != True:
            return False
        if dpiStepper.setAccelerationInStepsPerSecondPerSecond(stepperNum, speed) != True:
            return False
        if dpiStepper.setCurrentPositionInSteps(stepperNum, 0) != True:
            return False
    
    return True


if __name__ == "__main__":
    dpiStepper = DPiStepper()
    dpiStepper.setBoardNumber(0)
    if dpiStepper.initialize() != True:
        print("Communication with the DPiStepper board failed.")

    dpiStepper.enableMotors(True)

    microstepping = 8
    dpiStepper.setMicrostepping(microstepping)

    speed_steps_per_second = 200 * microstepping
    accel_steps_per_second_per_second = speed_steps_per_second
    dpiStepper.setSpeedInStepsPerSecond(0, speed_steps_per_second)
    dpiStepper.setSpeedInStepsPerSecond(1, speed_steps_per_second)
    dpiStepper.setAccelerationInStepsPerSecondPerSecond(0, accel_steps_per_second_per_second)
    dpiStepper.setAccelerationInStepsPerSecondPerSecond(1, accel_steps_per_second_per_second)
    
    try:
        moveBothToHomeInSteps(dpiStepper, 0, 0, 1, 200, 10000, 1, 1, 200, 10000)
    finally:
        dpiStepper.enableMotors(False)