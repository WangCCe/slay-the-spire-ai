import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import replace
from types import SimpleNamespace

import pytest


V2 = "noncombat-rl-decision-v2"


def test_offline_pilot_preserves_live_import_launcher_and_checkpoint_boundaries():
    root = Path(__file__).resolve().parents[1]
    live_sources = {
        "main": (root / "main.py").read_text(encoding="utf-8"),
        "batch_launcher": (root / "scripts" / "run_training_batch.py").read_text(
            encoding="utf-8"
        ),
        "game_launcher": (root / "scripts" / "restart_sts_modded.ps1").read_text(
            encoding="utf-8"
        ),
    }
    offline_sources = "\n".join(
        (root / "analysis_scripts" / name).read_text(encoding="utf-8")
        for name in (
            "noncombat_policy_dataset.py",
            "noncombat_policy_learning.py",
            "noncombat_policy_model.py",
        )
    )

    for live_source in live_sources.values():
        assert "noncombat_policy_learning" not in live_source
        assert "noncombat_policy_dataset" not in live_source
        assert "noncombat_policy_model" not in live_source
    assert 'pattern = os.path.join(checkpoint_dir, "rl_combat_model_ep*.pth")' in live_sources["main"]
    assert 'parser.add_argument("--checkpoint-dir", default="checkpoints")' in live_sources[
        "batch_launcher"
    ]
    assert (
        '[string]$ModIds = "basemod,CommunicationMod,superfastmode,StSExporter"'
        in live_sources["game_launcher"]
    )
    assert "config.properties" not in offline_sources
    assert "CommunicationMod" not in offline_sources


