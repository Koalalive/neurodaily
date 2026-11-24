"""HTTP surface for the Advanced Search optimisation workbench."""
from __future__ import annotations

from collections.abc import Callable
from datetime import date as CalendarDate
from threading import Event

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, StrictBool
from starlette.responses import JSONResponse

from .optimization import LOG, Optimizer
from .optimization_store import Conflict


class RequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Message(RequestBody):
    text: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=64)
    rounds: int = Field(default=4, ge=1, le=6)
    max_sources: int = Field(default=10, ge=1, le=14)
    focus_sources: list[str] = Field(default_factory=list, max_length=8)
    allow_tradeoffs: StrictBool = False


class Preference(RequestBody):
    enabled: StrictBool


class Label(RequestBody):
    ids: list[str] = Field(min_length=1, max_length=12)
    relevant: StrictBool
    date: CalendarDate | None = None


class Decision(RequestBody):
    candidate_id: str | None = Field(default=None, max_length=64)


def router(optimizer: Optimizer):
    api = APIRouter(prefix="/api/optimization")

    def response(operation: Callable):
        try:
            result = operation()
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from None
        except Conflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from None
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from None
        return JSONResponse(result, headers={"Cache-Control": "no-store"})

    @api.get("")
    def state(conversation_id: str | None = None, history_run_id: int | None = None):
        return response(lambda: optimizer.state(conversation_id, history_run_id))

    @api.post("/conversations")
    def start_conversation():
        def operation():
            scope, cfg = optimizer.current()
            key = optimizer.store.conversation(scope, cfg.profile, new=True)
            return optimizer.state(key)

        return response(operation)

    @api.post("/messages")
    def send_message(payload: Message):
        def operation():
            record = optimizer.launch(**payload.model_dump())
            return optimizer.state(record["conversation_id"])

        return response(operation)

    @api.post("/preferences")
    def preferences(payload: Preference):
        def operation():
            scope, _ = optimizer.current()
            optimizer.store.preference(scope, payload.enabled)
            return {"enabled": payload.enabled}

        return response(operation)

    @api.post("/labels")
    def labels(payload: Label):
        def operation():
            ids = [identifier.strip() for identifier in payload.ids]
            if any(not identifier or len(identifier) > 500 or any(ord(c) < 32 for c in identifier)
                   for identifier in ids):
                raise ValueError("Invalid record identifiers")
            scope, _ = optimizer.current()
            optimizer.store.label(scope, ids, payload.relevant, payload.date.isoformat() if payload.date else None)
            return {"ok": True, "labels": optimizer.store.labels(scope)}

        return response(operation)

    @api.post("/runs/{run_id}/{action}")
    def decide(run_id: str, action: str, payload: Decision | None = None):
        def operation():
            if action not in {"accept", "reject", "resume", "cancel", "rollback"}:
                raise LookupError("Unknown optimisation action")
            updated = optimizer.command(run_id, action, payload.candidate_id if payload else None)
            return optimizer.state(updated["conversation_id"])

        return response(operation)

    return api


def worker(optimizer: Optimizer, stop: Event):
    while not stop.is_set():
        try:
            if optimizer.store.path.exists():
                optimizer.tick(stop)
        except Exception as exc:
            LOG.warning("Could not read the search optimisation queue (%s)", type(exc).__name__)
        stop.wait(0.8)
