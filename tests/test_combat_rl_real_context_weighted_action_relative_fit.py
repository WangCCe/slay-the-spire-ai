from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import torch

from analysis_scripts import combat_rl_real_context_weighted_action_relative_fit as fit


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_fixed_inputs_bind_support_passing_corpora_and_real_replays() -> None:
    assert fit.EXPERIMENT_ID.endswith("-r2")
    assert fit.FIXED_INPUTS["predecessor_failure"]["sha256"] == (
        "544ef6acf2d103c7c1f1bbe2aeca3f2c1355d3de63b6a2c291ea466bb14f5524"
    )
    assert fit.FIXED_INPUTS["train_corpus"]["sha256"] == (
        "af2c1d40f307eacee951333462ad5688e276f6006c8a6b0b5f5189b92845bbe2"
    )
    assert fit.FIXED_INPUTS["base_evaluation_corpus"]["sha256"] == (
        "c91532a0a5eb9ce8dc5611bdf54104f24b4567a78ad03425615dec574a6de6ce"
    )
    assert fit.FIXED_INPUTS["evaluation_supplement"]["sha256"] == (
        "e63bbc303abef4a71ad545cb55481d0bdeb74429a835edfcb612139aa8b3b1df"
    )
    assert fit.FIXED_INPUTS["real_r14_replay"]["sha256"] == (
        "eed11099d1b8d35baa8ce0ccbf87efb6fb4a864e6fe6246837b0cac91c505014"
    )
    assert fit.FIXED_INPUTS["real_r15_replay"]["sha256"] == (
        "67c3a49fbb2094d20793214c0a4a294684054eb6f4a24ac59573fab29c39a2dd"
    )
    assert fit.FIXED_RECIPE["updates"] == 4096
    assert fit.FIXED_RECIPE["include_item_semantics"] is True
    assert fit.RESULT_AUTHORITY["development_candidate"] is True
    assert fit.RESULT_AUTHORITY["gameplay"] is False
    assert fit.RESULT_AUTHORITY["production_checkpoint_writing"] is False


def test_support_gate_report_binding_is_exact_and_passed() -> None:
    report = json.loads(
        (REPO_ROOT / "reports/combat_rl_floor_23_27_context_support_gate_20260829_r1.json")
        .read_text(encoding="ascii")
    )
    conditions = fit.validate_support_gate_report(report)
    assert all(conditions.values())

    changed = copy.deepcopy(report)
    changed["decision"] = "corpus_support_insufficient_close_without_fit"
    with pytest.raises(ValueError, match="support gate binding differs"):
        fit.validate_support_gate_report(changed)


def test_bound_train_parity_split_has_registered_rows_and_weight_support() -> None:
    real, _ = fit.load_real_replay_bindings(
        (
            fit.RealReplayBinding(
                label="r14",
                path=fit.FIXED_INPUTS["real_r14_replay"]["path"],
                sha256=fit.FIXED_INPUTS["real_r14_replay"]["sha256"],
            ),
            fit.RealReplayBinding(
                label="r15",
                path=fit.FIXED_INPUTS["real_r15_replay"]["path"],
                sha256=fit.FIXED_INPUTS["real_r15_replay"]["sha256"],
            ),
        )
    )
    raw = fit.load_corpus(
        fit.FIXED_INPUTS["train_corpus"]["path"], expected_partition="train"
    )
    train = {
        "partition": "train",
        "tensors": {
            name: raw["tensors"][name] for name in fit.balanced.TENSOR_NAMES
        },
        "metadata": raw["metadata"],
        "row_count": raw["row_count"],
    }
    split = fit.seed_parity_split_indices(train["metadata"])
    assert split["fit"].numel() == 4100
    assert split["calibration"].numel() == 4213
    assert set(split["fit"].tolist()).isdisjoint(split["calibration"].tolist())

    for name in ("fit", "calibration"):
        partition = fit._selected_corpus(train, split[name], partition="train")
        context = fit.balanced.derive_context_weights(real, partition)
        supported = fit.build_supported_selective_corpus(
            partition["tensors"], partition["metadata"]
        )
        split_report = fit._split_report(
            name, split[name], partition, supported, context
        )
        assert set(split_report["class_support"]) == {
            "severe",
            "neutral",
            "beneficial",
        }
        state_weights = context["weights"][supported["source_row_indices"]]
        pair_weights = fit.derive_pair_sampling_weights(
            supported["pair_row_indices"],
            state_weights,
            labels=supported["labels"],
        )
        assert context["metrics"]["real_context_mass_covered"] >= 0.90
        assert all(mass > 0.0 for mass in pair_weights["class_mass"])
        ranking_pairs = fit.build_within_state_ranking_pairs(
            supported["pair_row_indices"], supported["labels"]
        )
        ranking_weights = fit.derive_ranking_sampling_weights(
            ranking_pairs, supported["pair_row_indices"], state_weights
        )
        assert torch.isclose(
            ranking_weights.sum(), torch.tensor(1.0, dtype=ranking_weights.dtype)
        )


