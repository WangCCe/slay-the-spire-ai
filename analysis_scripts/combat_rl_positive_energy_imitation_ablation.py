"""Test executed-action imitation on positive-energy combat replay states."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from combat_rl_dropout_update_ablation import _batch, _make_network  # noqa: E402
from spirecomm.ai.rl.v2.action_space import END_TURN_ACTION  # noqa: E402
from spirecomm.ai.rl.v2.state_encoder import StateEncoderV2  # noqa: E402


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _quantile(values: torch.Tensor, probability: float) -> float:
    finite = values.detach().float().reshape(-1)
    finite = finite[torch.isfinite(finite)]
    return float(torch.quantile(finite, probability)) if finite.numel() else math.nan


def _evaluate(
    online: torch.nn.Module,
    target: torch.nn.Module,
    replay: dict,
    indices: torch.Tensor,
    parent_actions: torch.Tensor,
) -> dict:
    online.eval()
    target.eval()
    rows = torch.arange(indices.numel())
    actions = replay["actions"][indices].long()
    dones = replay["dones"][indices].bool()
    rewards = replay["rewards"][indices].float()
    positive_energy = (
        replay["continuous"][indices, StateEncoderV2.ENERGY_RATIO_INDEX].float()
        > 0.0
    )
    eligible_imitation = positive_energy & (actions != END_TURN_ACTION)
    correction_eligible = eligible_imitation & (
        parent_actions == END_TURN_ACTION
    )

    with torch.no_grad():
        q_values = online(*_batch(replay, indices))
        next_online_q = online(*_batch(replay, indices, "next_"))
        next_actions = next_online_q.argmax(dim=1)
        next_q = target(*_batch(replay, indices, "next_"))[rows, next_actions]
        next_q = torch.where(dones, torch.zeros_like(next_q), next_q)
        targets = rewards + (~dones).float() * 0.99 * next_q
        selected_q = q_values[rows, actions]
        absolute_td = (targets - selected_q).abs()
        greedy_actions = q_values.argmax(dim=1)

    return {
        "smooth_l1": float(F.smooth_l1_loss(selected_q, targets)),
        "absolute_td_p50": _quantile(absolute_td, 0.50),
        "absolute_td_p95": _quantile(absolute_td, 0.95),
        "parent_action_agreement": float(
            (greedy_actions == parent_actions).float().mean()
        ),
        "executed_action_agreement": float(
            (greedy_actions == actions).float().mean()
        ),
        "eligible_executed_action_agreement": float(
            (greedy_actions[eligible_imitation] == actions[eligible_imitation])
            .float()
            .mean()
        ),
        "correction_state_count": int(correction_eligible.sum()),
        "correction_executed_action_agreement": float(
            (greedy_actions[correction_eligible] == actions[correction_eligible])
            .float()
            .mean()
        ),
        "positive_energy_state_count": int(positive_energy.sum()),
        "positive_energy_end_turn_count": int(
            ((greedy_actions == END_TURN_ACTION) & positive_energy).sum()
        ),
        "positive_energy_end_turn_share": float(
            ((greedy_actions == END_TURN_ACTION) & positive_energy).sum()
            / positive_energy.sum()
        ),
    }


def _train_variant(
    *,
    parent: dict,
    replay: dict,
    metadata: dict,
    train_count: int,
    holdout_indices: torch.Tensor,
    holdout_parent_actions: torch.Tensor,
    batches: list[torch.Tensor],
    replicate_seed: int,
    imitation_weight: float,
    learning_rate: float,
    parent_end_turn_only: bool,
) -> dict:
    online = _make_network(metadata, parent["online_network_state_dict"])
    target = _make_network(
        metadata,
        parent.get("target_network_state_dict", parent["online_network_state_dict"]),
    )
    anchor = _make_network(metadata, parent["online_network_state_dict"])
    target.eval()
    anchor.eval()
    for parameter in anchor.parameters():
        parameter.requires_grad_(False)
    optimizer = torch.optim.Adam(online.parameters(), lr=learning_rate)

    losses = []
    td_losses = []
    anchor_losses = []
    imitation_losses = []
    eligible_counts = []
    for update, indices in enumerate(batches):
        rows = torch.arange(indices.numel())
        actions = replay["actions"][indices].long()
        rewards = replay["rewards"][indices].float()
        dones = replay["dones"][indices].bool()
        action_masks = replay["action_masks"][indices].bool()
        positive_energy = (
            replay["continuous"][
                indices, StateEncoderV2.ENERGY_RATIO_INDEX
            ].float()
            > 0.0
        )
        eligible = positive_energy & (actions != END_TURN_ACTION)

        online.train()
        torch.manual_seed(replicate_seed * 100_000 + update)
        current_q_values = online(*_batch(replay, indices))
        current_q = current_q_values[rows, actions]
        with torch.no_grad():
            next_online_q = online(*_batch(replay, indices, "next_"))
            next_actions = next_online_q.argmax(dim=1)
            next_q = target(*_batch(replay, indices, "next_"))[rows, next_actions]
            next_q = torch.where(dones, torch.zeros_like(next_q), next_q)
            targets = rewards + (~dones).float() * 0.99 * next_q
            anchor_actions = anchor(
                replay["continuous"][indices].float(),
                replay["card_ids"][indices].long(),
                replay["potion_ids"][indices].long(),
                replay["relic_ids"][indices].long(),
                action_masks,
            ).argmax(dim=1)
        if parent_end_turn_only:
            eligible &= anchor_actions == END_TURN_ACTION

        td_loss = F.smooth_l1_loss(current_q, targets)
        anchor_loss = F.cross_entropy(current_q_values, anchor_actions)
        imitation_loss = (
            F.cross_entropy(current_q_values[eligible], actions[eligible])
            if bool(eligible.any())
            else torch.zeros((), dtype=td_loss.dtype)
        )
        loss = td_loss + anchor_loss + imitation_weight * imitation_loss

        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(online.parameters(), max_norm=10.0)
        optimizer.step()

        losses.append(float(loss))
        td_losses.append(float(td_loss))
        anchor_losses.append(float(anchor_loss))
        imitation_losses.append(float(imitation_loss))
        eligible_counts.append(int(eligible.sum()))

    result = _evaluate(
        online,
        target,
        replay,
        holdout_indices,
        holdout_parent_actions,
    )
    result.update(
        {
            "replicate_seed": replicate_seed,
            "imitation_weight": imitation_weight,
            "updates": len(batches),
            "mean_total_loss": float(np.mean(losses)),
            "mean_td_loss": float(np.mean(td_losses)),
            "mean_anchor_loss": float(np.mean(anchor_losses)),
            "mean_imitation_loss": float(np.mean(imitation_losses)),
            "mean_eligible_batch_count": float(np.mean(eligible_counts)),
            "train_count": train_count,
        }
    )
    return result


def run(args: argparse.Namespace) -> dict:
    parent_path = args.parent_checkpoint.resolve()
    replay_path = args.replay_checkpoint.resolve()
    parent = torch.load(parent_path, map_location="cpu", weights_only=True)
    replay_checkpoint = torch.load(replay_path, map_location="cpu", weights_only=True)
    replay = replay_checkpoint["replay_buffer_state_dict"]
    metadata = replay_checkpoint["metadata"]
    transition_count = int(replay["transition_count"])
    if transition_count <= args.holdout_count:
        raise ValueError("Replay must contain more transitions than the holdout")
    train_count = transition_count - args.holdout_count
    if args.batch_size > train_count:
        raise ValueError("Batch size exceeds the training partition")

    holdout_indices = torch.arange(train_count, transition_count)
    parent_network = _make_network(metadata, parent["online_network_state_dict"])
    parent_network.eval()
    with torch.no_grad():
        holdout_parent_actions = parent_network(
            *_batch(replay, holdout_indices)
        ).argmax(dim=1)
    parent_baseline = _evaluate(
        parent_network,
        _make_network(
            metadata,
            parent.get("target_network_state_dict", parent["online_network_state_dict"]),
        ),
        replay,
        holdout_indices,
        holdout_parent_actions,
    )

    replicates = []
    for replicate_seed in args.replicate_seeds:
        rng = np.random.default_rng(replicate_seed)
        batches = [
            torch.from_numpy(
                rng.choice(train_count, size=args.batch_size, replace=False)
            ).long()
            for _ in range(args.updates)
        ]
        for weight in args.imitation_weights:
            replicates.append(
                _train_variant(
                    parent=parent,
                    replay=replay,
                    metadata=metadata,
                    train_count=train_count,
                    holdout_indices=holdout_indices,
                    holdout_parent_actions=holdout_parent_actions,
                    batches=batches,
                    replicate_seed=replicate_seed,
                    imitation_weight=weight,
                    learning_rate=args.learning_rate,
                    parent_end_turn_only=args.parent_end_turn_only,
                )
            )

    metric_names = (
        "smooth_l1",
        "absolute_td_p50",
        "absolute_td_p95",
        "parent_action_agreement",
        "executed_action_agreement",
        "eligible_executed_action_agreement",
        "correction_executed_action_agreement",
        "positive_energy_end_turn_share",
        "mean_total_loss",
        "mean_td_loss",
        "mean_anchor_loss",
        "mean_imitation_loss",
    )
    summaries = {}
    for weight in args.imitation_weights:
        rows = [row for row in replicates if row["imitation_weight"] == weight]
        summaries[str(weight)] = {
            name: {
                "mean": float(np.mean([row[name] for row in rows])),
                "min": float(np.min([row[name] for row in rows])),
                "max": float(np.max([row[name] for row in rows])),
            }
            for name in metric_names
        }

    baseline = summaries[str(args.imitation_weights[0])]
    imitation_agreement_metric = (
        "correction_executed_action_agreement"
        if args.parent_end_turn_only
        else "executed_action_agreement"
    )
    eligible_weights = []
    for weight in args.imitation_weights[1:]:
        summary = summaries[str(weight)]
        if (
            summary["parent_action_agreement"]["min"] >= 0.88
            and summary["positive_energy_end_turn_share"]["max"]
            < baseline["positive_energy_end_turn_share"]["min"]
            and summary[imitation_agreement_metric]["min"]
            > baseline[imitation_agreement_metric]["max"]
            and summary["smooth_l1"]["max"]
            <= baseline["smooth_l1"]["max"] * 1.10
        ):
            eligible_weights.append(weight)

    return {
        "schema_version": 1,
        "source_commit": args.source_commit,
        "analysis_script": {
            "path": str(Path(__file__).resolve()),
            "sha256": _sha256(Path(__file__).resolve()),
        },
        "inputs": {
            "parent_checkpoint": {
                "path": str(parent_path),
                "sha256": _sha256(parent_path),
            },
            "replay_checkpoint": {
                "path": str(replay_path),
                "sha256": _sha256(replay_path),
            },
        },
        "design": {
            "transition_count": transition_count,
            "train_count": train_count,
            "holdout_count": args.holdout_count,
            "batch_size": args.batch_size,
            "updates": args.updates,
            "replicate_seeds": args.replicate_seeds,
            "imitation_weights": args.imitation_weights,
            "learning_rate": args.learning_rate,
            "parent_anchor_weight": 1.0,
            "eligible_states": (
                "energy_ratio > 0 and executed action != EndTurn and "
                "parent greedy action == EndTurn"
                if args.parent_end_turn_only
                else "energy_ratio > 0 and executed action != EndTurn"
            ),
            "parent_end_turn_only": args.parent_end_turn_only,
        },
        "parent_baseline": parent_baseline,
        "replicates": replicates,
        "summaries": summaries,
        "eligible_weights": eligible_weights,
        "selected_weight": min(eligible_weights) if eligible_weights else None,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent-checkpoint", type=Path, required=True)
    parser.add_argument("--replay-checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--updates", type=int, default=64)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--holdout-count", type=int, default=1024)
    parser.add_argument("--replicate-seeds", type=int, nargs="+", default=[101, 202, 303])
    parser.add_argument(
        "--imitation-weights", type=float, nargs="+", default=[0.0, 0.25, 0.5]
    )
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--parent-end-turn-only", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = run(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": str(args.output.resolve()),
                "eligible_weights": result["eligible_weights"],
                "selected_weight": result["selected_weight"],
                "summaries": result["summaries"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
