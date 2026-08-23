"""Skeleton-audit tuzatishlari: TimeSkill va SystemControlSkill testlari."""

from unittest.mock import patch

import pytest

from skills.time import TimeSkill


class TestTimeSkill:
    @pytest.mark.asyncio
    async def test_time_query(self):
        result = await TimeSkill().execute("soat necha bo'ldi")
        assert result is not None
        assert result["source"] == "time"
        assert "Hozir soat" in result["response"]
        assert ":" in result["response"]

    @pytest.mark.asyncio
    async def test_date_query(self):
        result = await TimeSkill().execute("bugun qanday kun")
        assert result is not None
        assert "Bugun" in result["response"]
        assert any(
            d in result["response"]
            for d in ("dushanba", "seshanba", "chorshanba", "payshanba", "juma", "shanba", "yakshanba")
        )


class TestSystemControlSkill:
    @pytest.fixture
    def skill(self):
        from skills.system import SystemControlSkill

        return SystemControlSkill()

    @pytest.mark.asyncio
    async def test_open_app_found_in_path(self, skill):
        with (
            patch("skills.system.shutil.which", return_value="/usr/bin/firefox"),
            patch("skills.system.subprocess.Popen") as mock_popen,
        ):
            result = await skill.execute("firefoxni och")

        assert result is not None
        assert "firefox" in result["response"]
        mock_popen.assert_called_once_with(["/usr/bin/firefox"])

    @pytest.mark.asyncio
    async def test_open_app_not_in_path(self, skill):
        with patch("skills.system.shutil.which", return_value=None):
            result = await skill.execute("notepadni och")

        assert result is not None
        assert "topilmadi" in result["response"]

    @pytest.mark.asyncio
    async def test_open_url(self, skill):
        with patch("skills.system.subprocess.Popen") as mock_popen:
            result = await skill.execute("https://example.com ochish")

        assert result is not None
        assert "example.com" in result["response"]
        mock_popen.assert_called_once()
        assert mock_popen.call_args.args[0] == ["xdg-open", "https://example.com"]

    @pytest.mark.asyncio
    async def test_rejects_malicious_name(self, skill):
        with patch("skills.system.shutil.which"), patch("skills.system.subprocess.Popen") as mock_popen:
            result = await skill.execute("rm -rf / och")

        # Xavfsiz nom filtri: argumentlar hech qachon uzatilmaydi
        assert result is not None
        called_cmd = mock_popen.call_args.args[0] if mock_popen.call_args is not None else []
        assert all(not str(a).startswith("-") for a in called_cmd)

    @pytest.mark.asyncio
    async def test_close_app_success(self, skill):
        with (
            patch("skills.system.shutil.which", return_value="/usr/bin/pkill"),
            patch("skills.system.subprocess.run") as mock_run,
        ):
            mock_run.return_value.returncode = 0
            result = await skill.execute("firefoxni yop")

        assert result is not None
        assert "yopildi" in result["response"]
        assert mock_run.call_args.args[0] == ["pkill", "-x", "firefox"]

    @pytest.mark.asyncio
    async def test_close_app_not_running(self, skill):
        with (
            patch("skills.system.shutil.which", return_value="/usr/bin/pkill"),
            patch("skills.system.subprocess.run") as mock_run,
        ):
            mock_run.return_value.returncode = 1
            result = await skill.execute("ghostni yop")

        assert result is not None
        assert "topilmadi" in result["response"]

    def test_requires_confirmation(self, skill):
        """Bu skill hech qachon tasdiqsiz bajarilmasligi kerak."""
        assert skill.requires_confirmation is True
