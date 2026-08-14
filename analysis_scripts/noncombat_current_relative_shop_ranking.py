"""Train a Current-relative shop ranker and evaluate one fresh gated policy."""

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
import torch.nn.functional as F

from analysis_scripts import noncombat_card_acceptance_empirical_successor_runtime as model_codec
from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot_runner as native_runner
from analysis_scripts import noncombat_current_policy_simulator_bridge as current_bridge
from analysis_scripts import noncombat_event_option_counterfactual_outcomes as event
from analysis_scripts import noncombat_route_counterfactual_ranking as route
from analysis_scripts import noncombat_state_conditioned_shop_ranking as ranking
from analysis_scripts.noncombat_state_conditioned_ranker import (
    StateConditionedCandidateRanker,
)


DEFAULT_NATIVE_REGISTRATION = event.DEFAULT_NATIVE_REGISTRATION
DEFAULT_CURRENT_BRIDGE_INPUT = event.DEFAULT_CURRENT_BRIDGE_INPUT
DEFAULT_TRAIN_DATASET = Path(
    "reports/noncombat_state_conditioned_shop_ranking_20260814_r1/train_dataset.json"
)
DEFAULT_OUTPUT_DIR = Path(
    "reports/noncombat_current_relative_shop_ranking_20260814_r1"
)
EXPECTED_TRAIN_SHA256 = (
    "e346d26e2e29d297b316d9247ef9cf6619bb3fce274b0b88f34d69a9be5f736a"
)
EXPECTED_TRAIN_SOURCES = 64
EXPECTED_FIT_SOURCES = 48
EXPECTED_TUNE_SOURCES = 16
CHECKPOINT_EPOCHS = (1, 2, 4, 8, 16, 32)
SCORE_MARGINS = (0.0, 0.01, 0.02, 0.05, 0.1, 0.2)
BATCH_SIZE = 16
FRESH_SEEDS = tuple(range(95460, 95492))
MAX_FRESH_SOURCE_STATES = 16
MAX_FRESH_BRANCHES = 256
MAX_FRESH_CENSORED = 16
FRESH_REPLAYS = 4
MIN_FRESH_SOURCES = 12
MIN_FRESH_INFORMATIVE = 4
MAX_CHARGED_SECONDS = 7_200.0
SCHEMA_VERSION = "noncombat-current-relative-shop-ranking-v1"
MODEL_SCHEMA_VERSION = "noncombat-current-relative-shop-model-v1"
MANIFEST_SCHEMA_VERSION = "noncombat-current-relative-shop-manifest-v1"
BOUND_SOURCE_PATHS = tuple(
    dict.fromkeys(
        (
            Path("analysis_scripts/noncombat_current_relative_shop_ranking.py"),
            *ranking.BOUND_SOURCE_PATHS,
        )
    )
)


class CurrentRelativeShopBlocked(RuntimeError):
    """Raised when fixed Current-relative shop evidence cannot be produced."""


@dataclass(frozen=True)
class TrainSelection:
    model: StateConditionedCandidateRanker
    selected_epoch: int
    selected_margin: float
    metrics: dict[str, Any]


@dataclass(frozen=True)
class CurrentRelativeResult:
    configuration: dict[str, Any]
    fresh: route.RoutePartition
    model: dict[str, Any]
    metrics: dict[str, Any]
    report: dict[str, Any]


def _canonical_bytes(value: Any) -> bytes:
    return event._canonical_bytes(value)


def _sha256_file(path: Path) -> str:
    return event._sha256_file(path)


def load_train_dataset(
    path: Path, *, expected_sha256: str = EXPECTED_TRAIN_SHA256
) -> route.RoutePartition:
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise CurrentRelativeShopBlocked("bound shop train dataset identity differs")
    try:
        partition = route.restore_partition(payload)
    except route.RouteExperimentBlocked as exc:
        raise CurrentRelativeShopBlocked(str(exc)) from exc
    if partition.name != "train" or len(partition.rows) != EXPECTED_TRAIN_SOURCES:
        raise CurrentRelativeShopBlocked("bound shop train dataset support differs")
    fit, tune = ranking._hash_split(partition.rows)
    if (len(fit), len(tune)) != (EXPECTED_FIT_SOURCES, EXPECTED_TUNE_SOURCES):
        raise CurrentRelativeShopBlocked("bound shop train split differs")
    return partition


def current_relative_loss(
    model: StateConditionedCandidateRanker,
    rows: Sequence[route.RouteRow],
) -> torch.Tensor | None:
    losses: list[torch.Tensor] = []
    weights: list[float] = []
    for row in rows:
        action_ids = [candidate["action_id"] for candidate in row.candidates]
        current_index = action_ids.index(row.current_action_id)
        scores = model(row.state_features, row.candidate_features)
        returns = row.action_returns
        for index, value in enumerate(returns):
            if index == current_index:
                continue
            difference = value - returns[current_index]
            if difference == 0:
                continue
            signed_margin = (
                scores[index] - scores[current_index]
                if difference > 0
                else scores[current_index] - scores[index]
            )
            weight = abs(difference)
            losses.append(weight * F.softplus(-signed_margin))
            weights.append(weight)
    if not losses:
        return None
    return torch.stack(losses).sum() / math.fsum(weights)


