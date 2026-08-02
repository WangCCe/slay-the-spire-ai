"""Build a source-bound, no-authority formal non-combat reward contract."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from numbers import Real
from pathlib import Path, PurePosixPath
from typing import Any

from analysis_scripts.noncombat_simulator_adapter import (
    canonical_json_bytes,
    sha256_bytes,
)


class RewardContractBlocked(ValueError):
    """Raised when the formal reward contract cannot be trusted."""


REGISTRATION_SCHEMA_VERSION = "noncombat-formal-reward-contract-input-v1"
CONTRACT_SCHEMA_VERSION = "noncombat-formal-rl-reward-contract-v1"
VERIFICATION_SCHEMA_VERSION = "noncombat-formal-reward-verification-v1"
MANIFEST_SCHEMA_VERSION = "noncombat-formal-reward-manifest-v1"
CONTRACT_ID = "noncombat-formal-reward-contract-v1"
VERDICT = "formal_reward_contract_ready"
SCRIPT_RELATIVE_PATH = "analysis_scripts/noncombat_formal_reward_contract.py"
MAX_FLOOR = 57
MAX_EPISODE_FLOOR_PROGRESS = 1.0

EXCLUSIONS = (
    "behavior_action_probability",
    "bottled_label",
    "current_policy_label",
    "deck_heuristics",
    "gold",
    "hp",
    "ope_estimates",
    "simpleagent_label",
    "teacher_agreement",
)

SOURCE_BINDINGS: dict[str, tuple[str, str | None]] = {
    "contract_spec": (
        "openspec/specs/noncombat-formal-reward-contract/spec.md",
        None,
    ),
    "contract_tests": (
        "tests/test_noncombat_formal_reward_contract.py",
        None,
    ),
    "decision_loop_spec": (
        "openspec/specs/noncombat-rl-decision-loop/spec.md",
        None,
    ),
    "ope_readiness_spec": (
        "openspec/specs/noncombat-ope-readiness/spec.md",
        None,
    ),
    "prior_readiness_manifest": (
        "reports/noncombat_formal_rl_readiness_audit_20260802/"
        "artifact_manifest.json",
        "noncombat-formal-rl-readiness-manifest-v1",
    ),
    "prior_readiness_report": (
        "reports/noncombat_formal_rl_readiness_audit_20260802/report.json",
        "noncombat-formal-rl-readiness-report-v1",
    ),
    "readiness_spec": (
        "openspec/specs/noncombat-formal-rl-readiness-audit/spec.md",
        None,
    ),
    "simulator_smoke_implementation": (
        "analysis_scripts/noncombat_simulator_training_smoke.py",
        None,
    ),
    "simulator_smoke_spec": (
        "openspec/specs/noncombat-simulator-training-smoke/spec.md",
        None,
    ),
    "simulator_smoke_tests": (
        "tests/test_noncombat_simulator_training_smoke.py",
        None,
    ),
}

CANONICAL_ARTIFACT_NAMES = (
    "artifact_manifest.json",
    "configuration.json",
    "contract.json",
    "report.md",
    "verification.json",
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


def _registered_contract() -> dict[str, Any]:
    return {
        "contract_id": CONTRACT_ID,
        "exclusions": list(EXCLUSIONS),
        "floor_progress": {
            "complete_episode_bound": [0.0, MAX_EPISODE_FLOOR_PROGRESS],
            "discount": 1.0,
            "formula": (
                "max(0,cap(successor_floor,0,57)-"
                "cap(source_floor,0,57))/57"
            ),
            "max_floor": MAX_FLOOR,
            "monotone_simulator_floor_required_for_episode_bound": True,
            "role": "potential_shaping",
            "scope": "simulator_training_only",
        },
        "optimization": {
            "maximum_episode_floor_progress": MAX_EPISODE_FLOOR_PROGRESS,
            "permitted_modes": [
                "lexicographic",
                "strict_primary_dominance",
            ],
            "production_mode_selected": False,
            "production_weight_selected": False,
            "strict_scalar_constraint": (
                "victory_weight > maximum_episode_floor_progress"
            ),
        },
        "primary_objective": {
            "direction": "maximize",
            "name": "terminal_victory",
            "outcome_field": "victory",
        },
        "smoke_reward_assessment": {
            "formal_compatible": False,
            "maximum_episode_floor_progress": MAX_EPISODE_FLOOR_PROGRESS,
            "reason": "strict dominance requires victory_bonus > 1.0",
            "replacement_weight_selected": False,
            "version": "simulator-floor-progress-victory-v1",
            "victory_bonus": 1.0,
        },
        "verification_requirements": [
            "formula_tests",
            "provenance_boundary_tests",
            "terminal_objective_tests",
        ],
    }


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RewardContractBlocked(f"invalid_evidence: {label} must be an object")
    return value


def _require_keys(
    value: Mapping[str, Any], expected: set[str], label: str
) -> None:
    actual = set(value)
    if actual != expected:
        raise RewardContractBlocked(
            f"invalid_evidence: {label} keys differ: "
            f"missing={sorted(expected - actual)}, extra={sorted(actual - expected)}"
        )


def _strict_json_bytes(payload: bytes, label: str) -> dict[str, Any]:
    def reject_duplicates(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise RewardContractBlocked(
                    f"invalid_evidence: {label} contains duplicate key {key!r}"
                )
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise RewardContractBlocked(
            f"invalid_evidence: {label} contains non-finite number {value}"
        )

    try:
        parsed = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=reject_duplicates,
            parse_constant=reject_constant,
        )
    except RewardContractBlocked:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RewardContractBlocked(
            f"invalid_evidence: {label} is invalid JSON: {exc}"
        ) from exc
    return dict(_mapping(parsed, label))


def _canonical_relative_path(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise RewardContractBlocked(f"invalid_evidence: {label} path is invalid")
    pure = PurePosixPath(value)
    if (
        pure.is_absolute()
        or "\\" in value
        or any(part in {"", ".", ".."} for part in pure.parts)
        or pure.as_posix() != value
    ):
        raise RewardContractBlocked(
            f"invalid_evidence: {label} path must be canonical repo-relative"
        )
    return value


def _validate_binding(
    value: object,
    label: str,
    *,
    expected_path: str,
    expected_schema: str | None,
) -> dict[str, Any]:
    binding = dict(_mapping(value, label))
    expected_keys = {"path", "sha256", "size_bytes"}
    if expected_schema is not None:
        expected_keys.add("expected_schema")
    _require_keys(binding, expected_keys, label)
    binding["path"] = _canonical_relative_path(binding["path"], label)
    if binding["path"] != expected_path:
        raise RewardContractBlocked(f"invalid_evidence: {label} path drifted")
    digest = binding.get("sha256")
    if not isinstance(digest, str) or not _SHA256_PATTERN.fullmatch(digest):
        raise RewardContractBlocked(f"invalid_evidence: {label} SHA-256 is invalid")
    size = binding.get("size_bytes")
    if type(size) is not int or size <= 0:
        raise RewardContractBlocked(f"invalid_evidence: {label} size is invalid")
    if expected_schema is not None and binding.get("expected_schema") != expected_schema:
        raise RewardContractBlocked(f"invalid_evidence: {label} schema drifted")
    return binding


def validate_registration(value: object) -> dict[str, Any]:
    registration = dict(_mapping(value, "registration"))
    _require_keys(
        registration,
        {"authority", "contract", "identity", "schema_version", "sources"},
        "registration",
    )
    if registration.get("schema_version") != REGISTRATION_SCHEMA_VERSION:
        raise RewardContractBlocked("invalid_evidence: registration schema mismatch")
    if registration.get("authority") != _authority():
        raise RewardContractBlocked("invalid_evidence: registration authority drifted")
    if registration.get("contract") != _registered_contract():
        raise RewardContractBlocked("invalid_evidence: reward contract drifted")

    identity = dict(_mapping(registration.get("identity"), "identity"))
    _require_keys(identity, {"implementation", "source_commit"}, "identity")
    commit = identity.get("source_commit")
    if not isinstance(commit, str) or not _COMMIT_PATTERN.fullmatch(commit):
        raise RewardContractBlocked("invalid_evidence: source commit is invalid")
    identity["implementation"] = _validate_binding(
        identity.get("implementation"),
        "identity.implementation",
        expected_path=SCRIPT_RELATIVE_PATH,
        expected_schema=None,
    )
    registration["identity"] = identity

    sources = dict(_mapping(registration.get("sources"), "sources"))
    if set(sources) != set(SOURCE_BINDINGS):
        raise RewardContractBlocked("invalid_evidence: source inventory drifted")
    for source_id, (path, schema) in SOURCE_BINDINGS.items():
        sources[source_id] = _validate_binding(
            sources[source_id],
            f"sources.{source_id}",
            expected_path=path,
            expected_schema=schema,
        )
    registration["sources"] = sources
    return registration


def load_registration(path: Path | str) -> dict[str, Any]:
    payload = Path(path).read_bytes()
    registration = validate_registration(_strict_json_bytes(payload, "registration"))
    if payload != canonical_json_bytes(registration):
        raise RewardContractBlocked(
            "invalid_evidence: registration bytes are not canonical"
        )
    return registration


def _resolved_repo_path(repo_root: Path, relative: str, label: str) -> Path:
    root = repo_root.resolve()
    path = root.joinpath(*PurePosixPath(relative).parts).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise RewardContractBlocked(
            f"invalid_evidence: {label} path escapes repository"
        ) from exc
    return path


def _binding_for_path(
    path: Path | str,
    *,
    repo_root: Path,
    expected_schema: str | None,
) -> dict[str, Any]:
    absolute = Path(path).resolve()
    try:
        relative = absolute.relative_to(repo_root.resolve()).as_posix()
    except ValueError as exc:
        raise RewardContractBlocked(
            f"invalid_evidence: source is outside repository: {absolute}"
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
            raise RewardContractBlocked(
                f"invalid_evidence: {relative} schema mismatch"
            )
        if payload != canonical_json_bytes(document):
            raise RewardContractBlocked(
                f"invalid_evidence: {relative} bytes are not canonical"
            )
        binding["expected_schema"] = expected_schema
    return binding


def build_registration(
    *, repo_root: Path | str, implementation_commit: str
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    sources = {
        source_id: _binding_for_path(
            root.joinpath(*PurePosixPath(path).parts),
            repo_root=root,
            expected_schema=schema,
        )
        for source_id, (path, schema) in SOURCE_BINDINGS.items()
    }
    registration = {
        "authority": _authority(),
        "contract": _registered_contract(),
        "identity": {
            "implementation": _binding_for_path(
                root.joinpath(*PurePosixPath(SCRIPT_RELATIVE_PATH).parts),
                repo_root=root,
                expected_schema=None,
            ),
            "source_commit": implementation_commit,
        },
        "schema_version": REGISTRATION_SCHEMA_VERSION,
        "sources": sources,
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
        raise RewardContractBlocked(
            "invalid_evidence: cannot read registered source commit"
        ) from exc
    return result.stdout


def _verify_binding_bytes(
    binding: Mapping[str, Any], *, repo_root: Path, label: str
) -> bytes:
    path = _resolved_repo_path(repo_root, str(binding["path"]), label)
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise RewardContractBlocked(
            f"invalid_evidence: cannot read {label}: {path}"
        ) from exc
    if len(payload) != binding["size_bytes"]:
        raise RewardContractBlocked(f"invalid_evidence: {label} size mismatch")
    if sha256_bytes(payload) != binding["sha256"]:
        raise RewardContractBlocked(f"invalid_evidence: {label} SHA-256 mismatch")
    return payload


def _require_all_false_authorities(value: object, label: str) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            child_label = f"{label}.{key}"
            if key == "authority":
                authority = _mapping(item, child_label)
                if not authority:
                    raise RewardContractBlocked(
                        f"invalid_evidence: {child_label} is empty"
                    )
                for name, enabled in authority.items():
                    if type(enabled) is not bool or enabled:
                        raise RewardContractBlocked(
                            "invalid_evidence: authority must remain false: "
                            f"{child_label}.{name}"
                        )
            _require_all_false_authorities(item, child_label)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _require_all_false_authorities(item, f"{label}[{index}]")


@dataclass(frozen=True)
class ValidatedRewardContext:
    registration: dict[str, Any]
    registration_sha256: str
    source_inventory: dict[str, Any]


def _validate_prior_readiness(
    *, report: Mapping[str, Any], manifest: Mapping[str, Any], report_digest: str
) -> None:
    if report.get("verdict") != "not_ready_for_bounded_training_proposal":
        raise RewardContractBlocked(
            "invalid_evidence: prior readiness verdict differs"
        )
    if report.get("failed_domains") != [
        "reward",
        "baseline_policy",
        "outcome_support",
    ]:
        raise RewardContractBlocked(
            "invalid_evidence: prior readiness failed domains differ"
        )
    if report.get("next_prerequisites") != [
        "add_noncombat_formal_reward_contract",
        "establish_non_teacher_credible_baseline_floor",
        "expand_source_comparable_target_supported_outcomes",
    ]:
        raise RewardContractBlocked(
            "invalid_evidence: prior readiness prerequisites differ"
        )
    artifacts = _mapping(manifest.get("artifacts"), "prior manifest artifacts")
    report_binding = _mapping(
        artifacts.get("report.json"), "prior manifest report binding"
    )
    if report_binding.get("sha256") != report_digest:
        raise RewardContractBlocked(
            "invalid_evidence: prior report manifest link mismatch"
        )
    if manifest.get("registration_sha256") != report.get("registration_sha256"):
        raise RewardContractBlocked(
            "invalid_evidence: prior readiness registration link mismatch"
        )
    _require_all_false_authorities(report, "prior readiness report")
    _require_all_false_authorities(manifest, "prior readiness manifest")


def load_validated_context(
    registration: Mapping[str, Any], *, repo_root: Path | str
) -> ValidatedRewardContext:
    value = validate_registration(registration)
    root = Path(repo_root).resolve()
    commit = value["identity"]["source_commit"]
    all_bindings = {
        "implementation": value["identity"]["implementation"],
        **value["sources"],
    }
    inventory: dict[str, Any] = {}
    documents: dict[str, dict[str, Any]] = {}
    for source_id, binding in all_bindings.items():
        payload = _verify_binding_bytes(
            binding, repo_root=root, label=f"registered {source_id}"
        )
        committed = _git_blob_bytes(root, commit, binding["path"])
        if committed != payload:
            raise RewardContractBlocked(
                f"invalid_evidence: {source_id} bytes differ from registered commit"
            )
        inventory[source_id] = {
            "path": binding["path"],
            "sha256": binding["sha256"],
            "size_bytes": binding["size_bytes"],
            "status": "validated",
        }
        schema = binding.get("expected_schema")
        if schema is not None:
            document = _strict_json_bytes(payload, f"registered {source_id}")
            if document.get("schema_version") != schema:
                raise RewardContractBlocked(
                    f"invalid_evidence: {source_id} schema mismatch"
                )
            if payload != canonical_json_bytes(document):
                raise RewardContractBlocked(
                    f"invalid_evidence: {source_id} is not canonical"
                )
            documents[source_id] = document

    _validate_prior_readiness(
        report=documents["prior_readiness_report"],
        manifest=documents["prior_readiness_manifest"],
        report_digest=value["sources"]["prior_readiness_report"]["sha256"],
    )
    _require_all_false_authorities(value, "registration")
    registration_sha256 = sha256_bytes(canonical_json_bytes(value))
    return ValidatedRewardContext(
        registration=value,
        registration_sha256=registration_sha256,
        source_inventory=inventory,
    )


def _finite_number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise RewardContractBlocked(f"invalid_transition: {label} must be finite")
    result = float(value)
    if not math.isfinite(result):
        raise RewardContractBlocked(f"invalid_transition: {label} must be finite")
    return result


def floor_progress(source_floor: object, successor_floor: object) -> float:
    """Return bounded non-negative simulator floor advancement."""
    before = min(max(_finite_number(source_floor, "source floor"), 0.0), 57.0)
    after = min(max(_finite_number(successor_floor, "successor floor"), 0.0), 57.0)
    return max(0.0, after - before) / 57.0


def terminal_victory(terminal: object, outcome: object) -> int:
    """Return one only for an explicit terminal player victory."""
    if type(terminal) is not bool:
        raise RewardContractBlocked("invalid_transition: terminal must be boolean")
    if outcome is not None and not isinstance(outcome, str):
        raise RewardContractBlocked(
            "invalid_transition: outcome must be a string or null"
        )
    return int(terminal and outcome == "player_victory")


def reward_channels(transition: object) -> dict[str, float | int]:
    """Compute only the two formal channels from one simulator transition."""
    value = _mapping(transition, "transition")
    source = _mapping(value.get("source_state"), "transition.source_state")
    successor = _mapping(value.get("successor"), "transition.successor")
    successor_state = _mapping(
        successor.get("state"), "transition.successor.state"
    )
    return {
        "floor_progress": floor_progress(
            source.get("floor"), successor_state.get("floor")
        ),
        "terminal_victory": terminal_victory(
            successor.get("terminal"), successor_state.get("outcome")
        ),
    }


def validate_scalarization(
    mode: str, *, victory_weight: object | None = None
) -> dict[str, Any]:
    """Validate a future proposal's optimization relationship."""
    if mode == "lexicographic":
        if victory_weight is not None:
            raise RewardContractBlocked(
                "invalid_scalarization: lexicographic mode has no scalar weight"
            )
        return {
            "mode": mode,
            "priority": ["terminal_victory", "floor_progress"],
            "production_weight_selected": False,
        }
    if mode == "strict_primary_dominance":
        weight = _finite_number(victory_weight, "victory weight")
        if weight <= MAX_EPISODE_FLOOR_PROGRESS:
            raise RewardContractBlocked(
                "invalid_scalarization: victory weight must be strictly greater "
                "than maximum episode floor progress"
            )
        return {
            "maximum_episode_floor_progress": MAX_EPISODE_FLOOR_PROGRESS,
            "mode": mode,
            "strict_dominance_proved": True,
            "victory_weight": weight,
        }
    raise RewardContractBlocked(f"invalid_scalarization: unsupported mode {mode!r}")


