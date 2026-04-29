from dpeaDPi.DPiStepper import *
from time import sleep

dpiStepper = DPiStepper()


def MoveBothToHomeInSteps(boardNum: int, stepperNum1: int, directionTowardHome1: int,
                speedInStepsPerSecond1: float, maxDistanceToMoveInSteps1: int, stepperNum2: int,
                directionTowardHome2: int,
                speedInStepsPerSecond2: float, maxDistanceToMoveInSteps2: int):

    dpiStepper.setBoardNumber(boardNum)

    """
Num_Stops_Motor variables are used as counters to count the amount of stops each motor has had:

Num_Stops_Motor = 1 means the motor has tripped the home sensor for the first time.

Num_Stops_Motor = 2 means the motor has moved away from the home sensor and no longer trips the sensor.

Num_Stops_Motor = 3 means the motor has moved back towards the home sensor and tripped the home sensor for the 
Second time.
    """

    Num_Stops_Motor1 = 0
    Num_Stops_Motor2 = 0
    if not ((directionTowardHome1 == 1) or (directionTowardHome1 == -1)):
        return False
    if not ((directionTowardHome2 == 1) or (directionTowardHome2 == -1)):
        return False

    if dpiStepper.enableMotors(True) != True:
        return False

    if dpiStepper.setSpeedInStepsPerSecond(stepperNum1, speedInStepsPerSecond1) != True:
        return False
    if dpiStepper.setAccelerationInStepsPerSecondPerSecond(stepperNum1, speedInStepsPerSecond1) != True:
        return False
    if dpiStepper.setSpeedInStepsPerSecond(stepperNum2, speedInStepsPerSecond2) != True:
        return False
    if dpiStepper.setAccelerationInStepsPerSecondPerSecond(stepperNum2, speedInStepsPerSecond2) != True:
        return False

    results1, stoppedFlg1, ___, homeAtHomeSwitchFlg1 = dpiStepper.getStepperStatus(stepperNum1)
    results2, stoppedFlg2, __, homeAtHomeSwitchFlg2 = dpiStepper.getStepperStatus(stepperNum2)
    if results1 != True:
        return False
    if results2 != True:
        return False

    if homeAtHomeSwitchFlg1 != True or homeAtHomeSwitchFlg2 != True:
        #
        # move toward the home switch
        #
        if dpiStepper.moveToRelativePositionInSteps(stepperNum2, maxDistanceToMoveInSteps2 * directionTowardHome2, False) != True:
            return False
        if dpiStepper.moveToRelativePositionInSteps(stepperNum1, maxDistanceToMoveInSteps1 * directionTowardHome1, False) != True:
            return False

    while True:
        results1, stoppedFlg1, ___, homeAtHomeSwitchFlg1 = dpiStepper.getStepperStatus(stepperNum1)
        results2, stoppedFlg2, __, homeAtHomeSwitchFlg2 = dpiStepper.getStepperStatus(stepperNum2)
        if results1 != True:
            return False
        if stoppedFlg1 and Num_Stops_Motor1 == 0:
            return False
        if results2 != True:
            return False
        if stoppedFlg2 and Num_Stops_Motor2 == 0:
            return False

        if homeAtHomeSwitchFlg1 == True and Num_Stops_Motor1 == 0:
            #print("Stopping Stepper1")
            dpiStepper.emergencyStop(stepperNum1)
            sleep(.1)
            Num_Stops_Motor1 = 1

        if homeAtHomeSwitchFlg2 == True and Num_Stops_Motor2 == 0:
            #print ("Stopping Stepper2")
            dpiStepper.emergencyStop(stepperNum2)
            sleep(.1)
            Num_Stops_Motor2 = 1

        if Num_Stops_Motor1 == 1 and Num_Stops_Motor2 == 1:
            #print ("both motors stopped!")
            break

    if dpiStepper.moveToRelativePositionInSteps(stepperNum1, -maxDistanceToMoveInSteps1 * directionTowardHome1, False) != True:
        return False
    if dpiStepper.moveToRelativePositionInSteps(stepperNum2, -maxDistanceToMoveInSteps2 * directionTowardHome2, False) != True:
        return False

    while True:
        results1, stoppedFlg1, ___, homeAtHomeSwitchFlg1 = dpiStepper.getStepperStatus(stepperNum1)
        results2, stoppedFlg2, __, homeAtHomeSwitchFlg2 = dpiStepper.getStepperStatus(stepperNum2)
        if results1 != True:
            return False
        if stoppedFlg1 and Num_Stops_Motor1 == 1:
            return False
        if results2 != True:
            return False
        if stoppedFlg2 and Num_Stops_Motor2 == 1:
            return False

        if homeAtHomeSwitchFlg1 != True and Num_Stops_Motor1 == 1:
            #print("Stepper1 out of Range")

            dpiStepper.emergencyStop(stepperNum1)
            Num_Stops_Motor1 = 2

        if homeAtHomeSwitchFlg2 != True and Num_Stops_Motor2 == 1:
            #print("Stepper2 out of Range")
            dpiStepper.emergencyStop(stepperNum2)
            Num_Stops_Motor2 = 2

        if Num_Stops_Motor2 == 2 and Num_Stops_Motor1 == 2:
            #print ("Both motors rehoming slowly")
            break

    if dpiStepper.setSpeedInStepsPerSecond(stepperNum1, speedInStepsPerSecond1 / 8) != True:
        return False
    if dpiStepper.moveToRelativePositionInSteps(stepperNum1, maxDistanceToMoveInSteps1 * directionTowardHome1, False) != True:
        return False

    if dpiStepper.setSpeedInStepsPerSecond(stepperNum2, speedInStepsPerSecond2 / 8) != True:
        return False
    if dpiStepper.moveToRelativePositionInSteps(stepperNum2, maxDistanceToMoveInSteps2 * directionTowardHome2,False) != True:
        return False


    while True:
        results1, stoppedFlg1, ___, homeAtHomeSwitchFlg1 = dpiStepper.getStepperStatus(stepperNum1)
        results2, stoppedFlg2, __, homeAtHomeSwitchFlg2 = dpiStepper.getStepperStatus(stepperNum2)
        if results1 != True:
            return False
        if stoppedFlg1 and Num_Stops_Motor1 == 2:
            return False
        if results2 != True:
            return False
        if stoppedFlg2 and Num_Stops_Motor2 == 2:
            return False

        if homeAtHomeSwitchFlg1 == True and Num_Stops_Motor1 == 2:
            #print("Stopping Stepper1")
            dpiStepper.emergencyStop(stepperNum1)
            sleep(.1)
            Num_Stops_Motor1 = 3

        if homeAtHomeSwitchFlg2 == True and Num_Stops_Motor2 == 2:
            #print("Stopping Stepper2")
            dpiStepper.emergencyStop(stepperNum2)
            sleep(.1)
            Num_Stops_Motor2 = 3

        if Num_Stops_Motor1 == 3 and Num_Stops_Motor2 == 3:
            #print("both motors successfully homed!")
            break