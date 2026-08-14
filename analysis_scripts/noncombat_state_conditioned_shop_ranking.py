"""Collect fresh shop outcomes and train one state-conditioned CPU ranker."""

from __future__ import annotations

import argparse
import copy
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import logging
import math
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

from analysis_scripts.noncombat_native_preload import preload_native_registration


_DEFAULT_NATIVE_REGISTRATION = Path(
    "reports/noncombat_card_counterfactual_corpus_expansion_20260813_r1/registration.json"
)
if __name__ == "__main__" and len(sys.argv) >= 2 and sys.argv[1] == "run":
    if "--native-registration" in sys.argv:
        _registration = Path(
            sys.argv[sys.argv.index("--native-registration") + 1]
        ).resolve()
    else:
        _registration = _DEFAULT_NATIVE_REGISTRATION.resolve()
    preload_native_registration(_registration)


import torch

from analysis_scripts import noncombat_card_acceptance_empirical_successor_runtime as model_codec
from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot_runner as native_runner
from analysis_scripts import noncombat_current_policy_simulator_bridge as current_bridge
from analysis_scripts import noncombat_event_option_counterfactual_outcomes as event
from analysis_scripts import noncombat_route_counterfactual_ranking as route
from analysis_scripts import noncombat_shop_counterfactual_outcomes as shop
from analysis_scripts.noncombat_state_conditioned_policy_input import (
    project_state_conditioned_policy_input,
)


DEFAULT_NATIVE_REGISTRATION = event.DEFAULT_NATIVE_REGISTRATION
DEFAULT_CURRENT_BRIDGE_INPUT = event.DEFAULT_CURRENT_BRIDGE_INPUT
DEFAULT_OUTPUT_DIR = Path(
    "reports/noncombat_state_conditioned_shop_ranking_20260814_r1"
)
TRAIN_SEEDS = tuple(range(95300, 95396))
DEVELOPMENT_SEEDS = tuple(range(95396, 95428))
CHECKPOINT_EPOCHS = (1, 2, 4, 8, 16)
MAX_TRAIN_SOURCE_STATES = 64
MAX_DEVELOPMENT_SOURCE_STATES = 16
MAX_TRAIN_BRANCHES = 768
MAX_DEVELOPMENT_BRANCHES = 256
MAX_TRAIN_CENSORED = 48
MAX_DEVELOPMENT_CENSORED = 16
TRAIN_REPLAYS = 8
DEVELOPMENT_REPLAYS = 4
MIN_TRAIN_SOURCE_STATES = 48
MIN_TRAIN_INFORMATIVE_STATES = 18
MIN_DEVELOPMENT_SOURCE_STATES = 12
MIN_DEVELOPMENT_INFORMATIVE_STATES = 4
MIN_ACTION_KINDS = 4
MAX_CHARGED_SECONDS = 14_400.0
SCHEMA_VERSION = "noncombat-state-conditioned-shop-ranking-v1"
MODEL_SCHEMA_VERSION = "noncombat-state-conditioned-shop-model-v1"
MANIFEST_SCHEMA_VERSION = "noncombat-state-conditioned-shop-manifest-v1"
BOUND_SOURCE_PATHS = tuple(
    dict.fromkeys(
        (
            Path("analysis_scripts/noncombat_state_conditioned_shop_ranking.py"),
            *shop.BOUND_SOURCE_PATHS,
            Path("analysis_scripts/noncombat_state_conditioned_policy_input.py"),
            Path("analysis_scripts/noncombat_state_conditioned_ranker.py"),
        )
    )
)


class StateConditionedShopBlocked(RuntimeError):
    """Raised when fixed state-conditioned shop evidence cannot be produced."""


@dataclass(frozen=True)
class ShopRankingResult:
    configuration: dict[str, Any]
    train: route.RoutePartition
    development: route.RoutePartition
    model: dict[str, Any]
    metrics: dict[str, Any]
    report: dict[str, Any]


def _canonical_bytes(value: Any) -> bytes:
    return event._canonical_bytes(value)


def _sha256_file(path: Path) -> str:
    return event._sha256_file(path)


def _partition_from_result(
    name: str, result: shop.ShopOutcomeResult
) -> route.RoutePartition:
    rows: list[route.RouteRow] = []
    for row in result.rows:
        if row.state_features is None or row.candidate_features is None:
            raise StateConditionedShopBlocked("shop projected features are absent")
        if (
            row.state_features.ndim != 1
            or row.candidate_features.ndim != 2
            or row.candidate_features.shape[0] != len(row.candidates)
            or row.candidate_features.shape[1] != row.state_features.shape[0]
        ):
            raise StateConditionedShopBlocked("shop projected feature shape differs")
        rows.append(
            route.RouteRow(
                seed=row.seed,
                decision_index=row.decision_index,
                source_sha256=row.source_sha256,
                state_features=row.state_features.detach().clone(),
                candidate_features=row.candidate_features.detach().clone(),
                candidates=copy.deepcopy(row.candidates),
                branch_outcomes=copy.deepcopy(row.branch_outcomes),
                current_action_id=row.current_action_id,
            )
        )
    return route.RoutePartition(
        name=name,
        seeds=tuple(sorted({row.seed for row in rows})),
        rows=tuple(rows),
        action_branches=result.action_branches,
        root_native_transitions=result.root_native_transitions,
        censored_sources=copy.deepcopy(result.censored_sources),
        budget_exhausted=result.budget_exhausted,
    )


