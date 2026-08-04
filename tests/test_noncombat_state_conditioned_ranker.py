from __future__ import annotations

import copy
import json
import math

import pytest
import torch

from analysis_scripts.noncombat_policy_diagnostics import (
    DIAGNOSTIC_SCHEMA_VERSION,
    PolicyDiagnosticError,
    summarize_policy_diagnostics,
)
from analysis_scripts.noncombat_state_conditioned_ranker import (
    ARCHITECTURE_ID,
    StateConditionedCandidateRanker,
    StateConditionedRankerError,
)


def _flipping_ranker() -> StateConditionedCandidateRanker:
    model = StateConditionedCandidateRanker(input_dim=1, hidden_dim=2)
    with torch.no_grad():
        model.hidden.weight.copy_(torch.tensor([[1.0, -1.0], [-1.0, 1.0]]))
        model.hidden.bias.zero_()
        model.scorer.weight.copy_(torch.tensor([[-1.0, -1.0]]))
        model.scorer.bias.zero_()
    return model


def _card_decision(
    decision_id: str,
    *,
    selected: str = "card_reward:take:0:anger",
    take_score: float = 2.0,
    skip_score: float = 1.0,
) -> dict[str, object]:
    take = {
        "action_id": "card_reward:take:0:anger",
        "kind": "take",
        "label": "Anger",
    }
    skip = {
        "action_id": "card_reward:skip:0",
        "kind": "skip",
        "label": "Skip",
    }
    return {
        "candidate_scores": {
            take["action_id"]: take_score,
            skip["action_id"]: skip_score,
        },
        "candidates": [take, skip],
        "category": "card_reward",
        "decision_id": decision_id,
        "selected_action_id": selected,
    }


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def test_state_only_change_can_reverse_the_same_candidate_ordering():
    model = _flipping_ranker()
    candidates = torch.tensor([[0.0], [1.0]], dtype=torch.float32)
    original_candidates = candidates.clone()

    low_state_scores = model(torch.tensor([0.0]), candidates)
    high_state_scores = model(torch.tensor([1.0]), candidates)

    assert int(torch.argmax(low_state_scores).item()) == 0
    assert int(torch.argmax(high_state_scores).item()) == 1
    assert torch.equal(candidates, original_candidates)


def test_candidate_permutation_only_permutes_scores():
    model = _flipping_ranker()
    state = torch.tensor([0.25], dtype=torch.float32)
    candidates = torch.tensor([[0.0], [1.0], [0.5]], dtype=torch.float32)

    original = model(state, candidates)
    permutation = torch.tensor([2, 0, 1])
    permuted = model(state, candidates[permutation])

    assert torch.equal(permuted, original[permutation])


def test_repeated_scoring_and_matching_state_dict_round_trip_are_exact():
    model = _flipping_ranker()
    state = torch.tensor([0.75], dtype=torch.float32)
    candidates = torch.tensor([[0.0], [1.0]], dtype=torch.float32)

    first = model(state, candidates)
    second = model(state, candidates)
    restored = StateConditionedCandidateRanker(input_dim=1, hidden_dim=2)
    restored.load_state_dict(copy.deepcopy(model.state_dict()))

    assert torch.equal(first, second)
    assert torch.equal(first, restored(state, candidates))
    with pytest.raises(RuntimeError):
        StateConditionedCandidateRanker(input_dim=2, hidden_dim=2).load_state_dict(
            model.state_dict()
        )


def test_ranker_exposes_stable_cpu_architecture_metadata():
    model = StateConditionedCandidateRanker(input_dim=8)

    assert model.architecture_metadata() == {
        "architecture_id": ARCHITECTURE_ID,
        "candidate_input_dim": 8,
        "device": "cpu",
        "dtype": "float32",
        "hidden_dim": 64,
        "state_conditioned": True,
        "state_input_dim": 8,
    }


@pytest.mark.parametrize(
    ("state", "candidates", "message"),
    [
        (torch.zeros((1, 1)), torch.zeros((1, 1)), "state_features must be rank 1"),
        (torch.zeros(1), torch.zeros(1), "candidate_features must be rank 2"),
        (torch.zeros(1), torch.zeros((0, 1)), "candidate_features must be nonempty"),
        (torch.zeros(2), torch.zeros((1, 1)), "state feature width must equal 1"),
        (torch.zeros(1), torch.zeros((1, 2)), "candidate feature width must equal 1"),
        (
            torch.tensor([math.nan], dtype=torch.float32),
            torch.zeros((1, 1)),
            "state_features must be finite",
        ),
        (
            torch.zeros(1),
            torch.tensor([[math.inf]], dtype=torch.float32),
            "candidate_features must be finite",
        ),
        (
            torch.zeros(1, dtype=torch.float64),
            torch.zeros((1, 1)),
            "state_features dtype must be float32",
        ),
    ],
)
def test_ranker_rejects_invalid_tensor_boundaries(state, candidates, message):
    model = StateConditionedCandidateRanker(input_dim=1, hidden_dim=2)

    with pytest.raises(StateConditionedRankerError, match=message):
        model(state, candidates)


