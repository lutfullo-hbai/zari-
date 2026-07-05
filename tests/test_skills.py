import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from skills.search import SearchSkill
from skills.base import BaseSkill
from skills.loader import SkillLoader


class TestBaseSkill:
    """Test BaseSkill abstract class"""

    def test_base_skill_is_abstract(self):
        """Test that BaseSkill cannot be instantiated"""
        with pytest.raises(TypeError):
            BaseSkill()

    def test_concrete_skill_implementation(self):
        """Test that concrete skill can be created"""
        class ConcreteSkill(BaseSkill):
            async def execute(self, query: str) -> str:
                return f"Result for: {query}"

        skill = ConcreteSkill()
        assert skill is not None

    @pytest.mark.asyncio
    async def test_concrete_skill_execution(self):
        """Test concrete skill execution"""
        class ConcreteSkill(BaseSkill):
            async def execute(self, query: str) -> str:
                return f"Result: {query}"

        skill = ConcreteSkill()
        result = await skill.execute("test query")
        assert result == "Result: test query"


class TestSearchSkill:
    """Test SearchSkill functionality"""

    @pytest.mark.asyncio
    async def test_search_skill_init(self):
        """Test SearchSkill initialization"""
        with patch('llm.ollama.OllamaClient'):
            skill = SearchSkill()
            assert skill.llm is not None

    @pytest.mark.asyncio
    async def test_search_skill_no_results(self):
        """Test search skill with no results"""
        with patch('llm.ollama.OllamaClient'):
            with patch.object(SearchSkill, '_wikipedia', return_value=None):
                with patch.object(SearchSkill, '_search_web', return_value=[]):
                    skill = SearchSkill()
                    result = await skill.execute("nonexistent query xyz")

                    assert result is None

    @pytest.mark.asyncio
    async def test_search_wikipedia_success(self):
        """Test Wikipedia search success"""
        mock_wiki_content = "Python is a programming language"

        with patch('llm.ollama.OllamaClient'):
            with patch.object(SearchSkill, '_wikipedia', return_value=mock_wiki_content):
                with patch.object(SearchSkill, '_summarize', return_value="Python summary"):
                    skill = SearchSkill()
                    result = await skill.execute("Python")

                    assert result is not None
                    assert "response" in result

    @pytest.mark.asyncio
    async def test_search_web_fallback(self):
        """Test web search fallback when Wikipedia fails"""
        with patch('llm.ollama.OllamaClient'):
            with patch.object(SearchSkill, '_wikipedia', return_value=None):
                with patch.object(SearchSkill, '_search_web', return_value=[{"title": "Result"}]):
                    with patch.object(SearchSkill, '_fetch_pages', return_value="Web content"):
                        with patch.object(SearchSkill, '_summarize', return_value="Summary"):
                            skill = SearchSkill()
                            result = await skill.execute("test query")

                            assert result is not None
                            assert "response" in result

    @pytest.mark.asyncio
    async def test_search_skill_error_handling(self):
        """Test search skill error handling"""
        with patch('llm.ollama.OllamaClient'):
            with patch.object(SearchSkill, '_wikipedia', side_effect=Exception("Wiki error")):
                with patch.object(SearchSkill, '_search_web', return_value=[]):
                    skill = SearchSkill()

                    result = await skill.execute("test")
                    assert result is None

    @pytest.mark.asyncio
    async def test_search_skill_uses_perplexica_backend_when_available(self):
        """Test that SearchSkill prefers a Perplexica-style backend if available"""
        with patch('llm.ollama.OllamaClient'):
            with patch.object(
                SearchSkill,
                '_search_with_perplexica',
                new_callable=AsyncMock,
                return_value={
                    'response': 'Perplexica summary',
                    'context': 'Perplexica context',
                    'source': 'perplexica',
                },
                create=True,
            ):
                skill = SearchSkill()
                result = await skill.execute('test query')

                assert result is not None
                assert result['source'] == 'perplexica'
                assert result['response'] == 'Perplexica summary'

    def test_search_extracts_text_from_html(self):
        """Test HTML text extraction"""
        html = "<html><body><p>Hello World</p></body></html>"

        with patch('llm.ollama.OllamaClient'):
            skill = SearchSkill()
            text = skill._extract_text(html)

            assert "Hello" in text
            assert "World" in text

    def test_search_removes_script_tags(self):
        """Test that script tags are removed"""
        html = "<html><script>alert('xss')</script><p>Content</p></html>"

        with patch('llm.ollama.OllamaClient'):
            skill = SearchSkill()
            text = skill._extract_text(html)

            assert "alert" not in text
            assert "Content" in text


