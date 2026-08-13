"""Train a family-preserving conditional card scorer on the merged corpus."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import types
from collections.abc import Mapping, Sequence
from typing import Any

import torch
import torch.nn.functional as F


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


from analysis_scripts import noncombat_card_acceptance_empirical_successor_runtime as runtime
from analysis_scripts import noncombat_card_acceptance_objective as objective
from analysis_scripts import noncombat_card_counterfactual_ranking_training as ranking
from analysis_scripts import noncombat_card_counterfactual_uplift_residual_crossfit as uplift
from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot as pilot
from analysis_scripts import noncombat_large_corpus_card_uplift_residual as residual
from analysis_scripts import noncombat_large_corpus_state_conditioned_card_ranking as predecessor


SCHEMA_VERSION = "noncombat-family-preserving-conditional-card-ranking-v1"
CONFIGURATION_SCHEMA_VERSION = f"{SCHEMA_VERSION}-configuration"
FOLDS_SCHEMA_VERSION = f"{SCHEMA_VERSION}-folds"
METRICS_SCHEMA_VERSION = f"{SCHEMA_VERSION}-metrics"
PREDICTIONS_SCHEMA_VERSION = f"{SCHEMA_VERSION}-predictions"
REPORT_SCHEMA_VERSION = f"{SCHEMA_VERSION}-report"
MANIFEST_SCHEMA_VERSION = f"{SCHEMA_VERSION}-manifest"

FOLD_COUNT = 5
BATCH_SIZE = 64
EPOCH_CHECKPOINTS = (1, 2, 4, 8, 16, 32)
MIN_CROSSFIT_CORRECTED_ACTIONS = 4
MIN_DEVELOPMENT_CORRECTED_ACTIONS = 2
MIN_RARE_DEVELOPMENT_CORRECTED_ACTIONS = 1
EXPECTED_TRAIN_ROWS = 773
EXPECTED_INFORMATIVE_TAKE_ROWS = 439
EXPECTED_INFORMATIVE_TAKE_SEEDS = 306
EXPECTED_UNEQUAL_TAKE_PAIRS = 960
EXPECTED_DEVELOPMENT_ROWS = 190
EXPECTED_RARE_DEVELOPMENT_ROWS = 64
TRAINABLE_PARAMETER_COUNT = 64

DEFAULT_CORPUS_ROOT = residual.DEFAULT_CORPUS_ROOT
DEFAULT_RARE_CORPUS_ROOT = residual.DEFAULT_RARE_CORPUS_ROOT
DEFAULT_PREDECESSOR_ROOT = Path(
    "reports/noncombat_large_corpus_state_conditioned_card_ranking_20260814_r1"
)
DEFAULT_OUTPUT_DIR = Path(
    "reports/noncombat_family_preserving_conditional_card_ranking_20260814_r1"
)
SOURCE_PATHS = tuple(
    sorted(
        {
            *predecessor.SOURCE_PATHS,
            "analysis_scripts/noncombat_family_preserving_conditional_card_ranking.py",
        }
    )
)
AUTHORITY = {
    name: False
    for name in (
        "audit_access",
        "causal_claim",
        "communication_mod",
        "formal_rl",
        "fresh_evaluation",
        "gameplay",
        "native_loading",
        "ope",
        "policy_quality",
        "production_model_loading",
        "promotion",
        "qualification",
    )
}
OPERATIONS = {
    "audit_access": False,
    "communication_mod": False,
    "development_evaluation": True,
    "environment_construction": False,
    "gameplay": False,
    "model_fitting": True,
    "model_loading": True,
    "native_loading": False,
    "ope": False,
    "production_model_loading": False,
    "seed_access": False,
    "training": True,
}


class ConditionalCardRankingBlocked(RuntimeError):
    """Raised when the family-preserving ranking contract cannot proceed."""


_canonical_bytes = predecessor._canonical_bytes
_binding = predecessor._binding
encode_model = predecessor.encode_model
restore_model = predecessor.restore_model


def _source_bindings(root: Path, source_commit: str) -> dict[str, Any]:
    try:
        if (
            subprocess.run(
                ["git", "cat-file", "-t", source_commit],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            != "commit"
        ):
            raise ConditionalCardRankingBlocked("source commit is unavailable")
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", source_commit, "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ConditionalCardRankingBlocked("source commit is not an ancestor") from exc
    bindings: dict[str, Any] = {}
    for relative in SOURCE_PATHS:
        actual = _binding(root / relative)
        try:
            committed = subprocess.run(
                ["git", "show", f"{source_commit}:{relative}"],
                cwd=root,
                check=True,
                capture_output=True,
            ).stdout
        except (OSError, subprocess.CalledProcessError) as exc:
            raise ConditionalCardRankingBlocked(
                f"source path is unavailable at commit: {relative}"
            ) from exc
        if hashlib.sha256(committed).hexdigest() != actual["sha256"]:
            raise ConditionalCardRankingBlocked(f"source bytes differ: {relative}")
        bindings[relative] = actual
    return bindings


def _row_key(row: ranking.CounterfactualRankingRow) -> tuple[int, int, str]:
    return row.seed, row.decision_index, row.source_sha256


def unequal_take_pair_count(row: ranking.CounterfactualRankingRow) -> int:
    return sum(
        row.action_returns[left] != row.action_returns[right]
        for left in range(3)
        for right in range(left + 1, 3)
    )


def informative_take_rows(
    rows: Sequence[ranking.CounterfactualRankingRow],
) -> tuple[ranking.CounterfactualRankingRow, ...]:
    normalized = uplift.validate_rows(rows)
    return tuple(
        sorted(
            (row for row in normalized if unequal_take_pair_count(row) > 0),
            key=_row_key,
        )
    )


def deterministic_batches(
    rows: Sequence[ranking.CounterfactualRankingRow],
    *,
    batch_size: int = BATCH_SIZE,
) -> tuple[tuple[ranking.CounterfactualRankingRow, ...], ...]:
    if isinstance(batch_size, bool) or not isinstance(batch_size, int) or batch_size <= 0:
        raise ConditionalCardRankingBlocked("batch size differs")
    ordered = informative_take_rows(rows)
    if not ordered:
        raise ConditionalCardRankingBlocked("take ranking rows are uninformative")
    return tuple(
        tuple(ordered[index : index + batch_size])
        for index in range(0, len(ordered), batch_size)
    )


def conditional_scorer_optimizer(
    bootstrap: runtime.PairedBootstrap,
) -> torch.optim.Adam:
    policy = bootstrap.candidate.card_policy
    for parameter in policy.parameters():
        parameter.requires_grad_(False)
        parameter.grad = None
    target = policy.conditional_ranker.scorer.weight
    target.requires_grad_(True)
    if target.numel() != TRAINABLE_PARAMETER_COUNT:
        raise ConditionalCardRankingBlocked("conditional scorer size differs")
    optimizer = torch.optim.Adam([target], **runtime._REGISTERED_ADAM_OPTIONS)
    try:
        registered = runtime._validated_registered_adam(optimizer)
    except runtime.SuccessorRuntimeError as exc:
        raise ConditionalCardRankingBlocked(str(exc)) from exc
    if registered != (target,) or optimizer.state:
        raise ConditionalCardRankingBlocked("conditional optimizer ownership differs")
    return optimizer


def _frozen_model_bytes(bootstrap: runtime.PairedBootstrap) -> bytes:
    try:
        value = json.loads(runtime.encode_paired_bootstrap(bootstrap))
        del value["models"]["candidate"]["conditional_ranker"]["scorer.weight"]
    except (KeyError, runtime.SuccessorRuntimeError) as exc:
        raise ConditionalCardRankingBlocked("frozen model encoding failed") from exc
    return _canonical_bytes(value)


def take_pairwise_loss(
    bootstrap: runtime.PairedBootstrap,
    rows: Sequence[ranking.CounterfactualRankingRow],
) -> torch.Tensor:
    weighted_losses: list[torch.Tensor] = []
    weights: list[float] = []
    for row in rows:
        try:
            output = runtime.forward_card_policy(
                bootstrap,
                arm="candidate",
                state_features=row.state_features,
                candidate_features=row.candidate_features,
                candidates=row.candidates,
            )
        except (RuntimeError, ValueError, runtime.SuccessorRuntimeError) as exc:
            raise ConditionalCardRankingBlocked("conditional ranking forward failed") from exc
        logits = output.conditional_logits
        for left in range(3):
            for right in range(left + 1, 3):
                difference = row.action_returns[left] - row.action_returns[right]
                if difference == 0:
                    continue
                better, worse = (left, right) if difference > 0 else (right, left)
                weight = abs(difference)
                weighted_losses.append(weight * F.softplus(-(logits[better] - logits[worse])))
                weights.append(weight)
    if not weighted_losses or math.fsum(weights) <= 0:
        raise ConditionalCardRankingBlocked("take ranking rows contain no unequal returns")
    loss = torch.stack(weighted_losses).sum() / math.fsum(weights)
    if loss.ndim != 0 or not bool(torch.isfinite(loss).item()):
        raise ConditionalCardRankingBlocked("take ranking loss is invalid")
    return loss


def _state_is_finite(value: Any) -> bool:
    if isinstance(value, torch.Tensor):
        return bool(torch.isfinite(value).all().item())
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, Mapping):
        return all(_state_is_finite(item) for item in value.values())
    if isinstance(value, (tuple, list)):
        return all(_state_is_finite(item) for item in value)
    return isinstance(value, (bool, int, str)) or value is None


def train_one_epoch(
    bootstrap: runtime.PairedBootstrap,
    optimizer: torch.optim.Optimizer,
    rows: Sequence[ranking.CounterfactualRankingRow],
    *,
    batch_size: int = BATCH_SIZE,
) -> dict[str, Any]:
    target = bootstrap.candidate.card_policy.conditional_ranker.scorer.weight
    try:
        parameters = runtime._validated_registered_adam(optimizer)
    except runtime.SuccessorRuntimeError as exc:
        raise ConditionalCardRankingBlocked(str(exc)) from exc
    if parameters != (target,):
        raise ConditionalCardRankingBlocked("conditional optimizer ownership differs")
    frozen_before = _frozen_model_bytes(bootstrap)
    target_before = target.detach().clone()
    losses: list[float] = []
    for batch in deterministic_batches(rows, batch_size=batch_size):
        optimizer.zero_grad(set_to_none=True)
        loss = take_pairwise_loss(bootstrap, batch)
        loss_value = float(loss.detach().item())
        loss.backward()
        if target.grad is None or not bool(torch.isfinite(target.grad).all().item()):
            raise ConditionalCardRankingBlocked("conditional scorer gradient is invalid")
        optimizer.step()
        if not bool(torch.isfinite(target).all().item()) or not _state_is_finite(
            optimizer.state
        ):
            raise ConditionalCardRankingBlocked("conditional optimizer state is nonfinite")
        losses.append(loss_value)
    if _frozen_model_bytes(bootstrap) != frozen_before:
        raise ConditionalCardRankingBlocked("frozen model state changed")
    if torch.equal(target.detach(), target_before):
        raise ConditionalCardRankingBlocked("conditional scorer did not change")
    return {
        "batch_count": len(losses),
        "maximum_batch_loss": max(losses),
        "mean_batch_loss": math.fsum(losses) / len(losses),
        "minimum_batch_loss": min(losses),
    }


def policy_predictions(
    bootstrap: runtime.PairedBootstrap,
    rows: Sequence[ranking.CounterfactualRankingRow],
) -> list[dict[str, Any]]:
    normalized = uplift.validate_rows(rows)
    predictions: list[dict[str, Any]] = []
    with torch.no_grad():
        for row in normalized:
            try:
                output = runtime.forward_card_policy(
                    bootstrap,
                    arm="candidate",
                    state_features=row.state_features,
                    candidate_features=row.candidate_features,
                    candidates=row.candidates,
                )
                terms = objective.build_card_acceptance_policy_terms(
                    output.family_logits,
                    output.conditional_logits,
                    row.candidates,
                    row.candidates[0]["action_id"],
                    category="card_reward",
                )
                selected_action_id = runtime.select_two_stage_action(terms, greedy=True)
            except (RuntimeError, TypeError, ValueError, runtime.SuccessorRuntimeError) as exc:
                raise ConditionalCardRankingBlocked("two-stage evaluation failed") from exc
            selected_index = next(
                index
                for index, candidate in enumerate(row.candidates)
                if candidate["action_id"] == selected_action_id
            )
            best_return = max(row.action_returns)
            best_indices = tuple(
                index
                for index, value in enumerate(row.action_returns)
                if value == best_return
            )
            family_position = {
                family: index for index, family in enumerate(terms.family_order)
            }
            pair_weight = pair_correct = 0.0
            take_pair_weight = take_pair_correct = 0.0
            for left in range(4):
                for right in range(left + 1, 4):
                    difference = row.action_returns[left] - row.action_returns[right]
                    if difference == 0:
                        continue
                    better, worse = (left, right) if difference > 0 else (right, left)
                    better_family = terms.candidate_families[better]
                    worse_family = terms.candidate_families[worse]
                    if better_family == worse_family:
                        delta = float(
                            terms.conditional_log_probabilities[better]
                            - terms.conditional_log_probabilities[worse]
                        )
                    else:
                        delta = float(
                            terms.family_log_probabilities[
                                family_position[better_family]
                            ]
                            - terms.family_log_probabilities[family_position[worse_family]]
                        )
                    weight = abs(difference)
                    credit = 1.0 if delta > 0 else 0.5 if delta == 0 else 0.0
                    pair_weight += weight
                    pair_correct += weight * credit
                    if left < 3 and right < 3:
                        take_pair_weight += weight
                        take_pair_correct += weight * credit
            predictions.append(
                {
                    "actual_best_action_ids": sorted(
                        row.candidates[index]["action_id"] for index in best_indices
                    ),
                    "decision_index": row.decision_index,
                    "pair_correct": pair_correct,
                    "pair_weight": pair_weight,
                    "regret": best_return - row.action_returns[selected_index],
                    "seed": row.seed,
                    "selected_action_id": selected_action_id,
                    "selected_family": row.candidates[selected_index]["kind"],
                    "source_sha256": row.source_sha256,
                    "take_pair_correct": take_pair_correct,
                    "take_pair_weight": take_pair_weight,
                    "unique_best": len(best_indices) == 1,
                }
            )
    return predictions


def metrics_from_predictions(
    predictions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    rows = tuple(predictions)
    if not rows or len({row["source_sha256"] for row in rows}) != len(rows):
        raise ConditionalCardRankingBlocked("prediction identities differ")
    pair_weight = math.fsum(float(row["pair_weight"]) for row in rows)
    take_pair_weight = math.fsum(float(row["take_pair_weight"]) for row in rows)
    unique = tuple(row for row in rows if row["unique_best"])
    if pair_weight <= 0 or take_pair_weight <= 0 or not unique:
        raise ConditionalCardRankingBlocked("prediction metric support differs")
    regrets = tuple(float(row["regret"]) for row in rows)
    return {
        "maximum_top_action_regret": max(regrets),
        "mean_top_action_regret": math.fsum(regrets) / len(regrets),
        "predictions": [copy.deepcopy(dict(row)) for row in rows],
        "source_states": len(rows),
        "take_weighted_pairwise_accuracy": math.fsum(
            float(row["take_pair_correct"]) for row in rows
        )
        / take_pair_weight,
        "take_weighted_pairwise_margin": take_pair_weight,
        "unique_best_accuracy": sum(
            row["selected_action_id"] in row["actual_best_action_ids"] for row in unique
        )
        / len(unique),
        "unique_best_states": len(unique),
        "weighted_pairwise_accuracy": math.fsum(
            float(row["pair_correct"]) for row in rows
        )
        / pair_weight,
        "weighted_pairwise_margin": pair_weight,
    }


def evaluate_policy(
    bootstrap: runtime.PairedBootstrap,
    rows: Sequence[ranking.CounterfactualRankingRow],
) -> dict[str, Any]:
    return metrics_from_predictions(policy_predictions(bootstrap, rows))


def compare_predictions(
    entry: Mapping[str, Any], candidate: Mapping[str, Any]
) -> dict[str, int]:
    before = {row["source_sha256"]: row for row in entry["predictions"]}
    after = {row["source_sha256"]: row for row in candidate["predictions"]}
    if set(before) != set(after):
        raise ConditionalCardRankingBlocked("comparison identities differ")
    flips = corrected = worsened = family_flips = 0
    for source, entry_row in before.items():
        candidate_row = after[source]
        changed = entry_row["selected_action_id"] != candidate_row["selected_action_id"]
        flips += int(changed)
        family_flips += int(entry_row["selected_family"] != candidate_row["selected_family"])
        corrected += int(
            changed
            and entry_row["selected_action_id"] not in entry_row["actual_best_action_ids"]
            and candidate_row["selected_action_id"]
            in candidate_row["actual_best_action_ids"]
        )
        worsened += int(candidate_row["regret"] > entry_row["regret"])
    return {
        "action_flips": flips,
        "corrected_actions": corrected,
        "family_flips": family_flips,
        "worsened_actions": worsened,
    }


def _metrics_without_predictions(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: copy.deepcopy(item) for key, item in value.items() if key != "predictions"}


def _comparison_checks(
    entry: Mapping[str, Any],
    candidate: Mapping[str, Any],
    comparison: Mapping[str, int],
    *,
    minimum_corrected_actions: int,
    strict_mean: bool = True,
    strict_take_pairwise: bool = True,
) -> dict[str, bool]:
    return {
        "corrected_actions": comparison["corrected_actions"]
        >= minimum_corrected_actions,
        "family_choices_preserved": comparison["family_flips"] == 0,
        "maximum_regret_nonincreasing": candidate["maximum_top_action_regret"]
        <= entry["maximum_top_action_regret"],
        "mean_regret_improved": candidate["mean_top_action_regret"]
        < entry["mean_top_action_regret"]
        if strict_mean
        else candidate["mean_top_action_regret"] <= entry["mean_top_action_regret"],
        "take_pairwise_improved": candidate["take_weighted_pairwise_accuracy"]
        > entry["take_weighted_pairwise_accuracy"]
        if strict_take_pairwise
        else candidate["take_weighted_pairwise_accuracy"]
        >= entry["take_weighted_pairwise_accuracy"],
        "unique_best_accuracy_nondecreasing": candidate["unique_best_accuracy"]
        >= entry["unique_best_accuracy"],
        "worsened_actions_bounded": comparison["worsened_actions"]
        <= comparison["corrected_actions"],
    }


def train_checkpoints(
    entry_bytes: bytes,
    *,
    fit_rows: Sequence[ranking.CounterfactualRankingRow],
    score_partition: Sequence[ranking.CounterfactualRankingRow],
    epoch_checkpoints: Sequence[int] = EPOCH_CHECKPOINTS,
    batch_size: int = BATCH_SIZE,
) -> tuple[dict[int, list[dict[str, Any]]], list[dict[str, Any]], runtime.PairedBootstrap]:
    checkpoints = tuple(epoch_checkpoints)
    if (
        not checkpoints
        or tuple(sorted(set(checkpoints))) != checkpoints
        or any(isinstance(epoch, bool) or not isinstance(epoch, int) or epoch <= 0 for epoch in checkpoints)
    ):
        raise ConditionalCardRankingBlocked("epoch checkpoints differ")
    model = restore_model(entry_bytes)
    frozen_before = _frozen_model_bytes(model)
    scorer_before = model.candidate.card_policy.conditional_ranker.scorer.weight.detach().clone()
    optimizer = conditional_scorer_optimizer(model)
    losses: list[dict[str, Any]] = []
    predictions: dict[int, list[dict[str, Any]]] = {}
    for epoch in range(1, checkpoints[-1] + 1):
        diagnostic = train_one_epoch(model, optimizer, fit_rows, batch_size=batch_size)
        diagnostic["epoch"] = epoch
        losses.append(diagnostic)
        if epoch in checkpoints:
            predictions[epoch] = policy_predictions(model, score_partition)
    if _frozen_model_bytes(model) != frozen_before:
        raise ConditionalCardRankingBlocked("frozen final model differs")
    if torch.equal(
        model.candidate.card_policy.conditional_ranker.scorer.weight.detach(),
        scorer_before,
    ):
        raise ConditionalCardRankingBlocked("conditional final scorer did not change")
    return predictions, losses, model


def _selection_key(candidate: Mapping[str, Any]) -> tuple[float, float, float, float, int]:
    metrics = candidate["metrics"]
    return (
        float(metrics["mean_top_action_regret"]),
        float(metrics["maximum_top_action_regret"]),
        -float(metrics["take_weighted_pairwise_accuracy"]),
        -float(metrics["unique_best_accuracy"]),
        int(candidate["epochs"]),
    )


def crossfit_select_epochs(
    entry_bytes: bytes,
    rows: Sequence[ranking.CounterfactualRankingRow],
) -> dict[str, Any]:
    normalized = uplift.validate_rows(rows)
    folds = uplift.build_seed_folds(sorted({row.seed for row in normalized}), FOLD_COUNT)
    entry = restore_model(entry_bytes)
    entry_metrics = evaluate_policy(entry, normalized)
    candidate_predictions = {epoch: [] for epoch in EPOCH_CHECKPOINTS}
    fold_losses: list[dict[str, Any]] = []
    for fold_index, fold in enumerate(folds):
        heldout = set(fold)
        fit_rows = tuple(row for row in normalized if row.seed not in heldout)
        heldout_rows = tuple(row for row in normalized if row.seed in heldout)
        predictions, losses, _ = train_checkpoints(
            entry_bytes,
            fit_rows=fit_rows,
            score_partition=heldout_rows,
        )
        fold_losses.append(
            {"fold_index": fold_index, "heldout_seeds": list(fold), "losses": losses}
        )
        for epoch in EPOCH_CHECKPOINTS:
            candidate_predictions[epoch].extend(predictions[epoch])
    candidates: list[dict[str, Any]] = []
    candidate_metrics: dict[int, dict[str, Any]] = {}
    for epoch in EPOCH_CHECKPOINTS:
        metrics = metrics_from_predictions(candidate_predictions[epoch])
        candidate_metrics[epoch] = metrics
        comparison = compare_predictions(entry_metrics, metrics)
        checks = _comparison_checks(
            entry_metrics,
            metrics,
            comparison,
            minimum_corrected_actions=MIN_CROSSFIT_CORRECTED_ACTIONS,
        )
        candidates.append(
            {
                "checks": checks,
                "comparison": comparison,
                "epochs": epoch,
                "metrics": _metrics_without_predictions(metrics),
                "selection_key": list(
                    _selection_key({"epochs": epoch, "metrics": metrics})
                ),
            }
        )
    passing = [candidate for candidate in candidates if all(candidate["checks"].values())]
    selected = min(passing, key=_selection_key) if passing else None
    return {
        "candidate_metrics": candidate_metrics,
        "candidates": candidates,
        "entry_metrics": entry_metrics,
        "fold_losses": fold_losses,
        "folds": folds,
        "selected_epochs": None if selected is None else selected["epochs"],
    }


def _validate_train_support(
    rows: Sequence[ranking.CounterfactualRankingRow],
) -> tuple[ranking.CounterfactualRankingRow, ...]:
    normalized = uplift.validate_rows(rows)
    informative = informative_take_rows(normalized)
    if (
        len(normalized) != EXPECTED_TRAIN_ROWS
        or len(informative) != EXPECTED_INFORMATIVE_TAKE_ROWS
        or len({row.seed for row in informative}) != EXPECTED_INFORMATIVE_TAKE_SEEDS
        or sum(unequal_take_pair_count(row) for row in normalized)
        != EXPECTED_UNEQUAL_TAKE_PAIRS
    ):
        raise ConditionalCardRankingBlocked("merged take support differs")
    return normalized


def _write_artifact(staging: Path, output: Path, name: str, payload: bytes) -> dict[str, Any]:
    return predecessor._write_artifact(staging, output, name, payload)


def _configuration(*, inputs: Mapping[str, Any], source: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "authority": copy.deepcopy(AUTHORITY),
        "batch_size": BATCH_SIZE,
        "epoch_checkpoints": list(EPOCH_CHECKPOINTS),
        "fold_count": FOLD_COUNT,
        "inputs": copy.deepcopy(dict(inputs)),
        "metric_policy": "two-stage-family-then-conditional-greedy-v1",
        "operations": copy.deepcopy(OPERATIONS),
        "optimizer": copy.deepcopy(runtime._REGISTERED_ADAM_OPTIONS),
        "schema_version": CONFIGURATION_SCHEMA_VERSION,
        "trainable_parameter_count": TRAINABLE_PARAMETER_COUNT,
        "trainable_parameters": ["conditional_ranker.scorer.weight"],
    }


def _render_report(report: Mapping[str, Any]) -> str:
    return "\n".join(
        [
            "# Family-Preserving Conditional Card Ranking",
            "",
            f"- Verdict: `{report['verdict']}`",
            f"- Selected epochs: `{report['selected_epochs']}`",
            f"- Development accessed: `{report['development_accessed']}`",
            f"- Audit accessed: `{report['audit_accessed']}`",
            "- Metric policy: `two-stage-family-then-conditional-greedy-v1`",
            "",
            "## Boundary",
            "",
            "- Only the 64-value conditional scorer weight was trainable.",
            "- Entry family choices were required to remain exact.",
            "- Reserved audit seeds, native code, game, and CommunicationMod were not accessed.",
            "",
        ]
    )


def execute(
    *,
    repo_root: Path | str,
    source_commit: str,
    corpus_root: Path | str = DEFAULT_CORPUS_ROOT,
    rare_corpus_root: Path | str = DEFAULT_RARE_CORPUS_ROOT,
    predecessor_root: Path | str = DEFAULT_PREDECESSOR_ROOT,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    corpus_path = Path(corpus_root).resolve()
    rare_path = Path(rare_corpus_root).resolve()
    predecessor_path = Path(predecessor_root).resolve()
    output = Path(output_dir).resolve()
    staging = output.with_name(f".{output.name}.{source_commit}.staging")
    if output.exists() or staging.exists():
        raise ConditionalCardRankingBlocked("output boundary differs")
    source = {
        "bindings": _source_bindings(root, source_commit),
        "commit": source_commit,
        "repo_root": root.as_posix(),
    }
    existing_train, entry, inputs = residual._load_train_inputs(corpus_path)
    rare_train, rare_inputs = residual._load_rare_train_inputs(rare_path)
    inputs.update(rare_inputs)
    predecessor_report = residual._read_canonical(predecessor_path / "report.json")
    if (
        predecessor_report.get("verdict")
        != "state_conditioned_card_ranking_not_ready_after_development"
        or predecessor_report.get("audit_accessed") is not False
    ):
        raise ConditionalCardRankingBlocked("predecessor no-go differs")
    inputs["predecessor_manifest"] = _binding(
        predecessor_path / "artifact_manifest.json"
    )
    inputs["predecessor_report"] = _binding(predecessor_path / "report.json")
    train_rows = _validate_train_support(
        residual._merge_disjoint_rows(existing_train, rare_train)
    )
    entry_bytes = encode_model(entry)
    frozen_entry = _frozen_model_bytes(entry)
    selection = crossfit_select_epochs(entry_bytes, train_rows)

    staging.mkdir(parents=False, exist_ok=False)
    configuration = _configuration(inputs=inputs, source=source)
    configuration_binding = _write_artifact(
        staging, output, "configuration.json", _canonical_bytes(configuration)
    )
    folds = {
        "candidates": selection["candidates"],
        "fold_losses": selection["fold_losses"],
        "folds": [list(fold) for fold in selection["folds"]],
        "schema_version": FOLDS_SCHEMA_VERSION,
        "selected_epochs": selection["selected_epochs"],
    }
    folds_binding = _write_artifact(staging, output, "folds.json", _canonical_bytes(folds))
    selected_epochs = selection["selected_epochs"]
    if selected_epochs is None:
        report = {
            "audit_accessed": False,
            "authority": copy.deepcopy(AUTHORITY),
            "development_accessed": False,
            "operations": copy.deepcopy(OPERATIONS),
            "selected_epochs": None,
            "train_only_stop": True,
            "verdict": "family_preserving_conditional_card_ranking_not_ready_after_crossfit",
        }
        metrics = {
            "crossfit_candidates": selection["candidates"],
            "crossfit_entry": _metrics_without_predictions(selection["entry_metrics"]),
            "schema_version": METRICS_SCHEMA_VERSION,
        }
        predictions = {
            "crossfit": {
                str(epoch): selection["candidate_metrics"][epoch]["predictions"]
                for epoch in EPOCH_CHECKPOINTS
            },
            "schema_version": PREDICTIONS_SCHEMA_VERSION,
        }
        artifacts = {
            "configuration.json": configuration_binding,
            "folds.json": folds_binding,
            "metrics.json": _write_artifact(staging, output, "metrics.json", _canonical_bytes(metrics)),
            "predictions.json": _write_artifact(staging, output, "predictions.json", _canonical_bytes(predictions)),
            "report.json": _write_artifact(staging, output, "report.json", _canonical_bytes(report)),
            "report.md": _write_artifact(staging, output, "report.md", _render_report(report).encode("ascii")),
        }
        manifest = {"artifacts": artifacts, "schema_version": MANIFEST_SCHEMA_VERSION, "verdict": report["verdict"]}
        _write_artifact(staging, output, "artifact_manifest.json", _canonical_bytes(manifest))
        staging.rename(output)
        return report

    final_predictions, final_losses, final_model = train_checkpoints(
        entry_bytes,
        fit_rows=train_rows,
        score_partition=train_rows,
        epoch_checkpoints=(selected_epochs,),
    )
    model_payload = encode_model(final_model)
    model_binding = _write_artifact(staging, output, "trained_model.json", model_payload)
    restored = restore_model(model_payload)
    if _frozen_model_bytes(restored) != frozen_entry or encode_model(restored) != model_payload:
        raise ConditionalCardRankingBlocked("restored conditional model differs")

    corpus_report = residual._read_canonical(corpus_path / "report.json")
    existing_development, development_binding = residual._load_development_inputs(
        corpus_path, corpus_report
    )
    rare_report = residual._read_canonical(rare_path / "report.json")
    rare_development, rare_development_binding, rare_projection = residual._load_rare_development_inputs(
        rare_path, rare_report
    )
    development_rows = residual._merge_disjoint_rows(
        existing_development, rare_development
    )
    if (
        len(development_rows) != EXPECTED_DEVELOPMENT_ROWS
        or len(rare_development) != EXPECTED_RARE_DEVELOPMENT_ROWS
    ):
        raise ConditionalCardRankingBlocked("development support differs")
    inputs["development_dataset"] = development_binding
    inputs["rare_development_dataset"] = rare_development_binding
    inputs["rare_development_projection"] = rare_projection
    configuration = _configuration(inputs=inputs, source=source)
    (staging / "configuration.json").write_bytes(_canonical_bytes(configuration))
    configuration_binding = _binding(staging / "configuration.json")
    configuration_binding["path"] = (output / "configuration.json").as_posix()

    entry_development = evaluate_policy(entry, development_rows)
    trained_development = evaluate_policy(restored, development_rows)
    development_comparison = compare_predictions(entry_development, trained_development)
    development_checks = _comparison_checks(
        entry_development,
        trained_development,
        development_comparison,
        minimum_corrected_actions=MIN_DEVELOPMENT_CORRECTED_ACTIONS,
    )
    entry_rare = evaluate_policy(entry, rare_development)
    trained_rare = evaluate_policy(restored, rare_development)
    rare_comparison = compare_predictions(entry_rare, trained_rare)
    rare_checks = _comparison_checks(
        entry_rare,
        trained_rare,
        rare_comparison,
        minimum_corrected_actions=MIN_RARE_DEVELOPMENT_CORRECTED_ACTIONS,
        strict_mean=False,
        strict_take_pairwise=False,
    )
    ready = all(development_checks.values()) and all(rare_checks.values())
    verdict = (
        "family_preserving_conditional_card_ranking_ready_for_reserved_audit_proposal"
        if ready
        else "family_preserving_conditional_card_ranking_not_ready_after_development"
    )
    metrics = {
        "crossfit_candidates": selection["candidates"],
        "crossfit_entry": _metrics_without_predictions(selection["entry_metrics"]),
        "development": {
            "checks": development_checks,
            "comparison": development_comparison,
            "entry": _metrics_without_predictions(entry_development),
            "trained": _metrics_without_predictions(trained_development),
        },
        "final_train": {
            "entry": _metrics_without_predictions(evaluate_policy(entry, train_rows)),
            "losses": final_losses,
            "trained": _metrics_without_predictions(
                metrics_from_predictions(final_predictions[selected_epochs])
            ),
        },
        "rare_development": {
            "checks": rare_checks,
            "comparison": rare_comparison,
            "entry": _metrics_without_predictions(entry_rare),
            "trained": _metrics_without_predictions(trained_rare),
        },
        "schema_version": METRICS_SCHEMA_VERSION,
    }
    predictions = {
        "crossfit": {
            str(epoch): selection["candidate_metrics"][epoch]["predictions"]
            for epoch in EPOCH_CHECKPOINTS
        },
        "development": {
            "entry": entry_development["predictions"],
            "trained": trained_development["predictions"],
        },
        "rare_development": {
            "entry": entry_rare["predictions"],
            "trained": trained_rare["predictions"],
        },
        "schema_version": PREDICTIONS_SCHEMA_VERSION,
    }
    report = {
        "audit_accessed": False,
        "authority": copy.deepcopy(AUTHORITY),
        "development_accessed": True,
        "development_checks": development_checks,
        "development_comparison": development_comparison,
        "model": model_binding,
        "operations": copy.deepcopy(OPERATIONS),
        "rare_development_checks": rare_checks,
        "rare_development_comparison": rare_comparison,
        "schema_version": REPORT_SCHEMA_VERSION,
        "selected_epochs": selected_epochs,
        "train_only_stop": False,
        "verdict": verdict,
    }
    artifacts = {
        "configuration.json": configuration_binding,
        "folds.json": folds_binding,
        "metrics.json": _write_artifact(staging, output, "metrics.json", _canonical_bytes(metrics)),
        "predictions.json": _write_artifact(staging, output, "predictions.json", _canonical_bytes(predictions)),
        "report.json": _write_artifact(staging, output, "report.json", _canonical_bytes(report)),
        "report.md": _write_artifact(staging, output, "report.md", _render_report(report).encode("ascii")),
        "trained_model.json": model_binding,
    }
    manifest = {"artifacts": artifacts, "schema_version": MANIFEST_SCHEMA_VERSION, "verdict": verdict}
    _write_artifact(staging, output, "artifact_manifest.json", _canonical_bytes(manifest))
    staging.rename(output)
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--corpus-root", default=str(DEFAULT_CORPUS_ROOT))
    parser.add_argument("--rare-corpus-root", default=str(DEFAULT_RARE_CORPUS_ROOT))
    parser.add_argument("--predecessor-root", default=str(DEFAULT_PREDECESSOR_ROOT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        report = execute(
            repo_root=args.repo_root,
            source_commit=args.source_commit,
            corpus_root=args.corpus_root,
            rare_corpus_root=args.rare_corpus_root,
            predecessor_root=args.predecessor_root,
            output_dir=args.output_dir,
        )
    except (
        ConditionalCardRankingBlocked,
        OSError,
        ranking.CounterfactualRankingBlocked,
        residual.LargeCorpusResidualBlocked,
        runtime.SuccessorRuntimeError,
        subprocess.SubprocessError,
        uplift.UpliftCrossfitBlocked,
    ) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(_canonical_bytes(report).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
