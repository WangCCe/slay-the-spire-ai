"""Build a bounded SimpleAgent-anchored non-combat simulator warm start."""

from __future__ import annotations

import copy
import json
import math
from collections.abc import Mapping, Sequence
from numbers import Real
from pathlib import Path
from typing import Any

from analysis_scripts.noncombat_simulator_adapter import (
    NATIVE_TARGET_POLICY_ID,
    validate_provenance,
)
from analysis_scripts.noncombat_simulator_training_smoke import (
    FEATURE_VERSION,
    SmokeBlocked,
    _validate_binding,
)


INPUT_SCHEMA_VERSION = "noncombat-simulator-baseline-warm-start-input-v1"
MODEL_ARCHITECTURE = "candidate-ranker-mlp-v1"
PRIOR_SEEDS = tuple(
    sorted(
        set(range(20))
        | set(range(1000, 1032))
        | set(range(2000, 2064))
        | set(range(3000, 3064))
    )
)
REGISTERED_SOURCE_FILES = (
    "analysis_scripts/noncombat_policy_model.py",
    "analysis_scripts/noncombat_simulator_adapter.py",
    "analysis_scripts/noncombat_simulator_baseline_warm_start.py",
    "analysis_scripts/noncombat_simulator_fit.py",
    "analysis_scripts/noncombat_simulator_policy_validity.py",
    "analysis_scripts/noncombat_simulator_training_smoke.py",
)


class WarmStartBlocked(RuntimeError):
    """Raised when the warm-start contract requires a fail-closed stop."""


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise WarmStartBlocked(f"{label} must be an object")
    return dict(value)


def _require_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise WarmStartBlocked(f"{label} keys mismatch")


def _require_exact(
    value: Mapping[str, Any], field: str, expected: object, label: str
) -> None:
    if value.get(field) != expected:
        raise WarmStartBlocked(f"{label}.{field} must equal {expected!r}")


def _is_hex(value: object, length: int) -> bool:
    return (
        isinstance(value, str)
        and len(value) == length
        and all(character in "0123456789abcdef" for character in value.lower())
    )


def _validated_binding(value: object, label: str) -> dict[str, Any]:
    try:
        return _validate_binding(value, label)
    except SmokeBlocked as exc:
        raise WarmStartBlocked(str(exc)) from exc


def _positive_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise WarmStartBlocked(f"{label} must be a positive integer")
    return value


