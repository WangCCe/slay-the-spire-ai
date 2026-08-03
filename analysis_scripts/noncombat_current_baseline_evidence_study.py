"""Run the preregistered post-repair Current baseline evidence study."""

from __future__ import annotations

import argparse
import copy
import json
import os
import random
import subprocess
import sys
import time
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any


_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import analysis_scripts.noncombat_reachable_event_native_compatibility as compatibility
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
    hash_compiled_simulator_sources,
    load_native_module,
    sha256_bytes,
    sha256_file,
    validate_candidates,
)
from analysis_scripts.noncombat_simulator_training_smoke import (
    SmokeBlocked,
    paired_bootstrap_interval,
)


PREIMPLEMENTATION_SCHEMA_VERSION = (
    "noncombat-current-baseline-evidence-study-preimplementation-v1"
)
REGISTRATION_SCHEMA_VERSION = (
    "noncombat-current-baseline-evidence-study-registration-v1"
)
EXECUTION_AUTHORIZATION_SCHEMA_VERSION = (
    "noncombat-current-baseline-evidence-study-execution-authorization-v1"
)
RESULT_SCHEMA_VERSION = "noncombat-current-baseline-evidence-study-result-v1"
JOURNAL_SCHEMA_VERSION = "noncombat-current-baseline-evidence-study-journal-v1"
CONFIGURATION_SCHEMA_VERSION = (
    "noncombat-current-baseline-evidence-study-configuration-v1"
)
ROWS_SCHEMA_VERSION = "noncombat-current-baseline-evidence-study-rows-v1"
BOOTSTRAP_SCHEMA_VERSION = (
    "noncombat-current-baseline-evidence-study-bootstrap-v1"
)
METRICS_SCHEMA_VERSION = "noncombat-current-baseline-evidence-study-metrics-v1"
MANIFEST_SCHEMA_VERSION = "noncombat-current-baseline-evidence-study-manifest-v1"
PREFLIGHT_SCHEMA_VERSION = "noncombat-current-baseline-evidence-study-preflight-v1"

PREIMPLEMENTATION_PATH = (
    "reports/noncombat_current_baseline_evidence_study_20260803_"
    "preimplementation.json"
)
DEFAULT_SEED_INVENTORY_PATH = (
    "reports/noncombat_current_baseline_evidence_study_20260803_"
    "seed_inventory.json"
)
DEFAULT_REGISTRATION_PATH = (
    "reports/noncombat_current_baseline_evidence_study_20260803_input.json"
)
DEFAULT_PREFLIGHT_PATH = (
    "reports/noncombat_current_baseline_evidence_study_20260803_preflight.json"
)
DEFAULT_EXECUTION_AUTHORIZATION_PATH = (
    "reports/noncombat_current_baseline_evidence_study_20260803_"
    "execution_authorization.json"
)
DEFAULT_OUTPUT_DIRECTORY = (
    "reports/noncombat_current_baseline_evidence_study_20260803"
)

EXPECTED_PREIMPLEMENTATION_SHA256 = (
    "dd9aac6e3d25d1b42a356889396cb33924132b38a2ea6cba14d6c7eac1c8597b"
)
EXPECTED_PREIMPLEMENTATION_SIZE_BYTES = 14110
DECLARED_SUPPORT_REASON = "unsupported_shop_courier_restock_semantics"

CANARY_SEEDS = tuple(range(11000, 11016))
HOLDOUT_SEEDS = tuple(range(12000, 12064))
REPLAY_COUNT = 2
MAX_DECISIONS_PER_EPISODE = 500
CANARY_POLICY_EPISODE_LIMIT = 64
HOLDOUT_POLICY_EPISODE_LIMIT = 256
CANARY_MAX_WALL_SECONDS = 600.0
TOTAL_MAX_WALL_SECONDS = 1800.0
BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_SEED = 20260803
BOOTSTRAP_CONFIDENCE = 0.95

CURRENT_POLICY_ID = POLICY_ID
CONTROL_POLICY_ID = "deterministic_first_candidate_control_v1"
CURRENT_POLICY = copy.deepcopy(compatibility.CURRENT_POLICY)
CONTROL_POLICY = {
    "action_selection": "first_candidate_in_registered_order",
    "policy_id": CONTROL_POLICY_ID,
    "reference_policy_free": True,
}
POLICY_IDS = (CURRENT_POLICY_ID, CONTROL_POLICY_ID)

ALL_FALSE_AUTHORITY = {
    "baseline_floor_authorized": False,
    "environment_construction_authorized": False,
    "execution_authorized": False,
    "formal_rl_authorized": False,
    "fresh_evidence_authorized": False,
    "gameplay_authorized": False,
    "model_fitting_authorized": False,
    "native_loading_authorized": False,
    "ope_authorized": False,
    "policy_loading_authorized": False,
    "promotion_authorized": False,
    "qualification_authorized": False,
    "reward_authorized": False,
    "seed_access_authorized": False,
    "target_supported_outcome_authorized": False,
    "training_authorized": False,
}

GATES = {
    "bootstrap": {
        "confidence": BOOTSTRAP_CONFIDENCE,
        "resamples": BOOTSTRAP_RESAMPLES,
        "seed": BOOTSTRAP_SEED,
    },
    "canary": {
        "complete_pair_count": len(CANARY_SEEDS),
        "current_category_coverage": list(TARGET_CATEGORIES),
        "current_mean_floor_min": 15.0,
        "current_minus_control_mean_floor_min": 0.0,
        "max_declared_support_rows_per_policy": 1,
        "replay_identity_required": True,
        "unexpected_failure_count_max": 0,
    },
    "holdout": {
        "absolute_bootstrap_lower_min": 15.0,
        "complete_pair_count": len(HOLDOUT_SEEDS),
        "current_category_coverage": list(TARGET_CATEGORIES),
        "current_mean_floor_min": 18.0,
        "current_minus_control_bootstrap_lower_exclusive_min": 0.0,
        "current_minus_control_mean_floor_min": 3.0,
        "max_declared_support_rows_per_policy": 3,
        "replay_identity_required": True,
        "unexpected_failure_count_max": 0,
    },
}

LIMITS = {
    "canary_max_wall_seconds": CANARY_MAX_WALL_SECONDS,
    "canary_policy_episode_limit": CANARY_POLICY_EPISODE_LIMIT,
    "holdout_policy_episode_limit": HOLDOUT_POLICY_EPISODE_LIMIT,
    "max_decisions_per_episode": MAX_DECISIONS_PER_EPISODE,
    "replay_count": REPLAY_COUNT,
    "total_max_wall_seconds": TOTAL_MAX_WALL_SECONDS,
}

CANONICAL_ARTIFACT_NAMES = (
    "artifact_manifest.json",
    "bootstrap_draws.json",
    "configuration.json",
    "execution_journal.json",
    "metrics.json",
    "report.md",
    "trajectory_rows.json",
)

IMPLEMENTATION_SOURCE_FILES = tuple(
    dict.fromkeys(
        (
            "analysis_scripts/noncombat_current_baseline_evidence_study.py",
            "tests/test_noncombat_current_baseline_evidence_study.py",
            *compatibility.IMPLEMENTATION_SOURCE_FILES,
        )
    )
)

EXACT_EXECUTION_COMMAND = (
    r"D:\anaconda\envs\stsai\python.exe",
    "analysis_scripts/noncombat_current_baseline_evidence_study.py",
    "execute",
)
FIXED_DLL_DIRECTORIES = (r"D:\programs\CLion\bin\mingw\bin",)


class StudyBlocked(RuntimeError):
    """Raised when the immutable study contract cannot be proved."""

    def __init__(self, reason: str, detail: object | None = None):
        self.reason = reason
        self.detail = detail
        message = reason if detail is None else f"{reason}: {detail}"
        super().__init__(message)


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise StudyBlocked("invalid_mapping", label)
    return dict(value)


