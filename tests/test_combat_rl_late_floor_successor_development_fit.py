from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest
import torch

from analysis_scripts import combat_rl_action_relative_live_context_target as live_target
from analysis_scripts import combat_rl_action_relative_successor_delta_ablation as base
from analysis_scripts import combat_rl_late_floor_successor_development_fit as late_fit


def _corpus(
    partition: str,
    *,
    seeds: tuple[int, ...],
    battle: int = 10,
    floors: tuple[int, ...] | None = None,
) -> dict:
    floors = floors or tuple(28 + index for index in range(len(seeds)))
    count = len(seeds)
    continuous = torch.zeros((count, 4), dtype=torch.float32)
    continuous[:, 0] = torch.tensor(
        [0.2 + 0.2 * index for index in range(count)], dtype=torch.float32
    )
    continuous[:, 3] = torch.tensor(floors, dtype=torch.float32) / 50.0
    state = {
        "continuous": continuous,
        "card_ids": torch.tensor([[1, 0]] * count, dtype=torch.long),
        "potion_ids": torch.tensor([[0, 2]] * count, dtype=torch.long),
        "relic_ids": torch.tensor([[1, 2, 0]] * count, dtype=torch.long),
        "action_masks": torch.tensor([[True, True, False]] * count),
    }
    tensors = {
        **state,
        "guard_actions": torch.zeros(count, dtype=torch.long),
        "target_actions": torch.ones(count, dtype=torch.long),
        "advantages": torch.tensor(
            [0.5 if index % 2 == 0 else -0.5 for index in range(count)]
        ),
        "positive": torch.tensor(
            [index % 2 == 0 for index in range(count)], dtype=torch.bool
        ),
    }
    pairs = {
        "source_rows": torch.arange(count),
        "candidate_actions": torch.ones(count, dtype=torch.long),
        "guard_returns": torch.zeros(count),
        "candidate_returns": tensors["advantages"].clone(),
        "advantages": tensors["advantages"].clone(),
        "guard_immediate_rewards": torch.zeros(count),
        "candidate_immediate_rewards": tensors["advantages"].clone(),
        "guard_dispositions": torch.full((count,), base.SUPPORTED),
        "candidate_dispositions": torch.full((count,), base.SUPPORTED),
    }
    for prefix in ("guard", "candidate"):
        for name, tensor in state.items():
            pairs[f"{prefix}_successor_{name}"] = tensor.clone()
    return base.validate_successor_corpus(
        {
            "schema_version": base.CORPUS_SCHEMA,
            "corpus_kind": base.CORPUS_KIND,
            "partition": partition,
            "tensors": tensors,
            "metadata": [
                {
                    "seed": seed,
                    "battle_index": battle,
                    "floor": floor,
                    "guard_action_index": 0,
                    "target_action_index": 1,
                    "branch_returns": {
                        "0": 0.0,
                        "1": 0.5 if index % 2 == 0 else -0.5,
                    },
                }
                for index, (seed, floor) in enumerate(zip(seeds, floors))
            ],
            "pairs": pairs,
            "row_count": count,
            "pair_count": count,
        },
        expected_partition=partition,
    )


def _target_rows(corpus: dict) -> list[dict]:
    context = late_fit.build_fresh_context_projection(corpus)
    return [
        {
            "floor": row["floor"],
            "floor_ratio": row["floor_ratio"],
            "player_hp_ratio": row["player_hp_ratio"],
            "potion_occupied_slots": row["potion_occupied_slots"],
            "relic_occupied_slots": row["relic_occupied_slots"],
            "player_hp_quartile": row["player_hp_quartile"],
            "context_cell_id": row["context_cell_id"],
        }
        for row in context["rows"]
    ]


def _bindings(tmp_path: Path, names: tuple[str, ...]) -> dict[str, dict[str, str]]:
    result = {}
    for name in names:
        path = tmp_path / name
        path.write_bytes(name.encode("ascii"))
        result[name] = late_fit.file_binding(path)
    return result


