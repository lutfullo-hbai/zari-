import logging
import re

log = logging.getLogger("zari")


INTENT_PRIORITY: dict[str, int] = {
    "network": 85,
    "clipboard": 80,
    "screenshot": 80,
    "filemanager": 80,
    "weather": 70,
    "timer": 65,
    "calculator": 60,
    "note": 55,
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
    "system_info": r"\b(kompyuter|tizim|system|protsessor|CPU|cpu|ram|xotira|disk|uptime|python|versiya|holat|ma'lumot)\b",
    "email": r"\b(gmail|email|mail|xat|yubor|send)\b",
    "music": r"\b(musiqa|qo.?y|qo.?shiq|music|song|play|tingla|yoq)\b",
    "workflow": r"\b(workflow|flow|automation|template|n8n|telegram|slack|google sheets|sheet|webhook|valyuta|oltin|currency)\b",
    "note": r"\b(yozib ol|esla|eslatma|note|saqla|yodda)\b",
    "timer": r"\b(timer|daqiqa|soniya|minut|sekund|vaqt o.lcha)\b",
    "calculator": r"\b(hisobla|calculate|necha bo.ladi)\b",
    "clipboard": r"\b(clipboard|buffer|nusxa)\b",
    "screenshot": r"\b(skrin|screen|rasm ola)\b",
    "filemanager": r"\b(fayl|folder|papka|katalog|file|directory)\b",
    "network": r"\b(ip|dns|ping|network|tarmoq)\b",
    "wiki": r"\b(eslab qol|uni esla|esimda saqla|bil|ismim|yoshim|manzil)\b",
    "search": (
        r"\b(qidir|top|izla|search|find|"
        r"sabab|define|meaning|nima degan|"
        r"ma.lumot|tushuntir|izohla)"
    ),
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
        log.debug(
            "Intent detection: %s (confidence: %.2f)",
            best_intent,
            best_confidence
        )
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
