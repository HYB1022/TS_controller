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
pyinstaller --clean --onefile --noconsole ^
    --icon="imgs\icon.ico" ^
    --add-data "imgs\icon.ico;imgs" ^
    --add-data "fonts\NanumGothic-Regular.ttf;fonts" ^
    --add-data "fonts\NanumGothic-Bold.ttf;fonts" ^
    --exclude-module tkinter.test ^
    --exclude-module pydoc ^
    --exclude-module unittest ^
    --exclude-module distutils ^
    --exclude-module email ^
    --exclude-module html ^
    --exclude-module http ^
    --exclude-module logging ^
    --upx-dir=. ^
    TS_controller.py

echo.
echo ===================================================
echo  빌드 완료! 후처리 및 정리 작업을 시작합니다.
echo ===================================================

:: 3. 빌드 중간에 생성된 찌꺼기 임시 폴더(build) 및 설정 로그(.spec) 청소
if exist "build" (
    echo [1/3] 임시 작업용 build 폴더 삭제 중...
    rmdir /s /q "build"
)
if exist "TS_controller.spec" (
    del /f /q "TS_controller.spec"
)

:: 4. vehicles 폴더 복사
if exist "dist" (
    echo [2/3] vehicles 폴더 및 하위 설정을 dist 폴더로 복사 중...
    xcopy /e /i /y "vehicles" "dist\vehicles" >nul
)

:: 5. fonts 폴더를 dist 옆에도 복사 (비동결 환경 대비)
if exist "dist" (
    echo [3/3] fonts 폴더를 dist 폴더로 복사 중...
    xcopy /e /i /y "fonts" "dist\fonts" >nul
)

echo ===================================================
echo  Done!
echo ===================================================
echo.

pause
