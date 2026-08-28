"""Development-only action-relative post-guard advantage scorer."""

from __future__ import annotations

import copy
from dataclasses import asdict, dataclass
import math
from typing import Any, Mapping, NamedTuple, Sequence

import torch
import torch.nn as nn
import torch.nn.functional as F

from spirecomm.ai.rl.v2.latent_gated_adapter import state_dict_sha256


ARTIFACT_SCHEMA_VERSION = 1
ARTIFACT_KIND = "combat_action_relative_advantage_residual_development"


@dataclass(frozen=True)
class ActionRelativeAdvantageConfig:
    hidden_dim: int = 64
    advantage_threshold: float = 0.5
    target_clip: float = 20.0
    target_scale: float = 10.0

    def validate(self) -> None:
        if not isinstance(self.hidden_dim, int) or isinstance(self.hidden_dim, bool):
            raise ValueError("action-relative hidden_dim must be an integer")
        if self.hidden_dim <= 0:
            raise ValueError("action-relative hidden_dim must be positive")
        for name, value in (
            ("advantage_threshold", self.advantage_threshold),
            ("target_clip", self.target_clip),
            ("target_scale", self.target_scale),
        ):
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ValueError(f"action-relative {name} must be numeric")
            if not math.isfinite(float(value)) or float(value) <= 0.0:
                raise ValueError(f"action-relative {name} must be finite and positive")


class ActionRelativeSelection(NamedTuple):
    actions: torch.Tensor
    guard_actions: torch.Tensor
    residual_actions: torch.Tensor
    predicted_advantages: torch.Tensor
    gate_open: torch.Tensor
    telemetry: dict[str, Any]


def _normalized_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "network_type",
        "continuous_dim",
        "action_dim",
        "card_vocab",
        "potion_vocab",
        "relic_vocab",
        "card_slots",
        "potion_slots",
        "relic_slots",
    }
    if not isinstance(metadata, Mapping) or set(metadata) != required:
        raise ValueError("action-relative metadata keys differ")
    normalized = dict(metadata)
    if normalized["network_type"] not in {"standard", "dueling"}:
        raise ValueError("action-relative network type is invalid")
    for name in required - {"network_type"}:
        value = normalized[name]
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ValueError(f"action-relative metadata {name} must be positive")
        normalized[name] = int(value)
    return normalized


def _last_linear_output(module: nn.Module) -> int:
    for layer in reversed(tuple(module.modules())):
        if isinstance(layer, nn.Linear):
            return int(layer.out_features)
    raise ValueError("action-relative parent hidden layers contain no linear output")


def _validate_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"action-relative {label} SHA-256 is missing")
    normalized = value.lower()
    if len(normalized) != 64 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise ValueError(f"action-relative {label} SHA-256 is invalid")
    return normalized


