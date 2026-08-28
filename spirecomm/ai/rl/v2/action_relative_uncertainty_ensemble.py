"""Development-only action-relative uncertainty ensemble."""

from __future__ import annotations

import copy
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from typing import Any, Mapping, NamedTuple, Sequence

import torch
import torch.nn as nn
import torch.nn.functional as F

from spirecomm.ai.rl.v2.action_relative_advantage_residual import (
    ActionRelativeAdvantageConfig,
    ActionRelativeAdvantageResidual,
    _cpu_state,
    _validate_sha256,
    _validated_scorer_state,
)
from spirecomm.ai.rl.v2.latent_gated_adapter import state_dict_sha256


ARTIFACT_SCHEMA_VERSION = 1
ARTIFACT_KIND = "combat_action_relative_uncertainty_ensemble_development"


@dataclass(frozen=True)
class ActionRelativeUncertaintyConfig:
    hidden_dim: int = 64
    member_count: int = 5
    confidence_scale: float = 1.0
    advantage_threshold: float = 0.5
    target_clip: float = 20.0
    target_scale: float = 10.0

    def validate(self) -> None:
        if not isinstance(self.hidden_dim, int) or isinstance(self.hidden_dim, bool):
            raise ValueError("uncertainty ensemble hidden_dim must be an integer")
        if self.hidden_dim <= 0:
            raise ValueError("uncertainty ensemble hidden_dim must be positive")
        if self.member_count != 5:
            raise ValueError("uncertainty ensemble requires exactly five members")
        for name, value in (
            ("confidence_scale", self.confidence_scale),
            ("advantage_threshold", self.advantage_threshold),
            ("target_clip", self.target_clip),
            ("target_scale", self.target_scale),
        ):
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ValueError(f"uncertainty ensemble {name} must be numeric")
            if not math.isfinite(float(value)) or float(value) <= 0.0:
                raise ValueError(f"uncertainty ensemble {name} must be finite and positive")


class ActionRelativeCandidateStatistics(NamedTuple):
    member_predictions: torch.Tensor
    means: torch.Tensor
    standard_deviations: torch.Tensor
    lower_confidence_scores: torch.Tensor


class ActionRelativeEnsembleSelection(NamedTuple):
    actions: torch.Tensor
    guard_actions: torch.Tensor
    residual_actions: torch.Tensor
    predicted_advantages: torch.Tensor
    gate_open: torch.Tensor
    member_means: torch.Tensor
    member_standard_deviations: torch.Tensor
    telemetry: dict[str, Any]


def _manifest_sha256(values: Sequence[str]) -> str:
    payload = json.dumps(list(values), separators=(",", ":")).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


