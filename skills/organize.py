"""Papkani kategoriya bo'yicha tartibga solish."""

import logging
import re
from pathlib import Path

from skills.base import BaseSkill

log = logging.getLogger("zari")

CATEGORY_DIRS = {
    "rasmlar": {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg", ".ico"},
    "hujjatlar": {
        ".pdf",
        ".docx",
        ".doc",
        ".xlsx",
        ".xls",
        ".pptx",
        ".txt",
        ".md",
        ".csv",
        ".odt",
    },
    "musiqa": {".mp3", ".wav", ".flac", ".ogg", ".m4a"},
    "videolar": {".mp4", ".mkv", ".avi", ".mov", ".webm"},
    "arxivlar": {".zip", ".tar", ".gz", ".rar", ".7z", ".bz2"},
    "kodlar": {".py", ".js", ".ts", ".sh", ".json", ".yaml", ".yml", ".toml"},
}


def _category_for(ext: str) -> str:
    for cat, exts in CATEGORY_DIRS.items():
        if ext.lower() in exts:
            return cat
    return "boshqalar"


class OrganizeSkill(BaseSkill):
    """Har doim tasdiq talab qiladi va hech qachon ustiga yozmaydi."""

    priority = 82
    timeout = 60.0
    requires_confirmation = True
    confirmation_type = "danger"

    async def execute(self, query: str) -> dict | None:
        text = query.lower()
        if not any(w in text for w in ["tartibga sol", "tartibla", "sarala", "organize"]):
            return None

        # MUHIM: matnni tozalamasdan to'g'ridan-to'g'ri qidiramiz,
        # aks holda "organizes" kabi yo'llar buzilib qoladi.
        raw = self._extract_dir(text)
        target = Path(raw).expanduser() if raw else Path.home()
        if not target.is_dir():
            return {
                "response": f"Papka topilmadi: {raw or '~'}",
                "context": "",
                "source": "organize",
            }

        moved, skipped = await self._organize(target)
        if moved == 0 and skipped == 0:
            return {
                "response": f"{target.name}/ allaqachon tartibli.",
                "context": "",
                "source": "organize",
            }

        parts = [f"{moved} ta fayl kategoriyalarga joylashtirildi."]
        if skipped:
            parts.append(f"{skipped} ta xatolik tufayli qoldirildi.")
        return {
            "response": " ".join(parts),
            "context": str(target),
            "source": "organize",
        }

    @staticmethod
    def _extract_dir(cleaned: str) -> str:
        """Tirnoqli (bo'shliqqa ega bo'lishi mumkin) yoki oddiy yo'lni oladi."""
        m = re.search(r'"([^"]+)"|\'([^\']+)\'', cleaned)
        if m:
            return next(g for g in m.groups() if g).strip()
        m = re.search(r"~(?:/[\w.\-]+)*|/(?:[\w.\-]+/+)*[\w.\-]+", cleaned)
        return m.group(0).strip() if m else ""

    @staticmethod
    def _unique_dest(dest_dir: Path, name: str) -> Path:
        dest = dest_dir / name
        stem, suffix = Path(name).stem, Path(name).suffix
        counter = 2
        while dest.exists():
            dest = dest_dir / f"{stem} ({counter}){suffix}"
            counter += 1
        return dest

    async def _organize(self, target: Path) -> tuple[int, int]:
        moved = skipped = 0
        for item in sorted(target.iterdir()):
            if not item.is_file():
                continue
            cat = _category_for(item.suffix)
            cat_dir = target / cat.capitalize()
            try:
                cat_dir.mkdir(exist_ok=True)
                dest = self._unique_dest(cat_dir, item.name)
                item.rename(dest)
                log.info("Organize: %s -> %s", item.name, dest)
                moved += 1
            except OSError as e:
                log.warning("Organize skip %s: %s", item.name, e)
                skipped += 1
        return moved, skipped
