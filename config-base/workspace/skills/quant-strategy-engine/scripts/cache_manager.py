#!/usr/bin/env python3
"""
缓存管理模块 - Cache Manager
内存缓存（LRU），提升热门数据读取速度
"""

from collections import OrderedDict
from datetime import datetime, timedelta
from pathlib import Path
import json
import threading

class LRUCache:
    """LRU 缓存"""
    
    def __init__(self, capacity=10000):
        """
        初始化缓存
        
        Args:
            capacity: 缓存容量（最大条目数）
        """
        self.capacity = capacity
        self.cache = OrderedDict()
        self.lock = threading.Lock()
        self.hits = 0
        self.misses = 0
    
    def get(self, key):
        """
        获取缓存
        
        Args:
            key: 缓存键
        
        Returns:
            缓存值，不存在返回 None
        """
        with self.lock:
            if key in self.cache:
                # 移动到末尾（最近使用）
                self.cache.move_to_end(key)
                self.hits += 1
                return self.cache[key]
            else:
                self.misses += 1
                return None
    
    def set(self, key, value, ttl=None):
        """
        设置缓存
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒）
        """
        with self.lock:
            # 如果已满，删除最旧的
            if len(self.cache) >= self.capacity and key not in self.cache:
                self.cache.popitem(last=False)
            
            # 存储值和过期时间
            expire_at = datetime.now() + timedelta(seconds=ttl) if ttl else None
            self.cache[key] = {
                'value': value,
                'expire_at': expire_at
            }
            
            # 移动到末尾
            self.cache.move_to_end(key)
    
    def delete(self, key):
        """删除缓存"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
    
    def clear(self):
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0
    
    def get_stats(self):
        """获取缓存统计"""
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0
        
        return {
            'capacity': self.capacity,
            'current_size': len(self.cache),
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': f"{hit_rate:.2%}"
        }
    
    def cleanup_expired(self):
        """清理过期缓存"""
        with self.lock:
            now = datetime.now()
            expired_keys = []
            
            for key, item in self.cache.items():
                if item['expire_at'] and item['expire_at'] < now:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.cache[key]
            
            if expired_keys:
                print(f"✅ 清理 {len(expired_keys)} 条过期缓存")


class CacheManager:
    """缓存管理器"""
    
    def __init__(self):
        # 缓存配置
        self.config = {
            'daily_data': {'capacity': 10000, 'ttl': 86400},  # 日线数据，缓存 1 天
            'factor_scores': {'capacity': 5000, 'ttl': 86400},  # 因子得分，缓存 1 天
            'stock_list': {'capacity': 100, 'ttl': 604800},  # 股票列表，缓存 7 天
            'market_state': {'capacity': 10, 'ttl': 3600},  # 市场状态，缓存 1 小时
        }
        
        # 初始化缓存实例
        self.caches = {}
        for name, config in self.config.items():
            self.caches[name] = LRUCache(capacity=config['capacity'])
        
        # 缓存目录
        self.cache_dir = Path.home() / ".openclaw" / "data" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        print("✅ 缓存管理器初始化完成")
        print(f"   缓存目录：{self.cache_dir}")
    
    def get_daily_data(self, ts_code, trade_date):
        """获取日线数据缓存"""
        key = f"{ts_code}:{trade_date}"
        return self.caches['daily_data'].get(key)
    
    def set_daily_data(self, ts_code, trade_date, data):
        """设置日线数据缓存"""
        key = f"{ts_code}:{trade_date}"
        config = self.config['daily_data']
        self.caches['daily_data'].set(key, data, ttl=config['ttl'])
    
    def get_factor_scores(self, ts_code, trade_date):
        """获取因子得分缓存"""
        key = f"{ts_code}:{trade_date}"
        return self.caches['factor_scores'].get(key)
    
    def set_factor_scores(self, ts_code, trade_date, data):
        """设置因子得分缓存"""
        key = f"{ts_code}:{trade_date}"
        config = self.config['factor_scores']
        self.caches['factor_scores'].set(key, data, ttl=config['ttl'])
    
    def get_stock_list(self):
        """获取股票列表缓存"""
        return self.caches['stock_list'].get('all_stocks')
    
    def set_stock_list(self, stock_list):
        """设置股票列表缓存"""
        config = self.config['stock_list']
        self.caches['stock_list'].set('all_stocks', stock_list, ttl=config['ttl'])
    
    def get_market_state(self):
        """获取市场状态缓存"""
        return self.caches['market_state'].get('current')
    
    def set_market_state(self, state):
        """设置市场状态缓存"""
        config = self.config['market_state']
        self.caches['market_state'].set('current', state, ttl=config['ttl'])
    
    def get_all_stats(self):
        """获取所有缓存统计"""
        stats = {}
        for name, cache in self.caches.items():
            stats[name] = cache.get_stats()
        return stats
    
    def cleanup_all_expired(self):
        """清理所有过期缓存"""
        for cache in self.caches.values():
            cache.cleanup_expired()
    
    def save_cache_to_disk(self):
        """保存缓存到磁盘（可选）"""
        # 保存股票列表等持久化数据
        stock_list = self.get_stock_list()
        if stock_list:
            cache_file = self.cache_dir / "stock_list.json"
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(stock_list, f, ensure_ascii=False, indent=2)
            print(f"✅ 缓存已保存到 {cache_file}")
    
    def load_cache_from_disk(self):
        """从磁盘加载缓存（可选）"""
        cache_file = self.cache_dir / "stock_list.json"
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8') as f:
                stock_list = json.load(f)
            self.set_stock_list(stock_list)
            print(f"✅ 缓存已从 {cache_file} 加载")


# 测试
if __name__ == "__main__":
    cache_manager = CacheManager()
    
    # 测试缓存
    print("\n" + "=" * 70)
    print("缓存测试")
    print("=" * 70)
    
    # 设置缓存
    cache_manager.set_daily_data("000001.SZ", "20260309", {"close": 10.82, "pct_chg": 0.09})
    cache_manager.set_factor_scores("000001.SZ", "20260309", {"total_score": 85.5})
    
    # 获取缓存
    daily_data = cache_manager.get_daily_data("000001.SZ", "20260309")
    print(f"日线数据缓存：{daily_data}")
    
    factor_scores = cache_manager.get_factor_scores("000001.SZ", "20260309")
    print(f"因子得分缓存：{factor_scores}")
    
    # 缓存统计
    print("\n缓存统计:")
    stats = cache_manager.get_all_stats()
    for name, stat in stats.items():
        print(f"  {name}: 容量={stat['capacity']}, 当前={stat['current_size']}, 命中率={stat['hit_rate']}")
    
    print("\n" + "=" * 70)
    print("✅ 缓存管理模块测试完成")
    print("=" * 70)
