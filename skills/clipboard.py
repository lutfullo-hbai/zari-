import logging

from skills.base import BaseSkill

log = logging.getLogger("zari")


class ClipboardSkill(BaseSkill):
    priority = 80
    timeout = 5.0

    async def execute(self, query: str) -> dict | None:
        text = query.lower().strip()
        if not text:
            return None

        if any(w in text for w in ["o'qi", "qidir", "ol", "read", "get", "ko'rsat", "nima"]):
            return await self._read_clipboard()

        if any(w in text for w in ["yoz", "saqla", "qo'y", "copy", "write", "set"]):
            return await self._write_clipboard(query)

        return None

    async def _read_clipboard(self) -> dict:
        try:
            import pyperclip
            content = pyperclip.paste()
            if not content:
                return {"response": "Clipboard bo'sh.", "context": "", "source": "clipboard"}
            response = f"Clipboardda: {content[:200]}"
            if len(content) > 200:
                response += "..."
            return {"response": response, "context": content, "source": "clipboard"}
        except Exception as e:
            log.warning("Clipboard o'qish xatosi: %s", e)
            return {"response": "Clipboard o'qish imkoniyati yo'q.", "context": "", "source": "clipboard"}

    async def _write_clipboard(self, query: str) -> dict:
        content = query
        for kw in ["yoz", "saqla", "qo'y", "clipboard", "copy", "write", "set", ":" ," — "]:
            if kw in content:
                idx = content.index(kw) + len(kw)
                content = content[idx:].strip().lstrip(":,; -—")
                break

        if not content:
            return None

        try:
            import pyperclip
            pyperclip.copy(content)
            return {
                "response": f"Clipboardga yozildi: {content[:100]}",
                "context": content,
                "source": "clipboard",
            }
        except Exception as e:
            log.warning("Clipboard yozish xatosi: %s", e)
            return {"response": "Clipboardga yozish imkoniyati yo'q.", "context": "", "source": "clipboard"}
