from __future__ import annotations

import copy

import pytest
import torch

from spirecomm.ai.rl.v2.latent_gated_adapter import (
    LatentGateConfig,
    LatentGatedActionAdapter,
    adapter_training_loss,
    build_development_artifact,
    load_development_artifact,
    state_dict_sha256,
)
from spirecomm.ai.rl.v2.network import create_dqn_v2


METADATA = {
    "network_type": "standard",
    "continuous_dim": 4,
    "action_dim": 3,
    "card_vocab": 6,
    "potion_vocab": 6,
    "relic_vocab": 6,
    "card_slots": 1,
    "potion_slots": 1,
    "relic_slots": 1,
}


def _fixture():
    torch.manual_seed(41)
    parent = create_dqn_v2(device="cpu", **METADATA)
    parent.eval()
    continuous = torch.tensor(
        [
            [-1.0, 0.0, 0.5, 1.0],
            [1.0, 0.5, 0.0, -1.0],
            [0.0, 1.0, -0.5, 0.5],
            [0.5, -0.5, 1.0, 0.0],
        ],
        dtype=torch.float32,
    )
    card_ids = torch.tensor([[1], [2], [3], [4]], dtype=torch.long)
    potion_ids = torch.tensor([[2], [3], [4], [1]], dtype=torch.long)
    relic_ids = torch.tensor([[3], [4], [1], [2]], dtype=torch.long)
    masks = torch.tensor(
        [
            [True, True, False],
            [True, True, True],
            [False, True, True],
            [True, False, True],
        ]
    )
    return parent, continuous, card_ids, potion_ids, relic_ids, masks


def _inputs(rows):
    _, continuous, card_ids, potion_ids, relic_ids, masks = rows
    return continuous, card_ids, potion_ids, relic_ids, masks


@pytest.mark.parametrize(
    "config",
    [
        LatentGateConfig(hidden_dim=0),
        LatentGateConfig(gate_threshold=0.0),
        LatentGateConfig(gate_threshold=1.0),
    ],
)
def test_config_rejects_invalid_values(config):
    with pytest.raises(ValueError):
        config.validate()


def test_parent_is_frozen_and_inventory_reaches_latent_features():
    rows = _fixture()
    parent = rows[0]
    adapter = LatentGatedActionAdapter(parent, METADATA, LatentGateConfig())
    continuous, card_ids, potion_ids, relic_ids, masks = _inputs(rows)

    components = adapter.correction_components(
        continuous, card_ids, potion_ids, relic_ids, masks
    )
    changed_cards = card_ids.clone()
    changed_cards[0, 0] = 5
    changed = adapter.correction_components(
        continuous, changed_cards, potion_ids, relic_ids, masks
    )

    assert components.features.shape == (4, adapter.feature_dim)
    assert components.parent_latent.shape[1] == 256
    assert torch.isfinite(components.features).all()
    assert not torch.equal(components.features[0], changed.features[0])
    assert all(not parameter.requires_grad for parameter in adapter.parent.parameters())
    assert all(parameter.requires_grad for parameter in adapter.gate.parameters())
    assert all(parameter.requires_grad for parameter in adapter.correction.parameters())


def test_closed_gate_is_exact_parent_action():
    rows = _fixture()
    parent = rows[0]
    adapter = LatentGatedActionAdapter(parent, METADATA, LatentGateConfig())
    inputs = _inputs(rows)
    with torch.no_grad():
        parent_actions = parent(*inputs).argmax(dim=1)
        adapter.correction[-1].bias.copy_(torch.tensor([100.0, -100.0, 50.0]))

    selected = adapter.select_actions(*inputs)

    assert torch.equal(selected.actions, parent_actions)
    assert not bool(selected.gate_open.any())
    assert selected.telemetry["gate_open_count"] == 0
    assert selected.telemetry["parent_action_preserved_count"] == 4


def test_open_gate_masks_illegal_correction_action():
    rows = _fixture()
    adapter = LatentGatedActionAdapter(rows[0], METADATA, LatentGateConfig())
    with torch.no_grad():
        adapter.gate[-1].bias.fill_(10.0)
        adapter.correction[-1].bias.copy_(torch.tensor([100.0, 5.0, 10.0]))

    selected = adapter.select_actions(*_inputs(rows))

    assert bool(selected.gate_open.all())
    assert selected.correction_actions[2].item() == 2
    assert selected.actions[2].item() == 2
    assert bool(rows[-1][torch.arange(4), selected.actions].all())


def test_empty_legal_mask_is_rejected():
    rows = list(_fixture())
    rows[-1] = rows[-1].clone()
    rows[-1][0] = False
    adapter = LatentGatedActionAdapter(rows[0], METADATA, LatentGateConfig())

    with pytest.raises(ValueError, match="legal action"):
        adapter.select_actions(*_inputs(rows))


