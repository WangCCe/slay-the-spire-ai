"""Train and evaluate a low-capacity card uplift residual on the large corpus."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import types
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


from analysis_scripts import noncombat_card_counterfactual_corpus_expansion_runner as corpus
from analysis_scripts import noncombat_card_counterfactual_ranking_training as ranking
from analysis_scripts import noncombat_card_counterfactual_ranking_training_runner as base_runner
from analysis_scripts import noncombat_card_counterfactual_uplift_residual_crossfit as uplift
from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot as pilot


SCHEMA_VERSION = "noncombat-large-corpus-card-uplift-residual-v1"
CONFIGURATION_SCHEMA_VERSION = f"{SCHEMA_VERSION}-configuration"
FOLDS_SCHEMA_VERSION = f"{SCHEMA_VERSION}-folds"
METRICS_SCHEMA_VERSION = f"{SCHEMA_VERSION}-metrics"
PREDICTIONS_SCHEMA_VERSION = f"{SCHEMA_VERSION}-predictions"
REPORT_SCHEMA_VERSION = f"{SCHEMA_VERSION}-report"
MANIFEST_SCHEMA_VERSION = f"{SCHEMA_VERSION}-manifest"
FOLD_COUNT = 5
MIN_DEVELOPMENT_CORRECTED_ACTIONS = 4
DEFAULT_CORPUS_ROOT = Path(
    "reports/noncombat_card_counterfactual_corpus_expansion_20260813_r1"
)
DEFAULT_OUTPUT_DIR = Path(
    "reports/noncombat_large_corpus_card_uplift_residual_20260813_r1"
)
SOURCE_PATHS = tuple(
    sorted(
        {
            *uplift.SOURCE_PATHS,
            "analysis_scripts/noncombat_card_counterfactual_corpus_expansion_runner.py",
            "analysis_scripts/noncombat_large_corpus_card_uplift_residual.py",
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


class LargeCorpusResidualBlocked(RuntimeError):
    """Raised when the fixed source-only residual contract cannot proceed."""


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
        raise LargeCorpusResidualBlocked("artifact is not canonical") from exc


def _read_canonical(path: Path | str) -> dict[str, Any]:
    source = Path(path).resolve()
    try:
        payload = source.read_bytes()
        value = json.loads(payload.decode("ascii"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LargeCorpusResidualBlocked(f"invalid canonical JSON: {source}") from exc
    if not isinstance(value, dict) or _canonical_bytes(value) != payload:
        raise LargeCorpusResidualBlocked(f"noncanonical JSON: {source}")
    return value


def _binding(path: Path | str) -> dict[str, Any]:
    source = Path(path).resolve()
    try:
        payload = source.read_bytes()
    except OSError as exc:
        raise LargeCorpusResidualBlocked(f"input is unavailable: {source}") from exc
    return {
        "path": source.as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


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
            raise LargeCorpusResidualBlocked("source commit is unavailable")
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", source_commit, "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise LargeCorpusResidualBlocked("source commit is not an ancestor") from exc
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
            raise LargeCorpusResidualBlocked(
                f"source path is unavailable at commit: {relative}"
            ) from exc
        if hashlib.sha256(committed).hexdigest() != actual["sha256"]:
            raise LargeCorpusResidualBlocked(f"source bytes differ: {relative}")
        bindings[relative] = actual
    return bindings


def _validate_corpus_metadata(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    report = _read_canonical(root / "report.json")
    registration = _read_canonical(root / "registration.json")
    schedule = registration.get("schedule")
    if (
        report.get("verdict")
        != "card_counterfactual_corpus_ready_for_source_only_training_proposal"
        or report.get("audit_accessed") is not False
        or report.get("training_performed") is not False
        or report.get("schedule") != schedule
        or schedule
        != {
            "development_seeds": list(corpus.DEVELOPMENT_SEEDS),
            "reserved_audit_seeds": list(corpus.RESERVED_AUDIT_SEEDS),
            "seed_status": "new-train-development-with-untouched-audit",
            "train_seeds": list(corpus.TRAIN_SEEDS),
        }
        or registration.get("authority") != corpus.AUTHORITY
        or registration.get("operations") != corpus.OPERATIONS
    ):
        raise LargeCorpusResidualBlocked("corpus metadata differs")
    return report, registration


def _load_train_inputs(
    corpus_root: Path,
) -> tuple[
    tuple[ranking.CounterfactualRankingRow, ...],
    Any,
    dict[str, dict[str, Any]],
]:
    root = corpus_root.resolve()
    report, registration = _validate_corpus_metadata(root)
    report_binding = _binding(root / "report.json")
    registration_binding = _binding(root / "registration.json")
    train_path = root / "train_dataset_full.json"
    train_binding = _binding(train_path)
    if report.get("datasets", {}).get("train") != train_binding:
        raise LargeCorpusResidualBlocked("train dataset binding differs")
    lineage_binding = registration.get("inputs", {}).get("lineage_registration")
    if not isinstance(lineage_binding, dict) or _binding(
        lineage_binding.get("path", "")
    ) != lineage_binding:
        raise LargeCorpusResidualBlocked("lineage registration differs")
    lineage = _read_canonical(lineage_binding["path"])
    entry_binding = lineage.get("inputs", {}).get("entry_checkpoint")
    if not isinstance(entry_binding, dict) or _binding(
        entry_binding.get("path", "")
    ) != entry_binding:
        raise LargeCorpusResidualBlocked("entry checkpoint differs")
    try:
        train = ranking.restore_counterfactual_partition(train_path.read_bytes())
        bootstrap = ranking.restore_entry_bootstrap(
            Path(entry_binding["path"]).read_bytes()
        )
    except (OSError, ranking.CounterfactualRankingBlocked) as exc:
        raise LargeCorpusResidualBlocked(str(exc)) from exc
    if train.name != "train" or train.seeds != corpus.TRAIN_SEEDS:
        raise LargeCorpusResidualBlocked("train seed lineage differs")
    rows = uplift.validate_rows(train.rows)
    if len(rows) != 497:
        raise LargeCorpusResidualBlocked("train support differs")
    return rows, bootstrap, {
        "corpus_registration": registration_binding,
        "corpus_report": report_binding,
        "entry_checkpoint": copy.deepcopy(entry_binding),
        "lineage_registration": copy.deepcopy(lineage_binding),
        "train_dataset": train_binding,
    }


def _load_development_inputs(
    corpus_root: Path, report: Mapping[str, Any]
) -> tuple[
    tuple[ranking.CounterfactualRankingRow, ...],
    dict[str, Any],
]:
    path = corpus_root.resolve() / "development_dataset_full.json"
    binding = _binding(path)
    if report.get("datasets", {}).get("development") != binding:
        raise LargeCorpusResidualBlocked("development dataset binding differs")
    try:
        partition = ranking.restore_counterfactual_partition(path.read_bytes())
    except (OSError, ranking.CounterfactualRankingBlocked) as exc:
        raise LargeCorpusResidualBlocked(str(exc)) from exc
    if partition.name != "holdout" or partition.seeds != corpus.DEVELOPMENT_SEEDS:
        raise LargeCorpusResidualBlocked("development seed lineage differs")
    rows = uplift.validate_rows(partition.rows)
    if len(rows) != 126:
        raise LargeCorpusResidualBlocked("development support differs")
    return rows, binding


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
        raise LargeCorpusResidualBlocked("entry checkpoint changed during scoring")
    return scores


def _selection_key(
    metrics: Mapping[str, Any], configuration: uplift.ResidualConfiguration
) -> tuple[float, float, float, float, int, int]:
    return (
        float(metrics["mean_top_action_regret"]),
        float(metrics["maximum_top_action_regret"]),
        -float(metrics["weighted_pairwise_accuracy"]),
        -float(metrics["unique_best_accuracy"]),
        configuration.strength,
        -configuration.shrinkage,
    )


def select_train_configuration(
    rows: Sequence[ranking.CounterfactualRankingRow],
    base_scores: Mapping[str, Sequence[float]],
) -> dict[str, Any]:
    normalized = uplift.validate_rows(rows)
    folds = uplift.build_seed_folds(
        sorted({row.seed for row in normalized}), FOLD_COUNT
    )
    candidates: list[dict[str, Any]] = []
    selected_scores: dict[str, tuple[float, ...]] | None = None
    for configuration in uplift.GRID:
        scores, unseen = uplift._cross_fitted_scores(
            normalized, folds, configuration, base_scores
        )
        metrics = uplift.evaluate_scores(normalized, scores)
        candidates.append(
            {
                "configuration": configuration.as_dict(),
                "metrics": {
                    key: value
                    for key, value in metrics.items()
                    if key != "predictions"
                },
                "selection_key": list(_selection_key(metrics, configuration)),
                "unseen_take_actions": unseen,
            }
        )
    selected_row = min(candidates, key=lambda item: tuple(item["selection_key"]))
    selected = uplift.ResidualConfiguration(**selected_row["configuration"])
    selected_scores, unseen = uplift._cross_fitted_scores(
        normalized, folds, selected, base_scores
    )
    if unseen != selected_row["unseen_take_actions"]:
        raise LargeCorpusResidualBlocked("selected train predictions differ")
    base_metrics = uplift.evaluate_scores(normalized, base_scores)
    candidate_metrics = uplift.evaluate_scores(normalized, selected_scores)
    comparison = uplift.compare_predictions(base_metrics, candidate_metrics)
    checks = {
        "maximum_regret_nonincreasing": candidate_metrics[
            "maximum_top_action_regret"
        ]
        <= base_metrics["maximum_top_action_regret"],
        "mean_regret_decreased": candidate_metrics["mean_top_action_regret"]
        < base_metrics["mean_top_action_regret"],
        "pairwise_accuracy_increased": candidate_metrics[
            "weighted_pairwise_accuracy"
        ]
        > base_metrics["weighted_pairwise_accuracy"],
        "unique_best_accuracy_nondecreasing": candidate_metrics[
            "unique_best_accuracy"
        ]
        >= base_metrics["unique_best_accuracy"],
    }
    return {
        "base_metrics": base_metrics,
        "candidate_metrics": candidate_metrics,
        "candidates": candidates,
        "checks": checks,
        "comparison": comparison,
        "folds": [list(fold) for fold in folds],
        "selected_configuration": selected,
    }


def _development_checks(
    base: Mapping[str, Any],
    candidate: Mapping[str, Any],
    comparison: Mapping[str, int],
) -> dict[str, bool]:
    return {
        "corrected_actions": comparison["corrected_actions"]
        >= MIN_DEVELOPMENT_CORRECTED_ACTIONS,
        "maximum_regret_nonincreasing": candidate["maximum_top_action_regret"]
        <= base["maximum_top_action_regret"],
        "mean_regret_decreased": candidate["mean_top_action_regret"]
        < base["mean_top_action_regret"],
        "pairwise_accuracy_increased": candidate["weighted_pairwise_accuracy"]
        > base["weighted_pairwise_accuracy"],
        "unique_best_accuracy_nondecreasing": candidate["unique_best_accuracy"]
        >= base["unique_best_accuracy"],
        "worsened_actions_bounded": comparison["worsened_actions"]
        <= comparison["corrected_actions"],
    }


def _write_artifact(
    staging: Path, output: Path, name: str, payload: bytes
) -> dict[str, Any]:
    (staging / name).write_bytes(payload)
    return {
        "path": (output / name).as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _metrics_without_predictions(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key != "predictions"}


def _render_report(report: Mapping[str, Any], metrics: Mapping[str, Any]) -> str:
    train = metrics["train"]
    development = metrics["development"]
    lines = [
        "# Large-Corpus Card Uplift Residual",
        "",
        f"- Verdict: `{report['verdict']}`",
        f"- Selected configuration: `{report['selected_configuration']}`",
        f"- Model parameters: `{report['model_parameters']}`",
        f"- Unseen development take actions: `{report['unseen_development_take_actions']}`",
        "",
        "| Partition | Metric | Frozen entry | Residual |",
        "| --- | --- | ---: | ---: |",
    ]
    for name, values in (("Train cross-fit", train), ("Development", development)):
        for metric in (
            "mean_top_action_regret",
            "maximum_top_action_regret",
            "weighted_pairwise_accuracy",
            "unique_best_accuracy",
        ):
            lines.append(
                f"| {name} | {metric} | {values['base'][metric]:.6f} | "
                f"{values['candidate'][metric]:.6f} |"
            )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- Configuration selection used train seeds only.",
            "- The fixed model was persisted before development parsing.",
            "- Reserved audit seeds, native code, game, and CommunicationMod were not accessed.",
            "- A positive verdict authorizes only a separate reserved-audit proposal.",
            "",
        ]
    )
    return "\n".join(lines)


def execute(
    *,
    repo_root: Path | str,
    source_commit: str,
    corpus_root: Path | str = DEFAULT_CORPUS_ROOT,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    corpus_path = Path(corpus_root).resolve()
    output = Path(output_dir).resolve()
    staging = output.with_name(f".{output.name}.{source_commit}.staging")
    if output.exists() or staging.exists():
        raise LargeCorpusResidualBlocked("output boundary differs")
    sources = _source_bindings(root, source_commit)
    train_rows, bootstrap, inputs = _load_train_inputs(corpus_path)
    entry_before = pilot.encode_candidate_card_policy(bootstrap)
    train_base_scores = _base_scores(bootstrap, train_rows)
    selection = select_train_configuration(train_rows, train_base_scores)
    selected = selection["selected_configuration"]
    model = uplift.fit_uplift_model(train_rows, shrinkage=selected.shrinkage)
    model_bytes = uplift.encode_uplift_model(model, selected)

    staging.mkdir(parents=False, exist_ok=False)
    model_binding = _write_artifact(
        staging, output, "residual_model.json", model_bytes
    )
    restored_model, restored_configuration = uplift.restore_uplift_model(model_bytes)
    if restored_configuration != selected:
        raise LargeCorpusResidualBlocked("restored configuration differs")

    corpus_report = _read_canonical(corpus_path / "report.json")
    development_rows, development_binding = _load_development_inputs(
        corpus_path, corpus_report
    )
    inputs["development_dataset"] = development_binding
    development_base_scores = _base_scores(bootstrap, development_rows)
    development_scores, unseen = uplift.score_residual_rows(
        development_rows,
        development_base_scores,
        restored_model,
        restored_configuration,
    )
    development_base = uplift.evaluate_scores(
        development_rows, development_base_scores
    )
    development_candidate = uplift.evaluate_scores(
        development_rows, development_scores
    )
    development_comparison = uplift.compare_predictions(
        development_base, development_candidate
    )
    development_checks = _development_checks(
        development_base, development_candidate, development_comparison
    )
    if pilot.encode_candidate_card_policy(bootstrap) != entry_before:
        raise LargeCorpusResidualBlocked("entry checkpoint changed during study")
    if uplift.encode_uplift_model(restored_model, restored_configuration) != model_bytes:
        raise LargeCorpusResidualBlocked("residual model changed during development")
    ready = all(selection["checks"].values()) and all(
        development_checks.values()
    )
    verdict = (
        "large_corpus_card_uplift_residual_ready_for_reserved_audit_proposal"
        if ready
        else "large_corpus_card_uplift_residual_not_ready"
    )
    configuration = {
        "authority": copy.deepcopy(AUTHORITY),
        "development_gates": {
            "minimum_corrected_actions": MIN_DEVELOPMENT_CORRECTED_ACTIONS,
            "worsened_actions_must_not_exceed_corrected": True,
        },
        "fold_count": FOLD_COUNT,
        "grid": [item.as_dict() for item in uplift.GRID],
        "inputs": inputs,
        "operations": copy.deepcopy(OPERATIONS),
        "schema_version": CONFIGURATION_SCHEMA_VERSION,
        "selection_order": [
            "mean_top_action_regret",
            "maximum_top_action_regret",
            "weighted_pairwise_accuracy_desc",
            "unique_best_accuracy_desc",
            "strength",
            "shrinkage_desc",
        ],
        "source": {
            "bindings": sources,
            "commit": source_commit,
            "repo_root": root.as_posix(),
        },
    }
    folds = {
        "candidates": selection["candidates"],
        "folds": selection["folds"],
        "schema_version": FOLDS_SCHEMA_VERSION,
        "selected_configuration": selected.as_dict(),
    }
    metrics = {
        "development": {
            "base": _metrics_without_predictions(development_base),
            "candidate": _metrics_without_predictions(development_candidate),
            "checks": development_checks,
            "comparison": development_comparison,
        },
        "schema_version": METRICS_SCHEMA_VERSION,
        "train": {
            "base": _metrics_without_predictions(selection["base_metrics"]),
            "candidate": _metrics_without_predictions(
                selection["candidate_metrics"]
            ),
            "checks": selection["checks"],
            "comparison": selection["comparison"],
        },
    }
    predictions = {
        "development": {
            "base": development_base["predictions"],
            "candidate": development_candidate["predictions"],
        },
        "schema_version": PREDICTIONS_SCHEMA_VERSION,
        "train": {
            "base": selection["base_metrics"]["predictions"],
            "candidate": selection["candidate_metrics"]["predictions"],
        },
    }
    report = {
        "audit_accessed": False,
        "authority": copy.deepcopy(AUTHORITY),
        "development_checks": development_checks,
        "development_comparison": development_comparison,
        "model": model_binding,
        "model_parameters": len(restored_model.card_uplifts) + 1,
        "operations": copy.deepcopy(OPERATIONS),
        "schema_version": REPORT_SCHEMA_VERSION,
        "selected_configuration": selected.as_dict(),
        "train_checks": selection["checks"],
        "unseen_development_take_actions": unseen,
        "verdict": verdict,
    }
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
            staging,
            output,
            "report.md",
            _render_report(report, metrics).encode("ascii"),
        ),
        "residual_model.json": model_binding,
    }
    manifest = {
        "artifacts": artifacts,
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "verdict": verdict,
    }
    _write_artifact(
        staging, output, "artifact_manifest.json", _canonical_bytes(manifest)
    )
    staging.rename(output)
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--corpus-root", default=str(DEFAULT_CORPUS_ROOT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        report = execute(
            repo_root=args.repo_root,
            source_commit=args.source_commit,
            corpus_root=args.corpus_root,
            output_dir=args.output_dir,
        )
    except (
        LargeCorpusResidualBlocked,
        OSError,
        ranking.CounterfactualRankingBlocked,
        subprocess.SubprocessError,
        uplift.UpliftCrossfitBlocked,
    ) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(_canonical_bytes(report).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
