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


def test_load_decision_trace_rejects_overlong_path_y_with_provenance(
    tmp_path: Path,
):
    row = _task2_trace_row()
    row["screen"]["paths"][0]["label"] = row["screen"]["paths"][0][
        "label"
    ].replace("M@2,7", f"M@2,{'9' * 5000}", 1)
    trace = _write_trace(tmp_path, "overlong-path-y.jsonl", [row])

    with pytest.raises(audit.EvidenceError, match="path label") as error:
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


def _task3_candidate(mode: str, start_y: int, symbols: tuple[str, ...]) -> str:
    elite_indexes = [index for index, symbol in enumerate(symbols) if symbol == "E"]
    elite_floors = "|".join(str(start_y + index + 1) for index in elite_indexes) or "none"
    recovery_before = "none"
    recovery_after = "none"
    if elite_indexes:
        first_elite = elite_indexes[0]
        rests_before = [index for index, symbol in enumerate(symbols[:first_elite]) if symbol == "R"]
        rests_after = [
            index
            for index, symbol in enumerate(symbols[first_elite + 1 :], first_elite + 1)
            if symbol == "R"
        ]
        if rests_before:
            recovery_before = str(first_elite - rests_before[-1])
        if rests_after:
            recovery_after = str(rests_after[0] - first_elite)
    return _candidate(
        mode,
        start_y=start_y,
        symbols="/".join(symbols),
        elite_count=len(elite_indexes),
        elite_floors=elite_floors,
        recovery_before=recovery_before,
        recovery_after=recovery_after,
    )


def _task3_payload(
    *,
    floor: int,
    start_y: int,
    conservative_symbols: tuple[str, ...],
    aggressive_symbols: tuple[str, ...],
    selected: str,
) -> str:
    conservative_elites = conservative_symbols.count("E")
    aggressive_elites = aggressive_symbols.count("E")
    return _payload(
        floor=str(floor),
        conservative_candidate=_task3_candidate(
            "conservative", start_y, conservative_symbols
        ),
        aggressive_candidate=_task3_candidate(
            "aggressive", start_y, aggressive_symbols
        ),
        minimum_elites=str(conservative_elites),
        added_elites=str(aggressive_elites - conservative_elites),
        budget=str(int(selected == "aggressive")),
        selected=selected,
        reasons="elite_budget" if selected == "aggressive" else "conservative_baseline",
    )


def _task3_graph(
    *,
    root_symbol: str = "M",
    alternate_aggressive_root: bool = False,
    ambiguous_aggressive_root: bool = False,
) -> list[dict]:
    shared_elite_child = not alternate_aggressive_root
    nodes = [
        _graph_node(0, 0, root_symbol, (0, 1), (2, 1)),
        _graph_node(
            0,
            1,
            "T",
            (0, 2),
            *((1, 2),) if shared_elite_child else (),
        ),
        _graph_node(2, 1, "?", (2, 2), (3, 2)),
        _graph_node(0, 2, "M", (0, 3)),
        _graph_node(1, 2, "E", (0, 3)),
        _graph_node(2, 2, "M", (0, 3)),
        _graph_node(3, 2, "E", (0, 3)),
        _graph_node(0, 3, "R"),
    ]
    if alternate_aggressive_root or ambiguous_aggressive_root:
        nodes.extend(
            [
                _graph_node(4, 0, root_symbol, (4, 1)),
                _graph_node(4, 1, "T", (1, 2)),
            ]
        )
    return nodes


