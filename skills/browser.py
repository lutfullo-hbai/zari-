"""Browser Agent — Playwright asosida web sahifalarni ochish va boshqarish.

MUHIM: Playwright o'rnatilmagan bo'lsa skill xavfsiz ravishda
o'zini o'chiradi (openwakeword patterni).
"""

import asyncio
import logging
import re
from urllib.parse import quote_plus, urlparse

from skills.base import BaseSkill

log = logging.getLogger("zari")

try:
    from playwright.sync_api import sync_playwright

    PW_AVAILABLE = True
except ImportError:
    PW_AVAILABLE = False

MAX_PAGE_CHARS = 4000
NAV_TIMEOUT_MS = 20000

KNOWN_DOMAINS = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "github": "https://github.com",
    "telegram": "https://web.telegram.org",
    "gmail": "https://mail.google.com",
    "wikipedia": "https://www.wikipedia.org",
    "instagram": "https://www.instagram.com",
    "facebook": "https://www.facebook.com",
    "twitter": "https://x.com",
}

URL_RE = re.compile(r"(?:https?://|www\.)[^\s\"'<>]+", re.IGNORECASE)
BARE_DOMAIN_RE = re.compile(
    r"\b[\w\-]+(?:\.[\w\-]+)*\.(com|net|org|uz|io|dev|ru|co|info|edu|gov)\b",
    re.IGNORECASE,
)


class BrowserSkill(BaseSkill):
    """Sayt ochish, matnini o'qish, YouTube/Google'da qidirish.

    Brauzer orqali harakatlar (klik/form) pul talab qilishi mumkin —
    shu sababli SKILL darajasida tasdiq majburiy.
    """

    priority = 75
    timeout = 60.0
    requires_confirmation = True
    confirmation_type = "danger"

    def __init__(self) -> None:
        super().__init__()
        self._pw = None
        self._browser = None

    async def execute(self, query: str) -> dict | None:
        text = query.lower()
        if not self._is_browser_intent(text):
            return None

        if not PW_AVAILABLE:
            return {
                "response": (
                    "Playwright o'rnatilmagan. O'rnatish: `pip install playwright && playwright install chromium`"
                ),
                "context": "",
                "source": "browser",
            }

        url = self._resolve_target(query)
        if not url:
            return {
                "response": "Qaysi saytni ochish kerakligini tushunmadim.",
                "context": "",
                "source": "browser",
            }

        loop = asyncio.get_running_loop()
        try:
            result = await loop.run_in_executor(None, self._browse, url)
        except Exception as e:
            log.warning("Browser xato: %s", e)
            return {
                "response": f"Sahifa ochilmadi: {e}"[:300],
                "context": "",
                "source": "browser",
            }

        title, body = result
        preview = body[:1500]
        response = f"{title}\n\n{preview}"
        if len(body) > 1500:
            response += "\n... (to'liq matn context'da)"
        return {
            "response": response.strip(),
            "context": body[:MAX_PAGE_CHARS],
            "source": "browser",
        }

    @staticmethod
    def _is_browser_intent(text: str) -> bool:
        return any(
            w in text
            for w in [
                "youtube",
                "google",
                "sayt",
                "veb ",
                "website",
                "brauzer",
                "browser",
                "havola",
                "instagram",
                "facebook",
                "twitter",
                "github",
                "telegram",
                "gmail",
            ]
        ) or bool(URL_RE.search(text))

    @staticmethod
    def _resolve_target(query: str) -> str | None:
        """URL > ma'lum doman > youtube/google qidiruv URL."""
        m = URL_RE.search(query)
        if m:
            url = m.group(0)
            if not url.lower().startswith("http"):
                url = "https://" + url
            return url

        bm = BARE_DOMAIN_RE.search(query)
        if bm:
            return "https://" + bm.group(0).lower()

        text = query.lower()
        # Qidiruv so'rovini ajratish
        sm = re.search(
            r"(?:youtube da|youtube'da|google da|google'da)\s+(.+?)\s*" r"(?:qidir|izla|top|ko'rsat|$)",
            text,
        )
        if sm and sm.group(1).strip():
            term = sm.group(1).strip()
            base = "https://www.youtube.com" if "youtube" in text else "https://www.google.com/search"
            path = "/results?search_query=" if "youtube" in base else "?q="
            return f"{base}{path}{quote_plus(term)}"

        for name, domain in KNOWN_DOMAINS.items():
            if name in text:
                return domain
        return None

    def _get_browser(self):
        if self._browser and self._browser.is_connected():
            return self._browser
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=True)
        return self._browser

    def _browse(self, url: str) -> tuple[str, str]:
        browser = self._get_browser()
        page = browser.new_page()
        try:
            page.goto(url, timeout=NAV_TIMEOUT_MS, wait_until="domcontentloaded")
            page.wait_for_timeout(1200)
            title = page.title() or urlparse(url).netloc
            raw = page.inner_text("body")
            body = re.sub(r"\n{3,}", "\n\n", raw).strip()
            return title.strip(), body[:MAX_PAGE_CHARS]
        finally:
            page.close()

    def close(self) -> None:
        for attr in ("_browser", "_pw"):
            obj = getattr(self, attr, None)
            if obj:
                try:
                    obj.close() if attr == "_browser" else obj.stop()
                except Exception:
                    pass
                setattr(self, attr, None)
