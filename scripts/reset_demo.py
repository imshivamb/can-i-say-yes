"""Restore the demo world to 12 September 2026, 09:00 IST."""

from __future__ import annotations

from pathlib import Path

from adapters.files.runtime import reset_runtime

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    reset_runtime(ROOT / "data")
    print("Demo reset to 2026-09-12T09:00:00+05:30")


if __name__ == "__main__":
    main()
