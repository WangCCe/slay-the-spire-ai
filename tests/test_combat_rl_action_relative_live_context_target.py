from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import pytest
import torch

from analysis_scripts import combat_rl_action_relative_live_context_target as target
from analysis_scripts.combat_rl_real_context_balanced_corpus import (
    SEMANTIC_CONTINUOUS_INDICES,
)


def _timestamp(value: float) -> str:
    return datetime.fromtimestamp(value, tz=timezone.utc).isoformat().replace(
        "+00:00", "Z"
    )


def _event(value: float, *, floor: int = 23, turn: int = 2, **overrides):
    event = {
        "event_type": "decision",
        "session_id": "session-a",
        "decision_sequence": 1,
        "state_sha256": "a" * 64,
        "timestamp": _timestamp(value),
        "floor": floor,
        "turn": turn,
        "eligible": True,
        "support_reason": "",
        "parent_action_index": 90,
        "guard_action_index": 1,
        "executed_action_index": 1,
        "executed_action_encodable": True,
        "executed_action_legal": True,
        "candidate_has_authority": False,
        "runtime_error_type": "",
    }
    event.update(overrides)
    return event


def _decision(value: float, *, floor: int = 23, turn: int = 2, hp: int = 20):
    return {
        "unix_time": value,
        "in_combat": True,
        "floor": floor,
        "turn": turn,
        "player": {"current_hp": hp, "max_hp": 80},
        "potions": [
            {"id": "Potion Slot"},
            {"id": "Fire Potion"},
            {"id": "Potion Slot"},
        ],
        "relics": [{"id": "a"}, {"id": "b"}, {"id": "c"}],
    }


def _run(timestamp: int, seed: int):
    return {
        "timestamp": timestamp,
        "seed_played": seed,
        "sha256": f"{seed:064x}",
        "path": f"runs/{timestamp}.run",
        "victory": False,
        "floor_reached": 30,
    }


def test_extract_target_rows_uses_exact_guard_membership_join_and_run() -> None:
    rows, exclusions = target.extract_target_rows(
        events=[
            _event(100.0),
            _event(
                100.5,
                decision_sequence=2,
                floor=24,
                parent_action_index=1,
                eligible=False,
                support_reason="parent_not_end_turn",
                guard_action_index=None,
            ),
        ],
        decision_rows=[_decision(100.012), _decision(100.51, floor=24)],
        completed_runs=[_run(101, 11)],
        batch_id="batch-1",
    )

    assert exclusions == {"parent_not_end_turn": 1}
    assert len(rows) == 1
    row = rows[0]
    assert row["run_timestamp"] == 101
    assert row["run_seed"] == 11
    assert row["state_sha256"] == "a" * 64
    assert row["join_delta_ms"] == pytest.approx(12.0)
    assert row["context_cell_id"] == "floor_23_27|p1|r3|h1"
    assert row["player_hp_ratio"] == pytest.approx(0.25)


def test_completed_run_loader_accepts_sts_decimal_string_seed(tmp_path: Path) -> None:
    run_dir = tmp_path / "runs"
    run_dir.mkdir()
    (run_dir / "101.run").write_text(
        json.dumps(
            {
                "timestamp": 101,
                "seed_played": "-7380894153858987122",
                "victory": False,
                "floor_reached": 12,
            }
        ),
        encoding="utf-8",
    )

    runs = target.load_completed_runs(run_dir)

    assert runs[0]["seed_played"] == -7380894153858987122


def test_batch_recovery_status_resumes_only_to_five_runs(tmp_path: Path) -> None:
    run_dir = tmp_path / "runs"
    run_dir.mkdir()
    for timestamp in range(101, 104):
        (run_dir / f"{timestamp}.run").write_text(
            json.dumps(
                {
                    "timestamp": timestamp,
                    "seed_played": str(timestamp + 1000),
                    "victory": False,
                    "floor_reached": 16,
                }
            ),
            encoding="utf-8",
        )

    status = target.batch_recovery_status(run_dir)

    assert status["completed_run_count"] == 3
    assert status["remaining_run_count"] == 2
    assert status["complete"] is False


