"""Development-only frozen-parent latent-gated action correction."""

from __future__ import annotations

import copy
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from typing import Any, Mapping, NamedTuple

import torch
import torch.nn as nn
import torch.nn.functional as F


ARTIFACT_SCHEMA_VERSION = 1
ARTIFACT_KIND = "latent_gated_correction_development"


@dataclass(frozen=True)
class LatentGateConfig:
    hidden_dim: int = 64
    gate_threshold: float = 0.90

    def validate(self) -> None:
        if not isinstance(self.hidden_dim, int) or isinstance(self.hidden_dim, bool):
            raise ValueError("latent gate hidden_dim must be an integer")
        if self.hidden_dim <= 0:
            raise ValueError("latent gate hidden_dim must be positive")
        if not math.isfinite(self.gate_threshold) or not (
            0.0 < self.gate_threshold < 1.0
        ):
            raise ValueError("latent gate threshold must be between zero and one")


class CorrectionComponents(NamedTuple):
    parent_q: torch.Tensor
    parent_latent: torch.Tensor
    features: torch.Tensor
    gate_logits: torch.Tensor
    correction_logits: torch.Tensor
    action_masks: torch.Tensor


class ActionSelection(NamedTuple):
    actions: torch.Tensor
    parent_actions: torch.Tensor
    correction_actions: torch.Tensor
    gate_probabilities: torch.Tensor
    gate_open: torch.Tensor
    telemetry: dict[str, Any]


def state_dict_sha256(state: Mapping[str, torch.Tensor]) -> str:
    digest = hashlib.sha256()
    for name in sorted(state):
        tensor = state[name].detach().cpu().contiguous()
        encoded_name = name.encode("utf-8")
        digest.update(len(encoded_name).to_bytes(4, "big"))
        digest.update(encoded_name)
        digest.update(str(tensor.dtype).encode("ascii"))
        digest.update(json.dumps(list(tensor.shape), separators=(",", ":")).encode("ascii"))
        digest.update(tensor.numpy().tobytes())
    return digest.hexdigest()


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
    if set(metadata) != required:
        raise ValueError("latent adapter metadata keys differ")
    normalized = dict(metadata)
    if normalized["network_type"] not in {"standard", "dueling"}:
        raise ValueError("latent adapter network type is invalid")
    for name in required - {"network_type"}:
        value = normalized[name]
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ValueError(f"latent adapter metadata {name} must be positive")
        normalized[name] = int(value)
    return normalized


def _last_linear_output(module: nn.Module) -> int:
    for layer in reversed(tuple(module.modules())):
        if isinstance(layer, nn.Linear):
            return int(layer.out_features)
    raise ValueError("latent adapter parent hidden layers contain no linear output")


