"""
Odat aniqlash — foydalanuvchi faolligini PostgreSQL tahlil qiladi.

Suhbat xabarlarining vaqt belgilarini tahlil qilib,
ish soatlari kabi odatlarni aniqlaydi va persona jadvaliga saqlaydi.
"""

import logging

from db.database import get_pool
from llm.persona import UserPersona

log = logging.getLogger("zari")

_MIN_MESSAGES = 15


def classify_peak_hour(hour_counts: dict[int, int]) -> str:
    """Eng ko'p xabar yozilgan soat bo'yicha odatni aniqlaydi."""
    if not hour_counts:
        return "unknown"
    peak = max(hour_counts, key=hour_counts.get)
    if 22 <= peak or peak <= 5:
        return "night"
    if 6 <= peak <= 11:
        return "morning"
    if 12 <= peak <= 17:
        return "day"
    return "evening"


async def detect_habits(min_messages: int = _MIN_MESSAGES) -> dict[str, str]:
    """Foydalanuvchi faolligini tahlil qilib, odat faktlarini qaytaradi."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    (EXTRACT(HOUR FROM created_at))::int AS hour,
                    COUNT(*)::int AS cnt
                FROM messages
                WHERE role = 'user'
                GROUP BY 1
                """
            )
    except Exception as e:
        log.warning("Odat tahlilida xatolik: %s", e)
        return {}

    total = sum(r["cnt"] for r in rows)
    if total < min_messages:
        log.debug("Odat aniqlash uchun yetarli xabar yo'q (%d/%d)", total, min_messages)
        return {}

    hour_counts: dict[int, int] = {r["hour"]: r["cnt"] for r in rows}
    work_hours = classify_peak_hour(hour_counts)

    top_hours = sorted(hour_counts.items(), key=lambda kv: kv[1], reverse=True)[:3]
    active_hours = ", ".join(f"{h}:00-{h + 1}:00" for h, _ in top_hours)

    return {
        "work_hours": work_hours,
        "active_hours": active_hours,
    }


async def analyze_and_store_habits(persona: UserPersona) -> dict[str, str]:
    """Odatlarni aniqlab, persona jadvaliga saqlaydi."""
    facts = await detect_habits()
    if not facts:
        return {}

    for key, value in facts.items():
        await persona.set(key, value, category="habit", confidence=0.8, source="analyzed")
        log.info("Odat aniqlandi: %s = %s", key, value)

    return facts
