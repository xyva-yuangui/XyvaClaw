#!/usr/bin/env python3
"""
V15 认知核心 — 统一编排器, 替代 cognitive-kernel-v6.py
拆分自 87.4KB 单文件 → ~40KB 编排器 + 独立子模块

V15 消息管道 (分层 + 并行):
  Event → Sense Bus → Cognitive Core
                       │
               ┌───────┴───────┐
               │  L0: 规则引擎  │ ← ~112条, <0.05ms, 86%拦截
               └───────┬───────┘
                       │ 未命中(14%)
               ┌───────┴───────┐
               │  L1: 闪电分类  │ ← mini1 7B, <1.6s
               └───────┬───────┘
                       │
            ┌──────────┤ (并行)
            │          │
     ┌──────┴──────┐   │
     │ 记忆/技能   │   │
     │ 检索(异步)  │   │
     └──────┬──────┘   │
            ├──────────┘
     ┌──────┴──────────────┐
     │ L2: 路由 → LLM生成  │
     └──────┬──────────────┘
     ┌──────┴──────┐
     │  质检门控    │ ← 规则式, <5ms
     └──────┬──────┘
     ┌──────┴──────┐   ┌────────────┐
     │  响应给用户  │   │  异步扇出:  │
     └─────────────┘   │  · 轨迹记录 │
                       │  · 学习信号  │
                       └────────────┘

接口兼容 (与 Gateway 对接不变):
  python3 scripts/v15/cognitive-core-v15.py --process "用户消息"
  python3 scripts/v15/cognitive-core-v15.py --boot
  python3 scripts/v15/cognitive-core-v15.py --daily
  python3 scripts/v15/cognitive-core-v15.py --status
  python3 scripts/v15/cognitive-core-v15.py --finalize '{"user_input":"...","draft_answer":"..."}'
"""
from __future__ import annotations

import importlib
import importlib.util
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# V15 契约层
try:
    from cognitive_contracts_v15 import (
        CognitiveRequest, CognitiveResolution, CognitiveExecutionTrace,
        CognitiveFallbackDecision, FallbackReason, ProcessStage,
        TraceStore, resolve_fallback, split_compound_intent,
    )
    _HAS_CONTRACTS = True
except ImportError:
    _HAS_CONTRACTS = False

WORKSPACE = Path(os.environ.get("OPENCLAW_WORKSPACE", os.path.expanduser("~/.openclaw/workspace")))
OPENCLAW_HOME = Path(os.path.expanduser("~/.openclaw"))
SCRIPTS_DIR = WORKSPACE / "scripts"
V15_DIR = SCRIPTS_DIR / "v15"
STATE_DIR = WORKSPACE / "state"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 延迟导入 V15 子模块
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_module_cache = {}

def _load_v15_module(name: str):
    """延迟加载V15子模块, 缓存"""
    if name in _module_cache:
        return _module_cache[name]
    # name like "rule-engine-v15" → file "rule-engine-v15.py"
    file_path = V15_DIR / f"{name}.py"
    if not file_path.exists():
        return None
    try:
        module_name = name.replace("-", "_")
        spec = importlib.util.spec_from_file_location(module_name, str(file_path))
        if spec is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        # 必须先注册到 sys.modules 再 exec_module：子模块内的 @dataclass 会通过
        # sys.modules[cls.__module__] 反查自身命名空间，未注册时报
        # "'NoneType' object has no attribute '__dict__'"，导致 llm-router / sense-bus /
        # prompt-cache 全部加载失败，管道降级为 "LLM Router 未加载"。
        sys.modules[module_name] = mod
        try:
            spec.loader.exec_module(mod)
        except Exception:
            sys.modules.pop(module_name, None)
            raise
        _module_cache[name] = mod
        return mod
    except Exception as e:
        print(f"⚠️ 加载 {name} 失败: {e}", file=sys.stderr)
        return None


def _get_rule_engine():
    return _load_v15_module("rule-engine-v15")

def _get_router():
    return _load_v15_module("llm-router-v15")

def _get_memory():
    return _load_v15_module("memory-fabric-v15")

def _get_prompt_cache():
    return _load_v15_module("prompt-cache-v15")

def _get_trajectory():
    return _load_v15_module("trajectory-recorder-v15")

def _get_skill_forge():
    return _load_v15_module("skill-forge-v15")

def _get_sense_bus():
    return _load_v15_module("sense-bus-v15")

def _get_self_cal():
    return _load_v15_module("self-calibration-v15")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 配置加载
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_trace_store = None

def _get_trace_store():
    global _trace_store
    if _trace_store is None and _HAS_CONTRACTS:
        _trace_store = TraceStore()
    return _trace_store


_config_cache = None

