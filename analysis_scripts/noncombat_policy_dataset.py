"""Build deterministic offline datasets from canonical non-combat samples."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping


CANONICAL_SCHEMA_VERSION = "noncombat-rl-decision-v2"
DATASET_MANIFEST_VERSION = "noncombat-policy-dataset-v1"
SPLIT_MANIFEST_VERSION = "noncombat-policy-split-v1"
LABEL_MODES = ("current", "bottled")
SPLIT_NAMES = ("train", "validation", "test")
MINIMUM_TRAJECTORIES = 10


@dataclass(frozen=True)
class PolicyRow:
    sample_id: str
    trajectory_group_id: str
    category: str
    state: Mapping[str, Any]
    candidates: tuple[Mapping[str, Any], ...]
    target_action_id: str
    outcome: Mapping[str, Any]


@dataclass(frozen=True)
class DatasetBuild:
    rows: tuple[PolicyRow, ...]
    manifest: Mapping[str, Any]


@dataclass(frozen=True)
class SplitManifest:
    assignments: Mapping[str, str]
    groups: Mapping[str, tuple[str, ...]]
    manifest: Mapping[str, Any]


def iter_jsonl(path) -> Iterator[Mapping[str, Any]]:
    """Yield mapping rows from a JSONL source without loading the file at once."""
    with Path(path).open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, Mapping):
                yield row


def build_policy_dataset(
    samples,
    *,
    label_mode,
    source_paths,
    source_commit,
    bottled_confidence="high",
) -> DatasetBuild:
    """Filter canonical samples into one isolated supervision label mode."""
    if label_mode not in LABEL_MODES:
        raise ValueError(f"unsupported label_mode: {label_mode}")

    exclusions = Counter()
    schema_versions = Counter()
    behavior_probability_counts = Counter()
    rows = []
    for sample in samples:
        if not isinstance(sample, Mapping):
            exclusions["legacy_schema"] += 1
            continue

        schema_version = str(sample.get("schema_version") or "")
        schema_versions[schema_version] += 1
        exclusion, target_action_id, candidates = _eligibility(
            sample,
            label_mode=label_mode,
            bottled_confidence=bottled_confidence,
        )
        if exclusion is not None:
            exclusions[exclusion] += 1
            continue

        if sample.get("behavior_action_probability") is None:
            behavior_probability_counts["unknown"] += 1
        else:
            behavior_probability_counts["known"] += 1

        rows.append(
            PolicyRow(
                sample_id=str(sample["sample_id"]),
                trajectory_group_id=str(sample["trajectory_group_id"]),
                category=str(sample.get("category") or ""),
                state=dict(sample.get("state") or {}),
                candidates=tuple(dict(candidate) for candidate in candidates),
                target_action_id=target_action_id,
                outcome=dict(sample.get("outcome") or {}),
            )
        )

    ordered_rows = tuple(_sort_rows(rows))
    manifest = _dataset_manifest(
        ordered_rows,
        label_mode=label_mode,
        source_paths=source_paths,
        source_commit=source_commit,
        schema_versions=schema_versions,
        exclusions=exclusions,
        behavior_probability_counts=behavior_probability_counts,
    )
    return DatasetBuild(rows=ordered_rows, manifest=manifest)


def assign_trajectory_splits(
    rows,
    *,
    split_seed,
    train_fraction=0.60,
    validation_fraction=0.20,
) -> SplitManifest:
    """Assign each trajectory, rather than each decision, to one stable split."""
    if not 0 <= train_fraction <= 1 or not 0 <= validation_fraction <= 1:
        raise ValueError("split fractions must be between zero and one")
    if train_fraction + validation_fraction > 1:
        raise ValueError("train and validation fractions cannot exceed one")

    ordered_rows = _sort_rows(rows)
    group_ids = sorted({row.trajectory_group_id for row in ordered_rows})
    ordered_groups = sorted(
        group_ids,
        key=lambda group_id: (_split_digest(split_seed, group_id), group_id),
    )
    group_count = len(ordered_groups)
    train_count = int(group_count * train_fraction)
    validation_count = int(group_count * validation_fraction)
    boundaries = (train_count, train_count + validation_count)
    groups = {
        "train": tuple(ordered_groups[: boundaries[0]]),
        "validation": tuple(ordered_groups[boundaries[0] : boundaries[1]]),
        "test": tuple(ordered_groups[boundaries[1] :]),
    }
    assignments = {
        group_id: split_name
        for split_name in SPLIT_NAMES
        for group_id in groups[split_name]
    }
    manifest = {
        "schema_version": SPLIT_MANIFEST_VERSION,
        "split_seed": str(split_seed),
        "train_fraction": train_fraction,
        "validation_fraction": validation_fraction,
        "assignments": dict(sorted(assignments.items())),
        "groups": {split: list(groups[split]) for split in SPLIT_NAMES},
        "manifest_hash": None,
    }
    manifest["manifest_hash"] = _canonical_hash(manifest)
    return SplitManifest(
        assignments=dict(sorted(assignments.items())),
        groups=groups,
        manifest=manifest,
    )


def evaluate_support(dataset, splits, *, min_trajectories=10) -> Mapping[str, Any]:
    """Report structural support only; outcomes remain diagnostics, never labels."""
    required_trajectories = max(MINIMUM_TRAJECTORIES, int(min_trajectories))
    rows = _sort_rows(dataset.rows)
    group_ids = {row.trajectory_group_id for row in rows}
    split_group_counts = {
        split: len(splits.groups.get(split, ())) for split in SPLIT_NAMES
    }
    overall_reasons = []
    if len(group_ids) < required_trajectories:
        overall_reasons.append("insufficient_trajectory_groups")
    for split in SPLIT_NAMES:
        if split_group_counts[split] == 0:
            overall_reasons.append(f"empty_{split}_split")

    category_groups = defaultdict(lambda: defaultdict(set))
    outcome_counts = Counter()
    for row in rows:
        split = splits.assignments.get(row.trajectory_group_id)
        if split in SPLIT_NAMES:
            category_groups[row.category][split].add(row.trajectory_group_id)
        join_status = row.outcome.get("join_status")
        if join_status:
            outcome_counts[str(join_status)] += 1
        if row.outcome.get("victory") is True:
            outcome_counts["victory"] += 1

    categories = {}
    for category in sorted(category_groups):
        train_count = len(category_groups[category]["train"])
        held_out_count = len(
            category_groups[category]["validation"]
            | category_groups[category]["test"]
        )
        reasons = []
        if train_count < 2:
            reasons.append("insufficient_train_trajectories")
        if held_out_count < 1:
            reasons.append("missing_held_out_trajectory")
        categories[category] = {
            "train_trajectory_count": train_count,
            "held_out_trajectory_count": held_out_count,
            "evaluable": not reasons,
            "blocking_reasons": reasons,
        }

    return {
        "overall": {
            "trajectory_count": len(group_ids),
            "minimum_trajectory_count": required_trajectories,
            "split_trajectory_counts": split_group_counts,
            "blocked": bool(overall_reasons),
            "blocking_reasons": overall_reasons,
        },
        "categories": categories,
        "outcome_counts": dict(sorted(outcome_counts.items())),
    }


def _eligibility(sample, *, label_mode, bottled_confidence):
    if sample.get("schema_version") != CANONICAL_SCHEMA_VERSION:
        return "legacy_schema", None, ()
    if not _identifier(sample.get("trajectory_group_id")):
        return "missing_trajectory_group", None, ()
    if not _identifier(sample.get("behavior_policy_id")) or not _identifier(
        sample.get("behavior_policy_commit")
    ):
        return "missing_behavior_policy", None, ()

    candidates = _available_candidates(sample.get("candidate_actions"))
    if not candidates:
        return "missing_candidates", None, ()

    if label_mode == "current":
        target_action_id = sample.get("selected_action_id")
    else:
        bottled_label = sample.get("bottled_label")
        bottled_label = bottled_label if isinstance(bottled_label, Mapping) else {}
        if bottled_label.get("oracle_mode") != "native_bottled":
            return "bottled_not_native", None, ()
        if bottled_label.get("confidence") != bottled_confidence:
            return "bottled_confidence", None, ()
        target_action_id = bottled_label.get("action_id")

    if not _identifier(target_action_id):
        return "missing_target", None, ()
    target_action_id = str(target_action_id)
    if target_action_id not in {str(candidate["action_id"]) for candidate in candidates}:
        return "target_not_candidate", None, ()
    return None, target_action_id, candidates


def _available_candidates(raw_candidates):
    if not isinstance(raw_candidates, list):
        return ()
    return tuple(
        candidate
        for candidate in raw_candidates
        if isinstance(candidate, Mapping)
        and candidate.get("available") is True
        and _identifier(candidate.get("action_id"))
    )


def _dataset_manifest(
    rows,
    *,
    label_mode,
    source_paths,
    source_commit,
    schema_versions,
    exclusions,
    behavior_probability_counts,
):
    category_rows = Counter(row.category for row in rows)
    category_groups = defaultdict(set)
    action_support = Counter()
    outcome_counts = Counter()
    for row in rows:
        category_groups[row.category].add(row.trajectory_group_id)
        action_support[row.target_action_id] += 1
        join_status = row.outcome.get("join_status")
        if join_status:
            outcome_counts[str(join_status)] += 1
        if row.outcome.get("victory") is True:
            outcome_counts["victory"] += 1

    trajectory_counts = {
        category: len(category_groups[category]) for category in sorted(category_groups)
    }
    trajectory_counts["overall"] = len({row.trajectory_group_id for row in rows})
    manifest = {
        "schema_version": DATASET_MANIFEST_VERSION,
        "source_commit": str(source_commit),
        "source_hashes": _source_hashes(source_paths),
        "input_sample_count": sum(schema_versions.values()),
        "schema_versions": dict(sorted(schema_versions.items())),
        "eligible_row_count": len(rows),
        "exclusions": dict(sorted(exclusions.items())),
        "label_mode": label_mode,
        "label_mode_counts": {
            mode: len(rows) if mode == label_mode else 0 for mode in LABEL_MODES
        },
        "category_counts": dict(sorted(category_rows.items())),
        "trajectory_counts": trajectory_counts,
        "outcome_counts": dict(sorted(outcome_counts.items())),
        "action_support": dict(sorted(action_support.items())),
        "behavior_probability_counts": {
            "known": behavior_probability_counts["known"],
            "unknown": behavior_probability_counts["unknown"],
        },
        "manifest_hash": None,
    }
    manifest["manifest_hash"] = _canonical_hash(manifest)
    return manifest


def _source_hashes(source_paths):
    return {
        path: _sha256_file(Path(path))
        for path in sorted({str(Path(path)) for path in source_paths})
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sort_rows(rows: Iterable[PolicyRow]):
    return sorted(rows, key=lambda row: (row.trajectory_group_id, row.sample_id))


def _split_digest(split_seed, group_id: str) -> str:
    return hashlib.sha256(f"{split_seed}:{group_id}".encode("utf-8")).hexdigest()


def _canonical_hash(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _identifier(value) -> bool:
    return isinstance(value, str) and bool(value.strip())
