"""Run the one-step card baseline-clipping mechanism ablation."""

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


REGISTRATION_SCHEMA_VERSION = "noncombat-card-only-baseline-clipping-ablation-registration-v1"
_EARLY_NATIVE_HANDLES: list[Any] = []


def _early_preload_native() -> None:
    if len(sys.argv) < 2 or sys.argv[1] != "ablate-worker":
        return
    try:
        registration_path = Path(
            sys.argv[sys.argv.index("--registration") + 1]
        ).resolve()
        registration = json.loads(registration_path.read_text(encoding="ascii"))
        if registration.get("schema_version") != REGISTRATION_SCHEMA_VERSION:
            raise RuntimeError("ablation worker registration schema differs")
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
                raise RuntimeError("ablation worker dependency cycle differs")
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
            raise RuntimeError("ablation worker dependency graph differs")

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
            raise RuntimeError("ablation worker native specification is unavailable")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if module.adapter_api_version() != "sts-lightspeed-noncombat-adapter-v3":
            raise RuntimeError("ablation worker native API differs")
        sys.modules["sts_lightspeed_noncombat_adapter"] = module
    except (IndexError, KeyError, OSError, RuntimeError, ValueError) as exc:
        raise RuntimeError("ablation worker early native load failed") from exc


_early_preload_native()


from analysis_scripts import noncombat_card_acceptance_empirical_successor_runtime as successor
from analysis_scripts import noncombat_card_only_baseline_clipping_ablation as ablation
from analysis_scripts import noncombat_card_only_behavior_sensitivity_diagnostic as diagnostic
from analysis_scripts import noncombat_card_only_behavior_sensitivity_runner as behavior_runner
from analysis_scripts import noncombat_card_only_behavior_sensitivity_training as training
from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot as pilot
from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot_runner as pilot_runner


