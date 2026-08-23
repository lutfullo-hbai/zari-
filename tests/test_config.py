

from core.config import Settings


class TestSettings:
    """Test configuration settings"""

    def test_default_values(self):
        """Test default configuration values"""
        s = Settings(_env_file=None)
        assert s.ollama_url == "http://localhost:11434"
        assert s.ollama_model == "qwen2.5:3b"
        assert s.groq_model == "llama-3.3-70b-versatile"
        assert s.groq_api_key == ""
        assert s.llm_provider == "ollama"
        assert s.wake_word == "jarvis"
        assert s.tts_voice == "uz-UZ-MadinaNeural"
        assert s.enable_translation == False
        assert s.whisper_language == "uz"
        assert s.log_level == "INFO"

    def test_env_override(self):
        """Test environment variable override"""
        s = Settings(
            ollama_url="http://custom:11434",
            ollama_model="llama3",
            groq_model="llama-3.1-8b-instant",
            llm_provider="ollama",
            wake_word="zari"
        )
        assert s.ollama_url == "http://custom:11434"
        assert s.ollama_model == "llama3"
        assert s.groq_model == "llama-3.1-8b-instant"
        assert s.llm_provider == "ollama"
        assert s.wake_word == "zari"

    def test_partial_override(self):
        """Test partial override"""
        s = Settings(ollama_url="http://remote:11434")
        assert s.ollama_url == "http://remote:11434"
        # Other defaults should remain
        assert s.ollama_model == "qwen2.5:3b"
        assert s.wake_word == "jarvis"

    def test_audio_device_settings(self):
        """Test audio device configuration"""
        s = Settings(
            audio_input_device=1,
            audio_output_device=2,
            audio_output_sample_rate=44100
        )
        assert s.audio_input_device == 1
        assert s.audio_output_device == 2
        assert s.audio_output_sample_rate == 44100

    def test_telegram_email_settings(self):
        """Test optional telegram and email settings"""
        s = Settings()
        # These should be empty by default
        assert s.telegram_token == ""
        assert s.email_address == ""

        s2 = Settings(
            telegram_token="test_token",
            email_address="test@example.com"
        )
        assert s2.telegram_token == "test_token"
        assert s2.email_address == "test@example.com"

    def test_smtp_settings(self):
        """Test SMTP settings defaults and override"""
        s = Settings(_env_file=None)
        assert s.smtp_host == ""
        assert s.smtp_port == 587
        assert s.smtp_username == ""
        assert s.smtp_password == ""
        assert s.smtp_use_tls is True
        assert s.sender_address == ""
        assert s.default_recipient == ""

        s2 = Settings(
            smtp_host="smtp.gmail.com",
            smtp_port=465,
            smtp_username="user@gmail.com",
            smtp_password="app_password",
            smtp_use_tls=False,
            sender_address="from@gmail.com",
            default_recipient="to@gmail.com",
        )
        assert s2.smtp_host == "smtp.gmail.com"
        assert s2.smtp_port == 465
        assert s2.smtp_username == "user@gmail.com"
        assert s2.smtp_password == "app_password"
        assert s2.smtp_use_tls is False
        assert s2.sender_address == "from@gmail.com"
        assert s2.default_recipient == "to@gmail.com"

    def test_translation_disabled(self):
        """Test disabling translation"""
        s = Settings(enable_translation=False)
        assert s.enable_translation == False

    def test_log_level_variations(self):
        """Test different log levels"""
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            s = Settings(log_level=level)
            assert s.log_level == level

    def test_database_url_format(self):
        """Test database URL"""
        s = Settings()
        # Default uses postgresql
        assert "postgresql" in s.database_url

    def test_redis_url_format(self):
        """Test Redis URL"""
        s = Settings()
        # Default Redis URL
        assert "redis://" in s.redis_url or "localhost" in s.redis_url

    def test_custom_db_and_redis(self):
        """Test custom database and Redis URLs"""
        s = Settings(
            database_url="postgresql://user:pass@remote/db",
            redis_url="redis://remote:6380"
        )
        assert s.database_url == "postgresql://user:pass@remote/db"
        assert s.redis_url == "redis://remote:6380"

    def test_invalid_log_level(self):
        """Test with invalid log level (should still work)"""
        s = Settings(log_level="INVALID")
        # Should not raise, but will log as INFO if invalid
        assert s.log_level == "INVALID"

    def test_type_coercion(self):
        """Test type coercion for numeric settings"""
        s = Settings(
            audio_input_device=None,
            audio_output_sample_rate=48000
        )
        assert s.audio_input_device is None
        assert isinstance(s.audio_output_sample_rate, int)


class TestSettingsEdgeCases:
    """Edge cases for settings"""

    def test_empty_wake_word(self):
        """Test with empty wake word"""
        s = Settings(wake_word="")
        assert s.wake_word == ""

    def test_special_characters_in_settings(self):
        """Test with special characters in URLs"""
        s = Settings(
            database_url="postgresql://user:p@ss$w0rd@host/db?param=value",
            redis_url="redis://:p@ssw0rd@localhost:6379"
        )
        assert "@" in s.database_url
        assert "@" in s.redis_url

    def test_very_long_token(self):
        """Test with very long token"""
        long_token = "x" * 1000
        s = Settings(telegram_token=long_token)
        assert s.telegram_token == long_token

    def test_unicode_in_settings(self):
        """Test with unicode characters"""
        s = Settings(
            wake_word="зари",
            tts_voice="uz-UZ-MadinaNeural"
        )
        assert s.wake_word == "зари"
        assert s.tts_voice == "uz-UZ-MadinaNeural"
