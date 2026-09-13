from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, Literal, Never

from strands import Agent
from strands.models.openai import OpenAIModel
from strands.types.exceptions import StructuredOutputException

from agent.config import aws_region, load_prompt, model_id
from agent.hooks import AuthorityAndTraceHooks
from agent.schemas.message import CustomerMessageDraft
from agent.session import AgentSession, ensure_request_id, use_session
from agent.tools import P0_TOOLS, WRITE_TOOLS
from agent.verify import verify_assessment, verify_reassessment
from domain.clock import DEMO_START
from domain.ids import new_id
from domain.models import AgentHandoff, FeasibilityAssessment, ParsedRequest
from domain.reassess import apply_reassessment

InvokeKind = Literal[
    "parse_request",
    "assess_feasibility",
    "reassess_commitment",
    "draft_customer_message",
]
AgentRole = Literal["investigator", "monitor"]


def _assert_never(value: Never) -> Never:
    raise ValueError(f"unhandled invoke kind: {value}")


def _build_model() -> OpenAIModel:
    """Build an OpenAI-compatible model routed through Amazon Bedrock Mantle."""
    return OpenAIModel(
        model_id=model_id(),
        bedrock_mantle_config={"region": aws_region()},
        params={"temperature": 0.0},
    )


def _system_prompt(kind: InvokeKind) -> str:
    text = load_prompt("system.md")
    match kind:
        case "parse_request":
            return load_prompt("parse.md")
        case "assess_feasibility":
            return text + "\n\n" + load_prompt("feasibility.md")
        case "reassess_commitment":
            return (
                text
                + "\n\n"
                + load_prompt("feasibility.md")
                + "\n\n"
                + load_prompt("escalation.md")
            )
        case "draft_customer_message":
            return text
        case _ as unreachable:
            return _assert_never(unreachable)


def build_investigator(
    kind: InvokeKind,
    *,
    callback_handler: Callable[..., Any] | None = None,
) -> Agent:
    if kind not in {"parse_request", "assess_feasibility", "draft_customer_message"}:
        raise ValueError(f"investigator cannot handle {kind}")
    model = _build_model()
    tools = [] if kind in {"parse_request", "draft_customer_message"} else list(P0_TOOLS)
    return Agent(
        name="investigator",
        description=(
            "Investigates customer requests and returns evidence-backed feasibility assessments."
        ),
        model=model,
        system_prompt=_system_prompt(kind),
        tools=tools,
        callback_handler=callback_handler,
        hooks=[] if kind == "parse_request" else [AuthorityAndTraceHooks()],
    )


def build_monitor(
    *,
    callback_handler: Callable[..., Any] | None = None,
) -> Agent:
    model = _build_model()
    investigator = build_investigator("assess_feasibility", callback_handler=callback_handler)
    return Agent(
        name="monitor",
        description="Monitors approved commitments and escalates only consequential delivery risk.",
        model=model,
        system_prompt=_system_prompt("reassess_commitment"),
        tools=list(P0_TOOLS) + list(WRITE_TOOLS) + [investigator.as_tool(
            name="investigator",
            description=(
                "Delegate evidence-backed feasibility investigation to the Investigator agent."
            ),
        )],
        callback_handler=callback_handler,
        hooks=[AuthorityAndTraceHooks()],
    )


def build_agent(
    kind: InvokeKind,
    *,
    callback_handler: Callable[..., Any] | None = None,
) -> Agent:
    """Backward-compatible entry point that preserves the two-agent boundary."""
    if kind == "reassess_commitment":
        return build_monitor(callback_handler=callback_handler)
    return build_investigator(kind, callback_handler=callback_handler)


def _parse_prompt(raw_text: str) -> str:
    return (
        "Extract a structured customer commitment request from the text.\n"
        "Use ISO dates. Store budget as integer INR rupees (₹4.2 lakh is 420000).\n"
        f"Simulation date: {DEMO_START.date().isoformat()}. "
        "When a date omits its year, use the simulation year.\n"
        "Give the request an id starting with req_. Work item ids start with wi_.\n"
        "If the customer is a known Northstar client, set customer_id "
        "(Acme Foods is cli_acme).\n\n"
        f"Customer text:\n{raw_text}"
    )


def _assess_prompt(request: ParsedRequest, extra: str = "") -> str:
    clock = request.received_at.isoformat()
    payload = request.model_dump_json(indent=2)
    return (
        f"{extra}"
        f"Simulation clock / request received_at: {clock}\n"
        f"request_id: {request.id}\n\n"
        "Investigate this parsed request with tools, then return the structured "
        "feasibility assessment. Pass this request_id to calculate_schedule, "
        "check_conflicts, and find_alternatives.\n\n"
        f"{payload}"
    )


