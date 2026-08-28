from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from analysis_scripts.combat_rl_action_relative_live_shadow_summary import (
    _render_summary,
    summarize_events,
)


def _registration():
    return SimpleNamespace(
        schema_version=2,
        inference_device="cpu",
        experiment_id="shadow-fixture",
        source_commit="a" * 40,
        registration_sha256="b" * 64,
        candidate_artifact_sha256="c" * 64,
        production_parent_checkpoint_sha256="d" * 64,
        parent_state_dict_sha256="e" * 64,
        trace_path=Path("trace.jsonl"),
        maximum_decision_count=2,
        minimum_eligible_count=1,
        maximum_p95_latency_ms=20.0,
    )


def _event(**overrides):
    event = {
        "event_type": "decision",
        "experiment_id": "shadow-fixture",
        "source_commit": "a" * 40,
        "registration_sha256": "b" * 64,
        "candidate_artifact_sha256": "c" * 64,
        "production_parent_checkpoint_sha256": "d" * 64,
        "parent_state_dict_sha256": "e" * 64,
        "session_id": "session-1",
        "decision_sequence": 1,
        "eligible": True,
        "parent_action_index": 90,
        "guard_action_index": 1,
        "executed_action_index": 1,
        "executed_action_encodable": True,
        "executed_action_legal": True,
        "candidate_action_index": 2,
        "candidate_action_legal": True,
        "candidate_action_forbidden": False,
        "candidate_would_intervene": True,
        "candidate_matches_executed": False,
        "candidate_has_authority": False,
        "support_reason": "",
        "runtime_error_type": "",
        "shadow_latency_ms": 3.0,
    }
    event.update(overrides)
    return event


def test_readiness_passes_only_for_neutral_legal_supported_trace():
    report = summarize_events([_event()], _registration())
    assert report["all_readiness_conditions_passed"] is True
    assert report["registration_schema_version"] == 2
    assert report["inference_device"] == "cpu"
    summary = _render_summary(report)
    assert "Registration schema: 2" in summary
    assert "Inference device: cpu" in summary
    assert report["eligible_count"] == 1
    assert report["decision"] == (
        "ready_for_separately_registered_matched_live_evaluation"
    )

    failed = summarize_events(
        [_event(candidate_has_authority=True, candidate_action_index=90)],
        _registration(),
    )
    assert failed["all_readiness_conditions_passed"] is False
    assert failed["readiness_conditions"]["candidate_has_no_authority"] is False
    assert failed["readiness_conditions"]["end_turn_constraint_satisfied"] is False


def test_ineligible_decision_must_not_contain_candidate_inference():
    event = _event(
        eligible=False,
        parent_action_index=2,
        guard_action_index=None,
        support_reason="parent_not_end_turn",
        candidate_action_index=None,
        candidate_action_legal=None,
        candidate_action_forbidden=None,
        candidate_would_intervene=False,
        candidate_matches_executed=None,
        shadow_latency_ms=0.0,
    )
    report = summarize_events([event], _registration())
    assert report["readiness_conditions"]["ineligible_decisions_not_inferred"] is True
    assert report["readiness_conditions"]["derived_fields_valid"] is True
    assert report["readiness_conditions"]["minimum_eligible_count_reached"] is False


def test_abstention_is_valid_but_identity_or_derived_drift_fails():
    abstention = _event(
        candidate_action_index=None,
        candidate_action_legal=None,
        candidate_action_forbidden=None,
        candidate_would_intervene=False,
        candidate_matches_executed=None,
        predicted_advantage=0.1,
    )
    report = summarize_events([abstention], _registration())
    assert report["all_readiness_conditions_passed"] is True

    identity_drift = dict(abstention, candidate_artifact_sha256="f" * 64)
    report = summarize_events([identity_drift], _registration())
    assert report["readiness_conditions"]["trace_identity_valid"] is False

    derived_drift = dict(abstention, support_reason="guard_not_replaced")
    report = summarize_events([derived_drift], _registration())
    assert report["readiness_conditions"]["derived_fields_valid"] is False
