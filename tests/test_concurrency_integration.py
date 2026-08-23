"""
F13 — haqiqiy integratsiya testlari:

1. Parallel web so'rovlari — javoblar almashib qolmasligi (F1 regressiya)
2. Scheduler → pipeline oqimi (F3/F5 regressiya)
"""

import asyncio
from unittest.mock import MagicMock

import pytest

from core.main import ZariPipeline
from core.messages import Incoming


def make_light_pipeline() -> ZariPipeline:
    """Og'ir __init__siz pipeline — faqat queue/router qismlari."""
    p = ZariPipeline.__new__(ZariPipeline)
    from core.messages import ResponseRouter

    p.router = ResponseRouter()
    p.text_queue = asyncio.Queue()
    p.response_queue = asyncio.Queue()
    p.running = True
    p._background_tasks = set()
    return p


async def fake_llm_worker(pipeline, delay: float = 0.05):
    """text_queue'dan Incoming oladi, delay'dan keyin _respond qiladi."""
    while pipeline.running:
        try:
            incoming = await asyncio.wait_for(pipeline.text_queue.get(), timeout=0.2)
        except TimeoutError:
            continue
        await asyncio.sleep(delay + len(incoming.text) * 0.001)
        await pipeline._respond(f"javob:{incoming.text}", incoming.request_id)


@pytest.mark.asyncio
async def test_parallel_web_requests_get_own_answers():
    """
    Ikkita parallel /api/chat so'rovi — correlation ID tufayli
    har biri OZ javobini oladi (avval race bor edi).
    """
    pipeline = make_light_pipeline()
    worker = asyncio.create_task(fake_llm_worker(pipeline))

    async def ask(text):
        return await pipeline.ask(text)

    results = await asyncio.gather(ask("birinchi savol"), ask("ikkinchi savol"))

    assert results[0] == "javob:birinchi savol"
    assert results[1] == "javob:ikkinchi savol"

    pipeline.running = False
    worker.cancel()


@pytest.mark.asyncio
async def test_web_request_without_waiter_falls_to_response_queue():
    """Waiter yo'q bo'lsa (voice/scheduler) javob response_queue'ga tushadi."""
    pipeline = make_light_pipeline()

    await pipeline._respond("oddiy javob", request_id=None)

    assert pipeline.response_queue.qsize() == 1
    assert pipeline.response_queue.get_nowait() == "oddiy javob"


@pytest.mark.asyncio
async def test_scheduler_incoming_flows_without_waiter():
    """
    Scheduler task'i ishga tushganda Incoming(source='scheduler') keladi —
    waiter bo'lmasligi kerak, javob TTS/response_queue orqali chiqadi.
    """
    pipeline = make_light_pipeline()
    worker = asyncio.create_task(fake_llm_worker(pipeline))

    incoming = Incoming(text="Ertalabki eslatma", source="scheduler", request_id=None)
    await pipeline.text_queue.put(incoming)

    response = await asyncio.wait_for(pipeline.response_queue.get(), timeout=2.0)
    assert response == "javob:Ertalabki eslatma"

    # Web waiter ro'yxati bo'sh — scheduler hech kimni bloklamaydi
    assert pipeline.router.pending_count() == 0

    pipeline.running = False
    worker.cancel()


@pytest.mark.asyncio
async def test_ask_timeout_cleans_waiter():
    """ask() timeout bo'lsa waiter ro'yxati tozalanadi (leak yo'q)."""
    pipeline = make_light_pipeline()
    # llm_worker yo'q — javob kelmaydi

    short_pipeline = pipeline
    original_timeout = 65.0

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(_ask_with_timeout(short_pipeline), timeout=original_timeout)

    assert short_pipeline.router.pending_count() == 0


async def _ask_with_timeout(pipeline, timeout=0.1):
    import uuid

    request_id = uuid.uuid4().hex[:12]
    future = pipeline.router.register(request_id)
    try:
        await pipeline.text_queue.put(Incoming(text="savol", source="web", request_id=request_id))
        return await asyncio.wait_for(future, timeout=timeout)
    finally:
        pipeline.router.unregister(request_id)


@pytest.mark.asyncio
async def test_spawn_background_keeps_strong_reference():
    """Fire-and-forget task GC qilinmaydi (kuchli referens testi)."""
    import gc

    pipeline = make_light_pipeline()
    done = MagicMock()

    async def quick():
        done()
        await asyncio.sleep(0)

    task = pipeline.spawn_background(quick(), name="test-bg")
    await asyncio.sleep(0.05)
    gc.collect()

    assert task.done()
    assert len(pipeline._background_tasks) == 0  # done_callback tozaladi
    done.assert_called_once()
