from __future__ import annotations

from agent.session import AgentSession
from domain.assess import assess_feasibility
from domain.models import Commitment, FeasibilityAssessment, ParsedRequest
from domain.reassess import assess_commitment
from domain.world import World


def verify_assessment(
    proposed: FeasibilityAssessment,
    world: World,
    request: ParsedRequest,
    session: AgentSession,
) -> FeasibilityAssessment:
    """Deterministic layer wins on decision, constraints, and alternatives.

    The LLM may write reasons. It may not manufacture SAFE.
    """
    truth = assess_feasibility(world, request)
    merged_evidence = {item.id: item for item in truth.evidence}
    seen_refs = {item.source_reference for item in truth.evidence}
    for item in session.evidence:
        if item.id in merged_evidence or item.source_reference in seen_refs:
            continue
        merged_evidence[item.id] = item
        seen_refs.add(item.source_reference)
    evidence = list(merged_evidence.values())
    known_ids = set(merged_evidence)
    grounded_reasons = [
        reason
        for reason in proposed.reasons
        if reason.evidence_ids and all(eid in known_ids for eid in reason.evidence_ids)
    ]
    reasons = grounded_reasons or truth.reasons
    if truth.decision == "UNSAFE":
        decision = "UNSAFE"
        alternatives = truth.alternatives
        constraints = truth.constraints
        required_human = True
    elif proposed.decision == "SAFE" and truth.decision != "SAFE":
        decision = truth.decision
        alternatives = truth.alternatives
        constraints = truth.constraints
        required_human = True
    else:
        decision = proposed.decision
        alternatives = proposed.alternatives or truth.alternatives
        constraints = proposed.constraints or truth.constraints
        required_human = proposed.required_human_decision or truth.required_human_decision

    return truth.model_copy(
        update={
            "decision": decision,
            "reasons": reasons,
            "evidence": evidence,
            "constraints": constraints,
            "alternatives": alternatives,
            "required_human_decision": required_human,
            "forecast_end": truth.forecast_end,
            "utilization_by_skill": truth.utilization_by_skill,
        }
    )


def verify_reassessment(
    proposed: FeasibilityAssessment,
    world: World,
    commitment: Commitment,
    request: ParsedRequest,
    session: AgentSession,
) -> FeasibilityAssessment:
    """Domain forecast and health win. The model cannot manufacture ON_TRACK."""
    truth = assess_commitment(world, commitment, request)
    merged_evidence = {item.id: item for item in truth.evidence}
    seen_refs = {item.source_reference for item in truth.evidence}
    for item in session.evidence:
        if item.id in merged_evidence or item.source_reference in seen_refs:
            continue
        merged_evidence[item.id] = item
        seen_refs.add(item.source_reference)
    grounded = [
        reason
        for reason in proposed.reasons
        if reason.evidence_ids and all(eid in merged_evidence for eid in reason.evidence_ids)
    ]
    return truth.model_copy(
        update={
            "reasons": grounded or truth.reasons,
            "evidence": list(merged_evidence.values()),
            "required_human_decision": truth.required_human_decision,
            "forecast_end": truth.forecast_end,
            "alternatives": truth.alternatives,
            "decision": truth.decision,
        }
    )
