"""Evaluate one frozen shop ranker against a robust initialization baseline."""

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
from analysis_scripts import noncombat_state_conditioned_shop_ranking as ranking
from analysis_scripts.noncombat_state_conditioned_ranker import (
    ARCHITECTURE_ID,
    StateConditionedCandidateRanker,
)


DEFAULT_NATIVE_REGISTRATION = event.DEFAULT_NATIVE_REGISTRATION
DEFAULT_CURRENT_BRIDGE_INPUT = event.DEFAULT_CURRENT_BRIDGE_INPUT
DEFAULT_MODEL = Path(
    "reports/noncombat_state_conditioned_shop_ranking_20260814_r1/model.json"
)
DEFAULT_OUTPUT_DIR = Path(
    "reports/noncombat_shop_robust_initialization_evaluation_20260814_r1"
)
EXPECTED_MODEL_SHA256 = (
    "3aa983a52a8bbe385735c6c18cd1b4b7f06c20b987edd7a07da8a30a51708b06"
)
EXPECTED_SELECTED_EPOCH = 4
EVALUATION_SEEDS = tuple(range(95428, 95460))
UNTRAINED_MODEL_SEEDS = tuple(range(32))
UNTRAINED_QUANTILE = 0.75
MAX_SOURCE_STATES = 16
MAX_ACTION_BRANCHES = 256
MAX_CENSORED_SOURCES = 16
REPLAY_SOURCE_COUNT = 4
MIN_SOURCE_STATES = 12
MIN_INFORMATIVE_STATES = 4
MAX_CHARGED_SECONDS = 7_200.0
SCHEMA_VERSION = "noncombat-shop-robust-initialization-evaluation-v1"
MANIFEST_SCHEMA_VERSION = "noncombat-shop-robust-initialization-manifest-v1"
BOUND_SOURCE_PATHS = tuple(
    dict.fromkeys(
        (
            Path("analysis_scripts/noncombat_shop_robust_initialization_evaluation.py"),
            *ranking.BOUND_SOURCE_PATHS,
        )
    )
)


class RobustShopEvaluationBlocked(RuntimeError):
    """Raised when the fixed fresh shop evaluation cannot remain valid."""


@dataclass(frozen=True)
class RobustEvaluationResult:
    configuration: dict[str, Any]
    evaluation: route.RoutePartition
    metrics: dict[str, Any]
    report: dict[str, Any]


def _canonical_bytes(value: Any) -> bytes:
    return event._canonical_bytes(value)


def _sha256_file(path: Path) -> str:
    return event._sha256_file(path)


def _new_untrained_model(
    *, seed: int, input_dim: int, hidden_dim: int
) -> StateConditionedCandidateRanker:
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed)
        model = StateConditionedCandidateRanker(input_dim, hidden_dim)
    return model.to(device="cpu", dtype=torch.float32).eval()


def load_bound_model(
    path: Path,
    *,
    expected_sha256: str = EXPECTED_MODEL_SHA256,
) -> tuple[StateConditionedCandidateRanker, dict[str, Any]]:
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise RobustShopEvaluationBlocked("bound shop model identity differs")
    value = json.loads(payload.decode("ascii"))
    if not isinstance(value, dict):
        raise RobustShopEvaluationBlocked("bound shop model must be an object")
    architecture = value.get("architecture")
    if not isinstance(architecture, dict):
        raise RobustShopEvaluationBlocked("bound shop model architecture differs")
    if (
        architecture.get("architecture_id") != ARCHITECTURE_ID
        or architecture.get("device") != "cpu"
        or architecture.get("dtype") != "float32"
        or architecture.get("state_conditioned") is not True
        or value.get("selected_epoch") != EXPECTED_SELECTED_EPOCH
    ):
        raise RobustShopEvaluationBlocked("bound shop model contract differs")
    input_dim = architecture.get("state_input_dim")
    candidate_dim = architecture.get("candidate_input_dim")
    hidden_dim = architecture.get("hidden_dim")
    if (
        isinstance(input_dim, bool)
        or not isinstance(input_dim, int)
        or input_dim <= 0
        or candidate_dim != input_dim
        or isinstance(hidden_dim, bool)
        or not isinstance(hidden_dim, int)
        or hidden_dim <= 0
    ):
        raise RobustShopEvaluationBlocked("bound shop model dimensions differ")
    model = StateConditionedCandidateRanker(input_dim, hidden_dim).to(
        device="cpu", dtype=torch.float32
    )
    try:
        model_codec._restore_model_state(model, value.get("state"), "shop model")
    except Exception as exc:
        raise RobustShopEvaluationBlocked("bound shop model state differs") from exc
    model.eval()
    return model, value


