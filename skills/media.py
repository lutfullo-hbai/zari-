"""MediaSkill — lokal media ijro va transport boshqaruvi (intent: "media").

- playerctl: play/pause/stop/next/previous (Mpv, Firefox, Spotify...)
- mpv: fayl yo'li yoki audio/video kengaytmali so'z topilsa — ochish
"""

import logging
import re
import shutil
import subprocess
from pathlib import Path

from skills.base import BaseSkill

log = logging.getLogger("zari")

MEDIA_EXT_RE = re.compile(r"(/?[\w .\-/]+\.(?:mp3|wav|flac|m4a|ogg|opus|mp4|mkv|avi|webm))", re.IGNORECASE)


class MediaSkill(BaseSkill):
    priority = 52
    timeout = 15.0

    async def execute(self, query: str) -> dict | None:
        text = (query or "").lower().strip()
        if not text:
            return None

        if any(w in text for w in ["pauza", "pause", "to'xtat", "toxtat", "stop"]):
            return await self._ctl("play-pause", "Pauza/to'g'rilandi.")
        if any(w in text for w in ["keyingi", "next"]):
            return await self._ctl("next", "Keyingi trekka o'tildi.")
        if any(w in text for w in ["oldingi", "previous", "orqaga"]):
            return await self._ctl("previous", "Oldingi trekka qaytildi.")

        # MUHIM: fayl yo'li "ijro et"/"play" so'zlaridan OLDIN tekshiriladi,
        # aks holda "music.mp3 ni ijro et" playerctl'ga ketadi.
        m = MEDIA_EXT_RE.search(query)
        if m and shutil.which("mpv"):
            raw = m.group(1).strip()
            path = Path(raw).expanduser()
            if not path.is_absolute():
                candidate = Path.home() / path
                path = candidate if candidate.exists() else path
            if path.exists():
                subprocess.Popen(
                    ["mpv", "--really-quiet", str(path)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                log.info("Media: %s", path)
                return {
                    "response": f"{path.name} ijro etilmoqda.",
                    "context": f"mpv:{path}",
                    "source": "media",
                }
            return {
                "response": f"Fayl topilmadi: {raw}",
                "context": "",
                "source": "media",
            }

        if any(w in text for w in ["davom", "ijro et", "play"]):
            return await self._ctl("play", "Ijro davom ettirildi.")

        return None

    async def _ctl(self, action: str, message: str) -> dict | None:
        playerctl = shutil.which("playerctl")
        if not playerctl:
            return {
                "response": "'playerctl' topilmadi — media boshqaruvi mavjud emas.",
                "context": "",
                "source": "media",
            }
        proc = subprocess.run([playerctl, action], capture_output=True, text=True, timeout=5)
        # playerctl: ijrochi yo'q bo'lsa nolikdan boshqa kod qaytaradi
        if proc.returncode != 0 and action != "play-pause":
            return {
                "response": "Faol media pleyer topilmadi.",
                "context": "",
                "source": "media",
            }
        log.info("Media: playerctl %s", action)
        return {"response": message, "context": f"playerctl:{action}", "source": "media"}
