"""Build a real context target from parent-only guard-replacement traces."""

from __future__ import annotations

import argparse
from collections import Counter
import copy
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any, Mapping, Sequence

import torch


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
EXPECTED_INTERPRETER = Path(r"D:\anaconda\envs\stsai\python.exe")
GAME_DIR = Path(r"D:\SteamLibrary\steamapps\common\SlayTheSpire")

from analysis_scripts import combat_rl_real_context_balanced_corpus as balanced
from analysis_scripts import combat_rl_action_relative_live_shadow_summary as shadow_summary
from analysis_scripts.combat_lightspeed_replay_distribution_calibration import (
    FLOOR_STRATA,
)
from spirecomm.ai.rl.v2.action_relative_live_shadow import (
    load_live_shadow_registration,
)


TARGET_SCHEMA = "combat-rl-action-relative-live-context-target-v1"
REGISTRATION_SCHEMA = "combat-rl-action-relative-live-context-target-registration-v1"
REPORT_SCHEMA = "combat-rl-action-relative-live-context-target-report-v1"
MANIFEST_SCHEMA = "combat-rl-action-relative-live-context-target-manifest-v1"
END_TURN_ACTION_INDEX = 90
DEFAULT_EXPECTED_RUN_COUNT = 20
DEFAULT_MINIMUM_ROW_COUNT = 300
DEFAULT_MINIMUM_LATE_ROW_COUNT = 20
DEFAULT_MAXIMUM_JOIN_DELTA_SECONDS = 0.100
DEFAULT_MAXIMUM_UNJOINED_ELIGIBLE_COUNT = 5
DEFAULT_MAXIMUM_UNJOINED_ELIGIBLE_FRACTION = 0.01
DEFAULT_MAXIMUM_BATCH_WALL_SECONDS = 3_600.0
DEFAULT_MAXIMUM_OUTPUT_BYTES = 16_777_216
EMPTY_POTION_IDS = frozenset({"", "Potion Slot"})
SOURCE_BOUND_PATHS = (
    "analysis_scripts/combat_rl_action_relative_live_context_target.py",
    "analysis_scripts/combat_rl_action_relative_live_shadow_summary.py",
    "analysis_scripts/combat_rl_real_context_balanced_corpus.py",
)
TARGET_AUTHORITY = {
    "candidate_action_takeover": False,
    "gameplay_quality_claim": False,
    "model_fitting": False,
    "online_training": False,
    "promotion": False,
    "qualification": False,
    "target_publication": True,
}
TARGET_SHADOW_REQUIRED_CONDITIONS = (
    "trace_identity_valid",
    "decision_sequence_valid",
    "decision_count_within_budget",
    "minimum_eligible_count_reached",
    "candidate_has_no_authority",
    "eligible_guard_identity_valid",
    "derived_fields_valid",
    "ineligible_decisions_not_inferred",
    "runtime_error_count_zero",
)


def _canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("ascii")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256(value: Any, *, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} SHA-256 is missing")
    normalized = value.lower()
    if len(normalized) != 64 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise ValueError(f"{label} SHA-256 is invalid")
    return normalized


def _source_commit(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("target source commit is missing")
    normalized = value.lower()
    if len(normalized) != 40 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise ValueError("target source commit is invalid")
    return normalized


def _absolute_path(value: Any, *, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} path is missing")
    raw = Path(value)
    if not raw.is_absolute():
        raise ValueError(f"{label} path must be absolute")
    return raw.resolve()


def _binding(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    if not resolved.is_file():
        raise ValueError(f"target bound file is missing: {resolved}")
    return {
        "path": str(resolved),
        "sha256": sha256_file(resolved),
        "size_bytes": resolved.stat().st_size,
    }


def _source_file_bindings() -> dict[str, dict[str, Any]]:
    return {
        relative: _binding(REPO_ROOT / relative) for relative in SOURCE_BOUND_PATHS
    }


def _communication_mod_command(
    *, shadow_registration_path: Path, parent_checkpoint_path: Path
) -> list[str]:
    return [
        str(EXPECTED_INTERPRETER.resolve()),
        str((REPO_ROOT / "scripts" / "run_training_batch.py").resolve()),
        "--eval",
        "--epsilon",
        "0.0",
        "--max-games",
        "5",
        "--phase",
        "conservative",
        "--agent",
        "combat_rl",
        "--rl-version",
        "v2",
        "--model",
        str(parent_checkpoint_path.resolve()),
        "--restart-guidance",
        "--truncate-log-after-backup",
        "--truncate-traces-at-start",
        "--skip-checkpoint-backup",
        "--skip-maintenance",
        "--skip-post-analysis",
        "--decision-trace-path",
        str((GAME_DIR / "ai_decision_trace_clean.jsonl").resolve()),
        "--sim-divergence-trace-path",
        str((GAME_DIR / "sim_divergence_trace_clean.jsonl").resolve()),
        "--combat-action-relative-shadow-registration",
        str(shadow_registration_path.resolve()),
    ]


def _timestamp_seconds(value: Any, *, label: str) -> float:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} timestamp is missing")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label} timestamp is invalid") from exc
    result = parsed.timestamp()
    if not math.isfinite(result):
        raise ValueError(f"{label} timestamp is invalid")
    return result


