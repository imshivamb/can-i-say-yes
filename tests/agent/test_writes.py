from datetime import date
from pathlib import Path

import pytest

from adapters.files.store import read_runtime, read_seed_commitment_ids
from adapters.files.world import DATA_ROOT, load_world
from agent.human import approve_decision, fulfill_approved_option, open_decision
from agent.offline import run_recorded_investigation
from agent.session import AgentSession, use_session
from agent.tools.writes import create_commitment


def _session(tmp_path: Path) -> AgentSession:
    return AgentSession(
        world=load_world(),
        data_root=tmp_path,
        seed_commitment_ids=read_seed_commitment_ids(DATA_ROOT),
    )


def test_create_commitment_without_decision_does_not_persist(tmp_path: Path) -> None:
    session = _session(tmp_path)
    assessment = run_recorded_investigation(session)
    before = {item.id for item in session.world.commitments}
    with use_session(session):
        result = create_commitment(
            request_id=assessment.request_id,
            assessment_id=assessment.id,
            decision_id="dec_missing",
            alternative_id="alt_a",
        )
    assert result["ok"] is False
    assert result["error_code"] == "DENIED"
    assert {item.id for item in session.world.commitments} == before
    runtime = read_runtime(tmp_path)
    assert runtime.commitments == []
    assert any(item.result_status == "denied" for item in session.audit)


def test_approve_option_a_persists_sept_22_commitment_and_outbox(tmp_path: Path) -> None:
    session = _session(tmp_path)
    assessment = run_recorded_investigation(session)
    decision = open_decision(
        session,
        assessment,
        reason="Original Sept 18 date is unsafe.",
    )
    approve_decision(session, decision.id, "alt_a")
    fulfill_approved_option(session, decision.id)

    created = [
        item for item in session.world.commitments if item.request_id == assessment.request_id
    ]
    assert len(created) == 1
    commitment = created[0]
    assert commitment.committed_deadline == date(2026, 9, 22)
    assert commitment.status == "MONITORING"
    assert commitment.health == "ON_TRACK"
    assert commitment.approved_alternative_id == "alt_a"
    assert commitment.extra_cost.amount == 0
    assert session.outbox
    message = session.outbox[-1]
    assert message.to == "priya@acmefoods.example"
    assert message.commitment_id == commitment.id
    assert "22 September 2026" in message.body
    assert "₹0" in message.body

    runtime = read_runtime(tmp_path)
    assert any(item.id == commitment.id for item in runtime.commitments)
    assert runtime.outbox
    assert runtime.outbox[-1].body == message.body
    assert any(
        item.status == "APPROVED" and item.chosen_option_id == "alt_a"
        for item in runtime.decisions
    )


def test_approve_queues_local_outbox_when_live_without_ses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CISAY_LIVE_INTEGRATIONS", "1")
    monkeypatch.delenv("SES_FROM_ADDRESS", raising=False)
    session = _session(tmp_path)
    assessment = run_recorded_investigation(session)
    decision = open_decision(
        session,
        assessment,
        reason="Original Sept 18 date is unsafe.",
    )
    approve_decision(session, decision.id, "alt_a")
    fulfill_approved_option(session, decision.id)
    assert session.outbox[-1].to == "priya@acmefoods.example"
