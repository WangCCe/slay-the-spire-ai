"""Strict read-only audit of action-family counterfactuals on frozen scores."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import os
import stat
import tempfile
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from numbers import Real
from pathlib import Path, PurePosixPath
from typing import Any

import torch

from analysis_scripts import noncombat_action_family_distribution as family_distribution


AUDIT_SCHEMA_VERSION = "noncombat-action-family-counterfactual-audit-v1"
COLLAPSE_AUDIT_SCHEMA_VERSION = "noncombat-state-conditioned-collapse-audit-v1"
TRAINING_ROWS_SCHEMA_VERSION = "noncombat-state-conditioned-training-rows-v1"
EVALUATION_SCHEMA_VERSION = (
    "noncombat-state-conditioned-simulator-learning-paired-evaluation-v1"
)
TERMINAL_VERDICT = "experiment_stopped_at_canary"
TERMINAL_CONCLUSION = "mechanism_narrowed_causality_unresolved"
TARGET_CATEGORIES = ("card_reward", "event", "route", "shop")
TARGET_SOURCE_PATHS = ("evaluation.json", "training_rows.json")

COLLAPSE_AUTHORITY_NAMES = (
    "causal_claim",
    "communication_mod",
    "formal_rl",
    "gameplay",
    "holdout_access",
    "model_fitting",
    "model_loading",
    "native_loading",
    "policy_promotion",
    "qualification",
    "seed_replay",
    "successor_experiment",
    "threshold_change",
    "training",
)
AUDIT_AUTHORITY_NAMES = (
    "deterministic_selection_authority",
    "experiment_execution_authority",
    "formal_rl_authority",
    "gameplay_authority",
    "holdout_access_authority",
    "model_loading_authority",
    "native_loading_authority",
    "policy_promotion_authority",
    "qualification_authority",
    "seed_access_authority",
    "training_authority",
    "training_objective_authority",
)

COLLAPSE_KEYS = {
    "authority",
    "canary",
    "command",
    "conclusion",
    "integrity",
    "schema_version",
    "trajectory",
}
INTEGRITY_KEYS = {
    "checkpoint_count",
    "checkpoint_identity",
    "holdout_accessed",
    "initial_model_sha256",
    "logical_execution_id",
    "source_artifacts",
    "source_root",
    "status",
    "terminal_verdict",
}
DECISION_KEYS = {
    "candidate_scores",
    "candidates",
    "category",
    "decision_id",
    "selected_action_id",
    "state_effect",
}
POLICY_KEYS = {
    "categories",
    "diagnostic_rows",
    "diagnostics",
    "episode_rows",
    "replay_diagnostic_rows",
    "replay_episode_rows",
    "replay_exact",
    "unsupported_episodes",
    "victories",
}
CONCLUSION_KEYS = {
    "bounded_interpretations",
    "prohibited_claims",
    "status",
    "unresolved_hypotheses",
}
TRAJECTORY_KEYS = {
    "aggregate",
    "boundaries",
    "chunk_count",
    "chunks",
    "initial_tensor_gap",
    "pre_update_post_update_alignment",
}
CANARY_KEYS = {"blockers", "initial", "trained", "verdict"}
METRIC_PHASE_KEYS = {"card_reward", "controls", "decision_count", "outcomes"}
TRAINING_CHUNK_KEYS = {
    "categories",
    "chunk_index",
    "diagnostic_rows",
    "entropy_coefficient",
    "episode_end",
    "episode_rows",
    "episode_start",
    "episodes",
    "gradient_norm_after_clip",
    "gradient_norm_before_clip",
    "loss",
    "mean_entropy",
    "mean_episode_return",
    "optimizer_update",
    "pass_index",
    "unsupported_episodes",
    "victories",
}
CANARY_GATE_KEYS = {
    "behavior_gate",
    "blockers",
    "floor_difference_ci",
    "initial_victories",
    "passed",
    "trained_victories",
    "unsupported_rate",
    "verdict",
}
POLICY_DIAGNOSTICS_KEYS = {
    "authority",
    "categories",
    "decision_count",
    "schema_version",
    "state_effect",
}
STATE_EFFECT_KEYS = {
    "category",
    "decision_id",
    "max_abs_relative_score_change",
    "relative_order_changed",
    "zero_state_scores",
}

EXPECTED_DISTRIBUTION_METADATA = {
    "authority": {
        "experiment_execution": False,
        "formal_rl": False,
        "gameplay": False,
        "model_loading": False,
        "native_loading": False,
        "policy_promotion": False,
        "qualification": False,
        "seed_access": False,
        "training": False,
    },
    "candidate_identity_field": "action_id",
    "device": "cpu",
    "distribution_dtype": "float64",
    "entropy_decomposition": "joint=family+expected_conditional",
    "family_aggregation": "max-candidate-score-v1",
    "family_identity_field": "kind",
    "schema_version": "noncombat-action-family-distribution-v1",
    "score_dtype": "float32",
}


class ActionFamilyCounterfactualAuditError(ValueError):
    """Raised when frozen counterfactual evidence is incomplete or inconsistent."""


def _reject_constant(value: str) -> None:
    raise ActionFamilyCounterfactualAuditError(
        f"JSON contains non-finite constant: {value}"
    )


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ActionFamilyCounterfactualAuditError(
                f"JSON contains duplicate key: {key}"
            )
        result[key] = value
    return result


def canonical_json_bytes(value: object) -> bytes:
    try:
        return (
            json.dumps(
                value,
                allow_nan=False,
                ensure_ascii=True,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ActionFamilyCounterfactualAuditError(
            f"value is not canonical JSON: {exc}"
        ) from exc


def _matches_canonical_json_bytes(value: object, raw: bytes) -> bool:
    """Compare canonical encoding incrementally without a second full payload."""
    encoder = json.JSONEncoder(
        allow_nan=False,
        ensure_ascii=True,
        indent=2,
        sort_keys=True,
    )
    offset = 0
    try:
        for chunk in encoder.iterencode(value):
            encoded = chunk.encode("utf-8")
            if not raw.startswith(encoded, offset):
                return False
            offset += len(encoded)
    except (TypeError, ValueError) as exc:
        raise ActionFamilyCounterfactualAuditError(
            f"value is not canonical JSON: {exc}"
        ) from exc
    return len(raw) == offset + 1 and raw[offset : offset + 1] == b"\n"


def _parse_canonical_json(
    raw: bytes, label: str
) -> dict[str, Any]:
    try:
        value = json.loads(
            raw,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ActionFamilyCounterfactualAuditError(
            f"{label} is invalid JSON: {exc}"
        ) from exc
    result = _mapping(value, label)
    if not _matches_canonical_json_bytes(result, raw):
        raise ActionFamilyCounterfactualAuditError(
            f"{label} is not canonical JSON"
        )
    return dict(result)


def _load_canonical_json(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    if _is_reparse_point(path) or not path.is_file():
        raise ActionFamilyCounterfactualAuditError(
            f"{label} must be a regular non-symlink file"
        )
    raw = path.read_bytes()
    return _parse_canonical_json(raw, label), raw


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ActionFamilyCounterfactualAuditError(f"{label} must be a mapping")
    return value


def _sequence(value: Any, label: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ActionFamilyCounterfactualAuditError(f"{label} must be a sequence")
    return value


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        raise ActionFamilyCounterfactualAuditError(
            f"{label} keys mismatch: expected {sorted(expected)}, got {sorted(actual)}"
        )


def _nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ActionFamilyCounterfactualAuditError(
            f"{label} must be a nonempty string"
        )
    return value


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ActionFamilyCounterfactualAuditError(
            f"{label} must be an integer >= {minimum}"
        )
    return value


def _finite_float32(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ActionFamilyCounterfactualAuditError(
            f"{label} must be a finite float32 value"
        )
    try:
        normalized = float(value)
    except (OverflowError, ValueError) as exc:
        raise ActionFamilyCounterfactualAuditError(
            f"{label} must be a finite float32 value"
        ) from exc
    if (
        not math.isfinite(normalized)
        or abs(normalized) > torch.finfo(torch.float32).max
    ):
        raise ActionFamilyCounterfactualAuditError(
            f"{label} must be a finite float32 value"
        )
    return normalized


def _all_false_authority(
    value: Any, names: Sequence[str], label: str
) -> dict[str, bool]:
    authority = _mapping(value, label)
    if set(authority) != set(names) or any(
        authority.get(name) is not False for name in names
    ):
        raise ActionFamilyCounterfactualAuditError(
            f"{label} must be exact all-false authority"
        )
    return {name: False for name in names}


def _normalized_root(path: Path) -> Path:
    if _is_reparse_point(path) or not path.is_dir():
        raise ActionFamilyCounterfactualAuditError(
            "source root must be a regular non-symlink directory"
        )
    return path.resolve(strict=True)


def _is_reparse_point(path: Path) -> bool:
    """Treat Windows junctions and other reparse points like symlinks."""
    try:
        metadata = os.lstat(path)
    except FileNotFoundError:
        return False
    attributes = getattr(metadata, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return path.is_symlink() or bool(reparse_flag and attributes & reparse_flag)


def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(str(left)) == os.path.normcase(str(right))


def _is_within(path: Path, root: Path) -> bool:
    try:
        return os.path.commonpath((str(path), str(root))) == str(root)
    except ValueError:
        return False


def _metric_phase_counts(value: Any, label: str) -> dict[str, int]:
    phase = _mapping(value, label)
    _exact_keys(phase, METRIC_PHASE_KEYS, label)
    controls = _mapping(phase.get("controls"), f"{label}.controls")
    if set(controls) != {"event", "route", "shop"}:
        raise ActionFamilyCounterfactualAuditError(
            f"{label}.controls categories mismatch"
        )
    counts = {
        "card_reward": _integer(
            _mapping(phase.get("card_reward"), f"{label}.card_reward").get(
                "decision_count"
            ),
            f"{label}.card_reward.decision_count",
        )
    }
    for category in ("event", "route", "shop"):
        counts[category] = _integer(
            _mapping(controls[category], f"{label}.controls.{category}").get(
                "decision_count"
            ),
            f"{label}.controls.{category}.decision_count",
        )
    expected_total = sum(counts.values())
    actual_total = _integer(phase.get("decision_count"), f"{label}.decision_count")
    if actual_total != expected_total:
        raise ActionFamilyCounterfactualAuditError(
            f"{label} count mismatch: {actual_total} != {expected_total}"
        )
    return counts


def _validate_collapse_audit(
    collapse: Mapping[str, Any], source_root: Path
) -> tuple[dict[str, dict[str, int]], dict[str, dict[str, Any]], int]:
    _exact_keys(collapse, COLLAPSE_KEYS, "collapse audit")
    if collapse.get("schema_version") != COLLAPSE_AUDIT_SCHEMA_VERSION:
        raise ActionFamilyCounterfactualAuditError("collapse audit schema mismatch")
    _all_false_authority(
        collapse.get("authority"),
        COLLAPSE_AUTHORITY_NAMES,
        "collapse audit authority",
    )

    integrity = _mapping(collapse.get("integrity"), "collapse audit.integrity")
    _exact_keys(integrity, INTEGRITY_KEYS, "collapse audit.integrity")
    if integrity.get("status") != "valid":
        raise ActionFamilyCounterfactualAuditError(
            "collapse audit terminal status mismatch"
        )
    if integrity.get("terminal_verdict") != TERMINAL_VERDICT:
        raise ActionFamilyCounterfactualAuditError(
            "collapse audit terminal verdict mismatch"
        )
    if integrity.get("holdout_accessed") is not False:
        raise ActionFamilyCounterfactualAuditError(
            "collapse audit indicates holdout access"
        )
    recorded_root = Path(
        _nonempty_string(integrity.get("source_root"), "collapse audit source_root")
    ).resolve(strict=False)
    if not _same_path(recorded_root, source_root):
        raise ActionFamilyCounterfactualAuditError(
            "collapse audit source_root does not match explicit source root"
        )

    conclusion = _mapping(collapse.get("conclusion"), "collapse audit.conclusion")
    _exact_keys(conclusion, CONCLUSION_KEYS, "collapse audit.conclusion")
    if conclusion.get("status") != TERMINAL_CONCLUSION:
        raise ActionFamilyCounterfactualAuditError(
            "collapse audit conclusion status mismatch"
        )

    trajectory = _mapping(collapse.get("trajectory"), "collapse audit.trajectory")
    _exact_keys(trajectory, TRAJECTORY_KEYS, "collapse audit.trajectory")
    training_counts = _metric_phase_counts(
        _mapping(trajectory.get("aggregate"), "collapse audit.trajectory.aggregate"),
        "collapse audit.trajectory.aggregate",
    )
    chunk_count = _integer(
        trajectory.get("chunk_count"), "collapse audit.trajectory.chunk_count"
    )
    canary = _mapping(collapse.get("canary"), "collapse audit.canary")
    _exact_keys(canary, CANARY_KEYS, "collapse audit.canary")
    if canary.get("verdict") != TERMINAL_VERDICT:
        raise ActionFamilyCounterfactualAuditError(
            "collapse audit canary verdict mismatch"
        )
    expected_counts = {
        "initial_canary": _metric_phase_counts(
            canary.get("initial"), "collapse audit.canary.initial"
        ),
        "trained_canary": _metric_phase_counts(
            canary.get("trained"), "collapse audit.canary.trained"
        ),
        "training": training_counts,
    }

    source_artifacts = _sequence(
        integrity.get("source_artifacts"), "collapse audit source_artifacts"
    )
    identities: dict[str, dict[str, Any]] = {}
    for index, raw_identity in enumerate(source_artifacts):
        identity = _mapping(
            raw_identity, f"collapse audit source_artifacts[{index}]"
        )
        _exact_keys(
            identity,
            {"path", "sha256", "size_bytes"},
            f"collapse audit source_artifacts[{index}]",
        )
        relative_path = _nonempty_string(
            identity.get("path"),
            f"collapse audit source_artifacts[{index}].path",
        )
        if relative_path not in TARGET_SOURCE_PATHS:
            continue
        if relative_path in identities:
            raise ActionFamilyCounterfactualAuditError(
                f"duplicate source identity: {relative_path}"
            )
        digest = _nonempty_string(
            identity.get("sha256"),
            f"collapse audit source_artifacts[{index}].sha256",
        )
        if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
            raise ActionFamilyCounterfactualAuditError(
                f"invalid source sha256: {relative_path}"
            )
        identities[relative_path] = {
            "path": relative_path,
            "sha256": digest,
            "size_bytes": _integer(
                identity.get("size_bytes"),
                f"collapse audit source_artifacts[{index}].size_bytes",
            ),
        }
    if set(identities) != set(TARGET_SOURCE_PATHS):
        raise ActionFamilyCounterfactualAuditError(
            "collapse audit does not bind the exact scored-row source set"
        )
    return expected_counts, identities, chunk_count


def _load_bound_source(
    source_root: Path, identity: Mapping[str, Any]
) -> dict[str, Any]:
    relative_text = str(identity["path"])
    relative = PurePosixPath(relative_text)
    if (
        relative.is_absolute()
        or relative.parts != (relative_text,)
        or relative_text not in TARGET_SOURCE_PATHS
    ):
        raise ActionFamilyCounterfactualAuditError(
            f"source path is not canonical: {relative_text}"
        )
    path = source_root / relative_text
    if _is_reparse_point(path) or not path.is_file():
        raise ActionFamilyCounterfactualAuditError(
            f"source artifact must be a regular non-symlink file: {relative_text}"
        )
    resolved = path.resolve(strict=True)
    if not _is_within(resolved, source_root) or not _same_path(
        resolved.parent, source_root
    ):
        raise ActionFamilyCounterfactualAuditError(
            f"source artifact escapes source root: {relative_text}"
        )
    raw = path.read_bytes()
    if len(raw) != identity["size_bytes"] or hashlib.sha256(raw).hexdigest() != identity[
        "sha256"
    ]:
        raise ActionFamilyCounterfactualAuditError(
            f"source identity mismatch: {relative_text}"
        )
    return _parse_canonical_json(raw, relative_text)


def _validated_categories(value: Any, label: str) -> None:
    categories = _sequence(value, label)
    if len(categories) != len(TARGET_CATEGORIES) or set(categories) != set(
        TARGET_CATEGORIES
    ):
        raise ActionFamilyCounterfactualAuditError(
            f"{label} categories mismatch"
        )


def _validated_decision(value: Any, label: str) -> dict[str, Any]:
    row = _mapping(value, label)
    _exact_keys(row, DECISION_KEYS, label)
    category = _nonempty_string(row.get("category"), f"{label}.category")
    if category not in TARGET_CATEGORIES:
        raise ActionFamilyCounterfactualAuditError(
            f"{label}.category is unsupported: {category}"
        )
    decision_id = _nonempty_string(
        row.get("decision_id"), f"{label}.decision_id"
    )
    candidates = _sequence(row.get("candidates"), f"{label}.candidates")
    if not candidates:
        raise ActionFamilyCounterfactualAuditError(
            f"{label}.candidates must be nonempty"
        )
    normalized_candidates: list[dict[str, str]] = []
    action_ids: list[str] = []
    seen: set[str] = set()
    for index, raw_candidate in enumerate(candidates):
        candidate_label = f"{label}.candidates[{index}]"
        candidate = _mapping(raw_candidate, candidate_label)
        _exact_keys(candidate, {"action_id", "kind"}, candidate_label)
        action_id = _nonempty_string(
            candidate.get("action_id"), f"{candidate_label}.action_id"
        )
        if action_id in seen:
            raise ActionFamilyCounterfactualAuditError(
                f"{label} duplicate candidate action_id: {action_id}"
            )
        kind = _nonempty_string(candidate.get("kind"), f"{candidate_label}.kind")
        seen.add(action_id)
        action_ids.append(action_id)
        normalized_candidates.append({"action_id": action_id, "kind": kind})

    candidate_scores = _mapping(
        row.get("candidate_scores"), f"{label}.candidate_scores"
    )
    if set(candidate_scores) != set(action_ids):
        raise ActionFamilyCounterfactualAuditError(
            f"{label} candidate score identities do not align"
        )
    scores = [
        _finite_float32(
            candidate_scores[action_id],
            f"{label}.candidate_scores[{action_id!r}]",
        )
        for action_id in action_ids
    ]
    selected_action_id = _nonempty_string(
        row.get("selected_action_id"), f"{label}.selected_action_id"
    )
    if selected_action_id not in seen:
        raise ActionFamilyCounterfactualAuditError(
            f"{label}.selected_action_id is not a candidate"
        )
    state_effect = _mapping(row.get("state_effect"), f"{label}.state_effect")
    _exact_keys(state_effect, STATE_EFFECT_KEYS, f"{label}.state_effect")
    return {
        "action_ids": tuple(action_ids),
        "candidates": tuple(normalized_candidates),
        "category": category,
        "decision_id": decision_id,
        "scores": tuple(scores),
        "selected_action_id": selected_action_id,
    }


def _training_row_items(
    training: Mapping[str, Any], expected_chunk_count: int
) -> Iterable[tuple[Any, str]]:
    _exact_keys(
        training,
        {"chunks", "episode_count", "schema_version"},
        "training_rows.json",
    )
    if training.get("schema_version") != TRAINING_ROWS_SCHEMA_VERSION:
        raise ActionFamilyCounterfactualAuditError("training rows schema mismatch")
    _integer(training.get("episode_count"), "training_rows.json.episode_count")
    chunks = _sequence(training.get("chunks"), "training_rows.json.chunks")
    if len(chunks) != expected_chunk_count:
        raise ActionFamilyCounterfactualAuditError(
            "training_rows.json chunk count mismatch"
        )
    for chunk_index, raw_chunk in enumerate(chunks):
        chunk = _mapping(raw_chunk, f"training_rows.json.chunks[{chunk_index}]")
        _exact_keys(
            chunk,
            TRAINING_CHUNK_KEYS,
            f"training_rows.json.chunks[{chunk_index}]",
        )
        if _integer(
            chunk.get("chunk_index"),
            f"training_rows.json.chunks[{chunk_index}].chunk_index",
        ) != chunk_index:
            raise ActionFamilyCounterfactualAuditError(
                "training_rows.json chunk indices are not contiguous"
            )
        _validated_categories(
            chunk.get("categories"),
            f"training_rows.json.chunks[{chunk_index}].categories",
        )
        rows = _sequence(
            chunk.get("diagnostic_rows"),
            f"training_rows.json.chunks[{chunk_index}].diagnostic_rows",
        )
        for row_index, row in enumerate(rows):
            yield row, (
                f"training_rows.json.chunks[{chunk_index}]"
                f".diagnostic_rows[{row_index}]"
            )


def _evaluation_policy_rows(
    policy: Any, label: str
) -> Sequence[Any]:
    value = _mapping(policy, label)
    _exact_keys(value, POLICY_KEYS, label)
    _validated_categories(value.get("categories"), f"{label}.categories")
    if value.get("replay_exact") is not True:
        raise ActionFamilyCounterfactualAuditError(f"{label}.replay_exact mismatch")
    rows = _sequence(value.get("diagnostic_rows"), f"{label}.diagnostic_rows")
    diagnostics = _mapping(value.get("diagnostics"), f"{label}.diagnostics")
    _exact_keys(diagnostics, POLICY_DIAGNOSTICS_KEYS, f"{label}.diagnostics")
    if "decision_count" in diagnostics and _integer(
        diagnostics.get("decision_count"), f"{label}.diagnostics.decision_count"
    ) != len(rows):
        raise ActionFamilyCounterfactualAuditError(
            f"{label}.diagnostics count mismatch"
        )
    _sequence(value.get("replay_diagnostic_rows"), f"{label}.replay_diagnostic_rows")
    _sequence(value.get("replay_episode_rows"), f"{label}.replay_episode_rows")
    return rows


def _evaluation_rows(
    evaluation: Mapping[str, Any]
) -> tuple[Sequence[Any], Sequence[Any]]:
    _exact_keys(
        evaluation,
        {"canary", "canary_gate", "holdout", "verdict"},
        "evaluation.json",
    )
    if evaluation.get("verdict") != TERMINAL_VERDICT:
        raise ActionFamilyCounterfactualAuditError("evaluation verdict mismatch")
    holdout = _mapping(evaluation.get("holdout"), "evaluation.json.holdout")
    _exact_keys(holdout, {"accessed", "episode_count"}, "evaluation.json.holdout")
    if holdout.get("accessed") is not False or _integer(
        holdout.get("episode_count"), "evaluation.json.holdout.episode_count"
    ) != 0:
        raise ActionFamilyCounterfactualAuditError(
            "evaluation indicates holdout access"
        )
    gate = _mapping(evaluation.get("canary_gate"), "evaluation.json.canary_gate")
    _exact_keys(gate, CANARY_GATE_KEYS, "evaluation.json.canary_gate")
    if gate.get("verdict") != TERMINAL_VERDICT:
        raise ActionFamilyCounterfactualAuditError(
            "evaluation canary gate verdict mismatch"
        )
    canary = _mapping(evaluation.get("canary"), "evaluation.json.canary")
    _exact_keys(
        canary,
        {
            "cohort",
            "floor_difference_ci",
            "initial",
            "paired_rows",
            "schema_version",
            "seeds",
            "trained",
            "unsupported_rate",
            "unsupported_rate_denominator",
        },
        "evaluation.json.canary",
    )
    if (
        canary.get("cohort") != "canary"
        or canary.get("schema_version") != EVALUATION_SCHEMA_VERSION
    ):
        raise ActionFamilyCounterfactualAuditError(
            "evaluation canary identity mismatch"
        )
    return (
        _evaluation_policy_rows(
            canary.get("initial"), "evaluation.json.canary.initial"
        ),
        _evaluation_policy_rows(
            canary.get("trained"), "evaluation.json.canary.trained"
        ),
    )


def _unique_argmax(values: Sequence[float]) -> tuple[int | None, int]:
    maximum = max(values)
    indices = [index for index, value in enumerate(values) if value == maximum]
    return (indices[0] if len(indices) == 1 else None, len(indices))


def _clean_float(value: float) -> float:
    if abs(value) < 1e-15:
        return 0.0
    return float(value)


def _counter_dict(counter: Counter[str]) -> dict[str, int]:
    return {name: counter[name] for name in sorted(counter)}


@dataclass
class _CategoryAccumulator:
    decision_count: int = 0
    candidate_count: int = 0
    families: set[str] = field(default_factory=set)
    family_opportunities: Counter[str] = field(default_factory=Counter)
    candidate_occurrences: Counter[str] = field(default_factory=Counter)
    flat_mass_sums: defaultdict[str, float] = field(
        default_factory=lambda: defaultdict(float)
    )
    hierarchical_mass_sums: defaultdict[str, float] = field(
        default_factory=lambda: defaultdict(float)
    )
    flat_entropy_sum: float = 0.0
    family_entropy_sum: float = 0.0
    conditional_entropy_sum: float = 0.0
    joint_entropy_sum: float = 0.0
    one_family_count: int = 0
    multi_family_count: int = 0
    raw_score_tie_count: int = 0
    joint_probability_tie_count: int = 0
    comparable_count: int = 0
    transition_count: int = 0
    transitions: Counter[str] = field(default_factory=Counter)
    score_kinds: Counter[str] = field(default_factory=Counter)
    joint_kinds: Counter[str] = field(default_factory=Counter)
    selected_kinds: Counter[str] = field(default_factory=Counter)
    two_stage_comparable_count: int = 0
    two_stage_equivalent_count: int = 0
    two_stage_mismatch_count: int = 0
    max_probability_sum_error: float = 0.0
    max_entropy_decomposition_error: float = 0.0
    max_one_family_fallback_error: float = 0.0

    def add(self, row: Mapping[str, Any], label: str) -> None:
        candidates = row["candidates"]
        score_tensor = torch.tensor(row["scores"], dtype=torch.float32, device="cpu")
        try:
            distribution = family_distribution.build_action_family_distribution(
                score_tensor, candidates
            )
        except family_distribution.ActionFamilyDistributionError as exc:
            raise ActionFamilyCounterfactualAuditError(
                f"{label} distribution failed: {exc}"
            ) from exc
        action_ids = tuple(row["action_ids"])
        kinds = tuple(candidate["kind"] for candidate in candidates)
        if (
            distribution.action_ids != action_ids
            or distribution.candidate_families != kinds
        ):
            raise ActionFamilyCounterfactualAuditError(
                f"{label} distribution identity drift"
            )

        flat_log_probabilities = torch.log_softmax(
            score_tensor.to(torch.float64), dim=0
        )
        flat_probabilities = flat_log_probabilities.exp()
        candidate_probabilities = distribution.candidate_probabilities
        flat_values = [float(value) for value in flat_probabilities.tolist()]
        joint_values = [float(value) for value in candidate_probabilities.tolist()]
        score_values = [float(value) for value in score_tensor.tolist()]
        family_values = [float(value) for value in distribution.family_logits.tolist()]
        flat_family_mass: defaultdict[str, float] = defaultdict(float)
        for kind, probability in zip(kinds, flat_values, strict=True):
            flat_family_mass[kind] += probability
        hierarchical_family_mass = {
            family: float(distribution.family_probabilities[index].item())
            for index, family in enumerate(distribution.family_order)
        }

        probability_error = max(
            abs(sum(flat_values) - 1.0),
            abs(sum(joint_values) - 1.0),
            abs(sum(hierarchical_family_mass.values()) - 1.0),
        )
        entropy_error = abs(
            float(distribution.joint_entropy.item())
            - float(distribution.family_entropy.item())
            - float(distribution.conditional_entropy.item())
        )
        if probability_error > 1e-10 or entropy_error > 1e-10:
            raise ActionFamilyCounterfactualAuditError(
                f"{label} distribution invariant mismatch"
            )

        family_set = set(kinds)
        one_family_error = 0.0
        if len(family_set) == 1:
            one_family_error = max(
                abs(flat - joint)
                for flat, joint in zip(flat_values, joint_values, strict=True)
            )
            if one_family_error > 1e-12 or abs(
                float(distribution.family_entropy.item())
            ) > 1e-12:
                raise ActionFamilyCounterfactualAuditError(
                    f"{label} one-family fallback mismatch"
                )

        self.decision_count += 1
        self.candidate_count += len(candidates)
        self.families.update(family_set)
        for family in family_set:
            self.family_opportunities[family] += 1
            self.flat_mass_sums[family] += flat_family_mass[family]
            self.hierarchical_mass_sums[family] += hierarchical_family_mass[family]
        self.candidate_occurrences.update(kinds)
        flat_entropy = -(
            flat_probabilities * flat_log_probabilities
        ).sum()
        if not torch.isfinite(flat_entropy).item():
            raise ActionFamilyCounterfactualAuditError(
                f"{label} flat entropy must remain finite"
            )
        self.flat_entropy_sum += float(flat_entropy.item())
        self.family_entropy_sum += float(distribution.family_entropy.item())
        self.conditional_entropy_sum += float(distribution.conditional_entropy.item())
        self.joint_entropy_sum += float(distribution.joint_entropy.item())
        self.one_family_count += int(len(family_set) == 1)
        self.multi_family_count += int(len(family_set) > 1)
        self.max_probability_sum_error = max(
            self.max_probability_sum_error, probability_error
        )
        self.max_entropy_decomposition_error = max(
            self.max_entropy_decomposition_error, entropy_error
        )
        self.max_one_family_fallback_error = max(
            self.max_one_family_fallback_error, one_family_error
        )

        score_index, score_ties = _unique_argmax(score_values)
        joint_index, joint_ties = _unique_argmax(joint_values)
        self.raw_score_tie_count += int(score_ties > 1)
        self.joint_probability_tie_count += int(joint_ties > 1)
        if score_index is not None:
            self.score_kinds[kinds[score_index]] += 1
        if joint_index is not None:
            self.joint_kinds[kinds[joint_index]] += 1
        selected_index = action_ids.index(row["selected_action_id"])
        self.selected_kinds[kinds[selected_index]] += 1
        if score_index is not None and joint_index is not None:
            self.comparable_count += 1
            if score_index != joint_index:
                self.transition_count += 1
                self.transitions[f"{kinds[score_index]}->{kinds[joint_index]}"] += 1

        if score_index is not None:
            family_index, family_ties = _unique_argmax(family_values)
            two_stage_index: int | None = None
            if family_index is not None and family_ties == 1:
                chosen_family = distribution.family_order[family_index]
                family_candidate_indices = [
                    index for index, kind in enumerate(kinds) if kind == chosen_family
                ]
                family_scores = [score_values[index] for index in family_candidate_indices]
                within_index, within_ties = _unique_argmax(family_scores)
                if within_index is not None and within_ties == 1:
                    two_stage_index = family_candidate_indices[within_index]
            self.two_stage_comparable_count += int(two_stage_index is not None)
            self.two_stage_equivalent_count += int(two_stage_index == score_index)
            self.two_stage_mismatch_count += int(
                two_stage_index is not None and two_stage_index != score_index
            )

    def finish(self) -> dict[str, Any]:
        if self.decision_count == 0:
            raise ActionFamilyCounterfactualAuditError(
                "counterfactual category contains no decisions"
            )
        family_mass = {}
        for family in sorted(self.families):
            count = self.family_opportunities[family]
            flat_mean = self.flat_mass_sums[family] / count
            hierarchical_mean = self.hierarchical_mass_sums[family] / count
            family_mass[family] = {
                "flat_mean_when_present": _clean_float(flat_mean),
                "hierarchical_mean_when_present": _clean_float(hierarchical_mean),
                "mean_delta_when_present": _clean_float(
                    hierarchical_mean - flat_mean
                ),
                "opportunity_count": count,
            }
        rate = (
            self.transition_count / self.comparable_count
            if self.comparable_count
            else None
        )
        return {
            "argmax": {
                "comparable_count": self.comparable_count,
                "joint_kind_counts": _counter_dict(self.joint_kinds),
                "joint_probability_tie_count": self.joint_probability_tie_count,
                "raw_score_tie_count": self.raw_score_tie_count,
                "score_kind_counts": _counter_dict(self.score_kinds),
                "selected_kind_counts": _counter_dict(self.selected_kinds),
                "transition_count": self.transition_count,
                "transition_counts": _counter_dict(self.transitions),
                "transition_rate": _clean_float(rate) if rate is not None else None,
                "two_stage_comparable_count": self.two_stage_comparable_count,
                "two_stage_equivalent_count": self.two_stage_equivalent_count,
                "two_stage_mismatch_count": self.two_stage_mismatch_count,
            },
            "candidate_count": self.candidate_count,
            "candidate_kind_occurrences": _counter_dict(self.candidate_occurrences),
            "decision_count": self.decision_count,
            "entropy": {
                "conditional_mean": _clean_float(
                    self.conditional_entropy_sum / self.decision_count
                ),
                "family_mean": _clean_float(
                    self.family_entropy_sum / self.decision_count
                ),
                "flat_candidate_mean": _clean_float(
                    self.flat_entropy_sum / self.decision_count
                ),
                "joint_mean": _clean_float(
                    self.joint_entropy_sum / self.decision_count
                ),
            },
            "families": sorted(self.families),
            "family_mass": family_mass,
            "family_opportunity_counts": _counter_dict(self.family_opportunities),
            "invariants": {
                "entropy_decomposition_max_abs_error": _clean_float(
                    self.max_entropy_decomposition_error
                ),
                "one_family_fallback_max_abs_error": _clean_float(
                    self.max_one_family_fallback_error
                ),
                "probability_sum_max_abs_error": _clean_float(
                    self.max_probability_sum_error
                ),
            },
            "row_shape": {
                "multi_family_count": self.multi_family_count,
                "one_family_count": self.one_family_count,
            },
        }


def _analyze_phase(
    rows: Iterable[tuple[Any, str]],
    expected_counts: Mapping[str, int],
    phase_name: str,
) -> dict[str, Any]:
    accumulators = {category: _CategoryAccumulator() for category in TARGET_CATEGORIES}
    seen_decision_ids: set[str] = set()
    actual_counts: Counter[str] = Counter()
    with torch.no_grad():
        for raw_row, label in rows:
            row = _validated_decision(raw_row, label)
            decision_id = row["decision_id"]
            if decision_id in seen_decision_ids:
                raise ActionFamilyCounterfactualAuditError(
                    f"{phase_name} duplicate decision_id: {decision_id}"
                )
            seen_decision_ids.add(decision_id)
            category = row["category"]
            accumulators[category].add(row, label)
            actual_counts[category] += 1
    for category in TARGET_CATEGORIES:
        if actual_counts[category] != expected_counts[category]:
            raise ActionFamilyCounterfactualAuditError(
                f"{phase_name}.{category} count mismatch: "
                f"{actual_counts[category]} != {expected_counts[category]}"
            )
    return {
        "categories": {
            category: accumulators[category].finish()
            for category in TARGET_CATEGORIES
        },
        "decision_count": sum(actual_counts.values()),
    }


def _authority() -> dict[str, bool]:
    return {name: False for name in AUDIT_AUTHORITY_NAMES}


def audit_counterfactuals(
    collapse_audit_path: Path | str, source_root: Path | str
) -> dict[str, Any]:
    """Validate frozen inputs and recompute bounded action-family diagnostics."""
    collapse_path = Path(collapse_audit_path)
    if _is_reparse_point(collapse_path) or not collapse_path.is_file():
        raise ActionFamilyCounterfactualAuditError(
            "collapse audit must be a regular non-symlink file"
        )
    collapse_path = collapse_path.resolve(strict=True)
    root = _normalized_root(Path(source_root))
    collapse, collapse_raw = _load_canonical_json(collapse_path, "collapse audit")
    expected_counts, identities, chunk_count = _validate_collapse_audit(
        collapse, root
    )
    metadata = family_distribution.distribution_metadata()
    if metadata != EXPECTED_DISTRIBUTION_METADATA:
        raise ActionFamilyCounterfactualAuditError(
            "action-family distribution metadata mismatch"
        )

    training = _load_bound_source(root, identities["training_rows.json"])
    training_phase = _analyze_phase(
        _training_row_items(training, chunk_count),
        expected_counts["training"],
        "training",
    )
    del training
    gc.collect()

    evaluation = _load_bound_source(root, identities["evaluation.json"])
    initial_rows, trained_rows = _evaluation_rows(evaluation)
    phases = {
        "training": training_phase,
        "initial_canary": _analyze_phase(
            (
                (row, f"evaluation.json.canary.initial.diagnostic_rows[{index}]")
                for index, row in enumerate(initial_rows)
            ),
            expected_counts["initial_canary"],
            "initial_canary",
        ),
        "trained_canary": _analyze_phase(
            (
                (row, f"evaluation.json.canary.trained.diagnostic_rows[{index}]")
                for index, row in enumerate(trained_rows)
            ),
            expected_counts["trained_canary"],
            "trained_canary",
        ),
    }
    result = {
        "authority": _authority(),
        "conclusion": {
            "bounded_interpretations": [
                "joint_candidate_argmax_is_not_a_neutral_greedy_projection",
                "family_only_entropy_is_incomplete_for_single_family_categories",
                "max_pooling_reallocates_shop_and_card_reward_mass",
            ],
            "prohibited_claims": [
                "deterministic_selection_rule",
                "entropy_coefficient_choice",
                "formal_rl_readiness",
                "intervention_effectiveness",
                "policy_promotion",
                "successor_experiment_authority",
            ],
            "status": "counterfactual_measured_selection_semantics_unresolved",
        },
        "distribution_metadata": metadata,
        "inputs": {
            "collapse_audit": {
                "file_name": collapse_path.name,
                "sha256": hashlib.sha256(collapse_raw).hexdigest(),
                "size_bytes": len(collapse_raw),
            },
            "source_artifacts": [identities[path] for path in TARGET_SOURCE_PATHS],
            "terminal_conclusion": TERMINAL_CONCLUSION,
            "terminal_verdict": TERMINAL_VERDICT,
        },
        "phases": phases,
        "schema_version": AUDIT_SCHEMA_VERSION,
    }
    return json.loads(canonical_json_bytes(result).decode("utf-8"))


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def render_markdown(result: Mapping[str, Any]) -> str:
    """Render deterministic human-readable counterfactual evidence."""
    lines = [
        "# Non-Combat Action-Family Counterfactual Audit",
        "",
        "## Evidence Boundary",
        "",
        "This report recomputes distributions from hash-bound frozen scores. It",
        "does not open checkpoints, replay seeds, inspect holdout rows, construct",
        "an environment, load a production model, train, select, or promote a policy.",
        "",
        "## Inputs",
        "",
        "| Artifact | Bytes | SHA-256 |",
        "| --- | ---: | --- |",
    ]
    collapse = result["inputs"]["collapse_audit"]
    lines.append(
        f"| `{collapse['file_name']}` | {collapse['size_bytes']} | `{collapse['sha256']}` |"
    )
    for identity in result["inputs"]["source_artifacts"]:
        lines.append(
            f"| `{identity['path']}` | {identity['size_bytes']} | `{identity['sha256']}` |"
        )
    lines.extend(
        [
            "",
            "## Counterfactual Summary",
            "",
            "| Phase | Category | Rows | Multi-family | Score-to-joint changes | Rate | Family H | Conditional H | Joint H |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for phase_name in ("training", "initial_canary", "trained_canary"):
        phase = result["phases"][phase_name]
        for category in TARGET_CATEGORIES:
            metrics = phase["categories"][category]
            argmax = metrics["argmax"]
            entropy = metrics["entropy"]
            lines.append(
                "| "
                f"{phase_name} | {category} | {metrics['decision_count']} | "
                f"{metrics['row_shape']['multi_family_count']} | "
                f"{argmax['transition_count']} | {_fmt(argmax['transition_rate'])} | "
                f"{_fmt(entropy['family_mean'])} | "
                f"{_fmt(entropy['conditional_mean'])} | "
                f"{_fmt(entropy['joint_mean'])} |"
            )
    lines.extend(
        [
            "",
            "## Family Mass",
            "",
            "Means are conditioned on the family being available in the row.",
            "",
            "| Phase | Category | Family | Opportunities | Flat | Hierarchical | Delta |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for phase_name in ("training", "initial_canary", "trained_canary"):
        for category in TARGET_CATEGORIES:
            masses = result["phases"][phase_name]["categories"][category][
                "family_mass"
            ]
            for family in sorted(masses):
                values = masses[family]
                lines.append(
                    "| "
                    f"{phase_name} | {category} | {family} | "
                    f"{values['opportunity_count']} | "
                    f"{_fmt(values['flat_mean_when_present'])} | "
                    f"{_fmt(values['hierarchical_mean_when_present'])} | "
                    f"{_fmt(values['mean_delta_when_present'])} |"
                )
    lines.extend(
        [
            "",
            "## Bounded Conclusions",
            "",
            "- Joint candidate probability is not a neutral deterministic projection",
            "  of max-pooled family scores; score and joint argmax are reported separately.",
            "- Event and route rows have one family, so family entropy alone provides no",
            "  regularization there; conditional entropy remains a distinct quantity.",
            "- The measured mass reallocations do not select a training objective, entropy",
            "  coefficient, deterministic policy, or successor experiment.",
            "",
            "## Authority",
            "",
        ]
    )
    lines.extend(
        f"- {name}: false" for name in sorted(result["authority"])
    )
    lines.append("")
    return "\n".join(lines)


def _validate_output_paths(
    collapse_path: Path,
    source_root: Path,
    output_json: Path,
    output_markdown: Path,
) -> tuple[Path, Path]:
    resolved_outputs: list[Path] = []
    for path, label in (
        (output_json, "JSON output"),
        (output_markdown, "Markdown output"),
    ):
        if _is_reparse_point(path):
            raise ActionFamilyCounterfactualAuditError(
                f"{label} must not be a symlink"
            )
        resolved = path.resolve(strict=False)
        if _is_within(resolved, source_root):
            raise ActionFamilyCounterfactualAuditError(
                f"{label} must remain outside source root"
            )
        if _same_path(resolved, collapse_path):
            raise ActionFamilyCounterfactualAuditError(
                f"{label} must not replace the collapse audit"
            )
        resolved_outputs.append(resolved)
    if _same_path(resolved_outputs[0], resolved_outputs[1]):
        raise ActionFamilyCounterfactualAuditError(
            "JSON and Markdown outputs must be distinct"
        )
    return resolved_outputs[0], resolved_outputs[1]


def _stage_payload(path: Path, payload: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="wb", prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, delete=False
    ) as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
        return Path(stream.name)


def _write_pair_with_rollback(
    output_json: Path,
    json_payload: bytes,
    output_markdown: Path,
    markdown_payload: bytes,
) -> None:
    staged: list[Path] = []
    backups: dict[Path, Path | None] = {}
    installed: list[Path] = []
    preserve_backups = False
    try:
        staged_json = _stage_payload(output_json, json_payload)
        staged.append(staged_json)
        staged_markdown = _stage_payload(output_markdown, markdown_payload)
        staged.append(staged_markdown)
        for output in (output_json, output_markdown):
            backups[output] = (
                _stage_payload(output, output.read_bytes())
                if output.exists()
                else None
            )
        os.replace(staged_json, output_json)
        installed.append(output_json)
        os.replace(staged_markdown, output_markdown)
        installed.append(output_markdown)
    except BaseException as exc:
        rollback_errors: list[OSError] = []
        for output in reversed(installed):
            backup = backups.get(output)
            try:
                if backup is None:
                    output.unlink(missing_ok=True)
                else:
                    os.replace(backup, output)
                    backups[output] = None
            except OSError as rollback_error:
                rollback_errors.append(rollback_error)
        if rollback_errors:
            preserve_backups = True
            recovery_paths = ", ".join(
                str(path) for path in backups.values() if path is not None
            )
            raise ActionFamilyCounterfactualAuditError(
                "report publication failed and rollback was incomplete; "
                f"recovery backups preserved: {recovery_paths}"
            ) from exc
        raise
    finally:
        for path in staged:
            path.unlink(missing_ok=True)
        if not preserve_backups:
            for path in backups.values():
                if path is not None:
                    path.unlink(missing_ok=True)


def publish_counterfactual_audit(
    collapse_audit_path: Path | str,
    source_root: Path | str,
    *,
    output_json: Path | str,
    output_markdown: Path | str,
) -> dict[str, Any]:
    """Publish canonical JSON and deterministic Markdown after full validation."""
    collapse_path = Path(collapse_audit_path).resolve(strict=False)
    root = _normalized_root(Path(source_root))
    resolved_json, resolved_markdown = _validate_output_paths(
        collapse_path,
        root,
        Path(output_json),
        Path(output_markdown),
    )
    result = audit_counterfactuals(collapse_audit_path, root)
    json_payload = canonical_json_bytes(result)
    markdown_payload = render_markdown(result).encode("utf-8")
    _write_pair_with_rollback(
        resolved_json,
        json_payload,
        resolved_markdown,
        markdown_payload,
    )
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit frozen non-combat action-family counterfactuals."
    )
    parser.add_argument("--collapse-audit", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-markdown", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result = publish_counterfactual_audit(
        args.collapse_audit,
        args.source_root,
        output_json=args.output_json,
        output_markdown=args.output_markdown,
    )
    print(
        json.dumps(
            {
                "decision_count": sum(
                    phase["decision_count"] for phase in result["phases"].values()
                ),
                "schema_version": result["schema_version"],
                "status": result["conclusion"]["status"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
