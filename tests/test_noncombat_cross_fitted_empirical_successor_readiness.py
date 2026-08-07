from __future__ import annotations

import ast
import copy
import ctypes
import hashlib
import io
import json
import os
import subprocess
import sys
import threading
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from analysis_scripts import (
    noncombat_cross_fitted_empirical_successor_readiness as readiness,
)
from analysis_scripts import (
    verify_noncombat_cross_fitted_empirical_successor_readiness as verifier,
)
from analysis_scripts import (
    noncombat_cross_fitted_hierarchical_learning_seed_inventory as seed_inventory,
)


ROOT = Path(__file__).resolve().parents[1]
CONSUMED_CANONICAL_SEARCH_START = 0
CONSUMED_INVENTORY_SHA256 = (
    "435cf41b1cff21178d6de253677544b0e96f8b8ec431c181981aef36591a7174"
)
CONSUMED_SELECTION_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-fresh-schedule-v1"
)


def _binding(path: str, payload: bytes = b"bound\n") -> dict[str, object]:
    return {
        "path": path,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _inventory(commit: str = "a" * 40) -> dict[str, object]:
    excluded = list(range(512, 1024))
    return {
        "canonical_search_start": 0,
        "excluded_seed_count": len(excluded),
        "excluded_seeds": excluded,
        "repository_commit": commit,
        "reserved_seed_ranges": [],
        "row_count": 0,
        "rows": [],
        "schema_version": (
            "noncombat-cross-fitted-hierarchical-learning-seed-inventory-v1"
        ),
        "source_bindings": [],
        "source_count": 0,
    }


def _schedule(inventory: dict[str, object]) -> dict[str, object]:
    seeds = list(range(512))
    return {
        "canonical_search_start": 0,
        "inventory_sha256": readiness.canonical_digest(inventory),
        "schema_version": (
            "noncombat-cross-fitted-hierarchical-learning-fresh-schedule-v1"
        ),
        "seed_count": 512,
        "seeds": seeds,
    }


def _consumed_registration() -> dict[str, object]:
    seeds = list(range(1769, 2281))
    return {
        "registration_id": (
            "noncombat-cross-fitted-hierarchical-learning-successor-20260806-r1"
        ),
        "schedule": {
            "canonical_search_start": CONSUMED_CANONICAL_SEARCH_START,
            "chunk_count": 8,
            "chunks": [seeds[index : index + 64] for index in range(0, 512, 64)],
            "episodes_per_chunk": 64,
            "inventory_sha256": CONSUMED_INVENTORY_SHA256,
            "seeds": seeds,
            "seeds_sha256": readiness.canonical_digest(seeds),
            "selection_schema_version": CONSUMED_SELECTION_SCHEMA_VERSION,
        },
    }


def _source_binding(commit: str = "a" * 40) -> dict[str, object]:
    bindings = [
        {
            **_binding("analysis_scripts/a.py", b"a\n"),
            "role": "auditor_source",
        },
        {
            **_binding("reports/evidence.json", b"{}\n"),
            "role": "immutable_evidence",
        },
    ]
    return {
        "bindings": bindings,
        "bindings_sha256": readiness.canonical_digest(bindings),
        "head_commit": commit,
        "origin_master_commit": commit,
        "source_commit": commit,
        "status": "passed",
        "tracked_clean": True,
    }


def _complete_source_binding(
    module,
    *,
    path_overrides: dict[str, str] | None = None,
    payload_overrides: dict[str, bytes] | None = None,
) -> tuple[dict[str, object], dict[str, bytes]]:
    commit = "a" * 40
    paths = path_overrides or {}
    payloads_by_role = payload_overrides or {}
    payloads: dict[str, bytes] = {}
    rows = []
    for role, canonical_path in module.BOUND_INPUT_PATHS:
        path = paths.get(role, canonical_path)
        payload = payloads_by_role.get(role, f"{role}\n".encode("ascii"))
        payloads[path] = payload
        rows.append({**_binding(path, payload), "role": role})
    return (
        {
            "bindings": rows,
            "bindings_sha256": module.canonical_digest(rows),
            "head_commit": commit,
            "origin_master_commit": commit,
            "source_commit": commit,
            "status": "passed",
            "tracked_clean": True,
        },
        payloads,
    )


def _rehearsal() -> dict[str, object]:
    stages = [
        {
            "ceiling_seconds": "300.000",
            "elapsed_seconds": "1.000",
            "name": name,
            "status": "passed",
        }
        for name in readiness.REHEARSAL_STAGE_ORDER
    ]
    return {
        "blocked_imports": list(readiness.BLOCKED_REHEARSAL_IMPORTS),
        "child_exit_code": 0,
        "context_validation_count": {
            "after_chunk": 1,
            "after_closeout": 1,
            "after_setup": 1,
        },
        "empirical_operations": {
            name: False for name in readiness.EMPIRICAL_OPERATION_NAMES
        },
        "registration_size_bytes": 63_171_200,
        "scratch_artifacts": {
            "file_count": 8,
            "sha256": "b" * 64,
            "size_bytes": 63_200_000,
        },
        "stage_results": stages,
        "status": "passed",
        "synthetic_control_positions": 64,
        "terminal_verdict": "experiment_failed_after_seed_access",
        "verified": True,
    }


def _historical_throughput() -> dict[str, object]:
    return {
        "execution": {
            "charged_seconds": Decimal("2165.4520000000193"),
            "checkpoint_count": 8,
            "completed_training_episodes": 512,
            "optimizer_updates": 8,
            "training_chunk_count": 8,
        },
        "training": {"episodes": 512, "evaluation_episodes": 0},
    }


def _candidate_artifact() -> dict[str, object]:
    inventory = _inventory()
    return readiness.build_candidate_artifact(
        source_commit="a" * 40,
        historical_inventory=inventory,
        candidate_schedule=_schedule(inventory),
        consumed_registration=_consumed_registration(),
        consumed_registration_binding=_binding(
            readiness.CONSUMED_REGISTRATION_PATH, b"consumed\n"
        ),
    )


def _report_and_artifacts() -> tuple[dict[str, object], dict[str, bytes]]:
    candidate = _candidate_artifact()
    report = readiness.build_report(
        audit_id="noncombat-cross-fitted-empirical-successor-readiness-test",
        source_binding=_source_binding(),
        candidate_artifact=candidate,
        candidate_binding=readiness.build_candidate_binding(candidate),
        rehearsal=_rehearsal(),
        budget=readiness.build_budget_evidence(_historical_throughput()),
    )
    return report, readiness.build_publication_artifacts(
        report=report, candidate_artifact=candidate
    )


@pytest.mark.parametrize(
    "relative_path",
    [
        "analysis_scripts/noncombat_cross_fitted_empirical_successor_readiness.py",
        "analysis_scripts/verify_noncombat_cross_fitted_empirical_successor_readiness.py",
    ],
)
def test_readiness_modules_have_stdlib_only_top_level_imports(relative_path):
    tree = ast.parse((ROOT / relative_path).read_text(encoding="utf-8"))
    imported_roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".", 1)[0])
    assert imported_roots <= set(sys.stdlib_module_names) | {"__future__"}
    assert imported_roots.isdisjoint(
        {"analysis_scripts", "numpy", "spirecomm", "sts_lightspeed", "torch"}
    )


def test_authority_and_decision_precedence_are_exact():
    authority = readiness.readiness_authority()
    assert tuple(authority) == readiness.AUTHORITY_NAMES
    assert authority and set(authority.values()) == {False}

    decision = readiness.classify_decision([])
    assert decision == {
        "failed_gates": [],
        "reason": "go",
        "status": "go",
    }
    decision = readiness.classify_decision(
        ["budget_binding", "cohort_not_fresh", "artifact_binding"]
    )
    assert decision == {
        "failed_gates": [
            "cohort_not_fresh",
            "budget_binding",
            "artifact_binding",
        ],
        "reason": "no_go_cohort_not_fresh",
        "status": "no_go",
    }
    with pytest.raises(readiness.ReadinessBlocked, match="failure gate"):
        readiness.classify_decision(["unknown"])


def test_fixed_budget_is_exact_and_not_timing_tuned():
    budget = readiness.build_budget_evidence(_historical_throughput())
    assert budget == {
        "ceiling_seconds": "14400.000",
        "control_reservation_seconds": "3600.000",
        "historical_charged_seconds": "2165.452",
        "historical_counts": {
            "checkpoint_count": 8,
            "evaluation_episodes": 0,
            "optimizer_updates": 8,
            "training_chunk_count": 8,
            "training_episodes": 512,
        },
        "historical_multiplier": "3.000",
        "margin_seconds": "4303.644",
        "projected_total_seconds": "10096.356",
        "status": "passed",
    }

    changed = copy.deepcopy(_historical_throughput())
    changed["execution"]["completed_training_episodes"] = 511
    with pytest.raises(readiness.ReadinessBlocked, match="budget binding"):
        readiness.build_budget_evidence(changed)

    changed_charge = copy.deepcopy(_historical_throughput())
    changed_charge["execution"]["charged_seconds"] = Decimal("2165.4520005")
    with pytest.raises(readiness.ReadinessBlocked, match="historical charge"):
        readiness.build_budget_evidence(changed_charge)


