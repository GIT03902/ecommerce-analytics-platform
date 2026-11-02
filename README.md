# 电商销售数据分析与智能预警平台

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.1-000000?logo=flask&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-1.7-F7931E?logo=scikitlearn&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Platform](https://img.shields.io/badge/Platform-Web%20%2B%20Docker-blue)

> 基于 Flask + 随机森林的全栈电商数据分析系统，融合 RFM 客户分层、K-Means 聚类、随机森林销量预测，提供可视化仪表盘与智能预警能力。

<table>
<tr>
<td align="center"><b>68,364</b><br><sub>订单数据</sub></td>
<td align="center"><b>5,000</b><br><sub>消费者</sub></td>
<td align="center"><b>200</b><br><sub>商品</sub></td>
<td align="center"><b>2</b><br><sub>机器学习模型</sub></td>
<td align="center"><b>9</b><br><sub>功能页面</sub></td>
<td align="center"><b>16</b><br><sub>Agent 意图</sub></td>
</tr>
</table>

## 项目亮点

- **全栈架构**：Flask 后端 + ECharts 可视化 + SQLAlchemy 双模式数据库（SQLite/MySQL）
- **机器学习双模型**：K-Means 客户聚类 + 随机森林销量预测，模型可解释（特征重要性）
- **智能预警中心**：库存预警（按可售天数分级）、客户流失预警、销量预测驱动备货
- **真实数据模拟**：6 万+ 订单，覆盖 618/双11/双12/国庆/春节等促销高峰与周末效应
- **一键部署**：内置初始化脚本，自动生成数据、训练模型；支持 Docker
- **完整业务闭环**：登录认证 → 经营总览 → 仪表盘 → 趋势 → 客户 → 商品 → 预测 → 预警 → 数据导出

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Flask 3.1、Flask-Login（认证）、SQLAlchemy 2.0 |
| 数据库 | SQLite（默认零配置）/ MySQL 8（可切换） |
| 机器学习 | scikit-learn 1.7（KMeans、RandomForest、StandardScaler、LabelEncoder） |
| 数据处理 | pandas 2.2、numpy 1.26 |
| 可视化 | ECharts 5.5（柱/折/饼/散点/堆叠/中国地图） |
| 部署 | Docker、docker-compose |

## 目录结构

```
ecommerce-analytics-platform/
├── app.py                  # Flask 主应用（路由、认证、错误处理）
├── run.py                  # 启动入口
├── setup.py                # 一键初始化（生成数据 + 训练模型）
├── config.py               # 全局配置（双模式数据库、阈值、促销日）
├── requirements.txt
├── data/
│   └── generate_data.py    # 电商数据生成器（用户/商品/订单）
├── models/                 # 数据模型 + ML 模型
│   ├── database.py         # SQLAlchemy ORM（5 张表）
│   ├── rfm.py              # RFM + K-Means 客户分层
│   └── predictor.py        # 随机森林销量预测
├── services/               # 业务服务层
│   ├── analytics.py        # KPI 与图表数据查询
│   ├── auth.py             # Flask-Login 认证
│   └── exporter.py         # Excel 导出
├── templates/              # Jinja2 页面（8 个）
├── static/css/style.css    # 简洁大字体 UI
├── static/js/main.js       # ECharts 通用工具
├── Dockerfile / docker-compose.yml
├── start.bat / start.sh    # 一键启动脚本
└── README.md
```

## 快速开始

### 方式一：本地运行（推荐体验）

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 一键初始化（生成 6 万+ 订单数据 + 训练 RFM 与随机森林模型，约 1-2 分钟）
python setup.py

# 3. 启动
python run.py
```

访问 http://127.0.0.1:5000 ，使用 `admin / admin123` 登录。

Windows 用户也可直接双击 `start.bat`。

### 方式二：Docker 部署

```bash
docker-compose up --build
```

### 切换 MySQL 模式

```bash
# 先建库
mysql -uroot -p -e "CREATE DATABASE ecommerce DEFAULT CHARSET utf8mb4;"

# 设置环境变量后启动
export DB_MODE=mysql
export DB_USER=root
export DB_PWD=your_password
python setup.py && python run.py
```

## 核心功能页面

| 路由 | 功能 |
|------|------|
| `/login` | 管理员登录 |
| `/` | 系统概览（KPI + 功能导航） |
| `/dashboard` | 经营仪表盘（GMV/品类/地域地图/渠道/用户增长） |
| `/trend` | 销量趋势（90 天日趋势/促销对比/品类堆叠） |
| `/customers` | 客户分析（RFM 分层/散点/流失清单） |
| `/products` | 商品分析（热销榜/滞销品/库存预警） |
| `/forecast` | 销量预测（模型评估/预测曲线/特征重要性） |
| `/warning` | 智能预警中心（库存+流失+预测） |
| `/agent` | 🤖 智能分析助手（自然语言对话，自动调度分析工具） |
| `/export/<type>` | 数据导出 Excel（6 类报表） |
| `/api/*` | JSON 接口（供二次开发） |

## 机器学习模型说明

### 1. RFM + K-Means 客户分层
- **R**ecency：最近购买距今天数
- **F**requency：购买频次
- **M**onetary：累计消费金额
- StandardScaler 标准化后 K-Means（k=4）聚类
- 按金额降序标注：高价值 / 潜力 / 一般 / 流失预警

### 2. 随机森林销量预测
**特征工程**：品类编码、星期、月份、日、是否周末、是否促销、lag_1、lag_7、7 日滚动均值
**目标**：次日品类销量
**训练**：2024-01 ~ 2024-11 训练，2024-12 测试
**评估**：MAE、R²
**预测**：递推滞后，预测未来 7 天各品类销量

## 数据说明

数据由 `data/generate_data.py` 程序生成，模拟真实电商场景：
- 5000 用户、200 商品、8 品类、20 省份、4 渠道
- ~6 万订单，时间跨度 2024 全年
- 内置促销高峰：618、双11、双12、国庆、春节等
- 周末销量上量、用户复购分层（高价值/潜力/一般/低频）

## 默认账号

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | admin | admin123 |
| 分析师 | analyst | analyst123 |

## 技术亮点（面试可讲）

1. **双模式数据库抽象**：通过环境变量切换 SQLite/MySQL，零改动适配
2. **机器学习全流程**：特征工程 → 训练 → 评估 → 持久化(joblib) → 在线预测 → 预测日志留存
3. **业务驱动建模**：库存预警用"预计可售天数"分级，客户分层直连运营动作
4. **可视化丰富度**：6 类图表 + 中国地图 + 堆叠 + 散点 + 特征重要性
5. **工程化交付**：一键初始化、Docker、健康检查、Excel 导出、JSON API、错误处理
6. **AI 分析助手**：系统内置 Agent 智能体，自然语言意图识别 → 工具调度 → 对话式生成结论+图表+追问建议

## License

MIT
