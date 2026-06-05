import json
import subprocess
import sys
from pathlib import Path

from analysis_scripts.validation_state import (
    load_validation_state,
    pytest_baseline_is_current,
    record_pytest_baseline,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "analysis_scripts" / "validation_state.py"


def test_records_pytest_baseline_and_detects_stale_commit(tmp_path):
    state_path = tmp_path / "validation_state.json"

    state = record_pytest_baseline(
        state_path,
        commit="abc1234",
        command=["python", "-m", "pytest"],
        outcome="passed",
        test_count=1502,
        duration_seconds=42.5,
    )

    loaded = load_validation_state(state_path)
    assert loaded == state
    assert loaded["pytest_baseline"]["commit"] == "abc1234"
    assert loaded["pytest_baseline"]["outcome"] == "passed"
    assert loaded["pytest_baseline"]["test_count"] == 1502
    assert loaded["pytest_baseline"]["command"] == ["python", "-m", "pytest"]
    assert pytest_baseline_is_current(loaded, "abc1234") is True
    assert pytest_baseline_is_current(loaded, "def5678") is False


def test_validation_state_cli_records_pytest_baseline(tmp_path):
    state_path = tmp_path / "validation_state.json"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "record-pytest",
            "--state-path",
            str(state_path),
            "--commit",
            "abc1234",
            "--command",
            "python -m pytest",
            "--outcome",
            "passed",
            "--test-count",
            "1502",
            "--duration-seconds",
            "42.5",
        ],
        capture_output=True,
        text=True,
        timeout=15,
    )

    assert result.returncode == 0, result.stderr
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["pytest_baseline"]["commit"] == "abc1234"
    assert state["pytest_baseline"]["outcome"] == "passed"
    assert "pytest baseline recorded" in result.stdout
