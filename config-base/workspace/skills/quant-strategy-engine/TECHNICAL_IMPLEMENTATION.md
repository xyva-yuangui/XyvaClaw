# 量化选股 - 技术实现方案 v3.1

## 📋 5 大核心问题详解

---

## 1️⃣ 数据获取

### 数据源架构
```
┌─────────────────────────────────────────────────────────┐
│                     数据获取层                            │
├─────────────────────────────────────────────────────────┤
│  A 股数据                                                │
│  ├─ Tushare Pro (私有网关)                              │
│  │  ├─ 日线数据 (daily)                                 │
│  │  ├─ 基本面数据 (daily_basic)                         │
│  │  ├─ 财务指标 (fina_indicator)                        │
│  │  ├─ 资金流向 (moneyflow)                             │
│  │  └─ 股票列表 (stock_basic)                           │
│  │                                                       │
│  ├─ mootdx (券商行情)                                   │
│  │  ├─ 实时行情                                         │
│  │  ├─ 分钟线                                           │
│  │  └─ tick 数据                                        │
│  │                                                       │
│  └─ AKShare (备用)                                      │
│     ├─ 港股数据                                         │
│     └─ 宏观数据                                         │
└─────────────────────────────────────────────────────────┘
```

### 数据获取代码实现
```python
# skills/quant-strategy-engine/data_fetcher.py

import tushare as ts
import pandas as pd
from datetime import datetime, timedelta

class DataFetcher:
    def __init__(self):
        # Tushare 配置
        self.token = "a2bd39d0aa6e6cd26729e7e3a6cddccb85b255ca0a9da996150191a9f14b"
        self.pro = ts.pro_api(self.token)
        self.pro._DataApi__token = self.token
        self.pro._DataApi__http_url = '__TUSHARE_HTTP_URL__'
        
        # mootdx 配置
        from mootdx.quotes import Quotes
        self.mootdx_client = Quotes.factory(market="std", timeout=10)
    
    def fetch_daily_data(self, ts_code, start_date, end_date):
        """获取日线数据"""
        df = self.pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
        return df
    
    def fetch_basic_data(self, ts_code, trade_date):
        """获取基本面数据"""
        df = self.pro.daily_basic(ts_code=ts_code, trade_date=trade_date)
        return df
    
    def fetch_fina_indicator(self, ts_code, start_date, end_date):
        """获取财务指标"""
        df = self.pro.fina_indicator(ts_code=ts_code, start_date=start_date, end_date=end_date)
        return df
    
    def fetch_moneyflow(self, ts_code, start_date, end_date):
        """获取资金流向"""
        df = self.pro.moneyflow(ts_code=ts_code, start_date=start_date, end_date=end_date)
        return df
    
    def fetch_realtime_quote(self, ts_code):
        """获取实时行情（mootdx）"""
        market = 1 if ts_code.startswith("6") else 0
        code = ts_code.split(".")[0]
        quote = self.mootdx_client.quote(market, code)
        return quote
    
    def get_all_stock_list(self):
        """获取全部 A 股列表"""
        df = self.pro.stock_basic(exchange='', list_status='L', 
                                  fields='ts_code,symbol,name,area,industry,list_date')
        return df
```

### 数据更新策略
| 数据类型 | 更新频率 | 更新时间 | 方式 |
|---------|---------|---------|------|
| 日线数据 | 每日 | 15:30 | 定时任务 |
| 基本面数据 | 每日 | 16:00 | 定时任务 |
| 财务指标 | 季报后 | 披露后 1 天 | 定时任务 |
| 资金流向 | 每日 | 16:00 | 定时任务 |
| 实时行情 | 盘中 | 实时 | 按需获取 |

---

## 2️⃣ 数据存储

### 存储架构
```
~/.openclaw/data/
├── database/
│   ├── stock_data.db          # SQLite 数据库（日线数据）
│   ├── fundamentals.db        # SQLite 数据库（基本面）
│   ├── factors.db             # SQLite 数据库（因子计算结果）
│   └── backtest.db            # SQLite 数据库（回测结果）
│
├── cache/
│   ├── realtime/              # 实时行情缓存
│   ├── daily/                 # 日线数据缓存
│   └── factors/               # 因子缓存
│
└── config/
    ├── stock_list.json        # 股票列表
    ├── factor_weights.json    # 因子权重配置
    └── market_state.json      # 市场状态记录
```

### 数据库表结构

