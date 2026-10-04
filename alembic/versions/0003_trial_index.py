"""add evaluation trial identifiers

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    # A server default backfills pre-evaluation rows safely, then is removed
    # so application defaults remain the single source for future inserts.
    op.add_column("runs", sa.Column("trial_index", sa.Integer(), nullable=False, server_default="0"))
    op.add_column(
        "verification_sessions",
        sa.Column("trial_index", sa.Integer(), nullable=False, server_default="0"),
    )
    op.alter_column("runs", "trial_index", server_default=None)
    op.alter_column("verification_sessions", "trial_index", server_default=None)


def downgrade():
    op.drop_column("verification_sessions", "trial_index")
    op.drop_column("runs", "trial_index")
