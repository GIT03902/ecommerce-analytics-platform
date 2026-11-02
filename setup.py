# -*- coding: utf-8 -*-
"""
一键初始化：生成数据 + 训练模型。
用法：python setup.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from models.database import init_db, is_empty


def banner(title):
    print('\n' + '=' * 60)
    print(f'  {title}')
    print('=' * 60)


def main():
    banner('电商销售数据分析与智能预警平台 · 一键初始化')
    print(f'数据库模式：{config.DB_MODE}')
    print(f'数据库连接：{config.SQLALCHEMY_DATABASE_URI}')

    # 1. 初始化表结构
    banner('步骤 1/3：初始化数据库表结构')
    init_db()
    print('  表结构创建完成。')

    # 2. 生成数据
    if is_empty():
        banner('步骤 2/3：生成电商数据（用户/商品/订单）')
        from data import generate_data
        generate_data.main()
    else:
        banner('步骤 2/3：数据已存在，跳过生成')
        print('  如需重新生成，请删除 instance/ecommerce.db 后重跑。')

    # 3. 训练模型
    banner('步骤 3/3：训练机器学习模型（RFM聚类 + 随机森林销量预测）')
    t0 = time.time()
    from models import rfm as R
    rfm, summary, _ = R.compute_rfm(force=True)
    print(f'  RFM 聚类完成，{config.KMEANS_CLUSTERS} 类客户分层：')
    for c in summary.index:
        lab = R.compute_rfm()[2][c]
        print(f'    簇 {c} → {lab}：人数 {int(summary.loc[c, "count"])}，'
              f'平均金额 {summary.loc[c, "m"]:.0f} 元，平均频次 {summary.loc[c, "f"]:.1f}')

    from models import predictor as P
    res = P.train_and_forecast(force=True)
    print(f'  随机森林销量预测训练完成（{config.RF_N_ESTIMATORS} 棵树）：')
    print(f'    测试集 MAE = {res["mae"]:.2f}')
    print(f'    测试集 R²  = {res["r2"]:.4f}')
    print(f'    已预测未来 {config.FORECAST_DAYS} 天各品类销量。')

    dt = time.time() - t0
    banner('初始化完成！')
    print(f'  总耗时：{dt:.1f} 秒')
    print(f'  默认账号：admin / admin123')
    print(f'  启动命令：python run.py')
    print(f'  访问地址：http://127.0.0.1:5000')
    print('=' * 60 + '\n')


if __name__ == '__main__':
    main()
