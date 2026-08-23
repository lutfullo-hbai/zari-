import asyncio
from unittest.mock import MagicMock, patch

import pytest

from core.config import settings
from llm.factory import create_llm_client
from llm.groq_client import GroqClient
from llm.translator import Translator


def _make_groq_response(content: str):
    """Groq API javob formatini yaratadi."""
    choice = MagicMock()
    choice.message.content = content
    response = MagicMock()
    response.choices = [choice]
    return response


class TestGroqClient:
    """Test GroqClient functionality"""

    def test_init(self):
        """Test GroqClient initialization"""
        with patch('llm.groq_client.Groq'):
            client = GroqClient()
            assert client.model == "llama-3.3-70b-versatile"

    @pytest.mark.asyncio
    async def test_chat_async(self):
        """Test async chat method"""
        mock_groq = MagicMock()
        mock_groq.chat.completions.create.return_value = _make_groq_response("Javob berish")

        with patch('llm.groq_client.Groq', return_value=mock_groq):
            client = GroqClient(client=mock_groq)
            messages = [{"role": "user", "content": "Salom"}]
            response = await client.chat_async(messages)
            assert response == "Javob berish"

    def test_chat_sync(self):
        """Test sync chat method"""
        mock_groq = MagicMock()
        mock_groq.chat.completions.create.return_value = _make_groq_response("Javob")

        client = GroqClient(client=mock_groq)
        response = client.chat(messages=[{"role": "user", "content": "test"}])
        assert response == "Javob"

    @pytest.mark.asyncio
    async def test_chat_async_timeout(self):
        """Test async chat raises TimeoutError when LLM is too slow"""
        def slow_create(*args, **kwargs):
            import time
            time.sleep(0.5)
            return _make_groq_response("")

        mock_groq = MagicMock()
        mock_groq.chat.completions.create.side_effect = slow_create

        client = GroqClient(client=mock_groq)

        with pytest.raises(asyncio.TimeoutError):
            await client.chat_async(
                [{"role": "user", "content": "test"}],
                timeout=0.05,
            )

    @pytest.mark.asyncio
    async def test_chat_stream(self):
        """Test streaming chat"""
        chunk1 = MagicMock()
        chunk1.choices = [MagicMock(delta=MagicMock(content="Part "))]

        chunk2 = MagicMock()
        chunk2.choices = [MagicMock(delta=MagicMock(content="1"))]

        mock_groq = MagicMock()
        mock_groq.chat.completions.create.return_value = [chunk1, chunk2]

        client = GroqClient(client=mock_groq)

        chunks = []
        async for chunk in client.chat_stream([{"role": "user", "content": "test"}]):
            chunks.append(chunk)

        assert len(chunks) == 2

    @pytest.mark.asyncio
    async def test_chat_stream_async(self):
        """Test async streaming chat"""
        chunk1 = MagicMock()
        chunk1.choices = [MagicMock(delta=MagicMock(content="Part "))]

        chunk2 = MagicMock()
        chunk2.choices = [MagicMock(delta=MagicMock(content="2"))]

        mock_groq = MagicMock()
        mock_groq.chat.completions.create.return_value = [chunk1, chunk2]

        client = GroqClient(client=mock_groq)

        chunks = []
        async for chunk in client.chat_stream_async([{"role": "user", "content": "test"}], timeout=5):
            chunks.append(chunk)

        assert len(chunks) == 2
        assert chunks[0] == "Part "
        assert chunks[1] == "2"


