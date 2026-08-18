"""Evaluate a frozen combat candidate on an untouched replay checkpoint."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch


REPO_ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_DIR = Path(__file__).resolve().parent
for import_root in (REPO_ROOT, ANALYSIS_DIR):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from combat_rl_dropout_update_ablation import _batch, _make_network  # noqa: E402
from combat_rl_n_step_return_candidate import (  # noqa: E402
    _evaluate_n_step,
    _load,
    _n_step_targets,
    _sha256,
)
from combat_rl_outcome_constrained_pairwise_candidate import (  # noqa: E402
    TD_ONLY_OFF_TARGET_DISAGREEMENT_MAX,
    TD_ONLY_PARENT_AGREEMENT_MIN,
    _relative_l2,
)


def _decision(eligibility: dict) -> str:
    return (
        "eligible_for_bounded_live_gate"
        if eligibility.get("all_conditions_passed") is True
        else "not_eligible_for_live_gate"
    )


def _eligibility(
    metrics: dict,
    baseline: dict,
    *,
    parent_action_agreement_min: float,
    off_target_parent_disagreement_max: float,
    positive_energy_end_turn_count_increase_max: int | None,
    require_one_step_smooth_l1_improvement: bool,
) -> dict:
    checks = {
        "smooth_l1_improved": metrics["smooth_l1"] < baseline["smooth_l1"],
        "parent_action_agreement_passed": metrics["parent_action_agreement"]
        >= parent_action_agreement_min,
        "off_target_parent_disagreement_passed": metrics[
            "off_target_parent_disagreement_share"
        ]
        <= off_target_parent_disagreement_max,
    }
    if require_one_step_smooth_l1_improvement:
        checks["one_step_smooth_l1_improved"] = metrics[
            "one_step_smooth_l1"
        ] < baseline["one_step_smooth_l1"]
    if positive_energy_end_turn_count_increase_max is not None:
        checks["positive_energy_end_turn_count_passed"] = metrics[
            "positive_energy_end_turn_count"
        ] <= (
            baseline["positive_energy_end_turn_count"]
            + positive_energy_end_turn_count_increase_max
        )
    checks["all_conditions_passed"] = all(checks.values())
    return checks


def run(args: argparse.Namespace) -> dict:
    if args.horizon <= 0:
        raise ValueError("Return horizon must be positive")
    if not 0.0 <= args.gamma <= 1.0:
        raise ValueError("Gamma must be within [0, 1]")
    if not 0.0 <= args.parent_action_agreement_min <= 1.0:
        raise ValueError("Parent action agreement threshold must be within [0, 1]")
    if not 0.0 <= args.off_target_parent_disagreement_max <= 1.0:
        raise ValueError("Off-target disagreement threshold must be within [0, 1]")
    if (
        args.positive_energy_end_turn_count_increase_max is not None
        and args.positive_energy_end_turn_count_increase_max < 0
    ):
        raise ValueError("Positive-energy End Turn increase must be non-negative")

    parent_path = args.parent_checkpoint.resolve()
    candidate_path = args.candidate_checkpoint.resolve()
    replay_path = args.replay_checkpoint.resolve()
    parent = torch.load(parent_path, map_location="cpu", weights_only=True)
    candidate = torch.load(candidate_path, map_location="cpu", weights_only=True)
    _, replay, replay_metadata = _load(replay_path)
    if parent["metadata"] != candidate["metadata"]:
        raise ValueError("Parent and candidate metadata differ")
    if parent["metadata"] != replay_metadata:
        raise ValueError("Parent and replay metadata differ")
    if candidate.get("checkpoint_kind") != "weights":
        raise ValueError("Frozen candidate must be a weights checkpoint")

    parent_hash = _sha256(parent_path)
    provenance = candidate.get("provenance", {})
    if provenance.get("parent_checkpoint_sha256") != parent_hash:
        raise ValueError("Candidate provenance does not bind the parent checkpoint")
    if int(provenance.get("horizon", 1)) != args.horizon:
        raise ValueError("Candidate provenance does not bind the requested horizon")
    if abs(float(provenance.get("gamma", args.gamma)) - args.gamma) > 1e-12:
        raise ValueError("Candidate provenance does not bind the requested gamma")

    parent_state = parent["online_network_state_dict"]
    parent_target_state = parent.get("target_network_state_dict", parent_state)
    candidate_state = candidate["online_network_state_dict"]
    parent_online = _make_network(replay_metadata, parent_state)
    parent_target = _make_network(replay_metadata, parent_target_state)
    candidate_online = _make_network(replay_metadata, candidate_state)
    transition_count = int(replay["transition_count"])
    indices = torch.arange(transition_count)
    targets = _n_step_targets(
        parent_online,
        parent_target,
        replay,
        horizon=args.horizon,
        gamma=args.gamma,
    )
    with torch.no_grad():
        parent_actions = parent_online(*_batch(replay, indices)).argmax(dim=1)
    baseline = _evaluate_n_step(
        parent_online,
        parent_target,
        replay,
        parent_actions,
        targets,
    )
    candidate_metrics = _evaluate_n_step(
        candidate_online,
        parent_target,
        replay,
        parent_actions,
        targets,
    )
    eligibility = _eligibility(
        candidate_metrics,
        baseline,
        parent_action_agreement_min=args.parent_action_agreement_min,
        off_target_parent_disagreement_max=(
            args.off_target_parent_disagreement_max
        ),
        positive_energy_end_turn_count_increase_max=(
            args.positive_energy_end_turn_count_increase_max
        ),
        require_one_step_smooth_l1_improvement=(
            args.require_one_step_smooth_l1_improvement
        ),
    )
    result = {
        "schema_version": 1,
        "gate_id": args.gate_id,
        "source_commit": args.source_commit,
        "inputs": {
            "parent_checkpoint": {
                "path": str(parent_path),
                "sha256": parent_hash,
            },
            "candidate_checkpoint": {
                "path": str(candidate_path),
                "sha256": _sha256(candidate_path),
                "provenance": provenance,
            },
            "replay_checkpoint": {
                "path": str(replay_path),
                "sha256": _sha256(replay_path),
                "transition_count": transition_count,
                "source_transition_count": int(
                    replay.get("source_transition_count", transition_count)
                ),
                "truncated": bool(replay.get("truncated", False)),
            },
        },
        "design": {
            "objective": "frozen_candidate_n_step_replay_gate",
            "horizon": args.horizon,
            "gamma": args.gamma,
            "model_fitting": False,
            "checkpoint_writing": False,
            "eligibility_thresholds": {
                "smooth_l1_must_improve": True,
                "one_step_smooth_l1_must_improve": (
                    args.require_one_step_smooth_l1_improvement
                ),
                "parent_action_agreement_min": args.parent_action_agreement_min,
                "off_target_parent_disagreement_max": (
                    args.off_target_parent_disagreement_max
                ),
                "positive_energy_end_turn_count_increase_max": (
                    args.positive_energy_end_turn_count_increase_max
                ),
            },
        },
        "parent_baseline": baseline,
        "candidate": {
            **candidate_metrics,
            "relative_l2_from_parent": _relative_l2(
                candidate_online, parent_state
            ),
        },
        "eligibility": eligibility,
        "decision": _decision(eligibility),
        "authority": "offline fresh-replay confirmation only; bounded live gate requires a separate matched registration",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent-checkpoint", type=Path, required=True)
    parser.add_argument("--candidate-checkpoint", type=Path, required=True)
    parser.add_argument("--replay-checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--gate-id", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--horizon", type=int, default=1)
    parser.add_argument("--gamma", type=float, default=0.99)
    parser.add_argument(
        "--parent-action-agreement-min",
        type=float,
        default=TD_ONLY_PARENT_AGREEMENT_MIN,
    )
    parser.add_argument(
        "--off-target-parent-disagreement-max",
        type=float,
        default=TD_ONLY_OFF_TARGET_DISAGREEMENT_MAX,
    )
    parser.add_argument(
        "--positive-energy-end-turn-count-increase-max",
        type=int,
        default=None,
    )
    parser.add_argument(
        "--require-one-step-smooth-l1-improvement",
        action="store_true",
    )
    return parser


def main() -> int:
    result = run(build_parser().parse_args())
    print(
        json.dumps(
            {
                "decision": result["decision"],
                "eligibility": result["eligibility"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
