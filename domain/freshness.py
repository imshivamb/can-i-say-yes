from __future__ import annotations

from datetime import datetime, timedelta

from domain.clock import ensure_tz
from domain.enums import EvidenceFreshness
from domain.models import Evidence

FRESH_WITHIN = timedelta(days=7)


def freshness_for(as_of: datetime, now: datetime, superseded: bool = False) -> EvidenceFreshness:
    if superseded:
        return "superseded"
    as_of = ensure_tz(as_of)
    now = ensure_tz(now)
    if now - as_of <= FRESH_WITHIN:
        return "current"
    return "stale"


def mark_superseded(items: list[Evidence]) -> list[Evidence]:
    """Later evidence from the same source_reference supersedes earlier ones."""
    by_source: dict[str, list[Evidence]] = {}
    for item in items:
        by_source.setdefault(item.source_reference, []).append(item)
    superseded_ids: set[str] = set()
    for group in by_source.values():
        ordered = sorted(group, key=lambda e: e.timestamp)
        for earlier in ordered[:-1]:
            superseded_ids.add(earlier.id)
    updated: list[Evidence] = []
    for item in items:
        if item.id in superseded_ids:
            updated.append(item.model_copy(update={"freshness": "superseded"}))
        else:
            updated.append(item)
    return updated