def _build_contract(registration_sha256: str) -> dict[str, Any]:
    registered = _registered_contract()
    return {
        "authority": _authority(),
        "contract_id": CONTRACT_ID,
        "exclusions": registered["exclusions"],
        "optimization": registered["optimization"],
        "primary_objective": registered["primary_objective"],
        "provenance": {
            "live_and_ope": {
                "floor_reached_role": "diagnostic",
                "primary_outcome": "victory",
                "simulator_reward_attribution": False,
            },
            "simulator": {
                "floor_progress_role": "potential_shaping",
                "scope": "simulator_training_only",
            },
            "simulator_live_separated": True,
        },
        "reference_labels_excluded": True,
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "secondary_channels": [
            {
                "bounds": [0.0, MAX_EPISODE_FLOOR_PROGRESS],
                "discount": 1.0,
                "formula": registered["floor_progress"]["formula"],
                "max_floor": MAX_FLOOR,
                "name": "floor_progress",
                "outcome_field": "floor_reached",
                "role": "potential_shaping",
                "scope": "simulator_training_only",
            }
        ],
        "smoke_reward_assessment": registered["smoke_reward_assessment"],
        "source_registration_sha256": registration_sha256,
        "verification": {
            "formula_tests": True,
            "provenance_boundary_tests": True,
            "terminal_objective_tests": True,
        },
        "verdict": VERDICT,
    }


