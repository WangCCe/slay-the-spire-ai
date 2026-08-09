"""Source-only disjoint family and conditional heads for card rewards."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import torch

from analysis_scripts.noncombat_state_conditioned_ranker import (
    ARCHITECTURE_ID as RANKER_ARCHITECTURE_ID,
    DEFAULT_HIDDEN_DIM,
    StateConditionedCandidateRanker,
    StateConditionedRankerError,
)


POLICY_SCHEMA_VERSION = "noncombat-card-acceptance-policy-v1"
POLICY_ARCHITECTURE_ID = "disjoint-card-acceptance-heads-v1"
FAMILY_AGGREGATION = "canonical-mean-projected-candidate-features-v1"
INPUT_PROJECTION = "caller-supplied-preprojected-float32-v1"
MODEL_DTYPE = torch.float32
AGGREGATION_DTYPE = torch.float64
ACCEPTANCE_DTYPE = torch.float64


class CardAcceptancePolicyError(ValueError):
    """Raised when the source-only card-acceptance boundary is invalid."""


@dataclass(frozen=True)
class FamilyFeatureBatch:
    action_ids: tuple[str, ...]
    candidate_families: tuple[str, ...]
    family_order: tuple[str, ...]
    family_candidate_indices: tuple[tuple[int, ...], ...]
    family_features: torch.Tensor


@dataclass(frozen=True)
class CardAcceptancePolicyOutput:
    family_batch: FamilyFeatureBatch
    conditional_logits: torch.Tensor
    family_logits: torch.Tensor
    acceptance_active: bool
    acceptance_coordinate: torch.Tensor | None


def policy_metadata() -> dict[str, Any]:
    return {
        "acceptance_dtype": "float64",
        "aggregation_dtype": "float64",
        "architecture_id": POLICY_ARCHITECTURE_ID,
        "candidate_identity_field": "action_id",
        "checkpoint_namespaces": {
            "conditional_ranker": "conditional_ranker.*",
            "family_head": "family_head.*",
        },
        "device": "cpu",
        "family_aggregation": FAMILY_AGGREGATION,
        "family_identity_field": "kind",
        "input_projection": INPUT_PROJECTION,
        "model_dtype": "float32",
        "output_type": "CardAcceptancePolicyOutput",
        "ranker_architecture_id": RANKER_ARCHITECTURE_ID,
        "schema_version": POLICY_SCHEMA_VERSION,
    }


def _validated_candidate_features(value: Any) -> torch.Tensor:
    if not isinstance(value, torch.Tensor):
        raise CardAcceptancePolicyError("candidate_features must be a tensor")
    if value.ndim != 2:
        raise CardAcceptancePolicyError("candidate_features must be rank 2")
    if value.shape[0] == 0 or value.shape[1] == 0:
        raise CardAcceptancePolicyError("candidate_features must be nonempty")
    if value.device.type != "cpu":
        raise CardAcceptancePolicyError("candidate_features must remain on CPU")
    if value.dtype != MODEL_DTYPE:
        raise CardAcceptancePolicyError("candidate_features dtype must be float32")
    if not torch.isfinite(value).all().item():
        raise CardAcceptancePolicyError("candidate_features must be finite")
    return value


def _validated_candidates(
    value: Any, *, expected_count: int, category: Any
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if category != "card_reward":
        raise CardAcceptancePolicyError("category must equal card_reward")
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise CardAcceptancePolicyError("candidates must be a sequence")
    if len(value) != expected_count:
        raise CardAcceptancePolicyError("candidate features and candidates must align")

    action_ids: list[str] = []
    families: list[str] = []
    seen_action_ids: set[str] = set()
    for index, candidate in enumerate(value):
        if not isinstance(candidate, Mapping):
            raise CardAcceptancePolicyError(
                f"candidate[{index}] must be a mapping"
            )
        action_id = candidate.get("action_id")
        if not isinstance(action_id, str) or not action_id:
            raise CardAcceptancePolicyError(
                f"candidate[{index}] action_id must be nonempty"
            )
        if action_id in seen_action_ids:
            raise CardAcceptancePolicyError(f"duplicate action_id: {action_id}")
        kind = candidate.get("kind")
        if not isinstance(kind, str) or not kind:
            raise CardAcceptancePolicyError(
                f"candidate[{index}] kind must be nonempty"
            )
        seen_action_ids.add(action_id)
        action_ids.append(action_id)
        families.append(kind)
    if "take" not in families:
        raise CardAcceptancePolicyError("card_reward candidates must include take")
    return tuple(action_ids), tuple(families)


def build_family_features(
    candidate_features: torch.Tensor,
    candidates: Sequence[Mapping[str, Any]],
    *,
    category: str,
) -> FamilyFeatureBatch:
    features = _validated_candidate_features(candidate_features)
    action_ids, candidate_families = _validated_candidates(
        candidates, expected_count=features.shape[0], category=category
    )
    family_order = tuple(sorted(set(candidate_families)))
    family_candidate_indices = tuple(
        tuple(
            sorted(
                (
                    index
                    for index, family in enumerate(candidate_families)
                    if family == expected_family
                ),
                key=lambda index: action_ids[index],
            )
        )
        for expected_family in family_order
    )

    family_features: list[torch.Tensor] = []
    float32_limit = torch.finfo(MODEL_DTYPE).max
    for indices in family_candidate_indices:
        index_tensor = torch.tensor(indices, dtype=torch.long, device="cpu")
        rows = features.index_select(0, index_tensor).to(dtype=AGGREGATION_DTYPE)
        mean = rows.mean(dim=0)
        if not torch.isfinite(mean).all().item():
            raise CardAcceptancePolicyError("family feature mean must be finite")
        if torch.any(torch.abs(mean) > float32_limit).item():
            raise CardAcceptancePolicyError(
                "family feature mean must be float32-representable"
            )
        converted = mean.to(dtype=MODEL_DTYPE)
        if not torch.isfinite(converted).all().item():
            raise CardAcceptancePolicyError(
                "converted family feature mean must be finite"
            )
        family_features.append(converted)

    stacked = torch.stack(family_features)
    return FamilyFeatureBatch(
        action_ids=action_ids,
        candidate_families=candidate_families,
        family_order=family_order,
        family_candidate_indices=family_candidate_indices,
        family_features=stacked,
    )


def _acceptance_coordinate(
    family_logits: torch.Tensor, family_order: tuple[str, ...]
) -> tuple[bool, torch.Tensor | None]:
    if family_order == ("take",):
        return False, None
    take_index = family_order.index("take")
    non_take_indices = torch.tensor(
        [index for index in range(len(family_order)) if index != take_index],
        dtype=torch.long,
        device="cpu",
    )
    logits = family_logits.to(dtype=ACCEPTANCE_DTYPE)
    coordinate = logits[take_index] - torch.logsumexp(
        logits.index_select(0, non_take_indices), dim=0
    )
    if not torch.isfinite(coordinate).item():
        raise CardAcceptancePolicyError("acceptance coordinate must be finite")
    return True, coordinate


class CardAcceptancePolicy(torch.nn.Module):
    def __init__(
        self, input_dim: int, hidden_dim: int = DEFAULT_HIDDEN_DIM
    ) -> None:
        super().__init__()
        self.family_head = StateConditionedCandidateRanker(input_dim, hidden_dim)
        self.conditional_ranker = StateConditionedCandidateRanker(
            input_dim, hidden_dim
        )
        self.input_dim = self.family_head.input_dim
        self.hidden_dim = self.family_head.hidden_dim

    def architecture_metadata(self) -> dict[str, Any]:
        return {
            **policy_metadata(),
            "hidden_dim": self.hidden_dim,
            "input_dim": self.input_dim,
        }

    def forward(
        self,
        state_features: torch.Tensor,
        candidate_features: torch.Tensor,
        candidates: Sequence[Mapping[str, Any]],
        *,
        category: str,
    ) -> CardAcceptancePolicyOutput:
        family_batch = build_family_features(
            candidate_features, candidates, category=category
        )
        try:
            conditional_logits = self.conditional_ranker(
                state_features, candidate_features
            )
            family_logits = self.family_head(
                state_features, family_batch.family_features
            )
        except StateConditionedRankerError as exc:
            raise CardAcceptancePolicyError(str(exc)) from exc
        acceptance_active, acceptance_coordinate = _acceptance_coordinate(
            family_logits, family_batch.family_order
        )
        return CardAcceptancePolicyOutput(
            family_batch=family_batch,
            conditional_logits=conditional_logits,
            family_logits=family_logits,
            acceptance_active=acceptance_active,
            acceptance_coordinate=acceptance_coordinate,
        )


__all__ = [
    "CardAcceptancePolicy",
    "CardAcceptancePolicyError",
    "CardAcceptancePolicyOutput",
    "FamilyFeatureBatch",
    "build_family_features",
    "policy_metadata",
]
