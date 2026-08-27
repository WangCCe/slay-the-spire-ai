import copy
from dataclasses import replace
import math
import os
from pathlib import Path
import random
import subprocess
import sys
from types import ModuleType, SimpleNamespace

import numpy as np
import torch
import pytest

from analysis_scripts.combat_lightspeed_training_smoke import (
    DISCOUNTED_EPISODE_RETURN_TARGET,
    ENCOUNTER_ENUM_ENCODING,
    ENCOUNTER_ENUM_V1,
    ENCOUNTER_ENUM_V1_SHA256,
    ENCOUNTER_HASH_ALGORITHM,
    ENCOUNTER_PARENT_EQUIVALENCE_TOLERANCE,
    FROZEN_PARENT_GUARDED_EPSILON_BEHAVIOR,
    FROZEN_PARENT_GREEDY_ANCHOR_LABEL,
    FROZEN_PARENT_N_STEP_TARGET,
    GREEDY_NATIVE_REWARD_DEPLOYMENT_GUARD_PROXY,
    GUARD_REPLACEMENT_EXECUTED_ACTION_ANCHOR_LABEL,
    NO_DEPLOYMENT_GUARD_PROXY,
    ONE_STEP_TD_TARGET,
    REPORT_AUTHORITY,
    UNIFORM_NON_END_TURN_BEHAVIOR,
    ReplayTransition,
    SmokeConfig,
    _publish,
    _transition,
    apply_deployment_guard_proxy,
    append_encounter_identity,
    calculate_native_reward,
    collect_transitions,
    create_fresh_trainer,
    encounter_from_snapshot,
    encounter_identity_bucket,
    encounter_parent_equivalence_passes,
    frozen_parent_bootstrap_values,
    initialize_trainer,
    insert_transitions,
    load_initial_checkpoint,
    migrate_parent_for_encounter_identity,
    parameter_delta,
    parameter_sha256,
    paired_evaluation,
    prepare_replay_targets,
    prepare_replay_transitions,
    run_optimizer,
    select_behavior_action,
    select_collection_behavior_action,
    select_profile_transitions,
    successor_disposition,
    unexpected_initialization_failures,
    validate_collection_behavior_prerequisites,
    run_smoke,
)
from analysis_scripts.combat_lightspeed_bridge import (
    NativeCombatEnvironment,
    canonical_json_bytes,
    load_native_module,
)
from spirecomm.ai.rl.checkpoint_io import load_torch_checkpoint, save_torch_checkpoint
from spirecomm.ai.rl.v2.action_space import END_TURN_ACTION
from spirecomm.ai.rl.v2.id_mapping import IdMapper, build_id_mapper


REPO_ROOT = Path(__file__).resolve().parents[1]


def _actions():
    return [
        {"action_id": "play_card:0:1", "available": True, "kind": "play_card", "rl_action_index": 1},
        {"action_id": "play_card:1:1", "available": True, "kind": "play_card", "rl_action_index": 7},
        {"action_id": "end_turn", "available": True, "kind": "end_turn", "rl_action_index": 90},
    ]


def _snapshot(*, monster_hp=10, player_hp=80, energy=3, turn=1, targetable=True):
    return {
        "state": {
            "turn": turn,
            "player": {"current_hp": player_hp, "max_hp": 80, "energy": energy},
            "monsters": [
                {
                    "native_slot": 0,
                    "current_hp": monster_hp,
                    "targetable": targetable,
                    "is_gone": not targetable,
                }
            ],
        }
    }


class _GuardEnvironment:
    def __init__(self, before, successors, selected_action_id=None):
        self.before = copy.deepcopy(before)
        self.successors = copy.deepcopy(successors)
        self.selected_action_id = selected_action_id

    def clone(self):
        return type(self)(self.before, self.successors, self.selected_action_id)

    def step(self, action_id):
        self.selected_action_id = action_id

    def status(self):
        return copy.deepcopy(self.successors[self.selected_action_id]["status"])

    def snapshot(self):
        if self.selected_action_id is None:
            return copy.deepcopy(self.before)
        return copy.deepcopy(self.successors[self.selected_action_id]["snapshot"])


class _FixedActionTrainer:
    def __init__(self, action_index):
        self.action_index = action_index
        self.calls = 0

    def select_action(self, *_args, **_kwargs):
        self.calls += 1
        return self.action_index


def _mapped_state():
    return SimpleNamespace(
        state=SimpleNamespace(
            continuous=np.zeros(1, dtype=np.float32),
            card_ids=np.zeros(1, dtype=np.int64),
            potion_ids=np.zeros(1, dtype=np.int64),
            relic_ids=np.zeros(1, dtype=np.int64),
        ),
        action_mask=np.ones(133, dtype=bool),
    )


def _mapper():
    return IdMapper(
        card_ids={"Strike": 1},
        potion_ids={"Fire Potion": 1},
        relic_ids={"Burning Blood": 1},
        card_tags={"Strike": []},
    )


def test_behavior_action_is_seeded_and_forces_end_turn_at_bound():
    left = select_behavior_action(
        _actions(),
        rng=random.Random(17),
        actions_since_end_turn=0,
        max_actions_per_turn=3,
    )
    right = select_behavior_action(
        _actions(),
        rng=random.Random(17),
        actions_since_end_turn=0,
        max_actions_per_turn=3,
    )
    bounded = select_behavior_action(
        _actions(),
        rng=random.Random(17),
        actions_since_end_turn=3,
        max_actions_per_turn=3,
    )

    assert left == right
    assert left["kind"] == "play_card"
    assert bounded["kind"] == "end_turn"


def test_collection_behavior_defaults_to_existing_uniform_selector():
    config = SmokeConfig(train_seeds=(10,), evaluation_seeds=(20,))
    direct = select_behavior_action(
        _actions(),
        rng=random.Random(17),
        actions_since_end_turn=0,
        max_actions_per_turn=config.max_actions_per_turn,
    )

    selected, telemetry = select_collection_behavior_action(
        _GuardEnvironment(_snapshot(), {}),
        behavior_trainer=None,
        mapped=_mapped_state(),
        legal_actions=_actions(),
        before_snapshot=_snapshot(),
        rng=random.Random(17),
        actions_since_end_turn=0,
        config=config,
    )

    assert config.behavior_policy == UNIFORM_NON_END_TURN_BEHAVIOR
    assert selected == direct
    assert telemetry["uniform_branch_count"] == 1
    assert sum(telemetry.values()) == 1


def test_default_collection_wrapper_preserves_multistep_rng_sequence():
    config = SmokeConfig(
        train_seeds=(10,),
        evaluation_seeds=(20,),
        max_actions_per_turn=3,
    )
    legacy_rng = random.Random(29)
    wrapper_rng = random.Random(29)
    legacy_actions = []
    wrapper_actions = []
    for actions_since_end_turn in (0, 1, 2, 3, 0, 2):
        legacy_actions.append(
            select_behavior_action(
                _actions(),
                rng=legacy_rng,
                actions_since_end_turn=actions_since_end_turn,
                max_actions_per_turn=config.max_actions_per_turn,
            )["action_id"]
        )
        selected, _telemetry = select_collection_behavior_action(
            _GuardEnvironment(_snapshot(), {}),
            behavior_trainer=None,
            mapped=_mapped_state(),
            legal_actions=_actions(),
            before_snapshot=_snapshot(),
            rng=wrapper_rng,
            actions_since_end_turn=actions_since_end_turn,
            config=config,
        )
        wrapper_actions.append(selected["action_id"])

    assert wrapper_actions == legacy_actions
    assert wrapper_rng.getstate() == legacy_rng.getstate()


def test_guarded_parent_collection_stores_post_proxy_action():
    before = _snapshot(monster_hp=10, energy=2)
    successors = {
        "play_card:0:1": {
            "status": {"terminal": False, "supported": True},
            "snapshot": _snapshot(monster_hp=4, energy=1),
        },
        "play_card:1:1": {
            "status": {"terminal": False, "supported": True},
            "snapshot": _snapshot(monster_hp=0, energy=1),
        },
    }
    trainer = _FixedActionTrainer(90)
    config = SmokeConfig(
        train_seeds=(10,),
        evaluation_seeds=(20,),
        behavior_policy=FROZEN_PARENT_GUARDED_EPSILON_BEHAVIOR,
        behavior_epsilon=0.0,
        deployment_guard_proxy=GREEDY_NATIVE_REWARD_DEPLOYMENT_GUARD_PROXY,
    )

    selected, telemetry = select_collection_behavior_action(
        _GuardEnvironment(before, successors),
        behavior_trainer=trainer,
        mapped=_mapped_state(),
        legal_actions=_actions(),
        before_snapshot=before,
        rng=random.Random(17),
        actions_since_end_turn=0,
        config=config,
    )

    assert trainer.calls == 1
    assert selected["action_id"] == "play_card:1:1"
    assert telemetry["parent_branch_count"] == 1
    assert telemetry["raw_policy_end_turn_count"] == 1
    assert telemetry["guard_proxy_replacement_count"] == 1


def test_guarded_collection_exploration_uses_existing_non_end_turn_selector():
    trainer = _FixedActionTrainer(90)
    config = SmokeConfig(
        train_seeds=(10,),
        evaluation_seeds=(20,),
        behavior_policy=FROZEN_PARENT_GUARDED_EPSILON_BEHAVIOR,
        behavior_epsilon=1.0,
        deployment_guard_proxy=GREEDY_NATIVE_REWARD_DEPLOYMENT_GUARD_PROXY,
    )

    selected, telemetry = select_collection_behavior_action(
        _GuardEnvironment(_snapshot(), {}),
        behavior_trainer=trainer,
        mapped=_mapped_state(),
        legal_actions=_actions(),
        before_snapshot=_snapshot(),
        rng=random.Random(17),
        actions_since_end_turn=0,
        config=config,
    )

    assert trainer.calls == 0
    assert selected["kind"] == "play_card"
    assert telemetry["exploration_branch_count"] == 1
    assert telemetry["guard_proxy_replacement_count"] == 0


def test_guarded_collection_forces_end_turn_at_bound_without_proxy():
    trainer = _FixedActionTrainer(1)
    config = SmokeConfig(
        train_seeds=(10,),
        evaluation_seeds=(20,),
        max_actions_per_turn=3,
        behavior_policy=FROZEN_PARENT_GUARDED_EPSILON_BEHAVIOR,
        behavior_epsilon=0.0,
        deployment_guard_proxy=GREEDY_NATIVE_REWARD_DEPLOYMENT_GUARD_PROXY,
    )

    selected, telemetry = select_collection_behavior_action(
        _GuardEnvironment(_snapshot(), {}),
        behavior_trainer=trainer,
        mapped=_mapped_state(),
        legal_actions=_actions(),
        before_snapshot=_snapshot(),
        rng=random.Random(17),
        actions_since_end_turn=3,
        config=config,
    )

    assert trainer.calls == 0
    assert selected["kind"] == "end_turn"
    assert telemetry["forced_end_turn_branch_count"] == 1
    assert telemetry["forced_end_turn_count"] == 1
    assert telemetry["guard_proxy_replacement_count"] == 0


