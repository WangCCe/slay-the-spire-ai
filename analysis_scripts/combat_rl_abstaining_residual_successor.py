"""Fit one source-bound frozen-parent abstaining residual successor."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, Mapping

import torch
import torch.nn.functional as F


REPO_ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_DIR = Path(__file__).resolve().parent
for import_root in (REPO_ROOT, ANALYSIS_DIR):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from combat_rl_abstaining_residual_head import (  # noqa: E402
    AdapterConfig,
    AbstainingResidualQAdapter,
    build_adapter_artifact,
    build_residual_optimizer,
    load_adapter_artifact,
    residual_training_loss,
    state_dict_sha256,
    validate_residual_training_source,
)
from combat_rl_candidate_callability_successor import (  # noqa: E402
    _batch,
    _frozen_next_bootstrap,
    _make_network,
    _provenance_action_metrics,
    _split_candidate_spans,
    _stratified_optimizer_batches,
    _validate_callability_checkpoint,
    _validate_optimizer_batch_provenance,
    _variable_bootstrap_targets,
    build_candidate_decision_spans,
)
from combat_rl_inventory_embedding_successor import (  # noqa: E402
    _atomic_torch_save,
    _sha256,
)
from combat_rl_provenance_aware_successor import _summary  # noqa: E402
from spirecomm.ai.rl.v2.action_space import END_TURN_ACTION  # noqa: E402
from spirecomm.ai.rl.v2.state_encoder import StateEncoderV2  # noqa: E402


REGISTRATION_ID = "combat-rl-abstaining-residual-collection-20260828-r1"
EXPERIMENT_ID = "combat-rl-abstaining-residual-successor-20260828-r1"
COLLECTION_DECISION = "collection_qualified_for_runner_binding_supplement"
EXPECTED_REGISTRATION_SHA256 = (
    "404061b8838dc90dd9215ecce1ccd9a3198acfb71d75674a784700f7d9744078"
)
EXPECTED_COLLECTION_REPORT_SHA256 = (
    "beb0304b4c6d46a6b99f3e29663484fad8fbf5251e212d6d52d26caee4e37484"
)
EXPECTED_CHECKPOINT_SHA256 = (
    "ba02c749e73caecae59469220abe30e40e826699e95ca910a8b18d7eaa1f5900"
)
EXPECTED_TRANSITION_COUNT = 1916
EXPECTED_INTERPRETER = Path(r"D:\anaconda\envs\stsai\python.exe")
VALIDATION_FRACTION = 0.2
SPLIT_SEED = 2026082812
TRAINING_SEED = 2026082813
LEARNING_RATE = 0.001
BATCH_SIZE = 64
OPTIMIZER_STEPS = 128
GAMMA = 0.99

FIXED_RECIPE = {
    "status": "fixed_pending_runner_binding_supplement",
    "architecture": "frozen_parent_abstaining_bounded_residual",
    "adapter_hidden_dim": 32,
    "gate_threshold": 0.9,
    "residual_scale": 4.0,
    "batch_direct_count": 32,
    "batch_changed_count": 32,
    "batch_size": BATCH_SIZE,
    "optimizer": "Adam",
    "learning_rate": LEARNING_RATE,
    "optimizer_steps": OPTIMIZER_STEPS,
    "gate_loss_weight": 1.0,
    "changed_action_loss_weight": 1.0,
    "changed_smdp_td_loss_weight": 0.25,
    "gamma": GAMMA,
    "bootstrap_action_policy": "frozen_parent_masked_greedy",
    "decision_unit": "candidate_callable_smdp_span",
    "device": "cpu",
    "validation_fraction": VALIDATION_FRACTION,
    "split_seed": SPLIT_SEED,
    "training_seed": TRAINING_SEED,
    "closed_checkpoint_sha256": (
        "9f4570eaa5c9fd5df770734a5cc038dd6ba87da7983838fed243f05ef19b1860"
    ),
    "supplement_rule": (
        "A later supplement may bind only runner source, checkpoint, output, "
        "and execution identities. It may not change the cohort, recipe, "
        "thresholds, seeds, or authority before fitting."
    ),
}

FIXED_TECHNICAL_GATES = {
    "validation_smdp_td_improves": True,
    "overall_parent_disagreement_minimum": 0.05,
    "direct_parent_disagreement_maximum": 0.1,
    "direct_gate_open_share_maximum": 0.1,
    "changed_gate_open_share_minimum": 0.25,
    "changed_proposal_executed_label_agreement_uplift_minimum": 0.1,
    "positive_energy_end_turn_increase_maximum": 2,
    "both_validation_candidate_strata_nonempty": True,
    "finite_objectives": True,
    "parent_state_immutable": True,
    "exact_serialization_round_trip": True,
    "complete_integrity_and_provenance": True,
}

REGISTERED_AUTHORITY = {
    "collection": True,
    "cpu_development_fit": False,
    "fresh_holdout": False,
    "gameplay_evaluation": False,
    "qualification": False,
    "promotion": False,
    "policy_quality_claim": False,
    "production_checkpoint_loading": False,
    "same_corpus_retry_or_tuning": False,
}

RESULT_AUTHORITY = {
    "cpu_development_fit_completed": True,
    "fresh_holdout": False,
    "gameplay_evaluation": False,
    "qualification": False,
    "promotion": False,
    "policy_quality_claim": False,
    "production_checkpoint_loading": False,
    "same_corpus_retry_or_tuning": False,
}

SOURCE_SNAPSHOT_PATHS = (
    "analysis_scripts/combat_rl_abstaining_residual_successor.py",
    "analysis_scripts/combat_rl_abstaining_residual_head.py",
    "analysis_scripts/combat_rl_candidate_callability_successor.py",
    "analysis_scripts/combat_rl_inventory_embedding_successor.py",
    "analysis_scripts/combat_rl_provenance_aware_successor.py",
    "analysis_scripts/combat_rl_dropout_update_ablation.py",
    "spirecomm/ai/rl/v2/action_space.py",
    "spirecomm/ai/rl/v2/network.py",
    "spirecomm/ai/rl/v2/replay_buffer.py",
    "spirecomm/ai/rl/v2/state_encoder.py",
    "spirecomm/ai/rl/v2/trainer.py",
)


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        indent=2,
        sort_keys=True,
    ).encode("ascii") + b"\n"


def _adapter_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    names = (
        "network_type",
        "continuous_dim",
        "action_dim",
        "card_vocab",
        "potion_vocab",
        "relic_vocab",
        "card_slots",
        "potion_slots",
        "relic_slots",
    )
    if any(name not in metadata for name in names):
        raise ValueError("checkpoint adapter metadata is incomplete")
    return {name: metadata[name] for name in names}


def _validate_registration(registration: Mapping[str, Any]) -> None:
    if registration.get("schema_version") != 1:
        raise ValueError("registration schema version changed")
    if registration.get("registration_id") != REGISTRATION_ID:
        raise ValueError("registration id changed")
    if registration.get("experiment_id") != EXPERIMENT_ID:
        raise ValueError("registration experiment id changed")
    if registration.get("fixed_downstream_recipe") != FIXED_RECIPE:
        raise ValueError("registration fixed downstream recipe changed")
    if registration.get("technical_gates") != FIXED_TECHNICAL_GATES:
        raise ValueError("registration technical gates changed")
    if registration.get("authority") != REGISTERED_AUTHORITY:
        raise ValueError("registration authority changed")
    collection = registration.get("collection")
    if not isinstance(collection, Mapping):
        raise ValueError("registration collection is missing")
    if (
        collection.get("game_count") != 10
        or collection.get("epsilon") != 0.0
        or collection.get("learning_starts") != 100000
        or collection.get("optimizer_updates") != 0
    ):
        raise ValueError("registration collection boundary changed")


def _validate_collection_report(
    report: Mapping[str, Any],
    *,
    expected_registration_sha256: str,
    expected_checkpoint_sha256: str,
    expected_transition_count: int,
) -> None:
    if report.get("decision") != COLLECTION_DECISION:
        raise ValueError("collection report is not qualified for runner binding")
    authority = report.get("authority")
    if not isinstance(authority, Mapping) or (
        authority.get("runner_binding_supplement") is not True
        or authority.get("cpu_development_fit") is not False
    ):
        raise ValueError("collection report authority changed")
    registration = report.get("registration")
    if not isinstance(registration, Mapping) or (
        registration.get("id") != REGISTRATION_ID
        or registration.get("sha256") != expected_registration_sha256
    ):
        raise ValueError("collection report registration binding changed")
    checkpoint = report.get("checkpoint")
    if not isinstance(checkpoint, Mapping):
        raise ValueError("collection report checkpoint is missing")
    expected = {
        "sha256": expected_checkpoint_sha256,
        "transition_count": expected_transition_count,
        "replay_schema_version": 3,
        "optimizer_state_count": 0,
        "online_target_equal": True,
        "parent_state_matches_production_r16": True,
        "direct_eval_parent_agreement": 1.0,
    }
    for name, value in expected.items():
        if checkpoint.get(name) != value:
            raise ValueError(f"collection report checkpoint {name} changed")
    integrity = report.get("integrity")
    expected_integrity = {
        "active_config_restored": True,
        "all_ascension_zero": True,
        "all_chose_seed": True,
        "all_registered_seeds_match": True,
        "debug_error_severity_count": 0,
        "error_suffix_exception_count": 0,
        "error_suffix_rl_failure_count": 0,
        "error_suffix_traceback_count": 0,
        "ironclad_autosave_count": 0,
        "max_games_exit_count": 1,
        "new_ai_marker_count": 10,
        "project_game_process_count": 0,
        "run_count": 10,
    }
    if not isinstance(integrity, Mapping) or any(
        integrity.get(name) != value for name, value in expected_integrity.items()
    ):
        raise ValueError("collection report integrity checks are incomplete")
    provenance = report.get("source_provenance")
    if not isinstance(provenance, Mapping) or (
        provenance.get("direct_unchanged_proposal_count") != 350
        or provenance.get("changed_same_state_proposal_count") != 502
        or provenance.get("no_proposal_takeover_count") != 1064
        or provenance.get("legacy_unknown_count") != 0
    ):
        raise ValueError("collection report callability provenance changed")
    spans = report.get("spans")
    if not isinstance(spans, Mapping) or (
        spans.get("decision_span_count") != 852
        or spans.get("source_row_reconciliation_count")
        != expected_transition_count
    ):
        raise ValueError("collection report SMDP reconciliation changed")


def _same_path(observed: Any, expected: Path) -> bool:
    if not isinstance(observed, str):
        return False
    return Path(observed).resolve() == expected.resolve()


def _is_within(path: Path, directory: Path) -> bool:
    path = path.resolve()
    directory = directory.resolve()
    return path == directory or directory in path.parents


def _fixed_input_arguments(args: argparse.Namespace) -> None:
    expected = {
        "registration_sha256": EXPECTED_REGISTRATION_SHA256,
        "collection_report_sha256": EXPECTED_COLLECTION_REPORT_SHA256,
        "expected_checkpoint_sha256": EXPECTED_CHECKPOINT_SHA256,
        "expected_transition_count": EXPECTED_TRANSITION_COUNT,
        "experiment_id": EXPERIMENT_ID,
    }
    for name, value in expected.items():
        if getattr(args, name) != value:
            raise ValueError(f"fixed residual input {name} changed")


def _git_blob(source_commit: str, relative_path: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{source_commit}:{relative_path}"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(
            f"source commit does not bind required path: {relative_path}"
        )
    return result.stdout


def _source_snapshot_hashes(source_commit: str) -> dict[str, str]:
    if len(source_commit) != 40 or any(
        character not in "0123456789abcdef" for character in source_commit
    ):
        raise ValueError("source commit must be a full lowercase Git hash")
    result: dict[str, str] = {}
    for relative_path in SOURCE_SNAPSHOT_PATHS:
        current_path = REPO_ROOT / relative_path
        current_hash = _sha256(current_path)
        committed_hash = hashlib.sha256(
            _git_blob(source_commit, relative_path)
        ).hexdigest()
        if current_hash != committed_hash:
            raise ValueError(
                f"current source differs from bound commit: {relative_path}"
            )
        result[relative_path] = current_hash
    return result


def _command_template(
    args: argparse.Namespace,
    *,
    runner_path: Path,
) -> list[str]:
    return [
        str(EXPECTED_INTERPRETER.resolve()),
        "-I",
        str(runner_path.resolve()),
        "--registration",
        str(args.registration.resolve()),
        "--registration-sha256",
        args.registration_sha256,
        "--collection-report",
        str(args.collection_report.resolve()),
        "--collection-report-sha256",
        args.collection_report_sha256,
        "--training-checkpoint",
        str(args.training_checkpoint.resolve()),
        "--expected-checkpoint-sha256",
        args.expected_checkpoint_sha256,
        "--expected-transition-count",
        str(args.expected_transition_count),
        "--runner-binding-supplement",
        str(args.runner_binding_supplement.resolve()),
        "--runner-binding-supplement-sha256",
        "<self-sha256>",
        "--output-dir",
        str(args.output_dir.resolve()),
        "--attempt-receipt",
        str(args.attempt_receipt.resolve()),
        "--experiment-id",
        args.experiment_id,
        "--source-commit",
        args.source_commit,
    ]


def _validate_runner_binding(
    binding: Mapping[str, Any],
    *,
    source_commit: str,
    runner_path: Path,
    registration_path: Path,
    registration_sha256: str,
    collection_report_path: Path,
    collection_report_sha256: str,
    checkpoint_path: Path,
    checkpoint_sha256: str,
    output_dir: Path,
    attempt_receipt: Path,
    source_files: Mapping[str, str],
    command_template: list[str],
) -> Path:
    if binding.get("schema_version") != 1:
        raise ValueError("runner binding schema version changed")
    if binding.get("experiment_id") != EXPERIMENT_ID:
        raise ValueError("runner binding experiment id changed")
    if binding.get("source_commit") != source_commit:
        raise ValueError("runner binding source commit changed")
    if not _same_path(binding.get("interpreter"), EXPECTED_INTERPRETER):
        raise ValueError("runner binding interpreter changed")
    if binding.get("isolated_mode") != "-I":
        raise ValueError("runner binding isolated mode changed")
    if binding.get("command_template") != command_template:
        raise ValueError("runner binding command template changed")
    if binding.get("source_files") != dict(source_files):
        raise ValueError("runner binding source file snapshot changed")
    runner = binding.get("runner")
    if not isinstance(runner, Mapping) or not _same_path(
        runner.get("path"), runner_path
    ) or runner.get("sha256") != _sha256(runner_path):
        raise ValueError("runner binding source identity changed")
    inputs = (
        ("registration", registration_path, registration_sha256),
        ("collection_report", collection_report_path, collection_report_sha256),
        ("training_checkpoint", checkpoint_path, checkpoint_sha256),
    )
    for name, path, sha256 in inputs:
        value = binding.get(name)
        if not isinstance(value, Mapping) or not _same_path(
            value.get("path"), path
        ) or value.get("sha256") != sha256:
            raise ValueError(f"runner binding {name} identity changed")
    if not _same_path(binding.get("output_dir"), output_dir):
        raise ValueError("runner binding output directory changed")
    if not _same_path(binding.get("attempt_receipt"), attempt_receipt):
        raise ValueError("runner binding attempt receipt changed")
    staging_dir = output_dir.with_name(f".{output_dir.name}.staging")
    if not _same_path(binding.get("staging_dir"), staging_dir):
        raise ValueError("runner binding staging directory changed")
    if _is_within(attempt_receipt, output_dir) or _is_within(
        attempt_receipt, staging_dir
    ):
        raise ValueError("attempt receipt must be outside output and staging")
    if binding.get("failure_policy") != "started_attempt_is_not_retried_or_tuned":
        raise ValueError("runner binding failure policy changed")
    if binding.get("fixed_recipe_sha256") != hashlib.sha256(
        _canonical_json_bytes(FIXED_RECIPE)
    ).hexdigest():
        raise ValueError("runner binding recipe hash changed")
    if binding.get("fixed_technical_gates_sha256") != hashlib.sha256(
        _canonical_json_bytes(FIXED_TECHNICAL_GATES)
    ).hexdigest():
        raise ValueError("runner binding technical gate hash changed")
    return staging_dir


def _fit_residual_candidate(
    *,
    metadata: Mapping[str, Any],
    parent_state: Mapping[str, torch.Tensor],
    target_state: Mapping[str, torch.Tensor],
    spans: Mapping[str, torch.Tensor],
    train_indices: torch.Tensor,
    learning_rate: float = LEARNING_RATE,
    batch_size: int = BATCH_SIZE,
    optimizer_steps: int = OPTIMIZER_STEPS,
    seed: int = TRAINING_SEED,
) -> tuple[AbstainingResidualQAdapter, torch.optim.Adam, dict[str, Any]]:
    torch.manual_seed(seed)
    parent = _make_network(metadata, parent_state)
    target = _make_network(metadata, target_state)
    parent.eval()
    target.eval()
    adapter = AbstainingResidualQAdapter(
        parent,
        _adapter_metadata(metadata),
        AdapterConfig(
            hidden_dim=FIXED_RECIPE["adapter_hidden_dim"],
            gate_threshold=FIXED_RECIPE["gate_threshold"],
            residual_scale=FIXED_RECIPE["residual_scale"],
        ),
    )
    parent_hash_before = state_dict_sha256(adapter.parent.state_dict())
    correction_hash_before = state_dict_sha256(adapter.correction.state_dict())
    optimizer = build_residual_optimizer(adapter, learning_rate=learning_rate)
    batches = _stratified_optimizer_batches(
        spans,
        train_indices,
        batch_size=batch_size,
        optimizer_steps=optimizer_steps,
        seed=seed,
    )
    batch_provenance = _validate_optimizer_batch_provenance(spans, batches)
    objective_rows: dict[str, list[float]] = {
        "total_loss": [],
        "gate_loss": [],
        "action_loss": [],
        "td_loss": [],
    }
    for update_index, indices in enumerate(batches):
        adapter.train()
        torch.manual_seed(seed * 100_000 + update_index)
        with torch.no_grad():
            targets = _variable_bootstrap_targets(
                rewards=spans["rewards"][indices],
                bootstrap_discounts=spans["bootstrap_discounts"][indices],
                next_bootstrap=_frozen_next_bootstrap(
                    adapter.parent, target, spans, indices
                ),
            )
        loss, telemetry = residual_training_loss(
            adapter,
            continuous=spans["continuous"][indices].float(),
            card_ids=spans["card_ids"][indices].long(),
            potion_ids=spans["potion_ids"][indices].long(),
            relic_ids=spans["relic_ids"][indices].long(),
            action_masks=spans["action_masks"][indices].bool(),
            executed_actions=spans["actions"][indices].long(),
            changed=spans["anchor_to_executed_action"][indices].bool(),
            smdp_targets=targets,
        )
        optimizer.zero_grad()
        loss.backward()
        if any(parameter.grad is not None for parameter in adapter.parent.parameters()):
            raise RuntimeError("frozen parent received a gradient")
        torch.nn.utils.clip_grad_norm_(adapter.correction.parameters(), max_norm=10.0)
        optimizer.step()
        for name in objective_rows:
            objective_rows[name].append(float(telemetry[name]))

    parent_hash_after = state_dict_sha256(adapter.parent.state_dict())
    finite = all(
        math.isfinite(value)
        for values in objective_rows.values()
        for value in values
    )
    telemetry = {
        "optimizer_update_count": len(batches),
        "batch_provenance": batch_provenance,
        "total_loss": _summary(objective_rows["total_loss"]),
        "gate_loss": _summary(objective_rows["gate_loss"]),
        "changed_action_loss": _summary(objective_rows["action_loss"]),
        "changed_smdp_td_loss": _summary(objective_rows["td_loss"]),
        "all_objective_values_finite": finite,
        "parent_state_dict_sha256_before": parent_hash_before,
        "parent_state_dict_sha256_after": parent_hash_after,
        "parent_immutable": parent_hash_before == parent_hash_after,
        "correction_state_dict_sha256_before": correction_hash_before,
        "correction_state_dict_sha256_after": state_dict_sha256(
            adapter.correction.state_dict()
        ),
    }
    if not finite:
        raise RuntimeError("residual optimizer produced a non-finite objective")
    if not telemetry["parent_immutable"]:
        raise RuntimeError("frozen parent state changed during fitting")
    return adapter, optimizer, telemetry


def _evaluate_residual_partition(
    *,
    adapter: AbstainingResidualQAdapter,
    target: torch.nn.Module,
    spans: Mapping[str, torch.Tensor],
    indices: torch.Tensor,
) -> dict[str, Any]:
    adapter.eval()
    target.eval()
    inputs = _batch(spans, indices)
    rows = torch.arange(indices.numel())
    actions = spans["actions"][indices].long()
    changed = spans["anchor_to_executed_action"][indices].bool()
    with torch.no_grad():
        parent_q = adapter.parent(*inputs)
        candidate_q = adapter(*inputs)
        _, gate_logits, _, _ = adapter.correction_components(*inputs)
        gate_probabilities = torch.sigmoid(gate_logits)
        gate_open = gate_probabilities.ge(adapter.config.gate_threshold)
        targets = _variable_bootstrap_targets(
            rewards=spans["rewards"][indices],
            bootstrap_discounts=spans["bootstrap_discounts"][indices],
            next_bootstrap=_frozen_next_bootstrap(
                adapter.parent, target, spans, indices
            ),
        )
    parent_actions = parent_q.argmax(1)
    candidate_actions = candidate_q.argmax(1)
    provenance = _provenance_action_metrics(
        parent_actions=parent_actions,
        candidate_actions=candidate_actions,
        executed_actions=actions,
        overrides=changed,
    )
    provenance.pop("anchor_labels")

    def gate_metrics(mask: torch.Tensor) -> dict[str, Any]:
        count = int(mask.sum().item())
        if not count:
            return {"gate_open_count": 0, "gate_open_share": None}
        return {
            "gate_open_count": int(gate_open[mask].sum().item()),
            "gate_open_share": float(gate_open[mask].float().mean().item()),
        }

    direct = dict(provenance["direct"])
    direct.update(gate_metrics(~changed))
    changed_metrics = dict(provenance["override"])
    changed_metrics.update(gate_metrics(changed))
    continuous = spans["continuous"][indices].float()
    positive_energy = continuous[:, StateEncoderV2.ENERGY_RATIO_INDEX].gt(0.0)
    parent_end_turn = int(
        (positive_energy & parent_actions.eq(END_TURN_ACTION)).sum().item()
    )
    candidate_end_turn = int(
        (positive_energy & candidate_actions.eq(END_TURN_ACTION)).sum().item()
    )
    return {
        "decision_span_count": int(indices.numel()),
        "source_transition_count": int(
            spans["span_lengths"][indices].sum().item()
        ),
        "parent_smooth_l1": float(
            F.smooth_l1_loss(parent_q[rows, actions], targets).item()
        ),
        "candidate_smooth_l1": float(
            F.smooth_l1_loss(candidate_q[rows, actions], targets).item()
        ),
        "parent_anchor_label_agreement": provenance[
            "parent_anchor_label_agreement"
        ],
        "candidate_anchor_label_agreement": provenance[
            "candidate_anchor_label_agreement"
        ],
        "action_disagreement_count": provenance["action_disagreement_count"],
        "action_disagreement_share": provenance["action_disagreement_share"],
        "gate_open_count": int(gate_open.sum().item()),
        "gate_open_share": float(gate_open.float().mean().item()),
        "gate_probability": _summary(gate_probabilities.tolist()),
        "positive_energy_state_count": int(positive_energy.sum().item()),
        "parent_positive_energy_end_turn_count": parent_end_turn,
        "candidate_positive_energy_end_turn_count": candidate_end_turn,
        "positive_energy_end_turn_count_delta": candidate_end_turn - parent_end_turn,
        "span_lengths": _summary(
            [float(value) for value in spans["span_lengths"][indices].tolist()]
        ),
        "bootstrap_discounts": _summary(
            [
                float(value)
                for value in spans["bootstrap_discounts"][indices].tolist()
            ]
        ),
        "strata": {
            "direct": direct,
            "changed_proposal": changed_metrics,
        },
    }


def _residual_eligibility(
    *,
    validation: Mapping[str, Any],
    training: Mapping[str, Any],
    adapter_round_trip_exact: bool,
    callability_complete: bool,
) -> dict[str, bool]:
    direct = validation["strata"]["direct"]
    changed = validation["strata"]["changed_proposal"]
    changed_uplift = float(changed["candidate_anchor_label_agreement"]) - float(
        changed["parent_anchor_label_agreement"]
    )
    batch = training["batch_provenance"]
    checks = {
        "metrics_finite": all(
            math.isfinite(float(validation[name]))
            for name in (
                "parent_smooth_l1",
                "candidate_smooth_l1",
                "action_disagreement_share",
                "gate_open_share",
            )
        ),
        "optimizer_budget_exact": int(training["optimizer_update_count"])
        == OPTIMIZER_STEPS,
        "objective_values_finite": bool(training["all_objective_values_finite"]),
        "parent_state_immutable": bool(training["parent_immutable"]),
        "adapter_round_trip_exact": bool(adapter_round_trip_exact),
        "callability_complete": bool(callability_complete),
        "optimizer_batches_candidate_callable": int(
            batch["ineligible_sample_count"]
        )
        == 0,
        "every_batch_contains_registered_strata_counts": int(
            batch["minimum_direct_count"]
        )
        == FIXED_RECIPE["batch_direct_count"]
        and int(batch["maximum_direct_count"])
        == FIXED_RECIPE["batch_direct_count"]
        and int(batch["minimum_changed_count"])
        == FIXED_RECIPE["batch_changed_count"]
        and int(batch["maximum_changed_count"])
        == FIXED_RECIPE["batch_changed_count"],
        "validation_smdp_td_improved": float(validation["candidate_smooth_l1"])
        < float(validation["parent_smooth_l1"]),
        "overall_parent_disagreement_at_least_material_floor": float(
            validation["action_disagreement_share"]
        )
        >= FIXED_TECHNICAL_GATES["overall_parent_disagreement_minimum"],
        "direct_parent_disagreement_at_most_ceiling": float(
            direct["action_disagreement_share"]
        )
        <= FIXED_TECHNICAL_GATES["direct_parent_disagreement_maximum"],
        "direct_gate_open_share_at_most_ceiling": float(
            direct["gate_open_share"]
        )
        <= FIXED_TECHNICAL_GATES["direct_gate_open_share_maximum"],
        "changed_gate_open_share_at_least_floor": float(
            changed["gate_open_share"]
        )
        >= FIXED_TECHNICAL_GATES["changed_gate_open_share_minimum"],
        "changed_proposal_executed_label_uplift_at_least_floor": changed_uplift
        >= FIXED_TECHNICAL_GATES[
            "changed_proposal_executed_label_agreement_uplift_minimum"
        ],
        "positive_energy_end_turn_increase_bounded": int(
            validation["positive_energy_end_turn_count_delta"]
        )
        <= FIXED_TECHNICAL_GATES["positive_energy_end_turn_increase_maximum"],
        "validation_strata_nonempty": int(direct["transition_count"]) > 0
        and int(changed["transition_count"]) > 0,
    }
    checks["all_conditions_passed"] = all(checks.values())
    return checks


def _write_started_receipt(
    path: Path,
    *,
    supplement_sha256: str,
    source_commit: str,
    checkpoint_sha256: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "status": "started_no_retry",
        "experiment_id": EXPERIMENT_ID,
        "source_commit": source_commit,
        "runner_binding_supplement_sha256": supplement_sha256,
        "training_checkpoint_sha256": checkpoint_sha256,
    }
    with path.open("xb") as handle:
        handle.write(_canonical_json_bytes(payload))


def _round_trip_exact(
    original: AbstainingResidualQAdapter,
    restored: AbstainingResidualQAdapter,
    spans: Mapping[str, torch.Tensor],
    indices: torch.Tensor,
) -> bool:
    if state_dict_sha256(original.correction.state_dict()) != state_dict_sha256(
        restored.correction.state_dict()
    ):
        return False
    original.eval()
    restored.eval()
    with torch.no_grad():
        return torch.equal(original(*_batch(spans, indices)), restored(*_batch(spans, indices)))


def _require_round_trip_exact(exact: bool) -> None:
    if not exact:
        raise RuntimeError("residual adapter serialization round trip differs")


def run(args: argparse.Namespace) -> dict[str, Any]:
    runner_path = Path(__file__).resolve()
    _fixed_input_arguments(args)
    if Path(sys.executable).resolve() != EXPECTED_INTERPRETER.resolve():
        raise ValueError("residual fit must use the registered Windows interpreter")
    if not bool(sys.flags.isolated):
        raise ValueError("residual fit must run in isolated -I mode")
    source_files = _source_snapshot_hashes(args.source_commit)
    registration_path = args.registration.resolve()
    collection_report_path = args.collection_report.resolve()
    checkpoint_path = args.training_checkpoint.resolve()
    supplement_path = args.runner_binding_supplement.resolve()
    output_dir = args.output_dir.resolve()
    attempt_receipt = args.attempt_receipt.resolve()
    supplied = (
        (registration_path, args.registration_sha256, "registration"),
        (collection_report_path, args.collection_report_sha256, "collection report"),
        (checkpoint_path, args.expected_checkpoint_sha256, "training checkpoint"),
        (supplement_path, args.runner_binding_supplement_sha256, "runner binding"),
    )
    for path, expected_hash, label in supplied:
        if _sha256(path) != expected_hash:
            raise ValueError(f"{label} hash mismatch")
    if args.experiment_id != EXPERIMENT_ID:
        raise ValueError("experiment id changed")
    validate_residual_training_source(args.expected_checkpoint_sha256)
    registration = json.loads(registration_path.read_text(encoding="utf-8"))
    _validate_registration(registration)
    collection_report = json.loads(
        collection_report_path.read_text(encoding="utf-8")
    )
    _validate_collection_report(
        collection_report,
        expected_registration_sha256=args.registration_sha256,
        expected_checkpoint_sha256=args.expected_checkpoint_sha256,
        expected_transition_count=args.expected_transition_count,
    )
    binding = json.loads(supplement_path.read_text(encoding="utf-8"))
    staging_dir = _validate_runner_binding(
        binding,
        source_commit=args.source_commit,
        runner_path=runner_path,
        registration_path=registration_path,
        registration_sha256=args.registration_sha256,
        collection_report_path=collection_report_path,
        collection_report_sha256=args.collection_report_sha256,
        checkpoint_path=checkpoint_path,
        checkpoint_sha256=args.expected_checkpoint_sha256,
        output_dir=output_dir,
        attempt_receipt=attempt_receipt,
        source_files=source_files,
        command_template=_command_template(args, runner_path=runner_path),
    )
    for path, label in (
        (output_dir, "output directory"),
        (staging_dir, "staging directory"),
        (attempt_receipt, "attempt receipt"),
    ):
        if path.exists():
            raise ValueError(f"{label} already exists: {path}")

    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    metadata, replay, provenance_counts = _validate_callability_checkpoint(
        checkpoint,
        expected_transition_count=args.expected_transition_count,
    )
    parent_state = checkpoint["online_network_state_dict"]
    target_state = checkpoint["target_network_state_dict"]
    parent_hash = state_dict_sha256(parent_state)
    if parent_hash != state_dict_sha256(target_state):
        raise ValueError("training checkpoint parent and target differ")
    if parent_hash != collection_report["checkpoint"][
        "online_state_dict_sha256"
    ]:
        raise ValueError("collection report parent state identity changed")
    spans, span_telemetry = build_candidate_decision_spans(replay, gamma=GAMMA)
    split = _split_candidate_spans(
        spans,
        validation_fraction=VALIDATION_FRACTION,
        seed=SPLIT_SEED,
    )
    train_indices = split["train_indices"]
    validation_indices = split["validation_indices"]
    for label, indices in (
        ("training", train_indices),
        ("validation", validation_indices),
    ):
        changed = spans["anchor_to_executed_action"][indices].bool()
        if not bool(changed.any()) or not bool((~changed).any()):
            raise ValueError(f"{label} candidate strata are empty")
    _stratified_optimizer_batches(
        spans,
        train_indices,
        batch_size=BATCH_SIZE,
        optimizer_steps=OPTIMIZER_STEPS,
        seed=TRAINING_SEED,
    )

    _write_started_receipt(
        attempt_receipt,
        supplement_sha256=args.runner_binding_supplement_sha256,
        source_commit=args.source_commit,
        checkpoint_sha256=args.expected_checkpoint_sha256,
    )
    adapter, optimizer, training = _fit_residual_candidate(
        metadata=metadata,
        parent_state=parent_state,
        target_state=target_state,
        spans=spans,
        train_indices=train_indices,
    )
    target = _make_network(metadata, target_state)
    train_evaluation = _evaluate_residual_partition(
        adapter=adapter,
        target=target,
        spans=spans,
        indices=train_indices,
    )
    validation = _evaluate_residual_partition(
        adapter=adapter,
        target=target,
        spans=spans,
        indices=validation_indices,
    )

    staging_dir.mkdir(parents=True, exist_ok=False)
    try:
        artifact = build_adapter_artifact(
            adapter,
            optimizer,
            parent_checkpoint_sha256=args.expected_checkpoint_sha256,
            seed=TRAINING_SEED,
            update_count=OPTIMIZER_STEPS,
            telemetry={
                "experiment_id": EXPERIMENT_ID,
                "source_commit": args.source_commit,
                "training": training,
            },
        )
        artifact_path = staging_dir / "abstaining_residual_development_adapter.pth"
        _atomic_torch_save(artifact, artifact_path)
        loaded_artifact = torch.load(
            artifact_path, map_location="cpu", weights_only=True
        )
        restored, _ = load_adapter_artifact(
            _make_network(metadata, parent_state),
            _adapter_metadata(metadata),
            loaded_artifact,
            expected_parent_checkpoint_sha256=args.expected_checkpoint_sha256,
        )
        round_trip_exact = _round_trip_exact(
            adapter,
            restored,
            spans,
            torch.cat((train_indices, validation_indices)),
        )
        _require_round_trip_exact(round_trip_exact)
        eligibility = _residual_eligibility(
            validation=validation,
            training=training,
            adapter_round_trip_exact=round_trip_exact,
            callability_complete=(
                span_telemetry["source_row_reconciliation_count"]
                == span_telemetry["source_transition_count"]
            ),
        )
        report = {
            "schema_version": 1,
            "experiment_id": EXPERIMENT_ID,
            "source_commit": args.source_commit,
            "decision": (
                "eligible_for_separately_registered_fresh_holdout_only"
                if eligibility["all_conditions_passed"]
                else "fixed_residual_fit_failed_cohort_closed"
            ),
            "bindings": {
                "registration": {
                    "path": str(registration_path),
                    "sha256": args.registration_sha256,
                },
                "collection_report": {
                    "path": str(collection_report_path),
                    "sha256": args.collection_report_sha256,
                },
                "training_checkpoint": {
                    "path": str(checkpoint_path),
                    "sha256": args.expected_checkpoint_sha256,
                    "transition_count": args.expected_transition_count,
                    "parent_state_dict_sha256": parent_hash,
                },
                "runner_binding_supplement": {
                    "path": str(supplement_path),
                    "sha256": args.runner_binding_supplement_sha256,
                },
                "attempt_receipt": str(attempt_receipt),
            },
            "recipe": FIXED_RECIPE,
            "technical_gates": FIXED_TECHNICAL_GATES,
            "source_provenance": provenance_counts,
            "span_telemetry": span_telemetry,
            "partition": {
                "unit": "terminal_delimited_combat_group",
                "combat_group_count": split["combat_group_count"],
                "training_group_indices": split["train_group_indices"].tolist(),
                "validation_group_indices": split[
                    "validation_group_indices"
                ].tolist(),
                "training_decision_span_count": int(train_indices.numel()),
                "validation_decision_span_count": int(
                    validation_indices.numel()
                ),
            },
            "training": training,
            "train_evaluation": train_evaluation,
            "validation": validation,
            "eligibility": eligibility,
            "adapter": {
                "path": artifact_path.name,
                "sha256": _sha256(artifact_path),
                "size_bytes": artifact_path.stat().st_size,
                "correction_state_dict_sha256": state_dict_sha256(
                    adapter.correction.state_dict()
                ),
                "parent_state_dict_sha256": state_dict_sha256(
                    adapter.parent.state_dict()
                ),
                "round_trip_exact": round_trip_exact,
                "production_compatible": False,
            },
            "authority": RESULT_AUTHORITY,
            "limitations": [
                "This development cohort cannot serve as its own holdout.",
                "A passing result authorizes only a separate fresh-holdout registration.",
                "A failed result closes this corpus without retry or tuning.",
                "Production r16 remains authoritative.",
            ],
        }
        (staging_dir / "report.json").write_bytes(_canonical_json_bytes(report))
        os.replace(staging_dir, output_dir)
        return report
    except Exception:
        shutil.rmtree(staging_dir, ignore_errors=True)
        raise


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fit one source-bound abstaining residual combat RL successor."
    )
    parser.add_argument("--registration", type=Path, required=True)
    parser.add_argument("--registration-sha256", required=True)
    parser.add_argument("--collection-report", type=Path, required=True)
    parser.add_argument("--collection-report-sha256", required=True)
    parser.add_argument("--training-checkpoint", type=Path, required=True)
    parser.add_argument("--expected-checkpoint-sha256", required=True)
    parser.add_argument("--expected-transition-count", type=int, required=True)
    parser.add_argument("--runner-binding-supplement", type=Path, required=True)
    parser.add_argument("--runner-binding-supplement-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--attempt-receipt", type=Path, required=True)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--source-commit", required=True)
    return parser.parse_args()


if __name__ == "__main__":
    run(_parse_args())
