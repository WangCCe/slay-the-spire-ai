"""Run one preregistered reused-seed Current bridge diagnostic smoke."""

from __future__ import annotations

import argparse
import copy
import json
import os
import subprocess
import sys
import time
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any


_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import analysis_scripts.noncombat_reachable_event_native_compatibility as predecessor
from analysis_scripts.noncombat_current_policy_simulator_bridge import (
    BridgeBlocked,
    CurrentPolicyBridgeSession,
    MetadataCatalog,
    POLICY_ID,
    hash_bound_files,
)
from analysis_scripts.noncombat_event_option_semantics import (
    reachable_event_option_semantics_identity,
)
from analysis_scripts.noncombat_simulator_adapter import (
    NativeSimulatorEnvironment,
    SimulatorAdapterError,
    TARGET_CATEGORIES,
    canonical_json_bytes,
    load_native_module,
    sha256_bytes,
    sha256_file,
    validate_candidates,
)


INPUT_SCHEMA_VERSION = "noncombat-current-bridge-diagnostic-smoke-input-v1"
EXECUTION_SCHEMA_VERSION = "noncombat-current-bridge-diagnostic-smoke-execution-v1"
JOURNAL_SCHEMA_VERSION = "noncombat-current-bridge-diagnostic-smoke-journal-v1"
CONFIGURATION_SCHEMA_VERSION = (
    "noncombat-current-bridge-diagnostic-smoke-configuration-v1"
)
METRICS_SCHEMA_VERSION = "noncombat-current-bridge-diagnostic-smoke-metrics-v1"
TRAJECTORY_SCHEMA_VERSION = (
    "noncombat-current-bridge-diagnostic-smoke-trajectories-v1"
)
MANIFEST_SCHEMA_VERSION = "noncombat-current-bridge-diagnostic-smoke-manifest-v1"
PREIMPLEMENTATION_SCHEMA_VERSION = (
    "noncombat-current-bridge-diagnostic-smoke-preimplementation-v1"
)

FIXED_SEEDS = (7000, 7100, 2000, 10)
REPLAY_COUNT = 2
MAX_DECISIONS_PER_REPLAY = 500
MAX_WALL_SECONDS = 600.0
DECLARED_SUPPORT_REASON = "unsupported_shop_courier_restock_semantics"

EXPECTED_ADAPTER_COMMIT = "cbacad62afcffd944aff856490458caa8e6d8328"
EXPECTED_MODULE_SHA256 = (
    "7ac2c750fba6e38d4a023cab72a4d67f158fe7f88414058e5876cef5003fcb88"
)
EXPECTED_MODULE_SIZE_BYTES = 4225024
EXPECTED_PREIMPLEMENTATION_SHA256 = (
    "35bee05b114c30a6b15da52232807a7295f487b565f06ca55c46938f3f435f1e"
)
EXPECTED_PREIMPLEMENTATION_SIZE_BYTES = 6949
EXPECTED_PLANNING_COMMIT = "2bb0d0e53074daad1bf01254cffaa23c4f24210b"

R2_PREIMPLEMENTATION_SCHEMA_VERSION = (
    "noncombat-current-bridge-diagnostic-smoke-preimplementation-v2"
)
R2_INPUT_SCHEMA_VERSION = "noncombat-current-bridge-diagnostic-smoke-input-v2"
R2_EXECUTION_SCHEMA_VERSION = (
    "noncombat-current-bridge-diagnostic-smoke-execution-v2"
)
R2_JOURNAL_SCHEMA_VERSION = (
    "noncombat-current-bridge-diagnostic-smoke-journal-v2"
)
R2_CONFIGURATION_SCHEMA_VERSION = (
    "noncombat-current-bridge-diagnostic-smoke-configuration-v2"
)
R2_METRICS_SCHEMA_VERSION = (
    "noncombat-current-bridge-diagnostic-smoke-metrics-v2"
)
R2_TRAJECTORY_SCHEMA_VERSION = (
    "noncombat-current-bridge-diagnostic-smoke-trajectories-v2"
)
R2_MANIFEST_SCHEMA_VERSION = (
    "noncombat-current-bridge-diagnostic-smoke-manifest-v2"
)
R2_EXPECTED_PREIMPLEMENTATION_SHA256 = (
    "aabbc0e007f2f44f05c1f529ce03ada57c715fe257237fa2c830a6f2035ed9c9"
)
R2_EXPECTED_PREIMPLEMENTATION_SIZE_BYTES = 5603
R2_EXPECTED_PLANNING_COMMIT = "7a0fefcc120d325349c8c60e7560d8ecd790f5fd"

PREIMPLEMENTATION_PATH = (
    "reports/noncombat_current_bridge_diagnostic_smoke_20260803_"
    "preimplementation.json"
)
DEFAULT_REGISTRATION_PATH = (
    "reports/noncombat_current_bridge_diagnostic_smoke_20260803_input.json"
)
DEFAULT_OUTPUT_DIRECTORY = (
    "reports/noncombat_current_bridge_diagnostic_smoke_20260803"
)
R2_PREIMPLEMENTATION_PATH = (
    "reports/noncombat_current_bridge_diagnostic_smoke_20260803_"
    "r2_preimplementation.json"
)
R2_REGISTRATION_PATH = (
    "reports/noncombat_current_bridge_diagnostic_smoke_20260803_r2_input.json"
)
R2_OUTPUT_DIRECTORY = (
    "reports/noncombat_current_bridge_diagnostic_smoke_20260803_r2"
)

CANONICAL_ARTIFACT_NAMES = (
    "artifact_manifest.json",
    "configuration.json",
    "execution_journal.json",
    "metrics.json",
    "report.md",
    "trajectory_rows.json",
)

ALL_FALSE_AUTHORITY = {
    "baseline_floor_authorized": False,
    "formal_rl_authorized": False,
    "fresh_evidence_authorized": False,
    "gameplay_authorized": False,
    "model_fitting_authorized": False,
    "ope_authorized": False,
    "policy_loading_authorized": False,
    "promotion_authorized": False,
    "qualification_authorized": False,
    "reward_authorized": False,
    "target_supported_outcome_authorized": False,
    "training_authorized": False,
}

CURRENT_POLICY = copy.deepcopy(predecessor.CURRENT_POLICY)
ADAPTER_SOURCE_FILES = predecessor.ADAPTER_SOURCE_FILES
IMPLEMENTATION_SOURCE_FILES = tuple(
    dict.fromkeys(
        (
            "analysis_scripts/noncombat_current_bridge_diagnostic_smoke.py",
            "tests/test_noncombat_current_bridge_diagnostic_smoke.py",
            *predecessor.IMPLEMENTATION_SOURCE_FILES,
        )
    )
)


@dataclass(frozen=True)
class DiagnosticProfile:
    """Immutable publication identity for one diagnostic registration."""

    name: str
    input_schema_version: str
    execution_schema_version: str
    journal_schema_version: str
    configuration_schema_version: str
    metrics_schema_version: str
    trajectory_schema_version: str
    manifest_schema_version: str
    preimplementation_schema_version: str
    preimplementation_path: str
    preimplementation_sha256: str
    preimplementation_size_bytes: int
    planning_commit: str
    registration_path: str
    output_directory: str
    implementation_source_files: tuple[str, ...]


V1_PROFILE = DiagnosticProfile(
    name="v1-consumed",
    input_schema_version=INPUT_SCHEMA_VERSION,
    execution_schema_version=EXECUTION_SCHEMA_VERSION,
    journal_schema_version=JOURNAL_SCHEMA_VERSION,
    configuration_schema_version=CONFIGURATION_SCHEMA_VERSION,
    metrics_schema_version=METRICS_SCHEMA_VERSION,
    trajectory_schema_version=TRAJECTORY_SCHEMA_VERSION,
    manifest_schema_version=MANIFEST_SCHEMA_VERSION,
    preimplementation_schema_version=PREIMPLEMENTATION_SCHEMA_VERSION,
    preimplementation_path=PREIMPLEMENTATION_PATH,
    preimplementation_sha256=EXPECTED_PREIMPLEMENTATION_SHA256,
    preimplementation_size_bytes=EXPECTED_PREIMPLEMENTATION_SIZE_BYTES,
    planning_commit=EXPECTED_PLANNING_COMMIT,
    registration_path=DEFAULT_REGISTRATION_PATH,
    output_directory=DEFAULT_OUTPUT_DIRECTORY,
    implementation_source_files=IMPLEMENTATION_SOURCE_FILES,
)

R2_PROFILE = DiagnosticProfile(
    name="r2-successor",
    input_schema_version=R2_INPUT_SCHEMA_VERSION,
    execution_schema_version=R2_EXECUTION_SCHEMA_VERSION,
    journal_schema_version=R2_JOURNAL_SCHEMA_VERSION,
    configuration_schema_version=R2_CONFIGURATION_SCHEMA_VERSION,
    metrics_schema_version=R2_METRICS_SCHEMA_VERSION,
    trajectory_schema_version=R2_TRAJECTORY_SCHEMA_VERSION,
    manifest_schema_version=R2_MANIFEST_SCHEMA_VERSION,
    preimplementation_schema_version=R2_PREIMPLEMENTATION_SCHEMA_VERSION,
    preimplementation_path=R2_PREIMPLEMENTATION_PATH,
    preimplementation_sha256=R2_EXPECTED_PREIMPLEMENTATION_SHA256,
    preimplementation_size_bytes=R2_EXPECTED_PREIMPLEMENTATION_SIZE_BYTES,
    planning_commit=R2_EXPECTED_PLANNING_COMMIT,
    registration_path=R2_REGISTRATION_PATH,
    output_directory=R2_OUTPUT_DIRECTORY,
    implementation_source_files=IMPLEMENTATION_SOURCE_FILES,
)

SUPPORTED_PROFILES = (V1_PROFILE, R2_PROFILE)

