from __future__ import annotations

import importlib
import hashlib
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
    assert metadata["baseline"] == {
        "feature_dim": 128,
        "fit_trajectories_per_fold": 48,
        "fold_count": 4,
        "held_out_trajectories_per_fold": 16,
        "prediction_bounds": [0.0, 3.0],
        "ridge_coefficient": 0.001,
        "ridge_residual_atol": 1e-9,
        "ridge_residual_rtol": 1e-9,
        "scale": 1.0,
        "solver": "cpu-float64-cholesky-v1",
        "source_dim": 1024,
        "trajectory_weighting": "equal-trajectory-mean-squared-error-v1",
    }
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


def test_source_inventory_binds_closed_modules_and_transitive_dependencies(tmp_path):
    control = _control()
    declaration = control.module_dependency_inventory()
    expected_dependencies = (
        "analysis_scripts_package",
        "action_family_distribution",
        "advantage_attribution",
        "card_acceptance_objective",
        "card_acceptance_policy",
        "candidate_feature_projection",
        "formal_reward",
        "hierarchical_objective",
        "policy_input",
        "simulator_adapter",
        "simulator_rl_policy_projection",
        "state_conditioned_ranker",
    )

    assert tuple(row["role"] for row in declaration["modules"]) == (
        "control_plane",
        "torch_runtime",
        "seed_inventory",
        "independent_verifier",
    )
    assert tuple(row["name"] for row in declaration["public_dependencies"]) == (
        expected_dependencies
    )
    for index, row in enumerate(
        declaration["modules"] + declaration["public_dependencies"]
    ):
        path = tmp_path / row["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"source-{index}\n".encode("ascii"))

    first = control.build_source_inventory(tmp_path)
    second = control.build_source_inventory(tmp_path)

    assert first == second
    assert first["schema_version"] == (
        "noncombat-card-acceptance-empirical-successor-source-inventory-v1"
    )
    body = {key: value for key, value in first.items() if key != "inventory_sha256"}
    assert first["inventory_sha256"] == control.canonical_json_sha256(body)
    assert all(row["size_bytes"] > 0 for row in first["modules"])
    changed_path = tmp_path / declaration["public_dependencies"][0]["path"]
    changed_path.write_bytes(b"changed\n")
    assert control.build_source_inventory(tmp_path) != first


def test_experiment_configuration_identity_binds_canonical_contract():
    control = _control()
    contract = control.experiment_contract()

    identity = control.experiment_configuration_identity()

    assert identity == {
        "canonical_size_bytes": len(control.canonical_json_bytes(contract)),
        "contract_sha256": control.canonical_json_sha256(contract),
        "schema_version": (
            "noncombat-card-acceptance-empirical-successor-config-identity-v1"
        ),
    }
    contract["algorithm"]["learning_rate"] = 99.0
    assert control.experiment_configuration_identity() == identity


def test_native_config_and_checkpoint_bindings_are_inert(tmp_path):
    control = _control()
    native_module = tmp_path / "native" / "adapter.pyd"
    native_module.parent.mkdir(parents=True)
    native_module.write_bytes(b"synthetic-native")
    dll_directory = tmp_path / "native" / "bin"
    dll_directory.mkdir()
    module_sha256 = hashlib.sha256(native_module.read_bytes()).hexdigest()
    provenance = {
        "build": {
            "adapter_api_version": "sts-lightspeed-noncombat-adapter-v3",
            "compiler": "synthetic",
        },
        "module_sha256": module_sha256,
    }
    native = control.build_native_identity(
        module_path=native_module,
        dll_directories=[dll_directory],
        provenance=provenance,
    )

    config = tmp_path / "config.properties"
    config.write_bytes(b'command="synthetic"\n')
    checkpoints = tmp_path / "checkpoints"
    (checkpoints / "nested").mkdir(parents=True)
    (checkpoints / "model-a.pth").write_bytes(b"model-a")
    (checkpoints / "nested" / "model-b.pth").write_bytes(b"model-b")
    first = control.build_isolation_identity(
        communication_mod_config=config,
        production_checkpoint_root=checkpoints,
    )
    second = control.build_isolation_identity(
        communication_mod_config=config,
        production_checkpoint_root=checkpoints,
    )

    assert native["module"] == control.external_file_binding(native_module)
    assert native["provenance_sha256"] == control.canonical_json_sha256(provenance)
    assert native["dll_directories"] == [dll_directory.resolve().as_posix()]
    assert first == second
    assert first["communication_mod_config"] == control.external_file_binding(config)
    assert first["production_checkpoints"]["file_count"] == 2
    (checkpoints / "nested" / "model-b.pth").write_bytes(b"changed")
    assert control.build_isolation_identity(
        communication_mod_config=config,
        production_checkpoint_root=checkpoints,
    ) != first


def test_runtime_import_is_explicitly_deferred():
    control = _control()
    imported = []
    sentinel = object()

    loaded = control._load_runtime_module(
        module_importer=lambda name: (imported.append(name), sentinel)[1]
    )

    assert loaded is sentinel
    assert imported == [RUNTIME_MODULE]
