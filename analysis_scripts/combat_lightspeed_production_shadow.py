"""Export an exact production RL v2 policy as a simulator-only parent."""

from __future__ import annotations

import argparse
import copy
import io
import json
import math
import re
import shutil
import sys
import uuid
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import torch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from analysis_scripts.combat_lightspeed_bridge import (  # noqa: E402
    ACTION_DIM,
    CARD_SLOTS,
    CONTINUOUS_DIM,
    POTION_SLOTS,
    RELIC_SLOTS,
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
)
from analysis_scripts.combat_lightspeed_training_smoke import (  # noqa: E402
    create_fresh_trainer,
    parameter_sha256,
)
from spirecomm.ai.rl.checkpoint_io import (  # noqa: E402
    load_torch_checkpoint,
    save_torch_checkpoint,
)
from spirecomm.ai.rl.v2.id_mapping import (  # noqa: E402
    IdMapper,
    build_id_mapper_from_payload,
)


REPORT_SCHEMA_VERSION = "combat-lightspeed-production-shadow-v1"
MANIFEST_SCHEMA_VERSION = "combat-lightspeed-production-shadow-manifest-v1"
PRODUCTION_CHECKPOINT_KIND = "weights"
SHADOW_CHECKPOINT_KIND = "simulator_training_smoke"
SHADOW_SOURCE_TYPE = "combat_lightspeed_production_rl_v2_shadow"
SHADOW_FILENAME = "simulator_only_production_shadow.pth"
PROBE_SEED = 2026081901
CONVERTER_AUTHORITY = {
    "communication_mod": False,
    "evaluation": False,
    "formal_rl": False,
    "gameplay": False,
    "model_fitting": False,
    "model_loading_for_equivalence": True,
    "promotion": False,
    "production_checkpoint_read": True,
    "qualification": False,
    "training": False,
    "source_only_shadow_conversion": True,
}
SHADOW_AUTHORITY = {
    "communication_mod": False,
    "evaluation": False,
    "formal_rl": False,
    "gameplay": False,
    "model_fitting": False,
    "production_agent_loading": False,
    "production_training": False,
    "promotion": False,
    "qualification": False,
    "simulator_parent_loading": True,
    "simulator_training_parent": True,
}


def expected_rl_v2_metadata(id_mapper: IdMapper) -> dict[str, Any]:
    return {
        "rl_space_version": "v2",
        "network_type": "dueling",
        "continuous_dim": CONTINUOUS_DIM,
        "action_dim": ACTION_DIM,
        "card_vocab": id_mapper.card_vocab_size,
        "potion_vocab": id_mapper.potion_vocab_size,
        "relic_vocab": id_mapper.relic_vocab_size,
        "card_slots": CARD_SLOTS,
        "potion_slots": POTION_SLOTS,
        "relic_slots": RELIC_SLOTS,
    }


def _validate_sha256(value: str, *, label: str) -> str:
    normalized = str(value).lower()
    if not re.fullmatch(r"[0-9a-f]{64}", normalized):
        raise ValueError(f"{label} must be a 64-character SHA-256")
    return normalized


def _clone_tensor_state(state: Mapping[str, torch.Tensor]) -> dict[str, torch.Tensor]:
    if not state:
        raise ValueError("production checkpoint online state is missing or empty")
    cloned: dict[str, torch.Tensor] = {}
    for name, value in state.items():
        if not isinstance(name, str) or not isinstance(value, torch.Tensor):
            raise ValueError("production checkpoint online state contains non-tensor values")
        tensor = value.detach().cpu().clone()
        if not bool(torch.isfinite(tensor).all()):
            raise ValueError(f"production checkpoint tensor is not finite: {name}")
        cloned[name] = tensor
    return cloned


def _load_torch_checkpoint_bytes(payload: bytes) -> Any:
    stream = io.BytesIO(payload)
    try:
        return torch.load(stream, map_location="cpu", weights_only=True)
    except TypeError as exc:
        if "weights_only" not in str(exc):
            raise
        stream.seek(0)
        return torch.load(stream, map_location="cpu")


