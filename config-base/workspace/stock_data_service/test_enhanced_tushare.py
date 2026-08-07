#!/usr/bin/env python3
"""
测试增强后的TushareProvider
"""

import sys
import os

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 现在导入
try:
    from providers.tushare_provider import TushareProvider
    print("✅ 导入成功")
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    # 尝试直接导入
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "tushare_provider", 
        os.path.join(current_dir, "providers", "tushare_provider.py")
    )
    tushare_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tushare_module)
    TushareProvider = tushare_module.TushareProvider
    print("✅ 直接导入成功")

# 创建配置
config = {
    'token': 'REDACTED_HEX_TOKEN',
    'gateway_url': ''
}

print('🧪 测试增强后的TushareProvider')
print('=' * 60)

provider = TushareProvider(config)

# 测试各种方法
test_cases = [
    ('get_stock_basic', {'symbol': '000001.SZ'}),
    ('get_daily_data', {'symbol': '000001.SZ', 'start_date': '20260301', 'end_date': '20260323'}),
    ('get_moneyflow', {'symbol': '000001.SZ', 'start_date': '20260301', 'end_date': '20260323'}),
    ('get_fina_indicator', {'symbol': '000001.SZ'}),
    ('get_index_data', {'index_code': '000001.SH', 'start_date': '20260301', 'end_date': '20260323'}),
    ('get_macro_data', {'indicator': 'gdp'}),
    ('get_trade_calendar', {'exchange': 'SSE', 'start_date': '20260301', 'end_date': '20260331'}),
]

for method_name, kwargs in test_cases:
    print(f'\n测试 {method_name}():')
    try:
        method = getattr(provider, method_name)
        result = method(**kwargs)
        
        if result is not None:
            if hasattr(result, 'shape'):
                print(f'  ✅ 成功: {len(result)} 行数据')
                # 显示前几列
                if len(result) > 0:
                    cols = list(result.columns)[:3]
                    print(f'     列: {cols}')
            elif isinstance(result, dict):
                print(f'  ✅ 成功: 字典类型，{len(result)} 个键')
                for key in result:
                    if hasattr(result[key], 'shape'):
                        print(f'     {key}: {len(result[key])} 行')
            else:
                print(f'  ✅ 成功: 返回数据')
        else:
            print(f'  ⚠️  返回空数据')
            
    except Exception as e:
        print(f'  ❌ 失败: {str(e)[:50]}...')

print('\n' + '=' * 60)
print('📊 TushareProvider增强完成！')

# 测试provider状态
print(f'\nProvider状态:')
print(f'  名称: {provider.name}')
print(f'  可用性: {provider.is_available}')
print(f'  统计: {provider.get_stats()}')