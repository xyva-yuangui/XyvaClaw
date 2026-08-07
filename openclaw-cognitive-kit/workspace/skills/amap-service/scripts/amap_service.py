#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests>=2.28"]
# ///
"""
amap-service — 高德地图 Web Service 统一入口

用法:
  uv run amap_service.py route --origin "北京南站" --dest "天安门" [--mode driving]
  uv run amap_service.py poi   --keywords "火锅" --city "成都"
  uv run amap_service.py geo   --address "上海市浦东新区陆家嘴"
  uv run amap_service.py regeo --location "121.473701,31.230416"
  uv run amap_service.py staticmap --location "121.473701,31.230416" [--out map.png]
  uv run amap_service.py ip    [--ip 8.8.8.8]
  uv run amap_service.py district --keywords "海淀区"
  uv run amap_service.py weather --city "北京"
  uv run amap_service.py search --keywords "星巴克" --city "上海"
"""

import argparse
import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import amap_api as api


def _print(data: dict | str, compact: bool = False):
    if isinstance(data, str):
        print(data)
        return
    if compact:
        print(json.dumps(data, ensure_ascii=False))
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2))


def _error(msg: str):
    print(f"[amap-service] 错误: {msg}", file=sys.stderr)
    sys.exit(1)


def _resolve_location(s: str) -> str:
    """如果输入像 'lng,lat' 就直接返回，否则通过地理编码解析。"""
    if s and "," in s and all(c.isdigit() or c in ".,+-" for c in s.replace(",", "")):
        return s
    loc = api._latlng_from_address(s)
    if not loc:
        _error(f"无法解析地址为经纬度: {s}")
    return loc


# ──────────────────────────────────────────────────────
# 子命令处理
# ──────────────────────────────────────────────────────

def cmd_route(args):
    origin = _resolve_location(args.origin)
    dest = _resolve_location(args.dest)
    mode = args.mode.lower()

    if mode == "driving":
        data = api.route_driving(origin, dest)
    elif mode == "walking":
        data = api.route_walking(origin, dest)
    elif mode in ("transit", "bus"):
        city = args.city or "北京"
        data = api.route_transit(origin, dest, city)
    elif mode in ("riding", "bike"):
        data = api.route_riding(origin, dest)
    else:
        _error(f"不支持的出行方式: {mode}，可选: driving/walking/transit/riding")

    if "error" in data:
        _error(data["error"])

    if mode == "driving":
        routes = data.get("route", {}).get("paths", [])
        if routes:
            r = routes[0]
            dist_km = int(r.get("distance", 0)) / 1000
            dur_min = int(r.get("duration", 0)) / 60
            print(f"驾车路线: {dist_km:.1f} 公里，预计 {dur_min:.0f} 分钟")
            for step in r.get("steps", [])[:5]:
                print(f"  → {step.get('instruction', '')}")
        else:
            _print(data)
    elif mode == "walking":
        paths = data.get("route", {}).get("paths", [])
        if paths:
            p = paths[0]
            dist = int(p.get("distance", 0))
            dur = int(p.get("duration", 0))
            print(f"步行路线: {dist} 米，预计 {dur // 60} 分钟")
        else:
            _print(data)
    else:
        _print(data)


def cmd_poi(args):
    search_type = "around" if args.location else "text"
    data = api.poi_search(
        keywords=args.keywords,
        city=args.city or "",
        types=args.types or "",
        radius=args.radius,
        location=args.location or "",
        search_type=search_type,
    )
    if "error" in data:
        _error(data["error"])

    pois = data.get("pois", [])
    if not pois:
        print("未找到相关 POI")
        return
    for i, p in enumerate(pois[:15]):
        name = p.get("name", "")
        addr = p.get("address", "-")
        dist = p.get("distance", "")
        tel = p.get("tel", "")
        dist_str = f"{dist}m " if dist else ""
        tel_str = f"☎ {tel}" if tel else ""
        print(f"{i+1:2}. {name}  {dist_str}{addr}  {tel_str}")


def cmd_geo(args):
    data = api.geocode(args.address, args.city or "")
    if "error" in data:
        _error(data["error"])
    for g in data.get("geocodes", []):
        print(f"地址: {g.get('formatted_address','')}")
        print(f"坐标: {g.get('location','')}")
        print(f"精度: {g.get('level','')}")


def cmd_regeo(args):
    data = api.regeocode(args.location, args.radius)
    if "error" in data:
        _error(data["error"])
    reg = data.get("regeocode", {})
    addr = reg.get("formatted_address", "")
    print(f"地址: {addr}")
    comp = reg.get("addressComponent", {})
    print(f"省: {comp.get('province','')}  市: {comp.get('city','')}  区: {comp.get('district','')}  街道: {comp.get('towncode','')}")


