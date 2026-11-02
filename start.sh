#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "============================================================"
echo "  电商销售数据分析与智能预警平台 - 一键启动"
echo "============================================================"

# 安装依赖
echo "[1/3] 检查依赖..."
pip install -q -r requirements.txt

# 初始化数据 + 训练模型
echo "[2/3] 初始化数据与模型..."
python setup.py

# 启动服务
echo "[3/3] 启动 Web 服务..."
echo ""
echo "  访问地址: http://127.0.0.1:5000"
echo "  默认账号: admin / admin123"
echo ""
python run.py