def _finite_number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise WarmStartBlocked(f"{label} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise WarmStartBlocked(f"{label} must be a finite number")
    return result


def _seed_array(value: object, label: str, *, nonempty: bool = True) -> list[int]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise WarmStartBlocked(f"{label} must be an array")
    seeds = list(value)
    if nonempty and not seeds:
        raise WarmStartBlocked(f"{label} must be nonempty")
    if any(isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds):
        raise WarmStartBlocked(f"{label} must contain only integers")
    if len(seeds) != len(set(seeds)):
        raise WarmStartBlocked(f"{label} must be unique")
    if seeds != sorted(seeds):
        raise WarmStartBlocked(f"{label} must be sorted")
    return seeds


def _validate_identity(value: object) -> dict[str, Any]:
    identity = _mapping(value, "identity")
    _require_keys(
        identity,
        {
            "adapter_fit_input",
            "adapter_fit_report",
            "adapter_provenance",
            "excluded_baselines",
            "implementation",
            "prior_evidence",
            "runtime",
        },
        "identity",
    )
    identity["adapter_fit_input"] = _validated_binding(
        identity["adapter_fit_input"], "identity.adapter_fit_input"
    )
    identity["adapter_fit_report"] = _validated_binding(
        identity["adapter_fit_report"], "identity.adapter_fit_report"
    )
    try:
        identity["adapter_provenance"] = validate_provenance(
            identity["adapter_provenance"]
        )
    except (TypeError, ValueError) as exc:
        raise WarmStartBlocked(f"identity.adapter_provenance is invalid: {exc}") from exc
    if (
        identity["adapter_provenance"]["build"].get("native_target_policy_id")
        != NATIVE_TARGET_POLICY_ID
    ):
        raise WarmStartBlocked(
            "identity.adapter_provenance.build.native_target_policy_id mismatch"
        )

    implementation = _mapping(identity["implementation"], "identity.implementation")
    _require_keys(
        implementation, {"commit", "source_files", "source_sha256"},
        "identity.implementation"
    )
    if not _is_hex(implementation["commit"], 40):
        raise WarmStartBlocked("identity.implementation.commit is invalid")
    if implementation["source_files"] != list(REGISTERED_SOURCE_FILES):
        raise WarmStartBlocked(
            "identity.implementation.source_files must equal the registered source list"
        )
    if not _is_hex(implementation["source_sha256"], 64):
        raise WarmStartBlocked("identity.implementation.source_sha256 is invalid")
    identity["implementation"] = implementation

    runtime = _mapping(identity["runtime"], "identity.runtime")
    _require_keys(runtime, {"python", "torch"}, "identity.runtime")
    for field in ("python", "torch"):
        if not isinstance(runtime[field], str) or not runtime[field]:
            raise WarmStartBlocked(f"identity.runtime.{field} is required")
    identity["runtime"] = runtime

    prior_evidence = _mapping(identity["prior_evidence"], "identity.prior_evidence")
    _require_keys(
        prior_evidence,
        {
            "policy_validity_manifest",
            "policy_validity_registration",
            "smoke_manifest",
            "smoke_registration",
        },
        "identity.prior_evidence",
    )
    for name in sorted(prior_evidence):
        prior_evidence[name] = _validated_binding(
            prior_evidence[name], f"identity.prior_evidence.{name}"
        )
    identity["prior_evidence"] = prior_evidence

    excluded = _mapping(identity["excluded_baselines"], "identity.excluded_baselines")
    _require_keys(excluded, {"bottled", "current"}, "identity.excluded_baselines")
    for name in ("bottled", "current"):
        entry = _mapping(excluded[name], f"identity.excluded_baselines.{name}")
        _require_keys(
            entry,
            {"feature_version", "model", "reason"},
            f"identity.excluded_baselines.{name}",
        )
        _require_exact(
            entry,
            "feature_version",
            "noncombat-policy-features-v1",
            f"identity.excluded_baselines.{name}",
        )
        _require_exact(
            entry,
            "reason",
            "unvalidated_simulator_feature_action_bridge",
            f"identity.excluded_baselines.{name}",
        )
        entry["model"] = _validated_binding(
            entry["model"], f"identity.excluded_baselines.{name}.model"
        )
        excluded[name] = entry
    identity["excluded_baselines"] = excluded
    return identity


def _validate_cohorts(value: object) -> dict[str, list[int]]:
    cohorts = _mapping(value, "study.cohorts")
    _require_keys(
        cohorts,
        {
            "excluded_prior_seeds",
            "final_test_seeds",
            "train_seeds",
            "validation_seeds",
        },
        "study.cohorts",
    )
    excluded = _seed_array(
        cohorts["excluded_prior_seeds"], "study.cohorts.excluded_prior_seeds"
    )
    if excluded != list(PRIOR_SEEDS):
        raise WarmStartBlocked(
            "study.cohorts.excluded_prior_seeds must equal the registered prior seeds"
        )
    result = {"excluded_prior_seeds": excluded}
    for name in ("train_seeds", "validation_seeds", "final_test_seeds"):
        result[name] = _seed_array(cohorts[name], f"study.cohorts.{name}")
        if set(result[name]) & set(PRIOR_SEEDS):
            raise WarmStartBlocked("study cohorts overlap excluded prior seeds")
    if (
        set(result["train_seeds"]) & set(result["validation_seeds"])
        or set(result["train_seeds"]) & set(result["final_test_seeds"])
        or set(result["validation_seeds"]) & set(result["final_test_seeds"])
    ):
        raise WarmStartBlocked("study cohorts must be mutually disjoint")
    return result


def _validate_model(value: object) -> dict[str, Any]:
    model = _mapping(value, "study.model")
    expected = {
        "activation": "relu",
        "architecture": MODEL_ARCHITECTURE,
        "dropout": 0.0,
        "feature_version": FEATURE_VERSION,
        "hash_dim": 1024,
        "hidden_dim": 128,
        "model_seed": 0,
    }
    _require_keys(model, set(expected), "study.model")
    for field, expected_value in expected.items():
        _require_exact(model, field, expected_value, "study.model")
    return model


def _validate_optimizer(value: object) -> dict[str, Any]:
    optimizer = _mapping(value, "study.optimizer")
    _require_keys(
        optimizer,
        {
            "algorithm",
            "beta1",
            "beta2",
            "category_balanced",
            "deterministic_order",
            "epochs",
            "epsilon",
            "learning_rate",
            "weight_decay",
        },
        "study.optimizer",
    )
    for field, expected in {
        "algorithm": "adam",
        "category_balanced": True,
        "deterministic_order": True,
        "weight_decay": 0.0,
    }.items():
        _require_exact(optimizer, field, expected, "study.optimizer")
    optimizer["epochs"] = _positive_int(
        optimizer["epochs"], "study.optimizer.epochs"
    )
    learning_rate = _finite_number(
        optimizer["learning_rate"], "study.optimizer.learning_rate"
    )
    if not 0.0 < learning_rate <= 1.0:
        raise WarmStartBlocked("study.optimizer.learning_rate must be in (0, 1]")
    epsilon = _finite_number(optimizer["epsilon"], "study.optimizer.epsilon")
    if epsilon <= 0.0:
        raise WarmStartBlocked("study.optimizer.epsilon must be positive")
    for field in ("beta1", "beta2"):
        beta = _finite_number(optimizer[field], f"study.optimizer.{field}")
        if not 0.0 <= beta < 1.0:
            raise WarmStartBlocked(f"study.optimizer.{field} must be in [0, 1)")
    return optimizer


def _validate_evaluation(value: object) -> dict[str, Any]:
    evaluation = _mapping(value, "study.evaluation")
    _require_keys(
        evaluation,
        {
            "action_fit_metric",
            "bootstrap_resamples",
            "bootstrap_seed",
            "confidence_level",
            "primary_comparison",
            "thresholds",
        },
        "study.evaluation",
    )
    _require_exact(
        evaluation, "action_fit_metric", "exact_action_agreement", "study.evaluation"
    )
    _require_exact(
        evaluation,
        "primary_comparison",
        "candidate_minus_native_simple_agent",
        "study.evaluation",
    )
    evaluation["bootstrap_resamples"] = _positive_int(
        evaluation["bootstrap_resamples"],
        "study.evaluation.bootstrap_resamples",
    )
    bootstrap_seed = evaluation["bootstrap_seed"]
    if isinstance(bootstrap_seed, bool) or not isinstance(bootstrap_seed, int):
        raise WarmStartBlocked("study.evaluation.bootstrap_seed must be an integer")
    confidence = _finite_number(
        evaluation["confidence_level"], "study.evaluation.confidence_level"
    )
    if not 0.0 < confidence < 1.0:
        raise WarmStartBlocked(
            "study.evaluation.confidence_level must be between zero and one"
        )

    thresholds = _mapping(
        evaluation["thresholds"], "study.evaluation.thresholds"
    )
    agreement_fields = {
        "minimum_macro_category_action_agreement",
        "minimum_overall_action_agreement",
        "minimum_per_category_action_agreement",
    }
    _require_keys(
        thresholds,
        agreement_fields
        | {"floor_noninferiority_margin", "maximum_mean_floor_deficit"},
        "study.evaluation.thresholds",
    )
    for field in sorted(agreement_fields):
        threshold = _finite_number(
            thresholds[field], f"study.evaluation.thresholds.{field}"
        )
        if not 0.0 <= threshold <= 1.0:
            raise WarmStartBlocked(
                f"study.evaluation.thresholds.{field} must be in [0, 1]"
            )
    margin = _finite_number(
        thresholds["floor_noninferiority_margin"],
        "study.evaluation.thresholds.floor_noninferiority_margin",
    )
    mean_deficit = _finite_number(
        thresholds["maximum_mean_floor_deficit"],
        "study.evaluation.thresholds.maximum_mean_floor_deficit",
    )
    if margin < 0.0 or mean_deficit < 0.0:
        raise WarmStartBlocked("floor deficit thresholds must be non-negative")
    if mean_deficit > margin:
        raise WarmStartBlocked(
            "maximum_mean_floor_deficit must not exceed floor_noninferiority_margin"
        )
    evaluation["thresholds"] = thresholds
    return evaluation


def _validate_limits(
    value: object,
    *,
    cohorts: Mapping[str, Sequence[int]],
    optimizer: Mapping[str, Any],
) -> dict[str, Any]:
    limits = _mapping(value, "study.limits")
    integer_fields = {
        "max_decisions_per_episode",
        "max_demo_rows",
        "max_epochs",
        "max_final_policy_episodes",
        "max_total_policy_episodes",
        "max_train_episodes",
        "max_validation_policy_episodes",
    }
    _require_keys(
        limits, integer_fields | {"max_wall_seconds_per_execution"}, "study.limits"
    )
    for field in sorted(integer_fields):
        limits[field] = _positive_int(limits[field], f"study.limits.{field}")
    wall_seconds = _finite_number(
        limits["max_wall_seconds_per_execution"],
        "study.limits.max_wall_seconds_per_execution",
    )
    if wall_seconds <= 0.0:
        raise WarmStartBlocked(
            "study.limits.max_wall_seconds_per_execution must be positive"
        )
    required_train = len(cohorts["train_seeds"])
    required_validation = 2 * len(cohorts["validation_seeds"])
    required_final = 2 * len(cohorts["final_test_seeds"])
    if limits["max_train_episodes"] < required_train:
        raise WarmStartBlocked("study.limits.max_train_episodes is insufficient")
    if limits["max_validation_policy_episodes"] < required_validation:
        raise WarmStartBlocked(
            "study.limits.max_validation_policy_episodes is insufficient"
        )
    if limits["max_final_policy_episodes"] < required_final:
        raise WarmStartBlocked(
            "study.limits.max_final_policy_episodes is insufficient"
        )
    if limits["max_total_policy_episodes"] < (
        required_train + required_validation + required_final
    ):
        raise WarmStartBlocked(
            "study.limits.max_total_policy_episodes is insufficient"
        )
    if limits["max_epochs"] < optimizer["epochs"]:
        raise WarmStartBlocked("study.limits.max_epochs is insufficient")
    return limits


def _validate_execution(value: object) -> dict[str, Any]:
    execution = _mapping(value, "study.execution")
    expected = {
        "allow_alternate_cohort": False,
        "allow_model_selection": False,
        "allow_parameter_retry": False,
        "allow_test_on_validation_failure": False,
        "model_config_count": 1,
        "primary_count": 1,
        "replay_count": 1,
        "validation_is_stop_gate": True,
    }
    _require_keys(execution, set(expected), "study.execution")
    for field, expected_value in expected.items():
        _require_exact(execution, field, expected_value, "study.execution")
    return execution


def validate_warm_start_registration(value: object) -> dict[str, Any]:
    """Validate an immutable warm-start registration without adding defaults."""
    registration = _mapping(value, "registration")
    _require_keys(registration, {"identity", "schema_version", "study"}, "registration")
    if registration["schema_version"] != INPUT_SCHEMA_VERSION:
        raise WarmStartBlocked("registration schema_version mismatch")
    registration = copy.deepcopy(registration)
    registration["identity"] = _validate_identity(registration["identity"])

    study = _mapping(registration["study"], "study")
    _require_keys(
        study,
        {
            "ascension",
            "cohorts",
            "evaluation",
            "execution",
            "limits",
            "model",
            "optimizer",
        },
        "study",
    )
    _require_exact(study, "ascension", 0, "study")
    cohorts = _validate_cohorts(study["cohorts"])
    model = _validate_model(study["model"])
    optimizer = _validate_optimizer(study["optimizer"])
    evaluation = _validate_evaluation(study["evaluation"])
    limits = _validate_limits(study["limits"], cohorts=cohorts, optimizer=optimizer)
    execution = _validate_execution(study["execution"])
    study.update(
        cohorts=cohorts,
        model=model,
        optimizer=optimizer,
        evaluation=evaluation,
        limits=limits,
        execution=execution,
    )
    registration["study"] = study
    return registration


def _reject_duplicate_pairs(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise WarmStartBlocked(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_warm_start_registration(path: Path | str) -> dict[str, Any]:
    try:
        value = json.loads(
            Path(path).read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
        )
    except WarmStartBlocked:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise WarmStartBlocked(f"cannot load warm-start input {path}: {exc}") from exc
    return validate_warm_start_registration(value)