@pytest.mark.parametrize(
    ("epsilon", "expected_branch", "expected_trainer_calls"),
    (
        (0.0, "parent_branch_count", 1),
        (1.0, "exploration_branch_count", 0),
    ),
)
def test_guarded_end_turn_only_state_consumes_draw_below_cap(
    epsilon,
    expected_branch,
    expected_trainer_calls,
):
    trainer = _FixedActionTrainer(90)
    config = SmokeConfig(
        train_seeds=(10,),
        evaluation_seeds=(20,),
        max_actions_per_turn=3,
        behavior_policy=FROZEN_PARENT_GUARDED_EPSILON_BEHAVIOR,
        behavior_epsilon=epsilon,
        deployment_guard_proxy=GREEDY_NATIVE_REWARD_DEPLOYMENT_GUARD_PROXY,
    )
    rng = random.Random(31)
    expected_rng = random.Random(31)
    expected_rng.random()

    selected, telemetry = select_collection_behavior_action(
        _GuardEnvironment(_snapshot(), {}),
        behavior_trainer=trainer,
        mapped=_mapped_state(),
        legal_actions=(_actions()[-1],),
        before_snapshot=_snapshot(),
        rng=rng,
        actions_since_end_turn=0,
        config=config,
    )

    assert selected["kind"] == "end_turn"
    assert trainer.calls == expected_trainer_calls
    assert telemetry[expected_branch] == 1
    assert telemetry["forced_end_turn_branch_count"] == 0
    assert telemetry["forced_end_turn_count"] == 0
    assert rng.getstate() == expected_rng.getstate()


def test_guarded_collection_behavior_validates_mode_epsilon_and_prerequisites():
    base = SmokeConfig(train_seeds=(10,), evaluation_seeds=(20,))
    with pytest.raises(ValueError, match="unknown collection behavior policy"):
        replace(base, behavior_policy="unknown").validate()
    for value in (-0.1, 1.1, float("nan"), float("inf")):
        with pytest.raises(ValueError, match="behavior epsilon"):
            replace(base, behavior_epsilon=value).validate()

    guarded = replace(
        base,
        behavior_policy=FROZEN_PARENT_GUARDED_EPSILON_BEHAVIOR,
        behavior_epsilon=0.1,
        deployment_guard_proxy=GREEDY_NATIVE_REWARD_DEPLOYMENT_GUARD_PROXY,
    )
    guarded.validate()
    with pytest.raises(ValueError, match="warm-start checkpoint"):
        validate_collection_behavior_prerequisites(
            guarded,
            has_initial_checkpoint=False,
        )
    with pytest.raises(ValueError, match="registered deployment guard proxy"):
        validate_collection_behavior_prerequisites(
            replace(guarded, deployment_guard_proxy=NO_DEPLOYMENT_GUARD_PROXY),
            has_initial_checkpoint=True,
        )
    validate_collection_behavior_prerequisites(
        guarded,
        has_initial_checkpoint=True,
    )


def test_proxy_aware_anchor_mode_requires_guarded_anchored_warm_start():
    base = SmokeConfig(train_seeds=(10,), evaluation_seeds=(20,))
    assert base.parent_anchor_label_mode == FROZEN_PARENT_GREEDY_ANCHOR_LABEL
    with pytest.raises(ValueError, match="unknown parent anchor label mode"):
        replace(base, parent_anchor_label_mode="unknown").validate()

    proxy_aware = replace(
        base,
        parent_anchor_label_mode=GUARD_REPLACEMENT_EXECUTED_ACTION_ANCHOR_LABEL,
    )
    with pytest.raises(ValueError, match="guarded-parent behavior"):
        validate_collection_behavior_prerequisites(
            proxy_aware,
            has_initial_checkpoint=True,
        )
    guarded = replace(
        proxy_aware,
        behavior_policy=FROZEN_PARENT_GUARDED_EPSILON_BEHAVIOR,
        deployment_guard_proxy=GREEDY_NATIVE_REWARD_DEPLOYMENT_GUARD_PROXY,
    )
    with pytest.raises(ValueError, match="positive parent policy anchor"):
        validate_collection_behavior_prerequisites(
            guarded,
            has_initial_checkpoint=True,
        )
    validate_collection_behavior_prerequisites(
        replace(guarded, parent_policy_anchor_weight=1.0),
        has_initial_checkpoint=True,
    )


def test_guarded_collector_rechecks_proxy_and_registered_parent_before_reset():
    guarded = SmokeConfig(
        train_seeds=(10,),
        evaluation_seeds=(20,),
        behavior_policy=FROZEN_PARENT_GUARDED_EPSILON_BEHAVIOR,
        behavior_epsilon=0.1,
        deployment_guard_proxy=GREEDY_NATIVE_REWARD_DEPLOYMENT_GUARD_PROXY,
    )
    trainer = create_fresh_trainer(
        _mapper(),
        seed=37,
        batch_size=2,
        learning_starts=2,
    )

    with pytest.raises(ValueError, match="registered deployment guard proxy"):
        collect_transitions(
            ModuleType("unused"),
            id_mapper=_mapper(),
            config=replace(guarded, deployment_guard_proxy=NO_DEPLOYMENT_GUARD_PROXY),
            behavior_trainer=trainer,
            expected_behavior_parent_sha256=parameter_sha256(
                trainer.online_network.state_dict()
            ),
        )
    with pytest.raises(ValueError, match="expected parent hash"):
        collect_transitions(
            ModuleType("unused"),
            id_mapper=_mapper(),
            config=guarded,
            behavior_trainer=trainer,
        )
    with pytest.raises(ValueError, match="does not match registration"):
        collect_transitions(
            ModuleType("unused"),
            id_mapper=_mapper(),
            config=guarded,
            behavior_trainer=trainer,
            expected_behavior_parent_sha256="0" * 64,
        )


def test_training_profiles_are_deterministic_seed_index_product():
    config = SmokeConfig(
        train_seeds=(10, 11),
        evaluation_seeds=(20,),
        battle_indices=(0, 3),
    )
    config.validate()
    assert config.profiles(config.train_seeds) == (
        (10, 0),
        (10, 3),
        (11, 0),
        (11, 3),
    )


def test_deployment_guard_proxy_defaults_to_raw_action_and_validates_mode():
    config = SmokeConfig(train_seeds=(10,), evaluation_seeds=(20,))
    config.validate()
    assert config.deployment_guard_proxy == NO_DEPLOYMENT_GUARD_PROXY

    with pytest.raises(ValueError, match="unknown deployment guard proxy"):
        replace(config, deployment_guard_proxy="unknown").validate()

    raw = _actions()[-1]
    environment = _GuardEnvironment(_snapshot(), {})
    selected, telemetry = apply_deployment_guard_proxy(
        environment,
        raw,
        _actions(),
        _snapshot(),
        mode=NO_DEPLOYMENT_GUARD_PROXY,
    )

    assert selected == raw
    assert telemetry == {
        "raw_policy_end_turn_count": 1,
        "forced_end_turn_count": 0,
        "guard_proxy_eligible_count": 0,
        "guard_proxy_replacement_count": 0,
        "guard_proxy_no_supported_replacement_count": 0,
    }


def test_deployment_guard_proxy_replaces_eligible_end_turn_deterministically():
    before = _snapshot(monster_hp=10, energy=2)
    successors = {
        "play_card:0:1": {
            "status": {"terminal": False, "supported": True},
            "snapshot": _snapshot(monster_hp=4, energy=1),
        },
        "play_card:1:1": {
            "status": {"terminal": False, "supported": True},
            "snapshot": _snapshot(monster_hp=0, energy=1),
        },
    }
    environment = _GuardEnvironment(before, successors)

    selected, telemetry = apply_deployment_guard_proxy(
        environment,
        _actions()[-1],
        _actions(),
        before,
        mode=GREEDY_NATIVE_REWARD_DEPLOYMENT_GUARD_PROXY,
    )

    assert selected["action_id"] == "play_card:1:1"
    assert telemetry["raw_policy_end_turn_count"] == 1
    assert telemetry["guard_proxy_eligible_count"] == 1
    assert telemetry["guard_proxy_replacement_count"] == 1
    assert telemetry["guard_proxy_no_supported_replacement_count"] == 0

    tied = copy.deepcopy(successors)
    tied["play_card:1:1"] = copy.deepcopy(tied["play_card:0:1"])
    selected, _telemetry = apply_deployment_guard_proxy(
        _GuardEnvironment(before, tied),
        _actions()[-1],
        _actions(),
        before,
        mode=GREEDY_NATIVE_REWARD_DEPLOYMENT_GUARD_PROXY,
    )
    assert selected["action_id"] == "play_card:0:1"


@pytest.mark.parametrize(
    ("before", "actions", "policy_selected"),
    (
        (_snapshot(energy=0), _actions(), True),
        (_snapshot(energy=2), (_actions()[-1],), True),
        (_snapshot(energy=2), _actions(), False),
    ),
)
def test_deployment_guard_proxy_preserves_ineligible_end_turn(
    before, actions, policy_selected
):
    selected, telemetry = apply_deployment_guard_proxy(
        _GuardEnvironment(before, {}),
        _actions()[-1],
        actions,
        before,
        mode=GREEDY_NATIVE_REWARD_DEPLOYMENT_GUARD_PROXY,
        policy_selected=policy_selected,
    )

    assert selected["kind"] == "end_turn"
    assert telemetry["guard_proxy_eligible_count"] == 0
    assert telemetry["guard_proxy_replacement_count"] == 0
    assert telemetry["forced_end_turn_count"] == int(not policy_selected)


def test_deployment_guard_proxy_retains_end_turn_without_supported_card_successor():
    before = _snapshot(energy=2)
    successors = {
        action["action_id"]: {
            "status": {
                "terminal": False,
                "supported": False,
                "unsupported_reason": "unsupported_card",
            },
            "snapshot": before,
        }
        for action in _actions()
        if action["kind"] == "play_card"
    }

    selected, telemetry = apply_deployment_guard_proxy(
        _GuardEnvironment(before, successors),
        _actions()[-1],
        _actions(),
        before,
        mode=GREEDY_NATIVE_REWARD_DEPLOYMENT_GUARD_PROXY,
    )

    assert selected["kind"] == "end_turn"
    assert telemetry["guard_proxy_eligible_count"] == 1
    assert telemetry["guard_proxy_replacement_count"] == 0
    assert telemetry["guard_proxy_no_supported_replacement_count"] == 1


