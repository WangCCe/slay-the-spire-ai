"""Run one preregistered API v3 Current-policy native compatibility cohort."""

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

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from analysis_scripts.noncombat_current_policy_simulator_bridge import (
    BridgeBlocked,
    CurrentPolicyBridgeSession,
    MetadataCatalog,
    POLICY_ID,
    hash_bound_files,
)
from analysis_scripts.noncombat_event_option_semantics import (
    event_option_semantics_identity,
)
from analysis_scripts.noncombat_simulator_adapter import (
    ADAPTER_API_VERSION,
    NativeSimulatorEnvironment,
    SimulatorAdapterError,
    TARGET_CATEGORIES,
    canonical_json_bytes,
    hash_compiled_simulator_sources,
    load_native_module,
    sha256_bytes,
    sha256_file,
    validate_candidates,
    validate_provenance,
)


INPUT_SCHEMA_VERSION = "noncombat-total-event-native-compatibility-input-v1"
SEED_LEDGER_SCHEMA_VERSION = (
    "noncombat-total-event-native-compatibility-seed-ledger-v1"
)
EXECUTION_SCHEMA_VERSION = (
    "noncombat-total-event-native-compatibility-execution-v1"
)
JOURNAL_SCHEMA_VERSION = (
    "noncombat-total-event-native-compatibility-journal-v1"
)
CONFIGURATION_SCHEMA_VERSION = (
    "noncombat-total-event-native-compatibility-configuration-v1"
)
METRICS_SCHEMA_VERSION = (
    "noncombat-total-event-native-compatibility-metrics-v1"
)
TRAJECTORY_SCHEMA_VERSION = (
    "noncombat-total-event-native-compatibility-trajectories-v1"
)
MANIFEST_SCHEMA_VERSION = (
    "noncombat-total-event-native-compatibility-manifest-v1"
)

COHORT_SEEDS = tuple(range(7000, 7008))
REPLAY_COUNT = 2
MAX_DECISIONS_PER_REPLAY = 500
MAX_WALL_SECONDS = 120.0