def expand_action_relative_examples(
    tensors: Mapping[str, torch.Tensor],
    metadata: Sequence[Mapping[str, Any]],
    *,
    action_dim: int,
) -> dict[str, torch.Tensor]:
    required = {
        "continuous",
        "card_ids",
        "potion_ids",
        "relic_ids",
        "action_masks",
        "guard_actions",
    }
    if not isinstance(tensors, Mapping) or not required.issubset(tensors):
        raise ValueError("action-relative corpus tensors are incomplete")
    if not isinstance(action_dim, int) or isinstance(action_dim, bool) or action_dim <= 0:
        raise ValueError("action-relative action_dim must be positive")
    row_count = int(tensors["guard_actions"].numel())
    if len(metadata) != row_count:
        raise ValueError("action-relative corpus metadata row count differs")
    if tensors["action_masks"].shape != (row_count, action_dim):
        raise ValueError("action-relative corpus action mask shape differs")
    for name in required - {"guard_actions", "action_masks"}:
        value = tensors[name]
        if not isinstance(value, torch.Tensor) or value.dim() != 2:
            raise ValueError(f"action-relative corpus {name} shape differs")
        if value.shape[0] != row_count:
            raise ValueError(f"action-relative corpus {name} row count differs")

    action_masks = tensors["action_masks"].bool()
    guard_actions = tensors["guard_actions"].reshape(-1).long()
    rows = torch.arange(row_count, device=guard_actions.device)
    if bool((guard_actions < 0).any()) or bool((guard_actions >= action_dim).any()):
        raise ValueError("action-relative guard action is outside action space")
    if not bool(action_masks[rows, guard_actions].all()):
        raise ValueError("action-relative guard action is illegal")

    row_indices: list[int] = []
    candidate_actions: list[int] = []
    candidate_returns: list[float] = []
    guard_returns: list[float] = []
    raw_advantages: list[float] = []
    for row_index, row_metadata in enumerate(metadata):
        if not isinstance(row_metadata, Mapping):
            raise ValueError("action-relative corpus metadata row is invalid")
        metadata_guard = row_metadata.get("guard_action_index")
        if not isinstance(metadata_guard, int) or isinstance(metadata_guard, bool):
            raise ValueError("action-relative metadata guard action is invalid")
        guard_action = int(guard_actions[row_index])
        if metadata_guard != guard_action:
            raise ValueError("action-relative metadata guard action differs")
        guard_return = row_metadata.get("guard_return")
        if not isinstance(guard_return, (int, float)) or isinstance(guard_return, bool):
            raise ValueError("action-relative guard return is invalid")
        guard_return = float(guard_return)
        if not math.isfinite(guard_return):
            raise ValueError("action-relative guard return must be finite")
        branches = row_metadata.get("branch_returns")
        if not isinstance(branches, Mapping) or len(branches) < 2:
            raise ValueError("action-relative branch returns are missing")
        normalized_branches: dict[int, float] = {}
        for raw_action, raw_return in branches.items():
            try:
                action = int(raw_action)
            except (TypeError, ValueError) as exc:
                raise ValueError("action-relative branch identity is invalid") from exc
            if action in normalized_branches:
                raise ValueError("action-relative branch identity is duplicated")
            if not 0 <= action < action_dim:
                raise ValueError("action-relative branch action is outside action space")
            if not isinstance(raw_return, (int, float)) or isinstance(raw_return, bool):
                raise ValueError("action-relative branch return is invalid")
            branch_return = float(raw_return)
            if not math.isfinite(branch_return):
                raise ValueError("action-relative branch return must be finite")
            if not bool(action_masks[row_index, action]):
                raise ValueError("action-relative branch action is illegal")
            normalized_branches[action] = branch_return
        if guard_action not in normalized_branches or not math.isclose(
            normalized_branches[guard_action], guard_return, rel_tol=0.0, abs_tol=1e-6
        ):
            raise ValueError("action-relative guard branch return differs")
        alternatives = 0
        for action, branch_return in sorted(normalized_branches.items()):
            if action == guard_action:
                continue
            advantage = branch_return - guard_return
            if not math.isfinite(advantage):
                raise ValueError("action-relative advantage must be finite")
            row_indices.append(row_index)
            candidate_actions.append(action)
            candidate_returns.append(branch_return)
            guard_returns.append(guard_return)
            raw_advantages.append(advantage)
            alternatives += 1
        if alternatives == 0:
            raise ValueError("action-relative row has no alternative branch")

    device = guard_actions.device
    return {
        "row_indices": torch.tensor(row_indices, dtype=torch.long, device=device),
        "candidate_actions": torch.tensor(
            candidate_actions, dtype=torch.long, device=device
        ),
        "candidate_returns": torch.tensor(
            candidate_returns, dtype=torch.float32, device=device
        ),
        "guard_returns": torch.tensor(
            guard_returns, dtype=torch.float32, device=device
        ),
        "raw_advantages": torch.tensor(
            raw_advantages, dtype=torch.float32, device=device
        ),
    }


