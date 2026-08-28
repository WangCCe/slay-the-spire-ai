"""Run the fixed provenance-balanced combat objective ablation."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys
from typing import Mapping, Sequence

import torch


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from analysis_scripts.combat_rl_provenance_aware_successor import (  # noqa: E402
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
from analysis_scripts.combat_rl_stratified_provenance_successor import (  # noqa: E402
    _eligibility,
    _stratum_counts,
)


EXPECTED_REGISTRATION_SHA256 = (
    "5c9a9ec70f7c4dcdcd8908cca2a092ffdc0329960ea9b65fcb978fd3512119f8"
)
EXPECTED_INPUT_SHA256 = (
    "606727df27dd82ac825767097b71f07d6aa39ad37e0ea5d5d432e88c9288c28f"
)
EXPECTED_REFERENCE_REPORT_SHA256 = (
    "b8679c2b95f82563439c3b5e0d3b2fac24ffda8fac06995c3f01765a4212fd9c"
)
EXPECTED_DIRECT_AUDIT_SHA256 = (
    "208f5f0cf900e36636c2123f91700873716190407012c4770b6a14e7d7fbe88b"
)
EXPECTED_PARENT_STATE_SHA256 = (
    "23491db97fe31cf12052207ea321b4c2ac23a922f2a0916a3dc54d604ee3a720"
)
EXPECTED_REFERENCE_CANDIDATE_SHA256 = (
    "8d82e0ee5486daeb963d524a6e34b599716b966976f1406e4220973760df6ccf"
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
ARMS = (
    {
        "label": "balanced_anchor",
        "provenance_balanced_anchor": True,
        "direct_only_top_action_margin_guard": False,
        "top_action_margin_guard_weight": 0.0,
        "top_action_margin_guard_cap": 0.1,
    },
    {
        "label": "balanced_anchor_direct_margin",
        "provenance_balanced_anchor": True,
        "direct_only_top_action_margin_guard": True,
        "top_action_margin_guard_weight": 1.0,
        "top_action_margin_guard_cap": 0.1,
    },
)


def _validate_reference_report(report: Mapping[str, object]) -> None:
    if (
        report.get("decision")
        != "development_candidate_not_eligible_no_same_corpus_tuning"
    ):
        raise ValueError("reference decision is not the registered failed result")
    if report.get("source_commit") != "ef661a471924ad7e55ec5ed35cbfad48c7e62876":
        raise ValueError("reference source commit changed")
    if report.get("input", {}).get("sha256") != EXPECTED_INPUT_SHA256:
        raise ValueError("reference input hash changed")
    if (
        report.get("candidate", {}).get("sha256")
        != EXPECTED_REFERENCE_CANDIDATE_SHA256
    ):
        raise ValueError("reference candidate hash changed")
    if int(report.get("recipe", {}).get("optimizer_steps", -1)) != OPTIMIZER_STEPS:
        raise ValueError("reference optimizer budget changed")


def _validate_registration(registration: Mapping[str, object]) -> None:
    if (
        registration.get("registration_id")
        != "combat-rl-provenance-balanced-objective-ablation-20260828-r1"
    ):
        raise ValueError("registration id changed")
    if tuple(registration.get("arms", ())) != ARMS:
        raise ValueError("registered arm matrix changed")
    recipe = registration.get("common_recipe", {})
    expected_recipe = {
        "device": "cpu",
        "validation_fraction": VALIDATION_FRACTION,
        "split_seed": SPLIT_SEED,
        "training_seed": TRAINING_SEED,
        "learning_rate": LEARNING_RATE,
        "batch_size": BATCH_SIZE,
        "parent_policy_anchor_weight": ANCHOR_WEIGHT,
        "optimizer_updates": OPTIMIZER_STEPS,
        "gamma": GAMMA,
    }
    if any(recipe.get(name) != value for name, value in expected_recipe.items()):
        raise ValueError("registered common recipe changed")
    authority = registration.get("authority", {})
    prohibited = (
        "candidate",
        "fresh_holdout",
        "gameplay",
        "communication_mod",
        "qualification",
        "promotion",
        "policy_quality",
        "production_checkpoint_writing",
    )
    if any(bool(authority.get(name)) for name in prohibited):
        raise ValueError("registration grants prohibited authority")


def _add_batch_stratum_gate(
    checks: Mapping[str, bool], *, training: Mapping[str, object]
) -> dict[str, bool]:
    result = {
        name: bool(value)
        for name, value in checks.items()
        if name != "all_conditions_passed"
    }
    direct_minimum = float(
        training["parent_policy_anchor_direct_count"]["minimum"]
    )
    override_minimum = float(
        training["parent_policy_anchor_override_count"]["minimum"]
    )
    result["every_training_batch_contains_both_provenance_strata"] = (
        direct_minimum > 0.0 and override_minimum > 0.0
    )
    result["all_conditions_passed"] = all(result.values())
    return result


def _select_objective_recipe(
    arm_results: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    passing = [
        arm
        for arm in arm_results
        if bool(arm["eligibility"]["all_conditions_passed"])
    ]
    if not passing:
        return {
            "recommended_recipe": None,
            "passing_arm_count": 0,
            "next_step": "investigate_residual_or_separate_head",
            "authority": "objective_design_only",
        }
    simplicity = {"balanced_anchor": 0, "balanced_anchor_direct_margin": 1}
    selected = min(
        passing,
        key=lambda arm: (
            float(
                arm["stratified_gate_metrics"]["direct_parent_disagreement"]
            ),
            -float(
                arm["stratified_gate_metrics"][
                    "override_executed_label_agreement_uplift"
                ]
            ),
            simplicity[str(arm["label"])],
        ),
    )
    return {
        "recommended_recipe": selected["label"],
        "passing_arm_count": len(passing),
        "next_step": "collect_new_replay_after_freezing_recommended_recipe",
        "authority": "objective_design_only",
    }


def _fit_arm(
    *,
    arm: Mapping[str, object],
    metadata: Mapping[str, object],
    replay: Mapping[str, object],
    parent_state: Mapping[str, torch.Tensor],
    target_state: Mapping[str, torch.Tensor],
    train_indices: torch.Tensor,
    validation_indices: torch.Tensor,
    staging: Path,
    experiment_id: str,
    source_commit: str,
) -> dict:
    candidate_state, training = _fit_candidate(
        metadata=metadata,
        parent_state=parent_state,
        target_state=target_state,
        replay=replay,
        train_indices=train_indices,
        learning_rate=LEARNING_RATE,
        batch_size=BATCH_SIZE,
        anchor_weight=ANCHOR_WEIGHT,
        optimizer_steps=OPTIMIZER_STEPS,
        seed=TRAINING_SEED,
        provenance_balanced_anchor=bool(arm["provenance_balanced_anchor"]),
        top_action_margin_guard_weight=float(
            arm["top_action_margin_guard_weight"]
        ),
        top_action_margin_guard_cap=float(arm["top_action_margin_guard_cap"]),
        direct_only_top_action_margin_guard=bool(
            arm["direct_only_top_action_margin_guard"]
        ),
    )
    train_evaluation = _evaluate_partition(
        metadata=metadata,
        parent_state=parent_state,
        target_state=target_state,
        candidate_state=candidate_state,
        replay=replay,
        indices=train_indices,
    )
    validation = _evaluate_partition(
        metadata=metadata,
        parent_state=parent_state,
        target_state=target_state,
        candidate_state=candidate_state,
        replay=replay,
        indices=validation_indices,
    )
    checkpoint_path = staging / f"{arm['label']}_exploratory_weights.pth"
    payload = {
        "checkpoint_schema_version": 2,
        "checkpoint_kind": "weights",
        "metadata": dict(metadata),
        "rl_space_version": metadata["rl_space_version"],
        "online_network_state_dict": candidate_state,
        "episode": 0,
        "production_compatible": True,
        "objective_ablation_only": True,
        "provenance": {
            "construction": "provenance_balanced_objective_ablation",
            "arm": arm["label"],
            "experiment_id": experiment_id,
            "source_commit": source_commit,
            "training_checkpoint_sha256": EXPECTED_INPUT_SHA256,
            "split_seed": SPLIT_SEED,
            "training_seed": TRAINING_SEED,
            "optimizer_steps": OPTIMIZER_STEPS,
            "no_candidate_authority": True,
        },
    }
    _atomic_torch_save(payload, checkpoint_path)
    loaded = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    round_trip_exact = _state_dict_sha256(
        loaded["online_network_state_dict"]
    ) == _state_dict_sha256(candidate_state)
    checks = _eligibility(
        validation=validation,
        training=training,
        candidate_round_trip_exact=round_trip_exact,
    )
    checks = _add_batch_stratum_gate(checks, training=training)
    override = validation["strata"]["override"]
    gate_metrics = {
        "overall_parent_disagreement": validation["action_disagreement_share"],
        "direct_parent_disagreement": validation["strata"]["direct"][
            "action_disagreement_share"
        ],
        "override_executed_label_agreement_uplift": (
            float(override["candidate_anchor_label_agreement"])
            - float(override["parent_anchor_label_agreement"])
        ),
    }
    return {
        "label": arm["label"],
        "recipe": dict(arm),
        "training": training,
        "parameter_movement": {
            "whole_model_relative_l2": _relative_l2(
                candidate_state, parent_state
            ),
            "parent_state_dict_sha256": _state_dict_sha256(parent_state),
            "exploratory_state_dict_sha256": _state_dict_sha256(candidate_state),
        },
        "train_evaluation": train_evaluation,
        "validation": validation,
        "stratified_gate_metrics": gate_metrics,
        "eligibility": checks,
        "exploratory_weights": {
            "path": checkpoint_path.name,
            "sha256": _sha256(checkpoint_path),
            "size_bytes": checkpoint_path.stat().st_size,
            "round_trip_state_exact": round_trip_exact,
            "objective_ablation_only": True,
            "candidate_authority": False,
        },
    }


def run(args: argparse.Namespace) -> dict:
    registration_path = args.registration.resolve()
    checkpoint_path = args.training_checkpoint.resolve()
    reference_path = args.reference_report.resolve()
    direct_audit_path = args.direct_margin_audit.resolve()
    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise ValueError(f"output directory already exists: {output_dir}")
    bindings = (
        (registration_path, EXPECTED_REGISTRATION_SHA256, "registration"),
        (checkpoint_path, EXPECTED_INPUT_SHA256, "training checkpoint"),
        (reference_path, EXPECTED_REFERENCE_REPORT_SHA256, "reference report"),
        (direct_audit_path, EXPECTED_DIRECT_AUDIT_SHA256, "direct margin audit"),
    )
    for path, expected, label in bindings:
        actual = _sha256(path)
        if actual != expected:
            raise ValueError(f"{label} hash mismatch: {actual} != {expected}")
    registration = json.loads(registration_path.read_text(encoding="utf-8"))
    reference = json.loads(reference_path.read_text(encoding="utf-8"))
    direct_audit = json.loads(direct_audit_path.read_text(encoding="utf-8"))
    _validate_registration(registration)
    _validate_reference_report(reference)
    if (
        direct_audit.get("verdict")
        != "shared_objective_cross_stratum_interference_supported"
    ):
        raise ValueError("direct margin audit verdict changed")

    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    metadata, replay, provenance = _validate_parity_checkpoint(
        checkpoint, expected_transition_count=EXPECTED_TRANSITION_COUNT
    )
    if _optimizer_state_count(checkpoint) != 0:
        raise ValueError("training checkpoint optimizer state must be empty")
    parent_state = checkpoint["online_network_state_dict"]
    target_state = checkpoint["target_network_state_dict"]
    parent_hash = _state_dict_sha256(parent_state)
    if (
        parent_hash != EXPECTED_PARENT_STATE_SHA256
        or _state_dict_sha256(target_state) != parent_hash
    ):
        raise ValueError("training checkpoint is not frozen production r16")
    split = _combat_group_split(
        replay["dones"][:EXPECTED_TRANSITION_COUNT],
        validation_fraction=VALIDATION_FRACTION,
        seed=SPLIT_SEED,
    )

    staging = output_dir.with_name(f".{output_dir.name}.{os.getpid()}.staging")
    if staging.exists():
        raise ValueError(f"staging directory already exists: {staging}")
    staging.mkdir(parents=True)
    try:
        arm_results = [
            _fit_arm(
                arm=arm,
                metadata=metadata,
                replay=replay,
                parent_state=parent_state,
                target_state=target_state,
                train_indices=split.train_indices,
                validation_indices=split.validation_indices,
                staging=staging,
                experiment_id=args.experiment_id,
                source_commit=args.source_commit,
            )
            for arm in ARMS
        ]
        selection = _select_objective_recipe(arm_results)
        report = {
            "schema_version": 1,
            "experiment_id": args.experiment_id,
            "source_commit": args.source_commit,
            "decision": (
                "objective_recipe_recommended_for_new_corpus"
                if selection["recommended_recipe"] is not None
                else "no_objective_recipe_recommended"
            ),
            "bindings": {
                "registration": {
                    "path": str(registration_path),
                    "sha256": EXPECTED_REGISTRATION_SHA256,
                },
                "training_checkpoint": {
                    "path": str(checkpoint_path),
                    "sha256": EXPECTED_INPUT_SHA256,
                    "transition_count": EXPECTED_TRANSITION_COUNT,
                    "parent_state_dict_sha256": parent_hash,
                    "provenance": provenance,
                },
                "global_anchor_reference_report": {
                    "path": str(reference_path),
                    "sha256": EXPECTED_REFERENCE_REPORT_SHA256,
                    "candidate_sha256": EXPECTED_REFERENCE_CANDIDATE_SHA256,
                    "reference_not_refitted": True,
                },
                "direct_margin_audit": {
                    "path": str(direct_audit_path),
                    "sha256": EXPECTED_DIRECT_AUDIT_SHA256,
                },
            },
            "common_recipe": {
                "device": "cpu",
                "validation_fraction": VALIDATION_FRACTION,
                "split_seed": SPLIT_SEED,
                "training_seed": TRAINING_SEED,
                "learning_rate": LEARNING_RATE,
                "batch_size": BATCH_SIZE,
                "parent_policy_anchor_weight": ANCHOR_WEIGHT,
                "optimizer_steps_per_arm": OPTIMIZER_STEPS,
                "gamma": GAMMA,
                "same_corpus_purpose": "objective_design_only",
            },
            "split": {
                "unit": "terminal_delimited_combat_group",
                "group_count": split.group_count,
                "train_group_count": split.train_group_count,
                "validation_group_count": split.validation_group_count,
                "train_transition_count": int(split.train_indices.numel()),
                "validation_transition_count": int(
                    split.validation_indices.numel()
                ),
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
            "reference_metrics": {
                "direct_parent_disagreement": reference[
                    "stratified_gate_metrics"
                ]["direct_parent_disagreement"],
                "override_executed_label_agreement_uplift": reference[
                    "stratified_gate_metrics"
                ]["override_executed_label_agreement_uplift"],
                "validation_one_step_td_improved": reference["eligibility"][
                    "validation_one_step_td_improved"
                ],
            },
            "arms": arm_results,
            "selection": selection,
            "authority": {
                "training": True,
                "model_fitting": True,
                "objective_recipe_recommendation": selection[
                    "recommended_recipe"
                ]
                is not None,
                "candidate": False,
                "fresh_holdout": False,
                "gameplay": False,
                "communication_mod": False,
                "qualification": False,
                "promotion": False,
                "policy_quality": False,
                "production_checkpoint_writing": False,
            },
            "limitations": [
                "The R2 validation split is reused for objective design and grants no candidate or downstream authority.",
                "A recommended recipe must be frozen before collecting a new replay for any final candidate fit.",
                "No additional arms, thresholds, seeds, or update budgets may be introduced under this registration.",
            ],
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
    parser.add_argument("--registration", type=Path, required=True)
    parser.add_argument("--training-checkpoint", type=Path, required=True)
    parser.add_argument("--reference-report", type=Path, required=True)
    parser.add_argument("--direct-margin-audit", type=Path, required=True)
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
                "selection": report["selection"],
                "arms": [
                    {
                        "label": arm["label"],
                        "eligibility": arm["eligibility"],
                        "stratified_gate_metrics": arm[
                            "stratified_gate_metrics"
                        ],
                        "exploratory_weights": arm["exploratory_weights"],
                    }
                    for arm in report["arms"]
                ],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