def test_parent_policy_constraint_weight_must_be_finite_and_non_negative():
    for value in (-0.1, float("nan"), float("inf")):
        with pytest.raises(ValueError, match="parent policy anchor weight"):
            SmokeConfig(
                train_seeds=(10,),
                evaluation_seeds=(20,),
                parent_policy_anchor_weight=value,
            ).validate()

    with pytest.raises(ValueError, match="replay balance seed"):
        SmokeConfig(
            train_seeds=(10,),
            evaluation_seeds=(20,),
            replay_balance_seed=-1,
        ).validate()

    for value in (-0.1, float("nan"), float("inf")):
        with pytest.raises(ValueError, match="end-turn margin guard weight"):
            SmokeConfig(
                train_seeds=(10,),
                evaluation_seeds=(20,),
                parent_end_turn_margin_guard_weight=value,
            ).validate()

    for value in (-0.1, float("nan"), float("inf")):
        with pytest.raises(ValueError, match="end-turn margin guard cap"):
            SmokeConfig(
                train_seeds=(10,),
                evaluation_seeds=(20,),
                parent_end_turn_margin_guard_cap=value,
            ).validate()

    with pytest.raises(ValueError, match="positive cap"):
        SmokeConfig(
            train_seeds=(10,),
            evaluation_seeds=(20,),
            parent_end_turn_margin_guard_weight=1.0,
            parent_end_turn_margin_guard_cap=0.0,
        ).validate()

    for value in (-0.1, float("nan"), float("inf")):
        with pytest.raises(ValueError, match="card-ranking guard weight"):
            SmokeConfig(
                train_seeds=(10,),
                evaluation_seeds=(20,),
                parent_card_ranking_guard_weight=value,
            ).validate()

    for value in (-0.1, float("nan"), float("inf")):
        with pytest.raises(ValueError, match="card-ranking guard cap"):
            SmokeConfig(
                train_seeds=(10,),
                evaluation_seeds=(20,),
                parent_card_ranking_guard_cap=value,
            ).validate()

    with pytest.raises(ValueError, match="positive cap"):
        SmokeConfig(
            train_seeds=(10,),
            evaluation_seeds=(20,),
            parent_card_ranking_guard_weight=1.0,
            parent_card_ranking_guard_cap=0.0,
        ).validate()

    for value in (-0.1, float("nan"), float("inf")):
        with pytest.raises(ValueError, match="top-action margin guard weight"):
            SmokeConfig(
                train_seeds=(10,),
                evaluation_seeds=(20,),
                parent_top_action_margin_guard_weight=value,
            ).validate()

    for value in (-0.1, float("nan"), float("inf")):
        with pytest.raises(ValueError, match="top-action margin guard cap"):
            SmokeConfig(
                train_seeds=(10,),
                evaluation_seeds=(20,),
                parent_top_action_margin_guard_cap=value,
            ).validate()

    with pytest.raises(ValueError, match="positive cap"):
        SmokeConfig(
            train_seeds=(10,),
            evaluation_seeds=(20,),
            parent_top_action_margin_guard_weight=1.0,
            parent_top_action_margin_guard_cap=0.0,
        ).validate()

    for value in (-1, 1, 1025):
        with pytest.raises(ValueError, match="encounter identity buckets"):
            SmokeConfig(
                train_seeds=(10,),
                evaluation_seeds=(20,),
                encounter_identity_buckets=value,
            ).validate()

    with pytest.raises(ValueError, match="unknown encounter identity encoding"):
        SmokeConfig(
            train_seeds=(10,),
            evaluation_seeds=(20,),
            encounter_identity_encoding="unknown",
        ).validate()
    with pytest.raises(ValueError, match="requires exactly 64 buckets"):
        SmokeConfig(
            train_seeds=(10,),
            evaluation_seeds=(20,),
            encounter_identity_buckets=32,
            encounter_identity_encoding=ENCOUNTER_ENUM_ENCODING,
        ).validate()
    with pytest.raises(ValueError, match="unknown replay target mode"):
        SmokeConfig(
            train_seeds=(10,),
            evaluation_seeds=(20,),
            replay_target_mode="unknown",
        ).validate()
    for value in (0.0, -0.1, 1.1, float("nan"), float("inf")):
        with pytest.raises(ValueError, match="replay return discount"):
            SmokeConfig(
                train_seeds=(10,),
                evaluation_seeds=(20,),
                replay_return_discount=value,
            ).validate()
    with pytest.raises(ValueError, match="require complete trajectories"):
        SmokeConfig(
            train_seeds=(10,),
            evaluation_seeds=(20,),
            replay_target_mode=DISCOUNTED_EPISODE_RETURN_TARGET,
        ).validate()
    with pytest.raises(ValueError, match="require complete trajectories"):
        SmokeConfig(
            train_seeds=(10,),
            evaluation_seeds=(20,),
            replay_target_mode=FROZEN_PARENT_N_STEP_TARGET,
        ).validate()
    for value in (0, -1, 1.5, True):
        with pytest.raises(ValueError, match="replay return horizon"):
            SmokeConfig(
                train_seeds=(10,),
                evaluation_seeds=(20,),
                replay_return_horizon=value,
            ).validate()


def test_encounter_identity_is_deterministic_opt_in_and_one_hot():
    continuous = np.linspace(0.0, 1.0, 328, dtype=np.float32)

    unchanged = append_encounter_identity(
        continuous,
        encounter=None,
        bucket_count=0,
    )
    left = append_encounter_identity(
        continuous,
        encounter="THREE_SENTRIES",
        bucket_count=64,
    )
    right = append_encounter_identity(
        continuous,
        encounter="THREE_SENTRIES",
        bucket_count=64,
    )

    assert np.array_equal(unchanged, continuous)
    assert unchanged is not continuous
    assert left.shape == (392,)
    assert np.array_equal(left, right)
    assert np.array_equal(left[:328], continuous)
    assert left[328:].sum() == pytest.approx(1.0)
    assert left[328 + encounter_identity_bucket("THREE_SENTRIES", 64)] == 1.0


def test_encounter_identity_rejects_missing_snapshot_metadata():
    with pytest.raises(ValueError, match="omits encounter identity"):
        encounter_from_snapshot({"state": {}})
    with pytest.raises(ValueError, match="non-empty string"):
        encounter_identity_bucket("", 64)


def test_collision_free_encounter_vocabulary_matches_lightspeed_enum_contract():
    assert len(ENCOUNTER_ENUM_V1) == 63
    assert len(set(ENCOUNTER_ENUM_V1)) == 63
    assert len(ENCOUNTER_ENUM_V1_SHA256) == 64
    assert encounter_identity_bucket(
        "CULTIST",
        64,
        encoding=ENCOUNTER_ENUM_ENCODING,
    ) == 1
    assert encounter_identity_bucket(
        "THREE_SENTRIES",
        64,
        encoding=ENCOUNTER_ENUM_ENCODING,
    ) == 17
    assert encounter_identity_bucket(
        "MYSTERIOUS_SPHERE_EVENT",
        64,
        encoding=ENCOUNTER_ENUM_ENCODING,
    ) == 63
    assignments = {
        encounter_identity_bucket(name, 64, encoding=ENCOUNTER_ENUM_ENCODING)
        for name in ENCOUNTER_ENUM_V1
    }
    assert assignments == set(range(1, 64))


def test_collision_free_encounter_vocabulary_rejects_unknown_identity():
    with pytest.raises(ValueError, match="unknown enum-v1 encounter identity"):
        encounter_identity_bucket(
            "NOT_A_LIGHTSPEED_ENCOUNTER",
            64,
            encoding=ENCOUNTER_ENUM_ENCODING,
        )
    with pytest.raises(ValueError, match="requires exactly 64 buckets"):
        encounter_identity_bucket(
            "CULTIST",
            32,
            encoding=ENCOUNTER_ENUM_ENCODING,
        )


def _stratum_transition(
    battle_index,
    action,
    *,
    seed=0,
    decision_index=0,
    reward=0.0,
    done=False,
    guard_proxy_replaced=False,
):
    return ReplayTransition(
        battle_index=battle_index,
        continuous=np.zeros(328, dtype=np.float32),
        card_ids=np.zeros(10, dtype=np.int64),
        potion_ids=np.zeros(5, dtype=np.int64),
        relic_ids=np.zeros(40, dtype=np.int64),
        action=action,
        reward=reward,
        next_continuous=np.zeros(328, dtype=np.float32),
        next_card_ids=np.zeros(10, dtype=np.int64),
        next_potion_ids=np.zeros(5, dtype=np.int64),
        next_relic_ids=np.zeros(40, dtype=np.int64),
        done=done,
        action_mask=np.ones(133, dtype=bool),
        next_action_mask=np.ones(133, dtype=bool),
        seed=seed,
        decision_index=decision_index,
        guard_proxy_replaced=guard_proxy_replaced,
    )


def test_guard_replacement_provenance_survives_targets_balancing_and_replay():
    replacement = _stratum_transition(
        0,
        1,
        seed=31,
        decision_index=0,
        reward=1.0,
        done=True,
        guard_proxy_replaced=True,
    )
    ordinary = replace(
        replacement,
        battle_index=3,
        guard_proxy_replaced=False,
    )
    targeted, _target_evidence = prepare_replay_targets(
        (replacement, ordinary),
        mode=DISCOUNTED_EPISODE_RETURN_TARGET,
        discount=0.99,
    )
    prepared, _balance_evidence = prepare_replay_transitions(
        targeted,
        battle_indices=(0, 3),
        stratify=True,
        seed=41,
    )
    trainer = create_fresh_trainer(
        _mapper(),
        seed=42,
        batch_size=2,
        learning_starts=2,
    )

    assert [row.guard_proxy_replaced for row in targeted] == [True, False]
    assert [row.guard_proxy_replaced for row in prepared] == [True, False]
    assert insert_transitions(
        trainer,
        prepared,
        parent_anchor_label_mode=GUARD_REPLACEMENT_EXECUTED_ACTION_ANCHOR_LABEL,
    ) == 2
    assert [row[13] for row in trainer.replay_buffer.buffer] == [True, False]


def test_raw_parent_anchor_mode_ignores_guard_replacement_provenance():
    row = _stratum_transition(0, 1, guard_proxy_replaced=True)
    trainer = create_fresh_trainer(
        _mapper(),
        seed=43,
        batch_size=2,
        learning_starts=2,
    )

    assert insert_transitions(
        trainer,
        (row,),
        parent_anchor_label_mode=FROZEN_PARENT_GREEDY_ANCHOR_LABEL,
    ) == 1
    assert trainer.replay_buffer.buffer[0][13] is False