def _collect_partition(
    environment_factory: Callable[[int], Any],
    session_factory: Callable[[int], Any],
    *,
    name: str,
    seeds: Sequence[int],
    max_source_states: int,
    max_action_branches: int,
    max_censored_sources: int,
    replay_source_count: int,
    minimum_complete_sources: int,
    minimum_informative_sources: int,
    maximum_charged_seconds: float,
    clock: Callable[[], float],
    branch_evaluator: Callable[..., Any] | None = None,
) -> route.RoutePartition:
    result = shop.collect_shop_outcomes(
        environment_factory,
        session_factory,
        seeds=seeds,
        max_source_states=max_source_states,
        max_action_branches=max_action_branches,
        max_censored_sources=max_censored_sources,
        max_shop_states_per_seed=1,
        replay_source_count=replay_source_count,
        minimum_complete_sources=minimum_complete_sources,
        minimum_informative_sources=minimum_informative_sources,
        minimum_action_kinds=MIN_ACTION_KINDS,
        max_decisions=shop.MAX_DECISIONS_PER_CONTINUATION,
        maximum_charged_seconds=maximum_charged_seconds,
        clock=clock,
        branch_evaluator=branch_evaluator,
        projector=project_state_conditioned_policy_input,
    )
    if not all(result.checks.values()):
        raise StateConditionedShopBlocked(f"{name} shop support floor is unmet")
    return _partition_from_result(name, result)


