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
        "deck": "5",
        "potion": "1",
        "relic": "0",
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


def _live_line(payload: str, *, boundary: str = "Starting game #1 as PlayerClass.IRONCLAD") -> list[str]:
    return [_line(boundary), _line(f"[ADAPTIVE_ROUTE] {payload}", millisecond=100)]


def _outcome_payload(outcome: str) -> str:
    if outcome == "success":
        return _payload()
    if outcome == "forced":
        return _payload(
            outcome="forced",
            budget="0",
            selected="conservative",
            reasons="forced_elite_route",
        )
    if outcome == "unsupported":
        return _payload(
            outcome="unsupported",
            candidate_pair="not_attempted",
            conservative_candidate="unavailable",
            aggressive_candidate="unavailable",
            minimum_elites="unavailable",
            added_elites="unavailable",
            fallback_candidate="not_applicable",
            budget="0",
            selected="conservative",
            reasons="unsupported_character",
        )
    if outcome == "candidate_generation_failed":
        return _payload(
            outcome="candidate_generation_failed",
            candidate_pair="generation_failed",
            conservative_candidate="unavailable",
            aggressive_candidate="unavailable",
            minimum_elites="unavailable",
            added_elites="unavailable",
            fallback_candidate=_candidate(
                "conservative",
                symbols="M/T/?/$/R/?/M/R",
                elite_count=0,
                elite_floors="none",
            ),
            budget="0",
            selected="conservative",
            reasons="candidate_generation_failed",
        )
    raise AssertionError(f"unexpected outcome {outcome}")


def _assert_rejected_live_line(tmp_path: Path, name: str, payload: str) -> None:
    source = _write_log(tmp_path, name, _live_line(payload))

    with pytest.raises(audit.EvidenceError) as error:
        audit.load_adaptive_logs([source], utc_offset_hours=8)

    assert str(error.value).startswith(f"{source}:2:")


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


def test_accepts_exact_production_game_boundary_suffix_and_rejects_trailing_text(tmp_path: Path):
    source = _write_log(tmp_path, "production-boundary.log", _live_line(_payload()))

    occurrences, _ = audit.load_adaptive_logs([source], utc_offset_hours=8)

    assert [occurrence.game_number for occurrence in occurrences] == [1]

    trailing_source = _write_log(
        tmp_path,
        "trailing-boundary.log",
        _live_line(_payload(), boundary="Starting game #1 as PlayerClass.IRONCLAD trailing"),
    )
    with pytest.raises(audit.EvidenceError, match="invalid game boundary") as error:
        audit.load_adaptive_logs([trailing_source], utc_offset_hours=8)
    assert str(error.value).startswith(f"{trailing_source}:1:")


@pytest.mark.parametrize(
    "outcome",
    ("success", "forced", "unsupported", "candidate_generation_failed"),
)
def test_loads_every_valid_outcome_contract_with_live_shaped_values(tmp_path: Path, outcome: str):
    source = _write_log(tmp_path, f"{outcome}.log", _live_line(_outcome_payload(outcome)))

    occurrences, _ = audit.load_adaptive_logs([source], utc_offset_hours=8)

    assert occurrences[0].fields["outcome"] == outcome
    if outcome == "candidate_generation_failed":
        assert occurrences[0].fields["fallback_candidate"].startswith("mode:conservative,")


@pytest.mark.parametrize(
    ("name", "payload"),
    [
        (
            "success-pair",
            _payload(
                candidate_pair="generation_failed",
                conservative_candidate="unavailable",
                aggressive_candidate="unavailable",
                minimum_elites="unavailable",
                added_elites="unavailable",
            ),
        ),
        ("forced-selection", _outcome_payload("forced").replace("selected=conservative", "selected=aggressive")),
        ("unsupported-pair", _outcome_payload("unsupported").replace("candidate_pair=not_attempted", "candidate_pair=complete")),
        ("unsupported-fallback", _outcome_payload("unsupported").replace("fallback_candidate=not_applicable", "fallback_candidate=unavailable")),
        ("failure-pair", _outcome_payload("candidate_generation_failed").replace("candidate_pair=generation_failed", "candidate_pair=not_attempted")),
        ("failure-selection", _outcome_payload("candidate_generation_failed").replace("selected=conservative", "selected=aggressive")),
        ("failure-fallback", _outcome_payload("candidate_generation_failed").replace("fallback_candidate=mode:conservative", "fallback_candidate=unavailable")),
    ],
)
def test_rejects_invalid_outcome_candidate_pair_fallback_and_selection_matrix(
    tmp_path: Path, name: str, payload: str
):
    _assert_rejected_live_line(tmp_path, f"{name}.log", payload)


@pytest.mark.parametrize(
    ("name", "payload"),
    [
        (
            "recovery",
            _payload(conservative_candidate=_candidate("conservative", symbols="M/T/?/$/R/?/M/R", elite_count=0, elite_floors="none", recovery_before="1")),
        ),
        ("minimum-elites", _payload(minimum_elites="99")),
        ("added-elites", _payload(added_elites="99")),
        ("hp", _payload(hp="bad")),
        ("hp-pct", _payload(hp_pct="nan")),
        ("deck", _payload(deck="-1")),
        ("potion", _payload(potion="x")),
        ("relic", _payload(relic="x")),
        ("elite-seen", _payload(elite_seen="unavailable")),
        ("last-rest", _payload(last_rest_floor="-1")),
        ("invalid-state-populated", _payload(state_valid="false")),
        ("act-zero", _payload(act="0")),
    ],
)
def test_rejects_invalid_candidate_derivations_counts_and_scalar_availability(
    tmp_path: Path, name: str, payload: str
):
    _assert_rejected_live_line(tmp_path, f"{name}.log", payload)


