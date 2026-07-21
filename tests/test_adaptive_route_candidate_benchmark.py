from pathlib import Path

import pytest

from analysis_scripts import benchmark_adaptive_route_candidates as benchmark
from analysis_scripts.benchmark_adaptive_route_candidates import load_route_fixture


FIXTURE_ROOT = Path("tests/fixtures/adaptive_route_maps")


def _reachable_nodes(nodes):
    by_coordinate = {(node["x"], node["y"]): node for node in nodes}
    reachable = {(node["x"], node["y"]) for node in nodes if node["y"] == 0}
    pending = list(reachable)
    while pending:
        coordinate = pending.pop()
        for child in by_coordinate[coordinate]["children"]:
            child_coordinate = (child["x"], child["y"])
            if child_coordinate not in reachable:
                reachable.add(child_coordinate)
                pending.append(child_coordinate)
    return reachable


@pytest.mark.parametrize("name", ("sparse", "typical", "dense"))
def test_full_height_fixture_shape(name):
    fixture = load_route_fixture(FIXTURE_ROOT / f"full_height_{name}.json")
    nodes = fixture["nodes"]

    assert fixture["schema_version"] == "adaptive-route-map-fixture-v1"
    assert fixture["fixture_id"] == f"full-height-{name}-v1"
    assert sorted({node["y"] for node in nodes}) == list(range(15))
    assert {node["x"] for node in nodes} <= set(range(7))
    assert len(_reachable_nodes(nodes)) >= 35
    assert all(1 <= len(node["children"]) <= 2 for node in nodes if node["y"] < 14)
    assert all(not node["children"] for node in nodes if node["y"] == 14)


@pytest.fixture(params=("sparse", "typical", "dense"))
def fixture_path(request):
    return FIXTURE_ROOT / f"full_height_{request.param}.json"


def test_benchmark_fixture_uses_excluded_warmups_and_exact_samples(
    monkeypatch,
    fixture_path,
):
    calls = []
    monkeypatch.setattr(
        benchmark,
        "timed_route_pair",
        lambda fixture: (calls.append(fixture) or 1_000, (0,) * 15, (1,) * 15),
    )

    result = benchmark.benchmark_fixture(fixture_path, warmups=10, samples=100)

    assert len(calls) == 110
    assert result.sample_count == 100
    assert result.warmup_count == 10
    assert result.durations_ns == (1_000,) * 100
    assert result.conservative_path == (0,) * 15
    assert result.aggressive_path == (1,) * 15


def test_benchmark_fixture_rejects_inconsistent_measured_paths(
    monkeypatch,
    fixture_path,
):
    paths = iter(((0,) * 15, (1,) * 15, (2,) * 15)
    )
    monkeypatch.setattr(
        benchmark,
        "timed_route_pair",
        lambda fixture: (1_000, next(paths), (1,) * 15),
    )

    with pytest.raises(ValueError, match="inconsistent conservative path"):
        benchmark.benchmark_fixture(fixture_path, warmups=0, samples=3)
