"""Source-only controls for the card-acceptance empirical successor."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
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
    """Return fresh identities for the four isolated successor modules."""
    return {
        "modules": [
            {"name": name, "path": path, "role": role}
            for role, name, path in _MODULE_SPECS
        ],
        "schema_version": DEPENDENCY_INVENTORY_SCHEMA_VERSION,
    }


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
