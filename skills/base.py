import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Literal

log = logging.getLogger("zari")


class BaseSkill(ABC):
    priority: int = 0
    timeout: float = 30.0
    retries: int = 0
    requires_confirmation: bool = False
    confirmation_type: Literal["danger", "destructive", "info"] | None = None

    @abstractmethod
    async def execute(self, query: str) -> dict | None:
        ...

    async def execute_with_retry(self, query: str) -> dict | None:
        for attempt in range(max(self.retries, 0) + 1):
            try:
                return await asyncio.wait_for(
                    self.execute(query), timeout=self.timeout
                )
            except asyncio.TimeoutError:
                log.warning(
                    "%s timed out (attempt %d/%d)",
                    self.__class__.__name__,
                    attempt + 1,
                    self.retries + 1,
                )
            except Exception as e:
                log.warning(
                    "%s error (attempt %d/%d): %s",
                    self.__class__.__name__,
                    attempt + 1,
                    self.retries + 1,
                    e,
                )
        return None
