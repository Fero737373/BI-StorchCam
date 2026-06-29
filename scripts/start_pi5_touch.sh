#!/bin/bash
set -e

APP_DIR="${APP_DIR:-$HOME/BI-StorchCam-work}"
LOG_DIR="$HOME/.cache/BI-StorchCam"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/storchcam.log"

export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}"

cd "$APP_DIR"

echo "===== Start $(date) =====" >> "$LOG"
python3 STORCH-CAM.py --kiosk >> "$LOG" 2>&1
