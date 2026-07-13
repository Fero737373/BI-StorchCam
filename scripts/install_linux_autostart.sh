#!/usr/bin/env bash
set -euo pipefail

APP_NAME="BI-StorchCam"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DESKTOP_DIR="$HOME/.config/autostart"
DESKTOP_FILE="$DESKTOP_DIR/storchcam.desktop"
START_SCRIPT="$PROJECT_DIR/scripts/start_pi5_touch.sh"
DIAG_SCRIPT="$PROJECT_DIR/scripts/storchcam_diagnose.sh"

mkdir -p "$DESKTOP_DIR"
chmod +x "$START_SCRIPT"
[ -f "$DIAG_SCRIPT" ] && chmod +x "$DIAG_SCRIPT"

cat > "$DESKTOP_FILE" <<DESKTOP
[Desktop Entry]
Type=Application
Name=$APP_NAME
Exec=/bin/bash $START_SCRIPT
Terminal=false
X-GNOME-Autostart-enabled=true
DESKTOP

# Desktop-Autostartdateien werden gelesen, nicht ausgeführt. 0644 verhindert
# die systemd-xdg-autostart Warnung zu ausführbaren .desktop-Dateien.
chmod 644 "$DESKTOP_FILE"
echo "Autostart wurde erstellt: $DESKTOP_FILE"
echo "Startscript: $START_SCRIPT"
echo "Diagnose: $DIAG_SCRIPT"
