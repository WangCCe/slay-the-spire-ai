from __future__ import annotations

import copy
from types import SimpleNamespace

import pytest
import torch

from analysis_scripts import noncombat_card_acceptance_empirical_successor_runtime as runtime
from analysis_scripts import noncombat_card_counterfactual_ranking_training as ranking
from analysis_scripts import noncombat_family_preserving_conditional_card_ranking as runner


def _candidates() -> tuple[dict[str, object], ...]:
    return (
        {"action_id": "take-a", "available": True, "category": "card_reward", "kind": "take", "label": "A", "raw": {"id": "A"}},
        {"action_id": "take-b", "available": True, "category": "card_reward", "kind": "take", "label": "B", "raw": {"id": "B"}},
        {"action_id": "take-c", "available": True, "category": "card_reward", "kind": "take", "label": "C", "raw": {"id": "C"}},
        {"action_id": "skip", "available": True, "category": "card_reward", "kind": "skip", "label": "skip", "raw": {"reward_index": 0}},
    )


def _row(
    seed: int,
    *,
    returns: tuple[float, float, float, float] = (0.4, 0.2, 0.1, 0.0),
) -> ranking.CounterfactualRankingRow:
    state = torch.zeros(runtime.HASH_DIM, dtype=torch.float32)
    state[seed % 32] = 1.0
    candidates = torch.zeros((4, runtime.HASH_DIM), dtype=torch.float32)
    candidates[0, 32] = 2.0
    candidates[1, 32] = 1.0
    candidates[2, 32] = -1.0
    candidates[3, 33] = 1.0
    return ranking.CounterfactualRankingRow(
        seed=seed,
        decision_index=0,
        source_sha256=f"{seed:064x}",
        state_features=state,
        candidate_features=candidates,
        candidates=copy.deepcopy(_candidates()),
        action_returns=returns,
    )


def test_optimizer_owns_exactly_conditional_scorer_weight():
    model = runtime.build_matched_bootstrap()

    optimizer = runner.conditional_scorer_optimizer(model)
    owned = runtime._validated_registered_adam(optimizer)

    assert owned == (model.candidate.card_policy.conditional_ranker.scorer.weight,)
    assert sum(parameter.numel() for parameter in owned) == 64
    assert all(
        not parameter.requires_grad
        for parameter in model.candidate.card_policy.parameters()
        if parameter is not owned[0]
    )


def test_take_loss_and_update_ignore_skip_return():
    first = runtime.build_matched_bootstrap()
    second = runtime.restore_paired_bootstrap(runtime.encode_paired_bootstrap(first))
    first_row = _row(1, returns=(0.4, 0.2, 0.1, 0.0))
    second_row = _row(1, returns=(0.4, 0.2, 0.1, 100.0))
    first_loss = float(runner.take_pairwise_loss(first, (first_row,)).item())
    second_loss = float(runner.take_pairwise_loss(second, (second_row,)).item())

    runner.train_one_epoch(
        first, runner.conditional_scorer_optimizer(first), (first_row,)
    )
    runner.train_one_epoch(
        second, runner.conditional_scorer_optimizer(second), (second_row,)
    )

    assert first_loss == second_loss
    assert torch.equal(
        first.candidate.card_policy.conditional_ranker.scorer.weight,
        second.candidate.card_policy.conditional_ranker.scorer.weight,
    )


def test_one_epoch_preserves_every_nonowned_model_byte():
    model = runtime.build_matched_bootstrap()
    frozen_before = runner._frozen_model_bytes(model)

    diagnostic = runner.train_one_epoch(
        model,
        runner.conditional_scorer_optimizer(model),
        tuple(_row(seed) for seed in range(1, 4)),
        batch_size=2,
    )

    assert diagnostic["batch_count"] == 2
    assert runner._frozen_model_bytes(model) == frozen_before


def test_policy_metrics_use_two_stage_selection_not_joint_argmax(monkeypatch):
    row = _row(1)
    output = SimpleNamespace(
        family_logits=torch.tensor([2.0, 3.0], dtype=torch.float32),
        conditional_logits=torch.tensor(
            [0.01, 0.0, -0.01, 100.0], dtype=torch.float32
        ),
    )
    monkeypatch.setattr(runner.runtime, "forward_card_policy", lambda *_a, **_k: output)

    metrics = runner.evaluate_policy(object(), (row,))

    # Joint argmax is skip because take mass is split; two-stage greedily chooses take.
    assert metrics["predictions"][0]["selected_family"] == "take"
    assert metrics["predictions"][0]["selected_action_id"] == "take-a"
    assert metrics["mean_top_action_regret"] == 0.0


def test_checkpoint_training_is_deterministic():
    entry = runner.encode_model(runtime.build_matched_bootstrap())
    rows = tuple(_row(seed) for seed in range(1, 5))

    first_predictions, first_losses, first_model = runner.train_checkpoints(
        entry,
        fit_rows=rows,
        score_partition=rows,
        epoch_checkpoints=(1, 2),
        batch_size=2,
    )
    second_predictions, second_losses, second_model = runner.train_checkpoints(
        entry,
        fit_rows=rows,
        score_partition=rows,
        epoch_checkpoints=(1, 2),
        batch_size=2,
    )

    assert first_predictions == second_predictions
    assert first_losses == second_losses
    assert runner.encode_model(first_model) == runner.encode_model(second_model)


def test_comparison_gate_requires_family_preservation():
    entry = {
        "maximum_top_action_regret": 0.4,
        "mean_top_action_regret": 0.2,
        "take_weighted_pairwise_accuracy": 0.5,
        "unique_best_accuracy": 0.3,
    }
    candidate = {
        "maximum_top_action_regret": 0.3,
        "mean_top_action_regret": 0.1,
        "take_weighted_pairwise_accuracy": 0.6,
        "unique_best_accuracy": 0.4,
    }

    checks = runner._comparison_checks(
        entry,
        candidate,
        {"corrected_actions": 4, "family_flips": 1, "worsened_actions": 2},
        minimum_corrected_actions=4,
    )

    assert checks["family_choices_preserved"] is False
    assert all(value for key, value in checks.items() if key != "family_choices_preserved")


def test_crossfit_stops_when_fixed_epochs_do_not_improve(monkeypatch):
    rows = tuple(_row(seed) for seed in range(10, 20))
    entry = runner.encode_model(runtime.build_matched_bootstrap())
    entry_model = runner.restore_model(entry)

    def unchanged(
        _entry,
        *,
        fit_rows,
        score_partition,
        epoch_checkpoints=runner.EPOCH_CHECKPOINTS,
        batch_size=runner.BATCH_SIZE,
    ):
        del fit_rows, batch_size
        predictions = runner.policy_predictions(entry_model, score_partition)
        return {epoch: predictions for epoch in epoch_checkpoints}, [], entry_model

    monkeypatch.setattr(runner, "train_checkpoints", unchanged)

    result = runner.crossfit_select_epochs(entry, rows)

    assert result["selected_epochs"] is None
    assert all(
        candidate["checks"]["mean_regret_improved"] is False
        for candidate in result["candidates"]
    )