def test_profile_selection_excludes_entire_incomplete_prefix_when_required():
    rows = [
        _stratum_transition(9, 1, seed=17, decision_index=0),
        _stratum_transition(9, 2, seed=17, decision_index=1),
    ]

    retained, retained_evidence = select_profile_transitions(
        rows,
        completed=False,
        incomplete_reason="decision_bound",
        complete_trajectories_only=False,
    )
    excluded, excluded_evidence = select_profile_transitions(
        rows,
        completed=False,
        incomplete_reason="decision_bound",
        complete_trajectories_only=True,
    )

    assert [id(row) for row in retained] == [id(row) for row in rows]
    assert retained_evidence["excluded"] is False
    assert excluded == []
    assert excluded_evidence == {
        "completed": False,
        "excluded": True,
        "incomplete_reason": "decision_bound",
        "transition_count": 2,
    }


def test_one_step_target_preserves_rows_rewards_and_terminal_flags():
    rows = [
        _stratum_transition(0, 1, seed=21, decision_index=0, reward=1.0),
        _stratum_transition(
            0,
            2,
            seed=21,
            decision_index=1,
            reward=3.0,
            done=True,
        ),
    ]

    prepared, metrics = prepare_replay_targets(
        rows,
        mode=ONE_STEP_TD_TARGET,
        discount=0.99,
    )

    assert [id(row) for row in prepared] == [id(row) for row in rows]
    assert [row.reward for row in prepared] == [1.0, 3.0]
    assert [row.done for row in prepared] == [False, True]
    assert metrics["discount"] is None
    assert metrics["source_transition_identity_sha256"] == metrics[
        "target_transition_identity_sha256"
    ]


def test_discounted_episode_return_is_backward_complete_and_non_bootstrapping():
    rows = [
        _stratum_transition(6, 1, seed=31, decision_index=0, reward=1.0),
        _stratum_transition(6, 2, seed=31, decision_index=1, reward=2.0),
        _stratum_transition(
            6,
            3,
            seed=31,
            decision_index=2,
            reward=3.0,
            done=True,
        ),
    ]

    prepared, metrics = prepare_replay_targets(
        rows,
        mode=DISCOUNTED_EPISODE_RETURN_TARGET,
        discount=0.5,
    )
    _one_step, one_step_metrics = prepare_replay_targets(
        rows,
        mode=ONE_STEP_TD_TARGET,
        discount=0.5,
    )

    assert [row.reward for row in prepared] == pytest.approx([2.75, 3.5, 3.0])
    assert all(row.done for row in prepared)
    assert metrics["source_transition_identity_sha256"] != metrics[
        "target_transition_identity_sha256"
    ]
    assert metrics["source_transition_identity_sha256"] == one_step_metrics[
        "source_transition_identity_sha256"
    ]
    assert metrics["terminal_target_count"] == 3
    assert metrics["source_reward"]["sum"] == pytest.approx(6.0)
    assert metrics["target_reward"]["sum"] == pytest.approx(9.25)


def test_frozen_parent_n_step_target_bootstraps_exact_horizon_and_stops_at_terminal():
    rows = [
        _stratum_transition(6, 1, seed=32, decision_index=0, reward=1.0),
        _stratum_transition(6, 2, seed=32, decision_index=1, reward=2.0),
        _stratum_transition(6, 3, seed=32, decision_index=2, reward=3.0),
        _stratum_transition(
            6,
            4,
            seed=32,
            decision_index=3,
            reward=4.0,
            done=True,
        ),
    ]

    prepared, metrics = prepare_replay_targets(
        rows,
        mode=FROZEN_PARENT_N_STEP_TARGET,
        discount=0.5,
        horizon=2,
        bootstrap_values=(10.0, 20.0, 30.0, 0.0),
        bootstrap_parameter_sha256="a" * 64,
    )

    assert [row.reward for row in prepared] == pytest.approx([7.0, 11.0, 5.0, 4.0])
    assert all(row.done for row in prepared)
    assert metrics["horizon"] == 2
    assert metrics["bootstrap_parameter_sha256"] == "a" * 64
    assert metrics["bootstrap_target_count"] == 2
    assert metrics["bootstrap_value"]["sum"] == pytest.approx(50.0)
    assert metrics["source_transition_identity_sha256"] != metrics[
        "target_transition_identity_sha256"
    ]


def test_frozen_parent_n_step_target_rejects_missing_or_invalid_bootstrap_evidence():
    rows = [
        _stratum_transition(3, 1, seed=33, decision_index=0, reward=1.0),
        _stratum_transition(
            3,
            2,
            seed=33,
            decision_index=1,
            reward=2.0,
            done=True,
        ),
    ]

    with pytest.raises(ValueError, match="positive integer"):
        prepare_replay_targets(
            rows,
            mode=FROZEN_PARENT_N_STEP_TARGET,
            discount=0.99,
            horizon=0,
        )
    with pytest.raises(ValueError, match="one bootstrap value per source row"):
        prepare_replay_targets(
            rows,
            mode=FROZEN_PARENT_N_STEP_TARGET,
            discount=0.99,
            horizon=2,
        )
    with pytest.raises(ValueError, match="lowercase parent parameter SHA-256"):
        prepare_replay_targets(
            rows,
            mode=FROZEN_PARENT_N_STEP_TARGET,
            discount=0.99,
            horizon=2,
            bootstrap_values=(1.0, 0.0),
            bootstrap_parameter_sha256="A" * 64,
        )
    with pytest.raises(ValueError, match="must be finite"):
        prepare_replay_targets(
            rows,
            mode=FROZEN_PARENT_N_STEP_TARGET,
            discount=0.99,
            horizon=2,
            bootstrap_values=(float("nan"), 0.0),
            bootstrap_parameter_sha256="a" * 64,
        )


def test_frozen_parent_bootstrap_values_are_masked_finite_and_restore_mode():
    trainer = create_fresh_trainer(
        _mapper(),
        seed=203,
        batch_size=2,
        learning_starts=2,
    )
    network = trainer.target_network
    nonterminal = _stratum_transition(0, 1, seed=34, decision_index=0)
    terminal = _stratum_transition(0, 2, seed=34, decision_index=1, done=True)
    nonterminal.next_action_mask[5:] = False

    network.eval()
    with torch.no_grad():
        expected = network(
            torch.from_numpy(nonterminal.next_continuous).float(),
            torch.from_numpy(nonterminal.next_card_ids).long(),
            torch.from_numpy(nonterminal.next_potion_ids).long(),
            torch.from_numpy(nonterminal.next_relic_ids).long(),
            torch.from_numpy(nonterminal.next_action_mask),
        ).max().item()
    network.train()
    values, parent_sha256 = frozen_parent_bootstrap_values(
        network,
        (nonterminal, terminal),
        batch_size=1,
    )

    assert values == pytest.approx([expected, 0.0])
    assert parent_sha256 == parameter_sha256(network.state_dict())
    assert network.training is True

    invalid = replace(nonterminal, next_action_mask=np.zeros(133, dtype=bool))
    with pytest.raises(ValueError, match="at least one legal next action"):
        frozen_parent_bootstrap_values(network, (invalid,))


def test_discounted_episode_return_rejects_incomplete_or_noncontiguous_profile():
    incomplete = [
        _stratum_transition(3, 1, seed=41, decision_index=0, reward=1.0),
    ]
    noncontiguous = [
        _stratum_transition(3, 1, seed=42, decision_index=1, reward=1.0, done=True),
    ]

    with pytest.raises(ValueError, match="requires a complete trajectory"):
        prepare_replay_targets(
            incomplete,
            mode=DISCOUNTED_EPISODE_RETURN_TARGET,
            discount=0.99,
        )
    with pytest.raises(ValueError, match="identity is not contiguous"):
        prepare_replay_targets(
            noncontiguous,
            mode=DISCOUNTED_EPISODE_RETURN_TARGET,
            discount=0.99,
        )


def test_default_replay_preparation_preserves_rows_and_counts():
    transitions = [
        _stratum_transition(0, 1),
        _stratum_transition(0, 2),
        _stratum_transition(3, 3),
    ]

    prepared, metrics = prepare_replay_transitions(
        transitions,
        battle_indices=(0, 3),
        stratify=False,
        seed=71,
    )

    assert [id(row) for row in prepared] == [id(row) for row in transitions]
    assert metrics["mode"] == "none"
    assert metrics["source_counts"] == {"0": 2, "3": 1}
    assert metrics["prepared_counts"] == {"0": 2, "3": 1}
    assert metrics["duplicate_counts"] == {"0": 0, "3": 0}


def test_stratified_replay_is_deterministic_balanced_and_retains_sources():
    transitions = [
        _stratum_transition(0, 1),
        _stratum_transition(0, 2),
        _stratum_transition(0, 3),
        _stratum_transition(3, 4),
        _stratum_transition(6, 5),
        _stratum_transition(6, 6),
    ]

    left, metrics = prepare_replay_transitions(
        transitions,
        battle_indices=(0, 3, 6),
        stratify=True,
        seed=73,
    )
    right, right_metrics = prepare_replay_transitions(
        transitions,
        battle_indices=(0, 3, 6),
        stratify=True,
        seed=73,
    )

    assert [row.action for row in left] == [row.action for row in right]
    assert metrics == right_metrics
    assert metrics["mode"] == "battle_index_oversample"
    assert metrics["target_count_per_stratum"] == 3
    assert metrics["prepared_counts"] == {"0": 3, "3": 3, "6": 3}
    assert metrics["duplicate_counts"] == {"0": 0, "3": 2, "6": 1}
    assert all(any(row is prepared for prepared in left) for row in transitions)
    assert [row.battle_index for row in left] == [0, 3, 6] * 3


def test_stratified_replay_rejects_missing_configured_stratum():
    with pytest.raises(ValueError, match="missing battle-index stratum: 9"):
        prepare_replay_transitions(
            [_stratum_transition(0, 1)],
            battle_indices=(0, 9),
            stratify=True,
            seed=79,
        )


def test_expected_later_battle_unreachable_profiles_are_not_integrity_failures():
    assert unexpected_initialization_failures(
        {
            "baseline_loss_before_requested_battle": 3,
            "baseline_run_terminated_before_battle": 1,
        }
    ) == {}
    assert unexpected_initialization_failures(
        {
            "baseline_loss_before_requested_battle": 3,
            "baseline_prior_battle_no_progress": 1,
        }
    ) == {"baseline_prior_battle_no_progress": 1}


