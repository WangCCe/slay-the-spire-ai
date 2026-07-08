import json
import subprocess
import sys
from pathlib import Path


def _write_trace(path, rows):
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")


def _base_trace_row(screen_type, action, screen):
    return {
        "timestamp": "2026-06-18T00:00:00.000Z",
        "unix_time": 1780000000.0,
        "source": "combat_rl",
        "decision_path": "fallback_noncombat",
        "floor": 3,
        "act": 1,
        "room_type": "",
        "screen_type": screen_type,
        "in_combat": False,
        "gold": 99,
        "player": {"current_hp": 68, "max_hp": 80, "block": 0, "energy": 0},
        "deck": [{"name": "Strike"}, {"name": "Defend"}, {"name": "Bash"}],
        "relics": [{"name": "Burning Blood"}],
        "potions": [],
        "screen": screen,
        "action": action,
    }


def test_exports_complete_noncombat_samples_from_trace(tmp_path):
    from analysis_scripts.noncombat_rl_decision_loop import (
        SCHEMA_VERSION,
        export_samples_from_trace,
    )

    rows = [
        _base_trace_row(
            "CARD_REWARD",
            {"type": "ChooseAction", "name": "Clothesline", "choice_index": 0},
            {
                "type": "CARD_REWARD",
                "cards": [{"name": "Clothesline"}, {"name": "Perfected Strike"}],
                "can_skip": True,
                "can_bowl": False,
            },
        ),
        _base_trace_row(
            "SHOP_SCREEN",
            {
                "type": "BuyPurgeAction",
                "name": "purge",
                "card_to_purge": {"name": "Strike"},
            },
            {
                "type": "SHOP_SCREEN",
                "cards": [{"name": "Perfected Strike", "price": 72}],
                "relics": [],
                "potions": [],
                "purge_available": True,
                "purge_cost": 75,
            },
        ),
        _base_trace_row(
            "EVENT",
            {"type": "ChooseAction", "choice_index": 1},
            {
                "type": "EVENT",
                "event_name": "Golden Shrine",
                "event_id": "Golden Shrine",
                "options": [{"label": "Pray"}, {"label": "Leave"}],
            },
        ),
        _base_trace_row(
            "MAP",
            {
                "type": "ChooseMapNodeAction",
                "choice_index": 0,
                "node": {"x": 0, "y": 1, "symbol": "M"},
            },
            {
                "type": "MAP",
                "next_nodes": [{"x": 0, "y": 1, "symbol": "M"}],
                "paths": [
                    {
                        "choice": 0,
                        "label": "M@0,1 -> ?@0,2",
                        "nodes": ["M", "?"],
                    }
                ],
            },
        ),
    ]
    trace_path = tmp_path / "trace.jsonl"
    _write_trace(trace_path, rows)

    samples = export_samples_from_trace(trace_path)

    assert [sample["schema_version"] for sample in samples] == [SCHEMA_VERSION] * 4
    assert {sample["category"] for sample in samples} == {
        "card_reward",
        "shop",
        "event",
        "route",
    }
    shop = next(sample for sample in samples if sample["category"] == "shop")
    assert {candidate["action_id"] for candidate in shop["candidate_actions"]} >= {
        "shop:buy_card:perfected_strike",
        "shop:purge:strike",
        "shop:leave",
    }
    assert shop["selected_action_id"] == "shop:purge:strike"
    assert shop["current_policy_label"]["label"] == "purge Strike"
    assert shop["bottled_label"]["label"] == "Perfected Strike"
    assert shop["evidence_quality"] == "complete"
    assert shop["outcome"]["join_status"] == "missing"


def test_partial_trace_sample_preserves_limitations(tmp_path):
    from analysis_scripts.noncombat_rl_decision_loop import export_samples_from_trace

    trace_path = tmp_path / "trace.jsonl"
    _write_trace(
        trace_path,
        [
            {
                "unix_time": 1780000001.0,
                "screen_type": "SHOP_SCREEN",
                "floor": 3,
                "act": 1,
                "screen": {"type": "SHOP_SCREEN", "cards": []},
                "action": {"type": "LeaveAction", "name": "leave"},
            }
        ],
    )

    [sample] = export_samples_from_trace(trace_path)

    assert sample["category"] == "shop"
    assert sample["evidence_quality"] == "partial"
    assert sample["limitations"]
    assert sample["candidate_actions"][-1]["action_id"] == "shop:leave"


