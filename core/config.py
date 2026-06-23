from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"

    database_url: str = "postgresql:///zari"
    redis_url: str = "redis://localhost:6379/0"

    wake_word: str = "jarvis"
    tts_voice: str = "uz-UZ-MadinaNeural"

    telegram_token: str = ""
    email_address: str = ""

    enable_translation: bool = True
    whisper_language: str = "uz"
    audio_input_device: int | None = None
    audio_output_device: int | None = None
    audio_output_sample_rate: int = 48000

    log_level: str = "INFO"
    log_format: str = "json"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
