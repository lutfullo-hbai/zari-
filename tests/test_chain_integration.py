"""AgentBrain zanjiri integratsiya testlari.

Maqsad: skill_executor.route_and_execute ning ko'p qadamli zanjir
xatti-harakatlari end-to-end tekshiriladi:
  - tartib saqlanishi va javoblar birlashtirilishi
  - zanjir o'rtasidagi XAVFLI skill BUTUN zanjirni bekor qilishi
  - rate-limit qadami o'tkazib yuborilib, qolganlari bajarilishi
  - LLM nomalum skill buyursa jimgina o'tkazib yuborilishi
"""

from unittest.mock import AsyncMock

import pytest

from core.brain import Action, Decision
from core.dialog_state import DialogManager
from core.rate_limiter import rate_limiter
from core.skill_executor import SkillExecutor
from skills.base import BaseSkill


def _make_safe_skill(name: str, calls: list[str], reply: str) -> BaseSkill:
    class SafeSkill(BaseSkill):
        async def execute(self, query: str) -> dict | None:
            calls.append(name)
            return {"response": f"{reply} ({name})", "context": "", "source": name}

    cls = type(f"{name.capitalize()}Skill", (SafeSkill,), {})
    return cls()


def _make_dangerous_skill(name: str, calls: list[str]) -> BaseSkill:
    class DangerSkill(BaseSkill):
        requires_confirmation = True
        confirmation_type = "danger"

        async def execute(self, query: str) -> dict | None:
            calls.append(name)
            return {"response": f"BAJARILDI {name}", "context": "", "source": name}

    cls = type(f"{name.capitalize()}DangerSkill", (DangerSkill,), {})
    return cls()


class FakeBrain:
    def __init__(self, actions: list[Action]):
        self._actions = actions
        self.calls = 0

    async def decide(self, text: str, matched_intents=None) -> Decision:
        self.calls += 1
        return Decision(actions=self._actions)


def _make_executor(
    skills: dict[str, BaseSkill],
) -> tuple[SkillExecutor, list]:
    """(executor, respond_qabul_qilingan_javoblar) juftligi."""
    responded: list[str] = []
    executor = SkillExecutor(
        skills=skills,
        memory=AsyncMock(),
        dialog=DialogManager(),
        brain=None,
        respond=AsyncMock(side_effect=lambda text, rid: responded.append(text)),
    )
    return executor, responded


async def _run_chain(executor: SkillExecutor, actions: list[Action]) -> tuple[str | None, bool]:
    executor._brain = FakeBrain(actions)
    # 3 ta intent moslaydigan matn — Brain yo'liga kirish uchun
    return await executor.route_and_execute("ob-havo qanday va eslatma qo'y va taymer qo'y", request_id="req-1")


class TestChainHappyPath:
    @pytest.mark.asyncio
    async def test_three_step_chain_executes_in_order(self):
        """[a, b, c] rejasi TARTIB bilan bajarilib, javoblar \\n bilan birlashadi."""
        calls: list[str] = []
        skills = {
            "alpha": _make_safe_skill("alpha", calls, "Birinchi"),
            "beta": _make_safe_skill("beta", calls, "Ikkinchi"),
            "gamma": _make_safe_skill("gamma", calls, "Uchinchi"),
        }
        executor, responded = _make_executor(skills)

        result, handled = await _run_chain(
            executor,
            [Action(skill="alpha"), Action(skill="beta"), Action(skill="gamma")],
        )

        assert handled is True
        assert calls == ["alpha", "beta", "gamma"]
        assert result == "Birinchi (alpha)\nIkkinchi (beta)\nUchinchi (gamma)"
        # Birlashgan javob respond orqali emas, return value sifatida ketadi
        assert responded == []

    @pytest.mark.asyncio
    async def test_brain_called_only_for_multi_intent(self):
        """Bitta intentda Brain chaqirilmaydi (tez yo'l)."""
        calls: list[str] = []
        skills = {"alpha": _make_safe_skill("alpha", calls, "Javob")}
        executor, _ = _make_executor(skills)
        fake_brain = FakeBrain([Action(skill="alpha")])
        executor._brain = fake_brain

        await executor.route_and_execute("alpha uchun savol", None)

        assert fake_brain.calls == 0


