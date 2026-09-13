from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel

from adapters.files.world import DATA_ROOT, _read_clock, _read_list
from domain.models import (
    ActivityItem,
    AuditRecord,
    Commitment,
    FeasibilityAssessment,
    HumanDecision,
    OutboxMessage,
    ParsedRequest,
    SimulationClock,
    Supplier,
    WorldEvent,
)


@dataclass
class RuntimeState:
    clock: SimulationClock
    commitments: list[Commitment]
    assessments: list[FeasibilityAssessment]
    decisions: list[HumanDecision]
    outbox: list[OutboxMessage]
    activity: list[ActivityItem]
    audit: list[AuditRecord]
    requests: list[ParsedRequest]
    events: list[WorldEvent]
    suppliers: list[Supplier]


def _write_list(path: Path, items: list[BaseModel]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [item.model_dump(mode="json") for item in items]
    path.write_text(json.dumps(payload, indent=2) + "\n")


def read_seed_commitment_ids(root: Path | None = None) -> set[str]:
    root = root or DATA_ROOT
    return {item.id for item in _read_list(root / "projects" / "commitments.json", Commitment)}


def read_runtime(root: Path) -> RuntimeState:
    runtime = root / "runtime"
    return RuntimeState(
        clock=_read_clock(runtime / "clock.json"),
        commitments=_read_list(runtime / "commitments.json", Commitment),
        assessments=_read_list(runtime / "assessments.json", FeasibilityAssessment),
        decisions=_read_list(runtime / "decisions.json", HumanDecision),
        outbox=_read_list(runtime / "outbox.json", OutboxMessage),
        activity=_read_list(runtime / "activity.json", ActivityItem),
        audit=_read_list(runtime / "audit.json", AuditRecord),
        requests=_read_list(runtime / "requests.json", ParsedRequest),
        events=_read_list(runtime / "events.json", WorldEvent),
        suppliers=_read_list(runtime / "suppliers.json", Supplier),
    )


def write_activity(root: Path, items: list[ActivityItem]) -> None:
    _write_list(root / "runtime" / "activity.json", items)


def write_runtime(
    root: Path,
    state: RuntimeState,
    seed_commitment_ids: set[str],
    clock: SimulationClock,
) -> None:
    runtime = root / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    created = [item for item in state.commitments if item.id not in seed_commitment_ids]
    _write_list(runtime / "commitments.json", created)
    _write_list(runtime / "assessments.json", state.assessments)
    _write_list(runtime / "decisions.json", state.decisions)
    _write_list(runtime / "outbox.json", state.outbox)
    _write_list(runtime / "activity.json", state.activity)
    _write_list(runtime / "audit.json", state.audit)
    _write_list(runtime / "requests.json", state.requests)
    _write_list(runtime / "events.json", state.events)
    _write_list(runtime / "suppliers.json", state.suppliers)
    (runtime / "clock.json").write_text(clock.model_dump_json(indent=2) + "\n")
