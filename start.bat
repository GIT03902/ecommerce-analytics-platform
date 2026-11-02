@echo off
chcp 65001 >nul
title 电商销售数据分析与智能预警平台

echo ============================================================
echo   电商销售数据分析与智能预警平台 - 一键启动
echo ============================================================
echo.

REM 检查 Python
where python >nul 2>nul
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

REM 安装依赖（首次）
echo [1/3] 检查依赖...
pip install -q -r requirements.txt

REM 初始化数据 + 训练模型
echo [2/3] 初始化数据与模型...
python setup.py
if errorlevel 1 (
    echo [错误] 初始化失败，请查看上方日志
    pause
    exit /b 1
)

REM 启动服务
echo [3/3] 启动 Web 服务...
echo.
echo   访问地址: http://127.0.0.1:5000
echo   默认账号: admin / admin123
echo.
python run.py
pause
