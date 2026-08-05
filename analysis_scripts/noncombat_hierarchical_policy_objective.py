"""Source-only hierarchical policy objective terms for non-combat actions."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import torch

from analysis_scripts import noncombat_action_family_distribution as family_distribution


OBJECTIVE_SCHEMA_VERSION = "noncombat-hierarchical-policy-objective-contract-v1"
DETERMINISTIC_SELECTION = "raw-score-max-set-v1"

_AUTHORITY = {
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
}

_EXPECTED_DISTRIBUTION_METADATA = {
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
    "family_aggregation": "max-candidate-score-v1",
    "family_identity_field": "kind",
    "schema_version": "noncombat-action-family-distribution-v1",
    "score_dtype": "float32",
}


class HierarchicalPolicyObjectiveError(ValueError):
    """Raised when hierarchical objective terms cannot be constructed exactly."""


@dataclass(frozen=True)
class HierarchicalPolicyTerms:
    """Differentiable selected-action terms plus score-derived greedy metadata."""

    action_ids: tuple[str, ...]
    family_order: tuple[str, ...]
    selected_action_id: str
    selected_index: int
    selected_family: str
    selected_family_index: int
    selected_family_log_probability: torch.Tensor
    selected_conditional_log_probability: torch.Tensor
    selected_joint_log_probability: torch.Tensor
    family_entropy: torch.Tensor
    conditional_entropy: torch.Tensor
    joint_entropy: torch.Tensor
    score_greedy_action_ids: tuple[str, ...]
    unique_score_greedy_action_id: str | None
    two_stage_score_greedy_action_ids: tuple[str, ...]
    unique_two_stage_score_greedy_action_id: str | None


def objective_metadata() -> dict[str, Any]:
    """Return stable identity and no-authority metadata for the contract."""
    return {
        "authority": dict(_AUTHORITY),
        "coefficient_api": False,
        "deterministic_selection": DETERMINISTIC_SELECTION,
        "distribution_schema_version": _EXPECTED_DISTRIBUTION_METADATA[
            "schema_version"
        ],
        "entropy_terms": ["family", "expected_conditional", "joint"],
        "loss_api": False,
        "schema_version": OBJECTIVE_SCHEMA_VERSION,
        "score_dtype": "float32",
        "selected_identity_field": "action_id",
        "tensor_device": "cpu",
        "term_dtype": "float64",
        "tie_breaking": "none-return-all-maxima",
        "two_stage_equivalence": "max-family-score-then-max-within-family",
    }


def _distribution_metadata_is_exact() -> None:
    if (
        family_distribution.distribution_metadata()
        != _EXPECTED_DISTRIBUTION_METADATA
    ):
        raise HierarchicalPolicyObjectiveError(
            "action-family distribution metadata mismatch"
        )


def _unique_or_none(action_ids: tuple[str, ...]) -> str | None:
    return action_ids[0] if len(action_ids) == 1 else None


def _raw_score_maxima(
    scores: torch.Tensor, action_ids: tuple[str, ...]
) -> tuple[str, ...]:
    detached = scores.detach()
    maximum = torch.amax(detached)
    return tuple(
        sorted(
            action_ids[index]
            for index in range(detached.shape[0])
            if bool(torch.eq(detached[index], maximum).item())
        )
    )


def _two_stage_score_maxima(
    scores: torch.Tensor,
    distribution: family_distribution.ActionFamilyDistribution,
) -> tuple[str, ...]:
    family_logits = distribution.family_logits.detach()
    maximum_family_logit = torch.amax(family_logits)
    maximum_families = {
        distribution.family_order[index]
        for index in range(family_logits.shape[0])
        if bool(torch.eq(family_logits[index], maximum_family_logit).item())
    }
    family_positions = {
        family: index for index, family in enumerate(distribution.family_order)
    }
    detached_scores = scores.detach().to(dtype=torch.float64)
    return tuple(
        sorted(
            distribution.action_ids[index]
            for index, family in enumerate(distribution.candidate_families)
            if family in maximum_families
            and bool(
                torch.eq(
                    detached_scores[index],
                    family_logits[family_positions[family]],
                ).item()
            )
        )
    )


def _require_finite(values: tuple[torch.Tensor, ...]) -> None:
    if any(not torch.isfinite(value).all().item() for value in values):
        raise HierarchicalPolicyObjectiveError(
            "hierarchical objective terms must remain finite"
        )


def build_hierarchical_policy_terms(
    scores: torch.Tensor,
    candidates: Sequence[Mapping[str, Any]],
    selected_action_id: str,
) -> HierarchicalPolicyTerms:
    """Build selected log-probability and entropy terms without defining a loss."""
    if not isinstance(selected_action_id, str) or not selected_action_id:
        raise HierarchicalPolicyObjectiveError(
            "selected_action_id must be a nonempty string"
        )
    _distribution_metadata_is_exact()
    try:
        distribution = family_distribution.build_action_family_distribution(
            scores, candidates
        )
    except family_distribution.ActionFamilyDistributionError as exc:
        raise HierarchicalPolicyObjectiveError(str(exc)) from exc
    if selected_action_id not in distribution.action_ids:
        raise HierarchicalPolicyObjectiveError(
            "selected_action_id must identify one candidate"
        )

    selected_index = distribution.action_ids.index(selected_action_id)
    selected_family = distribution.candidate_families[selected_index]
    selected_family_index = distribution.family_order.index(selected_family)
    selected_family_log_probability = distribution.family_log_probabilities[
        selected_family_index
    ]
    selected_conditional_log_probability = (
        distribution.conditional_log_probabilities[selected_index]
    )
    selected_joint_log_probability = distribution.candidate_log_probabilities[
        selected_index
    ]
    if not torch.equal(
        selected_joint_log_probability,
        selected_family_log_probability + selected_conditional_log_probability,
    ):
        raise HierarchicalPolicyObjectiveError(
            "selected hierarchical log-probability identity mismatch"
        )
    if not torch.allclose(
        distribution.joint_entropy,
        distribution.family_entropy + distribution.conditional_entropy,
        atol=1e-12,
        rtol=1e-12,
    ):
        raise HierarchicalPolicyObjectiveError(
            "hierarchical entropy identity mismatch"
        )

    score_greedy_action_ids = _raw_score_maxima(scores, distribution.action_ids)
    two_stage_score_greedy_action_ids = _two_stage_score_maxima(
        scores, distribution
    )
    if two_stage_score_greedy_action_ids != score_greedy_action_ids:
        raise HierarchicalPolicyObjectiveError(
            "two-stage score maxima differ from raw-score maxima"
        )
    exposed = (
        selected_family_log_probability,
        selected_conditional_log_probability,
        selected_joint_log_probability,
        distribution.family_entropy,
        distribution.conditional_entropy,
        distribution.joint_entropy,
    )
    _require_finite(exposed)
    return HierarchicalPolicyTerms(
        action_ids=distribution.action_ids,
        family_order=distribution.family_order,
        selected_action_id=selected_action_id,
        selected_index=selected_index,
        selected_family=selected_family,
        selected_family_index=selected_family_index,
        selected_family_log_probability=selected_family_log_probability,
        selected_conditional_log_probability=selected_conditional_log_probability,
        selected_joint_log_probability=selected_joint_log_probability,
        family_entropy=distribution.family_entropy,
        conditional_entropy=distribution.conditional_entropy,
        joint_entropy=distribution.joint_entropy,
        score_greedy_action_ids=score_greedy_action_ids,
        unique_score_greedy_action_id=_unique_or_none(score_greedy_action_ids),
        two_stage_score_greedy_action_ids=two_stage_score_greedy_action_ids,
        unique_two_stage_score_greedy_action_id=_unique_or_none(
            two_stage_score_greedy_action_ids
        ),
    )


def render_design_report() -> str:
    """Render deterministic synthetic evidence for the bounded contract."""
    scores = torch.tensor(
        [2.0, 0.0, 1.0], dtype=torch.float32, requires_grad=True
    )
    candidates = [
        {"action_id": "take-best", "kind": "take"},
        {"action_id": "take-low", "kind": "take"},
        {"action_id": "skip", "kind": "skip"},
    ]
    terms = build_hierarchical_policy_terms(scores, candidates, "take-low")
    factorization_exact = torch.equal(
        terms.selected_joint_log_probability,
        terms.selected_family_log_probability
        + terms.selected_conditional_log_probability,
    )
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
    gradient_finite = bool(
        all(
            term.requires_grad and torch.isfinite(gradient).all().item()
            for term, gradient in zip(exposed_terms, gradients, strict=True)
        )
    )

    route = build_hierarchical_policy_terms(
        torch.tensor([-1.0, 0.5, 2.0], dtype=torch.float32),
        [
            {"action_id": "route-a", "kind": "map_node"},
            {"action_id": "route-b", "kind": "map_node"},
            {"action_id": "route-c", "kind": "map_node"},
        ],
        "route-b",
    )
    one_family_exact = bool(
        route.selected_family_log_probability.item() == 0.0
        and route.family_entropy.item() == 0.0
        and torch.equal(
            route.selected_joint_log_probability,
            route.selected_conditional_log_probability,
        )
    )
    tie = build_hierarchical_policy_terms(
        torch.tensor([1.0, 1.0, 0.0], dtype=torch.float32),
        [
            {"action_id": "z-action", "kind": "take"},
            {"action_id": "a-action", "kind": "skip"},
            {"action_id": "m-action", "kind": "take"},
        ],
        "m-action",
    )
    limit = torch.finfo(torch.float32).max
    extreme_scores = torch.tensor(
        [limit, -limit, 0.0, -limit],
        dtype=torch.float32,
        requires_grad=True,
    )
    extreme = build_hierarchical_policy_terms(
        extreme_scores,
        [
            {"action_id": "take-best", "kind": "take"},
            {"action_id": "take-low", "kind": "take"},
            {"action_id": "skip", "kind": "skip"},
            {"action_id": "skip-low", "kind": "skip"},
        ],
        "skip",
    )
    extreme_values = (
        extreme.selected_family_log_probability,
        extreme.selected_conditional_log_probability,
        extreme.selected_joint_log_probability,
        extreme.family_entropy,
        extreme.conditional_entropy,
        extreme.joint_entropy,
    )
    extreme.selected_joint_log_probability.backward()
    extreme_finite = bool(
        all(torch.isfinite(value).item() for value in extreme_values)
        and extreme_scores.grad is not None
        and torch.isfinite(extreme_scores.grad).all().item()
    )
    authority_lines = [
        f"- {name}: {str(value).lower()}"
        for name, value in sorted(_AUTHORITY.items())
    ]
    lines = [
        "# Non-Combat Hierarchical Policy Objective Contract",
        "",
        "## Evidence Boundary",
        "",
        "This report uses fixed synthetic CPU score tensors only. It does not",
        "construct a loss, select a coefficient, sample or train a policy, load a",
        "model or native simulator, access a seed or holdout, or launch gameplay.",
        "",
        "## Objective Terms",
        "",
        "- Selected joint log probability is exactly family + conditional.",
        "- Family, expected conditional, and joint entropy remain separate.",
        "- The API accepts no coefficient, reward, return, advantage, or loss.",
        "",
        "## Deterministic Selection",
        "",
        "- Greedy metadata is the complete raw-score maximum set.",
        "- Two-stage max-family then max-within-family produces the same set.",
        "- Ties are sorted by action ID and are not broken by candidate order.",
        "- No joint-probability argmax selection API is defined.",
        "",
        "## Synthetic Invariants",
        "",
        f"- Selected factorization exact: `{str(factorization_exact).lower()}`.",
        f"- Each exposed term gradient finite: `{str(gradient_finite).lower()}`.",
        f"- One-family fallback exact: `{str(one_family_exact).lower()}`.",
        f"- Tied score maxima: `{', '.join(tie.score_greedy_action_ids)}`.",
        f"- Opposite float32 limits finite: `{str(extreme_finite).lower()}`.",
        "",
        "## Deferred Decisions",
        "",
        "- Family and conditional entropy coefficients require a separate",
        "  preregistered experiment proposal.",
        "- Sampling, loss reduction, reward, optimizer, and promotion remain",
        "  undefined here.",
        "- Synthetic gradient identities do not establish intervention value.",
        "",
        "## Authority",
        "",
        *authority_lines,
        "",
    ]
    return "\n".join(lines)
