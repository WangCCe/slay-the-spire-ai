"""Validate and export confirmed known-propensity non-combat evidence."""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from analysis_scripts.noncombat_rl_decision_loop import attach_live_outcomes
from spirecomm.ai.noncombat_exploration import (
    MANIFEST_SCHEMA_VERSION,
    ActionProbability,
    ExplorationCandidate,
    ExplorationConfig,
    ExplorationRecordStore,
    ExplorationSelection,
    NonCombatProposal,
    parse_exploration_config,
    verify_exploration_selection,
)


CANONICAL_EXPLORATION_SCHEMA_VERSION = "noncombat-rl-decision-v3"
_LEGACY_SCHEMA_VERSIONS = frozenset(
    {"noncombat-rl-decision-v1", "noncombat-rl-decision-v2"}
)
_REQUIRED_CATEGORIES = ("card_reward", "shop")
_MIN_UNIQUE_TRAJECTORIES = 25
_MIN_ARM_SUPPORT = 5


class ExplorationEvidenceError(ValueError):
    """Raised when a manifest or trace cannot support independent replay."""


@dataclass(frozen=True)
class ExplorationExportResult:
    samples: tuple[dict[str, Any], ...]
    exclusions: tuple[dict[str, Any], ...]
    validation_summary: dict[str, Any]
    isolation_verified: bool
    isolation_comparison: dict[str, Any]
    manifest: dict[str, Any]


def behavior_evidence_status(sample: Mapping[str, Any]) -> dict[str, Any]:
    """Classify propensity evidence without mutating legacy samples."""

    schema_version = sample.get("schema_version")
    if schema_version in _LEGACY_SCHEMA_VERSIONS:
        return {
            "verified": False,
            "reason": "legacy_schema_without_confirmed_exploration",
        }
    if schema_version != CANONICAL_EXPLORATION_SCHEMA_VERSION:
        return {"verified": False, "reason": "unsupported_schema"}

    exploration = sample.get("exploration")
    if not isinstance(exploration, Mapping):
        return {"verified": False, "reason": "missing_exploration_block"}
    requirements = (
        ("replay_status", "valid", "replay_not_valid"),
        ("confirmation_status", "confirmed", "confirmation_not_valid"),
        ("candidate_legality", "valid", "candidate_not_legal"),
    )
    for key, expected, reason in requirements:
        if exploration.get(key) != expected:
            return {"verified": False, "reason": reason}
    if sample.get("behavior_probability_status") != "verified_known_propensity":
        return {"verified": False, "reason": "probability_not_verified"}
    probability = sample.get("behavior_action_probability")
    if (
        isinstance(probability, bool)
        or not isinstance(probability, (int, float))
        or not math.isfinite(float(probability))
        or not 0 < float(probability) <= 1
    ):
        return {"verified": False, "reason": "probability_not_valid"}
    return {"verified": True, "reason": "verified_known_propensity"}


