"""One-step shared-trajectory ablation for card baseline clipping."""

from __future__ import annotations

import copy
from dataclasses import dataclass
import hashlib
import math
import statistics
from typing import Any, Literal, Mapping, Sequence

import torch

from analysis_scripts import noncombat_card_acceptance_empirical_successor_runtime as runtime
from analysis_scripts import noncombat_card_only_behavior_sensitivity_training as training
from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot as pilot
from analysis_scripts.noncombat_card_acceptance_objective import (
    CardAcceptancePolicyTerms,
    build_card_acceptance_policy_terms,
)


PredictionMode = Literal["clipped", "unclipped"]


class BaselineClippingAblationBlocked(RuntimeError):
    """Raised when the single-variable ablation contract differs."""


@dataclass(frozen=True)
class CompletedBaselineClippingAblation:
    clipped_branch: training.BehaviorSensitivityRuntime
    unclipped_branch: training.BehaviorSensitivityRuntime
    attempted_seeds: tuple[int, ...]
    supported_seeds: tuple[int, ...]
    censored_trajectories: tuple[dict[str, Any], ...]
    telemetry: dict[str, Any]


def _candidate_episodes(
    episodes: Sequence[Any],
) -> tuple[runtime.ArmEpisodeRollout, ...]:
    source = tuple(episodes)
    if not source:
        raise BaselineClippingAblationBlocked("shared trajectories must be nonempty")
    if any(
        not isinstance(episode, runtime.ArmEpisodeRollout)
        or episode.arm != "candidate"
        for episode in source
    ):
        raise BaselineClippingAblationBlocked(
            "shared trajectories must be candidate arm episodes"
        )
    return source


def rebuild_candidate_card_rows(
    bootstrap: runtime.PairedBootstrap,
    episodes: Sequence[runtime.ArmEpisodeRollout],
    *,
    baseline: runtime.ArmCrossFittedBaseline,
    prediction_mode: PredictionMode,
) -> tuple[tuple[CardAcceptancePolicyTerms, float], ...]:
    """Rebuild card terms on one branch while retaining stored decisions."""
    if prediction_mode not in ("clipped", "unclipped"):
        raise BaselineClippingAblationBlocked("baseline prediction mode differs")
    source = _candidate_episodes(episodes)
    if (
        not isinstance(baseline, runtime.ArmCrossFittedBaseline)
        or baseline.arm != "candidate"
    ):
        raise BaselineClippingAblationBlocked("candidate baseline differs")
    rollout_decisions = tuple(
        decision for episode in source for decision in episode.decisions
    )
    if len(rollout_decisions) != len(baseline.decisions) or len(
        baseline.predictions
    ) != len(baseline.decisions):
        raise BaselineClippingAblationBlocked("baseline decision counts differ")

    rows: list[tuple[CardAcceptancePolicyTerms, float]] = []
    for decision, baseline_decision, prediction in zip(
        rollout_decisions,
        baseline.decisions,
        baseline.predictions,
        strict=True,
    ):
        identity = decision.decision_id
        folded_state = runtime.fold_baseline_state_features(
            decision.state_features
        )
        if (
            identity != baseline_decision.decision_id
            or identity != prediction.decision_id
            or decision.decision_index != baseline_decision.decision_index
            or folded_state.shape != baseline_decision.state_features.shape
            or not torch.equal(folded_state, baseline_decision.state_features)
        ):
            raise BaselineClippingAblationBlocked(
                "stored decision and held-out prediction alignment differs"
            )
        if decision.category != "card_reward":
            if decision.card_terms is not None:
                raise BaselineClippingAblationBlocked(
                    "non-card decision carries card terms"
                )
            continue
        if (
            not isinstance(decision.candidate_features, torch.Tensor)
            or not decision.candidates
        ):
            raise BaselineClippingAblationBlocked(
                "stored card candidate context is unavailable"
            )
        try:
            output = runtime.forward_card_policy(
                bootstrap,
                arm="candidate",
                state_features=decision.state_features,
                candidate_features=decision.candidate_features,
                candidates=decision.candidates,
            )
            terms = build_card_acceptance_policy_terms(
                output.family_logits,
                output.conditional_logits,
                decision.candidates,
                decision.selected_action_id,
                category="card_reward",
            )
        except (RuntimeError, TypeError, ValueError) as exc:
            raise BaselineClippingAblationBlocked(str(exc)) from exc
        if (
            terms.action_ids
            != tuple(candidate["action_id"] for candidate in decision.candidates)
            or terms.selected_action_id != decision.selected_action_id
        ):
            raise BaselineClippingAblationBlocked(
                "rebuilt card candidate identity differs"
            )
        prediction_value = float(getattr(prediction, prediction_mode))
        advantage = float(baseline_decision.raw_return) - prediction_value
        if not all(
            math.isfinite(value)
            for value in (
                prediction_value,
                float(baseline_decision.raw_return),
                advantage,
            )
        ):
            raise BaselineClippingAblationBlocked(
                "rebuilt card advantage must be finite"
            )
        rows.append((terms, advantage))
    if not rows:
        raise BaselineClippingAblationBlocked("shared cohort has no card decisions")
    return tuple(rows)


