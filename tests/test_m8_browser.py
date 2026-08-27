"""M8 Browser Agent testlari: BrowserSkill (mock + real flag bilan)."""

import os
from unittest.mock import patch

import pytest

from core.router import match_intents


class TestBrowserRouting:
    def test_youtube_search(self):
        assert match_intents("youtube da lofi qidir")[0] == "browser"

    def test_google_query(self):
        assert match_intents("google da zari nima")[0] == "browser"

    def test_url(self):
        assert match_intents("https://example.com ni och")[0] == "browser"

    def test_plain_search_stays_search(self):
        """Sayt nomi yo'q bo'lsa duckduckgo search qoladi."""
        assert match_intents("zari haqida qidir")[0] != "browser"


class TestBrowserSkillUnit:
    @pytest.fixture
    def skill(self):
        from skills.browser import BrowserSkill

        s = BrowserSkill()
        yield s
        s.close()

    def test_requires_confirmation(self, skill):
        """Brauzer harakatlari pul talab qilishi mumkin — tasdiq MAJBURIY."""
        assert skill.requires_confirmation is True
        assert skill.confirmation_type == "danger"

    def test_resolve_direct_url(self, skill):
        url = skill._resolve_target("https://example.com saytni och")
        assert url == "https://example.com"

    def test_resolve_www_prefix(self, skill):
        url = skill._resolve_target("www.python.org ochib ber")
        assert url == "https://www.python.org"

    def test_resolve_known_domain(self, skill):
        assert skill._resolve_target("githubni och") == "https://github.com"
        assert skill._resolve_target("youtube och") == "https://www.youtube.com"

    def test_resolve_youtube_search(self, skill):
        url = skill._resolve_target("youtube da lofi music qidir")
        assert "youtube.com/results?search_query=" in url
        assert "lofi+music" in url

    def test_resolve_google_search(self, skill):
        url = skill._resolve_target("google da ob-havo qidir")
        assert "google.com/search?q=" in url
        assert "ob-havo" in url

    def test_resolve_none_for_unknown(self, skill):
        assert skill._resolve_target("salom dunyo") is None

    @pytest.mark.asyncio
    async def test_non_browser_intent_returns_none(self, skill):
        assert await skill.execute("ob-havo qanday") is None

    @pytest.mark.asyncio
    async def test_graceful_without_playwright(self, skill, tmp_path):
        """Playwright o'rnatilmagan muhitda crash EMAS — tushunarli javob."""
        from skills import browser as browser_mod

        with patch.object(browser_mod, "PW_AVAILABLE", False):
            result = await skill.execute("example.com saytni och")

        assert result is not None
        assert "o'rnatilmagan" in result["response"]
        assert result["source"] == "browser"

    @pytest.mark.asyncio
    async def test_browse_error_is_caught(self, skill):
        with patch.object(skill, "_browse", side_effect=RuntimeError("timeout")):
            result = await skill.execute("example.com saytni och")

        assert result is not None
        assert "ochilmadi" in result["response"]

    @pytest.mark.asyncio
    async def test_success_response_formatting(self, skill):
        with patch.object(
            skill,
            "_browse",
            return_value=("Test Sahifa", "Asosiy matn\n\nqatorlar"),
        ):
            result = await skill.execute("example.com saytni och")

        assert result is not None
        assert "Test Sahifa" in result["response"]
        assert "Asosiy matn" in result["response"]
        assert result["context"].startswith("Asosiy matn")


class TestBrowserRealIntegration:
    """Haqiqiy brauzer testlari — ZARI_BROWSER_TESTS=1 bilan ishlaydi.

    Lokal: ZARI_BROWSER_TESTS=1 pytest tests/test_m8_browser.py
    CI: o'tkazib yuboriladi (brauzer o'rnatilmagan bo'lishi mumkin).
    """

    needs_browser = pytest.mark.skipif(
        os.environ.get("ZARI_BROWSER_TESTS") != "1",
        reason="ZARI_BROWSER_TESTS=1 emas",
    )

    @needs_browser
    @pytest.mark.asyncio
    async def test_real_page_read(self):
        from skills.browser import PW_AVAILABLE, BrowserSkill

        if not PW_AVAILABLE:
            pytest.skip("Playwright yo'q")
        skill = BrowserSkill()
        try:
            result = await skill.execute("https://example.com saytni och")
        finally:
            skill.close()

        assert result is not None
        assert "Example Domain" in result["response"]

    @needs_browser
    @pytest.mark.asyncio
    async def test_real_browser_reused(self):
        from skills.browser import BrowserSkill

        skill = BrowserSkill()
        try:
            await skill.execute("https://example.com saytni och")
            first = skill._browser
            await skill.execute("https://www.iana.org/domains/reserved saytni och")
            assert skill._browser is first
        finally:
            skill.close()


class TestBrainKnowsBrowser:
    def test_brain_knows_browser(self):
        from core.brain import AVAILABLE_SKILLS

        assert "browser" in AVAILABLE_SKILLS


class TestYouTubePlay:
    @pytest.fixture
    def skill(self):
        from skills.browser import BrowserSkill

        s = BrowserSkill()
        yield s
        s.close()

    def test_term_extraction(self, skill):
        assert skill._youtube_term("youtube da lofi hip hop qo'y") == "lofi hip hop"
        assert skill._youtube_term("youtube da remix play") == "remix"
        assert skill._youtube_term("youtube och") == ""

    @pytest.mark.asyncio
    async def test_play_opens_visible_browser(self, skill):
        with (
            patch.object(
                skill,
                "_first_video",
                return_value=("https://www.youtube.com/watch?v=abc", "Lofi Radio"),
            ),
            patch("skills.browser.subprocess.Popen") as mock_open,
        ):
            result = await skill.execute("youtube da lofi qo'y")

        assert result is not None
        assert "ochildi" in result["response"]
        assert "Lofi Radio" in result["response"]
        opened = mock_open.call_args.args[0]
        assert opened == ["xdg-open", "https://www.youtube.com/watch?v=abc"]

    @pytest.mark.asyncio
    async def test_play_fallback_to_search_url(self, skill):
        """_first_video bo'sh qaytarsa — qidiruv sahifasi ochiladi."""
        with (
            patch.object(skill, "_first_video", return_value=("", "")),
            patch("skills.browser.subprocess.Popen") as mock_open,
        ):
            result = await skill.execute("youtube da jazz qo'y")

        assert result is not None
        opened_url = mock_open.call_args.args[0][1]
        assert "search_query=jazz" in opened_url

    @pytest.mark.asyncio
    async def test_empty_term_prompts_user(self, skill):
        result = await skill.execute("youtube da qo'y")
        assert "Nima ijro etish" in result["response"]

    @pytest.mark.asyncio
    async def test_no_confirmation_bypass(self, skill):
        """Ijro ham tasdiqsiz O'TMASLIGI kerak (skill darajasi)."""
        assert skill.requires_confirmation is True

    @pytest.mark.asyncio
    async def test_read_still_works_for_youtube_without_play_words(self, skill):
        """'youtube och' (qo'y so'zi yo'q) — oddiy o'qish rejimi."""
        with patch.object(
            skill,
            "_browse",
            return_value=("YouTube", "Sahifa matni"),
        ) as mock_browse:
            await skill.execute("youtube saytini och")

        assert mock_browse.call_args.args[0] == "https://www.youtube.com"
