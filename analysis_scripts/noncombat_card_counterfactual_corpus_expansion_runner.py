"""Collect a large reusable card counterfactual train/development corpus."""

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
from collections import Counter
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
    "noncombat-card-counterfactual-corpus-expansion-registration-v1"
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
            raise RuntimeError("corpus worker registration schema differs")
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
                raise RuntimeError("corpus dependency cycle differs")
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
            raise RuntimeError("corpus dependency graph differs")
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
            raise RuntimeError("corpus native spec is unavailable")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if module.adapter_api_version() != "sts-lightspeed-noncombat-adapter-v3":
            raise RuntimeError("corpus native API differs")
        sys.modules["sts_lightspeed_noncombat_adapter"] = module
    except (IndexError, KeyError, OSError, RuntimeError, ValueError) as exc:
        raise RuntimeError("corpus early native load failed") from exc


_early_preload_native()


from analysis_scripts import noncombat_card_counterfactual_ranking_training as ranking
from analysis_scripts import noncombat_card_counterfactual_ranking_training_runner as base_runner
from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot_runner as pilot_runner
from analysis_scripts import noncombat_simulator_adapter as adapter


PREFLIGHT_SCHEMA_VERSION = (
    "noncombat-card-counterfactual-corpus-expansion-preflight-v1"
)
REPORT_SCHEMA_VERSION = "noncombat-card-counterfactual-corpus-expansion-report-v1"
TERMINAL_SCHEMA_VERSION = (
    "noncombat-card-counterfactual-corpus-expansion-terminal-v1"
)
TRAIN_SEEDS = tuple(range(80000, 80256))
DEVELOPMENT_SEEDS = tuple(range(80256, 80320))
RESERVED_AUDIT_SEEDS = tuple(range(80320, 80384))
MAX_TRAIN_BRANCHES = 2_048
MAX_DEVELOPMENT_BRANCHES = 512
MAX_TRAIN_CENSORED_SEEDS = 16
MAX_DEVELOPMENT_CENSORED_SEEDS = 4
MIN_TRAIN_SOURCE_STATES = 440
MIN_DEVELOPMENT_SOURCE_STATES = 110
MAX_DATASET_BYTES = 128 * 1024 * 1024
MAX_CHARGED_SECONDS = 14_400.0
DEFAULT_LINEAGE_REGISTRATION = Path(
    "reports/noncombat_card_counterfactual_uplift_residual_audit_20260813_r1/registration.json"
)
DEFAULT_LINEAGE_REPORT = Path(
    "reports/noncombat_card_counterfactual_uplift_residual_audit_20260813_r1/report.json"
)
DEFAULT_OUTPUT_DIR = Path(
    "reports/noncombat_card_counterfactual_corpus_expansion_20260813_r1"
)
BOUND_SOURCE_PATHS = (
    "analysis_scripts/noncombat_card_acceptance_empirical_successor_runtime.py",
    "analysis_scripts/noncombat_card_acceptance_objective.py",
    "analysis_scripts/noncombat_card_action_counterfactual_credit.py",
    "analysis_scripts/noncombat_card_action_counterfactual_credit_runner.py",
    "analysis_scripts/noncombat_card_counterfactual_corpus_expansion_runner.py",
    "analysis_scripts/noncombat_card_counterfactual_ranking_training.py",
    "analysis_scripts/noncombat_card_counterfactual_ranking_training_runner.py",
    "analysis_scripts/noncombat_card_only_native_baseline_rl_pilot.py",
    "analysis_scripts/noncombat_card_only_native_baseline_rl_pilot_runner.py",
    "analysis_scripts/noncombat_formal_reward_contract.py",
    "analysis_scripts/noncombat_simulator_adapter.py",
    "analysis_scripts/noncombat_state_conditioned_policy_input.py",
)
AUTHORITY = {
    name: False
    for name in (
        "audit_access",
        "causal_claim",
        "communication_mod",
        "evaluation",
        "formal_rl",
        "gameplay",
        "model_fitting",
        "ope",
        "policy_quality",
        "production_model_loading",
        "promotion",
        "qualification",
        "training",
    )
}
OPERATIONS = {
    "audit_access": False,
    "communication_mod": False,
    "environment_construction": True,
    "evaluation": False,
    "gameplay": False,
    "model_fitting": False,
    "model_loading": False,
    "native_loading": True,
    "ope": False,
    "production_model_loading": False,
    "seed_access": True,
    "training": False,
}


