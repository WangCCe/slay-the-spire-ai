from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from analysis_scripts.combat_rl_action_relative_expanded_item_semantic_fit import (
    FIXED_INPUTS,
    FIXED_OFFLINE_GATES,
    FIXED_RECIPE,
    RESULT_AUTHORITY,
    apply_offline_gates,
    validate_corpus_report,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def _passing_metrics() -> dict:
    return {
        "selection": {
            "intervention_count": 30,
            "intervention_precision": 0.65,
            "mean_selected_true_advantage": FIXED_OFFLINE_GATES[
                "minimum_mean_selected_true_advantage_exclusive"
            ]
            + 1e-6,
            "severe_harm_count": 0,
            "illegal_action_count": 0,
            "forbidden_action_selection_count": 0,
        },
        "ranking": {
            "mean_policy_regret": FIXED_OFFLINE_GATES[
                "maximum_mean_policy_regret_exclusive"
            ]
            - 1e-6
        },
    }


def test_expanded_recipe_binds_disjoint_fit_calibration_and_fresh_cohorts():
    assert FIXED_RECIPE["include_item_semantics"] is True
    assert FIXED_RECIPE["updates"] == 4096
    assert (
        FIXED_RECIPE["fit_seed_first"],
        FIXED_RECIPE["fit_seed_last"],
    ) == (264000, 264767)
    assert (
        FIXED_RECIPE["calibration_seed_first"],
        FIXED_RECIPE["calibration_seed_last"],
    ) == (264768, 265023)
    assert FIXED_RECIPE["fresh_evaluation_seed_first"] == 266000
    assert FIXED_RECIPE["fresh_evaluation_seed_last"] == 266255


def test_expanded_fit_binds_published_corpus_hashes_and_original_offline_gates():
    assert FIXED_INPUTS["train_corpus"]["sha256"] == (
        "90f3e83763f2591065380e89b24ebbedc7bbc3ef529a749b0cbb54a2dab2fa1f"
    )
    assert FIXED_INPUTS["evaluation_corpus"]["sha256"] == (
        "028d51871b12fd509b87b6d45adb161b399a29c34782b30b28f66c0a97e48e58"
    )
    assert FIXED_OFFLINE_GATES == {
        "minimum_intervention_count": 30,
        "minimum_intervention_precision": 0.65,
        "minimum_mean_selected_true_advantage_exclusive": 0.18881003558635712,
        "maximum_mean_policy_regret_exclusive": 3.1811342239379883,
        "severe_harm_floor": -0.5,
        "maximum_severe_harm_count": 0,
        "illegal_action_count_zero": True,
        "forbidden_action_selection_count_zero": True,
    }


def test_expanded_corpus_report_must_match_fixed_cohort_and_authority():
    report = json.loads(
        (
            REPO_ROOT
            / "reports/combat_rl_guard_advantage_expanded_corpus_20260829_r1/report.json"
        ).read_text(encoding="ascii")
    )
    conditions = validate_corpus_report(report)
    assert all(conditions.values())

    changed = copy.deepcopy(report)
    changed["config"]["evaluation_seeds"][-1] += 1
    with pytest.raises(ValueError, match="report binding differs"):
        validate_corpus_report(changed)


def test_expanded_offline_gate_is_fixed_and_closes_on_any_boundary_failure():
    metrics = _passing_metrics()
    passed = apply_offline_gates(metrics)
    assert passed["all_conditions_passed"] is True
    assert passed["decision"] == "offline_passed_propose_fresh_lightspeed_gate"

    failed_metrics = copy.deepcopy(metrics)
    failed_metrics["selection"]["severe_harm_count"] = 1
    failed = apply_offline_gates(failed_metrics)
    assert failed["all_conditions_passed"] is False
    assert failed["decision"] == "offline_failed_close_without_fresh_gate_or_sweep"


def test_expanded_result_has_no_game_or_production_authority():
    assert RESULT_AUTHORITY == {
        "development_candidate": True,
        "fresh_lightspeed_gate": False,
        "native_loading": False,
        "lightspeed": False,
        "gameplay": False,
        "communication_mod": False,
        "production_checkpoint_loading": False,
        "production_checkpoint_writing": False,
        "qualification": False,
        "promotion": False,
    }
