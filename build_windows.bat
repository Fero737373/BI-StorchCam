@echo off
setlocal
cd /d "%~dp0"
if not exist .venv py -3 -m venv .venv || exit /b 1
call .venv\Scripts\activate.bat || exit /b 1
python -m pip install --upgrade pip || exit /b 1
python -m pip install -r requirements.txt || exit /b 1
python -m PyInstaller --clean --noconfirm BI-StorchCam.spec || exit /b 1
dist\BI-StorchCam.exe --test-config || exit /b 1
echo Build und Smoke-Test erfolgreich: %CD%\dist\BI-StorchCam.exe
exit /b 0
