import ollama
from core.config import settings


class OllamaClient:
    def __init__(self):
        self.client = ollama.Client(host=settings.ollama_url)
        self.model = settings.ollama_model

    def chat(self, messages: list[dict]) -> str:
        response = self.client.chat(model=self.model, messages=messages)
        return response["message"]["content"]

    async def chat_stream(self, messages: list[dict]):
        stream = self.client.chat(model=self.model, messages=messages, stream=True)
        for chunk in stream:
            yield chunk["message"]["content"]
