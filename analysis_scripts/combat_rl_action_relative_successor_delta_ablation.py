"""Collect and evaluate one action-relative first-successor delta ablation."""

from __future__ import annotations

import copy
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import time
from types import ModuleType
from typing import Any, Callable, Mapping, Sequence

import torch
import torch.nn.functional as F


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_ROOT = REPO_ROOT / "reports"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from analysis_scripts.combat_lightspeed_bridge import (  # noqa: E402
    NativeCombatEnvironment,
    collect_provenance,
    load_native_module,
)
from analysis_scripts.combat_lightspeed_training_smoke import (  # noqa: E402
    GREEDY_NATIVE_REWARD_DEPLOYMENT_GUARD_PROXY,
    _policy_action,
    apply_deployment_guard_proxy,
    calculate_native_reward,
    create_fresh_trainer,
    encounter_from_snapshot,
    initialization_failure_reason,
    initialize_trainer,
    load_initial_checkpoint,
    parameter_sha256,
    sha256_file,
    successor_disposition,
)
from analysis_scripts.combat_rl_guard_advantage_corpus import (  # noqa: E402
    _continuation_selector,
    canonical_action_identity,
    canonical_action_key,
    canonicalize_actions,
)
from analysis_scripts.combat_lightspeed_replay_distribution_calibration import (  # noqa: E402
    RealReplayBinding,
    load_real_replay_bindings,
)
from analysis_scripts.combat_rl_guard_advantage_residual_fit import (  # noqa: E402
    _trainer_metadata,
    _validate_commit,
)
from analysis_scripts.combat_rl_real_context_weighted_action_relative_fit import (  # noqa: E402
    FIXED_OFFLINE_GATES,
    FIXED_RECIPE as WEIGHTED_FIT_RECIPE,
    apply_weighted_offline_gates,
    build_weighted_class_balanced_sample_plan,
    build_weighted_replacement_sample_plan,
    derive_pair_sampling_weights,
    derive_ranking_sampling_weights,
    weighted_higher_quantile,
    weighted_policy_metrics,
)
from analysis_scripts import combat_rl_real_context_balanced_corpus as balanced  # noqa: E402
from spirecomm.ai.rl.v2.action_relative_selective_classifier import (  # noqa: E402
    BENEFICIAL_CLASS,
    CLASS_NAMES,
    ActionRelativeSelectiveClassifier,
    ActionRelativeSelectiveConfig,
    SUPPORTED_ACTION_STOP,
    build_within_state_ranking_pairs,
    classify_advantages,
)
from spirecomm.ai.rl.v2.id_mapping import build_id_mapper  # noqa: E402
from spirecomm.ai.rl.v2.latent_gated_adapter import state_dict_sha256  # noqa: E402


CORPUS_SCHEMA = "combat-rl-action-relative-successor-corpus-v1"
CORPUS_KIND = "combat_action_relative_first_successor_pairs"
CORPUS_REGISTRATION_SCHEMA = (
    "combat-rl-action-relative-successor-corpus-registration-v1"
)
CORPUS_EXPERIMENT_ID = "combat-rl-action-relative-successor-corpus-20260829-r2"
SMOKE_EXPERIMENT_ID = (
    "combat-rl-action-relative-successor-corpus-smoke-20260829-r1"
)
FIT_EXPERIMENT_ID = "combat-rl-action-relative-successor-delta-ablation-20260829-r1"
CORPUS_OUTPUT_DIR = REPORTS_ROOT / CORPUS_EXPERIMENT_ID.replace("-", "_")
SMOKE_OUTPUT_DIR = REPORTS_ROOT / SMOKE_EXPERIMENT_ID.replace("-", "_")
EXPECTED_INTERPRETER = Path(r"D:\anaconda\envs\stsai\python.exe")
SIMULATOR_REPO = Path(r"D:\CLionProjects\sts_lightspeed")
CORPUS_REGISTRATION_PATH = REPORTS_ROOT / (
    f"{CORPUS_EXPERIMENT_ID.replace('-', '_')}_registration.json"
)
CORPUS_PREFLIGHT_PATH = REPORTS_ROOT / (
    f"{CORPUS_EXPERIMENT_ID.replace('-', '_')}_preflight.json"
)
SMOKE_REGISTRATION_PATH = REPORTS_ROOT / (
    f"{SMOKE_EXPERIMENT_ID.replace('-', '_')}_registration.json"
)
SMOKE_PREFLIGHT_PATH = REPORTS_ROOT / (
    f"{SMOKE_EXPERIMENT_ID.replace('-', '_')}_preflight.json"
)
FIT_OUTPUT_DIR = REPORTS_ROOT / FIT_EXPERIMENT_ID.replace("-", "_")
FIT_REGISTRATION_PATH = REPORTS_ROOT / (
    f"{FIT_EXPERIMENT_ID.replace('-', '_')}_registration.json"
)
FIT_PREFLIGHT_PATH = REPORTS_ROOT / (
    f"{FIT_EXPERIMENT_ID.replace('-', '_')}_preflight.json"
)
FIT_REGISTRATION_SCHEMA = (
    "combat-rl-action-relative-successor-delta-ablation-registration-v1"
)
PREDECESSOR_FAILURE = {
    "path": REPORTS_ROOT
    / "combat_rl_action_relative_successor_corpus_20260829_r1_failure.json",
    "sha256": "c841ecae533f9e85caefa89867ee74399d8c08ca68210a8a264521b117abc3dd",
}

SUPPORTED = 0
TERMINAL_VICTORY = 1
TERMINAL_DEFEAT = 2
TERMINAL_OTHER = 3
DISPOSITION_COUNT = 4
DISPOSITION_NAMES = (
    "supported",
    "terminal_victory",
    "terminal_defeat",
    "terminal_other",
)
FLOAT32_CONSISTENCY_ATOL = 1e-4
FLOAT32_CONSISTENCY_RTOL = 1e-6

SOURCE_TENSOR_NAMES = (
    "continuous",
    "card_ids",
    "potion_ids",
    "relic_ids",
    "action_masks",
    "guard_actions",
    "target_actions",
    "advantages",
    "positive",
)
SUCCESSOR_STATE_NAMES = (
    "continuous",
    "card_ids",
    "potion_ids",
    "relic_ids",
    "action_masks",
)
PAIR_SCALAR_TENSOR_NAMES = (
    "source_rows",
    "candidate_actions",
    "guard_returns",
    "candidate_returns",
    "advantages",
    "guard_immediate_rewards",
    "candidate_immediate_rewards",
    "guard_dispositions",
    "candidate_dispositions",
)
PAIR_TENSOR_NAMES = PAIR_SCALAR_TENSOR_NAMES + tuple(
    f"{prefix}_successor_{name}"
    for prefix in ("guard", "candidate")
    for name in SUCCESSOR_STATE_NAMES
)

FIXED_COHORT = {
    "fit": [275000, 275767],
    "calibration": [275768, 276023],
    "fresh": [277000, 277255],
}
FIXED_CORPUS_RECIPE = {
    "partitions": copy.deepcopy(FIXED_COHORT),
    "battle_indices": [0, 3, 6, 9, 10],
    "ascension": 0,
    "max_source_decisions": 100,
    "max_actions_per_turn": 8,
    "max_states_per_profile": 2,
    "max_canonical_actions": 8,
    "continuation_decisions": 8,
    "return_discount": 0.99,
    "positive_advantage_margin": 0.5,
    "max_wall_seconds": 28800,
    "max_stored_bytes": 1610612736,
}
SMOKE_CORPUS_RECIPE = {
    **copy.deepcopy(FIXED_CORPUS_RECIPE),
    "partitions": {"smoke": [274990, 274991]},
    "battle_indices": [0, 10],
    "max_source_decisions": 40,
    "max_states_per_profile": 1,
    "continuation_decisions": 2,
    "max_wall_seconds": 900,
    "max_stored_bytes": 67108864,
}

FIXED_INPUTS = {
    "native_module": {
        "path": REPO_ROOT
        / ".sts_lightspeed_combat_guard_advantage_20260828_r1_build"
        / "sts_lightspeed_combat_adapter.cp310-win_amd64.pyd",
        "sha256": "195678b7fc6bf69815f3d2971404afb8ce72fb666700edf4203383429caf1009",
    },
    "items_json": {
        "path": Path(r"D:\SteamLibrary\steamapps\common\SlayTheSpire\export\items.json"),
        "sha256": "e23784ea8ed3092e3bfa9918240e162a9cbcb837badfb53c612eb0d83cc811dc",
    },
    "parent_checkpoint": {
        "path": REPORTS_ROOT
        / "combat_lightspeed_production_r16_shadow_20260819_r1"
        / "simulator_only_production_shadow.pth",
        "sha256": "ce2ae34f82b3f457fb35e87d429c397204c42d0f742d3ac8952d91b69119b83b",
    },
    "real_r14_replay": {
        "path": REPORTS_ROOT
        / "combat_rl_parent_on_policy_replay_collection_20260818_r14"
        / "rl_combat_model_ep20_steps3765.pth",
        "sha256": "eed11099d1b8d35baa8ce0ccbf87efb6fb4a864e6fe6246837b0cac91c505014",
    },
    "real_r15_replay": {
        "path": REPORTS_ROOT
        / "combat_rl_parent_on_policy_replay_collection_20260818_r15"
        / "rl_combat_model_ep20_steps3920.pth",
        "sha256": "67c3a49fbb2094d20793214c0a4a294684054eb6f4a24ac59573fab29c39a2dd",
    },
}
CORPUS_AUTHORITY = {
    "native_loading": True,
    "environment_construction": True,
    "cpu_corpus_collection": True,
    "model_fitting": False,
    "training": False,
    "fresh_evaluation": False,
    "lightspeed_policy_gate": False,
    "gameplay": False,
    "communication_mod": False,
    "production_checkpoint_loading": False,
    "production_checkpoint_writing": False,
    "qualification": False,
    "promotion": False,
}

SOURCE_SNAPSHOT_PATHS = (
    "analysis_scripts/combat_rl_action_relative_successor_delta_ablation.py",
    "analysis_scripts/combat_rl_guard_advantage_corpus.py",
    "analysis_scripts/combat_rl_real_context_weighted_action_relative_fit.py",
    "analysis_scripts/combat_rl_real_context_balanced_corpus.py",
    "analysis_scripts/combat_lightspeed_bridge.py",
    "analysis_scripts/combat_lightspeed_training_smoke.py",
    "spirecomm/ai/rl/v2/action_relative_selective_classifier.py",
    "spirecomm/ai/rl/v2/action_relative_advantage_residual.py",
    "spirecomm/ai/rl/v2/action_space.py",
    "spirecomm/ai/rl/v2/id_mapping.py",
    "spirecomm/ai/rl/v2/state_encoder.py",
    "spirecomm/ai/rl/v2/network.py",
)


@dataclass(frozen=True)
class SuccessorBranchResult:
    action_index: int
    total_return: float
    transition_count: int
    complete: bool
    terminal: bool
    immediate_reward: float | None = None
    disposition: int | None = None
    successor: Mapping[str, torch.Tensor] | None = None
    exclusion_reason: str = ""


