@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Run INSTALL_AND_RUN.bat once first so the runtime environment exists.
    pause
    exit /b 1
)
if not exist ".build-venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m venv ".build-venv"
    if errorlevel 1 goto :fail
)
".build-venv\Scripts\python.exe" -m pip install --disable-pip-version-check --no-cache-dir -r requirements-dev.txt
if errorlevel 1 goto :fail
rem Keep build and test tools out of the normal runtime environment.
".build-venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --windowed --name IzakamiRiskCalculator --paths src run.py
if errorlevel 1 goto :fail
echo.
echo Done. Run: dist\IzakamiRiskCalculator\IzakamiRiskCalculator.exe
pause
exit /b 0
:fail
echo Build failed.
pause
exit /b 1
