"""Build a bounded SimpleAgent-anchored non-combat simulator warm start."""

from __future__ import annotations

import copy
import json
import math
import os
import random
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from numbers import Real
from pathlib import Path
from typing import Any

from analysis_scripts.noncombat_simulator_adapter import (
    NATIVE_TARGET_POLICY_ID,
    SOURCE_TYPE,
    TARGET_CATEGORIES,
    SimulatorAdapterError,
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
    validate_candidates,
    validate_native_baseline_action,
    validate_provenance,
    validate_snapshot,
)
from analysis_scripts.noncombat_simulator_policy_validity import (
    PolicyValidityBlocked,
    evaluate_native_policy,
)
from analysis_scripts.noncombat_simulator_training_smoke import (
    FEATURE_VERSION,
    SmokeBlocked,
    _candidate_features,
    _validate_binding,
    evaluate_greedy_policy,
    paired_bootstrap_interval,
    project_policy_view,
    simulator_training_reward,
)


INPUT_SCHEMA_VERSION = "noncombat-simulator-baseline-warm-start-input-v1"
DEMONSTRATION_SCHEMA_VERSION = "noncombat-simulator-native-demonstration-v1"
DATASET_SCHEMA_VERSION = "noncombat-simulator-native-demonstration-dataset-v1"
MODEL_SCHEMA_VERSION = "noncombat-simulator-baseline-warm-start-model-v1"
TEACHER_FIT_SCHEMA_VERSION = "noncombat-simulator-baseline-teacher-fit-v1"
ROLLOUT_SCHEMA_VERSION = "noncombat-simulator-baseline-rollouts-v1"
DEMONSTRATION_ARTIFACT_SCHEMA_VERSION = (
    "noncombat-simulator-baseline-demonstrations-artifact-v1"
)
MODEL_ARTIFACT_SCHEMA_VERSION = "noncombat-simulator-baseline-model-artifact-v1"
TRAJECTORY_ARTIFACT_SCHEMA_VERSION = (
    "noncombat-simulator-baseline-trajectories-artifact-v1"
)
METRICS_ARTIFACT_SCHEMA_VERSION = "noncombat-simulator-baseline-metrics-artifact-v1"
MANIFEST_SCHEMA_VERSION = "noncombat-simulator-baseline-manifest-v1"
JOURNAL_SCHEMA_VERSION = "noncombat-simulator-baseline-journal-v1"
MODEL_ARCHITECTURE = "candidate-ranker-mlp-v1"
CANONICAL_ARTIFACT_NAMES = (
    "artifact_manifest.json",
    "demonstrations.json",
    "metrics.json",
    "model.json",
    "report.md",
    "trajectories.json",
)
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


@dataclass(frozen=True)
class WarmStartTrainingResult:
    model: Any
    initial_model: dict[str, Any]
    final_model: dict[str, Any]
    history: tuple[dict[str, Any], ...]


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
    actual = value.get(field)
    if type(actual) is not type(expected) or actual != expected:
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


def _adapter_call(label: str, call: Callable[[], Any]) -> Any:
    try:
        return call()
    except WarmStartBlocked:
        raise
    except (KeyError, SimulatorAdapterError, TypeError, ValueError) as exc:
        raise WarmStartBlocked(f"{label}: {exc}") from exc


def _validate_cohort_name(value: object) -> str:
    if value not in {"train", "validation", "final_test"}:
        raise WarmStartBlocked("cohort must be train, validation, or final_test")
    return str(value)


def _validate_nonnegative_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise WarmStartBlocked(f"{label} must be a non-negative integer")
    return value


def build_demonstration_row(
    *,
    cohort: str,
    seed: int,
    decision_index: int,
    source_snapshot: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    target_action: Mapping[str, Any],
    transition: Mapping[str, Any],
) -> dict[str, Any]:
    """Build one canonical teacher row from an already executed native step."""
    cohort = _validate_cohort_name(cohort)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise WarmStartBlocked("demonstration seed must be an integer")
    decision_index = _validate_nonnegative_int(
        decision_index, "demonstration decision_index"
    )
    try:
        snapshot = validate_snapshot(copy.deepcopy(dict(source_snapshot)))
        if snapshot["terminal"] is not False or snapshot["category"] not in TARGET_CATEGORIES:
            raise WarmStartBlocked("demonstration source must be a target decision")
        normalized_candidates = validate_candidates(
            [copy.deepcopy(dict(candidate)) for candidate in candidates],
            category=snapshot["category"],
        )
        target_id = target_action.get("action_id")
        match_count = sum(
            candidate["action_id"] == target_id for candidate in normalized_candidates
        )
        if match_count != 1:
            raise WarmStartBlocked(
                f"native target maps to {match_count} current candidates"
            )
        teacher = validate_native_baseline_action(
            copy.deepcopy(dict(target_action)),
            category=snapshot["category"],
            candidates=normalized_candidates,
        )
        normalized_transition = copy.deepcopy(dict(transition))
        if normalized_transition.get("source_type") != SOURCE_TYPE:
            raise WarmStartBlocked("demonstration transition source_type mismatch")
        if normalized_transition.get("category") != snapshot["category"]:
            raise WarmStartBlocked("demonstration transition category mismatch")
        if normalized_transition.get("selected_action_id") != teacher["action_id"]:
            raise WarmStartBlocked("demonstration transition selected action mismatch")
        if canonical_json_bytes(normalized_transition.get("source_state")) != (
            canonical_json_bytes(snapshot["state"])
        ):
            raise WarmStartBlocked("demonstration transition source state mismatch")
        if canonical_json_bytes(normalized_transition.get("candidate_actions")) != (
            canonical_json_bytes(normalized_candidates)
        ):
            raise WarmStartBlocked("demonstration transition candidates mismatch")
        provenance = validate_provenance(normalized_transition.get("provenance"))
        successor = _mapping(
            normalized_transition.get("successor"), "demonstration transition successor"
        )
        if not isinstance(successor.get("terminal"), bool):
            raise WarmStartBlocked(
                "demonstration transition successor.terminal must be boolean"
            )
        _mapping(successor.get("state"), "demonstration transition successor.state")
    except SimulatorAdapterError as exc:
        raise WarmStartBlocked(f"invalid demonstration row: {exc}") from exc

    policy_views = []
    for candidate in normalized_candidates:
        view = project_policy_view(snapshot["state"], candidate)
        policy_views.append(
            {
                "action_id": candidate["action_id"],
                "policy_view": view,
                "sha256": sha256_bytes(canonical_json_bytes(view)),
            }
        )
    return {
        "candidate_actions": normalized_candidates,
        "candidate_actions_sha256": sha256_bytes(
            canonical_json_bytes(normalized_candidates)
        ),
        "category": snapshot["category"],
        "cohort": cohort,
        "decision_index": decision_index,
        "policy_views": policy_views,
        "provenance": provenance,
        "schema_version": DEMONSTRATION_SCHEMA_VERSION,
        "seed": seed,
        "source_snapshot": snapshot,
        "source_snapshot_sha256": sha256_bytes(canonical_json_bytes(snapshot)),
        "source_type": SOURCE_TYPE,
        "successor": successor,
        "teacher": teacher,
    }


def build_demonstration_dataset(
    *,
    cohort: str,
    seeds: Sequence[int],
    rows: Sequence[Mapping[str, Any]],
    episodes: Sequence[Mapping[str, Any]],
    required_categories: Sequence[str] = TARGET_CATEGORIES,
) -> dict[str, Any]:
    """Validate and package canonical teacher rows for one cohort."""
    cohort = _validate_cohort_name(cohort)
    normalized_seeds = _seed_array(seeds, "demonstration seeds")
    normalized_rows = [copy.deepcopy(dict(row)) for row in rows]
    normalized_episodes = [copy.deepcopy(dict(episode)) for episode in episodes]
    if [episode.get("seed") for episode in normalized_episodes] != normalized_seeds:
        raise WarmStartBlocked("demonstration episode seeds mismatch")
    row_seeds = {seed: [] for seed in normalized_seeds}
    categories: set[str] = set()
    for row in normalized_rows:
        if row.get("schema_version") != DEMONSTRATION_SCHEMA_VERSION:
            raise WarmStartBlocked("demonstration row schema mismatch")
        if row.get("cohort") != cohort:
            raise WarmStartBlocked("demonstration row cohort mismatch")
        seed = row.get("seed")
        if seed not in row_seeds:
            raise WarmStartBlocked("demonstration row seed is outside cohort")
        row_seeds[seed].append(row)
        category = row.get("category")
        if category not in TARGET_CATEGORIES:
            raise WarmStartBlocked("demonstration row category mismatch")
        categories.add(category)
    for seed, seed_rows in row_seeds.items():
        if not seed_rows:
            raise WarmStartBlocked(f"demonstration seed {seed} has no rows")
        indices = [row.get("decision_index") for row in seed_rows]
        if indices != list(range(len(seed_rows))):
            raise WarmStartBlocked(
                f"demonstration seed {seed} decision indices are not contiguous"
            )
    required = set(required_categories)
    if not required.issubset(TARGET_CATEGORIES):
        raise WarmStartBlocked("required demonstration category is unsupported")
    missing = sorted(required - categories)
    if missing:
        raise WarmStartBlocked(
            "demonstration dataset missing categories: " + ", ".join(missing)
        )
    return {
        "all_categories": sorted(categories),
        "cohort": cohort,
        "episodes": normalized_episodes,
        "row_count": len(normalized_rows),
        "rows": normalized_rows,
        "schema_version": DATASET_SCHEMA_VERSION,
        "seeds": normalized_seeds,
        "source_type": SOURCE_TYPE,
        "teacher_policy_id": NATIVE_TARGET_POLICY_ID,
    }


