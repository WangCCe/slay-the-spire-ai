from __future__ import annotations

import copy
import gzip
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

import pytest

from analysis_scripts import (
    audit_hierarchical_card_reward_credit_assignment as audit,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PREIMPLEMENTATION_PATH = REPO_ROOT / (
    "reports/noncombat_hierarchical_card_reward_credit_assignment_"
    "audit_20260806_preimplementation.json"
)


def _canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _binding(path: str, payload: bytes) -> dict[str, object]:
    return {
        "path": path,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _lease_identity() -> dict[str, str]:
    return {
        "authorization_sha256": "a" * 64,
        "logical_execution_id": "fixture-execution-r1",
        "registration_sha256": "b" * 64,
    }


def _analysis_rows(
    count: int = 64,
    *,
    take_count: int = 32,
    combined_pressure: float = 0.001,
) -> list[dict[str, object]]:
    rows = []
    for index in range(count):
        selected = "take" if index < take_count else "skip"
        rows.append(
            {
                "combined_pressure": combined_pressure,
                "expected_conditional_entropy": 0.2,
                "expected_conditional_entropy_pressure": 0.0,
                "family_entropy": 0.6,
                "family_entropy_pressure": 0.0,
                "normalized_return": 1.0 if selected == "take" else -1.0,
                "policy_pressure": combined_pressure,
                "reward_to_go": 2.0 if selected == "take" else 0.0,
                "seed": 100 + index // 16,
                "selected_family": selected,
                "take_conditional_entropy": 0.3,
            }
        )
    return rows


def _report() -> dict[str, object]:
    return {
        "analysis": {
            "chunk_summaries": [],
            "eligible_decision_count": 64,
            "global_summary": {
                "combined_pressure_sum": 0.5,
                "skip_count": 32,
                "support": "supported",
                "take_count": 32,
            },
            "seed_clusters": [],
            "strata": {},
            "terminal_window": {
                "chunk_indices": [4, 5, 6, 7],
                "mean_take_family_margins": [0.05, 0.06, 0.07, 0.08],
                "strictly_growing": True,
            },
        },
        "authority": audit.audit_authority(),
        "identity": {
            "logical_execution_id": "fixture-execution-r1",
            "source": {
                "commit": "a" * 40,
                "git_blob": "b" * 40,
                "path": audit.DEFAULT_SOURCE_PATH,
                "sha256": "c" * 64,
                "size_bytes": 123,
            },
        },
        "integrity": {
            "consumed_artifact_count": 22,
            "input_bindings_verified": True,
            "source_only": True,
            "terminal_bundle_unchanged": True,
        },
        "limitations": list(audit.LIMITATIONS),
        "reconstruction": {
            "chunk_count": 8,
            "decision_count": 11807,
            "objective_reconciled": True,
            "training_episode_count": 512,
        },
        "schema_version": audit.AUDIT_SCHEMA_VERSION,
        "verdict": {
            "classification": (
                "direct_take_pressure_aligned_but_stratum_heterogeneous"
            ),
            "downstream_authority": audit.audit_authority(),
        },
    }


@pytest.mark.parametrize(
    "payload,match",
    [
        (b'{"a":1,"a":2}\n', "duplicate key"),
        (b'{"a":1}\n', "not canonical JSON"),
        (b'{"a":NaN}\n', "non-finite constant"),
    ],
)
def test_canonical_json_parser_fails_closed(payload: bytes, match: str) -> None:
    with pytest.raises(audit.CreditAssignmentAuditError, match=match):
        audit.parse_canonical_json_bytes(payload, "fixture")


def test_gzip_binding_checks_stored_and_canonical_identity(tmp_path: Path) -> None:
    canonical = _canonical({"chunks": [], "schema_version": "fixture-v1"})
    stored = gzip.compress(canonical, mtime=0)
    path = tmp_path / "training_rows.json.gz"
    path.write_bytes(stored)
    binding = {
        **_binding("training_rows.json.gz", stored),
        "canonical_sha256": hashlib.sha256(canonical).hexdigest(),
        "canonical_size_bytes": len(canonical),
        "compression": "gzip-mtime-zero-v1",
    }

    value, loaded = audit.load_bound_gzip_json(path, binding, "training rows")

    assert value == {"chunks": [], "schema_version": "fixture-v1"}
    assert loaded == canonical

    path.write_bytes(stored + b"drift")
    with pytest.raises(audit.CreditAssignmentAuditError, match="stored identity"):
        audit.load_bound_gzip_json(path, binding, "training rows")


def test_gzip_binding_rejects_canonical_hash_and_encoding_drift(
    tmp_path: Path,
) -> None:
    value = {"chunks": [], "schema_version": "fixture-v1"}
    canonical = _canonical(value)
    path = tmp_path / "training_rows.json.gz"
    path.write_bytes(gzip.compress(canonical, mtime=0))
    binding = {
        **_binding("training_rows.json.gz", path.read_bytes()),
        "canonical_sha256": "0" * 64,
        "canonical_size_bytes": len(canonical),
        "compression": "gzip-mtime-zero-v1",
    }
    with pytest.raises(audit.CreditAssignmentAuditError, match="canonical identity"):
        audit.load_bound_gzip_json(path, binding, "training rows")

    noncanonical = json.dumps(value, sort_keys=True).encode("utf-8")
    stored = gzip.compress(noncanonical, mtime=0)
    path.write_bytes(stored)
    binding.update(
        {
            "canonical_sha256": hashlib.sha256(noncanonical).hexdigest(),
            "canonical_size_bytes": len(noncanonical),
            "sha256": hashlib.sha256(stored).hexdigest(),
            "size_bytes": len(stored),
        }
    )
    with pytest.raises(audit.CreditAssignmentAuditError, match="not canonical JSON"):
        audit.load_bound_gzip_json(path, binding, "training rows")


def test_gzip_binding_rejects_declared_payload_above_fixed_bound(
    tmp_path: Path,
) -> None:
    canonical = _canonical({"schema_version": "fixture-v1"})
    stored = gzip.compress(canonical, mtime=0)
    path = tmp_path / "training_rows.json.gz"
    path.write_bytes(stored)
    binding = {
        **_binding("training_rows.json.gz", stored),
        "canonical_sha256": hashlib.sha256(canonical).hexdigest(),
        "canonical_size_bytes": audit._MAX_GZIP_BYTES + 1,
        "compression": "gzip-mtime-zero-v1",
    }

    with pytest.raises(audit.CreditAssignmentAuditError, match="bounded gzip"):
        audit.load_bound_gzip_json(path, binding, "training rows")


def test_inactive_lease_is_locked_before_identity_validation(
    tmp_path: Path,
) -> None:
    identity = _lease_identity()
    payload = _canonical(
        {
            "identity": identity,
            "schema_version": audit.LEASE_SCHEMA_VERSION,
        }
    )
    path = tmp_path / ".execution.lease"
    path.write_bytes(payload)
    binding = _binding(".execution.lease", payload)

    with audit.hold_inactive_lease(path, binding, identity) as locked_bytes:
        assert locked_bytes == payload
    assert path.read_bytes() == payload

    changed = copy.deepcopy(identity)
    changed["logical_execution_id"] = "different-r1"
    with pytest.raises(audit.CreditAssignmentAuditError, match="lease identity"):
        with audit.hold_inactive_lease(path, binding, changed):
            pass


def test_active_lease_fails_closed(tmp_path: Path) -> None:
    identity = _lease_identity()
    payload = _canonical(
        {
            "identity": identity,
            "schema_version": audit.LEASE_SCHEMA_VERSION,
        }
    )
    path = tmp_path / ".execution.lease"
    path.write_bytes(payload)
    binding = _binding(".execution.lease", payload)

    with path.open("r+b", buffering=0) as handle:
        audit.lock_file(handle)
        try:
            with pytest.raises(
                audit.CreditAssignmentAuditError,
                match="active execution",
            ):
                with audit.hold_inactive_lease(path, binding, identity):
                    pass
        finally:
            audit.unlock_file(handle)


def test_terminal_snapshot_excludes_only_the_root_lease(tmp_path: Path) -> None:
    root_lease = tmp_path / ".execution.lease"
    nested_lease = tmp_path / "nested/.execution.lease"
    nested_lease.parent.mkdir()
    root_lease.write_bytes(b"root")
    nested_lease.write_bytes(b"nested")

    snapshot = audit._terminal_snapshot(tmp_path)

    assert [row[0] for row in snapshot] == ["nested/.execution.lease"]


def test_head_source_identity_rejects_untracked_and_modified_bytes(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(
        ["git", "config", "user.email", "fixture@example.invalid"],
        cwd=repo,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Fixture"], cwd=repo, check=True
    )
    source = repo / audit.DEFAULT_SOURCE_PATH
    source.parent.mkdir(parents=True)
    payload = b'print("fixture")\n'
    source.write_bytes(payload)
    subprocess.run(["git", "add", "--", audit.DEFAULT_SOURCE_PATH], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "fixture"], cwd=repo, check=True)

    identity = audit.verify_head_source(repo, audit.DEFAULT_SOURCE_PATH)

    assert identity["sha256"] == hashlib.sha256(payload).hexdigest()
    assert identity["size_bytes"] == len(payload)
    assert len(identity["commit"]) == 40
    assert len(identity["git_blob"]) == 40

    source.write_bytes(payload + b"# drift\n")
    with pytest.raises(audit.CreditAssignmentAuditError, match="differs from HEAD"):
        audit.verify_head_source(repo, audit.DEFAULT_SOURCE_PATH)

    untracked = repo / "analysis_scripts/untracked.py"
    untracked.write_text("pass\n", encoding="ascii")
    with pytest.raises(audit.CreditAssignmentAuditError, match="tracked at HEAD"):
        audit.verify_head_source(repo, "analysis_scripts/untracked.py")


def test_fresh_import_loads_no_torch_native_or_runtime_modules() -> None:
    code = "\n".join(
        [
            "import json, sys",
            "from analysis_scripts import audit_hierarchical_card_reward_credit_assignment",
            "blocked = sorted(name for name in sys.modules if name == 'torch' or name.startswith('torch.') or 'noncombat_hierarchical_simulator_learning_runtime' in name or 'noncombat_simulator_adapter' in name)",
            "print(json.dumps(blocked))",
        ]
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(completed.stdout) == []


def test_import_isolation_detects_registered_native_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "sts_lightspeed_noncombat_adapter", object())

    assert (
        "sts_lightspeed_noncombat_adapter"
        in audit._forbidden_loaded_modules()
    )


def test_float32_reduction_matches_registered_torch_cpu_fixture() -> None:
    values = [
        -0.15160924196243286,
        -0.12343040108680725,
        -0.07578526437282562,
        -0.20351681113243103,
        -0.06522375345230103,
    ]

    assert audit.float32_mean(values) == -0.12391309440135956


def test_return_reconstruction_preserves_episode_and_row_order() -> None:
    rows = [
        {"decision_index": 0, "formal_reward": {"scalar_reward": 0.0}, "seed": 10},
        {"decision_index": 1, "formal_reward": {"scalar_reward": 1.0}, "seed": 10},
        {"decision_index": 0, "formal_reward": {"scalar_reward": 0.0}, "seed": 11},
        {"decision_index": 1, "formal_reward": {"scalar_reward": 0.0}, "seed": 11},
    ]

    reconstructed = audit.reconstruct_normalized_returns(rows, [10, 11])

    assert reconstructed["reward_to_go"] == [1.0, 1.0, 0.0, 0.0]
    assert reconstructed["normalized_returns"] == [1.0, 1.0, -1.0, -1.0]
    assert reconstructed["mean"] == 0.5
    assert reconstructed["standard_deviation"] == 0.5

    drifted = [rows[2], rows[3], rows[0], rows[1]]
    with pytest.raises(audit.CreditAssignmentAuditError, match="row order"):
        audit.reconstruct_normalized_returns(drifted, [10, 11])


def test_zero_variance_returns_use_registered_zero_branch() -> None:
    rows = [
        {"decision_index": 0, "formal_reward": {"scalar_reward": 0.0}, "seed": 1},
        {"decision_index": 0, "formal_reward": {"scalar_reward": 0.0}, "seed": 2},
    ]

    result = audit.reconstruct_normalized_returns(rows, [1, 2])

    assert result["standard_deviation"] == 0.0
    assert result["normalized_returns"] == [0.0, 0.0]


def test_conditional_entropy_and_direct_pressure_include_all_registered_terms() -> None:
    take_entropy = -0.25 * math.log(0.25) - 0.75 * math.log(0.75)
    row = {
        "candidates": [
            {"action_id": "take:a", "kind": "take"},
            {"action_id": "take:b", "kind": "take"},
            {"action_id": "skip", "kind": "skip"},
        ],
        "conditional_probabilities": {
            "skip": 1.0,
            "take:a": 0.25,
            "take:b": 0.75,
        },
        "entropies": {
            "expected_conditional": 0.6 * take_entropy,
            "family": -(0.6 * math.log(0.6) + 0.4 * math.log(0.4)),
        },
        "family_order": ["skip", "take"],
        "family_probabilities": {"skip": 0.4, "take": 0.6},
        "selected_family": "take",
    }

    entropies = audit.reconstruct_conditional_entropies(row, "fixture")
    pressure = audit.direct_take_pressure(
        normalized_return=1.25,
        selected_family="take",
        take_probability=0.6,
        family_entropy=row["entropies"]["family"],
        take_conditional_entropy=entropies["by_family"]["take"],
        expected_conditional_entropy=entropies["expected"],
        chunk_decision_count=100,
    )

    assert entropies["by_family"]["take"] == pytest.approx(take_entropy)
    assert entropies["by_family"]["skip"] == 0.0
    assert pressure == pytest.approx(
        {
            "combined": 0.005003764880876256,
            "expected_conditional_entropy": 1.34960434708514e-05,
            "family_entropy": -9.731162594595948e-06,
            "policy": 0.005,
        }
    )

    drifted = copy.deepcopy(row)
    drifted["entropies"]["expected_conditional"] += 0.01
    with pytest.raises(audit.CreditAssignmentAuditError, match="conditional entropy"):
        audit.reconstruct_conditional_entropies(drifted, "fixture")


@pytest.mark.parametrize(
    "floor,ordinal,probability,margin,expected",
    [
        (16.999, 0, 0.499, 0.024, ("<17", "first", "[0,0.50)", "[0,0.025)")),
        (17.0, 1, 0.50, 0.025, ("17..33", "second", "[0.50,0.51)", "[0.025,0.05)")),
        (34.0, 2, 0.51, 0.05, (">=34", "later", "[0.51,0.52)", "[0.05,0.075)")),
        (57.0, 9, 0.52, 0.075, (">=34", "later", "[0.52,1]", "[0.075,+inf)")),
    ],
)
def test_fixed_stratum_boundaries(
    floor: float,
    ordinal: int,
    probability: float,
    margin: float,
    expected: tuple[str, str, str, str],
) -> None:
    labels = audit.stratum_labels(
        effective_floor=floor,
        card_reward_ordinal=ordinal,
        take_probability=probability,
        family_margin=margin,
    )

    assert (
        labels["effective_floor"],
        labels["ordinal"],
        labels["take_propensity"],
        labels["family_margin"],
    ) == expected


def test_support_thresholds_and_selected_family_associations() -> None:
    supported = audit.summarize_stratum("all", _analysis_rows())
    sparse = audit.summarize_stratum("sparse", _analysis_rows(63, take_count=32))
    one_sided = audit.summarize_stratum(
        "one-sided", _analysis_rows(64, take_count=15)
    )

    assert supported["support"] == "supported"
    assert supported["take_count"] == 32
    assert supported["skip_count"] == 32
    assert supported["selected_family_associations"]["take"][
        "mean_normalized_return"
    ] == 1.0
    assert supported["selected_family_associations"]["skip"][
        "mean_normalized_return"
    ] == -1.0
    assert supported["mean_expected_conditional_entropy"] == 0.2
    assert supported["mean_take_conditional_entropy"] == 0.3
    assert sparse["support"] == "insufficient"
    assert one_sided["support"] == "insufficient"


def test_seed_clusters_preserve_repeated_decisions_and_sort_seed() -> None:
    rows = _analysis_rows()

    clusters = audit.summarize_seed_clusters(list(reversed(rows)))

    assert [row["seed"] for row in clusters] == [100, 101, 102, 103]
    assert all(row["eligible_count"] == 16 for row in clusters)
    assert sum(row["eligible_count"] for row in clusters) == 64


def _classify(
    *,
    reconstruction_valid: bool = True,
    global_supported: bool = True,
    supported_dimensions: dict[str, bool] | None = None,
    chunk_pressures: list[float] | None = None,
    terminal_window_margins: list[float] | None = None,
    nonchunk_strata: list[dict[str, object]] | None = None,
) -> str:
    return audit.classify_verdict(
        reconstruction_valid=reconstruction_valid,
        global_supported=global_supported,
        supported_dimensions=supported_dimensions
        or {
            "effective_floor": True,
            "family_margin": True,
            "ordinal": True,
            "take_propensity": True,
        },
        chunk_pressures=chunk_pressures or [1.0] * 8,
        terminal_window_margins=terminal_window_margins or [0.1, 0.2, 0.3, 0.4],
        nonchunk_strata=nonchunk_strata
        or [{"combined_pressure_sum": 1.0, "support": "supported"}],
    )


def test_verdict_precedence_is_fixed_and_reconstruction_failure_aborts() -> None:
    with pytest.raises(audit.CreditAssignmentAuditError, match="reconstruction"):
        _classify(reconstruction_valid=False)

    assert _classify(global_supported=False, chunk_pressures=[-1.0] * 8) == (
        "insufficient_overlap_or_evidence"
    )
    assert _classify(chunk_pressures=[1.0] * 7 + [0.0]) == (
        "direct_take_pressure_not_aligned"
    )
    assert _classify(terminal_window_margins=[0.1, 0.2, 0.2, 0.4]) == (
        "direct_take_pressure_not_aligned"
    )
    assert _classify(
        nonchunk_strata=[
            {"combined_pressure_sum": -0.1, "support": "supported"}
        ]
    ) == "direct_take_pressure_aligned_but_stratum_heterogeneous"
    assert _classify(
        nonchunk_strata=[
            {"combined_pressure_sum": -1.0, "support": "insufficient"},
            {"combined_pressure_sum": 1.0, "support": "supported"},
        ]
    ) == "direct_take_pressure_consistently_aligned"


def test_report_publication_is_byte_deterministic_and_all_false(
    tmp_path: Path,
) -> None:
    report = _report()
    output_json = tmp_path / "audit.json"
    output_markdown = tmp_path / "audit.md"

    audit.publish_reports(report, output_json, output_markdown)
    first = output_json.read_bytes(), output_markdown.read_bytes()
    audit.publish_reports(report, output_json, output_markdown)

    assert (output_json.read_bytes(), output_markdown.read_bytes()) == first
    assert output_json.read_bytes() == audit.canonical_json_bytes(report)
    assert output_markdown.read_bytes().endswith(b"\n")
    assert not any(report["authority"].values())
    assert not any(report["verdict"]["downstream_authority"].values())
    assert b"direct_take_pressure_aligned_but_stratum_heterogeneous" in first[1]


def test_preimplementation_record_binds_existing_terminal_evidence() -> None:
    record = audit.validate_preimplementation_record(
        REPO_ROOT,
        PREIMPLEMENTATION_PATH,
    )

    assert record["identity"]["planning_commit"] == (
        "4a23558cec1f55ec2efa3497064e47a568b04092"
    )
    assert len(record["inputs"]["checkpoints"]) == 8
    assert not any(record["authority"].values())
    assert record["verifier_result"]["verification"] == "verified"


def test_terminal_metadata_accepts_only_recorded_execution_authority() -> None:
    preimplementation = audit.parse_canonical_json_bytes(
        PREIMPLEMENTATION_PATH.read_bytes(),
        "preimplementation record",
    )
    inputs = preimplementation["inputs"]
    lease_binding = inputs["lease_control"]
    expected_identity = {
        "authorization_sha256": inputs["authorization"]["sha256"],
        "logical_execution_id": audit.LOGICAL_EXECUTION_ID,
        "registration_sha256": inputs["registration"]["sha256"],
    }
    terminal_root = REPO_ROOT / audit.DEFAULT_TERMINAL_DIRECTORY
    manifest_binding = inputs["artifact_manifest"]

    with audit.hold_inactive_lease(
        REPO_ROOT / lease_binding["path"],
        lease_binding,
        expected_identity,
    ) as locked_lease_bytes:
        audit.validate_preimplementation_record(
            REPO_ROOT,
            PREIMPLEMENTATION_PATH,
            locked_lease_bytes=locked_lease_bytes,
        )
        manifest, _ = audit.load_bound_json(
            REPO_ROOT / manifest_binding["path"],
            manifest_binding,
            "terminal artifact manifest",
        )
        bindings = audit._validate_manifest(manifest, terminal_root)
        metadata = audit._validate_terminal_metadata(
            terminal_root,
            bindings,
            manifest["identity"],
        )

    assert len(metadata["train_seeds"]) == 1024
    assert {
        name
        for name, authorized in audit.recorded_execution_authority().items()
        if authorized
    } == set(audit.RECORDED_EXECUTION_ENABLED)
    assert not any(audit.audit_authority().values())


def test_cli_rejects_all_caller_overrides(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        audit.main(["--repo-root", str(tmp_path)])
