---
name: quant-strategy-engine
version: 1.0.0
description: |
  量化策略引擎。整合选股筛选、因子分析、回测验证、信号生成、风控管理的完整量化流水线。
  与 a-share-real-time-data 联动获取实时数据，与 deep-reasoning-chain 联动辅助策略推理，
  与 real-time-sentinel 联动实现交易信号监控。支持交易日识别、数据源降级、分层报告。
status: stable
platform: [darwin, linux]
dependencies:
  skills: [a-share-real-time-data, deep-reasoning-chain, real-time-sentinel, python-dataviz]
  bins: [python3]
  python: [pandas, numpy, mootdx, ta]
metadata:
  openclaw:
    emoji: "📈"
---

# Quant Strategy Engine 📈

从选股到信号生成的完整量化策略流水线。

## 核心流水线

```
股票池定义 → 数据采集 → 因子计算 → 策略筛选 → 回测验证 → 信号生成 → 风控检查 → 报告输出
```

---

## 模块详解

### 1. 股票池管理 (Universe)

```bash
# 定义股票池
python3 scripts/qse.py universe --create "AI概念" \
  --sectors "人工智能,半导体,云计算" \
  --exclude-st --exclude-new-days 60

# 从已有筛选器加载
python3 scripts/qse.py universe --from-screener "quant-stock-screener"

# 查看股票池
python3 scripts/qse.py universe --list
```

**内置股票池**:
- `all-a` — 全部 A 股（排除 ST、退市）
- `hs300` — 沪深 300 成分股
- `csi500` — 中证 500 成分股
- `cyb` — 创业板
- `kcb` — 科创板

### 2. 数据采集 (Data)

```bash
# 采集日线数据
python3 scripts/qse.py data --universe "AI概念" --freq daily --days 250

# 采集分钟数据
python3 scripts/qse.py data --universe "AI概念" --freq 1min --days 5

# 采集实时行情
python3 scripts/qse.py data --universe "AI概念" --realtime
```

**数据源降级策略**:
```
mootdx (主) → tushare (备) → akshare (兜底)
```
- 主数据源超时 10s 自动切换
- 每次降级记录日志告警
- 每日自动检测主数据源恢复

**交易日识别**:
- 自动跳过周末和法定节假日
- 支持自定义交易日历
- 非交易日任务自动延迟到下一个交易日

### 3. 因子引擎 (Factors)

```bash
# 计算内置因子
python3 scripts/qse.py factors --universe "AI概念" --factors "momentum,value,volatility,volume"

# 因子 IC 分析
python3 scripts/qse.py factors --ic-analysis --factor "momentum" --period 20
```

**内置因子库**:

| 分类 | 因子 | 说明 |
|------|------|------|
| 动量 | `momentum_20d` | 20 日收益率 |
| 动量 | `rsi_14` | 14 日 RSI |
| 动量 | `macd_signal` | MACD 金叉/死叉信号 |
| 价值 | `pe_ratio` | 市盈率 |
| 价值 | `pb_ratio` | 市净率 |
| 价值 | `dividend_yield` | 股息率 |
| 波动 | `volatility_20d` | 20 日波动率 |
| 波动 | `atr_14` | 14 日 ATR |
| 量能 | `volume_ratio` | 量比 |
| 量能 | `turnover_rate` | 换手率 |
| 资金 | `money_flow` | 主力资金净流入 |
| 技术 | `ma_cross` | 均线交叉 |
| 技术 | `bollinger_position` | 布林带位置 |
| 技术 | `kdj_signal` | KDJ 信号 |

**自定义因子**:

```python
# factors/custom_factor.py
def my_factor(df):
    """自定义因子：放量突破20日高点"""
    df['high_20d'] = df['high'].rolling(20).max()
    df['vol_avg_20d'] = df['vol'].rolling(20).mean()
    return (df['close'] > df['high_20d']) & (df['vol'] > df['vol_avg_20d'] * 2)
```

### 4. 策略模板 (Strategies)

```bash
# 使用内置策略
python3 scripts/qse.py strategy --name "momentum_breakout" --universe "AI概念"

# 组合策略
python3 scripts/qse.py strategy --combine "momentum_breakout+value_filter" --universe "AI概念"
```

**内置策略**:

| 策略 | 逻辑 | 适用 |
|------|------|------|
| `momentum_breakout` | 放量突破+RSI<70+MACD金叉 | 趋势行情 |
| `mean_reversion` | 超跌反弹+RSI<30+偏离MA20>-10% | 震荡行情 |
| `value_growth` | 低PE+高ROE+营收增长>20% | 长期持有 |
| `volume_price` | 量价齐升+均线多头排列 | 主升浪 |
| `sector_rotation` | 板块轮动+资金流向 | 板块操作 |

