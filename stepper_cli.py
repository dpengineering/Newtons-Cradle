#!/usr/bin/env python3
"""Drive the arms by hand on the device. Each command runs to completion before the next prompt."""
import time

from arms import CradleArms
from config import Tuning
from main import open_boards

COMMANDS = """Commands:
  home                    - home all four axes
  back_to_home            - lower the scoopers, then bring both arms back to 0
  stop_balls              - stop the swinging balls and return home
  scoop <left> <right>    - scoop that many balls on each side
  status                  - print each axis's position and switch
  quit                    - disable the motors and exit"""


def run(arms):
    # The board round trips pace this loop. There is no event loop here to hand control back to.
    while arms.busy:
        arms.tick()


def main():
    arms = CradleArms(*open_boards(), Tuning.load(), time.monotonic)
    arms.initialize()
    arms.enable_motors(True)
    print(COMMANDS)
    try:
        prompt(arms)
    finally:
        arms.enable_motors(False)


def prompt(arms):
    while True:
        try:
            command, *args = input('> ').split() or ['']
        except (EOFError, KeyboardInterrupt):
            command, args = 'quit', []
        if command == 'quit':
            return
        if command == 'home':
            arms.home()
        elif command == 'back_to_home':
            arms.back_to_home()
        elif command == 'stop_balls':
            arms.stop_balls(end_at_home=True)
        elif command == 'scoop' and len(args) == 2 and all(arg.isdigit() for arg in args):
            try:
                arms.scoop(int(args[0]), int(args[1]))
            except ValueError as error:
                print(error)
                continue
        elif command == 'status':
            for board, stepper, name in arms.axes:
                print('%-17s %6d steps  %s' % (name, board.getCurrentPositionInSteps(stepper),
                                                board.getStepperStatus(stepper)))
            continue
        elif command:
            print(COMMANDS)
            continue
        run(arms)


if __name__ == '__main__':
    main()
