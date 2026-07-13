@echo off
echo ===================================================
echo  TS Controller Build Start
echo ===================================================

python -m nuitka --version >nul 2>&1
if errorlevel 1 (
    echo Installing Nuitka...
    pip install nuitka
)

if exist "dist" rmdir /s /q "dist"
if exist "TS_controller.dist" rmdir /s /q "TS_controller.dist"
if exist "TS_controller.build" rmdir /s /q "TS_controller.build"

python -m nuitka --onefile --show-progress --windows-console-mode=disable --windows-icon-from-ico="imgs\icon.ico" --include-data-files="imgs\icon.ico=imgs/icon.ico" --include-data-files="fonts\NanumGothic-Regular.ttf=fonts/NanumGothic-Regular.ttf" --include-data-files="fonts\NanumGothic-Bold.ttf=fonts/NanumGothic-Bold.ttf" --enable-plugin=tk-inter --nofollow-import-to=unittest --nofollow-import-to=pydoc --nofollow-import-to=distutils --nofollow-import-to=email --nofollow-import-to=html --nofollow-import-to=http --nofollow-import-to=logging --nofollow-import-to=xmlrpc --nofollow-import-to=xml --output-dir=dist TS_controller.py

echo.
echo ===================================================
echo  Build Done! Post-processing...
echo ===================================================

if exist "TS_controller.build" rmdir /s /q "TS_controller.build"

if exist "dist" (
    echo Copying vehicles folder...
    xcopy /e /i /y "vehicles" "dist\vehicles" >nul
)

echo ===================================================
echo  Done!
echo ===================================================
echo.

pause