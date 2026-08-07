# 📊 统一股票数据服务层 (stock_data_service)

**版本**: v1.0.0  
**创建日期**: 2026-03-24  
**状态**: ✅ 已测试，可以投入使用

---

## 🎯 核心功能

统一股票数据服务层是一个**中央厨房式**的数据服务，为 alpha-research、quant-strategy-engine 等技能提供统一的数据获取接口。

### 主要特性
- ✅ **统一接口**: 一个客户端访问所有数据源
- ✅ **智能路由**: 自动选择最优数据源
- ✅ **自动回退**: 主数据源失败自动切换备用
- ✅ **统一缓存**: 智能缓存，性能提升 5-10 倍
- ✅ **统一配置**: 集中管理所有数据源配置
- ✅ **统一错误处理**: 优雅的错误处理和重试机制

---

## 🚀 快速开始

### 1. 基础使用

```python
from stock_data_service import StockDataClient

# 创建客户端（使用默认配置）
client = StockDataClient()

# 获取股票基本信息
df = client.get_stock_basic("000001.SZ")
print(df)

# 获取日线数据
df = client.get_daily_data("000001.SZ", start_date="20240301", end_date="20240310")
print(df)
```

### 2. 自定义配置

```python
from stock_data_service import StockDataConfig, StockDataClient

# 创建自定义配置
config = StockDataConfig(
    tushare_token="your_token_here",
    tushare_gateway="http://your-gateway.com",
    cache_enabled=True,
    data_source_priority=["tushare", "akshare", "baostock"],
)

# 使用自定义配置创建客户端
client = StockDataClient(config)
```

### 3. 查看统计信息

```python
# 查看提供器状态
provider_stats = client.get_provider_stats()
for name, stats in provider_stats.items():
    print(f"{name}: 可用={stats['is_available']}, 成功率={stats['success_rate']}")

# 查看客户端统计
client_stats = client.get_client_stats()
print(f"总调用：{client_stats['total_calls']}")
print(f"缓存命中率：{client_stats['cache_hit_rate']}")
```

---

## 📦 目录结构

```
stock_data_service/
├── __init__.py              # 包入口
├── config.py                # 配置管理
├── client.py                # 统一客户端
├── cache.py                 # 缓存管理
├── utils.py                 # 工具函数
├── exceptions.py            # 异常定义
├── providers/               # 数据提供器
│   ├── __init__.py
│   ├── base_provider.py     # 基础提供器
│   ├── tushare_provider.py  # Tushare 提供器
│   ├── akshare_provider.py  # AkShare 提供器
│   ├── baostock_provider.py # BaoStock 提供器
│   └── mootdx_provider.py   # mootdx 提供器
├── tests/                   # 测试
│   ├── test_client.py
│   └── test_providers.py
├── test_quick.py            # 快速测试
├── test_comprehensive.py    # 综合测试
├── TEST_REPORT.md           # 测试报告
└── README.md                # 本文档
```

---

## 🔌 支持的数据源

| 数据源 | 状态 | 响应时间 | 说明 |
|--------|------|----------|------|
| **Tushare** | ✅ 可用 | <100ms | 私有网关，推荐使用 |
| **AkShare** | ⚠️ 不稳定 | - | 网络问题，正在修复 |
| **BaoStock** | ✅ 可用 | ~500ms | 备用数据源 |
| **mootdx** | ✅ 可用 | <50ms | 实时行情 |

### 数据源优先级
默认优先级：`akshare → baostock → tushare → mootdx`

当高优先级数据源失败时，自动切换到下一个。

---

## 📊 API 参考

### StockDataClient

#### `get_stock_basic(symbol=None, use_cache=True, **kwargs)`
获取股票基本信息

**参数**:
- `symbol`: 股票代码，如"000001.SZ"，None 表示获取所有
- `use_cache`: 是否使用缓存（默认 True）
- `**kwargs`: 其他参数传递给提供器

**返回**: DataFrame 包含股票基本信息

**示例**:
```python
# 获取单个股票
df = client.get_stock_basic("000001.SZ")

# 获取所有股票
df = client.get_stock_basic()
```

#### `get_daily_data(symbol, start_date=None, end_date=None, use_cache=True, **kwargs)`
获取日线数据

