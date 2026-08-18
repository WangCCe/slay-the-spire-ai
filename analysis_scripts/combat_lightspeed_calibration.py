"""Run bounded source-only calibration for the combat LightSTS bridge."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from analysis_scripts.combat_lightspeed_bridge import (
    ACTION_DIM,
    CARD_SLOTS,
    CONTINUOUS_DIM,
    MAX_BATTLE_INDEX,
    POTION_SLOTS,
    RELIC_SLOTS,
    SOURCE_TYPE,
    CombatBridgeError,
    NativeCombatEnvironment,
    canonical_json_bytes,
    collect_provenance,
    load_native_module,
    sha256_bytes,
    validate_card_select_settlement,
)
from spirecomm.ai.rl.v2.id_mapping import IdMapper, build_id_mapper


REPORT_SCHEMA_VERSION = "combat-lightspeed-bridge-calibration-v3"
REPORT_AUTHORITY = {
    "evaluation": False,
    "formal_rl": False,
    "gameplay": False,
    "mechanics_equivalence": False,
    "model_fitting": False,
    "model_loading": False,
    "ope": False,
    "policy_quality": False,
    "promotion": False,
    "qualification": False,
    "training": False,
}


@dataclass(frozen=True)
class CalibrationConfig:
    seeds: tuple[int, ...]
    battle_indices: tuple[int, ...] = (0,)
    ascension: int = 0
    max_decisions_per_seed: int = 200
    max_actions_per_turn: int = 8

    def validate(self) -> None:
        if not self.seeds:
            raise ValueError("at least one seed is required")
        if len(set(self.seeds)) != len(self.seeds):
            raise ValueError("calibration seeds must be unique")
        if any(seed < 0 for seed in self.seeds):
            raise ValueError("calibration seeds must be non-negative")
        if not self.battle_indices:
            raise ValueError("at least one battle index is required")
        if len(set(self.battle_indices)) != len(self.battle_indices):
            raise ValueError("calibration battle indices must be unique")
        if any(not 0 <= value <= MAX_BATTLE_INDEX for value in self.battle_indices):
            raise ValueError(f"battle indices must be in 0..{MAX_BATTLE_INDEX}")
        if not 0 <= self.ascension <= 20:
            raise ValueError("ascension must be in 0..20")
        if self.max_decisions_per_seed <= 0:
            raise ValueError("max decisions must be positive")
        if self.max_actions_per_turn <= 0:
            raise ValueError("max actions per turn must be positive")

    def profiles(self) -> tuple[tuple[int, int], ...]:
        return tuple(
            (seed, battle_index)
            for seed in self.seeds
            for battle_index in self.battle_indices
        )


def select_deterministic_action(
    actions: Sequence[Mapping[str, Any]],
    *,
    actions_since_end_turn: int,
    max_actions_per_turn: int,
) -> dict[str, Any]:
    """Choose a stable legal action while bounding zero-cost action chains."""

    available = [dict(action) for action in actions if action.get("available", True)]
    if not available:
        raise CombatBridgeError("no_legal_actions")
    ordered = sorted(available, key=lambda action: int(action["rl_action_index"]))
    end_turn = next((action for action in ordered if action.get("kind") == "end_turn"), None)
    if end_turn is None:
        raise CombatBridgeError("end_turn_missing")
    non_end_turn = [action for action in ordered if action.get("kind") != "end_turn"]
    if actions_since_end_turn >= max_actions_per_turn or not non_end_turn:
        return end_turn
    return non_end_turn[0]


def _environment_record(environment: NativeCombatEnvironment) -> dict[str, Any]:
    return {
        "actions": environment.legal_actions(),
        "snapshot": environment.snapshot(),
        "status": environment.status(),
    }


def _record_failure(
    blockers: list[str],
    seed_row: dict[str, Any],
    blocker: str,
    detail: object,
) -> None:
    blockers.append(blocker)
    seed_row["failure"] = {"blocker": blocker, "detail": str(detail)}


def _range_summary(values: Sequence[int]) -> dict[str, int] | None:
    return None if not values else {"minimum": min(values), "maximum": max(values)}


def run_calibration(
    native_module: ModuleType,
    *,
    id_mapper: IdMapper,
    config: CalibrationConfig,
    provenance: Mapping[str, Any],
) -> dict[str, Any]:
    """Exercise fixed simulator combats without loading a model or game state."""

    config.validate()
    blockers: list[str] = []
    profile_results: list[dict[str, Any]] = []
    initialization_failures: Counter[str] = Counter()
    unsupported_reasons: Counter[str] = Counter()
    terminal_outcomes: Counter[str] = Counter()
    mapping_errors: Counter[str] = Counter()
    available_action_families: Counter[str] = Counter()
    executed_action_families: Counter[str] = Counter()
    supported_state_count = 0
    reset_determinism_checks = 0
    clone_isolation_checks = 0
    successor_determinism_checks = 0
    executed_action_count = 0
    settlement_action_count = 0
    settlement_task_counts: Counter[str] = Counter()
    settlement_transition_count = 0
    decision_bound_count = 0
    reached_battle_indices: Counter[int] = Counter()
    reached_acts: Counter[int] = Counter()
    reached_encounters: Counter[str] = Counter()
    reached_floors: list[int] = []
    reached_deck_sizes: list[int] = []
    reached_relic_counts: list[int] = []
    reached_player_hp: list[int] = []
    stop_cohort = False

    for seed, battle_index in config.profiles():
        profile_row: dict[str, Any] = {
            "seed": seed,
            "battle_index": battle_index,
            "decisions": 0,
            "terminal": False,
            "truncated": False,
            "unsupported_reason": "",
        }
        try:
            environment = NativeCombatEnvironment.reset(
                native_module,
                seed=seed,
                ascension=config.ascension,
                battle_index=battle_index,
            )
            repeated = NativeCombatEnvironment.reset(
                native_module,
                seed=seed,
                ascension=config.ascension,
                battle_index=battle_index,
            )
        except Exception as exc:
            reason = str(exc).split(":", 1)[0] or type(exc).__name__
            initialization_failures[reason] += 1
            profile_row["initialization_failure"] = {
                "reason": reason,
                "detail": str(exc),
            }
            profile_results.append(profile_row)
            continue
        try:
            environment_record = _environment_record(environment)
            repeated_record = _environment_record(repeated)
            progression = dict(environment.snapshot().get("progression") or {})
        except Exception as exc:
            _record_failure(
                blockers,
                profile_row,
                "native_initial_record_failure",
                exc,
            )
            profile_results.append(profile_row)
            break
        if canonical_json_bytes(environment_record) != canonical_json_bytes(
            repeated_record
        ):
            _record_failure(
                blockers,
                profile_row,
                "reset_nondeterminism",
                {"seed": seed, "battle_index": battle_index},
            )
            profile_results.append(profile_row)
            break
        reset_determinism_checks += 1
        profile_row["progression"] = progression
        reached_battle_indices[int(progression["reached_battle_index"])] += 1
        reached_acts[int(progression["act"])] += 1
        reached_encounters[str(progression["encounter"])] += 1
        reached_floors.append(int(progression["floor"]))
        reached_deck_sizes.append(int(progression["deck_size"]))
        reached_relic_counts.append(int(progression["relic_count"]))
        reached_player_hp.append(int(progression["player_current_hp"]))
        actions_since_end_turn = 0

        for _ in range(config.max_decisions_per_seed):
            status = environment.status()
            if bool(status.get("terminal")):
                outcome = str(status.get("outcome") or "unknown")
                terminal_outcomes[outcome] += 1
                profile_row["terminal"] = True
                profile_row["outcome"] = outcome
                break
            if not bool(status.get("supported")):
                reason = str(
                    status.get("unsupported_reason")
                    or status.get("input_state")
                    or "unknown"
                )
                unsupported_reasons[reason] += 1
                profile_row["unsupported_reason"] = reason
                break

            try:
                mapped = environment.mapped_state(id_mapper=id_mapper)
            except CombatBridgeError as exc:
                mapping_errors[exc.reason] += 1
                _record_failure(blockers, profile_row, "mapping_failure", exc)
                stop_cohort = True
                break
            if (
                mapped.state.continuous.shape != (CONTINUOUS_DIM,)
                or mapped.state.card_ids.shape != (CARD_SLOTS,)
                or mapped.state.potion_ids.shape != (POTION_SLOTS,)
                or mapped.state.relic_ids.shape != (RELIC_SLOTS,)
                or mapped.action_mask.shape != (ACTION_DIM,)
            ):
                _record_failure(
                    blockers,
                    profile_row,
                    "rl_v2_shape_mismatch",
                    {"seed": seed, "battle_index": battle_index},
                )
                stop_cohort = True
                break

            supported_state_count += 1
            actions = environment.legal_actions()
            for family in {str(action.get("kind") or "unknown") for action in actions}:
                available_action_families[family] += 1
            try:
                selected = select_deterministic_action(
                    actions,
                    actions_since_end_turn=actions_since_end_turn,
                    max_actions_per_turn=config.max_actions_per_turn,
                )
            except CombatBridgeError as exc:
                _record_failure(blockers, profile_row, "action_selection_failure", exc)
                stop_cohort = True
                break

            try:
                original = canonical_json_bytes(_environment_record(environment))
            except Exception as exc:
                _record_failure(blockers, profile_row, "native_record_failure", exc)
                stop_cohort = True
                break
            left = environment.clone()
            right = environment.clone()
            try:
                left.step(str(selected["action_id"]))
                right.step(str(selected["action_id"]))
            except Exception as exc:  # Native exceptions must become report evidence.
                _record_failure(blockers, profile_row, "native_step_failure", exc)
                stop_cohort = True
                break
            try:
                source_record = canonical_json_bytes(_environment_record(environment))
                left_record = canonical_json_bytes(_environment_record(left))
                right_record = canonical_json_bytes(_environment_record(right))
            except Exception as exc:
                _record_failure(blockers, profile_row, "native_successor_record_failure", exc)
                stop_cohort = True
                break
            if source_record != original:
                _record_failure(
                    blockers,
                    profile_row,
                    "clone_isolation_failure",
                    {"seed": seed, "battle_index": battle_index},
                )
                stop_cohort = True
                break
            clone_isolation_checks += 1
            if left_record != right_record:
                _record_failure(
                    blockers,
                    profile_row,
                    "successor_nondeterminism",
                    {"seed": seed, "battle_index": battle_index},
                )
                stop_cohort = True
                break
            successor_determinism_checks += 1

            settlement = validate_card_select_settlement(
                left.snapshot().get("card_select_settlement")
            )
            if settlement["count"]:
                settlement_transition_count += 1
                settlement_action_count += int(settlement["count"])
                settlement_task_counts.update(settlement["tasks"])

            family = str(selected.get("kind") or "unknown")
            executed_action_families[family] += 1
            executed_action_count += 1
            profile_row["decisions"] += 1
            environment = left
            actions_since_end_turn = (
                0 if family == "end_turn" else actions_since_end_turn + 1
            )
        else:
            final_status = environment.status()
            if bool(final_status.get("terminal")):
                outcome = str(final_status.get("outcome") or "unknown")
                terminal_outcomes[outcome] += 1
                profile_row["terminal"] = True
                profile_row["outcome"] = outcome
            elif not bool(final_status.get("supported")):
                reason = str(
                    final_status.get("unsupported_reason")
                    or final_status.get("input_state")
                    or "unknown"
                )
                unsupported_reasons[reason] += 1
                profile_row["unsupported_reason"] = reason
            else:
                decision_bound_count += 1
                profile_row["truncated"] = True

        profile_results.append(profile_row)
        if stop_cohort:
            break

    if supported_state_count == 0:
        blockers.append("no_supported_states")
    later_battle_requested = any(value > 0 for value in config.battle_indices)
    positive_battle_profile_count = sum(
        count for index, count in reached_battle_indices.items() if index > 0
    )
    coverage_gate_passed = (
        positive_battle_profile_count > 0
        and len(reached_encounters) >= 2
        and bool(reached_floors)
        and max(reached_floors) > 1
    )
    if later_battle_requested and not coverage_gate_passed:
        blockers.append("later_battle_coverage_insufficient")
    blockers = list(dict.fromkeys(blockers))
    ready = not blockers
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "source_type": SOURCE_TYPE,
        "authority": dict(REPORT_AUTHORITY),
        "config": asdict(config),
        "provenance": dict(provenance),
        "metrics": {
            "available_action_family_state_counts": dict(sorted(available_action_families.items())),
            "card_select_settlement_action_count": settlement_action_count,
            "card_select_settlement_task_counts": dict(sorted(settlement_task_counts.items())),
            "card_select_settlement_transition_count": settlement_transition_count,
            "clone_isolation_checks": clone_isolation_checks,
            "decision_bound_seed_count": decision_bound_count,
            "executed_action_count": executed_action_count,
            "executed_action_family_counts": dict(sorted(executed_action_families.items())),
            "initialization_failure_counts": dict(sorted(initialization_failures.items())),
            "mapping_error_counts": dict(sorted(mapping_errors.items())),
            "profile_count_completed": len(profile_results),
            "profile_count_initialized": sum(reached_battle_indices.values()),
            "profile_count_registered": len(config.profiles()),
            "progression_coverage": {
                "act_counts": dict(sorted(reached_acts.items())),
                "battle_index_counts": dict(sorted(reached_battle_indices.items())),
                "coverage_gate_passed": coverage_gate_passed,
                "deck_size_range": _range_summary(reached_deck_sizes),
                "encounter_counts": dict(sorted(reached_encounters.items())),
                "floor_range": _range_summary(reached_floors),
                "player_hp_range": _range_summary(reached_player_hp),
                "positive_battle_profile_count": positive_battle_profile_count,
                "relic_count_range": _range_summary(reached_relic_counts),
            },
            "reset_determinism_checks": reset_determinism_checks,
            "seed_count_completed": len({row["seed"] for row in profile_results}),
            "seed_count_registered": len(config.seeds),
            "successor_determinism_checks": successor_determinism_checks,
            "supported_state_count": supported_state_count,
            "terminal_outcome_counts": dict(sorted(terminal_outcomes.items())),
            "unsupported_reason_counts": dict(sorted(unsupported_reasons.items())),
        },
        "profile_results": profile_results,
        "blockers": blockers,
        "verdict": (
            "later_battle_surface_ready_for_training"
            if ready and later_battle_requested
            else (
                "bridge_ready_for_live_divergence_calibration"
                if ready
                else "bridge_not_ready"
            )
        ),
        "next_gate": {
            "expanded_surface_training_coverage_gate_passed": (
                ready and later_battle_requested and coverage_gate_passed
            ),
            "real_game_divergence_calibration_authorized": False,
            "simulator_replay_generation_authorized": False,
            "requirements": [
                "bind any expanded-surface training to this module and profile evidence",
                "keep simulator-generated candidates outside production",
                "require matched real-game divergence evidence before transfer or qualification",
            ],
        },
    }


def _parse_seeds(value: str) -> tuple[int, ...]:
    text = value.strip()
    if ".." in text:
        start_text, end_text = text.split("..", 1)
        start = int(start_text)
        end = int(end_text)
        if end < start:
            raise argparse.ArgumentTypeError("seed range end must not precede start")
        return tuple(range(start, end + 1))
    try:
        return tuple(int(part.strip()) for part in text.split(",") if part.strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError("seeds must be comma-separated or start..end") from exc


def _render_summary(report: Mapping[str, Any]) -> str:
    metrics = report.get("metrics", {})
    blockers = report.get("blockers", [])
    blocker_text = ", ".join(str(value) for value in blockers) if blockers else "none"
    return "\n".join(
        (
            "# Combat LightSTS Bridge Calibration",
            "",
            f"- Verdict: `{report.get('verdict')}`",
            f"- Registered profiles: `{metrics.get('profile_count_registered', 0)}`",
            f"- Initialized profiles: `{metrics.get('profile_count_initialized', 0)}`",
            f"- Supported states: `{metrics.get('supported_state_count', 0)}`",
            f"- Deterministic successors: `{metrics.get('successor_determinism_checks', 0)}`",
            f"- Progression coverage: `{json.dumps(metrics.get('progression_coverage', {}), sort_keys=True)}`",
            f"- Initialization failures: `{json.dumps(metrics.get('initialization_failure_counts', {}), sort_keys=True)}`",
            f"- Terminal outcomes: `{json.dumps(metrics.get('terminal_outcome_counts', {}), sort_keys=True)}`",
            f"- Unsupported reasons: `{json.dumps(metrics.get('unsupported_reason_counts', {}), sort_keys=True)}`",
            f"- Blockers: `{blocker_text}`",
            "",
            "All authority flags are false. This report does not authorize training, gameplay,",
            "model loading, qualification, promotion, OPE, policy claims, or mechanics equivalence.",
            "Simulator replay generation remains gated on matched real-game divergence calibration.",
            "",
        )
    )


def _publish(output_dir: Path, report: Mapping[str, Any]) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=False)
    report_bytes = canonical_json_bytes(report) + b"\n"
    summary_bytes = _render_summary(report).encode("utf-8")
    manifest = {
        "schema_version": "combat-lightspeed-bridge-calibration-manifest-v3",
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


def _failure_report(config: CalibrationConfig, exc: Exception) -> dict[str, Any]:
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "source_type": SOURCE_TYPE,
        "authority": dict(REPORT_AUTHORITY),
        "config": asdict(config),
        "provenance": {},
        "metrics": {},
        "profile_results": [],
        "blockers": ["calibration_setup_failure"],
        "failure": {"type": type(exc).__name__, "detail": str(exc)},
        "verdict": "bridge_not_ready",
        "next_gate": {
            "real_game_divergence_calibration_authorized": False,
            "simulator_replay_generation_authorized": False,
            "requirements": ["resolve the source-only calibration setup failure"],
        },
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--simulator-repo", required=True, type=Path)
    parser.add_argument("--module", required=True, type=Path)
    parser.add_argument("--dll-dir", action="append", default=[], type=Path)
    parser.add_argument("--items-json", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--seeds", default="0..31", type=_parse_seeds)
    parser.add_argument("--battle-indices", default="0", type=_parse_seeds)
    parser.add_argument("--ascension", default=0, type=int)
    parser.add_argument("--max-decisions-per-seed", default=200, type=int)
    parser.add_argument("--max-actions-per-turn", default=8, type=int)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    config = CalibrationConfig(
        seeds=args.seeds,
        battle_indices=args.battle_indices,
        ascension=args.ascension,
        max_decisions_per_seed=args.max_decisions_per_seed,
        max_actions_per_turn=args.max_actions_per_turn,
    )
    try:
        config.validate()
        native_module = load_native_module(args.module, dll_directories=args.dll_dir)
        provenance = collect_provenance(
            repo_root=args.repo_root,
            simulator_repo=args.simulator_repo,
            module_path=args.module,
            native_module=native_module,
        )
        report = run_calibration(
            native_module,
            id_mapper=build_id_mapper(args.items_json),
            config=config,
            provenance=provenance,
        )
    except Exception as exc:
        report = _failure_report(config, exc)
    _publish(args.output_dir.resolve(), report)
    print(json.dumps({"output_dir": str(args.output_dir.resolve()), "verdict": report["verdict"]}))
    return 0 if report["verdict"] in {
        "bridge_ready_for_live_divergence_calibration",
        "later_battle_surface_ready_for_training",
    } else 2


if __name__ == "__main__":
    raise SystemExit(main())
