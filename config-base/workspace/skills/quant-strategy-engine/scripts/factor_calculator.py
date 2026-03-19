#!/usr/bin/env python3
"""
因子计算器 - Factor Calculator
计算 6 大类因子：估值/成长/动量/质量/技术/资金
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

class FactorCalculator:
    """因子计算器"""
    
    def __init__(self):
        self.storage = None  # 延迟初始化
    
    def _init_storage(self):
        """初始化数据存储器"""
        if self.storage is None:
            from data_storage import DataStorage
            self.storage = DataStorage()
    
    def calculate_all_factors(self, stock_list, trade_date):
        """
        计算所有因子
        
        Args:
            stock_list: 股票代码列表
            trade_date: 交易日期
        
        Returns:
            DataFrame: 因子得分
        """
        self._init_storage()
        
        results = []
        
        for i, ts_code in enumerate(stock_list[:50]):  # 先测试前 50 只
            try:
                # 获取数据
                daily_df = self.storage.get_daily_data(ts_code, '20260101', trade_date)
                
                if daily_df is None or len(daily_df) < 60:
                    continue
                
                # 计算各类因子
                valuation_score = self._calculate_valuation(ts_code, trade_date)
                growth_score = self._calculate_growth(ts_code, trade_date)
                momentum_score = self._calculate_momentum(daily_df)
                quality_score = self._calculate_quality(ts_code, trade_date)
                technical_score = self._calculate_technical(daily_df)
                moneyflow_score = self._calculate_moneyflow(ts_code, trade_date)
                
                results.append({
                    'ts_code': ts_code,
                    'name': ts_code.split('.')[0],  # 临时用代码代替
                    'trade_date': trade_date,
                    'valuation_score': valuation_score,
                    'growth_score': growth_score,
                    'momentum_score': momentum_score,
                    'quality_score': quality_score,
                    'technical_score': technical_score,
                    'moneyflow_score': moneyflow_score
                })
                
                if (i + 1) % 10 == 0:
                    print(f"  已计算 {i+1}/{len(stock_list[:50])} 只股票")
                
            except Exception as e:
                print(f"⚠️  {ts_code} 计算失败：{e}")
                continue
        
        return pd.DataFrame(results)
    
    def _calculate_valuation(self, ts_code, trade_date):
        """估值因子"""
        # TODO: 从基本面数据计算 PE、PB、PS
        # 临时返回随机值
        return np.random.uniform(50, 100)
    
    def _calculate_growth(self, ts_code, trade_date):
        """成长因子"""
        # TODO: 从财务数据计算增长率
        # 临时返回随机值
        return np.random.uniform(50, 100)
    
    def _calculate_momentum(self, daily_df):
        """动量因子"""
        if len(daily_df) < 60:
            return 50
        
        close = daily_df['close'].values
        
        # 5 日涨幅
        if len(close) >= 5:
            momentum_5d = ((close[-1] - close[-5]) / close[-5]) * 100
        else:
            momentum_5d = 0
        
        # 20 日涨幅
        if len(close) >= 20:
            momentum_20d = ((close[-1] - close[-20]) / close[-20]) * 100
        else:
            momentum_20d = 0
        
        # 标准化得分
        score = (momentum_5d + momentum_20d * 2) / 3
        score = min(max(score, 0), 100)  # 限制在 0-100
        
        return score
    
    def _calculate_quality(self, ts_code, trade_date):
        """质量因子"""
        # TODO: 从财务数据计算 ROE、ROA
        # 临时返回随机值
        return np.random.uniform(50, 100)
    
    def _calculate_technical(self, daily_df):
        """技术因子"""
        if len(daily_df) < 30:
            return 50
        
        close = daily_df['close'].values
        
        # RSI
        if len(close) >= 14:
            gains = []
            losses = []
            for i in range(1, min(15, len(close))):
                change = close[i] - close[i-1]
                if change > 0:
                    gains.append(change)
                    losses.append(0)
                else:
                    gains.append(0)
                    losses.append(abs(change))
            
            avg_gain = sum(gains) / len(gains) if gains else 0
            avg_loss = sum(losses) / len(losses) if losses else 1
            rs = avg_gain / avg_loss if avg_loss != 0 else 0
            rsi = 100 - (100 / (1 + rs))
        else:
            rsi = 50
        
        # 标准化
        if rsi < 30:
            score = 30 + rsi  # 超卖，高分
        elif rsi > 70:
            score = 100 - rsi  # 超买，低分
        else:
            score = rsi  # 正常
        
        return score
    
    def _calculate_moneyflow(self, ts_code, trade_date):
        """资金因子"""
        # TODO: 从资金流向数据计算
        # 临时返回随机值
        return np.random.uniform(50, 100)


if __name__ == "__main__":
    calc = FactorCalculator()
    print("因子计算器测试")
    print("需要数据支持，跳过测试")
