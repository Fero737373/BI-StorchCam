#!/usr/bin/env bash
set -euo pipefail

DESKTOP_FILE="${XDG_CONFIG_HOME:-$HOME/.config}/autostart/bi-storchcam.desktop"
if [[ -f "$DESKTOP_FILE" ]]; then
  rm "$DESKTOP_FILE"
  echo "Fallback-Autostart entfernt: $DESKTOP_FILE"
else
  echo "Kein Fallback-Autostart vorhanden."
fi
