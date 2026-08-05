from __future__ import annotations

import copy
import inspect
import json
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import MappingProxyType
from typing import get_args, get_origin, get_type_hints

import pytest
import torch

from analysis_scripts import noncombat_hierarchical_policy_objective as objective
from analysis_scripts.noncombat_hierarchical_policy_objective import (
    HierarchicalPolicyObjectiveError,
    build_hierarchical_policy_terms,
    objective_metadata,
    render_design_report,
)


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = (
    ROOT
    / "reports"
    / "noncombat_hierarchical_policy_objective_contract_20260806.md"
)


def _candidate(action_id: str, kind: str) -> dict[str, str]:
    return {"action_id": action_id, "kind": kind}


def _multi_family_fixture() -> tuple[torch.Tensor, list[dict[str, str]]]:
    return (
        torch.tensor([2.0, 0.0, 1.0], dtype=torch.float32, requires_grad=True),
        [
            _candidate("take-best", "take"),
            _candidate("take-low", "take"),
            _candidate("skip", "skip"),
        ],
    )


def test_selected_terms_preserve_exact_hierarchical_identity_and_alignment():
    scores, candidates = _multi_family_fixture()

    terms = build_hierarchical_policy_terms(scores, candidates, "take-low")

    assert terms.action_ids == ("take-best", "take-low", "skip")
    assert terms.selected_action_id == "take-low"
    assert terms.selected_index == 1
    assert terms.selected_family == "take"
    assert terms.family_order == ("skip", "take")
    assert terms.selected_family_index == 1
    assert torch.equal(
        terms.selected_joint_log_probability,
        terms.selected_family_log_probability
        + terms.selected_conditional_log_probability,
    )
    assert all(
        value.dtype == torch.float64 and value.device.type == "cpu"
        for value in (
            terms.selected_family_log_probability,
            terms.selected_conditional_log_probability,
            terms.selected_joint_log_probability,
            terms.family_entropy,
            terms.conditional_entropy,
            terms.joint_entropy,
        )
    )


@pytest.mark.parametrize("selected", [None, "", "missing", 7])
def test_invalid_selected_identity_fails_closed(selected: object):
    scores, candidates = _multi_family_fixture()

    with pytest.raises(
        HierarchicalPolicyObjectiveError, match="selected_action_id"
    ):
        build_hierarchical_policy_terms(scores, candidates, selected)  # type: ignore[arg-type]


def test_distribution_validation_is_not_bypassed():
    scores, candidates = _multi_family_fixture()
    candidates[1]["action_id"] = "take-best"

    with pytest.raises(HierarchicalPolicyObjectiveError, match="duplicate"):
        build_hierarchical_policy_terms(scores, candidates, "take-best")


def test_each_log_probability_and_entropy_term_retains_finite_gradients():
    scores, candidates = _multi_family_fixture()
    terms = build_hierarchical_policy_terms(scores, candidates, "take-low")

    exposed_terms = (
        terms.selected_family_log_probability,
        terms.selected_conditional_log_probability,
        terms.selected_joint_log_probability,
        terms.family_entropy,
        terms.conditional_entropy,
        terms.joint_entropy,
    )
    gradients = [
        torch.autograd.grad(term, scores, retain_graph=True)[0]
        for term in exposed_terms
    ]

    assert all(term.requires_grad for term in exposed_terms)
    assert all(torch.isfinite(gradient).all() for gradient in gradients)
    assert torch.allclose(
        terms.joint_entropy,
        terms.family_entropy + terms.conditional_entropy,
        atol=1e-12,
        rtol=1e-12,
    )


def test_selected_scalar_terms_are_permutation_invariant_by_identity():
    scores, candidates = _multi_family_fixture()
    original = build_hierarchical_policy_terms(scores, candidates, "take-low")
    permutation = [2, 0, 1]
    permuted_scores = scores.detach()[permutation].clone().requires_grad_(True)
    permuted_candidates = [copy.deepcopy(candidates[index]) for index in permutation]

    permuted = build_hierarchical_policy_terms(
        permuted_scores, permuted_candidates, "take-low"
    )

    for name in (
        "selected_family_log_probability",
        "selected_conditional_log_probability",
        "selected_joint_log_probability",
        "family_entropy",
        "conditional_entropy",
        "joint_entropy",
    ):
        assert torch.equal(getattr(original, name), getattr(permuted, name))
    assert permuted.selected_index == 2


