import asyncio
import json
import logging
import time
from datetime import datetime, timezone

from db.database import get_pool
from llm.ollama import OllamaClient

log = logging.getLogger("zari")

CATEGORIES = {"identity", "interest", "preference", "habit", "insight"}

_PERSONA_KEYWORDS = {
    "mening", "men", "ismim", "familiya", "yoshim", "kasbim",
    "ishim", "manzil", "yashayman", "tug'ilgan", "o'qiyman",
    "yoqadi", "yoqtirmayman", "qiziqaman", "hobbi", "mashg'ulot",
    "dasturchi", "o'qituvchi", "shifokor", "talaba", "o'quvchi",
    "sevimli", "yaxshi", "xohlayman", "rejam",
    "oilam", "ukam", "akam", "singlim", "onam", "dadam",
}

_PERSONA_PHRASES = [
    "my name", "i am", "i'm", "i work", "i live", "i like",
    "i love", "i study", "i hate", "i need",
]

_EXTRACTION_COOLDOWN = 30
_MIN_EXTRACT_LENGTH = 5

EXTRACT_PROMPT = """Siz foydalanuvchi xabarlaridan shaxsiy ma'lumotlarni topadigan AI siz.

Foydalanuvchi xabari: "{text}"

Yuqoridagi xabardan shaxsiy ma'lumotlarni toping.
Agar ma'lumot bo'lmasa, bo'sh massiv qaytaring.
Faqat aniq ma'lumot bo'lsa chiqaring — taxmin qilmang.

Natijani JSON formatida qaytaring:
[
  {{
    "key": "kalit_soz",
    "value": "qiymat",
    "category": "identity|interest|preference|habit|insight"
  }}
]

Misol:
- "mening ismim Ali" → [{{"key": "name", "value": "Ali", "category": "identity"}}]
- "jazz musiqa yoqadi" → [{{"key": "music_genre", "value": "jazz", "category": "interest"}}]
- "men dasturchiman" → [{{"key": "profession", "value": "dasturchi", "category": "identity"}}]
- "toshkentda yashayman" → [{{"key": "location", "value": "Toshkent", "category": "identity"}}]
- "qisqa javob bersangiz yaxshi" → [{{"key": "response_style", "value": "short", "category": "preference"}}]
- "kechasi ishlayman" → [{{"key": "work_hours", "value": "night", "category": "habit"}}]
"""


