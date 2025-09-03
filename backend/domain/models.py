from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class User:
    id: str
    email: str
    password: str
    meta_data: dict[str, Any]


@dataclass
class Run:
    id: str
    thread_id: str
    status: str
    graph_signature: str | None
    policy: str | None
    meta_data: dict[str, Any]


@dataclass
class Span:
    id: str
    run_id: str
    node_id: str | None
    checkpoint_id: str | None
    kind: str
    name: str
    start_ts: float
    end_ts: float | None
    fingerprint: str
    attrs: dict[str, Any]
