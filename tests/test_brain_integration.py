"""Agent Brain — SkillExecutor integratsiya testlari (route_and_execute)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.brain import Action, Decision
from core.messages import ResponseRouter
from core.skill_executor import SkillExecutor


class FakeSkill:
    def __init__(self, response: str):
        self.response = response
        self.execute_with_retry = AsyncMock(return_value=self._result())

    def _result(self):
        return {
            "response": self.response,
            "context": f"ctx:{self.response}",
            "source": "fake",
        }


def make_executor(brain=None, skills=None) -> SkillExecutor:
    memory = MagicMock()
    memory.add = AsyncMock()
    dialog = MagicMock()
    return SkillExecutor(
        skills=skills or {},
        memory=memory,
        dialog=dialog,
        brain=brain,
        respond=AsyncMock(),
    )


@pytest.mark.asyncio
async def test_single_intent_uses_fast_path():
    fast = AsyncMock(return_value=("javob", True))
    executor = make_executor(brain=AsyncMock())
    executor.match_and_execute = fast

    response, responded = await executor.route_and_execute("ob-havo qanday", "req-1")

    assert responded is True
    assert response == "javob"
    executor._brain.decide.assert_not_awaited()


@pytest.mark.asyncio
async def test_multi_intent_runs_brain_chain():
    brain = MagicMock()
    brain.decide = AsyncMock(return_value=Decision(actions=[Action(skill="search"), Action(skill="wiki")]))
    search_skill = FakeSkill("kurs 12 500")
    wiki_skill = FakeSkill("eslab qoldim")
    executor = make_executor(brain=brain, skills={"search": search_skill, "wiki": wiki_skill})

    response, responded = await executor.route_and_execute("valyuta kursini top va eslab qol", "req-2")

    assert responded is True
    assert "kurs" in response
    assert "eslab" in response

    search_skill.execute_with_retry.assert_awaited_once()
    wiki_skill.execute_with_retry.assert_awaited_once()
    assert executor._memory.add.await_count == 2


@pytest.mark.asyncio
async def test_brain_clarification_responds_question():
    brain = MagicMock()
    brain.decide = AsyncMock(
        return_value=Decision(
            actions=[],
            needs_clarification=True,
            clarification_question="Qaysi shahar?",
        )
    )
    router = ResponseRouter()
    respond = AsyncMock(wraps=lambda text, rid: router.resolve(rid, text))
    executor = SkillExecutor(skills={}, memory=MagicMock(), dialog=MagicMock(), brain=brain, respond=respond)

    request_id = "req-3"
    future = router.register(request_id)

    async def consume():
        # "ob-havo" + "musiqa" — 2 intent, brain ga yo'naltiriladi
        response, responded = await executor.route_and_execute("ob-havo ayt va musiqa qo'y", request_id)
        assert responded is True
        assert response is None

    task = asyncio.create_task(consume())
    answer = await asyncio.wait_for(future, timeout=1)
    await task

    assert answer == "Qaysi shahar?"


@pytest.mark.asyncio
async def test_disabled_brain_falls_back_to_regex():
    fast = AsyncMock(return_value=(None, False))
    executor = make_executor(brain=None)
    executor.match_and_execute = fast

    response, responded = await executor.route_and_execute("musiqa va ob-havo va email", "req-4")

    assert responded is False
    assert response is None


@pytest.mark.asyncio
async def test_brain_unknown_skill_is_skipped():
    brain = MagicMock()
    brain.decide = AsyncMock(return_value=Decision(actions=[Action(skill="mavjud"), Action(skill="ghost")]))
    skill = FakeSkill("natija")
    executor = make_executor(brain=brain, skills={"mavjud": skill})

    # "musiqa" + "ob-havo" — 2 intent, brain zanjiriga kiradi
    response, responded = await executor.route_and_execute("musiqa qo'y va ob-havo ayt", "req-5")

    assert responded is True
    assert response == "natija"


@pytest.mark.asyncio
async def test_brain_chain_all_fail_returns_none():
    brain = MagicMock()
    brain.decide = AsyncMock(return_value=Decision(actions=[Action(skill="ghost1"), Action(skill="ghost2")]))
    executor = make_executor(brain=brain)

    response, responded = await executor.route_and_execute("musiqa qo'y va ob-havo ayt", "req-6")

    assert responded is False
    assert response is None


@pytest.mark.asyncio
async def test_brain_direct_response_sent_via_respond():
    """Brain action'siz faqat javob qaytarsa — respond orqali yetkaziladi."""
    brain = MagicMock()
    brain.decide = AsyncMock(return_value=Decision(actions=[], response="Ikki xil so'rov, bittasini tanlang"))
    respond = AsyncMock()
    executor = SkillExecutor(
        skills={},
        memory=MagicMock(),
        dialog=MagicMock(),
        brain=brain,
        respond=respond,
    )

    response, responded = await executor.route_and_execute("musiqa qo'y va ob-havo ayt", "req-7")

    assert responded is True
    assert response == "Ikki xil so'rov, bittasini tanlang"
    respond.assert_awaited_once_with("Ikki xil so'rov, bittasini tanlang", "req-7")


