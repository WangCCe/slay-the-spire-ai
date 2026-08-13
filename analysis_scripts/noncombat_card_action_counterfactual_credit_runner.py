"""Thin one-shot runner for card action counterfactual credit evidence."""

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
    "noncombat-card-action-counterfactual-credit-registration-v1"
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
            raise RuntimeError("counterfactual worker registration schema differs")
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
                raise RuntimeError("counterfactual worker dependency cycle differs")
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
            raise RuntimeError("counterfactual worker dependency graph differs")

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
            raise RuntimeError("counterfactual worker native spec is unavailable")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if module.adapter_api_version() != "sts-lightspeed-noncombat-adapter-v3":
            raise RuntimeError("counterfactual worker native API differs")
        sys.modules["sts_lightspeed_noncombat_adapter"] = module
    except (IndexError, KeyError, OSError, RuntimeError, ValueError) as exc:
        raise RuntimeError("counterfactual worker early native load failed") from exc


_early_preload_native()


from analysis_scripts import noncombat_card_action_counterfactual_credit as credit
from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot_runner as pilot_runner
from analysis_scripts import noncombat_simulator_adapter as adapter


PREFLIGHT_SCHEMA_VERSION = (
    "noncombat-card-action-counterfactual-credit-preflight-v1"
)
TERMINAL_SCHEMA_VERSION = "noncombat-card-action-counterfactual-credit-terminal-v1"
MAX_CHARGED_SECONDS = 7_200.0
DEFAULT_PARENT_REGISTRATION = Path(
    "reports/noncombat_card_only_behavior_sensitivity_training_20260813_r1_registration.json"
)
DEFAULT_OUTPUT_DIR = Path(
    "reports/noncombat_card_action_counterfactual_credit_poc_20260813_r1"
)
COMMUNICATION_MOD_CONFIG = Path(
    r"C:\Users\20571\AppData\Local\ModTheSpire\CommunicationMod\config.properties"
)
PRODUCTION_CHECKPOINT_ROOT = Path(
    r"D:\SteamLibrary\steamapps\common\SlayTheSpire\checkpoints"
)
BOUND_SOURCE_PATHS = (
    "analysis_scripts/noncombat_card_acceptance_empirical_successor_runtime.py",
    "analysis_scripts/noncombat_card_action_counterfactual_credit.py",
    "analysis_scripts/noncombat_card_action_counterfactual_credit_runner.py",
    "analysis_scripts/noncombat_card_only_native_baseline_rl_pilot_runner.py",
    "analysis_scripts/noncombat_formal_reward_contract.py",
    "analysis_scripts/noncombat_simulator_adapter.py",
)
OPERATIONS = {
    "communication_mod": False,
    "environment_construction": True,
    "evaluation": False,
    "fresh_seed_access": False,
    "gameplay": False,
    "model_fitting": False,
    "model_loading": False,
    "native_loading": True,
    "ope": False,
    "seed_access": True,
    "training": False,
}


class CounterfactualRunnerBlocked(RuntimeError):
    """Raised when the bounded runner cannot preserve its registration."""


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
        raise CounterfactualRunnerBlocked("artifact is not canonical") from exc