def test_frozen_correction_source_manifest_records_required_boundaries():
    manifest_path = (
        Path(__file__).resolve().parents[1]
        / "reports"
        / "noncombat_policy_learning_source_20260712.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["review_status"] == "approved_duplicate_candidate_evidence"
    assert manifest["raw_evidence_review"] == {
        "verdict": "APPROVED_DUPLICATE_CANDIDATE_EVIDENCE",
        "critical_findings": 0,
        "important_findings": 0,
        "minor_findings": 0,
        "reviewed_evidence": {
            "artifact_hash_closures": True,
            "dataset_rows": {"current": 470, "bottled": 387},
            "focused_tests": 101,
            "metrics_tolerance": 1e-12,
            "split_trajectories": {"train": 8, "validation": 2, "test": 4},
            "zero_duplicate_candidate_ids": True,
        },
    }
    assert manifest["behavior_candidate"] == (
        "f321cb05a40c808d3abfba8b977dfe8988b8ee47"
    )
    assert manifest["commits"] == {
        "current_evidence_base": "1f39503e5ee31fb937c765ce4af49c28c2fc0618",
        "policy_implementation": "7b372cfdf0af7fb31acf42d119352926d1b92e7f",
        "behavior_candidate": "f321cb05a40c808d3abfba8b977dfe8988b8ee47",
    }
    assert manifest["source_report"] == {
        "path": "reports/trainable_baseline_qualification_batch2_retry1.md",
        "sha256": "B526552829D3B844F141C48A081C461E7CDE9F97F1948B6F24473702CF628148",
    }
    assert manifest["post_isolation"]["status"] == "unchanged"
    assert manifest["post_isolation"]["captured"] is True
    assert manifest["post_isolation"]["compared_to"] == (
        "duplicate_candidate_correction_pre_isolation"
    )
    assert manifest["post_isolation"]["captured_at_utc"] == (
        "2026-07-12T02:01:54.9780934Z"
    )
    assert manifest["post_isolation"]["comparison"] == {
        "communication_mod_config": "unchanged",
        "active_combat_checkpoint_inventory": "unchanged",
    }
    assert manifest["prior_phase_b_post_isolation"]["status"] == "superseded"
    assert manifest["prior_phase_b_post_isolation"]["captured_at_utc"] == (
        "2026-07-12T00:15:29.5266754Z"
    )
    assert [entry["verdict"] for entry in manifest["review_history"]] == [
        "APPROVED_FOR_PHASE_B",
        "PENDING_DUPLICATE_CANDIDATE_RE_REVIEW",
    ]
    assert manifest["final_whole_change_review"]["artifact_transaction_fix_commit"] == (
        "1fbbc01c7b2ea04a9dd2d58288a0cfb50f8e3d26"
    )
    assert manifest["final_whole_change_review"]["artifact_hash_recheck"] == {
        "count": 14,
        "all_unchanged": True,
        "transaction_debris_count": 0,
    }
    assert manifest["boundaries"]["formal_noncombat_rl_performed"] is False
    assert manifest["boundaries"]["formal_noncombat_rl_training_ready"] is False
    assert manifest["boundaries"]["live_policy_promotion_performed"] is False
    assert manifest["boundaries"]["live_policy_promotion_ready"] is False


def _sample(sample_id, group_id="run:1", **overrides):
    category = overrides.get("category", "route")
    sample = {
        "schema_version": V2,
        "sample_id": sample_id,
        "source": {"trace": "fixture.jsonl", "line": sample_id},
        "trajectory_group_id": group_id,
        "category": category,
        "state": {"floor": 1, "gold": 99},
        "candidate_actions": [
            {
                "action_id": f"{category}:choice:0",
                "kind": "map_node",
                "label": "route 0",
                "available": True,
                "raw": {"choice": 0},
            },
            {
                "action_id": f"{category}:choice:1",
                "kind": "map_node",
                "label": "route 1",
                "available": False,
                "raw": {"choice": 1},
            },
        ],
        "selected_action_id": f"{category}:choice:0",
        "current_policy_label": {
            "action_id": f"{category}:choice:0",
            "label": "selected current action",
            "source": "current_heuristic",
        },
        "bottled_label": {
            "action_id": f"{category}:choice:0",
            "oracle_mode": "native_bottled",
            "confidence": "high",
            "source": {"strategy": "REQUESTED_STRIKE"},
        },
        "behavior_policy_id": "current_heuristic",
        "behavior_policy_commit": "f321cb05",
        "behavior_action_probability": None,
        "behavior_probability_status": "unknown",
        "outcome": {"join_status": "matched", "victory": False},
    }
    sample.update(overrides)
    return sample


def _row(sample_id, group_id, category="route"):
    from analysis_scripts.noncombat_policy_dataset import PolicyRow

    return PolicyRow(
        sample_id=sample_id,
        trajectory_group_id=group_id,
        category=category,
        state={"floor": 1},
        candidates=(
            {
                "action_id": f"{category}:choice:0",
                "kind": "choice",
                "label": "choice 0",
                "available": True,
                "raw": {},
            },
        ),
        target_action_id=f"{category}:choice:0",
        outcome={"join_status": "matched", "victory": False},
    )


def test_current_dataset_excludes_legacy_and_unresolved_rows(tmp_path):
    from analysis_scripts.noncombat_policy_dataset import build_policy_dataset

    source = tmp_path / "samples.jsonl"
    source.write_text("source\n", encoding="utf-8")
    samples = [
        _sample("eligible"),
        _sample("legacy", schema_version="noncombat-rl-decision-v1"),
        _sample("missing-join", group_id=None, outcome={"join_status": "missing"}),
        _sample("ambiguous-join", group_id=None, outcome={"join_status": "ambiguous"}),
        _sample("missing-behavior", behavior_policy_id=None),
        _sample("missing-candidates", candidate_actions=[]),
        _sample("missing-target", selected_action_id=None),
        _sample("unmapped-target", selected_action_id="route:choice:99"),
    ]

    dataset = build_policy_dataset(
        samples,
        label_mode="current",
        source_paths=[source],
        source_commit="ccc5c480",
    )

    assert [row.sample_id for row in dataset.rows] == ["eligible"]
    assert dataset.rows[0].candidates == (samples[0]["candidate_actions"][0],)
    assert dataset.manifest["exclusions"] == {
        "legacy_schema": 1,
        "missing_behavior_policy": 1,
        "missing_candidates": 1,
        "missing_target": 1,
        "missing_trajectory_group": 2,
        "target_not_candidate": 1,
    }


def test_policy_dataset_excludes_duplicate_candidate_ids(tmp_path):
    from analysis_scripts.noncombat_policy_dataset import build_policy_dataset

    source = tmp_path / "samples.jsonl"
    source.write_text("source\n", encoding="utf-8")
    sample = _sample("duplicate-candidate")
    sample["candidate_actions"][1]["action_id"] = sample["candidate_actions"][0][
        "action_id"
    ]
    sample["candidate_actions"][1]["available"] = True

    dataset = build_policy_dataset(
        [sample],
        label_mode="current",
        source_paths=[source],
        source_commit="ccc5c480",
    )

    assert dataset.rows == ()
    assert dataset.manifest["exclusions"] == {"duplicate_candidate_id": 1}


def test_bottled_dataset_requires_native_high_confidence_mapped_labels(tmp_path):
    from analysis_scripts.noncombat_policy_dataset import build_policy_dataset

    source = tmp_path / "samples.jsonl"
    source.write_text("source\n", encoding="utf-8")
    native = _sample("native")
    non_native = _sample(
        "non-native",
        bottled_label={
            "action_id": "route:choice:0",
            "oracle_mode": "bottled_style",
            "confidence": "high",
        },
    )
    low_confidence = _sample(
        "low-confidence",
        bottled_label={
            "action_id": "route:choice:0",
            "oracle_mode": "native_bottled",
            "confidence": "low",
        },
    )
    missing_target = _sample(
        "missing-target",
        bottled_label={
            "action_id": None,
            "oracle_mode": "native_bottled",
            "confidence": "high",
        },
    )
    unmapped = _sample(
        "unmapped",
        bottled_label={
            "action_id": "route:choice:99",
            "oracle_mode": "native_bottled",
            "confidence": "high",
        },
    )

    dataset = build_policy_dataset(
        [native, non_native, low_confidence, missing_target, unmapped],
        label_mode="bottled",
        source_paths=[source],
        source_commit="ccc5c480",
    )

    assert [row.sample_id for row in dataset.rows] == ["native"]
    assert dataset.manifest["exclusions"] == {
        "bottled_confidence": 1,
        "bottled_not_native": 1,
        "missing_target": 1,
        "target_not_candidate": 1,
    }
    assert dataset.manifest["label_mode_counts"] == {"bottled": 1, "current": 0}


def test_manifest_is_canonical_and_counts_unknown_probability_without_fabrication(tmp_path):
    from analysis_scripts.noncombat_policy_dataset import build_policy_dataset, to_json_value

    source_a = tmp_path / "a.jsonl"
    source_b = tmp_path / "b.jsonl"
    source_a.write_text('{"source":"a"}\n', encoding="utf-8")
    source_b.write_text('{"source":"b"}\n', encoding="utf-8")
    unknown = _sample("z", group_id="run:z", category="shop")
    known = _sample(
        "a",
        group_id="run:a",
        category="event",
        behavior_action_probability=1.0,
        behavior_probability_status="deterministic",
        outcome={"join_status": "matched", "victory": True},
    )

    first = build_policy_dataset(
        [unknown, known],
        label_mode="current",
        source_paths=[source_b, source_a],
        source_commit="ccc5c480",
    )
    second = build_policy_dataset(
        [known, unknown],
        label_mode="current",
        source_paths=[source_a, source_b],
        source_commit="ccc5c480",
    )

    assert [row.sample_id for row in first.rows] == ["a", "z"]
    assert first.manifest == second.manifest
    assert first.manifest["source_hashes"] == {
        str(source_a): hashlib.sha256(source_a.read_bytes()).hexdigest(),
        str(source_b): hashlib.sha256(source_b.read_bytes()).hexdigest(),
    }
    assert first.manifest["schema_versions"] == {V2: 2}
    assert first.manifest["category_counts"] == {"event": 1, "shop": 1}
    assert first.manifest["trajectory_counts"] == {"event": 1, "overall": 2, "shop": 1}
    assert first.manifest["outcome_counts"] == {
        "rows": {
            "join_status": {"matched": 2},
            "victory": {"false": 1, "true": 1, "unknown": 0},
        },
        "trajectories": {
            "join_status": {"matched": 2},
            "victory": {"false": 1, "true": 1, "unknown": 0},
        },
    }
    assert first.manifest["action_support"] == {
        "available_candidate_action_counts": {
            "event:choice:0": 1,
            "shop:choice:0": 1,
        },
        "target_action_counts": {
            "event:choice:0": 1,
            "shop:choice:0": 1,
        },
    }
    assert first.manifest["behavior_probability_counts"] == {"known": 1, "unknown": 1}
    assert first.manifest["label_mode_counts"] == {"bottled": 0, "current": 2}
    canonical = json.dumps(
        to_json_value(first.manifest), sort_keys=True, separators=(",", ":")
    )
    assert first.manifest["manifest_hash"] == hashlib.sha256(
        canonical.replace(
            f'"manifest_hash":"{first.manifest["manifest_hash"]}"',
            '"manifest_hash":null',
        ).encode("utf-8")
    ).hexdigest()


def test_trajectory_splits_are_grouped_repeatable_and_sixty_twenty_twenty():
    from analysis_scripts.noncombat_policy_dataset import assign_trajectory_splits

    rows = [_row(f"sample-{index}", f"run:{index:02d}") for index in range(10)]
    rows.append(_row("same-group", "run:00", category="shop"))

    first = assign_trajectory_splits(rows, split_seed="pilot-seed")
    second = assign_trajectory_splits(list(reversed(rows)), split_seed="pilot-seed")

    assert {split: len(groups) for split, groups in first.groups.items()} == {
        "train": 6,
        "validation": 2,
        "test": 2,
    }
    assert first == second
    assert first.manifest["manifest_hash"] == second.manifest["manifest_hash"]
    assigned_groups = [group for groups in first.groups.values() for group in groups]
    assert len(assigned_groups) == len(set(assigned_groups)) == 10
    assert first.assignments["run:00"] in {"train", "validation", "test"}


def test_support_gate_blocks_insufficient_overall_or_category_coverage():
    from analysis_scripts.noncombat_policy_dataset import (
        DatasetBuild,
        assign_trajectory_splits,
        evaluate_support,
        to_json_value,
    )

    rows = [_row(f"route-{index}", f"run:{index:02d}") for index in range(10)]
    baseline_splits = assign_trajectory_splits(rows, split_seed="pilot-seed")
    only_train_group = baseline_splits.groups["train"][0]
    rows.append(_row("shop-only", only_train_group, category="shop"))
    dataset = DatasetBuild(rows=tuple(rows), manifest={})
    splits = assign_trajectory_splits(dataset.rows, split_seed="pilot-seed")

    support = evaluate_support(dataset, splits)

    assert support["overall"]["blocked"] is False
    assert support["categories"]["route"]["evaluable"] is True
    assert to_json_value(support["categories"]["shop"]) == {
        "blocking_reasons": ["insufficient_train_trajectories", "missing_held_out_trajectory"],
        "evaluable": False,
        "held_out_trajectory_count": 0,
        "train_trajectory_count": 1,
    }

    undersized_rows = [_row(f"small-{index}", f"run:small-{index}") for index in range(9)]
    undersized = DatasetBuild(rows=tuple(undersized_rows), manifest={})
    undersized_support = evaluate_support(
        undersized,
        assign_trajectory_splits(undersized.rows, split_seed="pilot-seed"),
        min_trajectories=1,
    )

    assert undersized_support["overall"]["blocked"] is True
    assert "insufficient_trajectory_groups" in undersized_support["overall"]["blocking_reasons"]


def test_bottled_confidence_configuration_cannot_lower_the_high_gate(tmp_path):
    from analysis_scripts.noncombat_policy_dataset import build_policy_dataset

    source = tmp_path / "samples.jsonl"
    source.write_text("source\n", encoding="utf-8")
    low_confidence = _sample(
        "low-confidence",
        bottled_label={
            "action_id": "route:choice:0",
            "oracle_mode": "native_bottled",
            "confidence": "low",
            "source": {"strategy": "REQUESTED_STRIKE"},
        },
    )

    with pytest.raises(ValueError, match="literal 'high'"):
        build_policy_dataset(
            [low_confidence],
            label_mode="bottled",
            source_paths=[source],
            source_commit="ccc5c480",
            bottled_confidence="low",
        )


def test_policy_rows_retain_current_and_bottled_provenance_immutably(tmp_path):
    from analysis_scripts.noncombat_policy_dataset import build_policy_dataset, to_json_value

    source = tmp_path / "samples.jsonl"
    source.write_text("source\n", encoding="utf-8")
    sample = _sample("provenance")

    current = build_policy_dataset(
        [sample],
        label_mode="current",
        source_paths=[source],
        source_commit="ccc5c480",
    ).rows[0]
    bottled = build_policy_dataset(
        [sample],
        label_mode="bottled",
        source_paths=[source],
        source_commit="ccc5c480",
    ).rows[0]

    assert current.source == sample["source"]
    assert current.label_mode == "current"
    assert current.behavior_policy_id == "current_heuristic"
    assert current.behavior_policy_commit == "f321cb05"
    assert current.behavior_action_probability is None
    assert current.behavior_probability_status == "unknown"
    assert current.label_provenance == {
        "mode": "current",
        "selected_label": sample["current_policy_label"],
    }
    assert bottled.label_provenance == {
        "mode": "bottled",
        "selected_label": sample["bottled_label"],
    }
    with pytest.raises(TypeError):
        current.state["floor"] = 9
    with pytest.raises(TypeError):
        current.label_provenance["mode"] = "bottled"
    assert to_json_value(current.label_provenance) == {
        "mode": "current",
        "selected_label": sample["current_policy_label"],
    }


def test_manifest_and_split_values_are_deeply_immutable(tmp_path):
    from analysis_scripts.noncombat_policy_dataset import (
        assign_trajectory_splits,
        build_policy_dataset,
        to_json_value,
    )

    source = tmp_path / "samples.jsonl"
    source.write_text("source\n", encoding="utf-8")
    dataset = build_policy_dataset(
        [_sample("immutable")],
        label_mode="current",
        source_paths=[source],
        source_commit="ccc5c480",
    )
    splits = assign_trajectory_splits(dataset.rows, split_seed="pilot-seed")

    with pytest.raises(TypeError):
        dataset.manifest["source_hashes"][str(source)] = "changed"
    with pytest.raises(TypeError):
        splits.assignments["run:1"] = "test"
    with pytest.raises((AttributeError, TypeError)):
        splits.manifest["groups"]["train"].append("run:new")
    assert json.loads(json.dumps(to_json_value(dataset.manifest), sort_keys=True))[
        "source_commit"
    ] == "ccc5c480"


def test_jsonl_input_is_auditable_and_malformed_lines_fail_with_context(tmp_path):
    from analysis_scripts.noncombat_policy_dataset import build_policy_dataset, iter_jsonl

    readable = tmp_path / "readable.jsonl"
    readable.write_text('{"schema_version":"noncombat-rl-decision-v1"}\n["not", "a", "mapping"]\n', encoding="utf-8")
    assert list(iter_jsonl(readable)) == [
        {"schema_version": "noncombat-rl-decision-v1"},
        ["not", "a", "mapping"],
    ]

    source = tmp_path / "samples.jsonl"
    source.write_text("source\n", encoding="utf-8")
    dataset = build_policy_dataset(
        [_sample("eligible"), ["not", "a", "mapping"]],
        label_mode="current",
        source_paths=[source],
        source_commit="ccc5c480",
    )
    assert dataset.manifest["input_sample_count"] == 2
    assert dataset.manifest["input_sample_count"] == (
        dataset.manifest["eligible_row_count"] + sum(dataset.manifest["exclusions"].values())
    )
    assert dataset.manifest["schema_versions"]["<non-mapping>"] == 1

    malformed = tmp_path / "malformed.jsonl"
    malformed.write_text('{"ok": true}\n{"bad":\n', encoding="utf-8")
    with pytest.raises(ValueError, match=r"malformed\.jsonl:2: malformed JSON"):
        list(iter_jsonl(malformed))


def test_malformed_candidates_are_excluded_from_policy_rows(tmp_path):
    from analysis_scripts.noncombat_policy_dataset import build_policy_dataset

    source = tmp_path / "samples.jsonl"
    source.write_text("source\n", encoding="utf-8")
    valid = _sample("valid")
    valid["candidate_actions"].append(
        {
            "action_id": "route:choice:bad",
            "kind": 7,
            "label": "bad",
            "available": True,
            "raw": "not-a-mapping",
        }
    )
    malformed_only = _sample(
        "malformed-only",
        candidate_actions=[
            {
                "action_id": "route:choice:0",
                "kind": 7,
                "label": "bad",
                "available": True,
                "raw": {},
            }
        ],
    )

    dataset = build_policy_dataset(
        [valid, malformed_only],
        label_mode="current",
        source_paths=[source],
        source_commit="ccc5c480",
    )

    assert [candidate["action_id"] for candidate in dataset.rows[0].candidates] == [
        "route:choice:0"
    ]
    assert dataset.manifest["exclusions"] == {"missing_candidates": 1}


def test_support_reports_empty_splits_all_categories_and_overall_blocking():
    from analysis_scripts.noncombat_policy_dataset import (
        DatasetBuild,
        assign_trajectory_splits,
        evaluate_support,
        to_json_value,
    )

    tiny = DatasetBuild(rows=(_row("one", "run:one"),), manifest={})
    tiny_support = evaluate_support(
        tiny,
        assign_trajectory_splits(tiny.rows, split_seed="pilot-seed"),
    )

    assert to_json_value(tiny_support["overall"]["blocking_reasons"]) == [
        "insufficient_trajectory_groups",
        "empty_train_split",
        "empty_validation_split",
    ]
    assert set(tiny_support["categories"]) == {
        "shop",
        "event",
        "route",
        "card_reward",
    }
    assert tiny_support["categories"]["event"]["evaluable"] is False

    rows = [_row(f"route-{index}", f"run:{index}") for index in range(5)]
    dataset = DatasetBuild(rows=tuple(rows), manifest={})
    support = evaluate_support(
        dataset,
        assign_trajectory_splits(dataset.rows, split_seed="pilot-seed"),
    )

    assert support["categories"]["route"]["evaluable"] is False
    assert "overall_support_blocked" in support["categories"]["route"][
        "blocking_reasons"
    ]


def test_action_and_outcome_support_keep_target_candidate_and_trajectory_counts(tmp_path):
    from analysis_scripts.noncombat_policy_dataset import build_policy_dataset

    source = tmp_path / "samples.jsonl"
    source.write_text("source\n", encoding="utf-8")
    samples = [
        _sample("true-a", group_id="run:true", outcome={"join_status": "matched", "victory": True}),
        _sample("true-b", group_id="run:true", outcome={"join_status": "matched", "victory": True}),
        _sample("false", group_id="run:false", outcome={"join_status": "matched", "victory": False}),
        _sample("unknown", group_id="run:unknown", outcome={"join_status": "missing"}),
    ]
    samples[0]["candidate_actions"].append(
        {
            "action_id": "route:choice:extra",
            "kind": "map_node",
            "label": "extra",
            "available": True,
            "raw": {"choice": 2},
        }
    )

    manifest = build_policy_dataset(
        samples,
        label_mode="current",
        source_paths=[source],
        source_commit="ccc5c480",
    ).manifest

    assert manifest["action_support"] == {
        "available_candidate_action_counts": {
            "route:choice:0": 4,
            "route:choice:extra": 1,
        },
        "target_action_counts": {"route:choice:0": 4},
    }
    assert manifest["outcome_counts"] == {
        "rows": {
            "join_status": {"matched": 3, "missing": 1},
            "victory": {"false": 1, "true": 2, "unknown": 1},
        },
        "trajectories": {
            "join_status": {"matched": 2, "missing": 1},
            "victory": {"false": 1, "true": 1, "unknown": 1},
        },
    }


@pytest.mark.parametrize(
    ("status", "probability"),
    [
        ("unknown", 0.5),
        ("deterministic", None),
        ("deterministic", True),
        ("deterministic", {"probability": 0.5}),
        ("deterministic", [0.5]),
        ("deterministic", -0.01),
        ("deterministic", 1.01),
        ("deterministic", float("nan")),
        ("deterministic", float("inf")),
        ("deterministic", float("-inf")),
    ],
)
def test_invalid_behavior_propensity_pairs_are_excluded(tmp_path, status, probability):
    from analysis_scripts.noncombat_policy_dataset import build_policy_dataset

    source = tmp_path / "samples.jsonl"
    source.write_text("source\n", encoding="utf-8")
    dataset = build_policy_dataset(
        [
            _sample(
                "invalid-propensity",
                behavior_action_probability=probability,
                behavior_probability_status=status,
            )
        ],
        label_mode="current",
        source_paths=[source],
        source_commit="ccc5c480",
    )

    assert dataset.rows == ()
    assert dataset.manifest["exclusions"] == {"invalid_behavior_probability": 1}
    assert dataset.manifest["input_sample_count"] == (
        dataset.manifest["eligible_row_count"] + sum(dataset.manifest["exclusions"].values())
    )


def test_behavior_propensity_normalizes_unknown_and_preserves_known_boundaries(tmp_path):
    from analysis_scripts.noncombat_policy_dataset import build_policy_dataset

    source = tmp_path / "samples.jsonl"
    source.write_text("source\n", encoding="utf-8")
    absent_status = _sample("absent-status")
    absent_status.pop("behavior_probability_status")
    dataset = build_policy_dataset(
        [
            _sample(
                "known-zero",
                behavior_action_probability=0,
                behavior_probability_status="deterministic",
            ),
            _sample(
                "known-one",
                behavior_action_probability=1,
                behavior_probability_status="deterministic",
            ),
            _sample("blank-status", behavior_probability_status="   "),
            absent_status,
        ],
        label_mode="current",
        source_paths=[source],
        source_commit="ccc5c480",
    )

    by_id = {row.sample_id: row for row in dataset.rows}
    assert by_id["known-zero"].behavior_action_probability == 0.0
    assert isinstance(by_id["known-zero"].behavior_action_probability, float)
    assert by_id["known-one"].behavior_action_probability == 1.0
    assert by_id["blank-status"].behavior_action_probability is None
    assert by_id["blank-status"].behavior_probability_status == "unknown"
    assert by_id["absent-status"].behavior_action_probability is None
    assert by_id["absent-status"].behavior_probability_status == "unknown"
    assert dataset.manifest["behavior_probability_counts"] == {"known": 2, "unknown": 2}


def test_invalid_mutable_behavior_propensity_never_reaches_rows_or_manifest(tmp_path):
    from analysis_scripts.noncombat_policy_dataset import build_policy_dataset, to_json_value

    source = tmp_path / "samples.jsonl"
    source.write_text("source\n", encoding="utf-8")
    invalid_probability = [0.5]
    dataset = build_policy_dataset(
        [
            _sample("valid"),
            _sample(
                "invalid-mutable",
                behavior_action_probability=invalid_probability,
                behavior_probability_status="deterministic",
            ),
        ],
        label_mode="current",
        source_paths=[source],
        source_commit="ccc5c480",
    )
    manifest_before = to_json_value(dataset.manifest)

    invalid_probability.append(0.25)

    assert [row.sample_id for row in dataset.rows] == ["valid"]
    assert to_json_value(dataset.manifest) == manifest_before
    assert dataset.manifest["exclusions"] == {"invalid_behavior_probability": 1}


@pytest.mark.parametrize("status", [7, True, ["deterministic"], {"status": "deterministic"}])
def test_non_string_behavior_propensity_status_is_excluded(tmp_path, status):
    from analysis_scripts.noncombat_policy_dataset import build_policy_dataset

    source = tmp_path / "samples.jsonl"
    source.write_text("source\n", encoding="utf-8")
    dataset = build_policy_dataset(
        [
            _sample(
                "invalid-status",
                behavior_action_probability=0.5,
                behavior_probability_status=status,
            )
        ],
        label_mode="current",
        source_paths=[source],
        source_commit="ccc5c480",
    )

    assert dataset.rows == ()
    assert dataset.manifest["exclusions"] == {"invalid_behavior_probability": 1}
    assert dataset.manifest["input_sample_count"] == (
        dataset.manifest["eligible_row_count"] + sum(dataset.manifest["exclusions"].values())
    )


def test_oversized_behavior_propensity_is_excluded_without_overflow(tmp_path):
    from analysis_scripts.noncombat_policy_dataset import build_policy_dataset

    source = tmp_path / "samples.jsonl"
    source.write_text("source\n", encoding="utf-8")
    dataset = build_policy_dataset(
        [
            _sample(
                "oversized-propensity",
                behavior_action_probability=10**400,
                behavior_probability_status="deterministic",
            )
        ],
        label_mode="current",
        source_paths=[source],
        source_commit="ccc5c480",
    )

    assert dataset.rows == ()
    assert dataset.manifest["exclusions"] == {"invalid_behavior_probability": 1}
    assert dataset.manifest["input_sample_count"] == (
        dataset.manifest["eligible_row_count"] + sum(dataset.manifest["exclusions"].values())
    )


def test_behavior_propensity_status_casefolds_unknown(tmp_path):
    from analysis_scripts.noncombat_policy_dataset import build_policy_dataset

    source = tmp_path / "samples.jsonl"
    source.write_text("source\n", encoding="utf-8")
    [row] = build_policy_dataset(
        [
            _sample(
                "casefolded-unknown",
                behavior_action_probability=None,
                behavior_probability_status=" UNKNOWN ",
            )
        ],
        label_mode="current",
        source_paths=[source],
        source_commit="ccc5c480",
    ).rows

    assert row.behavior_probability_status == "unknown"
    assert row.behavior_action_probability is None


def _learning_row(
    sample_id,
    *,
    label_mode="current",
    state=None,
    candidates=None,
    target_action_id=None,
):
    from analysis_scripts.noncombat_policy_dataset import PolicyRow

    candidates = candidates or (
        {
            "action_id": "route:take",
            "kind": "choice",
            "label": "take",
            "available": True,
            "raw": {"signal": "target"},
        },
        {
            "action_id": "route:skip",
            "kind": "choice",
            "label": "skip",
            "available": True,
            "raw": {"signal": "other"},
        },
    )
    return PolicyRow(
        sample_id=sample_id,
        trajectory_group_id=f"run:{sample_id}",
        category="route",
        state=state or {"floor": 1},
        candidates=tuple(candidates),
        target_action_id=target_action_id or candidates[0]["action_id"],
        outcome={"join_status": "matched", "victory": False},
        label_mode=label_mode,
    )


def test_candidate_features_use_stable_signed_hashes_and_numeric_values():
    from analysis_scripts.noncombat_policy_model import (
        FeatureConfig,
        candidate_feature_vector,
    )

    config = FeatureConfig(hash_dim=1024)
    row = SimpleNamespace(
        state={"nested": {"z": None, "a": True}, "sequence": [3, "alpha"]}
    )
    reordered_row = SimpleNamespace(
        state={"sequence": [3, "alpha"], "nested": {"a": True, "z": None}}
    )
    candidate = {"action_id": "route:take", "raw": {"choice": "left"}}
    reordered_candidate = {"raw": {"choice": "left"}, "action_id": "route:take"}

    first = candidate_feature_vector(row, candidate, config)
    assert first.shape == (1024,)
    assert str(first.dtype) == "torch.float32"
    assert first.device.type == "cpu"
    assert first.equal(candidate_feature_vector(row, candidate, config))
    assert first.equal(candidate_feature_vector(reordered_row, reordered_candidate, config))
    assert not first.equal(
        candidate_feature_vector(
            SimpleNamespace(state={"nested": {"z": None, "a": False}, "sequence": [3, "alpha"]}),
            candidate,
            config,
        )
    )
    assert not first.equal(candidate_feature_vector(row, {"action_id": "route:skip", "raw": {"choice": "left"}}, config))

    categorical = candidate_feature_vector(SimpleNamespace(state={}), {"value": "yes"}, config)
    categorical_digest = hashlib.sha256(b"candidate.value=yes").digest()
    categorical_bin = int.from_bytes(categorical_digest[:8], "big") % config.hash_dim
    categorical_sign = -1.0 if categorical_digest[8] & 1 else 1.0
    assert categorical[categorical_bin].item() == categorical_sign

    numeric = candidate_feature_vector(SimpleNamespace(state={"amount": -math.e}), {}, config)
    numeric_digest = hashlib.sha256(b"state.amount").digest()
    numeric_bin = int.from_bytes(numeric_digest[:8], "big") % config.hash_dim
    assert numeric[numeric_bin].item() == pytest.approx(-math.log1p(math.e) / 10.0)

    clipped = candidate_feature_vector(SimpleNamespace(state={"amount": 10**400}), {}, config)
    assert clipped[numeric_bin].item() == 1.0

    with pytest.raises(ValueError, match="hash_dim"):
        candidate_feature_vector(row, candidate, FeatureConfig(hash_dim=0))


def test_predictions_mask_to_each_rows_available_candidates_in_order():
    from analysis_scripts.noncombat_policy_model import (
        CandidateRanker,
        FeatureConfig,
        predict_ranker,
    )

    short_row = _learning_row("short")
    long_row = _learning_row(
        "long",
        candidates=(
            {
                "action_id": "route:third",
                "kind": "choice",
                "label": "third",
                "available": True,
                "raw": {"signal": "third"},
            },
            {
                "action_id": "route:first",
                "kind": "choice",
                "label": "first",
                "available": True,
                "raw": {"signal": "first"},
            },
            {
                "action_id": "route:second",
                "kind": "choice",
                "label": "second",
                "available": True,
                "raw": {"signal": "second"},
            },
        ),
        target_action_id="route:second",
    )

    predictions = predict_ranker(
        CandidateRanker(input_dim=64),
        (long_row, short_row),
        feature_config=FeatureConfig(hash_dim=64),
    )

    assert [prediction.sample_id for prediction in predictions] == ["long", "short"]
    for row, prediction in zip((long_row, short_row), predictions):
        candidate_ids = [candidate["action_id"] for candidate in row.candidates]
        assert prediction.predicted_action_id in candidate_ids
        assert len(prediction.probabilities) == len(candidate_ids)
        assert prediction.confidence == max(prediction.probabilities)


def test_training_rejects_mixed_label_modes_and_illegal_targets():
    from analysis_scripts.noncombat_policy_model import (
        FeatureConfig,
        TrainingConfig,
        train_ranker,
    )

    current = _learning_row("current")
    bottled = replace(_learning_row("bottled"), label_mode="bottled")
    with pytest.raises(ValueError, match="label mode"):
        train_ranker(
            (current,),
            (bottled,),
            feature_config=FeatureConfig(),
            training_config=TrainingConfig(),
        )

    illegal_target = replace(current, target_action_id="route:not-a-candidate")
    with pytest.raises(ValueError, match="target_action_id"):
        train_ranker(
            (illegal_target,),
            (current,),
            feature_config=FeatureConfig(),
            training_config=TrainingConfig(),
        )

    duplicate_candidates = replace(
        current,
        candidates=(current.candidates[0], current.candidates[0]),
    )
    with pytest.raises(ValueError, match="candidate action_ids must be unique"):
        train_ranker(
            (duplicate_candidates,),
            (current,),
            feature_config=FeatureConfig(),
            training_config=TrainingConfig(),
        )

    with pytest.raises(ValueError, match="train rows"):
        train_ranker(
            (),
            (current,),
            feature_config=FeatureConfig(),
            training_config=TrainingConfig(),
        )
    with pytest.raises(ValueError, match="validation rows"):
        train_ranker(
            (current,),
            (),
            feature_config=FeatureConfig(),
            training_config=TrainingConfig(),
        )

    bottled_result = train_ranker(
        (bottled,),
        (bottled,),
        feature_config=FeatureConfig(),
        training_config=TrainingConfig(max_epochs=1),
    )
    assert bottled_result.artifact_manifest["artifact_stem"] == "noncombat_policy_bottled"


@pytest.mark.parametrize(
    "config",
    (
        ("device", "cuda"),
        ("max_epochs", 0),
        ("max_epochs", 51),
        ("patience", 0),
        ("patience", 6),
        ("learning_rate", 0.0),
        ("learning_rate", float("nan")),
        ("learning_rate", float("inf")),
    ),
)
def test_training_rejects_invalid_cpu_configurations(config):
    from analysis_scripts.noncombat_policy_model import (
        FeatureConfig,
        TrainingConfig,
        train_ranker,
    )

    field, value = config
    with pytest.raises(ValueError):
        train_ranker(
            (_learning_row("train"),),
            (_learning_row("validation"),),
            feature_config=FeatureConfig(),
            training_config=replace(TrainingConfig(), **{field: value}),
        )


def test_training_is_bounded_deterministic_and_keeps_promotion_flags_false():
    from analysis_scripts.noncombat_policy_model import (
        FeatureConfig,
        TrainingConfig,
        predict_ranker,
        train_ranker,
    )

    train_rows = tuple(_learning_row(f"train-{index}") for index in range(3))
    validation_rows = tuple(_learning_row(f"validation-{index}") for index in range(2))
    feature_config = FeatureConfig(hash_dim=128)
    training_config = TrainingConfig(seed=17, max_epochs=50, patience=5)

    first = train_ranker(
        train_rows,
        validation_rows,
        feature_config=feature_config,
        training_config=training_config,
    )
    second = train_ranker(
        tuple(reversed(train_rows)),
        tuple(reversed(validation_rows)),
        feature_config=feature_config,
        training_config=training_config,
    )

    assert first.epochs_run <= 50
    assert first.epochs_run == second.epochs_run
    assert first.epochs_run == len(first.history)
    assert first.epochs_run == len(second.history)
    for first_epoch, second_epoch in zip(first.history, second.history):
        assert first_epoch["epoch"] == second_epoch["epoch"]
        assert first_epoch["train_loss"] == pytest.approx(
            second_epoch["train_loss"], rel=0, abs=1e-7
        )
        assert first_epoch["validation_loss"] == pytest.approx(
            second_epoch["validation_loss"], rel=0, abs=1e-7
        )
    assert first.best_validation_loss == pytest.approx(
        second.best_validation_loss, rel=0, abs=1e-7
    )
    assert next(first.model.parameters()).device.type == "cpu"
    assert first.artifact_manifest["artifact_stem"] == "noncombat_policy_current"
    assert first.artifact_manifest["formal_noncombat_rl_training_ready"] is False
    assert first.artifact_manifest["live_policy_promotion_ready"] is False
    _assert_deterministic_manifest(
        first.artifact_manifest,
        second.artifact_manifest,
    )

    first_predictions = predict_ranker(first.model, validation_rows, feature_config=feature_config)
    second_predictions = predict_ranker(
        second.model,
        tuple(reversed(validation_rows)),
        feature_config=feature_config,
    )
    assert len(first_predictions) == len(second_predictions)
    for first_prediction, second_prediction in zip(first_predictions, second_predictions):
        assert first_prediction.sample_id == second_prediction.sample_id
        assert first_prediction.predicted_action_id == second_prediction.predicted_action_id
        assert first_prediction.target_action_id == second_prediction.target_action_id
        assert first_prediction.confidence == pytest.approx(
            second_prediction.confidence, rel=0, abs=1e-7
        )
        assert len(first_prediction.probabilities) == len(second_prediction.probabilities)
        for first_probability, second_probability in zip(
            first_prediction.probabilities,
            second_prediction.probabilities,
        ):
            assert first_probability == pytest.approx(
                second_probability, rel=0, abs=1e-7
            )

    single_candidate = _learning_row(
        "single",
        candidates=(
            {
                "action_id": "route:only",
                "kind": "choice",
                "label": "only",
                "available": True,
                "raw": {},
            },
        ),
        target_action_id="route:only",
    )
    early_stopped = train_ranker(
        (single_candidate,),
        (single_candidate,),
        feature_config=feature_config,
        training_config=TrainingConfig(seed=17, max_epochs=50, patience=5),
    )
    assert early_stopped.epochs_run == 6


def _two_candidate_row(
    sample_id,
    group_id,
    category,
    target_action_id,
    *,
    candidate_action_ids=None,
    label_mode="current",
):
    from analysis_scripts.noncombat_policy_dataset import PolicyRow

    candidate_action_ids = candidate_action_ids or (
        f"{category}:choice:0",
        f"{category}:choice:1",
    )
    return PolicyRow(
        sample_id=sample_id,
        trajectory_group_id=group_id,
        category=category,
        state={"floor": 1, "gold": 99},
        candidates=(
            {
                "action_id": candidate_action_ids[0],
                "kind": "choice",
                "label": "choice 0",
                "available": True,
                "raw": {"choice": 0},
            },
            {
                "action_id": candidate_action_ids[1],
                "kind": "choice",
                "label": "choice 1",
                "available": True,
                "raw": {"choice": 1},
            },
        ),
        target_action_id=target_action_id,
        outcome={"join_status": "matched", "victory": False},
        label_mode=label_mode,
        behavior_policy_id="current_heuristic",
        behavior_policy_commit="f321cb05",
    )


def _write_trainable_samples(path, *, group_count=10):
    samples = []
    for group_index in range(group_count):
        for category in ("shop", "event", "route", "card_reward"):
            sample = _sample(
                f"{category}-{group_index}",
                group_id=f"run:{group_index:02d}",
                category=category,
            )
            sample["candidate_actions"][1]["available"] = True
            selected_action_id = f"{category}:choice:{group_index % 2}"
            sample["selected_action_id"] = selected_action_id
            sample["current_policy_label"]["action_id"] = selected_action_id
            sample["bottled_label"]["action_id"] = selected_action_id
            samples.append(sample)
    path.write_text(
        "\n".join(json.dumps(sample, sort_keys=True) for sample in samples) + "\n",
        encoding="utf-8",
    )
    return samples


def test_held_out_metrics_use_train_frequency_counts_and_candidate_legal_predictions():
    from analysis_scripts.noncombat_policy_learning import (
        build_frequency_counts,
        evaluate_ranker,
        frequency_baseline_prediction,
    )
    from analysis_scripts.noncombat_policy_model import CandidateRanker, FeatureConfig

    train_rows = (
        _two_candidate_row("route-train-a", "run:train-a", "route", "route:choice:1"),
        _two_candidate_row("route-train-b", "run:train-b", "route", "route:choice:1"),
        _two_candidate_row("event-train", "run:train-c", "event", "event:choice:0"),
    )
    held_out_rows = (
        _two_candidate_row("route-held-a", "run:validation-a", "route", "route:choice:0"),
        _two_candidate_row("route-held-b", "run:test-a", "route", "route:choice:0"),
        _two_candidate_row(
            "event-held",
            "run:test-b",
            "event",
            "event:choice:a",
            candidate_action_ids=("event:choice:z", "event:choice:a"),
        ),
    )
    frequency_counts = build_frequency_counts(train_rows)
    assert frequency_counts == {
        "event": {"event:choice:0": 1},
        "route": {"route:choice:1": 2},
    }
    assert frequency_baseline_prediction(held_out_rows[2], frequency_counts) == "event:choice:a"

    model = CandidateRanker(input_dim=8)
    for parameter in model.parameters():
        parameter.data.zero_()
    metrics = evaluate_ranker(
        model,
        held_out_rows,
        feature_config=FeatureConfig(hash_dim=8),
        frequency_counts=frequency_counts,
    )

    assert metrics["sample_count"] == 3
    assert metrics["model_reference_top1_agreement"] == pytest.approx(2 / 3)
    assert metrics["mean_target_cross_entropy"] == pytest.approx(math.log(2))
    assert metrics["top_confidence_ece"] == pytest.approx(1 / 6)
    assert metrics["candidate_legality"] == 1.0
    assert metrics["frequency_reference_top1_agreement"] == pytest.approx(1 / 3)
    assert metrics["per_category_counts"] == {"event": 1, "route": 2}


def test_policy_reports_keep_supervised_results_and_outcomes_diagnostic_only():
    from analysis_scripts.noncombat_policy_learning import render_policy_report

    dataset_manifest = {
        "label_mode": "current",
        "source_commit": "f321cb05",
        "exclusions": {"missing_trajectory_group": 2, "target_not_candidate": 1},
        "behavior_probability_counts": {"known": 0, "unknown": 3},
        "outcome_counts": {
            "rows": {"join_status": {"matched": 2}, "victory": {"false": 2}},
            "trajectories": {"join_status": {"matched": 2}, "victory": {"false": 2}},
        },
    }
    split_manifest = {
        "groups": {"train": ["run:1", "run:2"], "validation": ["run:3"], "test": ["run:4"]}
    }
    support = {
        "overall": {
            "blocked": True,
            "blocking_reasons": ["insufficient_trajectory_groups"],
            "trajectory_count": 4,
            "split_trajectory_counts": {"train": 2, "validation": 1, "test": 1},
        },
        "categories": {
            category: {
                "evaluable": category == "route",
                "blocking_reasons": [] if category == "route" else ["missing_held_out_trajectory"],
                "train_trajectory_count": 2 if category == "route" else 0,
                "held_out_trajectory_count": 1 if category == "route" else 0,
            }
            for category in ("shop", "event", "route", "card_reward")
        },
        "outcome_counts": dataset_manifest["outcome_counts"],
    }
    metrics = {
        "validation": {"sample_count": 2, "model_reference_top1_agreement": 0.5},
        "test": {"sample_count": 1, "model_reference_top1_agreement": 1.0},
    }

    blocked_report = render_policy_report(dataset_manifest, split_manifest, support)
    supervised_report = render_policy_report(dataset_manifest, split_manifest, support, metrics=metrics)

    required_lines = (
        "Formal non-combat RL: blocked",
        "Live policy promotion: blocked",
        "Off-policy evaluation: unsupported",
        "Missing trajectories, target mappings, unknown behavior propensities, and contextual alternative-action overlap block off-policy evaluation.",
        "Aggregate candidate counts do not establish contextual alternative-action overlap.",
        "## Dataset exclusions",
        "## Category support",
        "## Split counts",
        "## Outcome diagnostics",
    )
    for report in (blocked_report, supervised_report):
        assert all(line in report for line in required_lines)
        assert "causal uplift" not in report.casefold()
        assert "reward-improvement" not in report.casefold()
    assert "## Held-out metrics" not in blocked_report
    assert "## Held-out metrics" in supervised_report
    assert "### Validation" in supervised_report
    assert "### Test" in supervised_report


def test_support_cli_is_torch_free_and_train_writes_only_supported_artifacts(tmp_path):
    from analysis_scripts.noncombat_policy_learning import main

    samples_path = tmp_path / "samples.jsonl"
    _write_trainable_samples(samples_path, group_count=9)
    support_output = tmp_path / "support-output"
    script_path = Path(__file__).parents[1] / "analysis_scripts" / "noncombat_policy_learning.py"

    def run_with_blocked_model(arguments):
        program = "\n".join(
            (
                "import builtins, runpy, sys",
                "original_import = builtins.__import__",
                "def blocked_import(name, globals=None, locals=None, fromlist=(), level=0):",
                "    if name == 'torch' or name.startswith('torch.') or name == 'analysis_scripts.noncombat_policy_model':",
                "        raise ImportError('blocked for support CLI test')",
                "    return original_import(name, globals, locals, fromlist, level)",
                "builtins.__import__ = blocked_import",
                f"sys.argv = {arguments!r}",
                f"runpy.run_path({str(script_path)!r}, run_name='__main__')",
            )
        )
        return subprocess.run(
            [sys.executable, "-c", program], capture_output=True, text=True, check=False
        )

    support_arguments = [
        str(script_path),
        "support",
        "--samples",
        str(samples_path),
        "--output-dir",
        str(support_output),
        "--split-seed",
        "support-seed",
        "--source-commit",
        "f321cb05",
        "--label-mode",
        "current",
    ]
    support_result = run_with_blocked_model(support_arguments)
    help_result = run_with_blocked_model([str(script_path), "--help"])

    assert support_result.returncode == 0, support_result.stderr
    assert help_result.returncode == 0, help_result.stderr
    assert "support" in help_result.stdout and "train" in help_result.stdout
    assert sorted(path.name for path in support_output.iterdir()) == [
        "current_artifact_manifest.json",
        "current_dataset_manifest.json",
        "current_report.md",
        "current_split_manifest.json",
        "current_support.json",
    ]

    train_output = tmp_path / "train-output"
    assert main(
        [
            "train",
            "--samples",
            str(samples_path),
            "--output-dir",
            str(train_output),
            "--split-seed",
            "support-seed",
            "--source-commit",
            "f321cb05",
            "--label-mode",
            "current",
            "--max-epochs",
            "1",
            "--patience",
            "1",
        ]
    ) == 2
    assert not (train_output / "current_metrics.json").exists()
    assert not (train_output / "current_model.pt").exists()

    trainable_samples_path = tmp_path / "trainable-samples.jsonl"
    _write_trainable_samples(trainable_samples_path, group_count=10)
    successful_output = tmp_path / "successful-train-output"
    assert main(
        [
            "train",
            "--samples",
            str(trainable_samples_path),
            "--output-dir",
            str(successful_output),
            "--split-seed",
            "train-seed",
            "--source-commit",
            "f321cb05",
            "--label-mode",
            "current",
            "--seed",
            "7",
            "--max-epochs",
            "1",
            "--patience",
            "1",
        ]
    ) == 0
    assert sorted(path.name for path in successful_output.iterdir()) == [
        "current_artifact_manifest.json",
        "current_dataset_manifest.json",
        "current_metrics.json",
        "current_model.pt",
        "current_report.md",
        "current_split_manifest.json",
        "current_support.json",
    ]
    metrics = json.loads((successful_output / "current_metrics.json").read_text(encoding="utf-8"))
    assert set(metrics) == {"test", "validation"}
    assert metrics["validation"]["sample_count"] > 0
    assert metrics["test"]["sample_count"] > 0
    model_payload = __import__("torch").load(
        successful_output / "current_model.pt", map_location="cpu", weights_only=True
    )
    assert set(model_payload) == {"artifact_manifest", "state_dict"}
    assert model_payload["artifact_manifest"]["training_config"]["max_epochs"] == 1


def test_artifact_writer_hashes_final_files_and_removes_temps_on_failure(tmp_path, monkeypatch):
    from analysis_scripts.noncombat_policy_dataset import DatasetBuild, assign_trajectory_splits, evaluate_support
    from analysis_scripts.noncombat_policy_learning import write_pilot_artifacts

    rows = tuple(
        replace(_row(f"route-{index}", f"run:{index}"), label_mode="current")
        for index in range(10)
    )
    dataset = DatasetBuild(
        rows=rows,
        manifest={"label_mode": "current", "source_commit": "f321cb05", "exclusions": {}},
    )
    splits = assign_trajectory_splits(rows, split_seed="artifact-seed")
    support = evaluate_support(dataset, splits)
    output_dir = tmp_path / "artifacts"

    paths = write_pilot_artifacts(
        output_dir,
        mode="current",
        dataset=dataset,
        splits=splits,
        support=support,
    )

    artifact_manifest = json.loads(Path(paths["artifact_manifest"]).read_text(encoding="utf-8"))
    assert set(artifact_manifest["artifact_hashes"]) == {
        "current_dataset_manifest.json",
        "current_report.md",
        "current_split_manifest.json",
        "current_support.json",
    }
    assert "current_artifact_manifest.json" not in artifact_manifest["artifact_hashes"]
    for name, digest in artifact_manifest["artifact_hashes"].items():
        assert digest == hashlib.sha256((output_dir / name).read_bytes()).hexdigest()
    assert artifact_manifest["formal_noncombat_rl_training_ready"] is False
    assert artifact_manifest["live_policy_promotion_ready"] is False
    assert artifact_manifest["output_dir"] == str(output_dir.resolve())

    with pytest.raises(ValueError, match="checkpoints"):
        write_pilot_artifacts(
            tmp_path / "checkpoints",
            mode="current",
            dataset=dataset,
            splits=splits,
            support=support,
        )

    original_replace = Path.replace

    def fail_report_replace(self, target):
        if Path(target).name == "current_report.md":
            raise OSError("replace failed")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", fail_report_replace)
    failed_output = tmp_path / "failed-artifacts"
    with pytest.raises(OSError, match="replace failed"):
        write_pilot_artifacts(
            failed_output,
            mode="current",
            dataset=dataset,
            splits=splits,
            support=support,
        )
    assert not list(failed_output.glob(".*.tmp"))


def _artifact_fixture(*, group_count=10):
    from analysis_scripts.noncombat_policy_dataset import (
        DatasetBuild,
        assign_trajectory_splits,
        evaluate_support,
    )

    rows = tuple(
        _two_candidate_row(
            f"route-{index}",
            f"run:{index:02d}",
            "route",
            "route:choice:0",
        )
        for index in range(group_count)
    )
    dataset = DatasetBuild(
        rows=rows,
        manifest={
            "label_mode": "current",
            "source_commit": "f321cb05",
            "exclusions": {},
            "outcome_counts": {},
        },
    )
    splits = assign_trajectory_splits(rows, split_seed="artifact-transaction-seed")
    return dataset, splits, evaluate_support(dataset, splits)


def _valid_metrics():
    metric_block = {
        "sample_count": 1,
        "model_reference_top1_agreement": 1.0,
        "mean_target_cross_entropy": 0.0,
        "top_confidence_ece": 0.0,
        "candidate_legality": 1.0,
        "frequency_reference_top1_agreement": 1.0,
        "per_category_counts": {"route": 1},
    }
    return {"validation": dict(metric_block), "test": dict(metric_block)}


def _training_result_for_artifact(mode="current"):
    from analysis_scripts.noncombat_policy_model import CandidateRanker, TrainingResult

    return TrainingResult(
        model=CandidateRanker(input_dim=8),
        epochs_run=1,
        best_validation_loss=0.0,
        history=(),
        artifact_manifest={
            "label_mode": mode,
            "artifact_stem": f"noncombat_policy_{mode}",
            "training_config": {"device": "cpu", "max_epochs": 1},
        },
    )


def _managed_names(mode):
    return {
        f"{mode}_dataset_manifest.json",
        f"{mode}_split_manifest.json",
        f"{mode}_support.json",
        f"{mode}_report.md",
        f"{mode}_artifact_manifest.json",
        f"{mode}_metrics.json",
        f"{mode}_model.pt",
    }


def _managed_bytes(output_dir, mode):
    return {
        path.name: path.read_bytes()
        for path in output_dir.iterdir()
        if path.name in _managed_names(mode)
    }


def _assert_no_transaction_debris(output_dir):
    assert not list(output_dir.glob(".*.tmp"))
    assert not list(output_dir.glob(".*.backup"))


def _main_arguments(command, samples_path, output_dir, mode="current"):
    arguments = [
        command,
        "--samples",
        str(samples_path),
        "--output-dir",
        str(output_dir),
        "--split-seed",
        "artifact-transition-seed",
        "--source-commit",
        "f321cb05",
        "--label-mode",
        mode,
    ]
    if command == "train":
        arguments.extend(("--max-epochs", "1", "--patience", "1"))
    return arguments


def test_support_split_sample_counts_follow_split_assignments_deterministically():
    from analysis_scripts.noncombat_policy_dataset import (
        DatasetBuild,
        assign_trajectory_splits,
        evaluate_support,
    )

    base_rows = [
        _two_candidate_row(f"base-{index}", f"run:{index:02d}", "route", "route:choice:0")
        for index in range(10)
    ]
    initial_splits = assign_trajectory_splits(base_rows, split_seed="sample-count-seed")
    rows = list(base_rows)
    for split_name in ("train", "validation", "test"):
        group_id = initial_splits.groups[split_name][0]
        rows.append(
            _two_candidate_row(
                f"extra-{split_name}", group_id, "route", "route:choice:0"
            )
        )
    dataset = DatasetBuild(rows=tuple(rows), manifest={})
    splits = assign_trajectory_splits(dataset.rows, split_seed="sample-count-seed")

    support = evaluate_support(dataset, splits)

    assert support["overall"]["split_trajectory_counts"] == {
        "test": 2,
        "train": 6,
        "validation": 2,
    }
    assert support["overall"]["split_sample_counts"] == {
        "test": 3,
        "train": 7,
        "validation": 3,
    }


def test_artifact_transaction_removes_stale_current_model_and_preserves_other_mode(tmp_path):
    from analysis_scripts.noncombat_policy_learning import main

    samples_path = tmp_path / "samples.jsonl"
    _write_trainable_samples(samples_path, group_count=10)
    output_dir = tmp_path / "artifacts"

    assert main(_main_arguments("train", samples_path, output_dir, "current")) == 0
    assert main(_main_arguments("support", samples_path, output_dir, "bottled")) == 0
    bottled_before = _managed_bytes(output_dir, "bottled")
    unrelated = output_dir / "unrelated.txt"
    unrelated.write_bytes(b"preserve me")

    assert main(_main_arguments("support", samples_path, output_dir, "current")) == 0

    assert _managed_bytes(output_dir, "current").keys() == {
        "current_dataset_manifest.json",
        "current_split_manifest.json",
        "current_support.json",
        "current_report.md",
        "current_artifact_manifest.json",
    }
    assert _managed_bytes(output_dir, "bottled") == bottled_before
    assert unrelated.read_bytes() == b"preserve me"
    _assert_no_transaction_debris(output_dir)


def test_blocked_train_transaction_removes_stale_current_model(tmp_path):
    from analysis_scripts.noncombat_policy_learning import main

    trainable_samples = tmp_path / "trainable.jsonl"
    blocked_samples = tmp_path / "blocked.jsonl"
    _write_trainable_samples(trainable_samples, group_count=10)
    _write_trainable_samples(blocked_samples, group_count=9)
    output_dir = tmp_path / "artifacts"

    assert main(_main_arguments("train", trainable_samples, output_dir)) == 0
    assert main(_main_arguments("train", blocked_samples, output_dir)) == 2

    assert _managed_bytes(output_dir, "current").keys() == {
        "current_dataset_manifest.json",
        "current_split_manifest.json",
        "current_support.json",
        "current_report.md",
        "current_artifact_manifest.json",
    }
    _assert_no_transaction_debris(output_dir)


@pytest.mark.parametrize("failure_name", ["current_report.md", "current_artifact_manifest.json"])
def test_artifact_transaction_restores_existing_set_after_replace_failure(
    tmp_path, monkeypatch, failure_name
):
    from analysis_scripts.noncombat_policy_dataset import DatasetBuild
    from analysis_scripts.noncombat_policy_learning import write_pilot_artifacts

    dataset, splits, support = _artifact_fixture()
    changed_dataset = DatasetBuild(
        rows=dataset.rows,
        manifest={**dataset.manifest, "source_commit": "changed-commit"},
    )
    output_dir = tmp_path / "artifacts"
    result = _training_result_for_artifact()
    write_pilot_artifacts(
        output_dir,
        mode="current",
        dataset=dataset,
        splits=splits,
        support=support,
        model=result,
        metrics=_valid_metrics(),
    )
    before = _managed_bytes(output_dir, "current")
    original_replace = Path.replace
    failed = False

    def fail_once(self, target):
        nonlocal failed
        if not failed and self.name.endswith(".tmp") and Path(target).name == failure_name:
            failed = True
            raise OSError(f"injected {failure_name} replacement failure")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", fail_once)
    with pytest.raises(OSError, match="injected"):
        write_pilot_artifacts(
            output_dir,
            mode="current",
            dataset=changed_dataset,
            splits=splits,
            support=support,
        )

    assert _managed_bytes(output_dir, "current") == before
    _assert_no_transaction_debris(output_dir)


def test_artifact_transaction_restores_existing_set_after_model_staging_failure(tmp_path, monkeypatch):
    import torch

    from analysis_scripts.noncombat_policy_dataset import DatasetBuild
    from analysis_scripts.noncombat_policy_learning import write_pilot_artifacts

    dataset, splits, support = _artifact_fixture()
    changed_dataset = DatasetBuild(
        rows=dataset.rows,
        manifest={**dataset.manifest, "source_commit": "changed-commit"},
    )
    output_dir = tmp_path / "artifacts"
    result = _training_result_for_artifact()
    write_pilot_artifacts(
        output_dir,
        mode="current",
        dataset=dataset,
        splits=splits,
        support=support,
        model=result,
        metrics=_valid_metrics(),
    )
    before = _managed_bytes(output_dir, "current")

    def fail_model_stage(*args, **kwargs):
        raise OSError("injected model staging failure")

    monkeypatch.setattr(torch, "save", fail_model_stage)
    with pytest.raises(OSError, match="injected model staging failure"):
        write_pilot_artifacts(
            output_dir,
            mode="current",
            dataset=changed_dataset,
            splits=splits,
            support=support,
            model=result,
            metrics=_valid_metrics(),
        )

    assert _managed_bytes(output_dir, "current") == before
    _assert_no_transaction_debris(output_dir)


def test_artifact_transaction_leaves_no_finals_after_first_install_failure(tmp_path, monkeypatch):
    from analysis_scripts.noncombat_policy_learning import write_pilot_artifacts

    dataset, splits, support = _artifact_fixture()
    output_dir = tmp_path / "artifacts"
    original_replace = Path.replace

    def fail_report_install(self, target):
        if self.name.endswith(".tmp") and Path(target).name == "current_report.md":
            raise OSError("injected first-install failure")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", fail_report_install)
    with pytest.raises(OSError, match="injected first-install failure"):
        write_pilot_artifacts(
            output_dir,
            mode="current",
            dataset=dataset,
            splits=splits,
            support=support,
        )

    assert _managed_bytes(output_dir, "current") == {}
    _assert_no_transaction_debris(output_dir)


def _changed_artifact_dataset(dataset):
    from analysis_scripts.noncombat_policy_dataset import DatasetBuild

    return DatasetBuild(
        rows=dataset.rows,
        manifest={**dataset.manifest, "source_commit": "changed-recovery-commit"},
    )


def _write_complete_artifact_set(output_dir, dataset, splits, support):
    from analysis_scripts.noncombat_policy_learning import write_pilot_artifacts

    result = _training_result_for_artifact()
    write_pilot_artifacts(
        output_dir,
        mode="current",
        dataset=dataset,
        splits=splits,
        support=support,
        model=result,
        metrics=_valid_metrics(),
    )


def _assert_artifact_manifest_hashes(output_dir, mode="current"):
    manifest = json.loads(
        (output_dir / f"{mode}_artifact_manifest.json").read_text(encoding="utf-8")
    )
    for name, digest in manifest["artifact_hashes"].items():
        assert digest == hashlib.sha256((output_dir / name).read_bytes()).hexdigest()


def test_post_write_byte_staging_failure_cleans_registered_temporary_file(tmp_path, monkeypatch):
    import analysis_scripts.noncombat_policy_learning as learning

    dataset, splits, support = _artifact_fixture()
    output_dir = tmp_path / "artifacts"
    original_stage = learning._stage_bytes
    failed = False

    def write_then_fail(path, payload):
        nonlocal failed
        original_stage(path, payload)
        if not failed:
            failed = True
            raise OSError("injected byte staging post-write failure")

    monkeypatch.setattr(learning, "_stage_bytes", write_then_fail)
    with pytest.raises(OSError, match="byte staging post-write"):
        learning.write_pilot_artifacts(
            output_dir,
            mode="current",
            dataset=dataset,
            splits=splits,
            support=support,
        )

    assert _managed_bytes(output_dir, "current") == {}
    _assert_no_transaction_debris(output_dir)


def test_post_save_model_staging_failure_cleans_registered_temporary_file(tmp_path, monkeypatch):
    import analysis_scripts.noncombat_policy_learning as learning

    dataset, splits, support = _artifact_fixture()
    output_dir = tmp_path / "artifacts"
    result = _training_result_for_artifact()
    original_stage = learning._stage_model_artifact

    def save_then_fail(path, training_result):
        original_stage(path, training_result)
        raise OSError("injected model staging post-save failure")

    monkeypatch.setattr(learning, "_stage_model_artifact", save_then_fail)
    with pytest.raises(OSError, match="model staging post-save"):
        learning.write_pilot_artifacts(
            output_dir,
            mode="current",
            dataset=dataset,
            splits=splits,
            support=support,
            model=result,
            metrics=_valid_metrics(),
        )

    assert _managed_bytes(output_dir, "current") == {}
    _assert_no_transaction_debris(output_dir)


def test_pre_backup_move_failure_preserves_complete_prior_artifact_set(
    tmp_path, monkeypatch
):
    from analysis_scripts.noncombat_policy_learning import write_pilot_artifacts

    dataset, splits, support = _artifact_fixture()
    changed_dataset = _changed_artifact_dataset(dataset)
    output_dir = tmp_path / "artifacts"
    _write_complete_artifact_set(output_dir, dataset, splits, support)
    before = _managed_bytes(output_dir, "current")
    manifest_path = output_dir / "current_artifact_manifest.json"
    original_replace = Path.replace

    def fail_before_manifest_backup_move(self, target):
        if (
            self == manifest_path
            and Path(target).name == ".current_artifact_manifest.json.backup"
        ):
            raise OSError("injected manifest backup pre-move failure")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", fail_before_manifest_backup_move)
    with pytest.raises(OSError, match="manifest backup pre-move failure"):
        write_pilot_artifacts(
            output_dir,
            mode="current",
            dataset=changed_dataset,
            splits=splits,
            support=support,
        )

    assert _managed_bytes(output_dir, "current") == before
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "noncombat-policy-pilot-artifacts-v1"
    _assert_artifact_manifest_hashes(output_dir)
    _assert_no_transaction_debris(output_dir)


def test_post_backup_move_failure_restores_registered_backup(tmp_path, monkeypatch):
    from analysis_scripts.noncombat_policy_learning import write_pilot_artifacts

    dataset, splits, support = _artifact_fixture()
    changed_dataset = _changed_artifact_dataset(dataset)
    output_dir = tmp_path / "artifacts"
    _write_complete_artifact_set(output_dir, dataset, splits, support)
    before = _managed_bytes(output_dir, "current")
    original_replace = Path.replace
    failed = False

    def move_then_fail(self, target):
        nonlocal failed
        result = original_replace(self, target)
        if (
            not failed
            and self.name == "current_dataset_manifest.json"
            and Path(target).name == ".current_dataset_manifest.json.backup"
        ):
            failed = True
            raise OSError("injected backup post-move failure")
        return result

    monkeypatch.setattr(Path, "replace", move_then_fail)
    with pytest.raises(OSError, match="backup post-move"):
        write_pilot_artifacts(
            output_dir,
            mode="current",
            dataset=changed_dataset,
            splits=splits,
            support=support,
        )

    assert _managed_bytes(output_dir, "current") == before
    _assert_no_transaction_debris(output_dir)


def test_post_install_move_failure_removes_registered_new_final(tmp_path, monkeypatch):
    from analysis_scripts.noncombat_policy_learning import write_pilot_artifacts

    dataset, splits, support = _artifact_fixture()
    output_dir = tmp_path / "artifacts"
    original_replace = Path.replace
    failed = False

    def install_then_fail(self, target):
        nonlocal failed
        result = original_replace(self, target)
        if (
            not failed
            and self.name == ".current_dataset_manifest.json.tmp"
            and Path(target).name == "current_dataset_manifest.json"
        ):
            failed = True
            raise OSError("injected install post-move failure")
        return result

    monkeypatch.setattr(Path, "replace", install_then_fail)
    with pytest.raises(OSError, match="install post-move"):
        write_pilot_artifacts(
            output_dir,
            mode="current",
            dataset=dataset,
            splits=splits,
            support=support,
        )

    assert _managed_bytes(output_dir, "current") == {}
    _assert_no_transaction_debris(output_dir)


def test_stale_backup_refuses_before_any_final_is_moved(tmp_path, monkeypatch):
    from analysis_scripts.noncombat_policy_learning import write_pilot_artifacts

    dataset, splits, support = _artifact_fixture()
    changed_dataset = _changed_artifact_dataset(dataset)
    output_dir = tmp_path / "artifacts"
    _write_complete_artifact_set(output_dir, dataset, splits, support)
    stale_backup = output_dir / ".current_support.json.backup"
    stale_backup.write_bytes(b"existing recovery copy")
    before = _managed_bytes(output_dir, "current")
    original_replace = Path.replace
    backup_moves = []

    def record_backup_move(self, target):
        if self.name.startswith("current_") and Path(target).name.endswith(".backup"):
            backup_moves.append((self.name, Path(target).name))
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", record_backup_move)

    with pytest.raises(RuntimeError, match="stale transaction backup"):
        write_pilot_artifacts(
            output_dir,
            mode="current",
            dataset=changed_dataset,
            splits=splits,
            support=support,
        )

    assert _managed_bytes(output_dir, "current") == before
    assert stale_backup.read_bytes() == b"existing recovery copy"
    assert backup_moves == []
    assert not list(output_dir.glob(".*.tmp"))


def test_backup_cleanup_failure_keeps_accepted_new_artifacts_and_recovery_copy(tmp_path, monkeypatch):
    from analysis_scripts.noncombat_policy_learning import write_pilot_artifacts

    dataset, splits, support = _artifact_fixture()
    changed_dataset = _changed_artifact_dataset(dataset)
    output_dir = tmp_path / "artifacts"
    _write_complete_artifact_set(output_dir, dataset, splits, support)
    original_unlink = Path.unlink

    def fail_model_backup_cleanup(self, *args, **kwargs):
        if self.name == ".current_model.pt.backup":
            raise OSError("injected backup cleanup failure")
        return original_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_model_backup_cleanup)
    with pytest.raises(RuntimeError, match="committed.*cleanup"):
        write_pilot_artifacts(
            output_dir,
            mode="current",
            dataset=changed_dataset,
            splits=splits,
            support=support,
        )

    assert _managed_bytes(output_dir, "current").keys() == {
        "current_dataset_manifest.json",
        "current_split_manifest.json",
        "current_support.json",
        "current_report.md",
        "current_artifact_manifest.json",
    }
    _assert_artifact_manifest_hashes(output_dir)
    assert (output_dir / ".current_model.pt.backup").exists()