def _check_deadline(clock: Callable[[], float], deadline: float, label: str) -> None:
    now = _finite_number(clock(), "clock value")
    if now > deadline:
        raise WarmStartBlocked(f"{label} exceeded wall-time bound")


def collect_native_demonstrations(
    *,
    environment_factory: Callable[[int], Any],
    cohort: str,
    seeds: Sequence[int],
    max_decisions_per_episode: int,
    max_demo_rows: int,
    max_episodes: int,
    deadline: float,
    clock: Callable[[], float],
    required_categories: Sequence[str] = TARGET_CATEGORIES,
) -> dict[str, Any]:
    """Follow native SimpleAgent and collect a deterministic cohort dataset."""
    cohort = _validate_cohort_name(cohort)
    normalized_seeds = _seed_array(seeds, "demonstration seeds")
    max_decisions_per_episode = _positive_int(
        max_decisions_per_episode, "max_decisions_per_episode"
    )
    max_demo_rows = _positive_int(max_demo_rows, "max_demo_rows")
    max_episodes = _positive_int(max_episodes, "max_episodes")
    deadline = _finite_number(deadline, "deadline")
    if len(normalized_seeds) > max_episodes:
        raise WarmStartBlocked("demonstration cohort exceeds max_episodes")

    rows: list[dict[str, Any]] = []
    episodes: list[dict[str, Any]] = []
    for seed in normalized_seeds:
        _check_deadline(clock, deadline, "demonstration collection")
        environment = environment_factory(seed)
        episode_rows: list[dict[str, Any]] = []
        while True:
            _check_deadline(clock, deadline, "demonstration collection")
            snapshot = _adapter_call("invalid demonstration snapshot", environment.snapshot)
            try:
                snapshot = validate_snapshot(snapshot)
            except SimulatorAdapterError as exc:
                raise WarmStartBlocked(f"invalid demonstration snapshot: {exc}") from exc
            if snapshot["terminal"]:
                break
            if len(episode_rows) >= max_decisions_per_episode:
                raise WarmStartBlocked(
                    f"seed {seed} exceeded max_decisions_per_episode"
                )
            if len(rows) >= max_demo_rows:
                raise WarmStartBlocked("demonstration collection exceeded max_demo_rows")
            candidates = _adapter_call(
                "invalid demonstration candidates", environment.legal_actions
            )
            source_bytes = canonical_json_bytes(snapshot)
            candidate_bytes = canonical_json_bytes(candidates)
            target = _adapter_call(
                "invalid native target query", environment.native_baseline_action
            )
            after_query = _adapter_call(
                "invalid post-query snapshot", environment.snapshot
            )
            after_candidates = _adapter_call(
                "invalid post-query candidates", environment.legal_actions
            )
            if (
                canonical_json_bytes(after_query) != source_bytes
                or canonical_json_bytes(after_candidates) != candidate_bytes
            ):
                raise WarmStartBlocked("native target query mutated source")
            target_id = target.get("action_id") if isinstance(target, Mapping) else None
            match_count = sum(
                isinstance(candidate, Mapping)
                and candidate.get("action_id") == target_id
                for candidate in candidates
            )
            if match_count != 1:
                raise WarmStartBlocked(
                    f"native target maps to {match_count} current candidates"
                )
            transition = _adapter_call(
                "native baseline step failed", environment.step_native_baseline
            )
            row = build_demonstration_row(
                cohort=cohort,
                seed=seed,
                decision_index=len(episode_rows),
                source_snapshot=snapshot,
                candidates=candidates,
                target_action=target,
                transition=transition,
            )
            rows.append(row)
            episode_rows.append(row)

        terminal_state = _mapping(
            snapshot.get("state"), f"seed {seed} terminal snapshot.state"
        )
        outcome = terminal_state.get("outcome")
        if outcome not in {"player_loss", "player_victory"}:
            raise WarmStartBlocked(f"seed {seed} did not produce a terminal outcome")
        floor = _finite_number(terminal_state.get("floor"), f"seed {seed} terminal floor")
        action_ids = [row["teacher"]["action_id"] for row in episode_rows]
        episodes.append(
            {
                "action_sequence_sha256": sha256_bytes(
                    canonical_json_bytes(action_ids)
                ),
                "categories": sorted({row["category"] for row in episode_rows}),
                "decisions": len(episode_rows),
                "outcome": outcome,
                "row_sha256s": [
                    sha256_bytes(canonical_json_bytes(row)) for row in episode_rows
                ],
                "seed": seed,
                "selected_action_ids": action_ids,
                "terminal_floor": floor,
            }
        )

    return build_demonstration_dataset(
        cohort=cohort,
        seeds=normalized_seeds,
        rows=rows,
        episodes=episodes,
        required_categories=required_categories,
    )


def _demonstration_transition(row: Mapping[str, Any]) -> dict[str, Any]:
    snapshot = _mapping(row.get("source_snapshot"), "demonstration source_snapshot")
    teacher = _mapping(row.get("teacher"), "demonstration teacher")
    return {
        "candidate_actions": copy.deepcopy(row.get("candidate_actions")),
        "category": row.get("category"),
        "provenance": copy.deepcopy(row.get("provenance")),
        "selected_action_id": teacher.get("action_id"),
        "source_state": copy.deepcopy(snapshot.get("state")),
        "source_type": SOURCE_TYPE,
        "successor": copy.deepcopy(row.get("successor")),
    }


def native_policy_from_demonstrations(
    dataset: Mapping[str, Any],
) -> dict[str, Any]:
    """Reconstruct validated native rollout evidence without a second episode."""
    value = _mapping(dataset, "demonstration dataset")
    cohort = _validate_cohort_name(value.get("cohort"))
    seeds = _seed_array(value.get("seeds"), "demonstration seeds")
    rows_value = value.get("rows")
    episodes_value = value.get("episodes")
    if not isinstance(rows_value, list) or not isinstance(episodes_value, list):
        raise WarmStartBlocked("demonstration rows and episodes must be arrays")
    normalized = build_demonstration_dataset(
        cohort=cohort,
        seeds=seeds,
        rows=rows_value,
        episodes=episodes_value,
        required_categories=TARGET_CATEGORIES,
    )
    if canonical_json_bytes(normalized) != canonical_json_bytes(value):
        raise WarmStartBlocked("demonstration dataset canonical identity mismatch")

    rows_by_seed = {seed: [] for seed in seeds}
    for row_value in normalized["rows"]:
        row = _mapping(row_value, "demonstration row")
        transition = _demonstration_transition(row)
        rebuilt = build_demonstration_row(
            cohort=cohort,
            seed=row.get("seed"),
            decision_index=row.get("decision_index"),
            source_snapshot=_mapping(
                row.get("source_snapshot"), "demonstration source_snapshot"
            ),
            candidates=row.get("candidate_actions"),
            target_action=_mapping(row.get("teacher"), "demonstration teacher"),
            transition=transition,
        )
        if canonical_json_bytes(rebuilt) != canonical_json_bytes(row):
            raise WarmStartBlocked("demonstration row canonical identity mismatch")
        rows_by_seed[row["seed"]].append((row, transition))

    policy_rows = []
    for episode_value in normalized["episodes"]:
        episode = _mapping(episode_value, "demonstration episode")
        seed = episode.get("seed")
        seed_rows = rows_by_seed.get(seed)
        if not seed_rows:
            raise WarmStartBlocked("demonstration episode has no matching rows")
        for index in range(1, len(seed_rows)):
            previous = seed_rows[index - 1][0]
            current = seed_rows[index][0]
            previous_successor = _mapping(
                previous.get("successor"), "demonstration successor"
            )
            current_snapshot = _mapping(
                current.get("source_snapshot"), "demonstration source_snapshot"
            )
            if previous_successor.get("terminal") is not False or (
                canonical_json_bytes(previous_successor.get("state"))
                != canonical_json_bytes(current_snapshot.get("state"))
                or previous_successor.get("category") != current_snapshot.get("category")
            ):
                raise WarmStartBlocked("demonstration episode transition chain mismatch")
        last_successor = _mapping(
            seed_rows[-1][0].get("successor"), "demonstration final successor"
        )
        terminal_state = _mapping(
            last_successor.get("state"), "demonstration final successor.state"
        )
        if last_successor.get("terminal") is not True:
            raise WarmStartBlocked("demonstration episode does not end at terminal")
        if terminal_state.get("outcome") not in {"player_loss", "player_victory"}:
            raise WarmStartBlocked("demonstration episode terminal outcome mismatch")
        terminal_floor = _finite_number(
            terminal_state.get("floor"), "demonstration terminal floor"
        )

        action_rows = []
        for row, transition in seed_rows:
            teacher = _mapping(row.get("teacher"), "demonstration teacher")
            try:
                reward = simulator_training_reward(transition)
            except SmokeBlocked as exc:
                raise WarmStartBlocked(f"invalid demonstration reward: {exc}") from exc
            action_rows.append(
                {
                    "action_id": teacher["action_id"],
                    "category": row["category"],
                    "decision": row["decision_index"],
                    "native_action_sha256": sha256_bytes(
                        canonical_json_bytes(teacher)
                    ),
                    "reward": reward,
                }
            )
        selected_action_ids = [row["action_id"] for row in action_rows]
        expected_episode = {
            "action_sequence_sha256": sha256_bytes(
                canonical_json_bytes(selected_action_ids)
            ),
            "categories": sorted({row["category"] for row, _ in seed_rows}),
            "decisions": len(seed_rows),
            "outcome": terminal_state.get("outcome"),
            "row_sha256s": [
                sha256_bytes(canonical_json_bytes(row)) for row, _ in seed_rows
            ],
            "seed": seed,
            "selected_action_ids": selected_action_ids,
            "terminal_floor": terminal_floor,
        }
        if canonical_json_bytes(expected_episode) != canonical_json_bytes(episode):
            raise WarmStartBlocked("demonstration episode canonical identity mismatch")
        policy_rows.append(
            {
                "action_sequence_sha256": sha256_bytes(
                    canonical_json_bytes(action_rows)
                ),
                "candidate_legality": True,
                "categories": expected_episode["categories"],
                "decisions": expected_episode["decisions"],
                "native_action_sha256s": [
                    row["native_action_sha256"] for row in action_rows
                ],
                "outcome": expected_episode["outcome"],
                "seed": seed,
                "selected_action_ids": selected_action_ids,
                "terminal_floor": float(expected_episode["terminal_floor"]),
                "total_reward": sum(row["reward"] for row in action_rows),
            }
        )
    return {
        "all_categories": normalized["all_categories"],
        "candidate_legality": True,
        "policy_id": NATIVE_TARGET_POLICY_ID,
        "rows": policy_rows,
        "terminal_outcomes": all(
            row["outcome"] in {"player_loss", "player_victory"}
            for row in policy_rows
        ),
    }


