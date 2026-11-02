# -*- coding: utf-8 -*-
"""
电商数据生成器：生成用户、商品、订单数据并入库。
真实模拟：周末上量、618/双11/双12/春节/国庆促销高峰、品类差异价格、用户复购分层。
运行：python data/generate_data.py
"""
import os
import sys
import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from models.database import AdminUser, User, Product, Order, init_db, get_engine, get_session

random.seed(42)
np.random.seed(42)

# 品类配置：价格区间、销量占比
CATEGORIES = {
    '3C数码':   {'price_range': (199, 8999), 'share': 0.12},
    '服饰鞋包': {'price_range': (49, 999),   'share': 0.20},
    '家居家装': {'price_range': (29, 2999),  'share': 0.15},
    '美妆个护': {'price_range': (39, 899),   'share': 0.14},
    '食品酒水': {'price_range': (19, 599),   'share': 0.13},
    '图书文娱': {'price_range': (15, 199),   'share': 0.08},
    '母婴玩具': {'price_range': (39, 1299),  'share': 0.10},
    '运动户外': {'price_range': (59, 1999),  'share': 0.08},
}

REGIONS = ['北京', '上海', '广东', '浙江', '江苏', '四川', '湖北', '福建', '山东', '河南',
           '湖南', '安徽', '陕西', '辽宁', '重庆', '天津', '广西', '云南', '河北', '江西']

CHANNELS = ['APP', '小程序', 'PC网页', 'H5']


def gen_users(n):
    """生成用户数据。tier_hint 仅用于驱动订单生成，不入库。"""
    rows = []
    for i in range(1, n + 1):
        r = random.random()
        if r < 0.05:
            tier = '高价值'
        elif r < 0.25:
            tier = '潜力'
        elif r < 0.75:
            tier = '一般'
        else:
            tier = '低频'
        rows.append({
            'user_id': f'U{i:05d}',
            'register_date': datetime(2024, 1, 1) + timedelta(days=random.randint(0, 300)),
            'region': random.choice(REGIONS),
            'tier_hint': tier,
        })
    return pd.DataFrame(rows)


def gen_products(n):
    """生成商品数据，按品类占比分配。"""
    rows = []
    pid = 1
    cats = list(CATEGORIES.keys())
    counts = {c: max(5, int(n * CATEGORIES[c]['share'])) for c in cats}
    total = sum(counts.values())
    while total < n:
        counts[random.choice(cats)] += 1
        total += 1
    while total > n:
        c = random.choice(cats)
        if counts[c] > 5:
            counts[c] -= 1
            total -= 1
    for cat in cats:
        lo, hi = CATEGORIES[cat]['price_range']
        for _ in range(counts[cat]):
            price = round(np.random.uniform(lo, hi), 2)
            rows.append({
                'product_id': f'P{pid:04d}',
                'product_name': f'{cat}精选商品-{pid:03d}',
                'category': cat,
                'unit_price': price,
                'cost_ratio': round(np.random.uniform(0.45, 0.75), 3),
                'stock': random.randint(50, 5000),
            })
            pid += 1
    return pd.DataFrame(rows)


def _date_weights(start, days_total):
    """构造每日订单权重：周末上量 + 促销高峰。"""
    weights = []
    for d in range(days_total):
        dt = start + timedelta(days=d)
        w = 1.0
        if dt.weekday() >= 5:
            w *= 1.4
        key = dt.strftime('%Y-%m-%d')
        if key in config.PROMO_DAYS:
            w *= config.PROMO_DAYS[key][0]
        weights.append(w)
    arr = np.array(weights, dtype=float)
    arr /= arr.sum()
    return arr


