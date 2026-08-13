from __future__ import annotations

import copy
from pathlib import Path

import pytest
import torch

from analysis_scripts import noncombat_card_acceptance_empirical_successor_runtime as runtime
from analysis_scripts import noncombat_card_counterfactual_ranking_training as ranking
from analysis_scripts import noncombat_large_corpus_state_conditioned_card_ranking as runner


def _candidates() -> tuple[dict[str, object], ...]:
    return (
        {
            "action_id": "card_reward:take:0:0:a",
            "available": True,
            "category": "card_reward",
            "kind": "take",
            "label": "A",
            "raw": {"id": "A"},
        },
        {
            "action_id": "card_reward:take:0:1:b",
            "available": True,
            "category": "card_reward",
            "kind": "take",
            "label": "B",
            "raw": {"id": "B"},
        },
        {
            "action_id": "card_reward:take:0:2:c",
            "available": True,
            "category": "card_reward",
            "kind": "take",
            "label": "C",
            "raw": {"id": "C"},
        },
        {
            "action_id": "card_reward:skip:0",
            "available": True,
            "category": "card_reward",
            "kind": "skip",
            "label": "skip",
            "raw": {"reward_index": 0},
        },
    )


def _row(
    seed: int,
    decision_index: int = 0,
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
        decision_index=decision_index,
        source_sha256=f"{seed * 100 + decision_index:064x}",
        state_features=state,
        candidate_features=candidates,
        candidates=copy.deepcopy(_candidates()),
        action_returns=returns,
    )


def test_informative_batches_are_sorted_complete_and_omit_equal_rows():
    rows = (
        _row(1, 3),
        _row(1, 4),
        _row(2, 1, returns=(0.2, 0.2, 0.2, 0.2)),
        _row(3, 2),
        _row(4, 0),
        _row(5, 0),
    )

    batches = runner.deterministic_batches(rows, batch_size=2)

    assert [[(row.seed, row.decision_index) for row in batch] for batch in batches] == [
        [(1, 3), (1, 4)],
        [(3, 2), (4, 0)],
        [(5, 0)],
    ]


def test_one_epoch_rejects_optimizer_with_partial_card_head_ownership():
    model = runtime.build_matched_bootstrap()
    optimizer = torch.optim.Adam(
        [model.candidate.card_policy.family_head.scorer.weight],
        **runtime._REGISTERED_ADAM_OPTIONS,
    )

    with pytest.raises(runner.StateConditionedRankingBlocked, match="ownership"):
        runner.train_one_epoch(model, optimizer, (_row(1),))


def test_one_epoch_changes_only_candidate_card_heads_and_is_finite():
    model = runtime.build_matched_bootstrap()
    optimizer = runtime.build_candidate_card_optimizer(model)
    card_before = runner.pilot.encode_candidate_card_policy(model)
    guard_before = ranking._guard_bytes(model)

    diagnostic = runner.train_one_epoch(
        model,
        optimizer,
        tuple(_row(seed) for seed in range(1, 4)),
        batch_size=2,
    )

    assert diagnostic["batch_count"] == 2
    assert diagnostic["minimum_batch_loss"] > 0.0
    assert runner.pilot.encode_candidate_card_policy(model) != card_before
    assert ranking._guard_bytes(model) == guard_before


def test_model_envelope_round_trips_complete_bootstrap_exactly():
    entry = runtime.build_matched_bootstrap()

    encoded = runner.encode_model(entry)
    restored = runner.restore_model(encoded)

    assert runner.encode_model(restored) == encoded
    assert runtime.encode_paired_bootstrap(restored) == runtime.encode_paired_bootstrap(
        entry
    )


def test_checkpoint_training_is_deterministic_from_identical_entry_bytes():
    entry_bytes = runner.encode_model(runtime.build_matched_bootstrap())
    rows = tuple(_row(seed) for seed in range(1, 5))

    first_scores, first_losses, first_model = runner.train_checkpoints(
        entry_bytes,
        fit_rows=rows,
        score_partition=rows,
        epoch_checkpoints=(1, 2),
        batch_size=2,
    )
    second_scores, second_losses, second_model = runner.train_checkpoints(
        entry_bytes,
        fit_rows=rows,
        score_partition=rows,
        epoch_checkpoints=(1, 2),
        batch_size=2,
    )

    assert first_scores == second_scores
    assert first_losses == second_losses
    assert runner.encode_model(first_model) == runner.encode_model(second_model)


def test_crossfit_stops_when_no_fixed_epoch_improves(monkeypatch):
    rows = tuple(_row(seed) for seed in range(10, 20))
    entry_bytes = runner.encode_model(runtime.build_matched_bootstrap())
    entry = runner.restore_model(entry_bytes)
    base_scores = runner.score_rows(entry, rows)

    def train_without_change(
        _entry_bytes,
        *,
        fit_rows,
        score_partition,
        epoch_checkpoints=runner.EPOCH_CHECKPOINTS,
        batch_size=runner.BATCH_SIZE,
    ):
        del fit_rows, batch_size
        scores = {
            epoch: {
                row.source_sha256: base_scores[row.source_sha256]
                for row in score_partition
            }
            for epoch in epoch_checkpoints
        }
        return scores, [], runner.restore_model(_entry_bytes)

    monkeypatch.setattr(runner, "train_checkpoints", train_without_change)

    selection = runner.crossfit_select_epochs(entry_bytes, rows)

    assert selection["selected_epochs"] is None
    assert len(selection["folds"]) == runner.FOLD_COUNT
    assert all(
        candidate["checks"]["mean_regret_decreased"] is False
        for candidate in selection["candidates"]
    )


def test_train_only_stop_writes_no_model_and_never_loads_development(
    tmp_path: Path, monkeypatch
):
    rows = tuple(_row(seed) for seed in range(1, 3))
    entry = runtime.build_matched_bootstrap()
    output = tmp_path / "output"
    monkeypatch.setattr(runner, "_source_bindings", lambda _root, _commit: {})
    monkeypatch.setattr(
        runner.residual,
        "_load_train_inputs",
        lambda _root: (rows[:1], entry, {"existing_train": {}}),
    )
    monkeypatch.setattr(
        runner.residual,
        "_load_rare_train_inputs",
        lambda _root: (rows[1:], {"rare_train": {}}),
    )
    monkeypatch.setattr(runner, "_validate_train_support", tuple)
    base_scores = runner.score_rows(entry, rows)
    base_metrics = runner.uplift.evaluate_scores(rows, base_scores)
    monkeypatch.setattr(
        runner,
        "crossfit_select_epochs",
        lambda _entry, _rows: {
            "base_metrics": base_metrics,
            "candidates": [],
            "crossfit_scores": {
                epoch: base_scores for epoch in runner.EPOCH_CHECKPOINTS
            },
            "fold_losses": [],
            "folds": ((1,), (2,), (), (), ()),
            "selected_epochs": None,
            "selected_checks": None,
        },
    )
    monkeypatch.setattr(
        runner.residual,
        "_load_development_inputs",
        lambda *_args: pytest.fail("development must remain unread"),
    )

    report = runner.execute(
        repo_root=tmp_path,
        source_commit="a" * 40,
        corpus_root=tmp_path / "existing",
        rare_corpus_root=tmp_path / "rare",
        output_dir=output,
    )

    assert report["development_accessed"] is False
    assert report["train_only_stop"] is True
    assert not (output / "trained_model.json").exists()
