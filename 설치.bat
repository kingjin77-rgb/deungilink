@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ============================================================
echo   법무법인제이엘 등기자동화 - 설치
echo ============================================================
echo.

REM -- 1. Python 확인 --
python --version > nul 2>&1
if errorlevel 1 (
    echo [오류] Python 이 설치되어 있지 않습니다.
    echo        https://www.python.org/downloads/ 에서 설치하세요.
    echo        설치 시 "Add Python to PATH" 를 반드시 체크하세요.
    pause
    exit /b 1
)
echo [확인] Python:
python --version
echo.

REM -- 2. pip 업그레이드 --
echo pip 업그레이드 중...
python -m pip install --upgrade pip --quiet --disable-pip-version-check

REM -- 3. 패키지 설치 (requirements.txt) --
echo.
echo 패키지 설치 중... (수 분 소요될 수 있습니다)
if exist requirements.txt (
    python -m pip install -r requirements.txt --disable-pip-version-check
) else (
    python -m pip install pdfplumber openpyxl requests anthropic pdf2image Pillow pytesseract flask --disable-pip-version-check
)
if errorlevel 1 (
    echo.
    echo [오류] 패키지 설치 실패. 인터넷 연결을 확인하거나
    echo        이 창을 "관리자 권한으로 실행" 후 다시 시도하세요.
    pause
    exit /b 1
)

REM -- 4. config.ini 준비 --
echo.
if not exist config.ini (
    if exist config.ini.example (
        copy config.ini.example config.ini > nul
        echo [생성] config.ini 를 만들었습니다.
        echo        메모장으로 열어 API 키를 입력하세요.
    )
) else (
    echo [확인] config.ini 가 이미 있습니다.
)

echo.
echo ============================================================
echo   설치 완료!
echo ============================================================
echo.
echo  남은 준비 (스캔 PDF 처리에 필요):
echo   1) Poppler 설치 후 PATH 등록  (이미지 PDF 변환용)
echo   2) Tesseract-OCR 설치          (로컬 무료 OCR)
echo      자세한 내용은 README.md 참고
echo.
echo  실행: 실행.bat  더블클릭  (또는  python main.py)
echo.
pause