def test_historical_charge_preserves_exact_json_decimal_literal():
    drifted = b'{"execution":{"charged_seconds":2165.4520000000192}}'
    assert float("2165.4520000000192") == float("2165.4520000000193")

    producer_value = readiness._parse_bound_json(
        drifted,
        "historical throughput",
        exact_decimals=True,
    )
    verifier_value = verifier._json_object(
        drifted,
        "historical throughput",
        exact_decimals=True,
    )

    assert producer_value["execution"]["charged_seconds"] == Decimal(
        "2165.4520000000192"
    )
    assert verifier_value["execution"]["charged_seconds"] == Decimal(
        "2165.4520000000192"
    )
    with pytest.raises(readiness.ReadinessBlocked, match="historical charge"):
        readiness.build_budget_evidence(
            {
                "execution": {
                    **_historical_throughput()["execution"],
                    "charged_seconds": producer_value["execution"][
                        "charged_seconds"
                    ],
                },
                "training": _historical_throughput()["training"],
            }
        )

    quoted = b'{"execution":{"charged_seconds":"2165.4520000000193"}}'
    quoted_producer = readiness._parse_bound_json(
        quoted,
        "historical throughput",
        exact_decimals=True,
    )
    quoted_verifier = verifier._json_object(
        quoted,
        "historical throughput",
        exact_decimals=True,
    )
    with pytest.raises(readiness.ReadinessBlocked, match="JSON number"):
        readiness.build_budget_evidence(
            {
                "execution": {
                    **_historical_throughput()["execution"],
                    "charged_seconds": quoted_producer["execution"][
                        "charged_seconds"
                    ],
                },
                "training": _historical_throughput()["training"],
            }
        )
    with pytest.raises(verifier.VerificationError, match="JSON number"):
        verifier._exact_historical_charge(
            quoted_verifier["execution"]["charged_seconds"]
        )


def test_candidate_artifact_proves_full_consumed_cohort_disjointness():
    artifact = _candidate_artifact()
    assert artifact["disjointness"] == {
        "collision_count": 0,
        "collisions": [],
        "status": "passed",
    }
    assert artifact["candidate_schedule"]["seed_count"] == 512
    assert artifact["consumed_cohort"]["seed_count"] == 512
    assert artifact["consumed_cohort"]["seeds"][0] == 1769
    assert artifact["consumed_cohort"]["seeds"][-1] == 2280
    assert artifact["authority"] == readiness.readiness_authority()
    assert readiness.validate_candidate_artifact(artifact) == artifact

    collided_registration = _consumed_registration()
    consumed_seeds = list(collided_registration["schedule"]["seeds"])
    consumed_seeds[0] = 0
    consumed_seeds.sort()
    collided_registration["schedule"]["seeds"] = consumed_seeds
    collided_registration["schedule"]["chunks"] = [
        consumed_seeds[index : index + 64] for index in range(0, 512, 64)
    ]
    collided_registration["schedule"]["seeds_sha256"] = (
        readiness.canonical_digest(consumed_seeds)
    )
    collided = readiness.build_candidate_artifact(
        source_commit="a" * 40,
        historical_inventory=_inventory(),
        candidate_schedule=_schedule(_inventory()),
        consumed_registration=collided_registration,
        consumed_registration_binding=_binding(
            readiness.CONSUMED_REGISTRATION_PATH, b"consumed\n"
        ),
    )
    assert collided["disjointness"]["status"] == "failed"
    assert collided["disjointness"]["collisions"] == [0]


def test_consumed_schedule_accepts_exact_production_identity_in_both_paths():
    registration = _consumed_registration()
    schedule = registration["schedule"]
    binding = _binding(readiness.CONSUMED_REGISTRATION_PATH, b"consumed\n")

    consumed = readiness._consumed_cohort(registration, binding)

    assert consumed["seed_count"] == 512
    assert consumed["seeds_sha256"] == readiness.canonical_digest(
        schedule["seeds"]
    )
    assert verifier._verify_consumed_schedule(schedule) == schedule["seeds"]


def test_auditor_rejects_legacy_five_field_consumed_schedule():
    registration = _consumed_registration()
    for field in (
        "canonical_search_start",
        "inventory_sha256",
        "selection_schema_version",
    ):
        registration["schedule"].pop(field)

    with pytest.raises(readiness.ReadinessBlocked, match="consumed schedule"):
        readiness._consumed_cohort(
            registration,
            _binding(readiness.CONSUMED_REGISTRATION_PATH, b"consumed\n"),
        )


def test_independent_verifier_rejects_legacy_five_field_consumed_schedule():
    schedule = copy.deepcopy(_consumed_registration()["schedule"])
    for field in (
        "canonical_search_start",
        "inventory_sha256",
        "selection_schema_version",
    ):
        schedule.pop(field)

    with pytest.raises(verifier.VerificationError, match="consumed schedule"):
        verifier._verify_consumed_schedule(schedule)


@pytest.mark.parametrize(
    ("mutation", "field", "value"),
    (
        ("missing", "canonical_search_start", None),
        ("missing", "inventory_sha256", None),
        ("missing", "selection_schema_version", None),
        ("drift", "canonical_search_start", 1),
        ("malformed", "canonical_search_start", True),
        ("drift", "inventory_sha256", "0" * 64),
        ("malformed", "inventory_sha256", "not-a-digest"),
        ("drift", "selection_schema_version", "fresh-schedule-v2"),
        ("malformed", "selection_schema_version", 1),
        ("extra", "unexpected_provenance", "forbidden"),
    ),
)
def test_consumed_schedule_provenance_drift_fails_in_both_paths(
    mutation: str, field: str, value: object
):
    registration = _consumed_registration()
    schedule = registration["schedule"]
    if mutation == "missing":
        schedule.pop(field)
    else:
        schedule[field] = value

    with pytest.raises(readiness.ReadinessBlocked, match="consumed"):
        readiness._consumed_cohort(
            registration,
            _binding(readiness.CONSUMED_REGISTRATION_PATH, b"consumed\n"),
        )
    with pytest.raises(verifier.VerificationError, match="consumed"):
        verifier._verify_consumed_schedule(schedule)


def test_bound_inputs_use_existing_canonical_readiness_main_spec():
    expected = (
        "openspec/specs/noncombat-cross-fitted-empirical-successor-readiness/"
        "spec.md"
    )
    assert readiness.READINESS_CHANGE_SPEC_PATH == expected
    assert verifier.READINESS_CHANGE_SPEC_PATH == expected
    for module in (readiness, verifier):
        paths = {role: path for role, path in module.BOUND_INPUT_PATHS}
        assert paths["readiness_change_spec"] == expected
        assert all((ROOT / path).is_file() for path in paths.values())


def test_source_bindings_reject_retired_readiness_change_path(monkeypatch):
    retired = (
        "openspec/changes/assess-cross-fitted-empirical-successor-readiness/"
        "specs/noncombat-cross-fitted-empirical-successor-readiness/spec.md"
    )
    source, _payloads = _complete_source_binding(
        readiness,
        path_overrides={"readiness_change_spec": retired},
    )

    def forbidden(*_args, **_kwargs):
        raise AssertionError("retired source inventory reached Git or worktree I/O")

    with pytest.raises(readiness.ReadinessBlocked, match="input inventory"):
        readiness.load_bound_evidence(
            ROOT,
            source_binding=source,
            blob_reader=forbidden,
        )

    monkeypatch.setattr(verifier, "_git_command", forbidden)
    with pytest.raises(verifier.VerificationError, match="input inventory"):
        verifier._verify_live_source_binding(ROOT, source)


def test_source_binding_requires_exact_pushed_clean_tree_and_blob_hashes(tmp_path):
    commit = "a" * 40
    payloads = {
        "analysis_scripts/a.py": b"print('a')\n",
        "reports/evidence.json": b"{}\n",
    }

    def git_text(_root: Path, *args: str) -> str:
        answers = {
            ("rev-parse", "HEAD"): commit,
            ("rev-parse", "origin/master"): commit,
            ("status", "--porcelain", "--untracked-files=no"): "",
        }
        return answers[args]

    observed = readiness.observe_source_binding(
        tmp_path,
        source_commit=commit,
        required_paths=(
            ("auditor_source", "analysis_scripts/a.py"),
            ("immutable_evidence", "reports/evidence.json"),
        ),
        git_text=git_text,
        blob_reader=lambda _root, _commit, path: payloads[path],
        worktree_reader=lambda _root, path: payloads[path],
    )
    assert observed["status"] == "passed"
    assert observed["tracked_clean"] is True
    assert observed["bindings"][0]["role"] == "auditor_source"

    def drifted_git_text(root: Path, *args: str) -> str:
        if args == ("rev-parse", "origin/master"):
            return "b" * 40
        return git_text(root, *args)

    with pytest.raises(readiness.ReadinessBlocked, match="no_go_source_binding"):
        readiness.observe_source_binding(
            tmp_path,
            source_commit=commit,
            required_paths=(("auditor_source", "analysis_scripts/a.py"),),
            git_text=drifted_git_text,
            blob_reader=lambda _root, _commit, path: payloads[path],
            worktree_reader=lambda _root, path: payloads[path],
        )


