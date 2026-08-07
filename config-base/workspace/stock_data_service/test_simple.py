#!/usr/bin/env python3
"""
统一数据服务层简单测试
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stock_data_service import StockDataClient, StockDataConfig


def test_basic_functionality():
    """测试基本功能"""
    print("🧪 开始测试统一数据服务层...")
    print("=" * 60)
    
    # 创建客户端
    print("1. 创建客户端...")
    client = StockDataClient()
    print(f"   ✅ 客户端创建成功")
    print(f"   {client}")
    print()
    
    # 测试获取股票基本信息
    print("2. 测试获取股票基本信息...")
    try:
        df = client.get_stock_basic("000001.SZ")
        if df is not None and not df.empty:
            print(f"   ✅ 获取成功: {len(df)} 条记录")
            print(f"   列名: {list(df.columns)}")
            if len(df) > 0:
                print(f"   第一条记录: {df.iloc[0].to_dict()}")
        else:
            print("   ❌ 获取失败或返回空数据")
    except Exception as e:
        print(f"   ❌ 获取失败: {e}")
    print()
    
    # 测试获取日线数据
    print("3. 测试获取日线数据...")
    try:
        df = client.get_daily_data("000001.SZ", start_date="20240301", end_date="20240310")
        if df is not None and not df.empty:
            print(f"   ✅ 获取成功: {len(df)} 条记录")
            print(f"   日期范围: {df['trade_date'].min()} 到 {df['trade_date'].max()}")
            print(f"   列名: {list(df.columns)}")
        else:
            print("   ❌ 获取失败或返回空数据")
    except Exception as e:
        print(f"   ❌ 获取失败: {e}")
    print()
    
    # 测试缓存功能
    print("4. 测试缓存功能...")
    try:
        # 第一次获取（应该缓存）
        df1 = client.get_daily_data("000001.SZ", days=10)
        print(f"   ✅ 第一次获取成功: {len(df1) if df1 is not None else 0} 条")
        
        # 第二次获取（应该从缓存读取）
        df2 = client.get_daily_data("000001.SZ", days=10)
        print(f"   ✅ 第二次获取成功: {len(df2) if df2 is not None else 0} 条")
        
        # 检查是否相同
        if df1 is not None and df2 is not None:
            print(f"   ✅ 两次获取数据相同: {df1.equals(df2)}")
    except Exception as e:
        print(f"   ❌ 缓存测试失败: {e}")
    print()
    
    # 测试多数据源回退
    print("5. 测试多数据源回退...")
    try:
        # 获取提供器统计
        provider_stats = client.get_provider_stats()
        print(f"   ✅ 提供器统计:")
        for name, stats in provider_stats.items():
            print(f"     {name}: 可用={stats['is_available']}, "
                  f"调用={stats['calls']}, 成功率={stats['success_rate']}")
    except Exception as e:
        print(f"   ❌ 多数据源测试失败: {e}")
    print()
    
    # 获取客户端统计
    print("6. 获取客户端统计...")
    try:
        stats = client.get_client_stats()
        print(f"   ✅ 客户端统计:")
        print(f"     总调用次数: {stats['total_calls']}")
        print(f"     缓存命中率: {stats['cache_hit_rate']}")
        print(f"     错误率: {stats['error_rate']}")
        print(f"     提供器调用: {stats['provider_calls']}")
    except Exception as e:
        print(f"   ❌ 获取统计失败: {e}")
    print()
    
    # 清理
    print("7. 清理资源...")
    try:
        client.cleanup()
        print("   ✅ 清理成功")
    except Exception as e:
        print(f"   ❌ 清理失败: {e}")
    
    print("=" * 60)
    print("🎉 测试完成！")


def test_with_custom_config():
    """测试自定义配置"""
    print("\n🧪 测试自定义配置...")
    print("=" * 60)
    
    # 创建自定义配置
    config = StockDataConfig(
        tushare_token="REDACTED_HEX_TOKEN",
        tushare_gateway="",
        cache_enabled=True,
        data_source_priority=["tushare", "akshare"],  # 优先使用Tushare
    )
    
    print(f"自定义配置: {config}")
    
    # 使用自定义配置创建客户端
    client = StockDataClient(config)
    
    # 测试获取数据
    df = client.get_stock_basic("000001")
    if df is not None:
        print(f"✅ 使用自定义配置获取成功: {len(df)} 条")
    else:
        print("❌ 使用自定义配置获取失败")
    
    print("=" * 60)


def test_error_handling():
    """测试错误处理"""
    print("\n🧪 测试错误处理...")
    print("=" * 60)
    
    client = StockDataClient()
    
    # 测试无效股票代码
    print("1. 测试无效股票代码...")
    df = client.get_stock_basic("INVALID_CODE")
    if df is None or df.empty:
        print("   ✅ 正确处理无效代码（返回空或None）")
    else:
        print("   ⚠️  无效代码返回了数据")
    
    # 测试无效日期
    print("2. 测试无效日期...")
    df = client.get_daily_data("000001.SZ", start_date="99990101", end_date="99991231")
    if df is None or df.empty:
        print("   ✅ 正确处理无效日期（返回空或None）")
    else:
        print("   ⚠️  无效日期返回了数据")
    
    print("=" * 60)


if __name__ == "__main__":
    print("🚀 统一股票数据服务层测试套件")
    print("=" * 60)
    
    # 运行所有测试
    test_basic_functionality()
    test_with_custom_config()
    test_error_handling()
    
    print("\n🎯 所有测试完成！")
    print("=" * 60)