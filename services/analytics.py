# -*- coding: utf-8 -*-
"""
分析服务层：为路由提供 KPI 与图表数据。
所有函数返回可 JSON 序列化的 dict / list。
"""
import os
import sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from models.database import get_engine


def _load_orders():
    eng = get_engine()
    df = pd.read_sql('SELECT * FROM orders', eng)
    df['order_date'] = pd.to_datetime(df['order_date'])
    return df


def _load_products():
    eng = get_engine()
    return pd.read_sql('SELECT * FROM products', eng)


def _load_users():
    eng = get_engine()
    return pd.read_sql('SELECT * FROM users', eng)


# ============ KPI ============
def get_kpis():
    df = _load_orders()
    total_gmv = float(df['total_amount'].sum())
    total_orders = int(df['order_id'].nunique())
    total_users = int(df['user_id'].nunique())
    aov = round(total_gmv / total_orders, 2) if total_orders else 0
    # 复购率：购买>=2次的用户占比
    user_orders = df.groupby('user_id')['order_id'].nunique()
    repurchase = float((user_orders >= 2).mean() * 100)
    # 促销订单占比
    promo_rate = float((df['is_promotion'] == 1).mean() * 100)
    # 总销量
    total_qty = int(df['quantity'].sum())
    return {
        'total_gmv': round(total_gmv, 2),
        'total_orders': total_orders,
        'total_users': total_users,
        'aov': aov,
        'repurchase_rate': round(repurchase, 2),
        'promo_rate': round(promo_rate, 2),
        'total_qty': total_qty,
    }


# ============ 月度 GMV 趋势 ============
def get_monthly_gmv():
    df = _load_orders()
    df['month'] = df['order_date'].dt.to_period('M').astype(str)
    g = df.groupby('month').agg(
        gmv=('total_amount', 'sum'),
        orders=('order_id', 'count'),
        qty=('quantity', 'sum'),
    ).reset_index()
    g['gmv'] = g['gmv'].round(2)
    return g.to_dict(orient='records')


# ============ 品类销售 ============
def get_category_sales():
    df = _load_orders()
    g = df.groupby('category').agg(
        gmv=('total_amount', 'sum'),
        qty=('quantity', 'sum'),
        orders=('order_id', 'count'),
    ).reset_index().sort_values('gmv', ascending=False)
    g['gmv'] = g['gmv'].round(2)
    g['share'] = (g['gmv'] / g['gmv'].sum() * 100).round(2)
    return g.to_dict(orient='records')


# ============ Top 商品 ============
def get_top_products(n=10):
    df = _load_orders()
    prods = _load_products()
    g = df.groupby('product_id').agg(
        gmv=('total_amount', 'sum'),
        qty=('quantity', 'sum'),
        orders=('order_id', 'count'),
    ).reset_index().sort_values('gmv', ascending=False).head(n)
    g = g.merge(prods[['product_id', 'product_name', 'category']], on='product_id', how='left')
    g['gmv'] = g['gmv'].round(2)
    return g.to_dict(orient='records')


# ============ 区域销售（地图）============
def get_region_sales():
    df = _load_orders()
    g = df.groupby('region').agg(
        gmv=('total_amount', 'sum'),
        orders=('order_id', 'count'),
    ).reset_index().sort_values('gmv', ascending=False)
    g['gmv'] = g['gmv'].round(2)
    # ECharts 地图需要 name/value
    return [{'name': r['region'], 'value': round(r['gmv'] / 10000, 2)} for _, r in g.iterrows()]


# ============ 渠道分布 ============
def get_channel_dist():
    df = _load_orders()
    g = df.groupby('channel').agg(
        orders=('order_id', 'count'),
        gmv=('total_amount', 'sum'),
    ).reset_index()
    g['gmv'] = g['gmv'].round(2)
    return g.to_dict(orient='records')


# ============ 日销量趋势 ============
def get_daily_sales(days=60):
    df = _load_orders()
    g = df.groupby('order_date').agg(
        sales=('quantity', 'sum'),
        gmv=('total_amount', 'sum'),
        orders=('order_id', 'count'),
    ).reset_index().sort_values('order_date').tail(days)
    g['order_date'] = g['order_date'].dt.strftime('%Y-%m-%d')
    g['gmv'] = g['gmv'].round(2)
    return g.to_dict(orient='records')


