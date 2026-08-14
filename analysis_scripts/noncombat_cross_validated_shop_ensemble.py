"""Train a cross-validated shop ensemble and evaluate one fresh cohort."""

from __future__ import annotations

import argparse
import copy
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import logging
import math
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any


_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

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
DEFAULT_OUTPUT_DIR = Path(
    "reports/noncombat_cross_validated_shop_ensemble_20260814_r1"
)
DEFAULT_PREFLIGHT_OUTPUT_DIR = Path(
    "reports/noncombat_cross_validated_shop_ensemble_preflight_20260814_r1"
)
FOLD_COUNT = 5
MODEL_SEEDS = (1701, 1709, 1721, 1733, 1741)
CHECKPOINT_EPOCHS = (8, 16, 32)
VOTE_QUORUMS = (3, 4, 5)
BATCH_SIZE = 16
FRESH_SEEDS = tuple(range(95492, 95556))
MAX_FRESH_SOURCE_STATES = 32
MAX_FRESH_BRANCHES = 512
MAX_FRESH_CENSORED = 32
FRESH_REPLAYS = 8
MIN_FRESH_SOURCES = 32
MIN_FRESH_INFORMATIVE = 16
MAX_CHARGED_SECONDS = 14_400.0
MIN_OOF_OVERRIDES = 5
MIN_OOF_CORRECTIONS = 3
SCHEMA_VERSION = "noncombat-cross-validated-shop-ensemble-v1"
MODEL_SCHEMA_VERSION = "noncombat-cross-validated-shop-ensemble-model-v1"
MANIFEST_SCHEMA_VERSION = "noncombat-cross-validated-shop-ensemble-manifest-v1"


@dataclass(frozen=True)
class DatasetBinding:
    cohort: str
    path: Path
    sha256: str
    partition_name: str
    source_count: int


DATASET_BINDINGS = (
    DatasetBinding(
        cohort="train64",
        path=Path(
            "reports/noncombat_state_conditioned_shop_ranking_20260814_r1/train_dataset.json"
        ),
        sha256="e346d26e2e29d297b316d9247ef9cf6619bb3fce274b0b88f34d69a9be5f736a",
        partition_name="train",
        source_count=64,
    ),
    DatasetBinding(
        cohort="development16",
        path=Path(
            "reports/noncombat_state_conditioned_shop_ranking_20260814_r1/development_dataset.json"
        ),
        sha256="c802f80ca72ea32f1caf42d1699faf92f607aac97af03b8b495f70ad9e07ba8e",
        partition_name="development",
        source_count=16,
    ),
    DatasetBinding(
        cohort="robust16",
        path=Path(
            "reports/noncombat_shop_robust_initialization_evaluation_20260814_r1/evaluation_dataset.json"
        ),
        sha256="74a76101fabb6a61424f34a411d602e96be46f8f459ccc464b641ebb0c5e89a2",
        partition_name="development",
        source_count=16,
    ),
    DatasetBinding(
        cohort="relative16",
        path=Path(
            "reports/noncombat_current_relative_shop_ranking_20260814_r1/fresh_dataset.json"
        ),
        sha256="76dde3cdcd058d6d9920f9795ddaf241915baa02f261776ab9b17bdbb49c4ae3",
        partition_name="development",
        source_count=16,
    ),
)
BOUND_SOURCE_PATHS = tuple(
    dict.fromkeys(
        (
            Path("analysis_scripts/noncombat_cross_validated_shop_ensemble.py"),
            *ranking.BOUND_SOURCE_PATHS,
        )
    )
)


class CrossValidatedShopBlocked(RuntimeError):
    """Raised when frozen cross-validated shop evidence cannot be produced."""


class CrossValidationNoGo(CrossValidatedShopBlocked):
    """Carries complete OOF metrics when no configuration is eligible."""

    def __init__(self, metrics: Mapping[str, Any]) -> None:
        super().__init__("no eligible OOF shop ensemble configuration")
        self.metrics = copy.deepcopy(dict(metrics))


@dataclass(frozen=True)
class HistoricalCorpus:
    rows: tuple[route.RouteRow, ...]
    cohort_by_source: dict[str, str]
    audit: dict[str, Any]


@dataclass(frozen=True)
class CrossValidationSelection:
    selected_epoch: int
    selected_vote_quorum: int
    metrics: dict[str, Any]


@dataclass(frozen=True)
class CrossValidatedShopResult:
    configuration: dict[str, Any]
    corpus_audit: dict[str, Any]
    fresh: route.RoutePartition
    model: dict[str, Any]
    oof_metrics: dict[str, Any]
    metrics: dict[str, Any]
    report: dict[str, Any]


