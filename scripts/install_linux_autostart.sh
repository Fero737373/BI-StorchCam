#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AUTOSTART_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"
DESKTOP_FILE="$AUTOSTART_DIR/bi-storchcam.desktop"
START_SCRIPT="$APP_DIR/scripts/start_pi5_touch.sh"

mkdir -p "$AUTOSTART_DIR"
chmod 0755 "$START_SCRIPT"
cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=BI-StorchCam (Fallback)
Comment=Optionaler Desktop-Autostart; systemd-User-Service wird empfohlen
Exec=/bin/bash "$START_SCRIPT"
Terminal=false
X-GNOME-Autostart-enabled=true
EOF
chmod 0644 "$DESKTOP_FILE"
echo "Fallback-Autostart installiert: $DESKTOP_FILE"
echo "Für produktiven Betrieb empfohlen: bash $APP_DIR/scripts/install_systemd_user.sh"
