@echo off
chcp 65001 >nul
title TS Controller Module Installer

cd /d "%~dp0"

echo ==========================================
echo TS Controller 환경 점검
echo ==========================================
echo.

:: Python Launcher 확인
py --version >nul 2>&1
if not errorlevel 1 (
    echo [OK] Python 감지됨
    py "Tools\Modules.py"
    goto END
)

:: Python 확인
python --version >nul 2>&1
if not errorlevel 1 (
    echo [OK] Python 감지됨
    python "Tools\Modules.py"
    goto END
)

echo [ERROR] Python이 설치되어 있지 않습니다.
echo.
echo Python 다운로드 페이지를 엽니다...

start "" "https://www.python.org/downloads/"

echo.
echo Python 설치 후 다시 실행해 주세요.

:END
echo.
pause