def transformed_advantage_targets(
    raw_advantages: torch.Tensor, config: ActionRelativeAdvantageConfig
) -> torch.Tensor:
    config.validate()
    raw_advantages = raw_advantages.float()
    if not bool(torch.isfinite(raw_advantages).all()):
        raise ValueError("action-relative targets must be finite")
    return raw_advantages.clamp(-config.target_clip, config.target_clip) / float(
        config.target_scale
    )


class ActionRelativeAdvantageResidual(nn.Module):
    """Frozen parent plus a shared candidate-relative scalar scorer."""

    def __init__(
        self,
        parent: nn.Module,
        metadata: Mapping[str, Any],
        config: ActionRelativeAdvantageConfig,
    ) -> None:
        super().__init__()
        config.validate()
        self.metadata = _normalized_metadata(metadata)
        self.config = config
        self.parent = copy.deepcopy(parent)
        self.parent.eval()
        for parameter in self.parent.parameters():
            parameter.requires_grad_(False)
        required_parent = (
            "card_embedding",
            "potion_embedding",
            "relic_embedding",
            "hidden_layers",
        )
        if any(not hasattr(self.parent, name) for name in required_parent):
            raise ValueError("action-relative parent structure is unsupported")
        self.parent_latent_dim = _last_linear_output(self.parent.hidden_layers)
        action_dim = self.metadata["action_dim"]
        self.feature_dim = self.parent_latent_dim + 3 * action_dim
        device = next(self.parent.parameters()).device
        self.scorer = nn.Sequential(
            nn.Linear(self.feature_dim, config.hidden_dim),
            nn.ReLU(),
            nn.Linear(config.hidden_dim, 1),
        ).to(device)
        nn.init.zeros_(self.scorer[-1].weight)
        nn.init.zeros_(self.scorer[-1].bias)

    def train(self, mode: bool = True):
        super().train(mode)
        self.parent.eval()
        return self

    def _validated_state_inputs(
        self,
        continuous: torch.Tensor,
        card_ids: torch.Tensor,
        potion_ids: torch.Tensor,
        relic_ids: torch.Tensor,
        action_masks: torch.Tensor,
        guard_actions: torch.Tensor,
    ) -> tuple[torch.Tensor, ...]:
        values = [continuous, card_ids, potion_ids, relic_ids, action_masks]
        values = [value.unsqueeze(0) if value.dim() == 1 else value for value in values]
        batch_size = values[0].shape[0]
        if any(value.dim() != 2 or value.shape[0] != batch_size for value in values):
            raise ValueError("action-relative inputs need one equal batch dimension")
        expected_widths = (
            self.metadata["continuous_dim"],
            self.metadata["card_slots"],
            self.metadata["potion_slots"],
            self.metadata["relic_slots"],
            self.metadata["action_dim"],
        )
        if any(value.shape[1] != width for value, width in zip(values, expected_widths)):
            raise ValueError("action-relative input width differs")
        continuous, card_ids, potion_ids, relic_ids, action_masks = values
        if not bool(torch.isfinite(continuous).all()):
            raise ValueError("action-relative continuous inputs must be finite")
        for name, ids, embedding in (
            ("card", card_ids, self.parent.card_embedding),
            ("potion", potion_ids, self.parent.potion_embedding),
            ("relic", relic_ids, self.parent.relic_embedding),
        ):
            if bool((ids < 0).any()) or bool((ids >= embedding.num_embeddings).any()):
                raise ValueError(f"action-relative {name} id is outside the vocabulary")
        action_masks = action_masks.bool()
        guard_actions = guard_actions.reshape(-1).long()
        if guard_actions.shape != (batch_size,):
            raise ValueError("action-relative guard action shape differs")
        if bool((guard_actions < 0).any()) or bool(
            (guard_actions >= self.metadata["action_dim"]).any()
        ):
            raise ValueError("action-relative guard action is outside action space")
        rows = torch.arange(batch_size, device=guard_actions.device)
        if not bool(action_masks[rows, guard_actions].all()):
            raise ValueError("action-relative guard action must be legal")
        return (
            continuous.float(),
            card_ids.long(),
            potion_ids.long(),
            relic_ids.long(),
            action_masks,
            guard_actions,
        )

    def _parent_latent(
        self,
        continuous: torch.Tensor,
        card_ids: torch.Tensor,
        potion_ids: torch.Tensor,
        relic_ids: torch.Tensor,
    ) -> torch.Tensor:
        self.parent.eval()
        with torch.no_grad():
            embedded = torch.cat(
                (
                    continuous,
                    self.parent.card_embedding(card_ids).flatten(1),
                    self.parent.potion_embedding(potion_ids).flatten(1),
                    self.parent.relic_embedding(relic_ids).flatten(1),
                ),
                dim=1,
            )
            latent = self.parent.hidden_layers(embedded)
        if not bool(torch.isfinite(latent).all()):
            raise ValueError("action-relative parent latent is non-finite")
        return latent

    def score_candidates(
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
        batch_size = guard_actions.numel()
        candidate_actions = candidate_actions.reshape(-1).long()
        if candidate_actions.shape != (batch_size,):
            raise ValueError("action-relative candidate action shape differs")
        if bool((candidate_actions < 0).any()) or bool(
            (candidate_actions >= self.metadata["action_dim"]).any()
        ):
            raise ValueError("action-relative candidate action is outside action space")
        rows = torch.arange(batch_size, device=candidate_actions.device)
        if not bool(action_masks[rows, candidate_actions].all()):
            raise ValueError("action-relative candidate action must be legal")
        if bool(candidate_actions.eq(guard_actions).any()):
            raise ValueError("action-relative candidate action duplicates guard")

        latent = self._parent_latent(continuous, card_ids, potion_ids, relic_ids)
        action_dim = self.metadata["action_dim"]
        features = torch.cat(
            (
                latent,
                F.one_hot(guard_actions, num_classes=action_dim).float(),
                F.one_hot(candidate_actions, num_classes=action_dim).float(),
                action_masks.float(),
            ),
            dim=1,
        )
        scaled = self.scorer(features).squeeze(1)
        predictions = scaled * float(self.config.target_scale)
        if not bool(torch.isfinite(predictions).all()):
            raise ValueError("action-relative predictions must be finite")
        return predictions

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
    ) -> ActionRelativeSelection:
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
                raise ValueError("action-relative alternative mask shape differs")
            allowed = alternative_masks.bool().clone()
            if bool((allowed & ~action_masks).any()):
                raise ValueError("action-relative alternative mask contains illegal actions")
            if bool(allowed[rows, guard_actions].any()):
                raise ValueError("action-relative alternative mask contains guard action")
        forbidden = sorted(forbidden_action_indices)
        for action in forbidden:
            if not isinstance(action, int) or isinstance(action, bool) or not (
                0 <= action < self.metadata["action_dim"]
            ):
                raise ValueError("action-relative forbidden action is invalid")
            allowed[:, action] = False

        candidate_pairs = allowed.nonzero(as_tuple=False)
        residual_actions = guard_actions.clone()
        predicted_advantages = torch.full(
            (batch_size,), float("-inf"), dtype=continuous.dtype, device=continuous.device
        )
        has_allowed = allowed.any(dim=1)
        if candidate_pairs.numel():
            state_rows = candidate_pairs[:, 0]
            candidates = candidate_pairs[:, 1]
            pair_predictions = self.score_candidates(
                continuous[state_rows],
                card_ids[state_rows],
                potion_ids[state_rows],
                relic_ids[state_rows],
                action_masks[state_rows],
                guard_actions[state_rows],
                candidates,
            )
            score_matrix = torch.full(
                action_masks.shape,
                float("-inf"),
                dtype=pair_predictions.dtype,
                device=pair_predictions.device,
            )
            score_matrix[state_rows, candidates] = pair_predictions
            best_scores, best_actions = score_matrix.max(dim=1)
            residual_actions[has_allowed] = best_actions[has_allowed]
            predicted_advantages[has_allowed] = best_scores[has_allowed]
        gate_open = has_allowed & predicted_advantages.ge(
            float(self.config.advantage_threshold)
        )
        actions = torch.where(gate_open, residual_actions, guard_actions)
        if not bool(action_masks[rows, actions].all()):
            raise RuntimeError("action-relative residual selected an illegal action")
        if bool(gate_open.any()) and not bool(
            allowed[rows[gate_open], actions[gate_open]].all()
        ):
            raise RuntimeError("action-relative residual selected a forbidden action")
        forbidden_selection_count = sum(
            int(actions[gate_open].eq(action).sum().item()) for action in forbidden
        )
        return ActionRelativeSelection(
            actions=actions,
            guard_actions=guard_actions,
            residual_actions=residual_actions,
            predicted_advantages=predicted_advantages,
            gate_open=gate_open,
            telemetry={
                "row_count": int(batch_size),
                "intervention_count": int(gate_open.sum().item()),
                "guard_preserved_count": int((~gate_open).sum().item()),
                "no_allowed_alternative_count": int((~has_allowed).sum().item()),
                "forbidden_action_indices": forbidden,
                "forbidden_action_selection_count": forbidden_selection_count,
                "advantage_threshold": float(self.config.advantage_threshold),
            },
        )


