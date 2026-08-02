from __future__ import annotations

import copy
import json
import os
from pathlib import Path

import pytest

from analysis_scripts import noncombat_formal_rl_readiness_audit as audit


def _false_authority(**extra: bool) -> dict[str, bool]:
    return {"formal_noncombat_rl": False, **extra}


def _all_true(check_ids: list[str]) -> dict[str, bool]:
    return {check_id: True for check_id in check_ids}


def _ready_documents() -> dict:
    structural = audit._gate_contract()["structural_checks"]
    teacher_authority = _false_authority(policy_quality=False)
    smoke_authority = _false_authority(simulator_training_smoke=False)
    policy_authority = _false_authority(
        simulator_policy_validity=False, simulator_training=False
    )
    baseline_authority = _false_authority(
        simulator_rl_training=False, simulator_training=False
    )
    return {
        "teacher_configuration": {
            "authority": teacher_authority,
            "schema_version": audit.EVIDENCE_SCHEMAS["teacher_configuration"],
        },
        "teacher_report": {
            "adapter_gap_reasons": [],
            "audited_category_counts": {"card_reward": 4, "route": 5},
            "audited_row_count": 9,
            "authority": teacher_authority,
            "blockers": [],
            "reconstruction_match_count": 9,
            "reconstruction_mismatch_count": 0,
            "schema_version": audit.EVIDENCE_SCHEMAS["teacher_report"],
            "singleton_counts": {"card_reward": 0, "route": 2},
            "suitability_failed_check_ids": ["route_reads_survivability"],
            "verdict": "simpleagent_unsuitable_as_policy_quality_gate",
        },
        "simulator_smoke_registration": {
            "schema_version": audit.EVIDENCE_SCHEMAS[
                "simulator_smoke_registration"
            ],
            "smoke": {
                "cohorts": {"holdout_seeds": [3, 4], "train_seeds": [1, 2]},
                "reward": audit._gate_contract()["simulator_reward"],
            },
        },
        "simulator_smoke_metrics": {
            "authority": smoke_authority,
            "classification": {
                "authority": smoke_authority,
                "checks": _all_true(structural["simulator_smoke_metrics"]),
                "quality": "holdout_signal",
                "verdict": "pipeline_demonstrated_with_holdout_signal",
            },
            "schema_version": audit.EVIDENCE_SCHEMAS["simulator_smoke_metrics"],
        },
        "policy_validity_registration": {
            "schema_version": audit.EVIDENCE_SCHEMAS[
                "policy_validity_registration"
            ],
            "study": {
                "cohorts": {
                    "fit_seeds": [10],
                    "fresh_seeds": [40],
                    "smoke_holdout_seeds": [30],
                    "smoke_train_seeds": [20],
                },
                "execution": {"allow_model_update": False},
            },
        },
        "policy_validity_metrics": {
            "authority": policy_authority,
            "classification": {
                "authority": policy_authority,
                "checks": _all_true(structural["policy_validity_metrics"]),
                "quality": "baseline_signal",
                "verdict": "study_valid_with_baseline_signal",
            },
            "schema_version": audit.EVIDENCE_SCHEMAS["policy_validity_metrics"],
        },
        "baseline_registration": {
            "schema_version": audit.EVIDENCE_SCHEMAS["baseline_registration"],
            "study": {
                "cohorts": {
                    "excluded_prior_seeds": [10, 20, 30, 40],
                    "final_test_seeds": [70],
                    "train_seeds": [50],
                    "validation_seeds": [60],
                }
            },
        },
        "baseline_metrics": {
            "authority": baseline_authority,
            "classification": {
                "authority": baseline_authority,
                "blockers": [],
                "checks": _all_true(structural["baseline_metrics"]),
                "final_gate": {"passed": True},
                "final_test_untouched": False,
                "quality": "baseline_floor_demonstrated",
                "validation_gate": {"passed": True},
                "verdict": "study_valid_with_baseline_floor",
            },
            "schema_version": audit.EVIDENCE_SCHEMAS["baseline_metrics"],
        },
        "outcome_feasibility_input": {
            "schema_version": audit.EVIDENCE_SCHEMAS[
                "outcome_feasibility_input"
            ]
        },
        "outcome_feasibility_report": {
            "authority": _false_authority(),
            "operating_characteristics": {
                "plug_in_pass_probability": "0.900000000000"
            },
            "reference_evidence": {
                "reference_comparability": "source_comparable",
                "target_supported_victories": 3,
            },
            "result": {"blockers": [], "study_feasibility": "demonstrated"},
            "schema_version": audit.EVIDENCE_SCHEMAS[
                "outcome_feasibility_report"
            ],
            "source": {"manifest": {}},
        },
        "formal_reward_contract": {
            "authority": _false_authority(),
            "contract_id": "formal-reward-v1",
            "exclusions": audit._gate_contract()["formal_reward"][
                "required_exclusions"
            ],
            "primary_objective": audit._gate_contract()["formal_reward"][
                "primary_objective"
            ],
            "provenance": {"simulator_live_separated": True},
            "reference_labels_excluded": True,
            "schema_version": audit.FORMAL_REWARD_SCHEMA_VERSION,
            "secondary_channels": [
                {"outcome_field": "floor_reached", "role": "diagnostic"}
            ],
            "verification": {
                check_id: True
                for check_id in audit._gate_contract()["formal_reward"][
                    "required_verification_checks"
                ]
            },
        },
    }