@dataclass
class FreshAccessBoundary:
    """One-use in-memory boundary for deferred fresh-corpus access."""

    frozen_arms: dict[str, dict[str, Any]] | None = None
    accessed: bool = False

    def __post_init__(self) -> None:
        if self.frozen_arms is None:
            self.frozen_arms = {}

    def freeze_arm(self, name: str, state_sha256: str, threshold: float) -> None:
        if name not in {"control", "successor"}:
            raise ValueError("fresh boundary arm identity differs")
        if name in self.frozen_arms:
            raise RuntimeError("fresh boundary arm is already frozen")
        digest = _validate_sha256(state_sha256, label=f"{name} state")
        if not isinstance(threshold, (int, float)) or isinstance(threshold, bool):
            raise ValueError("fresh boundary threshold is invalid")
        if not math.isfinite(float(threshold)):
            raise ValueError("fresh boundary threshold is invalid")
        self.frozen_arms[name] = {
            "state_sha256": digest,
            "selection_threshold": float(threshold),
        }

    def authorize_fresh_access(self) -> dict[str, Any]:
        if set(self.frozen_arms) != {"control", "successor"}:
            raise RuntimeError("fresh access requires both arms and thresholds frozen")
        if self.accessed:
            raise RuntimeError("fresh evidence may be accessed only once")
        self.accessed = True
        return {
            "loaded_after_both_arms_and_thresholds_frozen": True,
            "arms": copy.deepcopy(self.frozen_arms),
            "single_access": True,
        }


def _canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(value, allow_nan=False, ensure_ascii=True, indent=2, sort_keys=True)
        + "\n"
    ).encode("ascii")


def _validate_sha256(value: Any, *, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} SHA-256 is missing")
    normalized = value.lower()
    if len(normalized) != 64 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise ValueError(f"{label} SHA-256 is invalid")
    return normalized


def _tensor_state(mapped: Any) -> dict[str, torch.Tensor]:
    if isinstance(mapped, Mapping):
        values = mapped
    else:
        values = {
            "continuous": torch.from_numpy(mapped.state.continuous.copy()).float(),
            "card_ids": torch.from_numpy(mapped.state.card_ids.copy()).long(),
            "potion_ids": torch.from_numpy(mapped.state.potion_ids.copy()).long(),
            "relic_ids": torch.from_numpy(mapped.state.relic_ids.copy()).long(),
            "action_masks": torch.from_numpy(mapped.action_mask.copy()).bool(),
        }
    result = {name: torch.as_tensor(values[name]).detach().cpu() for name in SUCCESSOR_STATE_NAMES}
    if set(result) != set(SUCCESSOR_STATE_NAMES):
        raise ValueError("successor state tensor inventory differs")
    if result["continuous"].ndim != 1 or result["action_masks"].ndim != 1:
        raise ValueError("successor state tensor dimensions differ")
    if not bool(torch.isfinite(result["continuous"]).all()):
        raise ValueError("successor state continuous values are not finite")
    return result


def _terminal_disposition(outcome: Any) -> int:
    if outcome == "player_victory":
        return TERMINAL_VICTORY
    if outcome == "player_defeat":
        return TERMINAL_DEFEAT
    return TERMINAL_OTHER


def rollout_successor_branch(
    source_environment: Any,
    first_action: Mapping[str, Any],
    *,
    source_actions_since_end_turn: int,
    continuation_selector: Callable[[Any, int], Mapping[str, Any]],
    continuation_decisions: int,
    discount: float,
    map_successor: Callable[[Any], Mapping[str, torch.Tensor] | Any],
    reward_fn: Callable[..., Mapping[str, float]] = calculate_native_reward,
) -> SuccessorBranchResult:
    if continuation_decisions < 0:
        raise ValueError("successor continuation decisions are invalid")
    if not math.isfinite(float(discount)) or not 0.0 < float(discount) <= 1.0:
        raise ValueError("successor return discount is invalid")
    environment = source_environment.clone()
    action = dict(first_action)
    action_index = int(first_action["rl_action_index"])
    total_return = 0.0
    transition_count = 0
    actions_since_end_turn = int(source_actions_since_end_turn)
    first_reward: float | None = None
    first_disposition: int | None = None
    first_successor: Mapping[str, torch.Tensor] | None = None
    for offset in range(continuation_decisions + 1):
        if offset:
            status = environment.status()
            disposition, reason = successor_disposition(status)
            if disposition == "terminal":
                return SuccessorBranchResult(
                    action_index,
                    total_return,
                    transition_count,
                    True,
                    True,
                    first_reward,
                    first_disposition,
                    first_successor,
                )
            if disposition == "exclude":
                return SuccessorBranchResult(
                    action_index,
                    total_return,
                    transition_count,
                    False,
                    False,
                    first_reward,
                    first_disposition,
                    first_successor,
                    reason,
                )
            action = dict(continuation_selector(environment, actions_since_end_turn))
        before = environment.snapshot()
        environment.step(str(action["action_id"]))
        status = environment.status()
        after = environment.snapshot()
        disposition, reason = successor_disposition(status)
        if disposition == "exclude":
            return SuccessorBranchResult(
                action_index,
                total_return,
                transition_count,
                False,
                False,
                first_reward,
                first_disposition,
                first_successor,
                reason,
            )
        reward = float(
            reward_fn(
                before,
                after,
                action_kind=str(action["kind"]),
                outcome=str(status.get("outcome") or "undecided"),
            )["total"]
        )
        if not math.isfinite(reward):
            raise ValueError("successor branch reward is not finite")
        total_return += (float(discount) ** offset) * reward
        transition_count += 1
        if offset == 0:
            first_reward = reward
            if disposition == "terminal":
                first_disposition = _terminal_disposition(status.get("outcome"))
            else:
                first_disposition = SUPPORTED
                first_successor = _tensor_state(map_successor(environment))
        actions_since_end_turn = (
            0 if action["kind"] == "end_turn" else actions_since_end_turn + 1
        )
        if disposition == "terminal":
            return SuccessorBranchResult(
                action_index,
                total_return,
                transition_count,
                True,
                True,
                first_reward,
                first_disposition,
                first_successor,
            )
    return SuccessorBranchResult(
        action_index,
        total_return,
        transition_count,
        True,
        False,
        first_reward,
        first_disposition,
        first_successor,
    )


def validate_partition_seed_contract(
    partitions: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, list[int]]:
    if set(partitions) != set(FIXED_COHORT):
        raise ValueError("successor partition inventory differs")
    observed: dict[str, list[int]] = {}
    all_seeds: set[int] = set()
    for name, rows in partitions.items():
        first, last = FIXED_COHORT[name]
        seeds: list[int] = []
        for row in rows:
            seed = row.get("seed")
            if not isinstance(seed, int) or isinstance(seed, bool):
                raise ValueError("successor partition seed is invalid")
            if not first <= seed <= last:
                raise ValueError("successor seed is outside registered partition")
            seeds.append(seed)
        overlap = all_seeds.intersection(seeds)
        if overlap:
            raise ValueError("successor seed partitions overlap")
        all_seeds.update(seeds)
        observed[name] = sorted(set(seeds))
    return observed


def _normalized_source_tensors(
    tensors: Mapping[str, Any], row_count: int
) -> dict[str, torch.Tensor]:
    if not isinstance(tensors, Mapping) or set(tensors) != set(SOURCE_TENSOR_NAMES):
        raise ValueError("successor corpus source tensor inventory differs")
    result = {
        name: torch.as_tensor(tensors[name]).detach().cpu()
        for name in SOURCE_TENSOR_NAMES
    }
    if row_count <= 0 or any(value.shape[0] != row_count for value in result.values()):
        raise ValueError("successor corpus source tensor rows differ")
    if result["continuous"].ndim != 2 or result["action_masks"].ndim != 2:
        raise ValueError("successor corpus source tensor dimensions differ")
    if not bool(torch.isfinite(result["continuous"]).all()) or not bool(
        torch.isfinite(result["advantages"]).all()
    ):
        raise ValueError("successor corpus source values are not finite")
    result["action_masks"] = result["action_masks"].bool()
    result["guard_actions"] = result["guard_actions"].long().reshape(-1)
    result["target_actions"] = result["target_actions"].long().reshape(-1)
    result["advantages"] = result["advantages"].float().reshape(-1)
    result["positive"] = result["positive"].bool().reshape(-1)
    return result


def _normalized_pair_tensors(
    pairs: Mapping[str, Any], pair_count: int
) -> dict[str, torch.Tensor]:
    if not isinstance(pairs, Mapping) or set(pairs) != set(PAIR_TENSOR_NAMES):
        raise ValueError("successor corpus pair tensor inventory differs")
    result = {
        name: torch.as_tensor(pairs[name]).detach().cpu() for name in PAIR_TENSOR_NAMES
    }
    if pair_count <= 0 or any(value.shape[0] != pair_count for value in result.values()):
        raise ValueError("successor corpus pair tensor rows differ")
    for name in ("source_rows", "candidate_actions", "guard_dispositions", "candidate_dispositions"):
        result[name] = result[name].long().reshape(-1)
    for name in (
        "guard_returns",
        "candidate_returns",
        "advantages",
        "guard_immediate_rewards",
        "candidate_immediate_rewards",
    ):
        result[name] = result[name].float().reshape(-1)
        if not bool(torch.isfinite(result[name]).all()):
            raise ValueError("successor corpus pair values are not finite")
    for prefix in ("guard", "candidate"):
        result[f"{prefix}_successor_action_masks"] = result[
            f"{prefix}_successor_action_masks"
        ].bool()
    return result


