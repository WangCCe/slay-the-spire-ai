from __future__ import annotations

import copy
from pathlib import Path

import pytest
import torch

import analysis_scripts.combat_rl_guard_advantage_residual_fit as residual_fit
from analysis_scripts.combat_rl_guard_advantage_residual_fit import (
    FIXED_RECIPE,
    REGISTERED_AUTHORITY,
    SOURCE_SNAPSHOT_PATHS,
    _alternative_masks,
    classification_metrics,
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
    runner = residual_fit.REPO_ROOT / SOURCE_SNAPSHOT_PATHS[0]
    return {
        "schema_version": 1,
        "experiment_id": residual_fit.EXPERIMENT_ID,
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
        },
        "recipe": copy.deepcopy(FIXED_RECIPE),
        "output_dir": str(residual_fit.REPORTS_ROOT / "guard_residual_fit_fixture"),
        "authority": copy.deepcopy(REGISTERED_AUTHORITY),
    }


def test_fixed_recipe_and_registration_are_exact():
    assert FIXED_RECIPE == {
        "architecture": "frozen_parent_post_guard_abstaining_residual",
        "hidden_dim": 64,
        "gate_threshold": pytest.approx(0.5),
        "optimizer": "adam",
        "learning_rate": pytest.approx(0.001),
        "updates": 512,
        "positive_rows_per_batch": 32,
        "negative_rows_per_batch": 32,
        "training_seed": 2026082822,
        "device": "cpu",
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


def test_alternative_masks_use_only_canonical_branch_representatives():
    action_masks = torch.tensor([[True, True, True, True], [True, True, True, False]])
    guards = torch.tensor([1, 0])
    metadata = [
        {"branch_returns": {"1": 0.0, "2": 1.0}},
        {"branch_returns": {"0": 0.0, "1": 1.0}},
    ]
    alternatives = _alternative_masks(metadata, action_masks, guards)
    assert alternatives.tolist() == [
        [False, False, True, False],
        [False, True, False, False],
    ]


def _fit_fixture() -> tuple[torch.nn.Module, dict[str, torch.Tensor], dict]:
    torch.manual_seed(3)
    parent = create_dqn_v2(device="cpu", **METADATA)
    row_count = 40
    positive = torch.tensor([True, False] * (row_count // 2))
    action_masks = torch.ones((row_count, 4), dtype=torch.bool)
    guards = torch.zeros(row_count, dtype=torch.long)
    alternatives = torch.zeros_like(action_masks)
    alternatives[:, 1] = True
    alternatives[:, 2] = True
    targets = torch.where(positive, torch.ones(row_count, dtype=torch.long), guards)
    corpus = {
        "continuous": torch.randn(row_count, 4),
        "card_ids": torch.randint(0, 5, (row_count, 1)),
        "potion_ids": torch.randint(0, 4, (row_count, 1)),
        "relic_ids": torch.randint(0, 3, (row_count, 1)),
        "action_masks": action_masks,
        "guard_actions": guards,
        "alternative_masks": alternatives,
        "target_actions": targets,
        "advantages": positive.float(),
        "positive": positive,
    }
    recipe = copy.deepcopy(FIXED_RECIPE)
    recipe["updates"] = 8
    recipe["positive_rows_per_batch"] = 4
    recipe["negative_rows_per_batch"] = 4
    return parent, corpus, recipe


def test_fit_is_deterministic_finite_and_freezes_parent():
    parent, corpus, recipe = _fit_fixture()
    parent_before = state_dict_sha256(parent.state_dict())
    first, first_report = fit_residual(
        parent=parent, metadata=METADATA, corpus=corpus, recipe=recipe
    )
    second, second_report = fit_residual(
        parent=parent, metadata=METADATA, corpus=corpus, recipe=recipe
    )
    assert first_report == second_report
    assert first_report["update_count"] == 8
    assert first_report["all_objectives_finite"] is True
    assert state_dict_sha256(first.gate.state_dict()) == state_dict_sha256(
        second.gate.state_dict()
    )
    assert state_dict_sha256(first.action_head.state_dict()) == state_dict_sha256(
        second.action_head.state_dict()
    )
    assert state_dict_sha256(parent.state_dict()) == parent_before
    assert all(parameter.grad is None for parameter in first.parent.parameters())
    metrics = classification_metrics(first, corpus)
    assert metrics["row_count"] == 40
    assert metrics["illegal_action_count"] == 0
    assert metrics["threshold"] == pytest.approx(0.5)
