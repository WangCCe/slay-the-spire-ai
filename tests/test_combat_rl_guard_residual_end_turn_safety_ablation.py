from __future__ import annotations

import copy

import pytest

import analysis_scripts.combat_rl_guard_residual_end_turn_safety_ablation as ablation
from analysis_scripts.combat_rl_guard_residual_end_turn_safety_ablation import (
    FIXED_ABLATION_GATES,
    FIXED_RECIPE,
    REGISTERED_AUTHORITY,
    SOURCE_SNAPSHOT_PATHS,
    apply_ablation_gates,
    validate_registration_payload,
)


def _registration() -> dict:
    runner = ablation.REPO_ROOT / SOURCE_SNAPSHOT_PATHS[0]
    inputs = {
        name: {"path": f"D:/fixture/{name}.bin", "sha256": str(index + 1) * 64}
        for index, name in enumerate(
            (
                "native_module",
                "items_json",
                "parent_checkpoint",
                "residual_artifact",
                "train_corpus",
                "evaluation_corpus",
            )
        )
    }
    return {
        "schema_version": 1,
        "experiment_id": ablation.EXPERIMENT_ID,
        "source_commit": "a" * 40,
        "runner": {"path": str(runner), "sha256": "b" * 64},
        "source_files": {
            path: ("b" * 64 if path == SOURCE_SNAPSHOT_PATHS[0] else "c" * 64)
            for path in SOURCE_SNAPSHOT_PATHS
        },
        "inputs": inputs,
        "recipe": copy.deepcopy(FIXED_RECIPE),
        "ablation_gates": copy.deepcopy(FIXED_ABLATION_GATES),
        "output_dir": str(ablation.REPORTS_ROOT / "end_turn_ablation_fixture"),
        "authority": copy.deepcopy(REGISTERED_AUTHORITY),
    }


def test_fixed_registration_recipe_gates_and_authority_are_exact():
    assert FIXED_RECIPE["seed_first"] == 265000
    assert FIXED_RECIPE["seed_last"] == 265255
    assert FIXED_RECIPE["masked_forbidden_residual_action_indices"] == [90]
    assert validate_registration_payload(_registration()) == _registration()


@pytest.mark.parametrize("section", ["recipe", "ablation_gates", "authority"])
def test_registration_rejects_execution_mutation(section):
    payload = _registration()
    if section == "recipe":
        payload[section]["seed_last"] += 1
    elif section == "ablation_gates":
        payload[section]["masked_end_turn_intervention_count_zero"] = False
    else:
        payload[section]["gameplay"] = True
    with pytest.raises(ValueError, match=section.replace("_", " ")):
        validate_registration_payload(payload)


def _arm(*, end_turn: int, forbidden: int, interventions: int) -> dict:
    return {
        "aggregate": {
            "residual_end_turn_intervention_count": end_turn,
            "residual_forbidden_action_intervention_count": forbidden,
            "residual_intervention_count": interventions,
        }
    }


def _pair(
    *,
    candidate_only: int,
    control_only: int,
    reward: float,
    hp: float,
    excluded: int = 0,
) -> dict:
    return {
        "aggregate": {
            "candidate_only_victories": candidate_only,
            "control_only_victories": control_only,
            "mean_reward_delta": reward,
            "mean_player_hp_delta": hp,
            "excluded_nonterminal_profile_count": excluded,
        }
    }


def test_ablation_gate_requires_control_safety_direct_improvement_and_treatment():
    passed = apply_ablation_gates(
        unrestricted=_arm(end_turn=3, forbidden=0, interventions=8),
        masked=_arm(end_turn=0, forbidden=0, interventions=5),
        control_to_masked=_pair(
            candidate_only=2, control_only=1, reward=0.2, hp=0.1
        ),
        unrestricted_to_masked=_pair(
            candidate_only=2, control_only=1, reward=0.3, hp=0.2
        ),
    )
    assert passed["all_conditions_passed"] is True
    assert passed["decision"].startswith("end_turn_mask_simulator_promising")

    failed = apply_ablation_gates(
        unrestricted=_arm(end_turn=3, forbidden=0, interventions=8),
        masked=_arm(end_turn=0, forbidden=0, interventions=5),
        control_to_masked=_pair(
            candidate_only=2, control_only=1, reward=-0.01, hp=0.1
        ),
        unrestricted_to_masked=_pair(
            candidate_only=2, control_only=1, reward=0.3, hp=0.2
        ),
    )
    assert failed["all_conditions_passed"] is False
    assert failed["decision"] == (
        "end_turn_safety_hypothesis_failed_close_without_second_ablation"
    )


@pytest.mark.parametrize(
    "mutation",
    ["no_treatment", "mask_failure", "direct_nonterminal", "direct_hp"],
)
def test_ablation_gate_rejects_each_mechanism_failure(mutation):
    unrestricted = _arm(end_turn=3, forbidden=0, interventions=8)
    masked = _arm(end_turn=0, forbidden=0, interventions=5)
    control_pair = _pair(candidate_only=2, control_only=1, reward=0.2, hp=0.1)
    direct_pair = _pair(candidate_only=2, control_only=1, reward=0.3, hp=0.2)
    if mutation == "no_treatment":
        unrestricted["aggregate"]["residual_end_turn_intervention_count"] = 0
    elif mutation == "mask_failure":
        masked["aggregate"]["residual_forbidden_action_intervention_count"] = 1
    elif mutation == "direct_nonterminal":
        direct_pair["aggregate"]["excluded_nonterminal_profile_count"] = 1
    else:
        direct_pair["aggregate"]["mean_player_hp_delta"] = -0.01
    result = apply_ablation_gates(
        unrestricted=unrestricted,
        masked=masked,
        control_to_masked=control_pair,
        unrestricted_to_masked=direct_pair,
    )
    assert result["all_conditions_passed"] is False
