from __future__ import annotations

import copy
import io

import pytest
import torch
import torch.nn.functional as F

from spirecomm.ai.rl.v2.action_relative_advantage_residual import (
    ActionRelativeAdvantageConfig,
    ActionRelativeAdvantageResidual,
    build_development_artifact,
    expand_action_relative_examples,
    load_development_artifact,
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


def _state_tensors() -> dict[str, torch.Tensor]:
    return {
        "continuous": torch.randn(2, 4),
        "card_ids": torch.tensor([[1], [2]]),
        "potion_ids": torch.tensor([[1], [2]]),
        "relic_ids": torch.tensor([[0], [1]]),
        "action_masks": torch.tensor(
            [[True, True, False, True], [True, True, True, False]]
        ),
        "guard_actions": torch.tensor([0, 1]),
    }


def _fixture() -> tuple[ActionRelativeAdvantageResidual, dict[str, torch.Tensor]]:
    torch.manual_seed(17)
    parent = create_dqn_v2(device="cpu", **METADATA)
    residual = ActionRelativeAdvantageResidual(
        parent,
        METADATA,
        ActionRelativeAdvantageConfig(
            hidden_dim=8,
            advantage_threshold=0.5,
            target_clip=20.0,
            target_scale=10.0,
        ),
    )
    inputs = _state_tensors()
    inputs["alternative_masks"] = torch.tensor(
        [[False, True, False, True], [True, False, True, False]]
    )
    return residual, inputs


def test_corpus_expansion_preserves_every_non_guard_branch_and_exact_advantage():
    tensors = _state_tensors()
    metadata = [
        {
            "guard_action_index": 0,
            "guard_return": 2.0,
            "branch_returns": {"0": 2.0, "1": 4.5, "3": -1.0},
        },
        {
            "guard_action_index": 1,
            "guard_return": -2.0,
            "branch_returns": {"0": -1.5, "1": -2.0, "2": 3.0},
        },
    ]

    expanded = expand_action_relative_examples(tensors, metadata, action_dim=4)

    assert expanded["row_indices"].tolist() == [0, 0, 1, 1]
    assert expanded["candidate_actions"].tolist() == [1, 3, 0, 2]
    assert expanded["raw_advantages"].tolist() == [2.5, -3.0, 0.5, 5.0]


def test_corpus_expansion_rejects_illegal_or_non_finite_branches():
    tensors = _state_tensors()
    metadata = [
        {
            "guard_action_index": 0,
            "guard_return": 2.0,
            "branch_returns": {"0": 2.0, "2": 3.0},
        },
        {
            "guard_action_index": 1,
            "guard_return": -2.0,
            "branch_returns": {"1": -2.0, "2": 3.0},
        },
    ]
    with pytest.raises(ValueError, match="illegal"):
        expand_action_relative_examples(tensors, metadata, action_dim=4)

    metadata[0]["branch_returns"] = {"0": 2.0, "1": float("nan")}
    with pytest.raises(ValueError, match="finite"):
        expand_action_relative_examples(tensors, metadata, action_dim=4)


def test_selection_abstains_below_threshold_and_masks_forbidden_before_argmax():
    residual, inputs = _fixture()
    with torch.no_grad():
        for parameter in residual.scorer.parameters():
            parameter.zero_()

    closed = residual.select_actions(**inputs)
    assert torch.equal(closed.actions, inputs["guard_actions"])
    assert closed.telemetry["intervention_count"] == 0

    with torch.no_grad():
        residual.scorer[-1].bias.fill_(0.1)
    opened = residual.select_actions(**inputs)
    assert opened.actions.tolist() == [1, 0]

    constrained = residual.select_actions(
        **inputs, forbidden_action_indices=frozenset({0, 1})
    )
    assert constrained.actions.tolist() == [3, 2]
    assert constrained.telemetry["forbidden_action_selection_count"] == 0


def test_all_alternatives_removed_preserves_exact_guard():
    residual, inputs = _fixture()
    with torch.no_grad():
        for parameter in residual.scorer.parameters():
            parameter.zero_()
        residual.scorer[-1].bias.fill_(0.1)

    selection = residual.select_actions(
        **inputs, forbidden_action_indices=frozenset({0, 1, 2, 3})
    )

    assert torch.equal(selection.actions, inputs["guard_actions"])
    assert selection.telemetry["no_allowed_alternative_count"] == 2
    assert selection.telemetry["intervention_count"] == 0


def test_scorer_training_leaves_parent_frozen():
    residual, inputs = _fixture()
    parent_before = state_dict_sha256(residual.parent.state_dict())
    predictions = residual.score_candidates(
        inputs["continuous"],
        inputs["card_ids"],
        inputs["potion_ids"],
        inputs["relic_ids"],
        inputs["action_masks"],
        inputs["guard_actions"],
        torch.tensor([1, 2]),
    )
    loss = F.smooth_l1_loss(predictions / residual.config.target_scale, torch.ones(2))
    loss.backward()

    assert torch.isfinite(loss)
    assert state_dict_sha256(residual.parent.state_dict()) == parent_before
    assert all(parameter.grad is None for parameter in residual.parent.parameters())
    assert any(parameter.grad is not None for parameter in residual.scorer.parameters())


def test_development_artifact_roundtrip_is_exact_and_source_bound():
    residual, inputs = _fixture()
    with torch.no_grad():
        residual.scorer[-1].bias.fill_(0.1)
    before = residual.select_actions(
        **inputs, forbidden_action_indices=frozenset({1})
    )
    artifact = build_development_artifact(
        residual,
        parent_checkpoint_sha256="a" * 64,
        corpus_sha256={"train": "b" * 64, "evaluation": "c" * 64},
        recipe={"training_seed": 17},
        telemetry={"fit": "fixture"},
    )
    buffer = io.BytesIO()
    torch.save(artifact, buffer)
    buffer.seek(0)
    loaded_artifact = torch.load(buffer, map_location="cpu", weights_only=False)
    restored = load_development_artifact(
        residual.parent,
        METADATA,
        loaded_artifact,
        expected_parent_checkpoint_sha256="a" * 64,
        expected_corpus_sha256={"train": "b" * 64, "evaluation": "c" * 64},
        expected_recipe={"training_seed": 17},
    )
    after = restored.select_actions(
        **inputs, forbidden_action_indices=frozenset({1})
    )

    assert torch.equal(after.actions, before.actions)
    assert torch.equal(after.residual_actions, before.residual_actions)
    assert torch.equal(after.predicted_advantages, before.predicted_advantages)
    assert state_dict_sha256(restored.scorer.state_dict()) == artifact[
        "scorer_state_dict_sha256"
    ]

    bad_artifact = copy.deepcopy(loaded_artifact)
    bad_artifact["corpus_sha256"]["train"] = "d" * 64
    with pytest.raises(ValueError, match="corpus identity"):
        load_development_artifact(
            residual.parent,
            METADATA,
            bad_artifact,
            expected_parent_checkpoint_sha256="a" * 64,
            expected_corpus_sha256={"train": "b" * 64, "evaluation": "c" * 64},
            expected_recipe={"training_seed": 17},
        )