def gen_orders(users_df, products_df):
    """根据用户分层生成订单。"""
    tier_orders = {'高价值': (40, 120), '潜力': (15, 40), '一般': (3, 12), '低频': (1, 3)}
    orders = []
    oid = 1
    start = datetime(2024, 1, 1)
    days_total = 365
    dw = _date_weights(start, days_total)

    products_by_cat = {}
    for _, p in products_df.iterrows():
        products_by_cat.setdefault(p['category'], []).append(p)

    for _, u in users_df.iterrows():
        lo, hi = tier_orders[u['tier_hint']]
        n_ord = random.randint(lo, hi)
        chosen_days = np.random.choice(days_total, size=n_ord, p=dw, replace=True)
        for d_off in chosen_days:
            odate = start + timedelta(days=int(d_off))
            cat = random.choice(list(CATEGORIES.keys()))
            p = random.choice(products_by_cat[cat])
            qty = max(1, min(np.random.poisson(1.5) + 1, 10))
            key = odate.strftime('%Y-%m-%d')
            discount = 0.85 if key in config.PROMO_DAYS else (0.95 if odate.weekday() >= 5 else 1.0)
            amount = round(p['unit_price'] * qty * discount, 2)
            orders.append({
                'order_id': f'O{oid:06d}',
                'user_id': u['user_id'],
                'product_id': p['product_id'],
                'category': cat,
                'quantity': int(qty),
                'unit_price': float(p['unit_price']),
                'total_amount': float(amount),
                'order_date': odate.strftime('%Y-%m-%d %H:%M:%S'),
                'channel': random.choice(CHANNELS),
                'region': u['region'],
                'is_promotion': 1 if key in config.PROMO_DAYS else 0,
            })
            oid += 1
    df = pd.DataFrame(orders)
    df = df.sort_values('order_date').reset_index(drop=True)
    return df


def create_default_admin():
    """创建默认管理员账号 admin / admin123。"""
    sess = get_session()
    existing = sess.query(AdminUser).filter_by(username='admin').first()
    if existing:
        sess.close()
        return
    admin = AdminUser(
        username='admin',
        password_hash=generate_password_hash('admin123'),
        display_name='系统管理员',
        role='admin',
    )
    analyst = AdminUser(
        username='analyst',
        password_hash=generate_password_hash('analyst123'),
        display_name='数据分析师',
        role='analyst',
    )
    sess.add_all([admin, analyst])
    sess.commit()
    sess.close()
    print('  默认账号已创建：admin/admin123（管理员）、analyst/analyst123（分析师）')


def main():
    print('=' * 60)
    print('  电商数据生成器')
    print('=' * 60)
    print(f'  数据库模式：{config.DB_MODE}')
    print(f'  连接：{config.SQLALCHEMY_DATABASE_URI}')
    print('==> 初始化数据库表结构...')
    init_db()

    from sqlalchemy import text
    eng = get_engine()
    with eng.connect() as conn:
        cnt = conn.execute(text('SELECT COUNT(*) FROM orders')).scalar()
    if cnt and cnt > 0:
        print(f'==> 数据库已有 {cnt} 条订单，跳过生成。')
        print('    如需重新生成，请删除 instance/ecommerce.db 后重跑。')
        create_default_admin()
        return

    print(f'==> 生成 {config.NUM_USERS} 个用户...')
    users = gen_users(config.NUM_USERS)
    print(f'==> 生成 {config.NUM_PRODUCTS} 个商品...')
    products = gen_products(config.NUM_PRODUCTS)
    print('==> 生成订单数据（约需 30-60 秒，请稍候）...')
    orders = gen_orders(users, products)
    print(f'==> 数据生成完成：用户 {len(users)} / 商品 {len(products)} / 订单 {len(orders)}')

    # 写 CSV 备份
    users.drop(columns=['tier_hint']).to_csv(
        os.path.join(config.DATA_DIR, 'users.csv'), index=False, encoding='utf-8-sig')
    products.to_csv(
        os.path.join(config.DATA_DIR, 'products.csv'), index=False, encoding='utf-8-sig')
    orders.to_csv(
        os.path.join(config.DATA_DIR, 'orders.csv'), index=False, encoding='utf-8-sig')
    print('==> CSV 备份已写入 data/ 目录')

    # 入库
    print('==> 写入数据库...')
    users.drop(columns=['tier_hint']).to_sql('users', eng, if_exists='append', index=False, chunksize=1000)
    products.to_sql('products', eng, if_exists='append', index=False, chunksize=1000)
    orders.to_sql('orders', eng, if_exists='append', index=False, chunksize=2000)
    print('==> 数据入库完成！')

    create_default_admin()
    print('=' * 60)
    print('  数据准备完毕，可运行：python setup.py 训练模型')
    print('=' * 60)


if __name__ == '__main__':
    main()