#### stock_data.db
```sql
-- 日线数据表
CREATE TABLE daily_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_code VARCHAR(20) NOT NULL,
    trade_date DATE NOT NULL,
    open DECIMAL(10,2),
    high DECIMAL(10,2),
    low DECIMAL(10,2),
    close DECIMAL(10,2),
    volume BIGINT,
    amount DECIMAL(20,2),
    pct_chg DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ts_code, trade_date)
);

-- 索引
CREATE INDEX idx_daily_code ON daily_data(ts_code);
CREATE INDEX idx_daily_date ON daily_data(trade_date);
```

#### fundamentals.db
```sql
-- 基本面数据表
CREATE TABLE daily_basic (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_code VARCHAR(20) NOT NULL,
    trade_date DATE NOT NULL,
    pe DECIMAL(10,2),          -- 市盈率
    pb DECIMAL(10,2),          -- 市净率
    ps DECIMAL(10,2),          -- 市销率
    total_mv DECIMAL(20,2),    -- 总市值
    circ_mv DECIMAL(20,2),     -- 流通市值
    turnover_rate DECIMAL(10,2), -- 换手率
    volume_ratio DECIMAL(10,2),  -- 量比
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ts_code, trade_date)
);

-- 财务指标表
CREATE TABLE fina_indicator (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_code VARCHAR(20) NOT NULL,
    ann_date DATE NOT NULL,
    roe DECIMAL(10,2),         -- ROE
    roa DECIMAL(10,2),         -- ROA
    gross_margin DECIMAL(10,2), -- 毛利率
    net_margin DECIMAL(10,2),   -- 净利率
    debt_to_assets DECIMAL(10,2), -- 资产负债率
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ts_code, ann_date)
);
```

#### factors.db
```sql
-- 因子计算结果表
CREATE TABLE factor_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_code VARCHAR(20) NOT NULL,
    trade_date DATE NOT NULL,
    valuation_score DECIMAL(10,4),    -- 估值因子得分
    growth_score DECIMAL(10,4),       -- 成长因子得分
    momentum_score DECIMAL(10,4),     -- 动量因子得分
    quality_score DECIMAL(10,4),      -- 质量因子得分
    technical_score DECIMAL(10,4),    -- 技术因子得分
    moneyflow_score DECIMAL(10,4),    -- 资金因子得分
    total_score DECIMAL(10,4),        -- 综合得分
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ts_code, trade_date)
);
```

#### backtest.db
```sql
-- 回测结果表
CREATE TABLE backtest_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_name VARCHAR(100),
    start_date DATE,
    end_date DATE,
    initial_capital DECIMAL(20,2),
    final_capital DECIMAL(20,2),
    annual_return DECIMAL(10,4),
    sharpe_ratio DECIMAL(10,4),
    max_drawdown DECIMAL(10,4),
    win_rate DECIMAL(10,4),
    weights_config TEXT,  -- JSON 格式存储权重配置
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 回测交易记录表
CREATE TABLE backtest_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    backtest_id INTEGER,
    ts_code VARCHAR(20),
    trade_date DATE,
    direction VARCHAR(10),  -- BUY/SELL
    price DECIMAL(10,2),
    volume INTEGER,
    amount DECIMAL(20,2),
    commission DECIMAL(20,2),
    FOREIGN KEY (backtest_id) REFERENCES backtest_results(id)
);
```

