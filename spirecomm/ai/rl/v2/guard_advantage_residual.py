"""Development-only post-guard residual for paired advantage labels."""

from __future__ import annotations

import copy
from dataclasses import asdict, dataclass
import math
from typing import Any, Mapping, NamedTuple

import torch
import torch.nn as nn
import torch.nn.functional as F

from spirecomm.ai.rl.v2.latent_gated_adapter import state_dict_sha256


ARTIFACT_SCHEMA_VERSION = 1
ARTIFACT_KIND = "combat_guard_advantage_residual_development"


@dataclass(frozen=True)
class GuardAdvantageResidualConfig:
    hidden_dim: int = 64
    gate_threshold: float = 0.5

    def validate(self) -> None:
        if not isinstance(self.hidden_dim, int) or isinstance(self.hidden_dim, bool):
            raise ValueError("guard residual hidden_dim must be an integer")
        if self.hidden_dim <= 0:
            raise ValueError("guard residual hidden_dim must be positive")
        if not math.isfinite(self.gate_threshold) or not (
            0.0 < self.gate_threshold < 1.0
        ):
            raise ValueError("guard residual threshold must be between zero and one")


class ResidualComponents(NamedTuple):
    parent_latent: torch.Tensor
    features: torch.Tensor
    gate_logits: torch.Tensor
    action_logits: torch.Tensor
    action_masks: torch.Tensor
    alternative_masks: torch.Tensor
    guard_actions: torch.Tensor


class ResidualSelection(NamedTuple):
    actions: torch.Tensor
    guard_actions: torch.Tensor
    residual_actions: torch.Tensor
    gate_probabilities: torch.Tensor
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
        raise ValueError("guard residual metadata keys differ")
    normalized = dict(metadata)
    if normalized["network_type"] not in {"standard", "dueling"}:
        raise ValueError("guard residual network type is invalid")
    for name in required - {"network_type"}:
        value = normalized[name]
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ValueError(f"guard residual metadata {name} must be positive")
        normalized[name] = int(value)
    return normalized


def _last_linear_output(module: nn.Module) -> int:
    for layer in reversed(tuple(module.modules())):
        if isinstance(layer, nn.Linear):
            return int(layer.out_features)
    raise ValueError("guard residual parent hidden layers contain no linear output")