def test_generic_shop_purge_action_maps_to_purge_candidate(tmp_path):
    from analysis_scripts.noncombat_rl_decision_loop import export_samples_from_trace

    trace_path = tmp_path / "trace.jsonl"
    _write_trace(
        trace_path,
        [
            _base_trace_row(
                "SHOP_SCREEN",
                {"type": "BuyPurgeAction", "name": "purge"},
                {
                    "type": "SHOP_SCREEN",
                    "cards": [],
                    "relics": [],
                    "potions": [],
                    "purge_available": True,
                    "purge_cost": 75,
                },
            )
        ],
    )

    [sample] = export_samples_from_trace(trace_path)

    assert sample["selected_action_id"] == "shop:purge:strike"
    assert sample["current_policy_label"]["label"] == "purge Strike"


def test_attach_live_outcomes_matches_exactly_one_run():
    from analysis_scripts.noncombat_rl_decision_loop import attach_live_outcomes

    samples = [
        {
            "sample_id": "trace:0",
            "unix_time": 1780000010.0,
            "outcome": {"join_status": "missing"},
        }
    ]
    outcomes = [
        {
            "run_file": "1780000000.run",
            "start_unix": 1780000000,
            "end_unix": 1780000200,
            "victory": False,
            "floor_reached": 12,
            "killed_by": "Gremlin Nob",
            "playtime": 200,
            "ai_marked": True,
        }
    ]

    [joined] = attach_live_outcomes(samples, outcomes)

    assert joined["outcome"]["join_status"] == "matched"
    assert joined["outcome"]["included_in_gate"] is True
    assert joined["outcome"]["floor_reached"] == 12


def test_attach_live_outcomes_excludes_missing_and_ambiguous_matches():
    from analysis_scripts.noncombat_rl_decision_loop import attach_live_outcomes

    missing = [
        {
            "sample_id": "trace:missing",
            "unix_time": 1780000500.0,
            "outcome": {"join_status": "missing"},
        }
    ]
    ambiguous = [
        {
            "sample_id": "trace:ambiguous",
            "unix_time": 1780000010.0,
            "outcome": {"join_status": "missing"},
        }
    ]
    outcomes = [
        {
            "run_file": "a.run",
            "start_unix": 1780000000,
            "end_unix": 1780000200,
            "victory": False,
            "floor_reached": 10,
            "killed_by": "A",
            "playtime": 200,
            "ai_marked": True,
        },
        {
            "run_file": "b.run",
            "start_unix": 1780000005,
            "end_unix": 1780000300,
            "victory": False,
            "floor_reached": 11,
            "killed_by": "B",
            "playtime": 295,
            "ai_marked": True,
        },
    ]

    assert attach_live_outcomes(missing, outcomes)[0]["outcome"]["join_status"] == "missing"
    joined = attach_live_outcomes(ambiguous, outcomes)[0]
    assert joined["outcome"]["join_status"] == "ambiguous"
    assert joined["outcome"]["included_in_gate"] is False


def test_load_run_outcomes_reads_ai_marked_run_windows(tmp_path):
    from analysis_scripts.noncombat_rl_decision_loop import load_run_outcomes

    runs_dir = tmp_path / "runs"
    ironclad_dir = runs_dir / "IRONCLAD"
    ironclad_dir.mkdir(parents=True)
    (runs_dir / "ai_games.txt").write_text("1780000000\n", encoding="utf-8")
    (ironclad_dir / "1780000000.run").write_text(
        json.dumps(
            {
                "victory": False,
                "floor_reached": 18,
                "killed_by": "Slime Boss",
                "playtime": 240,
            }
        ),
        encoding="utf-8",
    )

    outcomes = load_run_outcomes(runs_dir, character="IRONCLAD", limit=5)

    assert outcomes == [
        {
            "run_file": "1780000000.run",
            "start_unix": 1780000000,
            "end_unix": 1780000240,
            "victory": False,
            "floor_reached": 18,
            "killed_by": "Slime Boss",
            "playtime": 240,
            "ai_marked": True,
        }
    ]


