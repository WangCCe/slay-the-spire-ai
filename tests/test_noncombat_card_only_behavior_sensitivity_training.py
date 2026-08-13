from types import SimpleNamespace

import pytest
import torch

from analysis_scripts import noncombat_card_acceptance_empirical_successor_runtime as successor
from analysis_scripts import noncombat_card_only_behavior_sensitivity_training as training
from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot as pilot


def _probe_rows():
    return (SimpleNamespace(),)


def _evaluation(bootstrap, _rows):
    family_weight = next(bootstrap.candidate.card_policy.family_head.parameters())
    take = float(family_weight.reshape(-1)[0].item()) >= 0.0
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


def _runtime(monkeypatch):
    bootstrap = successor.build_matched_bootstrap()
    optimizer = successor.build_candidate_card_optimizer(bootstrap)
    for _ in range(training.FIRST_CHUNK_INDEX):
        for parameter in optimizer.param_groups[0]["params"]:
            parameter.grad = torch.zeros_like(parameter)
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
    monkeypatch.setattr(pilot, "evaluate_card_warm_start", _evaluation)
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
    return training.initialize_behavior_sensitivity_runtime(
        bootstrap=bootstrap,
        candidate_optimizer=optimizer,
        probe_rows=_probe_rows(),
    )


def _episodes(*, censored=0, unknown=False):
    result = []
    for seed in range(64):
        reason = None
        if seed < censored:
            reason = "unsupported_shop_courier_restock_semantics"
        if unknown and seed == 0:
            reason = "unknown_support_blocker"
        decision = successor.ArmRolloutDecision(
            arm="candidate",
            decision_id=f"candidate:seed-{seed}:decision-0",
            decision_index=0,
            category="card_reward",
            selected_action_id="take",
            state_features=torch.zeros(128, dtype=torch.float32),
            card_terms=object(),
            diagnostic={"selected_family": "take"},
        )
        result.append(
            successor.ArmEpisodeRollout(
                arm="candidate",
                seed=seed,
                trajectory_id=f"candidate:seed-{seed}",
                decisions=(decision,),
                transitions=({},),
                rewards=(0.0,),
                final_snapshot={"terminal": reason is None},
                floor_progress=0.25,
                terminal_victory=0,
                unsupported_reason=reason,
            )
        )
    return tuple(result)


def test_candidate_only_checkpoint_round_trips_from_four_step_entry(monkeypatch):
    value = _runtime(monkeypatch)

    checkpoint = training.encode_behavior_sensitivity_checkpoint(value)
    restored = training.restore_behavior_sensitivity_checkpoint(
        checkpoint,
        probe_rows=value.probe_rows,
        entry_model=value.entry_model,
    )

    assert training.encode_behavior_sensitivity_checkpoint(restored) == checkpoint
    assert restored.next_chunk_index == 4
    assert restored.environment_accesses == 0


def test_candidate_only_chunk_censors_declared_blocker_and_charges_64_accesses(
    monkeypatch,
):
    value = _runtime(monkeypatch)

    def fake_update(_bootstrap, optimizer, episodes):
        assert len(episodes) == 63
        for parameter in optimizer.param_groups[0]["params"]:
            parameter.grad = torch.full_like(parameter, 1e-6)
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
        return SimpleNamespace(seeds=tuple(episode.seed for episode in episodes))

    monkeypatch.setattr(
        successor,
        "apply_candidate_cross_fitted_chunk_update_exploratory",
        fake_update,
    )

    completed = training.complete_candidate_only_chunk(
        value,
        _episodes(censored=1),
        chunk_index=4,
    )

    assert completed.seeds == tuple(range(1, 64))
    assert completed.runtime.next_chunk_index == 5
    assert completed.runtime.environment_accesses == 64
    assert completed.censored_trajectories[0]["seed"] == 0


def test_candidate_only_unknown_blocker_restores_complete_entry(monkeypatch):
    value = _runtime(monkeypatch)
    before = training.encode_behavior_sensitivity_checkpoint(value)

    with pytest.raises(training.BehaviorSensitivityBlocked, match="unknown blocker"):
        training.complete_candidate_only_chunk(
            value,
            _episodes(unknown=True),
            chunk_index=4,
        )

    assert training.encode_behavior_sensitivity_checkpoint(value) == before


def test_candidate_only_update_failure_restores_model_optimizer_and_coordinates(
    monkeypatch,
):
    value = _runtime(monkeypatch)
    before = training.encode_behavior_sensitivity_checkpoint(value)

    def failing_update(bootstrap, optimizer, _episodes):
        for parameter in optimizer.param_groups[0]["params"]:
            parameter.grad = torch.full_like(parameter, 1e-6)
        optimizer.step()
        raise successor.SuccessorRuntimeError("fixture gradient failure")

    monkeypatch.setattr(
        successor,
        "apply_candidate_cross_fitted_chunk_update_exploratory",
        failing_update,
    )

    with pytest.raises(training.BehaviorSensitivityBlocked, match="gradient failure"):
        training.complete_candidate_only_chunk(
            value,
            _episodes(),
            chunk_index=4,
        )

    assert training.encode_behavior_sensitivity_checkpoint(value) == before


def test_candidate_only_collection_calls_one_environment_per_seed(monkeypatch):
    value = _runtime(monkeypatch)
    before = training.encode_behavior_sensitivity_checkpoint(value)
    calls = []
    episodes = _episodes()

    def fake_rollout(_bootstrap, *, environment_factory, seed, **_kwargs):
        environment_factory(seed)
        return episodes[seed]

    monkeypatch.setattr(
        successor,
        "rollout_candidate_card_only_native_baseline_training_episode",
        fake_rollout,
    )
    monkeypatch.setattr(
        training,
        "complete_candidate_only_chunk",
        lambda working, values, *, chunk_index: SimpleNamespace(
            runtime=working,
            values=values,
            chunk_index=chunk_index,
        ),
    )

    completed = training.collect_and_complete_candidate_only_chunk(
        value,
        environment_factory=lambda seed: calls.append(seed),
        seeds=tuple(range(64)),
        chunk_index=4,
        deadline=1.0,
        clock=lambda: 0.0,
    )

    assert calls == list(range(64))
    assert len(completed.values) == 64
    assert training.encode_behavior_sensitivity_checkpoint(value) == before
