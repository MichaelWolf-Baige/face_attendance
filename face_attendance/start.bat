@echo off
chcp 65001 >nul
echo ============================================
echo   Face Attendance System
echo ============================================
echo.

cd /d "%~dp0"

REM Find Python
set PYTHON_CMD=
where python >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python
) else (
    where py >nul 2>&1
    if %errorlevel% equ 0 (
        set PYTHON_CMD=py
    )
)

if "%PYTHON_CMD%"=="" (
    echo [ERROR] Python not found. Install Python 3.10+
    echo https://www.python.org/downloads/
    pause
    exit /b 1
)

echo   Select mode:
echo     [1] Auto-detect (recommended)
echo     [2] GPU mode (NVIDIA required)
echo     [3] CPU mode (integrated graphics / old PC)
echo.
set /p MODE="  Enter 1/2/3 (Enter for 1): "

set PROFILE_FLAG=
if "%MODE%"=="2" set PROFILE_FLAG=--gpu
if "%MODE%"=="3" set PROFILE_FLAG=--cpu

echo.
echo   Starting...
%PYTHON_CMD% main.py %PROFILE_FLAG%

if %errorlevel% neq 0 (
    echo.
    echo   Start failed! Check dependencies:
    echo     %PYTHON_CMD% -m pip install -r requirements.txt
    pause
)