# ============ 促销效果对比 ============
def get_promo_impact():
    df = _load_orders()
    df['is_promo'] = df['is_promotion'] == 1
    g = df.groupby('is_promo').agg(
        orders=('order_id', 'count'),
        gmv=('total_amount', 'sum'),
        avg_amount=('total_amount', 'mean'),
        qty=('quantity', 'sum'),
    ).reset_index()
    g['label'] = g['is_promo'].map({True: '促销日', False: '普通日'})
    g['gmv'] = g['gmv'].round(2)
    g['avg_amount'] = g['avg_amount'].round(2)
    return g[['label', 'orders', 'gmv', 'avg_amount', 'qty']].to_dict(orient='records')


# ============ 库存预警 ============
def get_low_stock_products():
    prods = _load_products()
    df = _load_orders()
    # 计算近30天销量
    recent = df[df['order_date'] >= df['order_date'].max() - pd.Timedelta(days=30)]
    sold = recent.groupby('product_id')['quantity'].sum().reset_index().rename(
        columns={'quantity': 'sold_30d'})
    prods = prods.merge(sold, on='product_id', how='left')
    prods['sold_30d'] = prods['sold_30d'].fillna(0).astype(int)
    # 预计可售天数
    prods['est_days'] = prods.apply(
        lambda r: int(r['stock'] / (r['sold_30d'] / 30)) if r['sold_30d'] > 0 else 9999, axis=1)
    low = prods[(prods['stock'] < config.LOW_STOCK_THRESHOLD) | (prods['est_days'] < 14)].copy()
    low = low.sort_values('est_days').head(30)
    low['warning'] = low.apply(_stock_warning_level, axis=1)
    return low[['product_id', 'product_name', 'category', 'stock', 'sold_30d', 'est_days', 'warning']].to_dict(orient='records')


def _stock_warning_level(r):
    if r['est_days'] < 7:
        return '紧急'
    if r['est_days'] < 14:
        return '预警'
    if r['stock'] < config.LOW_STOCK_THRESHOLD:
        return '关注'
    return '正常'


# ============ 滞销商品 ============
def get_slow_products(n=15):
    prods = _load_products()
    df = _load_orders()
    sold = df.groupby('product_id').agg(
        qty=('quantity', 'sum'),
        gmv=('total_amount', 'sum'),
    ).reset_index()
    prods = prods.merge(sold, on='product_id', how='left')
    prods['qty'] = prods['qty'].fillna(0)
    prods['gmv'] = prods['gmv'].fillna(0)
    slow = prods.sort_values('qty').head(n)
    slow['gmv'] = slow['gmv'].round(2)
    return slow[['product_id', 'product_name', 'category', 'stock', 'qty', 'gmv']].to_dict(orient='records')


# ============ 用户增长 ============
def get_user_growth():
    users = _load_users()
    users['register_date'] = pd.to_datetime(users['register_date'])
    users['month'] = users['register_date'].dt.to_period('M').astype(str)
    g = users.groupby('month').size().reset_index(name='new_users')
    g['cum_users'] = g['new_users'].cumsum()
    return g.to_dict(orient='records')


# ============ 时段热力（星期 × 小时）============
def get_hour_weekday_heatmap():
    df = _load_orders()
    df['hour'] = df['order_date'].dt.hour
    df['dow'] = df['order_date'].dt.dayofweek
    # 由于生成时未指定小时，这里按订单量近似分布
    g = df.groupby(['dow', 'hour']).size().reset_index(name='count')
    return g.to_dict(orient='records')


# ============ 品类月度趋势（堆叠图）============
def get_category_monthly():
    df = _load_orders()
    df['month'] = df['order_date'].dt.to_period('M').astype(str)
    g = df.groupby(['month', 'category'])['total_amount'].sum().reset_index()
    g['total_amount'] = g['total_amount'].round(2)
    pivot = g.pivot(index='month', columns='category', values='total_amount').fillna(0)
    months = pivot.index.tolist()
    series = []
    for cat in pivot.columns:
        series.append({'name': cat, 'data': [round(float(v), 2) for v in pivot[cat].tolist()]})
    return {'months': months, 'series': series}
