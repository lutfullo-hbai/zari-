import asyncio
import logging
import sys
from pathlib import Path

from core.config import settings
from skills.base import BaseSkill

log = logging.getLogger("zari")

N8N_PROJECT_DIR = Path(settings.n8n_workflows_dir).resolve() if settings.n8n_workflows_dir else Path("/dev/null")


def _import_workflow_db():
    if N8N_PROJECT_DIR.exists():
        sys.path.insert(0, str(N8N_PROJECT_DIR))
    from workflow_db import WorkflowDatabase
    return WorkflowDatabase


def _import_workflow_executor():
    if N8N_PROJECT_DIR.exists():
        sys.path.insert(0, str(N8N_PROJECT_DIR))
    try:
        from workflow_executor import WorkflowExecutor
        return WorkflowExecutor
    except ImportError:
        try:
            from executor import run_workflow
            return run_workflow
        except ImportError:
            return None


def _match_keywords(text: str, keywords: list[str]) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in keywords)


class N8nWorkflowSkill(BaseSkill):
    priority = 35
    timeout = 30.0

    def __init__(self):
        self._db = None
        self._executor = None
        self.db_path = str(N8N_PROJECT_DIR / "database" / "workflows.db")
        self.workflows_dir = str(N8N_PROJECT_DIR / "workflows")

    @property
    def db(self):
        if self._db is None:
            wdb = _import_workflow_db()
            self._db = wdb(db_path=self.db_path)
            self._db.workflows_dir = self.workflows_dir
        return self._db

    @property
    def executor(self):
        if self._executor is None:
            self._executor = _import_workflow_executor()
        return self._executor

    def _ensure_indexed(self):
        import os
        if not os.path.exists(self.db_path):
            log.info("N8N workflow bazasi topilmadi, indekslash boshlanmoqda...")
            stats = self.db.index_all_workflows()
            log.info("Indekslandi: %d processed, %d skipped, %d errors",
                     stats["processed"], stats["skipped"], stats["errors"])
            return stats["processed"] > 0 or stats["skipped"] > 0
        return True

    def _resolve_workflow_name(self, query: str) -> str | None:
        try:
            results, total = self.db.search_workflows(
                query=query, trigger_filter="all", complexity_filter="all", limit=1, offset=0,
            )
            if results:
                return results[0].get("filename") or results[0].get("name")
        except Exception:
            pass
        return None

    async def execute(self, query: str) -> dict | None:
        if not N8N_PROJECT_DIR.exists():
            return {
                "response": "N8N workflow shablonlari topilmadi.",
                "context": "",
                "source": "n8n_workflow",
            }

        try:
            has_data = await asyncio.to_thread(self._ensure_indexed)
            if not has_data:
                return {
                    "response": "Workflow bazasida hech qanday shablon topilmadi.",
                    "context": "",
                    "source": "n8n_workflow",
                }
        except Exception as e:
            log.error("N8N workflow indekslash xatosi: %s", e)
            return {
                "response": "Workflow bazasini yuklashda xatolik yuz berdi.",
                "context": "",
                "source": "n8n_workflow",
            }

        text = query.lower()

        if _match_keywords(text, ["stat", "necha", "qancha", "hisobot"]):
            return await self._handle_stats()

        if _match_keywords(text, ["kategori", "category", "turlar"]):
            return await self._handle_categories()

        if _match_keywords(text, ["run", "execute", "ishlat", "bajar", "start", "boshl", "trigger"]):
            return await self._handle_execute(query)

        return await self._handle_search(query)

    async def _handle_stats(self) -> dict:
        try:
            stats = await asyncio.to_thread(self.db.get_stats)
            response = (
                f"Jami {stats['total']} ta workflow shabloni mavjud. "
                f"Ulardan {stats['active']} ta faol. "
                f"Trigger turlari: {', '.join(f'{k} {v} ta' for k, v in stats['triggers'].items())}. "
                f"Murakkablik: {', '.join(f'{k} {v} ta' for k, v in stats['complexity'].items())}. "
                f"Jami {stats['total_nodes']} ta node, {stats['unique_integrations']} xil integratsiya."
            )
            return {"response": response, "context": str(stats), "source": "n8n_workflow"}
        except Exception as e:
            log.error("Stats xatosi: %s", e)
            return {"response": "Statistika olishda xatolik.", "context": "", "source": "n8n_workflow"}

    async def _handle_categories(self) -> dict:
        categories = await asyncio.to_thread(self.db.get_service_categories)
        lines = [f"  * {cat}: {', '.join(srvs)}" for cat, srvs in sorted(categories.items())]
        response = "Mavjud kategoriyalar:\n" + "\n".join(lines)
        return {"response": response, "context": str(list(categories.keys())), "source": "n8n_workflow"}

    async def _handle_execute(self, query: str) -> dict:
        workflow_name = await asyncio.to_thread(self._resolve_workflow_name, query)

        if not workflow_name:
            return await self._handle_search(query)

        if self.executor is None:
            return {
                "response": f"'{workflow_name}' workflow topildi, lekin workflow muharriki mavjud emas.",
                "context": workflow_name,
                "source": "n8n_workflow",
            }

        try:
            if callable(self.executor):
                if asyncio.iscoroutinefunction(self.executor):
                    result = await self.executor(workflow_name)
                else:
                    result = await asyncio.to_thread(self.executor, workflow_name)

            msg = f"'{workflow_name}' workflow bajarildi."
            if result:
                msg += f" Natija: {result}"
            return {"response": msg, "context": str(result), "source": "n8n_workflow"}

        except Exception as e:
            log.error("Workflow bajarish xatosi: %s", e)
            return {
                "response": f"'{workflow_name}' workflow bajarishda xatolik: {e}",
                "context": "",
                "source": "n8n_workflow",
            }

    async def _handle_search(self, query: str) -> dict | None:
        trigger = "all"
        complexity = "all"
        text = query.lower()

        if _match_keywords(text, ["webhook", "web", "api"]):
            trigger = "Webhook"
        elif _match_keywords(text, ["scheduled", "schedule", "vaqt", "rejala"]):
            trigger = "Scheduled"
        elif _match_keywords(text, ["manual"]):
            trigger = "Manual"

        if _match_keywords(text, ["simple", "low", "kichik", "oson"]):
            complexity = "low"
        elif _match_keywords(text, ["medium", "o'rta"]):
            complexity = "medium"
        elif _match_keywords(text, ["complex", "high", "murakkab", "katta"]):
            complexity = "high"

        try:
            results, total = await asyncio.to_thread(
                self.db.search_workflows,
                query=query,
                trigger_filter=trigger,
                complexity_filter=complexity,
                limit=5,
                offset=0,
            )
        except Exception as e:
            log.error("Workflow qidiruv xatosi: %s", e)
            return None

        if not results:
            return None

        lines = []
        for w in results:
            integrations = ", ".join(w.get("integrations", [])[:3]) or "none"
            lines.append(
                f"  * {w['name']} - {w['trigger_type']}, {w['node_count']} node, "
                f"{integrations}"
            )

        response = (
            f"{total} ta workflow topildi. Eng moslari:\n" + "\n".join(lines[:5])
        )
        return {
            "response": response,
            "context": str([r["filename"] for r in results[:5]]),
            "source": "n8n_workflow",
        }
