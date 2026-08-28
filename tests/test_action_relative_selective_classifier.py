from __future__ import annotations

import copy

import pytest
import torch

from spirecomm.ai.rl.v2.action_relative_selective_classifier import (
    BENEFICIAL_CLASS,
    NEUTRAL_CLASS,
    SEVERE_CLASS,
    ActionRelativeSelectiveClassifier,
    ActionRelativeSelectiveConfig,
    build_class_balanced_sample_plan,
    build_replacement_sample_plan,
    build_selective_development_artifact,
    build_supported_selective_corpus,
    build_within_state_ranking_pairs,
    classify_advantages,
    finite_sample_negative_threshold,
    load_selective_development_artifact,
)
from spirecomm.ai.rl.v2.latent_gated_adapter import state_dict_sha256
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


def _corpus() -> tuple[dict[str, torch.Tensor], list[dict]]:
    tensors = {
        "continuous": torch.arange(12, dtype=torch.float32).reshape(3, 4),
        "card_ids": torch.tensor([[1], [2], [3]]),
        "potion_ids": torch.tensor([[1], [2], [3]]),
        "relic_ids": torch.tensor([[0], [1], [2]]),
        "action_masks": torch.ones((3, 91), dtype=torch.bool),
        "guard_actions": torch.zeros(3, dtype=torch.long),
    }
    metadata = [
        {
            "seed": 1,
            "guard_action_index": 0,
            "guard_return": 0.0,
            "branch_returns": {"0": 0.0, "1": -0.5001, "60": 0.5, "90": 4.0},
        },
        {
            "seed": 2,
            "guard_action_index": 0,
            "guard_return": 0.0,
            "branch_returns": {"0": 0.0, "90": 2.0},
        },
        {
            "seed": 3,
            "guard_action_index": 0,
            "guard_return": 1.0,
            "branch_returns": {"0": 1.0, "2": 0.5, "61": 1.4999},
        },
    ]
    return tensors, metadata


def _classifier(*, threshold: float = 0.0) -> ActionRelativeSelectiveClassifier:
    torch.manual_seed(11)
    parent = create_dqn_v2(device="cpu", **METADATA)
    return ActionRelativeSelectiveClassifier(
        parent,
        METADATA,
        ActionRelativeSelectiveConfig(hidden_dim=8),
        selection_threshold=threshold,
    )


def test_supported_corpus_filters_rows_and_labels_exact_boundaries():
    tensors, metadata = _corpus()

    corpus = build_supported_selective_corpus(tensors, metadata)

    assert corpus["source_row_indices"].tolist() == [0, 2]
    assert corpus["excluded_unsupported_only_row_count"] == 1
    assert corpus["tensors"]["continuous"][:, 0].tolist() == [0.0, 8.0]
    assert corpus["pair_row_indices"].tolist() == [0, 0, 1, 1]
    assert corpus["candidate_actions"].tolist() == [1, 60, 2, 61]
    assert corpus["labels"].tolist() == [
        SEVERE_CLASS,
        BENEFICIAL_CLASS,
        NEUTRAL_CLASS,
        NEUTRAL_CLASS,
    ]
    assert classify_advantages(torch.tensor([-0.5001, -0.5, 0.4999, 0.5])).tolist() == [
        SEVERE_CLASS,
        NEUTRAL_CLASS,
        NEUTRAL_CLASS,
        BENEFICIAL_CLASS,
    ]

    bad_metadata = copy.deepcopy(metadata)
    bad_metadata[0]["branch_returns"]["91"] = 1.0
    with pytest.raises(ValueError, match="outside action space"):
        build_supported_selective_corpus(tensors, bad_metadata)


def test_evidence_selection_opens_and_abstains_at_immutable_threshold():
    tensors, metadata = _corpus()
    corpus = build_supported_selective_corpus(tensors, metadata)
    classifier = _classifier(threshold=1.0)
    with torch.no_grad():
        for parameter in classifier.classifier.parameters():
            parameter.zero_()
        classifier.classifier[-1].bias.copy_(torch.tensor([0.0, 0.0, 2.0]))

    selection = classifier.select_actions(
        **corpus["tensors"],
        alternative_masks=corpus["alternative_masks"],
        forbidden_action_indices=frozenset({90}),
    )

    assert selection.actions.tolist() == [1, 2]
    assert selection.gate_open.tolist() == [True, True]
    assert selection.evidence_scores.tolist() == pytest.approx(
        [2.0 - torch.log(torch.tensor(2.0)).item()] * 2
    )

    abstaining = _classifier(threshold=2.0)
    abstaining.classifier.load_state_dict(classifier.classifier.state_dict())
    closed = abstaining.select_actions(
        **corpus["tensors"],
        alternative_masks=corpus["alternative_masks"],
        forbidden_action_indices=frozenset({90}),
    )
    assert closed.actions.tolist() == [0, 0]
    assert closed.gate_open.tolist() == [False, False]


