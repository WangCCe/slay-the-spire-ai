"""Fit one bounded combat RL successor from parity-qualified live replay."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import shutil
import sys
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np
import torch
import torch.nn.functional as F


REPO_ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_DIR = Path(__file__).resolve().parent
for import_root in (REPO_ROOT, ANALYSIS_DIR):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from combat_rl_dropout_update_ablation import _batch, _make_network  # noqa: E402
from combat_rl_inventory_embedding_successor import (  # noqa: E402
    _atomic_torch_save,
    _combat_group_split,
    _frozen_parent_targets,
    _optimizer_state_count,
    _sha256,
    _state_dict_sha256,
    _validate_training_checkpoint,
)
from spirecomm.ai.rl.v2.action_space import END_TURN_ACTION  # noqa: E402
from spirecomm.ai.rl.v2.state_encoder import StateEncoderV2  # noqa: E402
from spirecomm.ai.rl.v2.trainer import DQNTrainerV2  # noqa: E402


EXPECTED_INPUT_SHA256 = (
    "302a7350a7e216ea548025ac4cb588c1ea77872328ccef977f94feab65e03fb4"
)
EXPECTED_TRANSITION_COUNT = 2109
VALIDATION_FRACTION = 0.2
SPLIT_SEED = 2026082803
TRAINING_SEED = 2026082804
LEARNING_RATE = 1e-4
BATCH_SIZE = 128
ANCHOR_WEIGHT = 1.0
OPTIMIZER_STEPS = 256
GAMMA = 0.99
MINIMUM_DISAGREEMENT = 0.02
MAXIMUM_DISAGREEMENT = 0.15
MAXIMUM_POSITIVE_ENERGY_END_TURN_INCREASE = 2


def _validate_parity_checkpoint(
    checkpoint: dict, *, expected_transition_count: int
) -> tuple[dict, dict, dict[str, int]]:
    if int(checkpoint.get("checkpoint_schema_version", -1)) != 2:
        raise ValueError("parity checkpoint must use training schema version 2")
    if checkpoint.get("checkpoint_kind") != "training":
        raise ValueError("parity checkpoint must be a training checkpoint")
    metadata, replay = _validate_training_checkpoint(
        checkpoint, expected_transition_count=expected_transition_count
    )
    if int(replay.get("schema_version", -1)) != 2:
        raise ValueError("parity replay must use schema version 2")
    overrides = replay.get("anchor_to_executed_action")
    if not isinstance(overrides, torch.Tensor):
        raise ValueError("parity replay is missing executed-action provenance")
    if overrides.dtype != torch.bool or tuple(overrides.shape) != (
        expected_transition_count,
    ):
        raise ValueError("parity replay executed-action provenance has invalid shape")
    override_count = int(overrides.sum().item())
    direct_count = expected_transition_count - override_count
    if override_count <= 0 or direct_count <= 0:
        raise ValueError(
            "parity replay must contain both direct and executed-action override rows"
        )
    return metadata, replay, {
        "direct_count": direct_count,
        "override_count": override_count,
    }


def _subset_replay_state(
    replay: Mapping[str, object], indices: torch.Tensor, metadata: Mapping[str, object]
) -> dict:
    selected = indices.detach().cpu().long()
    count = int(selected.numel())
    if count <= 0:
        raise ValueError("training split is empty")
    tensor_names = (
        "continuous",
        "card_ids",
        "potion_ids",
        "relic_ids",
        "actions",
        "rewards",
        "next_continuous",
        "next_card_ids",
        "next_potion_ids",
        "next_relic_ids",
        "dones",
        "action_masks",
        "next_action_masks",
        "anchor_to_executed_action",
    )
    result = {
        "schema_version": 2,
        "buffer_size": count,
        "continuous_dim": int(metadata["continuous_dim"]),
        "action_dim": int(metadata["action_dim"]),
        "card_slots": int(metadata["card_slots"]),
        "potion_slots": int(metadata["potion_slots"]),
        "relic_slots": int(metadata["relic_slots"]),
        "transition_count": count,
        "source_transition_count": count,
        "truncated": False,
    }
    for name in tensor_names:
        value = replay[name]
        if not isinstance(value, torch.Tensor):
            raise ValueError(f"replay field is not a tensor: {name}")
        result[name] = value[selected].detach().cpu().clone()
    return result


def _summary(values: Sequence[float]) -> dict[str, float]:
    if not values:
        raise ValueError("cannot summarize empty values")
    return {
        "first": float(values[0]),
        "last": float(values[-1]),
        "mean": float(np.mean(values)),
        "minimum": float(np.min(values)),
        "maximum": float(np.max(values)),
    }


def _make_trainer(
    *,
    metadata: Mapping[str, object],
    parent_state: Mapping[str, torch.Tensor],
    target_state: Mapping[str, torch.Tensor],
    replay: Mapping[str, object],
    train_indices: torch.Tensor,
    learning_rate: float,
    batch_size: int,
    anchor_weight: float,
    seed: int,
    provenance_balanced_anchor: bool = False,
    top_action_margin_guard_weight: float = 0.0,
    top_action_margin_guard_cap: float = 0.1,
    direct_only_top_action_margin_guard: bool = False,
) -> DQNTrainerV2:
    random.seed(seed)
    np.random.seed(seed % (2**32))
    torch.manual_seed(seed)
    training_count = int(train_indices.numel())
    trainer = DQNTrainerV2(
        continuous_dim=int(metadata["continuous_dim"]),
        action_dim=int(metadata["action_dim"]),
        card_slots=int(metadata["card_slots"]),
        potion_slots=int(metadata["potion_slots"]),
        relic_slots=int(metadata["relic_slots"]),
        card_vocab=int(metadata["card_vocab"]),
        potion_vocab=int(metadata["potion_vocab"]),
        relic_vocab=int(metadata["relic_vocab"]),
        learning_rate=learning_rate,
        gamma=GAMMA,
        buffer_size=max(training_count, batch_size),
        batch_size=batch_size,
        learning_starts=batch_size,
        target_update_freq=training_count + 1,
        train_freq=1,
        epsilon_start=0.0,
        epsilon_end=0.0,
        device="cpu",
        network_type=str(metadata["network_type"]),
        parent_policy_anchor_weight=anchor_weight,
        parent_policy_anchor_provenance_balanced=provenance_balanced_anchor,
        parent_top_action_margin_guard_weight=top_action_margin_guard_weight,
        parent_top_action_margin_guard_cap=top_action_margin_guard_cap,
        parent_top_action_margin_guard_direct_only=(
            direct_only_top_action_margin_guard
        ),
    )
    trainer.online_network.load_state_dict(parent_state, strict=True)
    trainer.target_network.load_state_dict(target_state, strict=True)
    trainer.target_network.eval()
    trainer.set_parent_policy_anchor(parent_state)
    trainer.replay_buffer.load_state_dict(
        _subset_replay_state(replay, train_indices, metadata)
    )
    trainer.total_steps = training_count
    trainer.online_network.train()
    return trainer


def _fit_candidate(
    *,
    metadata: Mapping[str, object],
    parent_state: Mapping[str, torch.Tensor],
    target_state: Mapping[str, torch.Tensor],
    replay: Mapping[str, object],
    train_indices: torch.Tensor,
    learning_rate: float,
    batch_size: int,
    anchor_weight: float,
    optimizer_steps: int,
    seed: int,
    provenance_balanced_anchor: bool = False,
    top_action_margin_guard_weight: float = 0.0,
    top_action_margin_guard_cap: float = 0.1,
    direct_only_top_action_margin_guard: bool = False,
) -> tuple[dict[str, torch.Tensor], dict]:
    if learning_rate <= 0.0 or not math.isfinite(learning_rate):
        raise ValueError("learning rate must be finite and positive")
    if batch_size <= 1 or optimizer_steps <= 0:
        raise ValueError("batch size and optimizer steps must be positive")
    if anchor_weight <= 0.0 or not math.isfinite(anchor_weight):
        raise ValueError("anchor weight must be finite and positive")
    if int(train_indices.numel()) < batch_size:
        raise ValueError("training split is smaller than the batch size")

    trainer = _make_trainer(
        metadata=metadata,
        parent_state=parent_state,
        target_state=target_state,
        replay=replay,
        train_indices=train_indices,
        learning_rate=learning_rate,
        batch_size=batch_size,
        anchor_weight=anchor_weight,
        seed=seed,
        provenance_balanced_anchor=provenance_balanced_anchor,
        top_action_margin_guard_weight=top_action_margin_guard_weight,
        top_action_margin_guard_cap=top_action_margin_guard_cap,
        direct_only_top_action_margin_guard=(
            direct_only_top_action_margin_guard
        ),
    )
    totals: list[float] = []
    td_losses: list[float] = []
    anchor_losses: list[float] = []
    anchor_direct_losses: list[float] = []
    anchor_direct_counts: list[float] = []
    anchor_override_losses: list[float] = []
    override_counts: list[float] = []
    top_margin_losses: list[float] = []
    top_margin_eligible_counts: list[float] = []
    top_margin_violation_counts: list[float] = []
    for _ in range(optimizer_steps):
        loss = trainer.train_step()
        values = (
            loss,
            trainer.last_td_loss,
            trainer.last_parent_policy_anchor_loss,
            trainer.last_parent_policy_anchor_override_count,
        )
        if loss is None or not all(
            value is not None and math.isfinite(float(value)) for value in values
        ):
            raise RuntimeError(f"optimizer produced invalid objective values: {values}")
        totals.append(float(loss))
        td_losses.append(float(trainer.last_td_loss))
        anchor_losses.append(float(trainer.last_parent_policy_anchor_loss))
        anchor_direct_losses.append(
            float(trainer.last_parent_policy_anchor_direct_loss)
        )
        anchor_direct_counts.append(
            float(trainer.last_parent_policy_anchor_direct_count)
        )
        anchor_override_losses.append(
            float(trainer.last_parent_policy_anchor_override_loss)
        )
        override_counts.append(float(trainer.last_parent_policy_anchor_override_count))
        top_margin_losses.append(
            float(trainer.last_parent_top_action_margin_guard_loss)
        )
        top_margin_eligible_counts.append(
            float(trainer.last_parent_top_action_margin_guard_eligible_count)
        )
        top_margin_violation_counts.append(
            float(
                trainer.last_parent_top_action_margin_guard_ranking_violation_count
            )
        )

    candidate = {
        name: value.detach().cpu().clone()
        for name, value in trainer.online_network.state_dict().items()
    }
    return candidate, {
        "optimizer_update_count": len(totals),
        "total_loss": _summary(totals),
        "td_loss": _summary(td_losses),
        "parent_policy_anchor_loss": _summary(anchor_losses),
        "parent_policy_anchor_direct_loss": _summary(anchor_direct_losses),
        "parent_policy_anchor_direct_count": _summary(anchor_direct_counts),
        "parent_policy_anchor_override_loss": _summary(anchor_override_losses),
        "sampled_override_count": _summary(override_counts),
        "parent_policy_anchor_override_count": _summary(override_counts),
        "parent_top_action_margin_guard_loss": _summary(top_margin_losses),
        "parent_top_action_margin_guard_eligible_count": _summary(
            top_margin_eligible_counts
        ),
        "parent_top_action_margin_guard_ranking_violation_count": _summary(
            top_margin_violation_counts
        ),
        "all_objective_values_finite": all(
            math.isfinite(value)
            for series in (
                totals,
                td_losses,
                anchor_losses,
                anchor_direct_losses,
                anchor_direct_counts,
                anchor_override_losses,
                override_counts,
                top_margin_losses,
                top_margin_eligible_counts,
                top_margin_violation_counts,
            )
            for value in series
        ),
    }


def _provenance_action_metrics(
    *,
    parent_actions: torch.Tensor,
    candidate_actions: torch.Tensor,
    executed_actions: torch.Tensor,
    overrides: torch.Tensor,
) -> dict:
    tensors = tuple(
        value.detach().cpu().reshape(-1)
        for value in (
            parent_actions,
            candidate_actions,
            executed_actions,
            overrides,
        )
    )
    parent, candidate, executed, override = tensors
    if not parent.numel() or any(value.shape != parent.shape for value in tensors):
        raise ValueError("provenance metric tensors must have one equal nonzero shape")
    override = override.bool()
    labels = torch.where(override, executed.long(), parent.long())

    def stratum(mask: torch.Tensor) -> dict:
        count = int(mask.sum().item())
        if not count:
            return {
                "transition_count": 0,
                "parent_anchor_label_agreement": None,
                "candidate_anchor_label_agreement": None,
                "action_disagreement_share": None,
            }
        return {
            "transition_count": count,
            "parent_anchor_label_agreement": float(
                parent[mask].eq(labels[mask]).float().mean().item()
            ),
            "candidate_anchor_label_agreement": float(
                candidate[mask].eq(labels[mask]).float().mean().item()
            ),
            "action_disagreement_share": float(
                candidate[mask].ne(parent[mask]).float().mean().item()
            ),
        }

    all_rows = torch.ones_like(override, dtype=torch.bool)
    metrics = stratum(all_rows)
    metrics.update(
        {
            "anchor_labels": labels.tolist(),
            "action_disagreement_count": int(candidate.ne(parent).sum().item()),
            "direct": stratum(~override),
            "override": stratum(override),
        }
    )
    return metrics


def _evaluate_partition(
    *,
    metadata: Mapping[str, object],
    parent_state: Mapping[str, torch.Tensor],
    target_state: Mapping[str, torch.Tensor],
    candidate_state: Mapping[str, torch.Tensor],
    replay: Mapping[str, object],
    indices: torch.Tensor,
) -> dict:
    parent = _make_network(metadata, parent_state)
    target = _make_network(metadata, target_state)
    candidate = _make_network(metadata, candidate_state)
    parent.eval()
    target.eval()
    candidate.eval()
    rows = torch.arange(indices.numel())
    actions = replay["actions"][indices].long()
    with torch.no_grad():
        parent_q = parent(*_batch(replay, indices))
        candidate_q = candidate(*_batch(replay, indices))
        targets = _frozen_parent_targets(parent, target, replay, indices, GAMMA)
    parent_actions = parent_q.argmax(dim=1)
    candidate_actions = candidate_q.argmax(dim=1)
    provenance = _provenance_action_metrics(
        parent_actions=parent_actions,
        candidate_actions=candidate_actions,
        executed_actions=actions,
        overrides=replay["anchor_to_executed_action"][indices].bool(),
    )
    provenance.pop("anchor_labels")

    continuous = replay["continuous"][indices].float()
    if continuous.shape[1] <= StateEncoderV2.ENERGY_RATIO_INDEX:
        positive_energy = torch.zeros(indices.numel(), dtype=torch.bool)
    else:
        positive_energy = continuous[:, StateEncoderV2.ENERGY_RATIO_INDEX].gt(0.0)
    parent_end_turn = int(
        (positive_energy & parent_actions.eq(END_TURN_ACTION)).sum().item()
    )
    candidate_end_turn = int(
        (positive_energy & candidate_actions.eq(END_TURN_ACTION)).sum().item()
    )
    return {
        "transition_count": int(indices.numel()),
        "parent_smooth_l1": float(
            F.smooth_l1_loss(parent_q[rows, actions], targets).item()
        ),
        "candidate_smooth_l1": float(
            F.smooth_l1_loss(candidate_q[rows, actions], targets).item()
        ),
        "parent_anchor_label_agreement": provenance[
            "parent_anchor_label_agreement"
        ],
        "candidate_anchor_label_agreement": provenance[
            "candidate_anchor_label_agreement"
        ],
        "action_disagreement_count": provenance["action_disagreement_count"],
        "action_disagreement_share": provenance["action_disagreement_share"],
        "positive_energy_state_count": int(positive_energy.sum().item()),
        "parent_positive_energy_end_turn_count": parent_end_turn,
        "candidate_positive_energy_end_turn_count": candidate_end_turn,
        "positive_energy_end_turn_count_delta": candidate_end_turn - parent_end_turn,
        "strata": {
            "direct": provenance["direct"],
            "override": provenance["override"],
        },
    }


def _relative_l2(
    candidate_state: Mapping[str, torch.Tensor],
    parent_state: Mapping[str, torch.Tensor],
) -> float:
    numerator = 0.0
    denominator = 0.0
    if list(candidate_state) != list(parent_state):
        raise ValueError("candidate and parent parameters are incompatible")
    for name in parent_state:
        candidate = candidate_state[name].detach().cpu().double()
        parent = parent_state[name].detach().cpu().double()
        numerator += float(torch.sum((candidate - parent) ** 2).item())
        denominator += float(torch.sum(parent**2).item())
    return math.sqrt(numerator / max(denominator, 1e-24))


def _eligibility(
    *,
    validation: Mapping[str, object],
    training: Mapping[str, object],
    candidate_round_trip_exact: bool,
) -> dict[str, bool]:
    metric_names = (
        "parent_smooth_l1",
        "candidate_smooth_l1",
        "parent_anchor_label_agreement",
        "candidate_anchor_label_agreement",
        "action_disagreement_share",
    )
    checks = {
        "metrics_finite": all(
            math.isfinite(float(validation[name])) for name in metric_names
        ),
        "optimizer_budget_exact": int(training["optimizer_update_count"])
        == OPTIMIZER_STEPS,
        "objective_values_finite": bool(training["all_objective_values_finite"]),
        "sampled_executed_action_overrides": float(
            training["sampled_override_count"]["maximum"]
        )
        > 0.0,
        "candidate_round_trip_exact": bool(candidate_round_trip_exact),
        "validation_one_step_td_improved": float(
            validation["candidate_smooth_l1"]
        )
        < float(validation["parent_smooth_l1"]),
        "validation_anchor_label_agreement_not_reduced": float(
            validation["candidate_anchor_label_agreement"]
        )
        >= float(validation["parent_anchor_label_agreement"]),
        "action_disagreement_at_least_material_floor": float(
            validation["action_disagreement_share"]
        )
        >= MINIMUM_DISAGREEMENT,
        "action_disagreement_at_most_drift_ceiling": float(
            validation["action_disagreement_share"]
        )
        <= MAXIMUM_DISAGREEMENT,
        "positive_energy_end_turn_increase_bounded": int(
            validation["positive_energy_end_turn_count_delta"]
        )
        <= MAXIMUM_POSITIVE_ENERGY_END_TURN_INCREASE,
    }
    checks["all_conditions_passed"] = all(checks.values())
    return checks


def _indices_sha256(indices: torch.Tensor) -> str:
    return hashlib.sha256(indices.detach().cpu().numpy().tobytes()).hexdigest()


def run(args: argparse.Namespace) -> dict:
    checkpoint_path = args.training_checkpoint.resolve()
    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise ValueError(f"output directory already exists: {output_dir}")
    actual_hash = _sha256(checkpoint_path)
    if actual_hash != EXPECTED_INPUT_SHA256:
        raise ValueError(
            f"training checkpoint hash mismatch: {actual_hash} != {EXPECTED_INPUT_SHA256}"
        )
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    metadata, replay, provenance = _validate_parity_checkpoint(
        checkpoint, expected_transition_count=EXPECTED_TRANSITION_COUNT
    )
    split = _combat_group_split(
        replay["dones"][:EXPECTED_TRANSITION_COUNT],
        validation_fraction=VALIDATION_FRACTION,
        seed=SPLIT_SEED,
    )
    parent_state = checkpoint["online_network_state_dict"]
    target_state = checkpoint["target_network_state_dict"]
    candidate_state, training = _fit_candidate(
        metadata=metadata,
        parent_state=parent_state,
        target_state=target_state,
        replay=replay,
        train_indices=split.train_indices,
        learning_rate=LEARNING_RATE,
        batch_size=BATCH_SIZE,
        anchor_weight=ANCHOR_WEIGHT,
        optimizer_steps=OPTIMIZER_STEPS,
        seed=TRAINING_SEED,
    )
    train_evaluation = _evaluate_partition(
        metadata=metadata,
        parent_state=parent_state,
        target_state=target_state,
        candidate_state=candidate_state,
        replay=replay,
        indices=split.train_indices,
    )
    validation = _evaluate_partition(
        metadata=metadata,
        parent_state=parent_state,
        target_state=target_state,
        candidate_state=candidate_state,
        replay=replay,
        indices=split.validation_indices,
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
            "metadata": dict(metadata),
            "rl_space_version": metadata["rl_space_version"],
            "online_network_state_dict": candidate_state,
            "episode": 0,
            "production_compatible": True,
            "provenance": {
                "construction": "provenance_aware_full_network_successor",
                "experiment_id": args.experiment_id,
                "source_commit": args.source_commit,
                "training_checkpoint_sha256": actual_hash,
                "split_seed": SPLIT_SEED,
                "training_seed": TRAINING_SEED,
                "optimizer_steps": OPTIMIZER_STEPS,
                "parent_policy_anchor_weight": ANCHOR_WEIGHT,
            },
        }
        _atomic_torch_save(payload, candidate_path)
        loaded = torch.load(candidate_path, map_location="cpu", weights_only=True)
        round_trip_exact = _state_dict_sha256(
            loaded["online_network_state_dict"]
        ) == _state_dict_sha256(candidate_state)
        eligibility = _eligibility(
            validation=validation,
            training=training,
            candidate_round_trip_exact=round_trip_exact,
        )
        report = {
            "schema_version": 1,
            "experiment_id": args.experiment_id,
            "source_commit": args.source_commit,
            "decision": (
                "eligible_for_separate_fresh_holdout_only"
                if eligibility["all_conditions_passed"]
                else "development_candidate_not_eligible_no_same_corpus_tuning"
            ),
            "input": {
                "path": str(checkpoint_path),
                "sha256": actual_hash,
                "transition_count": EXPECTED_TRANSITION_COUNT,
                "optimizer_state_count": _optimizer_state_count(checkpoint),
                "online_equals_target": True,
                "provenance": provenance,
            },
            "recipe": {
                "device": "cpu",
                "validation_fraction": VALIDATION_FRACTION,
                "split_seed": SPLIT_SEED,
                "training_seed": TRAINING_SEED,
                "learning_rate": LEARNING_RATE,
                "batch_size": BATCH_SIZE,
                "parent_policy_anchor_weight": ANCHOR_WEIGHT,
                "optimizer_steps": OPTIMIZER_STEPS,
                "gamma": GAMMA,
                "target_network": "frozen_input_r16",
                "parent_anchor": "frozen_input_r16",
                "same_corpus_sweep": False,
            },
            "split": {
                "unit": "terminal_delimited_combat_group",
                "group_count": split.group_count,
                "train_group_count": split.train_group_count,
                "validation_group_count": split.validation_group_count,
                "train_transition_count": int(split.train_indices.numel()),
                "validation_transition_count": int(
                    split.validation_indices.numel()
                ),
                "train_indices_sha256": _indices_sha256(split.train_indices),
                "validation_indices_sha256": _indices_sha256(
                    split.validation_indices
                ),
            },
            "training": training,
            "parameter_movement": {
                "whole_model_relative_l2": _relative_l2(
                    candidate_state, parent_state
                ),
                "parent_state_dict_sha256": _state_dict_sha256(parent_state),
                "candidate_state_dict_sha256": _state_dict_sha256(candidate_state),
            },
            "train_evaluation": train_evaluation,
            "validation": validation,
            "eligibility": eligibility,
            "candidate": {
                "path": candidate_path.name,
                "sha256": _sha256(candidate_path),
                "size_bytes": candidate_path.stat().st_size,
                "round_trip_state_exact": round_trip_exact,
                "development_only": True,
                "production_compatible": True,
            },
            "authority": {
                "training": True,
                "fresh_holdout": eligibility["all_conditions_passed"],
                "gameplay": False,
                "qualification": False,
                "promotion": False,
                "production_checkpoint_writing": False,
                "policy_quality": False,
            },
            "limitations": [
                "The validation partition comes from the training cohort and is not an independent policy-quality holdout.",
                "No same-corpus recipe or threshold changes are permitted after publication.",
                "Production r16 remains authoritative unless a separate fresh holdout and later gate pass.",
            ],
            "next_step": (
                "Freeze this candidate hash and register an unused fresh zero-update holdout."
                if eligibility["all_conditions_passed"]
                else "Retain r16 and stop this recipe line without same-corpus tuning."
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
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--source-commit", required=True)
    return parser


def main() -> int:
    report = run(build_parser().parse_args())
    print(
        json.dumps(
            {
                "decision": report["decision"],
                "candidate": report["candidate"],
                "eligibility": report["eligibility"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
