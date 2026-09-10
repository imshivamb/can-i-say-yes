from __future__ import annotations

from domain.models import Alternative


def rank_alternatives(alternatives: list[Alternative]) -> list[Alternative]:
    """Keep full scope, then avoid extra cost, then prefer the sooner date."""

    def key(alt: Alternative) -> tuple[int, int, int]:
        scope_cut = 0 if alt.kind != "reduced_scope" else 1
        extra = alt.extra_cost.amount
        deadline_ord = alt.new_deadline.toordinal() if alt.new_deadline else 0
        return (scope_cut, extra, deadline_ord)

    return sorted(alternatives, key=key)


def mark_recommended(alternatives: list[Alternative]) -> list[Alternative]:
    feasible = [a for a in alternatives if a.feasible]
    if not feasible:
        return [a.model_copy(update={"recommended": False}) for a in alternatives]
    winner_id = rank_alternatives(feasible)[0].id
    return [a.model_copy(update={"recommended": a.id == winner_id}) for a in alternatives]