def train_current_relative(
    rows: Sequence[route.RouteRow], *, epochs: int
) -> tuple[StateConditionedCandidateRanker, list[dict[str, float | int]]]:
    normalized = tuple(rows)
    if not normalized or epochs <= 0:
        raise CurrentRelativeShopBlocked("Current-relative training input differs")
    input_dim = normalized[0].state_features.shape[0]
    model = route._new_model(input_dim)
    optimizer = torch.optim.Adam(model.parameters(), lr=route.LEARNING_RATE)
    history: list[dict[str, float | int]] = []
    for epoch in range(1, epochs + 1):
        model.train()
        losses: list[float] = []
        for offset in range(0, len(normalized), BATCH_SIZE):
            loss = current_relative_loss(
                model, normalized[offset : offset + BATCH_SIZE]
            )
            if loss is None:
                continue
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            optimizer.step()
            losses.append(float(loss.detach().item()))
        if not losses:
            raise CurrentRelativeShopBlocked("Current-relative train pairs are empty")
        history.append(
            {"epoch": epoch, "mean_batch_loss": math.fsum(losses) / len(losses)}
        )
    model.eval()
    return model, history


def evaluate_gated(
    model: StateConditionedCandidateRanker,
    rows: Sequence[route.RouteRow],
    *,
    score_margin: float,
) -> dict[str, Any]:
    if score_margin not in SCORE_MARGINS:
        raise CurrentRelativeShopBlocked("shop score margin differs")
    regrets: list[float] = []
    predictions: list[dict[str, Any]] = []
    overrides = 0
    model.eval()
    with torch.no_grad():
        for row in rows:
            action_ids = [candidate["action_id"] for candidate in row.candidates]
            current_index = action_ids.index(row.current_action_id)
            scores = model(row.state_features, row.candidate_features)
            learned_index = int(torch.argmax(scores).item())
            advantage = float(scores[learned_index].item() - scores[current_index].item())
            selected_index = (
                learned_index
                if learned_index != current_index and advantage >= score_margin
                else current_index
            )
            overrides += int(selected_index != current_index)
            returns = row.action_returns
            regret = max(returns) - returns[selected_index]
            regrets.append(regret)
            predictions.append(
                {
                    "action_id": action_ids[selected_index],
                    "current_action_id": row.current_action_id,
                    "decision_index": row.decision_index,
                    "learned_action_id": action_ids[learned_index],
                    "regret": regret,
                    "score_advantage": advantage,
                    "seed": row.seed,
                    "source_sha256": row.source_sha256,
                }
            )
    if not regrets:
        raise CurrentRelativeShopBlocked("gated shop evaluation is empty")
    ordered = sorted(regrets)
    return {
        "maximum_regret": max(regrets),
        "mean_regret": math.fsum(regrets) / len(regrets),
        "override_count": overrides,
        "p95_regret": ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)],
        "predictions": predictions,
        "score_margin": score_margin,
    }


def select_train_only(partition: route.RoutePartition) -> TrainSelection:
    fit_rows, tune_rows = ranking._hash_split(partition.rows)
    current = route.evaluate_current(tune_rows)
    checkpoint_rows: list[dict[str, Any]] = []
    selected: tuple[tuple[float, float, int, float, int], StateConditionedCandidateRanker, float, int] | None = None
    for epoch in CHECKPOINT_EPOCHS:
        model, history = train_current_relative(fit_rows, epochs=epoch)
        margin_rows = []
        for margin in SCORE_MARGINS:
            gated = evaluate_gated(model, tune_rows, score_margin=margin)
            changes = route._prediction_changes(current, gated)
            eligible = (
                gated["override_count"] >= 1
                and changes["corrected"] >= 1
                and changes["worsened"] == 0
                and gated["mean_regret"] + 1e-12 < current["mean_regret"]
                and gated["maximum_regret"] <= current["maximum_regret"] + 1e-12
            )
            margin_rows.append(
                {
                    "changes_vs_current": changes,
                    "eligible": eligible,
                    "maximum_regret": gated["maximum_regret"],
                    "mean_regret": gated["mean_regret"],
                    "override_count": gated["override_count"],
                    "score_margin": margin,
                }
            )
            if eligible:
                key = (
                    gated["mean_regret"],
                    gated["maximum_regret"],
                    -changes["corrected"],
                    -margin,
                    epoch,
                )
                if selected is None or key < selected[0]:
                    selected = (key, model, margin, epoch)
        checkpoint_rows.append(
            {
                "epoch": epoch,
                "fit_final_loss": history[-1]["mean_batch_loss"],
                "margins": margin_rows,
            }
        )
    if selected is None:
        raise CurrentRelativeShopBlocked("no harm-free train-only shop selection")
    _, model, margin, epoch = selected
    return TrainSelection(
        model=model,
        selected_epoch=epoch,
        selected_margin=margin,
        metrics={
            "checkpoints": checkpoint_rows,
            "current_tune": {key: value for key, value in current.items() if key != "predictions"},
            "fit_sources": len(fit_rows),
            "selected_epoch": epoch,
            "selected_score_margin": margin,
            "tune_sources": len(tune_rows),
        },
    )


