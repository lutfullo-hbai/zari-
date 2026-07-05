import asyncio
import logging
import re

from skills.base import BaseSkill

log = logging.getLogger("zari")

_ACTIVE_TIMERS: dict[str, asyncio.Task] = {}


class TimerSkill(BaseSkill):
    priority = 65
    timeout = 300.0

    async def execute(self, query: str) -> dict | None:
        text = query.lower().strip()
        if not text:
            return None

        if any(w in text for w in ["stop", "to'xtat", "bekor", "cancel"]):
            return await self._stop_timer(text)

        seconds = self._parse_duration(text)
        if seconds is None:
            return None

        name = self._parse_name(text) or f"Timer ({seconds}s)"
        task = asyncio.create_task(self._countdown(name, seconds))
        _ACTIVE_TIMERS[name] = task
        task.add_done_callback(lambda _: _ACTIVE_TIMERS.pop(name, None))

        mins, secs = divmod(seconds, 60)
        if mins:
            dur_str = f"{mins} daqiqa {secs} soniya"
        else:
            dur_str = f"{secs} soniya"

        response = f"{name} boshlandi ({dur_str})"
        return {"response": response, "context": f"timer:{name}:{seconds}", "source": "timer"}

    def _parse_duration(self, text: str) -> int | None:
        patterns = [
            (r"(\d+)\s*(daqiqa|min|m)", 60),
            (r"(\d+)\s*(soniya|sec|s)", 1),
            (r"(\d+)\s*(soat|hour|h)", 3600),
        ]
        total = 0
        matched = False
        for pattern, multiplier in patterns:
            for m in re.finditer(pattern, text):
                total += int(m.group(1)) * multiplier
                matched = True
        return total if matched else None

    def _parse_name(self, text: str) -> str | None:
        for sep in ["deb nomla", "nomli", ":", " — "]:
            if sep in text:
                idx = text.index(sep) + len(sep)
                name = text[idx:].strip()
                name = re.sub(r"\b(\d+\s*(daqiqa|min|soniya|sec|soat|hour|s|h|m))\b", "", name).strip()
                return name if name else None
        return None

    async def _stop_timer(self, text: str) -> dict | None:
        if not _ACTIVE_TIMERS:
            return {"response": "Faol timer yo'q.", "context": "", "source": "timer"}

        for name, task in list(_ACTIVE_TIMERS.items()):
            task.cancel()
            return {"response": f"{name} to'xtatildi.", "context": "", "source": "timer"}

        return {"response": "Timer topilmadi.", "context": "", "source": "timer"}

    async def _countdown(self, name: str, seconds: int):
        try:
            await asyncio.sleep(seconds)
            log.info("TIMER: %s - vaqt tugadi!", name)
        except asyncio.CancelledError:
            log.info("Timer bekor qilindi: %s", name)
