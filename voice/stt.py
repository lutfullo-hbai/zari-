import logging
import re

from faster_whisper import WhisperModel

from core.config import settings

log = logging.getLogger("zari")

STT_CORRECTIONS: dict[str, str] = {
    "enxten": "Einstein",
    "enxte": "Einstein",
    "enste": "Einstein",
    "enxin": "Einstein",
    "enksin": "Einstein",
    "telefram": "Telegram",
    "telegramm": "Telegram",
    "paison": "Python",
    "payton": "Python",
    "javris": "Jarvis",
    "djevis": "Jarvis",
    "nayn": "n8n",
    "eneyn": "n8n",
    "kortana": "Cortana",
    "vindovs": "Windows",
    "vindouz": "Windows",
    "maykrosoft": "Microsoft",
    "mikrosoft": "Microsoft",
    "gugl": "Google",
    "gugol": "Google",
    "aplp": "Apple",
    "amazn": "Amazon",
    "neyral": "neyron",
    "kompьuter": "kompyuter",
    "printер": "printer",
    "skanер": "skaner",
}


def correct_stt(text: str) -> str:
    corrected = text
    for wrong, correct in STT_CORRECTIONS.items():
        pattern = re.compile(re.escape(wrong), re.IGNORECASE)
        corrected = pattern.sub(correct, corrected)
    return corrected


class SpeechToText:
    def __init__(self, model_name: str = "small"):
        self.model = WhisperModel(model_name, compute_type="int8")
        self.language = settings.whisper_language
        log.info("Whisper model: %s, compute: int8, language: %s", model_name, self.language or "auto")

    def transcribe(self, audio_path: str) -> str:
        segments, info = self.model.transcribe(audio_path, language=self.language or None)
        log.debug("Whisper detected language: %s (probability %.2f)", info.language, info.language_probability)
        raw_text = " ".join(seg.text for seg in segments).strip()
        corrected = correct_stt(raw_text)
        if raw_text != corrected:
            log.info("STT corrected: '%s' -> '%s'", raw_text, corrected)
        return corrected
