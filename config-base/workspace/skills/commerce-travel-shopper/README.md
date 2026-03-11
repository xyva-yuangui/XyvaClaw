# commerce-travel-shopper

飞书群内可执行版（首版）已落地：

- 任务创建与状态机流转
- 自动截图采集（含滚动、多平台会话复用）与报价提取、排序、下单草案、支付前校验
- OCR 自动提取（优先 sidecar 文本/JSON，缺失时回退 vision-reader 实图 OCR）与风控校验
- 文本命令确认：`CONFIRM_SUBMIT` / `CONFIRM_PAY` / `ABORT`
- 单群单活跃任务约束
- 审计日志与任务持久化

## 目录

- `scripts/feishu_agent_runtime.mjs`：CLI 入口（可被飞书消息路由调用）
- `scripts/collect_screenshots.mjs`：调用 browser-pilot 批量采集截图
- `lib/feishu_runtime.mjs`：核心运行时（状态机 + 权限 + 审计）
- `lib/workflow.mjs`：状态机定义与转移校验
- `runtime/`：运行时数据（自动生成）

## 快速开始

### 1) 创建任务

```bash
node scripts/feishu_agent_runtime.mjs create \
  --type flight \
  --query '{"from":"SHA","to":"SZX","date":"2026-03-10"}' \
  --platforms feizhu,qunar,ctrip,meituan \
  --operator momo
```

### 2) 推进状态到待提交确认

```bash
node scripts/feishu_agent_runtime.mjs advance --operator momo
node scripts/feishu_agent_runtime.mjs advance --operator momo
node scripts/feishu_agent_runtime.mjs advance --operator momo
node scripts/feishu_agent_runtime.mjs advance --operator momo
```

### 2.1 自动采集 + 自动比价（推荐）

```bash
# 一条命令完成：自动打开页面截图 -> OCR提取 -> 排序 -> 生成草案
node scripts/feishu_agent_runtime.mjs auto-compare \
  --task task_xxx \
  --urls '[{"source":"jd","url":"https://search.jd.com/Search?keyword=牛奶"},{"source":"taobao","url":"https://s.taobao.com/search?q=牛奶"}]' \
  --item-selector '.item-card' \
  --scroll-count 3 \
  --wait 3000 \
  --operator momo

# 仅查看“选中商品”的图片与价格（不是整页）
node scripts/feishu_agent_runtime.mjs selected --task task_xxx
```

### 2.2 导入截图与报价（兼容模式）

```bash
node scripts/feishu_agent_runtime.mjs ingest \
  --task task_xxx \
  --files '/tmp/ctrip_1.png,/tmp/qunar_1.png' \
  --operator momo

# 自动采集截图（通过 browser-pilot）并自动入库 evidence
node scripts/feishu_agent_runtime.mjs collect \
  --task task_xxx \
  --urls '[{"source":"ctrip","url":"https://flights.ctrip.com"},{"source":"qunar","url":"https://flight.qunar.com"}]' \
  --wait 3000 \
  --full-page \
  --operator momo

node scripts/feishu_agent_runtime.mjs extract \
  --task task_xxx \
  --offers '[{"offer_id":"o1","source":"ctrip","final_price":1280},{"offer_id":"o2","source":"qunar","final_price":1250}]' \
  --operator momo

node scripts/feishu_agent_runtime.mjs rank --task task_xxx --operator momo
node scripts/feishu_agent_runtime.mjs draft --task task_xxx --offer o2 --operator momo

# 使用截图 sidecar 自动提取报价（可替代 extract）
node scripts/feishu_agent_runtime.mjs ocr-extract --task task_xxx --operator momo
```

### 3) 飞书文本命令（兜底）

```bash
node scripts/feishu_agent_runtime.mjs cmd --text 'CONFIRM_SUBMIT task_xxx' --operator momo
node scripts/feishu_agent_runtime.mjs cmd --text 'CONFIRM_PAY task_xxx' --operator momo
node scripts/feishu_agent_runtime.mjs cmd --text 'ABORT task_xxx' --operator momo
```

### 3.1 支付前最终校验

```bash
node scripts/feishu_agent_runtime.mjs risk-check --task task_xxx --operator momo
node scripts/feishu_agent_runtime.mjs final-check --task task_xxx --operator momo
```

### 4) 查看当前任务

```bash
node scripts/feishu_agent_runtime.mjs active
node scripts/feishu_agent_runtime.mjs show --task task_xxx
```

## 权限控制（可选）

- 文件：`allowed_operators.json`（可选）
- 环境变量：`COMMERCE_ALLOWED_OPERATORS`（逗号分隔）

如果两者都为空，则默认不限制操作者。

## 持久化文件

- `runtime/state.json`：active task 指针
- `runtime/tasks/<task_id>.json`：任务快照
- `runtime/logs/<task_id>.events.jsonl`：事件审计日志

## 飞书接入建议

将机器人接收到的文本消息透传给：

```text
node scripts/feishu_agent_runtime.mjs cmd --text '<message>' --operator '<open_id或用户名>'
```

对卡片按钮回调，映射为同样三种命令即可：

- `CONFIRM_SUBMIT <task_id>`
- `CONFIRM_PAY <task_id>`
- `ABORT <task_id>`

## 飞书群内直连命令（已接入 feishu 扩展）

当 `extensions/feishu` 启用后，可在群里直接发：

```text
SHOP HELP
SHOP CREATE --type hotel --query '{"city":"深圳","checkin":"2026-03-10","checkout":"2026-03-12"}' --platforms feizhu,qunar,ctrip,meituan
SHOP ACTIVE
SHOP STATUS
SHOP SHOW
SHOP REPORT
SHOP SELECTED
SHOP COLLECT --urls '[{"source":"jd","url":"https://search.jd.com/Search?keyword=牛奶"}]' --item-selector '.item-card'
SHOP AUTO_COMPARE --urls '[{"source":"jd","url":"https://search.jd.com/Search?keyword=牛奶"},{"source":"taobao","url":"https://s.taobao.com/search?q=牛奶"}]' --item-selector '.item-card'
SHOP INGEST --files '/tmp/ctrip_1.png,/tmp/qunar_1.png'
SHOP OCR_EXTRACT
SHOP EXTRACT --offers '[{"offer_id":"o1","source":"ctrip","final_price":1280},{"offer_id":"o2","source":"qunar","final_price":1250}]'
SHOP RANK
SHOP DRAFT --offer o2
CONFIRM_SUBMIT
确认提交
SHOP RISK_CHECK
SHOP FINAL_CHECK
CONFIRM_PAY
确认支付
取消任务
```

说明：

- `SHOP AUTO_COMPARE` 会自动完成截图采集与比价，不需要你手工截图。
- `SHOP COLLECT` / `SHOP AUTO_COMPARE` 默认复用平台浏览器会话目录，减少重复登录。
- `SHOP SELECTED` 仅返回选中商品对应证据图片与价格信息。
- `SHOP INGEST` 可不写 `--files`，直接发送图片附件也会自动入库。
- `SHOP OCR_EXTRACT` 会读取截图旁的 sidecar（`*.txt` / `*.json`）做报价结构化。
- 可通过环境变量 `COMMERCE_SHOPPER_ROOT` 覆盖默认技能路径。
