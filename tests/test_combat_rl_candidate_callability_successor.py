import subprocess
import sys
from pathlib import Path

import pytest
import torch

from analysis_scripts.combat_rl_candidate_callability_successor import (
    ANCHOR_WEIGHT,
    BATCH_SIZE,
    DEVELOPMENT_AUTHORITY,
    DIRECT_MARGIN_CAP,
    DIRECT_MARGIN_WEIGHT,
    GAMMA,
    LEARNING_RATE,
    OPTIMIZER_STEPS,
    SPLIT_SEED,
    TRAINING_SEED,
    _callability_eligibility,
    _fit_callability_candidate,
    _validate_optimizer_batch_provenance,
    _variable_bootstrap_targets,
    build_candidate_decision_spans,
)
from spirecomm.ai.rl.v2.network import create_dqn_v2


REPO_ROOT = Path(__file__).resolve().parents[1]


def _replay(*, proposals, actions=None, rewards=None, dones=None):
    count = len(proposals)
    if actions is None:
        actions = [max(value, 0) for value in proposals]
    if rewards is None:
        rewards = [float(index + 1) for index in range(count)]
    if dones is None:
        dones = [False] * (count - 1) + [True]
    action_dim = 3
    continuous = torch.arange(count, dtype=torch.float32).reshape(count, 1)
    card_ids = torch.arange(count, dtype=torch.int64).reshape(count, 1)
    potion_ids = card_ids + 10
    relic_ids = card_ids + 20
    action_masks = torch.ones((count, action_dim), dtype=torch.bool)
    next_continuous = torch.zeros_like(continuous)
    next_card_ids = torch.zeros_like(card_ids)
    next_potion_ids = torch.zeros_like(potion_ids)
    next_relic_ids = torch.zeros_like(relic_ids)
    next_action_masks = torch.zeros_like(action_masks)
    for index in range(count - 1):
        if dones[index]:
            continue
        next_continuous[index] = continuous[index + 1]
        next_card_ids[index] = card_ids[index + 1]
        next_potion_ids[index] = potion_ids[index + 1]
        next_relic_ids[index] = relic_ids[index + 1]
        next_action_masks[index] = action_masks[index + 1]
    anchors = [
        True if proposal == -1 else proposal != action
        for proposal, action in zip(proposals, actions)
    ]
    return {
        "continuous": continuous,
        "card_ids": card_ids,
        "potion_ids": potion_ids,
        "relic_ids": relic_ids,
        "actions": torch.tensor(actions, dtype=torch.int64),
        "rewards": torch.tensor(rewards, dtype=torch.float32),
        "next_continuous": next_continuous,
        "next_card_ids": next_card_ids,
        "next_potion_ids": next_potion_ids,
        "next_relic_ids": next_relic_ids,
        "dones": torch.tensor(dones, dtype=torch.bool),
        "action_masks": action_masks,
        "next_action_masks": next_action_masks,
        "anchor_to_executed_action": torch.tensor(anchors, dtype=torch.bool),
        "proposed_action_indices": torch.tensor(proposals, dtype=torch.int64),
    }


def test_adjacent_proposals_form_one_step_decision_spans():
    spans, telemetry = build_candidate_decision_spans(
        _replay(proposals=[0, 1]),
        gamma=0.9,
    )

    assert spans["source_start_indices"].tolist() == [0, 1]
    assert spans["source_end_indices"].tolist() == [0, 1]
    assert spans["span_lengths"].tolist() == [1, 1]
    assert spans["rewards"].tolist() == pytest.approx([1.0, 2.0])
    assert spans["bootstrap_discounts"].tolist() == pytest.approx([0.9, 0.0])
    assert spans["next_continuous"][0].tolist() == [1.0]
    assert spans["dones"].tolist() == [False, True]
    assert telemetry["direct_decision_count"] == 2
    assert telemetry["changed_decision_count"] == 0


def test_takeover_rows_are_folded_into_preceding_decision_span():
    spans, telemetry = build_candidate_decision_spans(
        _replay(
            proposals=[0, -1, -1, 1],
            actions=[0, 2, 1, 2],
        ),
        gamma=0.9,
    )

    assert spans["source_start_indices"].tolist() == [0, 3]
    assert spans["source_end_indices"].tolist() == [2, 3]
    assert spans["span_lengths"].tolist() == [3, 1]
    assert spans["rewards"].tolist() == pytest.approx([5.23, 4.0])
    assert spans["bootstrap_discounts"].tolist() == pytest.approx([0.9**3, 0.0])
    assert spans["anchor_to_executed_action"].tolist() == [False, True]
    assert telemetry["attached_no_proposal_count"] == 2
    assert telemetry["direct_decision_count"] == 1
    assert telemetry["changed_decision_count"] == 1


