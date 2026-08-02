"""Build a bounded SimpleAgent-anchored non-combat simulator warm start."""

from __future__ import annotations

import copy
import json
import math
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
    validate_candidates,
    validate_native_baseline_action,
    validate_provenance,
    validate_snapshot,
)
from analysis_scripts.noncombat_simulator_training_smoke import (
    FEATURE_VERSION,
    SmokeBlocked,
    _candidate_features,
    _validate_binding,
    project_policy_view,
)


INPUT_SCHEMA_VERSION = "noncombat-simulator-baseline-warm-start-input-v1"
DEMONSTRATION_SCHEMA_VERSION = "noncombat-simulator-native-demonstration-v1"
DATASET_SCHEMA_VERSION = "noncombat-simulator-native-demonstration-dataset-v1"
MODEL_SCHEMA_VERSION = "noncombat-simulator-baseline-warm-start-model-v1"
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