def test_report_and_publication_are_exact_and_all_empirical_authority_is_false():
    report, artifacts = _report_and_artifacts()
    assert report["decision"] == {
        "failed_gates": [],
        "reason": "go",
        "status": "go",
    }
    assert report["eligibility"] == {
        "empirical_successor_registration_proposal_eligible": True
    }
    assert set(report["authority"].values()) == {False}
    assert set(report["rehearsal"]["empirical_operations"].values()) == {False}
    assert readiness.validate_report(report) == report
    assert set(artifacts) == set(readiness.PUBLICATION_FILENAMES)
    assert readiness.validate_publication_artifacts(artifacts)["decision"] == report[
        "decision"
    ]

    tampered = dict(artifacts)
    changed_report = json.loads(tampered[readiness.REPORT_FILENAME])
    changed_report["authority"]["training"] = True
    body = {
        key: value
        for key, value in changed_report.items()
        if key != "readiness_identity_sha256"
    }
    changed_report["readiness_identity_sha256"] = readiness.canonical_digest(body)
    tampered[readiness.REPORT_FILENAME] = readiness.canonical_json_bytes(changed_report)
    with pytest.raises(readiness.ReadinessBlocked, match="authority"):
        readiness.validate_publication_artifacts(tampered)


def test_candidate_inventory_uses_deterministic_bounded_gzip():
    candidate = _candidate_artifact()
    canonical = readiness.canonical_json_bytes(candidate)
    first = readiness.deterministic_gzip_bytes(canonical)
    second = readiness.deterministic_gzip_bytes(canonical)
    assert first == second
    assert first[4:8] == b"\x00\x00\x00\x00"
    assert readiness.bounded_gzip_payload(first) == canonical
    assert readiness.decode_candidate_artifact(first) == candidate
    binding = readiness.build_candidate_binding(candidate)
    assert binding["encoding"] == "gzip-mtime-zero-v1"
    assert binding["canonical_size_bytes"] == len(canonical)
    assert binding["size_bytes"] == len(first)

    with pytest.raises(readiness.ReadinessBlocked, match="gzip"):
        readiness.bounded_gzip_payload(first[:-1])


def test_no_alternate_final_publication_api():
    assert not hasattr(readiness, "publish_publication")
    assert not hasattr(readiness, "_publish_prevalidated_publication")


def test_independent_verifier_rejects_markdown_and_cohort_tampering():
    report, artifacts = _report_and_artifacts()
    candidate = readiness.decode_candidate_artifact(
        artifacts[readiness.CANDIDATE_INVENTORY_FILENAME]
    )
    rebuilt = candidate["historical_seed_inventory"]

    verified = verifier.verify_publication_payloads(
        artifacts,
        independently_rebuilt_inventory=rebuilt,
        expected_consumed_cohort=candidate["consumed_cohort"],
    )
    assert verified["decision"] == "go"
    assert verified["proposal_eligible"] is True
    assert verified["source_commit"] == report["source_commit"]

    bad_markdown = dict(artifacts)
    bad_markdown[readiness.REPORT_MARKDOWN_FILENAME] += b"drift\n"
    with pytest.raises(verifier.VerificationError, match="Markdown"):
        verifier.verify_publication_payloads(
            bad_markdown,
            independently_rebuilt_inventory=rebuilt,
        )

    bad_candidate = copy.deepcopy(candidate)
    bad_candidate["consumed_cohort"]["seeds"][0] = 0
    bad_candidate["consumed_cohort"]["seeds_sha256"] = verifier.canonical_digest(
        bad_candidate["consumed_cohort"]["seeds"]
    )
    bad_candidate["disjointness"] = {
        "collision_count": 0,
        "collisions": [],
        "status": "passed",
    }
    bad_artifacts = dict(artifacts)
    bad_artifacts[readiness.CANDIDATE_INVENTORY_FILENAME] = (
        readiness.deterministic_gzip_bytes(
            verifier.canonical_json_bytes(bad_candidate)
        )
    )
    with pytest.raises(verifier.VerificationError, match="cohort|collision"):
        verifier.verify_publication_payloads(
            bad_artifacts,
            independently_rebuilt_inventory=rebuilt,
        )

    mismatched_consumed = copy.deepcopy(candidate["consumed_cohort"])
    mismatched_consumed["registration_id"] += "-drift"
    with pytest.raises(verifier.VerificationError, match="bound registration"):
        verifier.verify_publication_payloads(
            artifacts,
            independently_rebuilt_inventory=rebuilt,
            expected_consumed_cohort=mismatched_consumed,
        )


def test_independent_verifier_rebuilds_seed_inventory_without_producer_imports(
    tmp_path,
):
    repo = tmp_path / "repo"
    report_dir = repo / "reports"
    report_dir.mkdir(parents=True)
    (report_dir / "a.json").write_bytes(
        b'{"cohorts":{"holdout":[4],"train":[3]},"used_seeds":[1,2]}\n'
    )
    (report_dir / "b.jsonl").write_bytes(
        b'{"diagnostic_seed":5}\n{"qualification_seeds":[6]}\n'
    )
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "readiness@example.invalid"],
        cwd=repo,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Readiness Test"],
        cwd=repo,
        check=True,
    )
    subprocess.run(["git", "add", "reports"], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-m", "seed evidence"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()

    expected = seed_inventory.build_seed_inventory(
        repo, repository_commit=commit
    )
    actual = verifier.rebuild_seed_inventory(repo, repository_commit=commit)
    assert actual == expected
    assert actual["excluded_seeds"][:6] == [1, 2, 3, 4, 5, 6]


def test_producer_streams_inventory_without_batch_capture_or_deepcopy(
    tmp_path, monkeypatch
):
    repo = tmp_path / "repo"
    report_dir = repo / "reports"
    report_dir.mkdir(parents=True)
    (report_dir / "a.json").write_bytes(
        b'{"cohorts":{"holdout":[4],"train":[3]},"used_seeds":[1,2]}\n'
    )
    (report_dir / "b.jsonl").write_bytes(
        b'{"diagnostic_seed":5}\n{"qualification_seeds":[6]}\n'
    )
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "readiness@example.invalid"],
        cwd=repo,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Readiness Test"],
        cwd=repo,
        check=True,
    )
    subprocess.run(["git", "add", "reports"], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-m", "seed evidence"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    expected_inventory = seed_inventory.build_seed_inventory(
        repo, repository_commit=commit
    )
    expected_schedule = seed_inventory.materialize_fresh_schedule(
        expected_inventory
    )

    def forbidden(*_args, **_kwargs):
        raise AssertionError("batch capture or deepcopy is forbidden")

    monkeypatch.setattr(seed_inventory, "_git_blob_batch", forbidden)
    monkeypatch.setattr(seed_inventory.copy, "deepcopy", forbidden)
    actual_inventory = readiness._build_streamed_seed_inventory(
        repo,
        repository_commit=commit,
        seed_module=seed_inventory,
    )
    actual_schedule = readiness._materialize_streamed_fresh_schedule(
        actual_inventory
    )

    assert actual_inventory == expected_inventory
    assert actual_schedule == expected_schedule


def test_rehearsal_summary_fails_closed_on_scaling_import_or_watchdog_drift():
    subsecond = _rehearsal()
    subsecond["stage_results"][0]["elapsed_seconds"] = "0.125"
    assert readiness.validate_rehearsal_summary(subsecond)["status"] == "passed"

    scaled = copy.deepcopy(_rehearsal())
    scaled["context_validation_count"]["after_chunk"] = 65
    with pytest.raises(readiness.ReadinessBlocked, match="scaling"):
        readiness.validate_rehearsal_summary(scaled)

    imported = copy.deepcopy(_rehearsal())
    imported["empirical_operations"]["native_loading"] = True
    with pytest.raises(readiness.ReadinessBlocked, match="boundary"):
        readiness.validate_rehearsal_summary(imported)

    timed_out = copy.deepcopy(_rehearsal())
    timed_out["stage_results"][1]["status"] = "timeout"
    with pytest.raises(readiness.ReadinessBlocked, match="boundary"):
        readiness.validate_rehearsal_summary(timed_out)


