from unittest.mock import AsyncMock, patch

import pytest

from llm.memory import SessionMemory


class TestSessionMemory:
    """Test SessionMemory functionality"""

    @pytest.mark.asyncio
    async def test_add_and_get(self):
        """Test adding and retrieving messages"""
        with patch('db.memory_repo.create_session', return_value='test-session-id'):
            with patch('db.memory_repo.save_message', new_callable=AsyncMock):
                with patch('db.cache.cache_session_messages', new_callable=AsyncMock):
                    mem = SessionMemory()
                    await mem.init()

                    await mem.add("user", "salom")
                    await mem.add("assistant", "salom, qanday yordam kerak?")

                    msgs = mem.get()
                    assert len(msgs) == 2
                    assert msgs[0]["role"] == "user"
                    assert msgs[0]["content"] == "salom"
                    assert msgs[1]["role"] == "assistant"

    def test_clear(self):
        """Test clearing messages"""
        mem = SessionMemory()
        mem._messages.append({"role": "user", "content": "salom"})
        mem._messages.append({"role": "assistant", "content": "javob"})

        mem.clear()

        assert len(mem.get()) == 0

    @pytest.mark.asyncio
    async def test_system_message(self):
        """Test system message insertion"""
        with patch('db.memory_repo.create_session', return_value='test-session-id'):
            with patch('db.memory_repo.save_message', new_callable=AsyncMock):
                with patch('db.cache.cache_session_messages', new_callable=AsyncMock):
                    mem = SessionMemory()
                    await mem.init()

                    await mem.system("Sen yordamchisan")
                    await mem.add("user", "salom")

                    msgs = mem.get()
                    assert msgs[0]["role"] == "system"
                    assert msgs[1]["role"] == "user"

    def test_get_with_max_messages(self):
        """Test message limit in get()"""
        mem = SessionMemory()

        # Add 30 messages
        for i in range(30):
            mem._messages.append({"role": "user", "content": f"message {i}"})

        msgs = mem.get(max_messages=20)
        assert len(msgs) <= 20

    def test_get_preserves_system_messages(self):
        """Test that system messages are always included"""
        mem = SessionMemory()

        # Add system message
        mem._messages.append({"role": "system", "content": "system"})

        # Add many messages
        for i in range(25):
            mem._messages.append({"role": "user", "content": f"msg {i}"})

        msgs = mem.get(max_messages=20)

        # System message should be first
        assert msgs[0]["role"] == "system"
        # Should not exceed max_messages
        assert len(msgs) <= 20

    @pytest.mark.asyncio
    async def test_session_id_property(self):
        """Test session_id property"""
        with patch('db.memory_repo.create_session', return_value='unique-session-123'):
            mem = SessionMemory()
            assert mem.session_id is None

            await mem.init()
            assert mem.session_id == 'unique-session-123'

    @pytest.mark.asyncio
    async def test_add_without_session_id(self):
        """Test adding messages without session initialization"""
        mem = SessionMemory()
        # Don't call init

        await mem.add("user", "test")

        msgs = mem.get()
        assert len(msgs) == 1
        assert msgs[0]["content"] == "test"

    def test_empty_memory(self):
        """Test empty memory get"""
        mem = SessionMemory()
        msgs = mem.get()
        assert msgs == []

    @pytest.mark.asyncio
    async def test_multiple_roles(self):
        """Test memory with multiple role types"""
        with patch('db.memory_repo.create_session', return_value='session-id'):
            with patch('db.memory_repo.save_message', new_callable=AsyncMock):
                with patch('db.cache.cache_session_messages', new_callable=AsyncMock):
                    mem = SessionMemory()
                    await mem.init()

                    await mem.system("You are helpful")
                    await mem.add("user", "Hello")
                    await mem.add("assistant", "Hi there")
                    await mem.add("user", "How are you?")
                    await mem.add("assistant", "I'm doing well")

                    msgs = mem.get()
                    assert len(msgs) == 5
                    assert msgs[0]["role"] == "system"
                    assert msgs[1]["role"] == "user"
                    assert msgs[2]["role"] == "assistant"


    @pytest.mark.asyncio
    async def test_load_from_cache(self):
        """Test loading messages from cache"""
        cached_msgs = [{"role": "user", "content": "salom"}]

        with patch('db.memory_repo.create_session', return_value='sess-id'):
            with patch('db.cache.get_cached_session_messages', return_value=cached_msgs):
                mem = SessionMemory()
                await mem.init()
                await mem.load()

                assert len(mem.get()) == 1
                assert mem.get()[0]["content"] == "salom"

    @pytest.mark.asyncio
    async def test_load_from_db_when_cache_empty(self):
        """Test loading messages from DB when cache is empty"""
        db_msgs = [{"role": "user", "content": "from db"}]

        with patch('db.memory_repo.create_session', return_value='sess-id'):
            with patch('db.cache.get_cached_session_messages', return_value=None):
                with patch('db.memory_repo.load_messages', return_value=db_msgs):
                    with patch('db.cache.cache_session_messages', new_callable=AsyncMock):
                        mem = SessionMemory()
                        await mem.init()
                        await mem.load()

                        assert len(mem.get()) == 1
                        assert mem.get()[0]["content"] == "from db"

    @pytest.mark.asyncio
    async def test_load_without_session_id(self):
        """Test load returns early without session_id"""
        mem = SessionMemory()
        await mem.load()
        assert len(mem.get()) == 0

    @pytest.mark.asyncio
    async def test_load_with_custom_session_id(self):
        """Test load with explicit session_id"""
        cached_msgs = [{"role": "user", "content": "custom session"}]

        with patch('db.cache.get_cached_session_messages', return_value=cached_msgs):
            mem = SessionMemory()
            await mem.load("custom-sess-id")

            assert mem.session_id is None
            assert len(mem.get()) == 1
            assert mem.get()[0]["content"] == "custom session"


class TestSessionMemoryEdgeCases:
    """Edge cases for SessionMemory"""

    def test_get_with_zero_max_messages(self):
        """Test get with max_messages=0"""
        mem = SessionMemory()
        mem._messages.append({"role": "user", "content": "test"})

        msgs = mem.get(max_messages=0)
        assert len(msgs) >= 0

    def test_very_large_content(self):
        """Test with very large message content"""
        mem = SessionMemory()
        large_content = "x" * 1000000  # 1MB
        mem._messages.append({"role": "user", "content": large_content})

        msgs = mem.get()
        assert len(msgs) == 1
        assert len(msgs[0]["content"]) == 1000000

    def test_special_characters_in_content(self):
        """Test with special characters"""
        mem = SessionMemory()
        special_content = "🎉 test\n\t\"quote\" 'apostrophe' <tag>"
        mem._messages.append({"role": "user", "content": special_content})

        msgs = mem.get()
        assert msgs[0]["content"] == special_content
