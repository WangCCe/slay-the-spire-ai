"""Audit frozen LightSTS action and Q-margin drift on fresh simulator states."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import uuid
from collections import Counter
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping, Sequence

import numpy as np
import torch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from analysis_scripts.combat_lightspeed_bridge import (  # noqa: E402
    canonical_json_bytes,
    collect_provenance,
    load_native_module,
    sha256_bytes,
    sha256_file,
)
from analysis_scripts.combat_lightspeed_frozen_candidate_comparison import (  # noqa: E402
    CandidateBinding,
    load_candidate,
    validate_candidate_structures,
)
from analysis_scripts.combat_lightspeed_training_smoke import (  # noqa: E402
    EXPECTED_UNREACHABLE_PROFILE_REASONS,
    SmokeConfig,
    collect_transitions,
    create_fresh_trainer,
    parameter_sha256,
    transition_identity_sha256,
    unexpected_initialization_failures,
)
from spirecomm.ai.rl.v2.action_space import (  # noqa: E402
    ACTION_DIM,
    END_TURN_ACTION,
    EVENT_COUNT,
    EVENT_OFFSET,
    MAP_COUNT,
    MAP_OFFSET,
    PLAY_CARD_COUNT,
    PLAY_CARD_OFFSET,
    REST_COUNT,
    REST_OFFSET,
    REWARD_COUNT,
    REWARD_OFFSET,
    SHOP_COUNT,
    SHOP_OFFSET,
    SYSTEM_COUNT,
    SYSTEM_OFFSET,
    USE_POTION_COUNT,
    USE_POTION_OFFSET,
)
from spirecomm.ai.rl.v2.id_mapping import build_id_mapper  # noqa: E402


REPORT_SCHEMA_VERSION = "combat-lightspeed-action-margin-drift-audit-v1"
MANIFEST_SCHEMA_VERSION = "combat-lightspeed-action-margin-drift-manifest-v1"
REPORT_AUTHORITY = {
    "communication_mod": False,
    "formal_rl": False,
    "gameplay": False,
    "live_policy_quality": False,
    "mechanics_equivalence": False,
    "model_fitting": False,
    "production_checkpoint_access": False,
    "promotion": False,
    "qualification": False,
    "simulator_state_audit": True,
    "training": False,
    "transfer": False,
}


def action_family(action_index: int) -> str:
    index = int(action_index)
    ranges = (
        (PLAY_CARD_OFFSET, PLAY_CARD_COUNT, "play_card"),
        (USE_POTION_OFFSET, USE_POTION_COUNT, "use_potion"),
        (REWARD_OFFSET, REWARD_COUNT, "reward"),
        (MAP_OFFSET, MAP_COUNT, "map"),
        (EVENT_OFFSET, EVENT_COUNT, "event"),
        (SHOP_OFFSET, SHOP_COUNT, "shop"),
        (REST_OFFSET, REST_COUNT, "rest"),
        (SYSTEM_OFFSET, SYSTEM_COUNT, "system"),
    )
    if index == END_TURN_ACTION:
        return "end_turn"
    for offset, count, label in ranges:
        if offset <= index < offset + count:
            return label
    raise ValueError(f"action index is outside RL v2 action space: {index}")


def _numeric_summary(values: np.ndarray) -> dict[str, Any]:
    finite = np.asarray(values, dtype=np.float64)
    finite = finite[np.isfinite(finite)]
    if not finite.size:
        return {
            "count": 0,
            "minimum": None,
            "p10": None,
            "p25": None,
            "median": None,
            "mean": None,
            "p75": None,
            "p90": None,
            "maximum": None,
        }
    quantiles = np.quantile(finite, [0.1, 0.25, 0.5, 0.75, 0.9])
    return {
        "count": int(finite.size),
        "minimum": float(np.min(finite)),
        "p10": float(quantiles[0]),
        "p25": float(quantiles[1]),
        "median": float(quantiles[2]),
        "mean": float(np.mean(finite)),
        "p75": float(quantiles[3]),
        "p90": float(quantiles[4]),
        "maximum": float(np.max(finite)),
    }


def _disagreement_group(disagree: np.ndarray) -> dict[str, Any]:
    count = int(disagree.size)
    disagreements = int(np.sum(disagree))
    return {
        "transition_count": count,
        "action_disagreement_count": disagreements,
        "action_disagreement_rate": disagreements / count if count else 0.0,
    }


def summarize_candidate_drift(
    parent_q: np.ndarray,
    candidate_q: np.ndarray,
    action_masks: np.ndarray,
    *,
    battle_indices: np.ndarray,
) -> dict[str, Any]:
    parent = np.asarray(parent_q, dtype=np.float64)
    candidate = np.asarray(candidate_q, dtype=np.float64)
    masks = np.asarray(action_masks, dtype=bool)
    battles = np.asarray(battle_indices, dtype=np.int64)
    if parent.shape != candidate.shape or parent.shape != masks.shape:
        raise ValueError("Q-value and action-mask shapes must match")
    if parent.ndim != 2 or parent.shape[1] != ACTION_DIM:
        raise ValueError("Q-value arrays must use the RL v2 action dimension")
    if battles.shape != (parent.shape[0],):
        raise ValueError("battle-index vector does not match Q-value rows")
    if not parent.shape[0] or np.any(np.sum(masks, axis=1) == 0):
        raise ValueError("every audited state must have at least one legal action")
    if not np.all(np.isfinite(parent[masks])) or not np.all(
        np.isfinite(candidate[masks])
    ):
        raise ValueError("valid-action Q values must be finite")

    masked_parent = np.where(masks, parent, -np.inf)
    masked_candidate = np.where(masks, candidate, -np.inf)
    parent_actions = np.argmax(masked_parent, axis=1)
    candidate_actions = np.argmax(masked_candidate, axis=1)
    disagree = parent_actions != candidate_actions
    row_indices = np.arange(parent.shape[0])
    sorted_parent = np.sort(masked_parent, axis=1)
    parent_margin = sorted_parent[:, -1] - sorted_parent[:, -2]
    parent_selected_q_delta = (
        masked_candidate[row_indices, parent_actions]
        - masked_parent[row_indices, parent_actions]
    )
    candidate_advantage_over_parent_action = (
        masked_candidate[row_indices, candidate_actions]
        - masked_candidate[row_indices, parent_actions]
    )
    family_flips = Counter(
        f"{action_family(left)}->{action_family(right)}"
        for left, right, changed in zip(
            parent_actions,
            candidate_actions,
            disagree,
            strict=True,
        )
        if changed
    )
    parent_families = np.asarray([action_family(value) for value in parent_actions])
    candidate_families = np.asarray(
        [action_family(value) for value in candidate_actions]
    )
    by_battle = {
        str(index): _disagreement_group(disagree[battles == index])
        for index in sorted(set(int(value) for value in battles))
    }
    by_parent_family = {
        family: _disagreement_group(disagree[parent_families == family])
        for family in sorted(set(parent_families.tolist()))
    }
    return {
        **_disagreement_group(disagree),
        "parent_action_family_counts": dict(
            sorted(Counter(parent_families.tolist()).items())
        ),
        "candidate_action_family_counts": dict(
            sorted(Counter(candidate_families.tolist()).items())
        ),
        "family_flip_counts": dict(sorted(family_flips.items())),
        "by_battle_index": by_battle,
        "by_parent_action_family": by_parent_family,
        "parent_margin": _numeric_summary(parent_margin),
        "parent_margin_when_agreeing": _numeric_summary(parent_margin[~disagree]),
        "parent_margin_when_disagreeing": _numeric_summary(parent_margin[disagree]),
        "parent_selected_q_delta": _numeric_summary(parent_selected_q_delta),
        "candidate_advantage_over_parent_action_when_disagreeing": _numeric_summary(
            candidate_advantage_over_parent_action[disagree]
        ),
        "valid_action_q_delta": _numeric_summary(candidate[masks] - parent[masks]),
    }


def _network_q_values(trainer, transitions, *, batch_size: int) -> np.ndarray:
    if batch_size <= 0:
        raise ValueError("inference batch size must be positive")
    network = trainer.online_network
    was_training = network.training
    network.eval()
    outputs = []
    try:
        with torch.no_grad():
            for start in range(0, len(transitions), batch_size):
                rows = transitions[start : start + batch_size]
                outputs.append(
                    network(
                        torch.from_numpy(np.stack([row.continuous for row in rows])).float(),
                        torch.from_numpy(np.stack([row.card_ids for row in rows])).long(),
                        torch.from_numpy(np.stack([row.potion_ids for row in rows])).long(),
                        torch.from_numpy(np.stack([row.relic_ids for row in rows])).long(),
                        torch.from_numpy(np.stack([row.action_mask for row in rows])).bool(),
                    )
                    .cpu()
                    .numpy()
                )
    finally:
        network.train(was_training)
    if not outputs:
        raise ValueError("audit transition corpus is empty")
    return np.concatenate(outputs, axis=0)


def run_audit(
    native_module: ModuleType,
    *,
    id_mapper,
    candidates: Sequence[Mapping[str, Any]],
    parent_label: str,
    config: SmokeConfig,
    provenance: Mapping[str, Any],
    inference_batch_size: int,
) -> dict[str, Any]:
    config.validate()
    validate_candidate_structures(candidates)
    by_label = {str(candidate["label"]): candidate for candidate in candidates}
    if len(by_label) != len(candidates) or parent_label not in by_label:
        raise ValueError("audit candidates must have unique labels and include parent")
    transitions, corpus = collect_transitions(
        native_module,
        id_mapper=id_mapper,
        config=config,
    )
    blockers = []
    unexpected = unexpected_initialization_failures(
        corpus["initialization_failure_counts"]
    )
    if unexpected:
        blockers.append("unexpected_initialization_failures")
    if corpus["unsupported_reason_counts"]:
        blockers.append("unsupported_states")
    if not transitions:
        blockers.append("empty_transition_corpus")

    drift = {}
    parent_policy = {}
    if transitions and not blockers:
        trainer = create_fresh_trainer(
            id_mapper,
            seed=0,
            batch_size=2,
            learning_starts=2,
        )
        trainer.online_network.load_state_dict(
            by_label[parent_label]["state_dict"],
            strict=True,
        )
        parent_q = _network_q_values(
            trainer,
            transitions,
            batch_size=inference_batch_size,
        )
        masks = np.stack([row.action_mask for row in transitions])
        battles = np.asarray([row.battle_index for row in transitions], dtype=np.int64)
        parent_actions = np.argmax(np.where(masks, parent_q, -np.inf), axis=1)
        behavior_actions = np.asarray([row.action for row in transitions], dtype=np.int64)
        parent_policy = {
            "behavior_action_agreement_count": int(
                np.sum(parent_actions == behavior_actions)
            ),
            "behavior_action_agreement_rate": float(
                np.mean(parent_actions == behavior_actions)
            ),
            "selected_action_family_counts": dict(
                sorted(Counter(action_family(value) for value in parent_actions).items())
            ),
        }
        for label, candidate in by_label.items():
            if label == parent_label:
                continue
            trainer.online_network.load_state_dict(candidate["state_dict"], strict=True)
            candidate_q = _network_q_values(
                trainer,
                transitions,
                batch_size=inference_batch_size,
            )
            drift[label] = summarize_candidate_drift(
                parent_q,
                candidate_q,
                masks,
                battle_indices=battles,
            )

    candidate_records = []
    for candidate in candidates:
        candidate_records.append(
            {
                key: candidate[key]
                for key in (
                    "label",
                    "path",
                    "sha256",
                    "size_bytes",
                    "checkpoint_kind",
                    "checkpoint_schema_version",
                    "production_compatible",
                    "source_type",
                    "source_binding",
                )
            }
            | {"parameter_sha256": parameter_sha256(candidate["state_dict"])}
        )
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "authority": dict(REPORT_AUTHORITY),
        "config": {
            "seeds": list(config.train_seeds),
            "battle_indices": list(config.battle_indices),
            "ascension": config.ascension,
            "max_decisions_per_seed": config.max_decisions_per_seed,
            "max_actions_per_turn": config.max_actions_per_turn,
            "behavior_seed": config.behavior_seed,
            "complete_trajectories_only": config.complete_trajectories_only,
            "profile_count": len(config.profiles(config.train_seeds)),
            "inference_batch_size": inference_batch_size,
        },
        "provenance": dict(provenance),
        "parent_label": parent_label,
        "candidates": candidate_records,
        "corpus": corpus,
        "transition_identity_sha256": transition_identity_sha256(transitions),
        "parent_policy": parent_policy,
        "candidate_drift": drift,
        "blockers": blockers,
        "verdict": "action_margin_drift_ready" if not blockers else "action_margin_drift_not_ready",
        "interpretation_authority": {
            "action_drift": not blockers,
            "policy_quality": False,
            "training_objective_selection": False,
        },
    }


def _summary_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# Combat LightSTS action-margin drift audit",
        "",
        f"- Verdict: `{report['verdict']}`",
        f"- Transitions: `{report['corpus']['accepted_transition_count']}`",
        f"- Parent: `{report['parent_label']}`",
        f"- Blockers: `{json.dumps(report['blockers'], sort_keys=True)}`",
        "",
        "| Candidate | Disagreement rate | Disagreements | Parent margin on flips |",
        "|---|---:|---:|---:|",
    ]
    for label, drift in report["candidate_drift"].items():
        lines.append(
            f"| {label} | {drift['action_disagreement_rate']:.6f} | "
            f"{drift['action_disagreement_count']} | "
            f"{drift['parent_margin_when_disagreeing']['mean']:.6f} |"
        )
    lines.extend(
        (
            "",
            "This source-only audit authorizes action/Q-margin diagnosis only. It grants no training, gameplay, transfer, qualification, promotion, mechanics-equivalence, or live policy-quality authority.",
            "",
        )
    )
    return "\n".join(lines)


def publish_audit(output_dir: Path, report: Mapping[str, Any]) -> dict[str, Any]:
    target = output_dir.resolve()
    if target.exists():
        raise FileExistsError(f"audit output already exists: {target}")
    staging = target.with_name(f".{target.name}.{uuid.uuid4().hex}.staging")
    created = False
    try:
        staging.mkdir(parents=True, exist_ok=False)
        created = True
        report_bytes = canonical_json_bytes(report) + b"\n"
        summary_bytes = _summary_markdown(report).encode("utf-8")
        (staging / "report.json").write_bytes(report_bytes)
        (staging / "summary.md").write_bytes(summary_bytes)
        artifacts = {
            name: {
                "sha256": sha256_file(staging / name),
                "size_bytes": (staging / name).stat().st_size,
            }
            for name in ("report.json", "summary.md")
        }
        manifest = {
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "artifacts": artifacts,
        }
        (staging / "manifest.json").write_bytes(
            canonical_json_bytes(manifest) + b"\n"
        )
        staging.rename(target)
        created = False
    except Exception:
        if created and staging.exists():
            shutil.rmtree(staging)
        raise
    return manifest


def _parse_integer_sequence(value: str) -> tuple[int, ...]:
    text = value.strip()
    if ".." in text:
        left, right = (int(part) for part in text.split("..", 1))
        if right < left:
            raise argparse.ArgumentTypeError("range end must not precede start")
        return tuple(range(left, right + 1))
    return tuple(int(part.strip()) for part in text.split(",") if part.strip())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--simulator-repo", required=True, type=Path)
    parser.add_argument("--module", required=True, type=Path)
    parser.add_argument("--dll-dir", action="append", default=[], type=Path)
    parser.add_argument("--items-json", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--candidate", action="append", nargs=3, required=True)
    parser.add_argument("--parent-label", required=True)
    parser.add_argument("--seeds", required=True, type=_parse_integer_sequence)
    parser.add_argument("--battle-indices", default="0,3,6,9", type=_parse_integer_sequence)
    parser.add_argument("--ascension", default=0, type=int)
    parser.add_argument("--max-decisions-per-seed", default=100, type=int)
    parser.add_argument("--max-actions-per-turn", default=8, type=int)
    parser.add_argument("--behavior-seed", default=2026081980, type=int)
    parser.add_argument("--inference-batch-size", default=512, type=int)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    candidates = [
        load_candidate(CandidateBinding(label, Path(path), sha256.lower()))
        for label, path, sha256 in args.candidate
    ]
    native_module = load_native_module(args.module, dll_directories=args.dll_dir)
    provenance = collect_provenance(
        repo_root=args.repo_root,
        simulator_repo=args.simulator_repo,
        module_path=args.module,
        native_module=native_module,
    )
    provenance["audit_script_sha256"] = sha256_file(Path(__file__))
    sentinel_seed = max(args.seeds) + 1
    config = SmokeConfig(
        train_seeds=args.seeds,
        evaluation_seeds=(sentinel_seed,),
        battle_indices=args.battle_indices,
        ascension=args.ascension,
        max_decisions_per_seed=args.max_decisions_per_seed,
        max_actions_per_turn=args.max_actions_per_turn,
        behavior_seed=args.behavior_seed,
        network_seed=0,
        batch_size=128,
        optimizer_steps=1,
        complete_trajectories_only=True,
    )
    report = run_audit(
        native_module,
        id_mapper=build_id_mapper(args.items_json),
        candidates=candidates,
        parent_label=args.parent_label,
        config=config,
        provenance=provenance,
        inference_batch_size=args.inference_batch_size,
    )
    publish_audit(args.output_dir, report)
    print(json.dumps({"output_dir": str(args.output_dir.resolve()), "verdict": report["verdict"]}))
    return 0 if report["verdict"] == "action_margin_drift_ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
