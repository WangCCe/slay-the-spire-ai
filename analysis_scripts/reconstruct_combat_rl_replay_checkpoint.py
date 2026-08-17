"""Reconstruct a complete replay from overlapping chronological checkpoints."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import torch


TENSOR_FIELDS = (
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
)


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


def _reconstruct_replay(prefix: dict, suffix: dict) -> tuple[dict, dict]:
    prefix_replay = prefix["replay_buffer_state_dict"]
    suffix_replay = suffix["replay_buffer_state_dict"]
    metadata_fields = (
        "schema_version",
        "buffer_size",
        "continuous_dim",
        "action_dim",
        "card_slots",
        "potion_slots",
        "relic_slots",
    )
    for field in metadata_fields:
        if prefix_replay[field] != suffix_replay[field]:
            raise ValueError(f"Replay metadata mismatch: {field}")

    prefix_count = int(prefix_replay["transition_count"])
    suffix_count = int(suffix_replay["transition_count"])
    prefix_end = int(prefix["total_steps"])
    suffix_end = int(suffix["total_steps"])
    prefix_start = prefix_end - prefix_count
    suffix_start = suffix_end - suffix_count
    if prefix_start != 0:
        raise ValueError("Prefix checkpoint must begin at transition zero")
    if bool(prefix_replay.get("truncated", False)):
        raise ValueError("Prefix replay must not be truncated")
    if not 0 <= suffix_start <= prefix_end <= suffix_end:
        raise ValueError("Replay checkpoints do not form an overlapping timeline")

    overlap_count = prefix_end - suffix_start
    prefix_overlap_start = suffix_start - prefix_start
    for field in TENSOR_FIELDS:
        prefix_value = prefix_replay[field]
        suffix_value = suffix_replay[field]
        if int(prefix_value.shape[0]) != prefix_count:
            raise ValueError(f"Prefix replay field count mismatch: {field}")
        if int(suffix_value.shape[0]) != suffix_count:
            raise ValueError(f"Suffix replay field count mismatch: {field}")
        if not torch.equal(
            prefix_value[
                prefix_overlap_start : prefix_overlap_start + overlap_count
            ],
            suffix_value[:overlap_count],
        ):
            raise ValueError(f"Replay overlap mismatch: {field}")

    reconstructed = {
        field: prefix_replay[field] for field in metadata_fields
    }
    for field in TENSOR_FIELDS:
        reconstructed[field] = torch.cat(
            (prefix_replay[field], suffix_replay[field][overlap_count:]),
            dim=0,
        )
    reconstructed_count = int(reconstructed["actions"].shape[0])
    if reconstructed_count != suffix_end:
        raise ValueError(
            "Reconstructed replay count does not match terminal total steps"
        )
    reconstructed.update(
        {
            "transition_count": reconstructed_count,
            "source_transition_count": reconstructed_count,
            "truncated": False,
        }
    )
    return reconstructed, {
        "prefix_start": prefix_start,
        "prefix_end": prefix_end,
        "suffix_start": suffix_start,
        "suffix_end": suffix_end,
        "overlap_transition_count": overlap_count,
        "appended_transition_count": suffix_count - overlap_count,
        "reconstructed_transition_count": reconstructed_count,
        "all_tensor_overlaps_equal": True,
    }


def run(args: argparse.Namespace) -> dict:
    prefix_path = args.prefix_checkpoint.resolve()
    suffix_path = args.suffix_checkpoint.resolve()
    prefix = torch.load(prefix_path, map_location="cpu", weights_only=True)
    suffix = torch.load(suffix_path, map_location="cpu", weights_only=True)
    if prefix["metadata"] != suffix["metadata"]:
        raise ValueError("Checkpoint metadata differ")
    for field in ("online_network_state_dict", "target_network_state_dict"):
        if not _state_dict_equal(prefix[field], suffix[field]):
            raise ValueError(f"Checkpoint network mismatch: {field}")

    replay, reconstruction = _reconstruct_replay(prefix, suffix)
    payload = dict(suffix)
    payload["replay_buffer_state_dict"] = replay
    payload["replay_reconstruction_provenance"] = {
        "source_commit": args.source_commit,
        "prefix_checkpoint_sha256": _sha256(prefix_path),
        "suffix_checkpoint_sha256": _sha256(suffix_path),
        **reconstruction,
    }
    output = args.output.resolve()
    _atomic_torch_save(payload, output)
    loaded = torch.load(output, map_location="cpu", weights_only=True)
    loaded_replay = loaded["replay_buffer_state_dict"]
    if int(loaded_replay["transition_count"]) != reconstruction[
        "reconstructed_transition_count"
    ] or any(
        not torch.equal(loaded_replay[field], replay[field])
        for field in TENSOR_FIELDS
    ):
        raise ValueError("Reconstructed replay checkpoint did not round-trip")

    manifest = {
        "schema_version": 1,
        "source_commit": args.source_commit,
        "prefix_checkpoint": {
            "path": str(prefix_path),
            "sha256": _sha256(prefix_path),
            "size_bytes": prefix_path.stat().st_size,
        },
        "suffix_checkpoint": {
            "path": str(suffix_path),
            "sha256": _sha256(suffix_path),
            "size_bytes": suffix_path.stat().st_size,
        },
        "output_checkpoint": {
            "path": str(output),
            "sha256": _sha256(output),
            "size_bytes": output.stat().st_size,
        },
        "reconstruction": reconstruction,
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix-checkpoint", type=Path, required=True)
    parser.add_argument("--suffix-checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    return parser


def main() -> int:
    print(json.dumps(run(build_parser().parse_args()), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
