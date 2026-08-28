from __future__ import annotations

import pytest
import torch

from analysis_scripts.combat_rl_action_relative_selection_latency import (
    _reject_ambient_combat_runtime,
    benchmark_selection,
)
from spirecomm.ai.rl.v2.action_relative_advantage_residual import (
    ActionRelativeAdvantageConfig,
    ActionRelativeAdvantageResidual,
)
from spirecomm.ai.rl.v2.network import create_dqn_v2


METADATA = {
    "network_type": "standard",
    "continuous_dim": 4,
    "action_dim": 6,
    "card_vocab": 5,
    "potion_vocab": 4,
    "relic_vocab": 3,
    "card_slots": 1,
    "potion_slots": 1,
    "relic_slots": 1,
}


def _fixture():
    torch.manual_seed(41)
    parent = create_dqn_v2(device="cpu", **METADATA)
    residual = ActionRelativeAdvantageResidual(
        parent,
        METADATA,
        ActionRelativeAdvantageConfig(hidden_dim=8),
    )
    tensors = {
        "continuous": torch.randn(3, 4),
        "card_ids": torch.tensor([[1], [2], [3]]),
        "potion_ids": torch.tensor([[1], [2], [1]]),
        "relic_ids": torch.tensor([[0], [1], [2]]),
        "action_masks": torch.tensor(
            [
                [True, True, True, False, False, True],
                [True, True, False, True, True, False],
                [True, False, True, True, False, True],
            ]
        ),
        "guard_actions": torch.tensor([0, 1, 2]),
        "alternative_masks": torch.tensor(
            [
                [False, True, True, False, False, True],
                [True, False, False, True, True, False],
                [True, False, False, True, False, True],
            ]
        ),
    }
    return residual, tensors


def test_benchmark_preserves_reference_outputs_and_counts_measurements():
    residual, tensors = _fixture()
    report = benchmark_selection(
        residual,
        tensors,
        warmup_calls=1,
        measurement_calls=6,
        row_selection_seed=43,
        forbidden_action_indices=frozenset({5}),
        gates={
            "maximum_optimized_p95_ms": 1000.0,
            "minimum_p50_speedup": 0.0,
            "prediction_atol": 1e-6,
            "prediction_rtol": 1e-6,
        },
    )

    assert report["measurement_calls"] == 6
    assert report["reference_latency"]["count"] == 6
    assert report["optimized_latency"]["count"] == 6
    assert report["maximum_prediction_delta"] <= 1e-6
    assert report["conditions"]["prediction_parity"] is True
    assert report["decision"] == "offline_latency_preflight_passed"


def test_benchmark_rejects_ambient_combat_runtime(monkeypatch):
    monkeypatch.setenv(
        "STS_COMBAT_RL_ACTION_RELATIVE_SHADOW_REGISTRATION", "unexpected.json"
    )

    with pytest.raises(ValueError, match="rejects ambient combat runtime"):
        _reject_ambient_combat_runtime()
