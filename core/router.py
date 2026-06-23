import re


INTENT_PATTERNS = {
    "search": (
        r"\b(qidir|top|izla|search|find|nima\b|kim\b|qanday|"
        r"sabab|define|meaning|what\b|who\b|why\b|when\b|"
        r"degani|haqida|ma.lumot|tushuntir|izohla)"
    ),
    "music": r"\b(musiqa|qo.?y|qo.?shiq|music|song|play)\b",
    "weather": r"\b(ob.havo|havo|weather)\b",
    "time": r"\b(soat necha|vaqt|time|kun)\b",
    "system": r"\b(och|yop|run|execute|open|close)\b",
    "chat": r".*",
}


def detect_intent(text: str) -> str:
    text = text.lower()
    for intent, pattern in INTENT_PATTERNS.items():
        if re.search(pattern, text):
            return intent
    return "chat"


def route(text: str) -> str:
    return detect_intent(text)
