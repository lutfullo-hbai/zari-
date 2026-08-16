"""
n8n Workflow Templates API client.

Existing n8n-workflow-templates loyihasining FastAPI serveriga ulanadi.
Port 8000 da ishlaydi, 2053+ ta workflow ni qidirish imkonini beradi.
"""

import logging
from typing import Any

import httpx

from core.config import settings

log = logging.getLogger("zari")


class N8nTemplatesClient:
    """n8n workflow templates API client."""

    def __init__(self, base_url: str = ""):
        self.base_url = (base_url or settings.n8n_templates_api_url).rstrip("/")
        self._timeout = 15.0

    def _is_available(self) -> bool:
        return bool(self.base_url)

    async def health_check(self) -> bool:
        """API server ishlashini tekshiradi."""
        if not self._is_available():
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/health")
                return resp.status_code == 200
        except Exception:
            return False

    async def get_stats(self) -> dict | None:
        """Statistika oladi."""
        if not self._is_available():
            return None
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(f"{self.base_url}/api/stats")
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            log.error("n8n templates stats olishda xato: %s", e)
            return None

    async def search_workflows(
        self,
        query: str = "",
        trigger: str = "all",
        complexity: str = "all",
        active_only: bool = False,
        page: int = 1,
        per_page: int = 20,
    ) -> dict | None:
        """Workflowlarni qidiradi."""
        if not self._is_available():
            return None
        try:
            params = {
                "q": query,
                "trigger": trigger,
                "complexity": complexity,
                "active_only": active_only,
                "page": page,
                "per_page": per_page,
            }
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(
                    f"{self.base_url}/api/workflows", params=params
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            log.error("n8n templates qidiruv xatosi: %s", e)
            return None

    async def get_workflow_detail(self, filename: str) -> dict | None:
        """Workflow tafsilotlarini oladi (metadata + raw JSON)."""
        if not self._is_available():
            return None
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(
                    f"{self.base_url}/api/workflows/{filename}"
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            log.error("n8n templates workflow olishda xato: %s", e)
            return None

    async def get_categories(self) -> dict | None:
        """Kategoriyalarni oladi."""
        if not self._is_available():
            return None
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(f"{self.base_url}/api/categories")
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            log.error("n8n templates kategoriyalar olishda xato: %s", e)
            return None

    async def get_workflow_diagram(self, filename: str) -> str | None:
        """Mermaid diagram oladi."""
        if not self._is_available():
            return None
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(
                    f"{self.base_url}/api/workflows/{filename}/diagram"
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("diagram")
        except Exception as e:
            log.error("n8n templates diagram olishda xato: %s", e)
            return None

    async def search_by_category(
        self, category: str, page: int = 1, per_page: int = 20
    ) -> dict | None:
        """Kategoriya bo'yicha qidiradi."""
        if not self._is_available():
            return None
        try:
            params = {"page": page, "per_page": per_page}
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(
                    f"{self.base_url}/api/workflows/category/{category}",
                    params=params,
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            log.error("n8n templates kategoriya qidiruv xatosi: %s", e)
            return None
