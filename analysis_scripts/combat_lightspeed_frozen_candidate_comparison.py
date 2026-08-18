"""Compare frozen simulator-only combat candidates on matched LightSTS profiles."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping, Sequence

import numpy as np
import torch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from analysis_scripts.combat_lightspeed_bridge import (  # noqa: E402
    SOURCE_TYPE,
    canonical_json_bytes,
    collect_provenance,
    load_native_module,
    sha256_bytes,
    sha256_file,
)
from analysis_scripts.combat_lightspeed_training_smoke import (  # noqa: E402
    EXPECTED_UNREACHABLE_PROFILE_REASONS,
    create_fresh_trainer,
    evaluate_policy,
    initialization_failure_reason,
    paired_evaluation,
)
from spirecomm.ai.rl.checkpoint_io import load_torch_checkpoint  # noqa: E402
from spirecomm.ai.rl.v2.id_mapping import IdMapper, build_id_mapper  # noqa: E402


REPORT_SCHEMA_VERSION = "combat-lightspeed-frozen-candidate-comparison-v1"
CHECKPOINT_KIND = "simulator_training_smoke"
REPORT_AUTHORITY = {
    "communication_mod": False,
    "formal_rl": False,
    "gameplay": False,
    "live_policy_quality": False,
    "mechanics_equivalence": False,
    "model_fitting": False,
    "ope": False,
    "production_checkpoint_access": False,
    "promotion": False,
    "qualification": False,
    "simulator_evaluation": True,
    "training": False,
    "transfer": False,
}
_LABEL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


class ComparisonBlocked(RuntimeError):
    """The frozen comparison cannot produce a trustworthy ranking."""

    def __init__(self, reason: str, detail: object | None = None):
        self.reason = reason
        self.detail = detail
        message = reason if detail is None else f"{reason}: {detail}"
        super().__init__(message)


@dataclass(frozen=True)
class CandidateBinding:
    label: str
    path: Path
    sha256: str

    def validate(self) -> None:
        if not _LABEL_PATTERN.fullmatch(self.label):
            raise ComparisonBlocked("candidate_label_invalid", self.label)
        if not re.fullmatch(r"[0-9a-f]{64}", self.sha256):
            raise ComparisonBlocked("candidate_sha256_invalid", self.label)

    def record(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "path": self.path.resolve().as_posix(),
            "sha256": self.sha256,
        }


@dataclass(frozen=True)
class ComparisonConfig:
    seeds: tuple[int, ...]
    battle_indices: tuple[int, ...]
    ascension: int = 0
    max_decisions_per_seed: int = 100
    max_actions_per_turn: int = 8

    def validate(self) -> None:
        if not self.seeds or len(set(self.seeds)) != len(self.seeds):
            raise ComparisonBlocked("comparison_seeds_invalid")
        if any(seed < 0 for seed in self.seeds):
            raise ComparisonBlocked("comparison_seed_negative")
        if not self.battle_indices or len(set(self.battle_indices)) != len(
            self.battle_indices
        ):
            raise ComparisonBlocked("comparison_battle_indices_invalid")
        if any(not 0 <= value <= 63 for value in self.battle_indices):
            raise ComparisonBlocked("comparison_battle_index_out_of_range")
        if not 0 <= self.ascension <= 20:
            raise ComparisonBlocked("comparison_ascension_out_of_range")
        if self.max_decisions_per_seed <= 0 or self.max_actions_per_turn <= 0:
            raise ComparisonBlocked("comparison_bounds_invalid")

    def profiles(self, seeds: Sequence[int]) -> tuple[tuple[int, int], ...]:
        return tuple(
            (int(seed), int(battle_index))
            for seed in seeds
            for battle_index in self.battle_indices
        )

    def record(self) -> dict[str, Any]:
        return {
            "seeds": list(self.seeds),
            "battle_indices": list(self.battle_indices),
            "ascension": self.ascension,
            "max_decisions_per_seed": self.max_decisions_per_seed,
            "max_actions_per_turn": self.max_actions_per_turn,
            "profile_count": len(self.profiles(self.seeds)),
        }


def _state_structure(state_dict: Mapping[str, Any]) -> tuple[tuple[str, tuple[int, ...], str], ...]:
    structure = []
    for key in sorted(state_dict):
        tensor = state_dict[key]
        if not isinstance(tensor, torch.Tensor):
            raise ComparisonBlocked("candidate_state_value_invalid", key)
        structure.append((str(key), tuple(int(value) for value in tensor.shape), str(tensor.dtype)))
    if not structure:
        raise ComparisonBlocked("candidate_state_dict_empty")
    return tuple(structure)


def load_candidate(binding: CandidateBinding) -> dict[str, Any]:
    binding.validate()
    path = binding.path.resolve()
    if not path.is_file():
        raise ComparisonBlocked("candidate_checkpoint_missing", binding.label)
    actual_sha256 = sha256_file(path)
    if actual_sha256 != binding.sha256:
        raise ComparisonBlocked(
            "candidate_checkpoint_hash_mismatch",
            {"label": binding.label, "actual": actual_sha256},
        )
    checkpoint = load_torch_checkpoint(path, map_location="cpu")
    if checkpoint.get("checkpoint_kind") != CHECKPOINT_KIND:
        raise ComparisonBlocked("candidate_checkpoint_kind_invalid", binding.label)
    if checkpoint.get("production_compatible") is not False:
        raise ComparisonBlocked("candidate_production_compatible", binding.label)
    state_dict = checkpoint.get("online_network_state_dict")
    if not isinstance(state_dict, Mapping):
        raise ComparisonBlocked("candidate_state_dict_missing", binding.label)
    metadata = checkpoint.get("metadata")
    if not isinstance(metadata, Mapping) or not isinstance(
        metadata.get("source_binding"), Mapping
    ):
        raise ComparisonBlocked("candidate_source_binding_missing", binding.label)
    state = dict(state_dict)
    structure = _state_structure(state)
    return {
        **binding.record(),
        "checkpoint_kind": CHECKPOINT_KIND,
        "checkpoint_schema_version": checkpoint.get("checkpoint_schema_version"),
        "production_compatible": False,
        "size_bytes": path.stat().st_size,
        "source_type": checkpoint.get("source_type"),
        "source_binding": dict(metadata["source_binding"]),
        "structure": structure,
        "state_dict": state,
    }


def validate_candidate_structures(candidates: Sequence[Mapping[str, Any]]) -> None:
    if len(candidates) < 2:
        raise ComparisonBlocked("candidate_count_insufficient")
    labels = [str(candidate["label"]) for candidate in candidates]
    if len(set(labels)) != len(labels):
        raise ComparisonBlocked("candidate_label_duplicate")
    expected = _state_structure(candidates[0]["state_dict"])
    for candidate in candidates[1:]:
        actual = _state_structure(candidate["state_dict"])
        if actual != expected:
            raise ComparisonBlocked("candidate_structure_mismatch", candidate["label"])


def _row_initialization(row: Mapping[str, Any]) -> tuple[str, str]:
    if row.get("outcome") != "initialization_failure":
        return "reachable", ""
    reason = initialization_failure_reason(
        row.get("initialization_failure_reason") or row.get("unsupported_reason")
    )
    return "unreachable", reason


def validate_matched_initialization(evaluations: Mapping[str, Mapping[str, Any]]) -> None:
    if len(evaluations) < 2:
        raise ComparisonBlocked("candidate_count_insufficient")
    reference_label = next(iter(evaluations))
    reference_rows = {
        (int(row["seed"]), int(row["battle_index"])): row
        for row in evaluations[reference_label]["rows"]
    }
    for label, evaluation in evaluations.items():
        rows = {
            (int(row["seed"]), int(row["battle_index"])): row
            for row in evaluation["rows"]
        }
        if set(rows) != set(reference_rows):
            raise ComparisonBlocked("candidate_profile_set_mismatch", label)
        for profile, reference in reference_rows.items():
            candidate = rows[profile]
            if _row_initialization(candidate) != _row_initialization(reference):
                raise ComparisonBlocked(
                    "candidate_initialization_mismatch",
                    {"label": label, "profile": profile},
                )
            if candidate.get("outcome") != "initialization_failure" and (
                canonical_json_bytes(candidate.get("progression") or {})
                != canonical_json_bytes(reference.get("progression") or {})
            ):
                raise ComparisonBlocked(
                    "candidate_progression_mismatch",
                    {"label": label, "profile": profile},
                )


def _mean(rows: Sequence[Mapping[str, Any]], key: str) -> float:
    return float(np.mean([float(row[key]) for row in rows])) if rows else 0.0


def _summarize_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    include_battle_indices: bool,
) -> dict[str, Any]:
    reachable = [row for row in rows if row.get("outcome") != "initialization_failure"]
    unreachable = [row for row in rows if row.get("outcome") == "initialization_failure"]
    unreachable_reasons = Counter(
        initialization_failure_reason(
            row.get("initialization_failure_reason") or row.get("unsupported_reason")
        )
        for row in unreachable
    )
    unsupported_reasons = Counter(
        str(row.get("unsupported_reason"))
        for row in reachable
        if row.get("unsupported_reason")
    )
    encounters = Counter(
        str(dict(row.get("progression") or {}).get("encounter") or "unknown")
        for row in reachable
    )
    result = {
        "profile_count_registered": len(rows),
        "profile_count_reachable": len(reachable),
        "profile_count_unreachable": len(unreachable),
        "unreachable_failure_counts": dict(sorted(unreachable_reasons.items())),
        "player_victory_count": sum(row.get("outcome") == "player_victory" for row in reachable),
        "player_loss_count": sum(row.get("outcome") == "player_loss" for row in reachable),
        "mean_player_hp": _mean(reachable, "player_hp"),
        "mean_reward": _mean(reachable, "reward"),
        "mean_decisions": _mean(reachable, "decisions"),
        "truncated_count": sum(bool(row.get("truncated")) for row in reachable),
        "unsupported_count": sum(unsupported_reasons.values()),
        "unsupported_reason_counts": dict(sorted(unsupported_reasons.items())),
        "card_select_settlement_action_count": sum(
            int(row.get("card_select_settlement_count", 0)) for row in reachable
        ),
        "encounter_counts": dict(sorted(encounters.items())),
    }
    if include_battle_indices:
        result["battle_indices"] = {
            str(index): _summarize_rows(
                [row for row in rows if int(row["battle_index"]) == index],
                include_battle_indices=False,
            )
            for index in sorted({int(row["battle_index"]) for row in rows})
        }
    return result


def summarize_evaluation(evaluation: Mapping[str, Any]) -> dict[str, Any]:
    return _summarize_rows(list(evaluation["rows"]), include_battle_indices=True)


def _summarize_pair_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "profile_count": len(rows),
        "candidate_only_victories": sum(
            row["candidate_outcome"] == "player_victory"
            and row["control_outcome"] != "player_victory"
            for row in rows
        ),
        "control_only_victories": sum(
            row["control_outcome"] == "player_victory"
            and row["candidate_outcome"] != "player_victory"
            for row in rows
        ),
        "mean_player_hp_delta": _mean(rows, "player_hp_delta"),
        "mean_reward_delta": _mean(rows, "reward_delta"),
        "mean_decision_delta": _mean(rows, "decision_delta"),
    }


def summarize_pairwise(pairwise: Mapping[str, Any]) -> dict[str, Any]:
    rows = list(pairwise["rows"])
    return {
        **dict(pairwise["aggregate"]),
        "battle_indices": {
            str(index): _summarize_pair_rows(
                [row for row in rows if int(row["battle_index"]) == index]
            )
            for index in sorted({int(row["battle_index"]) for row in rows})
        },
    }


def rank_candidates(metrics: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    ordered = sorted(
        metrics,
        key=lambda label: (
            -float(metrics[label]["mean_reward"]),
            -int(metrics[label]["player_victory_count"]),
            -float(metrics[label]["mean_player_hp"]),
            label,
        ),
    )
    if not ordered:
        return {"ordered_labels": [], "reward_leader": None, "winner": None, "guardrail_conflicts": []}
    leader = ordered[0]
    conflicts = []
    for other in ordered[1:]:
        if (
            int(metrics[leader]["player_victory_count"])
            < int(metrics[other]["player_victory_count"])
            or float(metrics[leader]["mean_player_hp"])
            < float(metrics[other]["mean_player_hp"])
        ):
            conflicts.append(
                {
                    "reward_leader": leader,
                    "guardrail_candidate": other,
                    "reward_leader_victories": int(metrics[leader]["player_victory_count"]),
                    "other_victories": int(metrics[other]["player_victory_count"]),
                    "reward_leader_mean_player_hp": float(metrics[leader]["mean_player_hp"]),
                    "other_mean_player_hp": float(metrics[other]["mean_player_hp"]),
                }
            )
    return {
        "ordered_labels": ordered,
        "reward_leader": leader,
        "winner": leader if not conflicts else None,
        "guardrail_conflicts": conflicts,
    }


def _candidate_report(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in candidate.items()
        if key not in {"state_dict", "structure"}
    } | {
        "state_structure": [
            {"key": key, "shape": list(shape), "dtype": dtype}
            for key, shape, dtype in candidate["structure"]
        ]
    }


def run_comparison(
    native_module: ModuleType,
    *,
    id_mapper: IdMapper,
    candidates: Sequence[Mapping[str, Any]],
    config: ComparisonConfig,
    provenance: Mapping[str, Any],
) -> dict[str, Any]:
    config.validate()
    validate_candidate_structures(candidates)
    trainer = create_fresh_trainer(
        id_mapper,
        seed=0,
        batch_size=2,
        learning_starts=2,
    )
    evaluations: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        trainer.online_network.load_state_dict(candidate["state_dict"], strict=True)
        evaluations[str(candidate["label"])] = evaluate_policy(
            native_module,
            id_mapper=id_mapper,
            trainer=trainer,
            seeds=config.seeds,
            config=config,
        )
    validate_matched_initialization(evaluations)
    metrics = {
        label: summarize_evaluation(evaluation)
        for label, evaluation in evaluations.items()
    }
    pairwise = {}
    for left, right in combinations((str(candidate["label"]) for candidate in candidates), 2):
        paired = paired_evaluation(evaluations[left], evaluations[right])
        pairwise[f"{left}__to__{right}"] = {
            "control": left,
            "candidate": right,
            **summarize_pairwise(paired),
        }

    blockers = []
    expected_profile_count = len(config.profiles(config.seeds))
    for label, summary in metrics.items():
        if summary["profile_count_registered"] != expected_profile_count:
            blockers.append(f"profile_accounting_failure:{label}")
        unexpected = {
            reason: count
            for reason, count in summary["unreachable_failure_counts"].items()
            if reason not in EXPECTED_UNREACHABLE_PROFILE_REASONS
        }
        if unexpected:
            blockers.append(f"initialization_integrity_failure:{label}")
        if summary["profile_count_reachable"] == 0:
            blockers.append(f"no_reachable_profiles:{label}")
        if summary["unsupported_count"]:
            blockers.append(f"unsupported_states:{label}")
        if summary["truncated_count"]:
            blockers.append(f"decision_bound_truncation:{label}")
    blockers = sorted(set(blockers))
    ranking = {} if blockers else rank_candidates(metrics)
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "source_type": SOURCE_TYPE,
        "authority": dict(REPORT_AUTHORITY),
        "config": config.record(),
        "provenance": dict(provenance),
        "candidates": [_candidate_report(candidate) for candidate in candidates],
        "evaluations": evaluations,
        "metrics": metrics,
        "pairwise": pairwise,
        "ranking": ranking,
        "blockers": blockers,
        "verdict": "comparison_ready" if not blockers else "comparison_not_ready",
        "next_gate": {
            "real_game_evaluation_authorized": False,
            "requirements": [
                "review the frozen candidate ranking and guardrails",
                "register a separate real-game evaluation before any live use",
                "do not load simulator-only checkpoints in production",
            ],
        },
    }


def _render_summary(report: Mapping[str, Any]) -> str:
    metrics = report.get("metrics", {})
    compact_metrics = {
        label: {
            "mean_player_hp": values.get("mean_player_hp"),
            "mean_reward": values.get("mean_reward"),
            "player_victory_count": values.get("player_victory_count"),
            "profile_count_reachable": values.get("profile_count_reachable"),
        }
        for label, values in metrics.items()
    }
    return "\n".join(
        (
            "# Combat LightSTS Frozen Candidate Comparison",
            "",
            f"- Verdict: `{report.get('verdict')}`",
            f"- Ranking: `{json.dumps(report.get('ranking', {}), sort_keys=True)}`",
            f"- Candidate metrics: `{json.dumps(compact_metrics, sort_keys=True)}`",
            f"- Blockers: `{json.dumps(report.get('blockers', []), sort_keys=True)}`",
            "",
            "This source-only comparison grants no gameplay, transfer, qualification,",
            "promotion, mechanics-equivalence, or live policy-quality authority.",
            "",
        )
    )


def _publish(output_dir: Path, report: Mapping[str, Any]) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=False)
    report_bytes = canonical_json_bytes(report) + b"\n"
    summary_bytes = _render_summary(report).encode("utf-8")
    manifest = {
        "schema_version": "combat-lightspeed-frozen-candidate-comparison-manifest-v1",
        "artifacts": {
            "report.json": {
                "sha256": sha256_bytes(report_bytes),
                "size_bytes": len(report_bytes),
            },
            "summary.md": {
                "sha256": sha256_bytes(summary_bytes),
                "size_bytes": len(summary_bytes),
            },
        },
    }
    artifacts = {
        "report.json": report_bytes,
        "summary.md": summary_bytes,
        "manifest.json": canonical_json_bytes(manifest) + b"\n",
    }
    for name, data in artifacts.items():
        temporary = output_dir / f".{name}.tmp"
        temporary.write_bytes(data)
        temporary.replace(output_dir / name)
    return manifest


def _parse_ints(value: str) -> tuple[int, ...]:
    text = value.strip()
    if ".." in text:
        start_text, end_text = text.split("..", 1)
        start = int(start_text)
        end = int(end_text)
        if end < start:
            raise argparse.ArgumentTypeError("range end must not precede start")
        return tuple(range(start, end + 1))
    try:
        return tuple(int(part.strip()) for part in text.split(",") if part.strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError("values must be comma-separated or start..end") from exc


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--simulator-repo", required=True, type=Path)
    parser.add_argument("--module", required=True, type=Path)
    parser.add_argument("--dll-dir", action="append", default=[], type=Path)
    parser.add_argument("--items-json", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--candidate",
        action="append",
        nargs=3,
        required=True,
        metavar=("LABEL", "PATH", "SHA256"),
    )
    parser.add_argument("--seeds", default="0..63", type=_parse_ints)
    parser.add_argument("--battle-indices", default="0,3,6,9", type=_parse_ints)
    parser.add_argument("--ascension", default=0, type=int)
    parser.add_argument("--max-decisions-per-seed", default=100, type=int)
    parser.add_argument("--max-actions-per-turn", default=8, type=int)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    bindings = tuple(
        CandidateBinding(str(label), Path(path), str(digest).lower())
        for label, path, digest in args.candidate
    )
    config = ComparisonConfig(
        seeds=args.seeds,
        battle_indices=args.battle_indices,
        ascension=args.ascension,
        max_decisions_per_seed=args.max_decisions_per_seed,
        max_actions_per_turn=args.max_actions_per_turn,
    )
    try:
        candidates = tuple(load_candidate(binding) for binding in bindings)
        validate_candidate_structures(candidates)
        native_module = load_native_module(
            args.module,
            dll_directories=tuple(args.dll_dir),
        )
        provenance = collect_provenance(
            repo_root=args.repo_root,
            simulator_repo=args.simulator_repo,
            module_path=args.module,
            native_module=native_module,
        )
        provenance.update(
            {
                "comparison_runner_sha256": sha256_file(Path(__file__)),
                "training_runner_sha256": sha256_file(
                    args.repo_root
                    / "analysis_scripts"
                    / "combat_lightspeed_training_smoke.py"
                ),
                "items_json_path": args.items_json.resolve().as_posix(),
                "items_json_sha256": sha256_file(args.items_json),
            }
        )
        report = run_comparison(
            native_module,
            id_mapper=build_id_mapper(args.items_json),
            candidates=candidates,
            config=config,
            provenance=provenance,
        )
    except Exception as exc:
        report = {
            "schema_version": REPORT_SCHEMA_VERSION,
            "source_type": SOURCE_TYPE,
            "authority": dict(REPORT_AUTHORITY),
            "config": config.record(),
            "candidate_bindings": [binding.record() for binding in bindings],
            "provenance": {},
            "metrics": {},
            "pairwise": {},
            "ranking": {},
            "blockers": ["comparison_setup_failure"],
            "failure": {"type": type(exc).__name__, "detail": str(exc)},
            "verdict": "comparison_not_ready",
            "next_gate": {"real_game_evaluation_authorized": False},
        }
    _publish(args.output_dir, report)
    print(json.dumps({"output_dir": str(args.output_dir), "verdict": report["verdict"]}))
    return 0 if report["verdict"] == "comparison_ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