class TestChainSafetyAbort:
    @pytest.mark.asyncio
    async def test_dangerous_mid_chain_aborts_everything(self):
        """KRITIK: [xavfsiz, XAVFLI, xavfsiz] rejada HECH NARSA bajarilmaydi.

        Executor reja to'liq shakllangach pre-skan qiladi — birinchi
        xavfli qadamda butun zanjir bekor bo'lib, tasdiq so'raladi.
        """
        calls: list[str] = []
        dangerous = _make_dangerous_skill("danger_zone", calls)
        skills = {
            "alpha": _make_safe_skill("alpha", calls, "Birinchi"),
            "delta": dangerous,
            "gamma": _make_safe_skill("gamma", calls, "Uchinchi"),
        }
        executor, responded = _make_executor(skills)

        result, handled = await _run_chain(
            executor,
            [Action(skill="alpha"), Action(skill="delta"), Action(skill="gamma")],
        )

        # HECH QAYSI skill ishga tushmagan — hatto xavfsizlari ham
        assert calls == [], f"Bajarilgan skill'lar: {calls}"
        assert result is None
        assert handled is True
        # Tasdiq savoli foydalanuvchiga yetgan
        assert any("Xavfli amal aniqlandi" in r for r in responded)
        # Dialog tasdiq holatiga o'tgan
        assert executor._dialog.pending_intent == "delta"
        assert executor._dialog.danger_skill is dangerous

    @pytest.mark.asyncio
    async def test_dangerous_first_step_also_aborts(self):
        calls: list[str] = []
        skills = {
            "delta": _make_dangerous_skill("delta", calls),
            "gamma": _make_safe_skill("gamma", calls, "Oxirgi"),
        }
        executor, responded = _make_executor(skills)

        result, handled = await _run_chain(executor, [Action(skill="delta"), Action(skill="gamma")])

        assert calls == []
        assert result is None
        assert handled is True
        assert len(responded) == 1


class TestChainResilience:
    @pytest.mark.asyncio
    async def test_unknown_skill_skipped_others_execute(self):
        """LLM nomalum skill buyursa — faqat o'sha qadam o'tkazib yuboriladi."""
        calls: list[str] = []
        skills = {
            "alpha": _make_safe_skill("alpha", calls, "Birinchi"),
            "gamma": _make_safe_skill("gamma", calls, "Uchinchi"),
        }
        executor, _ = _make_executor(skills)

        result, handled = await _run_chain(
            executor,
            [Action(skill="alpha"), Action(skill="ghost_skill"), Action(skill="gamma")],
        )

        assert calls == ["alpha", "gamma"]
        assert handled is True
        assert "ghost_skill" not in (result or "")

    @pytest.mark.asyncio
    async def test_rate_limited_step_skipped_others_execute(self):
        """Rate-limitlangan skill o'tkazib yuboriladi, zanjir davom etadi."""
        calls: list[str] = []

        class LimitedSkill(BaseSkill):
            async def execute(self, query):
                calls.append("limited")
                return {"response": "LIMITED", "context": "", "source": "limited"}

        limited_cls_name = LimitedSkill.__name__
        skills = {
            "limited": LimitedSkill(),
            "gamma": _make_safe_skill("gamma", calls, "Uchinchi"),
        }
        executor, _ = _make_executor(skills)

        original_is_allowed = rate_limiter.is_allowed
        try:
            rate_limiter.is_allowed = lambda name: name != limited_cls_name
            result, handled = await _run_chain(executor, [Action(skill="limited"), Action(skill="gamma")])
        finally:
            rate_limiter.is_allowed = original_is_allowed

        assert calls == ["gamma"], "Limitlangan skill bajarilmagan bo'lishi kerak"
        assert handled is True
        assert result == "Uchinchi (gamma)"

    @pytest.mark.asyncio
    async def test_all_steps_fail_returns_not_handled(self):
        """Hech bir skill javob bermasa — regex yo'lga qaytish uchun False."""

        class SilentSkill(BaseSkill):
            async def execute(self, query):
                return None

        skills = {"silent": SilentSkill()}
        executor, _ = _make_executor(skills)

        result, handled = await _run_chain(executor, [Action(skill="silent")])

        assert result is None
        assert handled is False