_WARM_START_MODEL_CLASS: type | None = None


def _torch_module():
    import torch

    return torch


def _warm_start_model_class():
    global _WARM_START_MODEL_CLASS
    if _WARM_START_MODEL_CLASS is None:
        torch = _torch_module()

        class WarmStartCandidateRanker(torch.nn.Module):
            def __init__(self, input_dim: int, hidden_dim: int) -> None:
                super().__init__()
                self.hidden = torch.nn.Linear(input_dim, hidden_dim)
                self.scorer = torch.nn.Linear(hidden_dim, 1)

            def forward(self, candidate_features):
                hidden = torch.relu(self.hidden(candidate_features))
                return self.scorer(hidden).squeeze(-1)

        _WARM_START_MODEL_CLASS = WarmStartCandidateRanker
    return _WARM_START_MODEL_CLASS


def _ensure_finite_tensor(value: Any, label: str) -> None:
    torch = _torch_module()
    if not torch.isfinite(value).all().item():
        raise WarmStartBlocked(f"non-finite {label}")


def _ensure_finite_model(model: Any) -> None:
    for name, tensor in model.state_dict().items():
        _ensure_finite_tensor(tensor, f"model tensor {name}")


def build_warm_start_model(
    *, hash_dim: int, hidden_dim: int, model_seed: int
) -> Any:
    """Create the deterministic CPU-only v1 MLP with gradients enabled."""
    hash_dim = _positive_int(hash_dim, "hash_dim")
    hidden_dim = _positive_int(hidden_dim, "hidden_dim")
    if model_seed != 0:
        raise WarmStartBlocked("model_seed must equal 0")
    torch = _torch_module()
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    random.seed(model_seed)
    torch.manual_seed(model_seed)
    model_class = _warm_start_model_class()
    model = model_class(hash_dim, hidden_dim)
    if next(model.parameters()).device.type != "cpu":
        raise WarmStartBlocked("warm-start model must remain on CPU")
    _ensure_finite_model(model)
    return model


def canonical_warm_start_model_payload(model: Any) -> dict[str, Any]:
    """Serialize the warm-start MLP without platform or archive metadata."""
    if not hasattr(model, "hidden") or not hasattr(model, "scorer"):
        raise WarmStartBlocked("warm-start model architecture mismatch")
    input_dim = getattr(model.hidden, "in_features", None)
    hidden_dim = getattr(model.hidden, "out_features", None)
    if (
        isinstance(input_dim, bool)
        or not isinstance(input_dim, int)
        or isinstance(hidden_dim, bool)
        or not isinstance(hidden_dim, int)
        or model.scorer.in_features != hidden_dim
        or model.scorer.out_features != 1
    ):
        raise WarmStartBlocked("warm-start model dimensions are invalid")
    state_dict: dict[str, Any] = {}
    for name, tensor in sorted(model.state_dict().items()):
        value = tensor.detach().to(device="cpu").contiguous()
        _ensure_finite_tensor(value, f"model tensor {name}")
        state_dict[name] = {
            "dtype": str(value.dtype).removeprefix("torch."),
            "shape": list(value.shape),
            "values": [float(item).hex() for item in value.reshape(-1).tolist()],
        }
    return {
        "architecture": MODEL_ARCHITECTURE,
        "hidden_dim": hidden_dim,
        "input_dim": input_dim,
        "schema_version": MODEL_SCHEMA_VERSION,
        "state_dict": state_dict,
    }


def load_warm_start_model(
    payload: Mapping[str, Any], *, expected_hash_dim: int, expected_hidden_dim: int
) -> Any:
    """Load and freeze one canonical v1 MLP, rejecting any noncanonical value."""
    expected_hash_dim = _positive_int(expected_hash_dim, "expected_hash_dim")
    expected_hidden_dim = _positive_int(expected_hidden_dim, "expected_hidden_dim")
    value = _mapping(payload, "warm-start model")
    _require_keys(
        value,
        {"architecture", "hidden_dim", "input_dim", "schema_version", "state_dict"},
        "warm-start model",
    )
    _require_exact(value, "architecture", MODEL_ARCHITECTURE, "warm-start model")
    _require_exact(value, "schema_version", MODEL_SCHEMA_VERSION, "warm-start model")
    _require_exact(value, "input_dim", expected_hash_dim, "warm-start model")
    _require_exact(value, "hidden_dim", expected_hidden_dim, "warm-start model")
    expected_shapes = {
        "hidden.bias": [expected_hidden_dim],
        "hidden.weight": [expected_hidden_dim, expected_hash_dim],
        "scorer.bias": [1],
        "scorer.weight": [1, expected_hidden_dim],
    }
    state = _mapping(value["state_dict"], "warm-start model.state_dict")
    _require_keys(state, set(expected_shapes), "warm-start model.state_dict")
    torch = _torch_module()
    tensors = {}
    for name, shape in expected_shapes.items():
        entry = _mapping(state[name], f"warm-start model.state_dict.{name}")
        _require_keys(
            entry, {"dtype", "shape", "values"},
            f"warm-start model.state_dict.{name}"
        )
        if entry["dtype"] != "float32" or entry["shape"] != shape:
            raise WarmStartBlocked(f"warm-start model tensor {name} metadata mismatch")
        raw_values = entry["values"]
        expected_count = math.prod(shape)
        if not isinstance(raw_values, list) or len(raw_values) != expected_count:
            raise WarmStartBlocked(f"warm-start model tensor {name} value count mismatch")
        parsed = []
        for raw in raw_values:
            if not isinstance(raw, str):
                raise WarmStartBlocked(f"warm-start model tensor {name} value is invalid")
            try:
                numeric = float.fromhex(raw)
            except ValueError as exc:
                raise WarmStartBlocked(
                    f"warm-start model tensor {name} value is invalid"
                ) from exc
            if not math.isfinite(numeric):
                raise WarmStartBlocked(
                    f"warm-start model tensor {name} values must be finite"
                )
            parsed.append(numeric)
        tensors[name] = torch.tensor(parsed, dtype=torch.float32).reshape(shape)

    model = build_warm_start_model(
        hash_dim=expected_hash_dim, hidden_dim=expected_hidden_dim, model_seed=0
    )
    model.load_state_dict(tensors, strict=True)
    model.requires_grad_(False)
    model.eval()
    if canonical_warm_start_model_payload(model) != copy.deepcopy(value):
        raise WarmStartBlocked("warm-start model canonical round trip mismatch")
    return model


def _validated_training_rows(
    dataset: Mapping[str, Any], *, hash_dim: int
) -> list[dict[str, Any]]:
    value = _mapping(dataset, "demonstration dataset")
    if value.get("schema_version") != DATASET_SCHEMA_VERSION:
        raise WarmStartBlocked("demonstration dataset schema mismatch")
    if value.get("source_type") != SOURCE_TYPE:
        raise WarmStartBlocked("demonstration dataset source_type mismatch")
    if value.get("teacher_policy_id") != NATIVE_TARGET_POLICY_ID:
        raise WarmStartBlocked("demonstration dataset teacher policy mismatch")
    if value.get("all_categories") != list(TARGET_CATEGORIES):
        raise WarmStartBlocked("training dataset must cover all target categories")
    rows_value = value.get("rows")
    if not isinstance(rows_value, list) or not rows_value:
        raise WarmStartBlocked("training dataset rows must be nonempty")
    rows = [copy.deepcopy(dict(_mapping(row, "demonstration row"))) for row in rows_value]
    ordering = [(row.get("seed"), row.get("decision_index")) for row in rows]
    if ordering != sorted(ordering):
        raise WarmStartBlocked("training demonstration rows must be deterministically ordered")
    for row in rows:
        if row.get("schema_version") != DEMONSTRATION_SCHEMA_VERSION:
            raise WarmStartBlocked("training demonstration row schema mismatch")
        try:
            snapshot = validate_snapshot(row.get("source_snapshot"))
            candidates = validate_candidates(
                row.get("candidate_actions"), category=snapshot["category"]
            )
            target = validate_native_baseline_action(
                row.get("teacher"), category=snapshot["category"], candidates=candidates
            )
        except SimulatorAdapterError as exc:
            raise WarmStartBlocked(f"invalid training demonstration row: {exc}") from exc
        policy_views = row.get("policy_views")
        if not isinstance(policy_views, list) or len(policy_views) != len(candidates):
            raise WarmStartBlocked("training policy view count mismatch")
        for candidate, entry_value in zip(candidates, policy_views, strict=True):
            entry = _mapping(entry_value, "training policy view")
            view = project_policy_view(snapshot["state"], candidate)
            if entry.get("action_id") != candidate["action_id"]:
                raise WarmStartBlocked("training policy view action mismatch")
            if canonical_json_bytes(entry.get("policy_view")) != canonical_json_bytes(view):
                raise WarmStartBlocked("training policy view mismatch")
            if entry.get("sha256") != sha256_bytes(canonical_json_bytes(view)):
                raise WarmStartBlocked("training policy view hash mismatch")
        features = _candidate_features(snapshot["state"], candidates, hash_dim=hash_dim)
        _ensure_finite_tensor(features, "training candidate features")
        target_ids = [candidate["action_id"] for candidate in candidates]
        row["_category"] = snapshot["category"]
        row["_features"] = features
        row["_target_index"] = target_ids.index(target["action_id"])
    return rows


