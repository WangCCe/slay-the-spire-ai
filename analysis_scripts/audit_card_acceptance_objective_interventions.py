"""Source-only objective-intervention audit for sealed card-reward gradients."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import hashlib
import importlib
import json
import math
from numbers import Real
import os
from pathlib import Path
import stat
import subprocess
import sys
from typing import Any


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class AuditError(ValueError):
    """Raised when immutable evidence or audit arithmetic is invalid."""


AUDIT_SCHEMA_VERSION = "noncombat-card-acceptance-objective-intervention-audit-v1"
PRIOR_AUDIT_SCHEMA_VERSION = "noncombat-card-acceptance-conditional-choice-audit-v1"
LOGICAL_EXECUTION_ID = (
    "noncombat-cross-fitted-hierarchical-learning-successor-20260808-r2"
)
EXPECTED_IDENTITY = {
    "authorization_sha256": (
        "80dffa2fa2c1d1a9d68d638276c73730415842f085c7d881609a37114d88152f"
    ),
    "logical_execution_id": LOGICAL_EXECUTION_ID,
    "registration_sha256": (
        "9d792cadbece4ea21768386904633ebded2e94525fb186bdcbf4a4d7729dbdf9"
    ),
    "request_sha256": (
        "6257a36c6573c8c412bb8727736e81b063dd0c7076f1ea5b41a70d4a08206c2e"
    ),
}
EXPECTED_TERMINAL_SHA256 = (
    "3de29ce568b0d418f4e1052c4b7c92040d2de316e035b455c47384daf48db1e0"
)
EXPECTED_MANIFEST_SHA256 = (
    "b563fe8f95fa705ffcf7eafe14c40672599e46ad2a611db6f473a654ec8860eb"
)
EXPECTED_TERMINAL_VERDICT = "experiment_completed_with_cross_fitted_mechanism_evidence"
EXPECTED_PRIOR_VERDICT = (
    "acceptance_pressure_with_conditional_concentration_but_mixed_direct_pressure"
)
EXPECTED_PRIOR_JSON_SHA256 = (
    "0a10f7e763a40d7a6de751abaa6ac3aa13e02bace06ff6453fd79942d2447f33"
)
EXPECTED_PRIOR_MARKDOWN_SHA256 = (
    "3a789e7924bdf2de55c2e27c98dfefeffb0ef58334dc7cd410f31c243af85825"
)

DEFAULT_SOURCE_PATH = (
    "analysis_scripts/audit_card_acceptance_objective_interventions.py"
)
DEFAULT_PRIOR_SOURCE_PATH = (
    "analysis_scripts/audit_card_acceptance_conditional_choice.py"
)
DEFAULT_BASELINE_SOURCE_PATH = "analysis_scripts/audit_cross_fitted_baseline_support.py"
DEFAULT_VERIFIER_SOURCE_PATH = (
    "analysis_scripts/verify_noncombat_cross_fitted_hierarchical_learning_experiment.py"
)
DEFAULT_SPEC_PATH = (
    "openspec/changes/audit-card-acceptance-objective-interventions/specs/"
    "noncombat-card-acceptance-objective-intervention-audit/spec.md"
)
DEFAULT_PRIOR_SPEC_PATH = (
    "openspec/specs/noncombat-card-acceptance-conditional-choice-audit/spec.md"
)
SOURCE_BINDING_PATHS = (
    DEFAULT_SOURCE_PATH,
    DEFAULT_PRIOR_SOURCE_PATH,
    DEFAULT_BASELINE_SOURCE_PATH,
    DEFAULT_VERIFIER_SOURCE_PATH,
    DEFAULT_SPEC_PATH,
    DEFAULT_PRIOR_SPEC_PATH,
)
DEFAULT_TERMINAL_ROOT = (
    "reports/noncombat_cross_fitted_hierarchical_learning_successor_20260808_r2"
)
DEFAULT_PRIOR_JSON_PATH = (
    "reports/noncombat_card_acceptance_conditional_choice_audit_20260809.json"
)
DEFAULT_PRIOR_MARKDOWN_PATH = (
    "reports/noncombat_card_acceptance_conditional_choice_audit_20260809.md"
)
DEFAULT_JSON_NAME = (
    "noncombat_card_acceptance_objective_intervention_audit_20260809.json"
)
DEFAULT_MARKDOWN_NAME = (
    "noncombat_card_acceptance_objective_intervention_audit_20260809.md"
)

COMPONENT_NAMES = (
    "card_reward_family_policy",
    "card_reward_conditional_policy",
    "other_policy",
    "family_entropy_regularizer",
    "conditional_entropy_regularizer",
)
EXPECTED_PRIOR_AUTHORITY_NAMES = (
    "causal",
    "causal_claim",
    "cohort_materialization",
    "communication_mod",
    "environment_construction",
    "evaluation",
    "execution",
    "formal_rl",
    "gameplay",
    "model_fitting",
    "model_loading",
    "native_loading",
    "ope",
    "policy_quality",
    "policy_promotion",
    "qualification",
    "replay",
    "seed_access",
    "training",
)
AUTHORITY_NAMES = tuple(
    sorted(
        {
            *EXPECTED_PRIOR_AUTHORITY_NAMES,
            "architecture_selection",
            "coefficient_selection",
            "objective_selection",
        }
    )
)
EXPECTED_PRIOR_LIMITATIONS = (
    "Acceptance and conditional pressures are descriptive row-local score-space "
    "coordinates, not causal effects or optimizer updates.",
    "Shared-parameter gradient geometry cannot identify a candidate-score effect "
    "because the sealed bundle contains no per-row score Jacobian.",
    "Repeated decisions within one trajectory are not independent samples.",
    "The exploratory probe used to scope this known-data audit was not a blind "
    "preregistration and selected no magnitude threshold.",
    "The audit estimates no policy value, confidence interval, OPE quantity, "
    "target-supported outcome, or live-game effect.",
    "No verdict authorizes fitting, training, replay, evaluation, model loading, "
    "gameplay, qualification, or promotion.",
)
LIMITATIONS = (
    "Gradient compositions are post-hoc Euclidean geometry in the retained "
    "shared-parameter coordinates, not policy-quality or causal evidence.",
    "The family-policy ablation is a structural control and is not a selected "
    "objective or recommended successor.",
    "The conflict guard constrains only the family-policy component relative "
    "to the conditional-policy component; other components remain unchanged.",
    "Synthetic independent-coordinate invariants establish representational "
    "feasibility but do not show that the current shared ranker implements it.",
    "The known r2 cohort influenced this post-hoc candidate set; no magnitude "
    "threshold, coefficient, architecture, or policy is selected.",
    "No verdict authorizes fitting, training, replay, evaluation, OPE, model "
    "loading, gameplay, qualification, promotion, or a live-policy change.",
)
EXPECTED_CHUNKS = 8
EXPECTED_TRAJECTORIES = 512
EXPECTED_DECISIONS = 11729
EXPECTED_CARD_REWARD_ROWS = 3536
VECTOR_ATOL = 1e-9
GRADIENT_ATOL = 1e-7
GRADIENT_RTOL = 1e-5
GRADIENT_NORM_CEILING = 1.0
GRADIENT_CLIP_EPSILON = 1e-6
MAX_JSON_REPORT_BYTES = 1 * 1024 * 1024
MAX_MARKDOWN_REPORT_BYTES = 64 * 1024
RAW_VECTOR_FIELD_NAMES = frozenset(
    {"component_vectors", "data_base64", "guarded_family", "raw_vectors", "values"}
)
_PRIOR_MODULE: Any | None = None


def audit_authority() -> dict[str, bool]:
    return {name: False for name in AUTHORITY_NAMES}


def audit_scope() -> dict[str, bool]:
    return {
        "artifact_mutation": False,
        "coefficient_search": False,
        "environment_construction": False,
        "evaluation": False,
        "model_loading": False,
        "native_loading": False,
        "new_seed_access": False,
        "objective_selection": False,
        "source_only": True,
        "training_or_replay": False,
    }


def _load_prior() -> Any:
    global _PRIOR_MODULE
    if _PRIOR_MODULE is None:
        _PRIOR_MODULE = importlib.import_module(
            "analysis_scripts.audit_card_acceptance_conditional_choice"
        )
    return _PRIOR_MODULE


def forbidden_loaded_modules() -> list[str]:
    prefixes = (
        "torch",
        "spirecomm",
        "sts_lightspeed_noncombat_adapter",
        "analysis_scripts.noncombat_cross_fitted_hierarchical_learning_experiment",
        "analysis_scripts.noncombat_cross_fitted_hierarchical_learning_runtime",
        "analysis_scripts.noncombat_simulator_adapter",
    )
    return sorted(
        name
        for name in sys.modules
        if any(name == prefix or name.startswith(prefix + ".") for prefix in prefixes)
    )


def _reject_constant(value: str) -> None:
    raise AuditError(f"JSON contains non-finite constant: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AuditError(f"JSON contains duplicate key: {key}")
        result[key] = value
    return result


def canonical_json_bytes(value: object) -> bytes:
    try:
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
    except (TypeError, ValueError) as exc:
        raise AuditError(f"value is not canonical JSON: {exc}") from exc


def parse_json_bytes(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AuditError(f"{label} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise AuditError(f"{label} must be a JSON object")
    return value


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise AuditError(f"{label} must be an object")
    return value


def _sequence(value: Any, label: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(
        value, Sequence
    ):
        raise AuditError(f"{label} must be an array")
    return value


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise AuditError(f"{label} must be finite")
    result = float(value)
    if not math.isfinite(result):
        raise AuditError(f"{label} must be finite")
    return result


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise AuditError(f"{label} must be an integer >= {minimum}")
    return value


def _is_reparse_point(path: Path) -> bool:
    try:
        observed = path.lstat()
    except OSError as exc:
        raise AuditError(f"cannot inspect path: {path}") from exc
    return bool(
        getattr(observed, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


def _regular_file(path: Path, label: str) -> Path:
    target = Path(path)
    try:
        observed = target.lstat()
    except OSError as exc:
        raise AuditError(f"{label} is unavailable") from exc
    if (
        not stat.S_ISREG(observed.st_mode)
        or target.is_symlink()
        or _is_reparse_point(target)
    ):
        raise AuditError(f"{label} must be a regular non-symlink file")
    return target


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _git(repo_root: Path, *args: str, allow_failure: bool = False) -> bytes:
    process = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        check=False,
    )
    if process.returncode and not allow_failure:
        message = process.stderr.decode("utf-8", errors="replace").strip()
        raise AuditError(f"git {' '.join(args)} failed: {message}")
    return process.stdout


def verify_pushed_source(repo_root: Path | str, source_commit: str) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    if not isinstance(source_commit, str) or len(source_commit) not in (40, 64):
        raise AuditError("source commit is invalid")
    head = _git(root, "rev-parse", "HEAD").decode("ascii").strip()
    origin = _git(root, "rev-parse", "origin/master").decode("ascii").strip()
    if head != source_commit or origin != source_commit:
        raise AuditError("source commit must match HEAD and origin/master")
    status = _git(root, "status", "--porcelain", "--", *SOURCE_BINDING_PATHS)
    if status.strip():
        raise AuditError("source worktree differs from the pushed commit")
    bindings: dict[str, dict[str, Any]] = {}
    for relative in SOURCE_BINDING_PATHS:
        path = _regular_file(root / relative, relative)
        raw = path.read_bytes()
        if raw != _git(root, "show", f"{head}:{relative}"):
            raise AuditError(f"source Git blob mismatch: {relative}")
        bindings[relative] = {"sha256": _digest(raw), "size_bytes": len(raw)}
    return {"bindings": bindings, "commit": head, "origin_master": origin}


def validate_prior_audit_bytes(
    json_raw: bytes, markdown_raw: bytes
) -> dict[str, Any]:
    if _digest(json_raw) != EXPECTED_PRIOR_JSON_SHA256:
        raise AuditError("prior audit JSON binding mismatch")
    if _digest(markdown_raw) != EXPECTED_PRIOR_MARKDOWN_SHA256:
        raise AuditError("prior audit Markdown binding mismatch")
    report = parse_json_bytes(json_raw, "prior card-acceptance audit")
    if canonical_json_bytes(report) != json_raw:
        raise AuditError("prior audit JSON is not canonical")
    counts = _mapping(
        _mapping(report.get("evidence"), "prior evidence").get("execution_counts"),
        "prior execution counts",
    )
    if (
        report.get("schema_version") != PRIOR_AUDIT_SCHEMA_VERSION
        or report.get("identity") != EXPECTED_IDENTITY
        or report.get("verdict") != EXPECTED_PRIOR_VERDICT
        or report.get("authority")
        != {name: False for name in EXPECTED_PRIOR_AUTHORITY_NAMES}
        or report.get("limitations") != list(EXPECTED_PRIOR_LIMITATIONS)
        or counts.get("chunks") != EXPECTED_CHUNKS
        or counts.get("trajectories") != EXPECTED_TRAJECTORIES
        or counts.get("decisions") != EXPECTED_DECISIONS
        or counts.get("card_reward_rows") != EXPECTED_CARD_REWARD_ROWS
        or counts.get("take_candidate_multiplicity") != {"3": 3522, "4": 14}
    ):
        raise AuditError("prior audit identity, count, or authority mismatch")
    terminal = _mapping(
        report.get("terminal_verification"), "prior terminal verification"
    )
    if (
        terminal.get("manifest_sha256") != EXPECTED_MANIFEST_SHA256
        or terminal.get("terminal_sha256") != EXPECTED_TERMINAL_SHA256
        or terminal.get("verdict") != EXPECTED_TERMINAL_VERDICT
        or terminal.get("completed_chunk_indices") != list(range(EXPECTED_CHUNKS))
    ):
        raise AuditError("prior terminal verification mismatch")
    return report


def _validate_vector_set(
    components: Mapping[str, Sequence[float]], full: Sequence[float]
) -> dict[str, tuple[float, ...]]:
    if set(components) != set(COMPONENT_NAMES):
        raise AuditError("gradient component identity mismatch")
    full_values = tuple(_finite(value, "full gradient value") for value in full)
    if not full_values:
        raise AuditError("gradient vectors must be nonempty")
    normalized: dict[str, tuple[float, ...]] = {}
    for name in COMPONENT_NAMES:
        values = tuple(
            _finite(value, f"{name} gradient value") for value in components[name]
        )
        if len(values) != len(full_values):
            raise AuditError("gradient component shape mismatch")
        normalized[name] = values
    reconstructed = tuple(
        math.fsum(normalized[name][index] for name in COMPONENT_NAMES)
        for index in range(len(full_values))
    )
    try:
        _load_prior()._maximum_vector_residual(
            reconstructed, full_values, "recorded gradient reconstruction"
        )
    except ValueError as exc:
        raise AuditError(str(exc)) from exc
    normalized["__full__"] = full_values
    return normalized


def decode_recorded_gradients(gradients: Mapping[str, Any]) -> dict[str, Any]:
    value = _mapping(gradients, "gradients")
    prior_module = _load_prior()
    try:
        reconciliation = prior_module.reconcile_gradient_vectors(value)
        payloads = _mapping(value.get("component_vectors"), "component vectors")
        components = {
            name: prior_module.decode_float64_vector(
                _mapping(payloads.get(name), f"component {name}"),
                f"component {name}",
            )
            for name in COMPONENT_NAMES
        }
        full = prior_module.decode_float64_vector(
            _mapping(value.get("full"), "full gradient"), "full gradient"
        )
    except ValueError as exc:
        raise AuditError(str(exc)) from exc
    normalized = _validate_vector_set(components, full)
    return {
        "components": {name: normalized[name] for name in COMPONENT_NAMES},
        "full": normalized["__full__"],
        "reconciliation": reconciliation,
    }


def _add(*vectors: Sequence[float]) -> tuple[float, ...]:
    if not vectors or not vectors[0]:
        raise AuditError("gradient vectors must be nonempty")
    size = len(vectors[0])
    if any(len(vector) != size for vector in vectors):
        raise AuditError("gradient vector shapes differ")
    return tuple(
        math.fsum(vector[index] for vector in vectors) for index in range(size)
    )


def _subtract(left: Sequence[float], right: Sequence[float]) -> tuple[float, ...]:
    if len(left) != len(right) or not left:
        raise AuditError("gradient vector shapes differ")
    return tuple(a - b for a, b in zip(left, right, strict=True))


def _scale(vector: Sequence[float], multiplier: float) -> tuple[float, ...]:
    factor = _finite(multiplier, "gradient multiplier")
    return tuple(value * factor for value in vector)


def _norm(vector: Sequence[float]) -> float:
    if not vector:
        raise AuditError("gradient vectors must be nonempty")
    return math.sqrt(math.fsum(value * value for value in vector))


def _dot(left: Sequence[float], right: Sequence[float]) -> float:
    return _finite(
        _load_prior().vector_geometry(left, right)["dot"], "gradient dot"
    )


def _frozen_clip(vector: Sequence[float]) -> dict[str, float]:
    raw_norm = _norm(vector)
    factor = (
        1.0
        if raw_norm <= GRADIENT_NORM_CEILING
        else GRADIENT_NORM_CEILING / (raw_norm + GRADIENT_CLIP_EPSILON)
    )
    return {"clip_factor": factor, "clipped_norm": raw_norm * factor}


def _candidate_summary(
    vector: Sequence[float],
    *,
    family: Sequence[float],
    conditional: Sequence[float],
    recorded: Sequence[float],
    retained_family_policy: Sequence[float],
) -> dict[str, Any]:
    prior_module = _load_prior()
    clip = _frozen_clip(vector)
    return {
        **clip,
        "displacement_from_recorded": _norm(_subtract(vector, recorded)),
        "raw_norm": _norm(vector),
        "retained_family_policy_norm": _norm(retained_family_policy),
        "to_conditional": prior_module.vector_geometry(vector, conditional),
        "to_family": prior_module.vector_geometry(vector, family),
        "to_recorded": prior_module.vector_geometry(vector, recorded),
    }


def analyze_gradient_components(
    components: Mapping[str, Sequence[float]], full: Sequence[float]
) -> dict[str, Any]:
    normalized = _validate_vector_set(components, full)
    values = {name: normalized[name] for name in COMPONENT_NAMES}
    recorded = normalized["__full__"]
    family = values["card_reward_family_policy"]
    conditional = values["card_reward_conditional_policy"]
    remainder = _add(
        values["other_policy"],
        values["family_entropy_regularizer"],
        values["conditional_entropy_regularizer"],
    )
    ablated = _add(conditional, remainder)
    conditional_norm_sq = _dot(conditional, conditional)
    family_conditional_dot = _dot(family, conditional)
    conditional_supported = conditional_norm_sq > 0.0
    projection_applied = conditional_supported and family_conditional_dot < 0.0
    projection_multiplier: float | None = None
    guarded_family = family
    if projection_applied:
        projection_multiplier = family_conditional_dot / conditional_norm_sq
        guarded_family = _subtract(
            family, _scale(conditional, projection_multiplier)
        )
    guarded = _add(guarded_family, conditional, remainder)
    guarded_dot = _dot(guarded_family, conditional)
    projected_to_zero = (
        not projection_applied
        or math.isclose(
            guarded_dot, 0.0, rel_tol=GRADIENT_RTOL, abs_tol=GRADIENT_ATOL
        )
    )
    non_conflict_unchanged = projection_applied or guarded_family == family
    return {
        "conditional_supported": conditional_supported,
        "family_conditional_dot": family_conditional_dot,
        "guard_invariants": {
            "conflict_projected_to_zero": projected_to_zero,
            "non_conflict_unchanged": non_conflict_unchanged,
        },
        "guarded_family": guarded_family,
        "guarded_family_conditional_dot": guarded_dot,
        "interventions": {
            "conditional_conflict_guarded": _candidate_summary(
                guarded,
                family=family,
                conditional=conditional,
                recorded=recorded,
                retained_family_policy=guarded_family,
            ),
            "family_policy_ablated": _candidate_summary(
                ablated,
                family=family,
                conditional=conditional,
                recorded=recorded,
                retained_family_policy=tuple(0.0 for _ in family),
            ),
            "recorded": _candidate_summary(
                recorded,
                family=family,
                conditional=conditional,
                recorded=recorded,
                retained_family_policy=family,
            ),
        },
        "projection_applied": projection_applied,
        "projection_multiplier": projection_multiplier,
    }


def classify_verdict(
    chunks: Sequence[Mapping[str, Any]],
) -> tuple[str, dict[str, Any]]:
    values = list(_sequence(chunks, "chunk summaries"))
    if [row.get("chunk_index") for row in values] != list(range(EXPECTED_CHUNKS)):
        raise AuditError("chunk indices must be exactly 0..7")
    unsupported: list[int] = []
    conflicting: list[int] = []
    for index, row in enumerate(values):
        supported = row.get("conditional_supported")
        if not isinstance(supported, bool):
            raise AuditError("conditional support must be boolean")
        if not supported:
            unsupported.append(index)
        dot = _finite(row.get("family_conditional_dot"), "family conditional dot")
        if dot < 0.0:
            conflicting.append(index)
        invariants = _mapping(row.get("guard_invariants"), "guard invariants")
        if invariants.get("conflict_projected_to_zero") is not True:
            raise AuditError("conflicting gradient was not projected to zero")
        if invariants.get("non_conflict_unchanged") is not True:
            raise AuditError("non-conflicting gradient changed")
    inputs = {
        "conditional_support": "insufficient" if unsupported else "supported",
        "conflicting_chunk_indices": conflicting,
        "unsupported_chunk_indices": unsupported,
    }
    if unsupported:
        return "insufficient_conditional_gradient_support", inputs
    if not conflicting:
        return "no_recorded_family_conditional_conflict", inputs
    return "bounded_conditional_conflict_guard_feasible", inputs


def summarize_windows(chunks: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    values = list(_sequence(chunks, "chunk summaries"))
    if [row.get("chunk_index") for row in values] != list(range(EXPECTED_CHUNKS)):
        raise AuditError("chunk indices must be exactly 0..7")

    def summarize(start: int, stop: int) -> dict[str, Any]:
        window = values[start:stop]
        return {
            "chunk_indices": list(range(start, stop)),
            "conflicting_chunk_indices": [
                int(row["chunk_index"])
                for row in window
                if _finite(
                    row.get("family_conditional_dot"), "family conditional dot"
                )
                < 0.0
            ],
            "projected_chunks": sum(
                row.get("projection_applied") is True for row in window
            ),
            "supported_chunks": sum(
                row.get("conditional_supported") is True for row in window
            ),
        }

    return {"early": summarize(0, 4), "final": summarize(4, 8)}


def _validated_logits(values: Mapping[str, Any], label: str) -> dict[str, float]:
    result: dict[str, float] = {}
    for raw_name, raw_value in values.items():
        if not isinstance(raw_name, str) or not raw_name:
            raise AuditError(f"{label} identity is invalid")
        result[raw_name] = _finite(raw_value, f"{label} {raw_name}")
    if not result:
        raise AuditError(f"{label} must be nonempty")
    return dict(sorted(result.items()))


def independent_distribution(
    family_logits: Mapping[str, Any],
    conditional_logits: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    prior_module = _load_prior()
    families = _validated_logits(_mapping(family_logits, "family logits"), "family logits")
    conditional_input = _mapping(conditional_logits, "conditional logits")
    if set(conditional_input) != set(families):
        raise AuditError("family and conditional coverage mismatch")
    family_order = list(families)
    family_values = prior_module._softmax([families[name] for name in family_order])
    family_probabilities = dict(zip(family_order, family_values, strict=True))
    conditional_probabilities: dict[str, dict[str, float]] = {}
    conditional_entropies: dict[str, float] = {}
    conditional_order: dict[str, list[str]] = {}
    conditional_top_two_margin: dict[str, float | None] = {}
    for family in family_order:
        logits = _validated_logits(
            _mapping(conditional_input[family], f"conditional logits {family}"),
            f"conditional logits {family}",
        )
        action_order = list(logits)
        probabilities = prior_module._softmax(
            [logits[action] for action in action_order]
        )
        mapping = dict(zip(action_order, probabilities, strict=True))
        conditional_probabilities[family] = mapping
        conditional_entropies[family] = prior_module._entropy(list(mapping.values()))
        ordered = sorted(mapping, key=lambda action: (-mapping[action], action))
        conditional_order[family] = ordered
        conditional_top_two_margin[family] = (
            mapping[ordered[0]] - mapping[ordered[1]]
            if len(ordered) >= 2
            else None
        )
    return {
        "conditional_entropies": conditional_entropies,
        "conditional_order": conditional_order,
        "conditional_probabilities": conditional_probabilities,
        "conditional_top_two_margin": conditional_top_two_margin,
        "family_entropy": prior_module._entropy(list(family_probabilities.values())),
        "family_order": family_order,
        "family_probabilities": family_probabilities,
    }


def max_pooled_distribution(
    candidates: Sequence[Mapping[str, Any]], scores: Mapping[str, Any]
) -> dict[str, Any]:
    try:
        return _load_prior().reconstruct_distribution(candidates, scores)
    except ValueError as exc:
        raise AuditError(str(exc)) from exc


def softmax_directional_derivative(
    logits: Mapping[str, Any], direction: Mapping[str, Any]
) -> dict[str, float]:
    prior_module = _load_prior()
    values = _validated_logits(_mapping(logits, "logits"), "logits")
    directions = _validated_logits(_mapping(direction, "direction"), "direction")
    if set(values) != set(directions):
        raise AuditError("logit and direction coverage mismatch")
    probabilities = prior_module._softmax(list(values.values()))
    names = list(values)
    mean_direction = math.fsum(
        probability * directions[name]
        for name, probability in zip(names, probabilities, strict=True)
    )
    return {
        name: probability * (directions[name] - mean_direction)
        for name, probability in zip(names, probabilities, strict=True)
    }


def finite_difference_softmax(
    logits: Mapping[str, Any],
    direction: Mapping[str, Any],
    *,
    epsilon: float,
) -> dict[str, float]:
    prior_module = _load_prior()
    values = _validated_logits(_mapping(logits, "logits"), "logits")
    directions = _validated_logits(_mapping(direction, "direction"), "direction")
    step = _finite(epsilon, "finite-difference epsilon")
    if step <= 0.0:
        raise AuditError("finite-difference epsilon must be positive")
    if set(values) != set(directions):
        raise AuditError("logit and direction coverage mismatch")
    names = list(values)
    plus = prior_module._softmax(
        [values[name] + step * directions[name] for name in names]
    )
    minus = prior_module._softmax(
        [values[name] - step * directions[name] for name in names]
    )
    return {
        name: (right - left) / (2.0 * step)
        for name, left, right in zip(names, minus, plus, strict=True)
    }


def synthetic_contracts() -> dict[str, Any]:
    family = {"skip": -0.3, "take": 0.2}
    conditional = {
        "skip": {"skip": 0.0},
        "take": {"a": 0.5, "b": 0.1, "c": -0.2},
    }
    original = independent_distribution(family, conditional)
    translated = independent_distribution(
        {**family, "take": family["take"] + 0.75}, conditional
    )
    changed_conditional_logits = {
        **conditional,
        "take": {"a": 0.7, "b": 0.0, "c": -0.3},
    }
    conditionally_changed = independent_distribution(
        family, changed_conditional_logits
    )
    one_family = independent_distribution(
        {"take": 0.0}, {"take": {"a": 0.2, "b": -0.1}}
    )
    one_family_translated = independent_distribution(
        {"take": 10.0}, {"take": {"a": 0.2, "b": -0.1}}
    )
    candidates = [
        {"action_id": "a", "kind": "take"},
        {"action_id": "b", "kind": "take"},
        {"action_id": "skip", "kind": "skip"},
    ]
    pooled = max_pooled_distribution(
        candidates, {"a": 0.5, "b": 0.1, "skip": 0.2}
    )
    pooled_changed = max_pooled_distribution(
        candidates, {"a": 0.8, "b": 0.1, "skip": 0.2}
    )
    pooled_tied = max_pooled_distribution(
        candidates, {"a": 0.5, "b": 0.5, "skip": 0.2}
    )
    logits = {"a": 0.5, "b": 0.1, "c": -0.2}
    direction = {"a": 0.2, "b": -0.1, "c": -0.1}
    analytical = softmax_directional_derivative(logits, direction)
    numerical = finite_difference_softmax(logits, direction, epsilon=1e-6)
    derivative_residual = max(
        abs(analytical[name] - numerical[name]) for name in analytical
    )
    acceptance_family_changed = (
        translated["family_probabilities"]["take"]
        != original["family_probabilities"]["take"]
    )
    acceptance_probabilities_unchanged = (
        translated["conditional_probabilities"]
        == original["conditional_probabilities"]
    )
    acceptance_order_unchanged = (
        translated["conditional_order"] == original["conditional_order"]
    )
    acceptance_entropy_unchanged = (
        translated["conditional_entropies"]
        == original["conditional_entropies"]
    )
    acceptance_margins_unchanged = (
        translated["conditional_top_two_margin"]
        == original["conditional_top_two_margin"]
    )
    acceptance_passed = all(
        (
            acceptance_family_changed,
            acceptance_probabilities_unchanged,
            acceptance_order_unchanged,
            acceptance_entropy_unchanged,
            acceptance_margins_unchanged,
        )
    )
    conditional_passed = (
        conditionally_changed["family_probabilities"]
        == original["family_probabilities"]
        and conditionally_changed["conditional_probabilities"]["take"]
        != original["conditional_probabilities"]["take"]
    )
    one_family_passed = one_family_translated == one_family
    pooled_passed = (
        pooled_changed["family_probabilities"]["take"]
        != pooled["family_probabilities"]["take"]
        and pooled_changed["conditional_probabilities"]["a"]
        != pooled["conditional_probabilities"]["a"]
    )
    tie_passed = pooled_tied["raw_score_max_action_ids"] == ["a", "b"]
    derivative_passed = derivative_residual <= 1e-9
    return {
        "acceptance_translation": {
            "conditional_entropy_unchanged": acceptance_entropy_unchanged,
            "conditional_margins_unchanged": acceptance_margins_unchanged,
            "conditional_order_unchanged": acceptance_order_unchanged,
            "conditional_probabilities_unchanged": (
                acceptance_probabilities_unchanged
            ),
            "family_mass_changed": acceptance_family_changed,
            "passed": acceptance_passed,
        },
        "all_passed": all(
            (
                acceptance_passed,
                conditional_passed,
                one_family_passed,
                pooled_passed,
                tie_passed,
                derivative_passed,
            )
        ),
        "conditional_perturbation": {
            "conditional_distribution_changed": conditional_passed,
            "family_mass_unchanged": conditional_passed,
        },
        "derivative": {
            "finite_difference_epsilon": 1e-6,
            "maximum_absolute_residual": derivative_residual,
            "passed": derivative_passed,
        },
        "max_pooled_control": {
            "coupling_observed": pooled_passed,
            "tie_action_ids": pooled_tied["raw_score_max_action_ids"],
        },
        "one_family_fallback": {
            "acceptance_inactive": one_family_passed,
            "family_mass": one_family["family_probabilities"]["take"],
        },
    }


def _public_chunk_analysis(result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value for key, value in result.items() if key != "guarded_family"
    }


def _analyze_bound_chunks(
    terminal_root: Path, prior_report: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    prior_module = _load_prior()
    prior_analysis = prior_module._analyze_chunks(terminal_root)
    if prior_report is not None:
        expected = _mapping(prior_report.get("evidence"), "prior evidence")
        if canonical_json_bytes(prior_analysis) != canonical_json_bytes(dict(expected)):
            raise AuditError("prior audit evidence reconstruction mismatch")
    chunks: list[dict[str, Any]] = []
    for checkpoint_number in range(1, EXPECTED_CHUNKS + 1):
        checkpoint_path = prior_module.baseline._regular_file(
            terminal_root
            / "checkpoints"
            / f"checkpoint_{checkpoint_number:04d}.json",
            f"checkpoint {checkpoint_number}",
        )
        checkpoint = prior_module.baseline.verifier._parse_canonical_json(
            checkpoint_path.read_bytes(), label=f"checkpoint {checkpoint_number}"
        )
        document = prior_module.baseline._read_bound_chunk(terminal_root, checkpoint)
        evidence = _mapping(document.get("evidence"), "chunk evidence")
        chunk_index = _integer(evidence.get("chunk_index"), "chunk index")
        if chunk_index != checkpoint_number - 1:
            raise AuditError("chunk order mismatch")
        decoded = decode_recorded_gradients(
            _mapping(evidence.get("gradients"), "gradients")
        )
        result = analyze_gradient_components(decoded["components"], decoded["full"])
        previous = _mapping(
            prior_analysis["chunk_results"][chunk_index], "prior chunk result"
        )
        previous_dot = _finite(
            _mapping(
                previous.get("gradient_geometry"), "prior gradient geometry"
            )["family_conditional"]["dot"],
            "prior family conditional dot",
        )
        if not math.isclose(
            result["family_conditional_dot"],
            previous_dot,
            rel_tol=GRADIENT_RTOL,
            abs_tol=GRADIENT_ATOL,
        ):
            raise AuditError("prior family conditional geometry mismatch")
        chunks.append(
            {
                "chunk_index": chunk_index,
                "recorded_reconstruction": decoded["reconciliation"],
                **_public_chunk_analysis(result),
            }
        )
    verdict, verdict_inputs = classify_verdict(chunks)
    contracts = synthetic_contracts()
    if contracts["all_passed"] is not True:
        raise AuditError("synthetic intervention contract failed")
    counts = _mapping(prior_analysis.get("execution_counts"), "execution counts")
    return {
        "chunk_results": chunks,
        "execution_counts": dict(counts),
        "synthetic_contracts": contracts,
        "verdict": verdict,
        "verdict_inputs": verdict_inputs,
        "windows": summarize_windows(chunks),
    }


def build_repository_audit(
    repo_root: Path | str, *, source_commit: str
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    terminal_root = (root / DEFAULT_TERMINAL_ROOT).resolve()
    source = verify_pushed_source(root, source_commit)
    prior_module = _load_prior()
    with prior_module.baseline.hold_inactive_lease(
        terminal_root / ".execution.lease"
    ):
        try:
            verification = prior_module.baseline.verifier.verify_terminal_bundle(
                terminal_root, repo_root=root
            )
            prior_module.baseline.validate_verifier_result(verification)
            prior_json_path = prior_module.baseline._regular_file(
                root / DEFAULT_PRIOR_JSON_PATH, "prior card-acceptance JSON"
            )
            prior_markdown_path = prior_module.baseline._regular_file(
                root / DEFAULT_PRIOR_MARKDOWN_PATH, "prior card-acceptance Markdown"
            )
            prior_json_raw = prior_json_path.read_bytes()
            prior_markdown_raw = prior_markdown_path.read_bytes()
            prior_report = validate_prior_audit_bytes(
                prior_json_raw, prior_markdown_raw
            )
            prior_module.baseline._validate_snapshot(terminal_root)
            analysis = _analyze_bound_chunks(terminal_root, prior_report)
        except AuditError:
            raise
        except (OSError, ValueError) as exc:
            raise AuditError(f"bound evidence verification failed: {exc}") from exc
    forbidden = forbidden_loaded_modules()
    if forbidden:
        raise AuditError(f"forbidden modules loaded: {forbidden}")
    return {
        "authority": audit_authority(),
        "evidence": analysis,
        "identity": EXPECTED_IDENTITY,
        "input_bindings": {
            "prior_json": {
                "path": DEFAULT_PRIOR_JSON_PATH,
                "sha256": EXPECTED_PRIOR_JSON_SHA256,
                "size_bytes": len(prior_json_raw),
                "verdict": prior_report["verdict"],
            },
            "prior_markdown": {
                "path": DEFAULT_PRIOR_MARKDOWN_PATH,
                "sha256": EXPECTED_PRIOR_MARKDOWN_SHA256,
                "size_bytes": len(prior_markdown_raw),
            },
            "terminal_manifest": {
                "manifest_sha256": EXPECTED_MANIFEST_SHA256,
                "terminal_sha256": EXPECTED_TERMINAL_SHA256,
            },
        },
        "limitations": list(LIMITATIONS),
        "schema_version": AUDIT_SCHEMA_VERSION,
        "scope": audit_scope(),
        "source": source,
        "terminal_verification": {
            "checkpoint_count": verification["checkpoint_count"],
            "completed_chunk_indices": verification["completed_chunk_indices"],
            "manifest_sha256": verification["manifest_sha256"],
            "terminal_sha256": verification["terminal_sha256"],
            "verdict": verification["verdict"],
        },
        "verdict": analysis["verdict"],
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    verdict = str(report.get("verdict", "unknown"))
    evidence = report.get("evidence")
    if not isinstance(evidence, Mapping):
        return (
            "# Card Acceptance Objective Intervention Audit\n\n"
            f"Verdict: `{verdict}`\n\nAll downstream authority remains false.\n"
        )
    chunks = list(_sequence(evidence.get("chunk_results"), "chunk results"))
    inputs = _mapping(evidence.get("verdict_inputs"), "verdict inputs")
    lines = [
        "# Card Acceptance Objective Intervention Audit",
        "",
        "## Decision",
        "",
        f"The bounded geometry verdict is `{verdict}`.",
        "It selects no objective, coefficient, architecture, successor, or policy",
        "and grants no training, evaluation, policy-quality, or causal authority.",
        "",
        "## Gradient Evidence",
        "",
        f"- Conflicting chunks: `{inputs.get('conflicting_chunk_indices', [])}`",
        f"- Unsupported chunks: `{inputs.get('unsupported_chunk_indices', [])}`",
        "",
        "| Chunk | F dot C | Projected | Guarded F dot C | Recorded norm | Ablated displacement | Guarded displacement |",
        "| ---: | ---: | :---: | ---: | ---: | ---: | ---: |",
    ]
    for raw in chunks:
        chunk = _mapping(raw, "chunk")
        interventions = chunk.get("interventions")
        if isinstance(interventions, Mapping):
            recorded = _mapping(interventions.get("recorded"), "recorded")
            ablated = _mapping(
                interventions.get("family_policy_ablated"), "ablated"
            )
            guarded = _mapping(
                interventions.get("conditional_conflict_guarded"), "guarded"
            )
            recorded_norm = _finite(recorded.get("raw_norm"), "recorded norm")
            ablated_displacement = _finite(
                ablated.get("displacement_from_recorded"), "ablated displacement"
            )
            guarded_displacement = _finite(
                guarded.get("displacement_from_recorded"), "guarded displacement"
            )
        else:
            recorded_norm = 0.0
            ablated_displacement = 0.0
            guarded_displacement = 0.0
        lines.append(
            "| {index} | {dot:.15g} | {projected} | {guard_dot:.15g} | "
            "{recorded:.15g} | {ablated:.15g} | {guarded:.15g} |".format(
                index=chunk.get("chunk_index"),
                dot=_finite(
                    chunk.get("family_conditional_dot"), "family conditional dot"
                ),
                projected=chunk.get("projection_applied") is True,
                guard_dot=_finite(
                    chunk.get("guarded_family_conditional_dot", 0.0),
                    "guarded family conditional dot",
                ),
                recorded=recorded_norm,
                ablated=ablated_displacement,
                guarded=guarded_displacement,
            )
        )
    lines.extend(
        [
            "",
            "## Limits",
            "",
            "Projection geometry is parameterization-specific and post-hoc.",
            "The audit does not rank interventions or estimate policy value.",
            "Any objective or empirical successor requires a separate reviewed proposal.",
            "",
        ]
    )
    return "\n".join(lines)


def _contains_raw_vector_fields(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            (
                isinstance(key, str)
                and (
                    key.lower() in RAW_VECTOR_FIELD_NAMES
                    or "vector" in key.lower()
                )
            )
            or _contains_raw_vector_fields(item)
            for key, item in value.items()
        )
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        if len(value) > EXPECTED_CHUNKS and all(
            isinstance(item, Real) and not isinstance(item, bool) for item in value
        ):
            return True
        return any(_contains_raw_vector_fields(item) for item in value)
    return False


def _require_exact_keys(
    value: Mapping[str, Any], expected: set[str], label: str
) -> None:
    if set(value) != expected:
        raise AuditError(f"{label} schema mismatch")


def _validate_geometry(value: Any, label: str) -> None:
    geometry = _mapping(value, label)
    _require_exact_keys(
        geometry, {"cosine", "dot", "left_norm", "right_norm"}, label
    )
    for name in ("dot", "left_norm", "right_norm"):
        _finite(geometry.get(name), f"{label}.{name}")
    cosine = geometry.get("cosine")
    if cosine is not None:
        _finite(cosine, f"{label}.cosine")


def _validate_recorded_reconstruction(value: Any) -> None:
    reconstruction = _mapping(value, "recorded reconstruction")
    _require_exact_keys(
        reconstruction,
        {
            "clip_factor",
            "component_norms",
            "family_conditional",
            "clipped_full_norm",
            "full_norm",
            "installed_matches_consumed",
            "pairwise",
            "reconstruction_max_abs",
            "to_full",
            "uniform_clip_max_abs",
        },
        "recorded reconstruction",
    )
    for name in (
        "clip_factor",
        "clipped_full_norm",
        "full_norm",
        "reconstruction_max_abs",
        "uniform_clip_max_abs",
    ):
        _finite(reconstruction.get(name), f"recorded reconstruction.{name}")
    if reconstruction.get("installed_matches_consumed") is not True:
        raise AuditError("recorded reconstruction installation mismatch")
    norms = _mapping(reconstruction.get("component_norms"), "component norms")
    _require_exact_keys(norms, set(COMPONENT_NAMES), "component norms")
    for name in COMPONENT_NAMES:
        _finite(norms.get(name), f"component norm {name}")
    _validate_geometry(reconstruction.get("family_conditional"), "family conditional")
    pairwise = _mapping(reconstruction.get("pairwise"), "pairwise geometry")
    expected_pairwise = {
        f"{left}__{right}"
        for left_index, left in enumerate(COMPONENT_NAMES)
        for right in COMPONENT_NAMES[left_index + 1 :]
    }
    _require_exact_keys(pairwise, expected_pairwise, "pairwise geometry")
    for name, geometry in pairwise.items():
        _validate_geometry(geometry, f"pairwise geometry {name}")
    to_full = _mapping(reconstruction.get("to_full"), "to-full geometry")
    _require_exact_keys(to_full, set(COMPONENT_NAMES), "to-full geometry")
    for name, geometry in to_full.items():
        _validate_geometry(geometry, f"to-full geometry {name}")


def _validate_intervention_summary(value: Any, label: str) -> None:
    summary = _mapping(value, label)
    _require_exact_keys(
        summary,
        {
            "clip_factor",
            "clipped_norm",
            "displacement_from_recorded",
            "raw_norm",
            "retained_family_policy_norm",
            "to_conditional",
            "to_family",
            "to_recorded",
        },
        label,
    )
    for name in (
        "clip_factor",
        "clipped_norm",
        "displacement_from_recorded",
        "raw_norm",
        "retained_family_policy_norm",
    ):
        _finite(summary.get(name), f"{label}.{name}")
    for name in ("to_conditional", "to_family", "to_recorded"):
        _validate_geometry(summary.get(name), f"{label}.{name}")


def _validate_public_chunk(value: Mapping[str, Any]) -> None:
    _require_exact_keys(
        value,
        {
            "chunk_index",
            "conditional_supported",
            "family_conditional_dot",
            "guard_invariants",
            "guarded_family_conditional_dot",
            "interventions",
            "projection_applied",
            "projection_multiplier",
            "recorded_reconstruction",
        },
        "report chunk",
    )
    _integer(value.get("chunk_index"), "chunk index")
    if not isinstance(value.get("conditional_supported"), bool):
        raise AuditError("chunk conditional support must be boolean")
    if not isinstance(value.get("projection_applied"), bool):
        raise AuditError("chunk projection flag must be boolean")
    _finite(value.get("family_conditional_dot"), "family conditional dot")
    _finite(
        value.get("guarded_family_conditional_dot"),
        "guarded family conditional dot",
    )
    multiplier = value.get("projection_multiplier")
    if multiplier is not None:
        _finite(multiplier, "projection multiplier")
    invariants = _mapping(value.get("guard_invariants"), "guard invariants")
    _require_exact_keys(
        invariants,
        {"conflict_projected_to_zero", "non_conflict_unchanged"},
        "guard invariants",
    )
    if set(invariants.values()) != {True}:
        raise AuditError("guard invariants must all pass")
    interventions = _mapping(value.get("interventions"), "interventions")
    _require_exact_keys(
        interventions,
        {
            "conditional_conflict_guarded",
            "family_policy_ablated",
            "recorded",
        },
        "interventions",
    )
    for name, summary in interventions.items():
        _validate_intervention_summary(summary, f"intervention {name}")
    _validate_recorded_reconstruction(value.get("recorded_reconstruction"))


def _validate_report_for_publication(report: Mapping[str, Any]) -> None:
    if _contains_raw_vector_fields(report):
        raise AuditError("report contains a raw vector field")
    required = {
        "authority",
        "evidence",
        "identity",
        "input_bindings",
        "limitations",
        "schema_version",
        "scope",
        "source",
        "terminal_verification",
        "verdict",
    }
    if set(report) != required:
        raise AuditError("report top-level schema mismatch")
    if report.get("schema_version") != AUDIT_SCHEMA_VERSION:
        raise AuditError("report schema version mismatch")
    if report.get("authority") != audit_authority():
        raise AuditError("report authority must be exact and all false")
    if report.get("scope") != audit_scope():
        raise AuditError("report scope mismatch")
    if report.get("identity") != EXPECTED_IDENTITY:
        raise AuditError("report identity mismatch")
    if report.get("limitations") != list(LIMITATIONS):
        raise AuditError("report limitations mismatch")
    input_bindings = _mapping(report.get("input_bindings"), "input bindings")
    _require_exact_keys(
        input_bindings,
        {"prior_json", "prior_markdown", "terminal_manifest"},
        "input bindings",
    )
    prior_json = _mapping(input_bindings.get("prior_json"), "prior JSON binding")
    _require_exact_keys(
        prior_json, {"path", "sha256", "size_bytes", "verdict"}, "prior JSON binding"
    )
    prior_markdown = _mapping(
        input_bindings.get("prior_markdown"), "prior Markdown binding"
    )
    _require_exact_keys(
        prior_markdown, {"path", "sha256", "size_bytes"}, "prior Markdown binding"
    )
    terminal_binding = _mapping(
        input_bindings.get("terminal_manifest"), "terminal binding"
    )
    _require_exact_keys(
        terminal_binding,
        {"manifest_sha256", "terminal_sha256"},
        "terminal binding",
    )
    if (
        prior_json.get("path") != DEFAULT_PRIOR_JSON_PATH
        or prior_json.get("sha256") != EXPECTED_PRIOR_JSON_SHA256
        or prior_json.get("verdict") != EXPECTED_PRIOR_VERDICT
        or prior_markdown.get("path") != DEFAULT_PRIOR_MARKDOWN_PATH
        or prior_markdown.get("sha256") != EXPECTED_PRIOR_MARKDOWN_SHA256
        or terminal_binding.get("manifest_sha256") != EXPECTED_MANIFEST_SHA256
        or terminal_binding.get("terminal_sha256") != EXPECTED_TERMINAL_SHA256
    ):
        raise AuditError("report input binding identity mismatch")
    _integer(prior_json.get("size_bytes"), "prior JSON size", minimum=1)
    _integer(prior_markdown.get("size_bytes"), "prior Markdown size", minimum=1)
    source = _mapping(report.get("source"), "report source")
    _require_exact_keys(
        source, {"bindings", "commit", "origin_master"}, "report source"
    )
    source_commit = source.get("commit")
    if not isinstance(source_commit, str) or len(source_commit) not in (40, 64):
        raise AuditError("report source identity mismatch")
    if source.get("origin_master") != source_commit:
        raise AuditError("report source origin mismatch")
    source_bindings = _mapping(source.get("bindings"), "source bindings")
    _require_exact_keys(
        source_bindings, set(SOURCE_BINDING_PATHS), "source bindings"
    )
    for relative, raw_binding in source_bindings.items():
        binding = _mapping(raw_binding, f"source binding {relative}")
        _require_exact_keys(
            binding, {"sha256", "size_bytes"}, f"source binding {relative}"
        )
        digest = binding.get("sha256")
        if not isinstance(digest, str) or len(digest) != 64:
            raise AuditError(f"source binding digest mismatch: {relative}")
        _integer(binding.get("size_bytes"), f"source binding size {relative}", minimum=1)
    terminal = _mapping(
        report.get("terminal_verification"), "report terminal verification"
    )
    if (
        terminal.get("checkpoint_count") != EXPECTED_CHUNKS
        or terminal.get("completed_chunk_indices") != list(range(EXPECTED_CHUNKS))
        or terminal.get("manifest_sha256") != EXPECTED_MANIFEST_SHA256
        or terminal.get("terminal_sha256") != EXPECTED_TERMINAL_SHA256
        or terminal.get("verdict") != EXPECTED_TERMINAL_VERDICT
    ):
        raise AuditError("report terminal verification mismatch")
    evidence = _mapping(report.get("evidence"), "report evidence")
    if set(evidence) != {
        "chunk_results",
        "execution_counts",
        "synthetic_contracts",
        "verdict",
        "verdict_inputs",
        "windows",
    }:
        raise AuditError("report evidence schema mismatch")
    chunks = [
        _mapping(chunk, "report chunk")
        for chunk in _sequence(evidence.get("chunk_results"), "report chunks")
    ]
    for chunk in chunks:
        _validate_public_chunk(chunk)
    verdict, inputs = classify_verdict(chunks)
    if (
        report.get("verdict") != verdict
        or evidence.get("verdict") != verdict
        or evidence.get("verdict_inputs") != inputs
    ):
        raise AuditError("report verdict mismatch")
    counts = _mapping(evidence.get("execution_counts"), "report execution counts")
    _require_exact_keys(
        counts,
        {
            "card_reward_rows",
            "chunks",
            "decisions",
            "take_candidate_multiplicity",
            "trajectories",
        },
        "report execution counts",
    )
    if (
        counts.get("chunks") != EXPECTED_CHUNKS
        or counts.get("trajectories") != EXPECTED_TRAJECTORIES
        or counts.get("decisions") != EXPECTED_DECISIONS
        or counts.get("card_reward_rows") != EXPECTED_CARD_REWARD_ROWS
    ):
        raise AuditError("report execution count mismatch")
    contracts = _mapping(
        evidence.get("synthetic_contracts"), "report synthetic contracts"
    )
    if dict(contracts) != synthetic_contracts():
        raise AuditError("report synthetic contracts mismatch")
    if evidence.get("windows") != summarize_windows(chunks):
        raise AuditError("report window summary mismatch")


def _binding(raw: bytes) -> dict[str, Any]:
    return {"sha256": _digest(raw), "size_bytes": len(raw)}


def publish_reports(
    report: Mapping[str, Any],
    output_dir: Path | str,
    *,
    consumed_root: Path | str | None = None,
) -> dict[str, Any]:
    _validate_report_for_publication(report)
    output = Path(output_dir).resolve()
    if consumed_root is not None:
        consumed = Path(consumed_root).resolve()
        if output == consumed or output.is_relative_to(consumed):
            raise AuditError("output directory is inside consumed evidence")
    if output.exists():
        raise AuditError("output directory already exists")
    json_raw = canonical_json_bytes(dict(report))
    markdown_raw = render_markdown(report).encode("utf-8")
    if len(json_raw) > MAX_JSON_REPORT_BYTES:
        raise AuditError("JSON report exceeds publication size bound")
    if len(markdown_raw) > MAX_MARKDOWN_REPORT_BYTES:
        raise AuditError("Markdown report exceeds publication size bound")
    output.mkdir(parents=True)
    json_path = output / DEFAULT_JSON_NAME
    markdown_path = output / DEFAULT_MARKDOWN_NAME
    json_temp = output / f".{DEFAULT_JSON_NAME}.tmp"
    markdown_temp = output / f".{DEFAULT_MARKDOWN_NAME}.tmp"
    try:
        json_temp.write_bytes(json_raw)
        markdown_temp.write_bytes(markdown_raw)
        os.replace(json_temp, json_path)
        os.replace(markdown_temp, markdown_path)
    except OSError:
        for path in (json_temp, markdown_temp, json_path, markdown_path):
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        try:
            output.rmdir()
        except OSError:
            pass
        raise
    return {"json": _binding(json_raw), "markdown": _binding(markdown_raw)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        report = build_repository_audit(
            arguments.repo_root, source_commit=arguments.source_commit
        )
        bindings = publish_reports(
            report,
            arguments.output_dir,
            consumed_root=arguments.repo_root / DEFAULT_TERMINAL_ROOT,
        )
    except (AuditError, OSError, ValueError) as exc:
        print(f"audit blocked: {exc}", file=sys.stderr)
        return 2
    print(canonical_json_bytes(bindings).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