class ActionRelativeUncertaintyEnsemble(ActionRelativeAdvantageResidual):
    """One frozen parent and five independently fitted scorer heads."""

    def __init__(
        self,
        parent: nn.Module,
        metadata: Mapping[str, Any],
        config: ActionRelativeUncertaintyConfig,
        *,
        member_seeds: Sequence[int],
    ) -> None:
        config.validate()
        seeds = tuple(int(seed) for seed in member_seeds)
        if len(seeds) != config.member_count or len(set(seeds)) != len(seeds):
            raise ValueError("uncertainty ensemble member seeds differ")
        if any(seed < 0 for seed in seeds):
            raise ValueError("uncertainty ensemble member seeds must be non-negative")
        super().__init__(
            parent,
            metadata,
            ActionRelativeAdvantageConfig(
                hidden_dim=config.hidden_dim,
                advantage_threshold=config.advantage_threshold,
                target_clip=config.target_clip,
                target_scale=config.target_scale,
            ),
        )
        del self.scorer
        self.config = config
        self.member_seeds = seeds
        self.member_scorers = nn.ModuleList(
            [self._new_member_scorer(seed) for seed in self.member_seeds]
        )
        self.bootstrap_samples: tuple[Any, ...] = ()

    def _new_member_scorer(self, seed: int) -> nn.Sequential:
        device = next(self.parent.parameters()).device
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(seed)
            scorer = nn.Sequential(
                nn.Linear(self.feature_dim, self.config.hidden_dim),
                nn.ReLU(),
                nn.Linear(self.config.hidden_dim, 1),
            ).to(device)
            nn.init.zeros_(scorer[-1].weight)
            nn.init.zeros_(scorer[-1].bias)
        return scorer

    def _candidate_features(
        self,
        continuous: torch.Tensor,
        card_ids: torch.Tensor,
        potion_ids: torch.Tensor,
        relic_ids: torch.Tensor,
        action_masks: torch.Tensor,
        guard_actions: torch.Tensor,
        candidate_actions: torch.Tensor,
    ) -> torch.Tensor:
        (
            continuous,
            card_ids,
            potion_ids,
            relic_ids,
            action_masks,
            guard_actions,
        ) = self._validated_state_inputs(
            continuous,
            card_ids,
            potion_ids,
            relic_ids,
            action_masks,
            guard_actions,
        )
        candidate_actions = candidate_actions.reshape(-1).long()
        if candidate_actions.shape != guard_actions.shape:
            raise ValueError("uncertainty ensemble candidate action shape differs")
        if bool((candidate_actions < 0).any()) or bool(
            (candidate_actions >= self.metadata["action_dim"]).any()
        ):
            raise ValueError("uncertainty ensemble candidate action is outside action space")
        rows = torch.arange(candidate_actions.numel(), device=candidate_actions.device)
        if not bool(action_masks[rows, candidate_actions].all()):
            raise ValueError("uncertainty ensemble candidate action must be legal")
        if bool(candidate_actions.eq(guard_actions).any()):
            raise ValueError("uncertainty ensemble candidate action duplicates guard")
        latent = self._parent_latent(continuous, card_ids, potion_ids, relic_ids)
        action_dim = self.metadata["action_dim"]
        return torch.cat(
            (
                latent,
                F.one_hot(guard_actions, num_classes=action_dim).float(),
                F.one_hot(candidate_actions, num_classes=action_dim).float(),
                action_masks.float(),
            ),
            dim=1,
        )

    def score_member_candidates(
        self,
        member_index: int,
        continuous: torch.Tensor,
        card_ids: torch.Tensor,
        potion_ids: torch.Tensor,
        relic_ids: torch.Tensor,
        action_masks: torch.Tensor,
        guard_actions: torch.Tensor,
        candidate_actions: torch.Tensor,
    ) -> torch.Tensor:
        if not 0 <= int(member_index) < len(self.member_scorers):
            raise ValueError("uncertainty ensemble member index differs")
        features = self._candidate_features(
            continuous,
            card_ids,
            potion_ids,
            relic_ids,
            action_masks,
            guard_actions,
            candidate_actions,
        )
        predictions = (
            self.member_scorers[int(member_index)](features).squeeze(1)
            * float(self.config.target_scale)
        )
        if not bool(torch.isfinite(predictions).all()):
            raise ValueError("uncertainty ensemble predictions must be finite")
        return predictions

    def score_candidate_statistics(
        self,
        continuous: torch.Tensor,
        card_ids: torch.Tensor,
        potion_ids: torch.Tensor,
        relic_ids: torch.Tensor,
        action_masks: torch.Tensor,
        guard_actions: torch.Tensor,
        candidate_actions: torch.Tensor,
    ) -> ActionRelativeCandidateStatistics:
        features = self._candidate_features(
            continuous,
            card_ids,
            potion_ids,
            relic_ids,
            action_masks,
            guard_actions,
            candidate_actions,
        )
        predictions = torch.stack(
            [
                scorer(features).squeeze(1) * float(self.config.target_scale)
                for scorer in self.member_scorers
            ],
            dim=1,
        )
        if not bool(torch.isfinite(predictions).all()):
            raise ValueError("uncertainty ensemble predictions must be finite")
        means = predictions.mean(dim=1)
        standard_deviations = predictions.std(dim=1, unbiased=True)
        lower = means - float(self.config.confidence_scale) * standard_deviations
        return ActionRelativeCandidateStatistics(
            member_predictions=predictions,
            means=means,
            standard_deviations=standard_deviations,
            lower_confidence_scores=lower,
        )

    def score_candidates(self, *args: Any, **kwargs: Any) -> torch.Tensor:
        return self.score_candidate_statistics(*args, **kwargs).lower_confidence_scores

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
    ) -> ActionRelativeEnsembleSelection:
        (
            continuous,
            card_ids,
            potion_ids,
            relic_ids,
            action_masks,
            guard_actions,
        ) = self._validated_state_inputs(
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
                raise ValueError("uncertainty ensemble alternative mask shape differs")
            allowed = alternative_masks.bool().clone()
            if bool((allowed & ~action_masks).any()):
                raise ValueError("uncertainty ensemble alternatives contain illegal actions")
            if bool(allowed[rows, guard_actions].any()):
                raise ValueError("uncertainty ensemble alternatives contain guard action")
        forbidden = sorted(forbidden_action_indices)
        for action in forbidden:
            if not isinstance(action, int) or isinstance(action, bool) or not (
                0 <= action < self.metadata["action_dim"]
            ):
                raise ValueError("uncertainty ensemble forbidden action is invalid")
            allowed[:, action] = False

        residual_actions = guard_actions.clone()
        lower_scores = torch.full(
            (batch_size,), float("-inf"), dtype=continuous.dtype, device=continuous.device
        )
        member_means = lower_scores.clone()
        member_stds = lower_scores.clone()
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
            score_matrix = torch.full_like(action_masks.float(), float("-inf"))
            score_matrix[state_rows, candidates] = stats.lower_confidence_scores
            best_scores, best_actions = score_matrix.max(dim=1)
            residual_actions[has_allowed] = best_actions[has_allowed]
            lower_scores[has_allowed] = best_scores[has_allowed]
            best_pair_mask = candidates.eq(best_actions[state_rows])
            best_rows = state_rows[best_pair_mask]
            member_means[best_rows] = stats.means[best_pair_mask]
            member_stds[best_rows] = stats.standard_deviations[best_pair_mask]
        gate_open = has_allowed & lower_scores.ge(float(self.config.advantage_threshold))
        actions = torch.where(gate_open, residual_actions, guard_actions)
        if not bool(action_masks[rows, actions].all()):
            raise RuntimeError("uncertainty ensemble selected an illegal action")
        forbidden_selection_count = sum(
            int(actions[gate_open].eq(action).sum().item()) for action in forbidden
        )
        return ActionRelativeEnsembleSelection(
            actions=actions,
            guard_actions=guard_actions,
            residual_actions=residual_actions,
            predicted_advantages=lower_scores,
            gate_open=gate_open,
            member_means=member_means,
            member_standard_deviations=member_stds,
            telemetry={
                "row_count": int(batch_size),
                "intervention_count": int(gate_open.sum().item()),
                "guard_preserved_count": int((~gate_open).sum().item()),
                "no_allowed_alternative_count": int((~has_allowed).sum().item()),
                "forbidden_action_indices": forbidden,
                "forbidden_action_selection_count": forbidden_selection_count,
                "advantage_threshold": float(self.config.advantage_threshold),
                "confidence_scale": float(self.config.confidence_scale),
                "member_count": int(self.config.member_count),
            },
        )


def build_ensemble_development_artifact(
    ensemble: ActionRelativeUncertaintyEnsemble,
    *,
    parent_checkpoint_sha256: str,
    corpus_sha256: Mapping[str, str],
    recipe: Mapping[str, Any],
    bootstrap_sha256: Sequence[str],
    telemetry: Mapping[str, Any],
) -> dict[str, Any]:
    corpus = {
        name: _validate_sha256(value, f"{name} corpus")
        for name, value in sorted(corpus_sha256.items())
    }
    if set(corpus) != {"train", "evaluation"}:
        raise ValueError("uncertainty ensemble corpus identities differ")
    bootstraps = [
        _validate_sha256(value, "bootstrap identity") for value in bootstrap_sha256
    ]
    if len(bootstraps) != ensemble.config.member_count or len(set(bootstraps)) != len(
        bootstraps
    ):
        raise ValueError("uncertainty ensemble bootstrap identities differ")
    member_states = [_cpu_state(scorer.state_dict()) for scorer in ensemble.member_scorers]
    return {
        "checkpoint_schema_version": ARTIFACT_SCHEMA_VERSION,
        "checkpoint_kind": ARTIFACT_KIND,
        "production_compatible": False,
        "metadata": dict(ensemble.metadata),
        "config": asdict(ensemble.config),
        "recipe": copy.deepcopy(dict(recipe)),
        "member_seeds": list(ensemble.member_seeds),
        "parent_checkpoint_sha256": _validate_sha256(
            parent_checkpoint_sha256, "parent checkpoint"
        ),
        "parent_state_dict_sha256": state_dict_sha256(ensemble.parent.state_dict()),
        "corpus_sha256": corpus,
        "bootstrap_sha256": bootstraps,
        "bootstrap_manifest_sha256": _manifest_sha256(bootstraps),
        "member_state_dicts": member_states,
        "member_state_dict_sha256": [state_dict_sha256(state) for state in member_states],
        "telemetry": copy.deepcopy(dict(telemetry)),
        "authority": {
            "development_only": True,
            "gameplay": False,
            "qualification": False,
            "promotion": False,
        },
    }


def load_ensemble_development_artifact(
    parent: nn.Module,
    metadata: Mapping[str, Any],
    artifact: Mapping[str, Any],
    *,
    expected_parent_checkpoint_sha256: str,
    expected_corpus_sha256: Mapping[str, str],
    expected_recipe: Mapping[str, Any],
) -> ActionRelativeUncertaintyEnsemble:
    required = {
        "checkpoint_schema_version",
        "checkpoint_kind",
        "production_compatible",
        "metadata",
        "config",
        "recipe",
        "member_seeds",
        "parent_checkpoint_sha256",
        "parent_state_dict_sha256",
        "corpus_sha256",
        "bootstrap_sha256",
        "bootstrap_manifest_sha256",
        "member_state_dicts",
        "member_state_dict_sha256",
        "telemetry",
        "authority",
    }
    if not isinstance(artifact, Mapping) or set(artifact) != required:
        raise ValueError("uncertainty ensemble artifact keys differ")
    if artifact["checkpoint_schema_version"] != ARTIFACT_SCHEMA_VERSION:
        raise ValueError("uncertainty ensemble artifact schema differs")
    if (
        artifact["checkpoint_kind"] != ARTIFACT_KIND
        or artifact["production_compatible"] is not False
    ):
        raise ValueError("uncertainty ensemble artifact kind differs")
    if dict(artifact["recipe"]) != dict(expected_recipe):
        raise ValueError("uncertainty ensemble recipe differs")
    if artifact["metadata"] != dict(metadata):
        raise ValueError("uncertainty ensemble metadata differs")
    if _validate_sha256(
        artifact["parent_checkpoint_sha256"], "parent checkpoint"
    ) != _validate_sha256(
        expected_parent_checkpoint_sha256,
        "expected parent checkpoint",
    ):
        raise ValueError("uncertainty ensemble parent checkpoint differs")
    if state_dict_sha256(parent.state_dict()) != _validate_sha256(
        artifact["parent_state_dict_sha256"], "parent state"
    ):
        raise ValueError("uncertainty ensemble parent state differs")
    observed_corpus = {
        name: _validate_sha256(value, f"{name} corpus")
        for name, value in artifact["corpus_sha256"].items()
    }
    expected_corpus = {
        name: _validate_sha256(value, f"expected {name} corpus")
        for name, value in expected_corpus_sha256.items()
    }
    if observed_corpus != expected_corpus or set(observed_corpus) != {"train", "evaluation"}:
        raise ValueError("uncertainty ensemble corpus identity differs")
    bootstraps = [
        _validate_sha256(value, "bootstrap identity")
        for value in artifact["bootstrap_sha256"]
    ]
    if len(set(bootstraps)) != len(bootstraps):
        raise ValueError("uncertainty ensemble bootstrap identities differ")
    if _manifest_sha256(bootstraps) != _validate_sha256(
        artifact["bootstrap_manifest_sha256"], "bootstrap identity"
    ):
        raise ValueError("uncertainty ensemble bootstrap identity differs")
    try:
        config = ActionRelativeUncertaintyConfig(**dict(artifact["config"]))
    except TypeError as exc:
        raise ValueError("uncertainty ensemble config differs") from exc
    expected_member_seeds = list(expected_recipe.get("member_seeds", ()))
    if list(artifact["member_seeds"]) != expected_member_seeds:
        raise ValueError("uncertainty ensemble member seeds differ")
    ensemble = ActionRelativeUncertaintyEnsemble(
        parent,
        metadata,
        config,
        member_seeds=artifact["member_seeds"],
    )
    if len(bootstraps) != config.member_count:
        raise ValueError("uncertainty ensemble bootstrap identity count differs")
    states = artifact["member_state_dicts"]
    hashes = artifact["member_state_dict_sha256"]
    if not isinstance(states, Sequence) or len(states) != config.member_count:
        raise ValueError("uncertainty ensemble member states differ")
    if not isinstance(hashes, Sequence) or len(hashes) != config.member_count:
        raise ValueError("uncertainty ensemble member hashes differ")
    for scorer, observed, expected_hash in zip(ensemble.member_scorers, states, hashes):
        state = _validated_scorer_state(observed, scorer.state_dict())
        if state_dict_sha256(state) != _validate_sha256(expected_hash, "member state"):
            raise ValueError("uncertainty ensemble member state identity differs")
        scorer.load_state_dict(state, strict=True)
    if artifact["authority"] != {
        "development_only": True,
        "gameplay": False,
        "qualification": False,
        "promotion": False,
    }:
        raise ValueError("uncertainty ensemble artifact authority differs")
    return ensemble
