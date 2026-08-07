#!/usr/bin/env python3
"""
Tushare 数据提供器（使用私有网关）
"""

import time
import logging
from typing import Optional, Dict, Any
import pandas as pd

from .base_provider import BaseDataProvider
from ..exceptions import TushareError
from ..utils import retry_on_failure, format_symbol, parse_symbol, validate_dataframe


class TushareProvider(BaseDataProvider):
    """Tushare 数据提供器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化 Tushare 提供器
        
        Args:
            config: 配置字典，包含 token 和 gateway_url
        """
        config = config or {}
        super().__init__("tushare", config)
        
        self.token = config.get("token", "")
        self.gateway_url = config.get("gateway_url", "")
        self.pro = None
        
        # 初始化 Tushare 客户端
        self._init_client()
    
    def _init_client(self):
        """初始化 Tushare 客户端"""
        try:
            import tushare as ts
            
            if not self.token:
                self.logger.error("Tushare token 未配置")
                self.is_available = False
                return
            
            # 设置 token
            ts.set_token(self.token)
            self.pro = ts.pro_api()
            
            # 设置私有网关
            if self.gateway_url:
                self.pro._DataApi__http_url = self.gateway_url
                self.logger.info(f"使用私有网关：{self.gateway_url}")
            
            # 测试连接
            self._test_connection()
            
        except ImportError:
            self.logger.error("未安装 tushare 库，请运行：pip install tushare")
            self.is_available = False
        except Exception as e:
            self.logger.error(f"初始化 Tushare 客户端失败：{e}")
            self.is_available = False
            self.last_error = str(e)
    
    def _test_connection(self):
        """测试连接"""
        try:
            start_time = time.time()
            # 简单查询测试
            df = self.pro.trade_cal(exchange='SSE', start_date='20240301', end_date='20240310')
            execution_time = time.time() - start_time
            
            if df is not None and not df.empty:
                self.is_available = True
                self.logger.info(f"Tushare 连接测试成功，响应时间：{execution_time:.2f}s")
                self.update_stats(True, execution_time)
            else:
                self.is_available = False
                self.logger.error("Tushare 连接测试返回空数据")
                self.update_stats(False, execution_time)
                
        except Exception as e:
            self.is_available = False
            self.last_error = str(e)
            self.logger.error(f"Tushare 连接测试失败：{e}")
            self.update_stats(False, 0)
    
    def check_availability(self) -> bool:
        """检查提供器是否可用"""
        if not self.is_available:
            # 尝试重新初始化
            self._init_client()
        return self.is_available
    
    @retry_on_failure(max_retries=3, delay=1, exceptions=(Exception,))
    def get_stock_basic(self, symbol: Optional[str] = None, **kwargs) -> Optional[pd.DataFrame]:
        """获取股票基本信息"""
        if not self.check_availability():
            self.logger.warning("Tushare 提供器不可用")
            return None
        
        try:
            start_time = time.time()
            
            if symbol:
                # 获取单个股票信息
                symbol_info = parse_symbol(symbol)
                # 只使用 ts_code 参数，避免 exchange 导致的问题
                query_params = {
                    "ts_code": symbol_info["full"],
                    **kwargs
                }
            else:
                # 获取所有股票信息 - 添加默认参数
                query_params = {
                    "exchange": "",
                    "list_status": "L",
                    **kwargs
                }
            
            # 移除 None 值
            query_params = {k: v for k, v in query_params.items() if v is not None}
            
            self.logger.debug(f"Tushare 查询参数：{query_params}")
            df = self.pro.stock_basic(**query_params)
            execution_time = time.time() - start_time
            
            if validate_dataframe(df):
                self.update_stats(True, execution_time)
                self.logger.info(f"获取股票基本信息成功：{len(df)}条，耗时：{execution_time:.2f}s")
                return df
            else:
                self.update_stats(False, execution_time)
                self.logger.warning(f"获取股票基本信息返回空数据，查询参数：{query_params}")
                return None
                
        except Exception as e:
            execution_time = time.time() - start_time if 'start_time' in locals() else 0
            self.update_stats(False, execution_time)
            self.last_error = str(e)
            self.logger.error(f"获取股票基本信息失败：{e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None
    
    @retry_on_failure(max_retries=3, delay=1, exceptions=(Exception,))
    def get_daily_data(self, symbol: str, start_date: Optional[str] = None, 
                      end_date: Optional[str] = None, **kwargs) -> Optional[pd.DataFrame]:
        """获取日线数据"""
        if not self.check_availability():
            self.logger.warning("Tushare 提供器不可用")
            return None
        
        try:
            start_time = time.time()
            
            symbol_info = parse_symbol(symbol)
            
            # 设置默认日期
            if not start_date:
                start_date = "20240101"  # 默认今年开始
            
            if not end_date:
                from datetime import datetime
                end_date = datetime.now().strftime("%Y%m%d")
            
            query_params = {
                "ts_code": symbol_info["full"],
                "start_date": start_date,
                "end_date": end_date,
                **kwargs
            }
            
            df = self.pro.daily(**query_params)
            execution_time = time.time() - start_time
            
            if validate_dataframe(df):
                # 按日期排序
                df = df.sort_values("trade_date")
                self.update_stats(True, execution_time)
                self.logger.info(f"获取日线数据成功：{len(df)}条，耗时：{execution_time:.2f}s")
                return df
            else:
                self.update_stats(False, execution_time)
                self.logger.warning("获取日线数据返回空数据")
                return None
                
        except Exception as e:
            execution_time = time.time() - start_time if 'start_time' in locals() else 0
            self.update_stats(False, execution_time)
            self.last_error = str(e)
            self.logger.error(f"获取日线数据失败：{e}")
            return None
    
    def get_financials(self, symbol: str, **kwargs) -> Optional[Dict[str, pd.DataFrame]]:
        """获取财务数据"""
        if not self.check_availability():
            self.logger.warning("Tushare 提供器不可用")
            return None
        
        try:
            start_time = time.time()
            symbol_info = parse_symbol(symbol)
            
            # 获取利润表
            income_df = self.pro.income(ts_code=symbol_info["full"], **kwargs)
            
            # 获取资产负债表
            balancesheet_df = self.pro.balancesheet(ts_code=symbol_info["full"], **kwargs)
            
            # 获取现金流量表
            cashflow_df = self.pro.cashflow(ts_code=symbol_info["full"], **kwargs)
            
            execution_time = time.time() - start_time
            
            # 合并财务数据
            financials = {
                "income": income_df,
                "balancesheet": balancesheet_df,
                "cashflow": cashflow_df,
            }
            
            self.update_stats(True, execution_time)
            self.logger.info(f"获取财务数据成功，耗时：{execution_time:.2f}s")
            return financials
            
        except Exception as e:
            execution_time = time.time() - start_time if 'start_time' in locals() else 0
            self.update_stats(False, execution_time)
            self.last_error = str(e)
            self.logger.error(f"获取财务数据失败：{e}")
            return None
    
    def get_moneyflow(self, symbol: str, start_date: Optional[str] = None, 
                      end_date: Optional[str] = None, **kwargs) -> Optional[pd.DataFrame]:
        """获取资金流向数据"""
        if not self.check_availability():
            self.logger.warning("Tushare 提供器不可用")
            return None
        
        try:
            start_time = time.time()
            symbol_info = parse_symbol(symbol)
            
            # 设置默认日期
            if not end_date:
                end_date = time.strftime("%Y%m%d")
            if not start_date:
                # 默认获取最近30天数据
                from datetime import datetime, timedelta
                end_dt = datetime.strptime(end_date, "%Y%m%d")
                start_dt = end_dt - timedelta(days=30)
                start_date = start_dt.strftime("%Y%m%d")
            
            # 获取资金流向数据
            df = self.pro.moneyflow(
                ts_code=symbol_info["full"],
                start_date=start_date,
                end_date=end_date,
                **kwargs
            )
            
            execution_time = time.time() - start_time
            
            if df is not None and not df.empty:
                self.update_stats(True, execution_time)
                self.logger.info(f"获取资金流向数据成功：{len(df)}条，耗时：{execution_time:.2f}s")
                return df
            else:
                self.update_stats(False, execution_time)
                self.logger.warning("资金流向数据返回为空")
                return None
                
        except Exception as e:
            execution_time = time.time() - start_time if 'start_time' in locals() else 0
            self.update_stats(False, execution_time)
            self.last_error = str(e)
            self.logger.error(f"获取资金流向数据失败：{e}")
            return None
    
    def get_fina_indicator(self, symbol: str, **kwargs) -> Optional[pd.DataFrame]:
        """获取财务指标数据"""
        if not self.check_availability():
            self.logger.warning("Tushare 提供器不可用")
            return None
        
        try:
            start_time = time.time()
            symbol_info = parse_symbol(symbol)
            
            # 获取财务指标
            df = self.pro.fina_indicator(ts_code=symbol_info["full"], **kwargs)
            
            execution_time = time.time() - start_time
            
            if df is not None and not df.empty:
                self.update_stats(True, execution_time)
                self.logger.info(f"获取财务指标成功：{len(df)}条，耗时：{execution_time:.2f}s")
                return df
            else:
                self.update_stats(False, execution_time)
                self.logger.warning("财务指标数据返回为空")
                return None
                
        except Exception as e:
            execution_time = time.time() - start_time if 'start_time' in locals() else 0
            self.update_stats(False, execution_time)
            self.last_error = str(e)
            self.logger.error(f"获取财务指标失败：{e}")
            return None
    
    def get_index_data(self, index_code: str, start_date: Optional[str] = None,
                      end_date: Optional[str] = None, **kwargs) -> Optional[pd.DataFrame]:
        """获取指数数据"""
        if not self.check_availability():
            self.logger.warning("Tushare 提供器不可用")
            return None
        
        try:
            start_time = time.time()
            
            # 设置默认日期
            if not end_date:
                end_date = time.strftime("%Y%m%d")
            if not start_date:
                # 默认获取最近90天数据
                from datetime import datetime, timedelta
                end_dt = datetime.strptime(end_date, "%Y%m%d")
                start_dt = end_dt - timedelta(days=90)
                start_date = start_dt.strftime("%Y%m%d")
            
            # 获取指数日线数据
            df = self.pro.index_daily(
                ts_code=index_code,
                start_date=start_date,
                end_date=end_date,
                **kwargs
            )
            
            execution_time = time.time() - start_time
            
            if df is not None and not df.empty:
                self.update_stats(True, execution_time)
                self.logger.info(f"获取指数数据成功：{len(df)}条，耗时：{execution_time:.2f}s")
                return df
            else:
                self.update_stats(False, execution_time)
                self.logger.warning("指数数据返回为空")
                return None
                
        except Exception as e:
            execution_time = time.time() - start_time if 'start_time' in locals() else 0
            self.update_stats(False, execution_time)
            self.last_error = str(e)
            self.logger.error(f"获取指数数据失败：{e}")
            return None
    
    def get_macro_data(self, indicator: str, **kwargs) -> Optional[pd.DataFrame]:
        """获取宏观数据"""
        if not self.check_availability():
            self.logger.warning("Tushare 提供器不可用")
            return None
        
        try:
            start_time = time.time()
            
            # 根据指标类型调用不同接口
            if indicator.lower() == "gdp":
                df = self.pro.cn_gdp(**kwargs)
            elif indicator.lower() == "cpi":
                df = self.pro.cn_cpi(**kwargs)
            elif indicator.lower() == "ppi":
                df = self.pro.cn_ppi(**kwargs)
            elif indicator.lower() == "m2":
                df = self.pro.cn_m(**kwargs)
            else:
                self.logger.error(f"不支持的宏观指标：{indicator}")
                return None
            
            execution_time = time.time() - start_time
            
            if df is not None and not df.empty:
                self.update_stats(True, execution_time)
                self.logger.info(f"获取宏观数据[{indicator}]成功：{len(df)}条，耗时：{execution_time:.2f}s")
                return df
            else:
                self.update_stats(False, execution_time)
                self.logger.warning(f"宏观数据[{indicator}]返回为空")
                return None
                
        except Exception as e:
            execution_time = time.time() - start_time if 'start_time' in locals() else 0
            self.update_stats(False, execution_time)
            self.last_error = str(e)
            self.logger.error(f"获取宏观数据[{indicator}]失败：{e}")
            return None
    
    def get_trade_calendar(self, exchange: str = "SSE", start_date: Optional[str] = None,
                          end_date: Optional[str] = None, **kwargs) -> Optional[pd.DataFrame]:
        """获取交易日历"""
        if not self.check_availability():
            self.logger.warning("Tushare 提供器不可用")
            return None
        
        try:
            start_time = time.time()
            
            # 设置默认日期（当前月份）
            if not end_date:
                end_date = time.strftime("%Y%m%d")
            if not start_date:
                # 默认获取当前月份
                start_date = end_date[:6] + "01"
            
            df = self.pro.trade_cal(
                exchange=exchange,
                start_date=start_date,
                end_date=end_date,
                **kwargs
            )
            
            execution_time = time.time() - start_time
            
            if df is not None and not df.empty:
                self.update_stats(True, execution_time)
                self.logger.info(f"获取交易日历成功：{len(df)}条，耗时：{execution_time:.2f}s")
                return df
            else:
                self.update_stats(False, execution_time)
                self.logger.warning("交易日历返回为空")
                return None
                
        except Exception as e:
            execution_time = time.time() - start_time if 'start_time' in locals() else 0
            self.update_stats(False, execution_time)
            self.last_error = str(e)
            self.logger.error(f"获取交易日历失败：{e}")
            return None
    
    def get_news(self, **kwargs) -> Optional[pd.DataFrame]:
        """获取新闻数据（Tushare网关可能有限制）"""
        if not self.check_availability():
            self.logger.warning("Tushare 提供器不可用")
            return None
        
        try:
            start_time = time.time()
            
            # 尝试获取新闻数据
            df = self.pro.news(**kwargs)
            
            execution_time = time.time() - start_time
            
            if df is not None and not df.empty:
                self.update_stats(True, execution_time)
                self.logger.info(f"获取新闻数据成功：{len(df)}条，耗时：{execution_time:.2f}s")
                return df
            else:
                self.update_stats(False, execution_time)
                self.logger.warning("新闻数据返回为空")
                return None
                
        except Exception as e:
            execution_time = time.time() - start_time if 'start_time' in locals() else 0
            self.update_stats(False, execution_time)
            self.last_error = str(e)
            self.logger.error(f"获取新闻数据失败：{e}")
            return None
    
    def get_realtime(self, symbol: str, **kwargs) -> Optional[pd.DataFrame]:
        """获取实时数据（Tushare网关不支持，返回None）"""
        self.logger.warning("Tushare 私有网关不支持实时数据接口")
        return None
    
    def get_stats(self, **kwargs) -> Optional[pd.DataFrame]:
        """获取统计数据"""
        # 这里可以添加其他统计数据的获取
        # 例如：融资融券、股东人数、龙虎榜等
        self.logger.info("get_stats 方法待实现")
        return None
    
    def __str__(self) -> str:
        """友好的字符串表示"""
        stats = self.get_stats()
        gateway_info = f"网关：{self.gateway_url}" if self.gateway_url else "使用官方 API"
        return (
            f"TushareProvider(\n"
            f"  可用性：{'✅' if self.is_available else '❌'}\n"
            f"  {gateway_info}\n"
            f"  调用次数：{stats['calls']}\n"
            f"  成功率：{stats['success_rate']}\n"
            f")"
        )
