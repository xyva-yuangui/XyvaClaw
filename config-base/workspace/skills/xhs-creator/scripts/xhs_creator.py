#!/usr/bin/env python3
"""
小红书统一创作流水线 (xhs-creator) - 修复版
合并自：xhs-content-workflow + xhs-content-templates + xhs-quality-checklist + xhs-monetization

Modes: auto, create, render-only, check-only
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

SKILLS_DIR = Path.home() / ".openclaw" / "workspace" / "skills"
OUTPUT_BASE = Path.home() / ".openclaw" / "output" / "xhs-creator"
RENDER_SCRIPT = SKILLS_DIR / "_archived" / "auto-redbook-skills-0.1.0" / "scripts" / "render_xhs_v2.py"
HUMANIZE_SCRIPT = SKILLS_DIR / "humanize-ai-text" / "scripts" / "transform.py"
TRACKER_SCRIPT = SKILLS_DIR / "effect-tracker" / "scripts" / "tracker.py"

STYLES = ["种草", "干货", "踩坑", "教程", "分享"]

TEMPLATES = {
    "pain-solution": {
        "name": "痛点解决型", "rating": 5,
        "structure": "痛点场景→效果数据→方案 1-3→核心心法→行动清单→福利→互动",
        "title_formula": "这{N}个{方法}让我{收益}！",
    },
    "compare": {
        "name": "对比测评型", "rating": 4,
        "structure": "选择困难→测评对象→维度对比→综合评分→购买建议→避坑提醒",
        "title_formula": "{A}vs{B}，到底选哪个？亲测后告诉你",
    },
    "tutorial": {
        "name": "教程步骤型", "rating": 4,
        "structure": "成果展示→前后对比→学习路径→步骤详解→FAQ→资源推荐",
        "title_formula": "手把手教你{技能}，{时间}就能学会！",
    },
    "list": {
        "name": "清单汇总型", "rating": 4,
        "structure": "汇总价值→筛选标准→清单项→使用建议→获取方式",
        "title_formula": "{N}个{领域}神器，全部免费！",
    },
    "story": {
        "name": "故事经历型", "rating": 5,
        "structure": "高光/低谷开场→背景→转折点→行动→关键决策→结果→经验",
        "title_formula": "从{起点}到{终点}，我做对了这{N}件事",
    },
    "opinion": {
        "name": "观点态度型", "rating": 3,
        "structure": "争议话题→个人立场→论据 1-3→反驳预设→升华观点",
        "title_formula": "别再{错误做法}了！{正确观点}才是关键",
    },
    "hot": {
        "name": "热点评论型", "rating": 3,
        "structure": "热点事件→背景→独特视角→深度分析→启示→互动",
        "title_formula": "关于{热点}，99% 的人都忽略了这个细节",
    },
}

STYLE_TEMPLATES = {
    "种草": ["pain-solution", "compare", "story"],
    "干货": ["tutorial", "list", "pain-solution"],
    "踩坑": ["story", "pain-solution", "opinion"],
    "教程": ["tutorial", "list"],
    "分享": ["story", "list", "opinion"],
}

QUALITY_WEIGHTS = {
    "content_depth": 0.30,
    "viral_structure": 0.30,
    "humanization": 0.25,
    "shareability": 0.15,
}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _track(action: str, status: str = "ok"):
    if TRACKER_SCRIPT.is_file():
        try:
            subprocess.run(
                [sys.executable, str(TRACKER_SCRIPT), "record",
                 "--skill", "xhs-creator", "--action", action, "--status", status],
                capture_output=True, timeout=5,
            )
        except Exception:
            pass


def _load_auto_tune_config() -> dict:
    """Load auto-tune optimization config"""
    config_file = SKILLS_DIR / "xhs-creator" / "config" / "auto_tune_config.json"
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {}


def _optimize_title(title: str, config: dict) -> str:
    """根据优化配置优化标题"""
    optimizations = config.get("optimizations", {})
    
    if not optimizations.get("title_enhancement", {}).get("enabled"):
        return title
    
    params = optimizations["title_enhancement"]["params"]
    optimized = title
    
    # 添加数字
    if params.get("add_numbers") and not any(c.isdigit() for c in optimized):
        optimized = f"5 个{optimized}"
    
    # 添加情绪词
    if params.get("add_emotions"):
        emotion_words = ["必备", "神器", "震惊", "必看", "绝了", "真香"]
        if not any(word in optimized for word in emotion_words):
            optimized = f"{optimized}必备"
    
    # 添加疑问句
    if params.get("add_questions") and "?" not in optimized and "？" not in optimized:
        optimized = f"{optimized}？"
    
    # 添加感叹号增强语气
    if "！" not in optimized and "!" not in optimized:
        optimized = f"{optimized}！"
    
    print(f"  🚀 标题优化：{title} → {optimized}")
    return optimized


def _select_template(style: str, template_name: str = None) -> dict:
    if template_name and template_name in TEMPLATES:
        return TEMPLATES[template_name]
    candidates = STYLE_TEMPLATES.get(style, ["pain-solution"])
    import random
    return TEMPLATES[random.choice(candidates)]


def _quality_check(content: str, title: str, tags: list) -> dict:
    score_detail = {}

    # Content depth
    lines = content.strip().split("\n")
    has_data = any(c in content for c in ["数据", "统计", "%", "调查", "研究"])
    has_sections = content.count("##") >= 3
    card_count = max(1, len(lines) // 15)
    depth = min(10, 3 + (2 if has_data else 0) + (2 if has_sections else 0) + min(3, card_count))
    score_detail["content_depth"] = depth

    # Viral structure
    title_ok = len(title) <= 20
    has_hook = any(kw in content[:200] for kw in ["你是不是", "为什么", "真的", "居然", "震惊"])
    has_cta = any(kw in content[-300:] for kw in ["收藏", "关注", "评论", "私信", "转发", "点赞"])
    viral = 4 + (2 if title_ok else 0) + (2 if has_hook else 0) + (2 if has_cta else 0)
    score_detail["viral_structure"] = min(10, viral)

    # Humanization
    ai_words = ["综上所述", "总之", "需要注意的是", "值得一提的是", "总而言之"]
    ai_count = sum(1 for w in ai_words if w in content)
    human_words = ["真香", "绝了", "yyds", "啊", "呢", "吧", "哈哈", "!", "！"]
    human_count = sum(1 for w in human_words if w in content)
    humanize = max(3, min(10, 7 - ai_count * 2 + min(3, human_count)))
    score_detail["humanization"] = humanize

    # Shareability
    tag_ok = 5 <= len(tags) <= 10
    has_list = "清单" in content or "步骤" in content or any(f"{i}." in content for i in range(1, 6))
    share = 5 + (2 if tag_ok else 0) + (2 if has_list else 0) + (1 if has_cta else 0)
    score_detail["shareability"] = min(10, share)

    total = sum(score_detail[k] * QUALITY_WEIGHTS[k] for k in QUALITY_WEIGHTS)

    if total >= 9:
        verdict = "爆款潜质 → 立即发布 + 推广"
    elif total >= 8:
        verdict = "优质内容 → 可发布"
    elif total >= 7:
        verdict = "合格 → 建议优化后发布"
    else:
        verdict = "不合格 → 重新创作"

    return {
        "total_score": round(total, 1),
        "detail": score_detail,
        "verdict": verdict,
        "checks": {
            "title_length": f"{len(title)}字 {'✅' if len(title) <= 20 else '❌ >20 字'}",
            "tag_count": f"{len(tags)}个 {'✅' if 5 <= len(tags) <= 10 else '⚠️'}",
            "has_hook": "✅" if has_hook else "⚠️ 缺少开头钩子",
            "has_cta": "✅" if has_cta else "⚠️ 缺少行动号召",
            "ai_taste": f"{'✅ 低' if ai_count == 0 else '⚠️ 检测到 ' + str(ai_count) + ' 个 AI 味词'}",
        },
    }






def _generate_real_content(topic: str, style: str, tpl: dict) -> str:
    """生成真实的 AI 工具推荐内容（爆款写法）"""
    
    # 真实 AI 工具数据（含个人体验）
    ai_tools = [
        {
            "name": "Notion AI",
            "scene": "文档写作、知识管理",
            "features": ["AI 写作辅助", "智能总结", "数据库自动化"],
            "steps": ["注册 Notion 账号", "启用 Notion AI", "输入/AI 调用"],
            "effect": "写文档不用从零开始了",
            "price": "$10/月"
        },
        {
            "name": "通义千问",
            "scene": "文案创作、代码生成",
            "features": ["多轮对话", "代码生成", "文档总结"],
            "steps": ["访问 tongyi.aliyun.com", "登录阿里云", "输入问题"],
            "effect": "日常问题能快速得到答案",
            "price": "免费 + 付费版"
        },
        {
            "name": "Cursor",
            "scene": "编程开发、代码审查",
            "features": ["AI 代码补全", "智能重构", "Bug 修复"],
            "steps": ["下载 Cursor", "导入项目", "Ctrl+K 调用 AI"],
            "effect": "写代码不用查那么多文档了",
            "price": "$20/月"
        },
        {
            "name": "飞书智能助手",
            "scene": "会议纪要、日程管理",
            "features": ["会议记录", "智能日程", "文档总结"],
            "steps": ["下载飞书", "启用智能助手", "输入/调用"],
            "effect": "开会不用手忙脚乱记笔记了",
            "price": "免费"
        },
        {
            "name": "秘塔写作猫",
            "scene": "文章写作、公文撰写",
            "features": ["语法纠错", "风格优化", "智能续写"],
            "steps": ["访问官网", "粘贴文本", "点击优化"],
            "effect": "写完后检查一下更有底",
            "price": "免费 + 付费版"
        },
    ]
    
    # 根据模板类型生成内容
    template_name = tpl.get("name", "")
    
    content_parts = []
    
    if "痛点" in template_name:
        # 痛点解决型 - 真实个人体验 + 爆款写法
        content_parts = [
            "## 😫 3 个月前，我也以为 AI 工具都是智商税",
            "",
            "说实话，刚开始我也觉得：",
            "- AI 写的东西能用？不可能吧...",
            "- 学这个不得花好多时间？",
            "- 那么多工具，哪个才是真好用？",
            "",
            "直到我被工作逼到崩溃——",
            "- 每天加班到 10 点，周末还要改稿",
            "- 领导要的数据，翻遍全网找不到",
            "- 同样的报告，改了 8 版还不行",
            "",
            "## 📊 现在我准点下班，领导还夸我效率高",
            "",
            "**真实数据**：",
            "- 使用时间：2025 年 12 月 -2026 年 3 月（3 个月）",
            "- 加班时间：从经常加班到偶尔加班",
            "- 工作效率：确实快了不少",
            "- 领导评价：说我现在交东西挺快",
            "- 副业收入：开始用 AI 接一些小项目",
            "",
            "## 🛠️ 就这 5 个神器，改变了我的一切",
            "",
        ]
        
        # 添加真实工具推荐（个人体验式）
        for i, tool in enumerate(ai_tools[:5], 1):
            content_parts.extend([
                f"### 🛠️ 神器{i}：{tool['name']}",
                "",
                f"**我用它来**：{tool['scene']}",
                "",
                f"**最香的功能**：",
            ])
            for feature in tool['features'][:2]:  # 只列 2 个核心功能
                content_parts.append(f"- ✅ {feature}")
            
            content_parts.extend([
                "",
                f"**我的使用流程**：",
            ])
            for j, step in enumerate(tool['steps'], 1):
                content_parts.append(f"{j}. {step}")
            
            content_parts.extend([
                "",
                f"**真实效果**：{tool['effect']}",
                f"**成本**：{tool['price']}",
                "",
                f"**推荐指数**：{'⭐' * (5 if '免费' in tool['price'] or '300%' in tool['effect'] else 4)}",
                "",
            ])
        
        # 添加结尾（爆款互动式）
        content_parts.extend([
            "## 💡 3 个月总结，这 3 点最重要",
            "",
            "1. **别贪多**：我先试了 20+ 个工具，最后就留了这 5 个",
            "2. **固定场景**：每个工具只用来做特定事情，形成肌肉记忆",
            "3. **边用边优化**：每周花 10 分钟复盘，找到最佳用法",
            "",
            "## ✅ 建议你从今天开始",
            "",
            "别一次性全学，会崩溃的！",
            "",
            "- **今天**：选 1 个最需要的工具，花 30 分钟试试",
            "- **本周**：把这个工具的核心功能摸透",
            "- **本月**：形成自己的工作流，效率自然翻倍",
            "",
            "## 🎁 给粉丝的福利",
            "",
            "我整理了 3 个月的实操经验：",
            "- 50+ AI 工具完整清单（按场景分类）",
            "- 每个工具的详细使用教程",
            "- 我自己的工作流模板",
            "",
            "**关注我，回复「AI 神器」免费领** 📩",
            "",
            "## 💬 最后聊聊",
            "",
            "你在用哪些 AI 工具？有没有踩过坑？",
            "评论区分享一下，帮大家避避雷～",
            "",
            "**觉得有用记得点赞 + 收藏**，不然刷着刷着就找不到了！",
            "**关注我**，下期分享《我是如何用 AI 做副业月入 5000+ 的》",
        ])
    
    elif "清单" in template_name:
        # 清单体型
        content_parts = ["## 📋 5 个打工人必备的 AI 效率神器", ""]
        for i, tool in enumerate(ai_tools[:5], 1):
            content_parts.extend([
                f"### {i}. {tool['name']}",
                f"**场景**：{tool['scene']}",
                f"**效果**：{tool['effect']}",
                f"**价格**：{tool['price']}",
                "",
            ])
    
    else:
        # 默认使用痛点解决型
        return _generate_real_content(topic, style, {"name": "痛点解决型"})
    
    return "\n".join(content_parts)

def _generate_content(topic: str, style: str, tpl: dict) -> str:
    """根据主题和模板自动生成内容"""
    import random
    
    # 根据模板类型生成内容
    template_name = tpl["name"]
    structure = tpl["structure"].split("→")
    
    content_parts = []
    
    # 通用内容生成逻辑
    if "清单" in template_name or "清单" in str(structure):
        # 清单体内容
        for i in range(1, 4):
            content_parts.extend([
                f"## {i}. {topic}技巧{i}",
                f"",
                f"**核心要点**：",
                f"- 要点 1：具体方法 + 效果",
                f"- 要点 2：使用场景 + 案例",
                f"- 要点 3：注意事项 + 避坑",
                f"",
                f"**实操步骤**：",
                f"1. 第一步：打开工具/平台",
                f"2. 第二步：设置参数/配置",
                f"3. 第三步：执行操作/优化",
                f"",
                f"**效果对比**：",
                f"- 使用前：耗时 X 小时，效果一般",
                f"- 使用后：耗时 Y 分钟，效果提升 Z%",
                f"",
            ])
    
    elif "教程" in template_name or "步骤" in str(structure):
        # 教程体内容
        content_parts = [
            "## 准备工作",
            "",
            "- 工具准备：XXX 工具/平台",
            "- 账号准备：注册/登录",
            "- 环境准备：浏览器/客户端",
            "",
            "## 第一步：基础配置",
            "",
            "1. 打开 XXX 工具/网站",
            "2. 点击设置/配置选项",
            "3. 按照以下参数设置：",
            "   - 参数 1：推荐值",
            "   - 参数 2：推荐值",
            "",
            "## 第二步：核心操作",
            "",
            "1. 进入主界面",
            "2. 选择功能模块",
            "3. 输入/上传内容",
            "4. 点击生成/处理",
            "",
            "## 第三步：优化调整",
            "",
            "- 根据结果调整参数",
            "- 多次尝试找到最佳配置",
            "- 保存常用配置模板",
            "",
        ]
    
    elif "痛点" in template_name:
        # 痛点解决型
        content_parts = [
            "## 痛点场景",
            "",
            "你是不是也经常遇到这些问题：",
            "- 每天加班到深夜，效率还是上不去",
            "- 重复性工作太多，没时间做创造性工作",
            "- 工具太多太杂，不知道哪个好用",
            "",
            "## 效果数据",
            "",
            "**亲测效果**：",
            "- 使用时间：3 个月",
            "- 效率提升：300%",
            "- 节省时间：每天 2 小时+",
            "- 产出质量：提升 50%",
            "",
            "## 方案 1-3",
            "",
            "### 方案 1：XXX 工具",
            "",
            "**适用场景**：文档处理/数据分析",
            "",
            "**使用方法**：",
            "1. 打开工具",
            "2. 导入数据",
            "3. 一键生成",
            "",
            "**优点**：快速、准确、易用",
            "**缺点**：需要学习成本",
            "",
        ]
    
    # 添加通用结尾
    content_parts.extend([
        "## 行动清单",
        "",
        "- [ ] 今天：选择 1 个工具开始尝试",
        "- [ ] 本周：熟练掌握核心功能",
        "- [ ] 本月：形成自己的工作流",
        "",
        "## 福利",
        "",
        "关注我，回复「工具」获取：",
        "- 完整工具清单",
        "- 使用教程",
        "- 配置模板",
        "",
        "## 互动",
        "",
        "你在用哪些 AI 工具？评论区分享一下～",
        "觉得有用记得点赞 + 收藏，不然就找不到了！",
    ])
    
    return "\n".join(content_parts)

def cmd_create(topic: str, style: str = "种草", template_name: str = None,
               auto: bool = False, no_research: bool = False, theme: str = "default") -> dict:
    # Load auto-tune config
    tune_config = _load_auto_tune_config()
    has_optimizations = bool(tune_config.get("optimizations"))
    
    print(f"\n📕 小红书创作流水线")
    print(f"   主题：{topic}")
    print(f"   风格：{style}")
    if has_optimizations:
        print(f"   🚀 优化配置：已启用 {len(tune_config['optimizations'])} 项优化")
    print()

    # Apply title optimization
    if has_optimizations:
        topic = _optimize_title(topic, tune_config)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = OUTPUT_BASE / f"{ts}_{topic[:20].replace(' ', '_')}"
    out_dir.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()

    # Step 1: Template selection with content structure optimization
    tpl = _select_template(style, template_name)
    
    # Apply content structure optimization
    if has_optimizations and tune_config["optimizations"].get("content_structure", {}).get("enabled"):
        if style in ["种草", "干货"]:
            prefer_templates = ["list", "tutorial", "pain-solution"]
            if tpl["name"] not in [TEMPLATES[t]["name"] for t in prefer_templates]:
                tpl = _select_template(style, "list")
                print(f"  📋 模板优化：切换到清单汇总型 (提升互动率)")
    
    print(f"  📋 模板：{tpl['name']} (⭐×{tpl['rating']})")
    print(f"     结构：{tpl['structure']}")

    # Step 2: Research
    research_data = {"topic": topic, "sources": [], "timestamp": _now()}
    if not no_research:
        print(f"\n  🔍 调研中...")
        research_data["method"] = "auto-researcher integration"
        research_data["instructions"] = (
            f"Agent: 使用 auto-researcher 搜索 '{topic} 小红书 热门'，"
            f"提取 3-5 个竞品爆款的结构和高互动元素"
        )
        print(f"     → Agent 需执行搜索并填充 research.json")

    research_file = out_dir / "research.json"
    with open(research_file, "w", encoding="utf-8") as f:
        json.dump(research_data, f, indent=2, ensure_ascii=False)

    # Step 3: Draft creation
    print(f"\n  ✍️  创作草稿...")
    draft_file = out_dir / "draft.md"
    
    # Generate actual content
    actual_content = _generate_real_content(topic, style, tpl)
    
    # 生成封面标题（用于渲染）
    cover_title = topic.replace("？", "").replace("!", "").replace("!", "")
    if len(cover_title) > 15:
        cover_title = cover_title[:15]
    
    with open(draft_file, "w", encoding="utf-8") as f:
        f.write(f"---\n")
        f.write(f'emoji: "📕"\n')
        f.write(f'title: "{topic}"\n')
        f.write(f'subtitle: "打工人必备 | 效率翻倍"\n')
        f.write(f'cover_title: "{cover_title}"\n')
        f.write(f'cover_subtitle: "亲测有效 | 建议收藏"\n')
        f.write(f"style: {style}\n")
        f.write(f"template: {tpl['name']}\n")
        f.write(f"---\n\n")
        f.write(f"# {topic}\n\n")
        f.write(f"<!-- 风格：{style} | 模板：{tpl['name']} -->\n\n")
        f.write(actual_content)
        f.write(f"\n\n---\n\n")
        f.write(f"#AI 工具 #效率神器 #打工人必备 #职场干货 #生产力工具\n")

    print(f"     → draft.md 已生成（含实际内容 + 封面标题）")

    # Step 4: Humanization instructions
    humanize_file = out_dir / "humanize_instructions.md"
    with open(humanize_file, "w", encoding="utf-8") as f:
        f.write("# 人性化改写指引\n\n")
        f.write("## 去 AI 味\n- 删除：综上所述、总之、需要注意的是、值得一提的是\n\n")
        f.write("## 加口语\n- 加入：真香、绝了、yyds + 语气词 啊/呢/吧\n\n")
        f.write("## 加情绪\n- 情绪词 + 感叹句 + 反问句\n\n")
        f.write("## 加细节\n- 个人经历 + 具体场景 + 具体数字 + 感官描述\n\n")
        f.write("## Agent 指令\n\n```bash\n")
        f.write(f"python3 {HUMANIZE_SCRIPT} --input draft.md --output final.md --style casual\n")
        f.write("```\n")

    # Step 5: Quality check
    print(f"  📊 质量检查...")
    with open(draft_file, "r", encoding="utf-8") as f:
        draft_content = f.read()
    tags = [t.strip() for t in draft_content.split("#") if t.strip() and len(t.strip()) < 20][-5:]
    qc = _quality_check(draft_content, topic, tags)
    qc_file = out_dir / "quality_report.json"
    with open(qc_file, "w", encoding="utf-8") as f:
        json.dump(qc, f, indent=2, ensure_ascii=False)
    print(f"     评分：{qc['total_score']}/10 — {qc['verdict']}")

    # Step 6: Render instructions
    render_file = out_dir / "render_instructions.md"
    with open(render_file, "w", encoding="utf-8") as f:
        f.write("# 渲染指引\n\n")
        f.write(f"主题：{theme}\n")
        f.write(f"尺寸：1080×1440 (3:4)\n\n")
        f.write("```bash\n")
        if RENDER_SCRIPT.is_file():
            f.write(f"python3 {RENDER_SCRIPT} final.md -t {theme} -m auto-split -o {out_dir}/\n")
        else:
            f.write("# render_xhs_v2.py 不可用，使用 xhs-creator 内置渲染\n")
            f.write(f"# Agent: 使用 qwen-image 或 superdesign 生成封面\n")
        f.write("```\n")

    elapsed_ms = int((time.monotonic() - start) * 1000)
    _track("create", "ok")

    result = {
        "topic": topic, "style": style, "template": tpl["name"],
        "quality_score": qc["total_score"], "verdict": qc["verdict"],
        "output_dir": str(out_dir), "elapsed_ms": elapsed_ms,
        "files": {
            "research": str(research_file),
            "draft": str(draft_file),
            "humanize": str(humanize_file),
            "quality": str(qc_file),
            "render": str(render_file),
        },
        "timestamp": _now(),
    }

    summary_file = out_dir / "summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n  ✅ 创作流水线完成！({elapsed_ms}ms)")
    print(f"  📂 {out_dir}")
    return result


def health_check() -> dict:
    checks = []

    deps = {
        "humanize-ai-text": HUMANIZE_SCRIPT,
        "render_xhs_v2": RENDER_SCRIPT,
        "effect-tracker": TRACKER_SCRIPT,
    }
    for name, path in deps.items():
        checks.append({"name": name, "status": "ok" if path.is_file() else "warn"})

    # Check playwright
    try:
        import importlib
        importlib.import_module("playwright")
        checks.append({"name": "playwright", "status": "ok"})
    except ImportError:
        checks.append({"name": "playwright", "status": "warn", "message": "pip install playwright"})

    checks.append({"name": "python3", "status": "ok"})

    overall = "fail" if any(c["status"] == "fail" for c in checks) \
        else "warn" if any(c["status"] == "warn" for c in checks) else "ok"

    return {"skill": "xhs-creator", "version": "1.0.0", "status": overall,
            "checks": checks, "timestamp": _now()}


def main():
    parser = argparse.ArgumentParser(description="小红书统一创作流水线")
    parser.add_argument("--check", action="store_true", help="健康检查")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("-t", "--topic", help="笔记主题")
    parser.add_argument("-s", "--style", default="种草", choices=STYLES)
    parser.add_argument("--template", choices=list(TEMPLATES.keys()))
    parser.add_argument("-a", "--auto", action="store_true", help="自动模式")
    parser.add_argument("--no-research", action="store_true")
    parser.add_argument("--theme", default="default")
    parser.add_argument("-o", "--output", help="输出目录")

    args = parser.parse_args()

    if args.check:
        result = health_check()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(0 if result["status"] != "fail" else 1)

    topic = args.topic
    if not topic:
        if args.auto:
            topic = "AI 效率工具推荐"
        else:
            topic = input("📝 请输入笔记主题：").strip()
            if not topic:
                print("主题不能为空")
                sys.exit(1)
    
    result = cmd_create(topic, args.style, args.template,
                        args.auto, args.no_research, args.theme)

    if args.json and result:
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
