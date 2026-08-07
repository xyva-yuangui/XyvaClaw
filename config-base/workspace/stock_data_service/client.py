#!/usr/bin/env python3
"""
统一股票数据服务客户端
"""

import time
import logging
from typing import Optional, Dict, Any, List
import pandas as pd

from .config import StockDataConfig, default_config
from .cache import StockDataCache, get_cache
from .utils import setup_logging, format_symbol, generate_cache_key, retry_on_failure
from .exceptions import (
    StockDataError, AllSourcesFailedError, NoDataError,
    ProviderNotAvailableError
)

# 导入提供器
from .providers.tushare_provider import TushareProvider
from .providers.akshare_provider import AkShareProvider
from .providers.baostock_provider import BaoStockProvider
from .providers.mootdx_provider import MootdxProvider


class StockDataClient:
    """统一股票数据客户端"""
    
    def __init__(self, config: Optional[StockDataConfig] = None):
        """
        初始化统一股票数据客户端
        
        Args:
            config: 配置对象，如果为None则使用默认配置
        """
        self.config = config or default_config
        self.cache = get_cache(self.config.cache_dir, self.config.cache_ttl)
        
        # 设置日志
        self.logger = setup_logging(self.config.log_level, self.config.log_file)
        self.logger.info(f"初始化StockDataClient，配置: {self.config}")
        
        # 初始化提供器
        self.providers = self._init_providers()
        self.logger.info(f"已初始化 {len(self.providers)} 个数据提供器")
        
        # 客户端统计
        self.stats = {
            "total_calls": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "provider_calls": {},
            "errors": 0,
        }
    
    def _init_providers(self) -> Dict[str, Any]:
        """初始化数据提供器"""
        providers = {}
        
        # Tushare提供器
        tushare_config = {
            "token": self.config.tushare_token,
            "gateway_url": self.config.tushare_gateway,
            "max_retries": self.config.max_retries,
            "retry_delay": self.config.retry_delay,
            "timeout": self.config.timeout,
        }
        providers["tushare"] = TushareProvider(tushare_config)
        
        # AkShare提供器
        providers["akshare"] = AkShareProvider({
            "max_retries": self.config.max_retries,
            "retry_delay": self.config.retry_delay,
            "timeout": self.config.timeout,
        })
        
        # BaoStock提供器（如果可用）
        try:
            providers["baostock"] = BaoStockProvider({
                "max_retries": self.config.max_retries,
                "retry_delay": self.config.retry_delay,
                "timeout": self.config.timeout,
            })
        except ImportError:
            self.logger.warning("BaoStock提供器不可用，未安装baostock库")
        
        # mootdx提供器（如果可用）
        try:
            providers["mootdx"] = MootdxProvider({
                "max_retries": self.config.max_retries,
                "retry_delay": self.config.retry_delay,
                "timeout": self.config.timeout,
            })
        except ImportError:
            self.logger.warning("mootdx提供器不可用，未安装mootdx库")
        
        return providers
    
    def get_stock_basic(self, symbol: Optional[str] = None, 
                       use_cache: bool = True, **kwargs) -> Optional[pd.DataFrame]:
        """
        获取股票基本信息
        
        Args:
            symbol: 股票代码，如"000001.SZ"或"000001"，None表示获取所有
            use_cache: 是否使用缓存
            **kwargs: 其他参数传递给提供器
        
        Returns:
            DataFrame包含股票基本信息，失败返回None
        """
        self.stats["total_calls"] += 1
        
        # 生成缓存键
        cache_key = generate_cache_key("get_stock_basic", symbol=symbol, **kwargs)
        
        # 检查缓存
        if use_cache and self.config.cache_enabled:
            cached_data = self.cache.get(cache_key, "basic")
            if cached_data is not None:
                self.stats["cache_hits"] += 1
                self.logger.debug(f"缓存命中: {cache_key}")
                return cached_data
        
        self.stats["cache_misses"] += 1
        
        # 按优先级尝试数据源
        errors = {}
        for source_name in self.config.data_source_priority:
            if source_name not in self.providers:
                continue
            
            provider = self.providers[source_name]
            
            # 检查提供器是否可用
            if not provider.check_availability():
                self.logger.debug(f"{source_name} 提供器不可用，跳过")
                continue
            
            try:
                start_time = time.time()
                self.logger.debug(f"尝试使用 {source_name} 获取股票基本信息...")
                
                # 调用提供器
                df = provider.get_stock_basic(symbol, **kwargs)
                execution_time = time.time() - start_time
                
                if df is not None and not df.empty:
                    self.logger.info(f"{source_name} 获取股票基本信息成功: {len(df)}条，耗时: {execution_time:.2f}s")
                    
                    # 更新提供器调用统计
                    if source_name not in self.stats["provider_calls"]:
                        self.stats["provider_calls"][source_name] = 0
                    self.stats["provider_calls"][source_name] += 1
                    
                    # 缓存结果
                    if use_cache and self.config.cache_enabled:
                        self.cache.set(cache_key, df, "basic")
                    
                    return df
                else:
                    self.logger.warning(f"{source_name} 返回空数据")
                    
            except Exception as e:
                errors[source_name] = str(e)
                self.logger.warning(f"{source_name} 获取失败: {e}")
                continue
        
        # 所有数据源都失败
        self.stats["errors"] += 1
        error_msg = f"获取股票基本信息失败"
        if symbol:
            error_msg += f" (symbol: {symbol})"
        
        if errors:
            error_msg += f"，错误详情: {errors}"
        
        self.logger.error(error_msg)
        return None
    
    def get_daily_data(self, symbol: str, start_date: Optional[str] = None,
                      end_date: Optional[str] = None, use_cache: bool = True,
                      **kwargs) -> Optional[pd.DataFrame]:
        """
        获取日线数据
        
        Args:
            symbol: 股票代码，如"000001.SZ"或"000001"
            start_date: 开始日期，格式"YYYYMMDD"
            end_date: 结束日期，格式"YYYYMMDD"
            use_cache: 是否使用缓存
            **kwargs: 其他参数传递给提供器
        
        Returns:
            DataFrame包含日线数据，失败返回None
        """
        self.stats["total_calls"] += 1
        
        # 格式化股票代码
        symbol = format_symbol(symbol)
        
        # 生成缓存键
        cache_key = generate_cache_key("get_daily_data", 
                                      symbol=symbol, 
                                      start_date=start_date,
                                      end_date=end_date,
                                      **kwargs)
        
        # 检查缓存
        if use_cache and self.config.cache_enabled:
            cached_data = self.cache.get(cache_key, "daily")
            if cached_data is not None:
                self.stats["cache_hits"] += 1
                self.logger.debug(f"缓存命中: {cache_key}")
                return cached_data
        
        self.stats["cache_misses"] += 1
        
        # 按优先级尝试数据源
        errors = {}
        for source_name in self.config.data_source_priority:
            if source_name not in self.providers:
                continue
            
            provider = self.providers[source_name]
            
            # 检查提供器是否可用
            if not provider.check_availability():
                self.logger.debug(f"{source_name} 提供器不可用，跳过")
                continue
            
            try:
                start_time = time.time()
                self.logger.debug(f"尝试使用 {source_name} 获取日线数据...")
                
                # 调用提供器
                df = provider.get_daily_data(symbol, start_date, end_date, **kwargs)
                execution_time = time.time() - start_time
                
                if df is not None and not df.empty:
                    self.logger.info(f"{source_name} 获取日线数据成功: {len(df)}条，耗时: {execution_time:.2f}s")
                    
                    # 更新提供器调用统计
                    if source_name not in self.stats["provider_calls"]:
                        self.stats["provider_calls"][source_name] = 0
                    self.stats["provider_calls"][source_name] += 1
                    
                    # 缓存结果
                    if use_cache and self.config.cache_enabled:
                        self.cache.set(cache_key, df, "daily")
                    
                    return df
                else:
                    self.logger.warning(f"{source_name} 返回空数据")
                    
            except Exception as e:
                errors[source_name] = str(e)
                self.logger.warning(f"{source_name} 获取失败: {e}")
                continue
        
        # 所有数据源都失败
        self.stats["errors"] += 1
        error_msg = f"获取日线数据失败 (symbol: {symbol})"
        if errors:
            error_msg += f"，错误详情: {errors}"
        
        self.logger.error(error_msg)
        return None
    
    def get_financials(self, symbol: str, use_cache: bool = True,
                      **kwargs) -> Optional[Dict[str, pd.DataFrame]]:
        """
        获取财务数据
        
        Args:
            symbol: 股票代码
            use_cache: 是否使用缓存
            **kwargs: 其他参数
        
        Returns:
            包含利润表、资产负债表、现金流量表的字典
        """
        # 目前主要使用Tushare获取财务数据
        if "tushare" not in self.providers:
            self.logger.error("Tushare提供器不可用，无法获取财务数据")
            return None
        
        provider = self.providers["tushare"]
        if not provider.check_availability():
            self.logger.error("Tushare提供器不可用")
            return None
        
        try:
            return provider.get_financials(symbol, **kwargs)
        except Exception as e:
            self.logger.error(f"获取财务数据失败: {e}")
            return None
    
    def get_realtime(self, symbols: List[str], **kwargs) -> Optional[pd.DataFrame]:
        """
        获取实时行情
        
        Args:
            symbols: 股票代码列表
            **kwargs: 其他参数
        
        Returns:
            实时行情DataFrame
        """
        # 尝试使用支持实时数据的提供器
        for source_name in ["akshare", "mootdx"]:
            if source_name in self.providers:
                provider = self.providers[source_name]
                if provider.check_availability():
                    try:
                        return provider.get_realtime(symbols, **kwargs)
                    except Exception as e:
                        self.logger.warning(f"{source_name} 获取实时行情失败: {e}")
                        continue
        
        self.logger.error("所有实时数据提供器都失败")
        return None
    
    def get_provider_stats(self) -> Dict[str, Dict]:
        """获取所有提供器的统计信息"""
        stats = {}
        for name, provider in self.providers.items():
            stats[name] = provider.get_stats()
        return stats
    
    def get_client_stats(self) -> Dict:
        """获取客户端统计信息"""
        cache_stats = self.cache.get_stats()
        
        # 计算缓存命中率
        total_cache_access = self.stats["cache_hits"] + self.stats["cache_misses"]
        cache_hit_rate = 0.0
        if total_cache_access > 0:
            cache_hit_rate = self.stats["cache_hits"] / total_cache_access * 100
        
        # 计算错误率
        error_rate = 0.0
        if self.stats["total_calls"] > 0:
            error_rate = self.stats["errors"] / self.stats["total_calls"] * 100
        
        return {
            "total_calls": self.stats["total_calls"],
            "cache_hits": self.stats["cache_hits"],
            "cache_misses": self.stats["cache_misses"],
            "cache_hit_rate": f"{cache_hit_rate:.1f}%",
            "errors": self.stats["errors"],
            "error_rate": f"{error_rate:.1f}%",
            "provider_calls": self.stats["provider_calls"],
            "cache_stats": cache_stats,
        }
    
    def cleanup(self):
        """清理资源"""
        # 清理过期缓存
        expired_count = self.cache.cleanup_expired()
        if expired_count > 0:
            self.logger.info(f"清理了 {expired_count} 个过期缓存文件")
        
        # 打印统计信息
        self.logger.info("客户端统计:")
        stats = self.get_client_stats()
        for key, value in stats.items():
            if key != "cache_stats":
                self.logger.info(f"  {key}: {value}")
    
    def __str__(self) -> str:
        """友好的字符串表示"""
        stats = self.get_client_stats()
        provider_stats = self.get_provider_stats()
        
        provider_info = []
        for name, stat in provider_stats.items():
            provider_info.append(f"    {name}: {'✅' if stat['is_available'] else '❌'} "
                               f"(调用: {stat['calls']}, 成功率: {stat['success_rate']})")
        
        return (
            f"StockDataClient(\n"
            f"  总调用次数: {stats['total_calls']}\n"
            f"  缓存命中率: {stats['cache_hit_rate']}\n"
            f"  错误率: {stats['error_rate']}\n"
            f"  提供器状态:\n" + "\n".join(provider_info) + "\n"
            f")"
        )


# 全局客户端实例
_client_instance = None

def get_client(config: Optional[StockDataConfig] = None) -> StockDataClient:
    """获取全局客户端实例"""
    global _client_instance
    if _client_instance is None:
        _client_instance = StockDataClient(config)
    return _client_instance