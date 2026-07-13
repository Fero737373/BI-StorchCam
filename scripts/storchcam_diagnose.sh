#!/usr/bin/env bash
set -u

APP_DIR="${APP_DIR:-$HOME/BI-StorchCam-work}"
CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/BI-StorchCam"
STAMP="$(date +%Y-%m-%d_%H-%M-%S)"
REPORT="$CACHE_DIR/diagnose-$STAMP.log"

mkdir -p "$CACHE_DIR"

{
  echo "========== BI-STORCHCAM DIAGNOSE =========="
  date
  echo "APP_DIR=$APP_DIR"
  echo

  echo "========== SYSTEM =========="
  uname -a
  uptime
  free -h
  df -h /
  command -v vcgencmd >/dev/null 2>&1 && vcgencmd measure_temp || true
  command -v vcgencmd >/dev/null 2>&1 && vcgencmd get_throttled || true
  echo

  echo "========== PROZESSE =========="
  ps -eo pid,ppid,stat,etime,cmd | grep -E 'launcher\.py|BI-StorchCam|storchcam-profile|chromium|chrome' | grep -v grep || echo "Keine StorchCam-/Browser-Prozesse gefunden"
  echo

  echo "========== PORT 8000 =========="
  ss -lntp 2>/dev/null | grep ':8000' || echo "Port 8000 ist nicht geöffnet"
  echo

  echo "========== STATE API =========="
  curl --max-time 5 -sS -i http://127.0.0.1:8000/api/state || true
  echo
  echo

  echo "========== AUTOSTART =========="
  AUTOSTART="$HOME/.config/autostart/storchcam.desktop"
  if [ -f "$AUTOSTART" ]; then
    ls -l "$AUTOSTART"
    cat "$AUTOSTART"
  else
    echo "Autostart-Datei fehlt: $AUTOSTART"
  fi
  echo

  echo "========== APP LOG =========="
  APP_LOG="$CACHE_DIR/storchcam.log"
  if [ -f "$APP_LOG" ]; then
    tail -n 250 "$APP_LOG"
  else
    echo "App-Log fehlt: $APP_LOG"
  fi
  echo

  echo "========== CHROMIUM LOG =========="
  BROWSER_LOG="$CACHE_DIR/chromium.log"
  if [ -f "$BROWSER_LOG" ]; then
    tail -n 300 "$BROWSER_LOG"
  else
    echo "Chromium-Log fehlt: $BROWSER_LOG"
  fi
  echo

  echo "========== LETZTE SYSTEMWARNUNGEN =========="
  journalctl -b -p warning..alert -n 200 --no-pager 2>/dev/null || true
  echo

  echo "========== KERNELWARNUNGEN =========="
  dmesg --level=err,warn 2>/dev/null | tail -n 150 || true
  echo

  echo "========== GIT-STAND =========="
  if [ -d "$APP_DIR/.git" ]; then
    git -C "$APP_DIR" status -sb
    git -C "$APP_DIR" log -1 --oneline
  else
    echo "Kein Git-Repository unter $APP_DIR"
  fi
  echo

  echo "========== ENDE =========="
} 2>&1 | tee "$REPORT"

echo
echo "Diagnose gespeichert unter: $REPORT"
