import copy
import json
import subprocess
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


@pytest.mark.parametrize(
    ("invalid_path", "error"),
    (
        ((6,) * 15, "missing conservative route node"),
        ((0,) + (1,) * 14, "illegal conservative route edge"),
    ),
)
def test_benchmark_fixture_rejects_invalid_complete_route_topology(
    monkeypatch,
    fixture_path,
    invalid_path,
    error,
):
    monkeypatch.setattr(
        benchmark,
        "timed_route_pair",
        lambda fixture: (1_000, invalid_path, (1,) * 15),
    )

    with pytest.raises(ValueError, match=error):
        benchmark.benchmark_fixture(fixture_path, warmups=0, samples=100)


def test_qualification_cases_include_shared_legacy_characterizations():
    case_ids = [case.fixture_id for case in benchmark.qualification_cases(FIXTURE_ROOT)]

    assert case_ids == [
        "legacy-optional-elite-v1",
        "legacy-forced-one-elite-v1",
        "legacy-forced-two-elite-v1",
        "legacy-hp-drop-replan-v1",
        "full-height-sparse-v1",
        "full-height-typical-v1",
        "full-height-dense-v1",
    ]


@pytest.mark.parametrize(
    ("warmups", "samples", "error"),
    (
        (9, 100, "at least 10"),
        (10, 99, "at least 100"),
    ),
)
def test_qualification_rejects_under_minimum_sampling(warmups, samples, error):
    with pytest.raises(ValueError, match=error):
        benchmark.validate_qualification_counts(warmups, samples)


def test_production_interpreter_guard_rejects_another_python():
    with pytest.raises(RuntimeError, match="production interpreter"):
        benchmark.ensure_production_interpreter(r"C:\\Python311\\python.exe")


def test_production_interpreter_guard_accepts_expected_windows_python():
    benchmark.ensure_production_interpreter(benchmark.PRODUCTION_PYTHON)


def test_benchmark_report_preserves_tested_revision_provenance():
    result = benchmark.FixtureBenchmark(
        fixture_id="fixture-v1",
        fixture_sha256="sha256",
        source="legacy_characterization",
        warmup_count=10,
        sample_count=100,
        durations_ns=(1_000,) * 100,
        conservative_path=(0,) * 15,
        aggressive_path=(0,) * 15,
    )
    provenance = {
        "tested_head": "db0808123",
        "task1_worktree": "dirty",
    }

    report = benchmark.benchmark_report((result,), provenance)

    assert report["provenance"] == provenance


@pytest.mark.parametrize(
    ("mutation", "error"),
    (
        (lambda fixture: fixture.update(schema_version="wrong"), "schema_version"),
        (
            lambda fixture: fixture.update(
                nodes=[node for node in fixture["nodes"] if node["x"] == 0]
            ),
            "at least 35 reachable nodes",
        ),
        (
            lambda fixture: fixture["nodes"][0].update(
                children=[{"x": 6, "y": 1}]
            ),
            "missing child",
        ),
    ),
)
def test_full_height_fixture_validator_rejects_contract_violations(mutation, error):
    fixture = copy.deepcopy(load_route_fixture(FIXTURE_ROOT / "full_height_sparse.json"))
    mutation(fixture)

    with pytest.raises(ValueError, match=error):
        benchmark.validate_full_height_fixture(fixture)


def test_cli_qualification_rejects_malformed_full_height_fixture_before_timing(
    tmp_path,
):
    fixture_root = tmp_path / "fixtures"
    fixture_root.mkdir()
    for name in ("sparse", "typical", "dense"):
        fixture = load_route_fixture(FIXTURE_ROOT / f"full_height_{name}.json")
        if name == "sparse":
            fixture["nodes"] = [node for node in fixture["nodes"] if node["x"] == 0]
        (fixture_root / f"full_height_{name}.json").write_text(
            json.dumps(fixture),
            encoding="utf-8",
        )

    output = tmp_path / "qualification.json"
    result = subprocess.run(
        [
            str(benchmark.PRODUCTION_PYTHON),
            str(benchmark.PROJECT_ROOT / "analysis_scripts/benchmark_adaptive_route_candidates.py"),
            "--fixture-root",
            str(fixture_root),
            "--warmups",
            "10",
            "--samples",
            "100",
            "--output",
            str(output),
            "--log",
            str(tmp_path / "route.log"),
        ],
        cwd=benchmark.PROJECT_ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "at least 35 reachable nodes" in result.stderr
    assert not output.exists()


def test_benchmark_report_preserves_raw_durations_and_matching_metrics():
    durations = (1_000_000, 2_000_000) * 50
    result = benchmark.FixtureBenchmark(
        fixture_id="fixture-v1",
        fixture_sha256="sha256",
        source="full_height_json",
        warmup_count=10,
        sample_count=100,
        durations_ns=durations,
        conservative_path=(0,) * 15,
        aggressive_path=(0,) * 15,
    )

    report = benchmark.benchmark_report((result,))
    fixture_report = report["fixtures"][0]

    assert fixture_report["durations_ns"] == list(durations)
    assert len(fixture_report["durations_ns"]) == fixture_report["sample_count"]
    assert fixture_report["metrics"] == {
        "median_ms": 1.5,
        "p95_ms": 2.0,
        "max_ms": 2.0,
    }
    assert report["aggregate"]["durations_ns"] == list(durations)
    assert len(report["aggregate"]["durations_ns"]) == report["aggregate"]["sample_count"]
