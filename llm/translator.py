import logging

from ollama import Client

from core.config import settings

log = logging.getLogger("zari")


class Translator:
    def __init__(self):
        self.client = Client(host=settings.ollama_url)
        self.model = settings.ollama_model

    def uz_to_en(self, text: str) -> str:
        prompt = (
            "You are a translator. Translate the following Uzbek text to English. "
            "Respond with ONLY the English translation, no explanations, no quotes.\n\n"
            f"Uzbek: {text}\n\nEnglish:"
        )
        try:
            resp = self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
            )
            translation = resp["message"]["content"].strip().strip('"').strip("'")
            log.debug("UZ->EN: '%s' -> '%s'", text, translation)
            return translation
        except Exception as e:
            log.error("Tarjima xatosi (UZ->EN): %s", e)
            return text

    def en_to_uz(self, text: str) -> str:
        prompt = (
            "You are a translator. Translate the following English text to Uzbek. "
            "Respond with ONLY the Uzbek translation, no explanations, no quotes.\n\n"
            f"English: {text}\n\nUzbek:"
        )
        try:
            resp = self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
            )
            translation = resp["message"]["content"].strip().strip('"').strip("'")
            log.debug("EN->UZ: '%s' -> '%s'", text, translation)
            return translation
        except Exception as e:
            log.error("Tarjima xatosi (EN->UZ): %s", e)
            return text
