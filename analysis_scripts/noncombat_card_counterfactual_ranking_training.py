"""Consumed-seed pairwise training from card action counterfactual returns."""

from __future__ import annotations

import copy
from dataclasses import dataclass
import hashlib
import json
import math
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

import torch
import torch.nn.functional as F

from analysis_scripts import noncombat_card_acceptance_empirical_successor_runtime as runtime
from analysis_scripts import noncombat_card_action_counterfactual_credit as credit
from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot as pilot
from analysis_scripts.noncombat_card_acceptance_objective import (
    CardAcceptanceObjectiveError,
    build_card_acceptance_policy_terms,
)
from analysis_scripts.noncombat_state_conditioned_policy_input import (
    PolicyInputError,
    project_state_conditioned_policy_input,
)


TRAIN_SEEDS = tuple(range(1000, 1016))
HOLDOUT_SEEDS = tuple(range(1016, 1024))
MAX_CARD_STATES_PER_SEED = 2
MAX_TRAIN_BRANCHES = 128
MAX_HOLDOUT_BRANCHES = 64
MAX_TRAIN_CENSORED_SEEDS = 2
MAX_HOLDOUT_CENSORED_SEEDS = 1
MIN_TRAIN_SOURCE_STATES = 24
MIN_HOLDOUT_SOURCE_STATES = 12
TRAINING_STEPS = 32
ENTRY_CHECKPOINT_SCHEMA_VERSION = "noncombat-card-only-residual-checkpoint-v1"
DATASET_SCHEMA_VERSION = "noncombat-card-counterfactual-ranking-dataset-v1"
TRAINING_REPORT_SCHEMA_VERSION = (
    "noncombat-card-counterfactual-ranking-training-v1"
)


class CounterfactualRankingBlocked(RuntimeError):
    """Raised when the fixed ranking training contract cannot proceed."""


@dataclass(frozen=True)
class CounterfactualRankingRow:
    seed: int
    decision_index: int
    source_sha256: str
    state_features: torch.Tensor
    candidate_features: torch.Tensor
    candidates: tuple[dict[str, Any], ...]
    action_returns: tuple[float, ...]

    @property
    def informative(self) -> bool:
        return max(self.action_returns) > min(self.action_returns)


@dataclass(frozen=True)
class CounterfactualPartition:
    name: str
    seeds: tuple[int, ...]
    rows: tuple[CounterfactualRankingRow, ...]
    action_branches: int
    root_native_transitions: int
    censored_seeds: tuple[dict[str, Any], ...]
    budget_exhausted: bool


@dataclass(frozen=True)
class CompletedCounterfactualRankingTraining:
    report: dict[str, Any]
    entry_model: bytes
    trained_model: bytes


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
        raise CounterfactualRankingBlocked("artifact is not canonical") from exc


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_ascii(value)).hexdigest()


def _exception_messages(exc: BaseException) -> tuple[str, ...]:
    messages: list[str] = []
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        messages.append(str(current))
        current = current.__cause__ or current.__context__
    return tuple(messages)


def registered_support_blocker(exc: BaseException) -> str | None:
    messages = _exception_messages(exc)
    for blocker in runtime.REGISTERED_SUPPORT_BLOCKERS:
        if any(blocker in message for message in messages):
            return blocker
    return None


