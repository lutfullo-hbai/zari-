import logging
import re
from datetime import datetime, timezone

from db.database import get_pool
from skills.base import BaseSkill

log = logging.getLogger("zari")

FACT_PATTERNS = [
    (r"(?:mening|meni|mening)\s+ismim\s+(\w+)", "name"),
    (r"ismim\s+(\w+)", "name"),
    (r"(?:mening|meni)\s+yoshim\s+(\d+)", "age"),
    (r"yoshim\s+(\d+)", "age"),
    (r"(?:mening|meni)\s+manzilim\s+(.+)", "address"),
    (r"men\s+(\w+)\s+(?:daman|man)", "profession"),
    (r"(?:mening|meni)\s+telefonim\s+([\d\-\+\s]+)", "phone"),
    (r"(?:mening|meni)\s+emailim\s+([\w\.@]+)", "email"),
    (r"(?:men|mening)\s+sevimli\s+(\w+)\s+(.+)", "favorite"),
    (r"menga\s+(\w+)\s+kerak", "need"),
]

ASK_PATTERNS = [
    (r"ismim\s+nima", "name"),
    (r"(?:men\s+)?(?:kimman|kim)", "name"),
    (r"yoshim\s+nechada", "age"),
    (r"necha\s+yoshdaman", "age"),
    (r"manzilim\s+qayer", "address"),
    (r"qayerda\s+yashayman", "address"),
    (r"telefonim\s+nima", "phone"),
    (r"emailim\s+nima", "email"),
    (r"sevimli\s+(\w+)\s+nima", "favorite_key"),
]


class WikiSkill(BaseSkill):
    priority = 15
    timeout = 5.0

    async def execute(self, query: str) -> dict | None:
        text = query.lower().strip()
        if not text:
            return None

        known = await self._check_ask(text)
        if known:
            return known

        learned = await self._check_learn(text)
        if learned:
            return learned

        if re.search(r"\b(bil|esla|yodda|wiki|eslab qol|uni esla|esimda saqla)\b", text):
            return await self._recall_all()

        return None

    async def _check_ask(self, text: str) -> dict | None:
        for pattern, key in ASK_PATTERNS:
            m = re.search(pattern, text)
            if not m:
                continue

            if key == "favorite_key" and m.lastindex and m.lastindex >= 1:
                category = m.group(1)
                full_key = f"favorite_{category}"
                val = await self._get(full_key)
                if val:
                    return {"response": f"Sevimli {category}ingiz: {val}", "context": f"{full_key}={val}", "source": "wiki"}
                return {"response": f"Sevimli {category}ingizni bilmayman. Ayting, eslab qolay.", "context": "", "source": "wiki"}

            if key == "name":
                val = await self._get("name")
                if val:
                    return {"response": f"Sizning ismingiz {val}.", "context": f"name={val}", "source": "wiki"}
                return {"response": "Ismingizni bilmayman. Ayting, eslab qolay.", "context": "", "source": "wiki"}

            if key == "age":
                val = await self._get("age")
                if val:
                    return {"response": f"Siz {val} yoshdasiz.", "context": f"age={val}", "source": "wiki"}
                return {"response": "Yoshingizni bilmayman.", "context": "", "source": "wiki"}

            if key == "address":
                val = await self._get("address")
                if val:
                    return {"response": f"Manzilingiz: {val}", "context": f"address={val}", "source": "wiki"}
                return {"response": "Manzilingizni bilmayman.", "context": "", "source": "wiki"}

            if key == "phone":
                val = await self._get("phone")
                if val:
                    return {"response": f"Telefon raqamingiz: {val}", "context": f"phone={val}", "source": "wiki"}
                return {"response": "Telefon raqamingizni bilmayman.", "context": "", "source": "wiki"}

            if key == "email":
                val = await self._get("email")
                if val:
                    return {"response": f"Emailingiz: {val}", "context": f"email={val}", "source": "wiki"}
                return {"response": "Emailingizni bilmayman.", "context": "", "source": "wiki"}

        return None

    async def _check_learn(self, text: str) -> dict | None:
        for pattern, key in FACT_PATTERNS:
            m = re.search(pattern, text)
            if not m:
                continue

            if key == "favorite" and m.lastindex and m.lastindex >= 2:
                category = m.group(1)
                value = m.group(2)
                full_key = f"favorite_{category}"
                await self._set(full_key, value)
                return {"response": f"Eslab qoldim: sevimli {category}ingiz {value}.", "context": f"{full_key}={value}", "source": "wiki"}

            if key == "name":
                val = m.group(1).capitalize()
                await self._set("name", val)
                return {"response": f"Tanishingizdan xursandman, {val}!", "context": f"name={val}", "source": "wiki"}

            if key == "age":
                val = m.group(1)
                await self._set("age", val)
                return {"response": f"Yoshingizni eslab qoldim: {val}", "context": f"age={val}", "source": "wiki"}

            if key == "address":
                val = m.group(1).strip()
                await self._set("address", val)
                return {"response": f"Manzilingizni eslab qoldim: {val}", "context": f"address={val}", "source": "wiki"}

            if key == "profession":
                val = m.group(1)
                await self._set("profession", val)
                return {"response": f"Siz {val} ekanligingizni eslab qoldim.", "context": f"profession={val}", "source": "wiki"}

            if key == "phone":
                val = m.group(1).strip()
                await self._set("phone", val)
                return {"response": f"Telefon raqamingizni eslab qoldim: {val}", "context": f"phone={val}", "source": "wiki"}

            if key == "email":
                val = m.group(1).strip()
                await self._set("email", val)
                return {"response": f"Emailingizni eslab qoldim: {val}", "context": f"email={val}", "source": "wiki"}

            if key == "need":
                val = m.group(1)
                await self._set("need", val)
                return {"response": f"Sizga {val} kerakligini eslab qoldim.", "context": f"need={val}", "source": "wiki"}

        return None

    async def _recall_all(self) -> dict | None:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT key, value FROM wiki ORDER BY key")

        if not rows:
            return {"response": "Siz haqingizda hech narsa bilmayman. Menga o'zingiz haqida ayting.", "context": "", "source": "wiki"}

        parts = []
        for r in rows:
            label = {
                "name": "Ismingiz",
                "age": "Yoshingiz",
                "address": "Manzilingiz",
                "phone": "Telefoningiz",
                "email": "Emailingiz",
                "profession": "Kasbingiz",
            }.get(r["key"], r["key"].capitalize())
            parts.append(f"{label}: {r['value']}")

        response = "Siz haqingizda bilganlarim:\n" + "\n".join(parts)
        return {"response": response, "context": str([dict(r) for r in rows]), "source": "wiki"}

    async def _get(self, key: str) -> str | None:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT value FROM wiki WHERE key = $1", key)
            return row["value"] if row else None

    async def _set(self, key: str, value: str):
        pool = await get_pool()
        async with pool.acquire() as conn:
            now = datetime.now(timezone.utc)
            await conn.execute(
                """INSERT INTO wiki (key, value, updated_at)
                   VALUES ($1, $2, $3)
                   ON CONFLICT(key) DO UPDATE SET value = $2, updated_at = $3""",
                key, value, now,
            )
