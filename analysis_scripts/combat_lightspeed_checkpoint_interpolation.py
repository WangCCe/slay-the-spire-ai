"""Construct bound simulator-only checkpoints along a frozen parameter direction."""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

import torch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from analysis_scripts.combat_lightspeed_bridge import (  # noqa: E402
    SOURCE_TYPE,
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
)
from analysis_scripts.combat_lightspeed_frozen_candidate_comparison import (  # noqa: E402
    CHECKPOINT_KIND,
    CandidateBinding,
    load_candidate,
    validate_candidate_structures,
)
from analysis_scripts.combat_lightspeed_training_smoke import (  # noqa: E402
    parameter_sha256,
)
from spirecomm.ai.rl.checkpoint_io import save_torch_checkpoint  # noqa: E402


REPORT_SCHEMA_VERSION = "combat-lightspeed-checkpoint-interpolation-v1"
REPORT_AUTHORITY = {
    "communication_mod": False,
    "formal_rl": False,
    "gameplay": False,
    "live_policy_quality": False,
    "mechanics_equivalence": False,
    "model_fitting": False,
    "production_checkpoint_access": False,
    "promotion": False,
    "qualification": False,
    "simulator_candidate_construction": True,
    "training": False,
    "transfer": False,
}


def validate_alphas(alphas: Sequence[float]) -> tuple[float, ...]:
    values = tuple(float(value) for value in alphas)
    if not values:
        raise ValueError("at least one interpolation alpha is required")
    if any(not math.isfinite(value) or not 0.0 < value < 1.0 for value in values):
        raise ValueError("every interpolation alpha must be finite and inside (0, 1)")
    if len(set(values)) != len(values):
        raise ValueError("interpolation alpha values must be unique")
    return tuple(sorted(values))


def interpolate_state(
    parent: Mapping[str, torch.Tensor],
    candidate: Mapping[str, torch.Tensor],
    alpha: float,
) -> dict[str, torch.Tensor]:
    value = validate_alphas((alpha,))[0]
    if tuple(parent) != tuple(candidate):
        raise ValueError("checkpoint state structure keys differ")
    result = {}
    for key in parent:
        left = parent[key]
        right = candidate[key]
        if not isinstance(left, torch.Tensor) or not isinstance(right, torch.Tensor):
            raise ValueError("checkpoint state structure contains a non-tensor value")
        if left.shape != right.shape or left.dtype != right.dtype:
            raise ValueError(f"checkpoint state structure differs at {key}")
        if not left.is_floating_point() or not right.is_floating_point():
            raise ValueError(f"checkpoint state tensor must be floating point: {key}")
        left_cpu = left.detach().cpu()
        right_cpu = right.detach().cpu()
        if not bool(torch.isfinite(left_cpu).all()) or not bool(
            torch.isfinite(right_cpu).all()
        ):
            raise ValueError(f"checkpoint state tensor must be finite: {key}")
        interpolated = left_cpu + value * (right_cpu - left_cpu)
        if not bool(torch.isfinite(interpolated).all()):
            raise ValueError(f"interpolated checkpoint tensor is not finite: {key}")
        result[str(key)] = interpolated.to(dtype=left_cpu.dtype)
    if not result:
        raise ValueError("checkpoint state structure is empty")
    return result


def _alpha_label(alpha: float) -> str:
    return format(alpha, ".12g").replace("-", "m").replace(".", "p")


def _input_record(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: candidate[key]
        for key in (
            "label",
            "path",
            "sha256",
            "size_bytes",
            "checkpoint_schema_version",
            "checkpoint_kind",
            "source_type",
            "production_compatible",
        )
    } | {"parameter_sha256": parameter_sha256(candidate["state_dict"])}