class UserPersona:
    def __init__(self):
        self._cache: dict[str, dict] | None = None
        self._last_extraction: float = 0

    async def ensure_table(self):
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS persona (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT 'general',
                    confidence REAL DEFAULT 1.0,
                    source TEXT DEFAULT 'manual',
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

    async def get(self, key: str) -> str | None:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT value FROM persona WHERE key = $1", key
            )
            return row["value"] if row else None

    async def set(self, key: str, value: str, category: str = "general", confidence: float = 1.0, source: str = "manual"):
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO persona (key, value, category, confidence, source, updated_at)
                   VALUES ($1, $2, $3, $4, $5, $6)
                   ON CONFLICT (key) DO UPDATE
                   SET value = $2, category = $3, confidence = $4, source = $5, updated_at = $6""",
                key, value, category, confidence, source, datetime.now(timezone.utc),
            )
        self._bust_cache()

    async def delete(self, key: str) -> bool:
        pool = await get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute("DELETE FROM persona WHERE key = $1", key)
        self._bust_cache()
        return result != "DELETE 0"

    async def delete_all(self) -> int:
        pool = await get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute("DELETE FROM persona")
        self._bust_cache()
        return int(result.split()[-1]) if result else 0

    async def get_all(self) -> list[dict]:
        if self._cache is not None:
            return list(self._cache.values())
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT key, value, category FROM persona ORDER BY category, key"
            )
        self._cache = {r["key"]: dict(r) for r in rows} if rows else {}
        return list(self._cache.values())

    def _bust_cache(self):
        self._cache = None

    async def get_system_text(self) -> str:
        rows = await self.get_all()
        if not rows:
            return ""
        parts = []
        label_map = {
            "name": "Ismingiz",
            "age": "Yoshingiz",
            "location": "Manzilingiz",
            "profession": "Kasbingiz",
            "music_genre": "Sevimli musiqangiz",
            "tech_stack": "Texnologiyalaringiz",
            "hobby": "Sevimli mashg'ulotingiz",
            "response_style": "Javob uslubi",
            "communication": "Muloqot uslubi",
            "tone": "Ohang",
            "work_hours": "Ish vaqtingiz",
            "language": "Til",
            "personality": "Sifatlaringiz",
            "favorite_food": "Sevimli taomingiz",
            "pet_name": "Uy hayvoningiz",
            "education": "Ma'lumotingiz",
            "relationship": "Oilaviy holatingiz",
            "birth_date": "Tug'ilgan kuningiz",
            "phone": "Telefon raqamingiz",
            "email": "Email manzilingiz",
            "goal": "Maqsadingiz",
            "skill": "Ko'nikmalaringiz",
            "company": "Ish joyingiz",
            "school": "O'quv muassasangiz",
        }
        for r in rows:
            label = label_map.get(r["key"], r["key"].replace("_", " ").capitalize())
            parts.append(f"{label}: {r['value']}")
        return "Foydalanuvchi haqida biladigan ma'lumotlarim:\n" + "\n".join(parts)

    def _should_extract(self, text: str) -> bool:
        text_lower = text.lower().strip()
        if len(text_lower) < _MIN_EXTRACT_LENGTH:
            return False

        now = time.time()
        if now - self._last_extraction < _EXTRACTION_COOLDOWN:
            return False

        text_words = set(text_lower.split())
        if text_words & _PERSONA_KEYWORDS:
            self._last_extraction = now
            return True

        for phrase in _PERSONA_PHRASES:
            if phrase in text_lower:
                self._last_extraction = now
                return True

        return False

    async def extract_from_conversation(self, text: str, llm: OllamaClient):
        if not self._should_extract(text):
            return

        prompt = EXTRACT_PROMPT.format(text=text.strip())
        try:
            raw = await asyncio.wait_for(
                llm.chat_async([{"role": "user", "content": prompt}], timeout=30),
                timeout=35,
            )
            facts = self._parse_llm_response(raw)
            for fact in facts:
                key = fact.get("key", "").strip()
                value = fact.get("value", "").strip()
                category = fact.get("category", "insight").strip()
                if key and value:
                    cat = category if category in CATEGORIES else "insight"
                    await self.set(key, value, cat, source="llm")
                    log.info("Persona: %s = %s (%s)", key, value, cat)
        except asyncio.TimeoutError:
            log.debug("Persona extraction timeout")
        except Exception as e:
            log.debug("Persona extraction error: %s", e)

    def _parse_llm_response(self, raw: str) -> list[dict]:
        text = raw.strip()
        if not text:
            return []

        if text.startswith("["):
            try:
                data = json.loads(text)
                if isinstance(data, list):
                    return data
            except json.JSONDecodeError:
                pass

        start = text.find("[")
        if start == -1:
            return []
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "[":
                depth += 1
            elif text[i] == "]":
                depth -= 1
                if depth == 0:
                    try:
                        data = json.loads(text[start:i+1])
                        if isinstance(data, list):
                            return data
                    except (json.JSONDecodeError, ValueError):
                        pass
                    return []
        return []

    async def learn_fact(self, key: str, value: str, category: str = "identity"):
        await self.set(key, value, category, source="manual")
        log.info("Persona learned: %s = %s", key, value)

    async def get_summary(self) -> str:
        rows = await self.get_all()
        if not rows:
            return "Yangi foydalanuvchi"
        vals = {r["key"]: r["value"] for r in rows}
        parts = []
        for k in ("name", "age", "location", "profession", "hobby", "language", "education"):
            if k in vals:
                parts.append(vals[k])
        return ", ".join(parts) if parts else "Ma'lumotli foydalanuvchi"


