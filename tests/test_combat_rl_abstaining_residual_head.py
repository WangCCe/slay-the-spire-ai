from __future__ import annotations

import copy

import pytest
import torch

from analysis_scripts.combat_rl_abstaining_residual_head import (
    AdapterConfig,
    CLOSED_R1_CHECKPOINT_SHA256,
    AbstainingResidualQAdapter,
    build_adapter_artifact,
    build_residual_optimizer,
    load_adapter_artifact,
    residual_training_loss,
    run_synthetic_smoke,
    state_dict_sha256,
    validate_residual_training_source,
)
from spirecomm.ai.rl.v2.network import create_dqn_v2


METADATA = {
    "network_type": "standard",
    "continuous_dim": 4,
    "action_dim": 3,
    "card_vocab": 5,
    "potion_vocab": 5,
    "relic_vocab": 5,
    "card_slots": 1,
    "potion_slots": 1,
    "relic_slots": 1,
}


def _fixture():
    torch.manual_seed(17)
    parent = create_dqn_v2(device="cpu", **METADATA)
    parent.eval()
    continuous = torch.tensor(
        [[-1.0, 0.0, 0.5, 1.0], [1.0, 0.5, 0.0, -1.0]],
        dtype=torch.float32,
    )
    ids = torch.tensor([[1], [2]], dtype=torch.long)
    masks = torch.tensor([[True, True, False], [True, True, True]])
    return parent, continuous, ids, masks


def _forward(module, continuous, ids, masks):
    return module(
        continuous=continuous,
        card_ids=ids,
        potion_ids=ids,
        relic_ids=ids,
        action_mask=masks,
    )


def test_zero_entry_is_exact_parent_and_parent_is_frozen():
    parent, continuous, ids, masks = _fixture()
    adapter = AbstainingResidualQAdapter(parent, METADATA, AdapterConfig())

    expected = _forward(parent, continuous, ids, masks)
    actual = _forward(adapter, continuous, ids, masks)

    assert torch.equal(actual, expected)
    assert torch.equal(adapter.get_best_action(continuous, ids, ids, ids, masks), expected.argmax(1))
    assert all(not parameter.requires_grad for parameter in adapter.parent.parameters())
    assert all(parameter.requires_grad for parameter in adapter.correction.parameters())
    assert torch.isneginf(actual[0, 2])


def test_gate_abstains_then_applies_bounded_legal_correction():
    parent, continuous, ids, masks = _fixture()
    config = AdapterConfig(gate_threshold=0.9, residual_scale=4.0)
    adapter = AbstainingResidualQAdapter(parent, METADATA, config)
    parent_q = _forward(parent, continuous, ids, masks)

    assert torch.equal(_forward(adapter, continuous, ids, masks), parent_q)

    with torch.no_grad():
        projection = adapter.correction[-1]
        projection.bias[0] = 10.0
        projection.bias[1:] = torch.tensor([-10.0, 10.0, 10.0])
    corrected = _forward(adapter, continuous, ids, masks)
    telemetry = adapter.last_forward_telemetry

    assert telemetry["gate_open_count"] == 2
    assert telemetry["maximum_abs_residual"] <= config.residual_scale
    assert not torch.equal(corrected[:, :2], parent_q[:, :2])
    assert torch.isneginf(corrected[0, 2])


def test_loss_updates_only_correction_parameters():
    parent, continuous, ids, masks = _fixture()
    adapter = AbstainingResidualQAdapter(parent, METADATA, AdapterConfig())
    parent_before = copy.deepcopy(adapter.parent.state_dict())
    parent_q = _forward(parent, continuous, ids, masks)
    parent_actions = parent_q.argmax(1)
    executed = torch.tensor([int(parent_actions[0]), (int(parent_actions[1]) + 1) % 3])
    changed = torch.tensor([False, True])
    targets = torch.tensor([0.0, 1.0])

    loss, telemetry = residual_training_loss(
        adapter,
        continuous=continuous,
        card_ids=ids,
        potion_ids=ids,
        relic_ids=ids,
        action_masks=masks,
        executed_actions=executed,
        changed=changed,
        smdp_targets=targets,
    )
    loss.backward()

    assert telemetry["direct_count"] == 1
    assert telemetry["changed_count"] == 1
    assert all(parameter.grad is None for parameter in adapter.parent.parameters())
    assert any(parameter.grad is not None for parameter in adapter.correction.parameters())
    assert state_dict_sha256(adapter.parent.state_dict()) == state_dict_sha256(parent_before)


def test_artifact_round_trip_restores_adapter_and_optimizer():
    parent, continuous, ids, masks = _fixture()
    adapter = AbstainingResidualQAdapter(parent, METADATA, AdapterConfig())
    optimizer = build_residual_optimizer(adapter, learning_rate=0.01)
    artifact = build_adapter_artifact(
        adapter,
        optimizer,
        parent_checkpoint_sha256="a" * 64,
        seed=23,
        update_count=0,
        telemetry={"mechanism": "fixture"},
    )

    restored, restored_optimizer = load_adapter_artifact(
        parent,
        METADATA,
        artifact,
        expected_parent_checkpoint_sha256="a" * 64,
    )

    assert artifact["production_compatible"] is False
    assert torch.equal(
        _forward(restored, continuous, ids, masks),
        _forward(adapter, continuous, ids, masks),
    )
    assert restored_optimizer.state_dict() == optimizer.state_dict()
    assert state_dict_sha256(restored.correction.state_dict()) == state_dict_sha256(
        adapter.correction.state_dict()
    )


def test_synthetic_smoke_is_deterministic_and_closed_r1_is_rejected(tmp_path):
    report = run_synthetic_smoke(tmp_path / "smoke")

    assert report["decision"] == "mechanism_ready_for_fresh_registration"
    assert report["deterministic_repeat_exact"] is True
    assert report["parent_immutable"] is True
    assert report["corrected_changed_count"] > 0
    assert report["direct_action_drift_count"] == 0
    assert (tmp_path / "smoke" / "adapter.pt").is_file()
    assert (tmp_path / "smoke" / "report.json").is_file()

    with pytest.raises(ValueError, match="closed R1"):
        validate_residual_training_source(CLOSED_R1_CHECKPOINT_SHA256)
