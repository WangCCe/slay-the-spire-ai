from __future__ import annotations

import pytest
import torch

from analysis_scripts import noncombat_card_acceptance_empirical_successor_runtime as successor
from analysis_scripts import noncombat_card_only_baseline_clipping_ablation as ablation
from analysis_scripts import noncombat_card_only_behavior_sensitivity_training as training
from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot as pilot
from analysis_scripts.noncombat_state_conditioned_policy_input import HASH_DIM


def _candidates() -> tuple[dict[str, str], ...]:
    return (
        {"action_id": "skip", "kind": "skip"},
        {"action_id": "take-a", "kind": "take"},
        {"action_id": "take-b", "kind": "take"},
    )


def _episode(bootstrap, *, seed: int = 7, position: int = 0, reward: float = 0.25):
    state = torch.zeros(HASH_DIM, dtype=torch.float32)
    state[position % HASH_DIM] = 1.0
    candidate_features = torch.zeros((3, HASH_DIM), dtype=torch.float32)
    candidate_features[0, 1] = 1.0
    candidate_features[1, 2] = 1.0
    candidate_features[2, 3] = 1.0
    output = successor.forward_card_policy(
        bootstrap,
        arm="candidate",
        state_features=state,
        candidate_features=candidate_features,
        candidates=_candidates(),
    )
    terms = successor.build_card_acceptance_policy_terms(
        output.family_logits,
        output.conditional_logits,
        _candidates(),
        "take-b",
        category="card_reward",
    )
    decision = successor.ArmRolloutDecision(
        arm="candidate",
        category="card_reward",
        decision_id=f"candidate:seed-{seed}:decision-0",
        decision_index=0,
        selected_action_id="take-b",
        state_features=state,
        card_terms=terms,
        diagnostic={},
        candidate_features=candidate_features,
        candidates=_candidates(),
    )
    return successor.ArmEpisodeRollout(
        arm="candidate",
        seed=seed,
        trajectory_id=f"candidate:seed-{seed}",
        decisions=(decision,),
        transitions=({},),
        rewards=(reward,),
        final_snapshot={"terminal": True},
        floor_progress=reward,
        terminal_victory=0,
        unsupported_reason=None,
    )


def _baseline(seed: int = 7):
    decision_id = f"candidate:seed-{seed}:decision-0"
    state = torch.zeros(HASH_DIM, dtype=torch.float32)
    state[0] = 1.0
    decision = successor.ArmBaselineDecision(
        arm="candidate",
        category="card_reward",
        decision_id=decision_id,
        decision_index=0,
        raw_return=0.25,
        reward=0.25,
        seed=seed,
        state_features=successor.fold_baseline_state_features(state),
        trajectory_id=f"candidate:seed-{seed}",
    )
    prediction = successor.ArmBaselinePrediction(
        decision_id=decision_id,
        fold_id="fold-0",
        trajectory_id=f"candidate:seed-{seed}",
        unclipped=-0.20,
        clipped=0.0,
        was_clipped=True,
        preclip_little_endian_hex="0" * 16,
        feature_sha256="f" * 64,
    )
    return successor.ArmCrossFittedBaseline(
        arm="candidate",
        decisions=(decision,),
        fold_trajectories={"fold-0": (f"candidate:seed-{seed}",)},
        models=(),
        predictions=(prediction,),
        advantage_batch=None,  # Not consumed by the branch reconstruction helper.
    )


def _clone_bootstrap(value):
    return successor.restore_paired_bootstrap(successor.encode_paired_bootstrap(value))


def _fake_evaluation(bootstrap, _rows):
    take = float(
        next(bootstrap.candidate.card_policy.family_head.parameters())
        .reshape(-1)[0]
        .item()
    ) >= 0.0
    return {
        "action_agreement": 0.0,
        "action_correct": 0,
        "family_agreement": 0.0,
        "family_correct": 0,
        "non_take_rate": 0.0 if take else 1.0,
        "predictions": [
            {
                "decision_index": 0,
                "predicted_action_id": "take" if take else "skip",
                "predicted_family": "take" if take else "skip",
                "seed": 7,
                "target_action_id": "skip",
                "target_family": "skip",
            }
        ],
        "row_count": 1,
        "take_rate": 1.0 if take else 0.0,
    }


def _behavior_runtime(monkeypatch):
    monkeypatch.setattr(pilot, "evaluate_card_warm_start", _fake_evaluation)
    monkeypatch.setattr(pilot, "_probe_sha256", lambda _rows: "p" * 64)
    monkeypatch.setattr(
        pilot,
        "classify_card_probe",
        lambda metrics: {
            "non_take_rate": metrics["non_take_rate"],
            "stop": False,
            "take_rate": metrics["take_rate"],
        },
    )
    bootstrap = successor.build_matched_bootstrap()
    optimizer = successor.build_candidate_card_optimizer(bootstrap)
    for _ in range(training.FIRST_CHUNK_INDEX):
        for parameter in optimizer.param_groups[0]["params"]:
            parameter.grad = torch.zeros_like(parameter)
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
    return training.initialize_behavior_sensitivity_runtime(
        bootstrap=bootstrap,
        candidate_optimizer=optimizer,
        probe_rows=(object(),),
    )


