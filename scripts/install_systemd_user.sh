#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
UNIT_FILE="$UNIT_DIR/bi-storchcam.service"
CONFIG_FILE="$HOME/.config/BI-StorchCam/config.json"
RUNTIME_DIR="/run/user/$(id -u)"
DISPLAY_VALUE="${DISPLAY:-:0}"
XAUTHORITY_VALUE="${XAUTHORITY:-$HOME/.Xauthority}"

if [[ -x "$APP_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$APP_DIR/.venv/bin/python"
else
  PYTHON_BIN="$(command -v python3)"
fi

mkdir -p "$UNIT_DIR" "$(dirname "$CONFIG_FILE")"
cat > "$UNIT_FILE" <<EOF
[Unit]
Description=BI-StorchCam web kiosk
Wants=network-online.target
After=network-online.target graphical-session.target
StartLimitIntervalSec=120
StartLimitBurst=8

[Service]
Type=simple
WorkingDirectory=$APP_DIR
ExecStart=$PYTHON_BIN $APP_DIR/scripts/start_storchcam.py
Restart=always
RestartSec=5
TimeoutStopSec=15
KillMode=mixed
Environment=HOME=$HOME
Environment=XDG_CONFIG_HOME=$HOME/.config
Environment=BI_STORCHCAM_CONFIG=$CONFIG_FILE
Environment=BI_STORCHCAM_CONSOLE_CONTROL=/home/fero/KonsolenDocker/bin/console-control
Environment=PYTHONUNBUFFERED=1
Environment=DISPLAY=$DISPLAY_VALUE
Environment=XAUTHORITY=$XAUTHORITY_VALUE
Environment=XDG_RUNTIME_DIR=$RUNTIME_DIR
Environment=XDG_SESSION_TYPE=x11
UnsetEnvironment=PYTHONHOME PYTHONPATH

[Install]
WantedBy=default.target
EOF

chmod 0644 "$UNIT_FILE"
systemctl --user daemon-reload
systemctl --user reset-failed bi-storchcam.service 2>/dev/null || true
systemctl --user enable --now bi-storchcam.service

echo "systemd-User-Service installiert und gestartet: $UNIT_FILE"
echo "Konfiguration: $CONFIG_FILE"
echo "Status: systemctl --user status bi-storchcam.service"
