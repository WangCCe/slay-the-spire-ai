import json
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace

import pytest

import analysis_scripts.noncombat_exploration_evidence as evidence_module
import analysis_scripts.noncombat_rl_decision_loop as decision_loop_module
from analysis_scripts.noncombat_outcome_evidence_expansion import (
    OutcomeEvidencePoolError,
    RegisteredSessionEvidence,
    build_registered_pool,
    build_registration,
    collect_registered_session_evidence,
    conservative_marker_run_pairs,
    derive_outcome_evidence_gate_metrics,
    evaluate_outcome_evidence_expansion_gate,
    render_registered_pool_manifest,
    render_registered_pool_samples,
)
from analysis_scripts.noncombat_ope_readiness import (
    build_current_deterministic_manifest,
)


STUDY_ID = "noncombat-outcome-evidence-expansion-20260715"
SEED_BASE = 2_026_071_500
SOURCE_COMMIT = "a" * 40
RUN_LOCK_HASH = "b" * 64


def _registration(tmp_path):
    return build_registration(
        study_id=STUDY_ID,
        artifact_root=tmp_path / "study",
        repo_root=tmp_path / "repo",
        seed_base=SEED_BASE,
        python_executable=Path(r"D:\anaconda\envs\stsai\python.exe"),
        communication_config_path=tmp_path / "config.properties",
        checkpoint_root=tmp_path / "checkpoints",
    )


def _sample(
    *,
    session_id,
    run_id,
    decision_index=0,
    category="card_reward",
    arm="baseline",
    victory=False,
):
    if category == "card_reward":
        baseline_action = f"card_reward:take:{run_id}-{decision_index}"
        alternative_action = "card_reward:skip"
        alternative_numerator = 3
        denominator = 100
    else:
        baseline_action = f"shop:buy:{run_id}-{decision_index}"
        alternative_action = "shop:leave"
        alternative_numerator = 1
        denominator = 10
    selected_action = (
        baseline_action if arm == "baseline" else alternative_action
    )
    selected_numerator = (
        denominator - alternative_numerator
        if arm == "baseline"
        else alternative_numerator
    )
    sample_id = f"{session_id}:{run_id}:{decision_index}"
    candidate_kind = "take" if category == "card_reward" else "buy"
    return {
        "schema_version": "noncombat-rl-decision-v3",
        "sample_id": sample_id,
        "trajectory_group_id": f"run:{run_id}",
        "trajectory_session_id": f"{session_id}:trajectory:{run_id}",
        "behavior_policy_id": f"known-propensity-epsilon-v1:{session_id}",
        "behavior_policy_commit": SOURCE_COMMIT,
        "behavior_probability_status": "verified_known_propensity",
        "behavior_action_probability": selected_numerator / denominator,
        "category": category,
        "floor": 3,
        "selected_action_id": selected_action,
        "candidate_actions": [
            {
                "action_id": baseline_action,
                "available": True,
                "executable": True,
                "kind": candidate_kind,
                "label": baseline_action,
                "raw": {},
            },
            {
                "action_id": alternative_action,
                "available": True,
                "executable": True,
                "kind": "skip" if category == "card_reward" else "leave",
                "label": alternative_action,
                "raw": {},
            },
        ],
        "current_policy_label": {
            "action_id": baseline_action,
            "label": baseline_action,
        },
        "exploration": {
            "decision_id": sample_id,
            "decision_index": decision_index,
            "state_hash": f"state:{sample_id}",
            "distribution_hash": f"distribution:{sample_id}",
            "trajectory_session_id": f"{session_id}:trajectory:{run_id}",
            "session_id": session_id,
            "source_commit": SOURCE_COMMIT,
            "baseline_action_id": baseline_action,
            "alternative_action_id": alternative_action,
            "selected_arm": arm,
            "selected_probability": {
                "numerator": selected_numerator,
                "denominator": denominator,
                "value": selected_numerator / denominator,
            },
            "candidate_distribution": [
                {
                    "action_id": baseline_action,
                    "numerator": denominator - alternative_numerator,
                    "denominator": denominator,
                    "value": (denominator - alternative_numerator) / denominator,
                },
                {
                    "action_id": alternative_action,
                    "numerator": alternative_numerator,
                    "denominator": denominator,
                    "value": alternative_numerator / denominator,
                },
            ],
            "replay_status": "valid",
            "confirmation_status": "confirmed",
            "candidate_legality": "valid",
        },
        "outcome": {
            "run_file": f"{run_id}.run",
            "join_status": "matched",
            "included_in_gate": True,
            "victory": victory,
            "floor_reached": 16,
            "killed_by": "" if victory else "Slime Boss",
            "playtime": 90,
        },
    }