def test_training_loss_uses_direct_rows_only_for_gate_and_freezes_parent():
    rows = _fixture()
    adapter = LatentGatedActionAdapter(rows[0], METADATA, LatentGateConfig())
    parent_before = copy.deepcopy(adapter.parent.state_dict())
    executed = torch.tensor([0, 1, 2, 2])
    changed = torch.tensor([False, False, True, True])

    loss, telemetry = adapter_training_loss(
        adapter,
        *_inputs(rows),
        executed_actions=executed,
        changed=changed,
    )
    changed_direct_labels = executed.clone()
    changed_direct_labels[:2] = torch.tensor([1, 0])
    _, changed_telemetry = adapter_training_loss(
        adapter,
        *_inputs(rows),
        executed_actions=changed_direct_labels,
        changed=changed,
    )
    loss.backward()

    assert telemetry["direct_count"] == 2
    assert telemetry["changed_count"] == 2
    assert telemetry["action_loss"] == changed_telemetry["action_loss"]
    assert all(parameter.grad is None for parameter in adapter.parent.parameters())
    assert any(parameter.grad is not None for parameter in adapter.gate.parameters())
    assert any(parameter.grad is not None for parameter in adapter.correction.parameters())
    assert state_dict_sha256(adapter.parent.state_dict()) == state_dict_sha256(
        parent_before
    )


def test_training_loss_rejects_illegal_changed_action():
    rows = _fixture()
    adapter = LatentGatedActionAdapter(rows[0], METADATA, LatentGateConfig())
    executed = torch.tensor([0, 1, 0, 2])
    changed = torch.tensor([False, False, True, True])

    with pytest.raises(ValueError, match="illegal"):
        adapter_training_loss(
            adapter,
            *_inputs(rows),
            executed_actions=executed,
            changed=changed,
        )


def test_development_artifact_round_trip_is_exact():
    rows = _fixture()
    adapter = LatentGatedActionAdapter(rows[0], METADATA, LatentGateConfig())
    with torch.no_grad():
        adapter.gate[-1].bias.fill_(1.25)
        adapter.correction[-1].bias.copy_(torch.tensor([1.0, 2.0, 3.0]))
    expected = adapter.select_actions(*_inputs(rows))
    artifact = build_development_artifact(
        adapter,
        parent_checkpoint_sha256="a" * 64,
        telemetry={"source": "fixture"},
    )

    restored = load_development_artifact(
        rows[0],
        METADATA,
        artifact,
        expected_parent_checkpoint_sha256="a" * 64,
    )
    actual = restored.select_actions(*_inputs(rows))

    assert artifact["production_compatible"] is False
    assert artifact["checkpoint_kind"] == "latent_gated_correction_development"
    assert torch.equal(actual.actions, expected.actions)
    assert torch.equal(actual.correction_actions, expected.correction_actions)
    assert torch.equal(actual.gate_probabilities, expected.gate_probabilities)
    assert actual.telemetry == expected.telemetry


def test_artifact_rejects_parent_identity_mismatch():
    rows = _fixture()
    adapter = LatentGatedActionAdapter(rows[0], METADATA, LatentGateConfig())
    artifact = build_development_artifact(
        adapter, parent_checkpoint_sha256="a" * 64, telemetry={}
    )

    with pytest.raises(ValueError, match="checkpoint"):
        load_development_artifact(
            rows[0],
            METADATA,
            artifact,
            expected_parent_checkpoint_sha256="b" * 64,
        )

    changed_parent = copy.deepcopy(rows[0])
    with torch.no_grad():
        next(changed_parent.parameters()).add_(1.0)
    with pytest.raises(ValueError, match="state identity"):
        load_development_artifact(
            changed_parent,
            METADATA,
            artifact,
            expected_parent_checkpoint_sha256="a" * 64,
        )


@pytest.mark.parametrize("mutation", ["extra", "nonfinite", "production"])
def test_artifact_rejects_malformed_or_production_payload(mutation):
    rows = _fixture()
    adapter = LatentGatedActionAdapter(rows[0], METADATA, LatentGateConfig())
    artifact = build_development_artifact(
        adapter, parent_checkpoint_sha256="a" * 64, telemetry={}
    )
    if mutation == "extra":
        artifact["gate_state_dict"]["unexpected"] = torch.zeros(1)
    elif mutation == "nonfinite":
        first = next(iter(artifact["correction_state_dict"]))
        artifact["correction_state_dict"][first].flatten()[0] = float("nan")
    else:
        artifact["production_compatible"] = True

    with pytest.raises(ValueError):
        load_development_artifact(
            rows[0],
            METADATA,
            artifact,
            expected_parent_checkpoint_sha256="a" * 64,
        )
