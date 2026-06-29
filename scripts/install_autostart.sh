#!/bin/bash
set -e

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AUTOSTART_DIR="$HOME/.config/autostart"
DESKTOP_FILE="$AUTOSTART_DIR/storchcam.desktop"
mkdir -p "$AUTOSTART_DIR"
chmod +x "$APP_DIR/scripts/start_pi5_touch.sh" || true

{
  echo "[Desktop Entry]"
  echo "Type=Application"
  echo "Name=BI-StorchCam"
  echo "Exec=/bin/bash $APP_DIR/scripts/start_pi5_touch.sh"
  echo "Terminal=false"
  echo "X-GNOME-Autostart-enabled=true"
} > "$DESKTOP_FILE"

echo "Autostart installiert: $DESKTOP_FILE"
echo "Startscript: $APP_DIR/scripts/start_pi5_touch.sh"