def _context(documents: dict) -> audit.ValidatedReadinessContext:
    return audit.ValidatedReadinessContext(
        registration={"contract": audit._gate_contract()},
        registration_sha256="a" * 64,
        documents=documents,
        inventory={
            "evidence": {},
            "registration_sha256": "a" * 64,
            "schema_version": audit.INVENTORY_SCHEMA_VERSION,
        },
    )


def test_ready_synthetic_evidence_only_allows_a_separate_proposal():
    documents = _ready_documents()
    domains = audit.evaluate_domains(documents)

    assert all(domain["status"] == "passed" for domain in domains.values())
    assert audit.classify_verdict(domains) == "ready_for_bounded_training_proposal"

    execution = audit.execute_audit(_context(documents))
    report = execution["report"]
    assert report["bounded_training_proposal_consideration"] is True
    assert report["authority"] == audit._authority()
    assert not any(report["authority"].values())


def test_current_shape_blocks_reward_baseline_and_outcome_in_fixed_order():
    documents = _ready_documents()
    documents.pop("formal_reward_contract")
    baseline = documents["baseline_metrics"]["classification"]
    baseline.update(
        {
            "final_gate": None,
            "final_test_untouched": True,
            "quality": "baseline_floor_not_demonstrated",
            "validation_gate": {"passed": False},
            "verdict": "study_valid_without_baseline_floor",
        }
    )
    outcome = documents["outcome_feasibility_report"]
    outcome["operating_characteristics"]["plug_in_pass_probability"] = (
        "0.000000000000"
    )
    outcome["reference_evidence"].update(
        {
            "reference_comparability": "historical_reference_only",
            "target_supported_victories": 0,
        }
    )
    outcome["result"] = {
        "blockers": [
            "reference_not_source_comparable",
            "no_target_supported_victory",
            "plug_in_pass_probability_below_minimum",
        ],
        "study_feasibility": "not_demonstrated",
    }

    execution = audit.execute_audit(_context(documents))

    assert execution["report"]["verdict"] == (
        "not_ready_for_bounded_training_proposal"
    )
    assert execution["report"]["failed_domains"] == [
        "reward",
        "baseline_policy",
        "outcome_support",
    ]
    assert execution["report"]["next_prerequisites"] == [
        "add_noncombat_formal_reward_contract",
        "establish_non_teacher_credible_baseline_floor",
        "expand_source_comparable_target_supported_outcomes",
    ]
    assert execution["matrix"]["domains"]["evaluation"]["status"] == "passed"


def test_teacher_limitation_stays_auxiliary_and_does_not_request_imitation():
    documents = _ready_documents()
    domains = audit.evaluate_domains(documents)

    reference = domains["reference_isolation"]
    assert reference["status"] == "passed"
    assert reference["details"]["teacher_verdict"] == (
        "simpleagent_unsuitable_as_policy_quality_gate"
    )
    assert reference["details"]["teacher_suitability_failed_check_ids"]
    assert "simpleagent" not in audit._gate_contract()["recommendations"][
        "baseline_policy"
    ]


