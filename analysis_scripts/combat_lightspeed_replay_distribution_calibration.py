"""Compare real combat replay with a frozen-parent LightSTS replay corpus."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
import math
from pathlib import Path
import shutil
import sys
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import torch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from analysis_scripts.combat_lightspeed_bridge import (  # noqa: E402
    ACTION_DIM,
    CARD_SLOTS,
    CONTINUOUS_DIM,
    POTION_SLOTS,
    RELIC_SLOTS,
    canonical_json_bytes,
    collect_provenance,
    load_native_module,
    sha256_bytes,
    sha256_file,
)
from analysis_scripts.combat_lightspeed_training_smoke import (  # noqa: E402
    FROZEN_PARENT_GUARDED_EPSILON_BEHAVIOR,
    FROZEN_PARENT_GREEDY_ANCHOR_LABEL,
    FROZEN_PARENT_RAW_GREEDY_BOOTSTRAP,
    GREEDY_NATIVE_REWARD_DEPLOYMENT_GUARD_PROXY,
    ONE_STEP_TD_TARGET,
    ReplayTransition,
    SmokeConfig,
    collect_transitions,
    load_initial_checkpoint,
    parameter_sha256,
)
from spirecomm.ai.rl.checkpoint_io import load_torch_checkpoint  # noqa: E402
from spirecomm.ai.rl.v2 import action_space  # noqa: E402
from spirecomm.ai.rl.v2.id_mapping import build_id_mapper  # noqa: E402
from spirecomm.ai.rl.v2.network import create_dqn_v2  # noqa: E402
from spirecomm.ai.rl.v2.replay_buffer import ReplayBufferV2  # noqa: E402


REPORT_SCHEMA_VERSION = "combat-lightspeed-replay-distribution-calibration-v1"
REPORT_AUTHORITY = {
    "evaluation": False,
    "formal_rl": False,
    "gameplay": False,
    "mechanics_equivalence": False,
    "ope": False,
    "policy_quality": False,
    "promotion": False,
    "qualification": False,
    "training": False,
}
FLOOR_STRATA = (
    ("floor_00_05", 0, 5),
    ("floor_06_10", 6, 10),
    ("floor_11_17", 11, 17),
    ("floor_18_22", 18, 22),
    ("floor_23_27", 23, 27),
    ("floor_28_34", 28, 34),
    ("floor_35_39", 35, 39),
    ("floor_40_44", 40, 44),
    ("floor_45_50", 45, 50),
)
STRATUM_ORDER = {name: index for index, (name, _start, _end) in enumerate(FLOOR_STRATA)}
MONSTER_ALIVE_INDICES = tuple(33 + (slot * 30) for slot in range(5))
SEMANTIC_CONTINUOUS_INDICES = {
    "player_hp_ratio": 0,
    "energy_ratio": 1,
    "block_ratio": 2,
    "floor_ratio": 3,
}


@dataclass(frozen=True)
class RealReplayBinding:
    label: str
    path: Path
    sha256: str


@dataclass(frozen=True)
class TransitionBatch:
    continuous: np.ndarray
    card_ids: np.ndarray
    potion_ids: np.ndarray
    relic_ids: np.ndarray
    actions: np.ndarray
    rewards: np.ndarray
    dones: np.ndarray
    action_masks: np.ndarray

    @property
    def transition_count(self) -> int:
        return int(self.actions.shape[0])

    def validate(self, *, label: str) -> None:
        count = self.transition_count
        expected = {
            "continuous": (count, CONTINUOUS_DIM),
            "card_ids": (count, CARD_SLOTS),
            "potion_ids": (count, POTION_SLOTS),
            "relic_ids": (count, RELIC_SLOTS),
            "actions": (count,),
            "rewards": (count,),
            "dones": (count,),
            "action_masks": (count, ACTION_DIM),
        }
        for name, shape in expected.items():
            actual = np.asarray(getattr(self, name))
            if actual.shape != shape:
                raise ValueError(
                    f"{label} transition {name} shape mismatch: {actual.shape} != {shape}"
                )
        if count <= 0:
            raise ValueError(f"{label} transition batch must be non-empty")
        if not np.isfinite(self.continuous).all():
            raise ValueError(f"{label} continuous replay contains non-finite values")
        if not np.isfinite(self.rewards).all():
            raise ValueError(f"{label} reward replay contains non-finite values")
        if np.any(self.actions < 0) or np.any(self.actions >= ACTION_DIM):
            raise ValueError(f"{label} replay action is outside the RL-v2 action range")
        selected_is_legal = self.action_masks[
            np.arange(count), self.actions.astype(np.int64, copy=False)
        ]
        if not bool(np.asarray(selected_is_legal, dtype=bool).all()):
            raise ValueError(f"{label} replay action is absent from its action mask")

    @classmethod
    def concatenate(
        cls,
        batches: Sequence["TransitionBatch"],
        *,
        label: str,
    ) -> "TransitionBatch":
        values = list(batches)
        if not values:
            raise ValueError(f"{label} requires at least one transition batch")
        result = cls(
            **{
                name: np.concatenate(
                    [np.asarray(getattr(batch, name)) for batch in values], axis=0
                )
                for name in cls.__dataclass_fields__
            }
        )
        result.validate(label=label)
        return result


@dataclass(frozen=True)
class FrozenBehaviorPolicy:
    online_network: torch.nn.Module


def _normalized_sha256(value: str, *, label: str) -> str:
    text = str(value).lower()
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise ValueError(f"{label} SHA-256 must be 64 lowercase hexadecimal characters")
    return text


def verify_file_identity(
    path: Path,
    expected_sha256: str,
    *,
    label: str,
) -> dict[str, Any]:
    resolved = Path(path).resolve()
    if not resolved.is_file():
        raise ValueError(f"{label} is missing: {resolved}")
    expected = _normalized_sha256(expected_sha256, label=label)
    actual = sha256_file(resolved)
    if actual != expected:
        raise ValueError(f"{label} hash mismatch: {actual} != {expected}")
    return {
        "path": resolved.as_posix(),
        "sha256": actual,
        "size_bytes": resolved.stat().st_size,
    }


def validate_provenance_identity(
    provenance: Mapping[str, Any],
    *,
    adapter_source_sha256: str,
    simulator_commit: str,
    simulator_source_sha256: str,
) -> dict[str, str]:
    expected = {
        "adapter_source_sha256": _normalized_sha256(
            adapter_source_sha256, label="adapter source"
        ),
        "simulator_commit": str(simulator_commit).lower(),
        "simulator_source_sha256": _normalized_sha256(
            simulator_source_sha256, label="simulator source"
        ),
    }
    if len(expected["simulator_commit"]) != 40 or any(
        character not in "0123456789abcdef"
        for character in expected["simulator_commit"]
    ):
        raise ValueError("simulator commit must be 40 lowercase hexadecimal characters")
    for key, expected_value in expected.items():
        actual = str(provenance.get(key, "")).lower()
        if actual != expected_value:
            raise ValueError(
                f"{key.replace('_', ' ')} mismatch: {actual} != {expected_value}"
            )
    return expected


def _batch_from_replay_state(state: Mapping[str, Any], *, label: str) -> TransitionBatch:
    replay_schema_version = int(state.get("schema_version", -1))
    if replay_schema_version not in {1, 2}:
        raise ValueError(f"{label} replay must use schema-v1 or schema-v2")
    if bool(state.get("truncated")):
        raise ValueError(f"{label} replay must be untruncated")
    count = int(state.get("transition_count", -1))
    source_count = int(state.get("source_transition_count", -1))
    if count <= 0 or source_count != count:
        raise ValueError(f"{label} replay must be complete and non-empty")
    expected_dimensions = {
        "continuous_dim": CONTINUOUS_DIM,
        "action_dim": ACTION_DIM,
        "card_slots": CARD_SLOTS,
        "potion_slots": POTION_SLOTS,
        "relic_slots": RELIC_SLOTS,
    }
    for key, expected in expected_dimensions.items():
        if int(state.get(key, -1)) != expected:
            raise ValueError(
                f"{label} replay {key} mismatch: {state.get(key)} != {expected}"
            )
    validator = ReplayBufferV2(
        buffer_size=max(int(state.get("buffer_size", count)), count),
        continuous_dim=CONTINUOUS_DIM,
        action_dim=ACTION_DIM,
        card_slots=CARD_SLOTS,
        potion_slots=POTION_SLOTS,
        relic_slots=RELIC_SLOTS,
    )
    try:
        validator.load_state_dict(dict(state))
    except ValueError as exc:
        raise ValueError(f"{label} replay validation failed: {exc}") from exc

    def numpy(name: str) -> np.ndarray:
        return state[name].detach().cpu().numpy().copy()

    batch = TransitionBatch(
        continuous=numpy("continuous").astype(np.float32, copy=False),
        card_ids=numpy("card_ids").astype(np.int64, copy=False),
        potion_ids=numpy("potion_ids").astype(np.int64, copy=False),
        relic_ids=numpy("relic_ids").astype(np.int64, copy=False),
        actions=numpy("actions").astype(np.int64, copy=False),
        rewards=numpy("rewards").astype(np.float64, copy=False),
        dones=numpy("dones").astype(bool, copy=False),
        action_masks=numpy("action_masks").astype(bool, copy=False),
    )
    batch.validate(label=label)
    return batch


def load_real_replay_bindings(
    bindings: Sequence[RealReplayBinding],
) -> tuple[TransitionBatch, list[dict[str, Any]]]:
    values = list(bindings)
    if not values:
        raise ValueError("at least one real replay checkpoint is required")
    labels = [str(binding.label) for binding in values]
    if any(not label for label in labels) or len(set(labels)) != len(labels):
        raise ValueError("real replay labels must be non-empty and unique")
    batches: list[TransitionBatch] = []
    evidence: list[dict[str, Any]] = []
    resolved_paths: set[Path] = set()
    for binding in values:
        label = str(binding.label)
        path = Path(binding.path).resolve()
        if path in resolved_paths:
            raise ValueError(f"real replay checkpoint path is duplicated: {path}")
        resolved_paths.add(path)
        if not path.is_file():
            raise ValueError(f"real replay checkpoint is missing: {path}")
        expected_sha256 = _normalized_sha256(
            binding.sha256, label=f"real replay {label}"
        )
        actual_sha256 = sha256_file(path)
        if actual_sha256 != expected_sha256:
            raise ValueError(
                f"real replay checkpoint hash mismatch for {label}: "
                f"{actual_sha256} != {expected_sha256}"
            )
        checkpoint = load_torch_checkpoint(str(path), map_location="cpu")
        if not isinstance(checkpoint, Mapping):
            raise ValueError(f"real replay checkpoint root is not a mapping: {label}")
        replay_state = checkpoint.get("replay_buffer_state_dict")
        if not isinstance(replay_state, Mapping):
            raise ValueError(f"real replay checkpoint omits replay state: {label}")
        batch = _batch_from_replay_state(replay_state, label=label)
        batches.append(batch)
        evidence.append(
            {
                "checkpoint_kind": checkpoint.get("checkpoint_kind"),
                "checkpoint_schema_version": checkpoint.get(
                    "checkpoint_schema_version"
                ),
                "label": label,
                "path": path.as_posix(),
                "replay_schema_version": int(replay_state["schema_version"]),
                "replay_transition_count": batch.transition_count,
                "sha256": actual_sha256,
                "size_bytes": path.stat().st_size,
            }
        )
    return TransitionBatch.concatenate(batches, label="real"), evidence


def floor_stratum(encoded_floor: float) -> str:
    value = float(encoded_floor)
    if not math.isfinite(value) or value < 0.0 or value > 1.0:
        raise ValueError(f"encoded floor is outside [0, 1]: {encoded_floor}")
    scaled = value * 50.0
    floor = int(round(scaled))
    if abs(scaled - floor) > 1e-4:
        raise ValueError(f"encoded floor is not an integer floor ratio: {encoded_floor}")
    for name, start, end in FLOOR_STRATA:
        if start <= floor <= end:
            return name
    raise ValueError(f"encoded floor has no canonical stratum: {encoded_floor}")


def combat_action_family(action: int) -> str:
    value = int(action)
    if not 0 <= value < action_space.ACTION_DIM:
        raise ValueError(f"action is outside RL-v2 range: {value}")
    if action_space.PLAY_CARD_OFFSET <= value < action_space.USE_POTION_OFFSET:
        return "play_card"
    if action_space.USE_POTION_OFFSET <= value < action_space.END_TURN_ACTION:
        return "use_potion"
    if value == action_space.END_TURN_ACTION:
        return "end_turn"
    if action_space.REWARD_OFFSET <= value < action_space.MAP_OFFSET:
        return "reward_choice"
    if action_space.MAP_OFFSET <= value < action_space.EVENT_OFFSET:
        return "map_choice"
    if action_space.EVENT_OFFSET <= value < action_space.SHOP_OFFSET:
        return "event_choice"
    if action_space.SHOP_OFFSET <= value < action_space.REST_OFFSET:
        return "shop_choice"
    if action_space.REST_OFFSET <= value < action_space.SYSTEM_OFFSET:
        return "rest_choice"
    return "system"


def _numeric_summary(values: np.ndarray) -> dict[str, float | int]:
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 1 or array.size == 0 or not np.isfinite(array).all():
        raise ValueError("numeric summary requires a finite non-empty vector")
    return {
        "count": int(array.size),
        "maximum": float(np.max(array)),
        "mean": float(np.mean(array)),
        "minimum": float(np.min(array)),
        "standard_deviation": float(np.std(array, ddof=0)),
    }


def _id_support(values: np.ndarray) -> list[int]:
    array = np.asarray(values, dtype=np.int64)
    return sorted(int(value) for value in np.unique(array) if int(value) != 0)


def _summarize_indices(batch: TransitionBatch, indices: np.ndarray) -> dict[str, Any]:
    continuous = batch.continuous[indices]
    card_ids = batch.card_ids[indices]
    potion_ids = batch.potion_ids[indices]
    relic_ids = batch.relic_ids[indices]
    actions = batch.actions[indices]
    action_masks = batch.action_masks[indices]
    semantic = {
        name: _numeric_summary(continuous[:, index])
        for name, index in SEMANTIC_CONTINUOUS_INDICES.items()
    }
    semantic.update(
        {
            "alive_monster_count": _numeric_summary(
                np.sum(continuous[:, MONSTER_ALIVE_INDICES] > 0.5, axis=1)
            ),
            "hand_occupied_slots": _numeric_summary(np.sum(card_ids != 0, axis=1)),
            "potion_occupied_slots": _numeric_summary(
                np.sum(potion_ids != 0, axis=1)
            ),
            "relic_occupied_slots": _numeric_summary(
                np.sum(relic_ids != 0, axis=1)
            ),
        }
    )
    family_counts = Counter(combat_action_family(int(action)) for action in actions)
    return {
        "action_family_counts": dict(sorted(family_counts.items())),
        "action_index_support": sorted(int(value) for value in np.unique(actions)),
        "card_id_support": _id_support(card_ids),
        "legal_action_count": _numeric_summary(np.sum(action_masks, axis=1)),
        "potion_id_support": _id_support(potion_ids),
        "relic_id_support": _id_support(relic_ids),
        "reward": _numeric_summary(batch.rewards[indices]),
        "semantic": semantic,
        "terminal_rate": _numeric_summary(batch.dones[indices].astype(np.float64)),
        "transition_count": int(indices.size),
    }


def summarize_source(batch: TransitionBatch) -> dict[str, Any]:
    batch.validate(label="source")
    strata = np.asarray(
        [floor_stratum(value) for value in batch.continuous[:, 3]], dtype=object
    )
    result = {
        "aggregate": _summarize_indices(
            batch, np.arange(batch.transition_count, dtype=np.int64)
        ),
        "strata": {},
        "transition_count": batch.transition_count,
    }
    for name, _start, _end in FLOOR_STRATA:
        indices = np.flatnonzero(strata == name)
        if indices.size:
            result["strata"][name] = _summarize_indices(batch, indices)
    return result


def _numeric_fields(summary: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {
        **dict(summary["semantic"]),
        "legal_action_count": summary["legal_action_count"],
        "reward": summary["reward"],
        "terminal_rate": summary["terminal_rate"],
    }


def _compare_numeric(
    real: Mapping[str, Any], simulator: Mapping[str, Any]
) -> dict[str, Any]:
    real_mean = float(real["mean"])
    simulator_mean = float(simulator["mean"])
    delta = simulator_mean - real_mean
    pooled_std = math.sqrt(
        (float(real["standard_deviation"]) ** 2 + float(simulator["standard_deviation"]) ** 2)
        / 2.0
    )
    degenerate = pooled_std <= 1e-12
    standardized = (
        0.0 if degenerate and abs(delta) <= 1e-12 else None
    )
    if not degenerate:
        standardized = abs(delta) / pooled_std
    return {
        "absolute_standardized_mean_difference": standardized,
        "degenerate_variance": degenerate,
        "pooled_standard_deviation": pooled_std,
        "real_mean": real_mean,
        "simulator_mean": simulator_mean,
        "simulator_minus_real_mean": delta,
    }


def _distribution(counts: Mapping[str, Any]) -> dict[str, float]:
    total = sum(int(value) for value in counts.values())
    if total <= 0:
        return {}
    return {str(key): int(value) / total for key, value in sorted(counts.items())}


def _total_variation(left: Mapping[str, Any], right: Mapping[str, Any]) -> float:
    left_distribution = _distribution(left)
    right_distribution = _distribution(right)
    keys = set(left_distribution).union(right_distribution)
    return 0.5 * sum(
        abs(left_distribution.get(key, 0.0) - right_distribution.get(key, 0.0))
        for key in keys
    )


def _support_overlap(left: Iterable[int], right: Iterable[int]) -> dict[str, Any]:
    left_set = set(int(value) for value in left)
    right_set = set(int(value) for value in right)
    intersection = left_set.intersection(right_set)
    union = left_set.union(right_set)
    return {
        "intersection_count": len(intersection),
        "jaccard": 1.0 if not union else len(intersection) / len(union),
        "real_only": sorted(left_set - right_set),
        "real_support_count": len(left_set),
        "simulator_only": sorted(right_set - left_set),
        "simulator_support_count": len(right_set),
        "union_count": len(union),
    }


def compare_sources(
    real_summary: Mapping[str, Any],
    simulator_summary: Mapping[str, Any],
    *,
    minimum_stratum_count: int,
) -> dict[str, Any]:
    if minimum_stratum_count <= 0:
        raise ValueError("minimum stratum count must be positive")
    real_strata = real_summary["strata"]
    simulator_strata = simulator_summary["strata"]
    common = [
        name
        for name, _start, _end in FLOOR_STRATA
        if name in real_strata
        and name in simulator_strata
        and int(real_strata[name]["transition_count"]) >= minimum_stratum_count
        and int(simulator_strata[name]["transition_count"])
        >= minimum_stratum_count
    ]
    strata: dict[str, Any] = {}
    numeric_ranking: list[dict[str, Any]] = []
    categorical_ranking: list[dict[str, Any]] = []
    for name in common:
        real = real_strata[name]
        simulator = simulator_strata[name]
        numeric = {
            metric: _compare_numeric(real_value, _numeric_fields(simulator)[metric])
            for metric, real_value in _numeric_fields(real).items()
        }
        action_family_tv = _total_variation(
            real["action_family_counts"], simulator["action_family_counts"]
        )
        supports = {
            "action_index": _support_overlap(
                real["action_index_support"], simulator["action_index_support"]
            ),
            "card_id": _support_overlap(
                real["card_id_support"], simulator["card_id_support"]
            ),
            "potion_id": _support_overlap(
                real["potion_id_support"], simulator["potion_id_support"]
            ),
            "relic_id": _support_overlap(
                real["relic_id_support"], simulator["relic_id_support"]
            ),
        }
        strata[name] = {
            "action_family_total_variation": action_family_tv,
            "numeric": numeric,
            "real_transition_count": int(real["transition_count"]),
            "simulator_transition_count": int(simulator["transition_count"]),
            "support": supports,
        }
        for metric, result in numeric.items():
            score = result["absolute_standardized_mean_difference"]
            if score is not None:
                numeric_ranking.append(
                    {"metric": metric, "score": float(score), "stratum": name}
                )
        categorical_ranking.append(
            {
                "metric": "action_family_total_variation",
                "score": action_family_tv,
                "stratum": name,
            }
        )
        for support_name, result in supports.items():
            categorical_ranking.append(
                {
                    "metric": f"{support_name}_support_nonoverlap",
                    "score": 1.0 - float(result["jaccard"]),
                    "stratum": name,
                }
            )

    ranking_key = lambda row: (  # noqa: E731
        -float(row["score"]),
        STRATUM_ORDER[str(row["stratum"])],
        str(row["metric"]),
    )
    return {
        "categorical_mismatch_ranking": sorted(categorical_ranking, key=ranking_key),
        "common_strata": common,
        "minimum_stratum_count": minimum_stratum_count,
        "numeric_mismatch_ranking": sorted(numeric_ranking, key=ranking_key),
        "real_only_or_under_minimum_strata": [
            name
            for name, _start, _end in FLOOR_STRATA
            if name in real_strata and name not in common
        ],
        "simulator_only_or_under_minimum_strata": [
            name
            for name, _start, _end in FLOOR_STRATA
            if name in simulator_strata and name not in common
        ],
        "strata": strata,
        "technical_comparison_ready": len(common) >= 2,
    }


def build_collection_config(
    *,
    seeds: Sequence[int],
    battle_indices: Sequence[int],
    behavior_seed: int,
    network_seed: int,
    max_decisions_per_seed: int,
    max_actions_per_turn: int,
    ascension: int = 0,
) -> SmokeConfig:
    train_seeds = tuple(int(seed) for seed in seeds)
    dummy_evaluation_seed = max(train_seeds, default=-1) + 1
    config = SmokeConfig(
        train_seeds=train_seeds,
        evaluation_seeds=(dummy_evaluation_seed,),
        battle_indices=tuple(int(value) for value in battle_indices),
        ascension=ascension,
        max_decisions_per_seed=max_decisions_per_seed,
        max_actions_per_turn=max_actions_per_turn,
        behavior_seed=behavior_seed,
        behavior_policy=FROZEN_PARENT_GUARDED_EPSILON_BEHAVIOR,
        behavior_epsilon=0.0,
        network_seed=network_seed,
        batch_size=128,
        optimizer_steps=1,
        parent_policy_anchor_weight=0.0,
        parent_anchor_label_mode=FROZEN_PARENT_GREEDY_ANCHOR_LABEL,
        replay_target_mode=ONE_STEP_TD_TARGET,
        frozen_parent_bootstrap_policy=FROZEN_PARENT_RAW_GREEDY_BOOTSTRAP,
        complete_trajectories_only=False,
        deployment_guard_proxy=GREEDY_NATIVE_REWARD_DEPLOYMENT_GUARD_PROXY,
    )
    config.validate()
    return config


def _batch_from_simulator_transitions(
    transitions: Sequence[ReplayTransition],
) -> TransitionBatch:
    rows = list(transitions)
    if not rows:
        raise ValueError("simulator collection produced no transitions")
    batch = TransitionBatch(
        continuous=np.stack([row.continuous for row in rows]).astype(np.float32),
        card_ids=np.stack([row.card_ids for row in rows]).astype(np.int64),
        potion_ids=np.stack([row.potion_ids for row in rows]).astype(np.int64),
        relic_ids=np.stack([row.relic_ids for row in rows]).astype(np.int64),
        actions=np.asarray([row.action for row in rows], dtype=np.int64),
        rewards=np.asarray([row.reward for row in rows], dtype=np.float64),
        dones=np.asarray([row.done for row in rows], dtype=bool),
        action_masks=np.stack([row.action_mask for row in rows]).astype(bool),
    )
    batch.validate(label="simulator")
    return batch


def collect_simulator_replay(
    native_module: object,
    *,
    items_json: Path,
    parent_checkpoint: Path,
    parent_checkpoint_sha256: str,
    config: SmokeConfig,
) -> tuple[TransitionBatch, dict[str, Any], dict[str, Any]]:
    id_mapper = build_id_mapper(items_json)
    initial_checkpoint = load_initial_checkpoint(
        parent_checkpoint,
        expected_sha256=parent_checkpoint_sha256,
    )
    parent_state = initial_checkpoint.get("state_dict")
    if not isinstance(parent_state, Mapping):
        raise ValueError("simulator calibration parent state is missing")
    torch.manual_seed(config.network_seed)
    network = create_dqn_v2(
        network_type="dueling",
        continuous_dim=CONTINUOUS_DIM,
        action_dim=ACTION_DIM,
        card_vocab=id_mapper.card_vocab_size,
        potion_vocab=id_mapper.potion_vocab_size,
        relic_vocab=id_mapper.relic_vocab_size,
        device="cpu",
        card_slots=CARD_SLOTS,
        potion_slots=POTION_SLOTS,
        relic_slots=RELIC_SLOTS,
    )
    try:
        network.load_state_dict(parent_state, strict=True)
    except (KeyError, RuntimeError, TypeError, ValueError) as exc:
        raise ValueError(f"simulator calibration parent is incompatible: {exc}") from exc
    network.eval()
    for parameter in network.parameters():
        parameter.requires_grad_(False)
    behavior_policy = FrozenBehaviorPolicy(network)
    parent_sha256 = parameter_sha256(network.state_dict())
    if parent_sha256 != initial_checkpoint.get("parameter_sha256"):
        raise ValueError("simulator calibration parent parameter hash changed during load")
    transitions, collection = collect_transitions(
        native_module,
        id_mapper=id_mapper,
        config=config,
        behavior_trainer=behavior_policy,
        expected_behavior_parent_sha256=parent_sha256,
    )
    current_parent_sha256 = parameter_sha256(network.state_dict())
    if current_parent_sha256 != parent_sha256:
        raise RuntimeError("simulator calibration parent changed during collection")
    collection = {
        **collection,
        "optimizer_constructed": False,
        "optimizer_step": 0,
        "parent_parameter_sha256": parent_sha256,
    }
    initialization = {
        key: value for key, value in initial_checkpoint.items() if key != "state_dict"
    }
    return _batch_from_simulator_transitions(transitions), collection, initialization


def build_report(
    *,
    real_summary: Mapping[str, Any],
    simulator_summary: Mapping[str, Any],
    comparison: Mapping[str, Any],
    provenance: Mapping[str, Any],
    config: Mapping[str, Any],
    real_bindings: Sequence[Mapping[str, Any]],
    simulator_collection: Mapping[str, Any],
    optimizer_step: int,
    initialization: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    blockers: list[str] = []
    if optimizer_step != 0:
        blockers.append("optimizer_step_nonzero")
    if not bool(comparison.get("technical_comparison_ready")):
        blockers.append("insufficient_common_strata")
    if int(real_summary.get("transition_count", 0)) <= 0:
        blockers.append("real_replay_empty")
    if int(simulator_summary.get("transition_count", 0)) <= 0:
        blockers.append("simulator_replay_empty")
    report = {
        "authority": dict(REPORT_AUTHORITY),
        "blockers": blockers,
        "comparison": dict(comparison),
        "config": dict(config),
        "limitations": [
            "The real and simulator transitions are not matched by seed, encounter, or state.",
            "Rows are serially correlated and descriptive counts are not independent samples.",
            "Distribution similarity does not establish mechanics equivalence or policy quality.",
        ],
        "operations": {
            "communication_mod": False,
            "gameplay": False,
            "model_fitting": False,
            "native_loading": True,
            "optimizer_updates": int(optimizer_step),
            "real_checkpoint_loading": True,
            "simulator_collection": True,
            "training": False,
        },
        "provenance": dict(provenance),
        "real": {
            "bindings": [dict(binding) for binding in real_bindings],
            "summary": dict(real_summary),
        },
        "schema_version": REPORT_SCHEMA_VERSION,
        "simulator": {
            "collection": dict(simulator_collection),
            "initialization": dict(initialization or {}),
            "summary": dict(simulator_summary),
        },
        "verdict": (
            "replay_distribution_calibration_ready"
            if not blockers
            else "replay_distribution_calibration_incomplete"
        ),
    }
    return report


def canonical_report_bytes(report: Mapping[str, Any]) -> bytes:
    return canonical_json_bytes(dict(report))


def _summary_markdown(report: Mapping[str, Any]) -> bytes:
    comparison = report["comparison"]
    numeric = list(comparison.get("numeric_mismatch_ranking") or [])[:8]
    categorical = list(comparison.get("categorical_mismatch_ranking") or [])[:8]
    lines = [
        "# Combat LightSTS Replay Distribution Calibration",
        "",
        f"- Verdict: `{report['verdict']}`",
        f"- Real transitions: `{report['real']['summary']['transition_count']}`",
        f"- Simulator transitions: `{report['simulator']['summary']['transition_count']}`",
        f"- Common strata: `{comparison.get('common_strata', [])}`",
        f"- Optimizer updates: `{report['operations']['optimizer_updates']}`",
        f"- Blockers: `{report['blockers'] or 'none'}`",
        "",
        "## Largest numeric mismatches",
        "",
    ]
    lines.extend(
        f"- `{row['stratum']}` `{row['metric']}`: `{row['score']:.6f}`"
        for row in numeric
    )
    lines.extend(["", "## Largest categorical mismatches", ""])
    lines.extend(
        f"- `{row['stratum']}` `{row['metric']}`: `{row['score']:.6f}`"
        for row in categorical
    )
    lines.extend(
        [
            "",
            "This is an unmatched descriptive comparison. It grants no gameplay,",
            "training, evaluation, mechanics-equivalence, policy-quality, qualification,",
            "or promotion authority.",
        ]
    )
    return ("\n".join(lines) + "\n").encode("utf-8")


def publish_report(
    output_dir: Path,
    report: Mapping[str, Any],
    *,
    max_report_bytes: int,
) -> None:
    if max_report_bytes <= 0:
        raise ValueError("max report bytes must be positive")
    output = output_dir.resolve()
    staging = output.parent / f".{output.name}.staging"
    if output.exists() or staging.exists():
        raise FileExistsError(f"calibration output or staging already exists: {output}")
    report_bytes = canonical_report_bytes(report) + b"\n"
    if len(report_bytes) > max_report_bytes:
        raise ValueError(
            f"calibration report exceeds size bound: {len(report_bytes)} > {max_report_bytes}"
        )
    summary_bytes = _summary_markdown(report)
    artifacts = {"report.json": report_bytes, "summary.md": summary_bytes}
    manifest = {
        "artifacts": {
            name: {"sha256": sha256_bytes(data), "size_bytes": len(data)}
            for name, data in sorted(artifacts.items())
        },
        "schema_version": "combat-lightspeed-replay-distribution-calibration-manifest-v1",
    }
    artifacts["manifest.json"] = canonical_json_bytes(manifest) + b"\n"
    staging.mkdir(parents=True, exist_ok=False)
    try:
        for name, data in artifacts.items():
            temporary = staging / f".{name}.tmp"
            temporary.write_bytes(data)
            temporary.replace(staging / name)
        staging.replace(output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def _parse_ints(value: str) -> tuple[int, ...]:
    text = value.strip()
    if ".." in text:
        start_text, end_text = text.split("..", 1)
        start, end = int(start_text), int(end_text)
        if end < start:
            raise argparse.ArgumentTypeError("range end must not precede start")
        return tuple(range(start, end + 1))
    return tuple(int(part.strip()) for part in text.split(",") if part.strip())


def _parse_labeled_values(values: Sequence[str], *, option: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in values:
        if "=" not in raw:
            raise ValueError(f"{option} must use LABEL=VALUE")
        label, value = raw.split("=", 1)
        if not label or not value or label in result:
            raise ValueError(f"{option} labels must be unique and non-empty")
        result[label] = value
    return result


def _real_bindings(args: argparse.Namespace) -> tuple[RealReplayBinding, ...]:
    paths = _parse_labeled_values(args.real_checkpoint, option="--real-checkpoint")
    hashes = _parse_labeled_values(
        args.real_checkpoint_sha256, option="--real-checkpoint-sha256"
    )
    if set(paths) != set(hashes):
        raise ValueError("real checkpoint path and SHA-256 labels must match")
    return tuple(
        RealReplayBinding(label, Path(paths[label]), hashes[label])
        for label in sorted(paths)
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--simulator-repo", required=True, type=Path)
    parser.add_argument("--module", required=True, type=Path)
    parser.add_argument("--expected-module-sha256", required=True)
    parser.add_argument("--dll-dir", action="append", default=[], type=Path)
    parser.add_argument("--items-json", required=True, type=Path)
    parser.add_argument("--expected-items-sha256", required=True)
    parser.add_argument("--expected-runner-sha256", required=True)
    parser.add_argument("--expected-adapter-source-sha256", required=True)
    parser.add_argument("--expected-simulator-commit", required=True)
    parser.add_argument("--expected-simulator-source-sha256", required=True)
    parser.add_argument("--parent-checkpoint", required=True, type=Path)
    parser.add_argument("--parent-checkpoint-sha256", required=True)
    parser.add_argument("--real-checkpoint", action="append", default=[], required=True)
    parser.add_argument(
        "--real-checkpoint-sha256", action="append", default=[], required=True
    )
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--simulator-seeds", required=True, type=_parse_ints)
    parser.add_argument("--battle-indices", default="0..12", type=_parse_ints)
    parser.add_argument("--ascension", default=0, type=int)
    parser.add_argument("--max-decisions-per-seed", default=100, type=int)
    parser.add_argument("--max-actions-per-turn", default=8, type=int)
    parser.add_argument("--behavior-seed", default=2026082804, type=int)
    parser.add_argument("--network-seed", default=2026082805, type=int)
    parser.add_argument("--minimum-stratum-count", default=64, type=int)
    parser.add_argument("--max-report-bytes", default=4_194_304, type=int)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    bindings = _real_bindings(args)
    real_batch, real_evidence = load_real_replay_bindings(bindings)

    registered_identity = {
        "items_json": verify_file_identity(
            args.items_json,
            args.expected_items_sha256,
            label="items JSON",
        ),
        "module": verify_file_identity(
            args.module,
            args.expected_module_sha256,
            label="native module",
        ),
        "runner": verify_file_identity(
            Path(__file__),
            args.expected_runner_sha256,
            label="calibration runner",
        ),
    }

    native_module = load_native_module(args.module, dll_directories=args.dll_dir)
    provenance = collect_provenance(
        repo_root=args.repo_root,
        simulator_repo=args.simulator_repo,
        module_path=args.module,
        native_module=native_module,
    )
    registered_identity["source"] = validate_provenance_identity(
        provenance,
        adapter_source_sha256=args.expected_adapter_source_sha256,
        simulator_commit=args.expected_simulator_commit,
        simulator_source_sha256=args.expected_simulator_source_sha256,
    )
    provenance["calibration_runner_sha256"] = registered_identity["runner"][
        "sha256"
    ]
    provenance["items_json_path"] = registered_identity["items_json"]["path"]
    provenance["items_json_sha256"] = registered_identity["items_json"]["sha256"]
    provenance["registered_identity"] = registered_identity
    collection_config = build_collection_config(
        seeds=args.simulator_seeds,
        battle_indices=args.battle_indices,
        behavior_seed=args.behavior_seed,
        network_seed=args.network_seed,
        max_decisions_per_seed=args.max_decisions_per_seed,
        max_actions_per_turn=args.max_actions_per_turn,
        ascension=args.ascension,
    )
    simulator_batch, collection, initialization = collect_simulator_replay(
        native_module,
        items_json=args.items_json,
        parent_checkpoint=args.parent_checkpoint,
        parent_checkpoint_sha256=args.parent_checkpoint_sha256,
        config=collection_config,
    )
    real_summary = summarize_source(real_batch)
    simulator_summary = summarize_source(simulator_batch)
    comparison = compare_sources(
        real_summary,
        simulator_summary,
        minimum_stratum_count=args.minimum_stratum_count,
    )
    report_config = {
        "ascension": args.ascension,
        "battle_indices": list(args.battle_indices),
        "behavior_epsilon": 0.0,
        "behavior_policy": FROZEN_PARENT_GUARDED_EPSILON_BEHAVIOR,
        "behavior_seed": args.behavior_seed,
        "max_actions_per_turn": args.max_actions_per_turn,
        "max_decisions_per_seed": args.max_decisions_per_seed,
        "minimum_stratum_count": args.minimum_stratum_count,
        "network_seed": args.network_seed,
        "simulator_seeds": list(args.simulator_seeds),
    }
    report = build_report(
        real_summary=real_summary,
        simulator_summary=simulator_summary,
        comparison=comparison,
        provenance=provenance,
        config=report_config,
        real_bindings=real_evidence,
        simulator_collection=collection,
        optimizer_step=int(collection["optimizer_step"]),
        initialization=initialization,
    )
    repeated = build_report(
        real_summary=real_summary,
        simulator_summary=simulator_summary,
        comparison=comparison,
        provenance=provenance,
        config=report_config,
        real_bindings=real_evidence,
        simulator_collection=collection,
        optimizer_step=int(collection["optimizer_step"]),
        initialization=initialization,
    )
    if canonical_report_bytes(report) != canonical_report_bytes(repeated):
        raise RuntimeError("calibration report is not deterministic in memory")
    publish_report(
        args.output_dir,
        report,
        max_report_bytes=args.max_report_bytes,
    )
    print(
        canonical_json_bytes(
            {"output_dir": str(args.output_dir.resolve()), "verdict": report["verdict"]}
        ).decode("utf-8")
    )
    return 0 if report["verdict"] == "replay_distribution_calibration_ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
