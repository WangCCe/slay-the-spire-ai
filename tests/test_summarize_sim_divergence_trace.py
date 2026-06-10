import json
import subprocess
import sys
from pathlib import Path

from analysis_scripts.summarize_sim_divergence_trace import (
    load_trace,
    summarize_trace,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "analysis_scripts" / "summarize_sim_divergence_trace.py"


def _write_jsonl(path, rows):
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            if isinstance(row, str):
                handle.write(row + "\n")
            else:
                handle.write(json.dumps(row, sort_keys=True) + "\n")


def test_trace_summary_filters_old_rows_and_groups_core_dimensions(tmp_path):
    trace_path = tmp_path / "sim_divergence_trace_clean.jsonl"
    _write_jsonl(
        trace_path,
        [
            {
                "unix_time": 100.0,
                "reason": "monster_state_mismatch",
                "action": {
                    "type": "PlayCardAction",
                    "card": {"name": "Strike"},
                },
                "diffs": {"monsters[0].hp": {"expected": 10, "actual": 15}},
            },
            "{not-json",
            {
                "unix_time": 200.0,
                "floor": 16,
                "turn": 4,
                "reason": "monster_state_mismatch",
                "action": {
                    "type": "PlayCardAction",
                    "card": {"name": "Havoc"},
                },
                "diffs": {
                    "monsters[0].hp": {"expected": 174, "actual": 188},
                    "monsters[0].block": {"expected": 0, "actual": 4},
                },
            },
            {
                "unix_time": 210.0,
                "floor": 16,
                "turn": 5,
                "reason": "player_state_mismatch",
                "action": {"type": "EndTurnAction"},
                "diffs": {"player.block": {"expected": 0, "actual": 6}},
            },
        ],
    )

    loaded = load_trace(trace_path, since_unix=150.0)
    summary = summarize_trace(loaded)

    assert summary.events_analyzed == 2
    assert summary.skipped_before_cutoff == 1
    assert summary.malformed_lines == 1
    assert summary.by_reason["monster_state_mismatch"] == 1
    assert summary.by_reason["player_state_mismatch"] == 1
    assert summary.by_action_card["PlayCardAction | Havoc"] == 1
    assert summary.by_action_card["EndTurnAction | -"] == 1
    assert summary.by_diff_key["monsters[0].hp"] == 1
    assert summary.by_diff_key["monsters[0].block"] == 1
    assert summary.by_diff_key["player.block"] == 1
    assert summary.latest_examples[0].card == "Havoc"


def test_trace_summary_cli_reports_fresh_distribution(tmp_path):
    trace_path = tmp_path / "sim_divergence_trace_clean.jsonl"
    _write_jsonl(
        trace_path,
        [
            {
                "unix_time": 100.0,
                "reason": "old",
                "action": {"type": "PlayCardAction", "card": {"name": "Strike"}},
                "diffs": {"old.diff": {}},
            },
            {
                "unix_time": 200.0,
                "floor": 33,
                "turn": 9,
                "reason": "player_state_mismatch",
                "action": {"type": "PlayCardAction", "card": {"name": "Havoc+"}},
                "diffs": {"player.block": {"expected": 11, "actual": 7}},
            },
        ],
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--trace",
            str(trace_path),
            "--since-unix",
            "150",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "Sim Divergence Trace Summary" in output
    assert "Events analyzed: 1" in output
    assert "Skipped before cutoff: 1" in output
    assert "player_state_mismatch: 1" in output
    assert "PlayCardAction | Havoc+: 1" in output
    assert "player.block: 1" in output
