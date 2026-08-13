"""Train one bounded event-option ranker with a conservative Current fallback."""

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
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from typing import Any


DEFAULT_NATIVE_REGISTRATION = Path(
    "reports/noncombat_card_counterfactual_corpus_expansion_20260813_r1/registration.json"
)
DEFAULT_CURRENT_BRIDGE_INPUT = Path(
    "reports/noncombat_current_policy_simulator_bridge_20260802_r2_input.json"
)
DEFAULT_OUTPUT_DIR = Path(
    "reports/noncombat_event_option_counterfactual_ranking_20260814_r1"
)
TRAIN_SEEDS = tuple(range(94100, 94228))
DEVELOPMENT_SEEDS = tuple(range(94228, 94260))
CHECKPOINT_EPOCHS = (1, 2, 4, 8, 16)
CONFIDENCE_THRESHOLDS = (0.50, 0.55, 0.60, 0.70, 0.80, 0.90)
MAX_EVENT_STATES_PER_SEED = 2
MAX_TRAIN_SOURCE_STATES = 256
MAX_DEVELOPMENT_SOURCE_STATES = 64
MAX_TRAIN_BRANCHES = 1_024
MAX_DEVELOPMENT_BRANCHES = 256
MAX_TRAIN_CENSORED_SOURCES = 64
MAX_DEVELOPMENT_CENSORED_SOURCES = 16
MIN_TRAIN_SOURCE_STATES = 192
MIN_TRAIN_INFORMATIVE_STATES = 72
MIN_DEVELOPMENT_SOURCE_STATES = 48
MIN_DEVELOPMENT_INFORMATIVE_STATES = 16
MIN_DEVELOPMENT_EVENT_IDS = 8
MAX_CHARGED_SECONDS = 7_200.0
SCHEMA_VERSION = "noncombat-event-option-counterfactual-ranking-v1"
DATASET_SCHEMA_VERSION = "noncombat-event-option-counterfactual-dataset-v1"
MODEL_SCHEMA_VERSION = "noncombat-event-option-counterfactual-model-v1"
MANIFEST_SCHEMA_VERSION = "noncombat-event-option-counterfactual-manifest-v1"
BOUND_SOURCE_PATHS = (
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
        raise RuntimeError("event ranker early native load failed") from exc


if __name__ == "__main__":
    _bootstrap_direct_script_imports()
    _early_preload_native()


import torch

from analysis_scripts import noncombat_card_acceptance_empirical_successor_runtime as model_codec
from analysis_scripts import noncombat_card_action_counterfactual_credit as credit
from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot_runner as native_runner
from analysis_scripts import noncombat_current_policy_simulator_bridge as current_bridge
from analysis_scripts import noncombat_route_counterfactual_ranking as route
from analysis_scripts.noncombat_state_conditioned_ranker import StateConditionedCandidateRanker


class EventRankingBlocked(RuntimeError):
    """Raised when the fixed event learning experiment cannot produce evidence."""


def _canonical_bytes(value: Any) -> bytes:
    try:
        return route._canonical_bytes(value)
    except route.RouteExperimentBlocked as exc:
        raise EventRankingBlocked(str(exc)) from exc


def _event_ids(partition: route.RoutePartition) -> tuple[str, ...]:
    values: set[str] = set()
    for row in partition.rows:
        raw = row.candidates[0].get("raw", {})
        event_id = raw.get("event_id") if isinstance(raw, Mapping) else None
        if not isinstance(event_id, str) or not event_id:
            raise EventRankingBlocked("event candidate identity is missing")
        values.add(event_id)
    return tuple(sorted(values))


def encode_event_partition(partition: route.RoutePartition) -> bytes:
    value = json.loads(route.encode_partition(partition).decode("ascii"))
    value["schema_version"] = DATASET_SCHEMA_VERSION
    value["target_category"] = "event"
    return _canonical_bytes(value)


def restore_event_partition(payload: bytes) -> route.RoutePartition:
    try:
        value = json.loads(payload.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EventRankingBlocked("event dataset JSON is invalid") from exc
    if not isinstance(value, dict) or _canonical_bytes(value) != payload:
        raise EventRankingBlocked("event dataset is not canonical")
    if value.pop("schema_version", None) != DATASET_SCHEMA_VERSION:
        raise EventRankingBlocked("event dataset schema differs")
    if value.pop("target_category", None) != "event":
        raise EventRankingBlocked("event dataset target category differs")
    value["schema_version"] = route.DATASET_SCHEMA_VERSION
    try:
        partition = route.restore_partition(route._canonical_bytes(value))
    except route.RouteExperimentBlocked as exc:
        raise EventRankingBlocked(str(exc)) from exc
    _event_ids(partition)
    return partition


def _percentile95(regrets: Sequence[float]) -> float:
    values = sorted(float(value) for value in regrets)
    if not values or any(not math.isfinite(value) or value < 0 for value in values):
        raise EventRankingBlocked("regret values are invalid")
    return values[max(0, math.ceil(0.95 * len(values)) - 1)]


def _with_tail(metrics: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(metrics))
    result["p95_regret"] = _percentile95(
        [float(row["regret"]) for row in result["predictions"]]
    )
    return result


def evaluate_gated_policy(
    model: StateConditionedCandidateRanker,
    rows: Sequence[route.RouteRow],
    *,
    confidence_threshold: float,
) -> dict[str, Any]:
    if confidence_threshold not in CONFIDENCE_THRESHOLDS:
        raise EventRankingBlocked("confidence threshold differs")
    regrets: list[float] = []
    predictions: list[dict[str, Any]] = []
    unique_best = unique_correct = overrides = 0
    model.eval()
    with torch.no_grad():
        for row in rows:
            action_ids = [candidate["action_id"] for candidate in row.candidates]
            current_index = action_ids.index(row.current_action_id)
            scores = model(row.state_features, row.candidate_features)
            learned_index = int(torch.argmax(scores).item())
            score_advantage = float(
                scores[learned_index].item() - scores[current_index].item()
            )
            confidence = float(torch.sigmoid(torch.tensor(score_advantage)).item())
            selected_index = (
                learned_index
                if learned_index != current_index and confidence >= confidence_threshold
                else current_index
            )
            overrides += int(selected_index != current_index)
            returns = row.action_returns
            best_return = max(returns)
            regret = best_return - returns[selected_index]
            regrets.append(regret)
            best_indices = [
                index for index, value in enumerate(returns) if value == best_return
            ]
            if len(best_indices) == 1:
                unique_best += 1
                unique_correct += int(selected_index == best_indices[0])
            predictions.append(
                {
                    "action_id": action_ids[selected_index],
                    "confidence": confidence,
                    "current_action_id": row.current_action_id,
                    "decision_index": row.decision_index,
                    "learned_action_id": action_ids[learned_index],
                    "regret": regret,
                    "seed": row.seed,
                    "source_sha256": row.source_sha256,
                }
            )
    if not regrets:
        raise EventRankingBlocked("gated evaluation has no rows")
    return {
        "confidence_threshold": confidence_threshold,
        "maximum_regret": max(regrets),
        "mean_regret": math.fsum(regrets) / len(regrets),
        "override_count": overrides,
        "p95_regret": _percentile95(regrets),
        "predictions": predictions,
        "unique_best_accuracy": unique_correct / unique_best if unique_best else None,
        "unique_best_rows": unique_best,
    }


def _changes(current: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, int]:
    try:
        return route._prediction_changes(current, candidate)
    except route.RouteExperimentBlocked as exc:
        raise EventRankingBlocked(str(exc)) from exc


def _partition_summary(partition: route.RoutePartition) -> dict[str, Any]:
    spreads = [max(row.action_returns) - min(row.action_returns) for row in partition.rows]
    return {
        "action_branches": partition.action_branches,
        "budget_exhausted": partition.budget_exhausted,
        "censor_reasons": dict(
            sorted(Counter(row["reason"] for row in partition.censored_sources).items())
        ),
        "censored_sources": len(partition.censored_sources),
        "distinct_event_ids": len(_event_ids(partition)),
        "event_ids": list(_event_ids(partition)),
        "informative_source_states": sum(row.informative for row in partition.rows),
        "return_spread_maximum": max(spreads) if spreads else None,
        "return_spread_mean": math.fsum(spreads) / len(spreads) if spreads else None,
        "root_native_transitions": partition.root_native_transitions,
        "source_states": len(partition.rows),
    }


def _collect_partition(
    environment_factory: Callable[[int], Any],
    baseline_session_factory: Callable[[int], Any],
    *,
    name: str,
    seeds: Sequence[int],
    deadline: float,
    clock: Callable[[], float],
    branch_evaluator: Callable[..., credit.BranchTrace],
) -> route.RoutePartition:
    train = name == "train"
    try:
        return route.collect_outcome_partition(
            environment_factory,
            baseline_session_factory,
            target_category="event",
            name=name,
            seeds=seeds,
            max_source_states=(
                MAX_TRAIN_SOURCE_STATES if train else MAX_DEVELOPMENT_SOURCE_STATES
            ),
            max_action_branches=(MAX_TRAIN_BRANCHES if train else MAX_DEVELOPMENT_BRANCHES),
            max_censored_sources=(
                MAX_TRAIN_CENSORED_SOURCES if train else MAX_DEVELOPMENT_CENSORED_SOURCES
            ),
            max_route_states_per_seed=MAX_EVENT_STATES_PER_SEED,
            deadline=deadline,
            clock=clock,
            branch_evaluator=branch_evaluator,
        )
    except route.RouteExperimentBlocked as exc:
        raise EventRankingBlocked(str(exc)) from exc


def run_experiment(
    environment_factory: Callable[[int], Any],
    baseline_session_factory: Callable[[int], Any],
    *,
    train_seeds: Sequence[int] = TRAIN_SEEDS,
    development_seeds: Sequence[int] = DEVELOPMENT_SEEDS,
    minimum_train_rows: int = MIN_TRAIN_SOURCE_STATES,
    minimum_train_informative: int = MIN_TRAIN_INFORMATIVE_STATES,
    minimum_development_rows: int = MIN_DEVELOPMENT_SOURCE_STATES,
    minimum_development_informative: int = MIN_DEVELOPMENT_INFORMATIVE_STATES,
    minimum_development_event_ids: int = MIN_DEVELOPMENT_EVENT_IDS,
    maximum_charged_seconds: float = MAX_CHARGED_SECONDS,
    clock: Callable[[], float] = time.monotonic,
    branch_evaluator: Callable[..., credit.BranchTrace] = credit.evaluate_action_branch_for_category,
) -> route.ExperimentResult:
    train_schedule = tuple(train_seeds)
    development_schedule = tuple(development_seeds)
    if not train_schedule or not development_schedule or set(train_schedule) & set(development_schedule):
        raise EventRankingBlocked("train and development seed schedules differ")
    started = float(clock())
    deadline = started + maximum_charged_seconds
    train = _collect_partition(
        environment_factory,
        baseline_session_factory,
        name="train",
        seeds=train_schedule,
        deadline=deadline,
        clock=clock,
        branch_evaluator=branch_evaluator,
    )
    train_informative = sum(row.informative for row in train.rows)
    if len(train.rows) < minimum_train_rows or train_informative < minimum_train_informative:
        raise EventRankingBlocked("train event support floor is unmet")
    fit_rows = tuple(row for row in train.rows if row.seed % 4 != 0)
    tune_rows = tuple(row for row in train.rows if row.seed % 4 == 0)
    if not fit_rows or not tune_rows:
        raise EventRankingBlocked("train-only fit/tune split is empty")
    current_tune = _with_tail(route.evaluate_current(tune_rows))
    checkpoint_metrics: list[dict[str, Any]] = []
    selected_model: StateConditionedCandidateRanker | None = None
    selected_epoch: int | None = None
    selected_threshold: float | None = None
    selected_key: tuple[float, float, int, int, float, int] | None = None
    for epoch in CHECKPOINT_EPOCHS:
        candidate, history = route.train_model(fit_rows, epochs=epoch)
        raw_tune = _with_tail(route.evaluate_model(candidate, tune_rows))
        threshold_rows: list[dict[str, Any]] = []
        for threshold in CONFIDENCE_THRESHOLDS:
            gated_tune = evaluate_gated_policy(
                candidate, tune_rows, confidence_threshold=threshold
            )
            changes = _changes(current_tune, gated_tune)
            key = (
                gated_tune["mean_regret"],
                gated_tune["maximum_regret"],
                changes["worsened"],
                -changes["corrected"],
                -threshold,
                epoch,
            )
            threshold_rows.append(
                {
                    "changes_vs_current": changes,
                    "confidence_threshold": threshold,
                    "maximum_regret": gated_tune["maximum_regret"],
                    "mean_regret": gated_tune["mean_regret"],
                    "override_count": gated_tune["override_count"],
                    "p95_regret": gated_tune["p95_regret"],
                }
            )
            if selected_key is None or key < selected_key:
                selected_key = key
                selected_model = candidate
                selected_epoch = epoch
                selected_threshold = threshold
        checkpoint_metrics.append(
            {
                "epoch": epoch,
                "fit_final_loss": history[-1]["mean_batch_loss"],
                "raw_tune": {
                    key: value for key, value in raw_tune.items() if key != "predictions"
                },
                "thresholds": threshold_rows,
            }
        )
    if selected_model is None or selected_epoch is None or selected_threshold is None:
        raise EventRankingBlocked("train-only selection failed")

    development = _collect_partition(
        environment_factory,
        baseline_session_factory,
        name="development",
        seeds=development_schedule,
        deadline=deadline,
        clock=clock,
        branch_evaluator=branch_evaluator,
    )
    development_informative = sum(row.informative for row in development.rows)
    development_events = len(_event_ids(development))
    input_dim = development.rows[0].state_features.shape[0] if development.rows else 0
    if input_dim <= 0:
        raise EventRankingBlocked("development event partition is empty")
    current = _with_tail(route.evaluate_current(development.rows))
    untrained = _with_tail(route.evaluate_model(route._new_model(input_dim), development.rows))
    raw = _with_tail(route.evaluate_model(selected_model, development.rows))
    gated = evaluate_gated_policy(
        selected_model,
        development.rows,
        confidence_threshold=selected_threshold,
    )
    changes = _changes(current, gated)
    checks = {
        "action_changes_at_least_one": changes["action_changes"] >= 1,
        "corrects_at_least_one_current_decision": changes["corrected"] >= 1,
        "development_event_diversity": development_events >= minimum_development_event_ids,
        "development_informative_support": (
            development_informative >= minimum_development_informative
        ),
        "development_support": len(development.rows) >= minimum_development_rows,
        "maximum_regret_noninferior_to_current": (
            gated["maximum_regret"] <= current["maximum_regret"] + 1e-12
        ),
        "mean_regret_improves_current": (
            gated["mean_regret"] + 1e-12 < current["mean_regret"]
        ),
        "p95_regret_noninferior_to_current": (
            gated["p95_regret"] <= current["p95_regret"] + 1e-12
        ),
        "raw_pairwise_accuracy_improves_initialization": (
            raw["weighted_pairwise_accuracy"]
            > untrained["weighted_pairwise_accuracy"] + 1e-12
        ),
        "worsened_not_more_than_corrected": changes["worsened"] <= changes["corrected"],
    }
    elapsed = float(clock()) - started
    if not math.isfinite(elapsed) or elapsed < 0 or elapsed > maximum_charged_seconds:
        raise EventRankingBlocked("event experiment charged time differs")
    verdict = (
        "event_counterfactual_ranker_ready_for_shadow_evaluation_proposal"
        if all(checks.values())
        else "event_counterfactual_ranker_not_ready_after_development"
    )
    metrics = {
        "changes_vs_current": changes,
        "checks": checks,
        "development": {
            "current": current,
            "gated": gated,
            "raw": raw,
            "untrained": untrained,
        },
        "development_access_count": 1,
        "selection": {
            "checkpoints": checkpoint_metrics,
            "current_tune": {
                key: value for key, value in current_tune.items() if key != "predictions"
            },
            "selected_confidence_threshold": selected_threshold,
            "selected_epoch": selected_epoch,
        },
        "verdict": verdict,
    }
    model_artifact = {
        "architecture": selected_model.architecture_metadata(),
        "model_seed": route.MODEL_SEED,
        "schema_version": MODEL_SCHEMA_VERSION,
        "selected_confidence_threshold": selected_threshold,
        "selected_epoch": selected_epoch,
        "state": model_codec._encode_model_state(selected_model),
    }
    configuration = {
        "batch_size": route.BATCH_SIZE,
        "checkpoint_epochs": list(CHECKPOINT_EPOCHS),
        "confidence_thresholds": list(CONFIDENCE_THRESHOLDS),
        "development_seeds": list(development_schedule),
        "learning_rate": route.LEARNING_RATE,
        "maximum_charged_seconds": maximum_charged_seconds,
        "maximum_event_states_per_seed": MAX_EVENT_STATES_PER_SEED,
        "model_seed": route.MODEL_SEED,
        "reward": "strict-primary-dominance:2*victory+floor/57",
        "schema_version": SCHEMA_VERSION,
        "train_seeds": list(train_schedule),
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
        "development": _partition_summary(development),
        "development_access_count": 1,
        "operations": {
            "communication_mod": False,
            "gameplay": False,
            "model_fitting": True,
            "native_loading": True,
            "production_checkpoint_access": False,
            "seed_access": True,
            "training": True,
        },
        "schema_version": SCHEMA_VERSION,
        "train": _partition_summary(train),
        "verdict": verdict,
    }
    return route.ExperimentResult(
        configuration=configuration,
        train=train,
        development=development,
        model=model_artifact,
        metrics=metrics,
        report=report,
    )


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="ascii"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EventRankingBlocked(f"cannot read JSON: {path}") from exc
    if not isinstance(value, dict):
        raise EventRankingBlocked(f"JSON root must be an object: {path}")
    return value


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
        raise EventRankingBlocked("cannot resolve source commit") from exc
    return {
        "commit": commit,
        "files": files,
        "source_sha256": hashlib.sha256(_canonical_bytes(files)).hexdigest(),
    }


def _write_artifacts(
    output: Path, result: route.ExperimentResult, identity: dict[str, Any]
) -> None:
    output.mkdir(parents=False, exist_ok=False)
    artifacts: dict[str, bytes] = {
        "configuration.json": _canonical_bytes(result.configuration),
        "development_dataset.json": encode_event_partition(result.development),
        "metrics.json": _canonical_bytes(result.metrics),
        "model.json": _canonical_bytes(result.model),
        "report.json": _canonical_bytes({**result.report, "identity": identity}),
        "train_dataset.json": encode_event_partition(result.train),
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
    development = result.metrics["development"]
    changes = result.metrics["changes_vs_current"]
    lines = (
        "# Outcome-Backed Event Option Ranking",
        "",
        f"- Verdict: `{result.report['verdict']}`",
        f"- Charged seconds: `{result.report['charged_seconds']:.3f}`",
        f"- Train source states: `{len(result.train.rows)}`",
        f"- Development source states: `{len(result.development.rows)}`",
        f"- Selected epoch: `{result.metrics['selection']['selected_epoch']}`",
        f"- Selected confidence threshold: `{result.metrics['selection']['selected_confidence_threshold']:.2f}`",
        "",
        "## Development",
        "",
        "| Policy | Mean regret | P95 regret | Max regret | Unique-best accuracy | Pairwise accuracy |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
        f"| Current | {development['current']['mean_regret']:.6f} | {development['current']['p95_regret']:.6f} | {development['current']['maximum_regret']:.6f} | {development['current']['unique_best_accuracy'] or 0:.6f} | n/a |",
        f"| Untrained | {development['untrained']['mean_regret']:.6f} | {development['untrained']['p95_regret']:.6f} | {development['untrained']['maximum_regret']:.6f} | {development['untrained']['unique_best_accuracy'] or 0:.6f} | {development['untrained']['weighted_pairwise_accuracy']:.6f} |",
        f"| Raw | {development['raw']['mean_regret']:.6f} | {development['raw']['p95_regret']:.6f} | {development['raw']['maximum_regret']:.6f} | {development['raw']['unique_best_accuracy'] or 0:.6f} | {development['raw']['weighted_pairwise_accuracy']:.6f} |",
        f"| Gated | {development['gated']['mean_regret']:.6f} | {development['gated']['p95_regret']:.6f} | {development['gated']['maximum_regret']:.6f} | {development['gated']['unique_best_accuracy'] or 0:.6f} | n/a |",
        "",
        f"Action changes versus Current: {changes['action_changes']}; corrected: {changes['corrected']}; worsened: {changes['worsened']}.",
        "",
        "Frozen Current-policy continuation is downstream context, not an unbiased live-policy value estimate. No gameplay, CommunicationMod, production checkpoint, qualification, or promotion authority is granted.",
        "",
    )
    (output / "report.md").write_text("\n".join(lines), encoding="ascii", newline="\n")


def execute_cli(args: argparse.Namespace) -> dict[str, Any]:
    logging.getLogger().setLevel(logging.ERROR)
    repo_root = Path(args.repo_root).resolve()
    output = Path(args.output_dir).resolve()
    if output.exists():
        raise EventRankingBlocked("output directory already exists")
    native_registration_path = Path(args.native_registration).resolve()
    bridge_input_path = Path(args.current_bridge_input).resolve()
    native_registration = _read_json(native_registration_path)
    bridge_input = _read_json(bridge_input_path)
    try:
        native_identity = native_registration["native"]["identity"]
        metadata_binding = bridge_input["identity"]["metadata"]
        current_policy = bridge_input["current_policy"]
    except KeyError as exc:
        raise EventRankingBlocked("registered input fields differ") from exc
    metadata_path = Path(metadata_binding["path"]).resolve()
    if not metadata_path.is_file() or _sha256_file(metadata_path) != metadata_binding["sha256"]:
        raise EventRankingBlocked("Current policy metadata bytes differ")
    if list(native_runner._forbidden_processes()):
        raise EventRankingBlocked("game or CommunicationMod is active")
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

    result = run_experiment(
        environment_factory,
        baseline_session_factory,
        branch_evaluator=branch_evaluator,
    )
    if list(native_runner._forbidden_processes()):
        raise EventRankingBlocked("game or CommunicationMod started during execution")
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
    }
    _write_artifacts(output, result, identity)
    return {
        "development_source_states": len(result.development.rows),
        "output_dir": output.as_posix(),
        "selected_confidence_threshold": result.metrics["selection"]["selected_confidence_threshold"],
        "selected_epoch": result.metrics["selection"]["selected_epoch"],
        "train_source_states": len(result.train.rows),
        "verdict": result.report["verdict"],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run")
    run.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    run.add_argument("--native-registration", default=str(DEFAULT_NATIVE_REGISTRATION))
    run.add_argument("--current-bridge-input", default=str(DEFAULT_CURRENT_BRIDGE_INPUT))
    run.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command != "run":
        raise EventRankingBlocked("unsupported command")
    print(json.dumps(execute_cli(args), ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