def test_sampling_ranking_and_frozen_parent_are_deterministic():
    labels = torch.tensor(
        [SEVERE_CLASS, SEVERE_CLASS, NEUTRAL_CLASS, NEUTRAL_CLASS,
         BENEFICIAL_CLASS, BENEFICIAL_CLASS]
    )
    first = build_class_balanced_sample_plan(
        labels, updates=4, samples_per_class=3, seed=101
    )
    second = build_class_balanced_sample_plan(
        labels, updates=4, samples_per_class=3, seed=101
    )
    assert torch.equal(first, second)
    for class_index in range(3):
        assert labels[first[:, class_index]].eq(class_index).all()

    ranking_pairs = build_within_state_ranking_pairs(
        torch.tensor([0, 0, 0, 1, 1]),
        torch.tensor(
            [BENEFICIAL_CLASS, NEUTRAL_CLASS, SEVERE_CLASS,
             NEUTRAL_CLASS, BENEFICIAL_CLASS]
        ),
    )
    assert ranking_pairs.tolist() == [[0, 1], [0, 2], [4, 3]]
    assert torch.equal(
        build_replacement_sample_plan(
            3, updates=4, samples_per_update=2, seed=202
        ),
        build_replacement_sample_plan(
            3, updates=4, samples_per_update=2, seed=202
        ),
    )

    classifier = _classifier()
    tensors, metadata = _corpus()
    corpus = build_supported_selective_corpus(tensors, metadata)
    pair_rows = corpus["pair_row_indices"]
    parent_before = state_dict_sha256(classifier.parent.state_dict())
    logits = classifier.score_candidate_logits(
        **{name: value[pair_rows] for name, value in corpus["tensors"].items()},
        candidate_actions=corpus["candidate_actions"],
    )
    torch.nn.functional.cross_entropy(logits, corpus["labels"]).backward()
    assert all(parameter.grad is None for parameter in classifier.parent.parameters())
    assert state_dict_sha256(classifier.parent.state_dict()) == parent_before


def test_finite_sample_negative_threshold_uses_higher_conformal_rank():
    evidence = torch.arange(21, dtype=torch.float32)
    labels = torch.tensor([NEUTRAL_CLASS] * 20 + [BENEFICIAL_CLASS])

    threshold, rank, negative_count = finite_sample_negative_threshold(
        evidence, labels, quantile=0.95
    )

    assert threshold == 19.0
    assert rank == 20
    assert negative_count == 20


def test_development_artifact_roundtrip_is_exact_and_source_bound():
    classifier = _classifier(threshold=1.25)
    artifact = build_selective_development_artifact(
        classifier,
        parent_checkpoint_sha256="a" * 64,
        corpus_sha256={"train": "b" * 64, "evaluation": "c" * 64},
        recipe={"architecture": "fixture"},
        split_sha256={"fit": "d" * 64, "calibration": "e" * 64},
        class_support={"severe": 3, "neutral": 4, "beneficial": 5},
        ranking_support=6,
        sampling_plan_sha256="f" * 64,
        telemetry={"fit": "fixture"},
    )

    loaded = load_selective_development_artifact(
        artifact,
        parent=classifier.parent,
        expected_metadata=METADATA,
        expected_parent_checkpoint_sha256="a" * 64,
        expected_corpus_sha256={"train": "b" * 64, "evaluation": "c" * 64},
        expected_recipe={"architecture": "fixture"},
        expected_split_sha256={"fit": "d" * 64, "calibration": "e" * 64},
        expected_sampling_plan_sha256="f" * 64,
    )

    tensors, metadata = _corpus()
    corpus = build_supported_selective_corpus(tensors, metadata)
    rows = corpus["pair_row_indices"]
    arguments = {
        name: corpus["tensors"][name][rows]
        for name in (
            "continuous",
            "card_ids",
            "potion_ids",
            "relic_ids",
            "action_masks",
            "guard_actions",
        )
    }
    expected = classifier.score_candidate_logits(
        **arguments, candidate_actions=corpus["candidate_actions"]
    )
    actual = loaded.score_candidate_logits(
        **arguments, candidate_actions=corpus["candidate_actions"]
    )
    assert torch.equal(actual, expected)

    bad = copy.deepcopy(artifact)
    bad["selection_threshold"] = 1.0
    with pytest.raises(ValueError):
        load_selective_development_artifact(
            bad,
            parent=classifier.parent,
            expected_metadata=METADATA,
            expected_parent_checkpoint_sha256="a" * 64,
            expected_corpus_sha256={"train": "b" * 64, "evaluation": "c" * 64},
            expected_recipe={"architecture": "fixture"},
            expected_split_sha256={"fit": "d" * 64, "calibration": "e" * 64},
            expected_sampling_plan_sha256="f" * 64,
        )
