"""One-shot runner for consumed-seed card counterfactual ranking training."""

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
    "noncombat-card-counterfactual-ranking-training-registration-v1"
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
            raise RuntimeError("ranking worker registration schema differs")
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
                raise RuntimeError("ranking worker dependency cycle differs")
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
            raise RuntimeError("ranking worker dependency graph differs")
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
            raise RuntimeError("ranking worker native spec is unavailable")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if module.adapter_api_version() != "sts-lightspeed-noncombat-adapter-v3":
            raise RuntimeError("ranking worker native API differs")
        sys.modules["sts_lightspeed_noncombat_adapter"] = module
    except (IndexError, KeyError, OSError, RuntimeError, ValueError) as exc:
        raise RuntimeError("ranking worker early native load failed") from exc


_early_preload_native()


from analysis_scripts import noncombat_card_action_counterfactual_credit_runner as credit_runner
from analysis_scripts import noncombat_card_counterfactual_ranking_training as training
from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot_runner as pilot_runner
from analysis_scripts import noncombat_simulator_adapter as adapter


PREFLIGHT_SCHEMA_VERSION = (
    "noncombat-card-counterfactual-ranking-training-preflight-v1"
)
TERMINAL_SCHEMA_VERSION = (
    "noncombat-card-counterfactual-ranking-training-terminal-v1"
)
MAX_CHARGED_SECONDS = 7_200.0
DEFAULT_PARENT_REGISTRATION = Path(
    "reports/noncombat_card_action_counterfactual_credit_poc_20260813_r1_registration.json"
)
DEFAULT_ENTRY_CHECKPOINT = Path(
    "reports/noncombat_card_only_native_baseline_rl_pilot_20260813_r7/checkpoint_004.json"
)
DEFAULT_OUTPUT_DIR = Path(
    "reports/noncombat_card_counterfactual_ranking_training_20260813_r1"
)
COMMUNICATION_MOD_CONFIG = credit_runner.COMMUNICATION_MOD_CONFIG
PRODUCTION_CHECKPOINT_ROOT = credit_runner.PRODUCTION_CHECKPOINT_ROOT
BOUND_SOURCE_PATHS = (
    "analysis_scripts/noncombat_card_acceptance_empirical_successor_runtime.py",
    "analysis_scripts/noncombat_card_acceptance_objective.py",
    "analysis_scripts/noncombat_card_action_counterfactual_credit.py",
    "analysis_scripts/noncombat_card_action_counterfactual_credit_runner.py",
    "analysis_scripts/noncombat_card_counterfactual_ranking_training.py",
    "analysis_scripts/noncombat_card_counterfactual_ranking_training_runner.py",
    "analysis_scripts/noncombat_card_only_native_baseline_rl_pilot.py",
    "analysis_scripts/noncombat_card_only_native_baseline_rl_pilot_runner.py",
    "analysis_scripts/noncombat_formal_reward_contract.py",
    "analysis_scripts/noncombat_simulator_adapter.py",
    "analysis_scripts/noncombat_state_conditioned_policy_input.py",
)
FALSE_DOWNSTREAM_AUTHORITY = {
    name: False
    for name in (
        "causal_claim",
        "communication_mod",
        "formal_rl",
        "fresh_evaluation",
        "further_training",
        "gameplay",
        "ope",
        "policy_quality",
        "production_model_loading",
        "promotion",
        "qualification",
    )
}
OPERATIONS = {
    "communication_mod": False,
    "consumed_holdout_evaluation": True,
    "environment_construction": True,
    "fresh_evaluation": False,
    "gameplay": False,
    "model_fitting": True,
    "model_loading": True,
    "native_loading": True,
    "ope": False,
    "production_model_loading": False,
    "seed_access": True,
    "training": True,
}


class RankingRunnerBlocked(RuntimeError):
    """Raised when the one-shot ranking runner cannot preserve its contract."""


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
        raise RankingRunnerBlocked("runner artifact is not canonical") from exc