def _complete_sample(category, matched=True):
    return {
        "schema_version": "noncombat-rl-decision-v1",
        "sample_id": f"{category}:1",
        "category": category,
        "evidence_quality": "complete",
        "candidate_actions": [
            {
                "action_id": f"{category}:a",
                "kind": "test",
                "label": "A",
                "available": True,
                "raw": {},
            }
        ],
        "selected_action_id": f"{category}:a",
        "current_policy_label": {"label": "A", "action_id": f"{category}:a"},
        "bottled_label": {
            "label": "A",
            "action_id": f"{category}:a",
            "confidence": "high",
            "reason": "same",
        },
        "outcome": {
            "join_status": "matched" if matched else "missing",
            "included_in_gate": matched,
            "victory": False,
            "floor_reached": 20,
        },
    }


def test_gate_blocks_when_reward_contract_is_missing():
    from analysis_scripts.noncombat_rl_decision_loop import evaluate_promotion

    samples = [
        _complete_sample(category)
        for category in ["shop", "event", "route", "card_reward"]
    ]

    result = evaluate_promotion(samples, reward_contract=None)

    assert result["status"] == "blocked"
    assert "reward_contract_missing" in result["blocking_reasons"]
    assert result["formal_noncombat_rl_training_ready"] is False


def test_gate_allows_data_loop_when_state_action_reward_eval_are_present():
    from analysis_scripts.noncombat_rl_decision_loop import (
        default_reward_contract,
        evaluate_promotion,
    )

    samples = [
        _complete_sample(category)
        for category in ["shop", "event", "route", "card_reward"]
    ]

    result = evaluate_promotion(samples, reward_contract=default_reward_contract())

    assert result["status"] == "allowed"
    assert result["readiness"]["state"] == "present"
    assert result["readiness"]["action"] == "present"
    assert result["readiness"]["reward"] == "present"
    assert result["readiness"]["evaluation"] == "present"
    assert result["formal_noncombat_rl_training_ready"] is False


def test_report_names_gate_reward_and_training_guard():
    from analysis_scripts.noncombat_rl_decision_loop import (
        default_reward_contract,
        evaluate_promotion,
        render_readiness_report,
    )

    samples = [
        _complete_sample(category)
        for category in ["shop", "event", "route", "card_reward"]
    ]
    gate = evaluate_promotion(samples, reward_contract=default_reward_contract())

    report = render_readiness_report(samples, gate)

    assert "# Non-Combat RL Decision Loop Readiness" in report
    assert "Promotion status: allowed" in report
    assert "Reward readiness" in report
    assert "Formal non-combat RL training: blocked" in report


def test_report_lists_current_vs_bottled_disagreements():
    from analysis_scripts.noncombat_rl_decision_loop import (
        default_reward_contract,
        evaluate_promotion,
        render_readiness_report,
    )

    sample = _complete_sample("shop")
    sample["selected_action_id"] = "shop:leave"
    sample["current_policy_label"] = {"label": "leave", "action_id": "shop:leave"}
    sample["bottled_label"] = {
        "label": "Perfected Strike",
        "action_id": "shop:buy_card:perfected_strike",
        "confidence": "high",
        "reason": "native Bottled shop priority",
    }
    gate = evaluate_promotion([sample], reward_contract=default_reward_contract())

    report = render_readiness_report([sample], gate)

    assert "## Current-vs-Bottled Disagreements" in report
    assert "Action-id disagreements: 1/1" in report
    assert "shop: shop:leave -> shop:buy_card:perfected_strike" in report


def test_export_samples_can_use_native_bottled_oracle_metadata(tmp_path):
    from analysis_scripts.noncombat_rl_decision_loop import export_samples_from_trace
    from tests.test_bottled_policy_oracle import _write_fake_bottled_checkout

    checkout = _write_fake_bottled_checkout(tmp_path / "bottled_ai")
    trace_path = tmp_path / "trace.jsonl"
    _write_trace(
        trace_path,
        [
            _base_trace_row(
                "CARD_REWARD",
                {"type": "ChooseAction", "name": "skip"},
                {
                    "type": "CARD_REWARD",
                    "cards": [{"name": "Sentinel"}],
                    "can_skip": True,
                    "can_bowl": False,
                },
            )
        ],
    )

    [sample] = export_samples_from_trace(
        trace_path,
        reference_mode="native_bottled",
        bottled_repo_path=checkout,
    )

    assert sample["bottled_label"]["label"] == "Sentinel"
    assert sample["bottled_label"]["oracle_mode"] == "native_bottled"
    assert sample["bottled_label"]["source"]["strategy"] == "REQUESTED_STRIKE"
    assert sample["bottled_label"]["action_id"] == "card_reward:take:sentinel"


