"""Synthesize frozen evidence for formal non-combat RL readiness."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from typing import Any

from analysis_scripts.noncombat_simulator_adapter import (
    canonical_json_bytes,
    sha256_bytes,
)


class ReadinessAuditBlocked(ValueError):
    """Raised when registered readiness evidence cannot be trusted."""


REGISTRATION_SCHEMA_VERSION = "noncombat-formal-rl-readiness-audit-input-v1"
INVENTORY_SCHEMA_VERSION = "noncombat-formal-rl-readiness-evidence-inventory-v1"
MATRIX_SCHEMA_VERSION = "noncombat-formal-rl-readiness-matrix-v1"
REPORT_SCHEMA_VERSION = "noncombat-formal-rl-readiness-report-v1"
MANIFEST_SCHEMA_VERSION = "noncombat-formal-rl-readiness-manifest-v1"
FORMAL_REWARD_SCHEMA_VERSION = "noncombat-formal-rl-reward-contract-v1"
SCRIPT_RELATIVE_PATH = (
    "analysis_scripts/noncombat_formal_rl_readiness_audit.py"
)

EVIDENCE_SCHEMAS = {
    "teacher_configuration": (
        "noncombat-state-action-teacher-sufficiency-audit-input-v2"
    ),
    "teacher_manifest": "noncombat-state-action-teacher-audit-manifest-v1",
    "teacher_report": "noncombat-state-action-teacher-audit-report-v1",
    "simulator_smoke_registration": "noncombat-simulator-training-smoke-input-v1",
    "simulator_smoke_manifest": (
        "noncombat-simulator-training-smoke-artifact-manifest-v1"
    ),
    "simulator_smoke_metrics": "noncombat-simulator-training-metrics-v1",
    "policy_validity_registration": "noncombat-simulator-policy-validity-input-v1",
    "policy_validity_manifest": "noncombat-simulator-policy-validity-manifest-v1",
    "policy_validity_metrics": "noncombat-simulator-policy-validity-metrics-v1",
    "baseline_registration": "noncombat-simulator-baseline-warm-start-input-v1",
    "baseline_manifest": "noncombat-simulator-baseline-manifest-v1",
    "baseline_metrics": "noncombat-simulator-baseline-metrics-artifact-v1",
    "outcome_feasibility_input": "noncombat-study-feasibility-input-v1",
    "outcome_feasibility_report": "noncombat-study-feasibility-v1",
    "formal_reward_contract": FORMAL_REWARD_SCHEMA_VERSION,
}
OPTIONAL_EVIDENCE_IDS = ("formal_reward_contract",)
REQUIRED_EVIDENCE_IDS = tuple(
    name for name in EVIDENCE_SCHEMAS if name not in OPTIONAL_EVIDENCE_IDS
)
DOMAIN_ORDER = (
    "state_action",
    "reference_isolation",
    "reward",
    "baseline_policy",
    "outcome_support",
    "evaluation",
)
VERDICT_ORDER = (
    "invalid_evidence",
    "not_ready_for_bounded_training_proposal",
    "ready_for_bounded_training_proposal",
)
CANONICAL_ARTIFACT_NAMES = (
    "artifact_manifest.json",
    "configuration.json",
    "evidence_inventory.json",
    "readiness_matrix.json",
    "report.json",
    "report.md",
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def _authority() -> dict[str, bool]:
    return {
        "formal_noncombat_rl": False,
        "gameplay": False,
        "live_policy_loading": False,
        "model_fitting": False,
        "native_module_loading": False,
        "ope_reinterpretation": False,
        "policy_promotion": False,
        "qualification": False,
        "simulator_rollout": False,
        "simulator_training": False,
    }


def _gate_contract() -> dict[str, Any]:
    return {
        "baseline": {
            "passing_quality": "baseline_floor_demonstrated",
            "passing_verdict": "study_valid_with_baseline_floor",
        },
        "domain_order": list(DOMAIN_ORDER),
        "formal_reward": {
            "expected_schema": FORMAL_REWARD_SCHEMA_VERSION,
            "primary_objective": {
                "direction": "maximize",
                "name": "terminal_victory",
                "outcome_field": "victory",
            },
            "required_exclusions": [
                "bottled_label",
                "current_policy_label",
                "simpleagent_label",
                "teacher_agreement",
            ],
            "required_verification_checks": [
                "formula_tests",
                "provenance_boundary_tests",
                "terminal_objective_tests",
            ],
            "secondary_floor_roles": ["diagnostic", "potential_shaping"],
        },
        "outcome_support": {
            "minimum_pass_probability": "0.800000000000",
            "minimum_supported_victories": 3,
            "passing_comparability": "source_comparable",
            "passing_status": "demonstrated",
        },
        "prerequisite_order": list(DOMAIN_ORDER),
        "recommendations": {
            "baseline_policy": "establish_non_teacher_credible_baseline_floor",
            "evaluation": "complete_noncombat_evaluation_isolation_contract",
            "outcome_support": (
                "expand_source_comparable_target_supported_outcomes"
            ),
            "reference_isolation": "isolate_auxiliary_reference_roles",
            "reward": "add_noncombat_formal_reward_contract",
            "state_action": "repair_noncombat_state_action_contract",
        },
        "reference_roles": {
            "bottled": "auxiliary_reference",
            "current": "behavior_reference",
            "simpleagent": "auxiliary_regression_oracle",
        },
        "simulator_reward": {
            "max_floor": 57,
            "progress_divisor": 57.0,
            "version": "simulator-floor-progress-victory-v1",
            "victory_bonus": 1.0,
        },
        "structural_checks": {
            "baseline_metrics": [
                "episode_budget",
                "final_test_access_contract",
                "identity",
                "implementation_fit",
                "model_frozen",
                "registration",
                "registration_hash_closure",
                "replay_identity",
                "train_four_category_coverage",
            ],
            "policy_validity_metrics": [
                "candidate_legality",
                "episode_count",
                "finite_metrics",
                "four_category_coverage",
                "model_immutability",
                "no_gradients",
                "replay_identity",
                "terminal_outcomes",
                "within_bounds",
            ],
            "simulator_smoke_metrics": [
                "candidate_legality",
                "four_category_coverage",
                "replay_identity",
                "seed_disjoint",
                "terminal_outcomes",
                "within_bounds",
            ],
        },
        "verdict_precedence": list(VERDICT_ORDER),
        "version": "noncombat-formal-rl-readiness-gates-v1",
    }


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ReadinessAuditBlocked(f"invalid_evidence: {label} must be an object")
    return value


def _require_keys(
    value: Mapping[str, Any], expected: set[str], label: str
) -> None:
    actual = set(value)
    if actual != expected:
        raise ReadinessAuditBlocked(
            f"invalid_evidence: {label} keys differ: "
            f"missing={sorted(expected - actual)}, extra={sorted(actual - expected)}"
        )


def _strict_json_bytes(payload: bytes, label: str) -> dict[str, Any]:
    def reject_duplicates(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ReadinessAuditBlocked(
                    f"invalid_evidence: {label} contains duplicate key {key!r}"
                )
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise ReadinessAuditBlocked(
            f"invalid_evidence: {label} contains non-finite number {value}"
        )

    try:
        parsed = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=reject_duplicates,
            parse_constant=reject_constant,
        )
    except ReadinessAuditBlocked:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ReadinessAuditBlocked(
            f"invalid_evidence: {label} is invalid JSON: {exc}"
        ) from exc
    return dict(_mapping(parsed, label))


def _canonical_relative_path(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ReadinessAuditBlocked(f"invalid_evidence: {label} path is invalid")
    pure = PurePosixPath(value)
    if (
        pure.is_absolute()
        or "\\" in value
        or any(part in {"", ".", ".."} for part in pure.parts)
        or pure.as_posix() != value
    ):
        raise ReadinessAuditBlocked(
            f"invalid_evidence: {label} path must be canonical repo-relative"
        )
    return value


def _validate_binding(
    value: object,
    label: str,
    *,
    expected_schema: str | None,
) -> dict[str, Any]:
    binding = dict(_mapping(value, label))
    expected_keys = {"path", "sha256", "size_bytes"}
    if expected_schema is not None:
        expected_keys.add("expected_schema")
    _require_keys(binding, expected_keys, label)
    binding["path"] = _canonical_relative_path(binding["path"], label)
    digest = binding.get("sha256")
    if not isinstance(digest, str) or not _SHA256_PATTERN.fullmatch(digest):
        raise ReadinessAuditBlocked(
            f"invalid_evidence: {label} SHA-256 is invalid"
        )
    size = binding.get("size_bytes")
    if type(size) is not int or size < 0:
        raise ReadinessAuditBlocked(
            f"invalid_evidence: {label} size_bytes is invalid"
        )
    if expected_schema is not None and binding.get("expected_schema") != expected_schema:
        raise ReadinessAuditBlocked(
            f"invalid_evidence: {label} expected schema drifted"
        )
    return binding


def validate_registration(value: object) -> dict[str, Any]:
    registration = dict(_mapping(value, "registration"))
    _require_keys(
        registration,
        {
            "authority",
            "contract",
            "declared_missing_evidence",
            "evidence",
            "identity",
            "schema_version",
        },
        "registration",
    )
    if registration["schema_version"] != REGISTRATION_SCHEMA_VERSION:
        raise ReadinessAuditBlocked("invalid_evidence: registration schema mismatch")
    if registration["authority"] != _authority():
        raise ReadinessAuditBlocked("invalid_evidence: registration authority drifted")
    if registration["contract"] != _gate_contract():
        raise ReadinessAuditBlocked("invalid_evidence: readiness gate contract drifted")

    identity = dict(_mapping(registration["identity"], "registration.identity"))
    _require_keys(identity, {"implementation", "source_commit"}, "identity")
    if not isinstance(identity["source_commit"], str) or not _COMMIT_PATTERN.fullmatch(
        identity["source_commit"]
    ):
        raise ReadinessAuditBlocked("invalid_evidence: source commit is invalid")
    identity["implementation"] = _validate_binding(
        identity["implementation"],
        "identity.implementation",
        expected_schema=None,
    )
    if identity["implementation"]["path"] != SCRIPT_RELATIVE_PATH:
        raise ReadinessAuditBlocked(
            "invalid_evidence: implementation path differs from the audit source"
        )
    registration["identity"] = identity

    evidence = dict(_mapping(registration["evidence"], "registration.evidence"))
    if set(evidence) != set(EVIDENCE_SCHEMAS):
        raise ReadinessAuditBlocked(
            "invalid_evidence: registered evidence inventory differs"
        )
    for evidence_id, schema in EVIDENCE_SCHEMAS.items():
        item = evidence[evidence_id]
        if item is None:
            if evidence_id not in OPTIONAL_EVIDENCE_IDS:
                raise ReadinessAuditBlocked(
                    f"invalid_evidence: required evidence is absent: {evidence_id}"
                )
            continue
        evidence[evidence_id] = _validate_binding(
            item, f"evidence.{evidence_id}", expected_schema=schema
        )
    registration["evidence"] = evidence

    declared_missing = registration["declared_missing_evidence"]
    if not isinstance(declared_missing, list) or any(
        not isinstance(item, str) for item in declared_missing
    ):
        raise ReadinessAuditBlocked(
            "invalid_evidence: declared_missing_evidence is invalid"
        )
    expected_missing = sorted(name for name, item in evidence.items() if item is None)
    if declared_missing != expected_missing:
        raise ReadinessAuditBlocked(
            "invalid_evidence: declared missing evidence does not match bindings"
        )
    return registration


def load_registration(path: Path | str) -> dict[str, Any]:
    payload = Path(path).read_bytes()
    registration = validate_registration(_strict_json_bytes(payload, "registration"))
    if payload != canonical_json_bytes(registration):
        raise ReadinessAuditBlocked(
            "invalid_evidence: registration bytes are not canonical"
        )
    return registration


def _resolved_repo_path(repo_root: Path, relative: str, label: str) -> Path:
    root = repo_root.resolve()
    pure = PurePosixPath(relative)
    path = root.joinpath(*pure.parts).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ReadinessAuditBlocked(
            f"invalid_evidence: {label} path escapes repository"
        ) from exc
    return path


def _binding_for_path(
    path: Path | str,
    *,
    repo_root: Path,
    expected_schema: str | None,
) -> dict[str, Any]:
    root = repo_root.resolve()
    absolute = Path(path).resolve()
    try:
        relative = absolute.relative_to(root).as_posix()
    except ValueError as exc:
        raise ReadinessAuditBlocked(
            f"invalid_evidence: registration input is outside repository: {absolute}"
        ) from exc
    payload = absolute.read_bytes()
    binding: dict[str, Any] = {
        "path": relative,
        "sha256": sha256_bytes(payload),
        "size_bytes": len(payload),
    }
    if expected_schema is not None:
        document = _strict_json_bytes(payload, relative)
        if document.get("schema_version") != expected_schema:
            raise ReadinessAuditBlocked(
                f"invalid_evidence: {relative} schema mismatch"
            )
        binding["expected_schema"] = expected_schema
    return binding


def build_registration(
    *,
    repo_root: Path | str,
    implementation_commit: str,
    evidence_paths: Mapping[str, Path | str | None],
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    if set(evidence_paths) != set(EVIDENCE_SCHEMAS):
        raise ReadinessAuditBlocked(
            "invalid_evidence: evidence path inventory differs"
        )
    evidence: dict[str, Any] = {}
    for evidence_id, schema in EVIDENCE_SCHEMAS.items():
        path = evidence_paths[evidence_id]
        evidence[evidence_id] = (
            None
            if path is None
            else _binding_for_path(path, repo_root=root, expected_schema=schema)
        )
    registration = {
        "authority": _authority(),
        "contract": _gate_contract(),
        "declared_missing_evidence": sorted(
            name for name, item in evidence.items() if item is None
        ),
        "evidence": evidence,
        "identity": {
            "implementation": _binding_for_path(
                root.joinpath(*PurePosixPath(SCRIPT_RELATIVE_PATH).parts),
                repo_root=root,
                expected_schema=None,
            ),
            "source_commit": implementation_commit,
        },
        "schema_version": REGISTRATION_SCHEMA_VERSION,
    }
    return validate_registration(registration)


def _git_blob_bytes(repo_root: Path, commit: str, relative_path: str) -> bytes:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "show", f"{commit}:{relative_path}"],
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ReadinessAuditBlocked(
            "invalid_evidence: cannot read registered implementation commit"
        ) from exc
    return result.stdout


def _verify_binding_bytes(
    binding: Mapping[str, Any], *, repo_root: Path, label: str
) -> tuple[bytes, Path]:
    path = _resolved_repo_path(repo_root, str(binding["path"]), label)
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise ReadinessAuditBlocked(
            f"invalid_evidence: cannot read {label}: {path}"
        ) from exc
    if len(payload) != binding["size_bytes"]:
        raise ReadinessAuditBlocked(f"invalid_evidence: {label} size mismatch")
    if sha256_bytes(payload) != binding["sha256"]:
        raise ReadinessAuditBlocked(f"invalid_evidence: {label} SHA-256 mismatch")
    return payload, path


def _require_all_false_authorities(value: object, label: str) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            child_label = f"{label}.{key}"
            if key == "authority":
                authority = _mapping(item, child_label)
                if not authority:
                    raise ReadinessAuditBlocked(
                        f"invalid_evidence: {child_label} is empty"
                    )
                for name, enabled in authority.items():
                    if type(enabled) is not bool or enabled:
                        raise ReadinessAuditBlocked(
                            "invalid_evidence: authority must remain false: "
                            f"{child_label}.{name}"
                        )
            _require_all_false_authorities(item, child_label)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _require_all_false_authorities(item, f"{label}[{index}]")


def _nested(value: Mapping[str, Any], *keys: str) -> Any:
    current: Any = value
    for key in keys:
        current = _mapping(current, ".".join(keys))[key]
    return current


def _validate_embedded_identity(
    documents: Mapping[str, Mapping[str, Any]],
    bindings: Mapping[str, Mapping[str, Any] | None],
) -> None:
    teacher_manifest = documents["teacher_manifest"]
    teacher_report = documents["teacher_report"]
    teacher_hashes = _mapping(
        teacher_manifest.get("artifact_hashes"), "teacher artifact_hashes"
    )
    if teacher_manifest.get("configuration_sha256") != bindings[
        "teacher_configuration"
    ]["sha256"]:
        raise ReadinessAuditBlocked(
            "invalid_evidence: teacher configuration link mismatch"
        )
    if teacher_hashes.get("report.json") != bindings["teacher_report"]["sha256"]:
        raise ReadinessAuditBlocked("invalid_evidence: teacher report link mismatch")
    if teacher_manifest.get("verdict") != teacher_report.get("verdict"):
        raise ReadinessAuditBlocked("invalid_evidence: teacher verdict link mismatch")

    linked_groups = (
        (
            "simulator_smoke_registration",
            "simulator_smoke_manifest",
            "simulator_smoke_metrics",
        ),
        (
            "policy_validity_registration",
            "policy_validity_manifest",
            "policy_validity_metrics",
        ),
        ("baseline_registration", "baseline_manifest", "baseline_metrics"),
    )
    for registration_id, manifest_id, metrics_id in linked_groups:
        expected_registration = sha256_bytes(
            canonical_json_bytes(documents[registration_id])
        )
        manifest = documents[manifest_id]
        metrics = documents[metrics_id]
        if (
            manifest.get("registration_sha256") != expected_registration
            or metrics.get("registration_sha256") != expected_registration
        ):
            raise ReadinessAuditBlocked(
                f"invalid_evidence: {metrics_id} registration link mismatch"
            )
        hashes = _mapping(
            manifest.get("artifact_hashes"), f"{manifest_id}.artifact_hashes"
        )
        if hashes.get("metrics.json") != bindings[metrics_id]["sha256"]:
            raise ReadinessAuditBlocked(
                f"invalid_evidence: {metrics_id} manifest link mismatch"
            )
        classification = _mapping(
            metrics.get("classification"), f"{metrics_id}.classification"
        )
        if manifest.get("verdict") != classification.get("verdict"):
            raise ReadinessAuditBlocked(
                f"invalid_evidence: {metrics_id} verdict link mismatch"
            )

    feasibility = documents["outcome_feasibility_report"]
    source_manifest = _nested(feasibility, "source", "manifest")
    input_binding = bindings["outcome_feasibility_input"]
    if dict(source_manifest) != {
        "path": input_binding["path"],
        "sha256": input_binding["sha256"],
        "size_bytes": input_binding["size_bytes"],
    }:
        raise ReadinessAuditBlocked(
            "invalid_evidence: outcome feasibility input link mismatch"
        )


def _validate_structural_checks(
    documents: Mapping[str, Mapping[str, Any]], contract: Mapping[str, Any]
) -> None:
    structural = _mapping(contract["structural_checks"], "structural checks")
    for evidence_id, required in structural.items():
        checks = _nested(documents[evidence_id], "classification", "checks")
        for check_id in required:
            if checks.get(check_id) is not True:
                raise ReadinessAuditBlocked(
                    "invalid_evidence: required structural check failed: "
                    f"{evidence_id}.{check_id}"
                )


@dataclass(frozen=True)
class ValidatedReadinessContext:
    registration: dict[str, Any]
    registration_sha256: str
    documents: dict[str, dict[str, Any]]
    inventory: dict[str, Any]


def load_validated_context(
    registration: Mapping[str, Any], *, repo_root: Path | str
) -> ValidatedReadinessContext:
    value = validate_registration(registration)
    root = Path(repo_root).resolve()
    implementation = value["identity"]["implementation"]
    implementation_bytes, _ = _verify_binding_bytes(
        implementation, repo_root=root, label="registered implementation"
    )
    committed_bytes = _git_blob_bytes(
        root, value["identity"]["source_commit"], implementation["path"]
    )
    if committed_bytes != implementation_bytes:
        raise ReadinessAuditBlocked(
            "invalid_evidence: implementation bytes differ from registered commit"
        )

    documents: dict[str, dict[str, Any]] = {}
    inventory_items: dict[str, Any] = {}
    for evidence_id, binding in value["evidence"].items():
        if binding is None:
            inventory_items[evidence_id] = {
                "expected_schema": EVIDENCE_SCHEMAS[evidence_id],
                "status": "declared_missing",
            }
            continue
        payload, _ = _verify_binding_bytes(
            binding, repo_root=root, label=f"evidence.{evidence_id}"
        )
        document = _strict_json_bytes(payload, f"evidence.{evidence_id}")
        if document.get("schema_version") != binding["expected_schema"]:
            raise ReadinessAuditBlocked(
                f"invalid_evidence: evidence.{evidence_id} schema mismatch"
            )
        documents[evidence_id] = document
        inventory_items[evidence_id] = {
            "expected_schema": binding["expected_schema"],
            "path": binding["path"],
            "sha256": binding["sha256"],
            "size_bytes": binding["size_bytes"],
            "status": "validated",
        }

    _validate_embedded_identity(documents, value["evidence"])
    _validate_structural_checks(documents, value["contract"])
    _require_all_false_authorities(value, "registration")
    for evidence_id, document in documents.items():
        _require_all_false_authorities(document, evidence_id)

    registration_sha256 = sha256_bytes(canonical_json_bytes(value))
    inventory = {
        "evidence": inventory_items,
        "registration_sha256": registration_sha256,
        "schema_version": INVENTORY_SCHEMA_VERSION,
    }
    return ValidatedReadinessContext(
        registration=value,
        registration_sha256=registration_sha256,
        documents=documents,
        inventory=inventory,
    )


def _domain(
    *,
    checks: Mapping[str, bool],
    evidence: Sequence[str],
    blocker: str,
    details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    checked = dict(checks)
    passed = all(checked.values())
    return {
        "blockers": [] if passed else [blocker],
        "checks": checked,
        "details": dict(details or {}),
        "evidence": list(evidence),
        "status": "passed" if passed else "blocked",
    }


def _seed_set(value: object, label: str) -> set[int]:
    if not isinstance(value, list) or any(type(item) is not int for item in value):
        raise ReadinessAuditBlocked(f"invalid_evidence: {label} seeds are invalid")
    if len(set(value)) != len(value):
        raise ReadinessAuditBlocked(f"invalid_evidence: {label} seeds repeat")
    return set(value)


def _pairwise_disjoint(groups: Sequence[set[int]]) -> bool:
    seen: set[int] = set()
    for group in groups:
        if seen.intersection(group):
            return False
        seen.update(group)
    return True


def _decimal(value: object, label: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ReadinessAuditBlocked(
            f"invalid_evidence: {label} is not a decimal"
        ) from exc
    if not result.is_finite():
        raise ReadinessAuditBlocked(f"invalid_evidence: {label} is not finite")
    return result


def evaluate_domains(
    documents: Mapping[str, Mapping[str, Any]],
    *,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    gates = dict(contract or _gate_contract())
    teacher = documents["teacher_report"]
    smoke_registration = documents["simulator_smoke_registration"]
    smoke_metrics = documents["simulator_smoke_metrics"]
    policy_registration = documents["policy_validity_registration"]
    policy_metrics = documents["policy_validity_metrics"]
    baseline_registration = documents["baseline_registration"]
    baseline_metrics = documents["baseline_metrics"]
    feasibility = documents["outcome_feasibility_report"]

    category_counts = _mapping(
        teacher.get("audited_category_counts"), "teacher category counts"
    )
    singleton_counts = _mapping(
        teacher.get("singleton_counts"), "teacher singleton counts"
    )
    smoke_checks = _nested(smoke_metrics, "classification", "checks")
    state_checks = {
        "adapter_gaps_absent": teacher.get("adapter_gap_reasons") == [],
        "card_reward_multi_candidate_rows": (
            category_counts.get("card_reward", 0)
            - singleton_counts.get("card_reward", 0)
            > 0
        ),
        "four_category_candidate_coverage": (
            smoke_checks.get("four_category_coverage") is True
        ),
        "reconstruction_exact": (
            teacher.get("reconstruction_mismatch_count") == 0
            and teacher.get("reconstruction_match_count")
            == teacher.get("audited_row_count")
        ),
        "route_multi_candidate_rows": (
            category_counts.get("route", 0) - singleton_counts.get("route", 0)
            > 0
        ),
        "simulator_candidate_legality": (
            smoke_checks.get("candidate_legality") is True
        ),
        "teacher_audit_blockers_absent": teacher.get("blockers") == [],
    }
    state_action = _domain(
        checks=state_checks,
        evidence=["teacher_report", "simulator_smoke_metrics"],
        blocker="state_action_contract_not_closed",
        details={
            "audited_rows": teacher.get("audited_row_count"),
            "reconstruction_matches": teacher.get("reconstruction_match_count"),
        },
    )

    suitability_failures = teacher.get("suitability_failed_check_ids")
    teacher_is_limited = isinstance(suitability_failures, list) and bool(
        suitability_failures
    )
    formal_reward = documents.get("formal_reward_contract")
    smoke_reward = _nested(smoke_registration, "smoke", "reward")
    reference_checks = {
        "formal_reward_excludes_references_when_present": (
            formal_reward is None
            or formal_reward.get("reference_labels_excluded") is True
        ),
        "reference_roles_are_auxiliary": gates.get("reference_roles")
        == _gate_contract()["reference_roles"],
        "simulator_reward_is_reference_free": dict(smoke_reward)
        == gates["simulator_reward"],
        "teacher_limitation_is_preserved": (
            not teacher_is_limited
            or teacher.get("verdict")
            == "simpleagent_unsuitable_as_policy_quality_gate"
        ),
        "teacher_policy_quality_authority_closed": (
            _mapping(teacher.get("authority"), "teacher authority").get(
                "policy_quality"
            )
            is False
        ),
    }
    reference_isolation = _domain(
        checks=reference_checks,
        evidence=["teacher_report", "simulator_smoke_registration"],
        blocker="auxiliary_reference_roles_not_isolated",
        details={
            "teacher_suitability_failed_check_ids": suitability_failures,
            "teacher_verdict": teacher.get("verdict"),
        },
    )

    reward_contract = _mapping(gates["formal_reward"], "formal reward gates")
    if formal_reward is None:
        reward_checks = {
            "formal_contract_present": False,
            "primary_terminal_victory": False,
            "reference_labels_excluded": False,
            "secondary_floor_role_explicit": False,
            "simulator_live_provenance_separated": False,
            "verification_checks_pass": False,
        }
        reward_details = {
            "simulator_reward": dict(smoke_reward),
            "simulator_reward_scope": "simulator_training_smoke_only",
        }
    else:
        secondary = formal_reward.get("secondary_channels")
        provenance = formal_reward.get("provenance")
        floor_channels = []
        if isinstance(secondary, list):
            floor_channels = [
                item
                for item in secondary
                if isinstance(item, Mapping)
                and item.get("outcome_field") == "floor_reached"
            ]
        verification = formal_reward.get("verification")
        exclusions = formal_reward.get("exclusions")
        reward_checks = {
            "formal_contract_present": True,
            "primary_terminal_victory": formal_reward.get("primary_objective")
            == reward_contract["primary_objective"],
            "reference_labels_excluded": (
                formal_reward.get("reference_labels_excluded") is True
                and isinstance(exclusions, list)
                and set(reward_contract["required_exclusions"]).issubset(exclusions)
            ),
            "secondary_floor_role_explicit": (
                len(floor_channels) == 1
                and floor_channels[0].get("role")
                in reward_contract["secondary_floor_roles"]
            ),
            "simulator_live_provenance_separated": (
                isinstance(provenance, Mapping)
                and provenance.get("simulator_live_separated")
                is True
            ),
            "verification_checks_pass": (
                isinstance(verification, Mapping)
                and all(
                    verification.get(check_id) is True
                    for check_id in reward_contract[
                        "required_verification_checks"
                    ]
                )
            ),
        }
        reward_details = {
            "formal_reward_contract_id": formal_reward.get("contract_id"),
            "simulator_reward": dict(smoke_reward),
        }
    reward = _domain(
        checks=reward_checks,
        evidence=[
            "simulator_smoke_registration",
            "formal_reward_contract",
        ],
        blocker=(
            "formal_reward_contract_missing"
            if formal_reward is None
            else "formal_reward_contract_not_ready"
        ),
        details=reward_details,
    )

    baseline_classification = _mapping(
        baseline_metrics.get("classification"), "baseline classification"
    )
    policy_classification = _mapping(
        policy_metrics.get("classification"), "policy classification"
    )
    baseline_contract = _mapping(gates["baseline"], "baseline gate")
    baseline_checks = {
        "baseline_quality_demonstrated": baseline_classification.get("quality")
        == baseline_contract["passing_quality"],
        "baseline_verdict_passes": baseline_classification.get("verdict")
        == baseline_contract["passing_verdict"],
        "final_gate_passed": (
            isinstance(baseline_classification.get("final_gate"), Mapping)
            and baseline_classification["final_gate"].get("passed") is True
        ),
        "final_test_access_contract": _mapping(
            baseline_classification.get("checks"), "baseline checks"
        ).get("final_test_access_contract")
        is True,
        "replay_identity": _mapping(
            baseline_classification.get("checks"), "baseline checks"
        ).get("replay_identity")
        is True,
        "validation_gate_passed": _mapping(
            baseline_classification.get("validation_gate"), "validation gate"
        ).get("passed")
        is True,
    }
    baseline_policy = _domain(
        checks=baseline_checks,
        evidence=[
            "baseline_registration",
            "baseline_metrics",
            "policy_validity_metrics",
        ],
        blocker="credible_baseline_floor_not_demonstrated",
        details={
            "baseline_quality": baseline_classification.get("quality"),
            "baseline_verdict": baseline_classification.get("verdict"),
            "policy_validity_quality": policy_classification.get("quality"),
            "policy_validity_verdict": policy_classification.get("verdict"),
        },
    )

    outcome_contract = _mapping(gates["outcome_support"], "outcome gate")
    reference_evidence = _mapping(
        feasibility.get("reference_evidence"), "feasibility reference evidence"
    )
    feasibility_result = _mapping(
        feasibility.get("result"), "feasibility result"
    )
    operating = _mapping(
        feasibility.get("operating_characteristics"),
        "feasibility operating characteristics",
    )
    supported_victories = reference_evidence.get("target_supported_victories")
    outcome_checks = {
        "feasibility_demonstrated": feasibility_result.get("study_feasibility")
        == outcome_contract["passing_status"],
        "pass_probability_floor": _decimal(
            operating.get("plug_in_pass_probability"), "plug-in pass probability"
        )
        >= _decimal(
            outcome_contract["minimum_pass_probability"],
            "minimum pass probability",
        ),
        "source_comparable": reference_evidence.get("reference_comparability")
        == outcome_contract["passing_comparability"],
        "supported_victory_floor": (
            type(supported_victories) is int
            and supported_victories
            >= outcome_contract["minimum_supported_victories"]
        ),
    }
    outcome_support = _domain(
        checks=outcome_checks,
        evidence=["outcome_feasibility_input", "outcome_feasibility_report"],
        blocker="target_supported_outcome_evidence_not_demonstrated",
        details={
            "feasibility_blockers": feasibility_result.get("blockers"),
            "plug_in_pass_probability": operating.get(
                "plug_in_pass_probability"
            ),
            "target_supported_victories": supported_victories,
        },
    )

    smoke_cohorts = _nested(smoke_registration, "smoke", "cohorts")
    smoke_train = _seed_set(smoke_cohorts.get("train_seeds"), "smoke train")
    smoke_holdout = _seed_set(
        smoke_cohorts.get("holdout_seeds"), "smoke holdout"
    )
    policy_study = _mapping(policy_registration.get("study"), "policy study")
    policy_cohorts = _mapping(policy_study.get("cohorts"), "policy cohorts")
    policy_groups = [
        _seed_set(policy_cohorts.get(name), f"policy {name}")
        for name in (
            "fit_seeds",
            "smoke_train_seeds",
            "smoke_holdout_seeds",
            "fresh_seeds",
        )
    ]
    baseline_study = _mapping(
        baseline_registration.get("study"), "baseline study"
    )
    baseline_cohorts = _mapping(
        baseline_study.get("cohorts"), "baseline cohorts"
    )
    baseline_groups = [
        _seed_set(baseline_cohorts.get(name), f"baseline {name}")
        for name in ("train_seeds", "validation_seeds", "final_test_seeds")
    ]
    excluded = _seed_set(
        baseline_cohorts.get("excluded_prior_seeds"), "baseline excluded prior"
    )
    policy_checks = _mapping(
        policy_classification.get("checks"), "policy classification checks"
    )
    baseline_structural = _mapping(
        baseline_classification.get("checks"), "baseline classification checks"
    )
    evaluation_checks = {
        "baseline_cohorts_isolated": (
            _pairwise_disjoint(baseline_groups)
            and not excluded.intersection(set().union(*baseline_groups))
        ),
        "final_test_access_contract": baseline_structural.get(
            "final_test_access_contract"
        )
        is True,
        "frozen_policy_evaluation": (
            _nested(policy_study, "execution").get("allow_model_update") is False
            and policy_checks.get("model_immutability") is True
            and policy_checks.get("no_gradients") is True
        ),
        "policy_cohorts_isolated": _pairwise_disjoint(policy_groups),
        "registered_replays_match": (
            smoke_checks.get("replay_identity") is True
            and policy_checks.get("replay_identity") is True
            and baseline_structural.get("replay_identity") is True
        ),
        "smoke_train_holdout_disjoint": smoke_train.isdisjoint(smoke_holdout),
    }
    evaluation = _domain(
        checks=evaluation_checks,
        evidence=[
            "simulator_smoke_registration",
            "simulator_smoke_metrics",
            "policy_validity_registration",
            "policy_validity_metrics",
            "baseline_registration",
            "baseline_metrics",
        ],
        blocker="evaluation_isolation_contract_not_closed",
    )

    return {
        "state_action": state_action,
        "reference_isolation": reference_isolation,
        "reward": reward,
        "baseline_policy": baseline_policy,
        "outcome_support": outcome_support,
        "evaluation": evaluation,
    }


def classify_verdict(
    domains: Mapping[str, Mapping[str, Any]], *, integrity_valid: bool = True
) -> str:
    if not integrity_valid:
        return "invalid_evidence"
    if set(domains) != set(DOMAIN_ORDER):
        raise ReadinessAuditBlocked(
            "invalid_evidence: readiness domain inventory differs"
        )
    if all(domains[name].get("status") == "passed" for name in DOMAIN_ORDER):
        return "ready_for_bounded_training_proposal"
    return "not_ready_for_bounded_training_proposal"


def execute_audit(context: ValidatedReadinessContext) -> dict[str, Any]:
    domains = evaluate_domains(
        context.documents, contract=context.registration["contract"]
    )
    verdict = classify_verdict(domains)
    failed_domains = [
        name for name in DOMAIN_ORDER if domains[name]["status"] != "passed"
    ]
    recommendations = context.registration["contract"]["recommendations"]
    prerequisites = [recommendations[name] for name in failed_domains]
    bounded_consideration = verdict == "ready_for_bounded_training_proposal"
    matrix = {
        "domain_order": list(DOMAIN_ORDER),
        "domains": domains,
        "failed_domains": failed_domains,
        "integrity": {
            "checks": {
                "embedded_identities": True,
                "no_authority_leak": True,
                "registered_bytes": True,
                "registered_schemas": True,
                "structural_replays": True,
            },
            "status": "passed",
        },
        "registration_sha256": context.registration_sha256,
        "schema_version": MATRIX_SCHEMA_VERSION,
        "verdict": verdict,
    }
    report = {
        "authority": _authority(),
        "bounded_training_proposal_consideration": bounded_consideration,
        "failed_domains": failed_domains,
        "limitations": [
            "Simulator evidence remains separate from live evidence.",
            "Reference policies remain auxiliary and are not reward or policy-quality truth.",
            "A positive verdict requires a separate accepted OpenSpec before execution.",
        ],
        "next_prerequisites": prerequisites,
        "registration_sha256": context.registration_sha256,
        "schema_version": REPORT_SCHEMA_VERSION,
        "verdict": verdict,
    }
    return {"matrix": matrix, "report": report}


def _render_markdown(
    *, report: Mapping[str, Any], matrix: Mapping[str, Any]
) -> str:
    lines = [
        "# Non-Combat Formal RL Readiness Audit",
        "",
        f"- Verdict: `{report['verdict']}`",
        "- Bounded-training proposal consideration: "
        f"`{str(report['bounded_training_proposal_consideration']).lower()}`",
        f"- Registration SHA-256: `{report['registration_sha256']}`",
        "- Training, gameplay, loading, OPE, qualification, and promotion authority: `false`",
        "",
        "## Readiness Matrix",
        "",
        "| Domain | Status | Blockers |",
        "| --- | --- | --- |",
    ]
    for name in matrix["domain_order"]:
        domain = matrix["domains"][name]
        blockers = ", ".join(domain["blockers"]) or "None"
        lines.append(f"| `{name}` | `{domain['status']}` | {blockers} |")
    lines.extend(["", "## Next Prerequisites", ""])
    if report["next_prerequisites"]:
        lines.extend(f"- `{item}`" for item in report["next_prerequisites"])
    else:
        lines.append("- None; review a separate bounded-training proposal.")
    lines.extend(["", "## Evidence Interpretation", ""])
    for name in matrix["domain_order"]:
        domain = matrix["domains"][name]
        lines.append(f"### {name.replace('_', ' ').title()}")
        lines.append("")
        for check_id, passed in domain["checks"].items():
            lines.append(f"- `{check_id}`: `{str(passed).lower()}`")
        if domain["details"]:
            lines.append(
                "- Details: `"
                + json.dumps(domain["details"], sort_keys=True, separators=(",", ":"))
                + "`"
            )
        lines.append("")
    lines.extend(["## Limitations", ""])
    lines.extend(f"- {item}" for item in report["limitations"])
    return "\n".join(lines) + "\n"


def _artifact_binding(payload: bytes) -> dict[str, Any]:
    return {"sha256": sha256_bytes(payload), "size_bytes": len(payload)}


def build_artifacts(
    *, context: ValidatedReadinessContext, execution: Mapping[str, Any]
) -> dict[str, bytes]:
    report = dict(_mapping(execution.get("report"), "execution.report"))
    matrix = dict(_mapping(execution.get("matrix"), "execution.matrix"))
    artifacts = {
        "configuration.json": canonical_json_bytes(context.registration),
        "evidence_inventory.json": canonical_json_bytes(context.inventory),
        "readiness_matrix.json": canonical_json_bytes(matrix),
        "report.json": canonical_json_bytes(report),
        "report.md": _render_markdown(report=report, matrix=matrix).encode("utf-8"),
    }
    manifest = {
        "artifacts": {
            name: _artifact_binding(payload)
            for name, payload in sorted(artifacts.items())
        },
        "authority": _authority(),
        "canonical_artifact_names": list(CANONICAL_ARTIFACT_NAMES),
        "configuration_sha256": sha256_bytes(artifacts["configuration.json"]),
        "registration_sha256": context.registration_sha256,
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "verdict": report["verdict"],
    }
    artifacts["artifact_manifest.json"] = canonical_json_bytes(manifest)
    validate_artifact_payloads(artifacts)
    return artifacts


def validate_artifact_payloads(
    artifacts: Mapping[str, bytes],
) -> dict[str, Any]:
    if set(artifacts) != set(CANONICAL_ARTIFACT_NAMES):
        raise ReadinessAuditBlocked(
            "invalid_evidence: canonical artifact inventory mismatch"
        )
    manifest = _strict_json_bytes(
        artifacts["artifact_manifest.json"], "artifact manifest"
    )
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise ReadinessAuditBlocked("invalid_evidence: manifest schema mismatch")
    if manifest.get("canonical_artifact_names") != list(CANONICAL_ARTIFACT_NAMES):
        raise ReadinessAuditBlocked(
            "invalid_evidence: canonical artifact name list mismatch"
        )
    if manifest.get("authority") != _authority():
        raise ReadinessAuditBlocked("invalid_evidence: manifest authority mismatch")
    expected_bindings = {
        name: _artifact_binding(artifacts[name])
        for name in sorted(artifacts)
        if name != "artifact_manifest.json"
    }
    if manifest.get("artifacts") != expected_bindings:
        raise ReadinessAuditBlocked("invalid_evidence: artifact hash closure mismatch")

    configuration = validate_registration(
        _strict_json_bytes(artifacts["configuration.json"], "configuration")
    )
    registration_sha256 = sha256_bytes(canonical_json_bytes(configuration))
    if (
        manifest.get("configuration_sha256")
        != sha256_bytes(artifacts["configuration.json"])
        or manifest.get("registration_sha256") != registration_sha256
    ):
        raise ReadinessAuditBlocked(
            "invalid_evidence: manifest configuration identity mismatch"
        )
    inventory = _strict_json_bytes(
        artifacts["evidence_inventory.json"], "evidence inventory"
    )
    matrix = _strict_json_bytes(artifacts["readiness_matrix.json"], "readiness matrix")
    report = _strict_json_bytes(artifacts["report.json"], "report")
    if (
        inventory.get("schema_version") != INVENTORY_SCHEMA_VERSION
        or matrix.get("schema_version") != MATRIX_SCHEMA_VERSION
        or report.get("schema_version") != REPORT_SCHEMA_VERSION
    ):
        raise ReadinessAuditBlocked("invalid_evidence: canonical schema mismatch")
    if any(
        value.get("registration_sha256") != registration_sha256
        for value in (inventory, matrix, report)
    ):
        raise ReadinessAuditBlocked(
            "invalid_evidence: canonical registration identity mismatch"
        )
    verdict = report.get("verdict")
    if (
        verdict not in VERDICT_ORDER
        or matrix.get("verdict") != verdict
        or manifest.get("verdict") != verdict
    ):
        raise ReadinessAuditBlocked("invalid_evidence: canonical verdict mismatch")
    expected_consideration = verdict == "ready_for_bounded_training_proposal"
    if report.get("bounded_training_proposal_consideration") is not expected_consideration:
        raise ReadinessAuditBlocked(
            "invalid_evidence: bounded proposal consideration mismatch"
        )
    if report.get("authority") != _authority():
        raise ReadinessAuditBlocked("invalid_evidence: report authority mismatch")
    try:
        markdown = artifacts["report.md"].decode("utf-8")
    except UnicodeError as exc:
        raise ReadinessAuditBlocked(
            "invalid_evidence: report Markdown is not UTF-8"
        ) from exc
    if not markdown.startswith("# Non-Combat Formal RL Readiness Audit\n"):
        raise ReadinessAuditBlocked(
            "invalid_evidence: report Markdown header mismatch"
        )
    return manifest


def validate_artifact_directory(output_dir: Path | str) -> dict[str, Any]:
    root = Path(output_dir)
    try:
        names = {path.name for path in root.iterdir() if path.is_file()}
        entries = {path.name for path in root.iterdir()}
    except OSError as exc:
        raise ReadinessAuditBlocked(
            f"invalid_evidence: cannot inspect artifact directory: {exc}"
        ) from exc
    if names != set(CANONICAL_ARTIFACT_NAMES) or entries != names:
        raise ReadinessAuditBlocked(
            "invalid_evidence: published artifact inventory mismatch"
        )
    return validate_artifact_payloads(
        {name: (root / name).read_bytes() for name in CANONICAL_ARTIFACT_NAMES}
    )


def publish_artifacts(
    output_dir: Path | str,
    artifacts: Mapping[str, bytes],
    *,
    replace: Callable[[str | os.PathLike[str], str | os.PathLike[str]], None] = os.replace,
) -> None:
    validate_artifact_payloads(artifacts)
    destination = Path(output_dir)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise ReadinessAuditBlocked(
            "invalid_evidence: audit output directory already exists"
        )
    destination.mkdir()
    order = sorted(name for name in artifacts if name != "artifact_manifest.json")
    order.append("artifact_manifest.json")
    temporary = {name: destination / f".{name}.tmp" for name in order}
    installed: list[str] = []
    try:
        for name in order:
            temporary[name].write_bytes(artifacts[name])
        for name in order:
            replace(temporary[name], destination / name)
            installed.append(name)
    except Exception:
        for name in installed:
            (destination / name).unlink(missing_ok=True)
        for path in temporary.values():
            path.unlink(missing_ok=True)
        destination.rmdir()
        raise
    finally:
        for path in temporary.values():
            path.unlink(missing_ok=True)
    validate_artifact_directory(destination)


def run_registered_audit(
    *, context: ValidatedReadinessContext, output_dir: Path | str
) -> dict[str, Any]:
    execution = execute_audit(context)
    artifacts = build_artifacts(context=context, execution=execution)
    publish_artifacts(output_dir, artifacts)
    return validate_artifact_directory(output_dir)


def recompute_artifact_directory(
    *, context: ValidatedReadinessContext, output_dir: Path | str
) -> dict[str, Any]:
    root = Path(output_dir)
    manifest = validate_artifact_directory(root)
    execution = execute_audit(context)
    expected = build_artifacts(context=context, execution=execution)
    for name in CANONICAL_ARTIFACT_NAMES:
        if (root / name).read_bytes() != expected[name]:
            raise ReadinessAuditBlocked(
                f"invalid_evidence: canonical recomputation mismatch: {name}"
            )
    return manifest


def _evidence_paths_from_args(args: argparse.Namespace) -> dict[str, Path | None]:
    return {
        evidence_id: getattr(args, evidence_id)
        for evidence_id in EVIDENCE_SCHEMAS
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    register = commands.add_parser("register", description="Freeze audit inputs.")
    register.add_argument("--implementation-commit", required=True)
    for evidence_id in EVIDENCE_SCHEMAS:
        option = "--" + evidence_id.replace("_", "-")
        register.add_argument(
            option,
            dest=evidence_id,
            type=Path,
            required=evidence_id not in OPTIONAL_EVIDENCE_IDS,
        )
    register.add_argument("--output", type=Path, required=True)
    run = commands.add_parser("run", description="Run the registered audit.")
    run.add_argument("--input", type=Path, required=True)
    run.add_argument("--output-dir", type=Path, required=True)
    validate = commands.add_parser(
        "validate", description="Strictly recompute a published audit."
    )
    validate.add_argument("--input", type=Path, required=True)
    validate.add_argument("--output-dir", type=Path, required=True)
    return parser


def _invalid_error(exc: Exception) -> dict[str, Any]:
    return {
        "authority": _authority(),
        "bounded_training_proposal_consideration": False,
        "error": str(exc),
        "verdict": "invalid_evidence",
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo_root = Path(__file__).resolve().parents[1]
    try:
        if args.command == "register":
            registration = build_registration(
                repo_root=repo_root,
                implementation_commit=args.implementation_commit,
                evidence_paths=_evidence_paths_from_args(args),
            )
            load_validated_context(registration, repo_root=repo_root)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            if args.output.exists():
                raise ReadinessAuditBlocked(
                    "invalid_evidence: registration output already exists"
                )
            args.output.write_bytes(canonical_json_bytes(registration))
            print(sha256_bytes(args.output.read_bytes()))
            return 0
        registration = load_registration(args.input)
        context = load_validated_context(registration, repo_root=repo_root)
        if args.command == "run":
            manifest = run_registered_audit(
                context=context, output_dir=args.output_dir
            )
        else:
            manifest = recompute_artifact_directory(
                context=context, output_dir=args.output_dir
            )
        print(json.dumps(manifest, indent=2, sort_keys=True))
        return 0
    except (OSError, KeyError, ReadinessAuditBlocked) as exc:
        print(json.dumps(_invalid_error(exc), indent=2, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
