# 每日选股推送工作流

自动化每日 A 股选股流程，从交易日历确认到飞书推送的完整流水线。

## 快速开始

### 1. 配置

编辑 `config.yaml`，设置：
- `feishu.channel_id`: 目标飞书群聊 ID
- `strategy.filters`: 选股筛选条件
- `schedule.time`: 执行时间

### 2. 手动运行

```bash
cd ~/.xyvaclaw/workspace/skills/workflow/examples/daily-stock-report
./run.sh --manual
```

### 3. 设置定时任务

在 OpenClaw 中创建 Cron：

```json
{
  "type": "systemEvent",
  "handler": "main",
  "command": "bash ~/.xyvaclaw/workspace/skills/workflow/examples/daily-stock-report/run.sh",
  "schedule": "09:00",
  "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
  "timezone": "Asia/Shanghai",
  "deleteAfterRun": true
}
```

## 目录结构

```
daily-stock-report/
├── flow.md            # 工作流定义文档
├── config.yaml        # 配置参数
├── run.sh            # 执行脚本
├── README.md         # 使用说明
└── output/           # 输出目录（自动生成）
    ├── reports/      # 选股报告
    └── logs/         # 执行日志
```

## 输出文件

### 选股报告
- 位置：`output/reports/daily_report_YYYYMMDD.md`
- 格式：Markdown
- 内容：选股列表、详细分析、风险提示

### 执行日志
- 位置：`output/logs/workflow_YYYYMMDD_HHMMSS.log`
- 格式：文本日志
- 内容：每个步骤的执行状态

### 结果 JSON
- 位置：`output/reports/workflow_result_YYYYMMDD_HHMMSS.json`
- 格式：JSON
- 内容：执行摘要、选股数量、发送状态

## 配置说明

### 选股策略

```yaml
strategy:
  filters:
    min_volume: 1000000      # 最小成交量（股）
    min_market_cap: 5000000000  # 最小市值（元）
    exclude_st: true         # 排除 ST 股票
    max_stocks: 20           # 最大选股数量
```

### 飞书推送

```yaml
feishu:
  enabled: true
  channel_id: "oc_XXXXXXXXXXXXXX"
  message_type: "markdown"
  mention_all: false
```

## 错误处理

### 非交易日
- 自动检测周末和节假日
- 记录日志并跳过
- 不发送告警

### API 失败
- 自动重试 3 次
- 指数退避（60s, 120s, 180s）
- 失败后发送告警消息

### 选股结果为空
- 记录日志
- 发送通知：「今日无符合选股条件的股票」

## 自定义

### 修改选股策略

编辑 `run.sh` 的步骤 2，调用实际的 `quant-strategy-engine`：

```bash
python3 $WORKSPACE_DIR/skills/quant-strategy-engine/run.py \
  --strategy technical \
  --output $OUTPUT_DIR/selected_stocks.json
```

### 修改报告模板

编辑 `run.sh` 的步骤 3，自定义 Markdown 模板。

### 添加新的输出格式

在步骤 3 后添加：

```bash
# 生成 Excel 版本
python3 $WORKSPACE_DIR/skills/excel-xlsx/generate.py \
  --input $OUTPUT_DIR/selected_stocks.json \
  --output $OUTPUT_DIR/daily_report.xlsx
```

## 故障排查

### 查看日志

```bash
tail -f output/logs/workflow_*.log
```

### 检查飞书配置

```bash
cat config/feishu_channel.json
```

### 测试选股策略

```bash
python3 skills/quant-strategy-engine/run.py --check
```

## 版本历史

- **1.0.0** (2026-03-08): 初始版本
  - 基础工作流框架
  - 交易日历检查
  - 选股报告生成
  - 飞书推送集成
