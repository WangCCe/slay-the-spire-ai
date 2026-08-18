"""Fit a full-combat-return candidate with an End Turn trust constraint."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import torch


REPO_ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_DIR = Path(__file__).resolve().parent
for import_root in (REPO_ROOT, ANALYSIS_DIR):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from combat_rl_dropout_update_ablation import _batch, _make_network  # noqa: E402
from combat_rl_n_step_return_candidate import (  # noqa: E402
    _evaluate_n_step,
    _fit_full_gradient,
    _load,
    _n_step_targets,
    _sha256,
)
from combat_rl_outcome_constrained_pairwise_candidate import (  # noqa: E402
    _interpolate_with_parent,
    _relative_l2,
)
from combat_rl_positive_energy_imitation_ablation import (  # noqa: E402
    _atomic_torch_save,
    _state_dict_equal,
)


def _development_eligibility(metrics: dict, baseline: dict) -> dict:
    checks = {
        "full_return_smooth_l1_improved": (
            metrics["smooth_l1"] < baseline["smooth_l1"]
        ),
        "one_step_smooth_l1_improved": (
            metrics["one_step_smooth_l1"]
            < baseline["one_step_smooth_l1"]
        ),
        "parent_action_agreement_at_least_0_99": (
            metrics["parent_action_agreement"] >= 0.99
        ),
        "off_target_parent_disagreement_at_most_0_01": (
            metrics["off_target_parent_disagreement_share"] <= 0.01
        ),
        "positive_energy_end_turn_count_increase_at_most_1": (
            metrics["positive_energy_end_turn_count"]
            <= baseline["positive_energy_end_turn_count"] + 1
        ),
    }
    checks["all_conditions_passed"] = all(checks.values())
    return checks


def _select_eligible_weight(configurations: list[dict]) -> float | None:
    passing = [
        float(row["end_turn_preservation_weight"])
        for row in configurations
        if float(row["end_turn_preservation_weight"]) > 0.0
        and row["all_development_replays_passed"] is True
    ]
    return min(passing) if passing else None


def _evaluate_development_replay(
    *,
    parent: dict,
    candidate: torch.nn.Module,
    replay_path: Path,
    expected_metadata: dict,
    horizon: int,
    gamma: float,
) -> dict:
    _, replay, metadata = _load(replay_path)
    if metadata != expected_metadata:
        raise ValueError(f"Development replay metadata differs: {replay_path}")
    count = int(replay["transition_count"])
    indices = torch.arange(count)
    parent_online = _make_network(metadata, parent["online_network_state_dict"])
    parent_target = _make_network(
        metadata,
        parent.get(
            "target_network_state_dict", parent["online_network_state_dict"]
        ),
    )
    targets = _n_step_targets(
        parent_online,
        parent_target,
        replay,
        horizon=horizon,
        gamma=gamma,
    )
    with torch.no_grad():
        parent_actions = parent_online(*_batch(replay, indices)).argmax(dim=1)
    baseline = _evaluate_n_step(
        parent_online,
        parent_target,
        replay,
        parent_actions,
        targets,
    )
    metrics = _evaluate_n_step(
        candidate,
        parent_target,
        replay,
        parent_actions,
        targets,
    )
    return {
        "path": str(replay_path),
        "sha256": _sha256(replay_path),
        "transition_count": count,
        "parent_baseline": baseline,
        "candidate": metrics,
        "eligibility": _development_eligibility(metrics, baseline),
    }


def run(args: argparse.Namespace) -> dict:
    if args.horizon <= 0:
        raise ValueError("Return horizon must be positive")
    if not 0.0 <= args.gamma <= 1.0:
        raise ValueError("Gamma must be within [0, 1]")
    if not 0.0 < args.interpolation_alpha <= 1.0:
        raise ValueError("Interpolation alpha must be within (0, 1]")
    if not args.end_turn_preservation_weights:
        raise ValueError("At least one End Turn preservation weight is required")
    if any(
        not math.isfinite(weight) or weight < 0.0
        for weight in args.end_turn_preservation_weights
    ):
        raise ValueError("End Turn preservation weights must be non-negative")
    if len(set(args.end_turn_preservation_weights)) != len(
        args.end_turn_preservation_weights
    ):
        raise ValueError("End Turn preservation weights must be unique")

    parent_path = args.parent_checkpoint.resolve()
    train_path = args.train_replay_checkpoint.resolve()
    development_paths = [path.resolve() for path in args.development_replay_checkpoints]
    output_checkpoint = args.output_checkpoint.resolve()
    parent = torch.load(parent_path, map_location="cpu", weights_only=True)
    _, train_replay, train_metadata = _load(train_path)
    parent_online = _make_network(
        train_metadata, parent["online_network_state_dict"]
    )
    parent_target = _make_network(
        train_metadata,
        parent.get(
            "target_network_state_dict", parent["online_network_state_dict"]
        ),
    )
    train_targets = _n_step_targets(
        parent_online,
        parent_target,
        train_replay,
        horizon=args.horizon,
        gamma=args.gamma,
    )

    configurations = []
    candidates: dict[float, torch.nn.Module] = {}
    for weight in args.end_turn_preservation_weights:
        trained, training = _fit_full_gradient(
            parent=parent,
            metadata=train_metadata,
            replay=train_replay,
            targets=train_targets,
            chunk_size=args.batch_size,
            steps=args.full_gradient_steps,
            learning_rate=args.learning_rate,
            td_weight=args.td_weight,
            optimizer_name="sgd",
            end_turn_preservation_weight=weight,
            end_turn_preservation_margin_floor=(
                args.end_turn_preservation_margin_floor
            ),
        )
        candidate = _interpolate_with_parent(
            train_metadata,
            trained,
            parent["online_network_state_dict"],
            args.interpolation_alpha,
        )
        candidates[weight] = candidate
        development = {
            path.parent.name: _evaluate_development_replay(
                parent=parent,
                candidate=candidate,
                replay_path=path,
                expected_metadata=train_metadata,
                horizon=args.horizon,
                gamma=args.gamma,
            )
            for path in development_paths
        }
        configurations.append(
            {
                "end_turn_preservation_weight": weight,
                "training": training,
                "relative_l2_from_parent": _relative_l2(
                    candidate, parent["online_network_state_dict"]
                ),
                "development_replays": development,
                "all_development_replays_passed": all(
                    row["eligibility"]["all_conditions_passed"]
                    for row in development.values()
                ),
            }
        )

    selected_weight = _select_eligible_weight(configurations)
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
                "transition_count": int(train_replay["transition_count"]),
            },
            "development_replay_checkpoints": [
                {"path": str(path), "sha256": _sha256(path)}
                for path in development_paths
            ],
        },
        "design": {
            "objective": "full_combat_return_with_parent_non_end_margin_preservation",
            "horizon": args.horizon,
            "gamma": args.gamma,
            "optimizer": "sgd",
            "full_gradient_steps": args.full_gradient_steps,
            "batch_size": args.batch_size,
            "learning_rate": args.learning_rate,
            "td_weight": args.td_weight,
            "parent_anchor_objective": "q_smooth_l1",
            "parent_anchor_weight": 1.0,
            "end_turn_preservation_weights": args.end_turn_preservation_weights,
            "end_turn_preservation_margin_floor": (
                args.end_turn_preservation_margin_floor
            ),
            "interpolation_alpha": args.interpolation_alpha,
            "selection": "smallest positive weight passing every development replay",
        },
        "configurations": configurations,
        "selected_end_turn_preservation_weight": selected_weight,
        "authority": "consumed-development fitting only; fresh replay confirmation required before any live gate",
    }

    if selected_weight is not None:
        selected = candidates[selected_weight]
        state = {
            name: value.detach().cpu()
            for name, value in selected.state_dict().items()
        }
        payload = {
            "checkpoint_schema_version": 2,
            "checkpoint_kind": "weights",
            "metadata": train_metadata,
            "rl_space_version": train_metadata["rl_space_version"],
            "online_network_state_dict": state,
            "episode": 0,
            "provenance": {
                "construction": "full_combat_return_end_turn_trust_interpolation",
                "experiment_id": args.experiment_id,
                "source_commit": args.source_commit,
                "parent_checkpoint_sha256": _sha256(parent_path),
                "train_replay_checkpoint_sha256": _sha256(train_path),
                "development_replay_checkpoint_sha256": [
                    _sha256(path) for path in development_paths
                ],
                "horizon": args.horizon,
                "gamma": args.gamma,
                "optimizer": "sgd",
                "full_gradient_steps": args.full_gradient_steps,
                "batch_size": args.batch_size,
                "learning_rate": args.learning_rate,
                "td_weight": args.td_weight,
                "end_turn_preservation_weight": selected_weight,
                "end_turn_preservation_margin_floor": (
                    args.end_turn_preservation_margin_floor
                ),
                "interpolation_alpha": args.interpolation_alpha,
            },
        }
        _atomic_torch_save(payload, output_checkpoint)
        loaded = torch.load(
            output_checkpoint, map_location="cpu", weights_only=True
        )
        if not _state_dict_equal(loaded["online_network_state_dict"], state):
            raise ValueError("End Turn trust checkpoint did not round-trip")
        result["selected_checkpoint"] = {
            "path": str(output_checkpoint),
            "sha256": _sha256(output_checkpoint),
            "size_bytes": output_checkpoint.stat().st_size,
        }

    result["decision"] = (
        "eligible_for_fresh_replay_confirmation_only"
        if "selected_checkpoint" in result
        else "not_eligible_for_fresh_replay_confirmation"
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent-checkpoint", type=Path, required=True)
    parser.add_argument("--train-replay-checkpoint", type=Path, required=True)
    parser.add_argument(
        "--development-replay-checkpoints", type=Path, nargs="+", required=True
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-checkpoint", type=Path, required=True)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--horizon", type=int, default=4096)
    parser.add_argument("--gamma", type=float, default=0.99)
    parser.add_argument("--full-gradient-steps", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--td-weight", type=float, default=0.2)
    parser.add_argument(
        "--end-turn-preservation-weights",
        type=float,
        nargs="+",
        default=[0.0, 0.25, 0.5, 1.0, 2.0, 4.0],
    )
    parser.add_argument(
        "--end-turn-preservation-margin-floor", type=float, default=0.0
    )
    parser.add_argument("--interpolation-alpha", type=float, default=0.5)
    return parser


def main() -> int:
    result = run(build_parser().parse_args())
    print(
        json.dumps(
            {
                "decision": result["decision"],
                "selected_end_turn_preservation_weight": result[
                    "selected_end_turn_preservation_weight"
                ],
                "selected_checkpoint": result.get("selected_checkpoint"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
