@echo off
chcp 65001 >nul
title 安科创作平台
cd /d %~dp0

echo ============================================
echo   🎲 安科创作平台 - 一键启动
echo ============================================

REM 1. 创建虚拟环境(不存在时)
if not exist ".venv\Scripts\python.exe" (
    echo [1/3] 创建虚拟环境...
    python -m venv .venv
    if errorlevel 1 (
        echo [错误] 创建虚拟环境失败,请确认已安装 Python 3.10+
        pause
        exit /b 1
    )
) else (
    echo [1/3] 虚拟环境已存在
)

REM 2. 激活虚拟环境并安装依赖
call .venv\Scripts\activate.bat
echo [2/3] 安装依赖...
pip install -e ".[dev]" -q

REM 3. 启动服务
echo [3/3] 启动服务:http://127.0.0.1:8000
echo        API 文档:http://127.0.0.1:8000/docs
echo --------------------------------------------
python run.py
pause
