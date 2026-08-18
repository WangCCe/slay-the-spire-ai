"""Run a bounded simulator-only combat RL training smoke on CPU."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import random
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping, Sequence

import numpy as np
import torch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from analysis_scripts.combat_lightspeed_bridge import (  # noqa: E402
    ACTION_DIM,
    CARD_SLOTS,
    CONTINUOUS_DIM,
    MAX_BATTLE_INDEX,
    POTION_SLOTS,
    RELIC_SLOTS,
    SOURCE_TYPE,
    MappedCombatState,
    NativeCombatEnvironment,
    canonical_json_bytes,
    collect_provenance,
    load_native_module,
    sha256_bytes,
    sha256_file,
    validate_card_select_settlement,
)
from spirecomm.ai.rl.checkpoint_io import (  # noqa: E402
    load_torch_checkpoint,
    save_torch_checkpoint,
)
from spirecomm.ai.rl.v2.id_mapping import IdMapper, build_id_mapper  # noqa: E402
from spirecomm.ai.rl.v2.trainer import DQNTrainerV2  # noqa: E402


REPORT_SCHEMA_VERSION = "combat-lightspeed-training-smoke-v4"
CHECKPOINT_KIND = "simulator_training_smoke"
REPORT_AUTHORITY = {
    "gameplay": False,
    "larger_simulator_experiment": False,
    "live_policy_quality": False,
    "mechanics_equivalence": False,
    "production_checkpoint_loading": False,
    "production_checkpoint_writing": False,
    "promotion": False,
    "qualification": False,
    "simulator_fitting": True,
    "transfer": False,
}
EXPECTED_UNREACHABLE_PROFILE_REASONS = frozenset(
    {
        "baseline_loss_before_requested_battle",
        "baseline_run_terminated_before_battle",
    }
)


@dataclass(frozen=True)
class SmokeConfig:
    train_seeds: tuple[int, ...]
    evaluation_seeds: tuple[int, ...]
    battle_indices: tuple[int, ...] = (0,)
    ascension: int = 0
    max_decisions_per_seed: int = 80
    max_actions_per_turn: int = 8
    behavior_seed: int = 2026081901
    network_seed: int = 2026081902
    batch_size: int = 128
    optimizer_steps: int = 64

    def validate(self) -> None:
        if not self.train_seeds or not self.evaluation_seeds:
            raise ValueError("train and evaluation seeds must be non-empty")
        if len(set(self.train_seeds)) != len(self.train_seeds):
            raise ValueError("training seeds must be unique")
        if len(set(self.evaluation_seeds)) != len(self.evaluation_seeds):
            raise ValueError("evaluation seeds must be unique")
        if set(self.train_seeds).intersection(self.evaluation_seeds):
            raise ValueError("training and evaluation seeds must be disjoint")
        if any(seed < 0 for seed in (*self.train_seeds, *self.evaluation_seeds)):
            raise ValueError("seeds must be non-negative")
        if not self.battle_indices:
            raise ValueError("at least one battle index is required")
        if len(set(self.battle_indices)) != len(self.battle_indices):
            raise ValueError("battle indices must be unique")
        if any(not 0 <= value <= MAX_BATTLE_INDEX for value in self.battle_indices):
            raise ValueError(f"battle indices must be in 0..{MAX_BATTLE_INDEX}")
        if not 0 <= self.ascension <= 20:
            raise ValueError("ascension must be in 0..20")
        if self.max_decisions_per_seed <= 0 or self.max_actions_per_turn <= 0:
            raise ValueError("decision and per-turn action bounds must be positive")
        if self.batch_size <= 1 or self.optimizer_steps <= 0:
            raise ValueError("batch size and optimizer steps must be positive")

    def profiles(self, seeds: Sequence[int]) -> tuple[tuple[int, int], ...]:
        return tuple(
            (seed, battle_index)
            for seed in seeds
            for battle_index in self.battle_indices
        )


@dataclass(frozen=True)
class ReplayTransition:
    continuous: np.ndarray
    card_ids: np.ndarray
    potion_ids: np.ndarray
    relic_ids: np.ndarray
    action: int
    reward: float
    next_continuous: np.ndarray
    next_card_ids: np.ndarray
    next_potion_ids: np.ndarray
    next_relic_ids: np.ndarray
    done: bool
    action_mask: np.ndarray
    next_action_mask: np.ndarray


def initialization_failure_reason(value: object) -> str:
    text = str(value)
    if text.startswith("initialization_failure:"):
        text = text.split(":", 1)[1]
    return text.split(":", 1)[0] or type(value).__name__


def unexpected_initialization_failures(
    counts: Mapping[str, int],
) -> dict[str, int]:
    return {
        reason: int(count)
        for reason, count in counts.items()
        if reason not in EXPECTED_UNREACHABLE_PROFILE_REASONS and int(count) > 0
    }


def select_behavior_action(
    actions: Sequence[Mapping[str, Any]],
    *,
    rng: random.Random,
    actions_since_end_turn: int,
    max_actions_per_turn: int,
) -> dict[str, Any]:
    available = [dict(action) for action in actions if action.get("available", True)]
    if not available:
        raise ValueError("no legal simulator actions")
    ordered = sorted(available, key=lambda action: int(action["rl_action_index"]))
    end_turn = next((action for action in ordered if action.get("kind") == "end_turn"), None)
    if end_turn is None:
        raise ValueError("legal simulator actions omit End Turn")
    non_end_turn = [action for action in ordered if action.get("kind") != "end_turn"]
    if actions_since_end_turn >= max_actions_per_turn or not non_end_turn:
        return end_turn
    return non_end_turn[rng.randrange(len(non_end_turn))]


def _state(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    value = snapshot.get("state")
    if not isinstance(value, Mapping):
        raise ValueError("native snapshot omits state")
    return dict(value)


def _alive_monsters(state: Mapping[str, Any]) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for raw in state.get("monsters") or []:
        monster = dict(raw)
        slot = int(monster["native_slot"])
        result[slot] = monster
    return result


def calculate_native_reward(
    before_snapshot: Mapping[str, Any],
    after_snapshot: Mapping[str, Any],
    *,
    action_kind: str,
    outcome: str,
) -> dict[str, Any]:
    before = _state(before_snapshot)
    after = _state(after_snapshot)
    before_monsters = _alive_monsters(before)
    after_monsters = _alive_monsters(after)
    damage_dealt = 0
    kills = 0
    for slot, monster in before_monsters.items():
        before_hp = max(int(monster.get("current_hp", 0)), 0)
        after_monster = after_monsters.get(slot, {})
        after_hp = max(int(after_monster.get("current_hp", 0)), 0)
        damage_dealt += max(before_hp - after_hp, 0)
        if before_hp > 0 and after_hp <= 0:
            kills += 1

    before_player = dict(before.get("player") or {})
    after_player = dict(after.get("player") or {})
    before_hp = int(before_player.get("current_hp", 0))
    after_hp = int(after_player.get("current_hp", 0))
    max_hp = max(int(before_player.get("max_hp", 0)), 1)
    hp_lost = max(before_hp - after_hp, 0)
    turn_ended = int(after.get("turn", 0)) > int(before.get("turn", 0))
    all_lethal = outcome == "player_victory"
    total = (
        damage_dealt * 0.05
        + kills * 10.0
        + (20.0 if all_lethal else 0.0)
        - 50.0 * hp_lost / max_hp
        + (-0.05 if turn_ended else 0.0)
    )
    return {
        "damage_dealt": damage_dealt,
        "kills": kills,
        "all_lethal": all_lethal,
        "hp_lost": hp_lost,
        "turn_ended": turn_ended,
        "action_kind": action_kind,
        "total": float(total),
    }


def successor_disposition(status: Mapping[str, Any]) -> tuple[str, str]:
    if bool(status.get("terminal")):
        return "terminal", str(status.get("outcome") or "unknown")
    if bool(status.get("supported")):
        return "supported", ""
    reason = str(status.get("unsupported_reason") or status.get("input_state") or "unknown")
    return "exclude", reason


def create_fresh_trainer(
    id_mapper: IdMapper,
    *,
    seed: int,
    batch_size: int,
    learning_starts: int,
    buffer_size: int = 100_000,
) -> DQNTrainerV2:
    random.seed(seed)
    np.random.seed(seed % (2**32))
    torch.manual_seed(seed)
    trainer = DQNTrainerV2(
        continuous_dim=CONTINUOUS_DIM,
        action_dim=ACTION_DIM,
        card_slots=CARD_SLOTS,
        potion_slots=POTION_SLOTS,
        relic_slots=RELIC_SLOTS,
        card_vocab=id_mapper.card_vocab_size,
        potion_vocab=id_mapper.potion_vocab_size,
        relic_vocab=id_mapper.relic_vocab_size,
        batch_size=batch_size,
        learning_starts=learning_starts,
        buffer_size=buffer_size,
        train_freq=1,
        target_update_freq=10_000_000,
        epsilon_start=0.0,
        epsilon_end=0.0,
        device="cpu",
        network_type="dueling",
    )
    return trainer


def parameter_sha256(state_dict: Mapping[str, torch.Tensor]) -> str:
    digest = hashlib.sha256()
    for name in sorted(state_dict):
        tensor = state_dict[name].detach().cpu().contiguous()
        name_bytes = name.encode("utf-8")
        digest.update(len(name_bytes).to_bytes(4, "big"))
        digest.update(name_bytes)
        digest.update(str(tensor.dtype).encode("ascii"))
        digest.update(canonical_json_bytes(list(tensor.shape)))
        digest.update(tensor.numpy().tobytes())
    return digest.hexdigest()


def parameter_delta(
    before: Mapping[str, torch.Tensor],
    after: Mapping[str, torch.Tensor],
) -> dict[str, float]:
    squared = 0.0
    maximum = 0.0
    for name in sorted(before):
        difference = after[name].detach().cpu().double() - before[name].detach().cpu().double()
        squared += float(torch.sum(difference * difference).item())
        if difference.numel():
            maximum = max(maximum, float(torch.max(torch.abs(difference)).item()))
    return {"l2": math.sqrt(squared), "max_abs": maximum}


def load_initial_checkpoint(
    path: Path,
    *,
    expected_sha256: str | None,
) -> dict[str, Any]:
    resolved = path.resolve()
    if not resolved.is_file():
        raise ValueError(f"initial checkpoint does not exist: {resolved}")
    actual_sha256 = sha256_file(resolved)
    if expected_sha256 is not None and actual_sha256 != expected_sha256.lower():
        raise ValueError(
            "initial checkpoint hash mismatch: "
            f"expected {expected_sha256.lower()}, got {actual_sha256}"
        )
    checkpoint = load_torch_checkpoint(str(resolved), map_location="cpu")
    if not isinstance(checkpoint, Mapping):
        raise ValueError("initial checkpoint root must be a mapping")
    if checkpoint.get("checkpoint_kind") != CHECKPOINT_KIND:
        raise ValueError("initial checkpoint kind must be simulator_training_smoke")
    if checkpoint.get("production_compatible") is not False:
        raise ValueError("initial checkpoint must not be production-compatible")
    state_dict = checkpoint.get("online_network_state_dict")
    if not isinstance(state_dict, Mapping) or not state_dict:
        raise ValueError("initial checkpoint online state is missing or empty")
    state = dict(state_dict)
    if any(not isinstance(value, torch.Tensor) for value in state.values()):
        raise ValueError("initial checkpoint online state contains non-tensor values")
    return {
        "path": str(resolved),
        "checkpoint_sha256": actual_sha256,
        "size_bytes": resolved.stat().st_size,
        "checkpoint_schema_version": checkpoint.get("checkpoint_schema_version"),
        "checkpoint_kind": CHECKPOINT_KIND,
        "source_type": checkpoint.get("source_type"),
        "production_compatible": False,
        "parameter_sha256": parameter_sha256(state),
        "state_dict": state,
    }


def initialize_trainer(
    trainer: DQNTrainerV2,
    initial_checkpoint: Mapping[str, Any] | None,
) -> tuple[dict[str, torch.Tensor], dict[str, Any]]:
    if initial_checkpoint is None:
        state = copy.deepcopy(trainer.online_network.state_dict())
        return state, {
            "mode": "fresh",
            "parameter_sha256": parameter_sha256(state),
        }

    state = initial_checkpoint.get("state_dict")
    if not isinstance(state, Mapping):
        raise ValueError("initial checkpoint state_dict is missing")
    try:
        trainer.online_network.load_state_dict(state, strict=True)
        trainer.target_network.load_state_dict(state, strict=True)
    except (KeyError, RuntimeError, TypeError, ValueError) as exc:
        raise ValueError(f"initial checkpoint network incompatible: {exc}") from exc
    trainer.target_network.eval()
    control = copy.deepcopy(trainer.online_network.state_dict())
    record = {
        key: value
        for key, value in initial_checkpoint.items()
        if key != "state_dict"
    }
    record["mode"] = "warm_start"
    loaded_sha256 = parameter_sha256(control)
    if loaded_sha256 != record.get("parameter_sha256"):
        raise ValueError("initial checkpoint parameter hash changed during load")
    return control, record


def _terminal_next_state() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    return (
        np.zeros(CONTINUOUS_DIM, dtype=np.float32),
        np.zeros(CARD_SLOTS, dtype=np.int64),
        np.zeros(POTION_SLOTS, dtype=np.int64),
        np.zeros(RELIC_SLOTS, dtype=np.int64),
        np.zeros(ACTION_DIM, dtype=bool),
    )


def _transition(
    current: MappedCombatState,
    *,
    action_index: int,
    reward: float,
    successor: MappedCombatState | None,
    done: bool,
) -> ReplayTransition:
    if successor is None:
        next_continuous, next_cards, next_potions, next_relics, next_mask = _terminal_next_state()
    else:
        next_continuous = successor.state.continuous.copy()
        next_cards = successor.state.card_ids.copy()
        next_potions = successor.state.potion_ids.copy()
        next_relics = successor.state.relic_ids.copy()
        next_mask = successor.action_mask.copy()
    return ReplayTransition(
        continuous=current.state.continuous.copy(),
        card_ids=current.state.card_ids.copy(),
        potion_ids=current.state.potion_ids.copy(),
        relic_ids=current.state.relic_ids.copy(),
        action=action_index,
        reward=reward,
        next_continuous=next_continuous,
        next_card_ids=next_cards,
        next_potion_ids=next_potions,
        next_relic_ids=next_relics,
        done=done,
        action_mask=current.action_mask.copy(),
        next_action_mask=next_mask,
    )


def collect_transitions(
    native_module: ModuleType,
    *,
    id_mapper: IdMapper,
    config: SmokeConfig,
) -> tuple[list[ReplayTransition], dict[str, Any]]:
    transitions: list[ReplayTransition] = []
    actions = Counter()
    outcomes = Counter()
    unsupported = Counter()
    encounters = Counter()
    rewards: list[float] = []
    settlement_actions = 0
    settlement_tasks = Counter()
    settlement_transitions = 0
    truncated = 0
    initialization_failures = Counter()
    progression_battle_indices = Counter()
    progression_acts = Counter()
    progression_encounters = Counter()
    initialized_profiles = 0

    for seed, battle_index in config.profiles(config.train_seeds):
        try:
            environment = NativeCombatEnvironment.reset(
                native_module,
                seed,
                config.ascension,
                battle_index,
            )
        except Exception as exc:
            initialization_failures[initialization_failure_reason(exc)] += 1
            continue
        progression = dict(environment.snapshot().get("progression") or {})
        progression_battle_indices[int(progression["reached_battle_index"])] += 1
        progression_acts[int(progression["act"])] += 1
        progression_encounters[str(progression["encounter"])] += 1
        initialized_profiles += 1
        rng = random.Random(config.behavior_seed ^ seed ^ (battle_index << 32))
        actions_since_end_turn = 0
        for _ in range(config.max_decisions_per_seed):
            status = environment.status()
            disposition, reason = successor_disposition(status)
            if disposition == "terminal":
                outcomes[reason] += 1
                break
            if disposition == "exclude":
                unsupported[reason] += 1
                break

            current = environment.mapped_state(id_mapper=id_mapper)
            before = environment.snapshot()
            encounters[str(_state(before).get("encounter") or "unknown")] += 1
            selected = select_behavior_action(
                environment.legal_actions(),
                rng=rng,
                actions_since_end_turn=actions_since_end_turn,
                max_actions_per_turn=config.max_actions_per_turn,
            )
            action_index = int(selected["rl_action_index"])
            if not bool(current.action_mask[action_index]):
                raise RuntimeError("selected simulator action is absent from the RL mask")

            successor_environment = environment.clone()
            successor_environment.step(str(selected["action_id"]))
            after = successor_environment.snapshot()
            settlement = validate_card_select_settlement(
                after.get("card_select_settlement")
            )
            if settlement["count"]:
                settlement_transitions += 1
                settlement_actions += int(settlement["count"])
                settlement_tasks.update(settlement["tasks"])
            successor_status = successor_environment.status()
            successor_kind, successor_reason = successor_disposition(successor_status)
            reward_record = calculate_native_reward(
                before,
                after,
                action_kind=str(selected["kind"]),
                outcome=str(successor_status.get("outcome") or "undecided"),
            )
            if successor_kind == "exclude":
                unsupported[successor_reason] += 1
                break
            successor_mapped = (
                None
                if successor_kind == "terminal"
                else successor_environment.mapped_state(id_mapper=id_mapper)
            )
            transitions.append(
                _transition(
                    current,
                    action_index=action_index,
                    reward=float(reward_record["total"]),
                    successor=successor_mapped,
                    done=successor_kind == "terminal",
                )
            )
            rewards.append(float(reward_record["total"]))
            family = str(selected["kind"])
            actions[family] += 1
            environment = successor_environment
            actions_since_end_turn = 0 if family == "end_turn" else actions_since_end_turn + 1
            if successor_kind == "terminal":
                outcomes[successor_reason] += 1
                break
        else:
            truncated += 1

    reward_array = np.asarray(rewards, dtype=np.float64)
    return transitions, {
        "accepted_transition_count": len(transitions),
        "action_family_counts": dict(sorted(actions.items())),
        "decision_bound_seed_count": truncated,
        "encounter_state_counts": dict(sorted(encounters.items())),
        "outcome_counts": dict(sorted(outcomes.items())),
        "reward": {
            "count": len(rewards),
            "mean": float(reward_array.mean()) if len(reward_array) else 0.0,
            "minimum": float(reward_array.min()) if len(reward_array) else 0.0,
            "maximum": float(reward_array.max()) if len(reward_array) else 0.0,
            "sum": float(reward_array.sum()) if len(reward_array) else 0.0,
        },
        "card_select_settlement": {
            "action_count": settlement_actions,
            "task_counts": dict(sorted(settlement_tasks.items())),
            "transition_count": settlement_transitions,
        },
        "initialization_failure_counts": dict(sorted(initialization_failures.items())),
        "profile_count_initialized": initialized_profiles,
        "profile_count_registered": len(config.profiles(config.train_seeds)),
        "progression_coverage": {
            "act_counts": dict(sorted(progression_acts.items())),
            "battle_index_counts": dict(sorted(progression_battle_indices.items())),
            "encounter_counts": dict(sorted(progression_encounters.items())),
        },
        "seed_count": len(config.train_seeds),
        "unsupported_reason_counts": dict(sorted(unsupported.items())),
    }


def insert_transitions(trainer: DQNTrainerV2, transitions: Sequence[ReplayTransition]) -> int:
    accepted = 0
    for row in transitions:
        if trainer.store_transition(
            row.continuous,
            row.card_ids,
            row.potion_ids,
            row.relic_ids,
            row.action,
            row.reward,
            row.next_continuous,
            row.next_card_ids,
            row.next_potion_ids,
            row.next_relic_ids,
            row.done,
            action_mask=row.action_mask,
            next_action_mask=row.next_action_mask,
        ):
            accepted += 1
    return accepted


def run_optimizer(trainer: DQNTrainerV2, steps: int) -> list[float]:
    if len(trainer.replay_buffer) < trainer.learning_starts:
        raise RuntimeError("replay does not satisfy learning_starts")
    trainer.target_update_freq = trainer.total_steps + 1
    losses: list[float] = []
    for _ in range(steps):
        loss = trainer.train_step()
        if loss is None or not math.isfinite(loss):
            raise RuntimeError(f"optimizer returned invalid loss: {loss}")
        losses.append(float(loss))
    return losses


def _policy_action(
    trainer: DQNTrainerV2,
    mapped: MappedCombatState,
    actions: Sequence[Mapping[str, Any]],
    *,
    actions_since_end_turn: int,
    max_actions_per_turn: int,
) -> dict[str, Any]:
    if actions_since_end_turn >= max_actions_per_turn:
        return next(dict(action) for action in actions if action.get("kind") == "end_turn")
    index = trainer.select_action(
        mapped.state.continuous,
        mapped.state.card_ids,
        mapped.state.potion_ids,
        mapped.state.relic_ids,
        mapped.action_mask,
        training=False,
    )
    return next(dict(action) for action in actions if int(action["rl_action_index"]) == index)


def evaluate_policy(
    native_module: ModuleType,
    *,
    id_mapper: IdMapper,
    trainer: DQNTrainerV2,
    seeds: Sequence[int],
    config: SmokeConfig,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    was_training = trainer.online_network.training
    trainer.online_network.eval()
    try:
        for seed, battle_index in config.profiles(seeds):
            try:
                environment = NativeCombatEnvironment.reset(
                    native_module,
                    seed,
                    config.ascension,
                    battle_index,
                )
            except Exception as exc:
                rows.append(
                    {
                        "seed": int(seed),
                        "battle_index": int(battle_index),
                        "outcome": "initialization_failure",
                        "player_hp": 0,
                        "decisions": 0,
                        "reward": 0.0,
                        "initialization_failure_reason": initialization_failure_reason(exc),
                        "unsupported_reason": f"initialization_failure:{exc}",
                        "truncated": False,
                        "card_select_settlement_count": 0,
                        "card_select_settlement_task_counts": {},
                    }
                )
                continue
            progression = dict(environment.snapshot().get("progression") or {})
            actions_since_end_turn = 0
            total_reward = 0.0
            decisions = 0
            unsupported_reason = ""
            outcome = "undecided"
            truncated = False
            settlement_actions = 0
            settlement_tasks = Counter()
            for _ in range(config.max_decisions_per_seed):
                status = environment.status()
                disposition, reason = successor_disposition(status)
                if disposition == "terminal":
                    outcome = reason
                    break
                if disposition == "exclude":
                    unsupported_reason = reason
                    break
                mapped = environment.mapped_state(id_mapper=id_mapper)
                legal = environment.legal_actions()
                selected = _policy_action(
                    trainer,
                    mapped,
                    legal,
                    actions_since_end_turn=actions_since_end_turn,
                    max_actions_per_turn=config.max_actions_per_turn,
                )
                before = environment.snapshot()
                environment.step(str(selected["action_id"]))
                status = environment.status()
                after = environment.snapshot()
                settlement = validate_card_select_settlement(
                    after.get("card_select_settlement")
                )
                settlement_actions += int(settlement["count"])
                settlement_tasks.update(settlement["tasks"])
                total_reward += calculate_native_reward(
                    before,
                    after,
                    action_kind=str(selected["kind"]),
                    outcome=str(status.get("outcome") or "undecided"),
                )["total"]
                decisions += 1
                actions_since_end_turn = (
                    0 if selected["kind"] == "end_turn" else actions_since_end_turn + 1
                )
            else:
                truncated = True
            final_state = _state(environment.snapshot())
            rows.append(
                {
                    "seed": int(seed),
                    "battle_index": int(battle_index),
                    "progression": progression,
                    "outcome": outcome,
                    "player_hp": int(dict(final_state.get("player") or {}).get("current_hp", 0)),
                    "decisions": decisions,
                    "reward": float(total_reward),
                    "unsupported_reason": unsupported_reason,
                    "truncated": truncated,
                    "card_select_settlement_count": settlement_actions,
                    "card_select_settlement_task_counts": dict(
                        sorted(settlement_tasks.items())
                    ),
                }
            )
    finally:
        trainer.online_network.train(was_training)

    rewards = np.asarray([row["reward"] for row in rows], dtype=np.float64)
    hp = np.asarray([row["player_hp"] for row in rows], dtype=np.float64)
    decisions = np.asarray([row["decisions"] for row in rows], dtype=np.float64)
    settlement_tasks = Counter()
    for row in rows:
        settlement_tasks.update(row["card_select_settlement_task_counts"])
    return {
        "rows": rows,
        "aggregate": {
            "mean_decisions": float(decisions.mean()),
            "mean_player_hp": float(hp.mean()),
            "mean_reward": float(rewards.mean()),
            "player_loss_count": sum(row["outcome"] == "player_loss" for row in rows),
            "player_victory_count": sum(row["outcome"] == "player_victory" for row in rows),
            "seed_count": len(rows),
            "profile_count": len(rows),
            "profile_count_initialized": sum(
                row["outcome"] != "initialization_failure" for row in rows
            ),
            "profile_count_unreachable": sum(
                row["outcome"] == "initialization_failure"
                and row.get("initialization_failure_reason")
                in EXPECTED_UNREACHABLE_PROFILE_REASONS
                for row in rows
            ),
            "truncated_count": sum(bool(row["truncated"]) for row in rows),
            "unsupported_count": sum(
                bool(row["unsupported_reason"])
                and row["outcome"] != "initialization_failure"
                for row in rows
            ),
            "card_select_settlement_action_count": sum(
                int(row["card_select_settlement_count"]) for row in rows
            ),
            "card_select_settlement_seed_count": sum(
                int(row["card_select_settlement_count"]) > 0 for row in rows
            ),
            "card_select_settlement_task_counts": dict(sorted(settlement_tasks.items())),
        },
    }


def paired_evaluation(control: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, Any]:
    control_rows = {
        (int(row["seed"]), int(row.get("battle_index", 0))): row
        for row in control["rows"]
    }
    candidate_rows = {
        (int(row["seed"]), int(row.get("battle_index", 0))): row
        for row in candidate["rows"]
    }
    if set(control_rows) != set(candidate_rows):
        raise RuntimeError("paired evaluation seed mismatch")
    rows = []
    excluded_initialization_failures = Counter()
    for seed, battle_index in sorted(control_rows):
        left = control_rows[(seed, battle_index)]
        right = candidate_rows[(seed, battle_index)]
        left_initialization_failure = left["outcome"] == "initialization_failure"
        right_initialization_failure = right["outcome"] == "initialization_failure"
        if left_initialization_failure or right_initialization_failure:
            if left_initialization_failure != right_initialization_failure:
                raise RuntimeError("paired evaluation initialization mismatch")
            left_reason = initialization_failure_reason(
                left.get("initialization_failure_reason")
                or left.get("unsupported_reason")
            )
            right_reason = initialization_failure_reason(
                right.get("initialization_failure_reason")
                or right.get("unsupported_reason")
            )
            if left_reason != right_reason:
                raise RuntimeError("paired evaluation initialization reason mismatch")
            excluded_initialization_failures[left_reason] += 1
            continue
        rows.append(
            {
                "seed": seed,
                "battle_index": battle_index,
                "control_outcome": left["outcome"],
                "candidate_outcome": right["outcome"],
                "player_hp_delta": right["player_hp"] - left["player_hp"],
                "reward_delta": right["reward"] - left["reward"],
                "decision_delta": right["decisions"] - left["decisions"],
            }
        )
    player_hp_deltas = [row["player_hp_delta"] for row in rows]
    reward_deltas = [row["reward_delta"] for row in rows]
    return {
        "rows": rows,
        "aggregate": {
            "profile_count": len(rows),
            "excluded_initialization_profile_count": sum(
                excluded_initialization_failures.values()
            ),
            "excluded_initialization_failure_counts": dict(
                sorted(excluded_initialization_failures.items())
            ),
            "mean_player_hp_delta": float(np.mean(player_hp_deltas)) if rows else 0.0,
            "mean_reward_delta": float(np.mean(reward_deltas)) if rows else 0.0,
            "candidate_only_victories": sum(
                row["candidate_outcome"] == "player_victory"
                and row["control_outcome"] != "player_victory"
                for row in rows
            ),
            "control_only_victories": sum(
                row["control_outcome"] == "player_victory"
                and row["candidate_outcome"] != "player_victory"
                for row in rows
            ),
        },
    }


def _publish(
    output_dir: Path,
    *,
    report: dict[str, Any],
    candidate_state: Mapping[str, torch.Tensor] | None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=False)
    candidate_path = output_dir / "simulator_only_candidate.pth"
    if candidate_state is not None:
        source_binding = {
            "adapter_source_sha256": report["provenance"]["adapter_source_sha256"],
            "module_sha256": report["provenance"]["module_sha256"],
            "simulator_source_sha256": report["provenance"]["simulator_source_sha256"],
            "training_runner_sha256": report["provenance"]["training_runner_sha256"],
            "config_sha256": sha256_bytes(canonical_json_bytes(report["config"])),
            "initial_parameter_sha256": report["training"]["initial_parameter_sha256"],
            "candidate_parameter_sha256": report["training"]["candidate_parameter_sha256"],
        }
        if report["initialization"]["mode"] == "warm_start":
            source_binding["initial_checkpoint_sha256"] = report["initialization"][
                "checkpoint_sha256"
            ]
            source_binding["initial_checkpoint_parameter_sha256"] = report[
                "initialization"
            ]["parameter_sha256"]
        checkpoint = {
            "checkpoint_schema_version": 0,
            "checkpoint_kind": CHECKPOINT_KIND,
            "source_type": SOURCE_TYPE,
            "production_compatible": False,
            "online_network_state_dict": dict(candidate_state),
            "metadata": {
                "authority": dict(REPORT_AUTHORITY),
                "report_schema_version": REPORT_SCHEMA_VERSION,
                "source_binding": source_binding,
            },
        }
        save_torch_checkpoint(checkpoint, str(candidate_path))
        report["candidate"] = {
            "path": candidate_path.name,
            "sha256": sha256_file(candidate_path),
            "size_bytes": candidate_path.stat().st_size,
            "checkpoint_kind": CHECKPOINT_KIND,
            "production_compatible": False,
        }

    summary = "\n".join(
        (
            "# Combat LightSTS Training Smoke",
            "",
            f"- Verdict: `{report['verdict']}`",
            f"- Replay transitions: `{report.get('training', {}).get('replay_transition_count', 0)}`",
            f"- Optimizer updates: `{report.get('training', {}).get('optimizer_update_count', 0)}`",
            f"- Parameter L2 delta: `{report.get('training', {}).get('parameter_delta', {}).get('l2', 0.0)}`",
            f"- Held-out paired metrics: `{json.dumps(report.get('evaluation', {}).get('paired', {}).get('aggregate', {}), sort_keys=True)}`",
            "",
            "This simulator-only smoke grants no gameplay, transfer, qualification,",
            "promotion, mechanics-equivalence, or live policy-quality authority.",
            "",
        )
    ).encode("utf-8")
    report_bytes = canonical_json_bytes(report) + b"\n"
    artifacts = {
        "report.json": report_bytes,
        "summary.md": summary,
    }
    manifest_entries = {
        name: {"sha256": sha256_bytes(data), "size_bytes": len(data)}
        for name, data in artifacts.items()
    }
    if candidate_path.is_file():
        manifest_entries[candidate_path.name] = {
            "sha256": sha256_file(candidate_path),
            "size_bytes": candidate_path.stat().st_size,
        }
    manifest = {
        "schema_version": "combat-lightspeed-training-smoke-manifest-v4",
        "artifacts": manifest_entries,
    }
    artifacts["manifest.json"] = canonical_json_bytes(manifest) + b"\n"
    for name, data in artifacts.items():
        temporary = output_dir / f".{name}.tmp"
        temporary.write_bytes(data)
        temporary.replace(output_dir / name)


def run_smoke(
    native_module: ModuleType,
    *,
    id_mapper: IdMapper,
    config: SmokeConfig,
    provenance: Mapping[str, Any],
    initial_checkpoint: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, torch.Tensor]]:
    config.validate()
    trainer = create_fresh_trainer(
        id_mapper,
        seed=config.network_seed,
        batch_size=config.batch_size,
        learning_starts=config.batch_size,
    )
    initial, initialization = initialize_trainer(trainer, initial_checkpoint)
    initial_sha256 = parameter_sha256(initial)
    transitions, corpus_metrics = collect_transitions(
        native_module,
        id_mapper=id_mapper,
        config=config,
    )
    accepted = insert_transitions(trainer, transitions)
    if accepted != len(transitions):
        raise RuntimeError(f"replay rejected transitions: {accepted}/{len(transitions)}")
    losses = run_optimizer(trainer, config.optimizer_steps)
    candidate = copy.deepcopy(trainer.online_network.state_dict())
    candidate_sha256 = parameter_sha256(candidate)
    delta = parameter_delta(initial, candidate)

    trainer.online_network.load_state_dict(initial)
    control_evaluation = evaluate_policy(
        native_module,
        id_mapper=id_mapper,
        trainer=trainer,
        seeds=config.evaluation_seeds,
        config=config,
    )
    trainer.online_network.load_state_dict(candidate)
    candidate_evaluation = evaluate_policy(
        native_module,
        id_mapper=id_mapper,
        trainer=trainer,
        seeds=config.evaluation_seeds,
        config=config,
    )
    paired = paired_evaluation(control_evaluation, candidate_evaluation)

    blockers = []
    if not transitions:
        blockers.append("no_replay_transitions")
    if len(losses) != config.optimizer_steps or not all(math.isfinite(value) for value in losses):
        blockers.append("optimizer_incomplete")
    if delta["l2"] <= 0.0 or initial_sha256 == candidate_sha256:
        blockers.append("parameters_unchanged")
    if unexpected_initialization_failures(
        corpus_metrics["initialization_failure_counts"]
    ):
        blockers.append("training_profile_initialization_failure")
    if (
        control_evaluation["aggregate"]["profile_count"]
        != len(config.profiles(config.evaluation_seeds))
        or candidate_evaluation["aggregate"]["profile_count"]
        != len(config.profiles(config.evaluation_seeds))
    ):
        blockers.append("held_out_evaluation_incomplete")
    if any(
        row["outcome"] == "initialization_failure"
        and initialization_failure_reason(
            row.get("initialization_failure_reason") or row.get("unsupported_reason")
        )
        not in EXPECTED_UNREACHABLE_PROFILE_REASONS
        for evaluation in (control_evaluation, candidate_evaluation)
        for row in evaluation["rows"]
    ):
        blockers.append("evaluation_profile_initialization_failure")
    if paired["aggregate"]["profile_count"] == 0:
        blockers.append("held_out_evaluation_empty")
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "source_type": SOURCE_TYPE,
        "authority": dict(REPORT_AUTHORITY),
        "config": asdict(config),
        "provenance": dict(provenance),
        "initialization": initialization,
        "reward_definition": {
            "damage_scale": 0.05,
            "kill_reward": 10.0,
            "all_lethal_bonus": 20.0,
            "hp_loss_ratio_penalty": 50.0,
            "turn_end_penalty": -0.05,
            "omitted_channels": [
                "vulnerable_damage_bonus",
                "enemy_strength_gain_penalty",
                "progression",
                "acquisition",
                "run_terminal",
            ],
        },
        "corpus": corpus_metrics,
        "training": {
            "initial_parameter_sha256": initial_sha256,
            "candidate_parameter_sha256": candidate_sha256,
            "parameter_delta": delta,
            "replay_transition_count": accepted,
            "optimizer_update_count": len(losses),
            "loss_first": losses[0],
            "loss_last": losses[-1],
            "loss_mean": float(np.mean(losses)),
            "loss_minimum": float(np.min(losses)),
            "loss_maximum": float(np.max(losses)),
        },
        "evaluation": {
            "control": control_evaluation,
            "candidate": candidate_evaluation,
            "paired": paired,
        },
        "blockers": blockers,
        "verdict": "technical_smoke_ready" if not blockers else "technical_smoke_not_ready",
        "next_gate": {
            "larger_simulator_experiment_authorized": False,
            "live_transfer_authorized": False,
            "requirements": [
                "review held-out simulator metrics before sizing a larger run",
                "pre-register any larger simulator cohort and optimizer budget",
                "require matched real-game divergence evidence before transfer or qualification",
            ],
        },
    }
    return report, candidate


def _parse_seeds(value: str) -> tuple[int, ...]:
    text = value.strip()
    if ".." in text:
        start_text, end_text = text.split("..", 1)
        start, end = int(start_text), int(end_text)
        if end < start:
            raise argparse.ArgumentTypeError("seed range end must not precede start")
        return tuple(range(start, end + 1))
    return tuple(int(part.strip()) for part in text.split(",") if part.strip())


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--simulator-repo", required=True, type=Path)
    parser.add_argument("--module", required=True, type=Path)
    parser.add_argument("--dll-dir", action="append", default=[], type=Path)
    parser.add_argument("--items-json", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--train-seeds", default="0..255", type=_parse_seeds)
    parser.add_argument("--evaluation-seeds", default="10000..10063", type=_parse_seeds)
    parser.add_argument("--battle-indices", default="0", type=_parse_seeds)
    parser.add_argument("--ascension", default=0, type=int)
    parser.add_argument("--max-decisions-per-seed", default=80, type=int)
    parser.add_argument("--max-actions-per-turn", default=8, type=int)
    parser.add_argument("--behavior-seed", default=2026081901, type=int)
    parser.add_argument("--network-seed", default=2026081902, type=int)
    parser.add_argument("--batch-size", default=128, type=int)
    parser.add_argument("--optimizer-steps", default=64, type=int)
    parser.add_argument("--initial-checkpoint", type=Path)
    parser.add_argument("--initial-checkpoint-sha256")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if bool(args.initial_checkpoint) != bool(args.initial_checkpoint_sha256):
        raise ValueError(
            "--initial-checkpoint and --initial-checkpoint-sha256 must be supplied together"
        )
    config = SmokeConfig(
        train_seeds=args.train_seeds,
        evaluation_seeds=args.evaluation_seeds,
        battle_indices=args.battle_indices,
        ascension=args.ascension,
        max_decisions_per_seed=args.max_decisions_per_seed,
        max_actions_per_turn=args.max_actions_per_turn,
        behavior_seed=args.behavior_seed,
        network_seed=args.network_seed,
        batch_size=args.batch_size,
        optimizer_steps=args.optimizer_steps,
    )
    native_module = load_native_module(args.module, dll_directories=args.dll_dir)
    provenance = collect_provenance(
        repo_root=args.repo_root,
        simulator_repo=args.simulator_repo,
        module_path=args.module,
        native_module=native_module,
    )
    provenance["training_runner_sha256"] = sha256_file(Path(__file__))
    initial_checkpoint = None
    if args.initial_checkpoint is not None:
        initial_checkpoint = load_initial_checkpoint(
            args.initial_checkpoint,
            expected_sha256=args.initial_checkpoint_sha256,
        )
    report, candidate = run_smoke(
        native_module,
        id_mapper=build_id_mapper(args.items_json),
        config=config,
        provenance=provenance,
        initial_checkpoint=initial_checkpoint,
    )
    _publish(args.output_dir.resolve(), report=report, candidate_state=candidate)
    print(json.dumps({"output_dir": str(args.output_dir.resolve()), "verdict": report["verdict"]}))
    return 0 if report["verdict"] == "technical_smoke_ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
