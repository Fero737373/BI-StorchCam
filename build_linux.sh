#!/usr/bin/env bash
set -e

echo "== BI-StorchCam Linux Build =="

if [ ! -d .venv ]; then
    python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

pyinstaller \
  --onefile \
  --windowed \
  --name BI-StorchCam \
  --clean \
  launcher.py

echo
echo "Fertig. Binary liegt in dist/BI-StorchCam"
