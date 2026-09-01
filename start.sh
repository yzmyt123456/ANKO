#!/usr/bin/env bash
# 安科创作平台 一键启动(macOS / Linux)
set -e
cd "$(dirname "$0")"

echo "============================================"
echo "  🎲 安科创作平台 - 一键启动"
echo "============================================"

# 1. 创建虚拟环境(不存在时)
if [ ! -d ".venv" ]; then
    echo "[1/3] 创建虚拟环境..."
    python3 -m venv .venv
else
    echo "[1/3] 虚拟环境已存在"
fi

# 2. 激活虚拟环境并安装依赖
source .venv/bin/activate
echo "[2/3] 安装依赖..."
pip install -e ".[dev]" -q

# 3. 启动服务
echo "[3/3] 启动服务:http://127.0.0.1:8000"
echo "        API 文档:http://127.0.0.1:8000/docs"
echo "--------------------------------------------"
python run.py
