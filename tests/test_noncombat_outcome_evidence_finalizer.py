import hashlib
import json
from fractions import Fraction
from pathlib import Path

import pytest

from analysis_scripts import noncombat_ope_estimate_artifacts as estimate_artifacts
from analysis_scripts import noncombat_ope_estimation as estimation
from analysis_scripts import noncombat_ope_readiness as readiness
from analysis_scripts import noncombat_outcome_evidence_expansion as expansion


STUDY_ID = "noncombat-outcome-evidence-expansion-20260715"
RUN_LOCK_HASH = "b" * 64
POOL_HASH = "c" * 64
TARGET_HASH = "d" * 64
SAMPLE_TEXT = '{"sample_id":"sample-1"}\n'


def _registration(tmp_path):
    repo_root = tmp_path / "repo"
    calibration_path = (
        repo_root
        / "reports"
        / "noncombat_ope_estimator_calibration_20260714.json"
    )
    calibration_path.parent.mkdir(parents=True)
    calibration_path.write_text('{"calibration":"frozen"}\n', encoding="utf-8")
    return expansion.build_registration(
        study_id=STUDY_ID,
        artifact_root=tmp_path / "study",
        repo_root=repo_root,
        seed_base=2_026_071_500,
        python_executable=Path(r"D:\anaconda\envs\stsai\python.exe"),
        communication_config_path=tmp_path / "config.properties",
        checkpoint_root=tmp_path / "checkpoints",
    )


def _ledger_snapshot(registration):
    terminal_slots = [
        {
            "complete_trajectories": 25,
            "marker_end_count": slot.slot_number * 25,
            "marker_start_count": (slot.slot_number - 1) * 25,
            "process_exit_code": 0,
            "session_id": slot.session_id,
            "slot_number": slot.slot_number,
            "terminal_status": "completed",
        }
        for slot in registration.slots
    ]
    return {
        "active_slot": None,
        "all_slots_terminal": True,
        "global_stop": None,
        "initialized": True,
        "terminal_slot_count": 24,
        "terminal_slots": terminal_slots,
    }


def _pool(registration=None):
    manifest = {
        "pool_manifest_hash": POOL_HASH,
        "sample_jsonl_sha256": hashlib.sha256(
            SAMPLE_TEXT.encode("utf-8")
        ).hexdigest(),
    }
    if registration is not None:
        manifest.update(
            {
                "registration_hash": registration.registration_hash,
                "run_lock_hash": RUN_LOCK_HASH,
            }
        )
    return expansion.RegisteredPool(
        samples=({"sample_id": "sample-1"},),
        manifest=manifest,
    )


def _metrics(*, supported_victories=3, ess_fraction=Fraction(1, 2)):
    return expansion.OutcomeEvidenceGateMetrics(
        all_registered_slots_accounted=True,
        global_integrity_stop=False,
        complete_trajectory_count=575,
        category_arm_support={
            "card_reward": {"alternative": 50, "baseline": 50},
            "shop": {"alternative": 50, "baseline": 50},
        },
        nonzero_weight_trajectory_count=288,
        ess_fraction=ess_fraction,
        max_normalized_weight=Fraction(1, 20),
        supported_victory_count=supported_victories,
    )