def test_one_family_fallback_retains_conditional_objective_and_entropy():
    scores = torch.tensor([-1.0, 0.5, 2.0], dtype=torch.float32, requires_grad=True)
    candidates = [
        _candidate("route-a", "map_node"),
        _candidate("route-b", "map_node"),
        _candidate("route-c", "map_node"),
    ]

    terms = build_hierarchical_policy_terms(scores, candidates, "route-b")

    assert terms.selected_family_log_probability.item() == 0.0
    assert terms.family_entropy.item() == 0.0
    assert torch.equal(
        terms.selected_joint_log_probability,
        terms.selected_conditional_log_probability,
    )
    assert terms.conditional_entropy.item() > 0.0
    assert torch.equal(terms.joint_entropy, terms.conditional_entropy)


def test_unique_score_greedy_action_uses_raw_score_and_matches_two_stage():
    scores, candidates = _multi_family_fixture()

    terms = build_hierarchical_policy_terms(scores, candidates, "skip")

    assert terms.score_greedy_action_ids == ("take-best",)
    assert terms.unique_score_greedy_action_id == "take-best"
    assert terms.two_stage_score_greedy_action_ids == ("take-best",)
    assert terms.unique_two_stage_score_greedy_action_id == "take-best"
    assert not any("joint" in name and "greedy" in name for name in terms.__dataclass_fields__)


@pytest.mark.parametrize(
    "scores",
    (
        [1.0, 1.0, 0.0],
        [1.0, 0.0, 1.0],
    ),
)
def test_score_ties_are_complete_sorted_and_not_broken(scores: list[float]):
    candidates = [
        _candidate("z-action", "take"),
        _candidate("a-action", "take"),
        _candidate("m-action", "skip"),
    ]

    terms = build_hierarchical_policy_terms(
        torch.tensor(scores, dtype=torch.float32), candidates, "a-action"
    )
    tied = tuple(
        sorted(
            candidates[index]["action_id"]
            for index, score in enumerate(scores)
            if score == max(scores)
        )
    )

    assert terms.score_greedy_action_ids == tied
    assert terms.two_stage_score_greedy_action_ids == tied
    assert terms.unique_score_greedy_action_id is None
    assert terms.unique_two_stage_score_greedy_action_id is None


def test_tie_metadata_is_permutation_stable():
    scores = torch.tensor([1.0, 1.0, 0.0], dtype=torch.float32)
    candidates = [
        _candidate("z-action", "take"),
        _candidate("a-action", "skip"),
        _candidate("m-action", "take"),
    ]
    first = build_hierarchical_policy_terms(scores, candidates, "m-action")
    permutation = [2, 0, 1]
    second = build_hierarchical_policy_terms(
        scores[permutation],
        [candidates[index] for index in permutation],
        "m-action",
    )

    assert first.score_greedy_action_ids == second.score_greedy_action_ids
    assert (
        first.two_stage_score_greedy_action_ids
        == second.two_stage_score_greedy_action_ids
    )


def test_opposite_float32_limits_keep_terms_and_backward_finite():
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

    terms = build_hierarchical_policy_terms(scores, candidates, "skip")
    exposed = (
        terms.selected_family_log_probability,
        terms.selected_conditional_log_probability,
        terms.selected_joint_log_probability,
        terms.family_entropy,
        terms.conditional_entropy,
        terms.joint_entropy,
    )

    assert all(torch.isfinite(value).item() for value in exposed)
    terms.selected_joint_log_probability.backward()
    assert scores.grad is not None
    assert torch.isfinite(scores.grad).all()


def test_api_has_no_coefficient_reward_advantage_or_loss_surface():
    parameters = inspect.signature(build_hierarchical_policy_terms).parameters
    assert tuple(parameters) == ("scores", "candidates", "selected_action_id")
    forbidden = {"coefficient", "reward", "return", "advantage", "loss"}
    assert not any(
        word in name for name in parameters for word in forbidden
    )


def test_candidate_type_boundary_matches_sequence_of_mappings():
    hints = get_type_hints(build_hierarchical_policy_terms)
    candidate_hint = hints["candidates"]
    assert get_origin(candidate_hint) is Sequence
    mapping_hint = get_args(candidate_hint)[0]
    assert get_origin(mapping_hint) is Mapping

    scores = torch.tensor([1.0, 0.0], dtype=torch.float32)
    candidates = (
        MappingProxyType({"action_id": "take", "kind": "take"}),
        MappingProxyType({"action_id": "skip", "kind": "skip"}),
    )
    terms = build_hierarchical_policy_terms(scores, candidates, "take")
    assert terms.selected_action_id == "take"