def _validate_training_parameters(
    *,
    epochs: int,
    learning_rate: float,
    betas: Sequence[float],
    epsilon: float,
    weight_decay: float,
) -> tuple[int, float, tuple[float, float], float]:
    epochs = _positive_int(epochs, "epochs")
    learning_rate = _finite_number(learning_rate, "learning_rate")
    epsilon = _finite_number(epsilon, "epsilon")
    weight_decay = _finite_number(weight_decay, "weight_decay")
    if not 0.0 < learning_rate <= 1.0:
        raise WarmStartBlocked("learning_rate must be in (0, 1]")
    if epsilon <= 0.0:
        raise WarmStartBlocked("epsilon must be positive")
    if weight_decay != 0.0:
        raise WarmStartBlocked("weight_decay must equal 0.0")
    if not isinstance(betas, Sequence) or isinstance(betas, (str, bytes)) or len(betas) != 2:
        raise WarmStartBlocked("betas must contain two values")
    parsed_betas = tuple(_finite_number(value, "beta") for value in betas)
    if any(not 0.0 <= value < 1.0 for value in parsed_betas):
        raise WarmStartBlocked("betas must be in [0, 1)")
    return epochs, learning_rate, parsed_betas, epsilon


def train_warm_start_ranker(
    dataset: Mapping[str, Any],
    *,
    hash_dim: int,
    hidden_dim: int,
    model_seed: int,
    epochs: int,
    learning_rate: float,
    betas: Sequence[float],
    epsilon: float,
    weight_decay: float,
) -> WarmStartTrainingResult:
    """Train the one fixed category-balanced supervised warm-start ranker."""
    hash_dim = _positive_int(hash_dim, "hash_dim")
    hidden_dim = _positive_int(hidden_dim, "hidden_dim")
    epochs, learning_rate, parsed_betas, epsilon = _validate_training_parameters(
        epochs=epochs,
        learning_rate=learning_rate,
        betas=betas,
        epsilon=epsilon,
        weight_decay=weight_decay,
    )
    rows = _validated_training_rows(dataset, hash_dim=hash_dim)
    grouped = {
        category: [row for row in rows if row["_category"] == category]
        for category in TARGET_CATEGORIES
    }
    if any(not category_rows for category_rows in grouped.values()):
        raise WarmStartBlocked("training dataset must contain every target category")

    torch = _torch_module()
    model = build_warm_start_model(
        hash_dim=hash_dim, hidden_dim=hidden_dim, model_seed=model_seed
    )
    initial_model = canonical_warm_start_model_payload(model)
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=learning_rate,
        betas=parsed_betas,
        eps=epsilon,
        weight_decay=weight_decay,
    )
    history: list[dict[str, Any]] = []
    category_count = float(len(TARGET_CATEGORIES))
    for epoch in range(1, epochs + 1):
        model.train()
        optimizer.zero_grad(set_to_none=True)
        category_losses: dict[str, float] = {}
        for category in TARGET_CATEGORIES:
            category_rows = grouped[category]
            row_loss_values = []
            row_count = float(len(category_rows))
            for row in category_rows:
                logits = model(row["_features"])
                _ensure_finite_tensor(logits, "training logits")
                target = torch.tensor(
                    [row["_target_index"]], dtype=torch.long, device="cpu"
                )
                loss = torch.nn.functional.cross_entropy(logits.unsqueeze(0), target)
                _ensure_finite_tensor(loss, "training loss")
                (loss / (category_count * row_count)).backward()
                row_loss_values.append(float(loss.detach().item()))
            category_losses[category] = sum(row_loss_values) / len(row_loss_values)
        for name, parameter in model.named_parameters():
            if parameter.grad is None:
                raise WarmStartBlocked(f"missing model gradient: {name}")
            _ensure_finite_tensor(parameter.grad, f"model gradient {name}")
        optimizer.step()
        _ensure_finite_model(model)
        history.append(
            {
                "category_losses": category_losses,
                "category_row_counts": {
                    category: len(grouped[category]) for category in TARGET_CATEGORIES
                },
                "epoch": epoch,
                "loss": sum(category_losses.values()) / len(category_losses),
            }
        )
    optimizer.zero_grad(set_to_none=True)
    model.requires_grad_(False)
    model.eval()
    final_model = canonical_warm_start_model_payload(model)
    return WarmStartTrainingResult(
        model=model,
        initial_model=initial_model,
        final_model=final_model,
        history=tuple(history),
    )


def predict_warm_start_action(
    model: Any,
    *,
    snapshot: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    hash_dim: int,
) -> dict[str, Any]:
    """Score the complete current candidate set without teacher fallback."""
    hash_dim = _positive_int(hash_dim, "hash_dim")
    try:
        normalized_snapshot = validate_snapshot(snapshot)
        if normalized_snapshot["terminal"]:
            raise WarmStartBlocked("cannot score a terminal snapshot")
        normalized_candidates = validate_candidates(
            list(candidates), category=normalized_snapshot["category"]
        )
    except SimulatorAdapterError as exc:
        raise WarmStartBlocked(f"invalid warm-start prediction input: {exc}") from exc
    if not hasattr(model, "hidden") or model.hidden.in_features != hash_dim:
        raise WarmStartBlocked("prediction model input dimension mismatch")
    if next(model.parameters()).device.type != "cpu":
        raise WarmStartBlocked("prediction model must remain on CPU")
    _ensure_finite_model(model)
    features = _candidate_features(
        normalized_snapshot["state"], normalized_candidates, hash_dim=hash_dim
    )
    torch = _torch_module()
    model.eval()
    with torch.no_grad():
        logits = model(features)
        probabilities = torch.softmax(logits, dim=0)
    _ensure_finite_tensor(logits, "prediction logits")
    _ensure_finite_tensor(probabilities, "prediction probabilities")
    selected_index = int(torch.argmax(probabilities).item())
    candidate_ids = [candidate["action_id"] for candidate in normalized_candidates]
    return {
        "candidate_action_ids": candidate_ids,
        "probabilities": [float(value) for value in probabilities.tolist()],
        "scores": [float(value) for value in logits.tolist()],
        "selected_action_id": candidate_ids[selected_index],
    }


def evaluate_teacher_fit(
    model: Any, *, dataset: Mapping[str, Any], hash_dim: int
) -> dict[str, Any]:
    """Measure frozen-model agreement on independent baseline-following states."""
    rows = _validated_training_rows(dataset, hash_dim=hash_dim)
    result_rows = []
    category_values = {category: [] for category in TARGET_CATEGORIES}
    for row in rows:
        prediction = predict_warm_start_action(
            model,
            snapshot=row["source_snapshot"],
            candidates=row["candidate_actions"],
            hash_dim=hash_dim,
        )
        target_id = row["teacher"]["action_id"]
        target_index = prediction["candidate_action_ids"].index(target_id)
        target_probability = prediction["probabilities"][target_index]
        if not math.isfinite(target_probability) or not 0.0 < target_probability <= 1.0:
            raise WarmStartBlocked("teacher target probability must be finite and positive")
        cross_entropy = -math.log(target_probability)
        correct = prediction["selected_action_id"] == target_id
        category = row["category"]
        category_values[category].append((correct, cross_entropy))
        result_rows.append(
            {
                "candidate_action_ids": prediction["candidate_action_ids"],
                "category": category,
                "correct": correct,
                "cross_entropy": cross_entropy,
                "decision_index": row["decision_index"],
                "predicted_action_id": prediction["selected_action_id"],
                "seed": row["seed"],
                "target_action_id": target_id,
                "target_probability": target_probability,
            }
        )
    by_category = {}
    for category in TARGET_CATEGORIES:
        values = category_values[category]
        if not values:
            raise WarmStartBlocked(f"teacher fit is missing category {category}")
        by_category[category] = {
            "action_agreement": sum(correct for correct, _ in values) / len(values),
            "mean_cross_entropy": sum(loss for _, loss in values) / len(values),
            "row_count": len(values),
        }
    overall_agreement = sum(row["correct"] for row in result_rows) / len(result_rows)
    overall_cross_entropy = sum(row["cross_entropy"] for row in result_rows) / len(
        result_rows
    )
    finite_metrics = all(
        math.isfinite(float(value))
        for value in (
            overall_agreement,
            overall_cross_entropy,
            *(entry["action_agreement"] for entry in by_category.values()),
            *(entry["mean_cross_entropy"] for entry in by_category.values()),
        )
    )
    return {
        "by_category": by_category,
        "checks": {
            "candidate_legality": all(
                row["predicted_action_id"] in row["candidate_action_ids"]
                for row in result_rows
            ),
            "finite_metrics": finite_metrics,
            "four_category_coverage": set(by_category) == set(TARGET_CATEGORIES),
        },
        "macro_category_action_agreement": sum(
            entry["action_agreement"] for entry in by_category.values()
        )
        / len(by_category),
        "overall_action_agreement": overall_agreement,
        "overall_cross_entropy": overall_cross_entropy,
        "row_count": len(result_rows),
        "rows": result_rows,
        "schema_version": TEACHER_FIT_SCHEMA_VERSION,
    }


