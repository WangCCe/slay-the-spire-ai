from __future__ import annotations

import copy
import inspect
import json
from collections.abc import Mapping, Sequence
from dataclasses import fields
from pathlib import Path
from typing import Any, get_args, get_origin, get_type_hints

import pytest
import torch

from analysis_scripts import noncombat_card_acceptance_objective as objective
from analysis_scripts import noncombat_card_acceptance_policy as policy_module
from analysis_scripts.noncombat_card_acceptance_objective import (
    CardAcceptanceObjectiveError,
    CardAcceptancePolicyTerms,
    build_card_acceptance_policy_terms,
    build_contract_report,
    canonical_json_bytes,
    objective_metadata,
    render_contract_markdown,
)
from analysis_scripts.noncombat_card_acceptance_policy import CardAcceptancePolicy


ROOT = Path(__file__).resolve().parents[1]
REPORT_JSON_PATH = (
    ROOT
    / "reports"
    / "noncombat_card_acceptance_objective_architecture_contract_20260809.json"
)
REPORT_MD_PATH = REPORT_JSON_PATH.with_suffix(".md")


def _candidate(action_id: str, kind: str) -> dict[str, str]:
    return {"action_id": action_id, "kind": kind}


def _candidates() -> list[dict[str, str]]:
    return [
        _candidate("take-a", "take"),
        _candidate("bowl", "bowl"),
        _candidate("take-b", "take"),
        _candidate("skip", "skip"),
    ]


def _logits(*, requires_grad: bool = False):
    family = torch.tensor(
        [0.5, -0.5, 1.5], dtype=torch.float32, requires_grad=requires_grad
    )
    conditional = torch.tensor(
        [2.0, 0.0, 0.0, 1.0],
        dtype=torch.float32,
        requires_grad=requires_grad,
    )
    return family, conditional


def _terms(*, selected: str = "take-b", requires_grad: bool = False):
    family, conditional = _logits(requires_grad=requires_grad)
    return build_card_acceptance_policy_terms(
        family,
        conditional,
        _candidates(),
        selected,
        category="card_reward",
    )


