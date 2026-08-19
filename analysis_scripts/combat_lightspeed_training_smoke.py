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
from dataclasses import asdict, dataclass, replace
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
from spirecomm.ai.rl.v2.network import create_dqn_v2  # noqa: E402
from spirecomm.ai.rl.v2.trainer import DQNTrainerV2  # noqa: E402
from spirecomm.ai.rl.v2.types import EncodedStateV2  # noqa: E402


REPORT_SCHEMA_VERSION = "combat-lightspeed-training-smoke-v10"
CHECKPOINT_KIND = "simulator_training_smoke"
ONE_STEP_TD_TARGET = "one-step-td"
DISCOUNTED_EPISODE_RETURN_TARGET = "discounted-episode-return"
FROZEN_PARENT_N_STEP_TARGET = "frozen-parent-n-step-return"
ENCOUNTER_HASH_ALGORITHM = "sha256-first-8-bytes-modulo"
ENCOUNTER_ENUM_ENCODING = "monster-encounter-enum-v1"
MAX_ENCOUNTER_IDENTITY_BUCKETS = 1024
ENCOUNTER_PARENT_EQUIVALENCE_TOLERANCE = 1e-5
ENCOUNTER_ENUM_V1 = (
    "CULTIST",
    "JAW_WORM",
    "TWO_LOUSE",
    "SMALL_SLIMES",
    "BLUE_SLAVER",
    "GREMLIN_GANG",
    "LOOTER",
    "LARGE_SLIME",
    "LOTS_OF_SLIMES",
    "EXORDIUM_THUGS",
    "EXORDIUM_WILDLIFE",
    "RED_SLAVER",
    "THREE_LOUSE",
    "TWO_FUNGI_BEASTS",
    "GREMLIN_NOB",
    "LAGAVULIN",
    "THREE_SENTRIES",
    "SLIME_BOSS",
    "THE_GUARDIAN",
    "HEXAGHOST",
    "SPHERIC_GUARDIAN",
    "CHOSEN",
    "SHELL_PARASITE",
    "THREE_BYRDS",
    "TWO_THIEVES",
    "CHOSEN_AND_BYRDS",
    "SENTRY_AND_SPHERE",
    "SNAKE_PLANT",
    "SNECKO",
    "CENTURION_AND_HEALER",
    "CULTIST_AND_CHOSEN",
    "THREE_CULTIST",
    "SHELLED_PARASITE_AND_FUNGI",
    "GREMLIN_LEADER",
    "SLAVERS",
    "BOOK_OF_STABBING",
    "AUTOMATON",
    "COLLECTOR",
    "CHAMP",
    "THREE_DARKLINGS",
    "ORB_WALKER",
    "THREE_SHAPES",
    "SPIRE_GROWTH",
    "TRANSIENT",
    "FOUR_SHAPES",
    "MAW",
    "SPHERE_AND_TWO_SHAPES",
    "JAW_WORM_HORDE",
    "WRITHING_MASS",
    "GIANT_HEAD",
    "NEMESIS",
    "REPTOMANCER",
    "AWAKENED_ONE",
    "TIME_EATER",
    "DONU_AND_DECA",
    "SHIELD_AND_SPEAR",
    "THE_HEART",
    "LAGAVULIN_EVENT",
    "COLOSSEUM_EVENT_SLAVERS",
    "COLOSSEUM_EVENT_NOBS",
    "MASKED_BANDITS_EVENT",
    "MUSHROOMS_EVENT",
    "MYSTERIOUS_SPHERE_EVENT",
)
ENCOUNTER_ENUM_V1_IDS = {
    encounter: index + 1 for index, encounter in enumerate(ENCOUNTER_ENUM_V1)
}
ENCOUNTER_ENUM_V1_SHA256 = sha256_bytes(canonical_json_bytes(ENCOUNTER_ENUM_V1))
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
    parent_policy_anchor_weight: float = 0.0
    parent_end_turn_margin_guard_weight: float = 0.0
    parent_end_turn_margin_guard_cap: float = 0.1
    balance_replay_by_battle_index: bool = False
    replay_balance_seed: int = 2026081903
    encounter_identity_buckets: int = 0
    encounter_identity_encoding: str = ENCOUNTER_HASH_ALGORITHM
    replay_target_mode: str = ONE_STEP_TD_TARGET
    replay_return_discount: float = 0.99
    replay_return_horizon: int = 3
    complete_trajectories_only: bool = False

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
        if (
            not math.isfinite(self.parent_policy_anchor_weight)
            or self.parent_policy_anchor_weight < 0.0
        ):
            raise ValueError(
                "parent policy anchor weight must be finite and non-negative"
            )
        if (
            not math.isfinite(self.parent_end_turn_margin_guard_weight)
            or self.parent_end_turn_margin_guard_weight < 0.0
        ):
            raise ValueError(
                "parent end-turn margin guard weight must be finite and non-negative"
            )
        if (
            not math.isfinite(self.parent_end_turn_margin_guard_cap)
            or self.parent_end_turn_margin_guard_cap < 0.0
        ):
            raise ValueError(
                "parent end-turn margin guard cap must be finite and non-negative"
            )
        if (
            self.parent_end_turn_margin_guard_weight > 0.0
            and self.parent_end_turn_margin_guard_cap <= 0.0
        ):
            raise ValueError(
                "positive end-turn margin guard weight requires a positive cap"
            )
        if self.replay_balance_seed < 0:
            raise ValueError("replay balance seed must be non-negative")
        if self.encounter_identity_buckets != 0 and not (
            2 <= self.encounter_identity_buckets <= MAX_ENCOUNTER_IDENTITY_BUCKETS
        ):
            raise ValueError(
                "encounter identity buckets must be zero or in "
                f"2..{MAX_ENCOUNTER_IDENTITY_BUCKETS}"
            )
        if self.encounter_identity_encoding not in {
            ENCOUNTER_HASH_ALGORITHM,
            ENCOUNTER_ENUM_ENCODING,
        }:
            raise ValueError("unknown encounter identity encoding")
        if (
            self.encounter_identity_encoding == ENCOUNTER_ENUM_ENCODING
            and self.encounter_identity_buckets != 64
        ):
            raise ValueError("enum-v1 encounter identity requires exactly 64 buckets")
        if self.replay_target_mode not in {
            ONE_STEP_TD_TARGET,
            DISCOUNTED_EPISODE_RETURN_TARGET,
            FROZEN_PARENT_N_STEP_TARGET,
        }:
            raise ValueError("unknown replay target mode")
        if not math.isfinite(self.replay_return_discount) or not (
            0.0 < self.replay_return_discount <= 1.0
        ):
            raise ValueError("replay return discount must be finite and in (0, 1]")
        if (
            not isinstance(self.replay_return_horizon, int)
            or isinstance(self.replay_return_horizon, bool)
            or self.replay_return_horizon <= 0
        ):
            raise ValueError("replay return horizon must be a positive integer")
        if (
            self.replay_target_mode
            in {DISCOUNTED_EPISODE_RETURN_TARGET, FROZEN_PARENT_N_STEP_TARGET}
            and not self.complete_trajectories_only
        ):
            raise ValueError(
                "discounted and n-step returns require complete trajectories only"
            )

    def profiles(self, seeds: Sequence[int]) -> tuple[tuple[int, int], ...]:
        return tuple(
            (seed, battle_index)
            for seed in seeds
            for battle_index in self.battle_indices
        )


