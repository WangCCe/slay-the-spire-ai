"""Package one confirmed LightSTS combat policy as isolated RL v2 weights."""

from __future__ import annotations

import argparse
import copy
import io
import json
import re
import shutil
import sys
import uuid
from pathlib import Path
from typing import Any, Mapping, Sequence

import torch


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from analysis_scripts.combat_lightspeed_bridge import (  # noqa: E402
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
)
from analysis_scripts.combat_lightspeed_production_shadow import (  # noqa: E402
    load_production_checkpoint,
    prove_reload_equivalence,
)
from analysis_scripts.combat_lightspeed_training_smoke import (  # noqa: E402
    parameter_sha256,
)
from spirecomm.ai.rl.checkpoint_io import save_torch_checkpoint  # noqa: E402
from spirecomm.ai.rl.v2.id_mapping import (  # noqa: E402
    IdMapper,
    build_id_mapper_from_payload,
)


REPORT_SCHEMA_VERSION = "combat-lightspeed-production-candidate-packaging-v1"
MANIFEST_SCHEMA_VERSION = (
    "combat-lightspeed-production-candidate-packaging-manifest-v1"
)
SIMULATOR_CHECKPOINT_KIND = "simulator_training_smoke"
SIMULATOR_SOURCE_TYPE = "sts_lightspeed_combat_simulation"
PACKAGED_FILENAME = "rl_combat_model_lightspeed_candidate.pth"
CONVERTER_AUTHORITY = {
    "communication_mod": False,
    "evaluation": False,
    "formal_rl": False,
    "gameplay": False,
    "model_fitting": False,
    "packaging": True,
    "production_checkpoint_read": True,
    "production_replacement": False,
    "promotion": False,
    "qualification": False,
    "training": False,
}


def _validate_sha256(value: str, *, label: str) -> str:
    normalized = str(value).lower()
    if not re.fullmatch(r"[0-9a-f]{64}", normalized):
        raise ValueError(f"{label} must be a 64-character SHA-256")
    return normalized


def _load_checkpoint_bytes(payload: bytes) -> Any:
    stream = io.BytesIO(payload)
    try:
        return torch.load(stream, map_location="cpu", weights_only=True)
    except TypeError as exc:
        if "weights_only" not in str(exc):
            raise
        stream.seek(0)
        return torch.load(stream, map_location="cpu")


def _clone_candidate_state(
    state: Mapping[str, torch.Tensor],
) -> dict[str, torch.Tensor]:
    if not state:
        raise ValueError("candidate checkpoint online state is missing or empty")
    cloned: dict[str, torch.Tensor] = {}
    for name, value in state.items():
        if not isinstance(name, str) or not isinstance(value, torch.Tensor):
            raise ValueError("candidate checkpoint online state contains non-tensor values")
        tensor = value.detach().cpu().clone()
        if not bool(torch.isfinite(tensor).all()):
            raise ValueError(f"candidate checkpoint tensor is not finite: {name}")
        cloned[name] = tensor
    return cloned


def _structure_evidence(
    candidate: Mapping[str, torch.Tensor],
    production: Mapping[str, torch.Tensor],
) -> dict[str, Any]:
    candidate_keys = set(candidate)
    production_keys = set(production)
    shared = sorted(candidate_keys & production_keys)
    shape_mismatches = {
        name: [list(candidate[name].shape), list(production[name].shape)]
        for name in shared
        if candidate[name].shape != production[name].shape
    }
    dtype_mismatches = {
        name: [str(candidate[name].dtype), str(production[name].dtype)]
        for name in shared
        if candidate[name].dtype != production[name].dtype
    }
    passed = (
        candidate_keys == production_keys
        and not shape_mismatches
        and not dtype_mismatches
    )
    return {
        "keys_match": candidate_keys == production_keys,
        "missing_from_candidate": sorted(production_keys - candidate_keys),
        "unexpected_in_candidate": sorted(candidate_keys - production_keys),
        "shape_mismatches": shape_mismatches,
        "dtype_mismatches": dtype_mismatches,
        "passed": passed,
    }


