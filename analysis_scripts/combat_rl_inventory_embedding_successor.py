"""Fit a development-only combat successor through inventory embeddings."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import shutil
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F


REPO_ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_DIR = Path(__file__).resolve().parent
for import_root in (REPO_ROOT, ANALYSIS_DIR):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from combat_rl_dropout_update_ablation import _batch, _make_network  # noqa: E402
from spirecomm.ai.rl.v2.action_space import END_TURN_ACTION  # noqa: E402
from spirecomm.ai.rl.v2.state_encoder import StateEncoderV2  # noqa: E402


INVENTORY_PARAMETERS = {
    "potion_embedding.weight",
    "relic_embedding.weight",
}


@dataclass(frozen=True)
class CombatGroupSplit:
    train_indices: torch.Tensor
    validation_indices: torch.Tensor
    group_count: int
    train_group_count: int
    validation_group_count: int


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _state_dict_sha256(state: dict[str, torch.Tensor]) -> str:
    digest = hashlib.sha256()
    for name, value in state.items():
        tensor = value.detach().cpu().contiguous()
        digest.update(name.encode("utf-8"))
        digest.update(str(tensor.dtype).encode("ascii"))
        digest.update(json.dumps(list(tensor.shape)).encode("ascii"))
        digest.update(tensor.numpy().tobytes())
    return digest.hexdigest()


def _atomic_torch_save(payload: dict, output: Path) -> None:
    temporary = output.with_name(f".{output.name}.tmp")
    try:
        buffer = io.BytesIO()
        torch.save(payload, buffer)
        temporary.write_bytes(buffer.getvalue())
        os.replace(temporary, output)
    finally:
        if temporary.exists():
            temporary.unlink()


def _combat_group_split(
    dones: torch.Tensor, *, validation_fraction: float, seed: int
) -> CombatGroupSplit:
    if not 0.0 < validation_fraction < 1.0:
        raise ValueError("validation fraction must be within (0, 1)")
    terminal = dones.detach().cpu().bool().reshape(-1)
    if terminal.numel() < 2:
        raise ValueError("replay must contain at least two transitions")

    groups: list[list[int]] = []
    start = 0
    for index, done in enumerate(terminal.tolist()):
        if done:
            groups.append(list(range(start, index + 1)))
            start = index + 1
    if start < terminal.numel():
        groups.append(list(range(start, terminal.numel())))
    if len(groups) < 2:
        raise ValueError("replay must contain at least two combat groups")

    validation_count = max(1, int(round(len(groups) * validation_fraction)))
    validation_count = min(validation_count, len(groups) - 1)
    order = np.random.default_rng(seed).permutation(len(groups)).tolist()
    validation_groups = set(order[:validation_count])
    train_indices = sorted(
        index
        for group_index, group in enumerate(groups)
        if group_index not in validation_groups
        for index in group
    )
    validation_indices = sorted(
        index
        for group_index, group in enumerate(groups)
        if group_index in validation_groups
        for index in group
    )
    return CombatGroupSplit(
        train_indices=torch.tensor(train_indices, dtype=torch.long),
        validation_indices=torch.tensor(validation_indices, dtype=torch.long),
        group_count=len(groups),
        train_group_count=len(groups) - validation_count,
        validation_group_count=validation_count,
    )


def _one_step_targets_from_bootstrap(
    *,
    rewards: torch.Tensor,
    dones: torch.Tensor,
    next_bootstrap: torch.Tensor,
    gamma: float,
) -> torch.Tensor:
    if not 0.0 <= gamma <= 1.0 or not math.isfinite(gamma):
        raise ValueError("gamma must be finite and within [0, 1]")
    if rewards.shape != dones.shape or rewards.shape != next_bootstrap.shape:
        raise ValueError("one-step target tensors must have identical shapes")
    rewards = rewards.float()
    dones = dones.bool()
    next_bootstrap = next_bootstrap.float()
    finite_bootstrap = torch.where(
        dones, torch.zeros_like(next_bootstrap), next_bootstrap
    )
    return rewards + (~dones).float() * gamma * finite_bootstrap


def _optimizer_state_count(checkpoint: dict) -> int:
    optimizer = checkpoint.get("optimizer_state_dict") or {}
    state = optimizer.get("state", {}) if isinstance(optimizer, dict) else {}
    return len(state)


def _validate_training_checkpoint(
    checkpoint: dict, *, expected_transition_count: int
) -> tuple[dict, dict]:
    required = {
        "metadata",
        "online_network_state_dict",
        "target_network_state_dict",
        "replay_buffer_state_dict",
    }
    missing = required - set(checkpoint)
    if missing:
        raise ValueError(f"checkpoint is missing fields: {sorted(missing)}")
    if _optimizer_state_count(checkpoint) != 0:
        raise ValueError("checkpoint optimizer state must be empty")

    metadata = checkpoint["metadata"]
    replay = checkpoint["replay_buffer_state_dict"]
    count = int(replay.get("transition_count", 0))
    if count <= 0 or count != expected_transition_count:
        raise ValueError(
            f"checkpoint transition count {count} does not match expected transition count {expected_transition_count}"
        )
    required_replay = {
        "continuous",
        "card_ids",
        "potion_ids",
        "relic_ids",
        "action_masks",
        "actions",
        "rewards",
        "dones",
        "next_continuous",
        "next_card_ids",
        "next_potion_ids",
        "next_relic_ids",
        "next_action_masks",
    }
    replay_missing = required_replay - set(replay)
    if replay_missing:
        raise ValueError(f"replay is missing tensors: {sorted(replay_missing)}")
    for name in required_replay:
        value = replay[name]
        if not isinstance(value, torch.Tensor) or value.shape[0] < count:
            raise ValueError(f"replay tensor {name} is shorter than transition count")
    for name in ("continuous", "rewards", "next_continuous"):
        if not bool(torch.isfinite(replay[name][:count]).all()):
            raise ValueError(f"replay tensor {name} contains non-finite values")

    for name, vocabulary in (
        ("card_ids", int(metadata["card_vocab"])),
        ("potion_ids", int(metadata["potion_vocab"])),
        ("relic_ids", int(metadata["relic_vocab"])),
        ("next_card_ids", int(metadata["card_vocab"])),
        ("next_potion_ids", int(metadata["potion_vocab"])),
        ("next_relic_ids", int(metadata["relic_vocab"])),
    ):
        values = replay[name][:count]
        if int(values.min()) < 0 or int(values.max()) >= vocabulary:
            raise ValueError(f"replay tensor {name} exceeds its vocabulary")
    action_dim = int(metadata["action_dim"])
    actions = replay["actions"][:count].long()
    if int(actions.min()) < 0 or int(actions.max()) >= action_dim:
        raise ValueError("replay actions exceed the action space")
    masks = replay["action_masks"][:count].bool()
    if not bool(masks.any(dim=1).all()):
        raise ValueError("replay contains a transition without a legal action")
    if not bool(masks[torch.arange(count), actions].all()):
        raise ValueError("replay contains an executed action outside its legal mask")

    online = checkpoint["online_network_state_dict"]
    target = checkpoint["target_network_state_dict"]
    if list(online) != list(target) or any(
        not torch.equal(online[name], target[name]) for name in online
    ):
        raise ValueError("checkpoint online and target states must be identical")
    _make_network(metadata, online)
    return metadata, replay


def _observed_nonzero_rows(
    replay: dict, indices: torch.Tensor, name: str
) -> list[int]:
    values = torch.unique(replay[name][indices].long()).tolist()
    return sorted(int(value) for value in values if int(value) != 0)


def _frozen_parent_targets(
    parent: torch.nn.Module,
    target: torch.nn.Module,
    replay: dict,
    indices: torch.Tensor,
    gamma: float,
) -> torch.Tensor:
    with torch.no_grad():
        next_parent_q = parent(*_batch(replay, indices, "next_"))
        next_actions = next_parent_q.argmax(dim=1)
        next_target_q = target(*_batch(replay, indices, "next_"))
        rows = torch.arange(indices.numel())
        bootstrap = next_target_q[rows, next_actions]
    return _one_step_targets_from_bootstrap(
        rewards=replay["rewards"][indices],
        dones=replay["dones"][indices],
        next_bootstrap=bootstrap,
        gamma=gamma,
    )


def _fit_inventory_embeddings(
    *,
    parent_state: dict,
    target_state: dict,
    metadata: dict,
    replay: dict,
    train_indices: torch.Tensor,
    epochs: int,
    batch_size: int,
    learning_rate: float,
    td_weight: float,
    anchor_weight: float,
    gamma: float,
    seed: int,
) -> tuple[torch.nn.Module, dict]:
    if epochs <= 0 or batch_size <= 0:
        raise ValueError("epochs and batch size must be positive")
    if learning_rate <= 0.0 or not math.isfinite(learning_rate):
        raise ValueError("learning rate must be finite and positive")
    if td_weight <= 0.0 or anchor_weight < 0.0:
        raise ValueError("loss weights are invalid")
    if train_indices.numel() == 0:
        raise ValueError("training split is empty")

    torch.manual_seed(seed)
    online = _make_network(metadata, parent_state)
    target = _make_network(metadata, target_state)
    anchor = _make_network(metadata, parent_state)
    online.eval()
    target.eval()
    anchor.eval()
    for parameter in online.parameters():
        parameter.requires_grad_(False)
    online.potion_embedding.weight.requires_grad_(True)
    online.relic_embedding.weight.requires_grad_(True)

    potion_rows = _observed_nonzero_rows(replay, train_indices, "potion_ids")
    relic_rows = _observed_nonzero_rows(replay, train_indices, "relic_ids")
    if not potion_rows and not relic_rows:
        raise ValueError("training split contains no nonzero inventory ids")
    potion_mask = torch.zeros_like(online.potion_embedding.weight)
    relic_mask = torch.zeros_like(online.relic_embedding.weight)
    potion_mask[potion_rows] = 1.0
    relic_mask[relic_rows] = 1.0
    optimizer = torch.optim.Adam(
        [online.potion_embedding.weight, online.relic_embedding.weight],
        lr=learning_rate,
    )
    parent_potion = parent_state["potion_embedding.weight"].detach().clone()
    parent_relic = parent_state["relic_embedding.weight"].detach().clone()
    rng = np.random.default_rng(seed)

    epoch_metrics = []
    for epoch in range(epochs):
        permutation = rng.permutation(train_indices.numpy())
        losses = []
        td_losses = []
        anchor_losses = []
        gradient_norms = []
        for start in range(0, len(permutation), batch_size):
            indices = torch.from_numpy(permutation[start : start + batch_size]).long()
            rows = torch.arange(indices.numel())
            actions = replay["actions"][indices].long()
            action_masks = replay["action_masks"][indices].bool()
            q_values = online(*_batch(replay, indices))
            selected_q = q_values[rows, actions]
            with torch.no_grad():
                anchor_q = anchor(*_batch(replay, indices))
                targets = _frozen_parent_targets(
                    anchor, target, replay, indices, gamma
                )
            td_loss = F.smooth_l1_loss(selected_q, targets)
            anchor_loss = F.smooth_l1_loss(
                q_values[action_masks], anchor_q[action_masks]
            )
            loss = td_weight * td_loss + anchor_weight * anchor_loss
            optimizer.zero_grad()
            loss.backward()
            online.potion_embedding.weight.grad.mul_(potion_mask)
            online.relic_embedding.weight.grad.mul_(relic_mask)
            gradient_norm = float(
                torch.nn.utils.clip_grad_norm_(
                    [
                        online.potion_embedding.weight,
                        online.relic_embedding.weight,
                    ],
                    max_norm=10.0,
                )
            )
            optimizer.step()
            with torch.no_grad():
                online.potion_embedding.weight[potion_mask[:, 0] == 0] = (
                    parent_potion[potion_mask[:, 0] == 0]
                )
                online.relic_embedding.weight[relic_mask[:, 0] == 0] = (
                    parent_relic[relic_mask[:, 0] == 0]
                )
            if not bool(torch.isfinite(loss)):
                raise ValueError("training produced a non-finite loss")
            losses.append(float(loss))
            td_losses.append(float(td_loss))
            anchor_losses.append(float(anchor_loss))
            gradient_norms.append(gradient_norm)
        epoch_metrics.append(
            {
                "epoch": epoch + 1,
                "mean_loss": sum(losses) / len(losses),
                "mean_td_loss": sum(td_losses) / len(td_losses),
                "mean_anchor_loss": sum(anchor_losses) / len(anchor_losses),
                "max_gradient_norm": max(gradient_norms),
            }
        )
    return online, {
        "updates": epochs * math.ceil(train_indices.numel() / batch_size),
        "epochs": epochs,
        "observed_nonzero_potion_rows": potion_rows,
        "observed_nonzero_relic_rows": relic_rows,
        "epoch_metrics": epoch_metrics,
    }


def _metrics_from_predictions(
    *,
    indices: torch.Tensor,
    replay: dict,
    parent_q: torch.Tensor,
    candidate_q: torch.Tensor,
    targets: torch.Tensor,
) -> dict:
    if indices.numel() == 0:
        return {"transition_count": 0}
    rows = torch.arange(indices.numel())
    actions = replay["actions"][indices].long()
    parent_actions = parent_q.argmax(dim=1)
    candidate_actions = candidate_q.argmax(dim=1)
    parent_selected = parent_q[rows, actions]
    candidate_selected = candidate_q[rows, actions]
    changed = candidate_actions.ne(parent_actions)
    continuous = replay["continuous"][indices].float()
    positive_energy = (
        continuous.shape[1] > StateEncoderV2.ENERGY_RATIO_INDEX
        and continuous[:, StateEncoderV2.ENERGY_RATIO_INDEX].gt(0.0)
    )
    action_dim = parent_q.shape[1]
    if isinstance(positive_energy, bool) or action_dim <= END_TURN_ACTION:
        parent_positive_end_turn = 0
        candidate_positive_end_turn = 0
        positive_energy_count = 0
    else:
        parent_positive_end_turn = int(
            (positive_energy & parent_actions.eq(END_TURN_ACTION)).sum()
        )
        candidate_positive_end_turn = int(
            (positive_energy & candidate_actions.eq(END_TURN_ACTION)).sum()
        )
        positive_energy_count = int(positive_energy.sum())
    transitions = Counter(
        f"{int(left)}->{int(right)}"
        for left, right in zip(
            parent_actions[changed].tolist(), candidate_actions[changed].tolist()
        )
    )
    return {
        "transition_count": int(indices.numel()),
        "parent_smooth_l1": float(F.smooth_l1_loss(parent_selected, targets)),
        "candidate_smooth_l1": float(
            F.smooth_l1_loss(candidate_selected, targets)
        ),
        "parent_executed_action_agreement": float(
            parent_actions.eq(actions).float().mean()
        ),
        "candidate_executed_action_agreement": float(
            candidate_actions.eq(actions).float().mean()
        ),
        "parent_action_agreement": float(
            candidate_actions.eq(parent_actions).float().mean()
        ),
        "action_disagreement_count": int(changed.sum()),
        "action_disagreement_share": float(changed.float().mean()),
        "positive_energy_state_count": positive_energy_count,
        "parent_positive_energy_end_turn_count": parent_positive_end_turn,
        "candidate_positive_energy_end_turn_count": candidate_positive_end_turn,
        "positive_energy_end_turn_count_delta": (
            candidate_positive_end_turn - parent_positive_end_turn
        ),
        "action_transitions": dict(sorted(transitions.items())),
        "changed_source_indices": indices[changed].tolist(),
    }


def _evaluate(
    *,
    parent: torch.nn.Module,
    target: torch.nn.Module,
    candidate: torch.nn.Module,
    replay: dict,
    indices: torch.Tensor,
    gamma: float,
) -> dict:
    parent.eval()
    target.eval()
    candidate.eval()
    with torch.no_grad():
        parent_q = parent(*_batch(replay, indices))
        candidate_q = candidate(*_batch(replay, indices))
        targets = _frozen_parent_targets(parent, target, replay, indices, gamma)

    potion_present = replay["potion_ids"][indices].ne(0).any(dim=1)
    relic_count = replay["relic_ids"][indices].ne(0).sum(dim=1)
    masks = {
        "all": torch.ones(indices.numel(), dtype=torch.bool),
        "potion_present": potion_present,
        "potion_absent": ~potion_present,
        "single_relic": relic_count.eq(1),
        "multiple_relics": relic_count.gt(1),
    }
    result = {}
    for label, mask in masks.items():
        selected = torch.where(mask)[0]
        result[label] = _metrics_from_predictions(
            indices=indices[selected],
            replay=replay,
            parent_q=parent_q[selected],
            candidate_q=candidate_q[selected],
            targets=targets[selected],
        )
    return result


def _relative_l2(current: torch.Tensor, reference: torch.Tensor) -> float:
    numerator = float(torch.sum((current.double() - reference.double()) ** 2))
    denominator = float(torch.sum(reference.double() ** 2))
    return math.sqrt(numerator / max(denominator, 1e-24))


def _parameter_isolation(
    candidate_state: dict,
    parent_state: dict,
    *,
    observed_potion_rows: list[int],
    observed_relic_rows: list[int],
) -> dict:
    non_inventory_exact = all(
        torch.equal(candidate_state[name], parent_state[name])
        for name in parent_state
        if name not in INVENTORY_PARAMETERS
    )
    rows = {}
    outside_exact = True
    zero_rows_exact = True
    for kind, parameter_name, observed in (
        ("potion", "potion_embedding.weight", observed_potion_rows),
        ("relic", "relic_embedding.weight", observed_relic_rows),
    ):
        current = candidate_state[parameter_name]
        parent = parent_state[parameter_name]
        changed = [
            index
            for index in range(current.shape[0])
            if not torch.equal(current[index], parent[index])
        ]
        observed_set = set(observed)
        outside_exact &= all(index in observed_set for index in changed)
        zero_rows_exact &= torch.equal(current[0], parent[0])
        rows[kind] = {
            "observed_nonzero_rows": observed,
            "changed_rows": changed,
            "changed_row_count": len(changed),
            "relative_l2": _relative_l2(current, parent),
        }

    all_exact = non_inventory_exact and outside_exact and zero_rows_exact
    return {
        "all_required_tensors_isolated": all_exact,
        "non_inventory_parameters_exact": non_inventory_exact,
        "zero_inventory_rows_exact": zero_rows_exact,
        "unobserved_inventory_rows_exact": outside_exact,
        "rows": rows,
    }


def _eligibility(
    *,
    validation: dict,
    isolation: dict,
    minimum_disagreement: float,
    maximum_disagreement: float,
    maximum_end_turn_increase: int,
) -> dict:
    metrics = validation["all"]
    finite = all(
        math.isfinite(float(metrics[name]))
        for name in (
            "parent_smooth_l1",
            "candidate_smooth_l1",
            "action_disagreement_share",
        )
    )
    checks = {
        "metrics_finite": finite,
        "validation_one_step_loss_improved": (
            metrics["candidate_smooth_l1"] < metrics["parent_smooth_l1"]
        ),
        "action_disagreement_at_least_material_floor": (
            metrics["action_disagreement_share"] >= minimum_disagreement
        ),
        "action_disagreement_at_most_drift_ceiling": (
            metrics["action_disagreement_share"] <= maximum_disagreement
        ),
        "positive_energy_end_turn_increase_bounded": (
            metrics["positive_energy_end_turn_count_delta"]
            <= maximum_end_turn_increase
        ),
        "parameter_isolation_exact": isolation[
            "all_required_tensors_isolated"
        ],
        "both_inventory_embeddings_changed": (
            isolation["rows"]["potion"]["changed_row_count"] > 0
            and isolation["rows"]["relic"]["changed_row_count"] > 0
        ),
    }
    checks["all_conditions_passed"] = all(checks.values())
    return checks


def run(args: argparse.Namespace) -> dict:
    checkpoint_path = args.training_checkpoint.resolve()
    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise ValueError(f"output directory already exists: {output_dir}")
    actual_hash = _sha256(checkpoint_path)
    if actual_hash != args.expected_sha256:
        raise ValueError(
            f"training checkpoint hash mismatch: {actual_hash} != {args.expected_sha256}"
        )
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    metadata, replay = _validate_training_checkpoint(
        checkpoint, expected_transition_count=args.expected_transition_count
    )
    count = int(replay["transition_count"])
    split = _combat_group_split(
        replay["dones"][:count],
        validation_fraction=args.validation_fraction,
        seed=args.split_seed,
    )
    parent_state = checkpoint["online_network_state_dict"]
    target_state = checkpoint["target_network_state_dict"]
    parent = _make_network(metadata, parent_state)
    target = _make_network(metadata, target_state)
    candidate, training = _fit_inventory_embeddings(
        parent_state=parent_state,
        target_state=target_state,
        metadata=metadata,
        replay=replay,
        train_indices=split.train_indices,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        td_weight=args.td_weight,
        anchor_weight=args.anchor_weight,
        gamma=args.gamma,
        seed=args.training_seed,
    )
    candidate_state = {
        name: value.detach().cpu().clone()
        for name, value in candidate.state_dict().items()
    }
    isolation = _parameter_isolation(
        candidate_state,
        parent_state,
        observed_potion_rows=training["observed_nonzero_potion_rows"],
        observed_relic_rows=training["observed_nonzero_relic_rows"],
    )
    validation = _evaluate(
        parent=parent,
        target=target,
        candidate=candidate,
        replay=replay,
        indices=split.validation_indices,
        gamma=args.gamma,
    )
    train_evaluation = _evaluate(
        parent=parent,
        target=target,
        candidate=candidate,
        replay=replay,
        indices=split.train_indices,
        gamma=args.gamma,
    )
    eligibility = _eligibility(
        validation=validation,
        isolation=isolation,
        minimum_disagreement=args.minimum_disagreement,
        maximum_disagreement=args.maximum_disagreement,
        maximum_end_turn_increase=args.maximum_end_turn_increase,
    )

    staging = output_dir.with_name(f".{output_dir.name}.{os.getpid()}.staging")
    if staging.exists():
        raise ValueError(f"staging directory already exists: {staging}")
    staging.mkdir(parents=True)
    try:
        candidate_path = staging / "development_candidate.pth"
        payload = {
            "checkpoint_schema_version": 2,
            "checkpoint_kind": "weights",
            "metadata": metadata,
            "rl_space_version": metadata["rl_space_version"],
            "online_network_state_dict": candidate_state,
            "episode": 0,
            "provenance": {
                "construction": "inventory_embedding_only_one_step_successor",
                "experiment_id": args.experiment_id,
                "source_commit": args.source_commit,
                "training_checkpoint_sha256": actual_hash,
                "split_seed": args.split_seed,
                "training_seed": args.training_seed,
                "validation_fraction": args.validation_fraction,
                "epochs": args.epochs,
                "batch_size": args.batch_size,
                "learning_rate": args.learning_rate,
                "td_weight": args.td_weight,
                "anchor_weight": args.anchor_weight,
                "gamma": args.gamma,
            },
        }
        _atomic_torch_save(payload, candidate_path)
        loaded = torch.load(candidate_path, map_location="cpu", weights_only=True)
        if _state_dict_sha256(loaded["online_network_state_dict"]) != (
            _state_dict_sha256(candidate_state)
        ):
            raise ValueError("candidate checkpoint failed state round-trip")
        candidate_hash = _sha256(candidate_path)
        report = {
            "schema_version": 1,
            "experiment_id": args.experiment_id,
            "source_commit": args.source_commit,
            "decision": (
                "eligible_for_separate_fresh_holdout_only"
                if eligibility["all_conditions_passed"]
                else "development_candidate_not_eligible_no_same_corpus_tuning"
            ),
            "inputs": {
                "training_checkpoint": {
                    "path": str(checkpoint_path),
                    "sha256": actual_hash,
                    "transition_count": count,
                    "optimizer_state_count": _optimizer_state_count(checkpoint),
                    "online_equals_target": True,
                }
            },
            "design": {
                "target": "stored_one_step_frozen_parent_double_dqn",
                "optimizer": "adam",
                "trainable_parameters": sorted(INVENTORY_PARAMETERS),
                "zero_and_unobserved_rows_frozen": True,
                "split_unit": "terminal_delimited_combat_group",
                "validation_fraction": args.validation_fraction,
                "split_seed": args.split_seed,
                "training_seed": args.training_seed,
                "epochs": args.epochs,
                "batch_size": args.batch_size,
                "learning_rate": args.learning_rate,
                "td_weight": args.td_weight,
                "anchor_weight": args.anchor_weight,
                "gamma": args.gamma,
                "minimum_disagreement": args.minimum_disagreement,
                "maximum_disagreement": args.maximum_disagreement,
                "maximum_positive_energy_end_turn_increase": (
                    args.maximum_end_turn_increase
                ),
                "same_corpus_sweep": False,
            },
            "split": {
                "group_count": split.group_count,
                "train_group_count": split.train_group_count,
                "validation_group_count": split.validation_group_count,
                "train_transition_count": int(split.train_indices.numel()),
                "validation_transition_count": int(
                    split.validation_indices.numel()
                ),
                "train_indices_sha256": hashlib.sha256(
                    split.train_indices.numpy().tobytes()
                ).hexdigest(),
                "validation_indices_sha256": hashlib.sha256(
                    split.validation_indices.numpy().tobytes()
                ).hexdigest(),
            },
            "training": training,
            "parameter_isolation": isolation,
            "train_evaluation": train_evaluation,
            "validation": validation,
            "eligibility": eligibility,
            "candidate": {
                "path": "development_candidate.pth",
                "sha256": candidate_hash,
                "state_dict_sha256": _state_dict_sha256(candidate_state),
                "size_bytes": candidate_path.stat().st_size,
                "production_compatible": True,
                "development_only": True,
            },
            "authority": {
                "training": True,
                "fresh_holdout": eligibility["all_conditions_passed"],
                "gameplay": False,
                "qualification": False,
                "promotion": False,
                "production_checkpoint_loading": False,
                "production_checkpoint_writing": False,
            },
            "limitations": [
                "The r2 split is development evidence, not an independent policy-quality holdout.",
                "One removed boundary transition means array adjacency is not valid for n-step or full-return reconstruction.",
                "No same-corpus tuning or threshold change is authorized after publication.",
            ],
            "next_step": (
                "Freeze this hash and collect a separate fresh zero-update r16 holdout before any gameplay gate."
                if eligibility["all_conditions_passed"]
                else "Retain r16 and diagnose this fixed result without tuning on r2."
            ),
        }
        (staging / "report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.replace(staging, output_dir)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training-checkpoint", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--expected-transition-count", type=int, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--validation-fraction", type=float, default=0.2)
    parser.add_argument("--split-seed", type=int, default=2026082801)
    parser.add_argument("--training-seed", type=int, default=2026082802)
    parser.add_argument("--epochs", type=int, default=16)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--td-weight", type=float, default=0.2)
    parser.add_argument("--anchor-weight", type=float, default=1.0)
    parser.add_argument("--gamma", type=float, default=0.99)
    parser.add_argument("--minimum-disagreement", type=float, default=0.005)
    parser.add_argument("--maximum-disagreement", type=float, default=0.05)
    parser.add_argument("--maximum-end-turn-increase", type=int, default=2)
    return parser


def main() -> int:
    result = run(build_parser().parse_args())
    print(
        json.dumps(
            {
                "decision": result["decision"],
                "candidate": result["candidate"],
                "eligibility": result["eligibility"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