def validate_successor_corpus(
    corpus: Mapping[str, Any], *, expected_partition: str
) -> dict[str, Any]:
    required = {
        "schema_version",
        "corpus_kind",
        "partition",
        "tensors",
        "metadata",
        "pairs",
        "row_count",
        "pair_count",
    }
    if not isinstance(corpus, Mapping) or set(corpus) != required:
        raise ValueError("successor corpus root keys differ")
    if corpus["schema_version"] != CORPUS_SCHEMA or corpus["corpus_kind"] != CORPUS_KIND:
        raise ValueError("successor corpus identity differs")
    if corpus["partition"] != expected_partition:
        raise ValueError("successor corpus partition differs")
    row_count = int(corpus["row_count"])
    pair_count = int(corpus["pair_count"])
    metadata = corpus["metadata"]
    if not isinstance(metadata, list) or len(metadata) != row_count:
        raise ValueError("successor corpus metadata rows differ")
    tensors = _normalized_source_tensors(corpus["tensors"], row_count)
    pairs = _normalized_pair_tensors(corpus["pairs"], pair_count)
    source_rows = pairs["source_rows"]
    if bool((source_rows < 0).any()) or bool((source_rows >= row_count).any()):
        raise ValueError("successor pair source row is invalid")
    if source_rows.tolist() != sorted(source_rows.tolist()):
        raise ValueError("successor pair source rows are not stable")
    action_dim = int(tensors["action_masks"].shape[1])
    guards = tensors["guard_actions"]
    candidates = pairs["candidate_actions"]
    rows = torch.arange(row_count)
    if bool((guards < 0).any()) or bool((guards >= action_dim).any()) or not bool(
        tensors["action_masks"][rows, guards].all()
    ):
        raise ValueError("successor corpus guard action is illegal")
    if bool((candidates < 0).any()) or bool((candidates >= SUPPORTED_ACTION_STOP).any()):
        raise ValueError("successor corpus candidate action is unsupported")
    if not bool(tensors["action_masks"][source_rows, candidates].all()):
        raise ValueError("successor corpus candidate action is illegal")
    if bool(candidates.eq(guards[source_rows]).any()):
        raise ValueError("successor corpus candidate duplicates guard")
    if not torch.allclose(
        pairs["candidate_returns"] - pairs["guard_returns"],
        pairs["advantages"],
        atol=FLOAT32_CONSISTENCY_ATOL,
        rtol=FLOAT32_CONSISTENCY_RTOL,
    ):
        raise ValueError("successor pair advantage differs from branch returns")
    valid_dispositions = set(range(DISPOSITION_COUNT))
    for prefix in ("guard", "candidate"):
        dispositions = pairs[f"{prefix}_dispositions"]
        if not set(dispositions.tolist()).issubset(valid_dispositions):
            raise ValueError("successor pair disposition is invalid")
        terminal = dispositions.ne(SUPPORTED)
        for state_name in SUCCESSOR_STATE_NAMES:
            state = pairs[f"{prefix}_successor_{state_name}"]
            if state.ndim < 2:
                raise ValueError("successor pair state dimensions differ")
            if bool(terminal.any()) and bool(state[terminal].ne(0).any()):
                raise ValueError("terminal successor tensors must be zero")
        supported = ~terminal
        if bool(supported.any()) and not bool(
            pairs[f"{prefix}_successor_action_masks"][supported].any(dim=1).all()
        ):
            raise ValueError("supported successor lacks legal actions")
    for source_index, row in enumerate(metadata):
        if not isinstance(row, Mapping):
            raise ValueError("successor corpus metadata row is invalid")
        guard = int(guards[source_index])
        if int(row.get("guard_action_index", -1)) != guard:
            raise ValueError("successor corpus metadata guard differs")
        branches = row.get("branch_returns")
        if not isinstance(branches, Mapping) or str(guard) not in branches:
            raise ValueError("successor corpus branch returns are missing")
        member = source_rows.eq(source_index).nonzero(as_tuple=False).reshape(-1)
        if not int(member.numel()):
            raise ValueError("successor corpus source lacks candidate pairs")
        for pair_index in member.tolist():
            action = int(candidates[pair_index])
            if str(action) not in branches or not math.isclose(
                float(branches[str(action)]),
                float(pairs["candidate_returns"][pair_index]),
                abs_tol=FLOAT32_CONSISTENCY_ATOL,
                rel_tol=FLOAT32_CONSISTENCY_RTOL,
            ):
                raise ValueError("successor pair branch return differs")
            if not math.isclose(
                float(branches[str(guard)]),
                float(pairs["guard_returns"][pair_index]),
                abs_tol=FLOAT32_CONSISTENCY_ATOL,
                rel_tol=FLOAT32_CONSISTENCY_RTOL,
            ):
                raise ValueError("successor guard branch return differs")
    return {
        "schema_version": CORPUS_SCHEMA,
        "corpus_kind": CORPUS_KIND,
        "partition": expected_partition,
        "tensors": tensors,
        "metadata": [copy.deepcopy(dict(row)) for row in metadata],
        "pairs": pairs,
        "row_count": row_count,
        "pair_count": pair_count,
    }


def mask_terminal_latents(
    latents: torch.Tensor, dispositions: torch.Tensor
) -> torch.Tensor:
    values = latents.float()
    codes = dispositions.reshape(-1).long()
    if values.ndim != 2 or values.shape[0] != codes.numel():
        raise ValueError("successor latent rows differ")
    if not set(codes.tolist()).issubset(set(range(DISPOSITION_COUNT))):
        raise ValueError("successor latent disposition is invalid")
    return values * codes.eq(SUPPORTED).to(values.dtype).unsqueeze(1)


def compose_successor_delta_features(
    base_features: torch.Tensor,
    *,
    candidate_latent: torch.Tensor,
    guard_latent: torch.Tensor,
    candidate_rewards: torch.Tensor,
    guard_rewards: torch.Tensor,
    candidate_dispositions: torch.Tensor,
    guard_dispositions: torch.Tensor,
) -> torch.Tensor:
    base = base_features.float()
    candidate = candidate_latent.float()
    guard = guard_latent.float()
    count = base.shape[0]
    if base.ndim != 2 or candidate.shape != guard.shape or candidate.ndim != 2:
        raise ValueError("successor feature latent shapes differ")
    if candidate.shape[0] != count:
        raise ValueError("successor feature rows differ")
    candidate_codes = candidate_dispositions.reshape(-1).long()
    guard_codes = guard_dispositions.reshape(-1).long()
    candidate_reward = candidate_rewards.reshape(-1).float()
    guard_reward = guard_rewards.reshape(-1).float()
    if any(value.numel() != count for value in (
        candidate_codes, guard_codes, candidate_reward, guard_reward
    )):
        raise ValueError("successor feature scalar rows differ")
    values = torch.cat(
        (
            base,
            candidate - guard,
            (candidate_reward - guard_reward).unsqueeze(1),
            F.one_hot(candidate_codes, num_classes=DISPOSITION_COUNT).float(),
            F.one_hot(guard_codes, num_classes=DISPOSITION_COUNT).float(),
        ),
        dim=1,
    )
    if not bool(torch.isfinite(values).all()):
        raise ValueError("successor features are not finite")
    return values


def compare_representation_signal(
    control: Mapping[str, Any], successor: Mapping[str, Any]
) -> dict[str, Any]:
    control_selection = control["raw"]["selection"]
    successor_selection = successor["raw"]["selection"]
    control_count = int(control_selection["intervention_count"])
    successor_count = int(successor_selection["intervention_count"])
    control_rate = (
        int(control_selection["severe_harm_count"]) / control_count
        if control_count
        else 0.0
    )
    successor_rate = (
        int(successor_selection["severe_harm_count"]) / successor_count
        if successor_count
        else 0.0
    )
    precision_delta = float(successor["weighted"]["intervention_precision"]) - float(
        control["weighted"]["intervention_precision"]
    )
    advantage_delta = float(
        successor["weighted"]["mean_selected_true_advantage"]
    ) - float(control["weighted"]["mean_selected_true_advantage"])
    conditions = {
        "weighted_precision_improvement_at_least_0_10": precision_delta >= 0.10,
        "weighted_mean_selected_advantage_improvement_at_least_0_10": (
            advantage_delta >= 0.10
        ),
        "raw_severe_harm_rate_reduced_at_least_half": (
            successor_rate <= 0.5 * control_rate
        ),
    }
    passed = all(conditions.values())
    return {
        "conditions": conditions,
        "all_conditions_passed": passed,
        "weighted_precision_delta": precision_delta,
        "weighted_mean_selected_advantage_delta": advantage_delta,
        "control_raw_severe_harm_rate": control_rate,
        "successor_raw_severe_harm_rate": successor_rate,
        "decision": (
            "descriptive_successor_signal_without_policy_authority"
            if passed
            else "no_material_successor_representation_signal"
        ),
        "authority": {
            "fresh_lightspeed_gate": False,
            "gameplay": False,
            "qualification": False,
            "promotion": False,
        },
    }


def _input_registration(*, smoke: bool) -> dict[str, dict[str, str]]:
    result = {
        name: {"path": str(binding["path"].resolve()), "sha256": binding["sha256"]}
        for name, binding in sorted(FIXED_INPUTS.items())
    }
    if not smoke:
        result["predecessor_failure"] = {
            "path": str(PREDECESSOR_FAILURE["path"].resolve()),
            "sha256": PREDECESSOR_FAILURE["sha256"],
        }
    return dict(sorted(result.items()))


def _source_file_hashes() -> dict[str, str]:
    return {
        relative: sha256_file(REPO_ROOT / relative)
        for relative in SOURCE_SNAPSHOT_PATHS
    }


def build_corpus_registration(
    source_commit: str,
    *,
    experiment_id: str,
    output_dir: Path,
    smoke: bool,
) -> dict[str, Any]:
    source_commit = _validate_commit(source_commit)
    expected_id = SMOKE_EXPERIMENT_ID if smoke else CORPUS_EXPERIMENT_ID
    expected_output = SMOKE_OUTPUT_DIR if smoke else CORPUS_OUTPUT_DIR
    if experiment_id != expected_id or output_dir.resolve() != expected_output.resolve():
        raise ValueError("successor corpus registration identity differs")
    return {
        "schema_version": CORPUS_REGISTRATION_SCHEMA,
        "experiment_id": expected_id,
        "source_commit": source_commit,
        "runner": {
            "path": str(Path(__file__).resolve()),
            "sha256": sha256_file(Path(__file__)),
        },
        "source_files": _source_file_hashes(),
        "inputs": _input_registration(smoke=smoke),
        "recipe": copy.deepcopy(SMOKE_CORPUS_RECIPE if smoke else FIXED_CORPUS_RECIPE),
        "output_dir": str(expected_output.resolve()),
        "smoke": smoke,
        "attempt": 1 if smoke else 2,
        "authority": copy.deepcopy(CORPUS_AUTHORITY),
    }


def validate_corpus_registration(
    registration: Mapping[str, Any], *, smoke: bool
) -> dict[str, Any]:
    expected = build_corpus_registration(
        str(registration.get("source_commit", "")),
        experiment_id=SMOKE_EXPERIMENT_ID if smoke else CORPUS_EXPERIMENT_ID,
        output_dir=SMOKE_OUTPUT_DIR if smoke else CORPUS_OUTPUT_DIR,
        smoke=smoke,
    )
    if dict(registration) != expected:
        raise ValueError("successor corpus registration payload differs")
    return copy.deepcopy(expected)


def _zero_successor_like(source: Mapping[str, torch.Tensor]) -> dict[str, torch.Tensor]:
    return {name: torch.zeros_like(source[name]) for name in SUCCESSOR_STATE_NAMES}


def _successor_or_zero(
    result: SuccessorBranchResult, source: Mapping[str, torch.Tensor]
) -> dict[str, torch.Tensor]:
    if result.disposition == SUPPORTED:
        if result.successor is None:
            raise ValueError("supported successor state is missing")
        mapped = _tensor_state(result.successor)
        for name in SUCCESSOR_STATE_NAMES:
            if mapped[name].shape != source[name].shape:
                raise ValueError("successor state shape differs from source")
        return mapped
    if result.disposition in {
        TERMINAL_VICTORY,
        TERMINAL_DEFEAT,
        TERMINAL_OTHER,
    }:
        if result.successor is not None:
            raise ValueError("terminal successor unexpectedly has mapped state")
        return _zero_successor_like(source)
    raise ValueError("successor branch disposition is incomplete")


