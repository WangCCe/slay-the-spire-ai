from __future__ import annotations

import copy
import gzip
import hashlib
import importlib
import io
import json
import math
import struct
from pathlib import Path

import pytest


CONTROL_MODULE = (
    "analysis_scripts.noncombat_card_acceptance_empirical_successor_experiment"
)
VERIFIER_MODULE = (
    "analysis_scripts.verify_noncombat_card_acceptance_empirical_successor"
)
RUNTIME_MODULE = (
    "analysis_scripts.noncombat_card_acceptance_empirical_successor_runtime"
)


def _control():
    return importlib.import_module(CONTROL_MODULE)


def _verifier():
    return importlib.import_module(VERIFIER_MODULE)


def _runtime():
    return importlib.import_module(RUNTIME_MODULE)


def _training_context(control):
    registration = {
        "registration_id": "card-acceptance-verifier-fixture-v1",
        "registration_sha256": "c" * 64,
    }
    request = control.build_stage_request(
        stage="training",
        request_id="card-acceptance-verifier-training-request-v1",
        source_commit="a" * 40,
        source_inventory_sha256="b" * 64,
        configuration_identity=control.experiment_configuration_identity(),
        prerequisite_bindings={
            "registration_sha256": registration["registration_sha256"]
        },
        output_root="D:/synthetic/card-acceptance-verifier/training",
    )
    authorization = control.build_stage_authorization(
        request=request,
        authorization_id="card-acceptance-verifier-training-authorization-v1",
        request_review_sha256="1" * 64,
        approval_record_sha256="2" * 64,
    )
    return control._build_validated_execution_context(
        registration=registration,
        request=request,
        authorization=authorization,
        registration_validator=lambda value: copy.deepcopy(dict(value)),
    )


def _publish_terminal_fixture(tmp_path: Path):
    control = _control()
    context = _training_context(control)
    output = tmp_path / "execution"
    clock_values = iter((100.0, 101.25))
    with control.ExecutionLease(
        output,
        context=context,
        child_process_id=71_001,
        process_alive=lambda process_id: process_id == 71_001,
        clock=lambda: next(clock_values),
    ) as lease:
        control.initialize_access_journal(context, lease)
        control.initialize_resource_ledger(context, lease)
        control.perform_journaled_environment_access(
            context,
            lease,
            seed=90_001,
            arm="candidate",
            purpose="training",
            access=lambda: None,
        )
        control.publish_managed_artifact(
            context,
            lease,
            relative_path="evidence/summary.json",
            payload=control.canonical_json_bytes({"fixture": "terminal"}),
        )
        intent = control.publish_terminal_intent(
            context,
            lease,
            verdict="training_failed",
            details={"reason": "synthetic-verifier-fixture"},
        )
        terminal = control.publish_terminal_document(
            context,
            lease,
            terminal_intent=intent,
        )
        manifest = control.publish_artifact_manifest(
            context,
            lease,
            terminal_document=terminal,
        )
    return output, intent["identity"], manifest


def test_independent_verifier_reconstructs_terminal_lifecycle_bundle(tmp_path):
    verifier = _verifier()
    output, identity, manifest = _publish_terminal_fixture(tmp_path)

    result = verifier.verify_terminal_bundle(
        output,
        expected_identity=identity,
        expected_child_process_id=71_001,
        owner_alive=lambda _process_id: False,
    )

    assert result["verified"] is True
    assert result["identity"] == identity
    assert result["verdict"] == "training_failed"
    assert result["debited_accesses"] == 1
    assert result["resources"]["environment_accesses"] == 1
    assert result["manifest_sha256"] == manifest["manifest_sha256"]
    assert result["authority"] == verifier.verifier_contract()["authority"]


def test_independent_verifier_rejects_manifested_artifact_drift(tmp_path):
    verifier = _verifier()
    output, identity, _manifest = _publish_terminal_fixture(tmp_path)
    artifact = output / "evidence" / "summary.json"
    original = artifact.read_bytes()
    artifact.write_bytes(original.replace(b"terminal", b"drifted!"))

    with pytest.raises(verifier.VerificationError, match="artifact|inventory|manifest"):
        verifier.verify_terminal_bundle(
            output,
            expected_identity=identity,
            expected_child_process_id=71_001,
            owner_alive=lambda _process_id: False,
        )