def publish_interpolations(
    output_dir: Path,
    *,
    parent_binding: CandidateBinding,
    candidate_binding: CandidateBinding,
    alphas: Sequence[float],
    source_commit: str,
) -> dict[str, Any]:
    values = validate_alphas(alphas)
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", source_commit):
        raise ValueError("source commit must be a lowercase 40- or 64-hex identity")
    parent = load_candidate(parent_binding)
    candidate = load_candidate(candidate_binding)
    validate_candidate_structures((parent, candidate))
    parent_state = parent["state_dict"]
    candidate_state = candidate["state_dict"]
    states = {
        alpha: interpolate_state(parent_state, candidate_state, alpha)
        for alpha in values
    }

    target = output_dir.resolve()
    if target.exists():
        raise FileExistsError(f"interpolation output already exists: {target}")
    staging = target.with_name(f".{target.name}.staging")
    if staging.exists():
        raise FileExistsError(f"interpolation staging output already exists: {staging}")

    parent_record = _input_record(parent)
    candidate_record = _input_record(candidate)
    outputs = []
    try:
        staging.mkdir(parents=True, exist_ok=False)
        for alpha, state in states.items():
            parameter_hash = parameter_sha256(state)
            filename = f"simulator_only_candidate_alpha_{_alpha_label(alpha)}.pth"
            path = staging / filename
            source_binding = {
                "construction": "linear_parent_candidate_interpolation",
                "alpha": alpha,
                "source_commit": source_commit,
                "parent_checkpoint_sha256": parent_record["sha256"],
                "candidate_checkpoint_sha256": candidate_record["sha256"],
                "parent_parameter_sha256": parent_record["parameter_sha256"],
                "candidate_parameter_sha256": candidate_record["parameter_sha256"],
                "candidate_parameter_output_sha256": parameter_hash,
            }
            save_torch_checkpoint(
                {
                    "checkpoint_schema_version": 0,
                    "checkpoint_kind": CHECKPOINT_KIND,
                    "source_type": SOURCE_TYPE,
                    "production_compatible": False,
                    "online_network_state_dict": state,
                    "metadata": {
                        "authority": dict(REPORT_AUTHORITY),
                        "source_binding": source_binding,
                    },
                },
                str(path),
            )
            outputs.append(
                {
                    "alpha": alpha,
                    "path": filename,
                    "sha256": sha256_file(path),
                    "size_bytes": path.stat().st_size,
                    "parameter_sha256": parameter_hash,
                    "checkpoint_kind": CHECKPOINT_KIND,
                    "production_compatible": False,
                }
            )

        report = {
            "schema_version": REPORT_SCHEMA_VERSION,
            "source_type": SOURCE_TYPE,
            "source_commit": source_commit,
            "authority": dict(REPORT_AUTHORITY),
            "inputs": {
                "parent": parent_record,
                "candidate": candidate_record,
            },
            "alphas": list(values),
            "outputs": outputs,
            "selection": {
                "performed": False,
                "requires_separate_frozen_comparison": True,
            },
            "verdict": "interpolations_ready",
        }
        report_bytes = canonical_json_bytes(report) + b"\n"
        (staging / "report.json").write_bytes(report_bytes)
        artifacts = {
            "report.json": {
                "sha256": sha256_bytes(report_bytes),
                "size_bytes": len(report_bytes),
            }
        }
        artifacts.update(
            {
                row["path"]: {
                    "sha256": row["sha256"],
                    "size_bytes": row["size_bytes"],
                }
                for row in outputs
            }
        )
        manifest = {
            "schema_version": "combat-lightspeed-checkpoint-interpolation-manifest-v1",
            "artifacts": artifacts,
        }
        (staging / "manifest.json").write_bytes(
            canonical_json_bytes(manifest) + b"\n"
        )
        staging.replace(target)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    return report


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent-checkpoint", required=True, type=Path)
    parser.add_argument("--parent-sha256", required=True)
    parser.add_argument("--candidate-checkpoint", required=True, type=Path)
    parser.add_argument("--candidate-sha256", required=True)
    parser.add_argument("--alpha", action="append", required=True, type=float)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    report = publish_interpolations(
        args.output_dir,
        parent_binding=CandidateBinding(
            "parent", args.parent_checkpoint, args.parent_sha256.lower()
        ),
        candidate_binding=CandidateBinding(
            "candidate", args.candidate_checkpoint, args.candidate_sha256.lower()
        ),
        alphas=args.alpha,
        source_commit=args.source_commit.lower(),
    )
    print(
        json.dumps(
            {
                "output_dir": str(args.output_dir.resolve()),
                "verdict": report["verdict"],
                "outputs": report["outputs"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

