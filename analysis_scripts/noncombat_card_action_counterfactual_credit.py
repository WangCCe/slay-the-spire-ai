"""Bounded action-level counterfactual credit for native card-reward states."""

from __future__ import annotations

import copy
import hashlib
import math
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from analysis_scripts import noncombat_card_acceptance_empirical_successor_runtime as successor
from analysis_scripts import noncombat_formal_reward_contract as reward_contract
from analysis_scripts import noncombat_simulator_adapter as adapter


REPORT_SCHEMA_VERSION = "noncombat-card-action-counterfactual-credit-poc-v1"
CONSUMED_DEVELOPMENT_SEEDS = tuple(range(1000, 1008))
MAX_CARD_STATES_PER_SEED = 2
MAX_ACTION_BRANCHES = 64
MAX_DECISIONS_PER_CONTINUATION = successor.MAX_DECISIONS_PER_EPISODE
MIN_COMPLETE_SOURCE_STATES = 8
MIN_INFORMATIVE_SOURCE_STATES = 4
FALSE_DOWNSTREAM_AUTHORITY = {
    name: False
    for name in (
        "causal_claim",
        "cohort_expansion",
        "communication_mod",
        "formal_rl",
        "fresh_evaluation",
        "gameplay",
        "model_fitting",
        "ope",
        "policy_quality",
        "promotion",
        "qualification",
        "threshold_tuning",
        "training",
    )
}


class CounterfactualCreditBlocked(RuntimeError):
    """Raised when comparable action-level evidence cannot be produced."""


@dataclass(frozen=True)
class BranchTrace:
    action_id: str
    action_sequence: tuple[str, ...]
    floor_progress: float
    initial_transition_sha256: str
    terminal_state_sha256: str
    terminal_summary: Mapping[str, Any]
    terminal_victory: int
    total_return: float
    transition_count: int

    def signature(self) -> tuple[Any, ...]:
        return (
            self.action_sequence,
            self.floor_progress,
            self.initial_transition_sha256,
            _sha256_json(dict(self.terminal_summary)),
            self.terminal_state_sha256,
            self.terminal_victory,
            self.total_return,
            self.transition_count,
        )

    def compact(self, candidate: Mapping[str, Any]) -> dict[str, Any]:
        action_sequence_bytes = adapter.canonical_json_bytes(
            list(self.action_sequence)
        )
        return {
            "action_id": self.action_id,
            "action_kind": candidate["kind"],
            "action_label": candidate["label"],
            "action_sequence_length": len(self.action_sequence),
            "action_sequence_sha256": hashlib.sha256(
                action_sequence_bytes
            ).hexdigest(),
            "candidate_sha256": _sha256_json(candidate),
            "floor_progress": self.floor_progress,
            "initial_transition_sha256": self.initial_transition_sha256,
            "terminal_state_sha256": self.terminal_state_sha256,
            "terminal_summary": dict(self.terminal_summary),
            "terminal_victory": self.terminal_victory,
            "total_return": self.total_return,
            "transition_count": self.transition_count,
        }


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(adapter.canonical_json_bytes(value)).hexdigest()


