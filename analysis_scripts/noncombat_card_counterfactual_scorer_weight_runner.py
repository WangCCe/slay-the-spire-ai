"""Staged scorer-weight card counterfactual development and audit runner."""

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


REGISTRATION_SCHEMA_VERSION = (
    "noncombat-card-counterfactual-scorer-weight-registration-v1"
)
_EARLY_NATIVE_HANDLES: list[Any] = []


def _is_direct_worker_invocation() -> bool:
    return (
        len(sys.argv) >= 2
        and sys.argv[1] == "run-worker"
        and Path(sys.argv[0]).resolve() == Path(__file__).resolve()
    )


def _early_preload_native() -> None:
    if not _is_direct_worker_invocation():
        return
    try:
        registration_path = Path(
            sys.argv[sys.argv.index("--registration") + 1]
        ).resolve()
        registration = json.loads(registration_path.read_text(encoding="ascii"))
        if registration.get("schema_version") != REGISTRATION_SCHEMA_VERSION:
            raise RuntimeError("scorer-weight worker registration schema differs")
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
                raise RuntimeError("scorer-weight dependency cycle differs")
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
            raise RuntimeError("scorer-weight dependency graph differs")
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
            raise RuntimeError("scorer-weight native spec is unavailable")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if module.adapter_api_version() != "sts-lightspeed-noncombat-adapter-v3":
            raise RuntimeError("scorer-weight native API differs")
        sys.modules["sts_lightspeed_noncombat_adapter"] = module
    except (IndexError, KeyError, OSError, RuntimeError, ValueError) as exc:
        raise RuntimeError("scorer-weight early native load failed") from exc


_early_preload_native()


from analysis_scripts import noncombat_card_counterfactual_ranking_training as training
from analysis_scripts import noncombat_card_counterfactual_ranking_training_runner as base_runner
from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot_runner as pilot_runner
from analysis_scripts import noncombat_simulator_adapter as adapter


PREFLIGHT_SCHEMA_VERSION = (
    "noncombat-card-counterfactual-scorer-weight-preflight-v1"
)
TERMINAL_SCHEMA_VERSION = (
    "noncombat-card-counterfactual-scorer-weight-terminal-v1"
)
MAX_CHARGED_SECONDS = 7_200.0
AUDIT_SEEDS = tuple(range(1024, 1032))
MAX_AUDIT_BRANCHES = 64
MAX_AUDIT_CENSORED_SEEDS = 1
MIN_AUDIT_SOURCE_STATES = 12
MAX_DATASET_BYTES = 64 * 1024 * 1024
DEFAULT_R2_REGISTRATION = Path(
    "reports/noncombat_card_counterfactual_ranking_training_20260813_r2_registration.json"
)
DEFAULT_R2_REPORT = Path(
    "reports/noncombat_card_counterfactual_ranking_training_20260813_r2/report.json"
)
DEFAULT_ENTRY_CHECKPOINT = base_runner.DEFAULT_ENTRY_CHECKPOINT
DEFAULT_OUTPUT_DIR = Path(
    "reports/noncombat_card_counterfactual_scorer_weight_20260813_r1"
)
BOUND_SOURCE_PATHS = tuple(
    sorted(
        set(base_runner.BOUND_SOURCE_PATHS)
        | {
            "analysis_scripts/noncombat_card_counterfactual_scorer_weight_runner.py",
        }
    )
)
FALSE_DOWNSTREAM_AUTHORITY = copy.deepcopy(base_runner.FALSE_DOWNSTREAM_AUTHORITY)
OPERATIONS = {
    **base_runner.OPERATIONS,
    "conditional_audit_access": True,
}


class ScorerWeightRunnerBlocked(RuntimeError):
    """Raised when the staged scorer-weight runner cannot proceed."""


