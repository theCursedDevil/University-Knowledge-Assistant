"""add_document_role_restriction_check

Revision ID: f18c7a9d4b21
Revises: cd7a0430f759
Create Date: 2026-11-24
"""
from typing import Sequence, Union

from alembic import op

revision: str = "f18c7a9d4b21"
down_revision: Union[str, None] = "cd7a0430f759"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_document_role_restriction",
        "documents",
        "role_restriction IS NULL OR role_restriction IN ('all', 'student', 'faculty', 'admin')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_document_role_restriction", "documents", type_="check")
