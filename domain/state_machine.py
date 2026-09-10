from __future__ import annotations

from typing import Never

from domain.enums import CommitmentStatus, DecisionStatus
from domain.exceptions import InvalidTransitionError

COMMITMENT_TRANSITIONS: dict[CommitmentStatus, frozenset[CommitmentStatus]] = {
    "DRAFT": frozenset({"ASSESSED"}),
    "ASSESSED": frozenset({"APPROVED", "REJECTED"}),
    "APPROVED": frozenset({"COMMITTED"}),
    "REJECTED": frozenset(),
    "COMMITTED": frozenset({"MONITORING"}),
    "MONITORING": frozenset({"MONITORING", "HUMAN_REVIEW", "FULFILLED", "FAILED"}),
    "HUMAN_REVIEW": frozenset({"REVISED", "CANCELLED"}),
    "REVISED": frozenset({"MONITORING"}),
    "CANCELLED": frozenset(),
    "FULFILLED": frozenset(),
    "FAILED": frozenset(),
}

DECISION_TRANSITIONS: dict[DecisionStatus, frozenset[DecisionStatus]] = {
    "OPEN": frozenset({"APPROVED", "REJECTED", "CHOSEN_OTHER", "EXPIRED"}),
    "APPROVED": frozenset(),
    "REJECTED": frozenset(),
    "CHOSEN_OTHER": frozenset(),
    "EXPIRED": frozenset(),
}


def _assert_never(value: Never) -> Never:
    raise InvalidTransitionError(f"unhandled status: {value}")


def _known_commitment_status(status: CommitmentStatus) -> CommitmentStatus:
    match status:
        case (
            "DRAFT"
            | "ASSESSED"
            | "APPROVED"
            | "REJECTED"
            | "COMMITTED"
            | "MONITORING"
            | "HUMAN_REVIEW"
            | "REVISED"
            | "CANCELLED"
            | "FULFILLED"
            | "FAILED"
        ):
            return status
        case _ as unreachable:
            return _assert_never(unreachable)


def _known_decision_status(status: DecisionStatus) -> DecisionStatus:
    match status:
        case "OPEN" | "APPROVED" | "REJECTED" | "CHOSEN_OTHER" | "EXPIRED":
            return status
        case _ as unreachable:
            return _assert_never(unreachable)


def can_transition_commitment(current: CommitmentStatus, target: CommitmentStatus) -> bool:
    current = _known_commitment_status(current)
    target = _known_commitment_status(target)
    return target in COMMITMENT_TRANSITIONS[current]


def transition_commitment(current: CommitmentStatus, target: CommitmentStatus) -> CommitmentStatus:
    if not can_transition_commitment(current, target):
        raise InvalidTransitionError(f"cannot transition commitment {current} → {target}")
    return target


def can_transition_decision(current: DecisionStatus, target: DecisionStatus) -> bool:
    current = _known_decision_status(current)
    target = _known_decision_status(target)
    return target in DECISION_TRANSITIONS[current]


def transition_decision(current: DecisionStatus, target: DecisionStatus) -> DecisionStatus:
    if not can_transition_decision(current, target):
        raise InvalidTransitionError(f"cannot transition decision {current} → {target}")
    return target