def test_objective_metadata_signature_and_output_fields_are_exact():
    assert objective_metadata() == {
        "candidate_identity_field": "action_id",
        "coefficient_api": False,
        "device": "cpu",
        "entropy_terms": (
            "family",
            "per_family_conditional",
            "expected_conditional",
            "joint",
        ),
        "family_identity_field": "kind",
        "input_logit_dtype": "float32",
        "loss_api": False,
        "optimizer_api": False,
        "output_type": "CardAcceptancePolicyTerms",
        "schema_version": "noncombat-card-acceptance-objective-v1",
        "selected_terms": (
            "family_log_probability",
            "conditional_log_probability",
            "joint_log_probability",
        ),
        "term_dtype": "float64",
        "tie_policy": "lexicographic-all-maxima-no-unique-on-tie-v1",
        "update_api": False,
    }
    parameters = inspect.signature(build_card_acceptance_policy_terms).parameters
    assert tuple(parameters) == (
        "family_logits",
        "conditional_logits",
        "candidates",
        "selected_action_id",
        "category",
    )
    assert all(
        parameters[name].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        for name in (
            "family_logits",
            "conditional_logits",
            "candidates",
            "selected_action_id",
        )
    )
    assert parameters["category"].kind is inspect.Parameter.KEYWORD_ONLY
    assert all(
        parameter.default is inspect.Parameter.empty
        for parameter in parameters.values()
    )
    builder_hints = get_type_hints(build_card_acceptance_policy_terms)
    assert builder_hints["family_logits"] is torch.Tensor
    assert builder_hints["conditional_logits"] is torch.Tensor
    assert builder_hints["selected_action_id"] is str
    assert builder_hints["category"] is str
    assert builder_hints["return"] is CardAcceptancePolicyTerms
    assert get_origin(builder_hints["candidates"]) is Sequence
    assert get_origin(get_args(builder_hints["candidates"])[0]) is Mapping
    assert get_args(get_args(builder_hints["candidates"])[0]) == (str, Any)
    assert not inspect.signature(objective_metadata).parameters
    assert not inspect.signature(build_contract_report).parameters
    assert get_type_hints(objective_metadata)["return"] == dict[str, Any]
    assert get_type_hints(build_contract_report)["return"] == dict[str, Any]
    assert tuple(inspect.signature(canonical_json_bytes).parameters) == ("report",)
    assert tuple(inspect.signature(render_contract_markdown).parameters) == (
        "report",
    )
    assert (
        inspect.signature(canonical_json_bytes).parameters["report"].default
        is inspect.Parameter.empty
    )
    assert (
        inspect.signature(render_contract_markdown).parameters["report"].default
        is inspect.Parameter.empty
    )
    canonical_hints = get_type_hints(canonical_json_bytes)
    markdown_hints = get_type_hints(render_contract_markdown)
    for hints, return_type in ((canonical_hints, bytes), (markdown_hints, str)):
        assert get_origin(hints["report"]) is Mapping
        assert get_args(hints["report"]) == (str, Any)
        assert hints["return"] is return_type
    assert tuple(field.name for field in fields(CardAcceptancePolicyTerms)) == (
        "action_ids",
        "candidate_families",
        "family_order",
        "selected_action_id",
        "selected_index",
        "selected_family",
        "selected_family_index",
        "acceptance_active",
        "acceptance_coordinate",
        "family_log_probabilities",
        "family_probabilities",
        "conditional_log_probabilities",
        "conditional_probabilities",
        "joint_log_probabilities",
        "joint_probabilities",
        "selected_family_log_probability",
        "selected_conditional_log_probability",
        "selected_joint_log_probability",
        "family_entropy",
        "per_family_conditional_entropies",
        "expected_conditional_entropy",
        "joint_entropy",
        "greedy_family_ids",
        "unique_greedy_family_id",
        "greedy_action_ids_by_family",
        "two_stage_greedy_action_ids",
        "unique_two_stage_greedy_action_id",
    )


def test_explicit_family_and_conditional_probabilities_are_aligned():
    terms = _terms()
    family_logits, conditional_logits = _logits()
    expected_family = torch.softmax(family_logits.double(), dim=0)
    expected_take = torch.softmax(conditional_logits[[0, 2]].double(), dim=0)

    assert terms.action_ids == ("take-a", "bowl", "take-b", "skip")
    assert terms.candidate_families == ("take", "bowl", "take", "skip")
    assert terms.family_order == ("bowl", "skip", "take")
    assert torch.allclose(terms.family_probabilities, expected_family)
    assert torch.allclose(
        terms.conditional_probabilities,
        torch.stack((expected_take[0], torch.tensor(1.0), expected_take[1], torch.tensor(1.0))).double(),
    )
    expected_joint = torch.stack(
        (
            expected_family[2] * expected_take[0],
            expected_family[0],
            expected_family[2] * expected_take[1],
            expected_family[1],
        )
    )
    assert torch.allclose(terms.joint_probabilities, expected_joint)
    assert torch.allclose(terms.joint_log_probabilities.exp(), expected_joint)
    assert torch.allclose(
        terms.family_probabilities.sum(), torch.tensor(1.0, dtype=torch.float64)
    )
    assert torch.allclose(
        terms.joint_probabilities.sum(), torch.tensor(1.0, dtype=torch.float64)
    )


