#!/usr/bin/env python3
"""
数据存储模块 - Data Storage
SQLite 数据库存储，带索引优化和批量操作
"""

import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
import json

class DataStorage:
    """数据存储管理器"""
    
    def __init__(self):
        # 数据库目录
        self.data_dir = Path.home() / ".openclaw" / "data" / "database"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 数据库文件
        self.stock_db = self.data_dir / "stock_data.db"
        self.fundamentals_db = self.data_dir / "fundamentals.db"
        self.factors_db = self.data_dir / "factors.db"
        self.backtest_db = self.data_dir / "backtest.db"
        
        # 初始化数据库
        self._init_databases()
        
        print("✅ 数据存储初始化完成")
        print(f"   数据库目录：{self.data_dir}")
    
    def _init_databases(self):
        """初始化所有数据库"""
        self._init_stock_db()
        self._init_fundamentals_db()
        self._init_factors_db()
        self._init_backtest_db()
    
    def _init_stock_db(self):
        """初始化股票数据库"""
        conn = sqlite3.connect(str(self.stock_db))
        
        # 日线数据表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_code VARCHAR(20) NOT NULL,
                trade_date DATE NOT NULL,
                open DECIMAL(10,2),
                high DECIMAL(10,2),
                low DECIMAL(10,2),
                close DECIMAL(10,2),
                pre_close DECIMAL(10,2),
                change DECIMAL(10,2),
                pct_chg DECIMAL(10,2),
                volume BIGINT,
                amount DECIMAL(20,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(ts_code, trade_date)
            )
        """)
        
        # 索引优化
        conn.execute("CREATE INDEX IF NOT EXISTS idx_daily_code ON daily_data(ts_code)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_daily_date ON daily_data(trade_date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_daily_code_date ON daily_data(ts_code, trade_date)")
        
        conn.commit()
        conn.close()
        print("✅ stock_data.db 初始化完成")
    
    def _init_fundamentals_db(self):
        """初始化基本面数据库"""
        conn = sqlite3.connect(str(self.fundamentals_db))
        
        # 基本面数据表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_basic (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_code VARCHAR(20) NOT NULL,
                trade_date DATE NOT NULL,
                pe DECIMAL(10,2),
                pb DECIMAL(10,2),
                ps DECIMAL(10,2),
                total_mv DECIMAL(20,2),
                circ_mv DECIMAL(20,2),
                turnover_rate DECIMAL(10,2),
                volume_ratio DECIMAL(10,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(ts_code, trade_date)
            )
        """)
        
        # 财务指标表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS fina_indicator (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_code VARCHAR(20) NOT NULL,
                ann_date DATE NOT NULL,
                roe DECIMAL(10,2),
                roa DECIMAL(10,2),
                gross_margin DECIMAL(10,2),
                net_margin DECIMAL(10,2),
                debt_to_assets DECIMAL(10,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(ts_code, ann_date)
            )
        """)
        
        # 索引
        conn.execute("CREATE INDEX IF NOT EXISTS idx_basic_code ON daily_basic(ts_code)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fina_code ON fina_indicator(ts_code)")
        
        conn.commit()
        conn.close()
        print("✅ fundamentals.db 初始化完成")
    
    def _init_factors_db(self):
        """初始化因子数据库"""
        conn = sqlite3.connect(str(self.factors_db))
        
        # 因子得分表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS factor_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_code VARCHAR(20) NOT NULL,
                trade_date DATE NOT NULL,
                valuation_score DECIMAL(10,4),
                growth_score DECIMAL(10,4),
                momentum_score DECIMAL(10,4),
                quality_score DECIMAL(10,4),
                technical_score DECIMAL(10,4),
                moneyflow_score DECIMAL(10,4),
                total_score DECIMAL(10,4),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(ts_code, trade_date)
            )
        """)
        
        # 索引
        conn.execute("CREATE INDEX IF NOT EXISTS idx_factor_code ON factor_scores(ts_code)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_factor_date ON factor_scores(trade_date)")
        
        conn.commit()
        conn.close()
        print("✅ factors.db 初始化完成")
    
    def _init_backtest_db(self):
        """初始化回测数据库"""
        conn = sqlite3.connect(str(self.backtest_db))
        
        # 回测结果表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS backtest_results (
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
                weights_config TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 交易记录表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS backtest_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                backtest_id INTEGER,
                ts_code VARCHAR(20),
                trade_date DATE,
                direction VARCHAR(10),
                price DECIMAL(10,2),
                volume INTEGER,
                amount DECIMAL(20,2),
                FOREIGN KEY (backtest_id) REFERENCES backtest_results(id)
            )
        """)
        
        conn.commit()
        conn.close()
        print("✅ backtest.db 初始化完成")
    
    def save_daily_data(self, df):
        """
        保存日线数据（批量插入）
        
        Args:
            df: DataFrame (ts_code, trade_date, open, high, low, close, volume, amount, pct_chg)
        """
        if df is None or len(df) == 0:
            print("⚠️  无数据可保存")
            return
        
        conn = sqlite3.connect(str(self.stock_db))
        
        try:
            # 只保存需要的列
            columns = ['ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'pre_close', 'change', 'pct_chg', 'volume', 'amount']
            df_filtered = df.copy()
            
            # 确保所有列都存在
            for col in columns:
                if col not in df_filtered.columns:
                    df_filtered[col] = None
            
            # 选择需要的列
            df_filtered = df_filtered[columns]
            
            # 批量插入（忽略重复）
            df_filtered.to_sql('daily_data', conn, if_exists='append', index=False, method='multi')
            conn.commit()
            print(f"✅ 保存日线数据 {len(df_filtered)} 条")
        except Exception as e:
            print(f"❌ 保存失败：{e}")
            conn.rollback()
        finally:
            conn.close()
    
    def save_daily_basic(self, df):
        """保存基本面数据"""
        if df is None or len(df) == 0:
            return
        
        conn = sqlite3.connect(str(self.fundamentals_db))
        try:
            df.to_sql('daily_basic', conn, if_exists='append', index=False, method='multi')
            conn.commit()
            print(f"✅ 保存基本面数据 {len(df)} 条")
        except Exception as e:
            print(f"❌ 保存失败：{e}")
            conn.rollback()
        finally:
            conn.close()
    
    def save_fina_indicator(self, df):
        """保存财务指标"""
        if df is None or len(df) == 0:
            return
        
        conn = sqlite3.connect(str(self.fundamentals_db))
        try:
            df.to_sql('fina_indicator', conn, if_exists='append', index=False, method='multi')
            conn.commit()
            print(f"✅ 保存财务指标 {len(df)} 条")
        except Exception as e:
            print(f"❌ 保存失败：{e}")
            conn.rollback()
        finally:
            conn.close()
    
    def save_factor_scores(self, df):
        """保存因子得分"""
        if df is None or len(df) == 0:
            return
        
        conn = sqlite3.connect(str(self.factors_db))
        try:
            df.to_sql('factor_scores', conn, if_exists='append', index=False, method='multi')
            conn.commit()
            print(f"✅ 保存因子得分 {len(df)} 条")
        except Exception as e:
            print(f"❌ 保存失败：{e}")
            conn.rollback()
        finally:
            conn.close()
    
    def get_daily_data(self, ts_code, start_date, end_date):
        """
        获取日线数据
        
        Args:
            ts_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            DataFrame: 日线数据
        """
        conn = sqlite3.connect(str(self.stock_db))
        
        query = """
            SELECT * FROM daily_data 
            WHERE ts_code = ? AND trade_date BETWEEN ? AND ?
            ORDER BY trade_date DESC
        """
        
        df = pd.read_sql_query(query, conn, params=(ts_code, start_date, end_date))
        conn.close()
        
        if len(df) > 0:
            print(f"✅ 获取 {ts_code} 日线数据 {len(df)} 条")
        return df
    
    def get_stock_list_from_db(self):
        """从数据库获取股票列表"""
        conn = sqlite3.connect(str(self.stock_db))
        
        query = "SELECT DISTINCT ts_code FROM daily_data"
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df['ts_code'].tolist() if len(df) > 0 else []
    
    def get_database_stats(self):
        """获取数据库统计信息"""
        stats = {}
        
        # 日线数据
        conn = sqlite3.connect(str(self.stock_db))
        cursor = conn.execute("SELECT COUNT(*) FROM daily_data")
        stats['daily_data_count'] = cursor.fetchone()[0]
        conn.close()
        
        # 基本面数据
        conn = sqlite3.connect(str(self.fundamentals_db))
        cursor = conn.execute("SELECT COUNT(*) FROM daily_basic")
        stats['basic_data_count'] = cursor.fetchone()[0]
        conn.close()
        
        # 因子得分
        conn = sqlite3.connect(str(self.factors_db))
        cursor = conn.execute("SELECT COUNT(*) FROM factor_scores")
        stats['factor_scores_count'] = cursor.fetchone()[0]
        conn.close()
        
        # 文件大小
        stats['stock_db_size_mb'] = self.stock_db.stat().st_size / 1024 / 1024
        stats['fundamentals_db_size_mb'] = self.fundamentals_db.stat().st_size / 1024 / 1024
        stats['factors_db_size_mb'] = self.factors_db.stat().st_size / 1024 / 1024
        
        return stats
    
    def vacuum_database(self):
        """优化数据库（VACUUM）"""
        print("开始优化数据库...")
        
        for db_path in [self.stock_db, self.fundamentals_db, self.factors_db, self.backtest_db]:
            if db_path.exists():
                conn = sqlite3.connect(str(db_path))
                conn.execute("VACUUM")
                conn.execute("ANALYZE")
                conn.commit()
                conn.close()
                print(f"✅ {db_path.name} 优化完成")
        
        print("✅ 数据库优化完成")


# 测试
if __name__ == "__main__":
    storage = DataStorage()
    
    # 测试数据库统计
    print("\n" + "=" * 70)
    print("数据库统计信息")
    print("=" * 70)
    stats = storage.get_database_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    print("\n" + "=" * 70)
    print("✅ 数据存储模块测试完成")
    print("=" * 70)
