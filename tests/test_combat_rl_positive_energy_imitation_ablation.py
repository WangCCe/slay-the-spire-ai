import pytest
import torch

from analysis_scripts.combat_rl_positive_energy_imitation_ablation import (
    _pairwise_end_turn_margin_loss,
)
from spirecomm.ai.rl.v2.action_space import END_TURN_ACTION


def test_pairwise_end_turn_margin_loss_only_uses_eligible_rows():
    q_values = torch.zeros((3, END_TURN_ACTION + 1), dtype=torch.float32)
    actions = torch.tensor([2, 3, 4])
    eligible = torch.tensor([True, True, False])
    q_values[0, 2] = 0.75
    q_values[1, 3] = -0.5

    loss = _pairwise_end_turn_margin_loss(
        q_values,
        actions,
        eligible,
        margin=1.0,
    )

    assert float(loss) == pytest.approx((0.25 + 1.5) / 2)


def test_pairwise_end_turn_margin_loss_is_zero_without_eligible_rows():
    q_values = torch.zeros((2, END_TURN_ACTION + 1), dtype=torch.float32)
    actions = torch.tensor([2, 3])

    loss = _pairwise_end_turn_margin_loss(
        q_values,
        actions,
        torch.tensor([False, False]),
        margin=1.0,
    )

    assert float(loss) == 0.0
