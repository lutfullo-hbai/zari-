import asyncio
import logging

import httpx
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
import wikipedia

from core.config import settings
from db.cache import cache_llm_response, get_cached_llm_response
from llm.factory import LLMClient, create_llm_client
from skills.base import BaseSkill

log = logging.getLogger("zari")

MAX_CHARS_PER_PAGE = 3000
MAX_RESULTS = 3


PERPLEXICA_FOCUS_MODES = {"web", "academic", "news", "social", "writing"}


class SearchSkill(BaseSkill):
    priority = 20
    timeout = 60.0
    retries = 1

    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or create_llm_client()
        self.perplexica_url = settings.perplexica_url.rstrip("/") if settings.perplexica_url else ""
        self.search_backend = (settings.search_backend or "auto").lower()
        self.perplexica_focus = (
            settings.perplexica_focus_mode or "web"
        ).lower()
        if self.perplexica_focus not in PERPLEXICA_FOCUS_MODES:
            self.perplexica_focus = "web"

    async def execute(self, query: str) -> dict | None:
        try:
            cached = await get_cached_llm_response(f"search:{query}")
            if cached:
                return {
                    "response": cached,
                    "context": cached[:500],
                    "source": "cache",
                }
        except Exception:
            pass

        perplexica_result = await self._search_with_perplexica(query)
        if perplexica_result:
            try:
                await cache_llm_response(f"search:{query}", perplexica_result["response"])
            except Exception:
                pass
            return perplexica_result

        context = ""
        source = ""

        try:
            wiki = await self._wikipedia(query)
        except Exception as e:
            log.warning("Wikipedia xatosi: %s", e)
            wiki = None

        if wiki:
            context = wiki
            source = "wikipedia"
            log.info("Wikipedia ma'lumot topildi: %d chars", len(context))
        else:
            try:
                results = await self._search_web(query)
            except Exception as e:
                log.warning("Search xatosi: %s", e)
                results = None
            if results:
                context = await self._fetch_pages(results)
                source = "web"
                log.info("Web scraping: %d chars from %d ta natija", len(context), len(results))

        if not context:
            return None

        summary = await self._summarize(context, query)
        result = {
            "response": summary,
            "context": context[:500],
            "source": source,
        }
        if summary:
            try:
                await cache_llm_response(f"search:{query}", summary)
            except Exception:
                pass
        return result

    _EMBED_KEYWORDS = {"nomic", "embed", "bert", "minilm", "mxbai"}

    async def _get_vane_providers(self) -> dict | None:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.perplexica_url}/api/providers")
                resp.raise_for_status()
                data = resp.json()
                for p in data.get("providers", []):
                    if p["name"].lower() == "ollama":
                        chat = next(
                            (
                                m
                                for m in p.get("chatModels", [])
                                if not any(kw in m["key"].lower() for kw in self._EMBED_KEYWORDS)
                            ),
                            None,
                        ) or next(iter(p.get("chatModels", [])), {})
                        embed = next(iter(p.get("embeddingModels", [])), {})
                        return {
                            "providerId": p["id"],
                            "chatKey": chat.get("key", ""),
                            "embedKey": embed.get("key", ""),
                        }
        except Exception as e:
            log.warning("Vane providers xatosi: %s", e)
        return None

    async def _search_with_perplexica(self, query: str) -> dict | None:
        if not self.perplexica_url:
            return None

        if self.search_backend not in {"auto", "perplexica"}:
            return None

        providers = await self._get_vane_providers()
        if not providers:
            return None

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.perplexica_url}/api/search",
                    json={
                        "chatModel": {
                            "providerId": providers["providerId"],
                            "key": providers["chatKey"],
                        },
                        "embeddingModel": {
                            "providerId": providers["providerId"],
                            "key": providers["embedKey"],
                        },
                        "sources": [self.perplexica_focus],
                        "query": query,
                    },
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                data = response.json()

            answer = data.get("message", "")
            sources = data.get("sources", [])

            if not answer:
                return None

            source_str = "\n".join(
                s.get("metadata", {}).get("title", s.get("url", ""))
                for s in sources[:MAX_RESULTS]
            ) if sources else ""

            context = answer
            if source_str:
                context += f"\n\nManbalar:\n{source_str}"

            return {
                "response": answer,
                "context": context[:500],
                "source": "perplexica",
            }
        except Exception as e:
            log.warning("Perplexica qidiruv xatosi: %s", e)
            return None

    async def _search_web(self, query: str) -> list[dict]:
        try:
            def _search():
                with DDGS(timeout=10) as ddgs:
                    return list(ddgs.text(query, max_results=MAX_RESULTS))
            results = await asyncio.wait_for(
                asyncio.to_thread(_search),
                timeout=15.0,
            )
            return [
                {"title": r["title"], "url": r["href"], "body": r.get("body", "")}
                for r in results
            ]
        except asyncio.TimeoutError:
            log.error("Qidiruv timeout: 15 soniya")
            return []
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
            def _wiki_search_uz():
                wikipedia.set_lang("uz")
                return wikipedia.search(query)
            search = await asyncio.to_thread(_wiki_search_uz)
            if not search:
                def _wiki_search_en():
                    wikipedia.set_lang("en")
                    return wikipedia.search(query)
                search = await asyncio.to_thread(_wiki_search_en)
            if not search:
                return None
            try:
                def _wiki_page():
                    return wikipedia.page(search[0])
                page = await asyncio.to_thread(_wiki_page)
                text = page.summary[:MAX_CHARS_PER_PAGE]
                return f"Wikipedia: {page.title}\n\n{text}"
            except wikipedia.DisambiguationError as e:
                if e.options:
                    def _wiki_disambig():
                        return wikipedia.page(e.options[0])
                    page = await asyncio.to_thread(_wiki_disambig)
                    text = page.summary[:MAX_CHARS_PER_PAGE]
                    return f"Wikipedia: {page.title}\n\n{text}"
            except Exception:
                return None
        except Exception as e:
            log.debug("Wikipedia xatosi: %s", e)
            return None

    async def _summarize(self, context: str, query: str) -> str:
        messages = [
            {"role": "system", "content": "Siz faqat o'zbek tilida javob beradigan yordamchisiz."},
            {"role": "user", "content": (
                "Berilgan matn asosida foydalanuvchi savoliga o'zbek tilida qisqa va aniq javob ber. "
                "Faqat matndagi ma'lumotlardan foydalan, o'zing ma'lumot qo'shma. "
                "Javob 3-5 gapdan oshmasin.\n\n"
                f"Foydalanuvchi: {query}\n\n"
                f"Matn: {context[:4000]}\n\n"
                "Javob:"
            )},
        ]
        try:
            resp = await self.llm.chat_async(messages, timeout=60)
            return resp.strip()
        except Exception as e:
            log.error("Xulosa xatosi: %s", e)
            return "Kechirasiz, ma'lumotni tahlil qilishda xatolik yuz berdi."