def nearest_rank_quantile(values: Sequence[float], quantile: float) -> float:
    normalized = tuple(float(value) for value in values)
    if (
        not normalized
        or not math.isfinite(quantile)
        or not 0 < quantile <= 1
        or any(not math.isfinite(value) for value in normalized)
    ):
        raise RobustShopEvaluationBlocked("untrained quantile input differs")
    ordered = sorted(normalized)
    index = math.ceil(quantile * len(ordered)) - 1
    return ordered[index]


def run_evaluation(
    environment_factory: Callable[[int], Any],
    session_factory: Callable[[int], Any],
    model: StateConditionedCandidateRanker,
    model_payload: Mapping[str, Any],
    *,
    evaluation_seeds: Sequence[int] = EVALUATION_SEEDS,
    minimum_rows: int = MIN_SOURCE_STATES,
    minimum_informative: int = MIN_INFORMATIVE_STATES,
    maximum_charged_seconds: float = MAX_CHARGED_SECONDS,
    clock: Callable[[], float] = time.monotonic,
    branch_evaluator: Callable[..., Any] | None = None,
) -> RobustEvaluationResult:
    schedule = tuple(evaluation_seeds)
    if not schedule or len(set(schedule)) != len(schedule):
        raise RobustShopEvaluationBlocked("fresh evaluation seed schedule differs")
    started = float(clock())
    partition = ranking._collect_partition(
        environment_factory,
        session_factory,
        name="development",
        seeds=schedule,
        max_source_states=MAX_SOURCE_STATES,
        max_action_branches=MAX_ACTION_BRANCHES,
        max_censored_sources=MAX_CENSORED_SOURCES,
        replay_source_count=REPLAY_SOURCE_COUNT,
        minimum_complete_sources=minimum_rows,
        minimum_informative_sources=minimum_informative,
        maximum_charged_seconds=maximum_charged_seconds,
        clock=clock,
        branch_evaluator=branch_evaluator,
    )
    input_dim = partition.rows[0].state_features.shape[0]
    architecture = model_payload["architecture"]
    if input_dim != architecture["state_input_dim"]:
        raise RobustShopEvaluationBlocked("fresh feature width differs from model")
    trained = route.evaluate_model(model, partition.rows)
    current = route.evaluate_current(partition.rows)
    changes = route._prediction_changes(current, trained)
    untrained_rows = []
    for seed in UNTRAINED_MODEL_SEEDS:
        baseline = _new_untrained_model(
            seed=seed,
            input_dim=input_dim,
            hidden_dim=int(architecture["hidden_dim"]),
        )
        metrics = route.evaluate_model(baseline, partition.rows)
        untrained_rows.append(
            {
                "maximum_regret": metrics["maximum_regret"],
                "mean_regret": metrics["mean_regret"],
                "model_seed": seed,
                "weighted_pairwise_accuracy": metrics["weighted_pairwise_accuracy"],
            }
        )
    pairwise_values = [row["weighted_pairwise_accuracy"] for row in untrained_rows]
    threshold = nearest_rank_quantile(pairwise_values, UNTRAINED_QUANTILE)
    checks = {
        "corrects_at_least_one_current_decision": changes["corrected"] >= 1,
        "fresh_informative_support": sum(row.informative for row in partition.rows) >= minimum_informative,
        "fresh_support": len(partition.rows) >= minimum_rows,
        "maximum_regret_noninferior_to_current": trained["maximum_regret"] <= current["maximum_regret"] + 1e-12,
        "mean_regret_improves_current": trained["mean_regret"] + 1e-12 < current["mean_regret"],
        "pairwise_exceeds_untrained_q75": trained["weighted_pairwise_accuracy"] > threshold + 1e-12,
        "worsened_not_more_than_corrected": changes["worsened"] <= changes["corrected"],
    }
    elapsed = float(clock()) - started
    if not math.isfinite(elapsed) or elapsed < 0 or elapsed > maximum_charged_seconds:
        raise RobustShopEvaluationBlocked("fresh evaluation charged time differs")
    verdict = (
        "shop_ranker_ready_for_live_shadow_proposal"
        if all(checks.values())
        else "shop_ranker_not_ready_after_robust_fresh_evaluation"
    )
    metrics = {
        "changes_vs_current": changes,
        "checks": checks,
        "current": current,
        "trained": trained,
        "untrained_distribution": {
            "model_metrics": untrained_rows,
            "model_seeds": list(UNTRAINED_MODEL_SEEDS),
            "pairwise_maximum": max(pairwise_values),
            "pairwise_mean": math.fsum(pairwise_values) / len(pairwise_values),
            "pairwise_minimum": min(pairwise_values),
            "pairwise_q75": threshold,
            "quantile": UNTRAINED_QUANTILE,
        },
        "verdict": verdict,
    }
    configuration = {
        "evaluation_seeds": list(schedule),
        "maximum_charged_seconds": maximum_charged_seconds,
        "model_sha256": EXPECTED_MODEL_SHA256,
        "model_selected_epoch": EXPECTED_SELECTED_EPOCH,
        "schema_version": SCHEMA_VERSION,
        "untrained_model_seeds": list(UNTRAINED_MODEL_SEEDS),
        "untrained_quantile": UNTRAINED_QUANTILE,
    }
    report = {
        "authority": {
            "formal_rl": False,
            "gameplay": False,
            "policy_intervention": False,
            "promotion": False,
            "qualification": False,
        },
        "charged_seconds": elapsed,
        "evaluation": ranking._partition_summary(partition),
        "operations": {
            "communication_mod": False,
            "evaluation": True,
            "gameplay": False,
            "model_fitting": False,
            "model_loading": True,
            "native_loading": True,
            "production_checkpoint_access": False,
            "protected_seed_access": False,
            "training": False,
        },
        "schema_version": SCHEMA_VERSION,
        "verdict": verdict,
    }
    return RobustEvaluationResult(
        configuration=configuration,
        evaluation=partition,
        metrics=metrics,
        report=report,
    )


