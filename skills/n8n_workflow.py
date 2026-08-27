"""
n8n Workflow skill — to'liq n8n integratsiya.

LLM = miya (qaror qiladi), n8n = qo'llar (bajaradi).

Qo'llab-quvvatlanayotgan buyruqlar:
  - "n8n workflow top <nom>" — templates dan qidirish
  - "n8n workflowlar" — n8n serverdagi barcha workflow'lar
  - "n8n stats" — statistika
  - "n8n kategoriyalar" — kategoriyalar
  - "n8n ishga tushir <nom>" — workflow ni faollashtirish
  - "n8n to'xtat <nom>" — workflow ni o'chirish
  - "n8n webhook <path>" — webhook orqali trigger
  - "n8n tarix <nom>" — execution tarixi
  - "n8n diagram <filename>" — Mermaid diagram
  - "n8n yarat" — yangi workflow yaratish (web UI)
"""

import logging

from llm.n8n_client import N8nClient
from llm.n8n_templates_client import N8nTemplatesClient
from skills.base import BaseSkill

log = logging.getLogger("zari")


def _match_keywords(text: str, keywords: list[str]) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in keywords)


class N8nWorkflowSkill(BaseSkill):
    """n8n bilan to'liq integratsiya — LLM qaror qiladi, n8n bajaradi."""

    priority = 35
    timeout = 30.0
    requires_confirmation = True
    confirmation_type = "danger"

    def __init__(self) -> None:
        self._n8n = N8nClient()
        self._templates = N8nTemplatesClient()

    async def execute(self, query: str) -> dict | None:
        text = query.lower()

        if _match_keywords(text, ["stat", "necha", "qancha", "hisobot"]):
            return await self._handle_stats()

        if _match_keywords(text, ["kategori", "category", "turlar"]):
            return await self._handle_categories()

        if _match_keywords(text, ["webhook", "trigger", "yoruq"]):
            return await self._handle_trigger(query)

        if _match_keywords(text, ["tarix", "history", "execution", "natija"]):
            return await self._handle_executions(query)

        if _match_keywords(text, ["to'xtat", "o'chir", "deactivate", "stop"]):
            return await self._handle_deactivate(query)

        if _match_keywords(
            text, ["run", "execute", "ishlat", "bajar", "start", "boshl", "ishga tushir", "faollashtir"]
        ):
            return await self._handle_activate(query)

        if _match_keywords(text, ["list", "ro'yxat", "workflowlar", "barchasi", "mavjud"]):
            return await self._handle_list()

        if _match_keywords(text, ["diagram", "tasvir", "rasm"]):
            return await self._handle_diagram(query)

        if _match_keywords(text, ["yarat", "create", "qo'sh"]):
            return await self._handle_create(query)

        return await self._handle_search(query)

    async def _handle_stats(self) -> dict:
        stats = await self._templates.get_stats()
        if stats is None:
            return {
                "response": "n8n workflow templates server ishlamayapti. Docker compose up bilan ishga tushiring.",
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
        data = await self._templates.get_categories()
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

    async def _handle_search(self, query: str) -> dict | None:
        result = await self._templates.search_workflows(query=query, per_page=5)
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

    async def _handle_list(self) -> dict:
        if not await self._n8n.health_check():
            return {
                "response": "n8n server ishlamayapti. Docker compose up bilan ishga tushiring.",
                "context": "",
                "source": "n8n_workflow",
            }

        workflows = await self._n8n.list_workflows(limit=20)
        if not workflows:
            return {
                "response": "n8n serverda workflow topilmadi.",
                "context": "",
                "source": "n8n_workflow",
            }

        lines = []
        for w in workflows:
            status = "faol" if w.get("active") else "nofaol"
            name = w.get("name", "Noma'lum")
            lines.append(f"  * {name} [{status}] (ID: {w.get('id', '?')})")

        response = f"n8n serverdagi workflow'lar ({len(workflows)} ta):\n" + "\n".join(lines)
        return {
            "response": response,
            "context": str([w.get("id") for w in workflows]),
            "source": "n8n_workflow",
        }

    async def _handle_activate(self, query: str) -> dict:
        if not await self._n8n.health_check():
            return {
                "response": "n8n server ishlamayapti.",
                "context": "",
                "source": "n8n_workflow",
            }

        workflow_id = await self._find_workflow_id(query)
        if not workflow_id:
            return {
                "response": "Workflow topilmadi. Nomini aniqroq ayting.",
                "context": "",
                "source": "n8n_workflow",
            }

        success = await self._n8n.activate_workflow(workflow_id)
        if success:
            return {
                "response": f"Workflow {workflow_id} faollashtirildi.",
                "context": workflow_id,
                "source": "n8n_workflow",
            }
        return {
            "response": f"Workflow {workflow_id} ni faollashtirib bo'lmadi.",
            "context": "",
            "source": "n8n_workflow",
        }

    async def _handle_deactivate(self, query: str) -> dict:
        if not await self._n8n.health_check():
            return {
                "response": "n8n server ishlamayapti.",
                "context": "",
                "source": "n8n_workflow",
            }

        workflow_id = await self._find_workflow_id(query)
        if not workflow_id:
            return {
                "response": "Workflow topilmadi. Nomini aniqroq ayting.",
                "context": "",
                "source": "n8n_workflow",
            }

        success = await self._n8n.deactivate_workflow(workflow_id)
        if success:
            return {
                "response": f"Workflow {workflow_id} o'chirildi.",
                "context": workflow_id,
                "source": "n8n_workflow",
            }
        return {
            "response": f"Workflow {workflow_id} ni o'chirib bo'lmadi.",
            "context": "",
            "source": "n8n_workflow",
        }

    async def _handle_trigger(self, query: str) -> dict:
        if not await self._n8n.health_check():
            return {
                "response": "n8n server ishlamayapti.",
                "context": "",
                "source": "n8n_workflow",
            }

        webhook_path = self._extract_webhook_path(query)
        if not webhook_path:
            return {
                "response": "Webhook path ko'rsatilmadi. Masalan: 'n8n webhook my-webhook'",
                "context": "",
                "source": "n8n_workflow",
            }

        result = await self._n8n.trigger_webhook(webhook_path)
        if result is not None:
            return {
                "response": f"Webhook '{webhook_path}' ishga tushirildi. Natija: {str(result)[:200]}",
                "context": str(result),
                "source": "n8n_workflow",
            }
        return {
            "response": f"Webhook '{webhook_path}' ishga tushirilmadi.",
            "context": "",
            "source": "n8n_workflow",
        }

    async def _handle_executions(self, query: str) -> dict:
        if not await self._n8n.health_check():
            return {
                "response": "n8n server ishlamayapti.",
                "context": "",
                "source": "n8n_workflow",
            }

        workflow_id = await self._find_workflow_id(query)
        if not workflow_id:
            return {
                "response": "Workflow topilmadi. Nomini aniqroq ayting.",
                "context": "",
                "source": "n8n_workflow",
            }

        executions = await self._n8n.get_executions(workflow_id, limit=5)
        if not executions:
            return {
                "response": f"Workflow {workflow_id} uchun execution topilmadi.",
                "context": "",
                "source": "n8n_workflow",
            }

        lines = []
        for ex in executions:
            status = ex.get("status", "noma'lum")
            created = ex.get("createdAt", "?")
            lines.append(f"  * {status} — {created}")

        response = f"Workflow {workflow_id} tarixi ({len(executions)} ta):\n" + "\n".join(lines)
        return {
            "response": response,
            "context": str(executions),
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
            result = await self._templates.search_workflows(query=query, per_page=1)
            if result and result.get("workflows"):
                filename = result["workflows"][0]["filename"]

        if not filename:
            return {
                "response": "Workflow faylini topa olmadim.",
                "context": "",
                "source": "n8n_workflow",
            }

        diagram = await self._templates.get_workflow_diagram(filename)
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
            "response": "Workflow yaratish uchun n8n veb-interfeysini ishating: http://localhost:5678",
            "context": "",
            "source": "n8n_workflow",
        }

    async def _find_workflow_id(self, query: str) -> str | None:
        """So'rov bo'yicha workflow ID ni topadi."""
        name = self._extract_workflow_name(query)
        if not name:
            return None

        workflows = await self._n8n.search_workflows(name)
        if workflows:
            return str(workflows[0].get("id", ""))

        all_wf = await self._n8n.list_workflows(limit=50)
        name_lower = name.lower()
        for w in all_wf:
            if name_lower in w.get("name", "").lower():
                return str(w.get("id", ""))

        return None

    def _extract_workflow_name(self, query: str) -> str:
        text = query.lower()
        for word in [
            "n8n",
            "workflow",
            "ishga tushir",
            "bajar",
            "run",
            "execute",
            "start",
            "trigger",
            "to'xtat",
            "o'chir",
            "deactivate",
            "stop",
            "tarix",
            "history",
            "execution",
            "webhook",
            "faollashtir",
        ]:
            text = text.replace(word, "")
        return text.strip()

    def _extract_webhook_path(self, query: str) -> str:
        text = query.lower()
        for word in ["n8n", "webhook", "trigger", "yoruq", "ishga tushir"]:
            text = text.replace(word, "")
        return text.strip()
