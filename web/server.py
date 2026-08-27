"""
Zari Web UI — kirish nuqtasi.

FastAPI serverni va pipeline ni parallel ishga tushiradi.
    python -m web.server
"""

import asyncio
import signal
import sys

import uvicorn

from core.config import settings
from core.logging import get_logger
from core.main import ZariPipeline
from web.app import app, set_pipeline

log = get_logger("zari.web")


async def run_server(pipeline: ZariPipeline) -> None:
    config = uvicorn.Config(
        app,
        host=settings.web_host,
        port=settings.web_port,
        log_level="info",
        access_log=False,
    )
    server = uvicorn.Server(config)
    await server.serve()


async def main() -> None:
    pipeline = ZariPipeline()
    await pipeline.init()
    set_pipeline(pipeline)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(_shutdown(pipeline)))

    log.info("Zari Web UI ishga tushmoqda... http://%s:%s", settings.web_host, settings.web_port)

    await asyncio.gather(
        pipeline.start_text_only(),
        run_server(pipeline),
    )


async def _shutdown(pipeline: ZariPipeline) -> None:
    log.info("Shutdown...")
    await pipeline.stop()
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
