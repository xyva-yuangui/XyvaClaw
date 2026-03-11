#!/usr/bin/env python3
"""
选股器 - Stock Selector
基于多因子模型和动态权重进行选股
"""

import sys
import pandas as pd
from pathlib import Path
from datetime import datetime

# 导入模块
sys.path.insert(0, str(Path(__file__).parent))
from data_storage import DataStorage
from factor_calculator import FactorCalculator
from risk_controller import RiskController

class StockSelector:
    """选股器"""
    
    def __init__(self):
        self.storage = DataStorage()
        self.factor_calc = FactorCalculator()
        self.risk_ctrl = RiskController()
        
        # 选股配置
        self.config = {
            'top_n': 10,  # 选股数量
            'min_market_cap': 100,  # 最小市值（亿）
            'min_daily_volume': 1,  # 最小日均成交（亿）
            'exclude_st': True,  # 排除 ST
            'weights': {  # 因子权重
                '估值': 0.25,
                '成长': 0.25,
                '动量': 0.20,
                '质量': 0.15,
                '技术': 0.10,
                '资金': 0.05
            }
        }
    
    def select_stocks(self, trade_date=None):
        """
        选股
        
        Args:
            trade_date: 交易日期（默认今天）
        
        Returns:
            DataFrame: 选股结果
        """
        if trade_date is None:
            trade_date = datetime.now().strftime('%Y%m%d')
        
        print("=" * 70)
        print("📈 量化选股")
        print("=" * 70)
        print(f"交易日期：{trade_date}")
        print(f"选股数量：{self.config['top_n']}")
        print(f"因子权重：{self.config['weights']}")
        print("=" * 70)
        
        # 1. 获取股票列表
        print("\n【步骤 1】获取股票列表...")
        stock_list = self.storage.get_stock_list_from_db()
        print(f"获取到 {len(stock_list)} 只股票")
        
        # 2. 初筛
        print("\n【步骤 2】初筛...")
        filtered_stocks = self._filter_stocks(stock_list)
        print(f"初筛后剩余 {len(filtered_stocks)} 只股票")
        
        # 3. 计算因子得分
        print("\n【步骤 3】计算因子得分...")
        factor_scores = self.factor_calc.calculate_all_factors(filtered_stocks, trade_date)
        
        # 4. 计算综合得分
        print("\n【步骤 4】计算综合得分...")
        factor_scores['total_score'] = (
            factor_scores['valuation_score'] * self.config['weights']['估值'] +
            factor_scores['growth_score'] * self.config['weights']['成长'] +
            factor_scores['momentum_score'] * self.config['weights']['动量'] +
            factor_scores['quality_score'] * self.config['weights']['质量'] +
            factor_scores['technical_score'] * self.config['weights']['技术'] +
            factor_scores['moneyflow_score'] * self.config['weights']['资金']
        )
        
        # 5. 排序选股
        print("\n【步骤 5】排序选股...")
        selected = factor_scores.nlargest(self.config['top_n'], 'total_score')
        
        # 6. 风险控制
        print("\n【步骤 6】风险控制...")
        selected = self.risk_ctrl.apply_risk_control(selected)
        
        # 7. 输出结果
        print("\n" + "=" * 70)
        print("🏆 选股结果 Top 10")
        print("=" * 70)
        print(selected[['ts_code', 'name', 'total_score', 'valuation_score', 'growth_score', 'momentum_score']].to_string())
        
        print("\n" + "=" * 70)
        print("✅ 选股完成")
        print("=" * 70)
        
        return selected
    
    def _filter_stocks(self, stock_list):
        """初筛"""
        # TODO: 实现 ST 排除、市值筛选、成交筛选
        # 暂时返回全部
        return stock_list


if __name__ == "__main__":
    selector = StockSelector()
    result = selector.select_stocks()
