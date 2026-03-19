---
name: commerce-travel-shopper
version: 0.2.0-beta
status: draft
description: Screenshot-driven cross-platform comparison assistant for flights, hotels, and shopping. Supports controlled agent execution with human confirmations.
metadata:
  openclaw:
    emoji: "🧭"
    requires:
      anyBins: ["node"]
---

# Commerce & Travel Shopper（无API版，自动采集 + 自动比价）

> 运行入口：`node scripts/feishu_agent_runtime.mjs`（支持 create/collect/auto-compare/ocr-extract/rank/draft/final-check/cmd）

目标：在你没有 API 的情况下，支持以下平台的真实页面比价，并尽量降低封控风险：

- 酒店/机票：**飞猪、去哪儿、携程、美团**
- 商品：**淘宝、京东**

## 1) 核心策略（无API场景）

1. **自动采集驱动，不做高频爬取**
   - 通过自动打开页面 + 自动滚动截图 + OCR结构化提取完成比价。
2. **关键风控人工确认，采集分析自动执行**
   - Skill 自动采集截图并分析；登录态通过平台 profile 复用，减少反复登录。
3. **一次比价只采“首屏+前N条”**
   - 控制访问深度，默认每平台只取前 10 条候选，避免异常流量。
4. **强审计**
   - 每条报价必须绑定截图证据（source + timestamp + evidence_id）。

## 2) 平台覆盖矩阵

| 场景 | 平台 | 采集方式 | 关键字段 |
|---|---|---|---|
| 机票 | 飞猪/去哪儿/携程/美团 | 搜索结果页截图 + 详情页截图（可选） | 票价、税费、起降时间、中转、行李、退改 |
| 酒店 | 飞猪/去哪儿/携程/美团 | 列表页截图 + 房型详情截图 | 每晚价、总价、早餐、取消政策、评分、位置 |
| 商品 | 淘宝/京东 | 列表页截图 + 商品详情截图 | 到手价、券后价、运费、店铺评分、发货地/时效 |

## 3) 能力模块（重构后）

### A. Task Planner（任务规划）
输入：
- 机票：出发地/目的地/日期/舱位偏好/行李需求
- 酒店：城市/入住离店/人数/预算/星级/可取消要求
- 商品：关键词/型号/预算/必须参数（颜色/版本/容量）

输出：平台查询清单 + 自动采集任务列表。

### B. Screenshot Collector（截图采集器）
- Skill 自动打开平台页面并滚动采集
- 支持 `item-selector` 定位商品卡片，只截候选商品区域
- 默认每平台独立会话目录，复用 cookie/session

### C. OCR Parser（截图解析）
- 从截图提取：价格、税费/服务费、规则文本、店铺/酒店评分。
- 解析失败字段标记为 `unknown`，避免误导自动决策。

### D. Offer Normalizer（报价归一）
统一结构：
- `base_price`、`tax_fee`、`coupon`、`final_price`
- `policy_text`（退改/取消）
- `inventory_hint`（有房/有票/库存）
- `source_platform`、`captured_at`、`evidence_id`

### E. Decision Engine（推荐引擎）
- 机票：总价 40% + 总耗时 25% + 退改 20% + 行李 15%
- 酒店：总价 35% + 取消政策 25% + 地理位置/评分 25% + 房型条件 15%
- 商品：到手价 45% + 店铺可信度 25% + 物流时效 15% + 售后 15%

## 4) 反封控改进（重点）

1. **“慢采集”协议**
   - 每平台每轮查询最多 1 次，轮次间隔 2~5 分钟随机等待。
2. **会话隔离**
   - 平台独立浏览器 profile（飞猪/去哪儿/携程/美团/淘宝/京东分离）。
3. **只读模式优先**
   - 首版不自动点击“立即购买/提交订单”，只到比价与草案。
4. **验证码止损**
   - 出现验证码立即暂停该平台任务并记录，交由人工处理。
5. **缓存窗口**
   - 同一查询 30 分钟内优先复用上次截图结果，不重复访问。

## 5) 执行流程（你实际可用）

1. 你下达任务（例如“明晚上海到深圳机票比价”）。
2. Skill 自动执行 `AUTO_COMPARE`：逐个平台打开、滚动截图、结构化提取。
3. Skill 输出统一报价表 + 选中商品证据图（非整页）。
5. Skill 生成推荐结论 + 风险提示（退改、隐藏费用）。
6. 若你确认，再生成下单草案（不自动支付）。

### 一键自动比价命令（飞书）

```text
SHOP AUTO_COMPARE --urls '[{"source":"jd","url":"https://search.jd.com/Search?keyword=牛奶"},{"source":"taobao","url":"https://s.taobao.com/search?q=牛奶"}]' --item-selector '.item-card'
SHOP SELECTED
```

### 同款 SKU 比价命令（平台内 + 跨平台）

```text
SHOP DOCTOR
SHOP SET_ANCHOR --keyword "特仑苏A" --brand "蒙牛" --spec "250ml*24" --pack-count 24
SHOP SAME_REPORT --threshold 0.78
SHOP AUTO_COMPARE_SAME --urls '[{"source":"jd","url":"https://search.jd.com/Search?keyword=特仑苏250ml*24"},{"source":"taobao","url":"https://s.taobao.com/search?q=特仑苏250ml*24"}]' --spec "250ml*24" --threshold 0.78
```

- `DOCTOR`：输出当前实际加载的 runtime 路径、模块路径、版本号（用于排查“改了但没生效”）
- `SET_ANCHOR`：定义同款锚点（品牌/规格/件数）
- `SAME_REPORT`：对当前任务已提取报价生成同款报告
- `AUTO_COMPARE_SAME`：自动采集 + OCR + 同款匹配 + 平台内/跨平台报告一键完成

