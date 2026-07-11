"""Build immutable, deterministic offline datasets from canonical non-combat samples."""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from numbers import Real
from types import MappingProxyType
from typing import Any


CANONICAL_SCHEMA_VERSION = "noncombat-rl-decision-v2"
DATASET_MANIFEST_VERSION = "noncombat-policy-dataset-v1"
SPLIT_MANIFEST_VERSION = "noncombat-policy-split-v1"
LABEL_MODES = ("current", "bottled")
SPLIT_NAMES = ("train", "validation", "test")
SUPPORTED_CATEGORIES = ("shop", "event", "route", "card_reward")
MINIMUM_TRAJECTORIES = 10
NON_MAPPING_SCHEMA_BUCKET = "<non-mapping>"


@dataclass(frozen=True)
class PolicyRow:
    sample_id: str
    trajectory_group_id: str
    category: str
    state: Mapping[str, Any]
    candidates: tuple[Mapping[str, Any], ...]
    target_action_id: str
    outcome: Mapping[str, Any]
    source: Mapping[str, Any] = field(default_factory=dict)
    label_mode: str = ""
    behavior_policy_id: str = ""
    behavior_policy_commit: str = ""
    behavior_action_probability: Any = None
    behavior_probability_status: str = "unknown"
    label_provenance: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        probability_valid, probability, status = _normalize_behavior_probability(
            self.behavior_action_probability,
            self.behavior_probability_status,
        )
        if not probability_valid:
            raise ValueError("invalid behavior probability evidence")
        object.__setattr__(self, "behavior_action_probability", probability)
        object.__setattr__(self, "behavior_probability_status", status)
        object.__setattr__(self, "state", freeze_value(self.state))
        object.__setattr__(self, "candidates", tuple(freeze_value(candidate) for candidate in self.candidates))
        object.__setattr__(self, "outcome", freeze_value(self.outcome))
        object.__setattr__(self, "source", freeze_value(self.source))
        object.__setattr__(self, "label_provenance", freeze_value(self.label_provenance))


@dataclass(frozen=True)
class DatasetBuild:
    rows: tuple[PolicyRow, ...]
    manifest: Mapping[str, Any]

    def __post_init__(self):
        object.__setattr__(self, "rows", tuple(self.rows))
        object.__setattr__(self, "manifest", freeze_value(self.manifest))


@dataclass(frozen=True)
class SplitManifest:
    assignments: Mapping[str, str]
    groups: Mapping[str, tuple[str, ...]]
    manifest: Mapping[str, Any]

    def __post_init__(self):
        object.__setattr__(self, "assignments", freeze_value(self.assignments))
        object.__setattr__(self, "groups", freeze_value(self.groups))
        object.__setattr__(self, "manifest", freeze_value(self.manifest))


def freeze_value(value):
    """Recursively freeze JSON-compatible values used by rows and manifests."""
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(key): freeze_value(value[key]) for key in sorted(value, key=str)}
        )
    if isinstance(value, (list, tuple)):
        return tuple(freeze_value(item) for item in value)
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise TypeError(f"value is not JSON-compatible: {type(value).__name__}")


