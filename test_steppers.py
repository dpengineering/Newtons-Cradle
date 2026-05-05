#!/usr/bin/env python3
"""Simple CLI to initialize and test the DPiStepper hardware.
Run this on the device with the steppers attached.
"""

import stepper_hardware as hardware


def print_menu():
    print("\nDPiStepper Test CLI")
    print("Commands:")
    print("  home <board>     - home steppers on specified board (0 or 1)")
    print("  double_home      - double_home()")
    print("  status           - print basic status of steppers")
    print("  move_h <mm>      - move both horizontals by mm")
    print("  move_v <mm>      - move both verticals by mm")
    print("  quit             - exit")


def safe_call(fn, *a, **k):
    try:
        return fn(*a, **k)
    except Exception as e:
        print("Error:", e)


def main():
    hardware.init_hardware()

    print("Hardware initialized. Use commands to test steppers.")
    print_menu()

    while True:
        try:
            cmd = input('> ').strip().split()
        except (EOFError, KeyboardInterrupt):
            print('\nExiting')
            break

        if not cmd:
            continue
        c = cmd[0]
        if c == 'quit' or c == 'q':
            hardware.dpiStepper1.enableMotors(False)
            hardware.dpiStepper0.enableMotors(False)
            break
        elif c == 'home' and len(cmd) == 2:
            try:
                board_num = int(cmd[1])
                safe_call(hardware.home, board=board_num)
            except ValueError:
                print('Invalid board number')
        elif c == 'double_home':
            safe_call(hardware.double_home)
        elif c == 'status':
            try:
                b1 = hardware.dpiStepper0.getStepperStatus(0)
                b2 = hardware.dpiStepper1.getStepperStatus(0)
                print('Stepper0 status 0:', b1)
                print('Stepper1 status 0:', b2)
            except Exception as e:
                print('Error reading status:', e)
        elif c == 'move_h' and len(cmd) == 2:
            try:
                mm = float(cmd[1])
                safe_call(hardware.set_horizontal_pos, mm)
            except ValueError:
                print('Invalid number')
        elif c == 'move_v' and len(cmd) == 2:
            try:
                mm = float(cmd[1])
                safe_call(hardware.set_vertical_pos, mm)
            except ValueError:
                print('Invalid number')
        else:
            print('Unknown command')
    


if __name__ == '__main__':
    main()
