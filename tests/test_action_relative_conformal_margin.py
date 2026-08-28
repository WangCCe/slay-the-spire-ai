from __future__ import annotations

import copy
import io

import pytest
import torch

from spirecomm.ai.rl.v2.action_relative_conformal_margin import (
    ActionRelativeConformalConfig,
    ActionRelativeConformalMarginGate,
    build_conformal_development_artifact,
    load_conformal_development_artifact,
)
from spirecomm.ai.rl.v2.action_relative_uncertainty_ensemble import (
    ActionRelativeUncertaintyConfig,
    ActionRelativeUncertaintyEnsemble,
    build_ensemble_development_artifact,
)
from spirecomm.ai.rl.v2.network import create_dqn_v2


METADATA = {
    "network_type": "standard",
    "continuous_dim": 4,
    "action_dim": 91,
    "card_vocab": 5,
    "potion_vocab": 4,
    "relic_vocab": 3,
    "card_slots": 1,
    "potion_slots": 1,
    "relic_slots": 1,
}
MEMBER_SEEDS = (201, 202, 203, 204, 205)
ENSEMBLE_RECIPE = {"member_seeds": list(MEMBER_SEEDS)}
CORRECTIONS = {"card": 0.25, "potion": 0.75}


def _fixture() -> tuple[ActionRelativeConformalMarginGate, dict[str, torch.Tensor]]:
    torch.manual_seed(31)
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
    with torch.no_grad():
        for scorer in ensemble.member_scorers:
            for parameter in scorer.parameters():
                parameter.zero_()
            scorer[-1].bias.fill_(1.0)
    gate = ActionRelativeConformalMarginGate(
        ensemble,
        ActionRelativeConformalConfig(alpha=0.1, advantage_threshold=0.5),
        corrections=CORRECTIONS,
    )
    masks = torch.zeros((2, 91), dtype=torch.bool)
    masks[0, [0, 1, 60]] = True
    masks[1, [0, 60, 90]] = True
    alternatives = torch.zeros_like(masks)
    alternatives[0, [1, 60]] = True
    alternatives[1, [60, 90]] = True
    inputs = {
        "continuous": torch.randn(2, 4),
        "card_ids": torch.tensor([[1], [2]]),
        "potion_ids": torch.tensor([[1], [2]]),
        "relic_ids": torch.tensor([[0], [1]]),
        "action_masks": masks,
        "guard_actions": torch.tensor([0, 0]),
        "alternative_masks": alternatives,
    }
    return gate, inputs


def test_family_corrections_route_card_and_potion_scores():
    gate, inputs = _fixture()
    rows = torch.tensor([0, 0])
    stats = gate.score_candidate_statistics(
        inputs["continuous"][rows],
        inputs["card_ids"][rows],
        inputs["potion_ids"][rows],
        inputs["relic_ids"][rows],
        inputs["action_masks"][rows],
        inputs["guard_actions"][rows],
        torch.tensor([1, 60]),
    )

    assert torch.allclose(stats.raw_lower_scores, torch.ones(2))
    assert torch.allclose(stats.corrections, torch.tensor([0.25, 0.75]))
    assert torch.allclose(stats.calibrated_lower_scores, torch.tensor([0.75, 0.25]))


def test_selection_ranks_calibrated_margin_abstains_and_rejects_unsupported():
    gate, inputs = _fixture()
    selection = gate.select_actions(**inputs)

    assert selection.actions.tolist() == [1, 0]
    assert selection.gate_open.tolist() == [True, False]
    assert selection.family_corrections.tolist() == pytest.approx([0.25, 0.75])
    assert selection.telemetry["unsupported_alternative_count"] == 1

    with pytest.raises(ValueError, match="unsupported action family"):
        gate.score_candidates(
            inputs["continuous"][:1],
            inputs["card_ids"][:1],
            inputs["potion_ids"][:1],
            inputs["relic_ids"][:1],
            inputs["action_masks"][:1],
            inputs["guard_actions"][:1],
            torch.tensor([90]),
        )


def test_conformal_artifact_roundtrip_is_exact_and_split_bound():
    gate, inputs = _fixture()
    nested = build_ensemble_development_artifact(
        gate.ensemble,
        parent_checkpoint_sha256="a" * 64,
        corpus_sha256={"train": "b" * 64, "evaluation": "c" * 64},
        recipe=ENSEMBLE_RECIPE,
        bootstrap_sha256=[str(index) * 64 for index in range(1, 6)],
        telemetry={"fit": "fixture"},
    )
    recipe = {
        "ensemble_recipe": ENSEMBLE_RECIPE,
        "fit_seeds": [1, 2],
        "calibration_seeds": [3],
    }
    artifact = build_conformal_development_artifact(
        gate,
        ensemble_artifact=nested,
        recipe=recipe,
        split_sha256={"fit": "d" * 64, "calibration": "e" * 64},
        calibration_support={"card": 120, "potion": 110},
        telemetry={"calibration": "fixture"},
    )
    buffer = io.BytesIO()
    torch.save(artifact, buffer)
    buffer.seek(0)
    loaded = torch.load(buffer, map_location="cpu", weights_only=False)
    restored = load_conformal_development_artifact(
        gate.ensemble.parent,
        METADATA,
        loaded,
        expected_parent_checkpoint_sha256="a" * 64,
        expected_corpus_sha256={"train": "b" * 64, "evaluation": "c" * 64},
        expected_recipe=recipe,
        expected_split_sha256={"fit": "d" * 64, "calibration": "e" * 64},
    )
    before = gate.select_actions(**inputs)
    after = restored.select_actions(**inputs)

    assert torch.equal(after.actions, before.actions)
    assert torch.equal(after.predicted_advantages, before.predicted_advantages)
    assert torch.equal(after.raw_lower_scores, before.raw_lower_scores)
    assert torch.equal(after.family_corrections, before.family_corrections)

    bad = copy.deepcopy(loaded)
    bad["split_sha256"]["calibration"] = "f" * 64
    with pytest.raises(ValueError, match="split identity"):
        load_conformal_development_artifact(
            gate.ensemble.parent,
            METADATA,
            bad,
            expected_parent_checkpoint_sha256="a" * 64,
            expected_corpus_sha256={"train": "b" * 64, "evaluation": "c" * 64},
            expected_recipe=recipe,
            expected_split_sha256={"fit": "d" * 64, "calibration": "e" * 64},
        )