def _canonical_bytes(value: Any) -> bytes:
    return event._canonical_bytes(value)


def _sha256_file(path: Path) -> str:
    return event._sha256_file(path)


def _fold_for_source(source_sha256: str) -> int:
    digest = hashlib.sha256(
        f"shop-cross-validation-v1:{source_sha256}".encode("ascii")
    ).digest()
    return int.from_bytes(digest[:8], "big") % FOLD_COUNT


def _policy_without_predictions(policy: Mapping[str, Any]) -> dict[str, Any]:
    return {key: copy.deepcopy(value) for key, value in policy.items() if key != "predictions"}


def _action_kind(row: route.RouteRow, action_id: str) -> str:
    for candidate in row.candidates:
        if candidate["action_id"] == action_id:
            return str(candidate["kind"])
    raise CrossValidatedShopBlocked("shop action id is absent from candidates")


def _cohort_summary(rows: Sequence[route.RouteRow]) -> dict[str, Any]:
    current = route.evaluate_current(rows)
    current_kinds = Counter(_action_kind(row, row.current_action_id) for row in rows)
    best_kinds = Counter(
        _action_kind(
            row,
            row.candidates[
                max(range(len(row.action_returns)), key=lambda index: row.action_returns[index])
            ]["action_id"],
        )
        for row in rows
    )
    spreads = [max(row.action_returns) - min(row.action_returns) for row in rows]
    return {
        "action_branches": sum(len(row.action_returns) for row in rows),
        "best_action_kinds": dict(sorted(best_kinds.items())),
        "current": _policy_without_predictions(current),
        "current_action_kinds": dict(sorted(current_kinds.items())),
        "informative_sources": sum(row.informative for row in rows),
        "mean_return_spread": math.fsum(spreads) / len(spreads),
        "source_count": len(rows),
    }


def load_historical_corpus(
    repo_root: Path,
    *,
    bindings: Sequence[DatasetBinding] = DATASET_BINDINGS,
) -> HistoricalCorpus:
    normalized_bindings = tuple(bindings)
    if not normalized_bindings or len({item.cohort for item in normalized_bindings}) != len(normalized_bindings):
        raise CrossValidatedShopBlocked("historical shop binding set differs")
    rows: list[route.RouteRow] = []
    cohort_by_source: dict[str, str] = {}
    binding_rows: list[dict[str, Any]] = []
    cohort_summaries: dict[str, Any] = {}
    feature_width: int | None = None
    for binding in normalized_bindings:
        path = binding.path if binding.path.is_absolute() else repo_root / binding.path
        try:
            payload = path.read_bytes()
        except OSError as exc:
            raise CrossValidatedShopBlocked("bound historical shop dataset is unreadable") from exc
        if hashlib.sha256(payload).hexdigest() != binding.sha256:
            raise CrossValidatedShopBlocked("bound historical shop dataset identity differs")
        try:
            partition = route.restore_partition(payload)
        except route.RouteExperimentBlocked as exc:
            raise CrossValidatedShopBlocked(str(exc)) from exc
        if partition.name != binding.partition_name or len(partition.rows) != binding.source_count:
            raise CrossValidatedShopBlocked("bound historical shop dataset support differs")
        for row in partition.rows:
            if not re.fullmatch(r"[0-9a-f]{64}", row.source_sha256):
                raise CrossValidatedShopBlocked("historical shop source identity differs")
            width = int(row.state_features.shape[0])
            if (
                row.candidate_features.shape[1] != width
                or not torch.isfinite(row.state_features).all().item()
                or not torch.isfinite(row.candidate_features).all().item()
            ):
                raise CrossValidatedShopBlocked("historical shop feature boundary differs")
            if feature_width is None:
                feature_width = width
            elif width != feature_width:
                raise CrossValidatedShopBlocked("historical shop feature widths differ")
            if row.source_sha256 in cohort_by_source:
                raise CrossValidatedShopBlocked("historical shop source hashes overlap")
            cohort_by_source[row.source_sha256] = binding.cohort
            rows.append(row)
        cohort_summaries[binding.cohort] = _cohort_summary(partition.rows)
        binding_rows.append(
            {
                "cohort": binding.cohort,
                "partition_name": binding.partition_name,
                "path": path.as_posix(),
                "sha256": binding.sha256,
                "source_count": binding.source_count,
            }
        )
    normalized_rows = tuple(sorted(rows, key=lambda row: row.source_sha256))
    expected_sources = sum(binding.source_count for binding in normalized_bindings)
    if len(normalized_rows) != expected_sources or feature_width is None:
        raise CrossValidatedShopBlocked("historical shop aggregate support differs")
    fold_support: dict[str, Any] = {}
    for fold in range(FOLD_COUNT):
        held_out = [row for row in normalized_rows if _fold_for_source(row.source_sha256) == fold]
        cohorts = Counter(cohort_by_source[row.source_sha256] for row in held_out)
        if not held_out or len(cohorts) < 2:
            raise CrossValidatedShopBlocked("historical shop fold support differs")
        fold_support[str(fold)] = {
            "cohorts": dict(sorted(cohorts.items())),
            "source_count": len(held_out),
        }
    audit = {
        "bindings": binding_rows,
        "cohorts": cohort_summaries,
        "feature_width": feature_width,
        "fold_support": fold_support,
        "overall": _cohort_summary(normalized_rows),
        "schema_version": SCHEMA_VERSION,
        "source_count": len(normalized_rows),
        "unique_source_count": len(cohort_by_source),
    }
    return HistoricalCorpus(
        rows=normalized_rows,
        cohort_by_source=cohort_by_source,
        audit=audit,
    )