def _fixed_transitions() -> list[dict[str, Any]]:
    return [
        {
            "expected": {"floor_progress": 1.0 / 57.0, "terminal_victory": 0},
            "id": "one_floor_advance",
            "transition": {
                "source_state": {"floor": 0},
                "successor": {
                    "state": {"floor": 1, "outcome": None},
                    "terminal": False,
                },
            },
        },
        {
            "expected": {"floor_progress": 0.0, "terminal_victory": 0},
            "id": "floor_regression",
            "transition": {
                "source_state": {"floor": 20},
                "successor": {
                    "state": {"floor": 19, "outcome": None},
                    "terminal": False,
                },
            },
        },
        {
            "expected": {"floor_progress": 1.0 / 57.0, "terminal_victory": 1},
            "id": "capped_terminal_victory",
            "transition": {
                "source_state": {"floor": 56},
                "successor": {
                    "state": {"floor": 99, "outcome": "player_victory"},
                    "terminal": True,
                },
            },
        },
        {
            "expected": {"floor_progress": 0.0, "terminal_victory": 0},
            "id": "nonterminal_victory_looking_outcome",
            "transition": {
                "source_state": {"floor": 57},
                "successor": {
                    "state": {"floor": 57, "outcome": "player_victory"},
                    "terminal": False,
                },
            },
        },
    ]