def load_simulator_candidate(
    path: Path,
    *,
    expected_sha256: str,
) -> dict[str, Any]:
    resolved = path.resolve()
    if not resolved.is_file():
        raise ValueError(f"candidate checkpoint does not exist: {resolved}")
    expected_hash = _validate_sha256(
        expected_sha256,
        label="expected candidate checkpoint hash",
    )
    checkpoint_bytes = resolved.read_bytes()
    actual_hash = sha256_bytes(checkpoint_bytes)
    if actual_hash != expected_hash:
        raise ValueError(
            "candidate checkpoint hash mismatch: "
            f"expected {expected_hash}, got {actual_hash}"
        )
    checkpoint = _load_checkpoint_bytes(checkpoint_bytes)
    if not isinstance(checkpoint, Mapping):
        raise ValueError("candidate checkpoint root must be a mapping")
    if checkpoint.get("checkpoint_schema_version") != 0:
        raise ValueError("candidate checkpoint schema version must be 0")
    if checkpoint.get("checkpoint_kind") != SIMULATOR_CHECKPOINT_KIND:
        raise ValueError("candidate checkpoint kind must be simulator_training_smoke")
    if checkpoint.get("source_type") != SIMULATOR_SOURCE_TYPE:
        raise ValueError("candidate checkpoint source type is not a training result")
    if checkpoint.get("production_compatible") is not False:
        raise ValueError("candidate checkpoint must not be production-compatible")
    raw_state = checkpoint.get("online_network_state_dict")
    if not isinstance(raw_state, Mapping):
        raise ValueError("candidate checkpoint online state is missing or empty")
    state = _clone_candidate_state(raw_state)
    candidate_parameter_hash = parameter_sha256(state)
    metadata = checkpoint.get("metadata")
    if not isinstance(metadata, Mapping):
        raise ValueError("candidate checkpoint metadata is missing")
    source_binding = metadata.get("source_binding")
    if not isinstance(source_binding, Mapping):
        raise ValueError("candidate checkpoint source binding is missing")
    bound_parameter_hash = source_binding.get("candidate_parameter_sha256")
    if bound_parameter_hash != candidate_parameter_hash:
        raise ValueError(
            "candidate parameter binding mismatch: "
            f"expected {candidate_parameter_hash}, got {bound_parameter_hash}"
        )
    return {
        "path": str(resolved),
        "checkpoint_sha256": actual_hash,
        "size_bytes": len(checkpoint_bytes),
        "checkpoint_schema_version": 0,
        "checkpoint_kind": SIMULATOR_CHECKPOINT_KIND,
        "source_type": SIMULATOR_SOURCE_TYPE,
        "production_compatible": False,
        "parameter_sha256": candidate_parameter_hash,
        "parameter_count": sum(int(value.numel()) for value in state.values()),
        "state_dict": state,
        "source_binding": copy.deepcopy(dict(source_binding)),
    }


def load_confirmation_report(
    path: Path,
    *,
    expected_sha256: str,
    candidate_sha256: str,
) -> dict[str, Any]:
    resolved = path.resolve()
    if not resolved.is_file():
        raise ValueError(f"confirmation report does not exist: {resolved}")
    expected_hash = _validate_sha256(
        expected_sha256,
        label="expected confirmation report hash",
    )
    report_bytes = resolved.read_bytes()
    actual_hash = sha256_bytes(report_bytes)
    if actual_hash != expected_hash:
        raise ValueError(
            "confirmation report hash mismatch: "
            f"expected {expected_hash}, got {actual_hash}"
        )
    try:
        report = json.loads(report_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"confirmation report is invalid JSON: {exc}") from exc
    if not isinstance(report, Mapping):
        raise ValueError("confirmation report root must be an object")
    candidates = report.get("candidates")
    if not isinstance(candidates, list) or not any(
        isinstance(row, Mapping) and row.get("sha256") == candidate_sha256
        for row in candidates
    ):
        raise ValueError(
            "confirmation report does not bind the simulator candidate hash"
        )
    return {
        "path": str(resolved),
        "sha256": actual_hash,
        "size_bytes": len(report_bytes),
        "schema_version": report.get("schema_version"),
    }


def _load_items(
    path: Path,
    *,
    expected_sha256: str,
) -> tuple[IdMapper, dict[str, Any]]:
    resolved = path.resolve()
    if not resolved.is_file():
        raise ValueError(f"items JSON does not exist: {resolved}")
    expected_hash = _validate_sha256(expected_sha256, label="expected items hash")
    items_bytes = resolved.read_bytes()
    actual_hash = sha256_bytes(items_bytes)
    if actual_hash != expected_hash:
        raise ValueError(
            f"items JSON hash mismatch: expected {expected_hash}, got {actual_hash}"
        )
    try:
        payload = json.loads(items_bytes.decode("utf-8"))
        if not isinstance(payload, Mapping):
            raise TypeError("items JSON root is not an object")
        mapper = build_id_mapper_from_payload(payload)
    except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"items JSON is invalid: {exc}") from exc
    return mapper, {
        "path": str(resolved),
        "sha256": actual_hash,
        "size_bytes": len(items_bytes),
        "card_vocab": mapper.card_vocab_size,
        "potion_vocab": mapper.potion_vocab_size,
        "relic_vocab": mapper.relic_vocab_size,
    }


