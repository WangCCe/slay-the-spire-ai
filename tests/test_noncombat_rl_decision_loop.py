import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


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


def test_v2_frozen_source_summary_matches_contract():
    fixture_path = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "noncombat_policy_learning"
        / "frozen_20260710_summary.json"
    )

    summary = json.loads(fixture_path.read_text(encoding="utf-8"))

    assert summary == {
        "samples_path": "reports/noncombat_rl_decision_samples_20260710_post_exec_command_fixes_25_bottled.jsonl",
        "sha256": "77DA5265ACF7A447C2C76321BED66F0D65C7A5C6614188C42505381D32C7E186",
        "sample_count": 373,
        "matched_sample_count": 216,
        "matched_trajectory_count": 6,
        "victory_trajectory_count": 0,
        "category_counts": {
            "card_reward": 70,
            "event": 61,
            "route": 224,
            "shop": 18,
        },
        "matched_trajectory_counts": {
            "card_reward": 6,
            "event": 4,
            "route": 5,
            "shop": 3,
        },
    }


def test_v2_export_includes_explicit_behavior_provenance(tmp_path):
    from analysis_scripts.noncombat_rl_decision_loop import export_samples_from_trace

    trace_path = tmp_path / "trace.jsonl"
    _write_trace(
        trace_path,
        [
            _base_trace_row(
                "CARD_REWARD",
                {"type": "ChooseAction", "name": "Clothesline", "choice_index": 0},
                {
                    "type": "CARD_REWARD",
                    "cards": [{"name": "Clothesline"}],
                    "can_skip": True,
                    "can_bowl": False,
                },
            )
        ],
    )

    [sample] = export_samples_from_trace(
        trace_path,
        behavior_policy_id="current_heuristic",
        behavior_policy_commit="f321cb05",
    )

    assert sample["schema_version"] == "noncombat-rl-decision-v2"
    assert sample["trajectory_group_id"] is None
    assert sample["behavior_policy_id"] == "current_heuristic"
    assert sample["behavior_policy_commit"] == "f321cb05"
    assert sample["behavior_action_probability"] is None
    assert sample["behavior_probability_status"] == "unknown"


def test_v2_export_respects_until_unix(tmp_path):
    from analysis_scripts.noncombat_rl_decision_loop import export_samples_from_trace

    first = _base_trace_row(
        "CARD_REWARD",
        {"type": "ChooseAction", "name": "Clothesline", "choice_index": 0},
        {
            "type": "CARD_REWARD",
            "cards": [{"name": "Clothesline"}],
            "can_skip": True,
            "can_bowl": False,
        },
    )
    second = dict(first)
    first["unix_time"] = 1780000010.0
    second["unix_time"] = 1780000011.0
    trace_path = tmp_path / "trace.jsonl"
    _write_trace(trace_path, [first, second])

    samples = export_samples_from_trace(trace_path, until_unix=1780000010.0)

    assert [sample["sample_id"] for sample in samples] == ["trace:0"]


def test_stable_sample_id_uses_absolute_line_number(tmp_path):
    from analysis_scripts.noncombat_rl_decision_loop import export_samples_from_trace

    trace_path = tmp_path / "trace.jsonl"
    _write_trace(
        trace_path,
        [
            {"unix_time": 1780000000.0},
            _base_trace_row(
                "CARD_REWARD",
                {"type": "ChooseAction", "name": "Clothesline", "choice_index": 0},
                {
                    "type": "CARD_REWARD",
                    "cards": [{"name": "Clothesline"}],
                    "can_skip": True,
                    "can_bowl": False,
                },
            ),
        ],
    )

    [full_trace_sample] = export_samples_from_trace(trace_path, tail=2)
    [tailed_sample] = export_samples_from_trace(trace_path, tail=1)

    assert full_trace_sample["sample_id"] == "trace:1"
    assert tailed_sample["sample_id"] == full_trace_sample["sample_id"]


def test_exporter_source_does_not_reference_live_runtime_paths():
    source_path = (
        Path(__file__).resolve().parents[1]
        / "analysis_scripts"
        / "noncombat_rl_decision_loop.py"
    )
    source = source_path.read_text(encoding="utf-8")

    assert "CommunicationMod" not in source
    assert "config.properties" not in source
    assert "checkpoints" not in source


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


