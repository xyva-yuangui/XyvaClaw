#!/usr/bin/env python3
"""
风险控制器 - Risk Controller
止损、仓位控制、行业分散
"""

import pandas as pd
import numpy as np

class RiskController:
    """风险控制器"""
    
    def __init__(self):
        self.config = {
            'stop_loss': -0.05,  # 止损位 -5%
            'max_position': 0.20,  # 单只最大仓位 20%
            'max_industry': 0.30,  # 单行业最大仓位 30%
            'max_stocks': 10  # 最大持股数
        }
    
    def apply_risk_control(self, df):
        """
        应用风险控制
        
        Args:
            df: 选股结果
        
        Returns:
            DataFrame: 风险控制后的结果
        """
        # 1. 限制持股数量
        if len(df) > self.config['max_stocks']:
            df = df.head(self.config['max_stocks'])
        
        # 2. 计算建议仓位
        df['position'] = 1.0 / len(df)  # 等权重
        
        # 3. 检查单只仓位限制
        df['position'] = df['position'].clip(upper=self.config['max_position'])
        
        # 4. 添加止损位
        df['stop_loss'] = self.config['stop_loss']
        
        print(f"  选股数量：{len(df)}")
        print(f"  单只仓位：{df['position'].iloc[0]:.1%}")
        print(f"  止损位：{self.config['stop_loss']:.1%}")
        
        return df
    
    def calculate_position(self, capital, stock_count):
        """
        计算仓位
        
        Args:
            capital: 总资金
            stock_count: 持股数量
        
        Returns:
            float: 单只股票仓位
        """
        base_position = 1.0 / stock_count
        position = min(base_position, self.config['max_position'])
        return position * capital


if __name__ == "__main__":
    ctrl = RiskController()
    print("风险控制器测试")
    print("配置：", ctrl.config)