def _integer(value: Any, *, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{label} must be an integer")
    return int(value)


def _run_seed(value: Any) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return int(value)
    if isinstance(value, str):
        normalized = value.strip()
        digits = normalized[1:] if normalized.startswith("-") else normalized
        if digits and digits.isdigit():
            return int(normalized)
    raise ValueError("run seed must be an integer or decimal string")


def floor_stratum(floor: int) -> str:
    value = _integer(floor, label="context floor")
    for name, start, end in FLOOR_STRATA:
        if start <= value <= end:
            return name
    raise ValueError("context floor is outside the canonical strata")


def context_cell_id(
    *,
    floor: int,
    potion_occupied_slots: int,
    relic_occupied_slots: int,
    player_hp_quartile: int,
) -> str:
    potion = _integer(potion_occupied_slots, label="occupied potion slots")
    relic = _integer(relic_occupied_slots, label="occupied relic slots")
    quartile = _integer(player_hp_quartile, label="player HP quartile")
    if potion < 0 or relic < 0 or not 0 <= quartile <= 3:
        raise ValueError("context inventory or HP quartile is invalid")
    return f"{floor_stratum(floor)}|p{potion}|r{relic}|h{quartile}"


def load_jsonl(path: Path, *, label: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            if not raw.strip():
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{label} line {line_number} is invalid JSON"
                ) from exc
            if not isinstance(row, dict):
                raise ValueError(f"{label} line {line_number} is not an object")
            rows.append(row)
    return rows


def load_completed_runs(run_dir: Path) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    for path in sorted(run_dir.rglob("*.run")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"completed run is invalid JSON: {path}") from exc
        if not isinstance(payload, Mapping):
            raise ValueError(f"completed run is not an object: {path}")
        timestamp = _integer(payload.get("timestamp"), label="run timestamp")
        seed = _run_seed(payload.get("seed_played"))
        filename_timestamp = path.stem
        if not filename_timestamp.isdigit() or int(filename_timestamp) != timestamp:
            raise ValueError("completed run filename and timestamp differ")
        runs.append(
            {
                "path": path.resolve().as_posix(),
                "sha256": sha256_file(path),
                "timestamp": timestamp,
                "seed_played": seed,
                "victory": payload.get("victory") is True,
                "floor_reached": _integer(
                    payload.get("floor_reached"), label="run floor reached"
                ),
            }
        )
    timestamps = [int(row["timestamp"]) for row in runs]
    seeds = [int(row["seed_played"]) for row in runs]
    if len(timestamps) != len(set(timestamps)) or len(seeds) != len(set(seeds)):
        raise ValueError("completed run timestamps or seeds are duplicated")
    return sorted(runs, key=lambda row: int(row["timestamp"]))


def batch_recovery_status(
    run_dir: Path, *, expected_run_count: int = 5
) -> dict[str, Any]:
    expected = _integer(expected_run_count, label="expected batch run count")
    if expected <= 0:
        raise ValueError("expected batch run count must be positive")
    runs = load_completed_runs(run_dir) if run_dir.exists() else []
    if len(runs) > expected:
        raise ValueError("target batch already exceeds its registered run count")
    return {
        "completed_run_count": len(runs),
        "remaining_run_count": expected - len(runs),
        "complete": len(runs) == expected,
        "run_timestamps": [int(run["timestamp"]) for run in runs],
        "run_seeds": [int(run["seed_played"]) for run in runs],
    }


def target_shadow_conditions(readiness: Mapping[str, Any]) -> dict[str, bool]:
    conditions = readiness.get("readiness_conditions")
    if not isinstance(conditions, Mapping):
        raise ValueError("target shadow readiness conditions are missing")
    selected: dict[str, bool] = {}
    for name in TARGET_SHADOW_REQUIRED_CONDITIONS:
        value = conditions.get(name)
        if not isinstance(value, bool):
            raise ValueError(f"target shadow readiness condition is invalid: {name}")
        selected[name] = value
    return selected


def _validate_decision_rows(
    rows: Sequence[Mapping[str, Any]],
) -> list[tuple[int, Mapping[str, Any], float]]:
    validated: list[tuple[int, Mapping[str, Any], float]] = []
    for index, row in enumerate(rows):
        if row.get("in_combat") is not True:
            continue
        timestamp = row.get("unix_time")
        if not isinstance(timestamp, (int, float)) or isinstance(timestamp, bool):
            raise ValueError("decision-state timestamp is invalid")
        value = float(timestamp)
        if not math.isfinite(value):
            raise ValueError("decision-state timestamp is invalid")
        _integer(row.get("floor"), label="decision-state floor")
        _integer(row.get("turn"), label="decision-state turn")
        validated.append((index, row, value))
    return validated


def _target_context(
    decision: Mapping[str, Any],
    *,
    event: Mapping[str, Any],
    run: Mapping[str, Any],
    batch_id: str,
    join_delta_seconds: float,
) -> dict[str, Any]:
    player = decision.get("player")
    if not isinstance(player, Mapping):
        raise ValueError("decision-state player is missing")
    current_hp = player.get("current_hp")
    maximum_hp = player.get("max_hp")
    if not isinstance(current_hp, (int, float)) or not isinstance(
        maximum_hp, (int, float)
    ):
        raise ValueError("decision-state player HP is invalid")
    current = float(current_hp)
    maximum = float(maximum_hp)
    if not math.isfinite(current) or not math.isfinite(maximum) or maximum <= 0:
        raise ValueError("decision-state player HP is invalid")
    hp_ratio = current / maximum
    if not 0.0 <= hp_ratio <= 1.0:
        raise ValueError("decision-state player HP ratio is outside [0, 1]")
    potions = decision.get("potions")
    relics = decision.get("relics")
    if not isinstance(potions, list) or not isinstance(relics, list):
        raise ValueError("decision-state inventory is missing")
    potion_count = sum(
        isinstance(item, Mapping) and str(item.get("id") or "") not in EMPTY_POTION_IDS
        for item in potions
    )
    relic_count = len(relics)
    floor = _integer(decision.get("floor"), label="decision-state floor")
    quartile = min(3, max(0, int(hp_ratio * 4.0)))
    return {
        "batch_id": batch_id,
        "session_id": str(event["session_id"]),
        "decision_sequence": _integer(
            event["decision_sequence"], label="shadow decision sequence"
        ),
        "state_sha256": _sha256(event.get("state_sha256"), label="shadow state"),
        "shadow_timestamp": str(event["timestamp"]),
        "decision_timestamp": float(decision["unix_time"]),
        "join_delta_ms": float(join_delta_seconds * 1000.0),
        "run_timestamp": int(run["timestamp"]),
        "run_seed": int(run["seed_played"]),
        "run_sha256": str(run["sha256"]),
        "floor": floor,
        "turn": _integer(decision.get("turn"), label="decision-state turn"),
        "floor_ratio": floor / 50.0,
        "player_hp_ratio": hp_ratio,
        "potion_occupied_slots": int(potion_count),
        "relic_occupied_slots": int(relic_count),
        "player_hp_quartile": quartile,
        "context_cell_id": context_cell_id(
            floor=floor,
            potion_occupied_slots=int(potion_count),
            relic_occupied_slots=int(relic_count),
            player_hp_quartile=quartile,
        ),
    }


def extract_target_rows(
    *,
    events: Sequence[Mapping[str, Any]],
    decision_rows: Sequence[Mapping[str, Any]],
    completed_runs: Sequence[Mapping[str, Any]],
    batch_id: str,
    maximum_join_delta_seconds: float = DEFAULT_MAXIMUM_JOIN_DELTA_SECONDS,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    if not isinstance(batch_id, str) or not batch_id.strip():
        raise ValueError("target batch identity is missing")
    if not math.isfinite(maximum_join_delta_seconds) or maximum_join_delta_seconds <= 0:
        raise ValueError("maximum decision-state join delta is invalid")
    runs = sorted(completed_runs, key=lambda row: int(row["timestamp"]))
    if not runs:
        raise ValueError("completed run inventory is empty")
    validated_decisions = _validate_decision_rows(decision_rows)
    used_decision_indices: set[int] = set()
    target_rows: list[dict[str, Any]] = []
    exclusions: Counter[str] = Counter()
    sessions: dict[str, int] = {}
    for event in events:
        if event.get("event_type") == "error" or event.get("runtime_error_type"):
            raise ValueError("shadow trace contains a runtime error")
        if event.get("event_type") != "decision":
            continue
        if event.get("candidate_has_authority") is not False:
            raise ValueError("shadow trace grants candidate authority")
        session = event.get("session_id")
        sequence = event.get("decision_sequence")
        if not isinstance(session, str) or not isinstance(sequence, int):
            raise ValueError("shadow decision sequence is invalid")
        expected = sessions.get(session, 0) + 1
        if sequence != expected:
            raise ValueError("shadow decision sequence is not contiguous")
        sessions[session] = sequence
        if event.get("eligible") is not True:
            reason = str(event.get("support_reason") or "ineligible")
            exclusions[reason] += 1
            continue
        if (
            event.get("support_reason") != ""
            or event.get("parent_action_index") != END_TURN_ACTION_INDEX
            or event.get("guard_action_index") == END_TURN_ACTION_INDEX
            or not isinstance(event.get("guard_action_index"), int)
            or event.get("executed_action_index") != event.get("guard_action_index")
            or event.get("executed_action_encodable") is not True
            or event.get("executed_action_legal") is not True
        ):
            raise ValueError("eligible shadow guard identity differs")
        event_time = _timestamp_seconds(event.get("timestamp"), label="shadow")
        event_floor = _integer(event.get("floor"), label="shadow floor")
        event_turn = _integer(event.get("turn"), label="shadow turn")
        matches = [
            (abs(decision_time - event_time), index, decision, decision_time)
            for index, decision, decision_time in validated_decisions
            if int(decision["floor"]) == event_floor
            and int(decision["turn"]) == event_turn
            and abs(decision_time - event_time) <= maximum_join_delta_seconds
        ]
        if not matches:
            exclusions["eligible_decision_state_join_missing"] += 1
            continue
        matches.sort(key=lambda value: (value[0], value[1]))
        if len(matches) > 1 and abs(matches[0][0] - matches[1][0]) <= 1e-9:
            raise ValueError("eligible shadow decision-state join is ambiguous")
        delta, index, decision, decision_time = matches[0]
        if index in used_decision_indices:
            raise ValueError("eligible shadow decision-state join is reused")
        used_decision_indices.add(index)
        run = next(
            (row for row in runs if int(row["timestamp"]) >= decision_time), None
        )
        if run is None:
            raise ValueError("eligible shadow decision is outside completed runs")
        target_rows.append(
            _target_context(
                decision,
                event=event,
                run=run,
                batch_id=batch_id.strip(),
                join_delta_seconds=delta,
            )
        )
    return target_rows, dict(sorted(exclusions.items()))


def context_target_identity(rows: Sequence[Mapping[str, Any]]) -> str:
    return hashlib.sha256(_canonical_json_bytes(list(rows))).hexdigest()


def validate_target_sufficiency(
    rows: Sequence[Mapping[str, Any]],
    *,
    completed_runs: Sequence[Mapping[str, Any]],
    development_run_seeds: set[int],
    expected_run_count: int = DEFAULT_EXPECTED_RUN_COUNT,
    minimum_row_count: int = DEFAULT_MINIMUM_ROW_COUNT,
    minimum_late_row_count: int = DEFAULT_MINIMUM_LATE_ROW_COUNT,
    unjoined_eligible_count: int = 0,
    maximum_unjoined_eligible_count: int = DEFAULT_MAXIMUM_UNJOINED_ELIGIBLE_COUNT,
    maximum_unjoined_eligible_fraction: float = (
        DEFAULT_MAXIMUM_UNJOINED_ELIGIBLE_FRACTION
    ),
) -> dict[str, Any]:
    for value, label in (
        (expected_run_count, "expected run count"),
        (minimum_row_count, "minimum target row count"),
        (minimum_late_row_count, "minimum late target row count"),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ValueError(f"{label} must be positive")
    if (
        not isinstance(unjoined_eligible_count, int)
        or isinstance(unjoined_eligible_count, bool)
        or unjoined_eligible_count < 0
    ):
        raise ValueError("unjoined eligible count must be nonnegative")
    if (
        not isinstance(maximum_unjoined_eligible_count, int)
        or isinstance(maximum_unjoined_eligible_count, bool)
        or maximum_unjoined_eligible_count < 0
    ):
        raise ValueError("maximum unjoined eligible count must be nonnegative")
    if (
        not isinstance(maximum_unjoined_eligible_fraction, (int, float))
        or isinstance(maximum_unjoined_eligible_fraction, bool)
        or not math.isfinite(float(maximum_unjoined_eligible_fraction))
        or not 0.0 <= float(maximum_unjoined_eligible_fraction) <= 1.0
    ):
        raise ValueError("maximum unjoined eligible fraction is invalid")
    runs = list(completed_runs)
    run_timestamps = [int(run["timestamp"]) for run in runs]
    run_seeds = [int(run["seed_played"]) for run in runs]
    if len(run_timestamps) != len(set(run_timestamps)) or len(run_seeds) != len(
        set(run_seeds)
    ):
        raise ValueError("formal target run inventory is duplicated")
    overlap = sorted(set(run_seeds).intersection(development_run_seeds))
    if overlap:
        raise ValueError("formal target contains a development run seed")
    by_timestamp = {int(run["timestamp"]): run for run in runs}
    late_rows = 0
    decision_identities: set[tuple[str, str, int]] = set()
    for row in rows:
        batch_id = row.get("batch_id")
        session_id = row.get("session_id")
        sequence = _integer(
            row.get("decision_sequence"), label="target decision sequence"
        )
        if not isinstance(batch_id, str) or not batch_id:
            raise ValueError("target batch identity is missing")
        if not isinstance(session_id, str) or not session_id:
            raise ValueError("target session identity is missing")
        identity = (batch_id, session_id, sequence)
        if identity in decision_identities:
            raise ValueError("target decision identity is duplicated")
        decision_identities.add(identity)
        _sha256(row.get("state_sha256"), label="target state")
        timestamp = _integer(row.get("run_timestamp"), label="target run timestamp")
        seed = _integer(row.get("run_seed"), label="target run seed")
        if timestamp not in by_timestamp or int(by_timestamp[timestamp]["seed_played"]) != seed:
            raise ValueError("target row run identity is absent from the inventory")
        floor = _integer(row.get("floor"), label="target floor")
        hp_ratio = float(row.get("player_hp_ratio"))
        if not math.isfinite(hp_ratio) or not 0.0 <= hp_ratio <= 1.0:
            raise ValueError("target player HP ratio is invalid")
        expected_cell = context_cell_id(
            floor=floor,
            potion_occupied_slots=_integer(
                row.get("potion_occupied_slots"), label="target potion slots"
            ),
            relic_occupied_slots=_integer(
                row.get("relic_occupied_slots"), label="target relic slots"
            ),
            player_hp_quartile=_integer(
                row.get("player_hp_quartile"), label="target HP quartile"
            ),
        )
        if row.get("context_cell_id") != expected_cell:
            raise ValueError("target context cell identity differs")
        if 23 <= floor <= 34:
            late_rows += 1
    eligible_opportunity_count = len(rows) + unjoined_eligible_count
    unjoined_eligible_fraction = (
        unjoined_eligible_count / eligible_opportunity_count
        if eligible_opportunity_count
        else 0.0
    )
    conditions = {
        "completed_run_count": len(runs) == expected_run_count,
        "minimum_target_rows": len(rows) >= minimum_row_count,
        "minimum_late_target_rows": late_rows >= minimum_late_row_count,
        "maximum_unjoined_eligible_count": (
            unjoined_eligible_count <= maximum_unjoined_eligible_count
        ),
        "maximum_unjoined_eligible_fraction": (
            unjoined_eligible_fraction
            <= float(maximum_unjoined_eligible_fraction)
        ),
        "run_seed_isolation": not overlap,
        "run_identity_complete": True,
        "context_rows_valid": True,
    }
    return {
        "conditions": conditions,
        "all_conditions_passed": all(conditions.values()),
        "completed_run_count": len(runs),
        "target_row_count": len(rows),
        "late_target_row_count": late_rows,
        "eligible_opportunity_count": eligible_opportunity_count,
        "unjoined_eligible_count": unjoined_eligible_count,
        "unjoined_eligible_fraction": unjoined_eligible_fraction,
        "target_identity_sha256": context_target_identity(rows),
    }


def _target_feature_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    cells: list[str] = []
    features = {
        "floor_ratio": [],
        "player_hp_ratio": [],
        "potion_occupied_slots": [],
        "relic_occupied_slots": [],
    }
    for row in rows:
        floor = _integer(row.get("floor"), label="target floor")
        hp_ratio = float(row.get("player_hp_ratio"))
        potion = _integer(
            row.get("potion_occupied_slots"), label="target potion slots"
        )
        relic = _integer(row.get("relic_occupied_slots"), label="target relic slots")
        quartile = _integer(row.get("player_hp_quartile"), label="target HP quartile")
        cell = context_cell_id(
            floor=floor,
            potion_occupied_slots=potion,
            relic_occupied_slots=relic,
            player_hp_quartile=quartile,
        )
        if row.get("context_cell_id") != cell:
            raise ValueError("target context cell identity differs")
        floor_ratio = float(row.get("floor_ratio"))
        if abs(floor_ratio - floor / 50.0) > 1e-6:
            raise ValueError("target floor ratio differs")
        if not math.isfinite(hp_ratio) or not 0.0 <= hp_ratio <= 1.0:
            raise ValueError("target player HP ratio is invalid")
        cells.append(cell)
        features["floor_ratio"].append(floor_ratio)
        features["player_hp_ratio"].append(hp_ratio)
        features["potion_occupied_slots"].append(float(potion))
        features["relic_occupied_slots"].append(float(relic))
    if not cells:
        raise ValueError("live context target is empty")
    return {
        "cells": cells,
        **{
            name: torch.tensor(values, dtype=torch.float64)
            for name, values in features.items()
        },
    }


def derive_context_weights_from_target(
    target_rows: Sequence[Mapping[str, Any]], simulator: Mapping[str, Any]
) -> dict[str, Any]:
    real_rows = _target_feature_rows(target_rows)
    simulator_rows = balanced._context_rows(simulator)
    simulator_cell_ids = list(simulator_rows["cell_ids"])
    real_counts = Counter(real_rows["cells"])
    simulator_counts = Counter(simulator_cell_ids)
    common = set(real_counts).intersection(simulator_counts)
    if not common:
        raise ValueError("live target and simulator context support do not overlap")
    real_total = len(real_rows["cells"])
    simulator_total = len(simulator_cell_ids)
    raw_weights = torch.tensor(
        [
            (real_counts[cell] / real_total)
            / (simulator_counts[cell] / simulator_total)
            if cell in common
            else 0.0
            for cell in simulator_cell_ids
        ],
        dtype=torch.float64,
    )
    weight_sum = float(raw_weights.sum())
    if not math.isfinite(weight_sum) or weight_sum <= 0.0:
        raise ValueError("live target context weights cannot be normalized")
    weights = raw_weights / weight_sum
    floor_coverage: dict[str, float | None] = {}
    for stratum in ("floor_23_27", "floor_28_34"):
        denominator = sum(
            count
            for cell, count in real_counts.items()
            if cell.startswith(f"{stratum}|")
        )
        numerator = sum(
            count
            for cell, count in real_counts.items()
            if cell.startswith(f"{stratum}|") and cell in common
        )
        floor_coverage[stratum] = numerator / denominator if denominator else None
    smds = {
        name: {
            "raw": balanced._smd(
                real_rows[name], simulator_rows[name], weights=None
            ),
            "weighted": balanced._smd(
                real_rows[name], simulator_rows[name], weights=weights
            ),
        }
        for name in (
            "floor_ratio",
            "player_hp_ratio",
            "potion_occupied_slots",
            "relic_occupied_slots",
        )
    }
    effective_sample_size = 1.0 / float(weights.square().sum())
    metrics = {
        "real_row_count": real_total,
        "simulator_row_count": simulator_total,
        "real_context_cell_count": len(real_counts),
        "simulator_context_cell_count": len(simulator_counts),
        "matched_context_cell_count": len(common),
        "real_context_mass_covered": sum(real_counts[cell] for cell in common)
        / real_total,
        "simulator_mass_retained": sum(
            simulator_counts[cell] for cell in common
        )
        / simulator_total,
        "floor_context_mass_covered": floor_coverage,
        "effective_sample_size": effective_sample_size,
        "effective_sample_size_fraction": effective_sample_size / simulator_total,
        "maximum_normalized_weight": float(weights.max()),
        "zero_weight_row_count": int((weights == 0.0).sum()),
        "standardized_mean_differences": smds,
    }
    return {
        "weights": weights,
        "cell_ids": simulator_cell_ids,
        "matched_cell_ids": sorted(common),
        "metrics": metrics,
    }


def build_target_registration(
    *,
    experiment_id: str,
    source_commit: str,
    development_audit_path: Path,
    development_run_seeds: Sequence[int],
    batches: Sequence[Mapping[str, Any]],
    output_dir: Path,
) -> dict[str, Any]:
    if not isinstance(experiment_id, str) or not experiment_id.strip():
        raise ValueError("target experiment identity is missing")
    normalized_commit = _source_commit(source_commit)
    normalized_seeds = sorted({_integer(value, label="development run seed") for value in development_run_seeds})
    if len(normalized_seeds) != 20:
        raise ValueError("target development run seed inventory must contain 20 seeds")
    normalized_batches: list[dict[str, Any]] = []
    batch_ids: set[str] = set()
    parent_identity: dict[str, str] | None = None
    for raw in batches:
        expected_keys = {
            "batch_id",
            "shadow_registration_path",
            "trace_path",
            "decision_trace_path",
            "run_dir",
        }
        if not isinstance(raw, Mapping) or set(raw) != expected_keys:
            raise ValueError("target batch registration keys differ")
        batch_id = raw["batch_id"]
        if not isinstance(batch_id, str) or not batch_id.strip() or batch_id in batch_ids:
            raise ValueError("target batch identity is missing or duplicated")
        batch_ids.add(batch_id)
        shadow_path = _absolute_path(
            raw["shadow_registration_path"], label="shadow registration"
        )
        trace_path = _absolute_path(raw["trace_path"], label="shadow trace")
        decision_path = _absolute_path(
            raw["decision_trace_path"], label="decision trace"
        )
        run_dir = _absolute_path(raw["run_dir"], label="run directory")
        shadow = load_live_shadow_registration(
            shadow_path, repo_root=REPO_ROOT, require_committed=False
        )
        if shadow.source_commit != normalized_commit:
            raise ValueError("target shadow source commit differs")
        if shadow.trace_path != trace_path:
            raise ValueError("target shadow trace path differs")
        current_parent = {
            "checkpoint_path": str(shadow.production_parent_checkpoint_path),
            "checkpoint_sha256": shadow.production_parent_checkpoint_sha256,
            "parameter_sha256": shadow.parent_state_dict_sha256,
        }
        if parent_identity is None:
            parent_identity = current_parent
        elif parent_identity != current_parent:
            raise ValueError("target shadow parent identity differs across batches")
        normalized_batches.append(
            {
                "batch_id": batch_id.strip(),
                "expected_run_count": 5,
                "shadow_registration": _binding(shadow_path),
                "trace_path": str(trace_path),
                "decision_trace_path": str(decision_path),
                "run_dir": str(run_dir),
                "communication_mod_command": _communication_mod_command(
                    shadow_registration_path=shadow_path,
                    parent_checkpoint_path=shadow.production_parent_checkpoint_path,
                ),
            }
        )
    if len(normalized_batches) != 4:
        raise ValueError("target registration must contain four batches")
    output = output_dir.resolve()
    try:
        output.relative_to((REPO_ROOT / "reports").resolve())
    except ValueError as exc:
        raise ValueError("target output must be inside reports") from exc
    return {
        "schema_version": REGISTRATION_SCHEMA,
        "experiment_id": experiment_id.strip(),
        "source_commit": normalized_commit,
        "source_files": _source_file_bindings(),
        "production_parent": parent_identity,
        "development_audit": _binding(development_audit_path),
        "development_run_seeds": normalized_seeds,
        "batches": normalized_batches,
        "target_contract": {
            "expected_run_count": DEFAULT_EXPECTED_RUN_COUNT,
            "minimum_row_count": DEFAULT_MINIMUM_ROW_COUNT,
            "minimum_late_row_count": DEFAULT_MINIMUM_LATE_ROW_COUNT,
            "maximum_join_delta_seconds": DEFAULT_MAXIMUM_JOIN_DELTA_SECONDS,
            "maximum_unjoined_eligible_count": (
                DEFAULT_MAXIMUM_UNJOINED_ELIGIBLE_COUNT
            ),
            "maximum_unjoined_eligible_fraction": (
                DEFAULT_MAXIMUM_UNJOINED_ELIGIBLE_FRACTION
            ),
            "context_schema": TARGET_SCHEMA,
        },
        "resource_limits": {
            "maximum_batch_wall_seconds": DEFAULT_MAXIMUM_BATCH_WALL_SECONDS,
            "maximum_output_bytes": DEFAULT_MAXIMUM_OUTPUT_BYTES,
        },
        "output_dir": str(output),
        "authority": copy.deepcopy(TARGET_AUTHORITY),
    }


def validate_target_registration(
    registration: Mapping[str, Any], *, require_batch_outputs: bool
) -> dict[str, Any]:
    expected_keys = {
        "schema_version",
        "experiment_id",
        "source_commit",
        "source_files",
        "production_parent",
        "development_audit",
        "development_run_seeds",
        "batches",
        "target_contract",
        "resource_limits",
        "output_dir",
        "authority",
    }
    if not isinstance(registration, Mapping) or set(registration) != expected_keys:
        raise ValueError("target registration keys differ")
    if registration["schema_version"] != REGISTRATION_SCHEMA:
        raise ValueError("target registration schema differs")
    _source_commit(registration["source_commit"])
    parent = registration["production_parent"]
    if not isinstance(parent, Mapping) or set(parent) != {
        "checkpoint_path",
        "checkpoint_sha256",
        "parameter_sha256",
    }:
        raise ValueError("target production parent binding differs")
    parent_checkpoint_path = _absolute_path(
        parent["checkpoint_path"], label="production parent checkpoint"
    )
    parent_checkpoint_sha = _sha256(
        parent["checkpoint_sha256"], label="production parent checkpoint"
    )
    parent_parameter_sha = _sha256(
        parent["parameter_sha256"], label="production parent parameter"
    )
    source_files = registration["source_files"]
    if not isinstance(source_files, Mapping) or set(source_files) != set(
        SOURCE_BOUND_PATHS
    ):
        raise ValueError("target source file inventory differs")
    for relative, binding in source_files.items():
        _validate_bound_file(binding, expected_path=REPO_ROOT / relative, label=relative)
    _validate_bound_file(
        registration["development_audit"],
        expected_path=None,
        label="development audit",
    )
    development_seeds = registration["development_run_seeds"]
    if (
        not isinstance(development_seeds, list)
        or len(development_seeds) != 20
        or development_seeds != sorted(set(development_seeds))
        or any(not isinstance(seed, int) or isinstance(seed, bool) for seed in development_seeds)
    ):
        raise ValueError("target development run seed inventory differs")
    contract = registration["target_contract"]
    if contract != {
        "expected_run_count": DEFAULT_EXPECTED_RUN_COUNT,
        "minimum_row_count": DEFAULT_MINIMUM_ROW_COUNT,
        "minimum_late_row_count": DEFAULT_MINIMUM_LATE_ROW_COUNT,
        "maximum_join_delta_seconds": DEFAULT_MAXIMUM_JOIN_DELTA_SECONDS,
        "maximum_unjoined_eligible_count": DEFAULT_MAXIMUM_UNJOINED_ELIGIBLE_COUNT,
        "maximum_unjoined_eligible_fraction": (
            DEFAULT_MAXIMUM_UNJOINED_ELIGIBLE_FRACTION
        ),
        "context_schema": TARGET_SCHEMA,
    }:
        raise ValueError("target contract differs")
    if registration["authority"] != TARGET_AUTHORITY:
        raise ValueError("target authority differs")
    if registration["resource_limits"] != {
        "maximum_batch_wall_seconds": DEFAULT_MAXIMUM_BATCH_WALL_SECONDS,
        "maximum_output_bytes": DEFAULT_MAXIMUM_OUTPUT_BYTES,
    }:
        raise ValueError("target resource limits differ")
    batches = registration["batches"]
    if not isinstance(batches, list) or len(batches) != 4:
        raise ValueError("target batch inventory differs")
    batch_ids: set[str] = set()
    for batch in batches:
        if not isinstance(batch, Mapping) or set(batch) != {
            "batch_id",
            "expected_run_count",
            "shadow_registration",
            "trace_path",
            "decision_trace_path",
            "run_dir",
            "communication_mod_command",
        }:
            raise ValueError("target batch keys differ")
        batch_id = batch["batch_id"]
        if not isinstance(batch_id, str) or not batch_id or batch_id in batch_ids:
            raise ValueError("target batch identity differs")
        batch_ids.add(batch_id)
        if batch["expected_run_count"] != 5:
            raise ValueError("target batch run count differs")
        _validate_bound_file(
            batch["shadow_registration"],
            expected_path=None,
            label=f"{batch_id} shadow registration",
        )
        shadow = load_live_shadow_registration(
            batch["shadow_registration"]["path"],
            repo_root=REPO_ROOT,
            require_committed=False,
        )
        if (
            shadow.source_commit != registration["source_commit"]
            or shadow.production_parent_checkpoint_path != parent_checkpoint_path
            or shadow.production_parent_checkpoint_sha256 != parent_checkpoint_sha
            or shadow.parent_state_dict_sha256 != parent_parameter_sha
            or shadow.trace_path != Path(batch["trace_path"]).resolve()
        ):
            raise ValueError("target shadow registration identity differs")
        if batch["communication_mod_command"] != _communication_mod_command(
            shadow_registration_path=Path(batch["shadow_registration"]["path"]),
            parent_checkpoint_path=parent_checkpoint_path,
        ):
            raise ValueError("target CommunicationMod command differs")
        for name in ("trace_path", "decision_trace_path", "run_dir"):
            path = _absolute_path(batch[name], label=f"{batch_id} {name}")
            try:
                path.relative_to((REPO_ROOT / "reports").resolve())
            except ValueError as exc:
                raise ValueError("target batch output must be inside reports") from exc
            if require_batch_outputs:
                if name == "run_dir" and not path.is_dir():
                    raise ValueError(f"target batch run directory is missing: {batch_id}")
                if name != "run_dir" and not path.is_file():
                    raise ValueError(f"target batch trace is missing: {batch_id}")
    output = _absolute_path(registration["output_dir"], label="target output")
    try:
        output.relative_to((REPO_ROOT / "reports").resolve())
    except ValueError as exc:
        raise ValueError("target output must be inside reports") from exc
    return copy.deepcopy(dict(registration))


def validate_source_binding(source_commit: str) -> None:
    commit = _source_commit(source_commit)
    common = {
        "cwd": str(REPO_ROOT),
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "check": False,
    }
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, "HEAD"], **common
    )
    if ancestor.returncode != 0:
        raise ValueError("target source commit is not an ancestor")
    for relative in SOURCE_BOUND_PATHS:
        present = subprocess.run(
            ["git", "cat-file", "-e", f"{commit}:{relative}"], **common
        )
        if present.returncode != 0:
            raise ValueError(f"target source is absent: {relative}")
    unchanged = subprocess.run(
        ["git", "diff", "--quiet", commit, "--", *SOURCE_BOUND_PATHS], **common
    )
    if unchanged.returncode != 0:
        raise ValueError("target sources differ from registration")


def require_committed_file(path: Path, *, label: str) -> None:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"{label} must be inside the repository") from exc
    common = {
        "cwd": str(REPO_ROOT),
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "check": False,
    }
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", relative], **common
    )
    unchanged = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", relative], **common
    )
    if tracked.returncode != 0 or unchanged.returncode != 0:
        raise ValueError(f"{label} must be committed and unchanged")


