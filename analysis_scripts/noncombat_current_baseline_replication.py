"""Run the unique post-final-repair Current baseline replication."""

from __future__ import annotations

import argparse
import copy
import sys
import threading
from collections.abc import Mapping, Sequence
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Any
from unittest.mock import patch


_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import analysis_scripts.noncombat_current_baseline_evidence_study as predecessor
import analysis_scripts.noncombat_reachable_event_native_compatibility as compatibility
from analysis_scripts.noncombat_current_policy_simulator_bridge import hash_bound_files
from analysis_scripts.noncombat_simulator_adapter import (
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
)


PREIMPLEMENTATION_SCHEMA_VERSION = (
    "noncombat-current-baseline-replication-preimplementation-v1"
)
REGISTRATION_SCHEMA_VERSION = "noncombat-current-baseline-replication-registration-v1"
EXECUTION_AUTHORIZATION_SCHEMA_VERSION = (
    "noncombat-current-baseline-replication-execution-authorization-v1"
)
RESULT_SCHEMA_VERSION = "noncombat-current-baseline-replication-result-v1"
JOURNAL_SCHEMA_VERSION = "noncombat-current-baseline-replication-journal-v1"
CONFIGURATION_SCHEMA_VERSION = "noncombat-current-baseline-replication-configuration-v1"
ROWS_SCHEMA_VERSION = "noncombat-current-baseline-replication-rows-v1"
BOOTSTRAP_SCHEMA_VERSION = "noncombat-current-baseline-replication-bootstrap-v1"
METRICS_SCHEMA_VERSION = "noncombat-current-baseline-replication-metrics-v1"
MANIFEST_SCHEMA_VERSION = "noncombat-current-baseline-replication-manifest-v1"
PREFLIGHT_SCHEMA_VERSION = "noncombat-current-baseline-replication-preflight-v1"

PREIMPLEMENTATION_PATH = (
    "reports/noncombat_current_baseline_replication_20260805_preimplementation.json"
)
DEFAULT_SEED_INVENTORY_PATH = (
    "reports/noncombat_current_baseline_replication_20260805_seed_inventory.json"
)
DEFAULT_REGISTRATION_PATH = (
    "reports/noncombat_current_baseline_replication_20260805_input.json"
)
DEFAULT_PREFLIGHT_PATH = (
    "reports/noncombat_current_baseline_replication_20260805_preflight.json"
)
DEFAULT_EXECUTION_AUTHORIZATION_PATH = (
    "reports/noncombat_current_baseline_replication_20260805_"
    "execution_authorization.json"
)
DEFAULT_OUTPUT_DIRECTORY = "reports/noncombat_current_baseline_replication_20260805"

EXPECTED_PREIMPLEMENTATION_SHA256 = (
    "c8ba9f4d0c496c3698e036d01cc222b8286522475bd0d1133c104f8161eb5675"
)
EXPECTED_PREIMPLEMENTATION_SIZE_BYTES = 12106
SEARCH_START = 60000
CANARY_COUNT = 16
HOLDOUT_COUNT = 64
TOTAL_COHORT_COUNT = CANARY_COUNT + HOLDOUT_COUNT

