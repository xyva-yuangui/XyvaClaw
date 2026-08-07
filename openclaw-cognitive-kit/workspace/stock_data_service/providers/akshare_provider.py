#!/usr/bin/env python3
"""
AkShare数据提供器
"""

import time
import logging
from typing import Optional, Dict, Any
import pandas as pd

from .base_provider import BaseDataProvider
from ..exceptions import AkShareError
from ..utils import retry_on_failure, format_symbol, parse_symbol, validate_dataframe


class AkShareProvider(BaseDataProvider):
    """AkShare数据提供器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化AkShare提供器
        
        Args:
            config: 配置字典
        """
        config = config or {}
        super().__init__("akshare", config)
        
        # 初始化AkShare客户端
        self._init_client()
    
    def _init_client(self):
        """初始化AkShare客户端"""
        try:
            import akshare as ak
            self.ak = ak
            
            # 测试连接
            self._test_connection()
            
        except ImportError:
            self.logger.error("未安装akshare库，请运行: pip install akshare")
            self.is_available = False
        except Exception as e:
            self.logger.error(f"初始化AkShare客户端失败: {e}")
            self.is_available = False
            self.last_error = str(e)
    
    def _test_connection(self):
        """测试连接"""
        try:
            start_time = time.time()
            # 简单查询测试
            df = self.ak.stock_zh_a_spot_em()
            execution_time = time.time() - start_time
            
            if validate_dataframe(df):
                self.is_available = True
                self.logger.info(f"AkShare连接测试成功，获取{len(df)}只股票，响应时间: {execution_time:.2f}s")
                self.update_stats(True, execution_time)
            else:
                self.is_available = False
                self.logger.error("AkShare连接测试返回空数据")
                self.update_stats(False, execution_time)
                
        except Exception as e:
            self.is_available = False
            self.last_error = str(e)
            self.logger.error(f"AkShare连接测试失败: {e}")
            self.update_stats(False, 0)
    
    def check_availability(self) -> bool:
        """检查提供器是否可用"""
        return self.is_available
    
    @retry_on_failure(max_retries=3, delay=1, exceptions=(Exception,))
    def get_stock_basic(self, symbol: Optional[str] = None, **kwargs) -> Optional[pd.DataFrame]:
        """获取股票基本信息"""
        if not self.check_availability():
            self.logger.warning("AkShare提供器不可用")
            return None
        
        try:
            start_time = time.time()
            
            if symbol:
                # 获取单个股票信息
                symbol_info = parse_symbol(symbol)
                code = symbol_info["code"]
                
                # 尝试多种方式获取股票信息
                df = None
                
                # 方法1: 从实时行情中筛选
                try:
                    spot_df = self.ak.stock_zh_a_spot_em()
                    if not spot_df.empty:
                        df = spot_df[spot_df["代码"] == code]
                except:
                    pass
                
                # 方法2: 使用个股信息接口
                if df is None or df.empty:
                    try:
                        df = self.ak.stock_individual_info_em(symbol=code)
                    except:
                        pass
                
            else:
                # 获取所有股票实时行情
                df = self.ak.stock_zh_a_spot_em()
            
            execution_time = time.time() - start_time
            
            if validate_dataframe(df):
                self.update_stats(True, execution_time)
                self.logger.info(f"获取股票基本信息成功: {len(df)}条，耗时: {execution_time:.2f}s")
                return df
            else:
                self.update_stats(False, execution_time)
                self.logger.warning("获取股票基本信息返回空数据")
                return None
                
        except Exception as e:
            execution_time = time.time() - start_time if 'start_time' in locals() else 0
            self.update_stats(False, execution_time)
            self.last_error = str(e)
            self.logger.error(f"获取股票基本信息失败: {e}")
            return None
    
    @retry_on_failure(max_retries=3, delay=1, exceptions=(Exception,))
    def get_daily_data(self, symbol: str, start_date: Optional[str] = None, 
                      end_date: Optional[str] = None, **kwargs) -> Optional[pd.DataFrame]:
        """获取日线数据"""
        if not self.check_availability():
            self.logger.warning("AkShare提供器不可用")
            return None
        
        try:
            start_time = time.time()
            
            symbol_info = parse_symbol(symbol)
            code = symbol_info["code"]
            
            # 设置默认日期
            if not start_date:
                start_date = "20240101"  # 默认今年开始
            
            if not end_date:
                from datetime import datetime
                end_date = datetime.now().strftime("%Y%m%d")
            
            # 转换日期格式
            start_date_fmt = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}"
            end_date_fmt = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}"
            
            df = None
            
            # 尝试多种方式获取日线数据
            try:
                # 方法1: A股日线数据
                if symbol_info["exchange"] in ["SH", "SZ"]:
                    df = self.ak.stock_zh_a_hist(
                        symbol=code,
                        period="daily",
                        start_date=start_date_fmt,
                        end_date=end_date_fmt,
                        adjust="qfq"  # 前复权
                    )
            except:
                pass
            
            # 方法2: 备用接口
            if df is None or df.empty:
                try:
                    df = self.ak.stock_zh_a_daily(
                        symbol=f"sh{code}" if symbol_info["exchange"] == "SH" else f"sz{code}",
                        start_date=start_date_fmt,
                        end_date=end_date_fmt,
                        adjust="qfq"
                    )
                except:
                    pass
            
            execution_time = time.time() - start_time
            
            if validate_dataframe(df):
                # 重命名列以保持一致性
                if "日期" in df.columns:
                    df = df.rename(columns={"日期": "trade_date"})
                if "收盘" in df.columns:
                    df = df.rename(columns={"收盘": "close"})
                if "开盘" in df.columns:
                    df = df.rename(columns={"开盘": "open"})
                if "最高" in df.columns:
                    df = df.rename(columns={"最高": "high"})
                if "最低" in df.columns:
                    df = df.rename(columns={"最低": "low"})
                if "成交量" in df.columns:
                    df = df.rename(columns={"成交量": "vol"})
                if "成交额" in df.columns:
                    df = df.rename(columns={"成交额": "amount"})
                
                # 按日期排序
                if "trade_date" in df.columns:
                    df = df.sort_values("trade_date")
                
                self.update_stats(True, execution_time)
                self.logger.info(f"获取日线数据成功: {len(df)}条，耗时: {execution_time:.2f}s")
                return df
            else:
                self.update_stats(False, execution_time)
                self.logger.warning("获取日线数据返回空数据")
                return None
                
        except Exception as e:
            execution_time = time.time() - start_time if 'start_time' in locals() else 0
            self.update_stats(False, execution_time)
            self.last_error = str(e)
            self.logger.error(f"获取日线数据失败: {e}")
            return None
    
    def get_realtime(self, symbols: list, **kwargs) -> Optional[pd.DataFrame]:
        """获取实时行情"""
        if not self.check_availability():
            self.logger.warning("AkShare提供器不可用")
            return None
        
        try:
            start_time = time.time()
            
            # 获取所有A股实时行情
            df = self.ak.stock_zh_a_spot_em()
            
            # 如果指定了symbols，进行筛选
            if symbols:
                symbol_codes = [parse_symbol(s)["code"] for s in symbols]
                df = df[df["代码"].isin(symbol_codes)]
            
            execution_time = time.time() - start_time
            
            if validate_dataframe(df):
                self.update_stats(True, execution_time)
                self.logger.info(f"获取实时行情成功: {len(df)}条，耗时: {execution_time:.2f}s")
                return df
            else:
                self.update_stats(False, execution_time)
                self.logger.warning("获取实时行情返回空数据")
                return None
                
        except Exception as e:
            execution_time = time.time() - start_time if 'start_time' in locals() else 0
            self.update_stats(False, execution_time)
            self.last_error = str(e)
            self.logger.error(f"获取实时行情失败: {e}")
            return None
    
    def __str__(self) -> str:
        """友好的字符串表示"""
        stats = self.get_stats()
        return (
            f"AkShareProvider(\n"
            f"  可用性: {'✅' if self.is_available else '❌'}\n"
            f"  调用次数: {stats['calls']}\n"
            f"  成功率: {stats['success_rate']}\n"
            f"  平均时间: {stats['avg_time']}\n"
            f")"
        )