EXPECTED_TRACKED_EVIDENCE_IDS = (
    "baseline_floor_closeout",
    "baseline_floor_input",
    "baseline_floor_result",
    "current_bridge_closeout",
    "current_bridge_input",
    "current_bridge_manifest",
    "current_bridge_metrics",
    "reachable_compatibility_closeout",
    "reachable_compatibility_input",
    "reachable_compatibility_journal",
    "reachable_compatibility_manifest",
    "reachable_event_repair",
    "remove_sentinel_repair",
    "shop_support_envelope",
    "sold_inventory_repair",
    "total_compatibility_closeout",
    "total_compatibility_input",
    "total_compatibility_journal",
    "total_compatibility_manifest",
)

EXPECTED_MODULE_EVIDENCE = (
    {
        "id": "original_v3",
        "path": (
            ".sts_lightspeed_adapter_v3_build/"
            "sts_lightspeed_noncombat_adapter.cp310-win_amd64.pyd"
        ),
        "sha256": (
            "410ac6b742192cfcd3568e36975bc87ecab4c2de9093d30113258b74a887e8cb"
        ),
        "size_bytes": 4223488,
    },
    {
        "id": "sold_inventory_v3",
        "path": (
            ".sts_lightspeed_adapter_v3_sold_inventory_build/"
            "sts_lightspeed_noncombat_adapter.cp310-win_amd64.pyd"
        ),
        "sha256": (
            "f5dde34657156db74e437bcb954fc0ceb739604bb43a3bcb10da5fd861bc48b8"
        ),
        "size_bytes": 4224512,
    },
    {
        "id": "shop_support_v3",
        "path": (
            ".sts_lightspeed_adapter_v3_shop_support_build/"
            "sts_lightspeed_noncombat_adapter.cp310-win_amd64.pyd"
        ),
        "sha256": EXPECTED_MODULE_SHA256,
        "size_bytes": EXPECTED_MODULE_SIZE_BYTES,
    },
)


class DiagnosticBlocked(RuntimeError):
    """Raised when the immutable diagnostic boundary cannot be proved."""

    def __init__(self, reason: str, detail: object | None = None):
        self.reason = reason
        self.detail = detail
        message = reason if detail is None else f"{reason}: {detail}"
        super().__init__(message)


def _coerce_profile(profile: DiagnosticProfile) -> DiagnosticProfile:
    if profile not in SUPPORTED_PROFILES:
        raise DiagnosticBlocked("diagnostic_profile_unsupported")
    return profile


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise DiagnosticBlocked("invalid_mapping", label)
    return dict(value)