def test_collection_registration_binds_fixed_slices_and_contamination(
    tmp_path: Path,
) -> None:
    inputs = _bindings(tmp_path, late_fit.COLLECTION_INPUT_NAMES)
    registration = late_fit.build_collection_registration(
        "a" * 40, inputs=inputs
    )
    validated = late_fit.validate_collection_registration(registration)

    assert validated["recipe"]["slices"] == {
        "fit_battle_10": {
            "partition": "fit",
            "seed_bounds": [288000, 290047],
            "battle_indices": [10],
        },
        "calibration_battle_10": {
            "partition": "calibration",
            "seed_bounds": [290048, 290559],
            "battle_indices": [10],
        },
        "fresh_battle_10": {
            "partition": "fresh",
            "seed_bounds": [291000, 292023],
            "battle_indices": [10],
        },
    }
    assert validated["contamination"]["development_target_only"] is True
    assert validated["contamination"]["prior_fresh_policy_confirmation"] is False
    assert validated["authority"]["native_loading"] is True
    assert validated["authority"]["model_fitting"] is False
    assert validated["authority"]["gameplay"] is False

    registration["recipe"]["slices"]["fit_battle_10"]["seed_bounds"][0] += 1
    with pytest.raises(ValueError, match="registration payload differs"):
        late_fit.validate_collection_registration(registration)


def test_fixed_slices_are_disjoint_and_reject_lineage_collision() -> None:
    late_fit.validate_slice_contract(late_fit.FIXED_SLICES, occupied_seeds={275000})
    with pytest.raises(ValueError, match="lineage"):
        late_fit.validate_slice_contract(
            late_fit.FIXED_SLICES, occupied_seeds={291111}
        )


def test_merge_offsets_pair_rows_and_preserves_partition_order() -> None:
    left = _corpus("fit", seeds=(275000, 275001))
    right = _corpus("fit", seeds=(288000, 288001))

    merged = late_fit.merge_successor_corpora("fit", left, right)

    assert merged["row_count"] == 4
    assert merged["pairs"]["source_rows"].tolist() == [0, 1, 2, 3]
    assert [row["seed"] for row in merged["metadata"]] == [
        275000,
        275001,
        288000,
        288001,
    ]


def test_fresh_context_projection_excludes_labels_and_roundtrips() -> None:
    fresh = _corpus("fresh", seeds=(291000, 291001))

    projection = late_fit.build_fresh_context_projection(fresh)
    validated = late_fit.validate_fresh_context_projection(
        projection,
        expected_corpus_identity=base.successor_corpus_identity(fresh),
    )

    assert validated["row_count"] == 2
    assert validated["policy_label_access"] is False
    assert set(validated["rows"][0]) == {
        "row_index",
        "seed",
        "battle_index",
        "floor",
        "floor_ratio",
        "player_hp_ratio",
        "potion_occupied_slots",
        "relic_occupied_slots",
        "player_hp_quartile",
        "context_cell_id",
    }
    assert not {
        "advantages",
        "positive",
        "target_advantage",
        "target_return",
        "branch_returns",
    }.intersection(validated["rows"][0])

    contaminated = copy.deepcopy(projection)
    contaminated["rows"][0]["target_advantage"] = 0.5
    with pytest.raises(ValueError, match="projection row fields"):
        late_fit.validate_fresh_context_projection(
            contaminated,
            expected_corpus_identity=base.successor_corpus_identity(fresh),
        )


def test_projection_context_metrics_equal_full_corpus_metrics() -> None:
    fresh = _corpus("fresh", seeds=(291000, 291001), floors=(28, 33))
    target_rows = _target_rows(fresh)
    projection = late_fit.build_fresh_context_projection(fresh)

    projected = late_fit.derive_context_weights_from_projection(
        target_rows, projection
    )
    full = live_target.derive_context_weights_from_target(target_rows, fresh)

    assert projected["cell_ids"] == full["cell_ids"]
    assert projected["matched_cell_ids"] == full["matched_cell_ids"]
    assert projected["metrics"] == full["metrics"]
    assert torch.equal(projected["weights"], full["weights"])