def test_scratch_verifier_scaling_failure_keeps_typed_gate(tmp_path, monkeypatch):
    root = (tmp_path / "repo").resolve()
    root.mkdir()
    monkeypatch.setattr(
        readiness,
        "_spawn_process_tree",
        lambda *_args, **_kwargs: SimpleNamespace(pid=12345),
    )
    monkeypatch.setattr(
        readiness,
        "_monitor_rehearsal_child",
        lambda _process: {},
    )
    stderr = verifier.canonical_json_bytes(
        {
            "error": (
                "no_go_control_plane_scaling: complete registration "
                "validation count grew"
            ),
            "status": "verification_failed",
            "type": "VerificationError",
        }
    )
    monkeypatch.setattr(
        readiness,
        "_run_supervised_command",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=1,
            stdout=b"",
            stderr=stderr,
        ),
    )

    with pytest.raises(
        readiness.ReadinessBlocked, match="no_go_control_plane_scaling"
    ) as captured:
        readiness.run_actual_scale_rehearsal(
            root,
            source_commit="a" * 40,
            scratch_root=root / "scratch",
        )
    assert (
        readiness._failure_gate(captured.value, "rehearsal_boundary")
        == "control_plane_scaling"
    )


@pytest.mark.parametrize(
    "error",
    [
        "generic verifier failure at C:/no_go_control_plane_scaling/scratch",
        "no_go_source_binding: nested source diagnostic",
        "no_go_budget_binding: nested budget diagnostic",
    ],
)
def test_scratch_verifier_ignores_non_scaling_gate_markers(error):
    stderr = verifier.canonical_json_bytes(
        {
            "error": error,
            "status": "verification_failed",
            "type": "VerificationError",
        }
    )
    assert (
        readiness._scratch_verifier_failure_gate(stderr)
        == "rehearsal_boundary"
    )


def test_independent_scratch_verifier_types_scaling_drift():
    with pytest.raises(
        verifier.VerificationError, match="no_go_control_plane_scaling"
    ):
        verifier._verify_context_validation_count(
            {"after_chunk": 2, "after_closeout": 1, "after_setup": 1}
        )


def test_independent_source_binding_replays_exact_git_and_worktree_bytes(
    tmp_path, monkeypatch
):
    repo = tmp_path / "repo"
    repo.mkdir()
    files = {
        "analysis_scripts/a.py": b"print('bound')\n",
        "reports/evidence.json": b"{}\n",
    }
    for relative, payload in files.items():
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "readiness@example.invalid"],
        cwd=repo,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Readiness Test"],
        cwd=repo,
        check=True,
    )
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-m", "bound source"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    subprocess.run(
        ["git", "update-ref", "refs/remotes/origin/master", commit],
        cwd=repo,
        check=True,
    )
    roles_and_paths = (
        ("auditor_source", "analysis_scripts/a.py"),
        ("immutable_evidence", "reports/evidence.json"),
    )
    monkeypatch.setattr(verifier, "BOUND_INPUT_PATHS", roles_and_paths)
    rows = [
        {**_binding(path, files[path]), "role": role}
        for role, path in roles_and_paths
    ]
    source = {
        "bindings": rows,
        "bindings_sha256": verifier.canonical_digest(rows),
        "head_commit": commit,
        "origin_master_commit": commit,
        "source_commit": commit,
        "status": "passed",
        "tracked_clean": True,
    }
    observed = verifier._verify_live_source_binding(repo, source)
    assert observed["source_commit"] == commit

    (repo / "reports" / "evidence.json").write_bytes(b'{"drift":true}\n')
    with pytest.raises(verifier.VerificationError, match="pushed clean"):
        verifier._verify_live_source_binding(repo, source)


def test_rehearsal_watchdog_kills_child_at_fixed_stage_boundary(monkeypatch):
    released = threading.Event()
    stage_started = readiness.canonical_json_bytes(
        {"kind": "stage_started", "stage": "context_setup"}
    ).decode("utf-8")

    class BlockingOutput:
        def __init__(self):
            self.first = True

        def __iter__(self):
            return self

        def __next__(self):
            if self.first:
                self.first = False
                return stage_started
            released.wait(1)
            raise StopIteration

    class FakeProcess:
        def __init__(self):
            self.stdout = BlockingOutput()
            self.stderr = io.StringIO("")
            self.killed = False
            self._readiness_job = SimpleNamespace(
                terminate_and_wait=lambda _timeout: self.kill(),
                close=lambda: None,
            )

        def poll(self):
            return None if not self.killed else 1

        def kill(self):
            self.killed = True
            released.set()

        def wait(self, timeout=None):
            del timeout
            return 1

    process = FakeProcess()
    monkeypatch.setattr(readiness, "STAGE_CEILING_SECONDS", Decimal("0.010"))
    with pytest.raises(readiness.ReadinessBlocked, match="watchdog expired"):
        readiness._monitor_rehearsal_child(process)
    assert process.killed is True


def test_rehearsal_monitor_kills_child_on_event_parse_failure():
    events = "".join(
        payload.decode("utf-8")
        for payload in (
            readiness.canonical_json_bytes(
                {"kind": "stage_started", "stage": "context_setup"}
            ),
            readiness.canonical_json_bytes(
                {
                    "elapsed_seconds": "not-a-decimal",
                    "kind": "stage_completed",
                    "stage": "context_setup",
                }
            ),
        )
    )

    class FakeProcess:
        def __init__(self):
            self.stdout = io.StringIO(events)
            self.stderr = io.StringIO("")
            self.killed = False
            self._readiness_job = SimpleNamespace(
                terminate_and_wait=lambda _timeout: self.kill(),
                close=lambda: None,
            )

        def poll(self):
            return None if not self.killed else 1

        def kill(self):
            self.killed = True

        def wait(self, timeout=None):
            del timeout
            return 1

    process = FakeProcess()
    with pytest.raises(readiness.ReadinessBlocked, match="canonical"):
        readiness._monitor_rehearsal_child(process)
    assert process.killed is True


def test_readiness_runner_installs_bound_repo_root_for_isolated_imports(
    tmp_path, monkeypatch
):
    root = (tmp_path / "repo").resolve()
    root.mkdir()
    monkeypatch.setattr(
        sys,
        "path",
        [entry for entry in sys.path if Path(entry or ".").resolve() != root],
    )

    class SourceObserved(RuntimeError):
        pass

    def observe(repo_root, *, source_commit):
        assert Path(repo_root).resolve() == root
        assert source_commit == "a" * 40
        assert sys.path[0] == str(root)
        raise SourceObserved

    monkeypatch.setattr(readiness, "observe_source_binding", observe)
    with pytest.raises(readiness.ReadinessAttemptTerminal) as captured:
        readiness.run_readiness_audit(
            repo_root=root,
            source_commit="a" * 40,
            scratch_root=root / "scratch",
            output_dir=root / "publication",
            audit_id="isolated-import-path-test",
        )
    assert isinstance(captured.value.__cause__, SourceObserved)
    assert captured.value.result["decision"] == {
        "failed_gates": ["source_binding"],
        "reason": "no_go_source_binding",
        "status": "no_go",
    }