def test_restore_failure_preserves_backup_and_restores_unrelated_artifacts(tmp_path, monkeypatch):
    from analysis_scripts.noncombat_policy_learning import write_pilot_artifacts

    dataset, splits, support = _artifact_fixture()
    changed_dataset = _changed_artifact_dataset(dataset)
    output_dir = tmp_path / "artifacts"
    _write_complete_artifact_set(output_dir, dataset, splits, support)
    before = _managed_bytes(output_dir, "current")
    original_replace = Path.replace
    install_failed = False

    def fail_install_then_support_restore(self, target):
        nonlocal install_failed
        if (
            self.name == ".current_support.json.backup"
            and Path(target).name == "current_support.json"
        ):
            raise OSError("injected support restore failure")
        result = original_replace(self, target)
        if (
            not install_failed
            and self.name == ".current_report.md.tmp"
            and Path(target).name == "current_report.md"
        ):
            install_failed = True
            raise OSError("injected report install failure")
        return result

    monkeypatch.setattr(Path, "replace", fail_install_then_support_restore)
    with pytest.raises(RuntimeError) as error:
        write_pilot_artifacts(
            output_dir,
            mode="current",
            dataset=changed_dataset,
            splits=splits,
            support=support,
        )

    assert ".current_support.json.backup" in str(error.value)
    assert ".current_artifact_manifest.json.backup" in str(error.value)
    expected_restored = {
        name: payload
        for name, payload in before.items()
        if name not in {"current_support.json", "current_artifact_manifest.json"}
    }
    assert _managed_bytes(output_dir, "current") == expected_restored
    support_backup = output_dir / ".current_support.json.backup"
    manifest_backup = output_dir / ".current_artifact_manifest.json.backup"
    assert support_backup.read_bytes() == before["current_support.json"]
    assert manifest_backup.read_bytes() == before["current_artifact_manifest.json"]
    assert not (output_dir / "current_artifact_manifest.json").exists()
    assert not list(output_dir.glob(".*.tmp"))


