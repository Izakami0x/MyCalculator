@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Run INSTALL_AND_RUN.bat once first so the private environment exists.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check pyinstaller
if errorlevel 1 goto :fail
rem One-folder build: starts faster and triggers fewer antivirus false positives than --onefile.
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --windowed --name IzakamiRiskCalculator --paths src run.py
if errorlevel 1 goto :fail
echo.
echo Done. Run: dist\IzakamiRiskCalculator\IzakamiRiskCalculator.exe
pause
exit /b 0
:fail
echo Build failed.
pause
exit /b 1