@pytest.mark.parametrize(
    ("name", "payload"),
    [
        ("character-unavailable", _payload(character="unavailable")),
        ("act-unavailable", _payload(act="unavailable")),
        ("deck-above-cap", _payload(deck="8")),
        ("potion-above-cap", _payload(potion="3")),
        ("relic-above-cap", _payload(relic="3")),
        ("budget-above-domain", _payload(budget="2")),
        ("aggressive-without-budget", _payload(budget="0")),
        (
            "success-conservative-with-budget",
            _payload(selected="conservative", budget="1"),
        ),
        (
            "forced-conservative-with-budget",
            _outcome_payload("forced").replace("budget=0", "budget=1"),
        ),
        (
            "unsupported-conservative-with-budget",
            _outcome_payload("unsupported").replace("budget=0", "budget=1"),
        ),
        (
            "generation-failure-conservative-with-budget",
            _outcome_payload("candidate_generation_failed").replace(
                "budget=0", "budget=1"
            ),
        ),
    ],
)
def test_rejects_impossible_valid_state_resources_and_budget_selection_matrix(
    tmp_path: Path, name: str, payload: str
):
    _assert_rejected_live_line(tmp_path, f"{name}.log", payload)


def test_loads_valid_resource_caps_and_budget_selection_boundaries(tmp_path: Path):
    payloads = [
        _payload(deck="7", potion="2", relic="2"),
        _payload(
            character="unavailable",
            act="unavailable",
            state_valid="false",
            hp="unavailable",
            hp_pct="unavailable",
            deck="unavailable",
            potion="unavailable",
            relic="unavailable",
            elite_seen="unavailable",
            last_rest_floor="unavailable",
            budget="0",
            selected="conservative",
        ),
    ]
    source = _write_log(
        tmp_path,
        "valid-scalar-boundaries.log",
        [
            _line("Starting game #1 as PlayerClass.IRONCLAD"),
            *[
                _line(f"[ADAPTIVE_ROUTE] {payload}", millisecond=index)
                for index, payload in enumerate(payloads, start=100)
            ],
        ],
    )

    occurrences, _ = audit.load_adaptive_logs([source], utc_offset_hours=8)

    assert [occurrence.fields["state_valid"] for occurrence in occurrences] == [
        "true",
        "false",
    ]


def test_accepts_invalid_state_only_with_unavailable_state_scalars():
    payload = _payload(
        state_valid="false",
        hp="unavailable",
        hp_pct="unavailable",
        deck="unavailable",
        potion="unavailable",
        relic="unavailable",
        elite_seen="unavailable",
        last_rest_floor="unavailable",
        budget="0",
        selected="conservative",
    )

    fields, _, _ = audit.parse_adaptive_payload(payload)

    assert fields["state_valid"] == "false"


def test_rejects_invalid_state_with_aggressive_budget_using_log_provenance(
    tmp_path: Path,
):
    payload = _payload(
        state_valid="false",
        hp="unavailable",
        hp_pct="unavailable",
        deck="unavailable",
        potion="unavailable",
        relic="unavailable",
        elite_seen="unavailable",
        last_rest_floor="unavailable",
        budget="1",
        selected="aggressive",
    )

    _assert_rejected_live_line(tmp_path, "invalid-state-aggressive.log", payload)


@pytest.mark.parametrize(
    "payload",
    [
        lambda: _payload().replace(" ", "  ", 1),
        lambda: _payload().replace(" ", "\t", 1),
        lambda: " " + _payload(),
        lambda: _payload() + " ",
    ],
)
def test_rejects_noncanonical_payload_whitespace_before_deduplication(payload):
    with pytest.raises(audit.EvidenceError, match="canonical"):
        audit.parse_adaptive_payload(payload())


def test_malformed_whitespace_cannot_become_a_second_deduplication_key(tmp_path: Path):
    canonical = _payload()
    source = _write_log(
        tmp_path,
        "whitespace-dedup.log",
        [
            _line("Starting game #1 as PlayerClass.IRONCLAD"),
            _line(f"[ADAPTIVE_ROUTE] {canonical}", millisecond=100),
            _line(f"[ADAPTIVE_ROUTE] {canonical.replace(' ', '  ', 1)}", millisecond=200),
        ],
    )

    with pytest.raises(audit.EvidenceError, match="canonical") as error:
        audit.load_adaptive_logs([source], utc_offset_hours=8)
    assert str(error.value).startswith(f"{source}:3:")


@pytest.mark.parametrize("utc_offset_hours", [True, float("nan"), float("inf"), float("-inf"), -24, 24])
def test_rejects_utc_offsets_outside_datetime_timezone_domain(utc_offset_hours: float):
    with pytest.raises(audit.EvidenceError, match="UTC offset"):
        audit._validate_utc_offset(utc_offset_hours)


@pytest.mark.parametrize("utc_offset_hours", [-23.999, 23.999])
def test_accepts_utc_offsets_just_inside_datetime_timezone_domain(utc_offset_hours: float):
    assert audit._validate_utc_offset(utc_offset_hours) == utc_offset_hours


def test_converts_fractional_utc_offset_to_known_unix_timestamp(tmp_path: Path):
    source = _write_log(tmp_path, "fractional-offset.log", _live_line(_payload()))

    occurrences, _ = audit.load_adaptive_logs([source], utc_offset_hours=5.5)

    assert occurrences[0].unix_time == datetime(
        2026, 7, 22, 12, 0, 0, 100000, tzinfo=timezone(timedelta(hours=5.5))
    ).timestamp()
