"""
Local workflow executor — n8n formatidagi JSON fayllarni lokalda bajarradi.

Xavfsizlik: executeCommand node faqat xavfsiz buyruqlarni bajaradi.
Shell injection oldini olish uchun shell=True ishlatilmaydi.
"""

import json
import logging
import os
import subprocess

import httpx

log = logging.getLogger("zari")

WORKFLOWS_DIR = os.path.join(os.path.dirname(__file__), "workflows")

ALLOWED_COMMANDS = {
    "ls",
    "cat",
    "echo",
    "date",
    "uname",
    "whoami",
    "pwd",
    "uptime",
    "df",
    "free",
    "ps",
    "top",
    "hostname",
}


def run_workflow(workflow_name: str) -> str:
    if not workflow_name.endswith(".json"):
        workflow_name += ".json"

    for root, dirs, files in os.walk(WORKFLOWS_DIR):
        for fname in files:
            if fname == workflow_name:
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, encoding="utf-8") as f:
                        data = json.load(f)
                except Exception as e:
                    return f"Workflow faylini o'qishda xatolik: {e}"

                return _execute_workflow_nodes(data)

    return f"'{workflow_name}' workflow topilmadi."


def _execute_workflow_nodes(data: dict) -> str:
    nodes = data.get("nodes", [])
    results = []

    for node in nodes:
        node_type = node.get("type", "")
        params = node.get("parameters", {})

        if "httpRequest" in node_type:
            result = _exec_http(params)
        elif "executeCommand" in node_type:
            result = _exec_command(params)
        elif "set" in node_type:
            result = _exec_set(params)
        else:
            result = f"Node '{node.get('name', 'unknown')}' qo'llab-quvvatlanmaydi"

        results.append(f"[{node.get('name', '?')}]: {result}")

    return "\n".join(results)


def _exec_http(params: dict) -> str:
    url = params.get("url", "")
    method = params.get("method", "GET")
    if not url:
        return "URL ko'rsatilmagan"
    try:
        with httpx.Client(timeout=15.0) as client:
            if method.upper() == "GET":
                resp = client.get(url)
            elif method.upper() == "POST":
                resp = client.post(url, json=params.get("body", {}))
            elif method.upper() == "PUT":
                resp = client.put(url, json=params.get("body", {}))
            elif method.upper() == "DELETE":
                resp = client.delete(url)
            else:
                resp = client.get(url)

            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                return f"{len(data)} ta ma'lumot olindi"
            return str(data)[:300]
    except Exception as e:
        return f"HTTP xatosi: {e}"


def _exec_command(params: dict) -> str:
    command = params.get("command", "")
    if not command:
        return "Buyruq ko'rsatilmagan"

    parts = command.strip().split()
    if not parts:
        return "Buyruq bo'sh"

    base_cmd = parts[0]
    if base_cmd not in ALLOWED_COMMANDS:
        return (
            f"Xavfsizlik: '{base_cmd}' buyrug'i ruxsat etilmagan. Ruxsat etilgan: {', '.join(sorted(ALLOWED_COMMANDS))}"
        )

    try:
        result = subprocess.run(
            parts,
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = result.stdout.strip() or result.stderr.strip()
        return output[:300] if output else "Hech qanday natija yo'q"
    except subprocess.TimeoutExpired:
        return "Buyruq timeout (10 soniya)"
    except Exception as e:
        return f"Buyruq xatosi: {e}"


def _exec_set(params: dict) -> str:
    values = params.get("values", {})
    if isinstance(values, dict):
        string_vals = values.get("string", [])
        return f"Ma'lumot formatlandi: {len(string_vals)} ta maydon"
    return "Formatlandi"
