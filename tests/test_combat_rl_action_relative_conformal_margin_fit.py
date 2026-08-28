from __future__ import annotations

import copy

import pytest
import torch

import analysis_scripts.combat_rl_action_relative_conformal_margin_fit as fit_runner
from analysis_scripts.combat_rl_action_relative_conformal_margin_fit import (
    FIXED_OFFLINE_GATES,
    FIXED_RECIPE,
    REGISTERED_AUTHORITY,
    SOURCE_SNAPSHOT_PATHS,
    apply_offline_gates,
    calibrate_action_families,
    finite_sample_conformal_correction,
    split_fit_calibration_corpus,
    validate_registration_payload,
)


def _registration() -> dict:
    runner = fit_runner.REPO_ROOT / SOURCE_SNAPSHOT_PATHS[0]
    return {
        "schema_version": 1,
        "experiment_id": fit_runner.EXPERIMENT_ID,
        "source_commit": "a" * 40,
        "runner": {"path": str(runner), "sha256": "b" * 64},
        "source_files": {
            path: ("b" * 64 if path == SOURCE_SNAPSHOT_PATHS[0] else "c" * 64)
            for path in SOURCE_SNAPSHOT_PATHS
        },
        "inputs": {
            "items_json": {"path": "D:/fixture/items.json", "sha256": "d" * 64},
            "parent_checkpoint": {"path": "D:/fixture/parent.pth", "sha256": "e" * 64},
            "train_corpus": {"path": "D:/fixture/train.pt", "sha256": "f" * 64},
            "evaluation_corpus": {"path": "D:/fixture/eval.pt", "sha256": "1" * 64},
            "baseline_fit_report": {"path": "D:/fixture/base.json", "sha256": "2" * 64},
            "uncertainty_fit_report": {"path": "D:/fixture/ensemble.json", "sha256": "3" * 64},
            "error_audit": {"path": "D:/fixture/audit.md", "sha256": "4" * 64},
        },
        "recipe": copy.deepcopy(FIXED_RECIPE),
        "offline_gates": copy.deepcopy(FIXED_OFFLINE_GATES),
        "output_dir": str(fit_runner.REPORTS_ROOT / "conformal_fit_fixture"),
        "authority": copy.deepcopy(REGISTERED_AUTHORITY),
    }


def _corpus_fixture() -> tuple[dict[str, torch.Tensor], list[dict]]:
    tensors = {
        "continuous": torch.arange(24, dtype=torch.float32).reshape(6, 4),
        "card_ids": torch.arange(6).reshape(6, 1),
        "potion_ids": torch.zeros((6, 1), dtype=torch.long),
        "relic_ids": torch.zeros((6, 1), dtype=torch.long),
        "action_masks": torch.ones((6, 91), dtype=torch.bool),
        "guard_actions": torch.zeros(6, dtype=torch.long),
    }
    metadata = [
        {
            "seed": seed,
            "guard_action_index": 0,
            "guard_return": 0.0,
            "branch_returns": {"0": 0.0, "1": 1.0, "60": 2.0, "90": -1.0},
        }
        for seed in (10, 10, 11, 12, 13, 13)
    ]
    return tensors, metadata


def test_seed_split_is_exact_aligned_and_disjoint():
    tensors, metadata = _corpus_fixture()
    split = split_fit_calibration_corpus(
        tensors,
        metadata,
        fit_seeds=frozenset({10, 11}),
        calibration_seeds=frozenset({12, 13}),
        minimum_family_support=1,
    )

    assert split["fit"]["row_indices"].tolist() == [0, 1, 2]
    assert split["calibration"]["row_indices"].tolist() == [3, 4, 5]
    assert split["fit"]["tensors"]["continuous"][:, 0].tolist() == [0.0, 4.0, 8.0]
    assert [row["seed"] for row in split["calibration"]["metadata"]] == [12, 13, 13]
    assert split["fit"]["family_support"] == {"card": 3, "potion": 3}
    assert split["calibration"]["family_support"] == {"card": 3, "potion": 3}


def test_supported_corpus_drops_unsupported_only_rows_with_tensor_alignment():
    tensors, metadata = _corpus_fixture()
    metadata[0]["branch_returns"] = {"0": 0.0, "90": -1.0}

    supported = fit_runner._supported_corpus(tensors, metadata)

    assert supported["row_indices"].tolist() == [1, 2, 3, 4, 5]
    assert supported["excluded_unsupported_only_row_count"] == 1
    assert supported["tensors"]["continuous"][:, 0].tolist() == [4.0, 8.0, 12.0, 16.0, 20.0]
    assert len(supported["metadata"]) == 5
    assert all("90" not in row["branch_returns"] for row in supported["metadata"])