def to_json_value(value):
    """Convert immutable dataset values into plain JSON-compatible dict/list values."""
    if is_dataclass(value):
        return {item.name: to_json_value(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Mapping):
        return {str(key): to_json_value(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (list, tuple)):
        return [to_json_value(item) for item in value]
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise TypeError(f"value is not JSON-compatible: {type(value).__name__}")


def iter_jsonl(path) -> Iterator[Any]:
    """Yield every JSONL value, failing with source context instead of dropping rows."""
    source_path = Path(path)
    with source_path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"{source_path}:{line_number}: malformed JSON ({error.msg})"
                ) from error


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
    if bottled_confidence != "high":
        raise ValueError("bottled_confidence must be literal 'high'")

    exclusions = Counter()
    schema_versions = Counter()
    behavior_probability_counts = Counter()
    rows = []
    input_sample_count = 0
    for sample in samples:
        input_sample_count += 1
        if not isinstance(sample, Mapping):
            schema_versions[NON_MAPPING_SCHEMA_BUCKET] += 1
            exclusions["legacy_schema"] += 1
            continue

        schema_version = _schema_bucket(sample.get("schema_version"))
        schema_versions[schema_version] += 1
        exclusion, target_action_id, candidates, label_provenance = _eligibility(
            sample,
            label_mode=label_mode,
        )
        if exclusion is not None:
            exclusions[exclusion] += 1
            continue

        probability_valid, behavior_probability, behavior_status = _normalize_behavior_probability(
            sample.get("behavior_action_probability"),
            sample.get("behavior_probability_status"),
        )
        if not probability_valid:
            exclusions["invalid_behavior_probability"] += 1
            continue
        if behavior_status == "unknown":
            behavior_probability_counts["unknown"] += 1
        else:
            behavior_probability_counts["known"] += 1

        rows.append(
            PolicyRow(
                sample_id=str(sample["sample_id"]),
                trajectory_group_id=str(sample["trajectory_group_id"]),
                category=str(sample.get("category") or ""),
                state=_mapping_or_empty(sample.get("state")),
                candidates=tuple(candidates),
                target_action_id=target_action_id,
                outcome=_mapping_or_empty(sample.get("outcome")),
                source=_source_mapping(sample.get("source")),
                label_mode=label_mode,
                behavior_policy_id=str(sample["behavior_policy_id"]),
                behavior_policy_commit=str(sample["behavior_policy_commit"]),
                behavior_action_probability=behavior_probability,
                behavior_probability_status=behavior_status,
                label_provenance=label_provenance,
            )
        )

    ordered_rows = tuple(_sort_rows(rows))
    if input_sample_count != len(ordered_rows) + sum(exclusions.values()):
        raise AssertionError("dataset input accounting mismatch")
    manifest = _dataset_manifest(
        ordered_rows,
        label_mode=label_mode,
        source_paths=source_paths,
        source_commit=source_commit,
        input_sample_count=input_sample_count,
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

    group_ids = sorted({row.trajectory_group_id for row in _sort_rows(rows)})
    ordered_groups = sorted(
        group_ids,
        key=lambda group_id: (_split_digest(split_seed, group_id), group_id),
    )
    group_count = len(ordered_groups)
    train_count = int(group_count * train_fraction)
    validation_count = int(group_count * validation_fraction)
    groups = {
        "train": tuple(ordered_groups[:train_count]),
        "validation": tuple(ordered_groups[train_count : train_count + validation_count]),
        "test": tuple(ordered_groups[train_count + validation_count :]),
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
    return SplitManifest(assignments=assignments, groups=groups, manifest=manifest)


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
    for row in rows:
        split = splits.assignments.get(row.trajectory_group_id)
        if split in SPLIT_NAMES:
            category_groups[row.category][split].add(row.trajectory_group_id)

    categories = {}
    extra_categories = sorted(set(category_groups) - set(SUPPORTED_CATEGORIES))
    for category in (*SUPPORTED_CATEGORIES, *extra_categories):
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
        if overall_reasons:
            reasons.append("overall_support_blocked")
        categories[category] = {
            "train_trajectory_count": train_count,
            "held_out_trajectory_count": held_out_count,
            "evaluable": not reasons,
            "blocking_reasons": reasons,
        }

    return freeze_value(
        {
            "overall": {
                "trajectory_count": len(group_ids),
                "minimum_trajectory_count": required_trajectories,
                "split_trajectory_counts": split_group_counts,
                "blocked": bool(overall_reasons),
                "blocking_reasons": overall_reasons,
            },
            "categories": categories,
            "outcome_counts": _outcome_counts(rows),
        }
    )


def _eligibility(sample, *, label_mode):
    if sample.get("schema_version") != CANONICAL_SCHEMA_VERSION:
        return "legacy_schema", None, (), {}
    if not _identifier(sample.get("trajectory_group_id")):
        return "missing_trajectory_group", None, (), {}
    if not _identifier(sample.get("behavior_policy_id")) or not _identifier(
        sample.get("behavior_policy_commit")
    ):
        return "missing_behavior_policy", None, (), {}

    candidates = _available_candidates(sample.get("candidate_actions"))
    if not candidates:
        return "missing_candidates", None, (), {}

    if label_mode == "current":
        target_action_id = sample.get("selected_action_id")
        selected_label = _mapping_or_empty(sample.get("current_policy_label"))
    else:
        bottled_label = _mapping_or_empty(sample.get("bottled_label"))
        if bottled_label.get("oracle_mode") != "native_bottled":
            return "bottled_not_native", None, (), {}
        if bottled_label.get("confidence") != "high":
            return "bottled_confidence", None, (), {}
        target_action_id = bottled_label.get("action_id")
        selected_label = bottled_label

    if not _identifier(target_action_id):
        return "missing_target", None, (), {}
    target_action_id = str(target_action_id)
    if target_action_id not in {str(candidate["action_id"]) for candidate in candidates}:
        return "target_not_candidate", None, (), {}
    if not selected_label:
        selected_label = {"action_id": target_action_id}
    return None, target_action_id, candidates, {
        "mode": label_mode,
        "selected_label": selected_label,
    }


def _available_candidates(raw_candidates):
    if not isinstance(raw_candidates, list):
        return ()
    return tuple(candidate for candidate in raw_candidates if _is_canonical_candidate(candidate))


def _is_canonical_candidate(candidate) -> bool:
    return (
        isinstance(candidate, Mapping)
        and _identifier(candidate.get("action_id"))
        and _identifier(candidate.get("kind"))
        and isinstance(candidate.get("label"), str)
        and candidate.get("available") is True
        and isinstance(candidate.get("raw"), Mapping)
    )


def _dataset_manifest(
    rows,
    *,
    label_mode,
    source_paths,
    source_commit,
    input_sample_count,
    schema_versions,
    exclusions,
    behavior_probability_counts,
):
    category_rows = Counter(row.category for row in rows)
    category_groups = defaultdict(set)
    target_action_counts = Counter()
    available_candidate_action_counts = Counter()
    for row in rows:
        category_groups[row.category].add(row.trajectory_group_id)
        target_action_counts[row.target_action_id] += 1
        for candidate in row.candidates:
            available_candidate_action_counts[str(candidate["action_id"])] += 1

    trajectory_counts = {
        category: len(category_groups[category]) for category in sorted(category_groups)
    }
    trajectory_counts["overall"] = len({row.trajectory_group_id for row in rows})
    manifest = {
        "schema_version": DATASET_MANIFEST_VERSION,
        "source_commit": str(source_commit),
        "source_hashes": _source_hashes(source_paths),
        "input_sample_count": input_sample_count,
        "schema_versions": dict(sorted(schema_versions.items())),
        "eligible_row_count": len(rows),
        "exclusions": dict(sorted(exclusions.items())),
        "label_mode": label_mode,
        "label_mode_counts": {
            mode: len(rows) if mode == label_mode else 0 for mode in LABEL_MODES
        },
        "category_counts": dict(sorted(category_rows.items())),
        "trajectory_counts": trajectory_counts,
        "outcome_counts": _outcome_counts(rows),
        "action_support": {
            "target_action_counts": dict(sorted(target_action_counts.items())),
            "available_candidate_action_counts": dict(
                sorted(available_candidate_action_counts.items())
            ),
        },
        "behavior_probability_counts": {
            "known": behavior_probability_counts["known"],
            "unknown": behavior_probability_counts["unknown"],
        },
        "manifest_hash": None,
    }
    manifest["manifest_hash"] = _canonical_hash(manifest)
    return manifest


def _outcome_counts(rows):
    row_join_status = Counter()
    row_victory = Counter()
    grouped_outcomes = defaultdict(list)
    for row in rows:
        join_status = _join_status(row.outcome)
        victory = _victory_status(row.outcome)
        row_join_status[join_status] += 1
        row_victory[victory] += 1
        grouped_outcomes[row.trajectory_group_id].append((join_status, victory))

    trajectory_join_status = Counter()
    trajectory_victory = Counter()
    for outcomes in grouped_outcomes.values():
        trajectory_join_status[_group_status([item[0] for item in outcomes])] += 1
        trajectory_victory[_group_status([item[1] for item in outcomes])] += 1

    return {
        "rows": {
            "join_status": dict(sorted(row_join_status.items())),
            "victory": _victory_counts(row_victory),
        },
        "trajectories": {
            "join_status": dict(sorted(trajectory_join_status.items())),
            "victory": _victory_counts(trajectory_victory),
        },
    }


def _join_status(outcome) -> str:
    value = outcome.get("join_status")
    return str(value) if value else "unknown"


def _victory_status(outcome) -> str:
    if outcome.get("victory") is True:
        return "true"
    if outcome.get("victory") is False:
        return "false"
    return "unknown"


def _group_status(values) -> str:
    values = set(values)
    return next(iter(values)) if len(values) == 1 else "mixed"


def _victory_counts(counts):
    result = {status: counts[status] for status in ("true", "false", "unknown")}
    if counts["mixed"]:
        result["mixed"] = counts["mixed"]
    return dict(sorted(result.items()))


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
    canonical = json.dumps(to_json_value(payload), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _identifier(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _mapping_or_empty(value):
    return dict(value) if isinstance(value, Mapping) else {}


def _source_mapping(value):
    if isinstance(value, Mapping):
        return dict(value)
    return {"value": value}


def _schema_bucket(value) -> str:
    return str(value) if value is not None else "<missing>"


def _normalize_behavior_probability(probability, status):
    if status is None:
        normalized_status = "unknown"
    elif not isinstance(status, str):
        return False, None, "unknown"
    else:
        normalized_status = status.strip().casefold() or "unknown"
    if normalized_status == "unknown":
        return probability is None, None, normalized_status
    if isinstance(probability, bool) or not isinstance(probability, Real):
        return False, None, normalized_status
    try:
        normalized_probability = float(probability)
    except (OverflowError, ValueError, TypeError):
        return False, None, normalized_status
    if not math.isfinite(normalized_probability) or not 0.0 <= normalized_probability <= 1.0:
        return False, None, normalized_status
    return True, normalized_probability, normalized_status
