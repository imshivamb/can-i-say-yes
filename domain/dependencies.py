from __future__ import annotations

from datetime import date

from domain.clock import next_working_day
from domain.models import CustomerAsset, WorkItem
from domain.world import World


def missing_assets(world: World, work_items: list[WorkItem]) -> list[CustomerAsset]:
    missing: list[CustomerAsset] = []
    seen: set[str] = set()
    for item in work_items:
        for asset_id in item.required_asset_ids:
            if asset_id in seen:
                continue
            seen.add(asset_id)
            asset = world.asset(asset_id)
            if asset.required and not asset.received:
                missing.append(asset)
    return missing


def asset_ready_date(asset: CustomerAsset, today: date) -> date | None:
    """Earliest date the asset can unblock work.

    Received assets are ready on received_on or today.
    Unreceived assets with a future promise use that date.
    Unreceived assets whose promise is already late are treated as
    arriving two working days from today — a conservative slip, not a guess
    that they are here now.
    """
    if asset.received:
        return asset.received_on or today
    if asset.promised_on and asset.promised_on > today:
        return asset.promised_on
    ready = today
    for _ in range(2):
        ready = next_working_day(ready)
    return ready


def earliest_item_start(
    world: World,
    item: WorkItem,
    today: date,
    supplier_available_from: date | None,
) -> date:
    start = today
    for asset_id in item.required_asset_ids:
        asset = world.asset(asset_id)
        ready = asset_ready_date(asset, today)
        if ready and ready > start:
            start = ready
    if supplier_available_from and supplier_available_from > start:
        start = supplier_available_from
    return start