class TestMusicSkill:
    """Test MusicSkill functionality"""

    @pytest.mark.asyncio
    async def test_music_skill_empty_query(self):
        """Test music skill with empty query"""
        from skills.music import MusicSkill
        skill = MusicSkill()
        result = await skill.execute("")

        assert result is not None
        assert "Nima musiqani" in result["response"]
        assert result["source"] == "music"

    @pytest.mark.asyncio
    async def test_music_skill_search_exception(self):
        """Test music skill handles search exception"""
        from skills.music import MusicSkill
        with patch.object(MusicSkill, '_search_youtube', side_effect=Exception("YouTube error")):
            skill = MusicSkill()
            result = await skill.execute("qo'y musiqa")

            assert result is not None
            assert "xatolik" in result["response"]
            assert result["source"] == "music"

    @pytest.mark.asyncio
    async def test_music_skill_no_results(self):
        """Test music skill with no results"""
        from skills.music import MusicSkill
        with patch.object(MusicSkill, '_search_youtube', return_value=[]):
            skill = MusicSkill()
            result = await skill.execute("qo'y musiqa")

            assert result is None

    @pytest.mark.asyncio
    async def test_music_skill_parse_query(self):
        """Test music query parsing removes keywords"""
        from skills.music import MusicSkill
        skill = MusicSkill()
        parsed = skill._parse_query("qo'y musiqa jazz")
        assert "qo'y" not in parsed
        assert "musiqa" not in parsed
        assert "jazz" in parsed

    @pytest.mark.asyncio
    async def test_music_skill_loader_discovers(self):
        """Test that SkillLoader finds MusicSkill"""
        from skills.music import MusicSkill
        loader = SkillLoader(package_name="skills")
        discovered = loader.discover()

        assert "music" in discovered
        assert issubclass(discovered["music"], BaseSkill)

    def test_format_duration(self):
        """Test duration formatting"""
        from skills.music import MusicSkill
        skill = MusicSkill()
        assert skill._format_duration(0) == ""
        assert skill._format_duration(45) == "0:45"
        assert skill._format_duration(125) == "2:05"
        assert skill._format_duration(3661) == "1:01:01"


class TestSkillErrorHandling:
    """Test error handling in skills"""

    @pytest.mark.asyncio
    async def test_skill_with_network_error(self):
        """Test skill handling network errors"""
        with patch('llm.ollama.OllamaClient'):
            with patch.object(SearchSkill, '_wikipedia', return_value=None):
                with patch.object(SearchSkill, '_search_web', side_effect=Exception("Network error")):
                    skill = SearchSkill()

                    result = await skill.execute("test")
                    assert result is None

    @pytest.mark.asyncio
    async def test_skill_with_timeout(self):
        """Test skill handling timeout"""
        with patch('llm.ollama.OllamaClient'):
            with patch.object(SearchSkill, '_wikipedia', side_effect=TimeoutError()):
                with patch.object(SearchSkill, '_search_web', return_value=[]):
                    skill = SearchSkill()

                    result = await skill.execute("test")
                    assert result is None


class TestSkillIntegration:
    """Test skill integration scenarios"""

    @pytest.mark.asyncio
    async def test_skill_loader_discovers_search_skill(self):
        """Test that SkillLoader finds SearchSkill"""
        loader = SkillLoader(package_name="skills")
        discovered = loader.discover()

        assert "search" in discovered
        assert issubclass(discovered["search"], BaseSkill)

    @pytest.mark.asyncio
    async def test_skill_loader_instantiate_search(self):
        """Test that SkillLoader can instantiate search skill"""
        with patch('llm.ollama.OllamaClient'):
            loader = SkillLoader(package_name="skills")
            instances = loader.instantiate_all()

            assert "search" in instances
            assert isinstance(instances["search"], SearchSkill)

    @pytest.mark.asyncio
    async def test_search_skill_cache_hit(self):
        """Test that search skill returns cached response when available"""
        with patch('llm.ollama.OllamaClient'):
            with patch('skills.search.get_cached_llm_response', new_callable=AsyncMock, return_value="Cached result"):
                skill = SearchSkill()
                result = await skill.execute("test query")

                assert result is not None
                assert result["response"] == "Cached result"
                assert result["source"] == "cache"
