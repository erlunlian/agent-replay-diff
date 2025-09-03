"""
Lightweight observability + deterministic replay helpers.

Goals (per design.md):
- Record external I/O spans with minimal SDK surface.
- Tag spans with {run_id, node_id, checkpoint_id}.
- Support stubbed responses and deterministic replay policies.
- Provide a graph recorder that captures nodes/edges/condition functions to
  derive a deterministic graph signature/id.

This module intentionally avoids tight coupling to DB/storage. It exposes
simple in-memory facilities you can replace later with durable stores.
"""

from __future__ import annotations

import contextlib
import dataclasses
import functools
import hashlib
import json
import threading
import time
import types
import uuid
from typing import Any, Callable, Iterator

# --------------------
# Span & Artifact model
# --------------------


@dataclasses.dataclass(slots=True)
class Artifact:
    uri: str
    mime: str
    sha256: str
    size: int
    redacted: bool = False
    is_synthetic: bool = False


@dataclasses.dataclass(slots=True)
class Span:
    id: str
    run_id: str | None
    checkpoint_id: str | None
    node_id: str | None
    kind: str  # e.g., "http", "db", "tool"
    name: str
    start: float
    end: float | None
    attrs: dict[str, Any]
    fingerprint: str
    request_artifact: Artifact | None = None
    response_artifact: Artifact | None = None


# --------------------
# Thread-local context
# --------------------


_local = threading.local()


def _get_ctx() -> dict[str, Any]:
    ctx = getattr(_local, "ctx", None)
    if ctx is None:
        ctx = {
            "run_id": None,
            "node_id": None,
            "checkpoint_id": None,
            "policy": "strict",
        }
        _local.ctx = ctx
    return ctx


@contextlib.contextmanager
def span_context(
    *,
    run_id: str | None,
    node_id: str | None,
    checkpoint_id: str | None,
    policy: str | None = None,
) -> Iterator[None]:
    ctx = _get_ctx()
    prev = ctx.copy()
    try:
        if run_id is not None:
            ctx["run_id"] = run_id
        if node_id is not None:
            ctx["node_id"] = node_id
        if checkpoint_id is not None:
            ctx["checkpoint_id"] = checkpoint_id
        if policy is not None:
            ctx["policy"] = policy
        yield
    finally:
        _local.ctx = prev


# --------------------
# Stub registry & recorder
# --------------------


class _StubRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._fingerprint_to_response: dict[str, Any] = {}

    def add_stub(self, fingerprint: str, response: Any) -> None:
        with self._lock:
            self._fingerprint_to_response[fingerprint] = response

    def get(self, fingerprint: str) -> tuple[bool, Any | None]:
        with self._lock:
            if fingerprint in self._fingerprint_to_response:
                return True, self._fingerprint_to_response[fingerprint]
            return False, None


STUBS = _StubRegistry()
RECORDED_SPANS: list[Span] = []


def _now() -> float:
    return time.time()


def _safe_json(obj: Any) -> str:
    try:
        return json.dumps(obj, sort_keys=True, default=str)
    except Exception:
        return json.dumps(str(obj))