def _patch_pipeline(
    monkeypatch,
    *,
    supported_victories=3,
    ess_fraction=Fraction(1, 2),
    unsafe=False,
    loader_blocked=False,
    loader_error=None,
    readiness_ready=True,
):
    calls = {}
    target = {
        "construction_mode": "current_deterministic",
        "diagnostic_only": False,
        "manifest_hash": TARGET_HASH,
    }
    readiness_artifact = {
        "diagnostics": {"floor_reached": {"maximum": 99}},
        "readiness": {
            "outcome_contract_ready": True,
            "overlap_ready": readiness_ready,
            "target_policy_ready": True,
        },
    }
    if not readiness_ready:
        readiness_artifact["blockers"] = ["minimum_ess_fraction"]
    estimate = {
        "estimates": {"floor_reached": {"self_normalized_is": 99}},
        "gates": {
            "formal_noncombat_rl_training_ready": unsafe,
            "live_policy_promotion_ready": unsafe,
            "ope_estimate_ready": True,
            "policy_comparison_ready": True,
        },
        "source": {"calibration_file_sha256": "a" * 64},
    }

    monkeypatch.setattr(
        expansion,
        "render_registered_pool_samples",
        lambda _pool_value: SAMPLE_TEXT,
    )
    monkeypatch.setattr(
        expansion,
        "render_registered_pool_manifest",
        lambda _pool_value: json.dumps(_pool_value.manifest, sort_keys=True) + "\n",
    )

    def build_target(samples, *, source_sample_sha256):
        calls["target"] = (tuple(samples), source_sample_sha256)
        return target

    def build_readiness(sample_path, target_manifest):
        path = Path(sample_path)
        assert path.name == "registered-pool-samples.jsonl"
        assert path.read_text(encoding="utf-8") == SAMPLE_TEXT
        assert target_manifest is target
        calls["readiness"] = path
        return readiness_artifact

    def load_bundle(
        *, sample_path, target_manifest_path, readiness_path, calibration_path
    ):
        paths = tuple(
            Path(path)
            for path in (sample_path, target_manifest_path, readiness_path)
        )
        assert all(path.exists() for path in paths)
        assert Path(calibration_path).as_posix().endswith(
            "reports/noncombat_ope_estimator_calibration_20260714.json"
        )
        calls["bundle"] = (*paths, Path(calibration_path))
        if loader_error is not None:
            raise estimation.EstimatorInputError(loader_error)
        if loader_blocked:
            raise estimation.EstimatorInputError(
                "independent readiness replay found overlap blockers"
            )
        return object()

    def build_estimate(bundle, *, seed, replicate_count, confidence_level):
        assert bundle is not None
        calls["estimate"] = (seed, replicate_count, confidence_level)
        return estimate

    monkeypatch.setattr(readiness, "build_current_deterministic_manifest", build_target)
    monkeypatch.setattr(readiness, "render_target_manifest_json", lambda _value: "{}\n")
    monkeypatch.setattr(readiness, "build_readiness_artifact", build_readiness)
    monkeypatch.setattr(
        readiness,
        "render_readiness_json",
        lambda value: json.dumps(value),
    )
    monkeypatch.setattr(
        readiness,
        "render_readiness_markdown",
        lambda _value: "ready\n",
    )
    monkeypatch.setattr(estimation, "load_estimator_bundle", load_bundle)
    monkeypatch.setattr(estimate_artifacts, "build_estimate_artifact", build_estimate)
    monkeypatch.setattr(
        estimate_artifacts,
        "render_estimate_json",
        lambda value: json.dumps(value, sort_keys=True) + "\n",
    )
    monkeypatch.setattr(
        estimate_artifacts,
        "render_estimate_markdown",
        lambda _value: "estimate\n",
    )
    monkeypatch.setattr(
        expansion,
        "derive_outcome_evidence_gate_metrics",
        lambda *_args, **_kwargs: _metrics(
            supported_victories=supported_victories,
            ess_fraction=ess_fraction,
        ),
    )
    return calls


def test_registered_finalizer_runs_frozen_production_pipeline_once(
    tmp_path, monkeypatch
):
    registration = _registration(tmp_path)
    calls = _patch_pipeline(monkeypatch)

    result = expansion.finalize_registered_outcome_evidence(
        registration,
        run_lock_hash=RUN_LOCK_HASH,
        ledger_snapshot=_ledger_snapshot(registration),
        pool=_pool(registration),
    )

    assert calls["target"][1] == hashlib.sha256(
        SAMPLE_TEXT.encode("utf-8")
    ).hexdigest()
    assert calls["estimate"] == (
        f"{STUDY_ID}:current-deterministic-bootstrap-v1",
        10_000,
        Fraction(95, 100),
    )
    assert result["closeout"]["status"] == "ready"
    assert result["closeout"]["gates"][
        "formal_noncombat_rl_training_ready"
    ] is False
    assert result["closeout"]["gates"]["live_policy_promotion_ready"] is False
    for path in result["paths"].values():
        assert Path(path).is_file()

    with pytest.raises(expansion.OutcomeEvidencePoolError, match="already finalized"):
        expansion.finalize_registered_outcome_evidence(
            registration,
            run_lock_hash=RUN_LOCK_HASH,
            ledger_snapshot=_ledger_snapshot(registration),
            pool=_pool(registration),
        )


def test_registered_finalizer_refuses_an_existing_atomic_claim(
    tmp_path, monkeypatch
):
    registration = _registration(tmp_path)
    claim_path = Path(registration.artifact_root) / "finalization-claim.json"
    claim_path.parent.mkdir(parents=True)
    claim_path.write_text("existing claim\n", encoding="utf-8")
    monkeypatch.setattr(
        expansion,
        "render_registered_pool_samples",
        lambda _pool_value: pytest.fail("claimed study must not read the pool"),
    )

    with pytest.raises(expansion.OutcomeEvidencePoolError, match="already finalized"):
        expansion.finalize_registered_outcome_evidence(
            registration,
            run_lock_hash=RUN_LOCK_HASH,
            ledger_snapshot=_ledger_snapshot(registration),
            pool=_pool(),
        )

    assert claim_path.read_text(encoding="utf-8") == "existing claim\n"


