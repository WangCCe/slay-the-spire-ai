from __future__ import annotations

import copy
from pathlib import Path

import pytest
import torch

from analysis_scripts import combat_rl_real_context_balanced_corpus as balanced


def _corpus(
    *,
    partition: str,
    floors: list[int],
    seeds: list[int],
    potion_counts: list[int] | None = None,
    relic_counts: list[int] | None = None,
    hp_ratios: list[float] | None = None,
) -> dict:
    count = len(floors)
    assert len(seeds) == count
    potion_counts = potion_counts or [0] * count
    relic_counts = relic_counts or [1] * count
    hp_ratios = hp_ratios or [0.5] * count
    continuous = torch.zeros((count, 4), dtype=torch.float32)
    continuous[:, 0] = torch.tensor(hp_ratios)
    continuous[:, 3] = torch.tensor(floors, dtype=torch.float32) / 50.0
    potion_ids = torch.zeros((count, 3), dtype=torch.long)
    relic_ids = torch.zeros((count, 8), dtype=torch.long)
    for row, occupied in enumerate(potion_counts):
        potion_ids[row, :occupied] = torch.arange(1, occupied + 1)
    for row, occupied in enumerate(relic_counts):
        relic_ids[row, :occupied] = torch.arange(1, occupied + 1)
    action_masks = torch.ones((count, 6), dtype=torch.bool)
    positive = torch.tensor([row % 2 == 0 for row in range(count)])
    return {
        "partition": partition,
        "tensors": {
            "continuous": continuous,
            "card_ids": torch.zeros((count, 10), dtype=torch.long),
            "potion_ids": potion_ids,
            "relic_ids": relic_ids,
            "action_masks": action_masks,
            "guard_actions": torch.ones(count, dtype=torch.long),
            "target_actions": torch.full((count,), 2, dtype=torch.long),
            "advantages": torch.where(positive, 1.0, -1.0),
            "positive": positive,
        },
        "metadata": [
            {
                "seed": seed,
                "floor": floor,
                "encounter": f"encounter-{row}",
                "guard_action_index": 1,
                "target_action_index": 2,
            }
            for row, (seed, floor) in enumerate(zip(seeds, floors, strict=True))
        ],
        "row_count": count,
    }


def test_fixed_cohort_is_disjoint_and_targets_late_battles() -> None:
    assert balanced.FIXED_RECIPE["train_seed_first"] == 268000
    assert balanced.FIXED_RECIPE["train_seed_last"] == 269023
    assert balanced.FIXED_RECIPE["evaluation_seed_first"] == 270000
    assert balanced.FIXED_RECIPE["evaluation_seed_last"] == 270511
    assert balanced.FIXED_RECIPE["battle_indices"] == [10, 11, 12, 13, 14]
    assert balanced.FIXED_RECIPE["target_floor_first"] == 23
    assert balanced.FIXED_RECIPE["target_floor_last"] == 34
    balanced.validate_seed_isolation(
        base_train=range(264000, 265024),
        base_evaluation=range(266000, 266256),
        supplement_train=range(268000, 269024),
        supplement_evaluation=range(270000, 270512),
    )


def test_floor_filter_and_combination_preserve_alignment_and_sources() -> None:
    base = _corpus(partition="train", floors=[5, 20], seeds=[1, 2])
    supplement = _corpus(
        partition="train", floors=[22, 23, 34, 35], seeds=[3, 4, 5, 6]
    )
    filtered, exclusions = balanced.filter_supplement_corpus(supplement)
    assert filtered["row_count"] == 2
    assert [row["floor"] for row in filtered["metadata"]] == [23, 34]
    assert exclusions == {"below_target_floor": 1, "above_target_floor": 1}

    combined = balanced.combine_corpora(base, filtered, partition="train")
    assert combined["row_count"] == 4
    assert combined["tensors"]["continuous"].shape[0] == 4
    assert [row["source_component"] for row in combined["metadata"]] == [
        "expanded_base",
        "expanded_base",
        "late_supplement",
        "late_supplement",
    ]
    assert [row["seed"] for row in combined["metadata"]] == [1, 2, 4, 5]


def test_seed_overlap_is_rejected() -> None:
    with pytest.raises(ValueError, match="seed partitions overlap"):
        balanced.validate_seed_isolation(
            base_train=[1],
            base_evaluation=[2],
            supplement_train=[3],
            supplement_evaluation=[2],
        )


def test_exact_context_weights_zero_unmatched_cells_and_normalize() -> None:
    real = _corpus(
        partition="real",
        floors=[12, 12, 24, 24],
        seeds=[1, 2, 3, 4],
        potion_counts=[0, 0, 1, 1],
        relic_counts=[2, 2, 4, 4],
        hp_ratios=[0.4, 0.4, 0.6, 0.6],
    )
    simulator = _corpus(
        partition="train",
        floors=[12, 12, 24, 30],
        seeds=[5, 6, 7, 8],
        potion_counts=[0, 0, 1, 2],
        relic_counts=[2, 2, 4, 6],
        hp_ratios=[0.4, 0.4, 0.6, 0.9],
    )
    result = balanced.derive_context_weights(real, simulator)
    weights = result["weights"]
    assert torch.isclose(weights.sum(), torch.tensor(1.0, dtype=weights.dtype))
    assert weights.tolist() == pytest.approx([0.25, 0.25, 0.5, 0.0])
    assert result["metrics"]["real_context_mass_covered"] == pytest.approx(1.0)
    assert result["metrics"]["simulator_mass_retained"] == pytest.approx(0.75)
    assert result["metrics"]["effective_sample_size"] == pytest.approx(8.0 / 3.0)
    assert result["cell_ids"][0] == result["cell_ids"][1]
    assert result["cell_ids"][3] not in result["matched_cell_ids"]