def _new_model(input_dim: int, model_seed: int) -> StateConditionedCandidateRanker:
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(model_seed)
        model = StateConditionedCandidateRanker(input_dim, route.DEFAULT_HIDDEN_DIM)
    return model.to(device="cpu", dtype=torch.float32)


def _current_relative_loss(
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


def train_model(
    rows: Sequence[route.RouteRow],
    *,
    epochs: int,
    model_seed: int,
) -> tuple[StateConditionedCandidateRanker, dict[str, float | int]]:
    normalized = tuple(rows)
    if not normalized or epochs <= 0 or model_seed < 0:
        raise CrossValidatedShopBlocked("cross-validated shop training input differs")
    input_dim = int(normalized[0].state_features.shape[0])
    model = _new_model(input_dim, model_seed)
    optimizer = torch.optim.Adam(model.parameters(), lr=route.LEARNING_RATE)
    first_loss: float | None = None
    final_loss: float | None = None
    for _epoch in range(1, epochs + 1):
        model.train()
        batch_losses: list[float] = []
        for offset in range(0, len(normalized), BATCH_SIZE):
            loss = _current_relative_loss(model, normalized[offset : offset + BATCH_SIZE])
            if loss is None:
                continue
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            optimizer.step()
            batch_losses.append(float(loss.detach().item()))
        if not batch_losses:
            raise CrossValidatedShopBlocked("cross-validated shop train pairs are empty")
        final_loss = math.fsum(batch_losses) / len(batch_losses)
        if first_loss is None:
            first_loss = final_loss
    model.eval()
    return model, {
        "epochs": epochs,
        "final_mean_batch_loss": final_loss,
        "first_mean_batch_loss": first_loss,
        "model_seed": model_seed,
    }


def train_ensemble(
    rows: Sequence[route.RouteRow],
    *,
    epochs: int,
    model_seeds: Sequence[int] = MODEL_SEEDS,
) -> tuple[tuple[StateConditionedCandidateRanker, ...], list[dict[str, float | int]]]:
    seeds = tuple(model_seeds)
    if not seeds or len(set(seeds)) != len(seeds):
        raise CrossValidatedShopBlocked("shop ensemble model seeds differ")
    models: list[StateConditionedCandidateRanker] = []
    histories: list[dict[str, float | int]] = []
    for seed in seeds:
        model, history = train_model(rows, epochs=epochs, model_seed=seed)
        models.append(model)
        histories.append(history)
    return tuple(models), histories


def _ensemble_base_prediction(
    models: Sequence[StateConditionedCandidateRanker],
    row: route.RouteRow,
) -> dict[str, Any]:
    normalized = tuple(models)
    if not normalized:
        raise CrossValidatedShopBlocked("shop ensemble is empty")
    action_ids = [candidate["action_id"] for candidate in row.candidates]
    current_index = action_ids.index(row.current_action_id)
    votes = Counter()
    centered_scores: list[torch.Tensor] = []
    with torch.no_grad():
        for model in normalized:
            model.eval()
            scores = model(row.state_features, row.candidate_features)
            centered = scores - scores[current_index]
            centered_scores.append(centered)
            votes[int(torch.argmax(centered).item())] += 1
    mean_scores = torch.stack(centered_scores).mean(dim=0)
    learned_index = sorted(
        range(len(action_ids)),
        key=lambda index: (
            -votes[index],
            -float(mean_scores[index].item()),
            action_ids[index],
        ),
    )[0]
    returns = row.action_returns
    return {
        "current_action_id": row.current_action_id,
        "decision_index": row.decision_index,
        "learned_action_id": action_ids[learned_index],
        "learned_index": learned_index,
        "mean_centered_score": float(mean_scores[learned_index].item()),
        "raw_regret": max(returns) - returns[learned_index],
        "seed": row.seed,
        "source_sha256": row.source_sha256,
        "vote_count": votes[learned_index],
        "vote_fraction": votes[learned_index] / len(normalized),
        "votes": {action_ids[index]: votes[index] for index in range(len(action_ids)) if votes[index]},
    }


def _evaluate_bases(
    rows: Sequence[route.RouteRow],
    bases_by_source: Mapping[str, Mapping[str, Any]],
    *,
    vote_quorum: int,
) -> dict[str, Any]:
    if vote_quorum <= 0:
        raise CrossValidatedShopBlocked("shop ensemble vote quorum differs")
    regrets: list[float] = []
    predictions: list[dict[str, Any]] = []
    overrides = 0
    for row in rows:
        try:
            base = bases_by_source[row.source_sha256]
        except KeyError as exc:
            raise CrossValidatedShopBlocked("shop ensemble source coverage differs") from exc
        action_ids = [candidate["action_id"] for candidate in row.candidates]
        learned_action_id = str(base["learned_action_id"])
        selected_action_id = (
            learned_action_id
            if learned_action_id != row.current_action_id
            and int(base["vote_count"]) >= vote_quorum
            else row.current_action_id
        )
        selected_index = action_ids.index(selected_action_id)
        regret = max(row.action_returns) - row.action_returns[selected_index]
        overrides += int(selected_action_id != row.current_action_id)
        regrets.append(regret)
        predictions.append(
            {
                "action_id": selected_action_id,
                "current_action_id": row.current_action_id,
                "decision_index": row.decision_index,
                "learned_action_id": learned_action_id,
                "mean_centered_score": base["mean_centered_score"],
                "regret": regret,
                "seed": row.seed,
                "source_sha256": row.source_sha256,
                "vote_count": base["vote_count"],
                "vote_fraction": base["vote_fraction"],
            }
        )
    if len(predictions) != len(bases_by_source) or not regrets:
        raise CrossValidatedShopBlocked("shop ensemble prediction coverage differs")
    ordered = sorted(regrets)
    return {
        "maximum_regret": max(regrets),
        "mean_regret": math.fsum(regrets) / len(regrets),
        "override_count": overrides,
        "p95_regret": ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)],
        "predictions": predictions,
        "vote_quorum": vote_quorum,
    }


