"""Candidate-only continuation runtime for card behavior sensitivity training."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
import json
import math
from typing import Any, Callable, Mapping, Sequence
import time

from analysis_scripts import noncombat_card_acceptance_empirical_successor_runtime as runtime
from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot as pilot


FIRST_CHUNK_INDEX = 4
FINAL_CHUNK_INDEX = 20
CHUNK_SEED_COUNT = 64
MAX_CENSORED_TRAJECTORIES = 8
MAX_TRAINING_ENVIRONMENT_ACCESSES = 1_024
CHECKPOINT_SCHEMA_VERSION = "noncombat-card-only-behavior-sensitivity-checkpoint-v1"


class BehaviorSensitivityBlocked(RuntimeError):
    """Raised when the fixed continuation contract cannot proceed."""


@dataclass
class BehaviorSensitivityRuntime:
    bootstrap: runtime.PairedBootstrap
    candidate_optimizer: Any
    probe_rows: tuple[Any, ...]
    entry_model: bytes
    entry_predictions: tuple[dict[str, Any], ...]
    next_chunk_index: int = FIRST_CHUNK_INDEX
    environment_accesses: int = 0
    completed_decisions: int = 0
    completed_summaries: list[dict[str, Any]] = field(default_factory=list)
    stopped_for_concentration: bool = False


@dataclass(frozen=True)
class CompletedCandidateOnlyChunk:
    chunk_index: int
    attempted_seeds: tuple[int, ...]
    seeds: tuple[int, ...]
    censored_trajectories: tuple[dict[str, Any], ...]
    episodes: tuple[runtime.ArmEpisodeRollout, ...]
    behavior: dict[str, Any]
    update: runtime.CandidateChunkUpdateEvidence
    checkpoint: bytes
    runtime: BehaviorSensitivityRuntime


def _canonical_ascii(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise BehaviorSensitivityBlocked("checkpoint is not canonical JSON") from exc


def _optimizer_step_count(optimizer: Any) -> int:
    try:
        encoded = runtime.encode_optimizer_state(optimizer)
        decoded = runtime._decode_state_value(encoded, "candidate optimizer")
        steps = {
            int(float(state["step"].item())) for state in decoded["state"].values()
        }
    except (KeyError, TypeError, ValueError, runtime.SuccessorRuntimeError) as exc:
        raise BehaviorSensitivityBlocked("candidate optimizer state is invalid") from exc
    if len(steps) != 1:
        raise BehaviorSensitivityBlocked("candidate optimizer step coordinate differs")
    return steps.pop()


def _prediction_identity(prediction: Mapping[str, Any]) -> tuple[int, int]:
    try:
        identity = (int(prediction["seed"]), int(prediction["decision_index"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise BehaviorSensitivityBlocked("probe prediction identity is invalid") from exc
    return identity


def _normalize_predictions(values: Sequence[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    predictions = tuple(copy.deepcopy(dict(value)) for value in values)
    identities = tuple(_prediction_identity(value) for value in predictions)
    if not predictions or identities != tuple(sorted(set(identities))):
        raise BehaviorSensitivityBlocked("probe prediction identities differ")
    required = {
        "decision_index",
        "predicted_action_id",
        "predicted_family",
        "seed",
        "target_action_id",
        "target_family",
    }
    if any(set(value) != required for value in predictions):
        raise BehaviorSensitivityBlocked("probe prediction fields differ")
    return predictions


def _model_parameter_l2(entry_model: bytes, current_model: bytes) -> float:
    try:
        entry = json.loads(entry_model.decode("ascii"))
        current = json.loads(current_model.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BehaviorSensitivityBlocked("candidate model encoding is invalid") from exc
    if set(entry) != set(current):
        raise BehaviorSensitivityBlocked("candidate model fields differ")
    squares = []
    for head in ("conditional_ranker", "family_head"):
        if set(entry[head]) != set(current[head]):
            raise BehaviorSensitivityBlocked("candidate model parameter fields differ")
        for name in sorted(entry[head]):
            left = entry[head][name]
            right = current[head][name]
            if left["dtype"] != right["dtype"] or left["shape"] != right["shape"]:
                raise BehaviorSensitivityBlocked("candidate model parameter shape differs")
            if len(left["values"]) != len(right["values"]):
                raise BehaviorSensitivityBlocked("candidate model parameter length differs")
            squares.extend(
                (float(a) - float(b)) ** 2
                for a, b in zip(left["values"], right["values"], strict=True)
            )
    result = math.sqrt(math.fsum(squares))
    if not math.isfinite(result):
        raise BehaviorSensitivityBlocked("candidate model distance is invalid")
    return result


def initialize_behavior_sensitivity_runtime(
    *,
    bootstrap: runtime.PairedBootstrap,
    candidate_optimizer: Any,
    probe_rows: Sequence[Any],
) -> BehaviorSensitivityRuntime:
    if _optimizer_step_count(candidate_optimizer) != FIRST_CHUNK_INDEX:
        raise BehaviorSensitivityBlocked("continuation requires four optimizer steps")
    normalized_probe = tuple(probe_rows)
    evaluation = pilot.evaluate_card_warm_start(bootstrap, normalized_probe)
    value = BehaviorSensitivityRuntime(
        bootstrap=bootstrap,
        candidate_optimizer=candidate_optimizer,
        probe_rows=normalized_probe,
        entry_model=pilot.encode_candidate_card_policy(bootstrap),
        entry_predictions=_normalize_predictions(evaluation["predictions"]),
    )
    _validate_behavior_sensitivity_runtime(value)
    return value


def _validate_behavior_sensitivity_runtime(value: BehaviorSensitivityRuntime) -> None:
    if not isinstance(value, BehaviorSensitivityRuntime):
        raise BehaviorSensitivityBlocked("behavior sensitivity runtime differs")
    coordinates = (
        value.next_chunk_index,
        value.environment_accesses,
        value.completed_decisions,
    )
    if any(isinstance(item, bool) or not isinstance(item, int) or item < 0 for item in coordinates):
        raise BehaviorSensitivityBlocked("continuation coordinate is invalid")
    completed_chunks = value.next_chunk_index - FIRST_CHUNK_INDEX
    if not 0 <= completed_chunks <= FINAL_CHUNK_INDEX - FIRST_CHUNK_INDEX:
        raise BehaviorSensitivityBlocked("continuation chunk coordinate differs")
    if (
        value.environment_accesses != completed_chunks * CHUNK_SEED_COUNT
        or len(value.completed_summaries) != completed_chunks
        or _optimizer_step_count(value.candidate_optimizer) != value.next_chunk_index
    ):
        raise BehaviorSensitivityBlocked("continuation resource coordinate differs")
    if value.completed_decisions > value.environment_accesses * 500:
        raise BehaviorSensitivityBlocked("continuation decision coordinate exceeds bound")
    if not isinstance(value.stopped_for_concentration, bool):
        raise BehaviorSensitivityBlocked("continuation stop coordinate is invalid")
    if value.completed_summaries:
        expected_stop = bool(value.completed_summaries[-1]["behavior"]["stop"])
    else:
        expected_stop = False
    if value.stopped_for_concentration != expected_stop:
        raise BehaviorSensitivityBlocked("continuation stop state differs")
    current = pilot.encode_candidate_card_policy(value.bootstrap)
    if not value.entry_model or _canonical_ascii(json.loads(value.entry_model)) != value.entry_model:
        raise BehaviorSensitivityBlocked("entry model encoding is invalid")
    if _normalize_predictions(value.entry_predictions) != value.entry_predictions:
        raise BehaviorSensitivityBlocked("entry prediction binding differs")
    pilot._probe_sha256(value.probe_rows)
    runtime.encode_paired_bootstrap(value.bootstrap)
    expected_parameters = tuple(
        parameter
        for _, parameter in runtime._arm_named_trainable_parameters(
            value.bootstrap, arm="candidate"
        )
    )
    actual_parameters = tuple(
        parameter
        for group in value.candidate_optimizer.param_groups
        for parameter in group["params"]
    )
    if tuple(map(id, actual_parameters)) != tuple(map(id, expected_parameters)):
        raise BehaviorSensitivityBlocked("candidate optimizer parameter ownership differs")
    _model_parameter_l2(value.entry_model, current)


def _behavior_summary(value: BehaviorSensitivityRuntime) -> dict[str, Any]:
    evaluation = pilot.evaluate_card_warm_start(value.bootstrap, value.probe_rows)
    current_predictions = _normalize_predictions(evaluation["predictions"])
    if tuple(map(_prediction_identity, current_predictions)) != tuple(
        map(_prediction_identity, value.entry_predictions)
    ):
        raise BehaviorSensitivityBlocked("current probe identity differs from entry")
    action_flips = sum(
        left["predicted_action_id"] != right["predicted_action_id"]
        for left, right in zip(value.entry_predictions, current_predictions, strict=True)
    )
    family_flips = sum(
        left["predicted_family"] != right["predicted_family"]
        for left, right in zip(value.entry_predictions, current_predictions, strict=True)
    )
    current_model = pilot.encode_candidate_card_policy(value.bootstrap)
    classified = pilot.classify_card_probe(evaluation)
    return {
        "action_flips_from_entry": action_flips,
        "family_flips_from_entry": family_flips,
        "model_sha256": hashlib.sha256(current_model).hexdigest(),
        "parameter_l2_from_entry": _model_parameter_l2(value.entry_model, current_model),
        "probe_rows": len(current_predictions),
        "stop": classified["stop"],
        "take_rate": classified["take_rate"],
    }


def behavior_summary(value: BehaviorSensitivityRuntime) -> dict[str, Any]:
    _validate_behavior_sensitivity_runtime(value)
    return _behavior_summary(value)


def encode_behavior_sensitivity_checkpoint(value: BehaviorSensitivityRuntime) -> bytes:
    _validate_behavior_sensitivity_runtime(value)
    return _canonical_ascii(
        {
            "bootstrap": json.loads(runtime.encode_paired_bootstrap(value.bootstrap)),
            "candidate_optimizer": runtime.encode_optimizer_state(value.candidate_optimizer),
            "coordinates": {
                "completed_decisions": value.completed_decisions,
                "environment_accesses": value.environment_accesses,
                "next_chunk_index": value.next_chunk_index,
            },
            "entry_model_sha256": hashlib.sha256(value.entry_model).hexdigest(),
            "entry_predictions": copy.deepcopy(list(value.entry_predictions)),
            "probe_sha256": pilot._probe_sha256(value.probe_rows),
            "schema_version": CHECKPOINT_SCHEMA_VERSION,
            "stopped_for_concentration": value.stopped_for_concentration,
            "summaries": copy.deepcopy(value.completed_summaries),
        }
    )


def restore_behavior_sensitivity_checkpoint(
    payload: bytes,
    *,
    probe_rows: Sequence[Any],
    entry_model: bytes,
) -> BehaviorSensitivityRuntime:
    try:
        parsed = json.loads(payload.decode("ascii"))
    except (AttributeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BehaviorSensitivityBlocked("continuation checkpoint JSON is invalid") from exc
    if _canonical_ascii(parsed) != payload:
        raise BehaviorSensitivityBlocked("continuation checkpoint is not canonical")
    expected_fields = {
        "bootstrap",
        "candidate_optimizer",
        "coordinates",
        "entry_model_sha256",
        "entry_predictions",
        "probe_sha256",
        "schema_version",
        "stopped_for_concentration",
        "summaries",
    }
    if set(parsed) != expected_fields or parsed["schema_version"] != CHECKPOINT_SCHEMA_VERSION:
        raise BehaviorSensitivityBlocked("continuation checkpoint fields differ")
    normalized_probe = tuple(probe_rows)
    if parsed["probe_sha256"] != pilot._probe_sha256(normalized_probe):
        raise BehaviorSensitivityBlocked("continuation probe binding differs")
    if parsed["entry_model_sha256"] != hashlib.sha256(entry_model).hexdigest():
        raise BehaviorSensitivityBlocked("continuation entry model binding differs")
    try:
        bootstrap = runtime.restore_paired_bootstrap(_canonical_ascii(parsed["bootstrap"]))
        optimizer = runtime.build_candidate_card_optimizer(bootstrap)
        runtime.restore_optimizer_state(optimizer, parsed["candidate_optimizer"])
    except runtime.SuccessorRuntimeError as exc:
        raise BehaviorSensitivityBlocked(str(exc)) from exc
    coordinates = parsed["coordinates"]
    if set(coordinates) != {
        "completed_decisions",
        "environment_accesses",
        "next_chunk_index",
    }:
        raise BehaviorSensitivityBlocked("continuation checkpoint coordinates differ")
    value = BehaviorSensitivityRuntime(
        bootstrap=bootstrap,
        candidate_optimizer=optimizer,
        probe_rows=normalized_probe,
        entry_model=entry_model,
        entry_predictions=_normalize_predictions(parsed["entry_predictions"]),
        next_chunk_index=coordinates["next_chunk_index"],
        environment_accesses=coordinates["environment_accesses"],
        completed_decisions=coordinates["completed_decisions"],
        completed_summaries=copy.deepcopy(parsed["summaries"]),
        stopped_for_concentration=parsed["stopped_for_concentration"],
    )
    _validate_behavior_sensitivity_runtime(value)
    return value


def _validate_candidate_trajectories(
    episodes: Sequence[Any],
) -> tuple[tuple[runtime.ArmEpisodeRollout, ...], tuple[dict[str, Any], ...]]:
    attempted = tuple(episodes)
    if len(attempted) != CHUNK_SEED_COUNT:
        raise BehaviorSensitivityBlocked("candidate-only chunk requires 64 trajectories")
    if any(not isinstance(episode, runtime.ArmEpisodeRollout) for episode in attempted):
        raise BehaviorSensitivityBlocked("candidate-only trajectory identity differs")
    seeds = tuple(episode.seed for episode in attempted)
    if seeds != tuple(sorted(set(seeds))):
        raise BehaviorSensitivityBlocked("candidate-only seeds must be ascending unique")
    supported = []
    censored = []
    for episode in attempted:
        if episode.arm != "candidate":
            raise BehaviorSensitivityBlocked("candidate-only trajectory arm differs")
        if episode.unsupported_reason is not None:
            if episode.unsupported_reason not in runtime.REGISTERED_SUPPORT_BLOCKERS:
                raise BehaviorSensitivityBlocked("candidate-only trajectory has an unknown blocker")
            last = episode.decisions[-1] if episode.decisions else None
            censored.append(
                {
                    "category": None if last is None else last.category,
                    "decision_id": None if last is None else last.decision_id,
                    "reason": episode.unsupported_reason,
                    "seed": episode.seed,
                }
            )
            continue
        if episode.final_snapshot.get("terminal") is not True:
            raise BehaviorSensitivityBlocked("candidate-only trajectory is not terminal")
        supported.append(episode)
    if len(censored) > MAX_CENSORED_TRAJECTORIES:
        raise BehaviorSensitivityBlocked("candidate-only censor bound exceeded")
    if len(supported) < runtime.MIN_CANDIDATE_TRAJECTORIES_PER_CHUNK:
        raise BehaviorSensitivityBlocked("candidate-only support floor is unmet")
    return tuple(supported), tuple(censored)


def complete_candidate_only_chunk(
    value: BehaviorSensitivityRuntime,
    episodes: Sequence[Any],
    *,
    chunk_index: int,
) -> CompletedCandidateOnlyChunk:
    _validate_behavior_sensitivity_runtime(value)
    entry_checkpoint = encode_behavior_sensitivity_checkpoint(value)
    try:
        if value.stopped_for_concentration or value.next_chunk_index >= FINAL_CHUNK_INDEX:
            raise BehaviorSensitivityBlocked("continuation cannot start another chunk")
        if chunk_index != value.next_chunk_index:
            raise BehaviorSensitivityBlocked("continuation chunk index differs")
        attempted = tuple(episodes)
        supported, censored = _validate_candidate_trajectories(attempted)
        update = runtime.apply_candidate_cross_fitted_chunk_update_exploratory(
            value.bootstrap,
            value.candidate_optimizer,
            supported,
        )
        behavior = _behavior_summary(value)
        summary = {
            "attempted_trajectories": len(attempted),
            "behavior": behavior,
            "candidate_card_decisions": sum(
                decision.category == "card_reward"
                for episode in supported
                for decision in episode.decisions
            ),
            "candidate_floor_mean": math.fsum(
                episode.floor_progress for episode in supported
            ) / len(supported),
            "candidate_victories": sum(episode.terminal_victory for episode in supported),
            "censored_trajectories": copy.deepcopy(list(censored)),
            "chunk_index": chunk_index,
            "supported_trajectories": len(supported),
        }
        value.next_chunk_index += 1
        value.environment_accesses += CHUNK_SEED_COUNT
        value.completed_decisions += sum(len(episode.decisions) for episode in supported)
        value.completed_summaries.append(summary)
        value.stopped_for_concentration = behavior["stop"]
        checkpoint = encode_behavior_sensitivity_checkpoint(value)
        restored = restore_behavior_sensitivity_checkpoint(
            checkpoint,
            probe_rows=value.probe_rows,
            entry_model=value.entry_model,
        )
        if encode_behavior_sensitivity_checkpoint(restored) != checkpoint:
            raise BehaviorSensitivityBlocked("continuation checkpoint restore differs")
        return CompletedCandidateOnlyChunk(
            chunk_index=chunk_index,
            attempted_seeds=tuple(episode.seed for episode in attempted),
            seeds=tuple(episode.seed for episode in supported),
            censored_trajectories=censored,
            episodes=supported,
            behavior=behavior,
            update=update,
            checkpoint=checkpoint,
            runtime=value,
        )
    except Exception as exc:
        restored = restore_behavior_sensitivity_checkpoint(
            entry_checkpoint,
            probe_rows=value.probe_rows,
            entry_model=value.entry_model,
        )
        for field_name in BehaviorSensitivityRuntime.__dataclass_fields__:
            setattr(value, field_name, getattr(restored, field_name))
        if isinstance(exc, runtime.SuccessorRuntimeError):
            raise BehaviorSensitivityBlocked(str(exc)) from exc
        raise


def collect_and_complete_candidate_only_chunk(
    value: BehaviorSensitivityRuntime,
    *,
    environment_factory: Callable[[int], Any],
    seeds: Sequence[int],
    chunk_index: int,
    deadline: float,
    clock: Callable[[], float] = time.monotonic,
    before_episode: Callable[[int], None] = lambda _seed: None,
    after_episode: Callable[[int], None] = lambda _seed: None,
) -> CompletedCandidateOnlyChunk:
    _validate_behavior_sensitivity_runtime(value)
    entry_checkpoint = encode_behavior_sensitivity_checkpoint(value)
    working = restore_behavior_sensitivity_checkpoint(
        entry_checkpoint,
        probe_rows=value.probe_rows,
        entry_model=value.entry_model,
    )
    normalized_seeds = tuple(seeds)
    if len(normalized_seeds) != CHUNK_SEED_COUNT or normalized_seeds != tuple(
        sorted(set(normalized_seeds))
    ):
        raise BehaviorSensitivityBlocked("candidate-only collection requires 64 ascending seeds")
    if not all(callable(callback) for callback in (clock, before_episode, after_episode)):
        raise BehaviorSensitivityBlocked("candidate-only callback is invalid")
    if float(clock()) > float(deadline):
        raise BehaviorSensitivityBlocked("candidate-only deadline reached before collection")
    episodes = []
    try:
        for seed in normalized_seeds:
            if float(clock()) > float(deadline):
                raise BehaviorSensitivityBlocked("candidate-only deadline reached during collection")
            before_episode(seed)
            episodes.append(
                runtime.rollout_candidate_card_only_native_baseline_training_episode(
                    working.bootstrap,
                    environment_factory=environment_factory,
                    seed=seed,
                    deadline=float(deadline),
                    clock=clock,
                )
            )
            after_episode(seed)
        return complete_candidate_only_chunk(
            working,
            tuple(episodes),
            chunk_index=chunk_index,
        )
    except runtime.SuccessorRuntimeError as exc:
        raise BehaviorSensitivityBlocked(str(exc)) from exc
    finally:
        if encode_behavior_sensitivity_checkpoint(value) != entry_checkpoint:
            raise BehaviorSensitivityBlocked("partial collection mutated complete checkpoint")


__all__ = [
    "BehaviorSensitivityBlocked",
    "BehaviorSensitivityRuntime",
    "CompletedCandidateOnlyChunk",
    "behavior_summary",
    "collect_and_complete_candidate_only_chunk",
    "complete_candidate_only_chunk",
    "encode_behavior_sensitivity_checkpoint",
    "initialize_behavior_sensitivity_runtime",
    "restore_behavior_sensitivity_checkpoint",
]