def _sequence(value: object, label: str) -> list[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise DiagnosticBlocked("invalid_sequence", label)
    return list(value)


def _require_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise DiagnosticBlocked(
            "object_keys_mismatch",
            {"actual": sorted(value), "expected": sorted(expected), "label": label},
        )


def _is_hex(value: object, length: int) -> bool:
    if not isinstance(value, str) or len(value) != length:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _canonical_equal(left: object, right: object) -> bool:
    try:
        return canonical_json_bytes(left) == canonical_json_bytes(right)
    except (TypeError, ValueError):
        return False


def _validate_binding(
    value: object, label: str, *, repository_relative: bool
) -> dict[str, Any]:
    binding = _mapping(value, label)
    _require_keys(binding, {"path", "sha256", "size_bytes"}, label)
    path = binding["path"]
    if not isinstance(path, str) or not path:
        raise DiagnosticBlocked("binding_path_invalid", label)
    if repository_relative:
        pure = PurePosixPath(path)
        if (
            "\\" in path
            or pure.is_absolute()
            or any(part in {"", ".", ".."} for part in pure.parts)
        ):
            raise DiagnosticBlocked("binding_path_invalid", label)
    elif not Path(path).is_absolute():
        raise DiagnosticBlocked("binding_path_invalid", label)
    if not _is_hex(binding["sha256"], 64):
        raise DiagnosticBlocked("binding_hash_invalid", label)
    size = binding["size_bytes"]
    if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
        raise DiagnosticBlocked("binding_size_invalid", label)
    return binding


def _file_binding(path: Path, display_path: str) -> dict[str, Any]:
    if not path.is_file():
        raise DiagnosticBlocked("bound_file_missing", display_path)
    return {
        "path": display_path,
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def _validate_provenance(value: object) -> dict[str, Any]:
    try:
        provenance = predecessor._validate_provenance(copy.deepcopy(value))
    except predecessor.CompatibilityBlocked as exc:
        raise DiagnosticBlocked(exc.reason, exc.detail) from exc
    contract = reachable_event_option_semantics_identity()
    if (
        provenance["adapter_commit"] != EXPECTED_ADAPTER_COMMIT
        or provenance["module_sha256"] != EXPECTED_MODULE_SHA256
        or provenance["module_size_bytes"] != EXPECTED_MODULE_SIZE_BYTES
    ):
        raise DiagnosticBlocked("registered_module_identity_mismatch")
    if (
        provenance["simulator_commit"] != contract["simulator_commit"]
        or provenance["simulator_source_sha256"]
        != contract["simulator_source_sha256"]
    ):
        raise DiagnosticBlocked("native_simulator_contract_mismatch")
    return provenance


def _validate_seed_rationale(value: object) -> list[dict[str, Any]]:
    rationale = _sequence(value, "seed_rationale")
    if len(rationale) != len(FIXED_SEEDS):
        raise DiagnosticBlocked("preimplementation_seed_rationale_mismatch")
    normalized = []
    for index, raw in enumerate(rationale):
        row = _mapping(raw, f"seed_rationale[{index}]")
        if (
            set(row) != {"boundary", "seed"}
            or row["seed"] != FIXED_SEEDS[index]
            or not isinstance(row["boundary"], str)
            or not row["boundary"]
        ):
            raise DiagnosticBlocked("preimplementation_seed_rationale_mismatch")
        normalized.append(row)
    return normalized


def _validate_relative_binding_path(
    value: object, *, label: str, expected_path: str
) -> dict[str, Any]:
    binding = _validate_binding(value, label, repository_relative=True)
    if binding["path"] != expected_path:
        raise DiagnosticBlocked("preimplementation_lineage_path_mismatch", label)
    return binding


def _validate_r2_preimplementation(value: object) -> dict[str, Any]:
    baseline = _mapping(value, "preimplementation")
    _require_keys(
        baseline,
        {
            "authority",
            "cohort",
            "lineage",
            "module",
            "planning_commit",
            "schema_version",
            "seed_rationale",
        },
        "preimplementation",
    )
    if baseline["schema_version"] != R2_PROFILE.preimplementation_schema_version:
        raise DiagnosticBlocked("preimplementation_schema_mismatch")
    if not _canonical_equal(baseline["authority"], ALL_FALSE_AUTHORITY):
        raise DiagnosticBlocked("preimplementation_authority_mismatch")
    if baseline["planning_commit"] != R2_PROFILE.planning_commit:
        raise DiagnosticBlocked("preimplementation_planning_commit_mismatch")
    expected_cohort = {
        "max_decisions_per_replay": MAX_DECISIONS_PER_REPLAY,
        "max_wall_seconds": MAX_WALL_SECONDS,
        "replay_count": REPLAY_COUNT,
        "seeds": list(FIXED_SEEDS),
    }
    if not _canonical_equal(baseline["cohort"], expected_cohort):
        raise DiagnosticBlocked("preimplementation_cohort_mismatch")

    lineage = _mapping(baseline["lineage"], "lineage")
    _require_keys(
        lineage,
        {"anti_retry_decision", "candidate_schema_fix", "consumed_v1"},
        "lineage",
    )
    lineage["anti_retry_decision"] = _validate_relative_binding_path(
        lineage["anti_retry_decision"],
        label="anti_retry_decision",
        expected_path=(
            "reports/noncombat_current_bridge_diagnostic_"
            "successor_eligibility_20260803.md"
        ),
    )

    source_fix = _mapping(lineage["candidate_schema_fix"], "candidate_schema_fix")
    _require_keys(source_fix, {"archive_files", "commit"}, "candidate_schema_fix")
    if source_fix["commit"] != "b0c7ccc0b88a7a847b1119a984b6378032d94b78":
        raise DiagnosticBlocked("candidate_schema_fix_commit_mismatch")
    expected_fix_paths = (
        "openspec/changes/archive/2026-08-03-fix-current-bridge-"
        "diagnostic-candidate-schema/design.md",
        "openspec/changes/archive/2026-08-03-fix-current-bridge-"
        "diagnostic-candidate-schema/proposal.md",
        "openspec/changes/archive/2026-08-03-fix-current-bridge-"
        "diagnostic-candidate-schema/specs/"
        "noncombat-current-bridge-diagnostic-smoke/spec.md",
        "openspec/changes/archive/2026-08-03-fix-current-bridge-"
        "diagnostic-candidate-schema/tasks.md",
    )
    fix_files = _sequence(source_fix["archive_files"], "source fix archive files")
    if len(fix_files) != len(expected_fix_paths):
        raise DiagnosticBlocked("candidate_schema_fix_inventory_mismatch")
    source_fix["archive_files"] = [
        _validate_relative_binding_path(
            row,
            label=f"candidate_schema_fix.archive_files[{index}]",
            expected_path=expected_path,
        )
        for index, (row, expected_path) in enumerate(
            zip(fix_files, expected_fix_paths, strict=True)
        )
    ]
    lineage["candidate_schema_fix"] = source_fix

    consumed = _mapping(lineage["consumed_v1"], "consumed_v1")
    _require_keys(
        consumed,
        {
            "artifacts",
            "closeout",
            "failure",
            "preimplementation",
            "preregistration_commit",
            "registration",
        },
        "consumed_v1",
    )
    if (
        consumed["preregistration_commit"]
        != "b3da176bc6dab63d3e245b9d4159190b7077eab8"
    ):
        raise DiagnosticBlocked("consumed_v1_commit_mismatch")
    consumed["preimplementation"] = _validate_relative_binding_path(
        consumed["preimplementation"],
        label="consumed_v1.preimplementation",
        expected_path=V1_PROFILE.preimplementation_path,
    )
    consumed["registration"] = _validate_relative_binding_path(
        consumed["registration"],
        label="consumed_v1.registration",
        expected_path=V1_PROFILE.registration_path,
    )
    consumed["closeout"] = _validate_relative_binding_path(
        consumed["closeout"],
        label="consumed_v1.closeout",
        expected_path=(
            "reports/noncombat_current_bridge_diagnostic_smoke_"
            "20260803_closeout.md"
        ),
    )
    expected_artifact_paths = tuple(
        f"{V1_PROFILE.output_directory}/{name}"
        for name in CANONICAL_ARTIFACT_NAMES
    )
    artifacts = _sequence(consumed["artifacts"], "consumed_v1.artifacts")
    if len(artifacts) != len(expected_artifact_paths):
        raise DiagnosticBlocked("consumed_v1_artifact_inventory_mismatch")
    consumed["artifacts"] = [
        _validate_relative_binding_path(
            row,
            label=f"consumed_v1.artifacts[{index}]",
            expected_path=expected_path,
        )
        for index, (row, expected_path) in enumerate(
            zip(artifacts, expected_artifact_paths, strict=True)
        )
    ]
    expected_failure = {
        "category_counts": {category: 0 for category in TARGET_CATEGORIES},
        "reason": "diagnostic_execution_failed",
        "retained_rows": 0,
        "status": "failed",
        "support_blocker_count": 0,
        "terminal_row_count": 0,
        "verdict": "current_bridge_diagnostic_failed",
    }
    if not _canonical_equal(consumed["failure"], expected_failure):
        raise DiagnosticBlocked("consumed_v1_failure_mismatch")
    lineage["consumed_v1"] = consumed

    module = _validate_relative_binding_path(
        baseline["module"],
        label="module",
        expected_path=(
            ".sts_lightspeed_adapter_v3_shop_support_build/"
            "sts_lightspeed_noncombat_adapter.cp310-win_amd64.pyd"
        ),
    )
    if (
        module["sha256"] != EXPECTED_MODULE_SHA256
        or module["size_bytes"] != EXPECTED_MODULE_SIZE_BYTES
    ):
        raise DiagnosticBlocked("preimplementation_module_inventory_mismatch")
    baseline["lineage"] = lineage
    baseline["module"] = module
    baseline["seed_rationale"] = _validate_seed_rationale(
        baseline["seed_rationale"]
    )
    return baseline


def validate_preimplementation(
    value: object, *, profile: DiagnosticProfile = V1_PROFILE
) -> dict[str, Any]:
    profile = _coerce_profile(profile)
    if profile == R2_PROFILE:
        return _validate_r2_preimplementation(value)
    baseline = _mapping(value, "preimplementation")
    _require_keys(
        baseline,
        {
            "authority",
            "cohort",
            "module_evidence",
            "planning_commit",
            "schema_version",
            "seed_rationale",
            "tracked_evidence",
        },
        "preimplementation",
    )
    if baseline["schema_version"] != profile.preimplementation_schema_version:
        raise DiagnosticBlocked("preimplementation_schema_mismatch")
    if not _canonical_equal(baseline["authority"], ALL_FALSE_AUTHORITY):
        raise DiagnosticBlocked("preimplementation_authority_mismatch")
    if baseline["planning_commit"] != profile.planning_commit:
        raise DiagnosticBlocked("preimplementation_planning_commit_mismatch")
    expected_cohort = {
        "max_decisions_per_replay": MAX_DECISIONS_PER_REPLAY,
        "max_wall_seconds": MAX_WALL_SECONDS,
        "replay_count": REPLAY_COUNT,
        "seeds": list(FIXED_SEEDS),
    }
    if not _canonical_equal(baseline["cohort"], expected_cohort):
        raise DiagnosticBlocked("preimplementation_cohort_mismatch")

    tracked = _sequence(baseline["tracked_evidence"], "tracked_evidence")
    tracked_ids = tuple(
        row.get("id") for row in tracked if isinstance(row, Mapping)
    )
    if tracked_ids != EXPECTED_TRACKED_EVIDENCE_IDS:
        raise DiagnosticBlocked("preimplementation_tracked_inventory_mismatch")
    normalized_tracked = []
    for index, raw in enumerate(tracked):
        row = _mapping(raw, f"tracked_evidence[{index}]")
        _require_keys(row, {"id", "path", "sha256", "size_bytes"}, "tracked row")
        normalized_tracked.append(
            {
                "id": row["id"],
                **_validate_binding(
                    {key: row[key] for key in ("path", "sha256", "size_bytes")},
                    f"tracked_evidence.{row['id']}",
                    repository_relative=True,
                ),
            }
        )

    modules = _sequence(baseline["module_evidence"], "module_evidence")
    if not _canonical_equal(modules, list(EXPECTED_MODULE_EVIDENCE)):
        raise DiagnosticBlocked("preimplementation_module_inventory_mismatch")

    baseline["tracked_evidence"] = normalized_tracked
    baseline["seed_rationale"] = _validate_seed_rationale(
        baseline["seed_rationale"]
    )
    return baseline


def build_registration(
    *,
    identity: Mapping[str, Any],
    profile: DiagnosticProfile = V1_PROFILE,
) -> dict[str, Any]:
    profile = _coerce_profile(profile)
    registration = {
        "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
        "cohort": {"replay_count": REPLAY_COUNT, "seeds": list(FIXED_SEEDS)},
        "current_policy": copy.deepcopy(CURRENT_POLICY),
        "identity": copy.deepcopy(dict(identity)),
        "limits": {
            "max_decisions_per_replay": MAX_DECISIONS_PER_REPLAY,
            "max_wall_seconds": MAX_WALL_SECONDS,
        },
        "output": {
            "artifact_names": list(CANONICAL_ARTIFACT_NAMES),
            "directory": profile.output_directory,
        },
        "schema_version": profile.input_schema_version,
    }
    return validate_registration(registration, profile=profile)


def validate_registration(
    value: object, *, profile: DiagnosticProfile = V1_PROFILE
) -> dict[str, Any]:
    profile = _coerce_profile(profile)
    registration = _mapping(value, "registration")
    _require_keys(
        registration,
        {
            "authority",
            "cohort",
            "current_policy",
            "identity",
            "limits",
            "output",
            "schema_version",
        },
        "registration",
    )
    if registration["schema_version"] != profile.input_schema_version:
        raise DiagnosticBlocked("registration_schema_mismatch")
    if not _canonical_equal(registration["authority"], ALL_FALSE_AUTHORITY):
        raise DiagnosticBlocked("authority_must_be_all_false")
    if not _canonical_equal(registration["current_policy"], CURRENT_POLICY):
        raise DiagnosticBlocked("current_policy_configuration_mismatch")
    if not _canonical_equal(
        registration["cohort"],
        {"replay_count": REPLAY_COUNT, "seeds": list(FIXED_SEEDS)},
    ):
        raise DiagnosticBlocked("registration_cohort_mismatch")
    if not _canonical_equal(
        registration["limits"],
        {
            "max_decisions_per_replay": MAX_DECISIONS_PER_REPLAY,
            "max_wall_seconds": MAX_WALL_SECONDS,
        },
    ):
        raise DiagnosticBlocked("registration_limits_mismatch")
    if not _canonical_equal(
        registration["output"],
        {
            "artifact_names": list(CANONICAL_ARTIFACT_NAMES),
            "directory": profile.output_directory,
        },
    ):
        raise DiagnosticBlocked("registration_output_mismatch")

    identity = _mapping(registration["identity"], "identity")
    _require_keys(
        identity,
        {
            "adapter_provenance",
            "adapter_source_files",
            "contract",
            "contract_file",
            "implementation",
            "metadata",
            "module_path",
            "preimplementation",
            "runtime",
            "simulator_path",
        },
        "identity",
    )
    identity["adapter_provenance"] = _validate_provenance(
        identity["adapter_provenance"]
    )
    if identity["adapter_source_files"] != list(ADAPTER_SOURCE_FILES):
        raise DiagnosticBlocked("adapter_source_files_mismatch")
    contract = reachable_event_option_semantics_identity()
    if not _canonical_equal(identity["contract"], contract):
        raise DiagnosticBlocked("event_contract_identity_mismatch")
    identity["contract_file"] = _validate_binding(
        identity["contract_file"], "contract_file", repository_relative=True
    )
    contract_binding = contract["observation_contract"]
    if (
        identity["contract_file"]["path"] != contract_binding["path"]
        or identity["contract_file"]["sha256"] != contract_binding["sha256"]
    ):
        raise DiagnosticBlocked("event_contract_binding_mismatch")

    implementation = _mapping(identity["implementation"], "implementation")
    _require_keys(
        implementation,
        {"commit", "source_files", "source_sha256"},
        "implementation",
    )
    if (
        not _is_hex(implementation["commit"], 40)
        or implementation["source_files"]
        != list(profile.implementation_source_files)
        or not _is_hex(implementation["source_sha256"], 64)
    ):
        raise DiagnosticBlocked("implementation_identity_mismatch")
    identity["implementation"] = implementation
    identity["metadata"] = _validate_binding(
        identity["metadata"], "metadata", repository_relative=False
    )
    if not isinstance(identity["module_path"], str) or not Path(
        identity["module_path"]
    ).is_absolute():
        raise DiagnosticBlocked("module_path_not_absolute")
    if not isinstance(identity["simulator_path"], str) or not Path(
        identity["simulator_path"]
    ).is_absolute():
        raise DiagnosticBlocked("simulator_path_not_absolute")
    identity["preimplementation"] = _validate_binding(
        identity["preimplementation"],
        "preimplementation",
        repository_relative=True,
    )
    if not _canonical_equal(
        identity["preimplementation"],
        {
            "path": profile.preimplementation_path,
            "sha256": profile.preimplementation_sha256,
            "size_bytes": profile.preimplementation_size_bytes,
        },
    ):
        raise DiagnosticBlocked("preimplementation_binding_mismatch")
    runtime = _mapping(identity["runtime"], "runtime")
    _require_keys(runtime, {"executable", "python"}, "runtime")
    if (
        not isinstance(runtime["executable"], str)
        or not Path(runtime["executable"]).is_absolute()
        or not isinstance(runtime["python"], str)
        or not runtime["python"]
    ):
        raise DiagnosticBlocked("runtime_identity_invalid")
    identity["runtime"] = runtime
    registration["identity"] = identity
    return registration


def _reject_duplicate_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise DiagnosticBlocked("duplicate_json_key", key)
        result[key] = value
    return result


def _load_json(path: Path | str, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            Path(path).read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
        )
    except DiagnosticBlocked:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DiagnosticBlocked(
            "cannot_load_json", {"error": str(exc), "label": label}
        ) from exc
    return _mapping(value, label)


def load_registration(
    path: Path | str, *, profile: DiagnosticProfile = V1_PROFILE
) -> dict[str, Any]:
    return validate_registration(
        _load_json(path, "registration"), profile=profile
    )


def _verify_binding(
    *, repo_root: Path, binding: Mapping[str, Any], repository_relative: bool
) -> Path:
    path = (
        (repo_root / str(binding["path"])).resolve()
        if repository_relative
        else Path(str(binding["path"])).resolve()
    )
    if not path.is_file():
        raise DiagnosticBlocked("bound_file_missing", binding["path"])
    if path.stat().st_size != binding["size_bytes"]:
        raise DiagnosticBlocked("bound_file_size_mismatch", binding["path"])
    if sha256_file(path) != binding["sha256"]:
        raise DiagnosticBlocked("bound_file_hash_mismatch", binding["path"])
    return path


def validate_preimplementation_file(
    path: Path | str,
    *,
    repo_root: Path | str,
    profile: DiagnosticProfile = V1_PROFILE,
) -> dict[str, Any]:
    profile = _coerce_profile(profile)
    root = Path(repo_root).resolve()
    source = Path(path).resolve()
    expected = (root / profile.preimplementation_path).resolve()
    if source != expected:
        raise DiagnosticBlocked("preimplementation_path_mismatch")
    raw = source.read_bytes()
    if (
        len(raw) != profile.preimplementation_size_bytes
        or sha256_bytes(raw) != profile.preimplementation_sha256
    ):
        raise DiagnosticBlocked("preimplementation_file_identity_mismatch")
    baseline = validate_preimplementation(
        _load_json(source, "preimplementation"), profile=profile
    )
    if raw != canonical_json_bytes(baseline):
        raise DiagnosticBlocked("preimplementation_not_canonical")
    if profile == V1_PROFILE:
        for row in baseline["tracked_evidence"]:
            _verify_binding(repo_root=root, binding=row, repository_relative=True)
        for row in baseline["module_evidence"]:
            _verify_binding(repo_root=root, binding=row, repository_relative=True)
        return baseline

    lineage = baseline["lineage"]
    consumed = lineage["consumed_v1"]
    bindings = [
        lineage["anti_retry_decision"],
        *lineage["candidate_schema_fix"]["archive_files"],
        consumed["preimplementation"],
        consumed["registration"],
        consumed["closeout"],
        *consumed["artifacts"],
        baseline["module"],
    ]
    for row in bindings:
        _verify_binding(repo_root=root, binding=row, repository_relative=True)
    validate_preimplementation_file(
        root / consumed["preimplementation"]["path"],
        repo_root=root,
        profile=V1_PROFILE,
    )
    v1_registration_path = root / consumed["registration"]["path"]
    v1_registration = load_registration(
        v1_registration_path, profile=V1_PROFILE
    )
    manifest = verify_artifact_directory(
        registration=v1_registration,
        registration_sha256=sha256_file(v1_registration_path),
        output_directory=root / V1_PROFILE.output_directory,
        profile=V1_PROFILE,
    )
    v1_result = _mapping(
        _load_json(
            root / V1_PROFILE.output_directory / "trajectory_rows.json",
            "consumed v1 trajectories",
        ).get("result"),
        "consumed v1 result",
    )
    actual_failure = {
        "category_counts": copy.deepcopy(v1_result.get("category_counts")),
        "reason": v1_result.get("reason"),
        "retained_rows": len(_sequence(v1_result.get("rows"), "consumed rows")),
        "status": v1_result.get("status"),
        "support_blocker_count": v1_result.get("support_blocker_count"),
        "terminal_row_count": v1_result.get("terminal_row_count"),
        "verdict": v1_result.get("verdict"),
    }
    if (
        manifest["verdict"] != consumed["failure"]["verdict"]
        or not _canonical_equal(actual_failure, consumed["failure"])
    ):
        raise DiagnosticBlocked("consumed_v1_failure_mismatch")
    fix_commit = lineage["candidate_schema_fix"]["commit"]
    for row in lineage["candidate_schema_fix"]["archive_files"]:
        committed = _git_bytes(root, "show", f"{fix_commit}:{row['path']}")
        if (
            len(committed) != row["size_bytes"]
            or sha256_bytes(committed) != row["sha256"]
        ):
            raise DiagnosticBlocked("candidate_schema_fix_commit_mismatch")
    return baseline


def validate_registration_evidence(
    registration: Mapping[str, Any],
    repo_root: Path | str,
    *,
    profile: DiagnosticProfile = V1_PROFILE,
) -> MetadataCatalog:
    profile = _coerce_profile(profile)
    normalized = validate_registration(
        copy.deepcopy(registration), profile=profile
    )
    root = Path(repo_root).resolve()
    identity = normalized["identity"]
    preimplementation_path = _verify_binding(
        repo_root=root,
        binding=identity["preimplementation"],
        repository_relative=True,
    )
    validate_preimplementation_file(
        preimplementation_path, repo_root=root, profile=profile
    )
    contract_path = _verify_binding(
        repo_root=root,
        binding=identity["contract_file"],
        repository_relative=True,
    )
    if sha256_file(contract_path) != identity["contract"]["observation_contract"][
        "sha256"
    ]:
        raise DiagnosticBlocked("event_contract_binding_mismatch")
    implementation = identity["implementation"]
    if hash_bound_files(root, implementation["source_files"]) != implementation[
        "source_sha256"
    ]:
        raise DiagnosticBlocked("implementation_source_hash_mismatch")
    try:
        predecessor.predecessor._verify_sources_at_commit(
            root, implementation["commit"], implementation["source_files"]
        )
        predecessor.predecessor._verify_sources_at_commit(
            root, EXPECTED_ADAPTER_COMMIT, ADAPTER_SOURCE_FILES
        )
    except predecessor.predecessor.CompatibilityBlocked as exc:
        raise DiagnosticBlocked(exc.reason, exc.detail) from exc
    if not _canonical_equal(
        identity["runtime"],
        {
            "executable": str(Path(sys.executable).resolve()),
            "python": sys.version.split()[0],
        },
    ):
        raise DiagnosticBlocked("runtime_identity_mismatch")
    metadata_path = _verify_binding(
        repo_root=root, binding=identity["metadata"], repository_relative=False
    )
    module_path = Path(identity["module_path"]).resolve()
    provenance = identity["adapter_provenance"]
    if (
        not module_path.is_file()
        or module_path.stat().st_size != provenance["module_size_bytes"]
        or sha256_file(module_path) != provenance["module_sha256"]
    ):
        raise DiagnosticBlocked("native_module_binding_mismatch")
    return MetadataCatalog(metadata_path)


def _git_bytes(repo_root: Path, *args: str) -> bytes:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise DiagnosticBlocked("git_command_failed", list(args)) from exc
    return completed.stdout


def _git_text(repo_root: Path, *args: str) -> str:
    return _git_bytes(repo_root, *args).decode("utf-8").strip()


def _assert_clean_pushed_head(repo_root: Path) -> str:
    if _git_text(repo_root, "status", "--porcelain", "--untracked-files=no"):
        raise DiagnosticBlocked("tracked_tree_dirty")
    head = _git_text(repo_root, "rev-parse", "HEAD")
    origin = _git_text(repo_root, "rev-parse", "origin/master")
    if head != origin:
        raise DiagnosticBlocked(
            "head_not_pushed", {"head": head, "origin_master": origin}
        )
    if not _is_hex(head, 40):
        raise DiagnosticBlocked("head_commit_invalid", head)
    return head


def assert_pushed_registration(
    *,
    registration_path: Path | str,
    repo_root: Path | str,
    profile: DiagnosticProfile = V1_PROFILE,
) -> dict[str, Any]:
    profile = _coerce_profile(profile)
    root = Path(repo_root).resolve()
    path = Path(registration_path).resolve()
    expected = (root / profile.registration_path).resolve()
    if path != expected or not path.is_file():
        raise DiagnosticBlocked("registration_path_mismatch")
    registration = load_registration(path, profile=profile)
    if (root / registration["output"]["directory"]).exists():
        raise DiagnosticBlocked("output_directory_already_exists")
    head = _assert_clean_pushed_head(root)
    relative = path.relative_to(root).as_posix()
    committed = _git_bytes(root, "show", f"{head}:{relative}")
    actual = path.read_bytes()
    if committed != actual:
        raise DiagnosticBlocked("pushed_registration_mismatch")
    return {
        "preregistration_commit": head,
        "registration_sha256": sha256_bytes(actual),
    }


def _preserved_detail(detail: object | None) -> object | None:
    try:
        canonical_json_bytes({"detail": detail})
        return copy.deepcopy(detail)
    except (TypeError, ValueError):
        return {"repr": repr(detail), "type": type(detail).__name__}


def _make_replay_row(
    *,
    seed: int,
    disposition: str,
    decisions: list[dict[str, Any]],
    event_identities: list[dict[str, Any]],
    category_counts: Counter,
    last_supported_floor: int | None,
    last_supported_decision_index: int | None,
    terminal_floor: int | None,
    outcome: str | None,
    support_reason: str | None,
) -> dict[str, Any]:
    row = {
        "category_counts": {
            category: category_counts[category] for category in TARGET_CATEGORIES
        },
        "decision_count": len(decisions),
        "decisions": decisions,
        "disposition": disposition,
        "event_identities": event_identities,
        "last_supported_decision_index": last_supported_decision_index,
        "last_supported_floor": last_supported_floor,
        "outcome": outcome,
        "seed": seed,
        "support_reason": support_reason,
        "terminal_floor": terminal_floor,
    }
    row["trajectory_sha256"] = sha256_bytes(canonical_json_bytes(row))
    return row


def _declared_support_row(
    *,
    seed: int,
    decisions: list[dict[str, Any]],
    event_identities: list[dict[str, Any]],
    category_counts: Counter,
    last_supported_floor: int | None,
    last_supported_decision_index: int | None,
) -> dict[str, Any]:
    return _make_replay_row(
        seed=seed,
        disposition="declared_support_blocked",
        decisions=decisions,
        event_identities=event_identities,
        category_counts=category_counts,
        last_supported_floor=last_supported_floor,
        last_supported_decision_index=last_supported_decision_index,
        terminal_floor=None,
        outcome=None,
        support_reason=DECLARED_SUPPORT_REASON,
    )


def _is_declared_support_exception(exc: BaseException) -> bool:
    return type(exc) is RuntimeError and str(exc) == DECLARED_SUPPORT_REASON


def _run_replay(
    *,
    environment: Any,
    session: Any,
    seed: int,
    max_decisions: int,
    deadline: float,
    monotonic: Callable[[], float],
) -> dict[str, Any]:
    decisions: list[dict[str, Any]] = []
    category_counts = Counter()
    event_identities: list[dict[str, Any]] = []
    last_floor = None
    last_decision_index = None
    while True:
        if monotonic() > deadline:
            raise DiagnosticBlocked("execution_deadline_exceeded")
        try:
            snapshot = _mapping(environment.snapshot(), "native snapshot")
        except DiagnosticBlocked:
            raise
        except Exception as exc:
            if _is_declared_support_exception(exc):
                return _declared_support_row(
                    seed=seed,
                    decisions=decisions,
                    event_identities=event_identities,
                    category_counts=category_counts,
                    last_supported_floor=last_floor,
                    last_supported_decision_index=last_decision_index,
                )
            raise DiagnosticBlocked(
                "native_snapshot_failed",
                {"message": str(exc), "type": type(exc).__name__},
            ) from exc
        if snapshot.get("terminal") is True:
            break
        if len(decisions) >= max_decisions:
            raise DiagnosticBlocked(
                "decision_limit_exceeded", {"limit": max_decisions, "seed": seed}
            )
        state = _mapping(snapshot.get("state"), "native snapshot.state")
        if state.get("seed") != str(seed):
            raise DiagnosticBlocked("environment_seed_mismatch", seed)
        floor = state.get("floor")
        decision_index = snapshot.get("decision_count")
        if (
            isinstance(floor, bool)
            or not isinstance(floor, int)
            or isinstance(decision_index, bool)
            or not isinstance(decision_index, int)
        ):
            raise DiagnosticBlocked(
                "decision_coordinates_invalid",
                {"decision_index": decision_index, "floor": floor},
            )
        last_floor = floor
        last_decision_index = decision_index
        category = snapshot.get("category")
        if category not in TARGET_CATEGORIES:
            raise DiagnosticBlocked("target_category_invalid", category)
        try:
            candidates = validate_candidates(
                environment.legal_actions(), category=category
            )
        except (SimulatorAdapterError, TypeError, ValueError) as exc:
            raise DiagnosticBlocked("legal_actions_invalid", str(exc)) from exc
        except Exception as exc:
            if _is_declared_support_exception(exc):
                return _declared_support_row(
                    seed=seed,
                    decisions=decisions,
                    event_identities=event_identities,
                    category_counts=category_counts,
                    last_supported_floor=last_floor,
                    last_supported_decision_index=last_decision_index,
                )
            raise DiagnosticBlocked(
                "native_legal_actions_failed",
                {"message": str(exc), "type": type(exc).__name__},
            ) from exc
        before_snapshot = canonical_json_bytes(snapshot)
        before_candidates = canonical_json_bytes(candidates)
        try:
            evaluation = _mapping(
                session.evaluate(
                    snapshot=snapshot,
                    candidates=candidates,
                    decision_index=decision_index,
                ),
                "Current evaluation",
            )
        except BridgeBlocked as exc:
            raise DiagnosticBlocked(exc.reason, exc.detail) from exc
        except DiagnosticBlocked:
            raise
        except Exception as exc:
            raise DiagnosticBlocked(
                "current_policy_evaluation_failed",
                {"message": str(exc), "type": type(exc).__name__},
            ) from exc
        if canonical_json_bytes(snapshot) != before_snapshot:
            raise DiagnosticBlocked("source_snapshot_mutated")
        if canonical_json_bytes(candidates) != before_candidates:
            raise DiagnosticBlocked("source_candidates_mutated")
        if (
            evaluation.get("category") != category
            or evaluation.get("policy_id") != POLICY_ID
            or not isinstance(evaluation.get("action_type"), str)
            or not evaluation["action_type"]
            or evaluation.get("fallback_used") is not False
            or evaluation.get("tracker_enabled") is not False
            or evaluation.get("source_mutated") is not False
        ):
            raise DiagnosticBlocked("current_evaluation_contract_invalid", evaluation)
        snapshot_sha256 = sha256_bytes(before_snapshot)
        candidates_sha256 = sha256_bytes(before_candidates)
        if (
            evaluation.get("input_snapshot_sha256") != snapshot_sha256
            or evaluation.get("input_candidates_sha256") != candidates_sha256
        ):
            raise DiagnosticBlocked("policy_input_hash_mismatch")
        action_id = evaluation.get("action_id")
        matches = [
            candidate for candidate in candidates if candidate["action_id"] == action_id
        ]
        if len(matches) != 1:
            raise DiagnosticBlocked("selected_action_not_unique_candidate", action_id)
        event_observation = None
        if category == "event":
            try:
                event_observation = predecessor._event_diagnostic(
                    evaluation, matches[0], candidates, snapshot
                )
            except predecessor.CompatibilityBlocked as exc:
                raise DiagnosticBlocked(exc.reason, exc.detail) from exc
        try:
            transition = _mapping(environment.step(action_id), "native transition")
        except Exception as exc:
            if _is_declared_support_exception(exc):
                return _declared_support_row(
                    seed=seed,
                    decisions=decisions,
                    event_identities=event_identities,
                    category_counts=category_counts,
                    last_supported_floor=last_floor,
                    last_supported_decision_index=last_decision_index,
                )
            raise DiagnosticBlocked(
                "native_step_failed",
                {"message": str(exc), "type": type(exc).__name__},
            ) from exc
        if transition.get("selected_action_id") != action_id:
            raise DiagnosticBlocked("transition_action_mismatch", action_id)
        if event_observation is not None:
            event_identities.append(copy.deepcopy(event_observation))
        decisions.append(
            {
                "action_id": action_id,
                "action_type": evaluation["action_type"],
                "candidate_actions_sha256": candidates_sha256,
                "category": category,
                "decision_index": decision_index,
                "event_observation": event_observation,
                "policy_input_sha256": sha256_bytes(
                    canonical_json_bytes(
                        {
                            "candidates": evaluation.get(
                                "input_candidates_sha256"
                            ),
                            "snapshot": evaluation.get("input_snapshot_sha256"),
                        }
                    )
                ),
                "source_snapshot_sha256": snapshot_sha256,
            }
        )
        category_counts[category] += 1

    state = _mapping(snapshot.get("state"), "terminal state")
    terminal_floor = state.get("floor")
    outcome = state.get("outcome")
    if (
        state.get("seed") != str(seed)
        or isinstance(terminal_floor, bool)
        or not isinstance(terminal_floor, int)
        or terminal_floor < 0
        or outcome not in {"player_loss", "player_victory"}
    ):
        raise DiagnosticBlocked(
            "terminal_state_invalid",
            {
                "floor": terminal_floor,
                "outcome": outcome,
                "seed": state.get("seed"),
            },
        )
    return _make_replay_row(
        seed=seed,
        disposition="terminal",
        decisions=decisions,
        event_identities=event_identities,
        category_counts=category_counts,
        last_supported_floor=last_floor,
        last_supported_decision_index=last_decision_index,
        terminal_floor=terminal_floor,
        outcome=outcome,
        support_reason=None,
    )


def _counts_for_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts = Counter()
    for row in rows:
        counts.update(row["category_counts"])
    return {category: counts[category] for category in TARGET_CATEGORIES}


def _failed_result(
    *,
    reason: str,
    detail: object | None,
    rows: list[dict[str, Any]],
    profile: DiagnosticProfile = V1_PROFILE,
) -> dict[str, Any]:
    profile = _coerce_profile(profile)
    terminal_count = sum(row["disposition"] == "terminal" for row in rows)
    support_count = sum(
        row["disposition"] == "declared_support_blocked" for row in rows
    )
    return {
        "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
        "category_counts": _counts_for_rows(rows),
        "detail": _preserved_detail(detail),
        "reason": reason,
        "rows": rows,
        "schema_version": profile.execution_schema_version,
        "seeds": list(FIXED_SEEDS),
        "status": "failed",
        "support_blocker_count": support_count,
        "terminal_row_count": terminal_count,
        "verdict": "current_bridge_diagnostic_failed",
    }


def run_diagnostic(
    *,
    registration: Mapping[str, Any],
    environment_factory: Callable[[int], Any],
    session_factory: Callable[[], Any],
    monotonic: Callable[[], float] = time.monotonic,
    profile: DiagnosticProfile = V1_PROFILE,
) -> dict[str, Any]:
    profile = _coerce_profile(profile)
    normalized = validate_registration(
        copy.deepcopy(registration), profile=profile
    )
    deadline = monotonic() + normalized["limits"]["max_wall_seconds"]
    rows: list[dict[str, Any]] = []
    try:
        for seed in FIXED_SEEDS:
            replays = []
            for _ in range(REPLAY_COUNT):
                if monotonic() > deadline:
                    raise DiagnosticBlocked("execution_deadline_exceeded")
                try:
                    environment = environment_factory(seed)
                    session = session_factory()
                except KeyboardInterrupt:
                    raise
                except Exception as exc:
                    raise DiagnosticBlocked(
                        "environment_construction_failed",
                        {"message": str(exc), "type": type(exc).__name__},
                    ) from exc
                replays.append(
                    _run_replay(
                        environment=environment,
                        session=session,
                        seed=seed,
                        max_decisions=MAX_DECISIONS_PER_REPLAY,
                        deadline=deadline,
                        monotonic=monotonic,
                    )
                )
            if replays[0]["disposition"] != replays[1]["disposition"]:
                raise DiagnosticBlocked(
                    "replay_disposition_mismatch",
                    {
                        "first": replays[0]["disposition"],
                        "second": replays[1]["disposition"],
                        "seed": seed,
                    },
                )
            if canonical_json_bytes(replays[0]) != canonical_json_bytes(replays[1]):
                raise DiagnosticBlocked(
                    "trajectory_nondeterministic",
                    {
                        "first": replays[0]["trajectory_sha256"],
                        "second": replays[1]["trajectory_sha256"],
                        "seed": seed,
                    },
                )
            rows.append({**replays[0], "replay_count": REPLAY_COUNT})

        category_counts = _counts_for_rows(rows)
        terminal_count = sum(row["disposition"] == "terminal" for row in rows)
        support_count = len(rows) - terminal_count
        if terminal_count == 0:
            return {
                "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
                "category_counts": category_counts,
                "detail": None,
                "reason": None,
                "rows": rows,
                "schema_version": profile.execution_schema_version,
                "seeds": list(FIXED_SEEDS),
                "status": "support_limited",
                "support_blocker_count": support_count,
                "terminal_row_count": 0,
                "verdict": "current_bridge_diagnostic_support_limited",
            }
        missing = [
            category for category, count in category_counts.items() if count <= 0
        ]
        if missing:
            return _failed_result(
                reason="aggregate_category_coverage_missing",
                detail=missing,
                rows=rows,
                profile=profile,
            )
        return {
            "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
            "category_counts": category_counts,
            "detail": None,
            "reason": None,
            "rows": rows,
            "schema_version": profile.execution_schema_version,
            "seeds": list(FIXED_SEEDS),
            "status": "passed",
            "support_blocker_count": support_count,
            "terminal_row_count": terminal_count,
            "verdict": "current_bridge_diagnostic_passed",
        }
    except KeyboardInterrupt:
        raise
    except DiagnosticBlocked as exc:
        return _failed_result(
            reason=exc.reason,
            detail=exc.detail,
            rows=rows,
            profile=profile,
        )
    except Exception as exc:
        return _failed_result(
            reason="diagnostic_execution_failed",
            detail={"message": str(exc), "type": type(exc).__name__},
            rows=rows,
            profile=profile,
        )


def _validate_result_row(
    value: object, *, expected_seed: int, row_index: int
) -> dict[str, Any]:
    row = _mapping(value, f"row[{row_index}]")
    _require_keys(
        row,
        {
            "category_counts",
            "decision_count",
            "decisions",
            "disposition",
            "event_identities",
            "last_supported_decision_index",
            "last_supported_floor",
            "outcome",
            "replay_count",
            "seed",
            "support_reason",
            "terminal_floor",
            "trajectory_sha256",
        },
        f"row[{row_index}]",
    )
    if (
        isinstance(row["seed"], bool)
        or not isinstance(row["seed"], int)
        or row["seed"] != expected_seed
        or isinstance(row["replay_count"], bool)
        or not isinstance(row["replay_count"], int)
        or row["replay_count"] != REPLAY_COUNT
    ):
        raise DiagnosticBlocked("execution_row_identity_mismatch", row_index)
    decisions = _sequence(row["decisions"], f"row[{row_index}].decisions")
    event_identities = _sequence(
        row["event_identities"], f"row[{row_index}].event_identities"
    )
    if (
        isinstance(row["decision_count"], bool)
        or not isinstance(row["decision_count"], int)
        or row["decision_count"] < 0
        or row["decision_count"] != len(decisions)
        or len(decisions) > MAX_DECISIONS_PER_REPLAY
        or not _is_hex(row["trajectory_sha256"], 64)
    ):
        raise DiagnosticBlocked("execution_row_decision_count_mismatch", row_index)
    recomputed = Counter()
    normalized_decisions = []
    expected_event_identities = []
    previous_decision_index: int | None = None
    for decision_offset, raw_decision in enumerate(decisions):
        normalized_decision = _mapping(
            raw_decision, f"row[{row_index}].decision[{decision_offset}]"
        )
        _require_keys(
            normalized_decision,
            {
                "action_id",
                "action_type",
                "candidate_actions_sha256",
                "category",
                "decision_index",
                "event_observation",
                "policy_input_sha256",
                "source_snapshot_sha256",
            },
            f"row[{row_index}].decision[{decision_offset}]",
        )
        decision_index = normalized_decision["decision_index"]
        if (
            not isinstance(normalized_decision["action_id"], str)
            or not normalized_decision["action_id"]
            or not isinstance(normalized_decision["action_type"], str)
            or not normalized_decision["action_type"]
            or normalized_decision["category"] not in TARGET_CATEGORIES
            or isinstance(decision_index, bool)
            or not isinstance(decision_index, int)
            or decision_index < 0
            or (
                previous_decision_index is not None
                and decision_index <= previous_decision_index
            )
            or any(
                not _is_hex(normalized_decision[field], 64)
                for field in (
                    "candidate_actions_sha256",
                    "policy_input_sha256",
                    "source_snapshot_sha256",
                )
            )
        ):
            raise DiagnosticBlocked(
                "execution_row_decision_invalid",
                {"decision": decision_offset, "row": row_index},
            )
        previous_decision_index = decision_index
        observation = normalized_decision["event_observation"]
        if normalized_decision["category"] == "event":
            observation = _mapping(
                observation,
                f"row[{row_index}].decision[{decision_offset}].event_observation",
            )
            _require_keys(
                observation,
                {
                    "current_event_id",
                    "current_position",
                    "event_data",
                    "selected_action_id",
                    "semantics_source",
                    "simulator_choice_index",
                    "upstream_event_id",
                },
                f"row[{row_index}].decision[{decision_offset}].event_observation",
            )
            if (
                observation["semantics_source"]
                != reachable_event_option_semantics_identity()["contract_id"]
                or observation["selected_action_id"]
                != normalized_decision["action_id"]
                or isinstance(observation["current_position"], bool)
                or not isinstance(observation["current_position"], int)
                or observation["current_position"] < 0
                or isinstance(observation["simulator_choice_index"], bool)
                or not isinstance(observation["simulator_choice_index"], int)
                or observation["simulator_choice_index"] < 0
                or not isinstance(observation["upstream_event_id"], str)
                or not observation["upstream_event_id"]
                or not isinstance(observation["current_event_id"], str)
                or not observation["current_event_id"]
            ):
                raise DiagnosticBlocked(
                    "execution_event_observation_invalid",
                    {"decision": decision_offset, "row": row_index},
                )
            expected_event_identities.append(copy.deepcopy(observation))
        elif observation is not None:
            raise DiagnosticBlocked(
                "execution_non_event_observation_present",
                {"decision": decision_offset, "row": row_index},
            )
        normalized_decisions.append(normalized_decision)
        recomputed[normalized_decision["category"]] += 1
    counts = _mapping(row["category_counts"], "row category counts")
    expected_counts = {
        category: recomputed[category] for category in TARGET_CATEGORIES
    }
    if (
        set(counts) != set(TARGET_CATEGORIES)
        or any(
            isinstance(count, bool) or not isinstance(count, int) or count < 0
            for count in counts.values()
        )
        or counts != expected_counts
    ):
        raise DiagnosticBlocked("execution_row_counts_mismatch", row_index)
    if event_identities != expected_event_identities:
        raise DiagnosticBlocked("execution_row_event_identities_mismatch", row_index)
    disposition = row["disposition"]
    if disposition == "terminal":
        if (
            row["support_reason"] is not None
            or row["outcome"] not in {"player_loss", "player_victory"}
            or isinstance(row["terminal_floor"], bool)
            or not isinstance(row["terminal_floor"], int)
            or row["terminal_floor"] < 0
        ):
            raise DiagnosticBlocked("terminal_row_invalid", row_index)
    elif disposition == "declared_support_blocked":
        if (
            row["support_reason"] != DECLARED_SUPPORT_REASON
            or row["outcome"] is not None
            or row["terminal_floor"] is not None
        ):
            raise DiagnosticBlocked("declared_support_row_invalid", row_index)
    else:
        raise DiagnosticBlocked("execution_row_disposition_invalid", row_index)
    for coordinate in ("last_supported_decision_index", "last_supported_floor"):
        value = row[coordinate]
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, int) or value < 0
        ):
            raise DiagnosticBlocked("execution_row_coordinates_invalid", row_index)
    base = copy.deepcopy(row)
    del base["replay_count"]
    actual_hash = base.pop("trajectory_sha256")
    if actual_hash != sha256_bytes(canonical_json_bytes(base)):
        raise DiagnosticBlocked("trajectory_hash_mismatch", row_index)
    row["decisions"] = normalized_decisions
    row["event_identities"] = event_identities
    return row