> 架构说明：SHOP 命令核心实现已下沉到 `~/.openclaw/workspace/skills/commerce-travel-shopper/lib/feishu_bridge_core.mjs`，
> Feishu 扩展侧仅保留代理层，避免双仓逻辑漂移。

## 6) 代理执行模式（关键节点人工确认）

这是你要的“AI代理执行”版本：

- 代理可做：打开页面、截图、解析、比价、进入下单页、填写订单信息、点击“提交订单前一步”。
- 必须人工确认：
  1. **点击“提交订单”前确认**
  2. **进入支付页前确认**
  3. **点击“支付/付款”前最终确认**

### 6.1 状态机（必须遵守）

1. `COLLECTING`：采集截图
2. `ANALYZING`：OCR与规则解析
3. `RANKED`：比价排序完成
4. `DRAFT_READY`：订单草案生成
5. `WAIT_CONFIRM_SUBMIT`：等待你确认“可提交订单”
6. `WAIT_CONFIRM_PAY`：等待你确认“可发起支付”
7. `DONE`：完成
8. `ABORTED`：中止（触发风控/人工取消）

### 6.2 三道确认口令（建议固定）

- 提交前：`CONFIRM_SUBMIT <task_id>`
- 支付前：`CONFIRM_PAY <task_id>`
- 强制中止：`ABORT <task_id>`

任何时候收到 `ABORT`，代理立刻停止所有点击行为。

## 7) 平台级执行清单（机票/酒店/商品）

### 7.1 机票（飞猪/去哪儿/携程/美团）

每个平台最少采集：
1. 搜索结果首屏（默认排序）
2. 价格排序后首屏
3. 入选航班详情页（含退改、行李、税费）

进入下单阶段前必须二次核验：
- 票面价、税费、总价是否一致
- 航变/退改政策是否变化

### 7.2 酒店（飞猪/去哪儿/携程/美团）

每个平台最少采集：
1. 列表页首屏
2. 价格排序后首屏
3. 入选酒店房型详情页（早餐、取消政策、税费）

进入下单阶段前必须二次核验：
- 入住离店日期、人数、房型
- 总价是否含服务费/税费

### 7.3 商品（淘宝/京东）

每个平台最少采集：
1. 列表页首屏
2. 目标商品详情页
3. 结算页价格构成（券后、运费、总价）

进入下单阶段前必须二次核验：
- 规格（颜色/容量/版本）
- 到手价与运费
- 店铺评分与售后条款

## 8) Skill 接口建议（无API版）

- `prepare_compare_task(query)`：生成截图采集清单
- `ingest_screenshots(task_id, files[])`：导入截图
- `extract_offers(task_id)`：OCR + 结构化
- `rank_offers(task_id)`：比价排序
- `build_checkout_draft(task_id, offer_id)`：生成下单草案
- `final_check(task_id)`：支付前最后校验

## 9) 数据结构建议（截图证据必填）

```json
{
  "task_type": "flight",
  "query": {"from": "SHA", "to": "SZX", "date": "2026-03-15"},
  "offers": [
    {
      "source": "ctrip",
      "final_price": 1280,
      "tax_fee": 120,
      "policy": "改签收费",
      "evidence_id": "ev_001",
      "screenshot_file": "screenshots/flight-ctrip-001.png"
    }
  ],
  "recommended_offer_id": "offer_2",
  "reason": ["总价最低", "退改更灵活"]
}
```

建议新增字段（用于代理执行）：

```json
{
  "execution": {
    "state": "WAIT_CONFIRM_SUBMIT",
    "confirm_submit": false,
    "confirm_pay": false,
    "abort": false
  }
}
```

## 10) 安全边界

- 不存明文支付密码与短信验证码。
- 登录态使用本地加密存储并可一键失效。
- 所有下单动作需要 `confirm_token` 二次确认。
- 审计日志保留：查询、推荐、人工确认、执行结果。

## 11) 回滚与止损（必须实现）

触发以下任一条件，立即 `ABORTED`：

1. 截图与解析价格偏差 > 5%
2. 退改/取消条款缺失或无法识别
3. 页面出现风控验证且 2 分钟内未人工完成
4. 下单页价格高于你设定上限
5. 你发送 `ABORT <task_id>`

回滚动作：
- 停止点击
- 关闭当前下单页
- 输出“中止原因 + 最后证据截图 + 当前最佳候选”

## 12) 你的场景推荐落地（本次改进版）

优先做：
1. **飞猪/去哪儿/携程/美团机酒四平台截图比价**
2. **淘宝/京东商品双平台截图比价**
3. **统一比价报告 + 风险解释 + 下单草案（不自动支付）**

不建议首版就做：
- 全自动支付
- 验证码绕过
- 高频翻页抓取

以上三项会显著提高封控和账号风险。

## 13) 可直接使用的任务模板

### 13.1 机票任务

```text
TASK flight_compare
from=SHA
to=SZX
date=2026-03-10
passengers=1
baggage=20kg
budget=1500
platforms=feizhu,qunar,ctrip,meituan
mode=agent_execution
```

### 13.2 酒店任务

```text
TASK hotel_compare
city=深圳
checkin=2026-03-10
checkout=2026-03-12
guests=2
budget_per_night=600
cancel_policy=free_cancel
platforms=feizhu,qunar,ctrip,meituan
mode=agent_execution
```

### 13.3 商品任务（淘宝+京东）

```text
TASK shop_compare
keyword=iPhone 15 256G
budget=6000
platforms=taobao,jd
must_have=国行,未拆封
mode=agent_execution
```

### 13.4 执行确认模板

```text
CONFIRM_SUBMIT task_20260302_xxx
CONFIRM_PAY task_20260302_xxx
ABORT task_20260302_xxx
```
