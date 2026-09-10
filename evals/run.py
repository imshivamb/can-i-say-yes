from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from evals.evaluators import evaluate_case, summarize
from evals.scenarios import scenarios


def main() -> int:
    results = [evaluate_case(case) for case in scenarios()]
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": summarize(results),
        "cases": [result.as_dict() for result in results],
    }
    output_dir = Path("evals/results")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "latest.json"
    output_path.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