def test_independent_verifier_rejects_live_or_wrong_lease_owner(tmp_path):
    verifier = _verifier()
    output, identity, _manifest = _publish_terminal_fixture(tmp_path)

    with pytest.raises(verifier.VerificationError, match="lease|owner|alive"):
        verifier.verify_terminal_bundle(
            output,
            expected_identity=identity,
            expected_child_process_id=71_001,
            owner_alive=lambda process_id: process_id == 71_001,
        )

    lease_path = output / ".execution.lease"
    lease = _control()._parse_canonical_mapping(
        lease_path.read_bytes(),
        "lease fixture",
    )
    lease["owner"]["child_process_id"] = 71_002
    lease_path.write_bytes(_control().canonical_json_bytes(lease))
    with pytest.raises(verifier.VerificationError, match="lease|owner|identity"):
        verifier.verify_terminal_bundle(
            output,
            expected_identity=identity,
            expected_child_process_id=71_001,
            owner_alive=lambda _process_id: False,
        )


@pytest.mark.parametrize(
    "failure_kind",
    (
        "truncation",
        "unknown_field",
        "wrong_order",
        "wrong_digest",
        "wrong_stage",
        "byte_ceiling",
        "elapsed_charge",
        "publication_order",
    ),
)
def test_independent_lifecycle_verifier_fail_closed_matrix(
    tmp_path,
    monkeypatch,
    failure_kind,
):
    verifier = _verifier()
    control = _control()
    output, identity, _manifest = _publish_terminal_fixture(tmp_path)
    expected_identity = copy.deepcopy(identity)
    if failure_kind == "truncation":
        journal = output / "access_journal.jsonl"
        journal.write_bytes(journal.read_bytes()[:-1])
    elif failure_kind == "unknown_field":
        terminal_path = output / "terminal.json"
        terminal = json.loads(terminal_path.read_bytes())
        terminal["unknown_field"] = True
        terminal_path.write_bytes(control.canonical_json_bytes(terminal))
    elif failure_kind == "wrong_order":
        ledger_path = output / "resource_ledger.jsonl"
        events = ledger_path.read_bytes().splitlines(keepends=True)
        assert len(events) >= 2
        events[0], events[-1] = events[-1], events[0]
        ledger_path.write_bytes(b"".join(events))
    elif failure_kind == "wrong_digest":
        manifest_path = output / "artifact_manifest.json"
        manifest = json.loads(manifest_path.read_bytes())
        manifest["manifest_sha256"] = "0" * 64
        manifest_path.write_bytes(control.canonical_json_bytes(manifest))
    elif failure_kind == "wrong_stage":
        expected_identity["stage"] = "holdout"
    elif failure_kind == "byte_ceiling":
        monkeypatch.setattr(verifier, "_MAX_ARTIFACT_BYTES", 8)
    elif failure_kind == "elapsed_charge":
        ledger_path = output / "resource_ledger.jsonl"
        events = [json.loads(line) for line in ledger_path.read_bytes().splitlines()]
        assert len(events) >= 2
        events[-1]["resources"]["charged_seconds"] = -1.0
        ledger_path.write_bytes(
            b"".join(control.canonical_json_bytes(event) for event in events)
        )
    elif failure_kind == "publication_order":
        (output / "artifact_manifest.json").unlink()
    else:
        raise AssertionError(failure_kind)

    with pytest.raises(verifier.VerificationError):
        verifier.verify_terminal_bundle(
            output,
            expected_identity=expected_identity,
            expected_child_process_id=71_001,
            owner_alive=lambda _process_id: False,
        )


def test_independent_verifier_reconstructs_matched_bootstrap_without_torch():
    runtime = _runtime()
    verifier = _verifier()
    encoded = runtime.encode_paired_bootstrap(runtime.build_matched_bootstrap())

    result = verifier.verify_paired_bootstrap_bytes(encoded)

    assert result == {
        "architecture": {
            "hidden_dim": 64,
            "input_dim": 1_024,
            "model_seed": 0,
        },
        "generator_pairs_exact": True,
        "model_copy_count": 5,
        "model_state_sha256": result["model_state_sha256"],
        "verified": True,
    }
    assert len(result["model_state_sha256"]) == 64


def test_independent_bootstrap_verifier_rejects_mapping_or_state_drift():
    runtime = _runtime()
    verifier = _verifier()
    encoded = runtime.encode_paired_bootstrap(runtime.build_matched_bootstrap())
    parsed = json.loads(encoded)
    parsed["models"]["control"]["shared_card_ranker"]["scorer.bias"][
        "values"
    ][0] += 1.0
    drifted = runtime._canonical_json_bytes(parsed)

    with pytest.raises(verifier.VerificationError, match="model|state|mapping"):
        verifier.verify_paired_bootstrap_bytes(drifted)