def test_terminal_takeover_span_accumulates_without_bootstrap():
    spans, telemetry = build_candidate_decision_spans(
        _replay(proposals=[0, -1], actions=[0, 2]),
        gamma=0.9,
    )

    assert spans["source_start_indices"].tolist() == [0]
    assert spans["source_end_indices"].tolist() == [1]
    assert spans["rewards"].tolist() == pytest.approx([2.8])
    assert spans["bootstrap_discounts"].tolist() == [0.0]
    assert spans["dones"].tolist() == [True]
    assert telemetry["attached_no_proposal_count"] == 1


def test_no_proposal_prefix_is_reported_but_not_attributed():
    spans, telemetry = build_candidate_decision_spans(
        _replay(proposals=[-1, -1, 0], actions=[2, 1, 0]),
        gamma=0.9,
    )

    assert spans["source_start_indices"].tolist() == [2]
    assert telemetry["uncontrolled_prefix_count"] == 2
    assert telemetry["attached_no_proposal_count"] == 0
    assert telemetry["source_row_reconciliation_count"] == 3


def test_terminal_combat_partition_prevents_cross_group_bootstrap():
    spans, telemetry = build_candidate_decision_spans(
        _replay(
            proposals=[0, -1, 1],
            actions=[0, 2, 1],
            dones=[False, True, True],
        ),
        gamma=0.9,
    )

    assert spans["combat_group_indices"].tolist() == [0, 1]
    assert spans["source_end_indices"].tolist() == [1, 2]
    assert spans["dones"].tolist() == [True, True]
    assert spans["bootstrap_discounts"].tolist() == [0.0, 0.0]
    assert telemetry["combat_group_count"] == 2


def test_unknown_proposal_identity_blocks_span_construction():
    replay = _replay(proposals=[0, -1])
    replay["proposed_action_indices"][1] = -2

    with pytest.raises(ValueError, match="unknown proposal identity"):
        build_candidate_decision_spans(replay, gamma=0.9)


def test_nonterminal_replay_tail_blocks_span_construction():
    replay = _replay(proposals=[0, -1], dones=[False, False])

    with pytest.raises(ValueError, match="terminal-delimited"):
        build_candidate_decision_spans(replay, gamma=0.9)


def test_registered_callability_recipe_is_exact_and_bounded():
    assert OPTIMIZER_STEPS == 64
    assert BATCH_SIZE == 128
    assert LEARNING_RATE == pytest.approx(1e-4)
    assert GAMMA == pytest.approx(0.99)
    assert ANCHOR_WEIGHT == pytest.approx(1.0)
    assert DIRECT_MARGIN_WEIGHT == pytest.approx(1.0)
    assert DIRECT_MARGIN_CAP == pytest.approx(0.1)
    assert SPLIT_SEED == 2026082807
    assert TRAINING_SEED == 2026082808


def test_variable_bootstrap_targets_use_per_span_discount():
    targets = _variable_bootstrap_targets(
        rewards=torch.tensor([1.0, 2.0]),
        bootstrap_discounts=torch.tensor([0.81, 0.0]),
        next_bootstrap=torch.tensor([10.0, 50.0]),
    )

    assert targets.tolist() == pytest.approx([9.1, 2.0])


def test_optimizer_batch_gate_requires_only_both_callable_strata():
    spans = {
        "proposed_action_indices": torch.tensor([0, 1, 2], dtype=torch.int64),
        "anchor_to_executed_action": torch.tensor(
            [False, True, False], dtype=torch.bool
        ),
    }
    telemetry = _validate_optimizer_batch_provenance(
        spans,
        (torch.tensor([0, 1]), torch.tensor([1, 2])),
    )
    assert telemetry["batch_count"] == 2
    assert telemetry["minimum_direct_count"] == 1
    assert telemetry["minimum_changed_count"] == 1
    assert telemetry["ineligible_sample_count"] == 0

    ineligible = dict(spans)
    ineligible["proposed_action_indices"] = torch.tensor(
        [0, -1, 2], dtype=torch.int64
    )
    with pytest.raises(ValueError, match="candidate-callable"):
        _validate_optimizer_batch_provenance(
            ineligible,
            (torch.tensor([0, 1]),),
        )

    with pytest.raises(ValueError, match="both direct and changed"):
        _validate_optimizer_batch_provenance(
            spans,
            (torch.tensor([0, 2]),),
        )


