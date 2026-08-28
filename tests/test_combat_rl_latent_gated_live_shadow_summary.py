from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from analysis_scripts.combat_rl_latent_gated_live_shadow_summary import (
    summarize_live_shadow_trace,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path: Path, *, minimum=2, maximum=3, latency=50.0):
    reports = tmp_path / "reports" / "shadow"
    reports.mkdir(parents=True)
    candidate = tmp_path / "candidate.pth"
    checkpoint = tmp_path / "parent.pth"
    candidate.write_bytes(b"candidate")
    checkpoint.write_bytes(b"parent")
    trace = reports / "trace.jsonl"
    registration = {
        "schema_version": 1,
        "experiment_id": "summary-fixture",
        "mode": "shadow",
        "source_commit": "c" * 40,
        "candidate_artifact": {
            "path": str(candidate),
            "sha256": _sha256(candidate),
            "parent_checkpoint_sha256": "a" * 64,
        },
        "production_parent_checkpoint": {
            "path": str(checkpoint),
            "sha256": _sha256(checkpoint),
        },
        "parent_state_dict_sha256": "b" * 64,
        "trace_path": str(trace),
        "maximum_decision_count": maximum,
        "readiness_gates": {
            "minimum_decision_count": minimum,
            "maximum_p95_latency_ms": latency,
        },
    }
    registration_path = tmp_path / "registration.json"
    registration_path.write_text(
        json.dumps(registration, sort_keys=True), encoding="utf-8"
    )
    registration_sha = _sha256(registration_path)

    def decision(sequence, *, latency_ms=10.0, **overrides):
        event = {
            "trace_schema_version": 1,
            "event_type": "decision",
            "experiment_id": "summary-fixture",
            "session_id": "session-a",
            "source_commit": "c" * 40,
            "registration_sha256": registration_sha,
            "candidate_artifact_sha256": _sha256(candidate),
            "production_parent_checkpoint_sha256": _sha256(checkpoint),
            "parent_state_dict_sha256": "b" * 64,
            "state_sha256": "d" * 64,
            "event_sequence": sequence,
            "decision_sequence": sequence,
            "parent_action_index": 0,
            "shadow_parent_action_index": 0,
            "candidate_action_index": 1,
            "correction_action_index": 1,
            "executed_action_index": 1,
            "legal_action_indices": [0, 1],
            "gate_probability": 0.9,
            "gate_threshold": 0.5,
            "gate_open": True,
            "candidate_action_legal": True,
            "executed_action_encodable": True,
            "executed_action_legal": True,
            "parent_parity": True,
            "proposal_changed": True,
            "candidate_matches_executed": True,
            "correction_matches_executed": True,
            "shadow_latency_ms": latency_ms,
            "act": 1,
            "floor": 7,
            "room_type": "MonsterRoom",
            "timestamp": "2026-08-28T08:00:00.000Z",
        }
        event.update(overrides)
        return event

    return registration_path, trace, decision


def _write(trace: Path, events):
    trace.write_text(
        "".join(json.dumps(event, sort_keys=True) + "\n" for event in events),
        encoding="utf-8",
    )


def _summarize(tmp_path, registration_path):
    return summarize_live_shadow_trace(
        registration_path,
        repo_root=tmp_path,
        require_committed_registration=False,
    )


def test_summary_marks_complete_healthy_trace_ready(tmp_path):
    registration, trace, decision = _fixture(tmp_path)
    _write(trace, [decision(1, latency_ms=10.0), decision(2, latency_ms=20.0)])

    report = _summarize(tmp_path, registration)

    assert report["decision"] == (
        "eligible_for_separately_bounded_matched_gameplay_evaluation"
    )
    assert report["criteria"]["all_conditions_passed"] is True
    assert report["metrics"]["decision_count"] == 2
    assert report["metrics"]["parent_parity_share"] == 1.0
    assert report["metrics"]["candidate_legal_share"] == 1.0
    assert report["metrics"]["candidate_matches_executed_share"] == 1.0
    assert report["metrics"]["p95_shadow_latency_ms"] == pytest.approx(19.5)
    assert report["authority"]["candidate_action_takeover"] is False


