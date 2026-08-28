"""Experiment-only frozen-parent combat RL correction head."""

from __future__ import annotations

import argparse
import copy
from dataclasses import asdict, dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
from typing import Any, Mapping

import torch
import torch.nn as nn
import torch.nn.functional as F


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from spirecomm.ai.rl.v2.network import create_dqn_v2  # noqa: E402


CLOSED_R1_CHECKPOINT_SHA256 = (
    "9f4570eaa5c9fd5df770734a5cc038dd6ba87da7983838fed243f05ef19b1860"
)
ARTIFACT_SCHEMA_VERSION = 1
ARTIFACT_KIND = "combat_rl_abstaining_residual_mechanism"
SMOKE_SEED = 2026082811
SMOKE_UPDATES = 160
SMOKE_LEARNING_RATE = 0.03


@dataclass(frozen=True)
class AdapterConfig:
    hidden_dim: int = 32
    gate_threshold: float = 0.90
    residual_scale: float = 4.0

    def validate(self) -> None:
        if self.hidden_dim <= 0:
            raise ValueError("adapter hidden_dim must be positive")
        if not math.isfinite(self.gate_threshold) or not (
            0.0 < self.gate_threshold < 1.0
        ):
            raise ValueError("adapter gate_threshold must be between zero and one")
        if not math.isfinite(self.residual_scale) or self.residual_scale <= 0.0:
            raise ValueError("adapter residual_scale must be finite and positive")


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


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        indent=2,
        sort_keys=True,
    ).encode("ascii") + b"\n"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
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
        raise ValueError("adapter metadata keys differ")
    normalized = dict(metadata)
    if normalized["network_type"] not in {"standard", "dueling"}:
        raise ValueError("adapter network_type is invalid")
    for name in required - {"network_type"}:
        normalized[name] = int(normalized[name])
        if normalized[name] <= 0:
            raise ValueError(f"adapter metadata {name} must be positive")
    return normalized