def _rollout_rows_by_seed(
    policy: Mapping[str, Any], *, label: str
) -> dict[int, Mapping[str, Any]]:
    rows = policy.get("rows")
    if not isinstance(rows, list):
        raise WarmStartBlocked(f"{label}.rows must be an array")
    result = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise WarmStartBlocked(f"{label} row must be an object")
        seed = row.get("seed")
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise WarmStartBlocked(f"{label} row seed is invalid")
        if seed in result:
            raise WarmStartBlocked(f"{label} has duplicate seed {seed}")
        result[seed] = row
    return result


def _paired_rollout_comparison(
    candidate: Mapping[str, Any],
    native: Mapping[str, Any],
    *,
    seeds: Sequence[int],
    bootstrap_seed: int,
    bootstrap_resamples: int,
    confidence_level: float,
) -> dict[str, Any]:
    candidate_rows = _rollout_rows_by_seed(candidate, label="candidate policy")
    native_rows = _rollout_rows_by_seed(native, label="native policy")
    paired_rows = []
    for seed in seeds:
        if seed not in candidate_rows or seed not in native_rows:
            raise WarmStartBlocked(f"rollout comparison is missing paired seed {seed}")
        candidate_row = candidate_rows[seed]
        native_row = native_rows[seed]
        paired_rows.append(
            {
                "candidate_outcome": candidate_row["outcome"],
                "candidate_terminal_floor": candidate_row["terminal_floor"],
                "floor_difference": candidate_row["terminal_floor"]
                - native_row["terminal_floor"],
                "native_outcome": native_row["outcome"],
                "native_terminal_floor": native_row["terminal_floor"],
                "seed": seed,
                "victory_difference": int(
                    candidate_row["outcome"] == "player_victory"
                )
                - int(native_row["outcome"] == "player_victory"),
            }
        )
    try:
        interval = paired_bootstrap_interval(
            [row["floor_difference"] for row in paired_rows],
            seed=bootstrap_seed,
            resamples=bootstrap_resamples,
            confidence_level=confidence_level,
        )
    except (SimulatorAdapterError, SmokeBlocked) as exc:
        raise WarmStartBlocked(str(exc)) from exc
    return {
        "comparison_id": "candidate_minus_native_simple_agent",
        "floor_difference_ci": interval,
        "paired_rows": paired_rows,
    }


