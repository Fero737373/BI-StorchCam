# -*- coding: utf-8 -*-
from __future__ import annotations

import subprocess

_last_cpu: tuple[int, int] | None = None


def get_ip() -> str:
    try:
        out = subprocess.check_output(["hostname", "-I"], text=True, timeout=2).strip()
        ips = [x for x in out.split() if not x.startswith("127.")]
        return ips[0] if ips else "keine IP"
    except Exception:
        return "keine IP"


def get_cpu() -> int:
    global _last_cpu
    try:
        with open("/proc/stat", encoding="utf-8") as f:
            nums = [int(x) for x in f.readline().split()[1:]]
        idle = nums[3] + nums[4]
        total = sum(nums)
        if _last_cpu is None:
            _last_cpu = (total, idle)
            return 0
        prev_total, prev_idle = _last_cpu
        _last_cpu = (total, idle)
        dt = total - prev_total
        di = idle - prev_idle
        return 0 if dt <= 0 else round(100 * (dt - di) / dt)
    except Exception:
        return 0


def get_ram() -> int:
    try:
        mem = {}
        with open("/proc/meminfo", encoding="utf-8") as f:
            for line in f:
                parts = line.split()
                mem[parts[0].rstrip(":")] = int(parts[1])
        total = mem.get("MemTotal", 1)
        avail = mem.get("MemAvailable", 0)
        return round(100 * (total - avail) / total)
    except Exception:
        return 0


def get_temp() -> int:
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", encoding="utf-8") as f:
            return round(int(f.read().strip()) / 1000)
    except Exception:
        return 0


def get_uptime() -> str:
    try:
        with open("/proc/uptime", encoding="utf-8") as f:
            seconds = float(f.read().split()[0])
        return f"{int(seconds // 3600)}h {int((seconds % 3600) // 60)}m"
    except Exception:
        return "-"


def get_system_status() -> dict:
    return {
        "ip": get_ip(),
        "cpu": get_cpu(),
        "ram": get_ram(),
        "temp": get_temp(),
        "uptime": get_uptime(),
    }
