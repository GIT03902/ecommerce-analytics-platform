# -*- coding: utf-8 -*-
"""启动入口：python run.py

支持云端部署：自动读取 PORT 环境变量绑定 0.0.0.0。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    print('\n' + '=' * 50)
    print('  电商销售数据分析与智能预警平台')
    print(f'  访问地址：http://127.0.0.1:{port}')
    print('  默认账号：admin / admin123')
    print('=' * 50 + '\n')
    app.run(host='0.0.0.0', port=port, debug=debug)