def load_config() -> dict:
    global _config_cache
    if _config_cache is not None:
        return _config_cache
    config_path = OPENCLAW_HOME / "openclaw.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            _config_cache = json.load(f)
    else:
        _config_cache = {}
    return _config_cache


def _add_diagnostic(result: dict, stage: str, level: str, message: str, detail=None):
    result.setdefault("diagnostics", []).append({
        "stage": stage,
        "level": level,
        "message": message,
        "detail": detail,
    })
    if level == "error":
        result.setdefault("errors", []).append({
            "stage": stage,
            "message": message,
            "detail": detail,
        })


def _emit_sense_event(event_type: str, payload: dict, priority: int = 1, requires_response: bool = False):
    sb_mod = _get_sense_bus()
    if not sb_mod:
        return None
    try:
        event = sb_mod.SenseEvent(
            source="cognitive_core",
            event_type=event_type,
            priority=priority,
            payload=payload,
            requires_response=requires_response,
        )
        return sb_mod.emit(event)
    except Exception:
        return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 核心: process_message
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def process_message(user_input: str, session_id: str = "default",
                    sender_id: str = "", context: dict = None) -> dict:
    """
    V15 消息处理主管道 (强契约 + 强轨迹 + 强降级 + 强闭环)
    返回: {
        answer, intent, action_type, model_used, skills,
        routing, latency_ms, rule_id, compound_intent,
        request_id, trace_saved, ...
    }
    """
    start_time = time.time()
    text = user_input.strip() if user_input else ""

    # ── 构建请求契约 ──
    req = None
    trace = None
    resolution = None
    if _HAS_CONTRACTS:
        req = CognitiveRequest(
            user_input=text, session_id=session_id,
            sender_id=sender_id, context=context or {},
        )
        trace = CognitiveExecutionTrace(request_id=req.request_id, request=req)
        resolution = CognitiveResolution(request_id=req.request_id)
        trace.add_stage(ProcessStage.INIT, "ok", 0, f"input_len={len(text)}")

    result = {
        "answer": "",
        "intent": "unknown",
        "action_type": "chat",
        "model_used": "",
        "skills": [],
        "rule_id": None,
        "compound_intent": False,
        "session_id": session_id,
        "timestamp": datetime.now().isoformat(),
        "routing": {},
        "diagnostics": [],
        "errors": [],
        "skill_resolution": {},
        "raw_input": text,
        "request_id": req.request_id if req else "",
    }

    _emit_sense_event("user_message", {
        "session_id": session_id,
        "sender_id": sender_id,
        "text": text[:1000],
        "context": context or {},
    }, priority=0, requires_response=True)

    # ── L0: 规则引擎匹配 (<0.05ms) ──
    t0 = time.time()
    rule_result = None
    re_mod = _get_rule_engine()
    if re_mod:
        try:
            rule_result = re_mod.match(text)
            if rule_result and rule_result.get("matched"):
                result["intent"] = rule_result.get("intent", "unknown")
                result["action_type"] = rule_result.get("action_type", "chat")
                result["rule_id"] = rule_result.get("rule_id")
                result["skills"] = rule_result.get("routing", {}).get("suggested_skills", [])
                result["routing"] = rule_result.get("routing", {})
                if resolution:
                    resolution.intent = result["intent"]
                    resolution.action_type = result["action_type"]
                    resolution.rule_id = result["rule_id"]
                    resolution.rule_matched = True
            if hasattr(re_mod, "detect_compound_intent"):
                is_compound = re_mod.detect_compound_intent(text)
                result["compound_intent"] = is_compound
                if resolution:
                    resolution.compound_intent = is_compound
            if trace:
                trace.add_stage(ProcessStage.RULE_ENGINE, "ok", int((time.time() - t0) * 1000),
                                f"matched={bool(rule_result and rule_result.get('matched'))}")
        except Exception as e:
            _add_diagnostic(result, "rule_engine", "error", "规则引擎匹配失败", str(e))
            if trace:
                trace.add_stage(ProcessStage.RULE_ENGINE, "error", int((time.time() - t0) * 1000), str(e)[:200])
    else:
        _add_diagnostic(result, "rule_engine", "warn", "规则引擎未加载")
        if trace:
            trace.add_stage(ProcessStage.RULE_ENGINE, "warn", 0, "not_loaded")

    # ── L1: 闪电分类 (规则未匹配时) ──
    t0 = time.time()
    classification = {}
    if not (rule_result and rule_result.get("matched")):
        router_mod = _get_router()
        if router_mod:
            try:
                router = router_mod.LLMRouter()
                classification = router.classify(text)
                result["intent"] = classification.get("intent", "unknown")
                result["routing"].update(classification.get("routing", {}))
                if resolution:
                    resolution.intent = result["intent"]
                    resolution.classification = classification
                if trace:
                    trace.add_stage(ProcessStage.CLASSIFICATION, "ok", int((time.time() - t0) * 1000),
                                    f"intent={result['intent']}")
            except Exception as e:
                _add_diagnostic(result, "classification", "error", "闪电分类失败", str(e))
                classification = {"intent": "unknown", "complexity": "medium", "domain": "general"}
                if trace:
                    trace.add_stage(ProcessStage.CLASSIFICATION, "error", int((time.time() - t0) * 1000), str(e)[:200])
                if _HAS_CONTRACTS and trace:
                    fb = resolve_fallback(FallbackReason.CLASSIFY_FAIL_NO_RULE, req.request_id if req else "", str(e)[:200])
                    trace.add_fallback(fb)
        else:
            _add_diagnostic(result, "classification", "warn", "LLM Router 未加载，跳过闪电分类")
            if trace:
                trace.add_stage(ProcessStage.CLASSIFICATION, "warn", 0, "not_loaded")

    # ── 复合意图拆分 ──
    compound_steps = []
    if result.get("compound_intent") and _HAS_CONTRACTS:
        t0 = time.time()
        compound_steps = split_compound_intent(text)
        if req:
            req.is_compound = len(compound_steps) > 1
            req.sub_intents = compound_steps
        if resolution:
            resolution.compound_steps = compound_steps
        if trace:
            trace.add_stage(ProcessStage.COMPOUND_SPLIT, "ok", int((time.time() - t0) * 1000),
                            f"steps={len(compound_steps)}")

    # ── 记忆检索 (并行准备) ──
    t0 = time.time()
    memory_context = ""
    mem_mod = _get_memory()
    if mem_mod and text:
        try:
            fabric = mem_mod.MemoryFabric()
            # 签名为 search(query, top_k=5, category='')；旧代码用 limit= 会抛 TypeError
            # 并被下方 except 吞掉，导致记忆检索从未成功过
            memories = fabric.search(text, top_k=3)
            if memories:
                memory_context = "\n".join(
                    f"[记忆] {m.get('content', m.get('snippet', ''))[:200]}" for m in memories[:3]
                )
                result["memory_hits"] = len(memories[:3])
                if resolution:
                    resolution.memory_hits = len(memories[:3])
                    resolution.memory_context = memory_context[:500]
            if trace:
                trace.add_stage(ProcessStage.MEMORY_RETRIEVAL, "ok", int((time.time() - t0) * 1000),
                                f"hits={result.get('memory_hits', 0)}")
        except Exception as e:
            _add_diagnostic(result, "memory", "warn", "记忆检索失败", str(e))
            if trace:
                trace.add_stage(ProcessStage.MEMORY_RETRIEVAL, "error", int((time.time() - t0) * 1000), str(e)[:200])
            if _HAS_CONTRACTS and trace:
                fb = resolve_fallback(FallbackReason.MEMORY_RETRIEVE_FAIL, req.request_id if req else "", str(e)[:200])
                trace.add_fallback(fb)
    elif not mem_mod:
        _add_diagnostic(result, "memory", "warn", "记忆模块未加载")
        if trace:
            trace.add_stage(ProcessStage.MEMORY_RETRIEVAL, "warn", 0, "not_loaded")

    # ── 技能解析 ──
    t0 = time.time()
    skill_context = ""
    sf_mod = _get_skill_forge()
    if sf_mod:
        try:
            forge = sf_mod.SkillForge()
            if hasattr(forge, "resolve_contract"):
                contract = forge.resolve_contract(result["intent"], result.get("skills"))
                result["skill_resolution"] = contract
                if contract.get("selected"):
                    skill_context = json.dumps(contract["selected"], ensure_ascii=False)
                    if resolution:
                        resolution.skill_selected = contract.get("selected_name")
                        resolution.skill_contract_ok = contract.get("contract_ok", False)
                        resolution.skill_resolution = contract
                elif result.get("skills"):
                    _add_diagnostic(result, "skill_forge", "warn", "技能候选存在但未解析出可执行技能", contract)
            else:
                resolved = forge.resolve(result["intent"], result.get("skills"))
                if resolved:
                    result["skill_resolution"] = {"selected": resolved.to_dict(), "contract_ok": True}
                    skill_context = json.dumps(resolved.to_dict(), ensure_ascii=False)
                    if resolution:
                        resolution.skill_selected = resolved.name
                        resolution.skill_contract_ok = True
            if trace:
                trace.add_stage(ProcessStage.SKILL_RESOLUTION, "ok", int((time.time() - t0) * 1000),
                                f"selected={resolution.skill_selected if resolution else 'N/A'}")
        except Exception as e:
            _add_diagnostic(result, "skill_forge", "error", "技能解析失败", str(e))
            if trace:
                trace.add_stage(ProcessStage.SKILL_RESOLUTION, "error", int((time.time() - t0) * 1000), str(e)[:200])
            if _HAS_CONTRACTS and trace:
                fb = resolve_fallback(FallbackReason.SKILL_RESOLVE_FAIL, req.request_id if req else "", str(e)[:200])
                trace.add_fallback(fb)
    else:
        _add_diagnostic(result, "skill_forge", "warn", "Skill Forge 未加载")
        if trace:
            trace.add_stage(ProcessStage.SKILL_RESOLUTION, "warn", 0, "not_loaded")

    # ── Prompt 组装 ──
    t0 = time.time()
    try:
        system_prompt = _build_system_prompt(memory_context, skill_context, result)
        if trace:
            trace.add_stage(ProcessStage.PROMPT_ASSEMBLY, "ok", int((time.time() - t0) * 1000))
    except Exception as e:
        system_prompt = "你是这台机器的私人 AI 助手。"
        if trace:
            trace.add_stage(ProcessStage.PROMPT_ASSEMBLY, "error", int((time.time() - t0) * 1000), str(e)[:200])
        if _HAS_CONTRACTS and trace:
            fb = resolve_fallback(FallbackReason.PROMPT_ASSEMBLY_FAIL, req.request_id if req else "", str(e)[:200])
            trace.add_fallback(fb)

    # ── 复合意图执行管道 ──
    if len(compound_steps) > 1:
        result["answer"] = _execute_compound_pipeline(compound_steps, system_prompt, result, trace, req)
    else:
        # ── L2: 路由决策 + LLM 调用 ──
        result["answer"] = _execute_single_llm(text, system_prompt, rule_result, classification, result, trace, req, resolution)

    # ── 质检门控 ──
    t0 = time.time()
    result["answer"] = _quality_gate(result["answer"], result)
    if not result["answer"] and result.get("skill_resolution", {}).get("selected_name"):
        selected_name = result["skill_resolution"].get("selected_name")
        result["answer"] = f"已识别为 `{result.get('intent', 'unknown')}`，建议优先调用技能 `{selected_name}` 继续处理。"
        _add_diagnostic(result, "fallback", "warn", "生成结果为空，已返回技能级回退提示", selected_name)
    if trace:
        trace.add_stage(ProcessStage.QUALITY_GATE, "ok", int((time.time() - t0) * 1000))

    # ── 延迟计算 ──
    result["latency_ms"] = int((time.time() - start_time) * 1000)

    # ── 保存执行轨迹 ──
    if trace:
        trace.answer = result.get("answer", "")[:500]
        trace.model_used = result.get("model_used", "")
        trace.total_latency_ms = result["latency_ms"]
        trace.quality_score = 0.8 if trace.error_count == 0 else max(0.3, 0.8 - trace.error_count * 0.15)
        trace.resolution = resolution
        trace.finalized = True
        trace.add_stage(ProcessStage.DONE, "ok", result["latency_ms"])
        store = _get_trace_store()
        if store:
            try:
                store.save_trace(trace)
                result["trace_saved"] = True
            except Exception:
                result["trace_saved"] = False

    # ── 异步扇出: 轨迹 + 学习 ──
    _async_fanout(text, result, session_id)
    _emit_sense_event("process_result", {
        "session_id": session_id,
        "intent": result.get("intent"),
        "rule_id": result.get("rule_id"),
        "model_used": result.get("model_used"),
        "latency_ms": result.get("latency_ms"),
        "error_count": len(result.get("errors", [])),
        "request_id": result.get("request_id", ""),
    }, priority=1)

    return result


