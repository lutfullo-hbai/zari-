import logging
import os
import re
import shutil
from pathlib import Path

from skills.base import BaseSkill

log = logging.getLogger("zari")

ALLOWED_DIRS = {Path.home(), Path("/tmp")}
SAFE_MODE = True


class FileManagerSkill(BaseSkill):
    priority = 80
    timeout = 15.0
    requires_confirmation = True
    confirmation_type = "danger"

    async def execute(self, query: str) -> dict | None:
        text = query.lower().strip()
        if not text:
            return None

        if any(w in text for w in ["list", "ko'rsat", "nima bor", "show", "ls"]):
            return await self._list_files(text)

        if any(w in text for w in ["och", "open", "cat", "o'qi", "read"]):
            return await self._read_file(text)

        if any(w in text for w in ["ochir", "o'chir", "delete", "rm"]):
            return await self._delete_file(text)

        if any(w in text for w in ["ko'chir", "move", "nomini o'zgartir", "rename", "copy", "nusxa"]):
            return await self._move_file(text)

        return None

    def _resolve_path(self, path_str: str) -> Path | None:
        p = Path(path_str).expanduser().resolve()
        if SAFE_MODE:
            allowed = False
            for d in ALLOWED_DIRS:
                if d in p.parents or d == p:
                    allowed = True
                    break
            if not allowed:
                return None
        return p

    async def _list_files(self, text: str) -> dict | None:
        dir_path = Path.home()
        for kw in ["list", "ko'rsat", "nima bor", "show", "ls"]:
            text = text.replace(kw, "").strip()
        text = text.strip()
        if text and Path(text).expanduser().exists():
            dir_path = Path(text).expanduser()

        try:
            entries = sorted(os.listdir(dir_path))[:30]
            dirs = [e + "/" for e in entries if (dir_path / e).is_dir()]
            files = [e for e in entries if not (dir_path / e).is_dir()]
            response = f"{dir_path.name}/ da {len(entries)} ta element:\n"
            response += "\n".join("  " + e for e in (dirs + files)[:25])
            return {"response": response, "context": str(dir_path), "source": "filemanager"}
        except Exception as e:
            log.warning("List xatosi: %s", e)
            return {"response": "Katalog ochilmadi.", "context": "", "source": "filemanager"}

    async def _read_file(self, text: str) -> dict | None:
        path = self._extract_path(text)
        if not path:
            return None
        p = self._resolve_path(path)
        if not p or not p.is_file():
            return {"response": f"Fayl topilmadi: {path}", "context": "", "source": "filemanager"}

        if p.stat().st_size > 100000:
            return {"response": "Fayl juda katta (100KB dan oshgan).", "context": "", "source": "filemanager"}

        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            preview = content[:500]
            response = f"{p.name} ({len(content)} chars):\n{preview}"
            if len(content) > 500:
                response += "..."
            return {"response": response, "context": content, "source": "filemanager"}
        except Exception as e:
            log.warning("Read xatosi: %s", e)
            return {"response": f"Fayl o'qilmadi: {path}", "context": "", "source": "filemanager"}

    async def _delete_file(self, text: str) -> dict | None:
        path = self._extract_path(text)
        if not path:
            return None
        p = self._resolve_path(path)
        if not p or not p.exists():
            return {"response": f"Topilmadi: {path}", "context": "", "source": "filemanager"}

        try:
            if p.is_file():
                p.unlink()
                return {"response": f"Fayl o'chirildi: {p.name}", "context": "", "source": "filemanager"}
            shutil.rmtree(p)
            return {"response": f"Katalog o'chirildi: {p.name}", "context": "", "source": "filemanager"}
        except Exception as e:
            log.warning("Delete xatosi: %s", e)
            return {"response": f"O'chirishda xatolik: {path}", "context": "", "source": "filemanager"}

    async def _move_file(self, text: str) -> dict | None:
        parts = (
            text.replace("ko'chir", "")
            .replace("nomini o'zgartir", "")
            .replace("rename", "")
            .replace("move", "")
            .replace("copy", "")
            .replace("nusxa", "")
            .split()
        )
        if len(parts) < 2:
            return None
        src = self._resolve_path(parts[0])
        dst = self._resolve_path(parts[-1])
        if not src or not dst:
            return {"response": "Noto'g'ri yo'l.", "context": "", "source": "filemanager"}
        try:
            if "copy" in text or "nusxa" in text:
                shutil.copy2(src, dst)
                return {"response": f"Nusxa olindi: {src.name} -> {dst}", "context": "", "source": "filemanager"}
            src.rename(dst)
            return {"response": f"Ko'chirildi: {src.name} -> {dst}", "context": "", "source": "filemanager"}
        except Exception as e:
            log.warning("Move xatosi: %s", e)
            return {"response": "Ko'chirishda xatolik.", "context": "", "source": "filemanager"}

    def _extract_path(self, text: str) -> str | None:
        cleaned = text.strip()

        for kw in [
            "och",
            "open",
            "cat",
            "o'qi",
            "read",
            "ochir",
            "o'chir",
            "delete",
            "rm",
            "ko'chir",
            "move",
            "nomini o'zgartir",
            "rename",
            "copy",
            "nusxa",
            "list",
            "ko'rsat",
            "ls",
            "fayl",
            "faylni",
            "papka",
            "katalog",
            "yo'li",
            "manzil",
        ]:
            cleaned = re.sub(rf"\b{re.escape(kw)}\b", " ", cleaned, flags=re.IGNORECASE)

        for pattern in [r'"([^"]+)"', r"'([^']+)'"]:
            match = re.search(pattern, cleaned)
            if match:
                return match.group(1).strip()

        tokens = [token for token in re.split(r"\s+", cleaned) if token]
        for token in reversed(tokens):
            token = token.strip(".,!?")
            if not token:
                continue
            if token in {".", "..", "~"}:
                continue
            if re.match(r"^(~|/|\.{1,2}/|[A-Za-z]:[\\/]).+", token):
                return token
            if "/" in token or "\\" in token or token.startswith("."):
                return token
            if re.search(r"\.(txt|md|py|json|yaml|yml|csv|log|ini|toml|sql)$", token, re.IGNORECASE):
                return token

        cleaned = cleaned.strip().strip(".,!?").strip()
        return cleaned if cleaned else None
