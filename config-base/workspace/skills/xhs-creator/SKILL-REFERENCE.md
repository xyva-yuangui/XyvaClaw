---
name: xhs-creator
version: 1.0.0
description: |
  小红书统一内容创作流水线。整合选题→调研→模板→创作→改写→质检→制图，
  一键生成高质量小红书笔记素材。合并原 xhs-content-workflow、xhs-content-templates、
  xhs-quality-checklist、xhs-monetization 四个技能。
status: stable
platform: [darwin, linux]
dependencies:
  skills: [academic-deep-research, content-creator, humanize-ai-text]
  bins: [python3]
  python: [playwright]
metadata:
  openclaw:
    emoji: "📕"
---

# 小红书统一创作流水线 (xhs-creator)

> 合并自: xhs-content-workflow + xhs-content-templates + xhs-quality-checklist + xhs-monetization

一键完成从选题到成品的完整工作流：

```
选题 → 深度调研 → 爆款模板 → 内容创作 → 人性化改写 → 质量检查 → 图片渲染 → 输出成品
```

---

## 快速开始

```bash
# 自动模式（推荐）
python xhs_creator.py -a -t "AI 工作流"

# 指定主题+风格
python xhs_creator.py -t "租房避坑指南" -s 踩坑

# 交互式
python xhs_creator.py

# 仅制图（已有文案）
python xhs_creator.py --render-only my_note.md

# 仅质检
python xhs_creator.py --check-only final.md
```

