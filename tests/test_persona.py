import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from llm.persona import UserPersona


class MockPool:
    def acquire(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    def fetchrow(self, *args, **kwargs):
        return AsyncMock(return_value=None)()

    def fetch(self, *args, **kwargs):
        return AsyncMock(return_value=[])()

    def execute(self, *args, **kwargs):
        return AsyncMock(return_value="DELETE 0")()


@pytest.fixture
def persona():
    return UserPersona()


class TestUserPersona:
    def test_init(self, persona):
        assert persona._cache is None

    @pytest.mark.asyncio
    async def test_learn_fact(self, persona):
        with patch("llm.persona.UserPersona.set", new_callable=AsyncMock) as mock_set:
            await persona.learn_fact("name", "Ali", "identity")
            mock_set.assert_called_once_with("name", "Ali", "identity", source="manual")

    @pytest.mark.asyncio
    async def test_get_summary_empty(self, persona):
        with patch.object(persona, "get_all", return_value=[]):
            summary = await persona.get_summary()
            assert summary == "Yangi foydalanuvchi"

    @pytest.mark.asyncio
    async def test_get_summary_with_data(self, persona):
        rows = [
            {"key": "name", "value": "Ali", "category": "identity"},
            {"key": "age", "value": "25", "category": "identity"},
            {"key": "location", "value": "Toshkent", "category": "identity"},
        ]
        with patch.object(persona, "get_all", return_value=rows):
            summary = await persona.get_summary()
            assert "Ali" in summary
            assert "25" in summary
            assert "Toshkent" in summary

    @pytest.mark.asyncio
    async def test_get_system_text_empty(self, persona):
        with patch.object(persona, "get_all", return_value=[]):
            text = await persona.get_system_text()
            assert text == ""

    @pytest.mark.asyncio
    async def test_get_system_text_with_data(self, persona):
        rows = [
            {"key": "name", "value": "Ali", "category": "identity"},
            {"key": "music_genre", "value": "jazz", "category": "interest"},
        ]
        with patch.object(persona, "get_all", return_value=rows):
            text = await persona.get_system_text()
            assert "Ismingiz" in text
            assert "Ali" in text
            assert "Sevimli musiqangiz" in text
            assert "jazz" in text

    def test_parse_llm_response_valid(self, persona):
        raw = '[{"key": "name", "value": "Ali", "category": "identity"}]'
        result = persona._parse_llm_response(raw)
        assert len(result) == 1
        assert result[0]["key"] == "name"
        assert result[0]["value"] == "Ali"

    def test_parse_llm_response_empty(self, persona):
        result = persona._parse_llm_response("[]")
        assert result == []

    def test_parse_llm_response_invalid(self, persona):
        result = persona._parse_llm_response("not json")
        assert result == []

    def test_parse_llm_response_partial(self, persona):
        raw = """Here is the result:
        [{"key": "name", "value": "Ali", "category": "identity"}]
        """
        result = persona._parse_llm_response(raw)
        assert len(result) == 1
        assert result[0]["value"] == "Ali"

    def test_parse_llm_response_multiple(self, persona):
        raw = """[
            {"key": "name", "value": "Ali", "category": "identity"},
            {"key": "music_genre", "value": "jazz", "category": "interest"}
        ]"""
        result = persona._parse_llm_response(raw)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_extract_short_text_skipped(self, persona):
        llm = MagicMock()
        await persona.extract_from_conversation("ab", llm)
        llm.chat_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_extract_timeout(self, persona):
        llm = MagicMock()
        llm.chat_async = AsyncMock(side_effect=asyncio.TimeoutError)
        await persona.extract_from_conversation("mening ismim Ali", llm)

    @pytest.mark.asyncio
    async def test_get_system_text_preserves_order(self, persona):
        rows = [
            {"key": "name", "value": "Ali", "category": "identity"},
            {"key": "profession", "value": "dasturchi", "category": "identity"},
        ]
        with patch.object(persona, "get_all", return_value=rows):
            text = await persona.get_system_text()
            assert text.index("Ismingiz") < text.index("Kasbingiz")


    def test_parse_llm_response_value_with_brackets(self, persona):
        raw = '[{"key": "test", "value": "some [text]", "category": "identity"}]'
        result = persona._parse_llm_response(raw)
        assert len(result) == 1
        assert result[0]["value"] == "some [text]"

    def test_parse_llm_response_multiple_elements_preserved(self, persona):
        raw = """[
            {"key": "name", "value": "Ali", "category": "identity"},
            {"key": "age", "value": "25", "category": "identity"},
            {"key": "hobby", "value": "coding", "category": "interest"}
        ]"""
        result = persona._parse_llm_response(raw)
        assert len(result) == 3

    def test_parse_llm_response_markdown_code_block(self, persona):
        raw = """Here is the info:
```json
[{"key": "name", "value": "Ali", "category": "identity"}]
```"""
        result = persona._parse_llm_response(raw)
        assert len(result) == 1
        assert result[0]["value"] == "Ali"

    def test_parse_llm_response_empty_string(self, persona):
        result = persona._parse_llm_response("")
        assert result == []

    def test_parse_llm_response_wrapped_in_text(self, persona):
        raw = """I found this information:
[{"key": "name", "value": "Ali", "category": "identity"}, {"key": "age", "value": "25", "category": "identity"}]
Hope this helps!"""
        result = persona._parse_llm_response(raw)
        assert len(result) == 2

    def test_should_extract_too_short(self, persona):
        assert persona._should_extract("ha") is False
        assert persona._should_extract("yo'q") is False

    def test_should_extract_no_keywords(self, persona):
        assert persona._should_extract("Toshkentda havo qanday") is False

    def test_should_extract_valid(self, persona):
        assert persona._should_extract("mening ismim Ali") is True

    def test_should_extract_cooldown(self, persona):
        persona._last_extraction = 0  # force no cooldown
        assert persona._should_extract("mening ismim Ali") is True
        assert persona._should_extract("mening yoshim 25") is False  # cooldown active

    def test_should_extract_english_keywords(self, persona):
        persona._last_extraction = 0
        assert persona._should_extract("my name is Ali") is True
        persona._last_extraction = 0
        assert persona._should_extract("i live in Tashkent") is True

    @pytest.mark.asyncio
    async def test_extract_no_keywords_skips_llm(self, persona):
        llm = MagicMock()
        await persona.extract_from_conversation("Toshkentda havo qanday", llm)
        llm.chat_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_extract_cooldown_skips_llm(self, persona):
        llm = MagicMock()
        persona._last_extraction = time.time()
        await persona.extract_from_conversation("mening ismim Ali", llm)
        llm.chat_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_extract_valid_calls_llm(self, persona):
        llm = MagicMock()
        llm.chat_async = AsyncMock(return_value='[{"key": "name", "value": "Ali", "category": "identity"}]')
        persona._last_extraction = 0
        with patch.object(persona, "set", new_callable=AsyncMock) as mock_set:
            await persona.extract_from_conversation("mening ismim Ali", llm)
            mock_set.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete(self, persona):
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="DELETE 1")
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        with patch("llm.persona.get_pool", return_value=mock_pool):
            result = await persona.delete("name")
            assert result is True

    @pytest.mark.asyncio
    async def test_delete_not_found(self, persona):
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="DELETE 0")
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        with patch("llm.persona.get_pool", return_value=mock_pool):
            result = await persona.delete("nonexistent")
            assert result is False

    @pytest.mark.asyncio
    async def test_delete_all(self, persona):
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="DELETE 3")
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        with patch("llm.persona.get_pool", return_value=mock_pool):
            count = await persona.delete_all()
            assert count == 3

    @pytest.mark.asyncio
    async def test_get_summary_with_hobby(self, persona):
        rows = [
            {"key": "name", "value": "Ali", "category": "identity"},
            {"key": "hobby", "value": "coding", "category": "interest"},
        ]
        with patch.object(persona, "get_all", return_value=rows):
            summary = await persona.get_summary()
            assert "Ali" in summary
            assert "coding" in summary

    @pytest.mark.asyncio
    async def test_get_system_text_new_label(self, persona):
        rows = [
            {"key": "favorite_food", "value": "osh", "category": "preference"},
        ]
        with patch.object(persona, "get_all", return_value=rows):
            text = await persona.get_system_text()
            assert "Sevimli taomingiz" in text
            assert "osh" in text


class TestUserPersonaDB:
    """Tests that require DB mocking"""

    @pytest.mark.asyncio
    async def test_ensure_table(self, persona):
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        with patch("llm.persona.get_pool", return_value=mock_pool):
            await persona.ensure_table()
            assert mock_conn.execute.called

    @pytest.mark.asyncio
    async def test_set_and_get(self, persona):
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchrow = AsyncMock(return_value={"value": "Ali"})

        with patch("llm.persona.get_pool", return_value=mock_pool):
            val = await persona.get("name")
            assert val == "Ali"

    @pytest.mark.asyncio
    async def test_get_not_found(self, persona):
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchrow = AsyncMock(return_value=None)

        with patch("llm.persona.get_pool", return_value=mock_pool):
            val = await persona.get("nonexistent")
            assert val is None

    @pytest.mark.asyncio
    async def test_set_invalidates_cache(self, persona):
        persona._cache = {"name": {"key": "name", "value": "Ali"}}

        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        with patch("llm.persona.get_pool", return_value=mock_pool):
            await persona.set("name", "Vali", "identity")
            assert persona._cache is None