def _configuration() -> dict[str, Any]:
    return {
        "maximum_audit_branches": MAX_AUDIT_BRANCHES,
        "maximum_audit_censored_seeds": MAX_AUDIT_CENSORED_SEEDS,
        "maximum_card_states_per_seed": training.MAX_CARD_STATES_PER_SEED,
        "maximum_charged_seconds": MAX_CHARGED_SECONDS,
        "maximum_dataset_bytes": MAX_DATASET_BYTES,
        "maximum_development_branches": training.MAX_HOLDOUT_BRANCHES,
        "maximum_development_censored_seeds": training.MAX_HOLDOUT_CENSORED_SEEDS,
        "maximum_train_branches": training.MAX_TRAIN_BRANCHES,
        "maximum_train_censored_seeds": training.MAX_TRAIN_CENSORED_SEEDS,
        "minimum_audit_source_states": MIN_AUDIT_SOURCE_STATES,
        "minimum_development_source_states": training.MIN_HOLDOUT_SOURCE_STATES,
        "minimum_train_source_states": training.MIN_TRAIN_SOURCE_STATES,
        "trainable_parameter_count": 128,
        "training_steps": training.TRAINING_STEPS,
    }


def _source_bindings(root: Path) -> dict[str, dict[str, Any]]:
    return {
        relative: pilot_runner._file_binding(root / relative)
        for relative in BOUND_SOURCE_PATHS
    }


