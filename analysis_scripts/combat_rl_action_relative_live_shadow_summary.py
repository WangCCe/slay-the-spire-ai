"""Summarize one registered action-relative live shadow trace."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import shutil
import sys
from typing import Any, Mapping, Sequence

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from spirecomm.ai.rl.v2.action_relative_live_shadow import (  # noqa: E402
    ActionRelativeShadowRegistration,
    END_TURN_ACTION_INDEX,
    load_live_shadow_registration,
)


def load_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            try:
                event = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"shadow trace line {line_number} is invalid JSON") from exc
            if not isinstance(event, dict):
                raise ValueError(f"shadow trace line {line_number} is not an object")
            events.append(event)
    return events


def summarize_events(
    events: Sequence[Mapping[str, Any]],
    registration: ActionRelativeShadowRegistration,
) -> dict[str, Any]:
    identity_valid = True
    sequence_valid = True
    sessions: dict[str, int] = {}
    decisions: list[Mapping[str, Any]] = []
    error_event_count = 0
    for event in events:
        if (
            event.get("experiment_id") != registration.experiment_id
            or event.get("registration_sha256") != registration.registration_sha256
            or event.get("source_commit") != registration.source_commit
            or event.get("candidate_artifact_sha256")
            != registration.candidate_artifact_sha256
            or event.get("production_parent_checkpoint_sha256")
            != registration.production_parent_checkpoint_sha256
            or event.get("parent_state_dict_sha256")
            != registration.parent_state_dict_sha256
        ):
            identity_valid = False
        event_type = event.get("event_type")
        if event_type == "error":
            error_event_count += 1
            continue
        if event_type != "decision":
            continue
        decisions.append(event)
        session = event.get("session_id")
        sequence = event.get("decision_sequence")
        if not isinstance(session, str) or not isinstance(sequence, int):
            sequence_valid = False
        else:
            expected = sessions.get(session, 0) + 1
            if sequence != expected:
                sequence_valid = False
            sessions[session] = sequence

    eligible = [event for event in decisions if event.get("eligible") is True]
    runtime_error_count = sum(bool(event.get("runtime_error_type")) for event in decisions)
    authority_violation_count = sum(
        event.get("candidate_has_authority") is not False for event in decisions
    )
    interventions = [
        event for event in eligible if event.get("candidate_would_intervene") is True
    ]
    eligible_legality_failures = sum(
        event.get("candidate_action_legal") is not True for event in interventions
    )
    forbidden_failures = sum(
        event.get("candidate_action_forbidden") is not False
        or event.get("candidate_action_index") == END_TURN_ACTION_INDEX
        for event in interventions
    )
    guard_identity_failures = sum(
        event.get("parent_action_index") != END_TURN_ACTION_INDEX
        or event.get("guard_action_index") != event.get("executed_action_index")
        or event.get("guard_action_index") == END_TURN_ACTION_INDEX
        for event in eligible
    )
    ineligible_inference_count = sum(
        event.get("candidate_action_index") is not None
        or event.get("predicted_advantage") is not None
        or event.get("shadow_latency_ms") != 0.0
        for event in decisions
        if event.get("eligible") is not True
    )
    derived_field_failures = 0
    for event in decisions:
        parent = event.get("parent_action_index")
        executed = event.get("executed_action_index")
        encodable = event.get("executed_action_encodable") is True
        legal = event.get("executed_action_legal") is True
        if parent != END_TURN_ACTION_INDEX:
            expected_reason = "parent_not_end_turn"
        elif not encodable:
            expected_reason = "executed_action_unencodable"
        elif not legal:
            expected_reason = "executed_action_illegal"
        elif executed == END_TURN_ACTION_INDEX:
            expected_reason = "guard_not_replaced"
        else:
            expected_reason = ""
        expected_eligible = expected_reason == ""
        if (
            event.get("eligible") is not expected_eligible
            or event.get("support_reason") != expected_reason
            or event.get("guard_action_index")
            != (executed if expected_eligible else None)
        ):
            derived_field_failures += 1
            continue
        candidate = event.get("candidate_action_index")
        intervenes = event.get("candidate_would_intervene") is True
        if expected_eligible and intervenes:
            if (
                not isinstance(candidate, int)
                or isinstance(candidate, bool)
                or candidate == executed
                or event.get("candidate_matches_executed") is not False
            ):
                derived_field_failures += 1
        elif expected_eligible and (
            candidate is not None
            or event.get("candidate_action_legal") is not None
            or event.get("candidate_action_forbidden") is not None
            or event.get("candidate_matches_executed") is not None
        ):
            derived_field_failures += 1
    latencies = np.asarray(
        [float(event["shadow_latency_ms"]) for event in eligible], dtype=np.float64
    )
    finite_latency = bool(np.isfinite(latencies).all())
    p95_latency = float(np.quantile(latencies, 0.95)) if latencies.size else 0.0
    support_reasons: dict[str, int] = {}
    for event in decisions:
        reason = str(event.get("support_reason") or "eligible")
        support_reasons[reason] = support_reasons.get(reason, 0) + 1
    conditions = {
        "trace_identity_valid": identity_valid,
        "decision_sequence_valid": sequence_valid,
        "decision_count_within_budget": len(decisions)
        <= registration.maximum_decision_count,
        "minimum_eligible_count_reached": len(eligible)
        >= registration.minimum_eligible_count,
        "candidate_has_no_authority": authority_violation_count == 0,
        "eligible_candidates_legal": eligible_legality_failures == 0,
        "end_turn_constraint_satisfied": forbidden_failures == 0,
        "eligible_guard_identity_valid": guard_identity_failures == 0,
        "derived_fields_valid": derived_field_failures == 0,
        "ineligible_decisions_not_inferred": ineligible_inference_count == 0,
        "runtime_error_count_zero": runtime_error_count + error_event_count == 0,
        "latency_finite_and_within_ceiling": finite_latency
        and p95_latency <= registration.maximum_p95_latency_ms,
    }
    passed = all(conditions.values())
    return {
        "registration_schema_version": registration.schema_version,
        "inference_device": registration.inference_device,
        "experiment_id": registration.experiment_id,
        "source_commit": registration.source_commit,
        "registration_sha256": registration.registration_sha256,
        "trace_path": str(registration.trace_path),
        "event_count": len(events),
        "decision_count": len(decisions),
        "eligible_count": len(eligible),
        "runtime_error_count": runtime_error_count,
        "error_event_count": error_event_count,
        "candidate_would_intervene_count": len(interventions),
        "candidate_matches_guard_count": sum(
            event.get("candidate_matches_executed") is True for event in eligible
        ),
        "support_reason_counts": dict(sorted(support_reasons.items())),
        "latency": {
            "count": int(latencies.size),
            "mean_ms": float(latencies.mean()) if latencies.size else 0.0,
            "p95_ms": p95_latency,
            "maximum_ms": float(latencies.max()) if latencies.size else 0.0,
        },
        "readiness_conditions": conditions,
        "all_readiness_conditions_passed": passed,
        "decision": (
            "ready_for_separately_registered_matched_live_evaluation"
            if passed
            else "not_ready_for_candidate_action_authority"
        ),
        "authority": {
            "gameplay_quality_claim": False,
            "candidate_action_authority": False,
            "qualification": False,
            "promotion": False,
        },
    }


def _render_summary(report: Mapping[str, Any]) -> str:
    return "\n".join(
        (
            "# Action-Relative Live Shadow Readiness",
            "",
            f"- Registration schema: {report['registration_schema_version']}",
            f"- Inference device: {report['inference_device']}",
            f"- Decisions: {report['decision_count']}",
            f"- Eligible guard replacements: {report['eligible_count']}",
            f"- Candidate intervention intents: {report['candidate_would_intervene_count']}",
            f"- Runtime errors: {report['runtime_error_count'] + report['error_event_count']}",
            f"- Inference p95 ms: {report['latency']['p95_ms']:.6f}",
            f"- Decision: {report['decision']}",
            "",
        )
    )


def run(registration_path: Path, output_dir: Path) -> dict[str, Any]:
    registration = load_live_shadow_registration(
        registration_path, repo_root=REPO_ROOT, require_committed=True
    )
    if not registration.trace_path.is_file():
        raise ValueError("registered action-relative shadow trace is missing")
    output = output_dir.resolve()
    try:
        output.relative_to((REPO_ROOT / "reports").resolve())
    except ValueError as exc:
        raise ValueError("shadow summary output must be inside reports") from exc
    staging = output.with_name(f".{output.name}.staging")
    if output.exists() or staging.exists():
        raise ValueError("shadow summary output or staging already exists")
    report = summarize_events(load_events(registration.trace_path), registration)
    staging.mkdir(parents=True)
    try:
        (staging / "report.json").write_text(
            json.dumps(report, allow_nan=False, indent=2, sort_keys=True) + "\n",
            encoding="ascii",
            newline="\n",
        )
        (staging / "summary.md").write_text(
            _render_summary(report), encoding="ascii", newline="\n"
        )
        os.replace(staging, output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registration", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.registration, args.output_dir)
    print(json.dumps({"decision": report["decision"]}, sort_keys=True))


if __name__ == "__main__":
    main()