def test_claimed_attempt_terminalizes_keyboard_interrupt(tmp_path, monkeypatch):
    root = (tmp_path / "repo").resolve()
    root.mkdir()
    commit = "a" * 40

    def interrupt(*_args, **_kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(readiness, "observe_source_binding", interrupt)
    with pytest.raises(KeyboardInterrupt):
        readiness.run_readiness_audit(
            repo_root=root,
            source_commit=commit,
            scratch_root=root / "scratch",
            output_dir=root / "publication",
            audit_id="interrupt-terminal-test",
        )

    attempt_dir = root / readiness.ATTEMPT_ROOT_PATH / commit
    terminal = json.loads(
        (attempt_dir / readiness.ATTEMPT_TERMINAL_FILENAME).read_text()
    )
    assert terminal["decision"] == {
        "failed_gates": ["source_binding"],
        "reason": "no_go_source_binding",
        "status": "no_go",
    }
    assert set(terminal["empirical_operations"].values()) == {False}


def test_source_commit_attempt_claim_is_path_independent_and_one_shot(tmp_path):
    root = (tmp_path / "repo").resolve()
    root.mkdir()
    first = readiness._claim_readiness_attempt(
        root,
        source_commit="a" * 40,
        audit_id="source-attempt-r1",
        scratch_root=root / "scratch-a",
        output_dir=root / "publication-a",
    )
    assert first["attempt_dir"].is_dir()
    assert first["started"]["source_commit"] == "a" * 40
    with pytest.raises(readiness.ReadinessBlocked, match="source identity.*consumed"):
        readiness._claim_readiness_attempt(
            root,
            source_commit="a" * 40,
            audit_id="source-attempt-r2",
            scratch_root=root / "scratch-b",
            output_dir=root / "publication-b",
        )


def test_attempt_claim_never_exposes_directory_without_started_receipt(
    tmp_path, monkeypatch
):
    root = (tmp_path / "repo").resolve()
    root.mkdir()
    commit = "a" * 40

    def fail_write(*_args, **_kwargs):
        raise readiness.ReadinessBlocked("injected started receipt failure")

    monkeypatch.setattr(readiness, "_write_canonical_once", fail_write)
    with pytest.raises(readiness.ReadinessBlocked, match="injected"):
        readiness._claim_readiness_attempt(
            root,
            source_commit=commit,
            audit_id="atomic-source-attempt",
            scratch_root=root / "scratch",
            output_dir=root / "publication",
        )

    attempt_dir = root / readiness.ATTEMPT_ROOT_PATH / commit
    assert not attempt_dir.exists()


def test_attempt_claim_terminalizes_interrupt_after_atomic_rename(
    tmp_path, monkeypatch
):
    root = (tmp_path / "repo").resolve()
    root.mkdir()
    commit = "a" * 40
    real_rename = readiness.os.rename

    def interrupt_after_rename(source, destination):
        real_rename(source, destination)
        raise KeyboardInterrupt

    monkeypatch.setattr(readiness.os, "rename", interrupt_after_rename)
    with pytest.raises(KeyboardInterrupt):
        readiness.run_readiness_audit(
            repo_root=root,
            source_commit=commit,
            scratch_root=root / "scratch",
            output_dir=root / "publication",
            audit_id="post-rename-interrupt-test",
        )

    attempt_dir = root / readiness.ATTEMPT_ROOT_PATH / commit
    assert (attempt_dir / readiness.ATTEMPT_STARTED_FILENAME).is_file()
    terminal = json.loads(
        (attempt_dir / readiness.ATTEMPT_TERMINAL_FILENAME).read_text()
    )
    assert terminal["decision"]["reason"] == "no_go_source_binding"


def test_runner_recovers_claim_when_interrupt_follows_helper_return(
    tmp_path, monkeypatch
):
    root = (tmp_path / "repo").resolve()
    root.mkdir()
    commit = "a" * 40
    real_claim = readiness._claim_readiness_attempt

    def interrupt_after_return(*args, **kwargs):
        real_claim(*args, **kwargs)
        raise KeyboardInterrupt

    monkeypatch.setattr(
        readiness, "_claim_readiness_attempt", interrupt_after_return
    )
    with pytest.raises(KeyboardInterrupt):
        readiness.run_readiness_audit(
            repo_root=root,
            source_commit=commit,
            scratch_root=root / "scratch",
            output_dir=root / "publication",
            audit_id="post-claim-return-interrupt-test",
        )

    attempt_dir = root / readiness.ATTEMPT_ROOT_PATH / commit
    terminal = json.loads(
        (attempt_dir / readiness.ATTEMPT_TERMINAL_FILENAME).read_text()
    )
    assert terminal["decision"]["reason"] == "no_go_source_binding"


@pytest.mark.parametrize(
    ("message", "default_gate", "expected_gate"),
    [
        ("no_go_source_binding: drift", "artifact_binding", "source_binding"),
        (
            "no_go_budget_binding: arithmetic drifted",
            "cohort_not_fresh",
            "budget_binding",
        ),
        (
            "no_go_control_plane_scaling: validation count grew",
            "rehearsal_boundary",
            "control_plane_scaling",
        ),
        (
            "no_go_artifact_binding: independent verifier failed: "
            "no_go_control_plane_scaling: child detail",
            "artifact_binding",
            "artifact_binding",
        ),
        ("independent publication failed", "artifact_binding", "artifact_binding"),
    ],
)
def test_prepublication_failures_have_typed_gate_precedence(
    message, default_gate, expected_gate
):
    error = readiness.ReadinessBlocked(message)
    assert readiness._failure_gate(error, default_gate) == expected_gate


def test_untyped_failure_text_cannot_override_active_gate():
    for message in (
        "access denied: C:/source_binding/no_go_budget_binding/publication",
        "no-go-budget-binding: denied",
        "[wrapped] no_go_budget_binding: denied",
    ):
        assert (
            readiness._failure_gate(PermissionError(message), "artifact_binding")
            == "artifact_binding"
        )


def test_bound_evidence_parse_failure_precedes_and_types_cohort_work(
    tmp_path, monkeypatch
):
    events = []

    def reject_evidence(*_args, **_kwargs):
        events.append("evidence")
        raise readiness.ReadinessBlocked("consumed registration is invalid JSON")

    def build_inventory(*_args, **_kwargs):
        events.append("inventory")
        return _inventory()

    monkeypatch.setattr(readiness, "load_bound_evidence", reject_evidence)
    monkeypatch.setattr(
        readiness, "_build_streamed_seed_inventory", build_inventory
    )
    monkeypatch.setattr(
        readiness,
        "_materialize_streamed_fresh_schedule",
        lambda inventory: _schedule(inventory),
    )

    with pytest.raises(
        readiness.ReadinessBlocked, match="no_go_source_binding"
    ):
        readiness.build_candidate_from_git(
            tmp_path,
            source_binding=_source_binding(),
        )
    assert events == ["evidence"]


@pytest.mark.parametrize(
    "mutation",
    [
        "seed_type",
        "chunk_seed_type",
        "chunks",
        "chunk_count",
        "digest",
        "missing_provenance",
        "extra_provenance",
        "malformed_provenance",
        "drifted_provenance",
    ],
)
def test_complete_consumed_schedule_is_source_bound_before_inventory(
    tmp_path, monkeypatch, mutation
):
    registration = _consumed_registration()
    schedule = registration["schedule"]
    if mutation == "seed_type":
        schedule["seeds"][0] = "1769"
    elif mutation == "chunk_seed_type":
        schedule["chunks"][0][0] = 1769.0
    elif mutation == "chunks":
        schedule["chunks"][0] = schedule["chunks"][0][:-1]
    elif mutation == "chunk_count":
        schedule["chunk_count"] = 7
    elif mutation == "digest":
        schedule.pop("seeds_sha256")
    elif mutation == "missing_provenance":
        schedule.pop("inventory_sha256")
    elif mutation == "extra_provenance":
        schedule["unexpected_provenance"] = "forbidden"
    elif mutation == "malformed_provenance":
        schedule["canonical_search_start"] = True
    else:
        schedule["selection_schema_version"] = "fresh-schedule-v2"

    monkeypatch.setattr(
        readiness,
        "load_bound_evidence",
        lambda *_args, **_kwargs: {
            "consumed_registration": registration,
            "consumed_registration_binding": _binding(
                readiness.CONSUMED_REGISTRATION_PATH,
                b"consumed\n",
            ),
            "historical_throughput": _historical_throughput(),
        },
    )

    def forbidden_inventory(*_args, **_kwargs):
        raise AssertionError("malformed source evidence reached inventory work")

    monkeypatch.setattr(
        readiness, "_build_streamed_seed_inventory", forbidden_inventory
    )
    with pytest.raises(
        readiness.ReadinessBlocked, match="no_go_source_binding"
    ):
        readiness.build_candidate_from_git(
            tmp_path,
            source_binding=_source_binding(),
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_provenance",
        "extra_provenance",
        "malformed_provenance",
        "drifted_provenance",
    ],
)
def test_independent_verifier_rejects_provenance_before_inventory_rebuild(
    tmp_path, monkeypatch, mutation
):
    schedule = copy.deepcopy(_consumed_registration()["schedule"])
    if mutation == "missing_provenance":
        schedule.pop("inventory_sha256")
    elif mutation == "extra_provenance":
        schedule["unexpected_provenance"] = "forbidden"
    elif mutation == "malformed_provenance":
        schedule["canonical_search_start"] = True
    else:
        schedule["selection_schema_version"] = "fresh-schedule-v2"
    registration_payload = verifier.canonical_json_bytes(
        {
            "registration_id": (
                "noncombat-cross-fitted-hierarchical-learning-successor-"
                "20260806-r1"
            ),
            "schedule": schedule,
        }
    )
    source, payloads = _complete_source_binding(
        verifier,
        payload_overrides={"consumed_registration": registration_payload},
    )
    output = tmp_path / "publication"
    output.mkdir()
    _report, artifacts = _report_and_artifacts()
    for name, payload in artifacts.items():
        (output / name).write_bytes(payload)

    monkeypatch.setattr(
        verifier,
        "_verify_live_source_binding",
        lambda *_args, **_kwargs: source,
    )
    monkeypatch.setattr(
        verifier,
        "_git_blob",
        lambda _root, _commit, path: payloads[path],
    )

    def forbidden_inventory(*_args, **_kwargs):
        raise AssertionError("malformed provenance reached inventory rebuild")

    monkeypatch.setattr(verifier, "rebuild_seed_inventory", forbidden_inventory)
    with pytest.raises(verifier.VerificationError, match="consumed schedule"):
        verifier.verify_publication(output, repo_root=tmp_path)


def test_independent_consumed_schedule_rejects_float_chunk_seed():
    schedule = copy.deepcopy(_consumed_registration()["schedule"])
    schedule["chunks"][0][0] = 1769.0
    with pytest.raises(verifier.VerificationError, match="consumed"):
        verifier._verify_consumed_schedule(schedule)


