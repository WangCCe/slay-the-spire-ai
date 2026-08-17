"""Fit one outcome-constrained pairwise combat candidate and validate on unseen replay."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import torch


REPO_ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_DIR = Path(__file__).resolve().parent
for import_root in (REPO_ROOT, ANALYSIS_DIR):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from combat_rl_dropout_update_ablation import _batch, _make_network
from combat_rl_positive_energy_imitation_ablation import (
    _atomic_torch_save,
    _evaluate,
    _state_dict_equal,
    _train_variant,
)
from spirecomm.ai.rl.v2.action_space import END_TURN_ACTION
from spirecomm.ai.rl.v2.state_encoder import StateEncoderV2


PARENT_AGREEMENT_MIN = 0.95
POSITIVE_ENERGY_END_TURN_REDUCTION_MIN = 0.01
OFF_TARGET_DISAGREEMENT_MAX = 0.03


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative_l2(left: torch.nn.Module, right_state: dict) -> float:
    numerator = torch.zeros((), dtype=torch.float64)
    denominator = torch.zeros((), dtype=torch.float64)
    for name, value in left.state_dict().items():
        reference = right_state[name].detach().cpu().double()
        current = value.detach().cpu().double()
        numerator += torch.sum((current - reference) ** 2)
        denominator += torch.sum(reference**2)
    return math.sqrt(float(numerator / denominator))


def _interpolate_with_parent(
    metadata: dict,
    trained: torch.nn.Module,
    parent_state: dict,
    alpha: float,
) -> torch.nn.Module:
    if not math.isfinite(alpha) or not 0.0 < alpha <= 1.0:
        raise ValueError("Interpolation alpha must be within (0, 1]")
    interpolated = {
        name: parent_state[name].detach().cpu()
        + alpha
        * (
            value.detach().cpu()
            - parent_state[name].detach().cpu()
        )
        for name, value in trained.state_dict().items()
    }
    return _make_network(metadata, interpolated)


def _evaluate_candidate(
    online: torch.nn.Module,
    target: torch.nn.Module,
    replay: dict,
    parent_actions: torch.Tensor,
) -> dict:
    indices = torch.arange(int(replay["transition_count"]))
    metrics = _evaluate(online, target, replay, indices, parent_actions)
    with torch.no_grad():
        greedy_actions = online(*_batch(replay, indices)).argmax(dim=1)
    actions = replay["actions"][indices].long()
    positive_energy = (
        replay["continuous"][indices, StateEncoderV2.ENERGY_RATIO_INDEX]
        .float()
        .gt(0.0)
    )
    correction = (
        positive_energy
        & actions.ne(END_TURN_ACTION)
        & parent_actions.eq(END_TURN_ACTION)
    )
    off_target = ~correction
    metrics.update(
        {
            "correction_state_count": int(correction.sum()),
            "off_target_state_count": int(off_target.sum()),
            "off_target_parent_disagreement_count": int(
                greedy_actions[off_target].ne(parent_actions[off_target]).sum()
            ),
            "off_target_parent_disagreement_share": float(
                greedy_actions[off_target]
                .ne(parent_actions[off_target])
                .float()
                .mean()
            ),
        }
    )
    return metrics


def _eligibility(metrics: dict, baseline: dict) -> dict:
    checks = {
        "unseen_smooth_l1_improved": metrics["smooth_l1"]
        < baseline["smooth_l1"],
        "parent_action_agreement_at_least_0_95": metrics[
            "parent_action_agreement"
        ]
        >= PARENT_AGREEMENT_MIN,
        "positive_energy_end_turn_reduced_by_at_least_0_01": metrics[
            "positive_energy_end_turn_share"
        ]
        <= baseline["positive_energy_end_turn_share"]
        - POSITIVE_ENERGY_END_TURN_REDUCTION_MIN,
        "intervention_margin_improved": metrics[
            "intervention_executed_over_end_turn_share"
        ]
        > baseline["intervention_executed_over_end_turn_share"],
        "off_target_parent_disagreement_at_most_0_03": metrics[
            "off_target_parent_disagreement_share"
        ]
        <= OFF_TARGET_DISAGREEMENT_MAX,
    }
    checks["all_conditions_passed"] = all(checks.values())
    return checks


def _load_replay(path: Path) -> tuple[dict, dict, dict]:
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    replay = checkpoint["replay_buffer_state_dict"]
    metadata = checkpoint["metadata"]
    if int(replay["transition_count"]) <= 0:
        raise ValueError(f"Replay is empty: {path}")
    return checkpoint, replay, metadata


def run(args: argparse.Namespace) -> dict:
    if args.td_weight <= 0.0 or not math.isfinite(args.td_weight):
        raise ValueError("TD weight must be finite and positive")
    if args.imitation_weight <= 0.0 or not math.isfinite(args.imitation_weight):
        raise ValueError("Imitation weight must be finite and positive")
    if args.updates <= 0 or args.batch_size <= 0:
        raise ValueError("Updates and batch size must be positive")

    parent_path = args.parent_checkpoint.resolve()
    train_path = args.train_replay_checkpoint.resolve()
    validation_path = args.validation_replay_checkpoint.resolve()
    output_checkpoint = args.output_checkpoint.resolve()
    parent = torch.load(parent_path, map_location="cpu", weights_only=True)
    _, train_replay, train_metadata = _load_replay(train_path)
    _, validation_replay, validation_metadata = _load_replay(validation_path)
    if train_metadata != validation_metadata:
        raise ValueError("Training and validation replay metadata differ")

    train_count = int(train_replay["transition_count"])
    validation_count = int(validation_replay["transition_count"])
    if args.batch_size > train_count:
        raise ValueError("Batch size exceeds the training replay")

    parent_online = _make_network(
        validation_metadata, parent["online_network_state_dict"]
    )
    parent_target = _make_network(
        validation_metadata,
        parent.get(
            "target_network_state_dict", parent["online_network_state_dict"]
        ),
    )
    parent_online.eval()
    parent_target.eval()
    validation_indices = torch.arange(validation_count)
    with torch.no_grad():
        validation_parent_actions = parent_online(
            *_batch(validation_replay, validation_indices)
        ).argmax(dim=1)
    baseline = _evaluate_candidate(
        parent_online,
        parent_target,
        validation_replay,
        validation_parent_actions,
    )

    train_eval_count = min(512, train_count)
    train_eval_indices = torch.arange(train_eval_count)
    train_parent = _make_network(
        train_metadata, parent["online_network_state_dict"]
    )
    train_parent.eval()
    with torch.no_grad():
        train_parent_actions = train_parent(
            *_batch(train_replay, train_eval_indices)
        ).argmax(dim=1)

    replicates = []
    for replicate_seed in args.replicate_seeds:
        rng = np.random.default_rng(replicate_seed)
        batches = [
            torch.from_numpy(
                rng.choice(train_count, size=args.batch_size, replace=False)
            ).long()
            for _ in range(args.updates)
        ]
        train_metrics, network = _train_variant(
            parent=parent,
            replay=train_replay,
            metadata=train_metadata,
            train_count=train_count,
            holdout_indices=train_eval_indices,
            holdout_parent_actions=train_parent_actions,
            batches=batches,
            replicate_seed=replicate_seed,
            imitation_weight=args.imitation_weight,
            learning_rate=args.learning_rate,
            parent_end_turn_only=True,
            imitation_objective="pairwise_end_turn_margin",
            pairwise_margin=args.pairwise_margin,
            td_weight=args.td_weight,
            anchor_objective="q_smooth_l1",
        )
        validation_metrics = _evaluate_candidate(
            network,
            parent_target,
            validation_replay,
            validation_parent_actions,
        )
        replicates.append(
            {
                "replicate_seed": replicate_seed,
                "relative_l2_from_parent": _relative_l2(
                    network, parent["online_network_state_dict"]
                ),
                "mean_total_loss": train_metrics["mean_total_loss"],
                "mean_td_loss": train_metrics["mean_td_loss"],
                "mean_anchor_loss": train_metrics["mean_anchor_loss"],
                "mean_imitation_loss": train_metrics["mean_imitation_loss"],
                "validation": validation_metrics,
                "eligibility": _eligibility(validation_metrics, baseline),
            }
        )

        if args.interpolation_alphas:
            interpolation_results = {}
            for alpha in args.interpolation_alphas:
                interpolated = _interpolate_with_parent(
                    train_metadata,
                    network,
                    parent["online_network_state_dict"],
                    alpha,
                )
                interpolated_metrics = _evaluate_candidate(
                    interpolated,
                    parent_target,
                    validation_replay,
                    validation_parent_actions,
                )
                interpolation_results[str(alpha)] = {
                    "relative_l2_from_parent": _relative_l2(
                        interpolated, parent["online_network_state_dict"]
                    ),
                    "validation": interpolated_metrics,
                    "eligibility": _eligibility(interpolated_metrics, baseline),
                }
            replicates[-1]["interpolations"] = interpolation_results

    eligible_interpolation_alphas = [
        alpha
        for alpha in args.interpolation_alphas
        if all(
            row["interpolations"][str(alpha)]["eligibility"][
                "all_conditions_passed"
            ]
            for row in replicates
        )
    ]
    selected_interpolation_alpha = (
        min(eligible_interpolation_alphas)
        if eligible_interpolation_alphas
        else None
    )
    if args.interpolation_alphas:
        all_replicates_passed = selected_interpolation_alpha is not None
    else:
        all_replicates_passed = all(
            row["eligibility"]["all_conditions_passed"] for row in replicates
        )
    result = {
        "schema_version": 1,
        "experiment_id": args.experiment_id,
        "source_commit": args.source_commit,
        "inputs": {
            "parent_checkpoint": {
                "path": str(parent_path),
                "sha256": _sha256(parent_path),
            },
            "train_replay_checkpoint": {
                "path": str(train_path),
                "sha256": _sha256(train_path),
                "transition_count": train_count,
            },
            "unseen_validation_replay_checkpoint": {
                "path": str(validation_path),
                "sha256": _sha256(validation_path),
                "transition_count": validation_count,
            },
        },
        "design": {
            "updates": args.updates,
            "batch_size": args.batch_size,
            "replicate_seeds": args.replicate_seeds,
            "candidate_seed": args.candidate_seed,
            "learning_rate": args.learning_rate,
            "td_weight": args.td_weight,
            "parent_anchor_objective": "q_smooth_l1",
            "parent_anchor_weight": 1.0,
            "imitation_objective": "pairwise_end_turn_margin",
            "imitation_weight": args.imitation_weight,
            "pairwise_margin": args.pairwise_margin,
            "single_fixed_configuration": True,
            "interpolation_alphas": args.interpolation_alphas,
        },
        "eligibility_thresholds": {
            "unseen_smooth_l1_must_improve": True,
            "parent_action_agreement_min": PARENT_AGREEMENT_MIN,
            "positive_energy_end_turn_reduction_min": POSITIVE_ENERGY_END_TURN_REDUCTION_MIN,
            "intervention_margin_must_improve": True,
            "off_target_parent_disagreement_max": OFF_TARGET_DISAGREEMENT_MAX,
            "all_replicates_must_pass": True,
        },
        "unseen_parent_baseline": baseline,
        "replicates": replicates,
        "eligible_interpolation_alphas": eligible_interpolation_alphas,
        "selected_interpolation_alpha": selected_interpolation_alpha,
        "all_replicates_passed": all_replicates_passed,
        "authority": "offline model fitting only; no promotion authority",
    }

    if all_replicates_passed:
        rng = np.random.default_rng(args.candidate_seed)
        batches = [
            torch.from_numpy(
                rng.choice(train_count, size=args.batch_size, replace=False)
            ).long()
            for _ in range(args.updates)
        ]
        train_metrics, candidate = _train_variant(
            parent=parent,
            replay=train_replay,
            metadata=train_metadata,
            train_count=train_count,
            holdout_indices=train_eval_indices,
            holdout_parent_actions=train_parent_actions,
            batches=batches,
            replicate_seed=args.candidate_seed,
            imitation_weight=args.imitation_weight,
            learning_rate=args.learning_rate,
            parent_end_turn_only=True,
            imitation_objective="pairwise_end_turn_margin",
            pairwise_margin=args.pairwise_margin,
            td_weight=args.td_weight,
            anchor_objective="q_smooth_l1",
        )
        if selected_interpolation_alpha is not None:
            candidate = _interpolate_with_parent(
                train_metadata,
                candidate,
                parent["online_network_state_dict"],
                selected_interpolation_alpha,
            )
        candidate_metrics = _evaluate_candidate(
            candidate,
            parent_target,
            validation_replay,
            validation_parent_actions,
        )
        candidate_eligibility = _eligibility(candidate_metrics, baseline)
        result["candidate_fit"] = {
            "seed": args.candidate_seed,
            "relative_l2_from_parent": _relative_l2(
                candidate, parent["online_network_state_dict"]
            ),
            "mean_total_loss": train_metrics["mean_total_loss"],
            "mean_td_loss": train_metrics["mean_td_loss"],
            "mean_anchor_loss": train_metrics["mean_anchor_loss"],
            "mean_imitation_loss": train_metrics["mean_imitation_loss"],
            "validation": candidate_metrics,
            "eligibility": candidate_eligibility,
        }
        if candidate_eligibility["all_conditions_passed"]:
            state = {
                name: value.detach().cpu()
                for name, value in candidate.state_dict().items()
            }
            payload = {
                "checkpoint_schema_version": 2,
                "checkpoint_kind": "weights",
                "metadata": train_metadata,
                "rl_space_version": train_metadata["rl_space_version"],
                "online_network_state_dict": state,
                "episode": 0,
                "provenance": {
                    "construction": "outcome_constrained_pairwise_candidate",
                    "experiment_id": args.experiment_id,
                    "source_commit": args.source_commit,
                    "parent_checkpoint_sha256": _sha256(parent_path),
                    "train_replay_checkpoint_sha256": _sha256(train_path),
                    "validation_replay_checkpoint_sha256": _sha256(validation_path),
                    "candidate_seed": args.candidate_seed,
                    "updates": args.updates,
                    "batch_size": args.batch_size,
                    "learning_rate": args.learning_rate,
                    "td_weight": args.td_weight,
                    "imitation_weight": args.imitation_weight,
                    "pairwise_margin": args.pairwise_margin,
                    "interpolation_alpha": selected_interpolation_alpha,
                },
            }
            _atomic_torch_save(payload, output_checkpoint)
            loaded = torch.load(
                output_checkpoint, map_location="cpu", weights_only=True
            )
            if not _state_dict_equal(loaded["online_network_state_dict"], state):
                raise ValueError("Candidate checkpoint did not round-trip")
            result["selected_checkpoint"] = {
                "path": str(output_checkpoint),
                "sha256": _sha256(output_checkpoint),
                "size_bytes": output_checkpoint.stat().st_size,
            }

    if "selected_checkpoint" not in result:
        result["decision"] = "not_eligible_for_live_gate"
    elif args.requires_fresh_offline_confirmation:
        result["decision"] = "eligible_for_fresh_offline_confirmation_only"
    else:
        result["decision"] = "eligible_for_fresh_live_gate"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent-checkpoint", type=Path, required=True)
    parser.add_argument("--train-replay-checkpoint", type=Path, required=True)
    parser.add_argument("--validation-replay-checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-checkpoint", type=Path, required=True)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--updates", type=int, default=64)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--replicate-seeds", type=int, nargs="+", default=[101, 202, 303])
    parser.add_argument("--candidate-seed", type=int, default=404)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--td-weight", type=float, default=0.05)
    parser.add_argument("--imitation-weight", type=float, default=0.02)
    parser.add_argument("--pairwise-margin", type=float, default=1.0)
    parser.add_argument("--interpolation-alphas", type=float, nargs="+", default=[])
    parser.add_argument("--requires-fresh-offline-confirmation", action="store_true")
    return parser


def main() -> int:
    result = run(build_parser().parse_args())
    print(
        json.dumps(
            {
                "decision": result["decision"],
                "all_replicates_passed": result["all_replicates_passed"],
                "selected_checkpoint": result.get("selected_checkpoint"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
