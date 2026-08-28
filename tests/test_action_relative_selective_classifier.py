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
    _binding_sha256,
    build_class_balanced_sample_plan,
    build_replacement_sample_plan,
    build_selective_development_artifact,
    build_supported_selective_corpus,
    build_within_state_ranking_pairs,
    classify_advantages,
    finite_sample_negative_threshold,
    load_selective_development_artifact,
)
from spirecomm.ai.rl.v2 import action_space
from spirecomm.ai.rl.v2.latent_gated_adapter import state_dict_sha256
from spirecomm.ai.rl.v2.network import create_dqn_v2
from spirecomm.ai.rl.v2.state_encoder import StateEncoderV2


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


def _semantic_classifier() -> ActionRelativeSelectiveClassifier:
    metadata = {
        **METADATA,
        "continuous_dim": StateEncoderV2.CONTINUOUS_DIM,
        "card_slots": StateEncoderV2.CARD_SLOTS,
        "potion_slots": StateEncoderV2.POTION_SLOTS,
        "relic_slots": StateEncoderV2.RELIC_SLOTS,
    }
    torch.manual_seed(12)
    parent = create_dqn_v2(device="cpu", **metadata)
    return ActionRelativeSelectiveClassifier(
        parent,
        metadata,
        ActionRelativeSelectiveConfig(hidden_dim=8, include_item_semantics=True),
        selection_threshold=0.0,
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


def test_item_semantics_extract_exact_candidate_and_guard_slots():
    classifier = _semantic_classifier()
    continuous = torch.zeros((2, StateEncoderV2.CONTINUOUS_DIM))
    hand_offset = (
        StateEncoderV2.PLAYER_FEATURES
        + StateEncoderV2.MONSTER_SLOTS * StateEncoderV2.MONSTER_FEATURES
    )
    card_local = torch.arange(
        2 * StateEncoderV2.CARD_SLOTS * StateEncoderV2.HAND_FEATURES,
        dtype=torch.float32,
    ).reshape(2, StateEncoderV2.CARD_SLOTS, StateEncoderV2.HAND_FEATURES)
    continuous[
        :, hand_offset : hand_offset
        + StateEncoderV2.CARD_SLOTS * StateEncoderV2.HAND_FEATURES
    ] = card_local.reshape(2, -1)
    card_ids = torch.tensor(
        [[1, 2, 3, 4, 1, 2, 3, 4, 1, 2], [2, 3, 4, 1, 2, 3, 4, 1, 2, 3]]
    )
    potion_ids = torch.tensor([[1, 2, 3, 1, 2], [3, 2, 1, 3, 2]])
    relic_ids = torch.zeros((2, StateEncoderV2.RELIC_SLOTS), dtype=torch.long)
    action_masks = torch.zeros((2, 91), dtype=torch.bool)
    guard_actions = torch.tensor(
        [
            action_space.encode_use_potion(1, 4),
            action_space.encode_play_card(1, 0),
        ]
    )
    candidate_actions = torch.tensor(
        [
            action_space.encode_play_card(2, 3),
            action_space.encode_use_potion(0, 2),
        ]
    )
    rows = torch.arange(2)
    action_masks[rows, guard_actions] = True
    action_masks[rows, candidate_actions] = True

    semantic = classifier.item_semantic_features(
        continuous,
        card_ids,
        potion_ids,
        relic_ids,
        action_masks,
        guard_actions,
        candidate_actions,
    )

    card_dim = classifier.parent.card_embedding.embedding_dim
    potion_dim = classifier.parent.potion_embedding.embedding_dim
    cursor = 0
    candidate_card = semantic[:, cursor : cursor + card_dim]
    cursor += card_dim
    candidate_potion = semantic[:, cursor : cursor + potion_dim]
    cursor += potion_dim
    guard_card = semantic[:, cursor : cursor + card_dim]
    cursor += card_dim
    guard_potion = semantic[:, cursor : cursor + potion_dim]
    cursor += potion_dim
    candidate_local = semantic[:, cursor : cursor + StateEncoderV2.HAND_FEATURES]
    cursor += StateEncoderV2.HAND_FEATURES
    guard_local = semantic[:, cursor : cursor + StateEncoderV2.HAND_FEATURES]
    cursor += StateEncoderV2.HAND_FEATURES
    candidate_family = semantic[:, cursor : cursor + 2]
    cursor += 2
    guard_family = semantic[:, cursor : cursor + 2]
    cursor += 2
    candidate_slot = semantic[:, cursor : cursor + StateEncoderV2.CARD_SLOTS]
    cursor += StateEncoderV2.CARD_SLOTS
    guard_slot = semantic[:, cursor : cursor + StateEncoderV2.CARD_SLOTS]
    cursor += StateEncoderV2.CARD_SLOTS
    candidate_target = semantic[:, cursor : cursor + action_space.TARGET_SLOTS]
    cursor += action_space.TARGET_SLOTS
    guard_target = semantic[:, cursor : cursor + action_space.TARGET_SLOTS]
    cursor += action_space.TARGET_SLOTS
    assert cursor == classifier.item_semantic_dim

    assert torch.equal(
        candidate_card[0], classifier.parent.card_embedding(card_ids[0, 2])
    )
    assert not bool(candidate_card[1].any())
    assert not bool(candidate_potion[0].any())
    assert torch.equal(
        candidate_potion[1], classifier.parent.potion_embedding(potion_ids[1, 0])
    )
    assert not bool(guard_card[0].any())
    assert torch.equal(guard_card[1], classifier.parent.card_embedding(card_ids[1, 1]))
    assert torch.equal(guard_potion[0], classifier.parent.potion_embedding(potion_ids[0, 1]))
    assert not bool(guard_potion[1].any())
    assert torch.equal(candidate_local[0], card_local[0, 2])
    assert not bool(candidate_local[1].any())
    assert not bool(guard_local[0].any())
    assert torch.equal(guard_local[1], card_local[1, 1])
    assert candidate_family.tolist() == [[1.0, 0.0], [0.0, 1.0]]
    assert guard_family.tolist() == [[0.0, 1.0], [1.0, 0.0]]
    assert candidate_slot.argmax(dim=1).tolist() == [2, 0]
    assert guard_slot.argmax(dim=1).tolist() == [1, 1]
    assert candidate_target.argmax(dim=1).tolist() == [3, 2]
    assert guard_target.argmax(dim=1).tolist() == [4, 0]


def test_legacy_artifact_without_item_semantic_config_stays_exact():
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
    legacy = copy.deepcopy(artifact)
    assert legacy["config"].pop("include_item_semantics") is False
    legacy["binding_sha256"] = _binding_sha256(
        {
            name: value
            for name, value in legacy.items()
            if name
            not in {"classifier_state_dict", "telemetry", "binding_sha256"}
        }
    )

    loaded = load_selective_development_artifact(
        legacy,
        parent=classifier.parent,
        expected_metadata=METADATA,
        expected_parent_checkpoint_sha256="a" * 64,
        expected_corpus_sha256={"train": "b" * 64, "evaluation": "c" * 64},
        expected_recipe={"architecture": "fixture"},
        expected_split_sha256={"fit": "d" * 64, "calibration": "e" * 64},
        expected_sampling_plan_sha256="f" * 64,
    )

    assert loaded.config.include_item_semantics is False
    assert loaded.feature_dim == classifier.feature_dim
    assert state_dict_sha256(loaded.classifier.state_dict()) == state_dict_sha256(
        classifier.classifier.state_dict()
    )


def test_item_semantic_artifact_roundtrip_preserves_feature_head():
    classifier = _semantic_classifier()
    artifact = build_selective_development_artifact(
        classifier,
        parent_checkpoint_sha256="1" * 64,
        corpus_sha256={"train": "2" * 64, "evaluation": "3" * 64},
        recipe={"architecture": "item-semantic-fixture"},
        split_sha256={"fit": "4" * 64, "calibration": "5" * 64},
        class_support={"severe": 6, "neutral": 7, "beneficial": 8},
        ranking_support=9,
        sampling_plan_sha256="6" * 64,
        telemetry={"fit": "item-semantic-fixture"},
    )
    restored = load_selective_development_artifact(
        artifact,
        parent=classifier.parent,
        expected_metadata=classifier.metadata,
        expected_parent_checkpoint_sha256="1" * 64,
        expected_corpus_sha256={"train": "2" * 64, "evaluation": "3" * 64},
        expected_recipe={"architecture": "item-semantic-fixture"},
        expected_split_sha256={"fit": "4" * 64, "calibration": "5" * 64},
        expected_sampling_plan_sha256="6" * 64,
    )
    continuous = torch.zeros((1, StateEncoderV2.CONTINUOUS_DIM))
    card_ids = torch.ones((1, StateEncoderV2.CARD_SLOTS), dtype=torch.long)
    potion_ids = torch.ones((1, StateEncoderV2.POTION_SLOTS), dtype=torch.long)
    relic_ids = torch.zeros((1, StateEncoderV2.RELIC_SLOTS), dtype=torch.long)
    masks = torch.zeros((1, 91), dtype=torch.bool)
    masks[0, [0, 6]] = True
    arguments = {
        "continuous": continuous,
        "card_ids": card_ids,
        "potion_ids": potion_ids,
        "relic_ids": relic_ids,
        "action_masks": masks,
        "guard_actions": torch.tensor([0]),
        "candidate_actions": torch.tensor([6]),
    }

    assert restored.config.include_item_semantics is True
    assert restored.item_semantic_dim == classifier.item_semantic_dim
    assert torch.equal(
        restored.score_candidate_logits(**arguments),
        classifier.score_candidate_logits(**arguments),
    )


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