def _task3_trace_row(
    *,
    unix_time: float,
    floor: int,
    current_node: tuple[int, int],
    action_node: tuple[int, int],
    graph: list[dict],
) -> dict:
    by_coordinate = {(node["x"], node["y"]): node for node in graph}
    if current_node[1] == -1:
        next_coordinates = sorted(
            coordinate for coordinate in by_coordinate if coordinate[1] == 0
        )
        current_symbol = "?"
    else:
        next_coordinates = [
            (child["x"], child["y"])
            for child in by_coordinate[current_node]["children"]
        ]
        current_symbol = by_coordinate[current_node]["symbol"]
    action_choice = next_coordinates.index(action_node)
    return {
        "unix_time": unix_time,
        "act": 1,
        "floor": floor,
        "screen_type": "ScreenType.MAP",
        "screen": {
            "type": "ScreenType.MAP",
            "current_node": {
                "x": current_node[0],
                "y": current_node[1],
                "symbol": current_symbol,
            },
            "next_nodes": [
                {"x": x, "y": y, "symbol": by_coordinate[(x, y)]["symbol"]}
                for x, y in next_coordinates
            ],
            "map": {"nodes": graph},
            "paths": [
                _path_summary(choice, [coordinate], graph)
                for choice, coordinate in enumerate(next_coordinates)
            ],
        },
        "action": {
            "type": "ChooseMapNodeAction",
            "choice_index": action_choice,
            "node": {
                "x": action_node[0],
                "y": action_node[1],
                "symbol": by_coordinate[action_node]["symbol"],
            },
        },
    }


def _task3_unix_time(second: int, millisecond: int) -> float:
    value = datetime(
        2026,
        7,
        22,
        12,
        0,
        second,
        millisecond * 1000,
        tzinfo=timezone(timedelta(hours=8)),
    )
    return _epoch_microseconds(value) / 1_000_000