def _read_canonical(path: Path | str) -> dict[str, Any]:
    source = Path(path).resolve()
    try:
        payload = source.read_bytes()
        value = json.loads(payload.decode("ascii"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CounterfactualRunnerBlocked(f"invalid canonical JSON: {source}") from exc
    if not isinstance(value, dict) or _canonical_bytes(value) != payload:
        raise CounterfactualRunnerBlocked(f"noncanonical JSON: {source}")
    return value


def _write_canonical(path: Path | str, value: Mapping[str, Any]) -> dict[str, Any]:
    target = Path(path).resolve()
    payload = _canonical_bytes(dict(value))
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, target)
    return {
        "path": target.as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _source_bindings(root: Path) -> dict[str, dict[str, Any]]:
    return {
        relative: pilot_runner._file_binding(root / relative)
        for relative in BOUND_SOURCE_PATHS
    }


def _parent_native_identity(parent: Mapping[str, Any]) -> dict[str, Any]:
    native = parent.get("native")
    identity = native.get("identity") if isinstance(native, Mapping) else None
    if not isinstance(identity, dict) or identity.get(
        "adapter_api_version"
    ) != adapter.ADAPTER_API_VERSION:
        raise CounterfactualRunnerBlocked("parent native identity differs")
    return copy.deepcopy(identity)


def build_registration(
    *,
    repo_root: Path | str,
    source_commit: str,
    parent_registration_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    if pilot_runner._git(root, "cat-file", "-t", source_commit) != "commit":
        raise CounterfactualRunnerBlocked("source commit is unavailable")
    parent_path = Path(parent_registration_path).resolve()
    parent = _read_canonical(parent_path)
    output = Path(output_dir).resolve()
    checkpoint_root = PRODUCTION_CHECKPOINT_ROOT.resolve()
    if output == checkpoint_root or checkpoint_root in output.parents:
        raise CounterfactualRunnerBlocked("output overlaps production checkpoints")
    return validate_registration(
        {
            "configuration": {
                "maximum_action_branches": credit.MAX_ACTION_BRANCHES,
                "maximum_card_states_per_seed": credit.MAX_CARD_STATES_PER_SEED,
                "maximum_charged_seconds": MAX_CHARGED_SECONDS,
                "maximum_decisions_per_continuation": (
                    credit.MAX_DECISIONS_PER_CONTINUATION
                ),
                "minimum_complete_source_states": (
                    credit.MIN_COMPLETE_SOURCE_STATES
                ),
                "minimum_informative_source_states": (
                    credit.MIN_INFORMATIVE_SOURCE_STATES
                ),
            },
            "downstream_authority": copy.deepcopy(
                credit.FALSE_DOWNSTREAM_AUTHORITY
            ),
            "native": {
                "identity": _parent_native_identity(parent),
                "parent_registration": pilot_runner._file_binding(parent_path),
            },
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
                "seed_status": "already-consumed-development-only",
                "seeds": list(credit.CONSUMED_DEVELOPMENT_SEEDS),
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
        raise CounterfactualRunnerBlocked("registration must be an object")
    registration = copy.deepcopy(dict(value))
    if set(registration) != {
        "configuration",
        "downstream_authority",
        "native",
        "operations",
        "output_dir",
        "production_isolation",
        "schedule",
        "schema_version",
        "source",
    } or registration.get("schema_version") != REGISTRATION_SCHEMA_VERSION:
        raise CounterfactualRunnerBlocked("registration fields differ")
    if registration["configuration"] != {
        "maximum_action_branches": credit.MAX_ACTION_BRANCHES,
        "maximum_card_states_per_seed": credit.MAX_CARD_STATES_PER_SEED,
        "maximum_charged_seconds": MAX_CHARGED_SECONDS,
        "maximum_decisions_per_continuation": (
            credit.MAX_DECISIONS_PER_CONTINUATION
        ),
        "minimum_complete_source_states": credit.MIN_COMPLETE_SOURCE_STATES,
        "minimum_informative_source_states": (
            credit.MIN_INFORMATIVE_SOURCE_STATES
        ),
    }:
        raise CounterfactualRunnerBlocked("registration configuration differs")
    if registration["downstream_authority"] != credit.FALSE_DOWNSTREAM_AUTHORITY:
        raise CounterfactualRunnerBlocked("downstream authority differs")
    if registration["operations"] != OPERATIONS:
        raise CounterfactualRunnerBlocked("registered operations differ")
    if registration["schedule"] != {
        "seed_status": "already-consumed-development-only",
        "seeds": list(credit.CONSUMED_DEVELOPMENT_SEEDS),
    }:
        raise CounterfactualRunnerBlocked("registered seed schedule differs")
    if not isinstance(registration.get("output_dir"), str):
        raise CounterfactualRunnerBlocked("registration output differs")
    source = registration.get("source")
    if not isinstance(source, dict) or set(source) != {
        "bindings",
        "commit",
        "repo_root",
    } or set(source.get("bindings", {})) != set(BOUND_SOURCE_PATHS):
        raise CounterfactualRunnerBlocked("registration source differs")
    if not isinstance(source["commit"], str) or len(source["commit"]) != 40:
        raise CounterfactualRunnerBlocked("registration source commit differs")
    if any(
        not isinstance(binding, dict)
        or set(binding) != {"path", "sha256", "size_bytes"}
        for binding in source["bindings"].values()
    ):
        raise CounterfactualRunnerBlocked("source bindings differ")
    native = registration.get("native")
    if not isinstance(native, dict) or set(native) != {
        "identity",
        "parent_registration",
    }:
        raise CounterfactualRunnerBlocked("registration native differs")
    identity = native["identity"]
    if not isinstance(identity, dict) or identity.get(
        "adapter_api_version"
    ) != adapter.ADAPTER_API_VERSION:
        raise CounterfactualRunnerBlocked("native identity differs")
    bindings = [
        identity.get("module"),
        *identity.get("dependency_closure", {}).get("dependencies", ()),
        native["parent_registration"],
    ]
    if any(
        not isinstance(binding, dict)
        or set(binding) != {"path", "sha256", "size_bytes"}
        for binding in bindings
    ):
        raise CounterfactualRunnerBlocked("native bindings differ")
    isolation = registration.get("production_isolation")
    if not isinstance(isolation, dict) or set(isolation) != {
        "communication_mod_config",
        "production_checkpoints",
    }:
        raise CounterfactualRunnerBlocked("production isolation differs")
    return registration


def _binding_matches(binding: Mapping[str, Any]) -> bool:
    return pilot_runner._file_binding(binding["path"]) == dict(binding)


def production_isolation_matches(registration: Mapping[str, Any]) -> bool:
    isolation = registration["production_isolation"]
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
        raise CounterfactualRunnerBlocked("registered source is unavailable")
    try:
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", source["commit"], "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise CounterfactualRunnerBlocked(
            "registered source is not an ancestor of HEAD"
        ) from exc
    if any(not _binding_matches(row) for row in source["bindings"].values()):
        raise CounterfactualRunnerBlocked("registered source bytes differ")
    native = registration["native"]
    if not _binding_matches(native["parent_registration"]):
        raise CounterfactualRunnerBlocked("parent registration bytes differ")
    parent = _read_canonical(native["parent_registration"]["path"])
    if _parent_native_identity(parent) != native["identity"]:
        raise CounterfactualRunnerBlocked("parent native identity differs")
    native_bindings = [
        native["identity"]["module"],
        *native["identity"]["dependency_closure"]["dependencies"],
    ]
    if any(not _binding_matches(row) for row in native_bindings):
        raise CounterfactualRunnerBlocked("registered native bytes differ")
    if not production_isolation_matches(registration):
        raise CounterfactualRunnerBlocked("production isolation differs")
    if list(process_observer()):
        raise CounterfactualRunnerBlocked("game or CommunicationMod is active")
    output = Path(registration["output_dir"]).resolve()
    checkpoint_root = Path(
        registration["production_isolation"]["production_checkpoints"]["path"]
    ).resolve()
    if output.exists() or output == checkpoint_root or checkpoint_root in output.parents:
        raise CounterfactualRunnerBlocked("output boundary differs")
    return {
        "checks": {
            "consumed_seed_schedule_bound": True,
            "downstream_authority_false": True,
            "forbidden_processes_absent": True,
            "native_bytes_bound_without_loading": True,
            "output_outside_production": True,
            "production_isolation_bound": True,
            "source_bytes_bound": True,
        },
        "registration_sha256": hashlib.sha256(
            _canonical_bytes(registration)
        ).hexdigest(),
        "schema_version": PREFLIGHT_SCHEMA_VERSION,
        "verdict": "preflight_passed",
    }


def execute_poc(
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
        raise CounterfactualRunnerBlocked("runner clock is invalid")
    deadline = started + registration["configuration"]["maximum_charged_seconds"]
    environment_factory = environment_factory_loader(
        registration["native"]["identity"]
    )
    try:
        report = credit.run_counterfactual_credit_poc(
            environment_factory,
            seeds=tuple(registration["schedule"]["seeds"]),
            max_card_states_per_seed=registration["configuration"][
                "maximum_card_states_per_seed"
            ],
            max_action_branches=registration["configuration"][
                "maximum_action_branches"
            ],
            min_complete_source_states=registration["configuration"][
                "minimum_complete_source_states"
            ],
            min_informative_source_states=registration["configuration"][
                "minimum_informative_source_states"
            ],
            max_decisions=registration["configuration"][
                "maximum_decisions_per_continuation"
            ],
            deadline=deadline,
            clock=clock,
        )
    except credit.CounterfactualCreditBlocked as exc:
        raise CounterfactualRunnerBlocked(str(exc)) from exc
    if not production_isolation_matches(registration):
        raise CounterfactualRunnerBlocked("production isolation changed during POC")
    if list(process_observer()):
        raise CounterfactualRunnerBlocked("game or CommunicationMod started during POC")
    elapsed = float(clock()) - started
    if not math.isfinite(elapsed) or elapsed < 0 or elapsed > MAX_CHARGED_SECONDS:
        raise CounterfactualRunnerBlocked("charged time exceeds registration")
    report = copy.deepcopy(report)
    report["execution"] = {
        "charged_seconds": elapsed,
        "operations": copy.deepcopy(OPERATIONS),
        "production_isolation_passed": True,
        "source_commit": registration["source"]["commit"],
    }
    report_binding = _write_canonical(output / "report.json", report)
    terminal = {
        "action_branch_continuations": report["summary"][
            "action_branch_continuations"
        ],
        "downstream_authority": copy.deepcopy(credit.FALSE_DOWNSTREAM_AUTHORITY),
        "report": report_binding,
        "rollback": "native_simple_agent",
        "schema_version": TERMINAL_SCHEMA_VERSION,
        "verdict": report["verdict"],
    }
    _write_canonical(output / "terminal.json", terminal)
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
                output_dir=args.output_dir,
            )
            binding = _write_canonical(args.registration, registration)
            print(_canonical_bytes(binding).decode("ascii"))
            return 0
        registration = _read_canonical(args.registration)
        if args.command == "preflight":
            print(
                _canonical_bytes(preflight_registration(registration)).decode(
                    "ascii"
                )
            )
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
        terminal = execute_poc(registration)
        print(_canonical_bytes(terminal).decode("ascii"))
        return 0
    except (CounterfactualRunnerBlocked, OSError, subprocess.SubprocessError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