@dataclass(frozen=True)
class ReplayTransition:
    battle_index: int
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
    seed: int = 0
    decision_index: int = 0


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


def encounter_identity_bucket(
    encounter: object,
    bucket_count: int,
    *,
    encoding: str = ENCOUNTER_HASH_ALGORITHM,
) -> int:
    if not 2 <= bucket_count <= MAX_ENCOUNTER_IDENTITY_BUCKETS:
        raise ValueError("encounter identity bucket count is not enabled")
    if not isinstance(encounter, str) or not encounter:
        raise ValueError("encounter identity must be a non-empty string")
    if encoding == ENCOUNTER_ENUM_ENCODING:
        if bucket_count != 64:
            raise ValueError("enum-v1 encounter identity requires exactly 64 buckets")
        try:
            return ENCOUNTER_ENUM_V1_IDS[encounter]
        except KeyError as exc:
            raise ValueError(f"unknown enum-v1 encounter identity: {encounter}") from exc
    if encoding != ENCOUNTER_HASH_ALGORITHM:
        raise ValueError("unknown encounter identity encoding")
    digest = hashlib.sha256(encounter.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % bucket_count


def append_encounter_identity(
    continuous: np.ndarray,
    *,
    encounter: object,
    bucket_count: int,
    encoding: str = ENCOUNTER_HASH_ALGORITHM,
) -> np.ndarray:
    values = np.asarray(continuous, dtype=np.float32)
    if values.shape != (CONTINUOUS_DIM,):
        raise ValueError(f"legacy continuous observation has invalid shape: {values.shape}")
    if bucket_count == 0:
        return values.copy()
    bucket = encounter_identity_bucket(
        encounter,
        bucket_count,
        encoding=encoding,
    )
    result = np.zeros(CONTINUOUS_DIM + bucket_count, dtype=np.float32)
    result[:CONTINUOUS_DIM] = values
    result[CONTINUOUS_DIM + bucket] = 1.0
    return result


def encounter_from_snapshot(snapshot: Mapping[str, Any]) -> str:
    encounter = _state(snapshot).get("encounter")
    if not isinstance(encounter, str) or not encounter:
        raise ValueError("native snapshot omits encounter identity")
    return encounter


def augment_mapped_state(
    mapped: MappedCombatState,
    snapshot: Mapping[str, Any],
    *,
    bucket_count: int,
    encoding: str = ENCOUNTER_HASH_ALGORITHM,
) -> MappedCombatState:
    if bucket_count == 0:
        return mapped
    encounter = encounter_from_snapshot(snapshot)
    return MappedCombatState(
        state=EncodedStateV2(
            continuous=append_encounter_identity(
                mapped.state.continuous,
                encounter=encounter,
                bucket_count=bucket_count,
                encoding=encoding,
            ),
            card_ids=mapped.state.card_ids.copy(),
            potion_ids=mapped.state.potion_ids.copy(),
            relic_ids=mapped.state.relic_ids.copy(),
        ),
        action_mask=mapped.action_mask.copy(),
    )


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
    parent_policy_anchor_weight: float = 0.0,
    parent_end_turn_margin_guard_weight: float = 0.0,
    parent_end_turn_margin_guard_cap: float = 0.1,
    continuous_dim: int = CONTINUOUS_DIM,
) -> DQNTrainerV2:
    random.seed(seed)
    np.random.seed(seed % (2**32))
    torch.manual_seed(seed)
    trainer = DQNTrainerV2(
        continuous_dim=continuous_dim,
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
        parent_policy_anchor_weight=parent_policy_anchor_weight,
        parent_end_turn_margin_guard_weight=parent_end_turn_margin_guard_weight,
        parent_end_turn_margin_guard_cap=parent_end_turn_margin_guard_cap,
    )
    return trainer


def migrate_parent_for_encounter_identity(
    source: Mapping[str, torch.Tensor],
    target: Mapping[str, torch.Tensor],
    *,
    bucket_count: int,
) -> dict[str, torch.Tensor]:
    if not 2 <= bucket_count <= MAX_ENCOUNTER_IDENTITY_BUCKETS:
        raise ValueError("encounter identity bucket count is not enabled")
    first_weight = "hidden_layers.0.weight"
    if set(source) != set(target) or first_weight not in source:
        raise ValueError("encounter parent network keys are incompatible")
    migrated: dict[str, torch.Tensor] = {}
    for name in sorted(target):
        source_tensor = source[name]
        target_tensor = target[name]
        if name != first_weight:
            if source_tensor.shape != target_tensor.shape:
                raise ValueError(
                    f"encounter parent tensor shape mismatch for {name}: "
                    f"{tuple(source_tensor.shape)} != {tuple(target_tensor.shape)}"
                )
            migrated[name] = source_tensor.detach().cpu().clone()
            continue
        if (
            source_tensor.ndim != 2
            or target_tensor.ndim != 2
            or source_tensor.shape[0] != target_tensor.shape[0]
            or source_tensor.shape[1] < CONTINUOUS_DIM
            or target_tensor.shape[1] != source_tensor.shape[1] + bucket_count
        ):
            raise ValueError(
                "encounter parent first-layer shape is incompatible: "
                f"{tuple(source_tensor.shape)} -> {tuple(target_tensor.shape)}"
            )
        expanded = torch.zeros_like(target_tensor, device="cpu")
        source_cpu = source_tensor.detach().cpu()
        expanded[:, :CONTINUOUS_DIM] = source_cpu[:, :CONTINUOUS_DIM]
        expanded[:, CONTINUOUS_DIM + bucket_count :] = source_cpu[:, CONTINUOUS_DIM:]
        migrated[name] = expanded
    return migrated


