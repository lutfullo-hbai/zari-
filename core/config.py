from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Ollama — local-first asosiy provayder
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"

    # Groq API — tez cloud fallback
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # LLM provayderni tanlash: "ollama" | "groq"
    llm_provider: str = "ollama"

    # Agent Brain — ko'p intentli murakkab so'rovlarda LLM reja tuzadi
    enable_brain: bool = True

    database_url: str = "postgresql:///zari"
    redis_url: str = "redis://localhost:6379/0"

    wake_word: str = "jarvis"
    wake_threshold: float = 0.5
    wake_word_models: list[str] | None = None

    tts_voice: str = "uz-UZ-MadinaNeural"
    tts_engine: str = "edge"  # "edge" | "piper"
    piper_model_path: str = ""
    piper_voice: str = "en_US-lessac-medium"

    telegram_token: str = ""
    email_address: str = ""

    # SMTP (EmailSkill uchun)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    sender_address: str = ""
    default_recipient: str = ""

    # UZ<->EN tarjima — zamonaviy modellar o'zbekchani biladi, odatda kerakmas
    # (har bir xabarga 2 ta ortiqcha LLM chaqiruv qiladi)
    enable_translation: bool = False
    whisper_language: str = "uz"
    audio_input_device: int | None = None
    audio_output_device: int | None = None
    audio_output_sample_rate: int = 48000

    perplexica_url: str = ""
    perplexica_focus_mode: str = "web"
    search_backend: str = "auto"

    weather_api_key: str = ""
    n8n_url: str = "http://localhost:5678"
    n8n_api_key: str = ""
    n8n_templates_api_url: str = "http://localhost:8000"
    n8n_workflows_dir: str = ""

    rate_limit_max_calls: int = 10
    rate_limit_window: int = 60

    web_host: str = "0.0.0.0"
    web_port: int = 8080
    # Dashboard same-origin ishlaydi; tashqi klientlar uchun aniq origin ko'rsatilsin
    web_cors_origins: list[str] = [
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]
    # Bo'sh bo'lsa auth o'chirilgan (local dev). LAN/server uchun majburiy qiling.
    web_api_key: str = ""

    log_level: str = "INFO"
    log_format: str = "json"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