def _hash_str(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def compute_fingerprint(
    kind: str, name: str, *, args: tuple[Any, ...], kwargs: dict[str, Any]
) -> str:
    payload = {
        "kind": kind,
        "name": name,
        "args": _safe_json(args),
        "kwargs": _safe_json(kwargs),
    }
    return _hash_str(json.dumps(payload, sort_keys=True))


# --------------------
# Internal helpers to reduce nesting/duplication
# --------------------


def _make_request_payload(
    args: tuple[Any, ...], kwargs: dict[str, Any]
) -> dict[str, Any]:
    return {"args": _safe_json(args), "kwargs": _safe_json(kwargs)}


def _tool_attrs(
    *,
    function_qualname: str,
    mode: str,
    status: str,
    request_payload: dict[str, Any],
    response: Any | None = None,
    error: BaseException | None = None,
) -> dict[str, Any]:
    attrs: dict[str, Any] = {
        "function": function_qualname,
        "mode": mode,
        "status": status,
        "request": request_payload,
    }
    if error is not None:
        attrs["error"] = repr(error)
    if response is not None:
        attrs["response"] = _safe_json(response)
    return attrs


def _snapshot_state_dict(value: Any) -> Any | None:
    if not isinstance(value, dict):
        return None
    try:
        return json.loads(_safe_json(value))
    except Exception:
        return value


def _node_attrs(
    *,
    function_qualname: str,
    status: str,
    before_state: Any | None,
    after_state: Any | None = None,
    error: BaseException | None = None,
) -> dict[str, Any]:
    attrs: dict[str, Any] = {
        "function": function_qualname,
        "status": status,
        "before_state": before_state,
    }
    if after_state is not None:
        attrs["after_state"] = after_state
    if error is not None:
        attrs["error"] = repr(error)
    return attrs


def _record_span(
    *,
    kind: str,
    name: str,
    start_ts: float,
    end_ts: float,
    attrs: dict[str, Any],
    fingerprint: str,
    node_override: str | None = None,
) -> None:
    ctx = _get_ctx()
    span = Span(
        id=str(uuid.uuid4()),
        run_id=ctx.get("run_id"),
        checkpoint_id=ctx.get("checkpoint_id"),
        node_id=node_override if node_override is not None else ctx.get("node_id"),
        kind=kind,
        name=name,
        start=start_ts,
        end=end_ts,
        attrs=attrs,
        fingerprint=fingerprint,
    )
    RECORDED_SPANS.append(span)


def instrument_tool(
    name: str, *, kind: str = "tool"
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to record a span for a function and optionally stub responses.

    Usage:
        @instrument_tool("random")
        def _tool_random():
            ...
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        qualname = getattr(func, "__qualname__", func.__name__)

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_ts = _now()
            fingerprint = compute_fingerprint(kind, name, args=args, kwargs=kwargs)
            request_payload = _make_request_payload(args, kwargs)

            is_stubbed, stubbed_value = STUBS.get(fingerprint)
            if is_stubbed:
                result = stubbed_value
                end_ts = _now()
                attrs = _tool_attrs(
                    function_qualname=qualname,
                    mode="stubbed",
                    status="ok",
                    request_payload=request_payload,
                    response=result,
                )
                _record_span(
                    kind=kind,
                    name=name,
                    start_ts=start_ts,
                    end_ts=end_ts,
                    attrs=attrs,
                    fingerprint=fingerprint,
                )
                return result

            try:
                result = func(*args, **kwargs)
                end_ts = _now()
                attrs = _tool_attrs(
                    function_qualname=qualname,
                    mode="live",
                    status="ok",
                    request_payload=request_payload,
                    response=result,
                )
                _record_span(
                    kind=kind,
                    name=name,
                    start_ts=start_ts,
                    end_ts=end_ts,
                    attrs=attrs,
                    fingerprint=fingerprint,
                )
                return result
            except Exception as exc:
                end_ts = _now()
                attrs = _tool_attrs(
                    function_qualname=qualname,
                    mode="live",
                    status="error",
                    request_payload=request_payload,
                    error=exc,
                )
                _record_span(
                    kind=kind,
                    name=name,
                    start_ts=start_ts,
                    end_ts=end_ts,
                    attrs=attrs,
                    fingerprint=fingerprint,
                )
                raise

        return wrapper

    return decorator


def instrument_node(name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to record a span for a graph node execution."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        qualname = getattr(func, "__qualname__", func.__name__)

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_ts = _now()
            before_state = _snapshot_state_dict(args[0]) if args else None
            with span_context(
                run_id=_get_ctx().get("run_id"),
                node_id=name,
                checkpoint_id=_get_ctx().get("checkpoint_id"),
            ):
                try:
                    result = func(*args, **kwargs)
                    end_ts = _now()
                    after_state = _snapshot_state_dict(result)
                    attrs = _node_attrs(
                        function_qualname=qualname,
                        status="ok",
                        before_state=before_state,
                        after_state=after_state,
                    )
                    _record_span(
                        kind="node",
                        name=name,
                        start_ts=start_ts,
                        end_ts=end_ts,
                        attrs=attrs,
                        fingerprint=_hash_str(f"node:{name}:{qualname}"),
                        node_override=name,
                    )
                    return result
                except Exception as exc:
                    end_ts = _now()
                    attrs = _node_attrs(
                        function_qualname=qualname,
                        status="error",
                        before_state=before_state,
                        error=exc,
                    )
                    _record_span(
                        kind="node",
                        name=name,
                        start_ts=start_ts,
                        end_ts=end_ts,
                        attrs=attrs,
                        fingerprint=_hash_str(f"node:{name}:{qualname}"),
                        node_override=name,
                    )
                    raise

        return wrapper

    return decorator


# --------------------
# Graph recorder (monkey patches add_node/add_edge/add_conditional_edges)
# --------------------


@dataclasses.dataclass(slots=True)
class RecordedNode:
    name: str
    function_qualname: str


@dataclasses.dataclass(slots=True)
class RecordedEdge:
    source: str
    target: str


@dataclasses.dataclass(slots=True)
class RecordedConditional:
    source: str
    chooser_qualname: str
    mapping: dict[str, str]


@dataclasses.dataclass(slots=True)
class RecordedGraph:
    entrypoint: str | None
    nodes: list[RecordedNode]
    edges: list[RecordedEdge]
    conditionals: list[RecordedConditional]

    @property
    def signature(self) -> str:
        # Deterministic signature independent of object identity
        payload = {
            "entry": self.entrypoint,
            "nodes": [
                dataclasses.asdict(n) for n in sorted(self.nodes, key=lambda n: n.name)
            ],
            "edges": [
                dataclasses.asdict(e)
                for e in sorted(self.edges, key=lambda e: (e.source, e.target))
            ],
            "conds": [
                dataclasses.asdict(c)
                for c in sorted(
                    self.conditionals, key=lambda c: (c.source, c.chooser_qualname)
                )
            ],
        }
        return _hash_str(json.dumps(payload, sort_keys=True))


class _GraphRecorder:
    def __init__(self) -> None:
        self.nodes: list[RecordedNode] = []
        self.edges: list[RecordedEdge] = []
        self.conds: list[RecordedConditional] = []
        self.entrypoint: str | None = None

    def to_record(self) -> RecordedGraph:
        return RecordedGraph(
            self.entrypoint, list(self.nodes), list(self.edges), list(self.conds)
        )


@contextlib.contextmanager
def record_stategraph_build() -> Iterator[_GraphRecorder]:
    """Record StateGraph topology by monkey-patching add_node/edge/conditional.

    Usage:
        with record_stategraph_build() as rec:
            graph = StateGraph(State)
            ... add nodes/edges ...
        signature = rec.to_record().signature
    """

    try:
        from langgraph.graph import StateGraph  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency surface
        raise RuntimeError("LangGraph not available") from exc

    recorder = _GraphRecorder()

    orig_add_node = StateGraph.add_node
    orig_add_edge = StateGraph.add_edge
    orig_add_conditional_edges = StateGraph.add_conditional_edges
    orig_set_entry_point = StateGraph.set_entry_point

    def _qualname(fn: Any) -> str:
        if isinstance(fn, (types.FunctionType, types.MethodType)):
            return getattr(fn, "__qualname__", getattr(fn, "__name__", str(fn)))
        return str(fn)

    def add_node(self: Any, name: str, fn: Callable[..., Any]) -> None:  # type: ignore[override]
        recorder.nodes.append(RecordedNode(name=name, function_qualname=_qualname(fn)))
        return orig_add_node(self, name, fn)

    def add_edge(self: Any, source: str, target: str) -> None:  # type: ignore[override]
        recorder.edges.append(RecordedEdge(source=source, target=str(target)))
        return orig_add_edge(self, source, target)

    def add_conditional_edges(self: Any, source: str, chooser: Callable[..., Any], mapping: dict[str, Any]) -> None:  # type: ignore[override]
        normalized: dict[str, str] = {}
        for key, tgt in mapping.items():
            normalized[key] = str(tgt)
        recorder.conds.append(
            RecordedConditional(
                source=source, chooser_qualname=_qualname(chooser), mapping=normalized
            )
        )
        return orig_add_conditional_edges(self, source, chooser, mapping)

    def set_entry_point(self: Any, name: str) -> None:  # type: ignore[override]
        recorder.entrypoint = name
        return orig_set_entry_point(self, name)

    # Monkey patch
    StateGraph.add_node = add_node  # type: ignore[assignment]
    StateGraph.add_edge = add_edge  # type: ignore[assignment]
    StateGraph.add_conditional_edges = add_conditional_edges  # type: ignore[assignment]
    StateGraph.set_entry_point = set_entry_point  # type: ignore[assignment]

    try:
        yield recorder
    finally:
        # Restore
        StateGraph.add_node = orig_add_node  # type: ignore[assignment]
        StateGraph.add_edge = orig_add_edge  # type: ignore[assignment]
        StateGraph.add_conditional_edges = orig_add_conditional_edges  # type: ignore[assignment]
        StateGraph.set_entry_point = orig_set_entry_point  # type: ignore[assignment]


# --------------------
# LangGraph time-travel helpers
# --------------------


def compile_with_checkpointer(graph_builder: Any, *, checkpointer: Any | None):
    """Compile a StateGraph builder with optional checkpointer.

    Mirrors LangGraph's compile(checkpointer=...). The builder is the instance
    returned by StateGraph(...).
    """

    return graph_builder.compile(checkpointer=checkpointer)


def get_state_history(app: Any, *, config: dict[str, Any]) -> list[Any]:
    return list(app.get_state_history(config))


def resume_from_checkpoint(
    app: Any, *, checkpoint_config: dict[str, Any]
) -> Iterator[dict[str, Any]]:
    """Stream values resuming from a prior checkpoint config.

    checkpoint_config should contain {"configurable": {"thread_id": ..., "checkpoint_id": ...}}
    See LangGraph time travel docs.
    """

    return app.stream(None, checkpoint_config, stream_mode="values")


__all__ = [
    "Artifact",
    "Span",
    "span_context",
    "instrument_tool",
    "instrument_node",
    "STUBS",
    "RECORDED_SPANS",
    "record_stategraph_build",
    "RecordedGraph",
    "compile_with_checkpointer",
    "get_state_history",
    "resume_from_checkpoint",
]
