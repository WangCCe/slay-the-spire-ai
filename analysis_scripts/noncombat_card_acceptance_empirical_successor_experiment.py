"""Source-only controls for the card-acceptance empirical successor."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import json
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any


CONTRACT_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-contract-v1"
)
RUNTIME_METADATA_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-runtime-metadata-v1"
)
DEPENDENCY_INVENTORY_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-module-inventory-v1"
)
SOURCE_INVENTORY_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-source-inventory-v1"
)
CONFIG_IDENTITY_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-config-identity-v1"
)
RUNTIME_MODULE_NAME = (
    "analysis_scripts.noncombat_card_acceptance_empirical_successor_runtime"
)

_AUTHORITY_NAMES = (
    "causal",
    "communication_mod",
    "environment_construction",
    "evaluation",
    "execution",
    "formal_rl",
    "gameplay",
    "model_fitting",
    "native_loading",
    "ope",
    "production_model_loading",
    "promotion",
    "qualification",
    "seed_access",
    "training",
)
_MODULE_SPECS = (
    (
        "control_plane",
        "analysis_scripts.noncombat_card_acceptance_empirical_successor_experiment",
        "analysis_scripts/noncombat_card_acceptance_empirical_successor_experiment.py",
    ),
    (
        "torch_runtime",
        "analysis_scripts.noncombat_card_acceptance_empirical_successor_runtime",
        "analysis_scripts/noncombat_card_acceptance_empirical_successor_runtime.py",
    ),
    (
        "seed_inventory",
        "analysis_scripts.noncombat_card_acceptance_empirical_successor_seed_inventory",
        "analysis_scripts/noncombat_card_acceptance_empirical_successor_seed_inventory.py",
    ),
    (
        "independent_verifier",
        "analysis_scripts.verify_noncombat_card_acceptance_empirical_successor",
        "analysis_scripts/verify_noncombat_card_acceptance_empirical_successor.py",
    ),
)
_PUBLIC_DEPENDENCY_SPECS = (
    (
        "analysis_scripts_package",
        "analysis_scripts/__init__.py",
        (),
    ),
    (
        "action_family_distribution",
        "analysis_scripts/noncombat_action_family_distribution.py",
        (
            "ActionFamilyDistribution",
            "build_action_family_distribution",
            "distribution_metadata",
        ),
    ),
    (
        "advantage_attribution",
        "analysis_scripts/noncombat_hierarchical_advantage_attribution.py",
        (
            "FEATURE_FIELDS",
            "FEATURE_SCHEMA_VERSION",
            "AdvantageAttributionError",
            "AdvantageBatch",
            "build_advantage_batch",
        ),
    ),
    (
        "card_acceptance_objective",
        "analysis_scripts/noncombat_card_acceptance_objective.py",
        (
            "CardAcceptanceObjectiveError",
            "CardAcceptancePolicyTerms",
            "build_card_acceptance_policy_terms",
        ),
    ),
    (
        "card_acceptance_policy",
        "analysis_scripts/noncombat_card_acceptance_policy.py",
        (
            "CardAcceptancePolicy",
            "CardAcceptancePolicyError",
            "CardAcceptancePolicyOutput",
            "build_family_features",
        ),
    ),
    (
        "candidate_feature_projection",
        "analysis_scripts/noncombat_policy_model.py",
        ("FeatureConfig", "candidate_feature_vector"),
    ),
    (
        "formal_reward",
        "analysis_scripts/noncombat_formal_reward_contract.py",
        ("reward_channels", "validate_scalarization"),
    ),
    (
        "hierarchical_objective",
        "analysis_scripts/noncombat_hierarchical_policy_objective.py",
        ("build_hierarchical_policy_terms",),
    ),
    (
        "policy_input",
        "analysis_scripts/noncombat_state_conditioned_policy_input.py",
        (
            "HASH_DIM",
            "PolicyInputError",
            "project_state_conditioned_policy_input",
        ),
    ),
    (
        "simulator_adapter",
        "analysis_scripts/noncombat_simulator_adapter.py",
        (
            "ADAPTER_API_VERSION",
            "SimulatorAdapterError",
            "TARGET_CATEGORIES",
            "canonical_json_bytes",
            "validate_candidates",
            "validate_snapshot",
        ),
    ),
    (
        "simulator_rl_policy_projection",
        "analysis_scripts/noncombat_simulator_rl_experiment.py",
        ("canonical_json_bytes", "project_policy_view_v2"),
    ),
    (
        "state_conditioned_ranker",
        "analysis_scripts/noncombat_state_conditioned_ranker.py",
        ("DEFAULT_HIDDEN_DIM", "StateConditionedCandidateRanker"),
    ),
)


class SuccessorControlError(ValueError):
    """Raised when a source-only control value cannot be encoded safely."""


def canonical_json_bytes(value: object) -> bytes:
    """Encode deterministic ASCII JSON with exactly one trailing newline."""
    try:
        rendered = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise SuccessorControlError("value is not canonical JSON") from exc
    return rendered.encode("ascii") + b"\n"


def canonical_json_sha256(value: object) -> str:
    """Digest the exact canonical JSON representation."""
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _authority() -> dict[str, bool]:
    return {name: False for name in _AUTHORITY_NAMES}


def _algorithm() -> dict[str, Any]:
    return {
        "conditional_entropy_coefficient": 0.01,
        "discount": 1.0,
        "family_entropy_coefficient": 0.01,
        "gradient_norm_ceiling": 1.0,
        "learning_rate": 0.001,
        "model_seed": 0,
        "optimizer": "adam",
        "optimizer_amsgrad": False,
        "optimizer_betas": [0.9, 0.999],
        "optimizer_eps": 1e-8,
        "optimizer_weight_decay": 0.0,
    }


def _cohorts() -> dict[str, int]:
    return {
        "canary_pairs": 128,
        "holdout_pairs": 512,
        "training_chunks": 8,
        "training_pairs": 512,
        "training_pairs_per_chunk": 64,
    }


def _limits() -> dict[str, int | float]:
    return {
        "max_artifact_bytes": 64 * 1024 * 1024,
        "max_canary_environment_accesses": 512,
        "max_charged_seconds": 28_800.0,
        "max_decisions_per_episode": 500,
        "max_environment_accesses": 2_560,
        "max_holdout_environment_accesses": 1_024,
        "max_shadow_optimizer_steps": 1,
        "max_stored_bytes": 256 * 1024 * 1024,
        "max_training_environment_accesses": 1_024,
        "max_training_optimizer_steps": 16,
        "max_training_updates_per_arm": 8,
        "max_uncompressed_bytes": 512 * 1024 * 1024,
    }


def expected_runtime_metadata() -> dict[str, Any]:
    """Return fresh expected metadata without importing the runtime."""
    algorithm = _algorithm()
    return {
        "algorithm": algorithm,
        "architecture": {
            "candidate": "disjoint-family-and-conditional-heads",
            "control": "shared-card-ranker",
            "frozen_noncard_rankers": 2,
            "matched_rankers": 5,
        },
        "authority": _authority(),
        "baseline": {
            "feature_dim": 128,
            "fit_trajectories_per_fold": 48,
            "fold_count": 4,
            "held_out_trajectories_per_fold": 16,
            "prediction_bounds": [0.0, 3.0],
            "ridge_coefficient": 0.001,
            "ridge_residual_atol": 1e-9,
            "ridge_residual_rtol": 1e-9,
            "scale": 1.0,
            "solver": "cpu-float64-cholesky-v1",
            "source_dim": 1024,
            "trajectory_weighting": "equal-trajectory-mean-squared-error-v1",
        },
        "device": "cpu",
        "dtype": "float32",
        "environment": {
            "adapter_api_version": "sts-lightspeed-noncombat-adapter-v3",
            "ascension": 0,
            "device": "cpu",
        },
        "optimizer": {
            "amsgrad": algorithm["optimizer_amsgrad"],
            "betas": list(algorithm["optimizer_betas"]),
            "eps": algorithm["optimizer_eps"],
            "learning_rate": algorithm["learning_rate"],
            "name": algorithm["optimizer"],
            "weight_decay": algorithm["optimizer_weight_decay"],
        },
        "schema_version": RUNTIME_METADATA_SCHEMA_VERSION,
    }


def module_dependency_inventory() -> dict[str, Any]:
    """Declare the closed successor modules and local behavioral dependencies."""
    return {
        "modules": [
            {"name": name, "path": path, "role": role}
            for role, name, path in _MODULE_SPECS
        ],
        "public_dependencies": [
            {
                "name": name,
                "path": path,
                "public_symbols": list(public_symbols),
            }
            for name, path, public_symbols in _PUBLIC_DEPENDENCY_SPECS
        ],
        "schema_version": DEPENDENCY_INVENTORY_SCHEMA_VERSION,
    }


def _source_binding(path: str, payload: bytes) -> dict[str, Any]:
    return {
        "path": path,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def build_source_inventory(repo_root: Path | str) -> dict[str, Any]:
    """Hash the closed source declaration without importing any source module."""
    root = Path(repo_root).resolve()
    if not root.is_dir():
        raise SuccessorControlError("source repository root is missing")
    declaration = module_dependency_inventory()
    observed: dict[str, list[dict[str, Any]]] = {
        "modules": [],
        "public_dependencies": [],
    }
    try:
        for section in observed:
            for row in declaration[section]:
                path = str(row["path"])
                payload = (root / PurePosixPath(path)).read_bytes()
                observed[section].append({**row, **_source_binding(path, payload)})
    except OSError as exc:
        raise SuccessorControlError(
            f"source inventory cannot be observed: {exc}"
        ) from exc
    body = {
        **observed,
        "schema_version": SOURCE_INVENTORY_SCHEMA_VERSION,
    }
    return {**body, "inventory_sha256": canonical_json_sha256(body)}


def external_file_binding(path: Path | str) -> dict[str, Any]:
    """Hash one external file as inert bytes without importing or loading it."""
    candidate = Path(path).resolve()
    if not candidate.is_file():
        raise SuccessorControlError(f"external file is missing: {candidate}")
    try:
        payload = candidate.read_bytes()
    except OSError as exc:
        raise SuccessorControlError(
            f"external file cannot be read: {candidate}"
        ) from exc
    if not payload:
        raise SuccessorControlError(f"external file is empty: {candidate}")
    return {
        "path": candidate.as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _hash_named_bytes(rows: Sequence[tuple[str, bytes]]) -> str:
    digest = hashlib.sha256()
    for name, payload in rows:
        encoded_name = name.encode("utf-8")
        digest.update(len(encoded_name).to_bytes(4, "big"))
        digest.update(encoded_name)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


def snapshot_directory_tree(root: Path | str) -> dict[str, Any]:
    """Hash a complete directory tree in canonical relative-path order."""
    directory = Path(root).resolve()
    if not directory.is_dir():
        raise SuccessorControlError(f"directory root is missing: {directory}")
    try:
        files = sorted(
            (path for path in directory.rglob("*") if path.is_file()),
            key=lambda path: path.relative_to(directory).as_posix(),
        )
        rows = [
            (path.relative_to(directory).as_posix(), path.read_bytes())
            for path in files
        ]
    except OSError as exc:
        raise SuccessorControlError(
            f"directory tree cannot be read: {directory}"
        ) from exc
    return {
        "file_count": len(rows),
        "root": directory.as_posix(),
        "sha256": _hash_named_bytes(rows),
        "size_bytes": sum(len(payload) for _, payload in rows),
    }


def build_native_identity(
    *,
    module_path: Path | str,
    dll_directories: Sequence[Path | str],
    provenance: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind native bytes and declared provenance without loading the module."""
    if isinstance(dll_directories, (str, bytes)):
        raise SuccessorControlError("native DLL directories must be a sequence")
    normalized_directories = sorted(
        {Path(path).resolve().as_posix() for path in dll_directories}
    )
    if not normalized_directories or any(
        not Path(path).is_dir() for path in normalized_directories
    ):
        raise SuccessorControlError("native DLL directory is missing")
    module = external_file_binding(module_path)
    if not isinstance(provenance, Mapping) or not provenance:
        raise SuccessorControlError("native provenance must be a nonempty mapping")
    normalized_provenance = copy.deepcopy(dict(provenance))
    build = normalized_provenance.get("build")
    if not isinstance(build, Mapping) or build.get("adapter_api_version") != (
        "sts-lightspeed-noncombat-adapter-v3"
    ):
        raise SuccessorControlError("native provenance adapter API mismatch")
    if normalized_provenance.get("module_sha256") != module["sha256"]:
        raise SuccessorControlError("native provenance module digest mismatch")
    return {
        "adapter_api_version": "sts-lightspeed-noncombat-adapter-v3",
        "dll_directories": normalized_directories,
        "module": module,
        "provenance": normalized_provenance,
        "provenance_sha256": canonical_json_sha256(normalized_provenance),
    }


