from __future__ import annotations

import shutil
from pathlib import Path

from domain.clock import default_clock


def reset_runtime(data_root: Path) -> None:
    runtime = data_root / "runtime"
    if runtime.exists():
        shutil.rmtree(runtime)
    runtime.mkdir(parents=True)
    (runtime / "clock.json").write_text(default_clock().model_dump_json(indent=2) + "\n")
    for name in (
        "commitments.json",
        "assessments.json",
        "decisions.json",
        "evidence.json",
        "audit.json",
        "outbox.json",
        "activity.json",
        "requests.json",
        "events.json",
        "suppliers.json",
    ):
        (runtime / name).write_text("[]\n")
    (runtime / ".gitkeep").write_text("")