def load_production_checkpoint(
    path: Path,
    *,
    expected_sha256: str,
    id_mapper: IdMapper,
) -> dict[str, Any]:
    resolved = path.resolve()
    if not resolved.is_file():
        raise ValueError(f"production checkpoint does not exist: {resolved}")
    expected_hash = _validate_sha256(expected_sha256, label="expected checkpoint hash")
    checkpoint_bytes = resolved.read_bytes()
    actual_hash = sha256_bytes(checkpoint_bytes)
    if actual_hash != expected_hash:
        raise ValueError(
            "production checkpoint hash mismatch: "
            f"expected {expected_hash}, got {actual_hash}"
        )
    checkpoint = _load_torch_checkpoint_bytes(checkpoint_bytes)
    if not isinstance(checkpoint, Mapping):
        raise ValueError("production checkpoint root must be a mapping")
    if checkpoint.get("checkpoint_kind") != PRODUCTION_CHECKPOINT_KIND:
        raise ValueError("production checkpoint kind must be weights")
    if checkpoint.get("checkpoint_schema_version") != 2:
        raise ValueError("production checkpoint schema version must be 2")
    if checkpoint.get("rl_space_version") != "v2":
        raise ValueError("production checkpoint root RL space version must be v2")
    expected_metadata = expected_rl_v2_metadata(id_mapper)
    metadata = checkpoint.get("metadata")
    if not isinstance(metadata, Mapping) or dict(metadata) != expected_metadata:
        raise ValueError(
            "production checkpoint metadata mismatch: "
            f"expected {expected_metadata}, got {metadata}"
        )
    raw_state = checkpoint.get("online_network_state_dict")
    if not isinstance(raw_state, Mapping):
        raise ValueError("production checkpoint online state is missing or empty")
    state = _clone_tensor_state(raw_state)
    trainer = create_fresh_trainer(
        id_mapper,
        seed=PROBE_SEED,
        batch_size=1,
        learning_starts=1,
    )
    try:
        trainer.online_network.load_state_dict(state, strict=True)
    except (KeyError, RuntimeError, TypeError, ValueError) as exc:
        raise ValueError(f"production checkpoint network incompatible: {exc}") from exc
    return {
        "path": str(resolved),
        "checkpoint_sha256": actual_hash,
        "size_bytes": len(checkpoint_bytes),
        "checkpoint_schema_version": 2,
        "checkpoint_kind": PRODUCTION_CHECKPOINT_KIND,
        "rl_space_version": "v2",
        "metadata": expected_metadata,
        "parameter_sha256": parameter_sha256(state),
        "parameter_count": sum(int(value.numel()) for value in state.values()),
        "state_dict": state,
        "provenance": copy.deepcopy(checkpoint.get("provenance")),
    }


def _structure_evidence(
    source: Mapping[str, torch.Tensor],
    shadow: Mapping[str, torch.Tensor],
) -> dict[str, Any]:
    source_keys = set(source)
    shadow_keys = set(shadow)
    shared = sorted(source_keys & shadow_keys)
    shape_mismatches = {
        key: [list(source[key].shape), list(shadow[key].shape)]
        for key in shared
        if source[key].shape != shadow[key].shape
    }
    dtype_mismatches = {
        key: [str(source[key].dtype), str(shadow[key].dtype)]
        for key in shared
        if source[key].dtype != shadow[key].dtype
    }
    return {
        "keys_match": source_keys == shadow_keys,
        "missing_from_shadow": sorted(source_keys - shadow_keys),
        "unexpected_in_shadow": sorted(shadow_keys - source_keys),
        "shape_mismatches": shape_mismatches,
        "dtype_mismatches": dtype_mismatches,
        "passed": (
            source_keys == shadow_keys
            and not shape_mismatches
            and not dtype_mismatches
        ),
    }


