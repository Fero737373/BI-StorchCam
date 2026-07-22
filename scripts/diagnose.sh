#!/usr/bin/env bash
set -u

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$APP_DIR"
CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/BI-StorchCam"
CONFIG_FILE="${BI_STORCHCAM_CONFIG:-${XDG_CONFIG_HOME:-$HOME/.config}/BI-StorchCam/config.json}"
STAMP="$(date +%Y%m%d-%H%M%S)"
REPORT="$CACHE_DIR/diagnose-$STAMP.txt"
mkdir -p "$CACHE_DIR"

section() { echo; echo "===== $1 ====="; }
redacted_config() {
  python3 - "$CONFIG_FILE" <<'PY'
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
if not path.exists():
    print("Konfiguration fehlt:", path)
    raise SystemExit
try:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data.get("admin"), dict) and data["admin"].get("pin_hash"):
        data["admin"]["pin_hash"] = "<REDACTED>"
    print(json.dumps(data, ensure_ascii=False, indent=2))
except Exception as exc:
    print("Konfiguration nicht lesbar:", exc)
PY
}

{
  section "BI-STORCHCAM"
  date --iso-8601=seconds 2>/dev/null || date
  echo "Projekt: $APP_DIR"
  echo "Konfiguration: $CONFIG_FILE"
  python3 -m bi_storchcam --test-config 2>&1 || true

  section "SYSTEM"
  uname -a
  [[ -f /etc/os-release ]] && cat /etc/os-release
  echo "Architektur: $(uname -m)"
  python3 --version
  df -h "$APP_DIR" "$CACHE_DIR" 2>/dev/null || true
  free -h 2>/dev/null || true
  command -v vcgencmd >/dev/null && vcgencmd get_throttled || true
  command -v vcgencmd >/dev/null && vcgencmd measure_temp || true

  section "BROWSER"
  for browser in chromium chromium-browser google-chrome google-chrome-stable microsoft-edge msedge; do
    command -v "$browser" 2>/dev/null || true
  done

  section "SITZUNG UND DISPLAY"
  echo "XDG_SESSION_TYPE=${XDG_SESSION_TYPE:-<leer>}"
  echo "DISPLAY=${DISPLAY:-<leer>}"
  echo "WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-<leer>}"
  command -v xrandr >/dev/null && xrandr --query 2>&1 || true
  command -v xinput >/dev/null && xinput list 2>&1 || true

  section "PORT UND API"
  ss -ltnp 2>/dev/null | grep ':8000' || echo "Port 8000 nicht gebunden"
  curl --max-time 5 -fsS http://127.0.0.1:8000/api/health 2>&1 || true
  echo
  curl --max-time 5 -fsS http://127.0.0.1:8000/api/state 2>&1 || true

  section "SYSTEMD"
  systemctl --user status bi-storchcam.service --no-pager 2>&1 || true
  journalctl --user -u bi-storchcam.service -n 120 --no-pager 2>&1 || true

  section "PROZESSE"
  ps -eo pid,ppid,stat,etime,%cpu,%mem,cmd | grep -E 'BI-StorchCam|launcher.py|bi_storchcam|chromium|chrome|msedge' | grep -v grep || true

  section "BERECHTIGUNGEN"
  ls -ld "$APP_DIR" "$CACHE_DIR" "$(dirname "$CONFIG_FILE")" 2>&1 || true
  ls -l "$CONFIG_FILE" "$CONFIG_FILE.bak" 2>&1 || true

  section "KONFIGURATION REDAKTIERT"
  redacted_config

  section "APP-LOG"
  tail -n 250 "$CACHE_DIR/storchcam.log" 2>&1 || true

  section "BROWSER-LOG"
  tail -n 250 "$CACHE_DIR/chromium.log" 2>&1 || true
} > "$REPORT" 2>&1

cat "$REPORT"
echo
echo "Diagnose gespeichert: $REPORT"
