from __future__ import annotations

import math

import pytest

from analysis_scripts import noncombat_card_only_behavior_sensitivity_diagnostic as diagnostic


def test_distribution_metrics_are_symmetric_and_sensitive() -> None:
    result = diagnostic._distribution_metrics((0.75, 0.25), (0.60, 0.40))

    assert result["entry_to_final_kl"] > 0.0
    assert result["final_to_entry_kl"] > 0.0
    assert result["symmetric_kl"] == pytest.approx(
        0.5 * (result["entry_to_final_kl"] + result["final_to_entry_kl"])
    )
    assert result["total_variation"] == pytest.approx(0.15)


def test_compare_surfaces_detects_boundary_motion_without_action_flip() -> None:
    common = {
        "action_id": "take:Inflame",
        "decision_index": 3,
        "family": "take",
        "family_order": ["skip", "take"],
        "seed": 101,
        "target_action_id": "take:Inflame",
        "target_family": "take",
    }
    entry = {
        **common,
        "acceptance_coordinate": 1.5,
        "family_probabilities": [0.2, 0.8],
        "joint_probabilities": [0.2, 0.5, 0.3],
        "target_family_probability": 0.8,
        "target_joint_probability": 0.5,
        "two_stage_margin": 1.0,
    }
    final = {
        **common,
        "acceptance_coordinate": 0.8,
        "family_probabilities": [0.3, 0.7],
        "joint_probabilities": [0.3, 0.45, 0.25],
        "target_family_probability": 0.7,
        "target_joint_probability": 0.45,
        "two_stage_margin": 0.4,
    }

    row = diagnostic._compare_surfaces((entry,), (final,))[0]

    assert row["action_flip"] is False
    assert row["family_flip"] is False
    assert row["acceptance_coordinate_delta"] == pytest.approx(-0.7)
    assert row["margin_delta"] == pytest.approx(-0.6)
    assert row["moved_toward_boundary"] is True
    assert row["joint_symmetric_kl"] > 0.0
    assert row["target_family_log_probability_delta"] < 0.0
    assert row["target_joint_log_probability_delta"] < 0.0


def test_parameter_movement_splits_family_and_conditional_heads() -> None:
    def tensor(values: list[float]) -> dict[str, object]:
        return {"dtype": "float32", "shape": [len(values)], "values": values}

    entry = diagnostic._canonical_bytes(
        {
            "conditional_ranker": {"weight": tensor([0.0, 1.0])},
            "family_head": {"weight": tensor([1.0, 0.0])},
            "schema_version": "noncombat-card-only-warm-start-model-v1",
        }
    )
    final = diagnostic._canonical_bytes(
        {
            "conditional_ranker": {"weight": tensor([0.0, 2.0])},
            "family_head": {"weight": tensor([1.0, 2.0])},
            "schema_version": "noncombat-card-only-warm-start-model-v1",
        }
    )

    result = diagnostic._parameter_movement(entry, final)

    assert result["heads"]["conditional_ranker"]["delta_l2"] == pytest.approx(1.0)
    assert result["heads"]["family_head"]["delta_l2"] == pytest.approx(2.0)
    assert result["global_delta_l2"] == pytest.approx(math.sqrt(5.0))


def test_vector_helpers_measure_path_cancellation() -> None:
    first = diagnostic._vector_delta((0.0, 0.0), (1.0, 0.0))
    second = diagnostic._vector_delta((1.0, 0.0), (0.5, 0.0))

    assert diagnostic._vector_l2(first) == pytest.approx(1.0)
    assert diagnostic._vector_l2(second) == pytest.approx(0.5)
    assert diagnostic._cosine(first, second) == pytest.approx(-1.0)
