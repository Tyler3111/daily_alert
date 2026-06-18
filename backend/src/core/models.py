"""Database models for sources, jobs, and matches."""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class SourceState(Base):
    """Track fetch state for each data source."""

    __tablename__ = "source_states"
    __table_args__ = (
        UniqueConstraint("source", name="uq_source_states_source"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    last_fetch_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_fetch_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_fetch_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class Job(Base):
    """Store normalized job listings."""

    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("source", "source_id", name="uq_jobs_source_source_id"),
        Index("ix_jobs_source_posted_at", "source", "posted_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    company: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    raw_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    matches: Mapped[list["Match"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class Match(Base):
    """Store matching results for each job."""

    __tablename__ = "matches"
    __table_args__ = (
        Index("ix_matches_score", "score"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    match_type: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    job: Mapped[Job] = relationship(back_populates="matches")
