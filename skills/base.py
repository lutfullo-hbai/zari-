from abc import ABC, abstractmethod


class BaseSkill(ABC):
    @abstractmethod
    async def execute(self, query: str) -> str:
        ...
