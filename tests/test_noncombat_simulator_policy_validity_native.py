from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from analysis_scripts.noncombat_simulator_adapter import (
    ADAPTER_API_VERSION,
    NATIVE_TARGET_POLICY_ID,
    NativeSimulatorEnvironment,
    load_native_module,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
FAKE_PROVENANCE = {
    "adapter_commit": "1" * 40,
    "adapter_source_sha256": "2" * 64,
    "build": {
        "adapter_api_version": ADAPTER_API_VERSION,
        "baseline_policy_id": "test-baseline-v1",
        "compiler": "test-compiler",
        "cpp_standard": 201703,
        "native_target_policy_id": NATIVE_TARGET_POLICY_ID,
        "python": "3.10.18",
    },
    "module_sha256": "3" * 64,
    "module_size_bytes": 123,
    "simulator_commit": "4" * 40,
    "simulator_dirty": False,
    "simulator_source_file_count": 79,
    "simulator_source_sha256": "5" * 64,
    "submodules": {"json": "6" * 40, "pybind11": "7" * 40},
}


def test_native_adapter_preserves_published_smoke_compatibility():
    module_path = os.environ.get("STS_LIGHTSPEED_ADAPTER_MODULE")
    mingw_bin = os.environ.get("STS_LIGHTSPEED_MINGW_BIN")
    if not module_path or not mingw_bin:
        pytest.skip("set STS_LIGHTSPEED_ADAPTER_MODULE and STS_LIGHTSPEED_MINGW_BIN")

    # Windows must load the MinGW extension before PyTorch's runtime libraries.
    module = load_native_module(module_path, dll_directories=[mingw_bin])
    from analysis_scripts.noncombat_simulator_policy_validity import (
        COMPATIBILITY_SEEDS,
        build_initial_model,
        load_frozen_model,
        run_compatibility_gate,
    )

    model_payload = json.loads(
        (
            REPO_ROOT
            / "reports"
            / "noncombat_simulator_training_smoke_20260802"
            / "model.json"
        ).read_text(encoding="utf-8")
    )
    trajectories = json.loads(
        (
            REPO_ROOT
            / "reports"
            / "noncombat_simulator_training_smoke_20260802"
            / "trajectories.json"
        ).read_text(encoding="utf-8")
    )
    initial = build_initial_model(hash_dim=1024, model_seed=0)
    trained = load_frozen_model(model_payload, expected_hash_dim=1024)

    def factory(seed: int):
        return NativeSimulatorEnvironment(module.Environment(seed, 0), FAKE_PROVENANCE)

    compatibility = run_compatibility_gate(
        environment_factory=factory,
        initial_model=initial,
        trained_model=trained,
        published_trajectories=trajectories,
        seeds=COMPATIBILITY_SEEDS,
        hash_dim=1024,
        max_decisions_per_episode=500,
        deadline=time.perf_counter() + 120.0,
    )

    assert compatibility["matched"] is True
    assert compatibility["quality_rows_included"] == 0
