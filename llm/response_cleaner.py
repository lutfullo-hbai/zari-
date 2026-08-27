"""LLM javoblarini tozalash — thinking teglari va boshqa keraksiz qismlarni tozalash."""

import re

# <thinking>...</thinking> — to'liq blok (standard XML)
_CLOSED_FULL = re.compile(r"<thinking>[\s\S]*?</thinking>")
# <thinking>...钢厂 — Qwen format (chinese closing tag)
_QWEN_CLOSE = re.compile(r"钢厂[\s\S]*?钢厂")
# ```thinking...``` — code fence
_CODE_FENCE = re.compile(r"```thinking[\s\S]*?```")
# <thinking>...</thinking> — standard close, case-insensitive
_STANDARD_CLOSE = re.compile(r"<thinking>[\s\S]*?</thinking>", re.IGNORECASE)
# <thinking>... — qisqa format, to'liq blok (closing tagsiz, oxirigacha)
_OPEN_FULL = re.compile(r"<thinking>[\s\S]*", re.IGNORECASE)


def clean_llm_response(text: str) -> str:
    """LLM javobidan <thinking> teglarini va boshqa ichki mantiqni tozalash."""
    if not text:
        return text
    cleaned = _CLOSED_FULL.sub("", text)
    cleaned = _QWEN_CLOSE.sub("", cleaned)
    cleaned = _CODE_FENCE.sub("", cleaned)
    cleaned = _STANDARD_CLOSE.sub("", cleaned)
    cleaned = _OPEN_FULL.sub("", cleaned)
    return cleaned.strip()