GATES = copy.deepcopy(predecessor.GATES)
LIMITS = copy.deepcopy(predecessor.LIMITS)
ALL_FALSE_AUTHORITY = copy.deepcopy(predecessor.ALL_FALSE_AUTHORITY)
CURRENT_POLICY = copy.deepcopy(predecessor.CURRENT_POLICY)
CONTROL_POLICY = copy.deepcopy(predecessor.CONTROL_POLICY)
POLICY_IDS = predecessor.POLICY_IDS
CURRENT_POLICY_ID = predecessor.CURRENT_POLICY_ID
CONTROL_POLICY_ID = predecessor.CONTROL_POLICY_ID
DECLARED_SUPPORT_REASON = predecessor.DECLARED_SUPPORT_REASON
REPLAY_COUNT = predecessor.REPLAY_COUNT
MAX_DECISIONS_PER_EPISODE = predecessor.MAX_DECISIONS_PER_EPISODE
CANARY_POLICY_EPISODE_LIMIT = predecessor.CANARY_POLICY_EPISODE_LIMIT
HOLDOUT_POLICY_EPISODE_LIMIT = predecessor.HOLDOUT_POLICY_EPISODE_LIMIT
CANARY_MAX_WALL_SECONDS = predecessor.CANARY_MAX_WALL_SECONDS
TOTAL_MAX_WALL_SECONDS = predecessor.TOTAL_MAX_WALL_SECONDS
BOOTSTRAP_RESAMPLES = predecessor.BOOTSTRAP_RESAMPLES
BOOTSTRAP_SEED = predecessor.BOOTSTRAP_SEED
BOOTSTRAP_CONFIDENCE = predecessor.BOOTSTRAP_CONFIDENCE
TARGET_CATEGORIES = predecessor.TARGET_CATEGORIES
CANONICAL_ARTIFACT_NAMES = predecessor.CANONICAL_ARTIFACT_NAMES
FIXED_DLL_DIRECTORIES = predecessor.FIXED_DLL_DIRECTORIES

IMPLEMENTATION_SOURCE_FILES = tuple(
    dict.fromkeys(
        (
            "analysis_scripts/noncombat_current_baseline_replication.py",
            "tests/test_noncombat_current_baseline_replication.py",
            *predecessor.IMPLEMENTATION_SOURCE_FILES,
        )
    )
)
EXACT_EXECUTION_COMMAND = (
    r"D:\anaconda\envs\stsai\python.exe",
    "analysis_scripts/noncombat_current_baseline_replication.py",
    "execute",
)

ReplicationBlocked = predecessor.StudyBlocked

_CONTRACT_LOCK = threading.RLock()
_ORIGINAL_CLASSIFY_CANARY = predecessor.classify_canary
_ORIGINAL_CLASSIFY_HOLDOUT = predecessor.classify_holdout
_ORIGINAL_RUN_STUDY = predecessor.run_study
_ORIGINAL_BLOCKED_RESULT = predecessor._blocked_result
_ORIGINAL_REPORT = predecessor._report
_ORIGINAL_VALIDATE_REGISTRATION_EVIDENCE = predecessor.validate_registration_evidence
_ORIGINAL_PREPARE_REGISTRATION = predecessor.prepare_registration
_ORIGINAL_EXECUTE_REGISTERED = predecessor.execute_registered
_ORIGINAL_VERIFY_REGISTERED = predecessor.verify_registered

_MANAGED_SEED_SOURCE_EXCLUSIONS = {
    DEFAULT_SEED_INVENTORY_PATH,
    DEFAULT_REGISTRATION_PATH,
    DEFAULT_PREFLIGHT_PATH,
    DEFAULT_EXECUTION_AUTHORIZATION_PATH,
}

_SCHEMA_PATCHES = {
    "PREIMPLEMENTATION_SCHEMA_VERSION": PREIMPLEMENTATION_SCHEMA_VERSION,
    "REGISTRATION_SCHEMA_VERSION": REGISTRATION_SCHEMA_VERSION,
    "EXECUTION_AUTHORIZATION_SCHEMA_VERSION": EXECUTION_AUTHORIZATION_SCHEMA_VERSION,
    "RESULT_SCHEMA_VERSION": RESULT_SCHEMA_VERSION,
    "JOURNAL_SCHEMA_VERSION": JOURNAL_SCHEMA_VERSION,
    "CONFIGURATION_SCHEMA_VERSION": CONFIGURATION_SCHEMA_VERSION,
    "ROWS_SCHEMA_VERSION": ROWS_SCHEMA_VERSION,
    "BOOTSTRAP_SCHEMA_VERSION": BOOTSTRAP_SCHEMA_VERSION,
    "METRICS_SCHEMA_VERSION": METRICS_SCHEMA_VERSION,
    "MANIFEST_SCHEMA_VERSION": MANIFEST_SCHEMA_VERSION,
    "PREFLIGHT_SCHEMA_VERSION": PREFLIGHT_SCHEMA_VERSION,
}
_PATH_PATCHES = {
    "PREIMPLEMENTATION_PATH": PREIMPLEMENTATION_PATH,
    "DEFAULT_SEED_INVENTORY_PATH": DEFAULT_SEED_INVENTORY_PATH,
    "DEFAULT_REGISTRATION_PATH": DEFAULT_REGISTRATION_PATH,
    "DEFAULT_PREFLIGHT_PATH": DEFAULT_PREFLIGHT_PATH,
    "DEFAULT_EXECUTION_AUTHORIZATION_PATH": DEFAULT_EXECUTION_AUTHORIZATION_PATH,
    "DEFAULT_OUTPUT_DIRECTORY": DEFAULT_OUTPUT_DIRECTORY,
    "EXPECTED_PREIMPLEMENTATION_SHA256": EXPECTED_PREIMPLEMENTATION_SHA256,
    "EXPECTED_PREIMPLEMENTATION_SIZE_BYTES": EXPECTED_PREIMPLEMENTATION_SIZE_BYTES,
}


