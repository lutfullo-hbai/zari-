import pytest
from llm.memory import SessionMemory


@pytest.mark.asyncio
async def test_add_and_get():
    mem = SessionMemory()
    await mem.add("user", "salom")
    await mem.add("assistant", "salom, qanday yordam kerak?")
    msgs = mem.get()
    assert len(msgs) == 2
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"] == "salom"


def test_clear():
    mem = SessionMemory()
    mem._messages.append({"role": "user", "content": "salom"})
    mem.clear()
    assert len(mem.get()) == 0


@pytest.mark.asyncio
async def test_system_message():
    mem = SessionMemory()
    await mem.system("Sen yordamchisan")
    await mem.add("user", "salom")
    msgs = mem.get()
    assert msgs[0]["role"] == "system"
    assert msgs[1]["role"] == "user"
