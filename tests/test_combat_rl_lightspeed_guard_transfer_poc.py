import pytest
import torch

from analysis_scripts.combat_rl_lightspeed_guard_transfer_poc import (
    binary_roc_auc,
    fit_classifier,
    intervention_metrics,
    threshold_at_direct_open_cap,
)


def test_binary_roc_auc_handles_ties() -> None:
    scores = torch.tensor([0.1, 0.5, 0.5, 0.9])
    labels = torch.tensor([False, False, True, True])

    assert binary_roc_auc(scores, labels) == 0.875


def test_threshold_respects_direct_open_cap() -> None:
    scores = torch.tensor([0.05, 0.10, 0.20, 0.30, 0.70, 0.80, 0.90, 0.95])
    labels = torch.tensor([False, False, False, False, True, True, True, True])

    threshold = threshold_at_direct_open_cap(scores, labels, cap=0.10)
    metrics = intervention_metrics(scores, labels, thresholds=threshold)

    assert threshold == pytest.approx(0.70)
    assert metrics["direct_open_share"] == 0.0
    assert metrics["changed_open_share"] == 1.0


def test_fit_classifier_separates_simple_balanced_data() -> None:
    torch.manual_seed(7)
    negative = torch.randn(64, 3) - 2.0
    positive = torch.randn(64, 3) + 2.0
    features = torch.cat((negative, positive))
    labels = torch.cat(
        (torch.zeros(64, dtype=torch.bool), torch.ones(64, dtype=torch.bool))
    )

    model, losses = fit_classifier(
        features,
        labels,
        torch.arange(128),
        seed=9,
        updates=80,
    )
    with torch.no_grad():
        scores = torch.sigmoid(model(features))

    assert len(losses) == 80
    assert losses[-1] < losses[0]
    assert binary_roc_auc(scores, labels) > 0.99
