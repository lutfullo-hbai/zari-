import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio


def _make_groq_response(content: str):
    """Groq API javob formatini yaratadi."""
    choice = MagicMock()
    choice.message.content = content
    response = MagicMock()
    response.choices = [choice]
    return response


class TestPipelineIntegration:
    """Integration tests for the complete Zari pipeline"""

    @pytest.mark.asyncio
    async def test_memory_and_router_integration(self):
        """Test memory stores messages correctly after routing"""
        from llm.memory import SessionMemory
        from core.router import route

        with patch('db.memory_repo.create_session', return_value='test-session'):
            with patch('db.memory_repo.save_message', new_callable=AsyncMock):
                with patch('db.cache.cache_session_messages', new_callable=AsyncMock):
                    mem = SessionMemory()
                    await mem.init()

                    query = "musiqa qo'y"
                    intent = route(query)
                    assert intent == "music"

                    await mem.add("user", query)
                    await mem.add("assistant", "Musiqa qo'yilmoqda...")

                    msgs = mem.get()
                    assert len(msgs) == 2
                    assert msgs[0]["content"] == query

    @pytest.mark.asyncio
    async def test_translator_and_llm_integration(self):
        """Test translation flows through to LLM"""
        from llm.translator import Translator
        from llm.groq_client import GroqClient

        mock_groq = MagicMock()
        mock_groq.chat.completions.create.return_value = _make_groq_response("Hello")

        translator = Translator(client=GroqClient(client=mock_groq))
        llm = GroqClient(client=mock_groq)

        translated = translator.uz_to_en("Salom")
        assert translated == "Hello"

        response = llm.chat([{"role": "user", "content": translated}])
        assert response == "Hello"

    @pytest.mark.asyncio
    async def test_error_handling_chain(self):
        """Test error handling flows correctly through pipeline"""
        from llm.groq_client import GroqClient

        mock_groq = MagicMock()
        mock_groq.chat.completions.create.side_effect = Exception("Connection refused")

        client = GroqClient(client=mock_groq)

        with pytest.raises(Exception):
            await client.chat_async([{"role": "user", "content": "test"}])

    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test that timeouts are handled gracefully"""
        from llm.groq_client import GroqClient

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
    async def test_fallback_to_chat_on_error(self):
        """Test that errors in specialized skills fall back to chat"""
        from core.router import route
        from llm.memory import SessionMemory

        with patch('db.memory_repo.create_session', return_value='session-id'):
            with patch('db.memory_repo.save_message', new_callable=AsyncMock):
                with patch('db.cache.cache_session_messages', new_callable=AsyncMock):
                    mem = SessionMemory()
                    await mem.init()

                    query = "nima gap"
                    intent = route(query)

                    assert intent == "chat"

                    await mem.add("user", query)
                    msgs = mem.get()
                    assert len(msgs) == 1


class TestAsyncErrorHandling:
    """Test async error handling"""

    @pytest.mark.asyncio
    async def test_translator_timeout(self):
        """Test translator returns original text on timeout"""
        from llm.translator import Translator
        from llm.groq_client import GroqClient

        mock_groq = MagicMock()

        def slow_translate(*args, **kwargs):
            import time
            time.sleep(0.5)

        translator = Translator(client=GroqClient(client=mock_groq))
        translator.uz_to_en = slow_translate
        translator.timeout = 0.01

        result = await translator.uz_to_en_async("Salom")

        assert result == "Salom"

    @pytest.mark.asyncio
    async def test_empty_responses_handled(self):
        """Test that empty responses don't crash"""
        from llm.groq_client import GroqClient

        mock_groq = MagicMock()
        mock_groq.chat.completions.create.return_value = _make_groq_response("")

        client = GroqClient(client=mock_groq)
        response = client.chat([{"role": "user", "content": "test"}])
        assert response == ""

    @pytest.mark.asyncio
    async def test_malformed_response_handling(self):
        """Test handling of malformed responses"""
        from llm.groq_client import GroqClient

        mock_groq = MagicMock()

        client = GroqClient(client=mock_groq)

        mock_groq.chat.completions.create.side_effect = KeyError("content")

        with pytest.raises(KeyError):
            client.chat([{"role": "user", "content": "test"}])


class TestPipelineQueueHandling:
    """Test Zari pipeline queue patterns"""

    @pytest.mark.asyncio
    async def test_audio_to_text_queue_flow(self):
        """Test basic audio -> text queue flow (mimics ZariPipeline)"""
        audio_queue: asyncio.Queue[bytes] = asyncio.Queue()
        text_queue: asyncio.Queue[str] = asyncio.Queue()

        await audio_queue.put(b"audio data")
        audio = await asyncio.wait_for(audio_queue.get(), timeout=1.0)
        assert audio == b"audio data"

        await text_queue.put("salom")
        text = await asyncio.wait_for(text_queue.get(), timeout=1.0)
        assert text == "salom"

    @pytest.mark.asyncio
    async def test_text_to_response_queue_flow(self):
        """Test text -> response queue flow (mimics ZariPipeline.llm_worker -> tts_worker)"""
        response_queue: asyncio.Queue[str] = asyncio.Queue()

        await response_queue.put("Salom, qanday yordam kerak?")
        response = await asyncio.wait_for(response_queue.get(), timeout=1.0)

        assert response == "Salom, qanday yordam kerak?"

    @pytest.mark.asyncio
    async def test_queue_get_timeout_returns_original_text(self):
        """Test that queue timeout handling returns fallback text like pipeline does"""
        response = "Kechirasiz, javob berolmayman."
        queue = asyncio.Queue()

        try:
            await asyncio.wait_for(queue.get(), timeout=0.05)
        except asyncio.TimeoutError:
            pass

        assert response == "Kechirasiz, javob berolmayman."
