@echo off
chcp 65001 >nul
echo ===================================================
echo  TS Controller 빌드를 시작합니다...
echo ===================================================

:: 1. 기존 dist 폴더가 있다면 안전하게 먼저 완전히 삭제 (캐시 꼬임 방지)
if exist "dist" (
    echo [*] 이전 빌드의 dist 폴더를 감지하여 깔끔하게 정리 중...
    rmdir /s /q "dist"
)

:: 2. PyInstaller 경량화 빌드 실행
:: 불필요한 내장 대형 모듈(디버그 로그, 테스트 킷, 멀티미디어 도구)을 빌드에서 명시적으로 제외(Exclude)합니다.
pyinstaller --clean --onefile --noconsole ^
    --icon="icon.ico" ^
    --add-data "icon.ico;." ^
    --collect-all keyboard ^
    --exclude-module tkinter.test ^
    --exclude-module pydoc ^
    --exclude-module unittest ^
    --exclude-module distutils ^
    TS_controller.py

echo.
echo ===================================================
echo  빌드 완료! 후처리 및 정리 작업을 시작합니다.
echo ===================================================

:: 3. 빌드 중간에 생성된 찌꺼기 임시 폴더(build) 및 설정 로그(.spec) 청소
if exist "build" (
    echo [1/2] 임시 작업용 build 폴더 삭제 중...
    rmdir /s /q "build"
)
if exist "TS_controller.spec" (
    del /f /q "TS_controller.spec"
)

:: 4. 현재 폴더에 있는 *.ini 차량 프로필 설정 파일들을 새로 만든 dist 폴더로 복사
if exist "dist" (
    echo [2/2] 모든 .ini 환경 설정 파일들을 dist 폴더로 복사 중...
    copy /y "*.ini" "dist\" >nul
)

echo ===================================================
echo  Done!
echo ===================================================
echo.

pause