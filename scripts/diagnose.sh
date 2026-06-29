#!/bin/bash
set -u
OUT="$HOME/storchcam_diag_$(date +%Y%m%d_%H%M%S).txt"
{
  echo "===== SYSTEM ====="
  date
  hostname
  whoami
  uname -a
  cat /etc/os-release 2>/dev/null || true
  echo
  echo "===== DISPLAY ====="
  echo "DISPLAY=${DISPLAY:-LEER}"
  echo "WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-LEER}"
  echo "XDG_SESSION_TYPE=${XDG_SESSION_TYPE:-LEER}"
  DISPLAY=:0 XAUTHORITY="$HOME/.Xauthority" xrandr 2>/dev/null || true
  DISPLAY=:0 XAUTHORITY="$HOME/.Xauthority" xinput list 2>/dev/null || true
  echo
  echo "===== PYTHON TESTS ====="
  python3 --version
  python3 -m py_compile STORCH-CAM.py bi_storchcam/*.py bi_storchcam/providers/*.py
  python3 STORCH-CAM.py --test-weather || true
  python3 STORCH-CAM.py --test-transit || true
  python3 STORCH-CAM.py --test-radar || true
  echo
  echo "===== PROCESSES ====="
  ps aux | grep -Ei 'storch|chromium|http.server' | grep -v grep || true
} | tee "$OUT"
echo "Diagnose gespeichert: $OUT"
