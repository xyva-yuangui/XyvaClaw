# 量化选股系统 - 开发实施计划

## 📋 开发任务清单

### 阶段 1: 数据层（2 天）✅ 优先级最高

#### 1.1 数据获取模块
- [x] Tushare 配置（已完成）
- [ ] 数据获取类 `DataFetcher`
- [ ] 批量获取历史数据
- [ ] 增量更新机制
- [ ] 错误重试机制

#### 1.2 数据存储模块
- [ ] SQLite 数据库初始化
- [ ] 表结构创建（带索引）
- [ ] 批量插入优化
- [ ] 数据验证（去重、完整性）

#### 1.3 缓存层
- [ ] 内存缓存（热门数据）
- [ ] 缓存失效策略
- [ ] 缓存预热（开盘前）

---

### 阶段 2: 因子层（2 天）

#### 2.1 因子计算
- [ ] 估值因子（PE、PB、PS）
- [ ] 成长因子（营收增长、净利润增长）
- [ ] 动量因子（5 日/20 日/60 日涨幅）
- [ ] 质量因子（ROE、ROA、负债率）
- [ ] 技术因子（MACD、RSI）
- [ ] 资金因子（北向资金、主力流入）

#### 2.2 因子存储
- [ ] 因子得分表
- [ ] 因子 IC 值计算
- [ ] 因子相关性分析

---

### 阶段 3: 回测层（3 天）

#### 3.1 回测引擎
- [ ] 回测框架
- [ ] 交易模拟（买入/卖出）
- [ ] 手续费/滑点计算
- [ ] 持仓管理

#### 3.2 回测指标
- [ ] 年化收益
- [ ] 夏普比率
- [ ] 最大回撤
- [ ] 胜率/盈亏比

#### 3.3 权重优化
- [ ] 网格搜索
- [ ] 遗传算法（可选）
- [ ] 最优权重保存

---

### 阶段 4: 选股层（2 天）

#### 4.1 选股器
- [ ] 初筛（市值、成交、ST）
- [ ] 因子打分
- [ ] 排序选股
- [ ] 行业分散

#### 4.2 风险控制
- [ ] 止损位设置
- [ ] 仓位控制
- [ ] 行业限制

---

### 阶段 5: 优化层（1 天）

#### 5.1 性能优化
- [x] 索引优化（已规划）
- [ ] 查询优化
- [ ] 批量操作
- [ ] 连接池

#### 5.2 定期维护
- [ ] VACUUM 定时任务
- [ ] 数据清理（过期数据）
- [ ] 统计信息更新

---

### 阶段 6: 集成层（1 天）

#### 6.1 OpenClaw 集成
- [ ] 选股命令
- [ ] 结果推送（飞书）
- [ ] 定时任务（盘后选股）

#### 6.2 监控告警
- [ ] 数据更新监控
- [ ] 异常告警
- [ ] 性能监控

---

## 📅 时间安排

| 阶段 | 内容 | 天数 | 开始日期 |
|------|------|------|---------|
| 阶段 1 | 数据层 | 2 天 | 2026-03-09 |
| 阶段 2 | 因子层 | 2 天 | 2026-03-11 |
| 阶段 3 | 回测层 | 3 天 | 2026-03-13 |
| 阶段 4 | 选股层 | 2 天 | 2026-03-18 |
| 阶段 5 | 优化层 | 1 天 | 2026-03-20 |
| 阶段 6 | 集成层 | 1 天 | 2026-03-21 |

**总工期**: 11 天  
**预计完成**: 2026-03-21

---

## 🎯 第一阶段：数据层（立即开始）

### 任务 1.1: 创建数据获取模块
**文件**: `skills/quant-strategy-engine/scripts/data_fetcher.py`

**功能**:
- Tushare 数据获取
- mootdx 实时行情
- 批量获取
- 错误重试

**代码量**: ~300 行

### 任务 1.2: 创建数据存储模块
**文件**: `skills/quant-strategy-engine/scripts/data_storage.py`

**功能**:
- SQLite 数据库初始化
- 表结构创建（带索引）
- 批量插入
- 数据查询

**代码量**: ~400 行

### 任务 1.3: 创建缓存层
**文件**: `skills/quant-strategy-engine/scripts/cache_manager.py`

**功能**:
- 内存缓存（LRU）
- 缓存失效
- 缓存统计

**代码量**: ~150 行

### 任务 1.4: 数据初始化脚本
**文件**: `skills/quant-strategy-engine/scripts/init_data.py`

**功能**:
- 初始化数据库
- 导入历史数据
- 验证数据完整性

**代码量**: ~200 行

---

## 📊 优化方案实施

### 优化 1: 索引优化 ✅
```sql
-- 复合索引
CREATE INDEX idx_daily_code_date ON daily_data(ts_code, trade_date);
CREATE INDEX idx_daily_date_code ON daily_data(trade_date, ts_code);

-- 单列索引
CREATE INDEX idx_daily_code ON daily_data(ts_code);
CREATE INDEX idx_daily_date ON daily_data(trade_date);
```

### 优化 2: 批量操作 ✅
```python
# 批量插入（1000 条/批）
conn.executemany(sql, data_batch)

# 批量查询（使用 IN）
SELECT * FROM table WHERE ts_code IN (?, ?, ?)
```

### 优化 3: 缓存策略 ✅
```python
# 热门数据缓存
cache = {
    "daily:000001.SZ:20260309": {...},
    "factor:000001.SZ:20260309": {...},
}
# TTL: 交易日结束后失效
```

### 优化 4: 连接管理 ✅
```python
# 单例连接（避免频繁打开关闭）
class DatabaseManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.conn = sqlite3.connect(db_path)
        return cls._instance
```

### 优化 5: 定期维护 ⏰
```python
# Cron 任务（每月 1 号凌晨 3 点）
0 3 1 * * python3 ~/scripts/vacuum_db.py
```

---

## 🚀 立即开始

**现在开始实施阶段 1（数据层）**

预计完成时间：2 天（2026-03-11 前）

**交付物**:
1. ✅ `data_fetcher.py` - 数据获取
2. ✅ `data_storage.py` - 数据存储
3. ✅ `cache_manager.py` - 缓存管理
4. ✅ `init_data.py` - 数据初始化
5. ✅ 数据库文件（~/.openclaw/data/database/）

---

**圆规，我立即开始开发！预计 2 天内完成数据层，完成后向你汇报！** 🚀
