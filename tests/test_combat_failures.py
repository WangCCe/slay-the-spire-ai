import json
from pathlib import Path

from analysis_scripts.analyze_combat_failures import (
    collect_run_files,
    iter_combats,
    make_report,
    parse_log_action_hints,
    summarize_run,
)


def write_run(path: Path, *, killed_by="Gremlin Gang", floor=5, victory=False):
    path.write_text(
        json.dumps(
            {
                "victory": victory,
                "floor_reached": floor,
                "killed_by": killed_by,
                "path_taken": ["M", "M", "?", "M", "M"],
                "master_deck": ["Strike_R", "Defend_R", "Bash", "Anger"],
                "relics": ["Burning Blood"],
                "potions_obtained": [{"key": "Fire Potion"}],
                "potions_floor_usage": [],
                "items_purchased": [],
                "items_purged": ["Strike_R"],
                "damage_taken": [
                    {"enemies": "Jaw Worm", "floor": 1, "damage": 8, "turns": 3},
                    {"enemies": killed_by, "floor": floor, "damage": 55, "turns": 6},
                ],
            }
        ),
        encoding="utf-8",
    )


def test_collect_and_summarize_combat_failures(tmp_path):
    runs_dir = tmp_path / "runs" / "IRONCLAD"
    runs_dir.mkdir(parents=True)
    write_run(runs_dir / "1.run")
    write_run(runs_dir / "2.run", killed_by="Slime Boss", floor=16)

    run_files = collect_run_files(tmp_path / "runs", "IRONCLAD", 2)
    failures = []
    combats = []
    for run_file in run_files:
        data = json.loads(run_file.read_text(encoding="utf-8"))
        failures.append(summarize_run(run_file, data))
        combats.extend(iter_combats(run_file, data))

    report = make_report(failures, combats, {"log_found": 0})

    assert report["overall"]["runs"] == 2
    assert report["death_profile"]["boss_deaths"] == 1
    assert report["death_profile"]["potionless_deaths_after_obtaining_potions"] == 2
    assert report["growth_profile"]["avg_nonstarter_cards"] == 1.0
    assert any(item["enemy"] == "Gremlin Gang" for item in report["enemy_profile"])


def test_parse_log_action_hints(tmp_path):
    log_path = tmp_path / "ai_debug.log"
    log_path.write_text(
        "\n".join(
            [
                "[CALLBACK] Got action: PlayCardAction",
                "[CALLBACK] Got action: EndTurnAction",
                "[TURN_END] floor=3 turn=2 energy_remaining=1 hand=4",
                "Invalid command: confirm",
            ]
        ),
        encoding="utf-8",
    )

    hints = parse_log_action_hints(log_path, tail_lines=100)

    assert hints["log_found"] == 1
    assert hints["play_card_actions"] == 1
    assert hints["end_turn_actions"] == 1
    assert hints["turn_ends_with_energy"] == 1
    assert hints["invalid_commands"] == 1
