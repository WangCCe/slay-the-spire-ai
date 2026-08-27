from __future__ import annotations

import pytest
import torch

from analysis_scripts.combat_rl_inventory_embedding_successor import (
    _atomic_torch_save,
    _combat_group_split,
    _fit_inventory_embeddings,
    _one_step_targets_from_bootstrap,
    _sha256,
    _validate_training_checkpoint,
)
from spirecomm.ai.rl.v2.network import create_dqn_v2


def _metadata() -> dict:
    return {
        "network_type": "standard",
        "continuous_dim": 4,
        "card_vocab": 4,
        "potion_vocab": 4,
        "relic_vocab": 4,
        "action_dim": 3,
        "card_slots": 1,
        "potion_slots": 1,
        "relic_slots": 1,
        "rl_space_version": 2,
    }


def _replay(count: int = 12) -> dict:
    continuous = torch.arange(count * 4).reshape(count, 4).float() / 20.0
    card_ids = torch.ones((count, 1), dtype=torch.long)
    potion_ids = torch.tensor([[1], [2], [0]] * (count // 3), dtype=torch.long)
    relic_ids = torch.tensor([[1], [2], [1]] * (count // 3), dtype=torch.long)
    masks = torch.ones((count, 3), dtype=torch.bool)
    dones = torch.zeros(count, dtype=torch.bool)
    dones[[3, 7, 11]] = True
    return {
        "transition_count": count,
        "continuous": continuous,
        "card_ids": card_ids,
        "potion_ids": potion_ids,
        "relic_ids": relic_ids,
        "action_masks": masks,
        "actions": torch.tensor([0, 1, 2] * (count // 3), dtype=torch.long),
        "rewards": torch.linspace(-2.0, 4.0, count),
        "dones": dones,
        "next_continuous": continuous.flip(0),
        "next_card_ids": card_ids.flip(0),
        "next_potion_ids": potion_ids.flip(0),
        "next_relic_ids": relic_ids.flip(0),
        "next_action_masks": masks.flip(0),
    }


def test_combat_group_split_is_deterministic_and_keeps_groups_whole():
    dones = torch.tensor([False, True, False, False, True, True, False, True])

    first = _combat_group_split(dones, validation_fraction=0.25, seed=91)
    second = _combat_group_split(dones, validation_fraction=0.25, seed=91)

    assert torch.equal(first.train_indices, second.train_indices)
    assert torch.equal(first.validation_indices, second.validation_indices)
    assert sorted(first.train_indices.tolist() + first.validation_indices.tolist()) == list(
        range(len(dones))
    )
    train = set(first.train_indices.tolist())
    validation = set(first.validation_indices.tolist())
    for group in ({0, 1}, {2, 3, 4}, {5}, {6, 7}):
        assert group <= train or group <= validation


def test_one_step_targets_do_not_consume_following_array_rewards():
    targets = _one_step_targets_from_bootstrap(
        rewards=torch.tensor([1.0, 999.0]),
        dones=torch.tensor([False, True]),
        next_bootstrap=torch.tensor([10.0, float("-inf")]),
        gamma=0.9,
    )

    assert targets.tolist() == pytest.approx([10.0, 999.0])


def test_candidate_serialization_is_byte_deterministic(tmp_path):
    payload = {"state": {"weight": torch.arange(12).reshape(3, 4).float()}}
    first = tmp_path / "first.pth"
    second = tmp_path / "second.pth"

    _atomic_torch_save(payload, first)
    _atomic_torch_save(payload, second)

    assert _sha256(first) == _sha256(second)


def test_training_checkpoint_rejects_optimizer_state_and_hash_mismatch():
    metadata = _metadata()
    torch.manual_seed(7)
    network = create_dqn_v2(device="cpu", **{k: v for k, v in metadata.items() if k != "rl_space_version"})
    checkpoint = {
        "metadata": metadata,
        "online_network_state_dict": network.state_dict(),
        "target_network_state_dict": network.state_dict(),
        "optimizer_state_dict": {"state": {1: {"step": 1}}},
        "replay_buffer_state_dict": _replay(),
    }

    with pytest.raises(ValueError, match="optimizer"):
        _validate_training_checkpoint(checkpoint, expected_transition_count=12)

    checkpoint["optimizer_state_dict"] = {"state": {}}
    with pytest.raises(ValueError, match="transition count"):
        _validate_training_checkpoint(checkpoint, expected_transition_count=13)


def test_fit_updates_only_observed_nonzero_inventory_rows_and_is_deterministic():
    metadata = _metadata()
    replay = _replay()
    torch.manual_seed(11)
    parent_network = create_dqn_v2(
        device="cpu", **{k: v for k, v in metadata.items() if k != "rl_space_version"}
    )
    parent = {name: value.detach().clone() for name, value in parent_network.state_dict().items()}
    train_indices = torch.arange(int(replay["transition_count"]))

    first, first_metrics = _fit_inventory_embeddings(
        parent_state=parent,
        target_state=parent,
        metadata=metadata,
        replay=replay,
        train_indices=train_indices,
        epochs=3,
        batch_size=4,
        learning_rate=1e-2,
        td_weight=1.0,
        anchor_weight=0.1,
        gamma=0.9,
        seed=23,
    )
    second, second_metrics = _fit_inventory_embeddings(
        parent_state=parent,
        target_state=parent,
        metadata=metadata,
        replay=replay,
        train_indices=train_indices,
        epochs=3,
        batch_size=4,
        learning_rate=1e-2,
        td_weight=1.0,
        anchor_weight=0.1,
        gamma=0.9,
        seed=23,
    )

    first_state = first.state_dict()
    second_state = second.state_dict()
    assert first_metrics == second_metrics
    assert all(torch.equal(first_state[name], second_state[name]) for name in first_state)
    assert torch.equal(first_state["potion_embedding.weight"][0], parent["potion_embedding.weight"][0])
    assert torch.equal(first_state["potion_embedding.weight"][3], parent["potion_embedding.weight"][3])
    assert torch.equal(first_state["relic_embedding.weight"][0], parent["relic_embedding.weight"][0])
    assert torch.equal(first_state["relic_embedding.weight"][3], parent["relic_embedding.weight"][3])
    assert not torch.equal(first_state["potion_embedding.weight"][1], parent["potion_embedding.weight"][1])
    assert not torch.equal(first_state["relic_embedding.weight"][1], parent["relic_embedding.weight"][1])
    assert all(
        torch.equal(value, parent[name])
        for name, value in first_state.items()
        if name not in {"potion_embedding.weight", "relic_embedding.weight"}
    )
