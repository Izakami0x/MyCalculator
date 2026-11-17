@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "READY="
if exist ".izakami_ready" set /p READY=<".izakami_ready"
if /i "%READY%"=="%~dp0" if exist "launch.cmd" goto :launch
call "%~dp0INSTALL_AND_RUN.bat"
exit /b %errorlevel%

:launch
call "%~dp0launch.cmd"
exit /b 0
