"""Read-only parsing primitives for adaptive-route audit evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from math import isfinite
from pathlib import Path
import re
from typing import Sequence


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
    for key in ("deck", "potion", "relic"):
        _parse_nonnegative_integer(fields[key], key)
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
    if fields["character"] != "unavailable" and _CHARACTER.fullmatch(fields["character"]) is None:
        raise EvidenceError("adaptive character is invalid")
    if fields["act"] != "unavailable":
        _parse_positive_integer(fields["act"], "act")
    if fields["floor"] != "unavailable":
        _parse_nonnegative_integer(fields["floor"], "floor")
    _parse_nonnegative_integer(fields["budget"], "budget")
    _validate_state_scalars(fields)
    if fields["candidate_pair"] not in {
        "complete",
        "not_attempted",
        "generation_failed",
    }:
        raise EvidenceError("adaptive candidate_pair is invalid")
    if fields["selected"] not in {"conservative", "aggressive"}:
        raise EvidenceError("adaptive selected mode is invalid")
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
