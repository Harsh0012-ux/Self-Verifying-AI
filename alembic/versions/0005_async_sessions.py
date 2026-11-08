"""add async session support: mode, current_stage, error_message, runs.session_id

Revision ID: 0005
Revises: 0004
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    # ------------------------------------------------------------------ #
    # PostgreSQL: enum types cannot have values removed later, only added. #
    # We use IF NOT EXISTS (Postgres 9.3+) to make the migration re-        #
    # runnable in development without raising "already exists" errors.     #
    # ------------------------------------------------------------------ #
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        # ALTER TYPE … ADD VALUE cannot run inside a transaction block in
        # older Postgres versions; use COMMIT-less execution via autocommit.
        # SQLAlchemy makes this easy by executing raw DDL outside the
        # implicit transaction when we use op.execute with the connection.
        op.execute(
            "ALTER TYPE verificationstatus ADD VALUE IF NOT EXISTS 'pending'"
        )
        op.execute(
            "ALTER TYPE verificationstatus ADD VALUE IF NOT EXISTS 'failed'"
        )
    # For SQLite (used in tests) the Enum column is VARCHAR, so no ALTER
    # TYPE is needed — the new string values just work.

    # ------------------------------------------------------------------ #
    # verification_sessions: add mode, current_stage, error_message        #
    # ------------------------------------------------------------------ #
    op.add_column(
        "verification_sessions",
        sa.Column(
            "mode",
            sa.String(12),
            nullable=False,
            server_default="verified",
        ),
    )
    op.add_column(
        "verification_sessions",
        sa.Column(
            "current_stage",
            sa.String(30),
            nullable=True,
        ),
    )
    op.add_column(
        "verification_sessions",
        sa.Column("error_message", sa.Text(), nullable=True),
    )

    # Remove the server_default now that existing rows have been back-filled.
    if dialect == "postgresql":
        op.alter_column("verification_sessions", "mode", server_default=None)

    # ------------------------------------------------------------------ #
    # runs: add nullable session_id FK so baseline runs can be linked       #
    # ------------------------------------------------------------------ #
    op.add_column(
        "runs",
        sa.Column(
            "session_id",
            sa.Integer(),
            sa.ForeignKey("verification_sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_runs_session_id", "runs", ["session_id"])


def downgrade():
    op.drop_index("ix_runs_session_id", table_name="runs")
    op.drop_column("runs", "session_id")

    op.drop_column("verification_sessions", "error_message")
    op.drop_column("verification_sessions", "current_stage")
    op.drop_column("verification_sessions", "mode")

    # NOTE: PostgreSQL does not support removing enum values.
    # Downgrading will leave 'pending' and 'failed' in the enum type.
    # They will simply be unused after the columns referencing them are gone.
    # This is safe; no data integrity issue results.