def _hash_split(
    rows: Sequence[route.RouteRow],
) -> tuple[tuple[route.RouteRow, ...], tuple[route.RouteRow, ...]]:
    ordered = tuple(
        sorted(
            rows,
            key=lambda row: hashlib.sha256(
                f"shop-train-tune-v1:{row.source_sha256}".encode("ascii")
            ).hexdigest(),
        )
    )
    tune_count = max(1, len(ordered) // 4)
    tune = ordered[:tune_count]
    fit = ordered[tune_count:]
    if not fit or not tune:
        raise StateConditionedShopBlocked("train-only fit/tune split is empty")
    return fit, tune


def _partition_summary(partition: route.RoutePartition) -> dict[str, Any]:
    spreads = [max(row.action_returns) - min(row.action_returns) for row in partition.rows]
    return {
        "action_branches": partition.action_branches,
        "budget_exhausted": partition.budget_exhausted,
        "censored_sources": len(partition.censored_sources),
        "informative_sources": sum(row.informative for row in partition.rows),
        "maximum_return_spread": max(spreads) if spreads else None,
        "mean_return_spread": math.fsum(spreads) / len(spreads) if spreads else None,
        "root_native_transitions": partition.root_native_transitions,
        "source_count": len(partition.rows),
    }


def run_experiment(
    environment_factory: Callable[[int], Any],
    session_factory: Callable[[int], Any],
    *,
    train_seeds: Sequence[int] = TRAIN_SEEDS,
    development_seeds: Sequence[int] = DEVELOPMENT_SEEDS,
    minimum_train_rows: int = MIN_TRAIN_SOURCE_STATES,
    minimum_train_informative: int = MIN_TRAIN_INFORMATIVE_STATES,
    minimum_development_rows: int = MIN_DEVELOPMENT_SOURCE_STATES,
    minimum_development_informative: int = MIN_DEVELOPMENT_INFORMATIVE_STATES,
    maximum_charged_seconds: float = MAX_CHARGED_SECONDS,
    clock: Callable[[], float] = time.monotonic,
    branch_evaluator: Callable[..., Any] | None = None,
) -> ShopRankingResult:
    train_schedule = tuple(train_seeds)
    development_schedule = tuple(development_seeds)
    if (
        not train_schedule
        or not development_schedule
        or set(train_schedule) & set(development_schedule)
    ):
        raise StateConditionedShopBlocked("shop train/development seeds differ")
    started = float(clock())
    deadline = started + maximum_charged_seconds
    train = _collect_partition(
        environment_factory,
        session_factory,
        name="train",
        seeds=train_schedule,
        max_source_states=MAX_TRAIN_SOURCE_STATES,
        max_action_branches=MAX_TRAIN_BRANCHES,
        max_censored_sources=MAX_TRAIN_CENSORED,
        replay_source_count=TRAIN_REPLAYS,
        minimum_complete_sources=minimum_train_rows,
        minimum_informative_sources=minimum_train_informative,
        maximum_charged_seconds=max(0.001, deadline - float(clock())),
        clock=clock,
        branch_evaluator=branch_evaluator,
    )
    fit_rows, tune_rows = _hash_split(train.rows)
    checkpoints: list[dict[str, Any]] = []
    selected_epoch: int | None = None
    selected_key: tuple[float, float, int] | None = None
    for epoch in CHECKPOINT_EPOCHS:
        candidate, history = route.train_model(fit_rows, epochs=epoch)
        tune = route.evaluate_model(candidate, tune_rows)
        key = (tune["mean_regret"], -tune["weighted_pairwise_accuracy"], epoch)
        checkpoints.append(
            {
                "epoch": epoch,
                "fit_final_loss": history[-1]["mean_batch_loss"],
                "tune": {key: value for key, value in tune.items() if key != "predictions"},
            }
        )
        if selected_key is None or key < selected_key:
            selected_key = key
            selected_epoch = epoch
    if selected_epoch is None:
        raise StateConditionedShopBlocked("shop train-only selection failed")
    trained_model, final_history = route.train_model(
        train.rows, epochs=selected_epoch
    )

    development = _collect_partition(
        environment_factory,
        session_factory,
        name="development",
        seeds=development_schedule,
        max_source_states=MAX_DEVELOPMENT_SOURCE_STATES,
        max_action_branches=MAX_DEVELOPMENT_BRANCHES,
        max_censored_sources=MAX_DEVELOPMENT_CENSORED,
        replay_source_count=DEVELOPMENT_REPLAYS,
        minimum_complete_sources=minimum_development_rows,
        minimum_informative_sources=minimum_development_informative,
        maximum_charged_seconds=max(0.001, deadline - float(clock())),
        clock=clock,
        branch_evaluator=branch_evaluator,
    )
    input_dim = development.rows[0].state_features.shape[0]
    untrained = route.evaluate_model(route._new_model(input_dim), development.rows)
    trained = route.evaluate_model(trained_model, development.rows)
    current = route.evaluate_current(development.rows)
    changes = route._prediction_changes(current, trained)
    checks = {
        "corrects_at_least_one_current_decision": changes["corrected"] >= 1,
        "development_informative_support": sum(row.informative for row in development.rows) >= minimum_development_informative,
        "development_support": len(development.rows) >= minimum_development_rows,
        "maximum_regret_noninferior_to_current": trained["maximum_regret"] <= current["maximum_regret"] + 1e-12,
        "mean_regret_improves_current": trained["mean_regret"] + 1e-12 < current["mean_regret"],
        "pairwise_accuracy_improves_initialization": trained["weighted_pairwise_accuracy"] > untrained["weighted_pairwise_accuracy"] + 1e-12,
        "worsened_not_more_than_corrected": changes["worsened"] <= changes["corrected"],
    }
    elapsed = float(clock()) - started
    if not math.isfinite(elapsed) or elapsed < 0 or elapsed > maximum_charged_seconds:
        raise StateConditionedShopBlocked("shop experiment charged time differs")
    verdict = (
        "state_conditioned_shop_ranker_ready_for_fresh_shadow_proposal"
        if all(checks.values())
        else "state_conditioned_shop_ranker_not_ready_after_development"
    )
    metrics = {
        "changes_vs_current": changes,
        "checks": checks,
        "development": {"current": current, "trained": trained, "untrained": untrained},
        "development_access_count": 1,
        "selection": {"checkpoints": checkpoints, "selected_epoch": selected_epoch},
        "training_final_history": final_history,
        "verdict": verdict,
    }
    model = {
        "architecture": trained_model.architecture_metadata(),
        "model_seed": route.MODEL_SEED,
        "schema_version": MODEL_SCHEMA_VERSION,
        "selected_epoch": selected_epoch,
        "state": model_codec._encode_model_state(trained_model),
    }
    configuration = {
        "checkpoint_epochs": list(CHECKPOINT_EPOCHS),
        "development_seeds": list(development_schedule),
        "learning_rate": route.LEARNING_RATE,
        "maximum_charged_seconds": maximum_charged_seconds,
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
            "protected_seed_access": False,
            "seed_access": True,
            "training": True,
        },
        "schema_version": SCHEMA_VERSION,
        "train": _partition_summary(train),
        "verdict": verdict,
    }
    return ShopRankingResult(
        configuration=configuration,
        train=train,
        development=development,
        model=model,
        metrics=metrics,
        report=report,
    )


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
        raise StateConditionedShopBlocked("cannot resolve source commit") from exc
    return {
        "commit": commit,
        "files": files,
        "source_sha256": hashlib.sha256(_canonical_bytes(files)).hexdigest(),
    }


