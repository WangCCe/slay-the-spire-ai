from dataclasses import replace
import hashlib
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest
import torch

from analysis_scripts.combat_lightspeed_replay_distribution_calibration import (
    REPORT_AUTHORITY,
    RealReplayBinding,
    TransitionBatch,
    build_collection_config,
    build_report,
    canonical_report_bytes,
    combat_action_family,
    compare_sources,
    floor_stratum,
    load_real_replay_bindings,
    publish_report,
    summarize_source,
    validate_provenance_identity,
    verify_file_identity,
)
from analysis_scripts.combat_lightspeed_training_smoke import (
    FROZEN_PARENT_GUARDED_EPSILON_BEHAVIOR,
    GREEDY_NATIVE_REWARD_DEPLOYMENT_GUARD_PROXY,
)
from spirecomm.ai.rl.checkpoint_io import save_torch_checkpoint
from spirecomm.ai.rl.v2.state_encoder import StateEncoderV2


REPO_ROOT = Path(__file__).resolve().parents[1]
ACTION_DIM = 133
CARD_SLOTS = 10
POTION_SLOTS = 5
RELIC_SLOTS = 40


def _replay_state(*, floors=(1, 6, 18, 28), schema_version=2):
    count = len(floors)
    continuous = torch.zeros(
        (count, StateEncoderV2.CONTINUOUS_DIM), dtype=torch.float32
    )
    continuous[:, 0] = torch.tensor([0.5, 0.75, 0.25, 1.0][:count])
    continuous[:, 1] = 0.6
    continuous[:, 3] = torch.tensor(floors, dtype=torch.float32) / 50.0
    continuous[:, 33] = 1.0
    card_ids = torch.zeros((count, CARD_SLOTS), dtype=torch.int64)
    card_ids[:, :2] = torch.tensor([1, 2])
    potion_ids = torch.zeros((count, POTION_SLOTS), dtype=torch.int64)
    potion_ids[:, 0] = 3
    relic_ids = torch.zeros((count, RELIC_SLOTS), dtype=torch.int64)
    relic_ids[:, 0] = 4
    actions = torch.tensor([0, 60, 90, 91][:count], dtype=torch.int64)
    masks = torch.zeros((count, ACTION_DIM), dtype=torch.bool)
    masks[:, 0] = True
    masks[:, 90] = True
    masks[torch.arange(count), actions] = True
    dones = torch.zeros(count, dtype=torch.bool)
    dones[-1] = True
    result = {
        "schema_version": schema_version,
        "buffer_size": 100_000,
        "continuous_dim": StateEncoderV2.CONTINUOUS_DIM,
        "action_dim": ACTION_DIM,
        "card_slots": CARD_SLOTS,
        "potion_slots": POTION_SLOTS,
        "relic_slots": RELIC_SLOTS,
        "transition_count": count,
        "source_transition_count": count,
        "truncated": False,
        "continuous": continuous,
        "card_ids": card_ids,
        "potion_ids": potion_ids,
        "relic_ids": relic_ids,
        "actions": actions,
        "rewards": torch.tensor([1.0, -2.0, 3.0, 4.0][:count]),
        "next_continuous": continuous.clone(),
        "next_card_ids": card_ids.clone(),
        "next_potion_ids": potion_ids.clone(),
        "next_relic_ids": relic_ids.clone(),
        "dones": dones,
        "action_masks": masks,
        "next_action_masks": masks.clone(),
        "anchor_to_executed_action": torch.zeros(count, dtype=torch.bool),
    }
    if schema_version == 1:
        result.pop("anchor_to_executed_action")
    return result


def _write_checkpoint(tmp_path, state=None):
    path = tmp_path / "replay.pth"
    save_torch_checkpoint(
        {
            "checkpoint_schema_version": 3,
            "checkpoint_kind": "combat_rl_v2",
            "replay_buffer_state_dict": state or _replay_state(),
        },
        str(path),
    )
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return path, digest


def _batch(*, floors=(1, 6, 18, 28), reward_shift=0.0):
    state = _replay_state(floors=floors)
    return TransitionBatch(
        continuous=state["continuous"].numpy(),
        card_ids=state["card_ids"].numpy(),
        potion_ids=state["potion_ids"].numpy(),
        relic_ids=state["relic_ids"].numpy(),
        actions=state["actions"].numpy(),
        rewards=state["rewards"].numpy() + reward_shift,
        dones=state["dones"].numpy(),
        action_masks=state["action_masks"].numpy(),
    )


