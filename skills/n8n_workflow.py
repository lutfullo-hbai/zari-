"""
n8n Workflow skill — mavjud n8n-workflow-templates API serveri bilan integratsiya.

Foydalanuvchi so'rovlari:
  - "n8n workflow top" / "n8n workflowlar" — qidiruv
  - "n8n stats" — statistika
  - "n8n kategoriyalar" — kategoriyalar
  - "n8n workflow ishga tushir <nom>" — n8n serverda ishga tushirish
  - "n8n diagram <filename>" — Mermaid diagram
"""

import logging

from llm.n8n_templates_client import N8nTemplatesClient
from skills.base import BaseSkill

log = logging.getLogger("zari")


def _match_keywords(text: str, keywords: list[str]) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in keywords)


class N8nWorkflowSkill(BaseSkill):
    priority = 35
    timeout = 30.0
    requires_confirmation = True

    def __init__(self):
        self._client = N8nTemplatesClient()

    async def execute(self, query: str) -> dict | None:
        text = query.lower()

        if _match_keywords(text, ["stat", "necha", "qancha", "hisobot"]):
            return await self._handle_stats()

        if _match_keywords(text, ["kategori", "category", "turlar"]):
            return await self._handle_categories()

        if _match_keywords(text, ["run", "execute", "ishlat", "bajar", "start", "boshl", "trigger", "ishga tushir"]):
            return await self._handle_execute(query)

        if _match_keywords(text, ["diagram", "tasvir", "rasm"]):
            return await self._handle_diagram(query)

        if _match_keywords(text, ["yarat", "create", "qo'sh"]):
            return await self._handle_create(query)

        return await self._handle_search(query)

    async def _handle_stats(self) -> dict:
        stats = await self._client.get_stats()
        if stats is None:
            return {
                "response": (
                    "n8n workflow templates server ishlamayapti. Serverni ishga tushiring: python api_server.py"
                ),
                "context": "",
                "source": "n8n_workflow",
            }

        response = (
            f"n8n workflow bazasi: {stats['total']} ta shablon. "
            f"Faol: {stats['active']}, Nofaol: {stats['inactive']}. "
            f"Trigger turlari: {', '.join(f'{k} {v}' for k, v in stats['triggers'].items())}. "
            f"Murakkablik: {', '.join(f'{k} {v}' for k, v in stats['complexity'].items())}. "
            f"Integratsiyalar soni: {stats['unique_integrations']}."
        )
        return {"response": response, "context": str(stats), "source": "n8n_workflow"}

    async def _handle_categories(self) -> dict:
        data = await self._client.get_categories()
        if data is None:
            return {
                "response": "n8n workflow templates server ishlamayapti.",
                "context": "",
                "source": "n8n_workflow",
            }

        categories = data.get("categories", {})
        if not categories:
            return {
                "response": "Kategoriyalar topilmadi.",
                "context": "",
                "source": "n8n_workflow",
            }

        lines = [f"  * {cat}: {', '.join(srvs)}" for cat, srvs in sorted(categories.items())]
        response = "n8n workflow kategoriyalari:\n" + "\n".join(lines)
        return {"response": response, "context": str(list(categories.keys())), "source": "n8n_workflow"}

    async def _handle_execute(self, query: str) -> dict:
        workflow_name = self._extract_workflow_name(query)
        if not workflow_name:
            return {
                "response": "Qaysi workflow ni ishga tushirish kerak? Nomini ayting.",
                "context": "",
                "source": "n8n_workflow",
            }

        result = await self._client.search_workflows(query=workflow_name, per_page=1)
        if result is None or not result.get("workflows"):
            return {
                "response": f"'{workflow_name}' nomli workflow topilmadi.",
                "context": "",
                "source": "n8n_workflow",
            }

        wf = result["workflows"][0]
        filename = wf["filename"]
        name = wf["name"]

        return {
            "response": (
                f"'{name}' workflow topildi (fayl: {filename}). "
                f"n8n veb-interfeysidan ishga tushiring: http://localhost:5678/workflow/{filename}"
            ),
            "context": filename,
            "source": "n8n_workflow",
        }

    async def _handle_diagram(self, query: str) -> dict:
        parts = query.lower().split()
        filename = None
        for part in parts:
            if part.endswith(".json"):
                filename = part
                break

        if not filename:
            result = await self._client.search_workflows(query=query, per_page=1)
            if result and result.get("workflows"):
                filename = result["workflows"][0]["filename"]

        if not filename:
            return {
                "response": "Workflow faylini topa olmadim.",
                "context": "",
                "source": "n8n_workflow",
            }

        diagram = await self._client.get_workflow_diagram(filename)
        if diagram is None:
            return {
                "response": f"'{filename}' uchun diagram olishda xatolik.",
                "context": "",
                "source": "n8n_workflow",
            }

        return {
            "response": f"Workflow diagram ({filename}):\n```\n{diagram}\n```",
            "context": filename,
            "source": "n8n_workflow",
        }

    async def _handle_create(self, query: str) -> dict:
        return {
            "response": "Workflow yaratish uchun n8n veb-interfeysini ishlating: http://localhost:5678",
            "context": "",
            "source": "n8n_workflow",
        }

    async def _handle_search(self, query: str) -> dict | None:
        result = await self._client.search_workflows(query=query, per_page=5)
        if result is None:
            return {
                "response": "n8n workflow templates server ishlamayapti.",
                "context": "",
                "source": "n8n_workflow",
            }

        workflows = result.get("workflows", [])
        total = result.get("total", 0)
        if not workflows:
            return None

        lines = []
        for w in workflows:
            integrations = ", ".join(w.get("integrations", [])[:3]) or "yo'q"
            status = "faol" if w.get("active") else "nofaol"
            lines.append(f"  * {w['name']} — {w['trigger_type']}, {w['node_count']} node, {integrations} [{status}]")

        response = (
            f"{total} ta workflow topildi (sahifa {result.get('page', 1)}/{result.get('pages', 1)}):\n"
            + "\n".join(lines)
        )
        return {
            "response": response,
            "context": str([w["filename"] for w in workflows]),
            "source": "n8n_workflow",
        }

    def _extract_workflow_name(self, query: str) -> str:
        text = query.lower()
        for word in ["workflow", "ishga tushir", "bajar", "run", "execute", "start", "trigger"]:
            text = text.replace(word, "")
        return text.strip()
