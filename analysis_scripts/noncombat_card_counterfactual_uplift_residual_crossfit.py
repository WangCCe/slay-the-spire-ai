"""Nested source-only cross-fit for a frozen-base card uplift residual."""

from __future__ import annotations

import argparse
import copy
from dataclasses import dataclass
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import types
from collections import defaultdict
from collections.abc import Mapping, Sequence
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


from analysis_scripts import noncombat_card_counterfactual_ranking_training as ranking
from analysis_scripts import noncombat_card_counterfactual_ranking_training_runner as base_runner
from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot as pilot
from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot_runner as pilot_runner


SCHEMA_VERSION = "noncombat-card-counterfactual-uplift-residual-crossfit-v1"
CONFIGURATION_SCHEMA_VERSION = f"{SCHEMA_VERSION}-configuration"
FOLDS_SCHEMA_VERSION = f"{SCHEMA_VERSION}-folds"
PREDICTIONS_SCHEMA_VERSION = f"{SCHEMA_VERSION}-predictions"
METRICS_SCHEMA_VERSION = f"{SCHEMA_VERSION}-metrics"
REPORT_SCHEMA_VERSION = f"{SCHEMA_VERSION}-report"
MANIFEST_SCHEMA_VERSION = f"{SCHEMA_VERSION}-manifest"

OUTER_FOLD_COUNT = 4
INNER_FOLD_COUNT = 3
SHRINKAGES = (1, 3, 10)
STRENGTHS = (16, 32, 64, 128)
MIN_CORRECTED_ACTIONS = 2
MIN_SAFE_MEAN_FOLDS = 3
EXPECTED_TRAIN_SEEDS = tuple(range(1000, 1016))
EXPECTED_DEVELOPMENT_SEEDS = tuple(range(1016, 1024))

DEFAULT_EXPERIMENT_ROOT = Path(
    "reports/noncombat_card_counterfactual_scorer_weight_20260813_r1"
)
DEFAULT_OUTPUT_DIR = Path(
    "reports/noncombat_card_counterfactual_uplift_residual_crossfit_20260813_r1"
)
SOURCE_PATHS = tuple(
    sorted(
        {
            *base_runner.BOUND_SOURCE_PATHS,
            "analysis_scripts/noncombat_card_counterfactual_uplift_residual_crossfit.py",
        }
    )
)
AUTHORITY = {
    name: False
    for name in (
        "audit_access",
        "communication_mod",
        "formal_rl",
        "fresh_evaluation",
        "gameplay",
        "model_loading",
        "native_loading",
        "policy_quality",
        "production_model_loading",
        "promotion",
        "qualification",
    )
}


class UpliftCrossfitBlocked(RuntimeError):
    """Raised when the fixed cross-fit contract cannot be preserved."""


@dataclass(frozen=True)
class ResidualConfiguration:
    shrinkage: int
    strength: int

    def as_dict(self) -> dict[str, int]:
        return {"shrinkage": self.shrinkage, "strength": self.strength}


@dataclass(frozen=True)
class UpliftModel:
    global_uplift: float
    card_uplifts: dict[str, float]
    card_counts: dict[str, int]


GRID = tuple(
    ResidualConfiguration(shrinkage=shrinkage, strength=strength)
    for shrinkage in SHRINKAGES
    for strength in STRENGTHS
)


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise UpliftCrossfitBlocked("artifact is not canonical") from exc