def _session(registration, slot_number, samples):
    slot = registration.slots[slot_number - 1]
    rows = tuple(deepcopy(sample) for sample in samples)
    run_files = tuple(
        sorted(
            {sample["outcome"]["run_file"] for sample in rows},
            key=lambda value: int(Path(value).stem),
        )
    )
    count = len(rows)
    return RegisteredSessionEvidence(
        slot_number=slot_number,
        session_id=slot.session_id,
        run_lock_hash=RUN_LOCK_HASH,
        config_sha256=f"{slot_number:064x}",
        manifest_sha256=f"{slot_number + 100:064x}",
        manifest_hash=f"{slot_number + 200:064x}",
        trace_sha256=f"{slot_number + 300:064x}",
        marker_trajectory_count=25,
        joined_run_files=run_files,
        samples=rows,
        exclusions=(),
        validation_summary={
            "candidate_legal": count,
            "confirmed": count,
            "exported": count,
            "replay_valid": count,
        },
        provenance_verified=True,
        isolation_verified=True,
    )


def _study_evidence(registration):
    sessions = []
    run_counter = 10_000
    for slot in registration.slots:
        samples = []
        for category in ("card_reward", "shop"):
            for arm in ("baseline", "alternative"):
                for _ in range(2):
                    run_counter += 1
                    samples.append(
                        _sample(
                            session_id=slot.session_id,
                            run_id=str(run_counter),
                            category=category,
                            arm=arm,
                        )
                    )
        if slot.slot_number in {1, 2}:
            for category in ("card_reward", "shop"):
                for arm in ("baseline", "alternative"):
                    run_counter += 1
                    samples.append(
                        _sample(
                            session_id=slot.session_id,
                            run_id=str(run_counter),
                            category=category,
                            arm=arm,
                        )
                    )
        sessions.append(_session(registration, slot.slot_number, samples))
    return tuple(sessions)


def _ledger_snapshot(registration):
    return {
        "active_slot": None,
        "all_slots_terminal": True,
        "global_stop": None,
        "initialized": True,
        "terminal_slot_count": 24,
        "terminal_slots": [
            {
                "complete_trajectories": 25,
                "marker_start_count": (slot.slot_number - 1) * 25,
                "marker_end_count": slot.slot_number * 25,
                "process_exit_code": 0,
                "session_id": slot.session_id,
                "slot_number": slot.slot_number,
                "terminal_status": "completed",
            }
            for slot in registration.slots
        ],
    }


def _build(registration, sessions):
    return build_registered_pool(
        registration,
        run_lock_hash=RUN_LOCK_HASH,
        ledger_snapshot=_ledger_snapshot(registration),
        sessions=sessions,
    )


def test_registered_pool_aggregates_exact_support_across_all_slots(tmp_path):
    registration = _registration(tmp_path)
    pool = _build(registration, _study_evidence(registration))

    assert pool.manifest["accounting"]["registered_slot_count"] == 24
    assert pool.manifest["accounting"]["included_trajectory_count"] == 200
    assert pool.manifest["accounting"]["excluded_trajectory_count"] == 400
    assert (
        pool.manifest["accounting"]["included_trajectory_count"]
        + pool.manifest["accounting"]["excluded_trajectory_count"]
        == pool.manifest["accounting"]["marker_trajectory_count"]
    )
    assert pool.manifest["aggregate_arm_support"] == {
        "card_reward": {"alternative": 50, "baseline": 50},
        "shop": {"alternative": 50, "baseline": 50},
    }
    assert max(
        slot["included_decision_count"] for slot in pool.manifest["slots"]
    ) < 50
    card_alternative = next(
        sample
        for sample in pool.samples
        if sample["category"] == "card_reward"
        and sample["exploration"]["selected_arm"] == "alternative"
    )
    assert card_alternative["exploration"]["selected_probability"] == {
        "denominator": 100,
        "numerator": 3,
        "value": 0.03,
    }


