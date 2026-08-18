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
    POTION_SLOTS,
    RELIC_SLOTS,
    SOURCE_TYPE,
    CombatBridgeError,
    NativeCombatEnvironment,
    canonical_json_bytes,
    collect_provenance,
    load_native_module,
    sha256_bytes,
)
from spirecomm.ai.rl.v2.id_mapping import IdMapper, build_id_mapper


REPORT_SCHEMA_VERSION = "combat-lightspeed-bridge-calibration-v1"
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
        if not 0 <= self.ascension <= 20:
            raise ValueError("ascension must be in 0..20")
        if self.max_decisions_per_seed <= 0:
            raise ValueError("max decisions must be positive")
        if self.max_actions_per_turn <= 0:
            raise ValueError("max actions per turn must be positive")


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
    seed_results: list[dict[str, Any]] = []
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
    decision_bound_count = 0
    stop_cohort = False

    for seed in config.seeds:
        seed_row: dict[str, Any] = {
            "seed": seed,
            "decisions": 0,
            "terminal": False,
            "truncated": False,
            "unsupported_reason": "",
        }
        environment = NativeCombatEnvironment.reset(
            native_module,
            seed=seed,
            ascension=config.ascension,
        )
        repeated = NativeCombatEnvironment.reset(
            native_module,
            seed=seed,
            ascension=config.ascension,
        )
        if canonical_json_bytes(_environment_record(environment)) != canonical_json_bytes(
            _environment_record(repeated)
        ):
            _record_failure(blockers, seed_row, "reset_nondeterminism", seed)
            seed_results.append(seed_row)
            break
        reset_determinism_checks += 1
        actions_since_end_turn = 0

        for _ in range(config.max_decisions_per_seed):
            status = environment.status()
            if bool(status.get("terminal")):
                outcome = str(status.get("outcome") or "unknown")
                terminal_outcomes[outcome] += 1
                seed_row["terminal"] = True
                seed_row["outcome"] = outcome
                break
            if not bool(status.get("supported")):
                reason = str(
                    status.get("unsupported_reason")
                    or status.get("input_state")
                    or "unknown"
                )
                unsupported_reasons[reason] += 1
                seed_row["unsupported_reason"] = reason
                break

            try:
                mapped = environment.mapped_state(id_mapper=id_mapper)
            except CombatBridgeError as exc:
                mapping_errors[exc.reason] += 1
                _record_failure(blockers, seed_row, "mapping_failure", exc)
                stop_cohort = True
                break
            if (
                mapped.state.continuous.shape != (CONTINUOUS_DIM,)
                or mapped.state.card_ids.shape != (CARD_SLOTS,)
                or mapped.state.potion_ids.shape != (POTION_SLOTS,)
                or mapped.state.relic_ids.shape != (RELIC_SLOTS,)
                or mapped.action_mask.shape != (ACTION_DIM,)
            ):
                _record_failure(blockers, seed_row, "rl_v2_shape_mismatch", seed)
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
                _record_failure(blockers, seed_row, "action_selection_failure", exc)
                stop_cohort = True
                break

            original = canonical_json_bytes(_environment_record(environment))
            left = environment.clone()
            right = environment.clone()
            try:
                left.step(str(selected["action_id"]))
                right.step(str(selected["action_id"]))
            except Exception as exc:  # Native exceptions must become report evidence.
                _record_failure(blockers, seed_row, "native_step_failure", exc)
                stop_cohort = True
                break
            if canonical_json_bytes(_environment_record(environment)) != original:
                _record_failure(blockers, seed_row, "clone_isolation_failure", seed)
                stop_cohort = True
                break
            clone_isolation_checks += 1
            if canonical_json_bytes(_environment_record(left)) != canonical_json_bytes(
                _environment_record(right)
            ):
                _record_failure(blockers, seed_row, "successor_nondeterminism", seed)
                stop_cohort = True
                break
            successor_determinism_checks += 1

            family = str(selected.get("kind") or "unknown")
            executed_action_families[family] += 1
            executed_action_count += 1
            seed_row["decisions"] += 1
            environment = left
            actions_since_end_turn = (
                0 if family == "end_turn" else actions_since_end_turn + 1
            )
        else:
            final_status = environment.status()
            if bool(final_status.get("terminal")):
                outcome = str(final_status.get("outcome") or "unknown")
                terminal_outcomes[outcome] += 1
                seed_row["terminal"] = True
                seed_row["outcome"] = outcome
            elif not bool(final_status.get("supported")):
                reason = str(
                    final_status.get("unsupported_reason")
                    or final_status.get("input_state")
                    or "unknown"
                )
                unsupported_reasons[reason] += 1
                seed_row["unsupported_reason"] = reason
            else:
                decision_bound_count += 1
                seed_row["truncated"] = True

        seed_results.append(seed_row)
        if stop_cohort:
            break

    if supported_state_count == 0:
        blockers.append("no_supported_states")
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
            "clone_isolation_checks": clone_isolation_checks,
            "decision_bound_seed_count": decision_bound_count,
            "executed_action_count": executed_action_count,
            "executed_action_family_counts": dict(sorted(executed_action_families.items())),
            "mapping_error_counts": dict(sorted(mapping_errors.items())),
            "reset_determinism_checks": reset_determinism_checks,
            "seed_count_completed": len(seed_results),
            "seed_count_registered": len(config.seeds),
            "successor_determinism_checks": successor_determinism_checks,
            "supported_state_count": supported_state_count,
            "terminal_outcome_counts": dict(sorted(terminal_outcomes.items())),
            "unsupported_reason_counts": dict(sorted(unsupported_reasons.items())),
        },
        "seed_results": seed_results,
        "blockers": blockers,
        "verdict": (
            "bridge_ready_for_live_divergence_calibration"
            if ready
            else "bridge_not_ready"
        ),
        "next_gate": {
            "real_game_divergence_calibration_authorized": False,
            "simulator_replay_generation_authorized": False,
            "requirements": [
                "define a source-bound real battle-start import or matched replay surface",
                "compare matched action legality and successor state against the game",
                "pre-register material divergence thresholds and failure handling",
                "keep simulator-generated replay outside production until that gate passes",
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
            f"- Registered seeds: `{metrics.get('seed_count_registered', 0)}`",
            f"- Completed seeds: `{metrics.get('seed_count_completed', 0)}`",
            f"- Supported states: `{metrics.get('supported_state_count', 0)}`",
            f"- Deterministic successors: `{metrics.get('successor_determinism_checks', 0)}`",
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
        "schema_version": "combat-lightspeed-bridge-calibration-manifest-v1",
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
        "seed_results": [],
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
    parser.add_argument("--ascension", default=0, type=int)
    parser.add_argument("--max-decisions-per-seed", default=200, type=int)
    parser.add_argument("--max-actions-per-turn", default=8, type=int)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    config = CalibrationConfig(
        seeds=args.seeds,
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
    return 0 if report["verdict"] == "bridge_ready_for_live_divergence_calibration" else 2


if __name__ == "__main__":
    raise SystemExit(main())