def test_successful_rollback_restores_manifest_after_non_manifest_artifacts(tmp_path, monkeypatch):
    from analysis_scripts.noncombat_policy_learning import write_pilot_artifacts

    dataset, splits, support = _artifact_fixture()
    changed_dataset = _changed_artifact_dataset(dataset)
    output_dir = tmp_path / "artifacts"
    _write_complete_artifact_set(output_dir, dataset, splits, support)
    before = _managed_bytes(output_dir, "current")
    original_replace = Path.replace
    restore_order = []
    install_failed = False

    def record_restore_then_fail_report_install(self, target):
        nonlocal install_failed
        if self.name.endswith(".backup") and Path(target).name.startswith("current_"):
            restore_order.append(Path(target).name)
        result = original_replace(self, target)
        if (
            not install_failed
            and self.name == ".current_report.md.tmp"
            and Path(target).name == "current_report.md"
        ):
            install_failed = True
            raise OSError("injected report install failure")
        return result

    monkeypatch.setattr(Path, "replace", record_restore_then_fail_report_install)
    with pytest.raises(OSError, match="report install failure"):
        write_pilot_artifacts(
            output_dir,
            mode="current",
            dataset=changed_dataset,
            splits=splits,
            support=support,
        )

    assert _managed_bytes(output_dir, "current") == before
    assert restore_order[-1] == "current_artifact_manifest.json"
    assert set(restore_order[:-1]) == set(before) - {"current_artifact_manifest.json"}
    _assert_no_transaction_debris(output_dir)


