"""Fit one bounded combat RL successor with provenance-stratified gates."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import shutil
import sys
from typing import Mapping

import torch


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from analysis_scripts.combat_rl_provenance_aware_successor import (
    _atomic_torch_save,
    _combat_group_split,
    _evaluate_partition,
    _fit_candidate,
    _indices_sha256,
    _optimizer_state_count,
    _relative_l2,
    _sha256,
    _state_dict_sha256,
    _validate_parity_checkpoint,
)


EXPECTED_INPUT_SHA256 = (
    "606727df27dd82ac825767097b71f07d6aa39ad37e0ea5d5d432e88c9288c28f"
)
EXPECTED_PARENT_STATE_SHA256 = (
    "23491db97fe31cf12052207ea321b4c2ac23a922f2a0916a3dc54d604ee3a720"
)
EXPECTED_TRANSITION_COUNT = 2091
VALIDATION_FRACTION = 0.2
SPLIT_SEED = 2026082805
TRAINING_SEED = 2026082806
LEARNING_RATE = 1e-4
BATCH_SIZE = 128
ANCHOR_WEIGHT = 1.0
OPTIMIZER_STEPS = 64
GAMMA = 0.99
MINIMUM_OVERALL_DISAGREEMENT = 0.05
MAXIMUM_DIRECT_DISAGREEMENT = 0.10
MINIMUM_OVERRIDE_LABEL_AGREEMENT_UPLIFT = 0.10
MAXIMUM_POSITIVE_ENERGY_END_TURN_INCREASE = 2


def _eligibility(
    *,
    validation: Mapping[str, object],
    training: Mapping[str, object],
    candidate_round_trip_exact: bool,
) -> dict[str, bool]:
    direct = validation["strata"]["direct"]
    override = validation["strata"]["override"]
    strata_nonempty = (
        int(direct["transition_count"]) > 0
        and int(override["transition_count"]) > 0
    )
    metric_values = (
        validation["parent_smooth_l1"],
        validation["candidate_smooth_l1"],
        validation["action_disagreement_share"],
        direct["action_disagreement_share"],
        direct["parent_anchor_label_agreement"],
        direct["candidate_anchor_label_agreement"],
        override["action_disagreement_share"],
        override["parent_anchor_label_agreement"],
        override["candidate_anchor_label_agreement"],
    )
    metrics_finite = strata_nonempty and all(
        value is not None and math.isfinite(float(value)) for value in metric_values
    )
    override_uplift = (
        float(override["candidate_anchor_label_agreement"])
        - float(override["parent_anchor_label_agreement"])
        if metrics_finite
        else float("-inf")
    )
    direct_disagreement = (
        float(direct["action_disagreement_share"])
        if metrics_finite
        else float("inf")
    )
    overall_disagreement = (
        float(validation["action_disagreement_share"])
        if metrics_finite
        else float("-inf")
    )

    checks = {
        "metrics_finite": metrics_finite,
        "validation_provenance_strata_nonempty": strata_nonempty,
        "optimizer_budget_exact": int(training["optimizer_update_count"])
        == OPTIMIZER_STEPS,
        "objective_values_finite": bool(training["all_objective_values_finite"]),
        "sampled_executed_action_overrides": float(
            training["sampled_override_count"]["maximum"]
        )
        > 0.0,
        "candidate_round_trip_exact": bool(candidate_round_trip_exact),
        "validation_one_step_td_improved": float(
            validation["candidate_smooth_l1"]
        )
        < float(validation["parent_smooth_l1"]),
        "overall_parent_disagreement_at_least_material_floor": (
            overall_disagreement >= MINIMUM_OVERALL_DISAGREEMENT
        ),
        "direct_parent_disagreement_at_most_ceiling": (
            direct_disagreement <= MAXIMUM_DIRECT_DISAGREEMENT
        ),
        "override_executed_label_agreement_uplift_at_least_floor": (
            override_uplift >= MINIMUM_OVERRIDE_LABEL_AGREEMENT_UPLIFT
        ),
        "positive_energy_end_turn_increase_bounded": int(
            validation["positive_energy_end_turn_count_delta"]
        )
        <= MAXIMUM_POSITIVE_ENERGY_END_TURN_INCREASE,
    }
    checks["all_conditions_passed"] = all(checks.values())
    return checks


def _stratum_counts(replay: Mapping[str, object], indices: torch.Tensor) -> dict[str, int]:
    overrides = replay["anchor_to_executed_action"][indices].bool()
    override_count = int(overrides.sum().item())
    return {
        "direct": int(indices.numel()) - override_count,
        "override": override_count,
    }


def run(args: argparse.Namespace) -> dict:
    checkpoint_path = args.training_checkpoint.resolve()
    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise ValueError(f"output directory already exists: {output_dir}")
    actual_hash = _sha256(checkpoint_path)
    if actual_hash != EXPECTED_INPUT_SHA256:
        raise ValueError(
            f"training checkpoint hash mismatch: {actual_hash} != {EXPECTED_INPUT_SHA256}"
        )
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    metadata, replay, provenance = _validate_parity_checkpoint(
        checkpoint, expected_transition_count=EXPECTED_TRANSITION_COUNT
    )
    optimizer_state_count = _optimizer_state_count(checkpoint)
    if optimizer_state_count != 0:
        raise ValueError("training checkpoint optimizer state must be empty")
    parent_state = checkpoint["online_network_state_dict"]
    target_state = checkpoint["target_network_state_dict"]
    parent_hash = _state_dict_sha256(parent_state)
    target_hash = _state_dict_sha256(target_state)
    if parent_hash != EXPECTED_PARENT_STATE_SHA256 or target_hash != parent_hash:
        raise ValueError("training checkpoint weights do not equal frozen production r16")

    split = _combat_group_split(
        replay["dones"][:EXPECTED_TRANSITION_COUNT],
        validation_fraction=VALIDATION_FRACTION,
        seed=SPLIT_SEED,
    )
    candidate_state, training = _fit_candidate(
        metadata=metadata,
        parent_state=parent_state,
        target_state=target_state,
        replay=replay,
        train_indices=split.train_indices,
        learning_rate=LEARNING_RATE,
        batch_size=BATCH_SIZE,
        anchor_weight=ANCHOR_WEIGHT,
        optimizer_steps=OPTIMIZER_STEPS,
        seed=TRAINING_SEED,
    )
    train_evaluation = _evaluate_partition(
        metadata=metadata,
        parent_state=parent_state,
        target_state=target_state,
        candidate_state=candidate_state,
        replay=replay,
        indices=split.train_indices,
    )
    validation = _evaluate_partition(
        metadata=metadata,
        parent_state=parent_state,
        target_state=target_state,
        candidate_state=candidate_state,
        replay=replay,
        indices=split.validation_indices,
    )

    staging = output_dir.with_name(f".{output_dir.name}.{os.getpid()}.staging")
    if staging.exists():
        raise ValueError(f"staging directory already exists: {staging}")
    staging.mkdir(parents=True)
    try:
        candidate_path = staging / "development_candidate.pth"
        payload = {
            "checkpoint_schema_version": 2,
            "checkpoint_kind": "weights",
            "metadata": dict(metadata),
            "rl_space_version": metadata["rl_space_version"],
            "online_network_state_dict": candidate_state,
            "episode": 0,
            "production_compatible": True,
            "provenance": {
                "construction": "stratified_provenance_full_network_successor",
                "experiment_id": args.experiment_id,
                "source_commit": args.source_commit,
                "training_checkpoint_sha256": actual_hash,
                "split_seed": SPLIT_SEED,
                "training_seed": TRAINING_SEED,
                "optimizer_steps": OPTIMIZER_STEPS,
                "parent_policy_anchor_weight": ANCHOR_WEIGHT,
            },
        }
        _atomic_torch_save(payload, candidate_path)
        loaded = torch.load(candidate_path, map_location="cpu", weights_only=True)
        round_trip_exact = _state_dict_sha256(
            loaded["online_network_state_dict"]
        ) == _state_dict_sha256(candidate_state)
        eligibility = _eligibility(
            validation=validation,
            training=training,
            candidate_round_trip_exact=round_trip_exact,
        )
        override_validation = validation["strata"]["override"]
        report = {
            "schema_version": 1,
            "experiment_id": args.experiment_id,
            "source_commit": args.source_commit,
            "decision": (
                "eligible_for_separate_fresh_holdout_only"
                if eligibility["all_conditions_passed"]
                else "development_candidate_not_eligible_no_same_corpus_tuning"
            ),
            "input": {
                "path": str(checkpoint_path),
                "sha256": actual_hash,
                "transition_count": EXPECTED_TRANSITION_COUNT,
                "optimizer_state_count": optimizer_state_count,
                "online_state_dict_sha256": parent_hash,
                "target_state_dict_sha256": target_hash,
                "online_equals_target": target_hash == parent_hash,
                "online_equals_production_r16": parent_hash
                == EXPECTED_PARENT_STATE_SHA256,
                "provenance": provenance,
            },
            "recipe": {
                "device": "cpu",
                "validation_fraction": VALIDATION_FRACTION,
                "split_seed": SPLIT_SEED,
                "training_seed": TRAINING_SEED,
                "learning_rate": LEARNING_RATE,
                "batch_size": BATCH_SIZE,
                "parent_policy_anchor_weight": ANCHOR_WEIGHT,
                "optimizer_steps": OPTIMIZER_STEPS,
                "gamma": GAMMA,
                "target_network": "frozen_production_r16",
                "parent_anchor": "frozen_production_r16",
                "same_corpus_sweep": False,
            },
            "fixed_gate": {
                "minimum_overall_parent_disagreement": MINIMUM_OVERALL_DISAGREEMENT,
                "maximum_direct_parent_disagreement": MAXIMUM_DIRECT_DISAGREEMENT,
                "minimum_override_executed_label_agreement_uplift": MINIMUM_OVERRIDE_LABEL_AGREEMENT_UPLIFT,
                "maximum_positive_energy_end_turn_count_increase": MAXIMUM_POSITIVE_ENERGY_END_TURN_INCREASE,
            },
            "split": {
                "unit": "terminal_delimited_combat_group",
                "group_count": split.group_count,
                "train_group_count": split.train_group_count,
                "validation_group_count": split.validation_group_count,
                "train_transition_count": int(split.train_indices.numel()),
                "validation_transition_count": int(split.validation_indices.numel()),
                "train_provenance_counts": _stratum_counts(
                    replay, split.train_indices
                ),
                "validation_provenance_counts": _stratum_counts(
                    replay, split.validation_indices
                ),
                "train_indices_sha256": _indices_sha256(split.train_indices),
                "validation_indices_sha256": _indices_sha256(
                    split.validation_indices
                ),
            },
            "training": training,
            "parameter_movement": {
                "whole_model_relative_l2": _relative_l2(
                    candidate_state, parent_state
                ),
                "parent_state_dict_sha256": parent_hash,
                "candidate_state_dict_sha256": _state_dict_sha256(
                    candidate_state
                ),
            },
            "train_evaluation": train_evaluation,
            "validation": validation,
            "stratified_gate_metrics": {
                "overall_parent_disagreement": validation[
                    "action_disagreement_share"
                ],
                "direct_parent_disagreement": validation["strata"]["direct"][
                    "action_disagreement_share"
                ],
                "override_executed_label_agreement_uplift": (
                    float(override_validation["candidate_anchor_label_agreement"])
                    - float(override_validation["parent_anchor_label_agreement"])
                ),
            },
            "eligibility": eligibility,
            "candidate": {
                "path": candidate_path.name,
                "sha256": _sha256(candidate_path),
                "size_bytes": candidate_path.stat().st_size,
                "round_trip_state_exact": round_trip_exact,
                "development_only": True,
                "production_compatible": True,
            },
            "authority": {
                "training": True,
                "fresh_holdout": eligibility["all_conditions_passed"],
                "gameplay": False,
                "qualification": False,
                "promotion": False,
                "production_checkpoint_writing": False,
                "policy_quality": False,
            },
            "limitations": [
                "The validation partition comes from the training cohort and is not an independent policy-quality holdout.",
                "No same-corpus recipe or threshold changes are permitted after publication.",
                "Production r16 remains authoritative unless a separate fresh holdout and later gate pass.",
            ],
            "next_step": (
                "Freeze this candidate hash and register an unused fresh zero-update holdout."
                if eligibility["all_conditions_passed"]
                else "Retain r16 and stop this recipe line without same-corpus tuning."
            ),
        }
        (staging / "report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.replace(staging, output_dir)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training-checkpoint", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--source-commit", required=True)
    return parser


def main() -> int:
    report = run(build_parser().parse_args())
    print(
        json.dumps(
            {
                "decision": report["decision"],
                "candidate": report["candidate"],
                "stratified_gate_metrics": report["stratified_gate_metrics"],
                "eligibility": report["eligibility"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
