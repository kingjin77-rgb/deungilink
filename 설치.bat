@echo off
python --version > nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install from https://www.python.org/downloads/
    pause
    exit /b 1
)
echo Python OK:
python --version
echo.
echo Installing packages...
pip install pdfplumber openpyxl anthropic pdf2image Pillow pytesseract --quiet --disable-pip-version-check
if errorlevel 1 (
    echo [ERROR] Install failed. Check internet or run as Administrator.
    pause
    exit /b 1
)
echo.
echo === Done! Close this window and run the main program. ===
echo.
pause