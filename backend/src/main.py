"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.api import router as api_router
from src.core.config import settings
from src.core.database import Base, engine
from src.core import models as _models  # noqa: F401
from src.utils.logging import setup_logging

LOGGER = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Manage startup and shutdown lifecycle events."""

    setup_logging(settings.debug)
    LOGGER.info("Starting Job Alert Dashboard backend")
    try:
        async with engine.begin() as connection:
            await connection.execute(text("SELECT 1"))
            await connection.run_sync(Base.metadata.create_all)
        LOGGER.info("Database connection verified and tables initialized")
    except SQLAlchemyError as exc:
        LOGGER.exception("Database initialization failed: %s", exc)
        raise

    yield

    await engine.dispose()
    LOGGER.info("Backend shutdown complete")


app = FastAPI(title="Job Alert Dashboard", debug=settings.debug, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Return service health status."""

    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=settings.debug)
