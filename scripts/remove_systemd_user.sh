#!/usr/bin/env bash
set -euo pipefail

UNIT_FILE="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user/bi-storchcam.service"
systemctl --user disable --now bi-storchcam.service 2>/dev/null || true
if [[ -f "$UNIT_FILE" ]]; then
  rm "$UNIT_FILE"
fi
systemctl --user daemon-reload
systemctl --user reset-failed bi-storchcam.service 2>/dev/null || true
echo "BI-StorchCam systemd-User-Service entfernt. Konfiguration und Logs bleiben erhalten."
