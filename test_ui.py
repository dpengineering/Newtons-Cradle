#!/usr/bin/env python3
"""Run the Kivy UI without initializing hardware.
This imports `main` (which now defers hardware init) and stubs hardware functions
to safe no-ops so the UI can run on machines without DPiStepper attached.
"""
import os
import sys
import types

from kivy.uix.button import Button
from kivy.uix.widget import Widget


os.environ.setdefault("KIVY_NO_CONSOLELOG", "1")


def install_stub_modules():
    """Provide minimal stand-ins for hardware/vendor modules before importing main."""
    pidev_module = types.ModuleType("pidev")
    pidev_kivy_module = types.ModuleType("pidev.kivy")
    pidev_mixpanel_module = types.ModuleType("pidev.MixPanel")
    dpea_module = types.ModuleType("dpeaDPi")
    dpea_stepper_module = types.ModuleType("dpeaDPi.DPiStepper")

    class _NoOpStepper:
        def __init__(self, *args, **kwargs):
            self.board_number = None

        def setBoardNumber(self, number):
            self.board_number = number

        def initialize(self):
            return True

        def enableMotors(self, enabled):
            return None

        def setStepsPerMillimeter(self, *args, **kwargs):
            return None

        def setAccelerationInMillimetersPerSecondPerSecond(self, *args, **kwargs):
            return None

        def setSpeedInMillimetersPerSecond(self, *args, **kwargs):
            return None

        def moveToRelativePositionInMillimeters(self, *args, **kwargs):
            return None

        def moveToHomeInSteps(self, *args, **kwargs):
            return None

        def getStepperStatus(self, *args, **kwargs):
            return (False, False, False, False)

    class _NoOpMixPanel:
        def __init__(self, *args, **kwargs):
            pass

    class _NoOpButton(Button):
        pass

    class _NoOpPauseScreen(Widget):
        pass

    dpea_stepper_module.DPiStepper = _NoOpStepper
    pidev_kivy_module.DPEAButton = _NoOpButton
    pidev_kivy_module.PauseScreen = _NoOpPauseScreen
    pidev_mixpanel_module.MixPanel = _NoOpMixPanel

    pidev_module.kivy = pidev_kivy_module
    pidev_module.MixPanel = pidev_mixpanel_module

    sys.modules["pidev"] = pidev_module
    sys.modules["pidev.kivy"] = pidev_kivy_module
    sys.modules["pidev.MixPanel"] = pidev_mixpanel_module
    sys.modules["dpeaDPi"] = dpea_module
    sys.modules["dpeaDPi.DPiStepper"] = dpea_stepper_module


install_stub_modules()

import main


def stub(name):
    def _s(*a, **k):
        print(f"[stub] {name} called")

    return _s


# List of hardware functions to stub so UI won't touch hardware
hardware_stubs = [
    'init_hardware', 'home', 'quit_all', 'admin_quit_all', 'new_scoop',
    'scoop_left', 'scoop_right', 'scoop_both', 'scoopFiveBalls',
    'release_both', 'release_right', 'release_left', 'stop_balls',
    'double_home', 'set_horizontal_pos', 'set_vertical_pos',
    'set_vertical_pos_left', 'set_vertical_pos_right', 'set_horizontal_pos_left',
    'set_horizontal_pos_right', 'set_horizontal_speed', 'set_vertical_speed',
    'are_horizontal_busy', 'are_vertical_busy'
]

for name in hardware_stubs:
    if not hasattr(main, name):
        setattr(main, name, stub(name))
    else:
        # replace with stub to be safe
        setattr(main, name, stub(name))


if __name__ == '__main__':
    try:
        main.MyApp().run()
    except KeyboardInterrupt:
        print('Exiting UI')
