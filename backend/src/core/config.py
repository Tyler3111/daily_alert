"""Application settings loaded from environment variables."""

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    database_url: str = Field(
        default="postgresql+asyncpg://user:password@localhost:5432/job_dashboard",
        alias="DATABASE_URL",
    )
    postgres_user: str = Field(default="user", alias="POSTGRES_USER")
    postgres_password: str = Field(default="password", alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="job_dashboard", alias="POSTGRES_DB")
    job_keywords: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "software",
            "engineer",
            "backend",
            "fullstack",
            "python",
            "typescript",
            "hk",
            "hongkong",
        ],
        alias="JOB_KEYWORDS",
    )
    match_threshold: float = Field(default=0.6, alias="MATCH_THRESHOLD")
    fetch_interval_hours: int = Field(default=6, alias="FETCH_INTERVAL_HOURS")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")
    debug: bool = Field(default=True, alias="DEBUG")
    indeed_query: str = Field(default="software+engineer", alias="INDEED_QUERY")
    indeed_location: str = Field(default="hong+kong", alias="INDEED_LOCATION")

    @field_validator("job_keywords", mode="before")
    @classmethod
    def _parse_keywords(cls, value: str | list[str]) -> list[str]:
        """Parse keyword configuration from comma-separated string or list."""

        if isinstance(value, list):
            return value
        return [item.strip() for item in value.split(",") if item.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()


settings = get_settings()
