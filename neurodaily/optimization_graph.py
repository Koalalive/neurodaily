"""LangGraph orchestration for the local search optimisation worker."""
from __future__ import annotations

from contextlib import closing
import sqlite3
from typing import TypedDict


class State(TypedDict):
    run_id: str


def invoke(path, run_id, state, step, stop, *, decision=None):
    from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
    from langgraph.checkpoint.sqlite import SqliteSaver
    from langgraph.graph import END, START, StateGraph
    from langgraph.types import Command, interrupt
    from langsmith import tracing_context

    def next_stage(_):
        if stop.is_set():
            return END
        run = state()
        if run["status"] == "review":
            return "review"
        if run["status"] == "running":
            return run["stage"]
        return END

    def process(_):
        step()
        return {}

    def review(_):
        interrupt({"run_id": run_id, "status": "awaiting_review"})
        return {}

    phases = ("capture", "propose", "evaluate", "verify")
    graph = StateGraph(State)
    for phase in phases:
        graph.add_node(phase, process)
        graph.add_conditional_edges(phase, next_stage, [*phases, "review", END])
    graph.add_node("review", review)
    graph.add_conditional_edges(START, next_stage, [*phases, "review", END])
    graph.add_edge("review", END)

    with tracing_context(enabled=False), closing(sqlite3.connect(path, check_same_thread=False)) as connection:
        saver = SqliteSaver(connection, serde=JsonPlusSerializer(allowed_msgpack_modules=()))
        workflow = graph.compile(checkpointer=saver)
        configuration = {"configurable": {"thread_id": run_id}, "recursion_limit": 80}
        saved = workflow.get_state(configuration)
        if decision is not None:
            if saved.next == ("review",):
                workflow.invoke(Command(resume=decision), configuration)
        elif saved.next:
            workflow.invoke(None, configuration)
        else:
            workflow.invoke({"run_id": run_id}, configuration)
