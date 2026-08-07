#!/usr/bin/env python3
"""
全面测试验证脚本
对比统一接口库与现有技能的数据获取
"""

import sys
import os
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ComprehensiveTester:
    """全面测试器"""
    
    def __init__(self):
        self.results = {}
        self.test_data = {}
        
    def test_1_basic_functionality(self):
        """测试1：基础功能测试"""
        print("\n🧪 测试1：基础功能测试")
        print("-" * 40)
        
        test_results = {
            'name': '基础功能测试',
            'subtests': [],
            'status': 'pass'
        }
        
        # 1.1 检查文件结构
        print("1.1 检查文件结构...")
        required_files = [
            'client.py',
            'providers/__init__.py',
            'providers/base_provider.py',
            'providers/tushare_provider.py',
            'providers/akshare_provider.py',
            'providers/baostock_provider.py',
            'providers/mootdx_provider.py',
            'cache.py',
            'exceptions.py',
            'utils.py'
        ]
        
        missing_files = []
        for file in required_files:
            path = os.path.join(os.path.dirname(__file__), file)
            if not os.path.exists(path):
                missing_files.append(file)
        
        if missing_files:
            test_results['subtests'].append({
                'name': '文件结构检查',
                'status': 'fail',
                'message': f'缺少文件: {missing_files}'
            })
            test_results['status'] = 'fail'
        else:
            test_results['subtests'].append({
                'name': '文件结构检查',
                'status': 'pass',
                'message': '所有必需文件都存在'
            })
        
        # 1.2 测试导入
        print("1.2 测试导入...")
        try:
            # 尝试导入关键模块
            sys.path.insert(0, os.path.dirname(__file__))
            
            # 测试导入
            import importlib.util
            
            # 测试导入base_provider
            spec = importlib.util.spec_from_file_location(
                "base_provider",
                os.path.join(os.path.dirname(__file__), "providers", "base_provider.py")
            )
            base_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(base_module)
            
            test_results['subtests'].append({
                'name': '模块导入测试',
                'status': 'pass',
                'message': '关键模块导入成功'
            })
            
        except Exception as e:
            test_results['subtests'].append({
                'name': '模块导入测试',
                'status': 'fail',
                'message': f'导入失败: {str(e)}'
            })
            test_results['status'] = 'fail'
        
        # 1.3 测试配置文件
        print("1.3 测试配置文件...")
        config_path = os.path.join(os.path.dirname(__file__), 'config.py')
        if os.path.exists(config_path):
            try:
                # 尝试导入config模块
                import importlib.util
                spec = importlib.util.spec_from_file_location("config", config_path)
                config_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(config_module)
                
                # 检查必要的配置项
                required_configs = ['TUSHARE_TOKEN', 'TUSHARE_GATEWAY_URL']
                missing_configs = []
                
                for key in required_configs:
                    if not hasattr(config_module, key) or not getattr(config_module, key):
                        missing_configs.append(key)
                
                if missing_configs:
                    test_results['subtests'].append({
                        'name': '配置文件检查',
                        'status': 'warning',
                        'message': f'缺少配置项: {missing_configs}'
                    })
                else:
                    test_results['subtests'].append({
                        'name': '配置文件检查',
                        'status': 'pass',
                        'message': '配置文件完整'
                    })
                    
            except Exception as e:
                test_results['subtests'].append({
                    'name': '配置文件检查',
                    'status': 'fail',
                    'message': f'配置文件读取失败: {str(e)}'
                })
                test_results['status'] = 'fail'
        else:
            test_results['subtests'].append({
                'name': '配置文件检查',
                'status': 'warning',
                'message': '配置文件不存在'
            })
        
        self.results['basic_functionality'] = test_results
        return test_results
    
    def test_2_data_consistency(self):
        """测试2：数据一致性测试"""
        print("\n🧪 测试2：数据一致性测试")
        print("-" * 40)
        
        test_results = {
            'name': '数据一致性测试',
            'subtests': [],
            'status': 'pass'
        }
        
        # 2.1 测试股票基本信息获取
        print("2.1 测试股票基本信息获取...")
        
        # 这里需要实际调用接口进行测试
        # 由于需要实际数据源，这里先标记为需要手动测试
        test_results['subtests'].append({
            'name': '股票基本信息获取',
            'status': 'manual',
            'message': '需要手动测试实际数据获取'
        })
        
        # 2.2 测试日线数据获取
        print("2.2 测试日线数据获取...")
        test_results['subtests'].append({
            'name': '日线数据获取',
            'status': 'manual',
            'message': '需要手动测试实际数据获取'
        })
        
        # 2.3 测试财务数据获取
        print("2.3 测试财务数据获取...")
        test_results['subtests'].append({
            'name': '财务数据获取',
            'status': 'manual',
            'message': '需要手动测试实际数据获取'
        })
        
        # 2.4 测试资金流向数据获取
        print("2.4 测试资金流向数据获取...")
        test_results['subtests'].append({
            'name': '资金流向数据获取',
            'status': 'manual',
            'message': '需要手动测试实际数据获取'
        })
        
        self.results['data_consistency'] = test_results
        return test_results
    
    def test_3_performance_comparison(self):
        """测试3：性能对比测试"""
        print("\n🧪 测试3：性能对比测试")
        print("-" * 40)
        
        test_results = {
            'name': '性能对比测试',
            'subtests': [],
            'status': 'pass'
        }
        
        # 3.1 响应时间测试
        print("3.1 响应时间测试...")
        
        # 模拟测试
        test_cases = [
            {'name': '股票基本信息', 'expected_time': 1.0},
            {'name': '日线数据(30天)', 'expected_time': 2.0},
            {'name': '财务数据', 'expected_time': 1.5},
            {'name': '资金流向数据', 'expected_time': 1.5}
        ]
        
        for test_case in test_cases:
            test_results['subtests'].append({
                'name': f'{test_case["name"]}响应时间',
                'status': 'manual',
                'message': f'需要实际测试，期望响应时间<{test_case["expected_time"]}s'
            })
        
        # 3.2 并发性能测试
        print("3.2 并发性能测试...")
        test_results['subtests'].append({
            'name': '并发性能',
            'status': 'manual',
            'message': '需要测试多线程/多进程并发获取数据'
        })
        
        # 3.3 缓存性能测试
        print("3.3 缓存性能测试...")
        test_results['subtests'].append({
            'name': '缓存性能',
            'status': 'manual',
            'message': '需要测试缓存命中率和性能提升'
        })
        
        self.results['performance_comparison'] = test_results
        return test_results
    
    def test_4_error_handling(self):
        """测试4：错误处理测试"""
        print("\n🧪 测试4：错误处理测试")
        print("-" * 40)
        
        test_results = {
            'name': '错误处理测试',
            'subtests': [],
            'status': 'pass'
        }
        
        # 4.1 网络错误处理
        print("4.1 网络错误处理...")
        test_results['subtests'].append({
            'name': '网络错误处理',
            'status': 'manual',
            'message': '需要测试网络断开、超时等情况的处理'
        })
        
        # 4.2 数据源降级
        print("4.2 数据源降级...")
        test_results['subtests'].append({
            'name': '数据源降级机制',
            'status': 'manual',
            'message': '需要测试主数据源失败时自动切换到备用数据源'
        })
        
        # 4.3 数据格式错误
        print("4.3 数据格式错误...")
        test_results['subtests'].append({
            'name': '数据格式错误处理',
            'status': 'manual',
            'message': '需要测试返回数据格式不正确时的处理'
        })
        
        # 4.4 参数错误处理
        print("4.4 参数错误处理...")
        test_results['subtests'].append({
            'name': '参数错误处理',
            'status': 'manual',
            'message': '需要测试传入错误参数时的处理'
        })
        
        self.results['error_handling'] = test_results
        return test_results
    
    def test_5_integration_with_alpha_research(self):
        """测试5：与alpha-research集成测试"""
        print("\n🧪 测试5：与alpha-research集成测试")
        print("-" * 40)
        
        test_results = {
            'name': 'alpha-research集成测试',
            'subtests': [],
            'status': 'pass'
        }
        
        # 5.1 检查alpha-research目录结构
        print("5.1 检查alpha-research目录结构...")
        alpha_research_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'skills', 'alpha-research'
        )
        
        if os.path.exists(alpha_research_path):
            test_results['subtests'].append({
                'name': 'alpha-research目录存在',
                'status': 'pass',
                'message': f'目录路径: {alpha_research_path}'
            })
            
            # 检查关键文件
            required_files = [
                'SKILL.md',
                'provider.py',
                'analyzer.py',
                'report_generator.py'
            ]
            
            missing_files = []
            for file in required_files:
                if not os.path.exists(os.path.join(alpha_research_path, file)):
                    missing_files.append(file)
            
            if missing_files:
                test_results['subtests'].append({
                    'name': 'alpha-research关键文件',
                    'status': 'warning',
                    'message': f'缺少文件: {missing_files}'
                })
            else:
                test_results['subtests'].append({
                    'name': 'alpha-research关键文件',
                    'status': 'pass',
                    'message': '所有关键文件都存在'
                })
        else:
            test_results['subtests'].append({
                'name': 'alpha-research目录存在',
                'status': 'fail',
                'message': 'alpha-research目录不存在'
            })
            test_results['status'] = 'fail'
        
        # 5.2 分析数据接口兼容性
        print("5.2 分析数据接口兼容性...")
        test_results['subtests'].append({
            'name': '数据接口兼容性分析',
            'status': 'manual',
            'message': '需要分析alpha-research的provider.py与统一接口库的兼容性'
        })
        
        # 5.3 迁移复杂度评估
        print("5.3 迁移复杂度评估...")
        test_results['subtests'].append({
            'name': '迁移复杂度评估',
            'status': 'manual',
            'message': '需要评估迁移所需的工作量和风险'
        })
        
        self.results['integration_alpha_research'] = test_results
        return test_results
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始全面测试验证")
        print("=" * 60)
        
        start_time = time.time()
        
        # 运行所有测试
        self.test_1_basic_functionality()
        self.test_2_data_consistency()
        self.test_3_performance_comparison()
        self.test_4_error_handling()
        self.test_5_integration_with_alpha_research()
        
        total_time = time.time() - start_time
        
        # 生成测试报告
        self.generate_report(total_time)
    
    def generate_report(self, total_time):
        """生成测试报告"""
        print("\n" + "=" * 60)
        print("📊 全面测试验证报告")
        print("=" * 60)
        
        # 统计结果
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        warning_tests = 0
        manual_tests = 0
        
        for test_name, test_result in self.results.items():
            print(f"\n🔍 {test_result['name']}: {test_result['status']}")
            
            for subtask in test_result['subtests']:
                total_tests += 1
                status = subtask['status']
                
                if status == 'pass':
                    passed_tests += 1
                    status_emoji = '✅'
                elif status == 'fail':
                    failed_tests += 1
                    status_emoji = '❌'
                elif status == 'warning':
                    warning_tests += 1
                    status_emoji = '⚠️'
                elif status == 'manual':
                    manual_tests += 1
                    status_emoji = '🔧'
                else:
                    status_emoji = '❓'
                
                print(f"  {status_emoji} {subtask['name']}: {subtask['message']}")
        
        # 总结
        print("\n" + "=" * 60)
        print("📈 测试总结")
        print("=" * 60)
        
        print(f"总测试数: {total_tests}")
        print(f"✅ 通过: {passed_tests}")
        print(f"❌ 失败: {failed_tests}")
        print(f"⚠️  警告: {warning_tests}")
        print(f"🔧 需要手动测试: {manual_tests}")
        print(f"⏱️  总耗时: {total_time:.2f}秒")
        
        # 风险评估
        print("\n⚠️  风险评估:")
        if failed_tests > 0:
            print("  ❌ 存在失败测试，需要立即修复")
        if warning_tests > 0:
            print("  ⚠️  存在警告，建议检查")
        if manual_tests > total_tests * 0.5:
            print("  🔧 大量测试需要手动验证，建议优先完成")
        
        # 建议
        print("\n💡 建议:")
        if failed_tests == 0 and manual_tests < total_tests * 0.3:
            print("  ✅ 基础测试通过，可以开始实际数据测试")
        else:
            print("  🔧 需要先完成基础测试和手动验证")
        
        # 保存报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"comprehensive_test_report_{timestamp}.json"
        
        report_data = {
            'timestamp': timestamp,
            'total_time': total_time,
            'summary': {
                'total_tests': total_tests,
                'passed': passed_tests,
                'failed': failed_tests,
                'warnings': warning_tests,
                'manual': manual_tests
            },
            'results': self.results
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 详细报告已保存到: {report_file}")

def main():
    """主函数"""
    tester = ComprehensiveTester()
    tester.run_all_tests()

if __name__ == "__main__":
    main()