import logging

from faster_whisper import WhisperModel

from core.config import settings

log = logging.getLogger("zari")


class SpeechToText:
    def __init__(self, model_name: str = "small"):
        self.model = WhisperModel(model_name, compute_type="int8")
        self.language = settings.whisper_language
        log.info("Whisper model: %s, compute: int8, language: %s", model_name, self.language or "auto")

    def transcribe(self, audio_path: str) -> str:
        segments, info = self.model.transcribe(audio_path, language=self.language or None)
        log.debug("Whisper detected language: %s (probability %.2f)", info.language, info.language_probability)
        return " ".join(seg.text for seg in segments).strip()

    def transcribe_array(self, audio_array, sr: int = 16000) -> str:
        segments, _ = self.model.transcribe(audio_array, beam_size=1, language=self.language or None)
        return " ".join(seg.text for seg in segments).strip()
