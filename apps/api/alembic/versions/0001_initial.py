"""Initial schema — all VoxDesk tables.

Revision ID: 0001
Revises:
Create Date: 2026-07-16
"""

from alembic import op

from app.models import Base

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ponytail: bootstrap from the ORM metadata so schema and models can't
    # drift; use `alembic revision --autogenerate` for every change after this.
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
