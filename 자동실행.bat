@echo off
cd /d "%~dp0"
set "BUNDLED_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if exist "%BUNDLED_PY%" (
    "%BUNDLED_PY%" auto_run.py
    pause
    exit /b %errorlevel%
)

where py >nul 2>nul
if %errorlevel%==0 (
    py auto_run.py
    pause
    exit /b %errorlevel%
)

python auto_run.py
pause
