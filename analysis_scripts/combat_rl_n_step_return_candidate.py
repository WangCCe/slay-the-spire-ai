"""Fit a conservative n-step combat candidate and validate on replay."""

from __future__ import annotations

import argparse
import hashlib
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
from combat_rl_outcome_constrained_pairwise_candidate import (  # noqa: E402
    _build_batches,
    _evaluate_candidate,
    _interpolate_with_parent,
    _relative_l2,
    _td_only_eligibility,
)
from combat_rl_positive_energy_imitation_ablation import (  # noqa: E402
    _atomic_torch_save,
    _parent_anchor_loss,
    _state_dict_equal,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _n_step_targets_from_bootstrap(
    rewards: torch.Tensor,
    dones: torch.Tensor,
    bootstrap_values: torch.Tensor,
    *,
    horizon: int,
    gamma: float,
) -> torch.Tensor:
    if horizon <= 0:
        raise ValueError("N-step horizon must be positive")
    if not 0.0 <= gamma <= 1.0:
        raise ValueError("Gamma must be within [0, 1]")
    count = int(rewards.numel())
    targets = torch.empty(count, dtype=torch.float32)
    for start in range(count):
        total = 0.0
        discount = 1.0
        terminal = False
        last = start
        for offset in range(horizon):
            index = start + offset
            if index >= count:
                terminal = True
                break
            total += discount * float(rewards[index])
            last = index
            if bool(dones[index]):
                terminal = True
                break
            discount *= gamma
        if not terminal:
            total += discount * float(bootstrap_values[last])
        targets[start] = total
    return targets


def _n_step_targets(
    parent_online: torch.nn.Module,
    parent_target: torch.nn.Module,
    replay: dict,
    *,
    horizon: int,
    gamma: float,
) -> torch.Tensor:
    count = int(replay["transition_count"])
    indices = torch.arange(count)
    parent_online.eval()
    parent_target.eval()
    with torch.no_grad():
        next_online_q = parent_online(*_batch(replay, indices, "next_"))
        next_actions = next_online_q.argmax(dim=1)
        next_target_q = parent_target(*_batch(replay, indices, "next_"))
        bootstrap_values = next_target_q[indices, next_actions]
    return _n_step_targets_from_bootstrap(
        replay["rewards"][:count].float(),
        replay["dones"][:count].bool(),
        bootstrap_values,
        horizon=horizon,
        gamma=gamma,
    )


def _evaluate_n_step(
    online: torch.nn.Module,
    parent_target: torch.nn.Module,
    replay: dict,
    parent_actions: torch.Tensor,
    targets: torch.Tensor,
) -> dict:
    metrics = _evaluate_candidate(
        online, parent_target, replay, parent_actions
    )
    indices = torch.arange(int(replay["transition_count"]))
    actions = replay["actions"][indices].long()
    online.eval()
    with torch.no_grad():
        selected_q = online(*_batch(replay, indices))[indices, actions]
    absolute_error = (targets - selected_q).abs()
    metrics["one_step_smooth_l1"] = metrics["smooth_l1"]
    metrics["smooth_l1"] = float(F.smooth_l1_loss(selected_q, targets))
    metrics["absolute_td_p50"] = float(torch.quantile(absolute_error, 0.50))
    metrics["absolute_td_p95"] = float(torch.quantile(absolute_error, 0.95))
    return metrics


def _fit(
    *,
    parent: dict,
    metadata: dict,
    replay: dict,
    targets: torch.Tensor,
    batches: list[torch.Tensor],
    seed: int,
    learning_rate: float,
    td_weight: float,
) -> tuple[torch.nn.Module, dict]:
    online = _make_network(metadata, parent["online_network_state_dict"])
    anchor = _make_network(metadata, parent["online_network_state_dict"])
    anchor.eval()
    for parameter in anchor.parameters():
        parameter.requires_grad_(False)
    optimizer = torch.optim.Adam(online.parameters(), lr=learning_rate)
    total_losses = []
    td_losses = []
    anchor_losses = []
    for update, indices in enumerate(batches):
        rows = torch.arange(indices.numel())
        actions = replay["actions"][indices].long()
        action_masks = replay["action_masks"][indices].bool()
        online.train()
        torch.manual_seed(seed * 100_000 + update)
        q_values = online(*_batch(replay, indices))
        selected_q = q_values[rows, actions]
        with torch.no_grad():
            anchor_q = anchor(*_batch(replay, indices))
        td_loss = F.smooth_l1_loss(selected_q, targets[indices])
        anchor_loss = _parent_anchor_loss(
            q_values, anchor_q, action_masks, "q_smooth_l1"
        )
        loss = td_weight * td_loss + anchor_loss
        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(online.parameters(), max_norm=10.0)
        optimizer.step()
        total_losses.append(float(loss))
        td_losses.append(float(td_loss))
        anchor_losses.append(float(anchor_loss))
    return online, {
        "updates": len(batches),
        "mean_total_loss": sum(total_losses) / len(total_losses),
        "mean_td_loss": sum(td_losses) / len(td_losses),
        "mean_anchor_loss": sum(anchor_losses) / len(anchor_losses),
    }


def _load(path: Path) -> tuple[dict, dict, dict]:
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    replay = checkpoint["replay_buffer_state_dict"]
    if int(replay["transition_count"]) <= 0:
        raise ValueError(f"Replay is empty: {path}")
    return checkpoint, replay, checkpoint["metadata"]


def run(args: argparse.Namespace) -> dict:
    if args.horizon <= 1:
        raise ValueError("This experiment requires an n-step horizon above one")
    if not 0.0 <= args.gamma <= 1.0:
        raise ValueError("Gamma must be within [0, 1]")
    if args.td_weight <= 0.0 or not math.isfinite(args.td_weight):
        raise ValueError("TD weight must be finite and positive")
    if args.full_coverage_epochs <= 0:
        raise ValueError("At least one full-coverage epoch is required")

    parent_path = args.parent_checkpoint.resolve()
    train_path = args.train_replay_checkpoint.resolve()
    validation_path = args.validation_replay_checkpoint.resolve()
    output_checkpoint = args.output_checkpoint.resolve()
    parent = torch.load(parent_path, map_location="cpu", weights_only=True)
    _, train_replay, train_metadata = _load(train_path)
    _, validation_replay, validation_metadata = _load(validation_path)
    if train_metadata != validation_metadata:
        raise ValueError("Training and validation replay metadata differ")

    train_count = int(train_replay["transition_count"])
    validation_count = int(validation_replay["transition_count"])
    train_parent_online = _make_network(
        train_metadata, parent["online_network_state_dict"]
    )
    train_parent_target = _make_network(
        train_metadata,
        parent.get(
            "target_network_state_dict", parent["online_network_state_dict"]
        ),
    )
    validation_parent_online = _make_network(
        validation_metadata, parent["online_network_state_dict"]
    )
    validation_parent_target = _make_network(
        validation_metadata,
        parent.get(
            "target_network_state_dict", parent["online_network_state_dict"]
        ),
    )
    train_targets = _n_step_targets(
        train_parent_online,
        train_parent_target,
        train_replay,
        horizon=args.horizon,
        gamma=args.gamma,
    )
    validation_targets = _n_step_targets(
        validation_parent_online,
        validation_parent_target,
        validation_replay,
        horizon=args.horizon,
        gamma=args.gamma,
    )
    validation_indices = torch.arange(validation_count)
    with torch.no_grad():
        validation_parent_actions = validation_parent_online(
            *_batch(validation_replay, validation_indices)
        ).argmax(dim=1)
    baseline = _evaluate_n_step(
        validation_parent_online,
        validation_parent_target,
        validation_replay,
        validation_parent_actions,
        validation_targets,
    )

    replicates = []
    for seed in args.replicate_seeds:
        batches = _build_batches(
            train_count=train_count,
            batch_size=args.batch_size,
            updates=1,
            seed=seed,
            full_coverage_epochs=args.full_coverage_epochs,
        )
        trained, losses = _fit(
            parent=parent,
            metadata=train_metadata,
            replay=train_replay,
            targets=train_targets,
            batches=batches,
            seed=seed,
            learning_rate=args.learning_rate,
            td_weight=args.td_weight,
        )
        interpolations = {}
        for alpha in args.interpolation_alphas:
            candidate = _interpolate_with_parent(
                train_metadata,
                trained,
                parent["online_network_state_dict"],
                alpha,
            )
            metrics = _evaluate_n_step(
                candidate,
                validation_parent_target,
                validation_replay,
                validation_parent_actions,
                validation_targets,
            )
            interpolations[str(alpha)] = {
                "relative_l2_from_parent": _relative_l2(
                    candidate, parent["online_network_state_dict"]
                ),
                "validation": metrics,
                "eligibility": _td_only_eligibility(metrics, baseline),
            }
        replicates.append(
            {
                "replicate_seed": seed,
                "training": losses,
                "raw_relative_l2_from_parent": _relative_l2(
                    trained, parent["online_network_state_dict"]
                ),
                "interpolations": interpolations,
            }
        )

    eligible_alphas = [
        alpha
        for alpha in args.interpolation_alphas
        if all(
            row["interpolations"][str(alpha)]["eligibility"][
                "all_conditions_passed"
            ]
            for row in replicates
        )
    ]
    selected_alpha = min(eligible_alphas) if eligible_alphas else None
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
            "development_replay_checkpoint": {
                "path": str(validation_path),
                "sha256": _sha256(validation_path),
                "transition_count": validation_count,
            },
        },
        "design": {
            "horizon": args.horizon,
            "gamma": args.gamma,
            "full_coverage_epochs": args.full_coverage_epochs,
            "updates_per_replicate": replicates[0]["training"]["updates"],
            "batch_size": args.batch_size,
            "replicate_seeds": args.replicate_seeds,
            "candidate_seed": args.candidate_seed,
            "learning_rate": args.learning_rate,
            "td_weight": args.td_weight,
            "parent_anchor_objective": "q_smooth_l1",
            "parent_anchor_weight": 1.0,
            "imitation_weight": 0.0,
            "interpolation_alphas": args.interpolation_alphas,
        },
        "development_parent_baseline": baseline,
        "replicates": replicates,
        "eligible_interpolation_alphas": eligible_alphas,
        "selected_interpolation_alpha": selected_alpha,
        "authority": "development-only offline model fitting; fresh replay confirmation required before live evaluation",
    }

    if selected_alpha is not None:
        batches = _build_batches(
            train_count=train_count,
            batch_size=args.batch_size,
            updates=1,
            seed=args.candidate_seed,
            full_coverage_epochs=args.full_coverage_epochs,
        )
        trained, losses = _fit(
            parent=parent,
            metadata=train_metadata,
            replay=train_replay,
            targets=train_targets,
            batches=batches,
            seed=args.candidate_seed,
            learning_rate=args.learning_rate,
            td_weight=args.td_weight,
        )
        candidate = _interpolate_with_parent(
            train_metadata,
            trained,
            parent["online_network_state_dict"],
            selected_alpha,
        )
        metrics = _evaluate_n_step(
            candidate,
            validation_parent_target,
            validation_replay,
            validation_parent_actions,
            validation_targets,
        )
        eligibility = _td_only_eligibility(metrics, baseline)
        result["candidate_fit"] = {
            "seed": args.candidate_seed,
            "training": losses,
            "relative_l2_from_parent": _relative_l2(
                candidate, parent["online_network_state_dict"]
            ),
            "validation": metrics,
            "eligibility": eligibility,
        }
        if eligibility["all_conditions_passed"]:
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
                    "construction": "conservative_n_step_return_interpolation",
                    "experiment_id": args.experiment_id,
                    "source_commit": args.source_commit,
                    "parent_checkpoint_sha256": _sha256(parent_path),
                    "train_replay_checkpoint_sha256": _sha256(train_path),
                    "development_replay_checkpoint_sha256": _sha256(validation_path),
                    "horizon": args.horizon,
                    "gamma": args.gamma,
                    "full_coverage_epochs": args.full_coverage_epochs,
                    "candidate_seed": args.candidate_seed,
                    "batch_size": args.batch_size,
                    "learning_rate": args.learning_rate,
                    "td_weight": args.td_weight,
                    "interpolation_alpha": selected_alpha,
                },
            }
            _atomic_torch_save(payload, output_checkpoint)
            loaded = torch.load(
                output_checkpoint, map_location="cpu", weights_only=True
            )
            if not _state_dict_equal(loaded["online_network_state_dict"], state):
                raise ValueError("N-step candidate checkpoint did not round-trip")
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
    parser.add_argument("--validation-replay-checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-checkpoint", type=Path, required=True)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--horizon", type=int, default=3)
    parser.add_argument("--gamma", type=float, default=0.99)
    parser.add_argument("--full-coverage-epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--replicate-seeds", type=int, nargs="+", default=[101, 202, 303])
    parser.add_argument("--candidate-seed", type=int, default=404)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--td-weight", type=float, default=0.05)
    parser.add_argument("--interpolation-alphas", type=float, nargs="+", default=[0.25, 0.5, 0.75])
    return parser


def main() -> int:
    result = run(build_parser().parse_args())
    print(
        json.dumps(
            {
                "decision": result["decision"],
                "selected_interpolation_alpha": result[
                    "selected_interpolation_alpha"
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