def _validate_execution_result(
    value: object,
    registration: Mapping[str, Any],
    *,
    profile: DiagnosticProfile = V1_PROFILE,
) -> dict[str, Any]:
    profile = _coerce_profile(profile)
    validate_registration(copy.deepcopy(registration), profile=profile)
    result = _mapping(value, "execution result")
    _require_keys(
        result,
        {
            "authority",
            "category_counts",
            "detail",
            "reason",
            "rows",
            "schema_version",
            "seeds",
            "status",
            "support_blocker_count",
            "terminal_row_count",
            "verdict",
        },
        "execution result",
    )
    if result["schema_version"] != profile.execution_schema_version:
        raise DiagnosticBlocked("execution_schema_mismatch")
    if not _canonical_equal(result["authority"], ALL_FALSE_AUTHORITY):
        raise DiagnosticBlocked("authority_must_be_all_false")
    if not _canonical_equal(result["seeds"], list(FIXED_SEEDS)):
        raise DiagnosticBlocked("execution_seed_mismatch")
    raw_rows = _sequence(result["rows"], "execution rows")
    if len(raw_rows) > len(FIXED_SEEDS):
        raise DiagnosticBlocked("execution_row_count_exceeded")
    rows = [
        _validate_result_row(
            raw,
            expected_seed=FIXED_SEEDS[index],
            row_index=index,
        )
        for index, raw in enumerate(raw_rows)
    ]
    counts = _mapping(result["category_counts"], "category counts")
    if (
        set(counts) != set(TARGET_CATEGORIES)
        or any(
            isinstance(count, bool) or not isinstance(count, int) or count < 0
            for count in counts.values()
        )
        or counts != _counts_for_rows(rows)
    ):
        raise DiagnosticBlocked("execution_aggregate_counts_mismatch")
    terminal_count = sum(row["disposition"] == "terminal" for row in rows)
    support_count = sum(
        row["disposition"] == "declared_support_blocked" for row in rows
    )
    if any(
        isinstance(count, bool) or not isinstance(count, int) or count < 0
        for count in (
            result["terminal_row_count"],
            result["support_blocker_count"],
        )
    ) or (
        result["terminal_row_count"] != terminal_count
        or result["support_blocker_count"] != support_count
    ):
        raise DiagnosticBlocked("execution_disposition_counts_mismatch")
    complete = len(rows) == len(FIXED_SEEDS)
    missing_categories = [
        category for category, count in counts.items() if count <= 0
    ]
    if complete and terminal_count == 0:
        if (
            result["status"] != "support_limited"
            or result["verdict"]
            != "current_bridge_diagnostic_support_limited"
            or result["reason"] is not None
            or result["detail"] is not None
            or support_count != len(FIXED_SEEDS)
        ):
            raise DiagnosticBlocked("execution_verdict_precedence_invalid")
    elif complete and not missing_categories:
        if (
            result["status"] != "passed"
            or result["verdict"] != "current_bridge_diagnostic_passed"
            or result["reason"] is not None
            or result["detail"] is not None
            or terminal_count <= 0
        ):
            raise DiagnosticBlocked("execution_verdict_precedence_invalid")
    elif complete:
        if (
            result["status"] != "failed"
            or result["verdict"] != "current_bridge_diagnostic_failed"
            or result["reason"] != "aggregate_category_coverage_missing"
            or result["detail"] != missing_categories
        ):
            raise DiagnosticBlocked("execution_verdict_precedence_invalid")
    else:
        if (
            result["status"] != "failed"
            or result["verdict"] != "current_bridge_diagnostic_failed"
            or not isinstance(result["reason"], str)
            or not result["reason"]
            or result["reason"] == "aggregate_category_coverage_missing"
        ):
            raise DiagnosticBlocked("execution_verdict_precedence_invalid")
    result["rows"] = rows
    return result


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def _started_journal(
    *,
    registration_sha256: str,
    preregistration_commit: str,
    profile: DiagnosticProfile = V1_PROFILE,
) -> dict[str, Any]:
    profile = _coerce_profile(profile)
    return {
        "attempted_seeds": list(FIXED_SEEDS),
        "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
        "preregistration_commit": preregistration_commit,
        "registration_sha256": registration_sha256,
        "result_sha256": None,
        "schema_version": profile.journal_schema_version,
        "status": "started",
        "verdict": None,
    }


