import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import replace
from types import SimpleNamespace

import pytest


V2 = "noncombat-rl-decision-v2"


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