### 5. 回测引擎 (Backtest)

```bash
# 基础回测
python3 scripts/qse.py backtest --strategy "momentum_breakout" \
  --start 20250101 --end 20260301 --capital 1000000

# 参数优化
python3 scripts/qse.py backtest --strategy "momentum_breakout" \
  --optimize --param-grid "rsi_period:10,14,20;vol_mult:1.5,2,3"

# 分层报告
python3 scripts/qse.py backtest --strategy "momentum_breakout" --report detailed
```

**回测报告指标**:

| 指标 | 说明 |
|------|------|
| 年化收益率 | 策略年化回报 |
| 最大回撤 | 最大净值回撤 |
| 夏普比率 | 风险调整后收益 |
| 卡尔马比率 | 收益/最大回撤 |
| 胜率 | 盈利交易占比 |
| 盈亏比 | 平均盈利/平均亏损 |
| 基准对比 | vs 沪深300 |

**回测与模拟一致性审计**:
- 回测使用前复权数据
- 考虑涨跌停限制（不能买入涨停/卖出跌停）
- 考虑停牌日跳过
- 手续费：万3佣金 + 千1印花税（卖出）
- 滑点：默认 0.1%

### 6. 信号生成 (Signals)

```bash
# 生成今日信号
python3 scripts/qse.py signal --strategy "momentum_breakout" --universe "AI概念"

# 输出格式
python3 scripts/qse.py signal --format json  # json/csv/feishu
```

**信号输出格式**:

```json
{
  "date": "2026-03-05",
  "strategy": "momentum_breakout",
  "signals": [
    {
      "symbol": "300750.SZ",
      "name": "宁德时代",
      "action": "BUY",
      "price": 185.50,
      "strength": 0.85,
      "reasons": ["放量突破20日高点", "MACD金叉", "RSI=62"],
      "risk_level": "medium",
      "suggested_position": 0.1,
      "stop_loss": 176.23,
      "take_profit": 203.50
    }
  ]
}
```

### 7. 风控模块 (Risk)

```yaml
risk_rules:
  position:
    max_single: 0.1          # 单只最大仓位 10%
    max_sector: 0.3           # 单板块最大 30%
    max_total: 0.8            # 最大总仓位 80%
  stop_loss:
    single: -0.08             # 单只止损 -8%
    portfolio: -0.15           # 组合止损 -15%
    trailing: 0.1             # 移动止损 10%
  trading:
    max_daily_trades: 5       # 每日最多交易 5 次
    min_hold_days: 3          # 最少持有 3 天
    no_chase: true            # 不追涨停板
```

---

## 失败自动告警

与 `real-time-sentinel` 联动：

```yaml
alerts:
  data_fetch_fail:
    condition: "数据采集失败"
    action: "切换数据源 + 飞书告警"
  signal_anomaly:
    condition: "信号数量异常（>20 或 =0）"
    action: "暂停信号 + 人工确认"
  backtest_drift:
    condition: "回测与实盘偏差 >5%"
    action: "标红预警 + 策略审查"
```

---

## 分层报告

```bash
# 生成分层报告
python3 scripts/qse.py report --type layered

# 报告层次:
# L1 执行摘要 — 一句话结论 + 关键数字
# L2 策略概览 — 各策略表现 + 持仓变化 + 风险指标  
# L3 详细分析 — 每只股票的因子分析 + 交易记录 + 归因
# L4 数据附录 — 原始数据 + 参数配置 + 审计日志
```

---

## 与 quant-stock-screener 集成

```bash
# 先运行选股筛选（必须前置步骤）
python3 scripts/qse.py pipeline --screener-first \
  --strategy "momentum_breakout" \
  --report layered \
  --notify feishu
```

流水线: `quant-stock-screener(选股) → qse(因子+策略+回测+信号) → sentinel(监控) → messenger(通知)`

---

## 健康检查

```bash
python3 scripts/qse.py --check
# 检查: mootdx 连接
# 检查: 交易日历更新
# 检查: 策略配置有效
# 检查: 数据源可用性
```

---

## 注意事项

1. **非投资建议**: 量化信号仅供参考，投资决策需自行判断
2. **数据延迟**: 实时数据有 3-5 秒延迟，不适用于高频交易
3. **回测局限**: 历史表现不代表未来收益
4. **风控优先**: 任何时候风控规则优先于策略信号
5. **交易日**: 非交易日自动跳过所有操作

---

_版本: 1.0.0_  
_创建时间: 2026-03_