class CorpusExpansionBlocked(RuntimeError):
    """Raised when the fixed corpus collection contract cannot proceed."""


def _configuration() -> dict[str, Any]:
    return {
        "maximum_card_states_per_seed": ranking.MAX_CARD_STATES_PER_SEED,
        "maximum_charged_seconds": MAX_CHARGED_SECONDS,
        "maximum_dataset_bytes": MAX_DATASET_BYTES,
        "maximum_development_branches": MAX_DEVELOPMENT_BRANCHES,
        "maximum_development_censored_seeds": MAX_DEVELOPMENT_CENSORED_SEEDS,
        "maximum_train_branches": MAX_TRAIN_BRANCHES,
        "maximum_train_censored_seeds": MAX_TRAIN_CENSORED_SEEDS,
        "minimum_development_source_states": MIN_DEVELOPMENT_SOURCE_STATES,
        "minimum_train_source_states": MIN_TRAIN_SOURCE_STATES,
    }


def _source_bindings(root: Path, source_commit: str) -> dict[str, dict[str, Any]]:
    bindings: dict[str, dict[str, Any]] = {}
    for relative in BOUND_SOURCE_PATHS:
        actual = pilot_runner._file_binding(root / relative)
        try:
            committed = subprocess.run(
                ["git", "show", f"{source_commit}:{relative}"],
                cwd=root,
                check=True,
                capture_output=True,
            ).stdout
        except (OSError, subprocess.CalledProcessError) as exc:
            raise CorpusExpansionBlocked(
                f"source path is unavailable at commit: {relative}"
            ) from exc
        if hashlib.sha256(committed).hexdigest() != actual["sha256"]:
            raise CorpusExpansionBlocked(f"source bytes differ: {relative}")
        bindings[relative] = actual
    return bindings


def _input_bindings(
    lineage_registration: Path, lineage_report: Path
) -> dict[str, dict[str, Any]]:
    return {
        "lineage_registration": pilot_runner._file_binding(lineage_registration),
        "lineage_report": pilot_runner._file_binding(lineage_report),
    }


