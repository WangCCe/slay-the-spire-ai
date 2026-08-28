from __future__ import annotations

import copy
from pathlib import Path
import subprocess
import sys

import torch

from analysis_scripts.combat_rl_provenance_aware_successor import (
    _fit_candidate,
    _validate_parity_checkpoint,
)
from analysis_scripts.combat_rl_stratified_provenance_successor import (
    OPTIMIZER_STEPS,
    _eligibility,
)
from spirecomm.ai.rl.v2.network import create_dqn_v2


REPO_ROOT = Path(__file__).resolve().parents[1]


def _checkpoint(count: int = 12) -> dict:
    metadata = {
        "network_type": "standard",
        "continuous_dim": 4,
        "card_vocab": 4,
        "potion_vocab": 4,
        "relic_vocab": 4,
        "action_dim": 3,
        "card_slots": 1,
        "potion_slots": 1,
        "relic_slots": 1,
        "rl_space_version": "v2",
    }
    torch.manual_seed(11)
    network = create_dqn_v2(
        device="cpu",
        **{key: value for key, value in metadata.items() if key != "rl_space_version"},
    )
    state = copy.deepcopy(network.state_dict())
    continuous = torch.arange(count * 4).reshape(count, 4).float() / 20.0
    item_ids = torch.ones((count, 1), dtype=torch.long)
    masks = torch.ones((count, 3), dtype=torch.bool)
    dones = torch.zeros(count, dtype=torch.bool)
    dones[2::3] = True
    replay = {
        "schema_version": 2,
        "buffer_size": count,
        "continuous_dim": 4,
        "action_dim": 3,
        "card_slots": 1,
        "potion_slots": 1,
        "relic_slots": 1,
        "transition_count": count,
        "source_transition_count": count,
        "truncated": False,
        "continuous": continuous,
        "card_ids": item_ids,
        "potion_ids": item_ids,
        "relic_ids": item_ids,
        "action_masks": masks,
        "actions": torch.tensor([0, 1, 2] * (count // 3), dtype=torch.long),
        "rewards": torch.linspace(-1.0, 2.0, count),
        "dones": dones,
        "next_continuous": continuous.flip(0),
        "next_card_ids": item_ids.flip(0),
        "next_potion_ids": item_ids.flip(0),
        "next_relic_ids": item_ids.flip(0),
        "next_action_masks": masks.flip(0),
        "anchor_to_executed_action": torch.tensor(
            [False, True, True] * (count // 3), dtype=torch.bool
        ),
    }
    return {
        "checkpoint_schema_version": 2,
        "checkpoint_kind": "training",
        "metadata": metadata,
        "online_network_state_dict": state,
        "target_network_state_dict": copy.deepcopy(state),
        "optimizer_state_dict": {"state": {}},
        "replay_buffer_state_dict": replay,
    }


def _validation() -> dict:
    return {
        "parent_smooth_l1": 4.0,
        "candidate_smooth_l1": 3.5,
        "action_disagreement_share": 0.08,
        "positive_energy_end_turn_count_delta": 1,
        "strata": {
            "direct": {
                "transition_count": 20,
                "action_disagreement_share": 0.05,
                "parent_anchor_label_agreement": 1.0,
                "candidate_anchor_label_agreement": 0.95,
            },
            "override": {
                "transition_count": 80,
                "action_disagreement_share": 0.0875,
                "parent_anchor_label_agreement": 0.25,
                "candidate_anchor_label_agreement": 0.36,
            },
        },
    }


def _training() -> dict:
    return {
        "optimizer_update_count": 64,
        "sampled_override_count": {"maximum": 110.0},
        "all_objective_values_finite": True,
    }


def test_fixed_recipe_executes_exactly_64_optimizer_updates():
    assert OPTIMIZER_STEPS == 64
    checkpoint = _checkpoint()
    metadata, replay, _ = _validate_parity_checkpoint(
        checkpoint, expected_transition_count=12
    )

    _, training = _fit_candidate(
        metadata=metadata,
        parent_state=checkpoint["online_network_state_dict"],
        target_state=checkpoint["target_network_state_dict"],
        replay=replay,
        train_indices=torch.arange(9),
        learning_rate=1e-4,
        batch_size=4,
        anchor_weight=1.0,
        optimizer_steps=OPTIMIZER_STEPS,
        seed=2026082806,
    )

    assert training["optimizer_update_count"] == 64
    assert training["all_objective_values_finite"] is True
    assert training["sampled_override_count"]["maximum"] > 0


def test_isolated_direct_entrypoint_bootstraps_repo_root():
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            str(
                REPO_ROOT
                / "analysis_scripts"
                / "combat_rl_stratified_provenance_successor.py"
            ),
            "--help",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "--training-checkpoint" in result.stdout


def test_stratified_eligibility_passes_fixed_direct_and_override_gates():
    checks = _eligibility(
        validation=_validation(),
        training=_training(),
        candidate_round_trip_exact=True,
    )

    assert checks["validation_provenance_strata_nonempty"] is True
    assert checks["overall_parent_disagreement_at_least_material_floor"] is True
    assert checks["direct_parent_disagreement_at_most_ceiling"] is True
    assert checks["override_executed_label_agreement_uplift_at_least_floor"] is True
    assert checks["all_conditions_passed"] is True


def test_stratified_eligibility_fails_direct_drift_or_override_uplift():
    direct_drift = _validation()
    direct_drift["strata"]["direct"]["action_disagreement_share"] = 0.11
    direct_checks = _eligibility(
        validation=direct_drift,
        training=_training(),
        candidate_round_trip_exact=True,
    )
    assert direct_checks["direct_parent_disagreement_at_most_ceiling"] is False
    assert direct_checks["all_conditions_passed"] is False

    weak_override = _validation()
    weak_override["strata"]["override"][
        "candidate_anchor_label_agreement"
    ] = 0.349
    override_checks = _eligibility(
        validation=weak_override,
        training=_training(),
        candidate_round_trip_exact=True,
    )
    assert (
        override_checks[
            "override_executed_label_agreement_uplift_at_least_floor"
        ]
        is False
    )
    assert override_checks["all_conditions_passed"] is False


def test_stratified_eligibility_requires_both_validation_strata_and_exact_budget():
    missing_direct = _validation()
    missing_direct["strata"]["direct"]["transition_count"] = 0
    missing_direct["strata"]["direct"]["action_disagreement_share"] = None
    missing_checks = _eligibility(
        validation=missing_direct,
        training=_training(),
        candidate_round_trip_exact=True,
    )
    assert missing_checks["validation_provenance_strata_nonempty"] is False
    assert missing_checks["all_conditions_passed"] is False

    wrong_budget = _training()
    wrong_budget["optimizer_update_count"] = 63
    budget_checks = _eligibility(
        validation=_validation(),
        training=wrong_budget,
        candidate_round_trip_exact=True,
    )
    assert budget_checks["optimizer_budget_exact"] is False
    assert budget_checks["all_conditions_passed"] is False
