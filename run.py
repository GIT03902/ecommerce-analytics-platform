# -*- coding: utf-8 -*-
"""启动入口：python run.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app

if __name__ == '__main__':
    print('\n' + '=' * 50)
    print('  电商销售数据分析与智能预警平台')
    print('  访问地址：http://127.0.0.1:5000')
    print('  默认账号：admin / admin123')
    print('=' * 50 + '\n')
    app.run(host='0.0.0.0', port=5000, debug=True)
