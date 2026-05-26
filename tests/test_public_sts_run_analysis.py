import gzip
import json
import subprocess
import sys
from pathlib import Path

from analysis_scripts.analyze_public_sts_runs import (
    iter_run_records,
    summarize_runs,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "analysis_scripts" / "analyze_public_sts_runs.py"


def _run(**overrides):
    data = {
        "character_chosen": "IRONCLAD",
        "victory": False,
        "floor_reached": 10,
        "playtime": 600,
        "build_version": "2020-12-22",
        "ascension_level": 0,
        "is_daily": False,
        "is_endless": False,
        "chose_seed": False,
        "card_choices": [],
        "boss_relics": [],
        "neow_bonus": "NONE",
        "neow_cost": "NONE",
        "path_taken": [],
        "damage_taken": [],
    }
    data.update(overrides)
    return data


def test_iter_run_records_unwraps_metrics_event_and_json_array(tmp_path):
    source = tmp_path / "runs.json"
    wrapped = {"event": _run(floor_reached=20)}
    plain = _run(floor_reached=30)
    source.write_text(json.dumps([wrapped, plain]), encoding="utf-8")

    records = list(iter_run_records([source]))

    assert [record["floor_reached"] for record in records] == [20, 30]
    assert all("event" not in record for record in records)


def test_summarize_runs_filters_ironclad_and_counts_choices():
    records = [
        _run(
            victory=True,
            floor_reached=51,
            card_choices=[
                {
                    "floor": 1,
                    "picked": "Pommel Strike",
                    "not_picked": ["Cleave", "Flex"],
                },
                {
                    "floor": 7,
                    "picked": "Shrug It Off",
                    "not_picked": ["Warcry", "Havoc"],
                },
            ],
            boss_relics=[
                {"picked": "Snecko Eye", "not_picked": ["Black Blood", "Tiny House"]}
            ],
            neow_bonus="TRANSFORM_CARD",
            neow_cost="NONE",
            path_taken=["M", "M", "?", "E", "R"],
            damage_taken=[{"enemies": "Slime Boss", "damage": 9, "turns": 5}],
        ),
        _run(
            floor_reached=12,
            card_choices=[
                {
                    "floor": 3,
                    "picked": "SKIP",
                    "not_picked": ["Clash", "Fire Breathing", "True Grit"],
                }
            ],
            boss_relics=[],
            neow_bonus="THREE_ENEMY_KILL",
            path_taken=["M", "?", "M", "R"],
            damage_taken=[{"enemies": "Gremlin Nob", "damage": 25, "turns": 4}],
        ),
        _run(
            character_chosen="THE_SILENT",
            victory=True,
            floor_reached=51,
            card_choices=[{"picked": "Backflip", "not_picked": ["Dodge and Roll"]}],
        ),
    ]

    summary = summarize_runs(records, character="IRONCLAD")

    assert summary.run_count == 2
    assert summary.victories == 1
    assert summary.avg_floor == 31.5
    assert summary.card_pick_counts["Pommel Strike"].selected == 1
    assert summary.card_pick_counts["Pommel Strike"].offered == 1
    assert summary.card_pick_counts["Clash"].selected == 0
    assert summary.card_pick_counts["Clash"].offered == 1
    assert summary.skipped_card_rewards == 1
    assert summary.boss_relic_counts["Snecko Eye"].selected == 1
    assert summary.neow_counts["TRANSFORM_CARD"].runs == 1
    assert summary.act1_node_counts["E"] == 1
    assert summary.death_causes["Gremlin Nob"] == 1


def test_cli_reads_gzip_json_and_prints_summary(tmp_path):
    source = tmp_path / "sample.json.gz"
    runs = [
        {"event": _run(victory=True, floor_reached=51)},
        {"event": _run(floor_reached=9, neow_bonus="THREE_ENEMY_KILL")},
    ]
    with gzip.open(source, "wt", encoding="utf-8") as f:
        json.dump(runs, f)

    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(source), "--character", "IRONCLAD"],
        capture_output=True,
        text=True,
        timeout=15,
    )

    assert result.returncode == 0, result.stderr
    assert "Runs analyzed: 2" in result.stdout
    assert "Victories: 1 (50.0%)" in result.stdout
    assert "Top Neow bonuses" in result.stdout
