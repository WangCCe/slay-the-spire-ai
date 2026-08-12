import copy
from pathlib import Path
from types import SimpleNamespace

import pytest

from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot_runner as runner


def _registration(tmp_path):
    expected_seeds = list(runner.CONSUMED_DEVELOPMENT_SEEDS)
    return {
        "bottled": {
            "commit": "b" * 40,
            "commit_short": "b" * 7,
            "dirty": False,
            "path": (tmp_path / "bottled").as_posix(),
            "strategy": "REQUESTED_STRIKE",
            "tree": "c" * 40,
        },
        "configuration": {
            "comparison": "one-frozen-candidate-vs-native-control-v1",
            "maximum_charged_seconds": runner.MAX_CHARGED_SECONDS,
            "maximum_environment_accesses": runner.MAX_ENVIRONMENT_ACCESSES,
            "maximum_residual_chunks": runner.MAX_RESIDUAL_CHUNKS,
            "residual_chunk_pairs": 64,
            "warm_start": runner.pilot.card_warm_start_configuration(),
        },
        "corpus": {
            "allowed_cohorts": list(runner.pilot.ALLOWED_CORPUS_COHORTS),
            "card_row_counts": dict(runner.pilot.BOUND_CARD_ROW_COUNTS),
            "path": (tmp_path / "corpus.json").as_posix(),
            "registration_sha256": runner.pilot.BOUND_REGISTRATION_SHA256,
            "sha256": runner.pilot.BOUND_CORPUS_SHA256,
            "size_bytes": runner.pilot.BOUND_CORPUS_SIZE_BYTES,
        },
        "downstream_authority": dict(runner.FALSE_DOWNSTREAM_AUTHORITY),
        "native": {
            "identity": {
                "adapter_api_version": runner.adapter.ADAPTER_API_VERSION,
                "dependency_closure": {"dependencies": []},
                "dll_directories": [],
                "module": {
                    "path": (tmp_path / "native.pyd").as_posix(),
                    "sha256": "1" * 64,
                    "size_bytes": 1,
                },
                "provenance": {},
                "provenance_sha256": "2" * 64,
            },
            "manifest": {
                "path": (tmp_path / "native.json").as_posix(),
                "sha256": "d" * 64,
                "size_bytes": 1,
            },
        },
        "operations": dict(runner.REGISTERED_OPERATIONS),
        "output_dir": (tmp_path / "output").as_posix(),
        "production_isolation": {
            "communication_mod_config": {
                "path": (tmp_path / "config.properties").as_posix(),
                "sha256": "e" * 64,
                "size_bytes": 1,
            },
            "production_checkpoints": {
                "file_count": 0,
                "metadata_sha256": "f" * 64,
                "path": (tmp_path / "checkpoints").as_posix(),
                "size_bytes": 0,
            },
        },
        "schedule": {
            "comparison_seeds": expected_seeds,
            "residual_chunk_seeds": [expected_seeds] * runner.MAX_RESIDUAL_CHUNKS,
            "seed_status": "already-consumed-development-only",
        },
        "schema_version": runner.REGISTRATION_SCHEMA_VERSION,
        "source": {
            "bindings": {
                path: {"path": path, "sha256": "a" * 64, "size_bytes": 1}
                for path in runner.BOUND_SOURCE_PATHS
            },
            "commit": "a" * 40,
            "repo_root": tmp_path.as_posix(),
        },
    }


def test_registration_fixes_authority_schedule_and_corpus(tmp_path):
    registration = _registration(tmp_path)
    assert runner.validate_registration(registration) == registration

    authority = copy.deepcopy(registration)
    authority["downstream_authority"]["formal_rl"] = True
    with pytest.raises(runner.CardOnlyRunnerBlocked, match="authority"):
        runner.validate_registration(authority)

    protected = copy.deepcopy(registration)
    protected["corpus"]["allowed_cohorts"].append("final_test")
    with pytest.raises(runner.CardOnlyRunnerBlocked, match="corpus"):
        runner.validate_registration(protected)

    seeds = copy.deepcopy(registration)
    seeds["schedule"]["comparison_seeds"][0] += 1
    with pytest.raises(runner.CardOnlyRunnerBlocked, match="schedule"):
        runner.validate_registration(seeds)


