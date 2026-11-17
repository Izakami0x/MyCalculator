@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Izakami Risk Calculator - Setup
set "LOG=%~dp0install.log"
echo [%date% %time%] Setup started > "%LOG%"

rem --- find Python 3.11+ -------------------------------------------------------
set "PYCMD="
where py >nul 2>&1
if not errorlevel 1 (
    py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)" >nul 2>&1
    if not errorlevel 1 set "PYCMD=py -3"
)
if not defined PYCMD (
    where python >nul 2>&1
    if not errorlevel 1 (
        python -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)" >nul 2>&1
        if not errorlevel 1 set "PYCMD=python"
    )
)
if not defined PYCMD (
    echo.
    echo Python 3.11 or newer was not found.
    echo Install it from https://www.python.org/downloads/ ^(tick "Add python.exe to PATH"^)
    echo and run this file again.
    echo Python 3.11+ not found >> "%LOG%"
    if not "%IZAKAMI_SILENT%"=="1" pause
    exit /b 1
)
echo Using: %PYCMD% >> "%LOG%"
%PYCMD% -c "import sys; print(sys.executable); print(sys.version)" >> "%LOG%" 2>&1

rem --- anything built in another folder (or half-built) is thrown away ----------
set "READY="
if exist ".izakami_ready" set /p READY=<".izakami_ready"
if /i not "%READY%"=="%~dp0" (
    if exist ".venv" rmdir /s /q ".venv"
    if exist "libs" rmdir /s /q "libs"
    del /q ".izakami_ready" "launch.cmd" >nul 2>&1
)

rem --- preferred: a private virtual environment ----------------------------------
if not exist ".venv\Scripts\python.exe" (
    echo Creating a private virtual environment...
    %PYCMD% -m venv ".venv" >> "%LOG%" 2>&1
)
rem A venv that cannot start ^(e.g. "failed to locate pyvenv.cfg"^) is useless: detect it here.
".venv\Scripts\python.exe" -c "import sys" >> "%LOG%" 2>&1
if errorlevel 1 goto :novenv

echo Installing dependencies. The first run can take a few minutes...
".venv\Scripts\python.exe" -m pip uninstall -y PySide6 PySide6_Addons PySide6_WebEngine PySide6_Pdf >> "%LOG%" 2>&1
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check --no-cache-dir -r requirements.txt >> "%LOG%" 2>&1
if errorlevel 1 goto :novenv

echo @echo off>"launch.cmd"
echo start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0run.py">>"launch.cmd"
goto :done

rem --- fallback: libraries in a local folder, no virtual environment -------------
:novenv
echo.
echo The private environment could not be used. Switching to a local library folder...
echo Virtual environment unusable, falling back to local libs >> "%LOG%"
if exist ".venv" rmdir /s /q ".venv"
if exist "libs" rmdir /s /q "libs"
%PYCMD% -m pip install --disable-pip-version-check --no-cache-dir --target "%~dp0libs" -r requirements.txt >> "%LOG%" 2>&1
if errorlevel 1 goto :fail
set "PYW="
for /f "usebackq delims=" %%P in (`%PYCMD% -c "import sys,os; d=os.path.dirname(sys.executable); w=os.path.join(d,'pythonw.exe'); print(w if os.path.exists(w) else sys.executable)"`) do set "PYW=%%P"
if not defined PYW goto :fail
echo @echo off>"launch.cmd"
echo start "" "%PYW%" "%~dp0run.py">>"launch.cmd"

:done
echo %~dp0>".izakami_ready"
echo Starting Izakami...
echo Setup finished >> "%LOG%"
call "%~dp0launch.cmd"
exit /b 0

:fail
echo.
echo Setup failed. Details were saved to:
echo   %LOG%
echo Setup failed >> "%LOG%"
if not "%IZAKAMI_SILENT%"=="1" pause
exit /b 1
