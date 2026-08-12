import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch

from analysis_scripts.bottled_policy_oracle import BottledOracleResult
from analysis_scripts.noncombat_card_only_native_baseline_rl_pilot import (
    CORPUS_ARTIFACT_SCHEMA_VERSION,
    DATASET_SCHEMA_VERSION,
    DEMONSTRATION_SCHEMA_VERSION,
    BoundCardCorpus,
    CardWarmStartResult,
    CardOnlyPilotBlocked,
    WARM_START_EPOCHS,
    classify_card_warm_start_gate,
    classify_card_probe,
    collect_and_complete_card_only_residual_chunk,
    complete_card_only_residual_chunk,
    encode_card_only_residual_checkpoint,
    encode_candidate_card_policy,
    label_bound_card_corpus,
    load_bound_card_corpus,
    initialize_card_only_residual_runtime,
    project_bottled_card_labels,
    require_card_warm_start_gate,
    restore_card_only_residual_checkpoint,
    run_fixed_card_warm_start,
)
from analysis_scripts.noncombat_simulator_adapter import (
    ADAPTER_API_VERSION,
    NATIVE_BASELINE_ACTION_SCHEMA_VERSION,
    NATIVE_TARGET_POLICY_ID,
    SOURCE_TYPE,
    STATE_SCHEMA_VERSION,
    canonical_json_bytes,
)


PROVENANCE = {
    "adapter_commit": "a" * 40,
    "adapter_source_sha256": "b" * 64,
    "build": {
        "adapter_api_version": ADAPTER_API_VERSION,
        "compiler": "test",
        "cpp_standard": "20",
        "python": "3.10",
    },
    "module_sha256": "c" * 64,
    "simulator_commit": "d" * 40,
    "simulator_source_sha256": "e" * 64,
    "submodules": {"json": "f" * 40, "pybind11": "1" * 40},
}


def _candidate(action_id, kind, label, raw):
    return {
        "action_id": action_id,
        "available": True,
        "category": "card_reward",
        "kind": kind,
        "label": label,
        "raw": raw,
    }


def _card_row(*, cohort="train", bowl=False, duplicate=False):
    cards = [
        {"id": "ANGER", "name": "Anger", "slot": 0, "upgrade_count": 0, "upgraded": False}
    ]
    if duplicate:
        cards.append(
            {"id": "ANGER", "name": "Anger", "slot": 1, "upgrade_count": 0, "upgraded": False}
        )
    candidates = [
        _candidate(
            f"take-{index}",
            "take",
            card["name"],
            {**card, "misc": 0, "reward_index": 0},
        )
        for index, card in enumerate(cards)
    ]
    candidates.append(
        _candidate(
            "bowl" if bowl else "skip",
            "bowl" if bowl else "skip",
            "gain 2 max hp" if bowl else "skip",
            {"reward_index": 0},
        )
    )
    snapshot = {
        "adapter_api_version": "sts-lightspeed-noncombat-adapter-v2",
        "baseline_control": {"history": [], "policy_id": NATIVE_TARGET_POLICY_ID},
        "category": "card_reward",
        "decision_count": 0,
        "schema_version": STATE_SCHEMA_VERSION,
        "source_type": SOURCE_TYPE,
        "state": {
            "act": 1,
            "decision_context": {"cards": cards, "has_singing_bowl": bowl, "reward_index": 0},
            "deck": [
                {"id": "STRIKE_RED", "name": "Strike", "slot": 0, "upgrade_count": 0, "upgraded": False}
            ],
            "floor": 2,
        },
        "terminal": False,
    }
    return {
        "candidate_actions": candidates,
        "candidate_actions_sha256": hashlib.sha256(canonical_json_bytes(candidates)).hexdigest(),
        "category": "card_reward",
        "cohort": cohort,
        "decision_index": 0,
        "policy_views": [],
        "provenance": copy.deepcopy(PROVENANCE),
        "schema_version": DEMONSTRATION_SCHEMA_VERSION,
        "seed": 1000,
        "source_snapshot": snapshot,
        "source_snapshot_sha256": hashlib.sha256(canonical_json_bytes(snapshot)).hexdigest(),
        "source_type": SOURCE_TYPE,
        "successor": {"state": {}, "terminal": True},
        "teacher": {
            "action_id": "take-0",
            "category": "card_reward",
            "policy_id": NATIVE_TARGET_POLICY_ID,
            "schema_version": NATIVE_BASELINE_ACTION_SCHEMA_VERSION,
        },
    }