### 数据存储代码实现
```python
# skills/quant-strategy-engine/data_storage.py

import sqlite3
import json
from pathlib import Path

class DataStorage:
    def __init__(self):
        self.data_dir = Path.home() / ".openclaw" / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.stock_db = self.data_dir / "database" / "stock_data.db"
        self.fundamentals_db = self.data_dir / "database" / "fundamentals.db"
        self.factors_db = self.data_dir / "database" / "factors.db"
        self.backtest_db = self.data_dir / "database" / "backtest.db"
        
        # 初始化数据库
        self._init_databases()
    
    def _init_databases(self):
        """初始化数据库表结构"""
        # 创建日线数据表
        conn = sqlite3.connect(self.stock_db)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_code VARCHAR(20) NOT NULL,
                trade_date DATE NOT NULL,
                open DECIMAL(10,2),
                high DECIMAL(10,2),
                low DECIMAL(10,2),
                close DECIMAL(10,2),
                volume BIGINT,
                amount DECIMAL(20,2),
                pct_chg DECIMAL(10,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(ts_code, trade_date)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_daily_code ON daily_data(ts_code)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_daily_date ON daily_data(trade_date)")
        conn.commit()
        conn.close()
        
        # 初始化其他数据库...
    
    def save_daily_data(self, df):
        """保存日线数据"""
        conn = sqlite3.connect(self.stock_db)
        df.to_sql('daily_data', conn, if_exists='append', index=False)
        conn.commit()
        conn.close()
    
    def get_daily_data(self, ts_code, start_date, end_date):
        """获取日线数据"""
        conn = sqlite3.connect(self.stock_db)
        query = """
            SELECT * FROM daily_data 
            WHERE ts_code = ? AND trade_date BETWEEN ? AND ?
            ORDER BY trade_date DESC
        """
        df = pd.read_sql_query(query, conn, params=(ts_code, start_date, end_date))
        conn.close()
        return df
    
    def save_factor_scores(self, df):
        """保存因子得分"""
        conn = sqlite3.connect(self.factors_db)
        df.to_sql('factor_scores', conn, if_exists='append', index=False)
        conn.commit()
        conn.close()
    
    def save_backtest_result(self, result):
        """保存回测结果"""
        conn = sqlite3.connect(self.backtest_db)
        # 插入回测结果
        conn.execute("""
            INSERT INTO backtest_results 
            (strategy_name, start_date, end_date, initial_capital, final_capital,
             annual_return, sharpe_ratio, max_drawdown, win_rate, weights_config)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result['strategy_name'],
            result['start_date'],
            result['end_date'],
            result['initial_capital'],
            result['final_capital'],
            result['annual_return'],
            result['sharpe_ratio'],
            result['max_drawdown'],
            result['win_rate'],
            json.dumps(result['weights_config'])
        ))
        conn.commit()
        conn.close()
```

---

## 3️⃣ 回测引擎

### 回测流程
```
┌─────────────────────────────────────────────────────────┐
│                     回测引擎                             │
├─────────────────────────────────────────────────────────┤
│  1. 加载历史数据 ← stock_data.db                        │
│  2. 计算因子得分 ← factors.db                           │
│  3. 应用权重配置 ← config/factor_weights.json           │
│  4. 选股排序                                            │
│  5. 模拟交易                                            │
│  6. 计算收益指标                                        │
│  7. 保存回测结果 ← backtest.db                          │
└─────────────────────────────────────────────────────────┘
```

