"""
Uzoq muddatli xotira — PostgreSQL orqali kontekst olish.

Eski suhbatlardagi foydalanuvchi xabarlarini kalit so'zlar bo'yicha topib,
hozirgi suhbatga kontekst sifatida beradi. ChromaDB o'rniga PostgreSQL
ILIKE qidiruvi ishlatiladi (lokal, yengil).
"""

import logging
import re

from db.database import get_pool

log = logging.getLogger("zari")

MAX_CONTEXT_MESSAGES = 6
MAX_CONTEXT_CHARS = 1500

_STOPWORDS = {
    "salom",
    "assalom",
    "zari",
    "bor",
    "yoq",
    "bilan",
    "uchun",
    "bu",
    "shu",
    "men",
    "sen",
    "u",
    "biz",
    "siz",
    "ular",
    "mening",
    "sening",
    "uning",
    "bir",
    "nima",
    "qanday",
    "qayerda",
    "qachon",
    "kim",
    "nega",
    "ha",
    "yo'q",
    "endi",
    "hozir",
    "kerak",
    "bo'ladi",
    "bo'ldi",
    "qil",
    "ber",
    "ayt",
    "the",
    "and",
    "what",
    "how",
    "why",
    "when",
    "where",
    "can",
    "you",
    "your",
    "for",
    "this",
}


def extract_keywords(text: str) -> list[str]:
    """Matndan muhim kalit so'zlarni ajratadi."""
    words = re.findall(r"[a-zа-яёA-ZА-ЯЁ']+", text.lower())
    seen: set[str] = set()
    keywords: list[str] = []
    for w in words:
        if len(w) < 4 or w in _STOPWORDS or w in seen:
            continue
        seen.add(w)
        keywords.append(w)
    return keywords[:5]


async def retrieve_context(
    query: str,
    exclude_session_id: str | None = None,
    limit: int = MAX_CONTEXT_MESSAGES,
) -> str:
    """Kalit so'zlar bo'yicha eski suhbatlardan kontekst qaytaradi."""
    keywords = extract_keywords(query)
    if not keywords:
        return ""

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT DISTINCT content FROM messages
                WHERE role = 'user'
                  AND content ILIKE ANY($1::text[])
                  AND ($2::text IS NULL OR session_id <> $2)
                ORDER BY created_at DESC
                LIMIT $3
                """,
                [f"%{kw}%" for kw in keywords],
                exclude_session_id,
                limit,
            )
    except Exception as e:
        log.warning("Kontekst olishda xatolik: %s", e)
        return ""

    if not rows:
        return ""

    seen_lines: set[str] = set()
    lines: list[str] = []
    for row in rows:
        snippet = row["content"][:200].strip()
        if snippet and snippet not in seen_lines:
            seen_lines.add(snippet)
            lines.append(snippet)

    if not lines:
        return ""

    context = "O'tgan suhbatlardan mavzuga oid eslatmalar:\n- " + "\n- ".join(lines)
    return context[:MAX_CONTEXT_CHARS]
