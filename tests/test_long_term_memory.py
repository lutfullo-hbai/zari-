from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from llm.long_term_memory import extract_keywords, retrieve_context


class TestExtractKeywords:
    def test_basic_keywords(self):
        result = extract_keywords("salom zari, Python haqida ayting")
        assert "python" in result

    def test_filters_stopwords(self):
        result = extract_keywords("salom men zari bilan gaplashmoqchiman")
        assert "salom" not in result
        assert "bilan" not in result

    def test_filters_short_words(self):
        result = extract_keywords("yaxshi yomon katta kitob o'qish")
        for kw in result:
            assert len(kw) >= 4

    def test_limits_to_five(self):
        result = extract_keywords("python java golang rust kotlin swift")
        assert len(result) <= 5

    def test_empty_input(self):
        assert extract_keywords("") == []

    def test_deduplicates(self):
        result = extract_keywords("python python python")
        assert result.count("python") == 1


class TestRetrieveContext:
    @pytest.mark.asyncio
    async def test_returns_empty_for_no_keywords(self):
        result = await retrieve_context("salom")
        assert result == ""

    @pytest.mark.asyncio
    async def test_queries_db_with_keywords(self):
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = [
            {"content": "Python haqida bilaman"},
            {"content": "Python Django ishlataman"},
        ]
        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("llm.long_term_memory.get_pool", new_callable=AsyncMock, return_value=mock_pool):
            result = await retrieve_context("python haqida ayting")

        assert "Python haqida bilaman" in result
        assert "Python Django" in result
        assert "O'tgan suhbatlardan" in result

    @pytest.mark.asyncio
    async def test_excludes_current_session(self):
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = []
        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("llm.long_term_memory.get_pool", new_callable=AsyncMock, return_value=mock_pool):
            await retrieve_context("python dars", exclude_session_id="current-sess")

        call_args = mock_conn.fetch.call_args
        assert call_args[0][2] == "current-sess"

    @pytest.mark.asyncio
    async def test_returns_empty_on_db_error(self):
        with patch("llm.long_term_memory.get_pool", side_effect=Exception("db down")):
            result = await retrieve_context("python haqida")
        assert result == ""

    @pytest.mark.asyncio
    async def test_deduplicates_snippets(self):
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = [
            {"content": "takroriy xabar"},
            {"content": "takroriy xabar"},
            {"content": "boshqa xabar"},
        ]
        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("llm.long_term_memory.get_pool", new_callable=AsyncMock, return_value=mock_pool):
            result = await retrieve_context("takroriy xabar haqida")

        assert result.count("takroriy xabar") == 1
