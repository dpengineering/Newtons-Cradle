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
    print("  move_right <mm>    - move right horizontal by mm")
    print("  move_left <mm>     - move left horizontal by mm")
    print("  move_v <mm>      - move both verticals by mm")
    print("  quit             - exit")
    print(" --------- User Commands --------- ")
    print("  reset_scoops            - reset positions to 0")
    print("  reset_balls             - reset balls to initial position")
    print("  scoop <num_l> <num_r>   - scoop num_left and num_right balls")


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
        elif c == 'reset_scoops':
            safe_call(hardware.back_to_home)
        elif c == 'reset_balls':
            safe_call(hardware.stop_balls)
        elif c == 'scoop' and len(cmd) == 3:
            try:
                num_left = int(cmd[1])
                num_right = int(cmd[2])
                safe_call(hardware.scoop_both, num_left, num_right)
            except ValueError:
                print('Invalid numbers')
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
        elif c == 'move_right' and len(cmd) == 2:
            try:
                mm = float(cmd[1])
                safe_call(hardware.set_horizontal_pos_right, mm)
            except ValueError:
                print('Invalid number')
        elif c == 'move_left' and len(cmd) == 2:
            try:
                mm = float(cmd[1])
                safe_call(hardware.set_horizontal_pos_left, mm)
            except ValueError:
                print('Invalid number')
        else:
            print('Unknown command')
    


if __name__ == '__main__':
    main()
