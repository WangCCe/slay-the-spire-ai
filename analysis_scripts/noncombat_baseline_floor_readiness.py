from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping


INPUT_SCHEMA_VERSION = "noncombat-baseline-floor-readiness-audit-input-v1"
REPORT_SCHEMA_VERSION = "noncombat-baseline-floor-readiness-audit-report-v1"

NO_AUTHORITY = {
    "formal_rl_authorized": False,
    "fresh_evidence_authorized": False,
    "gameplay_authorized": False,
    "model_fitting_authorized": False,
    "native_loading_authorized": False,
    "ope_authorized": False,
    "policy_loading_authorized": False,
    "promotion_authorized": False,
    "qualification_authorized": False,
    "reward_authorized": False,
    "seed_selection_authorized": False,
    "simulator_environment_authorized": False,
    "training_authorized": False,
}

CANDIDATE_ROLES = (
    {
        "eligible": True,
        "policy_id": "current",
        "role": "eligible_non_teacher",
        "status": "structural_closure_required",
    },
    {
        "eligible": False,
        "policy_id": "native_simple_agent",
        "role": "auxiliary_deterministic_control",
        "status": "teacher_quality_gate_rejected",
    },
    {
        "eligible": False,
        "policy_id": "bottled",
        "role": "auxiliary_oracle",
        "status": "reference_only",
    },
    {
        "eligible": False,
        "policy_id": "seeded_initial",
        "role": "weak_control",
        "status": "not_credible_baseline_floor",
    },
    {
        "eligible": False,
        "policy_id": "smoke_trained",
        "role": "negative_policy_evidence",
        "status": "baseline_signal_not_demonstrated",
    },
    {
        "eligible": False,
        "policy_id": "simpleagent_warm_start",
        "role": "negative_policy_evidence",
        "status": "baseline_floor_not_demonstrated",
    },
    {
        "eligible": False,
        "policy_id": "structured_ranker",
        "role": "negative_policy_evidence",
        "status": "candidate_not_selected",
    },
    {
        "eligible": False,
        "policy_id": "route_card_residual",
        "role": "negative_policy_evidence",
        "status": "candidate_not_selected",
    },
)

UNSUPPORTED_EPISODE_CONTRACT = {
    "aggregate_metrics_include_unsupported": True,
    "denominator": "all_selected_episodes",
    "drop_allowed": False,
    "exact_reason_seed_rate_reporting": True,
    "paired_metrics_include_unsupported": True,
    "primary_disposition": "non_victory_last_supported_floor",
    "replacement_allowed": False,
    "retry_allowed": False,
    "supported_only_can_authorize": False,
    "unsupported_rate_ceiling_required": True,
}

BASELINE_FLOOR_CONTRACT_CHECKS = (
    "comparison_controls_fixed",
    "absolute_quality_gate_fixed",
    "paired_quality_gate_fixed",
    "unsupported_rate_ceiling_fixed",
    "replay_contract_fixed",
    "bootstrap_contract_fixed",
    "stop_rules_fixed",
    "untouched_holdout_fixed",
)

_REQUIRED_EVIDENCE_IDS = (
    "current_bridge",
    "formal_readiness",
    "formal_reward",
    "outcome_feasibility",
    "policy_validity",
    "reachable_compatibility",
    "reachable_event_repair",
    "remove_sentinel_repair",
    "residual_ranker",
    "shop_support_envelope",
    "sold_inventory_repair",
    "structured_ranker",
    "teacher_suitability",
    "total_compatibility",
    "warm_start",
)