@pytest.fixture(scope="module")
def one_chunk_checkpoint_bytes():
    runtime = _runtime()
    training = runtime.initialize_paired_training_runtime()
    initial_bootstrap = runtime.encode_paired_bootstrap(training.bootstrap)
    for optimizer in (
        training.optimizers.candidate,
        training.optimizers.control,
    ):
        optimizer.zero_grad(set_to_none=True)
        for parameter in optimizer.param_groups[0]["params"]:
            parameter.grad = runtime.torch.zeros_like(parameter)
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
    training.next_chunk_index = 1
    training.completed_pairs = 64
    training.completed_decisions = 128
    training.training_environment_accesses = 128
    training.candidate_optimizer_updates = 1
    training.control_optimizer_updates = 1
    training.training_optimizer_steps = 2
    training.completed_chunk_summaries = [
        {
            "candidate_card_decisions": [
                {
                    "multi_family": False,
                    "unique_greedy_family_id": "take",
                }
            ],
            "chunk_index": 0,
        }
    ]
    checkpoint = runtime.encode_paired_training_checkpoint(training)
    return initial_bootstrap, checkpoint


def test_independent_verifier_reconstructs_training_checkpoint_and_frozen_bytes(
    one_chunk_checkpoint_bytes,
):
    verifier = _verifier()
    initial_bootstrap, checkpoint = one_chunk_checkpoint_bytes

    result = verifier.verify_paired_training_checkpoint_bytes(
        checkpoint,
        initial_bootstrap_bytes=initial_bootstrap,
    )

    assert result == {
        "candidate_optimizer_updates": 1,
        "completed_pairs": 64,
        "control_optimizer_updates": 1,
        "frozen_noncard_verified": True,
        "next_chunk_index": 1,
        "stopped_for_family_saturation": False,
        "verified": True,
    }


def test_independent_checkpoint_verifier_rejects_frozen_state_drift(
    one_chunk_checkpoint_bytes,
):
    verifier = _verifier()
    initial_bootstrap, checkpoint = one_chunk_checkpoint_bytes
    drifted = json.loads(checkpoint)
    drifted["bootstrap"]["models"]["candidate"]["frozen_noncard_ranker"][
        "scorer.bias"
    ]["values"][0] += 1.0

    with pytest.raises(verifier.VerificationError, match="frozen|non-card|bytes"):
        verifier.verify_paired_training_checkpoint_bytes(
            _runtime_bytes(drifted),
            initial_bootstrap_bytes=initial_bootstrap,
        )


def _runtime_bytes(value):
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


def _gzip_bytes(value):
    buffer = io.BytesIO()
    with gzip.GzipFile(
        fileobj=buffer,
        mode="wb",
        filename="",
        mtime=0,
    ) as handle:
        handle.write(value)
    return buffer.getvalue()


def _tensor(values, shape):
    return {"dtype": "float64", "shape": list(shape), "values": list(values)}


def _canary_output(arm, seed, family):
    family_order = ["bowl", "skip"]
    family_probabilities = [0.6, 0.4] if family == "bowl" else [0.4, 0.6]
    family_index = family_order.index(family)
    action_ids = [f"bowl-{seed}", f"skip-{seed}"]
    selected_action_id = action_ids[family_index]
    card_terms = {
        "action_ids": action_ids,
        "candidate_families": family_order,
        "conditional_log_probabilities": _tensor([0.0, 0.0], [2]),
        "conditional_probabilities": _tensor([1.0, 1.0], [2]),
        "family_entropy": _tensor(
            [-sum(value * math.log(value) for value in family_probabilities)],
            [],
        ),
        "family_log_probabilities": _tensor(
            [math.log(value) for value in family_probabilities],
            [2],
        ),
        "family_order": family_order,
        "family_probabilities": _tensor(family_probabilities, [2]),
        "selected_action_id": selected_action_id,
        "selected_conditional_log_probability": _tensor([0.0], []),
        "selected_family": family,
        "selected_family_log_probability": _tensor(
            [math.log(family_probabilities[family_index])],
            [],
        ),
        "two_stage_greedy_action_ids": [selected_action_id],
        "unique_greedy_family_id": family,
        "unique_two_stage_greedy_action_id": selected_action_id,
    }
    decisions = []
    if arm == "candidate":
        decisions.append(
            {
                "candidate_features": _tensor([0.0, 0.0], [2, 1]),
                "candidates": [
                    {"action_id": action_ids[0], "family": "bowl"},
                    {"action_id": action_ids[1], "family": "skip"},
                ],
                "card_terms": card_terms,
                "category": "card_reward",
                "decision_id": f"candidate:seed-{seed}:decision-0",
                "decision_index": 0,
                "diagnostic": {},
                "selected_action_id": selected_action_id,
                "state_features": _tensor([0.0], [1]),
            }
        )
    else:
        decisions.append(
            {
                "candidate_features": None,
                "candidates": [],
                "card_terms": None,
                "category": "event",
                "decision_id": f"control:seed-{seed}:decision-0",
                "decision_index": 0,
                "diagnostic": {},
                "selected_action_id": "leave",
                "state_features": _tensor([0.0], [1]),
            }
        )
    return {
        "arm": arm,
        "decisions": decisions,
        "seed": seed,
        "terminal": {
            "final_snapshot": {
                "state": {"outcome": "player_loss"},
                "terminal": True,
            },
            "floor_progress": 0.0,
            "rewards": [0.0],
            "terminal_victory": 0,
            "trajectory_id": f"{arm}:seed-{seed}",
            "transitions": [],
            "unsupported_reason": None,
        },
    }


