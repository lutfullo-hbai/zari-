"""
n8n workflow import pipeline — templates bazasidan n8n serverga import.

n8n-workflow-templates (port 8000) dagi workflow'larni
n8n serverga (port 5678) import qiladi.
"""

import json
import logging

from llm.n8n_client import N8nClient
from llm.n8n_templates_client import N8nTemplatesClient

log = logging.getLogger("zari")


class N8nImportPipeline:
    """Templates → n8n import pipeline."""

    def __init__(self) -> None:
        self._n8n = N8nClient()
        self._templates = N8nTemplatesClient()

    async def import_workflow(self, filename: str) -> dict:
        """Bitta workflow ni templates dan n8n serverga import qiladi."""
        if not await self._n8n.health_check():
            return {"success": False, "error": "n8n server ishlamayapti"}

        if not await self._templates.health_check():
            return {"success": False, "error": "templates server ishlamayapti"}

        detail = await self._templates.get_workflow_detail(filename)
        if detail is None:
            return {"success": False, "error": f"'{filename}' topilmadi"}

        raw_json = detail.get("raw_json")
        if not raw_json:
            return {"success": False, "error": "Workflow JSON mavjud emas"}

        try:
            if isinstance(raw_json, str):
                workflow_data = json.loads(raw_json)
            else:
                workflow_data = raw_json
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"JSON parse xatosi: {e}"}

        result = await self._n8n.create_workflow(workflow_data)
        if result is None:
            return {"success": False, "error": "n8n serverda yaratishda xatolik"}

        workflow_id = result.get("id", "?")
        log.info("Workflow import qilindi: %s -> n8n ID: %s", filename, workflow_id)
        return {
            "success": True,
            "workflow_id": workflow_id,
            "name": workflow_data.get("name", filename),
        }

    async def import_by_query(self, query: str, limit: int = 5) -> dict:
        """So'rov bo'yicha workflow'larni import qiladi."""
        result = await self._templates.search_workflows(query=query, per_page=limit)
        if result is None:
            return {"success": False, "error": "Templates server ishlamayapti"}

        workflows = result.get("workflows", [])
        if not workflows:
            return {"success": False, "error": "Workflow topilmadi"}

        imported = []
        errors = []
        for wf in workflows:
            filename = wf.get("filename", "")
            if not filename:
                continue
            res = await self.import_workflow(filename)
            if res["success"]:
                imported.append(res)
            else:
                errors.append({"filename": filename, "error": res["error"]})

        return {
            "success": len(imported) > 0,
            "imported": len(imported),
            "errors": len(errors),
            "details": imported,
            "error_details": errors,
        }

    async def sync_all(self, limit: int = 50) -> dict:
        """Templates bazasidagi barcha workflow'larni sinxronlashtiradi."""
        result = await self._templates.search_workflows(per_page=limit)
        if result is None:
            return {"success": False, "error": "Templates server ishlamayapti"}

        workflows = result.get("workflows", [])
        total = result.get("total", 0)

        existing = await self._n8n.list_workflows(limit=200)
        existing_names = {w.get("name", "").lower() for w in existing}

        imported = []
        skipped = []
        for wf in workflows:
            name = wf.get("name", "").lower()
            if name in existing_names:
                skipped.append(wf.get("filename"))
                continue
            filename = wf.get("filename", "")
            if not filename:
                continue
            res = await self.import_workflow(filename)
            if res["success"]:
                imported.append(res)

        return {
            "success": True,
            "total_templates": total,
            "imported": len(imported),
            "skipped": len(skipped),
            "details": imported,
        }
