"""Initial schema from ORM models

Revision ID: dc7aa5fd62af
Revises:
Create Date: 2026-08-20 20:35:13.805469

"""

from collections.abc import Sequence

from alembic import op
from app.models import Base

# revision identifiers, used by Alembic.
revision: str = "dc7aa5fd62af"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
    if bind.dialect.name == "postgresql":
        import sqlalchemy as sa
        bind.execute(sa.text("""
            DO $$ DECLARE
                r RECORD;
            BEGIN
                FOR r IN (
                    SELECT typname
                    FROM pg_type
                    JOIN pg_namespace ON pg_type.typnamespace = pg_namespace.oid
                    WHERE typcategory = 'E' AND nspname = current_schema()
                ) LOOP
                    EXECUTE 'DROP TYPE IF EXISTS ' || quote_ident(r.typname) || ' CASCADE';
                END LOOP;
            END $$;
        """))

