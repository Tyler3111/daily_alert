"""Schemas for jobs domain models."""

from datetime import datetime

from pydantic import BaseModel


class JobCreate(BaseModel):
    """Schema for creating a new job record."""

    source: str
    source_id: str
    title: str
    company: str
    location: str | None = None
    description: str | None = None
    url: str
    posted_at: datetime | None = None
