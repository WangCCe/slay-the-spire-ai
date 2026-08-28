from __future__ import annotations

import pytest
import torch

from analysis_scripts.combat_rl_action_relative_selection_latency import (
    EXPERIMENT_ID,
    FIXED_GATES,
    _assert_parity,
    _reject_ambient_combat_runtime,
    benchmark_selection,
)
from spirecomm.ai.rl.v2.action_relative_advantage_residual import (
    ActionRelativeAdvantageConfig,
    ActionRelativeAdvantageResidual,
    ActionRelativeSelection,
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


def _selection(
    prediction: float,
    *,
    action: int = 2,
    gate_open: bool = True,
    telemetry: dict[str, int] | None = None,
) -> ActionRelativeSelection:
    return ActionRelativeSelection(
        actions=torch.tensor([action]),
        guard_actions=torch.tensor([0]),
        residual_actions=torch.tensor([2]),
        predicted_advantages=torch.tensor([prediction]),
        gate_open=torch.tensor([gate_open]),
        telemetry=telemetry or {"intervention_count": 1},
    )


def test_r2_identity_and_float32_gates_are_frozen():
    assert EXPERIMENT_ID == "combat-rl-action-relative-selection-latency-20260829-r2"
    assert FIXED_GATES == {
        "maximum_optimized_p95_ms": 15.0,
        "minimum_p50_speedup": 2.0,
        "prediction_atol": 1e-5,
        "prediction_rtol": 1e-5,
    }


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


def test_float32_prediction_parity_accepts_diagnostic_scale_delta():
    delta = _assert_parity(
        _selection(0.2),
        _selection(0.2000064),
        rtol=1e-5,
        atol=1e-5,
    )

    assert delta == pytest.approx(6.4e-6, abs=1e-7)


def test_float32_prediction_parity_rejects_out_of_tolerance_delta():
    with pytest.raises(RuntimeError, match="prediction parity failed"):
        _assert_parity(
            _selection(0.2),
            _selection(0.20002),
            rtol=1e-5,
            atol=1e-5,
        )


@pytest.mark.parametrize(
    "optimized",
    [
        _selection(0.2, action=3),
        _selection(0.2, gate_open=False),
        _selection(0.2, telemetry={"intervention_count": 0}),
    ],
)
def test_float32_prediction_parity_still_requires_exact_behavior(optimized):
    with pytest.raises(RuntimeError, match="parity failed"):
        _assert_parity(
            _selection(0.2),
            optimized,
            rtol=1e-5,
            atol=1e-5,
        )