def test_incomplete_formal_reward_contract_blocks_only_reward_domain():
    documents = _ready_documents()
    documents["formal_reward_contract"].pop("provenance")

    domains = audit.evaluate_domains(documents)

    assert domains["reward"]["status"] == "blocked"
    assert domains["reward"]["blockers"] == ["formal_reward_contract_not_ready"]
    assert domains["state_action"]["status"] == "passed"
    assert domains["evaluation"]["status"] == "passed"


def test_invalid_evidence_precedes_domain_results_and_authority_leaks_fail():
    domains = audit.evaluate_domains(_ready_documents())
    domains["reward"]["status"] = "blocked"
    assert audit.classify_verdict(domains, integrity_valid=False) == "invalid_evidence"

    with pytest.raises(audit.ReadinessAuditBlocked, match="authority must remain false"):
        audit._require_all_false_authorities(
            {"authority": {"formal_noncombat_rl": True}}, "fixture"
        )


def _write_json(root: Path, relative: str, value: dict) -> Path:
    path = root.joinpath(*Path(relative).parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(audit.canonical_json_bytes(value))
    return path


def _binding(path: Path, root: Path) -> dict:
    payload = path.read_bytes()
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": audit.sha256_bytes(payload),
        "size_bytes": len(payload),
    }


def _registered_fixture(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    authority_leak: bool = False,
) -> tuple[dict, dict[str, Path], bytes]:
    documents = _ready_documents()
    if authority_leak:
        documents["teacher_report"]["authority"]["formal_noncombat_rl"] = True
    implementation_path = root / audit.SCRIPT_RELATIVE_PATH
    implementation_path.parent.mkdir(parents=True, exist_ok=True)
    implementation_bytes = b"# frozen readiness implementation\n"
    implementation_path.write_bytes(implementation_bytes)

    paths: dict[str, Path] = {}
    for evidence_id in (
        "teacher_configuration",
        "simulator_smoke_registration",
        "policy_validity_registration",
        "baseline_registration",
        "outcome_feasibility_input",
        "formal_reward_contract",
    ):
        paths[evidence_id] = _write_json(
            root, f"evidence/{evidence_id}.json", documents[evidence_id]
        )
    for evidence_id in (
        "simulator_smoke_registration",
        "baseline_registration",
    ):
        paths[evidence_id].write_text(
            json.dumps(documents[evidence_id], separators=(",", ":")),
            encoding="utf-8",
        )

    teacher_report_path = _write_json(
        root, "evidence/teacher_report.json", documents["teacher_report"]
    )
    paths["teacher_report"] = teacher_report_path
    teacher_manifest = {
        "artifact_hashes": {
            "report.json": audit.sha256_bytes(teacher_report_path.read_bytes())
        },
        "authority": _false_authority(),
        "canonical_artifact_names": [],
        "configuration_sha256": audit.sha256_bytes(
            paths["teacher_configuration"].read_bytes()
        ),
        "managed_inventory": [],
        "schema_version": audit.EVIDENCE_SCHEMAS["teacher_manifest"],
        "verdict": documents["teacher_report"]["verdict"],
    }
    paths["teacher_manifest"] = _write_json(
        root, "evidence/teacher_manifest.json", teacher_manifest
    )

    linked_groups = (
        ("simulator_smoke", "simulator_smoke_registration", "simulator_smoke_metrics"),
        ("policy_validity", "policy_validity_registration", "policy_validity_metrics"),
        ("baseline", "baseline_registration", "baseline_metrics"),
    )
    for prefix, registration_id, metrics_id in linked_groups:
        registration_hash = audit.sha256_bytes(
            audit.canonical_json_bytes(documents[registration_id])
        )
        metrics = copy.deepcopy(documents[metrics_id])
        metrics["registration_sha256"] = registration_hash
        metrics_path = _write_json(root, f"evidence/{metrics_id}.json", metrics)
        paths[metrics_id] = metrics_path
        manifest_id = prefix + "_manifest"
        if prefix == "baseline":
            manifest_id = "baseline_manifest"
        manifest = {
            "artifact_hashes": {
                "metrics.json": audit.sha256_bytes(metrics_path.read_bytes())
            },
            "authority": _false_authority(),
            "canonical_artifact_names": [],
            "registration_sha256": registration_hash,
            "schema_version": audit.EVIDENCE_SCHEMAS[manifest_id],
            "verdict": metrics["classification"]["verdict"],
        }
        paths[manifest_id] = _write_json(
            root, f"evidence/{manifest_id}.json", manifest
        )

    feasibility = copy.deepcopy(documents["outcome_feasibility_report"])
    feasibility["source"]["manifest"] = _binding(
        paths["outcome_feasibility_input"], root
    )
    paths["outcome_feasibility_report"] = _write_json(
        root, "evidence/outcome_feasibility_report.json", feasibility
    )

    registration = audit.build_registration(
        repo_root=root,
        implementation_commit="a" * 40,
        evidence_paths=paths,
    )
    monkeypatch.setattr(
        audit, "_git_blob_bytes", lambda *_args, **_kwargs: implementation_bytes
    )
    return registration, paths, implementation_bytes