def evaluate_ensemble(
    models: Sequence[StateConditionedCandidateRanker],
    rows: Sequence[route.RouteRow],
    *,
    vote_quorum: int,
) -> dict[str, Any]:
    bases = {
        row.source_sha256: _ensemble_base_prediction(models, row) for row in rows
    }
    return _evaluate_bases(rows, bases, vote_quorum=vote_quorum)


def cross_validate(
    corpus: HistoricalCorpus,
    *,
    checkpoint_epochs: Sequence[int] = CHECKPOINT_EPOCHS,
    vote_quorums: Sequence[int] = VOTE_QUORUMS,
    trainer: Callable[..., tuple[tuple[StateConditionedCandidateRanker, ...], list[dict[str, float | int]]]] = train_ensemble,
) -> CrossValidationSelection:
    epochs_grid = tuple(checkpoint_epochs)
    quorum_grid = tuple(vote_quorums)
    if not epochs_grid or not quorum_grid or any(epoch <= 0 for epoch in epochs_grid):
        raise CrossValidatedShopBlocked("shop cross-validation grid differs")
    current = route.evaluate_current(corpus.rows)
    checkpoint_rows: list[dict[str, Any]] = []
    selected: tuple[tuple[Any, ...], int, int, dict[str, Any]] | None = None
    for epochs in epochs_grid:
        bases: dict[str, dict[str, Any]] = {}
        fold_rows: list[dict[str, Any]] = []
        for fold in range(FOLD_COUNT):
            fit_rows = tuple(
                row for row in corpus.rows if _fold_for_source(row.source_sha256) != fold
            )
            held_out = tuple(
                row for row in corpus.rows if _fold_for_source(row.source_sha256) == fold
            )
            models, histories = trainer(fit_rows, epochs=epochs, model_seeds=MODEL_SEEDS)
            for row in held_out:
                if row.source_sha256 in bases:
                    raise CrossValidatedShopBlocked("OOF source predicted more than once")
                bases[row.source_sha256] = _ensemble_base_prediction(models, row)
            fold_rows.append(
                {
                    "fit_sources": len(fit_rows),
                    "fold": fold,
                    "held_out_sources": len(held_out),
                    "model_histories": histories,
                }
            )
        if set(bases) != {row.source_sha256 for row in corpus.rows}:
            raise CrossValidatedShopBlocked("OOF source coverage differs")
        quorum_rows: list[dict[str, Any]] = []
        for quorum in quorum_grid:
            gated = _evaluate_bases(corpus.rows, bases, vote_quorum=quorum)
            changes = route._prediction_changes(current, gated)
            eligible = (
                gated["override_count"] >= MIN_OOF_OVERRIDES
                and changes["corrected"] >= MIN_OOF_CORRECTIONS
                and changes["worsened"] <= changes["corrected"]
                and gated["mean_regret"] + 1e-12 < current["mean_regret"]
                and gated["maximum_regret"] <= current["maximum_regret"] + 1e-12
            )
            summary = {
                "changes_vs_current": changes,
                "eligible": eligible,
                "maximum_regret": gated["maximum_regret"],
                "mean_regret": gated["mean_regret"],
                "override_count": gated["override_count"],
                "vote_quorum": quorum,
            }
            quorum_rows.append(summary)
            if eligible:
                key = (
                    gated["mean_regret"],
                    gated["maximum_regret"],
                    changes["worsened"],
                    -changes["corrected"],
                    gated["override_count"],
                    epochs,
                    -quorum,
                )
                if selected is None or key < selected[0]:
                    selected = (key, epochs, quorum, {"changes_vs_current": changes, "gated": gated})
        checkpoint_rows.append(
            {
                "epochs": epochs,
                "folds": fold_rows,
                "quorums": quorum_rows,
            }
        )
    if selected is None:
        raise CrossValidationNoGo(
            {
                "checkpoints": checkpoint_rows,
                "current": _policy_without_predictions(current),
                "fold_count": FOLD_COUNT,
                "selected": None,
                "selected_epoch": None,
                "selected_vote_quorum": None,
                "source_count": len(corpus.rows),
                "verdict": "cross_validated_shop_ensemble_not_eligible_after_oof",
            }
        )
    _, selected_epoch, selected_quorum, selected_metrics = selected
    return CrossValidationSelection(
        selected_epoch=selected_epoch,
        selected_vote_quorum=selected_quorum,
        metrics={
            "checkpoints": checkpoint_rows,
            "current": _policy_without_predictions(current),
            "fold_count": FOLD_COUNT,
            "selected": selected_metrics,
            "selected_epoch": selected_epoch,
            "selected_vote_quorum": selected_quorum,
            "source_count": len(corpus.rows),
        },
    )


