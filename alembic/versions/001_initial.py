"""initial schema — sessions, messages, persona, notes, wiki

Idempotent: IF NOT EXISTS — mavjud DB (init_db() davrida yaratilgan)
ham, bo'sh DB ham xatosiz upgrade qilinadi.

Revision ID: 001_initial
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages (session_id, created_at)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS persona (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'general',
            confidence REAL DEFAULT 1.0,
            source TEXT DEFAULT 'manual',
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id SERIAL PRIMARY KEY,
            title TEXT DEFAULT '',
            content TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now(),
            tags TEXT DEFAULT ''
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_notes_content ON notes (content)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS wiki (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_notes_content")
    op.execute("DROP TABLE IF EXISTS wiki")
    op.execute("DROP TABLE IF EXISTS notes")
    op.execute("DROP TABLE IF EXISTS persona")
    op.execute("DROP INDEX IF EXISTS idx_messages_session")
    op.execute("DROP TABLE IF EXISTS messages")
    op.execute("DROP TABLE IF EXISTS sessions")