def test_duplicate_shop_names_get_slot_unique_ids_without_changing_unique_ids():
    from analysis_scripts.noncombat_rl_decision_loop import normalize_candidates

    decision = SimpleNamespace(
        category="shop",
        context={
            "cards": [{"name": "Anger", "price": 55}],
            "relics": [],
            "potions": [
                {"name": "Swift Potion", "price": 49},
                {"name": "Swift Potion", "price": 48},
                {"name": "Fear Potion", "price": 50},
            ],
            "purge_available": False,
        },
    )

    candidates = normalize_candidates(decision)
    by_label = {}
    for candidate in candidates:
        by_label.setdefault(candidate["label"], []).append(candidate)

    assert [candidate["action_id"] for candidate in by_label["Swift Potion"]] == [
        "shop:buy_potion:swift_potion:slot:0",
        "shop:buy_potion:swift_potion:slot:1",
    ]
    assert [candidate["raw"]["shop_slot"] for candidate in by_label["Swift Potion"]] == [
        0,
        1,
    ]
    assert all(
        candidate["raw"]["shop_inventory"] == "potion"
        for candidate in by_label["Swift Potion"]
    )
    assert by_label["Fear Potion"][0]["action_id"] == "shop:buy_potion:fear_potion"
    assert by_label["Anger"][0]["action_id"] == "shop:buy_card:anger"
    assert by_label["leave"][0]["action_id"] == "shop:leave"


def test_name_only_duplicate_shop_labels_remain_ambiguous():
    from analysis_scripts.noncombat_rl_decision_loop import build_trainable_sample

    decision = SimpleNamespace(
        sample_id="duplicate-shop",
        category="shop",
        source="fixture",
        floor=3,
        act=1,
        evidence_quality="complete",
        limitations=[],
        our_choice={"kind": "purchase", "name": "Swift Potion"},
        context={
            "cards": [],
            "relics": [],
            "potions": [
                {"name": "Swift Potion", "price": 49},
                {"name": "Swift Potion", "price": 48},
            ],
            "purge_available": False,
        },
    )
    comparison = SimpleNamespace(
        current_choice="Swift Potion",
        reference_choice="Swift Potion",
        confidence="high",
        reason="fixture",
    )

    sample = build_trainable_sample(decision, comparison)

    assert sample["selected_action_id"] is None
    assert sample["current_policy_label"]["action_id"] is None
    assert sample["bottled_label"]["action_id"] is None


def test_attach_live_outcomes_matches_exactly_one_run():
    from analysis_scripts.noncombat_rl_decision_loop import attach_live_outcomes

    samples = [
        {
            "sample_id": "trace:0",
            "unix_time": 1780000010.0,
            "floor": 3,
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
    assert joined["trajectory_group_id"] == "run:1780000000"


def test_attach_live_outcomes_requires_ai_marking_and_never_matches_after_end():
    from analysis_scripts.noncombat_rl_decision_loop import attach_live_outcomes

    sample = {
        "sample_id": "trace:after-end",
        "unix_time": 1780000201.0,
        "floor": 3,
        "outcome": {"join_status": "missing"},
    }
    outcome = {
        "run_file": "1780000200.run",
        "start_unix": 1780000000,
        "end_unix": 1780000200,
        "victory": False,
        "floor_reached": 12,
        "killed_by": "Gremlin Nob",
        "playtime": 200,
        "ai_marked": True,
    }

    [after_end] = attach_live_outcomes([sample], [outcome])
    unmarked = dict(outcome)
    unmarked.pop("ai_marked")
    [without_marker] = attach_live_outcomes(
        [{**sample, "unix_time": 1780000100.0}],
        [unmarked],
    )

    assert after_end["outcome"]["join_status"] == "missing"
    assert after_end["trajectory_group_id"] is None
    assert without_marker["outcome"]["join_status"] == "missing"
    assert without_marker["trajectory_group_id"] is None


@pytest.mark.parametrize(
    ("sample_floor", "outcome_floor"),
    [
        (None, 12),
        ("not-a-floor", 12),
        (3, None),
        (3, "not-a-floor"),
        (3, 0),
    ],
)
def test_trajectory_group_requires_valid_floor_evidence(sample_floor, outcome_floor):
    from analysis_scripts.noncombat_rl_decision_loop import attach_live_outcomes

    [joined] = attach_live_outcomes(
        [
            {
                "sample_id": "trace:floor-evidence",
                "unix_time": 1780000010.0,
                "floor": sample_floor,
                "outcome": {"join_status": "missing"},
            }
        ],
        [
            {
                "run_file": "1780000000.run",
                "start_unix": 1780000000,
                "end_unix": 1780000200,
                "victory": False,
                "floor_reached": outcome_floor,
                "killed_by": "Gremlin Nob",
                "playtime": 200,
                "ai_marked": True,
            }
        ],
    )

    assert joined["outcome"]["join_status"] == "floor_inconsistent"
    assert joined["trajectory_group_id"] is None


def test_floor_zero_sample_preserves_unique_trajectory_group():
    from analysis_scripts.noncombat_rl_decision_loop import attach_live_outcomes

    [joined] = attach_live_outcomes(
        [
            {
                "sample_id": "trace:initial-route",
                "unix_time": 1780000010.0,
                "floor": 0,
                "outcome": {"join_status": "missing"},
            }
        ],
        [
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
        ],
    )

    assert joined["outcome"]["join_status"] == "matched"
    assert joined["trajectory_group_id"] == "run:1780000000"


def test_behavior_probability_requires_non_unknown_status(tmp_path):
    from analysis_scripts.noncombat_rl_decision_loop import export_samples_from_trace

    trace_path = tmp_path / "trace.jsonl"
    _write_trace(
        trace_path,
        [
            _base_trace_row(
                "CARD_REWARD",
                {"type": "ChooseAction", "name": "Clothesline", "choice_index": 0},
                {
                    "type": "CARD_REWARD",
                    "cards": [{"name": "Clothesline"}],
                    "can_skip": True,
                    "can_bowl": False,
                },
            )
        ],
    )

    with pytest.raises(ValueError, match="non-unknown probability status"):
        export_samples_from_trace(
            trace_path,
            behavior_action_probability=0.5,
            behavior_probability_status="unknown",
        )


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
            "floor": 3,
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
    assert attach_live_outcomes(missing, outcomes)[0]["trajectory_group_id"] is None
    joined = attach_live_outcomes(ambiguous, outcomes)[0]
    assert joined["outcome"]["join_status"] == "ambiguous"
    assert joined["outcome"]["included_in_gate"] is False
    assert joined["trajectory_group_id"] is None


def test_attach_live_outcomes_rejects_floor_inconsistent_match():
    from analysis_scripts.noncombat_rl_decision_loop import attach_live_outcomes

    samples = [
        {
            "sample_id": "trace:floor-too-high",
            "unix_time": 1780000100.0,
            "floor": 28,
            "outcome": {"join_status": "missing"},
        }
    ]
    outcomes = [
        {
            "run_file": "1780000000.run",
            "start_unix": 1780000000,
            "end_unix": 1780000200,
            "victory": False,
            "floor_reached": 21,
            "killed_by": "Centurion and Healer",
            "playtime": 200,
            "ai_marked": True,
        }
    ]

    [joined] = attach_live_outcomes(samples, outcomes)

    assert joined["outcome"]["join_status"] == "floor_inconsistent"
    assert joined["outcome"]["included_in_gate"] is False
    assert joined["trajectory_group_id"] is None


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
            "start_unix": 1779999760,
            "end_unix": 1780000000,
            "victory": False,
            "floor_reached": 18,
            "killed_by": "Slime Boss",
            "playtime": 240,
            "ai_marked": True,
        }
    ]


