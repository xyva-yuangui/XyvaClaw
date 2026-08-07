#!/usr/bin/env python3
"""
统一股票数据服务异常定义
"""


class StockDataError(Exception):
    """股票数据服务基础异常"""
    pass


class DataSourceError(StockDataError):
    """数据源异常"""
    pass


class TushareError(DataSourceError):
    """Tushare数据源异常"""
    pass


class AkShareError(DataSourceError):
    """AkShare数据源异常"""
    pass


class BaoStockError(DataSourceError):
    """BaoStock数据源异常"""
    pass


class MootdxError(DataSourceError):
    """mootdx数据源异常"""
    pass


class CacheError(StockDataError):
    """缓存异常"""
    pass


class ConfigError(StockDataError):
    """配置异常"""
    pass


class ValidationError(StockDataError):
    """数据验证异常"""
    pass


class RateLimitError(StockDataError):
    """速率限制异常"""
    pass


class NetworkError(StockDataError):
    """网络异常"""
    pass


class TimeoutError(StockDataError):
    """超时异常"""
    pass


class NoDataError(StockDataError):
    """无数据异常"""
    pass


class ProviderNotAvailableError(DataSourceError):
    """数据提供器不可用异常"""
    pass


class AllSourcesFailedError(StockDataError):
    """所有数据源都失败异常"""
    
    def __init__(self, errors: dict):
        self.errors = errors
        error_msgs = []
        for source, error in errors.items():
            error_msgs.append(f"{source}: {error}")
        
        super().__init__(f"所有数据源均失败:\n" + "\n".join(error_msgs))