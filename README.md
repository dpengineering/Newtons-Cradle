# Newton's Cradle

A physical, robotic Newton's Cradle exhibit. Visitors use a touchscreen to
choose how many balls to pull back and release on each side; motorized
"scooper" arms grab, lift, and release the selected balls to demonstrate
conservation of momentum.

## Hardware

- **Raspberry Pi** running the Kivy touchscreen app.
- **4 stepper motors** across **two DPiStepper boards** (`dpeaDPi` library). A
  board has three drivers, so the four motors need both:
  - Board 0 = right arm, Board 1 = left arm.
  - On each board: stepper 0 = horizontal axis, stepper 1 = vertical axis.
- **Home/limit switches** on each axis, used by the homing routine.

## Running

The app runs as a **systemd service** (`newtons-cradle.service`) that launches
`main.py` at boot and restarts it automatically if it ever exits or crashes.

Install on the Pi (repo cloned to `/home/pi/Newtons-Cradle`):

Dependencies are pinned in `pyproject.toml` / `uv.lock` and installed with
[uv](https://docs.astral.sh/uv/) into `.venv/`, which the service runs from.

```bash
cd /home/pi/Newtons-Cradle && uv sync --locked --no-dev

# One-time: create this machine's live tuning file from the template.
cp /home/pi/Newtons-Cradle/variables.example.json /home/pi/Newtons-Cradle/variables.json

sudo cp /home/pi/Newtons-Cradle/newtons-cradle.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now newtons-cradle.service
```

`variables.json` holds this exhibit's live tuning (offsets + cooldown) and is
written by the admin page, so it is **git-ignored** — each machine keeps its own
and `git pull` never overwrites it. `variables.example.json` is the tracked
default to copy from.

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

## Tests

```bash
uv sync --locked
uv run pytest
```

`tests/` runs the arms, the exhibit state machine and the Kivy screens against
`dpeaDPi`'s `SimulatedDPiStepper`, which replays the board firmware's
acceleration ramp, with each axis's home switch mounted at position 0. No
boards are needed.

To try the touchscreen without the boards, run the app against the simulator in
real time:

```bash
uv run python run_simulated.py
```

## Code layout

| File | Purpose |
|------|---------|
| `main.py` | Entry point. Kivy screens, ball gestures, and the admin screens, driven by `Exhibit`. |
| `exhibit.py` | `Exhibit`, the visitor-facing state machine. Each `Phase` has fixed outputs (label, whether touches count, motor power) and starts that phase's arm motion. |
| `arms.py` | `CradleArms`, the two scooper arms over two `StepperDriver` boards: homing, `stop_balls` and `scoop` as plans of motion steps. |
| `motion.py` | `MotionRunner`, which runs a plan one step at a time without blocking, and the step parts (`MoveTo`, `SeekSwitch`, `Settle`, `Do`). |
| `config.py` | Geometry, speeds and homing constants, and `Tuning`, the validated per-machine trims stored in `variables.json`. |
| `Kivy/` | `.kv` layouts, `AdminScreen`, and images. |
| `variables.json` | Per-machine live tuning (offsets + cooldown), written by the admin UI. Git-ignored; copied from `variables.example.json`. |
| `variables.example.json` | Tracked default template for `variables.json`. |
| `newtons-cradle.service` | systemd unit that runs the app at boot. |
| `stepper_cli.py` | CLI for homing, scooping and reading the axes by hand on the device. |
| `run_simulated.py` | Runs the app against simulated boards in real time, for machines without them. |

## How it runs

Everything runs on Kivy's main loop and nothing sleeps. Each frame calls
`Exhibit.tick()`, which polls the boards and moves to the next step or phase
once the current one is done. A visitor's scoop goes:

`READY` -> `PREPARING` (re-home only if an axis isn't at 0 on a closed switch)
-> `STOPPING_BALLS` -> `SCOOPING` -> `CHECKING_HOME` (re-home if an arm came
back short) -> `COOLDOWN` (motors off) -> `READY`.

Any board error or motion timeout turns the motors off and ends the app, and
systemd restarts it, which homes again on startup.

## UI

- Tap a ball to pull it and its outer neighbours to the nearer side (the middle
  ball goes right), or swipe it either way. Tap a pulled ball to lower it.
- At most 4 balls go to one side and 5 in total, and the outermost ball on each
  side can't be pulled across.

### Admin

- Invisible admin button in the bottom-right corner. Password: `7266`.
- **Restart** — stops any motion, homes, disables motors, and quits the app;
  the systemd service restarts it automatically. (Use this to reset a
  misbehaving session.)
- **Quit** — a true shutdown: stops any motion, homes, disables motors, then
  runs `systemctl stop newtons-cradle.service` so the app does **not** restart.
  The exhibit stays off until powered off or the service is started again.
- **Back** — stops any motion, re-homes the steppers, and returns to the main
  screen.

#### Tuning offsets and cooldown

The `+`/`−` controls at the top of the admin screen adjust live values that are
saved to `variables.json` and used from the next move on. A press that would
break a limit below is ignored:

- **`offset_left` / `offset_right`** — horizontal trim (mm) for each arm's
  pickup and release points. Defaults 9 (right) / −4 (left). Must keep the
  one-ball release point (60 mm) in front of home.
- **`offset_v_left` / `offset_v_right`** — vertical trim (mm) added to each arm's
  lift height. Defaults 0. Must keep the lift above 0.
- **`cooldown_secs`** — seconds the balls swing after a scoop before the next
  visitor can start one. Stored as `COOLDOWN_SECS`. Can't go below 0.

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
