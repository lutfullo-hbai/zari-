"""VolumeSkill — tizim ovozi boshqaruvi (intent: "volume").

amixer (ALSA) orqali: aniq foiz, +10/-10, mute/unmute.
"""

import logging
import re
import shutil
import subprocess

from skills.base import BaseSkill

log = logging.getLogger("zari")


class VolumeSkill(BaseSkill):
    priority = 78
    timeout = 5.0

    def __init__(self):
        self.mixer = "Master"

    async def execute(self, query: str) -> dict | None:
        text = (query or "").lower().strip()
        if not text:
            return None

        if shutil.which("amixer") is None:
            return {
                "response": "'amixer' topilmadi — ovoz boshqaruvi mavjud emas.",
                "context": "",
                "source": "volume",
            }

        if any(w in text for w in ["mute", "jim", "o'chir"]):
            return await self._run(["amixer", "sset", self.mixer, "mute"], "Ovoz o'chirildi (mute).")
        if any(w in text for w in ["unmute", "qayta yoq", "ovozni yoq"]):
            return await self._run(["amixer", "sset", self.mixer, "unmute"], "Ovoz yoqildi.")

        level = self._extract_level(text)
        if any(w in text for w in ["oshir", "ko'tar", "balandla"]):
            step = f"{level or 10}%+"
            return await self._run(["amixer", "sset", self.mixer, step], f"Ovoz {level or 10}% ga oshirildi.")
        if any(w in text for w in ["pastla", "pasaytir", "kamaytir", "kichikla"]):
            step = f"{level or 10}%-"
            return await self._run(["amixer", "sset", self.mixer, step], f"Ovoz {level or 10}% ga pasaytirildi.")
        if level is not None:
            return await self._set_level(level)

        # Faqat holat so'rash
        if any(w in text for w in ["necha", "holat", "qancha", "status"]):
            return await self._status()
        return None

    async def _set_level(self, level: int) -> dict:
        level = max(0, min(100, level))
        return await self._run(["amixer", "sset", self.mixer, f"{level}%"], f"Ovoz {level}% ga qo'yildi.")

    async def _run(self, cmd: list[str], message: str) -> dict:
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if proc.returncode != 0:
                return {
                    "response": "Ovozni o'zgartirib bo'lmadi.",
                    "context": "",
                    "source": "volume",
                }
            log.info("Volume: %s", " ".join(cmd[2:]))
            return {"response": message, "context": " ".join(cmd[2:]), "source": "volume"}
        except Exception as e:
            log.warning("Volume xato: %s", e)
            return {"response": f"Ovoz xatosi: {e}", "context": "", "source": "volume"}

    async def _status(self) -> dict:
        try:
            proc = subprocess.run(["amixer", "sget", self.mixer], capture_output=True, text=True, timeout=5)
            m = re.search(r"\[(\d{1,3})%\]", proc.stdout)
            muted = "[off]" in proc.stdout
            if m:
                state = "jim" if muted else "yoniq"
                return {
                    "response": f"Ovoz darajasi: {m.group(1)}% ({state}).",
                    "context": f"volume:{m.group(1)}",
                    "source": "volume",
                }
        except Exception as e:
            log.warning("Volume status xato: %s", e)
        return {"response": "Ovoz holatini o'qib bo'lmadi.", "context": "", "source": "volume"}

    @staticmethod
    def _extract_level(text: str) -> int | None:
        """'ovozni 50 ga' → 50; '50% ' → 50."""
        m = re.search(r"(\d{1,3})\s*(%|foiz|ga|gacha)?", text)
        if not m:
            return None
        return max(0, min(100, int(m.group(1))))
