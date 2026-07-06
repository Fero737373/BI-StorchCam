#!/usr/bin/env bash
set -euo pipefail

PORT="${1:-5901}"
LOG_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/BI-StorchCam"
LOG="$LOG_DIR/vnc.log"
mkdir -p "$LOG_DIR"

export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}"

echo "===== BI-StorchCam VNC Helper $(date) =====" | tee -a "$LOG"
echo "DISPLAY=$DISPLAY" | tee -a "$LOG"
echo "XAUTHORITY=$XAUTHORITY" | tee -a "$LOG"
echo "PORT=$PORT" | tee -a "$LOG"

if ! command -v x11vnc >/dev/null 2>&1; then
  echo "x11vnc fehlt. Installiere Paket ..." | tee -a "$LOG"
  sudo apt update
  sudo apt install -y x11vnc
fi

if ! DISPLAY="$DISPLAY" XAUTHORITY="$XAUTHORITY" xset q >/dev/null 2>&1; then
  echo "WARNUNG: Display $DISPLAY ist nicht erreichbar. Prüfe lokalen Desktop/Autologin." | tee -a "$LOG"
fi

# Alte x11vnc-Instanzen beenden, damit der Port frei ist.
pkill -f "x11vnc.*-rfbport" 2>/dev/null || true

# Ohne gespeichertes Passwort starten: nur im lokalen LAN verwenden.
# Für dauerhaften Betrieb besser: x11vnc -storepasswd und dann -rfbauth nutzen.
echo "Starte x11vnc auf Port $PORT ..." | tee -a "$LOG"
nohup x11vnc \
  -display "$DISPLAY" \
  -auth "$XAUTHORITY" \
  -rfbport "$PORT" \
  -forever \
  -shared \
  -noxdamage \
  -repeat \
  -nopw \
  >> "$LOG" 2>&1 &

sleep 2
ss -ltnp 2>/dev/null | grep -E ":$PORT" || true
echo "VNC läuft, wenn oben LISTEN auf :$PORT steht." | tee -a "$LOG"
echo "MobaXterm: Session -> VNC -> Remote host: Pi-IP -> Port: $PORT" | tee -a "$LOG"
echo "Log: $LOG" | tee -a "$LOG"
