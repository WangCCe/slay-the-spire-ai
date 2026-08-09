"""Explicit-logit source-only objective terms for card-acceptance policies."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json
from typing import Any

import torch

from analysis_scripts.noncombat_card_acceptance_policy import (
    CardAcceptancePolicy,
    build_family_features,
    policy_metadata,
)
from analysis_scripts.noncombat_state_conditioned_ranker import (
    ARCHITECTURE_ID as RANKER_ARCHITECTURE_ID,
)


OBJECTIVE_SCHEMA_VERSION = "noncombat-card-acceptance-objective-v1"
REPORT_SCHEMA_VERSION = (
    "noncombat-card-acceptance-objective-architecture-contract-report-v1"
)
LOGIT_DTYPE = torch.float32
TERM_DTYPE = torch.float64
TIE_POLICY = "lexicographic-all-maxima-no-unique-on-tie-v1"

_AUTHORITY = {
    "architecture_selection": False,
    "causal_claim": False,
    "coefficient_selection": False,
    "cohort_materialization": False,
    "communication_mod": False,
    "environment_construction": False,
    "evaluation": False,
    "execution": False,
    "fitting": False,
    "formal_rl": False,
    "gameplay": False,
    "loss_construction": False,
    "model_loading": False,
    "native_loading": False,
    "objective_selection": False,
    "ope": False,
    "optimizer_selection": False,
    "policy_promotion": False,
    "policy_quality": False,
    "qualification": False,
    "replay": False,
    "reward_selection": False,
    "seed_access": False,
    "training": False,
}

_PROHIBITED_MODULES = (
    "analysis_scripts.noncombat_cross_fitted_hierarchical_learning_experiment",
    "analysis_scripts.noncombat_cross_fitted_hierarchical_learning_runtime",
    "analysis_scripts.noncombat_simulator_adapter",
    "analysis_scripts.noncombat_simulator_rl_experiment",
    "analysis_scripts.noncombat_state_conditioned_policy_input",
    "analysis_scripts.verify_noncombat_cross_fitted_hierarchical_learning_experiment",
    "spirecomm",
    "sts_lightspeed_noncombat_adapter",
)


class CardAcceptanceObjectiveError(ValueError):
    """Raised when explicit card-acceptance objective terms are invalid."""


@dataclass(frozen=True)
class CardAcceptancePolicyTerms:
    action_ids: tuple[str, ...]
    candidate_families: tuple[str, ...]
    family_order: tuple[str, ...]
    selected_action_id: str
    selected_index: int
    selected_family: str
    selected_family_index: int
    acceptance_active: bool
    acceptance_coordinate: torch.Tensor | None
    family_log_probabilities: torch.Tensor
    family_probabilities: torch.Tensor
    conditional_log_probabilities: torch.Tensor
    conditional_probabilities: torch.Tensor
    joint_log_probabilities: torch.Tensor
    joint_probabilities: torch.Tensor
    selected_family_log_probability: torch.Tensor
    selected_conditional_log_probability: torch.Tensor
    selected_joint_log_probability: torch.Tensor
    family_entropy: torch.Tensor
    per_family_conditional_entropies: torch.Tensor
    expected_conditional_entropy: torch.Tensor
    joint_entropy: torch.Tensor
    greedy_family_ids: tuple[str, ...]
    unique_greedy_family_id: str | None
    greedy_action_ids_by_family: tuple[tuple[str, tuple[str, ...]], ...]
    two_stage_greedy_action_ids: tuple[str, ...]
    unique_two_stage_greedy_action_id: str | None


def objective_metadata() -> dict[str, Any]:
    return {
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
        "schema_version": OBJECTIVE_SCHEMA_VERSION,
        "selected_terms": (
            "family_log_probability",
            "conditional_log_probability",
            "joint_log_probability",
        ),
        "term_dtype": "float64",
        "tie_policy": TIE_POLICY,
        "update_api": False,
    }


def _validated_logits(value: Any, label: str) -> torch.Tensor:
    if not isinstance(value, torch.Tensor):
        raise CardAcceptanceObjectiveError(f"{label} must be a tensor")
    if value.ndim != 1:
        raise CardAcceptanceObjectiveError(f"{label} must be rank 1")
    if value.shape[0] == 0:
        raise CardAcceptanceObjectiveError(f"{label} must be nonempty")
    if value.device.type != "cpu":
        raise CardAcceptanceObjectiveError(f"{label} must remain on CPU")
    if value.dtype != LOGIT_DTYPE:
        raise CardAcceptanceObjectiveError(f"{label} dtype must be float32")
    if not torch.isfinite(value).all().item():
        raise CardAcceptanceObjectiveError(f"{label} must be finite")
    return value


def _validated_candidates(
    value: Any, *, expected_count: int, category: Any
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if category != "card_reward":
        raise CardAcceptanceObjectiveError("category must equal card_reward")
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise CardAcceptanceObjectiveError("candidates must be a sequence")
    if len(value) != expected_count:
        raise CardAcceptanceObjectiveError(
            "conditional_logits and candidates must align"
        )
    action_ids: list[str] = []
    families: list[str] = []
    seen: set[str] = set()
    for index, candidate in enumerate(value):
        if not isinstance(candidate, Mapping):
            raise CardAcceptanceObjectiveError(
                f"candidate[{index}] must be a mapping"
            )
        action_id = candidate.get("action_id")
        if not isinstance(action_id, str) or not action_id:
            raise CardAcceptanceObjectiveError(
                f"candidate[{index}] action_id must be nonempty"
            )
        if action_id in seen:
            raise CardAcceptanceObjectiveError(f"duplicate action_id: {action_id}")
        kind = candidate.get("kind")
        if not isinstance(kind, str) or not kind:
            raise CardAcceptanceObjectiveError(
                f"candidate[{index}] kind must be nonempty"
            )
        seen.add(action_id)
        action_ids.append(action_id)
        families.append(kind)
    if "take" not in families:
        raise CardAcceptanceObjectiveError("card_reward candidates must include take")
    return tuple(action_ids), tuple(families)


def _unique_or_none(values: tuple[str, ...]) -> str | None:
    return values[0] if len(values) == 1 else None


def _acceptance_coordinate(
    family_logits: torch.Tensor, family_order: tuple[str, ...]
) -> tuple[bool, torch.Tensor | None]:
    if family_order == ("take",):
        return False, None
    take_index = family_order.index("take")
    non_take = torch.tensor(
        [index for index in range(len(family_order)) if index != take_index],
        dtype=torch.long,
        device="cpu",
    )
    logits = family_logits.to(dtype=TERM_DTYPE)
    coordinate = logits[take_index] - torch.logsumexp(
        logits.index_select(0, non_take), dim=0
    )
    return True, coordinate


def _require_finite(values: Sequence[torch.Tensor]) -> None:
    if any(not torch.isfinite(value).all().item() for value in values):
        raise CardAcceptanceObjectiveError(
            "card-acceptance objective terms must remain finite"
        )


def build_card_acceptance_policy_terms(
    family_logits: torch.Tensor,
    conditional_logits: torch.Tensor,
    candidates: Sequence[Mapping[str, Any]],
    selected_action_id: str,
    *,
    category: str,
) -> CardAcceptancePolicyTerms:
    normalized_family_logits = _validated_logits(family_logits, "family_logits")
    normalized_conditional_logits = _validated_logits(
        conditional_logits, "conditional_logits"
    )
    action_ids, candidate_families = _validated_candidates(
        candidates,
        expected_count=normalized_conditional_logits.shape[0],
        category=category,
    )
    family_order = tuple(sorted(set(candidate_families)))
    if normalized_family_logits.shape[0] != len(family_order):
        raise CardAcceptanceObjectiveError(
            "family_logits must align with sorted candidate families"
        )
    if not isinstance(selected_action_id, str) or selected_action_id not in action_ids:
        raise CardAcceptanceObjectiveError(
            "selected_action_id must identify one candidate"
        )

    family_indices = {
        family: tuple(
            index
            for index, candidate_family in enumerate(candidate_families)
            if candidate_family == family
        )
        for family in family_order
    }
    family_logits64 = normalized_family_logits.to(dtype=TERM_DTYPE)
    conditional_logits64 = normalized_conditional_logits.to(dtype=TERM_DTYPE)
    family_log_probabilities = torch.log_softmax(family_logits64, dim=0)
    family_probabilities = family_log_probabilities.exp()

    conditional_by_candidate: list[torch.Tensor | None] = [None] * len(action_ids)
    per_family_conditional_entropies: list[torch.Tensor] = []
    greedy_action_ids_by_family: list[tuple[str, tuple[str, ...]]] = []
    for family in family_order:
        indices = family_indices[family]
        index_tensor = torch.tensor(indices, dtype=torch.long, device="cpu")
        logits = conditional_logits64.index_select(0, index_tensor)
        log_probabilities = torch.log_softmax(logits, dim=0)
        probabilities = log_probabilities.exp()
        per_family_conditional_entropies.append(
            -(probabilities * log_probabilities).sum()
        )
        for index, log_probability in zip(indices, log_probabilities, strict=True):
            conditional_by_candidate[index] = log_probability
        maximum = torch.amax(logits.detach())
        greedy_action_ids_by_family.append(
            (
                family,
                tuple(
                    sorted(
                        action_ids[index]
                        for index, value in zip(indices, logits.detach(), strict=True)
                        if bool(torch.eq(value, maximum).item())
                    )
                ),
            )
        )

    conditional_log_probabilities = torch.stack(
        [value for value in conditional_by_candidate if value is not None]
    )
    if conditional_log_probabilities.shape != normalized_conditional_logits.shape:
        raise CardAcceptanceObjectiveError(
            "conditional probabilities lost candidate alignment"
        )
    conditional_probabilities = conditional_log_probabilities.exp()
    family_position = {family: index for index, family in enumerate(family_order)}
    joint_log_probabilities = torch.stack(
        [
            family_log_probabilities[family_position[family]]
            + conditional_log_probabilities[index]
            for index, family in enumerate(candidate_families)
        ]
    )
    joint_probabilities = joint_log_probabilities.exp()
    family_entropy = -(family_probabilities * family_log_probabilities).sum()
    per_family_entropy_tensor = torch.stack(per_family_conditional_entropies)
    expected_conditional_entropy = (
        family_probabilities * per_family_entropy_tensor
    ).sum()
    joint_entropy = -(joint_probabilities * joint_log_probabilities).sum()
    acceptance_active, acceptance_coordinate = _acceptance_coordinate(
        normalized_family_logits, family_order
    )

    maximum_family_logit = torch.amax(family_logits64.detach())
    greedy_family_ids = tuple(
        family_order[index]
        for index, value in enumerate(family_logits64.detach())
        if bool(torch.eq(value, maximum_family_logit).item())
    )
    greedy_by_family = tuple(greedy_action_ids_by_family)
    greedy_lookup = dict(greedy_by_family)
    two_stage_greedy_action_ids = tuple(
        sorted(
            action_id
            for family in greedy_family_ids
            for action_id in greedy_lookup[family]
        )
    )
    selected_index = action_ids.index(selected_action_id)
    selected_family = candidate_families[selected_index]
    selected_family_index = family_position[selected_family]
    selected_family_log_probability = family_log_probabilities[
        selected_family_index
    ]
    selected_conditional_log_probability = conditional_log_probabilities[
        selected_index
    ]
    selected_joint_log_probability = joint_log_probabilities[selected_index]

    exposed = (
        family_log_probabilities,
        family_probabilities,
        conditional_log_probabilities,
        conditional_probabilities,
        joint_log_probabilities,
        joint_probabilities,
        selected_family_log_probability,
        selected_conditional_log_probability,
        selected_joint_log_probability,
        family_entropy,
        per_family_entropy_tensor,
        expected_conditional_entropy,
        joint_entropy,
    )
    if acceptance_coordinate is not None:
        exposed += (acceptance_coordinate,)
    _require_finite(exposed)
    if not torch.allclose(
        joint_entropy,
        family_entropy + expected_conditional_entropy,
        atol=1e-12,
        rtol=1e-12,
    ):
        raise CardAcceptanceObjectiveError("hierarchical entropy identity mismatch")

    return CardAcceptancePolicyTerms(
        action_ids=action_ids,
        candidate_families=candidate_families,
        family_order=family_order,
        selected_action_id=selected_action_id,
        selected_index=selected_index,
        selected_family=selected_family,
        selected_family_index=selected_family_index,
        acceptance_active=acceptance_active,
        acceptance_coordinate=acceptance_coordinate,
        family_log_probabilities=family_log_probabilities,
        family_probabilities=family_probabilities,
        conditional_log_probabilities=conditional_log_probabilities,
        conditional_probabilities=conditional_probabilities,
        joint_log_probabilities=joint_log_probabilities,
        joint_probabilities=joint_probabilities,
        selected_family_log_probability=selected_family_log_probability,
        selected_conditional_log_probability=selected_conditional_log_probability,
        selected_joint_log_probability=selected_joint_log_probability,
        family_entropy=family_entropy,
        per_family_conditional_entropies=per_family_entropy_tensor,
        expected_conditional_entropy=expected_conditional_entropy,
        joint_entropy=joint_entropy,
        greedy_family_ids=greedy_family_ids,
        unique_greedy_family_id=_unique_or_none(greedy_family_ids),
        greedy_action_ids_by_family=greedy_by_family,
        two_stage_greedy_action_ids=two_stage_greedy_action_ids,
        unique_two_stage_greedy_action_id=_unique_or_none(
            two_stage_greedy_action_ids
        ),
    )


def _has_nonzero(gradients: Sequence[torch.Tensor | None]) -> bool:
    return any(
        gradient is not None and bool(torch.count_nonzero(gradient).item())
        for gradient in gradients
    )


def _synthetic_invariants() -> dict[str, bool]:
    candidates = [
        {"action_id": "take-a", "kind": "take"},
        {"action_id": "bowl", "kind": "bowl"},
        {"action_id": "take-b", "kind": "take"},
        {"action_id": "skip", "kind": "skip"},
    ]
    features = torch.tensor(
        [[4.0, 0.0], [3.0, 2.0], [0.0, 2.0], [1.0, 0.0]],
        dtype=torch.float32,
    )
    original_batch = build_family_features(
        features, candidates, category="card_reward"
    )
    permutation = [3, 2, 0, 1]
    permuted_batch = build_family_features(
        features[permutation],
        [candidates[index] for index in permutation],
        category="card_reward",
    )
    family_logits = torch.tensor([0.5, -0.5, 1.5], dtype=torch.float32)
    conditional_logits = torch.tensor([2.0, 0.0, 0.0, 1.0], dtype=torch.float32)
    base = build_card_acceptance_policy_terms(
        family_logits,
        conditional_logits,
        candidates,
        "take-b",
        category="card_reward",
    )
    family_shift = build_card_acceptance_policy_terms(
        family_logits + torch.tensor([0.0, 0.0, 2.0]),
        conditional_logits,
        candidates,
        "take-b",
        category="card_reward",
    )
    conditional_shift = build_card_acceptance_policy_terms(
        family_logits,
        conditional_logits + torch.tensor([1.0, 0.0, -1.0, 0.0]),
        candidates,
        "take-b",
        category="card_reward",
    )

    take_skip_candidates = [
        {"action_id": "take-a", "kind": "take"},
        {"action_id": "take-b", "kind": "take"},
        {"action_id": "skip", "kind": "skip"},
    ]
    take_skip_smooth = build_card_acceptance_policy_terms(
        torch.tensor([0.25, 0.75], dtype=torch.float32),
        torch.tensor([1.0, -1.0, 0.0], dtype=torch.float32),
        take_skip_candidates,
        "take-b",
        category="card_reward",
    )
    take_only = build_card_acceptance_policy_terms(
        torch.tensor([0.0], dtype=torch.float32),
        torch.tensor([1.0, -1.0], dtype=torch.float32),
        take_skip_candidates[:2],
        "take-a",
        category="card_reward",
    )
    ties = build_card_acceptance_policy_terms(
        torch.ones(3, dtype=torch.float32),
        torch.ones(4, dtype=torch.float32),
        candidates,
        "take-a",
        category="card_reward",
    )

    with torch.random.fork_rng(devices=[]):
        model = CardAcceptancePolicy(input_dim=2, hidden_dim=3)
    with torch.no_grad():
        for head in (model.family_head, model.conditional_ranker):
            head.hidden.weight.fill_(0.1)
            head.hidden.bias.fill_(0.2)
            head.scorer.weight.fill_(0.3)
            head.scorer.bias.zero_()
    output = model(
        torch.tensor([0.5, 0.25]),
        features,
        candidates,
        category="card_reward",
    )
    differentiable = build_card_acceptance_policy_terms(
        output.family_logits,
        output.conditional_logits,
        candidates,
        "take-b",
        category="card_reward",
    )
    family_parameters = tuple(model.family_head.parameters())
    conditional_parameters = tuple(model.conditional_ranker.parameters())
    parameters = family_parameters + conditional_parameters
    split = len(family_parameters)

    def gradients(term: torch.Tensor) -> tuple[torch.Tensor | None, ...]:
        return torch.autograd.grad(
            term, parameters, allow_unused=True, retain_graph=True
        )

    family_gradients = gradients(-differentiable.selected_family_log_probability)
    conditional_gradients = gradients(
        -differentiable.selected_conditional_log_probability
    )
    combined_gradients = gradients(
        -differentiable.selected_family_log_probability
        - differentiable.selected_conditional_log_probability
    )
    entropy_gradients = gradients(differentiable.expected_conditional_entropy)
    reconstruction_exact = True
    for parameter, family_gradient, conditional_gradient, combined_gradient in zip(
        parameters,
        family_gradients,
        conditional_gradients,
        combined_gradients,
        strict=True,
    ):
        left = torch.zeros_like(parameter) if family_gradient is None else family_gradient
        right = (
            torch.zeros_like(parameter)
            if conditional_gradient is None
            else conditional_gradient
        )
        reconstruction_exact = reconstruction_exact and (
            combined_gradient is not None
            and torch.equal(combined_gradient, left + right)
        )

    limit = torch.finfo(torch.float32).max
    extreme = build_card_acceptance_policy_terms(
        torch.tensor([limit, -limit, 0.0], dtype=torch.float32),
        torch.tensor([limit, 0.0, -limit, 0.0], dtype=torch.float32),
        candidates,
        "take-b",
        category="card_reward",
    )
    extreme_values = tuple(
        value for value in extreme.__dict__.values() if isinstance(value, torch.Tensor)
    )
    family_ids = {id(parameter) for parameter in family_parameters}
    conditional_ids = {id(parameter) for parameter in conditional_parameters}
    family_storage = {
        parameter.untyped_storage().data_ptr() for parameter in family_parameters
    }
    conditional_storage = {
        parameter.untyped_storage().data_ptr()
        for parameter in conditional_parameters
    }
    fixture_checks = {
        "float32-extremes": all(
            torch.isfinite(value).all().item() for value in extreme_values
        ),
        "permutation": (
            original_batch.family_order == permuted_batch.family_order
            and torch.equal(
                original_batch.family_features, permuted_batch.family_features
            )
        ),
        "take-only": (
            take_only.family_order == ("take",)
            and take_only.acceptance_active is False
            and take_only.acceptance_coordinate is None
            and take_only.family_probabilities.item() == 1.0
            and take_only.expected_conditional_entropy.item() > 0.0
            and torch.equal(
                take_only.joint_entropy,
                take_only.expected_conditional_entropy,
            )
        ),
        "take-skip-bowl": (
            base.family_order == ("bowl", "skip", "take")
            and base.acceptance_active is True
        ),
        "take-skip-smooth": (
            take_skip_smooth.family_order == ("skip", "take")
            and take_skip_smooth.acceptance_active is True
            and take_skip_smooth.per_family_conditional_entropies[1].item() > 0.0
        ),
        "ties": (
            ties.greedy_family_ids == ("bowl", "skip", "take")
            and ties.unique_greedy_family_id is None
            and ties.two_stage_greedy_action_ids
            == ("bowl", "skip", "take-a", "take-b")
            and ties.unique_two_stage_greedy_action_id is None
        ),
    }
    if not all(fixture_checks.values()):
        failed = sorted(name for name, passed in fixture_checks.items() if not passed)
        raise CardAcceptanceObjectiveError(
            f"registered synthetic fixture failed: {failed[0]}"
        )
    return {
        "acceptance_independent_of_conditional": bool(
            torch.equal(base.acceptance_coordinate, conditional_shift.acceptance_coordinate)
        ),
        "conditional_gradient_isolated": bool(
            _has_nonzero(conditional_gradients[split:])
            and all(
                gradient is None or not torch.count_nonzero(gradient).item()
                for gradient in conditional_gradients[:split]
            )
        ),
        "conditional_independent_of_acceptance": bool(
            torch.equal(
                base.conditional_probabilities,
                family_shift.conditional_probabilities,
            )
        ),
        "entropy_identity": bool(
            torch.allclose(
                base.joint_entropy,
                base.family_entropy + base.expected_conditional_entropy,
                atol=1e-12,
                rtol=1e-12,
            )
        ),
        "expected_conditional_entropy_cross_head": bool(
            _has_nonzero(entropy_gradients[:split])
            and _has_nonzero(entropy_gradients[split:])
        ),
        "extremes_finite": bool(
            all(torch.isfinite(value).all().item() for value in extreme_values)
        ),
        "family_gradient_isolated": bool(
            _has_nonzero(family_gradients[:split])
            and all(
                gradient is None or not torch.count_nonzero(gradient).item()
                for gradient in family_gradients[split:]
            )
        ),
        "family_permutation_invariant": bool(
            original_batch.family_order == permuted_batch.family_order
            and torch.equal(
                original_batch.family_features, permuted_batch.family_features
            )
        ),
        "gradient_reconstruction_exact": bool(reconstruction_exact),
        "parameter_identity_disjoint": family_ids.isdisjoint(conditional_ids),
        "parameter_storage_disjoint": family_storage.isdisjoint(
            conditional_storage
        ),
        "probability_normalized": bool(
            torch.allclose(
                base.family_probabilities.sum(),
                torch.tensor(1.0, dtype=TERM_DTYPE),
                atol=1e-12,
                rtol=1e-12,
            )
            and torch.allclose(
                base.joint_probabilities.sum(),
                torch.tensor(1.0, dtype=TERM_DTYPE),
                atol=1e-12,
                rtol=1e-12,
            )
        ),
    }


def build_contract_report() -> dict[str, Any]:
    metadata = policy_metadata()
    return {
        "authority": dict(_AUTHORITY),
        "contracts": {
            "architecture": {
                "checkpoint_namespaces": metadata["checkpoint_namespaces"],
                "family_aggregation": metadata["family_aggregation"],
                "family_order": "lexicographic-kind",
                "input_projection": metadata["input_projection"],
                "parameter_sharing": "none",
            },
            "objective": {
                "acceptance_coordinate": "z_take-logsumexp-all-explicit-non-take-families-float64-v1",
                "entropy_decomposition": "joint=family+expected_conditional",
                "gradient_ownership": "selected-family:family-head;selected-conditional:conditional-ranker;expected-conditional:cross-head-v1",
                "probability_factorization": "p(family)*p(candidate|family)",
                "tie_policy": TIE_POLICY,
            },
            "synthetic_evidence": {
                "fixture_ids": (
                    "float32-extremes",
                    "permutation",
                    "take-only",
                    "take-skip-bowl",
                    "take-skip-smooth",
                    "ties",
                ),
                "invariants": _synthetic_invariants(),
            },
        },
        "dependencies": {
            "prohibited_modules": _PROHIBITED_MODULES,
            "required": {
                "ranker": {
                    "architecture_id": RANKER_ARCHITECTURE_ID,
                    "class": "StateConditionedCandidateRanker",
                    "module": "analysis_scripts.noncombat_state_conditioned_ranker",
                }
            },
        },
        "future_empirical_entry": {
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
        },
        "limitations": (
            "mean-family-features-lose-within-family-detail",
            "source-only-no-empirical-policy-quality",
            "two-head-checkpoints-require-new-identity",
            "variable-family-sets-require-validation",
        ),
        "schemas": {
            "objective": OBJECTIVE_SCHEMA_VERSION,
            "policy": metadata["schema_version"],
            "report": REPORT_SCHEMA_VERSION,
        },
    }


def canonical_json_bytes(report: Mapping[str, Any]) -> bytes:
    try:
        return (
            json.dumps(
                report,
                allow_nan=False,
                ensure_ascii=True,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CardAcceptanceObjectiveError(
            f"report must be canonical JSON: {exc}"
        ) from exc


def render_contract_markdown(report: Mapping[str, Any]) -> str:
    if tuple(report) != (
        "authority",
        "contracts",
        "dependencies",
        "future_empirical_entry",
        "limitations",
        "schemas",
    ):
        raise CardAcceptanceObjectiveError("report top-level fields must be exact")
    evidence = report["contracts"]["synthetic_evidence"]["invariants"]
    lines = [
        "# Non-Combat Card-Acceptance Objective Architecture Contract",
        "",
        f"- Policy schema: `{report['schemas']['policy']}`",
        f"- Objective schema: `{report['schemas']['objective']}`",
        f"- Report schema: `{report['schemas']['report']}`",
        "- Parameter sharing: `none`",
        "- Acceptance: `z_take - logsumexp(all explicit non-take families)`",
        "- Empirical authorization: `not-authorized-source-only-contract`",
        "",
        "## Synthetic Invariants",
        "",
    ]
    lines.extend(
        f"- `{name}`: `{str(bool(value)).lower()}`"
        for name, value in sorted(evidence.items())
    )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "This source-only contract selects no loss, coefficient, optimizer,",
            "cohort, execution, evaluation, policy promotion, or gameplay behavior.",
            "",
        ]
    )
    rendered = "\n".join(lines)
    if len(rendered.encode("utf-8")) > 32_768:
        raise CardAcceptanceObjectiveError("Markdown report exceeds 32768 bytes")
    return rendered


__all__ = [
    "CardAcceptanceObjectiveError",
    "CardAcceptancePolicyTerms",
    "build_card_acceptance_policy_terms",
    "build_contract_report",
    "canonical_json_bytes",
    "objective_metadata",
    "render_contract_markdown",
]
