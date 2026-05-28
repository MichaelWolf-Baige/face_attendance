@echo off
chcp 65001 >nul
echo ============================================
echo 人脸识别考勤系统
echo ============================================
echo.

cd /d "%~dp0"

REM 自动选择合适的 Python（优先 python，其次 py launcher）
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
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo 使用: %PYTHON_CMD%
echo 正在启动系统...
%PYTHON_CMD% main.py

if %errorlevel% neq 0 (
    echo.
    echo 启动失败！请检查依赖是否安装:
    echo   %PYTHON_CMD% -m pip install -r requirements.txt
    pause
)
