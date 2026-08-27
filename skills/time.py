"""TimeSkill — soat va sana so'rovlari (intent: "time")."""

from datetime import datetime

from skills.base import BaseSkill

WEEKDAYS_UZ = {
    0: "dushanba",
    1: "seshanba",
    2: "chorshanba",
    3: "payshanba",
    4: "juma",
    5: "shanba",
    6: "yakshanba",
}

MONTHS_UZ = {
    1: "yanvar",
    2: "fevral",
    3: "mart",
    4: "aprel",
    5: "may",
    6: "iyun",
    7: "iyul",
    8: "avgust",
    9: "sentabr",
    10: "oktabr",
    11: "noyabr",
    12: "dekabr",
}


class TimeSkill(BaseSkill):
    priority = 30
    timeout = 3.0

    async def execute(self, query: str) -> dict | None:
        text = (query or "").lower().strip()
        now = datetime.now()

        asks_date = any(w in text for w in ["bugun", "qanday kun", "sana", "nechanchi", "date"])
        asks_time = any(w in text for w in ["soat", "vaqt", "time", "necha"])

        if asks_date and not asks_time:
            response = f"Bugun {now.day}-{MONTHS_UZ[now.month]} {now.year}-yil, {WEEKDAYS_UZ[now.weekday()]}."
            context = f"date:{now.date().isoformat()}"
        else:
            response = f"Hozir soat {now.strftime('%H:%M')}, {WEEKDAYS_UZ[now.weekday()]}."
            context = f"time:{now.strftime('%H:%M')}"

        return {"response": response, "context": context, "source": "time"}
