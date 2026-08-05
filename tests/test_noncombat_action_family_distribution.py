from __future__ import annotations

import copy
import json
import math
import subprocess
import sys
from pathlib import Path

import pytest
import torch

from analysis_scripts.noncombat_action_family_distribution import (
    DISTRIBUTION_DTYPE,
    DISTRIBUTION_SCHEMA_VERSION,
    FAMILY_AGGREGATION,
    SCORE_DTYPE,
    ActionFamilyDistributionError,
    build_action_family_distribution,
    distribution_metadata,
    render_design_report,
)


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = (
    ROOT / "reports" / "noncombat_action_family_distribution_design_20260805.md"
)


def _candidate(action_id: str, kind: str) -> dict[str, str]:
    return {"action_id": action_id, "kind": kind}


def _family_value(distribution, family: str, values: torch.Tensor) -> float:
    index = distribution.family_order.index(family)
    return float(values[index].detach().item())


def _candidate_values(distribution, values: torch.Tensor) -> dict[str, float]:
    return {
        action_id: float(value)
        for action_id, value in zip(
            distribution.action_ids, values.detach().tolist(), strict=True
        )
    }


def test_equal_scores_remove_family_cardinality_pressure():
    candidates = [
        _candidate("take-a", "take"),
        _candidate("take-b", "take"),
        _candidate("take-c", "take"),
        _candidate("skip", "skip"),
    ]
    scores = torch.zeros(4, dtype=torch.float32)

    distribution = build_action_family_distribution(scores, candidates)

    assert distribution.family_order == ("skip", "take")
    assert torch.allclose(
        distribution.family_probabilities,
        torch.tensor([0.5, 0.5], dtype=DISTRIBUTION_DTYPE),
    )
    assert torch.allclose(
        distribution.candidate_probabilities,
        torch.tensor(
            [1.0 / 6.0, 1.0 / 6.0, 1.0 / 6.0, 0.5],
            dtype=DISTRIBUTION_DTYPE,
        ),
    )
    assert torch.allclose(
        distribution.candidate_probabilities.sum(),
        torch.tensor(1.0, dtype=DISTRIBUTION_DTYPE),
    )


@pytest.mark.parametrize("duplicate_score", [0.0, 2.0])
def test_distinct_duplicate_score_does_not_change_family_mass(duplicate_score):
    base_candidates = [
        _candidate("take-best", "take"),
        _candidate("take-low", "take"),
        _candidate("skip", "skip"),
    ]
    base_scores = torch.tensor([2.0, 0.0, 1.0], dtype=torch.float32)
    base = build_action_family_distribution(base_scores, base_candidates)

    duplicate_candidates = [
        *base_candidates,
        _candidate("take-duplicate", "take"),
    ]
    duplicate_scores = torch.tensor(
        [2.0, 0.0, 1.0, duplicate_score], dtype=torch.float32
    )
    duplicated = build_action_family_distribution(
        duplicate_scores, duplicate_candidates
    )

    assert torch.equal(duplicated.family_logits, base.family_logits)
    assert torch.equal(duplicated.family_probabilities, base.family_probabilities)
    assert torch.equal(duplicated.family_entropy, base.family_entropy)
    assert not torch.equal(
        duplicated.conditional_log_probabilities[:2],
        base.conditional_log_probabilities[:2],
    )


def test_candidate_permutation_preserves_family_values_and_follows_identity():
    candidates = [
        _candidate("take-a", "take"),
        _candidate("skip", "skip"),
        _candidate("take-b", "take"),
        _candidate("bowl", "bowl"),
    ]
    scores = torch.tensor([0.25, 0.75, 1.5, -0.5], dtype=torch.float32)
    original = build_action_family_distribution(scores, candidates)
    permutation = torch.tensor([3, 0, 2, 1])
    permuted_candidates = [candidates[index] for index in permutation.tolist()]
    permuted = build_action_family_distribution(
        scores[permutation], permuted_candidates
    )

    assert permuted.family_order == original.family_order
    assert torch.equal(permuted.family_logits, original.family_logits)
    assert torch.equal(permuted.family_probabilities, original.family_probabilities)
    assert torch.equal(permuted.family_entropy, original.family_entropy)
    assert torch.equal(permuted.conditional_entropy, original.conditional_entropy)
    assert torch.equal(permuted.joint_entropy, original.joint_entropy)
    assert _candidate_values(
        permuted, permuted.candidate_probabilities
    ) == _candidate_values(original, original.candidate_probabilities)
    assert _candidate_values(
        permuted, permuted.candidate_log_probabilities
    ) == _candidate_values(original, original.candidate_log_probabilities)