def test_metadata_is_exact_stable_and_all_false():
    expected = {
        "authority": {
            "coefficient_selection": False,
            "experiment_execution": False,
            "formal_rl": False,
            "gameplay": False,
            "loss_construction": False,
            "model_loading": False,
            "native_loading": False,
            "policy_promotion": False,
            "qualification": False,
            "sampling": False,
            "seed_access": False,
            "training": False,
        },
        "coefficient_api": False,
        "deterministic_selection": "raw-score-max-set-v1",
        "distribution_schema_version": (
            "noncombat-action-family-distribution-v1"
        ),
        "entropy_terms": ["family", "expected_conditional", "joint"],
        "loss_api": False,
        "schema_version": (
            "noncombat-hierarchical-policy-objective-contract-v1"
        ),
        "score_dtype": "float32",
        "selected_identity_field": "action_id",
        "tensor_device": "cpu",
        "term_dtype": "float64",
        "tie_breaking": "none-return-all-maxima",
        "two_stage_equivalence": "max-family-score-then-max-within-family",
    }

    first = objective_metadata()
    assert first == expected
    first["authority"]["training"] = True
    first["entropy_terms"].append("changed")
    assert objective_metadata() == expected


def test_distribution_metadata_drift_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
):
    scores, candidates = _multi_family_fixture()
    metadata = objective.family_distribution.distribution_metadata()
    metadata["schema_version"] = "changed"
    monkeypatch.setattr(
        objective.family_distribution,
        "distribution_metadata",
        lambda: metadata,
    )

    with pytest.raises(
        HierarchicalPolicyObjectiveError, match="distribution metadata"
    ):
        build_hierarchical_policy_terms(scores, candidates, "take-best")


def test_import_isolation_is_bidirectional():
    runtime_modules = (
        "analysis_scripts.noncombat_state_conditioned_ranker",
        "analysis_scripts.noncombat_state_conditioned_policy_input",
        "analysis_scripts.noncombat_state_conditioned_simulator_learning_experiment",
        "analysis_scripts.verify_noncombat_state_conditioned_simulator_learning_experiment",
        "spirecomm.ai.agent",
        "main",
    )
    runtime_checks = ",".join(
        f"{module_name!r}:{module_name!r} in sys.modules"
        for module_name in runtime_modules
    )
    import_objective = (
        "import importlib,json,sys;"
        "importlib.import_module('analysis_scripts.noncombat_hierarchical_policy_objective');"
        f"print(json.dumps({{{runtime_checks},"
        "'analysis_scripts.noncombat_simulator_adapter':"
        "'analysis_scripts.noncombat_simulator_adapter' in sys.modules,"
        "'sts_lightspeed_noncombat_adapter':"
        "'sts_lightspeed_noncombat_adapter' in sys.modules},sort_keys=True))"
    )
    objective_completed = subprocess.run(
        [sys.executable, "-c", import_objective],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert not any(json.loads(objective_completed.stdout).values())
    for module_name in runtime_modules:
        import_runtime = (
            "import importlib,json,sys;"
            f"importlib.import_module({module_name!r});"
            "print(json.dumps({'objective':"
            "'analysis_scripts.noncombat_hierarchical_policy_objective' in sys.modules},sort_keys=True))"
        )
        runtime_completed = subprocess.run(
            [sys.executable, "-c", import_runtime],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        assert json.loads(runtime_completed.stdout.splitlines()[-1]) == {
            "objective": False
        }


def test_design_report_is_deterministic_complete_and_checked_in():
    first = render_design_report()
    second = render_design_report()

    assert first == second
    assert REPORT_PATH.read_text(encoding="utf-8") == first
    for heading in (
        "# Non-Combat Hierarchical Policy Objective Contract",
        "## Evidence Boundary",
        "## Objective Terms",
        "## Deterministic Selection",
        "## Synthetic Invariants",
        "## Deferred Decisions",
        "## Authority",
    ):
        assert heading in first
    assert "family + conditional" in first
    assert "joint-probability argmax" in first
    assert "Each exposed term gradient finite: `true`" in first
    assert "coefficient_selection: false" in first
    assert "training: false" in first
    assert "timestamp" not in first.lower()