def test_paired_evaluation_excludes_matching_unreachable_profiles():
    unreachable = {
        "seed": 10,
        "battle_index": 9,
        "outcome": "initialization_failure",
        "initialization_failure_reason": "baseline_loss_before_requested_battle",
        "player_hp": 0,
        "reward": 0.0,
        "decisions": 0,
    }
    control = {
        "rows": [
            unreachable,
            {
                "seed": 11,
                "battle_index": 9,
                "outcome": "player_loss",
                "player_hp": 0,
                "reward": 5.0,
                "decisions": 7,
            },
        ]
    }
    candidate = {
        "rows": [
            dict(unreachable),
            {
                "seed": 11,
                "battle_index": 9,
                "outcome": "player_victory",
                "player_hp": 12,
                "reward": 15.0,
                "decisions": 6,
            },
        ]
    }

    paired = paired_evaluation(control, candidate)

    assert paired["aggregate"]["profile_count"] == 1
    assert paired["aggregate"]["excluded_initialization_profile_count"] == 1
    assert paired["aggregate"]["excluded_initialization_failure_counts"] == {
        "baseline_loss_before_requested_battle": 1
    }
    assert paired["aggregate"]["mean_player_hp_delta"] == 12.0
    assert paired["aggregate"]["mean_reward_delta"] == 10.0


def test_paired_evaluation_excludes_nonterminal_outcome_pairs():
    control = {
        "rows": [
            {
                "seed": 20,
                "battle_index": 9,
                "outcome": "undecided",
                "player_hp": 20,
                "reward": 9.0,
                "decisions": 100,
            },
            {
                "seed": 21,
                "battle_index": 9,
                "outcome": "player_victory",
                "player_hp": 10,
                "reward": 20.0,
                "decisions": 30,
            },
            {
                "seed": 22,
                "battle_index": 9,
                "outcome": "player_loss",
                "player_hp": 0,
                "reward": -5.0,
                "decisions": 12,
            },
        ]
    }
    candidate = {
        "rows": [
            {
                "seed": 20,
                "battle_index": 9,
                "outcome": "player_loss",
                "player_hp": 0,
                "reward": -4.0,
                "decisions": 15,
            },
            {
                "seed": 21,
                "battle_index": 9,
                "outcome": "undecided",
                "player_hp": 30,
                "reward": 15.0,
                "decisions": 100,
            },
            {
                "seed": 22,
                "battle_index": 9,
                "outcome": "player_victory",
                "player_hp": 8,
                "reward": 7.0,
                "decisions": 9,
            },
        ]
    }

    paired = paired_evaluation(control, candidate)

    assert paired["aggregate"]["profile_count"] == 1
    assert paired["aggregate"]["excluded_nonterminal_profile_count"] == 2
    assert paired["aggregate"]["excluded_nonterminal_outcome_pair_counts"] == {
        "control=player_victory,candidate=undecided": 1,
        "control=undecided,candidate=player_loss": 1,
    }
    assert paired["excluded_nonterminal_rows"] == [
        {
            "seed": 20,
            "battle_index": 9,
            "control_outcome": "undecided",
            "candidate_outcome": "player_loss",
        },
        {
            "seed": 21,
            "battle_index": 9,
            "control_outcome": "player_victory",
            "candidate_outcome": "undecided",
        },
    ]
    assert paired["aggregate"]["mean_player_hp_delta"] == 8.0
    assert paired["aggregate"]["mean_reward_delta"] == 12.0
    assert paired["aggregate"]["candidate_only_victories"] == 1
    assert paired["aggregate"]["control_only_victories"] == 0


def test_native_reward_uses_explicit_production_compatible_subset():
    reward = calculate_native_reward(
        _snapshot(),
        _snapshot(monster_hp=0, player_hp=75, turn=2, targetable=False),
        action_kind="end_turn",
        outcome="player_victory",
    )

    assert reward["damage_dealt"] == 10
    assert reward["kills"] == 1
    assert reward["hp_lost"] == 5
    assert reward["all_lethal"] is True
    assert reward["turn_ended"] is True
    assert reward["total"] == 27.325


def test_unsupported_successor_is_excluded_not_terminal():
    assert successor_disposition(
        {"supported": False, "terminal": False, "unsupported_reason": "unsupported_input_state:CARD_SELECT"}
    ) == ("exclude", "unsupported_input_state:CARD_SELECT")
    assert successor_disposition(
        {"supported": False, "terminal": True, "outcome": "player_victory"}
    ) == ("terminal", "player_victory")


def test_fresh_cpu_trainer_updates_parameters_without_production_checkpoint():
    trainer = create_fresh_trainer(
        _mapper(),
        seed=23,
        batch_size=2,
        learning_starts=2,
    )
    initial = copy.deepcopy(trainer.online_network.state_dict())
    state = np.zeros(328, dtype=np.float32)
    card_ids = np.zeros(10, dtype=np.int64)
    potion_ids = np.zeros(5, dtype=np.int64)
    relic_ids = np.zeros(40, dtype=np.int64)
    mask = np.zeros(133, dtype=bool)
    mask[[1, 90]] = True
    next_mask = mask.copy()

    for action, reward in ((1, 1.0), (90, -0.05)):
        assert trainer.store_transition(
            state,
            card_ids,
            potion_ids,
            relic_ids,
            action,
            reward,
            state,
            card_ids,
            potion_ids,
            relic_ids,
            False,
            action_mask=mask,
            next_action_mask=next_mask,
        )
    trainer.target_update_freq = 10_000_000
    loss = trainer.train_step()
    delta = parameter_delta(initial, trainer.online_network.state_dict())

    assert loss is not None and np.isfinite(loss)
    assert delta["l2"] > 0.0
    assert parameter_sha256(initial) != parameter_sha256(trainer.online_network.state_dict())
    assert REPORT_AUTHORITY["simulator_fitting"] is True
    assert all(
        not value
        for key, value in REPORT_AUTHORITY.items()
        if key != "simulator_fitting"
    )


def _write_simulator_checkpoint(path, state_dict, **overrides):
    checkpoint = {
        "checkpoint_schema_version": 0,
        "checkpoint_kind": "simulator_training_smoke",
        "source_type": "sts_lightspeed_native_combat",
        "production_compatible": False,
        "online_network_state_dict": state_dict,
        "metadata": {
            "source_binding": {
                "candidate_parameter_sha256": parameter_sha256(state_dict)
            }
        },
    }
    checkpoint.update(overrides)
    save_torch_checkpoint(checkpoint, str(path))


def test_simulator_checkpoint_warm_starts_online_target_and_control(tmp_path):
    parent = create_fresh_trainer(_mapper(), seed=41, batch_size=2, learning_starts=2)
    with torch.no_grad():
        for parameter in parent.online_network.parameters():
            parameter.add_(0.125)
    parent_state = copy.deepcopy(parent.online_network.state_dict())
    path = tmp_path / "parent.pth"
    _write_simulator_checkpoint(path, parent_state)

    binding = load_initial_checkpoint(path, expected_sha256=None)
    trainer = create_fresh_trainer(_mapper(), seed=99, batch_size=2, learning_starts=2)
    control, record = initialize_trainer(trainer, binding)

    assert record["mode"] == "warm_start"
    assert record["parameter_sha256"] == parameter_sha256(parent_state)
    assert parameter_sha256(control) == parameter_sha256(parent_state)
    assert parameter_sha256(trainer.online_network.state_dict()) == parameter_sha256(
        parent_state
    )
    assert parameter_sha256(trainer.target_network.state_dict()) == parameter_sha256(
        parent_state
    )
    assert trainer.parent_policy_anchor_network is None
    assert trainer.parent_end_turn_margin_guard_weight == 0.0
    assert trainer.parent_end_turn_margin_guard_cap == pytest.approx(0.1)
    assert trainer.parent_card_ranking_guard_weight == 0.0
    assert trainer.parent_card_ranking_guard_cap == pytest.approx(0.1)
    assert trainer.parent_top_action_margin_guard_weight == 0.0
    assert trainer.parent_top_action_margin_guard_cap == pytest.approx(0.1)


def test_encounter_parent_migration_inserts_zero_columns_and_preserves_policy(tmp_path):
    parent = create_fresh_trainer(_mapper(), seed=141, batch_size=2, learning_starts=2)
    parent_state = copy.deepcopy(parent.online_network.state_dict())
    path = tmp_path / "parent.pth"
    _write_simulator_checkpoint(path, parent_state)
    target = create_fresh_trainer(
        _mapper(),
        seed=142,
        batch_size=2,
        learning_starts=2,
        continuous_dim=392,
        parent_policy_anchor_weight=1.0,
    )

    migrated = migrate_parent_for_encounter_identity(
        parent_state,
        target.online_network.state_dict(),
        bucket_count=64,
    )
    first_weight = migrated["hidden_layers.0.weight"]
    assert torch.count_nonzero(first_weight[:, 328:392]).item() == 0
    assert torch.equal(
        first_weight[:, :328],
        parent_state["hidden_layers.0.weight"][:, :328],
    )
    assert torch.equal(
        first_weight[:, 392:],
        parent_state["hidden_layers.0.weight"][:, 328:],
    )

    control, record = initialize_trainer(
        target,
        load_initial_checkpoint(path, expected_sha256=None),
        encounter_identity_buckets=64,
    )

    migration = record["encounter_identity_migration"]
    assert record["mode"] == "warm_start_encounter_expansion"
    assert migration["hash_algorithm"] == ENCOUNTER_HASH_ALGORITHM
    assert migration["inserted_column_max_abs"] == 0.0
    assert migration["equivalence"]["passed"] is True
    assert migration["equivalence"]["action_mismatch_count"] == 0
    assert migration["equivalence"]["max_abs_q_delta"] <= 1e-6
    assert parameter_sha256(control) == record["parameter_sha256"]
    assert record["source_parameter_sha256"] == parameter_sha256(parent_state)
    assert parameter_sha256(
        target.parent_policy_anchor_network.state_dict()
    ) == record["parameter_sha256"]


@pytest.mark.parametrize(
    ("max_abs_q_delta", "action_mismatch_count", "expected"),
    (
        (7.62939453125e-6, 0, True),
        (1.0000001e-5, 0, False),
        (0.0, 1, False),
        (float("nan"), 0, False),
    ),
)
def test_encounter_parent_equivalence_uses_float32_boundary_and_exact_actions(
    max_abs_q_delta,
    action_mismatch_count,
    expected,
):
    assert ENCOUNTER_PARENT_EQUIVALENCE_TOLERANCE == pytest.approx(1e-5)
    assert (
        encounter_parent_equivalence_passes(
            max_abs_q_delta=max_abs_q_delta,
            action_mismatch_count=action_mismatch_count,
        )
        is expected
    )


def test_encounter_identity_requires_compatible_warm_start(tmp_path):
    target = create_fresh_trainer(
        _mapper(),
        seed=143,
        batch_size=2,
        learning_starts=2,
        continuous_dim=392,
    )
    with pytest.raises(ValueError, match="requires a warm-start"):
        initialize_trainer(target, None, encounter_identity_buckets=64)

    path = tmp_path / "invalid-parent.pth"
    _write_simulator_checkpoint(path, {"wrong": torch.zeros(1)})
    with pytest.raises(ValueError, match="keys are incompatible"):
        initialize_trainer(
            target,
            load_initial_checkpoint(path, expected_sha256=None),
            encounter_identity_buckets=64,
        )


