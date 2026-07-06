#!/bin/bash
set -euo pipefail

APP_DIR="${APP_DIR:-$HOME/BI-StorchCam-work}"
LOG_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/BI-StorchCam"
LOG="$LOG_DIR/storchcam.log"
PROFILE_DIR="${STORCHCAM_PROFILE_DIR:-/tmp/storchcam-profile}"

mkdir -p "$LOG_DIR"

export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}"

{
  echo "===== BI-StorchCam Pi Start $(date) ====="
  echo "APP_DIR=$APP_DIR"
  echo "DISPLAY=$DISPLAY"
  echo "XAUTHORITY=$XAUTHORITY"
  echo "PROFILE_DIR=$PROFILE_DIR"

  if [ ! -d "$APP_DIR" ]; then
    echo "FEHLER: APP_DIR existiert nicht: $APP_DIR"
    exit 1
  fi

  cd "$APP_DIR"

  if [ ! -f launcher.py ]; then
    echo "FEHLER: launcher.py fehlt in $APP_DIR"
    exit 1
  fi

  if [ ! -f bi_storchcam/web/index.html ]; then
    echo "FEHLER: bi_storchcam/web/index.html fehlt in $APP_DIR"
    exit 1
  fi

  # Alte Kiosk-/Legacy-Prozesse entfernen, damit nach einem Reboot nicht mehrere
  # StorchCam-Generationen parallel laufen oder ein alter Chromium-Tab hängen bleibt.
  pkill -f "chromium.*storchcam-profile" 2>/dev/null || true
  pkill -f "$HOME/storch.sh" 2>/dev/null || true
  pkill -f "$HOME/storch_data.py" 2>/dev/null || true

  # Chromium-Singleton-Dateien können nach einem Crash/Black-Screen den nächsten
  # sauberen Kiosk-Start blockieren. Der Profilinhalt bleibt ansonsten erhalten.
  rm -f "$PROFILE_DIR"/SingletonCookie "$PROFILE_DIR"/SingletonLock "$PROFILE_DIR"/SingletonSocket 2>/dev/null || true

  echo "Starte BI-StorchCam über launcher.py"
  exec python3 launcher.py --kiosk
} >> "$LOG" 2>&1
