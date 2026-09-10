from __future__ import annotations

from datetime import datetime

from agent.human import open_decision
from agent.offline import run_recorded_reassessment
from agent.session import AgentSession
from domain.clock import resolve_clock_target
from domain.events import apply_event, due_events, mark_consumed, set_clock
from domain.ids import new_id
from domain.models import ActivityItem, HumanDecision
from domain.monitor import monitors_for_event


def _has_open_decision(session: AgentSession, commitment_id: str) -> bool:
    return any(
        item.commitment_id == commitment_id and item.status == "OPEN"
        for item in session.decisions.values()
    )


def advance_clock(
    session: AgentSession,
    target: str | datetime,
    *,
    recorded: bool = True,
) -> list[HumanDecision]:
    """Set the simulation clock, consume due events, and reassess matched monitors."""
    del recorded
    set_clock(session.world, resolve_clock_target(target))
    opened: list[HumanDecision] = []
    for event in due_events(session.world):
        apply_event(session.world, event)
        affected = monitors_for_event(session.world, event)
        if not affected:
            session.activity.append(
                ActivityItem(
                    id=new_id("aud"),
                    timestamp=session.world.clock.now,
                    text=f"Checked {event.id}; no monitored commitment matched",
                )
            )
            mark_consumed(session.world, event.id)
            continue
        for commitment in affected:
            assessment = run_recorded_reassessment(session, commitment.id, event.id)
            updated = next(item for item in session.world.commitments if item.id == commitment.id)
            session.activity.append(
                ActivityItem(
                    id=new_id("aud"),
                    timestamp=session.world.clock.now,
                    text=f"Re-evaluated {updated.customer_name} · {updated.health}",
                    commitment_id=updated.id,
                )
            )
            if assessment.required_human_decision and not _has_open_decision(session, updated.id):
                decision = open_decision(
                    session,
                    assessment,
                    reason=(
                        f"{updated.customer_name} is {updated.health}: forecast "
                        f"{updated.current_forecast} vs committed {updated.committed_deadline}"
                    ),
                    commitment_id=updated.id,
                )
                opened.append(decision)
        mark_consumed(session.world, event.id)
    session.persist()
    return opened
