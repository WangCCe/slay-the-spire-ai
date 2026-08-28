from __future__ import annotations

import copy

import pytest
import torch

from analysis_scripts.combat_rl_action_relative_selective_classifier_fit import (
    FIXED_OFFLINE_GATES,
    FIXED_RECIPE,
    apply_offline_gates,
    calibrate_threshold,
    evaluate_selective_corpus,
    fit_selective_classifier,
    split_selective_corpus,
)
from spirecomm.ai.rl.v2.action_relative_selective_classifier import (
    ActionRelativeSelectiveClassifier,
    ActionRelativeSelectiveConfig,
)
from spirecomm.ai.rl.v2.latent_gated_adapter import state_dict_sha256
from spirecomm.ai.rl.v2.network import create_dqn_v2


METADATA = {
    "network_type": "standard",
    "continuous_dim": 4,
    "action_dim": 91,
    "card_vocab": 5,
    "potion_vocab": 4,
    "relic_vocab": 3,
    "card_slots": 1,
    "potion_slots": 1,
    "relic_slots": 1,
}


def _corpus() -> tuple[dict[str, torch.Tensor], list[dict]]:
    row_count = 4
    masks = torch.zeros((row_count, 91), dtype=torch.bool)
    masks[:, :4] = True
    tensors = {
        "continuous": torch.arange(16, dtype=torch.float32).reshape(row_count, 4),
        "card_ids": torch.tensor([[1], [2], [3], [4]]),
        "potion_ids": torch.tensor([[1], [2], [3], [1]]),
        "relic_ids": torch.tensor([[0], [1], [2], [0]]),
        "action_masks": masks,
        "guard_actions": torch.zeros(row_count, dtype=torch.long),
    }
    metadata = [
        {
            "seed": seed,
            "guard_action_index": 0,
            "guard_return": 0.0,
            "branch_returns": {"0": 0.0, "1": -1.0, "2": 0.0, "3": 1.0},
        }
        for seed in (10, 11, 20, 21)
    ]
    return tensors, metadata


def test_split_is_seed_disjoint_tensor_aligned_and_class_complete():
    tensors, metadata = _corpus()

    split = split_selective_corpus(
        tensors,
        metadata,
        fit_seeds=frozenset({10, 11}),
        calibration_seeds=frozenset({20, 21}),
    )

    assert split["fit"]["row_indices"].tolist() == [0, 1]
    assert split["calibration"]["row_indices"].tolist() == [2, 3]
    assert split["fit"]["pair_count"] == 6
    assert split["fit"]["class_support"] == {
        "severe": 2,
        "neutral": 2,
        "beneficial": 2,
    }
    assert split["fit"]["split_sha256"] != split["calibration"]["split_sha256"]

    with pytest.raises(ValueError, match="disjoint"):
        split_selective_corpus(
            tensors,
            metadata,
            fit_seeds=frozenset({10, 11}),
            calibration_seeds=frozenset({11, 20, 21}),
        )
    with pytest.raises(ValueError, match="outside"):
        split_selective_corpus(
            tensors,
            metadata,
            fit_seeds=frozenset({10}),
            calibration_seeds=frozenset({20, 21}),
        )


def test_small_fit_and_calibration_are_deterministic_and_freeze_parent():
    tensors, metadata = _corpus()
    split = split_selective_corpus(
        tensors,
        metadata,
        fit_seeds=frozenset({10, 11}),
        calibration_seeds=frozenset({20, 21}),
    )
    recipe = copy.deepcopy(FIXED_RECIPE)
    recipe.update(
        {
            "hidden_dim": 8,
            "updates": 3,
            "samples_per_class_per_update": 2,
            "ranking_pairs_per_update": 2,
        }
    )
    torch.manual_seed(41)
    parent = create_dqn_v2(device="cpu", **METADATA)
    parent_before = state_dict_sha256(parent.state_dict())

    first, first_fit = fit_selective_classifier(
        parent=parent,
        metadata=METADATA,
        corpus=split["fit"]["corpus"],
        recipe=recipe,
    )
    second, second_fit = fit_selective_classifier(
        parent=parent,
        metadata=METADATA,
        corpus=split["fit"]["corpus"],
        recipe=recipe,
    )

    assert first_fit["sampling_plan_sha256"] == second_fit["sampling_plan_sha256"]
    assert state_dict_sha256(first.classifier.state_dict()) == state_dict_sha256(
        second.classifier.state_dict()
    )
    assert state_dict_sha256(parent.state_dict()) == parent_before
    assert first_fit["parent_frozen"] is True

    calibrated, calibration = calibrate_threshold(
        first,
        split["calibration"]["corpus"],
        quantile=float(recipe["calibration_quantile"]),
    )
    assert calibrated.selection_threshold == calibration["selection_threshold"]
    assert calibration["negative_count"] == 4
    assert calibration["finite_sample_rank"] == 4


def test_offline_gate_uses_registered_strict_value_and_regret_bounds():
    metrics = {
        "selection": {
            "intervention_count": 30,
            "intervention_precision": 0.65,
            "mean_selected_true_advantage": FIXED_OFFLINE_GATES[
                "minimum_mean_selected_true_advantage_exclusive"
            ]
            + 1e-6,
            "severe_harm_count": 0,
            "illegal_action_count": 0,
            "forbidden_action_selection_count": 0,
        },
        "ranking": {
            "mean_policy_regret": FIXED_OFFLINE_GATES[
                "maximum_mean_policy_regret_exclusive"
            ]
            - 1e-6
        },
    }
    assert apply_offline_gates(metrics)["all_conditions_passed"] is True

    metrics["selection"]["mean_selected_true_advantage"] = FIXED_OFFLINE_GATES[
        "minimum_mean_selected_true_advantage_exclusive"
    ]
    failed = apply_offline_gates(metrics)
    assert failed["all_conditions_passed"] is False
    assert (
        failed["conditions"][
            "minimum_mean_selected_true_advantage_exclusive"
        ]
        is False
    )


def test_policy_metrics_keep_unsupported_rows_in_comparable_denominator():
    tensors, metadata = _corpus()
    tensors["action_masks"][-1, 90] = True
    metadata[-1]["branch_returns"] = {"0": 0.0, "90": 2.0}
    torch.manual_seed(43)
    parent = create_dqn_v2(device="cpu", **METADATA)
    classifier = ActionRelativeSelectiveClassifier(
        parent,
        METADATA,
        ActionRelativeSelectiveConfig(hidden_dim=8),
        selection_threshold=100.0,
    )

    metrics = evaluate_selective_corpus(
        classifier,
        tensors,
        metadata,
        forbidden_action_indices=[90],
        severe_harm_floor=-0.5,
    )

    assert metrics["source_row_count"] == 4
    assert metrics["row_count"] == 4
    assert metrics["supported_row_count"] == 3
    assert metrics["excluded_unsupported_only_row_count"] == 1
    assert metrics["selection"]["no_allowed_alternative_count"] == 1
    assert metrics["selection"]["intervention_count"] == 0