def test_acceptance_selected_terms_and_entropy_identity_are_exact():
    terms = _terms()
    family_logits, _ = _logits()
    expected_acceptance = family_logits[2].double() - torch.logsumexp(
        family_logits[:2].double(), dim=0
    )

    assert terms.acceptance_active is True
    assert torch.equal(terms.acceptance_coordinate, expected_acceptance)
    assert terms.selected_action_id == "take-b"
    assert terms.selected_index == 2
    assert terms.selected_family == "take"
    assert terms.selected_family_index == 2
    assert torch.equal(
        terms.selected_joint_log_probability,
        terms.selected_family_log_probability
        + terms.selected_conditional_log_probability,
    )
    assert terms.per_family_conditional_entropies.shape == (3,)
    assert terms.per_family_conditional_entropies[:2].tolist() == [0.0, 0.0]
    assert torch.allclose(
        terms.joint_entropy,
        terms.family_entropy + terms.expected_conditional_entropy,
        atol=1e-12,
        rtol=1e-12,
    )
    tensors = (
        terms.acceptance_coordinate,
        terms.family_log_probabilities,
        terms.family_probabilities,
        terms.conditional_log_probabilities,
        terms.conditional_probabilities,
        terms.joint_log_probabilities,
        terms.joint_probabilities,
        terms.selected_family_log_probability,
        terms.selected_conditional_log_probability,
        terms.selected_joint_log_probability,
        terms.family_entropy,
        terms.per_family_conditional_entropies,
        terms.expected_conditional_entropy,
        terms.joint_entropy,
    )
    assert all(value is not None and value.dtype == torch.float64 for value in tensors)
    assert all(value is not None and value.device.type == "cpu" for value in tensors)


def test_greedy_sets_are_complete_for_three_family_and_conditional_ties():
    terms = build_card_acceptance_policy_terms(
        torch.ones(3, dtype=torch.float32),
        torch.ones(4, dtype=torch.float32),
        _candidates(),
        "take-a",
        category="card_reward",
    )

    assert terms.greedy_family_ids == ("bowl", "skip", "take")
    assert terms.unique_greedy_family_id is None
    assert terms.greedy_action_ids_by_family == (
        ("bowl", ("bowl",)),
        ("skip", ("skip",)),
        ("take", ("take-a", "take-b")),
    )
    assert terms.two_stage_greedy_action_ids == (
        "bowl",
        "skip",
        "take-a",
        "take-b",
    )
    assert terms.unique_two_stage_greedy_action_id is None


def test_candidate_permutation_preserves_values_by_action_identity():
    candidates = _candidates()
    family_logits, conditional_logits = _logits()
    original = build_card_acceptance_policy_terms(
        family_logits,
        conditional_logits,
        candidates,
        "take-b",
        category="card_reward",
    )
    permutation = [3, 2, 0, 1]
    permuted = build_card_acceptance_policy_terms(
        family_logits,
        conditional_logits[permutation],
        [copy.deepcopy(candidates[index]) for index in permutation],
        "take-b",
        category="card_reward",
    )

    for name in (
        "family_log_probabilities",
        "family_probabilities",
        "per_family_conditional_entropies",
    ):
        assert torch.equal(getattr(original, name), getattr(permuted, name))
    for name in (
        "conditional_log_probabilities",
        "conditional_probabilities",
        "joint_log_probabilities",
        "joint_probabilities",
    ):
        left = dict(zip(original.action_ids, getattr(original, name).unbind()))
        right = dict(zip(permuted.action_ids, getattr(permuted, name).unbind()))
        assert left.keys() == right.keys()
        assert all(torch.equal(left[key], right[key]) for key in left)
    assert original.greedy_action_ids_by_family == permuted.greedy_action_ids_by_family


def test_family_and_conditional_coordinates_are_independent():
    base = _terms()
    family_logits, conditional_logits = _logits()
    acceptance_shift = build_card_acceptance_policy_terms(
        family_logits + torch.tensor([0.0, 0.0, 2.0]),
        conditional_logits,
        _candidates(),
        "take-b",
        category="card_reward",
    )
    conditional_shift = build_card_acceptance_policy_terms(
        family_logits,
        conditional_logits + torch.tensor([1.0, 0.0, -1.0, 0.0]),
        _candidates(),
        "take-b",
        category="card_reward",
    )

    assert not torch.equal(base.acceptance_coordinate, acceptance_shift.acceptance_coordinate)
    assert torch.equal(base.conditional_probabilities, acceptance_shift.conditional_probabilities)
    assert torch.equal(
        base.per_family_conditional_entropies,
        acceptance_shift.per_family_conditional_entropies,
    )
    assert torch.equal(base.acceptance_coordinate, conditional_shift.acceptance_coordinate)
    assert torch.equal(base.family_probabilities, conditional_shift.family_probabilities)
    assert not torch.equal(base.conditional_probabilities, conditional_shift.conditional_probabilities)