def test_conditional_fit_stops_before_fit_and_fresh_loader_on_support_failure() -> None:
    calls = []

    result = late_fit.run_if_supported(
        {"gate": {"passed": False}},
        fit=lambda: calls.append("fit"),
    )

    assert calls == []
    assert result == {
        "fit_executed": False,
        "fit_result": None,
        "decision": "development_support_insufficient_close_without_fit",
    }


def test_conditional_fit_executes_once_after_support_pass() -> None:
    calls = []

    result = late_fit.run_if_supported(
        {"gate": {"passed": True}},
        fit=lambda: calls.append("fit") or {"decision": "complete"},
    )

    assert calls == ["fit"]
    assert result["fit_executed"] is True
    assert result["fit_result"] == {"decision": "complete"}


def test_collection_package_validation_uses_projection_without_loading_fresh(
    tmp_path: Path, monkeypatch
) -> None:
    fresh = _corpus("fresh", seeds=(291000, 291001))
    projection = late_fit.build_fresh_context_projection(fresh)
    output = tmp_path / "collection"
    output.mkdir()
    for name in (
        "fit_corpus.pt",
        "calibration_corpus.pt",
        "fresh_corpus.pt",
        "registration.json",
    ):
        (output / name).write_bytes(name.encode("ascii"))
    (output / "fresh_context.json").write_bytes(
        late_fit._canonical_json_bytes(projection)
    )
    report = {
        "schema_version": late_fit.COLLECTION_REPORT_SCHEMA,
        "decision": "development_support_ready_for_registered_fit",
        "partitions": {
            "fresh": {"identity": base.successor_corpus_identity(fresh)}
        },
        "fresh_context_projection": {
            "projection_identity_sha256": projection[
                "projection_identity_sha256"
            ]
        },
        "development_support": {"gate": {"passed": True}},
        "fresh_policy_evaluation": False,
        "contamination": copy.deepcopy(late_fit.CONTAMINATION),
        "authority": copy.deepcopy(late_fit.COLLECTION_AUTHORITY),
    }
    (output / "report.json").write_bytes(late_fit._canonical_json_bytes(report))
    artifacts = {
        path.name: {
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "size_bytes": path.stat().st_size,
        }
        for path in output.iterdir()
    }
    manifest = {
        "decision": report["decision"],
        "artifacts": artifacts,
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest), encoding="ascii"
    )
    monkeypatch.setattr(
        base,
        "_load_successor_corpus",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("fresh corpus must not be deserialized")
        ),
    )

    validated = late_fit._validate_collection_package(
        {
            "collection_manifest": output / "manifest.json",
            "collection_report": output / "report.json",
            "fresh_context_projection": output / "fresh_context.json",
        }
    )

    assert validated["decision"] == report["decision"]


def test_fit_registration_binds_sealed_collection_and_fixed_recipe(
    tmp_path: Path,
) -> None:
    inputs = _bindings(tmp_path, late_fit.FIT_INPUT_NAMES)
    registration = late_fit.build_fit_registration("b" * 40, inputs=inputs)
    validated = late_fit.validate_fit_registration(registration)

    assert validated["recipe"] == base.FIXED_ABLATION_RECIPE
    assert validated["authority"]["model_fitting"] is True
    assert validated["authority"]["fresh_evaluation"] is True
    assert validated["authority"]["gameplay"] is False
    assert validated["contamination"]["independent_confirmation"] is False

    registration["recipe"]["updates"] += 1
    with pytest.raises(ValueError, match="registration payload differs"):
        late_fit.validate_fit_registration(registration)