def _shared_episodes(bootstrap):
    return tuple(
        _episode(
            bootstrap,
            seed=100 + position,
            position=position,
            reward=0.1 + 0.01 * (position % 11),
        )
        for position in range(64)
    )


def test_rebuilt_rows_change_only_clipped_baseline_arithmetic() -> None:
    bootstrap = successor.build_matched_bootstrap()
    episode = _episode(bootstrap)
    baseline = _baseline()

    clipped = ablation.rebuild_candidate_card_rows(
        bootstrap, (episode,), baseline=baseline, prediction_mode="clipped"
    )
    unclipped = ablation.rebuild_candidate_card_rows(
        bootstrap, (episode,), baseline=baseline, prediction_mode="unclipped"
    )

    assert clipped[0][0].selected_action_id == unclipped[0][0].selected_action_id
    assert clipped[0][1] == pytest.approx(0.25)
    assert unclipped[0][1] == pytest.approx(0.45)


def test_rebuilt_terms_are_owned_by_the_requested_branch() -> None:
    source = successor.build_matched_bootstrap()
    branch = _clone_bootstrap(source)
    rows = ablation.rebuild_candidate_card_rows(
        branch, (_episode(source),), baseline=_baseline(), prediction_mode="unclipped"
    )
    objective = successor.build_arm_card_reward_objective(rows)
    named = successor._arm_named_trainable_parameters(branch, arm="candidate")
    optimizer = successor.build_candidate_card_optimizer(branch)

    prepared = successor._prepare_arm_optimizer_step(
        optimizer,
        objective,
        parameters=tuple(parameter for _, parameter in named),
        parameter_names=tuple(name for name, _ in named),
        reconstruct_components=False,
    )

    assert prepared.preclip_global_norm > 0.0


def test_rebuilt_terms_reject_another_branch_optimizer() -> None:
    source = successor.build_matched_bootstrap()
    owner = _clone_bootstrap(source)
    wrong = _clone_bootstrap(source)
    rows = ablation.rebuild_candidate_card_rows(
        owner, (_episode(source),), baseline=_baseline(), prediction_mode="unclipped"
    )
    objective = successor.build_arm_card_reward_objective(rows)
    wrong_named = successor._arm_named_trainable_parameters(wrong, arm="candidate")

    with pytest.raises(successor.SuccessorRuntimeError, match="gradient is missing"):
        successor._prepare_arm_optimizer_step(
            successor.build_candidate_card_optimizer(wrong),
            objective,
            parameters=tuple(parameter for _, parameter in wrong_named),
            parameter_names=tuple(name for name, _ in wrong_named),
            reconstruct_components=False,
        )


def test_shared_ablation_advances_both_branches_once(monkeypatch) -> None:
    clipped = _behavior_runtime(monkeypatch)
    entry = training.encode_behavior_sensitivity_checkpoint(clipped)
    unclipped = training.restore_behavior_sensitivity_checkpoint(
        entry, probe_rows=clipped.probe_rows, entry_model=clipped.entry_model
    )

    completed = ablation.apply_shared_trajectory_ablation(
        clipped,
        unclipped,
        _shared_episodes(clipped.bootstrap),
        entry_checkpoint=entry,
    )

    assert completed.attempted_seeds == tuple(range(100, 164))
    assert completed.supported_seeds == completed.attempted_seeds
    assert completed.clipped_branch.next_chunk_index == 5
    assert completed.unclipped_branch.next_chunk_index == 5
    assert completed.clipped_branch.environment_accesses == 64
    assert completed.unclipped_branch.environment_accesses == 64
    assert completed.telemetry["baseline"]["card_prediction_count"] == 64
    assert -1.0 <= completed.telemetry["gradient_comparison"]["applied_cosine"] <= 1.0


def test_second_commit_failure_restores_both_complete_entry_states(
    monkeypatch,
) -> None:
    clipped = _behavior_runtime(monkeypatch)
    entry = training.encode_behavior_sensitivity_checkpoint(clipped)
    unclipped = training.restore_behavior_sensitivity_checkpoint(
        entry, probe_rows=clipped.probe_rows, entry_model=clipped.entry_model
    )
    original_commit = successor._commit_prepared_arm_step
    calls = 0

    def fail_second_commit(optimizer, prepared):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise successor.SuccessorRuntimeError("fixture second commit failure")
        return original_commit(optimizer, prepared)

    monkeypatch.setattr(successor, "_commit_prepared_arm_step", fail_second_commit)

    with pytest.raises(
        ablation.BaselineClippingAblationBlocked, match="second commit failure"
    ):
        ablation.apply_shared_trajectory_ablation(
            clipped,
            unclipped,
            _shared_episodes(clipped.bootstrap),
            entry_checkpoint=entry,
        )

    assert training.encode_behavior_sensitivity_checkpoint(clipped) == entry
    assert training.encode_behavior_sensitivity_checkpoint(unclipped) == entry