def evaluate_fresh(
    environment_factory: Callable[[int], Any],
    session_factory: Callable[[int], Any],
    selection: TrainSelection,
    *,
    fresh_seeds: Sequence[int] = FRESH_SEEDS,
    minimum_rows: int = MIN_FRESH_SOURCES,
    minimum_informative: int = MIN_FRESH_INFORMATIVE,
    maximum_charged_seconds: float = MAX_CHARGED_SECONDS,
    clock: Callable[[], float] = time.monotonic,
    branch_evaluator: Callable[..., Any] | None = None,
) -> CurrentRelativeResult:
    started = float(clock())
    fresh = ranking._collect_partition(
        environment_factory,
        session_factory,
        name="development",
        seeds=tuple(fresh_seeds),
        max_source_states=MAX_FRESH_SOURCE_STATES,
        max_action_branches=MAX_FRESH_BRANCHES,
        max_censored_sources=MAX_FRESH_CENSORED,
        replay_source_count=FRESH_REPLAYS,
        minimum_complete_sources=minimum_rows,
        minimum_informative_sources=minimum_informative,
        maximum_charged_seconds=maximum_charged_seconds,
        clock=clock,
        branch_evaluator=branch_evaluator,
    )
    current = route.evaluate_current(fresh.rows)
    gated = evaluate_gated(
        selection.model, fresh.rows, score_margin=selection.selected_margin
    )
    raw = route.evaluate_model(selection.model, fresh.rows)
    changes = route._prediction_changes(current, gated)
    checks = {
        "corrects_at_least_one_current_decision": changes["corrected"] >= 1,
        "fresh_informative_support": sum(row.informative for row in fresh.rows) >= minimum_informative,
        "fresh_support": len(fresh.rows) >= minimum_rows,
        "maximum_regret_noninferior_to_current": gated["maximum_regret"] <= current["maximum_regret"] + 1e-12,
        "mean_regret_improves_current": gated["mean_regret"] + 1e-12 < current["mean_regret"],
        "overrides_at_least_one": gated["override_count"] >= 1,
        "worsened_not_more_than_corrected": changes["worsened"] <= changes["corrected"],
    }
    elapsed = float(clock()) - started
    if not math.isfinite(elapsed) or elapsed < 0 or elapsed > maximum_charged_seconds:
        raise CurrentRelativeShopBlocked("Current-relative fresh time differs")
    verdict = (
        "current_relative_shop_ranker_ready_for_live_shadow_proposal"
        if all(checks.values())
        else "current_relative_shop_ranker_not_ready_after_fresh_evaluation"
    )
    model = {
        "architecture": selection.model.architecture_metadata(),
        "model_seed": route.MODEL_SEED,
        "objective": "weighted-current-relative-logistic-v1",
        "schema_version": MODEL_SCHEMA_VERSION,
        "selected_epoch": selection.selected_epoch,
        "selected_score_margin": selection.selected_margin,
        "state": model_codec._encode_model_state(selection.model),
    }
    metrics = {
        "changes_vs_current": changes,
        "checks": checks,
        "fresh": {"current": current, "gated": gated, "raw": raw},
        "selection": selection.metrics,
        "verdict": verdict,
    }
    configuration = {
        "batch_size": BATCH_SIZE,
        "checkpoint_epochs": list(CHECKPOINT_EPOCHS),
        "fresh_seeds": list(fresh_seeds),
        "maximum_charged_seconds": maximum_charged_seconds,
        "objective": "weighted-current-relative-logistic-v1",
        "schema_version": SCHEMA_VERSION,
        "score_margins": list(SCORE_MARGINS),
        "train_dataset_sha256": EXPECTED_TRAIN_SHA256,
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
        "fresh": ranking._partition_summary(fresh),
        "operations": {
            "communication_mod": False,
            "evaluation": True,
            "gameplay": False,
            "model_fitting": True,
            "native_loading": True,
            "prior_development_access": False,
            "prior_fresh_access": False,
            "production_checkpoint_access": False,
            "protected_seed_access": False,
            "training": True,
        },
        "schema_version": SCHEMA_VERSION,
        "verdict": verdict,
    }
    return CurrentRelativeResult(
        configuration=configuration,
        fresh=fresh,
        model=model,
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
        raise CurrentRelativeShopBlocked("cannot resolve source commit") from exc
    return {"commit": commit, "files": files, "source_sha256": hashlib.sha256(_canonical_bytes(files)).hexdigest()}


def write_artifacts(
    output: Path,
    result: CurrentRelativeResult,
    identity: Mapping[str, Any],
    train_binding: Mapping[str, Any],
) -> None:
    output.mkdir(parents=False, exist_ok=False)
    artifacts = {
        "configuration.json": _canonical_bytes(result.configuration),
        "fresh_dataset.json": route.encode_partition(result.fresh),
        "metrics.json": _canonical_bytes(result.metrics),
        "model.json": _canonical_bytes(result.model),
        "report.json": _canonical_bytes({**result.report, "identity": copy.deepcopy(dict(identity)), "train_binding": copy.deepcopy(dict(train_binding))}),
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
            "# Current-Relative Shop Ranking",
            "",
            f"- Verdict: `{result.report['verdict']}`",
            f"- Selected epoch/margin: `{result.model['selected_epoch']}/{result.model['selected_score_margin']}`",
            f"- Fresh sources: `{result.report['fresh']['source_count']}`",
            f"- Current mean regret: `{metrics['fresh']['current']['mean_regret']:.6f}`",
            f"- Gated mean regret: `{metrics['fresh']['gated']['mean_regret']:.6f}`",
            f"- Overrides/corrections/worsened: `{metrics['fresh']['gated']['override_count']}/{metrics['changes_vs_current']['corrected']}/{metrics['changes_vs_current']['worsened']}`",
            "",
            "This fixed experiment grants no live intervention or promotion authority.",
            "",
        )
    )
    (output / "report.md").write_text(markdown, encoding="ascii", newline="\n")


