@echo off
chcp 65001 >nul
title 酮伴妈妈问卷 - 局域网服务器

echo.
echo ============================================================
echo 🏡 酮伴妈妈问卷 - 局域网服务器启动器
echo ============================================================
echo.

cd /d "%~dp0"

python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未检测到 Python
    echo.
    echo 💡 请先安装 Python: https://www.python.org/downloads/
    echo    安装时记得勾选 "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

echo ✅ Python 已安装
echo.
echo 正在启动服务器...
echo.

python serve_quiz.py

pause

