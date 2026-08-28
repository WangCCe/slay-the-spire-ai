import pytest
import torch

from analysis_scripts.combat_rl_lightspeed_guard_transfer_poc import (
    binary_roc_auc,
    fit_action_classifier,
    fit_classifier,
    gated_action_metrics,
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


def test_action_classifier_learns_changed_legal_actions() -> None:
    features = torch.tensor(
        [[-2.0, 0.0], [-1.0, 0.0], [1.0, 0.0], [2.0, 0.0]] * 16
    )
    masks = torch.ones(64, 3, dtype=torch.bool)
    actions = torch.tensor([0, 0, 2, 2] * 16)
    changed = torch.ones(64, dtype=torch.bool)

    model, losses = fit_action_classifier(
        features, masks, actions, changed, seed=12, updates=100
    )
    with torch.no_grad():
        predicted = model(features, masks).argmax(dim=1)

    assert losses[-1] < losses[0]
    assert predicted.eq(actions).float().mean().item() > 0.95


def test_gated_action_metrics_preserve_closed_direct_rows() -> None:
    parent = torch.tensor([0, 1, 0, 1])
    correction = torch.tensor([2, 2, 2, 2])
    executed = torch.tensor([0, 1, 2, 2])
    changed = torch.tensor([False, False, True, True])
    gate_open = torch.tensor([False, False, True, False])
    continuous = torch.zeros(4, 328)

    metrics = gated_action_metrics(
        parent_actions=parent,
        correction_actions=correction,
        executed_actions=executed,
        changed=changed,
        gate_open=gate_open,
        continuous=continuous,
    )

    assert metrics["direct"]["candidate_agreement"] == 1.0
    assert metrics["changed"]["candidate_agreement"] == 0.5
    assert metrics["candidate_agreement"] == 0.75
