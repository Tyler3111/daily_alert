# src/core/base.py
"""Base class for SQLAlchemy models."""

from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """Base class for all database models."""
    pass