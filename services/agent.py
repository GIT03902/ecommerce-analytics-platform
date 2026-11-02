# -*- coding: utf-8 -*-
"""
电商分析智能体（Analytics Agent）
架构：意图识别 → 工具调度 → 结果生成（文字摘要 + 数据表 + 图表配置 + 追问建议）
零外部依赖，纯本地规则驱动，演示稳定。工具层复用 services.analytics 与 models。
"""
import services.analytics as A
from models import rfm as R
from models import predictor as P

# ECharts 通用色板
_COLORS = ['#2563eb', '#16a34a', '#d97706', '#dc2626', '#0891b2', '#7c3aed', '#db2777', '#65a30d']


def _fmt_money(n):
    n = float(n)
    if n >= 1e8:
        return f'{n/1e8:.2f} 亿'
    if n >= 1e4:
        return f'{n/1e4:.2f} 万'
    return f'{n:,.2f}'


class AnalyticsAgent:
    """电商分析智能体。"""

    def __init__(self):
        # (关键词列表, 意图名, handler)
        self._intents = [
            (['gmv', '成交', '销售额', '营收', '营业额', '交易额', '总收入', '卖了多少钱', '赚了多少'], 'revenue', self._h_revenue),
            (['月度', '每月', '月趋势', '月销量', '月报', '按月'], 'monthly', self._h_monthly),
            (['每天', '日销量', '日趋势', '近期', '最近', '日常'], 'daily', self._h_daily),
            (['品类', '类别', '分类', '类目', '哪个类', '商品类'], 'category', self._h_category),
            (['热销', '爆款', '排行', 'top', '排名', '卖得最好', '畅销', '最好卖'], 'top_products', self._h_top),
            (['地区', '地域', '省份', '城市', '哪里', '区域', '地图', '全国'], 'region', self._h_region),
            (['渠道', '来源', 'app', '小程序', 'pc', '下单方式', '下单来源'], 'channel', self._h_channel),
            (['库存', '缺货', '补货', '存货', '备货', '仓库'], 'low_stock', self._h_low_stock),
            (['滞销', '卖不动', '库存积压', '不好卖', '冷门'], 'slow', self._h_slow),
            (['客户分层', 'rfm', '高价值', '客户结构', '客户分', '用户分层', '分层'], 'tier', self._h_tier),
            (['流失', '沉寂', '召回', '不活跃', '睡眠', '沉睡'], 'churn', self._h_churn),
            (['促销', '大促', '活动', '618', '双11', '双12', '打折', '优惠', '大卖'], 'promo', self._h_promo),
            (['预测', '未来', 'forecast', '下周', '接下来', '预计', '备货预测'], 'forecast', self._h_forecast),
            (['客单价', '单均', '每单', '一单'], 'aov', self._h_aov),
            (['复购', '回头', '重复购买', '回购'], 'repurchase', self._h_repurchase),
            (['概况', '总览', 'overview', '整体', '综合', '数据怎么样', '看下数据', '汇报'], 'overview', self._h_revenue),
        ]

    # ============ 主入口 ============
    def ask(self, question):
        q = (question or '').strip().lower()
        if not q:
            return {'answer': '请输入您想了解的分析问题。', 'suggest': self._default_suggest()}
        for keywords, name, handler in self._intents:
            if any(k in q for k in keywords):
                try:
                    res = handler()
                    res['intent'] = name
                    res['question'] = question
                    res.setdefault('suggest', self._default_suggest())
                    return res
                except Exception as e:
                    return {'answer': f'分析过程中出现异常：{e}', 'intent': name, 'question': question}
        return self._fallback(question)

    def _default_suggest(self):
        return ['全年经营概况如何？', '哪个品类卖得最好？', '库存预警情况', '未来7天销量预测', '客户分层分布']

    def _fallback(self, question):
        return {
            'answer': (
                '我目前支持以下分析方向，可以直接点击下方建议问题，或换个说法提问：\n'
                '• 经营概况（GMV/订单/客单价/复购率）\n'
                '• 销量趋势（月度/日/品类堆叠）\n'
                '• 商品分析（热销榜/滞销/库存预警）\n'
                '• 客户分析（RFM 分层/流失预警）\n'
                '• 促销效果 / 销量预测'
            ),
            'question': question,
            'suggest': self._default_suggest(),
        }

    # ============ 工具 Handlers ============
    def _h_revenue(self):
        k = A.get_kpis()
        ans = (
            f"📊 全年经营概况\n"
            f"━━━━━━━━━━━━━━\n"
            f"• 总成交额 GMV：¥{_fmt_money(k['total_gmv'])}\n"
            f"• 总订单数：{k['total_orders']:,} 单\n"
            f"• 消费用户：{k['total_users']:,} 人\n"
            f"• 客单价：¥{_fmt_money(k['aov'])}\n"
            f"• 复购率：{k['repurchase_rate']:.1f}%\n"
            f"• 促销订单占比：{k['promo_rate']:.1f}%\n"
            f"• 总销量：{k['total_qty']:,} 件\n\n"
            f"💡 业务洞察：复购率达 {k['repurchase_rate']:.0f}%，用户黏性较强；"
            f"建议持续优化促销节奏提升 GMV。"
        )
        return {'answer': ans}

    def _h_monthly(self):
        data = A.get_monthly_gmv()
        months = [d['month'] for d in data]
        gmv = [round(d['gmv'] / 10000, 2) for d in data]
        orders = [d['orders'] for d in data]
        peak = max(data, key=lambda x: x['gmv'])
        ans = (
            f"📈 月度 GMV 趋势（单位：万元）\n"
            f"━━━━━━━━━━━━━━\n"
            f"• 峰值月份：{peak['month']}，GMV ¥{_fmt_money(peak['gmv'])}（{peak['orders']:,} 单）\n"
            f"• 12 个月累计：¥{_fmt_money(sum(d['gmv'] for d in data))}\n\n"
            f"💡 业务洞察：{peak['month']} 为全年高峰，与大促节点吻合，"
            f"建议在大促前 2 周开始备货与营销预热。"
        )
        chart = {
            'tooltip': {'trigger': 'axis'},
            'legend': {'data': ['GMV(万元)', '订单数'], 'top': 0},
            'grid': {'left': 50, 'right': 50, 'top': 40, 'bottom': 30},
            'xAxis': {'type': 'category', 'data': months},
            'yAxis': [{'type': 'value', 'name': 'GMV(万)'}, {'type': 'value', 'name': '订单'}],
            'series': [
                {'name': 'GMV(万元)', 'type': 'bar', 'data': gmv, 'itemStyle': {'color': '#2563eb', 'borderRadius': [4, 4, 0, 0]}},
                {'name': '订单数', 'type': 'line', 'yAxisIndex': 1, 'data': orders, 'itemStyle': {'color': '#16a34a'}},
            ],
        }
        return {'answer': ans, 'chart': chart}

    def _h_daily(self):
        data = A.get_daily_sales(30)
        dates = [d['order_date'] for d in data]
        sales = [d['sales'] for d in data]
        avg = sum(sales) / len(sales) if sales else 0
        peak = max(data, key=lambda x: x['sales'])
        ans = (
            f"📅 近 30 天日销量趋势\n"
            f"━━━━━━━━━━━━━━\n"
            f"• 日均销量：{avg:.0f} 件\n"
            f"• 峰值日：{peak['order_date']}，{peak['sales']} 件\n"
            f"• 峰值日 GMV：¥{_fmt_money(peak['gmv'])}\n\n"
            f"💡 业务洞察：注意周末与大促日的销量上量规律。"
        )
        chart = {
            'tooltip': {'trigger': 'axis'},
            'grid': {'left': 50, 'right': 20, 'top': 20, 'bottom': 30},
            'xAxis': {'type': 'category', 'data': dates},
            'yAxis': {'type': 'value', 'name': '销量(件)'},
            'series': [{'type': 'line', 'data': sales, 'smooth': True, 'areaStyle': {'opacity': 0.2}, 'itemStyle': {'color': '#2563eb'}}],
        }
        return {'answer': ans, 'chart': chart}

    def _h_category(self):
        data = A.get_category_sales()
        top = data[0]
        ans = (
            f"🛍️ 品类销售分析\n"
            f"━━━━━━━━━━━━━━\n"
            f"• 销售最好的品类：{top['category']}，GMV ¥{_fmt_money(top['gmv'])}（占比 {top['share']}%）\n"
            f"• 共 {len(data)} 个品类\n\n"
            f"💡 业务洞察：{top['category']} 是核心利润来源，"
            f"建议加大该品类的选品与库存投入。"
        )
        chart = {
            'tooltip': {'trigger': 'item', 'formatter': '{b}: ¥{c} ({d}%)'},
            'legend': {'bottom': 0},
            'series': [{'type': 'pie', 'radius': ['38%', '68%'],
                        'data': [{'name': d['category'], 'value': d['gmv']} for d in data]}],
        }
        table = {
            'columns': ['品类', 'GMV(元)', '销量(件)', '订单数', '占比(%)'],
            'rows': [[d['category'], f"{d['gmv']:,.0f}", d['qty'], d['orders'], d['share']] for d in data[:8]],
        }
        return {'answer': ans, 'chart': chart, 'table': table}

    def _h_top(self):
        data = A.get_top_products(10)
        ans = (
            f"🏆 热销商品 Top 10\n"
            f"━━━━━━━━━━━━━━\n"
            f"• 销冠：{data[0]['product_name']}，GMV ¥{_fmt_money(data[0]['gmv'])}\n"
            f"• Top3 合计 GMV：¥{_fmt_money(sum(d['gmv'] for d in data[:3]))}\n\n"
            f"💡 业务洞察：建议对 Top 商品保证库存充足，避免缺货损失。"
        )
        chart = {
            'tooltip': {'trigger': 'axis', 'axisPointer': {'type': 'shadow'}},
            'grid': {'left': 160, 'right': 50, 'top': 10, 'bottom': 30},
            'xAxis': {'type': 'value'},
            'yAxis': {'type': 'category', 'data': [d['product_name'] for d in data][::-1]},
            'series': [{'type': 'bar', 'data': [d['gmv'] for d in data][::-1],
                        'itemStyle': {'color': '#16a34a', 'borderRadius': [0, 4, 4, 0]},
                        'label': {'show': True, 'position': 'right', 'formatter': lambda p: '¥' + _fmt_money(p.value)}}],
        }
        table = {
            'columns': ['商品', '品类', 'GMV(元)', '销量(件)', '订单数'],
            'rows': [[d['product_name'], d['category'], f"{d['gmv']:,.0f}", d['qty'], d['orders']] for d in data[:8]],
        }
        return {'answer': ans, 'chart': chart, 'table': table}

    def _h_region(self):
        data = A.get_region_sales()
        top3 = data[:3]
        ans = (
            f"🗺️ 全国销售地域分布\n"
            f"━━━━━━━━━━━━━━\n"
            f"• 销售前三省份：{', '.join(d['name'] for d in top3)}\n"
            f"• {top3[0]['name']} GMV：¥{top3[0]['value']} 万\n\n"
            f"💡 业务洞察：东部沿海为核心市场，建议在低渗透省份加大营销投入。"
        )
        chart = {
            'tooltip': {'trigger': 'item', 'formatter': '{b}: ¥{c} 万'},
            'visualMap': {'min': 0, 'max': max(d['value'] for d in data) or 100, 'left': 20, 'bottom': 20,
                          'text': ['高', '低'], 'calculable': True, 'inRange': {'color': ['#dbeafe', '#3b82f6', '#1d4ed8']}},
            'series': [{'type': 'map', 'map': 'china', 'data': data}],
        }
        return {'answer': ans, 'chart': chart, 'need_map': True}

    def _h_channel(self):
        data = A.get_channel_dist()
        top = max(data, key=lambda x: x['orders'])
        ans = (
            f"📱 下单渠道分布\n"
            f"━━━━━━━━━━━━━━\n"
            f"• 主力渠道：{top['channel']}（{top['orders']:,} 单）\n"
            f"• 渠道数：{len(data)} 个\n\n"
            f"💡 业务洞察：移动端为主，建议持续优化 APP/小程序体验。"
        )
        chart = {
            'tooltip': {'trigger': 'item', 'formatter': '{b}: {c} 单 ({d}%)'},
            'legend': {'bottom': 0},
            'series': [{'type': 'pie', 'radius': ['30%', '70%'], 'roseType': 'radius',
                        'data': [{'name': d['channel'], 'value': d['orders']} for d in data]}],
        }
        return {'answer': ans, 'chart': chart}

    def _h_low_stock(self):
        data = A.get_low_stock_products()
        urgent = [d for d in data if d['warning'] in ('紧急', '预警')]
        ans = (
            f"⚠️ 库存预警分析\n"
            f"━━━━━━━━━━━━━━\n"
            f"• 需关注商品：{len(data)} 个\n"
            f"• 紧急/预警级：{len(urgent)} 个\n\n"
            f"💡 业务洞察：建议立即对紧急级商品启动补货流程，避免断货损失。"
        )
        table = {
            'columns': ['商品', '品类', '库存', '近30天销量', '可售天数', '级别'],
            'rows': [[d['product_name'], d['category'], d['stock'], d['sold_30d'],
                      ('∞' if d['est_days'] >= 9999 else d['est_days']), d['warning']] for d in data[:8]],
        }
        return {'answer': ans, 'table': table}

    def _h_slow(self):
        data = A.get_slow_products(10)
        ans = (
            f"📉 滞销商品分析\n"
            f"━━━━━━━━━━━━━━\n"
            f"• 滞销商品数：{len(data)} 个\n"
            f"• 最滞销：{data[0]['product_name']}（累计销量 {data[0]['qty']} 件）\n\n"
            f"💡 业务洞察：建议通过促销清仓或下架处理，释放库存资金。"
        )
        table = {
            'columns': ['商品', '品类', '库存', '累计销量', '累计GMV'],
            'rows': [[d['product_name'], d['category'], d['stock'], d['qty'], f"{d['gmv']:,.0f}"] for d in data[:8]],
        }
        return {'answer': ans, 'table': table}

    def _h_tier(self):
        dist = R.get_tier_distribution().to_dict(orient='records')
        hv = next((d for d in dist if d['tier'] == '高价值客户'), None)
        churn = next((d for d in dist if d['tier'] == '流失预警客户'), None)
        ans = (
            f"👥 客户 RFM 分层分析\n"
            f"━━━━━━━━━━━━━━\n"
            f"• 高价值客户：{hv['count']} 人（贡献金额占比 {hv['monetary_share']}%）\n"
            f"• 流失预警客户：{churn['count']} 人\n"
            f"• 客户总数：{sum(d['count'] for d in dist)} 人\n\n"
            f"💡 业务洞察：高价值客户贡献主要收入，需重点维系；"
            f"流失预警客户建议定向优惠券召回。"
        )
        colors = {'高价值客户': '#16a34a', '潜力客户': '#2563eb', '一般客户': '#d97706', '流失预警客户': '#dc2626'}
        chart = {
            'tooltip': {'trigger': 'item', 'formatter': '{b}: {c} 人 ({d}%)'},
            'legend': {'bottom': 0},
            'series': [{'type': 'pie', 'radius': ['40%', '70%'],
                        'data': [{'name': d['tier'], 'value': d['count'], 'itemStyle': {'color': colors.get(d['tier'])}} for d in dist]}],
        }
        table = {
            'columns': ['层级', '人数', '平均金额(元)', '平均频次', '金额占比(%)'],
            'rows': [[d['tier'], d['count'], f"{d['avg_monetary']:,.0f}", f"{d['avg_frequency']:.1f}", d['monetary_share']] for d in dist],
        }
        return {'answer': ans, 'chart': chart, 'table': table}

    def _h_churn(self):
        data = R.get_churn_users()
        high_value_churn = [u for u in data if u['monetary'] > 3000]
        ans = (
            f"🚨 客户流失预警\n"
            f"━━━━━━━━━━━━━━\n"
            f"• 流失预警客户：{len(data)} 人（沉寂 > 90 天）\n"
            f"• 其中高价值流失：{len(high_value_churn)} 人\n\n"
            f"💡 业务洞察：高价值流失客户需优先召回，"
            f"建议发放大额优惠券 + 个性化 Push。"
        )
        table = {
            'columns': ['用户ID', '累计金额(元)', '频次', '沉寂天数'],
            'rows': [[u['user_id'], f"{u['monetary']:,.0f}", u['frequency'], u['recency']] for u in data[:8]],
        }
        return {'answer': ans, 'table': table}

    def _h_promo(self):
        data = A.get_promo_impact()
        promo = next(d for d in data if d['label'] == '促销日')
        normal = next(d for d in data if d['label'] == '普通日')
        lift = (promo['gmv'] / normal['gmv'] - 1) * 100 if normal['gmv'] else 0
        ans = (
            f"🎉 促销效果分析\n"
            f"━━━━━━━━━━━━━━\n"
            f"• 促销日 GMV：¥{_fmt_money(promo['gmv'])}（{promo['orders']:,} 单）\n"
            f"• 普通日 GMV：¥{_fmt_money(normal['gmv'])}（{normal['orders']:,} 单）\n"
            f"• 促销提升：+{lift:.0f}%\n"
            f"• 促销日客单价：¥{_fmt_money(promo['avg_amount'])}\n\n"
            f"💡 业务洞察：促销显著拉高 GMV 与客单价，策略有效，"
            f"建议持续优化大促节奏。"
        )
        chart = {
            'tooltip': {'trigger': 'axis', 'axisPointer': {'type': 'shadow'}},
            'grid': {'left': 50, 'right': 30, 'top': 20, 'bottom': 30},
            'xAxis': {'type': 'category', 'data': [d['label'] for d in data]},
            'yAxis': [{'type': 'value', 'name': 'GMV'}],
            'series': [{'name': 'GMV', 'type': 'bar', 'data': [d['gmv'] for d in data],
                        'itemStyle': {'color': '#dc2626', 'borderRadius': [4, 4, 0, 0]}}],
        }
        return {'answer': ans, 'chart': chart}

    def _h_forecast(self):
        res = P.train_and_forecast()
        future_total = sum(d['predicted'] for d in res['future_total'])
        ans = (
            f"🔮 未来 7 天销量预测（随机森林模型）\n"
            f"━━━━━━━━━━━━━━\n"
            f"• 模型：RandomForest（{res['n_estimators']} 棵树）\n"
            f"• 测试集 R²：{res['r2']:.4f}，MAE：{res['mae']:.2f}\n"
            f"• 未来 7 天预测总销量：{future_total:,} 件\n\n"
            f"💡 业务洞察：建议按预测结果提前备货，"
            f"避免热销品类断货。模型 R² 越接近 1 越优。"
        )
        recent = res['recent_actual']
        future = res['future_total']
        chart = {
            'tooltip': {'trigger': 'axis'},
            'legend': {'data': ['实际销量', '预测销量'], 'top': 0},
            'grid': {'left': 50, 'right': 20, 'top': 40, 'bottom': 30},
            'xAxis': {'type': 'category', 'data': [d['order_date'] for d in recent] + [d['order_date'] for d in future]},
            'yAxis': {'type': 'value', 'name': '销量(件)'},
            'series': [
                {'name': '实际销量', 'type': 'line', 'smooth': True,
                 'data': [d['actual'] for d in recent] + [None] * len(future), 'itemStyle': {'color': '#2563eb'}},
                {'name': '预测销量', 'type': 'line', 'smooth': True,
                 'data': [None] * len(recent) + [d['predicted'] for d in future],
                 'itemStyle': {'color': '#dc2626'}, 'lineStyle': {'type': 'dashed'}},
            ],
        }
        return {'answer': ans, 'chart': chart}

    def _h_aov(self):
        k = A.get_kpis()
        ans = (
            f"💰 客单价分析\n"
            f"━━━━━━━━━━━━━━\n"
            f"• 客单价：¥{_fmt_money(k['aov'])}\n"
            f"• 总 GMV：¥{_fmt_money(k['total_gmv'])}\n"
            f"• 总订单：{k['total_orders']:,} 单\n\n"
            f"💡 业务洞察：可通过关联销售、满减门槛提升客单价。"
        )
        return {'answer': ans}

    def _h_repurchase(self):
        k = A.get_kpis()
        ans = (
            f"🔁 复购率分析\n"
            f"━━━━━━━━━━━━━━\n"
            f"• 复购率：{k['repurchase_rate']:.1f}%\n"
            f"• 消费用户：{k['total_users']:,} 人\n\n"
            f"💡 业务洞察：复购率较高，用户黏性强，"
            f"建议通过会员体系进一步提升忠诚度。"
        )
        return {'answer': ans}


# 全局单例
agent = AnalyticsAgent()