def _cpu_state(state: Mapping[str, torch.Tensor]) -> dict[str, torch.Tensor]:
    return {name: tensor.detach().cpu().clone() for name, tensor in state.items()}


def build_development_artifact(
    residual: ActionRelativeAdvantageResidual,
    *,
    parent_checkpoint_sha256: str,
    corpus_sha256: Mapping[str, str],
    recipe: Mapping[str, Any],
    telemetry: Mapping[str, Any],
) -> dict[str, Any]:
    corpus = {
        name: _validate_sha256(value, f"{name} corpus")
        for name, value in sorted(corpus_sha256.items())
    }
    if set(corpus) != {"train", "evaluation"}:
        raise ValueError("action-relative corpus identities differ")
    if not isinstance(recipe, Mapping) or not recipe:
        raise ValueError("action-relative recipe is missing")
    scorer_state = _cpu_state(residual.scorer.state_dict())
    return {
        "checkpoint_schema_version": ARTIFACT_SCHEMA_VERSION,
        "checkpoint_kind": ARTIFACT_KIND,
        "production_compatible": False,
        "metadata": dict(residual.metadata),
        "config": asdict(residual.config),
        "recipe": copy.deepcopy(dict(recipe)),
        "parent_checkpoint_sha256": _validate_sha256(
            parent_checkpoint_sha256, "parent checkpoint"
        ),
        "parent_state_dict_sha256": state_dict_sha256(residual.parent.state_dict()),
        "corpus_sha256": corpus,
        "scorer_state_dict": scorer_state,
        "scorer_state_dict_sha256": state_dict_sha256(scorer_state),
        "telemetry": copy.deepcopy(dict(telemetry)),
        "authority": {
            "development_only": True,
            "gameplay": False,
            "qualification": False,
            "promotion": False,
        },
    }