def _summary(values: Sequence[float]) -> dict[str, Any]:
    normalized = tuple(float(value) for value in values)
    if not normalized or not all(math.isfinite(value) for value in normalized):
        raise BaselineClippingAblationBlocked("telemetry values must be finite")
    return {
        "count": len(normalized),
        "maximum": max(normalized),
        "mean": math.fsum(normalized) / len(normalized),
        "minimum": min(normalized),
        "negative_count": sum(value < 0.0 for value in normalized),
        "positive_count": sum(value > 0.0 for value in normalized),
        "population_stddev": statistics.pstdev(normalized),
        "zero_count": sum(value == 0.0 for value in normalized),
    }


def _objective_summary(value: runtime.ArmCardRewardObjective) -> dict[str, Any]:
    return {
        "card_decision_count": value.card_decision_count,
        "conditional_entropy_loss": float(value.conditional_entropy_loss.detach()),
        "conditional_policy_loss": float(value.conditional_policy_loss.detach()),
        "family_entropy_loss": float(value.family_entropy_loss.detach()),
        "family_policy_loss": float(value.family_policy_loss.detach()),
        "total_loss": float(value.total_loss.detach()),
    }


def _head_norms(
    names: Sequence[str], gradients: Sequence[torch.Tensor]
) -> dict[str, float]:
    if len(names) != len(gradients):
        raise BaselineClippingAblationBlocked("gradient telemetry alignment differs")
    result = {}
    for head in ("conditional_ranker", "family_head"):
        squares = [
            float(torch.sum(gradient.detach().to(dtype=torch.float64) ** 2).item())
            for name, gradient in zip(names, gradients, strict=True)
            if name.startswith(f"{head}.")
        ]
        if not squares:
            raise BaselineClippingAblationBlocked("gradient telemetry head is empty")
        result[head] = math.sqrt(math.fsum(squares))
    return result


def _prepared_summary(value: Any) -> dict[str, Any]:
    return {
        "applied_head_l2": _head_norms(
            value.parameter_names, value.applied_gradients
        ),
        "combined_head_l2": _head_norms(
            value.parameter_names, value.combined_gradients
        ),
        "postclip_global_norm": float(value.postclip_global_norm),
        "preclip_global_norm": float(value.preclip_global_norm),
    }


def _step_summary(value: runtime.ArmOptimizerStepEvidence) -> dict[str, Any]:
    deltas = tuple(
        post.detach().to(dtype=torch.float64)
        - pre.detach().to(dtype=torch.float64)
        for pre, post in zip(value.pre_parameters, value.post_parameters, strict=True)
    )
    return {
        "model_step_head_l2": _head_norms(value.parameter_names, deltas),
        "model_step_l2": math.sqrt(
            math.fsum(float(torch.sum(delta**2).item()) for delta in deltas)
        ),
    }


def _flatten(values: Sequence[torch.Tensor]) -> torch.Tensor:
    if not values:
        raise BaselineClippingAblationBlocked("gradient vector is empty")
    return torch.cat(
        tuple(value.detach().to(dtype=torch.float64).reshape(-1) for value in values)
    )


def _cosine(left: Sequence[torch.Tensor], right: Sequence[torch.Tensor]) -> float:
    left_vector = _flatten(left)
    right_vector = _flatten(right)
    if left_vector.shape != right_vector.shape:
        raise BaselineClippingAblationBlocked("branch gradient shapes differ")
    denominator = float(
        (torch.linalg.vector_norm(left_vector) * torch.linalg.vector_norm(right_vector)).item()
    )
    if denominator == 0.0 or not math.isfinite(denominator):
        raise BaselineClippingAblationBlocked("branch gradient norm is invalid")
    result = float(torch.dot(left_vector, right_vector).item()) / denominator
    if not math.isfinite(result):
        raise BaselineClippingAblationBlocked("branch gradient cosine is invalid")
    return max(-1.0, min(1.0, result))