def preflight_target_registration(registration_path: Path) -> dict[str, Any]:
    require_committed_file(registration_path, label="target registration")
    registration = validate_target_registration(
        json.loads(registration_path.read_text(encoding="ascii")),
        require_batch_outputs=False,
    )
    validate_source_binding(registration["source_commit"])
    batch_statuses = []
    for batch in registration["batches"]:
        load_live_shadow_registration(
            batch["shadow_registration"]["path"],
            repo_root=REPO_ROOT,
            require_committed=True,
        )
        batch_statuses.append(
            {
                "batch_id": batch["batch_id"],
                **batch_recovery_status(
                    Path(batch["run_dir"]),
                    expected_run_count=int(batch["expected_run_count"]),
                ),
            }
        )
    output = Path(registration["output_dir"])
    collision_paths = (
        output,
        output.with_name(f".{output.name}.staging"),
        output.parent / f".{registration['experiment_id']}.started.json",
        output.parent / f"{output.name}_failure.json",
    )
    collisions = [str(path) for path in collision_paths if path.exists()]
    if collisions:
        raise ValueError("target publication output already exists")
    return {
        "schema_version": "combat-rl-action-relative-live-context-target-preflight-v1",
        "experiment_id": registration["experiment_id"],
        "source_commit": registration["source_commit"],
        "registration_sha256": sha256_file(registration_path),
        "batch_statuses": batch_statuses,
        "output_collision_count": 0,
        "authority": copy.deepcopy(TARGET_AUTHORITY),
        "passed": True,
    }


