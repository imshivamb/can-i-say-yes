from __future__ import annotations

import re
from datetime import datetime

from adapters.integrations import GmailAdapter
from agent.clock import advance_clock
from agent.session import AgentSession
from domain.models import EmailMessage, WorldEvent


def ingest_email(session: AgentSession, email: EmailMessage) -> WorldEvent | None:
    """Convert one inbound message into an idempotent world event."""
    event_id = f"evt_gmail_{email.id.removeprefix('eml_gmail_')}"
    if any(event.id == event_id for event in session.world.events):
        return None
    lowered = f"{email.subject} {email.body}".lower()
    event_type = "supplier_update" if any(
        word in lowered for word in ("editor", "supplier", "delayed", "slip", "available")
    ) else "message_received"
    available_match = re.search(r"(?:to|from|on)\s+(\d{4}-\d{2}-\d{2})", lowered)
    payload = {"email_id": email.id, "body": email.body}
    if event_type == "supplier_update" and available_match:
        payload.update(
            {
                "supplier_id": "sup_frame_grain",
                "available_from": available_match.group(1),
            }
        )
    event = WorldEvent(
        id=event_id,
        type=event_type,
        occurs_at=email.sent_at,
        source_reference=f"gmail:{email.id}",
        summary=email.subject or "Inbound Gmail message",
        payload=payload,
    )
    session.world.events.append(event)
    session.world.emails.append(email)
    return event


def poll_and_reassess(
    session: AgentSession,
    *,
    query: str = "newer_than:7d",
    now: datetime | None = None,
) -> list[str]:
    """Poll Gmail, ingest new messages, and wake the Monitor once per batch."""
    messages = GmailAdapter().poll(query)
    event_ids: list[str] = []
    for message in messages:
        event = ingest_email(session, message)
        if event is not None:
            event_ids.append(event.id)
    if event_ids:
        target = now or max(
            (event.occurs_at for event in session.world.events if event.id in event_ids),
            default=session.world.clock.now,
        )
        advance_clock(session, target, recorded=True)
    return event_ids

