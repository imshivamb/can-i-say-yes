from __future__ import annotations

from datetime import date, datetime
from typing import Never

from domain.clock import ensure_tz
from domain.models import SimulationClock, Supplier, WorldEvent
from domain.world import World


def _assert_never(value: Never) -> Never:
    raise ValueError(f"unhandled event type: {value}")


def due_events(world: World) -> list[WorldEvent]:
    now = ensure_tz(world.clock.now)
    seen: set[str] = set()
    due: list[WorldEvent] = []
    for event in world.events:
        if event.consumed or event.id in seen:
            continue
        if ensure_tz(event.occurs_at) <= now:
            seen.add(event.id)
            due.append(event)
    return due


def apply_event(world: World, event: WorldEvent) -> None:
    """Mutate world facts from a timeline event. Idempotent per field write."""
    match event.type:
        case "supplier_update":
            _apply_supplier_update(world, event)
        case "asset_received":
            _apply_asset_received(world, event)
        case "asset_delayed":
            _apply_asset_delayed(world, event)
        case "customer_scope_change" | "calendar_change" | "capacity_change" | "message_received":
            return
        case _ as unreachable:
            _assert_never(unreachable)


def mark_consumed(world: World, event_id: str) -> None:
    for index, event in enumerate(world.events):
        if event.id == event_id:
            world.events[index] = event.model_copy(update={"consumed": True})
            return


def set_clock(world: World, now: datetime) -> None:
    world.clock = SimulationClock(now=ensure_tz(now), timezone=world.clock.timezone)


def _apply_supplier_update(world: World, event: WorldEvent) -> None:
    supplier_id = event.payload.get("supplier_id")
    raw = event.payload.get("available_from")
    if not supplier_id or not raw:
        return
    available_from = date.fromisoformat(str(raw))
    for index, supplier in enumerate(world.suppliers):
        if supplier.id != supplier_id:
            continue
        updated: Supplier = supplier.model_copy(
            update={"available_from": available_from, "notes": event.summary or supplier.notes}
        )
        world.suppliers[index] = updated
        return


def _apply_asset_received(world: World, event: WorldEvent) -> None:
    asset_id = event.payload.get("asset_id")
    if not asset_id:
        return
    received_on = event.payload.get("received_on")
    for index, asset in enumerate(world.assets):
        if asset.id != asset_id:
            continue
        world.assets[index] = asset.model_copy(
            update={
                "received": True,
                "received_on": (
                    date.fromisoformat(str(received_on))
                    if received_on
                    else world.clock.now.date()
                ),
            }
        )
        return


def _apply_asset_delayed(world: World, event: WorldEvent) -> None:
    asset_id = event.payload.get("asset_id")
    promised_on = event.payload.get("promised_on")
    if not asset_id or not promised_on:
        return
    for index, asset in enumerate(world.assets):
        if asset.id != asset_id:
            continue
        world.assets[index] = asset.model_copy(
            update={"promised_on": date.fromisoformat(str(promised_on))}
        )
        return
