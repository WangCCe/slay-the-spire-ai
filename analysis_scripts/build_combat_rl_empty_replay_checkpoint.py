"""Build a no-update combat RL replay-collection checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path

import torch


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from spirecomm.ai.rl.v2.agent import RLAgentV2  # noqa: E402
from spirecomm.ai.rl.v2.id_mapping import build_id_mapper  # noqa: E402


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _state_dict_equal(left: dict, right: dict) -> bool:
    return list(left) == list(right) and all(
        torch.equal(left[name], right[name]) for name in left
    )


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
    if not math.isfinite(args.epsilon) or not 0.0 <= args.epsilon <= 1.0:
        raise ValueError("Epsilon must be finite and within [0, 1]")
    if args.learning_starts < RLAgentV2.CHECKPOINT_REPLAY_LIMIT:
        raise ValueError(
            f"Learning starts must be at least {RLAgentV2.CHECKPOINT_REPLAY_LIMIT}"
        )

    parent_path = args.parent_checkpoint.resolve()
    items_path = args.items_json.resolve()
    parent = torch.load(parent_path, map_location="cpu", weights_only=True)
    mapper = build_id_mapper(str(items_path))
    agent = RLAgentV2(
        model_path=str(parent_path),
        training=True,
        device="cpu",
        id_mapper=mapper,
    )
    agent.trainer.epsilon = float(args.epsilon)
    agent.trainer.learning_starts = int(args.learning_starts)
    agent.trainer.total_steps = 0
    agent.trainer.replay_buffer.clear()

    output = args.output.resolve()
    base = output.with_name(f".{output.stem}.base.pth")
    try:
        agent.save_model(str(base), episode=0)
        payload = torch.load(base, map_location="cpu", weights_only=True)
    finally:
        if base.exists():
            base.unlink()

    payload["provenance"] = {
        "construction": "parent_weights_with_empty_replay_for_collection",
        "source_commit": args.source_commit,
        "parent_checkpoint": str(parent_path),
        "parent_checkpoint_sha256": _sha256(parent_path),
        "items_json": str(items_path),
        "items_json_sha256": _sha256(items_path),
    }
    _atomic_torch_save(payload, output)
    loaded = torch.load(output, map_location="cpu", weights_only=True)

    replay = loaded["replay_buffer_state_dict"]
    checks = {
        "online_equals_parent": _state_dict_equal(
            loaded["online_network_state_dict"], parent["online_network_state_dict"]
        ),
        "target_equals_parent": _state_dict_equal(
            loaded["target_network_state_dict"], parent["online_network_state_dict"]
        ),
        "replay_is_empty": int(replay["transition_count"]) == 0,
        "optimizer_state_is_empty": not loaded["optimizer_state_dict"]["state"],
        "total_steps_is_zero": int(loaded["total_steps"]) == 0,
        "epsilon_matches": float(loaded["epsilon"]) == float(args.epsilon),
        "learning_starts_matches": int(loaded["learning_starts"])
        == int(args.learning_starts),
    }
    if not all(checks.values()):
        raise ValueError(f"Collection checkpoint validation failed: {checks}")

    manifest = {
        "schema_version": 1,
        "source_commit": args.source_commit,
        "inputs": payload["provenance"],
        "checkpoint": {
            "path": str(output),
            "sha256": _sha256(output),
            "size_bytes": output.stat().st_size,
            "checkpoint_schema_version": int(loaded["checkpoint_schema_version"]),
            "checkpoint_kind": loaded["checkpoint_kind"],
            "epsilon": float(loaded["epsilon"]),
            "learning_starts": int(loaded["learning_starts"]),
            "replay_transition_count": int(replay["transition_count"]),
            "total_steps": int(loaded["total_steps"]),
        },
        "validation": checks,
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent-checkpoint", type=Path, required=True)
    parser.add_argument("--items-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--epsilon", type=float, default=0.0)
    parser.add_argument(
        "--learning-starts", type=int, default=RLAgentV2.CHECKPOINT_REPLAY_LIMIT
    )
    return parser


def main() -> int:
    result = run(build_parser().parse_args())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
