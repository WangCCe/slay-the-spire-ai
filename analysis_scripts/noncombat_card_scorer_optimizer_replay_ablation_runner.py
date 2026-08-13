"""Run the one-step card scorer-only optimizer replay ablation."""

from __future__ import annotations

import argparse
import copy
import gc
import hashlib
import importlib.util
import json
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


REGISTRATION_SCHEMA_VERSION = "noncombat-card-scorer-optimizer-replay-ablation-registration-v1"
_EARLY_NATIVE_HANDLES: list[Any] = []


def _early_preload_native() -> None:
    if len(sys.argv) < 2 or sys.argv[1] != "scorer-worker":
        return
    try:
        registration_path = Path(
            sys.argv[sys.argv.index("--registration") + 1]
        ).resolve()
        registration = json.loads(registration_path.read_text(encoding="ascii"))
        if registration.get("schema_version") != REGISTRATION_SCHEMA_VERSION:
            raise RuntimeError("scorer worker registration schema differs")
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
                raise RuntimeError("scorer worker dependency cycle differs")
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
            raise RuntimeError("scorer worker dependency graph differs")
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        load_library = kernel32.LoadLibraryExW
        load_library.argtypes = (wintypes.LPCWSTR, wintypes.HANDLE, wintypes.DWORD)
        load_library.restype = wintypes.HMODULE
        for path in order:
            handle = load_library(str(path), None, 0x00000100 | 0x00000400)
            if not handle:
                raise OSError(ctypes.get_last_error(), "LoadLibraryExW failed", str(path))
            _EARLY_NATIVE_HANDLES.append(int(handle))
        for directory in native["dll_directories"]:
            _EARLY_NATIVE_HANDLES.append(os.add_dll_directory(directory))
        spec = importlib.util.spec_from_file_location(
            "sts_lightspeed_noncombat_adapter", module_path
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("scorer worker native specification is unavailable")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if module.adapter_api_version() != "sts-lightspeed-noncombat-adapter-v3":
            raise RuntimeError("scorer worker native API differs")
        sys.modules["sts_lightspeed_noncombat_adapter"] = module
    except (IndexError, KeyError, OSError, RuntimeError, ValueError) as exc:
        raise RuntimeError("scorer worker early native load failed") from exc


_early_preload_native()


from analysis_scripts import noncombat_card_acceptance_empirical_successor_runtime as successor
from analysis_scripts import noncombat_card_only_behavior_sensitivity_runner as behavior_runner
from analysis_scripts import noncombat_card_only_behavior_sensitivity_training as training
from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot as pilot
from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot_runner as pilot_runner
from analysis_scripts import noncombat_card_optimizer_replay as replay
from analysis_scripts import noncombat_card_scorer_optimizer_replay_ablation as ablation


MAX_CHARGED_SECONDS = 7_200.0
MAX_ENVIRONMENT_ACCESSES = 64
FALSE_AUTHORITY = {
    "causal_claim": False,
    "communication_mod": False,
    "formal_rl": False,
    "fresh_evaluation": False,
    "further_training": False,
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
    "fresh_evaluation": False,
    "gameplay": False,
    "model_fitting": True,
    "native_loading": True,
    "optimizer_steps": 2,
    "production_model_loading": False,
    "replay_write_and_read": True,
    "seed_access": True,
    "training": True,
}
SOURCE_PATHS = tuple(
    sorted(
        set(behavior_runner.SOURCE_PATHS)
        | {
            "analysis_scripts/noncombat_card_only_behavior_sensitivity_diagnostic.py",
            "analysis_scripts/noncombat_card_optimizer_replay.py",
            "analysis_scripts/noncombat_card_scorer_optimizer.py",
            "analysis_scripts/noncombat_card_scorer_optimizer_replay_ablation.py",
            "analysis_scripts/noncombat_card_scorer_optimizer_replay_ablation_runner.py",
        }
    )
)
DEFAULT_PARENT_REGISTRATION = Path(
    "reports/noncombat_card_only_behavior_sensitivity_training_20260813_r1_registration.json"
)
DEFAULT_ENTRY_CHECKPOINT = Path(
    "reports/noncombat_card_only_behavior_sensitivity_training_20260813_r1/checkpoint_004.json"
)
DEFAULT_HISTORICAL_CHECKPOINT = Path(
    "reports/noncombat_card_only_behavior_sensitivity_training_20260813_r1/checkpoint_005.json"
)
DEFAULT_OUTPUT_DIR = Path(
    "reports/noncombat_card_scorer_optimizer_replay_ablation_20260813_r1"
)


class ScorerReplayRunnerBlocked(RuntimeError):
    """Raised when the bound one-shot runner cannot proceed."""


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
        raise ScorerReplayRunnerBlocked("runner artifact is not canonical") from exc


def _read_canonical(path: Path | str) -> dict[str, Any]:
    source = Path(path).resolve()
    payload = source.read_bytes()
    try:
        value = json.loads(payload.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ScorerReplayRunnerBlocked(f"invalid JSON artifact: {source}") from exc
    if not isinstance(value, dict) or _canonical_bytes(value) != payload:
        raise ScorerReplayRunnerBlocked(f"artifact is not canonical: {source}")
    return value


def _write_canonical(path: Path | str, value: Mapping[str, Any]) -> dict[str, Any]:
    target = Path(path).resolve()
    target.write_bytes(_canonical_bytes(dict(value)))
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
    parent_registration_path: Path | str,
    entry_checkpoint_path: Path | str,
    historical_checkpoint_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    if pilot_runner._git(root, "rev-parse", "HEAD") != source_commit:
        raise ScorerReplayRunnerBlocked("registration requires current HEAD")
    parent_path = Path(parent_registration_path).resolve()
    parent = behavior_runner.validate_registration(_read_canonical(parent_path))
    entry_path = Path(entry_checkpoint_path).resolve()
    historical_path = Path(historical_checkpoint_path).resolve()
    output = Path(output_dir).resolve()
    production_root = Path(
        parent["production_isolation"]["production_checkpoints"]["path"]
    ).resolve()
    if output == production_root or production_root in output.parents:
        raise ScorerReplayRunnerBlocked("output overlaps production checkpoints")
    return validate_registration(
        {
            "configuration": {
                "entry_chunk_index": training.FIRST_CHUNK_INDEX,
                "maximum_canonical_replay_bytes": replay.MAX_CANONICAL_BYTES,
                "maximum_censored_trajectories": training.MAX_CENSORED_TRAJECTORIES,
                "maximum_charged_seconds": MAX_CHARGED_SECONDS,
                "maximum_environment_accesses": MAX_ENVIRONMENT_ACCESSES,
                "maximum_stored_replay_bytes": replay.MAX_STORED_BYTES,
                "minimum_supported_trajectories": successor.MIN_CANDIDATE_TRAJECTORIES_PER_CHUNK,
                "optimizer_steps_per_branch": 1,
                "retained_mean_joint_tv_threshold": ablation.RETAINED_MEAN_JOINT_TV_THRESHOLD,
            },
            "downstream_authority": copy.deepcopy(FALSE_AUTHORITY),
            "inputs": {
                "entry_checkpoint": pilot_runner._file_binding(entry_path),
                "historical_checkpoint": pilot_runner._file_binding(historical_path),
                "parent_registration": pilot_runner._file_binding(parent_path),
            },
            "native": copy.deepcopy(parent["native"]),
            "operations": copy.deepcopy(OPERATIONS),
            "output_dir": output.as_posix(),
            "policy_context": copy.deepcopy(parent["policy_context"]),
            "production_isolation": {
                "communication_mod_config": pilot_runner._file_binding(
                    pilot_runner.COMMUNICATION_MOD_CONFIG
                ),
                "production_checkpoints": pilot_runner._directory_metadata_binding(
                    production_root
                ),
            },
            "schedule": {
                "seed_status": "already-consumed-development-only",
                "shared_trajectory_seeds": list(
                    parent["schedule"]["training_chunk_seeds"][0]
                ),
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
    expected_configuration = {
        "entry_chunk_index": training.FIRST_CHUNK_INDEX,
        "maximum_canonical_replay_bytes": replay.MAX_CANONICAL_BYTES,
        "maximum_censored_trajectories": training.MAX_CENSORED_TRAJECTORIES,
        "maximum_charged_seconds": MAX_CHARGED_SECONDS,
        "maximum_environment_accesses": MAX_ENVIRONMENT_ACCESSES,
        "maximum_stored_replay_bytes": replay.MAX_STORED_BYTES,
        "minimum_supported_trajectories": successor.MIN_CANDIDATE_TRAJECTORIES_PER_CHUNK,
        "optimizer_steps_per_branch": 1,
        "retained_mean_joint_tv_threshold": ablation.RETAINED_MEAN_JOINT_TV_THRESHOLD,
    }
    if (
        set(registration) != expected_fields
        or registration.get("schema_version") != REGISTRATION_SCHEMA_VERSION
        or registration.get("configuration") != expected_configuration
        or registration.get("downstream_authority") != FALSE_AUTHORITY
        or registration.get("operations") != OPERATIONS
    ):
        raise ScorerReplayRunnerBlocked("registration fields or policy differ")
    inputs = registration["inputs"]
    if not isinstance(inputs, dict) or set(inputs) != {
        "entry_checkpoint",
        "historical_checkpoint",
        "parent_registration",
    } or any(
        not isinstance(binding, dict)
        or set(binding) != {"path", "sha256", "size_bytes"}
        for binding in inputs.values()
    ):
        raise ScorerReplayRunnerBlocked("registration inputs differ")
    source = registration["source"]
    if (
        not isinstance(source, dict)
        or set(source) != {"bindings", "commit", "repo_root"}
        or set(source["bindings"]) != set(SOURCE_PATHS)
        or not isinstance(source["commit"], str)
        or len(source["commit"]) != 40
    ):
        raise ScorerReplayRunnerBlocked("registration source differs")
    if registration["schedule"] != {
        "seed_status": "already-consumed-development-only",
        "shared_trajectory_seeds": list(pilot_runner.CONSUMED_DEVELOPMENT_SEEDS),
    }:
        raise ScorerReplayRunnerBlocked("registration schedule differs")
    if not isinstance(registration["output_dir"], str):
        raise ScorerReplayRunnerBlocked("registration output differs")
    if not isinstance(registration["native"], dict) or set(registration["native"]) != {
        "identity",
        "manifest",
    }:
        raise ScorerReplayRunnerBlocked("registration native differs")
    if not isinstance(registration["policy_context"], dict) or set(
        registration["policy_context"]
    ) != {"bottled", "corpus"}:
        raise ScorerReplayRunnerBlocked("registration policy context differs")
    if not isinstance(registration["production_isolation"], dict) or set(
        registration["production_isolation"]
    ) != {"communication_mod_config", "production_checkpoints"}:
        raise ScorerReplayRunnerBlocked("registration isolation differs")
    return registration


def _load_bound_runtimes(registration: Mapping[str, Any]):
    inputs = registration["inputs"]
    parent = behavior_runner.validate_registration(
        _read_canonical(inputs["parent_registration"]["path"])
    )
    probe_rows, initialized = behavior_runner._load_probe_and_entry(parent)
    entry_payload = Path(inputs["entry_checkpoint"]["path"]).read_bytes()
    collector = training.restore_behavior_sensitivity_checkpoint(
        entry_payload, probe_rows=probe_rows, entry_model=initialized.entry_model
    )
    full = training.restore_behavior_sensitivity_checkpoint(
        entry_payload, probe_rows=probe_rows, entry_model=initialized.entry_model
    )
    scorer_branch = training.restore_behavior_sensitivity_checkpoint(
        entry_payload, probe_rows=probe_rows, entry_model=initialized.entry_model
    )
    historical = training.restore_behavior_sensitivity_checkpoint(
        Path(inputs["historical_checkpoint"]["path"]).read_bytes(),
        probe_rows=probe_rows,
        entry_model=initialized.entry_model,
    )
    if (
        collector.next_chunk_index != training.FIRST_CHUNK_INDEX
        or full.next_chunk_index != training.FIRST_CHUNK_INDEX
        or scorer_branch.next_chunk_index != training.FIRST_CHUNK_INDEX
        or historical.next_chunk_index != training.FIRST_CHUNK_INDEX + 1
    ):
        raise ScorerReplayRunnerBlocked("bound checkpoint coordinates differ")
    return probe_rows, collector, full, scorer_branch, historical


def preflight_registration(
    value: Mapping[str, Any],
    *,
    process_observer: Callable[[], Sequence[Mapping[str, Any]]] = pilot_runner._forbidden_processes,
) -> dict[str, Any]:
    registration = validate_registration(value)
    root = Path(registration["source"]["repo_root"]).resolve()
    if pilot_runner._git(root, "rev-parse", "HEAD") != registration["source"]["commit"]:
        raise ScorerReplayRunnerBlocked("registered source is not current HEAD")
    if any(
        not pilot_runner._binding_matches(binding)
        for binding in registration["source"]["bindings"].values()
    ) or any(
        not pilot_runner._binding_matches(binding)
        for binding in registration["inputs"].values()
    ):
        raise ScorerReplayRunnerBlocked("registered source or input bytes differ")
    parent = behavior_runner.validate_registration(
        _read_canonical(registration["inputs"]["parent_registration"]["path"])
    )
    if (
        parent["native"] != registration["native"]
        or parent["policy_context"] != registration["policy_context"]
        or parent["schedule"]["training_chunk_seeds"][0]
        != registration["schedule"]["shared_trajectory_seeds"]
    ):
        raise ScorerReplayRunnerBlocked("parent experiment binding differs")
    native = registration["native"]
    native_bindings = [
        native["manifest"],
        native["identity"]["module"],
        *native["identity"]["dependency_closure"]["dependencies"],
    ]
    if any(not pilot_runner._binding_matches(binding) for binding in native_bindings):
        raise ScorerReplayRunnerBlocked("registered native bytes differ")
    context = registration["policy_context"]
    corpus_binding = {
        key: context["corpus"][key] for key in ("path", "sha256", "size_bytes")
    }
    if not pilot_runner._binding_matches(corpus_binding) or pilot_runner._bottled_identity(
        context["bottled"]["path"]
    ) != context["bottled"]:
        raise ScorerReplayRunnerBlocked("registered policy context differs")
    isolation = registration["production_isolation"]
    if not pilot_runner._binding_matches(isolation["communication_mod_config"]) or (
        pilot_runner._directory_metadata_binding(
            isolation["production_checkpoints"]["path"]
        )
        != isolation["production_checkpoints"]
    ):
        raise ScorerReplayRunnerBlocked("production isolation differs")
    if list(process_observer()):
        raise ScorerReplayRunnerBlocked("game or CommunicationMod process is active")
    output = Path(registration["output_dir"]).resolve()
    production_root = Path(isolation["production_checkpoints"]["path"]).resolve()
    if output.exists() or output == production_root or production_root in output.parents:
        raise ScorerReplayRunnerBlocked("output is unavailable or overlaps production")
    _load_bound_runtimes(registration)
    return {
        "checks": {
            "entry_and_historical_checkpoints_bound": True,
            "forbidden_processes_absent": True,
            "native_bytes_bound_without_loading": True,
            "output_absent_and_outside_production": True,
            "parent_policy_context_bound": True,
            "production_isolation_bound": True,
            "source_bound": True,
        },
        "registration_sha256": hashlib.sha256(_canonical_bytes(registration)).hexdigest(),
        "schema_version": "noncombat-card-scorer-optimizer-replay-ablation-preflight-v1",
        "verdict": "preflight_passed",
    }


def execute(value: Mapping[str, Any], *, clock: Callable[[], float] = time.monotonic) -> dict[str, Any]:
    registration = validate_registration(value)
    preflight = preflight_registration(registration)
    output = Path(registration["output_dir"]).resolve()
    output.mkdir(parents=False, exist_ok=False)
    _write_canonical(output / "registration.json", registration)
    _write_canonical(output / "preflight.json", preflight)
    _write_canonical(
        output / "started.json",
        {
            "environment_access_bound": MAX_ENVIRONMENT_ACCESSES,
            "replay_schema_version": replay.SCHEMA_VERSION,
            "source_commit": registration["source"]["commit"],
        },
    )
    probe_rows, collector, full, scorer_branch, historical = _load_bound_runtimes(
        registration
    )
    environment_factory = pilot_runner._load_environment_factory(
        registration["native"]["identity"]
    )
    deadline = float(clock()) + registration["configuration"]["maximum_charged_seconds"]
    attempted = []
    for seed in registration["schedule"]["shared_trajectory_seeds"]:
        if float(clock()) > deadline:
            raise ScorerReplayRunnerBlocked("deadline reached during collection")
        attempted.append(
            successor.rollout_candidate_card_only_native_baseline_training_episode(
                collector.bootstrap,
                environment_factory=environment_factory,
                seed=seed,
                deadline=deadline,
                clock=clock,
            )
        )
    supported, censored = training._validate_candidate_trajectories(tuple(attempted))
    generator_states = {
        name: generator.get_state().clone()
        for name, generator in collector.bootstrap.generators.items()
    }
    encoded = replay.encode_replay(supported, generator_states=generator_states)
    replay_path = output / "candidate_replay.json.gz"
    replay_path.write_bytes(encoded.stored)
    _write_canonical(output / "replay_binding.json", encoded.binding)

    del attempted, supported, generator_states, collector, environment_factory
    gc.collect()
    stored = replay_path.read_bytes()
    decoded = replay.decode_replay(stored, encoded.binding)
    completed = ablation.apply_decoded_replay_ablation(
        full_bootstrap=full.bootstrap,
        full_optimizer=full.candidate_optimizer,
        scorer_bootstrap=scorer_branch.bootstrap,
        scorer_source_optimizer=scorer_branch.candidate_optimizer,
        decoded=decoded,
        expected_full_bootstrap=successor.encode_paired_bootstrap(historical.bootstrap),
        expected_full_optimizer=successor.encode_optimizer_state(
            historical.candidate_optimizer
        ),
        probe_rows=probe_rows,
    )
    full_path = output / "full_checkpoint_005.json"
    scorer_path = output / "scorer_checkpoint_005.json"
    full_path.write_bytes(completed.full_checkpoint)
    scorer_path.write_bytes(completed.scorer_checkpoint)

    isolation = registration["production_isolation"]
    production_unchanged = pilot_runner._directory_metadata_binding(
        isolation["production_checkpoints"]["path"]
    ) == isolation["production_checkpoints"]
    communication_mod_unchanged = pilot_runner._binding_matches(
        isolation["communication_mod_config"]
    )
    if not production_unchanged or not communication_mod_unchanged:
        raise ScorerReplayRunnerBlocked("production isolation changed during execution")
    terminal = {
        "classification": completed.telemetry["classification"],
        "downstream_authority": copy.deepcopy(FALSE_AUTHORITY),
        "environment_accesses": MAX_ENVIRONMENT_ACCESSES,
        "optimizer_steps": {"full": 1, "scorer": 1},
        "production_isolation": {
            "communication_mod_unchanged": communication_mod_unchanged,
            "production_checkpoints_unchanged": production_unchanged,
        },
        "replay": copy.deepcopy(encoded.binding),
        "schema_version": "noncombat-card-scorer-optimizer-replay-ablation-terminal-v1",
        "support": {
            "attempted": MAX_ENVIRONMENT_ACCESSES,
            "censored": len(censored),
            "supported": len(decoded.episodes),
        },
        "verdict": completed.telemetry["classification"]["verdict"],
    }
    _write_canonical(output / "terminal.json", terminal)
    report = {
        "branch_artifacts": {
            "full_checkpoint": pilot_runner._file_binding(full_path),
            "scorer_checkpoint": pilot_runner._file_binding(scorer_path),
        },
        "censored_trajectories": list(censored),
        "downstream_authority": copy.deepcopy(FALSE_AUTHORITY),
        "preflight": preflight,
        "registration": registration,
        "replay": {
            "artifact": pilot_runner._file_binding(replay_path),
            "binding": copy.deepcopy(encoded.binding),
            "decoded_episode_count": len(decoded.episodes),
            "round_trip_exact": True,
        },
        "schema_version": "noncombat-card-scorer-optimizer-replay-ablation-report-v1",
        "telemetry": completed.telemetry,
        "terminal": terminal,
    }
    _write_canonical(output / "report.json", report)
    return terminal


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    register = subparsers.add_parser("register")
    register.add_argument("--repo-root", required=True)
    register.add_argument("--source-commit", required=True)
    register.add_argument("--parent-registration", default=str(DEFAULT_PARENT_REGISTRATION))
    register.add_argument("--entry-checkpoint", default=str(DEFAULT_ENTRY_CHECKPOINT))
    register.add_argument("--historical-checkpoint", default=str(DEFAULT_HISTORICAL_CHECKPOINT))
    register.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    register.add_argument("--registration", required=True)
    preflight = subparsers.add_parser("preflight")
    preflight.add_argument("--registration", required=True)
    run = subparsers.add_parser("run")
    run.add_argument("--registration", required=True)
    worker = subparsers.add_parser("scorer-worker")
    worker.add_argument("--registration", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "register":
            registration = build_registration(
                repo_root=args.repo_root,
                source_commit=args.source_commit,
                parent_registration_path=args.parent_registration,
                entry_checkpoint_path=args.entry_checkpoint,
                historical_checkpoint_path=args.historical_checkpoint,
                output_dir=args.output_dir,
            )
            print(_canonical_bytes(_write_canonical(args.registration, registration)).decode("ascii"))
            return 0
        registration = _read_canonical(args.registration)
        if args.command == "preflight":
            print(_canonical_bytes(preflight_registration(registration)).decode("ascii"))
            return 0
        if args.command == "run":
            preflight_registration(registration)
            completed = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    str(Path(__file__).resolve()),
                    "scorer-worker",
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
        ScorerReplayRunnerBlocked,
        ablation.ScorerReplayAblationBlocked,
        behavior_runner.BehaviorRunnerBlocked,
        pilot.CardOnlyPilotBlocked,
        pilot_runner.CardOnlyRunnerBlocked,
        replay.CardOptimizerReplayBlocked,
        successor.SuccessorRuntimeError,
        training.BehaviorSensitivityBlocked,
    ) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
