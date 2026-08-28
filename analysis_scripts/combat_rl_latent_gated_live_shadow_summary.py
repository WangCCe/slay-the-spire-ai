"""Summarize a bounded latent-gated combat live-shadow trace."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

import numpy as np

from spirecomm.ai.rl.v2.latent_gated_live_shadow import (
    TRACE_SCHEMA_VERSION,
    LiveShadowRegistration,
    _require_source_binding,
    load_live_shadow_registration,
)


READY_DECISION = "eligible_for_separately_bounded_matched_gameplay_evaluation"
NOT_READY_DECISION = "not_ready_for_matched_gameplay_evaluation"


def _read_events(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    events: list[dict[str, Any]] = []
    errors: list[str] = []
    if not path.is_file():
        return events, [f"trace is missing: {path}"]
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"line {line_number} is invalid JSON: {exc.msg}")
                continue
            if not isinstance(event, dict):
                errors.append(f"line {line_number} is not a JSON object")
                continue
            event["_line_number"] = line_number
            events.append(event)
    return events, errors


def _identity_errors(
    events: Iterable[Mapping[str, Any]], registration: LiveShadowRegistration
) -> list[str]:
    expected = {
        "trace_schema_version": TRACE_SCHEMA_VERSION,
        "experiment_id": registration.experiment_id,
        "source_commit": registration.source_commit,
        "registration_sha256": registration.registration_sha256,
        "candidate_artifact_sha256": registration.candidate_artifact_sha256,
        "production_parent_checkpoint_sha256": (
            registration.production_parent_checkpoint_sha256
        ),
        "parent_state_dict_sha256": registration.parent_state_dict_sha256,
    }
    errors = []
    for event in events:
        line_number = event.get("_line_number", "?")
        if event.get("event_type") not in {
            "decision",
            "transient_discard",
            "error",
        }:
            errors.append(f"line {line_number} has an unsupported event type")
        if not isinstance(event.get("session_id"), str) or not event.get("session_id"):
            errors.append(f"line {line_number} has no session identity")
        for field, expected_value in expected.items():
            if event.get(field) != expected_value:
                errors.append(f"line {line_number} {field} differs")
    return errors


def _decision_schema_errors(
    decisions: Iterable[Mapping[str, Any]],
) -> list[str]:
    required = {
        "state_sha256",
        "timestamp",
        "parent_action_index",
        "shadow_parent_action_index",
        "correction_action_index",
        "candidate_action_index",
        "executed_action_index",
        "legal_action_indices",
        "gate_probability",
        "gate_threshold",
        "gate_open",
        "candidate_action_legal",
        "parent_parity",
        "executed_action_encodable",
        "executed_action_legal",
        "proposal_changed",
        "candidate_matches_executed",
        "correction_matches_executed",
        "shadow_latency_ms",
    }
    errors = []
    for event in decisions:
        line_number = event.get("_line_number", "?")
        missing = sorted(required.difference(event))
        if missing:
            errors.append(f"line {line_number} decision fields are missing: {missing}")
            continue
        state_sha = event["state_sha256"]
        if not isinstance(state_sha, str) or len(state_sha) != 64 or any(
            character not in "0123456789abcdef" for character in state_sha.lower()
        ):
            errors.append(f"line {line_number} state identity is invalid")
        if not isinstance(event["timestamp"], str) or not event["timestamp"]:
            errors.append(f"line {line_number} timestamp is invalid")
        legal = event["legal_action_indices"]
        if (
            not isinstance(legal, list)
            or not legal
            or any(
                not isinstance(index, int) or isinstance(index, bool) or index < 0
                for index in legal
            )
            or len(set(legal)) != len(legal)
        ):
            errors.append(f"line {line_number} legal action indices are invalid")
            continue
        action_fields = (
            "parent_action_index",
            "shadow_parent_action_index",
            "correction_action_index",
            "candidate_action_index",
        )
        if any(
            not isinstance(event[field], int) or isinstance(event[field], bool)
            for field in action_fields
        ):
            errors.append(f"line {line_number} action index is invalid")
            continue
        parent = event["parent_action_index"]
        shadow_parent = event["shadow_parent_action_index"]
        correction = event["correction_action_index"]
        candidate = event["candidate_action_index"]
        if any(index not in legal for index in (parent, shadow_parent, correction, candidate)):
            errors.append(f"line {line_number} model action is outside the legal set")
        probability = event["gate_probability"]
        threshold = event["gate_threshold"]
        if (
            not isinstance(probability, (int, float))
            or isinstance(probability, bool)
            or not np.isfinite(float(probability))
            or not 0.0 <= float(probability) <= 1.0
            or not isinstance(threshold, (int, float))
            or isinstance(threshold, bool)
            or not np.isfinite(float(threshold))
            or not 0.0 < float(threshold) < 1.0
        ):
            errors.append(f"line {line_number} gate telemetry is invalid")
        elif event["gate_open"] is not (
            float(probability) >= float(threshold)
        ):
            errors.append(f"line {line_number} gate-open relation differs")
        booleans = (
            "gate_open",
            "candidate_action_legal",
            "parent_parity",
            "executed_action_encodable",
            "executed_action_legal",
            "proposal_changed",
            "candidate_matches_executed",
            "correction_matches_executed",
        )
        if any(not isinstance(event[field], bool) for field in booleans):
            errors.append(f"line {line_number} derived flag is not boolean")
            continue
        executed = event["executed_action_index"]
        executed_is_int = isinstance(executed, int) and not isinstance(executed, bool)
        if event["executed_action_encodable"] != executed_is_int:
            errors.append(f"line {line_number} executed encodability differs")
        executed_legal = executed_is_int and executed in legal
        relations = {
            "candidate_action_legal": candidate in legal,
            "parent_parity": shadow_parent == parent,
            "executed_action_legal": executed_legal,
            "proposal_changed": executed != parent,
            "candidate_matches_executed": executed == candidate,
            "correction_matches_executed": executed == correction,
        }
        for field, expected in relations.items():
            if event[field] != expected:
                errors.append(f"line {line_number} {field} relation differs")
        latency = event["shadow_latency_ms"]
        if (
            not isinstance(latency, (int, float))
            or isinstance(latency, bool)
            or not np.isfinite(float(latency))
            or float(latency) < 0.0
        ):
            errors.append(f"line {line_number} inference latency is invalid")
    return errors


def _transient_schema_errors(
    transients: Iterable[Mapping[str, Any]],
) -> list[str]:
    required = {
        "state_sha256",
        "timestamp",
        "parent_action_index",
        "shadow_parent_action_index",
        "correction_action_index",
        "candidate_action_index",
        "legal_action_indices",
        "gate_probability",
        "gate_threshold",
        "gate_open",
        "candidate_action_legal",
        "parent_parity",
        "shadow_latency_ms",
        "discard_reason",
    }
    errors = []
    for event in transients:
        line_number = event.get("_line_number", "?")
        missing = sorted(required.difference(event))
        if missing:
            errors.append(
                f"line {line_number} transient fields are missing: {missing}"
            )
            continue
        state_sha = event["state_sha256"]
        if not isinstance(state_sha, str) or len(state_sha) != 64 or any(
            character not in "0123456789abcdef"
            for character in state_sha.lower()
        ):
            errors.append(f"line {line_number} transient state identity is invalid")
        if not isinstance(event["timestamp"], str) or not event["timestamp"]:
            errors.append(f"line {line_number} transient timestamp is invalid")
        legal = event["legal_action_indices"]
        if (
            not isinstance(legal, list)
            or not legal
            or any(
                not isinstance(index, int) or isinstance(index, bool) or index < 0
                for index in legal
            )
            or len(set(legal)) != len(legal)
        ):
            errors.append(
                f"line {line_number} transient legal action indices are invalid"
            )
            continue
        action_fields = (
            "parent_action_index",
            "shadow_parent_action_index",
            "correction_action_index",
            "candidate_action_index",
        )
        if any(
            not isinstance(event[field], int) or isinstance(event[field], bool)
            for field in action_fields
        ):
            errors.append(f"line {line_number} transient action index is invalid")
            continue
        parent = event["parent_action_index"]
        shadow_parent = event["shadow_parent_action_index"]
        correction = event["correction_action_index"]
        candidate = event["candidate_action_index"]
        if any(
            index not in legal
            for index in (parent, shadow_parent, correction, candidate)
        ):
            errors.append(
                f"line {line_number} transient model action is outside the legal set"
            )
        probability = event["gate_probability"]
        threshold = event["gate_threshold"]
        if (
            not isinstance(probability, (int, float))
            or isinstance(probability, bool)
            or not np.isfinite(float(probability))
            or not 0.0 <= float(probability) <= 1.0
            or not isinstance(threshold, (int, float))
            or isinstance(threshold, bool)
            or not np.isfinite(float(threshold))
            or not 0.0 < float(threshold) < 1.0
        ):
            errors.append(f"line {line_number} transient gate telemetry is invalid")
        elif event["gate_open"] is not (
            float(probability) >= float(threshold)
        ):
            errors.append(f"line {line_number} transient gate-open relation differs")
        for field, expected in {
            "candidate_action_legal": candidate in legal,
            "parent_parity": shadow_parent == parent,
        }.items():
            if not isinstance(event[field], bool):
                errors.append(
                    f"line {line_number} transient {field} is not boolean"
                )
            elif event[field] != expected:
                errors.append(
                    f"line {line_number} transient {field} relation differs"
                )
        latency = event["shadow_latency_ms"]
        if (
            not isinstance(latency, (int, float))
            or isinstance(latency, bool)
            or not np.isfinite(float(latency))
            or float(latency) < 0.0
        ):
            errors.append(f"line {line_number} transient latency is invalid")
        if (
            not isinstance(event["discard_reason"], str)
            or not event["discard_reason"]
        ):
            errors.append(f"line {line_number} transient reason is invalid")
    return errors


def _sequence_errors(events: Iterable[Mapping[str, Any]]) -> list[str]:
    sessions: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for event in events:
        session = event.get("session_id")
        if isinstance(session, str) and session:
            sessions[session].append(event)
    errors = []
    for session, session_events in sessions.items():
        observed_events = [event.get("event_sequence") for event in session_events]
        if observed_events != list(range(1, len(session_events) + 1)):
            errors.append(f"session {session} event sequence is not contiguous")
        decisions = [
            event for event in session_events if event.get("event_type") == "decision"
        ]
        observed_decisions = [event.get("decision_sequence") for event in decisions]
        if observed_decisions != list(range(1, len(decisions) + 1)):
            errors.append(f"session {session} decision sequence is not contiguous")
    return errors


def _share(values: Iterable[bool]) -> float:
    observed = list(values)
    if not observed:
        return 0.0
    return sum(bool(value) for value in observed) / len(observed)


def _latency_metrics(decisions: list[Mapping[str, Any]]) -> dict[str, Optional[float]]:
    latencies = []
    for event in decisions:
        value = event.get("shadow_latency_ms")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            value = float(value)
            if np.isfinite(value) and value >= 0.0:
                latencies.append(value)
    if len(latencies) != len(decisions) or not latencies:
        return {
            "minimum_shadow_latency_ms": None,
            "p50_shadow_latency_ms": None,
            "p95_shadow_latency_ms": None,
            "maximum_shadow_latency_ms": None,
        }
    return {
        "minimum_shadow_latency_ms": min(latencies),
        "p50_shadow_latency_ms": float(np.percentile(latencies, 50)),
        "p95_shadow_latency_ms": float(np.percentile(latencies, 95)),
        "maximum_shadow_latency_ms": max(latencies),
    }


def _segment_metrics(decisions: list[Mapping[str, Any]]) -> dict[str, Any]:
    segments: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for event in decisions:
        key = "act={}|room={}".format(
            event.get("act"), event.get("room_type", "")
        )
        segments[key].append(event)
    return {
        key: {
            "decision_count": len(rows),
            "gate_open_share": _share(row.get("gate_open") is True for row in rows),
            "candidate_parent_disagreement_share": _share(
                row.get("candidate_action_index") != row.get("parent_action_index")
                for row in rows
            ),
            "proposal_changed_share": _share(
                row.get("proposal_changed") is True for row in rows
            ),
            "candidate_matches_executed_share": _share(
                row.get("candidate_matches_executed") is True for row in rows
            ),
        }
        for key, rows in sorted(segments.items())
    }


def _write_atomic_json(path: Path, payload: Mapping[str, Any], reports_root: Path) -> None:
    target = path.resolve()
    try:
        target.relative_to(reports_root.resolve())
    except ValueError as exc:
        raise ValueError("live shadow summary output must be inside reports") from exc
    if target.suffix.lower() != ".json":
        raise ValueError("live shadow summary output must be JSON")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    try:
        temporary.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, target)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def summarize_live_shadow_trace(
    registration_path: str | Path,
    *,
    repo_root: str | Path,
    output_path: Optional[str | Path] = None,
    require_committed_registration: bool = True,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    registration = load_live_shadow_registration(
        registration_path,
        repo_root=root,
        require_committed=require_committed_registration,
    )
    if require_committed_registration:
        _require_source_binding(registration.source_commit, root)
    events, parse_errors = _read_events(registration.trace_path)
    identity_errors = _identity_errors(events, registration)
    sequence_errors = _sequence_errors(events)
    decisions = [event for event in events if event.get("event_type") == "decision"]
    transients = [
        event
        for event in events
        if event.get("event_type") == "transient_discard"
    ]
    proposals = decisions + transients
    event_schema_errors = _decision_schema_errors(decisions)
    event_schema_errors.extend(_transient_schema_errors(transients))
    error_events = [event for event in events if event.get("event_type") == "error"]
    latency = _latency_metrics(proposals)
    p95_latency = latency["p95_shadow_latency_ms"]
    criteria = {
        "identity_valid": not parse_errors and not identity_errors,
        "event_schema_valid": not event_schema_errors,
        "sequence_contiguous": not sequence_errors,
        "minimum_decision_count_met": (
            len(decisions) >= registration.minimum_decision_count
        ),
        "within_decision_budget": (
            len(decisions) <= registration.maximum_decision_count
        ),
        "all_parent_actions_match": bool(proposals)
        and all(event.get("parent_parity") is True for event in proposals),
        "all_candidate_actions_legal": bool(proposals)
        and all(
            event.get("candidate_action_legal") is True for event in proposals
        ),
        "all_executed_actions_legal": bool(decisions)
        and all(
            event.get("executed_action_encodable") is True
            and event.get("executed_action_legal") is True
            for event in decisions
        ),
        "zero_error_events": not error_events,
        "p95_latency_within_ceiling": p95_latency is not None
        and p95_latency <= registration.maximum_p95_latency_ms,
    }
    criteria["all_conditions_passed"] = all(criteria.values())
    metrics = {
        "event_count": len(events),
        "proposal_count": len(proposals),
        "transient_discard_count": len(transients),
        "session_count": len(
            {
                event.get("session_id")
                for event in events
                if isinstance(event.get("session_id"), str)
            }
        ),
        "decision_count": len(decisions),
        "error_event_count": len(error_events),
        "parent_parity_share": _share(
            event.get("parent_parity") is True for event in proposals
        ),
        "candidate_legal_share": _share(
            event.get("candidate_action_legal") is True for event in proposals
        ),
        "executed_legal_share": _share(
            event.get("executed_action_encodable") is True
            and event.get("executed_action_legal") is True
            for event in decisions
        ),
        "gate_open_share": _share(
            event.get("gate_open") is True for event in decisions
        ),
        "candidate_parent_disagreement_share": _share(
            event.get("candidate_action_index") != event.get("parent_action_index")
            for event in decisions
        ),
        "proposal_changed_share": _share(
            event.get("proposal_changed") is True for event in decisions
        ),
        "candidate_matches_executed_share": _share(
            event.get("candidate_matches_executed") is True for event in decisions
        ),
        **latency,
    }
    report = {
        "schema_version": 1,
        "experiment_id": registration.experiment_id,
        "decision": READY_DECISION
        if criteria["all_conditions_passed"]
        else NOT_READY_DECISION,
        "registration": {
            "path": str(registration.registration_path),
            "sha256": registration.registration_sha256,
        },
        "trace": {
            "path": str(registration.trace_path),
            "parse_errors": parse_errors,
            "identity_errors": identity_errors,
            "sequence_errors": sequence_errors,
            "event_schema_errors": event_schema_errors,
        },
        "bindings": {
            "source_commit": registration.source_commit,
            "candidate_artifact_sha256": (
                registration.candidate_artifact_sha256
            ),
            "production_parent_checkpoint_sha256": (
                registration.production_parent_checkpoint_sha256
            ),
            "parent_state_dict_sha256": registration.parent_state_dict_sha256,
        },
        "registered_gates": {
            "minimum_decision_count": registration.minimum_decision_count,
            "maximum_decision_count": registration.maximum_decision_count,
            "maximum_p95_latency_ms": registration.maximum_p95_latency_ms,
            "latency_scope": "adapter_inference_only",
        },
        "criteria": criteria,
        "metrics": metrics,
        "segments": _segment_metrics(decisions),
        "authority": {
            "candidate_action_takeover": False,
            "gameplay_quality_claim": False,
            "online_training": False,
            "promotion": False,
            "matched_gameplay_evaluation": bool(
                criteria["all_conditions_passed"]
            ),
        },
        "limitations": [
            "Shadow telemetry measures runtime callability and guard-action agreement, not policy quality.",
            "The latency gate covers adapter inference only; full CommunicationMod delay must be reconciled from live logs.",
            "Transient WaitAction control commands are audited separately and do not consume the policy-decision budget.",
            "A hard process stop between proposal and commit can omit one pending decision; run and log reconciliation remains mandatory.",
            "A separately bounded matched gameplay evaluation is required before any promotion decision.",
        ],
    }
    if output_path is not None:
        _write_atomic_json(Path(output_path), report, root / "reports")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registration", required=True)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--output")
    parser.add_argument("--allow-uncommitted-registration", action="store_true")
    args = parser.parse_args()
    report = summarize_live_shadow_trace(
        args.registration,
        repo_root=args.repo_root,
        output_path=args.output,
        require_committed_registration=not args.allow_uncommitted_registration,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["criteria"]["all_conditions_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