def test_preflight_rejects_active_game_before_output(tmp_path, monkeypatch):
    registration = _registration(tmp_path)
    checkpoints = Path(
        registration["production_isolation"]["production_checkpoints"]["path"]
    )
    checkpoints.mkdir()
    monkeypatch.setattr(runner, "_git", lambda *_args: "commit")
    monkeypatch.setattr(runner, "_binding_matches", lambda _binding: True)
    monkeypatch.setattr(
        runner,
        "_native_identity_from_manifest",
        lambda _path: registration["native"]["identity"],
    )
    monkeypatch.setattr(
        runner, "_bottled_identity", lambda _path: registration["bottled"]
    )
    monkeypatch.setattr(
        runner,
        "_directory_metadata_binding",
        lambda _path: registration["production_isolation"]["production_checkpoints"],
    )
    monkeypatch.setattr(runner.subprocess, "run", lambda *_args, **_kwargs: None)

    with pytest.raises(runner.CardOnlyRunnerBlocked, match="process is active"):
        runner.preflight_registration(
            registration,
            process_observer=lambda: [{"name": "SlayTheSpire.exe"}],
        )
    assert not Path(registration["output_dir"]).exists()


def test_failed_warm_start_gate_never_loads_native(tmp_path, monkeypatch):
    registration = _registration(tmp_path)
    monkeypatch.setattr(
        runner,
        "preflight_registration",
        lambda *_args, **_kwargs: {
            "schema_version": runner.PREFLIGHT_SCHEMA_VERSION,
            "verdict": "preflight_passed",
        },
    )
    monkeypatch.setattr(runner.pilot, "load_bound_card_corpus", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(runner, "BottledPolicyOracle", lambda _path: object())
    monkeypatch.setattr(
        runner.pilot,
        "label_bound_card_corpus",
        lambda *_args, **_kwargs: {"counts": {"total": 477}},
    )
    monkeypatch.setattr(runner.runtime, "build_matched_bootstrap", lambda: object())
    warm_start = SimpleNamespace(
        bootstrap=object(),
        configuration=runner.pilot.card_warm_start_configuration(),
        final_model=b"final",
        final_validation={
            "action_agreement": 0.0,
            "action_correct": 0,
            "family_agreement": 0.0,
            "family_correct": 0,
            "non_take_rate": 1.0,
            "row_count": 175,
            "take_rate": 0.0,
        },
        gate={"passed": False, "verdict": "card_warm_start_gate_failed"},
        optimizer_steps=128,
        zero_model=b"zero",
        zero_validation={
            "action_agreement": 0.0,
            "action_correct": 0,
            "family_agreement": 0.0,
            "family_correct": 0,
            "non_take_rate": 1.0,
            "row_count": 175,
            "take_rate": 0.0,
        },
    )
    monkeypatch.setattr(
        runner.pilot, "run_fixed_card_warm_start", lambda *_args: warm_start
    )
    monkeypatch.setattr(
        runner.runtime, "encode_paired_bootstrap", lambda _bootstrap: b"checkpoint"
    )
    native_loads = []

    terminal = runner.execute_pilot(
        registration,
        clock=lambda: 0.0,
        process_observer=lambda: (),
        environment_factory_loader=lambda identity: native_loads.append(identity),
    )

    assert terminal["verdict"] == "card_only_native_baseline_pilot_not_ready"
    assert terminal["environment_accesses"] == 0
    assert native_loads == []
    assert (Path(registration["output_dir"]) / "terminal.json").is_file()
    assert (Path(registration["output_dir"]) / "report.json").is_file()


def _comparison_pairs(*, all_take=False, candidate_floor=2.0, control_floor=1.0):
    pairs = []
    for index, seed in enumerate(runner.CONSUMED_DEVELOPMENT_SEEDS):
        family = "take" if all_take or index % 2 == 0 else "skip"
        decision = SimpleNamespace(
            category="card_reward",
            diagnostic={"multi_family": True, "selected_family": family},
        )
        pairs.append(
            SimpleNamespace(
                seed=seed,
                candidate=SimpleNamespace(
                    decisions=(decision,),
                    floor_progress=candidate_floor,
                    terminal_victory=1 if index == 0 else 0,
                    unsupported_reason=None,
                ),
                control=SimpleNamespace(
                    decisions=(),
                    floor_progress=control_floor,
                    terminal_victory=0,
                    unsupported_reason=None,
                ),
            )
        )
    return tuple(pairs)


def test_frozen_comparison_requires_noninferiority_and_card_coverage():
    ready = runner.classify_frozen_comparison(_comparison_pairs())
    concentrated = runner.classify_frozen_comparison(
        _comparison_pairs(all_take=True)
    )
    inferior = runner.classify_frozen_comparison(
        _comparison_pairs(candidate_floor=0.5, control_floor=1.0)
    )

    assert ready["verdict"] == "ready_to_propose_fresh_card_only_evaluation"
    assert ready["take_rate"] == 0.5
    assert concentrated["verdict"] == "card_only_native_baseline_pilot_not_ready"
    assert concentrated["checks"]["candidate_card_coverage"] is False
    assert inferior["checks"]["candidate_floor_noninferior"] is False
