@echo off
chcp 65001 >nul
title 人脸识别考勤系统 - 环境安装

echo ============================================
echo   人脸识别考勤系统 - 一键环境安装
echo ============================================
echo.

cd /d "%~dp0"

REM ====== 检查 Python ======
echo [1/3] 检查 Python 环境...
set PYTHON_CMD=
where python >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo   已找到: %%i
    set PYTHON_CMD=python
) else (
    echo   [错误] 未找到 Python！
    echo   请先安装 Python 3.10+：https://www.python.org/downloads/
    echo   安装时务必勾选 "Add Python to PATH"
    pause
    exit /b 1
)

REM 检查 Python 版本
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PY_VER=%%i
for /f "tokens=1,2 delims=." %%a in ("%PY_VER%") do (
    set PY_MAJOR=%%a
    set PY_MINOR=%%b
)
if %PY_MAJOR% LSS 3 (
    echo   [错误] Python 版本需要 3.10+，当前: %PY_VER%
    pause
    exit /b 1
)
if %PY_MAJOR% EQU 3 if %PY_MINOR% LSS 10 (
    echo   [警告] 推荐 Python 3.10+，当前: %PY_VER%，可能兼容
)

REM ====== 安装依赖 ======
echo.
echo [2/3] 安装依赖包...
echo   这可能需要 5-10 分钟，取决于网络速度...
echo.
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if %errorlevel% neq 0 (
    echo.
    echo   [警告] 清华镜像安装失败，尝试默认源...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo.
        echo   [错误] 依赖安装失败！请检查网络连接。
        pause
        exit /b 1
    )
)

REM ====== 验证 ======
echo.
echo [3/3] 验证安装...
python -c "import cv2; import numpy; import PyQt5; import sqlalchemy; import openpyxl; import bcrypt; print('  所有基础依赖 OK')"
if %errorlevel% neq 0 (
    echo   [错误] 依赖验证失败
    pause
    exit /b 1
)

REM 不在这里导入 InsightFace，因为首次运行时会自动下载模型
echo   InsightFace/onnxruntime 将在首次启动时验证

echo.
echo ============================================
echo   安装完成！
echo.
echo   首次启动会自动下载 InsightFace 模型（约200MB），请耐心等待。
echo.
echo   启动方式：
echo     1. 双击 start.bat
echo     2. 或在终端运行: python main.py
echo.
echo   默认账号: admin / admin123
echo ============================================
pause
