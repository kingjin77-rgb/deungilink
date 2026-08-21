@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ============================================================
echo   법무법인제이엘 등기자동화 - exe 빌드
echo ============================================================
echo.

python --version > nul 2>&1
if errorlevel 1 (
    echo [오류] Python 이 설치되어 있지 않습니다.
    pause
    exit /b 1
)

echo PyInstaller 설치 확인 중...
python -m pip show pyinstaller > nul 2>&1
if errorlevel 1 (
    echo PyInstaller 설치 중...
    python -m pip install pyinstaller --quiet --disable-pip-version-check
)

echo.
echo 이전 빌드 결과물 정리 중...
if exist build rmdir /s /q build
if exist dist\JL_Registry_Auto rmdir /s /q dist\JL_Registry_Auto

echo.
echo 빌드 시작 (JL_Registry_Auto.spec)...
python -m PyInstaller JL_Registry_Auto.spec
if errorlevel 1 (
    echo.
    echo [오류] 빌드 실패. 위 로그를 확인하세요.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   빌드 완료: dist\JL_Registry_Auto\JL_Registry_Auto.exe
echo ============================================================
echo.
echo  배포 전 확인:
echo   1) dist\JL_Registry_Auto 폴더 전체를 배포(단일 exe 파일만으로는 동작 안 함)
echo   2) 대상 PC 환경변수 JL_REGISTRY_SECRET 설정 여부
echo   3) config.ini 에 실제 API 키 입력 여부
echo      (_internal\config.ini — 빌드에는 빈 템플릿만 포함됨)
echo.
pause