def test_ranker_rejects_boolean_dimensions():
    with pytest.raises(StateConditionedRankerError, match="input_dim"):
        StateConditionedCandidateRanker(input_dim=True)
    with pytest.raises(StateConditionedRankerError, match="hidden_dim"):
        StateConditionedCandidateRanker(input_dim=1, hidden_dim=False)


def test_card_reward_diagnostics_report_exact_take_saturation_and_margins():
    rows = [
        _card_decision("d1", take_score=2.0, skip_score=1.0),
        _card_decision("d2", take_score=1.2, skip_score=0.8),
        {
            "candidate_scores": {
                "card_reward:bowl:0": 0.0,
                "card_reward:skip:0": 0.5,
                "card_reward:take:0:anger": 0.5,
            },
            "candidates": [
                {
                    "action_id": "card_reward:bowl:0",
                    "kind": "bowl",
                    "label": "Singing Bowl",
                },
                {
                    "action_id": "card_reward:skip:0",
                    "kind": "skip",
                    "label": "Skip",
                },
                {
                    "action_id": "card_reward:take:0:anger",
                    "kind": "take",
                    "label": "Anger",
                },
            ],
            "category": "card_reward",
            "decision_id": "d3",
            "selected_action_id": "card_reward:take:0:anger",
        },
    ]

    summary = summarize_policy_diagnostics(rows)
    card = summary["categories"]["card_reward"]

    assert summary["schema_version"] == DIAGNOSTIC_SCHEMA_VERSION
    assert summary["decision_count"] == 3
    assert set(summary["authority"].values()) == {False}
    assert card["candidate_kind_opportunities"] == {"bowl": 1, "skip": 3, "take": 3}
    assert card["candidate_kind_occurrences"] == {"bowl": 1, "skip": 3, "take": 3}
    assert card["selected_kinds"] == {
        "take": {"count": 3, "rate": 1.0}
    }
    assert card["distinct_selected_kinds"] == ["take"]
    assert card["exact_single_kind_saturation"] is True
    assert card["single_candidate_decisions"] == 0
    assert card["card_reward"] == {
        "availability_decisions": {"bowl": 1, "skip": 3, "take": 3},
        "selections": {"bowl": 0, "skip": 0, "take": 3},
    }
    assert card["top_score_margin"] == {
        "count": 3,
        "max": 1.0,
        "mean": pytest.approx(1.4 / 3.0),
        "median": pytest.approx(0.4),
        "min": 0.0,
    }
    assert card["selected_score_margin"] == card["top_score_margin"]


def test_diagnostic_summary_is_independent_of_row_and_candidate_order():
    rows = [
        _card_decision("d1", take_score=2.0, skip_score=1.0),
        _card_decision("d2", take_score=0.25, skip_score=0.75),
    ]
    reordered = copy.deepcopy(list(reversed(rows)))
    for row in reordered:
        row["candidates"].reverse()

    assert _canonical(summarize_policy_diagnostics(rows)) == _canonical(
        summarize_policy_diagnostics(reordered)
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate_decision",
        "empty_candidates",
        "duplicate_candidate",
        "empty_kind",
        "missing_selection",
        "missing_score",
        "extra_score",
        "nonfinite_score",
    ],
)
def test_diagnostics_fail_closed_for_incomplete_rows(mutation):
    rows = [_card_decision("d1"), _card_decision("d2")]
    if mutation == "duplicate_decision":
        rows[1]["decision_id"] = "d1"
    elif mutation == "empty_candidates":
        rows[0]["candidates"] = []
        rows[0]["candidate_scores"] = {}
    elif mutation == "duplicate_candidate":
        rows[0]["candidates"].append(copy.deepcopy(rows[0]["candidates"][0]))
    elif mutation == "empty_kind":
        rows[0]["candidates"][0]["kind"] = ""
    elif mutation == "missing_selection":
        rows[0]["selected_action_id"] = "card_reward:take:0:missing"
    elif mutation == "missing_score":
        rows[0]["candidate_scores"].pop("card_reward:skip:0")
    elif mutation == "extra_score":
        rows[0]["candidate_scores"]["card_reward:take:0:extra"] = 0.0
    else:
        rows[0]["candidate_scores"]["card_reward:skip:0"] = math.nan

    with pytest.raises(PolicyDiagnosticError):
        summarize_policy_diagnostics(rows)