def _stack_successor_partition(
    source_rows: Sequence[Mapping[str, Any]],
    pair_rows: Sequence[Mapping[str, Any]],
    *,
    partition: str,
) -> dict[str, Any]:
    if not source_rows or not pair_rows:
        raise ValueError("successor partition has no complete pairs")
    tensors = {
        name: torch.stack([torch.as_tensor(row[name]) for row in source_rows])
        for name in (
            "continuous",
            "card_ids",
            "potion_ids",
            "relic_ids",
            "action_masks",
        )
    }
    tensors.update(
        {
            "guard_actions": torch.tensor(
                [row["guard_action_index"] for row in source_rows], dtype=torch.long
            ),
            "target_actions": torch.tensor(
                [row["target_action_index"] for row in source_rows], dtype=torch.long
            ),
            "advantages": torch.tensor(
                [row["target_advantage"] for row in source_rows], dtype=torch.float32
            ),
            "positive": torch.tensor(
                [row["positive"] for row in source_rows], dtype=torch.bool
            ),
        }
    )
    pairs: dict[str, torch.Tensor] = {
        "source_rows": torch.tensor(
            [row["source_row"] for row in pair_rows], dtype=torch.long
        ),
        "candidate_actions": torch.tensor(
            [row["candidate_action_index"] for row in pair_rows], dtype=torch.long
        ),
    }
    for name in (
        "guard_returns",
        "candidate_returns",
        "advantages",
        "guard_immediate_rewards",
        "candidate_immediate_rewards",
    ):
        pairs[name] = torch.tensor(
            [row[name] for row in pair_rows], dtype=torch.float32
        )
    for name in ("guard_dispositions", "candidate_dispositions"):
        pairs[name] = torch.tensor([row[name] for row in pair_rows], dtype=torch.long)
    for prefix in ("guard", "candidate"):
        for name in SUCCESSOR_STATE_NAMES:
            pairs[f"{prefix}_successor_{name}"] = torch.stack(
                [torch.as_tensor(row[f"{prefix}_successor"][name]) for row in pair_rows]
            )
    tensor_keys = {
        "continuous",
        "card_ids",
        "potion_ids",
        "relic_ids",
        "action_masks",
    }
    metadata = [
        {key: copy.deepcopy(value) for key, value in row.items() if key not in tensor_keys}
        for row in source_rows
    ]
    return validate_successor_corpus(
        {
            "schema_version": CORPUS_SCHEMA,
            "corpus_kind": CORPUS_KIND,
            "partition": partition,
            "tensors": tensors,
            "metadata": metadata,
            "pairs": pairs,
            "row_count": len(source_rows),
            "pair_count": len(pair_rows),
        },
        expected_partition=partition,
    )


def _sha256_tensors(values: Mapping[str, torch.Tensor]) -> str:
    digest = hashlib.sha256()
    for name in sorted(values):
        tensor = torch.as_tensor(values[name]).detach().cpu().contiguous()
        encoded = name.encode("ascii")
        digest.update(len(encoded).to_bytes(4, "big"))
        digest.update(encoded)
        dtype = str(tensor.dtype).encode("ascii")
        digest.update(len(dtype).to_bytes(4, "big"))
        digest.update(dtype)
        shape = json.dumps(list(tensor.shape), separators=(",", ":")).encode("ascii")
        digest.update(len(shape).to_bytes(4, "big"))
        digest.update(shape)
        data = tensor.numpy().tobytes(order="C")
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def successor_corpus_identity(corpus: Mapping[str, Any]) -> dict[str, str]:
    partition = str(corpus.get("partition", ""))
    normalized = validate_successor_corpus(corpus, expected_partition=partition)
    return {
        "source_tensor_sha256": _sha256_tensors(normalized["tensors"]),
        "pair_tensor_sha256": _sha256_tensors(normalized["pairs"]),
        "metadata_sha256": hashlib.sha256(
            _canonical_json_bytes({"rows": normalized["metadata"]})
        ).hexdigest(),
    }


def _partition_summary(
    corpus: Mapping[str, Any],
    *,
    registered_profiles: int,
    initialized_profiles: int,
    source_decisions: int,
    skip_reasons: Counter[str],
    exclusion_reasons: Counter[str],
    initialization_failures: Counter[str],
) -> dict[str, Any]:
    advantages = corpus["pairs"]["advantages"].float()
    dispositions = {
        prefix: Counter(
            DISPOSITION_NAMES[int(value)]
            for value in corpus["pairs"][f"{prefix}_dispositions"].tolist()
        )
        for prefix in ("guard", "candidate")
    }
    return {
        "registered_profile_count": registered_profiles,
        "initialized_profile_count": initialized_profiles,
        "source_decision_count": source_decisions,
        "retained_state_count": int(corpus["row_count"]),
        "pair_count": int(corpus["pair_count"]),
        "positive_state_count": int(corpus["tensors"]["positive"].sum()),
        "pair_advantage": {
            "minimum": float(advantages.min()),
            "mean": float(advantages.mean()),
            "maximum": float(advantages.max()),
        },
        "mean_pairs_per_state": int(corpus["pair_count"]) / int(corpus["row_count"]),
        "guard_disposition_counts": dict(sorted(dispositions["guard"].items())),
        "candidate_disposition_counts": dict(
            sorted(dispositions["candidate"].items())
        ),
        "skip_reason_counts": dict(sorted(skip_reasons.items())),
        "exclusion_reason_counts": dict(sorted(exclusion_reasons.items())),
        "initialization_failure_counts": dict(
            sorted(initialization_failures.items())
        ),
        "identity": successor_corpus_identity(corpus),
    }


def _balanced_source_view(
    corpus: Mapping[str, Any], *, partition: str
) -> dict[str, Any]:
    normalized = validate_successor_corpus(
        corpus, expected_partition=str(corpus["partition"])
    )
    return balanced.validate_corpus(
        {
            "partition": partition,
            "tensors": {
                name: normalized["tensors"][name] for name in balanced.TENSOR_NAMES
            },
            "metadata": normalized["metadata"],
            "row_count": normalized["row_count"],
        },
        expected_partition=partition,
    )


def _combined_training_source_view(
    fit: Mapping[str, Any], calibration: Mapping[str, Any]
) -> dict[str, Any]:
    left = _balanced_source_view(fit, partition="train")
    right = _balanced_source_view(calibration, partition="train")
    return balanced.validate_corpus(
        {
            "partition": "train",
            "tensors": {
                name: torch.cat((left["tensors"][name], right["tensors"][name]))
                for name in balanced.TENSOR_NAMES
            },
            "metadata": left["metadata"] + right["metadata"],
            "row_count": left["row_count"] + right["row_count"],
        },
        expected_partition="train",
    )


def _corpus_support_evidence(
    corpora: Mapping[str, Mapping[str, Any]], paths: Mapping[str, Path]
) -> dict[str, Any]:
    real, real_evidence = load_real_replay_bindings(
        (
            RealReplayBinding(
                label="r14",
                path=paths["real_r14_replay"],
                sha256=FIXED_INPUTS["real_r14_replay"]["sha256"],
            ),
            RealReplayBinding(
                label="r15",
                path=paths["real_r15_replay"],
                sha256=FIXED_INPUTS["real_r15_replay"]["sha256"],
            ),
        )
    )
    train = _combined_training_source_view(corpora["fit"], corpora["calibration"])
    fresh = _balanced_source_view(corpora["fresh"], partition="evaluation")
    train_context = balanced.derive_context_weights(real, train)
    fresh_context = balanced.derive_context_weights(real, fresh)
    integrity = balanced._integrity_conditions(train, fresh)
    late_rows = sum(23 <= int(row["floor"]) <= 34 for row in fresh["metadata"])
    gate = balanced.apply_support_gates(
        train_metrics=train_context["metrics"],
        evaluation_metrics=fresh_context["metrics"],
        evaluation_late_floor_rows=late_rows,
        integrity_conditions=integrity,
    )
    return {
        "real_replay": real_evidence,
        "train": train_context["metrics"],
        "fresh": fresh_context["metrics"],
        "evaluation_late_floor_rows": late_rows,
        "integrity": integrity,
        "gate": gate,
    }


def collect_successor_partition(
    native_module: ModuleType,
    *,
    id_mapper: Any,
    trainer: Any,
    partition: str,
    seeds: Sequence[int],
    recipe: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    source_rows: list[dict[str, Any]] = []
    pair_rows: list[dict[str, Any]] = []
    skip_reasons: Counter[str] = Counter()
    exclusion_reasons: Counter[str] = Counter()
    initialization_failures: Counter[str] = Counter()
    decisions = 0
    initialized = 0
    continuation = _continuation_selector(
        trainer,
        id_mapper,
        max_actions_per_turn=int(recipe["max_actions_per_turn"]),
    )
    was_training = trainer.online_network.training
    trainer.online_network.eval()
    try:
        for seed in seeds:
            for battle_index in recipe["battle_indices"]:
                try:
                    environment = NativeCombatEnvironment.reset(
                        native_module,
                        int(seed),
                        int(recipe["ascension"]),
                        int(battle_index),
                    )
                except Exception as exc:
                    initialization_failures[initialization_failure_reason(exc)] += 1
                    continue
                initialized += 1
                actions_since_end_turn = 0
                retained_for_profile = 0
                for _ in range(int(recipe["max_source_decisions"])):
                    status = environment.status()
                    disposition, reason = successor_disposition(status)
                    if disposition != "supported":
                        if disposition == "exclude":
                            skip_reasons[f"source_unsupported:{reason}"] += 1
                        break
                    before = environment.snapshot()
                    mapped = environment.mapped_state(id_mapper=id_mapper)
                    source_state = _tensor_state(mapped)
                    legal = environment.legal_actions()
                    raw = _policy_action(
                        trainer,
                        mapped,
                        legal,
                        actions_since_end_turn=actions_since_end_turn,
                        max_actions_per_turn=int(recipe["max_actions_per_turn"]),
                    )
                    guarded, guard_telemetry = apply_deployment_guard_proxy(
                        environment,
                        raw,
                        legal,
                        before,
                        mode=GREEDY_NATIVE_REWARD_DEPLOYMENT_GUARD_PROXY,
                        policy_selected=(
                            actions_since_end_turn < int(recipe["max_actions_per_turn"])
                        ),
                    )
                    decisions += 1
                    if raw["kind"] != "end_turn":
                        skip_reasons["parent_not_end_turn"] += 1
                    elif not guard_telemetry["guard_proxy_replacement_count"]:
                        skip_reasons["guard_not_replaced"] += 1
                    else:
                        canonical, representatives = canonicalize_actions(legal, mapped)
                        guard_index = representatives[int(guarded["rl_action_index"])]
                        if len(canonical) <= 1:
                            skip_reasons["no_distinct_alternative"] += 1
                        elif len(canonical) > int(recipe["max_canonical_actions"]):
                            skip_reasons["too_many_canonical_actions"] += 1
                        else:
                            results = {
                                int(action["rl_action_index"]): rollout_successor_branch(
                                    environment,
                                    action,
                                    source_actions_since_end_turn=actions_since_end_turn,
                                    continuation_selector=continuation,
                                    continuation_decisions=int(
                                        recipe["continuation_decisions"]
                                    ),
                                    discount=float(recipe["return_discount"]),
                                    map_successor=lambda branch_environment: (
                                        branch_environment.mapped_state(
                                            id_mapper=id_mapper
                                        )
                                    ),
                                )
                                for action in canonical
                            }
                            guard_result = results[guard_index]
                            if not guard_result.complete:
                                exclusion_reasons[
                                    f"guard:{guard_result.exclusion_reason}"
                                ] += 1
                            else:
                                complete_candidates = [
                                    result
                                    for action_index, result in sorted(results.items())
                                    if action_index != guard_index
                                    and action_index < SUPPORTED_ACTION_STOP
                                    and result.complete
                                ]
                                for action_index, result in sorted(results.items()):
                                    if action_index >= SUPPORTED_ACTION_STOP:
                                        exclusion_reasons[
                                            "candidate:unsupported_action_family"
                                        ] += 1
                                    elif action_index != guard_index and not result.complete:
                                        exclusion_reasons[
                                            f"candidate:{result.exclusion_reason}"
                                        ] += 1
                                if not complete_candidates:
                                    skip_reasons["no_complete_candidate"] += 1
                                else:
                                    all_complete = [guard_result, *complete_candidates]
                                    target = max(
                                        all_complete,
                                        key=lambda result: (
                                            result.total_return,
                                            -result.action_index,
                                        ),
                                    )
                                    target_action = next(
                                        action
                                        for action in canonical
                                        if int(action["rl_action_index"])
                                        == target.action_index
                                    )
                                    target_advantage = float(
                                        target.total_return - guard_result.total_return
                                    )
                                    source_index = len(source_rows)
                                    branch_returns = {
                                        str(result.action_index): float(result.total_return)
                                        for result in all_complete
                                    }
                                    source_rows.append(
                                        {
                                            **source_state,
                                            "seed": int(seed),
                                            "battle_index": int(battle_index),
                                            "act": int(before["state"]["act"]),
                                            "floor": int(before["state"]["floor"]),
                                            "turn": int(before["state"]["turn"]),
                                            "encounter": encounter_from_snapshot(before),
                                            "raw_parent_action_index": int(
                                                raw["rl_action_index"]
                                            ),
                                            "guard_action_index": guard_index,
                                            "target_action_index": target.action_index,
                                            "target_identity": canonical_action_identity(
                                                canonical_action_key(target_action, mapped)
                                            ),
                                            "guard_return": float(
                                                guard_result.total_return
                                            ),
                                            "target_return": float(target.total_return),
                                            "target_advantage": target_advantage,
                                            "positive": target_advantage
                                            >= float(
                                                recipe["positive_advantage_margin"]
                                            ),
                                            "branch_count": len(all_complete),
                                            "branch_returns": branch_returns,
                                        }
                                    )
                                    guard_successor = _successor_or_zero(
                                        guard_result, source_state
                                    )
                                    for candidate in complete_candidates:
                                        pair_rows.append(
                                            {
                                                "source_row": source_index,
                                                "candidate_action_index": (
                                                    candidate.action_index
                                                ),
                                                "guard_returns": float(
                                                    guard_result.total_return
                                                ),
                                                "candidate_returns": float(
                                                    candidate.total_return
                                                ),
                                                "advantages": float(
                                                    candidate.total_return
                                                    - guard_result.total_return
                                                ),
                                                "guard_immediate_rewards": float(
                                                    guard_result.immediate_reward
                                                ),
                                                "candidate_immediate_rewards": float(
                                                    candidate.immediate_reward
                                                ),
                                                "guard_dispositions": int(
                                                    guard_result.disposition
                                                ),
                                                "candidate_dispositions": int(
                                                    candidate.disposition
                                                ),
                                                "guard_successor": guard_successor,
                                                "candidate_successor": (
                                                    _successor_or_zero(
                                                        candidate, source_state
                                                    )
                                                ),
                                            }
                                        )
                                    retained_for_profile += 1
                    if retained_for_profile >= int(recipe["max_states_per_profile"]):
                        break
                    environment.step(str(guarded["action_id"]))
                    actions_since_end_turn = (
                        0
                        if guarded["kind"] == "end_turn"
                        else actions_since_end_turn + 1
                    )
    finally:
        trainer.online_network.train(was_training)
    corpus = _stack_successor_partition(
        source_rows, pair_rows, partition=partition
    )
    summary = _partition_summary(
        corpus,
        registered_profiles=len(seeds) * len(recipe["battle_indices"]),
        initialized_profiles=initialized,
        source_decisions=decisions,
        skip_reasons=skip_reasons,
        exclusion_reasons=exclusion_reasons,
        initialization_failures=initialization_failures,
    )
    return corpus, summary


def _validated_source_commit(source_commit: str) -> str:
    source_commit = _validate_commit(source_commit)
    current = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="ascii",
    ).stdout.strip()
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", source_commit, current],
        cwd=REPO_ROOT,
        check=False,
    ).returncode:
        raise ValueError("successor source commit is not an ancestor")
    for relative in SOURCE_SNAPSHOT_PATHS:
        if subprocess.run(
            ["git", "diff", "--quiet", source_commit, "--", relative],
            cwd=REPO_ROOT,
            check=False,
        ).returncode:
            raise ValueError(f"successor source changed: {relative}")
    return source_commit


