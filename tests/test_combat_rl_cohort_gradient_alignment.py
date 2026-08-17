import argparse
from pathlib import Path

import pytest
import torch

from analysis_scripts.combat_rl_cohort_gradient_alignment import (
    _cosine_similarity,
    _matching_indices,
    _parse_cohort,
    _weighted_mean_gradient,
)


def test_cosine_similarity_reports_alignment_and_conflict():
    horizontal = torch.tensor([1.0, 0.0])

    assert _cosine_similarity(horizontal, horizontal) == pytest.approx(1.0)
    assert _cosine_similarity(horizontal, -horizontal) == pytest.approx(-1.0)
    assert _cosine_similarity(
        horizontal, torch.tensor([0.0, 1.0])
    ) == pytest.approx(0.0)


def test_weighted_mean_gradient_uses_row_counts():
    result = _weighted_mean_gradient(
        [torch.tensor([1.0, 3.0]), torch.tensor([5.0, 7.0])],
        [1, 3],
    )

    assert result.tolist() == pytest.approx([4.0, 6.0])


def test_parse_cohort_requires_name_and_path():
    assert _parse_cohort("r1=replay.pth") == ("r1", Path("replay.pth"))
    with pytest.raises(argparse.ArgumentTypeError):
        _parse_cohort("replay.pth")


def test_matching_indices_returns_flat_row_indices():
    assert _matching_indices(torch.tensor([False, True, False, True])).tolist() == [
        1,
        3,
    ]