@pytest.mark.asyncio
async def test_dangerous_brain_action_asks_confirmation():
    """
    REGRESSIYA: Brain email/fayl-o'chirish kabi xavfli skill'ni
    avtomatik bajara olmaydi — tasdiqlash savoli beriladi.
    """
    brain = MagicMock()
    brain.decide = AsyncMock(return_value=Decision(actions=[Action(skill="email", params={"query": "salom de"})]))
    respond = AsyncMock()
    dialog = MagicMock()
    dialog.begin_confirm.return_value = "Akbar akaga yuborilsinmi?"

    class DangerousSkill:
        requires_confirmation = True
        execute_with_retry = AsyncMock()

    executor = SkillExecutor(
        skills={"email": DangerousSkill()},
        memory=MagicMock(),
        dialog=dialog,
        brain=brain,
        respond=respond,
    )

    # "email" + "ob-havo" — 2 intent, brain yo'li
    response, responded = await executor.route_and_execute("akbarga email yubor va ob-havo ayt", "req-s1")

    assert responded is True
    assert response is None
    skill = executor._skills["email"]
    skill.execute_with_retry.assert_not_awaited()
    dialog.begin_confirm.assert_called_once_with("email", "salom de", skill)
    assert "Xavfli amal aniqlandi" in respond.await_args.args[0]


@pytest.mark.asyncio
async def test_brain_rate_limit_skips_action():
    """Rate limit tushgan skill zanjir bajarilishidan chiqarib yuboriladi."""
    from core.rate_limiter import rate_limiter

    brain = MagicMock()
    brain.decide = AsyncMock(return_value=Decision(actions=[Action(skill="wiki")]))
    skill = FakeSkill("javob")
    executor = make_executor(brain=brain, skills={"wiki": skill})

    with __import__("unittest").mock.patch.object(rate_limiter, "is_allowed", return_value=False):
        response, responded = await executor.route_and_execute("musiqa qo'y va ob-havo ayt", "req-rl")

    assert responded is False
    assert response is None
    skill.execute_with_retry.assert_not_awaited()


@pytest.mark.asyncio
async def test_safe_chain_unaffected_by_safety_wall():
    """Xavfsiz skill'lar (search/wiki) avvalgidek erkin bajariladi."""
    brain = MagicMock()
    brain.decide = AsyncMock(return_value=Decision(actions=[Action(skill="search"), Action(skill="wiki")]))
    search_skill = FakeSkill("natija")
    wiki_skill = FakeSkill("fakt")
    executor = make_executor(brain=brain, skills={"search": search_skill, "wiki": wiki_skill})
    for s in (search_skill, wiki_skill):
        s.requires_confirmation = False

    response, responded = await executor.route_and_execute("qidiruv qil va eslab qol", "req-safe")

    assert responded is True
    assert "natija" in response and "fakt" in response
