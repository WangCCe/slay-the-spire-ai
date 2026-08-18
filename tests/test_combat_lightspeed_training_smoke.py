import copy
import os
from pathlib import Path
import random
import subprocess
import sys

import numpy as np
import torch
import pytest

from analysis_scripts.combat_lightspeed_training_smoke import (
    REPORT_AUTHORITY,
    SmokeConfig,
    _publish,
    calculate_native_reward,
    create_fresh_trainer,
    parameter_delta,
    parameter_sha256,
    select_behavior_action,
    successor_disposition,
    run_smoke,
)
from analysis_scripts.combat_lightspeed_bridge import load_native_module
from spirecomm.ai.rl.checkpoint_io import load_torch_checkpoint
from spirecomm.ai.rl.v2.id_mapping import IdMapper, build_id_mapper


REPO_ROOT = Path(__file__).resolve().parents[1]


def _actions():
    return [
        {"action_id": "play_card:0:1", "available": True, "kind": "play_card", "rl_action_index": 1},
        {"action_id": "play_card:1:1", "available": True, "kind": "play_card", "rl_action_index": 7},
        {"action_id": "end_turn", "available": True, "kind": "end_turn", "rl_action_index": 90},
    ]


def _snapshot(*, monster_hp=10, player_hp=80, turn=1, targetable=True):
    return {
        "state": {
            "turn": turn,
            "player": {"current_hp": player_hp, "max_hp": 80},
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
    assert report["evaluation"]["control"]["aggregate"]["seed_count"] == 2
    assert report["evaluation"]["candidate"]["aggregate"]["seed_count"] == 2


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
