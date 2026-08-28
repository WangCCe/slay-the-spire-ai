"""Development-only conformal margin gate for action-relative ensembles."""

from __future__ import annotations

import copy
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from typing import Any, Mapping, NamedTuple

import torch
import torch.nn as nn

from spirecomm.ai.rl.v2.action_relative_uncertainty_ensemble import (
    ActionRelativeCandidateStatistics,
    ActionRelativeUncertaintyEnsemble,
    load_ensemble_development_artifact,
)
from spirecomm.ai.rl.v2.action_relative_advantage_residual import _validate_sha256


ARTIFACT_SCHEMA_VERSION = 1
ARTIFACT_KIND = "combat_action_relative_conformal_margin_development"
CARD_ACTION_STOP = 60
POTION_ACTION_STOP = 90


@dataclass(frozen=True)
class ActionRelativeConformalConfig:
    alpha: float = 0.1
    advantage_threshold: float = 0.5

    def validate(self) -> None:
        if not isinstance(self.alpha, (int, float)) or isinstance(self.alpha, bool):
            raise ValueError("conformal alpha must be numeric")
        if not math.isfinite(float(self.alpha)) or not 0.0 < float(self.alpha) < 1.0:
            raise ValueError("conformal alpha must be strictly between zero and one")
        if not isinstance(self.advantage_threshold, (int, float)) or isinstance(
            self.advantage_threshold, bool
        ):
            raise ValueError("conformal advantage threshold must be numeric")
        if not math.isfinite(float(self.advantage_threshold)) or float(
            self.advantage_threshold
        ) <= 0.0:
            raise ValueError("conformal advantage threshold must be finite and positive")


class ConformalCandidateStatistics(NamedTuple):
    member_predictions: torch.Tensor
    means: torch.Tensor
    standard_deviations: torch.Tensor
    raw_lower_scores: torch.Tensor
    corrections: torch.Tensor
    calibrated_lower_scores: torch.Tensor


class ConformalSelection(NamedTuple):
    actions: torch.Tensor
    guard_actions: torch.Tensor
    residual_actions: torch.Tensor
    predicted_advantages: torch.Tensor
    gate_open: torch.Tensor
    member_means: torch.Tensor
    member_standard_deviations: torch.Tensor
    raw_lower_scores: torch.Tensor
    family_corrections: torch.Tensor
    telemetry: dict[str, Any]


