"""Run the reserved audit for the frozen large-corpus card uplift residual."""

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
    "noncombat-large-corpus-card-uplift-residual-audit-registration-v1"
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
            raise RuntimeError("large-corpus audit registration schema differs")
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
                raise RuntimeError("large-corpus audit dependency cycle differs")
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
            raise RuntimeError("large-corpus audit dependency graph differs")
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
            raise RuntimeError("large-corpus audit native spec is unavailable")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if module.adapter_api_version() != "sts-lightspeed-noncombat-adapter-v3":
            raise RuntimeError("large-corpus audit native API differs")
        sys.modules["sts_lightspeed_noncombat_adapter"] = module
    except (IndexError, KeyError, OSError, RuntimeError, ValueError) as exc:
        raise RuntimeError("large-corpus audit early native load failed") from exc


_early_preload_native()


from analysis_scripts import noncombat_card_counterfactual_corpus_expansion_runner as corpus
from analysis_scripts import noncombat_card_counterfactual_ranking_training as ranking
from analysis_scripts import noncombat_card_counterfactual_ranking_training_runner as base_runner
from analysis_scripts import noncombat_card_counterfactual_uplift_residual_crossfit as uplift
from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot as pilot
from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot_runner as pilot_runner
from analysis_scripts import noncombat_large_corpus_card_uplift_residual as study
from analysis_scripts import noncombat_simulator_adapter as adapter


