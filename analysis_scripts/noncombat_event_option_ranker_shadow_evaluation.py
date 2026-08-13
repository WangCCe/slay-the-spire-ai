"""Evaluate one bound event-option ranker on a disjoint no-training cohort."""

from __future__ import annotations

import argparse
import copy
import ctypes
from ctypes import wintypes
import hashlib
import importlib.util
import json
import logging
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import types
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from typing import Any


DEFAULT_NATIVE_REGISTRATION = Path(
    "reports/noncombat_card_counterfactual_corpus_expansion_20260813_r1/registration.json"
)
DEFAULT_CURRENT_BRIDGE_INPUT = Path(
    "reports/noncombat_current_policy_simulator_bridge_20260802_r2_input.json"
)
DEFAULT_TRAINING_DIR = Path(
    "reports/noncombat_event_option_counterfactual_ranking_20260814_r1"
)
DEFAULT_OUTPUT_DIR = Path(
    "reports/noncombat_event_option_ranker_shadow_evaluation_20260814_r2"
)
SEEDS = tuple(range(94400, 94464))
MAX_EVENT_STATES_PER_SEED = 2
MAX_SOURCE_STATES = 128
MAX_ACTION_BRANCHES = 512
MAX_CENSORED_SOURCES = 32
MIN_SOURCE_STATES = 96
MIN_INFORMATIVE_STATES = 32
MIN_EVENT_IDS = 12
MAX_CHARGED_SECONDS = 7_200.0
SCHEMA_VERSION = "noncombat-event-option-ranker-shadow-evaluation-v1"
MANIFEST_SCHEMA_VERSION = "noncombat-event-option-ranker-shadow-manifest-v1"
BOUND_SOURCE_PATHS = (
    Path("analysis_scripts/noncombat_event_option_ranker_shadow_evaluation.py"),
    Path("analysis_scripts/noncombat_event_option_counterfactual_ranking.py"),
    Path("analysis_scripts/noncombat_route_counterfactual_ranking.py"),
    Path("analysis_scripts/noncombat_card_action_counterfactual_credit.py"),
    Path("analysis_scripts/noncombat_current_policy_simulator_bridge.py"),
    Path("analysis_scripts/noncombat_state_conditioned_policy_input.py"),
    Path("analysis_scripts/noncombat_state_conditioned_ranker.py"),
    Path("analysis_scripts/noncombat_event_option_semantics.py"),
)
_EARLY_NATIVE_HANDLES: list[Any] = []


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


def _early_preload_native() -> None:
    if not (__name__ == "__main__" and len(sys.argv) >= 2 and sys.argv[1] == "run"):
        return
    try:
        if "--native-registration" in sys.argv:
            registration_path = Path(
                sys.argv[sys.argv.index("--native-registration") + 1]
            ).resolve()
        else:
            registration_path = DEFAULT_NATIVE_REGISTRATION.resolve()
        registration = json.loads(registration_path.read_text(encoding="ascii"))
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
                raise RuntimeError("native dependency cycle differs")
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
            raise RuntimeError("native dependency graph differs")
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
            raise RuntimeError("native module spec is unavailable")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules["sts_lightspeed_noncombat_adapter"] = module
    except (IndexError, KeyError, OSError, RuntimeError, ValueError) as exc:
        raise RuntimeError("event shadow early native load failed") from exc


if __name__ == "__main__":
    _bootstrap_direct_script_imports()
    _early_preload_native()


from analysis_scripts import noncombat_card_acceptance_empirical_successor_runtime as model_codec
from analysis_scripts import noncombat_card_action_counterfactual_credit as credit
from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot_runner as native_runner
from analysis_scripts import noncombat_current_policy_simulator_bridge as current_bridge
from analysis_scripts import noncombat_event_option_counterfactual_ranking as training
from analysis_scripts import noncombat_route_counterfactual_ranking as route
from analysis_scripts.noncombat_state_conditioned_ranker import (
    ARCHITECTURE_ID,
    StateConditionedCandidateRanker,
)