class AbstainingResidualQAdapter(nn.Module):
    """Frozen DQN plus a gated, bounded correction head."""

    def __init__(
        self,
        parent: nn.Module,
        metadata: Mapping[str, Any],
        config: AdapterConfig,
    ) -> None:
        super().__init__()
        config.validate()
        self.metadata = _validate_metadata(metadata)
        self.config = config
        self.parent = copy.deepcopy(parent)
        self.parent.eval()
        for parameter in self.parent.parameters():
            parameter.requires_grad_(False)

        input_dim = (
            self.metadata["continuous_dim"] + 2 * self.metadata["action_dim"]
        )
        self.correction = nn.Sequential(
            nn.Linear(input_dim, config.hidden_dim),
            nn.ReLU(),
            nn.Linear(config.hidden_dim, self.metadata["action_dim"] + 1),
        ).to(next(self.parent.parameters()).device)
        projection = self.correction[-1]
        nn.init.zeros_(projection.weight)
        nn.init.zeros_(projection.bias)
        self.last_forward_telemetry: dict[str, Any] = {}

    def train(self, mode: bool = True):
        super().train(mode)
        self.parent.eval()
        return self

    def _validate_inputs(
        self,
        continuous: torch.Tensor,
        action_mask: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        if continuous.dim() == 1:
            continuous = continuous.unsqueeze(0)
        if action_mask.dim() == 1:
            action_mask = action_mask.unsqueeze(0)
        if continuous.shape[0] != action_mask.shape[0]:
            raise ValueError("adapter batch dimensions differ")
        if continuous.shape[1] != self.metadata["continuous_dim"]:
            raise ValueError("adapter continuous dimension differs")
        if action_mask.shape[1] != self.metadata["action_dim"]:
            raise ValueError("adapter action mask dimension differs")
        action_mask = action_mask.bool()
        if not bool(action_mask.any(dim=1).all()):
            raise ValueError("adapter requires at least one legal action per row")
        return continuous.float(), action_mask

    def correction_components(
        self,
        continuous: torch.Tensor,
        card_ids: torch.Tensor,
        potion_ids: torch.Tensor,
        relic_ids: torch.Tensor,
        action_mask: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        continuous, action_mask = self._validate_inputs(continuous, action_mask)
        self.parent.eval()
        with torch.no_grad():
            parent_q = self.parent(
                continuous=continuous,
                card_ids=card_ids,
                potion_ids=potion_ids,
                relic_ids=relic_ids,
                action_mask=None,
            )
        if not bool(torch.isfinite(parent_q).all()):
            raise ValueError("adapter parent Q values must be finite before masking")
        features = torch.cat(
            (continuous, parent_q.detach(), action_mask.float()), dim=1
        )
        raw = self.correction(features)
        if not bool(torch.isfinite(raw).all()):
            raise ValueError("adapter correction output must be finite")
        gate_logits = raw[:, 0]
        residuals = self.config.residual_scale * torch.tanh(raw[:, 1:])
        return parent_q, gate_logits, residuals, action_mask

    def forward(
        self,
        continuous: torch.Tensor,
        card_ids: torch.Tensor,
        potion_ids: torch.Tensor,
        relic_ids: torch.Tensor,
        action_mask: torch.Tensor,
    ) -> torch.Tensor:
        parent_q, gate_logits, residuals, action_mask = self.correction_components(
            continuous,
            card_ids,
            potion_ids,
            relic_ids,
            action_mask,
        )
        gate_probabilities = torch.sigmoid(gate_logits)
        gate_open = gate_probabilities.ge(self.config.gate_threshold)
        corrected_q = torch.where(
            gate_open.unsqueeze(1), parent_q + residuals, parent_q
        )
        corrected_q = corrected_q.masked_fill(~action_mask, float("-inf"))
        self.last_forward_telemetry = {
            "gate_open_count": int(gate_open.sum().item()),
            "row_count": int(gate_open.numel()),
            "maximum_abs_residual": float(residuals.abs().max().item()),
        }
        return corrected_q

    def get_best_action(
        self,
        continuous: torch.Tensor,
        card_ids: torch.Tensor,
        potion_ids: torch.Tensor,
        relic_ids: torch.Tensor,
        action_mask: torch.Tensor,
    ) -> torch.Tensor:
        with torch.no_grad():
            return self.forward(
                continuous,
                card_ids,
                potion_ids,
                relic_ids,
                action_mask,
            ).argmax(dim=1)


def residual_named_parameters(
    adapter: AbstainingResidualQAdapter,
) -> tuple[tuple[str, nn.Parameter], ...]:
    rows = tuple(adapter.correction.named_parameters())
    if not rows or any(not parameter.requires_grad for _, parameter in rows):
        raise ValueError("adapter correction parameters are not trainable")
    if any(parameter.requires_grad for parameter in adapter.parent.parameters()):
        raise ValueError("adapter parent parameters must remain frozen")
    return rows


def build_residual_optimizer(
    adapter: AbstainingResidualQAdapter,
    *,
    learning_rate: float,
) -> torch.optim.Adam:
    if not math.isfinite(learning_rate) or learning_rate <= 0.0:
        raise ValueError("residual learning rate must be finite and positive")
    return torch.optim.Adam(
        tuple(parameter for _, parameter in residual_named_parameters(adapter)),
        lr=learning_rate,
    )


def residual_training_loss(
    adapter: AbstainingResidualQAdapter,
    *,
    continuous: torch.Tensor,
    card_ids: torch.Tensor,
    potion_ids: torch.Tensor,
    relic_ids: torch.Tensor,
    action_masks: torch.Tensor,
    executed_actions: torch.Tensor,
    changed: torch.Tensor,
    smdp_targets: torch.Tensor,
) -> tuple[torch.Tensor, dict[str, Any]]:
    parent_q, gate_logits, residuals, action_masks = adapter.correction_components(
        continuous,
        card_ids,
        potion_ids,
        relic_ids,
        action_masks,
    )
    row_count = parent_q.shape[0]
    executed_actions = executed_actions.long()
    changed = changed.bool()
    smdp_targets = smdp_targets.float()
    if tuple(executed_actions.shape) != (row_count,):
        raise ValueError("executed action shape differs")
    if tuple(changed.shape) != (row_count,) or not bool(changed.any()) or not bool(
        (~changed).any()
    ):
        raise ValueError("residual loss requires direct and changed rows")
    if tuple(smdp_targets.shape) != (row_count,):
        raise ValueError("SMDP target shape differs")
    if not bool(
        action_masks.gather(1, executed_actions.unsqueeze(1)).squeeze(1).all()
    ):
        raise ValueError("executed residual action is illegal")

    gate_loss = F.binary_cross_entropy_with_logits(gate_logits, changed.float())
    candidate_q = (parent_q + residuals).masked_fill(
        ~action_masks, float("-inf")
    )
    changed_q = candidate_q[changed]
    changed_actions = executed_actions[changed]
    action_loss = F.cross_entropy(changed_q, changed_actions)
    selected_q = changed_q[
        torch.arange(changed_actions.numel(), device=changed_actions.device),
        changed_actions,
    ]
    td_loss = F.smooth_l1_loss(selected_q, smdp_targets[changed])
    total = gate_loss + action_loss + 0.25 * td_loss
    if not bool(torch.isfinite(total)):
        raise ValueError("residual objective must be finite")
    return total, {
        "total_loss": float(total.detach().item()),
        "gate_loss": float(gate_loss.detach().item()),
        "action_loss": float(action_loss.detach().item()),
        "td_loss": float(td_loss.detach().item()),
        "direct_count": int((~changed).sum().item()),
        "changed_count": int(changed.sum().item()),
    }


def build_adapter_artifact(
    adapter: AbstainingResidualQAdapter,
    optimizer: torch.optim.Optimizer,
    *,
    parent_checkpoint_sha256: str,
    seed: int,
    update_count: int,
    telemetry: Mapping[str, Any],
) -> dict[str, Any]:
    if len(parent_checkpoint_sha256) != 64 or any(
        character not in "0123456789abcdef" for character in parent_checkpoint_sha256
    ):
        raise ValueError("parent checkpoint SHA-256 is invalid")
    residual_named_parameters(adapter)
    correction_state = {
        name: value.detach().cpu().clone()
        for name, value in adapter.correction.state_dict().items()
    }
    return {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "checkpoint_kind": ARTIFACT_KIND,
        "production_compatible": False,
        "metadata": dict(adapter.metadata),
        "adapter_config": asdict(adapter.config),
        "parent_checkpoint_sha256": parent_checkpoint_sha256,
        "parent_state_dict_sha256": state_dict_sha256(adapter.parent.state_dict()),
        "correction_state_dict": correction_state,
        "correction_state_dict_sha256": state_dict_sha256(correction_state),
        "optimizer_state_dict": copy.deepcopy(optimizer.state_dict()),
        "optimizer_learning_rate": float(optimizer.param_groups[0]["lr"]),
        "seed": int(seed),
        "update_count": int(update_count),
        "telemetry": copy.deepcopy(dict(telemetry)),
    }


def load_adapter_artifact(
    parent: nn.Module,
    metadata: Mapping[str, Any],
    artifact: Mapping[str, Any],
    *,
    expected_parent_checkpoint_sha256: str,
) -> tuple[AbstainingResidualQAdapter, torch.optim.Adam]:
    if artifact.get("schema_version") != ARTIFACT_SCHEMA_VERSION:
        raise ValueError("residual artifact schema differs")
    if artifact.get("checkpoint_kind") != ARTIFACT_KIND:
        raise ValueError("residual artifact kind differs")
    if artifact.get("production_compatible") is not False:
        raise ValueError("residual artifact must remain non-production-compatible")
    if artifact.get("parent_checkpoint_sha256") != expected_parent_checkpoint_sha256:
        raise ValueError("residual artifact parent checkpoint differs")
    normalized_metadata = _validate_metadata(metadata)
    if artifact.get("metadata") != normalized_metadata:
        raise ValueError("residual artifact metadata differs")
    parent_hash = state_dict_sha256(parent.state_dict())
    if artifact.get("parent_state_dict_sha256") != parent_hash:
        raise ValueError("residual artifact parent parameter identity differs")
    config_payload = artifact.get("adapter_config")
    if not isinstance(config_payload, Mapping):
        raise ValueError("residual artifact adapter config is missing")
    config = AdapterConfig(**dict(config_payload))
    adapter = AbstainingResidualQAdapter(parent, normalized_metadata, config)
    correction_state = artifact.get("correction_state_dict")
    if not isinstance(correction_state, Mapping):
        raise ValueError("residual artifact correction state is missing")
    if artifact.get("correction_state_dict_sha256") != state_dict_sha256(
        correction_state
    ):
        raise ValueError("residual artifact correction hash differs")
    adapter.correction.load_state_dict(correction_state, strict=True)
    optimizer = build_residual_optimizer(
        adapter, learning_rate=float(artifact.get("optimizer_learning_rate", 0.0))
    )
    optimizer_state = artifact.get("optimizer_state_dict")
    if not isinstance(optimizer_state, Mapping):
        raise ValueError("residual artifact optimizer state is missing")
    optimizer.load_state_dict(optimizer_state)
    return adapter, optimizer


def validate_residual_training_source(checkpoint_sha256: str) -> None:
    if checkpoint_sha256 == CLOSED_R1_CHECKPOINT_SHA256:
        raise ValueError("closed R1 corpus cannot be used for residual fitting")
    if len(checkpoint_sha256) != 64 or any(
        character not in "0123456789abcdef" for character in checkpoint_sha256
    ):
        raise ValueError("residual training source SHA-256 is invalid")


def _synthetic_fixture(seed: int):
    metadata = {
        "network_type": "standard",
        "continuous_dim": 6,
        "action_dim": 4,
        "card_vocab": 8,
        "potion_vocab": 8,
        "relic_vocab": 8,
        "card_slots": 1,
        "potion_slots": 1,
        "relic_slots": 1,
    }
    torch.manual_seed(seed)
    parent = create_dqn_v2(device="cpu", **metadata)
    parent.eval()
    count = 64
    changed = torch.arange(count).ge(count // 2)
    generator = torch.Generator().manual_seed(seed + 1)
    continuous = torch.randn((count, 6), generator=generator) * 0.1
    continuous[:, 0] = torch.where(changed, 1.0, -1.0)
    ids = (torch.arange(count) % 7 + 1).reshape(count, 1).long()
    masks = torch.ones((count, 4), dtype=torch.bool)
    with torch.no_grad():
        parent_q = parent(continuous, ids, ids, ids, action_mask=masks)
    parent_actions = parent_q.argmax(dim=1)
    rankings = parent_q.argsort(dim=1, descending=True)
    executed = parent_actions.clone()
    executed[changed] = rankings[changed, 1]
    targets = parent_q[
        torch.arange(count), executed
    ].detach() + changed.float()
    return metadata, parent, continuous, ids, masks, changed, executed, targets


def _train_synthetic_once(seed: int):
    (
        metadata,
        parent,
        continuous,
        ids,
        masks,
        changed,
        executed,
        targets,
    ) = _synthetic_fixture(seed)
    parent_hash_before = state_dict_sha256(parent.state_dict())
    torch.manual_seed(seed + 2)
    adapter = AbstainingResidualQAdapter(parent, metadata, AdapterConfig())
    optimizer = build_residual_optimizer(adapter, learning_rate=SMOKE_LEARNING_RATE)
    final_loss: dict[str, Any] = {}
    for _ in range(SMOKE_UPDATES):
        loss, final_loss = residual_training_loss(
            adapter,
            continuous=continuous,
            card_ids=ids,
            potion_ids=ids,
            relic_ids=ids,
            action_masks=masks,
            executed_actions=executed,
            changed=changed,
            smdp_targets=targets,
        )
        optimizer.zero_grad()
        loss.backward()
        if any(parameter.grad is not None for parameter in adapter.parent.parameters()):
            raise RuntimeError("synthetic smoke produced a parent gradient")
        torch.nn.utils.clip_grad_norm_(
            tuple(parameter for _, parameter in residual_named_parameters(adapter)),
            max_norm=10.0,
        )
        optimizer.step()

    adapter.eval()
    with torch.no_grad():
        parent_q = parent(continuous, ids, ids, ids, action_mask=masks)
        candidate_q = adapter(continuous, ids, ids, ids, action_mask=masks)
        parent_actions = parent_q.argmax(dim=1)
        candidate_actions = candidate_q.argmax(dim=1)
        _, gate_logits, residuals, _ = adapter.correction_components(
            continuous, ids, ids, ids, masks
        )
        gate_probabilities = torch.sigmoid(gate_logits)
        gate_open = gate_probabilities.ge(adapter.config.gate_threshold)
    parent_hash_after = state_dict_sha256(adapter.parent.state_dict())
    report = {
        "update_count": SMOKE_UPDATES,
        "row_count": int(changed.numel()),
        "direct_count": int((~changed).sum().item()),
        "changed_count": int(changed.sum().item()),
        "gate_open_direct_count": int((gate_open & ~changed).sum().item()),
        "gate_open_changed_count": int((gate_open & changed).sum().item()),
        "direct_action_drift_count": int(
            (candidate_actions[~changed] != parent_actions[~changed]).sum().item()
        ),
        "corrected_changed_count": int(
            (
                (candidate_actions[changed] == executed[changed])
                & (candidate_actions[changed] != parent_actions[changed])
            ).sum().item()
        ),
        "maximum_abs_residual": float(residuals.abs().max().item()),
        "minimum_gate_probability": float(gate_probabilities.min().item()),
        "maximum_gate_probability": float(gate_probabilities.max().item()),
        "parent_immutable": parent_hash_before == parent_hash_after,
        "parent_state_dict_sha256": parent_hash_after,
        "correction_state_dict_sha256": state_dict_sha256(
            adapter.correction.state_dict()
        ),
        "final_loss": final_loss,
    }
    return adapter, optimizer, report


def run_synthetic_smoke(output_dir: Path | str) -> dict[str, Any]:
    output_dir = Path(output_dir).resolve()
    if output_dir.exists():
        raise FileExistsError(f"synthetic smoke output already exists: {output_dir}")
    first_adapter, first_optimizer, first = _train_synthetic_once(SMOKE_SEED)
    second_adapter, _second_optimizer, second = _train_synthetic_once(SMOKE_SEED)
    deterministic = (
        first["correction_state_dict_sha256"]
        == second["correction_state_dict_sha256"]
        and first == second
    )
    mechanism_ready = all(
        (
            deterministic,
            first["parent_immutable"],
            first["gate_open_direct_count"] == 0,
            first["gate_open_changed_count"] > 0,
            first["direct_action_drift_count"] == 0,
            first["corrected_changed_count"] > 0,
            first["maximum_abs_residual"] <= first_adapter.config.residual_scale,
        )
    )
    if not mechanism_ready:
        raise RuntimeError(f"synthetic residual mechanism failed: {first}")

    parent_checkpoint_sha256 = first["parent_state_dict_sha256"]
    artifact = build_adapter_artifact(
        first_adapter,
        first_optimizer,
        parent_checkpoint_sha256=parent_checkpoint_sha256,
        seed=SMOKE_SEED,
        update_count=SMOKE_UPDATES,
        telemetry=first,
    )
    report = {
        "schema_version": 1,
        "decision": "mechanism_ready_for_fresh_registration",
        "authority": {
            "fresh_registration": True,
            "gameplay": False,
            "model_fitting": False,
            "policy_quality": False,
            "production_loading": False,
            "promotion": False,
        },
        "closed_r1_checkpoint_sha256": CLOSED_R1_CHECKPOINT_SHA256,
        "deterministic_repeat_exact": deterministic,
        **first,
    }

    staging = output_dir.with_name(f".{output_dir.name}.staging")
    if staging.exists():
        raise FileExistsError(f"synthetic smoke staging already exists: {staging}")
    staging.mkdir(parents=True)
    try:
        artifact_path = staging / "adapter.pt"
        torch.save(artifact, artifact_path)
        report["artifact"] = {
            "path": "adapter.pt",
            "sha256": _sha256(artifact_path),
            "correction_state_dict_sha256": artifact[
                "correction_state_dict_sha256"
            ],
            "production_compatible": False,
        }
        (staging / "report.json").write_bytes(_canonical_json_bytes(report))
        (staging / "summary.md").write_text(
            "# Combat RL Abstaining Residual Mechanism Smoke\n\n"
            "The deterministic synthetic smoke passed. The frozen parent remained "
            "exact, direct rows abstained without action drift, and the correction "
            "head changed at least one changed-proposal target. This result permits "
            "only a separate fresh-cohort registration.\n",
            encoding="ascii",
        )
        os.replace(staging, output_dir)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    if state_dict_sha256(first_adapter.correction.state_dict()) != state_dict_sha256(
        second_adapter.correction.state_dict()
    ):
        raise RuntimeError("synthetic residual repeat changed after publication")
    return report


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the deterministic abstaining residual mechanism smoke."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT
        / "reports"
        / "combat_rl_abstaining_residual_head_mechanism_20260828_r1",
    )
    return parser.parse_args()


def main() -> None:
    report = run_synthetic_smoke(_parse_args().output_dir)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
