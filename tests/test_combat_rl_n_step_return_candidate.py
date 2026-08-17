import pytest
import torch

from analysis_scripts.combat_rl_n_step_return_candidate import (
    _n_step_targets_from_bootstrap,
)


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