def test_take_only_fallback_keeps_conditional_policy_live():
    terms = build_card_acceptance_policy_terms(
        torch.tensor([0.0], dtype=torch.float32),
        torch.tensor([1.0, -1.0], dtype=torch.float32),
        [_candidate("take-a", "take"), _candidate("take-b", "take")],
        "take-a",
        category="card_reward",
    )

    assert terms.acceptance_active is False
    assert terms.acceptance_coordinate is None
    assert terms.family_probabilities.item() == 1.0
    assert terms.family_entropy.item() == 0.0
    assert torch.equal(
        terms.selected_joint_log_probability,
        terms.selected_conditional_log_probability,
    )
    assert torch.equal(terms.joint_entropy, terms.expected_conditional_entropy)


@pytest.mark.parametrize(
    ("family_logits", "conditional_logits", "candidates", "selected", "category", "message"),
    [
        (torch.zeros(2), torch.zeros(2), [_candidate("take", "take"), _candidate("skip", "skip")], "take", "shop", "category"),
        (torch.zeros(2, dtype=torch.float64), torch.zeros(2), [_candidate("take", "take"), _candidate("skip", "skip")], "take", "card_reward", "float32"),
        (torch.zeros(2), torch.zeros(2, dtype=torch.float64), [_candidate("take", "take"), _candidate("skip", "skip")], "take", "card_reward", "float32"),
        (torch.zeros(2), torch.zeros(2), [_candidate("bowl", "bowl"), _candidate("skip", "skip")], "skip", "card_reward", "take"),
        (torch.zeros(1), torch.zeros(2), [_candidate("take", "take"), _candidate("skip", "skip")], "take", "card_reward", "family_logits"),
        (torch.tensor([float("nan"), 0.0]), torch.zeros(2), [_candidate("take", "take"), _candidate("skip", "skip")], "take", "card_reward", "finite"),
        (torch.zeros(2), torch.zeros(2), [_candidate("take", "take"), _candidate("skip", "skip")], "missing", "card_reward", "selected_action_id"),
    ],
)
def test_objective_boundary_fails_closed(
    family_logits, conditional_logits, candidates, selected, category, message
):
    with pytest.raises(CardAcceptanceObjectiveError, match=message):
        build_card_acceptance_policy_terms(
            family_logits,
            conditional_logits,
            candidates,
            selected,
            category=category,
        )


def test_opposite_float32_limits_keep_all_terms_and_gradients_finite():
    limit = torch.finfo(torch.float32).max
    family_logits = torch.tensor(
        [limit, -limit, 0.0], dtype=torch.float32, requires_grad=True
    )
    conditional_logits = torch.tensor(
        [limit, 0.0, -limit, 0.0], dtype=torch.float32, requires_grad=True
    )
    terms = build_card_acceptance_policy_terms(
        family_logits,
        conditional_logits,
        _candidates(),
        "take-b",
        category="card_reward",
    )
    exposed = tuple(
        value
        for value in terms.__dict__.values()
        if isinstance(value, torch.Tensor)
    )

    assert all(torch.isfinite(value).all() for value in exposed)
    gradients = torch.autograd.grad(
        terms.selected_joint_log_probability + terms.joint_entropy,
        (family_logits, conditional_logits),
    )
    assert all(torch.isfinite(gradient).all() for gradient in gradients)


