"""ResponseRouter va Incoming — correlation ID testlari."""

import asyncio

import pytest

from core.messages import Incoming, ResponseRouter


class TestIncoming:
    def test_defaults_are_voice(self):
        msg = Incoming(text="salom")
        assert msg.source == "voice"
        assert msg.request_id is None

    def test_web_message_with_request_id(self):
        msg = Incoming(text="salom", source="web", request_id="abc123")
        assert msg.source == "web"
        assert msg.request_id == "abc123"


class TestResponseRouter:
    @pytest.mark.asyncio
    async def test_register_returns_future(self):
        router = ResponseRouter()
        future = router.register("req-1")
        assert not future.done()
        assert router.pending_count() == 1

    @pytest.mark.asyncio
    async def test_resolve_delivers_to_waiter(self):
        router = ResponseRouter()
        future = router.register("req-1")

        delivered = router.resolve("req-1", "javob")

        assert delivered is True
        assert future.result() == "javob"

    @pytest.mark.asyncio
    async def test_resolve_without_request_id(self):
        router = ResponseRouter()
        assert router.resolve(None, "javob") is False

    @pytest.mark.asyncio
    async def test_resolve_unknown_request_id(self):
        router = ResponseRouter()
        assert router.resolve("nope", "javob") is False

    @pytest.mark.asyncio
    async def test_unregister_cancels_future(self):
        router = ResponseRouter()
        future = router.register("req-1")
        router.unregister("req-1")

        assert router.pending_count() == 0
        assert future.cancelled()

    @pytest.mark.asyncio
    async def test_concurrent_requests_get_own_answers(self):
        """Race condition regession: 2 so'rov — javoblar almashinmasligi kerak."""
        router = ResponseRouter()
        fut_a = router.register("req-a")
        fut_b = router.register("req-b")

        router.resolve("req-b", "B javobi")
        router.resolve("req-a", "A javobi")

        assert fut_a.result() == "A javobi"
        assert fut_b.result() == "B javobi"

    @pytest.mark.asyncio
    async def test_wait_with_timeout(self):
        router = ResponseRouter()
        future = router.register("req-slow")

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(future, timeout=0.05)

    @pytest.mark.asyncio
    async def test_resolve_after_timeout_is_noop(self):
        router = ResponseRouter()
        future = router.register("req-1")

        try:
            await asyncio.wait_for(future, timeout=0.05)
        except TimeoutError:
            pass

        delivered = router.resolve("req-1", "kechikkan javob")
        assert delivered is False

    @pytest.mark.asyncio
    async def test_ask_end_to_end_routing(self):
        """pipeline.ask() oqimini simulyatsiya qiladi."""
        router = ResponseRouter()
        request_id = "web-123"
        future = router.register(request_id)

        async def fake_llm_worker():
            await asyncio.sleep(0.01)
            router.resolve(request_id, "Zari javobi")

        asyncio.create_task(fake_llm_worker())
        result = await asyncio.wait_for(future, timeout=1)

        assert result == "Zari javobi"