def test_runner_does_not_install_final_publication_before_independent_verification(
    tmp_path, monkeypatch
):
    root = (tmp_path / "repo").resolve()
    root.mkdir()
    output = root / "publication"
    candidate = _candidate_artifact()
    monkeypatch.setattr(
        readiness,
        "observe_source_binding",
        lambda *_args, **_kwargs: _source_binding(),
    )
    monkeypatch.setattr(
        readiness,
        "build_candidate_from_git",
        lambda *_args, **_kwargs: (
            candidate,
            {"historical_throughput": _historical_throughput()},
        ),
    )
    monkeypatch.setattr(
        readiness,
        "run_actual_scale_rehearsal",
        lambda *_args, **_kwargs: _rehearsal(),
    )
    monkeypatch.setattr(
        readiness,
        "_run_independent_verifier",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=1,
            stdout=b"",
            stderr=b"independent drift",
        ),
    )
    with pytest.raises(readiness.ReadinessAttemptTerminal) as captured:
        readiness.run_readiness_audit(
            repo_root=root,
            source_commit="a" * 40,
            scratch_root=root / "scratch",
            output_dir=output,
            audit_id="verify-before-install-test",
        )
    assert captured.value.result["decision"] == {
        "failed_gates": ["artifact_binding"],
        "reason": "no_go_artifact_binding",
        "status": "no_go",
    }
    assert not output.exists()


def test_runner_rebinds_verified_staging_before_atomic_install(
    tmp_path, monkeypatch
):
    root = (tmp_path / "repo").resolve()
    root.mkdir()
    output = root / "publication"
    commit = "a" * 40
    candidate = _candidate_artifact()
    monkeypatch.setattr(
        readiness,
        "observe_source_binding",
        lambda *_args, **_kwargs: _source_binding(),
    )
    monkeypatch.setattr(
        readiness,
        "build_candidate_from_git",
        lambda *_args, **_kwargs: (
            candidate,
            {"historical_throughput": _historical_throughput()},
        ),
    )
    monkeypatch.setattr(
        readiness,
        "run_actual_scale_rehearsal",
        lambda *_args, **_kwargs: _rehearsal(),
    )

    def verify_then_tamper(command, **_kwargs):
        staging = Path(command[command.index("--output-dir") + 1])
        report = json.loads((staging / readiness.REPORT_FILENAME).read_text())
        candidate_payload = (
            staging / readiness.CANDIDATE_INVENTORY_FILENAME
        ).read_bytes()
        summary = {
            "candidate_inventory_sha256": hashlib.sha256(
                candidate_payload
            ).hexdigest(),
            "decision": report["decision"]["status"],
            "independent_inventory_sha256": candidate["candidate_schedule"][
                "inventory_sha256"
            ],
            "proposal_eligible": report["eligibility"][
                "empirical_successor_registration_proposal_eligible"
            ],
            "readiness_identity_sha256": report["readiness_identity_sha256"],
            "source_commit": commit,
            "status": "verified",
        }
        markdown = staging / readiness.REPORT_MARKDOWN_FILENAME
        markdown.write_bytes(markdown.read_bytes() + b"tampered after verify\n")
        return SimpleNamespace(
            returncode=0,
            stdout=readiness.canonical_json_bytes(summary),
            stderr=b"",
        )

    monkeypatch.setattr(
        readiness, "_run_independent_verifier", verify_then_tamper
    )
    with pytest.raises(readiness.ReadinessAttemptTerminal) as captured:
        readiness.run_readiness_audit(
            repo_root=root,
            source_commit=commit,
            scratch_root=root / "scratch",
            output_dir=output,
            audit_id="sealed-staging-rebind-test",
        )

    assert captured.value.result["decision"]["reason"] == "no_go_artifact_binding"
    assert not output.exists()


def test_sealed_copy_failure_removes_only_its_random_snapshot(
    tmp_path, monkeypatch
):
    staging = tmp_path / f".publication.{'a' * 40}.staging"
    staging.mkdir()
    _report, artifacts = _report_and_artifacts()
    for name, payload in artifacts.items():
        (staging / name).write_bytes(payload)
    bindings = readiness._observe_publication_bindings(staging, "test staging")

    def fail_fsync(_descriptor):
        raise OSError("injected sealed fsync failure")

    monkeypatch.setattr(readiness.os, "fsync", fail_fsync)
    with pytest.raises(readiness.ReadinessBlocked, match="seal"):
        readiness._seal_verified_staging(
            staging,
            tmp_path / "publication",
            publication_bindings=bindings,
            sealed_path=tmp_path / f".publication.{'b' * 64}.sealed",
        )

    assert staging.is_dir()
    assert not list(tmp_path.glob("*.sealed"))


def test_runner_terminalizes_independently_verified_no_go(tmp_path, monkeypatch):
    root = (tmp_path / "repo").resolve()
    root.mkdir()
    output = root / "publication"
    commit = "a" * 40
    inventory = _inventory()
    consumed = _consumed_registration()
    consumed_seeds = list(range(512))
    consumed["schedule"] = {
        "canonical_search_start": CONSUMED_CANONICAL_SEARCH_START,
        "chunk_count": 8,
        "chunks": [
            consumed_seeds[index : index + 64]
            for index in range(0, 512, 64)
        ],
        "episodes_per_chunk": 64,
        "inventory_sha256": CONSUMED_INVENTORY_SHA256,
        "seeds": consumed_seeds,
        "seeds_sha256": readiness.canonical_digest(consumed_seeds),
        "selection_schema_version": CONSUMED_SELECTION_SCHEMA_VERSION,
    }
    candidate = readiness.build_candidate_artifact(
        source_commit=commit,
        historical_inventory=inventory,
        candidate_schedule=_schedule(inventory),
        consumed_registration=consumed,
        consumed_registration_binding=_binding(
            readiness.CONSUMED_REGISTRATION_PATH, b"consumed\n"
        ),
    )
    assert candidate["disjointness"]["status"] == "failed"
    monkeypatch.setattr(
        readiness,
        "observe_source_binding",
        lambda *_args, **_kwargs: _source_binding(),
    )
    monkeypatch.setattr(
        readiness,
        "build_candidate_from_git",
        lambda *_args, **_kwargs: (
            candidate,
            {"historical_throughput": _historical_throughput()},
        ),
    )

    def forbidden_downstream(*_args, **_kwargs):
        raise AssertionError("cohort failure reached a downstream gate")

    monkeypatch.setattr(
        readiness,
        "run_actual_scale_rehearsal",
        forbidden_downstream,
    )
    monkeypatch.setattr(
        readiness, "_run_independent_verifier", forbidden_downstream
    )
    with pytest.raises(readiness.ReadinessAttemptTerminal) as captured:
        readiness.run_readiness_audit(
            repo_root=root,
            source_commit=commit,
            scratch_root=root / "scratch",
            output_dir=output,
            audit_id="verified-no-go-terminal-test",
        )

    assert captured.value.result["decision"] == {
        "failed_gates": ["cohort_not_fresh"],
        "reason": "no_go_cohort_not_fresh",
        "status": "no_go",
    }
    assert not output.exists()
    attempt_dir = root / readiness.ATTEMPT_ROOT_PATH / commit
    assert not (attempt_dir / readiness.ATTEMPT_VERIFIED_FILENAME).exists()
    assert (attempt_dir / readiness.ATTEMPT_TERMINAL_FILENAME).is_file()


def test_runner_reaches_budget_only_after_rehearsal(tmp_path, monkeypatch):
    root = (tmp_path / "repo").resolve()
    root.mkdir()
    candidate = _candidate_artifact()
    events = []
    monkeypatch.setattr(
        readiness,
        "observe_source_binding",
        lambda *_args, **_kwargs: _source_binding(),
    )
    monkeypatch.setattr(
        readiness,
        "build_candidate_from_git",
        lambda *_args, **_kwargs: (
            candidate,
            {"historical_throughput": _historical_throughput()},
        ),
    )

    def rehearse(*_args, **_kwargs):
        events.append("rehearsal")
        return _rehearsal()

    def reject_budget(_historical):
        events.append("budget")
        raise readiness.ReadinessBlocked(
            "no_go_budget_binding: injected exact budget drift"
        )

    monkeypatch.setattr(readiness, "run_actual_scale_rehearsal", rehearse)
    monkeypatch.setattr(readiness, "build_budget_evidence", reject_budget)

    with pytest.raises(readiness.ReadinessAttemptTerminal) as captured:
        readiness.run_readiness_audit(
            repo_root=root,
            source_commit="a" * 40,
            scratch_root=root / "scratch",
            output_dir=root / "publication",
            audit_id="rehearsal-before-budget-test",
        )

    assert events == ["rehearsal", "budget"]
    assert captured.value.result["decision"]["reason"] == "no_go_budget_binding"