class TestTranslator:
    """Test Translator functionality"""

    def test_init(self):
        """Test Translator initialization"""
        with patch('llm.groq_client.Groq'):
            translator = Translator()
            assert translator._llm.model == "llama-3.3-70b-versatile"

    def test_uz_to_en(self):
        """Test Uzbek to English translation"""
        mock_groq = MagicMock()
        mock_groq.chat.completions.create.return_value = _make_groq_response("Hello")

        translator = Translator(client=GroqClient(client=mock_groq))
        result = translator.uz_to_en("Salom")
        assert result == "Hello"

    def test_en_to_uz(self):
        """Test English to Uzbek translation"""
        mock_groq = MagicMock()
        mock_groq.chat.completions.create.return_value = _make_groq_response("Salom")

        translator = Translator(client=GroqClient(client=mock_groq))
        result = translator.en_to_uz("Hello")
        assert result == "Salom"

    def test_translation_error_handling(self):
        """Test error handling in translation"""
        mock_groq = MagicMock()
        mock_groq.chat.completions.create.side_effect = Exception("Network error")

        translator = Translator(client=GroqClient(client=mock_groq))
        result = translator.uz_to_en("Salom")
        assert result == "Salom"

    def test_translation_strips_quotes(self):
        """Test that translator strips quotes from response"""
        mock_groq = MagicMock()
        mock_groq.chat.completions.create.return_value = _make_groq_response('"Hello"')

        translator = Translator(client=GroqClient(client=mock_groq))
        result = translator.uz_to_en("Salom")
        assert result == "Hello"

    def test_translation_strips_apostrophes(self):
        """Test that translator strips apostrophes"""
        mock_groq = MagicMock()
        mock_groq.chat.completions.create.return_value = _make_groq_response("'Hello'")

        translator = Translator(client=GroqClient(client=mock_groq))
        result = translator.uz_to_en("Salom")
        assert result == "Hello"


class TestLLMEdgeCases:
    """Edge cases for LLM"""

    def test_empty_message(self):
        """Test with empty message"""
        mock_groq = MagicMock()
        mock_groq.chat.completions.create.return_value = _make_groq_response("")

        client = GroqClient(client=mock_groq)
        response = client.chat([{"role": "user", "content": ""}])
        assert response == ""

    def test_very_long_response(self):
        """Test with very long response"""
        long_text = "x" * 10000
        mock_groq = MagicMock()
        mock_groq.chat.completions.create.return_value = _make_groq_response(long_text)

        client = GroqClient(client=mock_groq)
        response = client.chat([{"role": "user", "content": "test"}])
        assert len(response) == 10000

    def test_special_characters_in_response(self):
        """Test with special characters"""
        mock_groq = MagicMock()
        special_text = "Hello\n\t\"quoted\" 🎉 <tag>"
        mock_groq.chat.completions.create.return_value = _make_groq_response(special_text)

        client = GroqClient(client=mock_groq)
        response = client.chat([{"role": "user", "content": "test"}])
        assert response == special_text


class TestLLMFactory:
    """LLM client factory funksiyasi testlari."""

    def test_create_groq_client(self):
        with patch('llm.factory.GroqClient') as mock_cls:
            client = create_llm_client("groq")
            mock_cls.assert_called_once_with()
            assert client is mock_cls.return_value

    def test_create_ollama_client(self):
        with patch('llm.factory.OllamaClient') as mock_cls:
            client = create_llm_client("ollama")
            mock_cls.assert_called_once_with()
            assert client is mock_cls.return_value

    def test_unknown_provider_falls_back_to_groq(self):
        with patch('llm.factory.GroqClient') as mock_groq, \
                patch('llm.factory.OllamaClient') as mock_ollama:
            client = create_llm_client("unknown")
            mock_groq.assert_called_once_with()
            mock_ollama.assert_not_called()
            assert client is mock_groq.return_value

    def test_case_insensitive_provider(self):
        with patch('llm.factory.OllamaClient') as mock_cls:
            create_llm_client("  OLLAMA ")
            mock_cls.assert_called_once_with()

    def test_uses_settings_provider(self):
        with patch('llm.factory.GroqClient') as mock_groq, \
                patch('llm.factory.OllamaClient') as mock_ollama, \
                patch.object(settings, "llm_provider", "groq"):
            client = create_llm_client()
            mock_groq.assert_called_once_with()
            mock_ollama.assert_not_called()
            assert client is mock_groq.return_value
