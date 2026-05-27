import json
import subprocess
import sys
from pathlib import Path

from analysis_scripts.diagnose_run import (
    build_report,
    extract_log_window,
    format_run_report,
    load_run_record,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "analysis_scripts" / "diagnose_run.py"


def _write_run(game_dir, timestamp="12345", **overrides):
    runs_dir = game_dir / "runs" / "IRONCLAD"
    runs_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "timestamp": int(timestamp),
        "local_time": "20260527123000",
        "victory": False,
        "floor_reached": 33,
        "killed_by": "Champ",
        "playtime": 156,
        "master_deck": ["Strike_R", "Bash", "Shrug It Off+1"],
        "relics": ["Burning Blood", "Sozu"],
        "card_choices": [
            {"floor": 1, "picked": "Uppercut", "not_picked": ["Clash", "Havoc"]},
            {"floor": 29, "picked": "SKIP", "not_picked": ["Power Through", "Warcry"]},
        ],
        "boss_relics": [
            {"picked": "Sozu", "not_picked": ["Runic Cube", "Tiny House"]},
        ],
        "campfire_choices": [
            {"floor": 6, "key": "SMITH", "data": "Bash"},
            {"floor": 32, "key": "REST"},
        ],
        "damage_taken": [
            {"floor": 16, "enemies": "Hexaghost", "damage": 30, "turns": 7},
            {"floor": 33, "enemies": "Champ", "damage": 75, "turns": 9},
        ],
    }
    data.update(overrides)
    run_file = runs_dir / f"{timestamp}.run"
    run_file.write_text(json.dumps(data), encoding="utf-8")
    return run_file


def test_load_run_record_accepts_timestamp_or_path(tmp_path):
    game_dir = tmp_path / "SlayTheSpire"
    run_file = _write_run(game_dir, timestamp="12345")

    by_timestamp_path, by_timestamp_record = load_run_record(
        game_dir=game_dir,
        character="IRONCLAD",
        run_ref="12345",
    )
    by_path_path, by_path_record = load_run_record(
        game_dir=game_dir,
        character="IRONCLAD",
        run_ref=str(run_file),
    )

    assert by_timestamp_path == run_file
    assert by_path_path == run_file
    assert by_timestamp_record["killed_by"] == "Champ"
    assert by_path_record["floor_reached"] == 33


def test_extract_log_window_uses_local_time_and_signal_filter(tmp_path):
    log_path = tmp_path / "ai_debug.log"
    log_path.write_text(
        "\n".join(
            [
                "2026-05-27 12:28:00,000 - INFO - outside",
                "2026-05-27 12:29:30,000 - INFO - [COMBAT] floor=33",
                "2026-05-27 12:29:50,000 - INFO - [LOOKAHEAD] damage=32",
                "2026-05-27 12:29:55,000 - INFO - ordinary detail",
                "2026-05-27 12:30:02,000 - INFO - [GAME_OVER] Saved state",
            ]
        ),
        encoding="utf-8",
    )

    lines = extract_log_window(
        log_path,
        local_time="20260527123000",
        before_seconds=40,
        after_seconds=5,
        signals_only=True,
        max_lines=20,
    )

    assert "outside" not in "\n".join(lines)
    assert any("[COMBAT]" in line for line in lines)
    assert any("[LOOKAHEAD]" in line for line in lines)
    assert any("[GAME_OVER]" in line for line in lines)
    assert all("ordinary detail" not in line for line in lines)


def test_format_run_report_compacts_key_run_evidence(tmp_path):
    game_dir = tmp_path / "SlayTheSpire"
    run_file = _write_run(game_dir)
    _, record = load_run_record(game_dir, "IRONCLAD", str(run_file))

    report = format_run_report(
        run_file=run_file,
        record=record,
        log_lines=["2026-05-27 12:29:50,000 - INFO - [LOOKAHEAD] damage=32"],
    )

    assert "Run file:" in report
    assert "Result: LOSS floor=33 killed_by=Champ" in report
    assert "Deck size: 3" in report
    assert "Boss relics: Sozu over Runic Cube, Tiny House" in report
    assert "Card rewards: 1 picks, 1 skips" in report
    assert "Final combat: Champ damage=75 turns=9" in report
    assert "[LOOKAHEAD] damage=32" in report


def test_diagnose_run_cli_prints_report_with_log_window(tmp_path):
    game_dir = tmp_path / "SlayTheSpire"
    _write_run(game_dir, timestamp="12345")
    (game_dir / "ai_debug.log").write_text(
        "2026-05-27 12:29:50,000 - INFO - [LOOKAHEAD] damage=32\n"
        "2026-05-27 12:30:01,000 - INFO - [GAME_OVER] Saved state\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "12345",
            "--game-dir",
            str(game_dir),
            "--before-seconds",
            "20",
            "--after-seconds",
            "5",
        ],
        capture_output=True,
        text=True,
        timeout=15,
    )

    assert result.returncode == 0, result.stderr
    assert "Result: LOSS floor=33 killed_by=Champ" in result.stdout
    assert "[GAME_OVER] Saved state" in result.stdout


def test_build_report_searches_archived_logs_when_current_log_misses(tmp_path):
    game_dir = tmp_path / "SlayTheSpire"
    _write_run(game_dir, timestamp="12345")
    (game_dir / "ai_debug.log").write_text(
        "2026-05-27 12:40:00,000 - INFO - unrelated current log\n",
        encoding="utf-8",
    )
    archive_dir = game_dir / "logs_archive"
    archive_dir.mkdir()
    (archive_dir / "ai_debug.log.20260527-123100.bak").write_text(
        "2026-05-27 12:29:50,000 - INFO - [LOOKAHEAD] archived damage=32\n"
        "2026-05-27 12:30:01,000 - INFO - [GAME_OVER] archived state\n",
        encoding="utf-8",
    )

    report = build_report(
        run_ref="12345",
        game_dir=game_dir,
        character="IRONCLAD",
        before_seconds=20,
        after_seconds=5,
        signals_only=True,
        max_log_lines=20,
    )

    assert "log source: ai_debug.log.20260527-123100.bak" in report
    assert "[LOOKAHEAD] archived damage=32" in report


def test_build_report_searches_rotated_logs_before_archives(tmp_path):
    game_dir = tmp_path / "SlayTheSpire"
    _write_run(game_dir, timestamp="12345")
    (game_dir / "ai_debug.log").write_text(
        "2026-05-27 12:40:00,000 - INFO - unrelated current log\n",
        encoding="utf-8",
    )
    (game_dir / "ai_debug.log.1").write_text(
        "2026-05-27 12:29:50,000 - INFO - [LOOKAHEAD] rotated damage=32\n"
        "2026-05-27 12:30:01,000 - INFO - [GAME_OVER] rotated state\n",
        encoding="utf-8",
    )
    archive_dir = game_dir / "logs_archive"
    archive_dir.mkdir()
    (archive_dir / "ai_debug.log.20260527-123100.bak").write_text(
        "2026-05-27 12:29:50,000 - INFO - [LOOKAHEAD] archived damage=32\n",
        encoding="utf-8",
    )

    report = build_report(
        run_ref="12345",
        game_dir=game_dir,
        character="IRONCLAD",
        before_seconds=20,
        after_seconds=5,
        signals_only=True,
        max_log_lines=20,
    )

    assert "log source: ai_debug.log.1" in report
    assert "[LOOKAHEAD] rotated damage=32" in report
    assert "archived damage=32" not in report
