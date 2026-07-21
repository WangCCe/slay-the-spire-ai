"""Measure paired conservative and aggressive map-route generation."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import os
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_PYTHON = Path(r"D:\anaconda\envs\stsai\python.exe")
MIN_WARMUPS = 10
MIN_SAMPLES = 100
FULL_HEIGHT_FIXTURE_SCHEMA = "adaptive-route-map-fixture-v1"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from spirecomm.ai.agent import SimpleAgent
from spirecomm.spire.character import PlayerClass
from spirecomm.spire.map import Map, Node
from spirecomm.spire.potion import Potion


@dataclass(frozen=True)
class FixtureBenchmark:
    fixture_id: str
    fixture_sha256: str
    source: str
    warmup_count: int
    sample_count: int
    durations_ns: tuple[int, ...]
    conservative_path: tuple[int, ...]
    aggressive_path: tuple[int, ...]


@dataclass(frozen=True)
class QualificationCase:
    fixture_id: str
    fixture: dict
    fixture_sha256: str
    source: str


def load_route_fixture(path: Path) -> dict:
    return json.loads(path.read_bytes())


def validate_full_height_fixture(fixture: dict) -> None:
    if fixture.get("schema_version") != FULL_HEIGHT_FIXTURE_SCHEMA:
        raise ValueError(
            f"invalid full-height fixture schema_version: {fixture.get('schema_version')!r}"
        )
    game = fixture.get("game")
    if not isinstance(game, dict) or game.get("act") != 1:
        raise ValueError("full-height fixture game.act must equal 1")
    nodes = fixture.get("nodes")
    if not isinstance(nodes, list):
        raise ValueError("full-height fixture nodes must be a list")

    by_coordinate = {}
    for node in nodes:
        if not isinstance(node, dict):
            raise ValueError("full-height fixture node must be an object")
        x = node.get("x")
        y = node.get("y")
        if type(x) is not int or x not in range(7):
            raise ValueError(f"invalid full-height fixture x coordinate: {x!r}")
        if type(y) is not int or y not in range(15):
            raise ValueError(f"invalid full-height fixture y coordinate: {y!r}")
        coordinate = (x, y)
        if coordinate in by_coordinate:
            raise ValueError(f"duplicate full-height fixture node: {coordinate}")
        by_coordinate[coordinate] = node

    if sorted({y for _, y in by_coordinate}) != list(range(15)):
        raise ValueError("full-height fixture must contain exactly layers y=0..14")

    child_coordinates = {}
    for coordinate, node in by_coordinate.items():
        x, y = coordinate
        children = node.get("children")
        if not isinstance(children, list):
            raise ValueError(f"full-height fixture children must be a list at {coordinate}")
        if y == 14:
            if children:
                raise ValueError(f"terminal full-height fixture node has children at {coordinate}")
            child_coordinates[coordinate] = ()
            continue
        if not 1 <= len(children) <= 2:
            raise ValueError(
                f"full-height fixture node must have one or two children at {coordinate}"
            )
        resolved_children = []
        for child in children:
            if not isinstance(child, dict):
                raise ValueError(f"invalid child at {coordinate}")
            child_coordinate = (child.get("x"), child.get("y"))
            if child_coordinate not in by_coordinate:
                raise ValueError(
                    f"missing child {child_coordinate} referenced from {coordinate}"
                )
            if child_coordinate[1] != y + 1:
                raise ValueError(
                    f"non-forward child edge from {coordinate} to {child_coordinate}"
                )
            resolved_children.append(child_coordinate)
        child_coordinates[coordinate] = tuple(resolved_children)

    starts = [coordinate for coordinate in by_coordinate if coordinate[1] == 0]
    if not starts:
        raise ValueError("full-height fixture has no valid starts")
    reachable = set(starts)
    pending = list(starts)
    while pending:
        coordinate = pending.pop()
        for child_coordinate in child_coordinates[coordinate]:
            if child_coordinate not in reachable:
                reachable.add(child_coordinate)
                pending.append(child_coordinate)
    if len(reachable) < 35:
        raise ValueError("full-height fixture requires at least 35 reachable nodes")


def _fixture_sha256(fixture: dict) -> str:
    fixture_bytes = json.dumps(
        fixture,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(fixture_bytes).hexdigest()


def _legacy_branch_nodes(x: int, symbols: list[str]) -> list[dict]:
    nodes = []
    for y, symbol in enumerate(symbols):
        children = [] if y == 14 else [{"x": x, "y": y + 1}]
        nodes.append({"x": x, "y": y, "symbol": symbol, "children": children})
    return nodes


def _legacy_route_fixture(fixture_id: str, branches: tuple[list[str], ...]) -> dict:
    return {
        "schema_version": "adaptive-route-map-fixture-v1",
        "fixture_id": fixture_id,
        "game": {
            "act": 1,
            "floor": 0,
            "current_hp": 80,
            "max_hp": 80,
            "gold": 99,
            "deck": [
                "Bash+",
                "Pommel Strike",
                "Headbutt",
                "Anger",
                "Shrug It Off",
                "Iron Wave",
            ],
            "potions": ["Fire Potion"],
            "relics": ["Burning Blood"],
        },
        "nodes": [
            node
            for x, symbols in enumerate(branches)
            for node in _legacy_branch_nodes(x, symbols)
        ],
    }


def legacy_route_fixture(case_name: str) -> dict:
    safe = ["M"] * 15
    elite = ["M"] * 15
    elite[7] = "E"
    elite[8] = "T"
    early = list(elite)
    delayed = ["M"] * 15
    delayed[8] = "R"
    delayed[9] = "E"
    cases = {
        "optional_elite": _legacy_route_fixture(
            "legacy-optional-elite-v1",
            (safe, elite),
        ),
        "forced_one_elite": _legacy_route_fixture(
            "legacy-forced-one-elite-v1",
            (early, delayed),
        ),
        "forced_two_elite": _legacy_route_fixture(
            "legacy-forced-two-elite-v1",
            (
                early[:10] + ["E", "T"] + early[12:],
                delayed[:12] + ["E"] + delayed[13:],
            ),
        ),
        "hp_drop_replan": _legacy_route_fixture(
            "legacy-hp-drop-replan-v1",
            (safe,),
        ),
    }
    return cases[case_name]


def _case_from_fixture(fixture: dict, source: str) -> QualificationCase:
    return QualificationCase(
        fixture_id=fixture["fixture_id"],
        fixture=fixture,
        fixture_sha256=_fixture_sha256(fixture),
        source=source,
    )


def _case_from_path(
    path: Path,
    expected_fixture_id: str | None = None,
) -> QualificationCase:
    fixture_bytes = path.read_bytes()
    fixture = json.loads(fixture_bytes)
    validate_full_height_fixture(fixture)
    if expected_fixture_id is not None and fixture.get("fixture_id") != expected_fixture_id:
        raise ValueError(
            f"full-height fixture_id for {path.name} must equal {expected_fixture_id!r}"
        )
    return QualificationCase(
        fixture_id=fixture["fixture_id"],
        fixture=fixture,
        fixture_sha256=hashlib.sha256(fixture_bytes).hexdigest(),
        source="full_height_json",
    )


def qualification_cases(fixture_root: Path) -> tuple[QualificationCase, ...]:
    legacy_cases = tuple(
        _case_from_fixture(legacy_route_fixture(name), "legacy_characterization")
        for name in (
            "optional_elite",
            "forced_one_elite",
            "forced_two_elite",
            "hp_drop_replan",
        )
    )
    full_height_cases = tuple(
        _case_from_path(
            fixture_root / f"full_height_{name}.json",
            expected_fixture_id,
        )
        for name, expected_fixture_id in (
            ("sparse", "full-height-sparse-v1"),
            ("typical", "full-height-typical-v1"),
            ("dense", "full-height-dense-v1"),
        )
    )
    return legacy_cases + full_height_cases


def _fixture_card(card_name: str) -> SimpleNamespace:
    name = str(card_name)
    upgrades = 1 if name.endswith("+") else 0
    canonical_name = name.rstrip("+")
    return SimpleNamespace(
        card_id=canonical_name,
        name=name,
        upgrades=upgrades,
    )


def _fixture_potion(potion_name: str) -> Potion:
    return Potion(
        potion_id=potion_name,
        name=potion_name,
        can_use=True,
        can_discard=True,
        requires_target=False,
    )


def build_fixture_agent(fixture: dict, elite_mode: str) -> SimpleAgent:
    game_data = fixture["game"]
    game_map = Map.from_json(fixture["nodes"])
    agent = SimpleAgent(chosen_class=PlayerClass.IRONCLAD, elite_mode=elite_mode)
    agent.game.map = game_map
    agent.game.act = int(game_data["act"])
    agent.game.floor = int(game_data["floor"])
    agent.game.current_hp = int(game_data["current_hp"])
    agent.game.max_hp = int(game_data["max_hp"])
    agent.game.gold = int(game_data["gold"])
    agent.game.deck = [_fixture_card(card) for card in game_data["deck"]]
    agent.game.hand = []
    agent.game.monsters = []
    agent.game.potions = [_fixture_potion(potion) for potion in game_data["potions"]]
    agent.game.relics = list(game_data["relics"])
    agent.game.screen = SimpleNamespace(
        current_node=Node(-1, -1, "M"),
        next_nodes=list(game_map.nodes[0].values()),
        boss_available=False,
    )
    return agent


def timed_route_pair(fixture: dict) -> tuple[int, tuple[int, ...], tuple[int, ...]]:
    conservative = build_fixture_agent(fixture, "conservative")
    aggressive = build_fixture_agent(fixture, "aggressive")
    started = time.perf_counter_ns()
    conservative.generate_map_route()
    aggressive.generate_map_route()
    elapsed = time.perf_counter_ns() - started
    return elapsed, tuple(conservative.map_route), tuple(aggressive.map_route)


def _validate_route(path: tuple[int, ...], mode: str, game_map: Map) -> None:
    if not path:
        raise ValueError(f"empty {mode} route")
    if len(path) != 15:
        raise ValueError(f"incomplete {mode} route: expected 15 nodes, got {len(path)}")
    for y, x in enumerate(path):
        node = game_map.get_node(x, y)
        if node is None:
            raise ValueError(f"missing {mode} route node at ({x}, {y})")
        if y == len(path) - 1:
            continue
        next_node = game_map.get_node(path[y + 1], y + 1)
        if next_node is None or not any(
            child.x == next_node.x and child.y == next_node.y
            for child in node.children
        ):
            raise ValueError(
                f"illegal {mode} route edge from ({x}, {y}) to ({path[y + 1]}, {y + 1})"
            )


def benchmark_fixture(path: Path, warmups: int, samples: int) -> FixtureBenchmark:
    return benchmark_case(_case_from_path(path), warmups, samples)


def benchmark_case(
    case: QualificationCase,
    warmups: int,
    samples: int,
) -> FixtureBenchmark:
    fixture = case.fixture
    game_map = Map.from_json(fixture["nodes"])
    if warmups < 0 or samples <= 0:
        raise ValueError("warmups must be non-negative and samples must be positive")

    for _ in range(warmups):
        duration, conservative_path, aggressive_path = timed_route_pair(fixture)
        del duration
        _validate_route(conservative_path, "conservative", game_map)
        _validate_route(aggressive_path, "aggressive", game_map)

    durations = []
    expected_conservative_path = None
    expected_aggressive_path = None
    for _ in range(samples):
        duration, conservative_path, aggressive_path = timed_route_pair(fixture)
        _validate_route(conservative_path, "conservative", game_map)
        _validate_route(aggressive_path, "aggressive", game_map)
        if expected_conservative_path is None:
            expected_conservative_path = conservative_path
            expected_aggressive_path = aggressive_path
        elif conservative_path != expected_conservative_path:
            raise ValueError("inconsistent conservative path across measured samples")
        elif aggressive_path != expected_aggressive_path:
            raise ValueError("inconsistent aggressive path across measured samples")
        durations.append(duration)

    return FixtureBenchmark(
        fixture_id=case.fixture_id,
        fixture_sha256=case.fixture_sha256,
        source=case.source,
        warmup_count=warmups,
        sample_count=samples,
        durations_ns=tuple(durations),
        conservative_path=expected_conservative_path,
        aggressive_path=expected_aggressive_path,
    )


def _nearest_rank(values: tuple[int, ...], percentile: float) -> int:
    ordered = sorted(values)
    return ordered[math.ceil(percentile * len(ordered)) - 1]


def _metrics(values: tuple[int, ...]) -> dict[str, float]:
    return {
        "median_ms": statistics.median(values) / 1_000_000,
        "p95_ms": _nearest_rank(values, 0.95) / 1_000_000,
        "max_ms": max(values) / 1_000_000,
    }


def configure_route_logging(log_path: Path) -> logging.Handler:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(handler)
    return handler


def validate_qualification_counts(warmups: int, samples: int) -> None:
    if warmups != MIN_WARMUPS:
        raise ValueError(f"qualification requires exactly {MIN_WARMUPS} warmups")
    if samples != MIN_SAMPLES:
        raise ValueError(f"qualification requires exactly {MIN_SAMPLES} samples")


def ensure_production_interpreter(executable: str | Path | None = None) -> None:
    actual = os.path.normcase(os.path.normpath(str(executable or sys.executable)))
    expected = os.path.normcase(os.path.normpath(str(PRODUCTION_PYTHON)))
    if actual != expected:
        raise RuntimeError(
            f"qualification requires production interpreter {PRODUCTION_PYTHON}; got {actual}"
        )


def benchmark_report(
    results: tuple[FixtureBenchmark, ...],
    provenance: dict | None = None,
) -> dict:
    aggregate_durations = tuple(
        duration
        for result in results
        for duration in result.durations_ns
    )
    aggregate_metrics = _metrics(aggregate_durations)
    passed = (
        aggregate_metrics["median_ms"] <= 25.0
        and aggregate_metrics["max_ms"] <= 100.0
    )
    report = {
        "schema_version": "adaptive-route-candidate-poc-v1",
        "fixtures": [
            {
                "fixture_id": result.fixture_id,
                "fixture_sha256": result.fixture_sha256,
                "source": result.source,
                "warmup_count": result.warmup_count,
                "sample_count": result.sample_count,
                "durations_ns": list(result.durations_ns),
                "metrics": _metrics(result.durations_ns),
                "conservative_path": list(result.conservative_path),
                "aggressive_path": list(result.aggressive_path),
            }
            for result in results
        ],
        "aggregate": {
            "fixture_count": len(results),
            "sample_count": len(aggregate_durations),
            "durations_ns": list(aggregate_durations),
            "metrics": aggregate_metrics,
        },
        "status": "PASS" if passed else "FAIL",
    }
    if provenance is not None:
        report["provenance"] = provenance
    return report


def benchmark_provenance() -> dict:
    try:
        tested_head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            check=True,
            text=True,
        ).stdout.strip()
        task1_status = subprocess.run(
            ["git", "status", "--short", "--", "analysis_scripts", "tests", "reports", "openspec"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            check=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return {"tested_head": "unavailable", "task1_worktree": "unavailable"}
    return {
        "tested_head": tested_head,
        "task1_worktree": "dirty" if task1_status else "clean",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-root", type=Path, required=True)
    parser.add_argument("--warmups", type=int, required=True)
    parser.add_argument("--samples", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        validate_qualification_counts(args.warmups, args.samples)
        ensure_production_interpreter()
        cases = qualification_cases(args.fixture_root)
    except (RuntimeError, ValueError) as error:
        print(f"qualification failed: {error}", file=sys.stderr)
        return 2
    handler = configure_route_logging(args.log)
    try:
        results = tuple(
            benchmark_case(case, args.warmups, args.samples)
            for case in cases
        )
        report = benchmark_report(results, benchmark_provenance())
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    finally:
        logging.getLogger().removeHandler(handler)
        handler.close()
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