def build_isolation_identity(
    *,
    communication_mod_config: Path | str,
    production_checkpoint_root: Path | str,
) -> dict[str, Any]:
    """Bind production configuration and checkpoint bytes without loading them."""
    return {
        "communication_mod_config": external_file_binding(
            communication_mod_config
        ),
        "production_checkpoints": snapshot_directory_tree(
            production_checkpoint_root
        ),
    }


def _load_runtime_module(
    *, module_importer: Callable[[str], Any] | None = None
) -> Any:
    """Import the Torch runtime only when a later validated preflight calls here."""
    importer = module_importer or importlib.import_module
    return importer(RUNTIME_MODULE_NAME)


def experiment_contract() -> dict[str, Any]:
    """Return the fixed source-only experiment contract."""
    return {
        "algorithm": _algorithm(),
        "authority": _authority(),
        "cohorts": _cohorts(),
        "environment": {
            "adapter_api_version": "sts-lightspeed-noncombat-adapter-v3",
            "ascension": 0,
            "device": "cpu",
        },
        "limits": _limits(),
        "runtime_metadata": expected_runtime_metadata(),
        "schema_version": CONTRACT_SCHEMA_VERSION,
    }


def experiment_configuration_identity() -> dict[str, Any]:
    """Bind the fixed source-only experiment configuration canonically."""
    payload = canonical_json_bytes(experiment_contract())
    return {
        "canonical_size_bytes": len(payload),
        "contract_sha256": hashlib.sha256(payload).hexdigest(),
        "schema_version": CONFIG_IDENTITY_SCHEMA_VERSION,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Card-acceptance empirical successor source controls"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("contract", help="print the immutable source contract")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command != "contract":
        raise SuccessorControlError("unknown source-only command")
    sys.stdout.buffer.write(canonical_json_bytes(experiment_contract()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