def _smooth_policy_output():
    policy = CardAcceptancePolicy(input_dim=2, hidden_dim=3)
    with torch.no_grad():
        for head in (policy.family_head, policy.conditional_ranker):
            head.hidden.weight.fill_(0.1)
            head.hidden.bias.fill_(0.2)
            head.scorer.weight.fill_(0.3)
            head.scorer.bias.zero_()
    output = policy(
        torch.tensor([0.5, 0.25]),
        torch.tensor([[4.0, 0.0], [3.0, 2.0], [0.0, 2.0], [1.0, 0.0]]),
        _candidates(),
        category="card_reward",
    )
    terms = build_card_acceptance_policy_terms(
        output.family_logits,
        output.conditional_logits,
        _candidates(),
        "take-b",
        category="card_reward",
    )
    return policy, terms


def _grads(term, parameters, *, retain_graph=True):
    return torch.autograd.grad(
        term, parameters, allow_unused=True, retain_graph=retain_graph
    )


def _has_nonzero(gradients) -> bool:
    return any(
        gradient is not None and bool(torch.count_nonzero(gradient).item())
        for gradient in gradients
    )


def test_selected_policy_and_per_family_entropy_gradient_ownership_is_exact():
    policy, terms = _smooth_policy_output()
    family_parameters = tuple(policy.family_head.parameters())
    conditional_parameters = tuple(policy.conditional_ranker.parameters())
    parameters = family_parameters + conditional_parameters

    family_gradients = _grads(-terms.selected_family_log_probability, parameters)
    conditional_gradients = _grads(
        -terms.selected_conditional_log_probability, parameters
    )
    take_index = terms.family_order.index("take")
    entropy_gradients = _grads(
        terms.per_family_conditional_entropies[take_index], parameters
    )

    split = len(family_parameters)
    assert _has_nonzero(family_gradients[:split])
    assert all(gradient is None or not torch.count_nonzero(gradient) for gradient in family_gradients[split:])
    assert _has_nonzero(conditional_gradients[split:])
    assert all(gradient is None or not torch.count_nonzero(gradient) for gradient in conditional_gradients[:split])
    assert _has_nonzero(entropy_gradients[split:])
    assert all(gradient is None or not torch.count_nonzero(gradient) for gradient in entropy_gradients[:split])


def test_named_component_gradients_reconstruct_and_expected_entropy_is_cross_head():
    policy, terms = _smooth_policy_output()
    parameters = tuple(policy.family_head.parameters()) + tuple(
        policy.conditional_ranker.parameters()
    )
    family_term = -terms.selected_family_log_probability
    conditional_term = -terms.selected_conditional_log_probability
    family_gradients = _grads(family_term, parameters)
    conditional_gradients = _grads(conditional_term, parameters)
    combined_gradients = _grads(family_term + conditional_term, parameters)
    entropy_gradients = _grads(
        terms.expected_conditional_entropy, parameters, retain_graph=False
    )

    for parameter, family_gradient, conditional_gradient, combined_gradient in zip(
        parameters,
        family_gradients,
        conditional_gradients,
        combined_gradients,
        strict=True,
    ):
        family_value = torch.zeros_like(parameter) if family_gradient is None else family_gradient
        conditional_value = (
            torch.zeros_like(parameter)
            if conditional_gradient is None
            else conditional_gradient
        )
        assert combined_gradient is not None
        assert torch.equal(combined_gradient, family_value + conditional_value)
    split = len(tuple(policy.family_head.parameters()))
    assert _has_nonzero(entropy_gradients[:split])
    assert _has_nonzero(entropy_gradients[split:])


