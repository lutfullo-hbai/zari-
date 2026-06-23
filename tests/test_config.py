from core.config import Settings


def test_default_values():
    s = Settings()
    assert s.ollama_url == "http://localhost:11434"
    assert s.ollama_model == "qwen2.5:3b"
    assert s.wake_word == "zari"
    assert s.tts_voice == "uz-UZ-MadinaNeural"


def test_env_override():
    s = Settings(ollama_url="http://custom:11434", ollama_model="llama3")
    assert s.ollama_url == "http://custom:11434"
    assert s.ollama_model == "llama3"
