import hashlib
import json


V2 = "noncombat-rl-decision-v2"


def _sample(sample_id, group_id="run:1", **overrides):
    category = overrides.get("category", "route")
    sample = {
        "schema_version": V2,
        "sample_id": sample_id,
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
        "bottled_label": {
            "action_id": f"{category}:choice:0",
            "oracle_mode": "native_bottled",
            "confidence": "high",
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
    from analysis_scripts.noncombat_policy_dataset import build_policy_dataset

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
    assert first.manifest["outcome_counts"] == {"matched": 2, "victory": 1}
    assert first.manifest["action_support"] == {
        "event:choice:0": 1,
        "shop:choice:0": 1,
    }
    assert first.manifest["behavior_probability_counts"] == {"known": 1, "unknown": 1}
    assert first.manifest["label_mode_counts"] == {"bottled": 0, "current": 2}
    canonical = json.dumps(first.manifest, sort_keys=True, separators=(",", ":"))
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
    assert support["categories"]["shop"] == {
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
