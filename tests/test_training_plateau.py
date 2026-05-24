import json
from pathlib import Path

from analysis_scripts.analyze_training_plateau import (
    ACT1_ELITES,
    analyze_plateau,
    collect_runs,
    make_report,
)


def write_run(path: Path, floor, killed_by, path_taken, victory=False):
    path.write_text(
        json.dumps(
            {
                "victory": victory,
                "floor_reached": floor,
                "score": floor * 10,
                "playtime": 30,
                "killed_by": killed_by,
                "ascension_level": 0,
                "path_taken": path_taken,
                "master_deck": ["Strike_R", "Defend_R", "Bash"],
                "relics": ["Burning Blood"],
                "damage_taken": [{"enemies": killed_by, "damage": 12}],
            }
        ),
        encoding="utf-8",
    )


def test_collect_runs_and_route_risk(tmp_path):
    runs_dir = tmp_path / "runs" / "IRONCLAD"
    runs_dir.mkdir(parents=True)
    write_run(runs_dir / "1.run", 7, "Lagavulin", ["M", "?", "E"])
    write_run(runs_dir / "2.run", 16, "Hexaghost", ["M", "M", "R", "BOSS"])

    runs = collect_runs(tmp_path / "runs", "IRONCLAD", 10)

    assert len(runs) == 2
    assert runs[0].act1_elites_taken == 1
    assert runs[0].died_to_act1_elite
    assert runs[1].reached_act1_boss


def test_plateau_detector_flags_flat_elite_wall(tmp_path):
    runs_dir = tmp_path / "runs" / "IRONCLAD"
    runs_dir.mkdir(parents=True)
    elite_names = sorted(ACT1_ELITES)
    for idx in range(20):
        write_run(
            runs_dir / f"{idx}.run",
            8 + (idx % 2),
            elite_names[idx % len(elite_names)],
            ["M", "M", "E"],
        )

    runs = collect_runs(tmp_path / "runs", "IRONCLAD", 20)
    report = make_report(runs, bucket_size=5)

    assert report["plateau"]["plateau"]
    assert report["overall"]["elite_death_rate"] == 100.0


def test_plateau_detector_does_not_flag_improving_trend():
    buckets = []
    for idx, floor in enumerate([5, 7, 9, 12], start=1):
        buckets.append(
            {
                "avg_floor": floor,
                "elite_death_rate": 10.0,
                "win_rate": 5.0,
            }
        )

    verdict = analyze_plateau(buckets, lookback=4)

    assert not verdict["plateau"]