def test_summary_audits_transient_wait_without_counting_a_policy_decision(
    tmp_path,
):
    registration, trace, decision = _fixture(tmp_path)
    transient = decision(1)
    transient["event_type"] = "transient_discard"
    transient["discard_reason"] = "wait_action"
    transient.pop("decision_sequence")
    for field in (
        "executed_action_index",
        "executed_action_encodable",
        "executed_action_legal",
        "proposal_changed",
        "candidate_matches_executed",
        "correction_matches_executed",
    ):
        transient.pop(field)
    _write(
        trace,
        [
            transient,
            decision(2, decision_sequence=1),
            decision(3, decision_sequence=2),
        ],
    )

    report = _summarize(tmp_path, registration)

    assert report["criteria"]["all_conditions_passed"] is True
    assert report["metrics"]["event_count"] == 3
    assert report["metrics"]["proposal_count"] == 3
    assert report["metrics"]["decision_count"] == 2
    assert report["metrics"]["transient_discard_count"] == 1


@pytest.mark.parametrize(
    ("case", "criterion"),
    [
        ("identity", "identity_valid"),
        ("derived", "event_schema_valid"),
        ("missing", "event_schema_valid"),
        ("sequence", "sequence_contiguous"),
        ("minimum", "minimum_decision_count_met"),
        ("parity", "all_parent_actions_match"),
        ("illegal", "all_candidate_actions_legal"),
        ("executed", "all_executed_actions_legal"),
        ("error", "zero_error_events"),
        ("budget", "within_decision_budget"),
        ("latency", "p95_latency_within_ceiling"),
    ],
)
def test_summary_rejects_each_readiness_failure(tmp_path, case, criterion):
    minimum = 3 if case == "minimum" else 2
    maximum = 1 if case == "budget" else 3
    registration, trace, decision = _fixture(
        tmp_path, minimum=minimum, maximum=max(maximum, minimum)
    )
    first = decision(1, latency_ms=100.0 if case == "latency" else 10.0)
    second = decision(2, latency_ms=100.0 if case == "latency" else 20.0)
    events = [first, second]
    if case == "identity":
        second["candidate_artifact_sha256"] = "f" * 64
    elif case == "derived":
        second["shadow_parent_action_index"] = 2
    elif case == "missing":
        second.pop("state_sha256")
    elif case == "sequence":
        second["event_sequence"] = 3
    elif case == "parity":
        second["parent_parity"] = False
    elif case == "illegal":
        second["candidate_action_legal"] = False
    elif case == "executed":
        second["executed_action_encodable"] = False
        second["executed_action_legal"] = False
    elif case == "error":
        second = dict(second)
        second["event_type"] = "error"
        second.pop("decision_sequence")
        events.append(second)
    elif case == "budget":
        payload = json.loads(registration.read_text(encoding="utf-8"))
        payload["maximum_decision_count"] = 1
        payload["readiness_gates"]["minimum_decision_count"] = 1
        registration.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        registration_sha = _sha256(registration)
        for event in events:
            event["registration_sha256"] = registration_sha
    _write(trace, events)

    report = _summarize(tmp_path, registration)

    assert report["decision"] == "not_ready_for_matched_gameplay_evaluation"
    assert report["criteria"][criterion] is False
    assert report["criteria"]["all_conditions_passed"] is False


def test_summary_writes_atomic_json_report_inside_reports(tmp_path):
    registration, trace, decision = _fixture(tmp_path)
    _write(trace, [decision(1), decision(2)])
    output = tmp_path / "reports" / "shadow" / "report.json"

    expected = summarize_live_shadow_trace(
        registration,
        repo_root=tmp_path,
        output_path=output,
        require_committed_registration=False,
    )

    assert json.loads(output.read_text(encoding="utf-8")) == expected
    assert not output.with_suffix(".json.tmp").exists()