def build_registration(
    *,
    repo_root: Path | str,
    source_commit: str,
    r2_registration_path: Path | str,
    r2_report_path: Path | str,
    entry_checkpoint_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    if pilot_runner._git(root, "cat-file", "-t", source_commit) != "commit":
        raise ScorerWeightRunnerBlocked("source commit is unavailable")
    r2_registration_path = Path(r2_registration_path).resolve()
    r2_registration = base_runner._read_canonical(r2_registration_path)
    r2_report_path = Path(r2_report_path).resolve()
    r2_report = base_runner._read_canonical(r2_report_path)
    if r2_report.get("verdict") != "card_counterfactual_ranking_training_not_ready":
        raise ScorerWeightRunnerBlocked("bound r2 verdict differs")
    output = Path(output_dir).resolve()
    checkpoint_root = base_runner.PRODUCTION_CHECKPOINT_ROOT.resolve()
    if output == checkpoint_root or checkpoint_root in output.parents:
        raise ScorerWeightRunnerBlocked("output overlaps production checkpoints")
    return validate_registration(
        {
            "configuration": _configuration(),
            "downstream_authority": copy.deepcopy(FALSE_DOWNSTREAM_AUTHORITY),
            "inputs": {
                "entry_checkpoint": pilot_runner._file_binding(
                    Path(entry_checkpoint_path).resolve()
                ),
                "r2_registration": pilot_runner._file_binding(
                    r2_registration_path
                ),
                "r2_report": pilot_runner._file_binding(r2_report_path),
            },
            "native": {
                "identity": copy.deepcopy(r2_registration["native"]["identity"])
            },
            "operations": copy.deepcopy(OPERATIONS),
            "output_dir": output.as_posix(),
            "production_isolation": copy.deepcopy(
                r2_registration["production_isolation"]
            ),
            "schedule": {
                "audit_access": "only_after_development_pass",
                "audit_seeds": list(AUDIT_SEEDS),
                "development_seeds": list(training.HOLDOUT_SEEDS),
                "seed_status": "already-consumed-development-only",
                "train_seeds": list(training.TRAIN_SEEDS),
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
    if not isinstance(value, Mapping):
        raise ScorerWeightRunnerBlocked("registration must be an object")
    registration = copy.deepcopy(dict(value))
    if set(registration) != {
        "configuration",
        "downstream_authority",
        "inputs",
        "native",
        "operations",
        "output_dir",
        "production_isolation",
        "schedule",
        "schema_version",
        "source",
    } or registration.get("schema_version") != REGISTRATION_SCHEMA_VERSION:
        raise ScorerWeightRunnerBlocked("registration fields differ")
    if registration["configuration"] != _configuration():
        raise ScorerWeightRunnerBlocked("configuration differs")
    if registration["downstream_authority"] != FALSE_DOWNSTREAM_AUTHORITY:
        raise ScorerWeightRunnerBlocked("authority differs")
    if registration["operations"] != OPERATIONS:
        raise ScorerWeightRunnerBlocked("operations differ")
    if registration["schedule"] != {
        "audit_access": "only_after_development_pass",
        "audit_seeds": list(AUDIT_SEEDS),
        "development_seeds": list(training.HOLDOUT_SEEDS),
        "seed_status": "already-consumed-development-only",
        "train_seeds": list(training.TRAIN_SEEDS),
    }:
        raise ScorerWeightRunnerBlocked("schedule differs")
    inputs = registration.get("inputs")
    if not isinstance(inputs, dict) or set(inputs) != {
        "entry_checkpoint",
        "r2_registration",
        "r2_report",
    }:
        raise ScorerWeightRunnerBlocked("inputs differ")
    source = registration.get("source")
    if not isinstance(source, dict) or set(source) != {
        "bindings",
        "commit",
        "repo_root",
    } or set(source.get("bindings", {})) != set(BOUND_SOURCE_PATHS):
        raise ScorerWeightRunnerBlocked("source differs")
    bindings = [*inputs.values(), *source["bindings"].values()]
    if any(
        not isinstance(binding, dict)
        or set(binding) != {"path", "sha256", "size_bytes"}
        for binding in bindings
    ):
        raise ScorerWeightRunnerBlocked("file bindings differ")
    native = registration.get("native")
    identity = native.get("identity") if isinstance(native, dict) else None
    if not isinstance(identity, dict) or identity.get(
        "adapter_api_version"
    ) != adapter.ADAPTER_API_VERSION:
        raise ScorerWeightRunnerBlocked("native identity differs")
    if not isinstance(registration.get("output_dir"), str):
        raise ScorerWeightRunnerBlocked("output differs")
    return registration


def _binding_matches(binding: Mapping[str, Any]) -> bool:
    return pilot_runner._file_binding(binding["path"]) == dict(binding)


def preflight_registration(
    value: Mapping[str, Any],
    *,
    process_observer: Callable[[], Sequence[Mapping[str, Any]]] = (
        pilot_runner._forbidden_processes
    ),
) -> dict[str, Any]:
    registration = validate_registration(value)
    source = registration["source"]
    root = Path(source["repo_root"]).resolve()
    if pilot_runner._git(root, "cat-file", "-t", source["commit"]) != "commit":
        raise ScorerWeightRunnerBlocked("registered source is unavailable")
    try:
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", source["commit"], "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ScorerWeightRunnerBlocked("registered source is not an ancestor") from exc
    if any(not _binding_matches(row) for row in source["bindings"].values()) or any(
        not _binding_matches(row) for row in registration["inputs"].values()
    ):
        raise ScorerWeightRunnerBlocked("registered source or input bytes differ")
    r2 = base_runner._read_canonical(
        registration["inputs"]["r2_registration"]["path"]
    )
    if r2["native"] != registration["native"] or r2[
        "production_isolation"
    ] != registration["production_isolation"]:
        raise ScorerWeightRunnerBlocked("r2 native or isolation binding differs")
    report = base_runner._read_canonical(registration["inputs"]["r2_report"]["path"])
    if report.get("verdict") != "card_counterfactual_ranking_training_not_ready":
        raise ScorerWeightRunnerBlocked("r2 report verdict differs")
    training.restore_entry_bootstrap(
        Path(registration["inputs"]["entry_checkpoint"]["path"]).read_bytes()
    )
    native = registration["native"]["identity"]
    if any(
        not _binding_matches(row)
        for row in [native["module"], *native["dependency_closure"]["dependencies"]]
    ):
        raise ScorerWeightRunnerBlocked("native bytes differ")
    if not base_runner.production_isolation_matches(registration):
        raise ScorerWeightRunnerBlocked("production isolation differs")
    if list(process_observer()):
        raise ScorerWeightRunnerBlocked("game or CommunicationMod is active")
    output = Path(registration["output_dir"]).resolve()
    checkpoint_root = Path(
        registration["production_isolation"]["production_checkpoints"]["path"]
    ).resolve()
    if output.exists() or output == checkpoint_root or checkpoint_root in output.parents:
        raise ScorerWeightRunnerBlocked("output boundary differs")
    return {
        "checks": {
            "audit_access_staged": True,
            "entry_and_r2_bound": True,
            "forbidden_processes_absent": True,
            "native_bytes_bound_without_loading": True,
            "production_isolation_bound": True,
            "source_bound": True,
        },
        "registration_sha256": hashlib.sha256(
            base_runner._canonical_bytes(registration)
        ).hexdigest(),
        "schema_version": PREFLIGHT_SCHEMA_VERSION,
        "verdict": "preflight_passed",
    }


def _collect(
    factory: Callable[[int], Any],
    *,
    name: str,
    seeds: Sequence[int],
    branches: int,
    censors: int,
    deadline: float,
    clock: Callable[[], float],
) -> training.CounterfactualPartition:
    try:
        return training.collect_counterfactual_partition(
            factory,
            name=name,
            seeds=seeds,
            max_action_branches=branches,
            max_censored_seeds=censors,
            max_card_states_per_seed=training.MAX_CARD_STATES_PER_SEED,
            deadline=deadline,
            clock=clock,
        )
    except training.CounterfactualRankingBlocked as exc:
        raise ScorerWeightRunnerBlocked(str(exc)) from exc


def _write_dataset(output: Path, partition: training.CounterfactualPartition) -> dict[str, Any]:
    payload = training.encode_counterfactual_partition(partition)
    if len(payload) > MAX_DATASET_BYTES:
        raise ScorerWeightRunnerBlocked("dataset exceeds registered byte bound")
    restored = training.restore_counterfactual_partition(payload)
    if training.encode_counterfactual_partition(restored) != payload:
        raise ScorerWeightRunnerBlocked("dataset restore differs")
    return base_runner._write_bytes(output, payload)


def execute(
    value: Mapping[str, Any],
    *,
    clock: Callable[[], float] = time.monotonic,
    process_observer: Callable[[], Sequence[Mapping[str, Any]]] = (
        pilot_runner._forbidden_processes
    ),
    environment_factory_loader: Callable[
        [Mapping[str, Any]], Callable[[int], Any]
    ] = pilot_runner._load_environment_factory,
) -> dict[str, Any]:
    registration = validate_registration(value)
    preflight = preflight_registration(registration, process_observer=process_observer)
    output = Path(registration["output_dir"]).resolve()
    output.mkdir(parents=False, exist_ok=False)
    base_runner._write_canonical(output / "registration.json", registration)
    base_runner._write_canonical(output / "preflight.json", preflight)
    started = float(clock())
    if not math.isfinite(started):
        raise ScorerWeightRunnerBlocked("runner clock is invalid")
    deadline = started + MAX_CHARGED_SECONDS
    factory = environment_factory_loader(registration["native"]["identity"])
    train = _collect(
        factory,
        name="train",
        seeds=training.TRAIN_SEEDS,
        branches=training.MAX_TRAIN_BRANCHES,
        censors=training.MAX_TRAIN_CENSORED_SEEDS,
        deadline=deadline,
        clock=clock,
    )
    development = _collect(
        factory,
        name="holdout",
        seeds=training.HOLDOUT_SEEDS,
        branches=training.MAX_HOLDOUT_BRANCHES,
        censors=training.MAX_HOLDOUT_CENSORED_SEEDS,
        deadline=deadline,
        clock=clock,
    )
    r2_report = base_runner._read_canonical(
        registration["inputs"]["r2_report"]["path"]
    )
    if training.compact_partition(train) != r2_report["datasets"]["train"] or (
        training.compact_partition(development)
        != r2_report["datasets"]["holdout"]
    ):
        raise ScorerWeightRunnerBlocked("reconstructed r2 dataset identity differs")
    if len(train.rows) < training.MIN_TRAIN_SOURCE_STATES or len(
        development.rows
    ) < training.MIN_HOLDOUT_SOURCE_STATES:
        raise ScorerWeightRunnerBlocked("train or development support floor is unmet")
    train_binding = _write_dataset(output / "train_dataset_full.json", train)
    development_binding = _write_dataset(
        output / "development_dataset_full.json", development
    )
    checkpoint_bytes = Path(
        registration["inputs"]["entry_checkpoint"]["path"]
    ).read_bytes()
    entry_bootstrap = training.restore_entry_bootstrap(checkpoint_bytes)
    trained_bootstrap = training.restore_entry_bootstrap(checkpoint_bytes)
    try:
        completed = training.train_scorer_weight_ranking(
            trained_bootstrap,
            train_rows=train.rows,
            development_rows=development.rows,
            training_steps=training.TRAINING_STEPS,
        )
    except training.CounterfactualRankingBlocked as exc:
        raise ScorerWeightRunnerBlocked(str(exc)) from exc
    model_binding = base_runner._write_bytes(
        output / "trained_model.json", completed.trained_model
    )
    development_passed = completed.report["verdict"] == (
        "card_counterfactual_scorer_weight_development_passed"
    )
    audit = None
    audit_partition = None
    audit_binding = None
    if development_passed:
        audit_partition = _collect(
            factory,
            name="audit",
            seeds=AUDIT_SEEDS,
            branches=MAX_AUDIT_BRANCHES,
            censors=MAX_AUDIT_CENSORED_SEEDS,
            deadline=deadline,
            clock=clock,
        )
        if len(audit_partition.rows) < MIN_AUDIT_SOURCE_STATES:
            raise ScorerWeightRunnerBlocked("audit support floor is unmet")
        audit_binding = _write_dataset(
            output / "audit_dataset_full.json", audit_partition
        )
        try:
            audit = training.audit_scorer_weight_model(
                entry_bootstrap, trained_bootstrap, audit_partition.rows
            )
        except training.CounterfactualRankingBlocked as exc:
            raise ScorerWeightRunnerBlocked(str(exc)) from exc
    if not base_runner.production_isolation_matches(registration):
        raise ScorerWeightRunnerBlocked("production isolation changed during run")
    if list(process_observer()):
        raise ScorerWeightRunnerBlocked("game or CommunicationMod started during run")
    elapsed = float(clock()) - started
    if not math.isfinite(elapsed) or elapsed < 0 or elapsed > MAX_CHARGED_SECONDS:
        raise ScorerWeightRunnerBlocked("charged time exceeds registration")
    ready = bool(
        development_passed
        and audit is not None
        and audit["verdict"] == "card_counterfactual_scorer_weight_audit_passed"
    )
    report = copy.deepcopy(completed.report)
    report.update(
        {
            "audit": audit,
            "audit_accessed": audit_partition is not None,
            "audit_dataset": audit_binding,
            "datasets": {
                "development": development_binding,
                "train": train_binding,
            },
            "downstream_authority": copy.deepcopy(FALSE_DOWNSTREAM_AUTHORITY),
            "execution": {
                "charged_seconds": elapsed,
                "operations": copy.deepcopy(OPERATIONS),
                "production_isolation_passed": True,
                "source_commit": registration["source"]["commit"],
            },
            "trained_model": model_binding,
            "verdict": (
                "card_counterfactual_scorer_weight_ready_for_fresh_eval_proposal"
                if ready
                else "card_counterfactual_scorer_weight_not_ready"
            ),
        }
    )
    report_binding = base_runner._write_canonical(output / "report.json", report)
    action_branches = train.action_branches + development.action_branches + (
        0 if audit_partition is None else audit_partition.action_branches
    )
    terminal = {
        "action_branches": action_branches,
        "audit_accessed": audit_partition is not None,
        "downstream_authority": copy.deepcopy(FALSE_DOWNSTREAM_AUTHORITY),
        "optimizer_steps": training.TRAINING_STEPS,
        "report": report_binding,
        "rollback": "tracked_r7_checkpoint_and_native_simple_agent",
        "schema_version": TERMINAL_SCHEMA_VERSION,
        "verdict": report["verdict"],
    }
    base_runner._write_canonical(output / "terminal.json", terminal)
    return terminal


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    register = subparsers.add_parser("register")
    register.add_argument("--repo-root", required=True)
    register.add_argument("--source-commit", required=True)
    register.add_argument("--r2-registration", default=str(DEFAULT_R2_REGISTRATION))
    register.add_argument("--r2-report", default=str(DEFAULT_R2_REPORT))
    register.add_argument("--entry-checkpoint", default=str(DEFAULT_ENTRY_CHECKPOINT))
    register.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    register.add_argument("--registration", required=True)
    for name in ("preflight", "run", "run-worker"):
        command = subparsers.add_parser(name)
        command.add_argument("--registration", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "register":
            registration = build_registration(
                repo_root=args.repo_root,
                source_commit=args.source_commit,
                r2_registration_path=args.r2_registration,
                r2_report_path=args.r2_report,
                entry_checkpoint_path=args.entry_checkpoint,
                output_dir=args.output_dir,
            )
            binding = base_runner._write_canonical(args.registration, registration)
            print(base_runner._canonical_bytes(binding).decode("ascii"))
            return 0
        registration = base_runner._read_canonical(args.registration)
        if args.command == "preflight":
            print(base_runner._canonical_bytes(preflight_registration(registration)).decode("ascii"))
            return 0
        if args.command == "run":
            preflight_registration(registration)
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
                check=False,
            )
            return completed.returncode
        terminal = execute(registration)
        print(base_runner._canonical_bytes(terminal).decode("ascii"))
        return 0
    except (ScorerWeightRunnerBlocked, OSError, subprocess.SubprocessError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
