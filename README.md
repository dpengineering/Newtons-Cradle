# Newton's Cradle

A physical, robotic Newton's Cradle exhibit. Visitors use a touchscreen to
choose how many balls to pull back and release on each side; motorized
"scooper" arms grab, lift, and release the selected balls to demonstrate
conservation of momentum.

## Hardware

- **Raspberry Pi** running the Kivy touchscreen app.
- **4 stepper motors** across **two DPiStepper boards** (`dpeaDPi` library):
  - Board 0 = right arm, Board 1 = left arm.
  - On each board: stepper 0 = horizontal axis, stepper 1 = vertical axis.
- **Home/limit switches** on each axis, used by the homing routine.

## Running

The app runs as a **systemd service** (`newtons-cradle.service`) that launches
`main.py` at boot and restarts it automatically if it ever exits or crashes.

Install on the Pi (repo cloned to `/home/pi/Newtons-Cradle`):

```bash
sudo cp /home/pi/Newtons-Cradle/newtons-cradle.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now newtons-cradle.service
```

Useful commands:

```bash
systemctl status newtons-cradle.service      # is it running?
journalctl -u newtons-cradle.service -f      # live logs
sudo systemctl restart newtons-cradle.service
```

`main.py` loads its `.kv` files and `AdminScreen` using paths relative to the
repo root, so it must be run with the repo root as the working directory (the
service sets `WorkingDirectory=/home/pi/Newtons-Cradle`).

> Note: SDL logs harmless `EVDEV KeyCode 330 ... not recognized by SDL`
> messages — that code is the touchscreen's `BTN_TOUCH` event, which has no
> keyboard mapping. It has no effect on the app; the service filters these
> lines out of the logs.

## Code layout

| File | Purpose |
|------|---------|
| `main.py` | Kivy app: touchscreen UI, ball gesture logic, scoop orchestration. Entry point. |
| `stepper_hardware.py` | Hardware API over the two DPiStepper boards (`init_hardware`, `scoop`, `home`, `double_home`, `stop_balls`, ...). |
| `moveBothToHome.py` | Homing routines against the axis home switches. |
| `Kivy/` | `.kv` layouts, `AdminScreen`, and images. |
| `variables.json` | Runtime-tunable left/right offsets, written by the admin UI. |
| `newtons-cradle.service` | systemd unit that runs the app at boot. |
| `test_steppers.py` | CLI for driving/testing the steppers directly on the device. |
| `test_ui.py` | Runs the Kivy UI with hardware stubbed out (for machines without the boards). |

## Key functions (`stepper_hardware.py`)

- **`scoop(num_left, num_right)`** — scoops the requested number of balls on
  each side. If either side is 5, sides are staggered to avoid a collision.
- **`stop_balls(end_at_home=True)`** — halts ball momentum before a re-scoop so
  the arms can grab cleanly.
- **`home(board)` / `double_home()`** — home the steppers. `double_home` homes
  each arm's vertical and horizontal motors together (two at a time).
- **`quit_all()` / `admin_quit_all()`** — home, disable motors, and quit; the
  systemd service then restarts the app.

## UI

- Sliders/ball images limit selection so the two sides never sum to more than 5.
- Ball images change color to reflect how many are selected per side.

### Admin

- Invisible admin button in the bottom-right corner. Password: `7266`.
- **Restart** — homes, disables motors, and quits the app; the systemd service
  restarts it automatically. (Use this to reset a misbehaving session.)
- **Quit** — a true shutdown: homes, disables motors, then runs
  `systemctl stop newtons-cradle.service` so the app does **not** restart. The
  exhibit stays off until powered off or the service is started again.
- **Back** — re-homes the steppers and returns to the main screen.

#### Enabling the Quit button

The **Quit** button runs `sudo systemctl stop newtons-cradle.service`. For the
`pi` user to do that without a password prompt, add a sudoers rule (run once on
the Pi):

```bash
echo 'pi ALL=(root) NOPASSWD: /usr/bin/systemctl stop newtons-cradle.service' \
  | sudo tee /etc/sudoers.d/newtons-cradle >/dev/null \
  && sudo chmod 440 /etc/sudoers.d/newtons-cradle \
  && sudo visudo -c
```

To bring the exhibit back after a **Quit**, power-cycle it or run
`sudo systemctl start newtons-cradle.service`.
