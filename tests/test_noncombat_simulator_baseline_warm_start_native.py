from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from analysis_scripts.noncombat_simulator_adapter import (
    NATIVE_TARGET_POLICY_ID,
    NativeSimulatorEnvironment,
    SimulatorAdapterError,
    canonical_json_bytes,
    load_native_module,
)
from analysis_scripts.noncombat_simulator_baseline_warm_start import (
    build_warm_start_model,
    canonical_warm_start_model_payload,
    collect_native_demonstrations,
    evaluate_warm_start_rollouts,
    load_warm_start_model,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
FIT_PROBE_SEEDS = (13,)


@pytest.fixture(scope="module")
def native_settings():
    module_path = os.environ.get("STS_LIGHTSPEED_ADAPTER_MODULE")
    mingw_bin = os.environ.get("STS_LIGHTSPEED_MINGW_BIN")
    simulator_root = os.environ.get("STS_LIGHTSPEED_ROOT")
    if not module_path or not mingw_bin or not simulator_root:
        pytest.skip(
            "set STS_LIGHTSPEED_ADAPTER_MODULE, STS_LIGHTSPEED_MINGW_BIN, "
            "and STS_LIGHTSPEED_ROOT"
        )
    module = load_native_module(module_path, dll_directories=[mingw_bin])
    fit_input = json.loads(
        (
            REPO_ROOT / "reports" / "noncombat_simulator_fit_20260802_r3_input.json"
        ).read_text(encoding="utf-8")
    )
    provenance = fit_input["registered_provenance"]

    def factory(seed: int):
        return NativeSimulatorEnvironment(module.Environment(seed, 0), provenance)

    return module, factory


@pytest.fixture(scope="module")
def native_demonstrations(native_settings):
    _, factory = native_settings
    return collect_native_demonstrations(
        environment_factory=factory,
        cohort="train",
        seeds=FIT_PROBE_SEEDS,
        max_decisions_per_episode=500,
        max_demo_rows=10_000,
        max_episodes=len(FIT_PROBE_SEEDS),
        deadline=time.perf_counter() + 90.0,
        clock=time.perf_counter,
    )


def test_native_warm_start_demonstrations_repeat_and_cover_contract(
    native_settings, native_demonstrations
):
    _, factory = native_settings
    repeated = collect_native_demonstrations(
        environment_factory=factory,
        cohort="train",
        seeds=FIT_PROBE_SEEDS,
        max_decisions_per_episode=500,
        max_demo_rows=10_000,
        max_episodes=len(FIT_PROBE_SEEDS),
        deadline=time.perf_counter() + 90.0,
        clock=time.perf_counter,
    )

    assert canonical_json_bytes(repeated) == canonical_json_bytes(native_demonstrations)
    assert native_demonstrations["all_categories"] == [
        "card_reward",
        "event",
        "route",
        "shop",
    ]
    assert [episode["seed"] for episode in native_demonstrations["episodes"]] == list(
        FIT_PROBE_SEEDS
    )
    assert all(
        episode["outcome"] in {"player_loss", "player_victory"}
        for episode in native_demonstrations["episodes"]
    )
    for row in native_demonstrations["rows"]:
        assert row["teacher"]["policy_id"] == NATIVE_TARGET_POLICY_ID
        assert sum(
            candidate["action_id"] == row["teacher"]["action_id"]
            for candidate in row["candidate_actions"]
        ) == 1


def test_native_warm_start_model_rollout_is_candidate_legal(native_settings):
    _, factory = native_settings
    demonstrations = collect_native_demonstrations(
        environment_factory=factory,
        cohort="validation",
        seeds=FIT_PROBE_SEEDS,
        max_decisions_per_episode=500,
        max_demo_rows=1_000,
        max_episodes=1,
        deadline=time.perf_counter() + 30.0,
        clock=time.perf_counter,
    )
    initial = build_warm_start_model(hash_dim=1024, hidden_dim=128, model_seed=0)
    frozen = load_warm_start_model(
        canonical_warm_start_model_payload(initial),
        expected_hash_dim=1024,
        expected_hidden_dim=128,
    )

    rollouts = evaluate_warm_start_rollouts(
        frozen,
        environment_factory=factory,
        seeds=FIT_PROBE_SEEDS,
        hash_dim=1024,
        max_decisions_per_episode=500,
        max_episodes=2,
        max_wall_seconds=30.0,
        bootstrap_seed=0,
        bootstrap_resamples=100,
        confidence_level=0.95,
        clock=time.perf_counter,
        native_demonstrations=demonstrations,
    )

    assert rollouts["checks"]["candidate_legality"] is True
    assert rollouts["checks"]["terminal_outcomes"] is True
    assert rollouts["policies"]["candidate"]["candidate_legality"] is True


def test_native_warm_start_counterfactual_continuation_fails_closed(
    native_settings,
):
    module, factory = native_settings
    environment = factory(FIT_PROBE_SEEDS[0])
    baseline = environment.native_baseline_action()
    alternative = next(
        candidate["action_id"]
        for candidate in environment.legal_actions()
        if candidate["action_id"] != baseline["action_id"]
    )
    branch = environment.clone()
    branch.step(alternative)

    with pytest.raises(SimulatorAdapterError, match="baseline-following"):
        branch.native_baseline_action()

    assert canonical_json_bytes(environment.native_baseline_action()) == (
        canonical_json_bytes(baseline)
    )
    assert module.adapter_api_version().endswith("v2")
