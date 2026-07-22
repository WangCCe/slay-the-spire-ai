"""Read-only parsing primitives for adaptive-route audit evidence."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from math import isfinite
import os
from pathlib import Path
import re
import sys
from typing import Sequence, TypeAlias


ADAPTIVE_KEYS = (
    "outcome", "character", "act", "floor", "state_valid", "hp", "hp_pct",
    "deck", "potion", "relic", "elite_seen", "last_rest_floor",
    "candidate_pair", "conservative_candidate", "aggressive_candidate",
    "minimum_elites", "added_elites", "fallback_candidate", "budget",
    "selected", "reasons",
)

_CANDIDATE_KEYS = (
    "mode",
    "start_y",
    "symbols",
    "elite_count",
    "elite_floors",
    "recovery_before",
    "recovery_after",
)
_ROUTE_SYMBOLS = frozenset(("M", "T", "?", "$", "R", "E"))
_RUN_SYMBOLS = _ROUTE_SYMBOLS | frozenset(("B",))
_TIMESTAMPED_INFO = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{1,6})"
    r"\s+-\s+INFO\s+-\s+(?P<message>.*)$"
)
_GAME_BOUNDARY = re.compile(
    r"^Starting game #(?P<game_number>[1-9]\d*)"
    r"(?: as PlayerClass\.(?P<player_class>[A-Z][A-Z0-9_]*))?$"
)
_CANONICAL_PAYLOAD = re.compile(r"^[^\s]+(?: [^\s]+)*$")
_CHARACTER = re.compile(r"^[A-Z][A-Z0-9_]*$")
_HP = re.compile(r"^(?P<current>0|[1-9]\d*)/(?P<maximum>[1-9]\d*)$")
_HP_PCT = re.compile(r"^[01]\.\d{6}$")
_MICROSECONDS_PER_SECOND = Decimal(1_000_000)
_MAX_NORMALIZED_MICROSECONDS = 2**63 - 1
_MAP_MAX_Y = 14
_UNIX_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


class EvidenceError(ValueError):
    """Evidence cannot be parsed without making an unsupported inference."""

    def __init__(
        self,
        message: str,
        source_path: Path | None = None,
        line_number: int | None = None,
    ) -> None:
        if source_path is not None:
            message = f"{source_path}:{line_number}: {message}"
        super().__init__(message)


@dataclass(frozen=True)
class Candidate:
    mode: str
    start_y: int
    symbols: tuple[str, ...]
    elite_count: int
    elite_floors: tuple[int, ...]
    recovery_before: int | None
    recovery_after: int | None


@dataclass(frozen=True)
class AdaptiveOccurrence:
    game_number: int
    source_path: Path
    line_number: int
    timestamp: datetime
    unix_time: Decimal
    payload: str
    fields: dict[str, str]
    conservative: Candidate | None
    aggressive: Candidate | None

    @property
    def unix_time_us(self) -> int:
        return _seconds_to_microseconds(self.unix_time, "adaptive unix_time")


@dataclass(frozen=True)
class AdaptiveRecord:
    game_number: int
    payload: str
    occurrences: tuple[AdaptiveOccurrence, ...]


Coordinate: TypeAlias = tuple[int, int]
CoordinatePath: TypeAlias = tuple[Coordinate, ...]


@dataclass(frozen=True)
class GraphNode:
    symbol: str
    children: tuple[Coordinate, ...]


@dataclass(frozen=True)
class TracePath:
    choice: int
    coordinates: CoordinatePath
    symbols: tuple[str, ...]


@dataclass(frozen=True)
class TraceMapDecision:
    unix_time: Decimal
    act: int
    floor: int
    current_node: Coordinate
    next_nodes: tuple[Coordinate, ...]
    graph: tuple[tuple[Coordinate, GraphNode], ...]
    paths: tuple[TracePath, ...]
    action_node: Coordinate
    semantic_fingerprint: str

    @property
    def unix_time_us(self) -> int:
        return _seconds_to_microseconds(self.unix_time, "decision unix_time")


@dataclass(frozen=True)
class JoinedOccurrence:
    occurrence: AdaptiveOccurrence
    decision: TraceMapDecision
    delta_seconds: Decimal

    @property
    def delta_us(self) -> int:
        return _seconds_to_microseconds(self.delta_seconds, "join delta")


@dataclass(frozen=True)
class JoinedRecord:
    record: AdaptiveRecord
    occurrences: tuple[JoinedOccurrence, ...]
    decision: TraceMapDecision


@dataclass(frozen=True)
class Divergence:
    index: int
    map_y: int
    entered_floor: int
    conservative: Coordinate
    aggressive: Coordinate


@dataclass(frozen=True)
class CandidatePairEvidence:
    conservative_matches: tuple[CoordinatePath, ...]
    aggressive_matches: tuple[CoordinatePath, ...]
    conservative_coordinate_sets: tuple[tuple[Coordinate, ...], ...]
    aggressive_coordinate_sets: tuple[tuple[Coordinate, ...], ...]
    conservative_match_count: int
    aggressive_match_count: int
    conservative_path: CoordinatePath | None
    aggressive_path: CoordinatePath | None
    conservative_immediate: Coordinate | None
    aggressive_immediate: Coordinate | None
    immediate_classification: str
    first_divergence: Divergence | None


@dataclass(frozen=True)
class RunEvidence:
    source_path: Path
    path_per_floor: tuple[str | None, ...]
    floor_reached: int | None
    victory: bool | None


def _parse_nonnegative_integer(value: str, label: str) -> int:
    if not re.fullmatch(r"0|[1-9]\d*", value):
        raise EvidenceError(f"{label} must be a non-negative integer")
    return int(value)


def _parse_optional_nonnegative_integer(value: str, label: str) -> int | None:
    if value == "none":
        return None
    return _parse_nonnegative_integer(value, label)


def _parse_positive_integer(value: str, label: str) -> int:
    parsed = _parse_nonnegative_integer(value, label)
    if parsed < 1:
        raise EvidenceError(f"{label} must be at least one")
    return parsed


def _candidate_derived_fields(
    symbols: tuple[str, ...], start_y: int
) -> tuple[tuple[int, ...], int | None, int | None]:
    elite_indexes = tuple(index for index, symbol in enumerate(symbols) if symbol == "E")
    elite_floors = tuple(start_y + index + 1 for index in elite_indexes)
    if not elite_indexes:
        return elite_floors, None, None
    first_elite_index = elite_indexes[0]
    prior_rests = [
        index for index, symbol in enumerate(symbols[:first_elite_index]) if symbol == "R"
    ]
    later_rests = [
        index
        for index, symbol in enumerate(symbols[first_elite_index + 1:], first_elite_index + 1)
        if symbol == "R"
    ]
    return (
        elite_floors,
        first_elite_index - prior_rests[-1] if prior_rests else None,
        later_rests[0] - first_elite_index if later_rests else None,
    )


def _validate_candidate_extent(candidate: Candidate) -> None:
    end_y = candidate.start_y + len(candidate.symbols) - 1
    if end_y > _MAP_MAX_Y:
        raise EvidenceError("candidate extent must stay within map y 0..14")


def _validate_candidate_pair_geometry(
    conservative: Candidate, aggressive: Candidate
) -> None:
    _validate_candidate_extent(conservative)
    _validate_candidate_extent(aggressive)
    if conservative.start_y != aggressive.start_y:
        raise EvidenceError("complete candidate pair must share start_y")
    if len(conservative.symbols) != len(aggressive.symbols):
        raise EvidenceError("complete candidate pair must share route extent")


def _parse_candidate(value: str) -> Candidate | None:
    if value == "unavailable":
        return None

    tokens = value.split(",")
    keys = tuple(token.partition(":")[0] for token in tokens)
    if keys != _CANDIDATE_KEYS or any(":" not in token for token in tokens):
        raise EvidenceError("candidate fields do not match the ordered contract")
    values = dict(token.split(":", 1) for token in tokens)
    if any(not field_value for field_value in values.values()):
        raise EvidenceError("candidate fields must not be empty")

    mode = values["mode"]
    if mode not in {"conservative", "aggressive"}:
        raise EvidenceError("candidate mode is invalid")
    start_y = _parse_nonnegative_integer(values["start_y"], "candidate start_y")
    symbols = tuple(values["symbols"].split("/"))
    if not symbols or any(symbol not in _ROUTE_SYMBOLS for symbol in symbols):
        raise EvidenceError("candidate route symbols are invalid")
    elite_count = _parse_nonnegative_integer(values["elite_count"], "candidate elite_count")

    elite_floors_value = values["elite_floors"]
    if elite_floors_value == "none":
        elite_floors = ()
    else:
        elite_floors = tuple(
            _parse_nonnegative_integer(floor, "candidate elite floor")
            for floor in elite_floors_value.split("|")
        )
    expected_elite_floors, expected_recovery_before, expected_recovery_after = (
        _candidate_derived_fields(symbols, start_y)
    )
    if (
        elite_count != len(elite_floors)
        or elite_count != len(expected_elite_floors)
        or elite_floors != expected_elite_floors
    ):
        raise EvidenceError("candidate elite counts do not match its route")

    recovery_before = _parse_optional_nonnegative_integer(
        values["recovery_before"], "candidate recovery_before"
    )
    recovery_after = _parse_optional_nonnegative_integer(
        values["recovery_after"], "candidate recovery_after"
    )
    if (recovery_before, recovery_after) != (
        expected_recovery_before,
        expected_recovery_after,
    ):
        raise EvidenceError("candidate recovery distances do not match its route")

    candidate = Candidate(
        mode=mode,
        start_y=start_y,
        symbols=symbols,
        elite_count=elite_count,
        elite_floors=elite_floors,
        recovery_before=recovery_before,
        recovery_after=recovery_after,
    )
    _validate_candidate_extent(candidate)
    return candidate


def _validate_state_scalars(fields: dict[str, str]) -> None:
    state_keys = ("hp", "hp_pct", "deck", "potion", "relic", "elite_seen", "last_rest_floor")
    if fields["state_valid"] == "false":
        if any(fields[key] != "unavailable" for key in state_keys):
            raise EvidenceError("invalid state must use unavailable state scalars")
        return

    if "unavailable" in (fields[key] for key in state_keys):
        raise EvidenceError("valid state must provide every state scalar")
    hp_match = _HP.fullmatch(fields["hp"])
    if hp_match is None:
        raise EvidenceError("hp must be current/max positive integer form")
    current_hp = int(hp_match.group("current"))
    maximum_hp = int(hp_match.group("maximum"))
    if current_hp > maximum_hp:
        raise EvidenceError("hp current value cannot exceed maximum")
    if _HP_PCT.fullmatch(fields["hp_pct"]) is None:
        raise EvidenceError("hp_pct must have six decimal places")
    hp_pct = float(fields["hp_pct"])
    if hp_pct > 1 or abs(hp_pct - current_hp / maximum_hp) > 0.000001:
        raise EvidenceError("hp_pct does not match hp")
    for key, maximum in (("deck", 7), ("potion", 2), ("relic", 2)):
        if _parse_nonnegative_integer(fields[key], key) > maximum:
            raise EvidenceError(f"{key} must not exceed {maximum}")
    if fields["elite_seen"] not in {"true", "false"}:
        raise EvidenceError("valid state elite_seen must be boolean")
    _parse_optional_nonnegative_integer(fields["last_rest_floor"], "last_rest_floor")


def _validate_fields(
    fields: dict[str, str], conservative: Candidate | None, aggressive: Candidate | None
) -> None:
    if any(not value for value in fields.values()):
        raise EvidenceError("adaptive payload fields must not be empty")
    if fields["outcome"] not in {
        "success",
        "forced",
        "unsupported",
        "candidate_generation_failed",
    }:
        raise EvidenceError("adaptive outcome is invalid")
    if fields["state_valid"] not in {"true", "false"}:
        raise EvidenceError("adaptive state_valid must be boolean")
    if fields["character"] == "unavailable":
        if fields["state_valid"] == "true":
            raise EvidenceError("valid state character must be available")
    elif _CHARACTER.fullmatch(fields["character"]) is None:
        raise EvidenceError("adaptive character is invalid")
    if fields["act"] == "unavailable":
        if fields["state_valid"] == "true":
            raise EvidenceError("valid state act must be available")
    else:
        _parse_positive_integer(fields["act"], "act")
    if fields["floor"] != "unavailable":
        _parse_nonnegative_integer(fields["floor"], "floor")
    budget = _parse_nonnegative_integer(fields["budget"], "budget")
    if budget not in {0, 1}:
        raise EvidenceError("budget must be zero or one")
    _validate_state_scalars(fields)
    if fields["candidate_pair"] not in {
        "complete",
        "not_attempted",
        "generation_failed",
    }:
        raise EvidenceError("adaptive candidate_pair is invalid")
    if fields["selected"] not in {"conservative", "aggressive"}:
        raise EvidenceError("adaptive selected mode is invalid")
    if fields["state_valid"] == "false" and (
        budget != 0 or fields["selected"] != "conservative"
    ):
        raise EvidenceError("invalid state must use zero budget and conservative selection")
    if budget != int(fields["selected"] == "aggressive"):
        raise EvidenceError("budget does not match selected mode")
    outcome = fields["outcome"]
    pair = fields["candidate_pair"]
    if outcome in {"success", "forced"}:
        if pair != "complete" or fields["fallback_candidate"] != "not_used":
            raise EvidenceError("complete outcome contract is invalid")
        if conservative is None or aggressive is None:
            raise EvidenceError("complete candidate pair requires both candidates")
        if conservative.mode != "conservative" or aggressive.mode != "aggressive":
            raise EvidenceError("candidate mode does not match its payload field")
        _validate_candidate_pair_geometry(conservative, aggressive)
        minimum_elites = _parse_nonnegative_integer(fields["minimum_elites"], "minimum_elites")
        added_elites = _parse_nonnegative_integer(fields["added_elites"], "added_elites")
        if minimum_elites != conservative.elite_count:
            raise EvidenceError("minimum_elites does not match conservative candidate")
        if added_elites != aggressive.elite_count - conservative.elite_count:
            raise EvidenceError("added_elites does not match candidate pair")
        if outcome == "forced" and fields["selected"] != "conservative":
            raise EvidenceError("forced outcome must select conservative")
        return
    if conservative is not None or aggressive is not None:
        raise EvidenceError("incomplete candidate pair must not include candidates")
    if fields["minimum_elites"] != "unavailable" or fields["added_elites"] != "unavailable":
        raise EvidenceError("incomplete candidate pair counts must be unavailable")
    if outcome == "unsupported":
        if (
            pair != "not_attempted"
            or fields["fallback_candidate"] != "not_applicable"
            or fields["selected"] != "conservative"
        ):
            raise EvidenceError("unsupported outcome contract is invalid")
        return
    if pair != "generation_failed" or fields["selected"] != "conservative":
        raise EvidenceError("candidate-generation failure contract is invalid")
    fallback = _parse_candidate(fields["fallback_candidate"])
    if fallback is None or fallback.mode != "conservative":
        raise EvidenceError("candidate-generation failure requires conservative fallback")


def parse_adaptive_payload(payload: str) -> tuple[dict[str, str], Candidate | None, Candidate | None]:
    """Parse one complete adaptive-routing payload without accepting reordering."""
    if _CANONICAL_PAYLOAD.fullmatch(payload) is None:
        raise EvidenceError("adaptive payload must use canonical single-space separators")
    tokens = payload.split(" ")
    keys = tuple(token.partition("=")[0] for token in tokens)
    if (
        keys != ADAPTIVE_KEYS
        or any(token.count("=") != 1 for token in tokens)
    ):
        raise EvidenceError("adaptive payload keys do not match the ordered contract")
    fields = dict(token.split("=", 1) for token in tokens)
    conservative = _parse_candidate(fields["conservative_candidate"])
    aggressive = _parse_candidate(fields["aggressive_candidate"])
    _validate_fields(fields, conservative, aggressive)
    return fields, conservative, aggressive


def _validate_paths(paths: Sequence[Path]) -> tuple[Path, ...]:
    if not isinstance(paths, (list, tuple)) or not paths:
        raise EvidenceError("adaptive log paths must be a non-empty ordered list or tuple")
    normalized = tuple(Path(path) for path in paths)
    if len(set(normalized)) != len(normalized):
        raise EvidenceError("adaptive log paths must not repeat a source")
    return normalized


def _validate_utc_offset(utc_offset_hours: float) -> float:
    if isinstance(utc_offset_hours, bool) or not isinstance(utc_offset_hours, (int, float)):
        raise EvidenceError("log UTC offset must be a finite number of hours")
    offset = float(utc_offset_hours)
    if not isfinite(offset) or abs(offset) >= 24:
        raise EvidenceError("log UTC offset must be strictly within 24 hours")
    return offset


def _timestamp_and_message(line: str) -> tuple[datetime, str] | None:
    match = _TIMESTAMPED_INFO.match(line)
    if match is None:
        return None
    try:
        timestamp = datetime.strptime(
            match.group("timestamp"), "%Y-%m-%d %H:%M:%S,%f"
        )
    except ValueError as error:
        raise EvidenceError(
            "timestamped INFO line has an invalid timestamp"
        ) from error
    return timestamp, match.group("message")


def _datetime_to_unix_seconds(timestamp: datetime, offset: timezone) -> Decimal:
    aware = timestamp.replace(tzinfo=offset).astimezone(timezone.utc)
    delta = aware - _UNIX_EPOCH
    microseconds = (
        (delta.days * 24 * 60 * 60 + delta.seconds) * 1_000_000
        + delta.microseconds
    )
    return Decimal(microseconds) / _MICROSECONDS_PER_SECOND


def _source_snapshot(source_path: Path, raw_bytes: bytes) -> dict:
    return {
        "source_path": str(source_path),
        "sha256": sha256(raw_bytes).hexdigest(),
        "byte_count": len(raw_bytes),
        "line_count": len(raw_bytes.splitlines()),
        "record_count": 0,
        "parse_status": "pending",
    }


def load_adaptive_logs(
    paths: Sequence[Path],
    utc_offset_hours: float,
    source_snapshots: list[dict] | None = None,
) -> tuple[list[AdaptiveOccurrence], list[dict]]:
    """Load chronologically ordered adaptive log sources with byte identities."""
    ordered_paths = _validate_paths(paths)
    offset_hours = _validate_utc_offset(utc_offset_hours)
    offset = timezone(timedelta(hours=offset_hours))
    occurrences: list[AdaptiveOccurrence] = []
    sources = [] if source_snapshots is None else source_snapshots
    active_game_number: int | None = None
    previous_game_number: int | None = None

    for source_path in ordered_paths:
        try:
            raw_bytes = source_path.read_bytes()
        except OSError as error:
            raise EvidenceError(f"cannot read UTF-8 adaptive log source: {error}", source_path) from error
        source = _source_snapshot(source_path, raw_bytes)
        sources.append(source)
        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError as error:
            source["parse_status"] = "invalid"
            raise EvidenceError(
                f"cannot read UTF-8 adaptive log source: {error}", source_path
            ) from error

        record_count = 0
        try:
            for line_number, line in enumerate(text.splitlines(), start=1):
                try:
                    parsed = _timestamp_and_message(line)
                except EvidenceError as error:
                    raise EvidenceError(
                        str(error), source_path, line_number
                    ) from error
                if parsed is None:
                    if "[ADAPTIVE_ROUTE]" in line:
                        raise EvidenceError("adaptive record must be a timestamped INFO line", source_path, line_number)
                    continue
                timestamp, message = parsed
                boundary = _GAME_BOUNDARY.fullmatch(message)
                if boundary is not None:
                    game_number = int(boundary.group("game_number"))
                    if previous_game_number is not None and game_number <= previous_game_number:
                        raise EvidenceError("non-monotonic game boundary", source_path, line_number)
                    active_game_number = game_number
                    previous_game_number = game_number
                    continue
                if message.startswith("Starting game #"):
                    raise EvidenceError("invalid game boundary", source_path, line_number)
                if "[ADAPTIVE_ROUTE]" not in message:
                    continue
                prefix = "[ADAPTIVE_ROUTE] "
                if not message.startswith(prefix):
                    raise EvidenceError("adaptive record must be prefixed exactly", source_path, line_number)
                if active_game_number is None:
                    raise EvidenceError("missing game boundary for adaptive record", source_path, line_number)
                payload = message[len(prefix):]
                try:
                    fields, conservative, aggressive = parse_adaptive_payload(payload)
                except EvidenceError as error:
                    raise EvidenceError(str(error), source_path, line_number) from error
                occurrences.append(
                    AdaptiveOccurrence(
                        game_number=active_game_number,
                        source_path=source_path,
                        line_number=line_number,
                        timestamp=timestamp,
                        unix_time=_datetime_to_unix_seconds(timestamp, offset),
                        payload=payload,
                        fields=fields,
                        conservative=conservative,
                        aggressive=aggressive,
                    )
                )
                record_count += 1
        except EvidenceError:
            source["record_count"] = record_count
            source["parse_status"] = "invalid"
            raise
        source["record_count"] = record_count
        source["parse_status"] = "valid"
    return occurrences, sources


def deduplicate_occurrences(
    occurrences: Sequence[AdaptiveOccurrence],
) -> list[AdaptiveRecord]:
    """Collapse repeated callbacks by game and complete payload, retaining provenance."""
    grouped: dict[tuple[int, str], list[AdaptiveOccurrence]] = {}
    for occurrence in occurrences:
        grouped.setdefault((occurrence.game_number, occurrence.payload), []).append(occurrence)
    return [
        AdaptiveRecord(
            game_number=game_number,
            payload=payload,
            occurrences=tuple(group),
        )
        for (game_number, payload), group in grouped.items()
    ]


def _strict_integer(value: object, label: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise EvidenceError(f"{label} must be an integer of at least {minimum}")
    return value


def _decimal_seconds(value: object, label: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise EvidenceError(f"{label} must be a finite number")
    try:
        parsed = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError, OverflowError) as error:
        raise EvidenceError(f"{label} must be a finite number") from error
    if not parsed.is_finite():
        raise EvidenceError(f"{label} must be a finite number")
    return parsed


def _seconds_to_microseconds(value: object, label: str) -> int:
    parsed = _decimal_seconds(value, label)
    maximum_seconds = Decimal(_MAX_NORMALIZED_MICROSECONDS) / _MICROSECONDS_PER_SECOND
    if abs(parsed) > maximum_seconds:
        raise EvidenceError(f"{label} is outside the supported exact range")
    scaled = parsed * _MICROSECONDS_PER_SECOND
    integral = scaled.to_integral_value()
    if scaled != integral:
        raise EvidenceError(f"{label} must have at most microsecond precision")
    return int(integral)


def _strict_number(value: object, label: str) -> Decimal:
    parsed = _decimal_seconds(value, label)
    _seconds_to_microseconds(parsed, label)
    return parsed


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant {value}")


def _strict_json_object(pairs: list[tuple[str, object]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key}")
        result[key] = value
    return result


def _trace_coordinate(
    value: object,
    label: str,
    *,
    require_symbol: bool = False,
    allow_virtual: bool = False,
) -> tuple[Coordinate, str | None]:
    if not isinstance(value, dict):
        raise EvidenceError(f"{label} must be an object")
    x = _strict_integer(value.get("x"), f"{label} x", minimum=-1 if allow_virtual else 0)
    y = _strict_integer(value.get("y"), f"{label} y", minimum=-1 if allow_virtual else 0)
    if y >= 0 and not 0 <= x <= 6:
        raise EvidenceError(f"{label} x must be within the seven-column map")
    if y >= 0 and y > _MAP_MAX_Y:
        raise EvidenceError(f"{label} map y must be within 0..14")
    if y == -1 and not allow_virtual:
        raise EvidenceError(f"{label} cannot be a virtual coordinate")
    if y == -1 and (x != 0 or value.get("symbol") != ""):
        raise EvidenceError(f"{label} must be the canonical virtual map root")
    symbol: str | None = None
    if require_symbol:
        symbol = value.get("symbol")
        if not isinstance(symbol, str):
            raise EvidenceError(f"{label} symbol must be a string")
    return (x, y), symbol


def _parse_graph(value: object) -> tuple[tuple[Coordinate, GraphNode], ...]:
    if not isinstance(value, dict) or not isinstance(value.get("nodes"), list):
        raise EvidenceError("map graph nodes must be a list")
    graph: dict[Coordinate, GraphNode] = {}
    for raw_node in value["nodes"]:
        coordinate, symbol = _trace_coordinate(raw_node, "graph node", require_symbol=True)
        if symbol not in _ROUTE_SYMBOLS:
            raise EvidenceError("graph node symbol is invalid")
        if coordinate in graph:
            raise EvidenceError("map graph contains a duplicate coordinate")
        raw_children = raw_node.get("children")
        if not isinstance(raw_children, list):
            raise EvidenceError("graph node children must be a list")
        children = tuple(
            _trace_coordinate(child, "graph child")[0] for child in raw_children
        )
        if len(set(children)) != len(children):
            raise EvidenceError("graph node contains duplicate children")
        graph[coordinate] = GraphNode(symbol=symbol, children=children)

    for coordinate, node in graph.items():
        for child in node.children:
            if child not in graph:
                raise EvidenceError("graph child does not exist in the map graph")
            if child[1] != coordinate[1] + 1:
                raise EvidenceError("graph children must advance exactly one row")
    return tuple(sorted(graph.items()))


_TRACE_PATH_NODE = re.compile(
    r"^(?P<symbol>[MT?$RE])@(?P<x>[0-6]),(?P<y>0|[1-9]\d?)$"
)


def _parse_trace_paths(
    value: object,
    next_nodes: tuple[Coordinate, ...],
    graph: dict[Coordinate, GraphNode],
) -> tuple[TracePath, ...]:
    if not isinstance(value, list) or not value:
        raise EvidenceError("map decision paths must be a non-empty list")
    paths: list[TracePath] = []
    for raw_path in value:
        if not isinstance(raw_path, dict):
            raise EvidenceError("map decision path must be an object")
        choice = _strict_integer(raw_path.get("choice"), "path choice")
        if choice >= len(next_nodes):
            raise EvidenceError("path choice does not reference an advertised next node")
        label = raw_path.get("label")
        symbols = raw_path.get("nodes")
        if not isinstance(label, str) or not label:
            raise EvidenceError("path label must be a non-empty string")
        if (
            not isinstance(symbols, list)
            or not symbols
            or any(
                not isinstance(symbol, str) or symbol not in _ROUTE_SYMBOLS
                for symbol in symbols
            )
        ):
            raise EvidenceError("path nodes contain invalid route symbols")

        coordinates: list[Coordinate] = []
        label_symbols: list[str] = []
        for part in label.split(" -> "):
            match = _TRACE_PATH_NODE.fullmatch(part)
            if match is None:
                raise EvidenceError("path label does not contain exact map coordinates")
            coordinate = (int(match.group("x")), int(match.group("y")))
            if coordinate[1] > _MAP_MAX_Y:
                raise EvidenceError("path map y must be within 0..14")
            if coordinate not in graph:
                raise EvidenceError("path coordinate does not exist in the map graph")
            if graph[coordinate].symbol != match.group("symbol"):
                raise EvidenceError("path label symbol disagrees with the map graph")
            coordinates.append(coordinate)
            label_symbols.append(match.group("symbol"))

        if tuple(symbols) != tuple(label_symbols):
            raise EvidenceError("path nodes disagree with the coordinate label")
        if coordinates[0] != next_nodes[choice]:
            raise EvidenceError("path does not start at its advertised next node")
        for parent, child in zip(coordinates, coordinates[1:]):
            if child not in graph[parent].children:
                raise EvidenceError("path contains a non-child graph edge")
        paths.append(
            TracePath(
                choice=choice,
                coordinates=tuple(coordinates),
                symbols=tuple(symbols),
            )
        )
    return tuple(paths)


def _reachable_children(
    current_node: Coordinate, graph: dict[Coordinate, GraphNode]
) -> set[Coordinate]:
    if current_node == (0, -1):
        return {coordinate for coordinate in graph if coordinate[1] == 0}
    if current_node not in graph:
        raise EvidenceError("current node does not exist in the map graph")
    return set(graph[current_node].children)


def _semantic_fingerprint(
    *,
    act: int,
    floor: int,
    current_node: Coordinate,
    next_nodes: tuple[Coordinate, ...],
    graph: tuple[tuple[Coordinate, GraphNode], ...],
    paths: tuple[TracePath, ...],
    action_node: Coordinate,
) -> str:
    semantic = {
        "act": act,
        "floor": floor,
        "current_node": current_node,
        "next_nodes": sorted(next_nodes),
        "graph": [
            {
                "coordinate": coordinate,
                "symbol": node.symbol,
                "children": sorted(node.children),
            }
            for coordinate, node in graph
        ],
        "paths": sorted(
            (path.coordinates, path.symbols) for path in paths
        ),
        "action_node": action_node,
    }
    canonical = json.dumps(semantic, sort_keys=True, separators=(",", ":"))
    return sha256(canonical.encode("utf-8")).hexdigest()


def _parse_trace_map_decision(row: dict) -> TraceMapDecision:
    unix_time = _strict_number(row.get("unix_time"), "decision unix_time")
    act = _strict_integer(row.get("act"), "decision act", minimum=1)
    floor = _strict_integer(row.get("floor"), "decision floor")
    if row.get("screen_type") != "ScreenType.MAP":
        raise EvidenceError("map decision screen_type is invalid")

    screen = row.get("screen")
    if not isinstance(screen, dict) or screen.get("type") != "ScreenType.MAP":
        raise EvidenceError("map decision screen snapshot is invalid")
    current_node, current_symbol = _trace_coordinate(
        screen.get("current_node"),
        "current node",
        require_symbol=True,
        allow_virtual=True,
    )
    graph_items = _parse_graph(screen.get("map"))
    graph = dict(graph_items)
    if current_node[1] >= 0:
        if current_node not in graph:
            raise EvidenceError("current node does not exist in the map graph")
        if graph[current_node].symbol != current_symbol:
            raise EvidenceError("current-node symbol disagrees with the map graph")

    raw_next_nodes = screen.get("next_nodes")
    if not isinstance(raw_next_nodes, list) or not raw_next_nodes:
        raise EvidenceError("map decision next_nodes must be a non-empty list")
    next_nodes: list[Coordinate] = []
    for raw_next_node in raw_next_nodes:
        coordinate, symbol = _trace_coordinate(
            raw_next_node, "next node", require_symbol=True
        )
        if coordinate not in graph:
            raise EvidenceError("next node does not exist in the map graph")
        if graph[coordinate].symbol != symbol:
            raise EvidenceError("next-node symbol disagrees with the map graph")
        next_nodes.append(coordinate)
    next_node_tuple = tuple(next_nodes)
    if len(set(next_node_tuple)) != len(next_node_tuple):
        raise EvidenceError("map decision contains duplicate next nodes")

    paths = _parse_trace_paths(screen.get("paths"), next_node_tuple, graph)
    action = row.get("action")
    if not isinstance(action, dict) or action.get("type") != "ChooseMapNodeAction":
        raise EvidenceError("map decision action must be ChooseMapNodeAction")
    choice_index = _strict_integer(action.get("choice_index"), "action choice_index")
    if choice_index >= len(next_node_tuple):
        raise EvidenceError("action choice_index is outside advertised next nodes")
    action_node, action_symbol = _trace_coordinate(
        action.get("node"), "action node", require_symbol=True
    )
    if action_node not in graph or graph[action_node].symbol != action_symbol:
        raise EvidenceError("action node disagrees with the map graph")
    if action_node not in set(next_node_tuple):
        raise EvidenceError("action node is not advertised by next_nodes")
    if next_node_tuple[choice_index] != action_node:
        raise EvidenceError("action choice_index does not identify its advertised node")
    if action_node not in _reachable_children(current_node, graph):
        raise EvidenceError("action node is not a reachable child of the current node")

    return TraceMapDecision(
        unix_time=unix_time,
        act=act,
        floor=floor,
        current_node=current_node,
        next_nodes=next_node_tuple,
        graph=graph_items,
        paths=paths,
        action_node=action_node,
        semantic_fingerprint=_semantic_fingerprint(
            act=act,
            floor=floor,
            current_node=current_node,
            next_nodes=next_node_tuple,
            graph=graph_items,
            paths=paths,
            action_node=action_node,
        ),
    )


def load_decision_trace(
    path: Path, source_snapshots: list[dict] | None = None
) -> tuple[list[TraceMapDecision], dict]:
    """Load strict JSONL and retain only node-selection MAP actions for joins."""
    source_path = Path(path)
    try:
        raw_bytes = source_path.read_bytes()
    except OSError as error:
        raise EvidenceError(
            f"cannot read UTF-8 decision trace source: {error}", source_path
        ) from error
    source = _source_snapshot(source_path, raw_bytes)
    if source_snapshots is not None:
        source_snapshots.append(source)
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        source["parse_status"] = "invalid"
        raise EvidenceError(
            f"cannot read UTF-8 decision trace source: {error}", source_path
        ) from error

    decisions: list[TraceMapDecision] = []
    record_count = 0
    map_record_count = 0
    node_action_record_count = 0
    boss_action_record_count = 0
    try:
        for line_number, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            record_count += 1
            try:
                row = json.loads(
                    line,
                    parse_float=Decimal,
                    parse_constant=_reject_json_constant,
                    object_pairs_hook=_strict_json_object,
                )
            except (json.JSONDecodeError, ValueError, InvalidOperation) as error:
                detail = error.msg if isinstance(error, json.JSONDecodeError) else str(error)
                raise EvidenceError(
                    f"malformed decision trace JSON: {detail}",
                    source_path,
                    line_number,
                ) from error
            if not isinstance(row, dict):
                raise EvidenceError(
                    "decision trace row must be an object", source_path, line_number
                )
            if row.get("screen_type") != "ScreenType.MAP":
                continue
            map_record_count += 1
            action = row.get("action")
            action_type = action.get("type") if isinstance(action, dict) else None
            if action_type == "ChooseMapBossAction":
                boss_action_record_count += 1
                continue
            if action_type != "ChooseMapNodeAction":
                raise EvidenceError(
                    "MAP row action must be a node or boss action",
                    source_path,
                    line_number,
                )
            try:
                decisions.append(_parse_trace_map_decision(row))
            except EvidenceError as error:
                raise EvidenceError(str(error), source_path, line_number) from error
            node_action_record_count += 1
    except EvidenceError:
        source.update(
            {
                "record_count": record_count,
                "map_record_count": map_record_count,
                "node_action_record_count": node_action_record_count,
                "boss_action_record_count": boss_action_record_count,
                "parse_status": "invalid",
            }
        )
        raise
    source.update(
        {
            "record_count": record_count,
            "map_record_count": map_record_count,
            "node_action_record_count": node_action_record_count,
            "boss_action_record_count": boss_action_record_count,
            "parse_status": "valid",
        }
    )
    return decisions, source


def _validate_join_tolerance(max_join_seconds: float) -> int:
    try:
        tolerance_us = _seconds_to_microseconds(
            max_join_seconds, "join tolerance"
        )
    except EvidenceError as error:
        raise EvidenceError("join tolerance must be a finite non-negative number") from error
    if tolerance_us < 0:
        raise EvidenceError("join tolerance must be a finite non-negative number")
    return tolerance_us


def join_occurrences(
    records: Sequence[AdaptiveRecord],
    trace_rows: Sequence[TraceMapDecision],
    max_join_seconds: float,
) -> list[JoinedRecord]:
    """Join every source occurrence before accepting semantic deduplication."""
    tolerance_us = _validate_join_tolerance(max_join_seconds)
    joined_records: list[JoinedRecord] = []
    for record in records:
        if not record.occurrences:
            raise EvidenceError("adaptive record has no source occurrences")
        joined_occurrences: list[JoinedOccurrence] = []
        for occurrence in record.occurrences:
            act_value = occurrence.fields.get("act")
            floor_value = occurrence.fields.get("floor")
            if act_value is None or not re.fullmatch(r"[1-9]\d*", act_value):
                raise EvidenceError(
                    "adaptive occurrence has no joinable act",
                    occurrence.source_path,
                    occurrence.line_number,
                )
            if floor_value is None or not re.fullmatch(r"0|[1-9]\d*", floor_value):
                raise EvidenceError(
                    "adaptive occurrence has no joinable floor",
                    occurrence.source_path,
                    occurrence.line_number,
                )
            act = int(act_value)
            floor = int(floor_value)
            same_state = [
                decision
                for decision in trace_rows
                if decision.act == act and decision.floor == floor
            ]
            if not same_state:
                raise EvidenceError(
                    "missing decision-trace join for adaptive occurrence",
                    occurrence.source_path,
                    occurrence.line_number,
                )
            candidates = [
                (abs(decision.unix_time_us - occurrence.unix_time_us), decision)
                for decision in same_state
            ]
            bounded = [
                candidate for candidate in candidates if candidate[0] <= tolerance_us
            ]
            if not bounded:
                raise EvidenceError(
                    "nearest decision-trace row is outside join tolerance",
                    occurrence.source_path,
                    occurrence.line_number,
                )
            bounded.sort(key=lambda candidate: candidate[0])
            nearest_delta, nearest = bounded[0]
            if len(bounded) > 1 and bounded[1][0] == nearest_delta:
                raise EvidenceError(
                    "tied nearest decision-trace join for adaptive occurrence",
                    occurrence.source_path,
                    occurrence.line_number,
                )
            joined_occurrences.append(
                JoinedOccurrence(
                    occurrence=occurrence,
                    decision=nearest,
                    delta_seconds=(
                        Decimal(nearest_delta) / _MICROSECONDS_PER_SECOND
                    ),
                )
            )

        fingerprints = {
            joined.decision.semantic_fingerprint for joined in joined_occurrences
        }
        if len(fingerprints) != 1:
            first = record.occurrences[0]
            raise EvidenceError(
                "duplicate occurrences disagree on joined map decision semantics",
                first.source_path,
                first.line_number,
            )
        canonical_decision = joined_occurrences[0].decision
        joined_records.append(
            JoinedRecord(
                record=record,
                occurrences=tuple(joined_occurrences),
                decision=canonical_decision,
            )
        )
    return joined_records


def matching_candidate_paths(
    candidate: Candidate, decision: TraceMapDecision
) -> tuple[CoordinatePath, ...]:
    """Enumerate every reachable graph path matching the exact candidate symbols."""
    _validate_candidate_extent(candidate)
    graph = dict(decision.graph)
    reachable = _reachable_children(decision.current_node, graph)
    starts = [
        coordinate
        for coordinate in decision.next_nodes
        if coordinate in reachable and coordinate[1] == candidate.start_y
    ]
    matches: set[CoordinatePath] = set()

    def walk(
        coordinate: Coordinate,
        symbol_index: int,
        coordinates: CoordinatePath,
    ) -> None:
        node = graph[coordinate]
        if node.symbol != candidate.symbols[symbol_index]:
            return
        next_coordinates = coordinates + (coordinate,)
        if symbol_index == len(candidate.symbols) - 1:
            matches.add(next_coordinates)
            return
        for child in node.children:
            walk(child, symbol_index + 1, next_coordinates)

    for start in starts:
        walk(start, 0, ())
    return tuple(sorted(matches))


def _coordinate_sets(
    paths: tuple[CoordinatePath, ...], candidate_length: int
) -> tuple[tuple[Coordinate, ...], ...]:
    if not paths:
        return ()
    return tuple(
        tuple(sorted({path[index] for path in paths}))
        for index in range(candidate_length)
    )


def _provable_first_divergence(
    conservative_sets: tuple[tuple[Coordinate, ...], ...],
    aggressive_sets: tuple[tuple[Coordinate, ...], ...],
) -> Divergence | None:
    prefix_is_singleton = True
    for index, (conservative_set, aggressive_set) in enumerate(
        zip(conservative_sets, aggressive_sets)
    ):
        if len(conservative_set) != 1 or len(aggressive_set) != 1:
            prefix_is_singleton = False
            continue
        conservative = conservative_set[0]
        aggressive = aggressive_set[0]
        if conservative != aggressive:
            if not prefix_is_singleton:
                return None
            if conservative[1] != aggressive[1]:
                return None
            return Divergence(
                index=index,
                map_y=conservative[1],
                entered_floor=conservative[1] + 1,
                conservative=conservative,
                aggressive=aggressive,
            )
    return None


def classify_candidate_pair(joined_record: JoinedRecord) -> CandidatePairEvidence:
    """Classify candidate coordinates without selecting through graph ambiguity."""
    occurrence = joined_record.record.occurrences[0]
    conservative = occurrence.conservative
    aggressive = occurrence.aggressive
    if conservative is None or aggressive is None:
        raise EvidenceError("candidate classification requires a complete candidate pair")
    _validate_candidate_pair_geometry(conservative, aggressive)

    conservative_matches = matching_candidate_paths(conservative, joined_record.decision)
    aggressive_matches = matching_candidate_paths(aggressive, joined_record.decision)
    conservative_sets = _coordinate_sets(
        conservative_matches, len(conservative.symbols)
    )
    aggressive_sets = _coordinate_sets(aggressive_matches, len(aggressive.symbols))
    conservative_immediate = (
        conservative_sets[0][0]
        if conservative_sets and len(conservative_sets[0]) == 1
        else None
    )
    aggressive_immediate = (
        aggressive_sets[0][0]
        if aggressive_sets and len(aggressive_sets[0]) == 1
        else None
    )
    if conservative_immediate is None or aggressive_immediate is None:
        immediate_classification = "ambiguous"
    elif conservative_immediate == aggressive_immediate:
        immediate_classification = "same"
    else:
        immediate_classification = "different"

    selected = occurrence.fields["selected"]
    selected_sets = conservative_sets if selected == "conservative" else aggressive_sets
    if selected_sets and joined_record.decision.action_node not in set(selected_sets[0]):
        raise EvidenceError("selected candidate contradicts joined action")

    return CandidatePairEvidence(
        conservative_matches=conservative_matches,
        aggressive_matches=aggressive_matches,
        conservative_coordinate_sets=conservative_sets,
        aggressive_coordinate_sets=aggressive_sets,
        conservative_match_count=len(conservative_matches),
        aggressive_match_count=len(aggressive_matches),
        conservative_path=(
            conservative_matches[0] if len(conservative_matches) == 1 else None
        ),
        aggressive_path=(
            aggressive_matches[0] if len(aggressive_matches) == 1 else None
        ),
        conservative_immediate=conservative_immediate,
        aggressive_immediate=aggressive_immediate,
        immediate_classification=immediate_classification,
        first_divergence=_provable_first_divergence(
            conservative_sets, aggressive_sets
        ),
    )


def _validate_ordered_sources(
    paths: Sequence[Path], label: str
) -> tuple[Path, ...]:
    if not isinstance(paths, (list, tuple)) or not paths:
        raise EvidenceError(f"{label} paths must be a non-empty ordered list or tuple")
    ordered = tuple(Path(path) for path in paths)
    for index, source_path in enumerate(ordered):
        for prior_path in ordered[:index]:
            if _paths_share_source(
                source_path, prior_path, f"ordered {label} identity"
            ):
                raise EvidenceError(
                    f"ordered {label} sources alias one physical file"
                )
    return ordered


def load_runs(
    paths: Sequence[Path], source_snapshots: list[dict] | None = None
) -> tuple[list[RunEvidence], list[dict]]:
    """Load ordered run records without inferring or rewriting path symbols."""
    ordered_paths = _validate_ordered_sources(paths, "run")
    runs: list[RunEvidence] = []
    sources = [] if source_snapshots is None else source_snapshots
    for source_path in ordered_paths:
        try:
            raw_bytes = source_path.read_bytes()
        except OSError as error:
            raise EvidenceError(
                f"cannot read strict UTF-8 run record: {error}", source_path
            ) from error
        source = _source_snapshot(source_path, raw_bytes)
        sources.append(source)
        try:
            text = raw_bytes.decode("utf-8")
            row = json.loads(
                text,
                parse_float=Decimal,
                parse_constant=_reject_json_constant,
                object_pairs_hook=_strict_json_object,
            )
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            source["parse_status"] = "invalid"
            detail = error.msg if isinstance(error, json.JSONDecodeError) else str(error)
            raise EvidenceError(
                f"cannot read strict UTF-8 run record: {detail}", source_path
            ) from error
        try:
            if not isinstance(row, dict):
                raise EvidenceError("run record must be an object", source_path)
            raw_path = row.get("path_per_floor")
            if not isinstance(raw_path, list):
                raise EvidenceError(
                    "run path_per_floor must contain only valid room symbols",
                    source_path,
                )
            for floor, symbol in enumerate(raw_path):
                if symbol is None:
                    if floor == 0 or raw_path[floor - 1] != "B":
                        raise EvidenceError(
                            f"run path_per_floor[{floor}] null transition slot "
                            "must immediately follow B",
                            source_path,
                        )
                elif not isinstance(symbol, str) or symbol not in _RUN_SYMBOLS:
                    raise EvidenceError(
                        "run path_per_floor must contain only valid room symbols",
                        source_path,
                    )
            floor_reached = row.get("floor_reached")
            if floor_reached is not None:
                floor_reached = _strict_integer(floor_reached, "run floor_reached")
            victory = row.get("victory")
            if victory is not None and not isinstance(victory, bool):
                raise EvidenceError("run victory must be boolean", source_path)
        except EvidenceError:
            source["parse_status"] = "invalid"
            raise
        runs.append(
            RunEvidence(
                source_path=source_path,
                path_per_floor=tuple(raw_path),
                floor_reached=floor_reached,
                victory=victory,
            )
        )
        source["record_count"] = 1
        source["parse_status"] = "valid"
    return runs, sources


def _empty_funnel() -> dict[str, int]:
    return {
        "adaptive_occurrences": 0,
        "callback_independent_records": 0,
        "candidate_generation_fallbacks": 0,
        "complete_candidate_pairs": 0,
        "zero_vs_one_opportunities": 0,
        "act1_zero_vs_one_opportunities": 0,
        "aggressive_selections": 0,
        "same_immediate_coordinate": 0,
        "different_immediate_coordinate": 0,
        "ambiguous_immediate_coordinate": 0,
        "provable_first_divergences": 0,
        "selection_revoked_before_divergence": 0,
        "route_left_before_divergence": 0,
        "divergences_taken": 0,
        "realized_optional_elites": 0,
    }


def _coordinate_json(coordinate: Coordinate | None) -> list[int] | None:
    return list(coordinate) if coordinate is not None else None


def _paths_json(paths: tuple[CoordinatePath, ...]) -> list[list[list[int]]]:
    return [[list(coordinate) for coordinate in path] for path in paths]


def _candidate_pair_json(evidence: CandidatePairEvidence) -> dict:
    divergence = evidence.first_divergence
    return {
        "conservative_match_count": evidence.conservative_match_count,
        "aggressive_match_count": evidence.aggressive_match_count,
        "conservative_matches": _paths_json(evidence.conservative_matches),
        "aggressive_matches": _paths_json(evidence.aggressive_matches),
        "conservative_immediate": _coordinate_json(evidence.conservative_immediate),
        "aggressive_immediate": _coordinate_json(evidence.aggressive_immediate),
        "immediate_classification": evidence.immediate_classification,
        "first_divergence": (
            None
            if divergence is None
            else {
                "index": divergence.index,
                "map_y": divergence.map_y,
                "entered_floor": divergence.entered_floor,
                "conservative": list(divergence.conservative),
                "aggressive": list(divergence.aggressive),
            }
        ),
    }


def _record_ledger_json(
    record_ordinal: int,
    joined: JoinedRecord,
    corroboration: dict,
    runs: Sequence[RunEvidence],
) -> dict:
    game_number = joined.record.game_number
    run_source_path = (
        str(runs[game_number - 1].source_path)
        if game_number <= len(runs)
        else None
    )
    return {
        "record_ordinal": record_ordinal,
        "game_number": game_number,
        "payload": joined.record.payload,
        "multiplicity": len(joined.occurrences),
        "occurrences": [
            {
                "source_path": str(item.occurrence.source_path),
                "line_number": item.occurrence.line_number,
                "timestamp": item.occurrence.timestamp.isoformat(
                    timespec="microseconds"
                ),
                "unix_time_seconds": str(item.occurrence.unix_time),
                "joined_decision_unix_time_seconds": str(item.decision.unix_time),
                "join_delta_seconds": str(item.delta_seconds),
            }
            for item in joined.occurrences
        ],
        "decision": {
            "semantic_fingerprint": joined.decision.semantic_fingerprint,
            "unix_time_seconds": str(joined.decision.unix_time),
            "act": joined.decision.act,
            "floor": joined.decision.floor,
            "current_coordinate": list(joined.decision.current_node),
            "next_coordinates": [
                list(coordinate) for coordinate in joined.decision.next_nodes
            ],
            "action_coordinate": list(joined.decision.action_node),
        },
        "run_corroboration": {
            "run_source_path": run_source_path,
            **corroboration,
        },
    }


def _fallback_json(
    fallback_number: int,
    record_ordinal: int,
    joined: JoinedRecord,
    corroboration: dict,
    runs: Sequence[RunEvidence],
) -> dict:
    game_number = joined.record.game_number
    run_source_path = (
        str(runs[game_number - 1].source_path)
        if game_number <= len(runs)
        else None
    )
    return {
        "fallback_number": fallback_number,
        "record_ordinal": record_ordinal,
        "game_number": game_number,
        "payload": joined.record.payload,
        "multiplicity": len(joined.occurrences),
        "occurrences": [
            {
                "source_path": str(item.occurrence.source_path),
                "line_number": item.occurrence.line_number,
                "timestamp": item.occurrence.timestamp.isoformat(
                    timespec="microseconds"
                ),
                "join_delta_seconds": str(item.delta_seconds),
            }
            for item in joined.occurrences
        ],
        "decision": {
            "act": joined.decision.act,
            "floor": joined.decision.floor,
            "current_coordinate": list(joined.decision.current_node),
            "next_coordinates": [
                list(coordinate) for coordinate in joined.decision.next_nodes
            ],
            "action_coordinate": list(joined.decision.action_node),
        },
        "run_corroboration": {
            "run_source_path": run_source_path,
            **corroboration,
        },
    }


def _run_corroboration(
    joined: JoinedRecord, runs: Sequence[RunEvidence]
) -> tuple[dict, dict | None]:
    decision = joined.decision
    graph = dict(decision.graph)
    trace_symbol = graph[decision.action_node].symbol
    game_number = joined.record.game_number
    if game_number > len(runs):
        return (
            {
                "trace_symbol": trace_symbol,
                "run_symbol": None,
                "run_compatibility": "missing",
            },
            {
                "code": "missing_ordered_run",
                "game_number": game_number,
                "act": decision.act,
                "floor": decision.floor,
            },
        )
    run = runs[game_number - 1]
    if decision.floor >= len(run.path_per_floor):
        return (
            {
                "trace_symbol": trace_symbol,
                "run_symbol": None,
                "run_compatibility": "missing",
            },
            {
                "code": "run_floor_missing",
                "game_number": game_number,
                "act": decision.act,
                "floor": decision.floor,
            },
        )
    run_symbol = run.path_per_floor[decision.floor]
    if run_symbol is None:
        return (
            {
                "trace_symbol": trace_symbol,
                "run_symbol": None,
                "run_compatibility": "transition_slot",
            },
            {
                "code": "run_transition_slot_targeted",
                "game_number": game_number,
                "run_source_path": str(run.source_path),
                "act": decision.act,
                "floor": decision.floor,
            },
        )
    if trace_symbol == run_symbol:
        compatibility = "exact"
        diagnostic = None
    elif trace_symbol == "?" and run_symbol != "B":
        compatibility = "event_resolved"
        diagnostic = None
    else:
        compatibility = "mismatch"
        diagnostic = {
            "code": "run_symbol_mismatch",
            "game_number": game_number,
            "act": decision.act,
            "floor": decision.floor,
            "trace_symbol": trace_symbol,
            "run_symbol": run_symbol,
        }
    return (
        {
            "trace_symbol": trace_symbol,
            "run_symbol": run_symbol,
            "run_compatibility": compatibility,
        },
        diagnostic,
    )


def _joined_step(
    joined: JoinedRecord, corroboration: dict
) -> dict:
    occurrence = joined.record.occurrences[0]
    joined_times = [item.decision.unix_time_us for item in joined.occurrences]
    return {
        "joined": joined,
        "selected": occurrence.fields["selected"],
        "first_time_us": min(joined_times),
        "last_time_us": max(joined_times),
        "corroboration": corroboration,
    }


def _treatment_evidence(
    joined: JoinedRecord,
    pair: CandidatePairEvidence,
    same_game_steps: Sequence[dict],
) -> dict:
    divergence = pair.first_divergence
    if divergence is None:
        return {"status": "ambiguous"}
    occurrence = joined.record.occurrences[0]
    aggressive = occurrence.aggressive
    conservative = occurrence.conservative
    if aggressive is None or conservative is None:
        return {"status": "ambiguous"}

    conservative_elite_floors = set(conservative.elite_floors)
    attributable_elites: dict[int, Coordinate] = {}
    for elite_floor in aggressive.elite_floors:
        if elite_floor in conservative_elite_floors:
            continue
        elite_index = elite_floor - aggressive.start_y - 1
        if elite_index < divergence.index:
            continue
        aggressive_set = pair.aggressive_coordinate_sets[elite_index]
        conservative_set = pair.conservative_coordinate_sets[elite_index]
        if len(aggressive_set) != 1 or aggressive_set[0] in set(conservative_set):
            continue
        attributable_elites[elite_index] = aggressive_set[0]

    origin_step = next(
        step for step in same_game_steps if step["joined"] is joined
    )
    origin_decision = joined.decision
    if origin_decision.action_node not in set(pair.aggressive_coordinate_sets[0]):
        return {"status": "trajectory_unattributable", "reason": "disconnected"}
    chronology_steps = sorted(
        (
            step
            for step in same_game_steps
            if step["joined"] is not joined
            and step["joined"].decision.act == origin_decision.act
            and step["last_time_us"] >= origin_step["first_time_us"]
        ),
        key=lambda step: (step["first_time_us"], step["last_time_us"]),
    )
    if any(
        step["first_time_us"] <= origin_step["last_time_us"]
        for step in chronology_steps
    ):
        return {
            "status": "trajectory_unattributable",
            "reason": "chronological_overlap",
        }

    def divergence_evidence(step: dict) -> dict:
        decision = step["joined"].decision
        return {
            "status": "divergence_taken",
            "divergence": {
                "act": decision.act,
                "floor": decision.floor,
                "coordinate": list(divergence.aggressive),
            },
        }

    def realized_elite(
        index: int, step: dict, current_treatment: dict
    ) -> dict | None:
        coordinate = attributable_elites.get(index)
        if coordinate is None:
            return None
        decision = step["joined"].decision
        corroboration = step["corroboration"]
        if (
            decision.action_node == coordinate
            and corroboration["trace_symbol"] == "E"
            and corroboration["run_symbol"] == "E"
            and corroboration["run_compatibility"] == "exact"
        ):
            return {
                "status": "realized_optional_elite",
                "divergence": current_treatment["divergence"],
                "elite": {
                    "act": decision.act,
                    "floor": decision.floor,
                    "coordinate": list(coordinate),
                    "trace_symbol": "E",
                    "run_symbol": "E",
                },
            }
        return None

    treatment: dict | None = None
    if divergence.index == 0:
        treatment = divergence_evidence(origin_step)
        elite = realized_elite(0, origin_step, treatment)
        if elite is not None:
            return elite

    max_target_index = max(
        (divergence.index, *attributable_elites.keys())
    )
    later_steps = [
        step
        for step in chronology_steps
        if step["first_time_us"] > origin_step["last_time_us"]
    ]
    previous_step = origin_step
    previous_time_us = origin_step["last_time_us"]
    expected_index = 1

    for step in later_steps:
        if expected_index > max_target_index:
            break
        decision = step["joined"].decision
        previous_decision = previous_step["joined"].decision
        if step["first_time_us"] <= previous_time_us:
            return {
                "status": "trajectory_unattributable",
                "reason": "chronological_overlap",
            }
        if (
            decision.floor == previous_decision.floor
            and decision.current_node == previous_decision.current_node
            and decision.action_node == previous_decision.action_node
        ):
            previous_time_us = step["last_time_us"]
            if step["selected"] != "aggressive" and expected_index <= divergence.index:
                return {
                    "status": "revoked_before_divergence",
                    "revocation": {
                        "act": decision.act,
                        "floor": decision.floor,
                        "selected": step["selected"],
                    },
                }
            continue
        if decision.floor != previous_decision.floor + 1:
            if treatment is not None:
                return treatment
            return {
                "status": "trajectory_unattributable",
                "reason": "floor_gap",
            }
        if decision.current_node != previous_decision.action_node:
            if treatment is not None:
                return treatment
            return {
                "status": "trajectory_unattributable",
                "reason": "disconnected",
            }
        if decision.action_node[1] != aggressive.start_y + expected_index:
            if treatment is not None:
                return treatment
            return {
                "status": "trajectory_unattributable",
                "reason": "coordinate_progression",
            }
        if step["selected"] != "aggressive":
            if expected_index <= divergence.index:
                return {
                    "status": "revoked_before_divergence",
                    "revocation": {
                        "act": decision.act,
                        "floor": decision.floor,
                        "selected": step["selected"],
                    },
                }
            return treatment or {"status": "incomplete_before_divergence"}
        if decision.action_node not in set(
            pair.aggressive_coordinate_sets[expected_index]
        ):
            if expected_index < divergence.index:
                return {
                    "status": "route_left_before_divergence",
                    "route_departure": {
                        "act": decision.act,
                        "floor": decision.floor,
                        "action_coordinate": list(decision.action_node),
                    },
                }
            if expected_index == divergence.index:
                return {
                    "status": "divergence_not_taken",
                    "divergence": {
                        "act": decision.act,
                        "floor": decision.floor,
                        "expected_coordinate": list(divergence.aggressive),
                        "action_coordinate": list(decision.action_node),
                    },
                }
            return treatment or {"status": "incomplete_before_divergence"}

        previous_step = step
        previous_time_us = step["last_time_us"]
        if expected_index == divergence.index:
            treatment = divergence_evidence(step)
        if treatment is not None:
            elite = realized_elite(expected_index, step, treatment)
            if elite is not None:
                return elite
        expected_index += 1

    return treatment or {"status": "incomplete_before_divergence"}


def _base_result(
    utc_offset_hours: float | None,
    max_join_seconds: float | None,
    sources: dict,
    diagnostics: list[dict],
) -> dict:
    return {
        "schema_version": "adaptive-route-opportunity-audit-v1",
        "parameters": {
            "log_utc_offset_hours": utc_offset_hours,
            "max_join_seconds": max_join_seconds,
        },
        "sources": sources,
        "integrity": {
            "status": "invalid" if diagnostics else "valid",
            "diagnostics": diagnostics,
        },
        "deduplication": {
            "adaptive_occurrences": 0,
            "callback_independent_records": 0,
            "multiplicities": [],
        },
        "funnel": _empty_funnel(),
        "runs": [],
        "fallbacks": [],
        "records": [],
        "opportunities": [],
    }


def build_audit(
    ai_logs: Sequence[Path],
    decision_trace: Path,
    runs: Sequence[Path],
    utc_offset_hours: float,
    max_join_seconds: float,
) -> tuple[dict, int]:
    """Build a deterministic, fail-closed adaptive-route opportunity audit."""
    sources: dict = {"ai_logs": [], "decision_trace": None, "runs": []}
    ai_sources: list[dict] = []
    trace_sources: list[dict] = []
    run_sources: list[dict] = []
    parameter_diagnostics: list[dict] = []
    try:
        validated_utc_offset = _validate_utc_offset(utc_offset_hours)
    except EvidenceError as error:
        validated_utc_offset = None
        parameter_diagnostics.append(
            {
                "code": "invalid_parameter",
                "parameter": "log_utc_offset_hours",
                "message": str(error),
            }
        )
    try:
        _validate_join_tolerance(max_join_seconds)
        validated_max_join = float(max_join_seconds)
    except (EvidenceError, OverflowError, TypeError, ValueError) as error:
        validated_max_join = None
        parameter_diagnostics.append(
            {
                "code": "invalid_parameter",
                "parameter": "max_join_seconds",
                "message": str(error),
            }
        )
    if parameter_diagnostics:
        return (
            _base_result(
                validated_utc_offset,
                validated_max_join,
                sources,
                parameter_diagnostics,
            ),
            2,
        )

    try:
        _validate_input_source_identity(ai_logs, decision_trace, runs)
        sources["ai_logs"] = ai_sources
        occurrences, _ = load_adaptive_logs(
            ai_logs, validated_utc_offset, ai_sources
        )
        trace_rows, trace_source = load_decision_trace(
            Path(decision_trace), trace_sources
        )
        sources["decision_trace"] = trace_source
        sources["runs"] = run_sources
        run_records, _ = load_runs(runs, run_sources)
        records = deduplicate_occurrences(occurrences)
        joined_records = join_occurrences(
            records, trace_rows, validated_max_join
        )
    except EvidenceError as error:
        if trace_sources:
            sources["decision_trace"] = trace_sources[0]
        result = _base_result(
            validated_utc_offset,
            validated_max_join,
            sources,
            [{"code": "evidence_error", "message": str(error)}],
        )
        return result, 2

    diagnostics: list[dict] = []
    corroborations: dict[int, dict] = {}
    classified: dict[int, CandidatePairEvidence] = {}
    for joined in joined_records:
        corroboration, diagnostic = _run_corroboration(joined, run_records)
        corroborations[id(joined)] = corroboration
        if diagnostic is not None:
            diagnostics.append(diagnostic)
        occurrence = joined.record.occurrences[0]
        if occurrence.fields["candidate_pair"] == "complete":
            try:
                classified[id(joined)] = classify_candidate_pair(joined)
            except EvidenceError as error:
                diagnostics.append(
                    {
                        "code": "candidate_attribution_error",
                        "game_number": joined.record.game_number,
                        "act": joined.decision.act,
                        "floor": joined.decision.floor,
                        "message": str(error),
                    }
                )

    result = _base_result(
        validated_utc_offset, validated_max_join, sources, diagnostics
    )
    funnel = result["funnel"]
    funnel["adaptive_occurrences"] = len(occurrences)
    funnel["callback_independent_records"] = len(records)
    fallback_records = [
        joined
        for joined in joined_records
        if joined.record.occurrences[0].fields["outcome"]
        == "candidate_generation_failed"
    ]
    funnel["candidate_generation_fallbacks"] = len(fallback_records)
    complete_records = [
        joined
        for joined in joined_records
        if joined.record.occurrences[0].fields["candidate_pair"] == "complete"
    ]
    funnel["complete_candidate_pairs"] = len(complete_records)
    result["deduplication"] = {
        "adaptive_occurrences": len(occurrences),
        "callback_independent_records": len(records),
        "multiplicities": [len(record.occurrences) for record in records],
    }
    result["runs"] = [
        {
            "game_number": index,
            "source_path": str(run.source_path),
            "path_per_floor": list(run.path_per_floor),
            "floor_reached": run.floor_reached,
            "victory": run.victory,
        }
        for index, run in enumerate(run_records, start=1)
    ]
    record_ordinals = {
        id(joined): record_ordinal
        for record_ordinal, joined in enumerate(joined_records, start=1)
    }
    result["records"] = [
        _record_ledger_json(
            record_ordinals[id(joined)],
            joined,
            corroborations[id(joined)],
            run_records,
        )
        for joined in joined_records
    ]
    result["fallbacks"] = [
        _fallback_json(
            fallback_number,
            record_ordinals[id(joined)],
            joined,
            corroborations[id(joined)],
            run_records,
        )
        for fallback_number, joined in enumerate(fallback_records, start=1)
    ]

    steps_by_game: dict[int, list[dict]] = {}
    for joined in joined_records:
        steps_by_game.setdefault(joined.record.game_number, []).append(
            _joined_step(joined, corroborations[id(joined)])
        )

    opportunities: list[dict] = []
    for joined in joined_records:
        occurrence = joined.record.occurrences[0]
        conservative = occurrence.conservative
        aggressive = occurrence.aggressive
        if (
            conservative is None
            or aggressive is None
            or conservative.elite_count != 0
            or aggressive.elite_count != 1
        ):
            continue
        funnel["zero_vs_one_opportunities"] += 1
        if joined.decision.act == 1:
            funnel["act1_zero_vs_one_opportunities"] += 1
        pair = classified.get(id(joined))
        corroboration = corroborations[id(joined)]
        decision_summary = {
            "act": joined.decision.act,
            "floor": joined.decision.floor,
            "action_coordinate": list(joined.decision.action_node),
            **corroboration,
        }
        selected = occurrence.fields["selected"]
        treatment = {"status": "not_aggressive"}
        if selected == "aggressive":
            funnel["aggressive_selections"] += 1
            if pair is None:
                treatment = {"status": "ambiguous"}
            else:
                funnel[f"{pair.immediate_classification}_immediate_coordinate"] += 1
                if pair.first_divergence is not None:
                    funnel["provable_first_divergences"] += 1
                treatment = _treatment_evidence(
                    joined,
                    pair,
                    steps_by_game[joined.record.game_number],
                )
                if treatment["status"] == "revoked_before_divergence":
                    funnel["selection_revoked_before_divergence"] += 1
                elif treatment["status"] == "route_left_before_divergence":
                    funnel["route_left_before_divergence"] += 1
                elif treatment["status"] in {
                    "divergence_taken",
                    "realized_optional_elite",
                }:
                    funnel["divergences_taken"] += 1
                if treatment["status"] == "realized_optional_elite":
                    funnel["realized_optional_elites"] += 1
        opportunities.append(
            {
                "opportunity_number": len(opportunities) + 1,
                "record_ordinal": record_ordinals[id(joined)],
                "game_number": joined.record.game_number,
                "selected": selected,
                "decision": decision_summary,
                "candidate_pair": (
                    _candidate_pair_json(pair) if pair is not None else None
                ),
                "treatment": treatment,
            }
        )
    result["opportunities"] = opportunities
    return result, 0 if result["integrity"]["status"] == "valid" else 2


def serialize_audit(result: dict) -> bytes:
    """Serialize stable ASCII JSON with sorted keys and one final newline."""
    return (
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("ascii")


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit frozen adaptive-route opportunity evidence."
    )
    parser.add_argument("--ai-log", action="append", required=True, type=Path)
    parser.add_argument("--decision-trace", required=True, type=Path)
    parser.add_argument("--run", action="append", required=True, type=Path)
    parser.add_argument("--log-utc-offset-hours", required=True, type=float)
    parser.add_argument("--max-join-seconds", required=True, type=float)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def _normalized_path_identity(path: Path, context: str) -> str:
    try:
        resolved = path.resolve(strict=False)
    except (OSError, RuntimeError) as error:
        raise EvidenceError(f"{context}: path normalization failed") from error
    return os.path.normcase(os.path.normpath(str(resolved)))


def _path_exists_for_identity(path: Path, context: str) -> bool:
    try:
        path.stat()
    except FileNotFoundError:
        return False
    except OSError as error:
        raise EvidenceError(f"{context}: file identity check failed") from error
    return True


def _paths_share_source(left: Path, right: Path, context: str) -> bool:
    if _normalized_path_identity(left, context) == _normalized_path_identity(
        right, context
    ):
        return True
    left_exists = _path_exists_for_identity(left, context)
    right_exists = _path_exists_for_identity(right, context)
    if not (left_exists and right_exists):
        return False
    try:
        return left.samefile(right)
    except OSError as error:
        raise EvidenceError(f"{context}: file identity check failed") from error


def _validate_input_source_identity(
    ai_logs: Sequence[Path], decision_trace: Path, runs: Sequence[Path]
) -> None:
    source_paths = (
        *_validate_paths(ai_logs),
        Path(decision_trace),
        *_validate_ordered_sources(runs, "run"),
    )
    for index, source_path in enumerate(source_paths):
        for prior_path in source_paths[:index]:
            if _paths_share_source(
                source_path, prior_path, "input source identity"
            ):
                raise EvidenceError("input sources alias one physical file")


def _validate_output_source_separation(
    output: Path, source_paths: Sequence[Path]
) -> None:
    for source_path in source_paths:
        if _paths_share_source(output, source_path, "output/source identity"):
            raise EvidenceError("output/source alias rejected")


def main(argv: Sequence[str] | None = None) -> int:
    args = _argument_parser().parse_args(argv)
    try:
        _validate_output_source_separation(
            args.output, [*args.ai_log, args.decision_trace, *args.run]
        )
    except EvidenceError as error:
        print(f"adaptive-route audit argument error: {error}", file=sys.stderr)
        return 2
    result, exit_code = build_audit(
        args.ai_log,
        args.decision_trace,
        args.run,
        args.log_utc_offset_hours,
        args.max_join_seconds,
    )
    args.output.write_bytes(serialize_audit(result))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