def _report_markdown(result: Mapping[str, Any]) -> bytes:
    lines = [
        "# Current Bridge Diagnostic Smoke",
        "",
        f"- Status: `{result['status']}`",
        f"- Verdict: `{result['verdict']}`",
        f"- Reason: `{result['reason']}`",
        f"- Terminal rows: `{result['terminal_row_count']}`",
        f"- Declared support rows: `{result['support_blocker_count']}`",
        "- Authority: reused-seed structural diagnostics only; every downstream flag is false.",
        "",
        "## Rows",
        "",
    ]
    for row in result["rows"]:
        lines.append(
            f"- Seed `{row['seed']}`: `{row['disposition']}`, decisions "
            f"`{row['decision_count']}`"
        )
    lines.extend(["", "## Category Counts", ""])
    for category in TARGET_CATEGORIES:
        lines.append(f"- {category}: `{result['category_counts'][category]}`")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "This result does not authorize fresh evidence, a baseline floor, policy",
            "quality, gameplay, reward, OPE, formal RL, training, qualification,",
            "policy/model loading, or promotion.",
            "",
        ]
    )
    return "\n".join(lines).encode("utf-8")


def _deterministic_payloads(
    *,
    registration: Mapping[str, Any],
    registration_sha256: str,
    preregistration_commit: str,
    result: Mapping[str, Any],
    profile: DiagnosticProfile = V1_PROFILE,
) -> dict[str, bytes]:
    profile = _coerce_profile(profile)
    normalized_registration = validate_registration(
        copy.deepcopy(registration), profile=profile
    )
    normalized_result = _validate_execution_result(
        result, normalized_registration, profile=profile
    )
    result_sha256 = sha256_bytes(canonical_json_bytes(normalized_result))
    journal = {
        **_started_journal(
            registration_sha256=registration_sha256,
            preregistration_commit=preregistration_commit,
            profile=profile,
        ),
        "result_sha256": result_sha256,
        "status": "finalized",
        "verdict": normalized_result["verdict"],
    }
    configuration = {
        "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
        "preregistration_commit": preregistration_commit,
        "registration": normalized_registration,
        "registration_sha256": registration_sha256,
        "schema_version": profile.configuration_schema_version,
    }
    metrics = {
        "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
        "category_counts": copy.deepcopy(normalized_result["category_counts"]),
        "reason": copy.deepcopy(normalized_result["reason"]),
        "registration_sha256": registration_sha256,
        "schema_version": profile.metrics_schema_version,
        "seeds": list(FIXED_SEEDS),
        "status": normalized_result["status"],
        "support_blocker_count": normalized_result["support_blocker_count"],
        "terminal_row_count": normalized_result["terminal_row_count"],
        "verdict": normalized_result["verdict"],
    }
    trajectories = {
        "result": normalized_result,
        "schema_version": profile.trajectory_schema_version,
    }
    return {
        "configuration.json": canonical_json_bytes(configuration),
        "execution_journal.json": canonical_json_bytes(journal),
        "metrics.json": canonical_json_bytes(metrics),
        "report.md": _report_markdown(normalized_result),
        "trajectory_rows.json": canonical_json_bytes(trajectories),
    }


