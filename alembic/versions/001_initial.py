"""initial schema — sessions, messages, persona, notes, wiki

Revision ID: 001_initial
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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
    op.create_index("idx_messages_session", "messages", ["session_id", "created_at"])

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
    op.create_index("idx_notes_content", "notes", ["content"])

    op.execute("""
        CREATE TABLE IF NOT EXISTS wiki (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """)


def downgrade() -> None:
    op.drop_table("wiki")
    op.drop_index("idx_notes_content", "notes")
    op.drop_table("notes")
    op.drop_table("persona")
    op.drop_index("idx_messages_session", "messages")
    op.drop_table("messages")
    op.drop_table("sessions")
