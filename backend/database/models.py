from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import JSON
from sqlmodel import Column, Field, SQLModel


class User(SQLModel, table=True):
    id: UUID = Field(primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    email: str
    password: str
    meta_data: dict[str, Any] = Field(sa_column=Column(JSON))


class Run(SQLModel, table=True):
    id: UUID = Field(primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    thread_id: str
    status: str
    graph_signature: str | None = None
    policy: str | None = None
    meta_data: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


class Span(SQLModel, table=True):
    id: UUID = Field(primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    run_id: UUID
    node_id: str | None = None
    checkpoint_id: str | None = None
    kind: str
    name: str
    start_ts: float
    end_ts: float | None = None
    fingerprint: str
    attrs: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