def encounter_parent_equivalence_passes(
    *,
    max_abs_q_delta: float,
    action_mismatch_count: int,
    tolerance: float = ENCOUNTER_PARENT_EQUIVALENCE_TOLERANCE,
) -> bool:
    return (
        math.isfinite(max_abs_q_delta)
        and 0.0 <= max_abs_q_delta <= tolerance
        and action_mismatch_count == 0
    )


def prove_encounter_parent_equivalence(
    trainer: DQNTrainerV2,
    source: Mapping[str, torch.Tensor],
    *,
    bucket_count: int,
    probe_count: int = 16,
    tolerance: float = ENCOUNTER_PARENT_EQUIVALENCE_TOLERANCE,
) -> dict[str, Any]:
    network = trainer.online_network
    was_training = network.training
    torch_rng_state = torch.random.get_rng_state()
    try:
        legacy = create_dqn_v2(
            network_type=trainer.network_type,
            continuous_dim=CONTINUOUS_DIM,
            action_dim=trainer.action_dim,
            card_vocab=network.card_embedding.num_embeddings,
            potion_vocab=network.potion_embedding.num_embeddings,
            relic_vocab=network.relic_embedding.num_embeddings,
            device="cpu",
            card_embed_dim=network.card_embedding.embedding_dim,
            potion_embed_dim=network.potion_embedding.embedding_dim,
            relic_embed_dim=network.relic_embedding.embedding_dim,
            card_slots=trainer.card_slots,
            potion_slots=trainer.potion_slots,
            relic_slots=trainer.relic_slots,
        )
        legacy.load_state_dict(source, strict=True)
        legacy.eval()
        network.eval()

        rng = np.random.default_rng(2026081926)
        continuous = rng.random((probe_count, CONTINUOUS_DIM), dtype=np.float32)
        encounter_features = np.zeros((probe_count, bucket_count), dtype=np.float32)
        encounter_features[
            np.arange(probe_count), np.arange(probe_count) % bucket_count
        ] = 1.0
        augmented = np.concatenate((continuous, encounter_features), axis=1)
        card_ids = rng.integers(
            0,
            network.card_embedding.num_embeddings,
            size=(probe_count, trainer.card_slots),
            dtype=np.int64,
        )
        potion_ids = rng.integers(
            0,
            network.potion_embedding.num_embeddings,
            size=(probe_count, trainer.potion_slots),
            dtype=np.int64,
        )
        relic_ids = rng.integers(
            0,
            network.relic_embedding.num_embeddings,
            size=(probe_count, trainer.relic_slots),
            dtype=np.int64,
        )
        action_mask = np.fromfunction(
            lambda row, action: (row + action) % 3 != 0,
            (probe_count, trainer.action_dim),
            dtype=int,
        ).astype(bool)
        action_mask[:, 0] = True

        def tensor(value: np.ndarray) -> torch.Tensor:
            return torch.from_numpy(value)

        with torch.no_grad():
            legacy_q = legacy(
                tensor(continuous).float(),
                tensor(card_ids).long(),
                tensor(potion_ids).long(),
                tensor(relic_ids).long(),
                tensor(action_mask),
            )
            migrated_q = network(
                tensor(augmented).float(),
                tensor(card_ids).long(),
                tensor(potion_ids).long(),
                tensor(relic_ids).long(),
                tensor(action_mask),
            )
        valid = tensor(action_mask)
        max_abs_q_delta = float(
            torch.max(torch.abs(legacy_q[valid] - migrated_q[valid])).item()
        )
        action_mismatch_count = int(
            (legacy_q.argmax(dim=1) != migrated_q.argmax(dim=1)).sum().item()
        )
    finally:
        torch.random.set_rng_state(torch_rng_state)
        network.train(was_training)
    passed = encounter_parent_equivalence_passes(
        max_abs_q_delta=max_abs_q_delta,
        action_mismatch_count=action_mismatch_count,
        tolerance=tolerance,
    )
    return {
        "action_mismatch_count": action_mismatch_count,
        "max_abs_q_delta": max_abs_q_delta,
        "passed": passed,
        "probe_count": probe_count,
        "tolerance": tolerance,
    }


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
    *,
    encounter_identity_buckets: int = 0,
    encounter_identity_encoding: str = ENCOUNTER_HASH_ALGORITHM,
) -> tuple[dict[str, torch.Tensor], dict[str, Any]]:
    if initial_checkpoint is None:
        if encounter_identity_buckets:
            raise ValueError(
                "encounter identity requires a warm-start simulator checkpoint"
            )
        if (
            trainer.parent_policy_anchor_weight > 0.0
            or trainer.parent_end_turn_margin_guard_weight > 0.0
        ):
            raise ValueError(
                "positive frozen-parent objective requires a warm-start checkpoint"
            )
        state = copy.deepcopy(trainer.online_network.state_dict())
        return state, {
            "mode": "fresh",
            "parameter_sha256": parameter_sha256(state),
            "parent_policy_anchor_weight": 0.0,
            "parent_end_turn_margin_guard_weight": 0.0,
            "parent_end_turn_margin_guard_cap": trainer.parent_end_turn_margin_guard_cap,
        }

    state = initial_checkpoint.get("state_dict")
    if not isinstance(state, Mapping):
        raise ValueError("initial checkpoint state_dict is missing")
    source_state = dict(state)
    if encounter_identity_buckets:
        state = migrate_parent_for_encounter_identity(
            source_state,
            trainer.online_network.state_dict(),
            bucket_count=encounter_identity_buckets,
        )
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
    if encounter_identity_buckets:
        record["mode"] = "warm_start_encounter_expansion"
        record["source_parameter_sha256"] = record.get("parameter_sha256")
        record["parameter_sha256"] = loaded_sha256
        equivalence = prove_encounter_parent_equivalence(
            trainer,
            source_state,
            bucket_count=encounter_identity_buckets,
        )
        if not equivalence["passed"]:
            raise ValueError(f"encounter parent equivalence failed: {equivalence}")
        first_weight = "hidden_layers.0.weight"
        encounter_columns = control[first_weight][
            :, CONTINUOUS_DIM : CONTINUOUS_DIM + encounter_identity_buckets
        ]
        record["encounter_identity_migration"] = {
            "bucket_count": encounter_identity_buckets,
            "encoding": encounter_identity_encoding,
            "hash_algorithm": (
                ENCOUNTER_HASH_ALGORITHM
                if encounter_identity_encoding == ENCOUNTER_HASH_ALGORITHM
                else None
            ),
            "inserted_column_max_abs": float(torch.max(torch.abs(encounter_columns)).item()),
            "migrated_parameter_sha256": loaded_sha256,
            "source_parameter_sha256": record["source_parameter_sha256"],
            "vocabulary_sha256": (
                ENCOUNTER_ENUM_V1_SHA256
                if encounter_identity_encoding == ENCOUNTER_ENUM_ENCODING
                else None
            ),
            "equivalence": equivalence,
        }
    elif loaded_sha256 != record.get("parameter_sha256"):
        raise ValueError("initial checkpoint parameter hash changed during load")
    record["parent_policy_anchor_weight"] = trainer.parent_policy_anchor_weight
    record["parent_end_turn_margin_guard_weight"] = (
        trainer.parent_end_turn_margin_guard_weight
    )
    record["parent_end_turn_margin_guard_cap"] = (
        trainer.parent_end_turn_margin_guard_cap
    )
    if (
        trainer.parent_policy_anchor_weight > 0.0
        or trainer.parent_end_turn_margin_guard_weight > 0.0
    ):
        trainer.set_parent_policy_anchor(control)
        record["parent_policy_anchor_parameter_sha256"] = parameter_sha256(
            trainer.parent_policy_anchor_network.state_dict()
        )
    return control, record


