"""
Agent Brain — LLM-based Decision Engine.

Foydalanuvchi so'rovlarini tahlil qilib, qaysi skill'larni ishga tushirish
kerakligini qaror qiladi. Oddiy regex routing dan tashqari, murakkab
so'rovlar uchun LLM orqali reja tuzadi.
"""

import json
import logging
from dataclasses import dataclass, field

from llm.factory import create_llm_client

log = logging.getLogger("zari")

AVAILABLE_SKILLS = [
    "weather",
    "time",
    "system",
    "volume",
    "brightness",
    "input",
    "media",
    "browser",
    "organize",
    "documents",
    "code_runner",
    "system_info",
    "email",
    "music",
    "workflow",
    "notes",
    "timer",
    "calculator",
    "clipboard",
    "screenshot",
    "filemanager",
    "network",
    "wiki",
    "search",
]


@dataclass
class Action:
    skill: str
    params: dict = field(default_factory=dict)


@dataclass
class Decision:
    actions: list[Action]
    response: str = ""
    needs_clarification: bool = False
    clarification_question: str = ""


_PLANNING_PROMPT = """Sen Zari AI yordamchisining Decision Engine'isan.
Foydalanuvchi so'rovini tahlil qilib, qaysi skill'larni ketma-ket ishga tushirish kerakligini aniqla.

Mavjud skill'lar: {skills}

Javobni JSON formatida ber:
{{
  "actions": [
    {{"skill": "skill_nomi", "params": {{"key": "value"}}}},
    ...
  ],
  "response": "qo'shimcha javob (kerak bo'lsa)",
  "needs_clarification": false,
  "clarification_question": "so'rov aniq emas bo'lsa, savol"
}}

Qoidalar:
- Birinchi navbatda aniq skill'larni ishlat
- Murakkab so'rovlar uchun chain qil (bir nechta action)
- Agar so'rov aniq bo'lmasa, clarification_question ber
- Faqat JSON qaytar, boshqa hech narsa yozma
- Agar hech qanday skill mos kelmasa, actions ni bo'sh qoldir

Foydalanuvchi so'rovi: {text}
Kontekst: {context}"""


class AgentBrain:
    """LLM-based Decision Engine — murakkab so'rovlar uchun reja tuzadi."""

    def __init__(self) -> None:
        self._llm = None

    def _get_llm(self):
        """Lazy init — konstruktor og'ir dependency'larga bog'lanmasin."""
        if self._llm is None:
            self._llm = create_llm_client()
        return self._llm

    async def decide(
        self,
        text: str,
        context: dict | None = None,
        matched_intents: list[str] | None = None,
    ) -> Decision:
        """Foydalanuvchi so'roviga qaror qiladi."""
        if matched_intents and len(matched_intents) == 1:
            return Decision(actions=[Action(skill=matched_intents[0])])

        if matched_intents and len(matched_intents) <= 3:
            decision = await self._plan_with_llm(text, context, matched_intents)
            if decision.actions:
                return decision

        if matched_intents:
            return Decision(actions=[Action(skill=matched_intents[0])])

        decision = await self._plan_with_llm(text, context, None)
        return decision

    async def _plan_with_llm(
        self,
        text: str,
        context: dict | None,
        hints: list[str] | None,
    ) -> Decision:
        """LLM orqali reja tuzadi."""
        context_str = json.dumps(context or {}, ensure_ascii=False, default=str)
        if hints:
            context_str += f"\nRegex topilgan intent'lar: {hints}"

        prompt = _PLANNING_PROMPT.format(
            skills=", ".join(AVAILABLE_SKILLS),
            text=text,
            context=context_str,
        )

        try:
            raw = await self._get_llm().chat_async(
                [{"role": "user", "content": prompt}],
                timeout=30,
            )
            return self._parse_plan(raw)
        except Exception as e:
            log.warning("Brain LLM reja tuzishda xatolik: %s", e)
            if hints:
                return Decision(actions=[Action(skill=hints[0])])
            return Decision(
                actions=[],
                response="Buni tushunmadim. Boshqachadan ayting.",
                needs_clarification=True,
                clarification_question="Nima qilishni xohlaysiz?",
            )

    def _parse_plan(self, raw: str) -> Decision:
        """LLM javobini Decision ga parse qiladi."""
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1])

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            log.warning("Brain: JSON parse xatosi: %s", text[:200])
            return Decision(actions=[], response=text[:500])

        actions = [
            Action(skill=a.get("skill", "chat"), params=a.get("params", {}))
            for a in data.get("actions", [])
            if a.get("skill")
        ]

        return Decision(
            actions=actions,
            response=data.get("response", ""),
            needs_clarification=data.get("needs_clarification", False),
            clarification_question=data.get("clarification_question", ""),
        )