def _validated_scorer_state(
    observed: Any, expected: Mapping[str, torch.Tensor]
) -> dict[str, torch.Tensor]:
    if not isinstance(observed, Mapping) or set(observed) != set(expected):
        raise ValueError("action-relative scorer state keys differ")
    normalized: dict[str, torch.Tensor] = {}
    for name, expected_tensor in expected.items():
        tensor = observed[name]
        if not isinstance(tensor, torch.Tensor):
            raise ValueError("action-relative scorer state contains a non-tensor")
        if tensor.shape != expected_tensor.shape or tensor.dtype != expected_tensor.dtype:
            raise ValueError("action-relative scorer state tensor differs")
        if not bool(torch.isfinite(tensor).all()):
            raise ValueError("action-relative scorer state is non-finite")
        normalized[name] = tensor.detach().cpu().clone()
    return normalized


def load_development_artifact(
    parent: nn.Module,
    metadata: Mapping[str, Any],
    artifact: Mapping[str, Any],
    *,
    expected_parent_checkpoint_sha256: str,
    expected_corpus_sha256: Mapping[str, str],
    expected_recipe: Mapping[str, Any],
) -> ActionRelativeAdvantageResidual:
    required = {
        "checkpoint_schema_version",
        "checkpoint_kind",
        "production_compatible",
        "metadata",
        "config",
        "recipe",
        "parent_checkpoint_sha256",
        "parent_state_dict_sha256",
        "corpus_sha256",
        "scorer_state_dict",
        "scorer_state_dict_sha256",
        "telemetry",
        "authority",
    }
    if not isinstance(artifact, Mapping) or set(artifact) != required:
        raise ValueError("action-relative artifact keys differ")
    if artifact["checkpoint_schema_version"] != ARTIFACT_SCHEMA_VERSION:
        raise ValueError("action-relative artifact schema differs")
    if artifact["checkpoint_kind"] != ARTIFACT_KIND:
        raise ValueError("action-relative artifact kind differs")
    if artifact["production_compatible"] is not False:
        raise ValueError("action-relative artifact must not be production-compatible")
    normalized_metadata = _normalized_metadata(metadata)
    if artifact["metadata"] != normalized_metadata:
        raise ValueError("action-relative artifact metadata differs")
    if _validate_sha256(
        artifact["parent_checkpoint_sha256"], "artifact parent checkpoint"
    ) != _validate_sha256(expected_parent_checkpoint_sha256, "expected parent checkpoint"):
        raise ValueError("action-relative parent checkpoint identity differs")
    observed_corpus = {
        name: _validate_sha256(value, f"artifact {name} corpus")
        for name, value in artifact["corpus_sha256"].items()
    }
    expected_corpus = {
        name: _validate_sha256(value, f"expected {name} corpus")
        for name, value in expected_corpus_sha256.items()
    }
    if observed_corpus != expected_corpus or set(observed_corpus) != {
        "train",
        "evaluation",
    }:
        raise ValueError("action-relative corpus identity differs")
    if state_dict_sha256(parent.state_dict()) != _validate_sha256(
        artifact["parent_state_dict_sha256"], "parent state"
    ):
        raise ValueError("action-relative parent state identity differs")
    if not isinstance(artifact["config"], Mapping):
        raise ValueError("action-relative artifact config is missing")
    try:
        config = ActionRelativeAdvantageConfig(**dict(artifact["config"]))
    except TypeError as exc:
        raise ValueError("action-relative artifact config differs") from exc
    if not isinstance(artifact["recipe"], Mapping) or dict(artifact["recipe"]) != dict(
        expected_recipe
    ):
        raise ValueError("action-relative artifact recipe differs")
    if artifact["authority"] != {
        "development_only": True,
        "gameplay": False,
        "qualification": False,
        "promotion": False,
    }:
        raise ValueError("action-relative artifact authority differs")
    residual = ActionRelativeAdvantageResidual(parent, normalized_metadata, config)
    scorer_state = _validated_scorer_state(
        artifact["scorer_state_dict"], residual.scorer.state_dict()
    )
    if state_dict_sha256(scorer_state) != _validate_sha256(
        artifact["scorer_state_dict_sha256"], "scorer state"
    ):
        raise ValueError("action-relative scorer state identity differs")
    residual.scorer.load_state_dict(scorer_state, strict=True)
    return residual
