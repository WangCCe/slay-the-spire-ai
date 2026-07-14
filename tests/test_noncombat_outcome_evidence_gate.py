from dataclasses import replace
from fractions import Fraction
from pathlib import Path

import pytest

from analysis_scripts.noncombat_outcome_evidence_expansion import (
    OutcomeEvidenceGateMetrics,
    OutcomeEvidencePoolError,
    build_outcome_evidence_closeout,
    build_registration,
    evaluate_outcome_evidence_expansion_gate,
    render_outcome_evidence_closeout_json,
    render_outcome_evidence_closeout_markdown,
)


STUDY_ID = "noncombat-outcome-evidence-expansion-20260715"
RUN_LOCK_HASH = "b" * 64
POOL_HASH = "c" * 64
TARGET_HASH = "d" * 64


def _registration(tmp_path):
    return build_registration(
        study_id=STUDY_ID,
        artifact_root=tmp_path / "study",
        repo_root=tmp_path / "repo",
        seed_base=2_026_071_500,
        python_executable=Path(r"D:\anaconda\envs\stsai\python.exe"),
        communication_config_path=tmp_path / "config.properties",
        checkpoint_root=tmp_path / "checkpoints",
    )


def _metrics(**changes):
    metrics = OutcomeEvidenceGateMetrics(
        all_registered_slots_accounted=True,
        global_integrity_stop=False,
        complete_trajectory_count=575,
        category_arm_support={
            "card_reward": {"alternative": 50, "baseline": 50},
            "shop": {"alternative": 50, "baseline": 50},
        },
        nonzero_weight_trajectory_count=288,
        ess_fraction=Fraction(1, 2),
        max_normalized_weight=Fraction(1, 20),
        supported_victory_count=3,
    )
    return replace(metrics, **changes)


def _failed_codes(gate):
    return {
        code
        for code, condition in gate["conditions"].items()
        if condition["passed"] is False
    }


def test_exact_gate_passes_at_every_registered_boundary(tmp_path):
    gate = evaluate_outcome_evidence_expansion_gate(
        _registration(tmp_path),
        _metrics(),
    )

    assert gate["outcome_evidence_expansion_ready"] is True
    assert gate["blockers"] == []
    assert all(row["passed"] is True for row in gate["conditions"].values())


@pytest.mark.parametrize(
    ("field", "below", "at", "condition"),
    [
        (
            "complete_trajectory_count",
            574,
            575,
            "minimum_complete_trajectories",
        ),
        (
            "ess_fraction",
            Fraction(499, 1000),
            Fraction(1, 2),
            "minimum_ess_fraction",
        ),
        (
            "max_normalized_weight",
            Fraction(51, 1000),
            Fraction(1, 20),
            "maximum_normalized_weight",
        ),
        (
            "supported_victory_count",
            2,
            3,
            "minimum_supported_victories",
        ),
    ],
)
def test_exact_gate_rejects_just_beyond_scalar_boundary(
    tmp_path, field, below, at, condition
):
    registration = _registration(tmp_path)
    blocked = evaluate_outcome_evidence_expansion_gate(
        registration,
        _metrics(**{field: below}),
    )
    passing = evaluate_outcome_evidence_expansion_gate(
        registration,
        _metrics(**{field: at}),
    )

    assert condition in _failed_codes(blocked)
    assert condition not in _failed_codes(passing)


@pytest.mark.parametrize("category", ["card_reward", "shop"])
@pytest.mark.parametrize("arm", ["baseline", "alternative"])
def test_exact_gate_requires_50_aggregate_decisions_per_arm(
    tmp_path, category, arm
):
    support = {
        "card_reward": {"alternative": 50, "baseline": 50},
        "shop": {"alternative": 50, "baseline": 50},
    }
    support[category][arm] = 49
    code = f"minimum_{category}_{arm}_decisions"

    blocked = evaluate_outcome_evidence_expansion_gate(
        _registration(tmp_path),
        _metrics(category_arm_support=support),
    )
    support[category][arm] = 50
    passing = evaluate_outcome_evidence_expansion_gate(
        _registration(tmp_path),
        _metrics(category_arm_support=support),
    )

    assert code in _failed_codes(blocked)
    assert code not in _failed_codes(passing)


def test_exact_gate_requires_at_least_half_nonzero_weight_trajectories(tmp_path):
    registration = _registration(tmp_path)
    blocked = evaluate_outcome_evidence_expansion_gate(
        registration,
        _metrics(
            complete_trajectory_count=600,
            nonzero_weight_trajectory_count=299,
        ),
    )
    passing = evaluate_outcome_evidence_expansion_gate(
        registration,
        _metrics(
            complete_trajectory_count=600,
            nonzero_weight_trajectory_count=300,
        ),
    )

    assert "minimum_nonzero_weight_fraction" in _failed_codes(blocked)
    assert "minimum_nonzero_weight_fraction" not in _failed_codes(passing)