def _canary_evidence(root):
    bindings = {
        arm: {
            "checkpoint_sha256": character * 64,
            "configuration_sha256": chr(ord(character) + 1) * 64,
            "source_sha256": chr(ord(character) + 2) * 64,
        }
        for arm, character in (("candidate", "1"), ("control", "4"))
    }
    seeds = tuple(range(10_000, 10_128))
    commitments = []
    replays = []
    previous = "0" * 64
    for seed_index, seed in enumerate(seeds):
        family = "bowl" if seed_index % 2 == 0 else "skip"
        for arm in ("candidate", "control"):
            sequence_index = len(commitments)
            output = _canary_output(arm, seed, family)
            output_bytes = _runtime_bytes(output)
            stored = _gzip_bytes(output_bytes)
            relative = f"canary/outputs/{sequence_index:04d}-{arm}.json.gz"
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(stored)
            artifact = {
                "encoding": "deterministic-gzip-v1",
                "path": relative,
                "stored_sha256": hashlib.sha256(stored).hexdigest(),
                "stored_size_bytes": len(stored),
                "uncompressed_sha256": hashlib.sha256(output_bytes).hexdigest(),
                "uncompressed_size_bytes": len(output_bytes),
            }
            body = {
                "arm": arm,
                "arm_binding": bindings[arm],
                "output_artifact": artifact,
                "output_sha256": artifact["uncompressed_sha256"],
                "previous_commitment_sha256": previous,
                "schema_version": (
                    "noncombat-card-acceptance-empirical-successor-"
                    "canary-commitment-v1"
                ),
                "seed": seed,
                "seed_index": seed_index,
                "sequence_index": sequence_index,
            }
            commitment = {
                **body,
                "commitment_sha256": hashlib.sha256(_runtime_bytes(body)).hexdigest(),
            }
            commitments.append(commitment)
            previous = commitment["commitment_sha256"]
            replay_body = {
                "arm": arm,
                "first_commitment_sha256": commitment["commitment_sha256"],
                "output_sha256": commitment["output_sha256"],
                "schema_version": (
                    "noncombat-card-acceptance-empirical-successor-canary-replay-v1"
                ),
                "seed": seed,
                "seed_index": seed_index,
                "sequence_index": sequence_index,
            }
            replays.append(
                {
                    **replay_body,
                    "replay_sha256": hashlib.sha256(
                        _runtime_bytes(replay_body)
                    ).hexdigest(),
                }
            )
    return seeds, bindings, commitments, replays


def test_independent_verifier_reconstructs_canary_outputs_chain_and_replays(
    tmp_path,
):
    verifier = _verifier()
    seeds, bindings, commitments, replays = _canary_evidence(tmp_path)

    result = verifier.verify_canary_evidence(
        artifact_root=tmp_path,
        seeds=seeds,
        arm_bindings=bindings,
        commitments=commitments,
        replays=replays,
    )

    assert result["verified"] is True
    assert result["commitment_count"] == 256
    assert result["replay_count"] == 256
    assert result["concentration"]["passed"] is True
    assert result["concentration"]["selected_family"]["counts"] == {
        "bowl": 64,
        "skip": 64,
    }


def test_independent_canary_verifier_rejects_replay_or_artifact_drift(tmp_path):
    verifier = _verifier()
    seeds, bindings, commitments, replays = _canary_evidence(tmp_path)
    replays[1]["output_sha256"] = "f" * 64

    with pytest.raises(verifier.VerificationError, match="replay|output|digest"):
        verifier.verify_canary_evidence(
            artifact_root=tmp_path,
            seeds=seeds,
            arm_bindings=bindings,
            commitments=commitments,
            replays=replays,
        )