def _validate_bound_inputs(registration: Mapping[str, Any]) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for name, binding in registration["inputs"].items():
        path = Path(binding["path"]).resolve()
        if not path.is_file() or sha256_file(path) != binding["sha256"]:
            raise ValueError(f"successor corpus input binding differs: {name}")
        paths[name] = path
    return paths


def _write_registration(*, smoke: bool, source_commit: str) -> dict[str, Any]:
    registration_path = SMOKE_REGISTRATION_PATH if smoke else CORPUS_REGISTRATION_PATH
    preflight_path = SMOKE_PREFLIGHT_PATH if smoke else CORPUS_PREFLIGHT_PATH
    output = SMOKE_OUTPUT_DIR if smoke else CORPUS_OUTPUT_DIR
    if registration_path.exists() or preflight_path.exists() or output.exists():
        raise ValueError("successor registration or output already exists")
    registration = build_corpus_registration(
        source_commit,
        experiment_id=SMOKE_EXPERIMENT_ID if smoke else CORPUS_EXPERIMENT_ID,
        output_dir=output,
        smoke=smoke,
    )
    validate_corpus_registration(registration, smoke=smoke)
    _validated_source_commit(source_commit)
    paths = _validate_bound_inputs(registration)
    preflight = {
        "schema_version": "combat-rl-action-relative-successor-corpus-preflight-v1",
        "experiment_id": registration["experiment_id"],
        "source_commit": source_commit,
        "registration_sha256": hashlib.sha256(
            _canonical_json_bytes(registration)
        ).hexdigest(),
        "validated_inputs": {
            name: {"path": str(path), "sha256": registration["inputs"][name]["sha256"]}
            for name, path in sorted(paths.items())
        },
        "output_absent": True,
        "source_only": True,
        "authority": copy.deepcopy(CORPUS_AUTHORITY),
    }
    registration_path.write_bytes(_canonical_json_bytes(registration))
    preflight_path.write_bytes(_canonical_json_bytes(preflight))
    return {"registration": registration, "preflight": preflight}


def _load_registration(path: Path) -> tuple[dict[str, Any], bool]:
    value = json.loads(path.read_text(encoding="ascii"))
    smoke = value.get("smoke") is True
    expected_path = SMOKE_REGISTRATION_PATH if smoke else CORPUS_REGISTRATION_PATH
    if path.resolve() != expected_path.resolve():
        raise ValueError("successor registration path differs")
    return validate_corpus_registration(value, smoke=smoke), smoke


def _render_corpus_summary(report: Mapping[str, Any]) -> str:
    lines = [
        "# Action-relative first-successor corpus",
        "",
        f"- Experiment: `{report['experiment_id']}`",
        f"- Smoke: `{str(report['smoke']).lower()}`",
    ]
    for name, summary in report["partitions"].items():
        lines.append(
            f"- {name}: `{summary['retained_state_count']}` states, "
            f"`{summary['pair_count']}` candidate pairs"
        )
    lines.extend(
        (
            "",
            "This is development-only simulator evidence. It grants no gameplay,",
            "training, qualification, promotion, or production authority.",
            "",
        )
    )
    return "\n".join(lines)