def encode_ensemble(
    models: Sequence[StateConditionedCandidateRanker],
    selection: CrossValidationSelection,
) -> dict[str, Any]:
    normalized = tuple(models)
    if len(normalized) != len(MODEL_SEEDS):
        raise CrossValidatedShopBlocked("final shop ensemble size differs")
    architecture = normalized[0].architecture_metadata()
    if any(model.architecture_metadata() != architecture for model in normalized):
        raise CrossValidatedShopBlocked("final shop ensemble architectures differ")
    return {
        "architecture": architecture,
        "model_seeds": list(MODEL_SEEDS),
        "objective": "weighted-current-relative-logistic-v1",
        "schema_version": MODEL_SCHEMA_VERSION,
        "selected_epoch": selection.selected_epoch,
        "selected_vote_quorum": selection.selected_vote_quorum,
        "states": [model_codec._encode_model_state(model) for model in normalized],
    }


def restore_ensemble(payload: Mapping[str, Any]) -> tuple[StateConditionedCandidateRanker, ...]:
    if payload.get("schema_version") != MODEL_SCHEMA_VERSION or payload.get("model_seeds") != list(MODEL_SEEDS):
        raise CrossValidatedShopBlocked("serialized shop ensemble identity differs")
    try:
        architecture = payload["architecture"]
        states = payload["states"]
        input_dim = int(architecture["state_input_dim"])
        hidden_dim = int(architecture["hidden_dim"])
    except (KeyError, TypeError, ValueError) as exc:
        raise CrossValidatedShopBlocked("serialized shop ensemble fields differ") from exc
    if not isinstance(states, list) or len(states) != len(MODEL_SEEDS):
        raise CrossValidatedShopBlocked("serialized shop ensemble states differ")
    models: list[StateConditionedCandidateRanker] = []
    for seed, state in zip(MODEL_SEEDS, states, strict=True):
        model = _new_model(input_dim, seed)
        if model.architecture_metadata() != architecture or model.hidden_dim != hidden_dim:
            raise CrossValidatedShopBlocked("serialized shop ensemble architecture differs")
        try:
            model_codec._restore_model_state(model, state, "shop ensemble model")
        except Exception as exc:
            raise CrossValidatedShopBlocked("serialized shop ensemble state differs") from exc
        model.eval()
        models.append(model)
    return tuple(models)