def test_registered_finalizer_retains_claim_after_transaction_failure(
    tmp_path, monkeypatch
):
    registration = _registration(tmp_path)
    _patch_pipeline(monkeypatch)

    def fail_transaction(_replacements):
        raise OSError("injected artifact transaction failure")

    monkeypatch.setattr(readiness, "_replace_files_transactionally", fail_transaction)

    with pytest.raises(OSError, match="injected artifact transaction failure"):
        expansion.finalize_registered_outcome_evidence(
            registration,
            run_lock_hash=RUN_LOCK_HASH,
            ledger_snapshot=_ledger_snapshot(registration),
            pool=_pool(registration),
        )

    artifact_root = Path(registration.artifact_root)
    claim_path = artifact_root / "finalization-claim.json"
    assert json.loads(claim_path.read_text(encoding="utf-8"))["mode"] == "complete"
    assert sorted(path.name for path in artifact_root.iterdir()) == [claim_path.name]

    monkeypatch.setattr(
        expansion,
        "render_registered_pool_samples",
        lambda _pool_value: pytest.fail("claimed study must not read the pool"),
    )
    with pytest.raises(expansion.OutcomeEvidencePoolError, match="already finalized"):
        expansion.finalize_registered_outcome_evidence(
            registration,
            run_lock_hash=RUN_LOCK_HASH,
            ledger_snapshot=_ledger_snapshot(registration),
            pool=_pool(registration),
        )


def test_registered_finalizer_rejects_a_pool_without_study_bindings(
    tmp_path, monkeypatch
):
    registration = _registration(tmp_path)
    _patch_pipeline(monkeypatch)

    with pytest.raises(expansion.OutcomeEvidencePoolError, match="run lock hash"):
        expansion.finalize_registered_outcome_evidence(
            registration,
            run_lock_hash=RUN_LOCK_HASH,
            ledger_snapshot=_ledger_snapshot(registration),
            pool=_pool(),
        )


def test_registered_finalizer_never_substitutes_floor_for_supported_victory(
    tmp_path, monkeypatch
):
    registration = _registration(tmp_path)
    _patch_pipeline(monkeypatch, supported_victories=2)

    result = expansion.finalize_registered_outcome_evidence(
        registration,
        run_lock_hash=RUN_LOCK_HASH,
        ledger_snapshot=_ledger_snapshot(registration),
        pool=_pool(registration),
    )

    closeout = result["closeout"]
    assert closeout["status"] == "inconclusive"
    assert "minimum_supported_victories" in closeout["blockers"]
    assert "floor_reached" not in expansion.render_outcome_evidence_closeout_json(
        closeout
    )


def test_registered_finalizer_rejects_downstream_training_or_promotion_authority(
    tmp_path, monkeypatch
):
    registration = _registration(tmp_path)
    _patch_pipeline(monkeypatch, unsafe=True)

    with pytest.raises(expansion.OutcomeEvidencePoolError, match="authority"):
        expansion.finalize_registered_outcome_evidence(
            registration,
            run_lock_hash=RUN_LOCK_HASH,
            ledger_snapshot=_ledger_snapshot(registration),
            pool=_pool(registration),
        )

    assert not Path(registration.artifact_root).exists()


def test_registered_finalizer_closes_out_when_estimator_input_is_not_ready(
    tmp_path, monkeypatch
):
    registration = _registration(tmp_path)
    _patch_pipeline(
        monkeypatch,
        ess_fraction=Fraction(499, 1000),
        loader_blocked=True,
        readiness_ready=False,
    )

    result = expansion.finalize_registered_outcome_evidence(
        registration,
        run_lock_hash=RUN_LOCK_HASH,
        ledger_snapshot=_ledger_snapshot(registration),
        pool=_pool(registration),
    )

    closeout = result["closeout"]
    estimate = json.loads(
        Path(result["paths"]["estimate_json"]).read_text(encoding="utf-8")
    )
    assert closeout["status"] == "inconclusive"
    assert "minimum_ess_fraction" in closeout["blockers"]
    assert estimate["schema_version"] == (
        "noncombat-outcome-evidence-estimate-blocked-v1"
    )
    assert estimate["estimates"] is None
    assert estimate["bootstrap"] is None
    assert estimate["influence"] is None
    assert estimate["gates"]["ope_estimate_ready"] is False
    assert estimate["gates"]["policy_comparison_ready"] is False
    assert estimate["gates"]["formal_noncombat_rl_training_ready"] is False
    assert estimate["gates"]["live_policy_promotion_ready"] is False


