# -*- coding: utf-8 -*-
"""
Dify 智能体集成客户端
====================
将电商分析助手的核心对话能力接入 Dify 平台：

工作流程：
  用户提问 → Flask /api/agent/ask
           → 本模块调用 Dify Agent 的 chat-messages API
           → Dify 大模型理解意图并调度工具
           → 工具回调 Flask /api/tool/* 开放 API 获取结构化数据
           → Dify 整合后返回自然语言回答
           → 前端展示

特性：
  - 多轮会话支持（conversation_id 自动维护）
  - 超时 / 连接失败自动降级到本地规则引擎
  - 与本地 agent.ask 返回结构兼容

依赖：requests
"""
import requests
import config

# 会话存储：user_id -> conversation_id（演示用内存，生产可换 Redis）
_conversations = {}


def is_enabled():
    """Dify 是否启用：DIFY_ENABLED=True 且配置了 API Key"""
    return (getattr(config, 'DIFY_ENABLED', False)
            and bool(getattr(config, 'DIFY_API_KEY', '')))


def _suggest():
    return ['全年经营概况如何？', '哪个品类卖得最好？', '库存预警情况',
            '未来7天销量预测', '客户分层分布', '促销效果分析']


def ask(question, user_id='web-user', conversation_id=None):
    """
    调用 Dify Agent 对话接口。

    Args:
        question: 用户问题
        user_id: 用户标识（用于多轮会话隔离）
        conversation_id: 会话 ID（None 时自动复用历史会话）

    Returns:
        与本地 agent.ask 兼容的 dict：
        {
            'answer': 自然语言回答,
            'mode': 'dify' | 'fallback',
            'conversation_id': 会话ID,
            'suggest': 建议问题列表
        }
    """
    base = getattr(config, 'DIFY_BASE_URL', 'http://localhost').rstrip('/')
    api_key = config.DIFY_API_KEY
    url = f'{base}/v1/chat-messages'

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }

    # 复用已有会话，支持多轮上下文
    if conversation_id is None:
        conversation_id = _conversations.get(user_id, '')

    payload = {
        'inputs': {},
        'query': question,
        'response_mode': 'streaming',  # Agent 应用仅支持流式响应
        'conversation_id': conversation_id or '',
        'user': user_id,
    }

    try:
        # 流式响应：逐行读取 SSE 数据并拼接 answer
        resp = requests.post(url, json=payload, headers=headers, timeout=60, stream=True)
        resp.raise_for_status()

        answer_parts = []
        final_answer = ''
        new_cid = ''
        import json
        for line in resp.iter_lines(decode_unicode=True):
            if not line or not line.startswith('data:'):
                continue
            chunk = line[5:].strip()
            if not chunk or chunk == '[DONE]':
                continue
            try:
                evt = json.loads(chunk)
            except Exception:
                continue
            event_type = evt.get('event', '')
            # 记录会话 ID
            cid = evt.get('conversation_id', '')
            if cid:
                new_cid = cid
            # agent_thought 是推理过程，跳过不展示
            # agent_message / message 才是实际回答内容
            if event_type in ('agent_message', 'message'):
                part = evt.get('answer', '')
                if part:
                    answer_parts.append(part)
                # message 事件通常包含完整回答，优先使用
                if event_type == 'message' and part:
                    final_answer = part
            elif event_type in ('message_end', 'agent_message_end'):
                # 结束事件，确认会话 ID
                pass

        # 优先用 message 事件的完整回答，否则拼接 agent_message 片段
        answer = final_answer or ''.join(answer_parts).strip() or '（Dify 未返回回答内容）'

        # 记录会话 ID 以支持后续多轮对话
        if new_cid:
            _conversations[user_id] = new_cid

        return {
            'answer': answer,
            'mode': 'dify',
            'conversation_id': new_cid,
            'suggest': _suggest(),
        }

    except requests.exceptions.Timeout:
        return {
            'answer': '⏱️ Dify 响应超时，已自动切换本地规则引擎。'
                      '请稍后重试，或检查 Dify 服务状态。',
            'mode': 'fallback',
            'suggest': _suggest(),
        }
    except requests.exceptions.ConnectionError:
        return {
            'answer': '⚠️ 无法连接 Dify 服务，已切换本地规则引擎。\n'
                      '请确认：\n'
                      '1. Dify 已启动（docker compose ps 查看容器状态）\n'
                      '2. config.py 中 DIFY_BASE_URL 配置正确\n'
                      '3. 网络可达',
            'mode': 'fallback',
            'suggest': _suggest(),
        }
    except Exception as e:
        return {
            'answer': f'Dify 调用异常：{e}',
            'mode': 'fallback',
            'suggest': _suggest(),
        }


def reset_conversation(user_id='web-user'):
    """重置指定用户的会话上下文，开启全新对话。"""
    _conversations.pop(user_id, None)
    return {'status': 'ok', 'message': '会话已重置'}


def get_status():
    """获取 Dify 集成状态信息（供前端 / 调试使用）。"""
    return {
        'enabled': is_enabled(),
        'base_url': getattr(config, 'DIFY_BASE_URL', ''),
        'has_api_key': bool(getattr(config, 'DIFY_API_KEY', '')),
        'tool_token_configured': bool(getattr(config, 'DIFY_TOOL_TOKEN', '')),
        'active_conversations': len(_conversations),
    }
