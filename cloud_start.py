# -*- coding: utf-8 -*-
"""云端部署启动入口（供 WorkBuddy Sites / Docker 等容器化环境使用）。

行为：
1. 强制 SQLite 模式（沙箱无 MySQL）
2. 首次启动自动初始化（生成 6.8 万订单数据 + 训练 RFM/随机森林模型）
3. 后续重启直接复用已有数据与模型，秒级启动
4. 监听 PORT 环境变量，绑定 0.0.0.0

用法（沙箱 startCmd）：python cloud_start.py
"""
import os
import sys
import glob

# 强制 SQLite 模式（必须在 import config 前设置）
os.environ.setdefault('DB_MODE', 'sqlite')
os.environ.setdefault('PYTHONUNBUFFERED', '1')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config


def _need_init():
    """判断是否需要执行初始化：数据库为空 或 模型文件缺失。"""
    from models.database import is_empty
    if is_empty():
        return True
    # 检查模型文件是否存在
    model_files = glob.glob(os.path.join(config.MODEL_DIR, '*.pkl'))
    if len(model_files) < 2:  # 至少应有 RFM 与 RF 两个模型
        return True
    return False


def main():
    port = int(os.environ.get('PORT', 5000))

    if _need_init():
        print('=' * 60)
        print('  首次启动：正在初始化数据并训练模型（约 1-2 分钟）...')
        print('=' * 60)
        from setup import main as setup_main
        setup_main()
        print('\n  初始化完成，启动 Web 服务...\n')

    from app import app
    print(f'\n  电商销售数据分析与智能预警平台已启动')
    print(f'  监听端口：{port}（0.0.0.0）')
    print(f'  默认账号：admin / admin123')
    print('=' * 60 + '\n')
    app.run(host='0.0.0.0', port=port, debug=False)


if __name__ == '__main__':
    main()
