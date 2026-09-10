from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from domain.enums import Authorization
from domain.models import Commitment, HumanDecision

READ_TOOLS = frozenset(
    {
        "search_email",
        "search_documents",
        "get_project_state",
        "get_capacity",
        "get_commitments",
        "get_supplier_status",
        "get_calendar",
        "get_dependencies",
    }
)
DOMAIN_TOOLS = frozenset({"calculate_schedule", "check_conflicts", "find_alternatives"})


@dataclass(frozen=True)
class PolicyContext:
    now: datetime
    decisions: list[HumanDecision]
    commitments: list[Commitment]


def authorize(tool: str, args: dict[str, Any], context: PolicyContext) -> Authorization:
    """The LLM proposes. This function permits."""
    match tool:
        case name if name in READ_TOOLS or name in DOMAIN_TOOLS:
            return "allow"
        case "request_human_decision":
            return "allow"
        case "monitor_commitment":
            return "allow" if _commitment_exists(args.get("commitment_id"), context) else "deny"
        case "create_commitment":
            return "allow" if _create_commitment_permitted(args, context) else "require_human"
        case "send_customer_message":
            return "allow" if _send_message_permitted(args, context) else "require_human"
        case "cancel_commitment":
            return "deny"
        case "bash" | "shell":
            return "deny"
        case _:
            return "deny"


def _commitment_exists(commitment_id: str | None, context: PolicyContext) -> bool:
    if not commitment_id:
        return False
    return any(item.id == commitment_id for item in context.commitments)


def _active_commitment_for_request(request_id: str, context: PolicyContext) -> bool:
    return any(
        item.request_id == request_id and item.status not in {"CANCELLED", "REJECTED"}
        for item in context.commitments
    )


def _decision_by_id(decision_id: str | None, context: PolicyContext) -> HumanDecision | None:
    if not decision_id:
        return None
    return next((item for item in context.decisions if item.id == decision_id), None)


def _not_expired(decision: HumanDecision, now: datetime) -> bool:
    return decision.expires_at is None or now < decision.expires_at


def _create_commitment_permitted(args: dict[str, Any], context: PolicyContext) -> bool:
    decision = _decision_by_id(args.get("decision_id"), context)
    if decision is None:
        return False
    request_id = args.get("request_id")
    return (
        decision.status == "APPROVED"
        and decision.chosen_option_id == args.get("alternative_id")
        and decision.request_id == request_id
        and _not_expired(decision, context.now)
        and not _active_commitment_for_request(str(request_id), context)
    )


def _send_message_permitted(args: dict[str, Any], context: PolicyContext) -> bool:
    decision = _decision_by_id(args.get("decision_id"), context)
    if decision is None or decision.status != "APPROVED":
        return False
    if not _not_expired(decision, context.now):
        return False
    commitment_id = args.get("commitment_id")
    commitment = next((item for item in context.commitments if item.id == commitment_id), None)
    if commitment is None:
        return False
    if decision.commitment_id and decision.commitment_id != commitment.id:
        return False
    if decision.request_id and decision.request_id != commitment.request_id:
        return False
    return True
