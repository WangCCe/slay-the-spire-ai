import hashlib
from fractions import Fraction

import pytest

from analysis_scripts.noncombat_ope_estimation import (
    BOOTSTRAP_DRAW_SCHEMA_VERSION,
    EstimatorInputError,
    WeightedTrajectory,
    bootstrap_trajectory_estimates,
    hash_draw_index,
    percentile_interval,
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


def _reference_draw(
    trajectory_count: int,
    seed: str,
    replicate_index: int,
    draw_index: int,
) -> int:
    payload = (
        f"{BOOTSTRAP_DRAW_SCHEMA_VERSION}\0{seed}\0"
        f"{replicate_index}\0{draw_index}"
    ).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest(), "big") % trajectory_count


def _exact_draw_estimates(ordered, draw_indices):
    selected = tuple(ordered[index] for index in draw_indices)
    count = len(selected)
    weight_sum = sum((row.weight for row in selected), Fraction(0, 1))
    result = {}
    for channel, outcomes in {
        "floor_reached": tuple(
            Fraction(row.floor_reached, 1) for row in selected
        ),
        "victory": tuple(Fraction(int(row.victory), 1) for row in selected),
    }.items():
        behavior = sum(outcomes, Fraction(0, 1)) / count
        weighted = sum(
            (row.weight * outcome for row, outcome in zip(selected, outcomes)),
            Fraction(0, 1),
        )
        ordinary = weighted / count
        self_normalized = weighted / weight_sum
        result[channel] = (
            behavior,
            ordinary,
            self_normalized,
            ordinary - behavior,
            self_normalized - behavior,
        )
    return result


def test_hash_draw_contract_and_paired_resampling_are_exact():
    trajectories = (
        _trajectory("run-c", 3, True, 50),
        _trajectory("run-a", 1, False, 10),
        _trajectory("run-b", 2, True, 30),
    )

    result = bootstrap_trajectory_estimates(
        trajectories,
        seed="paired-fixture",
        replicate_count=4,
    )

    ordered = tuple(sorted(trajectories, key=lambda row: row.group_id))
    assert result.ready is True
    assert result.undefined_replicates == ()
    for replicate in result.replicates:
        expected_draws = tuple(
            _reference_draw(
                len(ordered),
                "paired-fixture",
                replicate.replicate_index,
                draw_index,
            )
            for draw_index in range(len(ordered))
        )
        assert replicate.draw_indices == expected_draws
        assert replicate.draw_group_ids == tuple(
            ordered[index].group_id for index in expected_draws
        )
        expected = _exact_draw_estimates(ordered, expected_draws)
        assert replicate.estimates is not None
        for channel, exact in expected.items():
            estimate = replicate.estimates[channel]
            assert (
                estimate.behavior,
                estimate.ordinary_is,
                estimate.self_normalized_is,
                estimate.ordinary_uplift,
                estimate.self_normalized_uplift,
            ) == exact


def test_hash_draw_is_stable_and_bootstrap_is_row_order_invariant():
    trajectories = (
        _trajectory("run-a", 1, False, 10),
        _trajectory("run-b", 2, True, 30),
        _trajectory("run-c", 3, True, 50),
    )
    expected = _reference_draw(3, "stable-seed", 17, 2)

    assert hash_draw_index(3, "stable-seed", 17, 2) == expected
    assert bootstrap_trajectory_estimates(
        trajectories,
        seed="stable-seed",
        replicate_count=8,
    ) == bootstrap_trajectory_estimates(
        tuple(reversed(trajectories)),
        seed="stable-seed",
        replicate_count=8,
    )


def test_percentile_interval_uses_prespecified_exact_endpoint_indexes():
    values = tuple(Fraction(index, 1) for index in range(101))

    interval = percentile_interval(values, confidence_level=Fraction(95, 100))

    assert interval.lower_index == 2
    assert interval.upper_index == 98
    assert interval.lower == 2
    assert interval.upper == 98


def test_any_zero_snis_denominator_is_reported_and_blocks_intervals():
    trajectories = (
        _trajectory("run-zero", 0, True, 50),
        _trajectory("run-positive", 1, False, 10),
    )

    result = bootstrap_trajectory_estimates(
        trajectories,
        seed="zero-denominator",
        replicate_count=64,
    )

    assert result.ready is False
    assert result.blockers == ("bootstrap_undefined_replicates",)
    assert result.intervals == {}
    assert result.undefined_replicates
    for undefined in result.undefined_replicates:
        assert undefined.reason == "self_normalized_denominator_zero"
        replicate = result.replicates[undefined.replicate_index]
        assert replicate.estimates is None
        assert undefined.draw_indices == replicate.draw_indices
        assert undefined.draw_group_ids == replicate.draw_group_ids


@pytest.mark.parametrize(
    ("seed", "replicate_count"),
    [
        ("", 10),
        ("seed", 0),
        ("seed", 100_001),
    ],
)
def test_bootstrap_requires_a_nonempty_seed_and_bounded_replicate_count(
    seed,
    replicate_count,
):
    trajectories = (_trajectory("run-a", 1, True, 50),)

    with pytest.raises(EstimatorInputError):
        bootstrap_trajectory_estimates(
            trajectories,
            seed=seed,
            replicate_count=replicate_count,
        )
