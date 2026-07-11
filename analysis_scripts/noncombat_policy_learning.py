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
METRIC_NAMES = (
    "sample_count",
    "model_reference_top1_agreement",
    "mean_target_cross_entropy",
    "top_confidence_ece",
    "candidate_legality",
    "frequency_reference_top1_agreement",
    "per_category_counts",
)


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
    """Atomically write offline-only artifacts within one explicit output directory."""
    if mode not in LABEL_MODES:
        raise ValueError(f"unsupported label mode: {mode}")
    artifact_dir = _prepare_output_dir(output_dir)
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
        artifact_payloads[f"{mode}_metrics.json"] = _json_bytes(metrics)

    paths = {}
    for name, payload in artifact_payloads.items():
        path = _artifact_path(artifact_dir, name)
        _write_atomic_bytes(path, payload)
        paths[_artifact_key(name, mode)] = str(path)

    if model is not None:
        model_path = _artifact_path(artifact_dir, f"{mode}_model.pt")
        _write_model_artifact(model_path, model)
        paths["model"] = str(model_path)

    final_paths = [Path(path) for path in paths.values()]
    artifact_manifest = {
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
            to_json_value(model.artifact_manifest) if model is not None else None
        ),
        "artifact_hashes": {
            path.name: _sha256_file(path) for path in sorted(final_paths, key=lambda value: value.name)
        },
        "formal_noncombat_rl_training_ready": False,
        "live_policy_promotion_ready": False,
    }
    manifest_path = _artifact_path(artifact_dir, f"{mode}_artifact_manifest.json")
    _write_atomic_bytes(manifest_path, _json_bytes(artifact_manifest))
    paths["artifact_manifest"] = str(manifest_path)
    return dict(sorted(paths.items()))


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
    artifact_dir.mkdir(parents=True, exist_ok=True)
    if not artifact_dir.is_dir():
        raise ValueError("output_dir must be a directory")
    return artifact_dir


def _artifact_path(output_dir: Path, name: str) -> Path:
    path = output_dir / name
    if path.parent != output_dir:
        raise AssertionError("artifact path escaped explicit output_dir")
    return path


def _write_atomic_bytes(path: Path, payload: bytes) -> None:
    temporary_path = path.with_name(f".{path.name}.tmp")
    try:
        temporary_path.write_bytes(payload)
        temporary_path.replace(path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def _write_model_artifact(path: Path, training_result) -> None:
    from analysis_scripts.noncombat_policy_model import TrainingResult
    import torch

    if not isinstance(training_result, TrainingResult):
        raise TypeError("model must be a TrainingResult")
    state_dict = {
        name: tensor.detach().cpu().clone()
        for name, tensor in training_result.model.state_dict().items()
    }
    payload = {
        "state_dict": state_dict,
        "artifact_manifest": to_json_value(training_result.artifact_manifest),
    }
    temporary_path = path.with_name(f".{path.name}.tmp")
    try:
        torch.save(payload, temporary_path)
        temporary_path.replace(path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def _artifact_key(name: str, mode: str) -> str:
    suffix = name.removeprefix(f"{mode}_").removesuffix(".json")
    return suffix


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