def _structured[T](agent: Agent, prompt: str, model: type[T], attempts: int = 3) -> T:
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            result = agent(
                prompt,
                structured_output_model=model,
                structured_output_prompt=(
                    "Return exactly one valid instance of the requested schema. "
                    "Do not add explanatory prose."
                ),
            )
            output = result.structured_output
            if output is None:
                raise StructuredOutputException("structured_output was empty")
            return output
        except StructuredOutputException as exc:
            last_error = exc
            prompt = prompt + "\n\nReturn valid structured output only. Previous attempt failed."
    raise StructuredOutputException(str(last_error))


def parse_request_text(session: AgentSession, raw_text: str) -> ParsedRequest:
    agent = build_agent("parse_request", callback_handler=None)
    parsed = _structured(agent, _parse_prompt(raw_text), ParsedRequest)
    parsed = ensure_request_id(parsed)
    if not parsed.raw_text:
        parsed = parsed.model_copy(update={"raw_text": raw_text})
    if parsed.received_at.tzinfo is None:
        parsed = parsed.model_copy(update={"received_at": DEMO_START})
    return session.put_request(parsed)


def assess_request(
    session: AgentSession,
    request: ParsedRequest,
    *,
    kind: InvokeKind = "assess_feasibility",
    callback_handler: Callable[..., Any] | None = None,
) -> FeasibilityAssessment:
    session.put_request(request)
    agent = build_investigator(kind, callback_handler=callback_handler)
    try:
        proposed = _structured(agent, _assess_prompt(request), FeasibilityAssessment)
    except StructuredOutputException:
        proposed = FeasibilityAssessment(
            id="asm_failed",
            request_id=request.id,
            decision="UNKNOWN",
            confidence=0.0,
            reasons=[],
            evidence=[],
            constraints=[],
            alternatives=[],
            required_human_decision=True,
            created_at=session.world.clock.now,
        )
    return session.put_assessment(verify_assessment(proposed, session.world, request, session))


def invoke(
    session: AgentSession,
    kind: InvokeKind,
    *,
    prompt: str | None = None,
    request: ParsedRequest | None = None,
    commitment_id: str | None = None,
    callback_handler: Callable[..., Any] | None = None,
) -> ParsedRequest | FeasibilityAssessment | CustomerMessageDraft:
    with use_session(session):
        match kind:
            case "parse_request":
                if not prompt:
                    raise ValueError("parse_request requires prompt")
                return parse_request_text(session, prompt)
            case "assess_feasibility":
                if request is None:
                    raise ValueError("assess_feasibility requires a parsed request")
                return assess_request(
                    session, request, kind=kind, callback_handler=callback_handler
                )
            case "reassess_commitment":
                if commitment_id is None:
                    raise ValueError("reassess_commitment requires commitment_id")
                commitment = next(
                    item for item in session.world.commitments if item.id == commitment_id
                )
                if request is None:
                    request = session.requests.get(commitment.request_id)
                if request is None:
                    raise ValueError("reassess_commitment requires the committed request")
                extra = f"Re-evaluate commitment {commitment_id}.\n\n"
                handoff = session.record_handoff(
                    AgentHandoff(
                        id=new_id("hnd"),
                        source_agent="monitor",
                        target_agent="investigator",
                        kind="reassessment",
                        request_id=request.id,
                        commitment_id=commitment_id,
                        created_at=session.world.clock.now,
                    )
                )
                session.put_request(request)
                agent = build_monitor(callback_handler=callback_handler)
                proposed = _structured(agent, _assess_prompt(request, extra), FeasibilityAssessment)
                assessment = verify_reassessment(
                    proposed, session.world, commitment, request, session
                )
                session.put_assessment(assessment)
                apply_reassessment(session.world, commitment, assessment)
                session.handoffs[-1] = handoff.model_copy(
                    update={"assessment_id": assessment.id, "status": "completed"}
                )
                return assessment
            case "draft_customer_message":
                if not prompt:
                    raise ValueError("draft_customer_message requires prompt")
                agent = build_agent(kind, callback_handler=callback_handler)
                return _structured(agent, prompt, CustomerMessageDraft)
            case _ as unreachable:
                return _assert_never(unreachable)


def pretty_assessment(assessment: FeasibilityAssessment) -> str:
    return json.dumps(assessment.model_dump(mode="json"), indent=2)
