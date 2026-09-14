from __future__ import annotations

from strands import tool

from adapters.integrations import SESAdapter, live_outbound_enabled
from agent.session import current_session
from agent.tools.common import dump, fail, ok, write_tool
from domain.escalation import should_escalate
from domain.ids import new_id
from domain.models import (
    ActivityItem,
    Commitment,
    DecisionOption,
    HumanDecision,
    Money,
    OutboxMessage,
)
from domain.state_machine import transition_commitment

DEFAULT_MONITOR_EVENTS = [
    "supplier_update",
    "customer_scope_change",
    "calendar_change",
    "asset_delayed",
]


@tool
@write_tool("request_human_decision")
def request_human_decision(
    assessment_id: str,
    reason: str,
    recommended_option_id: str | None = None,
    request_id: str | None = None,
    commitment_id: str | None = None,
) -> dict:
    """Create an OPEN decision card from a feasibility assessment.

    Args:
        assessment_id: Assessment that produced alternatives.
        reason: Why a human must choose.
        recommended_option_id: Optional alternative id to highlight.
        request_id: Optional request id.
        commitment_id: Optional existing commitment id.
    """
    session = current_session()
    assessment = session.assessments.get(assessment_id)
    if assessment is None:
        return fail("INVALID_INPUT", f"unknown assessment_id {assessment_id}")
    escalate = should_escalate(
        new_external_promise=commitment_id is None,
        assessment_decision=assessment.decision,
        recovery_changes_terms=bool(assessment.alternatives),
    )
    if not escalate and assessment.decision == "SAFE":
        return fail("NO_ESCALATION", "assessment does not require a human decision")
    options = [
        DecisionOption(
            id=item.id,
            title=item.title,
            summary=item.summary,
            extra_cost=item.extra_cost,
            recommended=item.recommended,
        )
        for item in assessment.alternatives
    ]
    recommended = recommended_option_id or next(
        (item.id for item in assessment.alternatives if item.recommended),
        None,
    )
    decision = HumanDecision(
        id=new_id("dec"),
        commitment_id=commitment_id,
        request_id=request_id or assessment.request_id,
        assessment_id=assessment.id,
        reason=reason,
        options=options,
        recommended_option_id=recommended,
        evidence_ids=[item.id for item in assessment.evidence],
        created_at=session.world.clock.now,
        status="OPEN",
    )
    session.decisions[decision.id] = decision
    return ok(decision=dump(decision))


@tool
@write_tool("create_commitment")
def create_commitment(
    request_id: str,
    assessment_id: str,
    decision_id: str,
    alternative_id: str,
) -> dict:
    """Persist an approved commitment. Requires a matching APPROVED human decision.

    Args:
        request_id: Parsed request id.
        assessment_id: Assessment id.
        decision_id: Approved decision id.
        alternative_id: Chosen alternative id (must match the decision).
    """
    session = current_session()
    request = session.requests.get(request_id)
    assessment = session.assessments.get(assessment_id)
    if request is None or assessment is None:
        return fail("INVALID_INPUT", "unknown request or assessment")
    alternative = next(
        (item for item in assessment.alternatives if item.id == alternative_id),
        None,
    )
    if alternative is None:
        return fail("INVALID_INPUT", f"unknown alternative_id {alternative_id}")
    now = session.world.clock.now
    commitment = Commitment(
        id=new_id("cmt"),
        request_id=request.id,
        assessment_id=assessment.id,
        customer_id=request.customer_id or "cli_unknown",
        customer_name=request.customer_name,
        title=request.scope_summary,
        scope_summary=request.scope_summary,
        work_items=list(request.work_items),
        original_deadline=request.deadline,
        committed_deadline=alternative.new_deadline or request.deadline,
        current_forecast=alternative.forecast_end,
        budget=request.budget,
        extra_cost=alternative.extra_cost or Money(amount=0),
        status=transition_commitment("APPROVED", "COMMITTED"),
        approved_alternative_id=alternative.id,
        created_at=now,
        updated_at=now,
    )
    session.world.commitments.append(commitment)
    decision = session.decisions[decision_id]
    session.decisions[decision_id] = decision.model_copy(update={"commitment_id": commitment.id})
    session.activity.append(
        ActivityItem(
            id=new_id("aud"),
            timestamp=now,
            text=(
                f"Created commitment for {commitment.customer_name} "
                f"due {commitment.committed_deadline}"
            ),
            commitment_id=commitment.id,
        )
    )
    return ok(commitment=dump(commitment), commitment_id=commitment.id)


@tool
@write_tool("monitor_commitment")
def monitor_commitment(
    commitment_id: str,
    event_types: list[str] | None = None,
) -> dict:
    """Register which world events should wake re-evaluation for a commitment.

    Args:
        commitment_id: Commitment to watch.
        event_types: Event types to subscribe to.
    """
    session = current_session()
    index, commitment = next(
        (i, item)
        for i, item in enumerate(session.world.commitments)
        if item.id == commitment_id
    )
    types = event_types or DEFAULT_MONITOR_EVENTS
    updated = commitment.model_copy(
        update={
            "status": transition_commitment(commitment.status, "MONITORING"),
            "health": "ON_TRACK",
            "monitor_event_types": types,
            "updated_at": session.world.clock.now,
        }
    )
    session.world.commitments[index] = updated
    session.activity.append(
        ActivityItem(
            id=new_id("aud"),
            timestamp=session.world.clock.now,
            text=f"Monitoring {updated.customer_name} · {updated.health}",
            commitment_id=updated.id,
        )
    )
    return ok(commitment=dump(updated))


@tool
@write_tool("send_customer_message")
def send_customer_message(
    commitment_id: str,
    to: str,
    subject: str,
    body: str,
    decision_id: str,
) -> dict:
    """Send or queue a customer-facing message after human approval.

    The body may only confirm terms the human already approved.

    Args:
        commitment_id: Commitment this message is about.
        to: Customer address in the simulation.
        subject: Subject line.
        body: Message body.
        decision_id: Approved decision that authorized this promise.
    """
    session = current_session()
    commitment = next(item for item in session.world.commitments if item.id == commitment_id)
    message = OutboxMessage(
        id=new_id("eml"),
        commitment_id=commitment.id,
        to=to,
        subject=subject,
        body=body,
        decision_id=decision_id,
        sent_at=session.world.clock.now,
    )
    delivery = {"provider": "local_outbox", "status": "queued"}
    if live_outbound_enabled():
        try:
            result = SESAdapter().send(to=to, subject=subject, body=body)
            delivery = {
                "provider": result.provider,
                "message_id": result.message_id,
                "status": result.status,
            }
        except (OSError, ValueError, KeyError) as exc:
            return fail("DELIVERY_UNAVAILABLE", f"SES delivery unavailable: {exc}")
    session.outbox.append(message)
    session.activity.append(
        ActivityItem(
            id=new_id("aud"),
            timestamp=session.world.clock.now,
            text=(
                f"{'Sent' if delivery['status'] == 'sent' else 'Queued'} "
                f"customer message to {to}"
            ),
            commitment_id=commitment.id,
        )
    )
    return ok(message=dump(message), delivery=delivery)