def _holdout_evidence():
    runtime = _runtime()
    seeds = tuple(range(20_000, 20_512))
    pairs = []
    observations = []
    for seed_index, seed in enumerate(seeds):
        pairs.append(
            {
                "candidate_floor_progress": 1.0,
                "candidate_output_sha256": f"{seed_index + 1:064x}",
                "candidate_victory": 1,
                "control_floor_progress": 0.0,
                "control_output_sha256": f"{seed_index + 513:064x}",
                "control_victory": 0,
                "floor_progress_difference": 1.0,
                "seed": seed,
                "seed_index": seed_index,
            }
        )
        family = "bowl" if seed_index % 2 == 0 else "skip"
        observations.append(
            {
                "decision_id": f"candidate:seed-{seed}:decision-0",
                "decision_index": 0,
                "family_order": ["bowl", "skip"],
                "seed": seed,
                "selected_family": family,
                "unique_greedy_family_id": family,
            }
        )
    gate = {
        "counts": {"bowl": 256, "skip": 256},
        "denominator": 512,
        "family_count": 2,
        "maximum_count": 256,
        "maximum_rate": 0.5,
        "passed": True,
    }
    bootstrap = runtime.paired_floor_bootstrap_interval((1.0,) * 512)
    evidence = {
        "arm_bindings": {
            "candidate": {
                "checkpoint_sha256": "1" * 64,
                "configuration_sha256": "2" * 64,
                "source_sha256": "3" * 64,
            },
            "control": {
                "checkpoint_sha256": "4" * 64,
                "configuration_sha256": "5" * 64,
                "source_sha256": "6" * 64,
            },
        },
        "bootstrap": bootstrap,
        "concentration": {
            "passed": True,
            "selected_family": gate,
            "unique_greedy_family": gate,
        },
        "family_observations": observations,
        "outcome_class": "victory_and_floor_signal",
        "pairs": pairs,
        "resource_use": {"holdout_environment_accesses": 1_024},
        "seeds": list(seeds),
        "verdict": "holdout_completed",
        "verified_canary": {
            "terminal_sha256": "7" * 64,
            "verdict": "canary_passed",
            "verified": True,
        },
        "victory_counts": {"candidate": 512, "control": 0},
    }
    return evidence


def test_independent_verifier_reconstructs_holdout_bootstrap_and_outcome():
    verifier = _verifier()
    evidence = _holdout_evidence()

    result = verifier.verify_holdout_evidence(evidence)

    assert result["verified"] is True
    assert result["pair_count"] == 512
    assert result["outcome_class"] == "victory_and_floor_signal"
    assert result["bootstrap"] == evidence["bootstrap"]
    assert result["truth_table"] == {
        "equal:false": "no_learning_signal",
        "equal:true": "floor_only_signal",
        "fewer:false": "no_learning_signal",
        "fewer:true": "inconclusive_signal",
        "greater:false": "inconclusive_signal",
        "greater:true": "victory_and_floor_signal",
    }


def test_independent_holdout_verifier_rejects_pair_or_outcome_drift():
    verifier = _verifier()
    evidence = _holdout_evidence()
    evidence["pairs"][10]["floor_progress_difference"] = 0.0

    with pytest.raises(verifier.VerificationError, match="pair|floor|bootstrap"):
        verifier.verify_holdout_evidence(evidence)


def _adam_parameter(name, owner, pre, components, *, step=0):
    combined = sum(value or 0.0 for value in components.values())
    applied = combined
    next_step = step + 1
    first_moment = 0.9 * 0.0 + 0.1 * applied
    second_moment = 0.999 * 0.0 + 0.001 * applied * applied
    step_size = 0.001 / (1.0 - 0.9**next_step)
    denominator = (
        math.sqrt(second_moment) / math.sqrt(1.0 - 0.999**next_step)
    ) + 1e-8
    post = pre - step_size * first_moment / denominator
    return {
        "adam_after": {
            "exp_avg": [first_moment],
            "exp_avg_sq": [second_moment],
            "step": next_step,
        },
        "adam_before": {
            "exp_avg": [0.0],
            "exp_avg_sq": [0.0],
            "step": step,
        },
        "applied_gradient": [applied],
        "combined_gradient": [combined],
        "component_gradients": {
            component: (None if value is None else [value])
            for component, value in components.items()
        },
        "name": name,
        "owner": owner,
        "post_parameter": [post],
        "pre_parameter": [pre],
        "shape": [1],
    }