def test_registered_finalizer_does_not_mask_ready_estimator_failure(
    tmp_path, monkeypatch
):
    registration = _registration(tmp_path)
    _patch_pipeline(monkeypatch, loader_blocked=True, readiness_ready=True)

    with pytest.raises(
        expansion.OutcomeEvidencePoolError,
        match="production OPE finalization failed",
    ):
        expansion.finalize_registered_outcome_evidence(
            registration,
            run_lock_hash=RUN_LOCK_HASH,
            ledger_snapshot=_ledger_snapshot(registration),
            pool=_pool(registration),
        )

    assert not Path(registration.artifact_root).exists()


@pytest.mark.parametrize(
    "loader_error",
    [
        "stale calibration estimator implementation hash",
        "independent readiness replay failed: sample hash mismatch",
        "independent readiness replay failed: target hash mismatch",
        "independent readiness replay failed: readiness hash mismatch",
    ],
)
def test_registered_finalizer_does_not_mask_integrity_failure_when_not_ready(
    tmp_path, monkeypatch, loader_error
):
    registration = _registration(tmp_path)
    _patch_pipeline(
        monkeypatch,
        loader_error=loader_error,
        readiness_ready=False,
    )

    with pytest.raises(
        expansion.OutcomeEvidencePoolError,
        match="production OPE finalization failed",
    ):
        expansion.finalize_registered_outcome_evidence(
            registration,
            run_lock_hash=RUN_LOCK_HASH,
            ledger_snapshot=_ledger_snapshot(registration),
            pool=_pool(registration),
        )

    assert not Path(registration.artifact_root).exists()


def test_integrity_stop_finalizer_writes_only_a_blocked_closeout(tmp_path):
    registration = _registration(tmp_path)
    ledger_snapshot = {
        "active_slot": {
            "session_id": registration.slots[1].session_id,
            "slot_number": 2,
        },
        "all_slots_terminal": False,
        "global_stop": {"reason": "source lock drift"},
        "initialized": True,
        "terminal_slot_count": 1,
        "terminal_slots": [
            {
                "session_id": registration.slots[0].session_id,
                "slot_number": 1,
                "terminal_status": "completed",
            }
        ],
    }

    result = expansion.finalize_registered_integrity_stop(
        registration,
        run_lock_hash=RUN_LOCK_HASH,
        ledger_snapshot=ledger_snapshot,
    )

    closeout = result["closeout"]
    assert set(result["paths"]) == {"closeout_json", "closeout_markdown"}
    assert closeout["status"] == "blocked"
    assert closeout["integrity_stop"] == {"reason": "source lock drift"}
    assert closeout["source"] == {
        "calibration_file_sha256": None,
        "estimate_file_sha256": None,
        "pool_manifest_hash": None,
        "readiness_file_sha256": None,
        "target_manifest_hash": None,
    }
    assert closeout["slots"][0]["terminal_status"] == "completed"
    assert closeout["slots"][1]["terminal_status"] == "blocked"
    assert all(
        slot["terminal_status"] == "unlaunched"
        for slot in closeout["slots"][2:]
    )
    assert closeout["gates"]["outcome_evidence_expansion_ready"] is False
    assert closeout["gates"]["formal_noncombat_rl_training_ready"] is False
    assert closeout["gates"]["live_policy_promotion_ready"] is False
    assert "source lock drift" in Path(
        result["paths"]["closeout_markdown"]
    ).read_text(encoding="utf-8")


def test_integrity_stop_finalizer_retains_claim_after_transaction_failure(
    tmp_path, monkeypatch
):
    registration = _registration(tmp_path)
    ledger_snapshot = {
        "active_slot": None,
        "all_slots_terminal": False,
        "global_stop": {"reason": "source lock drift"},
        "initialized": True,
        "terminal_slot_count": 0,
        "terminal_slots": [],
    }

    def fail_transaction(_replacements):
        raise OSError("injected blocked transaction failure")

    monkeypatch.setattr(readiness, "_replace_files_transactionally", fail_transaction)

    with pytest.raises(OSError, match="injected blocked transaction failure"):
        expansion.finalize_registered_integrity_stop(
            registration,
            run_lock_hash=RUN_LOCK_HASH,
            ledger_snapshot=ledger_snapshot,
        )

    artifact_root = Path(registration.artifact_root)
    claim_path = artifact_root / "finalization-claim.json"
    assert json.loads(claim_path.read_text(encoding="utf-8"))["mode"] == (
        "integrity_stop"
    )
    assert sorted(path.name for path in artifact_root.iterdir()) == [claim_path.name]

    with pytest.raises(expansion.OutcomeEvidencePoolError, match="already finalized"):
        expansion.finalize_registered_integrity_stop(
            registration,
            run_lock_hash=RUN_LOCK_HASH,
            ledger_snapshot=ledger_snapshot,
        )
