from __future__ import annotations

import copy

import pytest

from analysis_scripts import noncombat_card_only_baseline_clipping_ablation_runner as runner


def _behavior(*, stop: bool = False):
    return {"stop": stop, "take_rate": 0.5}


def _function_summary(*, action_flips: int = 0, mean_tv: float = 0.0):
    return {
        "action_flips": action_flips,
        "joint_total_variation": {"mean": mean_tv},
    }


def test_reproduction_failure_precedes_material_signal() -> None:
    result = runner.classify_result(
        reproduction_exact=False,
        clipped_behavior=_behavior(),
        unclipped_behavior=_behavior(),
        function_summary=_function_summary(action_flips=1, mean_tv=0.5),
        applied_gradient_cosine=-1.0,
    )

    assert result["material_effect"] is True
    assert result["verdict"] == "baseline_clipping_ablation_reproduction_failed"


@pytest.mark.parametrize(
    ("action_flips", "mean_tv", "cosine"),
    (
        (1, 0.0, 1.0),
        (0, runner.MEAN_JOINT_TV_THRESHOLD, 1.0),
        (0, 0.0, runner.APPLIED_GRADIENT_COSINE_THRESHOLD),
    ),
)
def test_each_registered_material_condition_can_propose_four_steps(
    action_flips, mean_tv, cosine
) -> None:
    result = runner.classify_result(
        reproduction_exact=True,
        clipped_behavior=_behavior(),
        unclipped_behavior=_behavior(),
        function_summary=_function_summary(
            action_flips=action_flips, mean_tv=mean_tv
        ),
        applied_gradient_cosine=cosine,
    )

    assert result["material_effect"] is True
    assert result["verdict"] == "ready_to_propose_four_step_baseline_clipping_ablation"


def test_valid_but_immaterial_result_stops() -> None:
    result = runner.classify_result(
        reproduction_exact=True,
        clipped_behavior=_behavior(),
        unclipped_behavior=_behavior(),
        function_summary=_function_summary(
            mean_tv=runner.MEAN_JOINT_TV_THRESHOLD / 2.0
        ),
        applied_gradient_cosine=(
            runner.APPLIED_GRADIENT_COSINE_THRESHOLD + 1.0
        )
        / 2.0,
    )

    assert result["material_effect"] is False
    assert result["verdict"] == "baseline_clipping_not_material_in_one_step"


def test_branch_collapse_blocks_material_progression() -> None:
    result = runner.classify_result(
        reproduction_exact=True,
        clipped_behavior=_behavior(),
        unclipped_behavior=_behavior(stop=True),
        function_summary=_function_summary(action_flips=1),
        applied_gradient_cosine=1.0,
    )

    assert result["verdict"] == "baseline_clipping_ablation_branch_collapse"


def test_validate_registration_rejects_nonfalse_authority() -> None:
    binding = {"path": "x", "sha256": "0" * 64, "size_bytes": 1}
    registration = {
        "configuration": {
            "applied_gradient_cosine_threshold": runner.APPLIED_GRADIENT_COSINE_THRESHOLD,
            "entry_chunk_index": 4,
            "maximum_censored_trajectories": 8,
            "maximum_charged_seconds": runner.MAX_CHARGED_SECONDS,
            "maximum_environment_accesses": runner.MAX_ENVIRONMENT_ACCESSES,
            "mean_joint_total_variation_threshold": runner.MEAN_JOINT_TV_THRESHOLD,
            "minimum_supported_trajectories": 56,
            "optimizer_steps_per_branch": 1,
        },
        "downstream_authority": copy.deepcopy(runner.FALSE_AUTHORITY),
        "inputs": {
            "entry_checkpoint": binding,
            "historical_checkpoint": binding,
            "parent_registration": binding,
        },
        "native": {"identity": {}, "manifest": binding},
        "operations": copy.deepcopy(runner.OPERATIONS),
        "output_dir": "output",
        "policy_context": {"bottled": {}, "corpus": {}},
        "production_isolation": {
            "communication_mod_config": binding,
            "production_checkpoints": {},
        },
        "schedule": {
            "seed_status": "already-consumed-development-only",
            "shared_trajectory_seeds": list(
                runner.pilot_runner.CONSUMED_DEVELOPMENT_SEEDS
            ),
        },
        "schema_version": runner.REGISTRATION_SCHEMA_VERSION,
        "source": {
            "bindings": {
                name: binding for name in runner.SOURCE_PATHS
            },
            "commit": "0" * 40,
            "repo_root": "root",
        },
    }
    registration["downstream_authority"]["training"] = True

    with pytest.raises(runner.BaselineClippingRunnerBlocked, match="authority"):
        runner.validate_registration(registration)
