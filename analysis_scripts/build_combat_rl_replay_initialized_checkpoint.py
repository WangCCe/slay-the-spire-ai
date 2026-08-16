"""Build a parent-policy training checkpoint with a bound replay snapshot."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path

import torch


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_torch_save(payload: dict, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.tmp")
    try:
        torch.save(payload, temporary)
        os.replace(temporary, output)
    finally:
        if temporary.exists():
            temporary.unlink()


def run(args: argparse.Namespace) -> dict:
    parent_path = args.parent_checkpoint.resolve()
    replay_path = args.replay_checkpoint.resolve()
    parent = torch.load(parent_path, map_location="cpu", weights_only=True)
    replay_source = torch.load(replay_path, map_location="cpu", weights_only=True)

    if (
        not math.isfinite(args.parent_policy_anchor_weight)
        or args.parent_policy_anchor_weight <= 0.0
    ):
        raise ValueError("Parent policy anchor weight must be finite and positive")
    if (
        not math.isfinite(args.parent_end_turn_imitation_weight)
        or args.parent_end_turn_imitation_weight < 0.0
    ):
        raise ValueError(
            "Parent-EndTurn imitation weight must be finite and non-negative"
        )

    if parent.get("metadata") != replay_source.get("metadata"):
        raise ValueError("Parent and replay checkpoint metadata differ")
    if "online_network_state_dict" not in parent:
        raise ValueError("Parent checkpoint has no online network state")
    replay = replay_source.get("replay_buffer_state_dict")
    if not isinstance(replay, dict) or int(replay.get("transition_count", 0)) < 1:
        raise ValueError("Replay checkpoint has no transitions")
    optimizer = copy.deepcopy(replay_source.get("optimizer_state_dict"))
    if not isinstance(optimizer, dict) or "param_groups" not in optimizer:
        raise ValueError("Replay checkpoint has no compatible optimizer layout")
    optimizer["state"] = {}

    parent_state = parent["online_network_state_dict"]
    payload = {
        "checkpoint_schema_version": 2,
        "checkpoint_kind": "training",
        "metadata": parent["metadata"],
        "rl_space_version": parent["metadata"]["rl_space_version"],
        "online_network_state_dict": parent_state,
        "target_network_state_dict": parent_state,
        "replay_buffer_state_dict": replay,
        "optimizer_state_dict": optimizer,
        "epsilon": float(replay_source.get("epsilon", 1.0)),
        "learning_starts": int(replay_source.get("learning_starts", 4096)),
        "total_steps": int(
            replay.get("source_transition_count", replay["transition_count"])
        ),
        "episode": 0,
        "parent_policy_anchor_weight": float(args.parent_policy_anchor_weight),
        "parent_policy_anchor_state_dict": parent_state,
        "positive_energy_action_imitation_weight": 0.0,
        "positive_energy_parent_end_turn_imitation_weight": float(
            args.parent_end_turn_imitation_weight
        ),
        "provenance": {
            "construction": "parent_weights_with_replay_and_fresh_optimizer",
            "source_commit": args.source_commit,
            "parent_checkpoint": str(parent_path),
            "parent_checkpoint_sha256": _sha256(parent_path),
            "replay_checkpoint": str(replay_path),
            "replay_checkpoint_sha256": _sha256(replay_path),
        },
    }

    output = args.output.resolve()
    _atomic_torch_save(payload, output)
    loaded = torch.load(output, map_location="cpu", weights_only=True)
    if loaded["optimizer_state_dict"]["state"]:
        raise ValueError("Fresh optimizer state did not round-trip empty")
    for name, expected in parent_state.items():
        if not torch.equal(loaded["online_network_state_dict"][name], expected):
            raise ValueError(f"Parent tensor did not round-trip: {name}")
        if not torch.equal(loaded["target_network_state_dict"][name], expected):
            raise ValueError(f"Target tensor did not round-trip: {name}")

    manifest = {
        "schema_version": 1,
        "source_commit": args.source_commit,
        "inputs": {
            "parent_checkpoint": payload["provenance"]["parent_checkpoint"],
            "parent_checkpoint_sha256": payload["provenance"][
                "parent_checkpoint_sha256"
            ],
            "replay_checkpoint": payload["provenance"]["replay_checkpoint"],
            "replay_checkpoint_sha256": payload["provenance"][
                "replay_checkpoint_sha256"
            ],
        },
        "checkpoint": {
            "path": str(output),
            "sha256": _sha256(output),
            "size_bytes": output.stat().st_size,
            "checkpoint_kind": "training",
            "episode": 0,
            "total_steps": payload["total_steps"],
            "learning_starts": payload["learning_starts"],
            "replay_transition_count": int(replay["transition_count"]),
            "replay_source_transition_count": int(
                replay.get("source_transition_count", replay["transition_count"])
            ),
            "optimizer_state_is_empty": True,
            "online_target_and_anchor_equal_parent": True,
            "positive_energy_parent_end_turn_imitation_weight": float(
                args.parent_end_turn_imitation_weight
            ),
        },
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent-checkpoint", type=Path, required=True)
    parser.add_argument("--replay-checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--parent-policy-anchor-weight", type=float, default=1.0)
    parser.add_argument(
        "--parent-end-turn-imitation-weight", type=float, required=True
    )
    return parser


def main() -> int:
    result = run(build_parser().parse_args())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