def _artifact_binding(name: str, payload: bytes) -> dict[str, Any]:
    return {"path": name, "sha256": sha256_bytes(payload), "size_bytes": len(payload)}


def _build_manifest(
    *,
    registration_sha256: str,
    result: Mapping[str, Any],
    payloads: Mapping[str, bytes],
    profile: DiagnosticProfile = V1_PROFILE,
) -> bytes:
    profile = _coerce_profile(profile)
    manifest = {
        "artifact_bindings": {
            name: _artifact_binding(name, payload)
            for name, payload in sorted(payloads.items())
        },
        "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
        "registration_sha256": registration_sha256,
        "schema_version": profile.manifest_schema_version,
        "status": result["status"],
        "verdict": result["verdict"],
    }
    return canonical_json_bytes(manifest)


def consume_and_run(
    *,
    registration: Mapping[str, Any],
    registration_sha256: str,
    preregistration_commit: str,
    output_directory: Path | str,
    environment_factory: Callable[[int], Any],
    session_factory: Callable[[], Any],
    monotonic: Callable[[], float] = time.monotonic,
    profile: DiagnosticProfile = V1_PROFILE,
) -> dict[str, Any]:
    profile = _coerce_profile(profile)
    normalized = validate_registration(
        copy.deepcopy(registration), profile=profile
    )
    if not _is_hex(registration_sha256, 64) or not _is_hex(
        preregistration_commit, 40
    ):
        raise DiagnosticBlocked("execution_identity_invalid")
    output = Path(output_directory).resolve()
    if output.exists():
        raise DiagnosticBlocked("output_directory_already_exists", str(output))
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        output.mkdir()
    except FileExistsError as exc:
        raise DiagnosticBlocked("output_directory_already_exists", str(output)) from exc
    started = _started_journal(
        registration_sha256=registration_sha256,
        preregistration_commit=preregistration_commit,
        profile=profile,
    )
    _write_atomic(output / "execution_journal.json", canonical_json_bytes(started))
    result = run_diagnostic(
        registration=normalized,
        environment_factory=environment_factory,
        session_factory=session_factory,
        monotonic=monotonic,
        profile=profile,
    )
    payloads = _deterministic_payloads(
        registration=normalized,
        registration_sha256=registration_sha256,
        preregistration_commit=preregistration_commit,
        result=result,
        profile=profile,
    )
    for name, payload in payloads.items():
        _write_atomic(output / name, payload)
    manifest = _build_manifest(
        registration_sha256=registration_sha256,
        result=result,
        payloads=payloads,
        profile=profile,
    )
    _write_atomic(output / "artifact_manifest.json", manifest)
    return result