def test_single_family_is_the_original_candidate_softmax():
    candidates = [
        _candidate("route-a", "map_node"),
        _candidate("route-b", "map_node"),
        _candidate("route-c", "map_node"),
    ]
    scores = torch.tensor([-1.0, 0.5, 2.0], dtype=torch.float32)
    distribution = build_action_family_distribution(scores, candidates)

    assert distribution.family_order == ("map_node",)
    assert torch.equal(
        distribution.family_probabilities,
        torch.ones(1, dtype=DISTRIBUTION_DTYPE),
    )
    assert torch.allclose(
        distribution.candidate_probabilities,
        torch.softmax(scores.to(dtype=DISTRIBUTION_DTYPE), dim=0),
    )
    assert torch.allclose(
        distribution.candidate_log_probabilities,
        torch.log_softmax(scores.to(dtype=DISTRIBUTION_DTYPE), dim=0),
    )
    assert float(distribution.family_entropy.item()) == 0.0
    assert torch.allclose(
        distribution.conditional_entropy, distribution.joint_entropy
    )


def test_entropy_decomposition_and_probability_normalization_are_exactly_exposed():
    candidates = [
        _candidate("take-a", "take"),
        _candidate("take-b", "take"),
        _candidate("skip", "skip"),
        _candidate("bowl", "bowl"),
    ]
    scores = torch.tensor([2.0, -0.5, 0.25, 1.0], dtype=torch.float32)
    distribution = build_action_family_distribution(scores, candidates)

    assert torch.allclose(
        distribution.family_probabilities.sum(),
        torch.tensor(1.0, dtype=DISTRIBUTION_DTYPE),
    )
    assert torch.allclose(
        distribution.candidate_probabilities.sum(),
        torch.tensor(1.0, dtype=DISTRIBUTION_DTYPE),
    )
    assert torch.allclose(
        distribution.candidate_probabilities,
        distribution.candidate_log_probabilities.exp(),
    )
    assert torch.allclose(
        distribution.joint_entropy,
        distribution.family_entropy + distribution.conditional_entropy,
        atol=1e-6,
        rtol=1e-6,
    )
    direct_joint = -(
        distribution.candidate_probabilities
        * distribution.candidate_log_probabilities
    ).sum()
    assert torch.allclose(distribution.joint_entropy, direct_joint)


def test_extreme_finite_float32_scores_still_produce_finite_outputs():
    limit = torch.finfo(torch.float32).max
    scores = torch.tensor(
        [limit, -limit, 0.0, -limit], dtype=torch.float32, requires_grad=True
    )
    candidates = [
        _candidate("take-best", "take"),
        _candidate("take-low", "take"),
        _candidate("skip", "skip"),
        _candidate("skip-low", "skip"),
    ]

    distribution = build_action_family_distribution(scores, candidates)

    for value in (
        distribution.family_logits,
        distribution.family_log_probabilities,
        distribution.family_probabilities,
        distribution.conditional_log_probabilities,
        distribution.candidate_log_probabilities,
        distribution.candidate_probabilities,
        distribution.family_entropy,
        distribution.conditional_entropy,
        distribution.joint_entropy,
    ):
        assert value.dtype == DISTRIBUTION_DTYPE
        assert torch.isfinite(value).all().item()
    assert torch.allclose(
        distribution.family_probabilities.sum(),
        torch.tensor(1.0, dtype=DISTRIBUTION_DTYPE),
    )
    assert torch.allclose(
        distribution.candidate_probabilities.sum(),
        torch.tensor(1.0, dtype=DISTRIBUTION_DTYPE),
    )
    assert torch.allclose(
        distribution.joint_entropy,
        distribution.family_entropy + distribution.conditional_entropy,
    )
    for index, family in enumerate(distribution.candidate_families):
        family_index = distribution.family_order.index(family)
        assert torch.equal(
            distribution.candidate_log_probabilities[index],
            distribution.family_log_probabilities[family_index]
            + distribution.conditional_log_probabilities[index],
        )

    distribution.candidate_log_probabilities[3].backward()
    assert scores.grad is not None
    assert torch.isfinite(scores.grad).all().item()
    assert torch.count_nonzero(scores.grad).item() >= 2


def test_selected_log_probability_and_entropy_terms_have_finite_gradients():
    candidates = [
        _candidate("take-a", "take"),
        _candidate("take-b", "take"),
        _candidate("skip", "skip"),
    ]
    scores = torch.tensor([2.0, 0.0, 1.0], dtype=torch.float32, requires_grad=True)
    distribution = build_action_family_distribution(scores, candidates)

    loss = -distribution.candidate_log_probabilities[1]
    loss = loss - 0.1 * distribution.family_entropy
    loss = loss - 0.05 * distribution.conditional_entropy
    loss.backward()

    assert scores.grad is not None
    assert torch.isfinite(scores.grad).all().item()
    assert torch.count_nonzero(scores.grad).item() == 3


def test_tied_family_maxima_split_gradients_permutation_equivariantly():
    candidates = [
        _candidate("take-a", "take"),
        _candidate("take-b", "take"),
        _candidate("skip", "skip"),
    ]
    scores = torch.tensor([0.0, 0.0, 1.0], dtype=torch.float32, requires_grad=True)
    distribution = build_action_family_distribution(scores, candidates)
    take_index = distribution.family_order.index("take")
    distribution.family_logits[take_index].backward()

    assert torch.equal(scores.grad, torch.tensor([0.5, 0.5, 0.0]))


