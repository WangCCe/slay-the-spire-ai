from __future__ import annotations

import copy
from pathlib import Path

import pytest
import torch

from analysis_scripts import noncombat_card_acceptance_empirical_successor_runtime as runtime
from analysis_scripts import noncombat_card_counterfactual_ranking_training as ranking
from analysis_scripts.noncombat_simulator_adapter import (
    ADAPTER_API_VERSION,
    SOURCE_TYPE,
    STATE_SCHEMA_VERSION,
    build_transition,
)


def _provenance() -> dict[str, object]:
    return {
        "adapter_commit": "adapter",
        "adapter_source_sha256": "adapter-source",
        "build": {
            "adapter_api_version": ADAPTER_API_VERSION,
            "compiler": "test",
            "cpp_standard": 201703,
            "python": "3.10",
        },
        "module_sha256": "module",
        "simulator_commit": "simulator",
        "simulator_source_sha256": "simulator-source",
        "submodules": {"json": "json", "pybind11": "pybind11"},
    }


def _candidate(category: str, action_id: str, kind: str) -> dict[str, object]:
    return {
        "action_id": action_id,
        "available": True,
        "category": category,
        "kind": kind,
        "label": action_id,
        "raw": {"action_id": action_id},
    }


class _PartitionEnvironment:
    def __init__(
        self,
        seed: int,
        *,
        stage: int = 0,
        card: str | None = None,
        censor_seed: int | None = None,
    ) -> None:
        self.seed = seed
        self.stage = stage
        self.card = card
        self.censor_seed = censor_seed

    def snapshot(self) -> dict[str, object]:
        terminal = self.stage == 2
        floor = {None: 0, "take-a": 2, "take-b": 4, "take-c": 1, "skip": 0}[
            self.card
        ] if terminal else 0
        return {
            "adapter_api_version": ADAPTER_API_VERSION,
            "baseline_control": {"history": [], "policy_id": "test-native"},
            "category": None if terminal else ("card_reward" if self.stage == 0 else "route"),
            "decision_count": self.stage,
            "schema_version": STATE_SCHEMA_VERSION,
            "source_type": SOURCE_TYPE,
            "state": {
                "floor": floor,
                "outcome": "player_loss" if terminal else "undecided",
                "seed": str(self.seed),
            },
            "terminal": terminal,
        }

    def legal_actions(self) -> list[dict[str, object]]:
        if self.stage == 0:
            return [
                _candidate("card_reward", "take-a", "take"),
                _candidate("card_reward", "take-b", "take"),
                _candidate("card_reward", "take-c", "take"),
                _candidate("card_reward", "skip", "skip"),
            ]
        if self.stage == 1:
            return [_candidate("route", "continue", "map_node")]
        return []

    def clone(self):
        return type(self)(
            self.seed,
            stage=self.stage,
            card=self.card,
            censor_seed=self.censor_seed,
        )

    def step(self, action_id: str) -> dict[str, object]:
        before = self.snapshot()
        candidates = self.legal_actions()
        if action_id not in {candidate["action_id"] for candidate in candidates}:
            raise RuntimeError("illegal action")
        if self.stage == 0:
            self.card = action_id
            self.stage = 1
        else:
            self.stage = 2
        return build_transition(
            before=before,
            candidates=candidates,
            selected_action_id=action_id,
            after=self.snapshot(),
            provenance=_provenance(),
        )

    def step_native_baseline(self) -> dict[str, object]:
        if self.seed == self.censor_seed and self.stage == 1:
            raise RuntimeError("unsupported_shop_courier_restock_semantics")
        return self.step("take-a" if self.stage == 0 else "continue")


def test_partition_collects_complete_rows_and_stops_before_partial_source():
    partition = ranking.collect_counterfactual_partition(
        _PartitionEnvironment,
        name="train",
        seeds=(1, 2),
        max_action_branches=8,
        max_censored_seeds=0,
        max_card_states_per_seed=1,
    )

    assert len(partition.rows) == 2
    assert partition.action_branches == 8
    assert all(row.action_returns[1] > row.action_returns[0] for row in partition.rows)
    assert partition.censored_seeds == ()

    bounded = ranking.collect_counterfactual_partition(
        _PartitionEnvironment,
        name="train",
        seeds=(1,),
        max_action_branches=3,
        max_censored_seeds=0,
    )
    assert bounded.rows == ()
    assert bounded.action_branches == 0
    assert bounded.budget_exhausted is True


