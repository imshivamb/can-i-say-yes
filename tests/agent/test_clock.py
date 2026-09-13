from datetime import date
from pathlib import Path

import agent.clock as clock_module
from adapters.files.store import read_runtime, read_seed_commitment_ids
from adapters.files.world import DATA_ROOT, load_world
from agent.clock import advance_clock
from agent.human import approve_decision, fulfill_approved_option, open_decision
from agent.offline import run_recorded_investigation, run_recorded_reassessment
from agent.session import AgentSession


def _session(tmp_path: Path) -> AgentSession:
    return AgentSession(
        world=load_world(),
        data_root=tmp_path,
        seed_commitment_ids=read_seed_commitment_ids(DATA_ROOT),
    )


def _approve_option_a(session: AgentSession) -> None:
    assessment = run_recorded_investigation(session)
    decision = open_decision(session, assessment, reason="Original date is unsafe.")
    approve_decision(session, decision.id, "alt_a")
    fulfill_approved_option(session, decision.id)


def test_advance_supplier_delay_opens_at_risk_decision(tmp_path: Path) -> None:
    session = _session(tmp_path)
    _approve_option_a(session)
    first_decision_ids = set(session.decisions)
    opened = advance_clock(session, "supplier_delay")

    assert session.world.clock.now.isoformat() == "2026-09-19T10:00:00+05:30"
    assert session.world.supplier("sup_frame_grain").available_from == date(2026, 9, 20)
    event = next(item for item in session.world.events if item.id == "evt_supplier_delay")
    assert event.consumed is True

    acme = next(item for item in session.world.commitments if item.request_id == "req_acme_001")
    assert acme.health == "AT_RISK"
    assert acme.current_forecast == date(2026, 9, 23)
    assert acme.status == "HUMAN_REVIEW"
    assert len(opened) == 1
    assert opened[0].id not in first_decision_ids
    assert opened[0].recommended_option_id == "alt_backup"
    recommended = next(item for item in opened[0].options if item.recommended)
    assert recommended.extra_cost.amount == 18000

    runtime = read_runtime(tmp_path)
    assert any(item.id == opened[0].id and item.status == "OPEN" for item in runtime.decisions)
    assert any(item.id == "evt_supplier_delay" and item.consumed for item in runtime.events)


def test_second_advance_does_not_open_another_decision(tmp_path: Path) -> None:
    session = _session(tmp_path)
    _approve_option_a(session)
    first = advance_clock(session, "supplier_delay")
    second = advance_clock(session, "supplier_delay")
    assert len(first) == 1
    assert second == []


def test_plus_three_days_stays_quiet(tmp_path: Path) -> None:
    session = _session(tmp_path)
    _approve_option_a(session)
    opened = advance_clock(session, "plus_3_days")
    assert opened == []
    acme = next(item for item in session.world.commitments if item.request_id == "req_acme_001")
    assert acme.health == "ON_TRACK"
    event = next(item for item in session.world.events if item.id == "evt_supplier_delay")
    assert event.consumed is False


def test_live_monitor_path_is_selected_when_recording_is_off(
    tmp_path: Path, monkeypatch
) -> None:
    session = _session(tmp_path)
    _approve_option_a(session)
    calls: list[tuple[str, str]] = []

    def fake_invoke(
        current_session: AgentSession,
        kind: str,
        *,
        commitment_id: str | None = None,
        **_: object,
    ):
        calls.append((kind, commitment_id or ""))
        return run_recorded_reassessment(current_session, commitment_id or "", "evt_supplier_delay")

    monkeypatch.setattr(clock_module, "invoke", fake_invoke)
    advance_clock(session, "supplier_delay", recorded=False)

    acme = next(item for item in session.world.commitments if item.request_id == "req_acme_001")
    assert calls == [("reassess_commitment", acme.id)]