def test_callability_eligibility_uses_fixed_stratified_gates():
    validation = {
        "parent_smooth_l1": 4.0,
        "candidate_smooth_l1": 3.5,
        "action_disagreement_share": 0.20,
        "positive_energy_end_turn_count_delta": 1,
        "strata": {
            "direct": {
                "transition_count": 20,
                "action_disagreement_share": 0.10,
            },
            "changed_proposal": {
                "transition_count": 20,
                "parent_anchor_label_agreement": 0.20,
                "candidate_anchor_label_agreement": 0.35,
            },
        },
    }
    training = {
        "optimizer_update_count": 64,
        "all_objective_values_finite": True,
        "batch_provenance": {
            "minimum_direct_count": 1,
            "minimum_changed_count": 1,
            "ineligible_sample_count": 0,
        },
    }
    passed = _callability_eligibility(
        validation=validation,
        training=training,
        candidate_round_trip_exact=True,
        callability_complete=True,
    )
    assert passed["all_conditions_passed"] is True

    drift = _callability_eligibility(
        validation={
            **validation,
            "strata": {
                **validation["strata"],
                "direct": {
                    "transition_count": 20,
                    "action_disagreement_share": 0.11,
                },
            },
        },
        training=training,
        candidate_round_trip_exact=True,
        callability_complete=True,
    )
    assert drift["direct_parent_disagreement_at_most_ceiling"] is False
    assert drift["all_conditions_passed"] is False


def test_development_authority_never_grants_downstream_use():
    assert DEVELOPMENT_AUTHORITY == {
        "candidate": False,
        "communication_mod": False,
        "fresh_holdout": False,
        "gameplay": False,
        "model_fitting": True,
        "policy_quality": False,
        "production_checkpoint_writing": False,
        "promotion": False,
        "qualification": False,
        "training": True,
    }


def test_fixed_fitter_runs_only_balanced_callable_batches():
    count = 128
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
    }
    torch.manual_seed(11)
    parent = create_dqn_v2(device="cpu", **metadata)
    parent_state = {
        name: value.detach().clone() for name, value in parent.state_dict().items()
    }
    continuous = torch.linspace(0.0, 1.0, count * 4).reshape(count, 4)
    ids = (torch.arange(count) % 4).reshape(count, 1)
    masks = torch.ones((count, 3), dtype=torch.bool)
    changed = torch.tensor([False] * 64 + [True] * 64, dtype=torch.bool)
    spans = {
        "continuous": continuous,
        "card_ids": ids,
        "potion_ids": ids,
        "relic_ids": ids,
        "actions": torch.where(changed, torch.ones(count, dtype=torch.long), 0),
        "rewards": torch.linspace(-1.0, 1.0, count),
        "next_continuous": torch.zeros_like(continuous),
        "next_card_ids": torch.zeros_like(ids),
        "next_potion_ids": torch.zeros_like(ids),
        "next_relic_ids": torch.zeros_like(ids),
        "dones": torch.ones(count, dtype=torch.bool),
        "action_masks": masks,
        "next_action_masks": torch.zeros_like(masks),
        "anchor_to_executed_action": changed,
        "proposed_action_indices": torch.zeros(count, dtype=torch.long),
        "bootstrap_discounts": torch.zeros(count),
    }

    candidate, telemetry = _fit_callability_candidate(
        metadata=metadata,
        parent_state=parent_state,
        target_state=parent_state,
        spans=spans,
        train_indices=torch.arange(count),
        optimizer_steps=2,
        batch_size=128,
        seed=13,
    )

    assert telemetry["optimizer_update_count"] == 2
    assert telemetry["all_objective_values_finite"] is True
    assert telemetry["batch_provenance"]["minimum_direct_count"] == 64
    assert telemetry["batch_provenance"]["minimum_changed_count"] == 64
    assert any(
        not torch.equal(candidate[name], parent_state[name]) for name in candidate
    )


def test_isolated_direct_entrypoint_bootstraps_repo_root():
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            str(
                REPO_ROOT
                / "analysis_scripts"
                / "combat_rl_candidate_callability_successor.py"
            ),
            "--help",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "--registration-sha256" in result.stdout