def _objective_adam_evidence():
    components = {
        "family_policy": 1.0,
        "conditional_policy": 0.5,
        "family_entropy": -0.006,
        "conditional_entropy": -0.003,
    }
    return {
        "arm": "candidate",
        "card_decisions": [
            {
                "advantage": 2.0,
                "family_entropy": 0.6,
                "per_family_conditional_entropies": [0.2, 0.4],
                "selected_conditional_log_probability": -0.25,
                "selected_family_log_probability": -0.5,
            }
        ],
        "component_order": [
            "family_policy",
            "conditional_policy",
            "family_entropy",
            "conditional_entropy",
        ],
        "gradient_norm_ceiling": 1.0,
        "optimizer": {
            "betas": [0.9, 0.999],
            "eps": 1e-8,
            "learning_rate": 0.001,
            "name": "adam",
            "weight_decay": 0.0,
        },
        "parameters": [
            _adam_parameter(
                "family_head.bias",
                "family",
                1.0,
                {
                    "family_policy": 0.3,
                    "conditional_policy": None,
                    "family_entropy": -0.1,
                    "conditional_entropy": None,
                },
            ),
            _adam_parameter(
                "conditional_ranker.bias",
                "conditional",
                -1.0,
                {
                    "family_policy": None,
                    "conditional_policy": 0.4,
                    "family_entropy": None,
                    "conditional_entropy": -0.2,
                },
            ),
        ],
        "postclip_global_norm": math.sqrt(0.08),
        "preclip_global_norm": math.sqrt(0.08),
        "reported_components": components,
        "reported_total_loss": sum(components.values()),
        "schema_version": (
            "noncombat-card-acceptance-empirical-successor-optimizer-evidence-v1"
        ),
    }


def test_independent_verifier_reconstructs_objective_gradients_and_adam():
    verifier = _verifier()
    evidence = _objective_adam_evidence()

    result = verifier.verify_objective_and_adam_evidence(evidence)

    assert result["verified"] is True
    assert result["card_decision_count"] == 1
    assert result["parameter_count"] == 2
    assert result["components"] == pytest.approx(evidence["reported_components"])
    assert result["total_loss"] == pytest.approx(1.491)


def test_independent_optimizer_verifier_rejects_gradient_or_adam_drift():
    verifier = _verifier()
    evidence = _objective_adam_evidence()
    evidence["parameters"][0]["post_parameter"][0] += 0.01

    with pytest.raises(verifier.VerificationError, match="Adam|parameter|gradient"):
        verifier.verify_objective_and_adam_evidence(evidence)


def _baseline_feature_sha256(values):
    identity = {
        "dense_dim": 128,
        "dtype": "float32",
        "entries": [
            [index, value] for index, value in enumerate(values) if value != 0.0
        ],
        "folding": "ascending-source-index-modulo-128-float32-add-v1",
        "schema_version": "cross-fitted-baseline-state-features-v1",
        "source_dim": 1_024,
    }
    return hashlib.sha256(_runtime_bytes(identity) + b"\n").hexdigest()


def _cross_fitted_evidence():
    trajectory_ids = [f"candidate:seed-{30_000 + index}" for index in range(64)]
    folds = {
        f"fold-{fold_index}": sorted(
            trajectory_id
            for index, trajectory_id in enumerate(trajectory_ids)
            if index % 4 == fold_index
        )
        for fold_index in range(4)
    }
    coefficients = [2.0] + [0.0] * 128
    rhs = [2.0] + [0.0] * 128
    absolute_product_sums = [2.0] + [0.0] * 128
    models = []
    for fold_id, held_out in folds.items():
        models.append(
            {
                "absolute_product_sums": absolute_product_sums,
                "coefficients": coefficients,
                "fit_trajectory_ids": sorted(set(trajectory_ids) - set(held_out)),
                "fold_id": fold_id,
                "held_out_trajectory_ids": held_out,
                "kkt_residuals": [0.0] * 129,
                "rhs": rhs,
            }
        )
    features = [0.0] * 128
    decisions = []
    for index, trajectory_id in enumerate(trajectory_ids):
        fold_id = f"fold-{index % 4}"
        decisions.append(
            {
                "advantage": 0.0,
                "baseline_prediction": 2.0,
                "decision_id": f"{trajectory_id}:decision-0",
                "decision_index": 0,
                "feature_sha256": _baseline_feature_sha256(features),
                "feature_values": features,
                "fold_id": fold_id,
                "preclip_little_endian_hex": struct.pack("<d", 2.0).hex(),
                "raw_return": 2.0,
                "trajectory_id": trajectory_id,
                "unclipped_prediction": 2.0,
                "was_clipped": False,
            }
        )
    return {
        "arm": "candidate",
        "decisions": decisions,
        "fold_trajectories": folds,
        "models": models,
        "schema_version": (
            "noncombat-card-acceptance-empirical-successor-"
            "cross-fitted-baseline-evidence-v1"
        ),
        "trajectory_ids": trajectory_ids,
    }