def test_positive_parent_policy_constraint_freezes_loaded_parent(tmp_path):
    parent = create_fresh_trainer(_mapper(), seed=42, batch_size=2, learning_starts=2)
    parent_state = copy.deepcopy(parent.online_network.state_dict())
    path = tmp_path / "parent.pth"
    _write_simulator_checkpoint(path, parent_state)
    binding = load_initial_checkpoint(path, expected_sha256=None)
    trainer = create_fresh_trainer(
        _mapper(),
        seed=100,
        batch_size=2,
        learning_starts=2,
        parent_policy_anchor_weight=1.0,
    )

    control, record = initialize_trainer(trainer, binding)

    assert record["parent_policy_anchor_weight"] == pytest.approx(1.0)
    assert parameter_sha256(control) == parameter_sha256(parent_state)
    assert parameter_sha256(
        trainer.parent_policy_anchor_network.state_dict()
    ) == parameter_sha256(parent_state)
    assert all(
        not parameter.requires_grad
        for parameter in trainer.parent_policy_anchor_network.parameters()
    )


def test_positive_parent_policy_constraint_requires_warm_start():
    trainer = create_fresh_trainer(
        _mapper(),
        seed=44,
        batch_size=2,
        learning_starts=2,
        parent_policy_anchor_weight=1.0,
    )

    with pytest.raises(ValueError, match="requires a warm-start checkpoint"):
        initialize_trainer(trainer, None)


def test_positive_parent_end_turn_margin_guard_requires_and_freezes_warm_start(tmp_path):
    without_parent = create_fresh_trainer(
        _mapper(),
        seed=144,
        batch_size=2,
        learning_starts=2,
        parent_end_turn_margin_guard_weight=1.0,
        parent_end_turn_margin_guard_cap=0.1,
    )
    with pytest.raises(ValueError, match="requires a warm-start checkpoint"):
        initialize_trainer(without_parent, None)

    parent = create_fresh_trainer(_mapper(), seed=145, batch_size=2, learning_starts=2)
    path = tmp_path / "parent-margin-guard.pth"
    _write_simulator_checkpoint(path, parent.online_network.state_dict())
    guarded = create_fresh_trainer(
        _mapper(),
        seed=146,
        batch_size=2,
        learning_starts=2,
        parent_end_turn_margin_guard_weight=1.0,
        parent_end_turn_margin_guard_cap=0.1,
    )

    _control, record = initialize_trainer(
        guarded,
        load_initial_checkpoint(path, expected_sha256=None),
    )

    assert record["parent_end_turn_margin_guard_weight"] == pytest.approx(1.0)
    assert record["parent_end_turn_margin_guard_cap"] == pytest.approx(0.1)
    assert guarded.parent_policy_anchor_network is not None
    assert all(
        not parameter.requires_grad
        for parameter in guarded.parent_policy_anchor_network.parameters()
    )


def test_positive_parent_card_ranking_guard_requires_and_freezes_warm_start(tmp_path):
    without_parent = create_fresh_trainer(
        _mapper(),
        seed=149,
        batch_size=2,
        learning_starts=2,
        parent_card_ranking_guard_weight=1.0,
        parent_card_ranking_guard_cap=0.1,
    )
    with pytest.raises(ValueError, match="requires a warm-start checkpoint"):
        initialize_trainer(without_parent, None)

    parent = create_fresh_trainer(_mapper(), seed=150, batch_size=2, learning_starts=2)
    path = tmp_path / "parent-card-ranking-guard.pth"
    _write_simulator_checkpoint(path, parent.online_network.state_dict())
    guarded = create_fresh_trainer(
        _mapper(),
        seed=151,
        batch_size=2,
        learning_starts=2,
        parent_card_ranking_guard_weight=1.0,
        parent_card_ranking_guard_cap=0.1,
    )

    _control, record = initialize_trainer(
        guarded,
        load_initial_checkpoint(path, expected_sha256=None),
    )

    assert record["parent_card_ranking_guard_weight"] == pytest.approx(1.0)
    assert record["parent_card_ranking_guard_cap"] == pytest.approx(0.1)
    assert guarded.parent_policy_anchor_network is not None
    assert all(
        not parameter.requires_grad
        for parameter in guarded.parent_policy_anchor_network.parameters()
    )


def test_positive_parent_top_action_margin_guard_requires_warm_start(tmp_path):
    without_parent = create_fresh_trainer(
        _mapper(),
        seed=154,
        batch_size=2,
        learning_starts=2,
        parent_top_action_margin_guard_weight=1.0,
        parent_top_action_margin_guard_cap=0.1,
    )
    with pytest.raises(ValueError, match="requires a warm-start checkpoint"):
        initialize_trainer(without_parent, None)

    parent = create_fresh_trainer(_mapper(), seed=155, batch_size=2, learning_starts=2)
    path = tmp_path / "parent-top-action-margin-guard.pth"
    _write_simulator_checkpoint(path, parent.online_network.state_dict())
    guarded = create_fresh_trainer(
        _mapper(),
        seed=156,
        batch_size=2,
        learning_starts=2,
        parent_top_action_margin_guard_weight=1.0,
        parent_top_action_margin_guard_cap=0.1,
    )

    _control, record = initialize_trainer(
        guarded,
        load_initial_checkpoint(path, expected_sha256=None),
    )

    assert record["parent_top_action_margin_guard_weight"] == pytest.approx(1.0)
    assert record["parent_top_action_margin_guard_cap"] == pytest.approx(0.1)
    assert guarded.parent_policy_anchor_network is not None


def test_parent_policy_constraint_produces_finite_separate_loss(tmp_path):
    parent = create_fresh_trainer(_mapper(), seed=46, batch_size=2, learning_starts=2)
    path = tmp_path / "parent.pth"
    _write_simulator_checkpoint(path, parent.online_network.state_dict())
    trainer = create_fresh_trainer(
        _mapper(),
        seed=101,
        batch_size=2,
        learning_starts=2,
        parent_policy_anchor_weight=1.0,
    )
    initialize_trainer(
        trainer,
        load_initial_checkpoint(path, expected_sha256=None),
    )
    state = np.zeros(328, dtype=np.float32)
    card_ids = np.zeros(10, dtype=np.int64)
    potion_ids = np.zeros(5, dtype=np.int64)
    relic_ids = np.zeros(40, dtype=np.int64)
    mask = np.zeros(133, dtype=bool)
    mask[[1, 90]] = True
    for action, reward in ((1, 1.0), (90, -0.05)):
        assert trainer.store_transition(
            state,
            card_ids,
            potion_ids,
            relic_ids,
            action,
            reward,
            state,
            card_ids,
            potion_ids,
            relic_ids,
            False,
            action_mask=mask,
            next_action_mask=mask,
        )

    loss = trainer.train_step()

    assert math.isfinite(loss)
    assert trainer.last_td_loss > 0.0
    assert trainer.last_parent_policy_anchor_loss > 0.0
    assert loss == pytest.approx(
        trainer.last_td_loss + trainer.last_parent_policy_anchor_loss
    )


def test_parent_end_turn_margin_guard_produces_separate_metrics(tmp_path):
    parent = create_fresh_trainer(_mapper(), seed=147, batch_size=2, learning_starts=2)
    with torch.no_grad():
        for parameter in parent.online_network.parameters():
            parameter.zero_()
        parent.online_network.advantage_stream[2].bias[1] = 0.5
    path = tmp_path / "controlled-margin-parent.pth"
    _write_simulator_checkpoint(path, parent.online_network.state_dict())
    trainer = create_fresh_trainer(
        _mapper(),
        seed=148,
        batch_size=2,
        learning_starts=2,
        parent_policy_anchor_weight=1.0,
        parent_end_turn_margin_guard_weight=1.0,
        parent_end_turn_margin_guard_cap=0.1,
    )
    initialize_trainer(
        trainer,
        load_initial_checkpoint(path, expected_sha256=None),
    )
    with torch.no_grad():
        trainer.online_network.advantage_stream[2].bias[1] = 0.0
        trainer.online_network.advantage_stream[2].bias[END_TURN_ACTION] = 0.2

    state = np.zeros(328, dtype=np.float32)
    card_ids = np.zeros(10, dtype=np.int64)
    potion_ids = np.zeros(5, dtype=np.int64)
    relic_ids = np.zeros(40, dtype=np.int64)
    mask = np.zeros(133, dtype=bool)
    mask[[1, END_TURN_ACTION]] = True
    for _ in range(2):
        assert trainer.store_transition(
            state,
            card_ids,
            potion_ids,
            relic_ids,
            1,
            1.0,
            state,
            card_ids,
            potion_ids,
            relic_ids,
            False,
            action_mask=mask,
            next_action_mask=mask,
        )

    objective_metrics = run_optimizer(trainer, 1)
    loss = objective_metrics["total"][0]

    assert math.isfinite(loss)
    assert trainer.last_parent_end_turn_margin_guard_loss == pytest.approx(0.3)
    assert trainer.last_parent_end_turn_margin_guard_eligible_count == 2
    assert trainer.last_parent_end_turn_margin_guard_ranking_violation_count == 2
    assert objective_metrics["parent_end_turn_margin_guard"] == pytest.approx([0.3])
    assert objective_metrics[
        "parent_end_turn_margin_guard_eligible_count"
    ] == pytest.approx([2.0])
    assert objective_metrics[
        "parent_end_turn_margin_guard_ranking_violation_count"
    ] == pytest.approx([2.0])
    assert loss == pytest.approx(
        trainer.last_td_loss
        + trainer.last_parent_policy_anchor_loss
        + trainer.last_parent_end_turn_margin_guard_loss
    )


