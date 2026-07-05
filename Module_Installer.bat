@echo off
chcp 65001 >nul
title 파이썬 최신 버전 자동 설치 및 환경 구축 스크립트

echo ============================================================
echo  웹에서 최신 파이썬(Python)을 검색하여 자동 설치를 시작합니다.
echo  이 작업은 반드시 [관리자 권한]으로 실행되어야 합니다.
echo ============================================================
echo.

:: 관리자 권한 체크
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 에러: 반드시 마우스 우클릭 후 [관리자 권한으로 실행]해 주세요!
    goto END
)

:: 1. 이미 파이썬이 정상 설치되어 있는지 1차 체크
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [!] 이미 시스템에 파이썬이 설치되어 있는 것으로 감지되었습니다.
    echo [!] 곧바로 후속 라이브러리 검사 스크립트를 연결합니다.
    goto RUN_MODULES
)

:: 2. 시스템 비트(64비트 여부) 감지 및 최신 버전 웹 주소 파싱 (PowerShell 활용)
echo [-] 파이썬 공식 홈페이지에서 최신 안정화 버전 정보를 조회 중...
set "ARCH=amd64"
if "%PROCESSOR_ARCHITECTURE%"=="x86" if "%PROCESSOR_ARCHITEW6432%"=="" set "ARCH=win32"

for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "$url = 'https://www.python.org/ftp/python/'; $tags = (Invoke-WebRequest -Uri $url -UseBasicParsing).Links | Where-Object { $_.href -match '^([0-9]+\.[0-9]+\.[0-9]+)/$' } | ForEach-Object { $_.href.Trim('/') }; $latest = $tags | Sort-Object { [version]$_ } -Descending | Select-Object -First 1; echo $latest"`) do set "PY_VER=%%i"

if "%PY_VER%"=="" (
    echo [!] 최신 버전 자동 파싱에 실패하여 안정 버전(3.12.3)으로 대체합니다.
    set "PY_VER=3.12.3"
)

set "DOWNLOAD_URL=https://www.python.org/ftp/python/%PY_VER%/python-%PY_VER%-%ARCH%.exe"
set "INSTALLER_PATH=%TEMP%\python_latest_installer.exe"

echo [+] 발견된 최신 안정 버전: Python %PY_VER% (%ARCH%)
echo [-] 다운로드를 시작합니다. 잠시만 기다려 주세요...

:: 3. 최신 버전 설치 파일 다운로드
powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%DOWNLOAD_URL%' -OutFile '%INSTALLER_PATH%' -UseBasicParsing"

if not exist "%INSTALLER_PATH%" (
    echo ❌ 다운로드 실패! 인터넷 연결을 확인하거나 방화벽 설정을 확인해 주세요.
    goto END
)

echo [+] 다운로드 완료! 백그라운드 무인 설치를 시작합니다...
echo [*] 시스템 환경 변수(PATH) 등록 및 pip 초도 설치가 진행됩니다.
echo [*] 약 30초~1분 정도 소요되니 창을 닫지 마세요.

:: 4. 환경변수 포함 조용히 설치 진행
start /wait "" "%INSTALLER_PATH%" /quiet InstallAllUsers=1 PrependPath=1 Include_pip=1

:: 임시 설치 파일 삭제
del /q "%INSTALLER_PATH%"

:: 5. 즉시 명령어를 인식할 수 있도록 현재 창 환경변수 강제 새로고침
for /f "tokens=2*" %%a in ('reg query "HKLM\System\CurrentControlSet\Control\Session Manager\Environment" /v Path') do set "syspath=%%b"
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v Path') do set "usrpath=%%b"
set "PATH=%syspath%;%usrpath%"

echo.
echo ============================================================
echo  🎉 파이썬 최신 엔진 설치가 성공적으로 끝났습니다!
echo ============================================================
echo.

:RUN_MODULES
echo [-] 이어서 라이브러리 검사 프로세스(Tools\Modules.py)를 실행합니다...
echo.

:: pip 복구/업데이트 방어 코드 실행
python -m ensurepip --default-pip >nul 2>&1
python -m pip install --upgrade pip >nul 2>&1

:: Tools\Modules.py 파일 위치 추적 및 실행
if exist "Tools\Modules.py" (
    python Tools\Modules.py
) else if exist "Modules.py" (
    python Modules.py
) else (
    echo ❌ [경고] Tools\Modules.py 파일을 찾지 못했습니다.
    echo 💡 해당 스크립트 파일이 올바른 위치에 있는지 확인해 주세요.
)

:END
echo.
echo 작업이 완료되었습니다.
pause
exit