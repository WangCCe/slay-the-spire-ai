"""Offline-only non-combat policy pilot evaluation, artifacts, and CLI."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Optional


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from analysis_scripts.noncombat_policy_dataset import (  # noqa: E402
    LABEL_MODES,
    SPLIT_NAMES,
    SUPPORTED_CATEGORIES,
    assign_trajectory_splits,
    build_policy_dataset,
    evaluate_support,
    iter_jsonl,
    to_json_value,
)


ARTIFACT_MANIFEST_VERSION = "noncombat-policy-pilot-artifacts-v1"
BASE_ARTIFACT_SUFFIXES = (
    "dataset_manifest.json",
    "split_manifest.json",
    "support.json",
    "report.md",
    "artifact_manifest.json",
)
OPTIONAL_ARTIFACT_SUFFIXES = ("metrics.json", "model.pt")
METRIC_NAMES = (
    "sample_count",
    "model_reference_top1_agreement",
    "mean_target_cross_entropy",
    "top_confidence_ece",
    "candidate_legality",
    "frequency_reference_top1_agreement",
    "per_category_counts",
)


class ArtifactRecoveryError(RuntimeError):
    """Signals incomplete artifact cleanup while preserving recovery paths."""


def build_frequency_counts(rows) -> Mapping[str, Mapping[str, int]]:
    """Count only train-row target actions, grouped by decision category."""
    counts = defaultdict(Counter)
    for row in rows:
        counts[str(row.category)][str(row.target_action_id)] += 1
    return {
        category: dict(sorted(action_counts.items()))
        for category, action_counts in sorted(counts.items())
    }


def frequency_baseline_prediction(row, frequency_counts) -> str:
    """Choose a legal candidate by train frequency, then action id."""
    candidate_ids = _candidate_ids(row)
    category_counts = frequency_counts.get(str(row.category), {})
    return min(
        candidate_ids,
        key=lambda action_id: (-int(category_counts.get(action_id, 0)), action_id),
    )


def evaluate_ranker(model, rows, *, feature_config, frequency_counts) -> Mapping[str, Any]:
    """Evaluate a fitted ranker strictly on one held-out row collection."""
    from analysis_scripts.noncombat_policy_model import predict_ranker

    ordered_rows = tuple(sorted(rows, key=lambda row: str(row.sample_id)))
    if not ordered_rows:
        raise ValueError("held-out rows must be nonempty")
    predictions = predict_ranker(model, ordered_rows, feature_config=feature_config)
    if len(predictions) != len(ordered_rows):
        raise AssertionError("ranker prediction count does not match held-out rows")

    top1_matches = []
    target_losses = []
    confidences = []
    legal_predictions = []
    frequency_matches = []
    category_counts = Counter()
    for row, prediction in zip(ordered_rows, predictions):
        if prediction.sample_id != row.sample_id:
            raise AssertionError("ranker prediction order does not match held-out rows")
        candidate_ids = _candidate_ids(row)
        try:
            target_index = candidate_ids.index(str(row.target_action_id))
        except ValueError as error:
            raise ValueError("held-out target_action_id must map to a candidate") from error
        target_probability = float(prediction.probabilities[target_index])
        if not 0.0 < target_probability <= 1.0:
            raise ValueError("ranker target probability must be in (0, 1]")
        confidence = float(prediction.confidence)
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("ranker confidence must be between zero and one")

        top1_matches.append(prediction.predicted_action_id == row.target_action_id)
        target_losses.append(-math.log(target_probability))
        confidences.append(confidence)
        legal_predictions.append(prediction.predicted_action_id in candidate_ids)
        frequency_matches.append(
            frequency_baseline_prediction(row, frequency_counts) == row.target_action_id
        )
        category_counts[str(row.category)] += 1

    return {
        "sample_count": len(ordered_rows),
        "model_reference_top1_agreement": _mean(top1_matches),
        "mean_target_cross_entropy": _mean(target_losses),
        "top_confidence_ece": _top_confidence_ece(confidences, top1_matches),
        "candidate_legality": _mean(legal_predictions),
        "frequency_reference_top1_agreement": _mean(frequency_matches),
        "per_category_counts": dict(sorted(category_counts.items())),
    }


def render_policy_report(dataset_manifest, split_manifest, support, metrics=None) -> str:
    """Render a deterministic supervised-pilot report with fixed limitations."""
    category_support = support.get("categories", {})
    groups = split_manifest.get("groups", {})
    dataset_outcomes = dataset_manifest.get("outcome_counts", {})
    support_outcomes = support.get("outcome_counts", {})
    lines = [
        "# Non-combat policy-learning pilot",
        "",
        f"Label mode: {dataset_manifest.get('label_mode', 'unknown')}",
        f"Source commit: {dataset_manifest.get('source_commit', 'unknown')}",
        "",
        "Formal non-combat RL: blocked",
        "Live policy promotion: blocked",
        "Off-policy evaluation: unsupported",
        "",
        "## Limitations",
        "Missing trajectories, target mappings, unknown behavior propensities, and contextual alternative-action overlap block off-policy evaluation.",
        "Aggregate candidate counts do not establish contextual alternative-action overlap.",
        "Outcomes are diagnostics only and are not supervised targets.",
        "",
        "## Dataset exclusions",
        _json_block(dataset_manifest.get("exclusions", {})),
        "",
        "## Category support",
    ]
    for category in (*SUPPORTED_CATEGORIES, *sorted(set(category_support) - set(SUPPORTED_CATEGORIES))):
        lines.extend((f"### {category}", _json_block(category_support.get(category, {})), ""))
    lines.extend(
        (
            "## Split counts",
            _json_block(
                {
                    "groups": {
                        split: list(groups.get(split, ()))
                        for split in SPLIT_NAMES
                    },
                    "split_sample_counts": support.get("overall", {}).get(
                        "split_sample_counts", {}
                    ),
                    "support": support.get("overall", {}),
                }
            ),
            "",
            "## Outcome diagnostics",
            _json_block({"dataset": dataset_outcomes, "support": support_outcomes}),
        )
    )
    if metrics is not None:
        lines.extend(("", "## Held-out metrics"))
        for split in ("validation", "test"):
            if split in metrics:
                lines.extend(("", f"### {split.title()}", _json_block(metrics[split])))
    return "\n".join(lines).rstrip() + "\n"


def write_pilot_artifacts(
    output_dir,
    *,
    mode,
    dataset,
    splits,
    support,
    model=None,
    metrics=None,
) -> Mapping[str, str]:
    """Transactionally replace the complete managed artifact set for one mode."""
    artifact_dir = _prepare_output_dir(output_dir)
    training_result = _validate_artifact_inputs(
        mode,
        dataset=dataset,
        support=support,
        model=model,
        metrics=metrics,
    )
    artifact_dir.mkdir(parents=True, exist_ok=True)
    if not artifact_dir.is_dir():
        raise ValueError("output_dir must be a directory")

    manifest_name = _artifact_name(mode, "artifact_manifest.json")
    desired_names = set(_base_artifact_names(mode))
    artifact_payloads = {
        f"{mode}_dataset_manifest.json": _json_bytes(dataset.manifest),
        f"{mode}_split_manifest.json": _json_bytes(splits.manifest),
        f"{mode}_support.json": _json_bytes(support),
        f"{mode}_report.md": render_policy_report(
            dataset.manifest,
            splits.manifest,
            support,
            metrics=metrics,
        ).encode("utf-8"),
    }
    if metrics is not None:
        metrics_name = _artifact_name(mode, "metrics.json")
        artifact_payloads[metrics_name] = _json_bytes(metrics)
        desired_names.add(metrics_name)

    staged_paths = {}
    try:
        backups = _preflight_backup_paths(artifact_dir, mode)
        for name, payload in sorted(artifact_payloads.items()):
            staged_path = _temporary_path(_artifact_path(artifact_dir, name))
            staged_paths[name] = staged_path
            _stage_bytes(staged_path, payload)

        if training_result is not None:
            model_name = _artifact_name(mode, "model.pt")
            staged_path = _temporary_path(_artifact_path(artifact_dir, model_name))
            staged_paths[model_name] = staged_path
            _stage_model_artifact(staged_path, training_result)
            desired_names.add(model_name)

        artifact_hashes = {
            name: _sha256_file(staged_paths[name])
            for name in sorted(staged_paths)
        }
        artifact_manifest = _artifact_manifest(
            artifact_dir,
            mode=mode,
            dataset=dataset,
            splits=splits,
            training_result=training_result,
            artifact_hashes=artifact_hashes,
        )
        manifest_stage = _temporary_path(_artifact_path(artifact_dir, manifest_name))
        staged_paths[manifest_name] = manifest_stage
        _stage_bytes(manifest_stage, _json_bytes(artifact_manifest))
        _validate_staged_artifacts(staged_paths, manifest_name, artifact_manifest)
        _commit_artifact_transaction(
            artifact_dir,
            mode,
            staged_paths,
            manifest_name,
            backups,
        )
    except Exception as error:
        cleanup_errors = _cleanup_paths(staged_paths.values())
        if cleanup_errors:
            raise _recovery_error("artifact staging failed", error, cleanup_errors) from error
        raise

    return {
        _artifact_key(name, mode): str(_artifact_path(artifact_dir, name))
        for name in sorted(desired_names)
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run support inspection or bounded supervised training without live integration."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    dataset, splits, support = _build_dataset_and_support(args)

    write_pilot_artifacts(
        args.output_dir,
        mode=args.label_mode,
        dataset=dataset,
        splits=splits,
        support=support,
    )
    if args.command == "support":
        return 0
    if support["overall"]["blocked"]:
        return 2

    from analysis_scripts.noncombat_policy_model import FeatureConfig, TrainingConfig, train_ranker

    feature_config = FeatureConfig()
    training_config = TrainingConfig(
        seed=args.seed,
        learning_rate=args.learning_rate,
        max_epochs=args.max_epochs,
        patience=args.patience,
    )
    train_rows = _rows_for_split(dataset.rows, splits, "train")
    validation_rows = _rows_for_split(dataset.rows, splits, "validation")
    test_rows = _rows_for_split(dataset.rows, splits, "test")
    result = train_ranker(
        train_rows,
        validation_rows,
        feature_config=feature_config,
        training_config=training_config,
    )
    frequency_counts = build_frequency_counts(train_rows)
    metrics = {
        "validation": evaluate_ranker(
            result.model,
            validation_rows,
            feature_config=feature_config,
            frequency_counts=frequency_counts,
        ),
        "test": evaluate_ranker(
            result.model,
            test_rows,
            feature_config=feature_config,
            frequency_counts=frequency_counts,
        ),
    }
    write_pilot_artifacts(
        args.output_dir,
        mode=args.label_mode,
        dataset=dataset,
        splits=splits,
        support=support,
        model=result,
        metrics=metrics,
    )
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("support", "train"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("--samples", nargs="+", required=True, type=Path)
        command_parser.add_argument("--output-dir", required=True, type=Path)
        command_parser.add_argument("--split-seed", required=True)
        command_parser.add_argument("--source-commit", required=True)
        command_parser.add_argument("--label-mode", choices=LABEL_MODES, required=True)
        if command == "train":
            command_parser.add_argument("--seed", type=int, default=0)
            command_parser.add_argument("--learning-rate", type=float, default=1e-3)
            command_parser.add_argument("--max-epochs", type=int, default=50)
            command_parser.add_argument("--patience", type=int, default=5)
    return parser


def _build_dataset_and_support(args):
    sample_paths = tuple(Path(path) for path in args.samples)
    samples = []
    for sample_path in sample_paths:
        samples.extend(iter_jsonl(sample_path))
    dataset = build_policy_dataset(
        samples,
        label_mode=args.label_mode,
        source_paths=sample_paths,
        source_commit=args.source_commit,
    )
    splits = assign_trajectory_splits(dataset.rows, split_seed=args.split_seed)
    return dataset, splits, evaluate_support(dataset, splits)


def _rows_for_split(rows, splits, split_name):
    return tuple(
        row
        for row in rows
        if splits.assignments.get(row.trajectory_group_id) == split_name
    )


def _candidate_ids(row) -> tuple[str, ...]:
    candidates = getattr(row, "candidates", ())
    candidate_ids = tuple(str(candidate["action_id"]) for candidate in candidates)
    if not candidate_ids:
        raise ValueError("rows require available candidates")
    return candidate_ids


def _mean(values) -> float:
    values = tuple(values)
    if not values:
        raise ValueError("metric values must be nonempty")
    return sum(float(value) for value in values) / len(values)


def _top_confidence_ece(confidences, top1_matches) -> float:
    if len(confidences) != len(top1_matches) or not confidences:
        raise ValueError("calibration requires aligned nonempty predictions")
    bins = [[] for _ in range(10)]
    for confidence, matched in zip(confidences, top1_matches):
        bin_index = min(int(float(confidence) * 10), 9)
        bins[bin_index].append((float(confidence), bool(matched)))
    total = len(confidences)
    return sum(
        (len(items) / total)
        * abs(_mean(confidence for confidence, _ in items) - _mean(matched for _, matched in items))
        for items in bins
        if items
    )


def _json_block(value) -> str:
    return json.dumps(to_json_value(value), indent=2, sort_keys=True)


def _json_bytes(value) -> bytes:
    return (json.dumps(to_json_value(value), indent=2, sort_keys=True) + "\n").encode("utf-8")


def _prepare_output_dir(output_dir) -> Path:
    artifact_dir = Path(output_dir).resolve()
    if any(part.casefold() == "checkpoints" for part in artifact_dir.parts):
        raise ValueError("pilot artifacts cannot be written under checkpoints")
    return artifact_dir


def _artifact_path(output_dir: Path, name: str) -> Path:
    path = output_dir / name
    if path.parent != output_dir:
        raise AssertionError("artifact path escaped explicit output_dir")
    return path


def _validate_artifact_inputs(mode, *, dataset, support, model, metrics):
    if mode not in LABEL_MODES:
        raise ValueError(f"unsupported label mode: {mode}")
    if not isinstance(getattr(dataset, "manifest", None), Mapping):
        raise ValueError("dataset requires a manifest mapping")
    if dataset.manifest.get("label_mode") != mode:
        raise ValueError("dataset manifest label_mode must match mode")
    for row in getattr(dataset, "rows", ()):
        if getattr(row, "label_mode", None) != mode:
            raise ValueError("every dataset row label_mode must match mode")
    if not isinstance(support, Mapping) or not isinstance(support.get("overall"), Mapping):
        raise ValueError("support requires an overall mapping")
    blocked = support["overall"].get("blocked")
    if not isinstance(blocked, bool):
        raise ValueError("support overall blocked flag must be boolean")
    if (model is None) != (metrics is None):
        raise ValueError("model and metrics must be both present or both absent")
    if blocked and (model is not None or metrics is not None):
        raise ValueError("blocked support cannot write model or metrics")
    if metrics is not None:
        _validate_metrics(metrics)
    if model is None:
        return None

    from analysis_scripts.noncombat_policy_model import ARTIFACT_STEMS, TrainingResult

    if not isinstance(model, TrainingResult):
        raise ValueError("model must be a TrainingResult")
    model_manifest = model.artifact_manifest
    if model_manifest.get("label_mode") != mode:
        raise ValueError("TrainingResult label_mode must match mode")
    if model_manifest.get("artifact_stem") != ARTIFACT_STEMS[mode]:
        raise ValueError("TrainingResult artifact_stem must match mode")
    return model


def _validate_metrics(metrics) -> None:
    if not isinstance(metrics, Mapping) or set(metrics) != {"validation", "test"}:
        raise ValueError("metrics require exactly validation and test blocks")
    for split in ("validation", "test"):
        block = metrics[split]
        if not isinstance(block, Mapping) or not set(METRIC_NAMES).issubset(block):
            raise ValueError(f"metrics {split} block is incomplete")


def _artifact_name(mode: str, suffix: str) -> str:
    return f"{mode}_{suffix}"


def _base_artifact_names(mode: str) -> tuple[str, ...]:
    return tuple(_artifact_name(mode, suffix) for suffix in BASE_ARTIFACT_SUFFIXES)


def _managed_artifact_names(mode: str) -> tuple[str, ...]:
    return tuple(
        _artifact_name(mode, suffix)
        for suffix in (*BASE_ARTIFACT_SUFFIXES, *OPTIONAL_ARTIFACT_SUFFIXES)
    )


def _temporary_path(path: Path) -> Path:
    return path.with_name(f".{path.name}.tmp")


def _backup_path(path: Path) -> Path:
    return path.with_name(f".{path.name}.backup")


def _stage_bytes(path: Path, payload: bytes) -> None:
    path.write_bytes(payload)


def _stage_model_artifact(path: Path, training_result) -> None:
    import torch

    state_dict = {
        name: tensor.detach().cpu().clone()
        for name, tensor in training_result.model.state_dict().items()
    }
    payload = {
        "state_dict": state_dict,
        "artifact_manifest": to_json_value(training_result.artifact_manifest),
    }
    torch.save(payload, path)


def _artifact_manifest(
    artifact_dir: Path,
    *,
    mode,
    dataset,
    splits,
    training_result,
    artifact_hashes,
):
    return {
        "schema_version": ARTIFACT_MANIFEST_VERSION,
        "mode": mode,
        "output_dir": str(artifact_dir),
        "source_commit": str(dataset.manifest.get("source_commit", "")),
        "dataset_manifest_hash": dataset.manifest.get("manifest_hash"),
        "split_manifest_hash": splits.manifest.get("manifest_hash"),
        "configuration": {
            "label_mode": mode,
            "split_seed": splits.manifest.get("split_seed"),
        },
        "training_artifact_manifest": (
            to_json_value(training_result.artifact_manifest)
            if training_result is not None
            else None
        ),
        "artifact_hashes": dict(sorted(artifact_hashes.items())),
        "formal_noncombat_rl_training_ready": False,
        "live_policy_promotion_ready": False,
    }


def _validate_staged_artifacts(staged_paths, manifest_name, artifact_manifest) -> None:
    expected_hashes = {
        name: _sha256_file(path)
        for name, path in sorted(staged_paths.items())
        if name != manifest_name
    }
    if expected_hashes != artifact_manifest["artifact_hashes"]:
        raise AssertionError("staged artifact hashes do not match the manifest")
    serialized_manifest = json.loads(staged_paths[manifest_name].read_text(encoding="utf-8"))
    if serialized_manifest != to_json_value(artifact_manifest):
        raise AssertionError("staged artifact manifest does not match its payload")


def _preflight_backup_paths(artifact_dir: Path, mode) -> dict[str, Path]:
    backups = {}
    for name in sorted(_managed_artifact_names(mode)):
        final_path = _artifact_path(artifact_dir, name)
        backup_path = _backup_path(final_path)
        if backup_path.exists():
            raise ArtifactRecoveryError(f"stale transaction backup exists: {backup_path}")
        if not final_path.exists():
            continue
        if not final_path.is_file():
            raise ValueError(f"managed artifact path is not a file: {final_path}")
        backups[name] = backup_path
    return backups


def _commit_artifact_transaction(
    artifact_dir: Path,
    mode,
    staged_paths,
    manifest_name,
    backups,
) -> None:
    installed = []
    try:
        for name, backup_path in backups.items():
            final_path = _artifact_path(artifact_dir, name)
            final_path.replace(backup_path)

        install_order = sorted(name for name in staged_paths if name != manifest_name)
        install_order.append(manifest_name)
        for name in install_order:
            final_path = _artifact_path(artifact_dir, name)
            installed.append(final_path)
            staged_paths[name].replace(final_path)
    except Exception as error:
        rollback_errors = _rollback_artifact_transaction(
            artifact_dir,
            mode,
            installed,
            backups,
            manifest_name,
        )
        if rollback_errors:
            raise _recovery_error("artifact transaction failed", error, rollback_errors) from error
        raise

    cleanup_errors = _cleanup_paths(backups.values())
    if cleanup_errors:
        raise _recovery_error("artifact transaction committed", None, cleanup_errors)


def _rollback_artifact_transaction(
    artifact_dir: Path,
    mode,
    installed,
    backups,
    manifest_name,
):
    errors = []
    for final_path in reversed(installed):
        errors.extend(_cleanup_paths((final_path,)))
    non_manifest_restore_errors = []
    for name, backup_path in backups.items():
        if name == manifest_name:
            continue
        if not backup_path.exists():
            continue
        try:
            backup_path.replace(_artifact_path(artifact_dir, name))
        except Exception as error:
            non_manifest_restore_errors.append((backup_path, error))
    errors.extend(non_manifest_restore_errors)

    manifest_path = _artifact_path(artifact_dir, manifest_name)
    manifest_backup = backups.get(manifest_name)
    managed_state_errors = _recovered_managed_state_errors(
        artifact_dir,
        mode,
        backups,
        manifest_name,
    )
    if managed_state_errors:
        errors.extend(managed_state_errors)
        errors.extend(_cleanup_paths((manifest_path,)))
        if manifest_backup is not None and manifest_backup.exists():
            errors.append(
                (
                    manifest_backup,
                    RuntimeError("withheld until recovered managed set is complete"),
                )
            )
        return errors

    if manifest_backup is not None and manifest_backup.exists():
        try:
            manifest_backup.replace(manifest_path)
        except Exception as error:
            errors.append((manifest_backup, error))
    return errors


def _recovered_managed_state_errors(
    artifact_dir: Path,
    mode,
    backups,
    manifest_name,
):
    errors = []
    for name in _managed_artifact_names(mode):
        if name == manifest_name:
            continue
        final_path = _artifact_path(artifact_dir, name)
        backup_path = backups.get(name)
        if backup_path is None:
            if final_path.exists():
                errors.append(
                    (
                        final_path,
                        RuntimeError("unbacked managed artifact remains after rollback"),
                    )
                )
            continue
        if not final_path.is_file():
            errors.append(
                (
                    final_path,
                    RuntimeError("managed artifact final was not recovered as a file"),
                )
            )
        if backup_path.exists():
            errors.append(
                (
                    backup_path,
                    RuntimeError("managed artifact backup remains after rollback"),
                )
            )

    manifest_path = _artifact_path(artifact_dir, manifest_name)
    if manifest_path.exists():
        errors.append(
            (
                manifest_path,
                RuntimeError("artifact manifest final remains before recovery restore"),
            )
        )
    return errors


def _cleanup_paths(paths):
    errors = []
    for path in paths:
        try:
            if path.exists():
                path.unlink()
        except Exception as error:
            errors.append((path, error))
    return errors


def _recovery_error(prefix, primary_error, errors) -> ArtifactRecoveryError:
    details = ", ".join(f"{path}: {error}" for path, error in errors)
    if primary_error is None:
        return ArtifactRecoveryError(f"{prefix}; cleanup incomplete: {details}")
    return ArtifactRecoveryError(
        f"{prefix}: {primary_error}; recovery incomplete: {details}"
    )


def _artifact_key(name: str, mode: str) -> str:
    suffix = name.removeprefix(f"{mode}_").removesuffix(".json")
    return suffix


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