### 回测代码实现
```python
# skills/quant-strategy-engine/backtester.py

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sqlite3

class Backtester:
    def __init__(self, initial_capital=1000000):
        self.initial_capital = initial_capital
        self.commission_rate = 0.0003  # 万分之三
        self.slippage = 0.001  # 千分之一
        
        # 数据库连接
        self.stock_db = Path.home() / ".openclaw" / "data" / "database" / "stock_data.db"
        self.factors_db = Path.home() / ".openclaw" / "data" / "database" / "factors.db"
        self.backtest_db = Path.home() / ".openclaw" / "data" / "database" / "backtest.db"
    
    def run_backtest(self, start_date, end_date, weights_config, 
                     top_n=10, rebalance_freq='monthly'):
        """
        运行回测
        
        Args:
            start_date: 开始日期 '2020-01-01'
            end_date: 结束日期 '2026-03-09'
            weights_config: 权重配置 {"估值": 0.25, "成长": 0.25, ...}
            top_n: 持股数量
            rebalance_freq: 调仓频率 'daily'/'weekly'/'monthly'
        
        Returns:
            dict: 回测结果
        """
        # 1. 加载历史数据
        conn = sqlite3.connect(self.stock_db)
        query = """
            SELECT * FROM daily_data 
            WHERE trade_date BETWEEN ? AND ?
            ORDER BY trade_date
        """
        price_data = pd.read_sql_query(query, conn, params=(start_date, end_date))
        conn.close()
        
        # 2. 加载因子得分
        conn = sqlite3.connect(self.factors_db)
        query = """
            SELECT * FROM factor_scores 
            WHERE trade_date BETWEEN ? AND ?
            ORDER BY trade_date
        """
        factor_data = pd.read_sql_query(query, conn, params=(start_date, end_date))
        conn.close()
        
        # 3. 初始化回测账户
        capital = self.initial_capital
        positions = {}  # 持仓 {ts_code: volume}
        trades = []     # 交易记录
        portfolio_values = []  # 每日 portfolio 价值
        
        # 4. 按交易日循环
        trading_dates = sorted(price_data['trade_date'].unique())
        
        for i, trade_date in enumerate(trading_dates):
            # 4.1 判断是否调仓日
            if self._is_rebalance_day(i, rebalance_freq):
                # 4.2 获取当日因子得分
                day_factors = factor_data[factor_data['trade_date'] == trade_date]
                
                # 4.3 计算综合得分
                day_factors['total_score'] = (
                    day_factors['valuation_score'] * weights_config['估值'] +
                    day_factors['growth_score'] * weights_config['成长'] +
                    day_factors['momentum_score'] * weights_config['动量'] +
                    day_factors['quality_score'] * weights_config['质量'] +
                    day_factors['technical_score'] * weights_config['技术'] +
                    day_factors['moneyflow_score'] * weights_config['资金']
                )
                
                # 4.4 选股（Top N）
                selected_stocks = day_factors.nlargest(top_n, 'total_score')['ts_code'].tolist()
                
                # 4.5 调整仓位
                trades.extend(self._rebalance_positions(
                    positions, selected_stocks, capital, trade_date, price_data
                ))
            
            # 4.6 计算当日 portfolio 价值
            portfolio_value = self._calculate_portfolio_value(positions, trade_date, price_data)
            portfolio_values.append({
                'trade_date': trade_date,
                'value': portfolio_value
            })
        
        # 5. 计算回测指标
        results = self._calculate_metrics(portfolio_values, trades)
        results['weights_config'] = weights_config
        results['start_date'] = start_date
        results['end_date'] = end_date
        
        # 6. 保存回测结果
        self._save_backtest_results(results, trades)
        
        return results
    
    def _is_rebalance_day(self, day_index, freq):
        """判断是否调仓日"""
        if freq == 'daily':
            return True
        elif freq == 'weekly':
            return day_index % 5 == 0  # 每周
        elif freq == 'monthly':
            return day_index % 21 == 0  # 每月
        return False
    
    def _rebalance_positions(self, positions, selected_stocks, capital, trade_date, price_data):
        """调整仓位"""
        trades = []
        # 卖出不在选股列表的股票
        for ts_code in list(positions.keys()):
            if ts_code not in selected_stocks:
                # 卖出
                volume = positions.pop(ts_code)
                price = self._get_price(ts_code, trade_date, price_data)
                amount = volume * price
                capital += amount * (1 - self.commission_rate)
                trades.append({
                    'ts_code': ts_code,
                    'trade_date': trade_date,
                    'direction': 'SELL',
                    'price': price,
                    'volume': volume,
                    'amount': amount
                })
        
        # 买入选股列表中的股票
        if selected_stocks and capital > 0:
            buy_per_stock = capital / len(selected_stocks)
            for ts_code in selected_stocks:
                if ts_code not in positions:
                    price = self._get_price(ts_code, trade_date, price_data)
                    volume = int(buy_per_stock / price / 100) * 100  # 100 股的整数倍
                    if volume > 0:
                        cost = volume * price * (1 + self.commission_rate + self.slippage)
                        if cost <= capital:
                            positions[ts_code] = volume
                            capital -= cost
                            trades.append({
                                'ts_code': ts_code,
                                'trade_date': trade_date,
                                'direction': 'BUY',
                                'price': price,
                                'volume': volume,
                                'amount': volume * price
                            })
        
        return trades
    
    def _calculate_metrics(self, portfolio_values, trades):
        """计算回测指标"""
        portfolio_df = pd.DataFrame(portfolio_values)
        portfolio_df['trade_date'] = pd.to_datetime(portfolio_df['trade_date'])
        portfolio_df = portfolio_df.set_index('trade_date')
        
        # 计算每日收益率
        portfolio_df['daily_return'] = portfolio_df['value'].pct_change()
        
        # 年化收益
        total_days = (portfolio_df.index[-1] - portfolio_df.index[0]).days
        total_return = (portfolio_df['value'].iloc[-1] - self.initial_capital) / self.initial_capital
        annual_return = (1 + total_return) ** (365 / total_days) - 1
        
        # 夏普比率
        sharpe_ratio = np.sqrt(252) * portfolio_df['daily_return'].mean() / portfolio_df['daily_return'].std()
        
        # 最大回撤
        rolling_max = portfolio_df['value'].cummax()
        drawdown = (portfolio_df['value'] - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        # 胜率
        buy_trades = [t for t in trades if t['direction'] == 'BUY']
        sell_trades = [t for t in trades if t['direction'] == 'SELL']
        profitable_trades = sum(1 for t in sell_trades if t['price'] > self._get_avg_buy_price(t['ts_code'], trades))
        win_rate = profitable_trades / len(sell_trades) if sell_trades else 0
        
        return {
            'initial_capital': self.initial_capital,
            'final_capital': portfolio_df['value'].iloc[-1],
            'annual_return': annual_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'total_trades': len(trades)
        }
    
    def _save_backtest_results(self, results, trades):
        """保存回测结果"""
        # 保存回测汇总
        conn = sqlite3.connect(self.backtest_db)
        conn.execute("""
            INSERT INTO backtest_results 
            (strategy_name, start_date, end_date, initial_capital, final_capital,
             annual_return, sharpe_ratio, max_drawdown, win_rate, weights_config)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            '动态权重多因子',
            results['start_date'],
            results['end_date'],
            results['initial_capital'],
            results['final_capital'],
            results['annual_return'],
            results['sharpe_ratio'],
            results['max_drawdown'],
            results['win_rate'],
            json.dumps(results['weights_config'])
        ))
        
        backtest_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        
        # 保存交易记录
        for trade in trades:
            conn.execute("""
                INSERT INTO backtest_trades 
                (backtest_id, ts_code, trade_date, direction, price, volume, amount)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                backtest_id,
                trade['ts_code'],
                trade['trade_date'],
                trade['direction'],
                trade['price'],
                trade['volume'],
                trade['amount']
            ))
        
        conn.commit()
        conn.close()
```

