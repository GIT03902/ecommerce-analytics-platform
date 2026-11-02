# -*- coding: utf-8 -*-
"""
RFM 客户分层 + K-Means 聚类。
- R（Recency）：最近一次购买距今天数
- F（Frequency）：购买频次
- M（Monetary）：累计消费金额
用 K-Means 聚成 4 类，按金额降序标注：高价值/潜力/一般/流失预警。
模型持久化到 models_trained/kmeans.pkl。
"""
import os
import sys

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import joblib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from models.database import get_engine

# 参考日期（数据截止日）
REFERENCE_DATE = pd.Timestamp('2024-12-31')

_cache = None  # 简单内存缓存


def compute_rfm(force=False):
    """计算 RFM 并聚类，返回 (rfm_df, cluster_summary, label_map)。"""
    global _cache
    if _cache is not None and not force:
        return _cache

    eng = get_engine()
    df = pd.read_sql('SELECT user_id, order_id, order_date, total_amount FROM orders', eng)
    df['order_date'] = pd.to_datetime(df['order_date'])

    rfm = df.groupby('user_id').agg(
        recency=('order_date', lambda x: (REFERENCE_DATE - x.max()).days),
        frequency=('order_id', 'count'),
        monetary=('total_amount', 'sum'),
    ).reset_index()

    # 标准化
    scaler = StandardScaler()
    rfm_scaled = scaler.fit_transform(rfm[['recency', 'frequency', 'monetary']])

    # K-Means（加载或训练）
    km_path = os.path.join(config.MODEL_DIR, 'kmeans.pkl')
    if os.path.exists(km_path) and not force:
        km = joblib.load(km_path)
    else:
        km = KMeans(n_clusters=config.KMEANS_CLUSTERS, random_state=42, n_init=10)
        km.fit(rfm_scaled)
        joblib.dump(km, km_path)

    rfm['cluster'] = km.predict(rfm_scaled)

    # 给簇打标签：按平均金额降序
    cluster_summary = rfm.groupby('cluster').agg(
        m=('monetary', 'mean'),
        f=('frequency', 'mean'),
        r=('recency', 'mean'),
        count=('user_id', 'count'),
    ).sort_values('m', ascending=False)

    labels = ['高价值客户', '潜力客户', '一般客户', '流失预警客户']
    label_map = {c: labels[i] for i, c in enumerate(cluster_summary.index)}
    rfm['tier'] = rfm['cluster'].map(label_map)

    _cache = (rfm, cluster_summary, label_map)
    return _cache


def get_tier_distribution():
    """各客户层级数量与金额占比。"""
    rfm, summary, label_map = compute_rfm()
    dist = rfm.groupby('tier').agg(
        count=('user_id', 'count'),
        avg_monetary=('monetary', 'mean'),
        avg_frequency=('frequency', 'mean'),
        avg_recency=('recency', 'mean'),
        total_monetary=('monetary', 'sum'),
    ).reset_index()
    total = dist['total_monetary'].sum()
    dist['monetary_share'] = (dist['total_monetary'] / total * 100).round(2)
    # 排序
    order = ['高价值客户', '潜力客户', '一般客户', '流失预警客户']
    dist['tier'] = pd.Categorical(dist['tier'], categories=order, ordered=True)
    dist = dist.sort_values('tier').reset_index(drop=True)
    return dist


def get_rfm_scatter():
    """RFM 三维数据用于散点图（R vs M，颜色按层级）。"""
    rfm, _, _ = compute_rfm()
    # 采样以保证图表流畅
    if len(rfm) > 1500:
        rfm = rfm.sample(1500, random_state=42)
    return rfm[['recency', 'frequency', 'monetary', 'tier']].to_dict(orient='records')


def get_churn_users():
    """流失预警客户清单（最近购买 > 阈值天数）。"""
    rfm, _, _ = compute_rfm()
    churn = rfm[(rfm['recency'] > config.CHURN_RECENCY_DAYS) & (rfm['monetary'] > 0)].copy()
    churn = churn.sort_values('monetary', ascending=False).head(50)
    return churn[['user_id', 'recency', 'frequency', 'monetary', 'tier']].to_dict(orient='records')


def get_high_value_users():
    """高价值客户清单。"""
    rfm, _, _ = compute_rfm()
    hv = rfm[rfm['monetary'] >= config.HIGH_VALUE_MONETARY].copy()
    hv = hv.sort_values('monetary', ascending=False).head(50)
    return hv[['user_id', 'recency', 'frequency', 'monetary', 'tier']].to_dict(orient='records')
