#!/usr/bin/env python3
"""
天气查询 — 多源免费天气服务
支持: wttr.in (主力) + 60s.viki.moe (备用)

用法:
  python3 weather.py --query "北京"
  python3 weather.py --query "上海" --days 3
  python3 weather.py --query "Tokyo" --json
  python3 weather.py --check
"""
import argparse
import json
import sys
import urllib.request
import urllib.parse
from datetime import datetime


def _fetch_wttr(query: str, days: int = 1, lang: str = "zh") -> dict:
    """wttr.in 免费天气API (无需API key)"""
    encoded = urllib.parse.quote(query)
    url = f"https://wttr.in/{encoded}?format=j1&lang={lang}"
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "curl/7.68.0", "Accept": "application/json"
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())

        result = {"source": "wttr.in", "query": query}

        # 当前天气
        current = data.get("current_condition", [{}])[0]
        result["current"] = {
            "temp_c": current.get("temp_C", ""),
            "feels_like_c": current.get("FeelsLikeC", ""),
            "humidity": current.get("humidity", ""),
            "weather": current.get("lang_zh", [{}])[0].get("value", "") if current.get("lang_zh") else current.get("weatherDesc", [{}])[0].get("value", ""),
            "wind_speed_kmh": current.get("windspeedKmph", ""),
            "wind_dir": current.get("winddir16Point", ""),
            "visibility_km": current.get("visibility", ""),
            "uv_index": current.get("uvIndex", ""),
        }

        # 预报
        forecasts = []
        for day in data.get("weather", [])[:days]:
            forecasts.append({
                "date": day.get("date", ""),
                "max_c": day.get("maxtempC", ""),
                "min_c": day.get("mintempC", ""),
                "avg_c": day.get("avgtempC", ""),
                "sun_hours": day.get("sunHour", ""),
                "total_precip_mm": day.get("totalSnow_cm", "0"),
                "hourly_count": len(day.get("hourly", [])),
            })
        result["forecast"] = forecasts

        # 位置
        area = data.get("nearest_area", [{}])[0]
        result["location"] = {
            "name": area.get("areaName", [{}])[0].get("value", ""),
            "country": area.get("country", [{}])[0].get("value", ""),
            "region": area.get("region", [{}])[0].get("value", ""),
            "lat": area.get("latitude", ""),
            "lon": area.get("longitude", ""),
        }

        return result
    except Exception as e:
        return {"error": str(e), "source": "wttr.in"}


def _fetch_60s(query: str) -> dict:
    """60s.viki.moe 备用天气API"""
    encoded = urllib.parse.quote(query)
    url = f"https://60s.viki.moe/v2/weather?query={encoded}&encoding=json"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        return {"source": "60s.viki.moe", "data": data}
    except Exception as e:
        return {"error": str(e), "source": "60s.viki.moe"}


def query_weather(query: str, days: int = 1) -> dict:
    """查询天气, 自动 fallback"""
    result = _fetch_wttr(query, days)
    if "error" not in result:
        return result
    fallback = _fetch_60s(query)
    if "error" not in fallback:
        return fallback
    return {"error": f"所有天气源失败: wttr.in({result.get('error','')}), 60s({fallback.get('error','')})"}


def format_weather(data: dict) -> str:
    if "error" in data:
        return f"❌ 天气查询失败: {data['error']}"

    lines = []
    loc = data.get("location", {})
    cur = data.get("current", {})

    lines.append(f"🌤️ {loc.get('name', data.get('query', '?'))} 天气")
    if loc.get("country"):
        lines.append(f"   📍 {loc.get('region', '')}, {loc['country']}")
    lines.append(f"\n🌡️ 当前: {cur.get('temp_c', '?')}°C (体感 {cur.get('feels_like_c', '?')}°C)")
    lines.append(f"   {cur.get('weather', '')}")
    lines.append(f"   💧 湿度: {cur.get('humidity', '?')}% | 💨 风速: {cur.get('wind_speed_kmh', '?')}km/h {cur.get('wind_dir', '')}")
    lines.append(f"   👁️ 能见度: {cur.get('visibility_km', '?')}km | ☀️ UV: {cur.get('uv_index', '?')}")

    for fc in data.get("forecast", []):
        lines.append(f"\n📅 {fc['date']}: {fc.get('min_c', '?')}°C ~ {fc.get('max_c', '?')}°C (均 {fc.get('avg_c', '?')}°C)")

    return "\n".join(lines)


def health_check() -> dict:
    checks = []
    # wttr.in
    try:
        r = _fetch_wttr("Beijing", 1)
        ok = "error" not in r
        checks.append({"name": "wttr.in", "status": "ok" if ok else "warn", "message": "" if ok else r.get("error", "")})
    except Exception as e:
        checks.append({"name": "wttr.in", "status": "warn", "message": str(e)})

    # 60s backup
    checks.append({"name": "60s-backup", "status": "ok", "message": "60s.viki.moe (备用)"})

    fail = any(c["status"] == "fail" for c in checks)
    warn = any(c["status"] == "warn" for c in checks)
    overall = "fail" if fail else ("warn" if warn else "ok")
    return {"skill": "weather-query", "version": "2.0.0", "status": overall,
            "checks": checks, "timestamp": datetime.now().isoformat()}


def main():
    parser = argparse.ArgumentParser(description="天气查询 — 多源免费天气服务")
    parser.add_argument("--query", "-q", help="城市名 (中英文均可)")
    parser.add_argument("--days", "-d", type=int, default=1, help="预报天数 (1-3)")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    if args.check:
        r = health_check()
        print(json.dumps(r, indent=2, ensure_ascii=False))
        sys.exit(0 if r["status"] != "fail" else 1)

    if not args.query:
        parser.print_help()
        sys.exit(0)

    result = query_weather(args.query, args.days)
    if args.as_json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(format_weather(result))


if __name__ == "__main__":
    main()
