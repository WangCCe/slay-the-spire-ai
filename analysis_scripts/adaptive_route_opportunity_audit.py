"""Read-only parsing primitives for adaptive-route audit evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
import re
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
    unix_time: float
    payload: str
    fields: dict[str, str]
    conservative: Candidate | None
    aggressive: Candidate | None


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
    unix_time: float
    act: int
    floor: int
    current_node: Coordinate
    next_nodes: tuple[Coordinate, ...]
    graph: tuple[tuple[Coordinate, GraphNode], ...]
    paths: tuple[TracePath, ...]
    action_node: Coordinate
    semantic_fingerprint: str


@dataclass(frozen=True)
class JoinedOccurrence:
    occurrence: AdaptiveOccurrence
    decision: TraceMapDecision
    delta_seconds: float


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

    return Candidate(
        mode=mode,
        start_y=start_y,
        symbols=symbols,
        elite_count=elite_count,
        elite_floors=elite_floors,
        recovery_before=recovery_before,
        recovery_after=recovery_after,
    )


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
    return datetime.strptime(match.group("timestamp"), "%Y-%m-%d %H:%M:%S,%f"), match.group("message")


def load_adaptive_logs(
    paths: Sequence[Path], utc_offset_hours: float
) -> tuple[list[AdaptiveOccurrence], list[dict]]:
    """Load chronologically ordered adaptive log sources with byte identities."""
    ordered_paths = _validate_paths(paths)
    offset_hours = _validate_utc_offset(utc_offset_hours)
    offset = timezone(timedelta(hours=offset_hours))
    occurrences: list[AdaptiveOccurrence] = []
    sources: list[dict] = []
    active_game_number: int | None = None
    previous_game_number: int | None = None

    for source_path in ordered_paths:
        try:
            raw_bytes = source_path.read_bytes()
            text = raw_bytes.decode("utf-8")
        except (OSError, UnicodeDecodeError) as error:
            raise EvidenceError(f"cannot read UTF-8 adaptive log source: {error}", source_path) from error

        record_count = 0
        for line_number, line in enumerate(text.splitlines(), start=1):
            parsed = _timestamp_and_message(line)
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
                    unix_time=timestamp.replace(tzinfo=offset).timestamp(),
                    payload=payload,
                    fields=fields,
                    conservative=conservative,
                    aggressive=aggressive,
                )
            )
            record_count += 1
        sources.append(
            {
                "source_path": str(source_path),
                "sha256": sha256(raw_bytes).hexdigest(),
                "byte_count": len(raw_bytes),
                "line_count": len(text.splitlines()),
                "record_count": record_count,
            }
        )
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


def _strict_number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EvidenceError(f"{label} must be a finite number")
    parsed = float(value)
    if not isfinite(parsed):
        raise EvidenceError(f"{label} must be a finite number")
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
    if y == -1 and not allow_virtual:
        raise EvidenceError(f"{label} cannot be a virtual coordinate")
    if y == -1 and x < -1:
        raise EvidenceError(f"{label} virtual x is invalid")
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


_TRACE_PATH_NODE = re.compile(r"^(?P<symbol>[MT?$RE])@(?P<x>[0-6]),(?P<y>0|[1-9]\d*)$")


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
            or any(symbol not in _ROUTE_SYMBOLS for symbol in symbols)
        ):
            raise EvidenceError("path nodes contain invalid route symbols")

        coordinates: list[Coordinate] = []
        label_symbols: list[str] = []
        for part in label.split(" -> "):
            match = _TRACE_PATH_NODE.fullmatch(part)
            if match is None:
                raise EvidenceError("path label does not contain exact map coordinates")
            coordinate = (int(match.group("x")), int(match.group("y")))
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
    if current_node[1] == -1:
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


def load_decision_trace(path: Path) -> tuple[list[TraceMapDecision], dict]:
    """Load strict JSONL and retain only node-selection MAP actions for joins."""
    source_path = Path(path)
    try:
        raw_bytes = source_path.read_bytes()
        text = raw_bytes.decode("utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise EvidenceError(
            f"cannot read UTF-8 decision trace source: {error}", source_path
        ) from error

    decisions: list[TraceMapDecision] = []
    record_count = 0
    map_record_count = 0
    node_action_record_count = 0
    boss_action_record_count = 0
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        record_count += 1
        try:
            row = json.loads(
                line,
                parse_constant=_reject_json_constant,
                object_pairs_hook=_strict_json_object,
            )
        except (json.JSONDecodeError, ValueError) as error:
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

    return decisions, {
        "source_path": str(source_path),
        "sha256": sha256(raw_bytes).hexdigest(),
        "byte_count": len(raw_bytes),
        "line_count": len(text.splitlines()),
        "record_count": record_count,
        "map_record_count": map_record_count,
        "node_action_record_count": node_action_record_count,
        "boss_action_record_count": boss_action_record_count,
    }


def _validate_join_tolerance(max_join_seconds: float) -> float:
    if (
        isinstance(max_join_seconds, bool)
        or not isinstance(max_join_seconds, (int, float))
        or not isfinite(float(max_join_seconds))
        or max_join_seconds < 0
    ):
        raise EvidenceError("join tolerance must be a finite non-negative number")
    return float(max_join_seconds)


def join_occurrences(
    records: Sequence[AdaptiveRecord],
    trace_rows: Sequence[TraceMapDecision],
    max_join_seconds: float,
) -> list[JoinedRecord]:
    """Join every source occurrence before accepting semantic deduplication."""
    tolerance = _validate_join_tolerance(max_join_seconds)
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
                (abs(decision.unix_time - occurrence.unix_time), decision)
                for decision in same_state
            ]
            bounded = [candidate for candidate in candidates if candidate[0] <= tolerance]
            if not bounded:
                raise EvidenceError(
                    "nearest decision-trace row is outside join tolerance",
                    occurrence.source_path,
                    occurrence.line_number,
                )
            bounded.sort(key=lambda candidate: candidate[0])
            nearest_delta, nearest = bounded[0]
            if len(bounded) > 1 and abs(bounded[1][0] - nearest_delta) <= 1e-12:
                raise EvidenceError(
                    "tied nearest decision-trace join for adaptive occurrence",
                    occurrence.source_path,
                    occurrence.line_number,
                )
            joined_occurrences.append(
                JoinedOccurrence(
                    occurrence=occurrence,
                    decision=nearest,
                    delta_seconds=nearest_delta,
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