def test_independent_verifier_reconstructs_cross_fitted_advantages():
    verifier = _verifier()
    evidence = _cross_fitted_evidence()

    result = verifier.verify_cross_fitted_baseline_evidence(evidence)

    assert result == {
        "advantage_count": 64,
        "arm": "candidate",
        "fold_count": 4,
        "trajectory_count": 64,
        "verified": True,
    }


def test_independent_cross_fitted_verifier_rejects_fold_or_advantage_drift():
    verifier = _verifier()
    evidence = _cross_fitted_evidence()
    evidence["decisions"][0]["advantage"] = 1.0

    with pytest.raises(verifier.VerificationError, match="advantage|prediction|fold"):
        verifier.verify_cross_fitted_baseline_evidence(evidence)


def test_independent_cross_fitted_verifier_rejects_forged_normal_equation():
    verifier = _verifier()
    evidence = _cross_fitted_evidence()
    evidence["models"][0]["rhs"][0] = 100.0
    evidence["models"][0]["absolute_product_sums"][0] = 100.0

    with pytest.raises(verifier.VerificationError, match="normal equation|KKT|rhs"):
        verifier.verify_cross_fitted_baseline_evidence(evidence)


def _rollback_fixture(tmp_path: Path):
    control = _control()
    verifier = _verifier()
    external = tmp_path / "external"
    control_checkpoint = external / "experiment" / "control-checkpoint.bin"
    control_configuration = external / "experiment" / "control-config.json"
    production_config = external / "production" / "config.properties"
    production_checkpoints = external / "production" / "checkpoints"
    control_checkpoint.parent.mkdir(parents=True)
    production_checkpoints.mkdir(parents=True)
    control_checkpoint.write_bytes(b"registered-control-checkpoint")
    control_configuration.write_bytes(b'{"arm":"control"}\n')
    production_config.write_bytes(b'command="production"\n')
    (production_checkpoints / "production.bin").write_bytes(
        b"registered-production-checkpoint"
    )
    authority = control.build_rollback_authority(
        target_relative_path="experiment_target.json",
        control_checkpoint=control.external_file_binding(control_checkpoint),
        control_configuration=control.external_file_binding(control_configuration),
        production_isolation=control.build_isolation_identity(
            communication_mod_config=production_config,
            production_checkpoint_root=production_checkpoints,
        ),
    )
    output = tmp_path / "execution"
    output.mkdir()
    target = output / authority["target_relative_path"]
    target_bytes = control.canonical_json_bytes(authority["control_target"])
    target.write_bytes(target_bytes)
    expected_control = {
        "checkpoint": authority["control_target"]["checkpoint"],
        "configuration": authority["control_target"]["configuration"],
    }
    identity = {
        "authorization_sha256": "a" * 64,
        "registration_sha256": "b" * 64,
        "request_sha256": "c" * 64,
        "stage": "training",
    }
    body = {
        "candidate_enabled": False,
        "control_identities_after": {
            "matches_registered": True,
            "observed": expected_control,
        },
        "control_identities_before": {
            "matches_registered": True,
            "observed": expected_control,
        },
        "control_identities_verified": True,
        "control_target_after": {
            "path": authority["target_relative_path"],
            "sha256": hashlib.sha256(target_bytes).hexdigest(),
            "size_bytes": len(target_bytes),
        },
        "control_target_before": None,
        "control_target_verified": True,
        "downstream_authority": verifier.verifier_contract()["authority"],
        "identity": identity,
        "production_isolation_after": {
            "matches_registered": True,
            "observed": authority["production_isolation"],
        },
        "production_isolation_before": {
            "matches_registered": True,
            "observed": authority["production_isolation"],
        },
        "production_isolation_verified": True,
        "rollback_authority_sha256": authority["rollback_authority_sha256"],
        "schema_version": (
            "noncombat-card-acceptance-empirical-successor-"
            "rollback-observation-v1"
        ),
        "status": "rollback_verified",
        "trigger_class": "canary",
    }
    observation = {
        **body,
        "rollback_observation_sha256": hashlib.sha256(
            control.canonical_json_bytes(body)
        ).hexdigest(),
    }
    (output / "rollback.json").write_bytes(control.canonical_json_bytes(observation))
    return output, authority, identity, production_config, target


