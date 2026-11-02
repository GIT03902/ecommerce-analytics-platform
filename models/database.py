# -*- coding: utf-8 -*-
"""SQLAlchemy 数据模型与数据库连接（双模式：SQLite / MySQL）。"""
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker
import config

Base = declarative_base()


class AdminUser(Base):
    """管理员账号（登录系统）。"""
    __tablename__ = 'admin_users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    display_name = Column(String(50))
    role = Column(String(20), default='admin')

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class User(Base):
    """电商消费者。"""
    __tablename__ = 'users'
    user_id = Column(String(20), primary_key=True)
    register_date = Column(DateTime)
    region = Column(String(20))

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Product(Base):
    """商品。"""
    __tablename__ = 'products'
    product_id = Column(String(20), primary_key=True)
    product_name = Column(String(100))
    category = Column(String(20))
    unit_price = Column(Float)
    cost_ratio = Column(Float)
    stock = Column(Integer)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Order(Base):
    """订单。"""
    __tablename__ = 'orders'
    order_id = Column(String(20), primary_key=True)
    user_id = Column(String(20))
    product_id = Column(String(20))
    category = Column(String(20))
    quantity = Column(Integer)
    unit_price = Column(Float)
    total_amount = Column(Float)
    order_date = Column(DateTime, index=True)
    channel = Column(String(20))
    region = Column(String(20))
    is_promotion = Column(Integer)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class PredictionLog(Base):
    """预测记录（留存预测历史，体现系统智能化）。"""
    __tablename__ = 'prediction_logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    predict_date = Column(DateTime)
    category = Column(String(20))
    predicted_sales = Column(Integer)
    model_name = Column(String(50))
    mae = Column(Float)
    r2 = Column(Float)


_engine = None
_Session = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(config.SQLALCHEMY_DATABASE_URI, echo=False)
    return _engine


def get_session():
    global _Session
    if _Session is None:
        _Session = sessionmaker(bind=get_engine())
    return _Session()


def init_db():
    """创建所有表。"""
    engine = get_engine()
    Base.metadata.create_all(engine)
    return engine


def is_empty():
    """判断 orders 表是否为空。"""
    from sqlalchemy import text
    eng = get_engine()
    with eng.connect() as conn:
        r = conn.execute(text('SELECT COUNT(*) FROM orders')).scalar()
    return r == 0
