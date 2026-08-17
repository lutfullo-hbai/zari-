from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from llm.habits import analyze_and_store_habits, classify_peak_hour, detect_habits


class TestClassifyPeakHour:
    def test_night_owl(self):
        hours = {22: 10, 23: 15, 0: 8, 1: 5, 12: 2, 14: 1}
        assert classify_peak_hour(hours) == "night"

    def test_morning_person(self):
        hours = {6: 5, 7: 12, 8: 20, 9: 15, 14: 3}
        assert classify_peak_hour(hours) == "morning"

    def test_daytime(self):
        hours = {12: 10, 13: 25, 14: 18, 15: 12}
        assert classify_peak_hour(hours) == "day"

    def test_evening(self):
        hours = {18: 10, 19: 20, 20: 15, 21: 8}
        assert classify_peak_hour(hours) == "evening"

    def test_empty(self):
        assert classify_peak_hour({}) == "unknown"


class TestDetectHabits:
    @pytest.mark.asyncio
    async def test_returns_empty_below_threshold(self):
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = [
            {"hour": 14, "cnt": 3},
        ]
        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("llm.habits.get_pool", new_callable=AsyncMock, return_value=mock_pool):
            result = await detect_habits(min_messages=15)

        assert result == {}

    @pytest.mark.asyncio
    async def test_detects_night_owl(self):
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = [
            {"hour": 22, "cnt": 10},
            {"hour": 23, "cnt": 15},
            {"hour": 0, "cnt": 8},
            {"hour": 14, "cnt": 2},
        ]
        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("llm.habits.get_pool", new_callable=AsyncMock, return_value=mock_pool):
            result = await detect_habits(min_messages=15)

        assert result["work_hours"] == "night"
        assert "active_hours" in result

    @pytest.mark.asyncio
    async def test_returns_empty_on_db_error(self):
        with patch("llm.habits.get_pool", side_effect=Exception("db down")):
            result = await detect_habits()
        assert result == {}


class TestAnalyzeAndStoreHabits:
    @pytest.mark.asyncio
    async def test_stores_habits_in_persona(self):
        mock_persona = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = [
            {"hour": 23, "cnt": 20},
            {"hour": 14, "cnt": 3},
        ]
        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("llm.habits.get_pool", new_callable=AsyncMock, return_value=mock_pool):
            result = await analyze_and_store_habits(mock_persona)

        assert "work_hours" in result
        assert mock_persona.set.await_count >= 1
        call_kwargs = mock_persona.set.call_args_list[0]
        assert call_kwargs[1]["category"] == "habit"