class GuardAdvantageResidual(nn.Module):
    """Frozen parent plus a post-guard abstaining gate and action head."""

    def __init__(
        self,
        parent: nn.Module,
        metadata: Mapping[str, Any],
        config: GuardAdvantageResidualConfig,
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
            raise ValueError("guard residual parent structure is unsupported")

        self.parent_latent_dim = _last_linear_output(self.parent.hidden_layers)
        action_dim = self.metadata["action_dim"]
        self.feature_dim = self.parent_latent_dim + 2 * action_dim
        device = next(self.parent.parameters()).device
        self.gate = nn.Sequential(
            nn.Linear(self.feature_dim, config.hidden_dim),
            nn.ReLU(),
            nn.Linear(config.hidden_dim, 1),
        ).to(device)
        self.action_head = nn.Sequential(
            nn.Linear(self.feature_dim, config.hidden_dim),
            nn.ReLU(),
            nn.Linear(config.hidden_dim, action_dim),
        ).to(device)
        nn.init.zeros_(self.gate[-1].weight)
        nn.init.zeros_(self.gate[-1].bias)
        nn.init.zeros_(self.action_head[-1].weight)
        nn.init.zeros_(self.action_head[-1].bias)

    def train(self, mode: bool = True):
        super().train(mode)
        self.parent.eval()
        return self

    def _validated_inputs(
        self,
        continuous: torch.Tensor,
        card_ids: torch.Tensor,
        potion_ids: torch.Tensor,
        relic_ids: torch.Tensor,
        action_masks: torch.Tensor,
        guard_actions: torch.Tensor,
        alternative_masks: torch.Tensor | None,
    ) -> tuple[
        torch.Tensor,
        torch.Tensor,
        torch.Tensor,
        torch.Tensor,
        torch.Tensor,
        torch.Tensor,
        torch.Tensor,
    ]:
        values = [continuous, card_ids, potion_ids, relic_ids, action_masks]
        values = [value.unsqueeze(0) if value.dim() == 1 else value for value in values]
        batch_size = values[0].shape[0]
        if any(value.dim() != 2 or value.shape[0] != batch_size for value in values):
            raise ValueError("guard residual inputs need one equal batch dimension")
        expected_widths = (
            self.metadata["continuous_dim"],
            self.metadata["card_slots"],
            self.metadata["potion_slots"],
            self.metadata["relic_slots"],
            self.metadata["action_dim"],
        )
        if any(value.shape[1] != width for value, width in zip(values, expected_widths)):
            raise ValueError("guard residual input width differs")
        continuous, card_ids, potion_ids, relic_ids, action_masks = values
        if not bool(torch.isfinite(continuous).all()):
            raise ValueError("guard residual continuous inputs must be finite")
        for name, ids, embedding in (
            ("card", card_ids, self.parent.card_embedding),
            ("potion", potion_ids, self.parent.potion_embedding),
            ("relic", relic_ids, self.parent.relic_embedding),
        ):
            if bool((ids < 0).any()) or bool((ids >= embedding.num_embeddings).any()):
                raise ValueError(f"guard residual {name} id is outside the vocabulary")
        action_masks = action_masks.bool()
        guard_actions = guard_actions.reshape(-1).long()
        if guard_actions.shape != (batch_size,):
            raise ValueError("guard residual guard action shape differs")
        if bool((guard_actions < 0).any()) or bool(
            (guard_actions >= self.metadata["action_dim"]).any()
        ):
            raise ValueError("guard residual guard action is outside the action space")
        rows = torch.arange(batch_size, device=guard_actions.device)
        if not bool(action_masks[rows, guard_actions].all()):
            raise ValueError("guard residual guard action must be legal")

        if alternative_masks is None:
            alternative_masks = action_masks.clone()
            alternative_masks[rows, guard_actions] = False
        else:
            if alternative_masks.dim() == 1:
                alternative_masks = alternative_masks.unsqueeze(0)
            if alternative_masks.shape != action_masks.shape:
                raise ValueError("guard residual alternative mask shape differs")
            alternative_masks = alternative_masks.bool()
            if bool((alternative_masks & ~action_masks).any()):
                raise ValueError("guard residual alternative mask contains illegal actions")
            if bool(alternative_masks[rows, guard_actions].any()):
                raise ValueError("guard residual alternative mask contains guard action")
        if not bool(alternative_masks.any(dim=1).all()):
            raise ValueError("guard residual requires a legal alternative action")
        return (
            continuous.float(),
            card_ids.long(),
            potion_ids.long(),
            relic_ids.long(),
            action_masks,
            guard_actions,
            alternative_masks,
        )

    def residual_components(
        self,
        continuous: torch.Tensor,
        card_ids: torch.Tensor,
        potion_ids: torch.Tensor,
        relic_ids: torch.Tensor,
        action_masks: torch.Tensor,
        guard_actions: torch.Tensor,
        alternative_masks: torch.Tensor | None = None,
    ) -> ResidualComponents:
        (
            continuous,
            card_ids,
            potion_ids,
            relic_ids,
            action_masks,
            guard_actions,
            alternative_masks,
        ) = self._validated_inputs(
            continuous,
            card_ids,
            potion_ids,
            relic_ids,
            action_masks,
            guard_actions,
            alternative_masks,
        )
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
            parent_latent = self.parent.hidden_layers(embedded)
        guard_one_hot = F.one_hot(
            guard_actions, num_classes=self.metadata["action_dim"]
        ).float()
        features = torch.cat((parent_latent, guard_one_hot, action_masks.float()), dim=1)
        gate_logits = self.gate(features).squeeze(1)
        action_logits = self.action_head(features)
        if not bool(torch.isfinite(parent_latent).all()) or not bool(
            torch.isfinite(gate_logits).all()
        ) or not bool(torch.isfinite(action_logits).all()):
            raise ValueError("guard residual features and outputs must be finite")
        return ResidualComponents(
            parent_latent=parent_latent,
            features=features,
            gate_logits=gate_logits,
            action_logits=action_logits,
            action_masks=action_masks,
            alternative_masks=alternative_masks,
            guard_actions=guard_actions,
        )

    def select_actions(
        self,
        continuous: torch.Tensor,
        card_ids: torch.Tensor,
        potion_ids: torch.Tensor,
        relic_ids: torch.Tensor,
        action_masks: torch.Tensor,
        guard_actions: torch.Tensor,
        alternative_masks: torch.Tensor | None = None,
    ) -> ResidualSelection:
        components = self.residual_components(
            continuous,
            card_ids,
            potion_ids,
            relic_ids,
            action_masks,
            guard_actions,
            alternative_masks,
        )
        residual_actions = components.action_logits.masked_fill(
            ~components.alternative_masks, float("-inf")
        ).argmax(dim=1)
        probabilities = torch.sigmoid(components.gate_logits)
        gate_open = probabilities.ge(self.config.gate_threshold)
        actions = torch.where(gate_open, residual_actions, components.guard_actions)
        rows = torch.arange(actions.numel(), device=actions.device)
        if not bool(components.action_masks[rows, actions].all()):
            raise RuntimeError("guard residual selected an illegal action")
        if bool(gate_open.any()) and not bool(
            components.alternative_masks[rows[gate_open], actions[gate_open]].all()
        ):
            raise RuntimeError("guard residual selected a non-alternative action")
        return ResidualSelection(
            actions=actions,
            guard_actions=components.guard_actions,
            residual_actions=residual_actions,
            gate_probabilities=probabilities,
            gate_open=gate_open,
            telemetry={
                "row_count": int(actions.numel()),
                "gate_open_count": int(gate_open.sum().item()),
                "guard_preserved_count": int(actions.eq(components.guard_actions).sum().item()),
                "intervention_count": int(actions.ne(components.guard_actions).sum().item()),
                "gate_threshold": float(self.config.gate_threshold),
            },
        )


def residual_training_loss(
    residual: GuardAdvantageResidual,
    continuous: torch.Tensor,
    card_ids: torch.Tensor,
    potion_ids: torch.Tensor,
    relic_ids: torch.Tensor,
    action_masks: torch.Tensor,
    guard_actions: torch.Tensor,
    alternative_masks: torch.Tensor,
    *,
    target_actions: torch.Tensor,
    positive: torch.Tensor,
) -> tuple[torch.Tensor, dict[str, Any]]:
    components = residual.residual_components(
        continuous,
        card_ids,
        potion_ids,
        relic_ids,
        action_masks,
        guard_actions,
        alternative_masks,
    )
    row_count = components.gate_logits.numel()
    device = components.gate_logits.device
    target_actions = target_actions.to(device=device, dtype=torch.long).reshape(-1)
    positive = positive.to(device=device, dtype=torch.bool).reshape(-1)
    if target_actions.shape != (row_count,) or positive.shape != (row_count,):
        raise ValueError("guard residual training label shape differs")
    rows = torch.arange(row_count, device=device)
    if bool(positive.any()) and not bool(
        components.alternative_masks[rows[positive], target_actions[positive]].all()
    ):
        raise ValueError("guard residual positive target is not an allowed alternative")
    gate_loss = F.binary_cross_entropy_with_logits(
        components.gate_logits, positive.float()
    )
    if bool(positive.any()):
        action_logits = components.action_logits[positive].masked_fill(
            ~components.alternative_masks[positive], float("-inf")
        )
        action_loss = F.cross_entropy(action_logits, target_actions[positive])
    else:
        action_loss = components.action_logits.sum() * 0.0
    total_loss = gate_loss + action_loss
    if not bool(torch.isfinite(total_loss)):
        raise ValueError("guard residual training objective must be finite")
    return total_loss, {
        "total_loss": float(total_loss.detach().item()),
        "gate_loss": float(gate_loss.detach().item()),
        "action_loss": float(action_loss.detach().item()),
        "positive_count": int(positive.sum().item()),
        "negative_count": int((~positive).sum().item()),
    }


def _validate_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"guard residual {label} SHA-256 is missing")
    normalized = value.lower()
    if len(normalized) != 64 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise ValueError(f"guard residual {label} SHA-256 is invalid")
    return normalized


