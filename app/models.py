import enum
from datetime import UTC, datetime
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase): pass
class RunMode(str, enum.Enum): baseline = "baseline"; verified = "verified"


class VerificationStatus(str, enum.Enum):
    pending   = "pending"    # created, pipeline thread not yet started
    running   = "running"    # pipeline thread is executing
    succeeded = "succeeded"  # at least one candidate or repair passed all tests
    exhausted = "exhausted"  # all candidates and repairs failed
    failed    = "failed"     # unhandled exception during pipeline execution


class AttemptPhase(str, enum.Enum): candidate = "candidate"; repair = "repair"


class Run(Base):
    __tablename__ = "runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[str] = mapped_column(String(100), index=True)
    mode: Mapped[RunMode] = mapped_column(Enum(RunMode), nullable=False)
    # Zero is the backwards-compatible value for runs created outside an
    # evaluation batch.  Evaluation runners set this explicitly.
    trial_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    candidate_code: Mapped[str] = mapped_column(Text)
    hidden_passed: Mapped[bool] = mapped_column(Boolean)
    duration_ms: Mapped[float] = mapped_column()
    token_usage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    # Nullable FK linking a baseline run to its parent async session.
    # Null for runs created by the legacy synchronous /baseline/run endpoint.
    session_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("verification_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    test_results: Mapped[list["TestResult"]] = relationship(cascade="all, delete-orphan")


class TestResult(Base):
    __tablename__ = "test_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(200))
    passed: Mapped[bool] = mapped_column(Boolean)
    stdout: Mapped[str] = mapped_column(Text, default="")
    stderr: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class VerificationSession(Base):
    __tablename__ = "verification_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[str] = mapped_column(String(100), index=True)
    # Kept as a string instead of an enum so new interactive rows remain
    # clearly separable without changing the established HumanEval enum types.
    source: Mapped[str] = mapped_column(String(20), default="humaneval", nullable=False, index=True)
    # mode: baseline | verified | interactive — required for async /sessions API
    mode: Mapped[str] = mapped_column(String(12), nullable=False, default="verified")
    question: Mapped[str | None] = mapped_column(Text, nullable=True)
    oracle_kind: Mapped[str | None] = mapped_column(String(30), nullable=True)
    oracle_tests: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    trial_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[VerificationStatus] = mapped_column(Enum(VerificationStatus), nullable=False)
    # Human-readable pipeline stage for progress tracking (e.g. "generating_candidates")
    current_stage: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # Populated when status == failed; sanitised exception type + message only
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    attempts: Mapped[list["Attempt"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="Attempt.id"
    )


class Attempt(Base):
    __tablename__ = "attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("verification_sessions.id", ondelete="CASCADE"))
    phase: Mapped[AttemptPhase] = mapped_column(Enum(AttemptPhase), nullable=False)
    attempt_index: Mapped[int] = mapped_column(Integer, nullable=False)
    candidate_code: Mapped[str] = mapped_column(Text, nullable=False)
    passed_visible_tests: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    passed_hidden_tests: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_selected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    stdout: Mapped[str] = mapped_column(Text, default="", nullable=False)
    stderr: Mapped[str] = mapped_column(Text, default="", nullable=False)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_usage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[float | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    session: Mapped[VerificationSession] = relationship(back_populates="attempts")
