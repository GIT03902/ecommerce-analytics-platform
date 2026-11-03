# -*- coding: utf-8 -*-
"""
Flask 主应用：电商销售数据分析与智能预警平台
路由：
  /login, /logout              登录认证
  /                            首页（系统概览）
  /dashboard                   经营仪表盘
  /trend                        销量趋势分析
  /customers                    客户分析（RFM）
  /products                     商品分析
  /warning                      智能预警中心
  /forecast                     销量预测
  /export/<type>                数据导出
  /api/*                        JSON 接口
  /health                       健康检查（部署探活）
启动：python run.py
"""
import os

from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
from flask_login import login_required, current_user

import config
from models.database import init_db, is_empty
from services.auth import login_manager, do_login, do_logout
import services.analytics as A
import services.exporter as E
from models import rfm as R
from models import predictor as P


def create_app():
    app = Flask(__name__)
    app.config.from_object(config)
    app.jinja_env.auto_reload = True

    init_db()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = '请先登录'

    @app.context_processor
    def inject_globals():
        return {
            'current_user': current_user,
            'app_name': '电商销售数据分析与智能预警平台',
            'year': 2024,
        }

    @app.template_global('fmt_money')
    def fmt_money(n):
        if n is None:
            return '0'
        n = float(n)
        if n >= 1e8:
            return f'{n / 1e8:.2f} 亿'
        if n >= 1e4:
            return f'{n / 1e4:.2f} 万'
        return f'{n:,.2f}'

    @app.template_global('fmt_num')
    def fmt_num(n):
        if n is None:
            return '0'
        return f'{int(n):,}'

    @app.before_request
    def _check_db():
        # 数据库未初始化时，除登录/静态/健康检查外，一律引导初始化
        if request.endpoint in ('login', 'logout', 'static', 'health', 'setup_page'):
            return
        if not current_user.is_authenticated:
            return
        try:
            if is_empty():
                return render_template('setup.html')
        except Exception:
            return render_template('setup.html')

    # ============ 认证 ============
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            if do_login(username, password):
                next_url = request.args.get('next') or url_for('index')
                return redirect(next_url)
            return render_template('login.html', error='用户名或密码错误')
        return render_template('login.html')

    @app.route('/logout')
    @login_required
    def logout():
        do_logout()
        return redirect(url_for('login'))

    @app.route('/setup')
    def setup_page():
        return render_template('setup.html')

    @app.route('/health')
    def health():
        return jsonify({'status': 'ok', 'service': 'ecommerce-analytics'})

    # ============ 业务页面 ============
    @app.route('/')
    @login_required
    def index():
        kpis = A.get_kpis()
        monthly = A.get_monthly_gmv()
        category = A.get_category_sales()
        return render_template('index.html', kpis=kpis, monthly_gmv=monthly, category_sales=category)

    @app.route('/dashboard')
    @login_required
    def dashboard():
        return render_template('dashboard.html',
            kpis=A.get_kpis(),
            monthly_gmv=A.get_monthly_gmv(),
            category_sales=A.get_category_sales(),
            top_products=A.get_top_products(10),
            region_sales=A.get_region_sales(),
            channel_dist=A.get_channel_dist(),
            user_growth=A.get_user_growth(),
        )

    @app.route('/trend')
    @login_required
    def trend():
        return render_template('trend.html',
            daily_sales=A.get_daily_sales(90),
            promo_impact=A.get_promo_impact(),
            category_monthly=A.get_category_monthly(),
        )

    @app.route('/customers')
    @login_required
    def customers():
        return render_template('customers.html',
            tier_dist=R.get_tier_distribution().to_dict(orient='records'),
            rfm_scatter=R.get_rfm_scatter(),
            churn_users=R.get_churn_users(),
            high_value=R.get_high_value_users(),
        )

    @app.route('/products')
    @login_required
    def products():
        return render_template('products.html',
            category_sales=A.get_category_sales(),
            top_products=A.get_top_products(15),
            slow_products=A.get_slow_products(15),
            low_stock=A.get_low_stock_products(),
        )

    @app.route('/warning')
    @login_required
    def warning():
        low_stock = A.get_low_stock_products()
        churn = R.get_churn_users()
        forecast = P.train_and_forecast()
        # 预警汇总
        stock_warning = sum(1 for x in low_stock if x['warning'] in ('紧急', '预警'))
        return render_template('warning.html',
            low_stock=low_stock,
            churn_users=churn,
            forecast=forecast,
            low_stock_count=len(low_stock),
            stock_warning_count=stock_warning,
            churn_count=len(churn),
        )

    @app.route('/forecast')
    @login_required
    def forecast():
        res = P.train_and_forecast()
        return render_template('forecast.html', **res)

    # ============ Agent 智能分析助手 ============
    @app.route('/agent')
    @login_required
    def agent():
        return render_template('agent.html')

    @app.route('/api/agent/ask', methods=['POST'])
    @login_required
    def agent_ask():
        from services.agent import agent as bot
        payload = request.get_json(silent=True) or {}
        q = payload.get('question', '')
        uid = str(current_user.id) if current_user.is_authenticated else 'web-user'
        return jsonify(bot.ask(q, user_id=uid))

    @app.route('/api/dify/status')
    @login_required
    def dify_status():
        from services import dify_agent as D
        return jsonify(D.get_status())

    @app.route('/api/dify/reset', methods=['POST'])
    @login_required
    def dify_reset():
        from services import dify_agent as D
        uid = str(current_user.id) if current_user.is_authenticated else 'web-user'
        return jsonify(D.reset_conversation(uid))

    # ============ 数据导出 ============
    @app.route('/export/<ftype>')
    @login_required
    def export(ftype):
        m = {
            'kpi': E.export_kpi_summary,
            'category': E.export_category_sales,
            'top_products': E.export_top_products,
            'rfm': E.export_rfm,
            'low_stock': E.export_low_stock,
            'forecast': E.export_forecast,
        }
        if ftype not in m:
            return '未知导出类型', 404
        try:
            path = m[ftype]()
            return send_file(path, as_attachment=True, download_name=os.path.basename(path))
        except Exception as e:
            return f'导出失败：{e}', 500

    # ============ JSON API（供二次开发）============
    @app.route('/api/kpis')
    @login_required
    def api_kpis():
        return jsonify(A.get_kpis())

    @app.route('/api/monthly-gmv')
    @login_required
    def api_monthly():
        return jsonify(A.get_monthly_gmv())

    @app.route('/api/category-sales')
    @login_required
    def api_category():
        return jsonify(A.get_category_sales())

    @app.route('/api/top-products')
    @login_required
    def api_top():
        n = request.args.get('n', 10, type=int)
        return jsonify(A.get_top_products(n))

    @app.route('/api/region-sales')
    @login_required
    def api_region():
        return jsonify(A.get_region_sales())

    @app.route('/api/forecast')
    @login_required
    def api_forecast():
        return jsonify(P.train_and_forecast())

    @app.route('/api/low-stock')
    @login_required
    def api_low_stock():
        return jsonify(A.get_low_stock_products())

    @app.route('/api/tier-dist')
    @login_required
    def api_tier():
        return jsonify(R.get_tier_distribution().to_dict(orient='records'))

    # ============ Dify 工具开放 API（Bearer Token 鉴权）============
    # 供 Dify Agent 工具调用：大模型理解意图后回调这些接口获取结构化数据
    # 鉴权方式：请求头 Authorization: Bearer <DIFY_TOOL_TOKEN>
    def _check_tool_token():
        auth = request.headers.get('Authorization', '')
        token = auth.replace('Bearer ', '').strip()
        expected = getattr(config, 'DIFY_TOOL_TOKEN', '')
        return bool(token and expected and token == expected)

    @app.route('/api/tool/kpis')
    def tool_kpis():
        """经营概况：GMV、订单、客单价、复购率等核心 KPI"""
        if not _check_tool_token():
            return jsonify({'error': 'unauthorized'}), 401
        return jsonify(A.get_kpis())

    @app.route('/api/tool/monthly')
    def tool_monthly():
        """月度 GMV 趋势"""
        if not _check_tool_token():
            return jsonify({'error': 'unauthorized'}), 401
        return jsonify(A.get_monthly_gmv())

    @app.route('/api/tool/category')
    def tool_category():
        """品类销售分析"""
        if not _check_tool_token():
            return jsonify({'error': 'unauthorized'}), 401
        return jsonify(A.get_category_sales())

    @app.route('/api/tool/top-products')
    def tool_top():
        """热销商品 Top N"""
        if not _check_tool_token():
            return jsonify({'error': 'unauthorized'}), 401
        n = request.args.get('n', 10, type=int)
        return jsonify(A.get_top_products(n))

    @app.route('/api/tool/low-stock')
    def tool_low_stock():
        """库存预警商品"""
        if not _check_tool_token():
            return jsonify({'error': 'unauthorized'}), 401
        return jsonify(A.get_low_stock_products())

    @app.route('/api/tool/tier')
    def tool_tier():
        """客户 RFM 分层"""
        if not _check_tool_token():
            return jsonify({'error': 'unauthorized'}), 401
        return jsonify(R.get_tier_distribution().to_dict(orient='records'))

    @app.route('/api/tool/forecast')
    def tool_forecast():
        """随机森林销量预测"""
        if not _check_tool_token():
            return jsonify({'error': 'unauthorized'}), 401
        return jsonify(P.train_and_forecast())

    @app.route('/api/tool/region')
    def tool_region():
        """全国区域销售分布"""
        if not _check_tool_token():
            return jsonify({'error': 'unauthorized'}), 401
        return jsonify(A.get_region_sales())

    @app.route('/api/tool/channels')
    def tool_channels():
        """下单渠道分布"""
        if not _check_tool_token():
            return jsonify({'error': 'unauthorized'}), 401
        return jsonify(A.get_channel_dist())

    # ============ 错误处理 ============
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('error.html', code=404, msg='页面不存在'), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('error.html', code=500, msg='服务器内部错误'), 500

    return app


app = create_app()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
