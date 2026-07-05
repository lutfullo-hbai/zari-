# Migration Guide — Using New Async APIs

## Quick Reference

### For LLM Calls

**Old way (still works):**
```python
from llm.ollama import OllamaClient

client = OllamaClient()

# Blocking call (blocks event loop!)
response = client.chat([{"role": "user", "content": "Hello"}])
```

**New way (recommended):**
```python
from llm.ollama import OllamaClient
import asyncio

client = OllamaClient()

# Async call with timeout protection
async def main():
    response = await client.chat_async(
        [{"role": "user", "content": "Hello"}],
        timeout=60  # 60 second timeout
    )
    print(response)

asyncio.run(main())
```

### For Translation

**Old way (sync):**
```python
from llm.translator import Translator

translator = Translator()
english = translator.uz_to_en("Salom")  # Blocks!
```

**New way (async):**
```python
from llm.translator import Translator
import asyncio

translator = Translator()

async def main():
    english = await translator.uz_to_en_async("Salom")
    print(english)

asyncio.run(main())
```

### For Intent Routing

**Old way (simple):**
```python
from core.router import detect_intent

intent = detect_intent("musiqa qo'y")
# Returns: "music"
```

**New way (with confidence):**
```python
from core.router import detect_intent_with_confidence

intent, confidence = detect_intent_with_confidence("musiqa qo'y")
# Returns: ("music", 0.85)

# Use confidence to decide if LLM should disambiguate
from core.router import should_use_llm_routing

if should_use_llm_routing(confidence):
    # Query too ambiguous, use LLM for routing
    pass
```

### For Logging

**Old way (basic):**
```python
import logging

log = logging.getLogger("zari")
log.info("User said: %s", text)
```

**New way (structured):**
```python
from core.logging import get_logger

log = get_logger("zari")

# Simple logging still works
log.info("User said: %s", text)

# New: Structured logging with fields
log.info_event(
    "User query processed",
    user_id="user123",
    session_id="sess456",
    intent="search",
    duration_ms=42
)
```

---

## Migration Checklist

### If you're writing new code:
- [ ] Use `chat_async()` for LLM calls (not `chat()`)
- [ ] Use `uz_to_en_async()` for translations (not `uz_to_en()`)
- [ ] Use confidence-based routing (`detect_intent_with_confidence()`)
- [ ] Wrap calls in try-catch with timeout handling
- [ ] Use structured logging for important events

### If you're updating existing code:
- [ ] Replace `await asyncio.to_thread(llm.chat, ...)` with `await llm.chat_async(...)`
- [ ] Replace `await asyncio.to_thread(translator.uz_to_en, ...)` with `await translator.uz_to_en_async(...)`
- [ ] Add error handlers for `asyncio.TimeoutError`
- [ ] Add fallback responses for all error cases

### If you're running tests:
```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_llm.py -v

# Run with coverage
pytest --cov=core --cov=llm tests/
```

---

## Common Patterns

### Pattern 1: Safe LLM Call with Timeout
```python
async def safe_llm_call(messages, timeout=60):
    """Call LLM with error handling"""
    try:
        response = await llm.chat_async(messages, timeout=timeout)
        return response
    except asyncio.TimeoutError:
        log.error("LLM timeout after %d seconds", timeout)
        return "I'm taking too long. Please try again."
    except Exception as e:
        log.error("LLM error: %s", e)
        return "I encountered an error. Please try again."
```

### Pattern 2: Fallback Chain
```python
async def get_response(query):
    """Try multiple approaches in order"""
    intent, confidence = detect_intent_with_confidence(query)
    
    # Try skill if high confidence
    if confidence > 0.7:
        if intent == "search":
            try:
                result = await search_skill.execute(query)
                if result:
                    return result["response"]
            except Exception as e:
                log.warning("Search failed: %s", e)
    
    # Fall back to LLM
    try:
        response = await safe_llm_call([{"role": "user", "content": query}])
        return response
    except Exception as e:
        log.error("LLM fallback failed: %s", e)
        return "Unable to respond at this time."
```

