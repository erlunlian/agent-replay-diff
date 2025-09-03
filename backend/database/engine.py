import os

from sqlmodel import SQLModel, create_engine

# TEMP: Use SQLite locally if DATABASE_URL is not set
DATABASE_URL = os.environ.get("DATABASE_URL") or "sqlite:///./local.db"

# Use the provided database URL (e.g., postgresql+psycopg://user:pass@host:5432/db)
ENGINE = create_engine(DATABASE_URL, pool_pre_ping=True)


def ensure_tables() -> None:
    from . import models  # noqa: F401

    SQLModel.metadata.create_all(ENGINE)
