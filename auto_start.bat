@echo off
chcp 65001 > nul

set LAUNCHER=%~dp0launcher.py
set STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set VBS=%STARTUP%\KimSamuJang.vbs

REM -- Find pythonw.exe (first match wins) --
set PYTHONW=
for /f "delims=" %%i in ('where pythonw.exe 2^>nul') do (
    if "%PYTHONW%"=="" set PYTHONW=%%i
)
if "%PYTHONW%"=="" set PYTHONW=%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe
if not exist "%PYTHONW%" set PYTHONW=%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe
if not exist "%PYTHONW%" set PYTHONW=%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe

if not exist "%PYTHONW%" (
    echo [ERROR] pythonw.exe not found. Install Python first.
    pause
    exit /b 1
)

REM -- Register in Windows Startup --
if exist "%VBS%" del "%VBS%"
(
echo Set sh = CreateObject("WScript.Shell"^)
echo sh.Run """"%PYTHONW%"""" """"%LAUNCHER%"""", 0, False
) > "%VBS%"

if exist "%VBS%" (
    echo [OK] Startup registration done.
    echo VBS : %VBS%
) else (
    echo [WARN] Startup registration failed. Try running as Administrator.
)

REM -- Run launcher.py now --
echo.
echo Starting launcher...
start "" "%PYTHONW%" "%LAUNCHER%"
echo [OK] Launcher started. Chrome will open automatically.
echo.
pause