@pytest.mark.parametrize("failure", ["overlap", "outside", "support"])
def test_seed_split_rejects_overlap_outside_and_insufficient_support(failure):
    tensors, metadata = _corpus_fixture()
    fit = frozenset({10, 11})
    calibration = frozenset({12, 13})
    minimum = 1
    if failure == "overlap":
        calibration = frozenset({11, 12, 13})
    elif failure == "outside":
        metadata[0]["seed"] = 99
    else:
        minimum = 4
    with pytest.raises(ValueError):
        split_fit_calibration_corpus(
            tensors,
            metadata,
            fit_seeds=fit,
            calibration_seeds=calibration,
            minimum_family_support=minimum,
        )


def test_finite_sample_correction_uses_higher_rank_and_clamps_at_zero():
    correction = finite_sample_conformal_correction(
        torch.tensor([-2.0, -1.0, 0.0, 1.0]), alpha=0.25
    )
    assert correction["rank"] == 4
    assert correction["raw_correction"] == pytest.approx(1.0)
    assert correction["correction"] == pytest.approx(1.0)

    clamped = finite_sample_conformal_correction(
        torch.tensor([-3.0, -2.0, -1.0]), alpha=0.25
    )
    assert clamped["raw_correction"] == pytest.approx(-1.0)
    assert clamped["correction"] == pytest.approx(0.0)


def test_action_family_calibration_is_separate_and_fixed():
    result = calibrate_action_families(
        candidate_actions=torch.tensor([1, 2, 60, 61]),
        raw_scores=torch.tensor([1.0, 2.0, 3.0, 5.0]),
        true_advantages=torch.tensor([0.5, 0.5, 2.0, 1.0]),
        alpha=0.5,
        minimum_family_support=2,
    )

    assert result["corrections"] == {"card": pytest.approx(1.5), "potion": pytest.approx(4.0)}
    assert result["support"] == {"card": 2, "potion": 2}


def test_offline_gates_include_severe_harm_and_existing_quality_bounds():
    passing = {
        "selection": {
            "intervention_count": 30,
            "intervention_precision": 0.65,
            "mean_selected_true_advantage": 0.13,
            "severe_harm_count": 0,
            "illegal_action_count": 0,
            "forbidden_action_selection_count": 0,
        },
        "ranking": {"mean_policy_regret": 3.2},
    }
    assert apply_offline_gates(passing)["all_conditions_passed"] is True
    assert FIXED_OFFLINE_GATES["maximum_severe_harm_count"] == 0

    failing = copy.deepcopy(passing)
    failing["selection"]["severe_harm_count"] = 1
    result = apply_offline_gates(failing)
    assert result["all_conditions_passed"] is False
    assert result["decision"] == "offline_failed_close_without_fresh_gate_or_sweep"


def test_registration_binds_fixed_split_recipe_gates_and_inputs():
    assert FIXED_RECIPE["fit_seed_first"] == 262000
    assert FIXED_RECIPE["fit_seed_last"] == 262191
    assert FIXED_RECIPE["calibration_seed_first"] == 262192
    assert FIXED_RECIPE["calibration_seed_last"] == 262255
    assert FIXED_RECIPE["calibration_alpha"] == pytest.approx(0.1)
    assert validate_registration_payload(_registration()) == _registration()


@pytest.mark.parametrize(
    "mutation",
    ["root", "source", "runner", "inputs", "overlap", "recipe", "gate", "authority", "output"],
)
def test_registration_rejects_mutation(mutation):
    payload = _registration()
    if mutation == "root":
        payload["unexpected"] = True
    elif mutation == "source":
        payload["source_commit"] = "z" * 40
    elif mutation == "runner":
        payload["runner"]["sha256"] = "9" * 64
    elif mutation == "inputs":
        del payload["inputs"]["error_audit"]
    elif mutation == "overlap":
        payload["inputs"]["evaluation_corpus"]["sha256"] = payload["inputs"][
            "train_corpus"
        ]["sha256"]
    elif mutation == "recipe":
        payload["recipe"]["calibration_alpha"] = 0.2
    elif mutation == "gate":
        payload["offline_gates"]["maximum_severe_harm_count"] = 1
    elif mutation == "authority":
        payload["authority"]["native_loading"] = True
    else:
        payload["output_dir"] = "D:/outside"
    with pytest.raises(ValueError):
        validate_registration_payload(payload)
