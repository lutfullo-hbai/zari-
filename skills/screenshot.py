import logging
from datetime import datetime

from skills.base import BaseSkill

log = logging.getLogger("zari")


class ScreenshotSkill(BaseSkill):
    priority = 80
    timeout = 10.0

    async def execute(self, query: str) -> dict | None:
        text = query.lower().strip()
        if not text:
            return None

        if any(w in text for w in ["skrin", "screen", "rasm", "shot", "ekran", "surat"]):
            return await self._take_screenshot()

        return None

    async def _take_screenshot(self) -> dict:
        try:
            import io

            import mss
            from PIL import Image

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            filepath = f"/tmp/{filename}"

            with mss.mss() as sct:
                sct.shot(mon=1, output=filepath)

            img = Image.open(filepath)
            w, h = img.size

            buf = io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)

            response = f"Ekran rasmi olindi: {filename} ({w}x{h}, {len(buf.getvalue()) // 1024}KB). Fayl: {filepath}"
            return {"response": response, "context": filepath, "source": "screenshot"}
        except Exception as e:
            log.warning("Screenshot xatosi: %s", e)
            return {
                "response": "Ekran rasmi olish imkoniyati yo'q (mss/PIL kerak).",
                "context": "",
                "source": "screenshot",
            }