def test_seed_parity_split_is_disjoint_and_complete() -> None:
    metadata = [{"seed": seed} for seed in (10, 11, 10, 13, 12)]
    split = fit.seed_parity_split_indices(metadata)
    assert split["fit"].tolist() == [0, 2, 4]
    assert split["calibration"].tolist() == [1, 3]

    with pytest.raises(ValueError, match="seed is invalid"):
        fit.seed_parity_split_indices([{"seed": True}])


def test_pair_weights_preserve_each_state_mass_and_normalize_by_class() -> None:
    pair_rows = torch.tensor([0, 0, 1, 2, 2, 2])
    state_weights = torch.tensor([0.6, 0.4, 0.0], dtype=torch.float64)
    labels = torch.tensor([0, 1, 1, 0, 1, 2])

    result = fit.derive_pair_sampling_weights(
        pair_rows, state_weights, labels=labels
    )
    assert result["raw"].tolist() == pytest.approx([0.3, 0.3, 0.4, 0.0, 0.0, 0.0])
    assert result["raw"].sum().item() == pytest.approx(1.0)
    assert result["normalized_by_class"].tolist() == pytest.approx(
        [1.0, 0.3 / 0.7, 0.4 / 0.7, 0.0, 0.0, 0.0]
    )
    assert result["class_mass"] == pytest.approx([0.3, 0.7, 0.0])

    with pytest.raises(ValueError, match="positive sampling mass"):
        fit.build_weighted_class_balanced_sample_plan(
            labels,
            result["normalized_by_class"],
            updates=2,
            samples_per_class=2,
            seed=7,
        )


def test_weighted_class_plan_is_deterministic_and_never_draws_zero_mass() -> None:
    labels = torch.tensor([0, 0, 1, 1, 2, 2])
    weights = torch.tensor([1.0, 0.0, 0.25, 0.75, 0.0, 1.0], dtype=torch.float64)
    first = fit.build_weighted_class_balanced_sample_plan(
        labels, weights, updates=8, samples_per_class=4, seed=19
    )
    second = fit.build_weighted_class_balanced_sample_plan(
        labels, weights, updates=8, samples_per_class=4, seed=19
    )
    assert torch.equal(first, second)
    assert first.shape == (8, 3, 4)
    assert 1 not in first[:, 0].reshape(-1).tolist()
    assert 4 not in first[:, 2].reshape(-1).tolist()


def test_ranking_weights_preserve_state_mass_and_plan_is_deterministic() -> None:
    pair_rows = torch.tensor([0, 0, 0, 1, 1])
    ranking_pairs = torch.tensor([[0, 1], [0, 2], [3, 4]])
    state_weights = torch.tensor([0.75, 0.25], dtype=torch.float64)
    weights = fit.derive_ranking_sampling_weights(
        ranking_pairs, pair_rows, state_weights
    )
    assert weights.tolist() == pytest.approx([0.375, 0.375, 0.25])
    first = fit.build_weighted_replacement_sample_plan(
        weights, updates=5, samples_per_update=3, seed=23
    )
    second = fit.build_weighted_replacement_sample_plan(
        weights, updates=5, samples_per_update=3, seed=23
    )
    assert torch.equal(first, second)
    assert first.shape == (5, 3)


