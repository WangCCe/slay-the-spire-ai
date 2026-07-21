from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from analysis_scripts import adaptive_route_opportunity_audit as audit


def _candidate(
    mode: str,
    *,
    symbols: str,
    elite_count: int,
    elite_floors: str,
    recovery_before: str = "none",
    recovery_after: str = "none",
) -> str:
    return (
        f"mode:{mode},start_y:7,symbols:{symbols},elite_count:{elite_count},"
        f"elite_floors:{elite_floors},recovery_before:{recovery_before},"
        f"recovery_after:{recovery_after}"
    )


def _payload(**overrides: str) -> str:
    values = {
        "outcome": "success",
        "character": "IRONCLAD",
        "act": "1",
        "floor": "8",
        "state_valid": "true",
        "hp": "60/80",
        "hp_pct": "0.750000",
        "deck": "prepared",
        "potion": "none",
        "relic": "none",
        "elite_seen": "false",
        "last_rest_floor": "none",
        "candidate_pair": "complete",
        "conservative_candidate": _candidate(
            "conservative",
            symbols="M/T/?/$/R/?/M/R",
            elite_count=0,
            elite_floors="none",
        ),
        "aggressive_candidate": _candidate(
            "aggressive",
            symbols="M/T/?/$/R/?/E/R",
            elite_count=1,
            elite_floors="14",
            recovery_before="2",
            recovery_after="1",
        ),
        "minimum_elites": "0",
        "added_elites": "1",
        "fallback_candidate": "not_used",
        "budget": "1",
        "selected": "aggressive",
        "reasons": "elite_budget",
    }
    values.update(overrides)
    return " ".join(f"{key}={values[key]}" for key in audit.ADAPTIVE_KEYS)


def _line(message: str, second: int = 0, millisecond: int = 0) -> str:
    return f"2026-07-22 12:00:{second:02d},{millisecond:03d} - INFO - {message}\n"


def _write_log(tmp_path: Path, name: str, lines: list[str]) -> Path:
    path = tmp_path / name
    path.write_bytes("".join(lines).encode("utf-8"))
    return path


def test_parse_adaptive_payload_preserves_exact_fields_and_candidates():
    payload = _payload()

    fields, conservative, aggressive = audit.parse_adaptive_payload(payload)

    assert fields["candidate_pair"] == "complete"
    assert conservative == audit.Candidate(
        mode="conservative",
        start_y=7,
        symbols=("M", "T", "?", "$", "R", "?", "M", "R"),
        elite_count=0,
        elite_floors=(),
        recovery_before=None,
        recovery_after=None,
    )
    assert aggressive == audit.Candidate(
        mode="aggressive",
        start_y=7,
        symbols=("M", "T", "?", "$", "R", "?", "E", "R"),
        elite_count=1,
        elite_floors=(14,),
        recovery_before=2,
        recovery_after=1,
    )


def test_loads_occurrence_provenance_source_identity_and_deduplicates_callbacks(
    tmp_path: Path,
):
    payload = _payload()
    source = _write_log(
        tmp_path,
        "adaptive.log",
        [
            _line("Starting game #1"),
            _line(f"[ADAPTIVE_ROUTE] {payload}", millisecond=100),
            _line(f"[ADAPTIVE_ROUTE] {payload}", millisecond=200),
            _line("Starting game #2", second=1),
            _line(f"[ADAPTIVE_ROUTE] {payload}", second=1, millisecond=100),
            "\n",
        ],
    )

    occurrences, sources = audit.load_adaptive_logs([source], utc_offset_hours=8)
    records = audit.deduplicate_occurrences(occurrences)

    assert [(record.game_number, len(record.occurrences)) for record in records] == [
        (1, 2),
        (2, 1),
    ]
    first = records[0].occurrences[0]
    assert first.source_path == source
    assert first.line_number == 2
    assert first.timestamp == datetime(2026, 7, 22, 12, 0, 0, 100000)
    assert first.unix_time == datetime(
        2026, 7, 22, 12, 0, 0, 100000, tzinfo=timezone(timedelta(hours=8))
    ).timestamp()
    assert sources == [
        {
            "source_path": str(source),
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "byte_count": len(source.read_bytes()),
            "line_count": 6,
            "record_count": 3,
        }
    ]


@pytest.mark.parametrize(
    "payload",
    [
        lambda: " ".join(reversed(_payload().split())),
        lambda: _payload() + " unexpected=value",
        lambda: _payload(conservative_candidate="mode:conservative,start_y:7,symbols:M/X,elite_count:0,elite_floors:none,recovery_before:none,recovery_after:none"),
    ],
)
def test_rejects_reordered_extra_or_malformed_candidate_payloads(payload):
    with pytest.raises(audit.EvidenceError, match="adaptive payload|candidate"):
        audit.parse_adaptive_payload(payload())


def test_rejects_adaptive_record_without_a_game_boundary(tmp_path: Path):
    source = _write_log(
        tmp_path,
        "missing-boundary.log",
        [_line(f"[ADAPTIVE_ROUTE] {_payload()}")],
    )

    with pytest.raises(audit.EvidenceError, match="missing game boundary"):
        audit.load_adaptive_logs([source], utc_offset_hours=8)


def test_rejects_non_monotonic_game_boundaries(tmp_path: Path):
    source = _write_log(
        tmp_path,
        "non-monotonic.log",
        [
            _line("Starting game #2"),
            _line("Starting game #1", second=1),
        ],
    )

    with pytest.raises(audit.EvidenceError, match="non-monotonic game boundary"):
        audit.load_adaptive_logs([source], utc_offset_hours=8)
