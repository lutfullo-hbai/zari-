from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestCalculatorSkill:
    @pytest.mark.asyncio
    async def test_calc_addition(self):
        from skills.calculator import CalculatorSkill

        skill = CalculatorSkill()
        result = await skill.execute("hisobla 2 + 3")
        assert result is not None
        assert "5" in result["response"]
        assert result["source"] == "calculator"

    @pytest.mark.asyncio
    async def test_calc_multiplication(self):
        from skills.calculator import CalculatorSkill

        skill = CalculatorSkill()
        result = await skill.execute("hisobla 4 x 5")
        assert result is not None
        assert "20" in result["response"]

    @pytest.mark.asyncio
    async def test_calc_division(self):
        from skills.calculator import CalculatorSkill

        skill = CalculatorSkill()
        result = await skill.execute("10 / 3")
        assert result is not None

    @pytest.mark.asyncio
    async def test_calc_invalid(self):
        from skills.calculator import CalculatorSkill

        skill = CalculatorSkill()
        result = await skill.execute("hello world")
        assert result is None

    @pytest.mark.asyncio
    async def test_calc_prevents_code(self):
        from skills.calculator import CalculatorSkill

        skill = CalculatorSkill()
        result = await skill.execute("__import__('os').system('ls')")
        assert result is None


class TestNotesSkill:
    @pytest.mark.asyncio
    async def test_add_note(self):
        from skills.notes import NotesSkill

        with patch("skills.notes.get_pool", new_callable=AsyncMock) as mock_get_pool:
            mock_pool = MagicMock()
            mock_conn = AsyncMock()
            mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
            mock_get_pool.return_value = mock_pool
            skill = NotesSkill()
            result = await skill.execute("yozib ol: test eslatma")
            assert result is not None
            assert "saqlandi" in result["response"]
            assert result["source"] == "notes"

    @pytest.mark.asyncio
    async def test_add_note_no_content(self):
        from skills.notes import NotesSkill

        skill = NotesSkill()
        result = await skill.execute("yozib ol")
        assert result is None

    @pytest.mark.asyncio
    async def test_search_notes_empty(self):
        from skills.notes import NotesSkill

        with patch("skills.notes.get_pool", new_callable=AsyncMock) as mock_get_pool:
            mock_pool = MagicMock()
            mock_conn = AsyncMock()
            mock_conn.fetch.return_value = []
            mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
            mock_get_pool.return_value = mock_pool
            skill = NotesSkill()
            result = await skill.execute("eslatmalarimni ko'rsat")
            assert result is not None
            assert "yo'q" in result["response"] or "Hech" in result["response"]


class TestTimerSkill:
    @pytest.mark.asyncio
    async def test_timer_start_seconds(self):
        from skills.timer import TimerSkill

        skill = TimerSkill()
        result = await skill.execute("5 soniya timer")
        assert result is not None
        assert "boshlandi" in result["response"]
        assert result["source"] == "timer"

    @pytest.mark.asyncio
    async def test_timer_start_minutes(self):
        from skills.timer import TimerSkill

        skill = TimerSkill()
        result = await skill.execute("2 daqiqa timer")
        assert result is not None
        assert "daqiqa" in result["response"]

    @pytest.mark.asyncio
    async def test_timer_stop_no_active(self):
        from skills.timer import TimerSkill

        skill = TimerSkill()
        result = await skill.execute("timer to'xtat")
        assert result is not None
        assert "yo'q" in result["response"]

    @pytest.mark.asyncio
    async def test_timer_no_match(self):
        from skills.timer import TimerSkill

        skill = TimerSkill()
        result = await skill.execute("salom")
        assert result is None