def test_partition_censors_only_registered_blocker_without_replacement():
    partition = ranking.collect_counterfactual_partition(
        lambda seed: _PartitionEnvironment(seed, censor_seed=2),
        name="train",
        seeds=(1, 2, 3),
        max_action_branches=12,
        max_censored_seeds=1,
        max_card_states_per_seed=1,
    )

    assert [row.seed for row in partition.rows] == [1, 3]
    assert partition.censored_seeds == (
        {"reason": "unsupported_shop_courier_restock_semantics", "seed": 2},
    )

    with pytest.raises(ranking.CounterfactualRankingBlocked, match="censor limit"):
        ranking.collect_counterfactual_partition(
            lambda seed: _PartitionEnvironment(seed, censor_seed=2),
            name="train",
            seeds=(2,),
            max_action_branches=4,
            max_censored_seeds=0,
            max_card_states_per_seed=1,
        )


def _ranking_candidates() -> tuple[dict[str, object], ...]:
    return (
        _candidate("card_reward", "take-a", "take"),
        _candidate("card_reward", "take-b", "take"),
        _candidate("card_reward", "take-c", "take"),
        _candidate("card_reward", "skip", "skip"),
    )


def _ranking_row(seed: int, source: int, returns=(0.4, 0.2, 0.1, 0.0)):
    state = torch.zeros(1024, dtype=torch.float32)
    state[seed % 16] = 1.0
    candidates = torch.zeros((4, 1024), dtype=torch.float32)
    candidates[0, 32] = 2.0
    candidates[1, 32] = 1.0
    candidates[2, 32] = -1.0
    candidates[3, 33] = 1.0
    return ranking.CounterfactualRankingRow(
        seed=seed,
        decision_index=0,
        source_sha256=f"{source:064x}",
        state_features=state,
        candidate_features=candidates,
        candidates=copy.deepcopy(_ranking_candidates()),
        action_returns=tuple(returns),
    )


def test_pairwise_training_decreases_loss_and_never_uses_holdout_in_fit():
    first = runtime.build_matched_bootstrap()
    encoded = runtime.encode_paired_bootstrap(first)
    second = runtime.restore_paired_bootstrap(encoded)
    train_rows = tuple(_ranking_row(seed, seed) for seed in range(10, 14))
    holdout_a = (_ranking_row(20, 20), _ranking_row(21, 21))
    holdout_b = (
        _ranking_row(30, 30, returns=(0.0, 0.1, 0.2, 0.4)),
        _ranking_row(31, 31, returns=(0.0, 0.1, 0.2, 0.4)),
    )

    trained_a = ranking.train_counterfactual_ranking(
        first,
        train_rows=train_rows,
        holdout_rows=holdout_a,
        training_steps=4,
    )
    trained_b = ranking.train_counterfactual_ranking(
        second,
        train_rows=train_rows,
        holdout_rows=holdout_b,
        training_steps=4,
    )

    assert trained_a.report["fit"]["optimizer_steps"] == 4
    assert trained_a.report["fit"]["final_loss"] < trained_a.report["fit"][
        "first_step_loss"
    ]
    assert trained_a.entry_model != trained_a.trained_model
    assert trained_a.trained_model == trained_b.trained_model


def test_tracked_r7_entry_checkpoint_restores_without_optimizer_moments():
    checkpoint = Path(
        "reports/noncombat_card_only_native_baseline_rl_pilot_20260813_r7/checkpoint_004.json"
    ).read_bytes()

    bootstrap = ranking.restore_entry_bootstrap(checkpoint)
    optimizer = runtime.build_candidate_card_optimizer(bootstrap)

    assert optimizer.state == {}
