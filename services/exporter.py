# -*- coding: utf-8 -*-
"""Excel 导出服务：用 openpyxl 导出各业务报表。"""
import os
import pandas as pd

import config
import services.analytics as A
from models import rfm as R
from models import predictor as P


def export_kpi_summary():
    """导出经营总览 KPI。"""
    kpi = A.get_kpis()
    df = pd.DataFrame([
        {'指标': '总成交额 GMV（元）', '数值': kpi['total_gmv']},
        {'指标': '总订单数', '数值': kpi['total_orders']},
        {'指标': '消费用户数', '数值': kpi['total_users']},
        {'指标': '客单价（元）', '数值': kpi['aov']},
        {'指标': '复购率（%）', '数值': kpi['repurchase_rate']},
        {'指标': '促销订单占比（%）', '数值': kpi['promo_rate']},
        {'指标': '总销量（件）', '数值': kpi['total_qty']},
    ])
    return _save(df, '经营总览')


def export_category_sales():
    df = pd.DataFrame(A.get_category_sales())
    df.columns = ['品类', 'GMV(元)', '销量(件)', '订单数', '占比(%)']
    return _save(df, '品类销售明细')


def export_top_products():
    df = pd.DataFrame(A.get_top_products(50))
    df = df[['product_id', 'product_name', 'category', 'gmv', 'qty', 'orders']]
    df.columns = ['商品ID', '商品名称', '品类', 'GMV(元)', '销量(件)', '订单数']
    return _save(df, '热销商品Top50')


def export_rfm():
    rfm, _, _ = R.compute_rfm()
    df = rfm[['user_id', 'recency', 'frequency', 'monetary', 'tier']].copy()
    df.columns = ['用户ID', '最近购买天数(R)', '购买频次(F)', '累计金额(M)(元)', '客户分层']
    df = df.sort_values('累计金额(M)(元)', ascending=False)
    return _save(df, 'RFM客户分层明细')


def export_low_stock():
    df = pd.DataFrame(A.get_low_stock_products())
    df.columns = ['商品ID', '商品名称', '品类', '库存', '近30天销量', '预计可售天数', '预警级别']
    return _save(df, '库存预警清单')


def export_forecast():
    res = P.train_and_forecast()
    df = pd.DataFrame(res['future_by_category'])
    df.columns = ['日期', '品类', '预测销量(件)']
    df = df.sort_values(['日期', '品类'])
    meta = pd.DataFrame([
        {'项目': '模型', '值': 'RandomForestRegressor'},
        {'项目': '树数量', '值': res['n_estimators']},
        {'项目': 'MAE(平均绝对误差)', '值': round(res['mae'], 2)},
        {'项目': 'R²(决定系数)', '值': round(res['r2'], 4)},
    ])
    from openpyxl import Workbook
    path = os.path.join(config.EXPORT_DIR, '销量预测_未来7天.xlsx')
    wb = Workbook()
    ws1 = wb.active
    ws1.title = '模型评估'
    for r in meta.itertuples(index=False):
        ws1.append(list(r))
    ws2 = wb.create_sheet('预测明细')
    for r in df.itertuples(index=False):
        ws2.append(list(r))
    wb.save(path)
    return path


def _save(df, name):
    path = os.path.join(config.EXPORT_DIR, f'{name}.xlsx')
    df.to_excel(path, index=False)
    return path
