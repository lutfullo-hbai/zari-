"""SystemControlSkill — ilova/URL ochish va jarayon yopish (intent: "system").

Xavfsizlik:
- requires_confirmation=True — har doim dialog tasdig'idan keyin bajariladi
- Faqat ruxsat etilgan belgilardagi nomlar; PATH'da mavjud bo'lgan dasturlar
- URL'lar faqat http(s) sxemada
"""

import logging
import re
import shutil
import subprocess

from skills.base import BaseSkill

log = logging.getLogger("zari")

_SAFE_NAME = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9 ._-]{0,63}$")
_SAFE_URL = re.compile(r"^https?://[a-zA-Z0-9._~:/?#\[\]@!$&'()*+,;=%-]+$")


class SystemControlSkill(BaseSkill):
    priority = 25
    timeout = 10.0
    requires_confirmation = True
    confirmation_type = "danger"

    async def execute(self, query: str) -> dict | None:
        text = (query or "").lower().strip()
        if not text:
            return None

        words = text.split()
        if any(w in text for w in ["yop", "close", "o'chir", "kill"]):
            return await self._close_app(words)
        return await self._open_target(text)

    async def _open_target(self, text: str) -> dict | None:
        target = self._extract_after(text, ["och", "open", "ishga tushir", "run"])
        if not target:
            return {
                "response": "Nimani ochish kerak? (masalan: 'firefoxni och')",
                "context": "",
                "source": "system",
            }

        if target.startswith(("http://", "https://")):
            cleaned = target.rstrip(".,!?")
            if not _SAFE_URL.match(cleaned):
                return {"response": "Noto'g'ri URL.", "context": "", "source": "system"}
            subprocess.Popen(["xdg-open", cleaned])
            return {
                "response": f"{cleaned} ochilmoqda.",
                "context": f"open:{cleaned}",
                "source": "system",
            }

        app = self._extract_app_name(target)
        if not app:
            return {
                "response": f"Dastur nomini tushunmadim: {target}",
                "context": "",
                "source": "system",
            }
        executable = shutil.which(app)
        if executable is None:
            return {
                "response": f"'{app}' tizimda topilmadi.",
                "context": "",
                "source": "system",
            }

        log.info("Ilova ochilmoqda: %s (%s)", app, executable)
        subprocess.Popen([executable])
        return {
            "response": f"{app} ochilmoqda.",
            "context": f"open:{app}",
            "source": "system",
        }

    async def _close_app(self, words: list[str]) -> dict | None:
        name = next(
            (w for w in reversed(words) if w not in {"yop", "close", "o'chir", "kill", "ni", "ni yop", "iliq"}), ""
        )
        app = self._extract_app_name(name)
        if not app:
            return {
                "response": "Qaysi ilovani yopish kerak?",
                "context": "",
                "source": "system",
            }
        if shutil.which("pkill") is None:
            return {
                "response": "'pkill' topilmadi — yopish qo'llab-quvvatlanmaydi.",
                "context": "",
                "source": "system",
            }
        result = subprocess.run(["pkill", "-x", app], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return {
                "response": f"{app} yopildi.",
                "context": f"close:{app}",
                "source": "system",
            }
        return {
            "response": f"'{app}' degan jarayon ishlayotgani topilmadi.",
            "context": "",
            "source": "system",
        }

    def _extract_app_name(self, raw: str) -> str | None:
        """'firefoxni' → 'firefox'. Argumentlar (-rf kabi) HECH QACHON
        uzatilmaydi — faqat birinchi toza so'z nom sifatida qaraladi."""
        for token in raw.strip().rstrip(".,!?").split():
            candidate = token.removesuffix("ni").strip().lower()
            if not candidate or candidate.startswith("-"):
                continue
            if not _SAFE_NAME.match(candidate):
                return None  # shubhali belgilangan so'z — butunlay rad etish
            return candidate
        return None

    def _extract_after(self, text: str, triggers: list[str]) -> str:
        """Trigger'ni butun so'z sifatida topib, qolgan qismini qaytaradi.

        'firefoxni och' → '' (head), 'https://x.com ni och' → '',
        'och https://x.com' → 'https://x.com'.
        """
        pattern = "|".join(re.escape(t) for t in triggers)
        m = re.search(rf"\b({pattern})\w*\b", text)
        if not m:
            return ""
        rest = text[m.end() :].strip(" :'\"")
        if rest:
            return rest.split(",")[0].strip()
        # trigger oxirida bo'lsa — oldingi qism nishon bo'ladi
        return text[: m.start()].strip()
