"""verification sessions and attempts
Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "verification_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.String(100), nullable=False),
        sa.Column("status", sa.Enum("running", "succeeded", "exhausted", name="verificationstatus"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_verification_sessions_task_id", "verification_sessions", ["task_id"])
    op.create_table(
        "attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("verification_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("phase", sa.Enum("candidate", "repair", name="attemptphase"), nullable=False),
        sa.Column("attempt_index", sa.Integer(), nullable=False),
        sa.Column("candidate_code", sa.Text(), nullable=False),
        sa.Column("passed_visible_tests", sa.Boolean(), nullable=True),
        sa.Column("passed_hidden_tests", sa.Boolean(), nullable=True),
        sa.Column("is_selected", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("stdout", sa.Text(), nullable=False, server_default=""),
        sa.Column("stderr", sa.Text(), nullable=False, server_default=""),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("token_usage", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade():
    op.drop_table("attempts")
    op.drop_index("ix_verification_sessions_task_id", table_name="verification_sessions")
    op.drop_table("verification_sessions")
    op.execute("DROP TYPE attemptphase")
    op.execute("DROP TYPE verificationstatus")
