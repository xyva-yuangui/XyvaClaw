#!/usr/bin/env python3
"""
数据获取模块 - Data Fetcher
从 Tushare、mootdx 获取 A 股数据
"""

import tushare as ts
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import time
import sys

class DataFetcher:
    """数据获取器"""
    
    def __init__(self):
        # Tushare 配置
        self.token = "a2bd39d0aa6e6cd26729e7e3a6cddccb85b255ca0a9da996150191a9f14b"
        self.pro = ts.pro_api(self.token)
        self.pro._DataApi__token = self.token
        self.pro._DataApi__http_url = '__TUSHARE_HTTP_URL__'
        
        # mootdx 配置
        self.mootdx_client = None
        self._init_mootdx()
        
        # 重试配置
        self.max_retries = 3
        self.retry_delay = 1  # 秒
    
    def _init_mootdx(self):
        """初始化 mootdx"""
        try:
            from mootdx.quotes import Quotes
            self.mootdx_client = Quotes.factory(market="std", timeout=10)
            print("✅ mootdx 初始化成功")
        except Exception as e:
            print(f"⚠️  mootdx 初始化失败：{e}")
            self.mootdx_client = None
    
    def fetch_daily_data(self, ts_code, start_date, end_date, retry=0):
        """
        获取日线数据
        
        Args:
            ts_code: 股票代码 (000001.SZ)
            start_date: 开始日期 (20260101)
            end_date: 结束日期 (20260309)
            retry: 重试次数
        
        Returns:
            DataFrame: 日线数据
        """
        try:
            df = self.pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
            
            if df is not None and len(df) > 0:
                # 数据验证
                required_columns = ['ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'vol', 'amount', 'pct_chg']
                if all(col in df.columns for col in required_columns):
                    print(f"✅ 获取 {ts_code} 日线数据 {len(df)} 条")
                    return df
                else:
                    print(f"⚠️  {ts_code} 数据列不完整")
                    return None
            else:
                print(f"⚠️  {ts_code} 数据为空")
                return None
                
        except Exception as e:
            if retry < self.max_retries:
                print(f"⚠️  {ts_code} 获取失败，{self.retry_delay}秒后重试 ({retry+1}/{self.max_retries})")
                time.sleep(self.retry_delay)
                return self.fetch_daily_data(ts_code, start_date, end_date, retry + 1)
            else:
                print(f"❌ {ts_code} 获取失败：{e}")
                return None
    
    def fetch_daily_basic(self, ts_code, trade_date, retry=0):
        """
        获取基本面数据
        
        Args:
            ts_code: 股票代码
            trade_date: 交易日期
        
        Returns:
            DataFrame: 基本面数据
        """
        try:
            df = self.pro.daily_basic(ts_code=ts_code, trade_date=trade_date)
            
            if df is not None and len(df) > 0:
                print(f"✅ 获取 {ts_code} 基本面数据")
                return df
            else:
                return None
                
        except Exception as e:
            if retry < self.max_retries:
                time.sleep(self.retry_delay)
                return self.fetch_daily_basic(ts_code, trade_date, retry + 1)
            else:
                print(f"❌ {ts_code} 基本面数据获取失败：{e}")
                return None
    
    def fetch_fina_indicator(self, ts_code, start_date, end_date, retry=0):
        """
        获取财务指标
        
        Args:
            ts_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            DataFrame: 财务指标
        """
        try:
            df = self.pro.fina_indicator(ts_code=ts_code, start_date=start_date, end_date=end_date)
            
            if df is not None and len(df) > 0:
                print(f"✅ 获取 {ts_code} 财务指标 {len(df)} 条")
                return df
            else:
                return None
                
        except Exception as e:
            if retry < self.max_retries:
                time.sleep(self.retry_delay)
                return self.fetch_fina_indicator(ts_code, start_date, end_date, retry + 1)
            else:
                print(f"❌ {ts_code} 财务指标获取失败：{e}")
                return None
    
    def fetch_moneyflow(self, ts_code, start_date, end_date, retry=0):
        """
        获取资金流向
        
        Args:
            ts_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            DataFrame: 资金流向
        """
        try:
            df = self.pro.moneyflow(ts_code=ts_code, start_date=start_date, end_date=end_date)
            
            if df is not None and len(df) > 0:
                print(f"✅ 获取 {ts_code} 资金流向 {len(df)} 条")
                return df
            else:
                return None
                
        except Exception as e:
            if retry < self.max_retries:
                time.sleep(self.retry_delay)
                return self.fetch_moneyflow(ts_code, start_date, end_date, retry + 1)
            else:
                print(f"❌ {ts_code} 资金流向获取失败：{e}")
                return None
    
    def fetch_realtime_quote(self, ts_code):
        """
        获取实时行情（mootdx）
        
        Args:
            ts_code: 股票代码
        
        Returns:
            dict: 实时行情
        """
        if self.mootdx_client is None:
            print("❌ mootdx 未初始化")
            return None
        
        try:
            market = 1 if ts_code.startswith("6") else 0
            code = ts_code.split(".")[0]
            quote = self.mootdx_client.quote(market, code)
            
            if quote:
                print(f"✅ 获取 {ts_code} 实时行情")
                return quote
            else:
                return None
                
        except Exception as e:
            print(f"❌ {ts_code} 实时行情获取失败：{e}")
            return None
    
    def get_stock_list(self):
        """
        获取全部 A 股列表
        
        Returns:
            DataFrame: 股票列表
        """
        try:
            df = self.pro.stock_basic(
                exchange='',
                list_status='L',
                fields='ts_code,symbol,name,area,industry,list_date,market'
            )
            
            if df is not None and len(df) > 0:
                print(f"✅ 获取 A 股列表 {len(df)} 只")
                return df
            else:
                print("❌ A 股列表获取失败")
                return None
                
        except Exception as e:
            print(f"❌ A 股列表获取失败：{e}")
            return None
    
    def batch_fetch_daily(self, stock_list, start_date, end_date, batch_size=100):
        """
        批量获取日线数据
        
        Args:
            stock_list: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            batch_size: 批次大小
        
        Returns:
            DataFrame: 所有股票的日线数据
        """
        all_data = []
        total = len(stock_list)
        
        print(f"\n开始批量获取日线数据，共 {total} 只股票...")
        
        for i in range(0, total, batch_size):
            batch = stock_list[i:i+batch_size]
            print(f"\n批次 {i//batch_size + 1}/{(total + batch_size - 1)//batch_size}")
            
            for ts_code in batch:
                df = self.fetch_daily_data(ts_code, start_date, end_date)
                if df is not None:
                    all_data.append(df)
                
                # 避免请求过快
                time.sleep(0.1)
        
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            print(f"\n✅ 批量获取完成，共 {len(combined_df)} 条数据")
            return combined_df
        else:
            print("\n❌ 批量获取失败")
            return None


# 测试
if __name__ == "__main__":
    fetcher = DataFetcher()
    
    # 测试获取股票列表
    print("=" * 70)
    print("测试 1: 获取 A 股列表")
    print("=" * 70)
    stock_list = fetcher.get_stock_list()
    if stock_list is not None:
        print(stock_list.head())
    
    # 测试获取日线数据
    print("\n" + "=" * 70)
    print("测试 2: 获取日线数据")
    print("=" * 70)
    df = fetcher.fetch_daily_data("000001.SZ", "20260301", "20260309")
    if df is not None:
        print(df.head())
    
    # 测试获取基本面数据
    print("\n" + "=" * 70)
    print("测试 3: 获取基本面数据")
    print("=" * 70)
    basic_df = fetcher.fetch_daily_basic("000001.SZ", "20260309")
    if basic_df is not None:
        print(basic_df)
    
    print("\n" + "=" * 70)
    print("✅ 数据获取模块测试完成")
    print("=" * 70)
