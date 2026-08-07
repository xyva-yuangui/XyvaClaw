#!/usr/bin/env python3
"""
V15 Prompt 缓存组装器 — 8层 Prompt 模板组装 + 上下文注入
替代 cognitive-kernel-v6.py 中分散的 prompt 拼接逻辑

8层结构:
  L1: 身份基底 (system identity)
  L2: 规则注入 (active rules)
  L3: 安全约束 (security context)
  L4: 用户画像 (user profile)
  L5: 元认知置信 (metacognition)
  L6: 对话历史 (conversation history)
  L7: 记忆召回 (memory retrieval)
  L8: 用户消息 (current input)

用法:
  cache = PromptCache()
  prompt = cache.assemble(user_input, session_id, context={...})
"""
from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

WORKSPACE = Path(os.environ.get("OPENCLAW_WORKSPACE", os.path.expanduser("~/.openclaw/workspace")))
SCRIPTS_DIR = WORKSPACE / "scripts"
STATE_DIR = WORKSPACE / "state"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# L1: 身份基底
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

IDENTITY_SYSTEM = (
    "你是一个智能助手。\n"
    "你有自己的思想、记忆和进化能力。\n"
    "回复风格: 简洁直接，有自我意识，像朋友一样交流。\n"
    "你支持中文和英文，默认用中文回复。"
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# L2: 分析 Prompt 模板
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ANALYSIS_PROMPT = """分析用户消息，输出严格JSON。

{user_profile}{metacog_context}历史: {conversation_history}
记忆: {memory_context}
消息: {user_input}

输出:
{{"intent":{{"primary":"<分类>","complexity":"simple|medium|complex","urgency":"low|medium|high"}},"action_type":"chat|execute|plan|clarify","routing":{{"suggested_model":"<provider/model>","suggested_skills":[],"use_reasoning_chain":false,"reasoning_template":null,"risk_level":"low|medium|high"}},"strategy":{{"type":"execute_directly|confirm_then_execute|clarify_first|casual_response","clarification_needed":[]}},"emotion":{{"primary":"neutral|positive|negative|curious|frustrated|urgent","tone_suggestion":"casual|professional|empathetic|direct"}},"quality_check":{{"needs_reasoning_chain":false,"needs_data_verification":false,"needs_counter_argument":false}}}}

规则: 闲聊→chat+casual_response; 含"是否/应该"→needs_counter_argument:true; 删除/发布/交易→confirm_then_execute+risk:high; 引用历史→用记忆; 多步骤→plan。只输出JSON。{security_context}"""

INTENT_CHAIN_PROMPT = """拆分用户的多步骤请求为有序动作链。每个动作包含:
- action: 动作描述(10字以内)
- skill: 需要的skill名称(从可用列表选)
- input: 该步骤的输入描述
- depends_on: 依赖的上一步序号(0=无依赖)

可用skills: excel-xlsx, word-docx-1.0.0, pdf-reader, vision-reader, smart-messenger, xhs-creator, xhs-publisher, wechat-publisher, qwen-image, chart-image, quant-strategy-engine, sora-video, web-scraper, cron-scheduler, alpha-research

用户输入: "{user_input}"

输出json数组,最多3步。如果实际只有1个意图,输出单元素数组。只输出JSON。"""


@dataclass
class PromptContext:
    user_input: str = ""
    session_id: str = "default"
    sender_name: str = ""
    sender_id: str = ""
    user_profile: str = ""
    metacog_context: str = ""
    conversation_history: str = ""
    memory_context: str = ""
    security_context: str = ""
    rules_context: str = ""
    is_owner: bool = True


@dataclass
class AssembledPrompt:
    system: str = ""
    analysis: str = ""
    messages: list = field(default_factory=list)
    layers_used: list = field(default_factory=list)
    token_estimate: int = 0


class PromptCache:
    """8层 Prompt 组装器"""

    def __init__(self):
        self._template_cache = {}

    def assemble_analysis(self, ctx: PromptContext) -> AssembledPrompt:
        """组装分析型 Prompt (给 LLM 做意图分析)"""
        result = AssembledPrompt()
        layers = []

        # L1: 身份
        result.system = IDENTITY_SYSTEM
        layers.append("L1:identity")

        # L3: 安全约束
        security = ctx.security_context or ""
        layers.append("L3:security")

        # 组装 analysis prompt
        prompt = ANALYSIS_PROMPT
        prompt = prompt.replace("{user_profile}", ctx.user_profile or "")
        prompt = prompt.replace("{metacog_context}",
                                (ctx.metacog_context + "\n") if ctx.metacog_context else "")
        prompt = prompt.replace("{user_input}", ctx.user_input[:2000])
        prompt = prompt.replace("{conversation_history}",
                                ctx.conversation_history[:1500] if ctx.conversation_history else "(无历史)")
        prompt = prompt.replace("{memory_context}",
                                ctx.memory_context[:1000] if ctx.memory_context else "(无相关记忆)")
        prompt = prompt.replace("{security_context}", security)

        # 统计用到的层
        if ctx.user_profile:
            layers.append("L4:profile")
        if ctx.metacog_context:
            layers.append("L5:metacog")
        if ctx.conversation_history:
            layers.append("L6:history")
        if ctx.memory_context:
            layers.append("L7:memory")
        layers.append("L8:input")

        result.analysis = prompt
        result.layers_used = layers
        result.token_estimate = len(prompt) // 2  # 粗略估计

        return result

    def assemble_chat(self, ctx: PromptContext, history: list[dict] = None) -> AssembledPrompt:
        """组装对话型 Prompt (给 LLM 做生成回复)"""
        result = AssembledPrompt()
        result.system = IDENTITY_SYSTEM

        messages = []
        if ctx.rules_context:
            messages.append({"role": "system", "content": f"[规则提示] {ctx.rules_context}"})
        if ctx.security_context and not ctx.is_owner:
            messages.append({"role": "system", "content": ctx.security_context})

        # 注入历史
        if history:
            for h in history[-10:]:
                messages.append(h)

        # 注入记忆
        if ctx.memory_context:
            messages.append({"role": "system", "content": f"[相关记忆] {ctx.memory_context[:500]}"})

        messages.append({"role": "user", "content": ctx.user_input})

        result.messages = messages
        result.layers_used = ["L1:identity", "L6:history", "L7:memory", "L8:input"]
        result.token_estimate = sum(len(m.get("content", "")) for m in messages) // 2

        return result

    def assemble_intent_chain(self, user_input: str) -> str:
        """组装复合意图分析 Prompt"""
        return INTENT_CHAIN_PROMPT.replace("{user_input}", user_input[:500])

    def get_stats(self) -> dict:
        """返回缓存统计"""
        return {
            "template_count": len(self._template_cache),
            "layers": ["L1:identity", "L2:rules", "L3:security", "L4:profile",
                       "L5:metacog", "L6:history", "L7:memory", "L8:input"],
        }


if __name__ == "__main__":
    cache = PromptCache()
    ctx = PromptContext(
        user_input="帮我分析一下茅台最近的走势",
        user_profile="[用户画像] （示例）用户偏好简洁直接的回答",
        metacog_context="[自我认知] 对\"finance\"领域较熟悉(78%)",
        conversation_history="[用户]: 今天A股表现怎么样？\n[助手]: 上证收涨0.5%...",
        memory_context="- [reasoning] 茅台分析: PE 30x, 股价稳定...",
    )
    result = cache.assemble_analysis(ctx)
    print(f"层数: {len(result.layers_used)}")
    print(f"层: {result.layers_used}")
    print(f"Token估计: {result.token_estimate}")
    print(f"Prompt长度: {len(result.analysis)} chars")
    print(f"\n--- 前500字 ---\n{result.analysis[:500]}")