def _write_corpus(path: Path, *, final_test=None, duplicate=False):
    datasets = {}
    for cohort in ("train", "validation"):
        row = _card_row(cohort=cohort, duplicate=duplicate)
        datasets[cohort] = {
            "all_categories": ["card_reward"],
            "cohort": cohort,
            "episodes": [],
            "row_count": 1,
            "rows": [row],
            "schema_version": DATASET_SCHEMA_VERSION,
            "seeds": [1000],
            "source_type": SOURCE_TYPE,
            "teacher_policy_id": NATIVE_TARGET_POLICY_ID,
        }
    datasets["final_test"] = final_test
    value = {
        "datasets": datasets,
        "registration_sha256": "2" * 64,
        "schema_version": CORPUS_ARTIFACT_SCHEMA_VERSION,
    }
    path.write_bytes(canonical_json_bytes(value))
    return hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_size


def _load_fixture(path, *, final_test=None, duplicate=False):
    sha256, size = _write_corpus(path, final_test=final_test, duplicate=duplicate)
    return load_bound_card_corpus(
        path,
        expected_sha256=sha256,
        expected_size_bytes=size,
        expected_registration_sha256="2" * 64,
        expected_card_row_counts={"train": 1, "validation": 1},
    )


class FakeOracle:
    def __init__(self, labels, *, dirty=False, commit="abc123"):
        self.labels = iter(labels)
        self.source = {
            "commit": commit,
            "dirty": dirty,
            "mode": "native_bottled",
            "path": "C:/bottled_ai",
            "strategy": "REQUESTED_STRIKE",
        }

    def source_metadata(self):
        return dict(self.source)

    def evaluate(self, sample):
        assert sample.category == "card_reward"
        assert sample.evidence_quality == "complete"
        assert sample.context["offered"]
        return BottledOracleResult(
            label=next(self.labels),
            confidence="high",
            reason="fixture",
            source=dict(self.source),
        )


def test_bound_reader_extracts_only_train_and_validation_card_rows(tmp_path):
    corpus = _load_fixture(tmp_path / "demonstrations.json")

    assert set(corpus.rows) == {"train", "validation"}
    assert [row["cohort"] for row in corpus.rows["train"]] == ["train"]
    assert corpus.source["sha256"]


@pytest.mark.parametrize("drift", ["size", "sha256"])
def test_bound_reader_rejects_corpus_drift(tmp_path, drift):
    path = tmp_path / "demonstrations.json"
    sha256, size = _write_corpus(path)

    with pytest.raises(CardOnlyPilotBlocked, match=drift):
        load_bound_card_corpus(
            path,
            expected_sha256="0" * 64 if drift == "sha256" else sha256,
            expected_size_bytes=size + 1 if drift == "size" else size,
            expected_registration_sha256="2" * 64,
            expected_card_row_counts={"train": 1, "validation": 1},
        )


def test_bound_reader_denies_final_test_request_before_reading(tmp_path):
    path = tmp_path / "missing.json"

    with pytest.raises(CardOnlyPilotBlocked, match="final_test"):
        load_bound_card_corpus(path, cohorts=("train", "final_test"))


def test_bound_reader_rejects_populated_final_test(tmp_path):
    path = tmp_path / "demonstrations.json"
    sha256, size = _write_corpus(path, final_test={"rows": ["protected"]})

    with pytest.raises(CardOnlyPilotBlocked, match="must remain absent"):
        load_bound_card_corpus(
            path,
            expected_sha256=sha256,
            expected_size_bytes=size,
            expected_registration_sha256="2" * 64,
            expected_card_row_counts={"train": 1, "validation": 1},
        )


