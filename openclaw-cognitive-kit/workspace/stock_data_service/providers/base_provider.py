#!/usr/bin/env python3
"""
基础数据提供器抽象类
"""

import abc
import logging
from typing import Optional, Dict, Any
import pandas as pd

from ..exceptions import DataSourceError
from ..utils import retry_on_failure, validate_dataframe


class BaseDataProvider(abc.ABC):
    """基础数据提供器抽象类"""
    
    def __init__(self, name: str, config: Dict[str, Any] = None):
        """
        初始化数据提供器
        
        Args:
            name: 提供器名称
            config: 配置字典
        """
        self.name = name
        self.config = config or {}
        self.logger = logging.getLogger(f"stock_data_service.provider.{name}")
        self.is_available = True
        self.last_error = None
        self.stats = {
            "calls": 0,
            "success": 0,
            "errors": 0,
            "total_time": 0.0,
        }
    
    @abc.abstractmethod
    def get_stock_basic(self, symbol: Optional[str] = None, **kwargs) -> Optional[pd.DataFrame]:
        """获取股票基本信息"""
        pass
    
    @abc.abstractmethod
    def get_daily_data(self, symbol: str, start_date: Optional[str] = None, 
                      end_date: Optional[str] = None, **kwargs) -> Optional[pd.DataFrame]:
        """获取日线数据"""
        pass
    
    @abc.abstractmethod
    def check_availability(self) -> bool:
        """检查提供器是否可用"""
        pass
    
    def get_financials(self, symbol: str, **kwargs) -> Optional[pd.DataFrame]:
        """获取财务数据（可选实现）"""
        self.logger.warning(f"{self.name} 未实现 get_financials 方法")
        return None
    
    def get_news(self, symbol: Optional[str] = None, **kwargs) -> Optional[pd.DataFrame]:
        """获取新闻数据（可选实现）"""
        self.logger.warning(f"{self.name} 未实现 get_news 方法")
        return None
    
    def get_realtime(self, symbols: list, **kwargs) -> Optional[pd.DataFrame]:
        """获取实时行情（可选实现）"""
        self.logger.warning(f"{self.name} 未实现 get_realtime 方法")
        return None
    
    def update_stats(self, success: bool, execution_time: float):
        """更新统计信息"""
        self.stats["calls"] += 1
        self.stats["total_time"] += execution_time
        
        if success:
            self.stats["success"] += 1
            self.is_available = True
            self.last_error = None
        else:
            self.stats["errors"] += 1
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        avg_time = 0.0
        if self.stats["calls"] > 0:
            avg_time = self.stats["total_time"] / self.stats["calls"]
        
        success_rate = 0.0
        if self.stats["calls"] > 0:
            success_rate = self.stats["success"] / self.stats["calls"] * 100
        
        return {
            "name": self.name,
            "is_available": self.is_available,
            "calls": self.stats["calls"],
            "success": self.stats["success"],
            "errors": self.stats["errors"],
            "success_rate": f"{success_rate:.1f}%",
            "avg_time": f"{avg_time:.3f}s",
            "last_error": str(self.last_error) if self.last_error else None,
        }
    
    def __str__(self) -> str:
        """友好的字符串表示"""
        stats = self.get_stats()
        return (
            f"{self.name}Provider(\n"
            f"  可用性: {'✅' if self.is_available else '❌'}\n"
            f"  调用次数: {stats['calls']}\n"
            f"  成功率: {stats['success_rate']}\n"
            f"  平均时间: {stats['avg_time']}\n"
            f")"
        )


class RetryProvider(BaseDataProvider):
    """带重试功能的数据提供器"""
    
    def __init__(self, name: str, config: Dict[str, Any] = None):
        super().__init__(name, config)
        self.max_retries = config.get("max_retries", 3)
        self.retry_delay = config.get("retry_delay", 1)
    
    @retry_on_failure(max_retries=3, delay=1)
    def get_stock_basic(self, symbol: Optional[str] = None, **kwargs) -> Optional[pd.DataFrame]:
        """带重试的获取股票基本信息"""
        return super().get_stock_basic(symbol, **kwargs)
    
    @retry_on_failure(max_retries=3, delay=1)
    def get_daily_data(self, symbol: str, start_date: Optional[str] = None, 
                      end_date: Optional[str] = None, **kwargs) -> Optional[pd.DataFrame]:
        """带重试的获取日线数据"""
        return super().get_daily_data(symbol, start_date, end_date, **kwargs)