def export_confirmed_exploration_samples(
    trace_path: Path | str,
    manifest_path: Path | str,
    *,
    outcomes: Optional[Sequence[Mapping[str, Any]]] = None,
    post_isolation_hashes: Optional[Mapping[str, Any]] = None,
) -> ExplorationExportResult:
    """Replay a session and export only uniquely confirmed executable actions."""

    trace_path = Path(trace_path).resolve()
    manifest_path = Path(manifest_path).resolve()
    manifest, config = _load_and_validate_manifest(manifest_path, trace_path)
    records = ExplorationRecordStore(trace_path).read_records()
    proposals: dict[str, dict[str, Any]] = {}
    resolutions: dict[str, dict[str, Any]] = {}
    for record in records:
        decision_id = record["decision_id"]
        if record["record_type"] == "proposed":
            proposals[decision_id] = record
        else:
            resolutions[decision_id] = record

    summary = {
        "proposed_records": len(proposals),
        "resolution_records": len(resolutions),
        "eligible_proposals": 0,
        "confirmed": 0,
        "replay_valid": 0,
        "candidate_legal": 0,
        "shadow_only": 0,
        "excluded": 0,
        "exclusion_reasons": {},
    }
    samples: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []

    for decision_id, proposed_record in proposals.items():
        proposal_record = proposed_record.get("proposal", {})
        if not bool(proposal_record.get("execution_eligible")):
            summary["shadow_only"] += 1
            _exclude(exclusions, proposed_record, "shadow_only")
            continue

        summary["eligible_proposals"] += 1
        resolution = resolutions.get(decision_id)
        if resolution is None:
            _exclude(exclusions, proposed_record, "confirmation_missing")
            continue
        status = str(resolution.get("status") or "missing")
        if status != "confirmed" or not bool(
            resolution.get("executed_known_propensity")
        ):
            _exclude(exclusions, proposed_record, f"confirmation_{status}")
            continue
        if not _resolution_matches_proposal(proposed_record, resolution):
            _exclude(exclusions, proposed_record, "confirmation_link_mismatch")
            continue
        summary["confirmed"] += 1

        try:
            proposal = _proposal_from_record(proposal_record)
            selection = _selection_from_record(proposed_record["selection"])
        except (KeyError, TypeError, ValueError) as exc:
            _exclude(
                exclusions,
                proposed_record,
                "replay_mismatch",
                detail=str(exc),
            )
            continue

        if proposal.state_hash != proposal_record.get("state_hash"):
            _exclude(exclusions, proposed_record, "replay_mismatch")
            continue
        replay = verify_exploration_selection(
            config,
            proposal,
            selection,
            trajectory_session_id=str(proposed_record["trajectory_session_id"]),
            decision_index=int(proposed_record["decision_index"]),
        )
        if not replay.valid:
            _exclude(
                exclusions,
                proposed_record,
                "replay_mismatch",
                detail=",".join(replay.errors),
            )
            continue
        summary["replay_valid"] += 1

        if not _selected_candidate_is_legal(
            proposed_record.get("selected_candidate"),
            proposal,
            selection,
        ):
            _exclude(exclusions, proposed_record, "selected_candidate_illegal")
            continue
        summary["candidate_legal"] += 1
        samples.append(
            _build_v3_sample(
                proposed_record,
                resolution,
                proposal,
                selection,
                manifest,
                config,
            )
        )

    joined_samples = attach_live_outcomes(samples, list(outcomes or ()))
    isolation = compare_isolation_snapshots(
        manifest.get("pre_session_isolation_hashes", {}),
        post_isolation_hashes,
    )
    reason_counts = Counter(row["reason"] for row in exclusions)
    summary["excluded"] = len(exclusions)
    summary["exclusion_reasons"] = dict(sorted(reason_counts.items()))
    summary["exported"] = len(joined_samples)
    summary["outcome_matched"] = sum(
        sample.get("outcome", {}).get("join_status") == "matched"
        for sample in joined_samples
    )
    summary["isolation_verified"] = isolation["verified"]
    return ExplorationExportResult(
        samples=tuple(joined_samples),
        exclusions=tuple(exclusions),
        validation_summary=summary,
        isolation_verified=bool(isolation["verified"]),
        isolation_comparison=isolation,
        manifest=manifest,
    )


def compare_isolation_snapshots(
    expected: Mapping[str, Any],
    observed: Optional[Mapping[str, Any]],
) -> dict[str, Any]:
    """Require exact path membership and metadata equality."""

    if observed is None:
        return {"verified": False, "mismatches": ["post_snapshot_missing"]}
    if not isinstance(expected, Mapping) or not isinstance(observed, Mapping):
        return {"verified": False, "mismatches": ["snapshot_not_mapping"]}

    mismatches: list[str] = []
    if not expected:
        mismatches.append("pre_snapshot_empty")
    for key in sorted(expected, key=str):
        metadata = expected[key]
        key_text = str(key)
        if not isinstance(metadata, Mapping):
            mismatches.append(f"{key_text}:metadata_not_mapping_at_baseline")
        elif metadata.get("exists") is not True:
            mismatches.append(f"{key_text}:not_present_at_baseline")
        elif metadata.get("is_file") is not True:
            mismatches.append(f"{key_text}:not_file_at_baseline")
        else:
            for field in ("size", "mtime_ns", "sha256"):
                if field not in metadata:
                    mismatches.append(
                        f"{key_text}:{field}_missing_at_baseline"
                    )
    expected_keys = {str(key) for key in expected}
    observed_keys = {str(key) for key in observed}
    for key in sorted(expected_keys - observed_keys):
        mismatches.append(f"{key}:missing")
    for key in sorted(observed_keys - expected_keys):
        mismatches.append(f"{key}:unexpected")
    for key in sorted(expected_keys & observed_keys):
        expected_metadata = expected[key]
        observed_metadata = observed[key]
        if not isinstance(expected_metadata, Mapping) or not isinstance(
            observed_metadata, Mapping
        ):
            if expected_metadata != observed_metadata:
                mismatches.append(f"{key}:metadata_mismatch")
            continue
        metadata_keys = {str(field) for field in expected_metadata} | {
            str(field) for field in observed_metadata
        }
        for field in sorted(metadata_keys):
            if field not in expected_metadata:
                mismatches.append(f"{key}:{field}_unexpected")
            elif field not in observed_metadata:
                mismatches.append(f"{key}:{field}_missing")
            elif expected_metadata[field] != observed_metadata[field]:
                mismatches.append(f"{key}:{field}_mismatch")
    return {"verified": not mismatches, "mismatches": mismatches}


