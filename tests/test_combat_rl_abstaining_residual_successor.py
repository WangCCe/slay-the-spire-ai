from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch

from analysis_scripts.combat_rl_abstaining_residual_head import state_dict_sha256
from analysis_scripts.combat_rl_abstaining_residual_successor import (
    BATCH_SIZE,
    EXPECTED_CHECKPOINT_SHA256,
    EXPECTED_COLLECTION_REPORT_SHA256,
    EXPECTED_INTERPRETER,
    EXPECTED_REGISTRATION_SHA256,
    EXPECTED_TRANSITION_COUNT,
    FIXED_RECIPE,
    FIXED_TECHNICAL_GATES,
    OPTIMIZER_STEPS,
    _fit_residual_candidate,
    _residual_eligibility,
    _canonical_json_bytes,
    _fixed_input_arguments,
    _require_round_trip_exact,
    _validate_collection_report,
    _validate_registration,
    _validate_runner_binding,
)
from spirecomm.ai.rl.v2.network import create_dqn_v2


REPO_ROOT = Path(__file__).resolve().parents[1]
METADATA = {
    "network_type": "standard",
    "continuous_dim": 4,
    "action_dim": 3,
    "card_vocab": 5,
    "potion_vocab": 5,
    "relic_vocab": 5,
    "card_slots": 1,
    "potion_slots": 1,
    "relic_slots": 1,
}


def _registration():
    return {
        "schema_version": 1,
        "registration_id": "combat-rl-abstaining-residual-collection-20260828-r1",
        "experiment_id": "combat-rl-abstaining-residual-successor-20260828-r1",
        "fixed_downstream_recipe": copy.deepcopy(FIXED_RECIPE),
        "technical_gates": copy.deepcopy(FIXED_TECHNICAL_GATES),
        "authority": {
            "collection": True,
            "cpu_development_fit": False,
            "fresh_holdout": False,
            "gameplay_evaluation": False,
            "qualification": False,
            "promotion": False,
            "policy_quality_claim": False,
            "production_checkpoint_loading": False,
            "same_corpus_retry_or_tuning": False,
        },
        "collection": {
            "game_count": 10,
            "epsilon": 0.0,
            "learning_starts": 100000,
            "optimizer_updates": 0,
        },
    }


def _spans(parent_state):
    count = 64
    parent = create_dqn_v2(device="cpu", **METADATA)
    parent.load_state_dict(parent_state)
    parent.eval()
    continuous = torch.linspace(-1.0, 1.0, count * 4).reshape(count, 4)
    ids = (torch.arange(count) % 5).reshape(count, 1)
    masks = torch.ones((count, 3), dtype=torch.bool)
    with torch.no_grad():
        parent_actions = parent(continuous, ids, ids, ids, masks).argmax(1)
    changed = torch.tensor([False] * 32 + [True] * 32, dtype=torch.bool)
    actions = torch.where(changed, (parent_actions + 1) % 3, parent_actions)
    return {
        "continuous": continuous,
        "card_ids": ids,
        "potion_ids": ids,
        "relic_ids": ids,
        "actions": actions,
        "rewards": torch.where(changed, torch.ones(count), torch.zeros(count)),
        "next_continuous": torch.zeros_like(continuous),
        "next_card_ids": torch.zeros_like(ids),
        "next_potion_ids": torch.zeros_like(ids),
        "next_relic_ids": torch.zeros_like(ids),
        "dones": torch.ones(count, dtype=torch.bool),
        "action_masks": masks,
        "next_action_masks": torch.zeros_like(masks),
        "anchor_to_executed_action": changed,
        "proposed_action_indices": parent_actions,
        "bootstrap_discounts": torch.zeros(count),
        "span_lengths": torch.ones(count, dtype=torch.long),
    }


def test_registered_recipe_and_gate_contract_is_exact():
    assert OPTIMIZER_STEPS == 128
    assert BATCH_SIZE == 64
    assert FIXED_RECIPE["batch_direct_count"] == 32
    assert FIXED_RECIPE["batch_changed_count"] == 32
    assert FIXED_RECIPE["adapter_hidden_dim"] == 32
    assert FIXED_RECIPE["gate_threshold"] == pytest.approx(0.9)
    assert FIXED_RECIPE["residual_scale"] == pytest.approx(4.0)
    assert FIXED_RECIPE["learning_rate"] == pytest.approx(0.001)
    assert FIXED_TECHNICAL_GATES["direct_gate_open_share_maximum"] == pytest.approx(0.1)
    assert FIXED_TECHNICAL_GATES["changed_gate_open_share_minimum"] == pytest.approx(0.25)

    _validate_registration(_registration())
    changed = _registration()
    changed["fixed_downstream_recipe"]["optimizer_steps"] = 127
    with pytest.raises(ValueError, match="recipe changed"):
        _validate_registration(changed)


