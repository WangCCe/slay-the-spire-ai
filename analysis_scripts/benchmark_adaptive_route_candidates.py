"""Measure paired conservative and aggressive map-route generation."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
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
    warmup_count: int
    sample_count: int
    durations_ns: tuple[int, ...]
    conservative_path: tuple[int, ...]
    aggressive_path: tuple[int, ...]


def load_route_fixture(path: Path) -> dict:
    return json.loads(path.read_bytes())


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


def _validate_route(path: tuple[int, ...], mode: str) -> None:
    if not path:
        raise ValueError(f"empty {mode} route")
    if len(path) != 15:
        raise ValueError(f"incomplete {mode} route: expected 15 nodes, got {len(path)}")


def benchmark_fixture(path: Path, warmups: int, samples: int) -> FixtureBenchmark:
    fixture_bytes = path.read_bytes()
    fixture = json.loads(fixture_bytes)
    fixture_id = fixture["fixture_id"]
    fixture_sha256 = hashlib.sha256(fixture_bytes).hexdigest()
    if warmups < 0 or samples <= 0:
        raise ValueError("warmups must be non-negative and samples must be positive")

    for _ in range(warmups):
        duration, conservative_path, aggressive_path = timed_route_pair(fixture)
        del duration
        _validate_route(conservative_path, "conservative")
        _validate_route(aggressive_path, "aggressive")

    durations = []
    expected_conservative_path = None
    expected_aggressive_path = None
    for _ in range(samples):
        duration, conservative_path, aggressive_path = timed_route_pair(fixture)
        _validate_route(conservative_path, "conservative")
        _validate_route(aggressive_path, "aggressive")
        if expected_conservative_path is None:
            expected_conservative_path = conservative_path
            expected_aggressive_path = aggressive_path
        elif conservative_path != expected_conservative_path:
            raise ValueError("inconsistent conservative path across measured samples")
        elif aggressive_path != expected_aggressive_path:
            raise ValueError("inconsistent aggressive path across measured samples")
        durations.append(duration)

    return FixtureBenchmark(
        fixture_id=fixture_id,
        fixture_sha256=fixture_sha256,
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


def benchmark_report(results: tuple[FixtureBenchmark, ...]) -> dict:
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
    return {
        "schema_version": "adaptive-route-candidate-poc-v1",
        "fixtures": [
            {
                "fixture_id": result.fixture_id,
                "fixture_sha256": result.fixture_sha256,
                "warmup_count": result.warmup_count,
                "sample_count": result.sample_count,
                "metrics": _metrics(result.durations_ns),
                "conservative_path": list(result.conservative_path),
                "aggressive_path": list(result.aggressive_path),
            }
            for result in results
        ],
        "aggregate": {
            "fixture_count": len(results),
            "sample_count": len(aggregate_durations),
            "metrics": aggregate_metrics,
        },
        "status": "PASS" if passed else "FAIL",
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
    handler = configure_route_logging(args.log)
    try:
        fixture_paths = tuple(
            args.fixture_root / f"full_height_{name}.json"
            for name in ("sparse", "typical", "dense")
        )
        results = tuple(
            benchmark_fixture(path, args.warmups, args.samples)
            for path in fixture_paths
        )
        report = benchmark_report(results)
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
