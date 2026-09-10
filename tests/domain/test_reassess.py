from datetime import date

from adapters.files.world import load_world
from domain.clock import NAMED_JUMPS
from domain.events import apply_event, due_events, set_clock
from domain.fixtures import acme_campaign_request
from domain.models import Commitment, Money
from domain.monitor import monitors_for_event
from domain.reassess import assess_commitment, forecast_commitment, health_for_forecast


def _acme_commitment(world) -> Commitment:
    request = acme_campaign_request()
    return Commitment(
        id="cmt_acme_test",
        request_id=request.id,
        assessment_id="asm_test",
        customer_id="cli_acme",
        customer_name="Acme Foods",
        title="September campaign package",
        scope_summary="September campaign package",
        work_items=list(request.work_items),
        original_deadline=date(2026, 9, 18),
        committed_deadline=date(2026, 9, 22),
        current_forecast=date(2026, 9, 22),
        extra_cost=Money(amount=0),
        status="MONITORING",
        health="ON_TRACK",
        monitor_event_types=[
            "supplier_update",
            "customer_scope_change",
            "calendar_change",
            "asset_delayed",
        ],
        created_at=world.clock.now,
        updated_at=world.clock.now,
    )


def test_supplier_delay_forecast_is_sept_23() -> None:
    world = load_world()
    commitment = _acme_commitment(world)
    world.commitments.append(commitment)
    set_clock(world, NAMED_JUMPS["supplier_delay"])
    event = next(item for item in due_events(world) if item.id == "evt_supplier_delay")
    apply_event(world, event)
    assert world.supplier("sup_frame_grain").available_from == date(2026, 9, 20)
    forecast = forecast_commitment(world, commitment)
    assert forecast == date(2026, 9, 23)
    assert health_for_forecast(forecast, commitment.committed_deadline) == "AT_RISK"


def test_supplier_delay_matches_acme_not_bloom() -> None:
    world = load_world()
    acme = _acme_commitment(world)
    world.commitments.append(acme)
    event = next(item for item in world.events if item.id == "evt_supplier_delay")
    matched = {item.id for item in monitors_for_event(world, event)}
    assert acme.id in matched
    assert "cmt_bloom_festive" not in matched


def test_recovery_assessment_recommends_backup_editor() -> None:
    world = load_world()
    commitment = _acme_commitment(world)
    world.commitments.append(commitment)
    set_clock(world, NAMED_JUMPS["supplier_delay"])
    apply_event(world, next(item for item in due_events(world) if item.id == "evt_supplier_delay"))
    assessment = assess_commitment(world, commitment, acme_campaign_request())
    assert assessment.decision == "UNSAFE"
    assert assessment.forecast_end == date(2026, 9, 23)
    assert assessment.required_human_decision is True
    recommended = next(item for item in assessment.alternatives if item.recommended)
    assert recommended.id == "alt_backup"
    assert recommended.extra_cost.amount == 18000