_EXPECTED_JSON_FACTS = {
    "formal_readiness": (
        (("schema_version",), "noncombat-formal-rl-readiness-report-v1"),
        (("verdict",), "not_ready_for_bounded_training_proposal"),
        (("failed_domains",), ["baseline_policy", "outcome_support"]),
    ),
    "policy_validity": (
        (("schema_version",), "noncombat-simulator-policy-validity-metrics-v1"),
        (("classification", "verdict"), "study_valid_without_baseline_signal"),
        (("classification", "quality"), "baseline_signal_not_demonstrated"),
    ),
    "warm_start": (
        (("schema_version",), "noncombat-simulator-baseline-metrics-artifact-v1"),
        (("classification", "verdict"), "study_valid_without_baseline_floor"),
        (("classification", "quality"), "baseline_floor_not_demonstrated"),
        (("classification", "final_test_untouched"), True),
    ),
    "structured_ranker": (
        (("schema_version",), "noncombat-structured-baseline-ranker-metrics-v1"),
        (("classification", "verdict"), "poc_valid_without_structured_candidate"),
        (("classification", "selected_candidate_id"), None),
    ),
    "residual_ranker": (
        (("schema_version",), "noncombat-route-card-residual-metrics-v1"),
        (("classification", "verdict"), "poc_valid_without_route_card_residual"),
        (("classification", "selected_candidate_id"), None),
    ),
    "teacher_suitability": (
        (("schema_version",), "noncombat-teacher-suitability-v1"),
        (("policy_quality_gate_suitable",), False),
    ),
    "current_bridge": (
        (("schema_version",), "noncombat-current-policy-simulator-bridge-metrics-v2"),
        (("verdict",), "frozen_bridge_structurally_compatible"),
        (("stage1_passed",), True),
        (("passed_row_count",), 4),
        (("stage2", "executed"), True),
    ),
    "total_compatibility": (
        (("schema_version",), "noncombat-total-event-native-compatibility-metrics-v1"),
        (("verdict",), "total_event_native_compatibility_failed"),
        (("completed_seed_count",), 0),
    ),
    "reachable_compatibility": (
        (("schema_version",), "noncombat-reachable-event-native-compatibility-metrics-v1"),
        (("verdict",), "reachable_event_native_compatibility_failed"),
        (("completed_seed_rows",), 0),
    ),
    "formal_reward": (
        (("schema_version",), "noncombat-formal-rl-reward-contract-v1"),
        (("contract_id",), "noncombat-formal-reward-contract-v1"),
        (("verdict",), "formal_reward_contract_ready"),
        (("reference_labels_excluded",), True),
    ),
    "outcome_feasibility": (
        (("schema_version",), "noncombat-study-feasibility-v1"),
        (("result", "study_feasibility"), "not_demonstrated"),
        (("reference_evidence", "reference_comparability"), "historical_reference_only"),
        (("reference_evidence", "target_supported_victories"), 0),
    ),
}

_EXPECTED_TEXT_TOKENS = {
    "reachable_event_repair": (
        "`reachable_event_surface_closed`",
        "does not establish a new native compatibility result",
    ),
    "remove_sentinel_repair": (
        "`remove_cost == -1`",
        "`purge_available == false`",
    ),
    "sold_inventory_repair": (
        "`price == -1`",
        "does not authorize a third formal native cohort",
    ),
    "shop_support_envelope": (
        "`unsupported_shop_courier_restock_semantics`",
        "`training_authorized = false`",
    ),
}