@pytest.mark.parametrize(
    ("marker", "expected"),
    [(1779999999, False), (1780000001, True), (1780000031, False)],
)
def test_load_run_outcomes_uses_bounded_post_completion_marker(
    tmp_path,
    marker,
    expected,
):
    from analysis_scripts.noncombat_rl_decision_loop import load_run_outcomes

    runs_dir = tmp_path / "runs"
    ironclad_dir = runs_dir / "IRONCLAD"
    ironclad_dir.mkdir(parents=True)
    (runs_dir / "ai_games.txt").write_text(f"{marker}\n", encoding="utf-8")
    (ironclad_dir / "1780000000.run").write_text(
        json.dumps({"victory": False, "floor_reached": 18, "playtime": 240}),
        encoding="utf-8",
    )

    [outcome] = load_run_outcomes(runs_dir, character="IRONCLAD", limit=1)

    assert outcome["ai_marked"] is expected


def test_ai_marker_is_assigned_only_to_nearest_prior_run(tmp_path):
    from analysis_scripts.noncombat_rl_decision_loop import load_run_outcomes

    runs_dir = tmp_path / "runs"
    ironclad_dir = runs_dir / "IRONCLAD"
    ironclad_dir.mkdir(parents=True)
    (runs_dir / "ai_games.txt").write_text("1780000003\n", encoding="utf-8")
    for completed_unix in (1780000000, 1780000001):
        (ironclad_dir / f"{completed_unix}.run").write_text(
            json.dumps({"victory": False, "floor_reached": 18, "playtime": 240}),
            encoding="utf-8",
        )

    outcomes = load_run_outcomes(runs_dir, character="IRONCLAD", limit=5)

    assert {
        outcome["run_file"]: outcome["ai_marked"] for outcome in outcomes
    } == {
        "1780000000.run": False,
        "1780000001.run": True,
    }