def _fixed_verification(registration_sha256: str) -> dict[str, Any]:
    examples: list[dict[str, Any]] = []
    for example in _fixed_transitions():
        observed = reward_channels(example["transition"])
        expected = example["expected"]
        passed = (
            observed["terminal_victory"] == expected["terminal_victory"]
            and math.isclose(
                float(observed["floor_progress"]),
                float(expected["floor_progress"]),
                rel_tol=0.0,
                abs_tol=1e-15,
            )
        )
        examples.append(
            {
                "expected": expected,
                "id": example["id"],
                "observed": observed,
                "passed": passed,
            }
        )

    monotone_floors = [0, 1, 10, 56, 57, 99]
    episode_progress = sum(
        floor_progress(before, after)
        for before, after in zip(monotone_floors, monotone_floors[1:])
    )
    base = {
        "source_state": {"floor": 12},
        "successor": {
            "state": {"floor": 13, "outcome": None},
            "terminal": False,
        },
    }
    noisy = {
        **base,
        "behavior_action_probability": 0.99,
        "bottled_label": "changed",
        "current_policy_label": "changed",
        "deck_heuristics": {"score": 999},
        "gold": 999,
        "hp": 1,
        "ope_estimates": {"value": 999},
        "simpleagent_label": "changed",
        "teacher_agreement": True,
    }
    strict_scalar = validate_scalarization(
        "strict_primary_dominance", victory_weight=1.000001
    )
    equality_rejected = False
    try:
        validate_scalarization("strict_primary_dominance", victory_weight=1.0)
    except RewardContractBlocked:
        equality_rejected = True

    contract = _build_contract(registration_sha256)
    checks = {
        "authority_tests": not any(contract["authority"].values()),
        "bounds_tests": math.isclose(
            episode_progress,
            MAX_EPISODE_FLOOR_PROGRESS,
            rel_tol=0.0,
            abs_tol=1e-15,
        ),
        "excluded_field_invariance_tests": reward_channels(base)
        == reward_channels(noisy),
        "formula_tests": all(example["passed"] for example in examples),
        "provenance_boundary_tests": (
            contract["provenance"]["simulator_live_separated"] is True
            and contract["provenance"]["live_and_ope"]["floor_reached_role"]
            == "diagnostic"
            and contract["secondary_channels"][0]["scope"]
            == "simulator_training_only"
        ),
        "reference_exclusion_tests": set(EXCLUSIONS)
        == set(contract["exclusions"]),
        "scalarization_tests": (
            validate_scalarization("lexicographic")["priority"]
            == ["terminal_victory", "floor_progress"]
            and strict_scalar["strict_dominance_proved"] is True
            and equality_rejected
            and contract["smoke_reward_assessment"]["formal_compatible"]
            is False
            and contract["optimization"]["production_weight_selected"] is False
        ),
        "terminal_objective_tests": (
            terminal_victory(True, "player_victory") == 1
            and terminal_victory(False, "player_victory") == 0
            and terminal_victory(True, "player_loss") == 0
        ),
    }
    if not all(checks.values()):
        failed = [name for name, passed in checks.items() if not passed]
        raise RewardContractBlocked(
            f"invalid_evidence: fixed verification failed: {failed}"
        )
    return {
        "authority": _authority(),
        "checks": checks,
        "fixed_examples": examples,
        "monotone_episode_floor_progress": episode_progress,
        "registration_sha256": registration_sha256,
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "verdict": VERDICT,
    }