def verify_artifact_directory(
    *,
    registration: Mapping[str, Any],
    registration_sha256: str,
    output_directory: Path | str,
    profile: DiagnosticProfile = V1_PROFILE,
) -> dict[str, Any]:
    profile = _coerce_profile(profile)
    normalized = validate_registration(
        copy.deepcopy(registration), profile=profile
    )
    output = Path(output_directory).resolve()
    if not output.is_dir():
        raise DiagnosticBlocked("artifact_directory_missing", str(output))
    actual_names = sorted(path.name for path in output.iterdir())
    if actual_names != sorted(CANONICAL_ARTIFACT_NAMES):
        raise DiagnosticBlocked(
            "artifact_inventory_mismatch",
            {"actual": actual_names, "expected": sorted(CANONICAL_ARTIFACT_NAMES)},
        )
    configuration = _load_json(output / "configuration.json", "configuration")
    if (
        configuration.get("schema_version")
        != profile.configuration_schema_version
        or not _canonical_equal(configuration.get("registration"), normalized)
        or configuration.get("registration_sha256") != registration_sha256
        or not _canonical_equal(
            configuration.get("authority"), ALL_FALSE_AUTHORITY
        )
        or not _is_hex(configuration.get("preregistration_commit"), 40)
    ):
        raise DiagnosticBlocked("configuration_invalid")
    trajectories = _load_json(output / "trajectory_rows.json", "trajectories")
    if trajectories.get("schema_version") != profile.trajectory_schema_version:
        raise DiagnosticBlocked("trajectory_artifact_schema_mismatch")
    result = _validate_execution_result(
        trajectories.get("result"), normalized, profile=profile
    )
    payloads = _deterministic_payloads(
        registration=normalized,
        registration_sha256=registration_sha256,
        preregistration_commit=configuration["preregistration_commit"],
        result=result,
        profile=profile,
    )
    for name, expected in payloads.items():
        if (output / name).read_bytes() != expected:
            raise DiagnosticBlocked("artifact_recomputation_mismatch", name)
    expected_manifest = _build_manifest(
        registration_sha256=registration_sha256,
        result=result,
        payloads=payloads,
        profile=profile,
    )
    if (output / "artifact_manifest.json").read_bytes() != expected_manifest:
        raise DiagnosticBlocked("artifact_recomputation_mismatch", "artifact_manifest.json")
    return _load_json(output / "artifact_manifest.json", "manifest")


