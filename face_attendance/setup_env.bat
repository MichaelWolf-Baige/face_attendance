@echo off
chcp 65001 >nul
title 人脸识别考勤系统 - 环境安装

echo ============================================
echo   人脸识别考勤系统 - 环境安装
echo ============================================
echo.

cd /d "%~dp0"

REM ====== 检查 Python ======
echo [1/3] 检查 Python 环境...
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
    echo   [错误] 未找到 Python！请先安装 Python 3.10+
    echo   下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('%PYTHON_CMD% --version 2^>^&1') do echo   已找到: %%i

REM ====== 安装依赖 ======
echo.
echo [2/3] 安装依赖包...
%PYTHON_CMD% -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if %errorlevel% neq 0 (
    echo   清华镜像失败，尝试默认源...
    %PYTHON_CMD% -m pip install -r requirements.txt
)

REM ====== 验证 ======
echo.
echo [3/3] 验证安装...
%PYTHON_CMD% -c "import cv2; import numpy; import PyQt5; import sqlalchemy; import openpyxl; import bcrypt; import onnxruntime; print('  所有依赖 OK')"
if %errorlevel% neq 0 (
    echo   [错误] 依赖验证失败
    pause
    exit /b 1
)

echo.
echo ============================================
echo   安装完成！
echo.
echo   启动方式:
echo     - 双击 start.bat
echo     - 或在终端运行: python main.py
echo.
echo   首次启动会自动下载 InsightFace 模型（约200MB）
echo   默认账号: admin / admin123
echo.
echo   如需 GPU 加速 (NVIDIA): pip install onnxruntime-gpu
echo ============================================
pause
