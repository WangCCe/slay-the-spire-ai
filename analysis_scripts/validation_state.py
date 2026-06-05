#!/usr/bin/env python3
"""Record small validation workflow state snapshots."""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, Optional


DEFAULT_STATE_PATH = Path("reports") / "validation_state.json"


def load_validation_state(state_path: Path = DEFAULT_STATE_PATH) -> Dict:
    if not state_path.exists():
        return {}
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def write_validation_state(state_path: Path, state: Dict) -> Dict:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(state, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return state


def record_pytest_baseline(
    state_path: Path,
    commit: str,
    command: Iterable[str] | str,
    outcome: str,
    test_count: Optional[int] = None,
    duration_seconds: Optional[float] = None,
    timestamp: Optional[str] = None,
) -> Dict:
    state = load_validation_state(state_path)
    state["pytest_baseline"] = {
        "commit": str(commit),
        "command": _command_to_list(command),
        "outcome": str(outcome),
        "test_count": test_count,
        "duration_seconds": duration_seconds,
        "recorded_at": timestamp or datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }
    return write_validation_state(state_path, state)


def pytest_baseline_is_current(state: Dict, commit: str) -> bool:
    baseline = state.get("pytest_baseline")
    if not isinstance(baseline, dict):
        return False
    return baseline.get("commit") == commit and baseline.get("outcome") == "passed"


def _command_to_list(command: Iterable[str] | str):
    if isinstance(command, str):
        return command.split()
    return [str(part) for part in command]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command_name", required=True)

    record = subparsers.add_parser("record-pytest")
    record.add_argument("--state-path", type=Path, default=DEFAULT_STATE_PATH)
    record.add_argument("--commit", required=True)
    record.add_argument("--command", required=True)
    record.add_argument("--outcome", choices=["passed", "failed"], required=True)
    record.add_argument("--test-count", type=int, default=None)
    record.add_argument("--duration-seconds", type=float, default=None)

    args = parser.parse_args(argv)
    if args.command_name == "record-pytest":
        record_pytest_baseline(
            args.state_path,
            commit=args.commit,
            command=args.command,
            outcome=args.outcome,
            test_count=args.test_count,
            duration_seconds=args.duration_seconds,
        )
        print(f"pytest baseline recorded: {args.commit} {args.outcome}")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