def run_registered_corpus(registration_path: Path) -> dict[str, Any]:
    if Path(sys.executable).resolve() != EXPECTED_INTERPRETER.resolve():
        raise ValueError("successor corpus must use the registered Windows interpreter")
    if not bool(sys.flags.isolated):
        raise ValueError("successor corpus must run in isolated mode")
    registration, smoke = _load_registration(registration_path)
    _validated_source_commit(registration["source_commit"])
    paths = _validate_bound_inputs(registration)
    output = Path(registration["output_dir"]).resolve()
    staging = output.with_name(f".{output.name}.staging")
    started_path = REPORTS_ROOT / f".{registration['experiment_id']}.started.json"
    if output.exists() or staging.exists() or started_path.exists():
        raise ValueError("successor corpus output, staging, or receipt already exists")
    started_at = time.time()
    started = {
        "schema_version": "combat-rl-action-relative-successor-corpus-started-v1",
        "experiment_id": registration["experiment_id"],
        "source_commit": registration["source_commit"],
        "started_unix": started_at,
    }
    started_path.write_bytes(_canonical_json_bytes(started))

    native_module = load_native_module(paths["native_module"])
    mapper = build_id_mapper(paths["items_json"])
    initial = load_initial_checkpoint(
        paths["parent_checkpoint"],
        expected_sha256=registration["inputs"]["parent_checkpoint"]["sha256"],
    )
    trainer = create_fresh_trainer(
        mapper, seed=2026082901, batch_size=128, learning_starts=128
    )
    parent_state, initialization = initialize_trainer(trainer, initial)
    recipe = registration["recipe"]
    corpora: dict[str, dict[str, Any]] = {}
    summaries: dict[str, dict[str, Any]] = {}
    for partition, bounds in recipe["partitions"].items():
        seeds = tuple(range(int(bounds[0]), int(bounds[1]) + 1))
        corpus, summary = collect_successor_partition(
            native_module,
            id_mapper=mapper,
            trainer=trainer,
            partition=partition,
            seeds=seeds,
            recipe=recipe,
        )
        corpora[partition] = corpus
        summaries[partition] = summary
    if smoke:
        repeated, _ = collect_successor_partition(
            native_module,
            id_mapper=mapper,
            trainer=trainer,
            partition="smoke",
            seeds=tuple(
                range(
                    int(recipe["partitions"]["smoke"][0]),
                    int(recipe["partitions"]["smoke"][1]) + 1,
                )
            ),
            recipe=recipe,
        )
        deterministic = successor_corpus_identity(repeated) == successor_corpus_identity(
            corpora["smoke"]
        )
        if not deterministic:
            raise RuntimeError("successor smoke corpus is not deterministic")
    else:
        validate_partition_seed_contract(
            {name: corpora[name]["metadata"] for name in FIXED_COHORT}
        )
        deterministic = None
    support = None if smoke else _corpus_support_evidence(corpora, paths)
    provenance = collect_provenance(
        repo_root=REPO_ROOT,
        simulator_repo=SIMULATOR_REPO,
        module_path=paths["native_module"],
        native_module=native_module,
    )
    report = {
        "schema_version": "combat-rl-action-relative-successor-corpus-report-v1",
        "experiment_id": registration["experiment_id"],
        "source_commit": registration["source_commit"],
        "smoke": smoke,
        "recipe": copy.deepcopy(recipe),
        "inputs": copy.deepcopy(registration["inputs"]),
        "source_files": copy.deepcopy(registration["source_files"]),
        "initialization": initialization,
        "parent_parameter_sha256": parameter_sha256(parent_state),
        "partitions": summaries,
        "smoke_repeat_identity_exact": deterministic,
        "context_support": support,
        "provenance": provenance,
        "started_receipt": started,
        "elapsed_seconds_before_publication": time.time() - started_at,
        "authority": copy.deepcopy(CORPUS_AUTHORITY),
    }
    if report["elapsed_seconds_before_publication"] > float(recipe["max_wall_seconds"]):
        raise RuntimeError("successor corpus wall-time limit exceeded")
    staging.mkdir(parents=True, exist_ok=False)
    try:
        for partition, corpus in corpora.items():
            torch.save(corpus, staging / f"{partition}_corpus.pt")
            loaded = torch.load(
                staging / f"{partition}_corpus.pt",
                map_location="cpu",
                weights_only=False,
            )
            if successor_corpus_identity(loaded) != successor_corpus_identity(corpus):
                raise RuntimeError("successor corpus roundtrip identity differs")
        (staging / "report.json").write_bytes(_canonical_json_bytes(report))
        (staging / "summary.md").write_text(
            _render_corpus_summary(report), encoding="ascii", newline="\n"
        )
        shutil.copyfile(registration_path, staging / "registration.json")
        preflight_path = SMOKE_PREFLIGHT_PATH if smoke else CORPUS_PREFLIGHT_PATH
        shutil.copyfile(preflight_path, staging / "preflight.json")
        shutil.copyfile(started_path, staging / "started_receipt.json")
        stored = sum(path.stat().st_size for path in staging.rglob("*") if path.is_file())
        if stored > int(recipe["max_stored_bytes"]):
            raise RuntimeError("successor corpus stored-byte limit exceeded")
        artifacts = {
            path.relative_to(staging).as_posix(): {
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
            for path in sorted(staging.rglob("*"))
            if path.is_file() and path.name != "manifest.json"
        }
        manifest = {
            "schema_version": "combat-rl-action-relative-successor-corpus-manifest-v1",
            "experiment_id": registration["experiment_id"],
            "source_commit": registration["source_commit"],
            "artifacts": artifacts,
        }
        (staging / "manifest.json").write_bytes(_canonical_json_bytes(manifest))
        os.replace(staging, output)
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    return report


FIXED_ABLATION_RECIPE = {
    **copy.deepcopy(WEIGHTED_FIT_RECIPE),
    "architecture": "paired_current_state_control_vs_first_successor_delta",
    "include_item_semantics": True,
    "fit_partition": "fit",
    "calibration_partition": "calibration",
    "fresh_partition": "fresh",
    "successor_feature": (
        "candidate_minus_guard_frozen_latent_plus_immediate_reward_delta_"
        "plus_dispositions"
    ),
}

FIT_AUTHORITY = {
    "cpu_model_fitting": True,
    "fresh_evaluation": True,
    "native_loading": False,
    "lightspeed_policy_gate": False,
    "gameplay": False,
    "communication_mod": False,
    "production_checkpoint_loading": False,
    "production_checkpoint_writing": False,
    "qualification": False,
    "promotion": False,
}


def _pair_base_features(
    extractor: ActionRelativeSelectiveClassifier,
    corpus: Mapping[str, Any],
) -> torch.Tensor:
    pairs = corpus["pairs"]
    source_rows = pairs["source_rows"].long()
    tensors = corpus["tensors"]
    with torch.no_grad():
        features = extractor._candidate_features(
            continuous=tensors["continuous"][source_rows],
            card_ids=tensors["card_ids"][source_rows],
            potion_ids=tensors["potion_ids"][source_rows],
            relic_ids=tensors["relic_ids"][source_rows],
            action_masks=tensors["action_masks"][source_rows],
            guard_actions=tensors["guard_actions"][source_rows],
            candidate_actions=pairs["candidate_actions"],
        )
    return features.detach().cpu()


def _pair_successor_latents(
    extractor: ActionRelativeSelectiveClassifier,
    pairs: Mapping[str, torch.Tensor],
    *,
    prefix: str,
) -> torch.Tensor:
    with torch.no_grad():
        latent = extractor._parent_latent(
            pairs[f"{prefix}_successor_continuous"],
            pairs[f"{prefix}_successor_card_ids"],
            pairs[f"{prefix}_successor_potion_ids"],
            pairs[f"{prefix}_successor_relic_ids"],
        )
    return mask_terminal_latents(latent.detach().cpu(), pairs[f"{prefix}_dispositions"])


def build_ablation_feature_matrices(
    extractor: ActionRelativeSelectiveClassifier,
    corpus: Mapping[str, Any],
) -> dict[str, torch.Tensor]:
    normalized = validate_successor_corpus(
        corpus, expected_partition=str(corpus["partition"])
    )
    base = _pair_base_features(extractor, normalized)
    pairs = normalized["pairs"]
    candidate_latent = _pair_successor_latents(
        extractor, pairs, prefix="candidate"
    )
    guard_latent = _pair_successor_latents(extractor, pairs, prefix="guard")
    successor = compose_successor_delta_features(
        base,
        candidate_latent=candidate_latent,
        guard_latent=guard_latent,
        candidate_rewards=pairs["candidate_immediate_rewards"],
        guard_rewards=pairs["guard_immediate_rewards"],
        candidate_dispositions=pairs["candidate_dispositions"],
        guard_dispositions=pairs["guard_dispositions"],
    )
    return {
        "control": base,
        "successor": successor,
        "labels": classify_advantages(pairs["advantages"]),
    }


def _new_head(input_dim: int, *, seed: int) -> torch.nn.Sequential:
    if input_dim <= 0:
        raise ValueError("successor ablation input dimension is invalid")
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed)
        return torch.nn.Sequential(
            torch.nn.Linear(input_dim, int(FIXED_ABLATION_RECIPE["hidden_dim"])),
            torch.nn.ReLU(),
            torch.nn.Linear(int(FIXED_ABLATION_RECIPE["hidden_dim"]), 3),
        )


def _evidence(logits: torch.Tensor) -> torch.Tensor:
    return logits[:, BENEFICIAL_CLASS] - torch.logsumexp(
        logits[:, :BENEFICIAL_CLASS], dim=1
    )


def _fit_head(
    features: torch.Tensor,
    labels: torch.Tensor,
    *,
    class_plan: torch.Tensor,
    ranking_pairs: torch.Tensor,
    ranking_plan: torch.Tensor,
) -> tuple[torch.nn.Sequential, dict[str, Any]]:
    head = _new_head(
        int(features.shape[1]),
        seed=int(FIXED_ABLATION_RECIPE["model_initialization_seed"]),
    )
    optimizer = torch.optim.Adam(
        head.parameters(), lr=float(FIXED_ABLATION_RECIPE["learning_rate"])
    )
    losses: list[float] = []
    head.train()
    for update in range(int(FIXED_ABLATION_RECIPE["updates"])):
        class_indices = class_plan[update].reshape(-1)
        classification_loss = F.cross_entropy(
            head(features[class_indices]), labels[class_indices]
        )
        selected_pairs = ranking_pairs[ranking_plan[update]]
        ranking_logits = head(features[selected_pairs.reshape(-1)]).reshape(-1, 2, 3)
        ranking_evidence = _evidence(ranking_logits.reshape(-1, 3)).reshape(-1, 2)
        ranking_loss = F.softplus(
            -(ranking_evidence[:, 0] - ranking_evidence[:, 1])
        ).mean()
        loss = classification_loss + float(
            FIXED_ABLATION_RECIPE["ranking_loss_weight"]
        ) * ranking_loss
        if not bool(torch.isfinite(loss)):
            raise RuntimeError("successor ablation objective became non-finite")
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        optimizer.step()
        losses.append(float(loss.detach()))
    head.eval()
    return head, {
        "input_dim": int(features.shape[1]),
        "update_count": int(FIXED_ABLATION_RECIPE["updates"]),
        "loss_first": losses[0],
        "loss_last": losses[-1],
        "loss_minimum": min(losses),
        "loss_maximum": max(losses),
        "loss_mean": statistics.fmean(losses),
        "state_dict_sha256": state_dict_sha256(head.state_dict()),
    }


def _weighted_sampling_plan(
    corpus: Mapping[str, Any], state_weights: torch.Tensor
) -> dict[str, Any]:
    pairs = corpus["pairs"]
    labels = classify_advantages(pairs["advantages"])
    pair_weights = derive_pair_sampling_weights(
        pairs["source_rows"], state_weights, labels=labels
    )
    class_plan = build_weighted_class_balanced_sample_plan(
        labels,
        pair_weights["normalized_by_class"],
        updates=int(FIXED_ABLATION_RECIPE["updates"]),
        samples_per_class=int(
            FIXED_ABLATION_RECIPE["samples_per_class_per_update"]
        ),
        seed=int(FIXED_ABLATION_RECIPE["sampling_seed"]),
    )
    ranking_pairs = build_within_state_ranking_pairs(pairs["source_rows"], labels)
    ranking_weights = derive_ranking_sampling_weights(
        ranking_pairs, pairs["source_rows"], state_weights
    )
    ranking_plan = build_weighted_replacement_sample_plan(
        ranking_weights,
        updates=int(FIXED_ABLATION_RECIPE["updates"]),
        samples_per_update=int(FIXED_ABLATION_RECIPE["ranking_pairs_per_update"]),
        seed=int(FIXED_ABLATION_RECIPE["ranking_sampling_seed"]),
    )
    return {
        "labels": labels,
        "pair_weights": pair_weights,
        "class_plan": class_plan,
        "ranking_pairs": ranking_pairs,
        "ranking_weights": ranking_weights,
        "ranking_plan": ranking_plan,
        "sha256": _sha256_tensors(
            {
                "class_plan": class_plan,
                "pair_weights": pair_weights["raw"],
                "pair_weights_normalized": pair_weights["normalized_by_class"],
                "ranking_pairs": ranking_pairs,
                "ranking_weights": ranking_weights,
                "ranking_plan": ranking_plan,
            }
        ),
    }


def _calibrate_head(
    head: torch.nn.Module,
    features: torch.Tensor,
    labels: torch.Tensor,
    pair_weights: torch.Tensor,
) -> dict[str, Any]:
    with torch.no_grad():
        evidence = _evidence(head(features)).cpu()
    negative = labels.ne(BENEFICIAL_CLASS)
    threshold, details = weighted_higher_quantile(
        evidence[negative],
        pair_weights[negative],
        quantile=float(FIXED_ABLATION_RECIPE["calibration_quantile"]),
    )
    return {
        "selection_threshold": threshold,
        "pair_count": int(evidence.numel()),
        "negative_count": int(negative.sum()),
        "evidence_sha256": _sha256_tensors({"evidence": evidence}),
        **details,
    }


