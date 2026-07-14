"""Independently replay non-combat OPE readiness artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import defaultdict
from collections.abc import Mapping, Sequence
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from typing import Any


_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")


class ArtifactVerificationError(ValueError):
    """Raised when a persisted readiness claim cannot be replayed exactly."""


class _DuplicateJsonKeyError(ValueError):
    def __init__(self, key: str) -> None:
        super().__init__(key)
        self.key = key


class _Checks:
    def __init__(self) -> None:
        self.count = 0

    def require(self, condition: bool, message: str) -> None:
        self.count += 1
        if not condition:
            raise ArtifactVerificationError(message)


def verify_artifact_pair(
    sample_path: Path | str,
    target_manifest_path: Path | str,
    readiness_path: Path | str,
) -> dict[str, Any]:
    """Replay one complete-trajectory artifact pair and its closed gates."""

    checks = _Checks()
    sample_path = Path(sample_path)
    target_manifest_path = Path(target_manifest_path)
    readiness_path = Path(readiness_path)
    sample_bytes = sample_path.read_bytes()
    target_bytes = target_manifest_path.read_bytes()
    readiness_bytes = readiness_path.read_bytes()
    samples = _load_jsonl(sample_path)
    target = _load_mapping(target_bytes, target_manifest_path)
    readiness = _load_mapping(readiness_bytes, readiness_path)

    checks.require(
        readiness.get("schema_version") == "noncombat-ope-readiness-v1",
        "readiness schema mismatch",
    )
    checks.require(
        target.get("schema_version") == "noncombat-ope-target-policy-v1",
        "target schema mismatch",
    )
    construction_mode = target.get("construction_mode")
    checks.require(
        construction_mode in {"behavior_identity", "current_deterministic", "imported"},
        "target construction mode mismatch",
    )
    if construction_mode == "behavior_identity":
        checks.require(
            target.get("diagnostic_only") is True,
            "behavior identity must be diagnostic-only",
        )
    if construction_mode == "current_deterministic":
        checks.require(
            target.get("diagnostic_only") is False,
            "deterministic Current cannot be diagnostic-only",
        )
    source = readiness.get("source")
    checks.require(isinstance(source, Mapping), "readiness source block missing")
    sample_sha256 = hashlib.sha256(sample_bytes).hexdigest()
    target_content_sha256 = hashlib.sha256(target_bytes).hexdigest()
    checks.require(
        source.get("sample_sha256") == sample_sha256,
        "sample content hash mismatch",
    )
    checks.require(
        source.get("sample_size_bytes") == len(sample_bytes),
        "sample size mismatch",
    )
    checks.require(
        source.get("sample_file") == sample_path.name,
        "sample file binding mismatch",
    )
    checks.require(
        source.get("target_manifest_content_sha256") == target_content_sha256,
        "target content hash mismatch",
    )
    target_manifest_hash = _target_manifest_hash(target)
    checks.require(
        target.get("manifest_hash") == target_manifest_hash,
        "target manifest hash mismatch",
    )
    checks.require(
        source.get("target_manifest_hash") == target_manifest_hash,
        "readiness target manifest hash mismatch",
    )
    checks.require(
        target.get("source_sample_sha256") == sample_sha256,
        "target source sample hash mismatch",
    )

    sample_by_id: dict[str, Mapping[str, Any]] = {}
    samples_by_group: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    outcomes_by_group: dict[str, set[str]] = defaultdict(set)
    decision_indexes_by_group: dict[str, set[int]] = defaultdict(set)
    trajectory_sessions_by_group: dict[str, set[str]] = defaultdict(set)
    behavior_policies_by_group: dict[str, set[str]] = defaultdict(set)
    behavior_sessions_by_group: dict[str, set[str]] = defaultdict(set)
    source_commits_by_group: dict[str, set[str]] = defaultdict(set)
    for sample in samples:
        checks.require(isinstance(sample, Mapping), "sample must be a mapping")
        checks.require(
            sample.get("schema_version") == "noncombat-rl-decision-v3",
            "canonical sample schema mismatch",
        )
        sample_id = sample.get("sample_id")
        group_id = sample.get("trajectory_group_id")
        checks.require(
            isinstance(sample_id, str) and bool(sample_id),
            "sample identity missing",
        )
        checks.require(
            isinstance(group_id, str) and group_id.startswith("run:"),
            f"{sample_id}: trajectory group missing",
        )
        checks.require(
            sample_id not in sample_by_id,
            f"duplicate sample identity: {sample_id}",
        )
        exploration = sample.get("exploration")
        checks.require(
            isinstance(exploration, Mapping),
            f"{sample_id}: exploration block missing",
        )
        checks.require(
            exploration.get("decision_id") == sample_id,
            f"{sample_id}: decision identity mismatch",
        )
        decision_index = exploration.get("decision_index")
        checks.require(
            isinstance(decision_index, int)
            and not isinstance(decision_index, bool)
            and decision_index >= 0,
            f"{sample_id}: decision_index invalid",
        )
        checks.require(
            decision_index not in decision_indexes_by_group[group_id],
            f"{group_id}: duplicate decision_index: {decision_index}",
        )
        decision_indexes_by_group[group_id].add(decision_index)

        trajectory_session_id = sample.get("trajectory_session_id")
        checks.require(
            isinstance(trajectory_session_id, str)
            and bool(trajectory_session_id)
            and exploration.get("trajectory_session_id") == trajectory_session_id,
            f"{sample_id}: trajectory provenance mismatch",
        )
        behavior_policy_id = sample.get("behavior_policy_id")
        behavior_session_id = exploration.get("session_id")
        checks.require(
            isinstance(behavior_session_id, str)
            and behavior_policy_id
            == f"known-propensity-epsilon-v1:{behavior_session_id}",
            f"{sample_id}: behavior session provenance mismatch",
        )
        source_commit = sample.get("behavior_policy_commit")
        checks.require(
            isinstance(source_commit, str)
            and _COMMIT_PATTERN.fullmatch(source_commit) is not None
            and exploration.get("source_commit") == source_commit,
            f"{sample_id}: source commit provenance mismatch",
        )
        sample_by_id[sample_id] = sample
        samples_by_group[group_id].append(sample)
        trajectory_sessions_by_group[group_id].add(trajectory_session_id)
        behavior_policies_by_group[group_id].add(str(behavior_policy_id))
        behavior_sessions_by_group[group_id].add(behavior_session_id)
        source_commits_by_group[group_id].add(source_commit)
        outcome = sample.get("outcome")
        checks.require(
            isinstance(outcome, Mapping),
            f"{sample_id}: outcome missing",
        )
        checks.require(
            outcome.get("join_status") == "matched"
            and outcome.get("included_in_gate") is True,
            f"{sample_id}: outcome is not complete",
        )
        expected_run_file = f"{group_id.removeprefix('run:')}.run"
        checks.require(
            outcome.get("run_file") == expected_run_file,
            f"{sample_id}: outcome run file mismatch",
        )
        victory = outcome.get("victory")
        floor_reached = outcome.get("floor_reached")
        killed_by = outcome.get("killed_by")
        playtime = outcome.get("playtime")
        checks.require(
            isinstance(victory, bool),
            f"{sample_id}: victory must be boolean",
        )
        checks.require(
            isinstance(floor_reached, int)
            and not isinstance(floor_reached, bool)
            and floor_reached > 0,
            f"{sample_id}: floor_reached must be a positive integer",
        )
        checks.require(
            isinstance(killed_by, str),
            f"{sample_id}: killed_by must be a string",
        )
        checks.require(
            isinstance(playtime, int)
            and not isinstance(playtime, bool)
            and playtime >= 0,
            f"{sample_id}: playtime must be a non-negative integer",
        )
        decision_floor = sample.get("floor")
        checks.require(
            isinstance(decision_floor, int)
            and not isinstance(decision_floor, bool)
            and 0 <= decision_floor <= floor_reached,
            f"{sample_id}: outcome floor precedes decision",
        )
        outcomes_by_group[group_id].add(
            json.dumps(outcome, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        )

    for group_id in sorted(samples_by_group):
        checks.require(
            len(trajectory_sessions_by_group[group_id]) == 1,
            f"{group_id}: trajectory session conflict",
        )
        checks.require(
            len(behavior_policies_by_group[group_id]) == 1,
            f"{group_id}: behavior policy conflict",
        )
        checks.require(
            len(behavior_sessions_by_group[group_id]) == 1,
            f"{group_id}: behavior session conflict",
        )
        checks.require(
            len(source_commits_by_group[group_id]) == 1,
            f"{group_id}: source commit conflict",
        )
        checks.require(
            len(outcomes_by_group[group_id]) == 1,
            f"{group_id}: mixed trajectory outcome",
        )

    trajectory_audit = readiness.get("trajectory_audit")
    checks.require(
        isinstance(trajectory_audit, Mapping),
        "trajectory audit block missing",
    )
    checks.require(
        trajectory_audit.get("blocked_trajectories") == [],
        "independent verifier supports complete-trajectory artifacts only",
    )
    checks.require(
        trajectory_audit.get("input_decision_count") == len(samples),
        "trajectory audit input decision count mismatch",
    )
    checks.require(
        trajectory_audit.get("complete_decision_count") == len(samples),
        "trajectory audit complete decision count mismatch",
    )
    checks.require(
        trajectory_audit.get("complete_trajectory_count") == len(samples_by_group),
        "trajectory audit complete trajectory count mismatch",
    )
    complete_rows = trajectory_audit.get("complete_trajectories")
    checks.require(
        isinstance(complete_rows, list),
        "complete trajectory rows missing",
    )
    complete_by_group = {
        row.get("group_id"): row for row in complete_rows if isinstance(row, Mapping)
    }
    checks.require(
        len(complete_by_group) == len(complete_rows)
        and set(complete_by_group) == set(samples_by_group),
        "complete trajectory coverage mismatch",
    )
    for group_id, group_samples in sorted(samples_by_group.items()):
        row = complete_by_group[group_id]
        expected_outcome = json.loads(next(iter(outcomes_by_group[group_id])))
        checks.require(
            row.get("decision_count") == len(group_samples),
            f"{group_id}: complete trajectory decision count mismatch",
        )
        checks.require(
            row.get("trajectory_session_id")
            == group_samples[0].get("trajectory_session_id"),
            f"{group_id}: reported trajectory session mismatch",
        )
        checks.require(
            row.get("outcome") == {
                "floor_reached": expected_outcome["floor_reached"],
                "killed_by": expected_outcome["killed_by"],
                "playtime": expected_outcome["playtime"],
                "run_file": expected_outcome["run_file"],
                "victory": expected_outcome["victory"],
            },
            f"{group_id}: reported terminal outcome mismatch",
        )

    target_entries = target.get("entries")
    checks.require(
        isinstance(target_entries, list),
        "target entries missing",
    )
    target_by_id: dict[str, Mapping[str, Any]] = {}
    for entry in target_entries:
        checks.require(isinstance(entry, Mapping), "target entry must be a mapping")
        sample_id = entry.get("sample_id")
        checks.require(
            isinstance(sample_id, str) and sample_id not in target_by_id,
            f"duplicate or invalid target sample identity: {sample_id}",
        )
        target_by_id[sample_id] = entry
    checks.require(
        set(target_by_id) == set(sample_by_id),
        "target decision coverage mismatch",
    )

    diagnostics = readiness.get("diagnostics")
    checks.require(isinstance(diagnostics, Mapping), "diagnostics block missing")
    reported_trajectory_rows = diagnostics.get("trajectory_weights")
    checks.require(
        isinstance(reported_trajectory_rows, list),
        "reported trajectory weights missing",
    )
    reported_by_group: dict[str, Mapping[str, Any]] = {}
    reported_decisions: dict[str, Mapping[str, Any]] = {}
    for row in reported_trajectory_rows:
        checks.require(
            isinstance(row, Mapping),
            "reported trajectory row must be a mapping",
        )
        group_id = row.get("group_id")
        checks.require(
            isinstance(group_id, str) and group_id not in reported_by_group,
            f"duplicate reported trajectory: {group_id}",
        )
        reported_by_group[group_id] = row
        decision_rows = row.get("decisions")
        checks.require(
            isinstance(decision_rows, list),
            f"{group_id}: reported decisions missing",
        )
        for decision in decision_rows:
            checks.require(
                isinstance(decision, Mapping),
                f"{group_id}: reported decision must be a mapping",
            )
            sample_id = decision.get("sample_id")
            checks.require(
                isinstance(sample_id, str) and sample_id not in reported_decisions,
                f"duplicate reported decision: {sample_id}",
            )
            reported_decisions[sample_id] = decision
    checks.require(
        set(reported_decisions) == set(sample_by_id),
        "reported decision coverage mismatch",
    )

    exact_ratios: dict[str, Fraction] = {}
    trajectory_products: dict[str, Fraction] = {
        group_id: Fraction(1, 1) for group_id in samples_by_group
    }
    arm_decision_counts: dict[tuple[str, str], int] = defaultdict(int)
    arm_groups: dict[tuple[str, str], set[str]] = defaultdict(set)
    for sample_id in sorted(sample_by_id):
        sample = sample_by_id[sample_id]
        entry = target_by_id[sample_id]
        exploration = sample.get("exploration")
        checks.require(
            isinstance(exploration, Mapping),
            f"{sample_id}: exploration block missing",
        )
        checks.require(
            entry.get("state_hash") == exploration.get("state_hash"),
            f"{sample_id}: target state hash mismatch",
        )
        checks.require(
            entry.get("behavior_distribution_hash")
            == exploration.get("distribution_hash"),
            f"{sample_id}: target behavior distribution hash mismatch",
        )
        behavior = _distribution(
            exploration.get("candidate_distribution"),
            checks,
            context=f"{sample_id}: behavior",
        )
        target_distribution = _distribution(
            entry.get("probabilities"),
            checks,
            context=f"{sample_id}: target",
        )
        checks.require(
            set(behavior) == set(target_distribution),
            f"{sample_id}: target support mismatch",
        )
        checks.require(
            sum(behavior.values(), Fraction(0, 1)) == Fraction(1, 1),
            f"{sample_id}: behavior distribution is not normalized",
        )
        checks.require(
            sum(target_distribution.values(), Fraction(0, 1)) == Fraction(1, 1),
            f"{sample_id}: target distribution is not normalized",
        )
        if construction_mode == "behavior_identity":
            checks.require(
                target_distribution == behavior,
                f"{sample_id}: behavior identity distribution mismatch",
            )
        selected_action_id = sample.get("selected_action_id")
        checks.require(
            selected_action_id in behavior and selected_action_id in target_distribution,
            f"{sample_id}: selected action outside support",
        )
        selected_probability = _fraction_from_record(
            exploration.get("selected_probability"),
            checks,
            context=f"{sample_id}: selected behavior probability",
            probability=True,
        )
        checks.require(
            selected_probability == behavior[selected_action_id],
            f"{sample_id}: selected behavior probability mismatch",
        )
        checks.require(
            selected_probability > 0,
            f"{sample_id}: selected behavior probability is zero",
        )
        ratio = target_distribution[selected_action_id] / selected_probability
        exact_ratios[sample_id] = ratio
        group_id = str(sample["trajectory_group_id"])
        trajectory_products[group_id] *= ratio

        reported = reported_decisions[sample_id]
        checks.require(
            reported.get("selected_action_id") == selected_action_id,
            f"{sample_id}: reported selected action mismatch",
        )
        checks.require(
            reported.get("category") == sample.get("category"),
            f"{sample_id}: reported category mismatch",
        )
        checks.require(
            reported.get("selected_arm") == exploration.get("selected_arm"),
            f"{sample_id}: reported arm mismatch",
        )
        checks.require(
            _fraction_from_record(
                reported.get("behavior_probability"),
                checks,
                context=f"{sample_id}: reported behavior probability",
                probability=True,
            )
            == selected_probability,
            f"{sample_id}: reported behavior probability mismatch",
        )
        checks.require(
            _fraction_from_record(
                reported.get("target_probability"),
                checks,
                context=f"{sample_id}: reported target probability",
                probability=True,
            )
            == target_distribution[selected_action_id],
            f"{sample_id}: reported target probability mismatch",
        )
        checks.require(
            _fraction_from_record(
                reported.get("ratio"),
                checks,
                context=f"{sample_id}: reported decision ratio",
            )
            == ratio,
            f"{sample_id}: reported decision ratio mismatch",
        )
        arm_key = (
            str(sample.get("category") or "unknown"),
            str(exploration.get("selected_arm") or "unknown"),
        )
        arm_decision_counts[arm_key] += 1
        arm_groups[arm_key].add(group_id)

    checks.require(
        set(reported_by_group) == set(trajectory_products),
        "reported trajectory coverage mismatch",
    )
    for group_id, product in sorted(trajectory_products.items()):
        checks.require(
            len(outcomes_by_group[group_id]) == 1,
            f"{group_id}: mixed trajectory outcome",
        )
        reported_weight = _fraction_from_record(
            reported_by_group[group_id].get("weight"),
            checks,
            context=f"{group_id}: reported trajectory weight",
        )
        checks.require(
            reported_weight == product,
            f"{group_id}: reported trajectory weight mismatch",
        )

    ordered_weights = [trajectory_products[key] for key in sorted(trajectory_products)]
    trajectory_count = len(ordered_weights)
    decision_count = len(samples)
    weight_sum = sum(ordered_weights, Fraction(0, 1))
    squared_sum = sum((weight * weight for weight in ordered_weights), Fraction(0, 1))
    ess = weight_sum * weight_sum / squared_sum if squared_sum else Fraction(0, 1)
    ess_fraction = ess / trajectory_count if trajectory_count else Fraction(0, 1)
    max_normalized_weight = (
        max(ordered_weights) / weight_sum
        if ordered_weights and weight_sum
        else Fraction(0, 1)
    )
    nonzero_count = sum(weight != 0 for weight in ordered_weights)
    zero_count = trajectory_count - nonzero_count
    _compare_metric(diagnostics, "weight_sum", weight_sum, checks)
    _compare_metric(diagnostics, "effective_sample_size", ess, checks)
    _compare_metric(diagnostics, "ess_fraction", ess_fraction, checks)
    _compare_metric(
        diagnostics,
        "max_normalized_weight",
        max_normalized_weight,
        checks,
    )
    checks.require(
        diagnostics.get("trajectory_count") == trajectory_count,
        "reported trajectory count mismatch",
    )
    checks.require(
        diagnostics.get("decision_count") == decision_count,
        "reported decision count mismatch",
    )
    checks.require(
        diagnostics.get("nonzero_weight_count") == nonzero_count,
        "reported nonzero weight count mismatch",
    )
    checks.require(
        diagnostics.get("zero_weight_count") == zero_count,
        "reported zero weight count mismatch",
    )

    expected_arm_support: dict[str, dict[str, dict[str, int]]] = {}
    for category, arm in sorted(arm_decision_counts):
        expected_arm_support.setdefault(category, {})[arm] = {
            "decision_count": arm_decision_counts[(category, arm)],
            "trajectory_count": len(arm_groups[(category, arm)]),
        }
    checks.require(
        diagnostics.get("category_arm_support") == expected_arm_support,
        "reported category-arm support mismatch",
    )

    outcomes = [
        json.loads(next(iter(outcomes_by_group[group_id])))
        for group_id in sorted(outcomes_by_group)
    ]
    victories = [outcome["victory"] for outcome in outcomes]
    floors = [outcome["floor_reached"] for outcome in outcomes]
    expected_variation = {
        "floor_reached": {
            "maximum": max(floors) if floors else None,
            "minimum": min(floors) if floors else None,
            "unique_count": len(set(floors)),
        },
        "victory": {
            "false": sum(not value for value in victories),
            "true": sum(victories),
            "unique_count": len(set(victories)),
        },
    }
    checks.require(
        diagnostics.get("outcome_variation") == expected_variation,
        "reported outcome variation mismatch",
    )

    expected_blockers = _expected_overlap_blockers(
        trajectory_count=trajectory_count,
        nonzero_count=nonzero_count,
        ess=ess,
        ess_fraction=ess_fraction,
        max_normalized_weight=max_normalized_weight,
        victory_unique_count=len(set(victories)),
    )
    overlap = readiness.get("overlap_screens")
    checks.require(isinstance(overlap, Mapping), "overlap screen block missing")
    reported_blockers = overlap.get("blockers")
    checks.require(
        isinstance(reported_blockers, list),
        "overlap blockers missing",
    )
    checks.require(
        [row.get("code") for row in reported_blockers] == expected_blockers,
        "overlap blocker replay mismatch",
    )
    checks.require(
        overlap.get("ready") is (not expected_blockers),
        "overlap readiness mismatch",
    )

    identity_invariants_passed = construction_mode == "behavior_identity"
    identity = readiness.get("identity_self_check")
    checks.require(isinstance(identity, Mapping), "identity self-check missing")
    if identity_invariants_passed:
        checks.require(
            all(ratio == 1 for ratio in exact_ratios.values()),
            "identity decision ratio mismatch",
        )
        checks.require(
            all(weight == 1 for weight in ordered_weights),
            "identity trajectory weight mismatch",
        )
        checks.require(ess == trajectory_count, "identity ESS mismatch")
        checks.require(identity.get("applicable") is True, "identity applicability mismatch")
        checks.require(identity.get("passed") is True, "identity self-check did not pass")
        checks.require(
            identity.get("weighted_outcomes") == identity.get("unweighted_outcomes"),
            "identity weighted outcome mismatch",
        )
    else:
        checks.require(
            identity.get("applicable") is False,
            "candidate target identity applicability mismatch",
        )
        checks.require(
            identity.get("passed") is False,
            "candidate target identity self-check mismatch",
        )

    gates = readiness.get("readiness")
    checks.require(isinstance(gates, Mapping), "readiness gates missing")
    checks.require(gates.get("input_valid") is True, "input-valid gate mismatch")
    checks.require(
        gates.get("outcome_contract_ready") is True,
        "outcome-contract gate mismatch",
    )
    checks.require(
        gates.get("target_policy_ready") is True,
        "target-policy gate mismatch",
    )
    checks.require(
        gates.get("overlap_ready") is (not expected_blockers),
        "overlap gate mismatch",
    )
    checks.require(
        gates.get("identity_self_check_passed") is identity_invariants_passed,
        "identity gate mismatch",
    )
    for gate in (
        "estimator_validation_ready",
        "ope_ready",
        "causal_uplift_ready",
        "formal_noncombat_rl_training_ready",
        "live_policy_promotion_ready",
    ):
        checks.require(gates.get(gate) is False, f"downstream gate opened: {gate}")
    forbidden_keys = {
        "policy_value",
        "policy_value_estimate",
        "uplift",
        "uplift_estimate",
    }
    checks.require(
        forbidden_keys.isdisjoint(set(_mapping_keys(readiness))),
        "estimate field present in readiness artifact",
    )

    return {
        "schema_version": "noncombat-ope-artifact-audit-v1",
        "passed": True,
        "check_count": checks.count,
        "construction_mode": construction_mode,
        "sample_sha256": sample_sha256,
        "target_file_sha256": target_content_sha256,
        "target_manifest_hash": target_manifest_hash,
        "readiness_file_sha256": hashlib.sha256(readiness_bytes).hexdigest(),
        "decision_count": decision_count,
        "trajectory_count": trajectory_count,
        "nonzero_weight_count": nonzero_count,
        "zero_weight_count": zero_count,
        "effective_sample_size": _exact_record(ess),
        "ess_fraction": _exact_record(ess_fraction),
        "max_normalized_weight": _exact_record(max_normalized_weight),
        "identity_invariants_passed": identity_invariants_passed,
        "overlap_blockers": expected_blockers,
        "downstream_gates_closed": True,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Independently replay one non-combat OPE artifact pair."
    )
    parser.add_argument("--samples", required=True, type=Path)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--readiness", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = verify_artifact_pair(args.samples, args.target, args.readiness)
    except (ArtifactVerificationError, OSError, UnicodeError, ValueError) as exc:
        print(f"noncombat OPE artifact verification error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


def _load_jsonl(path: Path) -> list[Any]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(_strict_json_loads(line))
        except json.JSONDecodeError as exc:
            raise ArtifactVerificationError(
                f"{path}:{line_number}: malformed sample JSON"
            ) from exc
        except _DuplicateJsonKeyError as exc:
            raise ArtifactVerificationError(
                f"{path}:{line_number}: duplicate JSON key: {exc.key}"
            ) from exc
    return rows


def _load_mapping(data: bytes, path: Path) -> dict[str, Any]:
    try:
        value = _strict_json_loads(data.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ArtifactVerificationError(f"{path}: malformed JSON") from exc
    except _DuplicateJsonKeyError as exc:
        raise ArtifactVerificationError(
            f"{path}: duplicate JSON key: {exc.key}"
        ) from exc
    if not isinstance(value, dict):
        raise ArtifactVerificationError(f"{path}: JSON root must be an object")
    return value


def _target_manifest_hash(target: Mapping[str, Any]) -> str:
    payload = deepcopy(dict(target))
    payload["manifest_hash"] = None
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _distribution(
    records: Any,
    checks: _Checks,
    *,
    context: str,
) -> dict[str, Fraction]:
    checks.require(isinstance(records, list) and bool(records), f"{context}: missing distribution")
    result: dict[str, Fraction] = {}
    for record in records:
        checks.require(isinstance(record, Mapping), f"{context}: invalid probability row")
        action_id = record.get("action_id")
        checks.require(
            isinstance(action_id, str) and action_id not in result,
            f"{context}: duplicate or invalid action",
        )
        result[action_id] = _fraction_from_record(
            record,
            checks,
            context=f"{context} action {action_id}",
            probability=True,
        )
    return result


def _fraction_from_record(
    record: Any,
    checks: _Checks,
    *,
    context: str,
    probability: bool = False,
) -> Fraction:
    checks.require(isinstance(record, Mapping), f"{context}: exact record missing")
    numerator = record.get("numerator")
    denominator = record.get("denominator")
    checks.require(
        isinstance(numerator, int) and not isinstance(numerator, bool),
        f"{context}: numerator invalid",
    )
    checks.require(
        isinstance(denominator, int)
        and not isinstance(denominator, bool)
        and denominator > 0,
        f"{context}: denominator invalid",
    )
    if probability:
        checks.require(
            0 <= numerator <= denominator,
            f"{context}: probability outside zero-one",
        )
    value = Fraction(numerator, denominator)
    if "value" in record:
        rendered = record.get("value")
        checks.require(
            isinstance(rendered, (int, float))
            and not isinstance(rendered, bool)
            and math.isfinite(float(rendered)),
            f"{context}: rendered value invalid",
        )
        checks.require(
            float(rendered) == float(value),
            f"{context}: rendered value mismatch",
        )
    return value


def _compare_metric(
    diagnostics: Mapping[str, Any],
    key: str,
    expected: Fraction,
    checks: _Checks,
) -> None:
    actual = _fraction_from_record(
        diagnostics.get(key),
        checks,
        context=f"reported metric {key}",
    )
    checks.require(actual == expected, f"reported metric mismatch: {key}")


def _expected_overlap_blockers(
    *,
    trajectory_count: int,
    nonzero_count: int,
    ess: Fraction,
    ess_fraction: Fraction,
    max_normalized_weight: Fraction,
    victory_unique_count: int,
) -> list[str]:
    blockers = []
    if trajectory_count < 100:
        blockers.append("complete_trajectory_count_below_minimum")
    if nonzero_count < 50:
        blockers.append("nonzero_weight_trajectory_count_below_minimum")
    if ess < 50:
        blockers.append("effective_sample_size_below_minimum")
    if ess_fraction < Fraction(1, 2):
        blockers.append("ess_fraction_below_minimum")
    if max_normalized_weight > Fraction(1, 10):
        blockers.append("max_normalized_weight_above_maximum")
    if victory_unique_count != 2:
        blockers.append("primary_outcome_degenerate")
    return blockers


def _mapping_keys(value: Any):
    if isinstance(value, Mapping):
        for key, nested in value.items():
            yield str(key)
            yield from _mapping_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _mapping_keys(nested)


def _exact_record(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def _strict_json_loads(text: str) -> Any:
    def reject_duplicates(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise _DuplicateJsonKeyError(str(key))
            result[key] = value
        return result

    return json.loads(text, object_pairs_hook=reject_duplicates)


if __name__ == "__main__":
    raise SystemExit(main())