class TestWeatherSkill:
    @pytest.mark.asyncio
    async def test_weather_with_api_key(self):
        from core.config import settings
        from skills.weather import WeatherSkill

        old_key = settings.weather_api_key
        settings.weather_api_key = "test-key"
        skill = WeatherSkill()
        with patch("httpx.AsyncClient") as mock_client:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "name": "Tashkent",
                "main": {"temp": 25, "feels_like": 23, "humidity": 50},
                "weather": [{"description": "clear sky"}],
                "wind": {"speed": 3},
            }
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_resp
            result = await skill.execute("ob-havo Toshkent")
            assert result is not None
            assert "Tashkent" in result["response"]
            assert "25" in result["response"]
        settings.weather_api_key = old_key

    @pytest.mark.asyncio
    async def test_weather_no_city(self):
        from core.config import settings
        from skills.weather import WeatherSkill

        old = settings.weather_api_key
        settings.weather_api_key = ""
        skill = WeatherSkill()
        with patch.object(skill, "_weather_via_web", return_value=None):
            result = await skill.execute("salom")
            assert result is None
        settings.weather_api_key = old

    @pytest.mark.asyncio
    async def test_weather_api_404(self):
        from core.config import settings
        from skills.weather import WeatherSkill

        old_key = settings.weather_api_key
        settings.weather_api_key = "test-key"
        skill = WeatherSkill()
        with patch("httpx.AsyncClient") as mock_client:
            import httpx

            mock_resp = MagicMock()
            mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "404", request=MagicMock(), response=MagicMock(status_code=404)
            )
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_resp
            result = await skill.execute("ob-havo UnknownCity")
            assert result is not None
            assert "topilmadi" in result["response"]
        settings.weather_api_key = old_key


class TestClipboardSkill:
    @pytest.mark.asyncio
    async def test_clipboard_read(self):
        from skills.clipboard import ClipboardSkill

        with patch("pyperclip.paste", return_value="test content"):
            skill = ClipboardSkill()
            result = await skill.execute("clipboard o'qi")
            assert result is not None
            assert "test content" in result["response"]
            assert result["source"] == "clipboard"

    @pytest.mark.asyncio
    async def test_clipboard_read_empty(self):
        from skills.clipboard import ClipboardSkill

        with patch("pyperclip.paste", return_value=""):
            skill = ClipboardSkill()
            result = await skill.execute("clipboard o'qi")
            assert result is not None
            assert "bo'sh" in result["response"]

    @pytest.mark.asyncio
    async def test_clipboard_write(self):
        from skills.clipboard import ClipboardSkill

        with patch("pyperclip.copy") as mock_copy:
            skill = ClipboardSkill()
            result = await skill.execute("clipboardga yoz: hello world")
            assert result is not None
            assert "yozildi" in result["response"]
            mock_copy.assert_called_with("hello world")

    @pytest.mark.asyncio
    async def test_clipboard_no_match(self):
        from skills.clipboard import ClipboardSkill

        skill = ClipboardSkill()
        result = await skill.execute("salom")
        assert result is None


class TestScreenshotSkill:
    @pytest.mark.asyncio
    async def test_screenshot_no_match(self):
        from skills.screenshot import ScreenshotSkill

        skill = ScreenshotSkill()
        result = await skill.execute("salom")
        assert result is None


class TestFileManagerSkill:
    @pytest.mark.asyncio
    async def test_filemanager_no_match(self):
        from skills.filemanager import FileManagerSkill

        skill = FileManagerSkill()
        result = await skill.execute("salom")
        assert result is None

    @pytest.mark.asyncio
    async def test_read_file_with_natural_language_path(self, tmp_path):
        from skills.filemanager import FileManagerSkill

        file_path = tmp_path / "demo.txt"
        file_path.write_text("hello world", encoding="utf-8")

        skill = FileManagerSkill()
        result = await skill.execute(f"faylni och {file_path}")

        assert result is not None
        assert result["source"] == "filemanager"
        assert "demo.txt" in result["response"]
        assert "hello world" in result["response"]


class TestNetworkSkill:
    @pytest.mark.asyncio
    async def test_public_ip(self):
        from skills.network import NetworkSkill

        with patch("httpx.AsyncClient") as mock_client:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"ip": "8.8.8.8"}
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_resp
            with patch("skills.network.socket.gethostname", return_value="my-pc"):
                skill = NetworkSkill()
                result = await skill.execute("mening IP")
                assert result is not None
                assert "8.8.8.8" in result["response"]
                assert result["source"] == "network"

    @pytest.mark.asyncio
    async def test_network_no_match(self):
        from skills.network import NetworkSkill

        skill = NetworkSkill()
        result = await skill.execute("salom")
        assert result is None

    @pytest.mark.asyncio
    async def test_dns_lookup(self):
        from skills.network import NetworkSkill

        with patch("skills.network.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(None, None, None, None, ("1.1.1.1", 80))]
            skill = NetworkSkill()
            result = await skill.execute("dns google.com")
            assert result is not None
            assert "1.1.1.1" in result["response"]

    @pytest.mark.asyncio
    async def test_dns_no_domain(self):
        from skills.network import NetworkSkill

        skill = NetworkSkill()
        result = await skill.execute("dns")
        assert result is None
