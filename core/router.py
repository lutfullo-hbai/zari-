import logging
import re

log = logging.getLogger("zari")


INTENT_PRIORITY: dict[str, int] = {
    "network": 85,
    "clipboard": 80,
    "volume": 78,
    "brightness": 76,
    "media": 52,
    "input": 45,
    "code_runner": 40,
    "screenshot": 80,
    "filemanager": 80,
    "organize": 82,
    "browser": 75,
    "documents": 70,
    "weather": 70,
    "timer": 65,
    "calculator": 60,
    "notes": 55,
    "music": 50,
    "email": 40,
    "workflow": 35,
    "time": 30,
    "system": 25,
    "system_info": 22,
    "search": 20,
    "wiki": 15,
    "chat": 0,
}

INTENT_PATTERNS: dict[str, str] = {
    "weather": r"\b(ob.havo|obhavo|havo|weather|harorat)\b",
    "time": r"\b(soat necha|vaqt necha|kun necha|soat|time|bugun)\b",
    "system": r"\b(och|yop|run|execute|open|close)\b",
    "system_info": (
        r"\b(kompyuter\w*|tizim\w*|system\w*|protsessor\w*|CPU|cpu|ram\w*|"
        r"xotira\w*|disk\w*|uptime|python\w*|versiya\w*|holat\w*|ma'lumot)\b"
    ),
    "browser": (
        r"\b(youtube\w*|google\w*|sayt\w*|veb sayt|website\w*|brauzer\w*|"
        r"browser\w*|havola\w*|instagram\w*|facebook\w*|twitter\b|github\b|"
        r"https?://\S+)\b"
    ),
    "organize": r"\b(tartibga sol\w*|tartibla|sarala\w*|organize)\b",
    "documents": r"\b(pdf\w*|docx?\b|hujjat\w*|excel\w*|xlsx?\b|jadval fayl|powerpoint|pptx?)\b",
    "email": r"\b(gmail|email|mail|xat|yubor|send)\b",
    "music": r"\b(musiqa\w*|qo.?y\w*|qo.?shiq\w*|music\w*|song\w*|play\w*|tingla\w*|yoq\w*)\b",
    "workflow": (
        r"\b(workflow|flow|automation|template|n8n|telegram|slack|"
        r"google sheets|sheet|webhook|valyuta|oltin|currency)\b"
    ),
    "notes": r"\b(yozib ol|esla|eslatma|note|saqla|yodda)\b",
    "timer": r"\b(timer|daqiqa|soniya|minut|sekund|vaqt o.lcha)\b",
    "calculator": r"\b(hisobla|calculate|necha bo.ladi)\b",
    "clipboard": r"\b(clipboard\w*|buffer\w*|nusxa\w*)\b",
    "screenshot": r"\b(skrin\w*|screen\w*|rasm ola\w*|skrinshot)\b",
    "filemanager": r"\b(fayl\w*|folder\w*|papka\w*|katalog\w*|file\w*|directory)\b",
    "network": r"\b(ip|dns|ping|network|tarmoq)\b",
    "wiki": r"\b(eslab qol|uni esla|esimda saqla|bil|ismim|yoshim|manzil)\b",
    "search": (
        r"\b(qidir|top|izla|search|find|"
        r"sabab|define|meaning|nima degan|"
        r"ma.lumot|tushuntir|izohla|"
        r"article|maqola|topib ber|qidirib ber)"
    ),
    "volume": (r"\b(ovoz\w*|tovush\w*|volume\w*|mute\w*|unmute\w*|jim)\b"),
    "brightness": (r"\b(yorqin\w*|xira\w*|xiralik|brightness\w*|ekranni yorug)\b"),
    "media": (
        r"\b(pauza\w*|pause\w*|to'?xtat\w*|keyingi\w+|oldingi\w+|"
        r"previous\w*|davom ettir|trek\w*|\.mp3|\.mp4|\.mkv|\.wav|\.flac)"
    ),
    "input": (
        r"\b(sichqoncha\w*|mouse\w*|kursor\w*|cursor\w*|klaviatura\w*|"
        r"keyboard\w*|tugma\w*|enter\b|entir\b|escape\b|esc\b|"
        r"strelka\w*|ctrl\+\w+)\b"
    ),
    "code_runner": r"\b(kodni ishga\w*|kod yozib|ishga tushir kod|run kod|skriptni ishga)\b",
    "chat": r".*",
}

# Confidence thresholds
CONFIDENCE_THRESHOLD = 0.6


def detect_intent_with_confidence(text: str) -> tuple[str, float]:
    """
    Detect intent with confidence score

    Args:
        text: User query text

    Returns:
        Tuple of (intent, confidence_score)
    """
    text_lower = text.lower()

    # Check each pattern
    matches = {}
    for intent, pattern in INTENT_PATTERNS.items():
        if intent == "chat":  # Skip fallback for now
            continue

        # Try to find pattern
        match = re.search(pattern, text_lower)
        if match:
            # Calculate confidence based on match quality
            matched_text = match.group()
            confidence = min(len(matched_text) / len(text_lower) + 0.3, 1.0)
            matches[intent] = confidence

    # Return highest confidence match, or chat fallback
    if matches:
        best_intent = max(matches, key=matches.get)
        best_confidence = matches[best_intent]
        log.debug("Intent detection: %s (confidence: %.2f)", best_intent, best_confidence)
        return best_intent, best_confidence

    log.debug("No specific intent matched, using chat fallback")
    return "chat", 0.5


def detect_intent(text: str) -> str:
    """
    Detect intent from text (original function for backwards compatibility)

    Args:
        text: User query text

    Returns:
        Intent string
    """
    text_lower = text.lower()
    for intent, pattern in INTENT_PATTERNS.items():
        if re.search(pattern, text_lower):
            return intent
    return "chat"


def match_intents(text: str) -> list[str]:
    """Return all matching intents sorted by priority (highest first)."""
    text_lower = text.lower()
    matched = []
    for intent, pattern in INTENT_PATTERNS.items():
        if intent == "chat":
            continue
        if re.search(pattern, text_lower):
            matched.append(intent)
    matched.sort(key=lambda i: INTENT_PRIORITY.get(i, 0), reverse=True)
    return matched


def route(text: str) -> str:
    """
    Route user input to appropriate handler

    Args:
        text: User query text

    Returns:
        Intent string
    """
    return detect_intent(text)


def route_with_confidence(text: str) -> tuple[str, float]:
    """
    Route with confidence score

    Args:
        text: User query text

    Returns:
        Tuple of (intent, confidence)
    """
    return detect_intent_with_confidence(text)


def should_use_llm_routing(confidence: float) -> bool:
    """
    Determine if LLM should be used for routing based on confidence

    Args:
        confidence: Confidence score from pattern matching

    Returns:
        True if LLM should be used for disambiguation
    """
    return confidence < CONFIDENCE_THRESHOLD
