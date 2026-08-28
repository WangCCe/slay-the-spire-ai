from __future__ import annotations

import copy
import io

import pytest
import torch

from spirecomm.ai.rl.v2.action_relative_uncertainty_ensemble import (
    ActionRelativeUncertaintyConfig,
    ActionRelativeUncertaintyEnsemble,
    build_ensemble_development_artifact,
    load_ensemble_development_artifact,
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
MEMBER_SEEDS = (101, 102, 103, 104, 105)


def _fixture() -> tuple[ActionRelativeUncertaintyEnsemble, dict[str, torch.Tensor]]:
    torch.manual_seed(17)
    parent = create_dqn_v2(device="cpu", **METADATA)
    ensemble = ActionRelativeUncertaintyEnsemble(
        parent,
        METADATA,
        ActionRelativeUncertaintyConfig(
            hidden_dim=8,
            member_count=5,
            confidence_scale=1.0,
            advantage_threshold=0.5,
            target_clip=20.0,
            target_scale=1.0,
        ),
        member_seeds=MEMBER_SEEDS,
    )
    inputs = {
        "continuous": torch.randn(2, 4),
        "card_ids": torch.tensor([[1], [2]]),
        "potion_ids": torch.tensor([[1], [2]]),
        "relic_ids": torch.tensor([[0], [1]]),
        "action_masks": torch.tensor(
            [[True, True, False, True], [True, True, True, False]]
        ),
        "guard_actions": torch.tensor([0, 1]),
        "alternative_masks": torch.tensor(
            [[False, True, False, True], [True, False, True, False]]
        ),
    }
    return ensemble, inputs


def _set_constant_member_predictions(
    ensemble: ActionRelativeUncertaintyEnsemble, values: tuple[float, ...]
) -> None:
    with torch.no_grad():
        for scorer, value in zip(ensemble.member_scorers, values):
            for parameter in scorer.parameters():
                parameter.zero_()
            scorer[-1].bias.fill_(value)


def test_member_statistics_use_unbiased_sample_std_and_lcb():
    ensemble, inputs = _fixture()
    _set_constant_member_predictions(ensemble, (0.0, 1.0, 2.0, 3.0, 4.0))

    stats = ensemble.score_candidate_statistics(
        inputs["continuous"],
        inputs["card_ids"],
        inputs["potion_ids"],
        inputs["relic_ids"],
        inputs["action_masks"],
        inputs["guard_actions"],
        torch.tensor([1, 2]),
    )

    expected_std = torch.tensor([0.0, 1.0, 2.0, 3.0, 4.0]).std(unbiased=True)
    assert stats.member_predictions.shape == (2, 5)
    assert torch.allclose(stats.means, torch.full((2,), 2.0))
    assert torch.allclose(stats.standard_deviations, torch.full((2,), expected_std))
    assert torch.allclose(
        stats.lower_confidence_scores, torch.full((2,), 2.0 - expected_std)
    )


def test_selection_uses_lcb_abstains_and_masks_forbidden_actions():
    ensemble, inputs = _fixture()
    _set_constant_member_predictions(ensemble, (0.0, 1.0, 2.0, 3.0, 4.0))

    closed = ensemble.select_actions(**inputs)
    assert torch.equal(closed.actions, inputs["guard_actions"])
    assert closed.telemetry["intervention_count"] == 0

    _set_constant_member_predictions(ensemble, (1.0, 1.0, 1.0, 1.0, 1.0))
    opened = ensemble.select_actions(**inputs)
    assert opened.actions.tolist() == [1, 0]
    assert torch.allclose(opened.member_means, torch.ones(2))
    assert torch.allclose(opened.member_standard_deviations, torch.zeros(2))

    constrained = ensemble.select_actions(
        **inputs, forbidden_action_indices=frozenset({0, 1})
    )
    assert constrained.actions.tolist() == [3, 2]
    assert constrained.telemetry["forbidden_action_selection_count"] == 0


def test_training_members_preserves_one_shared_frozen_parent():
    ensemble, inputs = _fixture()
    parent_before = state_dict_sha256(ensemble.parent.state_dict())
    stats = ensemble.score_candidate_statistics(
        inputs["continuous"],
        inputs["card_ids"],
        inputs["potion_ids"],
        inputs["relic_ids"],
        inputs["action_masks"],
        inputs["guard_actions"],
        torch.tensor([1, 2]),
    )
    stats.member_predictions.sum().backward()

    assert state_dict_sha256(ensemble.parent.state_dict()) == parent_before
    assert all(parameter.grad is None for parameter in ensemble.parent.parameters())
    assert all(
        any(parameter.grad is not None for parameter in scorer.parameters())
        for scorer in ensemble.member_scorers
    )
    assert sum(key.startswith("parent.") for key in ensemble.state_dict()) > 0
    assert not any("member_scorers" in key and ".parent." in key for key in ensemble.state_dict())


def test_ensemble_artifact_roundtrip_is_exact_and_source_bound():
    ensemble, inputs = _fixture()
    _set_constant_member_predictions(ensemble, (1.0, 1.0, 1.0, 1.0, 1.0))
    before = ensemble.select_actions(**inputs, forbidden_action_indices=frozenset({1}))
    artifact = build_ensemble_development_artifact(
        ensemble,
        parent_checkpoint_sha256="a" * 64,
        corpus_sha256={"train": "b" * 64, "evaluation": "c" * 64},
        recipe={"member_seeds": list(MEMBER_SEEDS)},
        bootstrap_sha256=[str(index) * 64 for index in range(1, 6)],
        telemetry={"fit": "fixture"},
    )
    buffer = io.BytesIO()
    torch.save(artifact, buffer)
    buffer.seek(0)
    loaded = torch.load(buffer, map_location="cpu", weights_only=False)
    restored = load_ensemble_development_artifact(
        ensemble.parent,
        METADATA,
        loaded,
        expected_parent_checkpoint_sha256="a" * 64,
        expected_corpus_sha256={"train": "b" * 64, "evaluation": "c" * 64},
        expected_recipe={"member_seeds": list(MEMBER_SEEDS)},
    )
    after = restored.select_actions(**inputs, forbidden_action_indices=frozenset({1}))

    assert torch.equal(after.actions, before.actions)
    assert torch.equal(after.predicted_advantages, before.predicted_advantages)
    assert torch.equal(after.member_means, before.member_means)
    assert torch.equal(
        after.member_standard_deviations, before.member_standard_deviations
    )

    bad = copy.deepcopy(loaded)
    bad["bootstrap_sha256"][0] = "f" * 64
    with pytest.raises(ValueError, match="bootstrap identity"):
        load_ensemble_development_artifact(
            ensemble.parent,
            METADATA,
            bad,
            expected_parent_checkpoint_sha256="a" * 64,
            expected_corpus_sha256={"train": "b" * 64, "evaluation": "c" * 64},
            expected_recipe={"member_seeds": list(MEMBER_SEEDS)},
        )