def _execute_single_llm(text: str, system_prompt: str, rule_result: dict,
                        classification: dict, result: dict,
                        trace, req, resolution) -> str:
    """单次LLM调用流程"""
    t0 = time.time()
    routing_decision = None
    router_mod = _get_router()
    if router_mod:
        try:
            router = router_mod.LLMRouter()

            if rule_result and rule_result.get("matched"):
                routing = rule_result.get("routing", {})
                model = routing.get("suggested_model", "deepseek/deepseek-chat")
                routing_decision = router_mod.RoutingDecision(
                    model=model,
                    provider=_model_to_provider(model),
                    reason=f"rule:{result['rule_id']}",
                )
            else:
                routing_decision = router.route(text, classification)

            if trace:
                trace.add_stage(ProcessStage.ROUTING, "ok", int((time.time() - t0) * 1000),
                                f"model={routing_decision.model if routing_decision else 'none'}")

            if routing_decision:
                if resolution:
                    resolution.routing_model = routing_decision.model
                    resolution.routing_provider = routing_decision.provider
                    resolution.routing_reason = routing_decision.reason

                t1 = time.time()
                prompt = f"{system_prompt}\n\n用户: {text}"
                answer = router.execute(routing_decision, prompt)
                result["model_used"] = routing_decision.model
                result["routing_decision"] = {
                    "model": routing_decision.model,
                    "provider": routing_decision.provider,
                    "reason": routing_decision.reason,
                }
                if trace:
                    trace.add_stage(ProcessStage.LLM_EXECUTE, "ok", int((time.time() - t1) * 1000),
                                    f"model={routing_decision.model}")
                return answer or ""

        except Exception as e:
            result["model_used"] = "error"
            _add_diagnostic(result, "routing_execute", "error", "路由或生成失败", str(e))
            if trace:
                trace.add_stage(ProcessStage.LLM_EXECUTE, "error", int((time.time() - t0) * 1000), str(e)[:200])
            if _HAS_CONTRACTS and trace:
                if rule_result and rule_result.get("matched"):
                    fb = resolve_fallback(FallbackReason.RULE_HIT_LLM_FAIL, req.request_id if req else "", str(e)[:200])
                else:
                    fb = resolve_fallback(FallbackReason.ROUTER_UNAVAILABLE, req.request_id if req else "", str(e)[:200])
                trace.add_fallback(fb)
            return f"[认知核心错误] {str(e)[:200]}"
    else:
        _add_diagnostic(result, "routing_execute", "error", "LLM Router 未加载")
        if trace:
            trace.add_stage(ProcessStage.ROUTING, "error", 0, "router_not_loaded")
        if _HAS_CONTRACTS and trace:
            fb = resolve_fallback(FallbackReason.ROUTER_UNAVAILABLE, req.request_id if req else "", "LLM Router not loaded")
            trace.add_fallback(fb)
        return "[认知核心] LLM Router 未加载"


