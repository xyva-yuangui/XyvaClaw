#!/usr/bin/env python3
"""
高德 Web Service API 封装层
文档: https://lbs.amap.com/api/webservice/guide/api/direction
"""

import json
import os
from pathlib import Path
from typing import Optional
import requests

AMAP_BASE = "https://restapi.amap.com/v3"
AMAP_BASE_V5 = "https://restapi.amap.com/v5"
OPENCLAW_CFG = Path.home() / ".openclaw" / "openclaw.json"


def _get_api_key() -> str:
    key = os.environ.get("AMAP_API_KEY", "").strip()
    if key:
        return key
    try:
        cfg = json.loads(OPENCLAW_CFG.read_text(encoding="utf-8"))
        key = (cfg.get("models", {}).get("providers", {})
               .get("amap", {}).get("apiKey", "").strip())
        if key:
            return key
    except Exception:
        pass
    return "e5213aaec1484a8eb3ffbaf0a98612e8"


def _get(path: str, params: dict, base: str = AMAP_BASE) -> dict:
    params["key"] = _get_api_key()
    params["output"] = "json"
    try:
        r = requests.get(f"{base}{path}", params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data.get("status") != "1":
            return {"error": data.get("info", "API error"), "infocode": data.get("infocode")}
        return data
    except Exception as e:
        return {"error": str(e)}


def geocode(address: str, city: str = "") -> dict:
    params = {"address": address}
    if city:
        params["city"] = city
    return _get("/geocode/geo", params)


def regeocode(location: str, radius: int = 100) -> dict:
    return _get("/geocode/regeo", {"location": location, "radius": radius, "extensions": "all"})


def route_driving(origin: str, destination: str) -> dict:
    return _get("/direction/driving", {"origin": origin, "destination": destination, "extensions": "base"})


def route_walking(origin: str, destination: str) -> dict:
    return _get("/direction/walking", {"origin": origin, "destination": destination})


def route_transit(origin: str, destination: str, city: str, cityd: str = "") -> dict:
    params = {"origin": origin, "destination": destination, "city": city, "extensions": "base"}
    if cityd:
        params["cityd"] = cityd
    return _get("/direction/transit/integrated", params)


def route_riding(origin: str, destination: str) -> dict:
    return _get("/direction/riding", {"origin": origin, "destination": destination}, base=AMAP_BASE_V5)


def poi_search(keywords: str, city: str = "", types: str = "", radius: int = 3000,
               location: str = "", search_type: str = "text") -> dict:
    if search_type == "around" and location:
        return _get("/place/around", {
            "keywords": keywords, "location": location,
            "radius": radius, "types": types, "extensions": "base"
        })
    params = {"keywords": keywords, "extensions": "base"}
    if city:
        params["city"] = city
    if types:
        params["types"] = types
    return _get("/place/text", params)


def static_map(location: str, zoom: int = 14, size: str = "400*300",
               markers: str = "") -> bytes:
    params = {
        "key": _get_api_key(),
        "location": location,
        "zoom": zoom,
        "size": size,
        "markers": markers or f"mid,,A:{location}",
    }
    try:
        r = requests.get(f"{AMAP_BASE}/staticmap", params=params, timeout=15)
        r.raise_for_status()
        return r.content
    except Exception as e:
        return b""


def ip_location(ip: str = "") -> dict:
    params = {}
    if ip:
        params["ip"] = ip
    return _get("/ip", params)


def district_query(keywords: str, subdistrict: int = 1) -> dict:
    return _get("/config/district", {"keywords": keywords, "subdistrict": subdistrict, "extensions": "base"})


def weather_query(city: str) -> dict:
    return _get("/weather/weatherInfo", {"city": city, "extensions": "all"})


def _latlng_from_address(address: str) -> Optional[str]:
    """Resolve address string to 'lng,lat' for API calls."""
    data = geocode(address)
    geocodes = data.get("geocodes", [])
    if geocodes:
        return geocodes[0].get("location", "")
    return None