DEFAULT_REGISTRATION_PATH = (
    "reports/noncombat_total_event_native_compatibility_20260803_input.json"
)
DEFAULT_SEED_LEDGER_PATH = (
    "reports/noncombat_total_event_native_compatibility_20260803_seed_ledger.json"
)
DEFAULT_OUTPUT_DIRECTORY = (
    "reports/noncombat_total_event_native_compatibility_20260803"
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

ADAPTER_SOURCE_FILES = (
    "simulator_adapters/sts_lightspeed/CMakeLists.txt",
    "simulator_adapters/sts_lightspeed/noncombat_adapter.cpp",
)

IMPLEMENTATION_SOURCE_FILES = (
    "analysis_scripts/noncombat_total_event_native_compatibility.py",
    "analysis_scripts/noncombat_current_policy_simulator_bridge.py",
    "analysis_scripts/noncombat_event_option_observation_contract.py",
    "analysis_scripts/noncombat_event_option_semantics.py",
    "analysis_scripts/noncombat_simulator_adapter.py",
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
    "bridge_closeout": (
        "reports/noncombat_total_event_option_observation_bridge_20260803_closeout.md"
    ),
    "bridge_manifest": (
        "reports/noncombat_current_policy_simulator_bridge_20260802_r2/"
        "artifact_manifest.json"
    ),
    "bridge_registration": (
        "reports/noncombat_current_policy_simulator_bridge_20260802_r2_input.json"
    ),
}

PRIOR_SEED_SOURCES = (
    {
        "path": "reports/noncombat_simulator_policy_validity_20260802_input.json",
        "sets": (
            ("study.cohorts.fit_seeds", "consumed"),
            ("study.cohorts.smoke_train_seeds", "consumed"),
            ("study.cohorts.smoke_holdout_seeds", "consumed"),
            ("study.cohorts.compatibility_seeds", "consumed"),
            ("study.cohorts.fresh_seeds", "consumed"),
        ),
    },
    {
        "path": (
            "reports/noncombat_simulator_baseline_warm_start_20260802_input.json"
        ),
        "sets": (
            ("study.cohorts.excluded_prior_seeds", "consumed"),
            ("study.cohorts.train_seeds", "consumed"),
            ("study.cohorts.validation_seeds", "consumed"),
            ("study.cohorts.final_test_seeds", "reserved"),
        ),
    },
)


class CompatibilityBlocked(RuntimeError):
    """Raised when the preregistered compatibility boundary cannot be proved."""

    def __init__(self, reason: str, detail: object | None = None):
        self.reason = reason
        self.detail = detail
        message = reason if detail is None else f"{reason}: {detail}"
        super().__init__(message)


def _reject_duplicate_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CompatibilityBlocked("duplicate_json_key", key)
        result[key] = value
    return result


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
    path = PurePosixPath(str(value).replace("\\", "/"))
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise CompatibilityBlocked("path_not_repository_relative", label)
    return path.as_posix()


def _absolute_path(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or not Path(value).is_absolute():
        raise CompatibilityBlocked("path_not_absolute", label)
    return str(Path(value).resolve())


def _validate_binding(
    value: object, label: str, *, repository_relative: bool
) -> dict[str, Any]:
    binding = _mapping(value, label)
    _require_keys(binding, {"path", "sha256", "size_bytes"}, label)
    if repository_relative:
        binding["path"] = _repository_relative_path(binding["path"], label)
    elif not isinstance(binding["path"], str) or not binding["path"]:
        raise CompatibilityBlocked("binding_path_invalid", label)
    if not _is_hex(binding["sha256"], 64):
        raise CompatibilityBlocked("binding_sha256_invalid", label)
    size = binding["size_bytes"]
    if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
        raise CompatibilityBlocked("binding_size_invalid", label)
    return binding


def _load_json(path: Path | str, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            Path(path).read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
        )
    except CompatibilityBlocked:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CompatibilityBlocked("cannot_load_json", {"label": label, "error": str(exc)}) from exc
    return _mapping(value, label)


def _file_binding(path: Path, display_path: str) -> dict[str, Any]:
    if not path.is_file():
        raise CompatibilityBlocked("bound_file_missing", display_path)
    return {
        "path": display_path,
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def _json_path(value: Mapping[str, Any], path: str) -> object:
    current: object = value
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            raise CompatibilityBlocked("seed_ledger_json_path_missing", path)
        current = current[part]
    return current


def _validated_seed_array(value: object, label: str) -> list[int]:
    seeds = _sequence(value, label)
    if seeds != sorted(set(seeds)):
        raise CompatibilityBlocked("seed_array_not_sorted_unique", label)
    for seed in seeds:
        if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
            raise CompatibilityBlocked("seed_array_invalid", label)
    return seeds


def build_seed_ledger(repo_root: Path | str) -> dict[str, Any]:
    """Expand every bound historical seed set without touching a simulator."""

    root = Path(repo_root).resolve()
    consumed: set[int] = set()
    reserved: set[int] = set()
    sources = []
    for source_spec in PRIOR_SEED_SOURCES:
        relative = str(source_spec["path"])
        source_path = root / relative
        payload = _load_json(source_path, f"seed source {relative}")
        sets = []
        for json_path, disposition in source_spec["sets"]:
            seeds = _validated_seed_array(
                _json_path(payload, json_path), f"seed source {json_path}"
            )
            (consumed if disposition == "consumed" else reserved).update(seeds)
            sets.append(
                {
                    "disposition": disposition,
                    "json_path": json_path,
                    "seeds": seeds,
                }
            )
        sources.append(
            {"binding": _file_binding(source_path, relative), "sets": sets}
        )
    ledger = {
        "candidate_seeds": list(COHORT_SEEDS),
        "consumed_seeds": sorted(consumed),
        "reserved_seeds": sorted(reserved),
        "schema_version": SEED_LEDGER_SCHEMA_VERSION,
        "sources": sources,
    }
    return validate_seed_ledger(ledger)


def validate_seed_ledger(value: object) -> dict[str, Any]:
    ledger = _mapping(value, "seed ledger")
    _require_keys(
        ledger,
        {
            "candidate_seeds",
            "consumed_seeds",
            "reserved_seeds",
            "schema_version",
            "sources",
        },
        "seed ledger",
    )
    if ledger["schema_version"] != SEED_LEDGER_SCHEMA_VERSION:
        raise CompatibilityBlocked("seed_ledger_schema_mismatch")
    ledger["candidate_seeds"] = _validated_seed_array(
        ledger["candidate_seeds"], "seed ledger candidate_seeds"
    )
    ledger["consumed_seeds"] = _validated_seed_array(
        ledger["consumed_seeds"], "seed ledger consumed_seeds"
    )
    ledger["reserved_seeds"] = _validated_seed_array(
        ledger["reserved_seeds"], "seed ledger reserved_seeds"
    )
    if ledger["candidate_seeds"] != list(COHORT_SEEDS):
        raise CompatibilityBlocked("seed_ledger_candidate_mismatch")
    unavailable = set(ledger["consumed_seeds"]) | set(ledger["reserved_seeds"])
    overlap = sorted(set(ledger["candidate_seeds"]) & unavailable)
    if overlap:
        raise CompatibilityBlocked("seed_ledger_overlap", overlap)

    sources = _sequence(ledger["sources"], "seed ledger sources")
    if len(sources) != len(PRIOR_SEED_SOURCES):
        raise CompatibilityBlocked("seed_ledger_source_count_mismatch")
    computed_consumed: set[int] = set()
    computed_reserved: set[int] = set()
    normalized_sources = []
    for index, raw_source in enumerate(sources):
        source = _mapping(raw_source, f"seed ledger sources[{index}]")
        _require_keys(source, {"binding", "sets"}, f"seed ledger sources[{index}]")
        binding = _validate_binding(
            source["binding"],
            f"seed ledger sources[{index}].binding",
            repository_relative=True,
        )
        expected_spec = PRIOR_SEED_SOURCES[index]
        if binding["path"] != expected_spec["path"]:
            raise CompatibilityBlocked("seed_ledger_source_path_mismatch", index)
        raw_sets = _sequence(source["sets"], f"seed ledger sources[{index}].sets")
        if len(raw_sets) != len(expected_spec["sets"]):
            raise CompatibilityBlocked("seed_ledger_set_count_mismatch", index)
        normalized_sets = []
        for set_index, raw_set in enumerate(raw_sets):
            seed_set = _mapping(raw_set, "seed ledger set")
            _require_keys(
                seed_set, {"disposition", "json_path", "seeds"}, "seed ledger set"
            )
            expected_path, expected_disposition = expected_spec["sets"][set_index]
            if (
                seed_set["json_path"] != expected_path
                or seed_set["disposition"] != expected_disposition
            ):
                raise CompatibilityBlocked("seed_ledger_set_identity_mismatch")
            seeds = _validated_seed_array(seed_set["seeds"], expected_path)
            target = (
                computed_consumed
                if expected_disposition == "consumed"
                else computed_reserved
            )
            target.update(seeds)
            normalized_sets.append({**seed_set, "seeds": seeds})
        normalized_sources.append({"binding": binding, "sets": normalized_sets})
    if ledger["consumed_seeds"] != sorted(computed_consumed):
        raise CompatibilityBlocked("seed_ledger_consumed_mismatch")
    if ledger["reserved_seeds"] != sorted(computed_reserved):
        raise CompatibilityBlocked("seed_ledger_reserved_mismatch")
    ledger["sources"] = normalized_sources
    return ledger


def build_registration(*, identity: Mapping[str, Any]) -> dict[str, Any]:
    registration = {
        "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
        "cohort": {"replay_count": REPLAY_COUNT, "seeds": list(COHORT_SEEDS)},
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
        raise CompatibilityBlocked(
            "authority_must_be_all_false", registration["authority"]
        )
    if registration["current_policy"] != CURRENT_POLICY:
        raise CompatibilityBlocked("current_policy_mismatch")

    cohort = _mapping(registration["cohort"], "cohort")
    if cohort != {"replay_count": REPLAY_COUNT, "seeds": list(COHORT_SEEDS)}:
        raise CompatibilityBlocked("cohort_mismatch", cohort)
    registration["cohort"] = cohort
    limits = _mapping(registration["limits"], "limits")
    expected_limits = {
        "max_decisions_per_replay": MAX_DECISIONS_PER_REPLAY,
        "max_wall_seconds": MAX_WALL_SECONDS,
    }
    if limits != expected_limits:
        raise CompatibilityBlocked("limits_mismatch", limits)
    registration["limits"] = limits

    output = _mapping(registration["output"], "output")
    if output != {
        "artifact_names": list(CANONICAL_ARTIFACT_NAMES),
        "directory": DEFAULT_OUTPUT_DIRECTORY,
    }:
        raise CompatibilityBlocked("output_contract_mismatch", output)
    registration["output"] = output

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
            "seed_ledger",
            "simulator_path",
        },
        "identity",
    )
    try:
        provenance = validate_provenance(identity["adapter_provenance"])
    except (TypeError, ValueError) as exc:
        raise CompatibilityBlocked("native_provenance_invalid", str(exc)) from exc
    if provenance["build"].get("adapter_api_version") != ADAPTER_API_VERSION:
        raise CompatibilityBlocked("native_adapter_api_mismatch")
    build = _mapping(provenance["build"], "native build identity")
    expected_build_keys = {
        "adapter_api_version",
        "baseline_policy_id",
        "compiler",
        "cpp_standard",
        "native_target_policy_id",
        "pybind11_version",
        "python",
    }
    if set(build) != expected_build_keys:
        raise CompatibilityBlocked("native_build_identity_incomplete", sorted(build))
    if (
        build["baseline_policy_id"]
        != "sts_lightspeed_simple_agent_no_potions_v1"
        or build["native_target_policy_id"]
        != "sts_lightspeed_simple_agent_target_v1"
        or build["cpp_standard"] != 201703
        or build["python"] != sys.version.split()[0]
    ):
        raise CompatibilityBlocked("native_build_identity_mismatch", build)
    for field, length in (
        ("adapter_commit", 40),
        ("adapter_source_sha256", 64),
        ("module_sha256", 64),
        ("simulator_commit", 40),
        ("simulator_source_sha256", 64),
    ):
        if not _is_hex(provenance.get(field), length):
            raise CompatibilityBlocked("native_provenance_hash_invalid", field)
    module_size = provenance.get("module_size_bytes")
    source_count = provenance.get("simulator_source_file_count")
    if (
        isinstance(module_size, bool)
        or not isinstance(module_size, int)
        or module_size <= 0
        or isinstance(source_count, bool)
        or not isinstance(source_count, int)
        or source_count <= 0
        or not isinstance(provenance.get("simulator_dirty"), bool)
    ):
        raise CompatibilityBlocked("native_provenance_physical_identity_invalid")
    identity["adapter_provenance"] = copy.deepcopy(dict(provenance))
    submodules = _mapping(provenance.get("submodules"), "native submodules")
    if set(submodules) != {"json", "pybind11"} or any(
        not _is_hex(commit, 40) for commit in submodules.values()
    ):
        raise CompatibilityBlocked("native_submodule_identity_invalid")
    if identity["adapter_source_files"] != list(ADAPTER_SOURCE_FILES):
        raise CompatibilityBlocked("adapter_source_files_mismatch")

    expected_contract = event_option_semantics_identity()
    if identity["contract"] != expected_contract:
        raise CompatibilityBlocked("event_contract_identity_mismatch")
    if (
        provenance["simulator_commit"] != expected_contract["simulator_commit"]
        or provenance["simulator_source_sha256"]
        != expected_contract["simulator_source_sha256"]
    ):
        raise CompatibilityBlocked(
            "native_simulator_contract_mismatch",
            {
                "actual_commit": provenance["simulator_commit"],
                "actual_source_sha256": provenance["simulator_source_sha256"],
                "expected_commit": expected_contract["simulator_commit"],
                "expected_source_sha256": expected_contract[
                    "simulator_source_sha256"
                ],
            },
        )
    contract_file = _validate_binding(
        identity["contract_file"], "identity.contract_file", repository_relative=True
    )
    contract_identity = expected_contract["observation_contract"]
    if (
        contract_file["path"] != contract_identity["path"]
        or contract_file["sha256"] != contract_identity["sha256"]
    ):
        raise CompatibilityBlocked("event_contract_binding_mismatch")
    identity["contract_file"] = contract_file

    implementation = _mapping(identity["implementation"], "identity.implementation")
    _require_keys(
        implementation,
        {"commit", "source_files", "source_sha256"},
        "identity.implementation",
    )
    if not _is_hex(implementation["commit"], 40):
        raise CompatibilityBlocked("implementation_commit_invalid")
    if implementation["source_files"] != list(IMPLEMENTATION_SOURCE_FILES):
        raise CompatibilityBlocked("implementation_source_files_mismatch")
    if not _is_hex(implementation["source_sha256"], 64):
        raise CompatibilityBlocked("implementation_source_hash_invalid")
    identity["implementation"] = implementation
    identity["metadata"] = _validate_binding(
        identity["metadata"], "identity.metadata", repository_relative=False
    )
    identity["module_path"] = _absolute_path(identity["module_path"], "module_path")
    identity["simulator_path"] = _absolute_path(
        identity["simulator_path"], "simulator_path"
    )

    predecessors = _mapping(identity["predecessors"], "identity.predecessors")
    if set(predecessors) != set(PREDECESSOR_PATHS):
        raise CompatibilityBlocked("predecessor_keys_mismatch")
    normalized_predecessors = {}
    for name, expected_path in PREDECESSOR_PATHS.items():
        binding = _validate_binding(
            predecessors[name], f"identity.predecessors.{name}", repository_relative=True
        )
        if binding["path"] != expected_path:
            raise CompatibilityBlocked("predecessor_path_mismatch", name)
        normalized_predecessors[name] = binding
    identity["predecessors"] = normalized_predecessors

    runtime = _mapping(identity["runtime"], "identity.runtime")
    _require_keys(runtime, {"executable", "python"}, "identity.runtime")
    runtime["executable"] = _absolute_path(runtime["executable"], "runtime.executable")
    if not isinstance(runtime["python"], str) or not runtime["python"]:
        raise CompatibilityBlocked("runtime_python_invalid")
    identity["runtime"] = runtime
    identity["seed_ledger"] = _validate_binding(
        identity["seed_ledger"], "identity.seed_ledger", repository_relative=True
    )
    registration["identity"] = identity
    return registration


def load_registration(path: Path | str) -> dict[str, Any]:
    return validate_registration(_load_json(path, "registration"))


def _git_bytes(repo_root: Path, *args: str) -> bytes:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise CompatibilityBlocked("git_identity_failed", list(args)) from exc
    return completed.stdout


def _git_text(repo_root: Path, *args: str) -> str:
    try:
        return _git_bytes(repo_root, *args).decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise CompatibilityBlocked("git_identity_not_utf8", list(args)) from exc


def _assert_clean_pushed_head(repo_root: Path) -> str:
    if _git_bytes(repo_root, "status", "--porcelain=v1", "--untracked-files=no").strip():
        raise CompatibilityBlocked("tracked_tree_not_clean")
    head = _git_text(repo_root, "rev-parse", "HEAD")
    origin = _git_text(repo_root, "rev-parse", "origin/master")
    if not _is_hex(head, 40) or head != origin:
        raise CompatibilityBlocked(
            "head_not_pushed_to_origin_master", {"head": head, "origin_master": origin}
        )
    return head


def assert_pushed_registration(
    *,
    registration_path: Path | str,
    repo_root: Path | str,
    git_reader: Callable[..., bytes] = _git_bytes,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    path = Path(registration_path).resolve()
    try:
        relative = path.relative_to(root).as_posix()
    except ValueError as exc:
        raise CompatibilityBlocked("registration_outside_repository") from exc
    if git_reader(root, "status", "--porcelain=v1", "--untracked-files=no").strip():
        raise CompatibilityBlocked("tracked_tree_not_clean")
    try:
        head = git_reader(root, "rev-parse", "HEAD").decode("utf-8").strip()
        origin = git_reader(root, "rev-parse", "origin/master").decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise CompatibilityBlocked("git_identity_not_utf8") from exc
    if not _is_hex(head, 40) or head != origin:
        raise CompatibilityBlocked(
            "head_not_pushed_to_origin_master", {"head": head, "origin_master": origin}
        )
    committed = git_reader(root, "show", f"HEAD:{relative}")
    if not path.is_file() or path.read_bytes() != committed:
        raise CompatibilityBlocked("registration_blob_mismatch", relative)
    return {
        "preregistration_commit": head,
        "registration_path": relative,
        "registration_sha256": sha256_bytes(committed),
    }


def _verify_binding(
    *, repo_root: Path, binding: Mapping[str, Any], repository_relative: bool
) -> Path:
    path = (
        repo_root / str(binding["path"])
        if repository_relative
        else Path(str(binding["path"]))
    ).resolve()
    if not path.is_file():
        raise CompatibilityBlocked("bound_file_missing", binding["path"])
    if path.stat().st_size != binding["size_bytes"]:
        raise CompatibilityBlocked("bound_file_size_mismatch", binding["path"])
    if sha256_file(path) != binding["sha256"]:
        raise CompatibilityBlocked("bound_file_hash_mismatch", binding["path"])
    return path


def _verify_sources_at_commit(
    repo_root: Path, commit: str, source_files: Sequence[str]
) -> None:
    for relative in source_files:
        committed = _git_bytes(repo_root, "show", f"{commit}:{relative}")
        if committed != (repo_root / relative).read_bytes():
            raise CompatibilityBlocked(
                "source_differs_from_implementation_commit", relative
            )


def validate_registration_evidence(
    registration: Mapping[str, Any], repo_root: Path | str
) -> tuple[dict[str, Any], MetadataCatalog]:
    root = Path(repo_root).resolve()
    normalized = validate_registration(copy.deepcopy(registration))
    identity = normalized["identity"]
    contract_path = _verify_binding(
        repo_root=root,
        binding=identity["contract_file"],
        repository_relative=True,
    )
    expected_contract_path = (
        root / identity["contract"]["observation_contract"]["path"]
    ).resolve()
    if contract_path != expected_contract_path:
        raise CompatibilityBlocked("event_contract_path_mismatch")
    for binding in identity["predecessors"].values():
        _verify_binding(repo_root=root, binding=binding, repository_relative=True)
    metadata_path = _verify_binding(
        repo_root=root, binding=identity["metadata"], repository_relative=False
    )
    ledger_path = _verify_binding(
        repo_root=root, binding=identity["seed_ledger"], repository_relative=True
    )
    registered_ledger = validate_seed_ledger(_load_json(ledger_path, "seed ledger"))
    recomputed_ledger = build_seed_ledger(root)
    if canonical_json_bytes(registered_ledger) != canonical_json_bytes(recomputed_ledger):
        raise CompatibilityBlocked("seed_ledger_recomputation_mismatch")
    implementation = identity["implementation"]
    if hash_bound_files(root, implementation["source_files"]) != implementation[
        "source_sha256"
    ]:
        raise CompatibilityBlocked("implementation_source_hash_mismatch")
    _verify_sources_at_commit(root, implementation["commit"], implementation["source_files"])
    if identity["runtime"] != {
        "executable": str(Path(sys.executable).resolve()),
        "python": sys.version.split()[0],
    }:
        raise CompatibilityBlocked("runtime_identity_mismatch")
    module_path = Path(identity["module_path"])
    provenance = identity["adapter_provenance"]
    if (
        not module_path.is_file()
        or module_path.stat().st_size != provenance["module_size_bytes"]
        or sha256_file(module_path) != provenance["module_sha256"]
    ):
        raise CompatibilityBlocked("native_module_binding_mismatch")
    return registered_ledger, MetadataCatalog(metadata_path)


def collect_native_identity(
    *,
    module_path: Path | str,
    simulator_repo: Path | str,
    repo_root: Path | str,
    native_module: object,
    adapter_commit: str | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    module_file = Path(module_path).resolve()
    simulator = Path(simulator_repo).resolve()
    if not module_file.is_file() or not simulator.is_dir():
        raise CompatibilityBlocked("native_identity_path_missing")
    try:
        build = json.loads(native_module.build_info_json())
    except (AttributeError, TypeError, json.JSONDecodeError) as exc:
        raise CompatibilityBlocked("native_build_info_invalid", str(exc)) from exc
    build["python"] = sys.version.split()[0]
    if build.get("adapter_api_version") != ADAPTER_API_VERSION:
        raise CompatibilityBlocked("native_adapter_api_mismatch")
    source_hash, source_count = hash_compiled_simulator_sources(simulator)
    commit = adapter_commit or _git_text(root, "rev-parse", "HEAD")
    if adapter_commit is not None:
        _verify_sources_at_commit(root, adapter_commit, ADAPTER_SOURCE_FILES)
    identity = {
        "adapter_commit": commit,
        "adapter_source_sha256": hash_bound_files(root, ADAPTER_SOURCE_FILES),
        "build": build,
        "module_sha256": sha256_file(module_file),
        "module_size_bytes": module_file.stat().st_size,
        "simulator_commit": _git_text(simulator, "rev-parse", "HEAD"),
        "simulator_dirty": bool(
            _git_text(simulator, "status", "--porcelain=v1")
        ),
        "simulator_source_file_count": source_count,
        "simulator_source_sha256": source_hash,
        "submodules": {
            "json": _git_text(simulator / "json", "rev-parse", "HEAD"),
            "pybind11": _git_text(simulator / "pybind11", "rev-parse", "HEAD"),
        },
    }
    try:
        return validate_provenance(identity)
    except (TypeError, ValueError) as exc:
        raise CompatibilityBlocked("native_provenance_invalid", str(exc)) from exc


def _failed_result(
    *, reason: str, detail: object | None, rows: list[dict[str, Any]]
) -> dict[str, Any]:
    try:
        canonical_json_bytes({"detail": detail})
        preserved_detail = copy.deepcopy(detail)
    except (TypeError, ValueError):
        preserved_detail = {
            "repr": repr(detail),
            "type": type(detail).__name__,
        }
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
        "seeds": list(COHORT_SEEDS),
        "status": "failed",
        "verdict": "total_event_native_compatibility_failed",
    }


def _event_diagnostic(
    evaluation: Mapping[str, Any],
    candidate: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    expected_source = event_option_semantics_identity()["contract_id"]
    if evaluation.get("event_semantics_source") != expected_source:
        raise CompatibilityBlocked(
            "event_semantics_source_mismatch",
            evaluation.get("event_semantics_source"),
        )
    observation = _mapping(
        evaluation.get("event_observation"), "event observation"
    )
    expected_keys = {
        "current_event_id",
        "current_position",
        "event_data",
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
        if len(decisions) >= MAX_DECISIONS_PER_REPLAY:
            raise CompatibilityBlocked(
                "decision_limit_exceeded",
                {"limit": MAX_DECISIONS_PER_REPLAY, "seed": seed},
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
            raise CompatibilityBlocked(
                "policy_input_hash_mismatch",
                {
                    "actual_candidates": evaluation.get(
                        "input_candidates_sha256"
                    ),
                    "actual_snapshot": evaluation.get("input_snapshot_sha256"),
                    "expected_candidates": expected_candidates_sha256,
                    "expected_snapshot": expected_snapshot_sha256,
                },
            )
        action_id = evaluation.get("action_id")
        matches = [candidate for candidate in candidates if candidate["action_id"] == action_id]
        if len(matches) != 1:
            raise CompatibilityBlocked("selected_action_not_unique_candidate", action_id)
        event_observation = None
        if category == "event":
            event_observation = _event_diagnostic(
                evaluation, matches[0], candidates, snapshot
            )
            event_identities.append(
                {
                    "current_event_id": event_observation["current_event_id"],
                    "current_position": event_observation["current_position"],
                    "simulator_choice_index": event_observation[
                        "simulator_choice_index"
                    ],
                    "upstream_event_id": event_observation["upstream_event_id"],
                }
            )
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
        decision = {
            "action_id": action_id,
            "action_type": evaluation.get("action_type"),
            "candidate_actions_sha256": sha256_bytes(before_candidates),
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
        decisions.append(decision)
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
            for _ in range(REPLAY_COUNT):
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
        missing = [category for category, count in category_counts.items() if count <= 0]
        if missing:
            raise CompatibilityBlocked("aggregate_category_coverage_missing", missing)
        return {
            "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
            "category_counts": category_counts,
            "detail": None,
            "reason": None,
            "rows": rows,
            "schema_version": EXECUTION_SCHEMA_VERSION,
            "seeds": list(COHORT_SEEDS),
            "status": "passed",
            "verdict": "total_event_native_compatibility_passed",
        }
    except KeyboardInterrupt:
        raise
    except CompatibilityBlocked as exc:
        return _failed_result(reason=exc.reason, detail=exc.detail, rows=rows)
    except Exception as exc:
        return _failed_result(
            reason="compatibility_execution_failed",
            detail={"message": str(exc), "type": type(exc).__name__},
            rows=rows,
        )


def _validate_execution_result(value: object) -> dict[str, Any]:
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
    if result["authority"] != ALL_FALSE_AUTHORITY or result["seeds"] != list(
        COHORT_SEEDS
    ):
        raise CompatibilityBlocked("execution_identity_mismatch")
    counts = _mapping(result["category_counts"], "execution category_counts")
    if set(counts) != set(TARGET_CATEGORIES) or any(
        isinstance(count, bool) or not isinstance(count, int) or count < 0
        for count in counts.values()
    ):
        raise CompatibilityBlocked("execution_category_counts_invalid")
    rows = _sequence(result["rows"], "execution rows")
    if len(rows) > len(COHORT_SEEDS):
        raise CompatibilityBlocked("execution_row_count_exceeded")
    normalized_rows = []
    aggregate_counts = Counter()
    for row_index, raw_row in enumerate(rows):
        row = _mapping(raw_row, f"execution rows[{row_index}]")
        _require_keys(
            row,
            {
                "category_counts",
                "decision_count",
                "decisions",
                "event_identities",
                "outcome",
                "replay_count",
                "seed",
                "terminal_floor",
                "trajectory_sha256",
            },
            f"execution rows[{row_index}]",
        )
        if row["seed"] != COHORT_SEEDS[row_index] or row["replay_count"] != REPLAY_COUNT:
            raise CompatibilityBlocked("execution_row_identity_mismatch", row_index)
        decisions = _sequence(row["decisions"], f"execution row {row_index} decisions")
        if row["decision_count"] != len(decisions):
            raise CompatibilityBlocked(
                "execution_row_decision_count_mismatch", row_index
            )
        row_counts = Counter()
        expected_event_identities = []
        previous_decision_index: int | None = None
        for decision_index, raw_decision in enumerate(decisions):
            decision = _mapping(
                raw_decision, f"execution row {row_index} decision {decision_index}"
            )
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
                "execution decision",
            )
            if decision["category"] not in TARGET_CATEGORIES:
                raise CompatibilityBlocked("execution_decision_category_invalid")
            if (
                not isinstance(decision["action_id"], str)
                or not decision["action_id"]
                or not isinstance(decision["action_type"], str)
                or not decision["action_type"]
                or isinstance(decision["decision_index"], bool)
                or not isinstance(decision["decision_index"], int)
                or decision["decision_index"] < 0
                or (
                    previous_decision_index is not None
                    and decision["decision_index"] <= previous_decision_index
                )
            ):
                raise CompatibilityBlocked("execution_decision_identity_invalid")
            previous_decision_index = decision["decision_index"]
            for field in (
                "candidate_actions_sha256",
                "policy_input_sha256",
                "source_snapshot_sha256",
            ):
                if not _is_hex(decision[field], 64):
                    raise CompatibilityBlocked("execution_decision_hash_invalid", field)
            if decision["category"] == "event":
                observation = _mapping(
                    decision["event_observation"], "preserved event observation"
                )
                _require_keys(
                    observation,
                    {
                        "current_event_id",
                        "current_position",
                        "event_data",
                        "semantics_source",
                        "simulator_choice_index",
                        "upstream_event_id",
                    },
                    "preserved event observation",
                )
                if (
                    observation.get("semantics_source")
                    != event_option_semantics_identity()["contract_id"]
                    or not isinstance(observation.get("current_event_id"), str)
                    or not observation["current_event_id"]
                    or not isinstance(observation.get("upstream_event_id"), str)
                    or not observation["upstream_event_id"]
                    or isinstance(observation.get("current_position"), bool)
                    or not isinstance(observation.get("current_position"), int)
                    or observation["current_position"] < 0
                    or isinstance(observation.get("simulator_choice_index"), bool)
                    or not isinstance(observation.get("simulator_choice_index"), int)
                    or observation["simulator_choice_index"] < 0
                ):
                    raise CompatibilityBlocked(
                        "preserved_event_observation_invalid"
                    )
                expected_event_identities.append(
                    {
                        "current_event_id": observation["current_event_id"],
                        "current_position": observation["current_position"],
                        "simulator_choice_index": observation[
                            "simulator_choice_index"
                        ],
                        "upstream_event_id": observation["upstream_event_id"],
                    }
                )
            elif decision["event_observation"] is not None:
                raise CompatibilityBlocked("unexpected_event_observation")
            row_counts[decision["category"]] += 1
        expected_row_counts = {
            category: row_counts[category] for category in TARGET_CATEGORIES
        }
        if row["category_counts"] != expected_row_counts:
            raise CompatibilityBlocked("execution_row_category_counts_mismatch")
        if row["event_identities"] != expected_event_identities:
            raise CompatibilityBlocked("execution_row_event_identities_mismatch")
        if (
            isinstance(row["terminal_floor"], bool)
            or not isinstance(row["terminal_floor"], int)
            or row["outcome"] not in {"player_loss", "player_victory"}
        ):
            raise CompatibilityBlocked("execution_row_terminal_invalid")
        hash_input = copy.deepcopy(row)
        registered_hash = hash_input.pop("trajectory_sha256")
        hash_input.pop("replay_count")
        if registered_hash != sha256_bytes(canonical_json_bytes(hash_input)):
            raise CompatibilityBlocked("execution_row_trajectory_hash_mismatch")
        aggregate_counts.update(expected_row_counts)
        normalized_rows.append(row)
    if counts != {
        category: aggregate_counts[category] for category in TARGET_CATEGORIES
    }:
        raise CompatibilityBlocked("execution_aggregate_counts_mismatch")
    if result["status"] == "passed":
        if (
            result["verdict"] != "total_event_native_compatibility_passed"
            or result["reason"] is not None
            or result["detail"] is not None
            or len(rows) != len(COHORT_SEEDS)
            or any(count <= 0 for count in counts.values())
        ):
            raise CompatibilityBlocked("passed_execution_contract_invalid")
    elif result["status"] == "failed":
        if (
            result["verdict"] != "total_event_native_compatibility_failed"
            or not isinstance(result["reason"], str)
            or not result["reason"]
        ):
            raise CompatibilityBlocked("failed_execution_contract_invalid")
    else:
        raise CompatibilityBlocked("execution_status_invalid")
    result["category_counts"] = counts
    result["rows"] = normalized_rows
    return result


def _report_markdown(result: Mapping[str, Any]) -> bytes:
    lines = [
        "# API v3 Total Event Native Compatibility",
        "",
        "## Verdict",
        "",
        f"`{result['verdict']}`",
        "",
        "## Structural Evidence",
        "",
        f"- Registered seeds: `{COHORT_SEEDS[0]}..{COHORT_SEEDS[-1]}`.",
        f"- Replays per seed: `{REPLAY_COUNT}`.",
        f"- Completed deterministic seed rows: `{len(result['rows'])}`.",
    ]
    for category in TARGET_CATEGORIES:
        lines.append(
            f"- {category} decisions: `{result['category_counts'][category]}`."
        )
    if result["status"] == "failed":
        lines.extend(
            [
                "",
                "## First Blocker",
                "",
                f"- Reason: `{result['reason']}`.",
                f"- Detail: `{json.dumps(result['detail'], sort_keys=True)}`.",
            ]
        )
    lines.extend(
        [
            "",
            "## Authority",
            "",
            "This result is structural only. Gameplay, baseline-floor, outcome, reward,",
            "model, OPE, formal-RL, training, qualification, loading, and promotion",
            "authority remain false.",
            "",
        ]
    )
    return "\n".join(lines).encode("utf-8")


def _deterministic_artifacts(
    *,
    registration: Mapping[str, Any],
    registration_sha256: str,
    preregistration_commit: str,
    result: Mapping[str, Any],
) -> dict[str, bytes]:
    normalized_registration = validate_registration(copy.deepcopy(registration))
    normalized_result = _validate_execution_result(copy.deepcopy(result))
    configuration = {
        "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
        "cohort": copy.deepcopy(normalized_registration["cohort"]),
        "identity": copy.deepcopy(normalized_registration["identity"]),
        "limits": copy.deepcopy(normalized_registration["limits"]),
        "preregistration_commit": preregistration_commit,
        "registration_sha256": registration_sha256,
        "schema_version": CONFIGURATION_SCHEMA_VERSION,
    }
    metrics = {
        "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
        "category_counts": copy.deepcopy(normalized_result["category_counts"]),
        "completed_seed_count": len(normalized_result["rows"]),
        "detail": copy.deepcopy(normalized_result["detail"]),
        "reason": normalized_result["reason"],
        "registration_sha256": registration_sha256,
        "schema_version": METRICS_SCHEMA_VERSION,
        "status": normalized_result["status"],
        "verdict": normalized_result["verdict"],
    }
    trajectories = {
        "execution": copy.deepcopy(normalized_result),
        "schema_version": TRAJECTORY_SCHEMA_VERSION,
    }
    return {
        "configuration.json": canonical_json_bytes(configuration),
        "metrics.json": canonical_json_bytes(metrics),
        "report.md": _report_markdown(normalized_result),
        "trajectory_rows.json": canonical_json_bytes(trajectories),
    }


def _artifact_binding(name: str, payload: bytes) -> dict[str, Any]:
    return {"path": name, "sha256": sha256_bytes(payload), "size_bytes": len(payload)}


def _build_manifest(
    *, registration_sha256: str, result: Mapping[str, Any], payloads: Mapping[str, bytes]
) -> bytes:
    expected_names = set(CANONICAL_ARTIFACT_NAMES) - {"artifact_manifest.json"}
    if set(payloads) != expected_names:
        raise CompatibilityBlocked("artifact_inventory_mismatch")
    manifest = {
        "artifact_bindings": {
            name: _artifact_binding(name, payloads[name]) for name in sorted(payloads)
        },
        "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
        "registration_sha256": registration_sha256,
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "verdict": result["verdict"],
    }
    return canonical_json_bytes(manifest)


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(payload)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _publish_result_artifacts(
    *,
    output_dir: Path,
    registration: Mapping[str, Any],
    registration_sha256: str,
    preregistration_commit: str,
    result: Mapping[str, Any],
) -> None:
    journal_path = output_dir / "execution_journal.json"
    if not journal_path.is_file():
        raise CompatibilityBlocked("execution_journal_missing")
    payloads = _deterministic_artifacts(
        registration=registration,
        registration_sha256=registration_sha256,
        preregistration_commit=preregistration_commit,
        result=result,
    )
    payloads["execution_journal.json"] = journal_path.read_bytes()
    allowed_existing = {"execution_journal.json"}
    existing = {path.name for path in output_dir.iterdir()}
    if existing != allowed_existing:
        raise CompatibilityBlocked("output_inventory_before_publication_invalid", sorted(existing))
    for name in sorted(payloads):
        if name == "execution_journal.json":
            continue
        _write_atomic(output_dir / name, payloads[name])
    manifest = _build_manifest(
        registration_sha256=registration_sha256, result=result, payloads=payloads
    )
    _write_atomic(output_dir / "artifact_manifest.json", manifest)


def consume_and_run(
    *,
    registration: Mapping[str, Any],
    registration_sha256: str,
    preregistration_commit: str,
    output_dir: Path | str,
    environment_factory: Callable[[int], Any],
    session_factory: Callable[[], Any],
    utc_now: Callable[[], str],
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    normalized = validate_registration(copy.deepcopy(registration))
    root = Path(output_dir)
    journal_path = root / "execution_journal.json"
    if journal_path.exists():
        raise CompatibilityBlocked("cohort_already_consumed", str(journal_path))
    if root.exists() and any(root.iterdir()):
        raise CompatibilityBlocked("output_directory_not_empty", str(root))
    started_at = utc_now()
    started_monotonic = monotonic()
    started = {
        "canonical": False,
        "cohort_consumed": True,
        "preregistration_commit": preregistration_commit,
        "registration_sha256": registration_sha256,
        "schema_version": JOURNAL_SCHEMA_VERSION,
        "seeds": list(COHORT_SEEDS),
        "started_at_utc": started_at,
        "status": "started",
    }
    _write_atomic(journal_path, canonical_json_bytes(started))
    result = run_compatibility_cohort(
        registration=normalized,
        environment_factory=environment_factory,
        session_factory=session_factory,
        monotonic=monotonic,
    )
    finalized = {
        **started,
        "completed_at_utc": utc_now(),
        "elapsed_seconds": max(0.0, monotonic() - started_monotonic),
        "result_sha256": sha256_bytes(canonical_json_bytes(result)),
        "status": "finalized",
        "verdict": result["verdict"],
    }
    _write_atomic(journal_path, canonical_json_bytes(finalized))
    _publish_result_artifacts(
        output_dir=root,
        registration=normalized,
        registration_sha256=registration_sha256,
        preregistration_commit=preregistration_commit,
        result=result,
    )
    return result


def verify_artifact_directory(
    *, output_dir: Path | str, registration_path: Path | str
) -> dict[str, Any]:
    root = Path(output_dir)
    registration_file = Path(registration_path)
    registration = load_registration(registration_file)
    registration_sha256 = sha256_file(registration_file)
    try:
        inventory = {path.name for path in root.iterdir()}
    except OSError as exc:
        raise CompatibilityBlocked("cannot_inspect_artifact_directory", str(exc)) from exc
    if inventory != set(CANONICAL_ARTIFACT_NAMES):
        raise CompatibilityBlocked("published_artifact_inventory_mismatch", sorted(inventory))
    manifest = _load_json(root / "artifact_manifest.json", "artifact manifest")
    _require_keys(
        manifest,
        {
            "artifact_bindings",
            "authority",
            "registration_sha256",
            "schema_version",
            "verdict",
        },
        "artifact manifest",
    )
    if manifest["schema_version"] != MANIFEST_SCHEMA_VERSION:
        raise CompatibilityBlocked("manifest_schema_mismatch")
    if manifest["authority"] != ALL_FALSE_AUTHORITY:
        raise CompatibilityBlocked("manifest_authority_mismatch")
    if manifest["registration_sha256"] != registration_sha256:
        raise CompatibilityBlocked("manifest_registration_mismatch")
    bindings = _mapping(manifest["artifact_bindings"], "manifest artifact_bindings")
    expected_names = set(CANONICAL_ARTIFACT_NAMES) - {"artifact_manifest.json"}
    if set(bindings) != expected_names:
        raise CompatibilityBlocked("manifest_artifact_inventory_mismatch")
    payloads = {}
    for name in sorted(expected_names):
        binding = _validate_binding(
            bindings[name], f"artifact binding {name}", repository_relative=True
        )
        if binding["path"] != name:
            raise CompatibilityBlocked("artifact_binding_path_mismatch", name)
        payload = (root / name).read_bytes()
        if len(payload) != binding["size_bytes"] or sha256_bytes(payload) != binding[
            "sha256"
        ]:
            raise CompatibilityBlocked("artifact_hash_mismatch", name)
        payloads[name] = payload
    journal = _load_json(root / "execution_journal.json", "execution journal")
    _require_keys(
        journal,
        {
            "canonical",
            "cohort_consumed",
            "completed_at_utc",
            "elapsed_seconds",
            "preregistration_commit",
            "registration_sha256",
            "result_sha256",
            "schema_version",
            "seeds",
            "started_at_utc",
            "status",
            "verdict",
        },
        "execution journal",
    )
    if (
        journal.get("schema_version") != JOURNAL_SCHEMA_VERSION
        or journal.get("status") != "finalized"
        or journal.get("canonical") is not False
        or journal.get("cohort_consumed") is not True
        or journal.get("registration_sha256") != registration_sha256
        or journal.get("seeds") != list(COHORT_SEEDS)
        or not _is_hex(journal.get("preregistration_commit"), 40)
        or not _is_hex(journal.get("result_sha256"), 64)
        or not isinstance(journal.get("started_at_utc"), str)
        or not journal["started_at_utc"]
        or not isinstance(journal.get("completed_at_utc"), str)
        or not journal["completed_at_utc"]
        or isinstance(journal.get("elapsed_seconds"), bool)
        or not isinstance(journal.get("elapsed_seconds"), (int, float))
        or journal["elapsed_seconds"] < 0
    ):
        raise CompatibilityBlocked("execution_journal_contract_mismatch")
    trajectories = _load_json(root / "trajectory_rows.json", "trajectory rows")
    if trajectories.get("schema_version") != TRAJECTORY_SCHEMA_VERSION:
        raise CompatibilityBlocked("trajectory_schema_mismatch")
    result = _validate_execution_result(trajectories.get("execution"))
    expected_payloads = _deterministic_artifacts(
        registration=registration,
        registration_sha256=registration_sha256,
        preregistration_commit=journal["preregistration_commit"],
        result=result,
    )
    for name, expected in expected_payloads.items():
        if payloads[name] != expected:
            raise CompatibilityBlocked("artifact_recomputation_mismatch", name)
    expected_manifest = _build_manifest(
        registration_sha256=registration_sha256,
        result=result,
        payloads=payloads,
    )
    if (root / "artifact_manifest.json").read_bytes() != expected_manifest:
        raise CompatibilityBlocked("manifest_recomputation_mismatch")
    if journal.get("result_sha256") != sha256_bytes(canonical_json_bytes(result)):
        raise CompatibilityBlocked("journal_result_hash_mismatch")
    if manifest["verdict"] != result["verdict"]:
        raise CompatibilityBlocked("manifest_verdict_mismatch")
    return manifest


def _prepare_registration(
    *,
    repo_root: Path,
    module_path: Path,
    simulator_repo: Path,
    metadata_path: Path,
    dll_directories: Sequence[Path],
) -> dict[str, Any]:
    implementation_commit = _assert_clean_pushed_head(repo_root)
    registration_path = repo_root / DEFAULT_REGISTRATION_PATH
    ledger_path = repo_root / DEFAULT_SEED_LEDGER_PATH
    if registration_path.exists() or ledger_path.exists():
        raise CompatibilityBlocked("registration_or_ledger_already_exists")
    try:
        native_module = load_native_module(
            module_path, dll_directories=dll_directories
        )
    except SimulatorAdapterError as exc:
        raise CompatibilityBlocked("native_module_load_failed", str(exc)) from exc
    provenance = collect_native_identity(
        module_path=module_path,
        simulator_repo=simulator_repo,
        repo_root=repo_root,
        native_module=native_module,
        adapter_commit=implementation_commit,
    )
    ledger = build_seed_ledger(repo_root)
    _write_atomic(ledger_path, canonical_json_bytes(ledger))
    contract = event_option_semantics_identity()
    contract_relative = contract["observation_contract"]["path"]
    identity = {
        "adapter_provenance": provenance,
        "adapter_source_files": list(ADAPTER_SOURCE_FILES),
        "contract": contract,
        "contract_file": _file_binding(
            repo_root / contract_relative, contract_relative
        ),
        "implementation": {
            "commit": implementation_commit,
            "source_files": list(IMPLEMENTATION_SOURCE_FILES),
            "source_sha256": hash_bound_files(
                repo_root, IMPLEMENTATION_SOURCE_FILES
            ),
        },
        "metadata": _file_binding(metadata_path.resolve(), str(metadata_path.resolve())),
        "module_path": str(module_path.resolve()),
        "predecessors": {
            name: _file_binding(repo_root / relative, relative)
            for name, relative in PREDECESSOR_PATHS.items()
        },
        "runtime": {
            "executable": str(Path(sys.executable).resolve()),
            "python": sys.version.split()[0],
        },
        "seed_ledger": _file_binding(ledger_path, DEFAULT_SEED_LEDGER_PATH),
        "simulator_path": str(simulator_repo.resolve()),
    }
    registration = build_registration(identity=identity)
    _write_atomic(registration_path, canonical_json_bytes(registration))
    validate_registration_evidence(registration, repo_root)
    return {
        "implementation_commit": implementation_commit,
        "registration_path": DEFAULT_REGISTRATION_PATH,
        "registration_sha256": sha256_file(registration_path),
        "seed_ledger_path": DEFAULT_SEED_LEDGER_PATH,
        "seed_ledger_sha256": sha256_file(ledger_path),
    }


def _execute_registered(
    *, repo_root: Path, dll_directories: Sequence[Path]
) -> dict[str, Any]:
    registration_path = repo_root / DEFAULT_REGISTRATION_PATH
    pushed = assert_pushed_registration(
        registration_path=registration_path, repo_root=repo_root
    )
    registration = load_registration(registration_path)
    _, metadata = validate_registration_evidence(registration, repo_root)
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
        repo_root=repo_root,
        native_module=native_module,
        adapter_commit=identity["adapter_provenance"]["adapter_commit"],
    )
    if actual_provenance != identity["adapter_provenance"]:
        mismatches = sorted(
            key
            for key in set(actual_provenance) | set(identity["adapter_provenance"])
            if actual_provenance.get(key) != identity["adapter_provenance"].get(key)
        )
        raise CompatibilityBlocked("native_identity_mismatch", mismatches)
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
            event_semantics_identity=event_option_semantics_identity(),
            simulator_provenance=provenance,
        )

    output_dir = repo_root / registration["output"]["directory"]
    result = consume_and_run(
        registration=registration,
        registration_sha256=pushed["registration_sha256"],
        preregistration_commit=pushed["preregistration_commit"],
        output_dir=output_dir,
        environment_factory=environment_factory,
        session_factory=session_factory,
        utc_now=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )
    verify_artifact_directory(
        output_dir=output_dir, registration_path=registration_path
    )
    return {
        "output_directory": registration["output"]["directory"],
        "status": result["status"],
        "verdict": result["verdict"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    register = commands.add_parser(
        "register", description="Bind an API v3 module without constructing Environment."
    )
    register.add_argument("--repo-root", type=Path, default=_REPO_ROOT)
    register.add_argument("--module", type=Path, required=True)
    register.add_argument("--simulator-repo", type=Path, required=True)
    register.add_argument("--metadata", type=Path, required=True)
    register.add_argument("--dll-directory", type=Path, action="append", default=[])
    execute = commands.add_parser(
        "execute", description="Consume and run the exact pushed cohort once."
    )
    execute.add_argument("--repo-root", type=Path, default=_REPO_ROOT)
    execute.add_argument("--dll-directory", type=Path, action="append", default=[])
    verify = commands.add_parser(
        "verify", description="Recompute preserved artifacts without native execution."
    )
    verify.add_argument("--repo-root", type=Path, default=_REPO_ROOT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        root = args.repo_root.resolve()
        if args.command == "register":
            result = _prepare_registration(
                repo_root=root,
                module_path=args.module.resolve(),
                simulator_repo=args.simulator_repo.resolve(),
                metadata_path=args.metadata.resolve(),
                dll_directories=args.dll_directory,
            )
        elif args.command == "execute":
            result = _execute_registered(
                repo_root=root, dll_directories=args.dll_directory
            )
        else:
            registration_path = root / DEFAULT_REGISTRATION_PATH
            output_dir = root / DEFAULT_OUTPUT_DIRECTORY
            manifest = verify_artifact_directory(
                output_dir=output_dir, registration_path=registration_path
            )
            result = {"verdict": manifest["verdict"]}
    except CompatibilityBlocked as exc:
        print(json.dumps({"detail": exc.detail, "reason": exc.reason}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