@pytest.mark.parametrize(
    ("labels", "expected"),
    [
        (("Anger", "skip"), {"skip": 1, "take": 1}),
    ],
)
def test_bottled_bridge_maps_take_and_skip_and_reports_disagreement(
    tmp_path, labels, expected
):
    corpus = _load_fixture(tmp_path / "demonstrations.json")

    result = label_bound_card_corpus(
        corpus, FakeOracle(labels), expected_bottled_commit="abc123"
    )

    assert result["counts"]["label_family"] == expected
    assert result["counts"]["simple_agent_agreement"] == {"agree": 1, "disagree": 1}
    assert result["rows"]["train"][0]["bottled_action_id"] == "take-0"
    assert result["rows"]["validation"][0]["bottled_action_id"] == "skip"


def test_bottled_bridge_maps_bowl(tmp_path):
    path = tmp_path / "demonstrations.json"
    sha256, size = _write_corpus(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    for cohort in ("train", "validation"):
        row = _card_row(cohort=cohort, bowl=True)
        value["datasets"][cohort]["rows"] = [row]
    path.write_bytes(canonical_json_bytes(value))
    corpus = load_bound_card_corpus(
        path,
        expected_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        expected_size_bytes=path.stat().st_size,
        expected_registration_sha256="2" * 64,
        expected_card_row_counts={"train": 1, "validation": 1},
    )

    result = label_bound_card_corpus(
        corpus, FakeOracle(("bowl", "bowl")), expected_bottled_commit="abc123"
    )

    assert result["counts"]["label_family"] == {"bowl": 2}


def test_bottled_bridge_rejects_missing_context(tmp_path):
    corpus = _load_fixture(tmp_path / "demonstrations.json")
    bad_row = copy.deepcopy(corpus.rows["train"][0])
    del bad_row["source_snapshot"]["state"]["decision_context"]
    bad_row["source_snapshot_sha256"] = hashlib.sha256(
        canonical_json_bytes(bad_row["source_snapshot"])
    ).hexdigest()
    bad = BoundCardCorpus(corpus.source, {"train": (bad_row,)})

    with pytest.raises(CardOnlyPilotBlocked, match="decision_context"):
        label_bound_card_corpus(
            bad, FakeOracle(("skip",)), expected_bottled_commit="abc123"
        )


def test_bottled_bridge_rejects_ambiguous_card_label(tmp_path):
    corpus = _load_fixture(tmp_path / "demonstrations.json", duplicate=True)

    with pytest.raises(CardOnlyPilotBlocked, match="maps to 2"):
        label_bound_card_corpus(
            corpus, FakeOracle(("Anger", "Anger")), expected_bottled_commit="abc123"
        )


def test_bottled_bridge_requires_clean_bound_checkout(tmp_path):
    corpus = _load_fixture(tmp_path / "demonstrations.json")

    with pytest.raises(CardOnlyPilotBlocked, match="clean"):
        label_bound_card_corpus(
            corpus, FakeOracle((), dirty=True), expected_bottled_commit="abc123"
        )
    with pytest.raises(CardOnlyPilotBlocked, match="commit mismatch"):
        label_bound_card_corpus(
            corpus, FakeOracle((), commit="different"), expected_bottled_commit="abc123"
        )


def _labeled_fixture(tmp_path, *, validation_label="skip"):
    corpus = _load_fixture(tmp_path / f"labels-{validation_label}.json")
    return label_bound_card_corpus(
        corpus,
        FakeOracle(("Anger", validation_label)),
        expected_bottled_commit="abc123",
    )


def test_labeled_rows_project_through_current_card_feature_bridge(tmp_path):
    labels = _labeled_fixture(tmp_path)

    train = project_bottled_card_labels(labels, cohort="train")
    validation = project_bottled_card_labels(labels, cohort="validation")

    assert len(train) == len(validation) == 1
    assert train[0].target_action_id == "take-0"
    assert train[0].target_family == "take"
    assert validation[0].target_action_id == "skip"
    assert train[0].state_features.shape == (1024,)
    assert train[0].candidate_features.shape == (2, 1024)
    assert train[0].source_adapter_api_version == "sts-lightspeed-noncombat-adapter-v2"
    assert train[0].projection_adapter_api_version == ADAPTER_API_VERSION
    assert train[0].snapshot["adapter_api_version"].endswith("v2")
    assert not hasattr(train[0], "reward")
    assert not hasattr(train[0], "successor")


def test_labeled_row_projection_rejects_ambiguous_target(tmp_path):
    labels = _labeled_fixture(tmp_path)
    labels["rows"]["train"][0]["bottled_action_id"] = "missing"

    with pytest.raises(CardOnlyPilotBlocked, match="exactly one"):
        project_bottled_card_labels(labels, cohort="train")


def test_labeled_row_projection_rejects_decision_count_drift(tmp_path):
    labels = _labeled_fixture(tmp_path)
    row = labels["rows"]["train"][0]
    row["source_snapshot"]["decision_count"] = 9
    row["source_snapshot_sha256"] = hashlib.sha256(
        canonical_json_bytes(row["source_snapshot"])
    ).hexdigest()

    with pytest.raises(CardOnlyPilotBlocked, match="decision_count"):
        project_bottled_card_labels(labels, cohort="train")


def test_batched_warm_start_loss_matches_scalar_policy_loss_and_gradients(tmp_path):
    from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot as pilot
    from analysis_scripts import (
        noncombat_card_acceptance_empirical_successor_runtime as runtime,
    )

    row = project_bottled_card_labels(_labeled_fixture(tmp_path), cohort="train")[0]
    batched_bootstrap = runtime.build_matched_bootstrap()
    scalar_bootstrap = runtime.build_matched_bootstrap()
    batched_policy = batched_bootstrap.candidate.card_policy
    scalar_policy = scalar_bootstrap.candidate.card_policy

    batched_family, batched_conditional = pilot._warm_start_losses(
        batched_policy, (row,)
    )
    (batched_family + batched_conditional).backward()
    output = scalar_policy(
        row.state_features,
        row.candidate_features,
        row.candidates,
        category="card_reward",
    )
    family_index = output.family_batch.family_order.index(row.target_family)
    scalar_family = torch.nn.functional.cross_entropy(
        output.family_logits.unsqueeze(0), torch.tensor([family_index])
    )
    action_ids = output.family_batch.action_ids
    target_index = action_ids.index(row.target_action_id)
    family_indices = output.family_batch.family_candidate_indices[family_index]
    scalar_conditional = torch.nn.functional.cross_entropy(
        output.conditional_logits[
            torch.tensor(family_indices, dtype=torch.long)
        ].unsqueeze(0),
        torch.tensor([family_indices.index(target_index)]),
    )
    (scalar_family + scalar_conditional).backward()

    assert torch.equal(batched_family, scalar_family)
    assert torch.equal(batched_conditional, scalar_conditional)
    for (batched_name, batched_parameter), (scalar_name, scalar_parameter) in zip(
        batched_policy.named_parameters(),
        scalar_policy.named_parameters(),
        strict=True,
    ):
        assert batched_name == scalar_name
        assert torch.equal(batched_parameter.grad, scalar_parameter.grad)


def test_fixed_card_warm_start_is_deterministic_and_validation_does_not_train(
    tmp_path,
):
    from analysis_scripts import (
        noncombat_card_acceptance_empirical_successor_runtime as runtime,
    )

    labels = _labeled_fixture(tmp_path, validation_label="skip")
    alternate_validation = _labeled_fixture(
        tmp_path, validation_label="Anger"
    )
    first = run_fixed_card_warm_start(runtime.build_matched_bootstrap(), labels)
    replay = run_fixed_card_warm_start(runtime.build_matched_bootstrap(), labels)
    changed_validation = run_fixed_card_warm_start(
        runtime.build_matched_bootstrap(), alternate_validation
    )

    assert WARM_START_EPOCHS == 128
    assert first.zero_model == replay.zero_model
    assert first.final_model == replay.final_model
    assert first.history == replay.history
    assert first.final_model == changed_validation.final_model
    assert first.zero_model != first.final_model
    assert len(first.history) == WARM_START_EPOCHS
    assert first.optimizer_steps == WARM_START_EPOCHS
    assert first.configuration["batch_size"] == 32
    assert first.configuration["learning_rate"] == 0.001
    assert encode_candidate_card_policy(first.bootstrap) == first.final_model
    assert first.zero_validation != changed_validation.zero_validation


def test_warm_start_gate_classification_and_failed_gate_block_residual_access(
    tmp_path,
):
    from analysis_scripts import (
        noncombat_card_acceptance_empirical_successor_runtime as runtime,
    )

    passed = classify_card_warm_start_gate(
        {
            "action_agreement": 0.40,
            "family_agreement": 0.55,
            "non_take_rate": 0.50,
            "row_count": 100,
            "take_rate": 0.50,
        },
        {
            "action_agreement": 0.65,
            "family_agreement": 0.75,
            "non_take_rate": 0.45,
            "row_count": 100,
            "take_rate": 0.55,
        },
    )
    assert passed["verdict"] == "card_warm_start_gate_passed"
    assert set(passed["checks"].values()) == {True}

    failed = run_fixed_card_warm_start(
        runtime.build_matched_bootstrap(), _labeled_fixture(tmp_path)
    )
    assert failed.gate["verdict"] == "card_warm_start_gate_failed"
    with pytest.raises(CardOnlyPilotBlocked, match="residual RL is not authorized"):
        require_card_warm_start_gate(failed)


def _passed_warm_start(runtime):
    bootstrap = runtime.build_matched_bootstrap()
    model = encode_candidate_card_policy(bootstrap)
    metrics = {
        "action_agreement": 0.75,
        "family_agreement": 0.80,
        "non_take_rate": 0.45,
        "predictions": [],
        "row_count": 100,
        "take_rate": 0.55,
    }
    return CardWarmStartResult(
        bootstrap=bootstrap,
        configuration={"fixture": True},
        zero_model=model,
        final_model=model,
        zero_validation={**metrics, "family_agreement": 0.60},
        final_validation=metrics,
        gate={"passed": True, "verdict": "card_warm_start_gate_passed"},
        history=(),
        optimizer_steps=0,
    )


def _residual_runtime(tmp_path):
    from analysis_scripts import (
        noncombat_card_acceptance_empirical_successor_runtime as runtime,
    )

    labels = _labeled_fixture(tmp_path)
    return initialize_card_only_residual_runtime(
        _passed_warm_start(runtime), labels
    )


def test_zero_step_residual_checkpoint_round_trips_without_control_optimizer(tmp_path):
    runtime = _residual_runtime(tmp_path)

    checkpoint = encode_card_only_residual_checkpoint(runtime)
    restored = restore_card_only_residual_checkpoint(
        checkpoint, probe_rows=runtime.probe_rows
    )
    parsed = json.loads(checkpoint)

    assert encode_card_only_residual_checkpoint(restored) == checkpoint
    assert "candidate_optimizer" in parsed
    assert "control_optimizer" not in parsed
    assert parsed["coordinates"] == {
        "candidate_optimizer_steps": 0,
        "completed_decisions": 0,
        "completed_pairs": 0,
        "environment_accesses": 0,
        "next_chunk_index": 0,
    }


def test_residual_checkpoint_rejects_partial_or_probe_drift(tmp_path):
    runtime = _residual_runtime(tmp_path)
    parsed = json.loads(encode_card_only_residual_checkpoint(runtime))
    parsed["partial"] = True
    partial = json.dumps(
        parsed, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ).encode("ascii")

    with pytest.raises(CardOnlyPilotBlocked, match="fields differ"):
        restore_card_only_residual_checkpoint(
            partial, probe_rows=runtime.probe_rows
        )
    with pytest.raises(CardOnlyPilotBlocked, match="probe"):
        restore_card_only_residual_checkpoint(
            encode_card_only_residual_checkpoint(runtime),
            probe_rows=(),
        )


def test_residual_collection_deadline_and_failure_preserve_complete_checkpoint(
    tmp_path, monkeypatch
):
    from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot as pilot

    runtime = _residual_runtime(tmp_path)
    before = encode_card_only_residual_checkpoint(runtime)
    environment_calls = []

    with pytest.raises(CardOnlyPilotBlocked, match="deadline"):
        collect_and_complete_card_only_residual_chunk(
            runtime,
            environment_factory=lambda seed: environment_calls.append(seed),
            seeds=tuple(range(64)),
            chunk_index=0,
            deadline=0.0,
            clock=lambda: 1.0,
        )
    assert environment_calls == []
    assert encode_card_only_residual_checkpoint(runtime) == before

    monkeypatch.setattr(
        pilot.successor_runtime,
        "rollout_paired_card_only_native_baseline_training_episode",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            pilot.successor_runtime.SuccessorRuntimeError("fixture failure")
        ),
    )
    with pytest.raises(CardOnlyPilotBlocked, match="fixture failure"):
        collect_and_complete_card_only_residual_chunk(
            runtime,
            environment_factory=lambda seed: object(),
            seeds=tuple(range(64)),
            chunk_index=0,
            deadline=10.0,
            clock=lambda: 0.0,
        )
    assert encode_card_only_residual_checkpoint(runtime) == before


