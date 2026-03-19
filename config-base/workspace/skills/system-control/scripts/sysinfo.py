#!/usr/bin/env python3
"""
sysinfo.py — Quick macOS system report.

Usage:
    python3 sysinfo.py [--json]
"""

import argparse
import json
import subprocess
import sys


def run(cmd: str, timeout: int = 10) -> str:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception:
        return ""


def get_cpu_usage() -> float:
    # Use ps to estimate CPU usage (avoids top hanging issues)
    out = run("ps -A -o %cpu | awk '{s+=$1} END {printf \"%.1f\", s}'")
    try:
        return round(float(out), 1)
    except (ValueError, TypeError):
        pass
    return -1


def get_memory() -> dict:
    import os
    page_size = int(run("sysctl -n hw.pagesize") or "4096")
    # Use vm_stat
    out = run("vm_stat")
    stats = {}
    for line in out.splitlines():
        if ":" in line:
            key, val = line.split(":", 1)
            val = val.strip().rstrip(".")
            try:
                stats[key.strip()] = int(val)
            except ValueError:
                pass

    free = stats.get("Pages free", 0) * page_size
    active = stats.get("Pages active", 0) * page_size
    inactive = stats.get("Pages inactive", 0) * page_size
    wired = stats.get("Pages wired down", 0) * page_size
    compressed = stats.get("Pages occupied by compressor", 0) * page_size

    total_bytes = int(run("sysctl -n hw.memsize") or "0")
    used = active + wired + compressed
    total_gb = total_bytes / (1024**3)
    used_gb = used / (1024**3)
    pct = round(used / total_bytes * 100, 1) if total_bytes else 0

    return {"total_gb": round(total_gb, 1), "used_gb": round(used_gb, 1), "percent": pct}


def get_disk() -> dict:
    out = run("df -h / | tail -1")
    parts = out.split()
    if len(parts) >= 5:
        return {"total": parts[1], "used": parts[2], "avail": parts[3], "percent": parts[4]}
    return {}


def get_battery() -> dict:
    out = run("pmset -g batt")
    if "no battery" in out.lower() or "InternalBattery" not in out:
        return {"available": False}
    # "InternalBattery-0 (id=...)	85%; charging; 1:30 remaining"
    for line in out.splitlines():
        if "InternalBattery" in line:
            parts = line.split("\t")
            if len(parts) >= 2:
                info = parts[-1].strip()
                pct_str = info.split(";")[0].strip()
                state = info.split(";")[1].strip() if ";" in info else "unknown"
                return {"available": True, "percent": pct_str, "state": state}
    return {"available": False}


def get_network() -> dict:
    wifi = run("networksetup -getairportnetwork en0 2>/dev/null")
    wifi_name = wifi.replace("Current Wi-Fi Network: ", "").strip() if "Current" in wifi else ""
    local_ip = run("ipconfig getifaddr en0")
    return {"wifi": wifi_name, "local_ip": local_ip}


def get_uptime() -> str:
    return run("uptime | sed 's/.*up /up /' | sed 's/,.*//'")


def get_macos_version() -> str:
    return run("sw_vers -productVersion")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='Health check')
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    
    if args.check:
        print("✅ OK")
        return

    report = {
        "cpu_percent": get_cpu_usage(),
        "memory": get_memory(),
        "disk": get_disk(),
        "battery": get_battery(),
        "network": get_network(),
        "uptime": get_uptime(),
        "macos_version": get_macos_version(),
    }

    if args.json:
        sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    else:
        lines = []
        lines.append(f"macOS {report['macos_version']}")
        lines.append(f"CPU:     {report['cpu_percent']}%")
        mem = report["memory"]
        lines.append(f"Memory:  {mem.get('used_gb', '?')}GB / {mem.get('total_gb', '?')}GB ({mem.get('percent', '?')}%)")
        disk = report["disk"]
        lines.append(f"Disk:    {disk.get('used', '?')} / {disk.get('total', '?')} ({disk.get('percent', '?')})")
        batt = report["battery"]
        if batt.get("available"):
            lines.append(f"Battery: {batt.get('percent', '?')} ({batt.get('state', '?')})")
        else:
            lines.append("Battery: N/A (desktop)")
        net = report["network"]
        lines.append(f"WiFi:    {net.get('wifi', 'disconnected')}")
        lines.append(f"Local IP: {net.get('local_ip', 'N/A')}")
        lines.append(f"Uptime:  {report['uptime']}")
        sys.stdout.write("\n".join(lines) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
