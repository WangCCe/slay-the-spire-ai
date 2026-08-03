"""Run one preregistered native gate for reachable event semantics."""

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
from pathlib import Path, PurePosixPath
from typing import Any

import analysis_scripts.noncombat_total_event_native_compatibility as predecessor
from analysis_scripts.noncombat_current_policy_simulator_bridge import (
    BridgeBlocked,
    CurrentPolicyBridgeSession,
    MetadataCatalog,
    POLICY_ID,
    hash_bound_files,
)
from analysis_scripts.noncombat_event_option_semantics import (
    event_option_semantics_identity,
    reachable_event_option_semantics_identity,
)
from analysis_scripts.noncombat_simulator_adapter import (
    ADAPTER_API_VERSION,
    NativeSimulatorEnvironment,
    SimulatorAdapterError,
    TARGET_CATEGORIES,
    canonical_json_bytes,
    load_native_module,
    sha256_bytes,
    sha256_file,
    validate_candidates,
    validate_provenance,
)


INPUT_SCHEMA_VERSION = (
    "noncombat-reachable-event-native-compatibility-input-v1"
)
SEED_INVENTORY_SCHEMA_VERSION = (
    "noncombat-reachable-event-native-compatibility-seed-inventory-v1"
)
SEED_LEDGER_SCHEMA_VERSION = (
    "noncombat-reachable-event-native-compatibility-seed-ledger-v1"
)
EXECUTION_SCHEMA_VERSION = (
    "noncombat-reachable-event-native-compatibility-execution-v1"
)
JOURNAL_SCHEMA_VERSION = (
    "noncombat-reachable-event-native-compatibility-journal-v1"
)
CONFIGURATION_SCHEMA_VERSION = (
    "noncombat-reachable-event-native-compatibility-configuration-v1"
)
METRICS_SCHEMA_VERSION = (
    "noncombat-reachable-event-native-compatibility-metrics-v1"
)
TRAJECTORY_SCHEMA_VERSION = (
    "noncombat-reachable-event-native-compatibility-trajectories-v1"
)
MANIFEST_SCHEMA_VERSION = (
    "noncombat-reachable-event-native-compatibility-manifest-v1"
)

COHORT_SIZE = 8
COHORT_SEARCH_START = 7100
REPLAY_COUNT = 2
MAX_DECISIONS_PER_REPLAY = 500
MAX_WALL_SECONDS = 120.0

DEFAULT_REGISTRATION_PATH = (
    "reports/noncombat_reachable_event_native_compatibility_20260803_input.json"
)
DEFAULT_SEED_INVENTORY_PATH = (
    "reports/noncombat_reachable_event_native_compatibility_20260803_seed_inventory.json"
)
DEFAULT_SEED_LEDGER_PATH = (
    "reports/noncombat_reachable_event_native_compatibility_20260803_seed_ledger.json"
)
DEFAULT_OUTPUT_DIRECTORY = (
    "reports/noncombat_reachable_event_native_compatibility_20260803"
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
    "formal_rl_readiness_authorized": False,
    "fresh_evidence_authorized": False,
    "gameplay_authorized": False,
    "model_authorized": False,
    "ope_authorized": False,
    "policy_loading_authorized": False,
    "promotion_authorized": False,
    "qualification_authorized": False,
    "reward_authorized": False,
    "target_supported_outcome_authorized": False,
    "training_authorized": False,
}

CURRENT_POLICY = {
    "ascension": 0,
    "character": "IRONCLAD",
    "elite_mode": "conservative",
    "gameplay_io_enabled": False,
    "policy_id": POLICY_ID,
    "screen_entrypoint": "handle_screen",
    "tracker_enabled": False,
    "use_optimized_card_selection": True,
    "use_optimized_combat": True,
}

ADAPTER_SOURCE_FILES = predecessor.ADAPTER_SOURCE_FILES
IMPLEMENTATION_SOURCE_FILES = (
    "analysis_scripts/noncombat_reachable_event_native_compatibility.py",
    "analysis_scripts/noncombat_current_policy_simulator_bridge.py",
    "analysis_scripts/noncombat_event_option_semantics.py",
    "analysis_scripts/noncombat_reachable_event_surface_audit.py",
    "analysis_scripts/noncombat_simulator_adapter.py",
    "tests/test_noncombat_reachable_event_native_compatibility.py",
    "tests/test_noncombat_reachable_event_option_semantics.py",
    "spirecomm/ai/agent.py",
    "spirecomm/ai/decision/base.py",
    "spirecomm/ai/heuristics/card.py",
    "spirecomm/ai/heuristics/deck.py",
    "spirecomm/ai/heuristics/ironclad_deck.py",
    "spirecomm/ai/heuristics/ironclad_evaluator.py",
    "spirecomm/ai/heuristics/map_routing.py",
    "spirecomm/ai/priorities.py",
    "spirecomm/data/loader.py",
    "spirecomm/spire/card.py",
    "spirecomm/spire/game.py",
    "spirecomm/spire/map.py",
    "spirecomm/spire/potion.py",
    "spirecomm/spire/relic.py",
    "spirecomm/spire/screen.py",
)

PREDECESSOR_PATHS = {
    "compatibility_closeout": (
        "reports/noncombat_total_event_native_compatibility_20260803_closeout.md"
    ),
    "compatibility_journal": (
        "reports/noncombat_total_event_native_compatibility_20260803/"
        "execution_journal.json"
    ),
    "compatibility_manifest": (
        "reports/noncombat_total_event_native_compatibility_20260803/"
        "artifact_manifest.json"
    ),
    "compatibility_registration": (
        "reports/noncombat_total_event_native_compatibility_20260803_input.json"
    ),
    "compatibility_seed_ledger": (
        "reports/noncombat_total_event_native_compatibility_20260803_seed_ledger.json"
    ),
    "reachable_closeout": (
        "reports/noncombat_reachable_event_surface_20260803_closeout.md"
    ),
    "reachable_manifest": (
        "reports/noncombat_reachable_event_surface_audit_20260803/"
        "artifact_manifest.json"
    ),
}

_MANAGED_SEED_SOURCE_EXCLUSIONS = {
    DEFAULT_REGISTRATION_PATH,
    DEFAULT_SEED_INVENTORY_PATH,
    DEFAULT_SEED_LEDGER_PATH,
    (
        "reports/noncombat_current_baseline_evidence_study_20260803_"
        "preimplementation.json"
    ),
    (
        "reports/noncombat_current_baseline_evidence_study_20260803_"
        "seed_inventory.json"
    ),
    "reports/noncombat_current_baseline_evidence_study_20260803_input.json",
    "reports/noncombat_current_baseline_evidence_study_20260803_preflight.json",
    (
        "reports/noncombat_current_baseline_evidence_study_20260803_"
        "execution_authorization.json"
    ),
}


class CompatibilityBlocked(RuntimeError):
    """Raised when the immutable compatibility boundary cannot be proved."""

    def __init__(self, reason: str, detail: object | None = None):
        self.reason = reason
        self.detail = detail
        message = reason if detail is None else f"{reason}: {detail}"
        super().__init__(message)


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise CompatibilityBlocked("invalid_mapping", label)
    return dict(value)


