from __future__ import annotations

from dataclasses import asdict
from typing import Any
from uuid import UUID, uuid4

from agents.basic_agent import (
    build_basic_agent_with_memory_checkpointer,
    run_basic_agent,
)
from database.repositories import RunRepository, SpanRepository
from domain.models import Run as RunDom
from domain.models import Span as SpanDom
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from jsonpatch import make_patch
from services.observe import RECORDED_SPANS, span_context

router = APIRouter()


@router.get("/diff")
def diff_runs(left: UUID, right: UUID) -> JSONResponse:
    """Compute a structural diff between two runs' spans.

    Matching strategy (first pass):
    - Pair spans by (kind, name, node_id, fingerprint) when possible.
    - Report unmatched on either side for visibility.
    - For matched pairs, compute JSON Patch diffs for relevant structured attrs:
      * node spans: before_state, after_state
      * other spans: request, response
    """

    def _safe(obj: Any) -> Any:
        return obj if obj is not None else None

    def _patch(a: Any, b: Any) -> list[dict[str, Any]]:
        try:
            patch = make_patch(_safe(a), _safe(b))
            return list(patch.patch)
        except Exception:
            return []

    left_run = RunRepository.get_or_none(left)
    right_run = RunRepository.get_or_none(right)
    if not left_run or not right_run:
        raise HTTPException(status_code=404, detail="one or both runs not found")

    left_spans = SpanRepository.list_for_run(left)
    right_spans = SpanRepository.list_for_run(right)

    def _key(s: SpanDom) -> tuple[str, str, str | None, str]:
        return (s.kind, s.name, s.node_id, s.fingerprint)

    left_by_key: dict[tuple[str, str, str | None, str], SpanDom] = {
        _key(s): s for s in left_spans
    }
    right_by_key: dict[tuple[str, str, str | None, str], SpanDom] = {
        _key(s): s for s in right_spans
    }

    matched_keys = list(set(left_by_key.keys()) & set(right_by_key.keys()))
    only_left_keys = list(set(left_by_key.keys()) - set(right_by_key.keys()))
    only_right_keys = list(set(right_by_key.keys()) - set(left_by_key.keys()))

    matched: list[dict[str, Any]] = []
    for k in sorted(matched_keys):
        ls = left_by_key[k]
        rs = right_by_key[k]
        # Extract structured fields when present
        l_attrs = ls.attrs or {}
        r_attrs = rs.attrs or {}
        diffs: dict[str, Any] = {}
        if ls.kind == "node":
            diffs["before_state_patch"] = _patch(
                l_attrs.get("before_state"), r_attrs.get("before_state")
            )
            diffs["after_state_patch"] = _patch(
                l_attrs.get("after_state"), r_attrs.get("after_state")
            )
        else:
            diffs["request_patch"] = _patch(
                l_attrs.get("request"), r_attrs.get("request")
            )
            diffs["response_patch"] = _patch(
                l_attrs.get("response"), r_attrs.get("response")
            )

        matched.append(
            {
                "kind": ls.kind,
                "name": ls.name,
                "node_id": ls.node_id,
                "fingerprint": ls.fingerprint,
                "left": asdict(ls),
                "right": asdict(rs),
                "diffs": diffs,
            }
        )

    def _compact_span(s: SpanDom) -> dict[str, Any]:
        d = asdict(s)
        # keep essential identifying info for unmatched sets
        return {
            "id": d.get("id"),
            "kind": d.get("kind"),
            "name": d.get("name"),
            "node_id": d.get("node_id"),
            "fingerprint": d.get("fingerprint"),
        }

    only_left = [_compact_span(left_by_key[k]) for k in sorted(only_left_keys)]
    only_right = [_compact_span(right_by_key[k]) for k in sorted(only_right_keys)]

    payload = {
        "ok": True,
        "left_run": asdict(left_run),
        "right_run": asdict(right_run),
        "summary": {
            "matched": len(matched),
            "only_left": len(only_left),
            "only_right": len(only_right),
        },
        "matched": matched,
        "only_left": only_left,
        "only_right": only_right,
    }

    return JSONResponse(payload)