def test_report_schema_values_authority_and_future_entry_are_exact():
    report = build_contract_report()
    assert tuple(report) == (
        "authority",
        "contracts",
        "dependencies",
        "future_empirical_entry",
        "limitations",
        "schemas",
    )
    assert report["schemas"] == {
        "objective": "noncombat-card-acceptance-objective-v1",
        "policy": "noncombat-card-acceptance-policy-v1",
        "report": "noncombat-card-acceptance-objective-architecture-contract-report-v1",
    }
    assert set(report["authority"]) == {
        "architecture_selection",
        "causal_claim",
        "coefficient_selection",
        "cohort_materialization",
        "communication_mod",
        "environment_construction",
        "evaluation",
        "execution",
        "fitting",
        "formal_rl",
        "gameplay",
        "loss_construction",
        "model_loading",
        "native_loading",
        "objective_selection",
        "ope",
        "optimizer_selection",
        "policy_promotion",
        "policy_quality",
        "qualification",
        "replay",
        "reward_selection",
        "seed_access",
        "training",
    }
    assert set(report["authority"].values()) == {False}
    assert report["dependencies"] == {
        "prohibited_modules": (
            "analysis_scripts.noncombat_cross_fitted_hierarchical_learning_experiment",
            "analysis_scripts.noncombat_cross_fitted_hierarchical_learning_runtime",
            "analysis_scripts.noncombat_simulator_adapter",
            "analysis_scripts.noncombat_simulator_rl_experiment",
            "analysis_scripts.noncombat_state_conditioned_policy_input",
            "analysis_scripts.verify_noncombat_cross_fitted_hierarchical_learning_experiment",
            "spirecomm",
            "sts_lightspeed_noncombat_adapter",
        ),
        "required": {
            "ranker": {
                "architecture_id": "state-conditioned-candidate-ranker-mlp-v1",
                "class": "StateConditionedCandidateRanker",
                "module": "analysis_scripts.noncombat_state_conditioned_ranker",
            }
        },
    }
    assert report["contracts"]["architecture"] == {
        "checkpoint_namespaces": {
            "conditional_ranker": "conditional_ranker.*",
            "family_head": "family_head.*",
        },
        "family_aggregation": "canonical-mean-projected-candidate-features-v1",
        "family_order": "lexicographic-kind",
        "input_projection": "caller-supplied-preprojected-float32-v1",
        "parameter_sharing": "none",
    }
    assert report["contracts"]["objective"] == {
        "acceptance_coordinate": "z_take-logsumexp-all-explicit-non-take-families-float64-v1",
        "entropy_decomposition": "joint=family+expected_conditional",
        "gradient_ownership": "selected-family:family-head;selected-conditional:conditional-ranker;expected-conditional:cross-head-v1",
        "probability_factorization": "p(family)*p(candidate|family)",
        "tie_policy": "lexicographic-all-maxima-no-unique-on-tie-v1",
    }
    evidence = report["contracts"]["synthetic_evidence"]
    assert evidence["fixture_ids"] == (
        "float32-extremes",
        "permutation",
        "take-only",
        "take-skip-bowl",
        "take-skip-smooth",
        "ties",
    )
    assert set(evidence["invariants"]) == {
        "acceptance_independent_of_conditional",
        "conditional_gradient_isolated",
        "conditional_independent_of_acceptance",
        "entropy_identity",
        "expected_conditional_entropy_cross_head",
        "extremes_finite",
        "family_gradient_isolated",
        "family_permutation_invariant",
        "gradient_reconstruction_exact",
        "parameter_identity_disjoint",
        "parameter_storage_disjoint",
        "probability_normalized",
    }
    assert set(evidence["invariants"].values()) == {True}
    future = report["future_empirical_entry"]
    assert future == {
        "authorization": "not-authorized-source-only-contract",
        "canary": {
            "at_most_once": True,
            "candidate_disabled_before_authorization": True,
            "control_reproduction_required": True,
            "family_only_shadow_step_required": True,
            "max_candidate_family_rate": 0.95,
            "minimum_family_identities_per_set": 2,
            "paired_episodes": 128,
            "selected_family_denominator_min": 64,
            "unique_greedy_denominator_min": 64,
        },
        "holdout": {
            "at_most_once": True,
            "frozen_arms": True,
            "paired_seeds": 512,
            "requires_canary_pass": True,
        },
        "prohibitions": (
            "candidate-enable-before-authorization",
            "post-canary-replacement",
            "post-canary-resume",
            "post-canary-retry",
            "post-canary-tuning",
            "post-canary-update",
            "seed-inventory-reuse",
        ),
        "required_bindings": (
            "candidate_checkpoint_sha256",
            "candidate_config_sha256",
            "candidate_source_sha256",
            "control_checkpoint_sha256",
            "control_config_sha256",
            "control_source_sha256",
            "seed_inventory_sha256",
            "source_commit",
        ),
        "rollback": {
            "authority_required": True,
            "candidate_disabled": True,
            "promotion_authority": False,
            "target_binding_required": True,
            "trigger_classes": (
                "authority",
                "canary",
                "holdout",
                "identity",
                "legality",
                "preflight",
                "publication",
            ),
        },
    }
    assert report["limitations"] == (
        "mean-family-features-lose-within-family-detail",
        "source-only-no-empirical-policy-quality",
        "two-head-checkpoints-require-new-identity",
        "variable-family-sets-require-validation",
    )