def test_independent_verifier_reobserves_rollback_and_production_isolation(tmp_path):
    verifier = _verifier()
    output, authority, identity, _production_config, _target = _rollback_fixture(
        tmp_path
    )

    result = verifier.verify_rollback_evidence(
        output,
        rollback_authority=authority,
        expected_identity=identity,
    )

    assert result == {
        "candidate_enabled": False,
        "control_target_sha256": authority["control_target"]["target_sha256"],
        "production_isolation_verified": True,
        "status": "rollback_verified",
        "trigger_class": "canary",
        "verified": True,
    }


@pytest.mark.parametrize("drift", ["production", "target"])
def test_independent_rollback_verifier_rejects_postpublication_drift(
    tmp_path,
    drift,
):
    verifier = _verifier()
    output, authority, identity, production_config, target = _rollback_fixture(
        tmp_path
    )
    if drift == "production":
        production_config.write_bytes(b'command="drifted"\n')
    else:
        target.write_bytes(b'{"candidate_enabled":true}\n')

    with pytest.raises(
        verifier.VerificationError,
        match="rollback|control target|production isolation|changed",
    ):
        verifier.verify_rollback_evidence(
            output,
            rollback_authority=authority,
            expected_identity=identity,
        )


def _seed_inventory_evidence():
    verifier = _verifier()
    source_payload = b'{"used_seeds":[0,2]}\n'
    source_path = "reports/history/seeds.json"
    sources = [
        {
            "document_count": 1,
            "format": "json",
            "path": source_path,
            "row_count": 2,
            "sha256": hashlib.sha256(source_payload).hexdigest(),
            "size_bytes": len(source_payload),
        }
    ]
    registry_body = {
        "excluded_roots": [],
        "output_root_policy": {
            "candidate_output_root": (
                "reports/noncombat_card_acceptance_empirical_successor_test"
            ),
            "excluded_kinds": [
                "attempt",
                "candidate",
                "scratch",
                "sealed",
                "staging",
                "temporary",
            ],
            "registered_source_root": "reports",
            "schema_version": (
                "noncombat-card-acceptance-empirical-successor-"
                "output-root-policy-v1"
            ),
        },
        "repository_commit": "d" * 40,
        "schema_version": (
            "noncombat-card-acceptance-empirical-successor-"
            "seed-source-registry-v1"
        ),
        "source_count": 1,
        "sources": sources,
    }
    registry = {
        **registry_body,
        "registry_sha256": hashlib.sha256(
            verifier.canonical_json_bytes(registry_body)
        ).hexdigest(),
    }
    rows = [
        {
            "document_index": 0,
            "json_path": f"/used_seeds/{index}",
            "role": "used",
            "seed": seed,
            "source_path": source_path,
        }
        for index, seed in enumerate((0, 2))
    ]
    selected = [seed for seed in range(1_154) if seed not in {0, 2}]
    cohorts = {
        "training": selected[:512],
        "canary": selected[512:640],
        "holdout": selected[640:1_152],
    }
    body = {
        "authorization_sha256": "e" * 64,
        "cohort_counts": {"training": 512, "canary": 128, "holdout": 512},
        "cohorts": cohorts,
        "excluded_seed_count": 2,
        "excluded_seeds": [0, 2],
        "excluded_seeds_sha256": hashlib.sha256(
            verifier.canonical_json_bytes([0, 2])
        ).hexdigest(),
        "request_sha256": "f" * 64,
        "repository_commit": "d" * 40,
        "role_sha256": {
            role: hashlib.sha256(verifier.canonical_json_bytes(seeds)).hexdigest()
            for role, seeds in cohorts.items()
        },
        "row_count": len(rows),
        "rows": rows,
        "schema_version": (
            "noncombat-card-acceptance-empirical-successor-seed-inventory-v1"
        ),
        "source_registry": registry,
    }
    return {
        **body,
        "inventory_sha256": hashlib.sha256(
            verifier.canonical_json_bytes(body)
        ).hexdigest(),
    }


def test_independent_verifier_reconstructs_fixed_seed_inventory():
    verifier = _verifier()
    evidence = _seed_inventory_evidence()

    result = verifier.verify_seed_inventory_evidence(evidence)

    assert result == {
        "cohort_counts": {"training": 512, "canary": 128, "holdout": 512},
        "excluded_seed_count": 2,
        "inventory_sha256": evidence["inventory_sha256"],
        "source_count": 1,
        "verified": True,
    }


def test_independent_inventory_verifier_rejects_nonfresh_cohort():
    verifier = _verifier()
    evidence = _seed_inventory_evidence()
    evidence["cohorts"]["training"][0] = 0

    with pytest.raises(verifier.VerificationError, match="cohort|selection|fresh"):
        verifier.verify_seed_inventory_evidence(evidence)
