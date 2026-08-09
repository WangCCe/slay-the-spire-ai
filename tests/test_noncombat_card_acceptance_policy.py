from __future__ import annotations

import copy
import inspect
import json
import math
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import fields
from pathlib import Path
from typing import Any, get_args, get_origin, get_type_hints

import pytest
import torch

from analysis_scripts.noncombat_card_acceptance_policy import (
    CardAcceptancePolicy,
    CardAcceptancePolicyError,
    CardAcceptancePolicyOutput,
    FamilyFeatureBatch,
    build_family_features,
    policy_metadata,
)
from analysis_scripts.noncombat_state_conditioned_ranker import DEFAULT_HIDDEN_DIM


ROOT = Path(__file__).resolve().parents[1]


def _candidate(action_id: str, kind: str) -> dict[str, str]:
    return {"action_id": action_id, "kind": kind}


def _candidates() -> list[dict[str, str]]:
    return [
        _candidate("take-z", "take"),
        _candidate("bowl", "bowl"),
        _candidate("take-a", "take"),
        _candidate("skip", "skip"),
    ]


def _features() -> torch.Tensor:
    return torch.tensor(
        [[4.0, 0.0], [3.0, 1.0], [0.0, 4.0], [1.0, 3.0]],
        dtype=torch.float32,
    )


def test_policy_metadata_and_instance_metadata_are_exact():
    expected = {
        "acceptance_dtype": "float64",
        "aggregation_dtype": "float64",
        "architecture_id": "disjoint-card-acceptance-heads-v1",
        "candidate_identity_field": "action_id",
        "checkpoint_namespaces": {
            "conditional_ranker": "conditional_ranker.*",
            "family_head": "family_head.*",
        },
        "device": "cpu",
        "family_aggregation": "canonical-mean-projected-candidate-features-v1",
        "family_identity_field": "kind",
        "input_projection": "caller-supplied-preprojected-float32-v1",
        "model_dtype": "float32",
        "output_type": "CardAcceptancePolicyOutput",
        "ranker_architecture_id": "state-conditioned-candidate-ranker-mlp-v1",
        "schema_version": "noncombat-card-acceptance-policy-v1",
    }
    policy = CardAcceptancePolicy(input_dim=2, hidden_dim=3)

    assert policy_metadata() == expected
    assert policy.architecture_metadata() == {
        **expected,
        "hidden_dim": 3,
        "input_dim": 2,
    }


def test_public_signatures_and_ordered_outputs_are_exact():
    constructor = inspect.signature(CardAcceptancePolicy).parameters
    assert tuple(constructor) == ("input_dim", "hidden_dim")
    assert all(
        parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        for parameter in constructor.values()
    )
    assert constructor["input_dim"].default is inspect.Parameter.empty
    assert constructor["hidden_dim"].default == DEFAULT_HIDDEN_DIM
    constructor_hints = get_type_hints(CardAcceptancePolicy.__init__)
    assert constructor_hints == {
        "input_dim": int,
        "hidden_dim": int,
        "return": type(None),
    }
    forward = inspect.signature(CardAcceptancePolicy.forward).parameters
    assert tuple(forward) == (
        "self",
        "state_features",
        "candidate_features",
        "candidates",
        "category",
    )
    assert all(
        forward[name].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        for name in (
            "self",
            "state_features",
            "candidate_features",
            "candidates",
        )
    )
    assert forward["category"].kind is inspect.Parameter.KEYWORD_ONLY
    assert all(
        forward[name].default is inspect.Parameter.empty
        for name in (
            "state_features",
            "candidate_features",
            "candidates",
            "category",
        )
    )
    forward_hints = get_type_hints(CardAcceptancePolicy.forward)
    assert forward_hints["state_features"] is torch.Tensor
    assert forward_hints["candidate_features"] is torch.Tensor
    assert forward_hints["category"] is str
    assert forward_hints["return"] is CardAcceptancePolicyOutput
    assert get_origin(forward_hints["candidates"]) is Sequence
    assert get_origin(get_args(forward_hints["candidates"])[0]) is Mapping
    assert get_args(get_args(forward_hints["candidates"])[0]) == (str, Any)
    family_builder = inspect.signature(build_family_features).parameters
    assert tuple(family_builder) == (
        "candidate_features",
        "candidates",
        "category",
    )
    assert all(
        family_builder[name].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        for name in ("candidate_features", "candidates")
    )
    assert family_builder["category"].kind is inspect.Parameter.KEYWORD_ONLY
    assert all(
        parameter.default is inspect.Parameter.empty
        for parameter in family_builder.values()
    )
    family_hints = get_type_hints(build_family_features)
    assert family_hints["candidate_features"] is torch.Tensor
    assert family_hints["category"] is str
    assert family_hints["return"] is FamilyFeatureBatch
    assert get_origin(family_hints["candidates"]) is Sequence
    assert get_origin(get_args(family_hints["candidates"])[0]) is Mapping
    assert get_args(get_args(family_hints["candidates"])[0]) == (str, Any)
    assert not inspect.signature(policy_metadata).parameters
    assert get_type_hints(policy_metadata)["return"] == dict[str, Any]
    assert tuple(field.name for field in fields(FamilyFeatureBatch)) == (
        "action_ids",
        "candidate_families",
        "family_order",
        "family_candidate_indices",
        "family_features",
    )
    assert tuple(field.name for field in fields(CardAcceptancePolicyOutput)) == (
        "family_batch",
        "conditional_logits",
        "family_logits",
        "acceptance_active",
        "acceptance_coordinate",
    )