def _fake_residual_pairs(*, unsupported=False):
    pairs = []
    for seed in range(64):
        candidate_decision = SimpleNamespace(
            card_terms=object(), category="card_reward"
        )
        control_decision = SimpleNamespace(card_terms=None, category="card_reward")
        candidate = SimpleNamespace(
            decisions=(candidate_decision,),
            final_snapshot={"terminal": True},
            rewards=(0.0,),
            seed=seed,
            unsupported_reason=("fixture unsupported" if unsupported and seed == 0 else None),
        )
        control = SimpleNamespace(
            decisions=(control_decision,),
            final_snapshot={"terminal": True},
            rewards=(0.0,),
            seed=seed,
            unsupported_reason=None,
        )
        pairs.append(SimpleNamespace(seed=seed, candidate=candidate, control=control))
    return tuple(pairs)


def test_residual_concentration_stop_is_checkpointed_before_more_access(
    tmp_path, monkeypatch
):
    from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot as pilot

    runtime = _residual_runtime(tmp_path)

    def fake_update(bootstrap, optimizer, _episodes):
        for parameter in optimizer.param_groups[0]["params"]:
            parameter.grad = torch.full_like(parameter, 1e-6)
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
        return {"fixture": True}

    monkeypatch.setattr(
        pilot.successor_runtime,
        "apply_candidate_cross_fitted_chunk_update_exploratory",
        fake_update,
    )
    monkeypatch.setattr(
        pilot,
        "evaluate_card_warm_start",
        lambda *_args, **_kwargs: {
            "action_agreement": 0.0,
            "family_agreement": 0.0,
            "non_take_rate": 0.0,
            "predictions": [],
            "row_count": 1,
            "take_rate": 1.0,
        },
    )

    completed = complete_card_only_residual_chunk(
        runtime, _fake_residual_pairs(), chunk_index=0
    )

    assert classify_card_probe({"take_rate": 1.0, "non_take_rate": 0.0})[
        "stop"
    ] is True
    assert completed.probe["stop"] is True
    assert completed.runtime.stopped_for_concentration is True
    assert restore_card_only_residual_checkpoint(
        completed.checkpoint, probe_rows=runtime.probe_rows
    ).stopped_for_concentration is True
    with pytest.raises(CardOnlyPilotBlocked, match="cannot start"):
        complete_card_only_residual_chunk(
            completed.runtime, _fake_residual_pairs(), chunk_index=1
        )