def _terminal_next_state(
    continuous_dim: int = CONTINUOUS_DIM,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    return (
        np.zeros(continuous_dim, dtype=np.float32),
        np.zeros(CARD_SLOTS, dtype=np.int64),
        np.zeros(POTION_SLOTS, dtype=np.int64),
        np.zeros(RELIC_SLOTS, dtype=np.int64),
        np.zeros(ACTION_DIM, dtype=bool),
    )


def _transition(
    current: MappedCombatState,
    *,
    seed: int,
    decision_index: int,
    action_index: int,
    reward: float,
    successor: MappedCombatState | None,
    done: bool,
    battle_index: int,
) -> ReplayTransition:
    if successor is None:
        next_continuous, next_cards, next_potions, next_relics, next_mask = _terminal_next_state(
            current.state.continuous.size
        )
    else:
        next_continuous = successor.state.continuous.copy()
        next_cards = successor.state.card_ids.copy()
        next_potions = successor.state.potion_ids.copy()
        next_relics = successor.state.relic_ids.copy()
        next_mask = successor.action_mask.copy()
    return ReplayTransition(
        battle_index=battle_index,
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
        seed=seed,
        decision_index=decision_index,
    )


def select_profile_transitions(
    transitions: Sequence[ReplayTransition],
    *,
    completed: bool,
    incomplete_reason: str,
    complete_trajectories_only: bool,
) -> tuple[list[ReplayTransition], dict[str, Any]]:
    rows = list(transitions)
    if completed:
        return rows, {
            "completed": True,
            "excluded": False,
            "incomplete_reason": "",
            "transition_count": len(rows),
        }
    if not incomplete_reason:
        raise ValueError("incomplete trajectory requires a reason")
    excluded = bool(complete_trajectories_only)
    return ([] if excluded else rows), {
        "completed": False,
        "excluded": excluded,
        "incomplete_reason": incomplete_reason,
        "transition_count": len(rows),
    }


def _reward_summary(values: Sequence[float]) -> dict[str, float | int]:
    array = np.asarray(values, dtype=np.float64)
    return {
        "count": len(values),
        "mean": float(array.mean()) if len(array) else 0.0,
        "minimum": float(array.min()) if len(array) else 0.0,
        "maximum": float(array.max()) if len(array) else 0.0,
        "sum": float(array.sum()) if len(array) else 0.0,
    }


def transition_identity_sha256(
    transitions: Sequence[ReplayTransition],
) -> str:
    digest = hashlib.sha256()
    for row in transitions:
        digest.update(
            canonical_json_bytes(
                {
                    "action": row.action,
                    "battle_index": row.battle_index,
                    "decision_index": row.decision_index,
                    "done": row.done,
                    "reward": row.reward,
                    "seed": row.seed,
                }
            )
        )
        for name, value in (
            ("continuous", row.continuous),
            ("card_ids", row.card_ids),
            ("potion_ids", row.potion_ids),
            ("relic_ids", row.relic_ids),
            ("next_continuous", row.next_continuous),
            ("next_card_ids", row.next_card_ids),
            ("next_potion_ids", row.next_potion_ids),
            ("next_relic_ids", row.next_relic_ids),
            ("action_mask", row.action_mask),
            ("next_action_mask", row.next_action_mask),
        ):
            array = np.ascontiguousarray(value)
            digest.update(
                canonical_json_bytes(
                    {"dtype": array.dtype.str, "name": name, "shape": array.shape}
                )
            )
            digest.update(array.tobytes())
    return digest.hexdigest()


def frozen_parent_bootstrap_values(
    network: torch.nn.Module,
    transitions: Sequence[ReplayTransition],
    *,
    batch_size: int = 1024,
) -> tuple[list[float], str]:
    if batch_size <= 0:
        raise ValueError("bootstrap batch size must be positive")
    source = list(transitions)
    values = [0.0] * len(source)
    nonterminal_indices = [index for index, row in enumerate(source) if not row.done]
    for index in nonterminal_indices:
        if not bool(np.asarray(source[index].next_action_mask, dtype=bool).any()):
            raise ValueError(
                "frozen parent bootstrap requires at least one legal next action: "
                f"{(source[index].seed, source[index].battle_index, source[index].decision_index)}"
            )

    try:
        device = next(network.parameters()).device
    except StopIteration as exc:
        raise ValueError("frozen parent bootstrap network has no parameters") from exc
    was_training = network.training
    network.eval()
    try:
        with torch.no_grad():
            for start in range(0, len(nonterminal_indices), batch_size):
                indices = nonterminal_indices[start : start + batch_size]
                rows = [source[index] for index in indices]
                if not rows:
                    continue
                q_values = network(
                    continuous=torch.from_numpy(
                        np.stack([row.next_continuous for row in rows])
                    )
                    .float()
                    .to(device),
                    card_ids=torch.from_numpy(
                        np.stack([row.next_card_ids for row in rows])
                    )
                    .long()
                    .to(device),
                    potion_ids=torch.from_numpy(
                        np.stack([row.next_potion_ids for row in rows])
                    )
                    .long()
                    .to(device),
                    relic_ids=torch.from_numpy(
                        np.stack([row.next_relic_ids for row in rows])
                    )
                    .long()
                    .to(device),
                    action_mask=torch.from_numpy(
                        np.stack([row.next_action_mask for row in rows])
                    )
                    .bool()
                    .to(device),
                )
                maxima = q_values.max(dim=1).values.detach().cpu()
                if not bool(torch.isfinite(maxima).all()):
                    raise ValueError("frozen parent bootstrap value is not finite")
                for index, value in zip(indices, maxima.tolist()):
                    values[index] = float(value)
    finally:
        network.train(was_training)
    return values, parameter_sha256(network.state_dict())


def prepare_replay_targets(
    transitions: Sequence[ReplayTransition],
    *,
    mode: str,
    discount: float,
    horizon: int | None = None,
    bootstrap_values: Sequence[float] | None = None,
    bootstrap_parameter_sha256: str | None = None,
) -> tuple[list[ReplayTransition], dict[str, Any]]:
    if mode not in {
        ONE_STEP_TD_TARGET,
        DISCOUNTED_EPISODE_RETURN_TARGET,
        FROZEN_PARENT_N_STEP_TARGET,
    }:
        raise ValueError("unknown replay target mode")
    if not math.isfinite(discount) or not 0.0 < discount <= 1.0:
        raise ValueError("replay return discount must be finite and in (0, 1]")
    source = list(transitions)
    source_identity = transition_identity_sha256(source)
    if mode == ONE_STEP_TD_TARGET:
        return source, {
            "mode": mode,
            "discount": None,
            "horizon": None,
            "bootstrap_parameter_sha256": None,
            "bootstrap_target_count": 0,
            "bootstrap_value": _reward_summary([]),
            "source_transition_identity_sha256": source_identity,
            "target_transition_identity_sha256": source_identity,
            "source_reward": _reward_summary([row.reward for row in source]),
            "target_reward": _reward_summary([row.reward for row in source]),
            "terminal_target_count": sum(row.done for row in source),
        }

    is_n_step = mode == FROZEN_PARENT_N_STEP_TARGET
    if is_n_step:
        if not isinstance(horizon, int) or isinstance(horizon, bool) or horizon <= 0:
            raise ValueError("n-step replay return horizon must be a positive integer")
        if bootstrap_values is None or len(bootstrap_values) != len(source):
            raise ValueError("n-step replay returns require one bootstrap value per source row")
        if (
            not isinstance(bootstrap_parameter_sha256, str)
            or len(bootstrap_parameter_sha256) != 64
            or bootstrap_parameter_sha256.lower() != bootstrap_parameter_sha256
            or any(character not in "0123456789abcdef" for character in bootstrap_parameter_sha256)
        ):
            raise ValueError("n-step replay returns require a lowercase parent parameter SHA-256")
        bootstrap = [float(value) for value in bootstrap_values]
        if not all(math.isfinite(value) for value in bootstrap):
            raise ValueError("n-step replay bootstrap values must be finite")
    else:
        bootstrap = []

    groups: dict[tuple[int, int], list[ReplayTransition]] = {}
    source_indices: dict[tuple[int, int, int], int] = {}
    for index, row in enumerate(source):
        key = (row.seed, row.battle_index, row.decision_index)
        if key in source_indices:
            raise ValueError(f"duplicate trajectory decision identity: {key}")
        source_indices[key] = index
        groups.setdefault((row.seed, row.battle_index), []).append(row)
    transformed: dict[tuple[int, int, int], ReplayTransition] = {}
    used_bootstrap_values: list[float] = []
    for profile, rows in groups.items():
        ordered = sorted(rows, key=lambda row: row.decision_index)
        if [row.decision_index for row in ordered] != list(range(len(ordered))):
            raise ValueError(f"trajectory decision identity is not contiguous: {profile}")
        if not ordered or not ordered[-1].done or any(row.done for row in ordered[:-1]):
            label = "n-step return" if is_n_step else "discounted return"
            raise ValueError(f"{label} requires a complete trajectory: {profile}")
        if is_n_step:
            assert horizon is not None
            for start, row in enumerate(ordered):
                target = 0.0
                terminated = False
                for offset in range(horizon):
                    current = ordered[start + offset]
                    target += (discount**offset) * current.reward
                    if current.done:
                        terminated = True
                        break
                if not terminated:
                    bootstrap_row = ordered[start + horizon - 1]
                    bootstrap_index = source_indices[
                        (
                            bootstrap_row.seed,
                            bootstrap_row.battle_index,
                            bootstrap_row.decision_index,
                        )
                    ]
                    bootstrap_value = bootstrap[bootstrap_index]
                    target += (discount**horizon) * bootstrap_value
                    used_bootstrap_values.append(bootstrap_value)
                if not math.isfinite(target):
                    raise ValueError(f"n-step return is not finite: {profile}")
                key = (row.seed, row.battle_index, row.decision_index)
                transformed[key] = replace(row, reward=float(target), done=True)
        else:
            running_return = 0.0
            for row in reversed(ordered):
                running_return = float(row.reward + discount * running_return)
                if not math.isfinite(running_return):
                    raise ValueError(f"discounted return is not finite: {profile}")
                key = (row.seed, row.battle_index, row.decision_index)
                transformed[key] = replace(row, reward=running_return, done=True)
    result = [
        transformed[(row.seed, row.battle_index, row.decision_index)]
        for row in source
    ]
    return result, {
        "mode": mode,
        "discount": float(discount),
        "horizon": horizon if is_n_step else None,
        "bootstrap_parameter_sha256": (
            bootstrap_parameter_sha256 if is_n_step else None
        ),
        "bootstrap_target_count": len(used_bootstrap_values),
        "bootstrap_value": _reward_summary(used_bootstrap_values),
        "source_transition_identity_sha256": source_identity,
        "target_transition_identity_sha256": transition_identity_sha256(result),
        "source_reward": _reward_summary([row.reward for row in source]),
        "target_reward": _reward_summary([row.reward for row in result]),
        "terminal_target_count": len(result),
    }


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
    encounter_assignments: dict[str, int] = {}
    complete_profiles = 0
    incomplete_profiles = 0
    retained_incomplete_profiles = 0
    excluded_incomplete_profiles = 0
    excluded_incomplete_transitions = 0
    incomplete_profile_reasons = Counter()

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
        profile_transitions: list[ReplayTransition] = []
        profile_actions = Counter()
        profile_encounters = Counter()
        profile_rewards: list[float] = []
        profile_settlement_actions = 0
        profile_settlement_tasks = Counter()
        profile_settlement_transitions = 0
        profile_encounter_assignments: dict[str, int] = {}
        completed = False
        incomplete_reason = ""
        for decision_index in range(config.max_decisions_per_seed):
            status = environment.status()
            disposition, reason = successor_disposition(status)
            if disposition == "terminal":
                outcomes[reason] += 1
                completed = True
                break
            if disposition == "exclude":
                unsupported[reason] += 1
                incomplete_reason = reason
                break

            mapped = environment.mapped_state(id_mapper=id_mapper)
            before = environment.snapshot()
            encounter = (
                encounter_from_snapshot(before)
                if config.encounter_identity_buckets
                else str(_state(before).get("encounter") or "unknown")
            )
            if config.encounter_identity_buckets:
                profile_encounter_assignments[encounter] = encounter_identity_bucket(
                    encounter,
                    config.encounter_identity_buckets,
                    encoding=config.encounter_identity_encoding,
                )
            current = augment_mapped_state(
                mapped,
                before,
                bucket_count=config.encounter_identity_buckets,
                encoding=config.encounter_identity_encoding,
            )
            profile_encounters[encounter] += 1
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
                profile_settlement_transitions += 1
                profile_settlement_actions += int(settlement["count"])
                profile_settlement_tasks.update(settlement["tasks"])
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
                incomplete_reason = successor_reason
                break
            successor_mapped = (
                None
                if successor_kind == "terminal"
                else augment_mapped_state(
                    successor_environment.mapped_state(id_mapper=id_mapper),
                    after,
                    bucket_count=config.encounter_identity_buckets,
                    encoding=config.encounter_identity_encoding,
                )
            )
            profile_transitions.append(
                _transition(
                    current,
                    seed=seed,
                    decision_index=decision_index,
                    action_index=action_index,
                    reward=float(reward_record["total"]),
                    successor=successor_mapped,
                    done=successor_kind == "terminal",
                    battle_index=battle_index,
                )
            )
            profile_rewards.append(float(reward_record["total"]))
            family = str(selected["kind"])
            profile_actions[family] += 1
            environment = successor_environment
            actions_since_end_turn = 0 if family == "end_turn" else actions_since_end_turn + 1
            if successor_kind == "terminal":
                outcomes[successor_reason] += 1
                completed = True
                break
        else:
            truncated += 1
            incomplete_reason = "decision_bound"

        selected_transitions, profile_evidence = select_profile_transitions(
            profile_transitions,
            completed=completed,
            incomplete_reason=incomplete_reason,
            complete_trajectories_only=config.complete_trajectories_only,
        )
        if completed:
            complete_profiles += 1
        else:
            incomplete_profiles += 1
            incomplete_profile_reasons[incomplete_reason] += 1
            if profile_evidence["excluded"]:
                excluded_incomplete_profiles += 1
                excluded_incomplete_transitions += len(profile_transitions)
            else:
                retained_incomplete_profiles += 1
        if selected_transitions:
            transitions.extend(selected_transitions)
            actions.update(profile_actions)
            encounters.update(profile_encounters)
            rewards.extend(profile_rewards)
            settlement_actions += profile_settlement_actions
            settlement_tasks.update(profile_settlement_tasks)
            settlement_transitions += profile_settlement_transitions
            encounter_assignments.update(profile_encounter_assignments)

    return transitions, {
        "accepted_transition_count": len(transitions),
        "transition_battle_index_counts": dict(
            sorted(Counter(row.battle_index for row in transitions).items())
        ),
        "action_family_counts": dict(sorted(actions.items())),
        "decision_bound_seed_count": truncated,
        "encounter_state_counts": dict(sorted(encounters.items())),
        "outcome_counts": dict(sorted(outcomes.items())),
        "reward": _reward_summary(rewards),
        "card_select_settlement": {
            "action_count": settlement_actions,
            "task_counts": dict(sorted(settlement_tasks.items())),
            "transition_count": settlement_transitions,
        },
        "initialization_failure_counts": dict(sorted(initialization_failures.items())),
        "profile_count_initialized": initialized_profiles,
        "profile_count_registered": len(config.profiles(config.train_seeds)),
        "trajectory_eligibility": {
            "complete_trajectories_only": config.complete_trajectories_only,
            "complete_profile_count": complete_profiles,
            "incomplete_profile_count": incomplete_profiles,
            "retained_incomplete_profile_count": retained_incomplete_profiles,
            "excluded_incomplete_profile_count": excluded_incomplete_profiles,
            "excluded_incomplete_transition_count": excluded_incomplete_transitions,
            "incomplete_profile_reason_counts": dict(
                sorted(incomplete_profile_reasons.items())
            ),
            "source_transition_identity_sha256": transition_identity_sha256(
                transitions
            ),
        },
        "progression_coverage": {
            "act_counts": dict(sorted(progression_acts.items())),
            "battle_index_counts": dict(sorted(progression_battle_indices.items())),
            "encounter_counts": dict(sorted(progression_encounters.items())),
        },
        "seed_count": len(config.train_seeds),
        "unsupported_reason_counts": dict(sorted(unsupported.items())),
        "encounter_identity": {
            "bucket_count": config.encounter_identity_buckets,
            "encoding": (
                config.encounter_identity_encoding
                if config.encounter_identity_buckets
                else None
            ),
            "hash_algorithm": (
                ENCOUNTER_HASH_ALGORITHM
                if config.encounter_identity_buckets
                and config.encounter_identity_encoding == ENCOUNTER_HASH_ALGORITHM
                else None
            ),
            "assignments": dict(sorted(encounter_assignments.items())),
            "occupied_bucket_count": len(set(encounter_assignments.values())),
            "vocabulary_sha256": (
                ENCOUNTER_ENUM_V1_SHA256
                if config.encounter_identity_encoding == ENCOUNTER_ENUM_ENCODING
                else None
            ),
        },
    }


def prepare_replay_transitions(
    transitions: Sequence[ReplayTransition],
    *,
    battle_indices: Sequence[int],
    stratify: bool,
    seed: int,
) -> tuple[list[ReplayTransition], dict[str, Any]]:
    if seed < 0:
        raise ValueError("replay balance seed must be non-negative")
    indices = tuple(sorted(int(value) for value in battle_indices))
    groups = {value: [] for value in indices}
    for transition in transitions:
        if transition.battle_index not in groups:
            raise ValueError(
                f"transition has unconfigured battle-index stratum: "
                f"{transition.battle_index}"
            )
        groups[transition.battle_index].append(transition)
    source_counts = {str(index): len(groups[index]) for index in indices}

    if not stratify:
        return list(transitions), {
            "mode": "none",
            "seed": seed,
            "source_counts": source_counts,
            "prepared_counts": dict(source_counts),
            "duplicate_counts": {str(index): 0 for index in indices},
            "target_count_per_stratum": None,
            "source_transition_count": len(transitions),
            "prepared_transition_count": len(transitions),
        }

    missing = next((index for index in indices if not groups[index]), None)
    if missing is not None:
        raise ValueError(f"missing battle-index stratum: {missing}")
    target_count = max(len(rows) for rows in groups.values())
    prepared_groups: dict[int, list[ReplayTransition]] = {}
    for index in indices:
        source = groups[index]
        prepared = list(source)
        rng = random.Random(seed ^ (index << 32))
        while len(prepared) < target_count:
            repeated = list(source)
            rng.shuffle(repeated)
            prepared.extend(repeated[: target_count - len(prepared)])
        prepared_groups[index] = prepared
    prepared_rows = [
        prepared_groups[index][position]
        for position in range(target_count)
        for index in indices
    ]
    prepared_counts = {
        str(index): len(prepared_groups[index]) for index in indices
    }
    return prepared_rows, {
        "mode": "battle_index_oversample",
        "seed": seed,
        "source_counts": source_counts,
        "prepared_counts": prepared_counts,
        "duplicate_counts": {
            str(index): len(prepared_groups[index]) - len(groups[index])
            for index in indices
        },
        "target_count_per_stratum": target_count,
        "source_transition_count": len(transitions),
        "prepared_transition_count": len(prepared_rows),
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


def run_optimizer(trainer: DQNTrainerV2, steps: int) -> dict[str, list[float]]:
    if len(trainer.replay_buffer) < trainer.learning_starts:
        raise RuntimeError("replay does not satisfy learning_starts")
    trainer.target_update_freq = trainer.total_steps + 1
    losses: dict[str, list[float]] = {
        "total": [],
        "td": [],
        "parent_policy_anchor": [],
        "parent_end_turn_margin_guard": [],
        "parent_end_turn_margin_guard_eligible_count": [],
        "parent_end_turn_margin_guard_ranking_violation_count": [],
    }
    for _ in range(steps):
        loss = trainer.train_step()
        if loss is None or not math.isfinite(loss):
            raise RuntimeError(f"optimizer returned invalid loss: {loss}")
        values = {
            "total": float(loss),
            "td": float(trainer.last_td_loss),
            "parent_policy_anchor": float(trainer.last_parent_policy_anchor_loss),
            "parent_end_turn_margin_guard": float(
                trainer.last_parent_end_turn_margin_guard_loss
            ),
            "parent_end_turn_margin_guard_eligible_count": float(
                trainer.last_parent_end_turn_margin_guard_eligible_count
            ),
            "parent_end_turn_margin_guard_ranking_violation_count": float(
                trainer.last_parent_end_turn_margin_guard_ranking_violation_count
            ),
        }
        if not all(math.isfinite(value) for value in values.values()):
            raise RuntimeError(f"optimizer returned invalid objective metrics: {values}")
        for name, value in values.items():
            losses[name].append(value)
    return losses


def summarize_losses(values: Sequence[float]) -> dict[str, float]:
    if not values:
        raise ValueError("cannot summarize empty loss values")
    return {
        "first": float(values[0]),
        "last": float(values[-1]),
        "mean": float(np.mean(values)),
        "minimum": float(np.min(values)),
        "maximum": float(np.max(values)),
    }


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
                before = environment.snapshot()
                mapped = augment_mapped_state(
                    mapped,
                    before,
                    bucket_count=config.encounter_identity_buckets,
                    encoding=config.encounter_identity_encoding,
                )
                legal = environment.legal_actions()
                selected = _policy_action(
                    trainer,
                    mapped,
                    legal,
                    actions_since_end_turn=actions_since_end_turn,
                    max_actions_per_turn=config.max_actions_per_turn,
                )
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
        if report["initialization"].get("checkpoint_sha256"):
            source_binding["initial_checkpoint_sha256"] = report["initialization"][
                "checkpoint_sha256"
            ]
            source_binding["initial_checkpoint_parameter_sha256"] = report[
                "initialization"
            ].get(
                "source_parameter_sha256",
                report["initialization"]["parameter_sha256"],
            )
            source_binding["initial_parameter_sha256"] = report["initialization"][
                "parameter_sha256"
            ]
        if report["initialization"].get("source_parameter_sha256"):
            source_binding["source_checkpoint_parameter_sha256"] = report[
                "initialization"
            ]["source_parameter_sha256"]
        if report["initialization"].get("encounter_identity_migration"):
            source_binding["encounter_identity_migration"] = report[
                "initialization"
            ]["encounter_identity_migration"]
        source_binding["parent_policy_anchor_weight"] = report["training"][
            "parent_policy_anchor_weight"
        ]
        source_binding["parent_end_turn_margin_guard_weight"] = report["training"].get(
            "parent_end_turn_margin_guard_weight", 0.0
        )
        source_binding["parent_end_turn_margin_guard_cap"] = report["training"].get(
            "parent_end_turn_margin_guard_cap", 0.1
        )
        if report["training"].get("replay_target"):
            source_binding["replay_target"] = report["training"]["replay_target"]
        if report["initialization"].get("parent_policy_anchor_parameter_sha256"):
            source_binding["parent_policy_anchor_parameter_sha256"] = report[
                "initialization"
            ]["parent_policy_anchor_parameter_sha256"]
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
        "schema_version": "combat-lightspeed-training-smoke-manifest-v10",
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
        parent_policy_anchor_weight=config.parent_policy_anchor_weight,
        parent_end_turn_margin_guard_weight=(
            config.parent_end_turn_margin_guard_weight
        ),
        parent_end_turn_margin_guard_cap=config.parent_end_turn_margin_guard_cap,
        continuous_dim=CONTINUOUS_DIM + config.encounter_identity_buckets,
    )
    initial, initialization = initialize_trainer(
        trainer,
        initial_checkpoint,
        encounter_identity_buckets=config.encounter_identity_buckets,
        encounter_identity_encoding=config.encounter_identity_encoding,
    )
    initial_sha256 = parameter_sha256(initial)
    if (
        config.replay_target_mode == FROZEN_PARENT_N_STEP_TARGET
        and initial_checkpoint is None
    ):
        raise ValueError("frozen-parent n-step targets require a warm-start checkpoint")
    transitions, corpus_metrics = collect_transitions(
        native_module,
        id_mapper=id_mapper,
        config=config,
    )
    bootstrap_values = None
    bootstrap_parameter_sha256 = None
    if config.replay_target_mode == FROZEN_PARENT_N_STEP_TARGET:
        bootstrap_values, bootstrap_parameter_sha256 = frozen_parent_bootstrap_values(
            trainer.target_network,
            transitions,
        )
        if bootstrap_parameter_sha256 != initial_sha256:
            raise RuntimeError("frozen parent parameter identity changed before target preparation")
    target_transitions, replay_target = prepare_replay_targets(
        transitions,
        mode=config.replay_target_mode,
        discount=config.replay_return_discount,
        horizon=config.replay_return_horizon,
        bootstrap_values=bootstrap_values,
        bootstrap_parameter_sha256=bootstrap_parameter_sha256,
    )
    prepared_transitions, replay_preparation = prepare_replay_transitions(
        target_transitions,
        battle_indices=config.battle_indices,
        stratify=config.balance_replay_by_battle_index,
        seed=config.replay_balance_seed,
    )
    accepted = insert_transitions(trainer, prepared_transitions)
    if accepted != len(prepared_transitions):
        raise RuntimeError(
            f"replay rejected transitions: {accepted}/{len(prepared_transitions)}"
        )
    objective_losses = run_optimizer(trainer, config.optimizer_steps)
    losses = objective_losses["total"]
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
    if config.parent_policy_anchor_weight > 0.0 and not any(
        value > 0.0 for value in objective_losses["parent_policy_anchor"]
    ):
        blockers.append("parent_policy_anchor_loss_missing")
    if config.parent_end_turn_margin_guard_weight > 0.0 and not any(
        value > 0.0
        for value in objective_losses[
            "parent_end_turn_margin_guard_eligible_count"
        ]
    ):
        blockers.append("parent_end_turn_margin_guard_eligibility_missing")
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
        "observation_extension": {
            "encounter_identity": {
                "bucket_count": config.encounter_identity_buckets,
                "continuous_dim": CONTINUOUS_DIM + config.encounter_identity_buckets,
                "encoding": (
                    config.encounter_identity_encoding
                    if config.encounter_identity_buckets
                    else None
                ),
                "hash_algorithm": (
                    ENCOUNTER_HASH_ALGORITHM
                    if config.encounter_identity_buckets
                    and config.encounter_identity_encoding == ENCOUNTER_HASH_ALGORITHM
                    else None
                ),
                "vocabulary_sha256": (
                    ENCOUNTER_ENUM_V1_SHA256
                    if config.encounter_identity_encoding == ENCOUNTER_ENUM_ENCODING
                    else None
                ),
            }
        },
        "corpus": corpus_metrics,
        "training": {
            "initial_parameter_sha256": initial_sha256,
            "candidate_parameter_sha256": candidate_sha256,
            "parameter_delta": delta,
            "replay_transition_count": accepted,
            "source_replay_transition_count": len(transitions),
            "target_replay_transition_count": len(target_transitions),
            "replay_target": replay_target,
            "replay_preparation": replay_preparation,
            "optimizer_update_count": len(losses),
            "parent_policy_anchor_weight": config.parent_policy_anchor_weight,
            "parent_end_turn_margin_guard_weight": (
                config.parent_end_turn_margin_guard_weight
            ),
            "parent_end_turn_margin_guard_cap": (
                config.parent_end_turn_margin_guard_cap
            ),
            "loss_first": losses[0],
            "loss_last": losses[-1],
            "loss_mean": float(np.mean(losses)),
            "loss_minimum": float(np.min(losses)),
            "loss_maximum": float(np.max(losses)),
            "objective_losses": {
                name: summarize_losses(values)
                for name, values in objective_losses.items()
            },
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
    parser.add_argument("--parent-policy-anchor-weight", default=0.0, type=float)
    parser.add_argument(
        "--parent-end-turn-margin-guard-weight", default=0.0, type=float
    )
    parser.add_argument(
        "--parent-end-turn-margin-guard-cap", default=0.1, type=float
    )
    parser.add_argument("--balance-replay-by-battle-index", action="store_true")
    parser.add_argument("--replay-balance-seed", default=2026081903, type=int)
    parser.add_argument("--encounter-identity-buckets", default=0, type=int)
    parser.add_argument(
        "--encounter-identity-encoding",
        default=ENCOUNTER_HASH_ALGORITHM,
        choices=(ENCOUNTER_HASH_ALGORITHM, ENCOUNTER_ENUM_ENCODING),
    )
    parser.add_argument(
        "--replay-target-mode",
        default=ONE_STEP_TD_TARGET,
        choices=(
            ONE_STEP_TD_TARGET,
            DISCOUNTED_EPISODE_RETURN_TARGET,
            FROZEN_PARENT_N_STEP_TARGET,
        ),
    )
    parser.add_argument("--replay-return-discount", default=0.99, type=float)
    parser.add_argument("--replay-return-horizon", default=3, type=int)
    parser.add_argument("--complete-trajectories-only", action="store_true")
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
        parent_policy_anchor_weight=args.parent_policy_anchor_weight,
        parent_end_turn_margin_guard_weight=(
            args.parent_end_turn_margin_guard_weight
        ),
        parent_end_turn_margin_guard_cap=args.parent_end_turn_margin_guard_cap,
        balance_replay_by_battle_index=args.balance_replay_by_battle_index,
        replay_balance_seed=args.replay_balance_seed,
        encounter_identity_buckets=args.encounter_identity_buckets,
        encounter_identity_encoding=args.encounter_identity_encoding,
        replay_target_mode=args.replay_target_mode,
        replay_return_discount=args.replay_return_discount,
        replay_return_horizon=args.replay_return_horizon,
        complete_trajectories_only=args.complete_trajectories_only,
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