def _configuration(corpus: HistoricalCorpus) -> dict[str, Any]:
    return {
        "batch_size": BATCH_SIZE,
        "checkpoint_epochs": list(CHECKPOINT_EPOCHS),
        "dataset_bindings": copy.deepcopy(corpus.audit["bindings"]),
        "fold_count": FOLD_COUNT,
        "fresh_seeds": list(FRESH_SEEDS),
        "maximum_charged_seconds": MAX_CHARGED_SECONDS,
        "model_seeds": list(MODEL_SEEDS),
        "objective": "weighted-current-relative-logistic-v1",
        "schema_version": SCHEMA_VERSION,
        "vote_quorums": list(VOTE_QUORUMS),
    }


def _fit_frozen_ensemble(
    corpus: HistoricalCorpus,
    selection: CrossValidationSelection,
) -> tuple[tuple[StateConditionedCandidateRanker, ...], dict[str, Any]]:
    models, histories = train_ensemble(corpus.rows, epochs=selection.selected_epoch)
    payload = encode_ensemble(models, selection)
    restored = restore_ensemble(payload)
    original = evaluate_ensemble(
        models, corpus.rows, vote_quorum=selection.selected_vote_quorum
    )
    round_trip = evaluate_ensemble(
        restored, corpus.rows, vote_quorum=selection.selected_vote_quorum
    )
    if _canonical_bytes(original) != _canonical_bytes(round_trip):
        raise CrossValidatedShopBlocked("final shop ensemble round trip differs")
    payload["full_corpus_histories"] = histories
    payload["historical_gated_metrics"] = _policy_without_predictions(original)
    return models, payload