def test_combat_rl_smoke_command_is_bounded_and_not_noncombat_training():
    from analysis_scripts.noncombat_rl_decision_loop import combat_rl_smoke_command

    command = combat_rl_smoke_command(
        r"D:\anaconda\envs\stsai\python.exe",
        r"D:\SteamLibrary\steamapps\common\SlayTheSpire",
    )

    assert "--agent combat_rl" in command
    assert "--max-games 1" in command
    assert "--dry-run" in command
    assert "noncombat" not in command.lower()


def test_cli_writes_report_and_jsonl_samples(tmp_path, capsys):
    from analysis_scripts.noncombat_rl_decision_loop import main

    trace_path = tmp_path / "trace.jsonl"
    _write_trace(
        trace_path,
        [
            _base_trace_row(
                "SHOP_SCREEN",
                {
                    "type": "BuyPurgeAction",
                    "name": "purge",
                    "card_to_purge": {"name": "Strike"},
                },
                {
                    "type": "SHOP_SCREEN",
                    "cards": [{"name": "Perfected Strike", "price": 72}],
                    "relics": [],
                    "potions": [],
                    "purge_available": True,
                    "purge_cost": 75,
                },
            )
        ],
    )
    runs_dir = tmp_path / "runs"
    ironclad_dir = runs_dir / "IRONCLAD"
    ironclad_dir.mkdir(parents=True)
    (runs_dir / "ai_games.txt").write_text("1780000000\n", encoding="utf-8")
    (ironclad_dir / "1780000000.run").write_text(
        json.dumps({"victory": False, "floor_reached": 18, "playtime": 240}),
        encoding="utf-8",
    )
    report_path = tmp_path / "report.md"
    jsonl_path = tmp_path / "samples.jsonl"

    exit_code = main(
        [
            "--trace",
            str(trace_path),
            "--runs-dir",
            str(runs_dir),
            "--character",
            "IRONCLAD",
            "--output",
            str(report_path),
            "--json-output",
            str(jsonl_path),
        ]
    )

    assert exit_code == 0
    assert "Promotion status:" in capsys.readouterr().out
    assert "Formal non-combat RL training: blocked" in report_path.read_text(
        encoding="utf-8"
    )
    [sample_line] = jsonl_path.read_text(encoding="utf-8").splitlines()
    assert json.loads(sample_line)["schema_version"] == "noncombat-rl-decision-v1"


def test_direct_script_cli_writes_outputs(tmp_path):
    trace_path = tmp_path / "trace.jsonl"
    _write_trace(
        trace_path,
        [
            _base_trace_row(
                "SHOP_SCREEN",
                {
                    "type": "BuyPurgeAction",
                    "name": "purge",
                    "card_to_purge": {"name": "Strike"},
                },
                {
                    "type": "SHOP_SCREEN",
                    "cards": [{"name": "Perfected Strike", "price": 72}],
                    "relics": [],
                    "potions": [],
                    "purge_available": True,
                    "purge_cost": 75,
                },
            )
        ],
    )
    runs_dir = tmp_path / "runs"
    ironclad_dir = runs_dir / "IRONCLAD"
    ironclad_dir.mkdir(parents=True)
    (runs_dir / "ai_games.txt").write_text("1780000000\n", encoding="utf-8")
    (ironclad_dir / "1780000000.run").write_text(
        json.dumps({"victory": False, "floor_reached": 18, "playtime": 240}),
        encoding="utf-8",
    )
    report_path = tmp_path / "report.md"
    jsonl_path = tmp_path / "samples.jsonl"
    script_path = (
        Path(__file__).resolve().parents[1]
        / "analysis_scripts"
        / "noncombat_rl_decision_loop.py"
    )

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--trace",
            str(trace_path),
            "--runs-dir",
            str(runs_dir),
            "--character",
            "IRONCLAD",
            "--output",
            str(report_path),
            "--json-output",
            str(jsonl_path),
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Promotion status:" in result.stdout
    assert report_path.exists()
    assert json.loads(jsonl_path.read_text(encoding="utf-8").splitlines()[0])[
        "schema_version"
    ] == "noncombat-rl-decision-v1"
