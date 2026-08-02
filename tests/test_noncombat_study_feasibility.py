import hashlib
import json
import os
from decimal import Decimal
from pathlib import Path

import pytest

import analysis_scripts.noncombat_study_feasibility as feasibility


REPO_ROOT = Path(__file__).resolve().parents[1]


def _canonical_bytes(value):
    return (
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _write_canonical(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_bytes(value))


def _binding(root, path):
    payload = path.read_bytes()
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _write_fixture(
    root,
    *,
    trajectory_count=125,
    raw_victory_indexes=(0,),
    supported_indexes=(),
    comparability="historical_reference_only",
):
    reports = root / "reports"
    registration_path = reports / "registration.json"
    readiness_path = reports / "readiness.json"
    manifest_path = reports / "feasibility-input.json"

    registration = {
        "scheduled_attempts": 600,
        "schema_version": "noncombat-outcome-evidence-registration-v2",
        "study_id": "fixture-study",
        "thresholds": {"minimum_supported_victories": 3},
    }
    outcomes = []
    weights = []
    raw_victories = set(raw_victory_indexes)
    supported = set(supported_indexes)
    for index in range(trajectory_count):
        group_id = f"run:{index + 1}"
        outcomes.append(
            {
                "group_id": group_id,
                "outcome": {"victory": index in raw_victories},
            }
        )
        numerator = 1 if index in supported else 0
        weights.append(
            {
                "group_id": group_id,
                "weight": {
                    "denominator": 1,
                    "numerator": numerator,
                    "value": float(numerator),
                },
            }
        )
    readiness = {
        "diagnostics": {
            "trajectory_count": trajectory_count,
            "trajectory_weights": weights,
        },
        "schema_version": "noncombat-ope-readiness-v1",
        "source": {"sample_file": "fixture.jsonl"},
        "target_policy": {
            "construction_mode": "current_deterministic",
            "target_policy_commit": "a" * 40,
            "target_policy_id": "current_deterministic",
        },
        "trajectory_audit": {
            "complete_trajectories": outcomes,
            "complete_trajectory_count": trajectory_count,
        },
    }
    _write_canonical(registration_path, registration)
    _write_canonical(readiness_path, readiness)
    manifest = {
        "minimum_pass_probability": "0.80",
        "minimum_reference_trajectories": 100,
        "readiness": _binding(root, readiness_path),
        "reference_comparability": comparability,
        "registration": _binding(root, registration_path),
        "schema_version": "noncombat-study-feasibility-input-v1",
        "sensitivity_rates": [
            "0",
            "0.001",
            "0.00125",
            "0.0025",
            "0.005",
            "0.005568",
            "0.007",
            "0.008",
            "0.01",
        ],
    }
    _write_canonical(manifest_path, manifest)
    return manifest_path, registration_path, readiness_path


def test_binomial_operating_characteristics_are_deterministic():
    assert feasibility.binomial_tail_probability(600, 3, Decimal("0")) == 0
    assert feasibility.binomial_tail_probability(600, 3, Decimal("1")) == 1

    probability = feasibility.binomial_tail_probability(
        600,
        3,
        Decimal("0.008"),
    )
    assert abs(probability - Decimal("0.8585248984283778")) < Decimal("1e-15")

    required = feasibility.required_success_rate(600, 3, Decimal("0.80"))
    assert abs(required - Decimal("0.007118181088093867")) < Decimal("1e-15")
    assert feasibility.required_success_rate(600, 3, Decimal("0")) == 0
    assert feasibility.required_success_rate(600, 3, Decimal("1")) == 1


def test_zero_weight_raw_victory_does_not_count_as_supported(tmp_path):
    manifest_path, _registration, _readiness = _write_fixture(tmp_path)

    report = feasibility.analyze_manifest(manifest_path, repo_root=tmp_path)

    evidence = report["reference_evidence"]
    assert evidence["complete_trajectories"] == 125
    assert evidence["raw_victories"] == 1
    assert evidence["target_supported_victories"] == 0
    assert evidence["observed_supported_victory_rate"] == {
        "denominator": 125,
        "numerator": 0,
        "value": "0.000000000000",
    }
    assert report["operating_characteristics"]["plug_in_pass_probability"] == (
        "0.000000000000"
    )
    assert report["result"] == {
        "blockers": [
            "reference_not_source_comparable",
            "no_target_supported_victory",
            "plug_in_pass_probability_below_minimum",
        ],
        "separate_amendment_required": True,
        "study_feasibility": "not_demonstrated",
    }


def test_source_comparable_supported_evidence_can_demonstrate_feasibility(tmp_path):
    manifest_path, _registration, _readiness = _write_fixture(
        tmp_path,
        supported_indexes=(0,),
        comparability="source_comparable",
    )

    report = feasibility.analyze_manifest(manifest_path, repo_root=tmp_path)

    assert report["reference_evidence"]["target_supported_victories"] == 1
    assert Decimal(
        report["operating_characteristics"]["plug_in_pass_probability"]
    ) > Decimal("0.85")
    assert report["result"] == {
        "blockers": [],
        "separate_amendment_required": True,
        "study_feasibility": "demonstrated",
    }


def test_historical_reference_cannot_demonstrate_even_when_probability_passes(
    tmp_path,
):
    manifest_path, _registration, _readiness = _write_fixture(
        tmp_path,
        supported_indexes=(0,),
    )

    report = feasibility.analyze_manifest(manifest_path, repo_root=tmp_path)

    assert report["result"]["study_feasibility"] == "not_demonstrated"
    assert report["result"]["blockers"] == [
        "reference_not_source_comparable"
    ]


def test_source_comparable_reference_below_minimum_size_is_blocked(tmp_path):
    manifest_path, _registration, _readiness = _write_fixture(
        tmp_path,
        trajectory_count=99,
        supported_indexes=(0,),
        comparability="source_comparable",
    )

    report = feasibility.analyze_manifest(manifest_path, repo_root=tmp_path)

    assert report["result"]["blockers"] == [
        "insufficient_reference_trajectories"
    ]
    assert report["result"]["study_feasibility"] == "not_demonstrated"


def test_exact_weight_numerator_overrides_diagnostic_float_value(tmp_path):
    manifest_path, _registration, readiness_path = _write_fixture(
        tmp_path,
        supported_indexes=(0,),
        comparability="source_comparable",
    )
    readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
    readiness["diagnostics"]["trajectory_weights"][0]["weight"]["value"] = 0.0
    _write_canonical(readiness_path, readiness)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["readiness"] = _binding(tmp_path, readiness_path)
    _write_canonical(manifest_path, manifest)

    report = feasibility.analyze_manifest(manifest_path, repo_root=tmp_path)

    assert report["reference_evidence"]["target_supported_victories"] == 1
    assert report["result"]["study_feasibility"] == "demonstrated"


@pytest.mark.parametrize("failure", ["hash_mismatch", "missing_weight"])
def test_inconsistent_source_artifacts_fail_before_analysis(tmp_path, failure):
    manifest_path, _registration, readiness_path = _write_fixture(tmp_path)
    if failure == "hash_mismatch":
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["readiness"]["sha256"] = "0" * 64
        _write_canonical(manifest_path, manifest)
        match = "readiness SHA-256 mismatch"
    else:
        readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
        readiness["diagnostics"]["trajectory_weights"].pop()
        _write_canonical(readiness_path, readiness)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["readiness"] = _binding(tmp_path, readiness_path)
        _write_canonical(manifest_path, manifest)
        match = "trajectory outcome/weight keys differ"

    with pytest.raises(feasibility.FeasibilityInputError, match=match):
        feasibility.analyze_manifest(manifest_path, repo_root=tmp_path)


def test_duplicate_json_key_is_rejected(tmp_path):
    manifest_path, _registration, _readiness = _write_fixture(tmp_path)
    original = manifest_path.read_text(encoding="utf-8")
    manifest_path.write_text(
        original.replace(
            '  "schema_version": "noncombat-study-feasibility-input-v1",',
            '  "schema_version": "noncombat-study-feasibility-input-v1",\n'
            '  "schema_version": "noncombat-study-feasibility-input-v1",',
        ),
        encoding="utf-8",
        newline="\n",
    )

    with pytest.raises(feasibility.FeasibilityInputError, match="duplicate JSON key"):
        feasibility.analyze_manifest(manifest_path, repo_root=tmp_path)


def test_artifacts_are_reproducible_and_keep_all_authority_closed(tmp_path):
    manifest_path, _registration, _readiness = _write_fixture(tmp_path)
    json_output = tmp_path / "out" / "feasibility.json"
    markdown_output = tmp_path / "out" / "feasibility.md"

    first = feasibility.run_feasibility_audit(
        manifest_path,
        json_output,
        markdown_output,
        repo_root=tmp_path,
    )
    first_bytes = (json_output.read_bytes(), markdown_output.read_bytes())
    second = feasibility.run_feasibility_audit(
        manifest_path,
        json_output,
        markdown_output,
        repo_root=tmp_path,
    )

    assert first == second
    assert first_bytes == (json_output.read_bytes(), markdown_output.read_bytes())
    assert set(first["authority"].values()) == {False}
    assert b"not_demonstrated" in first_bytes[0]
    assert b"Planning only" in first_bytes[1]


def test_committed_current_audit_replays_byte_for_byte(tmp_path):
    manifest = REPO_ROOT / "reports/noncombat_study_feasibility_20260802_input.json"
    expected_json = REPO_ROOT / "reports/noncombat_study_feasibility_20260802.json"
    expected_markdown = REPO_ROOT / "reports/noncombat_study_feasibility_20260802.md"
    replay_json = tmp_path / "replay.json"
    replay_markdown = tmp_path / "replay.md"

    report = feasibility.run_feasibility_audit(
        manifest,
        replay_json,
        replay_markdown,
        repo_root=REPO_ROOT,
    )

    assert replay_json.read_bytes() == expected_json.read_bytes()
    assert replay_markdown.read_bytes() == expected_markdown.read_bytes()
    assert report["reference_evidence"] == {
        "complete_trajectories": 125,
        "observed_supported_victory_rate": {
            "denominator": 125,
            "numerator": 0,
            "value": "0.000000000000",
        },
        "raw_victories": 1,
        "reference_comparability": "historical_reference_only",
        "target_supported_victories": 0,
    }
    assert report["result"]["study_feasibility"] == "not_demonstrated"


def test_feasibility_sources_are_lf_bound_across_windows_checkouts():
    attributes = (REPO_ROOT / ".gitattributes").read_text(encoding="utf-8")

    assert "analysis_scripts/noncombat_study_feasibility.py text eol=lf\n" in attributes
    assert "reports/noncombat_study_feasibility_* text eol=lf\n" in attributes
    assert "tests/test_noncombat_study_feasibility.py text eol=lf\n" in attributes


def test_output_collision_is_rejected_without_mutating_input(tmp_path):
    manifest_path, registration_path, _readiness = _write_fixture(tmp_path)
    original = registration_path.read_bytes()

    with pytest.raises(feasibility.FeasibilityInputError, match="collides with input"):
        feasibility.run_feasibility_audit(
            manifest_path,
            registration_path,
            tmp_path / "out.md",
            repo_root=tmp_path,
        )

    assert registration_path.read_bytes() == original
    assert not (tmp_path / "out.md").exists()


def test_two_output_transaction_restores_existing_files_on_install_failure(
    tmp_path,
    monkeypatch,
):
    manifest_path, _registration, _readiness = _write_fixture(tmp_path)
    json_output = tmp_path / "out" / "feasibility.json"
    markdown_output = tmp_path / "out" / "feasibility.md"
    json_output.parent.mkdir()
    json_output.write_bytes(b"old-json\n")
    markdown_output.write_bytes(b"old-markdown\n")
    real_replace = os.replace
    failed = False

    def fail_second_install(source, destination):
        nonlocal failed
        if (
            not failed
            and Path(source).suffix == ".tmp"
            and Path(destination) == markdown_output
        ):
            failed = True
            raise OSError("simulated second-install failure")
        return real_replace(source, destination)

    monkeypatch.setattr(feasibility.os, "replace", fail_second_install)

    with pytest.raises(OSError, match="simulated second-install failure"):
        feasibility.run_feasibility_audit(
            manifest_path,
            json_output,
            markdown_output,
            repo_root=tmp_path,
        )

    assert json_output.read_bytes() == b"old-json\n"
    assert markdown_output.read_bytes() == b"old-markdown\n"
