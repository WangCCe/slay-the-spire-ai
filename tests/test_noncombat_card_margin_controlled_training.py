from __future__ import annotations

import copy

import pytest
import torch

from analysis_scripts import noncombat_card_acceptance_empirical_successor_runtime as runtime
from analysis_scripts import noncombat_card_margin_controlled_training as margin
from analysis_scripts.noncombat_card_acceptance_policy import CardAcceptancePolicy


def _candidates() -> list[dict[str, str]]:
    return [
        {"action_id": "take-z", "kind": "take"},
        {"action_id": "bowl", "kind": "bowl"},
        {"action_id": "take-a", "kind": "take"},
        {"action_id": "skip", "kind": "skip"},
    ]


def _features() -> torch.Tensor:
    return torch.tensor(
        [[4.0, 0.0], [3.0, 1.0], [0.0, 4.0], [1.0, 3.0]],
        dtype=torch.float32,
    )


def _scaled_policy(source: CardAcceptancePolicy) -> margin.MarginControlledCardPolicy:
    scaled = margin.MarginControlledCardPolicy(
        source.input_dim,
        source.hidden_dim,
        temperature=margin.LOGIT_TEMPERATURE,
    )
    scaled.family_head.load_state_dict(copy.deepcopy(source.family_head.state_dict()))
    scaled.conditional_ranker.load_state_dict(
        copy.deepcopy(source.conditional_ranker.state_dict())
    )
    scaled.freeze_base()
    return scaled


def test_zero_residual_compresses_logits_and_preserves_complete_ordering():
    torch.manual_seed(19)
    source = CardAcceptancePolicy(input_dim=2, hidden_dim=3)
    scaled = _scaled_policy(source)
    state = torch.tensor([0.5, 0.25], dtype=torch.float32)

    raw = source(state, _features(), _candidates(), category="card_reward")
    compressed = scaled(state, _features(), _candidates(), category="card_reward")

    assert torch.equal(
        compressed.family_logits,
        raw.family_logits / margin.LOGIT_TEMPERATURE,
    )
    assert torch.equal(
        compressed.conditional_logits,
        raw.conditional_logits / margin.LOGIT_TEMPERATURE,
    )
    assert torch.equal(
        torch.argsort(compressed.family_logits, descending=True, stable=True),
        torch.argsort(raw.family_logits, descending=True, stable=True),
    )
    assert torch.equal(
        torch.argsort(compressed.conditional_logits, descending=True, stable=True),
        torch.argsort(raw.conditional_logits, descending=True, stable=True),
    )
    assert all(
        not parameter.requires_grad
        for module in (scaled.family_head, scaled.conditional_ranker)
        for parameter in module.parameters()
    )
    assert all(
        parameter.requires_grad
        for module in (scaled.family_residual, scaled.conditional_residual)
        for parameter in module.parameters()
    )


@pytest.mark.parametrize("temperature", [0.0, -1.0, float("inf"), float("nan")])
def test_invalid_temperature_is_rejected(temperature: float):
    with pytest.raises(
        margin.MarginControlledTrainingBlocked,
        match="temperature must be positive",
    ):
        margin.MarginControlledCardPolicy(2, 3, temperature=temperature)


def test_bootstrap_owns_only_128_fresh_residual_parameters():
    source = runtime.build_matched_bootstrap()
    source_family = runtime._model_state_bytes(source.candidate.card_policy.family_head)
    source_conditional = runtime._model_state_bytes(
        source.candidate.card_policy.conditional_ranker
    )

    scaled = margin.build_margin_controlled_bootstrap(source)
    optimizer = margin.build_residual_optimizer(scaled)
    named = margin.residual_named_parameters(scaled)

    assert runtime._model_state_bytes(scaled.candidate.card_policy.family_head) == source_family
    assert (
        runtime._model_state_bytes(scaled.candidate.card_policy.conditional_ranker)
        == source_conditional
    )
    assert sum(parameter.numel() for _, parameter in named) == 128
    assert optimizer.param_groups[0]["params"] == [parameter for _, parameter in named]
    assert all(torch.count_nonzero(parameter).item() == 0 for _, parameter in named)


def test_entry_gate_requires_ordering_and_exact_temperature_scaling():
    raw = (
        {
            "action_id": "take-a",
            "decision_index": 1,
            "family": "take",
            "family_probabilities": [0.2, 0.8],
            "joint_entropy": 0.4,
            "joint_probabilities": [0.2, 0.8],
            "seed": 7,
            "two_stage_margin": 4.0,
        },
    )
    compressed = (
        {
            "action_id": "take-a",
            "decision_index": 1,
            "family": "take",
            "family_probabilities": [0.4, 0.6],
            "joint_entropy": 0.6,
            "joint_probabilities": [0.4, 0.6],
            "seed": 7,
            "two_stage_margin": 1.0,
        },
    )

    passed = margin._surface_entry_gate(
        raw,
        compressed,
        ordering_preserved=True,
        temperature=4.0,
    )
    failed = margin._surface_entry_gate(
        raw,
        compressed,
        ordering_preserved=False,
        temperature=4.0,
    )

    assert all(passed["checks"].values())
    assert failed["checks"]["entry_orderings_preserved"] is False


def test_residual_bytes_exclude_frozen_base_model():
    scaled = margin.build_margin_controlled_bootstrap(runtime.build_matched_bootstrap())
    base_before = margin._base_model_bytes(scaled)
    residual_before = margin._residual_bytes(scaled)

    with torch.no_grad():
        scaled.candidate.card_policy.family_residual.weight.add_(1.0)

    assert margin._base_model_bytes(scaled) == base_before
    assert margin._residual_bytes(scaled) != residual_before