def test_target_shadow_conditions_ignore_candidate_latency_only() -> None:
    conditions = {
        name: True for name in target.TARGET_SHADOW_REQUIRED_CONDITIONS
    }
    conditions["latency_finite_and_within_ceiling"] = False

    selected = target.target_shadow_conditions(
        {"readiness_conditions": conditions}
    )

    assert all(selected.values())
    assert "latency_finite_and_within_ceiling" not in selected


def test_extract_target_rows_rejects_authority_ambiguous_or_reused_join() -> None:
    with pytest.raises(ValueError, match="candidate authority"):
        target.extract_target_rows(
            events=[_event(100.0, candidate_has_authority=True)],
            decision_rows=[_decision(100.0)],
            completed_runs=[_run(101, 11)],
            batch_id="batch-1",
        )

    with pytest.raises(ValueError, match="decision-state join"):
        target.extract_target_rows(
            events=[_event(100.0), _event(100.001, decision_sequence=2)],
            decision_rows=[_decision(100.0)],
            completed_runs=[_run(101, 11)],
            batch_id="batch-1",
        )


def test_target_sufficiency_binds_run_and_development_seed_isolation() -> None:
    rows = []
    for index, floor in enumerate((23, 24, 30, 31), start=1):
        rows.append(
            {
                "batch_id": "batch-1",
                "session_id": "session-a",
                "decision_sequence": index,
                "state_sha256": f"{index:064x}",
                "run_timestamp": 100 + index,
                "run_seed": index,
                "floor": floor,
                "context_cell_id": target.context_cell_id(
                    floor=floor,
                    potion_occupied_slots=0,
                    relic_occupied_slots=1,
                    player_hp_quartile=3,
                ),
                "floor_ratio": floor / 50.0,
                "player_hp_ratio": 1.0,
                "potion_occupied_slots": 0,
                "relic_occupied_slots": 1,
                "player_hp_quartile": 3,
            }
        )
    evidence = target.validate_target_sufficiency(
        rows,
        completed_runs=[_run(101 + index, index + 1) for index in range(4)],
        development_run_seeds={99},
        expected_run_count=4,
        minimum_row_count=4,
        minimum_late_row_count=4,
    )
    assert evidence["all_conditions_passed"] is True

    with pytest.raises(ValueError, match="development run seed"):
        target.validate_target_sufficiency(
            rows,
            completed_runs=[_run(101 + index, index + 1) for index in range(4)],
            development_run_seeds={1},
            expected_run_count=4,
            minimum_row_count=4,
            minimum_late_row_count=4,
        )


def test_context_target_weights_match_cells_without_fake_replay() -> None:
    continuous = torch.zeros((4, 328), dtype=torch.float32)
    continuous[:, 3] = torch.tensor([23, 23, 30, 30]) / 50.0
    continuous[:, SEMANTIC_CONTINUOUS_INDICES["player_hp_ratio"]] = torch.tensor(
        [0.25, 0.25, 0.75, 0.75]
    )
    simulator = {
        "partition": "evaluation",
        "tensors": {
            "continuous": continuous,
            "potion_ids": torch.tensor(
                [[1, 0, 0], [1, 0, 0], [0, 0, 0], [0, 0, 0]]
            ),
            "relic_ids": torch.tensor(
                [[1, 2, 3], [1, 2, 3], [1, 2, 0], [1, 2, 0]]
            ),
        },
        "metadata": [{"floor": value} for value in (23, 23, 30, 30)],
        "row_count": 4,
    }
    target_rows = [
        {
            "context_cell_id": "floor_23_27|p1|r3|h1",
            "floor": 23,
            "floor_ratio": 23 / 50.0,
            "player_hp_ratio": 0.25,
            "potion_occupied_slots": 1,
            "relic_occupied_slots": 3,
            "player_hp_quartile": 1,
        },
        {
            "context_cell_id": "floor_28_34|p0|r2|h3",
            "floor": 30,
            "floor_ratio": 30 / 50.0,
            "player_hp_ratio": 0.75,
            "potion_occupied_slots": 0,
            "relic_occupied_slots": 2,
            "player_hp_quartile": 3,
        },
    ]

    result = target.derive_context_weights_from_target(target_rows, simulator)

    assert result["metrics"]["real_context_mass_covered"] == 1.0
    assert result["metrics"]["effective_sample_size"] == pytest.approx(4.0)
    assert result["metrics"]["maximum_normalized_weight"] == pytest.approx(0.25)
    assert result["weights"].tolist() == pytest.approx([0.25] * 4)


