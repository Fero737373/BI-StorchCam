#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${BI_STORCHCAM_PYTHON:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  if [[ -x "$APP_DIR/.venv/bin/python" ]]; then
    PYTHON_BIN="$APP_DIR/.venv/bin/python"
  else
    PYTHON_BIN="$(command -v python3)"
  fi
fi

cd "$APP_DIR"
exec "$PYTHON_BIN" launcher.py