def test_parent_card_ranking_guard_produces_separate_metrics(tmp_path):
    parent = create_fresh_trainer(_mapper(), seed=152, batch_size=2, learning_starts=2)
    with torch.no_grad():
        for parameter in parent.online_network.parameters():
            parameter.zero_()
        parent.online_network.advantage_stream[2].bias[1] = 0.5
        parent.online_network.advantage_stream[2].bias[7] = 0.3
    path = tmp_path / "controlled-card-ranking-parent.pth"
    _write_simulator_checkpoint(path, parent.online_network.state_dict())
    trainer = create_fresh_trainer(
        _mapper(),
        seed=153,
        batch_size=2,
        learning_starts=2,
        parent_policy_anchor_weight=1.0,
        parent_card_ranking_guard_weight=1.0,
        parent_card_ranking_guard_cap=0.1,
    )
    initialize_trainer(
        trainer,
        load_initial_checkpoint(path, expected_sha256=None),
    )
    with torch.no_grad():
        trainer.online_network.advantage_stream[2].bias[1] = 0.0
        trainer.online_network.advantage_stream[2].bias[7] = 0.2

    state = np.zeros(328, dtype=np.float32)
    card_ids = np.zeros(10, dtype=np.int64)
    potion_ids = np.zeros(5, dtype=np.int64)
    relic_ids = np.zeros(40, dtype=np.int64)
    mask = np.zeros(133, dtype=bool)
    mask[[1, 7, END_TURN_ACTION]] = True
    for _ in range(2):
        assert trainer.store_transition(
            state,
            card_ids,
            potion_ids,
            relic_ids,
            1,
            1.0,
            state,
            card_ids,
            potion_ids,
            relic_ids,
            False,
            action_mask=mask,
            next_action_mask=mask,
        )

    objective_metrics = run_optimizer(trainer, 1)
    loss = objective_metrics["total"][0]

    assert math.isfinite(loss)
    assert trainer.last_parent_card_ranking_guard_loss == pytest.approx(0.3)
    assert trainer.last_parent_card_ranking_guard_eligible_count == 2
    assert trainer.last_parent_card_ranking_guard_ranking_violation_count == 2
    assert objective_metrics["parent_card_ranking_guard"] == pytest.approx([0.3])
    assert objective_metrics[
        "parent_card_ranking_guard_eligible_count"
    ] == pytest.approx([2.0])
    assert objective_metrics[
        "parent_card_ranking_guard_ranking_violation_count"
    ] == pytest.approx([2.0])
    assert loss == pytest.approx(
        trainer.last_td_loss
        + trainer.last_parent_policy_anchor_loss
        + trainer.last_parent_card_ranking_guard_loss
    )


def test_parent_top_action_margin_guard_produces_separate_metrics(tmp_path):
    parent = create_fresh_trainer(_mapper(), seed=157, batch_size=2, learning_starts=2)
    with torch.no_grad():
        for parameter in parent.online_network.parameters():
            parameter.zero_()
        parent.online_network.advantage_stream[2].bias[END_TURN_ACTION] = 0.5
        parent.online_network.advantage_stream[2].bias[1] = 0.3
    path = tmp_path / "controlled-top-action-parent.pth"
    _write_simulator_checkpoint(path, parent.online_network.state_dict())
    trainer = create_fresh_trainer(
        _mapper(),
        seed=158,
        batch_size=2,
        learning_starts=2,
        parent_policy_anchor_weight=1.0,
        parent_top_action_margin_guard_weight=1.0,
        parent_top_action_margin_guard_cap=0.1,
    )
    initialize_trainer(
        trainer,
        load_initial_checkpoint(path, expected_sha256=None),
    )
    with torch.no_grad():
        trainer.online_network.advantage_stream[2].bias[END_TURN_ACTION] = 0.0
        trainer.online_network.advantage_stream[2].bias[1] = 0.2

    state = np.zeros(328, dtype=np.float32)
    card_ids = np.zeros(10, dtype=np.int64)
    potion_ids = np.zeros(5, dtype=np.int64)
    relic_ids = np.zeros(40, dtype=np.int64)
    mask = np.zeros(133, dtype=bool)
    mask[[1, END_TURN_ACTION]] = True
    for _ in range(2):
        assert trainer.store_transition(
            state,
            card_ids,
            potion_ids,
            relic_ids,
            1,
            1.0,
            state,
            card_ids,
            potion_ids,
            relic_ids,
            False,
            action_mask=mask,
            next_action_mask=mask,
        )

    objective_metrics = run_optimizer(trainer, 1)
    loss = objective_metrics["total"][0]

    assert math.isfinite(loss)
    assert trainer.last_parent_top_action_margin_guard_loss == pytest.approx(0.3)
    assert trainer.last_parent_top_action_margin_guard_eligible_count == 2
    assert trainer.last_parent_top_action_margin_guard_ranking_violation_count == 2
    assert objective_metrics["parent_top_action_margin_guard"] == pytest.approx([0.3])
    assert objective_metrics[
        "parent_top_action_margin_guard_eligible_count"
    ] == pytest.approx([2.0])
    assert objective_metrics[
        "parent_top_action_margin_guard_ranking_violation_count"
    ] == pytest.approx([2.0])
    assert loss == pytest.approx(
        trainer.last_td_loss
        + trainer.last_parent_policy_anchor_loss
        + trainer.last_parent_top_action_margin_guard_loss
    )


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"checkpoint_kind": "production_rl_v2"}, "kind"),
        ({"production_compatible": True}, "production-compatible"),
        ({"online_network_state_dict": None}, "online state"),
    ],
)
def test_warm_start_rejects_non_simulator_checkpoint_before_training(
    tmp_path, overrides, message
):
    trainer = create_fresh_trainer(_mapper(), seed=43, batch_size=2, learning_starts=2)
    path = tmp_path / "invalid.pth"
    _write_simulator_checkpoint(path, trainer.online_network.state_dict(), **overrides)

    with pytest.raises(ValueError, match=message):
        load_initial_checkpoint(path, expected_sha256=None)


def test_warm_start_rejects_hash_and_network_structure_mismatch(tmp_path):
    parent = create_fresh_trainer(_mapper(), seed=47, batch_size=2, learning_starts=2)
    path = tmp_path / "parent.pth"
    _write_simulator_checkpoint(path, parent.online_network.state_dict())

    with pytest.raises(ValueError, match="hash mismatch"):
        load_initial_checkpoint(path, expected_sha256="0" * 64)

    binding = load_initial_checkpoint(path, expected_sha256=None)
    binding["state_dict"] = {"wrong": torch.zeros(1)}
    target = create_fresh_trainer(_mapper(), seed=49, batch_size=2, learning_starts=2)
    with pytest.raises(ValueError, match="network incompatible"):
        initialize_trainer(target, binding)


def test_published_candidate_is_structurally_simulator_only(tmp_path):
    trainer = create_fresh_trainer(
        _mapper(),
        seed=29,
        batch_size=2,
        learning_starts=2,
    )
    report = {
        "verdict": "technical_smoke_ready",
        "config": {"network_seed": 29},
        "provenance": {
            "adapter_source_sha256": "a" * 64,
            "module_sha256": "b" * 64,
            "simulator_source_sha256": "c" * 64,
            "training_runner_sha256": "d" * 64,
        },
        "training": {
            "initial_parameter_sha256": "e" * 64,
            "candidate_parameter_sha256": "f" * 64,
            "parent_policy_anchor_weight": 1.0,
            "parent_anchor_label_mode": (
                GUARD_REPLACEMENT_EXECUTED_ACTION_ANCHOR_LABEL
            ),
            "parent_policy_anchor_override_count": {
                "first": 2.0,
                "last": 1.0,
                "mean": 1.5,
                "minimum": 1.0,
                "maximum": 2.0,
            },
            "parent_end_turn_margin_guard_weight": 1.0,
            "parent_end_turn_margin_guard_cap": 0.1,
            "replay_target": {
                "mode": FROZEN_PARENT_N_STEP_TARGET,
                "horizon": 3,
                "discount": 0.99,
                "bootstrap_parameter_sha256": "e" * 64,
            },
        },
        "corpus": {
            "behavior": {
                "mode": FROZEN_PARENT_GUARDED_EPSILON_BEHAVIOR,
                "epsilon": 0.1,
                "parent_parameter_sha256": "e" * 64,
                "parent_branch_count": 9,
                "exploration_branch_count": 1,
            }
        },
        "initialization": {
            "mode": "warm_start_encounter_expansion",
            "checkpoint_sha256": "1" * 64,
            "parameter_sha256": "e" * 64,
            "source_parameter_sha256": "9" * 64,
            "parent_policy_anchor_parameter_sha256": "e" * 64,
            "encounter_identity_migration": {
                "bucket_count": 64,
                "hash_algorithm": ENCOUNTER_HASH_ALGORITHM,
            },
        },
        "evaluation": {"paired": {"aggregate": {}}},
    }

    _publish(
        tmp_path / "smoke",
        report=report,
        candidate_state=trainer.online_network.state_dict(),
    )
    checkpoint = load_torch_checkpoint(
        tmp_path / "smoke" / "simulator_only_candidate.pth",
        map_location="cpu",
    )

    assert checkpoint["checkpoint_schema_version"] == 0
    assert checkpoint["checkpoint_kind"] == "simulator_training_smoke"
    assert checkpoint["production_compatible"] is False
    assert checkpoint["metadata"]["authority"]["simulator_fitting"] is True
    assert checkpoint["metadata"]["authority"]["promotion"] is False
    assert checkpoint["metadata"]["source_binding"]["module_sha256"] == "b" * 64
    assert checkpoint["metadata"]["source_binding"]["candidate_parameter_sha256"] == "f" * 64
    assert (
        checkpoint["metadata"]["source_binding"]["initial_checkpoint_sha256"]
        == "1" * 64
    )
    assert (
        checkpoint["metadata"]["source_binding"][
            "initial_checkpoint_parameter_sha256"
        ]
        == "9" * 64
    )
    assert (
        checkpoint["metadata"]["source_binding"]["initial_parameter_sha256"]
        == "e" * 64
    )
    assert (
        checkpoint["metadata"]["source_binding"]["encounter_identity_migration"][
            "bucket_count"
        ]
        == 64
    )
    assert (
        checkpoint["metadata"]["source_binding"]["parent_policy_anchor_weight"]
        == pytest.approx(1.0)
    )
    assert (
        checkpoint["metadata"]["source_binding"]["parent_anchor_label_mode"]
        == GUARD_REPLACEMENT_EXECUTED_ACTION_ANCHOR_LABEL
    )
    assert (
        checkpoint["metadata"]["source_binding"][
            "parent_end_turn_margin_guard_weight"
        ]
        == pytest.approx(1.0)
    )
    assert (
        checkpoint["metadata"]["source_binding"][
            "parent_end_turn_margin_guard_cap"
        ]
        == pytest.approx(0.1)
    )
    assert checkpoint["metadata"]["source_binding"]["replay_target"] == report[
        "training"
    ]["replay_target"]
    assert checkpoint["metadata"]["source_binding"]["collection_behavior"] == report[
        "corpus"
    ]["behavior"]


def test_opt_in_tiny_native_training_smoke():
    module_path = os.environ.get("STS_LIGHTSPEED_COMBAT_ADAPTER_MODULE")
    items_json = os.environ.get("STS_ITEMS_JSON")
    if not module_path or not items_json:
        pytest.skip("native combat adapter paths are not configured")
    dll_directory = os.environ.get("STS_LIGHTSPEED_MINGW_BIN")
    module = load_native_module(
        module_path,
        dll_directories=(() if not dll_directory else (dll_directory,)),
    )
    report, _candidate = run_smoke(
        module,
        id_mapper=build_id_mapper(items_json),
        config=SmokeConfig(
            train_seeds=(0, 1),
            evaluation_seeds=(10000, 10001),
            batch_size=2,
            optimizer_steps=1,
        ),
        provenance={"training_runner_sha256": "b" * 64},
    )

    assert report["verdict"] == "technical_smoke_ready"
    assert report["training"]["replay_transition_count"] >= 2
    assert report["training"]["optimizer_update_count"] == 1
    assert report["training"]["parameter_delta"]["l2"] > 0.0
    assert "card_select_settlement" in report["corpus"]
    assert report["evaluation"]["control"]["aggregate"]["seed_count"] == 2
    assert report["evaluation"]["candidate"]["aggregate"]["seed_count"] == 2
    assert "card_select_settlement_action_count" in report["evaluation"]["control"]["aggregate"]
    assert "card_select_settlement_action_count" in report["evaluation"]["candidate"]["aggregate"]


