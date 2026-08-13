import copy
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch

from analysis_scripts import noncombat_card_acceptance_empirical_successor_runtime as successor
from analysis_scripts import noncombat_card_only_behavior_sensitivity_runner as runner


def _registration(tmp_path):
    seeds = list(runner.pilot_runner.CONSUMED_DEVELOPMENT_SEEDS)
    bottled = {
        "commit": "b" * 40,
        "commit_short": "b" * 7,
        "dirty": False,
        "path": (tmp_path / "bottled").as_posix(),
        "strategy": "REQUESTED_STRIKE",
        "tree": "c" * 40,
    }
    corpus = {
        "allowed_cohorts": list(runner.pilot.ALLOWED_CORPUS_COHORTS),
        "card_row_counts": dict(runner.pilot.BOUND_CARD_ROW_COUNTS),
        "path": (tmp_path / "corpus.json").as_posix(),
        "registration_sha256": runner.pilot.BOUND_REGISTRATION_SHA256,
        "sha256": runner.pilot.BOUND_CORPUS_SHA256,
        "size_bytes": runner.pilot.BOUND_CORPUS_SIZE_BYTES,
    }
    return {
        "configuration": {
            "additional_chunks": runner.ADDITIONAL_CHUNKS,
            "first_chunk_index": runner.training.FIRST_CHUNK_INDEX,
            "last_chunk_index": runner.training.FINAL_CHUNK_INDEX - 1,
            "maximum_censored_trajectories_per_chunk": (
                runner.training.MAX_CENSORED_TRAJECTORIES
            ),
            "maximum_charged_seconds": runner.MAX_CHARGED_SECONDS,
            "maximum_environment_accesses": runner.MAX_ENVIRONMENT_ACCESSES,
            "minimum_action_flips": runner.MIN_ACTION_FLIPS,
            "training_environment_accesses_per_chunk": (
                runner.training.CHUNK_SEED_COUNT
            ),
        },
        "downstream_authority": copy.deepcopy(runner.FALSE_AUTHORITY),
        "inputs": {
            "r7_checkpoint": {
                "path": (tmp_path / "checkpoint.json").as_posix(),
                "sha256": "1" * 64,
                "size_bytes": 1,
            },
            "r7_registration": {
                "path": (tmp_path / "r7.json").as_posix(),
                "sha256": "2" * 64,
                "size_bytes": 1,
            },
        },
        "native": {
            "identity": {
                "dependency_closure": {"dependencies": []},
                "module": {
                    "path": (tmp_path / "native.pyd").as_posix(),
                    "sha256": "3" * 64,
                    "size_bytes": 1,
                },
            },
            "manifest": {
                "path": (tmp_path / "manifest.json").as_posix(),
                "sha256": "4" * 64,
                "size_bytes": 1,
            },
        },
        "operations": copy.deepcopy(runner.OPERATIONS),
        "output_dir": (tmp_path / "output").as_posix(),
        "policy_context": {"bottled": bottled, "corpus": corpus},
        "production_isolation": {
            "communication_mod_config": {
                "path": (tmp_path / "config.properties").as_posix(),
                "sha256": "5" * 64,
                "size_bytes": 1,
            },
            "production_checkpoints": {
                "file_count": 0,
                "metadata_sha256": "6" * 64,
                "path": (tmp_path / "production").as_posix(),
                "size_bytes": 0,
            },
        },
        "schedule": {
            "comparison_seeds": seeds,
            "training_chunk_seeds": [seeds] * runner.ADDITIONAL_CHUNKS,
            "seed_status": "already-consumed-development-only",
        },
        "schema_version": runner.REGISTRATION_SCHEMA_VERSION,
        "source": {
            "bindings": {
                path: {
                    "path": (tmp_path / path).as_posix(),
                    "sha256": "a" * 64,
                    "size_bytes": 1,
                }
                for path in runner.SOURCE_PATHS
            },
            "commit": "a" * 40,
            "repo_root": tmp_path.as_posix(),
        },
    }


def test_registration_fixes_schedule_resources_and_authority(tmp_path):
    registration = _registration(tmp_path)

    assert runner.validate_registration(registration) == registration

    authority = copy.deepcopy(registration)
    authority["downstream_authority"]["promotion"] = True
    with pytest.raises(runner.BehaviorRunnerBlocked, match="authority"):
        runner.validate_registration(authority)

    schedule = copy.deepcopy(registration)
    schedule["schedule"]["training_chunk_seeds"][0][0] += 1
    with pytest.raises(runner.BehaviorRunnerBlocked, match="schedule"):
        runner.validate_registration(schedule)


