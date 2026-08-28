from __future__ import annotations

import copy

import pytest
import torch

import analysis_scripts.combat_rl_action_relative_uncertainty_ensemble_fit as fit_runner
from analysis_scripts.combat_rl_action_relative_uncertainty_ensemble_fit import (
    FIXED_OFFLINE_GATES,
    FIXED_RECIPE,
    REGISTERED_AUTHORITY,
    SOURCE_SNAPSHOT_PATHS,
    apply_offline_gates,
    deterministic_bootstrap_indices,
    fit_ensemble,
    validate_registration_payload,
)
from spirecomm.ai.rl.v2.latent_gated_adapter import state_dict_sha256
from spirecomm.ai.rl.v2.network import create_dqn_v2


METADATA = {
    "network_type": "standard",
    "continuous_dim": 4,
    "action_dim": 4,
    "card_vocab": 5,
    "potion_vocab": 4,
    "relic_vocab": 3,
    "card_slots": 1,
    "potion_slots": 1,
    "relic_slots": 1,
}


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
            "parent_checkpoint": {
                "path": "D:/fixture/parent.pth",
                "sha256": "e" * 64,
            },
            "train_corpus": {"path": "D:/fixture/train.pt", "sha256": "f" * 64},
            "evaluation_corpus": {
                "path": "D:/fixture/eval.pt",
                "sha256": "1" * 64,
            },
            "prior_fit_report": {
                "path": "D:/fixture/prior.json",
                "sha256": "2" * 64,
            },
        },
        "recipe": copy.deepcopy(FIXED_RECIPE),
        "offline_gates": copy.deepcopy(FIXED_OFFLINE_GATES),
        "output_dir": str(fit_runner.REPORTS_ROOT / "uncertainty_ensemble_fit_fixture"),
        "authority": copy.deepcopy(REGISTERED_AUTHORITY),
    }


def _corpus_fixture() -> tuple[dict[str, torch.Tensor], list[dict]]:
    torch.manual_seed(23)
    row_count = 16
    tensors = {
        "continuous": torch.randn(row_count, 4),
        "card_ids": torch.randint(0, 5, (row_count, 1)),
        "potion_ids": torch.randint(0, 4, (row_count, 1)),
        "relic_ids": torch.randint(0, 3, (row_count, 1)),
        "action_masks": torch.ones((row_count, 4), dtype=torch.bool),
        "guard_actions": torch.zeros(row_count, dtype=torch.long),
    }
    metadata = []
    for index in range(row_count):
        first = 2.0 if index % 2 == 0 else -2.0
        metadata.append(
            {
                "guard_action_index": 0,
                "guard_return": 0.0,
                "branch_returns": {"0": 0.0, "1": first, "2": -first / 2.0},
            }
        )
    return tensors, metadata


def test_fixed_recipe_registration_and_offline_gates_are_exact():
    assert FIXED_RECIPE["member_count"] == 5
    assert FIXED_RECIPE["member_seeds"] == [
        2026082901,
        2026082902,
        2026082903,
        2026082904,
        2026082905,
    ]
    assert FIXED_RECIPE["confidence_scale"] == pytest.approx(1.0)
    assert FIXED_RECIPE["advantage_threshold"] == pytest.approx(0.5)
    assert FIXED_OFFLINE_GATES == {
        "minimum_intervention_count": 30,
        "minimum_intervention_precision": pytest.approx(0.65),
        "minimum_mean_selected_true_advantage": pytest.approx(
            0.12269661575555801
        ),
        "maximum_mean_policy_regret": pytest.approx(3.2472479343414307),
        "illegal_action_count_zero": True,
        "forbidden_action_selection_count_zero": True,
    }
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
        del payload["inputs"]["items_json"]
    elif mutation == "overlap":
        payload["inputs"]["evaluation_corpus"]["sha256"] = payload["inputs"][
            "train_corpus"
        ]["sha256"]
    elif mutation == "recipe":
        payload["recipe"]["confidence_scale"] = 2.0
    elif mutation == "gate":
        payload["offline_gates"]["minimum_intervention_count"] = 1
    elif mutation == "authority":
        payload["authority"]["gameplay"] = True
    else:
        payload["output_dir"] = "D:/outside"
    with pytest.raises(ValueError):
        validate_registration_payload(payload)


def test_bootstrap_indices_are_deterministic_distinct_and_source_bounded():
    first = deterministic_bootstrap_indices(64, FIXED_RECIPE["member_seeds"])
    second = deterministic_bootstrap_indices(64, FIXED_RECIPE["member_seeds"])

    assert len(first) == 5
    assert all(torch.equal(a.indices, b.indices) for a, b in zip(first, second))
    assert len({sample.sha256 for sample in first}) == 5
    assert all(sample.indices.shape == (64,) for sample in first)
    assert all(int(sample.indices.min()) >= 0 for sample in first)
    assert all(int(sample.indices.max()) < 64 for sample in first)


def test_fit_is_deterministic_finite_and_freezes_shared_parent():
    parent = create_dqn_v2(device="cpu", **METADATA)
    tensors, metadata = _corpus_fixture()
    recipe = copy.deepcopy(FIXED_RECIPE)
    recipe["updates"] = 8
    recipe["batch_size"] = 8
    parent_before = state_dict_sha256(parent.state_dict())

    first, first_fit = fit_ensemble(
        parent=parent,
        metadata=METADATA,
        tensors=tensors,
        corpus_metadata=metadata,
        recipe=recipe,
    )
    second, second_fit = fit_ensemble(
        parent=parent,
        metadata=METADATA,
        tensors=tensors,
        corpus_metadata=metadata,
        recipe=recipe,
    )

    assert first_fit == second_fit
    assert len(first_fit["members"]) == 5
    assert all(member["all_objectives_finite"] for member in first_fit["members"])
    assert [sample.sha256 for sample in first.bootstrap_samples] == [
        sample.sha256 for sample in second.bootstrap_samples
    ]
    assert state_dict_sha256(parent.state_dict()) == parent_before
    assert all(parameter.grad is None for parameter in first.parent.parameters())


def test_offline_gates_require_precision_coverage_value_regret_and_safety():
    passing = {
        "selection": {
            "intervention_count": 30,
            "intervention_precision": 0.65,
            "mean_selected_true_advantage": 0.13,
            "illegal_action_count": 0,
            "forbidden_action_selection_count": 0,
        },
        "ranking": {"mean_policy_regret": 3.2},
    }
    result = apply_offline_gates(passing)
    assert result["all_conditions_passed"] is True
    assert result["decision"] == "offline_passed_enter_fresh_lightspeed_gate"

    for path, value in (
        (("selection", "intervention_count"), 29),
        (("selection", "intervention_precision"), 0.64),
        (("selection", "mean_selected_true_advantage"), 0.12),
        (("ranking", "mean_policy_regret"), 3.25),
        (("selection", "illegal_action_count"), 1),
        (("selection", "forbidden_action_selection_count"), 1),
    ):
        failing = copy.deepcopy(passing)
        failing[path[0]][path[1]] = value
        assert apply_offline_gates(failing)["all_conditions_passed"] is False
