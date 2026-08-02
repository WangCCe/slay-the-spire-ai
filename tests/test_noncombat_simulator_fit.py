from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from analysis_scripts.noncombat_simulator_adapter import (
    ADAPTER_API_VERSION,
    TARGET_CATEGORIES,
    canonical_json_bytes,
    collect_provenance,
    load_native_module,
    sha256_file,
)
from analysis_scripts.noncombat_simulator_fit import (
    INPUT_SCHEMA_VERSION,
    REPORT_SCHEMA_VERSION,
    SimulatorFitError,
    classify_fit_report,
    load_bound_input,
    load_historical_fixture,
    publish_report_pair,
    render_markdown,
    report_json_bytes,
    run_native_audit,
    verify_historical_run_sources,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "noncombat_simulator_adapter"
    / "historical_prefixes_20260802.json"
)


def _provenance():
    return {
        "adapter_commit": "a" * 40,
        "adapter_source_sha256": "b" * 64,
        "build": {
            "adapter_api_version": ADAPTER_API_VERSION,
            "compiler": "test compiler",
            "cpp_standard": 201703,
            "python": "3.10.18",
        },
        "module_sha256": "c" * 64,
        "module_size_bytes": 123,
        "simulator_commit": "d" * 40,
        "simulator_dirty": True,
        "simulator_source_file_count": 79,
        "simulator_source_sha256": "e" * 64,
        "submodules": {"json": "f" * 40, "pybind11": "1" * 40},
    }


def _batch():
    return {
        "all_categories": sorted(TARGET_CATEGORIES),
        "checked_candidates": 46,
        "clone_isolation": True,
        "rows": [
            {
                "categories": sorted(TARGET_CATEGORIES),
                "decisions": 16,
                "floor": 8,
                "outcome": "player_loss",
                "seed": 0,
            },
            {
                "categories": ["card_reward", "event", "route"],
                "decisions": 33,
                "floor": 20,
                "outcome": "player_loss",
                "seed": 1,
            },
        ],
    }


def _native_baseline_batch():
    return {
        "all_categories": sorted(TARGET_CATEGORIES),
        "candidate_legality": True,
        "checked_decisions": 49,
        "non_mutation": True,
        "rows": [
            {
                "categories": sorted(TARGET_CATEGORIES),
                "decisions": 20,
                "floor": 12,
                "outcome": "player_loss",
                "seed": 0,
            },
            {
                "categories": ["card_reward", "event", "route"],
                "decisions": 29,
                "floor": 16,
                "outcome": "player_loss",
                "seed": 1,
            },
        ],
    }


def _historical_sources():
    return [
        {
            "actual_sha256": str(index) * 64,
            "actual_size_bytes": index + 1,
            "expected_sha256": str(index) * 64,
            "expected_size_bytes": index + 1,
            "matched": True,
            "run_file": f"{index}.run",
        }
        for index in range(6)
    ]


def _ready_report():
    first = _batch()
    second = json.loads(json.dumps(first))
    first_native = _native_baseline_batch()
    second_native = json.loads(json.dumps(first_native))
    return classify_fit_report(
        provenance=_provenance(),
        registered_provenance=_provenance(),
        first_batch=first,
        second_batch=second,
        first_native_baseline_batch=first_native,
        second_native_baseline_batch=second_native,
        historical={"expected_decisions": 12, "matched_decisions": 12, "rows": []},
        historical_sources=_historical_sources(),
        throughput_within_budget=True,
        seeds=[0, 1],
    )


def test_ready_report_requires_every_fit_check_and_has_no_authority():
    report = _ready_report()
    assert report["report_schema_version"] == REPORT_SCHEMA_VERSION
    assert report["verdict"] == "adapter_poc_ready"
    assert report["blockers"] == []
    assert set(report["checks"].values()) == {True}
    assert report["checks"]["native_baseline_candidate_mapping"] is True
    assert report["checks"]["native_baseline_non_mutation"] is True
    assert report["checks"]["native_baseline_repeated_seed_determinism"] is True
    assert report["batch"]["native_baseline"]["first"]["checked_decisions"] == 49
    assert set(report["authority"].values()) == {False}
    assert "disabled" in " ".join(report["limitations"]).lower()


def test_provenance_drift_blocks_fit_and_names_exact_field():
    expected = _provenance()
    expected["simulator_commit"] = "9" * 40
    first = _batch()
    report = classify_fit_report(
        provenance=_provenance(),
        registered_provenance=expected,
        first_batch=first,
        second_batch=json.loads(json.dumps(first)),
        first_native_baseline_batch=_native_baseline_batch(),
        second_native_baseline_batch=_native_baseline_batch(),
        historical={"expected_decisions": 12, "matched_decisions": 12, "rows": []},
        historical_sources=_historical_sources(),
        throughput_within_budget=True,
        seeds=[0, 1],
    )
    assert report["verdict"] == "blocked"
    assert report["blockers"] == ["provenance_identity"]
    assert report["provenance_mismatches"] == ["simulator_commit"]