@pytest.mark.parametrize("schema_version", [1, 2])
def test_complete_supported_real_replay_is_loaded_and_bound(tmp_path, schema_version):
    path, digest = _write_checkpoint(
        tmp_path, _replay_state(schema_version=schema_version)
    )

    batch, evidence = load_real_replay_bindings(
        (RealReplayBinding("real", path, digest),)
    )

    assert batch.transition_count == 4
    assert evidence[0]["label"] == "real"
    assert evidence[0]["replay_transition_count"] == 4
    assert evidence[0]["replay_schema_version"] == schema_version
    assert evidence[0]["sha256"] == digest


@pytest.mark.parametrize(
    ("mutation", "match"),
    [
        (lambda state: state.update(schema_version=3), "schema-v1 or schema-v2"),
        (lambda state: state.update(truncated=True), "untruncated"),
        (lambda state: state.update(source_transition_count=5), "complete"),
        (
            lambda state: state.update(
                continuous_dim=StateEncoderV2.CONTINUOUS_DIM - 1
            ),
            "continuous_dim mismatch",
        ),
        (
            lambda state: state.update(continuous=state["continuous"][:, :-1]),
            "continuous shape mismatch",
        ),
        (
            lambda state: state.update(
                actions=torch.tensor([0, 60, 90, 133], dtype=torch.int64)
            ),
            "action",
        ),
        (
            lambda state: state.update(
                action_masks=torch.zeros_like(state["action_masks"])
            ),
            "absent from its action mask",
        ),
    ],
)
def test_real_replay_contract_drift_fails_before_use(tmp_path, mutation, match):
    state = _replay_state()
    mutation(state)
    path, digest = _write_checkpoint(tmp_path, state)

    with pytest.raises(ValueError, match=match):
        load_real_replay_bindings((RealReplayBinding("real", path, digest),))


def test_real_checkpoint_hash_mismatch_fails_before_load(tmp_path):
    path, _ = _write_checkpoint(tmp_path)

    with pytest.raises(ValueError, match="hash mismatch"):
        load_real_replay_bindings((RealReplayBinding("real", path, "0" * 64),))


def test_registered_file_identity_rejects_hash_drift(tmp_path):
    path = tmp_path / "module.pyd"
    path.write_bytes(b"registered")

    identity = verify_file_identity(
        path,
        hashlib.sha256(b"registered").hexdigest(),
        label="native module",
    )

    assert identity["path"] == path.resolve().as_posix()
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_file_identity(path, "0" * 64, label="native module")


def test_registered_provenance_rejects_source_drift():
    provenance = {
        "adapter_source_sha256": "a" * 64,
        "simulator_commit": "b" * 40,
        "simulator_source_sha256": "c" * 64,
    }

    identity = validate_provenance_identity(
        provenance,
        adapter_source_sha256="a" * 64,
        simulator_commit="b" * 40,
        simulator_source_sha256="c" * 64,
    )

    assert identity["simulator_commit"] == "b" * 40
    with pytest.raises(ValueError, match="simulator source sha256 mismatch"):
        validate_provenance_identity(
            provenance,
            adapter_source_sha256="a" * 64,
            simulator_commit="b" * 40,
            simulator_source_sha256="d" * 64,
        )


@pytest.mark.parametrize(
    ("floor", "expected"),
    [
        (0, "floor_00_05"),
        (5, "floor_00_05"),
        (6, "floor_06_10"),
        (17, "floor_11_17"),
        (18, "floor_18_22"),
        (34, "floor_28_34"),
        (35, "floor_35_39"),
        (50, "floor_45_50"),
    ],
)
def test_floor_strata_follow_the_rl_v2_encoded_contract(floor, expected):
    assert floor_stratum(floor / 50.0) == expected


@pytest.mark.parametrize("value", [float("nan"), -0.01, 1.01, 0.333])
def test_invalid_or_non_integral_encoded_floor_is_rejected(value):
    with pytest.raises(ValueError, match="floor"):
        floor_stratum(value)


def test_source_summary_binds_semantics_action_families_and_id_support():
    summary = summarize_source(_batch())

    assert summary["transition_count"] == 4
    assert summary["strata"]["floor_00_05"]["semantic"]["player_hp_ratio"][
        "mean"
    ] == pytest.approx(0.5)
    assert summary["aggregate"]["action_family_counts"] == {
        "end_turn": 1,
        "play_card": 1,
        "reward_choice": 1,
        "use_potion": 1,
    }
    assert summary["aggregate"]["card_id_support"] == [1, 2]
    assert summary["aggregate"]["potion_id_support"] == [3]
    assert summary["aggregate"]["relic_id_support"] == [4]
    assert summary["aggregate"]["legal_action_count"]["mean"] == 2.5