class EventShadowBlocked(RuntimeError):
    """Raised when the fixed event shadow evaluation cannot produce evidence."""


def _canonical_bytes(value: Any) -> bytes:
    try:
        return route._canonical_bytes(value)
    except route.RouteExperimentBlocked as exc:
        raise EventShadowBlocked(str(exc)) from exc


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = path.read_bytes()
        value = json.loads(payload.decode("ascii"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EventShadowBlocked(f"cannot read JSON: {path}") from exc
    if not isinstance(value, dict):
        raise EventShadowBlocked(f"JSON root must be an object: {path}")
    return value


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_bound_model(
    training_dir: Path,
) -> tuple[StateConditionedCandidateRanker, dict[str, Any]]:
    root = training_dir.resolve()
    manifest_path = root / "artifact_manifest.json"
    model_path = root / "model.json"
    metrics_path = root / "metrics.json"
    report_path = root / "report.json"
    manifest = _read_json(manifest_path)
    bindings = {
        row.get("path"): row
        for row in manifest.get("artifacts", ())
        if isinstance(row, Mapping)
    }
    for name, path in (
        ("model.json", model_path),
        ("metrics.json", metrics_path),
        ("report.json", report_path),
    ):
        binding = bindings.get(name)
        if (
            not isinstance(binding, Mapping)
            or not path.is_file()
            or path.stat().st_size != binding.get("size_bytes")
            or _sha256_file(path) != binding.get("sha256")
        ):
            raise EventShadowBlocked(f"training {name} manifest binding differs")
    model_value = _read_json(model_path)
    metrics = _read_json(metrics_path)
    report = _read_json(report_path)
    if _canonical_bytes(model_value) != model_path.read_bytes():
        raise EventShadowBlocked("training model is not canonical")
    if model_value.get("schema_version") != training.MODEL_SCHEMA_VERSION:
        raise EventShadowBlocked("training model schema differs")
    if report.get("verdict") != (
        "event_counterfactual_ranker_ready_for_shadow_evaluation_proposal"
    ):
        raise EventShadowBlocked("training verdict does not permit shadow evaluation")
    selection = metrics.get("selection", {})
    if (
        selection.get("selected_epoch") != model_value.get("selected_epoch")
        or selection.get("selected_confidence_threshold")
        != model_value.get("selected_confidence_threshold")
        or model_value.get("selected_confidence_threshold")
        not in training.CONFIDENCE_THRESHOLDS
    ):
        raise EventShadowBlocked("training selected policy identity differs")
    architecture = model_value.get("architecture", {})
    if (
        architecture.get("architecture_id") != ARCHITECTURE_ID
        or architecture.get("state_input_dim")
        != architecture.get("candidate_input_dim")
        or not isinstance(architecture.get("state_input_dim"), int)
        or not isinstance(architecture.get("hidden_dim"), int)
    ):
        raise EventShadowBlocked("training model architecture differs")
    model = StateConditionedCandidateRanker(
        architecture["state_input_dim"], architecture["hidden_dim"]
    )
    try:
        model_codec._restore_model_state(model, model_value.get("state"), "event model")
        if model_codec._encode_model_state(model) != model_value["state"]:
            raise EventShadowBlocked("training model state round-trip differs")
    except model_codec.SuccessorRuntimeError as exc:
        raise EventShadowBlocked(str(exc)) from exc
    model.eval()
    identity = {
        "directory": root.as_posix(),
        "manifest": {
            "path": manifest_path.as_posix(),
            "sha256": _sha256_file(manifest_path),
        },
        "metrics": {
            "path": metrics_path.as_posix(),
            "sha256": _sha256_file(metrics_path),
        },
        "model": {
            "path": model_path.as_posix(),
            "sha256": _sha256_file(model_path),
        },
        "report": {
            "path": report_path.as_posix(),
            "sha256": _sha256_file(report_path),
        },
        "selected_confidence_threshold": model_value["selected_confidence_threshold"],
        "selected_epoch": model_value["selected_epoch"],
    }
    return model, identity


def _per_event_metrics(
    partition: route.RoutePartition,
    current: Mapping[str, Any],
    selected: Mapping[str, Any],
) -> dict[str, Any]:
    current_rows = {row["source_sha256"]: row for row in current["predictions"]}
    selected_rows = {row["source_sha256"]: row for row in selected["predictions"]}
    result: dict[str, dict[str, float | int]] = defaultdict(
        lambda: {
            "action_changes": 0,
            "corrected": 0,
            "current_regret": 0.0,
            "selected_regret": 0.0,
            "source_states": 0,
            "worsened": 0,
        }
    )
    for row in partition.rows:
        raw = row.candidates[0].get("raw", {})
        event_id = raw.get("event_id") if isinstance(raw, Mapping) else None
        if not isinstance(event_id, str) or not event_id:
            raise EventShadowBlocked("shadow event identity is missing")
        before = current_rows[row.source_sha256]
        after = selected_rows[row.source_sha256]
        values = result[event_id]
        values["source_states"] += 1
        values["action_changes"] += before["action_id"] != after["action_id"]
        values["corrected"] += after["regret"] < before["regret"]
        values["worsened"] += after["regret"] > before["regret"]
        values["current_regret"] += float(before["regret"])
        values["selected_regret"] += float(after["regret"])
    return dict(sorted(result.items()))


def evaluate_shadow(
    model: StateConditionedCandidateRanker,
    partition: route.RoutePartition,
    *,
    confidence_threshold: float,
    minimum_rows: int = MIN_SOURCE_STATES,
    minimum_informative: int = MIN_INFORMATIVE_STATES,
    minimum_event_ids: int = MIN_EVENT_IDS,
) -> tuple[dict[str, Any], str]:
    current = training._with_tail(route.evaluate_current(partition.rows))
    selected = training.evaluate_gated_policy(
        model,
        partition.rows,
        confidence_threshold=confidence_threshold,
    )
    changes = training._changes(current, selected)
    informative = sum(row.informative for row in partition.rows)
    event_ids = len(training._event_ids(partition))
    checks = {
        "action_changes_at_least_one": changes["action_changes"] >= 1,
        "corrects_at_least_one_current_decision": changes["corrected"] >= 1,
        "event_diversity": event_ids >= minimum_event_ids,
        "informative_support": informative >= minimum_informative,
        "maximum_regret_noninferior_to_current": (
            selected["maximum_regret"] <= current["maximum_regret"] + 1e-12
        ),
        "mean_regret_improves_current": (
            selected["mean_regret"] + 1e-12 < current["mean_regret"]
        ),
        "p95_regret_noninferior_to_current": (
            selected["p95_regret"] <= current["p95_regret"] + 1e-12
        ),
        "source_support": len(partition.rows) >= minimum_rows,
        "worsened_not_more_than_corrected": changes["worsened"] <= changes["corrected"],
    }
    verdict = (
        "event_ranker_shadow_benefit_replicated"
        if all(checks.values())
        else "event_ranker_shadow_benefit_not_replicated"
    )
    disagreement_confidences = sorted(
        float(row["confidence"])
        for row in selected["predictions"]
        if row["learned_action_id"] != row["current_action_id"]
    )
    metrics = {
        "changes_vs_current": changes,
        "checks": checks,
        "confidence": {
            "disagreement_count": len(disagreement_confidences),
            "maximum": max(disagreement_confidences) if disagreement_confidences else None,
            "minimum": min(disagreement_confidences) if disagreement_confidences else None,
        },
        "current": current,
        "per_event": _per_event_metrics(partition, current, selected),
        "selected": selected,
        "shadow_access_count": 1,
        "verdict": verdict,
    }
    return metrics, verdict


def _source_identity(repo_root: Path) -> dict[str, Any]:
    files = [
        {
            "path": path.as_posix(),
            "sha256": _sha256_file(repo_root / path),
            "size_bytes": (repo_root / path).stat().st_size,
        }
        for path in BOUND_SOURCE_PATHS
    ]
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
            encoding="ascii",
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise EventShadowBlocked("cannot resolve source commit") from exc
    return {
        "commit": commit,
        "files": files,
        "source_sha256": hashlib.sha256(_canonical_bytes(files)).hexdigest(),
    }


def _write_artifacts(
    output: Path,
    *,
    configuration: dict[str, Any],
    partition: route.RoutePartition,
    metrics: dict[str, Any],
    report: dict[str, Any],
) -> None:
    output.mkdir(parents=False, exist_ok=False)
    artifacts = {
        "configuration.json": _canonical_bytes(configuration),
        "dataset.json": training.encode_event_partition(partition),
        "metrics.json": _canonical_bytes(metrics),
        "report.json": _canonical_bytes(report),
    }
    for name, payload in artifacts.items():
        (output / name).write_bytes(payload)
    manifest = {
        "artifacts": [
            {
                "path": name,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
            }
            for name, payload in sorted(artifacts.items())
        ],
        "schema_version": MANIFEST_SCHEMA_VERSION,
    }
    (output / "artifact_manifest.json").write_bytes(_canonical_bytes(manifest))
    current = metrics["current"]
    selected = metrics["selected"]
    changes = metrics["changes_vs_current"]
    lines = (
        "# Event Option Ranker Fresh Shadow Evaluation",
        "",
        f"- Verdict: `{metrics['verdict']}`",
        f"- Charged seconds: `{report['charged_seconds']:.3f}`",
        f"- Source states: `{len(partition.rows)}`",
        f"- Informative states: `{sum(row.informative for row in partition.rows)}`",
        f"- Distinct event ids: `{len(training._event_ids(partition))}`",
        "",
        "| Policy | Mean regret | P95 regret | Max regret | Unique-best accuracy |",
        "| --- | ---: | ---: | ---: | ---: |",
        f"| Current | {current['mean_regret']:.6f} | {current['p95_regret']:.6f} | {current['maximum_regret']:.6f} | {current['unique_best_accuracy'] or 0:.6f} |",
        f"| Selected | {selected['mean_regret']:.6f} | {selected['p95_regret']:.6f} | {selected['maximum_regret']:.6f} | {selected['unique_best_accuracy'] or 0:.6f} |",
        "",
        f"Action changes versus Current: {changes['action_changes']}; corrected: {changes['corrected']}; worsened: {changes['worsened']}.",
        "",
        "This is a no-training simulator shadow evaluation. It grants no gameplay, production loading, qualification, or promotion authority.",
        "",
    )
    (output / "report.md").write_text("\n".join(lines), encoding="ascii", newline="\n")


def execute_cli(args: argparse.Namespace) -> dict[str, Any]:
    logging.getLogger().setLevel(logging.ERROR)
    repo_root = Path(args.repo_root).resolve()
    output = Path(args.output_dir).resolve()
    if output.exists():
        raise EventShadowBlocked("output directory already exists")
    model, training_identity = load_bound_model(Path(args.training_dir))
    native_registration_path = Path(args.native_registration).resolve()
    bridge_input_path = Path(args.current_bridge_input).resolve()
    native_registration = _read_json(native_registration_path)
    bridge_input = _read_json(bridge_input_path)
    try:
        native_identity = native_registration["native"]["identity"]
        metadata_binding = bridge_input["identity"]["metadata"]
        current_policy = bridge_input["current_policy"]
    except KeyError as exc:
        raise EventShadowBlocked("registered input fields differ") from exc
    metadata_path = Path(metadata_binding["path"]).resolve()
    if not metadata_path.is_file() or _sha256_file(metadata_path) != metadata_binding["sha256"]:
        raise EventShadowBlocked("Current policy metadata bytes differ")
    if list(native_runner._forbidden_processes()):
        raise EventShadowBlocked("game or CommunicationMod is active")
    environment_factory = native_runner._load_environment_factory(native_identity)
    metadata = current_bridge.MetadataCatalog(metadata_path)

    def baseline_session_factory(_seed: int) -> current_bridge.CurrentPolicyBridgeSession:
        return current_bridge.CurrentPolicyBridgeSession(
            metadata=metadata,
            current_policy=current_policy,
            event_semantics_identity=None,
            require_global_metadata_match=True,
            simulator_provenance=native_identity["provenance"],
        )

    def branch_evaluator(environment: Any, **kwargs: Any) -> credit.BranchTrace:
        return route.evaluate_action_with_current_continuation(
            environment,
            continuation_session_factory=lambda: baseline_session_factory(0),
            **kwargs,
        )

    started = time.monotonic()
    deadline = started + MAX_CHARGED_SECONDS
    try:
        partition = route.collect_outcome_partition(
            environment_factory,
            baseline_session_factory,
            target_category="event",
            name="development",
            seeds=SEEDS,
            max_source_states=MAX_SOURCE_STATES,
            max_action_branches=MAX_ACTION_BRANCHES,
            max_censored_sources=MAX_CENSORED_SOURCES,
            max_route_states_per_seed=MAX_EVENT_STATES_PER_SEED,
            deadline=deadline,
            branch_evaluator=branch_evaluator,
        )
    except route.RouteExperimentBlocked as exc:
        raise EventShadowBlocked(str(exc)) from exc
    metrics, verdict = evaluate_shadow(
        model,
        partition,
        confidence_threshold=training_identity["selected_confidence_threshold"],
    )
    elapsed = time.monotonic() - started
    if not math.isfinite(elapsed) or elapsed < 0 or elapsed > MAX_CHARGED_SECONDS:
        raise EventShadowBlocked("shadow charged time differs")
    if list(native_runner._forbidden_processes()):
        raise EventShadowBlocked("game or CommunicationMod started during execution")
    configuration = {
        "maximum_action_branches": MAX_ACTION_BRANCHES,
        "maximum_censored_sources": MAX_CENSORED_SOURCES,
        "maximum_charged_seconds": MAX_CHARGED_SECONDS,
        "maximum_event_states_per_seed": MAX_EVENT_STATES_PER_SEED,
        "maximum_source_states": MAX_SOURCE_STATES,
        "minimum_event_ids": MIN_EVENT_IDS,
        "minimum_informative_states": MIN_INFORMATIVE_STATES,
        "minimum_source_states": MIN_SOURCE_STATES,
        "schema_version": SCHEMA_VERSION,
        "seeds": list(SEEDS),
    }
    identity = {
        "current_bridge_input": {
            "path": bridge_input_path.as_posix(),
            "sha256": _sha256_file(bridge_input_path),
        },
        "metadata": copy.deepcopy(metadata_binding),
        "native_module": copy.deepcopy(native_identity["module"]),
        "native_registration": {
            "path": native_registration_path.as_posix(),
            "sha256": _sha256_file(native_registration_path),
        },
        "source": _source_identity(repo_root),
        "training": training_identity,
    }
    report = {
        "authority": {
            "formal_rl": False,
            "gameplay": False,
            "policy_loading": False,
            "promotion": False,
            "qualification": False,
        },
        "charged_seconds": elapsed,
        "identity": identity,
        "operations": {
            "communication_mod": False,
            "gameplay": False,
            "model_fitting": False,
            "model_loading": True,
            "native_loading": True,
            "production_checkpoint_access": False,
            "seed_access": True,
            "training": False,
        },
        "schema_version": SCHEMA_VERSION,
        "shadow": training._partition_summary(partition),
        "shadow_access_count": 1,
        "verdict": verdict,
    }
    _write_artifacts(
        output,
        configuration=configuration,
        partition=partition,
        metrics=metrics,
        report=report,
    )
    return {
        "informative_source_states": sum(row.informative for row in partition.rows),
        "output_dir": output.as_posix(),
        "source_states": len(partition.rows),
        "verdict": verdict,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run")
    run.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    run.add_argument("--native-registration", default=str(DEFAULT_NATIVE_REGISTRATION))
    run.add_argument("--current-bridge-input", default=str(DEFAULT_CURRENT_BRIDGE_INPUT))
    run.add_argument("--training-dir", default=str(DEFAULT_TRAINING_DIR))
    run.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command != "run":
        raise EventShadowBlocked("unsupported command")
    print(json.dumps(execute_cli(args), ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
