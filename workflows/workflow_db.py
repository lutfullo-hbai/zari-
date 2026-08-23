import json
import logging
import os
import sqlite3

log = logging.getLogger("zari")


class WorkflowDatabase:
    def __init__(self, db_path: str = ""):
        self.db_path = db_path or os.path.join(os.path.dirname(__file__), "database", "workflows.db")
        self.workflows_dir = os.path.join(os.path.dirname(__file__), "workflows")

    def _conn(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_table(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workflows (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    trigger_type TEXT DEFAULT 'Manual',
                    complexity TEXT DEFAULT 'low',
                    node_count INTEGER DEFAULT 0,
                    integrations TEXT DEFAULT '',
                    tags TEXT DEFAULT '',
                    category TEXT DEFAULT '',
                    raw_json TEXT DEFAULT ''
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_wf_name ON workflows(name)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_wf_trigger ON workflows(trigger_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_wf_tags ON workflows(tags)
            """)

    def index_all_workflows(self) -> dict:
        self._ensure_table()
        processed = 0
        skipped = 0
        errors = 0

        for root, dirs, files in os.walk(self.workflows_dir):
            for fname in files:
                if not fname.endswith(".json"):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, encoding="utf-8") as f:
                        data = json.load(f)
                except Exception as e:
                    log.warning("JSON parse xatosi %s: %s", fname, e)
                    errors += 1
                    continue

                category = os.path.basename(os.path.dirname(fpath))
                name = data.get("name", fname.replace(".json", ""))
                description = data.get("description", "")
                trigger_type = data.get("trigger_type", "Manual")
                complexity = data.get("complexity", "low")
                nodes = data.get("nodes", [])
                node_count = len(nodes)
                integrations = ", ".join(data.get("integrations", []))
                tags = ", ".join(data.get("tags", []))
                raw_json = json.dumps(data, ensure_ascii=False)

                try:
                    with self._conn() as conn:
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO workflows
                            (filename, name, description, trigger_type, complexity,
                             node_count, integrations, tags, category, raw_json)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                            (
                                fname,
                                name,
                                description,
                                trigger_type,
                                complexity,
                                node_count,
                                integrations,
                                tags,
                                category,
                                raw_json,
                            ),
                        )
                    processed += 1
                except Exception as e:
                    log.warning("DB yozish xatosi %s: %s", fname, e)
                    errors += 1

        return {"processed": processed, "skipped": skipped, "errors": errors}

    def get_stats(self) -> dict:
        self._ensure_table()
        with self._conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM workflows").fetchone()[0]
            active = conn.execute("SELECT COUNT(*) FROM workflows").fetchone()[0]
            triggers = {}
            for row in conn.execute("SELECT trigger_type, COUNT(*) as cnt FROM workflows GROUP BY trigger_type"):
                triggers[row["trigger_type"]] = row["cnt"]
            complexity = {}
            for row in conn.execute("SELECT complexity, COUNT(*) as cnt FROM workflows GROUP BY complexity"):
                complexity[row["complexity"]] = row["cnt"]
            total_nodes = conn.execute("SELECT COALESCE(SUM(node_count), 0) FROM workflows").fetchone()[0]
            unique_integrations = 0
            all_integrations = set()
            for row in conn.execute("SELECT integrations FROM workflows"):
                for i in row["integrations"].split(", "):
                    if i.strip():
                        all_integrations.add(i.strip())
            unique_integrations = len(all_integrations)

        return {
            "total": total,
            "active": active,
            "triggers": triggers,
            "complexity": complexity,
            "total_nodes": total_nodes,
            "unique_integrations": unique_integrations,
        }

    def get_service_categories(self) -> dict[str, list[str]]:
        self._ensure_table()
        cats: dict[str, list[str]] = {}
        with self._conn() as conn:
            for row in conn.execute("SELECT DISTINCT category, integrations FROM workflows"):
                cat = row["category"] or "other"
                if cat not in cats:
                    cats[cat] = []
                for i in row["integrations"].split(", "):
                    if i.strip() and i.strip() not in cats[cat]:
                        cats[cat].append(i.strip())
        return cats

    def search_workflows(
        self,
        query: str = "",
        trigger_filter: str = "all",
        complexity_filter: str = "all",
        limit: int = 5,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        self._ensure_table()
        where_clauses = []
        params = []

        if trigger_filter != "all":
            where_clauses.append("trigger_type = ?")
            params.append(trigger_filter)

        if complexity_filter != "all":
            where_clauses.append("complexity = ?")
            params.append(complexity_filter)

        if query:
            like_q = f"%{query}%"
            where_clauses.append("(name LIKE ? OR description LIKE ? OR tags LIKE ? OR integrations LIKE ?)")
            params.extend([like_q, like_q, like_q, like_q])

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        with self._conn() as conn:
            count_row = conn.execute(f"SELECT COUNT(*) FROM workflows WHERE {where_sql}", params).fetchone()[0]

            rows = conn.execute(
                f"SELECT * FROM workflows WHERE {where_sql} LIMIT ? OFFSET ?",
                params + [limit, offset],
            ).fetchall()

        results = []
        for r in rows:
            results.append(
                {
                    "filename": r["filename"],
                    "name": r["name"],
                    "description": r["description"],
                    "trigger_type": r["trigger_type"],
                    "complexity": r["complexity"],
                    "node_count": r["node_count"],
                    "integrations": r["integrations"].split(", ") if r["integrations"] else [],
                    "tags": r["tags"].split(", ") if r["tags"] else [],
                    "category": r["category"],
                }
            )

        return results, count_row
