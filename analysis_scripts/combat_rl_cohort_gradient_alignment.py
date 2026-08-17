"""Measure one-step TD gradient alignment across immutable replay cohorts."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import torch
import torch.nn.functional as F


REPO_ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_DIR = Path(__file__).resolve().parent
for import_root in (REPO_ROOT, ANALYSIS_DIR):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from combat_rl_dropout_update_ablation import _batch, _make_network  # noqa: E402
from combat_rl_n_step_return_candidate import (  # noqa: E402
    _load,
    _n_step_targets,
    _sha256,
)


def _parse_cohort(value: str) -> tuple[str, Path]:
    name, separator, raw_path = value.partition("=")
    if not separator or not name or not raw_path:
        raise argparse.ArgumentTypeError("Cohort must use NAME=PATH")
    return name, Path(raw_path)


def _cosine_similarity(left: torch.Tensor, right: torch.Tensor) -> float:
    denominator = float(
        torch.linalg.vector_norm(left) * torch.linalg.vector_norm(right)
    )
    if denominator == 0.0:
        return math.nan
    return float(torch.dot(left, right) / denominator)


def _weighted_mean_gradient(
    gradients: list[torch.Tensor], weights: list[int]
) -> torch.Tensor:
    if not gradients or len(gradients) != len(weights):
        raise ValueError("Gradients and weights must be non-empty and aligned")
    total_weight = sum(weights)
    if total_weight <= 0:
        raise ValueError("Gradient weights must sum to a positive value")
    return sum(
        (
            gradient * (weight / total_weight)
            for gradient, weight in zip(gradients, weights)
        ),
        torch.zeros_like(gradients[0]),
    )


def _gradient_for_indices(
    *,
    parent_state: dict,
    metadata: dict,
    replay: dict,
    targets: torch.Tensor,
    indices: torch.Tensor,
    chunk_size: int,
) -> tuple[torch.Tensor, float]:
    if indices.numel() == 0:
        raise ValueError("Gradient stratum must contain at least one row")
    if chunk_size <= 0:
        raise ValueError("Chunk size must be positive")

    network = _make_network(metadata, parent_state)
    network.eval()
    network.zero_grad()
    loss_sum = 0.0
    count = int(indices.numel())
    for start in range(0, count, chunk_size):
        selected_indices = indices[start : start + chunk_size]
        rows = torch.arange(selected_indices.numel())
        actions = replay["actions"][selected_indices].long()
        selected_q = network(*_batch(replay, selected_indices))[rows, actions]
        chunk_loss = F.smooth_l1_loss(
            selected_q,
            targets[selected_indices],
            reduction="sum",
        )
        (chunk_loss / count).backward()
        loss_sum += float(chunk_loss)

    gradient = torch.cat(
        [
            parameter.grad.detach().cpu().reshape(-1)
            for parameter in network.parameters()
            if parameter.grad is not None
        ]
    ).double()
    return gradient, loss_sum / count


def _pairwise_cosines(gradients: dict[str, torch.Tensor]) -> dict:
    return {
        left_name: {
            right_name: _cosine_similarity(left, right)
            for right_name, right in gradients.items()
        }
        for left_name, left in gradients.items()
    }


def run(args: argparse.Namespace) -> dict:
    if len(args.cohort) < 2:
        raise ValueError("At least two cohorts are required")
    cohort_names = [name for name, _ in args.cohort]
    if len(set(cohort_names)) != len(cohort_names):
        raise ValueError("Cohort names must be unique")
    if not 0.0 <= args.gamma <= 1.0:
        raise ValueError("Gamma must be within [0, 1]")

    parent_path = args.parent_checkpoint.resolve()
    parent = torch.load(parent_path, map_location="cpu", weights_only=True)
    parent_state = parent["online_network_state_dict"]
    target_state = parent.get("target_network_state_dict", parent_state)

    loaded = {}
    metadata = None
    for name, path in args.cohort:
        resolved = path.resolve()
        _, replay, cohort_metadata = _load(resolved)
        if metadata is None:
            metadata = cohort_metadata
        elif cohort_metadata != metadata:
            raise ValueError("Replay cohort metadata differ")
        loaded[name] = {"path": resolved, "replay": replay}

    gradients_by_stratum = {
        "all": {},
        "terminal": {},
        "nonterminal": {},
    }
    cohort_records = {}
    for name, row in loaded.items():
        replay = row["replay"]
        count = int(replay["transition_count"])
        dones = replay["dones"][:count].bool()
        parent_online = _make_network(metadata, parent_state)
        parent_target = _make_network(metadata, target_state)
        targets = _n_step_targets(
            parent_online,
            parent_target,
            replay,
            horizon=1,
            gamma=args.gamma,
        )
        strata = {
            "all": torch.arange(count),
            "terminal": torch.flatnonzero(dones),
            "nonterminal": torch.flatnonzero(~dones),
        }
        losses = {}
        gradient_norms = {}
        row_counts = {}
        for stratum, indices in strata.items():
            gradient, loss = _gradient_for_indices(
                parent_state=parent_state,
                metadata=metadata,
                replay=replay,
                targets=targets,
                indices=indices,
                chunk_size=args.chunk_size,
            )
            gradients_by_stratum[stratum][name] = gradient
            losses[stratum] = loss
            gradient_norms[stratum] = float(torch.linalg.vector_norm(gradient))
            row_counts[stratum] = int(indices.numel())
        rewards = replay["rewards"][:count].float()
        cohort_records[name] = {
            "path": str(row["path"]),
            "sha256": _sha256(row["path"]),
            "transition_count": count,
            "terminal_count": int(dones.sum()),
            "reward_mean": float(rewards.mean()),
            "reward_min": float(rewards.min()),
            "reward_max": float(rewards.max()),
            "smooth_l1": losses,
            "gradient_norm": gradient_norms,
            "stratum_row_count": row_counts,
        }

    alignment = {}
    for stratum, gradients in gradients_by_stratum.items():
        counts = {
            name: cohort_records[name]["stratum_row_count"][stratum]
            for name in cohort_names
        }
        aggregate = _weighted_mean_gradient(
            [gradients[name] for name in cohort_names],
            [counts[name] for name in cohort_names],
        )
        leave_one_out = {}
        for held_out in cohort_names:
            training_names = [name for name in cohort_names if name != held_out]
            training_gradient = _weighted_mean_gradient(
                [gradients[name] for name in training_names],
                [counts[name] for name in training_names],
            )
            cosine = _cosine_similarity(gradients[held_out], training_gradient)
            leave_one_out[held_out] = {
                "training_cohorts": training_names,
                "cosine": cosine,
                "first_order_descent_on_held_out": cosine > 0.0,
            }
        alignment[stratum] = {
            "pairwise_cosine": _pairwise_cosines(gradients),
            "weighted_aggregate_gradient_norm": float(
                torch.linalg.vector_norm(aggregate)
            ),
            "cohort_cosine_with_weighted_aggregate": {
                name: _cosine_similarity(gradient, aggregate)
                for name, gradient in gradients.items()
            },
            "leave_one_out": leave_one_out,
        }

    result = {
        "schema_version": 1,
        "audit_id": args.audit_id,
        "source_commit": args.source_commit,
        "design": {
            "objective": "one_step_double_dqn_smooth_l1_at_promoted_parent",
            "gamma": args.gamma,
            "chunk_size": args.chunk_size,
            "network_mode": "eval",
            "model_fitting": False,
            "policy_evaluation": False,
        },
        "parent_checkpoint": {
            "path": str(parent_path),
            "sha256": _sha256(parent_path),
        },
        "cohorts": cohort_records,
        "alignment": alignment,
        "authority": "read-only gradient diagnosis; no candidate or live authority",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent-checkpoint", type=Path, required=True)
    parser.add_argument(
        "--cohort",
        action="append",
        type=_parse_cohort,
        required=True,
        metavar="NAME=PATH",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--audit-id", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--gamma", type=float, default=0.99)
    parser.add_argument("--chunk-size", type=int, default=128)
    return parser


def main() -> int:
    result = run(build_parser().parse_args())
    print(
        json.dumps(
            {
                stratum: row["leave_one_out"]
                for stratum, row in result["alignment"].items()
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