def _sequence(value: object, label: str) -> list[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise StudyBlocked("invalid_sequence", label)
    return list(value)


def _require_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise StudyBlocked(
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


def _preserved_detail(detail: object | None) -> object | None:
    try:
        canonical_json_bytes({"detail": detail})
        return copy.deepcopy(detail)
    except (TypeError, ValueError):
        return {"repr": repr(detail), "type": type(detail).__name__}


def _validate_binding(
    value: object, label: str, *, repository_relative: bool
) -> dict[str, Any]:
    binding = _mapping(value, label)
    _require_keys(binding, {"path", "sha256", "size_bytes"}, label)
    path = binding["path"]
    if not isinstance(path, str) or not path:
        raise StudyBlocked("binding_path_invalid", label)
    if repository_relative:
        pure = PurePosixPath(path)
        if (
            "\\" in path
            or pure.is_absolute()
            or any(part in {"", ".", ".."} for part in pure.parts)
        ):
            raise StudyBlocked("binding_path_invalid", label)
    elif not Path(path).is_absolute():
        raise StudyBlocked("binding_path_invalid", label)
    if not _is_hex(binding["sha256"], 64):
        raise StudyBlocked("binding_hash_invalid", label)
    size = binding["size_bytes"]
    if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
        raise StudyBlocked("binding_size_invalid", label)
    return binding


def _file_binding(path: Path, display_path: str) -> dict[str, Any]:
    if not path.is_file():
        raise StudyBlocked("bound_file_missing", display_path)
    return {
        "path": display_path,
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def _reject_duplicate_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise StudyBlocked("duplicate_json_key", key)
        result[key] = value
    return result


def _load_json(path: Path | str, label: str) -> dict[str, Any]:
    try:
        raw = Path(path).read_bytes()
        value = json.loads(raw, object_pairs_hook=_reject_duplicate_pairs)
    except StudyBlocked:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise StudyBlocked(
            "cannot_load_json", {"error": str(exc), "label": label}
        ) from exc
    normalized = _mapping(value, label)
    if raw != canonical_json_bytes(normalized):
        raise StudyBlocked("json_not_canonical", label)
    return normalized


def _expected_preimplementation(repo_root: Path | str = _REPO_ROOT) -> dict[str, Any]:
    path = Path(repo_root).resolve() / PREIMPLEMENTATION_PATH
    if (
        not path.is_file()
        or path.stat().st_size != EXPECTED_PREIMPLEMENTATION_SIZE_BYTES
        or sha256_file(path) != EXPECTED_PREIMPLEMENTATION_SHA256
    ):
        raise StudyBlocked("preimplementation_file_identity_mismatch")
    value = _load_json(path, "preimplementation")
    if value.get("schema_version") != PREIMPLEMENTATION_SCHEMA_VERSION:
        raise StudyBlocked("preimplementation_schema_mismatch")
    return value


def validate_preimplementation(value: object) -> dict[str, Any]:
    baseline = _mapping(value, "preimplementation")
    expected = _expected_preimplementation()
    if not _canonical_equal(baseline, expected):
        raise StudyBlocked("preimplementation_identity_mismatch")
    return baseline


def load_preimplementation(
    path: Path | str = _REPO_ROOT / PREIMPLEMENTATION_PATH,
) -> dict[str, Any]:
    value = _load_json(path, "preimplementation")
    return validate_preimplementation(value)


def _registered_adapter_provenance() -> dict[str, Any]:
    baseline = _expected_preimplementation()
    binding = baseline["external_identity_expectations"]["source_registration"]
    path = _REPO_ROOT / binding["path"]
    if (
        not path.is_file()
        or path.stat().st_size != binding["size_bytes"]
        or sha256_file(path) != binding["sha256"]
    ):
        raise StudyBlocked("external_source_registration_identity_mismatch")
    registration = _load_json(path, "consumed r2 registration")
    return copy.deepcopy(registration["identity"]["adapter_provenance"])


def build_registration(*, identity: Mapping[str, Any]) -> dict[str, Any]:
    registration = {
        "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
        "cohorts": {
            "canary": list(CANARY_SEEDS),
            "holdout": list(HOLDOUT_SEEDS),
        },
        "gates": copy.deepcopy(GATES),
        "identity": copy.deepcopy(dict(identity)),
        "limits": copy.deepcopy(LIMITS),
        "output": {
            "artifact_names": list(CANONICAL_ARTIFACT_NAMES),
            "directory": DEFAULT_OUTPUT_DIRECTORY,
        },
        "policies": {
            "control": copy.deepcopy(CONTROL_POLICY),
            "current": copy.deepcopy(CURRENT_POLICY),
        },
        "schema_version": REGISTRATION_SCHEMA_VERSION,
    }
    return validate_registration(registration)


def validate_registration(value: object) -> dict[str, Any]:
    registration = _mapping(value, "registration")
    _require_keys(
        registration,
        {
            "authority",
            "cohorts",
            "gates",
            "identity",
            "limits",
            "output",
            "policies",
            "schema_version",
        },
        "registration",
    )
    if registration["schema_version"] != REGISTRATION_SCHEMA_VERSION:
        raise StudyBlocked("registration_schema_mismatch")
    if not _canonical_equal(registration["authority"], ALL_FALSE_AUTHORITY):
        raise StudyBlocked("authority_must_be_all_false")
    expected_cohorts = {
        "canary": list(CANARY_SEEDS),
        "holdout": list(HOLDOUT_SEEDS),
    }
    if not _canonical_equal(registration["cohorts"], expected_cohorts):
        raise StudyBlocked("registration_cohort_mismatch")
    if not _canonical_equal(registration["policies"], {
        "control": CONTROL_POLICY,
        "current": CURRENT_POLICY,
    }):
        raise StudyBlocked("registration_policy_mismatch")
    gates = _mapping(registration["gates"], "registration.gates")
    if not _canonical_equal(gates.get("bootstrap"), GATES["bootstrap"]):
        raise StudyBlocked("registration_bootstrap_mismatch")
    if not _canonical_equal(gates, GATES):
        raise StudyBlocked("registration_gate_mismatch")
    if not _canonical_equal(registration["limits"], LIMITS):
        raise StudyBlocked("registration_limit_mismatch")
    expected_output = {
        "artifact_names": list(CANONICAL_ARTIFACT_NAMES),
        "directory": DEFAULT_OUTPUT_DIRECTORY,
    }
    if not _canonical_equal(registration["output"], expected_output):
        raise StudyBlocked("registration_output_mismatch")

    identity = _mapping(registration["identity"], "registration.identity")
    _require_keys(
        identity,
        {
            "adapter_provenance",
            "adapter_source_files",
            "event_contract",
            "event_semantics",
            "implementation",
            "metadata",
            "module",
            "preimplementation",
            "runtime",
            "seed_inventory",
            "simulator",
        },
        "registration.identity",
    )
    baseline = _expected_preimplementation()
    expected_external = baseline["external_identity_expectations"]
    if not _canonical_equal(
        identity["adapter_provenance"], _registered_adapter_provenance()
    ):
        raise StudyBlocked("external_identity_mismatch", "adapter_provenance")
    if identity["adapter_source_files"] != list(compatibility.ADAPTER_SOURCE_FILES):
        raise StudyBlocked("adapter_source_files_mismatch")
    if not _canonical_equal(
        identity["event_semantics"], reachable_event_option_semantics_identity()
    ):
        raise StudyBlocked("event_semantics_identity_mismatch")
    event_contract = _validate_binding(
        identity["event_contract"],
        "event_contract",
        repository_relative=True,
    )
    observation_contract = identity["event_semantics"]["observation_contract"]
    if (
        event_contract["path"] != observation_contract["path"]
        or event_contract["sha256"] != observation_contract["sha256"]
    ):
        raise StudyBlocked("event_contract_binding_mismatch")
    implementation = _mapping(identity["implementation"], "implementation")
    _require_keys(
        implementation,
        {"commit", "source_files", "source_sha256"},
        "implementation",
    )
    if (
        not _is_hex(implementation["commit"], 40)
        or implementation["source_files"] != list(IMPLEMENTATION_SOURCE_FILES)
        or not _is_hex(implementation["source_sha256"], 64)
    ):
        raise StudyBlocked("implementation_identity_mismatch")
    for field in ("metadata", "module", "simulator"):
        if not _canonical_equal(identity[field], expected_external[field]):
            raise StudyBlocked("external_identity_mismatch", field)
    expected_preimplementation = {
        "path": PREIMPLEMENTATION_PATH,
        "sha256": EXPECTED_PREIMPLEMENTATION_SHA256,
        "size_bytes": EXPECTED_PREIMPLEMENTATION_SIZE_BYTES,
    }
    if not _canonical_equal(
        identity["preimplementation"], expected_preimplementation
    ):
        raise StudyBlocked("preimplementation_binding_mismatch")
    runtime = _mapping(identity["runtime"], "runtime")
    _require_keys(
        runtime,
        {"executable", "python", "sha256", "size_bytes"},
        "runtime",
    )
    if (
        runtime["executable"] != expected_external["runtime"]["executable"]
        or runtime["python"] != expected_external["runtime"]["python"]
        or not _is_hex(runtime["sha256"], 64)
        or isinstance(runtime["size_bytes"], bool)
        or not isinstance(runtime["size_bytes"], int)
        or runtime["size_bytes"] <= 0
    ):
        raise StudyBlocked("external_identity_mismatch", "runtime")
    seed_inventory = _validate_binding(
        identity["seed_inventory"],
        "seed_inventory",
        repository_relative=True,
    )
    if seed_inventory["path"] != DEFAULT_SEED_INVENTORY_PATH:
        raise StudyBlocked("seed_inventory_path_mismatch")
    identity["implementation"] = implementation
    identity["event_contract"] = event_contract
    identity["runtime"] = runtime
    identity["seed_inventory"] = seed_inventory
    registration["identity"] = identity
    return registration


def load_registration(path: Path | str = _REPO_ROOT / DEFAULT_REGISTRATION_PATH):
    return validate_registration(_load_json(path, "registration"))


def validate_execution_authorization(
    value: object,
    *,
    registration: Mapping[str, Any],
    registration_sha256: str,
    preregistration_commit: str,
) -> dict[str, Any]:
    if value is None:
        raise StudyBlocked("execution_authorization_missing")
    authorization = _mapping(value, "execution authorization")
    _require_keys(
        authorization,
        {
            "approval",
            "authority",
            "command",
            "preregistration_commit",
            "registration",
            "schema_version",
        },
        "execution authorization",
    )
    if authorization["schema_version"] != EXECUTION_AUTHORIZATION_SCHEMA_VERSION:
        raise StudyBlocked("execution_authorization_schema_mismatch")
    validate_registration(copy.deepcopy(registration))
    expected_approval = {
        "approved": True,
        "scope": "one_canary_and_conditional_holdout_same_attempt",
        "source": "explicit_user_approval",
    }
    if not _canonical_equal(authorization["approval"], expected_approval):
        raise StudyBlocked("execution_approval_mismatch")
    expected_authority = {
        **copy.deepcopy(ALL_FALSE_AUTHORITY),
        "execution_authorized": True,
    }
    if not _canonical_equal(authorization["authority"], expected_authority):
        raise StudyBlocked("execution_authority_mismatch")
    if authorization["command"] != list(EXACT_EXECUTION_COMMAND):
        raise StudyBlocked("execution_command_mismatch")
    if authorization["preregistration_commit"] != preregistration_commit:
        raise StudyBlocked("execution_commit_mismatch")
    expected_binding = {
        "path": DEFAULT_REGISTRATION_PATH,
        "sha256": registration_sha256,
        "size_bytes": len(canonical_json_bytes(registration)),
    }
    if not _canonical_equal(authorization["registration"], expected_binding):
        raise StudyBlocked("execution_registration_mismatch")
    return authorization


def _git_bytes(repo_root: Path, *args: str) -> bytes:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        raise StudyBlocked(
            "git_command_failed",
            {"args": list(args), "stderr": completed.stderr.decode(errors="replace")},
        )
    return completed.stdout


def _git_text(repo_root: Path, *args: str) -> str:
    return _git_bytes(repo_root, *args).decode("utf-8").strip()


def _assert_clean_pushed_head(repo_root: Path) -> str:
    if _git_text(repo_root, "status", "--porcelain", "--untracked-files=no"):
        raise StudyBlocked("tracked_tree_dirty")
    head = _git_text(repo_root, "rev-parse", "HEAD")
    origin = _git_text(repo_root, "rev-parse", "origin/master")
    if head != origin:
        raise StudyBlocked("head_not_pushed", {"head": head, "origin_master": origin})
    if not _is_hex(head, 40):
        raise StudyBlocked("head_identity_invalid")
    return head


def assert_pushed_registration(
    *, registration_path: Path | str, repo_root: Path | str
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    path = Path(registration_path).resolve()
    expected = (root / DEFAULT_REGISTRATION_PATH).resolve()
    if path != expected or not path.is_file():
        raise StudyBlocked("registration_path_mismatch")
    registration = load_registration(path)
    if (root / registration["output"]["directory"]).exists():
        raise StudyBlocked("output_directory_already_exists")
    head = _assert_clean_pushed_head(root)
    relative = path.relative_to(root).as_posix()
    if _git_bytes(root, "show", f"{head}:{relative}") != path.read_bytes():
        raise StudyBlocked("pushed_registration_mismatch")
    return {
        "preregistration_commit": head,
        "registration_sha256": sha256_file(path),
    }


def _is_declared_support_exception(exc: BaseException) -> bool:
    return type(exc) is RuntimeError and str(exc) == DECLARED_SUPPORT_REASON


def _episode_row(
    *,
    seed: int,
    policy_id: str,
    decisions: list[dict[str, Any]],
    category_counts: Counter,
    disposition: str,
    floor: int,
    outcome: str,
    support_reason: str | None,
) -> dict[str, Any]:
    row = {
        "action_sequence_sha256": sha256_bytes(
            canonical_json_bytes([decision["action_id"] for decision in decisions])
        ),
        "category_counts": {
            category: category_counts[category] for category in TARGET_CATEGORIES
        },
        "decision_count": len(decisions),
        "decisions": decisions,
        "disposition": disposition,
        "floor": floor,
        "outcome": outcome,
        "policy_id": policy_id,
        "seed": seed,
        "support_reason": support_reason,
    }
    row["trajectory_sha256"] = sha256_bytes(canonical_json_bytes(row))
    return row


def _declared_support_row(
    *,
    seed: int,
    policy_id: str,
    decisions: list[dict[str, Any]],
    category_counts: Counter,
    last_supported_floor: int | None,
) -> dict[str, Any]:
    if last_supported_floor is None:
        raise StudyBlocked("declared_support_without_supported_floor")
    return _episode_row(
        seed=seed,
        policy_id=policy_id,
        decisions=decisions,
        category_counts=category_counts,
        disposition="declared_support_blocked",
        floor=last_supported_floor,
        outcome="player_loss",
        support_reason=DECLARED_SUPPORT_REASON,
    )


def _current_action(
    *,
    session: Any,
    snapshot: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    decision_index: int,
    snapshot_sha256: str,
    candidates_sha256: str,
) -> tuple[str, str]:
    if session is None:
        raise StudyBlocked("current_session_missing")
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
        raise StudyBlocked(exc.reason, exc.detail) from exc
    except StudyBlocked:
        raise
    except Exception as exc:
        raise StudyBlocked(
            "current_policy_evaluation_failed",
            {"message": str(exc), "type": type(exc).__name__},
        ) from exc
    if (
        evaluation.get("category") != snapshot.get("category")
        or evaluation.get("policy_id") != CURRENT_POLICY_ID
        or not isinstance(evaluation.get("action_type"), str)
        or not evaluation["action_type"]
        or evaluation.get("fallback_used") is not False
        or evaluation.get("tracker_enabled") is not False
        or evaluation.get("source_mutated") is not False
        or evaluation.get("input_snapshot_sha256") != snapshot_sha256
        or evaluation.get("input_candidates_sha256") != candidates_sha256
    ):
        raise StudyBlocked("current_evaluation_contract_invalid", evaluation)
    action_id = evaluation.get("action_id")
    if sum(candidate.get("action_id") == action_id for candidate in candidates) != 1:
        raise StudyBlocked("selected_action_not_unique_candidate", action_id)
    if snapshot.get("category") == "event":
        expected_source = reachable_event_option_semantics_identity()["contract_id"]
        observation = evaluation.get("event_observation")
        if (
            evaluation.get("event_semantics_source") != expected_source
            or not isinstance(observation, Mapping)
            or observation.get("selected_action_id") != action_id
            or observation.get("semantics_source") != expected_source
        ):
            raise StudyBlocked("current_evaluation_contract_invalid", evaluation)
    return str(action_id), evaluation["action_type"]


def run_episode(
    *,
    environment: Any,
    session: Any,
    seed: int,
    policy_id: str,
    max_decisions: int,
    deadline: float,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    if policy_id not in POLICY_IDS:
        raise StudyBlocked("policy_id_invalid", policy_id)
    if (
        isinstance(seed, bool)
        or not isinstance(seed, int)
        or seed < 0
        or isinstance(max_decisions, bool)
        or not isinstance(max_decisions, int)
        or max_decisions <= 0
    ):
        raise StudyBlocked("episode_configuration_invalid")
    if policy_id == CONTROL_POLICY_ID and session is not None:
        raise StudyBlocked("control_session_must_be_absent")

    decisions: list[dict[str, Any]] = []
    category_counts = Counter()
    last_supported_floor: int | None = None
    while True:
        if monotonic() > deadline:
            raise StudyBlocked("execution_deadline_exceeded")
        try:
            snapshot = _mapping(environment.snapshot(), "native snapshot")
        except StudyBlocked:
            raise
        except Exception as exc:
            if _is_declared_support_exception(exc):
                return _declared_support_row(
                    seed=seed,
                    policy_id=policy_id,
                    decisions=decisions,
                    category_counts=category_counts,
                    last_supported_floor=last_supported_floor,
                )
            raise StudyBlocked(
                "native_snapshot_failed",
                {"message": str(exc), "type": type(exc).__name__},
            ) from exc
        if monotonic() > deadline:
            raise StudyBlocked("execution_deadline_exceeded")
        if snapshot.get("terminal") is True:
            break
        if snapshot.get("terminal") is not False:
            raise StudyBlocked("snapshot_terminal_invalid")
        if len(decisions) >= max_decisions:
            raise StudyBlocked(
                "decision_limit_exceeded", {"limit": max_decisions, "seed": seed}
            )
        state = _mapping(snapshot.get("state"), "native snapshot.state")
        floor = state.get("floor")
        decision_index = snapshot.get("decision_count")
        if (
            state.get("seed") != str(seed)
            or isinstance(floor, bool)
            or not isinstance(floor, int)
            or floor < 0
            or isinstance(decision_index, bool)
            or not isinstance(decision_index, int)
            or decision_index < 0
        ):
            raise StudyBlocked(
                "decision_coordinates_invalid",
                {
                    "decision_index": decision_index,
                    "floor": floor,
                    "seed": state.get("seed"),
                },
            )
        last_supported_floor = floor
        category = snapshot.get("category")
        if category not in TARGET_CATEGORIES:
            raise StudyBlocked("target_category_invalid", category)
        try:
            candidates = validate_candidates(
                environment.legal_actions(), category=category
            )
        except (SimulatorAdapterError, TypeError, ValueError) as exc:
            raise StudyBlocked("legal_actions_invalid", str(exc)) from exc
        except Exception as exc:
            if _is_declared_support_exception(exc):
                return _declared_support_row(
                    seed=seed,
                    policy_id=policy_id,
                    decisions=decisions,
                    category_counts=category_counts,
                    last_supported_floor=last_supported_floor,
                )
            raise StudyBlocked(
                "native_legal_actions_failed",
                {"message": str(exc), "type": type(exc).__name__},
            ) from exc
        if monotonic() > deadline:
            raise StudyBlocked("execution_deadline_exceeded")
        before_snapshot = canonical_json_bytes(snapshot)
        before_candidates = canonical_json_bytes(candidates)
        snapshot_sha256 = sha256_bytes(before_snapshot)
        candidates_sha256 = sha256_bytes(before_candidates)
        if policy_id == CURRENT_POLICY_ID:
            action_id, action_type = _current_action(
                session=session,
                snapshot=snapshot,
                candidates=candidates,
                decision_index=decision_index,
                snapshot_sha256=snapshot_sha256,
                candidates_sha256=candidates_sha256,
            )
        else:
            action_id = candidates[0]["action_id"]
            action_type = "FirstCandidateAction"
        if monotonic() > deadline:
            raise StudyBlocked("execution_deadline_exceeded")
        if canonical_json_bytes(snapshot) != before_snapshot:
            raise StudyBlocked("source_snapshot_mutated")
        if canonical_json_bytes(candidates) != before_candidates:
            raise StudyBlocked("source_candidates_mutated")
        try:
            transition = _mapping(environment.step(action_id), "native transition")
        except StudyBlocked:
            raise
        except Exception as exc:
            if _is_declared_support_exception(exc):
                return _declared_support_row(
                    seed=seed,
                    policy_id=policy_id,
                    decisions=decisions,
                    category_counts=category_counts,
                    last_supported_floor=last_supported_floor,
                )
            raise StudyBlocked(
                "native_step_failed",
                {"message": str(exc), "type": type(exc).__name__},
            ) from exc
        if monotonic() > deadline:
            raise StudyBlocked("execution_deadline_exceeded")
        if transition.get("selected_action_id") != action_id:
            raise StudyBlocked("transition_action_mismatch", action_id)
        decisions.append(
            {
                "action_id": action_id,
                "action_type": action_type,
                "candidate_actions_sha256": candidates_sha256,
                "category": category,
                "decision_index": decision_index,
                "policy_input_sha256": sha256_bytes(
                    canonical_json_bytes(
                        {
                            "candidates": candidates_sha256,
                            "snapshot": snapshot_sha256,
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
        raise StudyBlocked(
            "terminal_state_invalid",
            {
                "floor": terminal_floor,
                "outcome": outcome,
                "seed": state.get("seed"),
            },
        )
    return _episode_row(
        seed=seed,
        policy_id=policy_id,
        decisions=decisions,
        category_counts=category_counts,
        disposition="terminal",
        floor=terminal_floor,
        outcome=outcome,
        support_reason=None,
    )


def run_policy_pair(
    *,
    seed: int,
    environment_factory: Callable[[int, str, int], Any],
    session_factory: Callable[[], Any],
    deadline: float,
    monotonic: Callable[[], float] = time.monotonic,
) -> list[dict[str, Any]]:
    rows = []
    for policy_id in POLICY_IDS:
        replays = []
        for replay_index in range(REPLAY_COUNT):
            if monotonic() > deadline:
                raise StudyBlocked("execution_deadline_exceeded")
            try:
                environment = environment_factory(seed, policy_id, replay_index)
                session = session_factory() if policy_id == CURRENT_POLICY_ID else None
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                raise StudyBlocked(
                    "environment_construction_failed",
                    {"message": str(exc), "type": type(exc).__name__},
                ) from exc
            replays.append(
                run_episode(
                    environment=environment,
                    session=session,
                    seed=seed,
                    policy_id=policy_id,
                    max_decisions=MAX_DECISIONS_PER_EPISODE,
                    deadline=deadline,
                    monotonic=monotonic,
                )
            )
        if replays[0]["disposition"] != replays[1]["disposition"]:
            raise StudyBlocked(
                "replay_disposition_mismatch",
                {
                    "first": replays[0]["disposition"],
                    "policy_id": policy_id,
                    "second": replays[1]["disposition"],
                    "seed": seed,
                },
            )
        if canonical_json_bytes(replays[0]) != canonical_json_bytes(replays[1]):
            raise StudyBlocked(
                "trajectory_nondeterministic",
                {
                    "first": replays[0]["trajectory_sha256"],
                    "policy_id": policy_id,
                    "second": replays[1]["trajectory_sha256"],
                    "seed": seed,
                },
            )
        rows.append({**replays[0], "replay_count": REPLAY_COUNT})
    return rows


def _validate_decision(value: object, *, row_index: int, decision_index: int):
    decision = _mapping(value, f"row[{row_index}].decision[{decision_index}]")
    _require_keys(
        decision,
        {
            "action_id",
            "action_type",
            "candidate_actions_sha256",
            "category",
            "decision_index",
            "policy_input_sha256",
            "source_snapshot_sha256",
        },
        f"row[{row_index}].decision[{decision_index}]",
    )
    if (
        not isinstance(decision["action_id"], str)
        or not decision["action_id"]
        or not isinstance(decision["action_type"], str)
        or not decision["action_type"]
        or decision["category"] not in TARGET_CATEGORIES
        or isinstance(decision["decision_index"], bool)
        or not isinstance(decision["decision_index"], int)
        or decision["decision_index"] < 0
        or not all(
            _is_hex(decision[field], 64)
            for field in (
                "candidate_actions_sha256",
                "policy_input_sha256",
                "source_snapshot_sha256",
            )
        )
    ):
        raise StudyBlocked("decision_row_invalid", {"index": decision_index})
    return decision


def _validate_row(
    value: object,
    *,
    row_index: int,
    expected_seed: int | None = None,
    expected_policy_id: str | None = None,
) -> dict[str, Any]:
    row = _mapping(value, f"row[{row_index}]")
    _require_keys(
        row,
        {
            "action_sequence_sha256",
            "category_counts",
            "decision_count",
            "decisions",
            "disposition",
            "floor",
            "outcome",
            "policy_id",
            "replay_count",
            "seed",
            "support_reason",
            "trajectory_sha256",
        },
        f"row[{row_index}]",
    )
    if (
        row["policy_id"] not in POLICY_IDS
        or (expected_policy_id is not None and row["policy_id"] != expected_policy_id)
        or isinstance(row["seed"], bool)
        or not isinstance(row["seed"], int)
        or (expected_seed is not None and row["seed"] != expected_seed)
        or row["replay_count"] != REPLAY_COUNT
        or isinstance(row["floor"], bool)
        or not isinstance(row["floor"], int)
        or row["floor"] < 0
        or row["outcome"] not in {"player_loss", "player_victory"}
        or not _is_hex(row["trajectory_sha256"], 64)
        or not _is_hex(row["action_sequence_sha256"], 64)
    ):
        raise StudyBlocked("trajectory_row_invalid", row_index)
    decisions = [
        _validate_decision(raw, row_index=row_index, decision_index=index)
        for index, raw in enumerate(_sequence(row["decisions"], "decisions"))
    ]
    if row["decision_count"] != len(decisions):
        raise StudyBlocked("trajectory_decision_count_mismatch", row_index)
    expected_counts = Counter(decision["category"] for decision in decisions)
    category_counts = _mapping(row["category_counts"], "category_counts")
    if not _canonical_equal(
        category_counts,
        {category: expected_counts[category] for category in TARGET_CATEGORIES},
    ):
        raise StudyBlocked("trajectory_category_counts_mismatch", row_index)
    if row["disposition"] == "terminal":
        if row["support_reason"] is not None:
            raise StudyBlocked("trajectory_support_contract_invalid", row_index)
    elif row["disposition"] == "declared_support_blocked":
        if (
            row["support_reason"] != DECLARED_SUPPORT_REASON
            or row["outcome"] != "player_loss"
        ):
            raise StudyBlocked("trajectory_support_contract_invalid", row_index)
    else:
        raise StudyBlocked("trajectory_disposition_invalid", row_index)
    if row["action_sequence_sha256"] != sha256_bytes(
        canonical_json_bytes([decision["action_id"] for decision in decisions])
    ):
        raise StudyBlocked("action_sequence_hash_mismatch", row_index)
    unhashed = copy.deepcopy(row)
    unhashed.pop("replay_count")
    trajectory_sha256 = unhashed.pop("trajectory_sha256")
    if trajectory_sha256 != sha256_bytes(canonical_json_bytes(unhashed)):
        raise StudyBlocked("trajectory_hash_mismatch", row_index)
    row["decisions"] = decisions
    row["category_counts"] = category_counts
    return row


def _validated_stage_rows(
    rows: Sequence[Mapping[str, Any]], seeds: Sequence[int]
) -> list[dict[str, Any]]:
    raw_rows = _sequence(rows, "stage rows")
    expected_pairs = [
        (seed, policy_id) for seed in seeds for policy_id in POLICY_IDS
    ]
    if len(raw_rows) != len(expected_pairs):
        raise StudyBlocked(
            "stage_denominator_incomplete",
            {"actual": len(raw_rows), "expected": len(expected_pairs)},
        )
    normalized = [
        _validate_row(
            raw,
            row_index=index,
            expected_seed=expected_seed,
            expected_policy_id=expected_policy_id,
        )
        for index, (raw, (expected_seed, expected_policy_id)) in enumerate(
            zip(raw_rows, expected_pairs, strict=True)
        )
    ]
    return normalized


def _stage_metrics(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_policy = {policy_id: [] for policy_id in POLICY_IDS}
    for row in rows:
        by_policy[row["policy_id"]].append(row)
    current_rows = by_policy[CURRENT_POLICY_ID]
    control_rows = by_policy[CONTROL_POLICY_ID]
    current_floors = [float(row["floor"]) for row in current_rows]
    control_floors = [float(row["floor"]) for row in control_rows]
    differences = [
        current - control
        for current, control in zip(current_floors, control_floors, strict=True)
    ]
    coverage = Counter()
    for row in current_rows:
        coverage.update(row["category_counts"])
    support_counts = {
        policy_id: sum(
            row["disposition"] == "declared_support_blocked"
            for row in policy_rows
        )
        for policy_id, policy_rows in by_policy.items()
    }
    victory_counts = {
        policy_id: sum(row["outcome"] == "player_victory" for row in policy_rows)
        for policy_id, policy_rows in by_policy.items()
    }
    return {
        "control_mean_floor": sum(control_floors) / len(control_floors),
        "current_category_counts": {
            category: coverage[category] for category in TARGET_CATEGORIES
        },
        "current_mean_floor": sum(current_floors) / len(current_floors),
        "current_floors": current_floors,
        "paired_floor_differences": differences,
        "paired_mean_floor_difference": sum(differences) / len(differences),
        "support_counts": support_counts,
        "victory_counts": victory_counts,
    }


def classify_canary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    normalized = _validated_stage_rows(rows, CANARY_SEEDS)
    metrics = _stage_metrics(normalized)
    gate = GATES["canary"]
    coverage_passes = all(
        metrics["current_category_counts"][category] > 0
        for category in TARGET_CATEGORIES
    )
    support_passes = all(
        count <= gate["max_declared_support_rows_per_policy"]
        for count in metrics["support_counts"].values()
    )
    checks = {
        "category_coverage": coverage_passes,
        "current_mean_floor": metrics["current_mean_floor"]
        >= gate["current_mean_floor_min"],
        "paired_mean_floor_difference": metrics["paired_mean_floor_difference"]
        >= gate["current_minus_control_mean_floor_min"],
        "support_ceiling": support_passes,
    }
    passes = all(checks.values())
    return {
        "checks": checks,
        "control_mean_floor": metrics["control_mean_floor"],
        "current_category_counts": metrics["current_category_counts"],
        "current_mean_floor": metrics["current_mean_floor"],
        "paired_mean_floor_difference": metrics["paired_mean_floor_difference"],
        "pair_count": len(CANARY_SEEDS),
        "passes": passes,
        "support_counts": metrics["support_counts"],
        "verdict": "canary_passed" if passes else "study_stopped_at_canary",
        "victory_counts": metrics["victory_counts"],
    }


def _bootstrap_means(values: Sequence[float]) -> list[float]:
    normalized = [float(value) for value in values]
    generator = random.Random(BOOTSTRAP_SEED)
    return [
        sum(
            normalized[generator.randrange(len(normalized))]
            for _ in normalized
        )
        / len(normalized)
        for _ in range(BOOTSTRAP_RESAMPLES)
    ]


def _empty_bootstrap_draws() -> dict[str, Any]:
    return {
        "absolute_current_mean": [],
        "hashes": {
            "absolute_current_mean": sha256_bytes(canonical_json_bytes([])),
            "paired_floor_difference_mean": sha256_bytes(canonical_json_bytes([])),
        },
        "paired_floor_difference_mean": [],
        "parameters": copy.deepcopy(GATES["bootstrap"]),
        "schema_version": BOOTSTRAP_SCHEMA_VERSION,
        "status": "not_run",
    }


def classify_holdout(
    rows: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    normalized = _validated_stage_rows(rows, HOLDOUT_SEEDS)
    metrics = _stage_metrics(normalized)
    try:
        absolute_interval = paired_bootstrap_interval(
            metrics["current_floors"],
            seed=BOOTSTRAP_SEED,
            resamples=BOOTSTRAP_RESAMPLES,
            confidence_level=BOOTSTRAP_CONFIDENCE,
        )
        paired_interval = paired_bootstrap_interval(
            metrics["paired_floor_differences"],
            seed=BOOTSTRAP_SEED,
            resamples=BOOTSTRAP_RESAMPLES,
            confidence_level=BOOTSTRAP_CONFIDENCE,
        )
    except SmokeBlocked as exc:
        raise StudyBlocked("bootstrap_failed", str(exc)) from exc
    absolute_draws = _bootstrap_means(metrics["current_floors"])
    paired_draws = _bootstrap_means(metrics["paired_floor_differences"])
    draws = {
        "absolute_current_mean": absolute_draws,
        "hashes": {
            "absolute_current_mean": sha256_bytes(
                canonical_json_bytes(absolute_draws)
            ),
            "paired_floor_difference_mean": sha256_bytes(
                canonical_json_bytes(paired_draws)
            ),
        },
        "paired_floor_difference_mean": paired_draws,
        "parameters": copy.deepcopy(GATES["bootstrap"]),
        "schema_version": BOOTSTRAP_SCHEMA_VERSION,
        "status": "completed",
    }
    gate = GATES["holdout"]
    checks = {
        "absolute_bootstrap_lower": absolute_interval["lower"]
        >= gate["absolute_bootstrap_lower_min"],
        "category_coverage": all(
            metrics["current_category_counts"][category] > 0
            for category in TARGET_CATEGORIES
        ),
        "current_mean_floor": metrics["current_mean_floor"]
        >= gate["current_mean_floor_min"],
        "paired_bootstrap_lower": paired_interval["lower"]
        > gate["current_minus_control_bootstrap_lower_exclusive_min"],
        "paired_mean_floor_difference": metrics["paired_mean_floor_difference"]
        >= gate["current_minus_control_mean_floor_min"],
        "support_ceiling": all(
            count <= gate["max_declared_support_rows_per_policy"]
            for count in metrics["support_counts"].values()
        ),
    }
    passes = all(checks.values())
    return (
        {
            "absolute_bootstrap": absolute_interval,
            "checks": checks,
            "control_mean_floor": metrics["control_mean_floor"],
            "current_category_counts": metrics["current_category_counts"],
            "current_mean_floor": metrics["current_mean_floor"],
            "paired_bootstrap": paired_interval,
            "paired_mean_floor_difference": metrics[
                "paired_mean_floor_difference"
            ],
            "pair_count": len(HOLDOUT_SEEDS),
            "passes": passes,
            "support_counts": metrics["support_counts"],
            "verdict": (
                "study_valid_with_baseline_floor"
                if passes
                else "study_valid_without_baseline_floor"
            ),
            "victory_counts": metrics["victory_counts"],
        },
        draws,
    )


def _result(
    *,
    rows: list[dict[str, Any]],
    verdict: str,
    status: str,
    reason: str | None,
    detail: object | None,
    canary: Mapping[str, Any] | None,
    holdout: Mapping[str, Any] | None,
    holdout_accessed: bool,
    bootstrap_draws: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
        "bootstrap_draws": copy.deepcopy(dict(bootstrap_draws)),
        "canary": copy.deepcopy(dict(canary)) if canary is not None else None,
        "detail": _preserved_detail(detail),
        "holdout": copy.deepcopy(dict(holdout)) if holdout is not None else None,
        "holdout_accessed": holdout_accessed,
        "reason": reason,
        "rows": copy.deepcopy(rows),
        "schema_version": RESULT_SCHEMA_VERSION,
        "status": status,
        "verdict": verdict,
    }


def run_study(
    *,
    registration: Mapping[str, Any],
    environment_factory: Callable[[int, str, int], Any],
    session_factory: Callable[[], Any],
    monotonic: Callable[[], float] = time.monotonic,
    row_callback: Callable[[list[dict[str, Any]]], None] | None = None,
) -> dict[str, Any]:
    validate_registration(copy.deepcopy(registration))
    started = monotonic()
    canary_deadline = started + CANARY_MAX_WALL_SECONDS
    total_deadline = started + TOTAL_MAX_WALL_SECONDS
    rows: list[dict[str, Any]] = []
    holdout_accessed = False
    canary_classification = None
    try:
        for seed in CANARY_SEEDS:
            pair = run_policy_pair(
                seed=seed,
                environment_factory=environment_factory,
                session_factory=session_factory,
                deadline=canary_deadline,
                monotonic=monotonic,
            )
            rows.extend(pair)
            if row_callback is not None:
                row_callback(copy.deepcopy(rows))
        if len(rows) * REPLAY_COUNT != CANARY_POLICY_EPISODE_LIMIT:
            raise StudyBlocked("canary_policy_episode_limit_mismatch")
        canary_classification = classify_canary(rows)
        if not canary_classification["passes"]:
            return _result(
                rows=rows,
                verdict="study_stopped_at_canary",
                status="completed",
                reason=None,
                detail=None,
                canary=canary_classification,
                holdout=None,
                holdout_accessed=False,
                bootstrap_draws=_empty_bootstrap_draws(),
            )

        holdout_accessed = True
        holdout_rows = []
        for seed in HOLDOUT_SEEDS:
            if monotonic() > total_deadline:
                raise StudyBlocked("execution_deadline_exceeded")
            pair = run_policy_pair(
                seed=seed,
                environment_factory=environment_factory,
                session_factory=session_factory,
                deadline=total_deadline,
                monotonic=monotonic,
            )
            holdout_rows.extend(pair)
            rows.extend(pair)
            if row_callback is not None:
                row_callback(copy.deepcopy(rows))
        if len(holdout_rows) * REPLAY_COUNT != HOLDOUT_POLICY_EPISODE_LIMIT:
            raise StudyBlocked("holdout_policy_episode_limit_mismatch")
        holdout_classification, draws = classify_holdout(holdout_rows)
        return _result(
            rows=rows,
            verdict=holdout_classification["verdict"],
            status="completed",
            reason=None,
            detail=None,
            canary=canary_classification,
            holdout=holdout_classification,
            holdout_accessed=True,
            bootstrap_draws=draws,
        )
    except KeyboardInterrupt:
        raise
    except StudyBlocked as exc:
        return _result(
            rows=rows,
            verdict="study_blocked",
            status="blocked",
            reason=exc.reason,
            detail=exc.detail,
            canary=canary_classification,
            holdout=None,
            holdout_accessed=holdout_accessed,
            bootstrap_draws=_empty_bootstrap_draws(),
        )
    except Exception as exc:
        return _result(
            rows=rows,
            verdict="study_blocked",
            status="blocked",
            reason="study_execution_failed",
            detail={"message": str(exc), "type": type(exc).__name__},
            canary=canary_classification,
            holdout=None,
            holdout_accessed=holdout_accessed,
            bootstrap_draws=_empty_bootstrap_draws(),
        )


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_bytes(payload)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _started_journal(
    *, registration_sha256: str, preregistration_commit: str
) -> dict[str, Any]:
    return {
        "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
        "completed_row_count": 0,
        "holdout_accessed": False,
        "preregistration_commit": preregistration_commit,
        "registration_sha256": registration_sha256,
        "schema_version": JOURNAL_SCHEMA_VERSION,
        "state": "started",
    }


def _terminal_journal(
    *,
    result: Mapping[str, Any],
    registration_sha256: str,
    preregistration_commit: str,
) -> dict[str, Any]:
    return {
        "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
        "completed_row_count": len(result["rows"]),
        "detail": copy.deepcopy(result["detail"]),
        "holdout_accessed": result["holdout_accessed"],
        "preregistration_commit": preregistration_commit,
        "reason": result["reason"],
        "registration_sha256": registration_sha256,
        "schema_version": JOURNAL_SCHEMA_VERSION,
        "state": "terminal",
        "status": result["status"],
        "verdict": result["verdict"],
    }


def _configuration(
    *,
    registration: Mapping[str, Any],
    registration_sha256: str,
    preregistration_commit: str,
) -> dict[str, Any]:
    return {
        "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
        "preregistration_commit": preregistration_commit,
        "registration": copy.deepcopy(dict(registration)),
        "registration_sha256": registration_sha256,
        "schema_version": CONFIGURATION_SCHEMA_VERSION,
    }


def _trajectory_artifact(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
        "rows": copy.deepcopy(list(rows)),
        "schema_version": ROWS_SCHEMA_VERSION,
    }


def _metrics(result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
        "canary": copy.deepcopy(result["canary"]),
        "detail": copy.deepcopy(result["detail"]),
        "holdout": copy.deepcopy(result["holdout"]),
        "holdout_accessed": result["holdout_accessed"],
        "reason": result["reason"],
        "row_count": len(result["rows"]),
        "schema_version": METRICS_SCHEMA_VERSION,
        "status": result["status"],
        "verdict": result["verdict"],
    }


def _report(metrics: Mapping[str, Any]) -> bytes:
    lines = [
        "# Current Baseline Evidence Study",
        "",
        f"- Verdict: `{metrics['verdict']}`",
        f"- Status: `{metrics['status']}`",
        f"- Retained policy rows: {metrics['row_count']}",
        f"- Holdout accessed: `{str(metrics['holdout_accessed']).lower()}`",
        f"- Formal non-combat RL authorized: `false`",
        f"- Target-supported outcome authorized: `false`",
    ]
    if metrics["reason"] is not None:
        lines.append(f"- Blocking reason: `{metrics['reason']}`")
    canary = metrics["canary"]
    if canary is not None:
        lines.extend(
            [
                "",
                "## Canary",
                "",
                f"- Pairs: {canary['pair_count']}",
                f"- Current mean floor: {canary['current_mean_floor']}",
                (
                    "- Current minus control mean floor: "
                    f"{canary['paired_mean_floor_difference']}"
                ),
                f"- Passed: `{str(canary['passes']).lower()}`",
            ]
        )
    holdout = metrics["holdout"]
    if holdout is not None:
        lines.extend(
            [
                "",
                "## Holdout",
                "",
                f"- Pairs: {holdout['pair_count']}",
                f"- Current mean floor: {holdout['current_mean_floor']}",
                (
                    "- Current 95% bootstrap lower: "
                    f"{holdout['absolute_bootstrap']['lower']}"
                ),
                (
                    "- Current minus control mean floor: "
                    f"{holdout['paired_mean_floor_difference']}"
                ),
                (
                    "- Paired 95% bootstrap lower: "
                    f"{holdout['paired_bootstrap']['lower']}"
                ),
                f"- Passed: `{str(holdout['passes']).lower()}`",
            ]
        )
    return ("\n".join(lines) + "\n").encode("utf-8")


def _artifact_payloads(
    *,
    registration: Mapping[str, Any],
    registration_sha256: str,
    preregistration_commit: str,
    result: Mapping[str, Any],
) -> dict[str, bytes]:
    configuration = _configuration(
        registration=registration,
        registration_sha256=registration_sha256,
        preregistration_commit=preregistration_commit,
    )
    journal = _terminal_journal(
        result=result,
        registration_sha256=registration_sha256,
        preregistration_commit=preregistration_commit,
    )
    metrics = _metrics(result)
    payloads = {
        "bootstrap_draws.json": canonical_json_bytes(result["bootstrap_draws"]),
        "configuration.json": canonical_json_bytes(configuration),
        "execution_journal.json": canonical_json_bytes(journal),
        "metrics.json": canonical_json_bytes(metrics),
        "report.md": _report(metrics),
        "trajectory_rows.json": canonical_json_bytes(
            _trajectory_artifact(result["rows"])
        ),
    }
    manifest = {
        "artifact_hashes": {
            name: {
                "sha256": sha256_bytes(payload),
                "size_bytes": len(payload),
            }
            for name, payload in sorted(payloads.items())
        },
        "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
        "preregistration_commit": preregistration_commit,
        "registration_sha256": registration_sha256,
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "verdict": result["verdict"],
    }
    payloads["artifact_manifest.json"] = canonical_json_bytes(manifest)
    return payloads


def _partial_rows_payload(rows: Sequence[Mapping[str, Any]]) -> bytes:
    return canonical_json_bytes(_trajectory_artifact(rows))


def consume_and_run(
    *,
    registration: Mapping[str, Any],
    registration_sha256: str,
    preregistration_commit: str,
    output_directory: Path | str,
    environment_factory: Callable[[int, str, int], Any],
    session_factory: Callable[[], Any],
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    normalized = validate_registration(copy.deepcopy(registration))
    if not _is_hex(registration_sha256, 64):
        raise StudyBlocked("registration_hash_invalid")
    if not _is_hex(preregistration_commit, 40):
        raise StudyBlocked("preregistration_commit_invalid")
    output = Path(output_directory).resolve()
    if output.exists():
        raise StudyBlocked("output_directory_already_exists")
    output.mkdir(parents=True)
    _write_atomic(
        output / "execution_journal.json",
        canonical_json_bytes(
            _started_journal(
                registration_sha256=registration_sha256,
                preregistration_commit=preregistration_commit,
            )
        ),
    )

    def retain_partial(rows):
        _write_atomic(output / "trajectory_rows.json", _partial_rows_payload(rows))

    result = run_study(
        registration=normalized,
        environment_factory=environment_factory,
        session_factory=session_factory,
        monotonic=monotonic,
        row_callback=retain_partial,
    )
    payloads = _artifact_payloads(
        registration=normalized,
        registration_sha256=registration_sha256,
        preregistration_commit=preregistration_commit,
        result=result,
    )
    for name in CANONICAL_ARTIFACT_NAMES:
        if name == "artifact_manifest.json":
            continue
        _write_atomic(output / name, payloads[name])
    _write_atomic(output / "artifact_manifest.json", payloads["artifact_manifest.json"])
    return result


def _result_from_artifacts(
    *, metrics: Mapping[str, Any], rows: Sequence[Mapping[str, Any]], draws: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
        "bootstrap_draws": copy.deepcopy(dict(draws)),
        "canary": copy.deepcopy(metrics["canary"]),
        "detail": copy.deepcopy(metrics["detail"]),
        "holdout": copy.deepcopy(metrics["holdout"]),
        "holdout_accessed": metrics["holdout_accessed"],
        "reason": metrics["reason"],
        "rows": copy.deepcopy(list(rows)),
        "schema_version": RESULT_SCHEMA_VERSION,
        "status": metrics["status"],
        "verdict": metrics["verdict"],
    }


def verify_artifact_directory(
    *,
    registration: Mapping[str, Any],
    registration_sha256: str,
    output_directory: Path | str,
) -> dict[str, Any]:
    normalized = validate_registration(copy.deepcopy(registration))
    output = Path(output_directory).resolve()
    if not output.is_dir():
        raise StudyBlocked("artifact_directory_missing")
    names = sorted(path.name for path in output.iterdir())
    if names != sorted(CANONICAL_ARTIFACT_NAMES):
        raise StudyBlocked(
            "artifact_inventory_mismatch",
            {"actual": names, "expected": sorted(CANONICAL_ARTIFACT_NAMES)},
        )
    configuration = _load_json(output / "configuration.json", "configuration")
    journal = _load_json(output / "execution_journal.json", "journal")
    metrics = _load_json(output / "metrics.json", "metrics")
    trajectories = _load_json(output / "trajectory_rows.json", "trajectory rows")
    draws = _load_json(output / "bootstrap_draws.json", "bootstrap draws")
    manifest = _load_json(output / "artifact_manifest.json", "manifest")
    if (
        configuration.get("schema_version") != CONFIGURATION_SCHEMA_VERSION
        or journal.get("schema_version") != JOURNAL_SCHEMA_VERSION
        or journal.get("state") != "terminal"
        or metrics.get("schema_version") != METRICS_SCHEMA_VERSION
        or trajectories.get("schema_version") != ROWS_SCHEMA_VERSION
        or draws.get("schema_version") != BOOTSTRAP_SCHEMA_VERSION
        or manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION
    ):
        raise StudyBlocked("artifact_schema_mismatch")
    if not all(
        _canonical_equal(value.get("authority"), ALL_FALSE_AUTHORITY)
        for value in (configuration, journal, metrics, trajectories, manifest)
    ):
        raise StudyBlocked("artifact_authority_mismatch")
    rows = trajectories.get("rows")
    if not isinstance(rows, list) or metrics.get("row_count") != len(rows):
        raise StudyBlocked("artifact_row_count_mismatch")
    if metrics.get("holdout") is not None:
        canary_rows = rows[: len(CANARY_SEEDS) * len(POLICY_IDS)]
        holdout_rows = rows[len(canary_rows) :]
        if not _canonical_equal(metrics.get("canary"), classify_canary(canary_rows)):
            raise StudyBlocked("artifact_canary_metrics_mismatch")
        expected_holdout, expected_draws = classify_holdout(holdout_rows)
        if not _canonical_equal(metrics.get("holdout"), expected_holdout):
            raise StudyBlocked("artifact_holdout_metrics_mismatch")
        if not _canonical_equal(draws, expected_draws):
            raise StudyBlocked("artifact_bootstrap_mismatch")
    elif metrics.get("canary") is not None:
        if not _canonical_equal(metrics.get("canary"), classify_canary(rows)):
            raise StudyBlocked("artifact_canary_metrics_mismatch")
        if not _canonical_equal(draws, _empty_bootstrap_draws()):
            raise StudyBlocked("artifact_bootstrap_mismatch")
    result = _result_from_artifacts(metrics=metrics, rows=rows, draws=draws)
    expected_payloads = _artifact_payloads(
        registration=normalized,
        registration_sha256=registration_sha256,
        preregistration_commit=journal["preregistration_commit"],
        result=result,
    )
    for name, payload in expected_payloads.items():
        if (output / name).read_bytes() != payload:
            raise StudyBlocked("artifact_recomputation_mismatch", name)
    return manifest


def validate_study_seed_inventory(
    value: object, *, implementation_commit: str
) -> dict[str, Any]:
    try:
        inventory = compatibility.validate_seed_inventory(copy.deepcopy(value))
    except compatibility.CompatibilityBlocked as exc:
        raise StudyBlocked(exc.reason, exc.detail) from exc
    if inventory["repository_commit"] != implementation_commit:
        raise StudyBlocked("seed_inventory_commit_mismatch")
    baseline = _expected_preimplementation()
    expected = baseline["seed_exclusion"]
    selected = set(CANARY_SEEDS) | set(HOLDOUT_SEEDS)
    overlap = sorted(selected.intersection(inventory["excluded_seeds"]))
    if overlap:
        raise StudyBlocked("study_seed_overlap", overlap)
    if (
        inventory["source_count"] != expected["source_count"]
        or inventory["row_count"] != expected["row_count"]
        or inventory["excluded_seed_count"] != expected["excluded_seed_count"]
    ):
        raise StudyBlocked("seed_inventory_counts_mismatch")
    planning_equivalent = copy.deepcopy(inventory)
    planning_equivalent["repository_commit"] = baseline["planning_commit"]
    if sha256_bytes(canonical_json_bytes(planning_equivalent)) != expected[
        "inventory_sha256"
    ]:
        raise StudyBlocked("seed_inventory_planning_identity_mismatch")
    return inventory


def _verify_bound_file(
    *, repo_root: Path, binding: Mapping[str, Any], repository_relative: bool
) -> Path:
    normalized = _validate_binding(
        binding, "bound file", repository_relative=repository_relative
    )
    path = (
        (repo_root / normalized["path"]).resolve()
        if repository_relative
        else Path(normalized["path"]).resolve()
    )
    if (
        not path.is_file()
        or path.stat().st_size != normalized["size_bytes"]
        or sha256_file(path) != normalized["sha256"]
    ):
        raise StudyBlocked("bound_file_identity_mismatch", normalized["path"])
    return path


def _verify_sources_at_commit(
    repo_root: Path, commit: str, source_files: Sequence[str]
) -> None:
    for relative in source_files:
        path = (repo_root / relative).resolve()
        try:
            canonical_relative = path.relative_to(repo_root).as_posix()
        except ValueError as exc:
            raise StudyBlocked("source_file_escapes_repository", relative) from exc
        if _git_bytes(repo_root, "show", f"{commit}:{canonical_relative}") != path.read_bytes():
            raise StudyBlocked("source_differs_from_implementation_commit", relative)


def validate_registration_evidence(
    registration: Mapping[str, Any],
    repo_root: Path | str,
    *,
    require_output_absent: bool = True,
) -> tuple[dict[str, Any], Path]:
    normalized = validate_registration(copy.deepcopy(registration))
    root = Path(repo_root).resolve()
    identity = normalized["identity"]
    preimplementation_path = _verify_bound_file(
        repo_root=root,
        binding=identity["preimplementation"],
        repository_relative=True,
    )
    validate_preimplementation(_load_json(preimplementation_path, "preimplementation"))
    inventory_path = _verify_bound_file(
        repo_root=root,
        binding=identity["seed_inventory"],
        repository_relative=True,
    )
    inventory = validate_study_seed_inventory(
        _load_json(inventory_path, "seed inventory"),
        implementation_commit=identity["implementation"]["commit"],
    )
    try:
        compatibility.verify_seed_inventory(inventory, root)
    except compatibility.CompatibilityBlocked as exc:
        raise StudyBlocked(exc.reason, exc.detail) from exc
    implementation = identity["implementation"]
    if hash_bound_files(root, identity["adapter_source_files"]) != identity[
        "adapter_provenance"
    ]["adapter_source_sha256"]:
        raise StudyBlocked("adapter_source_hash_mismatch")
    if hash_bound_files(root, implementation["source_files"]) != implementation[
        "source_sha256"
    ]:
        raise StudyBlocked("implementation_source_hash_mismatch")
    _verify_sources_at_commit(root, implementation["commit"], implementation["source_files"])
    _verify_bound_file(
        repo_root=root,
        binding=identity["event_contract"],
        repository_relative=True,
    )
    _verify_bound_file(
        repo_root=root, binding=identity["metadata"], repository_relative=False
    )
    _verify_bound_file(
        repo_root=root, binding=identity["module"], repository_relative=False
    )
    runtime_binding = {
        "path": identity["runtime"]["executable"],
        "sha256": identity["runtime"]["sha256"],
        "size_bytes": identity["runtime"]["size_bytes"],
    }
    _verify_bound_file(
        repo_root=root, binding=runtime_binding, repository_relative=False
    )
    if (
        str(Path(sys.executable).resolve()) != identity["runtime"]["executable"]
        or sys.version.split()[0] != identity["runtime"]["python"]
    ):
        raise StudyBlocked("runtime_identity_mismatch")
    simulator = identity["simulator"]
    simulator_path = Path(simulator["path"]).resolve()
    if not simulator_path.is_dir():
        raise StudyBlocked("simulator_path_missing")
    if _git_text(simulator_path, "rev-parse", "HEAD") != simulator["commit"]:
        raise StudyBlocked("simulator_commit_mismatch")
    source_sha256, source_count = hash_compiled_simulator_sources(simulator_path)
    if (
        source_sha256 != simulator["source_sha256"]
        or source_count != simulator["source_file_count"]
    ):
        raise StudyBlocked("simulator_source_identity_mismatch")
    if require_output_absent and (root / normalized["output"]["directory"]).exists():
        raise StudyBlocked("output_directory_already_exists")
    return inventory, inventory_path


def _preflight(
    *,
    implementation_commit: str,
    registration_binding: Mapping[str, Any],
    seed_inventory_binding: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
        "checks": {
            "environment_constructed": False,
            "execution_authorization_present": False,
            "external_bytes_hashed": True,
            "native_module_imported": False,
            "output_root_absent": True,
            "registration_canonical": True,
            "seed_inventory_recomputed": True,
            "study_seed_environment_accessed": False,
            "tracked_clean_before_prepare": True,
        },
        "implementation_commit": implementation_commit,
        "next_gate": {
            "action": "commit_and_push_preregistration_then_stop_for_execution_approval",
            "execute_before_gate": False,
        },
        "registration": copy.deepcopy(dict(registration_binding)),
        "schema_version": PREFLIGHT_SCHEMA_VERSION,
        "seed_inventory": copy.deepcopy(dict(seed_inventory_binding)),
    }


def validate_preflight(
    value: object,
    *,
    implementation_commit: str,
    registration_binding: Mapping[str, Any],
    seed_inventory_binding: Mapping[str, Any],
) -> dict[str, Any]:
    preflight = _mapping(value, "preflight")
    expected = _preflight(
        implementation_commit=implementation_commit,
        registration_binding=registration_binding,
        seed_inventory_binding=seed_inventory_binding,
    )
    if not _canonical_equal(preflight, expected):
        raise StudyBlocked("preflight_identity_mismatch")
    return preflight


def prepare_registration(repo_root: Path | str = _REPO_ROOT) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    managed = (
        root / DEFAULT_SEED_INVENTORY_PATH,
        root / DEFAULT_REGISTRATION_PATH,
        root / DEFAULT_PREFLIGHT_PATH,
        root / DEFAULT_EXECUTION_AUTHORIZATION_PATH,
        root / DEFAULT_OUTPUT_DIRECTORY,
    )
    if any(path.exists() for path in managed):
        raise StudyBlocked("managed_evidence_already_exists")
    implementation_commit = _assert_clean_pushed_head(root)
    try:
        inventory = compatibility.build_tracked_seed_inventory(root)
    except compatibility.CompatibilityBlocked as exc:
        raise StudyBlocked(exc.reason, exc.detail) from exc
    inventory = validate_study_seed_inventory(
        inventory, implementation_commit=implementation_commit
    )
    baseline = _expected_preimplementation(root)
    external = baseline["external_identity_expectations"]
    module_path = _verify_bound_file(
        repo_root=root, binding=external["module"], repository_relative=False
    )
    metadata_path = _verify_bound_file(
        repo_root=root, binding=external["metadata"], repository_relative=False
    )
    runtime_path = Path(external["runtime"]["executable"]).resolve()
    if (
        runtime_path != Path(sys.executable).resolve()
        or sys.version.split()[0] != external["runtime"]["python"]
    ):
        raise StudyBlocked("runtime_identity_mismatch")
    runtime_binding = _file_binding(runtime_path, str(runtime_path))
    simulator = external["simulator"]
    simulator_path = Path(simulator["path"]).resolve()
    if _git_text(simulator_path, "rev-parse", "HEAD") != simulator["commit"]:
        raise StudyBlocked("simulator_commit_mismatch")
    simulator_sha256, simulator_count = hash_compiled_simulator_sources(simulator_path)
    if (
        simulator_sha256 != simulator["source_sha256"]
        or simulator_count != simulator["source_file_count"]
    ):
        raise StudyBlocked("simulator_source_identity_mismatch")

    inventory_bytes = canonical_json_bytes(inventory)
    inventory_binding = {
        "path": DEFAULT_SEED_INVENTORY_PATH,
        "sha256": sha256_bytes(inventory_bytes),
        "size_bytes": len(inventory_bytes),
    }
    event_semantics = reachable_event_option_semantics_identity()
    event_contract_path = event_semantics["observation_contract"]["path"]
    identity = {
        "adapter_provenance": _registered_adapter_provenance(),
        "adapter_source_files": list(compatibility.ADAPTER_SOURCE_FILES),
        "event_contract": _file_binding(
            root / event_contract_path, event_contract_path
        ),
        "event_semantics": event_semantics,
        "implementation": {
            "commit": implementation_commit,
            "source_files": list(IMPLEMENTATION_SOURCE_FILES),
            "source_sha256": hash_bound_files(root, IMPLEMENTATION_SOURCE_FILES),
        },
        "metadata": _file_binding(metadata_path, str(metadata_path)),
        "module": _file_binding(module_path, str(module_path)),
        "preimplementation": {
            "path": PREIMPLEMENTATION_PATH,
            "sha256": EXPECTED_PREIMPLEMENTATION_SHA256,
            "size_bytes": EXPECTED_PREIMPLEMENTATION_SIZE_BYTES,
        },
        "runtime": {
            "executable": runtime_binding["path"],
            "python": sys.version.split()[0],
            "sha256": runtime_binding["sha256"],
            "size_bytes": runtime_binding["size_bytes"],
        },
        "seed_inventory": inventory_binding,
        "simulator": copy.deepcopy(simulator),
    }
    registration = build_registration(identity=identity)
    registration_bytes = canonical_json_bytes(registration)
    registration_binding = {
        "path": DEFAULT_REGISTRATION_PATH,
        "sha256": sha256_bytes(registration_bytes),
        "size_bytes": len(registration_bytes),
    }
    preflight = _preflight(
        implementation_commit=implementation_commit,
        registration_binding=registration_binding,
        seed_inventory_binding=inventory_binding,
    )
    _write_atomic(root / DEFAULT_SEED_INVENTORY_PATH, inventory_bytes)
    _write_atomic(root / DEFAULT_REGISTRATION_PATH, registration_bytes)
    validate_registration_evidence(registration, root)
    _write_atomic(root / DEFAULT_PREFLIGHT_PATH, canonical_json_bytes(preflight))
    validate_preflight(
        _load_json(root / DEFAULT_PREFLIGHT_PATH, "preflight"),
        implementation_commit=implementation_commit,
        registration_binding=registration_binding,
        seed_inventory_binding=inventory_binding,
    )
    return {
        "implementation_commit": implementation_commit,
        "preflight_path": DEFAULT_PREFLIGHT_PATH,
        "registration_path": DEFAULT_REGISTRATION_PATH,
        "registration_sha256": registration_binding["sha256"],
        "seed_inventory_path": DEFAULT_SEED_INVENTORY_PATH,
        "seed_inventory_sha256": inventory_binding["sha256"],
    }


def _publish_terminal_result(
    *,
    output: Path,
    registration: Mapping[str, Any],
    registration_sha256: str,
    preregistration_commit: str,
    result: Mapping[str, Any],
) -> None:
    payloads = _artifact_payloads(
        registration=registration,
        registration_sha256=registration_sha256,
        preregistration_commit=preregistration_commit,
        result=result,
    )
    for name in CANONICAL_ARTIFACT_NAMES:
        if name == "artifact_manifest.json":
            continue
        _write_atomic(output / name, payloads[name])
    _write_atomic(output / "artifact_manifest.json", payloads["artifact_manifest.json"])


def _blocked_result(reason: str, detail: object | None = None):
    return _result(
        rows=[],
        verdict="study_blocked",
        status="blocked",
        reason=reason,
        detail=detail,
        canary=None,
        holdout=None,
        holdout_accessed=False,
        bootstrap_draws=_empty_bootstrap_draws(),
    )


def execute_registered(repo_root: Path | str = _REPO_ROOT) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    registration_path = root / DEFAULT_REGISTRATION_PATH
    authorization_path = root / DEFAULT_EXECUTION_AUTHORIZATION_PATH
    preflight_path = root / DEFAULT_PREFLIGHT_PATH
    if not registration_path.is_file():
        raise StudyBlocked("registration_path_mismatch")
    if not authorization_path.is_file():
        raise StudyBlocked("execution_authorization_missing")
    if not preflight_path.is_file():
        raise StudyBlocked("preflight_missing")
    current_head = _assert_clean_pushed_head(root)
    authorization_bytes = authorization_path.read_bytes()
    authorization_relative = authorization_path.relative_to(root).as_posix()
    if _git_bytes(root, "show", f"{current_head}:{authorization_relative}") != authorization_bytes:
        raise StudyBlocked("pushed_execution_authorization_mismatch")
    authorization = _load_json(authorization_path, "execution authorization")
    preregistration_commit = authorization.get("preregistration_commit")
    if not _is_hex(preregistration_commit, 40):
        raise StudyBlocked("execution_commit_mismatch")
    for path in (
        registration_path,
        root / DEFAULT_SEED_INVENTORY_PATH,
        preflight_path,
    ):
        relative = path.relative_to(root).as_posix()
        if (
            not path.is_file()
            or _git_bytes(root, "show", f"{preregistration_commit}:{relative}")
            != path.read_bytes()
        ):
            raise StudyBlocked("preregistration_evidence_mismatch", relative)
    registration = load_registration(registration_path)
    registration_sha256 = sha256_file(registration_path)
    validate_execution_authorization(
        authorization,
        registration=registration,
        registration_sha256=registration_sha256,
        preregistration_commit=preregistration_commit,
    )
    validate_registration_evidence(registration, root)
    registration_binding = {
        "path": DEFAULT_REGISTRATION_PATH,
        "sha256": registration_sha256,
        "size_bytes": registration_path.stat().st_size,
    }
    inventory_binding = registration["identity"]["seed_inventory"]
    validate_preflight(
        _load_json(preflight_path, "preflight"),
        implementation_commit=registration["identity"]["implementation"]["commit"],
        registration_binding=registration_binding,
        seed_inventory_binding=inventory_binding,
    )

    output = root / registration["output"]["directory"]
    if output.exists():
        raise StudyBlocked("output_directory_already_exists")
    output.mkdir(parents=True)
    _write_atomic(
        output / "execution_journal.json",
        canonical_json_bytes(
            _started_journal(
                registration_sha256=registration_sha256,
                preregistration_commit=preregistration_commit,
            )
        ),
    )
    identity = registration["identity"]
    try:
        native_module = load_native_module(
            identity["module"]["path"], dll_directories=FIXED_DLL_DIRECTORIES
        )
        try:
            actual_provenance = compatibility.collect_native_identity(
                module_path=identity["module"]["path"],
                simulator_repo=identity["simulator"]["path"],
                repo_root=root,
                native_module=native_module,
                adapter_commit=identity["adapter_provenance"]["adapter_commit"],
            )
        except compatibility.CompatibilityBlocked as exc:
            raise StudyBlocked(exc.reason, exc.detail) from exc
        if not _canonical_equal(actual_provenance, identity["adapter_provenance"]):
            raise StudyBlocked("native_identity_mismatch")
        metadata = MetadataCatalog(Path(identity["metadata"]["path"]))

        def environment_factory(seed: int, _policy_id: str, _replay_index: int):
            return NativeSimulatorEnvironment(
                native_module.Environment(seed, CURRENT_POLICY["ascension"]),
                actual_provenance,
            )

        def session_factory():
            return CurrentPolicyBridgeSession(
                metadata=metadata,
                current_policy=CURRENT_POLICY,
                event_semantics_identity=identity["event_semantics"],
                simulator_provenance=actual_provenance,
            )

        def retain_partial(rows):
            _write_atomic(output / "trajectory_rows.json", _partial_rows_payload(rows))

        result = run_study(
            registration=registration,
            environment_factory=environment_factory,
            session_factory=session_factory,
            row_callback=retain_partial,
        )
    except KeyboardInterrupt:
        raise
    except StudyBlocked as exc:
        result = _blocked_result(exc.reason, exc.detail)
    except (OSError, RuntimeError, SimulatorAdapterError) as exc:
        result = _blocked_result(
            "native_module_load_failed",
            {"message": str(exc), "type": type(exc).__name__},
        )
    except Exception as exc:
        result = _blocked_result(
            "study_execution_failed",
            {"message": str(exc), "type": type(exc).__name__},
        )
    _publish_terminal_result(
        output=output,
        registration=registration,
        registration_sha256=registration_sha256,
        preregistration_commit=preregistration_commit,
        result=result,
    )
    verify_artifact_directory(
        registration=registration,
        registration_sha256=registration_sha256,
        output_directory=output,
    )
    return {
        "output_directory": registration["output"]["directory"],
        "reason": result["reason"],
        "status": result["status"],
        "verdict": result["verdict"],
    }


def verify_registered(repo_root: Path | str = _REPO_ROOT) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    registration_path = root / DEFAULT_REGISTRATION_PATH
    registration = load_registration(registration_path)
    validate_registration_evidence(
        registration, root, require_output_absent=False
    )
    manifest = verify_artifact_directory(
        registration=registration,
        registration_sha256=sha256_file(registration_path),
        output_directory=root / registration["output"]["directory"],
    )
    return {
        "output_directory": registration["output"]["directory"],
        "verdict": manifest["verdict"],
        "verified_without_native_loading": True,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare, execute, or verify the fixed Current baseline study."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("prepare")
    commands.add_parser("execute")
    commands.add_parser("verify")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare_registration()
        elif args.command == "execute":
            result = execute_registered()
        else:
            result = verify_registered()
    except StudyBlocked as exc:
        print(
            json.dumps(
                {"detail": exc.detail, "reason": exc.reason}, sort_keys=True
            )
        )
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