def _cpu_state(state: Mapping[str, torch.Tensor]) -> dict[str, torch.Tensor]:
    return {name: tensor.detach().cpu().clone() for name, tensor in state.items()}


def build_development_artifact(
    residual: GuardAdvantageResidual,
    *,
    parent_checkpoint_sha256: str,
    corpus_sha256: Mapping[str, str],
    telemetry: Mapping[str, Any],
) -> dict[str, Any]:
    corpus = {
        name: _validate_sha256(value, f"{name} corpus")
        for name, value in sorted(corpus_sha256.items())
    }
    if set(corpus) != {"train", "evaluation"}:
        raise ValueError("guard residual corpus identities differ")
    gate_state = _cpu_state(residual.gate.state_dict())
    action_state = _cpu_state(residual.action_head.state_dict())
    return {
        "checkpoint_schema_version": ARTIFACT_SCHEMA_VERSION,
        "checkpoint_kind": ARTIFACT_KIND,
        "production_compatible": False,
        "metadata": dict(residual.metadata),
        "config": asdict(residual.config),
        "parent_checkpoint_sha256": _validate_sha256(
            parent_checkpoint_sha256, "parent checkpoint"
        ),
        "parent_state_dict_sha256": state_dict_sha256(residual.parent.state_dict()),
        "corpus_sha256": corpus,
        "gate_state_dict": gate_state,
        "gate_state_dict_sha256": state_dict_sha256(gate_state),
        "action_state_dict": action_state,
        "action_state_dict_sha256": state_dict_sha256(action_state),
        "telemetry": copy.deepcopy(dict(telemetry)),
        "authority": {
            "development_only": True,
            "gameplay": False,
            "qualification": False,
            "promotion": False,
        },
    }


