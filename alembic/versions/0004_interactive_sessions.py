"""add interactive verification metadata

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import sqlalchemy as sa


revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "verification_sessions",
        sa.Column("source", sa.String(length=20), nullable=False, server_default="humaneval"),
    )
    op.add_column("verification_sessions", sa.Column("question", sa.Text(), nullable=True))
    op.add_column("verification_sessions", sa.Column("oracle_kind", sa.String(length=30), nullable=True))
    op.add_column("verification_sessions", sa.Column("oracle_tests", sa.JSON(), nullable=True))
    op.create_index("ix_verification_sessions_source", "verification_sessions", ["source"])
    op.alter_column("verification_sessions", "source", server_default=None)


def downgrade():
    op.drop_index("ix_verification_sessions_source", table_name="verification_sessions")
    op.drop_column("verification_sessions", "oracle_tests")
    op.drop_column("verification_sessions", "oracle_kind")
    op.drop_column("verification_sessions", "question")
    op.drop_column("verification_sessions", "source")
