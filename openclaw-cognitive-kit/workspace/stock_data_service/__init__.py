#!/usr/bin/env python3
"""
统一股票数据服务层 (stock_data_service)

核心功能：
1. 统一数据获取接口
2. 智能数据源路由
3. 统一缓存管理
4. 统一错误处理
5. 统一配置管理

使用示例：
    from stock_data_service import StockDataClient
    
    # 创建客户端
    client = StockDataClient()
    
    # 获取股票基本信息
    df = client.get_stock_basic("000001.SZ")
    
    # 获取日线数据
    df = client.get_daily_data("000001.SZ", start_date="20240101")
    
    # 获取统计信息
    stats = client.get_client_stats()
"""

from .config import StockDataConfig, default_config
from .client import StockDataClient, get_client
from .cache import StockDataCache, get_cache
from .utils import setup_logging, format_symbol, generate_cache_key

# 导出异常
from .exceptions import (
    StockDataError,
    DataSourceError,
    TushareError,
    AkShareError,
    BaoStockError,
    MootdxError,
    CacheError,
    ConfigError,
    ValidationError,
    RateLimitError,
    NetworkError,
    TimeoutError,
    NoDataError,
    ProviderNotAvailableError,
    AllSourcesFailedError,
)

__version__ = "1.0.0"
__author__ = "OpenClaw Team"
__description__ = "统一股票数据服务层"

__all__ = [
    # 主要类
    "StockDataConfig",
    "StockDataClient",
    "StockDataCache",
    
    # 工厂函数
    "get_client",
    "get_cache",
    
    # 工具函数
    "setup_logging",
    "format_symbol",
    "generate_cache_key",
    
    # 异常
    "StockDataError",
    "DataSourceError",
    "TushareError",
    "AkShareError",
    "BaoStockError",
    "MootdxError",
    "CacheError",
    "ConfigError",
    "ValidationError",
    "RateLimitError",
    "NetworkError",
    "TimeoutError",
    "NoDataError",
    "ProviderNotAvailableError",
    "AllSourcesFailedError",
]