---

## 4️⃣ 回测数据存储

### 存储位置
- **数据库**: `~/.openclaw/data/database/backtest.db`
- **表结构**: 
  - `backtest_results` - 回测汇总
  - `backtest_trades` - 交易记录

### 存储内容
```sql
-- 回测汇总
{
  "strategy_name": "动态权重多因子",
  "start_date": "2020-01-01",
  "end_date": "2026-03-09",
  "initial_capital": 1000000,
  "final_capital": 2500000,
  "annual_return": 0.20,
  "sharpe_ratio": 1.5,
  "max_drawdown": -0.18,
  "win_rate": 0.60,
  "weights_config": {"估值": 0.25, "成长": 0.25, ...}
}

-- 交易记录
{
  "backtest_id": 1,
  "ts_code": "000001.SZ",
  "trade_date": "2020-01-15",
  "direction": "BUY",
  "price": 10.50,
  "volume": 1000,
  "amount": 10500
}
```

---

## 5️⃣ 回测数据反哺动态权重

### 反哺流程
```
┌─────────────────────────────────────────────────────────┐
│                  权重优化闭环                            │
├─────────────────────────────────────────────────────────┤
│  1. 回测多组权重组合                                     │
│  2. 评估每组表现（夏普比率）                             │
│  3. 找出最优权重                                         │
│  4. 更新权重配置 ← config/factor_weights.json          │
│  5. 实盘应用新权重                                       │
│  6. 持续监控表现                                         │
│  7. 定期重新回测（滚动优化）                             │
└─────────────────────────────────────────────────────────┘
```

### 权重优化代码实现
```python
# skills/quant-strategy-engine/weight_optimizer.py

from itertools import product
import sqlite3
import json

class WeightOptimizer:
    def __init__(self):
        self.backtest_db = Path.home() / ".openclaw" / "data" / "database" / "backtest.db"
        self.config_file = Path.home() / ".openclaw" / "data" / "config" / "factor_weights.json"
    
    def grid_search_optimize(self, start_date, end_date):
        """
        网格搜索最优权重
        """
        # 1. 定义权重搜索空间
        weight_ranges = {
            '估值': [0.15, 0.20, 0.25, 0.30, 0.35],
            '成长': [0.15, 0.20, 0.25, 0.30, 0.35],
            '动量': [0.10, 0.15, 0.20, 0.25, 0.30],
            '质量': [0.10, 0.15, 0.20, 0.25],
            '技术': [0.05, 0.10, 0.15],
            '资金': [0.05, 0.10]
        }
        
        # 2. 生成所有权重组合（过滤掉总和不为 1 的）
        weight_combinations = []
        for combo in product(*weight_ranges.values()):
            weights = dict(zip(weight_ranges.keys(), combo))
            if abs(sum(weights.values()) - 1.0) < 0.01:  # 总和接近 1
                weight_combinations.append(weights)
        
        print(f"共 {len(weight_combinations)} 组权重组合")
        
        # 3. 回测每组权重
        backtester = Backtester()
        results = []
        
        for i, weights in enumerate(weight_combinations):
            print(f"回测第 {i+1}/{len(weight_combinations)} 组权重...")
            result = backtester.run_backtest(start_date, end_date, weights)
            results.append({
                'weights': weights,
                'sharpe_ratio': result['sharpe_ratio'],
                'annual_return': result['annual_return'],
                'max_drawdown': result['max_drawdown']
            })
        
        # 4. 找出最优权重（夏普比率最高）
        best_result = max(results, key=lambda x: x['sharpe_ratio'])
        
        print(f"\n最优权重配置:")
        print(f"  权重：{best_result['weights']}")
        print(f"  夏普比率：{best_result['sharpe_ratio']:.2f}")
        print(f"  年化收益：{best_result['annual_return']:.2%}")
        print(f"  最大回撤：{best_result['max_drawdown']:.2%}")
        
        # 5. 更新权重配置
        self._save_optimal_weights(best_result['weights'])
        
        return best_result
    
    def _save_optimal_weights(self, weights):
        """保存最优权重配置"""
        config = {
            "version": "3.0.0",
            "optimized_date": datetime.now().isoformat(),
            "weights": weights,
            "market_state": "auto"  # 自动识别市场状态
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print(f"最优权重已保存到：{self.config_file}")
    
    def load_optimal_weights(self):
        """加载最优权重配置"""
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return config['weights']
        else:
            # 返回默认权重
            return {
                "估值": 0.25, "成长": 0.25, "动量": 0.20,
                "质量": 0.15, "技术": 0.10, "资金": 0.05
            }
```