PREFLIGHT_SCHEMA_VERSION = (
    "noncombat-large-corpus-card-uplift-residual-audit-preflight-v1"
)
REPORT_SCHEMA_VERSION = (
    "noncombat-large-corpus-card-uplift-residual-audit-report-v1"
)
TERMINAL_SCHEMA_VERSION = (
    "noncombat-large-corpus-card-uplift-residual-audit-terminal-v1"
)
AUDIT_SEEDS = corpus.RESERVED_AUDIT_SEEDS
MAX_AUDIT_BRANCHES = 512
MAX_AUDIT_CENSORED_SEEDS = 4
MIN_AUDIT_SOURCE_STATES = 110
MAX_DATASET_BYTES = 128 * 1024 * 1024
MAX_CHARGED_SECONDS = 3_600.0
DEFAULT_STUDY_ROOT = Path(
    "reports/noncombat_large_corpus_card_uplift_residual_20260813_r1"
)
DEFAULT_CORPUS_ROOT = corpus.DEFAULT_OUTPUT_DIR
DEFAULT_OUTPUT_DIR = Path(
    "reports/noncombat_large_corpus_card_uplift_residual_audit_20260813_r1"
)
BOUND_SOURCE_PATHS = tuple(
    sorted(
        {
            *study.SOURCE_PATHS,
            "analysis_scripts/noncombat_large_corpus_card_uplift_residual_audit_runner.py",
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
    "fresh_evaluation": False,
    "gameplay": False,
    "model_fitting": False,
    "model_loading": True,
    "native_loading": True,
    "ope": False,
    "production_model_loading": False,
    "seed_access": True,
    "training": False,
}


class LargeCorpusAuditBlocked(RuntimeError):
    """Raised when the fixed reserved-audit contract cannot proceed."""


def _configuration() -> dict[str, Any]:
    return {
        "development_equivalent_gates": {
            "minimum_corrected_actions": study.MIN_DEVELOPMENT_CORRECTED_ACTIONS,
            "worsened_actions_must_not_exceed_corrected": True,
        },
        "maximum_action_branches": MAX_AUDIT_BRANCHES,
        "maximum_card_states_per_seed": ranking.MAX_CARD_STATES_PER_SEED,
        "maximum_censored_seeds": MAX_AUDIT_CENSORED_SEEDS,
        "maximum_charged_seconds": MAX_CHARGED_SECONDS,
        "maximum_dataset_bytes": MAX_DATASET_BYTES,
        "minimum_source_states": MIN_AUDIT_SOURCE_STATES,
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
            raise LargeCorpusAuditBlocked(
                f"source path is unavailable at commit: {relative}"
            ) from exc
        if hashlib.sha256(committed).hexdigest() != actual["sha256"]:
            raise LargeCorpusAuditBlocked(f"source bytes differ: {relative}")
        bindings[relative] = actual
    return bindings


def _inputs(study_root: Path, corpus_root: Path) -> dict[str, dict[str, Any]]:
    return {
        "corpus_registration": pilot_runner._file_binding(
            corpus_root / "registration.json"
        ),
        "corpus_report": pilot_runner._file_binding(corpus_root / "report.json"),
        "development_dataset": pilot_runner._file_binding(
            corpus_root / "development_dataset_full.json"
        ),
        "entry_checkpoint": copy.deepcopy(
            study._read_canonical(study_root / "configuration.json")["inputs"][
                "entry_checkpoint"
            ]
        ),
        "residual_model": pilot_runner._file_binding(
            study_root / "residual_model.json"
        ),
        "study_configuration": pilot_runner._file_binding(
            study_root / "configuration.json"
        ),
        "study_manifest": pilot_runner._file_binding(
            study_root / "artifact_manifest.json"
        ),
        "study_metrics": pilot_runner._file_binding(study_root / "metrics.json"),
        "study_report": pilot_runner._file_binding(study_root / "report.json"),
        "train_dataset": pilot_runner._file_binding(
            corpus_root / "train_dataset_full.json"
        ),
    }


def build_registration(
    *,
    repo_root: Path | str,
    source_commit: str,
    study_root: Path | str,
    corpus_root: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    study_path = Path(study_root).resolve()
    corpus_path = Path(corpus_root).resolve()
    study_report = study._read_canonical(study_path / "report.json")
    corpus_registration = base_runner._read_canonical(
        corpus_path / "registration.json"
    )
    if study_report.get("verdict") != (
        "large_corpus_card_uplift_residual_ready_for_reserved_audit_proposal"
    ) or study_report.get("audit_accessed") is not False:
        raise LargeCorpusAuditBlocked("study verdict differs")
    try:
        if pilot_runner._git(root, "cat-file", "-t", source_commit) != "commit":
            raise LargeCorpusAuditBlocked("source commit is unavailable")
    except pilot_runner.CardOnlyRunnerBlocked as exc:
        raise LargeCorpusAuditBlocked("source commit is unavailable") from exc
    output = Path(output_dir).resolve()
    checkpoint_root = base_runner.PRODUCTION_CHECKPOINT_ROOT.resolve()
    if output == checkpoint_root or checkpoint_root in output.parents:
        raise LargeCorpusAuditBlocked("output overlaps production checkpoints")
    return validate_registration(
        {
            "authority": copy.deepcopy(AUTHORITY),
            "configuration": _configuration(),
            "inputs": _inputs(study_path, corpus_path),
            "native": copy.deepcopy(corpus_registration["native"]),
            "operations": copy.deepcopy(OPERATIONS),
            "output_dir": output.as_posix(),
            "production_isolation": copy.deepcopy(
                corpus_registration["production_isolation"]
            ),
            "schedule": {
                "audit_seeds": list(AUDIT_SEEDS),
                "seed_status": "reserved-untouched-audit",
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
        raise LargeCorpusAuditBlocked("registration must be an object")
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
        raise LargeCorpusAuditBlocked("registration fields differ")
    if registration["authority"] != AUTHORITY:
        raise LargeCorpusAuditBlocked("authority differs")
    if registration["configuration"] != _configuration():
        raise LargeCorpusAuditBlocked("configuration differs")
    if registration["operations"] != OPERATIONS:
        raise LargeCorpusAuditBlocked("operations differ")
    if registration["schedule"] != {
        "audit_seeds": list(AUDIT_SEEDS),
        "seed_status": "reserved-untouched-audit",
    }:
        raise LargeCorpusAuditBlocked("schedule differs")
    inputs = registration.get("inputs")
    expected_inputs = {
        "corpus_registration",
        "corpus_report",
        "development_dataset",
        "entry_checkpoint",
        "residual_model",
        "study_configuration",
        "study_manifest",
        "study_metrics",
        "study_report",
        "train_dataset",
    }
    if not isinstance(inputs, dict) or set(inputs) != expected_inputs:
        raise LargeCorpusAuditBlocked("inputs differ")
    source = registration.get("source")
    if (
        not isinstance(source, dict)
        or set(source) != {"bindings", "commit", "repo_root"}
        or set(source.get("bindings", {})) != set(BOUND_SOURCE_PATHS)
        or not isinstance(source.get("commit"), str)
        or len(source["commit"]) != 40
    ):
        raise LargeCorpusAuditBlocked("source differs")
    bindings = [*inputs.values(), *source["bindings"].values()]
    if any(
        not isinstance(binding, dict)
        or set(binding) != {"path", "sha256", "size_bytes"}
        for binding in bindings
    ):
        raise LargeCorpusAuditBlocked("file bindings differ")
    native = registration.get("native")
    identity = native.get("identity") if isinstance(native, dict) else None
    if not isinstance(identity, dict) or identity.get(
        "adapter_api_version"
    ) != adapter.ADAPTER_API_VERSION:
        raise LargeCorpusAuditBlocked("native identity differs")
    if not isinstance(registration.get("output_dir"), str):
        raise LargeCorpusAuditBlocked("output differs")
    return registration


def _binding_matches(binding: Mapping[str, Any]) -> bool:
    return pilot_runner._file_binding(binding["path"]) == dict(binding)


def _load_frozen_inputs(
    registration: Mapping[str, Any],
) -> tuple[Any, uplift.UpliftModel, uplift.ResidualConfiguration, bytes]:
    inputs = registration["inputs"]
    try:
        bootstrap = ranking.restore_entry_bootstrap(
            Path(inputs["entry_checkpoint"]["path"]).read_bytes()
        )
        model_bytes = Path(inputs["residual_model"]["path"]).read_bytes()
        model, configuration = uplift.restore_uplift_model(model_bytes)
    except (OSError, ranking.CounterfactualRankingBlocked, uplift.UpliftCrossfitBlocked) as exc:
        raise LargeCorpusAuditBlocked(str(exc)) from exc
    if configuration != uplift.ResidualConfiguration(shrinkage=1, strength=128):
        raise LargeCorpusAuditBlocked("frozen configuration differs")
    return bootstrap, model, configuration, model_bytes


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
        raise LargeCorpusAuditBlocked("registered source is not an ancestor") from exc
    if _source_bindings(root, source["commit"]) != source["bindings"] or any(
        not _binding_matches(binding) for binding in registration["inputs"].values()
    ):
        raise LargeCorpusAuditBlocked("registered source or input bytes differ")
    inputs = registration["inputs"]
    study_report = study._read_canonical(inputs["study_report"]["path"])
    study_manifest = study._read_canonical(inputs["study_manifest"]["path"])
    study_configuration = study._read_canonical(
        inputs["study_configuration"]["path"]
    )
    corpus_report = study._read_canonical(inputs["corpus_report"]["path"])
    corpus_registration = base_runner._read_canonical(
        inputs["corpus_registration"]["path"]
    )
    expected_verdict = (
        "large_corpus_card_uplift_residual_ready_for_reserved_audit_proposal"
    )
    if (
        study_report.get("verdict") != expected_verdict
        or study_report.get("audit_accessed") is not False
        or study_report.get("model") != inputs["residual_model"]
        or study_report.get("selected_configuration")
        != {"shrinkage": 1, "strength": 128}
        or study_manifest.get("verdict") != expected_verdict
        or study_manifest.get("artifacts", {}).get("report.json")
        != inputs["study_report"]
        or study_manifest.get("artifacts", {}).get("residual_model.json")
        != inputs["residual_model"]
        or study_configuration.get("inputs", {}).get("entry_checkpoint")
        != inputs["entry_checkpoint"]
        or study_configuration.get("inputs", {}).get("train_dataset")
        != inputs["train_dataset"]
        or study_configuration.get("inputs", {}).get("development_dataset")
        != inputs["development_dataset"]
        or corpus_report.get("audit_accessed") is not False
        or corpus_report.get("schedule", {}).get("reserved_audit_seeds")
        != list(AUDIT_SEEDS)
        or corpus_registration.get("native") != registration["native"]
        or corpus_registration.get("production_isolation")
        != registration["production_isolation"]
    ):
        raise LargeCorpusAuditBlocked("study or corpus lineage differs")
    _load_frozen_inputs(registration)
    native = registration["native"]["identity"]
    if any(
        not _binding_matches(binding)
        for binding in [
            native["module"],
            *native["dependency_closure"]["dependencies"],
        ]
    ):
        raise LargeCorpusAuditBlocked("native bytes differ")
    if not base_runner.production_isolation_matches(registration):
        raise LargeCorpusAuditBlocked("production isolation differs")
    if list(process_observer()):
        raise LargeCorpusAuditBlocked("game or CommunicationMod is active")
    output = Path(registration["output_dir"]).resolve()
    staging = output.with_name(f".{output.name}.{source['commit']}.staging")
    checkpoint_root = Path(
        registration["production_isolation"]["production_checkpoints"]["path"]
    ).resolve()
    if (
        output.exists()
        or staging.exists()
        or output == checkpoint_root
        or checkpoint_root in output.parents
    ):
        raise LargeCorpusAuditBlocked("output boundary differs")
    return {
        "checks": {
            "audit_schedule_bound": True,
            "forbidden_processes_absent": True,
            "frozen_model_restorable_without_fitting": True,
            "native_bytes_bound_without_loading": True,
            "production_isolation_bound": True,
            "source_and_lineage_bound": True,
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
        raise LargeCorpusAuditBlocked(str(exc)) from exc


def _write_artifact(
    staging: Path, output: Path, name: str, payload: bytes
) -> dict[str, Any]:
    (staging / name).write_bytes(payload)
    return {
        "path": (output / name).as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
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
    staging = output.with_name(
        f".{output.name}.{registration['source']['commit']}.staging"
    )
    started = float(clock())
    if not math.isfinite(started):
        raise LargeCorpusAuditBlocked("runner clock is invalid")
    deadline = started + MAX_CHARGED_SECONDS
    bootstrap, model, configuration, model_bytes = _load_frozen_inputs(registration)
    entry_before = pilot.encode_candidate_card_policy(bootstrap)
    staging.mkdir(parents=False, exist_ok=False)
    _write_artifact(staging, output, "residual_model.json", model_bytes)
    factory = environment_factory_loader(registration["native"]["identity"])
    audit = _collect(factory, deadline=deadline, clock=clock)
    if len(audit.rows) < MIN_AUDIT_SOURCE_STATES:
        raise LargeCorpusAuditBlocked("audit source support floor is unmet")
    dataset_payload = ranking.encode_counterfactual_partition(audit)
    if len(dataset_payload) > MAX_DATASET_BYTES or ranking.encode_counterfactual_partition(
        ranking.restore_counterfactual_partition(dataset_payload)
    ) != dataset_payload:
        raise LargeCorpusAuditBlocked("audit dataset boundary differs")
    base_scores = study._base_scores(bootstrap, audit.rows)
    candidate_scores, unseen = uplift.score_residual_rows(
        audit.rows, base_scores, model, configuration
    )
    base_metrics = uplift.evaluate_scores(audit.rows, base_scores)
    candidate_metrics = uplift.evaluate_scores(audit.rows, candidate_scores)
    comparison = uplift.compare_predictions(base_metrics, candidate_metrics)
    checks = study._development_checks(base_metrics, candidate_metrics, comparison)
    if pilot.encode_candidate_card_policy(bootstrap) != entry_before:
        raise LargeCorpusAuditBlocked("entry checkpoint changed during audit")
    if uplift.encode_uplift_model(model, configuration) != model_bytes:
        raise LargeCorpusAuditBlocked("residual model changed during audit")
    if not base_runner.production_isolation_matches(registration):
        raise LargeCorpusAuditBlocked("production isolation changed during audit")
    if list(process_observer()):
        raise LargeCorpusAuditBlocked("game or CommunicationMod started during audit")
    elapsed = float(clock()) - started
    if not math.isfinite(elapsed) or elapsed < 0 or elapsed > MAX_CHARGED_SECONDS:
        raise LargeCorpusAuditBlocked("charged time exceeds registration")
    ready = all(checks.values())
    verdict = (
        "large_corpus_card_uplift_residual_audit_ready_for_fresh_eval_proposal"
        if ready
        else "large_corpus_card_uplift_residual_audit_not_ready"
    )
    dataset_binding = _write_artifact(
        staging, output, "audit_dataset_full.json", dataset_payload
    )
    registration_binding = _write_artifact(
        staging,
        output,
        "registration.json",
        base_runner._canonical_bytes(registration),
    )
    preflight_binding = _write_artifact(
        staging, output, "preflight.json", base_runner._canonical_bytes(preflight)
    )
    metrics = {
        "base": {
            key: item for key, item in base_metrics.items() if key != "predictions"
        },
        "candidate": {
            key: item
            for key, item in candidate_metrics.items()
            if key != "predictions"
        },
        "checks": checks,
        "comparison": comparison,
    }
    report = {
        "audit_dataset": dataset_binding,
        "authority": copy.deepcopy(AUTHORITY),
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
            "source_states": len(audit.rows),
            "unseen_take_actions": unseen,
        },
        "metrics": metrics,
        "registration": registration_binding,
        "preflight": preflight_binding,
        "schema_version": REPORT_SCHEMA_VERSION,
        "verdict": verdict,
    }
    report_binding = _write_artifact(
        staging, output, "report.json", base_runner._canonical_bytes(report)
    )
    terminal = {
        "action_branches": audit.action_branches,
        "authority": copy.deepcopy(AUTHORITY),
        "audit_source_states": len(audit.rows),
        "report": report_binding,
        "schema_version": TERMINAL_SCHEMA_VERSION,
        "verdict": verdict,
    }
    _write_artifact(
        staging, output, "terminal.json", base_runner._canonical_bytes(terminal)
    )
    staging.rename(output)
    return terminal


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    register = subparsers.add_parser("register")
    register.add_argument("--repo-root", required=True)
    register.add_argument("--source-commit", required=True)
    register.add_argument("--study-root", default=str(DEFAULT_STUDY_ROOT))
    register.add_argument("--corpus-root", default=str(DEFAULT_CORPUS_ROOT))
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
                study_root=args.study_root,
                corpus_root=args.corpus_root,
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
        LargeCorpusAuditBlocked,
        OSError,
        base_runner.RankingRunnerBlocked,
        subprocess.SubprocessError,
        uplift.UpliftCrossfitBlocked,
    ) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