class AuditInputError(RuntimeError):
    def __init__(self, message: str):
        super().__init__(f"invalid_evidence: {message}")


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise AuditInputError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_json(path: Path) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except AuditInputError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AuditInputError(f"cannot read JSON {path}: {exc}") from exc


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _resolve_bound_path(root: Path, relative: Any, label: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise AuditInputError(f"{label} path must be a non-empty POSIX path")
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise AuditInputError(f"{label} path escapes repository root") from exc
    if not candidate.is_file():
        raise AuditInputError(f"{label} path is missing: {relative}")
    return candidate


def _validate_binding(root: Path, binding: Mapping[str, Any], label: str) -> Path:
    path = _resolve_bound_path(root, binding.get("path"), label)
    payload = path.read_bytes()
    if binding.get("size_bytes") != len(payload):
        raise AuditInputError(f"{label} size mismatch")
    if binding.get("sha256") != _sha256(payload):
        raise AuditInputError(f"{label} SHA-256 mismatch")
    return path


def _path_value(payload: Any, path: tuple[str, ...], evidence_id: str) -> Any:
    value = payload
    for key in path:
        if not isinstance(value, dict) or key not in value:
            raise AuditInputError(
                f"{evidence_id} missing expected field {'.'.join(path)}"
            )
        value = value[key]
    return value


def _validate_false_authority(payload: Any, evidence_id: str) -> None:
    if not isinstance(payload, dict) or "authority" not in payload:
        return
    authority = payload["authority"]
    if not isinstance(authority, dict) or not authority:
        raise AuditInputError(f"{evidence_id} authority must be a non-empty object")
    if any(value is not False for value in authority.values()):
        raise AuditInputError(f"{evidence_id} authority must remain false")


def _validate_json_evidence(evidence_id: str, payload: Any) -> None:
    facts = _EXPECTED_JSON_FACTS[evidence_id]
    for path, expected in facts:
        actual = _path_value(payload, path, evidence_id)
        if actual != expected:
            raise AuditInputError(
                f"{evidence_id} expected {'.'.join(path)}={expected!r}, got {actual!r}"
            )
    _validate_false_authority(payload, evidence_id)


def _validate_top_level_contract(registration: Mapping[str, Any]) -> None:
    if registration.get("schema_version") != INPUT_SCHEMA_VERSION:
        raise AuditInputError("registration schema_version mismatch")
    if not isinstance(registration.get("audit_id"), str) or not registration["audit_id"]:
        raise AuditInputError("audit_id must be a non-empty string")
    if registration.get("candidate_roles") != list(CANDIDATE_ROLES):
        raise AuditInputError("candidate_roles do not match the fixed role contract")
    if registration.get("unsupported_episode_contract") != UNSUPPORTED_EPISODE_CONTRACT:
        raise AuditInputError(
            "unsupported_episode_contract does not match the conservative contract"
        )
    if registration.get("authority") != NO_AUTHORITY:
        raise AuditInputError("authority does not match the all-false contract")

    checks = registration.get("baseline_floor_contract")
    if not isinstance(checks, dict) or set(checks) != set(BASELINE_FLOOR_CONTRACT_CHECKS):
        raise AuditInputError("baseline_floor_contract check set or order mismatch")
    if any(type(value) is not bool for value in checks.values()):
        raise AuditInputError("baseline_floor_contract checks must be booleans")


def classify_verdict(
    eligible_candidate: bool,
    completed_current_rows: int,
    contract_checks: Mapping[str, bool],
) -> tuple[str, str]:
    if not eligible_candidate:
        return (
            "no_viable_baseline_candidate",
            "define_non_teacher_baseline_candidate",
        )
    if completed_current_rows <= 0:
        return (
            "diagnostic_smoke_required",
            "reused_development_seed_current_bridge_smoke",
        )
    if not all(contract_checks.values()):
        return (
            "baseline_floor_contract_required",
            "define_baseline_floor_evaluation_contract",
        )
    return (
        "ready_for_baseline_floor_preregistration",
        "separate_baseline_floor_preregistration",
    )


def analyze_registration(
    registration_path: Path | str,
    *,
    repo_root: Path | str,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    registration_file = Path(registration_path).resolve()
    try:
        registration_file.relative_to(root)
    except ValueError as exc:
        raise AuditInputError("registration path escapes repository root") from exc
    registration = _load_json(registration_file)
    if not isinstance(registration, dict):
        raise AuditInputError("registration must be a JSON object")
    _validate_top_level_contract(registration)

    implementation = registration.get("implementation")
    if not isinstance(implementation, dict):
        raise AuditInputError("implementation binding is missing")
    _validate_binding(root, implementation, "implementation")

    evidence_rows = registration.get("evidence")
    if not isinstance(evidence_rows, list):
        raise AuditInputError("evidence must be a list")
    evidence_ids = tuple(row.get("id") for row in evidence_rows if isinstance(row, dict))
    if evidence_ids != _REQUIRED_EVIDENCE_IDS:
        raise AuditInputError("evidence ids or order do not match the fixed inventory")

    evidence_payloads: dict[str, Any] = {}
    for row in evidence_rows:
        evidence_id = row["id"]
        path = _validate_binding(root, row, f"evidence {evidence_id}")
        if evidence_id in _EXPECTED_JSON_FACTS:
            payload = _load_json(path)
            _validate_json_evidence(evidence_id, payload)
            evidence_payloads[evidence_id] = payload
        else:
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                raise AuditInputError(
                    f"cannot read text evidence {evidence_id}: {exc}"
                ) from exc
            for token in _EXPECTED_TEXT_TOKENS[evidence_id]:
                if token not in text:
                    raise AuditInputError(
                        f"{evidence_id} missing expected token {token!r}"
                    )
            evidence_payloads[evidence_id] = text

    current_roles = registration["candidate_roles"]
    eligible_current = any(
        row["policy_id"] == "current" and row["eligible"] is True
        for row in current_roles
    )
    total_rows = evidence_payloads["total_compatibility"]["completed_seed_count"]
    reachable_rows = evidence_payloads["reachable_compatibility"][
        "completed_seed_rows"
    ]
    completed_current_rows = max(total_rows, reachable_rows)
    contract_checks = {
        check: registration["baseline_floor_contract"][check]
        for check in BASELINE_FLOOR_CONTRACT_CHECKS
    }
    verdict, next_prerequisite = classify_verdict(
        eligible_current,
        completed_current_rows,
        contract_checks,
    )

    blockers = []
    if not eligible_current:
        blockers.append("eligible_non_teacher_candidate_absent")
    elif completed_current_rows <= 0:
        blockers.append("current_own_trajectory_complete_row_absent")
    blockers.extend(
        f"baseline_floor_contract_missing:{check}"
        for check, passed in contract_checks.items()
        if not passed
    )

    registration_bytes = registration_file.read_bytes()
    return {
        "audit_id": registration["audit_id"],
        "authority": dict(NO_AUTHORITY),
        "baseline_floor_contract": {
            "checks": dict(contract_checks),
            "complete": all(contract_checks.values()),
        },
        "candidate_roles": list(CANDIDATE_ROLES),
        "evidence_identity": {
            "evidence": evidence_rows,
            "implementation": implementation,
            "registration": {
                "path": registration_file.relative_to(root).as_posix(),
                "sha256": _sha256(registration_bytes),
                "size_bytes": len(registration_bytes),
            },
        },
        "result": {
            "blockers": blockers,
            "next_prerequisite": next_prerequisite,
            "outcome_support_remains_blocked": True,
            "verdict": verdict,
        },
        "schema_version": REPORT_SCHEMA_VERSION,
        "structural_evidence": {
            "completed_current_seed_rows": completed_current_rows,
            "current_bridge_frozen_rows_passed": evidence_payloads["current_bridge"][
                "passed_row_count"
            ],
            "current_bridge_stage1_passed": evidence_payloads["current_bridge"][
                "stage1_passed"
            ],
            "reachable_compatibility_verdict": evidence_payloads[
                "reachable_compatibility"
            ]["verdict"],
            "repairs_are_post_failure_only": True,
            "total_compatibility_verdict": evidence_payloads[
                "total_compatibility"
            ]["verdict"],
        },
        "unsupported_episode_contract": dict(UNSUPPORTED_EPISODE_CONTRACT),
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    result = report["result"]
    lines = [
        "# Non-Combat Baseline-Floor Readiness Audit",
        "",
        f"**Verdict:** `{result['verdict']}`",
        "",
        "Planning only. This audit grants no native, cohort, gameplay, reward, "
        "OPE, formal-RL, training, loading, qualification, or promotion authority.",
        "",
        "## Candidate Roles",
        "",
        "| Policy | Role | Eligible | Status |",
        "| --- | --- | --- | --- |",
    ]
    for row in report["candidate_roles"]:
        lines.append(
            f"| `{row['policy_id']}` | `{row['role']}` | "
            f"`{str(row['eligible']).lower()}` | `{row['status']}` |"
        )
    lines.extend(
        [
            "",
            "## Structural Evidence",
            "",
            f"- Frozen Current bridge rows passed: "
            f"`{report['structural_evidence']['current_bridge_frozen_rows_passed']}`",
            f"- Completed Current own-trajectory rows: "
            f"`{report['structural_evidence']['completed_current_seed_rows']}`",
            "- Subsequent repairs close known code boundaries but do not "
            "reinterpret consumed failures.",
            "",
            "## Unsupported Episodes",
            "",
            "Every selected episode remains in the denominator. A declared support "
            "blocker counts as a non-victory at the last supported floor; it cannot "
            "be dropped, replaced, or retried. A future registration must fix an "
            "unsupported-rate ceiling.",
            "",
            "## Blockers",
            "",
        ]
    )
    lines.extend(f"- `{blocker}`" for blocker in result["blockers"])
    lines.extend(
        [
            "",
            "## Next Prerequisite",
            "",
            f"`{result['next_prerequisite']}`",
            "",
            "The independent target-supported-outcome blocker remains unchanged.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def run_audit(
    registration_path: Path | str,
    json_output: Path | str,
    markdown_output: Path | str,
    *,
    repo_root: Path | str,
    strict: bool = False,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    registration_file = Path(registration_path).resolve()
    json_path = Path(json_output).resolve()
    markdown_path = Path(markdown_output).resolve()
    report = analyze_registration(registration_file, repo_root=root)

    registration = _load_json(registration_file)
    input_paths = {registration_file}
    input_paths.add(_resolve_bound_path(root, registration["implementation"]["path"], "implementation"))
    for row in registration["evidence"]:
        input_paths.add(_resolve_bound_path(root, row["path"], f"evidence {row['id']}"))
    if json_path == markdown_path or json_path in input_paths or markdown_path in input_paths:
        raise AuditInputError("output path collides with input or another output")

    json_bytes = _canonical_bytes(report)
    markdown_bytes = render_markdown(report).encode("utf-8")
    if strict:
        if not json_path.is_file() or json_path.read_bytes() != json_bytes:
            raise AuditInputError("strict JSON output mismatch")
        if not markdown_path.is_file() or markdown_path.read_bytes() != markdown_bytes:
            raise AuditInputError("strict Markdown output mismatch")
        return report

    _write_atomic(json_path, json_bytes)
    _write_atomic(markdown_path, markdown_bytes)
    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit non-combat baseline-floor preregistration readiness."
    )
    parser.add_argument("--registration", required=True, type=Path)
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--output-markdown", required=True, type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--strict", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    report = run_audit(
        args.registration,
        args.output_json,
        args.output_markdown,
        repo_root=args.repo_root,
        strict=args.strict,
    )
    print(json.dumps(report["result"], ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