def _validate_bound_file(
    binding: Any, *, expected_path: Path | None, label: str
) -> Path:
    if not isinstance(binding, Mapping) or set(binding) != {
        "path",
        "sha256",
        "size_bytes",
    }:
        raise ValueError(f"target {label} binding differs")
    path = _absolute_path(binding["path"], label=label)
    if expected_path is not None and path != expected_path.resolve():
        raise ValueError(f"target {label} path differs")
    digest = _sha256(binding["sha256"], label=label)
    size = _integer(binding["size_bytes"], label=f"{label} size")
    if not path.is_file() or path.stat().st_size != size or sha256_file(path) != digest:
        raise ValueError(f"target {label} binding differs")
    return path


def build_target_artifact(registration: Mapping[str, Any]) -> dict[str, Any]:
    validated = validate_target_registration(
        registration, require_batch_outputs=True
    )
    all_rows: list[dict[str, Any]] = []
    all_runs: list[dict[str, Any]] = []
    batch_summaries: list[dict[str, Any]] = []
    aggregate_exclusions: Counter[str] = Counter()
    for batch in validated["batches"]:
        events = load_jsonl(Path(batch["trace_path"]), label="shadow trace")
        shadow = load_live_shadow_registration(
            batch["shadow_registration"]["path"],
            repo_root=REPO_ROOT,
            require_committed=True,
        )
        readiness = shadow_summary.summarize_events(events, shadow)
        target_readiness = target_shadow_conditions(readiness)
        if not all(target_readiness.values()):
            raise ValueError("target shadow trace readiness failed")
        decision_rows = load_jsonl(
            Path(batch["decision_trace_path"]), label="decision trace"
        )
        runs = load_completed_runs(Path(batch["run_dir"]))
        if len(runs) != int(batch["expected_run_count"]):
            raise ValueError("target batch completed run count differs")
        rows, exclusions = extract_target_rows(
            events=events,
            decision_rows=decision_rows,
            completed_runs=runs,
            batch_id=str(batch["batch_id"]),
            maximum_join_delta_seconds=float(
                validated["target_contract"]["maximum_join_delta_seconds"]
            ),
        )
        all_rows.extend(rows)
        all_runs.extend(runs)
        aggregate_exclusions.update(exclusions)
        batch_summaries.append(
            {
                "batch_id": batch["batch_id"],
                "completed_run_count": len(runs),
                "target_row_count": len(rows),
                "late_target_row_count": sum(
                    23 <= int(row["floor"]) <= 34 for row in rows
                ),
                "exclusion_reason_counts": exclusions,
                "trace_sha256": sha256_file(Path(batch["trace_path"])),
                "decision_trace_sha256": sha256_file(
                    Path(batch["decision_trace_path"])
                ),
                "run_inventory_sha256": hashlib.sha256(
                    _canonical_json_bytes(runs)
                ).hexdigest(),
                "target_identity_sha256": context_target_identity(rows),
                "shadow_readiness": readiness,
                "target_shadow_conditions": target_readiness,
            }
        )
    sufficiency = validate_target_sufficiency(
        all_rows,
        completed_runs=all_runs,
        development_run_seeds=set(validated["development_run_seeds"]),
        expected_run_count=int(
            validated["target_contract"]["expected_run_count"]
        ),
        minimum_row_count=int(
            validated["target_contract"]["minimum_row_count"]
        ),
        minimum_late_row_count=int(
            validated["target_contract"]["minimum_late_row_count"]
        ),
        unjoined_eligible_count=aggregate_exclusions[
            "eligible_decision_state_join_missing"
        ],
        maximum_unjoined_eligible_count=int(
            validated["target_contract"]["maximum_unjoined_eligible_count"]
        ),
        maximum_unjoined_eligible_fraction=float(
            validated["target_contract"]["maximum_unjoined_eligible_fraction"]
        ),
    )
    return {
        "schema_version": TARGET_SCHEMA,
        "experiment_id": validated["experiment_id"],
        "source_commit": validated["source_commit"],
        "rows": all_rows,
        "completed_runs": all_runs,
        "batch_summaries": batch_summaries,
        "exclusion_reason_counts": dict(sorted(aggregate_exclusions.items())),
        "sufficiency": sufficiency,
        "target_identity_sha256": context_target_identity(all_rows),
        "authority": copy.deepcopy(TARGET_AUTHORITY),
    }


