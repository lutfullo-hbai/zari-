"""BrightnessSkill — monitor yorqinligi (intent: "brightness").

xrandr orqali software brightness (root kerak emas).
Diapazon cheklovi: 0.2–1.0 (0.2 dan past ekran ishlatilmaydi).
"""

import logging
import re
import shutil
import subprocess

from skills.base import BaseSkill

log = logging.getLogger("zari")

MIN_BRIGHTNESS = 0.2
MAX_BRIGHTNESS = 1.0


class BrightnessSkill(BaseSkill):
    priority = 76
    timeout = 8.0

    def __init__(self):
        self._output: str | None = None

    async def execute(self, query: str) -> dict | None:
        text = (query or "").lower().strip()
        if not text:
            return None

        if shutil.which("xrandr") is None:
            return {
                "response": "'xrandr' topilmadi — yorqinlik boshqaruvi mavjud emas.",
                "context": "",
                "source": "brightness",
            }

        level = self._extract_level(text)
        current = await self._get_current()

        if any(w in text for w in ["oshir", "yorug", "ko'tar"]):
            step = (level or 10) / 100
            target = min(MAX_BRIGHTNESS, current + step)
        elif any(w in text for w in ["pastla", "xira", "kamaytir", "pasaytir"]):
            step = (level or 10) / 100
            target = max(MIN_BRIGHTNESS, current - step)
        elif level is not None:
            target = max(MIN_BRIGHTNESS, min(MAX_BRIGHTNESS, level / 100))
        else:
            return {
                "response": "Yorqinlik darajasini ayting: 'yorqinlikni 70 ga qo'y'.",
                "context": "",
                "source": "brightness",
            }

        return await self._apply(target)

    async def _get_output(self) -> str | None:
        if self._output:
            return self._output
        proc = subprocess.run(["xrandr", "--current"], capture_output=True, text=True, timeout=5)
        for line in proc.stdout.splitlines():
            if " connected" in line and ("primary" in line or self._output is None):
                name = line.split()[0]
                if "primary" in line:
                    self._output = name
                    break
                if self._output is None:
                    self._output = name
        return self._output

    async def _get_current(self) -> float:
        output = await self._get_output()
        if not output:
            return 1.0
        proc = subprocess.run(["xrandr", "--verbose"], capture_output=True, text=True, timeout=5)
        m = re.search(r"Brightness:\s*(\d\.\d+)", proc.stdout)
        return float(m.group(1)) if m else 1.0

    async def _apply(self, value: float) -> dict:
        output = await self._get_output()
        if not output:
            return {
                "response": "Monitor topilmadi.",
                "context": "",
                "source": "brightness",
            }
        value = round(max(MIN_BRIGHTNESS, min(MAX_BRIGHTNESS, value)), 2)
        try:
            proc = subprocess.run(
                ["xrandr", "--output", output, "--brightness", str(value)],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if proc.returncode != 0:
                return {
                    "response": "Yorqinlikni o'zgartirib bo'lmadi.",
                    "context": "",
                    "source": "brightness",
                }
            log.info("Brightness: %s → %.2f", output, value)
            percent = int(value * 100)
            return {
                "response": f"Yorqinlik {percent}% ga qo'yildi.",
                "context": f"brightness:{value}",
                "source": "brightness",
            }
        except Exception as e:
            log.warning("Brightness xato: %s", e)
            return {"response": f"Yorqinlik xatosi: {e}", "context": "", "source": "brightness"}

    @staticmethod
    def _extract_level(text: str) -> int | None:
        m = re.search(r"(\d{1,3})\s*(%|foiz|ga)?", text)
        if not m:
            return None
        val = int(m.group(1))
        return val if 0 <= val <= 100 else None