def _source_identity(repo_root: Path) -> dict[str, Any]:
    files = [
        {"path": path.as_posix(), "sha256": _sha256_file(repo_root / path), "size_bytes": (repo_root / path).stat().st_size}
        for path in BOUND_SOURCE_PATHS
    ]
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo_root, check=True,
            capture_output=True, text=True, encoding="ascii"
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RobustShopEvaluationBlocked("cannot resolve source commit") from exc
    return {"commit": commit, "files": files, "source_sha256": hashlib.sha256(_canonical_bytes(files)).hexdigest()}


def write_artifacts(
    output: Path,
    result: RobustEvaluationResult,
    identity: Mapping[str, Any],
    model_binding: Mapping[str, Any],
) -> None:
    output.mkdir(parents=False, exist_ok=False)
    artifacts = {
        "configuration.json": _canonical_bytes(result.configuration),
        "evaluation_dataset.json": route.encode_partition(result.evaluation),
        "metrics.json": _canonical_bytes(result.metrics),
        "report.json": _canonical_bytes({**result.report, "identity": copy.deepcopy(dict(identity)), "model_binding": copy.deepcopy(dict(model_binding))}),
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
            "# Robust Shop Initialization Evaluation",
            "",
            f"- Verdict: `{result.report['verdict']}`",
            f"- Fresh sources: `{result.report['evaluation']['source_count']}`",
            f"- Current mean regret: `{metrics['current']['mean_regret']:.6f}`",
            f"- Trained mean regret: `{metrics['trained']['mean_regret']:.6f}`",
            f"- Trained pairwise accuracy: `{metrics['trained']['weighted_pairwise_accuracy']:.6f}`",
            f"- Untrained q75 pairwise accuracy: `{metrics['untrained_distribution']['pairwise_q75']:.6f}`",
            "",
            "This fixed fresh evaluation performs no fitting and grants no intervention or promotion authority.",
            "",
        )
    )
    (output / "report.md").write_text(markdown, encoding="ascii", newline="\n")


