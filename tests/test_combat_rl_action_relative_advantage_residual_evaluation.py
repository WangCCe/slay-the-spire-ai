from __future__ import annotations

import copy

import pytest
import torch

import analysis_scripts.combat_rl_action_relative_advantage_residual_evaluation as evaluation
from analysis_scripts.combat_rl_action_relative_advantage_residual_evaluation import (
    FIXED_POLICY_GATES,
    FIXED_RECIPE,
    REGISTERED_AUTHORITY,
    SOURCE_SNAPSHOT_PATHS,
    ActionRelativeEvaluationAdapter,
    apply_policy_gates,
    validate_registration_payload,
)
from spirecomm.ai.rl.v2.action_relative_advantage_residual import (
    ActionRelativeAdvantageConfig,
    ActionRelativeAdvantageResidual,
)
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
    runner = evaluation.REPO_ROOT / SOURCE_SNAPSHOT_PATHS[0]
    inputs = {
        "native_module": {"path": "D:/fixture/native.pyd", "sha256": "1" * 64},
        "items_json": {"path": "D:/fixture/items.json", "sha256": "2" * 64},
        "parent_checkpoint": {"path": "D:/fixture/parent.pth", "sha256": "3" * 64},
        "residual_artifact": {"path": "D:/fixture/residual.pth", "sha256": "4" * 64},
        "residual_fit_report": {"path": "D:/fixture/report.json", "sha256": "5" * 64},
        "train_corpus": {"path": "D:/fixture/train.pt", "sha256": "6" * 64},
        "evaluation_corpus": {"path": "D:/fixture/eval.pt", "sha256": "7" * 64},
    }
    return {
        "schema_version": 1,
        "experiment_id": evaluation.EXPERIMENT_ID,
        "source_commit": "a" * 40,
        "runner": {"path": str(runner), "sha256": "b" * 64},
        "source_files": {
            path: ("b" * 64 if path == SOURCE_SNAPSHOT_PATHS[0] else "c" * 64)
            for path in SOURCE_SNAPSHOT_PATHS
        },
        "inputs": inputs,
        "recipe": copy.deepcopy(FIXED_RECIPE),
        "policy_gates": copy.deepcopy(FIXED_POLICY_GATES),
        "output_dir": str(evaluation.REPORTS_ROOT / "action_relative_eval_fixture"),
        "authority": copy.deepcopy(REGISTERED_AUTHORITY),
    }


def test_registration_and_fresh_recipe_are_exact():
    assert FIXED_RECIPE["seed_first"] == 266000
    assert FIXED_RECIPE["seed_last"] == 266255
    assert FIXED_RECIPE["battle_indices"] == [0, 3, 6, 9]
    assert FIXED_RECIPE["forbidden_action_indices"] == [90]
    assert FIXED_POLICY_GATES == {
        "candidate_only_victories_at_least_control_only": True,
        "mean_reward_delta_non_negative": True,
        "mean_player_hp_delta_non_negative": True,
        "excluded_nonterminal_profile_count_zero": True,
        "residual_intervention_count_positive": True,
        "forbidden_action_intervention_count_zero": True,
    }
    assert validate_registration_payload(_registration()) == _registration()


@pytest.mark.parametrize(
    "mutation", ["root", "source", "runner", "inputs", "recipe", "gates", "authority", "output"]
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
        del payload["inputs"]["native_module"]
    elif mutation == "recipe":
        payload["recipe"]["seed_last"] += 1
    elif mutation == "gates":
        payload["policy_gates"]["mean_reward_delta_non_negative"] = False
    elif mutation == "authority":
        payload["authority"]["gameplay"] = True
    else:
        payload["output_dir"] = "D:/outside"
    with pytest.raises(ValueError):
        validate_registration_payload(payload)


def test_adapter_exposes_predicted_advantage_and_preserves_constraint_mask():
    parent = create_dqn_v2(device="cpu", **METADATA)
    residual = ActionRelativeAdvantageResidual(
        parent,
        METADATA,
        ActionRelativeAdvantageConfig(hidden_dim=8),
    )
    with torch.no_grad():
        for parameter in residual.scorer.parameters():
            parameter.zero_()
        residual.scorer[-1].bias.fill_(0.1)
    adapter = ActionRelativeEvaluationAdapter(residual)
    result = adapter.select_actions(
        torch.randn(1, 4),
        torch.tensor([[1]]),
        torch.tensor([[1]]),
        torch.tensor([[1]]),
        torch.tensor([[True, True, True, False]]),
        torch.tensor([0]),
        torch.tensor([[False, False, True, False]]),
    )

    assert result.actions.tolist() == [2]
    assert result.residual_actions.tolist() == [2]
    assert result.gate_open.tolist() == [True]
    assert result.gate_probabilities.tolist() == pytest.approx([1.0])


def test_policy_gates_require_outcomes_support_intervention_and_constraint():
    paired = {
        "aggregate": {
            "candidate_only_victories": 3,
            "control_only_victories": 2,
            "mean_reward_delta": 0.1,
            "mean_player_hp_delta": 0.2,
            "excluded_nonterminal_profile_count": 0,
        }
    }
    candidate = {
        "aggregate": {
            "residual_intervention_count": 5,
            "residual_forbidden_action_intervention_count": 0,
        }
    }
    passed = apply_policy_gates(paired, candidate)
    assert passed["all_conditions_passed"] is True

    candidate["aggregate"]["residual_forbidden_action_intervention_count"] = 1
    failed = apply_policy_gates(paired, candidate)
    assert failed["all_conditions_passed"] is False
    assert failed["decision"] == "action_relative_residual_failed_close_without_sweep"