def test_fixed_input_hashes_cannot_be_replaced_by_cli_values():
    args = SimpleNamespace(
        registration_sha256=EXPECTED_REGISTRATION_SHA256,
        collection_report_sha256=EXPECTED_COLLECTION_REPORT_SHA256,
        expected_checkpoint_sha256=EXPECTED_CHECKPOINT_SHA256,
        expected_transition_count=EXPECTED_TRANSITION_COUNT,
        experiment_id="combat-rl-abstaining-residual-successor-20260828-r1",
    )
    _fixed_input_arguments(args)

    args.expected_checkpoint_sha256 = "0" * 64
    with pytest.raises(ValueError, match="expected_checkpoint_sha256 changed"):
        _fixed_input_arguments(args)


def test_qualified_collection_report_matches_runner_contract():
    report = json.loads(
        (
            REPO_ROOT
            / "reports"
            / "combat_rl_abstaining_residual_collection_20260828_r1"
            / "report.json"
        ).read_text(encoding="utf-8")
    )
    _validate_collection_report(
        report,
        expected_registration_sha256=(
            "404061b8838dc90dd9215ecce1ccd9a3198acfb71d75674a784700f7d9744078"
        ),
        expected_checkpoint_sha256=(
            "ba02c749e73caecae59469220abe30e40e826699e95ca910a8b18d7eaa1f5900"
        ),
        expected_transition_count=1916,
    )


