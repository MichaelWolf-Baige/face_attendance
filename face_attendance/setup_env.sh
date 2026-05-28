#!/bin/bash
set -e

echo "============================================"
echo "  人脸识别考勤系统 - 一键环境安装"
echo "============================================"
echo ""

# ====== 检查 Python ======
echo "[1/3] 检查 Python 环境..."
PYTHON_CMD=""

if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "  [错误] 未找到 Python！"
    echo "  请先安装 Python 3.10+: https://www.python.org/downloads/"
    exit 1
fi

PY_VER=$($PYTHON_CMD --version 2>&1)
echo "  已找到: $PY_VER"

# ====== 安装依赖 ======
echo ""
echo "[2/3] 安装依赖包..."
echo "  这可能需要 5-10 分钟..."
$PYTHON_CMD -m pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo ""
    echo "  [警告] 默认源失败，尝试清华镜像..."
    $PYTHON_CMD -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
fi

# ====== 验证 ======
echo ""
echo "[3/3] 验证安装..."
$PYTHON_CMD -c "import cv2; import numpy; import PyQt5; import sqlalchemy; import openpyxl; import bcrypt; print('  所有基础依赖 OK')"

echo ""
echo "============================================"
echo "  安装完成！"
echo ""
echo "  首次启动会自动下载 InsightFace 模型（约200MB）"
echo ""
echo "  启动: python3 main.py"
echo "  默认账号: admin / admin123"
echo "============================================"