@router.post("/start")
def start_run(payload: dict[str, Any]) -> JSONResponse:
    thread_id = str(payload.get("thread_id") or uuid4())
    max_steps = int(payload.get("max_steps") or 5)
    policy = str(payload.get("policy") or "strict")

    # Build app with checkpointer so we can inspect history later
    app, memory = build_basic_agent_with_memory_checkpointer(max_steps=max_steps)

    # Create run record
    run_id = uuid4()
    run = RunDom(
        id=str(run_id),
        thread_id=thread_id,
        status="running",
        graph_signature=None,
        policy=policy,
        meta_data={},
    )
    RunRepository.create(run)

    # Execute by streaming values to generate checkpoints
    config = {"configurable": {"thread_id": thread_id}}
    try:
        # Ensure spans are tagged with this run_id/policy for all nested tool/node spans
        with span_context(
            run_id=str(run_id), node_id=None, checkpoint_id=None, policy=policy
        ):
            for _ in app.stream(
                {"max_steps": max_steps, "path": []}, config, stream_mode="values"
            ):
                pass
        # Save spans recorded so far for this run and clear in-memory buffer to avoid duplicates
        for s in list(RECORDED_SPANS):
            SpanRepository.create(
                SpanDom(
                    id=str(uuid4()),
                    run_id=str(run_id),
                    node_id=s.node_id,
                    checkpoint_id=s.checkpoint_id,
                    kind=s.kind,
                    name=s.name,
                    start_ts=s.start,
                    end_ts=s.end,
                    fingerprint=s.fingerprint,
                    attrs=s.attrs,
                )
            )
        RECORDED_SPANS.clear()
        run.status = "completed"
        RunRepository.update(run)
    except Exception as exc:  # pragma: no cover - simple demo flow
        run.status = "failed"
        RunRepository.update(run)
        raise HTTPException(status_code=500, detail=str(exc))

    return JSONResponse({"ok": True, "run_id": str(run_id), "thread_id": thread_id})


@router.get("")
def list_runs() -> JSONResponse:
    runs = RunRepository.list()
    return JSONResponse({"ok": True, "runs": [asdict(r) for r in runs]})


@router.get("/{run_id}")
def get_run(run_id: UUID) -> JSONResponse:
    run = RunRepository.get_or_none(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    return JSONResponse({"ok": True, "run": asdict(run)})


@router.get("/{run_id}/spans")
def list_spans(run_id: UUID) -> JSONResponse:
    spans = SpanRepository.list_for_run(run_id)
    return JSONResponse({"ok": True, "spans": [asdict(s) for s in spans]})


@router.get("/{run_id}/history")
def get_history(run_id: UUID) -> JSONResponse:
    # TODO(prod): Load persisted LangGraph checkpointer state for this run/thread
    #   - Use a durable checkpointer (e.g., SQLiteCheckpointer or custom DB-backed)
    #   - Store and retrieve by thread_id (and optionally run_id namespace)
    #   - Then call: list(app.get_state_history(config)) to return real checkpoints
    #   - Include for each state: checkpoint_id, next, minimal values, ts
    #   - Attach spans grouped by checkpoint_id for waterfall view
    #   - See LangGraph time-travel guide for expected shapes
    #   - https://langchain-ai.github.io/langgraph/tutorials/get-started/6-time-travel/
    # For demo, rebuild app and memory; in a real system we'd persist the memory
    app, memory = build_basic_agent_with_memory_checkpointer(max_steps=5)
    # No checkpoints to return here without persisted memory; return spans instead
    # TODO(prod): Replace spans-only fallback with real history:
    #   history = [
    #     {
    #       "checkpoint_id": st.config["configurable"]["checkpoint_id"],
    #       "next": st.next,
    #       "values": minimal_projection(st.values),
    #       "spans": spans_by_checkpoint.get(checkpoint_id, []),
    #     } for st in app.get_state_history(config)
    #   ]
    spans = SpanRepository.list_for_run(run_id)
    return JSONResponse(
        {"ok": True, "history": [], "spans": [asdict(s) for s in spans]}
    )


@router.post("/{run_id}/replay")
def replay_run(run_id: UUID, payload: dict[str, Any]) -> JSONResponse:
    # TODO(prod): Accept checkpoint_id and (optionally) thread_id in payload and resume
    #   - Load app + persisted checkpointer for the run/thread
    #   - Find the matching checkpoint from get_state_history(config)
    #   - Resume via: for ev in app.stream(None, to_replay.config, stream_mode="values")
    #   - Honor replay_policy: 'strict'|'hybrid'|'sim'
    #       * strict: require exact span fingerprint match; stop + diff on divergence
    #       * hybrid: prompt to stub or go live; log branch lineage
    #       * sim: use synthetic providers for speed
    #   - Wire STUBS to provide deterministic tool/LLM/HTTP/DB outputs
    #   - Persist replay as a new branch run (add parent_run_id if needed)
    # Here we simply re-run deterministically by setting fixed max_steps.
    max_steps = int(payload.get("max_steps") or 5)
    result = run_basic_agent(max_steps=max_steps, seed=42)
    return JSONResponse({"ok": True, "result": result})
