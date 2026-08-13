"""One-shot consumed audit for the fixed card uplift residual."""

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
    "noncombat-card-counterfactual-uplift-residual-audit-registration-v1"
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
            raise RuntimeError("uplift audit worker registration schema differs")
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
                raise RuntimeError("uplift audit dependency cycle differs")
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
            raise RuntimeError("uplift audit dependency graph differs")
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
            raise RuntimeError("uplift audit native spec is unavailable")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if module.adapter_api_version() != "sts-lightspeed-noncombat-adapter-v3":
            raise RuntimeError("uplift audit native API differs")
        sys.modules["sts_lightspeed_noncombat_adapter"] = module
    except (IndexError, KeyError, OSError, RuntimeError, ValueError) as exc:
        raise RuntimeError("uplift audit early native load failed") from exc


_early_preload_native()


from analysis_scripts import noncombat_card_counterfactual_ranking_training as ranking
from analysis_scripts import noncombat_card_counterfactual_ranking_training_runner as base_runner
from analysis_scripts import noncombat_card_counterfactual_scorer_weight_runner as scorer_runner
from analysis_scripts import noncombat_card_counterfactual_uplift_residual_crossfit as crossfit
from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot as pilot
from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot_runner as pilot_runner
from analysis_scripts import noncombat_simulator_adapter as adapter


