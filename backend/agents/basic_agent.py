"""
Basic demo LangGraph agent with simple tool-like calls and conditional routing.

This agent cycles through a small graph of nodes:
- random: generate a random number
- timestamp: capture current UNIX timestamp
- branch_a / branch_b: take different branches based on the random value
- loop/end decision: continue looping for a few iterations or end

Note: This is intentionally simple and does not wire into the EffectLogger yet.
"""

from __future__ import annotations

import random
import time
from typing import Literal, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, StateGraph
from services.observe import (
    compile_with_checkpointer,
    instrument_node,
    instrument_tool,
    record_stategraph_build,
)


class BasicAgentState(TypedDict, total=False):
    """State carried through the LangGraph nodes.

    - step: loop counter incremented on each branch
    - random_value: last generated random float in [0, 1)
    - timestamp: last captured UNIX timestamp
    - path: list of node names taken (for observability)
    - max_steps: stop condition when step >= max_steps
    - done: True when the graph decides to end
    """

    step: int
    random_value: float | None
    timestamp: float | None
    path: list[str]
    max_steps: int
    done: bool


def _initial_state(max_steps: int) -> BasicAgentState:
    return {
        "step": 0,
        "random_value": None,
        "timestamp": None,
        "path": [],
        "max_steps": max_steps,
        "done": False,
    }


# --- Simple tool-like functions (no external APIs) ---
@instrument_tool("random", kind="tool")
def _tool_random() -> float:
    """Generate a random number in [0, 1)."""

    return random.random()


@instrument_tool("timestamp", kind="tool")
def _tool_timestamp() -> float:
    """Return the current UNIX timestamp (seconds)."""

    return time.time()


# --- Graph nodes ---
@instrument_node("random")
def _node_random(state: BasicAgentState) -> BasicAgentState:
    value = _tool_random()
    state["random_value"] = value
    state.setdefault("path", []).append("random")
    return state


@instrument_node("timestamp")
def _node_timestamp(state: BasicAgentState) -> BasicAgentState:
    ts = _tool_timestamp()
    state["timestamp"] = ts
    state.setdefault("path", []).append("timestamp")
    return state


@instrument_node("branch_a")
def _node_branch_a(state: BasicAgentState) -> BasicAgentState:
    state["step"] = int(state.get("step", 0)) + 1
    state.setdefault("path", []).append("branch_a")
    return state


@instrument_node("branch_b")
def _node_branch_b(state: BasicAgentState) -> BasicAgentState:
    state["step"] = int(state.get("step", 0)) + 1
    state.setdefault("path", []).append("branch_b")
    return state


# --- Routing helpers ---
def _choose_branch(state: BasicAgentState) -> Literal["branch_a", "branch_b"]:
    """Decide which branch to take based on the random value."""

    rv = float(state.get("random_value") or 0.0)
    return "branch_a" if rv >= 0.5 else "branch_b"


def _route_after_branch(state: BasicAgentState) -> Literal["continue", "end"]:
    """Decide whether to continue looping or end the graph."""

    step = int(state.get("step", 0))
    max_steps = int(state.get("max_steps", 3))
    if step >= max_steps:
        state["done"] = True
        state.setdefault("path", []).append("end")
        return "end"
    return "continue"


def build_basic_agent(max_steps: int = 3, *, checkpointer: object | None = None):
    """Build and compile the demo graph.

    Returns a compiled LangGraph app which can be invoked with a state dict.
    """

    with record_stategraph_build():
        graph = StateGraph(BasicAgentState)

    # Nodes
    graph.add_node("random", _node_random)
    graph.add_node("timestamp", _node_timestamp)
    graph.add_node("branch_a", _node_branch_a)
    graph.add_node("branch_b", _node_branch_b)

    # Entry
    graph.set_entry_point("random")

    # Linear edge random -> timestamp
    graph.add_edge("random", "timestamp")

    # Conditional: from timestamp, choose which branch to take
    graph.add_conditional_edges(
        "timestamp",
        _choose_branch,
        {
            "branch_a": "branch_a",
            "branch_b": "branch_b",
        },
    )

    # After either branch, decide to continue loop or end
    for branch in ("branch_a", "branch_b"):
        graph.add_conditional_edges(
            branch,
            _route_after_branch,
            {
                "continue": "random",  # loop back to generate new random + timestamp
                "end": END,  # finish
            },
        )

    if checkpointer is not None:
        return compile_with_checkpointer(graph, checkpointer=checkpointer)
    return graph.compile()


def build_basic_agent_with_memory_checkpointer(max_steps: int = 3):
    memory = InMemorySaver()
    app = build_basic_agent(max_steps=max_steps, checkpointer=memory)
    return app, memory


def run_basic_agent(max_steps: int = 10, seed: int | None = None) -> BasicAgentState:
    """Run the demo agent to completion and return the final state.

    - max_steps: number of branch iterations before ending
    - seed: optional seed for deterministic random behavior
    """

    if seed is not None:
        random.seed(seed)
    # Register graph and start a run
    app = build_basic_agent(max_steps=max_steps)
    state = _initial_state(max_steps)
    try:
        result = app.invoke(state)
        return result
    except Exception:
        raise


__all__ = [
    "BasicAgentState",
    "build_basic_agent",
    "build_basic_agent_with_memory_checkpointer",
    "run_basic_agent",
]