def test_report_rendering_is_deterministic_and_lf_terminated():
    report = _ready_report()
    first_json = report_json_bytes(report)
    second_json = report_json_bytes(json.loads(first_json))
    assert first_json == second_json
    assert first_json.endswith(b"\n")

    first_markdown = render_markdown(report).encode("utf-8")
    second_markdown = render_markdown(json.loads(first_json)).encode("utf-8")
    assert first_markdown == second_markdown
    assert first_markdown.endswith(b"\n")
    assert b"simulator_training_smoke: `false`" in first_markdown


def test_pair_publication_rolls_back_first_output_when_second_replace_fails(tmp_path):
    json_path = tmp_path / "report.json"
    markdown_path = tmp_path / "report.md"
    json_path.write_bytes(b"old json\n")
    markdown_path.write_bytes(b"old markdown\n")
    calls = 0

    def fail_second(source, destination):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected second replace failure")
        os.replace(source, destination)

    with pytest.raises(OSError, match="injected"):
        publish_report_pair(
            _ready_report(),
            json_output=json_path,
            markdown_output=markdown_path,
            replace=fail_second,
        )

    assert json_path.read_bytes() == b"old json\n"
    assert markdown_path.read_bytes() == b"old markdown\n"
    assert not list(tmp_path.glob("*.tmp"))
    assert not list(tmp_path.glob("*.restore"))


def test_bound_input_rejects_fixture_hash_drift(tmp_path):
    fixture = tmp_path / "fixture.json"
    fixture.write_bytes(canonical_json_bytes({"schema_version": "fixture"}))
    manifest = {
        "audit": {"seeds": [0, 1]},
        "fixture": {
            "path": "fixture.json",
            "sha256": sha256_file(fixture),
            "size_bytes": fixture.stat().st_size,
        },
        "registered_provenance": _provenance(),
        "schema_version": INPUT_SCHEMA_VERSION,
    }
    input_path = tmp_path / "input.json"
    input_path.write_bytes(canonical_json_bytes(manifest))
    loaded, loaded_fixture = load_bound_input(input_path, tmp_path)
    assert loaded == manifest
    assert loaded_fixture == fixture

    fixture.write_text("drift\n", encoding="utf-8")
    with pytest.raises(SimulatorFitError, match="fixture size mismatch"):
        load_bound_input(input_path, tmp_path)


def test_historical_fixture_rejects_mutable_or_noncanonical_shape(tmp_path):
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    fixture["runs"][0]["decisions"][0]["candidates"].reverse()
    path = tmp_path / "bad.json"
    path.write_bytes(canonical_json_bytes(fixture))
    with pytest.raises(SimulatorFitError, match="not canonical"):
        load_historical_fixture(path)


def _integration_settings():
    module_path = os.environ.get("STS_LIGHTSPEED_ADAPTER_MODULE")
    simulator_root = os.environ.get("STS_LIGHTSPEED_ROOT")
    mingw_bin = os.environ.get("STS_LIGHTSPEED_MINGW_BIN")
    runs_directory = os.environ.get("STS_RUNS_DIRECTORY")
    if not module_path or not simulator_root or not mingw_bin or not runs_directory:
        pytest.skip("set STS_LIGHTSPEED adapter and run-directory integration variables")
    module = load_native_module(module_path, dll_directories=[mingw_bin])
    provenance = collect_provenance(
        simulator_repo=simulator_root,
        module_path=module_path,
        adapter_repo=REPO_ROOT,
        adapter_source_paths=[
            REPO_ROOT / "analysis_scripts" / "noncombat_simulator_adapter.py",
            REPO_ROOT / "analysis_scripts" / "noncombat_simulator_fit.py",
            REPO_ROOT / "simulator_adapters" / "sts_lightspeed" / "CMakeLists.txt",
            REPO_ROOT / "simulator_adapters" / "sts_lightspeed" / "noncombat_adapter.cpp",
        ],
        native_module=module,
    )
    return module, provenance, runs_directory


def test_native_fit_audit_passes_registered_poc_contract():
    module, provenance, runs_directory = _integration_settings()
    fixture = load_historical_fixture(FIXTURE_PATH)
    historical_sources = verify_historical_run_sources(fixture, runs_directory)
    report = run_native_audit(
        module=module,
        provenance=provenance,
        registered_provenance=provenance,
        fixture=fixture,
        historical_sources=historical_sources,
        seeds=list(range(20)),
        max_decisions=500,
        throughput_budget_seconds=90,
    )

    assert report["verdict"] == "adapter_poc_ready"
    assert report["batch"]["checked_candidates"] == 46
    assert report["batch"]["native_baseline"]["first"]["checked_decisions"] > 0
    assert report["checks"]["native_baseline_candidate_mapping"] is True
    assert report["checks"]["native_baseline_non_mutation"] is True
    assert report["historical_prefix"]["matched_decisions"] == 12
    assert set(report["authority"].values()) == {False}