def _validated_head_state(
    observed: Any,
    expected: Mapping[str, torch.Tensor],
    *,
    label: str,
) -> dict[str, torch.Tensor]:
    if not isinstance(observed, Mapping) or set(observed) != set(expected):
        raise ValueError(f"guard residual {label} state keys differ")
    normalized: dict[str, torch.Tensor] = {}
    for name, expected_tensor in expected.items():
        tensor = observed[name]
        if not isinstance(tensor, torch.Tensor):
            raise ValueError(f"guard residual {label} state contains a non-tensor")
        if tensor.shape != expected_tensor.shape or tensor.dtype != expected_tensor.dtype:
            raise ValueError(f"guard residual {label} state tensor differs")
        if not bool(torch.isfinite(tensor).all()):
            raise ValueError(f"guard residual {label} state is non-finite")
        normalized[name] = tensor.detach().cpu().clone()
    return normalized


def load_development_artifact(
    parent: nn.Module,
    metadata: Mapping[str, Any],
    artifact: Mapping[str, Any],
    *,
    expected_parent_checkpoint_sha256: str,
    expected_corpus_sha256: Mapping[str, str],
) -> GuardAdvantageResidual:
    required = {
        "checkpoint_schema_version",
        "checkpoint_kind",
        "production_compatible",
        "metadata",
        "config",
        "parent_checkpoint_sha256",
        "parent_state_dict_sha256",
        "corpus_sha256",
        "gate_state_dict",
        "gate_state_dict_sha256",
        "action_state_dict",
        "action_state_dict_sha256",
        "telemetry",
        "authority",
    }
    if not isinstance(artifact, Mapping) or set(artifact) != required:
        raise ValueError("guard residual artifact keys differ")
    if artifact["checkpoint_schema_version"] != ARTIFACT_SCHEMA_VERSION:
        raise ValueError("guard residual artifact schema differs")
    if artifact["checkpoint_kind"] != ARTIFACT_KIND:
        raise ValueError("guard residual artifact kind differs")
    if artifact["production_compatible"] is not False:
        raise ValueError("guard residual artifact must not be production-compatible")
    normalized_metadata = _normalized_metadata(metadata)
    if artifact["metadata"] != normalized_metadata:
        raise ValueError("guard residual artifact metadata differs")
    if _validate_sha256(
        artifact["parent_checkpoint_sha256"], "artifact parent checkpoint"
    ) != _validate_sha256(expected_parent_checkpoint_sha256, "expected parent checkpoint"):
        raise ValueError("guard residual parent checkpoint identity differs")
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
        raise ValueError("guard residual corpus identity differs")
    if state_dict_sha256(parent.state_dict()) != _validate_sha256(
        artifact["parent_state_dict_sha256"], "parent state"
    ):
        raise ValueError("guard residual parent state identity differs")
    if not isinstance(artifact["config"], Mapping):
        raise ValueError("guard residual artifact config is missing")
    try:
        config = GuardAdvantageResidualConfig(**dict(artifact["config"]))
    except TypeError as exc:
        raise ValueError("guard residual artifact config differs") from exc
    residual = GuardAdvantageResidual(parent, normalized_metadata, config)
    gate_state = _validated_head_state(
        artifact["gate_state_dict"], residual.gate.state_dict(), label="gate"
    )
    action_state = _validated_head_state(
        artifact["action_state_dict"],
        residual.action_head.state_dict(),
        label="action",
    )
    if state_dict_sha256(gate_state) != _validate_sha256(
        artifact["gate_state_dict_sha256"], "gate state"
    ):
        raise ValueError("guard residual gate state identity differs")
    if state_dict_sha256(action_state) != _validate_sha256(
        artifact["action_state_dict_sha256"], "action state"
    ):
        raise ValueError("guard residual action state identity differs")
    residual.gate.load_state_dict(gate_state, strict=True)
    residual.action_head.load_state_dict(action_state, strict=True)
    return residual