def prove_reload_equivalence(
    id_mapper: IdMapper,
    source_state: Mapping[str, torch.Tensor],
    shadow_state: Mapping[str, torch.Tensor],
    *,
    probe_count: int = 32,
    tolerance: float = 1e-7,
) -> dict[str, Any]:
    if probe_count <= 0:
        raise ValueError("probe count must be positive")
    if not math.isfinite(tolerance) or tolerance < 0.0:
        raise ValueError("equivalence tolerance must be finite and nonnegative")
    structure = _structure_evidence(source_state, shadow_state)
    source_hash = parameter_sha256(source_state)
    shadow_hash = parameter_sha256(shadow_state)
    base = {
        "probe_count": probe_count,
        "probe_seed": PROBE_SEED,
        "tolerance": tolerance,
        "structure": structure,
        "source_parameter_sha256": source_hash,
        "shadow_parameter_sha256": shadow_hash,
        "parameter_sha256_match": source_hash == shadow_hash,
    }
    if not structure["passed"]:
        return base | {
            "max_abs_q_delta": None,
            "action_mismatch_count": None,
            "passed": False,
        }

    source_trainer = create_fresh_trainer(
        id_mapper,
        seed=PROBE_SEED,
        batch_size=1,
        learning_starts=1,
    )
    shadow_trainer = create_fresh_trainer(
        id_mapper,
        seed=PROBE_SEED + 1,
        batch_size=1,
        learning_starts=1,
    )
    try:
        source_trainer.online_network.load_state_dict(source_state, strict=True)
        shadow_trainer.online_network.load_state_dict(shadow_state, strict=True)
    except (KeyError, RuntimeError, TypeError, ValueError):
        return base | {
            "max_abs_q_delta": None,
            "action_mismatch_count": None,
            "passed": False,
        }
    source_trainer.online_network.eval()
    shadow_trainer.online_network.eval()

    rng = np.random.default_rng(PROBE_SEED)
    continuous = rng.random((probe_count, CONTINUOUS_DIM), dtype=np.float32)
    card_ids = rng.integers(
        0,
        id_mapper.card_vocab_size,
        size=(probe_count, CARD_SLOTS),
        dtype=np.int64,
    )
    potion_ids = rng.integers(
        0,
        id_mapper.potion_vocab_size,
        size=(probe_count, POTION_SLOTS),
        dtype=np.int64,
    )
    relic_ids = rng.integers(
        0,
        id_mapper.relic_vocab_size,
        size=(probe_count, RELIC_SLOTS),
        dtype=np.int64,
    )
    action_mask = np.fromfunction(
        lambda row, action: (row + action) % 4 != 0,
        (probe_count, ACTION_DIM),
        dtype=int,
    ).astype(bool)
    action_mask[:, 0] = True

    continuous_tensor = torch.from_numpy(continuous).float()
    card_tensor = torch.from_numpy(card_ids).long()
    potion_tensor = torch.from_numpy(potion_ids).long()
    relic_tensor = torch.from_numpy(relic_ids).long()
    mask_tensor = torch.from_numpy(action_mask)
    with torch.no_grad():
        source_q = source_trainer.online_network(
            continuous_tensor,
            card_tensor,
            potion_tensor,
            relic_tensor,
            mask_tensor,
        )
        shadow_q = shadow_trainer.online_network(
            continuous_tensor,
            card_tensor,
            potion_tensor,
            relic_tensor,
            mask_tensor,
        )
    valid_source = source_q[mask_tensor]
    valid_shadow = shadow_q[mask_tensor]
    finite = bool(torch.isfinite(valid_source).all()) and bool(
        torch.isfinite(valid_shadow).all()
    )
    max_abs_q_delta = (
        float(torch.max(torch.abs(valid_source - valid_shadow)).item())
        if finite
        else math.inf
    )
    action_mismatch_count = int(
        (source_q.argmax(dim=1) != shadow_q.argmax(dim=1)).sum().item()
    )
    passed = (
        structure["passed"]
        and source_hash == shadow_hash
        and finite
        and max_abs_q_delta <= tolerance
        and action_mismatch_count == 0
    )
    return base | {
        "valid_q_values_finite": finite,
        "max_abs_q_delta": max_abs_q_delta,
        "action_mismatch_count": action_mismatch_count,
        "passed": passed,
    }