def build_registration(
    *,
    repo_root: Path | str,
    source_commit: str,
    lineage_registration_path: Path | str,
    lineage_report_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    lineage_registration_path = Path(lineage_registration_path).resolve()
    lineage_report_path = Path(lineage_report_path).resolve()
    lineage_registration = base_runner._read_canonical(lineage_registration_path)
    lineage_report = base_runner._read_canonical(lineage_report_path)
    if lineage_report.get("verdict") != (
        "card_counterfactual_uplift_residual_audit_not_ready"
    ):
        raise CorpusExpansionBlocked("lineage audit verdict differs")
    try:
        if pilot_runner._git(root, "cat-file", "-t", source_commit) != "commit":
            raise CorpusExpansionBlocked("source commit is unavailable")
    except pilot_runner.CardOnlyRunnerBlocked as exc:
        raise CorpusExpansionBlocked("source commit is unavailable") from exc
    output = Path(output_dir).resolve()
    checkpoint_root = base_runner.PRODUCTION_CHECKPOINT_ROOT.resolve()
    if output == checkpoint_root or checkpoint_root in output.parents:
        raise CorpusExpansionBlocked("output overlaps production checkpoints")
    return validate_registration(
        {
            "authority": copy.deepcopy(AUTHORITY),
            "configuration": _configuration(),
            "inputs": _input_bindings(
                lineage_registration_path, lineage_report_path
            ),
            "native": copy.deepcopy(lineage_registration["native"]),
            "operations": copy.deepcopy(OPERATIONS),
            "output_dir": output.as_posix(),
            "production_isolation": copy.deepcopy(
                lineage_registration["production_isolation"]
            ),
            "schedule": {
                "development_seeds": list(DEVELOPMENT_SEEDS),
                "reserved_audit_seeds": list(RESERVED_AUDIT_SEEDS),
                "seed_status": "new-train-development-with-untouched-audit",
                "train_seeds": list(TRAIN_SEEDS),
            },
            "schema_version": REGISTRATION_SCHEMA_VERSION,
            "source": {
                "bindings": _source_bindings(root, source_commit),
                "commit": source_commit,
                "repo_root": root.as_posix(),
            },
        }
    )


def validate_registration(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise CorpusExpansionBlocked("registration must be an object")
    registration = copy.deepcopy(dict(value))
    if set(registration) != {
        "authority",
        "configuration",
        "inputs",
        "native",
        "operations",
        "output_dir",
        "production_isolation",
        "schedule",
        "schema_version",
        "source",
    } or registration.get("schema_version") != REGISTRATION_SCHEMA_VERSION:
        raise CorpusExpansionBlocked("registration fields differ")
    if registration["authority"] != AUTHORITY:
        raise CorpusExpansionBlocked("authority differs")
    if registration["configuration"] != _configuration():
        raise CorpusExpansionBlocked("configuration differs")
    if registration["operations"] != OPERATIONS:
        raise CorpusExpansionBlocked("operations differ")
    expected_schedule = {
        "development_seeds": list(DEVELOPMENT_SEEDS),
        "reserved_audit_seeds": list(RESERVED_AUDIT_SEEDS),
        "seed_status": "new-train-development-with-untouched-audit",
        "train_seeds": list(TRAIN_SEEDS),
    }
    if registration["schedule"] != expected_schedule:
        raise CorpusExpansionBlocked("schedule differs")
    schedule_sets = [
        set(registration["schedule"][name])
        for name in (
            "train_seeds",
            "development_seeds",
            "reserved_audit_seeds",
        )
    ]
    if any(
        left & right
        for index, left in enumerate(schedule_sets)
        for right in schedule_sets[index + 1 :]
    ):
        raise CorpusExpansionBlocked("schedule overlaps")
    inputs = registration.get("inputs")
    if not isinstance(inputs, dict) or set(inputs) != {
        "lineage_registration",
        "lineage_report",
    }:
        raise CorpusExpansionBlocked("inputs differ")
    source = registration.get("source")
    if (
        not isinstance(source, dict)
        or set(source) != {"bindings", "commit", "repo_root"}
        or set(source.get("bindings", {})) != set(BOUND_SOURCE_PATHS)
    ):
        raise CorpusExpansionBlocked("source differs")
    if not isinstance(source["commit"], str) or len(source["commit"]) != 40:
        raise CorpusExpansionBlocked("source commit differs")
    bindings = [*inputs.values(), *source["bindings"].values()]
    if any(
        not isinstance(binding, dict)
        or set(binding) != {"path", "sha256", "size_bytes"}
        for binding in bindings
    ):
        raise CorpusExpansionBlocked("file bindings differ")
    native = registration.get("native")
    identity = native.get("identity") if isinstance(native, dict) else None
    if not isinstance(identity, dict) or identity.get(
        "adapter_api_version"
    ) != adapter.ADAPTER_API_VERSION:
        raise CorpusExpansionBlocked("native identity differs")
    if not isinstance(registration.get("output_dir"), str):
        raise CorpusExpansionBlocked("output differs")
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
    try:
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", source["commit"], "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise CorpusExpansionBlocked("registered source is not an ancestor") from exc
    if _source_bindings(root, source["commit"]) != source["bindings"] or any(
        not _binding_matches(binding)
        for binding in registration["inputs"].values()
    ):
        raise CorpusExpansionBlocked("registered source or input bytes differ")
    lineage_registration = base_runner._read_canonical(
        registration["inputs"]["lineage_registration"]["path"]
    )
    lineage_report = base_runner._read_canonical(
        registration["inputs"]["lineage_report"]["path"]
    )
    if (
        lineage_report.get("verdict")
        != "card_counterfactual_uplift_residual_audit_not_ready"
        or lineage_registration.get("native") != registration["native"]
        or lineage_registration.get("production_isolation")
        != registration["production_isolation"]
    ):
        raise CorpusExpansionBlocked("lineage evidence differs")
    native = registration["native"]["identity"]
    native_bindings = [
        native["module"],
        *native["dependency_closure"]["dependencies"],
    ]
    if any(not _binding_matches(binding) for binding in native_bindings):
        raise CorpusExpansionBlocked("native bytes differ")
    if not base_runner.production_isolation_matches(registration):
        raise CorpusExpansionBlocked("production isolation differs")
    if list(process_observer()):
        raise CorpusExpansionBlocked("game or CommunicationMod is active")
    output = Path(registration["output_dir"]).resolve()
    checkpoint_root = Path(
        registration["production_isolation"]["production_checkpoints"]["path"]
    ).resolve()
    if output.exists() or output == checkpoint_root or checkpoint_root in output.parents:
        raise CorpusExpansionBlocked("output boundary differs")
    return {
        "checks": {
            "audit_reserved_and_unaccessed": True,
            "forbidden_processes_absent": True,
            "lineage_bound": True,
            "native_bytes_bound_without_loading": True,
            "production_isolation_bound": True,
            "schedules_disjoint_and_fixed": True,
            "source_bytes_bound": True,
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
    max_action_branches: int,
    max_censored_seeds: int,
    deadline: float,
    clock: Callable[[], float],
) -> ranking.CounterfactualPartition:
    try:
        return ranking.collect_counterfactual_partition(
            factory,
            name=name,
            seeds=seeds,
            max_action_branches=max_action_branches,
            max_censored_seeds=max_censored_seeds,
            max_card_states_per_seed=ranking.MAX_CARD_STATES_PER_SEED,
            deadline=deadline,
            clock=clock,
        )
    except ranking.CounterfactualRankingBlocked as exc:
        raise CorpusExpansionBlocked(str(exc)) from exc


def _encode_dataset(partition: ranking.CounterfactualPartition) -> bytes:
    payload = ranking.encode_counterfactual_partition(partition)
    if len(payload) > MAX_DATASET_BYTES:
        raise CorpusExpansionBlocked(f"{partition.name} dataset exceeds bound")
    if ranking.encode_counterfactual_partition(
        ranking.restore_counterfactual_partition(payload)
    ) != payload:
        raise CorpusExpansionBlocked(f"{partition.name} dataset round trip differs")
    return payload


def partition_diagnostics(
    partition: ranking.CounterfactualPartition,
) -> dict[str, Any]:
    if not partition.rows:
        raise CorpusExpansionBlocked(f"{partition.name} has no source states")
    action_kinds: Counter[str] = Counter()
    candidate_counts: Counter[str] = Counter()
    take_card_ids: set[str] = set()
    returns: list[float] = []
    spreads: list[float] = []
    for row in partition.rows:
        candidate_counts[str(len(row.candidates))] += 1
        returns.extend(row.action_returns)
        spreads.append(max(row.action_returns) - min(row.action_returns))
        for candidate in row.candidates:
            kind = str(candidate.get("kind", "unknown"))
            action_kinds[kind] += 1
            raw = candidate.get("raw")
            if kind == "take" and isinstance(raw, Mapping):
                card_id = raw.get("id")
                if isinstance(card_id, str) and card_id:
                    take_card_ids.add(card_id)
    return {
        "action_branches": partition.action_branches,
        "action_kind_counts": dict(sorted(action_kinds.items())),
        "budget_exhausted": partition.budget_exhausted,
        "candidate_action_count": sum(len(row.candidates) for row in partition.rows),
        "candidate_count_distribution": dict(sorted(candidate_counts.items())),
        "censored_seeds": copy.deepcopy(list(partition.censored_seeds)),
        "informative_source_states": sum(row.informative for row in partition.rows),
        "return_summary": {
            "maximum": max(returns),
            "mean": sum(returns) / len(returns),
            "minimum": min(returns),
        },
        "root_native_transitions": partition.root_native_transitions,
        "source_states": len(partition.rows),
        "spread_summary": {
            "maximum": max(spreads),
            "mean": sum(spreads) / len(spreads),
            "minimum": min(spreads),
            "nonzero_states": sum(spread > 0 for spread in spreads),
        },
        "take_card_ids": sorted(take_card_ids),
        "unique_take_card_ids": len(take_card_ids),
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
    preflight = preflight_registration(registration, process_observer=process_observer)
    started = float(clock())
    if not math.isfinite(started):
        raise CorpusExpansionBlocked("runner clock is invalid")
    deadline = started + MAX_CHARGED_SECONDS
    factory = environment_factory_loader(registration["native"]["identity"])
    configuration = registration["configuration"]
    schedule = registration["schedule"]
    train = _collect(
        factory,
        name="train",
        seeds=schedule["train_seeds"],
        max_action_branches=configuration["maximum_train_branches"],
        max_censored_seeds=configuration["maximum_train_censored_seeds"],
        deadline=deadline,
        clock=clock,
    )
    development = _collect(
        factory,
        name="holdout",
        seeds=schedule["development_seeds"],
        max_action_branches=configuration["maximum_development_branches"],
        max_censored_seeds=configuration[
            "maximum_development_censored_seeds"
        ],
        deadline=deadline,
        clock=clock,
    )
    if len(train.rows) < configuration["minimum_train_source_states"]:
        raise CorpusExpansionBlocked("train source support floor is unmet")
    if len(development.rows) < configuration["minimum_development_source_states"]:
        raise CorpusExpansionBlocked("development source support floor is unmet")
    train_payload = _encode_dataset(train)
    development_payload = _encode_dataset(development)
    train_diagnostics = partition_diagnostics(train)
    development_diagnostics = partition_diagnostics(development)
    train_cards = set(train_diagnostics["take_card_ids"])
    development_diagnostics["unseen_take_card_ids"] = sorted(
        set(development_diagnostics["take_card_ids"]) - train_cards
    )
    if not base_runner.production_isolation_matches(registration):
        raise CorpusExpansionBlocked("production isolation changed during collection")
    if list(process_observer()):
        raise CorpusExpansionBlocked("game or CommunicationMod started during collection")
    elapsed = float(clock()) - started
    if not math.isfinite(elapsed) or elapsed < 0 or elapsed > MAX_CHARGED_SECONDS:
        raise CorpusExpansionBlocked("charged time exceeds registration")

    output = Path(registration["output_dir"]).resolve()
    output.mkdir(parents=False, exist_ok=False)
    base_runner._write_canonical(output / "registration.json", registration)
    base_runner._write_canonical(output / "preflight.json", preflight)
    train_binding = base_runner._write_bytes(
        output / "train_dataset_full.json", train_payload
    )
    development_binding = base_runner._write_bytes(
        output / "development_dataset_full.json", development_payload
    )
    report = {
        "audit_accessed": False,
        "authority": copy.deepcopy(AUTHORITY),
        "coverage": {
            "development": development_diagnostics,
            "train": train_diagnostics,
        },
        "datasets": {
            "development": development_binding,
            "train": train_binding,
        },
        "execution": {
            "charged_seconds": elapsed,
            "operations": copy.deepcopy(OPERATIONS),
            "production_isolation_passed": True,
            "source_commit": registration["source"]["commit"],
        },
        "schedule": copy.deepcopy(schedule),
        "schema_version": REPORT_SCHEMA_VERSION,
        "training_performed": False,
        "verdict": "card_counterfactual_corpus_ready_for_source_only_training_proposal",
    }
    report_binding = base_runner._write_canonical(output / "report.json", report)
    terminal = {
        "action_branches": train.action_branches + development.action_branches,
        "audit_accessed": False,
        "authority": copy.deepcopy(AUTHORITY),
        "development_source_states": len(development.rows),
        "report": report_binding,
        "schema_version": TERMINAL_SCHEMA_VERSION,
        "train_source_states": len(train.rows),
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
    register.add_argument(
        "--lineage-registration", default=str(DEFAULT_LINEAGE_REGISTRATION)
    )
    register.add_argument("--lineage-report", default=str(DEFAULT_LINEAGE_REPORT))
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
                lineage_registration_path=args.lineage_registration,
                lineage_report_path=args.lineage_report,
                output_dir=args.output_dir,
            )
            binding = base_runner._write_canonical(args.registration, registration)
            print(base_runner._canonical_bytes(binding).decode("ascii"))
            return 0
        registration = base_runner._read_canonical(args.registration)
        if args.command == "preflight":
            print(
                base_runner._canonical_bytes(
                    preflight_registration(registration)
                ).decode("ascii")
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
        terminal = execute(registration)
        print(base_runner._canonical_bytes(terminal).decode("ascii"))
        return 0
    except (
        CorpusExpansionBlocked,
        OSError,
        base_runner.RankingRunnerBlocked,
        subprocess.SubprocessError,
    ) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