def execute_cli(args: argparse.Namespace) -> dict[str, Any]:
    logging.getLogger().setLevel(logging.ERROR)
    repo_root = Path(args.repo_root).resolve()
    output = Path(args.output_dir).resolve()
    model_path = Path(args.model).resolve()
    if output.exists():
        raise RobustShopEvaluationBlocked("output directory already exists")
    model, model_payload = load_bound_model(model_path)
    native_registration_path = Path(args.native_registration).resolve()
    bridge_input_path = Path(args.current_bridge_input).resolve()
    native_registration = event._read_json(native_registration_path)
    bridge_input = event._read_json(bridge_input_path)
    try:
        native_identity = native_registration["native"]["identity"]
        metadata_binding = bridge_input["identity"]["metadata"]
        current_policy = bridge_input["current_policy"]
    except KeyError as exc:
        raise RobustShopEvaluationBlocked("registered input fields differ") from exc
    metadata_path = Path(metadata_binding["path"]).resolve()
    if not metadata_path.is_file() or _sha256_file(metadata_path) != metadata_binding["sha256"]:
        raise RobustShopEvaluationBlocked("Current policy metadata bytes differ")
    if list(native_runner._forbidden_processes()):
        raise RobustShopEvaluationBlocked("game or CommunicationMod is active")
    if "sts_lightspeed_noncombat_adapter" not in sys.modules:
        preload_native_registration(native_registration_path)
    environment_factory = native_runner._load_environment_factory(native_identity)
    metadata = current_bridge.MetadataCatalog(metadata_path)

    def session_factory(_seed: int) -> current_bridge.CurrentPolicyBridgeSession:
        return current_bridge.CurrentPolicyBridgeSession(
            metadata=metadata, current_policy=current_policy,
            event_semantics_identity=None, require_global_metadata_match=True,
            simulator_provenance=native_identity["provenance"],
        )

    result = run_evaluation(environment_factory, session_factory, model, model_payload)
    if list(native_runner._forbidden_processes()):
        raise RobustShopEvaluationBlocked("game or CommunicationMod started during execution")
    identity = {
        "current_bridge_input": {"path": bridge_input_path.as_posix(), "sha256": _sha256_file(bridge_input_path)},
        "metadata": copy.deepcopy(metadata_binding),
        "native_module": copy.deepcopy(native_identity["module"]),
        "native_registration": {"path": native_registration_path.as_posix(), "sha256": _sha256_file(native_registration_path)},
        "source": _source_identity(repo_root),
    }
    model_binding = {"path": model_path.as_posix(), "sha256": _sha256_file(model_path), "selected_epoch": model_payload["selected_epoch"]}
    write_artifacts(output, result, identity, model_binding)
    return {
        "fresh_sources": len(result.evaluation.rows),
        "output_dir": output.as_posix(),
        "pairwise_q75": result.metrics["untrained_distribution"]["pairwise_q75"],
        "trained_pairwise": result.metrics["trained"]["weighted_pairwise_accuracy"],
        "verdict": result.report["verdict"],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run")
    run.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    run.add_argument("--native-registration", default=str(DEFAULT_NATIVE_REGISTRATION))
    run.add_argument("--current-bridge-input", default=str(DEFAULT_CURRENT_BRIDGE_INPUT))
    run.add_argument("--model", default=str(DEFAULT_MODEL))
    run.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command != "run":
        raise RobustShopEvaluationBlocked("unsupported command")
    print(json.dumps(execute_cli(args), ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
