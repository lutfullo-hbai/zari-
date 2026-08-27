"""Code Runner — kodni izolyatsiya qilingan subprocess'da ishga tushirish."""

import logging
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from skills.base import BaseSkill

log = logging.getLogger("zari")

CODE_BLOCK_RE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.DOTALL)
MAX_OUTPUT_CHARS = 4000
TIMEOUT_SECONDS = 30


class CodeRunnerSkill(BaseSkill):
    """Python kodini vaqtinchalik papkada, timeout bilan ishga tushiradi.

    XAVFSIZLIK: bu to'liq sandbox EMAS — oddiy subprocess izolyatsiyasi.
    Shu sababli har doim foydalanuvchi tasdiqini talab qiladi.
    """

    priority = 40
    timeout = 45.0
    requires_confirmation = True
    confirmation_type = "danger"

    async def execute(self, query: str) -> dict | None:
        text = query.lower()
        if not any(w in text for w in ["kodni ishga", "ishga tushir", "run kod", "kod yozib"]):
            return None

        # 1) ```blok``` ichidagi kod
        m = CODE_BLOCK_RE.search(query)
        if m:
            return await self._run_code(m.group(1))

        # 2) .py fayl yo'li
        fm = re.search(r"([\w ./~\-]+\.py)\b", query)
        if fm:
            p = Path(fm.group(1).strip()).expanduser()
            if not p.is_absolute():
                cand = Path.home() / p
                p = cand if cand.exists() else p
            if p.is_file():
                return await self._run_file(p)

        # 3) "kod yozib ishga tushir: <kod>" — kalit so'zdan keyingi matn
        im = re.search(
            r"(?:kod yozib ishga tushir|kodni ishga tushir)[:\s]+(.+)",
            query,
            re.IGNORECASE | re.DOTALL,
        )
        if im and ("print(" in im.group(1) or "=" in im.group(1)):
            return await self._run_code(im.group(1).strip())

        return None

    async def _run_code(self, code: str) -> dict:
        proc = await self._exec([sys.executable, "-c", code])
        return self._format(proc)

    async def _run_file(self, path: Path) -> dict:
        proc = await self._exec([sys.executable, str(path)], cwd=str(path.parent))
        return self._format(proc)

    @staticmethod
    async def _exec(cmd: list[str], cwd: str | None = None) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        tmpdir = tempfile.mkdtemp(prefix="zari_run_")
        loop = __import__("asyncio").get_running_loop()
        try:
            return await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=TIMEOUT_SECONDS,
                    cwd=cwd or tmpdir,
                    env=env,
                ),
            )
        except subprocess.TimeoutExpired:
            return subprocess.CompletedProcess(cmd, returncode=124, stdout="", stderr=f"Timeout ({TIMEOUT_SECONDS}s)")

    @staticmethod
    def _format(proc: subprocess.CompletedProcess) -> dict:
        out = (proc.stdout or "").strip()[:MAX_OUTPUT_CHARS]
        err = (proc.stderr or "").strip()[:MAX_OUTPUT_CHARS]
        if proc.returncode == 0:
            response = out or "(kod bajarildi, chiqish bo'sh)"
            status = "OK"
        elif proc.returncode == 124:
            response = err
            status = "TIMEOUT"
        else:
            last_err = "\n".join(err.splitlines()[-6:])
            response = f"Xato (kod {proc.returncode}):\n{last_err}"
            status = "ERROR"
        return {
            "response": response,
            "context": f"code_runner:{status}",
            "source": "code_runner",
        }
