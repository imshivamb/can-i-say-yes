from __future__ import annotations

from domain.enums import CommitmentHealth, DecisionOutcome


def should_escalate(
    *,
    new_external_promise: bool = False,
    health: CommitmentHealth | None = None,
    assessment_decision: DecisionOutcome | None = None,
    recovery_changes_terms: bool = False,
    authority_boundary: bool = False,
    on_track_internal_update: bool = False,
) -> bool:
    """Open or keep a human decision only when a real choice is required."""
    if on_track_internal_update:
        return False
    if new_external_promise:
        return True
    if health in {"AT_RISK", "BLOCKED", "FAILED"}:
        return True
    if assessment_decision == "UNKNOWN":
        return True
    if recovery_changes_terms:
        return True
    if authority_boundary:
        return True
    return False
