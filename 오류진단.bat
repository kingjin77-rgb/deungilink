@echo off
cd /d "%~dp0"
echo 오류 진단 시작...
python main.py > 오류내용.txt 2>&1
echo.
echo === 오류 내용 ===
type 오류내용.txt
echo.
echo 위 내용을 스크린샷 찍어 개발팀에 전달하세요.
pause
