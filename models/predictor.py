# -*- coding: utf-8 -*-
"""
随机森林销量预测模型。
- 特征：品类编码、星期、月份、日、是否周末、是否促销、滞后销量(lag1/lag7)、7日滚动均值
- 目标：次日品类销量
- 评估：12月作为测试集，输出 MAE / R²
- 预测：未来 7 天各品类销量（递推滞后）
模型持久化到 models_trained/rf_sales.pkl，并写入 prediction_logs 表。
"""
import os
import sys
from datetime import timedelta

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_absolute_error, r2_score
import joblib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from models.database import get_engine, get_session, PredictionLog

_cache = None


def _build_daily():
    """从订单表构建日-品类粒度的销量序列。"""
    eng = get_engine()
    df = pd.read_sql(
        'SELECT order_date, order_id, category, quantity, total_amount, is_promotion FROM orders',
        eng)
    df['order_date'] = pd.to_datetime(df['order_date'])
    daily = df.groupby([pd.Grouper(key='order_date', freq='D'), 'category']).agg(
        sales=('quantity', 'sum'),
        gmv=('total_amount', 'sum'),
        orders=('order_id', 'count'),
        is_promotion=('is_promotion', 'max'),
    ).reset_index()
    return daily


def _add_features(daily):
    """构造时间与滞后特征。"""
    le = LabelEncoder()
    daily['cat_code'] = le.fit_transform(daily['category'])
    daily['dow'] = daily['order_date'].dt.dayofweek
    daily['month'] = daily['order_date'].dt.month
    daily['dom'] = daily['order_date'].dt.day
    daily['is_weekend'] = (daily['dow'] >= 5).astype(int)

    daily = daily.sort_values(['category', 'order_date'])
    # 滞后特征（按品类）
    daily['lag_1'] = daily.groupby('category')['sales'].shift(1)
    daily['lag_7'] = daily.groupby('category')['sales'].shift(7)
    daily['roll_7'] = (
        daily.groupby('category')['sales']
        .shift(1).rolling(7, min_periods=1).mean()
        .reset_index(level=0, drop=True)
    )
    daily = daily.dropna()
    return daily, le


def train_and_forecast(force=False):
    """训练 RF 并预测未来 N 天，返回结果字典。"""
    global _cache
    if _cache is not None and not force:
        return _cache

    daily = _build_daily()
    daily, le = _add_features(daily)

    FEATURES = ['cat_code', 'dow', 'month', 'dom', 'is_weekend', 'is_promotion', 'lag_1', 'lag_7', 'roll_7']
    TARGET = 'sales'

    train = daily[daily['order_date'] < '2024-12-01']
    test = daily[(daily['order_date'] >= '2024-12-01') & (daily['order_date'] <= '2024-12-31')]

    rf_path = os.path.join(config.MODEL_DIR, 'rf_sales.pkl')
    if os.path.exists(rf_path) and not force:
        rf, saved_le, saved_features = joblib.load(rf_path)
        le = saved_le
        FEATURES = saved_features
    else:
        rf = RandomForestRegressor(
            n_estimators=config.RF_N_ESTIMATORS, random_state=42, n_jobs=-1, max_depth=15)
        rf.fit(train[FEATURES], train[TARGET])
        joblib.dump((rf, le, FEATURES), rf_path)

    # 测试集评估
    test_pred = rf.predict(test[FEATURES])
    mae = float(mean_absolute_error(test[TARGET], test_pred))
    r2 = float(r2_score(test[TARGET], test_pred))

    # 测试集实际 vs 预测（取品类聚合按日，用于图表）
    test_eval = test.copy()
    test_eval['predicted'] = test_pred
    eval_by_day = test_eval.groupby('order_date').agg(
        actual=('sales', 'sum'), predicted=('predicted', 'sum')).reset_index()
    eval_by_day['order_date'] = eval_by_day['order_date'].dt.strftime('%Y-%m-%d')

    # 未来预测：递推 lag
    last_date = daily['order_date'].max()
    future_dates = [last_date + timedelta(days=i) for i in range(1, config.FORECAST_DAYS + 1)]
    cats = sorted(daily['category'].unique())
    cat_code_map = dict(zip(le.classes_, le.transform(le.classes_)))

    future_rows = []
    for cat in cats:
        sub = daily[daily['category'] == cat].sort_values('order_date')
        last7 = sub['sales'].tail(7).tolist()
        lag1 = sub['sales'].iloc[-1]
        roll7 = float(np.mean(last7))
        for fd in future_dates:
            is_promo, _ = config.is_promo_day(fd)
            x = {
                'cat_code': cat_code_map[cat],
                'dow': fd.weekday(),
                'month': fd.month,
                'dom': fd.day,
                'is_weekend': int(fd.weekday() >= 5),
                'is_promotion': int(is_promo),
                'lag_1': lag1,
                'lag_7': last7[-1] if len(last7) >= 7 else lag1,
                'roll_7': roll7,
            }
            pred = float(rf.predict(pd.DataFrame([x])[FEATURES])[0])
            pred = max(0, int(round(pred)))
            future_rows.append({
                'order_date': fd.strftime('%Y-%m-%d'),
                'category': cat,
                'predicted_sales': pred,
            })
            # 递推更新滞后
            last7 = last7[1:] + [pred]
            lag1 = pred
            roll7 = float(np.mean(last7))

    future_df = pd.DataFrame(future_rows)
    # 未来按日合计（用于趋势图）
    future_total = future_df.groupby('order_date')['predicted_sales'].sum().reset_index()
    future_total.columns = ['order_date', 'predicted']

    # 写预测日志
    try:
        sess = get_session()
        for fd in future_dates:
            day_rows = future_df[future_df['order_date'] == fd.strftime('%Y-%m-%d')]
            for _, r in day_rows.iterrows():
                log = PredictionLog(
                    predict_date=pd.Timestamp(fd),
                    category=r['category'],
                    predicted_sales=int(r['predicted_sales']),
                    model_name='RandomForest',
                    mae=mae,
                    r2=r2,
                )
                sess.add(log)
        sess.commit()
        sess.close()
    except Exception as e:
        print(f'[warn] 预测日志写入失败：{e}')

    # 特征重要性
    importances = sorted(
        zip(FEATURES, rf.feature_importances_), key=lambda x: -x[1])
    feat_imp = [{'feature': f, 'importance': float(i)} for f, i in importances]

    # 近 30 天实际销量（用于趋势图衔接）
    recent = daily[daily['order_date'] >= last_date - timedelta(days=29)]
    recent_total = recent.groupby('order_date')['sales'].sum().reset_index().rename(columns={'sales': 'actual'})
    recent_total['order_date'] = recent_total['order_date'].dt.strftime('%Y-%m-%d')

    _cache = {
        'mae': mae,
        'r2': r2,
        'eval_by_day': eval_by_day.to_dict(orient='records'),
        'future_by_category': future_df.to_dict(orient='records'),
        'future_total': future_total.to_dict(orient='records'),
        'recent_actual': recent_total.to_dict(orient='records'),
        'feature_importance': feat_imp,
        'n_estimators': config.RF_N_ESTIMATORS,
    }
    return _cache