PREFLIGHT_SCHEMA_VERSION = (
    "noncombat-card-counterfactual-uplift-residual-audit-preflight-v1"
)
TERMINAL_SCHEMA_VERSION = (
    "noncombat-card-counterfactual-uplift-residual-audit-terminal-v1"
)
REPORT_SCHEMA_VERSION = (
    "noncombat-card-counterfactual-uplift-residual-audit-report-v1"
)
AUDIT_SEEDS = tuple(range(1024, 1032))
MAX_AUDIT_BRANCHES = 64
MAX_AUDIT_CENSORED_SEEDS = 1
MIN_AUDIT_SOURCE_STATES = 12
MAX_DATASET_BYTES = 64 * 1024 * 1024
MAX_CHARGED_SECONDS = 3_600.0
FIXED_CONFIGURATION = crossfit.ResidualConfiguration(shrinkage=3, strength=128)
DEFAULT_CROSSFIT_ROOT = Path(
    "reports/noncombat_card_counterfactual_uplift_residual_crossfit_20260813_r1"
)
DEFAULT_SCORER_ROOT = Path(
    "reports/noncombat_card_counterfactual_scorer_weight_20260813_r1"
)
DEFAULT_OUTPUT_DIR = Path(
    "reports/noncombat_card_counterfactual_uplift_residual_audit_20260813_r1"
)
BOUND_SOURCE_PATHS = tuple(
    sorted(
        {
            *crossfit.SOURCE_PATHS,
            "analysis_scripts/noncombat_card_counterfactual_scorer_weight_runner.py",
            "analysis_scripts/noncombat_card_counterfactual_uplift_residual_audit_runner.py",
        }
    )
)
AUTHORITY = {
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
OPERATIONS = {
    "audit_evaluation": True,
    "communication_mod": False,
    "environment_construction": True,
    "exposed_model_fitting": True,
    "fresh_evaluation": False,
    "gameplay": False,
    "model_loading": True,
    "native_loading": True,
    "ope": False,
    "post_audit_fitting": False,
    "production_model_loading": False,
    "seed_access": True,
}


class UpliftAuditBlocked(RuntimeError):
    """Raised when the fixed audit contract cannot proceed."""


def _configuration() -> dict[str, Any]:
    return {
        "fixed_residual": FIXED_CONFIGURATION.as_dict(),
        "maximum_action_branches": MAX_AUDIT_BRANCHES,
        "maximum_card_states_per_seed": ranking.MAX_CARD_STATES_PER_SEED,
        "maximum_censored_seeds": MAX_AUDIT_CENSORED_SEEDS,
        "maximum_charged_seconds": MAX_CHARGED_SECONDS,
        "maximum_dataset_bytes": MAX_DATASET_BYTES,
        "minimum_source_states": MIN_AUDIT_SOURCE_STATES,
    }


def _source_bindings(
    root: Path, source_commit: str
) -> dict[str, dict[str, Any]]:
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
            raise UpliftAuditBlocked(
                f"source path is unavailable at commit: {relative}"
            ) from exc
        if hashlib.sha256(committed).hexdigest() != actual["sha256"]:
            raise UpliftAuditBlocked(f"source bytes differ: {relative}")
        bindings[relative] = actual
    return bindings


def _input_bindings(crossfit_root: Path, scorer_root: Path) -> dict[str, Any]:
    scorer_registration = base_runner._read_canonical(
        scorer_root / "registration.json"
    )
    return {
        "crossfit_configuration": pilot_runner._file_binding(
            crossfit_root / "configuration.json"
        ),
        "crossfit_manifest": pilot_runner._file_binding(
            crossfit_root / "artifact_manifest.json"
        ),
        "crossfit_report": pilot_runner._file_binding(crossfit_root / "report.json"),
        "development_dataset": pilot_runner._file_binding(
            scorer_root / "development_dataset_full.json"
        ),
        "entry_checkpoint": copy.deepcopy(
            scorer_registration["inputs"]["entry_checkpoint"]
        ),
        "scorer_registration": pilot_runner._file_binding(
            scorer_root / "registration.json"
        ),
        "scorer_report": pilot_runner._file_binding(scorer_root / "report.json"),
        "train_dataset": pilot_runner._file_binding(
            scorer_root / "train_dataset_full.json"
        ),
    }


def build_registration(
    *,
    repo_root: Path | str,
    source_commit: str,
    crossfit_root: Path | str,
    scorer_root: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    crossfit_path = Path(crossfit_root).resolve()
    scorer_path = Path(scorer_root).resolve()
    scorer_registration = base_runner._read_canonical(
        scorer_path / "registration.json"
    )
    crossfit_report = base_runner._read_canonical(crossfit_path / "report.json")
    if crossfit_report.get("verdict") != (
        "card_counterfactual_uplift_residual_ready_for_audit_proposal"
    ) or crossfit_report.get("audit_accessed") is not False:
        raise UpliftAuditBlocked("crossfit verdict differs")
    try:
        if pilot_runner._git(root, "cat-file", "-t", source_commit) != "commit":
            raise UpliftAuditBlocked("source commit is unavailable")
    except pilot_runner.CardOnlyRunnerBlocked as exc:
        raise UpliftAuditBlocked("source commit is unavailable") from exc
    output = Path(output_dir).resolve()
    checkpoint_root = base_runner.PRODUCTION_CHECKPOINT_ROOT.resolve()
    if output == checkpoint_root or checkpoint_root in output.parents:
        raise UpliftAuditBlocked("output overlaps production checkpoints")
    return validate_registration(
        {
            "authority": copy.deepcopy(AUTHORITY),
            "configuration": _configuration(),
            "inputs": _input_bindings(crossfit_path, scorer_path),
            "native": copy.deepcopy(scorer_registration["native"]),
            "operations": copy.deepcopy(OPERATIONS),
            "output_dir": output.as_posix(),
            "production_isolation": copy.deepcopy(
                scorer_registration["production_isolation"]
            ),
            "schedule": {
                "audit_seeds": list(AUDIT_SEEDS),
                "seed_status": "consumed-untouched-audit",
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
        raise UpliftAuditBlocked("registration must be an object")
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
        raise UpliftAuditBlocked("registration fields differ")
    if registration["authority"] != AUTHORITY:
        raise UpliftAuditBlocked("authority differs")
    if registration["configuration"] != _configuration():
        raise UpliftAuditBlocked("configuration differs")
    if registration["operations"] != OPERATIONS:
        raise UpliftAuditBlocked("operations differ")
    if registration["schedule"] != {
        "audit_seeds": list(AUDIT_SEEDS),
        "seed_status": "consumed-untouched-audit",
    }:
        raise UpliftAuditBlocked("schedule differs")
    inputs = registration.get("inputs")
    expected_inputs = {
        "crossfit_configuration",
        "crossfit_manifest",
        "crossfit_report",
        "development_dataset",
        "entry_checkpoint",
        "scorer_registration",
        "scorer_report",
        "train_dataset",
    }
    if not isinstance(inputs, dict) or set(inputs) != expected_inputs:
        raise UpliftAuditBlocked("inputs differ")
    source = registration.get("source")
    if (
        not isinstance(source, dict)
        or set(source) != {"bindings", "commit", "repo_root"}
        or set(source.get("bindings", {})) != set(BOUND_SOURCE_PATHS)
    ):
        raise UpliftAuditBlocked("source differs")
    bindings = [*inputs.values(), *source["bindings"].values()]
    if any(
        not isinstance(binding, dict)
        or set(binding) != {"path", "sha256", "size_bytes"}
        for binding in bindings
    ):
        raise UpliftAuditBlocked("file bindings differ")
    native = registration.get("native")
    identity = native.get("identity") if isinstance(native, dict) else None
    if not isinstance(identity, dict) or identity.get(
        "adapter_api_version"
    ) != adapter.ADAPTER_API_VERSION:
        raise UpliftAuditBlocked("native identity differs")
    if not isinstance(registration.get("output_dir"), str):
        raise UpliftAuditBlocked("output differs")
    return registration


def _binding_matches(binding: Mapping[str, Any]) -> bool:
    return pilot_runner._file_binding(binding["path"]) == dict(binding)


def _load_exposed_rows(
    registration: Mapping[str, Any],
) -> tuple[tuple[ranking.CounterfactualRankingRow, ...], Any]:
    inputs = registration["inputs"]
    try:
        train = ranking.restore_counterfactual_partition(
            Path(inputs["train_dataset"]["path"]).read_bytes()
        )
        development = ranking.restore_counterfactual_partition(
            Path(inputs["development_dataset"]["path"]).read_bytes()
        )
        bootstrap = ranking.restore_entry_bootstrap(
            Path(inputs["entry_checkpoint"]["path"]).read_bytes()
        )
    except (OSError, ranking.CounterfactualRankingBlocked) as exc:
        raise UpliftAuditBlocked(str(exc)) from exc
    if (
        train.name != "train"
        or train.seeds != crossfit.EXPECTED_TRAIN_SEEDS
        or development.name != "holdout"
        or development.seeds != crossfit.EXPECTED_DEVELOPMENT_SEEDS
    ):
        raise UpliftAuditBlocked("exposed dataset lineage differs")
    return crossfit.validate_rows((*train.rows, *development.rows)), bootstrap


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
        raise UpliftAuditBlocked("registered source is not an ancestor") from exc
    if _source_bindings(root, source["commit"]) != source["bindings"] or any(
        not _binding_matches(row) for row in registration["inputs"].values()
    ):
        raise UpliftAuditBlocked("registered source or input bytes differ")
    inputs = registration["inputs"]
    crossfit_configuration = base_runner._read_canonical(
        inputs["crossfit_configuration"]["path"]
    )
    crossfit_manifest = base_runner._read_canonical(
        inputs["crossfit_manifest"]["path"]
    )
    crossfit_report = base_runner._read_canonical(inputs["crossfit_report"]["path"])
    expected_crossfit_verdict = (
        "card_counterfactual_uplift_residual_ready_for_audit_proposal"
    )
    if (
        crossfit_report.get("verdict") != expected_crossfit_verdict
        or crossfit_report.get("audit_accessed") is not False
        or crossfit_manifest.get("verdict") != expected_crossfit_verdict
        or crossfit_manifest.get("artifacts", {}).get("configuration.json")
        != inputs["crossfit_configuration"]
        or crossfit_manifest.get("artifacts", {}).get("report.json")
        != inputs["crossfit_report"]
        or crossfit_configuration.get("inputs", {}).get("train_dataset")
        != inputs["train_dataset"]
        or crossfit_configuration.get("inputs", {}).get("development_dataset")
        != inputs["development_dataset"]
        or crossfit_configuration.get("inputs", {}).get("entry_checkpoint")
        != inputs["entry_checkpoint"]
        or crossfit_configuration.get("inputs", {}).get("scorer_registration")
        != inputs["scorer_registration"]
        or crossfit_configuration.get("inputs", {}).get("scorer_report")
        != inputs["scorer_report"]
    ):
        raise UpliftAuditBlocked("crossfit evidence differs")
    scorer_report = base_runner._read_canonical(inputs["scorer_report"]["path"])
    scorer_registration = base_runner._read_canonical(
        inputs["scorer_registration"]["path"]
    )
    if (
        scorer_report.get("verdict")
        != "card_counterfactual_scorer_weight_not_ready"
        or scorer_report.get("audit_accessed") is not False
        or scorer_report.get("datasets", {}).get("train")
        != inputs["train_dataset"]
        or scorer_report.get("datasets", {}).get("development")
        != inputs["development_dataset"]
        or scorer_registration.get("inputs", {}).get("entry_checkpoint")
        != inputs["entry_checkpoint"]
        or scorer_registration["native"] != registration["native"]
        or scorer_registration["production_isolation"]
        != registration["production_isolation"]
    ):
        raise UpliftAuditBlocked("scorer lineage differs")
    rows, bootstrap = _load_exposed_rows(registration)
    if len(rows) != 46 or not pilot.encode_candidate_card_policy(bootstrap):
        raise UpliftAuditBlocked("exposed fit inputs differ")
    native = registration["native"]["identity"]
    if any(
        not _binding_matches(row)
        for row in [native["module"], *native["dependency_closure"]["dependencies"]]
    ):
        raise UpliftAuditBlocked("native bytes differ")
    if not base_runner.production_isolation_matches(registration):
        raise UpliftAuditBlocked("production isolation differs")
    if list(process_observer()):
        raise UpliftAuditBlocked("game or CommunicationMod is active")
    output = Path(registration["output_dir"]).resolve()
    checkpoint_root = Path(
        registration["production_isolation"]["production_checkpoints"]["path"]
    ).resolve()
    if output.exists() or output == checkpoint_root or checkpoint_root in output.parents:
        raise UpliftAuditBlocked("output boundary differs")
    return {
        "checks": {
            "audit_untouched": True,
            "exposed_fit_inputs_restorable": True,
            "forbidden_processes_absent": True,
            "inputs_and_source_bound": True,
            "native_bytes_bound_without_loading": True,
            "production_isolation_bound": True,
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
    deadline: float,
    clock: Callable[[], float],
) -> ranking.CounterfactualPartition:
    try:
        return ranking.collect_counterfactual_partition(
            factory,
            name="audit",
            seeds=AUDIT_SEEDS,
            max_action_branches=MAX_AUDIT_BRANCHES,
            max_censored_seeds=MAX_AUDIT_CENSORED_SEEDS,
            max_card_states_per_seed=ranking.MAX_CARD_STATES_PER_SEED,
            deadline=deadline,
            clock=clock,
        )
    except ranking.CounterfactualRankingBlocked as exc:
        raise UpliftAuditBlocked(str(exc)) from exc


def _write_dataset(path: Path, partition: ranking.CounterfactualPartition) -> dict[str, Any]:
    payload = ranking.encode_counterfactual_partition(partition)
    if len(payload) > MAX_DATASET_BYTES:
        raise UpliftAuditBlocked("audit dataset exceeds registered bound")
    if ranking.encode_counterfactual_partition(
        ranking.restore_counterfactual_partition(payload)
    ) != payload:
        raise UpliftAuditBlocked("audit dataset round trip differs")
    return base_runner._write_bytes(path, payload)


def _audit_checks(
    base: Mapping[str, Any], candidate: Mapping[str, Any], comparison: Mapping[str, int]
) -> dict[str, bool]:
    return {
        "corrected_action": comparison["corrected_actions"] >= 1,
        "maximum_regret_nonincreasing": candidate["maximum_top_action_regret"]
        <= base["maximum_top_action_regret"],
        "mean_regret_decreased": candidate["mean_top_action_regret"]
        < base["mean_top_action_regret"],
        "pairwise_accuracy_increased": candidate["weighted_pairwise_accuracy"]
        > base["weighted_pairwise_accuracy"],
        "unique_best_accuracy_nondecreasing": candidate["unique_best_accuracy"]
        >= base["unique_best_accuracy"],
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
    output = Path(registration["output_dir"]).resolve()
    output.mkdir(parents=False, exist_ok=False)
    base_runner._write_canonical(output / "registration.json", registration)
    base_runner._write_canonical(output / "preflight.json", preflight)
    started = float(clock())
    if not math.isfinite(started):
        raise UpliftAuditBlocked("runner clock is invalid")
    deadline = started + MAX_CHARGED_SECONDS

    # The model is finalized and persisted before the first audit environment exists.
    exposed_rows, entry_bootstrap = _load_exposed_rows(registration)
    entry_before = pilot.encode_candidate_card_policy(entry_bootstrap)
    model = crossfit.fit_uplift_model(
        exposed_rows, shrinkage=FIXED_CONFIGURATION.shrinkage
    )
    model_bytes = crossfit.encode_uplift_model(model, FIXED_CONFIGURATION)
    restored_model, restored_configuration = crossfit.restore_uplift_model(model_bytes)
    if restored_configuration != FIXED_CONFIGURATION:
        raise UpliftAuditBlocked("fixed model configuration differs")
    model_binding = base_runner._write_bytes(output / "uplift_model.json", model_bytes)

    factory = environment_factory_loader(registration["native"]["identity"])
    audit = _collect(factory, deadline=deadline, clock=clock)
    if len(audit.rows) < MIN_AUDIT_SOURCE_STATES:
        raise UpliftAuditBlocked("audit support floor is unmet")
    dataset_binding = _write_dataset(output / "audit_dataset_full.json", audit)
    base_scores = crossfit._base_scores(entry_bootstrap, audit.rows)
    candidate_scores, unseen = crossfit.score_residual_rows(
        audit.rows,
        base_scores,
        restored_model,
        restored_configuration,
    )
    base_metrics = crossfit.evaluate_scores(audit.rows, base_scores)
    candidate_metrics = crossfit.evaluate_scores(audit.rows, candidate_scores)
    comparison = crossfit.compare_predictions(base_metrics, candidate_metrics)
    checks = _audit_checks(base_metrics, candidate_metrics, comparison)
    if pilot.encode_candidate_card_policy(entry_bootstrap) != entry_before:
        raise UpliftAuditBlocked("audit evaluation mutated entry model")
    if crossfit.encode_uplift_model(restored_model, restored_configuration) != model_bytes:
        raise UpliftAuditBlocked("audit evaluation mutated uplift model")
    if not base_runner.production_isolation_matches(registration):
        raise UpliftAuditBlocked("production isolation changed during audit")
    if list(process_observer()):
        raise UpliftAuditBlocked("game or CommunicationMod started during audit")
    elapsed = float(clock()) - started
    if not math.isfinite(elapsed) or elapsed < 0 or elapsed > MAX_CHARGED_SECONDS:
        raise UpliftAuditBlocked("charged time exceeds registration")
    ready = all(checks.values())
    report = {
        "audit_dataset": dataset_binding,
        "authority": copy.deepcopy(AUTHORITY),
        "base": base_metrics,
        "candidate": candidate_metrics,
        "checks": checks,
        "comparison": comparison,
        "execution": {
            "action_branches": audit.action_branches,
            "charged_seconds": elapsed,
            "censored_seeds": list(audit.censored_seeds),
            "operations": copy.deepcopy(OPERATIONS),
            "production_isolation_passed": True,
            "root_native_transitions": audit.root_native_transitions,
            "source_commit": registration["source"]["commit"],
            "unseen_take_actions": unseen,
        },
        "fixed_model": model_binding,
        "schema_version": REPORT_SCHEMA_VERSION,
        "verdict": (
            "card_counterfactual_uplift_residual_audit_ready_for_fresh_eval_proposal"
            if ready
            else "card_counterfactual_uplift_residual_audit_not_ready"
        ),
    }
    report_binding = base_runner._write_canonical(output / "report.json", report)
    terminal = {
        "action_branches": audit.action_branches,
        "authority": copy.deepcopy(AUTHORITY),
        "fixed_configuration": FIXED_CONFIGURATION.as_dict(),
        "report": report_binding,
        "rollback": "tracked_r7_checkpoint_and_native_simple_agent",
        "schema_version": TERMINAL_SCHEMA_VERSION,
        "source_states": len(audit.rows),
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
    register.add_argument("--crossfit-root", default=str(DEFAULT_CROSSFIT_ROOT))
    register.add_argument("--scorer-root", default=str(DEFAULT_SCORER_ROOT))
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
                crossfit_root=args.crossfit_root,
                scorer_root=args.scorer_root,
                output_dir=args.output_dir,
            )
            binding = base_runner._write_canonical(args.registration, registration)
            print(base_runner._canonical_bytes(binding).decode("ascii"))
            return 0
        registration = base_runner._read_canonical(args.registration)
        if args.command == "preflight":
            result = preflight_registration(registration)
            print(base_runner._canonical_bytes(result).decode("ascii"))
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
        OSError,
        subprocess.SubprocessError,
        UpliftAuditBlocked,
        base_runner.RankingRunnerBlocked,
        crossfit.UpliftCrossfitBlocked,
    ) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
