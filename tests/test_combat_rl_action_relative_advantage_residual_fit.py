from __future__ import annotations

import copy

import pytest
import torch

import analysis_scripts.combat_rl_action_relative_advantage_residual_fit as fit_runner
from analysis_scripts.combat_rl_action_relative_advantage_residual_fit import (
    FIXED_RECIPE,
    REGISTERED_AUTHORITY,
    SOURCE_SNAPSHOT_PATHS,
    evaluate_corpus,
    fit_residual,
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
        },
        "recipe": copy.deepcopy(FIXED_RECIPE),
        "output_dir": str(fit_runner.REPORTS_ROOT / "action_relative_fit_fixture"),
        "authority": copy.deepcopy(REGISTERED_AUTHORITY),
    }


def test_fixed_recipe_and_registration_are_exact():
    assert FIXED_RECIPE == {
        "architecture": "frozen_parent_action_relative_advantage_residual",
        "hidden_dim": 64,
        "advantage_threshold": pytest.approx(0.5),
        "target_clip": pytest.approx(20.0),
        "target_scale": pytest.approx(10.0),
        "optimizer": "adam",
        "learning_rate": pytest.approx(0.001),
        "updates": 1024,
        "batch_size": 256,
        "smooth_l1_beta": pytest.approx(0.1),
        "training_seed": 2026082823,
        "device": "cpu",
        "forbidden_action_indices": [90],
    }
    assert validate_registration_payload(_registration()) == _registration()


@pytest.mark.parametrize(
    "mutation",
    ["root", "source", "runner", "inputs", "overlap", "recipe", "authority", "output"],
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
        payload["recipe"]["updates"] += 1
    elif mutation == "authority":
        payload["authority"]["gameplay"] = True
    else:
        payload["output_dir"] = "D:/outside"
    with pytest.raises(ValueError):
        validate_registration_payload(payload)


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


def test_fit_is_deterministic_finite_and_freezes_parent():
    parent = create_dqn_v2(device="cpu", **METADATA)
    tensors, metadata = _corpus_fixture()
    recipe = copy.deepcopy(FIXED_RECIPE)
    recipe["updates"] = 16
    recipe["batch_size"] = 8
    parent_before = state_dict_sha256(parent.state_dict())

    first, first_fit = fit_residual(
        parent=parent,
        metadata=METADATA,
        tensors=tensors,
        corpus_metadata=metadata,
        recipe=recipe,
    )
    second, second_fit = fit_residual(
        parent=parent,
        metadata=METADATA,
        tensors=tensors,
        corpus_metadata=metadata,
        recipe=recipe,
    )

    assert first_fit == second_fit
    assert first_fit["update_count"] == 16
    assert first_fit["all_objectives_finite"] is True
    assert state_dict_sha256(first.scorer.state_dict()) == state_dict_sha256(
        second.scorer.state_dict()
    )
    assert state_dict_sha256(parent.state_dict()) == parent_before
    assert all(parameter.grad is None for parameter in first.parent.parameters())

    evaluation = evaluate_corpus(first, tensors, metadata, forbidden_action_indices=())
    assert evaluation["row_count"] == 16
    assert evaluation["alternative_count"] == 32
    assert evaluation["selection"]["illegal_action_count"] == 0
    assert evaluation["selection"]["forbidden_action_selection_count"] == 0
    assert set(evaluation["offline_integrity_conditions"]) == {
        "intervention_count_positive",
        "mean_selected_true_advantage_non_negative",
        "illegal_action_count_zero",
        "forbidden_action_selection_count_zero",
    }