class LatentGatedActionAdapter(nn.Module):
    """Frozen RL v2 parent plus an abstaining gate and legal action head."""

    def __init__(
        self,
        parent: nn.Module,
        metadata: Mapping[str, Any],
        config: LatentGateConfig,
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
            raise ValueError("latent adapter parent structure is unsupported")

        self.parent_latent_dim = _last_linear_output(self.parent.hidden_layers)
        self.feature_dim = self.parent_latent_dim + 2 * self.metadata["action_dim"]
        device = next(self.parent.parameters()).device
        self.gate = nn.Sequential(
            nn.Linear(self.feature_dim, config.hidden_dim),
            nn.ReLU(),
            nn.Linear(config.hidden_dim, 1),
        ).to(device)
        self.correction = nn.Sequential(
            nn.Linear(self.feature_dim, config.hidden_dim),
            nn.ReLU(),
            nn.Linear(config.hidden_dim, self.metadata["action_dim"]),
        ).to(device)
        nn.init.zeros_(self.gate[-1].weight)
        nn.init.zeros_(self.gate[-1].bias)
        nn.init.zeros_(self.correction[-1].weight)
        nn.init.zeros_(self.correction[-1].bias)

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
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        values = [continuous, card_ids, potion_ids, relic_ids, action_masks]
        values = [value.unsqueeze(0) if value.dim() == 1 else value for value in values]
        batch_size = values[0].shape[0]
        if any(value.dim() != 2 or value.shape[0] != batch_size for value in values):
            raise ValueError("latent adapter inputs must have one equal batch dimension")
        expected_widths = (
            self.metadata["continuous_dim"],
            self.metadata["card_slots"],
            self.metadata["potion_slots"],
            self.metadata["relic_slots"],
            self.metadata["action_dim"],
        )
        if any(value.shape[1] != width for value, width in zip(values, expected_widths)):
            raise ValueError("latent adapter input width differs")
        continuous, card_ids, potion_ids, relic_ids, action_masks = values
        if not bool(torch.isfinite(continuous).all()):
            raise ValueError("latent adapter continuous inputs must be finite")
        for name, ids, embedding in (
            ("card", card_ids, self.parent.card_embedding),
            ("potion", potion_ids, self.parent.potion_embedding),
            ("relic", relic_ids, self.parent.relic_embedding),
        ):
            ids = ids.long()
            if bool((ids < 0).any()) or bool((ids >= embedding.num_embeddings).any()):
                raise ValueError(f"latent adapter {name} id is outside the vocabulary")
        action_masks = action_masks.bool()
        if not bool(action_masks.any(dim=1).all()):
            raise ValueError("latent adapter requires at least one legal action")
        return (
            continuous.float(),
            card_ids.long(),
            potion_ids.long(),
            relic_ids.long(),
            action_masks,
        )

    def correction_components(
        self,
        continuous: torch.Tensor,
        card_ids: torch.Tensor,
        potion_ids: torch.Tensor,
        relic_ids: torch.Tensor,
        action_masks: torch.Tensor,
    ) -> CorrectionComponents:
        continuous, card_ids, potion_ids, relic_ids, action_masks = (
            self._validated_inputs(
                continuous, card_ids, potion_ids, relic_ids, action_masks
            )
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
            parent_q = self.parent(
                continuous=continuous,
                card_ids=card_ids,
                potion_ids=potion_ids,
                relic_ids=relic_ids,
                action_mask=None,
            )
        if parent_latent.shape != (continuous.shape[0], self.parent_latent_dim):
            raise ValueError("latent adapter parent latent shape differs")
        if parent_q.shape != (continuous.shape[0], self.metadata["action_dim"]):
            raise ValueError("latent adapter parent Q shape differs")
        if not bool(torch.isfinite(parent_latent).all()) or not bool(
            torch.isfinite(parent_q).all()
        ):
            raise ValueError("latent adapter parent features must be finite")
        features = torch.cat((parent_latent, parent_q, action_masks.float()), dim=1)
        gate_logits = self.gate(features).squeeze(1)
        correction_logits = self.correction(features)
        if not bool(torch.isfinite(gate_logits).all()) or not bool(
            torch.isfinite(correction_logits).all()
        ):
            raise ValueError("latent adapter correction outputs must be finite")
        return CorrectionComponents(
            parent_q=parent_q,
            parent_latent=parent_latent,
            features=features,
            gate_logits=gate_logits,
            correction_logits=correction_logits,
            action_masks=action_masks,
        )

    def select_actions(
        self,
        continuous: torch.Tensor,
        card_ids: torch.Tensor,
        potion_ids: torch.Tensor,
        relic_ids: torch.Tensor,
        action_masks: torch.Tensor,
    ) -> ActionSelection:
        components = self.correction_components(
            continuous, card_ids, potion_ids, relic_ids, action_masks
        )
        parent_actions = components.parent_q.masked_fill(
            ~components.action_masks, float("-inf")
        ).argmax(dim=1)
        correction_actions = components.correction_logits.masked_fill(
            ~components.action_masks, float("-inf")
        ).argmax(dim=1)
        gate_probabilities = torch.sigmoid(components.gate_logits)
        gate_open = gate_probabilities.ge(self.config.gate_threshold)
        actions = torch.where(gate_open, correction_actions, parent_actions)
        if not bool(
            components.action_masks[
                torch.arange(actions.numel(), device=actions.device), actions
            ].all()
        ):
            raise RuntimeError("latent adapter selected an illegal action")
        telemetry = {
            "row_count": int(actions.numel()),
            "gate_open_count": int(gate_open.sum().item()),
            "parent_action_preserved_count": int(
                actions.eq(parent_actions).sum().item()
            ),
            "action_disagreement_count": int(
                actions.ne(parent_actions).sum().item()
            ),
            "gate_threshold": float(self.config.gate_threshold),
        }
        return ActionSelection(
            actions=actions,
            parent_actions=parent_actions,
            correction_actions=correction_actions,
            gate_probabilities=gate_probabilities,
            gate_open=gate_open,
            telemetry=telemetry,
        )


def adapter_training_loss(
    adapter: LatentGatedActionAdapter,
    continuous: torch.Tensor,
    card_ids: torch.Tensor,
    potion_ids: torch.Tensor,
    relic_ids: torch.Tensor,
    action_masks: torch.Tensor,
    *,
    executed_actions: torch.Tensor,
    changed: torch.Tensor,
) -> tuple[torch.Tensor, dict[str, Any]]:
    components = adapter.correction_components(
        continuous, card_ids, potion_ids, relic_ids, action_masks
    )
    row_count = components.gate_logits.numel()
    device = components.gate_logits.device
    executed_actions = executed_actions.to(device=device, dtype=torch.long).reshape(-1)
    changed = changed.to(device=device, dtype=torch.bool).reshape(-1)
    if executed_actions.shape != (row_count,) or changed.shape != (row_count,):
        raise ValueError("latent adapter training label shape differs")
    if not bool(changed.any()) or not bool((~changed).any()):
        raise ValueError("latent adapter training requires direct and changed rows")
    rows = torch.arange(row_count, device=executed_actions.device)
    if not bool(components.action_masks[rows, executed_actions].all()):
        raise ValueError("latent adapter training contains an illegal executed action")
    gate_loss = F.binary_cross_entropy_with_logits(
        components.gate_logits, changed.float()
    )
    changed_logits = components.correction_logits[changed].masked_fill(
        ~components.action_masks[changed], float("-inf")
    )
    action_loss = F.cross_entropy(changed_logits, executed_actions[changed])
    total_loss = gate_loss + action_loss
    if not bool(torch.isfinite(total_loss)):
        raise ValueError("latent adapter training objective must be finite")
    return total_loss, {
        "total_loss": float(total_loss.detach().item()),
        "gate_loss": float(gate_loss.detach().item()),
        "action_loss": float(action_loss.detach().item()),
        "direct_count": int((~changed).sum().item()),
        "changed_count": int(changed.sum().item()),
    }


def _validate_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"latent adapter {label} SHA-256 is missing")
    normalized = value.lower()
    if len(normalized) != 64 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise ValueError(f"latent adapter {label} SHA-256 is invalid")
    return normalized


def _cpu_state(state: Mapping[str, torch.Tensor]) -> dict[str, torch.Tensor]:
    return {
        name: tensor.detach().cpu().clone()
        for name, tensor in state.items()
    }


def build_development_artifact(
    adapter: LatentGatedActionAdapter,
    *,
    parent_checkpoint_sha256: str,
    telemetry: Mapping[str, Any],
) -> dict[str, Any]:
    checkpoint_sha256 = _validate_sha256(
        parent_checkpoint_sha256, "parent checkpoint"
    )
    gate_state = _cpu_state(adapter.gate.state_dict())
    correction_state = _cpu_state(adapter.correction.state_dict())
    return {
        "checkpoint_schema_version": ARTIFACT_SCHEMA_VERSION,
        "checkpoint_kind": ARTIFACT_KIND,
        "production_compatible": False,
        "metadata": dict(adapter.metadata),
        "config": asdict(adapter.config),
        "parent_checkpoint_sha256": checkpoint_sha256,
        "parent_state_dict_sha256": state_dict_sha256(adapter.parent.state_dict()),
        "gate_state_dict": gate_state,
        "gate_state_dict_sha256": state_dict_sha256(gate_state),
        "correction_state_dict": correction_state,
        "correction_state_dict_sha256": state_dict_sha256(correction_state),
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
        raise ValueError(f"latent adapter {label} state keys differ")
    normalized: dict[str, torch.Tensor] = {}
    for name, expected_tensor in expected.items():
        tensor = observed[name]
        if not isinstance(tensor, torch.Tensor):
            raise ValueError(f"latent adapter {label} state contains a non-tensor")
        if tensor.shape != expected_tensor.shape or tensor.dtype != expected_tensor.dtype:
            raise ValueError(f"latent adapter {label} state tensor differs")
        if not bool(torch.isfinite(tensor).all()):
            raise ValueError(f"latent adapter {label} state is non-finite")
        normalized[name] = tensor.detach().cpu().clone()
    return normalized


def load_development_artifact(
    parent: nn.Module,
    metadata: Mapping[str, Any],
    artifact: Mapping[str, Any],
    *,
    expected_parent_checkpoint_sha256: str,
) -> LatentGatedActionAdapter:
    required = {
        "checkpoint_schema_version",
        "checkpoint_kind",
        "production_compatible",
        "metadata",
        "config",
        "parent_checkpoint_sha256",
        "parent_state_dict_sha256",
        "gate_state_dict",
        "gate_state_dict_sha256",
        "correction_state_dict",
        "correction_state_dict_sha256",
        "telemetry",
        "authority",
    }
    if not isinstance(artifact, Mapping) or set(artifact) != required:
        raise ValueError("latent adapter artifact keys differ")
    if artifact["checkpoint_schema_version"] != ARTIFACT_SCHEMA_VERSION:
        raise ValueError("latent adapter artifact schema differs")
    if artifact["checkpoint_kind"] != ARTIFACT_KIND:
        raise ValueError("latent adapter artifact kind differs")
    if artifact["production_compatible"] is not False:
        raise ValueError("latent adapter artifact must not be production-compatible")
    normalized_metadata = _normalized_metadata(metadata)
    if artifact["metadata"] != normalized_metadata:
        raise ValueError("latent adapter artifact metadata differs")
    expected_checkpoint = _validate_sha256(
        expected_parent_checkpoint_sha256, "expected parent checkpoint"
    )
    artifact_checkpoint = _validate_sha256(
        artifact["parent_checkpoint_sha256"], "artifact parent checkpoint"
    )
    if artifact_checkpoint != expected_checkpoint:
        raise ValueError("latent adapter parent checkpoint identity differs")
    expected_parent_state = _validate_sha256(
        artifact["parent_state_dict_sha256"], "parent state"
    )
    if state_dict_sha256(parent.state_dict()) != expected_parent_state:
        raise ValueError("latent adapter parent state identity differs")
    if not isinstance(artifact["config"], Mapping):
        raise ValueError("latent adapter artifact config is missing")
    try:
        config = LatentGateConfig(**dict(artifact["config"]))
    except TypeError as exc:
        raise ValueError("latent adapter artifact config differs") from exc
    adapter = LatentGatedActionAdapter(parent, normalized_metadata, config)
    gate_state = _validated_head_state(
        artifact["gate_state_dict"], adapter.gate.state_dict(), label="gate"
    )
    correction_state = _validated_head_state(
        artifact["correction_state_dict"],
        adapter.correction.state_dict(),
        label="correction",
    )
    if state_dict_sha256(gate_state) != _validate_sha256(
        artifact["gate_state_dict_sha256"], "gate state"
    ):
        raise ValueError("latent adapter gate state identity differs")
    if state_dict_sha256(correction_state) != _validate_sha256(
        artifact["correction_state_dict_sha256"], "correction state"
    ):
        raise ValueError("latent adapter correction state identity differs")
    adapter.gate.load_state_dict(gate_state, strict=True)
    adapter.correction.load_state_dict(correction_state, strict=True)
    return adapter
