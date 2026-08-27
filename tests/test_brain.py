import json
from unittest.mock import AsyncMock

import pytest

from core.brain import AVAILABLE_SKILLS, Action, AgentBrain, Decision


class TestDecision:
    def test_decision_defaults(self):
        d = Decision(actions=[])
        assert d.actions == []
        assert d.response == ""
        assert d.needs_clarification is False

    def test_action_defaults(self):
        a = Action(skill="weather")
        assert a.skill == "weather"
        assert a.params == {}


class TestAgentBrainDecide:
    @pytest.mark.asyncio
    async def test_single_intent_returns_directly(self):
        brain = AgentBrain()
        decision = await brain.decide("salom", matched_intents=["chat"])
        assert len(decision.actions) == 1
        assert decision.actions[0].skill == "chat"

    @pytest.mark.asyncio
    async def test_empty_intents_calls_llm(self):
        brain = AgentBrain()
        brain._llm = AsyncMock()
        brain._llm.chat_async = AsyncMock(
            return_value=json.dumps(
                {
                    "actions": [{"skill": "weather", "params": {"city": "Toshkent"}}],
                    "response": "",
                    "needs_clarification": False,
                }
            )
        )
        decision = await brain.decide("Toshkentda ob-havo qanday")
        assert len(decision.actions) == 1
        assert decision.actions[0].skill == "weather"
        assert decision.actions[0].params.get("city") == "Toshkent"

    @pytest.mark.asyncio
    async def test_llm_error_returns_clarification(self):
        brain = AgentBrain()
        brain._llm = AsyncMock()
        brain._llm.chat_async = AsyncMock(side_effect=Exception("llm down"))
        decision = await brain.decide("murakkab so'rov", matched_intents=[])
        assert decision.needs_clarification is True

    @pytest.mark.asyncio
    async def test_lazy_llm_not_created_on_fast_path(self):
        """Single intent — LLM client umuman yaratilmasligi kerak."""
        brain = AgentBrain()
        await brain.decide("salom", matched_intents=["chat"])
        assert brain._llm is None


class TestBrainParsePlan:
    def test_parse_valid_json(self):
        brain = AgentBrain()
        raw = json.dumps(
            {
                "actions": [{"skill": "search", "params": {}}],
                "response": "qidiryapman",
                "needs_clarification": False,
            }
        )
        decision = brain._parse_plan(raw)
        assert len(decision.actions) == 1
        assert decision.actions[0].skill == "search"
        assert decision.response == "qidiryapman"

    def test_parse_with_code_block(self):
        brain = AgentBrain()
        raw = (
            "```json\n"
            + json.dumps(
                {
                    "actions": [{"skill": "timer", "params": {"minutes": 5}}],
                }
            )
            + "\n```"
        )
        decision = brain._parse_plan(raw)
        assert decision.actions[0].skill == "timer"

    def test_parse_invalid_json_returns_text(self):
        brain = AgentBrain()
        decision = brain._parse_plan("bu oddiy matn, JSON emas")
        assert decision.response == "bu oddiy matn, JSON emas"
        assert decision.actions == []


class TestAvailableSkills:
    def test_skills_list_not_empty(self):
        assert len(AVAILABLE_SKILLS) > 0

    def test_common_skills_present(self):
        for s in ["weather", "search", "email", "timer", "notes"]:
            assert s in AVAILABLE_SKILLS
