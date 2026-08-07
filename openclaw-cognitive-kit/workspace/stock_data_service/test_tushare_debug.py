#!/usr/bin/env python3
"""
Tushare 调试测试
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("🔍 Tushare 调试测试")
print("=" * 60)

# 直接测试 Tushare
import tushare as ts

token = "REDACTED_HEX_TOKEN"
gateway = ""

print(f"\n1. 设置 Token: {'*' * 10}{token[-10:]}")
ts.set_token(token)

print(f"2. 初始化 API (网关：{gateway})")
pro = ts.pro_api()

# 设置私有网关
pro._DataApi__http_url = gateway
print(f"3. 网关已设置：{pro._DataApi__http_url}")

# 测试1: 获取所有股票基本信息
print("\n4. 测试获取股票基本信息...")
try:
    df = pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name,area,industry,market,list_date')
    print(f"   ✅ 获取成功: {len(df)} 条记录")
    print(f"   列名：{list(df.columns)}")
    if len(df) > 0:
        print(f"   前 3 条:")
        print(df[['ts_code', 'symbol', 'name']].head(3))
except Exception as e:
    print(f"   ❌ 获取失败: {e}")
    import traceback
    traceback.print_exc()

# 测试 2: 获取单个股票
print("\n5. 测试获取单个股票 (000001.SZ)...")
try:
    df = pro.stock_basic(ts_code='000001.SZ')
    print(f"   ✅ 获取成功: {len(df)} 条记录")
    if len(df) > 0:
        print(f"   数据：{df.iloc[0].to_dict()}")
except Exception as e:
    print(f"   ❌ 获取失败: {e}")

# 测试 3: 获取日线数据
print("\n6. 测试获取日线数据 (000001.SZ)...")
try:
    df = pro.daily(ts_code='000001.SZ', start_date='20240301', end_date='20240310')
    print(f"   ✅ 获取成功: {len(df)} 条记录")
    print(f"   列名：{list(df.columns)}")
    if len(df) > 0:
        print(f"   前 3 条:")
        print(df[['trade_date', 'open', 'high', 'low', 'close']].head(3))
except Exception as e:
    print(f"   ❌ 获取失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("🎉 Tushare 调试测试完成！")