def test_family_features_keep_exact_families_and_use_float64_mean():
    batch = build_family_features(
        _features(), _candidates(), category="card_reward"
    )

    assert batch.action_ids == ("take-z", "bowl", "take-a", "skip")
    assert batch.candidate_families == ("take", "bowl", "take", "skip")
    assert batch.family_order == ("bowl", "skip", "take")
    assert batch.family_candidate_indices == ((1,), (3,), (2, 0))
    assert batch.family_features.dtype == torch.float32
    assert batch.family_features.device.type == "cpu"
    assert batch.family_features.shape == (3, 2)
    assert torch.equal(
        batch.family_features,
        torch.tensor([[3.0, 1.0], [1.0, 3.0], [2.0, 2.0]]),
    )


def test_family_features_are_permutation_invariant_by_identity():
    candidates = _candidates()
    features = _features()
    original = build_family_features(features, candidates, category="card_reward")
    permutation = [3, 2, 0, 1]
    permuted = build_family_features(
        features[permutation],
        [copy.deepcopy(candidates[index]) for index in permutation],
        category="card_reward",
    )

    assert original.family_order == permuted.family_order
    assert torch.equal(original.family_features, permuted.family_features)
    original_by_action = dict(zip(original.action_ids, original.candidate_families))
    permuted_by_action = dict(zip(permuted.action_ids, permuted.candidate_families))
    assert original_by_action == permuted_by_action


@pytest.mark.parametrize("value", [torch.finfo(torch.float32).max, -torch.finfo(torch.float32).max])
def test_family_feature_extremes_do_not_overflow_float32_accumulation(value):
    features = torch.full((4, 2), value, dtype=torch.float32)
    candidates = [
        _candidate("take-b", "take"),
        _candidate("take-a", "take"),
        _candidate("skip-b", "skip"),
        _candidate("skip-a", "skip"),
    ]

    batch = build_family_features(features, candidates, category="card_reward")

    assert torch.isfinite(batch.family_features).all()
    assert torch.equal(batch.family_features, torch.full((2, 2), value))


def test_policy_owns_two_nonaliased_rankers_and_stable_namespaces():
    policy = CardAcceptancePolicy(input_dim=2, hidden_dim=3)
    family_parameters = tuple(policy.family_head.parameters())
    conditional_parameters = tuple(policy.conditional_ranker.parameters())

    assert family_parameters and conditional_parameters
    assert not set(map(id, family_parameters)) & set(map(id, conditional_parameters))
    family_storage = {parameter.untyped_storage().data_ptr() for parameter in family_parameters}
    conditional_storage = {
        parameter.untyped_storage().data_ptr() for parameter in conditional_parameters
    }
    assert family_storage.isdisjoint(conditional_storage)
    assert all(name.startswith(("family_head.", "conditional_ranker.")) for name in policy.state_dict())
    assert any(name.startswith("family_head.") for name in policy.state_dict())
    assert any(name.startswith("conditional_ranker.") for name in policy.state_dict())


def test_policy_forward_preserves_action_alignment_and_explicit_acceptance():
    policy = CardAcceptancePolicy(input_dim=2, hidden_dim=3)
    output = policy(
        torch.tensor([0.5, 0.25], dtype=torch.float32),
        _features(),
        _candidates(),
        category="card_reward",
    )

    assert output.family_batch.family_order == ("bowl", "skip", "take")
    assert output.conditional_logits.shape == (4,)
    assert output.family_logits.shape == (3,)
    assert output.conditional_logits.dtype == torch.float32
    assert output.family_logits.dtype == torch.float32
    assert output.acceptance_active is True
    assert output.acceptance_coordinate is not None
    assert output.acceptance_coordinate.shape == ()
    assert output.acceptance_coordinate.dtype == torch.float64
    expected = output.family_logits[2].double() - torch.logsumexp(
        output.family_logits[:2].double(), dim=0
    )
    assert torch.equal(output.acceptance_coordinate, expected)