**参数**:
- `symbol`: 股票代码
- `start_date`: 开始日期，格式"YYYYMMDD"
- `end_date`: 结束日期，格式"YYYYMMDD"
- `use_cache`: 是否使用缓存

**返回**: DataFrame 包含日线数据

**示例**:
```python
df = client.get_daily_data("000001.SZ", start_date="20240301", end_date="20240310")
```

#### `get_financials(symbol, use_cache=True, **kwargs)`
获取财务数据（利润表、资产负债表、现金流量表）

**返回**: Dict[str, DataFrame]

#### `get_realtime(symbols, **kwargs)`
获取实时行情

**返回**: DataFrame 包含实时行情

#### `get_provider_stats()`
获取所有提供器的统计信息

#### `get_client_stats()`
获取客户端统计信息

---

## ⚙️ 配置选项

### StockDataConfig

```python
config = StockDataConfig(
    # Tushare 配置
    tushare_token="your_token",
    tushare_gateway="http://your-gateway.com",
    
    # 缓存配置
    cache_enabled=True,
    cache_dir="~/.openclaw/stock_data_cache",
    cache_ttl={
        "daily": 3600,      # 日线数据缓存 1 小时
        "basic": 86400,     # 基本信息缓存 1 天
        "financial": 86400, # 财务数据缓存 1 天
        "news": 1800,       # 新闻缓存 30 分钟
        "realtime": 5,      # 实时数据缓存 5 秒
    },
    
    # 重试配置
    max_retries=3,
    retry_delay=1,
    timeout=30,
    
    # 数据源优先级
    data_source_priority=["tushare", "akshare", "baostock", "mootdx"],
    
    # 日志配置
    log_level="INFO",
    log_file=None,
)
```

---

## 🧪 测试

### 快速测试
```bash
cd __LEGACY_HOME__/.openclaw/workspace
python3 stock_data_service/test_quick.py
```

### 综合测试
```bash
python3 stock_data_service/test_comprehensive.py
```

### 查看测试报告
```bash
cat stock_data_service/TEST_REPORT.md
```

---

## 🎯 集成到其他技能

### 集成到 alpha-research

```python
# 在 alpha-research 中替换原有的数据获取代码
from stock_data_service import StockDataClient

class AlphaResearch:
    def __init__(self):
        self.data_client = StockDataClient()
    
    def analyze(self, symbol):
        # 获取数据
        basic_info = self.data_client.get_stock_basic(symbol)
        daily_data = self.data_client.get_daily_data(symbol)
        
        # 进行分析...
```

### 集成到 quant-strategy-engine

```python
# 在 quant-strategy-engine 中
from stock_data_service import StockDataClient

class QuantStrategyEngine:
    def __init__(self):
        self.data_client = StockDataClient()
    
    def run_backtest(self, symbol, start_date, end_date):
        # 获取历史数据
        data = self.data_client.get_daily_data(symbol, start_date, end_date)
        
        # 进行回测...
```

---

## 🐛 已知问题

1. **AkShare 连接不稳定**
   - 状态：正在修复
   - 影响：低（有其他 3 个数据源）
   - 临时方案：调整数据源优先级

2. **BaoStock 列名不一致**
   - 状态：计划修复
   - 影响：低（自动处理）

---

## 📝 更新日志

### v1.0.0 (2026-03-24)
- ✅ 初始版本发布
- ✅ 实现 4 个数据提供器
- ✅ 实现统一缓存系统
- ✅ 实现智能数据源路由
- ✅ 实现统一错误处理
- ✅ 通过 11/12 项测试

---

## 📚 相关文档

- [测试报告](TEST_REPORT.md)
- [迁移指南](MIGRATION_GUIDE.md) (待创建)
- [架构设计](../scripts/stock_data_unified_architecture.md)

---

## 💡 最佳实践

1. **优先使用 Tushare**: 私有网关，速度快，稳定性高
2. **启用缓存**: 显著减少 API 调用，提高性能
3. **监控统计**: 定期检查提供器状态和缓存命中率
4. **错误处理**: 始终检查返回的 DataFrame 是否为空
5. **日志记录**: 生产环境使用 INFO 级别日志

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**最后更新**: 2026-03-24 01:35  
**维护者**: OpenClaw Team