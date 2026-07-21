from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import replace
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from analysis_scripts import adaptive_route_opportunity_audit as audit


def _epoch_microseconds(value: datetime) -> int:
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    delta = value.astimezone(timezone.utc) - epoch
    return (delta.days * 24 * 60 * 60 + delta.seconds) * 1_000_000 + delta.microseconds


def _candidate(
    mode: str,
    *,
    start_y: int = 7,
    symbols: str,
    elite_count: int,
    elite_floors: str,
    recovery_before: str = "none",
    recovery_after: str = "none",
) -> str:
    return (
        f"mode:{mode},start_y:{start_y},symbols:{symbols},elite_count:{elite_count},"
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
    assert first.unix_time_us == _epoch_microseconds(
        datetime(
            2026,
            7,
            22,
            12,
            0,
            0,
            100000,
            tzinfo=timezone(timedelta(hours=8)),
        )
    )
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

    assert occurrences[0].unix_time_us == _epoch_microseconds(
        datetime(
            2026,
            7,
            22,
            12,
            0,
            0,
            100000,
            tzinfo=timezone(timedelta(hours=5.5)),
        )
    )


def _task2_payload(**overrides: str) -> str:
    values = {
        "aggressive_candidate": _candidate(
            "aggressive",
            symbols="M/T/?/$/R/M/E/R",
            elite_count=1,
            elite_floors="14",
            recovery_before="2",
            recovery_after="1",
        )
    }
    values.update(overrides)
    return _payload(**values)


def _graph_node(
    x: int, y: int, symbol: str, *children: tuple[int, int]
) -> dict:
    return {
        "x": x,
        "y": y,
        "symbol": symbol,
        "children": [{"x": child_x, "y": child_y} for child_x, child_y in children],
    }


def _task2_graph(
    *,
    ambiguous_conservative: bool = True,
    ambiguous_before_divergence: bool = False,
    different_immediate: bool = False,
) -> list[dict]:
    nodes = [
        _graph_node(2, 6, "?", (2, 7), (4, 7)),
        _graph_node(3, 6, "?", (2, 7)),
        _graph_node(2, 7, "M", (2, 8)),
        _graph_node(4, 7, "E"),
        _graph_node(6, 7, "M", (6, 8)),
        _graph_node(2, 8, "T", (2, 9)),
        _graph_node(6, 8, "T", (6, 9)),
        _graph_node(2, 9, "?", (2, 10)),
        _graph_node(6, 9, "?", (6, 10)),
        _graph_node(2, 10, "$", (2, 11)),
        _graph_node(6, 10, "$", (6, 11)),
        _graph_node(2, 11, "R", (1, 12), (0, 12)),
        _graph_node(6, 11, "R", (6, 12)),
        _graph_node(1, 12, "?", (1, 13)),
        _graph_node(0, 12, "M", (0, 13)),
        _graph_node(6, 12, "?", (6, 13)),
        _graph_node(
            1,
            13,
            "M",
            (0, 14),
            *((2, 14),) if ambiguous_conservative else (),
        ),
        _graph_node(0, 13, "E", (1, 14)),
        _graph_node(6, 13, "M", (6, 14)),
        _graph_node(0, 14, "R"),
        _graph_node(1, 14, "R"),
        _graph_node(2, 14, "R"),
        _graph_node(6, 14, "R"),
    ]
    by_coordinate = {(node["x"], node["y"]): node for node in nodes}

    if ambiguous_before_divergence:
        by_coordinate[(2, 9)]["children"].append({"x": 3, "y": 10})
        nodes.append(_graph_node(3, 10, "$", (2, 11)))

    if different_immediate:
        by_coordinate[(2, 11)]["children"] = [{"x": 1, "y": 12}]
        by_coordinate[(4, 7)].update(symbol="M", children=[{"x": 4, "y": 8}])
        nodes.extend(
            [
                _graph_node(4, 8, "T", (4, 9)),
                _graph_node(4, 9, "?", (4, 10)),
                _graph_node(4, 10, "$", (4, 11)),
                _graph_node(4, 11, "R", (4, 12)),
                _graph_node(4, 12, "M", (4, 13)),
                _graph_node(4, 13, "E", (4, 14)),
                _graph_node(4, 14, "R"),
            ]
        )
    return nodes


def _path_summary(choice: int, coordinates: list[tuple[int, int]], graph: list[dict]) -> dict:
    by_coordinate = {(node["x"], node["y"]): node for node in graph}
    labels = [
        f"{by_coordinate[coordinate]['symbol']}@{coordinate[0]},{coordinate[1]}"
        for coordinate in coordinates
    ]
    return {
        "choice": choice,
        "label": " -> ".join(labels),
        "nodes": [by_coordinate[coordinate]["symbol"] for coordinate in coordinates],
    }


def _task2_trace_row(
    *,
    unix_time: float = 100.0,
    ambiguous_conservative: bool = True,
    ambiguous_before_divergence: bool = False,
    different_immediate: bool = False,
    advertise_superset: bool = False,
) -> dict:
    graph = _task2_graph(
        ambiguous_conservative=ambiguous_conservative,
        ambiguous_before_divergence=ambiguous_before_divergence,
        different_immediate=different_immediate,
    )
    conservative_prefix = [(2, 7), (2, 8), (2, 9), (2, 10), (2, 11), (1, 12), (1, 13)]
    paths = [_path_summary(0, conservative_prefix + [(0, 14)], graph)]
    if ambiguous_conservative:
        paths.append(_path_summary(0, conservative_prefix + [(2, 14)], graph))

    if different_immediate:
        aggressive = [
            (4, 7), (4, 8), (4, 9), (4, 10),
            (4, 11), (4, 12), (4, 13), (4, 14),
        ]
        paths.append(_path_summary(1, aggressive, graph))
        action_coordinate = (4, 7)
        action_choice = 1
    else:
        aggressive = [
            (2, 7), (2, 8), (2, 9), (2, 10),
            (2, 11), (0, 12), (0, 13), (1, 14),
        ]
        paths.append(_path_summary(0, aggressive, graph))
        paths.append(_path_summary(1, [(4, 7)], graph))
        action_coordinate = (2, 7)
        action_choice = 0

    by_coordinate = {(node["x"], node["y"]): node for node in graph}
    next_coordinates = [(2, 7), (4, 7)]
    if advertise_superset:
        next_coordinates.append((6, 7))
    return {
        "unix_time": unix_time,
        "act": 1,
        "floor": 8,
        "screen_type": "ScreenType.MAP",
        "screen": {
            "type": "ScreenType.MAP",
            "current_node": {"x": 2, "y": 6, "symbol": "?"},
            "next_nodes": [
                {"x": x, "y": y, "symbol": by_coordinate[(x, y)]["symbol"]}
                for x, y in next_coordinates
            ],
            "map": {"nodes": graph},
            "paths": paths,
        },
        "action": {
            "type": "ChooseMapNodeAction",
            "choice_index": action_choice,
            "node": {
                "x": action_coordinate[0],
                "y": action_coordinate[1],
                "symbol": by_coordinate[action_coordinate]["symbol"],
            },
        },
    }


def _write_trace(tmp_path: Path, name: str, rows: list[dict]) -> Path:
    path = tmp_path / name
    text = "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n\n"
    path.write_text(text, encoding="utf-8")
    return path


def _task2_record(
    *, payload: str | None = None, unix_times: tuple[float, ...] = (100.0,)
) -> audit.AdaptiveRecord:
    payload = payload or _task2_payload()
    fields, conservative, aggressive = audit.parse_adaptive_payload(payload)
    occurrences = tuple(
        audit.AdaptiveOccurrence(
            game_number=1,
            source_path=Path("synthetic-adaptive.log"),
            line_number=index + 1,
            timestamp=datetime(2026, 7, 22, tzinfo=timezone.utc),
            unix_time=Decimal(str(unix_time)),
            payload=payload,
            fields=fields,
            conservative=conservative,
            aggressive=aggressive,
        )
        for index, unix_time in enumerate(unix_times)
    )
    return audit.AdaptiveRecord(game_number=1, payload=payload, occurrences=occurrences)


def _load_task2_decisions(tmp_path: Path, name: str, rows: list[dict]):
    trace = _write_trace(tmp_path, name, rows)
    return audit.load_decision_trace(trace)


def _coordinate_from_path_label(label: str) -> tuple[int, int]:
    coordinate = label.split(" -> ", 1)[0].split("@", 1)[1]
    x, y = coordinate.split(",", 1)
    return int(x), int(y)


def _reorder_trace_representation(row: dict) -> None:
    row["screen"]["map"]["nodes"].reverse()
    for node in row["screen"]["map"]["nodes"]:
        node["children"].reverse()
    row["screen"]["next_nodes"].reverse()
    choice_by_coordinate = {
        (node["x"], node["y"]): choice
        for choice, node in enumerate(row["screen"]["next_nodes"])
    }
    for path in row["screen"]["paths"]:
        path["choice"] = choice_by_coordinate[_coordinate_from_path_label(path["label"])]
    row["screen"]["paths"].reverse()
    action = row["action"]["node"]
    row["action"]["choice_index"] = choice_by_coordinate[(action["x"], action["y"])]


def _change_fingerprint_component(row: dict, component: str) -> None:
    nodes = row["screen"]["map"]["nodes"]
    by_coordinate = {(node["x"], node["y"]): node for node in nodes}
    if component == "current_node":
        row["screen"]["current_node"] = {"x": 3, "y": 6, "symbol": "?"}
    elif component == "next_nodes":
        row["screen"]["next_nodes"].append({"x": 6, "y": 7, "symbol": "M"})
    elif component == "graph":
        by_coordinate[(6, 14)]["symbol"] = "M"
    elif component == "paths":
        row["screen"]["paths"].pop()
    elif component == "action":
        row["action"] = {
            "type": "ChooseMapNodeAction",
            "choice_index": 1,
            "node": {"x": 4, "y": 7, "symbol": "E"},
        }
    else:
        raise AssertionError(f"unexpected fingerprint component {component}")


def test_load_decision_trace_parses_all_jsonl_and_ignores_map_boss_actions(tmp_path: Path):
    node_row = _task2_trace_row(unix_time=102.0)
    boss_row = copy.deepcopy(node_row)
    boss_row["unix_time"] = 101.0
    boss_row["action"] = {"type": "ChooseMapBossAction", "choice_index": 0}
    boss_row["screen"]["next_nodes"] = []
    boss_row["screen"]["paths"] = []
    non_map_row = {"unix_time": 100.0, "screen_type": "ScreenType.COMBAT"}
    trace = _write_trace(tmp_path, "mixed.jsonl", [non_map_row, boss_row, node_row])

    decisions, source = audit.load_decision_trace(trace)

    assert [decision.unix_time_us for decision in decisions] == [102_000_000]
    assert source["source_path"] == str(trace)
    assert source["sha256"] == hashlib.sha256(trace.read_bytes()).hexdigest()
    assert source["record_count"] == 3
    assert source["map_record_count"] == 2
    assert source["node_action_record_count"] == 1
    assert source["boss_action_record_count"] == 1


@pytest.mark.parametrize(
    ("contents", "message"),
    [
        ("{not-json}\n", "malformed decision trace JSON"),
        ("[]\n", "decision trace row must be an object"),
        (
            '{"screen_type":"ScreenType.COMBAT","unix_time":NaN}\n',
            "malformed decision trace JSON",
        ),
        (
            '{"screen_type":"ScreenType.MAP","unix_time":1e9999999999999999999}\n',
            "malformed decision trace JSON",
        ),
        (
            '{"screen_type":"ScreenType.COMBAT","screen_type":"ScreenType.MAP"}\n',
            "malformed decision trace JSON",
        ),
    ],
)
def test_load_decision_trace_rejects_malformed_or_nonobject_jsonl(
    tmp_path: Path, contents: str, message: str
):
    trace = tmp_path / "malformed.jsonl"
    trace.write_text(contents, encoding="utf-8")

    with pytest.raises(audit.EvidenceError, match=message) as error:
        audit.load_decision_trace(trace)

    assert str(error.value).startswith(f"{trace}:1:")


@pytest.mark.parametrize("bad_symbol", [[], {}, ["M"], {"symbol": "M"}])
def test_load_decision_trace_rejects_non_string_path_symbols_with_provenance(
    tmp_path: Path, bad_symbol: object
):
    row = _task2_trace_row()
    row["screen"]["paths"][0]["nodes"][0] = bad_symbol
    trace = _write_trace(tmp_path, "bad-path-symbol.jsonl", [row])

    with pytest.raises(audit.EvidenceError, match="path nodes") as error:
        audit.load_decision_trace(trace)

    assert str(error.value).startswith(f"{trace}:1:")


def test_load_decision_trace_rejects_extreme_epoch_number_with_provenance(
    tmp_path: Path,
):
    row = _task2_trace_row()
    row["unix_time"] = 10**400
    trace = _write_trace(tmp_path, "extreme-time.jsonl", [row])

    with pytest.raises(audit.EvidenceError, match="unix_time") as error:
        audit.load_decision_trace(trace)

    assert str(error.value).startswith(f"{trace}:1:")


def test_decision_trace_source_identity_counts_raw_bytes_and_physical_lines(
    tmp_path: Path,
):
    node = json.dumps(_task2_trace_row(), sort_keys=True)
    non_map = json.dumps({"screen_type": "ScreenType.COMBAT"}, sort_keys=True)
    raw = ("\r\n" + node + "\r\n\r\n" + non_map).encode("utf-8")
    trace = tmp_path / "physical-lines.jsonl"
    trace.write_bytes(raw)

    decisions, source = audit.load_decision_trace(trace)

    assert len(decisions) == 1
    assert source["byte_count"] == len(raw)
    assert source["line_count"] == 4
    assert source["record_count"] == 2


@pytest.mark.parametrize(
    ("case", "message"),
    [
        ("missing-child", "graph child"),
        ("child-skips-row", "advance exactly one row"),
        ("action-unadvertised", "advertised"),
        ("action-not-child", "reachable child"),
        ("next-symbol", "next-node symbol"),
        ("current-symbol", "current-node symbol"),
        ("path-symbol", "path nodes"),
        ("missing-paths", "paths"),
        ("duplicate-graph", "duplicate coordinate"),
        ("duplicate-child", "duplicate children"),
        ("duplicate-next", "duplicate next nodes"),
        ("graph-x-out-of-range", "seven-column"),
        ("graph-y-out-of-range", "map y"),
        ("child-y-out-of-range", "map y"),
        ("next-y-out-of-range", "map y"),
        ("path-y-out-of-range", "map y"),
        ("action-choice-mismatch", "choice_index does not identify"),
        ("path-non-child", "non-child graph edge"),
    ],
)
def test_load_decision_trace_rejects_invalid_graph_next_action_and_paths(
    tmp_path: Path, case: str, message: str
):
    row = _task2_trace_row(advertise_superset=True)
    nodes = row["screen"]["map"]["nodes"]
    by_coordinate = {(node["x"], node["y"]): node for node in nodes}
    if case == "missing-child":
        by_coordinate[(2, 6)]["children"][0] = {"x": 5, "y": 7}
    elif case == "child-skips-row":
        by_coordinate[(2, 6)]["children"][0] = {"x": 2, "y": 8}
    elif case == "action-unadvertised":
        row["screen"]["next_nodes"] = row["screen"]["next_nodes"][1:]
    elif case == "action-not-child":
        row["action"]["choice_index"] = 2
        row["action"]["node"] = {"x": 6, "y": 7, "symbol": "M"}
    elif case == "next-symbol":
        row["screen"]["next_nodes"][0]["symbol"] = "E"
    elif case == "current-symbol":
        row["screen"]["current_node"]["symbol"] = "M"
    elif case == "path-symbol":
        row["screen"]["paths"][0]["nodes"][0] = "E"
    elif case == "missing-paths":
        row["screen"].pop("paths")
    elif case == "duplicate-graph":
        nodes.append(copy.deepcopy(nodes[0]))
    elif case == "duplicate-child":
        by_coordinate[(2, 6)]["children"].append(
            copy.deepcopy(by_coordinate[(2, 6)]["children"][0])
        )
    elif case == "duplicate-next":
        row["screen"]["next_nodes"].append(
            copy.deepcopy(row["screen"]["next_nodes"][0])
        )
    elif case == "graph-x-out-of-range":
        by_coordinate[(3, 6)]["x"] = 7
    elif case == "graph-y-out-of-range":
        by_coordinate[(3, 6)]["y"] = 15
    elif case == "child-y-out-of-range":
        by_coordinate[(2, 6)]["children"][0]["y"] = 15
    elif case == "next-y-out-of-range":
        row["screen"]["next_nodes"][0]["y"] = 15
    elif case == "path-y-out-of-range":
        row["screen"]["paths"][0]["label"] = row["screen"]["paths"][0][
            "label"
        ].replace("R@0,14", "R@0,15")
    elif case == "action-choice-mismatch":
        row["action"]["choice_index"] = 1
    elif case == "path-non-child":
        row["screen"]["paths"][0]["label"] = row["screen"]["paths"][0][
            "label"
        ].replace("T@2,8", "T@6,8")

    trace = _write_trace(tmp_path, f"{case}.jsonl", [row])
    with pytest.raises(audit.EvidenceError, match=message) as error:
        audit.load_decision_trace(trace)

    assert str(error.value).startswith(f"{trace}:1:")


def test_join_occurrences_uses_unique_nearest_row_and_requires_duplicate_agreement(
    tmp_path: Path,
):
    record = _task2_record(unix_times=(100.0, 101.0))
    first = _task2_trace_row(unix_time=100.003, advertise_superset=True)
    second = _task2_trace_row(unix_time=101.002, advertise_superset=True)
    decisions, _ = _load_task2_decisions(tmp_path, "nearest.jsonl", [first, second])

    joined = audit.join_occurrences([record], decisions, max_join_seconds=0.01)

    assert len(joined) == 1
    assert [item.decision.unix_time_us for item in joined[0].occurrences] == [
        100_003_000,
        101_002_000,
    ]
    assert joined[0].occurrences[0].delta_us == 3_000
    assert joined[0].decision.semantic_fingerprint == decisions[0].semantic_fingerprint


@pytest.mark.parametrize(
    "component", ["current_node", "next_nodes", "graph", "paths", "action"]
)
def test_duplicate_occurrences_reject_each_fingerprint_disagreement(
    tmp_path: Path, component: str
):
    record = _task2_record(unix_times=(100.0, 101.0))
    first = _task2_trace_row(unix_time=100.0)
    second = _task2_trace_row(unix_time=101.0)
    _change_fingerprint_component(second, component)
    decisions, _ = _load_task2_decisions(
        tmp_path, f"fingerprint-{component}.jsonl", [first, second]
    )

    with pytest.raises(audit.EvidenceError, match="duplicate occurrences disagree"):
        audit.join_occurrences([record], decisions, max_join_seconds=0.01)


def test_semantic_fingerprint_ignores_harmless_representation_order(tmp_path: Path):
    first = _task2_trace_row(unix_time=100.0, advertise_superset=True)
    second = copy.deepcopy(first)
    second["unix_time"] = 101.0
    _reorder_trace_representation(second)
    decisions, _ = _load_task2_decisions(
        tmp_path, "representation-order.jsonl", [first, second]
    )

    assert decisions[0].semantic_fingerprint == decisions[1].semantic_fingerprint
    record = _task2_record(unix_times=(100.0, 101.0))
    joined = audit.join_occurrences([record], decisions, max_join_seconds=0.01)
    assert len(joined) == 1


def test_join_occurrences_rejects_epoch_scale_exact_tie(tmp_path: Path):
    record = _task2_record(unix_times=(1784563200.123,))
    rows = [
        _task2_trace_row(unix_time=1784563200.118),
        _task2_trace_row(unix_time=1784563200.128),
    ]
    decisions, _ = _load_task2_decisions(tmp_path, "epoch-tie.jsonl", rows)

    with pytest.raises(audit.EvidenceError, match="tied nearest"):
        audit.join_occurrences([record], decisions, max_join_seconds=0.01)


def test_join_occurrences_distinguishes_adjacent_microsecond_non_tie(tmp_path: Path):
    record = _task2_record(unix_times=(1784563200.123,))
    rows = [
        _task2_trace_row(unix_time=1784563200.118),
        _task2_trace_row(unix_time=1784563200.128001),
    ]
    decisions, _ = _load_task2_decisions(tmp_path, "epoch-adjacent.jsonl", rows)

    joined = audit.join_occurrences([record], decisions, max_join_seconds=0.01)

    assert joined[0].decision.unix_time_us == 1784563200118000
    assert joined[0].occurrences[0].delta_us == 5000


@pytest.mark.parametrize(
    "trace_time", [1784563200.113, 1784563200.133], ids=["before", "after"]
)
def test_join_occurrences_accepts_exact_tolerance_boundary_on_both_sides(
    tmp_path: Path, trace_time: float
):
    record = _task2_record(unix_times=(1784563200.123,))
    decisions, _ = _load_task2_decisions(
        tmp_path, "exact-boundary.jsonl", [_task2_trace_row(unix_time=trace_time)]
    )

    joined = audit.join_occurrences([record], decisions, max_join_seconds=0.01)

    assert joined[0].occurrences[0].delta_us == 10_000


@pytest.mark.parametrize(
    ("trace_time", "expected_delta_us"),
    [
        (1784563200.113001, 9_999),
        (1784563200.132999, 9_999),
    ],
    ids=["before", "after"],
)
def test_join_occurrences_accepts_just_inside_boundary_on_both_sides(
    tmp_path: Path, trace_time: float, expected_delta_us: int
):
    record = _task2_record(unix_times=(1784563200.123,))
    decisions, _ = _load_task2_decisions(
        tmp_path, "inside-boundary.jsonl", [_task2_trace_row(unix_time=trace_time)]
    )

    joined = audit.join_occurrences([record], decisions, max_join_seconds=0.01)

    assert joined[0].occurrences[0].delta_us == expected_delta_us


@pytest.mark.parametrize(
    "trace_time", [1784563200.112999, 1784563200.133001], ids=["before", "after"]
)
def test_join_occurrences_rejects_just_outside_boundary_on_both_sides(
    tmp_path: Path, trace_time: float
):
    record = _task2_record(unix_times=(1784563200.123,))
    decisions, _ = _load_task2_decisions(
        tmp_path, "outside-boundary.jsonl", [_task2_trace_row(unix_time=trace_time)]
    )

    with pytest.raises(audit.EvidenceError, match="outside join tolerance"):
        audit.join_occurrences([record], decisions, max_join_seconds=0.01)


@pytest.mark.parametrize(
    ("case", "message"),
    [
        ("missing", "missing decision-trace join"),
        ("out-of-tolerance", "outside join tolerance"),
        ("tied", "tied nearest decision-trace join"),
    ],
)
def test_join_occurrences_rejects_missing_out_of_tolerance_and_tied_rows(
    tmp_path: Path, case: str, message: str
):
    record = _task2_record()
    if case == "missing":
        rows = [_task2_trace_row(unix_time=100.0)]
        rows[0]["act"] = 2
    elif case == "out-of-tolerance":
        rows = [_task2_trace_row(unix_time=100.02)]
    else:
        rows = [
            _task2_trace_row(unix_time=99.995),
            _task2_trace_row(unix_time=100.005),
        ]
    decisions, _ = _load_task2_decisions(tmp_path, f"{case}.jsonl", rows)

    with pytest.raises(audit.EvidenceError, match=message):
        audit.join_occurrences([record], decisions, max_join_seconds=0.01)


def test_join_occurrences_rejects_semantically_contradictory_duplicate_callbacks(
    tmp_path: Path,
):
    record = _task2_record(unix_times=(100.0, 101.0))
    first = _task2_trace_row(unix_time=100.0)
    second = _task2_trace_row(unix_time=101.0)
    second["action"] = {
        "type": "ChooseMapNodeAction",
        "choice_index": 1,
        "node": {"x": 4, "y": 7, "symbol": "E"},
    }
    decisions, _ = _load_task2_decisions(tmp_path, "contradictory.jsonl", [first, second])

    with pytest.raises(audit.EvidenceError, match="duplicate occurrences disagree"):
        audit.join_occurrences([record], decisions, max_join_seconds=0.01)


def test_classify_candidate_pair_preserves_later_ambiguity_and_proves_first_divergence(
    tmp_path: Path,
):
    record = _task2_record()
    decisions, _ = _load_task2_decisions(
        tmp_path,
        "frozen-shape.jsonl",
        [_task2_trace_row(advertise_superset=True)],
    )
    joined = audit.join_occurrences([record], decisions, max_join_seconds=0.01)[0]

    evidence = audit.classify_candidate_pair(joined)

    assert evidence.immediate_classification == "same"
    assert evidence.conservative_immediate == (2, 7)
    assert evidence.aggressive_immediate == (2, 7)
    assert evidence.conservative_match_count == 2
    assert evidence.aggressive_match_count == 1
    assert evidence.conservative_path is None
    assert evidence.aggressive_path[0] == (2, 7)
    assert evidence.conservative_coordinate_sets[-1] == ((0, 14), (2, 14))
    assert evidence.first_divergence == audit.Divergence(
        index=5,
        map_y=12,
        entered_floor=13,
        conservative=(1, 12),
        aggressive=(0, 12),
    )


def test_matching_candidates_excludes_advertised_symbol_identical_non_child_branch(
    tmp_path: Path,
):
    record = _task2_record()
    decisions, _ = _load_task2_decisions(
        tmp_path,
        "unreachable-symbol-identical.jsonl",
        [_task2_trace_row(advertise_superset=True)],
    )
    conservative = record.occurrences[0].conservative

    matches = audit.matching_candidate_paths(conservative, decisions[0])

    assert len(matches) == 2
    assert all(path[0] == (2, 7) for path in matches)
    assert all((6, 7) not in path for path in matches)


def test_classify_candidate_pair_reports_unique_paths_when_each_candidate_has_one(
    tmp_path: Path,
):
    record = _task2_record()
    decisions, _ = _load_task2_decisions(
        tmp_path,
        "unique.jsonl",
        [_task2_trace_row(ambiguous_conservative=False)],
    )
    joined = audit.join_occurrences([record], decisions, max_join_seconds=0.01)[0]

    evidence = audit.classify_candidate_pair(joined)

    assert evidence.conservative_path[0] == (2, 7)
    assert evidence.aggressive_path[0] == (2, 7)
    assert evidence.conservative_match_count == evidence.aggressive_match_count == 1


def test_classify_candidate_pair_does_not_guess_divergence_after_ambiguous_prefix(
    tmp_path: Path,
):
    record = _task2_record()
    decisions, _ = _load_task2_decisions(
        tmp_path,
        "ambiguous-prefix.jsonl",
        [_task2_trace_row(ambiguous_before_divergence=True)],
    )
    joined = audit.join_occurrences([record], decisions, max_join_seconds=0.01)[0]

    evidence = audit.classify_candidate_pair(joined)

    assert evidence.conservative_coordinate_sets[3] == ((2, 10), (3, 10))
    assert evidence.aggressive_coordinate_sets[3] == ((2, 10), (3, 10))
    assert evidence.first_divergence is None


def test_classify_candidate_pair_reports_different_immediate_coordinates(tmp_path: Path):
    record = _task2_record()
    decisions, _ = _load_task2_decisions(
        tmp_path,
        "different-immediate.jsonl",
        [_task2_trace_row(different_immediate=True)],
    )
    joined = audit.join_occurrences([record], decisions, max_join_seconds=0.01)[0]

    evidence = audit.classify_candidate_pair(joined)

    assert evidence.immediate_classification == "different"
    assert evidence.first_divergence == audit.Divergence(
        index=0,
        map_y=7,
        entered_floor=8,
        conservative=(2, 7),
        aggressive=(4, 7),
    )


def test_classify_candidate_pair_marks_zero_match_candidate_ambiguous(tmp_path: Path):
    payload = _task2_payload(
        conservative_candidate=_candidate(
            "conservative",
            symbols="M/T/?/$/R/?/?/R",
            elite_count=0,
            elite_floors="none",
        )
    )
    record = _task2_record(payload=payload)
    decisions, _ = _load_task2_decisions(
        tmp_path, "zero-match.jsonl", [_task2_trace_row()]
    )
    joined = audit.join_occurrences([record], decisions, max_join_seconds=0.01)[0]

    evidence = audit.classify_candidate_pair(joined)

    assert evidence.conservative_match_count == 0
    assert evidence.conservative_path is None
    assert evidence.immediate_classification == "ambiguous"
    assert evidence.first_divergence is None


def test_classify_candidate_pair_rejects_selected_action_contradiction(tmp_path: Path):
    record = _task2_record()
    row = _task2_trace_row()
    row["action"] = {
        "type": "ChooseMapNodeAction",
        "choice_index": 1,
        "node": {"x": 4, "y": 7, "symbol": "E"},
    }
    decisions, _ = _load_task2_decisions(tmp_path, "selected-contradiction.jsonl", [row])
    joined = audit.join_occurrences([record], decisions, max_join_seconds=0.01)[0]

    with pytest.raises(audit.EvidenceError, match="selected candidate contradicts joined action"):
        audit.classify_candidate_pair(joined)


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (
            _task2_payload(
                conservative_candidate=_candidate(
                    "conservative",
                    start_y=6,
                    symbols="M/T/?/$/R/?/M/R",
                    elite_count=0,
                    elite_floors="none",
                )
            ),
            "start_y",
        ),
        (
            _task2_payload(
                aggressive_candidate=_candidate(
                    "aggressive",
                    symbols="M/T/?/$/R/E/R",
                    elite_count=1,
                    elite_floors="13",
                    recovery_before="1",
                    recovery_after="1",
                )
            ),
            "extent",
        ),
        (
            _task2_payload(
                conservative_candidate=_candidate(
                    "conservative",
                    start_y=8,
                    symbols="M/T/?/$/R/?/M/R",
                    elite_count=0,
                    elite_floors="none",
                ),
                aggressive_candidate=_candidate(
                    "aggressive",
                    start_y=8,
                    symbols="M/T/?/$/R/M/E/R",
                    elite_count=1,
                    elite_floors="15",
                    recovery_before="2",
                    recovery_after="1",
                ),
            ),
            "extent",
        ),
    ],
    ids=["different-start", "different-length", "past-map-end"],
)
def test_parse_complete_candidate_pair_rejects_impossible_geometry(
    payload: str, message: str
):
    with pytest.raises(audit.EvidenceError, match=message):
        audit.parse_adaptive_payload(payload)


