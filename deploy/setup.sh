#!/bin/bash
set -euo pipefail

REPO=git@github-newtons-cradle:dpengineering/Newtons-Cradle.git
EXHIBIT_DIR=/opt/dpea/Newtons-Cradle
SERVICE=newtons-cradle.service

fail() {
	echo "$1" >&2
	exit 1
}

# Stop early if this Pi is missing anything the exhibit needs. The boards talk RS485 over /dev/serial0.
[[ $EUID -ne 0 ]] || fail "Run setup.sh as the exhibit user, not root."
command -v uv >/dev/null || fail "uv is missing. Flash the DPEA Raspberry Pi image."
[[ -e /dev/serial0 ]] || fail "/dev/serial0 is missing. Enable the serial port in raspi-config."
for group in dialout video input; do
	id -nG | grep -qw "$group" || fail "$USER is not in the $group group."
done

# Clone the exhibit checkout over the deploy key, or reuse one that already pulls from this repo.
if [[ -d $EXHIBIT_DIR/.git ]]; then
	origin=$(git -C "$EXHIBIT_DIR" remote get-url origin)
	[[ $origin == "$REPO" ]] || fail "$EXHIBIT_DIR pulls from $origin, expected $REPO."
else
	sudo install -d -o "$USER" -g "$(id -gn)" "$(dirname "$EXHIBIT_DIR")"
	git clone "$REPO" "$EXHIBIT_DIR"
fi
# Install the exact pinned dependencies into the checkout's .venv.
(cd "$EXHIBIT_DIR" && uv sync --locked --no-dev)

# Fill in this Pi's user and checkout path, install both systemd units, and start them on every boot.
for unit in newtons-cradle-update.service "$SERVICE"; do
	sed -e "s|@USER@|$USER|g" -e "s|@EXHIBIT_DIR@|$EXHIBIT_DIR|g" "$EXHIBIT_DIR/deploy/systemd/$unit" \
		| sudo tee "/etc/systemd/system/$unit" >/dev/null
done
sudo systemctl daemon-reload
sudo systemctl enable newtons-cradle-update.service "$SERVICE"

# Let the admin Quit button stop the service without a password; visudo checks the rule before it goes live.
sudoers=$(mktemp)
echo "$USER ALL=(root) NOPASSWD: /usr/bin/systemctl stop $SERVICE" >"$sudoers"
sudo visudo -cqf "$sudoers"
sudo install -m 440 "$sudoers" /etc/sudoers.d/newtons-cradle
rm "$sudoers"

# Boot straight into the desktop the app draws on, and never blank the screen.
sudo raspi-config nonint do_boot_behaviour B4
sudo raspi-config nonint do_blanking 1

echo "Setup complete. Reboot to start the exhibit."
