#!/usr/bin/env python3
"""
统一数据服务层快速测试
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 60)
print("🧪 统一股票数据服务层 - 快速测试")
print("=" * 60)

# 测试1: 导入模块
print("\n1. 测试模块导入...")
try:
    from stock_data_service import StockDataClient, StockDataConfig
    print("   ✅ 模块导入成功")
except Exception as e:
    print(f"   ❌ 模块导入失败: {e}")
    sys.exit(1)

# 测试2: 创建配置
print("\n2. 测试创建配置...")
try:
    config = StockDataConfig(
        tushare_token="REDACTED_HEX_TOKEN",
        tushare_gateway="",
    )
    print(f"   ✅ 配置创建成功")
    print(f"      Token: {'*' * 10}{config.tushare_token[-10:]}")
    print(f"      网关：{config.tushare_gateway}")
except Exception as e:
    print(f"   ❌ 配置创建失败: {e}")
    sys.exit(1)

# 测试3: 创建客户端
print("\n3. 测试创建客户端...")
try:
    client = StockDataClient(config)
    print(f"   ✅ 客户端创建成功")
except Exception as e:
    print(f"   ❌ 客户端创建失败: {e}")
    sys.exit(1)

# 测试4: 检查提供器状态
print("\n4. 检查数据提供器状态...")
try:
    provider_stats = client.get_provider_stats()
    for name, stats in provider_stats.items():
        status = "✅" if stats['is_available'] else "❌"
        print(f"   {status} {name}: 调用={stats['calls']}, 成功率={stats['success_rate']}")
except Exception as e:
    print(f"   ❌ 检查失败: {e}")

# 测试5: 获取股票基本信息（简化）
print("\n5. 测试获取股票基本信息...")
try:
    import time
    start = time.time()
    df = client.get_stock_basic("000001.SZ")
    elapsed = time.time() - start
    
    if df is not None and not df.empty:
        print(f"   ✅ 获取成功: {len(df)} 条，耗时 {elapsed:.2f}s")
        print(f"      列数：{len(df.columns)}")
        if len(df) > 0:
            print(f"      示例：{df.iloc[0].to_dict()}")
    else:
        print(f"   ⚠️  返回空数据，耗时 {elapsed:.2f}s")
except Exception as e:
    print(f"   ❌ 获取失败: {e}")
    import traceback
    traceback.print_exc()

# 测试6: 获取统计信息
print("\n6. 获取客户端统计...")
try:
    stats = client.get_client_stats()
    print(f"   ✅ 统计信息:")
    print(f"      总调用：{stats['total_calls']}")
    print(f"      缓存命中：{stats['cache_hits']}")
    print(f"      错误数：{stats['errors']}")
except Exception as e:
    print(f"   ❌ 获取统计失败: {e}")

print("\n" + "=" * 60)
print("🎉 快速测试完成！")
print("=" * 60)
