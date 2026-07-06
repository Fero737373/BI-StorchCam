#!/usr/bin/env bash
set -euo pipefail

APP_NAME="BI-StorchCam"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DESKTOP_DIR="$HOME/.config/autostart"
DESKTOP_FILE="$DESKTOP_DIR/storchcam.desktop"
START_SCRIPT="$PROJECT_DIR/scripts/start_pi5_touch.sh"

mkdir -p "$DESKTOP_DIR"
chmod +x "$START_SCRIPT"

cat > "$DESKTOP_FILE" <<DESKTOP
[Desktop Entry]
Type=Application
Name=$APP_NAME
Exec=/bin/bash $START_SCRIPT
Terminal=false
X-GNOME-Autostart-enabled=true
DESKTOP

chmod +x "$DESKTOP_FILE"
echo "Autostart wurde erstellt: $DESKTOP_FILE"
echo "Startscript: $START_SCRIPT"
