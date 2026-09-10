from __future__ import annotations

from domain.models import Commitment, WorldEvent
from domain.scheduler import SKILL_TO_SUPPLIER
from domain.world import World

WATCHED_STATUSES = frozenset({"COMMITTED", "MONITORING", "HUMAN_REVIEW", "REVISED"})


def supplier_used_by_commitment(world: World, commitment: Commitment, supplier_id: str) -> bool:
    try:
        supplier = world.supplier(supplier_id)
    except StopIteration:
        return False
    needed = {SKILL_TO_SUPPLIER.get(item.skill) for item in commitment.work_items}
    return supplier.kind in needed


def event_matches_commitment(event: WorldEvent, commitment: Commitment, world: World) -> bool:
    if commitment.id in event.related_commitment_ids:
        return True
    if event.id in commitment.monitor_event_types:
        return True
    payload = event.payload
    if payload.get("client_id") and payload["client_id"] == commitment.customer_id:
        return True
    supplier_id = payload.get("supplier_id")
    if supplier_id and supplier_used_by_commitment(world, commitment, str(supplier_id)):
        return True
    asset_id = payload.get("asset_id")
    if asset_id and any(str(asset_id) in item.required_asset_ids for item in commitment.work_items):
        return True
    person_id = payload.get("person_id")
    if person_id:
        assigned = set()
        for project in world.projects:
            if project.client_id == commitment.customer_id:
                assigned.update(project.assigned_person_ids)
        if person_id in assigned:
            return True
    return False


def monitors_for_event(world: World, event: WorldEvent) -> list[Commitment]:
    matched: list[Commitment] = []
    for commitment in world.commitments:
        if commitment.status not in WATCHED_STATUSES:
            continue
        if (
            event.type not in commitment.monitor_event_types
            and event.id not in commitment.monitor_event_types
        ):
            continue
        if event_matches_commitment(event, commitment, world):
            matched.append(commitment)
    return matched
