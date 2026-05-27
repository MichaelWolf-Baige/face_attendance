@echo off
chcp 65001 >nul
echo ============================================
echo 人脸识别考勤系统
echo ============================================
echo.

cd /d "%~dp0"

REM 优先使用 py launcher 指定 Python 3.12（避免 3.13 没装依赖的问题）
set PYTHON_CMD=python
where py >nul 2>&1
if %errorlevel% equ 0 (
    py -3.12 -c "exit" >nul 2>&1
    if %errorlevel% equ 0 (
        set PYTHON_CMD=py -3.12
        echo 使用 Python 3.12
    )
)

echo 正在启动系统...
%PYTHON_CMD% main.py

if %errorlevel% neq 0 (
    echo.
    echo 启动失败，请检查依赖是否安装:
    echo   pip install -r requirements.txt
    echo   py -3.12 -m pip install -r requirements.txt
    pause
)