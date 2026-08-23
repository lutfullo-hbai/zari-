"""Agent Brain — pipeline integratsiya testlari (_route_and_execute)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.brain import Action, Decision
from core.main import ZariPipeline
from core.messages import ResponseRouter


class FakeSkill:
    def __init__(self, response: str):
        self.response = response
        self.execute_with_retry = AsyncMock(return_value=self._result())

    def _result(self):
        return {"response": self.response, "context": f"ctx:{self.response}", "source": "fake"}


def make_pipeline(brain=None) -> ZariPipeline:
    """Og'ir __init__siz pipeline — faqat _route_and_execute uchun kerakli qismlar."""
    pipeline = ZariPipeline.__new__(ZariPipeline)
    pipeline.router = ResponseRouter()
    pipeline.response_queue = asyncio.Queue()
    pipeline._skill_map = {}
    pipeline.memory = MagicMock()
    pipeline.memory.add = AsyncMock()
    pipeline.dialog = MagicMock()
    pipeline.rate_limiter = MagicMock()
    pipeline.brain = brain
    return pipeline


@pytest.mark.asyncio
async def test_single_intent_uses_fast_path():
    pipeline = make_pipeline(brain=AsyncMock())
    pipeline._match_and_execute_skills = AsyncMock(return_value=("javob", True))

    response, responded = await pipeline._route_and_execute("ob-havo qanday", "req-1")

    assert responded is True
    assert response == "javob"
    pipeline.brain.decide.assert_not_awaited()


@pytest.mark.asyncio
async def test_multi_intent_runs_brain_chain():
    brain = MagicMock()
    brain.decide = AsyncMock(return_value=Decision(actions=[Action(skill="search"), Action(skill="wiki")]))
    pipeline = make_pipeline(brain=brain)
    search_skill = FakeSkill("kurs 12 500")
    wiki_skill = FakeSkill("eslab qoldim")
    pipeline._skill_map = {"search": search_skill, "wiki": wiki_skill}

    response, responded = await pipeline._route_and_execute("valyuta kursini top va eslab qol", "req-2")

    assert responded is True
    assert "kurs" in response
    assert "eslab" in response

    search_skill.execute_with_retry.assert_awaited_once()
    wiki_skill.execute_with_retry.assert_awaited_once()
    assert pipeline.memory.add.await_count == 2


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
    pipeline = make_pipeline(brain=brain)

    request_id = "req-3"
    future = pipeline.router.register(request_id)

    async def consume():
        # "ob-havo" + "musiqa" — 2 intent, brain ga yo'naltiriladi
        response, responded = await pipeline._route_and_execute("ob-havo ayt va musiqa qo'y", request_id)
        assert responded is True
        assert response is None

    task = asyncio.create_task(consume())
    answer = await asyncio.wait_for(future, timeout=1)
    await task

    assert answer == "Qaysi shahar?"


@pytest.mark.asyncio
async def test_disabled_brain_falls_back_to_regex():
    pipeline = make_pipeline(brain=None)
    pipeline._match_and_execute_skills = AsyncMock(return_value=(None, False))

    response, responded = await pipeline._route_and_execute("musiqa va ob-havo va email", "req-4")

    assert responded is False
    assert response is None


@pytest.mark.asyncio
async def test_brain_unknown_skill_is_skipped():
    brain = MagicMock()
    brain.decide = AsyncMock(return_value=Decision(actions=[Action(skill="mavjud"), Action(skill="ghost")]))
    pipeline = make_pipeline(brain=brain)
    skill = FakeSkill("natija")
    pipeline._skill_map = {"mavjud": skill}

    # "musiqa" + "ob-havo" — 2 intent, brain zanjiriga kiradi
    response, responded = await pipeline._route_and_execute("musiqa qo'y va ob-havo ayt", "req-5")

    assert responded is True
    assert response == "natija"


@pytest.mark.asyncio
async def test_brain_chain_all_fail_returns_none():
    brain = MagicMock()
    brain.decide = AsyncMock(return_value=Decision(actions=[Action(skill="ghost1"), Action(skill="ghost2")]))
    pipeline = make_pipeline(brain=brain)

    response, responded = await pipeline._route_and_execute("musiqa qo'y va ob-havo ayt", "req-6")

    assert responded is False
    assert response is None