def test_weight_report_includes_raw_and_weighted_smd() -> None:
    real = _corpus(
        partition="real",
        floors=[12, 24],
        seeds=[1, 2],
        potion_counts=[0, 1],
        relic_counts=[2, 4],
        hp_ratios=[0.4, 0.6],
    )
    simulator = _corpus(
        partition="evaluation",
        floors=[12, 12, 24],
        seeds=[3, 4, 5],
        potion_counts=[0, 0, 1],
        relic_counts=[2, 2, 4],
        hp_ratios=[0.4, 0.4, 0.6],
    )
    metrics = balanced.derive_context_weights(real, simulator)["metrics"]
    for name in (
        "floor_ratio",
        "player_hp_ratio",
        "potion_occupied_slots",
        "relic_occupied_slots",
    ):
        assert set(metrics["standardized_mean_differences"][name]) == {
            "raw",
            "weighted",
        }
    assert metrics["standardized_mean_differences"]["potion_occupied_slots"][
        "weighted"
    ] == pytest.approx(0.0)


def _passing_partition_metrics(*, ess: float) -> dict:
    return {
        "real_context_mass_covered": 0.95,
        "floor_context_mass_covered": {
            "floor_23_27": 0.85,
            "floor_28_34": 0.70,
        },
        "effective_sample_size": ess,
        "maximum_normalized_weight": 0.01,
        "standardized_mean_differences": {
            "floor_ratio": {"weighted": 0.25},
            "player_hp_ratio": {"weighted": 0.15},
            "potion_occupied_slots": {"weighted": 0.10},
            "relic_occupied_slots": {"weighted": 0.10},
        },
    }


def test_support_gate_passes_only_complete_registered_conditions() -> None:
    result = balanced.apply_support_gates(
        train_metrics=_passing_partition_metrics(ess=800.0),
        evaluation_metrics=_passing_partition_metrics(ess=450.0),
        evaluation_late_floor_rows=300,
        integrity_conditions={
            "class_complete": True,
            "finite": True,
            "legal": True,
            "provenance": True,
            "seed_isolation": True,
        },
    )
    assert result["passed"] is True
    assert result["decision"] == "corpus_support_ready_for_separate_weighted_fit"
    assert all(result["conditions"].values())


def test_support_gate_fails_closed_without_changing_thresholds() -> None:
    evaluation = _passing_partition_metrics(ess=399.0)
    result = balanced.apply_support_gates(
        train_metrics=_passing_partition_metrics(ess=800.0),
        evaluation_metrics=evaluation,
        evaluation_late_floor_rows=300,
        integrity_conditions={
            "class_complete": True,
            "finite": True,
            "legal": True,
            "provenance": True,
            "seed_isolation": True,
        },
    )
    assert result["passed"] is False
    assert result["conditions"]["evaluation_effective_sample_size"] is False
    assert result["decision"] == "corpus_support_insufficient_close_without_fit"
    assert balanced.FIXED_GATES["evaluation_effective_sample_size_minimum"] == 400.0


@pytest.mark.parametrize("mutation", ["nonfinite", "illegal_guard", "illegal_target"])
def test_corpus_validation_rejects_nonfinite_and_illegal_rows(mutation: str) -> None:
    corpus = _corpus(partition="train", floors=[24, 25], seeds=[1, 2])
    if mutation == "nonfinite":
        corpus["tensors"]["continuous"][0, 0] = float("nan")
    elif mutation == "illegal_guard":
        corpus["tensors"]["action_masks"][0, 1] = False
    else:
        corpus["tensors"]["action_masks"][0, 2] = False
    with pytest.raises(ValueError, match="finite|illegal"):
        balanced.validate_corpus(corpus, expected_partition="train")


def test_corpus_validation_rejects_misaligned_metadata() -> None:
    corpus = _corpus(partition="train", floors=[24, 25], seeds=[1, 2])
    corpus["metadata"].pop()
    with pytest.raises(ValueError, match="row counts differ"):
        balanced.validate_corpus(corpus, expected_partition="train")


def test_output_path_must_be_absent_including_staging(tmp_path: Path) -> None:
    output = tmp_path / "result"
    staging = tmp_path / ".result.staging"
    balanced.ensure_output_paths_absent(output, staging)
    output.mkdir()
    with pytest.raises(ValueError, match="output already exists"):
        balanced.ensure_output_paths_absent(output, staging)
    output.rmdir()
    staging.mkdir()
    with pytest.raises(ValueError, match="staging output already exists"):
        balanced.ensure_output_paths_absent(output, staging)


def test_registration_binds_fixed_recipe_inputs_and_authority() -> None:
    registration = balanced.build_registration("a" * 40)
    validated = balanced.validate_registration(registration)
    assert validated["source_commit"] == "a" * 40
    assert validated["recipe"] == balanced.FIXED_RECIPE
    assert validated["gates"] == balanced.FIXED_GATES
    assert validated["authority"]["training"] is False
    assert validated["authority"]["gameplay"] is False
    assert set(validated["inputs"]) == set(balanced.FIXED_INPUTS)


@pytest.mark.parametrize("mutation", ["recipe", "input_hash", "output", "authority"])
def test_registration_rejects_drift(mutation: str) -> None:
    registration = balanced.build_registration("a" * 40)
    if mutation == "recipe":
        registration["recipe"]["battle_indices"] = [10, 11]
    elif mutation == "input_hash":
        registration["inputs"]["native_module"]["sha256"] = "0" * 64
    elif mutation == "output":
        registration["output_dir"] = "D:/different"
    else:
        registration["authority"]["training"] = True
    with pytest.raises(ValueError, match="differs"):
        balanced.validate_registration(copy.deepcopy(registration))
