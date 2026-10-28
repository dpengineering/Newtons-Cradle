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

## Set up the exhibit Pi

The Pi runs the DPEA Raspberry Pi image. The exhibit runs from a clean checkout
in `/opt/dpea/Newtons-Cradle` that tracks `main`. Develop in a separate checkout,
such as `~/src/Newtons-Cradle`.

Create a read-only deploy key on the Pi:

```bash
ssh-keygen -t ed25519 -N "" -C "newtons-cradle-pi" -f ~/.ssh/newtons_cradle_deploy
cat ~/.ssh/newtons_cradle_deploy.pub
```

Add the public key under the repository's Settings > Deploy keys with write
access left off. Then add this to `~/.ssh/config`:

```text
Host github-newtons-cradle
    HostName github.com
    User git
    IdentityFile ~/.ssh/newtons_cradle_deploy
    IdentitiesOnly yes
```

Clone the development checkout and run setup:

```bash
git clone git@github-newtons-cradle:dpengineering/Newtons-Cradle.git ~/src/Newtons-Cradle
~/src/Newtons-Cradle/deploy/setup.sh
sudo reboot
```

Setup clones the exhibit checkout, installs its dependencies, enables the
`newtons-cradle-update` and `newtons-cradle` services, lets the admin Quit button
stop the service, logs into the desktop at boot, and turns off screen blanking.
Run it again after changing anything in `deploy/systemd`.

On each boot, `newtons-cradle-update` fetches `main` and resets the exhibit
checkout to it. Without internet the exhibit runs the code it already has. If
the new commit's dependencies fail to install, it returns to the previous
commit. `newtons-cradle` then runs `main.py` on the desktop. If the app crashes
it stays off until the exhibit is power-cycled.

`variables.json` holds this exhibit's tuning from the admin screen. It is
git-ignored, so updates never touch it, and the app uses the defaults in
`config.py` until the admin screen saves one. When moving an exhibit to this
setup, copy its old `variables.json` into `/opt/dpea/Newtons-Cradle/`.

The exhibit holds the DPi boards. Stop it before running the development
checkout against the hardware:

```bash
sudo systemctl stop newtons-cradle
```

Read the logs, including why the app stopped:

```bash
journalctl -u newtons-cradle-update -b
journalctl -u newtons-cradle -b
```

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
| `variables.json` | Per-machine live tuning (offsets + cooldown), written by the admin UI. Git-ignored. |
| `variables.example.json` | Tracked default template for `variables.json`. |
| `deploy/` | `setup.sh`, the boot-time `update.sh`, and the systemd units that run the exhibit from `/opt`. |
| `stepper_cli.py` | CLI for homing, scooping and reading the axes by hand on the device. |
| `run_simulated.py` | Runs the app against simulated boards in real time, for machines without them. |

## How it runs

Everything runs on Kivy's main loop and nothing sleeps. Each frame calls
`Exhibit.tick()`, which polls the boards and moves to the next step or phase
once the current one is done. A visitor's scoop goes:

`READY` -> `PREPARING` (re-home only if an axis isn't at 0 on a closed switch)
-> `STOPPING_BALLS` -> `SCOOPING` -> `CHECKING_HOME` (re-home if an arm came
back short) -> `COOLDOWN` (motors off) -> `READY`.

Any board error or motion timeout turns the motors off and ends the app, which
stays off until the exhibit is power-cycled.

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
  The exhibit stays off until it is power-cycled.
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