def prepare_registration(
    *,
    repo_root: Path | str,
    module_path: Path | str,
    simulator_repo: Path | str,
    metadata_path: Path | str,
    dll_directories: Sequence[Path | str] = (),
    profile: DiagnosticProfile = V1_PROFILE,
) -> dict[str, Any]:
    profile = _coerce_profile(profile)
    root = Path(repo_root).resolve()
    native_path = Path(module_path).resolve()
    simulator_path = Path(simulator_repo).resolve()
    metadata = Path(metadata_path).resolve()
    implementation_commit = _assert_clean_pushed_head(root)
    registration_path = root / profile.registration_path
    output_path = root / profile.output_directory
    if registration_path.exists() or output_path.exists():
        raise DiagnosticBlocked("managed_evidence_already_exists")
    validate_preimplementation_file(
        root / profile.preimplementation_path,
        repo_root=root,
        profile=profile,
    )
    if (
        not native_path.is_file()
        or native_path.stat().st_size != EXPECTED_MODULE_SIZE_BYTES
        or sha256_file(native_path) != EXPECTED_MODULE_SHA256
    ):
        raise DiagnosticBlocked("native_module_binding_mismatch")
    try:
        native_module = load_native_module(
            native_path, dll_directories=dll_directories
        )
        provenance = predecessor.collect_native_identity(
            module_path=native_path,
            simulator_repo=simulator_path,
            repo_root=root,
            native_module=native_module,
            adapter_commit=EXPECTED_ADAPTER_COMMIT,
        )
    except (SimulatorAdapterError, predecessor.CompatibilityBlocked) as exc:
        reason = getattr(exc, "reason", "native_module_load_failed")
        detail = getattr(exc, "detail", str(exc))
        raise DiagnosticBlocked(reason, detail) from exc
    provenance = _validate_provenance(provenance)
    contract = reachable_event_option_semantics_identity()
    contract_relative = contract["observation_contract"]["path"]
    identity = {
        "adapter_provenance": provenance,
        "adapter_source_files": list(ADAPTER_SOURCE_FILES),
        "contract": contract,
        "contract_file": _file_binding(root / contract_relative, contract_relative),
        "implementation": {
            "commit": implementation_commit,
            "source_files": list(profile.implementation_source_files),
            "source_sha256": hash_bound_files(
                root, profile.implementation_source_files
            ),
        },
        "metadata": _file_binding(metadata, str(metadata)),
        "module_path": str(native_path),
        "preimplementation": _file_binding(
            root / profile.preimplementation_path,
            profile.preimplementation_path,
        ),
        "runtime": {
            "executable": str(Path(sys.executable).resolve()),
            "python": sys.version.split()[0],
        },
        "simulator_path": str(simulator_path),
    }
    registration = build_registration(identity=identity, profile=profile)
    validate_registration_evidence(registration, root, profile=profile)
    _write_atomic(registration_path, canonical_json_bytes(registration))
    return {
        "implementation_commit": implementation_commit,
        "registration_path": profile.registration_path,
        "registration_sha256": sha256_file(registration_path),
        "seeds": list(FIXED_SEEDS),
    }


def execute_registered(
    *,
    repo_root: Path | str,
    dll_directories: Sequence[Path | str] = (),
    profile: DiagnosticProfile = V1_PROFILE,
) -> dict[str, Any]:
    profile = _coerce_profile(profile)
    root = Path(repo_root).resolve()
    registration_path = root / profile.registration_path
    pushed = assert_pushed_registration(
        registration_path=registration_path, repo_root=root, profile=profile
    )
    registration = load_registration(registration_path, profile=profile)
    metadata = validate_registration_evidence(
        registration, root, profile=profile
    )
    identity = registration["identity"]
    try:
        native_module = load_native_module(
            identity["module_path"], dll_directories=dll_directories
        )
        actual_provenance = predecessor.collect_native_identity(
            module_path=identity["module_path"],
            simulator_repo=identity["simulator_path"],
            repo_root=root,
            native_module=native_module,
            adapter_commit=EXPECTED_ADAPTER_COMMIT,
        )
    except (SimulatorAdapterError, predecessor.CompatibilityBlocked) as exc:
        reason = getattr(exc, "reason", "native_module_load_failed")
        detail = getattr(exc, "detail", str(exc))
        raise DiagnosticBlocked(reason, detail) from exc
    if _validate_provenance(actual_provenance) != identity["adapter_provenance"]:
        raise DiagnosticBlocked("native_identity_mismatch")
    provenance = identity["adapter_provenance"]

    def environment_factory(seed: int) -> NativeSimulatorEnvironment:
        return NativeSimulatorEnvironment(
            native_module.Environment(seed, CURRENT_POLICY["ascension"]),
            provenance,
        )

    def session_factory() -> CurrentPolicyBridgeSession:
        return CurrentPolicyBridgeSession(
            metadata=metadata,
            current_policy=CURRENT_POLICY,
            event_semantics_identity=reachable_event_option_semantics_identity(),
            simulator_provenance=provenance,
        )

    result = consume_and_run(
        registration=registration,
        registration_sha256=pushed["registration_sha256"],
        preregistration_commit=pushed["preregistration_commit"],
        output_directory=root / profile.output_directory,
        environment_factory=environment_factory,
        session_factory=session_factory,
        profile=profile,
    )
    return {
        "output_directory": profile.output_directory,
        "reason": result["reason"],
        "status": result["status"],
        "verdict": result["verdict"],
    }


def verify_registered(
    *,
    repo_root: Path | str,
    profile: DiagnosticProfile = V1_PROFILE,
) -> dict[str, Any]:
    profile = _coerce_profile(profile)
    root = Path(repo_root).resolve()
    registration_path = root / profile.registration_path
    registration = load_registration(registration_path, profile=profile)
    validate_registration_evidence(registration, root, profile=profile)
    manifest = verify_artifact_directory(
        registration=registration,
        registration_sha256=sha256_file(registration_path),
        output_directory=root / profile.output_directory,
        profile=profile,
    )
    return {
        "output_directory": profile.output_directory,
        "verdict": manifest["verdict"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=_REPO_ROOT)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("prepare", "prepare-r2"):
        prepare = commands.add_parser(command)
        prepare.add_argument("--module", type=Path, required=True)
        prepare.add_argument("--simulator-repo", type=Path, required=True)
        prepare.add_argument("--metadata", type=Path, required=True)
        prepare.add_argument(
            "--dll-directory", action="append", type=Path, default=[]
        )
    for command in ("execute", "execute-r2"):
        execute = commands.add_parser(command)
        execute.add_argument(
            "--dll-directory", action="append", type=Path, default=[]
        )
    commands.add_parser("verify")
    commands.add_parser("verify-r2")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    profile = R2_PROFILE if args.command.endswith("-r2") else V1_PROFILE
    try:
        if args.command in {"prepare", "prepare-r2"}:
            result = prepare_registration(
                repo_root=args.repo_root,
                module_path=args.module,
                simulator_repo=args.simulator_repo,
                metadata_path=args.metadata,
                dll_directories=args.dll_directory,
                profile=profile,
            )
        elif args.command in {"execute", "execute-r2"}:
            result = execute_registered(
                repo_root=args.repo_root,
                dll_directories=args.dll_directory,
                profile=profile,
            )
        else:
            result = verify_registered(repo_root=args.repo_root, profile=profile)
    except DiagnosticBlocked as exc:
        print(json.dumps({"detail": exc.detail, "reason": exc.reason}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
