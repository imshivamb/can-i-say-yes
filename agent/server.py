from __future__ import annotations

import os
import threading
import traceback
from collections.abc import Callable
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from adapters.files.runtime import reset_runtime
from adapters.files.store import read_seed_commitment_ids
from adapters.files.world import DATA_ROOT, load_world
from agent.agent import invoke
from agent.clock import advance_clock
from agent.config import cors_origins
from agent.human import approve_decision, fulfill_approved_option, open_decision, reject_decision
from agent.offline import run_recorded_investigation
from agent.runtime import apply_session_snapshot
from agent.session import AgentSession
from agent.trigger import poll_and_reassess
from domain.fixtures import acme_campaign_request, nova_launch_request
from domain.ids import new_id
from domain.models import WorldEvent

app = FastAPI(title="Can I Say Yes?", version="0.2.0")


@app.exception_handler(Exception)
async def unhandled_error(_request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, HTTPException):
        raise exc
    detail: dict[str, Any] = {"detail": str(exc)}
    if os.getenv("CISAY_DEBUG", "").lower() in {"1", "true", "yes"}:
        detail["traceback"] = traceback.format_exc()
    return JSONResponse(status_code=500, content=detail)


app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Invocation(BaseModel):
    input: dict[str, Any]


class RequestInput(BaseModel):
    text: str
    recorded: bool = False
    example: Literal["acme", "nova"] = "acme"


class ApprovalInput(BaseModel):
    option_id: str


class AdvanceInput(BaseModel):
    to: str
    recorded: bool = False


class InboundEventInput(BaseModel):
    event_id: str
    summary: str
    source_reference: str
    related_commitment_ids: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)


_JOBS: dict[str, dict[str, Any]] = {}
_JOBS_LOCK = threading.Lock()


def _job_snapshot(job_id: str) -> dict[str, Any] | None:
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
        return None if job is None else dict(job)


def _start_job(work: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    job_id = new_id("job")
    with _JOBS_LOCK:
        _JOBS[job_id] = {"status": "pending"}

    def run() -> None:
        try:
            result = work()
            with _JOBS_LOCK:
                _JOBS[job_id] = {"status": "done", "result": result}
        except Exception as exc:
            with _JOBS_LOCK:
                _JOBS[job_id] = {"status": "error", "detail": str(exc)}

    threading.Thread(target=run, daemon=True).start()
    return {"job_id": job_id, "status": "pending"}


def _maybe_async(async_job: bool, work: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    if async_job:
        return _start_job(work)
    return work()


def _new_session() -> AgentSession:
    session = AgentSession(
        world=load_world(),
        data_root=DATA_ROOT,
        seed_commitment_ids=read_seed_commitment_ids(DATA_ROOT),
    )
    session.load_runtime()
    return session


def _recorded_mode(value: bool = False) -> bool:
    return value or os.getenv("CISAY_RECORDED", "").lower() in {"1", "true", "yes"}


def _find_or_404(items: dict[str, Any], item_id: str, label: str) -> Any:
    item = items.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"unknown {label}: {item_id}")
    return item


@app.get("/ping")
def ping() -> dict[str, str]:
    return {"status": "Healthy"}


@app.post("/invocations")
def invocations(payload: Invocation) -> dict[str, Any]:
    data = payload.input
    kind = data.get("kind")
    session = _new_session()
    apply_session_snapshot(session, data)
    try:
        if kind == "parse_request":
            result = invoke(session, "parse_request", prompt=data.get("prompt", ""))
        elif kind == "assess_feasibility":
            request = session.requests.get(data.get("request_id"))
            if request is None:
                raise ValueError("request_id is required and must be stored")
            result = invoke(session, "assess_feasibility", request=request)
        elif kind == "reassess_commitment":
            result = invoke(
                session,
                "reassess_commitment",
                commitment_id=data.get("commitment_id"),
            )
        elif kind == "draft_customer_message":
            result = invoke(session, "draft_customer_message", prompt=data.get("prompt", ""))
        else:
            raise HTTPException(status_code=400, detail=f"unknown invocation kind: {kind}")
    except (KeyError, ValueError, StopIteration) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"output": result.model_dump(mode="json")}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    job = _job_snapshot(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"unknown job: {job_id}")
    return job


@app.post("/api/requests")
def create_request(payload: RequestInput, async_job: bool = False) -> dict[str, Any]:
    def work() -> dict[str, Any]:
        session = _new_session()
        if _recorded_mode(payload.recorded):
            request = acme_campaign_request() if payload.example == "acme" else nova_launch_request()
            request = request.model_copy(update={"raw_text": payload.text})
            session.put_request(request)
        else:
            request = invoke(session, "parse_request", prompt=payload.text)
        session.persist()
        return {"request": request.model_dump(mode="json")}

    return _maybe_async(async_job, work)