### 参数说明

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--topic` | `-t` | 笔记主题 | 交互式输入 |
| `--style` | `-s` | 风格（种草/干货/踩坑/教程/分享） | 种草 |
| `--template` | | 指定模板（pain-solution/compare/tutorial/list/story/opinion/hot） | 自动选择 |
| `--output` | `-o` | 输出目录 | ./output |
| `--render-only` | `-r` | 仅渲染图片 | false |
| `--check-only` | | 仅运行质检 | false |
| `-a` / `--auto` | | 自动模式：从热门话题生成 | false |
| `--no-research` | | 跳过调研环节 | false |
| `--theme` | | 卡片主题（default/sakura-pink/magazine/glassmorphism 等） | default |
| `--check` | | 健康检查：验证依赖和配置 | false |

---

## 工作流详解

### 步骤 1: 选题确定

**来源**:
- 用户输入主题
- Reddit 热门话题（自动翻译中文）
- 微博热搜
- 竞品账号爆款

**输出**: 确定的主题 + 目标受众

### 步骤 2: 深度调研

**调用技能**: `academic-deep-research`

- 多源数据收集（搜索引擎前 10 页 + 竞品文案 3-5 篇）
- 关键词提取（核心 3-5 个 + 长尾 5-10 个）
- 竞品分析（爆款结构 + 高互动元素 + 评论区高频问题）

**输出**: `research.json`

### 步骤 3: 爆款模板选择

根据内容类型自动推荐模板：

| 内容类型 | 推荐模板 | 爆款率 |
|----------|---------|--------|
| 工具/方法推荐 | 痛点解决型 (pain-solution) | ⭐⭐⭐⭐⭐ |
| 产品对比 | 对比测评型 (compare) | ⭐⭐⭐⭐ |
| 技能教学 | 教程步骤型 (tutorial) | ⭐⭐⭐⭐ |
| 资源汇总 | 清单汇总型 (list) | ⭐⭐⭐⭐ |
| 个人成长 | 故事经历型 (story) | ⭐⭐⭐⭐⭐ |
| 观点输出 | 观点态度型 (opinion) | ⭐⭐⭐ |
| 热点评论 | 热点评论型 (hot) | ⭐⭐⭐ |

#### 模板详情

**痛点解决型** ⭐⭐⭐⭐⭐:
```
1. 痛点场景开场（引发共鸣）
2. 效果数据展示（建立信任）
3-5. 解决方案 1-3（详细步骤）
6. 核心心法/原则（升华）
7. 行动清单（促进行动）
8. 福利/资源（涨粉转化）
9. 互动提问（增加评论）
```
标题公式: 「这 X 个 [方法/工具] 让我 [具体收益]！」

**对比测评型** ⭐⭐⭐⭐:
```
1. 选择困难场景 → 2. 测评对象 → 3-5. 维度对比 → 6. 综合评分 → 7. 购买建议 → 8. 避坑提醒
```

**教程步骤型** ⭐⭐⭐⭐:
```
1. 学习成果展示 → 2. 前后对比 → 3. 学习路径 → 4-6. 步骤详解 → 7. FAQ → 8. 资源推荐
```

**清单汇总型** ⭐⭐⭐⭐:
```
1. 汇总价值 → 2. 筛选标准 → 3-N. 清单项 → N+1. 使用建议 → N+2. 获取方式
```

**故事经历型** ⭐⭐⭐⭐⭐:
```
1. 高光/低谷开场 → 2. 背景 → 3. 转折点 → 4. 行动过程 → 5. 关键决策 → 6. 结果展示 → 7. 经验总结
```

### 步骤 4: 内容创作

**调用技能**: `content-creator`

**创作要求**:
- **标题**: ≤20 字，包含数字/疑问/感叹，击中痛点
- **开头钩子**: 前 3 张卡片用痛点场景/数据/效果吸引
- **正文结构**: 清晰逻辑主线 + 分点分段 + 小标题引导
- **结尾**: 行动清单 + 互动提问 + 福利诱导

**输出**: `draft.md`

### 步骤 5: 人性化改写

**调用技能**: `humanize-ai-text`

- **去 AI 味**: 避免「总之」「综上所述」等 AI 常见词
- **加口语**: 「真香」「绝了」+ 语气词「啊」「呢」「吧」
- **加情绪**: 情绪词 + 感叹句 + 反问句 + 情绪波动
- **加细节**: 个人经历 + 具体场景 + 具体数字 + 感官描述

**输出**: `final.md`

### 步骤 6: 质量检查

**四维评分体系** (总分 10 分制):

| 维度 | 权重 | 检查项 |
|------|------|--------|
| 内容深度 | 30% | 调研充分性（3+ 数据源）、信息密度（≥8 张卡片）、数据支撑 |
| 爆款结构 | 30% | 标题（≤20字）、开头钩子、内容结构、情绪曲线、行动号召 |
| 人性化程度 | 25% | 去 AI 味、口语化、情绪表达、真实细节 |
| 传播性 | 15% | 可引用性、可保存性、互动设计、SEO（5-10 Tags） |

**发布标准**:
| 总分 | 建议 | 行动 |
|------|------|------|
| **9-10** | 爆款潜质 | 立即发布 + 推广 |
| **8-8.9** | 优质内容 | 可发布 |
| **7-7.9** | 合格 | 建议优化后发布 |
| **<7** | 不合格 | 重新创作 |

**输出**: `quality_report.json`

### 步骤 7: 图片渲染

渲染 Markdown 为小红书图片卡片（封面 + 正文卡片）:

```bash
python scripts/render_xhs.py final.md -t default -m auto-split -o output/
```

**渲染主题**: default / playful-geometric / neo-brutalism / botanical / professional / retro / terminal / sketch / sakura-pink / magazine / glassmorphism / zen-minimal / pop-art / nordic-clean / gradient-mesh / xhs-native-pro

**分页模式**: separator / auto-fit / auto-split / dynamic

**图片规格**: 1080×1440px (3:4)，DPR 2

---

## 爆款元素库

### 开头钩子 (选 1-2 个)
- 😱 痛点场景（「你是不是也...」）
- 📊 效果数据（「3 个月从...到...」）
- ❓ 疑问开场（「为什么...」）
- 💥 反常识（「[常识] 是错的」）

### 信任建立 (选 2-3 个)
- 📈 数据对比表格
- 📸 实际使用截图
- 💬 用户评价/案例
- 🏆 成果/成绩展示

### 行动号召 (选 1-2 个)
- ✅ 行动清单（「今天/本周/本月」）
- 🎁 福利资源（「私信获取」）
- 💬 互动提问（「你怎么看？」）
- ➕ 关注引导（「关注我获取更多」）

---

## 发布前最终检查

### 基础检查
- [ ] 标题 ≤ 20 字
- [ ] 图片数量 1-9 张
- [ ] 图片尺寸正确 (1080×1440)
- [ ] Tags 数量 5-10 个
- [ ] 无错别字 / 无敏感词

### 技术检查
- [ ] 封面文字清晰可读
- [ ] 图片无模糊/失真
- [ ] 颜色对比度足够

### 合规检查
- [ ] 无虚假宣传 / 无违禁词 / 无侵权内容 / 符合平台规范

---

## 输出结构

```
output/
└── 2026-03-05_AI 工作流/
    ├── research.json        # 调研数据
    ├── draft.md             # 初稿
    ├── final.md             # 改写稿（用于发布）
    ├── quality_report.json  # 质量报告
    ├── cover.png            # 封面图
    ├── card_1.png           # 正文卡片 1
    ├── card_2.png           # 正文卡片 2
    └── ...
```

---

## 注意事项

1. **调研真实性**: 数据必须有来源，不可编造
2. **改写适度**: 保持专业性，核心信息不变
3. **质量优先**: 评分 < 7 分必须重写
4. **合规发布**: 遵守平台规范，避免敏感词

---

_合并自: xhs-content-workflow v1.0 + xhs-content-templates + xhs-quality-checklist v1.0 + xhs-monetization_  
_创建时间: 2026-03_
