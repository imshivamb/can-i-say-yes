from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import BaseModel, TypeAdapter

from domain.clock import default_clock
from domain.models import (
    CalendarEvent,
    Client,
    Commitment,
    CustomerAsset,
    Document,
    EmailMessage,
    Person,
    Project,
    SimulationClock,
    Supplier,
    WorldEvent,
)
from domain.world import World

DATA_ROOT = Path(os.getenv("CISAY_DATA_DIR") or Path(__file__).resolve().parents[2] / "data")


def _read_list[T: BaseModel](path: Path, model: type[T]) -> list[T]:
    if not path.exists():
        return []
    raw = json.loads(path.read_text())
    return TypeAdapter(list[model]).validate_python(raw)


def _read_clock(path: Path) -> SimulationClock:
    if not path.exists():
        return default_clock()
    return SimulationClock.model_validate_json(path.read_text())


def _overlay[T: BaseModel](seed: list[T], runtime: list[T]) -> list[T]:
    if not runtime:
        return seed
    by_id = {item.id: item for item in seed}
    for item in runtime:
        by_id[item.id] = item
    return list(by_id.values())


def _merge_commitments(root: Path) -> list[Commitment]:
    seed = _read_list(root / "projects" / "commitments.json", Commitment)
    runtime = _read_list(root / "runtime" / "commitments.json", Commitment)
    seen = {item.id for item in seed}
    return seed + [item for item in runtime if item.id not in seen]


def load_world(root: Path | None = None) -> World:
    root = root or DATA_ROOT
    runtime = root / "runtime"
    return World(
        clock=_read_clock(runtime / "clock.json"),
        people=_read_list(root / "company" / "people.json", Person),
        clients=_read_list(root / "company" / "clients.json", Client),
        calendar=_read_list(root / "company" / "calendar.json", CalendarEvent),
        projects=_read_list(root / "projects" / "projects.json", Project),
        suppliers=_overlay(
            _read_list(root / "suppliers" / "suppliers.json", Supplier),
            _read_list(runtime / "suppliers.json", Supplier),
        ),
        emails=_read_list(root / "emails" / "emails.json", EmailMessage),
        documents=_read_list(root / "documents" / "documents.json", Document),
        assets=_read_list(root / "assets" / "assets.json", CustomerAsset),
        commitments=_merge_commitments(root),
        events=_overlay(
            _read_list(root / "events" / "timeline.json", WorldEvent),
            _read_list(runtime / "events.json", WorldEvent),
        ),
    )