def evaluate_ablation_head(
    head: torch.nn.Module,
    features: torch.Tensor,
    corpus: Mapping[str, Any],
    state_weights: torch.Tensor,
    *,
    selection_threshold: float,
) -> dict[str, Any]:
    normalized = validate_successor_corpus(
        corpus, expected_partition=str(corpus["partition"])
    )
    pairs = normalized["pairs"]
    labels = classify_advantages(pairs["advantages"])
    with torch.no_grad():
        logits = head(features)
        evidence = _evidence(logits).cpu()
    if int(evidence.numel()) != int(normalized["pair_count"]):
        raise ValueError("successor evaluation pair rows differ")
    forbidden = frozenset(
        int(value) for value in FIXED_ABLATION_RECIPE["forbidden_action_indices"]
    )
    source_count = int(normalized["row_count"])
    selected_true = torch.zeros(source_count)
    best_with_guard = torch.zeros(source_count)
    intervention_rows = torch.zeros(source_count, dtype=torch.bool)
    selected_actions = normalized["tensors"]["guard_actions"].clone()
    selected_pair_indices = torch.full((source_count,), -1, dtype=torch.long)
    for source_index in range(source_count):
        member = pairs["source_rows"].eq(source_index).nonzero(as_tuple=False).reshape(-1)
        allowed = torch.tensor(
            [
                int(pairs["candidate_actions"][index]) not in forbidden
                for index in member.tolist()
            ],
            dtype=torch.bool,
        )
        member = member[allowed]
        if not int(member.numel()):
            continue
        local = evidence[member]
        best_offset = int(local.argmax())
        pair_index = int(member[best_offset])
        best_with_guard[source_index] = max(
            0.0, float(pairs["advantages"][member].max())
        )
        if float(evidence[pair_index]) >= float(selection_threshold):
            intervention_rows[source_index] = True
            selected_pair_indices[source_index] = pair_index
            selected_true[source_index] = pairs["advantages"][pair_index]
            selected_actions[source_index] = pairs["candidate_actions"][pair_index]
    intervention_count = int(intervention_rows.sum())
    selected_interventions = selected_true[intervention_rows]
    source_masks = normalized["tensors"]["action_masks"]
    source_rows = torch.arange(source_count)
    illegal = int((~source_masks[source_rows, selected_actions]).sum())
    forbidden_count = sum(
        int(selected_actions[intervention_rows].eq(action).sum()) for action in forbidden
    )
    severe_count = int(
        selected_interventions.lt(
            float(FIXED_OFFLINE_GATES["severe_harm_floor"])
        ).sum()
    )
    predictions = logits.argmax(dim=1).cpu()
    confusion = torch.zeros((3, 3), dtype=torch.long)
    for truth, predicted in zip(labels.tolist(), predictions.tolist()):
        confusion[truth, predicted] += 1
    raw = {
        "row_count": source_count,
        "pair_count": int(normalized["pair_count"]),
        "classification": {
            "accuracy": float(predictions.eq(labels).float().mean()),
            "confusion_matrix_truth_rows": confusion.tolist(),
            "class_support": {
                name: int(labels.eq(class_index).sum())
                for class_index, name in enumerate(CLASS_NAMES)
            },
        },
        "ranking": {
            "mean_policy_regret": float((best_with_guard - selected_true).mean())
        },
        "selection": {
            "selection_threshold": float(selection_threshold),
            "intervention_count": intervention_count,
            "intervention_share": intervention_count / max(source_count, 1),
            "intervention_precision": (
                float(selected_interventions.ge(0.5).float().mean())
                if intervention_count
                else 0.0
            ),
            "mean_selected_true_advantage": float(selected_true.mean()),
            "mean_intervention_true_advantage": (
                float(selected_interventions.mean()) if intervention_count else 0.0
            ),
            "severe_harm_count": severe_count,
            "illegal_action_count": illegal,
            "forbidden_action_selection_count": forbidden_count,
        },
        "evidence": {
            "minimum": float(evidence.min()),
            "mean": float(evidence.mean()),
            "maximum": float(evidence.max()),
            "sha256": _sha256_tensors({"evidence": evidence}),
        },
    }
    weighted = weighted_policy_metrics(
        selected_true=selected_true,
        best_with_guard=best_with_guard,
        intervention_rows=intervention_rows,
        state_weights=state_weights,
        beneficial_floor=float(
            FIXED_ABLATION_RECIPE["beneficial_lower_inclusive"]
        ),
    )
    return {
        "raw": raw,
        "weighted": weighted,
        "selection": {
            "actions": selected_actions,
            "pair_indices": selected_pair_indices,
            "intervention_rows": intervention_rows,
        },
    }


def _fit_input_bindings() -> dict[str, dict[str, str]]:
    paths = {
        "items_json": FIXED_INPUTS["items_json"]["path"],
        "parent_checkpoint": FIXED_INPUTS["parent_checkpoint"]["path"],
        "real_r14_replay": FIXED_INPUTS["real_r14_replay"]["path"],
        "real_r15_replay": FIXED_INPUTS["real_r15_replay"]["path"],
        "fit_corpus": CORPUS_OUTPUT_DIR / "fit_corpus.pt",
        "calibration_corpus": CORPUS_OUTPUT_DIR / "calibration_corpus.pt",
        "fresh_corpus": CORPUS_OUTPUT_DIR / "fresh_corpus.pt",
        "corpus_report": CORPUS_OUTPUT_DIR / "report.json",
        "corpus_manifest": CORPUS_OUTPUT_DIR / "manifest.json",
        "corpus_registration": CORPUS_OUTPUT_DIR / "registration.json",
    }
    result: dict[str, dict[str, str]] = {}
    for name, path in paths.items():
        resolved = Path(path).resolve()
        if not resolved.is_file():
            raise ValueError(f"successor ablation input is unavailable: {name}")
        result[name] = {"path": str(resolved), "sha256": sha256_file(resolved)}
    return result


def build_fit_registration(
    source_commit: str, *, inputs: Mapping[str, Mapping[str, str]]
) -> dict[str, Any]:
    source_commit = _validate_commit(source_commit)
    expected_names = {
        "items_json",
        "parent_checkpoint",
        "real_r14_replay",
        "real_r15_replay",
        "fit_corpus",
        "calibration_corpus",
        "fresh_corpus",
        "corpus_report",
        "corpus_manifest",
        "corpus_registration",
    }
    if not isinstance(inputs, Mapping) or set(inputs) != expected_names:
        raise ValueError("successor ablation registration inputs differ")
    normalized_inputs: dict[str, dict[str, str]] = {}
    for name, binding in sorted(inputs.items()):
        if not isinstance(binding, Mapping) or set(binding) != {"path", "sha256"}:
            raise ValueError("successor ablation registration input differs")
        path = Path(str(binding["path"]))
        if not path.is_absolute():
            raise ValueError("successor ablation registration input path differs")
        normalized_inputs[name] = {
            "path": str(path.resolve()),
            "sha256": _validate_sha256(binding["sha256"], label=name),
        }
    return {
        "schema_version": FIT_REGISTRATION_SCHEMA,
        "experiment_id": FIT_EXPERIMENT_ID,
        "source_commit": source_commit,
        "runner": {
            "path": str(Path(__file__).resolve()),
            "sha256": sha256_file(Path(__file__)),
        },
        "source_files": _source_file_hashes(),
        "inputs": normalized_inputs,
        "recipe": copy.deepcopy(FIXED_ABLATION_RECIPE),
        "offline_gates": copy.deepcopy(FIXED_OFFLINE_GATES),
        "output_dir": str(FIT_OUTPUT_DIR.resolve()),
        "authority": copy.deepcopy(FIT_AUTHORITY),
    }


def validate_fit_registration(registration: Mapping[str, Any]) -> dict[str, Any]:
    expected = build_fit_registration(
        str(registration.get("source_commit", "")), inputs=registration.get("inputs", {})
    )
    if dict(registration) != expected:
        raise ValueError("successor ablation registration payload differs")
    return copy.deepcopy(expected)


def _write_fit_registration(source_commit: str) -> dict[str, Any]:
    if FIT_REGISTRATION_PATH.exists() or FIT_PREFLIGHT_PATH.exists() or FIT_OUTPUT_DIR.exists():
        raise ValueError("successor ablation registration or output already exists")
    inputs = _fit_input_bindings()
    report = json.loads(Path(inputs["corpus_report"]["path"]).read_text(encoding="ascii"))
    support = report.get("context_support")
    if not isinstance(support, Mapping) or support.get("gate", {}).get("passed") is not True:
        raise ValueError("successor ablation corpus support did not pass")
    registration = build_fit_registration(source_commit, inputs=inputs)
    validate_fit_registration(registration)
    _validated_source_commit(source_commit)
    preflight = {
        "schema_version": "combat-rl-action-relative-successor-delta-ablation-preflight-v1",
        "experiment_id": FIT_EXPERIMENT_ID,
        "source_commit": source_commit,
        "registration_sha256": hashlib.sha256(
            _canonical_json_bytes(registration)
        ).hexdigest(),
        "context_support_decision": support["gate"]["decision"],
        "output_absent": True,
        "fresh_tensor_access": False,
        "authority": copy.deepcopy(FIT_AUTHORITY),
    }
    FIT_REGISTRATION_PATH.write_bytes(_canonical_json_bytes(registration))
    FIT_PREFLIGHT_PATH.write_bytes(_canonical_json_bytes(preflight))
    return {"registration": registration, "preflight": preflight}


def _validated_fit_paths(
    registration: Mapping[str, Any], *, deferred_fresh: bool
) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for name, binding in registration["inputs"].items():
        path = Path(binding["path"]).resolve()
        if deferred_fresh and name == "fresh_corpus":
            paths[name] = path
            continue
        if not path.is_file() or sha256_file(path) != binding["sha256"]:
            raise ValueError(f"successor ablation input binding differs: {name}")
        paths[name] = path
    return paths


def _load_successor_corpus(path: Path, *, partition: str) -> dict[str, Any]:
    value = torch.load(path, map_location="cpu", weights_only=False)
    return validate_successor_corpus(value, expected_partition=partition)


def _head_artifact(
    head: torch.nn.Module,
    *,
    arm: str,
    threshold: float,
    input_dim: int,
) -> dict[str, Any]:
    state = {name: value.detach().cpu() for name, value in head.state_dict().items()}
    return {
        "arm": arm,
        "input_dim": input_dim,
        "hidden_dim": int(FIXED_ABLATION_RECIPE["hidden_dim"]),
        "selection_threshold": float(threshold),
        "state_dict": state,
        "state_dict_sha256": state_dict_sha256(state),
        "production_compatible": False,
    }


def _restore_head(artifact: Mapping[str, Any]) -> torch.nn.Module:
    head = _new_head(
        int(artifact["input_dim"]),
        seed=int(FIXED_ABLATION_RECIPE["model_initialization_seed"]),
    )
    state = {name: torch.as_tensor(value).detach().cpu() for name, value in artifact["state_dict"].items()}
    if state_dict_sha256(state) != artifact["state_dict_sha256"]:
        raise ValueError("successor ablation artifact state differs")
    head.load_state_dict(state, strict=True)
    head.eval()
    return head


def _render_fit_summary(report: Mapping[str, Any]) -> str:
    successor = report["fresh_evaluation"]["successor"]
    return "\n".join(
        (
            "# Action-relative successor-delta ablation",
            "",
            f"- Decision: `{report['decision']}`",
            f"- Hard gate: `{str(report['hard_gate']['all_conditions_passed']).lower()}`",
            f"- Descriptive signal: `{str(report['representation_signal']['all_conditions_passed']).lower()}`",
            f"- Successor interventions: `{successor['raw']['selection']['intervention_count']}`",
            f"- Successor severe harms: `{successor['raw']['selection']['severe_harm_count']}`",
            f"- Successor weighted precision: `{successor['weighted']['intervention_precision']:.6f}`",
            f"- Successor weighted mean advantage: `{successor['weighted']['mean_selected_true_advantage']:.6f}`",
            "",
            "This is development-only offline evidence. It grants no gameplay,",
            "qualification, promotion, or production authority.",
            "",
        )
    )


