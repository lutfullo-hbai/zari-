import asyncio
import logging
import re
import subprocess

from skills.base import BaseSkill

log = logging.getLogger("zari")

YT_DLP_CMD = "yt-dlp"
MAX_RESULTS = 5


class MusicSkill(BaseSkill):
    priority = 50
    timeout = 30.0

    async def execute(self, query: str) -> dict | None:
        text = query.lower()

        if not text.strip():
            return {
                "response": "Nima musiqani qidirish kerak?",
                "context": "",
                "source": "music",
            }

        search_query = self._parse_query(text)
        if not search_query:
            search_query = text

        try:
            results = await self._search_youtube(search_query)
        except Exception as e:
            log.error("YouTube qidiruv xatosi: %s", e)
            return {
                "response": "Musiqa qidirishda xatolik yuz berdi.",
                "context": "",
                "source": "music",
            }

        if not results:
            return None

        lines = []
        for i, r in enumerate(results[:MAX_RESULTS], 1):
            duration = r.get("duration", "")
            if duration:
                duration = f" [{duration}]"
            lines.append(f"  {i}. {r['title']}{duration}")

        response = (
            f"Topilgan musiqalar:\n" + "\n".join(lines) + "\n\n"
            f"Qaysi birini tinglaysiz?"
        )

        return {
            "response": response,
            "context": str([r["url"] for r in results[:MAX_RESULTS]]),
            "source": "music",
        }

    def _parse_query(self, text: str) -> str:
        text = re.sub(r"\b(musiqa|qo.y|qo.shiq|music|song|play|qidir|top|izla)\b", "", text).strip()
        text = re.sub(r"\s+", " ", text).strip()
        return text

    async def _search_youtube(self, query: str) -> list[dict]:
        def _search():
            result = subprocess.run(
                [YT_DLP_CMD, "ytsearch" + str(MAX_RESULTS) + ":" + query,
                 "--dump-json", "--flat-playlist", "--no-warnings"],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode != 0:
                log.warning("yt-dlp xatosi: %s", result.stderr.strip()[:200])
                return []

            entries = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                import json
                try:
                    data = json.loads(line)
                    entries.append({
                        "title": data.get("title", ""),
                        "url": f"https://youtube.com/watch?v={data.get('id', '')}",
                        "duration": self._format_duration(data.get("duration", 0)),
                        "channel": data.get("channel", ""),
                    })
                except json.JSONDecodeError:
                    continue
            return entries

        return await asyncio.to_thread(_search)

    def _format_duration(self, seconds: int) -> str:
        if not seconds:
            return ""
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"
