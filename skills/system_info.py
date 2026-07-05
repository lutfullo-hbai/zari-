"""System information skill — OS, CPU, RAM, disk, uptime, and Python version.

Provides system diagnostics as a voice-friendly text response.
All numeric values are formatted for natural speech output.
"""

import logging
import os
import platform
import shutil
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from skills.base import BaseSkill

log = logging.getLogger("zari")

_BYTE_UNITS = ["bayt", "KB", "MB", "GB", "TB"]

_KEYWORD_MAP: dict[str, str] = {
    "kompyuter": "system",
    "system": "system",
    "tizim": "system",
    "operatsion": "os",
    "os": "os",
    "protsessor": "cpu",
    "cpu": "cpu",
    "processor": "cpu",
    "ram": "memory",
    "memory": "memory",
    "xotira": "memory",
    "disk": "disk",
    "drive": "disk",
    "holat": "uptime",
    "uptime": "uptime",
    "vaqt": "uptime",
    "python": "python",
    "versiya": "version",
}


def _format_bytes(size_bytes: int) -> str:
    """Convert bytes to human-readable format."""
    if size_bytes == 0:
        return f"0 {_BYTE_UNITS[0]}"

    unit_index = 0
    size = float(size_bytes)
    while size >= 1024 and unit_index < len(_BYTE_UNITS) - 1:
        size /= 1024
        unit_index += 1

    if unit_index == 0:
        return f"{int(size)} {_BYTE_UNITS[unit_index]}"

    return f"{size:.1f} {_BYTE_UNITS[unit_index]}"


def _format_uptime(seconds: float) -> str:
    """Convert uptime seconds to human-readable string."""
    days, remainder = divmod(int(seconds), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)

    parts: list[str] = []
    if days > 0:
        parts.append(f"{days} kun")
    if hours > 0:
        parts.append(f"{hours} soat")
    if minutes > 0:
        parts.append(f"{minutes} minut")

    return ", ".join(parts) if parts else "bir necha soniya"


class SystemInfoSkill(BaseSkill):
    """Provides system information: OS, CPU, RAM, disk, uptime, Python version."""

    priority = 15
    timeout = 5.0
    retries = 0

    async def execute(self, query: str) -> dict[str, Any] | None:
        topic = self._detect_topic(query)
        if topic is None:
            return None

        try:
            response = await self._fetch_info(topic)
            return {"response": response, "context": response, "source": "system_info"}
        except OSError as e:
            log.warning("System info unavailable: %s", e)
            return {"response": "Tizim ma'lumotini olishda xatolik.", "context": "", "source": "system_info"}

    def _detect_topic(self, query: str) -> str | None:
        """Detect which system info topic the user is asking about."""
        text = query.lower().strip()
        if not text:
            return None

        matched_topics: list[str] = []
        for keyword, topic in _KEYWORD_MAP.items():
            if keyword in text and topic not in matched_topics:
                matched_topics.append(topic)

        if "all" in text or "hammasi" in text or "to'liq" in text:
            return "all"

        if not matched_topics:
            return None

        return matched_topics[0]

    async def _fetch_info(self, topic: str) -> str:
        """Route to the appropriate info fetcher based on topic."""
        fetcher = self._get_fetcher(topic)
        if fetcher is None:
            return "Kechirasiz, bu ma'lumotni ololmayman."

        return fetcher()

    def _get_fetcher(self, topic: str) -> Callable[[], str] | None:
        """Return the fetcher function for the given topic."""
        fetchers: dict[str, Callable[[], str]] = {
            "all": self._get_all_info,
            "os": self._get_os_info,
            "system": self._get_system_info,
            "cpu": self._get_cpu_info,
            "memory": self._get_memory_info,
            "disk": self._get_disk_info,
            "uptime": self._get_uptime_info,
            "python": self._get_python_info,
            "version": self._get_python_info,
        }
        return fetchers.get(topic)

    def _get_all_info(self) -> str:
        lines = [
            self._get_os_info(),
            self._get_cpu_info(),
            self._get_memory_info(),
            self._get_disk_info(),
            self._get_uptime_info(),
            self._get_python_info(),
        ]
        return "\n".join(lines)

    def _get_os_info(self) -> str:
        return f"Operatsion tizim: {platform.system()} {platform.release()}"

    def _get_system_info(self) -> str:
        node = platform.node()
        arch = platform.machine()
        return f"Kompyuter: {node}, arxitektura: {arch}"

    def _get_cpu_info(self) -> str:
        cpu_count = os.cpu_count() or 0
        freq = _get_cpu_freq_mhz()
        freq_part = f", {freq:.0f} MHz" if freq > 0 else ""
        return f"Protsessor: {cpu_count} yadro{freq_part}"

    def _get_memory_info(self) -> str:
        mem_info = _read_memory_info()
        if mem_info is None:
            return "Xotira ma'lumoti olinmadi."
        used = _format_bytes(mem_info["used"])
        total = _format_bytes(mem_info["total"])
        percent = mem_info["percent"]
        return f"RAM: {used} ishlatilgan / {total} ({percent:.0f}%)"

    def _get_disk_info(self) -> str:
        usage = shutil.disk_usage("/")
        used = _format_bytes(usage.used)
        total = _format_bytes(usage.total)
        percent = usage.used / usage.total * 100
        return f"Disk: {used} ishlatilgan / {total} ({percent:.0f}%)"

    def _get_uptime_info(self) -> str:
        seconds = _get_system_uptime()
        if seconds is None:
            return "Ish vaqti ma'lumoti olinmadi."
        formatted = _format_uptime(seconds)
        return f"Tizim ish vaqti: {formatted}"

    def _get_python_info(self) -> str:
        return f"Python: {platform.python_version()}"