def _write_task3_run(
    tmp_path: Path, name: str, symbols: list[str | None]
) -> Path:
    path = tmp_path / name
    path.write_text(
        json.dumps(
            {
                "path_per_floor": symbols,
                "floor_reached": len(symbols),
                "victory": False,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return path


def _write_task3_evidence(
    tmp_path: Path,
    records: list[dict],
    *,
    run_symbols: list[str],
    graph: list[dict] | None = None,
) -> tuple[list[Path], Path, list[Path]]:
    graph = graph or _task3_graph()
    log_lines = [_line("Starting game #1 as PlayerClass.IRONCLAD")]
    trace_rows = []
    active_game_number = 1
    for index, record in enumerate(records):
        second = index + 1
        game_number = record.get("game_number", 1)
        if game_number != active_game_number:
            log_lines.append(
                _line(
                    f"Starting game #{game_number} as PlayerClass.IRONCLAD",
                    second=second,
                )
            )
            active_game_number = game_number
        payload = _task3_payload(
            floor=record["floor"],
            start_y=record["start_y"],
            conservative_symbols=record["conservative_symbols"],
            aggressive_symbols=record["aggressive_symbols"],
            selected=record["selected"],
        )
        for millisecond in (100, 200):
            log_lines.append(
                _line(
                    f"[ADAPTIVE_ROUTE] {payload}",
                    second=second,
                    millisecond=millisecond,
                )
            )
            trace_rows.append(
                _task3_trace_row(
                    unix_time=_task3_unix_time(second, millisecond),
                    floor=record["floor"],
                    current_node=record["current_node"],
                    action_node=record["action_node"],
                    graph=graph,
                )
            )
    if active_game_number < 2:
        log_lines.append(_line("Starting game #2 as PlayerClass.IRONCLAD", second=20))
    ai_log = _write_log(tmp_path, "task3-ai.log", log_lines)
    trace = _write_trace(tmp_path, "task3-trace.jsonl", trace_rows)
    runs = [
        _write_task3_run(tmp_path, "game-1.run", run_symbols),
        _write_task3_run(tmp_path, "game-2.run", ["M"]),
    ]
    return [ai_log], trace, runs


def _task3_build(
    tmp_path: Path,
    records: list[dict],
    *,
    run_symbols: list[str],
    graph: list[dict] | None = None,
) -> tuple[dict, int, tuple[list[Path], Path, list[Path]]]:
    evidence = _write_task3_evidence(
        tmp_path,
        records,
        run_symbols=run_symbols,
        graph=graph,
    )
    result, exit_code = audit.build_audit(
        evidence[0], evidence[1], evidence[2], 8, 0.001
    )
    return result, exit_code, evidence


def _task3_initial_record(**overrides: object) -> dict:
    record = {
        "floor": 0,
        "start_y": 0,
        "conservative_symbols": ("M", "T", "M", "R"),
        "aggressive_symbols": ("M", "T", "E", "R"),
        "selected": "aggressive",
        "current_node": (-1, -1),
        "action_node": (0, 0),
    }
    record.update(overrides)
    return record


def test_load_runs_preserves_ordered_source_identity_and_path_symbols(tmp_path: Path):
    first = _write_task3_run(tmp_path, "first.run", ["M", "?", "E"])
    second = _write_task3_run(tmp_path, "second.run", ["T", "$", "R"])

    runs, sources = audit.load_runs([first, second])

    assert [run.path_per_floor for run in runs] == [
        ("M", "?", "E"),
        ("T", "$", "R"),
    ]
    assert [source["source_path"] for source in sources] == [str(first), str(second)]
    assert all(source["sha256"] and source["record_count"] == 1 for source in sources)


def test_build_audit_preserves_canonical_post_boss_transition_slot(tmp_path: Path):
    record = _task3_initial_record(floor=2)

    result, exit_code, _ = _task3_build(
        tmp_path, [record], run_symbols=["B", None, "M"]
    )

    assert exit_code == 0
    assert result["runs"][0]["path_per_floor"] == ["B", None, "M"]
    serialized = audit.serialize_audit(result)
    assert json.loads(serialized)["runs"][0]["path_per_floor"] == [
        "B",
        None,
        "M",
    ]


def test_load_runs_rejects_misplaced_transition_slot(tmp_path: Path):
    source = _write_task3_run(tmp_path, "misplaced-null.run", ["M", None, "M"])

    with pytest.raises(
        audit.EvidenceError,
        match=r"path_per_floor\[1\].*null.*immediately follow.*B",
    ):
        audit.load_runs([source])


def test_build_audit_rejects_action_targeted_transition_slot(tmp_path: Path):
    record = _task3_initial_record(floor=1)

    result, exit_code, evidence = _task3_build(
        tmp_path, [record], run_symbols=["B", None, "M"]
    )

    assert exit_code == 2
    assert result["integrity"]["diagnostics"] == [
        {
            "code": "run_transition_slot_targeted",
            "game_number": 1,
            "run_source_path": str(evidence[2][0]),
            "act": 1,
            "floor": 1,
        }
    ]


@pytest.mark.parametrize("alias_kind", ("normalized", "symlink", "hardlink"))
def test_load_runs_rejects_duplicate_physical_source_aliases_before_reading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, alias_kind: str
):
    source = _write_task3_run(tmp_path, "physical.run", ["M"])
    if alias_kind == "normalized":
        alias_parent = tmp_path / "run-alias-parent"
        alias_parent.mkdir()
        alias = alias_parent / ".." / source.name
    elif alias_kind == "symlink":
        alias = tmp_path / "run-symlink.run"
        try:
            alias.symlink_to(source)
        except OSError:
            original_resolve = Path.resolve
            source_target = source.resolve()

            def resolve_simulated_symlink(self: Path, strict: bool = False):
                if self == alias:
                    return source_target
                return original_resolve(self, strict=strict)

            monkeypatch.setattr(Path, "resolve", resolve_simulated_symlink)
    else:
        alias = tmp_path / "run-hardlink.run"
        try:
            alias.hardlink_to(source)
        except OSError as error:
            pytest.skip(f"hard links unavailable: {error}")

    def fail_if_read(_self: Path):
        pytest.fail("duplicate ordered run sources must be rejected before reading")

    monkeypatch.setattr(Path, "read_bytes", fail_if_read)

    with pytest.raises(
        audit.EvidenceError, match="ordered run sources alias one physical file"
    ):
        audit.load_runs([source, alias])


@pytest.mark.parametrize(
    ("failure_kind", "expected_message"),
    (
        ("normalization", "ordered run identity: path normalization failed"),
        ("samefile", "ordered run identity: file identity check failed"),
    ),
)
def test_load_runs_fails_closed_before_read_when_identity_is_uncertain(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_kind: str,
    expected_message: str,
):
    first = _write_task3_run(tmp_path, "identity-first.run", ["M"])
    second = _write_task3_run(tmp_path, "identity-second.run", ["T"])
    if failure_kind == "normalization":
        original_resolve = Path.resolve

        def fail_second_normalization(self: Path, strict: bool = False):
            if self == second:
                raise OSError("forced normalization failure")
            return original_resolve(self, strict=strict)

        monkeypatch.setattr(Path, "resolve", fail_second_normalization)
    else:
        def fail_identity_check(self: Path, other: Path):
            raise OSError("forced identity failure")

        monkeypatch.setattr(Path, "samefile", fail_identity_check)

    def fail_if_read(_self: Path):
        pytest.fail("uncertain ordered run identity must fail before reading")

    monkeypatch.setattr(Path, "read_bytes", fail_if_read)

    with pytest.raises(audit.EvidenceError, match=expected_message):
        audit.load_runs([first, second])


def _task3_two_root_graph() -> list[dict]:
    graph = _task3_graph()
    graph.extend(
        [
            _graph_node(4, 0, "T", (4, 1)),
            _graph_node(4, 1, "T", (0, 2), (1, 2)),
        ]
    )
    return graph


def _task3_two_game_records() -> list[dict]:
    return [
        _task3_initial_record(selected="conservative", game_number=1),
        {
            "game_number": 2,
            "floor": 0,
            "start_y": 0,
            "conservative_symbols": ("T", "T", "M", "R"),
            "aggressive_symbols": ("T", "T", "E", "R"),
            "selected": "conservative",
            "current_node": (-1, -1),
            "action_node": (4, 0),
        },
    ]


def test_build_audit_maps_joined_game_two_to_second_ordered_run(tmp_path: Path):
    evidence = _write_task3_evidence(
        tmp_path,
        _task3_two_game_records(),
        run_symbols=["M"],
        graph=_task3_two_root_graph(),
    )
    _write_task3_run(tmp_path, "game-2.run", ["T"])

    result, exit_code = audit.build_audit(
        evidence[0], evidence[1], evidence[2], 8, 0.001
    )

    assert exit_code == 0
    assert [
        (
            opportunity["game_number"],
            opportunity["decision"]["trace_symbol"],
            opportunity["decision"]["run_symbol"],
        )
        for opportunity in result["opportunities"]
    ] == [(1, "M", "M"), (2, "T", "T")]


def test_build_audit_reports_game_two_mismatch_against_second_ordered_run(
    tmp_path: Path,
):
    evidence = _write_task3_evidence(
        tmp_path,
        _task3_two_game_records(),
        run_symbols=["M"],
        graph=_task3_two_root_graph(),
    )
    _write_task3_run(tmp_path, "game-2.run", ["E"])

    result, exit_code = audit.build_audit(
        evidence[0], evidence[1], evidence[2], 8, 0.001
    )

    assert exit_code == 2
    assert result["integrity"]["diagnostics"] == [
        {
            "code": "run_symbol_mismatch",
            "game_number": 2,
            "act": 1,
            "floor": 0,
            "trace_symbol": "T",
            "run_symbol": "E",
        }
    ]


def test_build_audit_reports_exact_same_immediate_revocation_funnel(tmp_path: Path):
    records = [
        _task3_initial_record(),
        {
            "floor": 1,
            "start_y": 1,
            "conservative_symbols": ("T", "M", "R"),
            "aggressive_symbols": ("T", "E", "R"),
            "selected": "conservative",
            "current_node": (0, 0),
            "action_node": (0, 1),
        },
    ]

    result, exit_code, _ = _task3_build(
        tmp_path, records, run_symbols=["M", "T", "M", "R"]
    )

    assert exit_code == 0
    assert result["integrity"] == {"status": "valid", "diagnostics": []}
    assert result["funnel"] == {
        "adaptive_occurrences": 4,
        "callback_independent_records": 2,
        "candidate_generation_fallbacks": 0,
        "complete_candidate_pairs": 2,
        "zero_vs_one_opportunities": 2,
        "act1_zero_vs_one_opportunities": 2,
        "aggressive_selections": 1,
        "same_immediate_coordinate": 1,
        "different_immediate_coordinate": 0,
        "ambiguous_immediate_coordinate": 0,
        "provable_first_divergences": 1,
        "selection_revoked_before_divergence": 1,
        "route_left_before_divergence": 0,
        "divergences_taken": 0,
        "realized_optional_elites": 0,
    }
    assert result["opportunities"][0]["treatment"]["status"] == "revoked_before_divergence"
    assert result["opportunities"][0]["treatment"]["revocation"]["floor"] == 1


def test_build_audit_reports_route_departure_before_divergence(tmp_path: Path):
    records = [
        _task3_initial_record(),
        {
            "floor": 1,
            "start_y": 1,
            "conservative_symbols": ("?", "E", "R"),
            "aggressive_symbols": ("?", "E", "R"),
            "selected": "aggressive",
            "current_node": (0, 0),
            "action_node": (2, 1),
        },
    ]

    result, exit_code, _ = _task3_build(
        tmp_path, records, run_symbols=["M", "?", "E", "R"]
    )

    assert exit_code == 0
    assert result["funnel"]["route_left_before_divergence"] == 1
    assert result["funnel"]["divergences_taken"] == 0
    treatment = result["opportunities"][0]["treatment"]
    assert treatment["status"] == "route_left_before_divergence"
    assert treatment["route_departure"]["action_coordinate"] == [2, 1]


def test_build_audit_counts_immediate_divergence_when_action_takes_it(tmp_path: Path):
    graph = _task3_graph(alternate_aggressive_root=True)
    record = _task3_initial_record(action_node=(4, 0))

    result, exit_code, _ = _task3_build(
        tmp_path, [record], run_symbols=["M"], graph=graph
    )

    assert exit_code == 0
    assert result["funnel"]["different_immediate_coordinate"] == 1
    assert result["funnel"]["provable_first_divergences"] == 1
    assert result["funnel"]["divergences_taken"] == 1
    assert result["funnel"]["realized_optional_elites"] == 0


def test_build_audit_does_not_call_conservative_divergence_a_prior_departure(
    tmp_path: Path,
):
    records = [
        _task3_initial_record(),
        {
            "floor": 1,
            "start_y": 1,
            "conservative_symbols": ("T", "E", "R"),
            "aggressive_symbols": ("T", "E", "R"),
            "selected": "aggressive",
            "current_node": (0, 0),
            "action_node": (0, 1),
        },
        {
            "floor": 2,
            "start_y": 2,
            "conservative_symbols": ("M", "R"),
            "aggressive_symbols": ("M", "R"),
            "selected": "aggressive",
            "current_node": (0, 1),
            "action_node": (0, 2),
        },
    ]

    result, exit_code, _ = _task3_build(
        tmp_path, records, run_symbols=["M", "T", "M", "R"]
    )

    assert exit_code == 0
    assert result["funnel"]["route_left_before_divergence"] == 0
    assert result["funnel"]["divergences_taken"] == 0
    assert result["opportunities"][0]["treatment"]["status"] == "divergence_not_taken"


def test_treatment_ignores_complete_coordinate_chain_that_predates_opportunity(
    tmp_path: Path,
):
    records = [
        {
            "floor": 0,
            "start_y": 1,
            "conservative_symbols": ("?", "E", "R"),
            "aggressive_symbols": ("?", "E", "R"),
            "selected": "aggressive",
            "current_node": (0, 0),
            "action_node": (2, 1),
        },
        {
            "floor": 1,
            "start_y": 2,
            "conservative_symbols": ("E", "R"),
            "aggressive_symbols": ("E", "R"),
            "selected": "aggressive",
            "current_node": (2, 1),
            "action_node": (3, 2),
        },
        _task3_initial_record(
            conservative_symbols=("M", "?", "M", "R"),
            aggressive_symbols=("M", "?", "E", "R"),
        ),
    ]

    result, exit_code, _ = _task3_build(
        tmp_path, records, run_symbols=["M", "E", "R"]
    )

    assert exit_code == 0
    assert result["funnel"]["divergences_taken"] == 0
    assert result["funnel"]["realized_optional_elites"] == 0
    assert result["opportunities"][0]["treatment"]["status"] == (
        "incomplete_before_divergence"
    )


@pytest.mark.parametrize("broken_chain", ("disconnected", "floor_gap"))
def test_treatment_requires_connected_coordinates_and_consecutive_global_floors(
    tmp_path: Path, broken_chain: str
):
    graph = _task3_graph()
    if broken_chain == "disconnected":
        graph.append(_graph_node(4, 0, "?", (0, 1)))
        step_one_floor = 1
        step_two_floor = 2
        step_one_current = (4, 0)
        run_symbols = ["M", "T", "E"]
    else:
        step_one_floor = 2
        step_two_floor = 3
        step_one_current = (0, 0)
        run_symbols = ["M", "?", "T", "E"]
    records = [
        _task3_initial_record(),
        {
            "floor": step_one_floor,
            "start_y": 1,
            "conservative_symbols": ("T", "E", "R"),
            "aggressive_symbols": ("T", "E", "R"),
            "selected": "aggressive",
            "current_node": step_one_current,
            "action_node": (0, 1),
        },
        {
            "floor": step_two_floor,
            "start_y": 2,
            "conservative_symbols": ("E", "R"),
            "aggressive_symbols": ("E", "R"),
            "selected": "aggressive",
            "current_node": (0, 1),
            "action_node": (1, 2),
        },
    ]

    result, exit_code, _ = _task3_build(
        tmp_path, records, run_symbols=run_symbols, graph=graph
    )

    assert exit_code == 0
    assert result["funnel"]["divergences_taken"] == 0
    assert result["funnel"]["realized_optional_elites"] == 0
    treatment = result["opportunities"][0]["treatment"]
    assert treatment["status"] == "trajectory_unattributable"
    assert treatment["reason"] == broken_chain


def test_build_audit_counts_only_exact_trace_and_run_elite_attribution(tmp_path: Path):
    records = [
        _task3_initial_record(),
        {
            "floor": 1,
            "start_y": 1,
            "conservative_symbols": ("T", "E", "R"),
            "aggressive_symbols": ("T", "E", "R"),
            "selected": "aggressive",
            "current_node": (0, 0),
            "action_node": (0, 1),
        },
        {
            "floor": 2,
            "start_y": 2,
            "conservative_symbols": ("E", "R"),
            "aggressive_symbols": ("E", "R"),
            "selected": "aggressive",
            "current_node": (0, 1),
            "action_node": (1, 2),
        },
    ]

    result, exit_code, _ = _task3_build(
        tmp_path, records, run_symbols=["M", "T", "E", "R"]
    )

    assert exit_code == 0
    assert result["opportunities"][0]["treatment"]["status"] == "realized_optional_elite"
    assert result["opportunities"][0]["treatment"]["elite"] == {
        "act": 1,
        "floor": 2,
        "coordinate": [1, 2],
        "trace_symbol": "E",
        "run_symbol": "E",
    }
    assert result["funnel"]["realized_optional_elites"] == 1


def test_event_trace_resolves_to_nonboss_run_symbol_without_elite_attribution(tmp_path: Path):
    graph = _task3_graph(root_symbol="?")
    record = _task3_initial_record(
        conservative_symbols=("?", "T", "M", "R"),
        aggressive_symbols=("?", "T", "E", "R"),
        selected="conservative",
    )

    result, exit_code, _ = _task3_build(
        tmp_path, [record], run_symbols=["M"], graph=graph
    )

    assert exit_code == 0
    decision = result["opportunities"][0]["decision"]
    assert decision["trace_symbol"] == "?"
    assert decision["run_symbol"] == "M"
    assert decision["run_compatibility"] == "event_resolved"
    assert result["funnel"]["realized_optional_elites"] == 0


def test_exact_event_trace_and_run_symbols_are_classified_as_exact(tmp_path: Path):
    graph = _task3_graph(root_symbol="?")
    record = _task3_initial_record(
        conservative_symbols=("?", "T", "M", "R"),
        aggressive_symbols=("?", "T", "E", "R"),
        selected="conservative",
    )

    result, exit_code, _ = _task3_build(
        tmp_path, [record], run_symbols=["?"], graph=graph
    )

    assert exit_code == 0
    decision = result["opportunities"][0]["decision"]
    assert decision["trace_symbol"] == "?"
    assert decision["run_symbol"] == "?"
    assert decision["run_compatibility"] == "exact"
    assert result["funnel"]["realized_optional_elites"] == 0


def test_non_event_run_symbol_mismatch_marks_integrity_invalid(tmp_path: Path):
    result, exit_code, _ = _task3_build(
        tmp_path, [_task3_initial_record(selected="conservative")], run_symbols=["E"]
    )

    assert exit_code == 2
    assert result["integrity"]["status"] == "invalid"
    assert result["integrity"]["diagnostics"] == [
        {
            "code": "run_symbol_mismatch",
            "game_number": 1,
            "act": 1,
            "floor": 0,
            "trace_symbol": "M",
            "run_symbol": "E",
        }
    ]


def test_ambiguous_candidate_paths_are_excluded_from_divergence_uptake(tmp_path: Path):
    graph = _task3_graph(ambiguous_aggressive_root=True)

    result, exit_code, _ = _task3_build(
        tmp_path, [_task3_initial_record()], run_symbols=["M"], graph=graph
    )

    assert exit_code == 0
    assert result["funnel"]["ambiguous_immediate_coordinate"] == 1
    assert result["funnel"]["provable_first_divergences"] == 0
    assert result["funnel"]["divergences_taken"] == 0
    assert result["opportunities"][0]["treatment"]["status"] == "ambiguous"


def test_serialize_audit_is_stable_sorted_json_with_final_newline(tmp_path: Path):
    result_one, exit_one, evidence = _task3_build(
        tmp_path, [_task3_initial_record(selected="conservative")], run_symbols=["M"]
    )
    result_two, exit_two = audit.build_audit(
        evidence[0], evidence[1], evidence[2], 8, 0.001
    )

    first = audit.serialize_audit(result_one)
    second = audit.serialize_audit(result_two)

    assert (exit_one, exit_two) == (0, 0)
    assert first == second
    assert first.endswith(b"\n")
    assert json.loads(first) == result_one
    assert first == (
        json.dumps(result_one, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    ).encode("ascii")


def test_cli_writes_valid_and_invalid_artifacts_with_distinct_exit_codes(tmp_path: Path):
    _, _, evidence = _task3_build(
        tmp_path, [_task3_initial_record(selected="conservative")], run_symbols=["M"]
    )
    valid_output = tmp_path / "valid.json"
    invalid_run = _write_task3_run(tmp_path, "invalid.run", ["E"])
    invalid_output = tmp_path / "invalid.json"
    common = [
        "--ai-log",
        str(evidence[0][0]),
        "--decision-trace",
        str(evidence[1]),
        "--log-utc-offset-hours",
        "8",
        "--max-join-seconds",
        "0.001",
    ]

    valid_exit = audit.main(
        common
        + [
            "--run",
            str(evidence[2][0]),
            "--run",
            str(evidence[2][1]),
            "--output",
            str(valid_output),
        ]
    )
    invalid_exit = audit.main(
        common
        + [
            "--run",
            str(invalid_run),
            "--run",
            str(evidence[2][1]),
            "--output",
            str(invalid_output),
        ]
    )

    assert valid_exit == 0
    assert json.loads(valid_output.read_bytes())["integrity"]["status"] == "valid"
    assert invalid_exit == 2
    invalid_result = json.loads(invalid_output.read_bytes())
    assert invalid_result["integrity"]["status"] == "invalid"
    assert invalid_result["integrity"]["diagnostics"][0]["code"] == "run_symbol_mismatch"


def _task3_cli_arguments(
    evidence: tuple[list[Path], Path, list[Path]], output: Path
) -> list[str]:
    arguments = [
        "--decision-trace",
        str(evidence[1]),
        "--log-utc-offset-hours",
        "8",
        "--max-join-seconds",
        "0.001",
        "--output",
        str(output),
    ]
    for ai_log in evidence[0]:
        arguments.extend(("--ai-log", str(ai_log)))
    for run in evidence[2]:
        arguments.extend(("--run", str(run)))
    return arguments


@pytest.mark.parametrize("source_kind", ("ai_log", "decision_trace", "run"))
def test_cli_rejects_direct_output_source_collision_without_modifying_any_source(
    tmp_path: Path, source_kind: str
):
    _, _, evidence = _task3_build(
        tmp_path, [_task3_initial_record(selected="conservative")], run_symbols=["M"]
    )
    source = {
        "ai_log": evidence[0][0],
        "decision_trace": evidence[1],
        "run": evidence[2][0],
    }[source_kind]
    all_sources = [*evidence[0], evidence[1], *evidence[2]]
    original_bytes = {path: path.read_bytes() for path in all_sources}

    exit_code = audit.main(_task3_cli_arguments(evidence, source))

    assert exit_code == 2
    assert {path: path.read_bytes() for path in all_sources} == original_bytes


def test_cli_rejects_normalized_output_alias_before_loading_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _, _, evidence = _task3_build(
        tmp_path, [_task3_initial_record(selected="conservative")], run_symbols=["M"]
    )
    alias_parent = tmp_path / "alias-parent"
    alias_parent.mkdir()
    normalized_alias = alias_parent / ".." / evidence[0][0].name
    original = evidence[0][0].read_bytes()

    def fail_if_loaded(*_args, **_kwargs):
        pytest.fail("build_audit must not run for an output/source alias")

    monkeypatch.setattr(audit, "build_audit", fail_if_loaded)

    exit_code = audit.main(_task3_cli_arguments(evidence, normalized_alias))

    assert exit_code == 2
    assert evidence[0][0].read_bytes() == original


def test_cli_rejects_existing_file_identity_alias_without_modifying_source(
    tmp_path: Path,
):
    _, _, evidence = _task3_build(
        tmp_path, [_task3_initial_record(selected="conservative")], run_symbols=["M"]
    )
    source = evidence[2][0]
    identity_alias = tmp_path / "run-hardlink-output.json"
    try:
        identity_alias.hardlink_to(source)
    except OSError as error:
        pytest.skip(f"hard links unavailable: {error}")
    original = source.read_bytes()

    exit_code = audit.main(_task3_cli_arguments(evidence, identity_alias))

    assert exit_code == 2
    assert source.read_bytes() == original
    assert identity_alias.read_bytes() == original


@pytest.mark.parametrize(
    ("failure_kind", "expected_diagnostic"),
    (
        (
            "normalization",
            "adaptive-route audit argument error: output/source identity: "
            "path normalization failed\n",
        ),
        (
            "samefile",
            "adaptive-route audit argument error: output/source identity: "
            "file identity check failed\n",
        ),
    ),
)
def test_cli_identity_uncertainty_stops_before_build_and_output_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    failure_kind: str,
    expected_diagnostic: str,
):
    _, _, evidence = _task3_build(
        tmp_path, [_task3_initial_record(selected="conservative")], run_symbols=["M"]
    )
    output = tmp_path / "existing-output.json"
    output.write_bytes(b"output sentinel\n")
    source = evidence[0][0]
    source_bytes = source.read_bytes()

    def fail_if_built(*_args, **_kwargs):
        pytest.fail("build_audit must not run when source identity is uncertain")

    monkeypatch.setattr(audit, "build_audit", fail_if_built)
    if failure_kind == "normalization":
        original_resolve = Path.resolve

        def fail_output_normalization(self: Path, strict: bool = False):
            if self == output:
                raise OSError("forced normalization failure")
            return original_resolve(self, strict=strict)

        monkeypatch.setattr(Path, "resolve", fail_output_normalization)
    else:
        def fail_identity_check(self: Path, other: Path):
            raise OSError("forced identity failure")

        monkeypatch.setattr(Path, "samefile", fail_identity_check)

    exit_code = audit.main(_task3_cli_arguments(evidence, output))

    assert exit_code == 2
    assert capsys.readouterr().err == expected_diagnostic
    assert output.read_bytes() == b"output sentinel\n"
    assert source.read_bytes() == source_bytes


def test_cli_emits_deterministic_diagnostic_for_output_source_alias(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    _, _, evidence = _task3_build(
        tmp_path, [_task3_initial_record(selected="conservative")], run_symbols=["M"]
    )
    source = evidence[1]
    original = source.read_bytes()

    exit_code = audit.main(_task3_cli_arguments(evidence, source))

    assert exit_code == 2
    assert capsys.readouterr().err == (
        "adaptive-route audit argument error: output/source alias rejected\n"
    )
    assert source.read_bytes() == original