def collect_counterfactual_partition(
    environment_factory: Callable[[int], Any],
    *,
    name: str,
    seeds: Sequence[int],
    max_action_branches: int,
    max_censored_seeds: int,
    max_card_states_per_seed: int = MAX_CARD_STATES_PER_SEED,
    max_decisions: int = credit.MAX_DECISIONS_PER_CONTINUATION,
    deadline: float | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> CounterfactualPartition:
    """Collect complete source rows without exposing holdout data to fitting."""
    normalized_seeds = tuple(seeds)
    if name not in {"train", "holdout"}:
        raise CounterfactualRankingBlocked("partition name differs")
    if not callable(environment_factory) or not callable(clock):
        raise CounterfactualRankingBlocked("partition factory and clock are required")
    limits = (
        max_action_branches,
        max_censored_seeds,
        max_card_states_per_seed,
        max_decisions,
    )
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value < 0
        for value in limits
    ) or max_action_branches == 0 or max_card_states_per_seed == 0 or max_decisions == 0:
        raise CounterfactualRankingBlocked("partition limits are invalid")
    if not normalized_seeds or len(set(normalized_seeds)) != len(normalized_seeds):
        raise CounterfactualRankingBlocked("partition seeds are invalid")
    active_deadline = float("inf") if deadline is None else float(deadline)
    if deadline is not None and not math.isfinite(active_deadline):
        raise CounterfactualRankingBlocked("partition deadline is invalid")

    rows: list[CounterfactualRankingRow] = []
    censored: list[dict[str, Any]] = []
    branch_count = 0
    root_transitions = 0
    budget_exhausted = False
    for seed in normalized_seeds:
        if float(clock()) > active_deadline:
            raise CounterfactualRankingBlocked("partition deadline reached")
        try:
            environment = environment_factory(seed)
        except Exception as exc:
            raise CounterfactualRankingBlocked(
                f"environment construction failed for seed {seed}"
            ) from exc
        evaluated_for_seed = 0
        decision_index = 0
        censor_reason: str | None = None
        while True:
            snapshot, candidates = credit._environment_state(environment)
            if snapshot["terminal"]:
                break
            if decision_index >= max_decisions:
                raise CounterfactualRankingBlocked("root decision ceiling reached")
            eligible = (
                snapshot["category"] == "card_reward"
                and evaluated_for_seed < max_card_states_per_seed
            )
            if eligible:
                if branch_count + len(candidates) > max_action_branches:
                    budget_exhausted = True
                    break
                try:
                    policy_input = project_state_conditioned_policy_input(
                        snapshot, candidates
                    )
                except PolicyInputError as exc:
                    raise CounterfactualRankingBlocked(str(exc)) from exc
                source_sha256 = _sha256_json(
                    {"snapshot": snapshot, "candidate_actions": candidates}
                )
                returns: list[float] = []
                source_complete = True
                for candidate in candidates:
                    branch_count += 1
                    try:
                        trace = credit.evaluate_action_branch(
                            environment,
                            action_id=candidate["action_id"],
                            max_decisions=max_decisions,
                            deadline=(None if deadline is None else active_deadline),
                            clock=clock,
                        )
                    except credit.CounterfactualCreditBlocked as exc:
                        censor_reason = registered_support_blocker(exc)
                        if censor_reason is None:
                            raise CounterfactualRankingBlocked(str(exc)) from exc
                        source_complete = False
                        break
                    returns.append(trace.total_return)
                if not source_complete:
                    break
                if len(returns) != len(candidates):
                    raise CounterfactualRankingBlocked("source row is incomplete")
                rows.append(
                    CounterfactualRankingRow(
                        seed=seed,
                        decision_index=decision_index,
                        source_sha256=source_sha256,
                        state_features=policy_input.state_features.detach().clone(),
                        candidate_features=(
                            policy_input.candidate_features.detach().clone()
                        ),
                        candidates=tuple(copy.deepcopy(candidates)),
                        action_returns=tuple(returns),
                    )
                )
                evaluated_for_seed += 1
            try:
                environment, _ = credit._advance_native(environment)
            except credit.CounterfactualCreditBlocked as exc:
                censor_reason = registered_support_blocker(exc)
                if censor_reason is None:
                    raise CounterfactualRankingBlocked(str(exc)) from exc
                break
            root_transitions += 1
            decision_index += 1
        if censor_reason is not None:
            censored.append({"reason": censor_reason, "seed": seed})
            if len(censored) > max_censored_seeds:
                raise CounterfactualRankingBlocked(
                    f"{name} registered censor limit exceeded"
                )
        if budget_exhausted:
            break

    return CounterfactualPartition(
        name=name,
        seeds=normalized_seeds,
        rows=tuple(rows),
        action_branches=branch_count,
        root_native_transitions=root_transitions,
        censored_seeds=tuple(censored),
        budget_exhausted=budget_exhausted,
    )


