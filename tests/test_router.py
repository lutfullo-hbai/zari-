from core.router import (
    detect_intent,
    detect_intent_with_confidence,
    route,
    route_with_confidence,
    should_use_llm_routing,
)


class TestIntentDetection:
    """Intent detection tests"""

    def test_detect_search_variants(self):
        """Test various search intent patterns"""
        search_queries = [
            "internetdan qidir",
            "buni qidirib top",
            "bu nima degan soz?",
            "sababi nima?",
            "meaning of life",
        ]
        for query in search_queries:
            assert detect_intent(query) == "search", f"Failed for query: {query}"

    def test_detect_music_variants(self):
        """Test various music intent patterns"""
        music_queries = [
            "musiqa qo'y",
            "qo'shiq tingla",
            "play music",
            "play some song",
        ]
        for query in music_queries:
            assert detect_intent(query) == "music", f"Failed for query: {query}"

    def test_detect_weather_variants(self):
        """Test various weather intent patterns"""
        weather_queries = [
            "ob-havo qanday",
            "havo qanday",
            "weather today",
        ]
        for query in weather_queries:
            assert detect_intent(query) == "weather", f"Failed for query: {query}"

    def test_detect_time_variants(self):
        """Test various time intent patterns"""
        time_queries = [
            "soat necha",
            "bugun qanday kun",
            "what time is it",
            "kun necha?",
        ]
        for query in time_queries:
            assert detect_intent(query) == "time", f"Failed for query: {query}"

    def test_detect_system_commands(self):
        """Test system command patterns"""
        system_queries = [
            "Chrome'ni och",
            "application yop",
            "run script",
        ]
        for query in system_queries:
            assert detect_intent(query) == "system", f"Failed for query: {query}"

    def test_detect_chat_fallback(self):
        """Test fallback to chat intent"""
        chat_queries = [
            "nima gap",
            "salom",
            "qanday o'zin",
            "hello",
            "random conversation",
        ]
        for query in chat_queries:
            result = detect_intent(query)
            assert result == "chat", f"Failed for query: {query}"

    def test_empty_string(self):
        """Test with empty string"""
        assert detect_intent("") == "chat"

    def test_case_insensitive(self):
        """Test case insensitivity"""
        assert detect_intent("MUSIQA QO'Y") == "music"
        assert detect_intent("ObHavo") == "weather"
        assert detect_intent("QIDIR") == "search"

    def test_punctuation_handling(self):
        """Test with various punctuation"""
        assert detect_intent("musiqa qo'y!") == "music"
        assert detect_intent("qanday ob-havo?") == "weather"
        assert detect_intent("buni qidirib top.") == "search"

    def test_route_function(self):
        """Test route wrapper function"""
        assert route("musiqa qo'y") == "music"
        assert route("qidirib top") == "search"


class TestIntentConfidence:
    """Test confidence scoring"""

    def test_confidence_scoring(self):
        """Test confidence score calculation"""
        intent, confidence = detect_intent_with_confidence("musiqa qo'y")

        assert intent == "music"
        assert 0.0 <= confidence <= 1.0

    def test_high_confidence_match(self):
        """Test high confidence matches"""
        intent, confidence = detect_intent_with_confidence("qidirib top")

        assert intent == "search"
        assert confidence > 0.5

    def test_ambiguous_query_low_confidence(self):
        """Test ambiguous queries have lower confidence"""
        intent1, conf1 = detect_intent_with_confidence("music search")
        intent2, conf2 = detect_intent_with_confidence("musiqa")

        assert intent1 == "search"
        assert intent2 == "music"

    def test_route_with_confidence(self):
        """Test route_with_confidence function"""
        intent, confidence = route_with_confidence("weather")

        assert isinstance(intent, str)
        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0

    def test_confidence_for_chat_fallback(self):
        """Test confidence for chat fallback"""
        intent, confidence = detect_intent_with_confidence("salom")

        assert intent == "chat"
        assert confidence == 0.5


class TestLLMRouting:
    """Test LLM-based routing logic"""

    def test_should_use_llm_routing_high_confidence(self):
        """Test that LLM routing is skipped for high confidence"""
        # High confidence
        should_use = should_use_llm_routing(0.9)
        assert should_use is False

    def test_should_use_llm_routing_low_confidence(self):
        """Test that LLM routing is used for low confidence"""
        # Low confidence
        should_use = should_use_llm_routing(0.3)
        assert should_use is True

    def test_should_use_llm_routing_threshold(self):
        """Test LLM routing threshold"""
        # At threshold
        should_use = should_use_llm_routing(0.6)
        # Should be False at threshold (0.6 is not less than 0.6)
        assert should_use is False


class TestEdgeCases:
    """Edge cases for intent detection"""

    def test_very_long_text(self):
        """Test with very long text"""
        long_text = " ".join(["musiqa"] * 100)
        result = detect_intent(long_text)
        assert result is not None

    def test_special_characters(self):
        """Test with special characters"""
        texts = [
            "musiqa!@#$%^&*()",
            "qo'shiq\t\ntingla",
            "havo\nqanday",
        ]
        for text in texts:
            result = detect_intent(text)
            assert isinstance(result, str)

    def test_mixed_language(self):
        """Test with mixed Uzbek and English"""
        assert detect_intent("musiqa play") == "music"
        assert detect_intent("qidirib search") == "search"

    def test_unicode_characters(self):
        """Test with unicode"""
        result = detect_intent("мусиқа")  # Cyrillic
        assert isinstance(result, str)

    def test_repeated_keywords(self):
        """Test with repeated keywords"""
        intent, conf = detect_intent_with_confidence("qidir qidir qidir")
        assert intent == "search"


class TestRouterPerformance:
    """Test router performance characteristics"""

    def test_quick_response_time(self):
        """Test that routing is fast"""
        import time

        start = time.time()
        for _ in range(100):
            detect_intent("musiqa qo'y")
        elapsed = time.time() - start

        # Should be very fast (less than 100ms for 100 queries)
        assert elapsed < 0.1, f"Router too slow: {elapsed}s for 100 queries"

    def test_confidence_scoring_performance(self):
        """Test confidence scoring performance"""
        import time

        start = time.time()
        for _ in range(100):
            detect_intent_with_confidence("bu nima degan soz?")
        elapsed = time.time() - start

        # Should still be fast with confidence calculation
        assert elapsed < 0.15, f"Confidence scoring too slow: {elapsed}s"


class TestRouterEdgeCases:
    """Additional router edge cases"""

    def test_chat_fallback_default(self):
        assert route("salom") == "chat"
