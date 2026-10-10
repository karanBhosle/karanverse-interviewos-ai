"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-11
"""

from alembic import op

from app import models  # noqa: F401
from app.core.db import Base

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