def _restore_in_place(
    value: training.BehaviorSensitivityRuntime,
    *,
    entry_checkpoint: bytes,
) -> None:
    restored = training.restore_behavior_sensitivity_checkpoint(
        entry_checkpoint,
        probe_rows=value.probe_rows,
        entry_model=value.entry_model,
    )
    for field_name in training.BehaviorSensitivityRuntime.__dataclass_fields__:
        setattr(value, field_name, getattr(restored, field_name))


def _advance_branch(
    value: training.BehaviorSensitivityRuntime,
    *,
    branch: str,
    supported: Sequence[runtime.ArmEpisodeRollout],
    behavior: Mapping[str, Any],
    telemetry: Mapping[str, Any],
) -> None:
    value.next_chunk_index += 1
    value.environment_accesses += training.CHUNK_SEED_COUNT
    value.completed_decisions += sum(len(episode.decisions) for episode in supported)
    value.completed_summaries.append(
        {
            "ablation_branch": branch,
            "behavior": copy.deepcopy(dict(behavior)),
            "chunk_index": training.FIRST_CHUNK_INDEX,
            "telemetry_sha256": hashlib.sha256(
                training._canonical_ascii(telemetry)
            ).hexdigest(),
        }
    )
    value.stopped_for_concentration = bool(behavior["stop"])


