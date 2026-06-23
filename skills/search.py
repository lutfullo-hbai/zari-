import logging
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
import wikipedia

from core.config import settings
from llm.ollama import OllamaClient
from skills.base import BaseSkill

log = logging.getLogger("zari")

MAX_CHARS_PER_PAGE = 3000
MAX_RESULTS = 3


class SearchSkill(BaseSkill):
    def __init__(self):
        self.llm = OllamaClient()

    async def execute(self, query: str) -> dict:
        context = ""
        source = ""

        wiki = await self._wikipedia(query)
        if wiki:
            context = wiki
            source = "wikipedia"
            log.info("Wikipedia ma'lumot topildi: %d chars", len(context))
        else:
            results = await self._search_web(query)
            if results:
                context = await self._fetch_pages(results)
                source = "web"
                log.info("Web scraping: %d chars from %d ta natija", len(context), len(results))

        if not context:
            return None

        summary = await self._summarize(context, query)
        return {
            "response": summary,
            "context": context[:500],
            "source": source,
        }

    async def _search_web(self, query: str) -> list[dict]:
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=MAX_RESULTS))
                return [
                    {"title": r["title"], "url": r["href"], "body": r.get("body", "")}
                    for r in results
                ]
        except Exception as e:
            log.error("Qidiruv xatosi: %s", e)
            return []

    async def _fetch_pages(self, results: list[dict]) -> str:
        combined = []
        async with httpx.AsyncClient(timeout=10.0) as client:
            for r in results:
                try:
                    resp = await client.get(r["url"], follow_redirects=True)
                    resp.raise_for_status()
                    text = self._extract_text(resp.text)
                    if text:
                        combined.append(f"--- {r['url']} ---\n{text[:MAX_CHARS_PER_PAGE]}")
                except Exception as e:
                    log.debug("Sahifa o'qilmadi %s: %s", r["url"], e)
                    if r.get("body"):
                        combined.append(f"--- {r['url']} ---\n{r['body']}")
        return "\n\n".join(combined)

    def _extract_text(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return " ".join(lines)

    async def _wikipedia(self, query: str) -> str | None:
        try:
            wikipedia.set_lang("uz")
            search = wikipedia.search(query)
            if not search:
                wikipedia.set_lang("en")
                search = wikipedia.search(query)
            if not search:
                return None
            try:
                page = wikipedia.page(search[0])
                text = page.summary[:MAX_CHARS_PER_PAGE]
                return f"Wikipedia: {page.title}\n\n{text}"
            except wikipedia.DisambiguationError as e:
                if e.options:
                    page = wikipedia.page(e.options[0])
                    text = page.summary[:MAX_CHARS_PER_PAGE]
                    return f"Wikipedia: {page.title}\n\n{text}"
            except Exception:
                return None
        except Exception as e:
            log.debug("Wikipedia xatosi: %s", e)
            return None

    async def _summarize(self, context: str, query: str) -> str:
        prompt = (
            "Berilgan matn asosida foydalanuvchi savoliga o'zbek tilida qisqa va aniq javob ber. "
            "Faqat matndagi ma'lumotlardan foydalan, o'zing ma'lumot qo'shma. "
            "Javob 3-5 gapdan oshmasin.\n\n"
            f"Foydalanuvchi: {query}\n\n"
            f"Matn: {context[:4000]}\n\n"
            "Javob:"
        )
        try:
            resp = self.llm.chat([{"role": "user", "content": prompt}])
            return resp.strip()
        except Exception as e:
            log.error("Xulosa xatosi: %s", e)
            return "Kechirasiz, ma'lumotni tahlil qilishda xatolik yuz berdi."
