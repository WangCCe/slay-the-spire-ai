import pytest
import torch

from analysis_scripts.combat_rl_n_step_return_candidate import (
    _fit_full_gradient,
    _n_step_targets_from_bootstrap,
)
from spirecomm.ai.rl.v2.network import create_dqn_v2


def test_n_step_targets_stop_at_terminal_boundaries():
    targets = _n_step_targets_from_bootstrap(
        torch.tensor([1.0, 2.0, 3.0]),
        torch.tensor([False, True, True]),
        torch.tensor([10.0, 20.0, 30.0]),
        horizon=3,
        gamma=0.9,
    )

    assert targets.tolist() == pytest.approx([2.8, 2.0, 3.0])


def test_one_step_target_bootstraps_only_nonterminal_rows():
    targets = _n_step_targets_from_bootstrap(
        torch.tensor([1.0, 2.0]),
        torch.tensor([False, True]),
        torch.tensor([10.0, 20.0]),
        horizon=1,
        gamma=0.9,
    )

    assert targets.tolist() == pytest.approx([10.0, 2.0])


def test_three_step_target_bootstraps_from_last_included_transition():
    targets = _n_step_targets_from_bootstrap(
        torch.tensor([1.0, 2.0, 3.0, 4.0]),
        torch.tensor([False, False, False, True]),
        torch.tensor([10.0, 20.0, 30.0, 40.0]),
        horizon=3,
        gamma=0.5,
    )

    assert targets[0].item() == pytest.approx(6.5)


def test_n_step_targets_reject_nonpositive_horizon():
    with pytest.raises(ValueError, match="horizon"):
        _n_step_targets_from_bootstrap(
            torch.tensor([1.0]),
            torch.tensor([True]),
            torch.tensor([0.0]),
            horizon=0,
            gamma=0.99,
        )


def test_full_gradient_update_is_independent_of_memory_chunk_size():
    metadata = {
        "network_type": "standard",
        "continuous_dim": 4,
        "card_vocab": 3,
        "potion_vocab": 3,
        "relic_vocab": 3,
        "action_dim": 2,
        "card_slots": 1,
        "potion_slots": 1,
        "relic_slots": 1,
    }
    torch.manual_seed(7)
    parent_network = create_dqn_v2(device="cpu", **metadata)
    parent = {"online_network_state_dict": parent_network.state_dict()}
    count = 5
    replay = {
        "transition_count": count,
        "continuous": torch.arange(count * 4).reshape(count, 4).float() / 10,
        "card_ids": torch.zeros((count, 1), dtype=torch.long),
        "potion_ids": torch.ones((count, 1), dtype=torch.long),
        "relic_ids": torch.full((count, 1), 2, dtype=torch.long),
        "action_masks": torch.ones((count, 2), dtype=torch.bool),
        "actions": torch.tensor([0, 1, 0, 1, 0]),
    }
    targets = torch.tensor([1.0, -1.0, 0.5, 2.0, -0.5])

    chunked, chunked_metrics = _fit_full_gradient(
        parent=parent,
        metadata=metadata,
        replay=replay,
        targets=targets,
        chunk_size=2,
        steps=2,
        learning_rate=1e-4,
        td_weight=0.05,
    )
    unchunked, unchunked_metrics = _fit_full_gradient(
        parent=parent,
        metadata=metadata,
        replay=replay,
        targets=targets,
        chunk_size=count,
        steps=2,
        learning_rate=1e-4,
        td_weight=0.05,
    )

    assert chunked_metrics["dropout_enabled"] is False
    assert chunked_metrics["transition_passes"] == 2
    assert chunked_metrics["mean_td_loss"] == pytest.approx(
        unchunked_metrics["mean_td_loss"], rel=1e-6
    )
    repeated, _ = _fit_full_gradient(
        parent=parent,
        metadata=metadata,
        replay=replay,
        targets=targets,
        chunk_size=2,
        steps=2,
        learning_rate=1e-4,
        td_weight=0.05,
    )
    for name, value in chunked.state_dict().items():
        assert torch.allclose(
            value, unchunked.state_dict()[name], rtol=1e-5, atol=1e-5
        )
        assert torch.equal(value, repeated.state_dict()[name])


def test_full_gradient_sgd_uses_registered_optimizer():
    metadata = {
        "network_type": "standard",
        "continuous_dim": 4,
        "card_vocab": 3,
        "potion_vocab": 3,
        "relic_vocab": 3,
        "action_dim": 2,
        "card_slots": 1,
        "potion_slots": 1,
        "relic_slots": 1,
    }
    torch.manual_seed(11)
    parent_network = create_dqn_v2(device="cpu", **metadata)
    parent = {"online_network_state_dict": parent_network.state_dict()}
    replay = {
        "transition_count": 2,
        "continuous": torch.zeros((2, 4)),
        "card_ids": torch.zeros((2, 1), dtype=torch.long),
        "potion_ids": torch.zeros((2, 1), dtype=torch.long),
        "relic_ids": torch.zeros((2, 1), dtype=torch.long),
        "action_masks": torch.ones((2, 2), dtype=torch.bool),
        "actions": torch.tensor([0, 1]),
    }

    trained, metrics = _fit_full_gradient(
        parent=parent,
        metadata=metadata,
        replay=replay,
        targets=torch.tensor([1.0, -1.0]),
        chunk_size=2,
        steps=1,
        learning_rate=8e-4,
        td_weight=0.05,
        optimizer_name="sgd",
    )

    assert metrics["optimizer"] == "sgd"
    assert any(
        not torch.equal(value, parent["online_network_state_dict"][name])
        for name, value in trained.state_dict().items()
    )
