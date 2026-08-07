#!/usr/bin/env python3
"""
统一股票数据服务配置管理
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class StockDataConfig:
    """股票数据统一配置"""
    
    # Tushare配置（token 从环境变量/全局 config/tushare.json 读取，不再硬编码）
    # gateway 留空 = 使用 tushare 官方 API (api.tushare.pro)
    tushare_token: str = ""
    tushare_gateway: str = ""
    
    # 缓存配置
    cache_enabled: bool = True
    cache_dir: Path = Path.home() / ".openclaw" / "stock_data_cache"
    cache_ttl: Dict[str, int] = None
    
    # 重试配置
    max_retries: int = 3
    retry_delay: int = 1  # 秒
    timeout: int = 30     # 秒
    
    # 数据源优先级
    data_source_priority: List[str] = None
    
    # 日志配置
    log_level: str = "INFO"
    log_file: Optional[Path] = None
    
    def __post_init__(self):
        """初始化默认值"""
        # 设置默认缓存TTL
        if self.cache_ttl is None:
            self.cache_ttl = {
                "daily": 3600,           # 1小时
                "basic": 86400,          # 1天
                "financial": 86400,      # 1天
                "news": 1800,            # 30分钟
                "realtime": 5,           # 5秒
            }
        
        # 设置默认数据源优先级
        if self.data_source_priority is None:
            self.data_source_priority = ["akshare", "baostock", "tushare", "mootdx"]
        
        # 确保缓存目录存在
        if self.cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def from_env(cls) -> "StockDataConfig":
        """从环境变量创建配置，token 回退到全局 config/tushare.json"""
        token = os.getenv("TUSHARE_TOKEN", "")
        gateway = os.getenv("TUSHARE_GATEWAY", "")
        if not token:
            central = Path.home() / ".openclaw" / "workspace" / "config" / "tushare.json"
            try:
                import json
                c = json.loads(central.read_text())
                t = c.get("token", "")
                if t and not t.startswith(("YOUR_", "REDACTED")):
                    token = t
                    gateway = gateway or c.get("gateway", "")
            except (OSError, ValueError):
                pass
        return cls(
            tushare_token=token,
            tushare_gateway=gateway,  # 留空 = 官方 API
            cache_enabled=os.getenv("CACHE_ENABLED", "true").lower() == "true",
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            timeout=int(os.getenv("TIMEOUT", "30")),
        )
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "tushare_token": self.tushare_token,
            "tushare_gateway": self.tushare_gateway,
            "cache_enabled": self.cache_enabled,
            "cache_dir": str(self.cache_dir),
            "cache_ttl": self.cache_ttl,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "timeout": self.timeout,
            "data_source_priority": self.data_source_priority,
            "log_level": self.log_level,
        }
    
    def __str__(self) -> str:
        """友好的字符串表示"""
        return (
            f"StockDataConfig(\n"
            f"  tushare_token: {'*' * 10}{self.tushare_token[-10:] if self.tushare_token else 'None'}\n"
            f"  tushare_gateway: {self.tushare_gateway}\n"
            f"  cache_enabled: {self.cache_enabled}\n"
            f"  data_sources: {self.data_source_priority}\n"
            f")"
        )


# 默认配置实例
default_config = StockDataConfig.from_env()