def evaluate_known_propensity_qualification(
    samples: Sequence[Mapping[str, Any]],
    *,
    validation_summary: Mapping[str, Any],
    isolation_verified: bool,
    required_categories: Sequence[str] = _REQUIRED_CATEGORIES,
) -> dict[str, Any]:
    """Evaluate the data-collection gate without making policy claims."""

    eligible = _nonnegative_count(validation_summary.get("eligible_proposals"))
    confirmed = _nonnegative_count(validation_summary.get("confirmed"))
    replay_valid = _nonnegative_count(validation_summary.get("replay_valid"))
    candidate_legal = _nonnegative_count(validation_summary.get("candidate_legal"))
    joined = [
        sample
        for sample in samples
        if sample.get("trajectory_group_id")
        and sample.get("outcome", {}).get("included_in_gate") is True
        and sample.get("outcome", {}).get("join_status") == "matched"
    ]
    by_trajectory: dict[str, Mapping[str, Any]] = {}
    for sample in joined:
        by_trajectory.setdefault(str(sample["trajectory_group_id"]), sample)

    support: dict[str, dict[str, int]] = {
        str(category): {"baseline": 0, "alternative": 0}
        for category in required_categories
    }
    for sample in samples:
        category = str(sample.get("category") or "")
        arm = str(sample.get("exploration", {}).get("selected_arm") or "")
        if category in support and arm in support[category]:
            support[category][arm] += 1

    verified_probabilities = sum(
        behavior_evidence_status(sample).get("verified") is True
        for sample in samples
    )
    floor_distribution = Counter(
        str(sample.get("outcome", {}).get("floor_reached"))
        for sample in by_trajectory.values()
        if sample.get("outcome", {}).get("floor_reached") is not None
    )
    killed_by_distribution = Counter(
        str(sample.get("outcome", {}).get("killed_by"))
        for sample in by_trajectory.values()
        if sample.get("outcome", {}).get("killed_by")
    )
    victories = sum(
        bool(sample.get("outcome", {}).get("victory"))
        for sample in by_trajectory.values()
    )

    blockers: list[str] = []
    if len(by_trajectory) < _MIN_UNIQUE_TRAJECTORIES:
        blockers.append("insufficient_unique_joined_trajectories")
    if confirmed != eligible:
        blockers.append("confirmation_coverage_incomplete")
    if replay_valid != eligible:
        blockers.append("replay_coverage_incomplete")
    if candidate_legal != eligible:
        blockers.append("candidate_legality_coverage_incomplete")
    if verified_probabilities != eligible:
        blockers.append("propensity_coverage_incomplete")
    for category in required_categories:
        for arm in ("baseline", "alternative"):
            if support[str(category)][arm] < _MIN_ARM_SUPPORT:
                blockers.append(f"insufficient_{category}_{arm}_support")
    if not isolation_verified:
        blockers.append("isolation_not_verified")

    metrics = {
        "eligible_proposals": eligible,
        "confirmed": confirmed,
        "replay_valid": replay_valid,
        "candidate_legal": candidate_legal,
        "verified_propensities": verified_probabilities,
        "exported_samples": len(samples),
        "outcome_matched_samples": len(joined),
        "unique_joined_trajectories": len(by_trajectory),
        "category_arm_support": support,
        "floor_distribution": dict(sorted(floor_distribution.items())),
        "killed_by_distribution": dict(sorted(killed_by_distribution.items())),
        "victories": victories,
    }
    return {
        "known_propensity_exploration_data_ready": not blockers,
        "blocking_conditions": blockers,
        "metrics": metrics,
        "isolation_verified": bool(isolation_verified),
        "ope_ready": False,
        "causal_uplift_ready": False,
        "formal_noncombat_rl_training_ready": False,
        "live_policy_promotion_ready": False,
    }