def test_explicit_run_files_override_limit_and_missing_names_raise(tmp_path):
    from analysis_scripts.noncombat_rl_decision_loop import load_run_outcomes

    runs_dir = tmp_path / "runs"
    ironclad_dir = runs_dir / "IRONCLAD"
    ironclad_dir.mkdir(parents=True)
    (runs_dir / "ai_games.txt").write_text("1780000000\n", encoding="utf-8")
    for start_unix in (1780000000, 1780000100, 1780000200):
        (ironclad_dir / f"{start_unix}.run").write_text(
            json.dumps({"victory": False, "floor_reached": 18, "playtime": 240}),
            encoding="utf-8",
        )

    outcomes = load_run_outcomes(
        runs_dir,
        character="IRONCLAD",
        limit=1,
        run_files=["1780000000.run", "1780000200.run"],
    )

    assert [outcome["run_file"] for outcome in outcomes] == [
        "1780000000.run",
        "1780000200.run",
    ]
    with pytest.raises(FileNotFoundError, match="missing.run"):
        load_run_outcomes(runs_dir, character="IRONCLAD", run_files=["missing.run"])


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


def test_report_names_export_evidence_presence_gate_and_support_grain():
    from analysis_scripts.noncombat_rl_decision_loop import (
        default_reward_contract,
        evaluate_promotion,
        render_readiness_report,
    )

    samples = [
        _complete_sample(category)
        for category in ["shop", "event", "route", "card_reward"]
    ]
    for index, sample in enumerate(samples):
        sample["trajectory_group_id"] = f"run:{index // 2}"
        sample["outcome"]["victory"] = index < 2
    gate = evaluate_promotion(samples, reward_contract=default_reward_contract())

    report = render_readiness_report(samples, gate)

    assert "# Non-Combat RL Decision Loop Readiness" in report
    assert report.splitlines()[2] == (
        "This export evidence-presence gate does not authorize formal non-combat "
        "RL training or live-policy promotion."
    )
    assert "Export evidence-presence gate: passed" in report
    assert "Evidence-presence blocking reasons: none" in report
    assert "## Export Evidence-Presence Gate" in report
    assert "Audit-field presence:" in report
    assert "Matched decision rows: 4" in report
    assert "Unique non-null trajectory groups: 2" in report
    assert "Unique trajectory victories: 1" in report
    assert "Formal non-combat RL training: blocked" in report
    assert "Live policy promotion: blocked" in report
    assert "Off-policy evaluation: unsupported" in report
    assert "Promotion status" not in report
    assert "## Promotion Gate" not in report
    assert "## Reward readiness" not in report


def test_report_renders_blocked_export_evidence_presence_gate():
    from analysis_scripts.noncombat_rl_decision_loop import (
        evaluate_promotion,
        render_readiness_report,
    )

    samples = [
        _complete_sample(category)
        for category in ["shop", "event", "route", "card_reward"]
    ]
    gate = evaluate_promotion(samples, reward_contract=None)

    report = render_readiness_report(samples, gate)

    assert "Export evidence-presence gate: blocked" in report
    assert "Evidence-presence blocking reasons: reward_contract_missing" in report
    assert "Formal non-combat RL training: blocked" in report
    assert "Live policy promotion: blocked" in report
    assert "Off-policy evaluation: unsupported" in report


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
            "--until-unix",
            "1780000000",
            "--run-limit",
            "1",
            "--run-file",
            "1780000000.run",
            "--behavior-policy-id",
            "current_heuristic",
            "--behavior-policy-commit",
            "f321cb05",
            "--output",
            str(report_path),
            "--json-output",
            str(jsonl_path),
        ]
    )

    assert exit_code == 0
    assert "Export evidence-presence gate: blocked" in capsys.readouterr().out
    assert "Formal non-combat RL training: blocked" in report_path.read_text(
        encoding="utf-8"
    )
    [sample_line] = jsonl_path.read_text(encoding="utf-8").splitlines()
    sample = json.loads(sample_line)
    assert sample["schema_version"] == "noncombat-rl-decision-v2"
    assert sample["trajectory_group_id"] == "run:1780000000"
    assert sample["behavior_policy_id"] == "current_heuristic"
    assert sample["behavior_policy_commit"] == "f321cb05"
    assert sample["behavior_action_probability"] is None
    assert sample["behavior_probability_status"] == "unknown"


def test_cli_prints_passed_export_evidence_presence_gate(
    tmp_path, capsys, monkeypatch
):
    import analysis_scripts.noncombat_rl_decision_loop as decision_loop

    samples = [
        _complete_sample(category)
        for category in ["shop", "event", "route", "card_reward"]
    ]
    monkeypatch.setattr(
        decision_loop,
        "export_samples_from_trace",
        lambda *args, **kwargs: samples,
    )

    exit_code = decision_loop.main(["--trace", str(tmp_path / "unused.jsonl")])

    assert exit_code == 0
    stdout = capsys.readouterr().out
    assert "Export evidence-presence gate: passed" in stdout
    assert "Promotion status" not in stdout


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
    assert "Export evidence-presence gate: blocked" in result.stdout
    assert report_path.exists()
    assert json.loads(jsonl_path.read_text(encoding="utf-8").splitlines()[0])[
        "schema_version"
    ] == "noncombat-rl-decision-v2"