@app.post("/api/requests/{request_id}/assess")
def assess_request(
    request_id: str,
    recorded: bool = False,
    async_job: bool = False,
) -> dict[str, Any]:
    def work() -> dict[str, Any]:
        session = _new_session()
        request = _find_or_404(session.requests, request_id, "request")
        if _recorded_mode(recorded):
            assessment = run_recorded_investigation(session, request)
        else:
            assessment = invoke(session, "assess_feasibility", request=request)
        decision = None
        if assessment.required_human_decision:
            decision = open_decision(
                session,
                assessment,
                reason=f"{assessment.decision}: human approval is required for this promise.",
            )
        session.persist()
        return {
            "assessment": assessment.model_dump(mode="json"),
            "decision": decision.model_dump(mode="json") if decision else None,
        }

    return _maybe_async(async_job, work)


@app.get("/api/assessments/{assessment_id}")
def get_assessment(assessment_id: str) -> dict[str, Any]:
    session = _new_session()
    return _find_or_404(session.assessments, assessment_id, "assessment").model_dump(mode="json")


@app.get("/api/decisions")
def list_decisions() -> list[dict[str, Any]]:
    session = _new_session()
    return [item.model_dump(mode="json") for item in session.decisions.values()]


@app.get("/api/decisions/{decision_id}")
def get_decision(decision_id: str) -> dict[str, Any]:
    session = _new_session()
    return _find_or_404(session.decisions, decision_id, "decision").model_dump(mode="json")


@app.post("/api/decisions/{decision_id}/approve")
def approve(decision_id: str, payload: ApprovalInput) -> dict[str, Any]:
    session = _new_session()
    try:
        decision = approve_decision(session, decision_id, payload.option_id)
        fulfill_approved_option(session, decision.id)
    except (KeyError, ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    session.persist()
    return {"decision": session.decisions[decision_id].model_dump(mode="json")}


@app.post("/api/decisions/{decision_id}/reject")
def reject(decision_id: str) -> dict[str, Any]:
    session = _new_session()
    try:
        decision = reject_decision(session, decision_id)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"decision": decision.model_dump(mode="json")}


@app.get("/api/commitments")
def list_commitments() -> list[dict[str, Any]]:
    return [item.model_dump(mode="json") for item in _new_session().commitments()]


@app.get("/api/commitments/{commitment_id}")
def get_commitment(commitment_id: str) -> dict[str, Any]:
    session = _new_session()
    commitment = next(
        (item for item in session.commitments() if item.id == commitment_id),
        None,
    )
    if commitment is None:
        raise HTTPException(status_code=404, detail=f"unknown commitment: {commitment_id}")
    return commitment.model_dump(mode="json")


@app.get("/api/activity")
def activity() -> list[dict[str, Any]]:
    return [item.model_dump(mode="json") for item in _new_session().activity]


@app.get("/api/inbox")
def inbox() -> list[dict[str, Any]]:
    session = _new_session()
    return [item.model_dump(mode="json") for item in session.world.emails]


@app.get("/api/evidence/{evidence_id}")
def get_evidence(evidence_id: str) -> dict[str, Any]:
    session = _new_session()
    for assessment in session.assessments.values():
        for evidence in assessment.evidence:
            if evidence.id == evidence_id:
                return evidence.model_dump(mode="json")
    raise HTTPException(status_code=404, detail=f"unknown evidence: {evidence_id}")


@app.get("/api/clock")
def clock() -> dict[str, Any]:
    return _new_session().world.clock.model_dump(mode="json")


@app.post("/api/clock/advance")
def advance(payload: AdvanceInput, async_job: bool = False) -> dict[str, Any]:
    def work() -> dict[str, Any]:
        session = _new_session()
        opened = advance_clock(session, payload.to, recorded=payload.recorded)
        return {"opened_decisions": [item.model_dump(mode="json") for item in opened]}

    return _maybe_async(async_job, work)


@app.post("/api/events/inbound")
def inbound_event(payload: InboundEventInput, async_job: bool = False) -> dict[str, Any]:
    def work() -> dict[str, Any]:
        session = _new_session()
        event = WorldEvent(
            id=payload.event_id,
            type="supplier_update",
            occurs_at=session.world.clock.now,
            source_reference=payload.source_reference,
            summary=payload.summary,
            payload=payload.payload,
            related_commitment_ids=payload.related_commitment_ids,
        )
        if any(item.id == event.id for item in session.world.events):
            return {"status": "duplicate", "event_id": event.id}
        session.world.events.append(event)
        session.persist()
        opened = advance_clock(
            session,
            session.world.clock.now,
            recorded=_recorded_mode(),
        )
        return {"status": "accepted", "event_id": event.id, "opened_decisions": len(opened)}

    return _maybe_async(async_job, work)


@app.post("/api/integrations/gmail/poll")
def poll_gmail(query: str = "newer_than:7d") -> dict[str, Any]:
    session = _new_session()
    try:
        event_ids = poll_and_reassess(
            session,
            query=query,
            recorded=_recorded_mode(),
        )
    except (OSError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"status": "accepted", "event_ids": event_ids}


@app.post("/api/demo/reset")
def reset() -> dict[str, str]:
    reset_runtime(DATA_ROOT)
    with _JOBS_LOCK:
        _JOBS.clear()
    return {"status": "reset"}