def test_classify_candidate_pair_revalidates_geometry_before_positional_analysis(
    tmp_path: Path,
):
    record = _task2_record()
    decisions, _ = _load_task2_decisions(
        tmp_path, "manual-impossible-pair.jsonl", [_task2_trace_row()]
    )
    joined = audit.join_occurrences([record], decisions, max_join_seconds=0.01)[0]
    occurrence = joined.record.occurrences[0]
    impossible = replace(occurrence.conservative, start_y=6)
    malformed_occurrence = replace(occurrence, conservative=impossible)
    malformed_record = replace(joined.record, occurrences=(malformed_occurrence,))
    malformed_joined = replace(joined, record=malformed_record)

    with pytest.raises(audit.EvidenceError, match="start_y"):
        audit.classify_candidate_pair(malformed_joined)


def test_candidate_generation_fallback_joins_with_supersetted_next_nodes(tmp_path: Path):
    record = _task2_record(payload=_outcome_payload("candidate_generation_failed"))
    decisions, _ = _load_task2_decisions(
        tmp_path,
        "fallback-superset.jsonl",
        [_task2_trace_row(advertise_superset=True)],
    )

    joined = audit.join_occurrences([record], decisions, max_join_seconds=0.01)

    assert len(joined) == 1
    assert joined[0].record.occurrences[0].fields["outcome"] == "candidate_generation_failed"


@pytest.mark.parametrize(
    "max_join_seconds", [True, -0.01, float("nan"), float("inf"), 10**400]
)
def test_join_occurrences_rejects_invalid_tolerances(max_join_seconds: float):
    with pytest.raises(audit.EvidenceError, match="join tolerance"):
        audit.join_occurrences([], [], max_join_seconds=max_join_seconds)