def cmd_staticmap(args):
    location = _resolve_location(args.location)
    img_bytes = api.static_map(location, args.zoom, args.size)
    if not img_bytes:
        _error("获取静态地图失败")
    out = args.out or "amap_static.png"
    Path(out).write_bytes(img_bytes)
    print(f"静态地图已保存: {out}  ({len(img_bytes)//1024} KB)")


def cmd_ip(args):
    data = api.ip_location(args.ip or "")
    if "error" in data:
        _error(data["error"])
    print(f"IP: {data.get('ip','-')}")
    print(f"省份: {data.get('province','-')}  城市: {data.get('city','-')}")
    print(f"区域: {data.get('adcode','-')}")


def cmd_district(args):
    data = api.district_query(args.keywords, args.subdistrict)
    if "error" in data:
        _error(data["error"])
    districts = data.get("districts", [])
    for d in districts[:5]:
        print(f"{d.get('name','')}  adcode={d.get('adcode','')}  level={d.get('level','')}")
        for sub in d.get("districts", [])[:10]:
            print(f"  └ {sub.get('name','')}  {sub.get('adcode','')}")


def cmd_weather(args):
    data = api.weather_query(args.city)
    if "error" in data:
        _error(data["error"])
    forecasts = data.get("forecasts", [])
    if forecasts:
        f = forecasts[0]
        print(f"城市: {f.get('city','')}")
        for cast in f.get("casts", [])[:3]:
            print(f"  {cast.get('date','')} {cast.get('week','')}: {cast.get('dayweather','')} {cast.get('nightweather','')} "
                  f"{cast.get('daytemp','')}°/{cast.get('nighttemp','')}°  风向: {cast.get('daywind','')}{cast.get('daypower','')}级")
    lives = data.get("lives", [])
    if lives:
        lv = lives[0]
        print(f"\n实况: {lv.get('weather','')} {lv.get('temperature','')}°C  湿度{lv.get('humidity','')}%  "
              f"{lv.get('winddirection','')}风 {lv.get('windpower','')}级")


def cmd_search(args):
    data = api.poi_search(keywords=args.keywords, city=args.city or "")
    if "error" in data:
        _error(data["error"])
    pois = data.get("pois", [])
    if not pois:
        print("未找到结果")
        return
    for i, p in enumerate(pois[:10]):
        print(f"{i+1:2}. {p.get('name','')}  {p.get('address','-')}")


# ──────────────────────────────────────────────────────
# CLI 入口
# ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="高德地图 Web Service 工具")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_route = sub.add_parser("route", help="路径规划")
    p_route.add_argument("--origin", required=True)
    p_route.add_argument("--dest", required=True)
    p_route.add_argument("--mode", default="driving", choices=["driving","walking","transit","riding","bus","bike"])
    p_route.add_argument("--city", default="")

    p_poi = sub.add_parser("poi", help="周边/文本 POI 搜索")
    p_poi.add_argument("--keywords", required=True)
    p_poi.add_argument("--city", default="")
    p_poi.add_argument("--types", default="")
    p_poi.add_argument("--location", default="")
    p_poi.add_argument("--radius", type=int, default=3000)

    p_geo = sub.add_parser("geo", help="地理编码（地址→坐标）")
    p_geo.add_argument("--address", required=True)
    p_geo.add_argument("--city", default="")

    p_regeo = sub.add_parser("regeo", help="逆地理编码（坐标→地址）")
    p_regeo.add_argument("--location", required=True)
    p_regeo.add_argument("--radius", type=int, default=100)

    p_smap = sub.add_parser("staticmap", help="生成静态地图图片")
    p_smap.add_argument("--location", required=True)
    p_smap.add_argument("--zoom", type=int, default=14)
    p_smap.add_argument("--size", default="400*300")
    p_smap.add_argument("--out", default="")

    p_ip = sub.add_parser("ip", help="IP 定位")
    p_ip.add_argument("--ip", default="")

    p_dist = sub.add_parser("district", help="行政区查询")
    p_dist.add_argument("--keywords", required=True)
    p_dist.add_argument("--subdistrict", type=int, default=1)

    p_wx = sub.add_parser("weather", help="天气查询")
    p_wx.add_argument("--city", required=True)

    p_search = sub.add_parser("search", help="关键词搜索")
    p_search.add_argument("--keywords", required=True)
    p_search.add_argument("--city", default="")

    args = parser.parse_args()
    dispatch = {
        "route": cmd_route,
        "poi": cmd_poi,
        "geo": cmd_geo,
        "regeo": cmd_regeo,
        "staticmap": cmd_staticmap,
        "ip": cmd_ip,
        "district": cmd_district,
        "weather": cmd_weather,
        "search": cmd_search,
    }
    dispatch[args.cmd](args)


if __name__ == "__main__":
    main()