def _environment_state(
    environment: Any,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        return successor._environment_state(environment)
    except successor.SuccessorRuntimeError as exc:
        raise CounterfactualCreditBlocked(str(exc)) from exc


def _assert_source_unchanged(
    environment: Any,
    snapshot: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
) -> None:
    try:
        successor._assert_source_unchanged(environment, snapshot, candidates)
    except successor.SuccessorRuntimeError as exc:
        raise CounterfactualCreditBlocked(str(exc)) from exc


def _validated_transition(
    transition: Any,
    *,
    before: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    selected_action_id: str,
    after: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        return successor._validate_transition(
            transition,
            before=before,
            candidates=candidates,
            selected_action_id=selected_action_id,
            after=after,
        )
    except successor.SuccessorRuntimeError as exc:
        raise CounterfactualCreditBlocked(str(exc)) from exc


def _transition_reward(transition: Mapping[str, Any]) -> tuple[float, float, int]:
    try:
        channels = reward_contract.reward_channels(transition)
        reward_contract.validate_scalarization(
            "strict_primary_dominance", victory_weight=2.0
        )
    except reward_contract.RewardContractBlocked as exc:
        raise CounterfactualCreditBlocked(str(exc)) from exc
    floor_progress = float(channels["floor_progress"])
    terminal_victory = int(channels["terminal_victory"])
    scalar = 2.0 * terminal_victory + floor_progress
    if not all(math.isfinite(value) for value in (floor_progress, scalar)):
        raise CounterfactualCreditBlocked("formal reward must be finite")
    return scalar, floor_progress, terminal_victory


def _clone(environment: Any) -> Any:
    try:
        cloned = environment.clone()
    except Exception as exc:
        raise CounterfactualCreditBlocked("environment clone failed") from exc
    if cloned is environment:
        raise CounterfactualCreditBlocked(
            "environment clone must return a distinct branch"
        )
    return cloned


def _apply_forced_action(environment: Any, action_id: str) -> tuple[Any, dict[str, Any]]:
    before, candidates = _environment_state(environment)
    if action_id not in {candidate["action_id"] for candidate in candidates}:
        raise CounterfactualCreditBlocked("forced action is not source legal")
    successor_environment = _clone(environment)
    try:
        transition = successor_environment.step(action_id)
        after = adapter.validate_snapshot(successor_environment.snapshot())
    except (adapter.SimulatorAdapterError, RuntimeError) as exc:
        raise CounterfactualCreditBlocked("forced card action failed") from exc
    _assert_source_unchanged(environment, before, candidates)
    return successor_environment, _validated_transition(
        transition,
        before=before,
        candidates=candidates,
        selected_action_id=action_id,
        after=after,
    )


def _advance_native(environment: Any) -> tuple[Any, dict[str, Any]]:
    before, candidates = _environment_state(environment)
    if before["terminal"]:
        raise CounterfactualCreditBlocked("cannot advance a terminal environment")
    successor_environment = _clone(environment)
    native_step = getattr(successor_environment, "step_native_baseline", None)
    if not callable(native_step):
        raise CounterfactualCreditBlocked(
            "environment.step_native_baseline must be callable"
        )
    try:
        transition = native_step()
        after = adapter.validate_snapshot(successor_environment.snapshot())
    except (adapter.SimulatorAdapterError, RuntimeError) as exc:
        raise CounterfactualCreditBlocked("native continuation failed") from exc
    selected_action_id = transition.get("selected_action_id") if isinstance(
        transition, Mapping
    ) else None
    if not isinstance(selected_action_id, str):
        raise CounterfactualCreditBlocked("native transition action is invalid")
    _assert_source_unchanged(environment, before, candidates)
    return successor_environment, _validated_transition(
        transition,
        before=before,
        candidates=candidates,
        selected_action_id=selected_action_id,
        after=after,
    )


def _terminal_summary(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    if snapshot.get("terminal") is not True:
        raise CounterfactualCreditBlocked("branch did not reach terminal")
    state = snapshot["state"]
    outcome = state.get("outcome")
    if outcome not in {"player_loss", "player_victory"}:
        raise CounterfactualCreditBlocked("terminal outcome is invalid")
    return {
        "decision_count": snapshot.get("decision_count"),
        "floor": state.get("floor"),
        "outcome": outcome,
        "terminal": True,
    }


def evaluate_action_branch_for_category(
    source_environment: Any,
    *,
    action_id: str,
    source_category: str,
    max_decisions: int = MAX_DECISIONS_PER_CONTINUATION,
    deadline: float | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> BranchTrace:
    """Force one target-category action and use native SimpleAgent to terminal."""
    if isinstance(max_decisions, bool) or not isinstance(max_decisions, int) or (
        max_decisions <= 0
    ):
        raise CounterfactualCreditBlocked("continuation decision ceiling is invalid")
    if source_category not in adapter.TARGET_CATEGORIES:
        raise CounterfactualCreditBlocked("source category is not supported")
    source_snapshot, source_candidates = _environment_state(source_environment)
    if (
        source_snapshot["terminal"]
        or source_snapshot["category"] != source_category
    ):
        raise CounterfactualCreditBlocked(
            f"source must be a live {source_category} state"
        )
    active_deadline = float("inf") if deadline is None else float(deadline)
    if not callable(clock):
        raise CounterfactualCreditBlocked("branch clock must be callable")
    if deadline is not None and not math.isfinite(active_deadline):
        raise CounterfactualCreditBlocked("branch deadline is invalid")

    environment, first_transition = _apply_forced_action(
        source_environment, action_id
    )
    transitions = [first_transition]
    actions = [action_id]
    scalar, progress, victory = _transition_reward(first_transition)
    rewards = [scalar]
    floor_progress = progress
    terminal_victory = victory

    while True:
        if float(clock()) > active_deadline:
            raise CounterfactualCreditBlocked("branch deadline reached")
        snapshot, _ = _environment_state(environment)
        if snapshot["terminal"]:
            break
        if len(transitions) >= max_decisions:
            raise CounterfactualCreditBlocked(
                "continuation decision ceiling reached"
            )
        environment, transition = _advance_native(environment)
        transition_reward, progress, victory = _transition_reward(transition)
        transitions.append(transition)
        actions.append(transition["selected_action_id"])
        rewards.append(transition_reward)
        floor_progress += progress
        terminal_victory = max(terminal_victory, victory)

    _assert_source_unchanged(
        source_environment, source_snapshot, source_candidates
    )
    final_snapshot, final_candidates = _environment_state(environment)
    if final_candidates:
        raise CounterfactualCreditBlocked("terminal branch reported candidates")
    summary = _terminal_summary(final_snapshot)
    return BranchTrace(
        action_id=action_id,
        action_sequence=tuple(actions),
        floor_progress=floor_progress,
        initial_transition_sha256=_sha256_json(first_transition),
        terminal_state_sha256=_sha256_json(final_snapshot["state"]),
        terminal_summary=summary,
        terminal_victory=terminal_victory,
        total_return=math.fsum(rewards),
        transition_count=len(transitions),
    )


def evaluate_action_branch(
    source_environment: Any,
    *,
    action_id: str,
    max_decisions: int = MAX_DECISIONS_PER_CONTINUATION,
    deadline: float | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> BranchTrace:
    """Force one card-reward action and use native SimpleAgent to terminal."""
    return evaluate_action_branch_for_category(
        source_environment,
        action_id=action_id,
        source_category="card_reward",
        max_decisions=max_decisions,
        deadline=deadline,
        clock=clock,
    )


def evaluate_source_state(
    source_environment: Any,
    *,
    seed: int,
    decision_index: int,
    repeat_first_branch: bool,
    max_decisions: int = MAX_DECISIONS_PER_CONTINUATION,
    deadline: float | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Evaluate every legal action at one immutable card-reward source."""
    snapshot, candidates = _environment_state(source_environment)
    if snapshot["terminal"] or snapshot["category"] != "card_reward":
        raise CounterfactualCreditBlocked("eligible source category differs")
    source_sha256 = _sha256_json(
        {"snapshot": snapshot, "candidate_actions": candidates}
    )
    traces: list[BranchTrace] = []
    for candidate in candidates:
        traces.append(
            evaluate_action_branch(
                source_environment,
                action_id=candidate["action_id"],
                max_decisions=max_decisions,
                deadline=deadline,
                clock=clock,
            )
        )
    _assert_source_unchanged(source_environment, snapshot, candidates)

    replay_evidence = None
    if repeat_first_branch:
        replay = evaluate_action_branch(
            source_environment,
            action_id=traces[0].action_id,
            max_decisions=max_decisions,
            deadline=deadline,
            clock=clock,
        )
        replay_evidence = {
            "action_id": traces[0].action_id,
            "first_signature_sha256": _sha256_json(traces[0].signature()),
            "passed": replay.signature() == traces[0].signature(),
            "replay_signature_sha256": _sha256_json(replay.signature()),
            "source_sha256": source_sha256,
        }

    returns = [trace.total_return for trace in traces]
    best_return = max(returns)
    best_indices = [
        index for index, value in enumerate(returns) if value == best_return
    ]
    unique_best = len(best_indices) == 1
    result = {
        "action_count": len(candidates),
        "actions": [
            trace.compact(candidate)
            for trace, candidate in zip(traces, candidates, strict=True)
        ],
        "best_action_id": (
            traces[best_indices[0]].action_id if unique_best else None
        ),
        "decision_index": decision_index,
        "informative_unique_best": unique_best and max(returns) > min(returns),
        "return_spread": max(returns) - min(returns),
        "seed": seed,
        "source_sha256": source_sha256,
        "unique_best": unique_best,
    }
    return result, replay_evidence


def run_counterfactual_credit_poc(
    environment_factory: Callable[[int], Any],
    *,
    seeds: Sequence[int] = CONSUMED_DEVELOPMENT_SEEDS,
    max_card_states_per_seed: int = MAX_CARD_STATES_PER_SEED,
    max_action_branches: int = MAX_ACTION_BRANCHES,
    min_complete_source_states: int = MIN_COMPLETE_SOURCE_STATES,
    min_informative_source_states: int = MIN_INFORMATIVE_SOURCE_STATES,
    max_decisions: int = MAX_DECISIONS_PER_CONTINUATION,
    deadline: float | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    """Run the fixed consumed-seed counterfactual credit POC."""
    if not callable(environment_factory) or not callable(clock):
        raise CounterfactualCreditBlocked("factory and clock must be callable")
    integer_limits = (
        max_card_states_per_seed,
        max_action_branches,
        min_complete_source_states,
        min_informative_source_states,
        max_decisions,
    )
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value <= 0
        for value in integer_limits
    ):
        raise CounterfactualCreditBlocked("POC limits must be positive integers")
    normalized_seeds = tuple(seeds)
    if not normalized_seeds or len(set(normalized_seeds)) != len(normalized_seeds) or any(
        isinstance(seed, bool) or not isinstance(seed, int) or seed < 0
        for seed in normalized_seeds
    ):
        raise CounterfactualCreditBlocked("POC seeds are invalid")
    active_deadline = float("inf") if deadline is None else float(deadline)
    if deadline is not None and not math.isfinite(active_deadline):
        raise CounterfactualCreditBlocked("POC deadline is invalid")

    source_states: list[dict[str, Any]] = []
    deterministic_replay: dict[str, Any] | None = None
    branch_count = 0
    root_transition_count = 0
    budget_exhausted = False
    terminal_seed_count = 0

    for seed in normalized_seeds:
        if float(clock()) > active_deadline:
            raise CounterfactualCreditBlocked("POC deadline reached")
        try:
            environment = environment_factory(seed)
        except Exception as exc:
            raise CounterfactualCreditBlocked(
                f"environment construction failed for seed {seed}"
            ) from exc
        evaluated_for_seed = 0
        decision_index = 0
        while True:
            snapshot, candidates = _environment_state(environment)
            if snapshot["terminal"]:
                terminal_seed_count += 1
                break
            if decision_index >= max_decisions:
                raise CounterfactualCreditBlocked("root decision ceiling reached")
            eligible = (
                snapshot["category"] == "card_reward"
                and evaluated_for_seed < max_card_states_per_seed
            )
            if eligible:
                replay_count = 1 if deterministic_replay is None else 0
                required_branches = len(candidates) + replay_count
                if branch_count + required_branches > max_action_branches:
                    budget_exhausted = True
                    break
                source_result, replay = evaluate_source_state(
                    environment,
                    seed=seed,
                    decision_index=decision_index,
                    repeat_first_branch=replay_count == 1,
                    max_decisions=max_decisions,
                    deadline=(None if deadline is None else active_deadline),
                    clock=clock,
                )
                source_states.append(source_result)
                evaluated_for_seed += 1
                branch_count += required_branches
                if replay is not None:
                    deterministic_replay = replay
            environment, _ = _advance_native(environment)
            root_transition_count += 1
            decision_index += 1
        if budget_exhausted:
            break

    complete_count = len(source_states)
    informative_count = sum(
        int(source["informative_unique_best"]) for source in source_states
    )
    determinism_passed = bool(
        deterministic_replay is not None and deterministic_replay["passed"]
    )
    signal_viable = (
        complete_count >= min_complete_source_states
        and informative_count >= min_informative_source_states
        and determinism_passed
    )
    return {
        "configuration": {
            "maximum_action_branches": max_action_branches,
            "maximum_card_states_per_seed": max_card_states_per_seed,
            "maximum_decisions_per_continuation": max_decisions,
            "minimum_complete_source_states": min_complete_source_states,
            "minimum_informative_source_states": min_informative_source_states,
            "seeds": list(normalized_seeds),
        },
        "deterministic_replay": deterministic_replay,
        "downstream_authority": copy.deepcopy(FALSE_DOWNSTREAM_AUTHORITY),
        "schema_version": REPORT_SCHEMA_VERSION,
        "source_states": source_states,
        "summary": {
            "action_branch_continuations": branch_count,
            "budget_exhausted": budget_exhausted,
            "complete_source_states": complete_count,
            "determinism_passed": determinism_passed,
            "informative_unique_best_states": informative_count,
            "root_native_transitions": root_transition_count,
            "terminal_seed_count": terminal_seed_count,
        },
        "verdict": (
            "card_action_counterfactual_credit_viable"
            if signal_viable
            else "card_action_counterfactual_credit_not_ready"
        ),
    }
