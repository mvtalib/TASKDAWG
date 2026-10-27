"""Application settings, read from environment variables."""

import logging
import os
import secrets
from dataclasses import dataclass

log = logging.getLogger("taskdawg")


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    database_url: str
    secret_key: str
    access_token_minutes: int
    cors_origins: list[str]
    auto_create_tables: bool


def load_settings() -> Settings:
    secret_key = os.getenv("SECRET_KEY", "").strip()
    if not secret_key:
        # Fine for local development; tokens just stop working after a restart.
        secret_key = secrets.token_urlsafe(48)
        log.warning(
            "SECRET_KEY is not set. Using a temporary key, so logins will be "
            "invalidated whenever the server restarts. Set SECRET_KEY in production."
        )

    return Settings(
        database_url=os.getenv("DATABASE_URL", "sqlite:///./taskdawg.db"),
        secret_key=secret_key,
        access_token_minutes=int(os.getenv("ACCESS_TOKEN_MINUTES", "1440")),
        cors_origins=_csv(
            os.getenv("CORS_ORIGINS", "http://localhost:5500,http://127.0.0.1:5500")
        ),
        auto_create_tables=_bool(os.getenv("AUTO_CREATE_TABLES", "true")),
    )


settings = load_settings()
