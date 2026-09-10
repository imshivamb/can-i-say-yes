from datetime import date

from adapters.files.world import load_world
from domain.assess import assess_feasibility
from domain.capacity import utilization_for_skill
from domain.fixtures import acme_campaign_request
from domain.scheduler import calculate_schedule

REQUIRED_CODES = {
    "CAPACITY_OVERALLOCATED",
    "EXISTING_COMMITMENT",
    "MISSING_DEPENDENCY",
    "SUPPLIER_WINDOW",
}


def test_design_utilization_is_82_percent() -> None:
    world = load_world()
    assert abs(utilization_for_skill(world, "design") - 0.82) < 1e-9


def test_acme_sept_18_is_unsafe_with_four_conflicts() -> None:
    world = load_world()
    request = acme_campaign_request()
    assessment = assess_feasibility(world, request)

    assert assessment.decision == "UNSAFE"
    codes = {constraint.code for constraint in assessment.constraints}
    assert REQUIRED_CODES <= codes

    alt_ids = [alt.id for alt in assessment.alternatives]
    assert alt_ids == ["alt_a", "alt_b", "alt_c"]

    recommended = next(alt for alt in assessment.alternatives if alt.recommended)
    assert recommended.id == "alt_a"
    assert recommended.new_deadline == date(2026, 9, 22)
    assert recommended.extra_cost.amount == 0

    option_b = next(alt for alt in assessment.alternatives if alt.id == "alt_b")
    assert option_b.extra_cost.amount == 18000

    option_c = next(alt for alt in assessment.alternatives if alt.id == "alt_c")
    assert option_c.kind == "reduced_scope"

    for reason in assessment.reasons:
        if reason.conflict_code in REQUIRED_CODES:
            assert reason.evidence_ids

    assert abs(assessment.utilization_by_skill["design"] - 0.82) < 1e-9


def test_schedule_is_not_feasible_for_sept_18() -> None:
    world = load_world()
    schedule = calculate_schedule(world, acme_campaign_request())
    assert schedule.feasible_for_deadline is False
    assert schedule.forecast_end is not None
    assert schedule.forecast_end > date(2026, 9, 18)