def test_runner_binding_rejects_recipe_or_source_changes():
    runner = (
        REPO_ROOT
        / "analysis_scripts"
        / "combat_rl_abstaining_residual_successor.py"
    ).resolve()
    registration = (
        REPO_ROOT
        / "reports"
        / "combat_rl_abstaining_residual_collection_20260828_r1_registration.json"
    ).resolve()
    report = (
        REPO_ROOT
        / "reports"
        / "combat_rl_abstaining_residual_collection_20260828_r1"
        / "report.json"
    ).resolve()
    checkpoint = (
        REPO_ROOT
        / "reports"
        / "combat_rl_abstaining_residual_collection_20260828_r1"
        / "rl_combat_model_ep10_steps1916.pth"
    ).resolve()
    output = (
        REPO_ROOT / "reports" / "combat_rl_abstaining_residual_successor_fixture"
    ).resolve()
    receipt = output.with_suffix(".attempt.json")
    source_commit = "a" * 40
    registration_sha = "b" * 64
    report_sha = "c" * 64
    checkpoint_sha = "d" * 64
    source_files = {"runner.py": "e" * 64}
    command_template = ["python", "-I", "runner.py", "<self-sha256>"]
    binding = {
        "schema_version": 1,
        "experiment_id": "combat-rl-abstaining-residual-successor-20260828-r1",
        "source_commit": source_commit,
        "interpreter": str(EXPECTED_INTERPRETER.resolve()),
        "isolated_mode": "-I",
        "command_template": command_template,
        "source_files": source_files,
        "runner": {
            "path": str(runner),
            "sha256": hashlib.sha256(runner.read_bytes()).hexdigest(),
        },
        "registration": {"path": str(registration), "sha256": registration_sha},
        "collection_report": {"path": str(report), "sha256": report_sha},
        "training_checkpoint": {"path": str(checkpoint), "sha256": checkpoint_sha},
        "output_dir": str(output),
        "staging_dir": str(output.with_name(f".{output.name}.staging")),
        "attempt_receipt": str(receipt),
        "failure_policy": "started_attempt_is_not_retried_or_tuned",
        "fixed_recipe_sha256": hashlib.sha256(
            _canonical_json_bytes(FIXED_RECIPE)
        ).hexdigest(),
        "fixed_technical_gates_sha256": hashlib.sha256(
            _canonical_json_bytes(FIXED_TECHNICAL_GATES)
        ).hexdigest(),
    }

    staging = _validate_runner_binding(
        binding,
        source_commit=source_commit,
        runner_path=runner,
        registration_path=registration,
        registration_sha256=registration_sha,
        collection_report_path=report,
        collection_report_sha256=report_sha,
        checkpoint_path=checkpoint,
        checkpoint_sha256=checkpoint_sha,
        output_dir=output,
        attempt_receipt=receipt,
        source_files=source_files,
        command_template=command_template,
    )
    assert staging == output.with_name(f".{output.name}.staging")

    changed = copy.deepcopy(binding)
    changed["fixed_recipe_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="recipe hash changed"):
        _validate_runner_binding(
            changed,
            source_commit=source_commit,
            runner_path=runner,
            registration_path=registration,
            registration_sha256=registration_sha,
            collection_report_path=report,
            collection_report_sha256=report_sha,
            checkpoint_path=checkpoint,
            checkpoint_sha256=checkpoint_sha,
            output_dir=output,
            attempt_receipt=receipt,
            source_files=source_files,
            command_template=command_template,
        )

    nested_receipt = output / "started.json"
    nested = copy.deepcopy(binding)
    nested["attempt_receipt"] = str(nested_receipt)
    with pytest.raises(ValueError, match="outside output and staging"):
        _validate_runner_binding(
            nested,
            source_commit=source_commit,
            runner_path=runner,
            registration_path=registration,
            registration_sha256=registration_sha,
            collection_report_path=report,
            collection_report_sha256=report_sha,
            checkpoint_path=checkpoint,
            checkpoint_sha256=checkpoint_sha,
            output_dir=output,
            attempt_receipt=nested_receipt,
            source_files=source_files,
            command_template=command_template,
        )


def test_round_trip_failure_is_fatal_before_publication():
    _require_round_trip_exact(True)
    with pytest.raises(RuntimeError, match="serialization round trip differs"):
        _require_round_trip_exact(False)


def test_residual_fit_updates_only_correction_with_balanced_batches():
    torch.manual_seed(31)
    parent = create_dqn_v2(device="cpu", **METADATA)
    parent_state = copy.deepcopy(parent.state_dict())
    parent_hash = state_dict_sha256(parent_state)

    adapter, optimizer, telemetry = _fit_residual_candidate(
        metadata=METADATA,
        parent_state=parent_state,
        target_state=parent_state,
        spans=_spans(parent_state),
        train_indices=torch.arange(64),
        optimizer_steps=2,
        batch_size=64,
        seed=37,
    )

    assert telemetry["optimizer_update_count"] == 2
    assert telemetry["all_objective_values_finite"] is True
    assert telemetry["parent_immutable"] is True
    assert telemetry["batch_provenance"]["minimum_direct_count"] == 32
    assert telemetry["batch_provenance"]["minimum_changed_count"] == 32
    assert state_dict_sha256(adapter.parent.state_dict()) == parent_hash
    assert all(parameter.grad is None for parameter in adapter.parent.parameters())
    optimizer_parameter_ids = {
        id(parameter)
        for group in optimizer.param_groups
        for parameter in group["params"]
    }
    assert optimizer_parameter_ids == {
        id(parameter) for parameter in adapter.correction.parameters()
    }


def test_residual_eligibility_applies_gate_and_stability_thresholds():
    validation = {
        "parent_smooth_l1": 4.0,
        "candidate_smooth_l1": 3.5,
        "action_disagreement_share": 0.20,
        "positive_energy_end_turn_count_delta": 1,
        "gate_open_share": 0.30,
        "strata": {
            "direct": {
                "transition_count": 20,
                "action_disagreement_share": 0.05,
                "gate_open_share": 0.05,
            },
            "changed_proposal": {
                "transition_count": 20,
                "parent_anchor_label_agreement": 0.10,
                "candidate_anchor_label_agreement": 0.30,
                "gate_open_share": 0.50,
            },
        },
    }
    training = {
        "optimizer_update_count": 128,
        "all_objective_values_finite": True,
        "parent_immutable": True,
            "batch_provenance": {
                "minimum_direct_count": 32,
                "maximum_direct_count": 32,
                "minimum_changed_count": 32,
                "maximum_changed_count": 32,
                "ineligible_sample_count": 0,
            },
    }

    passed = _residual_eligibility(
        validation=validation,
        training=training,
        adapter_round_trip_exact=True,
        callability_complete=True,
    )
    assert passed["all_conditions_passed"] is True

    leaked = copy.deepcopy(validation)
    leaked["strata"]["direct"]["gate_open_share"] = 0.11
    failed = _residual_eligibility(
        validation=leaked,
        training=training,
        adapter_round_trip_exact=True,
        callability_complete=True,
    )
    assert failed["direct_gate_open_share_at_most_ceiling"] is False
    assert failed["all_conditions_passed"] is False


def test_isolated_direct_entrypoint_bootstraps_repo_root():
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            str(
                REPO_ROOT
                / "analysis_scripts"
                / "combat_rl_abstaining_residual_successor.py"
            ),
            "--help",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "--runner-binding-supplement" in result.stdout