def render_known_propensity_qualification_report(
    result: Mapping[str, Any],
) -> str:
    """Render a compact, auditable report with explicit downstream blocks."""

    metrics = result.get("metrics", {})
    blockers = list(result.get("blocking_conditions", ()))
    support = metrics.get("category_arm_support", {})
    floors = metrics.get("floor_distribution", {})
    killed_by = metrics.get("killed_by_distribution", {})
    lines = [
        "# Known-Propensity Non-Combat Exploration Qualification",
        "",
        "Known-propensity exploration data ready: "
        + _bool_text(result.get("known_propensity_exploration_data_ready")),
        f"Unique joined trajectories: {metrics.get('unique_joined_trajectories', 0)}",
        f"Eligible proposals: {metrics.get('eligible_proposals', 0)}",
        f"Confirmed proposals: {metrics.get('confirmed', 0)}",
        f"Replay-valid proposals: {metrics.get('replay_valid', 0)}",
        f"Candidate-legal proposals: {metrics.get('candidate_legal', 0)}",
        f"Verified propensities: {metrics.get('verified_propensities', 0)}",
        f"Victories: {metrics.get('victories', 0)}",
        "",
        "## Category Arm Support",
    ]
    for category in sorted(support):
        counts = support[category]
        lines.append(
            f"- {category}: baseline={counts.get('baseline', 0)}, "
            f"alternative={counts.get('alternative', 0)}"
        )
    lines.extend(["", "## Outcome Distribution"])
    lines.append("- Floors: " + _format_counts(floors))
    lines.append("- Killed by: " + _format_counts(killed_by))
    lines.extend(["", "## Blocking Conditions"])
    if blockers:
        lines.extend(f"- {blocker}" for blocker in blockers)
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Downstream Readiness",
            "OPE ready: " + _bool_text(result.get("ope_ready")),
            "Causal uplift ready: "
            + _bool_text(result.get("causal_uplift_ready")),
            "Formal non-combat RL training ready: "
            + _bool_text(result.get("formal_noncombat_rl_training_ready")),
            "Live policy promotion ready: "
            + _bool_text(result.get("live_policy_promotion_ready")),
            "",
        ]
    )
    return "\n".join(lines)