def test_policy_forward_is_permutation_stable_by_action_and_family_identity():
    policy = CardAcceptancePolicy(input_dim=2, hidden_dim=3)
    state = torch.tensor([0.5, 0.25], dtype=torch.float32)
    candidates = _candidates()
    features = _features()
    original = policy(state, features, candidates, category="card_reward")
    permutation = [3, 2, 0, 1]
    permuted = policy(
        state,
        features[permutation],
        [copy.deepcopy(candidates[index]) for index in permutation],
        category="card_reward",
    )

    original_conditional = dict(
        zip(original.family_batch.action_ids, original.conditional_logits.unbind())
    )
    permuted_conditional = dict(
        zip(permuted.family_batch.action_ids, permuted.conditional_logits.unbind())
    )
    assert original_conditional.keys() == permuted_conditional.keys()
    assert all(
        torch.equal(original_conditional[action_id], permuted_conditional[action_id])
        for action_id in original_conditional
    )
    original_family = dict(
        zip(original.family_batch.family_order, original.family_logits.unbind())
    )
    permuted_family = dict(
        zip(permuted.family_batch.family_order, permuted.family_logits.unbind())
    )
    assert original_family.keys() == permuted_family.keys()
    assert all(
        torch.equal(original_family[family], permuted_family[family])
        for family in original_family
    )
    assert torch.equal(
        original.acceptance_coordinate, permuted.acceptance_coordinate
    )


def test_take_only_policy_marks_acceptance_inactive():
    policy = CardAcceptancePolicy(input_dim=2, hidden_dim=3)
    output = policy(
        torch.zeros(2),
        torch.tensor([[1.0, 0.0], [0.0, 1.0]]),
        [_candidate("take-a", "take"), _candidate("take-b", "take")],
        category="card_reward",
    )

    assert output.family_batch.family_order == ("take",)
    assert output.acceptance_active is False
    assert output.acceptance_coordinate is None


@pytest.mark.parametrize(
    ("features", "candidates", "category", "message"),
    [
        (_features(), _candidates(), "shop", "category"),
        (_features()[:2], [_candidate("a", "skip"), _candidate("b", "bowl")], "card_reward", "take"),
        (_features()[:2], [_candidate("a", "take"), _candidate("a", "skip")], "card_reward", "duplicate"),
        (_features()[:2], [_candidate("a", "take"), _candidate("b", "")], "card_reward", "kind"),
        (torch.zeros((2, 2), dtype=torch.float64), [_candidate("a", "take"), _candidate("b", "skip")], "card_reward", "float32"),
        (torch.zeros(2), [_candidate("a", "take"), _candidate("b", "skip")], "card_reward", "rank 2"),
        (torch.zeros((1, 2)), [_candidate("a", "take"), _candidate("b", "skip")], "card_reward", "align"),
        (torch.tensor([[math.nan, 0.0], [0.0, 0.0]]), [_candidate("a", "take"), _candidate("b", "skip")], "card_reward", "finite"),
    ],
)
def test_family_feature_boundary_fails_closed(features, candidates, category, message):
    with pytest.raises(CardAcceptancePolicyError, match=message):
        build_family_features(features, candidates, category=category)


def test_policy_forward_reuses_ranker_tensor_validation():
    policy = CardAcceptancePolicy(input_dim=2, hidden_dim=3)
    with pytest.raises(CardAcceptancePolicyError, match="state_features"):
        policy(
            torch.zeros(2, dtype=torch.float64),
            _features(),
            _candidates(),
            category="card_reward",
        )


def test_fresh_import_avoids_every_prohibited_transitive_module():
    prohibited = (
        "analysis_scripts.noncombat_state_conditioned_policy_input",
        "analysis_scripts.noncombat_simulator_adapter",
        "analysis_scripts.noncombat_simulator_rl_experiment",
        "analysis_scripts.noncombat_cross_fitted_hierarchical_learning_runtime",
        "analysis_scripts.noncombat_cross_fitted_hierarchical_learning_experiment",
        "analysis_scripts.verify_noncombat_cross_fitted_hierarchical_learning_experiment",
        "spirecomm",
        "sts_lightspeed_noncombat_adapter",
    )
    script = (
        f"import json,sys;sys.path.insert(0,{str(ROOT)!r});"
        "import analysis_scripts.noncombat_card_acceptance_policy;"
        "import analysis_scripts.noncombat_card_acceptance_objective;"
        f"p={prohibited!r};"
        "print(json.dumps(sorted(x for x in p if x in sys.modules)))"
    )
    completed = subprocess.run(
        [sys.executable, "-I", "-c", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(completed.stdout) == []


def test_legacy_imports_do_not_load_the_new_capability():
    script = (
        f"import json,sys;sys.path.insert(0,{str(ROOT)!r});"
        "import analysis_scripts.noncombat_state_conditioned_ranker;"
        "import analysis_scripts.noncombat_action_family_distribution;"
        "import analysis_scripts.noncombat_hierarchical_policy_objective;"
        "print(json.dumps(sorted(x for x in sys.modules "
        "if x.startswith('analysis_scripts.noncombat_card_acceptance_'))))"
    )
    completed = subprocess.run(
        [sys.executable, "-I", "-c", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(completed.stdout) == []