def _summary_markdown(report: Mapping[str, Any]) -> str:
    source = report["source_checkpoint"]
    shadow = report["shadow_checkpoint"]
    equivalence = report["equivalence"]
    return "\n".join(
        (
            "# Production RL v2 simulator shadow",
            "",
            f"- Verdict: `{report['verdict']}`",
            f"- Source checkpoint SHA-256: `{source['checkpoint_sha256']}`",
            f"- Source parameter SHA-256: `{source['parameter_sha256']}`",
            f"- Shadow checkpoint SHA-256: `{shadow['checkpoint_sha256']}`",
            f"- Shadow parameter SHA-256: `{shadow['parameter_sha256']}`",
            f"- Parameter count: `{source['parameter_count']}`",
            f"- Probe count: `{equivalence['probe_count']}`",
            f"- Maximum valid-action Q delta: `{equivalence['max_abs_q_delta']}`",
            f"- Action mismatches: `{equivalence['action_mismatch_count']}`",
            "- Item identity evidence: current file hash plus vocabulary dimensions; "
            "the source checkpoint does not contain its historical items hash",
            "- Production compatible: `false`",
            "- LightSTS simulator parent loading: `true`",
            "- CommunicationMod and production agent loading: `false`",
            "",
        )
    )


def publish_production_shadow(
    output_dir: Path,
    *,
    production_checkpoint: Path,
    expected_checkpoint_sha256: str,
    items_json: Path,
    expected_items_sha256: str,
    source_commit: str,
    probe_count: int = 32,
    tolerance: float = 1e-7,
) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", source_commit):
        raise ValueError("source commit must be a lowercase 40- or 64-hex identity")
    target = output_dir.resolve()
    if target.exists():
        raise FileExistsError(f"shadow output already exists: {target}")
    staging = target.with_name(f".{target.name}.{uuid.uuid4().hex}.staging")

    items_path = items_json.resolve()
    if not items_path.is_file():
        raise ValueError(f"items JSON does not exist: {items_path}")
    expected_items_hash = _validate_sha256(
        expected_items_sha256,
        label="expected items hash",
    )
    items_bytes = items_path.read_bytes()
    actual_items_hash = sha256_bytes(items_bytes)
    if actual_items_hash != expected_items_hash:
        raise ValueError(
            f"items JSON hash mismatch: expected {expected_items_hash}, "
            f"got {actual_items_hash}"
        )
    try:
        items_payload = json.loads(items_bytes.decode("utf-8"))
        if not isinstance(items_payload, Mapping):
            raise TypeError("items JSON root is not an object")
        id_mapper = build_id_mapper_from_payload(items_payload)
    except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"items JSON is invalid: {exc}") from exc
    source = load_production_checkpoint(
        production_checkpoint,
        expected_sha256=expected_checkpoint_sha256,
        id_mapper=id_mapper,
    )
    converter_path = Path(__file__).resolve()
    converter_sha256 = sha256_bytes(converter_path.read_bytes())
    source_binding = {
        "construction": "exact_production_rl_v2_simulator_shadow",
        "source_commit": source_commit,
        "converter_path": str(converter_path),
        "converter_sha256": converter_sha256,
        "production_checkpoint_path": source["path"],
        "production_checkpoint_sha256": source["checkpoint_sha256"],
        "production_parameter_sha256": source["parameter_sha256"],
        "items_json_path": str(items_path),
        "items_json_sha256": actual_items_hash,
    }
    shadow_state = _clone_tensor_state(source["state_dict"])
    shadow_checkpoint = {
        "checkpoint_schema_version": 0,
        "checkpoint_kind": SHADOW_CHECKPOINT_KIND,
        "source_type": SHADOW_SOURCE_TYPE,
        "production_compatible": False,
        "online_network_state_dict": shadow_state,
        "metadata": {
            "authority": dict(SHADOW_AUTHORITY),
            "rl_v2": dict(source["metadata"]),
            "source_binding": source_binding,
        },
    }

    staging_created = False
    try:
        staging.mkdir(parents=True, exist_ok=False)
        staging_created = True
        shadow_path = staging / SHADOW_FILENAME
        save_torch_checkpoint(shadow_checkpoint, str(shadow_path))
        reloaded = load_torch_checkpoint(str(shadow_path), map_location="cpu")
        if not isinstance(reloaded, Mapping):
            raise ValueError("staged shadow checkpoint root must be a mapping")
        if reloaded.get("checkpoint_kind") != SHADOW_CHECKPOINT_KIND:
            raise ValueError("staged shadow checkpoint kind is invalid")
        if reloaded.get("production_compatible") is not False:
            raise ValueError("staged shadow checkpoint is production-compatible")
        raw_reloaded_state = reloaded.get("online_network_state_dict")
        if not isinstance(raw_reloaded_state, Mapping):
            raise ValueError("staged shadow online state is missing or empty")
        reloaded_state = _clone_tensor_state(raw_reloaded_state)
        equivalence = prove_reload_equivalence(
            id_mapper,
            source["state_dict"],
            reloaded_state,
            probe_count=probe_count,
            tolerance=tolerance,
        )
        if not equivalence["passed"]:
            raise ValueError(f"staged shadow equivalence failed: {equivalence}")

        shadow_record = {
            "path": SHADOW_FILENAME,
            "checkpoint_sha256": sha256_file(shadow_path),
            "size_bytes": shadow_path.stat().st_size,
            "checkpoint_schema_version": 0,
            "checkpoint_kind": SHADOW_CHECKPOINT_KIND,
            "source_type": SHADOW_SOURCE_TYPE,
            "production_compatible": False,
            "parameter_sha256": parameter_sha256(reloaded_state),
        }
        report = {
            "schema_version": REPORT_SCHEMA_VERSION,
            "source_type": SHADOW_SOURCE_TYPE,
            "source_commit": source_commit,
            "authority": dict(CONVERTER_AUTHORITY),
            "converter": {
                "path": str(converter_path),
                "sha256": converter_sha256,
            },
            "items": {
                "path": str(items_path),
                "sha256": actual_items_hash,
                "card_vocab": id_mapper.card_vocab_size,
                "potion_vocab": id_mapper.potion_vocab_size,
                "relic_vocab": id_mapper.relic_vocab_size,
                "source_checkpoint_items_sha256_available": False,
                "identity_evidence": "current_file_hash_and_vocabulary_dimensions_only",
            },
            "source_checkpoint": {
                key: source[key]
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
                    "provenance",
                )
            },
            "shadow_checkpoint": shadow_record,
            "equivalence": equivalence,
            "verdict": "production_shadow_ready",
        }
        report_bytes = canonical_json_bytes(report) + b"\n"
        summary_bytes = _summary_markdown(report).encode("utf-8")
        (staging / "report.json").write_bytes(report_bytes)
        (staging / "summary.md").write_bytes(summary_bytes)
        artifacts = {}
        for name in (SHADOW_FILENAME, "report.json", "summary.md"):
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
    parser.add_argument("--production-checkpoint", type=Path, required=True)
    parser.add_argument("--expected-checkpoint-sha256", required=True)
    parser.add_argument("--items-json", type=Path, required=True)
    parser.add_argument("--expected-items-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--probe-count", type=int, default=32)
    parser.add_argument("--tolerance", type=float, default=1e-7)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = publish_production_shadow(
        args.output_dir,
        production_checkpoint=args.production_checkpoint,
        expected_checkpoint_sha256=args.expected_checkpoint_sha256,
        items_json=args.items_json,
        expected_items_sha256=args.expected_items_sha256,
        source_commit=args.source_commit,
        probe_count=args.probe_count,
        tolerance=args.tolerance,
    )
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
