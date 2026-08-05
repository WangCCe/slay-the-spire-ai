from __future__ import annotations

import base64
import hashlib
import json
import math
import struct
from pathlib import Path

import pytest

from analysis_scripts.noncombat_state_conditioned_collapse_audit import (
    CollapseAuditError,
    analyze_decision_rows,
    audit_bundle,
    locate_saturation_boundaries,
    publish_audit,
    render_markdown,
)


AUTHORITY_NAMES = (
    "causal_claim_authorized",
    "cohort_materialization_authorized",
    "communication_mod_authorized",
    "environment_construction_authorized",
    "execution_authorized",
    "formal_rl_authorized",
    "fresh_evidence_authorized",
    "gameplay_authorized",
    "live_execution_authorized",
    "model_fitting_authorized",
    "native_loading_authorized",
    "ope_authorized",
    "policy_loading_authorized",
    "production_checkpoint_mutation_authorized",
    "promotion_authorized",
    "qualification_authorized",
    "seed_access_authorized",
    "target_supported_outcome_authorized",
    "training_authorized",
)


def _authority() -> dict[str, bool]:
    return {name: False for name in AUTHORITY_NAMES}


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=True, indent=2, sort_keys=True
    ).encode("utf-8") + b"\n"


def _write_json(path: Path, value: object) -> bytes:
    payload = _canonical(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return payload


def _tensor(values: list[float], shape: list[int] | None = None) -> dict[str, object]:
    data = struct.pack(f"<{len(values)}f", *values)
    return {
        "byte_order": "little",
        "data_base64": base64.b64encode(data).decode("ascii"),
        "data_sha256": hashlib.sha256(data).hexdigest(),
        "dtype": "float32",
        "shape": shape or [len(values)],
    }


def _model(value: float) -> dict[str, object]:
    return {
        "hidden.bias": _tensor([value]),
        "hidden.weight": _tensor([value, value], [1, 2]),
        "scorer.bias": _tensor([value]),
        "scorer.weight": _tensor([value], [1, 1]),
    }


def _decision(
    decision_id: str,
    *,
    selected: str,
    take_score: float,
    skip_score: float,
) -> dict[str, object]:
    candidates = [
        {"action_id": "card_reward:take:0:0:a", "kind": "take"},
        {"action_id": "card_reward:take:0:1:b", "kind": "take"},
        {"action_id": "card_reward:take:0:2:c", "kind": "take"},
        {"action_id": "card_reward:skip:0", "kind": "skip"},
    ]
    return {
        "candidate_scores": {
            candidates[0]["action_id"]: take_score,
            candidates[1]["action_id"]: take_score,
            candidates[2]["action_id"]: take_score,
            candidates[3]["action_id"]: skip_score,
        },
        "candidates": candidates,
        "category": "card_reward",
        "decision_id": decision_id,
        "selected_action_id": selected,
        "state_effect": {
            "category": "card_reward",
            "decision_id": decision_id,
            "max_abs_relative_score_change": 0.1,
            "relative_order_changed": True,
            "zero_state_scores": [0.0, 0.0, 0.0, 0.0],
        },
    }


def _episode(
    seed: int,
    selected_action_ids: list[str],
    *,
    chunk_index: int | None,
) -> dict[str, object]:
    row = {
        "action_sequence_sha256": hashlib.sha256(
            _canonical(selected_action_ids)
        ).hexdigest(),
        "candidate_legality": True,
        "categories": ["card_reward"],
        "decisions": len(selected_action_ids),
        "last_supported_floor": float((chunk_index or 0) + 1),
        "outcome": "player_loss",
        "retained": True,
        "seed": seed,
        "selected_action_ids": selected_action_ids,
        "terminal_floor": float((chunk_index or 0) + 1),
        "total_reward": 0.1 * ((chunk_index or 0) + 1),
        "unsupported_reason": None,
        "victory": False,
    }
    if chunk_index is not None:
        row["chunk_index"] = chunk_index
    return row


def _chunk(index: int, row: dict[str, object]) -> dict[str, object]:
    return {
        "categories": ["card_reward"],
        "chunk_index": index,
        "diagnostic_rows": [row],
        "entropy_coefficient": 0.01,
        "episode_end": index + 1,
        "episode_rows": [
            _episode(
                100 + index,
                [str(row["selected_action_id"])],
                chunk_index=index,
            )
        ],
        "episode_start": index,
        "episodes": 1,
        "gradient_norm_after_clip": 0.1,
        "gradient_norm_before_clip": 0.1,
        "loss": 0.2,
        "mean_entropy": 0.3,
        "mean_episode_return": 0.1 * (index + 1),
        "optimizer_update": index + 1,
        "pass_index": 0,
        "unsupported_episodes": 0,
        "victories": 0,
    }


def _policy(row: dict[str, object]) -> dict[str, object]:
    episode = _episode(
        200,
        [str(row["selected_action_id"])],
        chunk_index=None,
    )
    return {
        "categories": ["card_reward"],
        "diagnostic_rows": [row],
        "diagnostics": {
            "authority": _authority(),
            "schema_version": "fixture-diagnostics",
        },
        "episode_rows": [episode],
        "replay_diagnostic_rows": [row],
        "replay_episode_rows": [episode],
        "replay_exact": True,
        "unsupported_episodes": 0,
        "victories": 0,
    }


def _make_bundle(root: Path) -> Path:
    source = root / "terminal"
    source.mkdir()
    rows = [
        _decision(
            "chunk-0:seed-100:decision-0",
            selected="card_reward:skip:0",
            take_score=0.0,
            skip_score=0.0,
        ),
        _decision(
            "chunk-1:seed-101:decision-0",
            selected="card_reward:take:0:0:a",
            take_score=1.0,
            skip_score=0.0,
        ),
        _decision(
            "chunk-2:seed-102:decision-0",
            selected="card_reward:skip:0",
            take_score=2.0,
            skip_score=0.0,
        ),
    ]
    chunks = [_chunk(index, row) for index, row in enumerate(rows)]
    artifacts: dict[str, bytes] = {}
    artifacts["training_rows.json"] = _write_json(
        source / "training_rows.json",
        {
            "chunks": chunks,
            "episode_count": 3,
            "schema_version": "noncombat-state-conditioned-training-rows-v1",
        },
    )
    diagnostics = {
        "authority": _authority(),
        "evaluation": {
            "canary_initial": {
                "authority": _authority(),
                "schema_version": "fixture-diagnostics",
            },
            "canary_trained": {
                "authority": _authority(),
                "schema_version": "fixture-diagnostics",
            },
            "holdout_accessed": False,
            "holdout_initial": None,
            "holdout_trained": None,
        },
        "schema_version": "noncombat-state-conditioned-terminal-diagnostics-v1",
        "training": {
            "authority": _authority(),
            "schema_version": "fixture-diagnostics",
        },
    }
    artifacts["diagnostics.json"] = _write_json(
        source / "diagnostics.json", diagnostics
    )
    metrics = {
        "authority": _authority(),
        "blocked_reason": None,
        "completed_training_episodes": 3,
        "cumulative_wall_seconds": 1.0,
        "formal_readiness_unchanged": True,
        "isolation_unchanged": True,
        "optimizer_updates": 3,
        "policy_quality_baseline_established": False,
        "schema_version": "noncombat-state-conditioned-terminal-metrics-v1",
        "target_supported_outcomes_established": False,
        "training_observed_only_floor_shaping": True,
        "training_unsupported_episodes": 0,
        "training_victories": 0,
        "verdict": "experiment_stopped_at_canary",
    }
    artifacts["metrics.json"] = _write_json(source / "metrics.json", metrics)

    initial_row = _decision(
        "seed-200:decision-0",
        selected="card_reward:skip:0",
        take_score=0.0,
        skip_score=1.0,
    )
    trained_row = _decision(
        "seed-200:decision-0",
        selected="card_reward:take:0:0:a",
        take_score=3.0,
        skip_score=0.0,
    )
    evaluation = {
        "canary": {
            "cohort": "canary",
            "floor_difference_ci": {
                "confidence": 0.95,
                "lower": 1.0,
                "mean": 1.0,
                "resamples": 10,
                "seed": 0,
                "upper": 1.0,
            },
            "initial": _policy(initial_row),
            "paired_rows": [],
            "schema_version": "noncombat-state-conditioned-simulator-learning-paired-evaluation-v1",
            "seeds": [200],
            "trained": _policy(trained_row),
            "unsupported_rate": 0.0,
            "unsupported_rate_denominator": 2,
        },
        "canary_gate": {
            "behavior_gate": {
                "blockers": ["card_reward_selected_kind_saturation"],
                "passed": False,
                "schema_version": "noncombat-state-conditioned-behavior-gate-v1",
            },
            "blockers": ["card_reward_selected_kind_saturation"],
            "floor_difference_ci": {
                "confidence": 0.95,
                "lower": 1.0,
                "mean": 1.0,
                "resamples": 10,
                "seed": 0,
                "upper": 1.0,
            },
            "initial_victories": 0,
            "passed": False,
            "trained_victories": 0,
            "unsupported_rate": 0.0,
            "verdict": "experiment_stopped_at_canary",
        },
        "holdout": {"accessed": False, "episode_count": 0},
        "verdict": "experiment_stopped_at_canary",
    }
    artifacts["evaluation.json"] = _write_json(
        source / "evaluation.json", evaluation
    )

    previous_hash = None
    initial_model_sha256 = "a" * 64
    for index, chunk in enumerate(chunks, start=1):
        checkpoint = {
            "checkpoint_index": index,
            "identity": {
                "implementation_commit": "c" * 40,
                "logical_execution_id": "fixture-execution-r1",
                "registration_sha256": "d" * 64,
            },
            "initial_model_sha256": initial_model_sha256,
            "previous_checkpoint_sha256": previous_hash,
            "runtime": {
                "action_generator": {"kind": "fixture"},
                "completed_episodes": index,
                "cumulative_wall_seconds": float(index),
                "entropy_coefficient": 0.01,
                "gradient_norm_ceiling": 1.0,
                "model": _model(float(index)),
                "next_chunk_index": index,
                "optimizer": {"kind": "fixture"},
                "optimizer_updates": index,
                "python_random": {"kind": "fixture"},
            },
            "schema_version": "noncombat-state-conditioned-simulator-learning-checkpoint-v1",
            "training_chunk": chunk,
        }
        name = f"checkpoints/checkpoint_{index:04d}.json"
        payload = _write_json(source / name, checkpoint)
        artifacts[name] = payload
        previous_hash = hashlib.sha256(payload).hexdigest()

    final_model = {
        "architecture": {
            "architecture_id": "state-conditioned-candidate-ranker-mlp-v1",
            "candidate_input_dim": 1,
            "device": "cpu",
            "dtype": "float32",
            "hidden_dim": 1,
            "state_conditioned": True,
            "state_input_dim": 1,
        },
        "authority": _authority(),
        "initial_model_sha256": initial_model_sha256,
        "model": _model(3.0),
        "model_loading_authorized": False,
        "schema_version": "noncombat-state-conditioned-final-model-v1",
    }
    artifacts["final_model.json"] = _write_json(
        source / "final_model.json", final_model
    )
    entries = [
        {
            "path": name,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        }
        for name, payload in sorted(artifacts.items())
    ]
    entries.append(
        {"path": "registration.json", "sha256": "d" * 64, "size_bytes": 0}
    )
    entries.sort(key=lambda row: row["path"])
    _write_json(
        source / "artifact_manifest.json",
        {
            "artifact_count": len(entries),
            "artifacts": entries,
            "authority": _authority(),
            "logical_execution_id": "fixture-execution-r1",
            "manifest_kind": "full_terminal",
            "schema_version": "noncombat-state-conditioned-simulator-learning-manifest-v2",
            "verdict": "experiment_stopped_at_canary",
        },
    )
    return source


def _rebind_manifest_artifact(source: Path, name: str) -> None:
    manifest_path = source / "artifact_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload = (source / name).read_bytes()
    entry = next(row for row in manifest["artifacts"] if row["path"] == name)
    entry.update(sha256=hashlib.sha256(payload).hexdigest(), size_bytes=len(payload))
    _write_json(manifest_path, manifest)


def _rechain_checkpoints(source: Path) -> None:
    previous_hash = None
    for checkpoint_path in sorted((source / "checkpoints").glob("checkpoint_*.json")):
        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        checkpoint["previous_checkpoint_sha256"] = previous_hash
        payload = _write_json(checkpoint_path, checkpoint)
        _rebind_manifest_artifact(
            source, f"checkpoints/{checkpoint_path.name}"
        )
        previous_hash = hashlib.sha256(payload).hexdigest()


def _replace_training_chunks(source: Path, training: dict[str, object]) -> None:
    _write_json(source / "training_rows.json", training)
    _rebind_manifest_artifact(source, "training_rows.json")
    chunks = training["chunks"]
    for index, checkpoint_path in enumerate(
        sorted((source / "checkpoints").glob("checkpoint_*.json"))
    ):
        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        checkpoint["training_chunk"] = chunks[index]
        _write_json(checkpoint_path, checkpoint)
    _rechain_checkpoints(source)


def test_action_family_probability_exposes_candidate_multiplicity() -> None:
    row = _decision(
        "decision-0",
        selected="card_reward:skip:0",
        take_score=0.0,
        skip_score=0.0,
    )

    summary = analyze_decision_rows([row])["card_reward"]

    assert summary["eligible_take_skip_decisions"] == 1
    assert summary["selected_kinds"] == {"skip": {"count": 1, "rate": 1.0}}
    assert summary["greedy_kinds"] == {"take": {"count": 1, "rate": 1.0}}
    assert summary["take_candidate_share"]["mean"] == pytest.approx(0.75)
    assert summary["take_probability_mass"]["mean"] == pytest.approx(0.75)
    assert summary["take_probability_excess_over_candidate_share"]["mean"] == 0.0
    assert summary["candidate_entropy"]["mean"] == pytest.approx(math.log(4.0))
    assert summary["kind_entropy"]["mean"] == pytest.approx(
        -(0.75 * math.log(0.75) + 0.25 * math.log(0.25))
    )
    assert summary["greedy_take_only"] is False


def test_bowl_alternative_is_retained_but_not_take_skip_eligible() -> None:
    row = _decision(
        "decision-bowl",
        selected="card_reward:skip:0",
        take_score=0.0,
        skip_score=1.0,
    )
    row["candidates"][-1] = {
        "action_id": "card_reward:bowl:0",
        "kind": "bowl",
    }
    row["candidate_scores"]["card_reward:bowl:0"] = row["candidate_scores"].pop(
        "card_reward:skip:0"
    )
    row["selected_action_id"] = "card_reward:bowl:0"

    summary = analyze_decision_rows([row])["card_reward"]

    assert summary["decision_count"] == 1
    assert summary["eligible_take_skip_decisions"] == 0
    assert summary["bowl_alternative_decisions"] == 1
    assert summary["selected_kinds"] == {"bowl": {"count": 1, "rate": 1.0}}
    assert summary["selected_take_only"] is False
    assert summary["greedy_take_only"] is False


def test_saturation_boundary_separates_transient_and_persistent() -> None:
    chunks = [
        {"chunk_index": 0, "selected_take_only": False, "greedy_take_only": False},
        {"chunk_index": 1, "selected_take_only": True, "greedy_take_only": True},
        {"chunk_index": 2, "selected_take_only": False, "greedy_take_only": True},
    ]

    boundaries = locate_saturation_boundaries(chunks)

    assert boundaries["selected_take_only"]["first_observed_chunk"] == 1
    assert boundaries["selected_take_only"]["earliest_persistent_chunk"] is None
    assert boundaries["greedy_take_only"]["first_observed_chunk"] == 1
    assert boundaries["greedy_take_only"]["earliest_persistent_chunk"] == 1


def test_bundle_audit_aligns_chunks_and_preserves_initial_tensor_gap(
    tmp_path: Path,
) -> None:
    source = _make_bundle(tmp_path)

    result = audit_bundle(source, command=["fixture-audit"])

    assert result["integrity"]["status"] == "valid"
    assert result["trajectory"]["chunk_count"] == 3
    checkpoints = [row["checkpoint"] for row in result["trajectory"]["chunks"]]
    assert checkpoints[0]["model_delta_l2_from_previous_checkpoint"] is None
    assert checkpoints[0]["initial_tensor_gap"] is True
    assert checkpoints[1]["model_delta_l2_from_previous_checkpoint"] == pytest.approx(
        math.sqrt(5.0)
    )
    assert result["trajectory"]["boundaries"]["greedy_take_only"][
        "earliest_persistent_chunk"
    ] == 1
    assert result["canary"]["initial"]["card_reward"]["greedy_take_only"] is False
    assert result["canary"]["trained"]["card_reward"]["greedy_take_only"] is True
    assert result["conclusion"]["status"] == "mechanism_narrowed_causality_unresolved"
    assert result["authority"]["training"] is False
    assert result["authority"]["successor_experiment"] is False


def test_publish_is_byte_deterministic_and_does_not_modify_sources(tmp_path: Path) -> None:
    source = _make_bundle(tmp_path)
    before = {
        path.relative_to(source).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in source.rglob("*")
        if path.is_file()
    }
    output_json = tmp_path / "out" / "audit.json"
    output_markdown = tmp_path / "out" / "audit.md"

    first = publish_audit(source, output_json, output_markdown)
    first_bytes = (output_json.read_bytes(), output_markdown.read_bytes())
    second = publish_audit(source, output_json, output_markdown)

    assert second == first
    assert (output_json.read_bytes(), output_markdown.read_bytes()) == first_bytes
    after = {
        path.relative_to(source).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in source.rglob("*")
        if path.is_file()
    }
    assert after == before
    assert output_markdown.read_text(encoding="utf-8").startswith(
        "# State-Conditioned Card-Reward Collapse Audit\n"
    )
    markdown = output_markdown.read_text(encoding="utf-8")
    assert "## Chunk Trajectory" in markdown
    assert "Initial tensor gap" in markdown
    assert "## Training Outcomes And Controls" in markdown
    assert "- Outcomes: `" in markdown
    assert "| 0 | 0 | 1 |" in markdown
    assert "| 2 | 0 | 1 |" in markdown
    assert "2.2360679775" in markdown
    assert "## Evidence Gaps" in markdown

    result_with_control = json.loads(json.dumps(first))
    result_with_control["trajectory"]["aggregate"]["controls"]["route"] = {
        "decision_count": 1,
        "selected_kinds": {"map_node": {"count": 1, "rate": 1.0}},
    }
    rendered = render_markdown(result_with_control)
    assert "- `route` decisions: `1`; selected kinds:" in rendered


def test_audit_rejects_any_holdout_access(tmp_path: Path) -> None:
    source = _make_bundle(tmp_path)
    evaluation_path = source / "evaluation.json"
    evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
    evaluation["holdout"] = {"accessed": True, "episode_count": 1, "evaluation": {}}
    _write_json(evaluation_path, evaluation)
    _rebind_manifest_artifact(source, "evaluation.json")

    with pytest.raises(CollapseAuditError, match="holdout"):
        audit_bundle(source, command=["fixture-audit"])


def test_audit_rejects_candidate_score_drift(tmp_path: Path) -> None:
    source = _make_bundle(tmp_path)
    training_path = source / "training_rows.json"
    training = json.loads(training_path.read_text(encoding="utf-8"))
    training["chunks"][0]["diagnostic_rows"][0]["candidate_scores"].pop(
        "card_reward:skip:0"
    )
    _write_json(training_path, training)
    _rebind_manifest_artifact(source, "training_rows.json")

    with pytest.raises(CollapseAuditError, match="candidate_scores"):
        audit_bundle(source, command=["fixture-audit"])


def test_publish_rejects_output_inside_source_bundle(tmp_path: Path) -> None:
    source = _make_bundle(tmp_path)

    with pytest.raises(CollapseAuditError, match="outside the source bundle"):
        publish_audit(source, source / "audit.json", tmp_path / "audit.md")


def test_audit_rejects_unbound_source_byte_drift(tmp_path: Path) -> None:
    source = _make_bundle(tmp_path)
    with (source / "training_rows.json").open("ab") as handle:
        handle.write(b" ")

    with pytest.raises(CollapseAuditError, match="canonical JSON|manifest identity"):
        audit_bundle(source, command=["fixture-audit"])


def test_audit_rejects_checkpoint_chain_drift(tmp_path: Path) -> None:
    source = _make_bundle(tmp_path)
    checkpoint_path = source / "checkpoints" / "checkpoint_0002.json"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    checkpoint["previous_checkpoint_sha256"] = "e" * 64
    _write_json(checkpoint_path, checkpoint)
    _rebind_manifest_artifact(source, "checkpoints/checkpoint_0002.json")

    with pytest.raises(CollapseAuditError, match="chain mismatch"):
        audit_bundle(source, command=["fixture-audit"])


def test_audit_rejects_extra_checkpoint_directory(tmp_path: Path) -> None:
    source = _make_bundle(tmp_path)
    (source / "checkpoints" / "unexpected").mkdir()

    with pytest.raises(CollapseAuditError, match="checkpoint inventory"):
        audit_bundle(source, command=["fixture-audit"])


def test_audit_rejects_canary_category_declaration_drift(tmp_path: Path) -> None:
    source = _make_bundle(tmp_path)
    evaluation_path = source / "evaluation.json"
    evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
    evaluation["canary"]["trained"]["categories"] = []
    _write_json(evaluation_path, evaluation)
    _rebind_manifest_artifact(source, "evaluation.json")

    with pytest.raises(CollapseAuditError, match="categories"):
        audit_bundle(source, command=["fixture-audit"])


def test_audit_ignores_unallowlisted_files(tmp_path: Path) -> None:
    source = _make_bundle(tmp_path)
    (source / "registration.json").write_bytes(b"not-json")
    (source / "holdout_rows.json").write_bytes(b"not-json")

    result = audit_bundle(source, command=["fixture-audit"])

    assert result["integrity"]["status"] == "valid"
    source_names = {
        row["path"] for row in result["integrity"]["source_artifacts"]
    }
    assert "registration.json" not in source_names
    assert "holdout_rows.json" not in source_names


def test_audit_rejects_training_diagnostic_episode_action_mismatch(
    tmp_path: Path,
) -> None:
    source = _make_bundle(tmp_path)
    training_path = source / "training_rows.json"
    training = json.loads(training_path.read_text(encoding="utf-8"))
    episode = training["chunks"][0]["episode_rows"][0]
    episode["selected_action_ids"] = ["card_reward:take:0:0:a"]
    episode["action_sequence_sha256"] = hashlib.sha256(
        _canonical(episode["selected_action_ids"])
    ).hexdigest()
    _replace_training_chunks(source, training)

    with pytest.raises(CollapseAuditError, match="selected actions"):
        audit_bundle(source, command=["fixture-audit"])


def test_audit_rejects_canary_diagnostic_episode_action_mismatch(
    tmp_path: Path,
) -> None:
    source = _make_bundle(tmp_path)
    evaluation_path = source / "evaluation.json"
    evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
    policy = evaluation["canary"]["trained"]
    episode = policy["episode_rows"][0]
    episode["selected_action_ids"] = ["card_reward:skip:0"]
    episode["action_sequence_sha256"] = hashlib.sha256(
        _canonical(episode["selected_action_ids"])
    ).hexdigest()
    policy["replay_episode_rows"] = policy["episode_rows"]
    _write_json(evaluation_path, evaluation)
    _rebind_manifest_artifact(source, "evaluation.json")

    with pytest.raises(CollapseAuditError, match="selected actions"):
        audit_bundle(source, command=["fixture-audit"])


def test_audit_recomputes_canary_blocker_from_consistent_rows(
    tmp_path: Path,
) -> None:
    source = _make_bundle(tmp_path)
    evaluation_path = source / "evaluation.json"
    evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
    policy = evaluation["canary"]["trained"]
    row = policy["diagnostic_rows"][0]
    row["selected_action_id"] = "card_reward:skip:0"
    row["candidate_scores"]["card_reward:skip:0"] = 4.0
    policy["replay_diagnostic_rows"] = policy["diagnostic_rows"]
    episode = policy["episode_rows"][0]
    episode["selected_action_ids"] = ["card_reward:skip:0"]
    episode["action_sequence_sha256"] = hashlib.sha256(
        _canonical(episode["selected_action_ids"])
    ).hexdigest()
    policy["replay_episode_rows"] = policy["episode_rows"]
    _write_json(evaluation_path, evaluation)
    _rebind_manifest_artifact(source, "evaluation.json")

    with pytest.raises(CollapseAuditError, match="blocker does not recompute"):
        audit_bundle(source, command=["fixture-audit"])


def test_audit_rejects_true_source_authority(tmp_path: Path) -> None:
    source = _make_bundle(tmp_path)
    metrics_path = source / "metrics.json"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    metrics["authority"]["training_authorized"] = True
    _write_json(metrics_path, metrics)
    _rebind_manifest_artifact(source, "metrics.json")

    with pytest.raises(CollapseAuditError, match="all-false authority"):
        audit_bundle(source, command=["fixture-audit"])


def test_audit_rejects_mixed_checkpoint_execution_identity(tmp_path: Path) -> None:
    source = _make_bundle(tmp_path)
    checkpoint_path = source / "checkpoints" / "checkpoint_0002.json"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    checkpoint["identity"]["logical_execution_id"] = "different-execution-r1"
    _write_json(checkpoint_path, checkpoint)
    _rebind_manifest_artifact(source, "checkpoints/checkpoint_0002.json")

    with pytest.raises(CollapseAuditError, match="identity"):
        audit_bundle(source, command=["fixture-audit"])


def test_audit_rejects_same_count_tensor_reshape(tmp_path: Path) -> None:
    source = _make_bundle(tmp_path)
    checkpoint_path = source / "checkpoints" / "checkpoint_0002.json"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    checkpoint["runtime"]["model"]["hidden.weight"]["shape"] = [2, 1]
    _write_json(checkpoint_path, checkpoint)
    _rebind_manifest_artifact(source, "checkpoints/checkpoint_0002.json")

    with pytest.raises(CollapseAuditError, match="shape"):
        audit_bundle(source, command=["fixture-audit"])


def test_audit_rejects_boolean_checkpoint_coordinate(tmp_path: Path) -> None:
    source = _make_bundle(tmp_path)
    checkpoint_path = source / "checkpoints" / "checkpoint_0001.json"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    checkpoint["runtime"]["optimizer_updates"] = True
    _write_json(checkpoint_path, checkpoint)
    _rechain_checkpoints(source)

    with pytest.raises(CollapseAuditError, match="optimizer_updates"):
        audit_bundle(source, command=["fixture-audit"])


@pytest.mark.parametrize("episode_count", [False, 0.0, None])
def test_audit_rejects_noninteger_holdout_zero(
    tmp_path: Path, episode_count: object
) -> None:
    source = _make_bundle(tmp_path)
    evaluation_path = source / "evaluation.json"
    evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
    evaluation["holdout"]["episode_count"] = episode_count
    _write_json(evaluation_path, evaluation)
    _rebind_manifest_artifact(source, "evaluation.json")

    with pytest.raises(CollapseAuditError, match="holdout.*episode_count"):
        audit_bundle(source, command=["fixture-audit"])
