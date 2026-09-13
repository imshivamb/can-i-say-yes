from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from evals.evaluators import evaluate_suite, summarize
from evals.scenarios import live_scenarios, scenarios


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Can I Say Yes? eval suite.")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Call the live Bedrock Investigator instead of the recorded engine.",
    )
    args = parser.parse_args()
    cases = live_scenarios() if args.live else scenarios()
    results = evaluate_suite(cases, live=args.live)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "mode": "live" if args.live else "recorded",
        "summary": summarize(results),
        "cases": [result.as_dict() for result in results],
    }
    output_dir = Path("evals/results")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / ("live-latest.json" if args.live else "latest.json")
    output_path.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
