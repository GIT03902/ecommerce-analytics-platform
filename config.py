# -*- coding: utf-8 -*-
"""全局配置：支持 SQLite（默认零配置）/ MySQL 双模式切换。"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')
MODEL_DIR = os.path.join(BASE_DIR, 'models_trained')
DATA_DIR = os.path.join(BASE_DIR, 'data')
EXPORT_DIR = os.path.join(BASE_DIR, 'exports')

for _d in (INSTANCE_DIR, MODEL_DIR, DATA_DIR, EXPORT_DIR):
    os.makedirs(_d, exist_ok=True)

# ============ 数据库模式：sqlite（默认）/ mysql ============
DB_MODE = os.environ.get('DB_MODE', 'sqlite').lower()

if DB_MODE == 'mysql':
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PWD = os.environ.get('DB_PWD', '123456')
    DB_HOST = os.environ.get('DB_HOST', '127.0.0.1')
    DB_PORT = os.environ.get('DB_PORT', '3306')
    DB_NAME = os.environ.get('DB_NAME', 'ecommerce')
    SQLALCHEMY_DATABASE_URI = (
        f'mysql+pymysql://{DB_USER}:{DB_PWD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4'
    )
else:
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(INSTANCE_DIR, "ecommerce.db")}'

SQLALCHEMY_TRACK_MODIFICATIONS = False
SECRET_KEY = 'ecommerce-analytics-2024-secret-key'

# ============ 数据生成参数 ============
NUM_USERS = 5000
NUM_PRODUCTS = 200
START_DATE = '2024-01-01'
END_DATE = '2024-12-31'

# ============ 模型参数 ============
RF_N_ESTIMATORS = 120
KMEANS_CLUSTERS = 4
FORECAST_DAYS = 7  # 预测未来天数

# ============ 预警阈值 ============
LOW_STOCK_THRESHOLD = 200       # 库存预警阈值
CHURN_RECENCY_DAYS = 90         # 流失客户：超过90天未购买
HIGH_VALUE_MONETARY = 5000      # 高价值客户金额门槛

# ============ 促销高峰日（数据生成 + 未来预测共用）============
# key=YYYY-MM-DD, value=(倍率, 名称)
PROMO_DAYS = {
    '2024-02-05': (2.5, '年货节'),
    '2024-02-10': (2.0, '春节'),
    '2024-03-08': (1.8, '女王节'),
    '2024-06-18': (4.0, '618大促'),
    '2024-08-18': (2.0, '七夕'),
    '2024-09-09': (1.8, '99大促'),
    '2024-10-01': (2.0, '国庆'),
    '2024-10-02': (1.8, '国庆'),
    '2024-10-03': (1.8, '国庆'),
    '2024-11-11': (5.5, '双11全球狂欢'),
    '2024-11-12': (2.0, '双11返场'),
    '2024-12-12': (3.0, '双12'),
    '2025-01-01': (2.0, '元旦'),
}


def is_promo_day(date_obj):
    """判断某日是否促销日，返回 (是否促销, 名称)。"""
    key = date_obj.strftime('%Y-%m-%d')
    if key in PROMO_DAYS:
        return True, PROMO_DAYS[key][1]
    return False, ''


# ============ Dify 智能体集成配置 ============
# Dify 是开源 LLM 应用开发平台，集成后 Agent 助手由 Dify 大模型驱动：
#   用户提问 → Flask 调 Dify chat-messages API → Dify 调度工具回调 Flask /api/tool/*
# 未启用或 Dify 不可用时，自动降级到本地规则引擎（services/agent.py）
DIFY_ENABLED = os.environ.get('DIFY_ENABLED', 'false').lower() == 'true'
DIFY_BASE_URL = os.environ.get('DIFY_BASE_URL', 'http://localhost')  # Dify 服务地址
DIFY_API_KEY = os.environ.get('DIFY_API_KEY', '')  # Dify 应用的 API Key
# 开放工具 API 鉴权 Token（供 Dify Agent 工具回调使用）
DIFY_TOOL_TOKEN = os.environ.get('DIFY_TOOL_TOKEN', 'ecommerce-dify-tool-2024')
