#!/usr/bin/env bash
set -e

APP_NAME="BI-StorchCam"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DESKTOP_DIR="$HOME/.config/autostart"
DESKTOP_FILE="$DESKTOP_DIR/bi-storchcam.desktop"

mkdir -p "$DESKTOP_DIR"

cat > "$DESKTOP_FILE" <<DESKTOP
[Desktop Entry]
Type=Application
Name=$APP_NAME
Exec=/bin/bash -lc 'cd "$PROJECT_DIR" && if [ -x dist/BI-StorchCam ]; then ./dist/BI-StorchCam; else python3 launcher.py; fi'
Terminal=false
X-GNOME-Autostart-enabled=true
DESKTOP

chmod +x "$DESKTOP_FILE"
echo "Autostart wurde erstellt: $DESKTOP_FILE"