def _read_canonical(path: Path | str) -> dict[str, Any]:
    source = Path(path).resolve()
    try:
        payload = source.read_bytes()
        value = json.loads(payload.decode("ascii"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UpliftCrossfitBlocked(f"invalid canonical JSON: {source}") from exc
    if not isinstance(value, dict) or _canonical_bytes(value) != payload:
        raise UpliftCrossfitBlocked(f"noncanonical JSON: {source}")
    return value


def _binding(path: Path | str) -> dict[str, Any]:
    source = Path(path).resolve()
    try:
        payload = source.read_bytes()
    except OSError as exc:
        raise UpliftCrossfitBlocked(f"input is unavailable: {source}") from exc
    return {
        "path": source.as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _source_bindings(repo_root: Path, source_commit: str) -> dict[str, Any]:
    try:
        if pilot_runner._git(repo_root, "cat-file", "-t", source_commit) != "commit":
            raise UpliftCrossfitBlocked("source commit is unavailable")
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", source_commit, "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise UpliftCrossfitBlocked("source commit is not an ancestor") from exc
    bindings: dict[str, Any] = {}
    for relative in SOURCE_PATHS:
        path = repo_root / relative
        actual = _binding(path)
        try:
            committed = subprocess.run(
                ["git", "show", f"{source_commit}:{relative}"],
                cwd=repo_root,
                check=True,
                capture_output=True,
            ).stdout
        except (OSError, subprocess.CalledProcessError) as exc:
            raise UpliftCrossfitBlocked(
                f"source path is unavailable at commit: {relative}"
            ) from exc
        if hashlib.sha256(committed).hexdigest() != actual["sha256"]:
            raise UpliftCrossfitBlocked(f"source bytes differ: {relative}")
        bindings[relative] = actual
    return bindings


def build_seed_folds(seeds: Sequence[int], count: int) -> tuple[tuple[int, ...], ...]:
    normalized = tuple(sorted(seeds))
    if (
        isinstance(count, bool)
        or not isinstance(count, int)
        or count < 2
        or len(normalized) < count
        or len(set(normalized)) != len(normalized)
        or any(isinstance(seed, bool) or not isinstance(seed, int) for seed in normalized)
    ):
        raise UpliftCrossfitBlocked("seed fold inputs differ")
    folds = tuple(tuple(normalized[index::count]) for index in range(count))
    flattened = tuple(seed for fold in folds for seed in fold)
    if sorted(flattened) != list(normalized) or any(not fold for fold in folds):
        raise UpliftCrossfitBlocked("seed fold coverage differs")
    return folds


def _card_id(candidate: Mapping[str, Any]) -> str:
    raw = candidate.get("raw")
    card_id = raw.get("id") if isinstance(raw, Mapping) else None
    if not isinstance(card_id, str) or not card_id:
        raise UpliftCrossfitBlocked("take candidate card id differs")
    return card_id


def validate_rows(
    rows: Sequence[ranking.CounterfactualRankingRow],
) -> tuple[ranking.CounterfactualRankingRow, ...]:
    normalized = tuple(rows)
    if not normalized or len({row.source_sha256 for row in normalized}) != len(normalized):
        raise UpliftCrossfitBlocked("row source identities differ")
    for row in normalized:
        if (
            len(row.candidates) != 4
            or len(row.action_returns) != 4
            or tuple(candidate.get("kind") for candidate in row.candidates)
            != ("take", "take", "take", "skip")
        ):
            raise UpliftCrossfitBlocked("card action boundary differs")
        for candidate in row.candidates[:3]:
            _card_id(candidate)
        if any(not math.isfinite(value) for value in row.action_returns):
            raise UpliftCrossfitBlocked("counterfactual return differs")
    ordering = tuple((row.seed, row.decision_index) for row in normalized)
    if ordering != tuple(sorted(ordering)):
        raise UpliftCrossfitBlocked("row ordering differs")
    return normalized


def fit_uplift_model(
    rows: Sequence[ranking.CounterfactualRankingRow], *, shrinkage: int
) -> UpliftModel:
    normalized = validate_rows(rows)
    if shrinkage not in SHRINKAGES:
        raise UpliftCrossfitBlocked("uplift shrinkage differs")
    values: dict[str, list[float]] = defaultdict(list)
    all_values: list[float] = []
    for row in normalized:
        skip_return = row.action_returns[3]
        for index, candidate in enumerate(row.candidates[:3]):
            uplift = row.action_returns[index] - skip_return
            values[_card_id(candidate)].append(uplift)
            all_values.append(uplift)
    if not all_values:
        raise UpliftCrossfitBlocked("uplift support is empty")
    global_uplift = math.fsum(all_values) / len(all_values)
    card_uplifts = {
        card_id: (math.fsum(items) + shrinkage * global_uplift)
        / (len(items) + shrinkage)
        for card_id, items in sorted(values.items())
    }
    if not math.isfinite(global_uplift) or any(
        not math.isfinite(value) for value in card_uplifts.values()
    ):
        raise UpliftCrossfitBlocked("uplift model is nonfinite")
    return UpliftModel(
        global_uplift=global_uplift,
        card_uplifts=card_uplifts,
        card_counts={key: len(values[key]) for key in sorted(values)},
    )


def compose_scores(
    row: ranking.CounterfactualRankingRow,
    base_scores: Sequence[float],
    model: UpliftModel,
    *,
    strength: int,
) -> tuple[tuple[float, ...], int]:
    validate_rows((row,))
    if strength not in STRENGTHS or len(base_scores) != 4:
        raise UpliftCrossfitBlocked("residual score inputs differ")
    scores: list[float] = []
    unseen = 0
    for index, candidate in enumerate(row.candidates):
        if index == 3:
            uplift = 0.0
        else:
            card_id = _card_id(candidate)
            unseen += int(card_id not in model.card_uplifts)
            uplift = model.card_uplifts.get(card_id, model.global_uplift)
        score = float(base_scores[index]) + strength * uplift
        if not math.isfinite(score):
            raise UpliftCrossfitBlocked("composed score is nonfinite")
        scores.append(score)
    return tuple(scores), unseen


def evaluate_scores(
    rows: Sequence[ranking.CounterfactualRankingRow],
    scores_by_source: Mapping[str, Sequence[float]],
) -> dict[str, Any]:
    normalized = validate_rows(rows)
    if set(scores_by_source) != {row.source_sha256 for row in normalized}:
        raise UpliftCrossfitBlocked("prediction source coverage differs")
    regrets: list[float] = []
    pair_weight = 0.0
    pair_correct = 0.0
    unique_states = 0
    unique_correct = 0
    predictions: list[dict[str, Any]] = []
    for row in normalized:
        scores = tuple(float(value) for value in scores_by_source[row.source_sha256])
        if len(scores) != 4 or any(not math.isfinite(value) for value in scores):
            raise UpliftCrossfitBlocked("prediction score boundary differs")
        maximum = max(scores)
        predicted_index = min(
            (index for index, value in enumerate(scores) if value == maximum),
            key=lambda index: row.candidates[index]["action_id"],
        )
        best_return = max(row.action_returns)
        best_indices = tuple(
            index
            for index, value in enumerate(row.action_returns)
            if value == best_return
        )
        regret = best_return - row.action_returns[predicted_index]
        regrets.append(regret)
        if len(best_indices) == 1:
            unique_states += 1
            unique_correct += int(predicted_index == best_indices[0])
        for left in range(4):
            for right in range(left + 1, 4):
                difference = row.action_returns[left] - row.action_returns[right]
                if difference == 0:
                    continue
                better, worse = (left, right) if difference > 0 else (right, left)
                weight = abs(difference)
                pair_weight += weight
                pair_correct += weight * (
                    1.0
                    if scores[better] > scores[worse]
                    else 0.5
                    if scores[better] == scores[worse]
                    else 0.0
                )
        predictions.append(
            {
                "actual_best_action_ids": sorted(
                    row.candidates[index]["action_id"] for index in best_indices
                ),
                "decision_index": row.decision_index,
                "predicted_action_id": row.candidates[predicted_index]["action_id"],
                "regret": regret,
                "scores": [
                    {
                        "action_id": candidate["action_id"],
                        "score": score,
                    }
                    for candidate, score in zip(row.candidates, scores, strict=True)
                ],
                "seed": row.seed,
                "source_sha256": row.source_sha256,
            }
        )
    if pair_weight <= 0 or unique_states <= 0:
        raise UpliftCrossfitBlocked("metric support is insufficient")
    return {
        "maximum_top_action_regret": max(regrets),
        "mean_top_action_regret": math.fsum(regrets) / len(regrets),
        "predictions": predictions,
        "source_states": len(normalized),
        "unique_best_accuracy": unique_correct / unique_states,
        "unique_best_correct": unique_correct,
        "unique_best_states": unique_states,
        "weighted_pairwise_accuracy": pair_correct / pair_weight,
        "weighted_pairwise_margin": pair_weight,
    }


def _cross_fitted_scores(
    rows: Sequence[ranking.CounterfactualRankingRow],
    folds: Sequence[Sequence[int]],
    configuration: ResidualConfiguration,
    base_scores: Mapping[str, Sequence[float]],
) -> tuple[dict[str, tuple[float, ...]], int]:
    normalized = validate_rows(rows)
    row_seeds = {row.seed for row in normalized}
    fold_seeds = [set(fold) for fold in folds]
    if (
        set().union(*fold_seeds) != row_seeds
        or sum(len(fold) for fold in fold_seeds) != len(row_seeds)
        or any(fold_seeds[left] & fold_seeds[right] for left in range(len(fold_seeds)) for right in range(left + 1, len(fold_seeds)))
    ):
        raise UpliftCrossfitBlocked("cross-fit seed isolation differs")
    result: dict[str, tuple[float, ...]] = {}
    unseen_count = 0
    for heldout in fold_seeds:
        fit_rows = tuple(row for row in normalized if row.seed not in heldout)
        heldout_rows = tuple(row for row in normalized if row.seed in heldout)
        if not fit_rows or not heldout_rows or {row.seed for row in fit_rows} & heldout:
            raise UpliftCrossfitBlocked("cross-fit split differs")
        model = fit_uplift_model(fit_rows, shrinkage=configuration.shrinkage)
        for row in heldout_rows:
            scores, unseen = compose_scores(
                row,
                base_scores[row.source_sha256],
                model,
                strength=configuration.strength,
            )
            result[row.source_sha256] = scores
            unseen_count += unseen
    if len(result) != len(normalized):
        raise UpliftCrossfitBlocked("cross-fit prediction count differs")
    return result, unseen_count


def _selection_key(
    metrics: Mapping[str, Any], configuration: ResidualConfiguration
) -> tuple[float, float, float, float, int, int]:
    return (
        float(metrics["mean_top_action_regret"]),
        float(metrics["maximum_top_action_regret"]),
        -float(metrics["weighted_pairwise_accuracy"]),
        -float(metrics["unique_best_accuracy"]),
        configuration.strength,
        -configuration.shrinkage,
    )


def compare_predictions(
    base: Mapping[str, Any], candidate: Mapping[str, Any]
) -> dict[str, int]:
    base_rows = {row["source_sha256"]: row for row in base["predictions"]}
    candidate_rows = {
        row["source_sha256"]: row for row in candidate["predictions"]
    }
    if set(base_rows) != set(candidate_rows):
        raise UpliftCrossfitBlocked("comparison source identity differs")
    flips = corrected = worsened = 0
    for source, before in base_rows.items():
        after = candidate_rows[source]
        changed = before["predicted_action_id"] != after["predicted_action_id"]
        flips += int(changed)
        corrected += int(
            changed
            and before["predicted_action_id"] not in before["actual_best_action_ids"]
            and after["predicted_action_id"] in after["actual_best_action_ids"]
        )
        worsened += int(after["regret"] > before["regret"])
    return {"action_flips": flips, "corrected_actions": corrected, "worsened_actions": worsened}


def run_nested_crossfit(
    rows: Sequence[ranking.CounterfactualRankingRow],
    base_scores: Mapping[str, Sequence[float]],
) -> dict[str, Any]:
    normalized = validate_rows(rows)
    seeds = tuple(sorted({row.seed for row in normalized}))
    outer_folds = build_seed_folds(seeds, OUTER_FOLD_COUNT)
    outer_scores: dict[str, tuple[float, ...]] = {}
    fold_rows: list[dict[str, Any]] = []
    for outer_index, outer_holdout in enumerate(outer_folds):
        heldout = set(outer_holdout)
        fit_rows = tuple(row for row in normalized if row.seed not in heldout)
        heldout_rows = tuple(row for row in normalized if row.seed in heldout)
        inner_folds = build_seed_folds(
            sorted({row.seed for row in fit_rows}), INNER_FOLD_COUNT
        )
        candidates: list[dict[str, Any]] = []
        for configuration in GRID:
            inner_scores, unseen = _cross_fitted_scores(
                fit_rows, inner_folds, configuration, base_scores
            )
            inner_metrics = evaluate_scores(fit_rows, inner_scores)
            candidates.append(
                {
                    "configuration": configuration.as_dict(),
                    "metrics": {key: value for key, value in inner_metrics.items() if key != "predictions"},
                    "selection_key": list(_selection_key(inner_metrics, configuration)),
                    "unseen_take_actions": unseen,
                }
            )
        selected_row = min(candidates, key=lambda row: tuple(row["selection_key"]))
        selected = ResidualConfiguration(**selected_row["configuration"])
        model = fit_uplift_model(fit_rows, shrinkage=selected.shrinkage)
        unseen_count = 0
        for row in heldout_rows:
            scores, unseen = compose_scores(
                row,
                base_scores[row.source_sha256],
                model,
                strength=selected.strength,
            )
            outer_scores[row.source_sha256] = scores
            unseen_count += unseen
        base_fold = evaluate_scores(
            heldout_rows,
            {row.source_sha256: base_scores[row.source_sha256] for row in heldout_rows},
        )
        candidate_fold = evaluate_scores(
            heldout_rows,
            {row.source_sha256: outer_scores[row.source_sha256] for row in heldout_rows},
        )
        fold_rows.append(
            {
                "base": {key: value for key, value in base_fold.items() if key != "predictions"},
                "candidate": {key: value for key, value in candidate_fold.items() if key != "predictions"},
                "fit_seeds": sorted({row.seed for row in fit_rows}),
                "heldout_seeds": list(outer_holdout),
                "index": outer_index,
                "inner_candidates": candidates,
                "inner_folds": [list(fold) for fold in inner_folds],
                "selected_configuration": selected.as_dict(),
                "unseen_heldout_take_actions": unseen_count,
            }
        )
    if set(outer_scores) != {row.source_sha256 for row in normalized}:
        raise UpliftCrossfitBlocked("outer prediction coverage differs")
    base_metrics = evaluate_scores(normalized, base_scores)
    candidate_metrics = evaluate_scores(normalized, outer_scores)
    comparison = compare_predictions(base_metrics, candidate_metrics)
    checks = {
        "corrected_actions": comparison["corrected_actions"] >= MIN_CORRECTED_ACTIONS,
        "fold_maximum_regret_nonincreasing": all(
            row["candidate"]["maximum_top_action_regret"]
            <= row["base"]["maximum_top_action_regret"]
            for row in fold_rows
        ),
        "fold_mean_regret_safety": sum(
            row["candidate"]["mean_top_action_regret"]
            <= row["base"]["mean_top_action_regret"]
            for row in fold_rows
        )
        >= MIN_SAFE_MEAN_FOLDS,
        "maximum_regret_nonincreasing": candidate_metrics["maximum_top_action_regret"]
        <= base_metrics["maximum_top_action_regret"],
        "mean_regret_decreased": candidate_metrics["mean_top_action_regret"]
        < base_metrics["mean_top_action_regret"],
        "pairwise_accuracy_increased": candidate_metrics["weighted_pairwise_accuracy"]
        > base_metrics["weighted_pairwise_accuracy"],
        "unique_best_accuracy_nondecreasing": candidate_metrics["unique_best_accuracy"]
        >= base_metrics["unique_best_accuracy"],
    }
    return {
        "base_metrics": base_metrics,
        "candidate_metrics": candidate_metrics,
        "checks": checks,
        "comparison": comparison,
        "folds": fold_rows,
        "outer_folds": [list(fold) for fold in outer_folds],
        "verdict": (
            "card_counterfactual_uplift_residual_ready_for_audit_proposal"
            if all(checks.values())
            else "card_counterfactual_uplift_residual_not_ready"
        ),
    }


def _load_bound_inputs(experiment_root: Path) -> tuple[
    tuple[ranking.CounterfactualRankingRow, ...],
    Any,
    dict[str, Any],
]:
    root = experiment_root.resolve()
    report_path = root / "report.json"
    registration_path = root / "registration.json"
    train_path = root / "train_dataset_full.json"
    development_path = root / "development_dataset_full.json"
    report = _read_canonical(report_path)
    registration = _read_canonical(registration_path)
    train_binding = _binding(train_path)
    development_binding = _binding(development_path)
    if (
        report.get("verdict") != "card_counterfactual_scorer_weight_not_ready"
        or report.get("audit_accessed") is not False
        or report.get("datasets", {}).get("train") != train_binding
        or report.get("datasets", {}).get("development") != development_binding
    ):
        raise UpliftCrossfitBlocked("scorer-pilot dataset lineage differs")
    entry_binding = registration.get("inputs", {}).get("entry_checkpoint")
    if not isinstance(entry_binding, dict) or _binding(entry_binding.get("path", "")) != entry_binding:
        raise UpliftCrossfitBlocked("entry checkpoint lineage differs")
    try:
        train = ranking.restore_counterfactual_partition(train_path.read_bytes())
        development = ranking.restore_counterfactual_partition(
            development_path.read_bytes()
        )
        bootstrap = ranking.restore_entry_bootstrap(
            Path(entry_binding["path"]).read_bytes()
        )
    except (OSError, ranking.CounterfactualRankingBlocked) as exc:
        raise UpliftCrossfitBlocked(str(exc)) from exc
    if (
        train.name != "train"
        or train.seeds != EXPECTED_TRAIN_SEEDS
        or development.name != "holdout"
        or development.seeds != EXPECTED_DEVELOPMENT_SEEDS
    ):
        raise UpliftCrossfitBlocked("dataset seed lineage differs")
    rows = validate_rows((*train.rows, *development.rows))
    return rows, bootstrap, {
        "development_dataset": development_binding,
        "entry_checkpoint": entry_binding,
        "scorer_report": _binding(report_path),
        "scorer_registration": _binding(registration_path),
        "train_dataset": train_binding,
    }


def _base_scores(
    bootstrap: Any, rows: Sequence[ranking.CounterfactualRankingRow]
) -> dict[str, tuple[float, ...]]:
    before = pilot.encode_candidate_card_policy(bootstrap)
    scores = {
        row.source_sha256: tuple(
            float(value)
            for value in ranking._joint_log_probabilities(bootstrap, row)
            .detach()
            .tolist()
        )
        for row in rows
    }
    if pilot.encode_candidate_card_policy(bootstrap) != before:
        raise UpliftCrossfitBlocked("entry model changed during scoring")
    return scores


def _write_artifact(
    staging: Path, output: Path, name: str, payload: bytes
) -> dict[str, Any]:
    (staging / name).write_bytes(payload)
    return {
        "path": (output / name).as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _render_report(result: Mapping[str, Any]) -> str:
    base = result["base_metrics"]
    candidate = result["candidate_metrics"]
    lines = [
        "# Card Counterfactual Uplift Residual Cross-Fit",
        "",
        f"- Verdict: `{result['verdict']}`",
        f"- Outer folds: `{OUTER_FOLD_COUNT}`",
        f"- Source states: `{candidate['source_states']}`",
        f"- Action flips: `{result['comparison']['action_flips']}`",
        f"- Corrected actions: `{result['comparison']['corrected_actions']}`",
        "",
        "| Metric | Frozen entry | Uplift residual |",
        "| --- | ---: | ---: |",
        f"| Mean regret | {base['mean_top_action_regret']:.6f} | {candidate['mean_top_action_regret']:.6f} |",
        f"| Maximum regret | {base['maximum_top_action_regret']:.6f} | {candidate['maximum_top_action_regret']:.6f} |",
        f"| Weighted pairwise accuracy | {base['weighted_pairwise_accuracy']:.6f} | {candidate['weighted_pairwise_accuracy']:.6f} |",
        f"| Unique-best accuracy | {base['unique_best_accuracy']:.6f} | {candidate['unique_best_accuracy']:.6f} |",
        "",
        "## Checks",
        "",
    ]
    lines.extend(
        f"- {name}: `{'pass' if passed else 'fail'}`"
        for name, passed in sorted(result["checks"].items())
    )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- Source-only exposed development evidence; audit seeds were not accessed.",
            "- No native module, game, CommunicationMod, or production model was loaded.",
            "- A positive verdict authorizes only a separate audit proposal.",
            "",
        ]
    )
    return "\n".join(lines)


def execute(
    *,
    repo_root: Path | str,
    source_commit: str,
    experiment_root: Path | str = DEFAULT_EXPERIMENT_ROOT,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    output = Path(output_dir).resolve()
    staging = output.with_name(f".{output.name}.{source_commit}.staging")
    if output.exists() or staging.exists():
        raise UpliftCrossfitBlocked("output boundary differs")
    sources = _source_bindings(root, source_commit)
    rows, bootstrap, inputs = _load_bound_inputs(Path(experiment_root))
    base_scores = _base_scores(bootstrap, rows)
    result = run_nested_crossfit(rows, base_scores)
    configuration = {
        "authority": copy.deepcopy(AUTHORITY),
        "folds": {
            "inner_count": INNER_FOLD_COUNT,
            "outer_count": OUTER_FOLD_COUNT,
            "rule": "sorted-round-robin-seed-folds-v1",
        },
        "gates": {
            "minimum_corrected_actions": MIN_CORRECTED_ACTIONS,
            "minimum_safe_mean_folds": MIN_SAFE_MEAN_FOLDS,
        },
        "grid": [configuration.as_dict() for configuration in GRID],
        "inputs": inputs,
        "schema_version": CONFIGURATION_SCHEMA_VERSION,
        "source": {
            "bindings": sources,
            "commit": source_commit,
            "repo_root": root.as_posix(),
        },
    }
    folds = {
        "outer_folds": result["outer_folds"],
        "rows": result["folds"],
        "schema_version": FOLDS_SCHEMA_VERSION,
    }
    predictions = {
        "base": result["base_metrics"]["predictions"],
        "candidate": result["candidate_metrics"]["predictions"],
        "schema_version": PREDICTIONS_SCHEMA_VERSION,
    }
    metrics = {
        "base": {key: value for key, value in result["base_metrics"].items() if key != "predictions"},
        "candidate": {key: value for key, value in result["candidate_metrics"].items() if key != "predictions"},
        "checks": result["checks"],
        "comparison": result["comparison"],
        "folds": [
            {
                "base": row["base"],
                "candidate": row["candidate"],
                "index": row["index"],
            }
            for row in result["folds"]
        ],
        "schema_version": METRICS_SCHEMA_VERSION,
    }
    report = {
        "audit_accessed": False,
        "authority": copy.deepcopy(AUTHORITY),
        "checks": result["checks"],
        "comparison": result["comparison"],
        "schema_version": REPORT_SCHEMA_VERSION,
        "verdict": result["verdict"],
    }
    staging.mkdir(parents=False, exist_ok=False)
    artifacts = {
        "configuration.json": _write_artifact(
            staging, output, "configuration.json", _canonical_bytes(configuration)
        ),
        "folds.json": _write_artifact(
            staging, output, "folds.json", _canonical_bytes(folds)
        ),
        "metrics.json": _write_artifact(
            staging, output, "metrics.json", _canonical_bytes(metrics)
        ),
        "predictions.json": _write_artifact(
            staging, output, "predictions.json", _canonical_bytes(predictions)
        ),
        "report.json": _write_artifact(
            staging, output, "report.json", _canonical_bytes(report)
        ),
        "report.md": _write_artifact(
            staging, output, "report.md", _render_report(result).encode("ascii")
        ),
    }
    manifest = {
        "artifacts": artifacts,
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "verdict": result["verdict"],
    }
    _write_artifact(
        staging,
        output,
        "artifact_manifest.json",
        _canonical_bytes(manifest),
    )
    staging.rename(output)
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--experiment-root", default=str(DEFAULT_EXPERIMENT_ROOT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        report = execute(
            repo_root=args.repo_root,
            source_commit=args.source_commit,
            experiment_root=args.experiment_root,
            output_dir=args.output_dir,
        )
    except (OSError, subprocess.SubprocessError, UpliftCrossfitBlocked) as exc:
        print(str(exc))
        return 1
    print(_canonical_bytes(report).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