def _get_cpu_freq_mhz() -> float:
    """Get current CPU frequency in MHz. Returns 0 if unavailable."""
    try:
        freq = platform.processor()
        if freq:
            return 0
    except Exception:
        pass

    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("cpu MHz"):
                    return float(line.split(":")[1].strip())
    except (FileNotFoundError, ValueError, OSError):
        pass

    return 0


def _get_system_uptime() -> float | None:
    """Get system uptime in seconds. Platform-aware."""
    system = platform.system()
    if system == "Linux":
        return _get_linux_uptime()
    if system == "Darwin":
        return _get_macos_uptime()
    if system == "Windows":
        return _get_windows_uptime()
    return None


def _get_linux_uptime() -> float | None:
    try:
        with open("/proc/uptime") as f:
            seconds = float(f.read().split()[0])
        return seconds
    except (FileNotFoundError, ValueError, OSError):
        return None


def _get_macos_uptime() -> float | None:
    import subprocess
    try:
        result = subprocess.run(
            ["sysctl", "-n", "kern.boottime"],
            capture_output=True, text=True, timeout=2,
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split()
            boot_timestamp = float(parts[3].rstrip(","))
            now = datetime.now(timezone.utc).timestamp()
            return now - boot_timestamp
    except Exception:
        pass
    return None


def _get_windows_uptime() -> float | None:
    import subprocess
    try:
        result = subprocess.run(
            ["net", "stats", "srv"],
            capture_output=True, text=True, timeout=2,
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if "Statistics since" in line:
                    date_str = line.split(" since ")[-1].strip()
                    boot_time = datetime.strptime(date_str, "%m/%d/%Y %I:%M:%S %p")
                    boot_time = boot_time.replace(tzinfo=timezone.utc)
                    now = datetime.now(timezone.utc)
                    return (now - boot_time).total_seconds()
    except Exception:
        pass
    return None


def _read_memory_info() -> dict[str, float] | None:
    """Read memory info from /proc/meminfo on Linux. Returns None on other platforms."""
    try:
        with open("/proc/meminfo") as f:
            data: dict[str, int] = {}
            for line in f:
                parts = line.split(":")
                if len(parts) == 2:
                    key = parts[0].strip()
                    value_str = parts[1].strip().split()[0]
                    try:
                        data[key] = int(value_str)
                    except (ValueError, IndexError):
                        continue
                    if len(data) >= 5:
                        break

        total = data.get("MemTotal", 0)
        free = data.get("MemFree", 0)
        buffers = data.get("Buffers", 0)
        cached = data.get("Cached", 0)

        total_kb = float(total)
        free_kb = float(free + buffers + cached)
        used_kb = max(0, total_kb - free_kb)
        percent = (used_kb / total_kb * 100) if total_kb > 0 else 0

        return {
            "total": total_kb * 1024,
            "used": used_kb * 1024,
            "percent": percent,
        }
    except (FileNotFoundError, OSError):
        pass
    return None
