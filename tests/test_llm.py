import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from llm.ollama import OllamaClient
from llm.translator import Translator


class TestOllamaClient:
    """Test OllamaClient functionality"""
    
    def test_init(self):
        """Test OllamaClient initialization"""
        with patch('ollama.Client'):
            client = OllamaClient()
            assert client.model == "qwen2.5:3b"
    
    @pytest.mark.asyncio
    async def test_chat_async(self):
        """Test async chat method"""
        mock_client = MagicMock()
        mock_response = {"message": {"content": "Javob berish"}}
        mock_client.chat.return_value = mock_response
        
        with patch('ollama.Client', return_value=mock_client):
            client = OllamaClient()
            
            messages = [{"role": "user", "content": "Salom"}]
            response = await client.chat_async(messages)
            
            assert response == "Javob berish"
    
    def test_chat_sync(self):
        """Test sync chat method"""
        mock_client = MagicMock()
        mock_response = {"message": {"content": "Javob"}}
        mock_client.chat.return_value = mock_response
        
        with patch('ollama.Client', return_value=mock_client):
            client = OllamaClient()
            response = client.chat(messages=[{"role": "user", "content": "test"}])
            assert response == "Javob"
    
    @pytest.mark.asyncio
    async def test_chat_stream(self):
        """Test streaming chat"""
        mock_chunks = [
            {"message": {"content": "Part "}},
            {"message": {"content": "1"}},
        ]
        mock_client = MagicMock()
        mock_client.chat.return_value = iter(mock_chunks)
        
        with patch('ollama.Client', return_value=mock_client):
            client = OllamaClient()
            
            chunks = []
            async for chunk in client.chat_stream([{"role": "user", "content": "test"}]):
                chunks.append(chunk)
            
            assert len(chunks) == 2
    
    @pytest.mark.asyncio
    async def test_chat_async_timeout(self):
        """Test async chat raises TimeoutError when LLM is too slow"""
        def slow_chat(*args, **kwargs):
            import time
            time.sleep(0.5)

        mock_client = MagicMock()
        mock_client.chat = slow_chat

        with patch('ollama.Client', return_value=mock_client):
            client = OllamaClient()

            with pytest.raises(asyncio.TimeoutError):
                await client.chat_async(
                    [{"role": "user", "content": "test"}],
                    timeout=0.05,
                )

    @pytest.mark.asyncio
    async def test_chat_stream_async(self):
        """Test async streaming chat"""
        mock_chunks = [
            {"message": {"content": "Part "}},
            {"message": {"content": "2"}},
        ]
        mock_client = MagicMock()
        mock_client.chat.return_value = iter(mock_chunks)

        with patch('ollama.Client', return_value=mock_client):
            client = OllamaClient()

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
        with patch('llm.translator.Client'):
            translator = Translator()
            assert translator.model == "qwen2.5:3b"
    
    def test_uz_to_en(self):
        """Test Uzbek to English translation"""
        mock_client = MagicMock()
        mock_response = {"message": {"content": "Hello"}}
        mock_client.chat.return_value = mock_response
        
        with patch('llm.translator.Client', return_value=mock_client):
            translator = Translator()
            result = translator.uz_to_en("Salom")
            
            assert result == "Hello"
    
    def test_en_to_uz(self):
        """Test English to Uzbek translation"""
        mock_client = MagicMock()
        mock_response = {"message": {"content": "Salom"}}
        mock_client.chat.return_value = mock_response
        
        with patch('llm.translator.Client', return_value=mock_client):
            translator = Translator()
            result = translator.en_to_uz("Hello")
            
            assert result == "Salom"
    
    def test_translation_error_handling(self):
        """Test error handling in translation"""
        mock_client = MagicMock()
        mock_client.chat.side_effect = Exception("Network error")
        
        with patch('llm.translator.Client', return_value=mock_client):
            translator = Translator()
            # Should return original text on error
            result = translator.uz_to_en("Salom")
            assert result == "Salom"
    
    def test_translation_strips_quotes(self):
        """Test that translator strips quotes from response"""
        mock_client = MagicMock()
        mock_response = {"message": {"content": '"Hello"'}}
        mock_client.chat.return_value = mock_response
        
        with patch('llm.translator.Client', return_value=mock_client):
            translator = Translator()
            result = translator.uz_to_en("Salom")
            
            # Quotes should be stripped
            assert result == "Hello"
    
    def test_translation_strips_apostrophes(self):
        """Test that translator strips apostrophes"""
        mock_client = MagicMock()
        mock_response = {"message": {"content": "'Hello'"}}
        mock_client.chat.return_value = mock_response
        
        with patch('llm.translator.Client', return_value=mock_client):
            translator = Translator()
            result = translator.uz_to_en("Salom")
            
            assert result == "Hello"


class TestLLMEdgeCases:
    """Edge cases for LLM"""
    
    def test_empty_message(self):
        """Test with empty message"""
        mock_client = MagicMock()
        mock_response = {"message": {"content": ""}}
        mock_client.chat.return_value = mock_response
        
        with patch('ollama.Client', return_value=mock_client):
            client = OllamaClient()
            response = client.chat([{"role": "user", "content": ""}])
            assert response == ""
    
    def test_very_long_response(self):
        """Test with very long response"""
        long_text = "x" * 10000
        mock_client = MagicMock()
        mock_response = {"message": {"content": long_text}}
        mock_client.chat.return_value = mock_response
        
        with patch('ollama.Client', return_value=mock_client):
            client = OllamaClient()
            response = client.chat([{"role": "user", "content": "test"}])
            assert len(response) == 10000
    
    def test_special_characters_in_response(self):
        """Test with special characters"""
        mock_client = MagicMock()
        special_text = "Hello\n\t\"quoted\" 🎉 <tag>"
        mock_response = {"message": {"content": special_text}}
        mock_client.chat.return_value = mock_response
        
        with patch('ollama.Client', return_value=mock_client):
            client = OllamaClient()
            response = client.chat([{"role": "user", "content": "test"}])
            assert response == special_text