def test_runner_installs_only_independently_verified_staging(tmp_path, monkeypatch):
    root = (tmp_path / "repo").resolve()
    root.mkdir()
    output = root / "publication"
    commit = "a" * 40
    candidate = _candidate_artifact()
    monkeypatch.setattr(
        readiness,
        "observe_source_binding",
        lambda *_args, **_kwargs: _source_binding(),
    )
    monkeypatch.setattr(
        readiness,
        "build_candidate_from_git",
        lambda *_args, **_kwargs: (
            candidate,
            {"historical_throughput": _historical_throughput()},
        ),
    )
    monkeypatch.setattr(
        readiness,
        "run_actual_scale_rehearsal",
        lambda *_args, **_kwargs: _rehearsal(),
    )

    observed_staging = []

    def verify(command, **_kwargs):
        staging = Path(command[command.index("--output-dir") + 1])
        assert not output.exists()
        observed_staging.append(staging)
        report = json.loads((staging / readiness.REPORT_FILENAME).read_text())
        candidate_payload = (
            staging / readiness.CANDIDATE_INVENTORY_FILENAME
        ).read_bytes()
        summary = {
            "candidate_inventory_sha256": hashlib.sha256(
                candidate_payload
            ).hexdigest(),
            "decision": report["decision"]["status"],
            "independent_inventory_sha256": candidate["candidate_schedule"][
                "inventory_sha256"
            ],
            "proposal_eligible": report["eligibility"][
                "empirical_successor_registration_proposal_eligible"
            ],
            "readiness_identity_sha256": report["readiness_identity_sha256"],
            "source_commit": commit,
            "status": "verified",
        }
        return SimpleNamespace(
            returncode=0,
            stdout=readiness.canonical_json_bytes(summary),
            stderr=b"",
        )

    monkeypatch.setattr(readiness, "_run_independent_verifier", verify)
    result = readiness.run_readiness_audit(
        repo_root=root,
        source_commit=commit,
        scratch_root=root / "scratch",
        output_dir=output,
        audit_id="verified-staging-install-test",
    )

    assert result["decision"]["status"] == "go"
    assert {path.name for path in output.iterdir()} == set(
        readiness.PUBLICATION_FILENAMES
    )
    assert len(observed_staging) == 1
    assert not observed_staging[0].exists()
    attempt_dir = root / readiness.ATTEMPT_ROOT_PATH / commit
    assert {
        path.name for path in attempt_dir.iterdir()
    } == {
        readiness.ATTEMPT_STARTED_FILENAME,
        readiness.ATTEMPT_VERIFIED_FILENAME,
    }
    receipt = json.loads(
        (attempt_dir / readiness.ATTEMPT_VERIFIED_FILENAME).read_text()
    )
    assert receipt["status"] == "staging_independently_verified"


def test_runner_does_not_terminalize_interrupt_after_atomic_install(
    tmp_path, monkeypatch
):
    root = (tmp_path / "repo").resolve()
    root.mkdir()
    output = root / "publication"
    commit = "a" * 40
    candidate = _candidate_artifact()
    monkeypatch.setattr(
        readiness,
        "observe_source_binding",
        lambda *_args, **_kwargs: _source_binding(),
    )
    monkeypatch.setattr(
        readiness,
        "build_candidate_from_git",
        lambda *_args, **_kwargs: (
            candidate,
            {"historical_throughput": _historical_throughput()},
        ),
    )
    monkeypatch.setattr(
        readiness,
        "run_actual_scale_rehearsal",
        lambda *_args, **_kwargs: _rehearsal(),
    )

    def verify(command, **_kwargs):
        staging = Path(command[command.index("--output-dir") + 1])
        report = json.loads((staging / readiness.REPORT_FILENAME).read_text())
        candidate_payload = (
            staging / readiness.CANDIDATE_INVENTORY_FILENAME
        ).read_bytes()
        summary = {
            "candidate_inventory_sha256": hashlib.sha256(
                candidate_payload
            ).hexdigest(),
            "decision": report["decision"]["status"],
            "independent_inventory_sha256": candidate["candidate_schedule"][
                "inventory_sha256"
            ],
            "proposal_eligible": report["eligibility"][
                "empirical_successor_registration_proposal_eligible"
            ],
            "readiness_identity_sha256": report["readiness_identity_sha256"],
            "source_commit": commit,
            "status": "verified",
        }
        return SimpleNamespace(
            returncode=0,
            stdout=readiness.canonical_json_bytes(summary),
            stderr=b"",
        )

    monkeypatch.setattr(readiness, "_run_independent_verifier", verify)
    real_replace = readiness.os.replace
    expected_staging = output.parent / f".{output.name}.{commit}.staging"

    def interrupt_after_install(source, destination):
        real_replace(source, destination)
        if (
            Path(source).parent == output.parent
            and Path(source).name.endswith(".sealed")
            and Path(destination) == output
        ):
            raise KeyboardInterrupt

    monkeypatch.setattr(readiness.os, "replace", interrupt_after_install)
    with pytest.raises(KeyboardInterrupt):
        readiness.run_readiness_audit(
            repo_root=root,
            source_commit=commit,
            scratch_root=root / "scratch",
            output_dir=output,
            audit_id="post-install-interrupt-test",
        )

    attempt_dir = root / readiness.ATTEMPT_ROOT_PATH / commit
    assert output.is_dir()
    assert not expected_staging.exists()
    assert (attempt_dir / readiness.ATTEMPT_VERIFIED_FILENAME).is_file()
    assert not (attempt_dir / readiness.ATTEMPT_TERMINAL_FILENAME).exists()


def test_failed_install_recovery_terminalizes_and_removes_sealed_snapshot(
    tmp_path, monkeypatch
):
    root = (tmp_path / "repo").resolve()
    root.mkdir()
    output = root / "publication"
    commit = "a" * 40
    candidate = _candidate_artifact()
    monkeypatch.setattr(
        readiness,
        "observe_source_binding",
        lambda *_args, **_kwargs: _source_binding(),
    )
    monkeypatch.setattr(
        readiness,
        "build_candidate_from_git",
        lambda *_args, **_kwargs: (
            candidate,
            {"historical_throughput": _historical_throughput()},
        ),
    )
    monkeypatch.setattr(
        readiness,
        "run_actual_scale_rehearsal",
        lambda *_args, **_kwargs: _rehearsal(),
    )

    def verify(command, **_kwargs):
        staging = Path(command[command.index("--output-dir") + 1])
        report = json.loads((staging / readiness.REPORT_FILENAME).read_text())
        candidate_payload = (
            staging / readiness.CANDIDATE_INVENTORY_FILENAME
        ).read_bytes()
        summary = {
            "candidate_inventory_sha256": hashlib.sha256(
                candidate_payload
            ).hexdigest(),
            "decision": report["decision"]["status"],
            "independent_inventory_sha256": candidate["candidate_schedule"][
                "inventory_sha256"
            ],
            "proposal_eligible": report["eligibility"][
                "empirical_successor_registration_proposal_eligible"
            ],
            "readiness_identity_sha256": report["readiness_identity_sha256"],
            "source_commit": commit,
            "status": "verified",
        }
        return SimpleNamespace(
            returncode=0,
            stdout=readiness.canonical_json_bytes(summary),
            stderr=b"",
        )

    monkeypatch.setattr(readiness, "_run_independent_verifier", verify)
    real_replace = readiness.os.replace

    def fail_final_install(source, destination):
        if (
            Path(source).name.endswith(".sealed")
            and Path(destination) == output
        ):
            output.mkdir()
            (output / "invalid-entry").write_text("not a publication\n")
            raise OSError("injected final install failure")
        return real_replace(source, destination)

    monkeypatch.setattr(readiness.os, "replace", fail_final_install)
    with pytest.raises(readiness.ReadinessAttemptTerminal) as captured:
        readiness.run_readiness_audit(
            repo_root=root,
            source_commit=commit,
            scratch_root=root / "scratch",
            output_dir=output,
            audit_id="failed-install-recovery-test",
        )

    assert captured.value.result["decision"]["reason"] == "no_go_artifact_binding"
    attempt_dir = root / readiness.ATTEMPT_ROOT_PATH / commit
    assert (attempt_dir / readiness.ATTEMPT_TERMINAL_FILENAME).is_file()
    assert not list(root.glob(".*.sealed"))