def test_target_registration_cross_binds_four_shadow_batches(tmp_path: Path) -> None:
    development_audit = tmp_path / "audit.json"
    development_audit.write_text("{}\n", encoding="ascii")
    candidate = tmp_path / "candidate.pth"
    parent = tmp_path / "parent.pth"
    candidate.write_bytes(b"candidate")
    parent.write_bytes(b"parent")
    batches = []
    for index in range(4):
        batch_id = f"batch-{index + 1}"
        trace = (target.REPO_ROOT / "reports" / batch_id / "trace.jsonl").resolve()
        registration_path = tmp_path / f"{batch_id}.json"
        registration_path.write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "experiment_id": batch_id,
                    "mode": "shadow",
                    "source_commit": "a" * 40,
                    "inference_device": "cpu",
                    "candidate_artifact": {
                        "path": str(candidate.resolve()),
                        "sha256": "b" * 64,
                        "parent_checkpoint_sha256": "c" * 64,
                        "train_corpus_sha256": "d" * 64,
                        "evaluation_corpus_sha256": "e" * 64,
                    },
                    "production_parent_checkpoint": {
                        "path": str(parent.resolve()),
                        "sha256": "f" * 64,
                    },
                    "parent_state_dict_sha256": "1" * 64,
                    "trace_path": str(trace),
                    "maximum_decision_count": 1024,
                    "readiness_gates": {
                        "minimum_eligible_count": 50,
                        "maximum_p95_latency_ms": 20.0,
                    },
                }
            ),
            encoding="ascii",
        )
        batches.append(
            {
                "batch_id": batch_id,
                "shadow_registration_path": str(registration_path.resolve()),
                "trace_path": str(trace),
                "decision_trace_path": str(
                    trace.parent / "ai_decision_trace_clean.jsonl"
                ),
                "run_dir": str(trace.parent / "runs"),
            }
        )

    registration = target.build_target_registration(
        experiment_id="target-fixture",
        source_commit="a" * 40,
        development_audit_path=development_audit,
        development_run_seeds=range(20),
        batches=batches,
        output_dir=target.REPO_ROOT / "reports" / "target-fixture",
    )

    validated = target.validate_target_registration(
        registration, require_batch_outputs=False
    )
    assert len(validated["batches"]) == 4
    assert validated["production_parent"]["parameter_sha256"] == "1" * 64
    assert validated["authority"]["candidate_action_takeover"] is False
    command = validated["batches"][0]["communication_mod_command"]
    assert command[0] == str(target.EXPECTED_INTERPRETER)
    assert command[command.index("--max-games") + 1] == "5"
    assert command[-2:] == [
        "--combat-action-relative-shadow-registration",
        str((tmp_path / "batch-1.json").resolve()),
    ]

    config_drifted = json.loads(json.dumps(registration))
    config_drifted["batches"][0]["communication_mod_command"][0] = "python.exe"
    with pytest.raises(ValueError, match="CommunicationMod command"):
        target.validate_target_registration(
            config_drifted, require_batch_outputs=False
        )

    drifted = dict(batches[0], trace_path="relative/trace.jsonl")
    with pytest.raises(ValueError, match="absolute"):
        target.build_target_registration(
            experiment_id="target-fixture",
            source_commit="a" * 40,
            development_audit_path=development_audit,
            development_run_seeds=range(20),
            batches=[drifted, *batches[1:]],
            output_dir=target.REPO_ROOT / "reports" / "target-fixture",
        )
