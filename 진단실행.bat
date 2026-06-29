@echo off
cd /d "%~dp0"
python 진단.py
if exist 오류내용.txt (
    echo.
    echo === 오류내용.txt 내용 ===
    type 오류내용.txt
)
pause
