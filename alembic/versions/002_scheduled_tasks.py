"""scheduled_tasks — scheduler jadvali

Revision ID: 002_scheduled_tasks
Revises: 001_initial
Create Date: 2026-08-23 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "002_scheduled_tasks"
down_revision: str | None = "001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
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
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_next_run "
        "ON scheduled_tasks (is_active, next_run)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_scheduled_tasks_next_run")
    op.execute("DROP TABLE IF EXISTS scheduled_tasks")
