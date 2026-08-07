#!/usr/bin/env python3
"""
统一股票数据服务工具函数
"""

import time
import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union
from pathlib import Path

import pandas as pd


def setup_logging(level: str = "INFO", log_file: Optional[Path] = None) -> logging.Logger:
    """设置日志"""
    logger = logging.getLogger("stock_data_service")
    
    if not logger.handlers:
        logger.setLevel(getattr(logging, level.upper()))
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # 文件处理器（如果指定了日志文件）
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
    
    return logger


def generate_cache_key(func_name: str, **kwargs) -> str:
    """生成缓存键"""
    # 对参数进行排序以确保一致性
    sorted_kwargs = sorted(kwargs.items())
    param_str = json.dumps(sorted_kwargs, sort_keys=True, default=str)
    
    # 生成MD5哈希
    key_str = f"{func_name}:{param_str}"
    return hashlib.md5(key_str.encode()).hexdigest()


def format_symbol(symbol: str) -> str:
    """格式化股票代码"""
    if not symbol:
        return symbol
    
    # 移除空格和特殊字符
    symbol = symbol.strip().upper()
    
    # 添加后缀如果缺失
    if symbol.isdigit():
        if symbol.startswith('6'):
            return f"{symbol}.SH"
        elif symbol.startswith('0') or symbol.startswith('3'):
            return f"{symbol}.SZ"
        elif symbol.startswith('9'):
            return f"{symbol}.SH"  # 上证B股
        elif symbol.startswith('2'):
            return f"{symbol}.SZ"  # 深证B股
    
    return symbol


def parse_symbol(symbol: str) -> Dict[str, str]:
    """解析股票代码"""
    symbol = format_symbol(symbol)
    
    if '.' in symbol:
        code, exchange = symbol.split('.')
        return {
            "code": code,
            "exchange": exchange,
            "full": symbol
        }
    else:
        return {
            "code": symbol,
            "exchange": None,
            "full": symbol
        }


def is_trading_day(date: Optional[Union[str, datetime]] = None) -> bool:
    """判断是否为交易日（简化版）"""
    if date is None:
        date = datetime.now()
    elif isinstance(date, str):
        date = datetime.strptime(date, "%Y-%m-%d")
    
    # 简单判断：周一至周五为交易日
    weekday = date.weekday()  # 0=周一, 6=周日
    return weekday < 5  # 周一至周五


def get_trading_date(offset: int = 0) -> str:
    """获取交易日日期"""
    date = datetime.now()
    
    # 如果偏移量为负，向前找交易日
    if offset < 0:
        for _ in range(abs(offset)):
            date -= timedelta(days=1)
            while not is_trading_day(date):
                date -= timedelta(days=1)
    # 如果偏移量为正，向后找交易日
    elif offset > 0:
        for _ in range(offset):
            date += timedelta(days=1)
            while not is_trading_day(date):
                date += timedelta(days=1)
    
    return date.strftime("%Y%m%d")


def validate_dataframe(df: pd.DataFrame, required_columns: list = None) -> bool:
    """验证DataFrame数据"""
    if df is None or df.empty:
        return False
    
    if required_columns:
        missing = [col for col in required_columns if col not in df.columns]
        if missing:
            return False
    
    return True


def retry_on_failure(max_retries: int = 3, delay: int = 1, 
                     exceptions: tuple = (Exception,)):
    """重试装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        time.sleep(delay * (attempt + 1))  # 指数退避
                    continue
            raise last_exception
        return wrapper
    return decorator


def timer(func):
    """计时装饰器"""
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"{func.__name__} 执行时间: {end - start:.2f}秒")
        return result
    return wrapper


def format_size(size_bytes: int) -> str:
    """格式化字节大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def clean_nan_values(data: Any) -> Any:
    """清理NaN值"""
    if isinstance(data, pd.DataFrame):
        return data.fillna(0)
    elif isinstance(data, dict):
        return {k: (0 if pd.isna(v) else v) for k, v in data.items()}
    elif isinstance(data, list):
        return [0 if pd.isna(item) else item for item in data]
    else:
        return data