@pytest.mark.parametrize("mutation", ["missing", "extra", "run_lock"])
def test_registered_pool_rejects_session_set_or_lock_drift(tmp_path, mutation):
    registration = _registration(tmp_path)
    sessions = list(_study_evidence(registration))
    if mutation == "missing":
        sessions.pop()
    elif mutation == "extra":
        sessions.append(replace(sessions[-1], slot_number=25, session_id="extra"))
    else:
        sessions[0] = replace(sessions[0], run_lock_hash="c" * 64)

    with pytest.raises(OutcomeEvidencePoolError):
        _build(registration, sessions)


def test_registered_pool_rejects_duplicate_trajectory_across_sessions(tmp_path):
    registration = _registration(tmp_path)
    sessions = list(_study_evidence(registration))
    first = sessions[0].samples[0]
    duplicate = deepcopy(sessions[1].samples[0])
    duplicate["trajectory_group_id"] = first["trajectory_group_id"]
    duplicate["outcome"]["run_file"] = first["outcome"]["run_file"]
    sessions[1] = replace(
        sessions[1],
        samples=(duplicate, *sessions[1].samples[1:]),
        joined_run_files=(
            first["outcome"]["run_file"],
            *sessions[1].joined_run_files[1:],
        ),
    )

    with pytest.raises(OutcomeEvidencePoolError, match="duplicate.*trajectory"):
        _build(registration, sessions)


def test_registered_pool_rejects_selective_sample_omission(tmp_path):
    registration = _registration(tmp_path)
    sessions = list(_study_evidence(registration))
    sessions[0] = replace(sessions[0], samples=sessions[0].samples[1:])

    with pytest.raises(OutcomeEvidencePoolError, match="exported|omission"):
        _build(registration, sessions)


def test_registered_pool_rejects_conflicting_terminal_outcome(tmp_path):
    registration = _registration(tmp_path)
    sessions = list(_study_evidence(registration))
    first = deepcopy(sessions[0].samples[0])
    conflict = deepcopy(first)
    conflict["sample_id"] += ":conflict"
    conflict["exploration"]["decision_id"] = conflict["sample_id"]
    conflict["exploration"]["decision_index"] = 1
    conflict["outcome"]["victory"] = not first["outcome"]["victory"]
    conflict["outcome"]["killed_by"] = ""
    rows = (first, conflict, *sessions[0].samples[1:])
    summary = dict(sessions[0].validation_summary)
    for field in ("candidate_legal", "confirmed", "exported", "replay_valid"):
        summary[field] += 1
    sessions[0] = replace(sessions[0], samples=rows, validation_summary=summary)

    with pytest.raises(OutcomeEvidencePoolError, match="outcome.*conflict"):
        _build(registration, sessions)


def test_registered_pool_bytes_are_invariant_to_input_order(tmp_path):
    registration = _registration(tmp_path)
    sessions = _study_evidence(registration)
    reordered = tuple(
        replace(session, samples=tuple(reversed(session.samples)))
        for session in reversed(sessions)
    )

    first = _build(registration, sessions)
    second = _build(registration, reordered)

    assert render_registered_pool_samples(first) == render_registered_pool_samples(
        second
    )
    assert render_registered_pool_manifest(first) == render_registered_pool_manifest(
        second
    )
    assert json.loads(render_registered_pool_manifest(first))[
        "pool_manifest_hash"
    ] == first.manifest["pool_manifest_hash"]