### Pattern 3: Structured Event Logging
```python
async def process_query(query, session_id, user_id):
    """Process query with structured logging"""
    start_time = time.time()
    
    try:
        intent, confidence = detect_intent_with_confidence(query)
        
        log.info_event(
            "Query processed",
            user_id=user_id,
            session_id=session_id,
            intent=intent,
            confidence=confidence,
            duration_ms=int((time.time() - start_time) * 1000)
        )
        
        return intent
    except Exception as e:
        log.error_event(
            "Query processing failed",
            user_id=user_id,
            session_id=session_id,
            error=str(e),
            duration_ms=int((time.time() - start_time) * 1000)
        )
        raise
```

### Pattern 4: Concurrent Operations
```python
async def parallel_operations():
    """Run multiple async operations concurrently"""
    results = await asyncio.gather(
        llm.chat_async(messages1),
        translator.uz_to_en_async(text),
        search_skill.execute(query),
        return_exceptions=True  # Don't crash if one fails
    )
    
    # Handle results (may contain exceptions)
    for result in results:
        if isinstance(result, Exception):
            log.error("Operation failed: %s", result)
        else:
            process_result(result)
```

---

## Error Handling Examples

### TimeoutError
```python
try:
    response = await llm.chat_async(messages, timeout=60)
except asyncio.TimeoutError:
    log.error("LLM took more than 60 seconds")
    response = "Request timed out. Please try again."
```

### Connection Error
```python
try:
    response = await llm.chat_async(messages)
except ConnectionError:
    log.error("Cannot connect to Ollama")
    response = "Unable to reach the LLM. Is Ollama running?"
```

### Translation Error
```python
text_en = await translator.uz_to_en_async("Salom")
# Returns original text if translation fails
if text_en == "Salom":
    log.warning("Translation may have failed")
```

---

## Performance Tips

1. **Batch operations:** Use `asyncio.gather()` for parallel requests
2. **Cache results:** Don't re-translate same text repeatedly
3. **Set appropriate timeouts:** 60s for LLM, 10s for translation
4. **Profile your code:** Use `time.time()` to measure operations
5. **Monitor logs:** Watch for repeated timeout errors (tune timeout)

---

## Troubleshooting

### "asyncio.TimeoutError: Timed out"
- **Cause:** LLM taking too long
- **Solution:** Increase timeout or check if Ollama is overloaded
- **Code:** `await llm.chat_async(messages, timeout=120)`

### "Translation timeout"
- **Cause:** LLM busy or network slow
- **Solution:** Falls back to original text automatically
- **Note:** No action needed, translation fallback is automatic

### "Empty response"
- **Cause:** LLM returned empty string
- **Solution:** Check LLM model and prompt
- **Code:** Add validation `if not response.strip(): ...`

### Tests failing
- **Solution:** Run `pytest tests/ -v` to see detailed errors
- **Check:** Make sure PostgreSQL and Redis are running
- **Note:** Most tests mock external services

---

## Best Practices

✅ **DO:**
- Use async methods in async context
- Add timeout to all LLM calls
- Catch and log all exceptions
- Provide fallback responses
- Use structured logging

❌ **DON'T:**
- Call sync LLM methods in event loop
- Ignore timeouts
- Crash on errors
- Return None without logging
- Use print() for errors (use logger)

---

## Summary Table

| Operation | Old | New | Benefit |
|-----------|-----|-----|---------|
| LLM chat | `llm.chat()` | `await llm.chat_async()` | Non-blocking + timeout |
| Translation | `translator.uz_to_en()` | `await translator.uz_to_en_async()` | Non-blocking + fallback |
| Routing | `detect_intent()` | `detect_intent_with_confidence()` | Confidence score |
| Logging | `log.info()` | `log.info_event()` | Structured fields |
| Errors | None | Try-catch + fallback | Reliability |

---

**Questions?** Check the test files in `tests/` for examples!