def _sequence(value: object, label: str) -> list[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise CompatibilityBlocked("invalid_sequence", label)
    return list(value)


def _require_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise CompatibilityBlocked(
            "keys_mismatch",
            {"actual": sorted(value), "expected": sorted(expected), "label": label},
        )


def _is_hex(value: object, length: int) -> bool:
    return (
        isinstance(value, str)
        and len(value) == length
        and all(character in "0123456789abcdef" for character in value.lower())
    )


def _repository_relative_path(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise CompatibilityBlocked("path_not_repository_relative", label)
    path = PurePosixPath(value.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts:
        raise CompatibilityBlocked("path_not_repository_relative", label)
    return path.as_posix()


def _validate_binding(
    value: object, label: str, *, repository_relative: bool
) -> dict[str, Any]:
    binding = _mapping(value, label)
    _require_keys(binding, {"path", "sha256", "size_bytes"}, label)
    if repository_relative:
        binding["path"] = _repository_relative_path(binding["path"], label)
    elif not isinstance(binding["path"], str) or not Path(binding["path"]).is_absolute():
        raise CompatibilityBlocked("binding_path_not_absolute", label)
    if not _is_hex(binding["sha256"], 64):
        raise CompatibilityBlocked("binding_sha256_invalid", label)
    size = binding["size_bytes"]
    if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
        raise CompatibilityBlocked("binding_size_invalid", label)
    return binding


def _file_binding(path: Path, display_path: str) -> dict[str, Any]:
    if not path.is_file():
        raise CompatibilityBlocked("bound_file_missing", display_path)
    return {
        "path": display_path,
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def _role_for_seed_path(json_path: str) -> str:
    normalized = json_path.lower()
    roles = (
        (("final_test", "final-test", "reserved"), "reserved"),
        (("train", "fit_seed"), "training"),
        (("validation", "holdout"), "validation"),
        (("compatibility",), "compatibility"),
        (("qualification",), "qualification"),
        (("smoke",), "smoke"),
        (("consumed",), "consumed"),
        (("selected",), "selected"),
    )
    for needles, role in roles:
        if any(needle in normalized for needle in needles):
            return role
    return "ambiguous"


def _seed_scalar(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _seed_rows(value: object, source_path: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def visit(node: object, path: str, seed_context: bool) -> None:
        if isinstance(node, Mapping):
            for key in sorted(node):
                if not isinstance(key, str):
                    continue
                child_path = f"{path}.{key}" if path else key
                visit(
                    node[key],
                    child_path,
                    seed_context or "seed" in key.lower(),
                )
            return
        if isinstance(node, list):
            for index, child in enumerate(node):
                visit(child, f"{path}[{index}]", seed_context)
            return
        seed = _seed_scalar(node) if seed_context else None
        if seed is not None:
            rows.append(
                {
                    "json_path": path,
                    "role": _role_for_seed_path(path),
                    "seed": seed,
                    "source_path": source_path,
                }
            )

    visit(value, "", False)
    return rows


def _parse_seed_source(payload: bytes, path: str) -> object:
    def reject_duplicates(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise CompatibilityBlocked(
                    "seed_source_duplicate_key", {"key": key, "path": path}
                )
            result[key] = value
        return result

    try:
        return json.loads(
            payload.decode("utf-8"), object_pairs_hook=reject_duplicates
        )
    except CompatibilityBlocked:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CompatibilityBlocked(
            "seed_source_json_invalid", {"error": str(exc), "path": path}
        ) from exc


def build_seed_inventory_from_documents(
    documents: Mapping[str, bytes], *, repository_commit: str
) -> dict[str, Any]:
    if not _is_hex(repository_commit, 40):
        raise CompatibilityBlocked("seed_inventory_commit_invalid")
    normalized_documents: dict[str, bytes] = {}
    rows: list[dict[str, Any]] = []
    for raw_path, raw_payload in documents.items():
        path = _repository_relative_path(raw_path, "seed source")
        if path in normalized_documents:
            raise CompatibilityBlocked("seed_source_path_duplicate", path)
        if not isinstance(raw_payload, bytes) or not raw_payload:
            raise CompatibilityBlocked("seed_source_bytes_invalid", path)

        value = _parse_seed_source(raw_payload, path)
        normalized_documents[path] = raw_payload
        rows.extend(_seed_rows(value, path))

    bindings = [
        {
            "path": path,
            "sha256": sha256_bytes(payload),
            "size_bytes": len(payload),
        }
        for path, payload in sorted(normalized_documents.items())
    ]
    rows.sort(key=lambda row: (row["seed"], row["source_path"], row["json_path"]))
    excluded = sorted({row["seed"] for row in rows})
    inventory = {
        "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
        "excluded_seed_count": len(excluded),
        "excluded_seeds": excluded,
        "repository_commit": repository_commit,
        "row_count": len(rows),
        "rows": rows,
        "schema_version": SEED_INVENTORY_SCHEMA_VERSION,
        "source_bindings": bindings,
        "source_count": len(bindings),
    }
    return validate_seed_inventory(inventory)


def validate_seed_inventory(value: object) -> dict[str, Any]:
    inventory = _mapping(value, "seed inventory")
    _require_keys(
        inventory,
        {
            "authority",
            "excluded_seed_count",
            "excluded_seeds",
            "repository_commit",
            "row_count",
            "rows",
            "schema_version",
            "source_bindings",
            "source_count",
        },
        "seed inventory",
    )
    if inventory["schema_version"] != SEED_INVENTORY_SCHEMA_VERSION:
        raise CompatibilityBlocked("seed_inventory_schema_mismatch")
    if inventory["authority"] != ALL_FALSE_AUTHORITY:
        raise CompatibilityBlocked("authority_must_be_all_false")
    if not _is_hex(inventory["repository_commit"], 40):
        raise CompatibilityBlocked("seed_inventory_commit_invalid")
    bindings = [
        _validate_binding(row, "seed source binding", repository_relative=True)
        for row in _sequence(inventory["source_bindings"], "seed source bindings")
    ]
    if bindings != sorted(bindings, key=lambda row: row["path"]) or len(
        {row["path"] for row in bindings}
    ) != len(bindings):
        raise CompatibilityBlocked("seed_source_bindings_invalid")
    rows = []
    for index, raw_row in enumerate(_sequence(inventory["rows"], "seed rows")):
        row = _mapping(raw_row, f"seed row[{index}]")
        _require_keys(row, {"json_path", "role", "seed", "source_path"}, f"seed row[{index}]")
        if (
            not isinstance(row["json_path"], str)
            or not row["json_path"]
            or row["role"]
            not in {
                "ambiguous",
                "compatibility",
                "consumed",
                "qualification",
                "reserved",
                "selected",
                "smoke",
                "training",
                "validation",
            }
            or isinstance(row["seed"], bool)
            or not isinstance(row["seed"], int)
            or row["seed"] < 0
        ):
            raise CompatibilityBlocked("seed_inventory_row_invalid", index)
        row["source_path"] = _repository_relative_path(
            row["source_path"], f"seed row[{index}].source_path"
        )
        rows.append(row)
    expected_rows = sorted(
        rows, key=lambda row: (row["seed"], row["source_path"], row["json_path"])
    )
    excluded = sorted({row["seed"] for row in rows})
    if (
        rows != expected_rows
        or inventory["excluded_seeds"] != excluded
        or inventory["excluded_seed_count"] != len(excluded)
        or inventory["row_count"] != len(rows)
        or inventory["source_count"] != len(bindings)
    ):
        raise CompatibilityBlocked("seed_inventory_counts_mismatch")
    inventory["rows"] = rows
    inventory["source_bindings"] = bindings
    return inventory


def _git_bytes(repo_root: Path, *args: str) -> bytes:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        raise CompatibilityBlocked(
            "git_command_failed",
            {"args": list(args), "stderr": completed.stderr.decode(errors="replace")},
        )
    return completed.stdout


def _git_text(repo_root: Path, *args: str) -> str:
    return _git_bytes(repo_root, *args).decode("utf-8").strip()


def discover_seed_documents(repo_root: Path | str) -> dict[str, bytes]:
    root = Path(repo_root).resolve()
    tracked = _git_text(root, "ls-files", "--", "reports").splitlines()
    documents: dict[str, bytes] = {}
    for raw_path in tracked:
        path = raw_path.replace("\\", "/")
        if (
            not path.endswith(".json")
            or path in _MANAGED_SEED_SOURCE_EXCLUSIONS
            or path.startswith(f"{DEFAULT_OUTPUT_DIRECTORY}/")
        ):
            continue
        payload = (root / path).read_bytes()
        parsed = _parse_seed_source(payload, path)
        if _seed_rows(parsed, path):
            documents[path] = payload
    return documents


def build_tracked_seed_inventory(repo_root: Path | str) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    return build_seed_inventory_from_documents(
        discover_seed_documents(root),
        repository_commit=_git_text(root, "rev-parse", "HEAD"),
    )


def verify_seed_inventory(
    inventory: Mapping[str, Any], repo_root: Path | str
) -> dict[str, Any]:
    normalized = validate_seed_inventory(copy.deepcopy(inventory))
    recomputed = build_seed_inventory_from_documents(
        discover_seed_documents(repo_root),
        repository_commit=normalized["repository_commit"],
    )
    if canonical_json_bytes(normalized) != canonical_json_bytes(recomputed):
        raise CompatibilityBlocked("seed_inventory_recomputation_mismatch")
    return recomputed


def select_untouched_cohort(
    inventory: Mapping[str, Any], *, search_start: int = COHORT_SEARCH_START
) -> list[int]:
    normalized = validate_seed_inventory(copy.deepcopy(inventory))
    if isinstance(search_start, bool) or not isinstance(search_start, int) or search_start < 0:
        raise CompatibilityBlocked("seed_search_start_invalid")
    excluded = set(normalized["excluded_seeds"])
    selected = []
    candidate = search_start
    while len(selected) < COHORT_SIZE:
        if candidate not in excluded:
            selected.append(candidate)
        candidate += 1
    return selected


def build_seed_ledger(
    *, inventory: Mapping[str, Any], seeds: Sequence[int]
) -> dict[str, Any]:
    normalized_inventory = validate_seed_inventory(copy.deepcopy(inventory))
    ledger = {
        "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
        "cohort_seeds": list(seeds),
        "limits": {
            "max_decisions_per_replay": MAX_DECISIONS_PER_REPLAY,
            "max_wall_seconds": MAX_WALL_SECONDS,
            "replay_count": REPLAY_COUNT,
        },
        "seed_inventory_sha256": sha256_bytes(
            canonical_json_bytes(normalized_inventory)
        ),
        "selection": {
            "cohort_size": COHORT_SIZE,
            "search_start": COHORT_SEARCH_START,
            "strategy": "first_sorted_unexcluded_seeds_v1",
        },
        "schema_version": SEED_LEDGER_SCHEMA_VERSION,
    }
    return validate_seed_ledger(ledger, inventory=normalized_inventory)


def validate_seed_ledger(
    value: object, *, inventory: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    ledger = _mapping(value, "seed ledger")
    _require_keys(
        ledger,
        {"authority", "cohort_seeds", "limits", "seed_inventory_sha256", "selection", "schema_version"},
        "seed ledger",
    )
    if ledger["schema_version"] != SEED_LEDGER_SCHEMA_VERSION:
        raise CompatibilityBlocked("seed_ledger_schema_mismatch")
    if ledger["authority"] != ALL_FALSE_AUTHORITY:
        raise CompatibilityBlocked("authority_must_be_all_false")
    seeds = _sequence(ledger["cohort_seeds"], "cohort seeds")
    if (
        len(seeds) != COHORT_SIZE
        or seeds != sorted(set(seeds))
        or any(isinstance(seed, bool) or not isinstance(seed, int) or seed < 0 for seed in seeds)
    ):
        raise CompatibilityBlocked("seed_ledger_cohort_invalid")
    expected_limits = {
        "max_decisions_per_replay": MAX_DECISIONS_PER_REPLAY,
        "max_wall_seconds": MAX_WALL_SECONDS,
        "replay_count": REPLAY_COUNT,
    }
    expected_selection = {
        "cohort_size": COHORT_SIZE,
        "search_start": COHORT_SEARCH_START,
        "strategy": "first_sorted_unexcluded_seeds_v1",
    }
    if ledger["limits"] != expected_limits or ledger["selection"] != expected_selection:
        raise CompatibilityBlocked("seed_ledger_limits_mismatch")
    if not _is_hex(ledger["seed_inventory_sha256"], 64):
        raise CompatibilityBlocked("seed_inventory_hash_invalid")
    if inventory is not None:
        normalized = validate_seed_inventory(copy.deepcopy(inventory))
        if ledger["seed_inventory_sha256"] != sha256_bytes(
            canonical_json_bytes(normalized)
        ):
            raise CompatibilityBlocked("seed_ledger_inventory_mismatch")
        overlap = sorted(set(seeds).intersection(normalized["excluded_seeds"]))
        if overlap:
            raise CompatibilityBlocked("seed_ledger_candidate_overlap", overlap)
        expected_seeds = select_untouched_cohort(normalized)
        if seeds != expected_seeds:
            raise CompatibilityBlocked(
                "seed_ledger_selection_mismatch",
                {"actual": seeds, "expected": expected_seeds},
            )
    ledger["cohort_seeds"] = seeds
    return ledger


def build_registration(
    *, identity: Mapping[str, Any], seeds: Sequence[int]
) -> dict[str, Any]:
    registration = {
        "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
        "cohort": {"replay_count": REPLAY_COUNT, "seeds": list(seeds)},
        "current_policy": copy.deepcopy(CURRENT_POLICY),
        "identity": copy.deepcopy(dict(identity)),
        "limits": {
            "max_decisions_per_replay": MAX_DECISIONS_PER_REPLAY,
            "max_wall_seconds": MAX_WALL_SECONDS,
        },
        "output": {
            "artifact_names": list(CANONICAL_ARTIFACT_NAMES),
            "directory": DEFAULT_OUTPUT_DIRECTORY,
        },
        "schema_version": INPUT_SCHEMA_VERSION,
    }
    return validate_registration(registration)


def _validate_provenance(value: object) -> dict[str, Any]:
    try:
        provenance = validate_provenance(copy.deepcopy(value))
    except (TypeError, ValueError) as exc:
        raise CompatibilityBlocked("native_provenance_invalid", str(exc)) from exc
    expected_keys = {
        "adapter_commit",
        "adapter_source_sha256",
        "build",
        "module_sha256",
        "module_size_bytes",
        "simulator_commit",
        "simulator_dirty",
        "simulator_source_file_count",
        "simulator_source_sha256",
        "submodules",
    }
    _require_keys(provenance, expected_keys, "adapter provenance")
    build = _mapping(provenance["build"], "adapter build")
    if (
        build.get("adapter_api_version") != ADAPTER_API_VERSION
        or build.get("baseline_policy_id")
        != "sts_lightspeed_simple_agent_no_potions_v1"
        or build.get("native_target_policy_id")
        != "sts_lightspeed_simple_agent_target_v1"
        or build.get("cpp_standard") != 201703
        or not isinstance(build.get("compiler"), str)
        or not build["compiler"]
        or not isinstance(build.get("python"), str)
        or not build["python"]
    ):
        raise CompatibilityBlocked("native_build_identity_mismatch", build)
    for field, length in (
        ("adapter_commit", 40),
        ("adapter_source_sha256", 64),
        ("module_sha256", 64),
        ("simulator_commit", 40),
        ("simulator_source_sha256", 64),
    ):
        if not _is_hex(provenance[field], length):
            raise CompatibilityBlocked("native_provenance_hash_invalid", field)
    if (
        isinstance(provenance["module_size_bytes"], bool)
        or not isinstance(provenance["module_size_bytes"], int)
        or provenance["module_size_bytes"] <= 0
        or isinstance(provenance["simulator_source_file_count"], bool)
        or not isinstance(provenance["simulator_source_file_count"], int)
        or provenance["simulator_source_file_count"] <= 0
        or not isinstance(provenance["simulator_dirty"], bool)
    ):
        raise CompatibilityBlocked("native_provenance_physical_identity_invalid")
    submodules = _mapping(provenance["submodules"], "native submodules")
    if set(submodules) != {"json", "pybind11"} or any(
        not _is_hex(commit, 40) for commit in submodules.values()
    ):
        raise CompatibilityBlocked("native_submodule_identity_invalid")
    return provenance


def validate_registration(value: object) -> dict[str, Any]:
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
    if registration["schema_version"] != INPUT_SCHEMA_VERSION:
        raise CompatibilityBlocked("registration_schema_mismatch")
    if registration["authority"] != ALL_FALSE_AUTHORITY:
        raise CompatibilityBlocked("authority_must_be_all_false")
    if registration["current_policy"] != CURRENT_POLICY:
        raise CompatibilityBlocked("current_policy_configuration_mismatch")
    cohort = _mapping(registration["cohort"], "cohort")
    _require_keys(cohort, {"replay_count", "seeds"}, "cohort")
    seeds = _sequence(cohort["seeds"], "cohort.seeds")
    if (
        cohort["replay_count"] != REPLAY_COUNT
        or len(seeds) != COHORT_SIZE
        or seeds != sorted(set(seeds))
        or any(isinstance(seed, bool) or not isinstance(seed, int) or seed < 0 for seed in seeds)
    ):
        raise CompatibilityBlocked("registration_cohort_mismatch")
    expected_limits = {
        "max_decisions_per_replay": MAX_DECISIONS_PER_REPLAY,
        "max_wall_seconds": MAX_WALL_SECONDS,
    }
    if registration["limits"] != expected_limits:
        raise CompatibilityBlocked("registration_limits_mismatch")
    output = _mapping(registration["output"], "output")
    if output != {
        "artifact_names": list(CANONICAL_ARTIFACT_NAMES),
        "directory": DEFAULT_OUTPUT_DIRECTORY,
    }:
        raise CompatibilityBlocked("registration_output_mismatch")

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
            "predecessors",
            "runtime",
            "seed_inventory",
            "seed_ledger",
            "simulator_path",
        },
        "identity",
    )
    identity["adapter_provenance"] = _validate_provenance(
        identity["adapter_provenance"]
    )
    if identity["adapter_source_files"] != list(ADAPTER_SOURCE_FILES):
        raise CompatibilityBlocked("adapter_source_files_mismatch")
    expected_contract = reachable_event_option_semantics_identity()
    if identity["contract"] != expected_contract:
        raise CompatibilityBlocked("event_contract_identity_mismatch")
    if (
        identity["adapter_provenance"]["simulator_commit"]
        != expected_contract["simulator_commit"]
        or identity["adapter_provenance"]["simulator_source_sha256"]
        != expected_contract["simulator_source_sha256"]
    ):
        raise CompatibilityBlocked("native_simulator_contract_mismatch")
    identity["contract_file"] = _validate_binding(
        identity["contract_file"],
        "identity.contract_file",
        repository_relative=True,
    )
    contract_binding = expected_contract["observation_contract"]
    if (
        identity["contract_file"]["path"] != contract_binding["path"]
        or identity["contract_file"]["sha256"] != contract_binding["sha256"]
    ):
        raise CompatibilityBlocked("event_contract_binding_mismatch")

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
        raise CompatibilityBlocked("implementation_identity_mismatch")
    identity["implementation"] = implementation
    identity["metadata"] = _validate_binding(
        identity["metadata"], "identity.metadata", repository_relative=False
    )
    module_path = identity["module_path"]
    simulator_path = identity["simulator_path"]
    if not isinstance(module_path, str) or not Path(module_path).is_absolute():
        raise CompatibilityBlocked("module_path_not_absolute")
    if not isinstance(simulator_path, str) or not Path(simulator_path).is_absolute():
        raise CompatibilityBlocked("simulator_path_not_absolute")
    predecessors = _mapping(identity["predecessors"], "predecessors")
    if set(predecessors) != set(PREDECESSOR_PATHS):
        raise CompatibilityBlocked("predecessor_set_mismatch")
    identity["predecessors"] = {
        name: _validate_binding(
            predecessors[name], f"predecessors.{name}", repository_relative=True
        )
        for name in sorted(predecessors)
    }
    runtime = _mapping(identity["runtime"], "runtime")
    _require_keys(runtime, {"executable", "python"}, "runtime")
    if (
        not isinstance(runtime["executable"], str)
        or not Path(runtime["executable"]).is_absolute()
        or not isinstance(runtime["python"], str)
        or not runtime["python"]
    ):
        raise CompatibilityBlocked("runtime_identity_invalid")
    identity["runtime"] = runtime
    identity["seed_inventory"] = _validate_binding(
        identity["seed_inventory"],
        "identity.seed_inventory",
        repository_relative=True,
    )
    identity["seed_ledger"] = _validate_binding(
        identity["seed_ledger"],
        "identity.seed_ledger",
        repository_relative=True,
    )
    if identity["seed_inventory"]["path"] != DEFAULT_SEED_INVENTORY_PATH:
        raise CompatibilityBlocked("seed_inventory_path_mismatch")
    if identity["seed_ledger"]["path"] != DEFAULT_SEED_LEDGER_PATH:
        raise CompatibilityBlocked("seed_ledger_path_mismatch")
    registration["cohort"] = {"replay_count": REPLAY_COUNT, "seeds": seeds}
    registration["identity"] = identity
    return registration


def _reject_duplicate_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CompatibilityBlocked("duplicate_json_key", key)
        result[key] = value
    return result


def _load_json(path: Path | str, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            Path(path).read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
        )
    except CompatibilityBlocked:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CompatibilityBlocked(
            "cannot_load_json", {"error": str(exc), "label": label}
        ) from exc
    return _mapping(value, label)


def load_registration(path: Path | str) -> dict[str, Any]:
    return validate_registration(_load_json(path, "registration"))


def _verify_binding(
    *, repo_root: Path, binding: Mapping[str, Any], repository_relative: bool
) -> Path:
    path = (
        (repo_root / str(binding["path"])).resolve()
        if repository_relative
        else Path(str(binding["path"])).resolve()
    )
    if (
        not path.is_file()
        or path.stat().st_size != binding["size_bytes"]
        or sha256_file(path) != binding["sha256"]
    ):
        raise CompatibilityBlocked("bound_file_identity_mismatch", binding["path"])
    return path


def verify_predecessor_bindings(
    registration: Mapping[str, Any], repo_root: Path | str
) -> dict[str, Path]:
    normalized = validate_registration(copy.deepcopy(registration))
    root = Path(repo_root).resolve()
    paths = {}
    for name, binding in normalized["identity"]["predecessors"].items():
        try:
            paths[name] = _verify_binding(
                repo_root=root, binding=binding, repository_relative=True
            )
        except CompatibilityBlocked as exc:
            raise CompatibilityBlocked(
                "predecessor_binding_mismatch", {"name": name, "reason": exc.reason}
            ) from exc
    return paths


def validate_registration_evidence(
    registration: Mapping[str, Any], repo_root: Path | str
) -> tuple[dict[str, Any], dict[str, Any], MetadataCatalog]:
    normalized = validate_registration(copy.deepcopy(registration))
    root = Path(repo_root).resolve()
    identity = normalized["identity"]
    verify_predecessor_bindings(normalized, root)
    contract_path = _verify_binding(
        repo_root=root,
        binding=identity["contract_file"],
        repository_relative=True,
    )
    if sha256_file(contract_path) != identity["contract"]["observation_contract"]["sha256"]:
        raise CompatibilityBlocked("event_contract_binding_mismatch")
    inventory_path = _verify_binding(
        repo_root=root,
        binding=identity["seed_inventory"],
        repository_relative=True,
    )
    inventory = validate_seed_inventory(_load_json(inventory_path, "seed inventory"))
    verify_seed_inventory(inventory, root)
    ledger_path = _verify_binding(
        repo_root=root,
        binding=identity["seed_ledger"],
        repository_relative=True,
    )
    ledger = validate_seed_ledger(
        _load_json(ledger_path, "seed ledger"), inventory=inventory
    )
    if ledger["cohort_seeds"] != normalized["cohort"]["seeds"]:
        raise CompatibilityBlocked("registration_seed_ledger_mismatch")
    implementation = identity["implementation"]
    if hash_bound_files(root, implementation["source_files"]) != implementation[
        "source_sha256"
    ]:
        raise CompatibilityBlocked("implementation_source_hash_mismatch")
    try:
        predecessor._verify_sources_at_commit(
            root, implementation["commit"], implementation["source_files"]
        )
    except predecessor.CompatibilityBlocked as exc:
        raise CompatibilityBlocked(exc.reason, exc.detail) from exc
    if identity["runtime"] != {
        "executable": str(Path(sys.executable).resolve()),
        "python": sys.version.split()[0],
    }:
        raise CompatibilityBlocked("runtime_identity_mismatch")
    metadata_path = _verify_binding(
        repo_root=root, binding=identity["metadata"], repository_relative=False
    )
    module_path = Path(identity["module_path"])
    provenance = identity["adapter_provenance"]
    if (
        not module_path.is_file()
        or module_path.stat().st_size != provenance["module_size_bytes"]
        or sha256_file(module_path) != provenance["module_sha256"]
    ):
        raise CompatibilityBlocked("native_module_binding_mismatch")
    return inventory, ledger, MetadataCatalog(metadata_path)


def _assert_clean_pushed_head(repo_root: Path) -> str:
    if _git_text(repo_root, "status", "--porcelain", "--untracked-files=no"):
        raise CompatibilityBlocked("tracked_tree_dirty")
    head = _git_text(repo_root, "rev-parse", "HEAD")
    origin = _git_text(repo_root, "rev-parse", "origin/master")
    if head != origin:
        raise CompatibilityBlocked(
            "head_not_pushed", {"head": head, "origin_master": origin}
        )
    if not _is_hex(head, 40):
        raise CompatibilityBlocked("head_identity_invalid")
    return head


def assert_pushed_registration(
    *, registration_path: Path | str, repo_root: Path | str
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    path = Path(registration_path).resolve()
    try:
        relative = path.relative_to(root).as_posix()
    except ValueError as exc:
        raise CompatibilityBlocked("registration_path_outside_repository") from exc
    head = _assert_clean_pushed_head(root)
    registration_bytes = path.read_bytes()
    if _git_bytes(root, "show", f"{head}:{relative}") != registration_bytes:
        raise CompatibilityBlocked("pushed_registration_mismatch")
    registration = load_registration(path)
    for field, reason in (
        ("seed_inventory", "pushed_seed_inventory_mismatch"),
        ("seed_ledger", "pushed_seed_ledger_mismatch"),
    ):
        binding = registration["identity"][field]
        bound_path = root / binding["path"]
        bound_bytes = bound_path.read_bytes()
        if _git_bytes(root, "show", f"{head}:{binding['path']}") != bound_bytes:
            raise CompatibilityBlocked(reason)
    return {
        "preregistration_commit": head,
        "registration_sha256": sha256_bytes(registration_bytes),
    }


def collect_native_identity(**kwargs) -> dict[str, Any]:
    """Collect API/build identity without constructing an Environment."""

    try:
        identity = predecessor.collect_native_identity(**kwargs)
    except predecessor.CompatibilityBlocked as exc:
        raise CompatibilityBlocked(exc.reason, exc.detail) from exc
    return _validate_provenance(identity)


def _failed_result(
    *, registration: Mapping[str, Any], reason: str, detail: object | None, rows: list[dict[str, Any]]
) -> dict[str, Any]:
    try:
        canonical_json_bytes({"detail": detail})
        preserved_detail = copy.deepcopy(detail)
    except (TypeError, ValueError):
        preserved_detail = {"repr": repr(detail), "type": type(detail).__name__}
    counts = Counter()
    for row in rows:
        counts.update(row["category_counts"])
    return {
        "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
        "category_counts": {category: counts[category] for category in TARGET_CATEGORIES},
        "detail": preserved_detail,
        "reason": reason,
        "rows": rows,
        "schema_version": EXECUTION_SCHEMA_VERSION,
        "seeds": list(registration["cohort"]["seeds"]),
        "status": "failed",
        "verdict": "reachable_event_native_compatibility_failed",
    }


def _event_diagnostic(
    evaluation: Mapping[str, Any],
    candidate: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    expected_source = reachable_event_option_semantics_identity()["contract_id"]
    if evaluation.get("event_semantics_source") != expected_source:
        raise CompatibilityBlocked(
            "event_semantics_source_mismatch",
            evaluation.get("event_semantics_source"),
        )
    observation = _mapping(evaluation.get("event_observation"), "event observation")
    expected_keys = {
        "current_event_id",
        "current_position",
        "event_data",
        "selected_action_id",
        "semantics_source",
        "simulator_choice_index",
        "upstream_event_id",
    }
    _require_keys(observation, expected_keys, "event observation")
    raw = _mapping(candidate.get("raw"), "event candidate raw")
    state = _mapping(snapshot.get("state"), "event snapshot.state")
    context = _mapping(
        state.get("decision_context"), "event snapshot.state.decision_context"
    )
    current_position = observation["current_position"]
    simulator_index = observation["simulator_choice_index"]
    candidate_position = list(candidates).index(candidate)
    if (
        observation["semantics_source"] != expected_source
        or observation["selected_action_id"] != candidate.get("action_id")
        or isinstance(current_position, bool)
        or not isinstance(current_position, int)
        or current_position < 0
        or isinstance(simulator_index, bool)
        or not isinstance(simulator_index, int)
        or simulator_index < 0
        or current_position != candidate_position
        or raw.get("idx1") != simulator_index
        or observation["upstream_event_id"] != context.get("event_id")
        or observation["event_data"] != context.get("event_data")
        or not isinstance(observation["upstream_event_id"], str)
        or not observation["upstream_event_id"]
        or not isinstance(observation["current_event_id"], str)
        or not observation["current_event_id"]
    ):
        raise CompatibilityBlocked("event_observation_mapping_invalid", observation)
    return copy.deepcopy(observation)


def _run_replay(
    *,
    environment: Any,
    session: Any,
    seed: int,
    max_decisions: int,
    deadline: float,
    monotonic: Callable[[], float],
) -> dict[str, Any]:
    decisions = []
    category_counts = Counter()
    event_identities = []
    while True:
        if monotonic() > deadline:
            raise CompatibilityBlocked("execution_deadline_exceeded")
        try:
            snapshot = _mapping(environment.snapshot(), "native snapshot")
        except CompatibilityBlocked:
            raise
        except Exception as exc:
            raise CompatibilityBlocked(
                "native_snapshot_failed",
                {"message": str(exc), "type": type(exc).__name__},
            ) from exc
        if snapshot.get("terminal") is True:
            break
        if len(decisions) >= max_decisions:
            raise CompatibilityBlocked(
                "decision_limit_exceeded", {"limit": max_decisions, "seed": seed}
            )
        state = _mapping(snapshot.get("state"), "native snapshot.state")
        if state.get("seed") != str(seed):
            raise CompatibilityBlocked("environment_seed_mismatch", seed)
        decision_index = snapshot.get("decision_count")
        if isinstance(decision_index, bool) or not isinstance(decision_index, int):
            raise CompatibilityBlocked("decision_index_invalid", decision_index)
        category = snapshot.get("category")
        if category not in TARGET_CATEGORIES:
            raise CompatibilityBlocked("target_category_invalid", category)
        try:
            candidates = validate_candidates(
                environment.legal_actions(), category=category
            )
        except (SimulatorAdapterError, TypeError, ValueError) as exc:
            raise CompatibilityBlocked("legal_actions_invalid", str(exc)) from exc
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
            raise CompatibilityBlocked(exc.reason, exc.detail) from exc
        except CompatibilityBlocked:
            raise
        except Exception as exc:
            raise CompatibilityBlocked(
                "current_policy_evaluation_failed",
                {"message": str(exc), "type": type(exc).__name__},
            ) from exc
        if canonical_json_bytes(snapshot) != before_snapshot:
            raise CompatibilityBlocked("source_snapshot_mutated")
        if canonical_json_bytes(candidates) != before_candidates:
            raise CompatibilityBlocked("source_candidates_mutated")
        if (
            evaluation.get("category") != category
            or evaluation.get("policy_id") != POLICY_ID
            or evaluation.get("fallback_used") is not False
            or evaluation.get("tracker_enabled") is not False
            or evaluation.get("source_mutated") is not False
        ):
            raise CompatibilityBlocked("current_evaluation_contract_invalid", evaluation)
        expected_snapshot_sha256 = sha256_bytes(before_snapshot)
        expected_candidates_sha256 = sha256_bytes(before_candidates)
        if (
            evaluation.get("input_snapshot_sha256") != expected_snapshot_sha256
            or evaluation.get("input_candidates_sha256")
            != expected_candidates_sha256
        ):
            raise CompatibilityBlocked("policy_input_hash_mismatch")
        action_id = evaluation.get("action_id")
        matches = [
            candidate for candidate in candidates if candidate["action_id"] == action_id
        ]
        if len(matches) != 1:
            raise CompatibilityBlocked("selected_action_not_unique_candidate", action_id)
        event_observation = None
        if category == "event":
            event_observation = _event_diagnostic(
                evaluation, matches[0], candidates, snapshot
            )
            event_identities.append(copy.deepcopy(event_observation))
        try:
            transition = _mapping(environment.step(action_id), "native transition")
        except CompatibilityBlocked:
            raise
        except Exception as exc:
            raise CompatibilityBlocked(
                "native_step_failed",
                {"message": str(exc), "type": type(exc).__name__},
            ) from exc
        if transition.get("selected_action_id") != action_id:
            raise CompatibilityBlocked("transition_action_mismatch", action_id)
        decisions.append(
            {
                "action_id": action_id,
                "action_type": evaluation.get("action_type"),
                "candidate_actions_sha256": expected_candidates_sha256,
                "category": category,
                "decision_index": decision_index,
                "event_observation": event_observation,
                "policy_input_sha256": sha256_bytes(
                    canonical_json_bytes(
                        {
                            "candidates": evaluation.get("input_candidates_sha256"),
                            "snapshot": evaluation.get("input_snapshot_sha256"),
                        }
                    )
                ),
                "source_snapshot_sha256": expected_snapshot_sha256,
            }
        )
        category_counts[category] += 1

    state = _mapping(snapshot.get("state"), "terminal state")
    terminal_floor = state.get("floor")
    outcome = state.get("outcome")
    if (
        isinstance(terminal_floor, bool)
        or not isinstance(terminal_floor, int)
        or outcome not in {"player_loss", "player_victory"}
    ):
        raise CompatibilityBlocked(
            "terminal_state_invalid", {"floor": terminal_floor, "outcome": outcome}
        )
    row = {
        "category_counts": {
            category: category_counts[category] for category in TARGET_CATEGORIES
        },
        "decision_count": len(decisions),
        "decisions": decisions,
        "event_identities": event_identities,
        "outcome": outcome,
        "seed": seed,
        "terminal_floor": terminal_floor,
    }
    row["trajectory_sha256"] = sha256_bytes(canonical_json_bytes(row))
    return row


def run_compatibility_cohort(
    *,
    registration: Mapping[str, Any],
    environment_factory: Callable[[int], Any],
    session_factory: Callable[[], Any],
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    normalized = validate_registration(copy.deepcopy(registration))
    deadline = monotonic() + normalized["limits"]["max_wall_seconds"]
    rows: list[dict[str, Any]] = []
    try:
        for seed in normalized["cohort"]["seeds"]:
            replays = []
            for _ in range(normalized["cohort"]["replay_count"]):
                if monotonic() > deadline:
                    raise CompatibilityBlocked("execution_deadline_exceeded")
                try:
                    environment = environment_factory(seed)
                    session = session_factory()
                except KeyboardInterrupt:
                    raise
                except Exception as exc:
                    raise CompatibilityBlocked(
                        "environment_construction_failed",
                        {"message": str(exc), "type": type(exc).__name__},
                    ) from exc
                replays.append(
                    _run_replay(
                        environment=environment,
                        session=session,
                        seed=seed,
                        max_decisions=normalized["limits"][
                            "max_decisions_per_replay"
                        ],
                        deadline=deadline,
                        monotonic=monotonic,
                    )
                )
            if canonical_json_bytes(replays[0]) != canonical_json_bytes(replays[1]):
                raise CompatibilityBlocked(
                    "trajectory_nondeterministic",
                    {
                        "first": replays[0]["trajectory_sha256"],
                        "second": replays[1]["trajectory_sha256"],
                        "seed": seed,
                    },
                )
            rows.append({**replays[0], "replay_count": REPLAY_COUNT})
        counts = Counter()
        for row in rows:
            counts.update(row["category_counts"])
        category_counts = {
            category: counts[category] for category in TARGET_CATEGORIES
        }
        missing = [
            category for category, count in category_counts.items() if count <= 0
        ]
        if missing:
            raise CompatibilityBlocked("aggregate_category_coverage_missing", missing)
        return {
            "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
            "category_counts": category_counts,
            "detail": None,
            "reason": None,
            "rows": rows,
            "schema_version": EXECUTION_SCHEMA_VERSION,
            "seeds": list(normalized["cohort"]["seeds"]),
            "status": "passed",
            "verdict": "reachable_event_native_compatibility_passed",
        }
    except KeyboardInterrupt:
        raise
    except CompatibilityBlocked as exc:
        return _failed_result(
            registration=normalized,
            reason=exc.reason,
            detail=exc.detail,
            rows=rows,
        )
    except Exception as exc:
        return _failed_result(
            registration=normalized,
            reason="compatibility_execution_failed",
            detail={"message": str(exc), "type": type(exc).__name__},
            rows=rows,
        )


def _validate_result_row(
    value: object, *, expected_seed: int, row_index: int
) -> dict[str, Any]:
    row = _mapping(value, f"execution row[{row_index}]")
    expected_keys = {
        "category_counts",
        "decision_count",
        "decisions",
        "event_identities",
        "outcome",
        "replay_count",
        "seed",
        "terminal_floor",
        "trajectory_sha256",
    }
    _require_keys(row, expected_keys, f"execution row[{row_index}]")
    if (
        row["seed"] != expected_seed
        or row["replay_count"] != REPLAY_COUNT
        or row["outcome"] not in {"player_loss", "player_victory"}
        or isinstance(row["terminal_floor"], bool)
        or not isinstance(row["terminal_floor"], int)
        or row["terminal_floor"] < 0
        or isinstance(row["decision_count"], bool)
        or not isinstance(row["decision_count"], int)
        or row["decision_count"] < 0
        or not _is_hex(row["trajectory_sha256"], 64)
    ):
        raise CompatibilityBlocked("execution_row_identity_invalid", row_index)
    decisions = []
    decision_counts = Counter()
    expected_event_identities = []
    for decision_index, raw_decision in enumerate(
        _sequence(row["decisions"], f"execution row[{row_index}].decisions")
    ):
        decision = _mapping(raw_decision, f"decision[{row_index}:{decision_index}]")
        _require_keys(
            decision,
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
            f"decision[{row_index}:{decision_index}]",
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
            or any(
                not _is_hex(decision[field], 64)
                for field in (
                    "candidate_actions_sha256",
                    "policy_input_sha256",
                    "source_snapshot_sha256",
                )
            )
        ):
            raise CompatibilityBlocked(
                "execution_decision_invalid", {"row": row_index, "decision": decision_index}
            )
        observation = decision["event_observation"]
        if decision["category"] == "event":
            observation = _mapping(
                observation, f"event observation[{row_index}:{decision_index}]"
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
                f"event observation[{row_index}:{decision_index}]",
            )
            if (
                observation["semantics_source"]
                != reachable_event_option_semantics_identity()["contract_id"]
                or observation["selected_action_id"] != decision["action_id"]
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
                raise CompatibilityBlocked(
                    "execution_event_observation_invalid",
                    {"row": row_index, "decision": decision_index},
                )
            expected_event_identities.append(copy.deepcopy(observation))
        elif observation is not None:
            raise CompatibilityBlocked(
                "execution_non_event_observation_present",
                {"row": row_index, "decision": decision_index},
            )
        decisions.append(decision)
        decision_counts[decision["category"]] += 1
    if len(decisions) > MAX_DECISIONS_PER_REPLAY:
        raise CompatibilityBlocked("execution_decision_limit_exceeded", row_index)
    counts = _mapping(row["category_counts"], f"row[{row_index}].category_counts")
    expected_counts = {
        category: decision_counts[category] for category in TARGET_CATEGORIES
    }
    if (
        counts != expected_counts
        or row["decision_count"] != len(decisions)
        or row["event_identities"] != expected_event_identities
    ):
        raise CompatibilityBlocked("execution_row_counts_mismatch", row_index)
    base_row = copy.deepcopy(row)
    del base_row["replay_count"]
    actual_trajectory_sha256 = base_row.pop("trajectory_sha256")
    expected_trajectory_sha256 = sha256_bytes(canonical_json_bytes(base_row))
    if actual_trajectory_sha256 != expected_trajectory_sha256:
        raise CompatibilityBlocked("trajectory_hash_mismatch", row_index)
    return row


def _validate_execution_result(
    value: object, registration: Mapping[str, Any]
) -> dict[str, Any]:
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
            "verdict",
        },
        "execution result",
    )
    if result["schema_version"] != EXECUTION_SCHEMA_VERSION:
        raise CompatibilityBlocked("execution_schema_mismatch")
    if result["authority"] != ALL_FALSE_AUTHORITY:
        raise CompatibilityBlocked("authority_must_be_all_false")
    if result["seeds"] != list(registration["cohort"]["seeds"]):
        raise CompatibilityBlocked("execution_seed_mismatch")
    counts = _mapping(result["category_counts"], "category counts")
    if set(counts) != set(TARGET_CATEGORIES) or any(
        isinstance(count, bool) or not isinstance(count, int) or count < 0
        for count in counts.values()
    ):
        raise CompatibilityBlocked("execution_category_counts_invalid")
    raw_rows = _sequence(result["rows"], "execution rows")
    if len(raw_rows) > COHORT_SIZE:
        raise CompatibilityBlocked("execution_row_count_exceeded")
    rows = [
        _validate_result_row(
            raw_row,
            expected_seed=registration["cohort"]["seeds"][index],
            row_index=index,
        )
        for index, raw_row in enumerate(raw_rows)
    ]
    aggregate = Counter()
    for row in rows:
        aggregate.update(row["category_counts"])
    if counts != {category: aggregate[category] for category in TARGET_CATEGORIES}:
        raise CompatibilityBlocked("execution_aggregate_counts_mismatch")
    if result["status"] == "passed":
        if (
            result["verdict"] != "reachable_event_native_compatibility_passed"
            or result["reason"] is not None
            or result["detail"] is not None
            or len(rows) != COHORT_SIZE
            or any(count <= 0 for count in counts.values())
        ):
            raise CompatibilityBlocked("execution_pass_invalid")
    elif result["status"] == "failed":
        if (
            result["verdict"] != "reachable_event_native_compatibility_failed"
            or not isinstance(result["reason"], str)
            or not result["reason"]
        ):
            raise CompatibilityBlocked("execution_failure_invalid")
    else:
        raise CompatibilityBlocked("execution_status_invalid")
    result["rows"] = rows
    return copy.deepcopy(result)


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def _started_journal(
    *,
    registration: Mapping[str, Any],
    registration_sha256: str,
    preregistration_commit: str,
) -> dict[str, Any]:
    return {
        "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
        "consumed_seeds": list(registration["cohort"]["seeds"]),
        "preregistration_commit": preregistration_commit,
        "registration_sha256": registration_sha256,
        "result_sha256": None,
        "schema_version": JOURNAL_SCHEMA_VERSION,
        "status": "started",
        "verdict": None,
    }


def _report_markdown(result: Mapping[str, Any]) -> bytes:
    lines = [
        "# Reachable Event Native Compatibility",
        "",
        f"- Status: `{result['status']}`",
        f"- Verdict: `{result['verdict']}`",
        f"- Reason: `{result['reason']}`",
        f"- Completed seed rows: `{len(result['rows'])}`",
        "- Authority: structural compatibility only; every downstream flag is false.",
        "",
        "## Category Counts",
        "",
    ]
    for category in TARGET_CATEGORIES:
        lines.append(f"- {category}: `{result['category_counts'][category]}`")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "Terminal floors and outcomes are diagnostics only. This result does not",
            "authorize gameplay, a baseline floor, reward selection, OPE, formal RL,",
            "training, qualification, loading, or promotion.",
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
) -> dict[str, bytes]:
    validated_result = _validate_execution_result(result, registration)
    result_sha256 = sha256_bytes(canonical_json_bytes(validated_result))
    journal = {
        **_started_journal(
            registration=registration,
            registration_sha256=registration_sha256,
            preregistration_commit=preregistration_commit,
        ),
        "result_sha256": result_sha256,
        "status": "finalized",
        "verdict": validated_result["verdict"],
    }
    configuration = {
        "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
        "preregistration_commit": preregistration_commit,
        "registration": copy.deepcopy(dict(registration)),
        "registration_sha256": registration_sha256,
        "schema_version": CONFIGURATION_SCHEMA_VERSION,
    }
    metrics = {
        "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
        "category_counts": copy.deepcopy(validated_result["category_counts"]),
        "completed_seed_rows": len(validated_result["rows"]),
        "reason": copy.deepcopy(validated_result["reason"]),
        "registration_sha256": registration_sha256,
        "schema_version": METRICS_SCHEMA_VERSION,
        "seeds": list(validated_result["seeds"]),
        "status": validated_result["status"],
        "verdict": validated_result["verdict"],
    }
    trajectories = {
        "result": copy.deepcopy(validated_result),
        "schema_version": TRAJECTORY_SCHEMA_VERSION,
    }
    return {
        "configuration.json": canonical_json_bytes(configuration),
        "execution_journal.json": canonical_json_bytes(journal),
        "metrics.json": canonical_json_bytes(metrics),
        "report.md": _report_markdown(validated_result),
        "trajectory_rows.json": canonical_json_bytes(trajectories),
    }


def _artifact_binding(name: str, payload: bytes) -> dict[str, Any]:
    return {"path": name, "sha256": sha256_bytes(payload), "size_bytes": len(payload)}


def _build_manifest(
    *,
    registration_sha256: str,
    result: Mapping[str, Any],
    payloads: Mapping[str, bytes],
) -> bytes:
    manifest = {
        "artifact_bindings": {
            name: _artifact_binding(name, payload)
            for name, payload in sorted(payloads.items())
        },
        "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
        "registration_sha256": registration_sha256,
        "schema_version": MANIFEST_SCHEMA_VERSION,
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
) -> dict[str, Any]:
    normalized = validate_registration(copy.deepcopy(registration))
    if not _is_hex(registration_sha256, 64) or not _is_hex(
        preregistration_commit, 40
    ):
        raise CompatibilityBlocked("execution_identity_invalid")
    output = Path(output_directory).resolve()
    if output.exists():
        raise CompatibilityBlocked("output_directory_already_exists", str(output))
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        output.mkdir()
    except FileExistsError as exc:
        raise CompatibilityBlocked(
            "output_directory_already_exists", str(output)
        ) from exc
    started = _started_journal(
        registration=normalized,
        registration_sha256=registration_sha256,
        preregistration_commit=preregistration_commit,
    )
    _write_atomic(
        output / "execution_journal.json", canonical_json_bytes(started)
    )
    result = run_compatibility_cohort(
        registration=normalized,
        environment_factory=environment_factory,
        session_factory=session_factory,
        monotonic=monotonic,
    )
    payloads = _deterministic_payloads(
        registration=normalized,
        registration_sha256=registration_sha256,
        preregistration_commit=preregistration_commit,
        result=result,
    )
    for name, payload in payloads.items():
        _write_atomic(output / name, payload)
    manifest = _build_manifest(
        registration_sha256=registration_sha256,
        result=result,
        payloads=payloads,
    )
    _write_atomic(output / "artifact_manifest.json", manifest)
    return result


def verify_artifact_directory(
    *,
    registration: Mapping[str, Any],
    registration_sha256: str,
    output_directory: Path | str,
) -> dict[str, Any]:
    normalized = validate_registration(copy.deepcopy(registration))
    output = Path(output_directory).resolve()
    if not output.is_dir():
        raise CompatibilityBlocked("artifact_directory_missing", str(output))
    actual_names = sorted(path.name for path in output.iterdir() if path.is_file())
    if actual_names != sorted(CANONICAL_ARTIFACT_NAMES):
        raise CompatibilityBlocked(
            "artifact_inventory_mismatch",
            {"actual": actual_names, "expected": sorted(CANONICAL_ARTIFACT_NAMES)},
        )
    configuration = _load_json(output / "configuration.json", "configuration")
    if (
        configuration.get("schema_version") != CONFIGURATION_SCHEMA_VERSION
        or configuration.get("registration_sha256") != registration_sha256
        or configuration.get("registration") != normalized
        or configuration.get("authority") != ALL_FALSE_AUTHORITY
    ):
        raise CompatibilityBlocked("configuration_identity_mismatch")
    preregistration_commit = configuration.get("preregistration_commit")
    if not _is_hex(preregistration_commit, 40):
        raise CompatibilityBlocked("configuration_commit_invalid")
    trajectories = _load_json(output / "trajectory_rows.json", "trajectories")
    if trajectories.get("schema_version") != TRAJECTORY_SCHEMA_VERSION:
        raise CompatibilityBlocked("trajectory_schema_mismatch")
    result = _validate_execution_result(trajectories.get("result"), normalized)
    expected_payloads = _deterministic_payloads(
        registration=normalized,
        registration_sha256=registration_sha256,
        preregistration_commit=preregistration_commit,
        result=result,
    )
    for name, expected in expected_payloads.items():
        if (output / name).read_bytes() != expected:
            raise CompatibilityBlocked("artifact_recomputation_mismatch", name)
    expected_manifest = _build_manifest(
        registration_sha256=registration_sha256,
        result=result,
        payloads=expected_payloads,
    )
    if (output / "artifact_manifest.json").read_bytes() != expected_manifest:
        raise CompatibilityBlocked("manifest_recomputation_mismatch")
    return _load_json(output / "artifact_manifest.json", "manifest")


def prepare_registration(
    *,
    repo_root: Path | str,
    module_path: Path | str,
    simulator_repo: Path | str,
    metadata_path: Path | str,
    dll_directories: Sequence[Path | str] = (),
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    native_path = Path(module_path).resolve()
    simulator_path = Path(simulator_repo).resolve()
    metadata = Path(metadata_path).resolve()
    implementation_commit = _assert_clean_pushed_head(root)
    managed_paths = [
        root / DEFAULT_REGISTRATION_PATH,
        root / DEFAULT_SEED_INVENTORY_PATH,
        root / DEFAULT_SEED_LEDGER_PATH,
        root / DEFAULT_OUTPUT_DIRECTORY,
    ]
    if any(path.exists() for path in managed_paths):
        raise CompatibilityBlocked("managed_evidence_already_exists")
    inventory = build_tracked_seed_inventory(root)
    seeds = select_untouched_cohort(inventory)
    ledger = build_seed_ledger(inventory=inventory, seeds=seeds)
    try:
        native_module = load_native_module(
            native_path, dll_directories=dll_directories
        )
    except SimulatorAdapterError as exc:
        raise CompatibilityBlocked("native_module_load_failed", str(exc)) from exc
    provenance = collect_native_identity(
        module_path=native_path,
        simulator_repo=simulator_path,
        repo_root=root,
        native_module=native_module,
        adapter_commit=implementation_commit,
    )
    inventory_bytes = canonical_json_bytes(inventory)
    ledger_bytes = canonical_json_bytes(ledger)
    contract = reachable_event_option_semantics_identity()
    contract_relative = contract["observation_contract"]["path"]
    identity = {
        "adapter_provenance": provenance,
        "adapter_source_files": list(ADAPTER_SOURCE_FILES),
        "contract": contract,
        "contract_file": _file_binding(root / contract_relative, contract_relative),
        "implementation": {
            "commit": implementation_commit,
            "source_files": list(IMPLEMENTATION_SOURCE_FILES),
            "source_sha256": hash_bound_files(root, IMPLEMENTATION_SOURCE_FILES),
        },
        "metadata": _file_binding(metadata, str(metadata)),
        "module_path": str(native_path),
        "predecessors": {
            name: _file_binding(root / relative, relative)
            for name, relative in PREDECESSOR_PATHS.items()
        },
        "runtime": {
            "executable": str(Path(sys.executable).resolve()),
            "python": sys.version.split()[0],
        },
        "seed_inventory": {
            "path": DEFAULT_SEED_INVENTORY_PATH,
            "sha256": sha256_bytes(inventory_bytes),
            "size_bytes": len(inventory_bytes),
        },
        "seed_ledger": {
            "path": DEFAULT_SEED_LEDGER_PATH,
            "sha256": sha256_bytes(ledger_bytes),
            "size_bytes": len(ledger_bytes),
        },
        "simulator_path": str(simulator_path),
    }
    registration = build_registration(identity=identity, seeds=seeds)
    _write_atomic(root / DEFAULT_SEED_INVENTORY_PATH, inventory_bytes)
    _write_atomic(root / DEFAULT_SEED_LEDGER_PATH, ledger_bytes)
    _write_atomic(root / DEFAULT_REGISTRATION_PATH, canonical_json_bytes(registration))
    validate_registration_evidence(registration, root)
    return {
        "cohort_seeds": seeds,
        "implementation_commit": implementation_commit,
        "registration_path": DEFAULT_REGISTRATION_PATH,
        "registration_sha256": sha256_file(root / DEFAULT_REGISTRATION_PATH),
        "seed_inventory_path": DEFAULT_SEED_INVENTORY_PATH,
        "seed_inventory_sha256": sha256_file(root / DEFAULT_SEED_INVENTORY_PATH),
        "seed_ledger_path": DEFAULT_SEED_LEDGER_PATH,
        "seed_ledger_sha256": sha256_file(root / DEFAULT_SEED_LEDGER_PATH),
    }


def execute_registered(
    *, repo_root: Path | str, dll_directories: Sequence[Path | str] = ()
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    registration_path = root / DEFAULT_REGISTRATION_PATH
    pushed = assert_pushed_registration(
        registration_path=registration_path, repo_root=root
    )
    registration = load_registration(registration_path)
    _, _, metadata = validate_registration_evidence(registration, root)
    identity = registration["identity"]
    try:
        native_module = load_native_module(
            identity["module_path"], dll_directories=dll_directories
        )
    except SimulatorAdapterError as exc:
        raise CompatibilityBlocked("native_module_load_failed", str(exc)) from exc
    actual_provenance = collect_native_identity(
        module_path=identity["module_path"],
        simulator_repo=identity["simulator_path"],
        repo_root=root,
        native_module=native_module,
        adapter_commit=identity["adapter_provenance"]["adapter_commit"],
    )
    if actual_provenance != identity["adapter_provenance"]:
        raise CompatibilityBlocked("native_identity_mismatch")
    provenance = identity["adapter_provenance"]

    def environment_factory(seed: int) -> NativeSimulatorEnvironment:
        return NativeSimulatorEnvironment(
            native_module.Environment(seed, registration["current_policy"]["ascension"]),
            provenance,
        )

    def session_factory() -> CurrentPolicyBridgeSession:
        return CurrentPolicyBridgeSession(
            metadata=metadata,
            current_policy=registration["current_policy"],
            event_semantics_identity=reachable_event_option_semantics_identity(),
            simulator_provenance=provenance,
        )

    result = consume_and_run(
        registration=registration,
        registration_sha256=pushed["registration_sha256"],
        preregistration_commit=pushed["preregistration_commit"],
        output_directory=root / registration["output"]["directory"],
        environment_factory=environment_factory,
        session_factory=session_factory,
    )
    return {
        "output_directory": registration["output"]["directory"],
        "reason": result["reason"],
        "status": result["status"],
        "verdict": result["verdict"],
    }


def verify_registered(*, repo_root: Path | str) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    registration_path = root / DEFAULT_REGISTRATION_PATH
    registration = load_registration(registration_path)
    validate_registration_evidence(registration, root)
    manifest = verify_artifact_directory(
        registration=registration,
        registration_sha256=sha256_file(registration_path),
        output_directory=root / registration["output"]["directory"],
    )
    return {
        "output_directory": registration["output"]["directory"],
        "verdict": manifest["verdict"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare")
    prepare.add_argument("--module", type=Path, required=True)
    prepare.add_argument("--simulator-repo", type=Path, required=True)
    prepare.add_argument("--metadata", type=Path, required=True)
    prepare.add_argument("--dll-directory", action="append", type=Path, default=[])
    execute = commands.add_parser("execute")
    execute.add_argument("--dll-directory", action="append", type=Path, default=[])
    commands.add_parser("verify")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare_registration(
                repo_root=args.repo_root,
                module_path=args.module,
                simulator_repo=args.simulator_repo,
                metadata_path=args.metadata,
                dll_directories=args.dll_directory,
            )
        elif args.command == "execute":
            result = execute_registered(
                repo_root=args.repo_root, dll_directories=args.dll_directory
            )
        else:
            result = verify_registered(repo_root=args.repo_root)
    except CompatibilityBlocked as exc:
        print(json.dumps({"detail": exc.detail, "reason": exc.reason}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