def test_rollback_withholds_manifest_when_unbacked_model_survives_cleanup(
    tmp_path, monkeypatch
):
    from analysis_scripts.noncombat_policy_learning import write_pilot_artifacts

    dataset, splits, support = _artifact_fixture()
    changed_dataset = _changed_artifact_dataset(dataset)
    output_dir = tmp_path / "artifacts"
    write_pilot_artifacts(
        output_dir,
        mode="current",
        dataset=dataset,
        splits=splits,
        support=support,
    )
    before = _managed_bytes(output_dir, "current")
    result = _training_result_for_artifact()
    original_replace = Path.replace
    original_unlink = Path.unlink
    install_failed = False

    def fail_late_install(self, target):
        nonlocal install_failed
        result_path = original_replace(self, target)
        if (
            not install_failed
            and self.name == ".current_report.md.tmp"
            and Path(target).name == "current_report.md"
        ):
            install_failed = True
            raise OSError("injected report install failure")
        return result_path

    def leave_unbacked_model(self, *args, **kwargs):
        if self.name == "current_model.pt":
            raise OSError("injected model cleanup failure")
        return original_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "replace", fail_late_install)
    monkeypatch.setattr(Path, "unlink", leave_unbacked_model)
    with pytest.raises(RuntimeError) as error:
        write_pilot_artifacts(
            output_dir,
            mode="current",
            dataset=changed_dataset,
            splits=splits,
            support=support,
            model=result,
            metrics=_valid_metrics(),
        )

    assert "current_model.pt" in str(error.value)
    assert ".current_artifact_manifest.json.backup" in str(error.value)
    for name, payload in before.items():
        if name != "current_artifact_manifest.json":
            assert (output_dir / name).read_bytes() == payload
    assert (output_dir / "current_model.pt").exists()
    assert not (output_dir / "current_metrics.json").exists()
    assert not (output_dir / "current_artifact_manifest.json").exists()
    assert (
        output_dir / ".current_artifact_manifest.json.backup"
    ).read_bytes() == before["current_artifact_manifest.json"]
    assert not list(output_dir.glob(".*.tmp"))


