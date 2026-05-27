import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from analysis_scripts.diagnose_live_batch import (
    format_report,
    load_run_summaries,
    scan_text_for_signals,
    summarize_run_batch,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "analysis_scripts" / "diagnose_live_batch.py"


def _write_run(game_dir, timestamp, mtime, **overrides):
    runs_dir = game_dir / "runs" / "IRONCLAD"
    runs_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "victory": False,
        "floor_reached": 16,
        "killed_by": "Hexaghost",
        "playtime": 60,
        "card_choices": [],
        "path_taken": ["M", "M", "R", "BOSS"],
        "relics": ["Burning Blood"],
    }
    data.update(overrides)
    run_file = runs_dir / f"{timestamp}.run"
    run_file.write_text(json.dumps(data), encoding="utf-8")
    os.utime(run_file, (mtime, mtime))
    return run_file


def test_live_batch_summary_filters_since_and_counts_core_outcomes(tmp_path):
    game_dir = tmp_path / "SlayTheSpire"
    cutoff = datetime(2026, 5, 27, 12, 0, tzinfo=timezone.utc).timestamp()
    (game_dir / "runs").mkdir(parents=True, exist_ok=True)
    (game_dir / "runs" / "ai_games.txt").write_text("103\n", encoding="utf-8")
    _write_run(game_dir, 100, cutoff - 10, floor_reached=5, killed_by="Old")
    _write_run(
        game_dir,
        101,
        cutoff + 10,
        floor_reached=16,
        killed_by="Hexaghost",
        card_choices=[
            {"picked": "Pommel Strike", "not_picked": ["Clash", "Havoc"]},
            {"picked": "SKIP", "not_picked": ["Flex", "Warcry", "Armaments"]},
        ],
    )
    _write_run(
        game_dir,
        102,
        cutoff + 20,
        victory=True,
        floor_reached=51,
        killed_by=None,
        playtime=500,
        card_choices=[
            {"picked": "Shrug It Off", "not_picked": ["Clash", "Havoc"]},
        ],
    )

    runs = load_run_summaries(
        game_dir,
        character="IRONCLAD",
        since_timestamp=cutoff,
        limit=10,
    )
    summary = summarize_run_batch(runs)

    assert [run.file_name for run in runs] == ["101.run", "102.run"]
    assert summary.run_count == 2
    assert summary.victories == 1
    assert summary.ai_marked_count == 1
    assert summary.best_floor == 51
    assert summary.avg_floor == 33.5
    assert summary.death_causes["Hexaghost"] == 1
    assert summary.card_reward_picks == 2
    assert summary.card_reward_skips == 1


def test_live_batch_report_surfaces_log_signals():
    log_signals = scan_text_for_signals(
        "Traceback\nInvalid command: choose\nGame appears stuck\nTraceback\n"
    )
    error_signals = scan_text_for_signals("Communication Mod not responding\n")
    summary = summarize_run_batch([])

    report = format_report(
        game_dir=Path("D:/Game"),
        character="IRONCLAD",
        since_label="test-window",
        summary=summary,
        log_signals=log_signals,
        error_signals=error_signals,
        recent_error_tail=["Communication Mod not responding"],
    )

    assert "Runs analyzed: 0" in report
    assert "Traceback: 2" in report
    assert "Invalid command: 1" in report
    assert "Communication Mod not responding: 1" in report


def test_live_batch_diagnostics_cli_prints_compact_report(tmp_path):
    game_dir = tmp_path / "SlayTheSpire"
    cutoff = datetime(2026, 5, 27, 12, 0, tzinfo=timezone.utc).timestamp()
    _write_run(game_dir, 200, cutoff + 10, floor_reached=33, killed_by="Champ")
    (game_dir / "runs").mkdir(exist_ok=True)
    (game_dir / "runs" / "ai_games.txt").write_text("200\n", encoding="utf-8")
    (game_dir / "ai_debug.log").write_text(
        "CARD_REWARD\nGame appears stuck\n",
        encoding="utf-8",
    )
    (game_dir / "communication_mod_errors.log").write_text(
        "Traceback\nexample\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--game-dir",
            str(game_dir),
            "--since",
            str(int(cutoff)),
            "--tail-lines",
            "20",
        ],
        capture_output=True,
        text=True,
        timeout=15,
    )

    assert result.returncode == 0, result.stderr
    assert "Runs analyzed: 1" in result.stdout
    assert "Best floor: 33" in result.stdout
    assert "Champ: 1" in result.stdout
    assert "Game appears stuck: 1" in result.stdout