def _render_markdown(
    *, contract: Mapping[str, Any], verification: Mapping[str, Any]
) -> str:
    lines = [
        "# Non-Combat Formal Reward Contract",
        "",
        f"- Verdict: `{contract['verdict']}`",
        f"- Contract: `{contract['contract_id']}`",
        f"- Registration SHA-256: `{contract['source_registration_sha256']}`",
        "- Training, gameplay, evaluation, loading, and promotion authority: `false`",
        "",
        "## Ordered Channels",
        "",
        (
            "1. `terminal_victory`: primary objective; one only for an explicit "
            "terminal player victory."
        ),
        (
            "2. `floor_progress`: simulator-only potential shaping; bounded to "
            "`[0, 1]` over a valid monotone episode."
        ),
        "",
        "## Optimization Boundary",
        "",
        (
            "A future proposal must use victory-first lexicographic optimization "
            "or prove a scalar victory weight strictly greater than `1.0`. The "
            "smoke's `victory_bonus=1.0` is not automatically formal-compatible, "
            "and this contract selects no production weight."
        ),
        "",
        "## Provenance Boundary",
        "",
        (
            "Live and OPE evidence keeps victory primary and floor reached "
            "diagnostic. Simulator floor shaping is not attributed to live "
            "trajectories. Current, Bottled, SimpleAgent, teacher agreement, HP, "
            "gold, deck heuristics, behavior probabilities, and OPE estimates are "
            "excluded from reward."
        ),
        "",
        "## Verification",
        "",
    ]
    lines.extend(
        f"- `{check_id}`: `{str(passed).lower()}`"
        for check_id, passed in sorted(verification["checks"].items())
    )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            (
                "This artifact closes only the formal reward-definition "
                "prerequisite. It does not authorize training and does not resolve "
                "baseline-policy or target-supported-outcome evidence."
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def _artifact_binding(payload: bytes) -> dict[str, Any]:
    return {"sha256": sha256_bytes(payload), "size_bytes": len(payload)}


def build_artifacts(context: ValidatedRewardContext) -> dict[str, bytes]:
    contract = _build_contract(context.registration_sha256)
    verification = _fixed_verification(context.registration_sha256)
    artifacts = {
        "configuration.json": canonical_json_bytes(context.registration),
        "contract.json": canonical_json_bytes(contract),
        "report.md": _render_markdown(
            contract=contract, verification=verification
        ).encode("utf-8"),
        "verification.json": canonical_json_bytes(verification),
    }
    manifest = {
        "artifacts": {
            name: _artifact_binding(payload)
            for name, payload in sorted(artifacts.items())
        },
        "authority": _authority(),
        "canonical_artifact_names": list(CANONICAL_ARTIFACT_NAMES),
        "configuration_sha256": sha256_bytes(artifacts["configuration.json"]),
        "contract_sha256": sha256_bytes(artifacts["contract.json"]),
        "registration_sha256": context.registration_sha256,
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "verdict": VERDICT,
    }
    artifacts["artifact_manifest.json"] = canonical_json_bytes(manifest)
    validate_artifact_payloads(artifacts)
    return artifacts


def validate_artifact_payloads(artifacts: Mapping[str, bytes]) -> dict[str, Any]:
    if set(artifacts) != set(CANONICAL_ARTIFACT_NAMES):
        raise RewardContractBlocked(
            "invalid_evidence: canonical artifact inventory mismatch"
        )
    manifest = _strict_json_bytes(
        artifacts["artifact_manifest.json"], "artifact manifest"
    )
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise RewardContractBlocked("invalid_evidence: manifest schema mismatch")
    if manifest.get("canonical_artifact_names") != list(CANONICAL_ARTIFACT_NAMES):
        raise RewardContractBlocked(
            "invalid_evidence: canonical artifact names differ"
        )
    if manifest.get("authority") != _authority():
        raise RewardContractBlocked("invalid_evidence: manifest authority drifted")
    expected_bindings = {
        name: _artifact_binding(artifacts[name])
        for name in sorted(artifacts)
        if name != "artifact_manifest.json"
    }
    if manifest.get("artifacts") != expected_bindings:
        raise RewardContractBlocked("invalid_evidence: artifact hash closure mismatch")

    registration = validate_registration(
        _strict_json_bytes(artifacts["configuration.json"], "configuration")
    )
    if artifacts["configuration.json"] != canonical_json_bytes(registration):
        raise RewardContractBlocked(
            "invalid_evidence: configuration bytes are not canonical"
        )
    registration_sha256 = sha256_bytes(canonical_json_bytes(registration))
    if (
        manifest.get("configuration_sha256")
        != sha256_bytes(artifacts["configuration.json"])
        or manifest.get("registration_sha256") != registration_sha256
    ):
        raise RewardContractBlocked(
            "invalid_evidence: manifest registration identity mismatch"
        )

    contract = _strict_json_bytes(artifacts["contract.json"], "contract")
    expected_contract = _build_contract(registration_sha256)
    if contract != expected_contract or artifacts["contract.json"] != canonical_json_bytes(
        contract
    ):
        raise RewardContractBlocked("invalid_evidence: formal contract drifted")
    if manifest.get("contract_sha256") != sha256_bytes(artifacts["contract.json"]):
        raise RewardContractBlocked(
            "invalid_evidence: manifest contract identity mismatch"
        )

    verification = _strict_json_bytes(
        artifacts["verification.json"], "verification"
    )
    expected_verification = _fixed_verification(registration_sha256)
    if verification != expected_verification or artifacts[
        "verification.json"
    ] != canonical_json_bytes(verification):
        raise RewardContractBlocked("invalid_evidence: verification drifted")
    expected_markdown = _render_markdown(
        contract=contract, verification=verification
    ).encode("utf-8")
    if artifacts["report.md"] != expected_markdown:
        raise RewardContractBlocked("invalid_evidence: report Markdown drifted")
    _require_all_false_authorities(contract, "contract")
    _require_all_false_authorities(verification, "verification")
    return manifest


def validate_artifact_directory(output_dir: Path | str) -> dict[str, Any]:
    root = Path(output_dir)
    try:
        entries = list(root.iterdir())
    except OSError as exc:
        raise RewardContractBlocked(
            f"invalid_evidence: cannot inspect artifact directory: {exc}"
        ) from exc
    names = {path.name for path in entries if path.is_file()}
    if names != set(CANONICAL_ARTIFACT_NAMES) or len(entries) != len(names):
        raise RewardContractBlocked(
            "invalid_evidence: published artifact inventory mismatch"
        )
    return validate_artifact_payloads(
        {name: (root / name).read_bytes() for name in CANONICAL_ARTIFACT_NAMES}
    )


def publish_artifacts(
    output_dir: Path | str,
    artifacts: Mapping[str, bytes],
    *,
    replace: Callable[
        [str | os.PathLike[str], str | os.PathLike[str]], None
    ] = os.replace,
) -> None:
    validate_artifact_payloads(artifacts)
    destination = Path(output_dir)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise RewardContractBlocked(
            "invalid_evidence: contract output directory already exists"
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


def run_registered_contract(
    *, context: ValidatedRewardContext, output_dir: Path | str
) -> dict[str, Any]:
    artifacts = build_artifacts(context)
    publish_artifacts(output_dir, artifacts)
    return validate_artifact_directory(output_dir)


def recompute_artifact_directory(
    *, context: ValidatedRewardContext, output_dir: Path | str
) -> dict[str, Any]:
    root = Path(output_dir)
    manifest = validate_artifact_directory(root)
    expected = build_artifacts(context)
    for name in CANONICAL_ARTIFACT_NAMES:
        if (root / name).read_bytes() != expected[name]:
            raise RewardContractBlocked(
                f"invalid_evidence: canonical recomputation mismatch: {name}"
            )
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    register = commands.add_parser("register", description="Freeze contract inputs.")
    register.add_argument("--implementation-commit", required=True)
    register.add_argument("--output", type=Path, required=True)
    run = commands.add_parser("run", description="Publish the registered contract.")
    run.add_argument("--input", type=Path, required=True)
    run.add_argument("--output-dir", type=Path, required=True)
    validate = commands.add_parser(
        "validate", description="Strictly recompute a published contract."
    )
    validate.add_argument("--input", type=Path, required=True)
    validate.add_argument("--output-dir", type=Path, required=True)
    return parser


def _invalid_error(exc: Exception) -> dict[str, Any]:
    return {
        "authority": _authority(),
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
            )
            load_validated_context(registration, repo_root=repo_root)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            if args.output.exists():
                raise RewardContractBlocked(
                    "invalid_evidence: registration output already exists"
                )
            args.output.write_bytes(canonical_json_bytes(registration))
            print(sha256_bytes(args.output.read_bytes()))
            return 0
        registration = load_registration(args.input)
        context = load_validated_context(registration, repo_root=repo_root)
        if args.command == "run":
            manifest = run_registered_contract(
                context=context, output_dir=args.output_dir
            )
        else:
            manifest = recompute_artifact_directory(
                context=context, output_dir=args.output_dir
            )
        print(json.dumps(manifest, indent=2, sort_keys=True))
        return 0
    except (KeyError, OSError, RewardContractBlocked) as exc:
        print(json.dumps(_invalid_error(exc), indent=2, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