def test_seal_helper_return_interrupt_keeps_cleanup_ownership(
    tmp_path, monkeypatch
):
    root = (tmp_path / "repo").resolve()
    root.mkdir()
    output = root / "publication"
    commit = "a" * 40
    candidate = _candidate_artifact()
    monkeypatch.setattr(
        readiness,
        "observe_source_binding",
        lambda *_args, **_kwargs: _source_binding(),
    )
    monkeypatch.setattr(
        readiness,
        "build_candidate_from_git",
        lambda *_args, **_kwargs: (
            candidate,
            {"historical_throughput": _historical_throughput()},
        ),
    )
    monkeypatch.setattr(
        readiness,
        "run_actual_scale_rehearsal",
        lambda *_args, **_kwargs: _rehearsal(),
    )

    def verify(command, **_kwargs):
        staging = Path(command[command.index("--output-dir") + 1])
        report = json.loads((staging / readiness.REPORT_FILENAME).read_text())
        candidate_payload = (
            staging / readiness.CANDIDATE_INVENTORY_FILENAME
        ).read_bytes()
        summary = {
            "candidate_inventory_sha256": hashlib.sha256(
                candidate_payload
            ).hexdigest(),
            "decision": report["decision"]["status"],
            "independent_inventory_sha256": candidate["candidate_schedule"][
                "inventory_sha256"
            ],
            "proposal_eligible": report["eligibility"][
                "empirical_successor_registration_proposal_eligible"
            ],
            "readiness_identity_sha256": report["readiness_identity_sha256"],
            "source_commit": commit,
            "status": "verified",
        }
        return SimpleNamespace(
            returncode=0,
            stdout=readiness.canonical_json_bytes(summary),
            stderr=b"",
        )

    monkeypatch.setattr(readiness, "_run_independent_verifier", verify)
    real_seal = readiness._seal_verified_staging

    def interrupt_after_seal(*args, **kwargs):
        real_seal(*args, **kwargs)
        raise KeyboardInterrupt

    monkeypatch.setattr(
        readiness, "_seal_verified_staging", interrupt_after_seal
    )
    with pytest.raises(KeyboardInterrupt):
        readiness.run_readiness_audit(
            repo_root=root,
            source_commit=commit,
            scratch_root=root / "scratch",
            output_dir=output,
            audit_id="post-seal-return-interrupt-test",
        )

    attempt_dir = root / readiness.ATTEMPT_ROOT_PATH / commit
    assert (attempt_dir / readiness.ATTEMPT_TERMINAL_FILENAME).is_file()
    assert not output.exists()
    assert not list(root.glob(".*.sealed"))


def test_large_candidate_validation_never_deepcopies_owned_input():
    class DeepcopyForbiddenDict(dict):
        def __deepcopy__(self, memo):
            del memo
            raise AssertionError("deepcopy is forbidden for actual-scale evidence")

    candidate = _candidate_artifact()
    candidate["historical_seed_inventory"] = DeepcopyForbiddenDict(
        candidate["historical_seed_inventory"]
    )
    wrapped = DeepcopyForbiddenDict(candidate)
    assert readiness.validate_candidate_artifact(wrapped)["source_commit"] == "a" * 40
    assert verifier._verify_candidate(
        wrapped,
        independently_rebuilt_inventory=candidate["historical_seed_inventory"],
    )["source_commit"] == "a" * 40


def test_streamed_candidate_gzip_matches_canonical_bytes(tmp_path):
    candidate = _candidate_artifact()
    expected_canonical = readiness.canonical_json_bytes(candidate)
    expected_stored = readiness.deterministic_gzip_bytes(expected_canonical)
    destination = tmp_path / readiness.CANDIDATE_INVENTORY_FILENAME
    binding = readiness._write_canonical_gzip_file(destination, candidate)
    assert destination.read_bytes() == expected_stored
    assert binding == readiness._candidate_binding_from_encoded(
        expected_canonical, expected_stored
    )
    verifier_destination = tmp_path / "verifier-expected.json.gz"
    verifier_binding = verifier._write_expected_candidate_gzip(
        verifier_destination, candidate
    )
    assert verifier_destination.read_bytes() == expected_stored
    assert verifier_binding == binding


def test_independent_verifier_has_fixed_timeout_and_tree_termination(monkeypatch):
    assert readiness.INDEPENDENT_VERIFIER_CEILING_SECONDS == 900

    class TimedOutProcess:
        def communicate(self, timeout=None):
            assert timeout == 900
            raise subprocess.TimeoutExpired(["verifier"], timeout)

    process = TimedOutProcess()
    terminated = []
    monkeypatch.setattr(
        readiness,
        "_spawn_process_tree",
        lambda *_args, **_kwargs: process,
    )
    monkeypatch.setattr(
        readiness,
        "_terminate_process_tree",
        lambda observed: terminated.append(observed),
    )
    with pytest.raises(readiness.ReadinessBlocked, match="verifier.*timeout"):
        readiness._run_independent_verifier(
            ["verifier"],
            cwd=Path.cwd(),
            environment={},
        )
    assert terminated == [process]


def test_independent_verifier_interrupt_terminates_tree(monkeypatch):
    class InterruptedProcess:
        def communicate(self, timeout=None):
            assert timeout == readiness.INDEPENDENT_VERIFIER_CEILING_SECONDS
            raise KeyboardInterrupt

    process = InterruptedProcess()
    terminated = []
    monkeypatch.setattr(
        readiness,
        "_spawn_process_tree",
        lambda *_args, **_kwargs: process,
    )
    monkeypatch.setattr(
        readiness,
        "_terminate_process_tree",
        lambda observed: terminated.append(observed),
    )

    with pytest.raises(KeyboardInterrupt):
        readiness._run_independent_verifier(
            ["verifier"],
            cwd=Path.cwd(),
            environment={},
        )

    assert terminated == [process]


def test_windows_process_tree_termination_uses_taskkill_and_confirms_exit(
    monkeypatch,
):
    class Process:
        pid = 12345

        def __init__(self):
            self.exited = False

        def poll(self):
            return 1 if self.exited else None

        def kill(self):
            self.exited = True

        def wait(self, timeout=None):
            del timeout
            if not self.exited:
                raise subprocess.TimeoutExpired(["child"], 10)
            return 1

    process = Process()
    commands = []

    def taskkill(command, **kwargs):
        commands.append((command, kwargs))
        process.exited = True
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(readiness, "_IS_WINDOWS", True)
    monkeypatch.setattr(readiness.subprocess, "run", taskkill)
    readiness._terminate_process_tree(process)
    assert commands[0][0] == [
        "taskkill",
        "/PID",
        "12345",
        "/T",
        "/F",
    ]
    assert process.poll() is not None


def test_exited_process_still_terminates_and_confirms_bound_job(monkeypatch):
    class Job:
        def __init__(self):
            self.terminated = False
            self.closed = False

        def terminate_and_wait(self, timeout_seconds):
            assert timeout_seconds == 10
            self.terminated = True

        def close(self):
            self.closed = True

    class Process:
        pid = 12345

        def __init__(self, job):
            self._readiness_job = job

        def poll(self):
            return 0

        def wait(self, timeout=None):
            del timeout
            return 0

    job = Job()
    process = Process(job)
    monkeypatch.setattr(readiness, "_IS_WINDOWS", True)

    readiness._terminate_process_tree(process)

    assert process._readiness_job is None
    assert job.terminated is True
    assert job.closed is True


@pytest.mark.skipif(not readiness._IS_WINDOWS, reason="Windows Job Object contract")
def test_windows_job_terminates_descendant_after_parent_exit():
    child_code = (
        "from analysis_scripts.noncombat_cross_fitted_empirical_successor_readiness "
        "import _wait_for_windows_process_job_assignment as wait;wait();"
        "import subprocess,sys;"
        "child=subprocess.Popen([sys.executable,'-c',"
        "'import time;time.sleep(60)'],stdin=subprocess.DEVNULL,"
        "stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,close_fds=True);"
        "print(child.pid,flush=True)"
    )
    process = readiness._spawn_process_tree(
        [sys.executable, "-c", child_code],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert process.stdout is not None
    descendant_pid = int(process.stdout.readline().strip())
    assert process.wait(timeout=10) == 0

    readiness._terminate_process_tree(process)

    synchronize = 0x00100000
    wait_timeout = 0x00000102
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    handle = kernel32.OpenProcess(synchronize, False, descendant_pid)
    if handle:
        try:
            assert kernel32.WaitForSingleObject(handle, 0) != wait_timeout
        finally:
            kernel32.CloseHandle(handle)


def test_process_tree_termination_rejects_unconfirmed_direct_child_fallback(
    monkeypatch,
):
    class Process:
        pid = 12345

        def __init__(self):
            self.kill_count = 0
            self.wait_count = 0
            self.exited = False

        def poll(self):
            return 1 if self.exited else None

        def kill(self):
            self.kill_count += 1

        def wait(self, timeout=None):
            self.wait_count += 1
            if self.wait_count == 1:
                raise subprocess.TimeoutExpired(["child"], timeout)
            self.exited = True
            return 1

    process = Process()
    monkeypatch.setattr(readiness, "_IS_WINDOWS", True)
    monkeypatch.setattr(
        readiness.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=1),
    )

    with pytest.raises(readiness.ReadinessBlocked, match="descendant exit"):
        readiness._terminate_process_tree(process)

    assert process.kill_count == 2
    assert process.wait_count == 2
    assert process.poll() is not None


@pytest.mark.skipif(
    os.environ.get("STS_RUN_ACTUAL_SCALE_READINESS") != "1",
    reason="explicit one-shot 63 MB source-only rehearsal",
)
def test_actual_scale_rehearsal_is_isolated_verified_and_cleaned(tmp_path):
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    scratch = tmp_path / "actual-scale-rehearsal"
    result = readiness.run_actual_scale_rehearsal(
        ROOT,
        source_commit=commit,
        scratch_root=scratch,
    )
    assert result["status"] == "passed"
    assert result["synthetic_control_positions"] == 64
    assert result["context_validation_count"] == {
        "after_chunk": 1,
        "after_closeout": 1,
        "after_setup": 1,
    }
    assert set(result["empirical_operations"].values()) == {False}
    assert not scratch.exists()
