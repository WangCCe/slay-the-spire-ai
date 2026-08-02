"""Audit fixed-budget non-combat outcome-study feasibility offline."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, localcontext
from fractions import Fraction
from pathlib import Path, PurePosixPath
from typing import Any


INPUT_SCHEMA_VERSION = "noncombat-study-feasibility-input-v1"
REPORT_SCHEMA_VERSION = "noncombat-study-feasibility-v1"
REGISTRATION_SCHEMA_VERSION = "noncombat-outcome-evidence-registration-v2"
READINESS_SCHEMA_VERSION = "noncombat-ope-readiness-v1"
DECIMAL_PRECISION = 80
BISECTION_ITERATIONS = 192
DISPLAY_PLACES = 12
TARGET_PASS_PROBABILITIES = (
    Decimal("0.50"),
    Decimal("0.80"),
    Decimal("0.90"),
)
REFERENCE_COMPARABILITY_VALUES = {
    "historical_reference_only",
    "source_comparable",
}
AUTHORITY_FIELDS = (
    "replacement_qualification_preparation",
    "communication_mod_publication",
    "study_start",
    "study_run_lock_creation",
    "gameplay_collection",
    "ope_policy_claim",
    "causal_claim",
    "reward_change",
    "formal_noncombat_rl_training",
    "live_policy_promotion",
)
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_MANIFEST_KEYS = {
    "minimum_pass_probability",
    "minimum_reference_trajectories",
    "readiness",
    "reference_comparability",
    "registration",
    "schema_version",
    "sensitivity_rates",
}
_BINDING_KEYS = {"path", "sha256", "size_bytes"}


class FeasibilityInputError(ValueError):
    """Raised when feasibility evidence cannot be interpreted exactly."""


class _DuplicateJsonKeyError(ValueError):
    def __init__(self, key: str) -> None:
        super().__init__(key)
        self.key = key


@dataclass(frozen=True)
class _BoundArtifact:
    label: str
    relative_path: str
    path: Path
    sha256: str
    size_bytes: int
    value: dict[str, Any]


@dataclass(frozen=True)
class _AuditInputs:
    repo_root: Path
    manifest_path: Path
    manifest_sha256: str
    manifest_size_bytes: int
    manifest: dict[str, Any]
    registration: _BoundArtifact
    readiness: _BoundArtifact
    minimum_reference_trajectories: int
    minimum_pass_probability: Decimal
    reference_comparability: str
    sensitivity_rates: tuple[Decimal, ...]


def binomial_tail_probability(
    attempts: int,
    required_successes: int,
    success_rate: Decimal,
) -> Decimal:
    """Return P[X >= required_successes] for X ~ Binomial(attempts, rate)."""

    _validate_study_contract(attempts, required_successes)
    rate = _validate_probability(success_rate, "success_rate")
    if rate == 0:
        return Decimal(0)
    if rate == 1:
        return Decimal(1)
    with localcontext() as context:
        context.prec = DECIMAL_PRECISION
        complement = Decimal(1) - rate
        lower_tail = sum(
            Decimal(math.comb(attempts, successes))
            * (rate**successes)
            * (complement ** (attempts - successes))
            for successes in range(required_successes)
        )
        result = Decimal(1) - lower_tail
        return max(Decimal(0), min(Decimal(1), result))


def required_success_rate(
    attempts: int,
    required_successes: int,
    target_pass_probability: Decimal,
) -> Decimal:
    """Find the success rate needed for a fixed binomial pass probability."""

    _validate_study_contract(attempts, required_successes)
    target = _validate_probability(
        target_pass_probability,
        "target_pass_probability",
    )
    if target == 0:
        return Decimal(0)
    if target == 1:
        return Decimal(1)
    low = Decimal(0)
    high = Decimal(1)
    with localcontext() as context:
        context.prec = DECIMAL_PRECISION
        for _ in range(BISECTION_ITERATIONS):
            midpoint = (low + high) / 2
            if binomial_tail_probability(
                attempts,
                required_successes,
                midpoint,
            ) < target:
                low = midpoint
            else:
                high = midpoint
        return (low + high) / 2


def analyze_manifest(
    manifest_path: Path | str,
    *,
    repo_root: Path | str = ".",
) -> dict[str, Any]:
    """Build a deterministic planning-only feasibility report."""

    inputs = _load_inputs(Path(manifest_path), Path(repo_root))
    return _build_report(inputs)


def run_feasibility_audit(
    manifest_path: Path | str,
    json_output: Path | str,
    markdown_output: Path | str,
    *,
    repo_root: Path | str = ".",
) -> dict[str, Any]:
    """Analyze and transactionally publish deterministic JSON and Markdown."""

    inputs = _load_inputs(Path(manifest_path), Path(repo_root))
    report = _build_report(inputs)
    json_path = Path(json_output).resolve()
    markdown_path = Path(markdown_output).resolve()
    input_paths = {
        inputs.manifest_path,
        inputs.registration.path,
        inputs.readiness.path,
    }
    if json_path == markdown_path:
        raise FeasibilityInputError("output paths must be distinct")
    for output in (json_path, markdown_path):
        if output in input_paths:
            raise FeasibilityInputError(f"output path collides with input: {output}")

    json_bytes = _canonical_json_bytes(report)
    markdown_bytes = _render_markdown(report).encode("ascii")
    if _strict_json_loads(json_bytes.decode("ascii")) != report:
        raise FeasibilityInputError("rendered JSON did not replay exactly")
    if not markdown_bytes.endswith(b"\n"):
        raise FeasibilityInputError("rendered Markdown must end with LF")
    _replace_files_transactionally(
        ((json_path, json_bytes), (markdown_path, markdown_bytes))
    )
    return report


def _load_inputs(manifest_path: Path, repo_root: Path) -> _AuditInputs:
    root = repo_root.resolve()
    manifest_absolute = manifest_path.resolve()
    try:
        manifest_absolute.relative_to(root)
    except ValueError as exc:
        raise FeasibilityInputError("manifest path must be inside repo root") from exc
    manifest, manifest_bytes = _load_canonical_mapping(
        manifest_absolute,
        "input manifest",
    )
    if set(manifest) != _MANIFEST_KEYS:
        raise FeasibilityInputError(
            "input manifest keys differ: "
            f"missing={sorted(_MANIFEST_KEYS - set(manifest))}, "
            f"extra={sorted(set(manifest) - _MANIFEST_KEYS)}"
        )
    if manifest.get("schema_version") != INPUT_SCHEMA_VERSION:
        raise FeasibilityInputError("input manifest schema mismatch")

    minimum_reference = _required_nonnegative_int(
        manifest.get("minimum_reference_trajectories"),
        "minimum_reference_trajectories",
    )
    if minimum_reference == 0:
        raise FeasibilityInputError("minimum_reference_trajectories must be positive")
    minimum_probability = _decimal_from_canonical_string(
        manifest.get("minimum_pass_probability"),
        "minimum_pass_probability",
    )
    if not Decimal(0) < minimum_probability <= Decimal(1):
        raise FeasibilityInputError("minimum_pass_probability must be in (0, 1]")
    comparability = manifest.get("reference_comparability")
    if comparability not in REFERENCE_COMPARABILITY_VALUES:
        raise FeasibilityInputError("reference_comparability is invalid")
    sensitivity = _load_sensitivity_rates(manifest.get("sensitivity_rates"))

    registration = _load_bound_artifact(
        root,
        manifest.get("registration"),
        "registration",
    )
    readiness = _load_bound_artifact(
        root,
        manifest.get("readiness"),
        "readiness",
    )
    if registration.path == readiness.path:
        raise FeasibilityInputError("registration and readiness paths must differ")
    return _AuditInputs(
        repo_root=root,
        manifest_path=manifest_absolute,
        manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
        manifest_size_bytes=len(manifest_bytes),
        manifest=manifest,
        registration=registration,
        readiness=readiness,
        minimum_reference_trajectories=minimum_reference,
        minimum_pass_probability=minimum_probability,
        reference_comparability=str(comparability),
        sensitivity_rates=sensitivity,
    )


def _load_bound_artifact(
    repo_root: Path,
    binding_value: Any,
    label: str,
) -> _BoundArtifact:
    if not isinstance(binding_value, Mapping) or set(binding_value) != _BINDING_KEYS:
        raise FeasibilityInputError(f"{label} binding keys differ")
    relative_path = binding_value.get("path")
    if not isinstance(relative_path, str) or not relative_path:
        raise FeasibilityInputError(f"{label} path is invalid")
    pure_path = PurePosixPath(relative_path)
    if (
        pure_path.is_absolute()
        or "\\" in relative_path
        or any(part in {"", ".", ".."} for part in pure_path.parts)
    ):
        raise FeasibilityInputError(f"{label} path must be canonical repo-relative")
    path = repo_root.joinpath(*pure_path.parts).resolve()
    try:
        path.relative_to(repo_root)
    except ValueError as exc:
        raise FeasibilityInputError(f"{label} path escapes repo root") from exc
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise FeasibilityInputError(f"cannot read {label}: {path}") from exc
    expected_size = _required_nonnegative_int(
        binding_value.get("size_bytes"),
        f"{label} size_bytes",
    )
    if len(payload) != expected_size:
        raise FeasibilityInputError(f"{label} size mismatch")
    expected_hash = binding_value.get("sha256")
    if not isinstance(expected_hash, str) or not _SHA256_PATTERN.fullmatch(
        expected_hash
    ):
        raise FeasibilityInputError(f"{label} SHA-256 is invalid")
    actual_hash = hashlib.sha256(payload).hexdigest()
    if actual_hash != expected_hash:
        raise FeasibilityInputError(f"{label} SHA-256 mismatch")
    value, replayed_payload = _load_canonical_mapping(path, label)
    if replayed_payload != payload:
        raise FeasibilityInputError(f"{label} changed while being read")
    return _BoundArtifact(
        label=label,
        relative_path=relative_path,
        path=path,
        sha256=actual_hash,
        size_bytes=len(payload),
        value=value,
    )


def _build_report(inputs: _AuditInputs) -> dict[str, Any]:
    registration = inputs.registration.value
    if registration.get("schema_version") != REGISTRATION_SCHEMA_VERSION:
        raise FeasibilityInputError("registration schema mismatch")
    study_id = _required_string(registration.get("study_id"), "study_id")
    attempts = _required_nonnegative_int(
        registration.get("scheduled_attempts"),
        "scheduled_attempts",
    )
    thresholds = registration.get("thresholds")
    if not isinstance(thresholds, Mapping):
        raise FeasibilityInputError("registration thresholds are missing")
    required_victories = _required_nonnegative_int(
        thresholds.get("minimum_supported_victories"),
        "minimum_supported_victories",
    )
    _validate_study_contract(attempts, required_victories)

    readiness = inputs.readiness.value
    if readiness.get("schema_version") != READINESS_SCHEMA_VERSION:
        raise FeasibilityInputError("readiness schema mismatch")
    trajectory_count, raw_victories, supported_victories = _derive_counts(readiness)
    observed_rate = Fraction(supported_victories, trajectory_count)
    observed_decimal = Decimal(observed_rate.numerator) / Decimal(
        observed_rate.denominator
    )
    plug_in_probability = binomial_tail_probability(
        attempts,
        required_victories,
        observed_decimal,
    )

    blockers: list[str] = []
    if inputs.reference_comparability != "source_comparable":
        blockers.append("reference_not_source_comparable")
    if trajectory_count < inputs.minimum_reference_trajectories:
        blockers.append("insufficient_reference_trajectories")
    if supported_victories == 0:
        blockers.append("no_target_supported_victory")
    if plug_in_probability < inputs.minimum_pass_probability:
        blockers.append("plug_in_pass_probability_below_minimum")

    target_policy = readiness.get("target_policy")
    if not isinstance(target_policy, Mapping):
        raise FeasibilityInputError("readiness target_policy is missing")
    target_commit = _required_string(
        target_policy.get("target_policy_commit"),
        "target_policy_commit",
    )
    if not _COMMIT_PATTERN.fullmatch(target_commit):
        raise FeasibilityInputError("target_policy_commit is invalid")
    target_id = _required_string(
        target_policy.get("target_policy_id"),
        "target_policy_id",
    )
    construction_mode = _required_string(
        target_policy.get("construction_mode"),
        "target construction_mode",
    )

    required_rates = [
        {
            "supported_victory_rate": _format_decimal(
                required_success_rate(attempts, required_victories, target)
            ),
            "target_pass_probability": _format_decimal(target),
        }
        for target in TARGET_PASS_PROBABILITIES
    ]
    sensitivity = [
        {
            "pass_probability": _format_decimal(
                binomial_tail_probability(attempts, required_victories, rate)
            ),
            "supported_victory_rate": _format_decimal(rate),
        }
        for rate in inputs.sensitivity_rates
    ]
    status = "not_demonstrated" if blockers else "demonstrated"
    return {
        "authority": {field: False for field in AUTHORITY_FIELDS},
        "limitations": [
            "Planning-only plug-in probabilities do not estimate uncertainty, causality, or future policy performance.",
            "Raw victories with zero deterministic-Current weight do not satisfy the registered supported-victory gate.",
            "A demonstrated result would require a separate reviewed amendment before any live preparation.",
        ],
        "operating_characteristics": {
            "plug_in_pass_probability": _format_decimal(plug_in_probability),
            "required_supported_victory_rates": required_rates,
            "sensitivity": sensitivity,
        },
        "planning_configuration": {
            "bisection_iterations": BISECTION_ITERATIONS,
            "decimal_precision": DECIMAL_PRECISION,
            "minimum_pass_probability": _format_decimal(
                inputs.minimum_pass_probability
            ),
            "minimum_reference_trajectories": (
                inputs.minimum_reference_trajectories
            ),
        },
        "reference_evidence": {
            "complete_trajectories": trajectory_count,
            "observed_supported_victory_rate": _count_rate_record(
                supported_victories,
                trajectory_count,
            ),
            "raw_victories": raw_victories,
            "reference_comparability": inputs.reference_comparability,
            "target_supported_victories": supported_victories,
        },
        "result": {
            "blockers": blockers,
            "separate_amendment_required": True,
            "study_feasibility": status,
        },
        "schema_version": REPORT_SCHEMA_VERSION,
        "source": {
            "manifest": {
                "path": inputs.manifest_path.relative_to(inputs.repo_root).as_posix(),
                "sha256": inputs.manifest_sha256,
                "size_bytes": inputs.manifest_size_bytes,
            },
            "readiness": {
                "construction_mode": construction_mode,
                "path": inputs.readiness.relative_path,
                "sha256": inputs.readiness.sha256,
                "size_bytes": inputs.readiness.size_bytes,
                "target_policy_commit": target_commit,
                "target_policy_id": target_id,
            },
            "registration": {
                "path": inputs.registration.relative_path,
                "registration_hash": registration.get("registration_hash"),
                "sha256": inputs.registration.sha256,
                "size_bytes": inputs.registration.size_bytes,
                "study_id": study_id,
            },
        },
        "study_contract": {
            "minimum_supported_victories": required_victories,
            "scheduled_attempts": attempts,
        },
    }


def _derive_counts(readiness: Mapping[str, Any]) -> tuple[int, int, int]:
    audit = readiness.get("trajectory_audit")
    diagnostics = readiness.get("diagnostics")
    if not isinstance(audit, Mapping) or not isinstance(diagnostics, Mapping):
        raise FeasibilityInputError("readiness trajectory accounting is missing")
    outcome_rows = audit.get("complete_trajectories")
    weight_rows = diagnostics.get("trajectory_weights")
    if not isinstance(outcome_rows, list) or not isinstance(weight_rows, list):
        raise FeasibilityInputError("readiness trajectory rows are missing")

    outcomes: dict[str, bool] = {}
    for row in outcome_rows:
        if not isinstance(row, Mapping):
            raise FeasibilityInputError("invalid complete trajectory row")
        group_id = _required_string(row.get("group_id"), "trajectory group_id")
        if group_id in outcomes:
            raise FeasibilityInputError(f"duplicate trajectory outcome: {group_id}")
        outcome = row.get("outcome")
        if not isinstance(outcome, Mapping) or type(outcome.get("victory")) is not bool:
            raise FeasibilityInputError(f"invalid terminal victory: {group_id}")
        outcomes[group_id] = bool(outcome["victory"])

    weights: dict[str, Fraction] = {}
    for row in weight_rows:
        if not isinstance(row, Mapping):
            raise FeasibilityInputError("invalid trajectory weight row")
        group_id = _required_string(row.get("group_id"), "weight group_id")
        if group_id in weights:
            raise FeasibilityInputError(f"duplicate trajectory weight: {group_id}")
        weights[group_id] = _fraction_from_record(
            row.get("weight"),
            f"weight:{group_id}",
        )
        if weights[group_id] < 0:
            raise FeasibilityInputError(f"negative trajectory weight: {group_id}")

    if set(outcomes) != set(weights):
        raise FeasibilityInputError(
            "trajectory outcome/weight keys differ: "
            f"missing_weights={sorted(set(outcomes) - set(weights))}, "
            f"missing_outcomes={sorted(set(weights) - set(outcomes))}"
        )
    expected_count = audit.get("complete_trajectory_count")
    diagnostic_count = diagnostics.get("trajectory_count")
    if type(expected_count) is not int or expected_count != len(outcomes):
        raise FeasibilityInputError("complete trajectory count mismatch")
    if type(diagnostic_count) is not int or diagnostic_count != len(weights):
        raise FeasibilityInputError("diagnostic trajectory count mismatch")
    if not outcomes:
        raise FeasibilityInputError("at least one complete trajectory is required")
    raw_victories = sum(outcomes.values())
    supported_victories = sum(
        outcomes[group_id] and weights[group_id].numerator > 0
        for group_id in outcomes
    )
    return len(outcomes), raw_victories, supported_victories


def _render_markdown(report: Mapping[str, Any]) -> str:
    evidence = report["reference_evidence"]
    contract = report["study_contract"]
    operating = report["operating_characteristics"]
    result = report["result"]
    blockers = result["blockers"]
    lines = [
        "# Non-Combat Study Feasibility Audit",
        "",
        f"**Result:** `{result['study_feasibility']}`",
        "",
        "Planning only. This audit grants no qualification, gameplay, study, OPE, training, or promotion authority.",
        "",
        "## Registered Study",
        "",
        f"- Scheduled attempts: {contract['scheduled_attempts']}",
        f"- Required target-supported victories: {contract['minimum_supported_victories']}",
        f"- Plug-in pass probability: {operating['plug_in_pass_probability']}",
        "",
        "## Reference Evidence",
        "",
        f"- Comparability: `{evidence['reference_comparability']}`",
        f"- Complete trajectories: {evidence['complete_trajectories']}",
        f"- Raw victories: {evidence['raw_victories']}",
        f"- Target-supported victories: {evidence['target_supported_victories']}",
        f"- Observed supported-victory rate: {evidence['observed_supported_victory_rate']['value']}",
        "",
        "## Required Rates",
        "",
        "| Target pass probability | Required supported-victory rate |",
        "| ---: | ---: |",
    ]
    lines.extend(
        f"| {row['target_pass_probability']} | {row['supported_victory_rate']} |"
        for row in operating["required_supported_victory_rates"]
    )
    lines.extend(["", "## Blockers", ""])
    lines.extend(f"- `{blocker}`" for blocker in blockers)
    if not blockers:
        lines.append("- None")
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {limitation}" for limitation in report["limitations"])
    return "\n".join(lines) + "\n"


def _load_canonical_mapping(
    path: Path,
    description: str,
) -> tuple[dict[str, Any], bytes]:
    try:
        payload = path.read_bytes()
        text = payload.decode("utf-8")
        value = _strict_json_loads(text)
    except _DuplicateJsonKeyError as exc:
        raise FeasibilityInputError(
            f"{path}: duplicate JSON key: {exc.key}"
        ) from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise FeasibilityInputError(f"{path}: malformed {description}") from exc
    if not isinstance(value, dict):
        raise FeasibilityInputError(f"{path}: {description} must be a JSON object")
    canonical_forms = {
        _canonical_json_bytes(value),
        _canonical_compact_json_bytes(value),
    }
    if payload not in canonical_forms:
        raise FeasibilityInputError(f"{path}: non-canonical {description}")
    return value, payload


def _strict_json_loads(text: str) -> Any:
    def reject_duplicates(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise _DuplicateJsonKeyError(str(key))
            result[key] = value
        return result

    def reject_constant(value: str) -> Any:
        raise FeasibilityInputError(f"non-finite JSON number: {value}")

    return json.loads(
        text,
        object_pairs_hook=reject_duplicates,
        parse_constant=reject_constant,
    )


def _canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("ascii")


def _canonical_compact_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("ascii")


def _load_sensitivity_rates(value: Any) -> tuple[Decimal, ...]:
    if not isinstance(value, list) or not value:
        raise FeasibilityInputError("sensitivity_rates must be a non-empty list")
    rates = tuple(
        _decimal_from_canonical_string(item, f"sensitivity_rates[{index}]")
        for index, item in enumerate(value)
    )
    if any(rate < 0 or rate > 1 for rate in rates):
        raise FeasibilityInputError("sensitivity rates must be in [0, 1]")
    if any(left >= right for left, right in zip(rates, rates[1:])):
        raise FeasibilityInputError("sensitivity rates must be strictly increasing")
    return rates


def _decimal_from_canonical_string(value: Any, field: str) -> Decimal:
    if not isinstance(value, str) or not value:
        raise FeasibilityInputError(f"{field} must be a decimal string")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise FeasibilityInputError(f"{field} is invalid") from exc
    if not parsed.is_finite() or format(parsed, "f") != value:
        raise FeasibilityInputError(f"{field} is not canonical")
    return parsed


def _validate_probability(value: Decimal, field: str) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise FeasibilityInputError(f"{field} must be a finite Decimal")
    if value < 0 or value > 1:
        raise FeasibilityInputError(f"{field} must be in [0, 1]")
    return value


def _validate_study_contract(attempts: int, required_successes: int) -> None:
    if type(attempts) is not int or attempts <= 0:
        raise FeasibilityInputError("attempts must be a positive integer")
    if (
        type(required_successes) is not int
        or required_successes <= 0
        or required_successes > attempts
    ):
        raise FeasibilityInputError(
            "required_successes must be in [1, attempts]"
        )


def _required_nonnegative_int(value: Any, field: str) -> int:
    if type(value) is not int or value < 0:
        raise FeasibilityInputError(f"{field} must be a non-negative integer")
    return value


def _required_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise FeasibilityInputError(f"{field} must be a non-empty string")
    return value


def _fraction_from_record(value: Any, field: str) -> Fraction:
    if not isinstance(value, Mapping):
        raise FeasibilityInputError(f"missing exact fraction: {field}")
    numerator = value.get("numerator")
    denominator = value.get("denominator")
    if (
        type(numerator) is not int
        or type(denominator) is not int
        or denominator <= 0
    ):
        raise FeasibilityInputError(f"invalid exact fraction: {field}")
    return Fraction(numerator, denominator)


def _count_rate_record(numerator: int, denominator: int) -> dict[str, Any]:
    return {
        "denominator": denominator,
        "numerator": numerator,
        "value": _format_decimal(Decimal(numerator) / Decimal(denominator)),
    }


def _format_decimal(value: Decimal) -> str:
    quantum = Decimal(1).scaleb(-DISPLAY_PLACES)
    with localcontext() as context:
        context.prec = DECIMAL_PRECISION
        return format(value.quantize(quantum), "f")


def _replace_files_transactionally(
    payloads: Sequence[tuple[Path, bytes]],
) -> None:
    destinations = [Path(destination) for destination, _payload in payloads]
    if len(set(destinations)) != len(destinations):
        raise FeasibilityInputError("transaction destinations must be unique")
    for destination in destinations:
        destination.parent.mkdir(parents=True, exist_ok=True)

    temporary_files: dict[Path, Path] = {}
    backups: dict[Path, Path] = {}
    installed: list[Path] = []
    completed = False
    try:
        for destination, payload in payloads:
            temporary_files[destination] = _write_temporary_file(
                destination,
                payload,
            )
        for destination in destinations:
            if destination.exists():
                backup = _reserve_backup_path(destination)
                os.replace(destination, backup)
                backups[destination] = backup
        for destination in destinations:
            os.replace(temporary_files[destination], destination)
            installed.append(destination)
        completed = True
    except Exception as original_error:
        rollback_errors: list[str] = []
        for destination in reversed(installed):
            try:
                if destination.exists():
                    destination.unlink()
            except OSError as exc:
                rollback_errors.append(f"remove {destination}: {exc}")
        for destination, backup in backups.items():
            try:
                if backup.exists():
                    os.replace(backup, destination)
            except OSError as exc:
                rollback_errors.append(f"restore {destination}: {exc}")
        if rollback_errors:
            raise FeasibilityInputError(
                "artifact transaction rollback incomplete: "
                + "; ".join(rollback_errors)
            ) from original_error
        raise
    finally:
        for temporary in temporary_files.values():
            try:
                if temporary.exists():
                    temporary.unlink()
            except OSError:
                pass
        if completed:
            for backup in backups.values():
                try:
                    if backup.exists():
                        backup.unlink()
                except OSError:
                    pass


def _write_temporary_file(destination: Path, payload: bytes) -> Path:
    with tempfile.NamedTemporaryFile(
        mode="wb",
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
        delete=False,
    ) as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
        return Path(handle.name)


def _reserve_backup_path(destination: Path) -> Path:
    descriptor, raw_path = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".bak",
        dir=destination.parent,
    )
    os.close(descriptor)
    backup = Path(raw_path)
    backup.unlink()
    return backup


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--json-output", required=True, type=Path)
    parser.add_argument("--markdown-output", required=True, type=Path)
    parser.add_argument("--repo-root", default=Path.cwd(), type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        report = run_feasibility_audit(
            args.input,
            args.json_output,
            args.markdown_output,
            repo_root=args.repo_root,
        )
    except (FeasibilityInputError, OSError) as exc:
        print(f"noncombat study feasibility audit failed: {exc}", file=sys.stderr)
        return 2
    print(report["result"]["study_feasibility"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
