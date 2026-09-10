import pytest

from domain.exceptions import InvalidTransitionError
from domain.state_machine import (
    can_transition_commitment,
    can_transition_decision,
    transition_commitment,
    transition_decision,
)


def test_happy_path_commitment_lifecycle() -> None:
    status = "DRAFT"
    for nxt in ("ASSESSED", "APPROVED", "COMMITTED", "MONITORING"):
        status = transition_commitment(status, nxt)
    status = transition_commitment(status, "HUMAN_REVIEW")
    status = transition_commitment(status, "REVISED")
    status = transition_commitment(status, "MONITORING")
    status = transition_commitment(status, "FULFILLED")
    assert status == "FULFILLED"


def test_assessed_can_be_rejected() -> None:
    assert transition_commitment("ASSESSED", "REJECTED") == "REJECTED"


def test_illegal_commitment_transition_raises() -> None:
    with pytest.raises(InvalidTransitionError):
        transition_commitment("DRAFT", "COMMITTED")


def test_monitoring_may_self_transition() -> None:
    assert can_transition_commitment("MONITORING", "MONITORING")


def test_terminal_commitment_cannot_move() -> None:
    for status in ("REJECTED", "CANCELLED", "FULFILLED", "FAILED"):
        assert not can_transition_commitment(status, "MONITORING")


def test_decision_lifecycle() -> None:
    assert transition_decision("OPEN", "APPROVED") == "APPROVED"
    with pytest.raises(InvalidTransitionError):
        transition_decision("APPROVED", "REJECTED")


def test_open_decision_can_expire() -> None:
    assert can_transition_decision("OPEN", "EXPIRED")
