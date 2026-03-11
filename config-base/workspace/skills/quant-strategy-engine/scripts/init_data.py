#!/usr/bin/env python3
"""
数据初始化脚本 - Initialize Data
初始化数据库，导入历史数据
"""

import sys
sys.path.insert(0, '.')

from data_fetcher import DataFetcher
from data_storage import DataStorage
from cache_manager import CacheManager
from datetime import datetime, timedelta

def init_database():
    """初始化数据库"""
    print("=" * 70)
    print("数据初始化")
    print("=" * 70)
    
    # 初始化模块
    fetcher = DataFetcher()
    storage = DataStorage()
    cache_manager = CacheManager()
    
    # 获取股票列表
    print("\n" + "=" * 70)
    print("步骤 1: 获取股票列表")
    print("=" * 70)
    stock_list_df = fetcher.get_stock_list()
    
    if stock_list_df is not None:
        stock_codes = stock_list_df['ts_code'].tolist()
        print(f"获取到 {len(stock_codes)} 只股票")
        
        # 缓存股票列表
        cache_manager.set_stock_list(stock_codes)
        print("✅ 股票列表已缓存")
    else:
        print("❌ 获取股票列表失败")
        return
    
    # 导入历史数据（最近 1 年）
    print("\n" + "=" * 70)
    print("步骤 2: 导入历史数据（最近 1 年）")
    print("=" * 70)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    start_date_str = start_date.strftime('%Y%m%d')
    end_date_str = end_date.strftime('%Y%m%d')
    
    print(f"日期范围：{start_date_str} - {end_date_str}")
    print(f"股票数量：{len(stock_codes)}")
    print("预计时间：约 10-20 分钟\n")
    
    # 批量获取日线数据
    all_daily_data = fetcher.batch_fetch_daily(stock_codes, start_date_str, end_date_str, batch_size=50)
    
    if all_daily_data is not None:
        # 保存到数据库
        storage.save_daily_data(all_daily_data)
        print(f"✅ 保存日线数据 {len(all_daily_data)} 条")
    else:
        print("❌ 获取日线数据失败")
    
    # 获取基本面数据（最近 1 个月）
    print("\n" + "=" * 70)
    print("步骤 3: 导入基本面数据（最近 1 个月）")
    print("=" * 70)
    
    basic_start = (end_date - timedelta(days=30)).strftime('%Y%m%d')
    all_basic_data = []
    
    for i, ts_code in enumerate(stock_codes[:100]):  # 先测试前 100 只
        basic_df = fetcher.fetch_daily_basic(ts_code, end_date_str)
        if basic_df is not None:
            all_basic_data.append(basic_df)
        
        if (i + 1) % 20 == 0:
            print(f"已获取 {i+1}/{len(stock_codes[:100])} 只股票")
    
    if all_basic_data:
        combined_basic = pd.concat(all_basic_data, ignore_index=True)
        storage.save_daily_basic(combined_basic)
        print(f"✅ 保存基本面数据 {len(combined_basic)} 条")
    
    # 显示数据库统计
    print("\n" + "=" * 70)
    print("步骤 4: 数据库统计")
    print("=" * 70)
    stats = storage.get_database_stats()
    
    print("\n数据量统计:")
    print(f"  日线数据：{stats.get('daily_data_count', 0):,} 条")
    print(f"  基本面数据：{stats.get('basic_data_count', 0):,} 条")
    print(f"  因子得分：{stats.get('factor_scores_count', 0):,} 条")
    
    print("\n文件大小:")
    print(f"  stock_data.db: {stats.get('stock_db_size_mb', 0):.2f} MB")
    print(f"  fundamentals.db: {stats.get('fundamentals_db_size_mb', 0):.2f} MB")
    print(f"  factors.db: {stats.get('factors_db_size_mb', 0):.2f} MB")
    
    # 缓存统计
    print("\n" + "=" * 70)
    print("步骤 5: 缓存统计")
    print("=" * 70)
    cache_stats = cache_manager.get_all_stats()
    
    for name, stat in cache_stats.items():
        print(f"  {name}: 容量={stat['capacity']}, 当前={stat['current_size']}, 命中率={stat['hit_rate']}")
    
    print("\n" + "=" * 70)
    print("✅ 数据初始化完成")
    print("=" * 70)
    print("\n下一步:")
    print("  1. 运行因子计算：python3 factor_calculator.py")
    print("  2. 运行回测引擎：python3 backtester.py")
    print("  3. 运行选股器：python3 stock_selector.py")
    print("=" * 70)


if __name__ == "__main__":
    import pandas as pd
    init_database()