@pytest.mark.parametrize(
    ("action", "family"),
    [(0, "play_card"), (59, "play_card"), (60, "use_potion"), (90, "end_turn"), (91, "reward_choice"), (132, "system")],
)
def test_action_family_covers_the_full_rl_v2_space(action, family):
    assert combat_action_family(action) == family


def test_comparison_filters_common_support_and_ranks_numeric_mismatches():
    real = summarize_source(_batch(floors=(1, 1, 6, 6)))
    simulator = summarize_source(
        _batch(floors=(1, 1, 6, 6), reward_shift=3.0)
    )

    comparison = compare_sources(real, simulator, minimum_stratum_count=2)

    assert comparison["common_strata"] == ["floor_00_05", "floor_06_10"]
    assert comparison["technical_comparison_ready"] is True
    assert comparison["numeric_mismatch_ranking"][0]["metric"] == "reward"
    assert comparison["strata"]["floor_00_05"]["numeric"]["reward"][
        "simulator_minus_real_mean"
    ] == pytest.approx(3.0)


def test_degenerate_variance_is_explicit_and_deterministic():
    real = summarize_source(_batch(floors=(1, 1, 6, 6)))
    simulator = summarize_source(_batch(floors=(1, 1, 6, 6)))

    comparison = compare_sources(real, simulator, minimum_stratum_count=2)
    metric = comparison["strata"]["floor_00_05"]["numeric"]["energy_ratio"]

    assert metric["degenerate_variance"] is True
    assert metric["absolute_standardized_mean_difference"] == 0.0


def test_collection_config_is_frozen_parent_zero_epsilon_and_no_fit_contract():
    config = build_collection_config(
        seeds=(180000, 180001),
        battle_indices=(0, 3, 6),
        behavior_seed=2026082804,
        network_seed=2026082805,
        max_decisions_per_seed=100,
        max_actions_per_turn=8,
    )

    assert config.behavior_policy == FROZEN_PARENT_GUARDED_EPSILON_BEHAVIOR
    assert config.behavior_epsilon == 0.0
    assert config.deployment_guard_proxy == GREEDY_NATIVE_REWARD_DEPLOYMENT_GUARD_PROXY
    assert config.train_seeds == (180000, 180001)
    assert config.battle_indices == (0, 3, 6)


def test_report_is_deterministic_and_grants_no_downstream_authority():
    real = summarize_source(_batch(floors=(1, 1, 6, 6)))
    simulator = summarize_source(_batch(floors=(1, 1, 6, 6)))
    report = build_report(
        real_summary=real,
        simulator_summary=simulator,
        comparison=compare_sources(real, simulator, minimum_stratum_count=2),
        provenance={"source": "test"},
        config={"minimum_stratum_count": 2},
        real_bindings=[{"label": "real"}],
        simulator_collection={"accepted_transition_count": 4},
        optimizer_step=0,
    )

    assert report["verdict"] == "replay_distribution_calibration_ready"
    assert report["authority"] == REPORT_AUTHORITY
    assert not any(REPORT_AUTHORITY.values())
    assert canonical_report_bytes(report) == canonical_report_bytes(report)


def test_publication_writes_canonical_report_summary_and_manifest(tmp_path):
    real = summarize_source(_batch(floors=(1, 1, 6, 6)))
    simulator = summarize_source(_batch(floors=(1, 1, 6, 6)))
    report = build_report(
        real_summary=real,
        simulator_summary=simulator,
        comparison=compare_sources(real, simulator, minimum_stratum_count=2),
        provenance={"source": "test"},
        config={"minimum_stratum_count": 2},
        real_bindings=[{"label": "real"}],
        simulator_collection={"accepted_transition_count": 4},
        optimizer_step=0,
    )
    output = tmp_path / "report"

    publish_report(output, report, max_report_bytes=1_000_000)

    assert (output / "report.json").read_bytes() == canonical_report_bytes(report) + b"\n"
    assert (output / "summary.md").is_file()
    assert (output / "manifest.json").is_file()


def test_calibration_script_supports_direct_execution():
    completed = subprocess.run(
        [
            sys.executable,
            str(
                REPO_ROOT
                / "analysis_scripts"
                / "combat_lightspeed_replay_distribution_calibration.py"
            ),
            "--help",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "--real-checkpoint" in completed.stdout