def test_opt_in_native_discounted_return_training_smoke():
    module_path = os.environ.get("STS_LIGHTSPEED_COMBAT_ADAPTER_MODULE")
    items_json = os.environ.get("STS_ITEMS_JSON")
    if not module_path or not items_json:
        pytest.skip("native combat adapter paths are not configured")
    dll_directory = os.environ.get("STS_LIGHTSPEED_MINGW_BIN")
    module = load_native_module(
        module_path,
        dll_directories=(() if not dll_directory else (dll_directory,)),
    )
    report, _candidate = run_smoke(
        module,
        id_mapper=build_id_mapper(items_json),
        config=SmokeConfig(
            train_seeds=(0, 1),
            evaluation_seeds=(10000, 10001),
            max_decisions_per_seed=100,
            batch_size=2,
            optimizer_steps=1,
            replay_target_mode=DISCOUNTED_EPISODE_RETURN_TARGET,
            complete_trajectories_only=True,
        ),
        provenance={"training_runner_sha256": "b" * 64},
    )

    eligibility = report["corpus"]["trajectory_eligibility"]
    target = report["training"]["replay_target"]
    assert report["verdict"] == "technical_smoke_ready"
    assert eligibility["complete_profile_count"] == 2
    assert eligibility["incomplete_profile_count"] == 0
    assert eligibility["excluded_incomplete_profile_count"] == 0
    assert report["training"]["source_replay_transition_count"] == report[
        "training"
    ]["target_replay_transition_count"]
    assert target["mode"] == DISCOUNTED_EPISODE_RETURN_TARGET
    assert target["discount"] == pytest.approx(0.99)
    assert target["source_transition_identity_sha256"] == eligibility[
        "source_transition_identity_sha256"
    ]
    assert target["terminal_target_count"] == report["training"][
        "target_replay_transition_count"
    ]


def test_opt_in_native_frozen_parent_n_step_training_smoke():
    module_path = os.environ.get("STS_LIGHTSPEED_COMBAT_ADAPTER_MODULE")
    items_json = os.environ.get("STS_ITEMS_JSON")
    if not module_path or not items_json:
        pytest.skip("native combat adapter paths are not configured")
    dll_directory = os.environ.get("STS_LIGHTSPEED_MINGW_BIN")
    module = load_native_module(
        module_path,
        dll_directories=(() if not dll_directory else (dll_directory,)),
    )
    mapper = build_id_mapper(items_json)
    parent = create_fresh_trainer(
        mapper,
        seed=152,
        batch_size=2,
        learning_starts=2,
    )
    parent_state = copy.deepcopy(parent.online_network.state_dict())
    parent_sha256 = parameter_sha256(parent_state)
    report, _candidate = run_smoke(
        module,
        id_mapper=mapper,
        config=SmokeConfig(
            train_seeds=(4, 5),
            evaluation_seeds=(10004, 10005),
            max_decisions_per_seed=100,
            batch_size=2,
            optimizer_steps=1,
            replay_target_mode=FROZEN_PARENT_N_STEP_TARGET,
            replay_return_horizon=3,
            complete_trajectories_only=True,
        ),
        provenance={"training_runner_sha256": "b" * 64},
        initial_checkpoint={
            "checkpoint_sha256": "a" * 64,
            "checkpoint_kind": "simulator_training_smoke",
            "checkpoint_schema_version": 0,
            "parameter_sha256": parent_sha256,
            "path": "memory-parent.pth",
            "production_compatible": False,
            "size_bytes": 0,
            "source_type": "sts_lightspeed_native_combat",
            "state_dict": parent_state,
        },
    )

    target = report["training"]["replay_target"]
    assert report["verdict"] == "technical_smoke_ready"
    assert target["mode"] == FROZEN_PARENT_N_STEP_TARGET
    assert target["horizon"] == 3
    assert target["bootstrap_parameter_sha256"] == parent_sha256
    assert target["bootstrap_target_count"] > 0
    assert target["terminal_target_count"] == report["training"][
        "target_replay_transition_count"
    ]


def test_opt_in_native_encounter_identity_training_smoke():
    module_path = os.environ.get("STS_LIGHTSPEED_COMBAT_ADAPTER_MODULE")
    items_json = os.environ.get("STS_ITEMS_JSON")
    if not module_path or not items_json:
        pytest.skip("native combat adapter paths are not configured")
    dll_directory = os.environ.get("STS_LIGHTSPEED_MINGW_BIN")
    module = load_native_module(
        module_path,
        dll_directories=(() if not dll_directory else (dll_directory,)),
    )
    mapper = build_id_mapper(items_json)
    parent = create_fresh_trainer(
        mapper,
        seed=151,
        batch_size=2,
        learning_starts=2,
    )
    parent_state = copy.deepcopy(parent.online_network.state_dict())
    report, _candidate = run_smoke(
        module,
        id_mapper=mapper,
        config=SmokeConfig(
            train_seeds=(2, 3),
            evaluation_seeds=(10002, 10003),
            batch_size=2,
            optimizer_steps=1,
            parent_policy_anchor_weight=1.0,
            encounter_identity_buckets=64,
            encounter_identity_encoding=ENCOUNTER_ENUM_ENCODING,
        ),
        provenance={"training_runner_sha256": "b" * 64},
        initial_checkpoint={
            "checkpoint_sha256": "a" * 64,
            "checkpoint_kind": "simulator_training_smoke",
            "checkpoint_schema_version": 0,
            "parameter_sha256": parameter_sha256(parent_state),
            "path": "memory-parent.pth",
            "production_compatible": False,
            "size_bytes": 0,
            "source_type": "sts_lightspeed_native_combat",
            "state_dict": parent_state,
        },
    )

    identity = report["corpus"]["encounter_identity"]
    migration = report["initialization"]["encounter_identity_migration"]
    assert report["verdict"] == "technical_smoke_ready"
    assert report["observation_extension"]["encounter_identity"]["continuous_dim"] == 392
    assert identity["bucket_count"] == 64
    assert identity["encoding"] == ENCOUNTER_ENUM_ENCODING
    assert identity["assignments"]
    assert identity["occupied_bucket_count"] >= 1
    assert identity["vocabulary_sha256"] == ENCOUNTER_ENUM_V1_SHA256
    assert report["observation_extension"]["encounter_identity"][
        "vocabulary_sha256"
    ] == ENCOUNTER_ENUM_V1_SHA256
    assert migration["encoding"] == ENCOUNTER_ENUM_ENCODING
    assert migration["vocabulary_sha256"] == ENCOUNTER_ENUM_V1_SHA256
    assert migration["equivalence"]["passed"] is True
    assert report["training"]["optimizer_update_count"] == 1


def test_r3_card_select_blockers_settle_deterministically_across_clones():
    module_path = os.environ.get("STS_LIGHTSPEED_COMBAT_ADAPTER_MODULE")
    items_json = os.environ.get("STS_ITEMS_JSON")
    if not module_path or not items_json:
        pytest.skip("native combat adapter paths are not configured")
    dll_directory = os.environ.get("STS_LIGHTSPEED_MINGW_BIN")
    module = load_native_module(
        module_path,
        dll_directories=(() if not dll_directory else (dll_directory,)),
    )
    id_mapper = build_id_mapper(items_json)
    trainer = create_fresh_trainer(
        id_mapper,
        seed=2026081905,
        batch_size=2,
        learning_starts=2,
    )
    checkpoint = load_torch_checkpoint(
        REPO_ROOT
        / "reports"
        / "combat_lightspeed_training_smoke_20260819_r3_replication"
        / "simulator_only_candidate.pth",
        map_location="cpu",
    )
    trainer.online_network.load_state_dict(checkpoint["online_network_state_dict"])
    trainer.online_network.eval()

    for seed in (50252, 50254):
        environment = NativeCombatEnvironment.reset(module, seed=seed, ascension=0)
        actions_since_end_turn = 0
        settlement_seen = False
        for _ in range(80):
            status = environment.status()
            if status["terminal"]:
                break
            assert status["supported"], status
            mapped = environment.mapped_state(id_mapper=id_mapper)
            legal = environment.legal_actions()
            if actions_since_end_turn >= 8:
                selected = next(action for action in legal if action["kind"] == "end_turn")
            else:
                action_index = trainer.select_action(
                    mapped.state.continuous,
                    mapped.state.card_ids,
                    mapped.state.potion_ids,
                    mapped.state.relic_ids,
                    mapped.action_mask,
                    training=False,
                )
                selected = next(
                    action for action in legal if action["rl_action_index"] == action_index
                )

            original = canonical_json_bytes(environment.snapshot())
            left = environment.clone()
            right = environment.clone()
            left.step(selected["action_id"])
            right.step(selected["action_id"])
            assert canonical_json_bytes(environment.snapshot()) == original
            assert canonical_json_bytes(left.snapshot()) == canonical_json_bytes(right.snapshot())
            assert canonical_json_bytes(left.status()) == canonical_json_bytes(right.status())
            assert canonical_json_bytes(left.legal_actions()) == canonical_json_bytes(
                right.legal_actions()
            )

            settlement = left.snapshot()["card_select_settlement"]
            assert settlement["count"] == len(settlement["tasks"])
            if settlement["count"]:
                settlement_seen = True
                assert all(isinstance(task, str) and task for task in settlement["tasks"])
                assert left.status()["supported"] or left.status()["terminal"]

            environment = left
            actions_since_end_turn = (
                0 if selected["kind"] == "end_turn" else actions_since_end_turn + 1
            )
        else:
            pytest.fail(f"seed {seed} exceeded the decision bound")

        assert settlement_seen, seed
        assert environment.status()["terminal"] is True
        assert environment.status()["outcome"] == "player_victory"


def test_production_agent_import_does_not_load_training_smoke():
    code = (
        "import sys;"
        f"sys.path.insert(0, {str(REPO_ROOT)!r});"
        "import spirecomm.ai.rl.v2.agent;"
        "assert 'analysis_scripts.combat_lightspeed_training_smoke' not in sys.modules;"
        "assert 'sts_lightspeed_combat_adapter' not in sys.modules"
    )
    completed = subprocess.run(
        [sys.executable, "-I", "-c", code],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
