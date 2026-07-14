from dataclasses import replace
from fractions import Fraction

from analysis_scripts.noncombat_ope_estimation import (
    PercentileInterval,
    WeightedTrajectory,
    bootstrap_trajectory_estimates,
    estimate_outcome_channels,
    evaluate_policy_comparison,
    leave_one_trajectory_out,
)


def _trajectory(
    group_id: str,
    weight: int,
    victory: bool,
    floor_reached: int,
) -> WeightedTrajectory:
    return WeightedTrajectory(
        group_id=group_id,
        weight=Fraction(weight, 1),
        victory=victory,
        floor_reached=floor_reached,
        sample_ids=(f"sample-{group_id}",),
    )


def test_leave_one_out_recomputes_exact_estimates_and_influence():
    trajectories = (
        _trajectory("run-c", 1, False, 20),
        _trajectory("run-a", 10, True, 50),
        _trajectory("run-d", 1, False, 10),
        _trajectory("run-b", 10, True, 40),
    )

    diagnostics = leave_one_trajectory_out(trajectories)

    ordered = tuple(sorted(trajectories, key=lambda row: row.group_id))
    assert tuple(row.excluded_group_id for row in diagnostics.rows) == tuple(
        row.group_id for row in ordered
    )
    assert diagnostics.undefined_group_ids == ()
    for row in diagnostics.rows:
        expected = estimate_outcome_channels(
            tuple(
                trajectory
                for trajectory in ordered
                if trajectory.group_id != row.excluded_group_id
            )
        )
        assert row.estimates == expected
        assert row.blocker is None
        for channel, estimate in expected.items():
            full = diagnostics.full_sample_estimates[channel]
            assert row.absolute_changes[channel]["ordinary_uplift"] == abs(
                estimate.ordinary_uplift - full.ordinary_uplift
            )
            assert row.absolute_changes[channel]["self_normalized_uplift"] == abs(
                estimate.self_normalized_uplift
                - full.self_normalized_uplift
            )
    assert diagnostics == leave_one_trajectory_out(tuple(reversed(trajectories)))
    for channel, fields in diagnostics.max_absolute_changes.items():
        for field, maximum in fields.items():
            assert maximum == max(
                row.absolute_changes[channel][field] for row in diagnostics.rows
            )


def test_leave_one_out_reports_zero_denominator_without_dropping_row():
    trajectories = (
        _trajectory("run-zero", 0, True, 50),
        _trajectory("run-positive", 1, False, 10),
    )

    diagnostics = leave_one_trajectory_out(trajectories)

    assert diagnostics.undefined_group_ids == ("run-positive",)
    row = next(
        row
        for row in diagnostics.rows
        if row.excluded_group_id == "run-positive"
    )
    assert row.estimates is None
    assert row.blocker == "self_normalized_denominator_zero"
    assert row.absolute_changes == {}
    assert row.sign_changes == {}


def test_policy_comparison_gate_requires_victory_interval_and_influence():
    trajectories = (
        _trajectory("run-a", 10, True, 50),
        _trajectory("run-b", 10, True, 40),
        _trajectory("run-c", 1, False, 20),
        _trajectory("run-d", 1, False, 10),
    )
    estimates = estimate_outcome_channels(trajectories)
    influence = leave_one_trajectory_out(trajectories)
    bootstrap = bootstrap_trajectory_estimates(
        trajectories,
        seed="comparison-gate",
        replicate_count=8,
    )
    positive_victory = dict(bootstrap.intervals["victory"])
    positive_victory["self_normalized_uplift"] = PercentileInterval(
        lower=Fraction(1, 100),
        upper=Fraction(1, 2),
        lower_index=0,
        upper_index=7,
    )
    bootstrap = replace(
        bootstrap,
        intervals={
            "floor_reached": bootstrap.intervals["floor_reached"],
            "victory": positive_victory,
        },
    )

    gate = evaluate_policy_comparison(
        estimator_validation_ready=True,
        dataset_estimation_ready=True,
        estimates=estimates,
        bootstrap=bootstrap,
        influence=influence,
    )

    assert gate.ready is True
    assert gate.blockers == ()
    assert all(gate.conditions.values())


def test_floor_interval_cannot_substitute_for_failed_victory_gate():
    trajectories = (
        _trajectory("run-a", 10, True, 50),
        _trajectory("run-b", 10, True, 40),
        _trajectory("run-c", 1, False, 20),
        _trajectory("run-d", 1, False, 10),
    )
    estimates = estimate_outcome_channels(trajectories)
    influence = leave_one_trajectory_out(trajectories)
    bootstrap = bootstrap_trajectory_estimates(
        trajectories,
        seed="comparison-blocked",
        replicate_count=8,
    )
    floor_intervals = dict(bootstrap.intervals["floor_reached"])
    floor_intervals["self_normalized_uplift"] = PercentileInterval(
        lower=Fraction(100, 1),
        upper=Fraction(200, 1),
        lower_index=0,
        upper_index=7,
    )
    victory_intervals = dict(bootstrap.intervals["victory"])
    victory_intervals["self_normalized_uplift"] = PercentileInterval(
        lower=Fraction(0, 1),
        upper=Fraction(1, 2),
        lower_index=0,
        upper_index=7,
    )
    bootstrap = replace(
        bootstrap,
        intervals={
            "floor_reached": floor_intervals,
            "victory": victory_intervals,
        },
    )

    gate = evaluate_policy_comparison(
        estimator_validation_ready=True,
        dataset_estimation_ready=True,
        estimates=estimates,
        bootstrap=bootstrap,
        influence=influence,
    )

    assert gate.ready is False
    assert gate.conditions["primary_victory_snis_interval_positive"] is False
    assert gate.blockers == ("primary_victory_snis_interval_not_positive",)
