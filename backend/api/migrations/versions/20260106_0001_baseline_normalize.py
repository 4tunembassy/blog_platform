"""Baseline normalization: align minimal schema required by API

- content_items.title (NOT NULL)
- provenance_events.agent_name (NOT NULL default 'system')
- provenance_events.status (NOT NULL default 'ok')
- provenance_events.details (NOT NULL default '{}'::jsonb)

Idempotent.
"""

from __future__ import annotations

from alembic import op

revision = "20260106_0001_baseline_normalize"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # content_items.title
    op.execute("""
    ALTER TABLE public.content_items
    ADD COLUMN IF NOT EXISTS title text;
    """)
    op.execute("""
    UPDATE public.content_items SET title = '' WHERE title IS NULL;
    """)
    op.execute("""
    ALTER TABLE public.content_items
    ALTER COLUMN title SET NOT NULL;
    """)

    # provenance_events required fields
    op.execute("""
    ALTER TABLE public.provenance_events
    ADD COLUMN IF NOT EXISTS agent_name text;
    """)
    op.execute("""
    ALTER TABLE public.provenance_events
    ADD COLUMN IF NOT EXISTS status text;
    """)
    op.execute("""
    ALTER TABLE public.provenance_events
    ADD COLUMN IF NOT EXISTS details jsonb NOT NULL DEFAULT '{}'::jsonb;
    """)

    op.execute("""
    UPDATE public.provenance_events
    SET agent_name = COALESCE(agent_name, 'system')
    WHERE agent_name IS NULL;
    """)
    op.execute("""
    UPDATE public.provenance_events
    SET status = COALESCE(status, 'ok')
    WHERE status IS NULL;
    """)
    op.execute("""
    UPDATE public.provenance_events
    SET details = COALESCE(details, '{}'::jsonb)
    WHERE details IS NULL;
    """)

    op.execute("""
    ALTER TABLE public.provenance_events
    ALTER COLUMN agent_name SET NOT NULL;
    """)
    op.execute("""
    ALTER TABLE public.provenance_events
    ALTER COLUMN status SET NOT NULL;
    """)


def downgrade() -> None:
    raise NotImplementedError("Downgrades are not supported for baseline normalization.")
