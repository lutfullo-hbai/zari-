import time
import logging
from collections import defaultdict

from core.config import settings


log = logging.getLogger("zari")


class RateLimiter:
    def __init__(self, max_calls: int = 0, window: int = 60):
        self.max_calls = max_calls or settings.rate_limit_max_calls
        self.window = window or settings.rate_limit_window
        self._buckets: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        window_start = now - self.window
        self._buckets[key] = [t for t in self._buckets[key] if t > window_start]

        if len(self._buckets[key]) >= self.max_calls:
            log.warning("Rate limit exceeded for %s", key)
            return False

        self._buckets[key].append(now)
        return True

    def remaining(self, key: str) -> int:
        now = time.time()
        window_start = now - self.window
        self._buckets[key] = [t for t in self._buckets[key] if t > window_start]
        return max(0, self.max_calls - len(self._buckets[key]))


rate_limiter = RateLimiter()