def _load_and_validate_manifest(
    manifest_path: Path,
    trace_path: Path,
) -> tuple[dict[str, Any], ExplorationConfig]:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ExplorationEvidenceError(f"unable to read manifest: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ExplorationEvidenceError(f"invalid manifest JSON: {exc}") from exc
    if not isinstance(manifest, dict):
        raise ExplorationEvidenceError("manifest must be a JSON object")
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise ExplorationEvidenceError("unsupported exploration manifest schema")

    expected_manifest_hash = manifest.get("manifest_hash")
    hash_payload = dict(manifest)
    hash_payload.pop("manifest_hash", None)
    if expected_manifest_hash != _sha256_json(hash_payload):
        raise ExplorationEvidenceError("manifest hash mismatch")
    effective = manifest.get("effective_config")
    if not isinstance(effective, Mapping):
        raise ExplorationEvidenceError("manifest effective_config is missing")
    if manifest.get("effective_config_hash") != _sha256_json(effective):
        raise ExplorationEvidenceError("effective config hash mismatch")

    source_path_value = effective.get("source_path")
    source_path = Path(source_path_value) if source_path_value else None
    config = parse_exploration_config(effective, config_path=source_path)
    if config.to_record() != dict(effective):
        raise ExplorationEvidenceError("effective config does not replay exactly")
    if config.manifest_path != manifest_path:
        raise ExplorationEvidenceError("manifest path does not match effective config")
    if config.trace_path != trace_path:
        raise ExplorationEvidenceError("trace path does not match effective config")
    if manifest.get("session_id") != config.session_id:
        raise ExplorationEvidenceError("manifest session ID mismatch")
    source = manifest.get("source", {})
    if (
        not isinstance(source, Mapping)
        or source.get("commit") != config.source_commit
        or source.get("tracked_clean") is not True
    ):
        raise ExplorationEvidenceError("manifest source provenance mismatch")
    if source_path is not None:
        try:
            source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
        except OSError as exc:
            raise ExplorationEvidenceError(
                f"unable to validate config source hash: {exc}"
            ) from exc
        if manifest.get("config_file_sha256") != source_hash:
            raise ExplorationEvidenceError("config file hash mismatch")
    return manifest, config


def _proposal_from_record(record: Mapping[str, Any]) -> NonCombatProposal:
    candidates = tuple(
        ExplorationCandidate(
            action_id=str(candidate["action_id"]),
            kind=str(candidate["kind"]),
            label=str(candidate["label"]),
            available=candidate["available"],
            executable=candidate["executable"],
            raw=candidate.get("raw", {}),
        )
        for candidate in record["candidates"]
    )
    return NonCombatProposal(
        category=str(record["category"]),
        baseline_action_id=str(record["baseline_action_id"]),
        alternative_action_id=str(record["alternative_action_id"]),
        candidates=candidates,
        state=record["state"],
        execution_eligible=record["execution_eligible"],
        rollout_mode=str(record["rollout_mode"]),
        ineligibility_reason=str(record.get("ineligibility_reason") or ""),
    )


def _selection_from_record(record: Mapping[str, Any]) -> ExplorationSelection:
    distribution = tuple(
        _probability_from_record(entry) for entry in record["distribution"]
    )
    selected_numerator = int(record["selected_probability_numerator"])
    selected_denominator = int(record["selected_probability_denominator"])
    _validate_probability_value(
        record.get("selected_action_probability"),
        selected_numerator,
        selected_denominator,
    )
    return ExplorationSelection(
        schema_version=str(record["schema_version"]),
        session_id=str(record["session_id"]),
        trajectory_session_id=str(record["trajectory_session_id"]),
        decision_index=int(record["decision_index"]),
        category=str(record["category"]),
        state_hash=str(record["state_hash"]),
        distribution=distribution,
        distribution_hash=str(record["distribution_hash"]),
        draw_input_hash=str(record["draw_input_hash"]),
        draw_counter=int(record["draw_counter"]),
        draw_u64=int(record["draw_u64"]),
        draw_bucket=int(record["draw_bucket"]),
        selected_action_id=str(record["selected_action_id"]),
        selected_probability_numerator=selected_numerator,
        selected_probability_denominator=selected_denominator,
    )


def _probability_from_record(record: Mapping[str, Any]) -> ActionProbability:
    numerator = int(record["numerator"])
    denominator = int(record["denominator"])
    _validate_probability_value(record.get("value"), numerator, denominator)
    return ActionProbability(
        action_id=str(record["action_id"]),
        numerator=numerator,
        denominator=denominator,
    )


def _validate_probability_value(value: Any, numerator: int, denominator: int) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) != numerator / denominator
    ):
        raise ExplorationEvidenceError("probability float does not match exact value")


def _resolution_matches_proposal(
    proposed: Mapping[str, Any],
    resolution: Mapping[str, Any],
) -> bool:
    return all(
        resolution.get(field) == proposed.get(field)
        for field in (
            "decision_id",
            "session_id",
            "trajectory_session_id",
            "category",
        )
    ) and resolution.get("selected_action_id") == proposed.get("selection", {}).get(
        "selected_action_id"
    )


def _selected_candidate_is_legal(
    selected_record: Any,
    proposal: NonCombatProposal,
    selection: ExplorationSelection,
) -> bool:
    if not isinstance(selected_record, Mapping):
        return False
    if selected_record.get("action_id") != selection.selected_action_id:
        return False
    candidate = next(
        (
            item
            for item in proposal.candidates
            if item.action_id == selection.selected_action_id
        ),
        None,
    )
    if candidate is None or not candidate.available or not candidate.executable:
        return False
    return (
        selected_record.get("available") is True
        and selected_record.get("executable") is True
        and selected_record.get("kind") == candidate.kind
        and selected_record.get("label") == candidate.label
        and selected_record.get("raw", {}) == candidate.to_record()["raw"]
    )