def _summary_markdown(report: Mapping[str, Any]) -> str:
    packaged = report["packaged_checkpoint"]
    equivalence = report["equivalence"]
    return "\n".join(
        (
            "# LightSTS production candidate packaging",
            "",
            f"- Verdict: `{report['verdict']}`",
            f"- Candidate checkpoint SHA-256: `{report['simulator_candidate']['checkpoint_sha256']}`",
            f"- Candidate parameter SHA-256: `{report['simulator_candidate']['parameter_sha256']}`",
            f"- Packaged checkpoint SHA-256: `{packaged['checkpoint_sha256']}`",
            f"- Packaged parameter SHA-256: `{packaged['parameter_sha256']}`",
            f"- Parameter count: `{packaged['parameter_count']}`",
            f"- Probe count: `{equivalence['probe_count']}`",
            f"- Maximum valid-action Q delta: `{equivalence['max_abs_q_delta']}`",
            f"- Action mismatches: `{equivalence['action_mismatch_count']}`",
            "- Production compatible weights file: `true`",
            "- Production replacement, gameplay, qualification, and promotion: `false`",
            "",
        )
    )


def publish_production_candidate(
    output_dir: Path,
    *,
    simulator_candidate: Path,
    expected_candidate_sha256: str,
    production_parent: Path,
    expected_parent_sha256: str,
    items_json: Path,
    expected_items_sha256: str,
    confirmation_report: Path,
    expected_confirmation_sha256: str,
    source_commit: str,
    probe_count: int = 32,
) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", source_commit):
        raise ValueError("source commit must be a lowercase 40- or 64-hex identity")
    if probe_count <= 0:
        raise ValueError("probe count must be positive")
    target = output_dir.resolve()
    if target.exists():
        raise FileExistsError(f"packaging output already exists: {target}")

    mapper, items = _load_items(items_json, expected_sha256=expected_items_sha256)
    parent = load_production_checkpoint(
        production_parent,
        expected_sha256=expected_parent_sha256,
        id_mapper=mapper,
    )
    candidate = load_simulator_candidate(
        simulator_candidate,
        expected_sha256=expected_candidate_sha256,
    )
    confirmation = load_confirmation_report(
        confirmation_report,
        expected_sha256=expected_confirmation_sha256,
        candidate_sha256=candidate["checkpoint_sha256"],
    )
    structure = _structure_evidence(candidate["state_dict"], parent["state_dict"])
    if not structure["passed"]:
        raise ValueError(f"candidate structure mismatch: {structure}")

    converter_path = Path(__file__).resolve()
    converter_sha256 = sha256_bytes(converter_path.read_bytes())
    provenance = {
        "construction": "exact_lightspeed_candidate_production_packaging",
        "source_commit": source_commit,
        "converter_path": str(converter_path),
        "converter_sha256": converter_sha256,
        "simulator_candidate_checkpoint_sha256": candidate["checkpoint_sha256"],
        "simulator_candidate_parameter_sha256": candidate["parameter_sha256"],
        "production_parent_checkpoint_sha256": parent["checkpoint_sha256"],
        "production_parent_parameter_sha256": parent["parameter_sha256"],
        "items_json_sha256": items["sha256"],
        "confirmation_report_sha256": confirmation["sha256"],
    }
    payload = {
        "checkpoint_schema_version": 2,
        "checkpoint_kind": "weights",
        "metadata": copy.deepcopy(parent["metadata"]),
        "rl_space_version": "v2",
        "online_network_state_dict": _clone_candidate_state(candidate["state_dict"]),
        "episode": 0,
        "provenance": provenance,
    }

    staging = target.with_name(f".{target.name}.{uuid.uuid4().hex}.staging")
    staging_created = False
    try:
        staging.mkdir(parents=True, exist_ok=False)
        staging_created = True
        packaged_path = staging / PACKAGED_FILENAME
        save_torch_checkpoint(payload, str(packaged_path))
        packaged_hash = sha256_file(packaged_path)
        reloaded = load_production_checkpoint(
            packaged_path,
            expected_sha256=packaged_hash,
            id_mapper=mapper,
        )
        equivalence = prove_reload_equivalence(
            mapper,
            candidate["state_dict"],
            reloaded["state_dict"],
            probe_count=probe_count,
            tolerance=0.0,
        )
        if not equivalence["passed"]:
            raise ValueError(f"packaged checkpoint equivalence failed: {equivalence}")

        packaged = {
            "path": PACKAGED_FILENAME,
            "checkpoint_sha256": packaged_hash,
            "size_bytes": packaged_path.stat().st_size,
            "checkpoint_schema_version": 2,
            "checkpoint_kind": "weights",
            "rl_space_version": "v2",
            "parameter_sha256": reloaded["parameter_sha256"],
            "parameter_count": reloaded["parameter_count"],
            "production_loadable": True,
        }
        report = {
            "schema_version": REPORT_SCHEMA_VERSION,
            "source_commit": source_commit,
            "authority": dict(CONVERTER_AUTHORITY),
            "converter": {
                "path": str(converter_path),
                "sha256": converter_sha256,
            },
            "items": items,
            "confirmation": confirmation,
            "production_parent": {
                key: parent[key]
                for key in (
                    "path",
                    "checkpoint_sha256",
                    "size_bytes",
                    "checkpoint_schema_version",
                    "checkpoint_kind",
                    "rl_space_version",
                    "metadata",
                    "parameter_sha256",
                    "parameter_count",
                )
            },
            "simulator_candidate": {
                key: candidate[key]
                for key in (
                    "path",
                    "checkpoint_sha256",
                    "size_bytes",
                    "checkpoint_schema_version",
                    "checkpoint_kind",
                    "source_type",
                    "production_compatible",
                    "parameter_sha256",
                    "parameter_count",
                    "source_binding",
                )
            },
            "structure": structure,
            "packaged_checkpoint": packaged,
            "equivalence": equivalence,
            "production_state_unchanged": True,
            "verdict": "production_candidate_packaging_ready",
        }
        report_bytes = canonical_json_bytes(report) + b"\n"
        summary_bytes = _summary_markdown(report).encode("utf-8")
        (staging / "report.json").write_bytes(report_bytes)
        (staging / "summary.md").write_bytes(summary_bytes)
        artifacts = {}
        for name in (PACKAGED_FILENAME, "report.json", "summary.md"):
            artifact_path = staging / name
            artifacts[name] = {
                "sha256": sha256_file(artifact_path),
                "size_bytes": artifact_path.stat().st_size,
            }
        manifest = {
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "artifacts": artifacts,
        }
        (staging / "manifest.json").write_bytes(
            canonical_json_bytes(manifest) + b"\n"
        )
        for name, binding in artifacts.items():
            artifact_path = staging / name
            if (
                sha256_file(artifact_path) != binding["sha256"]
                or artifact_path.stat().st_size != binding["size_bytes"]
            ):
                raise ValueError(f"staged artifact changed before publication: {name}")
        staging.rename(target)
        staging_created = False
    except Exception:
        if staging_created and staging.exists():
            shutil.rmtree(staging)
        raise
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simulator-candidate", type=Path, required=True)
    parser.add_argument("--expected-candidate-sha256", required=True)
    parser.add_argument("--production-parent", type=Path, required=True)
    parser.add_argument("--expected-parent-sha256", required=True)
    parser.add_argument("--items-json", type=Path, required=True)
    parser.add_argument("--expected-items-sha256", required=True)
    parser.add_argument("--confirmation-report", type=Path, required=True)
    parser.add_argument("--expected-confirmation-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--probe-count", type=int, default=32)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = publish_production_candidate(
        args.output_dir,
        simulator_candidate=args.simulator_candidate,
        expected_candidate_sha256=args.expected_candidate_sha256,
        production_parent=args.production_parent,
        expected_parent_sha256=args.expected_parent_sha256,
        items_json=args.items_json,
        expected_items_sha256=args.expected_items_sha256,
        confirmation_report=args.confirmation_report,
        expected_confirmation_sha256=args.expected_confirmation_sha256,
        source_commit=args.source_commit,
        probe_count=args.probe_count,
    )
    print(
        json.dumps(
            {
                "output_dir": str(args.output_dir.resolve()),
                "verdict": report["verdict"],
                "checkpoint_sha256": report["packaged_checkpoint"][
                    "checkpoint_sha256"
                ],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
