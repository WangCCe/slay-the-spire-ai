from __future__ import annotations

import copy
import io

import pytest
import torch

from spirecomm.ai.rl.v2.guard_advantage_residual import (
    GuardAdvantageResidual,
    GuardAdvantageResidualConfig,
    build_development_artifact,
    load_development_artifact,
    residual_training_loss,
)
from spirecomm.ai.rl.v2.latent_gated_adapter import state_dict_sha256
from spirecomm.ai.rl.v2.network import create_dqn_v2


METADATA = {
    "network_type": "standard",
    "continuous_dim": 4,
    "action_dim": 4,
    "card_vocab": 5,
    "potion_vocab": 4,
    "relic_vocab": 3,
    "card_slots": 1,
    "potion_slots": 1,
    "relic_slots": 1,
}


def _fixture() -> tuple[GuardAdvantageResidual, dict[str, torch.Tensor]]:
    torch.manual_seed(11)
    parent = create_dqn_v2(device="cpu", **METADATA)
    residual = GuardAdvantageResidual(
        parent,
        METADATA,
        GuardAdvantageResidualConfig(hidden_dim=8, gate_threshold=0.6),
    )
    inputs = {
        "continuous": torch.randn(3, 4),
        "card_ids": torch.tensor([[1], [2], [3]]),
        "potion_ids": torch.tensor([[1], [2], [3]]),
        "relic_ids": torch.tensor([[0], [1], [2]]),
        "action_masks": torch.tensor(
            [[True, True, False, True], [True, True, True, False], [False, True, True, True]]
        ),
        "guard_actions": torch.tensor([0, 1, 3]),
        "alternative_masks": torch.tensor(
            [[False, True, False, True], [True, False, True, False], [False, True, True, False]]
        ),
    }
    return residual, inputs


def test_hard_gate_abstains_and_open_gate_selects_only_allowed_alternative():
    residual, inputs = _fixture()
    with torch.no_grad():
        residual.action_head[-1].weight.zero_()
        residual.action_head[-1].bias.copy_(torch.tensor([1.0, 2.0, 99.0, 3.0]))
        residual.gate[-1].weight.zero_()
        residual.gate[-1].bias.fill_(-20.0)

    closed = residual.select_actions(**inputs)
    assert torch.equal(closed.actions, inputs["guard_actions"])
    assert closed.telemetry["intervention_count"] == 0

    with torch.no_grad():
        residual.gate[-1].bias.fill_(20.0)
    opened = residual.select_actions(**inputs)
    assert opened.actions.tolist() == [3, 2, 2]
    assert opened.telemetry["intervention_count"] == 3
    rows = torch.arange(3)
    assert bool(inputs["alternative_masks"][rows, opened.actions].all())


def test_training_uses_all_gate_rows_and_positive_action_rows_only():
    residual, inputs = _fixture()
    parent_before = state_dict_sha256(residual.parent.state_dict())
    loss, metrics = residual_training_loss(
        residual,
        **inputs,
        target_actions=torch.tensor([3, 1, 2]),
        positive=torch.tensor([True, False, True]),
    )
    loss.backward()

    assert torch.isfinite(loss)
    assert metrics["positive_count"] == 2
    assert metrics["negative_count"] == 1
    assert state_dict_sha256(residual.parent.state_dict()) == parent_before
    assert all(parameter.grad is None for parameter in residual.parent.parameters())
    assert any(parameter.grad is not None for parameter in residual.gate.parameters())
    assert any(parameter.grad is not None for parameter in residual.action_head.parameters())


def test_invalid_guard_or_alternative_mask_is_rejected():
    residual, inputs = _fixture()
    bad_guard = copy.deepcopy(inputs)
    bad_guard["guard_actions"] = torch.tensor([2, 1, 3])
    with pytest.raises(ValueError, match="guard action must be legal"):
        residual.select_actions(**bad_guard)

    bad_alternative = copy.deepcopy(inputs)
    bad_alternative["alternative_masks"][0, 0] = True
    with pytest.raises(ValueError, match="contains guard action"):
        residual.select_actions(**bad_alternative)


def test_development_artifact_round_trip_is_exact_and_source_bound():
    residual, inputs = _fixture()
    with torch.no_grad():
        residual.gate[-1].bias.fill_(1.5)
        residual.action_head[-1].bias.copy_(torch.tensor([0.0, 1.0, 2.0, 3.0]))
    before = residual.select_actions(**inputs)
    artifact = build_development_artifact(
        residual,
        parent_checkpoint_sha256="a" * 64,
        corpus_sha256={"train": "b" * 64, "evaluation": "c" * 64},
        telemetry={"fit": "fixture"},
    )
    buffer = io.BytesIO()
    torch.save(artifact, buffer)
    buffer.seek(0)
    loaded_artifact = torch.load(buffer, map_location="cpu", weights_only=False)
    restored = load_development_artifact(
        residual.parent,
        METADATA,
        loaded_artifact,
        expected_parent_checkpoint_sha256="a" * 64,
        expected_corpus_sha256={"train": "b" * 64, "evaluation": "c" * 64},
    )
    after = restored.select_actions(**inputs)

    assert torch.equal(after.actions, before.actions)
    assert torch.equal(after.gate_open, before.gate_open)
    assert torch.equal(after.gate_probabilities, before.gate_probabilities)
    assert state_dict_sha256(restored.gate.state_dict()) == artifact[
        "gate_state_dict_sha256"
    ]
    assert state_dict_sha256(restored.action_head.state_dict()) == artifact[
        "action_state_dict_sha256"
    ]

    loaded_artifact["corpus_sha256"]["train"] = "d" * 64
    with pytest.raises(ValueError, match="corpus identity"):
        load_development_artifact(
            residual.parent,
            METADATA,
            loaded_artifact,
            expected_parent_checkpoint_sha256="a" * 64,
            expected_corpus_sha256={"train": "b" * 64, "evaluation": "c" * 64},
        )