def test_artifact_writer_rejects_inconsistent_inputs_before_writing(tmp_path):
    from analysis_scripts.noncombat_policy_dataset import DatasetBuild, to_json_value
    from analysis_scripts.noncombat_policy_learning import write_pilot_artifacts

    dataset, splits, support = _artifact_fixture()
    row_mode_mismatch = DatasetBuild(
        rows=(replace(dataset.rows[0], label_mode="bottled"), *dataset.rows[1:]),
        manifest=dataset.manifest,
    )
    manifest_mode_mismatch = DatasetBuild(
        rows=dataset.rows,
        manifest={**dataset.manifest, "label_mode": "bottled"},
    )
    blocked_support = to_json_value(support)
    blocked_support["overall"]["blocked"] = True

    cases = (
        ("manifest-mode", manifest_mode_mismatch, support, None, None),
        ("row-mode", row_mode_mismatch, support, None, None),
        ("metrics-only", dataset, support, None, _valid_metrics()),
        ("model-only", dataset, support, _training_result_for_artifact(), None),
        (
            "blocked-model",
            dataset,
            blocked_support,
            _training_result_for_artifact(),
            _valid_metrics(),
        ),
        (
            "invalid-metrics",
            dataset,
            support,
            _training_result_for_artifact(),
            {"validation": {}, "test": {}},
        ),
        (
            "model-mode",
            dataset,
            support,
            _training_result_for_artifact("bottled"),
            _valid_metrics(),
        ),
    )
    for name, case_dataset, case_support, model, metrics in cases:
        output_dir = tmp_path / name
        with pytest.raises(ValueError):
            write_pilot_artifacts(
                output_dir,
                mode="current",
                dataset=case_dataset,
                splits=splits,
                support=case_support,
                model=model,
                metrics=metrics,
            )
        if output_dir.exists():
            assert _managed_bytes(output_dir, "current") == {}
            _assert_no_transaction_debris(output_dir)