def _execute_compound_pipeline(steps: list, system_prompt: str,
                               result: dict, trace, req) -> str:
    """复合意图执行管道 — 依次执行每个子步骤"""
    answers = []
    router_mod = _get_router()
    if not router_mod:
        if _HAS_CONTRACTS and trace:
            fb = resolve_fallback(FallbackReason.COMPOUND_STEP_FAIL, req.request_id if req else "", "router not loaded")
            trace.add_fallback(fb)
        return "[复合意图] LLM Router 未加载"

    router = router_mod.LLMRouter()
    for i, step_text in enumerate(steps):
        t0 = time.time()
        step_label = f"compound_step_{i+1}/{len(steps)}"
        try:
            classification = router.classify(step_text)
            routing_decision = router.route(step_text, classification)
            if routing_decision:
                prompt = f"{system_prompt}\n\n用户: {step_text}"
                if answers:
                    prompt += f"\n\n[前序步骤结果]: {answers[-1][:300]}"
                answer = router.execute(routing_decision, prompt)
                answers.append(answer or "")
                result["model_used"] = routing_decision.model
                if trace:
                    trace.add_stage(ProcessStage.COMPOUND_STEP, "ok",
                                    int((time.time() - t0) * 1000),
                                    f"step={i+1}, intent={classification.get('intent', '?')}")
            else:
                answers.append(f"[步骤{i+1}] 路由失败")
                if trace:
                    trace.add_stage(ProcessStage.COMPOUND_STEP, "error",
                                    int((time.time() - t0) * 1000), "no routing decision")
        except Exception as e:
            answers.append(f"[步骤{i+1}] 执行失败: {str(e)[:100]}")
            if trace:
                trace.add_stage(ProcessStage.COMPOUND_STEP, "error",
                                int((time.time() - t0) * 1000), str(e)[:200])
            if _HAS_CONTRACTS and trace:
                fb = resolve_fallback(FallbackReason.COMPOUND_STEP_FAIL, req.request_id if req else "", str(e)[:200])
                trace.add_fallback(fb)

    if len(answers) == 1:
        return answers[0]
    parts = []
    for i, (step, answer) in enumerate(zip(steps, answers)):
        parts.append(f"**步骤{i+1}** ({step[:30]}...):\n{answer}")
    return "\n\n---\n\n".join(parts)


