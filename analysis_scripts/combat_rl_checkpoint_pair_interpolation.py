"""Scan and build a bounded interpolation between two combat RL checkpoints."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import torch


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from combat_rl_checkpoint_soup_diagnosis import (  # noqa: E402
    _interpolate_state,
    _relative_l2,
)
from combat_rl_dropout_update_ablation import _batch, _make_network  # noqa: E402
from combat_rl_positive_energy_imitation_ablation import _evaluate  # noqa: E402
from spirecomm.ai.rl.v2.action_space import END_TURN_ACTION  # noqa: E402
from spirecomm.ai.rl.v2.state_encoder import StateEncoderV2  # noqa: E402


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_torch_save(payload: dict, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.tmp")
    try:
        torch.save(payload, temporary)
        os.replace(temporary, output)
    finally:
        if temporary.exists():
            temporary.unlink()


def _state_dict_equal(left: dict, right: dict) -> bool:
    return list(left) == list(right) and all(
        torch.equal(left[name], right[name]) for name in left
    )


def _select_alpha(
    evaluations: dict[str, dict], retained_reduction_fraction: float
) -> tuple[list[float], float | None]:
    parent = evaluations["0.0"]
    candidate = evaluations["1.0"]
    full_reduction = (
        parent["positive_energy_end_turn_share"]
        - candidate["positive_energy_end_turn_share"]
    )
    if full_reduction <= 0.0:
        return [], None

    required_reduction = retained_reduction_fraction * full_reduction
    eligible = []
    for key, result in evaluations.items():
        alpha = float(key)
        if not 0.0 < alpha < 1.0:
            continue
        reduction = (
            parent["positive_energy_end_turn_share"]
            - result["positive_energy_end_turn_share"]
        )
        if (
            reduction >= required_reduction
            and result["parent_action_agreement"]
            > candidate["parent_action_agreement"]
            and result["correction_executed_action_agreement"]
            > parent["correction_executed_action_agreement"]
            and result["smooth_l1"] <= parent["smooth_l1"]
            and result["off_target_parent_disagreement_count"]
            < candidate["off_target_parent_disagreement_count"]
        ):
            eligible.append(alpha)
    return eligible, min(eligible) if eligible else None


def run(args: argparse.Namespace) -> dict:
    parent_path = args.parent_checkpoint.resolve()
    candidate_path = args.candidate_checkpoint.resolve()
    parent = torch.load(parent_path, map_location="cpu", weights_only=True)
    candidate = torch.load(candidate_path, map_location="cpu", weights_only=True)

    if parent["metadata"] != candidate["metadata"]:
        raise ValueError("Parent and candidate metadata differ")
    parent_state = parent["online_network_state_dict"]
    candidate_state = candidate["online_network_state_dict"]
    candidate_target = candidate.get("target_network_state_dict", candidate_state)
    anchor_state = candidate.get("parent_policy_anchor_state_dict")
    if anchor_state is None or not _state_dict_equal(anchor_state, parent_state):
        raise ValueError("Candidate parent anchor does not match parent checkpoint")

    alphas = sorted(set(float(alpha) for alpha in args.alphas))
    if not alphas or alphas[0] != 0.0 or alphas[-1] != 1.0:
        raise ValueError("Alpha scan must include endpoints 0.0 and 1.0")
    if any(alpha < 0.0 or alpha > 1.0 for alpha in alphas):
        raise ValueError("Alphas must be within [0, 1]")

    replay = candidate["replay_buffer_state_dict"]
    transition_count = int(replay["transition_count"])
    indices = torch.arange(transition_count)
    parent_network = _make_network(parent["metadata"], parent_state)
    parent_network.eval()
    with torch.no_grad():
        parent_actions = parent_network(*_batch(replay, indices)).argmax(dim=1)

    positive_energy = (
        replay["continuous"][indices, StateEncoderV2.ENERGY_RATIO_INDEX].float()
        > 0.0
    )
    executed_actions = replay["actions"][indices].long()
    correction_eligible = (
        positive_energy
        & (executed_actions != END_TURN_ACTION)
        & (parent_actions == END_TURN_ACTION)
    )
    off_target = ~correction_eligible

    evaluations = {}
    online_states = {}
    for alpha in alphas:
        online_state = _interpolate_state(parent_state, candidate_state, alpha)
        target_state = _interpolate_state(parent_state, candidate_target, alpha)
        online_states[alpha] = online_state
        online = _make_network(parent["metadata"], online_state)
        target = _make_network(parent["metadata"], target_state)
        result = _evaluate(online, target, replay, indices, parent_actions)
        online.eval()
        with torch.no_grad():
            greedy_actions = online(*_batch(replay, indices)).argmax(dim=1)
        off_target_disagreement = (greedy_actions != parent_actions) & off_target
        result.update(
            {
                "alpha": alpha,
                "relative_l2_from_parent": _relative_l2(
                    online_state, parent_state
                ),
                "off_target_state_count": int(off_target.sum()),
                "off_target_parent_disagreement_count": int(
                    off_target_disagreement.sum()
                ),
                "off_target_parent_disagreement_share": float(
                    off_target_disagreement.sum() / off_target.sum()
                ),
            }
        )
        evaluations[str(alpha)] = result

    eligible_alphas, selected_alpha = _select_alpha(
        evaluations, args.retained_reduction_fraction
    )
    result = {
        "schema_version": 1,
        "source_commit": args.source_commit,
        "analysis_script": {
            "path": str(Path(__file__).resolve()),
            "sha256": _sha256(Path(__file__).resolve()),
        },
        "inputs": {
            "parent_checkpoint": {
                "path": str(parent_path),
                "sha256": _sha256(parent_path),
            },
            "candidate_checkpoint": {
                "path": str(candidate_path),
                "sha256": _sha256(candidate_path),
            },
        },
        "design": {
            "device": "cpu",
            "transition_count": transition_count,
            "positive_energy_state_count": int(positive_energy.sum()),
            "correction_state_count": int(correction_eligible.sum()),
            "alphas": alphas,
            "retained_reduction_fraction": args.retained_reduction_fraction,
            "selection": (
                "minimum intermediate alpha retaining the required EndTurn "
                "reduction, improving parent agreement and off-target drift "
                "over the candidate, preserving positive correction, and not "
                "exceeding parent Smooth-L1"
            ),
        },
        "evaluations": evaluations,
        "eligible_alphas": eligible_alphas,
        "selected_alpha": selected_alpha,
        "authority": "offline diagnostic only; no promotion authority",
    }

    if selected_alpha is not None and args.output_checkpoint is not None:
        payload = {
            "checkpoint_schema_version": 2,
            "checkpoint_kind": "weights",
            "metadata": parent["metadata"],
            "rl_space_version": parent["metadata"]["rl_space_version"],
            "online_network_state_dict": online_states[selected_alpha],
            "episode": 0,
            "provenance": {
                "construction": "linear_parent_candidate_interpolation",
                "alpha": selected_alpha,
                "source_commit": args.source_commit,
                "parent_checkpoint_sha256": result["inputs"]["parent_checkpoint"][
                    "sha256"
                ],
                "candidate_checkpoint_sha256": result["inputs"][
                    "candidate_checkpoint"
                ]["sha256"],
            },
        }
        output = args.output_checkpoint.resolve()
        _atomic_torch_save(payload, output)
        loaded = torch.load(output, map_location="cpu", weights_only=True)
        if not _state_dict_equal(
            loaded["online_network_state_dict"], online_states[selected_alpha]
        ):
            raise ValueError("Written interpolation checkpoint did not round-trip")
        result["selected_checkpoint"] = {
            "path": str(output),
            "sha256": _sha256(output),
            "size_bytes": output.stat().st_size,
            "checkpoint_schema_version": 2,
            "checkpoint_kind": "weights",
        }

    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent-checkpoint", type=Path, required=True)
    parser.add_argument("--candidate-checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-checkpoint", type=Path)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument(
        "--alphas",
        type=float,
        nargs="+",
        default=[index / 10 for index in range(11)],
    )
    parser.add_argument("--retained-reduction-fraction", type=float, default=0.5)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = run(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": str(args.output.resolve()),
                "eligible_alphas": result["eligible_alphas"],
                "selected_alpha": result["selected_alpha"],
                "selected_checkpoint": result.get("selected_checkpoint"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
