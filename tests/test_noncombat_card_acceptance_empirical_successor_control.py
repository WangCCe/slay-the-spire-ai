from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
CONTROL_MODULE = (
    "analysis_scripts.noncombat_card_acceptance_empirical_successor_experiment"
)
RUNTIME_MODULE = (
    "analysis_scripts.noncombat_card_acceptance_empirical_successor_runtime"
)
SEED_MODULE = (
    "analysis_scripts.noncombat_card_acceptance_empirical_successor_seed_inventory"
)
VERIFIER_MODULE = (
    "analysis_scripts.verify_noncombat_card_acceptance_empirical_successor"
)


def _control():
    return importlib.import_module(CONTROL_MODULE)


def _verifier():
    return importlib.import_module(VERIFIER_MODULE)


def _isolated(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", "-c", script],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )


def test_control_and_verifier_import_without_runtime_torch_native_or_consumed_runner():
    forbidden = (
        "torch",
        "sts_lightspeed_noncombat_adapter",
        "analysis_scripts.noncombat_simulator_adapter",
        RUNTIME_MODULE,
        SEED_MODULE,
        "analysis_scripts.noncombat_cross_fitted_hierarchical_learning_experiment",
        "analysis_scripts.noncombat_cross_fitted_hierarchical_learning_runtime",
        "analysis_scripts.verify_noncombat_cross_fitted_hierarchical_learning_experiment",
    )
    script = f"""
import builtins
import json
import sys
sys.path.insert(0, {str(ROOT)!r})
forbidden = {forbidden!r}
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if any(name == item or name.startswith(item + '.') for item in forbidden):
        raise AssertionError('forbidden import: ' + name)
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
import {CONTROL_MODULE} as control
import {VERIFIER_MODULE} as verifier
control.experiment_contract()
verifier.verifier_contract()
print(json.dumps(sorted(name for name in forbidden if name in sys.modules)))
"""

    completed = _isolated(script)

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == []


def test_verifier_import_does_not_import_producer_runtime_seed_or_torch():
    forbidden = (
        CONTROL_MODULE,
        RUNTIME_MODULE,
        SEED_MODULE,
        "torch",
        "sts_lightspeed_noncombat_adapter",
        "analysis_scripts.noncombat_simulator_adapter",
    )
    script = f"""
import builtins
import json
import sys
sys.path.insert(0, {str(ROOT)!r})
forbidden = {forbidden!r}
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if any(name == item or name.startswith(item + '.') for item in forbidden):
        raise AssertionError('forbidden import: ' + name)
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
import {VERIFIER_MODULE} as verifier
verifier.verifier_contract()
print(json.dumps(sorted(name for name in forbidden if name in sys.modules)))
"""

    completed = _isolated(script)

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == []


def test_control_contract_and_metadata_are_fixed_and_caller_mutation_safe():
    control = _control()
    contract = control.experiment_contract()
    metadata = control.expected_runtime_metadata()
    dependencies = control.module_dependency_inventory()

    assert contract["schema_version"] == (
        "noncombat-card-acceptance-empirical-successor-contract-v1"
    )
    assert contract["algorithm"] == {
        "conditional_entropy_coefficient": 0.01,
        "discount": 1.0,
        "family_entropy_coefficient": 0.01,
        "gradient_norm_ceiling": 1.0,
        "learning_rate": 0.001,
        "model_seed": 0,
        "optimizer": "adam",
        "optimizer_amsgrad": False,
        "optimizer_betas": [0.9, 0.999],
        "optimizer_eps": 1e-8,
        "optimizer_weight_decay": 0.0,
    }
    assert contract["cohorts"] == {
        "canary_pairs": 128,
        "holdout_pairs": 512,
        "training_chunks": 8,
        "training_pairs": 512,
        "training_pairs_per_chunk": 64,
    }
    assert contract["limits"]["max_environment_accesses"] == 2560
    assert contract["limits"]["max_training_optimizer_steps"] == 16
    assert contract["limits"]["max_shadow_optimizer_steps"] == 1
    assert set(contract["authority"].values()) == {False}
    assert metadata["schema_version"] == (
        "noncombat-card-acceptance-empirical-successor-runtime-metadata-v1"
    )
    assert tuple(row["role"] for row in dependencies["modules"]) == (
        "control_plane",
        "torch_runtime",
        "seed_inventory",
        "independent_verifier",
    )

    contract["algorithm"]["learning_rate"] = 9.0
    metadata["optimizer"]["learning_rate"] = 9.0
    dependencies["modules"].clear()

    assert control.experiment_contract()["algorithm"]["learning_rate"] == 0.001
    assert control.expected_runtime_metadata()["optimizer"]["learning_rate"] == 0.001
    assert len(control.module_dependency_inventory()["modules"]) == 4


def test_contract_cli_is_canonical_and_repeatable_in_fresh_processes():
    control = _control()
    script = (
        f"import sys;sys.path.insert(0,{str(ROOT)!r});"
        f"import {CONTROL_MODULE} as module;"
        "raise SystemExit(module.main(['contract']))"
    )

    first = _isolated(script)
    second = _isolated(script)

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert first.stdout.encode("ascii") == control.canonical_json_bytes(
        control.experiment_contract()
    )
    assert second.stdout == first.stdout


def test_verifier_contract_is_independent_and_keeps_all_empirical_authority_false():
    verifier = _verifier()

    contract = verifier.verifier_contract()

    assert contract["schema_version"] == (
        "noncombat-card-acceptance-empirical-successor-verifier-contract-v1"
    )
    assert contract["producer_imported"] is False
    assert contract["runtime_imported"] is False
    assert contract["seed_inventory_imported"] is False
    assert set(contract["authority"].values()) == {False}
