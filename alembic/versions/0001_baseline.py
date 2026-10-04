"""baseline schema
Revision ID: 0001
"""
from alembic import op
import sqlalchemy as sa
revision = "0001"; down_revision = None; branch_labels = None; depends_on = None
def upgrade():
    op.create_table("runs", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("task_id", sa.String(100), nullable=False), sa.Column("mode", sa.Enum("baseline", "verified", name="runmode"), nullable=False), sa.Column("candidate_code", sa.Text(), nullable=False), sa.Column("hidden_passed", sa.Boolean(), nullable=False), sa.Column("duration_ms", sa.Float(), nullable=False), sa.Column("token_usage", sa.Integer(), nullable=True), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_index("ix_runs_task_id", "runs", ["task_id"])
    op.create_table("test_results", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("run_id", sa.Integer(), sa.ForeignKey("runs.id", ondelete="CASCADE"), nullable=False), sa.Column("name", sa.String(200), nullable=False), sa.Column("passed", sa.Boolean(), nullable=False), sa.Column("stdout", sa.Text(), nullable=False), sa.Column("stderr", sa.Text(), nullable=False), sa.Column("error", sa.Text(), nullable=True))
def downgrade():
    op.drop_table("test_results"); op.drop_index("ix_runs_task_id", table_name="runs"); op.drop_table("runs"); op.execute("DROP TYPE runmode")
