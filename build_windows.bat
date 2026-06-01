@echo off
setlocal

echo == BI-StorchCam Windows Build ==

if not exist .venv (
    py -3 -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

pyinstaller ^
  --onefile ^
  --windowed ^
  --name BI-StorchCam ^
  --clean ^
  launcher.py

echo.
echo Fertig. EXE liegt in dist\BI-StorchCam.exe
pause