def _build_system_prompt(memory_ctx: str, skill_ctx: str, result: dict) -> str:
    """构建系统 prompt"""
    pc_mod = _get_prompt_cache()
    if pc_mod:
        try:
            cache = pc_mod.PromptCache()
            if hasattr(cache, "assemble"):
                return cache.assemble(
                    intent=result.get("intent", ""),
                    memory_context=memory_ctx,
                    skill_context=skill_ctx,
                )
            if hasattr(cache, "assemble_chat") and hasattr(pc_mod, "PromptContext"):
                ctx = pc_mod.PromptContext(
                    user_input=result.get("raw_input", ""),
                    memory_context=memory_ctx,
                    rules_context=json.dumps(result.get("routing", {}), ensure_ascii=False),
                )
                assembled = cache.assemble_chat(ctx)
                if getattr(assembled, "system", ""):
                    parts = [assembled.system]
                    for message in getattr(assembled, "messages", []):
                        role = message.get("role", "system")
                        content = message.get("content", "")
                        parts.append(f"[{role}] {content}")
                    return "\n".join(parts)
        except Exception:
            pass

    # 回退: 基础 prompt
    parts = [
        "你是这台机器的私人 AI 助手。",
        "你聪明、高效、有记忆力，能调用各种技能完成任务。",
    ]
    if memory_ctx:
        parts.append(f"\n相关记忆:\n{memory_ctx}")
    if skill_ctx:
        parts.append(f"\n可用技能:\n{skill_ctx}")
    return "\n".join(parts)