def evaluate_warm_start_rollouts(
    model: Any,
    *,
    environment_factory: Callable[[int], Any],
    seeds: Sequence[int],
    hash_dim: int,
    max_decisions_per_episode: int,
    max_episodes: int,
    max_wall_seconds: float,
    bootstrap_seed: int,
    bootstrap_resamples: int,
    confidence_level: float,
    clock: Callable[[], float],
    native_demonstrations: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compare one frozen candidate with native SimpleAgent on paired seeds."""
    normalized_seeds = _seed_array(seeds, "rollout seeds")
    hash_dim = _positive_int(hash_dim, "hash_dim")
    max_decisions_per_episode = _positive_int(
        max_decisions_per_episode, "max_decisions_per_episode"
    )
    max_episodes = _positive_int(max_episodes, "max_episodes")
    bootstrap_resamples = _positive_int(bootstrap_resamples, "bootstrap_resamples")
    max_wall_seconds = _finite_number(max_wall_seconds, "max_wall_seconds")
    confidence_level = _finite_number(confidence_level, "confidence_level")
    if max_wall_seconds <= 0.0:
        raise WarmStartBlocked("max_wall_seconds must be positive")
    if max_episodes < 2 * len(normalized_seeds):
        raise WarmStartBlocked("max_episodes does not cover paired rollout policies")
    if isinstance(bootstrap_seed, bool) or not isinstance(bootstrap_seed, int):
        raise WarmStartBlocked("bootstrap_seed must be an integer")
    if not 0.0 < confidence_level < 1.0:
        raise WarmStartBlocked("confidence_level must be between zero and one")
    if any(parameter.requires_grad for parameter in model.parameters()):
        raise WarmStartBlocked("rollout model must be frozen")
    _ensure_finite_model(model)

    model_before = sha256_bytes(
        canonical_json_bytes(canonical_warm_start_model_payload(model))
    )
    started = _finite_number(clock(), "clock value")
    deadline = started + max_wall_seconds
    torch = _torch_module()
    native = None
    if native_demonstrations is not None:
        native = native_policy_from_demonstrations(native_demonstrations)
        if [row.get("seed") for row in native["rows"]] != normalized_seeds:
            raise WarmStartBlocked("native demonstration rollout seeds mismatch")
    try:
        with torch.inference_mode():
            candidate = evaluate_greedy_policy(
                model,
                environment_factory=environment_factory,
                seeds=normalized_seeds,
                hash_dim=hash_dim,
                max_decisions_per_episode=max_decisions_per_episode,
                deadline=deadline,
                clock=clock,
            )
            if native is None:
                native = evaluate_native_policy(
                    environment_factory=environment_factory,
                    seeds=normalized_seeds,
                    max_decisions_per_episode=max_decisions_per_episode,
                    deadline=deadline,
                    clock=clock,
                )
    except (PolicyValidityBlocked, SimulatorAdapterError, SmokeBlocked) as exc:
        raise WarmStartBlocked(str(exc)) from exc
    for policy in (candidate, native):
        for row in policy["rows"]:
            row["candidate_legality"] = policy.get("candidate_legality") is True

    model_after = sha256_bytes(
        canonical_json_bytes(canonical_warm_start_model_payload(model))
    )
    all_rows = [*candidate["rows"], *native["rows"]]
    finite_metrics = all(
        not isinstance(row.get("terminal_floor"), bool)
        and isinstance(row.get("terminal_floor"), Real)
        and math.isfinite(float(row["terminal_floor"]))
        and not isinstance(row.get("decisions"), bool)
        and isinstance(row.get("decisions"), int)
        and 0 <= row["decisions"] <= max_decisions_per_episode
        for row in all_rows
    )
    comparison = _paired_rollout_comparison(
        candidate,
        native,
        seeds=normalized_seeds,
        bootstrap_seed=bootstrap_seed,
        bootstrap_resamples=bootstrap_resamples,
        confidence_level=confidence_level,
    )
    return {
        "checks": {
            "candidate_legality": candidate.get("candidate_legality") is True
            and native.get("candidate_legality") is True,
            "episode_count": len(all_rows) == 2 * len(normalized_seeds),
            "finite_metrics": finite_metrics,
            "four_category_coverage": candidate.get("all_categories")
            == list(TARGET_CATEGORIES)
            and native.get("all_categories") == list(TARGET_CATEGORIES),
            "model_immutability": model_before == model_after,
            "no_gradients": all(
                parameter.grad is None for parameter in model.parameters()
            ),
            "terminal_outcomes": all(
                row.get("outcome") in {"player_loss", "player_victory"}
                for row in all_rows
            ),
            "within_bounds": len(all_rows) <= max_episodes,
        },
        "comparison": comparison,
        "model_sha256": model_after,
        "policies": {
            "candidate": candidate,
            "native_simple_agent": native,
        },
        "schema_version": ROLLOUT_SCHEMA_VERSION,
        "seeds": normalized_seeds,
        "victories": {
            "candidate": sum(
                row["outcome"] == "player_victory" for row in candidate["rows"]
            ),
            "native_simple_agent": sum(
                row["outcome"] == "player_victory" for row in native["rows"]
            ),
        },
    }


def _validated_gate_thresholds(value: Mapping[str, Any]) -> dict[str, float]:
    thresholds = _mapping(value, "quality thresholds")
    expected = {
        "floor_noninferiority_margin",
        "maximum_mean_floor_deficit",
        "minimum_macro_category_action_agreement",
        "minimum_overall_action_agreement",
        "minimum_per_category_action_agreement",
    }
    _require_keys(thresholds, expected, "quality thresholds")
    result = {
        name: _finite_number(thresholds[name], f"quality thresholds.{name}")
        for name in sorted(expected)
    }
    for field in (
        "minimum_macro_category_action_agreement",
        "minimum_overall_action_agreement",
        "minimum_per_category_action_agreement",
    ):
        if not 0.0 <= result[field] <= 1.0:
            raise WarmStartBlocked(f"quality thresholds.{field} must be in [0, 1]")
    if (
        result["floor_noninferiority_margin"] < 0.0
        or result["maximum_mean_floor_deficit"] < 0.0
    ):
        raise WarmStartBlocked("floor deficit thresholds must be non-negative")
    if (
        result["maximum_mean_floor_deficit"]
        > result["floor_noninferiority_margin"]
    ):
        raise WarmStartBlocked(
            "maximum_mean_floor_deficit must not exceed floor_noninferiority_margin"
        )
    return result


def classify_quality_gate(
    teacher_fit: Mapping[str, Any],
    rollouts: Mapping[str, Any],
    thresholds: Mapping[str, Any],
) -> dict[str, Any]:
    """Apply the same preregistered fit and rollout thresholds to one cohort."""
    limits = _validated_gate_thresholds(thresholds)
    by_category = _mapping(teacher_fit.get("by_category"), "teacher_fit.by_category")
    if set(by_category) != set(TARGET_CATEGORIES):
        raise WarmStartBlocked("teacher_fit categories mismatch")
    overall = _finite_number(
        teacher_fit.get("overall_action_agreement"),
        "teacher_fit.overall_action_agreement",
    )
    macro = _finite_number(
        teacher_fit.get("macro_category_action_agreement"),
        "teacher_fit.macro_category_action_agreement",
    )
    per_category = [
        _finite_number(
            _mapping(by_category[category], f"teacher_fit.{category}").get(
                "action_agreement"
            ),
            f"teacher_fit.{category}.action_agreement",
        )
        for category in TARGET_CATEGORIES
    ]
    comparison = _mapping(rollouts.get("comparison"), "rollouts.comparison")
    interval = _mapping(
        comparison.get("floor_difference_ci"),
        "rollouts.comparison.floor_difference_ci",
    )
    lower = _finite_number(interval.get("lower"), "rollout floor interval lower")
    mean = _finite_number(interval.get("mean"), "rollout floor interval mean")
    checks = {
        "macro_category_action_agreement": macro
        >= limits["minimum_macro_category_action_agreement"],
        "mean_floor_deficit": mean >= -limits["maximum_mean_floor_deficit"],
        "noninferiority_lower_bound": lower
        >= -limits["floor_noninferiority_margin"],
        "overall_action_agreement": overall
        >= limits["minimum_overall_action_agreement"],
        "per_category_action_agreement": min(per_category)
        >= limits["minimum_per_category_action_agreement"],
    }
    return {"checks": checks, "passed": all(checks.values())}


def run_warm_start_execution(
    *,
    registration: Mapping[str, Any],
    environment_factory: Callable[[int], Any],
    preflight_checks: Mapping[str, bool],
    clock: Callable[[], float],
) -> dict[str, Any]:
    """Run one bounded train/validation/final execution from a registration."""
    validated = validate_warm_start_registration(registration)
    checks = _mapping(preflight_checks, "preflight_checks")
    if not checks or any(not isinstance(value, bool) for value in checks.values()):
        raise WarmStartBlocked("preflight_checks must be nonempty booleans")
    failed_preflight = sorted(name for name, passed in checks.items() if not passed)
    if failed_preflight:
        raise WarmStartBlocked(
            "preflight checks failed: " + ", ".join(failed_preflight)
        )

    study = validated["study"]
    cohorts = study["cohorts"]
    evaluation = study["evaluation"]
    limits = study["limits"]
    model_config = study["model"]
    optimizer = study["optimizer"]
    started = _finite_number(clock(), "clock value")
    deadline = started + limits["max_wall_seconds_per_execution"]
    remaining_demo_rows = limits["max_demo_rows"]
    policy_episodes = 0

    def collect_phase(cohort: str, seeds: Sequence[int]) -> dict[str, Any]:
        nonlocal remaining_demo_rows, policy_episodes
        if remaining_demo_rows <= 0:
            raise WarmStartBlocked("execution exhausted max_demo_rows")
        dataset = collect_native_demonstrations(
            environment_factory=environment_factory,
            cohort=cohort,
            seeds=seeds,
            max_decisions_per_episode=limits["max_decisions_per_episode"],
            max_demo_rows=remaining_demo_rows,
            max_episodes=len(seeds),
            deadline=deadline,
            clock=clock,
            required_categories=TARGET_CATEGORIES,
        )
        remaining_demo_rows -= dataset["row_count"]
        policy_episodes += len(seeds)
        return dataset

    def evaluate_phase(
        model: Any,
        *,
        dataset: Mapping[str, Any],
        seeds: Sequence[int],
        max_episodes: int,
    ) -> dict[str, Any]:
        nonlocal policy_episodes
        now = _finite_number(clock(), "clock value")
        remaining_seconds = deadline - now
        if remaining_seconds <= 0.0:
            raise WarmStartBlocked("warm-start execution exceeded wall-time bound")
        teacher_fit = evaluate_teacher_fit(
            model, dataset=dataset, hash_dim=model_config["hash_dim"]
        )
        rollouts = evaluate_warm_start_rollouts(
            model,
            environment_factory=environment_factory,
            seeds=seeds,
            hash_dim=model_config["hash_dim"],
            max_decisions_per_episode=limits["max_decisions_per_episode"],
            max_episodes=max_episodes,
            max_wall_seconds=remaining_seconds,
            bootstrap_seed=evaluation["bootstrap_seed"],
            bootstrap_resamples=evaluation["bootstrap_resamples"],
            confidence_level=evaluation["confidence_level"],
            clock=clock,
            native_demonstrations=dataset,
        )
        policy_episodes += len(seeds)
        return {"rollouts": rollouts, "teacher_fit": teacher_fit}

    train_dataset = collect_phase("train", cohorts["train_seeds"])
    if policy_episodes > limits["max_train_episodes"]:
        raise WarmStartBlocked("execution exceeded max_train_episodes")
    training = train_warm_start_ranker(
        train_dataset,
        hash_dim=model_config["hash_dim"],
        hidden_dim=model_config["hidden_dim"],
        model_seed=model_config["model_seed"],
        epochs=optimizer["epochs"],
        learning_rate=optimizer["learning_rate"],
        betas=(optimizer["beta1"], optimizer["beta2"]),
        epsilon=optimizer["epsilon"],
        weight_decay=optimizer["weight_decay"],
    )
    _check_deadline(clock, deadline, "warm-start training")

    validation_dataset = collect_phase("validation", cohorts["validation_seeds"])
    validation = evaluate_phase(
        training.model,
        dataset=validation_dataset,
        seeds=cohorts["validation_seeds"],
        max_episodes=limits["max_validation_policy_episodes"],
    )
    validation_gate = classify_quality_gate(
        validation["teacher_fit"],
        validation["rollouts"],
        evaluation["thresholds"],
    )

    final_dataset = None
    final_test = None
    if validation_gate["passed"]:
        final_dataset = collect_phase("final_test", cohorts["final_test_seeds"])
        final_test = evaluate_phase(
            training.model,
            dataset=final_dataset,
            seeds=cohorts["final_test_seeds"],
            max_episodes=limits["max_final_policy_episodes"],
        )
    if policy_episodes > limits["max_total_policy_episodes"]:
        raise WarmStartBlocked("execution exceeded max_total_policy_episodes")
    _check_deadline(clock, deadline, "warm-start execution")

    internal_checks = {
        "episode_budget": policy_episodes <= limits["max_total_policy_episodes"],
        "model_frozen": all(
            not parameter.requires_grad for parameter in training.model.parameters()
        ),
        "registration": True,
        "train_four_category_coverage": train_dataset["all_categories"]
        == list(TARGET_CATEGORIES),
    }
    return {
        "datasets": {
            "final_test": final_dataset,
            "train": train_dataset,
            "validation": validation_dataset,
        },
        "final_test": final_test,
        "structural_checks": {**checks, **internal_checks},
        "training": {
            "final_model": training.final_model,
            "history": list(training.history),
            "initial_model": training.initial_model,
        },
        "validation": validation,
        "validation_gate": validation_gate,
    }


def _nested_structural_blockers(
    phase: str, evidence: Mapping[str, Any]
) -> list[str]:
    blockers = []
    for section in ("teacher_fit", "rollouts"):
        section_value = _mapping(evidence.get(section), f"{phase}.{section}")
        checks = _mapping(section_value.get("checks"), f"{phase}.{section}.checks")
        blockers.extend(
            f"{phase}.{section}.{name}"
            for name, passed in sorted(checks.items())
            if passed is not True
        )
    return blockers


def _authority() -> dict[str, bool]:
    return {
        "formal_noncombat_rl": False,
        "live_gameplay": False,
        "live_policy_loading": False,
        "live_study_launch": False,
        "ope_reinterpretation": False,
        "policy_promotion": False,
        "qualification": False,
        "simulator_rl_training": False,
        "simulator_training": False,
    }


def classify_warm_start_results(
    primary: Mapping[str, Any],
    replay: Mapping[str, Any],
    thresholds: Mapping[str, Any],
) -> dict[str, Any]:
    """Classify structure, validation stopping, and final baseline floor."""
    primary = _mapping(primary, "primary execution")
    replay = _mapping(replay, "replay execution")
    structural = _mapping(
        primary.get("structural_checks"), "primary structural_checks"
    )
    blockers = [
        name for name, passed in sorted(structural.items()) if passed is not True
    ]
    replay_identity = canonical_json_bytes(primary) == canonical_json_bytes(replay)
    if not replay_identity:
        blockers.append("replay_identity")

    validation = _mapping(primary.get("validation"), "primary validation")
    blockers.extend(_nested_structural_blockers("validation", validation))
    validation_gate = classify_quality_gate(
        _mapping(validation["teacher_fit"], "validation.teacher_fit"),
        _mapping(validation["rollouts"], "validation.rollouts"),
        thresholds,
    )
    final_test_value = primary.get("final_test")
    final_test_untouched = final_test_value is None
    final_gate = None
    if validation_gate["passed"]:
        if final_test_value is None:
            blockers.append("final_test_missing_after_validation_pass")
        else:
            final_test = _mapping(final_test_value, "primary final_test")
            blockers.extend(_nested_structural_blockers("final_test", final_test))
            final_gate = classify_quality_gate(
                _mapping(final_test["teacher_fit"], "final_test.teacher_fit"),
                _mapping(final_test["rollouts"], "final_test.rollouts"),
                thresholds,
            )
    elif final_test_value is not None:
        blockers.append("validation_stop_gate")

    final_test_access_contract = (
        validation_gate["passed"] and final_test_value is not None
    ) or (not validation_gate["passed"] and final_test_value is None)

    if blockers:
        quality = "not_evaluated"
        verdict = "blocked"
    elif final_gate is not None and final_gate["passed"]:
        quality = "baseline_floor_demonstrated"
        verdict = "study_valid_with_baseline_floor"
    else:
        quality = "baseline_floor_not_demonstrated"
        verdict = "study_valid_without_baseline_floor"
    return {
        "authority": _authority(),
        "blockers": blockers,
        "checks": {
            **structural,
            "final_test_access_contract": final_test_access_contract,
            "replay_identity": replay_identity,
        },
        "final_gate": final_gate,
        "final_test_untouched": final_test_untouched,
        "quality": quality,
        "validation_gate": validation_gate,
        "verdict": verdict,
    }


def _phase_metric_summary(
    evidence: Mapping[str, Any] | None, gate: Mapping[str, Any] | None
) -> dict[str, Any] | None:
    if evidence is None:
        return None
    teacher = _mapping(evidence.get("teacher_fit"), "phase teacher_fit")
    rollouts = _mapping(evidence.get("rollouts"), "phase rollouts")
    comparison = _mapping(rollouts.get("comparison"), "phase rollout comparison")
    return {
        "floor_difference_ci": copy.deepcopy(comparison.get("floor_difference_ci")),
        "gate": copy.deepcopy(gate),
        "macro_category_action_agreement": teacher.get(
            "macro_category_action_agreement"
        ),
        "overall_action_agreement": teacher.get("overall_action_agreement"),
        "teacher_row_count": teacher.get("row_count"),
        "victories": copy.deepcopy(rollouts.get("victories")),
    }


def _render_warm_start_report(metrics: Mapping[str, Any]) -> str:
    classification = _mapping(metrics.get("classification"), "metrics.classification")
    lines = [
        "# Non-Combat Simulator Baseline Warm Start",
        "",
        f"- Verdict: `{classification['verdict']}`",
        f"- Quality: `{classification['quality']}`",
        f"- Registration SHA-256: `{metrics['registration_sha256']}`",
        f"- Replay identity: `{str(classification['checks']['replay_identity']).lower()}`",
        f"- Final test untouched: `{str(classification['final_test_untouched']).lower()}`",
        "",
        "## Cohorts",
        "",
    ]
    for name, count in sorted(metrics["cohort_seed_counts"].items()):
        lines.append(f"- {name}: {count} seeds")
    lines.extend(["", "## Gates", ""])
    validation = metrics["validation"]
    lines.append(
        "- Validation: "
        + ("passed" if validation["gate"]["passed"] else "not demonstrated")
    )
    final_test = metrics["final_test"]
    if final_test is None:
        lines.append("- Final test: untouched")
    else:
        lines.append(
            "- Final test: "
            + ("passed" if final_test["gate"]["passed"] else "not demonstrated")
        )
    lines.extend(["", "## Blockers", ""])
    if classification["blockers"]:
        lines.extend(f"- {value}" for value in classification["blockers"])
    else:
        lines.append("- None")
    lines.extend(["", "## Authority", ""])
    lines.extend(
        f"- {name}: `{str(value).lower()}`"
        for name, value in sorted(classification["authority"].items())
    )
    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "- Demonstrations and rollout outcomes are simulator-only evidence.",
            "- SimpleAgent is auxiliary supervision, not reward or permanent ground truth.",
            "- This result does not authorize formal RL, live loading, gameplay, OPE, qualification, or promotion.",
            "- Current and Bottled remain excluded until a simulator feature/action bridge is validated.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_warm_start_artifacts(
    *,
    registration: Mapping[str, Any],
    primary: Mapping[str, Any],
    replay: Mapping[str, Any],
    classification: Mapping[str, Any],
) -> dict[str, bytes]:
    """Build the complete canonical artifact set entirely in memory."""
    validated_registration = validate_warm_start_registration(registration)
    primary = copy.deepcopy(_mapping(primary, "primary execution"))
    replay = copy.deepcopy(_mapping(replay, "replay execution"))
    expected_classification = classify_warm_start_results(
        primary,
        replay,
        validated_registration["study"]["evaluation"]["thresholds"],
    )
    if canonical_json_bytes(classification) != canonical_json_bytes(
        expected_classification
    ):
        raise WarmStartBlocked("warm-start classification does not match executions")
    classification = copy.deepcopy(expected_classification)
    datasets = _mapping(primary.get("datasets"), "primary.datasets")
    _require_keys(
        datasets, {"final_test", "train", "validation"}, "primary.datasets"
    )
    training = _mapping(primary.get("training"), "primary.training")
    _require_keys(
        training, {"final_model", "history", "initial_model"}, "primary.training"
    )
    registration_sha256 = sha256_bytes(canonical_json_bytes(validated_registration))
    primary_sha256 = sha256_bytes(canonical_json_bytes(primary))
    replay_sha256 = sha256_bytes(canonical_json_bytes(replay))
    initial_model_sha256 = sha256_bytes(
        canonical_json_bytes(training["initial_model"])
    )
    final_model_sha256 = sha256_bytes(canonical_json_bytes(training["final_model"]))

    demonstrations = {
        "datasets": copy.deepcopy(datasets),
        "registration_sha256": registration_sha256,
        "schema_version": DEMONSTRATION_ARTIFACT_SCHEMA_VERSION,
    }
    model = {
        "final_model": copy.deepcopy(training["final_model"]),
        "final_model_sha256": final_model_sha256,
        "history": copy.deepcopy(training["history"]),
        "initial_model": copy.deepcopy(training["initial_model"]),
        "initial_model_sha256": initial_model_sha256,
        "registration_sha256": registration_sha256,
        "schema_version": MODEL_ARTIFACT_SCHEMA_VERSION,
    }
    trajectories = {
        "final_test": copy.deepcopy(primary.get("final_test")),
        "primary_execution_sha256": primary_sha256,
        "registration_sha256": registration_sha256,
        "replay_execution_sha256": replay_sha256,
        "schema_version": TRAJECTORY_ARTIFACT_SCHEMA_VERSION,
        "structural_checks": copy.deepcopy(primary.get("structural_checks")),
        "validation": copy.deepcopy(primary.get("validation")),
    }
    cohorts = validated_registration["study"]["cohorts"]
    metrics = {
        "authority": copy.deepcopy(classification["authority"]),
        "checks": copy.deepcopy(classification["checks"]),
        "classification": classification,
        "cohort_seed_counts": {
            "final_test": len(cohorts["final_test_seeds"]),
            "train": len(cohorts["train_seeds"]),
            "validation": len(cohorts["validation_seeds"]),
        },
        "demonstration_row_counts": {
            name: None if dataset is None else dataset.get("row_count")
            for name, dataset in sorted(datasets.items())
        },
        "final_model_sha256": final_model_sha256,
        "final_test": _phase_metric_summary(
            primary.get("final_test"), classification.get("final_gate")
        ),
        "initial_model_sha256": initial_model_sha256,
        "primary_execution_sha256": primary_sha256,
        "registration_sha256": registration_sha256,
        "replay_execution_sha256": replay_sha256,
        "schema_version": METRICS_ARTIFACT_SCHEMA_VERSION,
        "training_epochs": len(training["history"]),
        "validation": _phase_metric_summary(
            _mapping(primary.get("validation"), "primary.validation"),
            classification.get("validation_gate"),
        ),
    }
    payloads = {
        "demonstrations.json": canonical_json_bytes(demonstrations),
        "metrics.json": canonical_json_bytes(metrics),
        "model.json": canonical_json_bytes(model),
        "report.md": _render_warm_start_report(metrics).encode("utf-8"),
        "trajectories.json": canonical_json_bytes(trajectories),
    }
    manifest = {
        "artifact_hashes": {
            name: sha256_bytes(payload) for name, payload in sorted(payloads.items())
        },
        "authority": copy.deepcopy(classification["authority"]),
        "registration_sha256": registration_sha256,
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "verdict": classification["verdict"],
    }
    payloads["artifact_manifest.json"] = canonical_json_bytes(manifest)
    validate_warm_start_artifact_payloads(payloads)
    return payloads


def _load_artifact_json(artifacts: Mapping[str, bytes], name: str) -> dict[str, Any]:
    try:
        value = json.loads(artifacts[name])
    except (KeyError, UnicodeError, json.JSONDecodeError) as exc:
        raise WarmStartBlocked(f"canonical artifact {name} is invalid: {exc}") from exc
    return _mapping(value, f"canonical artifact {name}")


def _validate_warm_start_artifact_semantics(
    *,
    manifest: Mapping[str, Any],
    demonstrations: Mapping[str, Any],
    metrics: Mapping[str, Any],
    model: Mapping[str, Any],
    trajectories: Mapping[str, Any],
) -> None:
    expected_schemas = {
        "demonstrations": DEMONSTRATION_ARTIFACT_SCHEMA_VERSION,
        "metrics": METRICS_ARTIFACT_SCHEMA_VERSION,
        "model": MODEL_ARTIFACT_SCHEMA_VERSION,
        "trajectories": TRAJECTORY_ARTIFACT_SCHEMA_VERSION,
    }
    payloads = {
        "demonstrations": demonstrations,
        "metrics": metrics,
        "model": model,
        "trajectories": trajectories,
    }
    registration_sha256 = manifest.get("registration_sha256")
    if not _is_hex(registration_sha256, 64):
        raise WarmStartBlocked("canonical registration SHA-256 is invalid")
    for name, payload in payloads.items():
        if payload.get("schema_version") != expected_schemas[name]:
            raise WarmStartBlocked(f"canonical {name} schema mismatch")
        if payload.get("registration_sha256") != registration_sha256:
            raise WarmStartBlocked(f"canonical {name} registration mismatch")

    authority = manifest.get("authority")
    classification = _mapping(metrics.get("classification"), "metrics.classification")
    valid_verdicts = {
        "blocked",
        "study_valid_with_baseline_floor",
        "study_valid_without_baseline_floor",
    }
    if (
        not isinstance(authority, Mapping)
        or dict(authority) != _authority()
        or metrics.get("authority") != authority
        or classification.get("authority") != authority
        or classification.get("verdict") != manifest.get("verdict")
        or manifest.get("verdict") not in valid_verdicts
    ):
        raise WarmStartBlocked("canonical artifact verdict or authority mismatch")

    datasets = _mapping(demonstrations.get("datasets"), "demonstrations.datasets")
    _require_keys(
        datasets, {"final_test", "train", "validation"}, "demonstrations.datasets"
    )
    for name in ("train", "validation"):
        dataset = _mapping(datasets[name], f"demonstrations.datasets.{name}")
        if dataset.get("schema_version") != DATASET_SCHEMA_VERSION:
            raise WarmStartBlocked(f"canonical {name} dataset schema mismatch")
        if dataset.get("cohort") != name:
            raise WarmStartBlocked(f"canonical {name} dataset cohort mismatch")
    if datasets["final_test"] is not None:
        final_dataset = _mapping(
            datasets["final_test"], "demonstrations.datasets.final_test"
        )
        if (
            final_dataset.get("schema_version") != DATASET_SCHEMA_VERSION
            or final_dataset.get("cohort") != "final_test"
        ):
            raise WarmStartBlocked("canonical final_test dataset mismatch")
    final_untouched = classification.get("final_test_untouched")
    if final_untouched is not (datasets["final_test"] is None):
        raise WarmStartBlocked("canonical final-test dataset access mismatch")
    if (trajectories.get("final_test") is None) is not bool(final_untouched):
        raise WarmStartBlocked("canonical final-test trajectory access mismatch")

    initial_payload = _mapping(model.get("initial_model"), "model.initial_model")
    final_payload = _mapping(model.get("final_model"), "model.final_model")
    for name, payload in (("initial", initial_payload), ("final", final_payload)):
        loaded = load_warm_start_model(
            payload, expected_hash_dim=1024, expected_hidden_dim=128
        )
        if canonical_warm_start_model_payload(loaded) != payload:
            raise WarmStartBlocked(f"canonical {name} model mismatch")
    initial_sha256 = sha256_bytes(canonical_json_bytes(initial_payload))
    final_sha256 = sha256_bytes(canonical_json_bytes(final_payload))
    if (
        model.get("initial_model_sha256") != initial_sha256
        or model.get("final_model_sha256") != final_sha256
        or metrics.get("initial_model_sha256") != initial_sha256
        or metrics.get("final_model_sha256") != final_sha256
    ):
        raise WarmStartBlocked("canonical model hash mismatch")

    primary_sha256 = trajectories.get("primary_execution_sha256")
    replay_sha256 = trajectories.get("replay_execution_sha256")
    if not _is_hex(primary_sha256, 64) or not _is_hex(replay_sha256, 64):
        raise WarmStartBlocked("canonical execution SHA-256 is invalid")
    if (
        metrics.get("primary_execution_sha256") != primary_sha256
        or metrics.get("replay_execution_sha256") != replay_sha256
        or classification.get("checks", {}).get("replay_identity")
        is not (primary_sha256 == replay_sha256)
    ):
        raise WarmStartBlocked("canonical execution identity mismatch")


def validate_warm_start_artifact_payloads(
    artifacts: Mapping[str, bytes]
) -> dict[str, Any]:
    """Validate an in-memory canonical artifact set and its semantic links."""
    if set(artifacts) != set(CANONICAL_ARTIFACT_NAMES):
        raise WarmStartBlocked("canonical artifact set is incomplete")
    if any(not isinstance(payload, bytes) for payload in artifacts.values()):
        raise WarmStartBlocked("canonical artifacts must be bytes")
    manifest = _load_artifact_json(artifacts, "artifact_manifest.json")
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise WarmStartBlocked("artifact manifest schema mismatch")
    expected_hashes = {
        name: sha256_bytes(artifacts[name])
        for name in sorted(artifacts)
        if name != "artifact_manifest.json"
    }
    if manifest.get("artifact_hashes") != expected_hashes:
        raise WarmStartBlocked("artifact manifest hash closure mismatch")
    try:
        report = artifacts["report.md"].decode("utf-8")
    except UnicodeError as exc:
        raise WarmStartBlocked(f"canonical report is invalid UTF-8: {exc}") from exc
    if not report.startswith("# Non-Combat Simulator Baseline Warm Start\n"):
        raise WarmStartBlocked("canonical report header mismatch")
    _validate_warm_start_artifact_semantics(
        manifest=manifest,
        demonstrations=_load_artifact_json(artifacts, "demonstrations.json"),
        metrics=_load_artifact_json(artifacts, "metrics.json"),
        model=_load_artifact_json(artifacts, "model.json"),
        trajectories=_load_artifact_json(artifacts, "trajectories.json"),
    )
    return manifest


def publish_warm_start_artifacts(
    output_dir: Path | str,
    artifacts: Mapping[str, bytes],
    *,
    replace: Callable[[str | os.PathLike[str], str | os.PathLike[str]], None] = os.replace,
) -> None:
    """Atomically install a validated canonical set, restoring prior bytes on error."""
    validate_warm_start_artifact_payloads(artifacts)
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    allowed = set(CANONICAL_ARTIFACT_NAMES) | {"execution_journal.json"}
    existing = {path.name for path in root.iterdir()}
    if not existing.issubset(allowed):
        raise WarmStartBlocked("output artifact inventory mismatch")
    order = sorted(name for name in artifacts if name != "artifact_manifest.json")
    order.append("artifact_manifest.json")
    destinations = {name: root / name for name in order}
    previous = {
        name: path.read_bytes() if path.is_file() else None
        for name, path in destinations.items()
    }
    temporary = {
        name: path.with_name(f".{path.name}.tmp") for name, path in destinations.items()
    }
    installed = []
    try:
        for name in order:
            temporary[name].write_bytes(artifacts[name])
        for name in order:
            replace(temporary[name], destinations[name])
            installed.append(name)
    except Exception:
        for name in installed:
            destination = destinations[name]
            prior = previous[name]
            if prior is None:
                destination.unlink(missing_ok=True)
            else:
                restore = destination.with_name(f".{destination.name}.restore")
                restore.write_bytes(prior)
                os.replace(restore, destination)
        raise
    finally:
        for path in temporary.values():
            path.unlink(missing_ok=True)
        for path in destinations.values():
            path.with_name(f".{path.name}.restore").unlink(missing_ok=True)
    validate_warm_start_artifact_directory(root)


def validate_warm_start_artifact_directory(
    output_dir: Path | str,
) -> dict[str, Any]:
    """Rehash and semantically validate one published artifact directory."""
    root = Path(output_dir)
    allowed = set(CANONICAL_ARTIFACT_NAMES) | {"execution_journal.json"}
    try:
        entries = {path.name for path in root.iterdir()}
    except OSError as exc:
        raise WarmStartBlocked(f"cannot inspect artifact directory: {exc}") from exc
    if not set(CANONICAL_ARTIFACT_NAMES).issubset(entries) or not entries.issubset(
        allowed
    ):
        raise WarmStartBlocked("published artifact inventory mismatch")
    try:
        artifacts = {
            name: (root / name).read_bytes() for name in CANONICAL_ARTIFACT_NAMES
        }
    except OSError as exc:
        raise WarmStartBlocked(f"cannot read published artifacts: {exc}") from exc
    manifest = validate_warm_start_artifact_payloads(artifacts)
    expected_hashes = manifest["artifact_hashes"]
    actual_hashes = {
        name: sha256_file(root / name) for name in sorted(expected_hashes)
    }
    if actual_hashes != expected_hashes:
        raise WarmStartBlocked("published artifact hash closure mismatch")
    journal_path = root / "execution_journal.json"
    if journal_path.exists():
        try:
            journal = json.loads(journal_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise WarmStartBlocked(f"published execution journal is invalid: {exc}") from exc
        if (
            not isinstance(journal, Mapping)
            or journal.get("schema_version") != JOURNAL_SCHEMA_VERSION
            or journal.get("canonical") is not False
        ):
            raise WarmStartBlocked("published execution journal contract mismatch")
    return manifest


def build_warm_start_execution_journal(
    *,
    primary_elapsed_seconds: float,
    replay_elapsed_seconds: float,
    wall_time_budget_seconds: float,
) -> dict[str, Any]:
    values = {}
    for name, raw in (
        ("primary_elapsed_seconds", primary_elapsed_seconds),
        ("replay_elapsed_seconds", replay_elapsed_seconds),
        ("wall_time_budget_seconds", wall_time_budget_seconds),
    ):
        value = _finite_number(raw, name)
        if value < 0.0:
            raise WarmStartBlocked(f"{name} must be non-negative")
        values[name] = value
    return {
        "canonical": False,
        **values,
        "schema_version": JOURNAL_SCHEMA_VERSION,
    }


def publish_warm_start_execution_journal(
    output_dir: Path | str, journal: Mapping[str, Any]
) -> None:
    root = Path(output_dir)
    validate_warm_start_artifact_directory(root)
    value = _mapping(journal, "execution journal")
    if (
        value.get("schema_version") != JOURNAL_SCHEMA_VERSION
        or value.get("canonical") is not False
    ):
        raise WarmStartBlocked("execution journal contract mismatch")
    destination = root / "execution_journal.json"
    temporary = destination.with_name(f".{destination.name}.tmp")
    temporary.write_bytes(canonical_json_bytes(value))
    try:
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    validate_warm_start_artifact_directory(root)
