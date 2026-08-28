from __future__ import annotations

from pathlib import Path
import subprocess
import sys

from analysis_scripts.combat_rl_provenance_balanced_objective_ablation import (
    ARMS,
    OPTIMIZER_STEPS,
    _add_batch_stratum_gate,
    _select_objective_recipe,
    _validate_reference_report,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def _arm_result(
    label: str,
    *,
    passed: bool,
    direct_drift: float,
    override_uplift: float,
) -> dict:
    return {
        "label": label,
        "eligibility": {"all_conditions_passed": passed},
        "stratified_gate_metrics": {
            "direct_parent_disagreement": direct_drift,
            "override_executed_label_agreement_uplift": override_uplift,
        },
    }


def test_registered_arm_matrix_is_exact_and_bounded():
    assert OPTIMIZER_STEPS == 64
    assert ARMS == (
        {
            "label": "balanced_anchor",
            "provenance_balanced_anchor": True,
            "direct_only_top_action_margin_guard": False,
            "top_action_margin_guard_weight": 0.0,
            "top_action_margin_guard_cap": 0.1,
        },
        {
            "label": "balanced_anchor_direct_margin",
            "provenance_balanced_anchor": True,
            "direct_only_top_action_margin_guard": True,
            "top_action_margin_guard_weight": 1.0,
            "top_action_margin_guard_cap": 0.1,
        },
    )


def test_batch_stratum_gate_requires_both_strata_on_every_update():
    base = {"metrics_finite": True, "all_conditions_passed": True}
    passed = _add_batch_stratum_gate(
        base,
        training={
            "parent_policy_anchor_direct_count": {"minimum": 20.0},
            "parent_policy_anchor_override_count": {"minimum": 95.0},
        },
    )
    assert passed["every_training_batch_contains_both_provenance_strata"] is True
    assert passed["all_conditions_passed"] is True

    failed = _add_batch_stratum_gate(
        base,
        training={
            "parent_policy_anchor_direct_count": {"minimum": 0.0},
            "parent_policy_anchor_override_count": {"minimum": 128.0},
        },
    )
    assert failed["every_training_batch_contains_both_provenance_strata"] is False
    assert failed["all_conditions_passed"] is False


def test_objective_selection_uses_fixed_direct_override_and_simplicity_order():
    only_guarded_passes = _select_objective_recipe(
        (
            _arm_result(
                "balanced_anchor", passed=False, direct_drift=0.12, override_uplift=0.3
            ),
            _arm_result(
                "balanced_anchor_direct_margin",
                passed=True,
                direct_drift=0.08,
                override_uplift=0.2,
            ),
        )
    )
    assert only_guarded_passes["recommended_recipe"] == (
        "balanced_anchor_direct_margin"
    )

    lower_direct_wins = _select_objective_recipe(
        (
            _arm_result(
                "balanced_anchor", passed=True, direct_drift=0.08, override_uplift=0.3
            ),
            _arm_result(
                "balanced_anchor_direct_margin",
                passed=True,
                direct_drift=0.07,
                override_uplift=0.2,
            ),
        )
    )
    assert lower_direct_wins["recommended_recipe"] == (
        "balanced_anchor_direct_margin"
    )

    simple_exact_tie = _select_objective_recipe(
        (
            _arm_result(
                "balanced_anchor", passed=True, direct_drift=0.07, override_uplift=0.2
            ),
            _arm_result(
                "balanced_anchor_direct_margin",
                passed=True,
                direct_drift=0.07,
                override_uplift=0.2,
            ),
        )
    )
    assert simple_exact_tie["recommended_recipe"] == "balanced_anchor"

    none = _select_objective_recipe(
        (
            _arm_result(
                "balanced_anchor", passed=False, direct_drift=0.2, override_uplift=0.3
            ),
            _arm_result(
                "balanced_anchor_direct_margin",
                passed=False,
                direct_drift=0.11,
                override_uplift=0.3,
            ),
        )
    )
    assert none["recommended_recipe"] is None
    assert none["next_step"] == "investigate_residual_or_separate_head"


def test_reference_report_validation_fails_closed():
    reference = {
        "decision": "development_candidate_not_eligible_no_same_corpus_tuning",
        "source_commit": "ef661a471924ad7e55ec5ed35cbfad48c7e62876",
        "input": {
            "sha256": "606727df27dd82ac825767097b71f07d6aa39ad37e0ea5d5d432e88c9288c28f"
        },
        "candidate": {
            "sha256": "8d82e0ee5486daeb963d524a6e34b599716b966976f1406e4220973760df6ccf"
        },
        "recipe": {"optimizer_steps": 64},
    }
    _validate_reference_report(reference)

    changed = dict(reference)
    changed["decision"] = "eligible_for_separate_fresh_holdout_only"
    try:
        _validate_reference_report(changed)
    except ValueError as exc:
        assert "reference decision" in str(exc)
    else:
        raise AssertionError("changed reference decision was accepted")


def test_isolated_direct_entrypoint_bootstraps_repo_root():
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            str(
                REPO_ROOT
                / "analysis_scripts"
                / "combat_rl_provenance_balanced_objective_ablation.py"
            ),
            "--help",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "--registration" in result.stdout