def _build_v3_sample(
    proposed: Mapping[str, Any],
    resolution: Mapping[str, Any],
    proposal: NonCombatProposal,
    selection: ExplorationSelection,
    manifest: Mapping[str, Any],
    config: ExplorationConfig,
) -> dict[str, Any]:
    selected_arm = (
        "alternative"
        if selection.selected_action_id == proposal.alternative_action_id
        else "baseline"
    )
    selected_probability = {
        "numerator": selection.selected_probability_numerator,
        "denominator": selection.selected_probability_denominator,
        "value": selection.selected_action_probability,
    }
    state = dict(proposal.to_record()["state"])
    source = manifest.get("source", {})
    exploration = {
        "session_id": config.session_id,
        "trajectory_session_id": proposed["trajectory_session_id"],
        "trajectory_started_unix": proposed.get("trajectory_started_unix"),
        "decision_id": proposed["decision_id"],
        "decision_index": proposed["decision_index"],
        "proposed_unix": proposed.get("proposed_unix"),
        "resolved_unix": resolution.get("resolved_unix"),
        "baseline_action_id": proposal.baseline_action_id,
        "alternative_action_id": proposal.alternative_action_id,
        "selected_arm": selected_arm,
        "candidate_distribution": [
            probability.to_record() for probability in selection.distribution
        ],
        "selected_probability": selected_probability,
        "state_hash": selection.state_hash,
        "distribution_hash": selection.distribution_hash,
        "draw_input_hash": selection.draw_input_hash,
        "draw_counter": selection.draw_counter,
        "draw_u64": selection.draw_u64,
        "draw_bucket": selection.draw_bucket,
        "replay_status": "valid",
        "confirmation_status": "confirmed",
        "confirmation_reason": resolution.get("reason"),
        "candidate_legality": "valid",
        "manifest_hash": manifest.get("manifest_hash"),
        "effective_config_hash": manifest.get("effective_config_hash"),
        "config_file_sha256": manifest.get("config_file_sha256"),
        "source_commit": source.get("commit"),
        "proposal_record_hash": _sha256_json(proposed),
        "resolution_record_hash": _sha256_json(resolution),
    }
    return {
        "schema_version": CANONICAL_EXPLORATION_SCHEMA_VERSION,
        "sample_id": proposed["decision_id"],
        "category": proposal.category,
        "source": "noncombat_exploration",
        "floor": state.get("floor"),
        "act": state.get("act"),
        "unix_time": proposed.get("trajectory_started_unix"),
        "trajectory_session_id": proposed["trajectory_session_id"],
        "trajectory_group_id": None,
        "behavior_policy_id": proposed["behavior_policy_id"],
        "behavior_policy_commit": config.source_commit,
        "behavior_action_probability": selection.selected_action_probability,
        "behavior_probability_status": "verified_known_propensity",
        "state": state,
        "candidate_actions": [
            candidate.to_record() for candidate in proposal.candidates
        ],
        "selected_action_id": selection.selected_action_id,
        "current_policy_label": {
            "label": proposal.baseline_action_id,
            "action_id": proposal.baseline_action_id,
        },
        "bottled_label": None,
        "evidence_quality": "confirmed_known_propensity",
        "limitations": [
            "abstention-only exploration does not establish policy quality"
        ],
        "outcome": {"join_status": "missing", "included_in_gate": False},
        "exploration": exploration,
    }


def _exclude(
    exclusions: list[dict[str, Any]],
    proposed: Mapping[str, Any],
    reason: str,
    *,
    detail: str = "",
) -> None:
    row = {
        "decision_id": proposed.get("decision_id"),
        "category": proposed.get("category"),
        "reason": reason,
    }
    if detail:
        row["detail"] = detail
    exclusions.append(row)


def _nonnegative_count(value: Any) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, number)


def _bool_text(value: Any) -> str:
    return "true" if value is True else "false"


def _format_counts(counts: Mapping[str, Any]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{key}={counts[key]}" for key in sorted(counts))


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()
