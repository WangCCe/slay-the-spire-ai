"""Source-only hierarchical distribution for non-combat action families."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import torch


DISTRIBUTION_SCHEMA_VERSION = "noncombat-action-family-distribution-v1"
FAMILY_AGGREGATION = "max-candidate-score-v1"
SCORE_DTYPE = torch.float32
DISTRIBUTION_DTYPE = torch.float64

_AUTHORITY = {
    "experiment_execution": False,
    "formal_rl": False,
    "gameplay": False,
    "model_loading": False,
    "native_loading": False,
    "policy_promotion": False,
    "qualification": False,
    "seed_access": False,
    "training": False,
}


class ActionFamilyDistributionError(ValueError):
    """Raised when an action-family distribution boundary is invalid."""


@dataclass(frozen=True)
class ActionFamilyDistribution:
    """Differentiable family and candidate probabilities for one decision."""

    action_ids: tuple[str, ...]
    candidate_families: tuple[str, ...]
    family_order: tuple[str, ...]
    family_logits: torch.Tensor
    family_log_probabilities: torch.Tensor
    family_probabilities: torch.Tensor
    conditional_log_probabilities: torch.Tensor
    candidate_log_probabilities: torch.Tensor
    candidate_probabilities: torch.Tensor
    family_entropy: torch.Tensor
    conditional_entropy: torch.Tensor
    joint_entropy: torch.Tensor


def distribution_metadata() -> dict[str, Any]:
    """Return stable identity and authority metadata for the capability."""
    return {
        "authority": dict(_AUTHORITY),
        "candidate_identity_field": "action_id",
        "device": "cpu",
        "distribution_dtype": "float64",
        "entropy_decomposition": "joint=family+expected_conditional",
        "family_aggregation": FAMILY_AGGREGATION,
        "family_identity_field": "kind",
        "schema_version": DISTRIBUTION_SCHEMA_VERSION,
        "score_dtype": "float32",
    }


def _validated_scores(value: Any) -> torch.Tensor:
    if not isinstance(value, torch.Tensor):
        raise ActionFamilyDistributionError("scores must be a tensor")
    if value.ndim != 1:
        raise ActionFamilyDistributionError("scores must be rank 1")
    if value.shape[0] == 0:
        raise ActionFamilyDistributionError("scores must be nonempty")
    if value.device.type != "cpu":
        raise ActionFamilyDistributionError("scores must remain on CPU")
    if value.dtype != SCORE_DTYPE:
        raise ActionFamilyDistributionError("scores dtype must be float32")
    if not torch.isfinite(value).all().item():
        raise ActionFamilyDistributionError("scores must be finite")
    return value


def _validated_candidates(
    value: Any, *, expected_count: int
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ActionFamilyDistributionError("candidates must be a sequence")
    if len(value) == 0:
        raise ActionFamilyDistributionError("candidates must be nonempty")
    if len(value) != expected_count:
        raise ActionFamilyDistributionError("scores and candidates must align")

    action_ids: list[str] = []
    families: list[str] = []
    seen_action_ids: set[str] = set()
    for index, raw_candidate in enumerate(value):
        if not isinstance(raw_candidate, Mapping):
            raise ActionFamilyDistributionError(
                f"candidate[{index}] must be a mapping"
            )
        action_id = raw_candidate.get("action_id")
        if not isinstance(action_id, str) or not action_id:
            raise ActionFamilyDistributionError(
                f"candidate[{index}] action_id must be nonempty"
            )
        if action_id in seen_action_ids:
            raise ActionFamilyDistributionError(
                f"duplicate candidate action_id: {action_id}"
            )
        kind = raw_candidate.get("kind")
        if not isinstance(kind, str) or not kind:
            raise ActionFamilyDistributionError(
                f"candidate[{index}] kind must be nonempty"
            )
        seen_action_ids.add(action_id)
        action_ids.append(action_id)
        families.append(kind)
    return tuple(action_ids), tuple(families)


def _require_finite_outputs(values: Sequence[torch.Tensor]) -> None:
    if any(not torch.isfinite(value).all().item() for value in values):
        raise ActionFamilyDistributionError("distribution outputs must be finite")


def build_action_family_distribution(
    scores: torch.Tensor, candidates: Sequence[Mapping[str, Any]]
) -> ActionFamilyDistribution:
    """Factor candidate scores into max-pooled family and conditional softmaxes."""
    normalized_scores = _validated_scores(scores)
    action_ids, candidate_families = _validated_candidates(
        candidates, expected_count=normalized_scores.shape[0]
    )
    family_order = tuple(sorted(set(candidate_families)))
    family_indices = {
        family: tuple(
            index
            for index, candidate_family in enumerate(candidate_families)
            if candidate_family == family
        )
        for family in family_order
    }

    family_logits: list[torch.Tensor] = []
    conditional_by_candidate: list[torch.Tensor | None] = [
        None for _ in candidate_families
    ]
    conditional_entropies_internal: list[torch.Tensor] = []
    for family in family_order:
        indices = torch.tensor(family_indices[family], dtype=torch.long, device="cpu")
        family_scores = normalized_scores.index_select(0, indices)
        family_logits.append(
            torch.amax(family_scores, dim=0).to(dtype=DISTRIBUTION_DTYPE)
        )
        family_log_probabilities_internal = torch.log_softmax(
            family_scores.to(dtype=DISTRIBUTION_DTYPE), dim=0
        )
        conditional_entropies_internal.append(
            -(
                family_log_probabilities_internal.exp()
                * family_log_probabilities_internal
            ).sum()
        )
        for candidate_index, conditional_log_probability in zip(
            family_indices[family],
            family_log_probabilities_internal.unbind(),
            strict=True,
        ):
            conditional_by_candidate[candidate_index] = conditional_log_probability

    stacked_family_logits = torch.stack(family_logits)
    family_log_probabilities_internal = torch.log_softmax(stacked_family_logits, dim=0)
    family_probabilities_internal = family_log_probabilities_internal.exp()
    conditional_log_probabilities_internal = torch.stack(
        [
            value
            for value in conditional_by_candidate
            if value is not None
        ]
    )
    if conditional_log_probabilities_internal.shape != normalized_scores.shape:
        raise ActionFamilyDistributionError(
            "conditional probabilities lost candidate alignment"
        )

    family_position = {family: index for index, family in enumerate(family_order)}
    candidate_log_probabilities_internal = torch.stack(
        [
            family_log_probabilities_internal[family_position[family]]
            + conditional_log_probabilities_internal[index]
            for index, family in enumerate(candidate_families)
        ]
    )
    candidate_probabilities_internal = candidate_log_probabilities_internal.exp()
    family_entropy_internal = -(
        family_probabilities_internal * family_log_probabilities_internal
    ).sum()
    conditional_entropy_internal = (
        family_probabilities_internal
        * torch.stack(conditional_entropies_internal)
    ).sum()
    joint_entropy_internal = -(
        candidate_probabilities_internal * candidate_log_probabilities_internal
    ).sum()
    family_log_probabilities = family_log_probabilities_internal
    family_probabilities = family_probabilities_internal
    conditional_log_probabilities = conditional_log_probabilities_internal
    candidate_log_probabilities = candidate_log_probabilities_internal
    candidate_probabilities = candidate_probabilities_internal
    family_entropy = family_entropy_internal
    conditional_entropy = conditional_entropy_internal
    joint_entropy = joint_entropy_internal
    _require_finite_outputs(
        (
            stacked_family_logits,
            family_log_probabilities,
            family_probabilities,
            conditional_log_probabilities,
            candidate_log_probabilities,
            candidate_probabilities,
            family_entropy,
            conditional_entropy,
            joint_entropy,
        )
    )

    return ActionFamilyDistribution(
        action_ids=action_ids,
        candidate_families=candidate_families,
        family_order=family_order,
        family_logits=stacked_family_logits,
        family_log_probabilities=family_log_probabilities,
        family_probabilities=family_probabilities,
        conditional_log_probabilities=conditional_log_probabilities,
        candidate_log_probabilities=candidate_log_probabilities,
        candidate_probabilities=candidate_probabilities,
        family_entropy=family_entropy,
        conditional_entropy=conditional_entropy,
        joint_entropy=joint_entropy,
    )


def _family_probability(distribution: ActionFamilyDistribution, family: str) -> float:
    index = distribution.family_order.index(family)
    return float(distribution.family_probabilities[index].detach().item())


def render_design_report() -> str:
    """Render deterministic synthetic evidence and bounded design conclusions."""
    with torch.no_grad():
        equal_candidates = [
            {"action_id": "take-a", "kind": "take"},
            {"action_id": "take-b", "kind": "take"},
            {"action_id": "take-c", "kind": "take"},
            {"action_id": "skip", "kind": "skip"},
        ]
        equal = build_action_family_distribution(
            torch.zeros(4, dtype=torch.float32), equal_candidates
        )
        base = build_action_family_distribution(
            torch.tensor([2.0, 0.0, 1.0], dtype=torch.float32),
            [
                {"action_id": "take-best", "kind": "take"},
                {"action_id": "take-low", "kind": "take"},
                {"action_id": "skip", "kind": "skip"},
            ],
        )
        duplicated = build_action_family_distribution(
            torch.tensor([2.0, 0.0, 1.0, 0.0], dtype=torch.float32),
            [
                {"action_id": "take-best", "kind": "take"},
                {"action_id": "take-low", "kind": "take"},
                {"action_id": "skip", "kind": "skip"},
                {"action_id": "take-duplicate", "kind": "take"},
            ],
        )
        route_scores = torch.tensor([-1.0, 0.5, 2.0], dtype=torch.float32)
        route = build_action_family_distribution(
            route_scores,
            [
                {"action_id": "route-a", "kind": "map_node"},
                {"action_id": "route-b", "kind": "map_node"},
                {"action_id": "route-c", "kind": "map_node"},
            ],
        )
        limit = torch.finfo(SCORE_DTYPE).max
        extreme = build_action_family_distribution(
            torch.tensor([limit, -limit, 0.0, -limit], dtype=SCORE_DTYPE),
            [
                {"action_id": "take-best", "kind": "take"},
                {"action_id": "take-low", "kind": "take"},
                {"action_id": "skip", "kind": "skip"},
                {"action_id": "skip-low", "kind": "skip"},
            ],
        )

    duplicate_invariant = bool(
        torch.equal(base.family_logits, duplicated.family_logits)
        and torch.equal(base.family_probabilities, duplicated.family_probabilities)
    )
    single_family_fallback = bool(
        torch.allclose(
            route.candidate_probabilities,
            torch.softmax(route_scores.to(dtype=DISTRIBUTION_DTYPE), 0),
        )
    )
    entropy_identity = bool(
        torch.allclose(
            equal.joint_entropy,
            equal.family_entropy + equal.conditional_entropy,
            atol=1e-6,
            rtol=1e-6,
        )
    )
    extreme_finite = all(
        torch.isfinite(value).all().item()
        for value in (
            extreme.family_log_probabilities,
            extreme.conditional_log_probabilities,
            extreme.candidate_log_probabilities,
            extreme.family_entropy,
            extreme.conditional_entropy,
            extreme.joint_entropy,
        )
    )
    authority_lines = [
        f"- {name}: {str(value).lower()}"
        for name, value in sorted(_AUTHORITY.items())
    ]

    lines = [
        "# Non-Combat Action-Family Distribution Design",
        "",
        "## Evidence Boundary",
        "",
        "This report uses fixed synthetic score vectors only. It does not load a",
        "simulator or native module, access a seed or holdout, train or select a",
        "model, set a coefficient, or establish intervention effectiveness.",
        "",
        "## Selected Factorization",
        "",
        f"- Family identity: `kind`.",
        f"- Family aggregation: `{FAMILY_AGGREGATION}`.",
        "- Score input dtype: `float32`; distribution dtype: `float64`.",
        "- Joint probability: `p(family) * p(candidate | family)`.",
        "- Entropy: `H(joint) = H(family) + E[H(candidate | family)]`.",
        "",
        "## Synthetic Invariants",
        "",
        "- Equal-score family probabilities with three `take` candidates and one",
        f"  `skip`: `skip={_family_probability(equal, 'skip'):.6f}`,",
        f"  `take={_family_probability(equal, 'take'):.6f}`.",
        "- Equal-score candidate probabilities:",
        "  `take=0.166667` each and `skip=0.500000`.",
        f"- Duplicate-score family mass invariant: `{str(duplicate_invariant).lower()}`.",
        (
            "- Single-family fallback matches ordinary softmax: "
            f"`{str(single_family_fallback).lower()}`."
        ),
        f"- Entropy decomposition holds within `1e-6`: `{str(entropy_identity).lower()}`.",
        (
            "- Opposite finite float32 limits retain finite outputs: "
            f"`{str(extreme_finite).lower()}`."
        ),
        "- Focused tests also cover normalization, identity-preserving permutations,",
        "  fail-closed inputs, finite selected-log-probability gradients, and fair",
        "  tied-maximum gradients.",
        "",
        "## Alternatives",
        "",
        "- `logmeanexp`: dense gradients, but a duplicated above- or below-average",
        "  candidate changes family mass.",
        "- Separate family head: cardinality independent, but requires new features,",
        "  parameters, checkpoints, and supervision not justified by source-only evidence.",
        "- Flat candidate softmax: retains the measured candidate-count pressure.",
        "",
        "## Risks And Open Questions",
        "",
        "- Max pooling concentrates family-level gradients on top-scoring candidates.",
        "- Greedy selection is undefined here. Two-stage score argmax and joint-",
        "  probability argmax can differ and require an explicit later decision.",
        "- Source-only invariants do not prove that training will avoid the observed",
        "  card-reward collapse.",
        "- A later review must decide whether `kind` is adequate for every shop state.",
        "- A later registered design must choose family and conditional entropy",
        "  coefficients before any empirical execution.",
        "",
        "## Authority",
        "",
        *authority_lines,
        "",
    ]
    return "\n".join(lines)