def test_preflight_rejects_active_game_before_entry_loading(tmp_path, monkeypatch):
    registration = _registration(tmp_path)
    r7 = {
        "native": registration["native"],
        "bottled": registration["policy_context"]["bottled"],
        "corpus": registration["policy_context"]["corpus"],
    }
    monkeypatch.setattr(runner.pilot_runner, "_git", lambda *_args: "a" * 40)
    monkeypatch.setattr(runner.pilot_runner, "_binding_matches", lambda _value: True)
    monkeypatch.setattr(runner, "_read_canonical", lambda _path: r7)
    monkeypatch.setattr(
        runner.pilot_runner,
        "_bottled_identity",
        lambda _path: registration["policy_context"]["bottled"],
    )
    monkeypatch.setattr(
        runner.pilot_runner,
        "_directory_metadata_binding",
        lambda _path: registration["production_isolation"]["production_checkpoints"],
    )
    entry_loads = []
    monkeypatch.setattr(
        runner,
        "_load_probe_and_entry",
        lambda _value: entry_loads.append(_value),
    )

    with pytest.raises(runner.BehaviorRunnerBlocked, match="process is active"):
        runner.preflight_registration(
            registration,
            process_observer=lambda: [{"name": "SlayTheSpire.exe"}],
        )

    assert entry_loads == []
    assert not Path(registration["output_dir"]).exists()


def _episode(seed, arm):
    take = seed % 2 == 0
    decision = successor.ArmRolloutDecision(
        arm=arm,
        category="card_reward",
        decision_id=f"{arm}:seed-{seed}:decision-0",
        decision_index=0,
        selected_action_id="take" if take else "skip",
        state_features=torch.zeros(128, dtype=torch.float32),
        card_terms=object() if arm == "candidate" else None,
        diagnostic={
            "multi_family": True,
            "selected_family": "take" if take else "skip",
        },
    )
    return successor.ArmEpisodeRollout(
        arm=arm,
        seed=seed,
        trajectory_id=f"{arm}:seed-{seed}",
        decisions=(decision,),
        transitions=({},),
        rewards=(0.0,),
        final_snapshot={"terminal": True},
        floor_progress=2.0 if arm == "candidate" else 1.0,
        terminal_victory=1 if arm == "candidate" and seed == 1000 else 0,
        unsupported_reason=None,
    )


@pytest.mark.parametrize(
    ("action_flips", "expected_verdict"),
    [
        (4, "ready_to_propose_fresh_card_only_evaluation"),
        (3, "card_only_behavior_sensitivity_not_ready"),
    ],
)
def test_terminal_comparison_requires_behavior_change(
    monkeypatch, action_flips, expected_verdict
):
    monkeypatch.setattr(
        runner.successor,
        "rollout_arm_frozen_evaluation",
        lambda _bootstrap, *, arm, seed, **_kwargs: _episode(seed, arm),
    )
    monkeypatch.setattr(
        runner.training,
        "behavior_summary",
        lambda _value: {
            "action_flips_from_entry": action_flips,
            "family_flips_from_entry": action_flips,
            "model_sha256": "a" * 64,
            "parameter_l2_from_entry": 1.0,
            "probe_rows": 175,
            "stop": False,
            "take_rate": 0.5,
        },
    )

    comparison = runner._terminal_comparison(
        SimpleNamespace(bootstrap=object()),
        environment_factory=lambda _seed: object(),
        seeds=runner.pilot_runner.CONSUMED_DEVELOPMENT_SEEDS,
        deadline=1.0,
        clock=lambda: 0.0,
    )

    assert comparison["verdict"] == expected_verdict
    assert comparison["checks"]["minimum_action_flips"] is (action_flips >= 4)


def test_resume_loads_only_latest_complete_checkpoint(tmp_path, monkeypatch):
    output = tmp_path / "output"
    output.mkdir()
    (output / "entry_model.json").write_bytes(b"entry")
    (output / "checkpoint_004.json").write_bytes(b"four")
    (output / "checkpoint_006.json").write_bytes(b"six")
    entry = SimpleNamespace(entry_model=b"entry")
    restored = SimpleNamespace(next_chunk_index=6)
    restore_calls = []
    monkeypatch.setattr(
        runner,
        "_load_probe_and_entry",
        lambda _registration: (("probe",), entry),
    )

    def fake_restore(payload, *, probe_rows, entry_model):
        restore_calls.append((payload, probe_rows, entry_model))
        return restored

    monkeypatch.setattr(
        runner.training,
        "restore_behavior_sensitivity_checkpoint",
        fake_restore,
    )

    actual = runner._load_or_initialize_runtime({}, output)

    assert actual is restored
    assert restore_calls == [(b"six", ("probe",), b"entry")]