def _write_artifacts(
    output: Path, result: ShopRankingResult, identity: Mapping[str, Any]
) -> None:
    output.mkdir(parents=False, exist_ok=False)
    artifacts = {
        "configuration.json": _canonical_bytes(result.configuration),
        "development_dataset.json": route.encode_partition(result.development),
        "metrics.json": _canonical_bytes(result.metrics),
        "model.json": _canonical_bytes(result.model),
        "report.json": _canonical_bytes({**result.report, "identity": copy.deepcopy(dict(identity))}),
        "train_dataset.json": route.encode_partition(result.train),
    }
    for name, payload in artifacts.items():
        (output / name).write_bytes(payload)
    manifest = {
        "artifacts": [
            {"path": name, "sha256": hashlib.sha256(payload).hexdigest(), "size_bytes": len(payload)}
            for name, payload in sorted(artifacts.items())
        ],
        "schema_version": MANIFEST_SCHEMA_VERSION,
    }
    (output / "artifact_manifest.json").write_bytes(_canonical_bytes(manifest))
    metrics = result.metrics
    markdown = "\n".join(
        (
            "# State-Conditioned Shop Ranking",
            "",
            f"- Verdict: `{result.report['verdict']}`",
            f"- Selected epoch: `{metrics['selection']['selected_epoch']}`",
            f"- Train/development sources: `{result.report['train']['source_count']}/{result.report['development']['source_count']}`",
            f"- Current development mean regret: `{metrics['development']['current']['mean_regret']:.6f}`",
            f"- Trained development mean regret: `{metrics['development']['trained']['mean_regret']:.6f}`",
            f"- Trained pairwise accuracy: `{metrics['development']['trained']['weighted_pairwise_accuracy']:.6f}`",
            "",
            "This is one fixed offline simulator experiment and grants no live policy authority.",
            "",
        )
    )
    (output / "report.md").write_text(markdown, encoding="ascii", newline="\n")


def execute_cli(args: argparse.Namespace) -> dict[str, Any]:
    logging.getLogger().setLevel(logging.ERROR)
    repo_root = Path(args.repo_root).resolve()
    output = Path(args.output_dir).resolve()
    if output.exists():
        raise StateConditionedShopBlocked("output directory already exists")
    native_registration_path = Path(args.native_registration).resolve()
    bridge_input_path = Path(args.current_bridge_input).resolve()
    native_registration = event._read_json(native_registration_path)
    bridge_input = event._read_json(bridge_input_path)
    try:
        native_identity = native_registration["native"]["identity"]
        metadata_binding = bridge_input["identity"]["metadata"]
        current_policy = bridge_input["current_policy"]
    except KeyError as exc:
        raise StateConditionedShopBlocked("registered input fields differ") from exc
    metadata_path = Path(metadata_binding["path"]).resolve()
    if not metadata_path.is_file() or _sha256_file(metadata_path) != metadata_binding["sha256"]:
        raise StateConditionedShopBlocked("Current policy metadata bytes differ")
    if list(native_runner._forbidden_processes()):
        raise StateConditionedShopBlocked("game or CommunicationMod is active")
    if "sts_lightspeed_noncombat_adapter" not in sys.modules:
        preload_native_registration(native_registration_path)
    environment_factory = native_runner._load_environment_factory(native_identity)
    metadata = current_bridge.MetadataCatalog(metadata_path)

    def session_factory(_seed: int) -> current_bridge.CurrentPolicyBridgeSession:
        return current_bridge.CurrentPolicyBridgeSession(
            metadata=metadata,
            current_policy=current_policy,
            event_semantics_identity=None,
            require_global_metadata_match=True,
            simulator_provenance=native_identity["provenance"],
        )

    result = run_experiment(environment_factory, session_factory)
    if list(native_runner._forbidden_processes()):
        raise StateConditionedShopBlocked("game or CommunicationMod started during execution")
    identity = {
        "current_bridge_input": {"path": bridge_input_path.as_posix(), "sha256": _sha256_file(bridge_input_path)},
        "metadata": copy.deepcopy(metadata_binding),
        "native_module": copy.deepcopy(native_identity["module"]),
        "native_registration": {"path": native_registration_path.as_posix(), "sha256": _sha256_file(native_registration_path)},
        "source": _source_identity(repo_root),
    }
    _write_artifacts(output, result, identity)
    return {
        "development_sources": len(result.development.rows),
        "output_dir": output.as_posix(),
        "selected_epoch": result.metrics["selection"]["selected_epoch"],
        "train_sources": len(result.train.rows),
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
        raise StateConditionedShopBlocked("unsupported command")
    print(json.dumps(execute_cli(args), ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