def test_report_executes_every_registered_fixture_and_preserves_rng(monkeypatch):
    original = objective.build_card_acceptance_policy_terms
    observed: list[tuple[tuple[str, ...], tuple[float, ...], int]] = []

    def recording_builder(
        family_logits,
        conditional_logits,
        candidates,
        selected_action_id,
        *,
        category,
    ):
        observed.append(
            (
                tuple(sorted({candidate["kind"] for candidate in candidates})),
                tuple(float(value) for value in family_logits.detach().tolist()),
                len(candidates),
            )
        )
        return original(
            family_logits,
            conditional_logits,
            candidates,
            selected_action_id,
            category=category,
        )

    monkeypatch.setattr(objective, "build_card_acceptance_policy_terms", recording_builder)
    rng_before = torch.random.get_rng_state().clone()
    report = objective.build_contract_report()

    assert torch.equal(torch.random.get_rng_state(), rng_before)
    assert report["contracts"]["synthetic_evidence"]["fixture_ids"] == (
        "float32-extremes",
        "permutation",
        "take-only",
        "take-skip-bowl",
        "take-skip-smooth",
        "ties",
    )
    assert any(families == ("take",) and count == 2 for families, _, count in observed)
    assert any(
        families == ("skip", "take") and count == 3
        for families, _, count in observed
    )
    assert any(
        families == ("bowl", "skip", "take")
        and logits == (1.0, 1.0, 1.0)
        for families, logits, _ in observed
    )
    assert any(
        families == ("bowl", "skip", "take")
        and max(abs(value) for value in logits) == torch.finfo(torch.float32).max
        for families, logits, _ in observed
    )


def test_report_rendering_is_canonical_deterministic_and_bounded():
    report = build_contract_report()
    first_json = canonical_json_bytes(report)
    second_json = canonical_json_bytes(build_contract_report())
    first_markdown = render_contract_markdown(report)
    second_markdown = render_contract_markdown(build_contract_report())

    assert first_json == second_json
    assert first_json == (
        json.dumps(
            report,
            allow_nan=False,
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
    assert first_markdown == second_markdown
    assert first_markdown.startswith("# Non-Combat Card-Acceptance Objective Architecture Contract\n")
    assert len(first_json) <= 131_072
    assert len(first_markdown.encode("utf-8")) <= 32_768
    assert REPORT_JSON_PATH.name.endswith("_20260809.json")
    assert REPORT_MD_PATH.name.endswith("_20260809.md")


def test_modules_expose_no_loss_coefficient_optimizer_or_update_api():
    forbidden = (
        "advantage",
        "coefficient",
        "execution",
        "fitting",
        "loss",
        "optimizer",
        "reward",
        "sampling",
        "training",
        "update",
    )
    for module in (policy_module, objective):
        public_names = tuple(name.lower() for name in dir(module) if not name.startswith("_"))
        assert not any(word in name for word in forbidden for name in public_names)
