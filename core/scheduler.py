"""
Scheduler — vaqt asosida avtomatik vazifalar.

PostgreSQL'ga saqlanuvchi schedule'lar: bir marta, kunlik, haftalik.
Pipeline text_queue orqali trigger qiladi.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from db.database import get_pool

log = logging.getLogger("zari")


@dataclass
class ScheduledTask:
    id: int | None = None
    name: str = ""
    message: str = ""
    schedule_type: str = "once"
    schedule_value: str = ""
    is_active: bool = True
    last_run: datetime | None = None
    next_run: datetime | None = None


async def init_scheduler_table() -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                message TEXT NOT NULL,
                schedule_type TEXT NOT NULL DEFAULT 'once',
                schedule_value TEXT NOT NULL DEFAULT '',
                is_active BOOLEAN NOT NULL DEFAULT true,
                last_run TIMESTAMPTZ,
                next_run TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )


async def add_task(
    name: str,
    message: str,
    schedule_type: str = "once",
    schedule_value: str = "",
) -> ScheduledTask:
    next_run = _calculate_next_run(schedule_type, schedule_value)
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO scheduled_tasks (name, message, schedule_type, schedule_value, next_run)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, name, message, schedule_type, schedule_value,
                      is_active, last_run, next_run
            """,
            name, message, schedule_type, schedule_value, next_run,
        )
    log.info("Task qo'shildi: %s (%s)", name, schedule_type)
    return _row_to_task(row)


async def list_tasks(active_only: bool = True) -> list[ScheduledTask]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        if active_only:
            rows = await conn.fetch(
                "SELECT * FROM scheduled_tasks WHERE is_active = true ORDER BY next_run"
            )
        else:
            rows = await conn.fetch(
                "SELECT * FROM scheduled_tasks ORDER BY next_run"
            )
    return [_row_to_task(r) for r in rows]


async def remove_task(task_id: int) -> bool:
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM scheduled_tasks WHERE id = $1", task_id
        )
    return result.endswith("1")


async def get_due_tasks() -> list[ScheduledTask]:
    now = datetime.now(UTC)
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM scheduled_tasks
            WHERE is_active = true AND (next_run IS NULL OR next_run <= $1)
            ORDER BY next_run
            """,
            now,
        )
    return [_row_to_task(r) for r in rows]


async def mark_executed(task_id: int, schedule_type: str, schedule_value: str) -> None:
    now = datetime.now(UTC)
    next_run = None if schedule_type == "once" else _calculate_next_run(schedule_type, schedule_value)
    is_active = schedule_type != "once"
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE scheduled_tasks
            SET last_run = $1, next_run = $2, is_active = $3
            WHERE id = $4
            """,
            now, next_run, is_active, task_id,
        )


async def run_scheduler_loop(text_queue: asyncio.Queue[str], interval: float = 30.0) -> None:
    """Asosiy scheduler tsikli — due task'larni text_queue'ga joylaydi."""
    log.info("Scheduler ishga tushdi (interval: %.0fs)", interval)
    while True:
        try:
            due = await get_due_tasks()
            for task in due:
                log.info("Scheduled task ishga tushdi: %s → %s", task.name, task.message)
                await text_queue.put(task.message)
                await mark_executed(task.id, task.schedule_type, task.schedule_value)
        except Exception as e:
            log.warning("Scheduler xatosi: %s", e)
        await asyncio.sleep(interval)


def _calculate_next_run(schedule_type: str, schedule_value: str) -> datetime | None:
    now = datetime.now(UTC)
    if schedule_type == "once":
        return now
    if schedule_type == "daily":
        try:
            hour, minute = schedule_value.split(":")
            target = now.replace(hour=int(hour), minute=int(minute), second=0, microsecond=0)
            if target <= now:
                from datetime import timedelta
                target += timedelta(days=1)
            return target
        except (ValueError, AttributeError):
            from datetime import timedelta
            return now + timedelta(days=1)
    if schedule_type == "interval":
        try:
            minutes = int(schedule_value)
            from datetime import timedelta
            return now + timedelta(minutes=minutes)
        except (ValueError, AttributeError):
            from datetime import timedelta
            return now + timedelta(hours=1)
    return now


def _row_to_task(row) -> ScheduledTask:
    return ScheduledTask(
        id=row["id"],
        name=row["name"],
        message=row["message"],
        schedule_type=row["schedule_type"],
        schedule_value=row["schedule_value"],
        is_active=row["is_active"],
        last_run=row["last_run"],
        next_run=row["next_run"],
    )
