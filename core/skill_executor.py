"""
SkillExecutor — intent bo'yicha skill tanlash va bajarish mantiqi.

ZariPipeline'dan ajratilgan (SRP): pipeline faqat worker orkestratsiyasi
bilan shug'ullanadi, skill routing zanjiri shu klassda.
"""

import logging
from collections.abc import Awaitable, Callable

from core.brain import AgentBrain
from core.rate_limiter import rate_limiter
from core.router import match_intents
from skills.base import BaseSkill

log = logging.getLogger("zari")

RespondFn = Callable[[str, str | None], Awaitable[None]]


class SkillExecutor:
    """Skill xaritasi + Brain zanjiri bilan so'rovni bajarish."""

    def __init__(
        self,
        skills: dict[str, BaseSkill],
        memory,
        dialog,
        brain: AgentBrain | None,
        respond: RespondFn,
    ) -> None:
        self._skills = skills
        self._memory = memory
        self._dialog = dialog
        self._brain = brain
        self._respond = respond

    def get_skill(self, name: str) -> BaseSkill | None:
        return self._skills.get(name)

    async def run_skill(self, skill: BaseSkill, text: str) -> str | None:
        try:
            result = await skill.execute_with_retry(text)
            if result:
                log.info("%s: %s", skill.__class__.__name__, result["response"])
                return result["response"]
        except Exception as e:
            log.error("%s skill error: %s", skill.__class__.__name__, e)
        return None

    async def execute_for_intent(self, intent: str, text: str, request_id: str | None) -> tuple[str | None, bool]:
        if intent == "search":
            search_result = await self._skills["search"].execute(text)
            if search_result:
                response = search_result["response"]
                ctx = search_result.get("context", "")
                src = search_result.get("source", "")
                await self._memory.add("system", f"Internetdan topilgan ma'lumot ({src}): {ctx}")
                log.info("Search (%s): %s", src, response)
                return response, True
            return None, False

        if intent == "email":
            email_result = await self._skills["email"].execute(text)
            if email_result:
                response = email_result["response"]
                log.info("Email: %s", response)
                return response, True
            return None, False

        if intent == "workflow":
            wf_skill = self.get_skill("n8n_workflow")
            if wf_skill:
                if not rate_limiter.is_allowed("N8nWorkflowSkill"):
                    await self._respond(
                        "Kechirasiz, workflow juda tez-tez ishga tushirilmoqda. Biroz kuting.",
                        request_id,
                    )
                    return None, True
                wf_result = await wf_skill.execute(text)
                if wf_result:
                    response = wf_result["response"]
                    ctx = wf_result.get("context", "")
                    src = wf_result.get("source", "")
                    await self._memory.add("system", f"N8N workflow ma'lumoti ({src}): {ctx}")
                    log.info("Workflow: %s", response)
                    return response, True
            return None, False

        skill = self.get_skill(intent)
        if not skill:
            return None, False

        skill_name = skill.__class__.__name__
        if getattr(skill, "requires_confirmation", False):
            if not rate_limiter.is_allowed(skill_name):
                await self._respond(
                    f"Kechirasiz, {skill_name} juda tez-tez ishlatilyapti. " "Biroz kuting va qayta urinib ko'ring.",
                    request_id,
                )
                return None, True

            question = self._dialog.begin_confirm(intent, text, skill)
            await self._respond(question, request_id)
            return None, True

        if intent in ("music", "weather", "timer", "notes"):
            if self._dialog.begin(intent, text):
                question = self._dialog.next_question()
                await self._respond(question, request_id)
                return None, True

        response = await self.run_skill(skill, text)
        if response:
            return response, True

        return None, False

    async def match_and_execute(self, text: str, request_id: str | None) -> tuple[str | None, bool]:
        for candidate_intent in match_intents(text):
            response, responded = await self.execute_for_intent(candidate_intent, text, request_id)
            if responded:
                return response, True
            if response is not None:
                return response, True
        return None, False

    async def route_and_execute(self, text: str, request_id: str | None) -> tuple[str | None, bool]:
        """
        Yo'naltirish: 1 intent → tez yo'l, ko'p intent → Agent Brain zanjiri.
        """
        matched = match_intents(text)
        if len(matched) <= 1 or self._brain is None:
            return await self.match_and_execute(text, request_id)

        decision = await self._brain.decide(text, matched_intents=matched)

        if decision.needs_clarification and decision.clarification_question:
            await self._respond(decision.clarification_question, request_id)
            return None, True

        if not decision.actions:
            if decision.response:
                await self._respond(decision.response, request_id)
                return decision.response, True
            # Brain action ham, javob ham bermadi — regex yo'lga qaytamiz
            return await self.match_and_execute(text, request_id)

        # Xavfsizlik devori: Brain LLM'i xavfli skill'ni avtomatik bajara olmaydi.
        # requires_confirmation bo'lgan skill faqat dialog tasdig'idan keyin ishlaydi.
        for action in decision.actions:
            skill = self.get_skill(action.skill)
            if skill is None:
                log.warning("Brain nomalum skill buyurdi: %s", action.skill)
                continue
            if getattr(skill, "requires_confirmation", False):
                query = str(action.params.get("query", text))
                question = self._dialog.begin_confirm(action.skill, query, skill)
                await self._respond(
                    f"Xavfli amal aniqlandi. Tasdiqlaysizmi?\n{question}",
                    request_id,
                )
                return None, True

        # Brain zanjiri — faqat xavfsiz skill'lar ketma-ket bajariladi
        responses: list[str] = []
        for action in decision.actions:
            skill = self.get_skill(action.skill)
            if skill is None:
                continue
            if not rate_limiter.is_allowed(skill.__class__.__name__):
                log.warning("Rate limit: %s o'tkazib yuborildi", action.skill)
                continue
            # Param sanitizatsiya: LLM params faqat o'qish/safe skill'larga.
            # Xavfli yo'nalishdagi hech narsa Brain tomonidan shakllantirilmaydi.
            query = str(action.params.get("query", text))
            result = await skill.execute_with_retry(query)
            if result and result.get("response"):
                responses.append(result["response"])
                ctx = result.get("context", "")
                await self._memory.add(
                    "system",
                    f"{action.skill} natijasi: {ctx or result['response']}",
                )

        if not responses:
            return None, False

        combined = "\n".join(responses)
        return combined, True
