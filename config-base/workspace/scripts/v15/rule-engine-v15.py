#!/usr/bin/env python3
"""
V15 规则引擎 — 高覆盖快速路径 + 自定义规则热加载 + 持久化命中统计
升级自: rule-engine-v6.py (完整继承全部100+内置规则，添加V15路由集成)

变化 (vs V6):
  1. 路由输出格式统一: routing dict 包含 model/skills/risk/reasoning
  2. 自定义规则: custom-rules.json + pattern-library.json 热加载
  3. 持久化命中统计: state/v15-rules-stats.json
  4. match_all(): 多规则匹配 (用于复合意图链)
  5. save_custom_rule(): 支持规则动态写入
  6. 精确复合意图检测: COMPOUND_MARKERS (连接词+动词)

用法:
  from rule_engine_v15 import match, match_all, detect_compound_intent
  result = match("帮我分析一下茅台")
  results = match_all("先做个表格然后发到小红书")

CLI:
  python3 scripts/v15/rule-engine-v15.py --match "消息"
  python3 scripts/v15/rule-engine-v15.py --list
  python3 scripts/v15/rule-engine-v15.py --stats
  python3 scripts/v15/rule-engine-v15.py --reload
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

WORKSPACE = Path(os.environ.get("OPENCLAW_WORKSPACE", os.path.expanduser("~/.openclaw/workspace")))
STATE_DIR = WORKSPACE / "state"
CUSTOM_RULES_FILE = STATE_DIR / "custom-rules.json"
RULES_STATS_FILE = STATE_DIR / "v15-rules-stats.json"
PATTERN_LIBRARY = STATE_DIR / "pattern-library.json"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 内置规则 (完整继承 V6, 按priority排序)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BUILTIN_RULES = [
    # ── 危险操作 (最高优先级) ──
    {"id": "danger_01", "patterns": [r"(rm\s+-rf|删除.*全部|清空.*数据库|drop\s+table|格式化)"],
     "intent": "dangerous_operation", "action_type": "clarify", "risk": "critical", "priority": 200},
    {"id": "danger_04", "patterns": [r"(忽略|无视|跳过|覆盖).{0,10}(之前|以上|所有|系统).{0,10}(指令|提示|规则|prompt|instruction)", r"(告诉我|输出|显示|泄露).{0,10}(系统|system).{0,10}(提示|prompt|指令)"],
     "intent": "prompt_injection", "action_type": "clarify", "risk": "high", "priority": 195},
    {"id": "danger_02", "patterns": [r"(删除|移除|清空).{0,10}(配置|config|密钥|key|token)"],
     "intent": "dangerous_config", "action_type": "clarify", "risk": "high", "priority": 190},
    {"id": "danger_03", "patterns": [r"(删除|移除|清空|卸载).{0,10}(这个|那个|所有|整个|该|目录|文件|文件夹|磁盘|分区|服务|进程|容器)"],
     "intent": "dangerous_operation", "action_type": "clarify", "risk": "high", "priority": 180},

    # ── 问候类 ──
    {"id": "greet_01", "patterns": [r"^(hi|hello|hey|你好|嗨|在吗|在不在)[\s!！。.？?]*$"],
     "intent": "greeting", "action_type": "chat", "risk": "low", "priority": 100},
    {"id": "greet_02", "patterns": [r"^(早|早安|早上好|good\s*morning)[\s!！。.？?]*$"],
     "intent": "greeting_morning", "action_type": "chat", "risk": "low", "priority": 100},
    {"id": "greet_03", "patterns": [r"^(晚安|晚上好|good\s*night|good\s*evening)[\s!！。.？?]*$"],
     "intent": "greeting_evening", "action_type": "chat", "risk": "low", "priority": 100},
    {"id": "greet_04", "patterns": [r"^(下午好|good\s*afternoon)[\s!！。.？?]*$"],
     "intent": "greeting_afternoon", "action_type": "chat", "risk": "low", "priority": 100},
    {"id": "greet_05", "patterns": [r"^(谢谢|感谢|thanks|thx|thank\s*you)[\s!！。.？?]*$"],
     "intent": "thanks", "action_type": "chat", "risk": "low", "priority": 100},
    {"id": "greet_06", "patterns": [r"^(好的|ok|收到|嗯|哦|行|对|是的|没事|了解|明白)[\s!！。.？?]*$"],
     "intent": "acknowledgment", "action_type": "chat", "risk": "low", "priority": 100},
    {"id": "greet_07", "patterns": [r"^(拜拜|再见|bye|see\s*you)[\s!！。.？?]*$"],
     "intent": "farewell", "action_type": "chat", "risk": "low", "priority": 100},

    # ── 确认/取消/反馈 ──
    {"id": "confirm_01", "patterns": [r"^(确认|确定|同意|可以|没问题|go|继续|执行|开始吧)[！!。.\s]*$"],
     "intent": "user_confirm", "action_type": "execute", "risk": "low", "priority": 95},
    {"id": "cancel_01", "patterns": [r"^(取消|算了|不要了|不用了|停止|stop|cancel|别.{0,3}了)[！!。.\s]*$"],
     "intent": "user_cancel", "action_type": "chat", "risk": "low", "priority": 95},
    {"id": "feedback_01", "patterns": [r"^(不对|错了|不是这个|重来|重新)[！!。.\s]*$"],
     "intent": "negative_feedback", "action_type": "chat", "risk": "low", "priority": 90},
    {"id": "feedback_02", "patterns": [r"^(很好|不错|对的|正确|完美|棒|牛|厉害|nice|great|good)[！!。.\s]*$"],
     "intent": "positive_feedback", "action_type": "chat", "risk": "low", "priority": 90},
    {"id": "calc_01", "patterns": [r"^\s*[\d\s\+\-\*\/\(\)\.%]+\s*[=？?]?\s*$"],
     "intent": "calculation", "action_type": "chat", "risk": "low", "priority": 90},

    # ── 图片/视觉 ──
    {"id": "vision_auto_01", "patterns": [r"__HAS_IMAGE__"],
     "intent": "auto_image_analysis", "action_type": "execute", "risk": "low", "priority": 85,
     "skills": ["vision-reader"], "model": "openai-codex/gpt-5.4-mini"},

    # ── 帮助 ──
    {"id": "help_01", "patterns": [r"^(你能做什么|你会什么|帮助|help|你的能力|功能列表)[？?！!\s]*$"],
     "intent": "capability_query", "action_type": "chat", "risk": "low", "priority": 80},

    # ── 系统 ──
    {"id": "sys_02", "patterns": [r"(重启|restart|gateway).{0,5}(服务|openclaw|网关)"],
     "intent": "system_restart", "action_type": "clarify", "risk": "high", "priority": 80},

    # ── 视频类 (video) ──
    {"id": "video_01", "patterns": [r"(做|生成|创建|制作).{0,10}视频", r"视频.{0,5}(做|生成|创建|制作)", r"(sora|视频生成|video)"],
     "intent": "video_creation", "action_type": "execute", "skills": ["video-studio", "sora-video", "auto-video-creator"], "risk": "low", "priority": 80},
    {"id": "video_02", "patterns": [r"(seedance|种子舞蹈|生成.*舞蹈)"],
     "intent": "seedance_video", "action_type": "execute", "skills": ["video-studio", "seedance-video"], "risk": "low", "priority": 80},
    {"id": "video_03", "patterns": [r"(字幕|subtitle|srt)", r"(加|生成|提取).{0,5}字幕"],
     "intent": "video_subtitle", "action_type": "execute", "skills": ["video-studio", "video-subtitles"], "risk": "low", "priority": 80},
    {"id": "vpub_01", "patterns": [r"(发布|上传|推送|发).{0,5}(视频).{0,15}(抖音|B站|bilibili|小红书|快手|视频号|TikTok|YouTube)",
                                    r"(抖音|bilibili|B站|小红书|快手|视频号|TikTok|YouTube).{0,10}(发布|上传|推送)"],
     "intent": "video_publish", "action_type": "execute", "skills": ["video-studio", "video-publisher"], "risk": "medium", "priority": 80},
    {"id": "vpub_02", "patterns": [r"(多平台|批量).{0,5}(发布|上传|推送).{0,5}视频",
                                    r"视频.{0,5}(同步|多平台|矩阵).{0,5}(发布|上传|推送)"],
     "intent": "video_multi_publish", "action_type": "execute", "skills": ["video-studio", "video-publisher"], "risk": "medium", "priority": 80},

    # ── 信息核查 ──
    {"id": "rumor_01", "patterns": [r"(核实|核查|验证|辟谣).{0,10}(这条|这个|这则|这篇|以下).{0,10}(消息|新闻|说法|信息)",
                                    r"(这是真的吗|这条消息真实吗|是真的吗|假的吗|有没有依据)",
                                    r"(真假|虚假|谣言|fake|辟谣).{0,10}(核查|验证|识别|判断)"],
     "intent": "fact_check", "action_type": "execute", "model": "deepseek/deepseek-reasoner",
     "skills": ["rumor-checker"], "risk": "low", "priority": 80, "use_reasoning": True},

    # ── PPT ──
    {"id": "ppt_01", "patterns": [r"(帮我|自动|AI).{0,5}(生成|制作|做|创建).{0,5}(PPT|ppt|演示文稿|幻灯片|Powerpoint)",
                                   r"(PPT|ppt|演示文稿|幻灯片).{0,5}(自动生成|AI生成|帮我做|帮我创建)"],
     "intent": "ppt_generate", "action_type": "execute", "skills": ["document-suite", "ppt-agent"], "risk": "low", "priority": 79},

    # ── 消息/通知 ──
    {"id": "msg_01", "patterns": [r"(发|发送|通知|告诉|转发).{0,10}(消息|信息|message)", r"(帮我|给).{0,5}(发|发送).{0,10}(给|到)"],
     "intent": "send_message", "action_type": "execute", "skills": ["smart-messenger"], "risk": "medium", "priority": 78},
    {"id": "msg_02", "patterns": [r"(微信|wechat|公众号).{0,10}(发|推送|发布)"],
     "intent": "wechat_publish", "action_type": "execute", "skills": ["wechat-suite", "wechat-publisher"], "risk": "medium", "priority": 65},

    # ── 天气 ──
    {"id": "weather_01", "patterns": [r"(天气|气温|温度|下雨|下雪|台风|暴雨|雾霾|pm2.5|PM2.5|紫外线)",
                                      r"(今天|明天|后天|这周|本周|周末).{0,5}(天气|气温|冷不冷|热不热|穿什么)"],
     "intent": "weather_query", "action_type": "execute", "skills": ["weather-query"], "risk": "low", "priority": 78},

    # ── 封面/缩略图 ──
    {"id": "thumb_01", "patterns": [r"(生成|制作|做|帮我.{0,3}).{0,5}(封面|缩略图|thumbnail|cover)",
                                    r"(封面|缩略图).{0,10}(生成|制作|做|创建|设计)",
                                    r"(抖音|小红书|YouTube|B站|公众号).{0,8}(封面|缩略图)"],
     "intent": "thumbnail_create", "action_type": "execute", "skills": ["video-studio", "thumbnail-generator"], "risk": "low", "priority": 78},

    # ── 导航/地图 ──
    {"id": "amap_01", "patterns": [r"(导航|路线|路径).{0,10}(从|到|怎么走|怎么去|规划)",
                                   r"(怎么|如何).{0,5}(去|到达|前往).{0,15}(地方|地点|地址|位置)"],
     "intent": "navigation", "action_type": "execute", "skills": ["amap-service"], "risk": "low", "priority": 78},

    # ── 会议 ──
    {"id": "mtg_01", "patterns": [r"(整理|写|生成).{0,5}(会议纪要|会议记录|纪要|minutes)",
                                   r"(会议纪要|会议记录|纪要).{0,5}(整理|帮我|写一|生成)"],
     "intent": "meeting_minutes", "action_type": "execute", "skills": ["meeting-assistant"], "risk": "low", "priority": 78},

    # ── 发票/单据 ──
    {"id": "inv_01", "patterns": [r"(生成|开|制作|做).{0,5}(发票|invoice|报价单|装箱单|packing.?list)",
                                  r"(发票|报价单|装箱单|商业发票|形式发票).{0,5}(生成|制作|帮我|做一)"],
     "intent": "invoice_create", "action_type": "execute", "skills": ["invoice-generator"], "risk": "low", "priority": 78},

    # ── 电商发布 ──
    {"id": "ep_01", "patterns": [r"(上架|发布|上传).{0,5}(shopify|Shopify|亚马逊|Amazon|amazon)",
                                 r"(shopify|Shopify|亚马逊|Amazon).{0,10}(上架|新品|商品|产品|listing|发布)"],
     "intent": "ecommerce_publish", "action_type": "execute", "skills": ["ecommerce-suite", "ecommerce-publisher", "product-description"], "risk": "medium", "priority": 78},

    # ── 电商Listing ──
    {"id": "pd_02", "patterns": [r"(亚马逊|Amazon|amazon).{0,10}(Listing|listing|标题|卖点|描述|文案)",
                                 r"(shopify|Shopify|淘宝|京东|拼多多|虾皮|shopee|lazada).{0,10}(商品|产品|listing|文案|描述)"],
     "intent": "ecommerce_listing", "action_type": "execute", "skills": ["ecommerce-suite", "product-description", "translation"], "risk": "low", "priority": 78},

    # ── rumor_02 ──
    {"id": "rumor_02", "patterns": [r"(帮我|麻烦).{0,5}(查一查|查查|核实|确认).{0,10}(消息|新闻|说法|信息)",
                                    r"(监控|监测|追踪).{0,5}(谣言|虚假信息|不实消息|热点).{0,5}(话题|内容)"],
     "intent": "rumor_monitor", "action_type": "execute", "skills": ["rumor-checker"], "risk": "low", "priority": 78},

    # ── 文档问答 ──
    {"id": "dqa_01", "patterns": [r"(这份|这个|这篇).{0,5}(文件|合同|文档|报告|pdf|PDF).{0,10}(写了|说了|提到|包含|里面)",
                                  r"(从|根据).{0,5}(文件|合同|文档|报告).{0,10}(找|查|告诉我|提取|总结)"],
     "intent": "document_qa", "action_type": "execute", "skills": ["document-suite", "document-qa"], "risk": "low", "priority": 77},

    # ── PPT (补充) ──
    {"id": "ppt_02", "patterns": [r"(关于|主题|topic).{0,20}(PPT|ppt|演示|slides|幻灯片)",
                                   r"(PPT|演示文稿|幻灯片).{0,10}(几页|多少页|几张|模板|风格|business|商务)"],
     "intent": "ppt_create", "action_type": "execute", "skills": ["document-suite", "ppt-agent", "pptx-reader-writer"], "risk": "low", "priority": 77},

    # ── 会议议程 ──
    {"id": "mtg_02", "patterns": [r"(生成|帮我做|制作).{0,5}(会议议程|议程|agenda)",
                                   r"(这次会议|下次会议|团队会议).{0,5}(议程|安排|主题|内容)"],
     "intent": "meeting_agenda", "action_type": "execute", "skills": ["meeting-assistant"], "risk": "low", "priority": 76},

    # ── POI搜索 ──
    {"id": "amap_02", "patterns": [r"(附近|周边|身边).{0,10}(餐厅|咖啡|超市|加油站|医院|酒店|停车场|药店|银行)",
                                   r"(找|搜|查).{0,5}(附近|周边).{0,5}(POI|地方|商家|店)"],
     "intent": "poi_search", "action_type": "execute", "skills": ["amap-service"], "risk": "low", "priority": 76},

    # ── 电商店铺管理 ──
    {"id": "ep_02", "patterns": [r"(更新|修改).{0,5}(价格|库存|sku|SKU).{0,10}(shopify|amazon|淘宝|JD)",
                                 r"(shopify|amazon|店铺).{0,5}(订单|销售|出单).{0,10}(查询|查看|最近|今天|本周)"],
     "intent": "shop_manage", "action_type": "execute", "skills": ["ecommerce-suite", "ecommerce-publisher"], "risk": "low", "priority": 76},

    # ── 商品文案 ──
    {"id": "pd_01", "patterns": [r"(写|生成|帮我写).{0,5}(商品|产品).{0,8}(标题|文案|描述|详情|卖点|Listing|listing)",
                                 r"(商品|产品).{0,5}(标题|文案|描述|详情|卖点|Listing).{0,5}(怎么写|帮我|写一|生成)"],
     "intent": "product_listing", "action_type": "execute", "skills": ["ecommerce-suite", "product-description"], "risk": "low", "priority": 76},

    # ── 视频脚本 ──
    {"id": "vs_01", "patterns": [r"(写|生成|帮我写).{0,5}(视频|短视频|带货|直播).{0,5}(脚本|话术|台词|分镜)",
                                 r"(视频|短视频|带货|直播).{0,5}(脚本|话术|台词|分镜).{0,5}(怎么写|帮我|写一|生成)"],
     "intent": "video_script", "action_type": "execute", "skills": ["video-studio", "video-script-writer"], "risk": "low", "priority": 76},
    {"id": "vs_02", "patterns": [r"(直播|带货).{0,5}(话术|脚本|流程|步骤)",
                                 r"(抖音|快手|淘宝).{0,5}直播.{0,5}(怎么说|话术|脚本)"],
     "intent": "live_script", "action_type": "execute", "skills": ["video-studio", "video-script-writer"], "risk": "low", "priority": 76},

    # ── 多平台文案 ──

    # ── 微信采集 ──
    {"id": "wcol_01", "patterns": [r"(搜索|采集|收集|抓取).{0,5}(微信|公众号|wechat).{0,5}(文章|内容|素材)",
                                   r"(公众号).{0,10}(文章|内容|素材).{0,5}(搜索|采集|下载|收集)"],
     "intent": "wechat_collect", "action_type": "execute", "skills": ["wechat-suite", "wechat-collector"], "risk": "low", "priority": 75},

    # ── DDG 显式搜索 ──
    {"id": "ddg_01", "patterns": [r"(duckduckgo|ddg|免费搜索).{0,10}(搜索|查询|搜)",
                                  r"(帮我|帮忙).{0,5}(搜|查).{0,30}(不要|不用|免费).{0,5}(key|api|brave|搜索引擎)"],
     "intent": "web_search", "action_type": "execute", "skills": ["research-suite"], "risk": "low", "priority": 75},

    # ── 小红书 ──

    # ── 邮件营销 ──
    {"id": "em_01", "patterns": [r"(写|生成|帮我).{0,5}(营销|促销|推广).{0,5}(邮件|email|Email)",
                                 r"(营销邮件|促销邮件|邮件营销|email marketing).{0,5}(写|生成|帮我|模板)"],
     "intent": "email_marketing", "action_type": "execute", "skills": ["ecommerce-suite", "email-marketing"], "risk": "low", "priority": 74},
    {"id": "em_02", "patterns": [r"(弃购|放弃购买|购物车挽回).{0,5}(邮件|话术|文案)",
                                 r"(欢迎邮件|用户召回|重新激活|reengagement).{0,5}(邮件|序列|流程)"],
     "intent": "email_sequence", "action_type": "execute", "skills": ["ecommerce-suite", "email-marketing"], "risk": "low", "priority": 74},

    # ── 地理编码 ──
    {"id": "amap_03", "patterns": [r"(地址|位置).{0,10}(经纬度|坐标|在哪|定位)",
                                   r"(经纬度|坐标).{0,5}(是多少|查询|转换|地址)",
                                   r"(高德|地图|静态地图|行政区).{0,10}(查|生成|导出|API)"],
     "intent": "geocoding", "action_type": "execute", "skills": ["amap-service"], "risk": "low", "priority": 74},

    # ── 洗稿/改写 ──
    {"id": "wcol_02", "patterns": [r"(洗稿|改写|二次创作).{0,10}(文章|内容|公众号)",
                                   r"(参考|借鉴).{0,5}(竞品|对手|公众号).{0,5}(文章|内容|写法)"],
     "intent": "article_rewrite", "action_type": "execute", "skills": ["wechat-suite", "wechat-collector"], "risk": "low", "priority": 73},

    # ── 状态查询 ──
    {"id": "status_01", "patterns": [r"^(现在|目前|当前).{0,5}(怎么样|什么情况|状态|进度|进展)[？?]?$"],
     "intent": "status_query", "action_type": "execute", "risk": "low", "priority": 75},
    {"id": "status_02", "patterns": [r"^(做|完成|弄).{0,5}(好了吗|完了吗|怎么样了)[？?]?$"],
     "intent": "progress_query", "action_type": "execute", "risk": "low", "priority": 75},

    # ── 文案 ──

    # ── 小红书数据 ──

    # ── 新闻/资讯 ──
    {"id": "news_01", "patterns": [r"(AI|人工智能|科技|互联网|行业|产品|技术).{0,5}(新闻|资讯|热点|动态|早报|晚报|日报|weekly)",
                                   r"(搜索|查|找).{0,8}(今天|今日|最新|昨天).{0,5}(新闻|资讯|消息|动态)",
                                   r"(帮我查|查一下|搜一下|看看).{0,5}(最新|今天|今日).{0,5}(新闻|资讯)",
                                   r"(每日|每天|定时).{0,5}(新闻|资讯|推送).{0,10}(top\d+|\d+条|精选|汇总)"],
     "intent": "news_search", "action_type": "execute", "skills": ["research-suite"], "risk": "low", "priority": 72},

    # ── 价格监控 ──
    {"id": "pm_01", "patterns": [r"(监控|盯着|追踪).{0,5}(价格|price).{0,10}(商品|产品|URL|链接)",
                                 r"(监控|盯着|追踪).{0,10}(商品|产品).{0,5}(价格|price)",
                                 r"(价格).{0,5}(降了|跌了|达到|提醒|通知|alert)"],
     "intent": "price_monitor", "action_type": "execute", "skills": ["ecommerce-suite", "price-monitor"], "risk": "low", "priority": 72},

    # ── SEO ──
    {"id": "seo_01", "patterns": [r"(SEO|seo|搜索引擎优化).{0,10}(关键词|优化|分析|建议|报告)",
                                  r"(关键词).{0,5}(研究|挖掘|规划|建议|推荐).{0,10}(SEO|搜索|亚马逊|谷歌)"],
     "intent": "seo_research", "action_type": "execute", "skills": ["ecommerce-suite", "seo-tools"], "risk": "low", "priority": 72},
    {"id": "seo_02", "patterns": [r"(优化|检查).{0,5}(这篇|这个|这份).{0,5}(文章|内容|Listing|listing).{0,5}(SEO|seo|关键词)",
                                  r"(文章|内容|Listing).{0,5}(SEO|seo).{0,5}(诊断|评分|改进|优化建议)"],
     "intent": "seo_optimize", "action_type": "execute", "skills": ["ecommerce-suite", "seo-tools"], "risk": "low", "priority": 72},

    # ── 图片 (子类型) ──
    {"id": "image_02a", "patterns": [r"(名片|business\s*card)"],
     "intent": "image_generation", "action_type": "execute", "skills": ["qwen-image"], "risk": "low", "priority": 72, "sub_intent": "biz_card"},
    {"id": "image_02b", "patterns": [r"(海报|poster|宣传图|banner|横幅)"],
     "intent": "image_generation", "action_type": "execute", "skills": ["qwen-image"], "risk": "low", "priority": 72, "sub_intent": "biz_poster"},
    {"id": "image_02c", "patterns": [r"(头像|avatar|IP形象|ip形象|个人形象)"],
     "intent": "image_generation", "action_type": "execute", "skills": ["qwen-image"], "risk": "low", "priority": 72, "sub_intent": "social_avatar"},
    {"id": "image_02d", "patterns": [r"(产品图|产品照|电商.*图|主图|白底图)"],
     "intent": "image_generation", "action_type": "execute", "skills": ["qwen-image"], "risk": "low", "priority": 72, "sub_intent": "ecom_main"},
    {"id": "image_02e", "patterns": [r"(微缩|miniature|等距|isometric|水晶|毛绒|充气).{0,5}(场景|风格|效果|质感|玩具)"],
     "intent": "image_generation", "action_type": "execute", "skills": ["qwen-image"], "risk": "low", "priority": 72, "sub_intent": "3d_auto"},
    {"id": "image_02f", "patterns": [r"(天气|weather).{0,5}(卡片|图|card)", r"(冰箱贴|美食地图|分镜|storyboard)"],
     "intent": "image_generation", "action_type": "execute", "skills": ["qwen-image"], "risk": "low", "priority": 72, "sub_intent": "util_auto"},

    # ── 日历 ──
    {"id": "cal_02", "patterns": [r"^(今天|今日|今天的).{0,10}(日程|安排|计划|事情|事项)[？?]?$",
                                  r"^(本周|这周|这星期).{0,5}(日程|安排|有什么)[？?]?$"],
     "intent": "calendar_view", "action_type": "execute", "skills": ["calendar-manager"], "risk": "low", "priority": 82},
    {"id": "cal_01", "patterns": [r"(添加|创建|新建|加一个).{0,5}(日历|日程|会议|提醒|事件)",
                                  r"(帮我加|帮我记).{0,10}(日历|日程)"],
     "intent": "calendar_add", "action_type": "execute", "skills": ["calendar-manager"], "risk": "low", "priority": 80},

    # ── 量化/金融 ──

    # ── 竞品分析 ──
    {"id": "ca_01", "patterns": [r"(分析|调研|了解).{0,5}(竞品|竞争对手|竞争者|competitor)",
                                 r"(竞品|竞争对手).{0,10}(价格|卖点|策略|优劣|分析|对比)"],
     "intent": "competitor_analysis", "action_type": "execute", "skills": ["ecommerce-suite", "competitor-analysis", "research-suite"], "risk": "low", "priority": 70},

    # ── 图片 (通用) ──
    {"id": "image_02g", "patterns": [r"(生成|画|做|创建).{0,5}(图片|图|封面|配图)", r"(PPT|ppt|logo|Logo|包装).{0,5}(设计|图)?"],
     "intent": "image_generation", "action_type": "execute", "skills": ["qwen-image", "chart-image"], "risk": "low", "priority": 70, "sub_intent": "auto"},
    {"id": "image_01", "patterns": [r"(看|识别|分析|解读).{0,5}(图片|图|截图|照片|screenshot)"],
     "intent": "image_analysis", "action_type": "execute", "model": "openai-codex/gpt-5.4-mini", "skills": ["vision-reader", "qwen-image"], "risk": "low", "priority": 70},
    {"id": "image_03", "patterns": [r"(OCR|文字识别|提取.*文字)"],
     "intent": "ocr", "action_type": "execute", "model": "openai-codex/gpt-5.4-mini", "skills": ["vision-reader"], "risk": "low", "priority": 70},

    # ── 社媒数据 ──
    {"id": "sma_01", "patterns": [r"(分析|看看|统计).{0,5}(账号|内容|帖子).{0,5}(数据|效果|表现|数据分析)",
                                  r"(社媒|社交媒体|抖音|小红书|B站).{0,5}(数据|运营报告|复盘|分析报告)"],
     "intent": "social_analytics", "action_type": "execute", "skills": ["ecommerce-suite", "social-media-analytics"], "risk": "low", "priority": 70},
    {"id": "sma_02", "patterns": [r"(哪个|哪些).{0,5}(视频|内容|帖子).{0,5}(效果|表现|播放|数据).{0,5}(最好|最高|TOP)",
                                  r"(爆款|爆文).{0,5}(规律|特点|分析|什么).{0,5}(数据|内容|我的)"],
     "intent": "top_content_analysis", "action_type": "execute", "skills": ["ecommerce-suite", "social-media-analytics"], "risk": "low", "priority": 70},

    # ── 文件/文档/记忆 ──
    {"id": "memory_01", "patterns": [r"(上次|之前|昨天|前天).{0,10}(那个|说的|提到|做的|方案)"],
     "intent": "memory_recall", "action_type": "execute", "risk": "low", "priority": 70, "use_memory": True,
     "skills": ["knowledge-graph-memory", "rag-knowledge-base"]},
    {"id": "memory_02", "patterns": [r"(记住|记一下|备忘|reminder|提醒我)"],
     "intent": "memory_store", "action_type": "execute", "risk": "low", "priority": 70},
    {"id": "memory_03", "patterns": [r"(搜索.*记忆|查.*笔记|知识库|knowledge)"],
     "intent": "knowledge_search", "action_type": "execute", "risk": "low", "priority": 70, "use_memory": True,
     "skills": ["rag-knowledge-base", "knowledge-graph-memory"]},
    {"id": "file_01", "patterns": [r"(收到|接收|传来|发来).{0,5}(文件|文档|图片|表格|excel|pdf|word|ppt)"],
     "intent": "file_received", "action_type": "execute", "risk": "low", "priority": 70,
     "skills": ["document-suite", "excel-xlsx", "word-docx-1.0.0", "vision-reader"]},
    {"id": "file_02", "patterns": [r"(读取|打开|解析|识别|提取).{0,5}(pdf|PDF)"],
     "intent": "pdf_read", "action_type": "execute", "skills": ["document-suite", "document-qa"], "risk": "low", "priority": 70},
    {"id": "file_03", "patterns": [r"(看看|帮我看|分析一下).{0,8}(这个文件|这张图|这个文档|这个表)"],
     "intent": "file_analysis", "action_type": "execute",
     "skills": ["document-suite", "excel-xlsx", "word-docx-1.0.0", "vision-reader"], "risk": "low", "priority": 70},

    # ── 市场分析 ──
    {"id": "ca_02", "patterns": [r"(市场概况|市场分析|行业分析).{0,10}(帮我|做|生成|报告)",
                                 r"(亚马逊|shopify|lazada|shopee).{0,5}(market|市场|品类|分析|行情)"],
     "intent": "market_overview", "action_type": "execute", "skills": ["ecommerce-suite", "competitor-analysis"], "risk": "low", "priority": 68},

    # ── Cron / 系统 ──
    {"id": "cron_01", "patterns": [r"(定时|cron|计划任务|schedule|每天|每周|每小时)"],
     "intent": "cron_management", "action_type": "execute", "skills": ["cron-scheduler"], "risk": "medium", "priority": 65},
    {"id": "sys_01", "patterns": [r"(系统状态|健康检查|health\s*check|status)"],
     "intent": "system_status", "action_type": "execute", "skills": ["system-control"], "risk": "low", "priority": 65},

    # ── 文档/Excel/Word ──
    {"id": "doc_01", "patterns": [r"(excel|xlsx|表格|电子表格)"],
     "intent": "excel_operation", "action_type": "execute", "skills": ["document-suite", "excel-xlsx"], "risk": "low", "priority": 65},
    {"id": "doc_02", "patterns": [r"(word|docx|文档|报告).{0,10}(生成|创建|写|导出)"],
     "intent": "word_generation", "action_type": "execute", "skills": ["document-suite", "word-docx-1.0.0"], "risk": "low", "priority": 65},
    {"id": "doc_03", "patterns": [r"(图表|chart|可视化|画.*图|柱状图|折线图|饼图)"],
     "intent": "data_visualization", "action_type": "execute", "skills": ["dataviz-suite", "python-dataviz", "chart-image"], "risk": "low", "priority": 65},

    # ── 翻译 ──
    {"id": "lang_01", "patterns": [r"(翻译|translate|英译中|中译英)"],
     "intent": "translation", "action_type": "execute", "risk": "low", "priority": 60},
    {"id": "lang_02", "patterns": [r"(总结|摘要|summarize|summary|概括)"],
     "intent": "summarization", "action_type": "execute", "risk": "low", "priority": 55},
    {"id": "lang_03", "patterns": [r"(翻译|translate).{0,10}(文件|合同|文档|pdf|csv|excel|listing)",
                                  r"(电商|商品|产品).{0,5}(文案|描述|listing).{0,5}(翻译|translate|英文|中文)"],
     "intent": "file_translation", "action_type": "execute", "skills": ["translation"], "risk": "low", "priority": 65},

    # ── 代码 ──
    {"id": "code_01", "patterns": [r"(写|编写|生成).{0,5}(代码|脚本|程序|function|class)"],
     "intent": "code_generation", "action_type": "execute", "model": "deepseek/deepseek-reasoner", "risk": "low", "priority": 60},
    {"id": "code_02", "patterns": [r"(debug|调试|报错|bug|error|异常|traceback)"],
     "intent": "debugging", "action_type": "execute", "model": "deepseek/deepseek-reasoner", "risk": "low", "priority": 60},
    {"id": "code_03", "patterns": [r"(python|javascript|typescript|bash|shell|sql)"],
     "intent": "code_task", "action_type": "execute", "risk": "low", "priority": 30},

    # ── 搜索/网页 ──
    {"id": "web_01", "patterns": [r"(搜索|搜一下|查一下|google|百度|search)", r"(打开|访问).{0,5}(网页|网站|链接|url)"],
     "intent": "web_search", "action_type": "execute", "skills": ["research-suite"], "risk": "low", "priority": 60},
    {"id": "web_02", "patterns": [r"(新闻|资讯|热点|rss|miniflux|feed)"],
     "intent": "news_reading", "action_type": "execute", "skills": ["research-suite", "miniflux-news"], "risk": "low", "priority": 60},
    {"id": "web_03", "patterns": [r"(reddit|帖子)"],
     "intent": "reddit_browse", "action_type": "execute", "skills": ["reddit-readonly-1.0.0"], "risk": "low", "priority": 60},
    {"id": "web_04", "patterns": [r"(爬|抓取|scrape|crawl).{0,10}(网页|数据|内容)"],
     "intent": "web_scrape", "action_type": "execute", "skills": ["web-scraper", "research-suite"], "risk": "low", "priority": 60},

    # ── 研究/调研 ──
    {"id": "research_01", "patterns": [r"(调研|研究|了解一下|学习).{0,10}(技术|产品|市场|行业)",
                                       r"(最新|今日|每日|今天).{0,5}(新闻|资讯|动态|热点|进展).{0,5}(有哪些|是什么|推送|汇总)",
                                       r"(AI|人工智能|科技|互联网).{0,8}(新闻|资讯|动态|发展|趋势).{0,5}(有哪些|是什么)"],
     "intent": "research", "action_type": "execute", "skills": ["research-suite"], "risk": "low", "priority": 55},
    {"id": "research_02", "patterns": [r"(深度研究|自动研究|研究报告|调研报告|多轮研究|交叉验证|最终报告)",
                                       r"(帮我|给我).{0,10}(做|生成|写).{0,10}(研究报告|调研报告)",
                                       r"(围绕|针对).{0,20}(主题|问题).{0,10}(做|展开).{0,10}(深度研究|研究报告)"],
     "intent": "deep_research", "action_type": "execute", "skills": ["auto-researcher", "research-suite"], "risk": "low", "priority": 56},

    # ── 深度推理 ──
    {"id": "reason_03", "patterns": [r"(投资|买入|卖出|加仓|减仓|止损).{0,10}(分析|建议|推荐)"],
     "intent": "investment_decision", "action_type": "plan", "risk": "high", "priority": 55,
     "skills": ["alpha-research"], "use_reasoning": True, "reasoning_template": "investment_decision"},
    {"id": "reason_04", "patterns": [r"(根因|root\s*cause|为什么.*失败|为什么.*出错|排查)"],
     "intent": "root_cause_analysis", "action_type": "execute", "risk": "low", "priority": 55,
     "use_reasoning": True, "reasoning_template": "root_cause_analysis"},
    # ── 效果追踪 / 工作流 ──
    {"id": "effect_01", "patterns": [r"(效果|成果|进度|进展|跟踪|track)"],
     "intent": "effect_tracking", "action_type": "execute", "skills": ["effect-tracker"], "risk": "low", "priority": 50},
    {"id": "flow_01", "patterns": [r"(工作流|workflow|流程|pipeline|自动化)"],
     "intent": "workflow", "action_type": "execute", "skills": ["workflow"], "risk": "low", "priority": 50},

    {"id": "reason_01", "patterns": [r"(分析|评估|比较).{0,15}(方案|策略|选型|架构|设计)"],
     "intent": "deep_analysis", "action_type": "plan", "risk": "low", "priority": 50,
     "use_reasoning": True, "reasoning_template": "scheme_evaluation"},
    {"id": "reason_05", "patterns": [r"^(?=.{15,}$).{0,30}(是否|应该|值不值|合不合理|有没有必要|需不需要|能不能|要不要).{0,30}$"],
     "intent": "quick_decision", "action_type": "execute", "risk": "low", "priority": 42,
     "use_reasoning": True, "reasoning_template": "general_analysis"},
    {"id": "reason_02", "patterns": [r"(是否|应该|合理|值得|有必要).{10,50}(吗|呢|么|呀|\?|？)"],
     "intent": "decision_analysis", "action_type": "execute", "risk": "low", "priority": 40,
     "use_reasoning": True, "reasoning_template": "general_analysis"},
]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 复合意图连接词检测 (零LLM开销)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMPOUND_MARKERS = [
    re.compile(r"(然后|接着|之后|再|同时|并且|顺便).{0,20}(帮我|给我|发到|保存|发送|生成|写|做|创建|上传|推送)"),
    re.compile(r"(先|第一步).{1,30}(再|然后|第二步|接着)"),
    re.compile(r"(完成后|做完后|生成后|写好后).{0,20}(再|然后|接着|发到|发|传|推)"),
]

# 预编译内置规则
for rule in BUILTIN_RULES:
    rule["_compiled"] = [re.compile(p, re.IGNORECASE) for p in rule["patterns"]]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 规则引擎核心
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_compiled_rules = None
_custom_rules = []


def _compile_rules():
    """编译所有规则的正则表达式"""
    global _compiled_rules
    all_rules = BUILTIN_RULES + _custom_rules
    _compiled_rules = []
    for rule in all_rules:
        compiled_patterns = []
        for pat in rule.get("patterns", []):
            try:
                compiled_patterns.append(re.compile(pat, re.IGNORECASE))
            except re.error:
                continue
        if compiled_patterns:
            _compiled_rules.append({**rule, "_compiled": compiled_patterns})
    _compiled_rules.sort(key=lambda r: r.get("priority", 50), reverse=True)


def load_custom_rules():
    """从文件加载自定义规则（rule-miner 生成 + pattern-library 高置信模式）"""
    global _custom_rules
    _custom_rules = []

    # 1. 从 custom-rules.json 加载
    if CUSTOM_RULES_FILE.exists():
        try:
            with open(CUSTOM_RULES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for r in data.get("rules", []):
                if r.get("status") not in ("active", "testing"):
                    continue
                patterns = r.get("pattern", r.get("patterns", []))
                if isinstance(patterns, str):
                    patterns = [patterns]
                if patterns:
                    _custom_rules.append({
                        "id": r.get("id", "custom"),
                        "patterns": patterns,
                        "intent": r.get("intent", "learned_pattern"),
                        "action_type": r.get("action_type", "execute"),
                        "skills": r.get("skills", []),
                        "risk": "low",
                        "priority": 45,
                        "_source": "custom_rule",
                    })
        except (json.JSONDecodeError, IOError):
            pass

    # 2. 从 pattern-library 中提取高置信度模式
    if PATTERN_LIBRARY.exists():
        try:
            with open(PATTERN_LIBRARY, "r", encoding="utf-8") as f:
                pl = json.load(f)
            for p in pl.get("patterns", []):
                if p.get("success_rate", 0) >= 0.85 and p.get("frequency", 0) >= 5:
                    pattern_text = p.get("pattern", "")
                    if pattern_text and not any(r["id"] == f"pl_{p.get('id','')}" for r in _custom_rules):
                        _custom_rules.append({
                            "id": f"pl_{p.get('id', '')}",
                            "patterns": [re.escape(pattern_text)],
                            "intent": p.get("intent", "learned_pattern"),
                            "action_type": "execute",
                            "skills": [],
                            "risk": "low",
                            "priority": 45,
                            "_source": "pattern_library",
                        })
        except (json.JSONDecodeError, IOError):
            pass

    _compile_rules()


def detect_compound_intent(user_input: str) -> bool:
    """检测是否为复合意图(含连接词+后续动词), 仅正则, 0ms开销"""
    text = user_input[:300]
    return any(p.search(text) for p in COMPOUND_MARKERS)


def match(user_input: str) -> dict:
    """匹配用户输入，返回最佳匹配规则结果"""
    if _compiled_rules is None:
        load_custom_rules()

    input_stripped = user_input.strip()
    if not input_stripped:
        return {
            "matched": True, "rule_id": "_empty_input",
            "intent": "greeting", "action_type": "chat",
            "routing": {"suggested_model": "deepseek/deepseek-chat", "suggested_skills": [],
                        "use_reasoning_chain": False, "reasoning_template": None,
                        "use_memory_search": False, "risk_level": "low"},
            "_source": "rule_engine:_empty_input", "_latency_ms": 0,
        }

    # 截断长文本，规则匹配只需前200字符
    match_text = input_stripped[:200] if len(input_stripped) > 200 else input_stripped

    start = time.monotonic()
    best_match = None
    best_priority = -1

    for rule in _compiled_rules:
        for compiled_pat in rule["_compiled"]:
            if compiled_pat.search(match_text):
                if rule.get("priority", 50) > best_priority:
                    best_priority = rule.get("priority", 50)
                    best_match = rule
                break

    elapsed_ms = int((time.monotonic() - start) * 1000000) / 1000

    if best_match:
        result = {
            "matched": True,
            "rule_id": best_match["id"],
            "intent": best_match.get("intent", "unknown"),
            "action_type": best_match.get("action_type", "chat"),
            "routing": {
                "suggested_model": best_match.get("model", "deepseek/deepseek-chat"),
                "suggested_skills": best_match.get("skills", []),
                "use_reasoning_chain": best_match.get("use_reasoning", False),
                "reasoning_template": best_match.get("reasoning_template"),
                "use_memory_search": best_match.get("use_memory", False),
                "risk_level": best_match.get("risk", "low"),
            },
            "_source": f"rule_engine:{best_match['id']}",
            "_latency_ms": elapsed_ms,
        }
        if best_match.get("sub_intent"):
            result["sub_intent"] = best_match["sub_intent"]
        _record_hit(best_match["id"])
        return result

    return {"matched": False, "_latency_ms": elapsed_ms}


def match_all(user_input: str, limit: int = 3) -> list:
    """返回所有匹配规则(按优先级降序), 用于复合意图链"""
    if _compiled_rules is None:
        load_custom_rules()
    input_stripped = user_input.strip()
    if not input_stripped:
        return []
    match_text = input_stripped[:200] if len(input_stripped) > 200 else input_stripped
    matches = []
    seen_intents = set()
    for rule in _compiled_rules:
        for compiled_pat in rule["_compiled"]:
            if compiled_pat.search(match_text):
                intent = rule.get("intent", "")
                if intent not in seen_intents:
                    seen_intents.add(intent)
                    matches.append({
                        "rule_id": rule["id"],
                        "intent": intent,
                        "action_type": rule.get("action_type", "chat"),
                        "skills": rule.get("skills", []),
                        "model": rule.get("model", "deepseek/deepseek-chat"),
                    })
                break
        if len(matches) >= limit:
            break
    return matches


def record_miss():
    """记录未命中"""
    stats = _load_stats()
    stats["total_misses"] += 1
    _save_stats(stats)


def _record_hit(rule_id: str):
    """记录规则命中统计"""
    stats = _load_stats()
    if rule_id not in stats["hits"]:
        stats["hits"][rule_id] = {"count": 0, "last_hit": None}
    stats["hits"][rule_id]["count"] += 1
    stats["hits"][rule_id]["last_hit"] = datetime.now().isoformat()
    stats["total_matches"] += 1
    _save_stats(stats)


def _load_stats() -> dict:
    if RULES_STATS_FILE.exists():
        try:
            with open(RULES_STATS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"hits": {}, "total_matches": 0, "total_misses": 0, "created_at": datetime.now().isoformat()}


def _save_stats(stats: dict):
    os.makedirs(STATE_DIR, exist_ok=True)
    stats["updated_at"] = datetime.now().isoformat()
    with open(RULES_STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)


def save_custom_rule(rule: dict):
    """保存一条自定义规则"""
    os.makedirs(STATE_DIR, exist_ok=True)
    data = {"rules": [], "updated_at": datetime.now().isoformat()}
    if CUSTOM_RULES_FILE.exists():
        try:
            with open(CUSTOM_RULES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    data["rules"] = [r for r in data.get("rules", []) if r.get("id") != rule.get("id")]
    data["rules"].append(rule)
    data["updated_at"] = datetime.now().isoformat()
    with open(CUSTOM_RULES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    load_custom_rules()


def show_stats():
    stats = _load_stats()
    total = stats.get("total_matches", 0) + stats.get("total_misses", 0)
    match_rate = stats["total_matches"] / total * 100 if total > 0 else 0
    print(f"📊 Rule Engine V15 Stats")
    print("=" * 60)
    print(f"  总请求: {total} | 命中: {stats['total_matches']} | 未命中: {stats['total_misses']}")
    print(f"  命中率: {match_rate:.1f}%")
    print(f"  内置规则: {len(BUILTIN_RULES)} | 自定义规则: {len(_custom_rules)}")
    if stats.get("hits"):
        print(f"\n  Top 10 规则命中:")
        sorted_hits = sorted(stats["hits"].items(), key=lambda x: x[1]["count"], reverse=True)
        for rule_id, info in sorted_hits[:10]:
            print(f"    {info['count']:4d}x  {rule_id}")


def list_rules():
    if _compiled_rules is None:
        load_custom_rules()
    print(f"� Rule Engine V15 — {len(BUILTIN_RULES)} 内置 + {len(_custom_rules)} 自定义")
    print("=" * 60)
    by_intent = {}
    for r in BUILTIN_RULES:
        cat = r["intent"].split("_")[0] if "_" in r["intent"] else r["intent"]
        if cat not in by_intent:
            by_intent[cat] = []
        by_intent[cat].append(r)
    for cat, rules in sorted(by_intent.items()):
        print(f"\n  [{cat}] ({len(rules)} 条)")
        for r in rules:
            print(f"    - {r['id']}: {r['intent']} → {r['action_type']} (p={r.get('priority', 50)})")


if __name__ == "__main__":
    load_custom_rules()

    if "--match" in sys.argv:
        idx = sys.argv.index("--match")
        if len(sys.argv) > idx + 1:
            user_input = " ".join(sys.argv[idx + 1:])
            result = match(user_input)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            if detect_compound_intent(user_input):
                print("\n⚡ 复合意图检测: 是")
                multi = match_all(user_input)
                if len(multi) > 1:
                    print(f"   匹配到 {len(multi)} 个意图:")
                    for m in multi:
                        print(f"     - {m['rule_id']}: {m['intent']}")

    elif "--stats" in sys.argv:
        show_stats()

    elif "--list" in sys.argv:
        list_rules()

    elif "--reload" in sys.argv:
        load_custom_rules()
        print(f"✅ 已重载: {len(BUILTIN_RULES)} 内置 + {len(_custom_rules)} 自定义规则")

    elif "--compound" in sys.argv:
        idx = sys.argv.index("--compound")
        text = " ".join(sys.argv[idx + 1:]) if len(sys.argv) > idx + 1 else ""
        print(f"复合意图: {'是' if detect_compound_intent(text) else '否'}")

    else:
        print("V15 Rule Engine")
        print("  --match <text>     匹配规则")
        print("  --list             列出所有规则")
        print("  --stats            查看统计")
        print("  --reload           重载自定义规则")
        print("  --compound <text>  检测复合意图")
