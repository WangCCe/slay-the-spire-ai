from __future__ import annotations

import copy

import pytest

from analysis_scripts import noncombat_card_only_behavior_sensitivity_runner as behavior_runner
from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot_runner as pilot_runner
from analysis_scripts import noncombat_card_optimizer_replay as replay
from analysis_scripts import noncombat_card_scorer_optimizer_replay_ablation as ablation
from analysis_scripts import noncombat_card_scorer_optimizer_replay_ablation_runner as runner


def _binding():
    return {"path": "D:/bound", "sha256": "a" * 64, "size_bytes": 1}


def _registration():
    return {
        "configuration": {
            "entry_chunk_index": 4,
            "maximum_canonical_replay_bytes": replay.MAX_CANONICAL_BYTES,
            "maximum_censored_trajectories": 8,
            "maximum_charged_seconds": 7200.0,
            "maximum_environment_accesses": 64,
            "maximum_stored_replay_bytes": replay.MAX_STORED_BYTES,
            "minimum_supported_trajectories": 56,
            "optimizer_steps_per_branch": 1,
            "retained_mean_joint_tv_threshold": ablation.RETAINED_MEAN_JOINT_TV_THRESHOLD,
        },
        "downstream_authority": copy.deepcopy(runner.FALSE_AUTHORITY),
        "inputs": {
            "entry_checkpoint": _binding(),
            "historical_checkpoint": _binding(),
            "parent_registration": _binding(),
        },
        "native": {"identity": {}, "manifest": _binding()},
        "operations": copy.deepcopy(runner.OPERATIONS),
        "output_dir": "D:/output",
        "policy_context": {"bottled": {}, "corpus": {}},
        "production_isolation": {
            "communication_mod_config": _binding(),
            "production_checkpoints": {},
        },
        "schedule": {
            "seed_status": "already-consumed-development-only",
            "shared_trajectory_seeds": list(pilot_runner.CONSUMED_DEVELOPMENT_SEEDS),
        },
        "schema_version": runner.REGISTRATION_SCHEMA_VERSION,
        "source": {
            "bindings": {path: _binding() for path in runner.SOURCE_PATHS},
            "commit": "b" * 40,
            "repo_root": "D:/repo",
        },
    }


def test_registration_fixes_replay_bounds_seed_schedule_and_tv_gate() -> None:
    registration = runner.validate_registration(_registration())

    assert registration["schedule"]["shared_trajectory_seeds"] == list(
        pilot_runner.CONSUMED_DEVELOPMENT_SEEDS
    )
    assert registration["configuration"]["retained_mean_joint_tv_threshold"] == 0.8
    assert registration["configuration"]["maximum_stored_replay_bytes"] == 64 * 1024 * 1024


def test_registration_rejects_retained_tv_threshold_drift() -> None:
    registration = _registration()
    registration["configuration"]["retained_mean_joint_tv_threshold"] = 0.79

    with pytest.raises(runner.ScorerReplayRunnerBlocked, match="fields or policy"):
        runner.validate_registration(registration)
