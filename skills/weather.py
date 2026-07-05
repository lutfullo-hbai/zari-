import logging

import httpx

from core.config import settings
from skills.base import BaseSkill

log = logging.getLogger("zari")


class WeatherSkill(BaseSkill):
    priority = 70
    timeout = 10.0

    def __init__(self):
        self.api_key = getattr(settings, "weather_api_key", "")
        self.api_url = "https://api.openweathermap.org/data/2.5/weather"

    async def execute(self, query: str) -> dict | None:
        text = query.lower().strip()

        if not self.api_key:
            try:
                return await self._weather_via_web(text)
            except Exception as e:
                log.warning("Weather web xatosi: %s", e)
                return {
                    "response": "Ob-havo uchun OpenWeatherMap API kaliti kerak. .env ga WEATHER_API_KEY qo'shing.",
                    "context": "",
                    "source": "weather",
                }

        city = self._parse_city(text)
        if not city:
            return None

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(self.api_url, params={
                    "q": city,
                    "appid": self.api_key,
                    "units": "metric",
                    "lang": "uz",
                })
                resp.raise_for_status()
                data = resp.json()

            temp = data["main"]["temp"]
            feels = data["main"]["feels_like"]
            desc = data["weather"][0]["description"]
            humidity = data["main"]["humidity"]
            wind = data["wind"]["speed"]
            city_name = data["name"]

            response = (
                f"{city_name} da ob-havo: {desc}. "
                f"Harorat: {temp:.0f}°C (his qilinadi: {feels:.0f}°C). "
                f"Namlik: {humidity}%. Shamol: {wind} m/s."
            )
            return {"response": response, "context": response, "source": "weather"}
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {"response": f"'{city}' shahri topilmadi.", "context": "", "source": "weather"}
            return {"response": "Ob-havo ma'lumotini olishda xatolik.", "context": "", "source": "weather"}
        except Exception as e:
            log.warning("Weather API xatosi: %s", e)
            return None

    async def _weather_via_web(self, text: str) -> dict | None:
        from skills.search import SearchSkill
        from llm.ollama import OllamaClient
        try:
            skill = SearchSkill(llm=OllamaClient())
            return await skill.execute(text)
        except Exception as e:
            log.debug("Weather via web xatosi: %s", e)
            return None

    def _parse_city(self, text: str) -> str | None:
        for kw in ["ob-havo", "obhavo", "havo", "weather", "harorat", "qanday"]:
            text = text.replace(kw, "").strip()
        for sep in [":", "—", "-", "da", "shahrida", "da havo", "da ob"]:
            if sep in text:
                idx = text.index(sep) + len(sep)
                text = text[idx:].strip()
        text = text.strip().strip(".,!?").strip()
        return text if text else None