def run_registered_fit(registration_path: Path) -> dict[str, Any]:
    if Path(sys.executable).resolve() != EXPECTED_INTERPRETER.resolve():
        raise ValueError("successor ablation must use the registered Windows interpreter")
    if not bool(sys.flags.isolated):
        raise ValueError("successor ablation must run in isolated mode")
    if registration_path.resolve() != FIT_REGISTRATION_PATH.resolve():
        raise ValueError("successor ablation registration path differs")
    registration = validate_fit_registration(
        json.loads(registration_path.read_text(encoding="ascii"))
    )
    _validated_source_commit(registration["source_commit"])
    paths = _validated_fit_paths(registration, deferred_fresh=True)
    staging = FIT_OUTPUT_DIR.with_name(f".{FIT_OUTPUT_DIR.name}.staging")
    started_path = REPORTS_ROOT / f".{FIT_EXPERIMENT_ID}.started.json"
    if FIT_OUTPUT_DIR.exists() or staging.exists() or started_path.exists():
        raise ValueError("successor ablation output, staging, or receipt already exists")
    corpus_report = json.loads(paths["corpus_report"].read_text(encoding="ascii"))
    support = corpus_report.get("context_support")
    if not isinstance(support, Mapping) or support.get("gate", {}).get("passed") is not True:
        raise ValueError("successor ablation context support differs")
    started = {
        "schema_version": "combat-rl-action-relative-successor-delta-ablation-started-v1",
        "experiment_id": FIT_EXPERIMENT_ID,
        "source_commit": registration["source_commit"],
        "started_unix": time.time(),
        "fresh_tensor_access": False,
    }
    started_path.write_bytes(_canonical_json_bytes(started))
    real, real_evidence = load_real_replay_bindings(
        (
            RealReplayBinding("r14", paths["real_r14_replay"], registration["inputs"]["real_r14_replay"]["sha256"]),
            RealReplayBinding("r15", paths["real_r15_replay"], registration["inputs"]["real_r15_replay"]["sha256"]),
        )
    )
    fit_corpus = _load_successor_corpus(paths["fit_corpus"], partition="fit")
    calibration_corpus = _load_successor_corpus(
        paths["calibration_corpus"], partition="calibration"
    )
    fit_context = balanced.derive_context_weights(real, fit_corpus)
    calibration_context = balanced.derive_context_weights(real, calibration_corpus)
    fit_plan = _weighted_sampling_plan(fit_corpus, fit_context["weights"])

    mapper = build_id_mapper(paths["items_json"])
    initial = load_initial_checkpoint(
        paths["parent_checkpoint"],
        expected_sha256=registration["inputs"]["parent_checkpoint"]["sha256"],
    )
    trainer = create_fresh_trainer(
        mapper,
        seed=int(FIXED_ABLATION_RECIPE["model_initialization_seed"]),
        batch_size=int(FIXED_ABLATION_RECIPE["samples_per_class_per_update"]) * 3,
        learning_starts=64,
    )
    parent_state, initialization = initialize_trainer(trainer, initial)
    parent = trainer.online_network
    parent.eval()
    metadata = _trainer_metadata(trainer)
    extractor = ActionRelativeSelectiveClassifier(
        parent,
        metadata,
        ActionRelativeSelectiveConfig(
            hidden_dim=int(FIXED_ABLATION_RECIPE["hidden_dim"]),
            include_item_semantics=True,
        ),
        selection_threshold=0.0,
    )
    extractor.eval()
    parent_before = state_dict_sha256(parent.state_dict())
    fit_features = build_ablation_feature_matrices(extractor, fit_corpus)
    heads: dict[str, torch.nn.Module] = {}
    fit_reports: dict[str, dict[str, Any]] = {}
    for arm in ("control", "successor"):
        head, fit_report = _fit_head(
            fit_features[arm],
            fit_plan["labels"],
            class_plan=fit_plan["class_plan"],
            ranking_pairs=fit_plan["ranking_pairs"],
            ranking_plan=fit_plan["ranking_plan"],
        )
        heads[arm] = head
        fit_reports[arm] = {
            **fit_report,
            "feature_sha256": _sha256_tensors({"features": fit_features[arm]}),
            "sampling_plan_sha256": fit_plan["sha256"],
        }
    calibration_features = build_ablation_feature_matrices(
        extractor, calibration_corpus
    )
    calibration_pair_weights = derive_pair_sampling_weights(
        calibration_corpus["pairs"]["source_rows"],
        calibration_context["weights"],
        labels=calibration_features["labels"],
    )["raw"]
    calibrations = {
        arm: _calibrate_head(
            heads[arm],
            calibration_features[arm],
            calibration_features["labels"],
            calibration_pair_weights,
        )
        for arm in ("control", "successor")
    }
    parent_after = state_dict_sha256(parent.state_dict())
    if parent_before != parent_after:
        raise RuntimeError("successor ablation changed the frozen parent")
    boundary = FreshAccessBoundary()
    for arm in ("control", "successor"):
        boundary.freeze_arm(
            arm,
            fit_reports[arm]["state_dict_sha256"],
            calibrations[arm]["selection_threshold"],
        )
    fresh_access = boundary.authorize_fresh_access()
    paths = _validated_fit_paths(registration, deferred_fresh=False)
    fresh_corpus = _load_successor_corpus(paths["fresh_corpus"], partition="fresh")
    fresh_context = balanced.derive_context_weights(real, fresh_corpus)
    fresh_features = build_ablation_feature_matrices(extractor, fresh_corpus)
    fresh_evaluation = {
        arm: evaluate_ablation_head(
            heads[arm],
            fresh_features[arm],
            fresh_corpus,
            fresh_context["weights"],
            selection_threshold=calibrations[arm]["selection_threshold"],
        )
        for arm in ("control", "successor")
    }
    hard_gate = apply_weighted_offline_gates(
        fresh_evaluation["successor"]["raw"],
        fresh_evaluation["successor"]["weighted"],
    )
    signal = compare_representation_signal(
        fresh_evaluation["control"], fresh_evaluation["successor"]
    )
    decision = (
        "offline_passed_propose_fresh_lightspeed_gate"
        if hard_gate["all_conditions_passed"]
        else signal["decision"]
    )
    artifacts = {
        arm: _head_artifact(
            heads[arm],
            arm=arm,
            threshold=calibrations[arm]["selection_threshold"],
            input_dim=int(fresh_features[arm].shape[1]),
        )
        for arm in ("control", "successor")
    }
    for arm in ("control", "successor"):
        restored = _restore_head(artifacts[arm])
        with torch.no_grad():
            if not torch.equal(
                heads[arm](fresh_features[arm]), restored(fresh_features[arm])
            ):
                raise RuntimeError("successor ablation artifact roundtrip changed logits")
    serializable_evaluation = {
        arm: {
            "raw": result["raw"],
            "weighted": result["weighted"],
        }
        for arm, result in fresh_evaluation.items()
    }
    report = {
        "schema_version": "combat-rl-action-relative-successor-delta-ablation-report-v1",
        "experiment_id": FIT_EXPERIMENT_ID,
        "source_commit": registration["source_commit"],
        "source_files": registration["source_files"],
        "inputs": registration["inputs"],
        "recipe": copy.deepcopy(FIXED_ABLATION_RECIPE),
        "offline_gates": copy.deepcopy(FIXED_OFFLINE_GATES),
        "corpus_support": support,
        "real_replay": real_evidence,
        "initialization": initialization,
        "parent_parameter_sha256": parameter_sha256(parent_state),
        "parent_state_dict_sha256_before": parent_before,
        "parent_state_dict_sha256_after": parent_after,
        "fit_context": fit_context["metrics"],
        "calibration_context": calibration_context["metrics"],
        "fresh_context": fresh_context["metrics"],
        "sampling_plan_sha256": fit_plan["sha256"],
        "fit": fit_reports,
        "calibration": calibrations,
        "fresh_access": fresh_access,
        "fresh_evaluation": serializable_evaluation,
        "hard_gate": hard_gate,
        "representation_signal": signal,
        "artifact_roundtrip_exact": True,
        "parameter_sweep": False,
        "decision": decision,
        "authority": {
            **copy.deepcopy(FIT_AUTHORITY),
            "lightspeed_policy_gate": bool(hard_gate["all_conditions_passed"]),
        },
    }
    staging.mkdir(parents=True, exist_ok=False)
    try:
        artifact_path = staging / "paired_successor_delta_ablation.pth"
        torch.save(
            {
                "schema_version": "combat-rl-action-relative-successor-delta-artifact-v1",
                "recipe": copy.deepcopy(FIXED_ABLATION_RECIPE),
                "parent_checkpoint_sha256": registration["inputs"]["parent_checkpoint"]["sha256"],
                "sampling_plan_sha256": fit_plan["sha256"],
                "arms": artifacts,
                "production_compatible": False,
            },
            artifact_path,
        )
        report["artifact"] = {
            "path": artifact_path.name,
            "sha256": sha256_file(artifact_path),
            "size_bytes": artifact_path.stat().st_size,
            "production_compatible": False,
        }
        (staging / "report.json").write_bytes(_canonical_json_bytes(report))
        (staging / "summary.md").write_text(
            _render_fit_summary(report), encoding="ascii", newline="\n"
        )
        shutil.copyfile(registration_path, staging / "registration.json")
        shutil.copyfile(FIT_PREFLIGHT_PATH, staging / "preflight.json")
        shutil.copyfile(started_path, staging / "started_receipt.json")
        manifest = {
            "schema_version": "combat-rl-action-relative-successor-delta-ablation-manifest-v1",
            "experiment_id": FIT_EXPERIMENT_ID,
            "source_commit": registration["source_commit"],
            "decision": decision,
            "artifacts": {
                path.relative_to(staging).as_posix(): {
                    "sha256": sha256_file(path),
                    "size_bytes": path.stat().st_size,
                }
                for path in sorted(staging.rglob("*"))
                if path.is_file() and path.name != "manifest.json"
            },
        }
        (staging / "manifest.json").write_bytes(_canonical_json_bytes(manifest))
        os.replace(staging, FIT_OUTPUT_DIR)
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    return report


__all__ = [
    "CORPUS_SCHEMA",
    "CORPUS_KIND",
    "CORPUS_EXPERIMENT_ID",
    "CORPUS_OUTPUT_DIR",
    "DISPOSITION_COUNT",
    "SUPPORTED",
    "TERMINAL_VICTORY",
    "TERMINAL_DEFEAT",
    "TERMINAL_OTHER",
    "FIXED_COHORT",
    "FIXED_CORPUS_RECIPE",
    "SuccessorBranchResult",
    "FreshAccessBoundary",
    "rollout_successor_branch",
    "validate_successor_corpus",
    "validate_partition_seed_contract",
    "mask_terminal_latents",
    "compose_successor_delta_features",
    "compare_representation_signal",
    "build_corpus_registration",
    "validate_corpus_registration",
    "collect_successor_partition",
    "successor_corpus_identity",
    "run_registered_corpus",
    "build_ablation_feature_matrices",
    "evaluate_ablation_head",
    "build_fit_registration",
    "validate_fit_registration",
    "run_registered_fit",
]


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--prepare-corpus-registration", choices=("smoke", "formal")
    )
    group.add_argument("--prepare-fit-registration", action="store_true")
    group.add_argument("--corpus-registration", type=Path)
    group.add_argument("--fit-registration", type=Path)
    parser.add_argument("--source-commit")
    arguments = parser.parse_args()
    if arguments.prepare_corpus_registration:
        if not arguments.source_commit:
            parser.error("--prepare-corpus-registration requires --source-commit")
        result = _write_registration(
            smoke=arguments.prepare_corpus_registration == "smoke",
            source_commit=arguments.source_commit,
        )
    elif arguments.prepare_fit_registration:
        if not arguments.source_commit:
            parser.error("--prepare-fit-registration requires --source-commit")
        result = _write_fit_registration(arguments.source_commit)
    elif arguments.corpus_registration:
        if arguments.source_commit:
            parser.error("--source-commit is only valid while preparing registration")
        result = run_registered_corpus(arguments.corpus_registration)
    else:
        if arguments.source_commit:
            parser.error("--source-commit is only valid while preparing registration")
        result = run_registered_fit(arguments.fit_registration)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
