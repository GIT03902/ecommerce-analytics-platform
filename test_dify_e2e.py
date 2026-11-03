"""Dify 集成端到端验证脚本"""
import os
import sys
import requests

# 确认环境变量
print("=" * 50)
print("Dify 集成端到端验证")
print("=" * 50)
print(f"DIFY_ENABLED  = {os.environ.get('DIFY_ENABLED')}")
print(f"DIFY_API_KEY  = {os.environ.get('DIFY_API_KEY', '')[:20]}...")
print(f"DIFY_BASE_URL = {os.environ.get('DIFY_BASE_URL')}")
print(f"DIFY_TOOL_TOKEN = {os.environ.get('DIFY_TOOL_TOKEN')}")
print()

# 创建会话
s = requests.Session()
BASE = "http://localhost:5000"

# 1. 登录
print("[1/4] 登录...")
r = s.post(f"{BASE}/login", data={
    "username": "admin",
    "password": "admin123"
}, allow_redirects=False, timeout=10)
print(f"    登录响应: HTTP {r.status_code}")
if r.status_code in (302, 200):
    print("    ✅ 登录成功")
else:
    print(f"    ❌ 登录失败: {r.status_code}")
    sys.exit(1)

# 2. 查询 Dify 状态
print()
print("[2/4] 查询 Dify 状态...")
r = s.get(f"{BASE}/api/dify/status", timeout=10)
print(f"    状态接口: HTTP {r.status_code}")
try:
    data = r.json()
    print(f"    ✅ Dify 启用: {data.get('enabled')}")
    print(f"    模式: {data.get('mode', 'unknown')}")
    print(f"    连接: {data.get('connected', 'unknown')}")
except Exception as e:
    print(f"    响应: {r.text[:200]}")

# 3. 测试 Dify Agent 对话
print()
print("[3/4] 测试 Dify Agent 对话...")
print("    问题: '最近销售情况怎么样？'")
r = s.post(f"{BASE}/api/agent/ask", json={
    "question": "最近销售情况怎么样？"
}, timeout=60)
print(f"    Agent 响应: HTTP {r.status_code}")
try:
    data = r.json()
    answer = data.get("answer", "")
    mode = data.get("mode", "unknown")
    print(f"    模式: {mode}")
    print(f"    回答前200字: {answer[:200]}")
    if mode == "dify" or "dify" in str(mode).lower():
        print("    ✅ Dify 大模型模式已激活！")
    else:
        print(f"    ⚠️ 当前模式: {mode}（可能 Dify 降级到本地引擎）")
except Exception as e:
    print(f"    ❌ 解析失败: {e}")
    print(f"    原始响应: {r.text[:300]}")

# 4. 测试工具 API（Dify 回调用）
print()
print("[4/4] 测试工具 API（供 Dify 回调）...")
r = requests.get(f"{BASE}/api/tool/kpis", headers={
    "Authorization": "Bearer ecommerce-dify-tool-2024"
}, timeout=10)
print(f"    工具API kpis: HTTP {r.status_code}")
if r.status_code == 200:
    print("    ✅ 工具 API 正常，Dify 可回调获取数据")
    try:
        kpis = r.json()
        if isinstance(kpis, list) and len(kpis) > 0:
            print(f"    返回 {len(kpis)} 条 KPI 数据")
    except Exception:
        pass
else:
    print(f"    ❌ 工具 API 异常")

print()
print("=" * 50)
print("验证完成！请在浏览器访问 http://localhost:5000")
print("登录后进入「智能分析助手」页面，标题旁徽章应显示「Dify 大模型」")
print("=" * 50)