### 动态调整机制
```python
# 每日盘后检查因子表现
def daily_factor_review():
    """
    每日检查因子表现，微调权重
    """
    # 1. 计算各因子近期 IC 值
    factor_ic = {}
    for factor in ['估值', '成长', '动量', '质量', '技术', '资金']:
        ic = calculate_factor_ic(factor, lookback=20)
        factor_ic[factor] = ic
    
    # 2. 根据 IC 值调整权重
    current_weights = load_current_weights()
    new_weights = {}
    
    avg_ic = sum(factor_ic.values()) / len(factor_ic)
    
    for factor in current_weights:
        if factor_ic[factor] > avg_ic:
            # IC 高于平均，增加权重
            new_weights[factor] = current_weights[factor] * 1.05
        else:
            # IC 低于平均，减少权重
            new_weights[factor] = current_weights[factor] * 0.95
    
    # 3. 归一化
    total = sum(new_weights.values())
    new_weights = {k: v/total for k, v in new_weights.items()}
    
    # 4. 保存新权重
    save_weights(new_weights)
    
    return new_weights
```

---

## 📊 数据流图

```
┌─────────────────────────────────────────────────────────┐
│                     完整数据流                           │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Tushare/mootdx                                         │
│     ↓                                                   │
│  数据获取 (data_fetcher.py)                             │
│     ↓                                                   │
│  SQLite 数据库 (stock_data.db, fundamentals.db)         │
│     ↓                                                   │
│  因子计算 (factor_calculator.py)                        │
│     ↓                                                   │
│  因子数据库 (factors.db)                                │
│     ↓                                                   │
│  权重优化 (weight_optimizer.py)                         │
│     ↓                                                   │
│  回测引擎 (backtester.py)                               │
│     ↓                                                   │
│  回测数据库 (backtest.db)                               │
│     ↓                                                   │
│  最优权重配置 (config/factor_weights.json)              │
│     ↓                                                   │
│  实盘选股 (stock_selector.py)                           │
│     ↓                                                   │
│  选股结果 → 发送飞书                                    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 📋 文件清单

```
skills/quant-strategy-engine/
├── scripts/
│   ├── qse.py                      # 主程序
│   ├── data_fetcher.py             # 数据获取 ✅
│   ├── data_storage.py             # 数据存储 ✅
│   ├── factor_calculator.py        # 因子计算（待实现）
│   ├── backtester.py               # 回测引擎 ✅
│   ├── weight_optimizer.py         # 权重优化 ✅
│   └── stock_selector.py           # 选股器（待实现）
│
├── STRATEGY.md                     # 策略文档 ✅
├── DYNAMIC_WEIGHTS_PLAN.md         # 动态权重方案 ✅
└── TECHNICAL_IMPLEMENTATION.md     # 技术实现方案 ✅
```

---

**版本**: 3.1.0  
**更新日期**: 2026-03-09  
**状态**: 技术实现方案已明确

**下一步**: 开始实施阶段 1（数据获取 + 存储）