def _cohort_values(value: object) -> tuple[tuple[int, ...], tuple[int, ...]]:
    registration = predecessor._mapping(value, "registration")
    cohorts = predecessor._mapping(registration.get("cohorts"), "registration.cohorts")
    if set(cohorts) != {"canary", "holdout"}:
        raise ReplicationBlocked("registration_cohort_keys_mismatch")
    canary = tuple(predecessor._sequence(cohorts["canary"], "canary cohort"))
    holdout = tuple(predecessor._sequence(cohorts["holdout"], "holdout cohort"))
    combined = canary + holdout
    if (
        len(canary) != CANARY_COUNT
        or len(holdout) != HOLDOUT_COUNT
        or any(isinstance(seed, bool) or not isinstance(seed, int) for seed in combined)
        or list(combined) != sorted(set(combined))
        or any(seed < SEARCH_START for seed in combined)
    ):
        raise ReplicationBlocked("registration_cohort_shape_mismatch")
    return canary, holdout


def select_replication_cohorts(
    inventory: Mapping[str, Any],
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    try:
        normalized = compatibility.validate_seed_inventory(copy.deepcopy(inventory))
    except compatibility.CompatibilityBlocked as exc:
        raise ReplicationBlocked(exc.reason, exc.detail) from exc
    excluded = set(normalized["excluded_seeds"])
    selected: list[int] = []
    candidate = SEARCH_START
    while len(selected) < TOTAL_COHORT_COUNT:
        if candidate not in excluded:
            selected.append(candidate)
        candidate += 1
    return tuple(selected[:CANARY_COUNT]), tuple(selected[CANARY_COUNT:])


def build_replication_seed_inventory(repo_root: Path | str) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    documents = compatibility.discover_seed_documents(root)
    documents = {
        path: payload
        for path, payload in documents.items()
        if path not in _MANAGED_SEED_SOURCE_EXCLUSIONS
        and not path.startswith(f"{DEFAULT_OUTPUT_DIRECTORY}/")
    }
    return compatibility.build_seed_inventory_from_documents(
        documents,
        repository_commit=predecessor._git_text(root, "rev-parse", "HEAD"),
    )


def verify_replication_seed_inventory(
    inventory: Mapping[str, Any], repo_root: Path | str
) -> dict[str, Any]:
    try:
        normalized = compatibility.validate_seed_inventory(copy.deepcopy(inventory))
    except compatibility.CompatibilityBlocked as exc:
        raise ReplicationBlocked(exc.reason, exc.detail) from exc
    root = Path(repo_root).resolve()
    documents = compatibility.discover_seed_documents(root)
    documents = {
        path: payload
        for path, payload in documents.items()
        if path not in _MANAGED_SEED_SOURCE_EXCLUSIONS
        and not path.startswith(f"{DEFAULT_OUTPUT_DIRECTORY}/")
    }
    recomputed = compatibility.build_seed_inventory_from_documents(
        documents,
        repository_commit=normalized["repository_commit"],
    )
    if canonical_json_bytes(normalized) != canonical_json_bytes(recomputed):
        raise ReplicationBlocked("seed_inventory_recomputation_mismatch")
    return recomputed


def _validate_replication_inventory(
    value: object,
    *,
    implementation_commit: str,
    canary: Sequence[int],
    holdout: Sequence[int],
) -> dict[str, Any]:
    try:
        inventory = compatibility.validate_seed_inventory(copy.deepcopy(value))
    except compatibility.CompatibilityBlocked as exc:
        raise ReplicationBlocked(exc.reason, exc.detail) from exc
    if inventory["repository_commit"] != implementation_commit:
        raise ReplicationBlocked("seed_inventory_commit_mismatch")
    expected_canary, expected_holdout = select_replication_cohorts(inventory)
    if tuple(canary) != expected_canary or tuple(holdout) != expected_holdout:
        raise ReplicationBlocked(
            "replication_cohort_selection_mismatch",
            {
                "actual_canary": list(canary),
                "actual_holdout": list(holdout),
                "expected_canary": list(expected_canary),
                "expected_holdout": list(expected_holdout),
            },
        )
    return inventory


def _transform_verdicts(value: Mapping[str, Any]) -> dict[str, Any]:
    transformed = copy.deepcopy(dict(value))
    verdicts = {
        "study_blocked": "replication_blocked",
        "study_stopped_at_canary": "replication_stopped_at_canary",
        "study_valid_with_baseline_floor": "replication_valid_with_baseline_floor",
        "study_valid_without_baseline_floor": "replication_valid_without_baseline_floor",
    }
    if transformed.get("verdict") in verdicts:
        transformed["verdict"] = verdicts[transformed["verdict"]]
    for field in ("canary", "holdout"):
        nested = transformed.get(field)
        if isinstance(nested, Mapping) and nested.get("verdict") in verdicts:
            transformed[field] = {
                **copy.deepcopy(dict(nested)),
                "verdict": verdicts[nested["verdict"]],
            }
    return transformed


def _replication_classify_canary(rows):
    return _transform_verdicts(_ORIGINAL_CLASSIFY_CANARY(rows))


def _replication_classify_holdout(rows):
    classification, draws = _ORIGINAL_CLASSIFY_HOLDOUT(rows)
    return _transform_verdicts(classification), draws


def _replication_run_study(**kwargs):
    return _transform_verdicts(_ORIGINAL_RUN_STUDY(**kwargs))


def _replication_blocked_result(reason: str, detail: object | None = None):
    return _transform_verdicts(_ORIGINAL_BLOCKED_RESULT(reason, detail))


def _replication_report(metrics: Mapping[str, Any]) -> bytes:
    payload = _ORIGINAL_REPORT(metrics)
    prefix = b"# Current Baseline Evidence Study\n"
    if not payload.startswith(prefix):
        raise ReplicationBlocked("report_predecessor_identity_mismatch")
    return b"# Final Current Baseline Replication\n" + payload[len(prefix) :]


def _verify_binding(repo_root: Path, binding: Mapping[str, Any]) -> Path:
    normalized = predecessor._validate_binding(
        binding, "lineage binding", repository_relative=True
    )
    path = (repo_root / normalized["path"]).resolve()
    if (
        not path.is_file()
        or path.stat().st_size != normalized["size_bytes"]
        or sha256_file(path) != normalized["sha256"]
    ):
        raise ReplicationBlocked("lineage_binding_mismatch", normalized["path"])
    return path


def classify_final_replication_eligibility(
    *,
    attempt_identity: str,
    verdict: str,
    reason: object | None,
    detail: object | None,
    completed_row_count: int,
    canary_complete: bool,
    holdout_accessed: bool,
) -> str:
    if (
        attempt_identity == "consumed_integrated_study"
        and verdict == "study_blocked"
        and reason == "card_metadata_cost_invalid"
        and detail == "Injury"
        and completed_row_count == 18
        and canary_complete is False
        and holdout_accessed is False
    ):
        return "ready_for_final_baseline_replication_proposal"
    return "baseline_lane_terminal"


def validate_lineage_evidence(repo_root: Path | str = _REPO_ROOT) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    baseline = load_preimplementation(root / PREIMPLEMENTATION_PATH)
    for group in ("closure", "consumed_study"):
        for binding in baseline["evidence"][group]:
            _verify_binding(root, binding)

    planning = baseline["planning"]
    if planning != {**planning, "pushed": True}:
        raise ReplicationBlocked("planning_push_identity_mismatch")
    for binding in planning["artifacts"]:
        normalized = predecessor._validate_binding(
            binding, "planning binding", repository_relative=True
        )
        payload = predecessor._git_bytes(
            root, "show", f"{planning['commit']}:{normalized['path']}"
        )
        if (
            len(payload) != normalized["size_bytes"]
            or sha256_bytes(payload) != normalized["sha256"]
        ):
            raise ReplicationBlocked(
                "planning_artifact_identity_mismatch", normalized["path"]
            )

    source = baseline["source_identity"]
    if hash_bound_files(root, source["files"]) != source["sha256"]:
        raise ReplicationBlocked("predecessor_source_identity_mismatch")

    journal = predecessor._load_json(
        root
        / "reports/noncombat_current_baseline_evidence_study_20260803/"
        "execution_journal.json",
        "consumed study journal",
    )
    if (
        journal.get("state") != "terminal"
        or journal.get("status") != "blocked"
        or journal.get("verdict") != "study_blocked"
        or journal.get("reason") != "card_metadata_cost_invalid"
        or journal.get("detail") != "Injury"
        or journal.get("completed_row_count") != 18
        or journal.get("holdout_accessed") is not False
    ):
        raise ReplicationBlocked("consumed_study_terminal_identity_mismatch")

    metrics = predecessor._load_json(
        root / "reports/noncombat_current_baseline_evidence_study_20260803/metrics.json",
        "consumed study metrics",
    )
    rows = predecessor._load_json(
        root
        / "reports/noncombat_current_baseline_evidence_study_20260803/"
        "trajectory_rows.json",
        "consumed study rows",
    )
    if (
        metrics.get("row_count") != 18
        or metrics.get("canary") is not None
        or metrics.get("holdout") is not None
        or metrics.get("holdout_accessed") is not False
        or len(rows.get("rows", [])) != 18
    ):
        raise ReplicationBlocked("consumed_study_partial_rows_mismatch")
    if classify_final_replication_eligibility(
        attempt_identity="consumed_integrated_study",
        verdict=journal["verdict"],
        reason=journal["reason"],
        detail=journal["detail"],
        completed_row_count=journal["completed_row_count"],
        canary_complete=metrics["canary"] is not None,
        holdout_accessed=journal["holdout_accessed"],
    ) != "ready_for_final_baseline_replication_proposal":
        raise ReplicationBlocked("final_replication_exception_not_permitted")

    registration = predecessor._load_json(
        root / "reports/noncombat_current_baseline_evidence_study_20260803_input.json",
        "consumed study registration",
    )
    expected_policies = {
        "control": copy.deepcopy(CONTROL_POLICY),
        "current": copy.deepcopy(CURRENT_POLICY),
    }
    if (
        canonical_json_bytes(registration.get("policies"))
        != canonical_json_bytes(expected_policies)
        or canonical_json_bytes(registration.get("gates"))
        != canonical_json_bytes(GATES)
        or canonical_json_bytes(registration.get("limits"))
        != canonical_json_bytes(LIMITS)
    ):
        raise ReplicationBlocked("consumed_contract_drift")
    return copy.deepcopy(baseline)


def _replication_validate_registration_evidence(
    registration,
    repo_root,
    *,
    require_output_absent: bool = True,
):
    result = _ORIGINAL_VALIDATE_REGISTRATION_EVIDENCE(
        registration,
        repo_root,
        require_output_absent=require_output_absent,
    )
    validate_lineage_evidence(repo_root)
    return result


@contextmanager
def _contract_context(canary: Sequence[int], holdout: Sequence[int]):
    canary_tuple = tuple(canary)
    holdout_tuple = tuple(holdout)
    if len(canary_tuple) != CANARY_COUNT or len(holdout_tuple) != HOLDOUT_COUNT:
        raise ReplicationBlocked("contract_cohort_shape_mismatch")
    with _CONTRACT_LOCK:
        with ExitStack() as stack:
            patches = {
                **_SCHEMA_PATCHES,
                **_PATH_PATCHES,
                "CANARY_SEEDS": canary_tuple,
                "HOLDOUT_SEEDS": holdout_tuple,
                "GATES": GATES,
                "LIMITS": LIMITS,
                "IMPLEMENTATION_SOURCE_FILES": IMPLEMENTATION_SOURCE_FILES,
                "EXACT_EXECUTION_COMMAND": EXACT_EXECUTION_COMMAND,
                "classify_canary": _replication_classify_canary,
                "classify_holdout": _replication_classify_holdout,
                "run_study": _replication_run_study,
                "_blocked_result": _replication_blocked_result,
                "_report": _replication_report,
                "validate_registration_evidence": (
                    _replication_validate_registration_evidence
                ),
                "validate_study_seed_inventory": (
                    lambda value, *, implementation_commit: (
                        _validate_replication_inventory(
                            value,
                            implementation_commit=implementation_commit,
                            canary=canary_tuple,
                            holdout=holdout_tuple,
                        )
                    )
                ),
            }
            for name, value in patches.items():
                stack.enter_context(patch.object(predecessor, name, value))
            stack.enter_context(
                patch.object(
                    compatibility,
                    "build_tracked_seed_inventory",
                    build_replication_seed_inventory,
                )
            )
            stack.enter_context(
                patch.object(
                    compatibility,
                    "verify_seed_inventory",
                    verify_replication_seed_inventory,
                )
            )
            yield


def load_preimplementation(
    path: Path | str = _REPO_ROOT / PREIMPLEMENTATION_PATH,
) -> dict[str, Any]:
    planned = tuple(range(SEARCH_START, SEARCH_START + TOTAL_COHORT_COUNT))
    with _contract_context(planned[:CANARY_COUNT], planned[CANARY_COUNT:]):
        return predecessor.load_preimplementation(path)


def build_registration(
    *,
    identity: Mapping[str, Any],
    canary: Sequence[int],
    holdout: Sequence[int],
) -> dict[str, Any]:
    with _contract_context(canary, holdout):
        return predecessor.build_registration(identity=identity)


def validate_registration(value: object) -> dict[str, Any]:
    canary, holdout = _cohort_values(value)
    with _contract_context(canary, holdout):
        return predecessor.validate_registration(copy.deepcopy(value))


def load_registration(
    path: Path | str = _REPO_ROOT / DEFAULT_REGISTRATION_PATH,
) -> dict[str, Any]:
    value = predecessor._load_json(path, "replication registration")
    return validate_registration(value)


def validate_execution_authorization(
    value: object,
    *,
    registration: Mapping[str, Any],
    registration_sha256: str,
    preregistration_commit: str,
) -> dict[str, Any]:
    canary, holdout = _cohort_values(registration)
    with _contract_context(canary, holdout):
        return predecessor.validate_execution_authorization(
            value,
            registration=registration,
            registration_sha256=registration_sha256,
            preregistration_commit=preregistration_commit,
        )


def classify_canary(rows: Sequence[Mapping[str, Any]], seeds: Sequence[int]):
    placeholder = tuple(range(SEARCH_START + CANARY_COUNT, SEARCH_START + TOTAL_COHORT_COUNT))
    with _contract_context(seeds, placeholder):
        return _replication_classify_canary(rows)


def classify_holdout(rows: Sequence[Mapping[str, Any]], seeds: Sequence[int]):
    placeholder = tuple(range(SEARCH_START, SEARCH_START + CANARY_COUNT))
    with _contract_context(placeholder, seeds):
        return _replication_classify_holdout(rows)


def run_study(**kwargs):
    canary, holdout = _cohort_values(kwargs["registration"])
    with _contract_context(canary, holdout):
        return _replication_run_study(**kwargs)


def consume_and_run(**kwargs):
    canary, holdout = _cohort_values(kwargs["registration"])
    with _contract_context(canary, holdout):
        return predecessor.consume_and_run(**kwargs)


def verify_artifact_directory(**kwargs):
    canary, holdout = _cohort_values(kwargs["registration"])
    with _contract_context(canary, holdout):
        return predecessor.verify_artifact_directory(**kwargs)


def validate_registration_evidence(
    registration: Mapping[str, Any],
    repo_root: Path | str,
    *,
    require_output_absent: bool = True,
):
    canary, holdout = _cohort_values(registration)
    with _contract_context(canary, holdout):
        return _replication_validate_registration_evidence(
            registration,
            repo_root,
            require_output_absent=require_output_absent,
        )


def prepare_registration(repo_root: Path | str = _REPO_ROOT) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    implementation_commit = predecessor._assert_clean_pushed_head(root)
    try:
        inventory = build_replication_seed_inventory(root)
    except compatibility.CompatibilityBlocked as exc:
        raise ReplicationBlocked(exc.reason, exc.detail) from exc
    if inventory["repository_commit"] != implementation_commit:
        raise ReplicationBlocked("seed_inventory_commit_mismatch")
    canary, holdout = select_replication_cohorts(inventory)
    with _contract_context(canary, holdout):
        return _ORIGINAL_PREPARE_REGISTRATION(root)


def preflight_registered(repo_root: Path | str = _REPO_ROOT) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    registration_path = root / DEFAULT_REGISTRATION_PATH
    registration = load_registration(registration_path)
    canary, holdout = _cohort_values(registration)
    with _contract_context(canary, holdout):
        validate_registration_evidence(registration, root)
        registration_binding = {
            "path": DEFAULT_REGISTRATION_PATH,
            "sha256": sha256_file(registration_path),
            "size_bytes": registration_path.stat().st_size,
        }
        predecessor.validate_preflight(
            predecessor._load_json(
                root / DEFAULT_PREFLIGHT_PATH, "replication preflight"
            ),
            implementation_commit=registration["identity"]["implementation"][
                "commit"
            ],
            registration_binding=registration_binding,
            seed_inventory_binding=registration["identity"]["seed_inventory"],
        )
    return {
        "cohort_count": TOTAL_COHORT_COUNT,
        "native_module_imported": False,
        "output_directory": DEFAULT_OUTPUT_DIRECTORY,
        "registration_sha256": registration_binding["sha256"],
        "verified_without_seed_access": True,
    }


def execute_registered(repo_root: Path | str = _REPO_ROOT) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    registration = load_registration(root / DEFAULT_REGISTRATION_PATH)
    canary, holdout = _cohort_values(registration)
    with _contract_context(canary, holdout):
        return _ORIGINAL_EXECUTE_REGISTERED(root)


def verify_registered(repo_root: Path | str = _REPO_ROOT) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    registration = load_registration(root / DEFAULT_REGISTRATION_PATH)
    canary, holdout = _cohort_values(registration)
    with _contract_context(canary, holdout):
        return _ORIGINAL_VERIFY_REGISTERED(root)


run_episode = predecessor.run_episode
run_policy_pair = predecessor.run_policy_pair
_episode_row = predecessor._episode_row
_declared_support_row = predecessor._declared_support_row
_validate_row = predecessor._validate_row
_stage_metrics = predecessor._stage_metrics


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare, preflight, execute, or verify the final Current baseline replication."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("prepare")
    commands.add_parser("preflight")
    commands.add_parser("execute")
    commands.add_parser("verify")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare_registration()
        elif args.command == "preflight":
            result = preflight_registered()
        elif args.command == "execute":
            result = execute_registered()
        else:
            result = verify_registered()
    except ReplicationBlocked as exc:
        print(
            canonical_json_bytes(
                {"detail": exc.detail, "reason": exc.reason, "status": "blocked"}
            ).decode("utf-8"),
            end="",
        )
        return 1
    print(canonical_json_bytes(result).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
