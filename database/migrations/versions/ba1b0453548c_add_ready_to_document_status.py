"""add_ready_to_document_status

Revision ID: ba1b0453548c
Revises: bc265d7aa4de
Create Date: 2026-11-21 18:23:05.638890

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ba1b0453548c'
down_revision: Union[str, None] = 'bc265d7aa4de'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_document_status", "documents", type_="check")
    op.create_check_constraint(
        "ck_document_status",
        "documents",
        "status IN ('processing', 'ready', 'indexed', 'failed')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_document_status", "documents", type_="check")
    op.create_check_constraint(
        "ck_document_status",
        "documents",
        "status IN ('processing', 'indexed', 'failed')",
    )
