---
name: amap-service
description: Use when users ask about navigation, directions, nearby places (POI search), geocoding, reverse geocoding, static map images, IP location, or administrative district queries in China. Requires AMAP_API_KEY to be configured.
---

# 高德地图服务 (amap-service)

调用高德 Web Service API，支持 9 大类地图能力。

## When to Use

- 导航 / 路径规划（驾车、步行、公交、骑行）
- 查附近餐厅 / 加油站 / 商场等 POI
- 地址 → 经纬度（地理编码）
- 经纬度 → 地址（逆地理编码）
- 生成静态地图图片
- IP 定位
- 行政区查询
- 天气查询（高德版，可替代 weather-query）

## Commands

```bash
uv run amap_service.py route --origin "北京南站" --dest "天安门" [--mode driving|walking|transit|riding]
uv run amap_service.py poi --keywords "火锅" --city "成都" [--radius 3000]
uv run amap_service.py geo --address "上海市浦东新区陆家嘴"
uv run amap_service.py regeo --location "121.473701,31.230416"
uv run amap_service.py staticmap --location "121.473701,31.230416" [--zoom 14] [--size 400x300]
uv run amap_service.py ip [--ip 8.8.8.8]
uv run amap_service.py district --keywords "海淀区"
uv run amap_service.py weather --city "北京"
uv run amap_service.py search --keywords "星巴克" --city "上海" [--type text|around]
```

## Configuration

API Key 读取顺序：
1. 环境变量 `AMAP_API_KEY`
2. `openclaw.json` → `skills.amap.apiKey`

申请地址：https://lbs.amap.com/（免费额度：5000次/天）
