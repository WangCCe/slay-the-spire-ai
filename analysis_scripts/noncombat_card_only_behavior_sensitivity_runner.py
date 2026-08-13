"""Run the bounded candidate-only card behavior sensitivity continuation."""

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


REGISTRATION_SCHEMA_VERSION = "noncombat-card-only-behavior-sensitivity-registration-v1"
_EARLY_NATIVE_HANDLES: list[Any] = []


def _early_preload_native() -> None:
    if len(sys.argv) < 2 or sys.argv[1] != "run-worker":
        return
    try:
        registration_path = Path(
            sys.argv[sys.argv.index("--registration") + 1]
        ).resolve()
        registration = json.loads(registration_path.read_text(encoding="ascii"))
        if registration.get("schema_version") != REGISTRATION_SCHEMA_VERSION:
            raise RuntimeError("behavior runner registration schema differs")
        native = registration["native"]["identity"]
        module_path = Path(native["module"]["path"]).resolve()
        dependencies = {
            Path(binding["path"]).name.casefold(): Path(binding["path"]).resolve()
            for binding in native["dependency_closure"]["dependencies"]
        }
        imports_by_path = {
            Path(row["path"]).resolve(): tuple(
                str(name).casefold() for name in row["imports"]
            )
            for row in native["dependency_closure"]["imports"]
        }
        order: list[Path] = []
        visiting: set[Path] = set()
        visited: set[Path] = set()

        def visit(path: Path) -> None:
            if path in visiting:
                raise RuntimeError("behavior runner dependency cycle differs")
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
            raise RuntimeError("behavior runner dependency graph differs")

        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        load_library = kernel32.LoadLibraryExW
        load_library.argtypes = (wintypes.LPCWSTR, wintypes.HANDLE, wintypes.DWORD)
        load_library.restype = wintypes.HMODULE
        for path in order:
            handle = load_library(str(path), None, 0x00000100 | 0x00000400)
            if not handle:
                raise OSError(
                    ctypes.get_last_error(), "LoadLibraryExW failed", str(path)
                )
            _EARLY_NATIVE_HANDLES.append(int(handle))
        for directory in native["dll_directories"]:
            _EARLY_NATIVE_HANDLES.append(os.add_dll_directory(directory))
        spec = importlib.util.spec_from_file_location(
            "sts_lightspeed_noncombat_adapter", module_path
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("behavior runner native specification is unavailable")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if module.adapter_api_version() != "sts-lightspeed-noncombat-adapter-v3":
            raise RuntimeError("behavior runner native API differs")
        sys.modules["sts_lightspeed_noncombat_adapter"] = module
    except (IndexError, KeyError, OSError, RuntimeError, ValueError) as exc:
        raise RuntimeError("behavior runner early native load failed") from exc


_early_preload_native()


from analysis_scripts.bottled_policy_oracle import BottledPolicyOracle
from analysis_scripts import noncombat_card_acceptance_empirical_successor_runtime as successor
from analysis_scripts import noncombat_card_only_behavior_sensitivity_training as training
from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot as pilot
from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot_runner as pilot_runner


MAX_CHARGED_SECONDS = 28_800.0
MAX_ENVIRONMENT_ACCESSES = 1_152
ADDITIONAL_CHUNKS = 16
MIN_ACTION_FLIPS = 4
FALSE_AUTHORITY = {
    "causal_claim": False,
    "communication_mod": False,
    "formal_rl": False,
    "fresh_evaluation": False,
    "gameplay": False,
    "ope": False,
    "policy_quality": False,
    "production_model_loading": False,
    "promotion": False,
    "qualification": False,
}
OPERATIONS = {
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
SOURCE_PATHS = tuple(
    sorted(
        set(pilot_runner.BOUND_SOURCE_PATHS)
        | {
            "analysis_scripts/noncombat_card_only_behavior_sensitivity_training.py",
            "analysis_scripts/noncombat_card_only_behavior_sensitivity_runner.py",
        }
    )
)
DEFAULT_R7_REGISTRATION = Path(
    "reports/noncombat_card_only_native_baseline_rl_pilot_20260813_r7/registration.json"
)
DEFAULT_R7_CHECKPOINT = Path(
    "reports/noncombat_card_only_native_baseline_rl_pilot_20260813_r7/checkpoint_004.json"
)
DEFAULT_OUTPUT_DIR = Path(
    "reports/noncombat_card_only_behavior_sensitivity_training_20260813_r1"
)


class BehaviorRunnerBlocked(RuntimeError):
    """Raised when the source-bound continuation cannot proceed."""


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
        raise BehaviorRunnerBlocked("artifact is not canonical JSON") from exc


def _read_canonical(path: Path | str) -> dict[str, Any]:
    source = Path(path).resolve()
    try:
        payload = source.read_bytes()
        value = json.loads(payload.decode("ascii"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BehaviorRunnerBlocked(f"artifact is unreadable: {source}") from exc
    if not isinstance(value, dict) or _canonical_bytes(value) != payload:
        raise BehaviorRunnerBlocked(f"artifact is not canonical: {source}")
    return value


def _write_canonical(path: Path | str, value: Mapping[str, Any]) -> dict[str, Any]:
    target = Path(path).resolve()
    payload = _canonical_bytes(dict(value))
    target.write_bytes(payload)
    return pilot_runner._file_binding(target)


def _source_bindings(root: Path) -> dict[str, dict[str, Any]]:
    return {
        relative: pilot_runner._file_binding(root / relative)
        for relative in SOURCE_PATHS
    }


def build_registration(
    *,
    repo_root: Path | str,
    source_commit: str,
    r7_registration_path: Path | str,
    r7_checkpoint_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    if pilot_runner._git(root, "rev-parse", "HEAD") != source_commit:
        raise BehaviorRunnerBlocked("registration requires the current HEAD")
    r7_registration_path = Path(r7_registration_path).resolve()
    r7_checkpoint_path = Path(r7_checkpoint_path).resolve()
    r7 = _read_canonical(r7_registration_path)
    if r7.get("schema_version") != pilot_runner.RESUME_REGISTRATION_SCHEMA_VERSION:
        raise BehaviorRunnerBlocked("r7 registration schema differs")
    output = Path(output_dir).resolve()
    production_root = Path(
        r7["production_isolation"]["production_checkpoints"]["path"]
    ).resolve()
    if output == production_root or production_root in output.parents:
        raise BehaviorRunnerBlocked("output overlaps production checkpoints")
    seeds = list(pilot_runner.CONSUMED_DEVELOPMENT_SEEDS)
    return validate_registration(
        {
            "configuration": {
                "additional_chunks": ADDITIONAL_CHUNKS,
                "first_chunk_index": training.FIRST_CHUNK_INDEX,
                "last_chunk_index": training.FINAL_CHUNK_INDEX - 1,
                "maximum_censored_trajectories_per_chunk": training.MAX_CENSORED_TRAJECTORIES,
                "maximum_charged_seconds": MAX_CHARGED_SECONDS,
                "maximum_environment_accesses": MAX_ENVIRONMENT_ACCESSES,
                "minimum_action_flips": MIN_ACTION_FLIPS,
                "training_environment_accesses_per_chunk": training.CHUNK_SEED_COUNT,
            },
            "downstream_authority": copy.deepcopy(FALSE_AUTHORITY),
            "inputs": {
                "r7_checkpoint": pilot_runner._file_binding(r7_checkpoint_path),
                "r7_registration": pilot_runner._file_binding(r7_registration_path),
            },
            "native": copy.deepcopy(r7["native"]),
            "operations": copy.deepcopy(OPERATIONS),
            "output_dir": output.as_posix(),
            "policy_context": {
                "bottled": copy.deepcopy(r7["bottled"]),
                "corpus": copy.deepcopy(r7["corpus"]),
            },
            "production_isolation": {
                "communication_mod_config": pilot_runner._file_binding(
                    pilot_runner.COMMUNICATION_MOD_CONFIG
                ),
                "production_checkpoints": pilot_runner._directory_metadata_binding(
                    production_root
                ),
            },
            "schedule": {
                "comparison_seeds": seeds,
                "training_chunk_seeds": [seeds] * ADDITIONAL_CHUNKS,
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


def validate_registration(value: Mapping[str, Any]) -> dict[str, Any]:
    registration = copy.deepcopy(dict(value))
    expected_fields = {
        "configuration",
        "downstream_authority",
        "inputs",
        "native",
        "operations",
        "output_dir",
        "policy_context",
        "production_isolation",
        "schedule",
        "schema_version",
        "source",
    }
    if set(registration) != expected_fields or registration.get(
        "schema_version"
    ) != REGISTRATION_SCHEMA_VERSION:
        raise BehaviorRunnerBlocked("registration fields differ")
    expected_configuration = {
        "additional_chunks": ADDITIONAL_CHUNKS,
        "first_chunk_index": training.FIRST_CHUNK_INDEX,
        "last_chunk_index": training.FINAL_CHUNK_INDEX - 1,
        "maximum_censored_trajectories_per_chunk": training.MAX_CENSORED_TRAJECTORIES,
        "maximum_charged_seconds": MAX_CHARGED_SECONDS,
        "maximum_environment_accesses": MAX_ENVIRONMENT_ACCESSES,
        "minimum_action_flips": MIN_ACTION_FLIPS,
        "training_environment_accesses_per_chunk": training.CHUNK_SEED_COUNT,
    }
    if registration["configuration"] != expected_configuration:
        raise BehaviorRunnerBlocked("registration configuration differs")
    if registration["downstream_authority"] != FALSE_AUTHORITY:
        raise BehaviorRunnerBlocked("registration authority differs")
    if registration["operations"] != OPERATIONS:
        raise BehaviorRunnerBlocked("registration operations differ")
    inputs = registration["inputs"]
    if not isinstance(inputs, dict) or set(inputs) != {
        "r7_checkpoint",
        "r7_registration",
    }:
        raise BehaviorRunnerBlocked("registration input bindings differ")
    if any(
        not isinstance(binding, dict)
        or set(binding) != {"path", "sha256", "size_bytes"}
        for binding in inputs.values()
    ):
        raise BehaviorRunnerBlocked("registration input file binding differs")
    source = registration["source"]
    if (
        not isinstance(source, dict)
        or set(source) != {"bindings", "commit", "repo_root"}
        or set(source["bindings"]) != set(SOURCE_PATHS)
        or not isinstance(source["commit"], str)
        or len(source["commit"]) != 40
    ):
        raise BehaviorRunnerBlocked("registration source differs")
    native = registration["native"]
    if not isinstance(native, dict) or set(native) != {"identity", "manifest"}:
        raise BehaviorRunnerBlocked("registration native identity differs")
    context = registration["policy_context"]
    if not isinstance(context, dict) or set(context) != {"bottled", "corpus"}:
        raise BehaviorRunnerBlocked("registration policy context differs")
    if context["corpus"].get("allowed_cohorts") != list(pilot.ALLOWED_CORPUS_COHORTS):
        raise BehaviorRunnerBlocked("registration corpus cohorts differ")
    seeds = list(pilot_runner.CONSUMED_DEVELOPMENT_SEEDS)
    if registration["schedule"] != {
        "comparison_seeds": seeds,
        "training_chunk_seeds": [seeds] * ADDITIONAL_CHUNKS,
        "seed_status": "already-consumed-development-only",
    }:
        raise BehaviorRunnerBlocked("registration schedule differs")
    isolation = registration["production_isolation"]
    if not isinstance(isolation, dict) or set(isolation) != {
        "communication_mod_config",
        "production_checkpoints",
    }:
        raise BehaviorRunnerBlocked("registration production isolation differs")
    if not isinstance(registration["output_dir"], str):
        raise BehaviorRunnerBlocked("registration output directory differs")
    return registration


def _load_probe_and_entry(
    registration: Mapping[str, Any],
) -> tuple[tuple[Any, ...], training.BehaviorSensitivityRuntime]:
    context = registration["policy_context"]
    corpus = pilot.load_bound_card_corpus(
        context["corpus"]["path"], cohorts=pilot.ALLOWED_CORPUS_COHORTS
    )
    oracle = BottledPolicyOracle(Path(context["bottled"]["path"]))
    labels = pilot.label_bound_card_corpus(
        corpus,
        oracle,
        expected_bottled_commit=context["bottled"]["commit_short"],
    )
    probe_rows = pilot.project_bottled_card_labels(labels, cohort="validation")
    r7 = pilot.restore_card_only_residual_checkpoint(
        Path(registration["inputs"]["r7_checkpoint"]["path"]).read_bytes(),
        probe_rows=probe_rows,
    )
    if (
        r7.next_chunk_index != training.FIRST_CHUNK_INDEX
        or r7.environment_accesses != 512
        or r7.candidate_optimizer_steps != training.FIRST_CHUNK_INDEX
    ):
        raise BehaviorRunnerBlocked("r7 continuation coordinate differs")
    continuation = training.initialize_behavior_sensitivity_runtime(
        bootstrap=r7.bootstrap,
        candidate_optimizer=r7.candidate_optimizer,
        probe_rows=probe_rows,
    )
    return probe_rows, continuation


def preflight_registration(
    value: Mapping[str, Any],
    *,
    process_observer: Callable[[], Sequence[Mapping[str, Any]]] = pilot_runner._forbidden_processes,
    allow_resume_output: bool = False,
) -> dict[str, Any]:
    registration = validate_registration(value)
    source = registration["source"]
    root = Path(source["repo_root"]).resolve()
    if pilot_runner._git(root, "rev-parse", "HEAD") != source["commit"]:
        raise BehaviorRunnerBlocked("registered source is not current HEAD")
    if any(
        not pilot_runner._binding_matches(binding)
        for binding in source["bindings"].values()
    ):
        raise BehaviorRunnerBlocked("registered source bytes differ")
    if any(
        not pilot_runner._binding_matches(binding)
        for binding in registration["inputs"].values()
    ):
        raise BehaviorRunnerBlocked("registered input bytes differ")
    r7 = _read_canonical(registration["inputs"]["r7_registration"]["path"])
    if r7["native"] != registration["native"] or r7["bottled"] != registration[
        "policy_context"
    ]["bottled"] or r7["corpus"] != registration["policy_context"]["corpus"]:
        raise BehaviorRunnerBlocked("r7 policy binding differs")
    native = registration["native"]
    native_bindings = [
        native["manifest"],
        native["identity"]["module"],
        *native["identity"]["dependency_closure"]["dependencies"],
    ]
    if any(not pilot_runner._binding_matches(binding) for binding in native_bindings):
        raise BehaviorRunnerBlocked("registered native bytes differ")
    context = registration["policy_context"]
    corpus_binding = {
        key: context["corpus"][key] for key in ("path", "sha256", "size_bytes")
    }
    if not pilot_runner._binding_matches(corpus_binding):
        raise BehaviorRunnerBlocked("registered corpus bytes differ")
    if pilot_runner._bottled_identity(context["bottled"]["path"]) != context["bottled"]:
        raise BehaviorRunnerBlocked("registered Bottled checkout differs")
    isolation = registration["production_isolation"]
    if not pilot_runner._binding_matches(isolation["communication_mod_config"]):
        raise BehaviorRunnerBlocked("CommunicationMod configuration differs")
    if pilot_runner._directory_metadata_binding(
        isolation["production_checkpoints"]["path"]
    ) != isolation["production_checkpoints"]:
        raise BehaviorRunnerBlocked("production checkpoint metadata differs")
    if list(process_observer()):
        raise BehaviorRunnerBlocked("game or CommunicationMod process is active")
    output = Path(registration["output_dir"]).resolve()
    production_root = Path(isolation["production_checkpoints"]["path"]).resolve()
    if output == production_root or production_root in output.parents:
        raise BehaviorRunnerBlocked("output overlaps production checkpoints")
    if output.exists():
        if not allow_resume_output or not output.is_dir():
            raise BehaviorRunnerBlocked("output already exists")
        if _read_canonical(output / "registration.json") != registration:
            raise BehaviorRunnerBlocked("resume output registration differs")
        if (output / "terminal.json").exists():
            raise BehaviorRunnerBlocked("continuation already has a terminal result")
    _load_probe_and_entry(registration)
    return {
        "checks": {
            "entry_checkpoint_bound": True,
            "forbidden_processes_absent": True,
            "native_bytes_bound_without_loading": True,
            "output_outside_production": True,
            "policy_context_bound": True,
            "production_isolation_bound": True,
            "source_bound": True,
        },
        "registration_sha256": hashlib.sha256(
            _canonical_bytes(registration)
        ).hexdigest(),
        "schema_version": "noncombat-card-only-behavior-sensitivity-preflight-v1",
        "verdict": "preflight_passed",
    }


def _load_or_initialize_runtime(
    registration: Mapping[str, Any], output: Path
) -> training.BehaviorSensitivityRuntime:
    probe_rows, entry = _load_probe_and_entry(registration)
    entry_model_path = output / "entry_model.json"
    checkpoints = sorted(output.glob("checkpoint_*.json"))
    if not checkpoints:
        entry_model_path.write_bytes(entry.entry_model)
        (output / "checkpoint_004.json").write_bytes(
            training.encode_behavior_sensitivity_checkpoint(entry)
        )
        return entry
    if entry_model_path.read_bytes() != entry.entry_model:
        raise BehaviorRunnerBlocked("entry model artifact differs")
    latest = checkpoints[-1]
    expected_name = f"checkpoint_{int(latest.stem.split('_')[1]):03d}.json"
    if latest.name != expected_name:
        raise BehaviorRunnerBlocked("continuation checkpoint name differs")
    restored = training.restore_behavior_sensitivity_checkpoint(
        latest.read_bytes(),
        probe_rows=probe_rows,
        entry_model=entry.entry_model,
    )
    if latest.name != f"checkpoint_{restored.next_chunk_index:03d}.json":
        raise BehaviorRunnerBlocked("continuation checkpoint coordinate differs")
    return restored


def _terminal_comparison(
    value: training.BehaviorSensitivityRuntime,
    *,
    environment_factory: Callable[[int], Any],
    seeds: Sequence[int],
    deadline: float,
    clock: Callable[[], float],
) -> dict[str, Any]:
    pairs = []
    for seed in seeds:
        if float(clock()) > deadline:
            raise BehaviorRunnerBlocked("deadline reached during terminal comparison")
        candidate = successor.rollout_arm_frozen_evaluation(
            value.bootstrap,
            arm="candidate",
            environment_factory=environment_factory,
            seed=seed,
            deadline=deadline,
            clock=clock,
            native_baseline_categories=tuple(
                category
                for category in pilot_runner.adapter.TARGET_CATEGORIES
                if category != "card_reward"
            ),
        )
        control = successor.rollout_arm_frozen_evaluation(
            value.bootstrap,
            arm="control",
            environment_factory=environment_factory,
            seed=seed,
            deadline=deadline,
            clock=clock,
            native_baseline_categories=pilot_runner.adapter.TARGET_CATEGORIES,
        )
        pairs.append(successor.PairedEpisodeRollout(seed=seed, candidate=candidate, control=control))
    comparison = pilot_runner.classify_frozen_comparison(tuple(pairs))
    behavior = training.behavior_summary(value)
    comparison["behavior"] = behavior
    comparison["checks"]["minimum_action_flips"] = (
        behavior["action_flips_from_entry"] >= MIN_ACTION_FLIPS
    )
    ready = all(comparison["checks"].values())
    comparison["verdict"] = (
        "ready_to_propose_fresh_card_only_evaluation"
        if ready
        else "card_only_behavior_sensitivity_not_ready"
    )
    return comparison


def execute(
    value: Mapping[str, Any],
    *,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    registration = validate_registration(value)
    output = Path(registration["output_dir"]).resolve()
    resume = output.exists()
    preflight = preflight_registration(
        registration, allow_resume_output=resume
    )
    if not resume:
        output.mkdir(parents=False, exist_ok=False)
        _write_canonical(output / "registration.json", registration)
        _write_canonical(output / "preflight.json", preflight)
    continuation = _load_or_initialize_runtime(registration, output)
    environment_factory = pilot_runner._load_environment_factory(
        registration["native"]["identity"]
    )
    started = float(clock())
    deadline = started + registration["configuration"]["maximum_charged_seconds"]
    seeds_by_chunk = registration["schedule"]["training_chunk_seeds"]
    while continuation.next_chunk_index < training.FINAL_CHUNK_INDEX:
        if continuation.stopped_for_concentration:
            break
        chunk_index = continuation.next_chunk_index
        schedule_index = chunk_index - training.FIRST_CHUNK_INDEX
        entry_checkpoint = output / f"checkpoint_{chunk_index:03d}.json"
        _write_canonical(
            output / "in_progress.json",
            {
                "chunk_index": chunk_index,
                "entry_checkpoint": pilot_runner._file_binding(entry_checkpoint),
                "seeds": seeds_by_chunk[schedule_index],
            },
        )
        completed = training.collect_and_complete_candidate_only_chunk(
            continuation,
            environment_factory=environment_factory,
            seeds=seeds_by_chunk[schedule_index],
            chunk_index=chunk_index,
            deadline=deadline,
            clock=clock,
        )
        continuation = completed.runtime
        _write_canonical(output / f"chunk_{chunk_index:03d}.json", continuation.completed_summaries[-1])
        (output / f"checkpoint_{continuation.next_chunk_index:03d}.json").write_bytes(
            completed.checkpoint
        )
        _write_canonical(
            output / "progress.json",
            {
                "environment_accesses": continuation.environment_accesses,
                "next_chunk_index": continuation.next_chunk_index,
                "optimizer_steps": continuation.next_chunk_index,
            },
        )
        (output / "in_progress.json").unlink(missing_ok=True)

    comparison = None
    if continuation.next_chunk_index == training.FINAL_CHUNK_INDEX and not continuation.stopped_for_concentration:
        comparison = _terminal_comparison(
            continuation,
            environment_factory=environment_factory,
            seeds=registration["schedule"]["comparison_seeds"],
            deadline=deadline,
            clock=clock,
        )
        _write_canonical(output / "comparison.json", comparison)
    environment_accesses = continuation.environment_accesses + (
        128 if comparison is not None else 0
    )
    if environment_accesses > MAX_ENVIRONMENT_ACCESSES:
        raise BehaviorRunnerBlocked("environment access bound exceeded")
    terminal = {
        "behavior": training.behavior_summary(continuation),
        "comparison": comparison,
        "downstream_authority": copy.deepcopy(FALSE_AUTHORITY),
        "environment_accesses": environment_accesses,
        "next_chunk_index": continuation.next_chunk_index,
        "optimizer_steps": continuation.next_chunk_index,
        "rollback": "native_simple_agent",
        "schema_version": "noncombat-card-only-behavior-sensitivity-terminal-v1",
        "verdict": (
            comparison["verdict"]
            if comparison is not None
            else "card_only_behavior_sensitivity_not_ready"
        ),
    }
    _write_canonical(output / "terminal.json", terminal)
    _write_canonical(
        output / "report.json",
        {
            "chunks": copy.deepcopy(continuation.completed_summaries),
            "downstream_authority": copy.deepcopy(FALSE_AUTHORITY),
            "preflight": preflight,
            "registration": registration,
            "terminal": terminal,
        },
    )
    return terminal


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    register = subparsers.add_parser("register")
    register.add_argument("--repo-root", required=True)
    register.add_argument("--source-commit", required=True)
    register.add_argument("--r7-registration", default=str(DEFAULT_R7_REGISTRATION))
    register.add_argument("--r7-checkpoint", default=str(DEFAULT_R7_CHECKPOINT))
    register.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    register.add_argument("--registration", required=True)
    preflight = subparsers.add_parser("preflight")
    preflight.add_argument("--registration", required=True)
    run = subparsers.add_parser("run")
    run.add_argument("--registration", required=True)
    worker = subparsers.add_parser("run-worker")
    worker.add_argument("--registration", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "register":
            registration = build_registration(
                repo_root=args.repo_root,
                source_commit=args.source_commit,
                r7_registration_path=args.r7_registration,
                r7_checkpoint_path=args.r7_checkpoint,
                output_dir=args.output_dir,
            )
            print(
                _canonical_bytes(
                    _write_canonical(args.registration, registration)
                ).decode("ascii")
            )
            return 0
        registration = _read_canonical(args.registration)
        if args.command == "preflight":
            print(_canonical_bytes(preflight_registration(registration)).decode("ascii"))
            return 0
        if args.command == "run":
            preflight_registration(
                registration,
                allow_resume_output=Path(registration["output_dir"]).exists(),
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    str(Path(__file__).resolve()),
                    "run-worker",
                    "--registration",
                    str(Path(args.registration).resolve()),
                ],
                cwd=Path(registration["source"]["repo_root"]),
                text=True,
            )
            return completed.returncode
        terminal = execute(registration)
        print(_canonical_bytes(terminal).decode("ascii"))
        return 0
    except (
        BehaviorRunnerBlocked,
        training.BehaviorSensitivityBlocked,
        pilot.CardOnlyPilotBlocked,
        pilot_runner.CardOnlyRunnerBlocked,
        successor.SuccessorRuntimeError,
    ) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
