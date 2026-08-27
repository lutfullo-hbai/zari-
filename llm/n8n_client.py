"""
n8n REST API client.

n8n server bilan HTTP orqali muloqot qiladi.
Barcha so'rovlar httpx orqali yuboriladi.
"""

import logging

import httpx

from core.config import settings

log = logging.getLogger("zari")


class N8nClient:
    """n8n REST API client — httpx bilan."""

    def __init__(self, base_url: str = "", api_key: str = ""):
        self.base_url = (base_url or settings.n8n_url).rstrip("/")
        self.api_key = api_key or settings.n8n_api_key
        self._api_base = f"{self.base_url}/api/v1"
        self._timeout = 15.0

    def _headers(self) -> dict[str, str]:
        h = {"Accept": "application/json"}
        if self.api_key:
            h["X-N8N-API-KEY"] = self.api_key
        return h

    def _is_available(self) -> bool:
        return bool(self.base_url)

    async def health_check(self) -> bool:
        """n8n server ishlashini tekshiradi."""
        if not self._is_available():
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{self.base_url}/healthz",
                    headers=self._headers(),
                )
                return resp.status_code == 200
        except Exception:
            return False

    async def list_workflows(self, limit: int = 50, offset: int = 0) -> list[dict]:
        """Barcha workflow larni ro'yxatini oladi."""
        if not self._is_available():
            return []
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(
                    f"{self._api_base}/workflows",
                    headers=self._headers(),
                    params={"limit": limit, "offset": offset},
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("data", [])
        except Exception as e:
            log.error("n8n workflows ro'yxatini olishda xato: %s", e)
            return []

    async def get_workflow(self, workflow_id: str) -> dict | None:
        """Bitta workflow ni oladi."""
        if not self._is_available():
            return None
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(
                    f"{self._api_base}/workflows/{workflow_id}",
                    headers=self._headers(),
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            log.error("n8n workflow olishda xato: %s", e)
            return None

    async def get_active_workflows(self) -> list[dict]:
        """Faol workflow larni oladi."""
        all_wf = await self.list_workflows(limit=100)
        return [w for w in all_wf if w.get("active")]

    async def activate_workflow(self, workflow_id: str) -> bool:
        """Workflow ni faollashtiradi."""
        if not self._is_available():
            return False
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._api_base}/workflows/{workflow_id}/activate",
                    headers=self._headers(),
                )
                resp.raise_for_status()
                log.info("n8n workflow %s faollashtirildi", workflow_id)
                return True
        except Exception as e:
            log.error("n8n workflow faollashtirishda xato: %s", e)
            return False

    async def deactivate_workflow(self, workflow_id: str) -> bool:
        """Workflow ni o'chiradi."""
        if not self._is_available():
            return False
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._api_base}/workflows/{workflow_id}/deactivate",
                    headers=self._headers(),
                )
                resp.raise_for_status()
                log.info("n8n workflow %s o'chirildi", workflow_id)
                return True
        except Exception as e:
            log.error("n8n workflow o'chirishda xato: %s", e)
            return False

    async def create_workflow(self, workflow_data: dict) -> dict | None:
        """Yangi workflow yaratadi."""
        if not self._is_available():
            return None
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._api_base}/workflows",
                    headers=self._headers(),
                    json=workflow_data,
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            log.error("n8n workflow yaratishda xato: %s", e)
            return None

    async def trigger_webhook(self, webhook_path: str, data: dict | None = None, method: str = "POST") -> dict | None:
        """Webhook orqali workflow ni ishga tushiradi."""
        url = f"{self.base_url}/webhook/{webhook_path}"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                if method.upper() == "GET":
                    resp = await client.get(url, headers=self._headers())
                else:
                    resp = await client.post(url, headers=self._headers(), json=data or {})
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            log.error("n8n webhook xatosi (%s): %s", webhook_path, e)
            return None

    async def get_executions(self, workflow_id: str, limit: int = 10) -> list[dict]:
        """Workflow execution tarixini oladi."""
        if not self._is_available():
            return []
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(
                    f"{self._api_base}/executions",
                    headers=self._headers(),
                    params={"workflowId": workflow_id, "limit": limit},
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("data", [])
        except Exception as e:
            log.error("n8n execution tarixini olishda xato: %s", e)
            return []

    async def search_workflows(self, query: str) -> list[dict]:
        """Workflow nomi bo'yicha qidiradi."""
        all_wf = await self.list_workflows(limit=100)
        if not query:
            return all_wf
        q = query.lower()
        return [w for w in all_wf if q in (w.get("name", "").lower()) or q in (w.get("description", "").lower())]