def publish_registered_target(registration_path: Path) -> dict[str, Any]:
    require_committed_file(registration_path, label="target registration")
    registration = validate_target_registration(
        json.loads(registration_path.read_text(encoding="ascii")),
        require_batch_outputs=True,
    )
    validate_source_binding(registration["source_commit"])
    output = Path(registration["output_dir"])
    staging = output.with_name(f".{output.name}.staging")
    started_path = output.parent / f".{registration['experiment_id']}.started.json"
    failure_path = output.parent / f"{output.name}_failure.json"
    if output.exists() or staging.exists() or started_path.exists() or failure_path.exists():
        raise ValueError("target output, staging, receipt, or failure already exists")
    started = {
        "schema_version": "combat-rl-action-relative-live-context-target-started-v1",
        "experiment_id": registration["experiment_id"],
        "source_commit": registration["source_commit"],
        "started_unix": time.time(),
    }
    started_path.write_bytes(_canonical_json_bytes(started))
    try:
        target = build_target_artifact(registration)
        report = {
            "schema_version": REPORT_SCHEMA,
            "experiment_id": registration["experiment_id"],
            "source_commit": registration["source_commit"],
            "target_identity_sha256": target["target_identity_sha256"],
            "batch_summaries": target["batch_summaries"],
            "sufficiency": target["sufficiency"],
            "decision": (
                "target_ready_for_one_aligned_support_evaluation"
                if target["sufficiency"]["all_conditions_passed"]
                else "target_insufficient_close_without_support_evaluation"
            ),
            "authority": copy.deepcopy(TARGET_AUTHORITY),
        }
        staging.mkdir(parents=True, exist_ok=False)
        (staging / "target.json").write_bytes(_canonical_json_bytes(target))
        (staging / "report.json").write_bytes(_canonical_json_bytes(report))
        shutil.copyfile(registration_path, staging / "registration.json")
        shutil.copyfile(started_path, staging / "started_receipt.json")
        manifest = {
            "schema_version": MANIFEST_SCHEMA,
            "experiment_id": registration["experiment_id"],
            "source_commit": registration["source_commit"],
            "decision": report["decision"],
            "artifacts": {
                path.name: {
                    "sha256": sha256_file(path),
                    "size_bytes": path.stat().st_size,
                }
                for path in sorted(staging.iterdir())
                if path.is_file() and path.name != "manifest.json"
            },
        }
        (staging / "manifest.json").write_bytes(_canonical_json_bytes(manifest))
        stored = sum(path.stat().st_size for path in staging.iterdir() if path.is_file())
        if stored > int(registration["resource_limits"]["maximum_output_bytes"]):
            raise RuntimeError("target output exceeds storage limit")
        os.replace(staging, output)
        return report
    except BaseException as exc:
        if staging.exists():
            shutil.rmtree(staging)
        failure = {
            "schema_version": "combat-rl-action-relative-live-context-target-failure-v1",
            "experiment_id": registration["experiment_id"],
            "source_commit": registration["source_commit"],
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "model_fitting_started": False,
            "training_started": False,
        }
        failure_path.write_bytes(_canonical_json_bytes(failure))
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--registration", type=Path)
    mode.add_argument("--preflight-registration", type=Path)
    mode.add_argument("--trace", type=Path)
    parser.add_argument("--decision-trace", type=Path)
    parser.add_argument("--runs", type=Path)
    parser.add_argument("--batch-id")
    args = parser.parse_args()
    if args.preflight_registration is not None:
        report = preflight_target_registration(args.preflight_registration)
        print(json.dumps(report, sort_keys=True))
        return
    elif args.registration is not None:
        report = publish_registered_target(args.registration)
        print(json.dumps({"decision": report["decision"]}, sort_keys=True))
        return
    if args.decision_trace is None or args.runs is None or not args.batch_id:
        parser.error("--trace requires --decision-trace, --runs, and --batch-id")
    completed_runs = load_completed_runs(args.runs)
    rows, exclusions = extract_target_rows(
        events=load_jsonl(args.trace, label="shadow trace"),
        decision_rows=load_jsonl(args.decision_trace, label="decision trace"),
        completed_runs=completed_runs,
        batch_id=args.batch_id,
    )
    print(
        json.dumps(
            {
                "target_row_count": len(rows),
                "target_identity_sha256": context_target_identity(rows),
                "exclusion_reason_counts": exclusions,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