def _model_to_provider(model: str) -> str:
    if "deepseek" in model:
        return "deepseek"
    elif "openai-codex" in model or "gpt-5" in model or "gpt-4" in model:
        return "openai-codex"
    elif "kimi" in model:
        return "kimi"
    else:
        return "deepseek"


def _quality_gate(answer: str, result: dict) -> str:
    """规则式质检, <5ms"""
    if not answer:
        return ""

    # 截断过长响应
    if len(answer) > 10000:
        answer = answer[:10000] + "\n\n[响应已截断]"

    # 敏感词检查 (示例)
    risk = result.get("routing", {}).get("risk_level", "low")
    if risk == "high" and len(answer) < 20:
        answer += "\n\n⚠️ 高风险操作，请确认后再执行。"

    return answer


def _async_fanout(user_input: str, result: dict, session_id: str):
    """异步扇出: 记录轨迹 + 发送学习信号"""
    # 轨迹记录
    tr_mod = _get_trajectory()
    if tr_mod:
        try:
            recorder = tr_mod.TrajectoryRecorder()
            recorder.record(
                user_input=user_input,
                intent=result.get("intent", ""),
                model_used=result.get("model_used", ""),
                latency_ms=result.get("latency_ms", 0),
                session_id=session_id,
                rule_id=result.get("rule_id", ""),
            )
        except Exception:
            pass


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# finalize_response
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def finalize_response(payload: dict) -> dict:
    """
    质检 + 后处理 + 学习信号
    payload: {"user_input": "...", "draft_answer": "...", "session_id": "..."}
    """
    user_input = payload.get("user_input", "")
    draft = payload.get("draft_answer", "")
    session_id = payload.get("session_id", "default")

    result = {
        "final_answer": draft,
        "quality_score": 0.8,
        "adjustments": [],
        "timestamp": datetime.now().isoformat(),
        "errors": [],
    }

    # 质检
    if not draft or len(draft.strip()) < 2:
        result["quality_score"] = 0.3
        result["adjustments"].append("answer_too_short")

    if len(draft) > 8000:
        result["final_answer"] = draft[:8000] + "\n\n[已截断]"
        result["adjustments"].append("truncated")

    # 自校准信号
    sc_mod = _get_self_cal()
    if sc_mod:
        try:
            cal = sc_mod.SelfCalibration()
            cal.calibrate(
                intent=payload.get("intent", ""),
                model_used=payload.get("model_used", ""),
                quality_score=result["quality_score"],
            )
        except Exception as e:
            result["errors"].append({"stage": "self_calibration", "message": str(e)})

    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# boot
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def boot() -> dict:
    """启动初始化: 加载子模块 + 预热"""
    print("🚀 Cognitive Core V15 启动...")
    results = {"modules": {}, "timestamp": datetime.now().isoformat()}

    modules_to_load = [
        "rule-engine-v15", "llm-router-v15", "cluster-client-v15",
        "memory-fabric-v15", "prompt-cache-v15", "trajectory-recorder-v15",
        "skill-forge-v15", "self-calibration-v15", "sense-bus-v15",
    ]

    for name in modules_to_load:
        t0 = time.time()
        mod = _load_v15_module(name)
        dt = int((time.time() - t0) * 1000)
        ok = mod is not None
        results["modules"][name] = {"ok": ok, "ms": dt}
        icon = "✅" if ok else "❌"
        print(f"  {icon} {name} ({dt}ms)")

    # 预热规则引擎
    re_mod = _get_rule_engine()
    if re_mod and hasattr(re_mod, "load_custom_rules"):
        re_mod.load_custom_rules()
        print("  ✅ 规则引擎预热完成")

    ok_count = sum(1 for v in results["modules"].values() if v["ok"])
    total = len(modules_to_load)
    print(f"\n🚀 启动完成: {ok_count}/{total} 模块加载成功")
    results["ok"] = ok_count
    results["total"] = total
    return results


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# daily
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def daily() -> dict:
    """每日维护: 委托给 daemon-loop"""
    print("🌙 Cognitive Core V15 每日维护 (委托 daemon-loop)")
    dl_mod = _load_v15_module("daemon-loop-v15")
    if dl_mod and hasattr(dl_mod, "run_daily"):
        return dl_mod.run_daily()
    else:
        print("  ⚠️ daemon-loop-v15 未加载, 跳过")
        return {"status": "skipped", "reason": "daemon-loop not available"}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# status
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def status() -> dict:
    """系统状态"""
    print("📊 Cognitive Core V15 Status")
    print("=" * 60)

    result = {
        "version": "15.0.0",
        "timestamp": datetime.now().isoformat(),
        "modules": {},
    }

    # 检查各模块
    modules = [
        ("rule-engine-v15", "规则引擎"),
        ("llm-router-v15", "LLM 路由"),
        ("cluster-client-v15", "集群客户端"),
        ("memory-fabric-v15", "记忆织网"),
        ("prompt-cache-v15", "Prompt 缓存"),
        ("trajectory-recorder-v15", "轨迹记录"),
        ("skill-forge-v15", "技能锻造"),
        ("self-calibration-v15", "自校准"),
        ("sense-bus-v15", "感知总线"),
        ("learning-loop-v15", "学习循环"),
        ("rule-miner-v15", "规则挖掘"),
        ("prescience-v15", "先知引擎"),
        ("daemon-loop-v15", "永驻循环"),
    ]

    for name, label in modules:
        exists = (V15_DIR / f"{name}.py").exists()
        icon = "✅" if exists else "❌"
        print(f"  {icon} {label} ({name})")
        result["modules"][name] = exists

    # 规则引擎统计
    re_mod = _get_rule_engine()
    if re_mod and hasattr(re_mod, "BUILTIN_RULES"):
        rule_count = len(re_mod.BUILTIN_RULES)
        print(f"\n  📋 内置规则: {rule_count} 条")
        result["builtin_rules"] = rule_count

    # 配置文件
    print("\n  配置文件:")
    for cfg_name in ["VERSION.json", "v15-cluster.json"]:
        cfg_path = WORKSPACE / "config" / cfg_name
        exists = cfg_path.exists()
        icon = "✅" if exists else "❌"
        print(f"    {icon} {cfg_name}")

    ok_count = sum(1 for v in result["modules"].values() if v)
    total = len(modules)
    print(f"\n  总计: {ok_count}/{total} 模块就绪")
    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# analyze_only: 仅分析不生成 (供 Gateway hook 插件调用)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def analyze_only(user_input: str, max_context_chars: int = 1200) -> dict:
    """
    只跑 L0 规则引擎 + 记忆检索 + 技能预选，**不调用任何 LLM**。

    用途: Gateway 的 before_prompt_build hook 调用本函数，把结果作为
    prependContext 注入到每轮 prompt。生成仍由 Gateway 自己的模型完成，
    避免双重 LLM 调用。

    返回: {ok, context, intent, action_type, rule_id, skills, memory_hits,
           compound_intent, risk_level, suggested_model, latency_ms}
    失败时返回 {ok: False, context: "", error: ...}，调用方应开放失败。
    """
    start = time.time()
    text = (user_input or "").strip()
    out = {
        "ok": True, "context": "", "intent": "unknown", "action_type": "chat",
        "rule_id": None, "skills": [], "memory_hits": 0,
        "compound_intent": False, "risk_level": "", "suggested_model": "",
    }
    if not text:
        out["latency_ms"] = 0
        return out

    parts = []

    # ── L0 规则引擎 ──
    re_mod = _get_rule_engine()
    if re_mod:
        try:
            rr = re_mod.match(text)
            if rr and rr.get("matched"):
                routing = rr.get("routing", {}) or {}
                out["intent"] = rr.get("intent", "unknown")
                out["action_type"] = rr.get("action_type", "chat")
                out["rule_id"] = rr.get("rule_id")
                out["skills"] = routing.get("suggested_skills", []) or []
                out["risk_level"] = routing.get("risk_level", "")
                out["suggested_model"] = routing.get("suggested_model", "")
                seg = f"意图={out['intent']} 动作={out['action_type']} 规则={out['rule_id']}"
                if out["skills"]:
                    seg += f" 建议技能={','.join(map(str, out['skills']))}"
                if out["risk_level"]:
                    seg += f" 风险={out['risk_level']}"
                parts.append(seg)
            if hasattr(re_mod, "detect_compound_intent"):
                out["compound_intent"] = bool(re_mod.detect_compound_intent(text))
                if out["compound_intent"]:
                    parts.append("复合意图=是（需拆解为多步执行）")
        except Exception as e:
            out["rule_error"] = str(e)[:200]

    # ── 记忆检索 ──
    mem_mod = _get_memory()
    if mem_mod:
        try:
            hits = mem_mod.MemoryFabric().search(text, top_k=3)
            if hits:
                out["memory_hits"] = len(hits)
                lines = []
                for h in hits:
                    snippet = h.get("content") or h.get("snippet") or ""
                    title = h.get("title") or h.get("source") or ""
                    lines.append(f"- {title}: {str(snippet)[:160]}".strip())
                parts.append("相关记忆:\n" + "\n".join(lines))
        except Exception as e:
            out["memory_error"] = str(e)[:200]

    # ── 技能预选 ──
    sf_mod = _get_skill_forge()
    if sf_mod and out["skills"]:
        try:
            forge = sf_mod.SkillForge()
            if hasattr(forge, "resolve_contract"):
                contract = forge.resolve_contract(out["intent"], out["skills"])
                sel = (contract or {}).get("selected")
                if sel:
                    name = sel.get("name") if isinstance(sel, dict) else str(sel)
                    out["skill_selected"] = name
                    parts.append(f"已匹配技能: {name}")
        except Exception as e:
            out["skill_error"] = str(e)[:200]

    if parts:
        body = "\n".join(parts)[:max_context_chars]
        out["context"] = "[V15 认知预分析]\n" + body

    out["latency_ms"] = int((time.time() - start) * 1000)
    return out


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CLI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    if "--analyze" in sys.argv:
        idx = sys.argv.index("--analyze")
        _text = sys.argv[idx + 1] if len(sys.argv) > idx + 1 else ""
        try:
            print(json.dumps(analyze_only(_text), ensure_ascii=False))
        except Exception as _e:
            # 开放失败：hook 侧拿到 ok=false 就跳过注入
            print(json.dumps({"ok": False, "context": "", "error": str(_e)[:200]},
                             ensure_ascii=False))

    elif "--process" in sys.argv:
        idx = sys.argv.index("--process")
        if len(sys.argv) > idx + 1:
            user_input = sys.argv[idx + 1]
            session_id = "default"
            if "--session" in sys.argv:
                si = sys.argv.index("--session")
                if len(sys.argv) > si + 1:
                    session_id = sys.argv[si + 1]
            result = process_message(user_input, session_id=session_id)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("用法: --process \"消息\" [--session <id>]")

    elif "--finalize" in sys.argv:
        idx = sys.argv.index("--finalize")
        if len(sys.argv) > idx + 1:
            try:
                payload = json.loads(sys.argv[idx + 1])
                result = finalize_response(payload)
                print(json.dumps(result, ensure_ascii=False, indent=2))
            except json.JSONDecodeError as e:
                print(f"JSON 解析错误: {e}")
        else:
            print("用法: --finalize '{\"user_input\":\"...\",\"draft_answer\":\"...\"}'")

    elif "--boot" in sys.argv:
        result = boot()
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif "--daily" in sys.argv:
        result = daily()
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif "--status" in sys.argv:
        result = status()

    elif "--traces" in sys.argv:
        store = _get_trace_store()
        if store:
            traces = store.get_recent_traces(20)
            print(f"📊 最近执行轨迹 ({len(traces)} 条)")
            for t in traces:
                icon = "✅" if t.get("error_count", 0) == 0 else "❌"
                print(f"  {icon} [{t.get('created_at', '')}] {t.get('intent', '?')} | {t.get('model_used', '?')} | {t.get('latency_ms', 0)}ms | q={t.get('quality_score', 0)}")
                if t.get("user_input"):
                    print(f"      {t['user_input']}")
        else:
            print("⚠️ 契约层未加载")

    elif "--trace-stats" in sys.argv:
        store = _get_trace_store()
        if store:
            stats = store.get_stats()
            print(json.dumps(stats, ensure_ascii=False, indent=2))
        else:
            print("⚠️ 契约层未加载")

    elif "--fallback-matrix" in sys.argv:
        if _HAS_CONTRACTS:
            from cognitive_contracts_v15 import FALLBACK_MATRIX
            print("📋 降级矩阵:")
            for reason, entry in FALLBACK_MATRIX.items():
                print(f"  [{entry['severity']:>8s}] {reason.value}")
                print(f"           → {entry['action']}: {entry['description']}")
        else:
            print("⚠️ 契约层未加载")

    else:
        print("V15 Cognitive Core — 认知核心")
        print('  --process "消息" [--session <id>]  处理消息')
        print("  --finalize '{...}'                质检后处理")
        print("  --boot                            启动初始化")
        print("  --daily                           每日维护")
        print("  --status                          系统状态")
        print("  --traces                          最近执行轨迹")
        print("  --trace-stats                     轨迹统计")
        print("  --fallback-matrix                 降级矩阵")