MAX_CHARGED_SECONDS = 7_200.0
MAX_ENVIRONMENT_ACCESSES = 64
MEAN_JOINT_TV_THRESHOLD = 0.001
APPLIED_GRADIENT_COSINE_THRESHOLD = 0.99
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
    "seed_access": True,
    "training": True,
}
SOURCE_PATHS = tuple(
    sorted(
        set(behavior_runner.SOURCE_PATHS)
        | {
            "analysis_scripts/noncombat_card_only_baseline_clipping_ablation.py",
            "analysis_scripts/noncombat_card_only_baseline_clipping_ablation_runner.py",
            "analysis_scripts/noncombat_card_only_behavior_sensitivity_diagnostic.py",
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
    "reports/noncombat_card_only_baseline_clipping_ablation_20260813_r1"
)


class BaselineClippingRunnerBlocked(RuntimeError):
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
        raise BaselineClippingRunnerBlocked("runner artifact is not canonical") from exc


def _read_canonical(path: Path | str) -> dict[str, Any]:
    source = Path(path).resolve()
    payload = source.read_bytes()
    try:
        value = json.loads(payload.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BaselineClippingRunnerBlocked(f"invalid JSON artifact: {source}") from exc
    if not isinstance(value, dict) or _canonical_bytes(value) != payload:
        raise BaselineClippingRunnerBlocked(f"artifact is not canonical: {source}")
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
        raise BaselineClippingRunnerBlocked("registration requires current HEAD")
    parent_path = Path(parent_registration_path).resolve()
    parent = behavior_runner.validate_registration(_read_canonical(parent_path))
    entry_path = Path(entry_checkpoint_path).resolve()
    historical_path = Path(historical_checkpoint_path).resolve()
    output = Path(output_dir).resolve()
    production_root = Path(
        parent["production_isolation"]["production_checkpoints"]["path"]
    ).resolve()
    if output == production_root or production_root in output.parents:
        raise BaselineClippingRunnerBlocked("output overlaps production checkpoints")
    seeds = list(parent["schedule"]["training_chunk_seeds"][0])
    return validate_registration(
        {
            "configuration": {
                "applied_gradient_cosine_threshold": APPLIED_GRADIENT_COSINE_THRESHOLD,
                "entry_chunk_index": training.FIRST_CHUNK_INDEX,
                "maximum_censored_trajectories": training.MAX_CENSORED_TRAJECTORIES,
                "maximum_charged_seconds": MAX_CHARGED_SECONDS,
                "maximum_environment_accesses": MAX_ENVIRONMENT_ACCESSES,
                "mean_joint_total_variation_threshold": MEAN_JOINT_TV_THRESHOLD,
                "minimum_supported_trajectories": successor.MIN_CANDIDATE_TRAJECTORIES_PER_CHUNK,
                "optimizer_steps_per_branch": 1,
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
                "shared_trajectory_seeds": seeds,
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
        raise BaselineClippingRunnerBlocked("registration fields differ")
    if registration["configuration"] != {
        "applied_gradient_cosine_threshold": APPLIED_GRADIENT_COSINE_THRESHOLD,
        "entry_chunk_index": training.FIRST_CHUNK_INDEX,
        "maximum_censored_trajectories": training.MAX_CENSORED_TRAJECTORIES,
        "maximum_charged_seconds": MAX_CHARGED_SECONDS,
        "maximum_environment_accesses": MAX_ENVIRONMENT_ACCESSES,
        "mean_joint_total_variation_threshold": MEAN_JOINT_TV_THRESHOLD,
        "minimum_supported_trajectories": successor.MIN_CANDIDATE_TRAJECTORIES_PER_CHUNK,
        "optimizer_steps_per_branch": 1,
    }:
        raise BaselineClippingRunnerBlocked("registration configuration differs")
    if registration["downstream_authority"] != FALSE_AUTHORITY:
        raise BaselineClippingRunnerBlocked("registration authority differs")
    if registration["operations"] != OPERATIONS:
        raise BaselineClippingRunnerBlocked("registration operations differ")
    inputs = registration["inputs"]
    if not isinstance(inputs, dict) or set(inputs) != {
        "entry_checkpoint",
        "historical_checkpoint",
        "parent_registration",
    }:
        raise BaselineClippingRunnerBlocked("registration inputs differ")
    if any(
        not isinstance(binding, dict)
        or set(binding) != {"path", "sha256", "size_bytes"}
        for binding in inputs.values()
    ):
        raise BaselineClippingRunnerBlocked("registration input binding differs")
    source = registration["source"]
    if (
        not isinstance(source, dict)
        or set(source) != {"bindings", "commit", "repo_root"}
        or set(source["bindings"]) != set(SOURCE_PATHS)
        or not isinstance(source["commit"], str)
        or len(source["commit"]) != 40
    ):
        raise BaselineClippingRunnerBlocked("registration source differs")
    seeds = list(pilot_runner.CONSUMED_DEVELOPMENT_SEEDS)
    if registration["schedule"] != {
        "seed_status": "already-consumed-development-only",
        "shared_trajectory_seeds": seeds,
    }:
        raise BaselineClippingRunnerBlocked("registration schedule differs")
    if not isinstance(registration["output_dir"], str):
        raise BaselineClippingRunnerBlocked("registration output differs")
    if not isinstance(registration["native"], dict) or set(
        registration["native"]
    ) != {"identity", "manifest"}:
        raise BaselineClippingRunnerBlocked("registration native differs")
    if not isinstance(registration["policy_context"], dict) or set(
        registration["policy_context"]
    ) != {"bottled", "corpus"}:
        raise BaselineClippingRunnerBlocked("registration policy context differs")
    if not isinstance(registration["production_isolation"], dict) or set(
        registration["production_isolation"]
    ) != {"communication_mod_config", "production_checkpoints"}:
        raise BaselineClippingRunnerBlocked("registration isolation differs")
    return registration


def _load_bound_runtimes(
    registration: Mapping[str, Any],
) -> tuple[tuple[Any, ...], bytes, Any, Any, Any]:
    inputs = registration["inputs"]
    parent = behavior_runner.validate_registration(
        _read_canonical(inputs["parent_registration"]["path"])
    )
    probe_rows, initialized = behavior_runner._load_probe_and_entry(parent)
    entry_payload = Path(inputs["entry_checkpoint"]["path"]).read_bytes()
    clipped = training.restore_behavior_sensitivity_checkpoint(
        entry_payload, probe_rows=probe_rows, entry_model=initialized.entry_model
    )
    unclipped = training.restore_behavior_sensitivity_checkpoint(
        entry_payload, probe_rows=probe_rows, entry_model=initialized.entry_model
    )
    historical = training.restore_behavior_sensitivity_checkpoint(
        Path(inputs["historical_checkpoint"]["path"]).read_bytes(),
        probe_rows=probe_rows,
        entry_model=initialized.entry_model,
    )
    if (
        clipped.next_chunk_index != training.FIRST_CHUNK_INDEX
        or unclipped.next_chunk_index != training.FIRST_CHUNK_INDEX
        or historical.next_chunk_index != training.FIRST_CHUNK_INDEX + 1
    ):
        raise BaselineClippingRunnerBlocked("bound checkpoint coordinates differ")
    return probe_rows, entry_payload, clipped, unclipped, historical


def preflight_registration(
    value: Mapping[str, Any],
    *,
    process_observer: Callable[[], Sequence[Mapping[str, Any]]] = pilot_runner._forbidden_processes,
) -> dict[str, Any]:
    registration = validate_registration(value)
    root = Path(registration["source"]["repo_root"]).resolve()
    if pilot_runner._git(root, "rev-parse", "HEAD") != registration["source"]["commit"]:
        raise BaselineClippingRunnerBlocked("registered source is not current HEAD")
    if any(
        not pilot_runner._binding_matches(binding)
        for binding in registration["source"]["bindings"].values()
    ):
        raise BaselineClippingRunnerBlocked("registered source bytes differ")
    if any(
        not pilot_runner._binding_matches(binding)
        for binding in registration["inputs"].values()
    ):
        raise BaselineClippingRunnerBlocked("registered input bytes differ")
    parent = behavior_runner.validate_registration(
        _read_canonical(registration["inputs"]["parent_registration"]["path"])
    )
    if (
        parent["native"] != registration["native"]
        or parent["policy_context"] != registration["policy_context"]
        or parent["schedule"]["training_chunk_seeds"][0]
        != registration["schedule"]["shared_trajectory_seeds"]
    ):
        raise BaselineClippingRunnerBlocked("parent experiment binding differs")
    native = registration["native"]
    native_bindings = [
        native["manifest"],
        native["identity"]["module"],
        *native["identity"]["dependency_closure"]["dependencies"],
    ]
    if any(not pilot_runner._binding_matches(binding) for binding in native_bindings):
        raise BaselineClippingRunnerBlocked("registered native bytes differ")
    context = registration["policy_context"]
    corpus_binding = {
        key: context["corpus"][key] for key in ("path", "sha256", "size_bytes")
    }
    if not pilot_runner._binding_matches(corpus_binding):
        raise BaselineClippingRunnerBlocked("registered corpus bytes differ")
    if pilot_runner._bottled_identity(context["bottled"]["path"]) != context["bottled"]:
        raise BaselineClippingRunnerBlocked("registered Bottled checkout differs")
    isolation = registration["production_isolation"]
    if not pilot_runner._binding_matches(isolation["communication_mod_config"]):
        raise BaselineClippingRunnerBlocked("CommunicationMod configuration differs")
    if pilot_runner._directory_metadata_binding(
        isolation["production_checkpoints"]["path"]
    ) != isolation["production_checkpoints"]:
        raise BaselineClippingRunnerBlocked("production checkpoint metadata differs")
    if list(process_observer()):
        raise BaselineClippingRunnerBlocked("game or CommunicationMod process is active")
    output = Path(registration["output_dir"]).resolve()
    production_root = Path(isolation["production_checkpoints"]["path"]).resolve()
    if output.exists():
        raise BaselineClippingRunnerBlocked("output already exists")
    if output == production_root or production_root in output.parents:
        raise BaselineClippingRunnerBlocked("output overlaps production checkpoints")
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
        "registration_sha256": hashlib.sha256(
            _canonical_bytes(registration)
        ).hexdigest(),
        "schema_version": "noncombat-card-only-baseline-clipping-ablation-preflight-v1",
        "verdict": "preflight_passed",
    }


def classify_result(
    *,
    reproduction_exact: bool,
    clipped_behavior: Mapping[str, Any],
    unclipped_behavior: Mapping[str, Any],
    function_summary: Mapping[str, Any],
    applied_gradient_cosine: float,
) -> dict[str, Any]:
    checks = {
        "applied_gradient_material": float(applied_gradient_cosine)
        <= APPLIED_GRADIENT_COSINE_THRESHOLD,
        "branch_coverage": not bool(clipped_behavior["stop"])
        and not bool(unclipped_behavior["stop"]),
        "exact_action_material": int(function_summary["action_flips"]) > 0,
        "mean_joint_tv_material": float(
            function_summary["joint_total_variation"]["mean"]
        )
        >= MEAN_JOINT_TV_THRESHOLD,
        "reproduction_exact": bool(reproduction_exact),
    }
    material = any(
        checks[name]
        for name in (
            "applied_gradient_material",
            "exact_action_material",
            "mean_joint_tv_material",
        )
    )
    if not checks["reproduction_exact"]:
        verdict = "baseline_clipping_ablation_reproduction_failed"
    elif not checks["branch_coverage"]:
        verdict = "baseline_clipping_ablation_branch_collapse"
    elif material:
        verdict = "ready_to_propose_four_step_baseline_clipping_ablation"
    else:
        verdict = "baseline_clipping_not_material_in_one_step"
    return {"checks": checks, "material_effect": material, "verdict": verdict}


def execute(
    value: Mapping[str, Any],
    *,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
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
            "seed_count": len(registration["schedule"]["shared_trajectory_seeds"]),
            "source_commit": registration["source"]["commit"],
        },
    )
    probe_rows, entry_payload, clipped, unclipped, historical = _load_bound_runtimes(
        registration
    )
    environment_factory = pilot_runner._load_environment_factory(
        registration["native"]["identity"]
    )
    deadline = float(clock()) + registration["configuration"]["maximum_charged_seconds"]
    episodes = []
    for seed in registration["schedule"]["shared_trajectory_seeds"]:
        if float(clock()) > deadline:
            raise BaselineClippingRunnerBlocked("deadline reached during collection")
        episodes.append(
            successor.rollout_candidate_card_only_native_baseline_training_episode(
                clipped.bootstrap,
                environment_factory=environment_factory,
                seed=seed,
                deadline=deadline,
                clock=clock,
            )
        )
    completed = ablation.apply_shared_trajectory_ablation(
        clipped,
        unclipped,
        tuple(episodes),
        entry_checkpoint=entry_payload,
    )
    if len(completed.attempted_seeds) != MAX_ENVIRONMENT_ACCESSES:
        raise BaselineClippingRunnerBlocked("environment access count differs")
    clipped_model = pilot.encode_candidate_card_policy(completed.clipped_branch.bootstrap)
    unclipped_model = pilot.encode_candidate_card_policy(
        completed.unclipped_branch.bootstrap
    )
    historical_model = pilot.encode_candidate_card_policy(historical.bootstrap)
    reproduction_exact = clipped_model == historical_model

    clipped_surface = diagnostic._policy_surface(
        completed.clipped_branch.bootstrap, probe_rows
    )
    unclipped_surface = diagnostic._policy_surface(
        completed.unclipped_branch.bootstrap, probe_rows
    )
    function_rows = diagnostic._compare_surfaces(clipped_surface, unclipped_surface)
    function_summary = diagnostic._build_summary(function_rows)
    clipped_behavior = completed.telemetry["branches"]["clipped"]["behavior"]
    unclipped_behavior = completed.telemetry["branches"]["unclipped"]["behavior"]
    classification = classify_result(
        reproduction_exact=reproduction_exact,
        clipped_behavior=clipped_behavior,
        unclipped_behavior=unclipped_behavior,
        function_summary=function_summary,
        applied_gradient_cosine=completed.telemetry["gradient_comparison"][
            "applied_cosine"
        ],
    )
    clipped_checkpoint = training.encode_behavior_sensitivity_checkpoint(
        completed.clipped_branch
    )
    unclipped_checkpoint = training.encode_behavior_sensitivity_checkpoint(
        completed.unclipped_branch
    )
    (output / "clipped_checkpoint_005.json").write_bytes(clipped_checkpoint)
    (output / "unclipped_checkpoint_005.json").write_bytes(unclipped_checkpoint)
    terminal = {
        "classification": classification,
        "downstream_authority": copy.deepcopy(FALSE_AUTHORITY),
        "environment_accesses": len(completed.attempted_seeds),
        "optimizer_steps": {"clipped": 1, "unclipped": 1},
        "reproduction": {
            "actual_clipped_model_sha256": hashlib.sha256(clipped_model).hexdigest(),
            "exact": reproduction_exact,
            "expected_historical_model_sha256": hashlib.sha256(
                historical_model
            ).hexdigest(),
        },
        "rollback": "entry_checkpoint_004_and_native_simple_agent",
        "schema_version": "noncombat-card-only-baseline-clipping-ablation-terminal-v1",
        "support": {
            "attempted": len(completed.attempted_seeds),
            "censored": len(completed.censored_trajectories),
            "supported": len(completed.supported_seeds),
        },
        "verdict": classification["verdict"],
    }
    _write_canonical(output / "terminal.json", terminal)
    report = {
        "branch_artifacts": {
            "clipped_checkpoint": pilot_runner._file_binding(
                output / "clipped_checkpoint_005.json"
            ),
            "clipped_model_sha256": hashlib.sha256(clipped_model).hexdigest(),
            "unclipped_checkpoint": pilot_runner._file_binding(
                output / "unclipped_checkpoint_005.json"
            ),
            "unclipped_model_sha256": hashlib.sha256(unclipped_model).hexdigest(),
        },
        "censored_trajectories": copy.deepcopy(
            list(completed.censored_trajectories)
        ),
        "downstream_authority": copy.deepcopy(FALSE_AUTHORITY),
        "function_comparison": {
            "rows": list(function_rows),
            "summary": function_summary,
        },
        "preflight": preflight,
        "registration": registration,
        "schema_version": "noncombat-card-only-baseline-clipping-ablation-report-v1",
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
    register.add_argument(
        "--parent-registration", default=str(DEFAULT_PARENT_REGISTRATION)
    )
    register.add_argument("--entry-checkpoint", default=str(DEFAULT_ENTRY_CHECKPOINT))
    register.add_argument(
        "--historical-checkpoint", default=str(DEFAULT_HISTORICAL_CHECKPOINT)
    )
    register.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    register.add_argument("--registration", required=True)
    preflight = subparsers.add_parser("preflight")
    preflight.add_argument("--registration", required=True)
    run = subparsers.add_parser("run")
    run.add_argument("--registration", required=True)
    worker = subparsers.add_parser("ablate-worker")
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
            preflight_registration(registration)
            completed = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    str(Path(__file__).resolve()),
                    "ablate-worker",
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
        BaselineClippingRunnerBlocked,
        ablation.BaselineClippingAblationBlocked,
        behavior_runner.BehaviorRunnerBlocked,
        pilot.CardOnlyPilotBlocked,
        pilot_runner.CardOnlyRunnerBlocked,
        successor.SuccessorRuntimeError,
        training.BehaviorSensitivityBlocked,
    ) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
