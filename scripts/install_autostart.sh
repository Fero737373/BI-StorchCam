#!/bin/bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AUTOSTART_DIR="$HOME/.config/autostart"
DESKTOP_FILE="$AUTOSTART_DIR/storchcam.desktop"
START_SCRIPT="$APP_DIR/scripts/start_pi5_touch.sh"

mkdir -p "$AUTOSTART_DIR"
chmod +x "$START_SCRIPT"

cat > "$DESKTOP_FILE" <<DESKTOP
[Desktop Entry]
Type=Application
Name=BI-StorchCam
Exec=/bin/bash $START_SCRIPT
Terminal=false
X-GNOME-Autostart-enabled=true
DESKTOP

chmod +x "$DESKTOP_FILE"
echo "Autostart installiert: $DESKTOP_FILE"
echo "Startscript: $START_SCRIPT"
