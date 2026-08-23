import logging
import re

from db.database import get_pool
from skills.base import BaseSkill

log = logging.getLogger("zari")


def _has_word(text: str, word: str) -> bool:
    return bool(re.search(rf"\b{re.escape(word)}\b", text))


class NotesSkill(BaseSkill):
    priority = 55
    timeout = 5.0

    async def execute(self, query: str) -> dict | None:
        text = query.lower().strip()
        if not text:
            return None

        if _has_word(text, "eslat"):
            return await self._search_notes(text)

        if any(_has_word(text, w) for w in ["yozib ol", "esla", "saqla", "yodda", "eslab qol"]):
            content = self._extract_content(query)
            if not content:
                return None
            return await self._add_note(content)

        if any(_has_word(text, w) for w in ["ochir", "o'chir", "delete", "remove"]):
            return await self._delete_note(text)

        if any(_has_word(text, w) for w in ["top", "qidir", "search", "ko'rsat", "list", "barcha"]):
            return await self._search_notes(text)

        return None

    def _extract_content(self, text: str) -> str:
        for sep in [":", ", ", " — ", " - "]:
            if sep in text:
                idx = text.index(sep) + len(sep)
                content = text[idx:].strip()
                if content:
                    return content
        parts = text.split(maxsplit=3)
        if len(parts) >= 3:
            return " ".join(parts[2:])
        return ""

    async def _add_note(self, content: str) -> dict:
        title = content[:50].strip()
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO notes (title, content) VALUES ($1, $2)",
                title,
                content,
            )
        response = f"Eslatma saqlandi: {title}"
        return {"response": response, "context": content, "source": "notes"}

    async def _search_notes(self, text: str) -> dict | None:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT id, title, content, created_at FROM notes ORDER BY id DESC LIMIT 20")

        if not rows:
            return {"response": "Hech qanday eslatma yo'q.", "context": "", "source": "notes"}

        kw = (
            text.replace("top", "")
            .replace("qidir", "")
            .replace("eslat", "")
            .replace("ko'rsat", "")
            .replace("list", "")
            .replace("barcha", "")
            .strip()
        )
        if kw:
            kw_lower = kw.lower()
            rows = [r for r in rows if kw_lower in r["title"].lower() or kw_lower in r["content"].lower()]

        if not rows:
            return {"response": f"'{kw}' bo'yicha eslatma topilmadi.", "context": "", "source": "notes"}

        lines = [f"  * {r['content'][:60]} ({str(r['created_at'])[:10]})" for r in rows[:10]]
        response = f"{len(rows)} ta eslatma:\n" + "\n".join(lines)
        return {"response": response, "context": str([r["content"] for r in rows]), "source": "notes"}

    async def _delete_note(self, text: str) -> dict:
        kw = text.replace("ochir", "").replace("o'chir", "").replace("delete", "").replace("remove", "").strip()
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT id, title, content FROM notes ORDER BY id DESC LIMIT 20")

            if not rows:
                return {"response": "O'chirish uchun eslatma yo'q.", "context": "", "source": "notes"}

            for r in rows:
                if kw.lower() in r["title"].lower() or kw.lower() in r["content"].lower():
                    await conn.execute("DELETE FROM notes WHERE id = $1", r["id"])
                    return {"response": f"Eslatma o'chirildi: {r['title']}", "context": "", "source": "notes"}

        return {"response": f"'{kw}' bo'yicha eslatma topilmadi.", "context": "", "source": "notes"}
