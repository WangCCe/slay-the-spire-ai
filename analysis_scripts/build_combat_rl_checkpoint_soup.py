"""Build the selected combat RL checkpoint soup as a weights-only checkpoint."""

from __future__ import annotations

import argparse
import json
import os
from collections import OrderedDict
from pathlib import Path

import torch

from combat_rl_checkpoint_soup_diagnosis import _sha256


def _mean_state(states: list[dict[str, torch.Tensor]]) -> OrderedDict:
    names = list(states[0])
    if any(list(state) != names for state in states[1:]):
        raise ValueError("Online state keys or ordering differ across replicas")
    return OrderedDict(
        (name, torch.stack([state[name].float() for state in states]).mean(dim=0))
        for name in names
    )


def _load_verified_inputs(report: dict) -> dict[str, dict]:
    if report.get("selected_soup") != "replicate_mean":
        raise ValueError("Diagnosis did not select the equal-weight replicate mean")
    if "replicate_mean" not in report.get("eligible_soups", []):
        raise ValueError("Selected replicate mean is not eligible")

    inputs = report.get("inputs", {})
    if set(inputs) != {"entry", "r1", "r2", "r3"}:
        raise ValueError("Diagnosis must bind exactly entry, r1, r2, and r3")

    checkpoints = {}
    for name, binding in inputs.items():
        path = Path(binding["path"])
        actual_hash = _sha256(path)
        if actual_hash != binding["sha256"]:
            raise ValueError(
                f"Input hash mismatch for {name}: expected {binding['sha256']}, "
                f"got {actual_hash}"
            )
        checkpoints[name] = torch.load(path, map_location="cpu", weights_only=True)
    return checkpoints


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
    diagnosis_path = args.diagnosis_report.resolve()
    diagnosis_hash = _sha256(diagnosis_path)
    report = json.loads(diagnosis_path.read_text(encoding="utf-8"))
    checkpoints = _load_verified_inputs(report)

    entry_metadata = checkpoints["entry"]["metadata"]
    for name, checkpoint in checkpoints.items():
        if checkpoint["metadata"] != entry_metadata:
            raise ValueError(f"Metadata mismatch for {name}")

    online_state = _mean_state(
        [checkpoints[name]["online_network_state_dict"] for name in ("r1", "r2", "r3")]
    )
    payload = {
        "checkpoint_schema_version": 2,
        "checkpoint_kind": "weights",
        "metadata": entry_metadata,
        "rl_space_version": entry_metadata["rl_space_version"],
        "online_network_state_dict": online_state,
        "episode": 0,
        "provenance": {
            "construction": "equal_weight_mean",
            "source_commit": args.source_commit,
            "diagnosis_report": str(diagnosis_path),
            "diagnosis_report_sha256": diagnosis_hash,
            "component_sha256": {
                name: report["inputs"][name]["sha256"] for name in ("r1", "r2", "r3")
            },
        },
    }

    output = args.output.resolve()
    _atomic_torch_save(payload, output)
    loaded = torch.load(output, map_location="cpu", weights_only=True)
    if loaded["checkpoint_kind"] != "weights":
        raise ValueError("Written checkpoint kind did not round-trip")
    for name, expected in online_state.items():
        if not torch.equal(loaded["online_network_state_dict"][name], expected):
            raise ValueError(f"Written tensor did not round-trip: {name}")

    manifest = {
        "schema_version": 1,
        "source_commit": args.source_commit,
        "diagnosis_report": {
            "path": str(diagnosis_path),
            "sha256": diagnosis_hash,
            "selected_soup": report["selected_soup"],
        },
        "checkpoint": {
            "path": str(output),
            "sha256": _sha256(output),
            "size_bytes": output.stat().st_size,
            "checkpoint_schema_version": 2,
            "checkpoint_kind": "weights",
        },
        "components": {
            name: report["inputs"][name] for name in ("r1", "r2", "r3")
        },
        "training_state_inherited": False,
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diagnosis-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    return parser


def main() -> int:
    result = run(build_parser().parse_args())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
