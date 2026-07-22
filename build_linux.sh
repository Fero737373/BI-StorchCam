#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m PyInstaller --clean --noconfirm BI-StorchCam.spec
"$ROOT/dist/BI-StorchCam" --test-config
echo "Build und Smoke-Test erfolgreich: $ROOT/dist/BI-StorchCam"