def _snapshot_fixture(*, blocked):
    from analysis_scripts.noncombat_policy_dataset import DatasetBuild, SplitManifest, evaluate_support

    groups = tuple(f"run:{index}" for index in range(10))
    if blocked:
        rows = (_two_candidate_row("route-0", "run:0", "route", "route:choice:0"),)
        assignments = {"run:0": "test"}
        split_groups = {"train": (), "validation": (), "test": ("run:0",)}
        exclusions = {"missing_target": 1}
        metrics = None
    else:
        rows = tuple(
            _two_candidate_row(
                f"{category}-{index}", group, category, f"{category}:choice:0"
            )
            for index, group in enumerate(groups)
            for category in ("shop", "event", "route", "card_reward")
        )
        assignments = {
            group: "train" if index < 6 else "validation" if index < 8 else "test"
            for index, group in enumerate(groups)
        }
        split_groups = {
            "train": groups[:6],
            "validation": groups[6:8],
            "test": groups[8:],
        }
        exclusions = {}
        metrics = {
            split: {
                "sample_count": 8,
                "model_reference_top1_agreement": 1.0,
                "mean_target_cross_entropy": 0.0,
                "top_confidence_ece": 0.0,
                "candidate_legality": 1.0,
                "frequency_reference_top1_agreement": 1.0,
                "per_category_counts": {
                    "card_reward": 2,
                    "event": 2,
                    "route": 2,
                    "shop": 2,
                },
            }
            for split in ("validation", "test")
        }
    dataset = DatasetBuild(
        rows=rows,
        manifest={
            "label_mode": "current",
            "source_commit": "snapshot",
            "exclusions": exclusions,
            "outcome_counts": {},
        },
    )
    splits = SplitManifest(
        assignments=assignments,
        groups=split_groups,
        manifest={"split_seed": "snapshot", "groups": {key: list(value) for key, value in split_groups.items()}},
    )
    return dataset, splits, evaluate_support(dataset, splits), metrics