def test_registered_pool_preserves_session_and_trajectory_exclusion_reasons(
    tmp_path,
):
    registration = _registration(tmp_path)
    sessions = list(_study_evidence(registration))
    sessions[0] = replace(
        sessions[0],
        joined_run_files=(*sessions[0].joined_run_files, "999999.run"),
        exclusions=(
            {"decision_id": "excluded-decision", "reason": "confirmation_missing"},
        ),
    )

    pool = _build(registration, sessions)

    assert pool.manifest["slots"][0]["export_exclusions"] == [
        {"decision_id": "excluded-decision", "reason": "confirmation_missing"}
    ]
    assert any(
        row["run_file"] == "999999.run"
        and row["reason"] == "no_complete_confirmed_decision"
        for row in pool.manifest["excluded_trajectories"]
    )


def test_registered_pool_renderers_reject_tampered_content(tmp_path):
    registration = _registration(tmp_path)
    sample_pool = _build(registration, _study_evidence(registration))
    sample_pool.samples[0]["floor"] = 99
    with pytest.raises(OutcomeEvidencePoolError, match="sample hash"):
        render_registered_pool_samples(sample_pool)

    manifest_pool = _build(registration, _study_evidence(registration))
    manifest_pool.manifest["accounting"]["included_trajectory_count"] = 0
    with pytest.raises(OutcomeEvidencePoolError, match="manifest hash"):
        render_registered_pool_manifest(manifest_pool)


def test_gate_metrics_are_derived_from_pool_and_deterministic_current(tmp_path):
    registration = _registration(tmp_path)
    pool = _build(registration, _study_evidence(registration))
    target = build_current_deterministic_manifest(
        pool.samples,
        source_sample_sha256=pool.manifest["sample_jsonl_sha256"],
    )

    metrics = derive_outcome_evidence_gate_metrics(
        registration,
        pool=pool,
        target_manifest=target,
        ledger_snapshot=_ledger_snapshot(registration),
    )
    gate = evaluate_outcome_evidence_expansion_gate(registration, metrics)

    assert metrics.complete_trajectory_count == 200
    assert metrics.nonzero_weight_trajectory_count == 100
    assert metrics.category_arm_support == {
        "card_reward": {"alternative": 50, "baseline": 50},
        "shop": {"alternative": 50, "baseline": 50},
    }
    assert isinstance(metrics.ess_fraction, Fraction)
    assert metrics.supported_victory_count == 0
    assert gate["blockers"] == [
        "minimum_complete_trajectories",
        "minimum_ess_fraction",
        "minimum_supported_victories",
    ]


def test_conservative_marker_run_pairs_require_mutual_uniqueness():
    assert conservative_marker_run_pairs(
        marker_timestamps=[100, 200],
        run_timestamps=[98, 197],
    ) == ((0, 98), (1, 197))
    assert conservative_marker_run_pairs(
        marker_timestamps=[100, 101],
        run_timestamps=[100],
    ) == ()
    assert conservative_marker_run_pairs(
        marker_timestamps=[100],
        run_timestamps=[102],
    ) == ()


