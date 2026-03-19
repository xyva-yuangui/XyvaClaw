#!/usr/bin/env python3
"""快速导入数据 - 先导入 100 只股票测试"""

import sys
sys.path.insert(0, '.')

from data_fetcher import DataFetcher
from data_storage import DataStorage
from datetime import datetime, timedelta

print("=" * 70)
print("快速数据导入 - 100 只股票")
print("=" * 70)

fetcher = DataFetcher()
storage = DataStorage()

# 获取股票列表
print("\n获取股票列表...")
stock_list_df = fetcher.get_stock_list()
if stock_list_df is None:
    print("❌ 获取股票列表失败")
    sys.exit(1)

stock_codes = stock_list_df['ts_code'].tolist()[:100]  # 前 100 只
print(f"获取到 {len(stock_codes)} 只股票")

# 导入日线数据（最近 3 个月）
end_date = datetime.now()
start_date = end_date - timedelta(days=90)
start_date_str = start_date.strftime('%Y%m%d')
end_date_str = end_date.strftime('%Y%m%d')

print(f"\n导入日线数据：{start_date_str} - {end_date_str}")
print("预计时间：5-10 分钟\n")

all_data = []
for i, ts_code in enumerate(stock_codes):
    df = fetcher.fetch_daily_data(ts_code, start_date_str, end_date_str)
    if df is not None:
        all_data.append(df)
    
    if (i + 1) % 20 == 0:
        print(f"已获取 {i+1}/{len(stock_codes)} 只股票")

if all_data:
    import pandas as pd
    combined = pd.concat(all_data, ignore_index=True)
    storage.save_daily_data(combined)
    print(f"\n✅ 保存日线数据 {len(combined)} 条")
    
    # 显示统计
    stats = storage.get_database_stats()
    print(f"\n数据库统计:")
    print(f"  日线数据：{stats['daily_data_count']:,} 条")
    print(f"  数据库大小：{stats['stock_db_size_mb']:.2f} MB")
else:
    print("\n❌ 获取数据失败")

print("\n" + "=" * 70)
print("✅ 数据导入完成")
print("=" * 70)
