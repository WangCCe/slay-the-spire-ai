"""Evaluate aligned combat RL checkpoint averages on independent replay panels."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import OrderedDict
from pathlib import Path

import torch
import torch.nn.functional as F

from combat_rl_dropout_update_ablation import _batch, _make_network


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _mean_state(states: list[dict[str, torch.Tensor]]) -> OrderedDict:
    return OrderedDict(
        (name, torch.stack([state[name].float() for state in states]).mean(dim=0))
        for name in states[0]
    )


def _interpolate_state(
    entry: dict[str, torch.Tensor], target: dict[str, torch.Tensor], alpha: float
) -> OrderedDict:
    return OrderedDict(
        (name, entry[name].float() + alpha * (target[name].float() - entry[name].float()))
        for name in entry
    )


def _relative_l2(state: dict[str, torch.Tensor], entry: dict[str, torch.Tensor]) -> float:
    delta_squared = 0.0
    entry_squared = 0.0
    for name, value in state.items():
        reference = entry[name].float()
        delta_squared += float(torch.sum((value.float() - reference) ** 2))
        entry_squared += float(torch.sum(reference**2))
    return math.sqrt(delta_squared) / max(math.sqrt(entry_squared), 1e-12)


def _quantile(values: torch.Tensor, probability: float) -> float:
    finite = values.detach().float().reshape(-1)
    finite = finite[torch.isfinite(finite)]
    return float(torch.quantile(finite, probability)) if finite.numel() else math.nan


def _evaluate(
    metadata: dict,
    online_state: dict[str, torch.Tensor],
    target_state: dict[str, torch.Tensor],
    replay: dict,
    entry_actions: torch.Tensor,
) -> dict:
    online = _make_network(metadata, online_state)
    target = _make_network(metadata, target_state)
    online.eval()
    target.eval()
    indices = torch.arange(int(replay["transition_count"]))
    rows = torch.arange(indices.numel())
    with torch.no_grad():
        q_values = online(*_batch(replay, indices))
        next_online_q = online(*_batch(replay, indices, "next_"))
        next_actions = next_online_q.argmax(dim=1)
        next_q = target(*_batch(replay, indices, "next_"))[rows, next_actions]
        dones = replay["dones"][indices].bool()
        next_q = torch.where(dones, torch.zeros_like(next_q), next_q)
        actions = replay["actions"][indices].long()
        selected_q = q_values[rows, actions]
        targets = replay["rewards"][indices].float() + (~dones).float() * 0.99 * next_q
        absolute_td = (targets - selected_q).abs()
        greedy_actions = q_values.argmax(dim=1)
        top_two = torch.topk(q_values, k=2, dim=1).values
        margins = top_two[:, 0] - top_two[:, 1]
    return {
        "smooth_l1": float(F.smooth_l1_loss(selected_q, targets)),
        "absolute_td_p50": _quantile(absolute_td, 0.50),
        "absolute_td_p95": _quantile(absolute_td, 0.95),
        "q_margin_p50": _quantile(margins, 0.50),
        "q_margin_p05": _quantile(margins, 0.05),
        "entry_action_agreement": float((greedy_actions == entry_actions).float().mean()),
        "executed_action_greedy_share": float((greedy_actions == actions).float().mean()),
    }


def run(args: argparse.Namespace) -> dict:
    paths = {"entry": args.entry_checkpoint.resolve()}
    for index, path in enumerate(args.replicate_checkpoints, start=1):
        paths[f"r{index}"] = path.resolve()
    checkpoints = {
        name: torch.load(path, map_location="cpu", weights_only=True)
        for name, path in paths.items()
    }
    entry = checkpoints["entry"]
    metadata = entry["metadata"]
    for name, checkpoint in checkpoints.items():
        if checkpoint["metadata"] != metadata:
            raise ValueError(f"Metadata mismatch for {name}: {paths[name]}")
        if checkpoint["online_network_state_dict"].keys() != entry[
            "online_network_state_dict"
        ].keys():
            raise ValueError(f"Online state keys mismatch for {name}")
        if checkpoint["target_network_state_dict"].keys() != entry[
            "target_network_state_dict"
        ].keys():
            raise ValueError(f"Target state keys mismatch for {name}")

    replicate_names = [name for name in checkpoints if name != "entry"]
    mean_online = _mean_state(
        [checkpoints[name]["online_network_state_dict"] for name in replicate_names]
    )
    mean_target = _mean_state(
        [checkpoints[name]["target_network_state_dict"] for name in replicate_names]
    )
    candidates = {
        name: (
            checkpoint["online_network_state_dict"],
            checkpoint["target_network_state_dict"],
        )
        for name, checkpoint in checkpoints.items()
    }
    candidates["replicate_mean"] = (mean_online, mean_target)
    for alpha in (0.25, 0.50, 0.75):
        candidates[f"entry_to_mean_{alpha:.2f}"] = (
            _interpolate_state(entry["online_network_state_dict"], mean_online, alpha),
            _interpolate_state(entry["target_network_state_dict"], mean_target, alpha),
        )

    panels = {
        name: checkpoints[name]["replay_buffer_state_dict"] for name in replicate_names
    }
    entry_actions = {}
    entry_network = _make_network(metadata, entry["online_network_state_dict"])
    entry_network.eval()
    with torch.no_grad():
        for panel_name, replay in panels.items():
            indices = torch.arange(int(replay["transition_count"]))
            entry_actions[panel_name] = entry_network(*_batch(replay, indices)).argmax(dim=1)

    evaluations = {}
    for candidate_name, (online_state, target_state) in candidates.items():
        evaluations[candidate_name] = {
            panel_name: _evaluate(
                metadata,
                online_state,
                target_state,
                replay,
                entry_actions[panel_name],
            )
            for panel_name, replay in panels.items()
        }

    entry_drift = entry["online_network_state_dict"]
    maximum_replicate_drift = max(
        _relative_l2(candidates[name][0], entry_drift) for name in replicate_names
    )
    summaries = {}
    for candidate_name, panel_results in evaluations.items():
        losses = [result["smooth_l1"] for result in panel_results.values()]
        normalized_losses = [
            result["smooth_l1"] / evaluations["entry"][panel_name]["smooth_l1"]
            for panel_name, result in panel_results.items()
        ]
        margin_ratios = [
            result["q_margin_p50"]
            / max(evaluations["entry"][panel_name]["q_margin_p50"], 1e-12)
            for panel_name, result in panel_results.items()
        ]
        drift = _relative_l2(candidates[candidate_name][0], entry_drift)
        summaries[candidate_name] = {
            "mean_smooth_l1": sum(losses) / len(losses),
            "mean_normalized_smooth_l1": sum(normalized_losses) / len(normalized_losses),
            "worst_normalized_smooth_l1": max(normalized_losses),
            "minimum_q_margin_p50_ratio_to_entry": min(margin_ratios),
            "relative_l2_from_entry": drift,
            "all_panels_loss_below_entry": all(value < 1.0 for value in normalized_losses),
            "all_panels_margin_at_least_75pct_entry": all(
                value >= 0.75 for value in margin_ratios
            ),
            "drift_no_greater_than_maximum_replicate": drift <= maximum_replicate_drift,
        }

    soup_names = [name for name in candidates if name not in checkpoints]
    eligible = [
        name
        for name in soup_names
        if summaries[name]["all_panels_loss_below_entry"]
        and summaries[name]["all_panels_margin_at_least_75pct_entry"]
        and summaries[name]["drift_no_greater_than_maximum_replicate"]
    ]
    selected = min(
        eligible,
        key=lambda name: summaries[name]["mean_normalized_smooth_l1"],
        default=None,
    )
    return {
        "schema_version": 1,
        "source_commit": args.source_commit,
        "inputs": {
            name: {"path": str(path), "sha256": _sha256(path)}
            for name, path in paths.items()
        },
        "design": {
            "device": "cpu",
            "replicate_names": replicate_names,
            "panel_transition_counts": {
                name: int(replay["transition_count"]) for name, replay in panels.items()
            },
            "candidates": list(candidates),
            "selection_requirements": {
                "all_panels_loss_below_entry": True,
                "all_panels_margin_at_least_75pct_entry": True,
                "drift_no_greater_than_maximum_replicate": True,
                "ranking": "minimum mean normalized Smooth-L1 loss",
            },
        },
        "evaluations": evaluations,
        "summaries": summaries,
        "eligible_soups": eligible,
        "selected_soup": selected,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entry-checkpoint", type=Path, required=True)
    parser.add_argument("--replicate-checkpoints", type=Path, nargs=3, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = run(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(args.output.resolve()),
                "eligible_soups": result["eligible_soups"],
                "selected_soup": result["selected_soup"],
                "summaries": result["summaries"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