def _expected_snapshot(*, blocked):
    if blocked:
        categories = {
            "shop": {
                "blocking_reasons": [
                    "insufficient_train_trajectories",
                    "missing_held_out_trajectory",
                    "overall_support_blocked",
                ],
                "evaluable": False,
                "held_out_trajectory_count": 0,
                "train_trajectory_count": 0,
            },
            "event": {
                "blocking_reasons": [
                    "insufficient_train_trajectories",
                    "missing_held_out_trajectory",
                    "overall_support_blocked",
                ],
                "evaluable": False,
                "held_out_trajectory_count": 0,
                "train_trajectory_count": 0,
            },
            "route": {
                "blocking_reasons": [
                    "insufficient_train_trajectories",
                    "overall_support_blocked",
                ],
                "evaluable": False,
                "held_out_trajectory_count": 1,
                "train_trajectory_count": 0,
            },
            "card_reward": {
                "blocking_reasons": [
                    "insufficient_train_trajectories",
                    "missing_held_out_trajectory",
                    "overall_support_blocked",
                ],
                "evaluable": False,
                "held_out_trajectory_count": 0,
                "train_trajectory_count": 0,
            },
        }
        exclusions = {"missing_target": 1}
        groups = {"train": [], "validation": [], "test": ["run:0"]}
        overall = {
            "blocked": True,
            "blocking_reasons": [
                "insufficient_trajectory_groups",
                "empty_train_split",
                "empty_validation_split",
            ],
            "minimum_trajectory_count": 10,
            "split_trajectory_counts": {"test": 1, "train": 0, "validation": 0},
            "split_sample_counts": {"test": 1, "train": 0, "validation": 0},
            "trajectory_count": 1,
        }
        outcomes = {
            "rows": {
                "join_status": {"matched": 1},
                "victory": {"false": 1, "true": 0, "unknown": 0},
            },
            "trajectories": {
                "join_status": {"matched": 1},
                "victory": {"false": 1, "true": 0, "unknown": 0},
            },
        }
        metrics = None
    else:
        categories = {
            category: {
                "blocking_reasons": [],
                "evaluable": True,
                "held_out_trajectory_count": 4,
                "train_trajectory_count": 6,
            }
            for category in ("shop", "event", "route", "card_reward")
        }
        exclusions = {}
        groups = {
            "train": [f"run:{index}" for index in range(6)],
            "validation": ["run:6", "run:7"],
            "test": ["run:8", "run:9"],
        }
        overall = {
            "blocked": False,
            "blocking_reasons": [],
            "minimum_trajectory_count": 10,
            "split_trajectory_counts": {"test": 2, "train": 6, "validation": 2},
            "split_sample_counts": {"test": 8, "train": 24, "validation": 8},
            "trajectory_count": 10,
        }
        outcomes = {
            "rows": {
                "join_status": {"matched": 40},
                "victory": {"false": 40, "true": 0, "unknown": 0},
            },
            "trajectories": {
                "join_status": {"matched": 10},
                "victory": {"false": 10, "true": 0, "unknown": 0},
            },
        }
        metrics = {
            split: {
                "sample_count": 8,
                "model_reference_top1_agreement": 1.0,
                "mean_target_cross_entropy": 0.0,
                "top_confidence_ece": 0.0,
                "candidate_legality": 1.0,
                "frequency_reference_top1_agreement": 1.0,
                "per_category_counts": {
                    "card_reward": 2,
                    "event": 2,
                    "route": 2,
                    "shop": 2,
                },
            }
            for split in ("validation", "test")
        }

    lines = [
        "# Non-combat policy-learning pilot",
        "",
        "Label mode: current",
        "Source commit: snapshot",
        "",
        "Formal non-combat RL: blocked",
        "Live policy promotion: blocked",
        "Off-policy evaluation: unsupported",
        "",
        "## Limitations",
        "Missing trajectories, target mappings, unknown behavior propensities, and contextual alternative-action overlap block off-policy evaluation.",
        "Aggregate candidate counts do not establish contextual alternative-action overlap.",
        "Outcomes are diagnostics only and are not supervised targets.",
        "",
        "## Dataset exclusions",
        json.dumps(exclusions, indent=2, sort_keys=True),
        "",
        "## Category support",
    ]
    for category in ("shop", "event", "route", "card_reward"):
        lines.extend((f"### {category}", json.dumps(categories[category], indent=2, sort_keys=True), ""))
    lines.extend(
        (
            "## Split counts",
            json.dumps(
                {
                    "groups": groups,
                    "split_sample_counts": overall["split_sample_counts"],
                    "support": overall,
                },
                indent=2,
                sort_keys=True,
            ),
            "",
            "## Outcome diagnostics",
            json.dumps({"dataset": {}, "support": outcomes}, indent=2, sort_keys=True),
        )
    )
    if metrics is not None:
        lines.extend(("", "## Held-out metrics"))
        for split in ("validation", "test"):
            lines.extend(("", f"### {split.title()}", json.dumps(metrics[split], indent=2, sort_keys=True)))
    return "\n".join(lines).rstrip() + "\n"


def test_blocked_policy_report_matches_exact_snapshot():
    from analysis_scripts.noncombat_policy_learning import render_policy_report

    dataset, splits, support, metrics = _snapshot_fixture(blocked=True)

    assert metrics is None
    assert support["overall"]["blocked"] is True
    assert render_policy_report(dataset.manifest, splits.manifest, support) == _expected_snapshot(
        blocked=True
    )


def test_overall_allowed_policy_report_matches_exact_snapshot_with_metrics():
    from analysis_scripts.noncombat_policy_learning import render_policy_report

    dataset, splits, support, metrics = _snapshot_fixture(blocked=False)

    assert support["overall"]["blocked"] is False
    assert set(metrics) == {"validation", "test"}
    assert render_policy_report(dataset.manifest, splits.manifest, support, metrics=metrics) == _expected_snapshot(
        blocked=False
    )


def test_review_status_matches_open_completion_tasks_and_evidence_reports():
    root = Path(__file__).resolve().parents[1]
    tasks = (
        root
        / "openspec"
        / "changes"
        / "add-noncombat-policy-learning-pilot"
        / "tasks.md"
    ).read_text(encoding="utf-8")
    gated_tasks = ("6.4", "7.1", "7.2", "7.3", "7.4", "7.5")
    gated_complete = all(f"- [x] {task_id} " in tasks for task_id in gated_tasks)
    pending_status = "pending_duplicate_candidate_re_review"
    approved_status = "approved_duplicate_candidate_evidence"
    source = json.loads(
        (
            root / "reports" / "noncombat_policy_learning_source_20260712.json"
        ).read_text(encoding="utf-8")
    )
    reports = [
        (root / "reports" / name).read_text(encoding="utf-8")
        for name in (
            "noncombat_policy_learning_support_20260712.md",
            "noncombat_policy_learning_current_20260712.md",
            "noncombat_policy_learning_bottled_20260712.md",
        )
    ]

    if source["review_status"] == approved_status:
        assert source["review_status"] == approved_status
        assert all(f"Review status: `{approved_status}`." in report for report in reports)
        assert all("pending" not in report.lower() for report in reports)
    else:
        assert source["review_status"] == pending_status
        assert gated_complete is False
        assert all(f"Review status: `{pending_status}`." in report for report in reports)
    if gated_complete:
        assert source["review_status"] == approved_status


def _assert_deterministic_manifest(first_manifest, second_manifest):
    assert tuple(first_manifest) == tuple(second_manifest)
    for key in first_manifest:
        first_value = first_manifest[key]
        second_value = second_manifest[key]
        if isinstance(first_value, Mapping):
            assert isinstance(second_value, Mapping)
            _assert_deterministic_manifest(first_value, second_value)
        elif isinstance(first_value, float):
            assert first_value == pytest.approx(second_value, rel=0, abs=1e-7)
        else:
            assert first_value == second_value