def test_registration_declared_missing_and_identity_drift_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    registration, paths, _ = _registered_fixture(tmp_path, monkeypatch)
    missing = copy.deepcopy(registration)
    missing["evidence"]["formal_reward_contract"] = None
    missing["declared_missing_evidence"] = ["formal_reward_contract"]
    assert audit.validate_registration(missing)["declared_missing_evidence"] == [
        "formal_reward_contract"
    ]

    audit.load_validated_context(registration, repo_root=tmp_path)
    paths["teacher_report"].write_bytes(b"{}\n")
    with pytest.raises(
        audit.ReadinessAuditBlocked, match=r"(?:size|SHA-256) mismatch"
    ):
        audit.load_validated_context(registration, repo_root=tmp_path)


def test_registered_authority_leak_is_invalid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    registration, _, _ = _registered_fixture(
        tmp_path, monkeypatch, authority_leak=True
    )
    with pytest.raises(audit.ReadinessAuditBlocked, match="authority must remain false"):
        audit.load_validated_context(registration, repo_root=tmp_path)


def test_atomic_publication_manifest_and_strict_recomputation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    registration, _, _ = _registered_fixture(tmp_path, monkeypatch)
    context = audit.load_validated_context(registration, repo_root=tmp_path)
    output = tmp_path / "canonical"
    installed = []

    def record_replace(source, destination):
        installed.append(Path(destination).name)
        os.replace(source, destination)

    artifacts = audit.build_artifacts(
        context=context, execution=audit.execute_audit(context)
    )
    audit.publish_artifacts(output, artifacts, replace=record_replace)
    manifest = audit.validate_artifact_directory(output)

    assert manifest["verdict"] == "ready_for_bounded_training_proposal"
    assert set(path.name for path in output.iterdir()) == set(
        audit.CANONICAL_ARTIFACT_NAMES
    )
    assert installed[-1] == "artifact_manifest.json"
    assert audit.recompute_artifact_directory(
        context=context, output_dir=output
    ) == manifest

    (output / "report.md").write_text("tampered\n", encoding="utf-8")
    with pytest.raises(audit.ReadinessAuditBlocked, match="hash closure mismatch"):
        audit.recompute_artifact_directory(context=context, output_dir=output)


def test_atomic_publication_cleans_staging_on_replace_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    registration, _, _ = _registered_fixture(tmp_path, monkeypatch)
    context = audit.load_validated_context(registration, repo_root=tmp_path)
    artifacts = audit.build_artifacts(
        context=context, execution=audit.execute_audit(context)
    )
    destination = tmp_path / "replace-failure"

    def fail_replace(_source, _destination):
        raise RuntimeError("replace failed")

    with pytest.raises(RuntimeError, match="replace failed"):
        audit.publish_artifacts(destination, artifacts, replace=fail_replace)

    assert not destination.exists()