def _read_canonical(path: Path | str) -> dict[str, Any]:
    source = Path(path).resolve()
    try:
        payload = source.read_bytes()
        value = json.loads(payload.decode("ascii"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RankingRunnerBlocked(f"invalid canonical JSON: {source}") from exc
    if not isinstance(value, dict) or _canonical_bytes(value) != payload:
        raise RankingRunnerBlocked(f"noncanonical JSON: {source}")
    return value


def _write_bytes(path: Path | str, payload: bytes) -> dict[str, Any]:
    target = Path(path).resolve()
    if not payload:
        raise RankingRunnerBlocked("artifact bytes are empty")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, target)
    return {
        "path": target.as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _write_canonical(path: Path | str, value: Mapping[str, Any]) -> dict[str, Any]:
    return _write_bytes(path, _canonical_bytes(dict(value)))


def _source_bindings(root: Path) -> dict[str, dict[str, Any]]:
    return {
        relative: pilot_runner._file_binding(root / relative)
        for relative in BOUND_SOURCE_PATHS
    }


def _parent_native(parent: Mapping[str, Any]) -> dict[str, Any]:
    native = parent.get("native")
    identity = native.get("identity") if isinstance(native, Mapping) else None
    if not isinstance(identity, dict) or identity.get(
        "adapter_api_version"
    ) != adapter.ADAPTER_API_VERSION:
        raise RankingRunnerBlocked("parent native identity differs")
    return copy.deepcopy(identity)


def _configuration() -> dict[str, Any]:
    return {
        "maximum_card_states_per_seed": training.MAX_CARD_STATES_PER_SEED,
        "maximum_charged_seconds": MAX_CHARGED_SECONDS,
        "maximum_holdout_branches": training.MAX_HOLDOUT_BRANCHES,
        "maximum_holdout_censored_seeds": training.MAX_HOLDOUT_CENSORED_SEEDS,
        "maximum_train_branches": training.MAX_TRAIN_BRANCHES,
        "maximum_train_censored_seeds": training.MAX_TRAIN_CENSORED_SEEDS,
        "minimum_holdout_source_states": training.MIN_HOLDOUT_SOURCE_STATES,
        "minimum_train_source_states": training.MIN_TRAIN_SOURCE_STATES,
        "training_steps": training.TRAINING_STEPS,
    }


def build_registration(
    *,
    repo_root: Path | str,
    source_commit: str,
    parent_registration_path: Path | str,
    entry_checkpoint_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    if pilot_runner._git(root, "cat-file", "-t", source_commit) != "commit":
        raise RankingRunnerBlocked("source commit is unavailable")
    parent_path = Path(parent_registration_path).resolve()
    parent = _read_canonical(parent_path)
    entry_path = Path(entry_checkpoint_path).resolve()
    output = Path(output_dir).resolve()
    checkpoint_root = PRODUCTION_CHECKPOINT_ROOT.resolve()
    if output == checkpoint_root or checkpoint_root in output.parents:
        raise RankingRunnerBlocked("output overlaps production checkpoints")
    return validate_registration(
        {
            "configuration": _configuration(),
            "downstream_authority": copy.deepcopy(FALSE_DOWNSTREAM_AUTHORITY),
            "inputs": {
                "entry_checkpoint": pilot_runner._file_binding(entry_path),
                "parent_registration": pilot_runner._file_binding(parent_path),
            },
            "native": {"identity": _parent_native(parent)},
            "operations": copy.deepcopy(OPERATIONS),
            "output_dir": output.as_posix(),
            "production_isolation": {
                "communication_mod_config": pilot_runner._file_binding(
                    COMMUNICATION_MOD_CONFIG
                ),
                "production_checkpoints": (
                    pilot_runner._directory_metadata_binding(checkpoint_root)
                ),
            },
            "schedule": {
                "holdout_seeds": list(training.HOLDOUT_SEEDS),
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
        raise RankingRunnerBlocked("registration must be an object")
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
        raise RankingRunnerBlocked("registration fields differ")
    if registration["configuration"] != _configuration():
        raise RankingRunnerBlocked("registration configuration differs")
    if registration["downstream_authority"] != FALSE_DOWNSTREAM_AUTHORITY:
        raise RankingRunnerBlocked("registration authority differs")
    if registration["operations"] != OPERATIONS:
        raise RankingRunnerBlocked("registration operations differ")
    if registration["schedule"] != {
        "holdout_seeds": list(training.HOLDOUT_SEEDS),
        "seed_status": "already-consumed-development-only",
        "train_seeds": list(training.TRAIN_SEEDS),
    }:
        raise RankingRunnerBlocked("registration schedule differs")
    inputs = registration.get("inputs")
    if not isinstance(inputs, dict) or set(inputs) != {
        "entry_checkpoint",
        "parent_registration",
    }:
        raise RankingRunnerBlocked("registration inputs differ")
    source = registration.get("source")
    if not isinstance(source, dict) or set(source) != {
        "bindings",
        "commit",
        "repo_root",
    } or set(source.get("bindings", {})) != set(BOUND_SOURCE_PATHS):
        raise RankingRunnerBlocked("registration source differs")
    if not isinstance(source["commit"], str) or len(source["commit"]) != 40:
        raise RankingRunnerBlocked("registration source commit differs")
    bindings = [*inputs.values(), *source["bindings"].values()]
    if any(
        not isinstance(binding, dict)
        or set(binding) != {"path", "sha256", "size_bytes"}
        for binding in bindings
    ):
        raise RankingRunnerBlocked("registration file bindings differ")
    native = registration.get("native")
    identity = native.get("identity") if isinstance(native, dict) else None
    if not isinstance(identity, dict) or identity.get(
        "adapter_api_version"
    ) != adapter.ADAPTER_API_VERSION:
        raise RankingRunnerBlocked("registration native differs")
    native_bindings = [
        identity.get("module"),
        *identity.get("dependency_closure", {}).get("dependencies", ()),
    ]
    if any(
        not isinstance(binding, dict)
        or set(binding) != {"path", "sha256", "size_bytes"}
        for binding in native_bindings
    ):
        raise RankingRunnerBlocked("native bindings differ")
    isolation = registration.get("production_isolation")
    if not isinstance(isolation, dict) or set(isolation) != {
        "communication_mod_config",
        "production_checkpoints",
    }:
        raise RankingRunnerBlocked("production isolation differs")
    if not isinstance(registration.get("output_dir"), str):
        raise RankingRunnerBlocked("registration output differs")
    return registration


def _binding_matches(binding: Mapping[str, Any]) -> bool:
    return pilot_runner._file_binding(binding["path"]) == dict(binding)


def production_isolation_matches(value: Mapping[str, Any]) -> bool:
    isolation = value["production_isolation"]
    return _binding_matches(isolation["communication_mod_config"]) and (
        pilot_runner._directory_metadata_binding(
            isolation["production_checkpoints"]["path"]
        )
        == isolation["production_checkpoints"]
    )


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
        raise RankingRunnerBlocked("registered source is unavailable")
    try:
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", source["commit"], "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RankingRunnerBlocked("registered source is not an ancestor") from exc
    if any(not _binding_matches(row) for row in source["bindings"].values()):
        raise RankingRunnerBlocked("registered source bytes differ")
    if any(not _binding_matches(row) for row in registration["inputs"].values()):
        raise RankingRunnerBlocked("registered input bytes differ")
    parent = _read_canonical(
        registration["inputs"]["parent_registration"]["path"]
    )
    if _parent_native(parent) != registration["native"]["identity"]:
        raise RankingRunnerBlocked("parent native identity differs")
    native = registration["native"]["identity"]
    native_bindings = [native["module"], *native["dependency_closure"]["dependencies"]]
    if any(not _binding_matches(row) for row in native_bindings):
        raise RankingRunnerBlocked("registered native bytes differ")
    entry_bytes = Path(
        registration["inputs"]["entry_checkpoint"]["path"]
    ).read_bytes()
    training.restore_entry_bootstrap(entry_bytes)
    if not production_isolation_matches(registration):
        raise RankingRunnerBlocked("production isolation differs")
    if list(process_observer()):
        raise RankingRunnerBlocked("game or CommunicationMod is active")
    output = Path(registration["output_dir"]).resolve()
    checkpoint_root = Path(
        registration["production_isolation"]["production_checkpoints"]["path"]
    ).resolve()
    if output.exists() or output == checkpoint_root or checkpoint_root in output.parents:
        raise RankingRunnerBlocked("output boundary differs")
    return {
        "checks": {
            "consumed_partitions_disjoint_and_bound": True,
            "entry_checkpoint_bound": True,
            "forbidden_processes_absent": True,
            "native_bytes_bound_without_loading": True,
            "production_isolation_bound": True,
            "source_bytes_bound": True,
        },
        "registration_sha256": hashlib.sha256(
            _canonical_bytes(registration)
        ).hexdigest(),
        "schema_version": PREFLIGHT_SCHEMA_VERSION,
        "verdict": "preflight_passed",
    }


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
    preflight = preflight_registration(
        registration, process_observer=process_observer
    )
    output = Path(registration["output_dir"]).resolve()
    output.mkdir(parents=False, exist_ok=False)
    _write_canonical(output / "registration.json", registration)
    _write_canonical(output / "preflight.json", preflight)
    started = float(clock())
    if not math.isfinite(started):
        raise RankingRunnerBlocked("runner clock is invalid")
    deadline = started + MAX_CHARGED_SECONDS
    factory = environment_factory_loader(registration["native"]["identity"])
    configuration = registration["configuration"]
    schedule = registration["schedule"]
    try:
        train = training.collect_counterfactual_partition(
            factory,
            name="train",
            seeds=schedule["train_seeds"],
            max_action_branches=configuration["maximum_train_branches"],
            max_censored_seeds=configuration["maximum_train_censored_seeds"],
            max_card_states_per_seed=configuration["maximum_card_states_per_seed"],
            deadline=deadline,
            clock=clock,
        )
        holdout = training.collect_counterfactual_partition(
            factory,
            name="holdout",
            seeds=schedule["holdout_seeds"],
            max_action_branches=configuration["maximum_holdout_branches"],
            max_censored_seeds=configuration["maximum_holdout_censored_seeds"],
            max_card_states_per_seed=configuration["maximum_card_states_per_seed"],
            deadline=deadline,
            clock=clock,
        )
    except training.CounterfactualRankingBlocked as exc:
        raise RankingRunnerBlocked(str(exc)) from exc
    train_compact = training.compact_partition(train)
    holdout_compact = training.compact_partition(holdout)
    _write_canonical(output / "train_dataset.json", train_compact)
    _write_canonical(output / "holdout_dataset.json", holdout_compact)
    if len(train.rows) < configuration["minimum_train_source_states"]:
        raise RankingRunnerBlocked("train source support floor is unmet")
    if len(holdout.rows) < configuration["minimum_holdout_source_states"]:
        raise RankingRunnerBlocked("holdout source support floor is unmet")
    entry_bytes = Path(
        registration["inputs"]["entry_checkpoint"]["path"]
    ).read_bytes()
    bootstrap = training.restore_entry_bootstrap(entry_bytes)
    try:
        completed = training.train_counterfactual_ranking(
            bootstrap,
            train_rows=train.rows,
            holdout_rows=holdout.rows,
            training_steps=configuration["training_steps"],
        )
    except training.CounterfactualRankingBlocked as exc:
        raise RankingRunnerBlocked(str(exc)) from exc
    if not production_isolation_matches(registration):
        raise RankingRunnerBlocked("production isolation changed during training")
    if list(process_observer()):
        raise RankingRunnerBlocked("game or CommunicationMod started during training")
    elapsed = float(clock()) - started
    if not math.isfinite(elapsed) or elapsed < 0 or elapsed > MAX_CHARGED_SECONDS:
        raise RankingRunnerBlocked("charged time exceeds registration")
    trained_model = _write_bytes(output / "trained_model.json", completed.trained_model)
    report = copy.deepcopy(completed.report)
    report["datasets"] = {"holdout": holdout_compact, "train": train_compact}
    report["downstream_authority"] = copy.deepcopy(FALSE_DOWNSTREAM_AUTHORITY)
    report["execution"] = {
        "charged_seconds": elapsed,
        "operations": copy.deepcopy(OPERATIONS),
        "production_isolation_passed": True,
        "source_commit": registration["source"]["commit"],
    }
    report["trained_model"] = trained_model
    report_binding = _write_canonical(output / "report.json", report)
    terminal = {
        "action_branches": train.action_branches + holdout.action_branches,
        "downstream_authority": copy.deepcopy(FALSE_DOWNSTREAM_AUTHORITY),
        "optimizer_steps": configuration["training_steps"],
        "report": report_binding,
        "rollback": "tracked_r7_checkpoint_and_native_simple_agent",
        "schema_version": TERMINAL_SCHEMA_VERSION,
        "verdict": completed.report["verdict"],
    }
    _write_canonical(output / "terminal.json", terminal)
    return terminal


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    register = subparsers.add_parser("register")
    register.add_argument("--repo-root", required=True)
    register.add_argument("--source-commit", required=True)
    register.add_argument("--parent-registration", default=str(DEFAULT_PARENT_REGISTRATION))
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
                parent_registration_path=args.parent_registration,
                entry_checkpoint_path=args.entry_checkpoint,
                output_dir=args.output_dir,
            )
            binding = _write_canonical(args.registration, registration)
            print(_canonical_bytes(binding).decode("ascii"))
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
                    "run-worker",
                    "--registration",
                    str(Path(args.registration).resolve()),
                ],
                cwd=Path(registration["source"]["repo_root"]),
                check=False,
            )
            return completed.returncode
        terminal = execute(registration)
        print(_canonical_bytes(terminal).decode("ascii"))
        return 0
    except (RankingRunnerBlocked, OSError, subprocess.SubprocessError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
