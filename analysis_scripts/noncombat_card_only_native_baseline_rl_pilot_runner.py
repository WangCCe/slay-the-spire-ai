"""One-shot runner for the card-only native-baseline RL pilot."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import types
from collections.abc import Callable, Mapping, Sequence
from typing import Any


def _bootstrap_direct_script_imports() -> None:
    if __package__:
        return
    repo_root = Path(__file__).resolve().parents[1]
    package_root = repo_root / "analysis_scripts"
    package = types.ModuleType("analysis_scripts")
    package.__file__ = str(package_root / "__init__.py")
    package.__package__ = "analysis_scripts"
    package.__path__ = [str(package_root)]
    package.__spec__ = importlib.util.spec_from_loader(
        "analysis_scripts", loader=None, is_package=True
    )
    sys.modules["analysis_scripts"] = package
    sys.path.append(str(repo_root))


if __name__ == "__main__":
    _bootstrap_direct_script_imports()


from analysis_scripts.bottled_policy_oracle import BottledPolicyOracle
from analysis_scripts import noncombat_card_acceptance_empirical_successor_runtime as runtime
from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot as pilot
from analysis_scripts import noncombat_simulator_adapter as adapter


REGISTRATION_SCHEMA_VERSION = "noncombat-card-only-native-baseline-pilot-registration-v1"
RESUME_REGISTRATION_SCHEMA_VERSION = (
    "noncombat-card-only-native-baseline-pilot-resume-registration-v1"
)
PREFLIGHT_SCHEMA_VERSION = "noncombat-card-only-native-baseline-pilot-preflight-v1"
REPORT_SCHEMA_VERSION = "noncombat-card-only-native-baseline-pilot-report-v1"
TERMINAL_SCHEMA_VERSION = "noncombat-card-only-native-baseline-pilot-terminal-v1"
CONSUMED_DEVELOPMENT_SEEDS = tuple(range(1000, 1032)) + tuple(range(2000, 2032))
MAX_RESIDUAL_CHUNKS = 4
MAX_ENVIRONMENT_ACCESSES = 640
MAX_CHARGED_SECONDS = 28_800.0
DEFAULT_NATIVE_MANIFEST = Path(
    "reports/noncombat_card_acceptance_empirical_successor_20260811_r6_training_launch_manifest.json"
)
DEFAULT_OUTPUT_DIR = Path(
    "reports/noncombat_card_only_native_baseline_rl_pilot_20260813"
)
DEFAULT_BOTTLED_REPO = Path(r"C:\Users\20571\Documents\bottled_ai")
COMMUNICATION_MOD_CONFIG = Path(
    r"C:\Users\20571\AppData\Local\ModTheSpire\CommunicationMod\config.properties"
)
PRODUCTION_CHECKPOINT_ROOT = Path(
    r"D:\SteamLibrary\steamapps\common\SlayTheSpire\checkpoints"
)
BOUND_SOURCE_PATHS = (
    "analysis_scripts/bottled_policy_oracle.py",
    "analysis_scripts/noncombat_card_acceptance_empirical_successor_runtime.py",
    "analysis_scripts/noncombat_card_acceptance_objective.py",
    "analysis_scripts/noncombat_card_acceptance_policy.py",
    "analysis_scripts/noncombat_card_only_native_baseline_rl_pilot.py",
    "analysis_scripts/noncombat_card_only_native_baseline_rl_pilot_runner.py",
    "analysis_scripts/noncombat_simulator_adapter.py",
    "analysis_scripts/noncombat_state_conditioned_policy_input.py",
    "analysis_scripts/offline_decision_comparator.py",
)
FALSE_DOWNSTREAM_AUTHORITY = {
    name: False
    for name in (
        "causal_claim",
        "communication_mod",
        "formal_rl",
        "fresh_evaluation",
        "gameplay",
        "ope",
        "policy_quality",
        "production_model_loading",
        "promotion",
        "qualification",
    )
}
_NATIVE_DEPENDENCY_HANDLES: list[Any] = []
REGISTERED_OPERATIONS = {
    "communication_mod": False,
    "environment_construction": True,
    "evaluation": True,
    "gameplay": False,
    "model_fitting": True,
    "native_loading": True,
    "production_model_loading": False,
    "seed_access": True,
    "training": True,
}


class CardOnlyRunnerBlocked(RuntimeError):
    """Raised when the one-shot runner must fail closed."""


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise CardOnlyRunnerBlocked("artifact is not canonical JSON") from exc


def _read_canonical(path: Path | str) -> dict[str, Any]:
    source = Path(path).resolve()
    try:
        payload = source.read_bytes()
        parsed = json.loads(payload.decode("ascii"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CardOnlyRunnerBlocked(f"invalid canonical JSON: {source}") from exc
    if _canonical_bytes(parsed) != payload or not isinstance(parsed, dict):
        raise CardOnlyRunnerBlocked(f"noncanonical JSON: {source}")
    return parsed


def _reject_duplicate_pairs(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise CardOnlyRunnerBlocked("JSON contains duplicate object keys")
        value[key] = item
    return value


def _reject_json_constant(value: str) -> Any:
    raise CardOnlyRunnerBlocked(f"JSON contains invalid constant: {value}")


def _read_strict_json(path: Path | str) -> dict[str, Any]:
    source = Path(path).resolve()
    try:
        parsed = json.loads(
            source.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_json_constant,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CardOnlyRunnerBlocked(f"invalid JSON: {source}") from exc
    if not isinstance(parsed, dict):
        raise CardOnlyRunnerBlocked(f"JSON root is not an object: {source}")
    return parsed


def _write_canonical(path: Path | str, value: Any) -> dict[str, Any]:
    target = Path(path).resolve()
    payload = _canonical_bytes(value)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    try:
        temporary.write_bytes(payload)
        os.replace(temporary, target)
    except OSError as exc:
        raise CardOnlyRunnerBlocked(f"cannot publish artifact: {target}") from exc
    return {
        "path": target.as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _write_bytes(path: Path | str, payload: bytes) -> dict[str, Any]:
    target = Path(path).resolve()
    if not isinstance(payload, bytes) or not payload:
        raise CardOnlyRunnerBlocked("artifact bytes are invalid")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    try:
        temporary.write_bytes(payload)
        os.replace(temporary, target)
    except OSError as exc:
        raise CardOnlyRunnerBlocked(f"cannot publish artifact: {target}") from exc
    return {
        "path": target.as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _file_binding(path: Path | str) -> dict[str, Any]:
    target = Path(path).resolve()
    if not target.is_file():
        raise CardOnlyRunnerBlocked(f"bound file is missing: {target}")
    digest = hashlib.sha256()
    size = 0
    try:
        with target.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
                size += len(chunk)
    except OSError as exc:
        raise CardOnlyRunnerBlocked(f"bound file cannot be read: {target}") from exc
    return {"path": target.as_posix(), "sha256": digest.hexdigest(), "size_bytes": size}


def _directory_metadata_binding(path: Path | str) -> dict[str, Any]:
    root = Path(path).resolve()
    if not root.is_dir():
        raise CardOnlyRunnerBlocked(f"bound directory is missing: {root}")
    try:
        rows = [
            {
                "mtime_ns": child.stat().st_mtime_ns,
                "path": child.relative_to(root).as_posix(),
                "size_bytes": child.stat().st_size,
            }
            for child in sorted(root.rglob("*"), key=lambda value: value.as_posix())
            if child.is_file()
        ]
    except OSError as exc:
        raise CardOnlyRunnerBlocked(f"bound directory cannot be observed: {root}") from exc
    return {
        "file_count": len(rows),
        "metadata_sha256": hashlib.sha256(_canonical_bytes(rows)).hexdigest(),
        "path": root.as_posix(),
        "size_bytes": sum(row["size_bytes"] for row in rows),
    }


def _git(repo: Path, *arguments: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise CardOnlyRunnerBlocked(f"git observation failed: {repo}") from exc
    return completed.stdout.strip()


def _bottled_identity(repo: Path | str) -> dict[str, Any]:
    root = Path(repo).resolve()
    if not (root / "rs" / "ai" / "requested_strike").is_dir():
        raise CardOnlyRunnerBlocked("Bottled REQUESTED_STRIKE checkout is unavailable")
    dirty = bool(_git(root, "status", "--porcelain=v1"))
    if dirty:
        raise CardOnlyRunnerBlocked("Bottled checkout must be clean")
    commit = _git(root, "rev-parse", "HEAD")
    return {
        "commit": commit,
        "commit_short": commit[:7],
        "dirty": False,
        "path": root.as_posix(),
        "strategy": "REQUESTED_STRIKE",
        "tree": _git(root, "rev-parse", "HEAD^{tree}"),
    }


def _source_bindings(repo_root: Path) -> dict[str, dict[str, Any]]:
    return {
        relative: _file_binding(repo_root / relative)
        for relative in BOUND_SOURCE_PATHS
    }


def _native_identity_from_manifest(path: Path | str) -> dict[str, Any]:
    manifest = _read_strict_json(path)
    native = manifest.get("native_identity")
    if not isinstance(native, dict):
        raise CardOnlyRunnerBlocked("native manifest identity is invalid")
    required = {"adapter_api_version", "dependency_closure", "dll_directories", "module", "provenance", "provenance_sha256"}
    if set(native) != required or native["adapter_api_version"] != adapter.ADAPTER_API_VERSION:
        raise CardOnlyRunnerBlocked("native manifest contract differs")
    return copy.deepcopy(native)


def build_registration(
    *,
    repo_root: Path | str,
    source_commit: str,
    native_manifest_path: Path | str,
    bottled_repo: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    if _git(root, "cat-file", "-t", source_commit) != "commit":
        raise CardOnlyRunnerBlocked("registered source commit is unavailable")
    corpus_path = (root / pilot.BOUND_CORPUS_PATH).resolve()
    corpus = _file_binding(corpus_path)
    if corpus != {
        "path": corpus_path.as_posix(),
        "sha256": pilot.BOUND_CORPUS_SHA256,
        "size_bytes": pilot.BOUND_CORPUS_SIZE_BYTES,
    }:
        raise CardOnlyRunnerBlocked("bound card corpus differs")
    output = Path(output_dir).resolve()
    checkpoint_root = PRODUCTION_CHECKPOINT_ROOT.resolve()
    if output == checkpoint_root or checkpoint_root in output.parents:
        raise CardOnlyRunnerBlocked("pilot output overlaps production checkpoints")
    native_manifest = Path(native_manifest_path).resolve()
    return validate_registration(
        {
            "bottled": _bottled_identity(bottled_repo),
            "configuration": {
                "comparison": "one-frozen-candidate-vs-native-control-v1",
                "maximum_charged_seconds": MAX_CHARGED_SECONDS,
                "maximum_environment_accesses": MAX_ENVIRONMENT_ACCESSES,
                "maximum_residual_chunks": MAX_RESIDUAL_CHUNKS,
                "residual_chunk_pairs": 64,
                "warm_start": pilot.card_warm_start_configuration(),
            },
            "corpus": {
                **corpus,
                "allowed_cohorts": list(pilot.ALLOWED_CORPUS_COHORTS),
                "card_row_counts": dict(pilot.BOUND_CARD_ROW_COUNTS),
                "registration_sha256": pilot.BOUND_REGISTRATION_SHA256,
            },
            "downstream_authority": dict(FALSE_DOWNSTREAM_AUTHORITY),
            "native": {
                "identity": _native_identity_from_manifest(native_manifest),
                "manifest": _file_binding(native_manifest),
            },
            "operations": dict(REGISTERED_OPERATIONS),
            "output_dir": output.as_posix(),
            "production_isolation": {
                "communication_mod_config": _file_binding(COMMUNICATION_MOD_CONFIG),
                "production_checkpoints": _directory_metadata_binding(checkpoint_root),
            },
            "schedule": {
                "comparison_seeds": list(CONSUMED_DEVELOPMENT_SEEDS),
                "residual_chunk_seeds": [
                    list(CONSUMED_DEVELOPMENT_SEEDS)
                    for _ in range(MAX_RESIDUAL_CHUNKS)
                ],
                "seed_status": "already-consumed-development-only",
            },
            "schema_version": REGISTRATION_SCHEMA_VERSION,
            "source": {
                "bindings": _source_bindings(root),
                "commit": source_commit,
                "repo_root": root.as_posix(),
            },
        }
    )


def build_resume_registration(
    *,
    repo_root: Path | str,
    source_commit: str,
    native_manifest_path: Path | str,
    bottled_repo: Path | str,
    output_dir: Path | str,
    resume_output_dir: Path | str,
) -> dict[str, Any]:
    registration = build_registration(
        repo_root=repo_root,
        source_commit=source_commit,
        native_manifest_path=native_manifest_path,
        bottled_repo=bottled_repo,
        output_dir=output_dir,
    )
    resume_root = Path(resume_output_dir).resolve()
    required = {
        name: _file_binding(resume_root / name)
        for name in (
            "checkpoint_000.json",
            "preflight.json",
            "registration.json",
            "report.json",
            "terminal.json",
            "warm_start.json",
            "warm_start_checkpoint.json",
        )
    }
    terminal = _read_canonical(resume_root / "terminal.json")
    if terminal != {
        "downstream_authority": FALSE_DOWNSTREAM_AUTHORITY,
        "environment_accesses": 0,
        "optimizer_steps": 1280,
        "rollback": "native_simple_agent",
        "schema_version": TERMINAL_SCHEMA_VERSION,
        "stop_reason": "native_load_failure_before_environment_access",
        "verdict": "card_only_native_baseline_pilot_not_ready",
        "warm_start_gate": "card_warm_start_gate_passed",
    }:
        raise CardOnlyRunnerBlocked("resume source terminal differs")
    registration["resume_from"] = {
        "artifacts": required,
        "environment_accesses": 0,
        "output_dir": resume_root.as_posix(),
        "stop_reason": "native_load_failure_before_environment_access",
    }
    registration["schema_version"] = RESUME_REGISTRATION_SCHEMA_VERSION
    return validate_registration(registration)


def validate_registration(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise CardOnlyRunnerBlocked("registration must be an object")
    registration = copy.deepcopy(dict(value))
    base_fields = {
        "bottled", "configuration", "corpus", "downstream_authority", "native",
        "operations", "output_dir", "production_isolation", "schedule",
        "schema_version", "source",
    }
    schema_version = registration.get("schema_version")
    expected_fields = (
        base_fields | {"resume_from"}
        if schema_version == RESUME_REGISTRATION_SCHEMA_VERSION
        else base_fields
    )
    if set(registration) != expected_fields or schema_version not in {
        REGISTRATION_SCHEMA_VERSION,
        RESUME_REGISTRATION_SCHEMA_VERSION,
    }:
        raise CardOnlyRunnerBlocked("registration fields differ")
    if registration["downstream_authority"] != FALSE_DOWNSTREAM_AUTHORITY:
        raise CardOnlyRunnerBlocked("registration downstream authority differs")
    configuration = registration.get("configuration")
    if not isinstance(configuration, dict) or configuration != {
        "comparison": "one-frozen-candidate-vs-native-control-v1",
        "maximum_charged_seconds": MAX_CHARGED_SECONDS,
        "maximum_environment_accesses": MAX_ENVIRONMENT_ACCESSES,
        "maximum_residual_chunks": MAX_RESIDUAL_CHUNKS,
        "residual_chunk_pairs": 64,
        "warm_start": pilot.card_warm_start_configuration(),
    }:
        raise CardOnlyRunnerBlocked("registration configuration differs")
    schedule = registration.get("schedule")
    expected_seeds = list(CONSUMED_DEVELOPMENT_SEEDS)
    if not isinstance(schedule, dict) or schedule != {
        "comparison_seeds": expected_seeds,
        "residual_chunk_seeds": [expected_seeds] * MAX_RESIDUAL_CHUNKS,
        "seed_status": "already-consumed-development-only",
    }:
        raise CardOnlyRunnerBlocked("registration schedule differs")
    corpus = registration.get("corpus")
    if not isinstance(corpus, dict) or corpus.get("allowed_cohorts") != list(
        pilot.ALLOWED_CORPUS_COHORTS
    ) or corpus.get("card_row_counts") != pilot.BOUND_CARD_ROW_COUNTS:
        raise CardOnlyRunnerBlocked("registration corpus contract differs")
    if corpus.get("sha256") != pilot.BOUND_CORPUS_SHA256 or corpus.get(
        "size_bytes"
    ) != pilot.BOUND_CORPUS_SIZE_BYTES or corpus.get(
        "registration_sha256"
    ) != pilot.BOUND_REGISTRATION_SHA256:
        raise CardOnlyRunnerBlocked("registration corpus identity differs")
    source = registration.get("source")
    if not isinstance(source, dict) or set(source.get("bindings", {})) != set(
        BOUND_SOURCE_PATHS
    ):
        raise CardOnlyRunnerBlocked("registration source bindings differ")
    if set(source) != {"bindings", "commit", "repo_root"} or not isinstance(
        source.get("repo_root"), str
    ):
        raise CardOnlyRunnerBlocked("registration source identity differs")
    if any(
        not isinstance(binding, dict)
        or set(binding) != {"path", "sha256", "size_bytes"}
        for binding in source["bindings"].values()
    ):
        raise CardOnlyRunnerBlocked("registration source file binding differs")
    if not isinstance(source.get("commit"), str) or len(source["commit"]) != 40:
        raise CardOnlyRunnerBlocked("registration source commit differs")
    bottled = registration.get("bottled")
    if not isinstance(bottled, dict) or bottled.get("dirty") is not False or bottled.get(
        "strategy"
    ) != "REQUESTED_STRIKE":
        raise CardOnlyRunnerBlocked("registration Bottled identity differs")
    native = registration.get("native")
    if not isinstance(native, dict) or set(native) != {"identity", "manifest"}:
        raise CardOnlyRunnerBlocked("registration native identity differs")
    native_identity = native["identity"]
    if not isinstance(native_identity, dict) or set(native_identity) != {
        "adapter_api_version",
        "dependency_closure",
        "dll_directories",
        "module",
        "provenance",
        "provenance_sha256",
    }:
        raise CardOnlyRunnerBlocked("registration native contract differs")
    dependency_closure = native_identity["dependency_closure"]
    if not isinstance(dependency_closure, dict) or not isinstance(
        dependency_closure.get("dependencies"), list
    ):
        raise CardOnlyRunnerBlocked("registration native dependency closure differs")
    native_bindings = [native_identity["module"], *dependency_closure["dependencies"]]
    if any(
        not isinstance(binding, dict)
        or set(binding) != {"path", "sha256", "size_bytes"}
        for binding in native_bindings
    ):
        raise CardOnlyRunnerBlocked("registration native file binding differs")
    operations = registration.get("operations")
    if operations != REGISTERED_OPERATIONS:
        raise CardOnlyRunnerBlocked("registration denied operations differ")
    isolation = registration.get("production_isolation")
    if not isinstance(isolation, dict) or set(isolation) != {
        "communication_mod_config",
        "production_checkpoints",
    }:
        raise CardOnlyRunnerBlocked("registration production isolation differs")
    if not isinstance(registration.get("output_dir"), str):
        raise CardOnlyRunnerBlocked("registration output directory differs")
    if schema_version == RESUME_REGISTRATION_SCHEMA_VERSION:
        resume = registration.get("resume_from")
        expected_artifacts = {
            "checkpoint_000.json",
            "preflight.json",
            "registration.json",
            "report.json",
            "terminal.json",
            "warm_start.json",
            "warm_start_checkpoint.json",
        }
        if (
            not isinstance(resume, dict)
            or set(resume) != {
                "artifacts",
                "environment_accesses",
                "output_dir",
                "stop_reason",
            }
            or set(resume.get("artifacts", {})) != expected_artifacts
            or resume.get("environment_accesses") != 0
            or resume.get("stop_reason")
            != "native_load_failure_before_environment_access"
        ):
            raise CardOnlyRunnerBlocked("resume registration boundary differs")
    return registration


def _forbidden_processes() -> list[dict[str, Any]]:
    command = (
        "Get-CimInstance Win32_Process | "
        "Select-Object Name,ProcessId,CommandLine | ConvertTo-Json -Compress"
    )
    try:
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", command],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        parsed = json.loads(completed.stdout or "[]")
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        raise CardOnlyRunnerBlocked("process preflight is unavailable") from exc
    rows = parsed if isinstance(parsed, list) else [parsed]
    blocked = []
    for row in rows:
        if not isinstance(row, dict):
            raise CardOnlyRunnerBlocked("process preflight row is invalid")
        name = str(row.get("Name") or "").casefold()
        line = str(row.get("CommandLine") or "").casefold()
        if name == "slaythespire.exe" or any(
            marker in line
            for marker in ("modthespire.jar", "communicationmod.jar", "slaythespire.exe")
        ):
            blocked.append(
                {"name": row.get("Name"), "process_id": row.get("ProcessId")}
            )
    return blocked


def _binding_matches(expected: Mapping[str, Any]) -> bool:
    return _file_binding(expected["path"]) == dict(expected)


def preflight_registration(
    registration: Mapping[str, Any],
    *,
    process_observer: Callable[[], Sequence[Mapping[str, Any]]] = _forbidden_processes,
) -> dict[str, Any]:
    value = validate_registration(registration)
    source = value["source"]
    root = Path(source["repo_root"]).resolve()
    if _git(root, "cat-file", "-t", source["commit"]) != "commit":
        raise CardOnlyRunnerBlocked("registered source commit is unavailable")
    try:
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", source["commit"], "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise CardOnlyRunnerBlocked("registered source is not an ancestor of HEAD") from exc
    if any(not _binding_matches(binding) for binding in source["bindings"].values()):
        raise CardOnlyRunnerBlocked("registered execution source differs")
    corpus = value["corpus"]
    if not _binding_matches(
        {key: corpus[key] for key in ("path", "sha256", "size_bytes")}
    ):
        raise CardOnlyRunnerBlocked("registered corpus bytes differ")
    native = value["native"]
    if not _binding_matches(native["manifest"]):
        raise CardOnlyRunnerBlocked("registered native manifest differs")
    observed_native = _native_identity_from_manifest(native["manifest"]["path"])
    if observed_native != native["identity"]:
        raise CardOnlyRunnerBlocked("registered native identity differs")
    native_bindings = [
        native["identity"]["module"],
        *native["identity"]["dependency_closure"]["dependencies"],
    ]
    if any(not _binding_matches(binding) for binding in native_bindings):
        raise CardOnlyRunnerBlocked("registered native bytes differ")
    bottled = value["bottled"]
    if _bottled_identity(bottled["path"]) != bottled:
        raise CardOnlyRunnerBlocked("registered Bottled checkout differs")
    isolation = value["production_isolation"]
    if not _binding_matches(isolation["communication_mod_config"]):
        raise CardOnlyRunnerBlocked("CommunicationMod configuration differs")
    if _directory_metadata_binding(isolation["production_checkpoints"]["path"]) != isolation[
        "production_checkpoints"
    ]:
        raise CardOnlyRunnerBlocked("production checkpoint metadata differs")
    blocked = list(process_observer())
    if blocked:
        raise CardOnlyRunnerBlocked("game or CommunicationMod process is active")
    output = Path(value["output_dir"]).resolve()
    checkpoint_root = Path(isolation["production_checkpoints"]["path"]).resolve()
    if output.exists() or output == checkpoint_root or checkpoint_root in output.parents:
        raise CardOnlyRunnerBlocked("pilot output boundary differs")
    resume = value.get("resume_from")
    if resume is not None:
        if any(
            not _binding_matches(binding)
            for binding in resume["artifacts"].values()
        ):
            raise CardOnlyRunnerBlocked("resume source artifact differs")
        if Path(resume["output_dir"]).resolve() == output:
            raise CardOnlyRunnerBlocked("resume source and destination overlap")
    return {
        "checks": {
            "bottled_clean_and_bound": True,
            "communication_mod_config_bound": True,
            "forbidden_processes_absent": True,
            "native_bytes_bound_without_loading": True,
            "output_outside_production": True,
            "production_checkpoint_metadata_bound": True,
            "source_and_corpus_bound": True,
        },
        "registration_sha256": hashlib.sha256(_canonical_bytes(value)).hexdigest(),
        "schema_version": PREFLIGHT_SCHEMA_VERSION,
        "verdict": "preflight_passed",
    }


def _compact_validation(metrics: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: metrics[key]
        for key in (
            "action_agreement", "action_correct", "family_agreement", "family_correct",
            "non_take_rate", "row_count", "take_rate",
        )
    }


def _publish_report(
    output: Path,
    *,
    preflight: Mapping[str, Any],
    warm_start: Mapping[str, Any] | None,
    chunks: Sequence[Mapping[str, Any]],
    comparison: Mapping[str, Any] | None,
    terminal: Mapping[str, Any],
) -> None:
    _write_canonical(
        output / "report.json",
        {
            "chunks": copy.deepcopy(list(chunks)),
            "comparison": copy.deepcopy(comparison),
            "downstream_authority": dict(FALSE_DOWNSTREAM_AUTHORITY),
            "preflight": copy.deepcopy(dict(preflight)),
            "rollback": "native_simple_agent",
            "schema_version": REPORT_SCHEMA_VERSION,
            "terminal": copy.deepcopy(dict(terminal)),
            "verdict": terminal["verdict"],
            "warm_start": copy.deepcopy(warm_start),
        },
    )


def _chunk_summary(completed: pilot.CompletedCardOnlyResidualChunk) -> dict[str, Any]:
    pairs = completed.episodes
    return {
        "candidate_floor_mean": sum(pair.candidate.floor_progress for pair in pairs) / len(pairs),
        "candidate_victories": sum(pair.candidate.terminal_victory for pair in pairs),
        "chunk_index": completed.chunk_index,
        "control_floor_mean": sum(pair.control.floor_progress for pair in pairs) / len(pairs),
        "control_optimizer_steps": 0,
        "control_victories": sum(pair.control.terminal_victory for pair in pairs),
        "environment_accesses": 128,
        "optimizer_steps": 1,
        "probe": copy.deepcopy(completed.probe),
        "seed_max": completed.seeds[-1],
        "seed_min": completed.seeds[0],
    }


def classify_frozen_comparison(pairs: Sequence[Any]) -> dict[str, Any]:
    source = tuple(pairs)
    if len(source) != 64 or tuple(pair.seed for pair in source) != CONSUMED_DEVELOPMENT_SEEDS:
        raise CardOnlyRunnerBlocked("frozen comparison cohort differs")
    unsupported = sum(
        arm.unsupported_reason is not None
        for pair in source
        for arm in (pair.candidate, pair.control)
    )
    candidate_victories = sum(pair.candidate.terminal_victory for pair in source)
    control_victories = sum(pair.control.terminal_victory for pair in source)
    candidate_floor_mean = sum(pair.candidate.floor_progress for pair in source) / 64
    control_floor_mean = sum(pair.control.floor_progress for pair in source) / 64
    multi_family = [
        decision
        for pair in source
        for decision in pair.candidate.decisions
        if decision.category == "card_reward"
        and decision.diagnostic.get("multi_family") is True
    ]
    take_count = sum(
        decision.diagnostic.get("selected_family") == "take"
        for decision in multi_family
    )
    take_rate = take_count / len(multi_family) if multi_family else None
    checks = {
        "candidate_floor_noninferior": candidate_floor_mean >= control_floor_mean,
        "candidate_victories_noninferior": candidate_victories >= control_victories,
        "candidate_card_coverage": take_rate is not None and 0.05 <= take_rate <= 0.95,
        "supported": unsupported == 0,
    }
    ready = all(checks.values())
    return {
        "candidate": {
            "mean_floor_progress": candidate_floor_mean,
            "victories": candidate_victories,
        },
        "checks": checks,
        "control": {
            "mean_floor_progress": control_floor_mean,
            "victories": control_victories,
        },
        "multi_family_card_decisions": len(multi_family),
        "take_rate": take_rate,
        "unsupported_episodes": unsupported,
        "verdict": (
            "ready_to_propose_fresh_card_only_evaluation"
            if ready
            else "card_only_native_baseline_pilot_not_ready"
        ),
    }


def _load_environment_factory(native_identity: Mapping[str, Any]) -> Callable[[int], Any]:
    _preload_native_dependencies(native_identity)
    module_binding = native_identity["module"]
    try:
        module = adapter.load_native_module(
            module_binding["path"],
            dll_directories=native_identity["dll_directories"],
        )
    except (ImportError, OSError, adapter.SimulatorAdapterError) as exc:
        raise CardOnlyRunnerBlocked("registered native module could not be loaded") from exc
    if Path(module.__file__).resolve().as_posix() != module_binding["path"]:
        raise CardOnlyRunnerBlocked("loaded native module path differs")
    if _file_binding(module.__file__) != module_binding:
        raise CardOnlyRunnerBlocked("loaded native module bytes differ")
    try:
        build = json.loads(module.build_info_json())
    except (AttributeError, TypeError, RuntimeError, json.JSONDecodeError) as exc:
        raise CardOnlyRunnerBlocked("loaded native build is invalid") from exc
    build["python"] = sys.version.split()[0]
    expected_build = copy.deepcopy(native_identity["provenance"]["build"])
    expected_build["python"] = sys.version.split()[0]
    if build != expected_build or module.adapter_api_version() != adapter.ADAPTER_API_VERSION:
        raise CardOnlyRunnerBlocked("loaded native provenance differs")
    provenance = adapter.validate_provenance(native_identity["provenance"])

    def factory(seed: int) -> adapter.NativeSimulatorEnvironment:
        return adapter.NativeSimulatorEnvironment(module.Environment(seed, 0), provenance)

    return factory


def _native_dependency_order(native_identity: Mapping[str, Any]) -> tuple[Path, ...]:
    closure = native_identity["dependency_closure"]
    module_path = Path(native_identity["module"]["path"]).resolve()
    dependencies = {
        Path(binding["path"]).name.casefold(): Path(binding["path"]).resolve()
        for binding in closure["dependencies"]
    }
    imports_by_path = {
        Path(row["path"]).resolve(): tuple(str(name).casefold() for name in row["imports"])
        for row in closure.get("imports", ())
    }
    order: list[Path] = []
    visiting: set[Path] = set()
    visited: set[Path] = set()

    def visit(path: Path) -> None:
        if path in visiting:
            raise CardOnlyRunnerBlocked("registered native dependency cycle differs")
        if path in visited:
            return
        visiting.add(path)
        for name in imports_by_path.get(path, ()):
            dependency = dependencies.get(name)
            if dependency is not None:
                visit(dependency)
        visiting.remove(path)
        visited.add(path)
        if path != module_path:
            order.append(path)

    visit(module_path)
    if set(order) != set(dependencies.values()):
        raise CardOnlyRunnerBlocked("registered native dependency graph differs")
    return tuple(order)


def _preload_native_dependencies(native_identity: Mapping[str, Any]) -> None:
    if os.name != "nt":
        raise CardOnlyRunnerBlocked("native dependency preload requires Windows")
    try:
        import ctypes

        for path in _native_dependency_order(native_identity):
            binding = next(
                item
                for item in native_identity["dependency_closure"]["dependencies"]
                if Path(item["path"]).resolve() == path
            )
            if _file_binding(path) != binding:
                raise CardOnlyRunnerBlocked("registered native dependency bytes differ")
            _NATIVE_DEPENDENCY_HANDLES.append(
                ctypes.WinDLL(str(path), winmode=0x00000100 | 0x00000400)
            )
    except CardOnlyRunnerBlocked:
        raise
    except (ImportError, OSError, StopIteration) as exc:
        raise CardOnlyRunnerBlocked(
            "registered native dependency could not be preloaded"
        ) from exc


def execute_pilot(
    registration: Mapping[str, Any],
    *,
    clock: Callable[[], float] = time.monotonic,
    process_observer: Callable[[], Sequence[Mapping[str, Any]]] = _forbidden_processes,
    environment_factory_loader: Callable[[Mapping[str, Any]], Callable[[int], Any]] = _load_environment_factory,
) -> dict[str, Any]:
    value = validate_registration(registration)
    preflight = preflight_registration(value, process_observer=process_observer)
    output = Path(value["output_dir"]).resolve()
    output.mkdir(parents=False, exist_ok=False)
    _write_canonical(output / "registration.json", value)
    _write_canonical(output / "preflight.json", preflight)
    started = float(clock())
    deadline = started + float(value["configuration"]["maximum_charged_seconds"])
    if not math.isfinite(started):
        raise CardOnlyRunnerBlocked("pilot clock is invalid")

    corpus = pilot.load_bound_card_corpus(
        value["corpus"]["path"], cohorts=pilot.ALLOWED_CORPUS_COHORTS
    )
    oracle = BottledPolicyOracle(Path(value["bottled"]["path"]))
    labels = pilot.label_bound_card_corpus(
        corpus,
        oracle,
        expected_bottled_commit=value["bottled"]["commit_short"],
    )
    resume = value.get("resume_from")
    warm_start = None
    if resume is None:
        warm_start = pilot.run_fixed_card_warm_start(
            runtime.build_matched_bootstrap(), labels
        )
        warm_report = {
            "configuration": warm_start.configuration,
            "final_model_sha256": hashlib.sha256(warm_start.final_model).hexdigest(),
            "final_validation": _compact_validation(warm_start.final_validation),
            "gate": warm_start.gate,
            "label_counts": labels["counts"],
            "optimizer_steps": warm_start.optimizer_steps,
            "zero_model_sha256": hashlib.sha256(warm_start.zero_model).hexdigest(),
            "zero_validation": _compact_validation(warm_start.zero_validation),
        }
        _write_canonical(output / "warm_start.json", warm_report)
        warm_checkpoint = runtime.encode_paired_bootstrap(warm_start.bootstrap)
        _write_bytes(output / "warm_start_checkpoint.json", warm_checkpoint)
    else:
        warm_report = _read_canonical(resume["artifacts"]["warm_start.json"]["path"])
        if warm_report.get("gate", {}).get("verdict") != (
            "card_warm_start_gate_passed"
        ):
            raise CardOnlyRunnerBlocked("resumed warm-start gate differs")
        probe_rows = pilot.project_bottled_card_labels(labels, cohort="validation")
        residual = pilot.restore_card_only_residual_checkpoint(
            Path(resume["artifacts"]["checkpoint_000.json"]["path"]).read_bytes(),
            probe_rows=probe_rows,
        )
        if (
            residual.next_chunk_index != 0
            or residual.environment_accesses != 0
            or residual.candidate_optimizer_steps != 0
            or residual.warm_start_model_sha256
            != warm_report["final_model_sha256"]
        ):
            raise CardOnlyRunnerBlocked("resumed zero-step checkpoint differs")
        _write_canonical(
            output / "resume.json",
            {
                "environment_accesses": 0,
                "source_artifacts": copy.deepcopy(resume["artifacts"]),
                "source_output_dir": resume["output_dir"],
                "stop_reason": resume["stop_reason"],
            },
        )
        _write_bytes(
            output / "checkpoint_000.json",
            pilot.encode_card_only_residual_checkpoint(residual),
        )

    if warm_report["gate"]["verdict"] != "card_warm_start_gate_passed":
        terminal = {
            "downstream_authority": dict(FALSE_DOWNSTREAM_AUTHORITY),
            "environment_accesses": 0,
            "optimizer_steps": warm_report["optimizer_steps"],
            "rollback": "native_simple_agent",
            "schema_version": TERMINAL_SCHEMA_VERSION,
            "verdict": "card_only_native_baseline_pilot_not_ready",
            "warm_start_gate": warm_report["gate"]["verdict"],
        }
        _write_canonical(output / "terminal.json", terminal)
        _publish_report(
            output,
            preflight=preflight,
            warm_start=warm_report,
            chunks=(),
            comparison=None,
            terminal=terminal,
        )
        return terminal

    if resume is None:
        if warm_start is None:
            raise CardOnlyRunnerBlocked("warm-start result is unavailable")
        residual = pilot.initialize_card_only_residual_runtime(warm_start, labels)
        _write_canonical(
            output / "checkpoint_000.json",
            json.loads(pilot.encode_card_only_residual_checkpoint(residual)),
        )
    environment_factory = environment_factory_loader(value["native"]["identity"])
    chunks = []
    for chunk_index, seeds in enumerate(value["schedule"]["residual_chunk_seeds"]):
        completed = pilot.collect_and_complete_card_only_residual_chunk(
            residual,
            environment_factory=environment_factory,
            seeds=seeds,
            chunk_index=chunk_index,
            deadline=deadline,
            clock=clock,
        )
        residual = completed.runtime
        summary = _chunk_summary(completed)
        chunks.append(summary)
        _write_canonical(output / f"chunk_{chunk_index:03d}.json", summary)
        _write_bytes(
            output / f"checkpoint_{chunk_index + 1:03d}.json",
            completed.checkpoint
        )
        if residual.stopped_for_concentration:
            break

    comparison_pairs = []
    for seed in value["schedule"]["comparison_seeds"]:
        if float(clock()) > deadline:
            raise CardOnlyRunnerBlocked("pilot deadline reached before comparison")
        try:
            pair = runtime.rollout_paired_card_only_native_baseline_frozen_evaluation(
                residual.bootstrap,
                environment_factory=environment_factory,
                seed=seed,
                deadline=deadline,
                clock=clock,
            )
        except runtime.SuccessorRuntimeError as exc:
            raise CardOnlyRunnerBlocked(str(exc)) from exc
        comparison_pairs.append(pair)
    comparison = classify_frozen_comparison(comparison_pairs)
    _write_canonical(output / "frozen_comparison.json", comparison)

    isolation = value["production_isolation"]
    if not _binding_matches(isolation["communication_mod_config"]) or (
        _directory_metadata_binding(isolation["production_checkpoints"]["path"])
        != isolation["production_checkpoints"]
    ):
        raise CardOnlyRunnerBlocked("production isolation changed during pilot")
    environment_accesses = residual.environment_accesses + 128
    if environment_accesses > MAX_ENVIRONMENT_ACCESSES:
        raise CardOnlyRunnerBlocked("pilot environment resource bound exceeded")
    terminal = {
        "chunks": chunks,
        "comparison": comparison,
        "downstream_authority": dict(FALSE_DOWNSTREAM_AUTHORITY),
        "environment_accesses": environment_accesses,
        "optimizer_steps": warm_report["optimizer_steps"] + residual.candidate_optimizer_steps,
        "rollback": "native_simple_agent",
        "schema_version": TERMINAL_SCHEMA_VERSION,
        "stopped_for_concentration": residual.stopped_for_concentration,
        "verdict": comparison["verdict"],
        "warm_start_gate": warm_report["gate"]["verdict"],
    }
    _write_canonical(output / "terminal.json", terminal)
    _publish_report(
        output,
        preflight=preflight,
        warm_start=warm_report,
        chunks=chunks,
        comparison=comparison,
        terminal=terminal,
    )
    return terminal


def terminalize_native_load_failure(registration: Mapping[str, Any]) -> dict[str, Any]:
    value = validate_registration(registration)
    if value.get("resume_from") is not None:
        raise CardOnlyRunnerBlocked("resume attempt cannot use initial terminalization")
    output = Path(value["output_dir"]).resolve()
    expected = {
        "checkpoint_000.json",
        "preflight.json",
        "registration.json",
        "warm_start.json",
        "warm_start_checkpoint.json",
    }
    observed = {path.name for path in output.iterdir() if path.is_file()}
    if observed != expected:
        raise CardOnlyRunnerBlocked("failed attempt artifact boundary differs")
    if _read_canonical(output / "registration.json") != value:
        raise CardOnlyRunnerBlocked("failed attempt registration differs")
    warm_report = _read_canonical(output / "warm_start.json")
    if warm_report.get("gate", {}).get("verdict") != (
        "card_warm_start_gate_passed"
    ):
        raise CardOnlyRunnerBlocked("failed attempt warm-start gate differs")
    terminal = {
        "downstream_authority": dict(FALSE_DOWNSTREAM_AUTHORITY),
        "environment_accesses": 0,
        "optimizer_steps": warm_report["optimizer_steps"],
        "rollback": "native_simple_agent",
        "schema_version": TERMINAL_SCHEMA_VERSION,
        "stop_reason": "native_load_failure_before_environment_access",
        "verdict": "card_only_native_baseline_pilot_not_ready",
        "warm_start_gate": warm_report["gate"]["verdict"],
    }
    _write_canonical(output / "terminal.json", terminal)
    _publish_report(
        output,
        preflight=_read_canonical(output / "preflight.json"),
        warm_start=warm_report,
        chunks=(),
        comparison=None,
        terminal=terminal,
    )
    return terminal


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    register = subparsers.add_parser("register")
    register.add_argument("--repo-root", required=True)
    register.add_argument("--source-commit", required=True)
    register.add_argument("--native-manifest", required=True)
    register.add_argument("--bottled-repo", required=True)
    register.add_argument("--output-dir", required=True)
    register.add_argument("--registration", required=True)
    resume = subparsers.add_parser("register-resume")
    resume.add_argument("--repo-root", required=True)
    resume.add_argument("--source-commit", required=True)
    resume.add_argument("--native-manifest", required=True)
    resume.add_argument("--bottled-repo", required=True)
    resume.add_argument("--output-dir", required=True)
    resume.add_argument("--resume-output-dir", required=True)
    resume.add_argument("--registration", required=True)
    preflight = subparsers.add_parser("preflight")
    preflight.add_argument("--registration", required=True)
    run = subparsers.add_parser("run")
    run.add_argument("--registration", required=True)
    terminalize = subparsers.add_parser("terminalize-native-load-failure")
    terminalize.add_argument("--registration", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    registration: dict[str, Any] | None = None
    try:
        if args.command == "register":
            registration = build_registration(
                repo_root=args.repo_root,
                source_commit=args.source_commit,
                native_manifest_path=args.native_manifest,
                bottled_repo=args.bottled_repo,
                output_dir=args.output_dir,
            )
            binding = _write_canonical(args.registration, registration)
            print(_canonical_bytes(binding).decode("ascii"))
            return 0
        if args.command == "register-resume":
            registration = build_resume_registration(
                repo_root=args.repo_root,
                source_commit=args.source_commit,
                native_manifest_path=args.native_manifest,
                bottled_repo=args.bottled_repo,
                output_dir=args.output_dir,
                resume_output_dir=args.resume_output_dir,
            )
            binding = _write_canonical(args.registration, registration)
            print(_canonical_bytes(binding).decode("ascii"))
            return 0
        registration = _read_canonical(args.registration)
        if args.command == "preflight":
            print(_canonical_bytes(preflight_registration(registration)).decode("ascii"))
            return 0
        if args.command == "terminalize-native-load-failure":
            terminal = terminalize_native_load_failure(registration)
            print(_canonical_bytes(terminal).decode("ascii"))
            return 0
        terminal = execute_pilot(registration)
        print(_canonical_bytes(terminal).decode("ascii"))
        return 0
    except (CardOnlyRunnerBlocked, pilot.CardOnlyPilotBlocked, adapter.SimulatorAdapterError) as exc:
        if args.command == "run" and registration is not None:
            output_value = registration.get("output_dir")
            if isinstance(output_value, str):
                output = Path(output_value).resolve()
                if output.is_dir() and not (output / "terminal.json").exists():
                    try:
                        _write_canonical(
                            output / "terminal.json",
                            {
                                "downstream_authority": dict(FALSE_DOWNSTREAM_AUTHORITY),
                                "rollback": "native_simple_agent",
                                "schema_version": TERMINAL_SCHEMA_VERSION,
                                "stop_reason": str(exc),
                                "verdict": "card_only_native_baseline_pilot_not_ready",
                            },
                        )
                        terminal = _read_canonical(output / "terminal.json")
                        _publish_report(
                            output,
                            preflight={"verdict": "execution_failed"},
                            warm_start=None,
                            chunks=(),
                            comparison=None,
                            terminal=terminal,
                        )
                    except CardOnlyRunnerBlocked:
                        pass
        print(f"blocked: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
