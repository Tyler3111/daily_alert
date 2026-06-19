"""Pydantic schemas for API responses."""

from datetime import datetime

from pydantic import BaseModel


class JobOut(BaseModel):
    """Placeholder job response schema."""

    id: int
    title: str
    company: str


class RefreshResponse(BaseModel):
    """Response for refresh endpoint."""

    success: bool
    message: str


class StatsResponse(BaseModel):
    """Response for dashboard statistics."""

    total_jobs: int
    total_matches: int
    last_refresh: datetime | None