def test_closeout_reports_separate_downstream_and_authority_gates(tmp_path):
    registration = _registration(tmp_path)
    slots = [
        {
            "session_id": slot.session_id,
            "slot_number": slot.slot_number,
            "terminal_status": "completed",
        }
        for slot in registration.slots
    ]
    closeout = build_outcome_evidence_closeout(
        registration,
        run_lock_hash=RUN_LOCK_HASH,
        pool_manifest_hash=POOL_HASH,
        target_manifest_hash=TARGET_HASH,
        slot_statuses=slots,
        metrics=_metrics(),
        readiness_artifact={
            "readiness": {
                "outcome_contract_ready": True,
                "overlap_ready": True,
                "target_policy_ready": True,
            }
        },
        estimate_artifact={
            "gates": {
                "ope_estimate_ready": True,
                "policy_comparison_ready": True,
            }
        },
    )

    assert closeout["status"] == "ready"
    assert closeout["gates"] == {
        "causal_uplift_ready": False,
        "dataset_ope_readiness_ready": True,
        "formal_noncombat_rl_training_ready": False,
        "live_policy_promotion_ready": False,
        "ope_estimate_ready": True,
        "outcome_evidence_expansion_ready": True,
        "policy_comparison_ready": True,
        "reward_design_ready": False,
    }
    rendered_json = render_outcome_evidence_closeout_json(closeout)
    rendered_markdown = render_outcome_evidence_closeout_markdown(closeout)
    assert "minimum_supported_victories" in rendered_json
    assert "minimum_supported_victories" in rendered_markdown
    assert "floor_reached" not in rendered_json
    assert "formal_noncombat_rl_training_ready" in rendered_json
    assert f"`{registration.slots[-1].session_id}`" in rendered_markdown
    assert "## Slot status" in rendered_markdown
    assert "## Blockers" in rendered_markdown


def test_closeout_renderers_reject_tampered_gate(tmp_path):
    registration = _registration(tmp_path)
    closeout = build_outcome_evidence_closeout(
        registration,
        run_lock_hash=RUN_LOCK_HASH,
        pool_manifest_hash=POOL_HASH,
        target_manifest_hash=TARGET_HASH,
        slot_statuses=[
            {
                "session_id": slot.session_id,
                "slot_number": slot.slot_number,
                "terminal_status": "completed",
            }
            for slot in registration.slots
        ],
        metrics=_metrics(),
    )
    closeout["gates"]["outcome_evidence_expansion_ready"] = False

    with pytest.raises(OutcomeEvidencePoolError, match="closeout hash"):
        render_outcome_evidence_closeout_json(closeout)


def test_closeout_distinguishes_inconclusive_from_integrity_blocked(tmp_path):
    registration = _registration(tmp_path)
    terminal_slots = [
        {
            "session_id": slot.session_id,
            "slot_number": slot.slot_number,
            "terminal_status": "completed",
        }
        for slot in registration.slots
    ]
    inconclusive = build_outcome_evidence_closeout(
        registration,
        run_lock_hash=RUN_LOCK_HASH,
        pool_manifest_hash=POOL_HASH,
        target_manifest_hash=TARGET_HASH,
        slot_statuses=terminal_slots,
        metrics=_metrics(complete_trajectory_count=574),
    )
    blocked_slots = [
        {
            **slot,
            "terminal_status": (
                "completed" if slot["slot_number"] == 1 else "unlaunched"
            ),
        }
        for slot in terminal_slots
    ]
    blocked = build_outcome_evidence_closeout(
        registration,
        run_lock_hash=RUN_LOCK_HASH,
        pool_manifest_hash=None,
        target_manifest_hash=None,
        slot_statuses=blocked_slots,
        metrics=_metrics(
            all_registered_slots_accounted=False,
            global_integrity_stop=True,
        ),
        integrity_stop_reason="test integrity stop",
    )

    assert inconclusive["status"] == "inconclusive"
    assert blocked["status"] == "blocked"
    assert blocked["gates"]["outcome_evidence_expansion_ready"] is False
    assert blocked["gates"]["formal_noncombat_rl_training_ready"] is False
    assert blocked["gates"]["live_policy_promotion_ready"] is False


def test_global_stop_closeout_rejects_pool_or_ope_artifacts(tmp_path):
    registration = _registration(tmp_path)
    slots = [
        {
            "session_id": slot.session_id,
            "slot_number": slot.slot_number,
            "terminal_status": "unlaunched",
        }
        for slot in registration.slots
    ]

    with pytest.raises(OutcomeEvidencePoolError, match="must not bind"):
        build_outcome_evidence_closeout(
            registration,
            run_lock_hash=RUN_LOCK_HASH,
            pool_manifest_hash=POOL_HASH,
            target_manifest_hash=TARGET_HASH,
            slot_statuses=slots,
            metrics=_metrics(
                all_registered_slots_accounted=False,
                global_integrity_stop=True,
            ),
            readiness_artifact={"readiness": {"overlap_ready": True}},
            estimate_artifact={"gates": {"ope_estimate_ready": True}},
            integrity_stop_reason="source lock drift",
        )
