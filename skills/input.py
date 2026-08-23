"""InputControlSkill — klaviatura/sichqoncha boshqaruvi (intent: "input").

Xavfsizlik qatlamlari:
- requires_confirmation=True — har doim dialog tasdig'i shart
- Tugmalar faqat ALLOWED_KEYS ro'yxatidan
- Sichqoncha koordinatalari ekran chegarasida (max 7680x4320)
- Matn kiritish (type) TAQIQLANGAN — keyslar orqali xavfsiz emas
"""

import logging
import re
import shutil
import subprocess

from skills.base import BaseSkill

log = logging.getLogger("zari")

MAX_X, MAX_Y = 7680, 4320

ALLOWED_KEYS = {
    # o'zbek/ingliz nomi → xdotool keysym
    "enter": "Return",
    "entir": "Return",
    "return": "Return",
    "escape": "Escape",
    "esc": "Escape",
    "tab": "Tab",
    "space": "space",
    "probel": "space",
    "backspace": "BackSpace",
    "delete": "Delete",
    "del": "Delete",
    "up": "Up",
    "yuqoriga": "Up",
    "down": "Down",
    "pastga": "Down",
    "left": "Left",
    "chapga": "Left",
    "right": "Right",
    "o'ngga": "Right",
    "home": "Home",
    "end": "End",
    "f1": "F1",
    "f2": "F2",
    "f3": "F3",
    "f4": "F4",
    "f5": "F5",
    "ctrl+c": "ctrl+c",
    "ctrl+v": "ctrl+v",
    "ctrl+x": "ctrl+x",
    "ctrl+s": "ctrl+s",
    "ctrl+a": "ctrl+a",
    "ctrl+z": "ctrl+z",
    "ctrl+w": "ctrl+w",
    "alt+tab": "alt+Tab",
}


class InputControlSkill(BaseSkill):
    priority = 45
    timeout = 8.0
    requires_confirmation = True
    confirmation_type = "danger"

    async def execute(self, query: str) -> dict | None:
        text = (query or "").lower().strip()
        if not text:
            return None

        if shutil.which("xdotool") is None:
            return {
                "response": "'xdotool' topilmadi — input boshqaruvi mavjud emas.",
                "context": "",
                "source": "input",
            }

        coords = self._extract_coords(text)
        if coords and any(w in text for w in ["sur", "move", "ol", "keltir"]):
            return await self._mouse_move(*coords)

        if any(w in text for w in ["bosing", "bos", "click", "press"]):
            if any(w in text for w in ["sichqoncha", "mouse", "chapka", "o'nka"]):
                return await self._mouse_click(text)
            return await self._press_key(text)

        return None

    async def _press_key(self, text: str) -> dict:
        key = self._find_key(text)
        if not key:
            return {
                "response": "Bu tugma ruxsat etilmagan yoki tushunmadim. "
                "Mumkin: Enter, Escape, Tab, strelkalar, Ctrl+C/V/S va h.k.",
                "context": "",
                "source": "input",
            }
        subprocess.run(["xdotool", "key", key], capture_output=True, timeout=5)
        log.info("Input: key %s", key)
        return {
            "response": f"'{key}' tugmasi bosildi.",
            "context": f"key:{key}",
            "source": "input",
        }

    async def _mouse_move(self, x: int, y: int) -> dict:
        x = max(0, min(MAX_X, x))
        y = max(0, min(MAX_Y, y))
        subprocess.run(
            ["xdotool", "mousemove", str(x), str(y)],
            capture_output=True,
            timeout=5,
        )
        log.info("Input: mouse %d,%d", x, y)
        return {
            "response": f"Sichqoncha {x}, {y} koordinatasiga ko'chirildi.",
            "context": f"mouse:{x},{y}",
            "source": "input",
        }

    async def _mouse_click(self, text: str) -> dict:
        button = 3 if any(w in text for w in ["o'nka", "o'ng", "right"]) else 1
        subprocess.run(["xdotool", "click", str(button)], capture_output=True, timeout=5)
        log.info("Input: click btn%d", button)
        side = "o'ng" if button == 3 else "chap"
        return {
            "response": f"{side.capitalize()} tugma bosildi.",
            "context": f"click:{button}",
            "source": "input",
        }

    @staticmethod
    def _find_key(text: str) -> str | None:
        """Uzun kombinatsiyalar birinchi (ctrl+c < c)."""
        for name in sorted(ALLOWED_KEYS, key=len, reverse=True):
            if re.search(rf"\b{re.escape(name)}\b", text):
                return ALLOWED_KEYS[name]
        return None

    @staticmethod
    def _extract_coords(text: str) -> tuple[int, int] | None:
        m = re.search(r"(\d{1,5})\s*[,;x ]\s*(\d{1,5})", text)
        if not m:
            return None
        x, y = int(m.group(1)), int(m.group(2))
        if x > MAX_X or y > MAX_Y:
            return None
        return x, y