def compact_partition(partition: CounterfactualPartition) -> dict[str, Any]:
    return {
        "action_branches": partition.action_branches,
        "budget_exhausted": partition.budget_exhausted,
        "censored_seeds": copy.deepcopy(list(partition.censored_seeds)),
        "informative_source_states": sum(row.informative for row in partition.rows),
        "name": partition.name,
        "root_native_transitions": partition.root_native_transitions,
        "schema_version": DATASET_SCHEMA_VERSION,
        "seeds": list(partition.seeds),
        "source_states": [
            {
                "action_count": len(row.candidates),
                "decision_index": row.decision_index,
                "return_spread": max(row.action_returns) - min(row.action_returns),
                "seed": row.seed,
                "source_sha256": row.source_sha256,
            }
            for row in partition.rows
        ],
    }


def restore_entry_bootstrap(checkpoint_bytes: bytes) -> runtime.PairedBootstrap:
    try:
        checkpoint = json.loads(checkpoint_bytes.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CounterfactualRankingBlocked("entry checkpoint JSON is invalid") from exc
    if not isinstance(checkpoint, dict) or _canonical_ascii(checkpoint) != checkpoint_bytes:
        raise CounterfactualRankingBlocked("entry checkpoint is not canonical")
    if checkpoint.get("schema_version") != ENTRY_CHECKPOINT_SCHEMA_VERSION:
        raise CounterfactualRankingBlocked("entry checkpoint schema differs")
    coordinates = checkpoint.get("coordinates")
    if not isinstance(coordinates, dict) or coordinates != {
        "candidate_optimizer_steps": 4,
        "completed_decisions": coordinates.get("completed_decisions"),
        "completed_pairs": 256,
        "environment_accesses": 512,
        "next_chunk_index": 4,
    } or not isinstance(coordinates["completed_decisions"], int):
        raise CounterfactualRankingBlocked("entry checkpoint coordinates differ")
    try:
        bootstrap = runtime.restore_paired_bootstrap(
            _canonical_ascii(checkpoint["bootstrap"])
        )
    except (KeyError, runtime.SuccessorRuntimeError) as exc:
        raise CounterfactualRankingBlocked("entry bootstrap restore failed") from exc
    return bootstrap


def _joint_log_probabilities(
    bootstrap: runtime.PairedBootstrap,
    row: CounterfactualRankingRow,
) -> torch.Tensor:
    try:
        output = runtime.forward_card_policy(
            bootstrap,
            arm="candidate",
            state_features=row.state_features,
            candidate_features=row.candidate_features,
            candidates=row.candidates,
        )
        terms = build_card_acceptance_policy_terms(
            output.family_logits,
            output.conditional_logits,
            row.candidates,
            row.candidates[0]["action_id"],
            category="card_reward",
        )
    except (
        CardAcceptanceObjectiveError,
        runtime.SuccessorRuntimeError,
        RuntimeError,
        ValueError,
    ) as exc:
        raise CounterfactualRankingBlocked("card ranking forward failed") from exc
    return terms.joint_log_probabilities


def pairwise_ranking_loss(
    bootstrap: runtime.PairedBootstrap,
    rows: Sequence[CounterfactualRankingRow],
) -> torch.Tensor:
    weighted_losses: list[torch.Tensor] = []
    weights: list[float] = []
    for row in rows:
        log_probabilities = _joint_log_probabilities(bootstrap, row)
        for left in range(len(row.action_returns)):
            for right in range(left + 1, len(row.action_returns)):
                difference = row.action_returns[left] - row.action_returns[right]
                if difference == 0:
                    continue
                better, worse = (left, right) if difference > 0 else (right, left)
                weight = abs(difference)
                weighted_losses.append(
                    weight
                    * F.softplus(
                        -(log_probabilities[better] - log_probabilities[worse])
                    )
                )
                weights.append(weight)
    if not weighted_losses or math.fsum(weights) <= 0:
        raise CounterfactualRankingBlocked("ranking rows contain no unequal returns")
    loss = torch.stack(weighted_losses).sum() / math.fsum(weights)
    if loss.ndim != 0 or not bool(torch.isfinite(loss).item()):
        raise CounterfactualRankingBlocked("ranking loss is invalid")
    return loss


def evaluate_ranking(
    bootstrap: runtime.PairedBootstrap,
    rows: Sequence[CounterfactualRankingRow],
) -> dict[str, Any]:
    normalized_rows = tuple(rows)
    if not normalized_rows:
        raise CounterfactualRankingBlocked("ranking evaluation requires rows")
    predictions: list[dict[str, Any]] = []
    regrets: list[float] = []
    pair_weight = 0.0
    correct_weight = 0.0
    unique_count = 0
    unique_correct = 0
    with torch.no_grad():
        for row in normalized_rows:
            log_probabilities = _joint_log_probabilities(bootstrap, row)
            maximum_log_probability = torch.amax(log_probabilities)
            predicted_indices = [
                index
                for index, value in enumerate(log_probabilities)
                if bool(torch.eq(value, maximum_log_probability).item())
            ]
            predicted_index = min(
                predicted_indices,
                key=lambda index: row.candidates[index]["action_id"],
            )
            best_return = max(row.action_returns)
            best_indices = [
                index
                for index, value in enumerate(row.action_returns)
                if value == best_return
            ]
            regret = best_return - row.action_returns[predicted_index]
            regrets.append(regret)
            if len(best_indices) == 1:
                unique_count += 1
                unique_correct += int(predicted_index == best_indices[0])
            for left in range(len(row.action_returns)):
                for right in range(left + 1, len(row.action_returns)):
                    difference = row.action_returns[left] - row.action_returns[right]
                    if difference == 0:
                        continue
                    better, worse = (left, right) if difference > 0 else (right, left)
                    weight = abs(difference)
                    log_difference = float(
                        (log_probabilities[better] - log_probabilities[worse]).item()
                    )
                    pair_weight += weight
                    correct_weight += weight * (
                        1.0 if log_difference > 0 else 0.5 if log_difference == 0 else 0.0
                    )
            predictions.append(
                {
                    "actual_best_action_ids": sorted(
                        row.candidates[index]["action_id"] for index in best_indices
                    ),
                    "decision_index": row.decision_index,
                    "predicted_action_id": row.candidates[predicted_index]["action_id"],
                    "regret": regret,
                    "seed": row.seed,
                    "source_sha256": row.source_sha256,
                }
            )
    if pair_weight <= 0 or unique_count == 0:
        raise CounterfactualRankingBlocked("ranking evaluation support is insufficient")
    return {
        "maximum_top_action_regret": max(regrets),
        "mean_top_action_regret": math.fsum(regrets) / len(regrets),
        "predictions": predictions,
        "source_states": len(normalized_rows),
        "unique_best_accuracy": unique_correct / unique_count,
        "unique_best_correct": unique_correct,
        "unique_best_states": unique_count,
        "weighted_pairwise_accuracy": correct_weight / pair_weight,
        "weighted_pairwise_margin": pair_weight,
    }


def _guard_bytes(bootstrap: runtime.PairedBootstrap) -> bytes:
    try:
        return pilot._warm_start_guard_bytes(bootstrap)
    except pilot.CardOnlyPilotBlocked as exc:
        raise CounterfactualRankingBlocked(str(exc)) from exc


def train_counterfactual_ranking(
    bootstrap: runtime.PairedBootstrap,
    *,
    train_rows: Sequence[CounterfactualRankingRow],
    holdout_rows: Sequence[CounterfactualRankingRow],
    training_steps: int = TRAINING_STEPS,
) -> CompletedCounterfactualRankingTraining:
    if isinstance(training_steps, bool) or not isinstance(training_steps, int) or training_steps <= 0:
        raise CounterfactualRankingBlocked("training step count is invalid")
    train_rows = tuple(train_rows)
    holdout_rows = tuple(holdout_rows)
    if {row.source_sha256 for row in train_rows} & {
        row.source_sha256 for row in holdout_rows
    }:
        raise CounterfactualRankingBlocked("train and holdout sources overlap")
    if {row.seed for row in train_rows} & {row.seed for row in holdout_rows}:
        raise CounterfactualRankingBlocked("train and holdout seeds overlap")
    entry_model = pilot.encode_candidate_card_policy(bootstrap)
    guard_before = _guard_bytes(bootstrap)
    entry_train = evaluate_ranking(bootstrap, train_rows)
    entry_holdout = evaluate_ranking(bootstrap, holdout_rows)
    optimizer = runtime.build_candidate_card_optimizer(bootstrap)
    if optimizer.state:
        raise CounterfactualRankingBlocked("fresh ranking optimizer has state")
    loss_history: list[float] = []
    for _ in range(training_steps):
        optimizer.zero_grad(set_to_none=True)
        loss = pairwise_ranking_loss(bootstrap, train_rows)
        loss_value = float(loss.detach().item())
        loss_history.append(loss_value)
        loss.backward()
        parameters = [
            parameter
            for group in optimizer.param_groups
            for parameter in group["params"]
        ]
        if any(
            parameter.grad is None
            or not bool(torch.isfinite(parameter.grad).all().item())
            for parameter in parameters
        ):
            raise CounterfactualRankingBlocked("ranking gradients are invalid")
        optimizer.step()
    final_loss = float(pairwise_ranking_loss(bootstrap, train_rows).detach().item())
    trained_train = evaluate_ranking(bootstrap, train_rows)
    trained_holdout = evaluate_ranking(bootstrap, holdout_rows)
    trained_model = pilot.encode_candidate_card_policy(bootstrap)
    if _guard_bytes(bootstrap) != guard_before:
        raise CounterfactualRankingBlocked("frozen/control model state changed")
    if trained_model == entry_model:
        raise CounterfactualRankingBlocked("ranking training did not change the model")

    entry_predictions = {
        row["source_sha256"]: row for row in entry_holdout["predictions"]
    }
    trained_predictions = {
        row["source_sha256"]: row for row in trained_holdout["predictions"]
    }
    action_flips = 0
    corrected_to_best = 0
    for source_sha256, before in entry_predictions.items():
        after = trained_predictions[source_sha256]
        if before["predicted_action_id"] != after["predicted_action_id"]:
            action_flips += 1
        if (
            before["predicted_action_id"] not in before["actual_best_action_ids"]
            and after["predicted_action_id"] in after["actual_best_action_ids"]
        ):
            corrected_to_best += 1

    checks = {
        "corrected_holdout_action": corrected_to_best >= 1,
        "heldout_maximum_regret_nonincreasing": (
            trained_holdout["maximum_top_action_regret"]
            <= entry_holdout["maximum_top_action_regret"]
        ),
        "heldout_mean_regret_decreased": (
            trained_holdout["mean_top_action_regret"]
            < entry_holdout["mean_top_action_regret"]
        ),
        "heldout_pairwise_accuracy_increased": (
            trained_holdout["weighted_pairwise_accuracy"]
            > entry_holdout["weighted_pairwise_accuracy"]
        ),
        "heldout_unique_best_accuracy_nondecreasing": False,
        "train_loss_decreased": final_loss < loss_history[0],
    }
    checks["heldout_unique_best_accuracy_nondecreasing"] = (
        trained_holdout["unique_best_accuracy"]
        >= entry_holdout["unique_best_accuracy"]
    )
    ready = all(checks.values())
    report = {
        "checks": checks,
        "entry_model_sha256": hashlib.sha256(entry_model).hexdigest(),
        "fit": {
            "final_loss": final_loss,
            "first_step_loss": loss_history[0],
            "loss_history": loss_history,
            "optimizer_steps": training_steps,
        },
        "holdout": {
            "action_flips": action_flips,
            "corrected_to_best": corrected_to_best,
            "entry": entry_holdout,
            "trained": trained_holdout,
        },
        "schema_version": TRAINING_REPORT_SCHEMA_VERSION,
        "train": {"entry": entry_train, "trained": trained_train},
        "trained_model_sha256": hashlib.sha256(trained_model).hexdigest(),
        "verdict": (
            "card_counterfactual_ranking_training_ready_for_expansion"
            if ready
            else "card_counterfactual_ranking_training_not_ready"
        ),
    }
    return CompletedCounterfactualRankingTraining(
        report=report,
        entry_model=entry_model,
        trained_model=trained_model,
    )