def test_collect_registered_session_evidence_uses_global_registered_joins(
    tmp_path, monkeypatch
):
    registration = _registration(tmp_path)
    runs_root = tmp_path / "runs"
    run_dir = runs_root / "IRONCLAD"
    run_dir.mkdir(parents=True)
    marker_path = runs_root / "ai_games.txt"
    markers = [1_000 + index * 20 for index in range(600)]
    run_timestamps = [marker - 2 for marker in markers]
    marker_path.write_text(
        "".join(f"{marker}\n" for marker in markers),
        encoding="utf-8",
    )
    for run_timestamp in run_timestamps:
        (run_dir / f"{run_timestamp}.run").write_text("{}", encoding="utf-8")

    communication_path = str((tmp_path / "config.properties").resolve())
    checkpoint_path = str((tmp_path / "checkpoints" / "model.pth").resolve())
    isolation = {
        communication_path: {
            "exists": True,
            "is_file": True,
            "semantic_sha256": "1" * 64,
            "sha256": "2" * 64,
            "size": 10,
        },
        checkpoint_path: {
            "exists": True,
            "is_file": True,
            "sha256": "3" * 64,
            "size": 20,
        },
    }
    run_lock = {
        "checkpoints": {
            "files": [
                {"path": checkpoint_path, "sha256": "3" * 64, "size": 20}
            ],
            "patterns": ["*.pth"],
            "root": str((tmp_path / "checkpoints").resolve()),
        },
        "communication_mod": {
            "path": communication_path,
            "semantic_sha256": "1" * 64,
        },
        "registration": {"canonical_hash": registration.registration_hash},
        "run_lock_hash": RUN_LOCK_HASH,
        "source": {"commit": SOURCE_COMMIT},
        "study_id": STUDY_ID,
    }
    for slot in registration.slots:
        Path(slot.config_path).parent.mkdir(parents=True, exist_ok=True)
        Path(slot.config_path).write_text("{}\n", encoding="utf-8")
        Path(slot.trace_path).write_text("", encoding="utf-8")
        manifest = {
            "effective_config": {
                "study_id": STUDY_ID,
                "study_registration_hash": registration.registration_hash,
                "study_run_lock_hash": RUN_LOCK_HASH,
                "study_slot_number": slot.slot_number,
            },
            "manifest_hash": f"{slot.slot_number + 400:064x}",
            "manifest_path": slot.manifest_path,
            "pre_session_isolation_hashes": isolation,
            "session_id": slot.session_id,
            "source": {"commit": SOURCE_COMMIT},
            "trace_path": slot.trace_path,
        }
        Path(slot.manifest_path).write_text(
            json.dumps(manifest, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    outcome_calls = []

    def fake_outcome_loader(
        _runs_root,
        character,
        limit,
        ai_markers_path,
        run_files,
    ):
        assert character == "IRONCLAD"
        assert limit == 0
        assert Path(ai_markers_path) == marker_path
        outcome_calls.append(tuple(run_files))
        return [
            {
                "ai_marked": True,
                "end_unix": int(Path(run_file).stem),
                "floor_reached": 16,
                "killed_by": "Slime Boss",
                "playtime": 90,
                "run_file": run_file,
                "start_unix": int(Path(run_file).stem) - 90,
                "victory": False,
            }
            for run_file in run_files
        ]

    def fake_exporter(
        _trace_path,
        manifest_path,
        *,
        outcomes,
        expected_pre_isolation_hashes,
        expected_source_commit,
    ):
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        session_id = manifest["session_id"]
        first_run = outcomes[0]["run_file"]
        sample = _sample(
            session_id=session_id,
            run_id=Path(first_run).stem,
        )
        assert expected_pre_isolation_hashes == isolation
        assert expected_source_commit == SOURCE_COMMIT
        return SimpleNamespace(
            exclusions=(),
            manifest=manifest,
            provenance_verified=True,
            samples=(sample,),
            validation_summary={
                "candidate_legal": 1,
                "confirmed": 1,
                "exported": 1,
                "replay_valid": 1,
            },
        )

    monkeypatch.setattr(decision_loop_module, "load_run_outcomes", fake_outcome_loader)
    monkeypatch.setattr(
        evidence_module,
        "export_confirmed_exploration_samples",
        fake_exporter,
    )

    sessions = collect_registered_session_evidence(
        registration,
        run_lock=run_lock,
        ledger_snapshot=_ledger_snapshot(registration),
        marker_path=marker_path,
        runs_root=runs_root,
    )

    assert [session.slot_number for session in sessions] == list(range(1, 25))
    assert all(len(session.joined_run_files) == 25 for session in sessions)
    assert len(outcome_calls) == 24
    assert len({run_file for call in outcome_calls for run_file in call}) == 600
    assert outcome_calls[0][0] == f"{run_timestamps[0]}.run"
    assert outcome_calls[-1][-1] == f"{run_timestamps[-1]}.run"