def test_residual_unsupported_pair_blocks_before_optimizer_step(tmp_path):
    runtime = _residual_runtime(tmp_path)
    before = encode_card_only_residual_checkpoint(runtime)

    with pytest.raises(CardOnlyPilotBlocked, match="unsupported"):
        complete_card_only_residual_chunk(
            runtime, _fake_residual_pairs(unsupported=True), chunk_index=0
        )

    assert encode_card_only_residual_checkpoint(runtime) == before


def test_residual_probe_failure_preserves_complete_checkpoint(tmp_path, monkeypatch):
    from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot as pilot

    runtime = _residual_runtime(tmp_path)
    before = encode_card_only_residual_checkpoint(runtime)

    def fake_update(bootstrap, optimizer, _episodes):
        for parameter in optimizer.param_groups[0]["params"]:
            parameter.grad = torch.full_like(parameter, 1e-6)
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
        return {"fixture": True}

    monkeypatch.setattr(
        pilot.successor_runtime,
        "apply_candidate_cross_fitted_chunk_update_exploratory",
        fake_update,
    )
    monkeypatch.setattr(
        pilot,
        "evaluate_card_warm_start",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            CardOnlyPilotBlocked("fixture probe failure")
        ),
    )

    with pytest.raises(CardOnlyPilotBlocked, match="fixture probe failure"):
        complete_card_only_residual_chunk(
            runtime, _fake_residual_pairs(), chunk_index=0
        )

    assert encode_card_only_residual_checkpoint(runtime) == before
