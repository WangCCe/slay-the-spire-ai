from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from analysis_scripts.combat_rl_action_relative_item_semantic_ablation import (
    FIXED_DEVELOPMENT_GATES,
    FIXED_RECIPE,
    RESULT_AUTHORITY,
    SOURCE_SNAPSHOT_PATHS,
    apply_development_gates,
    validate_predecessor_report,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def _passing_metrics() -> dict:
    return {
        "selection": {
            "intervention_count": 30,
            "intervention_precision": 0.55,
            "mean_selected_true_advantage": FIXED_DEVELOPMENT_GATES[
                "minimum_mean_selected_true_advantage_exclusive"
            ]
            + 1e-6,
            "severe_harm_count": 5,
            "illegal_action_count": 0,
            "forbidden_action_selection_count": 0,
        },
        "ranking": {
            "mean_policy_regret": FIXED_DEVELOPMENT_GATES[
                "maximum_mean_policy_regret_exclusive"
            ]
            - 1e-6
        },
    }


def test_recipe_and_authority_bind_item_semantic_development_only_scope():
    assert FIXED_RECIPE["include_item_semantics"] is True
    assert FIXED_RECIPE["updates"] == 4096
    assert FIXED_RECIPE["fit_seed_first"] == 262000
    assert FIXED_RECIPE["calibration_seed_last"] == 262255
    assert RESULT_AUTHORITY == {
        "development_ablation": True,
        "consumed_development_comparison": True,
        "fresh_corpus_authorized": False,
        "native_loading": False,
        "lightspeed": False,
        "gameplay": False,
        "communication_mod": False,
        "qualification": False,
        "promotion": False,
    }
    assert "analysis_scripts/combat_rl_action_relative_item_semantic_ablation.py" in SOURCE_SNAPSHOT_PATHS
    assert "spirecomm/ai/rl/v2/action_relative_selective_classifier.py" in SOURCE_SNAPSHOT_PATHS


def test_development_gates_use_fixed_strict_predecessor_comparison():
    metrics = _passing_metrics()
    assert apply_development_gates(metrics)["all_conditions_passed"] is True

    metrics["selection"]["mean_selected_true_advantage"] = FIXED_DEVELOPMENT_GATES[
        "minimum_mean_selected_true_advantage_exclusive"
    ]
    failed = apply_development_gates(metrics)
    assert failed["all_conditions_passed"] is False
    assert failed["decision"] == "item_semantics_failed_close_without_fresh_corpus"


def test_predecessor_report_must_match_consumed_comparison_baseline():
    report = json.loads(
        (
            REPO_ROOT
            / "reports/combat_rl_action_relative_selective_classifier_fit_20260829_r1/report.json"
        ).read_text(encoding="ascii")
    )
    validated = validate_predecessor_report(report)
    assert validated["intervention_count"] == 88
    assert validated["severe_harm_count"] == 19

    changed = copy.deepcopy(report)
    changed["evaluation"]["selection"]["intervention_precision"] += 1e-6
    with pytest.raises(ValueError, match="predecessor metrics differ"):
        validate_predecessor_report(changed)