def evaluate_fresh(
    environment_factory: Callable[[int], Any],
    session_factory: Callable[[int], Any],
    corpus: HistoricalCorpus,
    selection: CrossValidationSelection,
    models: Sequence[StateConditionedCandidateRanker],
    model_payload: Mapping[str, Any],
    *,
    fresh_seeds: Sequence[int] = FRESH_SEEDS,
    maximum_charged_seconds: float = MAX_CHARGED_SECONDS,
    clock: Callable[[], float] = time.monotonic,
    branch_evaluator: Callable[..., Any] | None = None,
) -> CrossValidatedShopResult:
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
        minimum_complete_sources=MIN_FRESH_SOURCES,
        minimum_informative_sources=MIN_FRESH_INFORMATIVE,
        maximum_charged_seconds=maximum_charged_seconds,
        clock=clock,
        branch_evaluator=branch_evaluator,
    )
    if len(fresh.rows) != MAX_FRESH_SOURCE_STATES:
        raise CrossValidatedShopBlocked("fresh shop source support differs")
    historical_hashes = {row.source_sha256 for row in corpus.rows}
    if historical_hashes.intersection(row.source_sha256 for row in fresh.rows):
        raise CrossValidatedShopBlocked("fresh shop sources overlap historical corpus")
    current = route.evaluate_current(fresh.rows)
    raw = evaluate_ensemble(models, fresh.rows, vote_quorum=1)
    gated = evaluate_ensemble(
        models, fresh.rows, vote_quorum=selection.selected_vote_quorum
    )
    changes = route._prediction_changes(current, gated)
    checks = {
        "corrects_at_least_one_current_decision": changes["corrected"] >= 1,
        "fresh_informative_support": sum(row.informative for row in fresh.rows) >= MIN_FRESH_INFORMATIVE,
        "fresh_support": len(fresh.rows) == MAX_FRESH_SOURCE_STATES,
        "maximum_regret_noninferior_to_current": gated["maximum_regret"] <= current["maximum_regret"] + 1e-12,
        "mean_regret_improves_current": gated["mean_regret"] + 1e-12 < current["mean_regret"],
        "overrides_at_least_one": gated["override_count"] >= 1,
        "worsened_not_more_than_corrected": changes["worsened"] <= changes["corrected"],
    }
    elapsed = float(clock()) - started
    if not math.isfinite(elapsed) or elapsed < 0 or elapsed > maximum_charged_seconds:
        raise CrossValidatedShopBlocked("cross-validated shop fresh time differs")
    verdict = (
        "cross_validated_shop_ensemble_ready_for_live_shadow_proposal"
        if all(checks.values())
        else "cross_validated_shop_ensemble_not_ready_after_fresh_evaluation"
    )
    metrics = {
        "changes_vs_current": changes,
        "checks": checks,
        "fresh": {"current": current, "gated": gated, "raw": raw},
        "verdict": verdict,
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
        "historical_source_count": len(corpus.rows),
        "operations": {
            "communication_mod": False,
            "evaluation": True,
            "fresh_source_access": True,
            "gameplay": False,
            "historical_corpus_access": True,
            "model_fitting": True,
            "model_loading": True,
            "native_loading": True,
            "production_checkpoint_access": False,
            "protected_seed_access": False,
            "training": True,
        },
        "schema_version": SCHEMA_VERSION,
        "verdict": verdict,
    }
    return CrossValidatedShopResult(
        configuration=_configuration(corpus),
        corpus_audit=copy.deepcopy(corpus.audit),
        fresh=fresh,
        model=copy.deepcopy(dict(model_payload)),
        oof_metrics=copy.deepcopy(selection.metrics),
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
        raise CrossValidatedShopBlocked("cannot resolve source commit") from exc
    return {
        "commit": commit,
        "files": files,
        "source_sha256": hashlib.sha256(_canonical_bytes(files)).hexdigest(),
    }


def write_artifacts(
    output: Path,
    result: CrossValidatedShopResult,
    identity: Mapping[str, Any],
) -> None:
    output.mkdir(parents=False, exist_ok=False)
    report_json = {
        **result.report,
        "identity": copy.deepcopy(dict(identity)),
    }
    metrics = result.metrics
    markdown = "\n".join(
        (
            "# Cross-Validated Shop Ensemble",
            "",
            f"- Verdict: `{result.report['verdict']}`",
            f"- Historical/fresh sources: `{result.report['historical_source_count']}/{result.report['fresh']['source_count']}`",
            f"- Selected epoch/quorum: `{result.model['selected_epoch']}/{result.model['selected_vote_quorum']}`",
            f"- Current mean regret: `{metrics['fresh']['current']['mean_regret']:.6f}`",
            f"- Gated mean regret: `{metrics['fresh']['gated']['mean_regret']:.6f}`",
            f"- Overrides/corrections/worsened: `{metrics['fresh']['gated']['override_count']}/{metrics['changes_vs_current']['corrected']}/{metrics['changes_vs_current']['worsened']}`",
            "",
            "This experiment grants no live intervention or promotion authority.",
            "",
        )
    ).encode("ascii")
    artifacts = {
        "configuration.json": _canonical_bytes(result.configuration),
        "corpus_audit.json": _canonical_bytes(result.corpus_audit),
        "fresh_dataset.json": route.encode_partition(result.fresh),
        "metrics.json": _canonical_bytes(result.metrics),
        "model.json": _canonical_bytes(result.model),
        "oof_metrics.json": _canonical_bytes(result.oof_metrics),
        "report.json": _canonical_bytes(report_json),
        "report.md": markdown,
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


def write_preflight_artifacts(
    output: Path,
    corpus: HistoricalCorpus,
    oof_metrics: Mapping[str, Any],
    identity: Mapping[str, Any],
    *,
    model_payload: Mapping[str, Any] | None,
) -> None:
    output.mkdir(parents=False, exist_ok=False)
    verdict = str(oof_metrics["verdict"])
    report = {
        "authority": {
            "formal_rl": False,
            "fresh_source_access": False,
            "gameplay": False,
            "policy_intervention": False,
            "promotion": False,
            "qualification": False,
        },
        "historical_source_count": len(corpus.rows),
        "identity": copy.deepcopy(dict(identity)),
        "operations": {
            "communication_mod": False,
            "evaluation": True,
            "fresh_source_access": False,
            "gameplay": False,
            "historical_corpus_access": True,
            "model_fitting": True,
            "native_loading": False,
            "production_checkpoint_access": False,
            "protected_seed_access": False,
            "training": True,
        },
        "schema_version": SCHEMA_VERSION,
        "verdict": verdict,
    }
    selected = oof_metrics.get("selected")
    if selected is None:
        summary = "No epoch/quorum configuration passed every OOF eligibility check."
    else:
        summary = (
            f"Selected epoch/quorum: {oof_metrics['selected_epoch']}/"
            f"{oof_metrics['selected_vote_quorum']}."
        )
    markdown = "\n".join(
        (
            "# Cross-Validated Shop Ensemble Preflight",
            "",
            f"- Verdict: `{verdict}`",
            f"- Historical sources: `{len(corpus.rows)}`",
            f"- Selected epoch/quorum: `{oof_metrics.get('selected_epoch')}/{oof_metrics.get('selected_vote_quorum')}`",
            "",
            summary,
            "Fresh simulator sources were not accessed.",
            "",
        )
    ).encode("ascii")
    artifacts = {
        "configuration.json": _canonical_bytes(_configuration(corpus)),
        "corpus_audit.json": _canonical_bytes(corpus.audit),
        "oof_metrics.json": _canonical_bytes(oof_metrics),
        "report.json": _canonical_bytes(report),
        "report.md": markdown,
    }
    if model_payload is not None:
        artifacts["model.json"] = _canonical_bytes(model_payload)
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


def _prepare(repo_root: Path) -> tuple[HistoricalCorpus, CrossValidationSelection, tuple[StateConditionedCandidateRanker, ...], dict[str, Any]]:
    corpus = load_historical_corpus(repo_root)
    selection = cross_validate(corpus)
    models, model_payload = _fit_frozen_ensemble(corpus, selection)
    return corpus, selection, models, model_payload


def execute_preflight(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).resolve()
    output = Path(args.output_dir).resolve()
    if output.exists():
        raise CrossValidatedShopBlocked("preflight output directory already exists")
    corpus = load_historical_corpus(repo_root)
    try:
        selection = cross_validate(corpus)
    except CrossValidationNoGo as exc:
        oof_metrics = exc.metrics
        model_payload = None
    else:
        _models, model_payload = _fit_frozen_ensemble(corpus, selection)
        oof_metrics = {
            **selection.metrics,
            "verdict": "cross_validated_shop_ensemble_preflight_passed",
        }
    identity = {"source": _source_identity(repo_root)}
    write_preflight_artifacts(
        output,
        corpus,
        oof_metrics,
        identity,
        model_payload=model_payload,
    )
    return {
        "historical_sources": len(corpus.rows),
        "model_state_sha256": (
            hashlib.sha256(_canonical_bytes(model_payload)).hexdigest()
            if model_payload is not None
            else None
        ),
        "output_dir": output.as_posix(),
        "selected_epoch": oof_metrics.get("selected_epoch"),
        "selected_vote_quorum": oof_metrics.get("selected_vote_quorum"),
        "verdict": oof_metrics["verdict"],
    }


def execute_run(args: argparse.Namespace) -> dict[str, Any]:
    logging.getLogger().setLevel(logging.ERROR)
    repo_root = Path(args.repo_root).resolve()
    output = Path(args.output_dir).resolve()
    if output.exists():
        raise CrossValidatedShopBlocked("output directory already exists")
    corpus, selection, models, model_payload = _prepare(repo_root)

    native_registration_path = Path(args.native_registration).resolve()
    bridge_input_path = Path(args.current_bridge_input).resolve()
    native_registration = event._read_json(native_registration_path)
    bridge_input = event._read_json(bridge_input_path)
    try:
        native_identity = native_registration["native"]["identity"]
        metadata_binding = bridge_input["identity"]["metadata"]
        current_policy = bridge_input["current_policy"]
    except KeyError as exc:
        raise CrossValidatedShopBlocked("registered input fields differ") from exc
    metadata_path = Path(metadata_binding["path"]).resolve()
    if not metadata_path.is_file() or _sha256_file(metadata_path) != metadata_binding["sha256"]:
        raise CrossValidatedShopBlocked("Current policy metadata bytes differ")
    if list(native_runner._forbidden_processes()):
        raise CrossValidatedShopBlocked("game or CommunicationMod is active")
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

    result = evaluate_fresh(
        environment_factory,
        session_factory,
        corpus,
        selection,
        models,
        model_payload,
    )
    if list(native_runner._forbidden_processes()):
        raise CrossValidatedShopBlocked("game or CommunicationMod started during execution")
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
    write_artifacts(output, result, identity)
    return {
        "fresh_sources": len(result.fresh.rows),
        "historical_sources": len(corpus.rows),
        "output_dir": output.as_posix(),
        "selected_epoch": selection.selected_epoch,
        "selected_vote_quorum": selection.selected_vote_quorum,
        "verdict": result.report["verdict"],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    preflight = subparsers.add_parser("preflight")
    preflight.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    preflight.add_argument("--output-dir", default=str(DEFAULT_PREFLIGHT_OUTPUT_DIR))
    run = subparsers.add_parser("run")
    run.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    run.add_argument("--native-registration", default=str(DEFAULT_NATIVE_REGISTRATION))
    run.add_argument("--current-bridge-input", default=str(DEFAULT_CURRENT_BRIDGE_INPUT))
    run.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "preflight":
        result = execute_preflight(args)
    elif args.command == "run":
        result = execute_run(args)
    else:
        raise CrossValidatedShopBlocked("unsupported command")
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
