from datetime import datetime, timedelta

from agent.policies.authorization import PolicyContext, authorize
from domain.clock import DEMO_START
from domain.models import Commitment, HumanDecision, Money


def _context(
    *,
    decisions: list[HumanDecision] | None = None,
    commitments: list[Commitment] | None = None,
    now: datetime | None = None,
) -> PolicyContext:
    return PolicyContext(
        now=now or DEMO_START,
        decisions=decisions or [],
        commitments=commitments or [],
    )


def _decision(**overrides: object) -> HumanDecision:
    base = HumanDecision(
        id="dec_001",
        request_id="req_acme_001",
        assessment_id="asm_001",
        reason="unsafe as asked",
        options=[],
        created_at=DEMO_START,
        status="APPROVED",
        chosen_option_id="alt_a",
    )
    return base.model_copy(update=overrides)


def _commitment(**overrides: object) -> Commitment:
    base = Commitment(
        id="cmt_001",
        request_id="req_acme_001",
        assessment_id="asm_001",
        customer_id="cli_acme",
        customer_name="Acme Foods",
        title="September campaign package",
        scope_summary="September campaign package",
        work_items=[],
        original_deadline=DEMO_START.date(),
        committed_deadline=DEMO_START.date(),
        extra_cost=Money(amount=0),
        status="COMMITTED",
        created_at=DEMO_START,
        updated_at=DEMO_START,
    )
    return base.model_copy(update=overrides)


def test_read_and_domain_tools_are_allowed() -> None:
    context = _context()
    assert authorize("get_capacity", {}, context) == "allow"
    assert authorize("calculate_schedule", {"request_id": "req_acme_001"}, context) == "allow"


def test_request_human_decision_is_allowed() -> None:
    assert authorize("request_human_decision", {"assessment_id": "asm_001"}, _context()) == "allow"


def test_create_commitment_requires_matching_approval() -> None:
    args = {
        "request_id": "req_acme_001",
        "assessment_id": "asm_001",
        "decision_id": "dec_001",
        "alternative_id": "alt_a",
    }
    assert authorize("create_commitment", args, _context()) == "require_human"
    approved = _decision()
    assert authorize("create_commitment", args, _context(decisions=[approved])) == "allow"


def test_create_commitment_denied_when_option_or_request_mismatch() -> None:
    args = {
        "request_id": "req_acme_001",
        "assessment_id": "asm_001",
        "decision_id": "dec_001",
        "alternative_id": "alt_b",
    }
    assert (
        authorize("create_commitment", args, _context(decisions=[_decision()])) == "require_human"
    )


def test_create_commitment_denied_when_expired_or_already_committed() -> None:
    args = {
        "request_id": "req_acme_001",
        "assessment_id": "asm_001",
        "decision_id": "dec_001",
        "alternative_id": "alt_a",
    }
    expired = _decision(expires_at=DEMO_START - timedelta(minutes=1))
    assert authorize("create_commitment", args, _context(decisions=[expired])) == "require_human"
    existing = _commitment()
    assert (
        authorize(
            "create_commitment",
            args,
            _context(decisions=[_decision()], commitments=[existing]),
        )
        == "require_human"
    )


def test_send_customer_message_requires_approved_matching_commitment() -> None:
    args = {
        "commitment_id": "cmt_001",
        "to": "priya@acmefoods.example",
        "subject": "Update",
        "body": "Due 22 September 2026. ₹0 extra.",
        "decision_id": "dec_001",
    }
    assert authorize("send_customer_message", args, _context()) == "require_human"
    decision = _decision(commitment_id="cmt_001")
    commitment = _commitment()
    assert (
        authorize(
            "send_customer_message",
            args,
            _context(decisions=[decision], commitments=[commitment]),
        )
        == "allow"
    )


def test_monitor_requires_existing_commitment() -> None:
    assert authorize("monitor_commitment", {"commitment_id": "cmt_missing"}, _context()) == "deny"
    assert (
        authorize(
            "monitor_commitment",
            {"commitment_id": "cmt_001"},
            _context(commitments=[_commitment()]),
        )
        == "allow"
    )


def test_shell_and_unknown_tools_are_denied() -> None:
    context = _context()
    assert authorize("bash", {"command": "ls"}, context) == "deny"
    assert authorize("cancel_commitment", {"commitment_id": "cmt_001"}, context) == "deny"
    assert authorize("invented_tool", {}, context) == "deny"