def test_weighted_higher_quantile_reduces_to_existing_equal_weight_rank() -> None:
    threshold, details = fit.weighted_higher_quantile(
        torch.tensor([1.0, 2.0, 3.0, 4.0]),
        torch.ones(4, dtype=torch.float64),
        quantile=0.5,
    )
    assert threshold == pytest.approx(3.0)
    assert details["finite_sample_rank"] == 3
    assert details["cumulative_target"] == pytest.approx(0.75)

    weighted, _ = fit.weighted_higher_quantile(
        torch.tensor([1.0, 2.0, 3.0]),
        torch.tensor([0.1, 0.1, 0.8], dtype=torch.float64),
        quantile=0.5,
    )
    assert weighted == pytest.approx(3.0)


def test_weighted_policy_metrics_and_gate_keep_raw_safety_absolute() -> None:
    weighted = fit.weighted_policy_metrics(
        selected_true=torch.tensor([1.0, -1.0, 0.0]),
        best_with_guard=torch.tensor([1.5, 0.5, 0.0]),
        intervention_rows=torch.tensor([True, True, False]),
        state_weights=torch.tensor([0.8, 0.1, 0.1], dtype=torch.float64),
        beneficial_floor=0.5,
    )
    assert weighted["intervention_precision"] == pytest.approx(8.0 / 9.0)
    assert weighted["mean_selected_true_advantage"] == pytest.approx(0.7)
    assert weighted["mean_policy_regret"] == pytest.approx(0.55)

    raw = {
        "selection": {
            "intervention_count": 30,
            "severe_harm_count": 0,
            "illegal_action_count": 0,
            "forbidden_action_selection_count": 0,
        }
    }
    passing_weighted = {
        "intervention_precision": 0.65,
        "mean_selected_true_advantage": fit.FIXED_OFFLINE_GATES[
            "minimum_mean_selected_true_advantage_exclusive"
        ]
        + 1e-6,
        "mean_policy_regret": fit.FIXED_OFFLINE_GATES[
            "maximum_mean_policy_regret_exclusive"
        ]
        - 1e-6,
    }
    passed = fit.apply_weighted_offline_gates(raw, passing_weighted)
    assert passed["all_conditions_passed"] is True
    assert passed["decision"] == "offline_passed_propose_fresh_lightspeed_gate"

    raw["selection"]["severe_harm_count"] = 1
    failed = fit.apply_weighted_offline_gates(raw, passing_weighted)
    assert failed["all_conditions_passed"] is False
    assert failed["conditions"]["raw_severe_harm_count_zero"] is False


def test_formal_evaluation_append_preserves_base_and_marks_new_rows() -> None:
    def corpus(seed: int, source: str | None, *, positive: bool) -> dict:
        metadata = {
            "seed": seed,
            "floor": 23,
            "encounter": "Book of Stabbing",
            "guard_action_index": 1,
            "target_action_index": 2,
        }
        if source is not None:
            metadata["source_component"] = source
        return {
            "partition": "evaluation",
            "tensors": {
                "continuous": torch.zeros((1, 4)),
                "card_ids": torch.zeros((1, 10), dtype=torch.long),
                "potion_ids": torch.zeros((1, 3), dtype=torch.long),
                "relic_ids": torch.zeros((1, 8), dtype=torch.long),
                "action_masks": torch.tensor([[False, True, True]]),
                "guard_actions": torch.tensor([1]),
                "target_actions": torch.tensor([2]),
                "advantages": torch.tensor([1.0 if positive else -1.0]),
                "positive": torch.tensor([positive]),
            },
            "metadata": [metadata],
            "row_count": 1,
        }

    combined = fit.append_formal_evaluation_corpus(
        corpus(10, "expanded_base", positive=True),
        corpus(11, None, positive=False),
    )
    assert combined["row_count"] == 2
    assert [row["source_component"] for row in combined["metadata"]] == [
        "expanded_base",
        "floor_23_27_fresh_evaluation_supplement",
    ]


def test_loaded_evaluation_corpora_project_to_balanced_tensor_inventory() -> None:
    for name in ("base_evaluation_corpus", "evaluation_supplement"):
        corpus = fit._loaded_balanced_corpus(
            fit.FIXED_INPUTS[name]["path"], partition="evaluation"
        )
        assert set(corpus["tensors"]) == set(fit.balanced.TENSOR_NAMES)