def execute_cli(args: argparse.Namespace) -> dict[str, Any]:
    logging.getLogger().setLevel(logging.ERROR)
    repo_root = Path(args.repo_root).resolve()
    output = Path(args.output_dir).resolve()
    train_path = Path(args.train_dataset).resolve()
    if output.exists():
        raise CurrentRelativeShopBlocked("output directory already exists")
    train = load_train_dataset(train_path)
    selection = select_train_only(train)

    native_registration_path = Path(args.native_registration).resolve()
    bridge_input_path = Path(args.current_bridge_input).resolve()
    native_registration = event._read_json(native_registration_path)
    bridge_input = event._read_json(bridge_input_path)
    try:
        native_identity = native_registration["native"]["identity"]
        metadata_binding = bridge_input["identity"]["metadata"]
        current_policy = bridge_input["current_policy"]
    except KeyError as exc:
        raise CurrentRelativeShopBlocked("registered input fields differ") from exc
    metadata_path = Path(metadata_binding["path"]).resolve()
    if not metadata_path.is_file() or _sha256_file(metadata_path) != metadata_binding["sha256"]:
        raise CurrentRelativeShopBlocked("Current policy metadata bytes differ")
    if list(native_runner._forbidden_processes()):
        raise CurrentRelativeShopBlocked("game or CommunicationMod is active")
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

    result = evaluate_fresh(environment_factory, session_factory, selection)
    if list(native_runner._forbidden_processes()):
        raise CurrentRelativeShopBlocked("game or CommunicationMod started during execution")
    identity = {
        "current_bridge_input": {"path": bridge_input_path.as_posix(), "sha256": _sha256_file(bridge_input_path)},
        "metadata": copy.deepcopy(metadata_binding),
        "native_module": copy.deepcopy(native_identity["module"]),
        "native_registration": {"path": native_registration_path.as_posix(), "sha256": _sha256_file(native_registration_path)},
        "source": _source_identity(repo_root),
    }
    train_binding = {"path": train_path.as_posix(), "sha256": _sha256_file(train_path), "source_count": len(train.rows)}
    write_artifacts(output, result, identity, train_binding)
    return {
        "fresh_sources": len(result.fresh.rows),
        "output_dir": output.as_posix(),
        "selected_epoch": selection.selected_epoch,
        "selected_score_margin": selection.selected_margin,
        "verdict": result.report["verdict"],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run")
    run.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    run.add_argument("--native-registration", default=str(DEFAULT_NATIVE_REGISTRATION))
    run.add_argument("--current-bridge-input", default=str(DEFAULT_CURRENT_BRIDGE_INPUT))
    run.add_argument("--train-dataset", default=str(DEFAULT_TRAIN_DATASET))
    run.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command != "run":
        raise CurrentRelativeShopBlocked("unsupported command")
    print(json.dumps(execute_cli(args), ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