def test_sources_are_not_mutated_and_identity_alignment_is_retained():
    candidates = [
        {"action_id": "take", "kind": "take", "ignored": {"slot": 1}},
        {"action_id": "skip", "kind": "skip", "ignored": {"slot": 2}},
    ]
    scores = torch.tensor([1.0, 0.0], dtype=torch.float32)
    original_candidates = copy.deepcopy(candidates)
    original_scores = scores.clone()

    distribution = build_action_family_distribution(scores, candidates)

    assert candidates == original_candidates
    assert torch.equal(scores, original_scores)
    assert distribution.action_ids == ("take", "skip")
    assert distribution.candidate_families == ("take", "skip")


@pytest.mark.parametrize(
    ("scores", "candidates", "message"),
    [
        ([], [_candidate("take", "take")], "scores must be a tensor"),
        (
            torch.zeros((1, 1), dtype=torch.float32),
            [_candidate("take", "take")],
            "rank 1",
        ),
        (torch.zeros(0, dtype=torch.float32), [], "nonempty"),
        (
            torch.zeros(1, dtype=torch.float64),
            [_candidate("take", "take")],
            "float32",
        ),
        (
            torch.tensor([math.nan], dtype=torch.float32),
            [_candidate("take", "take")],
            "finite",
        ),
        (
            torch.zeros(2, dtype=torch.float32),
            [_candidate("take", "take")],
            "align",
        ),
        (
            torch.zeros(1, dtype=torch.float32),
            "not-a-sequence",
            "candidates",
        ),
        (
            torch.zeros(1, dtype=torch.float32),
            [{}],
            "action_id",
        ),
        (
            torch.zeros(1, dtype=torch.float32),
            [_candidate("take", "")],
            "kind",
        ),
        (
            torch.zeros(2, dtype=torch.float32),
            [_candidate("same", "take"), _candidate("same", "skip")],
            "duplicate",
        ),
    ],
)
def test_invalid_boundaries_fail_closed(scores, candidates, message):
    with pytest.raises(ActionFamilyDistributionError, match=message):
        build_action_family_distribution(scores, candidates)


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA is unavailable")
def test_non_cpu_scores_fail_closed_when_cuda_is_available():
    with pytest.raises(ActionFamilyDistributionError, match="CPU"):
        build_action_family_distribution(
            torch.zeros(1, dtype=torch.float32, device="cuda"),
            [_candidate("take", "take")],
        )


def test_metadata_is_stable_json_compatible_and_authority_free():
    metadata = distribution_metadata()

    assert metadata == {
        "authority": {
            "experiment_execution": False,
            "formal_rl": False,
            "gameplay": False,
            "model_loading": False,
            "native_loading": False,
            "policy_promotion": False,
            "qualification": False,
            "seed_access": False,
            "training": False,
        },
        "candidate_identity_field": "action_id",
        "device": "cpu",
        "distribution_dtype": "float64",
        "entropy_decomposition": "joint=family+expected_conditional",
        "family_aggregation": FAMILY_AGGREGATION,
        "family_identity_field": "kind",
        "schema_version": DISTRIBUTION_SCHEMA_VERSION,
        "score_dtype": "float32",
    }
    assert set(metadata["authority"].values()) == {False}
    assert json.loads(json.dumps(metadata, sort_keys=True)) == metadata
    assert distribution_metadata() == metadata
    assert SCORE_DTYPE == torch.float32
    assert DISTRIBUTION_DTYPE == torch.float64


def test_import_does_not_pull_in_simulator_or_experiment_surfaces():
    code = (
        "import json,sys;"
        "import analysis_scripts.noncombat_action_family_distribution;"
        "print(json.dumps({"
        "'adapter':'analysis_scripts.noncombat_simulator_adapter' in sys.modules,"
        "'experiment':"
        "'analysis_scripts.noncombat_state_conditioned_simulator_learning_experiment'"
        " in sys.modules,"
        "'native':'sts_lightspeed_noncombat_adapter' in sys.modules},sort_keys=True))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(completed.stdout) == {
        "adapter": False,
        "experiment": False,
        "native": False,
    }


def test_design_report_is_deterministic_complete_and_checked_in():
    first = render_design_report()
    second = render_design_report()

    assert first == second
    assert REPORT_PATH.read_text(encoding="utf-8") == first
    for heading in (
        "# Non-Combat Action-Family Distribution Design",
        "## Evidence Boundary",
        "## Selected Factorization",
        "## Synthetic Invariants",
        "## Alternatives",
        "## Risks And Open Questions",
        "## Authority",
    ):
        assert heading in first
    assert "max-candidate-score-v1" in first
    assert "0.5" in first
    assert "Opposite finite float32 limits retain finite outputs: `true`" in first
    assert "experiment_execution: false" in first
    assert "training: false" in first
    assert "timestamp" not in first.lower()