def _manifest_sha256(value: Mapping[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def _validated_corrections(corrections: Mapping[str, Any]) -> dict[str, float]:
    if not isinstance(corrections, Mapping) or set(corrections) != {"card", "potion"}:
        raise ValueError("conformal correction families differ")
    normalized: dict[str, float] = {}
    for family in ("card", "potion"):
        value = corrections[family]
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("conformal correction must be numeric")
        if not math.isfinite(float(value)) or float(value) < 0.0:
            raise ValueError("conformal correction must be finite and non-negative")
        normalized[family] = float(value)
    return normalized


def action_family_indices(candidate_actions: torch.Tensor) -> torch.Tensor:
    actions = candidate_actions.reshape(-1).long()
    families = torch.full_like(actions, -1)
    families[(0 <= actions) & (actions < CARD_ACTION_STOP)] = 0
    families[(CARD_ACTION_STOP <= actions) & (actions < POTION_ACTION_STOP)] = 1
    if bool(families.lt(0).any()):
        raise ValueError("conformal candidate has unsupported action family")
    return families


class ActionRelativeConformalMarginGate(nn.Module):
    """Apply immutable family corrections to a fitted uncertainty ensemble."""

    def __init__(
        self,
        ensemble: ActionRelativeUncertaintyEnsemble,
        config: ActionRelativeConformalConfig,
        *,
        corrections: Mapping[str, Any],
    ) -> None:
        super().__init__()
        config.validate()
        self.ensemble = ensemble
        self.config = config
        self.corrections = _validated_corrections(corrections)
        self.metadata = dict(ensemble.metadata)

    @property
    def parent(self) -> nn.Module:
        return self.ensemble.parent

    def train(self, mode: bool = True):
        super().train(mode)
        self.ensemble.train(mode)
        self.ensemble.parent.eval()
        return self

    def score_candidate_statistics(
        self,
        continuous: torch.Tensor,
        card_ids: torch.Tensor,
        potion_ids: torch.Tensor,
        relic_ids: torch.Tensor,
        action_masks: torch.Tensor,
        guard_actions: torch.Tensor,
        candidate_actions: torch.Tensor,
    ) -> ConformalCandidateStatistics:
        families = action_family_indices(candidate_actions)
        raw: ActionRelativeCandidateStatistics = self.ensemble.score_candidate_statistics(
            continuous,
            card_ids,
            potion_ids,
            relic_ids,
            action_masks,
            guard_actions,
            candidate_actions,
        )
        correction_values = torch.tensor(
            [self.corrections["card"], self.corrections["potion"]],
            dtype=raw.lower_confidence_scores.dtype,
            device=raw.lower_confidence_scores.device,
        )
        corrections = correction_values[families]
        calibrated = raw.lower_confidence_scores - corrections
        return ConformalCandidateStatistics(
            member_predictions=raw.member_predictions,
            means=raw.means,
            standard_deviations=raw.standard_deviations,
            raw_lower_scores=raw.lower_confidence_scores,
            corrections=corrections,
            calibrated_lower_scores=calibrated,
        )

    def score_candidates(self, *args: Any, **kwargs: Any) -> torch.Tensor:
        return self.score_candidate_statistics(*args, **kwargs).calibrated_lower_scores

    def select_actions(
        self,
        continuous: torch.Tensor,
        card_ids: torch.Tensor,
        potion_ids: torch.Tensor,
        relic_ids: torch.Tensor,
        action_masks: torch.Tensor,
        guard_actions: torch.Tensor,
        alternative_masks: torch.Tensor | None = None,
        *,
        forbidden_action_indices: frozenset[int] = frozenset(),
    ) -> ConformalSelection:
        (
            continuous,
            card_ids,
            potion_ids,
            relic_ids,
            action_masks,
            guard_actions,
        ) = self.ensemble._validated_state_inputs(
            continuous,
            card_ids,
            potion_ids,
            relic_ids,
            action_masks,
            guard_actions,
        )
        batch_size = guard_actions.numel()
        rows = torch.arange(batch_size, device=guard_actions.device)
        if alternative_masks is None:
            allowed = action_masks.clone()
            allowed[rows, guard_actions] = False
        else:
            if alternative_masks.dim() == 1:
                alternative_masks = alternative_masks.unsqueeze(0)
            if alternative_masks.shape != action_masks.shape:
                raise ValueError("conformal alternative mask shape differs")
            allowed = alternative_masks.bool().clone()
            if bool((allowed & ~action_masks).any()):
                raise ValueError("conformal alternatives contain illegal actions")
            if bool(allowed[rows, guard_actions].any()):
                raise ValueError("conformal alternatives contain guard action")
        supported = torch.zeros_like(allowed)
        supported[:, : min(CARD_ACTION_STOP, supported.shape[1])] = True
        if supported.shape[1] > CARD_ACTION_STOP:
            supported[:, CARD_ACTION_STOP : min(POTION_ACTION_STOP, supported.shape[1])] = True
        unsupported_count = int((allowed & ~supported).sum().item())
        allowed &= supported
        forbidden = sorted(forbidden_action_indices)
        for action in forbidden:
            if not isinstance(action, int) or isinstance(action, bool) or not (
                0 <= action < self.metadata["action_dim"]
            ):
                raise ValueError("conformal forbidden action is invalid")
            allowed[:, action] = False

        residual_actions = guard_actions.clone()
        calibrated_scores = torch.full(
            (batch_size,), float("-inf"), dtype=continuous.dtype, device=continuous.device
        )
        means = calibrated_scores.clone()
        stds = calibrated_scores.clone()
        raw_scores = calibrated_scores.clone()
        corrections = calibrated_scores.clone()
        candidate_pairs = allowed.nonzero(as_tuple=False)
        has_allowed = allowed.any(dim=1)
        if candidate_pairs.numel():
            state_rows = candidate_pairs[:, 0]
            candidates = candidate_pairs[:, 1]
            stats = self.score_candidate_statistics(
                continuous[state_rows],
                card_ids[state_rows],
                potion_ids[state_rows],
                relic_ids[state_rows],
                action_masks[state_rows],
                guard_actions[state_rows],
                candidates,
            )
            matrix = torch.full_like(action_masks.float(), float("-inf"))
            matrix[state_rows, candidates] = stats.calibrated_lower_scores
            best_scores, best_actions = matrix.max(dim=1)
            residual_actions[has_allowed] = best_actions[has_allowed]
            calibrated_scores[has_allowed] = best_scores[has_allowed]
            selected_pairs = candidates.eq(best_actions[state_rows])
            selected_rows = state_rows[selected_pairs]
            means[selected_rows] = stats.means[selected_pairs]
            stds[selected_rows] = stats.standard_deviations[selected_pairs]
            raw_scores[selected_rows] = stats.raw_lower_scores[selected_pairs]
            corrections[selected_rows] = stats.corrections[selected_pairs]
        gate_open = has_allowed & calibrated_scores.ge(
            float(self.config.advantage_threshold)
        )
        actions = torch.where(gate_open, residual_actions, guard_actions)
        if not bool(action_masks[rows, actions].all()):
            raise RuntimeError("conformal gate selected an illegal action")
        forbidden_selection_count = sum(
            int(actions[gate_open].eq(action).sum().item()) for action in forbidden
        )
        return ConformalSelection(
            actions=actions,
            guard_actions=guard_actions,
            residual_actions=residual_actions,
            predicted_advantages=calibrated_scores,
            gate_open=gate_open,
            member_means=means,
            member_standard_deviations=stds,
            raw_lower_scores=raw_scores,
            family_corrections=corrections,
            telemetry={
                "row_count": int(batch_size),
                "intervention_count": int(gate_open.sum().item()),
                "guard_preserved_count": int((~gate_open).sum().item()),
                "no_allowed_alternative_count": int((~has_allowed).sum().item()),
                "unsupported_alternative_count": unsupported_count,
                "forbidden_action_indices": forbidden,
                "forbidden_action_selection_count": forbidden_selection_count,
                "advantage_threshold": float(self.config.advantage_threshold),
                "alpha": float(self.config.alpha),
                "corrections": dict(self.corrections),
            },
        )


def build_conformal_development_artifact(
    gate: ActionRelativeConformalMarginGate,
    *,
    ensemble_artifact: Mapping[str, Any],
    recipe: Mapping[str, Any],
    split_sha256: Mapping[str, str],
    calibration_support: Mapping[str, int],
    telemetry: Mapping[str, Any],
) -> dict[str, Any]:
    splits = {
        name: _validate_sha256(value, f"{name} split")
        for name, value in split_sha256.items()
    }
    if set(splits) != {"fit", "calibration"}:
        raise ValueError("conformal split identities differ")
    support = {name: int(value) for name, value in calibration_support.items()}
    if set(support) != {"card", "potion"} or any(value <= 0 for value in support.values()):
        raise ValueError("conformal calibration support differs")
    corrections = dict(gate.corrections)
    return {
        "checkpoint_schema_version": ARTIFACT_SCHEMA_VERSION,
        "checkpoint_kind": ARTIFACT_KIND,
        "production_compatible": False,
        "config": asdict(gate.config),
        "recipe": copy.deepcopy(dict(recipe)),
        "split_sha256": splits,
        "calibration_support": support,
        "corrections": corrections,
        "correction_manifest_sha256": _manifest_sha256(corrections),
        "ensemble_artifact": copy.deepcopy(dict(ensemble_artifact)),
        "telemetry": copy.deepcopy(dict(telemetry)),
        "authority": {
            "development_only": True,
            "gameplay": False,
            "qualification": False,
            "promotion": False,
        },
    }


def load_conformal_development_artifact(
    parent: nn.Module,
    metadata: Mapping[str, Any],
    artifact: Mapping[str, Any],
    *,
    expected_parent_checkpoint_sha256: str,
    expected_corpus_sha256: Mapping[str, str],
    expected_recipe: Mapping[str, Any],
    expected_split_sha256: Mapping[str, str],
) -> ActionRelativeConformalMarginGate:
    required = {
        "checkpoint_schema_version",
        "checkpoint_kind",
        "production_compatible",
        "config",
        "recipe",
        "split_sha256",
        "calibration_support",
        "corrections",
        "correction_manifest_sha256",
        "ensemble_artifact",
        "telemetry",
        "authority",
    }
    if not isinstance(artifact, Mapping) or set(artifact) != required:
        raise ValueError("conformal artifact keys differ")
    if artifact["checkpoint_schema_version"] != ARTIFACT_SCHEMA_VERSION:
        raise ValueError("conformal artifact schema differs")
    if artifact["checkpoint_kind"] != ARTIFACT_KIND or artifact["production_compatible"] is not False:
        raise ValueError("conformal artifact kind differs")
    if dict(artifact["recipe"]) != dict(expected_recipe):
        raise ValueError("conformal recipe differs")
    expected_splits = {
        name: _validate_sha256(value, f"expected {name} split")
        for name, value in expected_split_sha256.items()
    }
    observed_splits = {
        name: _validate_sha256(value, f"observed {name} split")
        for name, value in artifact["split_sha256"].items()
    }
    if observed_splits != expected_splits or set(observed_splits) != {"fit", "calibration"}:
        raise ValueError("conformal split identity differs")
    corrections = _validated_corrections(artifact["corrections"])
    if _manifest_sha256(corrections) != _validate_sha256(
        artifact["correction_manifest_sha256"], "correction manifest"
    ):
        raise ValueError("conformal correction identity differs")
    try:
        config = ActionRelativeConformalConfig(**dict(artifact["config"]))
    except TypeError as exc:
        raise ValueError("conformal config differs") from exc
    ensemble_recipe = expected_recipe.get("ensemble_recipe")
    if not isinstance(ensemble_recipe, Mapping):
        raise ValueError("conformal ensemble recipe is missing")
    ensemble = load_ensemble_development_artifact(
        parent,
        metadata,
        artifact["ensemble_artifact"],
        expected_parent_checkpoint_sha256=expected_parent_checkpoint_sha256,
        expected_corpus_sha256=expected_corpus_sha256,
        expected_recipe=ensemble_recipe,
    )
    if artifact["authority"] != {
        "development_only": True,
        "gameplay": False,
        "qualification": False,
        "promotion": False,
    }:
        raise ValueError("conformal artifact authority differs")
    return ActionRelativeConformalMarginGate(
        ensemble,
        config,
        corrections=corrections,
    )