def apply_shared_trajectory_ablation(
    clipped_branch: training.BehaviorSensitivityRuntime,
    unclipped_branch: training.BehaviorSensitivityRuntime,
    episodes: Sequence[runtime.ArmEpisodeRollout],
    *,
    entry_checkpoint: bytes,
) -> CompletedBaselineClippingAblation:
    """Prepare both branch steps before committing either one."""
    try:
        training._validate_behavior_sensitivity_runtime(clipped_branch)
        training._validate_behavior_sensitivity_runtime(unclipped_branch)
        if (
            clipped_branch.next_chunk_index != training.FIRST_CHUNK_INDEX
            or unclipped_branch.next_chunk_index != training.FIRST_CHUNK_INDEX
            or pilot.encode_candidate_card_policy(clipped_branch.bootstrap)
            != pilot.encode_candidate_card_policy(unclipped_branch.bootstrap)
            or runtime.encode_optimizer_state(clipped_branch.candidate_optimizer)
            != runtime.encode_optimizer_state(unclipped_branch.candidate_optimizer)
        ):
            raise BaselineClippingAblationBlocked("ablation entry branches differ")
        attempted = _candidate_episodes(episodes)
        supported, censored = training._validate_candidate_trajectories(attempted)
        baseline = runtime.build_candidate_cross_fitted_baseline(supported)
        clipped_rows = runtime.build_arm_card_reward_rows(
            supported, arm="candidate", baseline=baseline
        )
        unclipped_rows = rebuild_candidate_card_rows(
            unclipped_branch.bootstrap,
            supported,
            baseline=baseline,
            prediction_mode="unclipped",
        )
        if (
            len(clipped_rows) != len(unclipped_rows)
            or tuple(row[0].selected_action_id for row in clipped_rows)
            != tuple(row[0].selected_action_id for row in unclipped_rows)
        ):
            raise BaselineClippingAblationBlocked("branch card rows differ")
        clipped_objective = runtime.build_arm_card_reward_objective(clipped_rows)
        unclipped_objective = runtime.build_arm_card_reward_objective(unclipped_rows)

        clipped_named = runtime._arm_named_trainable_parameters(
            clipped_branch.bootstrap, arm="candidate"
        )
        unclipped_named = runtime._arm_named_trainable_parameters(
            unclipped_branch.bootstrap, arm="candidate"
        )
        if tuple(name for name, _ in clipped_named) != tuple(
            name for name, _ in unclipped_named
        ):
            raise BaselineClippingAblationBlocked("branch parameter names differ")
        clipped_prepared = runtime._prepare_arm_optimizer_step(
            clipped_branch.candidate_optimizer,
            clipped_objective,
            parameters=tuple(parameter for _, parameter in clipped_named),
            parameter_names=tuple(name for name, _ in clipped_named),
            reconstruct_components=False,
        )
        unclipped_prepared = runtime._prepare_arm_optimizer_step(
            unclipped_branch.candidate_optimizer,
            unclipped_objective,
            parameters=tuple(parameter for _, parameter in unclipped_named),
            parameter_names=tuple(name for name, _ in unclipped_named),
            reconstruct_components=False,
        )

        card_predictions = tuple(
            prediction
            for decision, prediction in zip(
                baseline.decisions, baseline.predictions, strict=True
            )
            if decision.category == "card_reward"
        )
        clipped_advantages = tuple(float(advantage) for _, advantage in clipped_rows)
        unclipped_advantages = tuple(
            float(advantage) for _, advantage in unclipped_rows
        )
        precommit = {
            "baseline": {
                "card_prediction_count": len(card_predictions),
                "clipped_count": sum(
                    bool(prediction.was_clipped) for prediction in card_predictions
                ),
                "clipped_predictions": _summary(
                    tuple(float(prediction.clipped) for prediction in card_predictions)
                ),
                "unclipped_predictions": _summary(
                    tuple(float(prediction.unclipped) for prediction in card_predictions)
                ),
            },
            "branches": {
                "clipped": {
                    "advantages": _summary(clipped_advantages),
                    "gradient": _prepared_summary(clipped_prepared),
                    "objective": _objective_summary(clipped_objective),
                },
                "unclipped": {
                    "advantages": _summary(unclipped_advantages),
                    "gradient": _prepared_summary(unclipped_prepared),
                    "objective": _objective_summary(unclipped_objective),
                },
            },
            "gradient_comparison": {
                "applied_cosine": _cosine(
                    clipped_prepared.applied_gradients,
                    unclipped_prepared.applied_gradients,
                ),
                "combined_cosine": _cosine(
                    clipped_prepared.combined_gradients,
                    unclipped_prepared.combined_gradients,
                ),
            },
        }
        clipped_step = runtime._commit_prepared_arm_step(
            clipped_branch.candidate_optimizer, clipped_prepared
        )
        unclipped_step = runtime._commit_prepared_arm_step(
            unclipped_branch.candidate_optimizer, unclipped_prepared
        )
        clipped_behavior = training._behavior_summary(clipped_branch)
        unclipped_behavior = training._behavior_summary(unclipped_branch)
        precommit["branches"]["clipped"]["behavior"] = clipped_behavior
        precommit["branches"]["clipped"]["step"] = _step_summary(clipped_step)
        precommit["branches"]["unclipped"]["behavior"] = unclipped_behavior
        precommit["branches"]["unclipped"]["step"] = _step_summary(unclipped_step)
        _advance_branch(
            clipped_branch,
            branch="clipped",
            supported=supported,
            behavior=clipped_behavior,
            telemetry=precommit["branches"]["clipped"],
        )
        _advance_branch(
            unclipped_branch,
            branch="unclipped",
            supported=supported,
            behavior=unclipped_behavior,
            telemetry=precommit["branches"]["unclipped"],
        )
        clipped_checkpoint = training.encode_behavior_sensitivity_checkpoint(
            clipped_branch
        )
        unclipped_checkpoint = training.encode_behavior_sensitivity_checkpoint(
            unclipped_branch
        )
        precommit["branches"]["clipped"]["checkpoint_sha256"] = hashlib.sha256(
            clipped_checkpoint
        ).hexdigest()
        precommit["branches"]["unclipped"]["checkpoint_sha256"] = hashlib.sha256(
            unclipped_checkpoint
        ).hexdigest()
        return CompletedBaselineClippingAblation(
            clipped_branch=clipped_branch,
            unclipped_branch=unclipped_branch,
            attempted_seeds=tuple(episode.seed for episode in attempted),
            supported_seeds=tuple(episode.seed for episode in supported),
            censored_trajectories=censored,
            telemetry=precommit,
        )
    except Exception as exc:
        _restore_in_place(clipped_branch, entry_checkpoint=entry_checkpoint)
        _restore_in_place(unclipped_branch, entry_checkpoint=entry_checkpoint)
        if isinstance(exc, runtime.SuccessorRuntimeError):
            raise BaselineClippingAblationBlocked(str(exc)) from exc
        raise


__all__ = [
    "BaselineClippingAblationBlocked",
    "CompletedBaselineClippingAblation",
    "apply_shared_trajectory_ablation",
    "rebuild_candidate_card_rows",
]
