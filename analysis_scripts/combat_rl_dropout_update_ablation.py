"""Compare combat RL update-stability choices on a fixed replay snapshot."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from spirecomm.ai.rl.v2.network import create_dqn_v2  # noqa: E402


VARIANTS = ("current", "deterministic_bootstrap", "no_dropout")
SNAPSHOT_UPDATES = (0, 8, 32, 64, 128)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _make_network(metadata: dict, state_dict: dict) -> torch.nn.Module:
    network = create_dqn_v2(
        network_type=metadata["network_type"],
        continuous_dim=metadata["continuous_dim"],
        action_dim=metadata["action_dim"],
        card_vocab=metadata["card_vocab"],
        potion_vocab=metadata["potion_vocab"],
        relic_vocab=metadata["relic_vocab"],
        device="cpu",
        card_slots=metadata["card_slots"],
        potion_slots=metadata["potion_slots"],
        relic_slots=metadata["relic_slots"],
    )
    network.load_state_dict(state_dict)
    return network


def _batch(replay: dict, indices: torch.Tensor, prefix: str = "") -> tuple:
    return (
        replay[f"{prefix}continuous"][indices].float(),
        replay[f"{prefix}card_ids"][indices].long(),
        replay[f"{prefix}potion_ids"][indices].long(),
        replay[f"{prefix}relic_ids"][indices].long(),
        replay[f"{prefix}action_masks"][indices].bool(),
    )


def _quantile(values: torch.Tensor, probability: float) -> float:
    values = values.detach().float().reshape(-1)
    values = values[torch.isfinite(values)]
    if not values.numel():
        return math.nan
    return float(torch.quantile(values, probability))


def _relative_l2(network: torch.nn.Module, reference_state: dict) -> float:
    delta_squared = 0.0
    reference_squared = 0.0
    for name, parameter in network.state_dict().items():
        reference = reference_state[name].detach().cpu()
        current = parameter.detach().cpu()
        delta_squared += float(torch.sum((current - reference) ** 2))
        reference_squared += float(torch.sum(reference**2))
    return math.sqrt(delta_squared) / max(math.sqrt(reference_squared), 1e-12)


def _evaluate(
    online: torch.nn.Module,
    target: torch.nn.Module,
    replay: dict,
    indices: torch.Tensor,
    reference_actions: torch.Tensor,
    reference_state: dict,
    gamma: float,
) -> dict:
    online.eval()
    target.eval()
    with torch.no_grad():
        current = _batch(replay, indices)
        next_state = _batch(replay, indices, "next_")
        q_values = online(*current)
        next_online_q = online(*next_state)
        next_actions = next_online_q.argmax(dim=1)
        next_target_q = target(*next_state)

        rows = torch.arange(indices.numel())
        actions = replay["actions"][indices].long()
        rewards = replay["rewards"][indices].float()
        dones = replay["dones"][indices].bool()
        selected_q = q_values[rows, actions]
        next_q = next_target_q[rows, next_actions]
        next_q = torch.where(dones, torch.zeros_like(next_q), next_q)
        targets = rewards + (~dones).float() * gamma * next_q
        absolute_td = (targets - selected_q).abs()

        top_two = torch.topk(q_values, k=2, dim=1).values
        margins = top_two[:, 0] - top_two[:, 1]
        finite_margins = margins[torch.isfinite(margins)]
        greedy_actions = q_values.argmax(dim=1)

    return {
        "smooth_l1": float(F.smooth_l1_loss(selected_q, targets)),
        "absolute_td_p50": _quantile(absolute_td, 0.50),
        "absolute_td_p95": _quantile(absolute_td, 0.95),
        "absolute_td_p99": _quantile(absolute_td, 0.99),
        "greedy_action_agreement_with_entry": float(
            (greedy_actions == reference_actions).float().mean()
        ),
        "executed_action_greedy_share": float((greedy_actions == actions).float().mean()),
        "q_margin_p50": _quantile(finite_margins, 0.50),
        "q_margin_p05": _quantile(finite_margins, 0.05),
        "relative_l2_from_entry": _relative_l2(online, reference_state),
    }


def _train_replicate(
    *,
    variant: str,
    replicate_seed: int,
    entry: dict,
    replay: dict,
    metadata: dict,
    train_count: int,
    holdout_indices: torch.Tensor,
    reference_actions: torch.Tensor,
    updates: int,
    batch_size: int,
    gamma: float,
    target_sync_update: int,
    gradient_clip: float,
    optimizer_mode: str,
    learning_rate: float,
) -> dict:
    online = _make_network(metadata, entry["online_network_state_dict"])
    target = _make_network(metadata, entry["target_network_state_dict"])
    target.eval()
    optimizer = torch.optim.Adam(online.parameters(), lr=learning_rate)
    if optimizer_mode == "preserved":
        optimizer.load_state_dict(copy.deepcopy(entry["optimizer_state_dict"]))
        for parameter_group in optimizer.param_groups:
            parameter_group["lr"] = learning_rate

    schedule_rng = np.random.default_rng(replicate_seed)
    batches = [
        torch.from_numpy(
            schedule_rng.choice(train_count, size=batch_size, replace=False)
        ).long()
        for _ in range(updates)
    ]
    snapshot_updates = set(SNAPSHOT_UPDATES) | {updates}
    snapshots = {}
    losses = []
    gradient_norms = []
    clipped_updates = 0

    for completed_updates in range(updates + 1):
        if completed_updates in snapshot_updates:
            snapshots[str(completed_updates)] = _evaluate(
                online,
                target,
                replay,
                holdout_indices,
                reference_actions,
                entry["online_network_state_dict"],
                gamma,
            )
        if completed_updates == updates:
            break

        indices = batches[completed_updates]
        actions = replay["actions"][indices].long()
        rewards = replay["rewards"][indices].float()
        dones = replay["dones"][indices].bool()
        rows = torch.arange(indices.numel())

        if variant == "no_dropout":
            online.eval()
        else:
            online.train()
        torch.manual_seed(replicate_seed * 100_000 + completed_updates)
        current_q = online(*_batch(replay, indices))
        selected_q = current_q[rows, actions]

        with torch.no_grad():
            if variant == "deterministic_bootstrap":
                online.eval()
            next_online_q = online(*_batch(replay, indices, "next_"))
            next_actions = next_online_q.argmax(dim=1)
            target.eval()
            next_target_q = target(*_batch(replay, indices, "next_"))
            next_q = next_target_q[rows, next_actions]
            next_q = torch.where(dones, torch.zeros_like(next_q), next_q)
            targets = rewards + (~dones).float() * gamma * next_q

        loss = F.smooth_l1_loss(selected_q, targets)
        optimizer.zero_grad()
        loss.backward()
        gradient_norm = float(
            torch.nn.utils.clip_grad_norm_(online.parameters(), gradient_clip)
        )
        optimizer.step()

        losses.append(float(loss))
        gradient_norms.append(gradient_norm)
        clipped_updates += int(gradient_norm > gradient_clip)

        if completed_updates + 1 == target_sync_update:
            target.load_state_dict(online.state_dict())

    return {
        "variant": variant,
        "replicate_seed": replicate_seed,
        "updates": updates,
        "target_sync_update": target_sync_update,
        "gradient_clip": gradient_clip,
        "optimizer_mode": optimizer_mode,
        "learning_rate": learning_rate,
        "mean_training_loss": float(np.mean(losses)),
        "last_32_training_loss": float(np.mean(losses[-32:])),
        "gradient_norm_p50": float(np.quantile(gradient_norms, 0.50)),
        "gradient_norm_p95": float(np.quantile(gradient_norms, 0.95)),
        "gradient_norm_max": float(np.max(gradient_norms)),
        "clipped_update_count": clipped_updates,
        "snapshots": snapshots,
    }


def _aggregate(replicates: list[dict], updates: int) -> dict:
    final_key = str(updates)
    metric_names = sorted(replicates[0]["snapshots"][final_key])
    aggregate = {}
    for name in metric_names:
        values = [replicate["snapshots"][final_key][name] for replicate in replicates]
        aggregate[name] = {
            "mean": float(np.mean(values)),
            "min": float(np.min(values)),
            "max": float(np.max(values)),
        }
    for name in (
        "mean_training_loss",
        "last_32_training_loss",
        "gradient_norm_p50",
        "gradient_norm_p95",
        "gradient_norm_max",
        "clipped_update_count",
    ):
        values = [replicate[name] for replicate in replicates]
        aggregate[name] = {
            "mean": float(np.mean(values)),
            "min": float(np.min(values)),
            "max": float(np.max(values)),
        }
    return aggregate


def run(args: argparse.Namespace) -> dict:
    started = time.monotonic()
    entry_path = args.entry_checkpoint.resolve()
    replay_path = args.replay_checkpoint.resolve()
    entry = torch.load(entry_path, map_location="cpu", weights_only=True)
    replay_checkpoint = torch.load(replay_path, map_location="cpu", weights_only=True)
    replay = replay_checkpoint["replay_buffer_state_dict"]
    metadata = replay_checkpoint["metadata"]

    transition_count = int(replay["transition_count"])
    if transition_count <= args.holdout_count:
        raise ValueError("Replay must contain more transitions than the holdout")
    if args.batch_size > transition_count - args.holdout_count:
        raise ValueError("Batch size exceeds the training partition")

    train_count = transition_count - args.holdout_count
    holdout_indices = torch.arange(train_count, transition_count)
    reference = _make_network(metadata, entry["online_network_state_dict"])
    reference.eval()
    with torch.no_grad():
        reference_actions = reference(*_batch(replay, holdout_indices)).argmax(dim=1)

    result = {
        "schema_version": 1,
        "source_commit": args.source_commit,
        "analysis_script": {
            "path": str(Path(__file__).resolve()),
            "sha256": _sha256(Path(__file__).resolve()),
        },
        "runtime": {
            "device": "cpu",
            "torch_version": torch.__version__,
        },
        "entry_checkpoint": {
            "path": str(entry_path),
            "sha256": _sha256(entry_path),
        },
        "replay_checkpoint": {
            "path": str(replay_path),
            "sha256": _sha256(replay_path),
        },
        "design": {
            "variants": args.variants,
            "gradient_clips": args.gradient_clips,
            "optimizer_modes": args.optimizer_modes,
            "learning_rates": args.learning_rates,
            "replicate_seeds": args.replicate_seeds,
            "updates": args.updates,
            "batch_size": args.batch_size,
            "gamma": args.gamma,
            "target_sync_update": args.target_sync_update,
            "transition_count": transition_count,
            "train_count": train_count,
            "holdout_count": args.holdout_count,
            "partition": "chronological; newest transitions held out",
            "same_batch_schedule_across_variants": True,
        },
        "variants": {},
    }

    for variant in args.variants:
        for gradient_clip in args.gradient_clips:
            for optimizer_mode in args.optimizer_modes:
                for learning_rate in args.learning_rates:
                    experiment_name = (
                        f"{variant}_clip_{gradient_clip:g}_"
                        f"{optimizer_mode}_lr_{learning_rate:g}"
                    )
                    replicates = [
                        _train_replicate(
                            variant=variant,
                            replicate_seed=seed,
                            entry=entry,
                            replay=replay,
                            metadata=metadata,
                            train_count=train_count,
                            holdout_indices=holdout_indices,
                            reference_actions=reference_actions,
                            updates=args.updates,
                            batch_size=args.batch_size,
                            gamma=args.gamma,
                            target_sync_update=args.target_sync_update,
                            gradient_clip=gradient_clip,
                            optimizer_mode=optimizer_mode,
                            learning_rate=learning_rate,
                        )
                        for seed in args.replicate_seeds
                    ]
                    result["variants"][experiment_name] = {
                        "variant": variant,
                        "gradient_clip": gradient_clip,
                        "optimizer_mode": optimizer_mode,
                        "learning_rate": learning_rate,
                        "replicates": replicates,
                        "final_aggregate": _aggregate(replicates, args.updates),
                    }

    result["runtime_seconds"] = time.monotonic() - started
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entry-checkpoint", type=Path, required=True)
    parser.add_argument("--replay-checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--updates", type=int, default=282)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--holdout-count", type=int, default=1024)
    parser.add_argument("--gamma", type=float, default=0.99)
    parser.add_argument("--target-sync-update", type=int, default=15)
    parser.add_argument("--replicate-seeds", type=int, nargs="+", default=[17, 29, 43])
    parser.add_argument("--variants", choices=VARIANTS, nargs="+", default=list(VARIANTS))
    parser.add_argument("--gradient-clips", type=float, nargs="+", default=[10.0])
    parser.add_argument(
        "--optimizer-modes", choices=("preserved", "reset"), nargs="+", default=["preserved"]
    )
    parser.add_argument("--learning-rates", type=float, nargs="+", default=[1e-4])
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = run(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(args.output.resolve()),
        "runtime_seconds": result["runtime_seconds"],
        "variants": {
            name: data["final_aggregate"] for name, data in result["variants"].items()
        },
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
