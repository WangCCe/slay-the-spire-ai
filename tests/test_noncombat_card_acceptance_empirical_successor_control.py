from __future__ import annotations

import importlib
import copy
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import struct
import sys

import pytest


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


def test_source_inventory_binds_closed_modules_and_transitive_dependencies(
    tmp_path, monkeypatch
):
    control = _control()
    declaration = control.module_dependency_inventory()
    preservation = {
        "artifact_file_count": 13,
        "artifact_root_count": 3,
        "manifest_sha256": "9" * 64,
        "source_file_count": 5,
        "verified": True,
    }
    observations = []
    monkeypatch.setattr(
        control,
        "verify_consumed_evidence_preservation",
        lambda repo_root: (observations.append(Path(repo_root)), preservation)[1],
    )
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
        "noncombat-card-acceptance-empirical-successor-source-inventory-v2"
    )
    assert first["consumed_evidence_preservation"] == preservation
    assert observations == [tmp_path.resolve(), tmp_path.resolve()]
    body = {key: value for key, value in first.items() if key != "inventory_sha256"}
    assert first["inventory_sha256"] == control.canonical_json_sha256(body)
    assert all(row["size_bytes"] > 0 for row in first["modules"])
    changed_path = tmp_path / declaration["public_dependencies"][0]["path"]
    changed_path.write_bytes(b"changed\n")
    assert control.build_source_inventory(tmp_path) != first


def _preservation_json_payload(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _preservation_file_row(path, payload):
    git_blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
    return {
        "git_blob_oid": hashlib.sha1(git_blob).hexdigest(),
        "path": path,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _preservation_git(repo, *args):
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _write_preservation_fixture(tmp_path, monkeypatch, control):
    source_paths = ("consumed/source_a.py", "consumed/source_b.py")
    artifact_file_paths = ("reports/consumed.json",)
    artifact_root_paths = ("reports/consumed-root",)
    source_payloads = (b"VALUE = 1\n", b"OTHER = 2\n")
    artifact_payload = b'{"consumed":true}\n'
    rooted_payload = b"fixed-evidence\n"

    for path, payload in zip(source_paths, source_payloads, strict=True):
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    artifact_target = tmp_path / artifact_file_paths[0]
    artifact_target.parent.mkdir(parents=True, exist_ok=True)
    artifact_target.write_bytes(artifact_payload)
    rooted_target = tmp_path / artifact_root_paths[0] / "nested" / "evidence.bin"
    rooted_target.parent.mkdir(parents=True, exist_ok=True)
    rooted_target.write_bytes(rooted_payload)

    _preservation_git(tmp_path, "init", "-q")
    _preservation_git(tmp_path, "config", "user.email", "synthetic@example.invalid")
    _preservation_git(tmp_path, "config", "user.name", "Synthetic Test")
    _preservation_git(
        tmp_path,
        "add",
        "consumed",
        "reports/consumed.json",
        "reports/consumed-root",
    )
    _preservation_git(tmp_path, "commit", "-q", "-m", "synthetic baseline")
    baseline_commit = _preservation_git(tmp_path, "rev-parse", "HEAD")
    baseline_tree = _preservation_git(tmp_path, "rev-parse", "HEAD^{tree}")

    entries = [
        {"path": "nested", "type": "directory"},
        {
            "path": "nested/evidence.bin",
            "sha256": hashlib.sha256(rooted_payload).hexdigest(),
            "size_bytes": len(rooted_payload),
            "type": "file",
        },
    ]
    baseline = {
        "remote_commit": baseline_commit,
        "remote_ref": "origin/master",
        "source_commit": baseline_commit,
        "source_tree": baseline_tree,
        "tracked_worktree_clean": True,
    }
    body = {
        "artifact_files": [
            _preservation_file_row(artifact_file_paths[0], artifact_payload)
        ],
        "artifact_roots": [
            {
                "directory_count": 1,
                "directory_inventory_sha256": hashlib.sha256(
                    _preservation_json_payload(entries)
                ).hexdigest(),
                "entries": entries,
                "file_count": 1,
                "root": artifact_root_paths[0],
                "total_file_bytes": len(rooted_payload),
            }
        ],
        "baseline": baseline,
        "closed_artifact_file_paths": list(artifact_file_paths),
        "closed_artifact_root_paths": list(artifact_root_paths),
        "closed_source_paths": list(source_paths),
        "created_at_utc": "2026-08-10T00:00:00+00:00",
        "directory_inventory_schema": "sorted-relative-path-type-rows-v1",
        "manifest_id": "synthetic-preservation-v1",
        "schema_version": "synthetic-preservation-schema-v1",
        "source_files": [
            _preservation_file_row(path, payload)
            for path, payload in zip(source_paths, source_payloads, strict=True)
        ],
    }
    manifest = {
        **body,
        "manifest_sha256": hashlib.sha256(
            _preservation_json_payload(body)
        ).hexdigest(),
    }
    manifest_path = tmp_path / "reports" / "preservation.json"
    manifest_path.write_bytes(_preservation_json_payload(manifest) + b"\n")
    _preservation_git(tmp_path, "add", "reports/preservation.json")
    _preservation_git(tmp_path, "commit", "-q", "-m", "publish preservation")
    publication_commit = _preservation_git(tmp_path, "rev-parse", "HEAD")
    publication_tree = _preservation_git(tmp_path, "rev-parse", "HEAD^{tree}")
    _preservation_git(
        tmp_path,
        "update-ref",
        "refs/remotes/origin/master",
        publication_commit,
    )

    monkeypatch.setattr(
        control,
        "CONSUMED_EVIDENCE_PRESERVATION_SCHEMA_VERSION",
        manifest["schema_version"],
    )
    monkeypatch.setattr(
        control,
        "CONSUMED_EVIDENCE_PRESERVATION_MANIFEST_ID",
        manifest["manifest_id"],
    )
    monkeypatch.setattr(
        control,
        "CONSUMED_EVIDENCE_PRESERVATION_MANIFEST_PATH",
        "reports/preservation.json",
    )
    monkeypatch.setattr(
        control,
        "CONSUMED_EVIDENCE_PRESERVATION_MANIFEST_SHA256",
        manifest["manifest_sha256"],
    )
    monkeypatch.setattr(
        control,
        "CONSUMED_EVIDENCE_PRESERVATION_BASELINE",
        baseline,
    )
    monkeypatch.setattr(
        control,
        "CONSUMED_EVIDENCE_PRESERVATION_SOURCE_PATHS",
        source_paths,
    )
    monkeypatch.setattr(
        control,
        "CONSUMED_EVIDENCE_PRESERVATION_ARTIFACT_FILE_PATHS",
        artifact_file_paths,
    )
    monkeypatch.setattr(
        control,
        "CONSUMED_EVIDENCE_PRESERVATION_ARTIFACT_ROOT_PATHS",
        artifact_root_paths,
    )
    monkeypatch.setattr(
        control,
        "CONSUMED_EVIDENCE_PRESERVATION_PUBLICATION_COMMIT",
        publication_commit,
        raising=False,
    )
    monkeypatch.setattr(
        control,
        "CONSUMED_EVIDENCE_PRESERVATION_PUBLICATION_TREE",
        publication_tree,
        raising=False,
    )
    return manifest_path


def _rewrite_preservation_manifest(path, monkeypatch, control, manifest):
    body = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    manifest["manifest_sha256"] = hashlib.sha256(
        _preservation_json_payload(body)
    ).hexdigest()
    path.write_bytes(_preservation_json_payload(manifest) + b"\n")
    monkeypatch.setattr(
        control,
        "CONSUMED_EVIDENCE_PRESERVATION_MANIFEST_SHA256",
        manifest["manifest_sha256"],
    )
    repo = path.parents[1]
    _preservation_git(repo, "add", "-A")
    _preservation_git(repo, "commit", "-q", "--amend", "--no-edit")
    publication_commit = _preservation_git(repo, "rev-parse", "HEAD")
    publication_tree = _preservation_git(repo, "rev-parse", "HEAD^{tree}")
    _preservation_git(
        repo,
        "update-ref",
        "refs/remotes/origin/master",
        publication_commit,
    )
    monkeypatch.setattr(
        control,
        "CONSUMED_EVIDENCE_PRESERVATION_PUBLICATION_COMMIT",
        publication_commit,
        raising=False,
    )
    monkeypatch.setattr(
        control,
        "CONSUMED_EVIDENCE_PRESERVATION_PUBLICATION_TREE",
        publication_tree,
        raising=False,
    )


def test_reviewed_consumed_evidence_manifest_reobserves_current_repository():
    control = _control()

    result = control.verify_consumed_evidence_preservation(ROOT)

    assert result == {
        "artifact_file_count": 13,
        "artifact_root_count": 3,
        "baseline_source_commit": (
            "6f620434ba962216fb4cab11bd4bb0a8aefc4674"
        ),
        "baseline_source_tree": (
            "ad7c1c4f18af90966577c01a2851444ff66c66e1"
        ),
        "manifest_sha256": (
            "6d5ec05d51a53a73c053e1591b3fb85d746c06efdc5c1b96f82a176e3de4e992"
        ),
        "publication_commit": (
            "df706481140f62fd5b08aaa370d27b27360430f2"
        ),
        "publication_tree": "a04b20e870bad125d090f4e1b2ad90b438536e60",
        "pushed_remote_ref": "origin/master",
        "source_file_count": 5,
        "verified": True,
    }


def test_consumed_evidence_preservation_accepts_exact_synthetic_fixture(
    tmp_path, monkeypatch
):
    control = _control()
    _write_preservation_fixture(tmp_path, monkeypatch, control)

    result = control.verify_consumed_evidence_preservation(tmp_path)

    assert result["verified"] is True
    assert result["source_file_count"] == 2
    assert result["artifact_file_count"] == 1
    assert result["artifact_root_count"] == 1


def test_consumed_evidence_preservation_requires_reviewed_git_publication(
    tmp_path, monkeypatch
):
    control = _control()
    _write_preservation_fixture(tmp_path, monkeypatch, control)
    (tmp_path / ".git").rename(tmp_path / "git-disabled")

    with pytest.raises(control.SuccessorControlError, match="Git|git|publication"):
        control.verify_consumed_evidence_preservation(tmp_path)


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        ("changed", "source.*mismatch"),
        ("missing", "missing"),
        ("extra", "artifact root.*mismatch"),
        ("reordered", "closed source"),
        ("successor_import", "imports successor"),
        ("successor_dynamic_import", "imports successor"),
        ("successor_nested_dynamic_import", "imports successor"),
        ("successor_getattr_dynamic_import", "imports successor"),
        ("successor_getattr_alias_dynamic_import", "imports successor"),
        ("successor_importlib_module_alias", "imports successor"),
    ),
)
def test_consumed_evidence_preservation_rejects_closed_mutation_matrix(
    tmp_path, monkeypatch, mutation, message
):
    control = _control()
    manifest_path = _write_preservation_fixture(tmp_path, monkeypatch, control)
    manifest = json.loads(manifest_path.read_bytes())

    if mutation == "changed":
        (tmp_path / manifest["closed_source_paths"][0]).write_bytes(b"VALUE = 9\n")
    elif mutation == "missing":
        (tmp_path / manifest["closed_artifact_file_paths"][0]).unlink()
    elif mutation == "extra":
        (tmp_path / manifest["closed_artifact_root_paths"][0] / "extra.bin").write_bytes(
            b"extra\n"
        )
    elif mutation == "reordered":
        manifest["closed_source_paths"].reverse()
        manifest["source_files"].reverse()
        _rewrite_preservation_manifest(
            manifest_path, monkeypatch, control, manifest
        )
    elif mutation in {
        "successor_import",
        "successor_dynamic_import",
        "successor_nested_dynamic_import",
        "successor_getattr_dynamic_import",
        "successor_getattr_alias_dynamic_import",
        "successor_importlib_module_alias",
    }:
        path = tmp_path / manifest["closed_source_paths"][0]
        if mutation == "successor_import":
            payload = (
                b"import analysis_scripts."
                b"noncombat_card_acceptance_empirical_successor_runtime\n"
            )
        elif mutation == "successor_dynamic_import":
            payload = (
                b"import importlib\n"
                b"importlib.import_module(\n"
                b"    'analysis_scripts."
                b"noncombat_card_acceptance_empirical_successor_runtime'\n"
                b")\n"
            )
        elif mutation == "successor_nested_dynamic_import":
            payload = (
                b"def load_successor():\n"
                b"    from importlib import import_module as load\n"
                b"    return load(\n"
                b"        'analysis_scripts."
                b"noncombat_card_acceptance_empirical_successor_runtime'\n"
                b"    )\n"
            )
        elif mutation == "successor_getattr_dynamic_import":
            payload = (
                b"import importlib\n"
                b"getattr(importlib, 'import_module')(\n"
                b"    'analysis_scripts."
                b"noncombat_card_acceptance_empirical_successor_runtime'\n"
                b")\n"
            )
        elif mutation == "successor_getattr_alias_dynamic_import":
            payload = (
                b"import importlib\n"
                b"lookup = getattr\n"
                b"loader = lookup(importlib, 'import_module')\n"
                b"loader(\n"
                b"    'analysis_scripts."
                b"noncombat_card_acceptance_empirical_successor_runtime'\n"
                b")\n"
            )
        else:
            payload = (
                b"import importlib\n"
                b"module_loader = importlib\n"
                b"loader = module_loader.import_module\n"
                b"loader(\n"
                b"    'analysis_scripts."
                b"noncombat_card_acceptance_empirical_successor_runtime'\n"
                b")\n"
            )
        path.write_bytes(payload)
        manifest["source_files"][0] = _preservation_file_row(
            manifest["closed_source_paths"][0], payload
        )
        _rewrite_preservation_manifest(
            manifest_path, monkeypatch, control, manifest
        )
    else:
        raise AssertionError(mutation)

    with pytest.raises(control.SuccessorControlError, match=message):
        control.verify_consumed_evidence_preservation(tmp_path)


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


def _stage_prerequisites(stage: str) -> dict[str, str]:
    if stage == "inventory":
        return {}
    if stage == "inventory-verification":
        return {
            "inventory_authorization_sha256": "2" * 64,
            "inventory_file_sha256": "3" * 64,
            "inventory_launch_observation_sha256": "4" * 64,
            "inventory_receipt_sha256": "5" * 64,
            "inventory_request_sha256": "1" * 64,
            "inventory_sha256": "6" * 64,
        }
    if stage == "training":
        return {"registration_sha256": "c" * 64}
    if stage == "canary":
        return {
            "frozen_seal_sha256": "d" * 64,
            "registration_sha256": "c" * 64,
            "training_terminal_sha256": "e" * 64,
        }
    if stage == "holdout":
        return {
            "canary_terminal_sha256": "f" * 64,
            "frozen_seal_sha256": "d" * 64,
            "registration_sha256": "c" * 64,
        }
    raise AssertionError(stage)


def _stage_request(control, stage: str):
    return control.build_stage_request(
        stage=stage,
        request_id=f"card-acceptance-20260809-{stage}-request-v1",
        source_commit="a" * 40,
        source_inventory_sha256="b" * 64,
        configuration_identity=control.experiment_configuration_identity(),
        prerequisite_bindings=_stage_prerequisites(stage),
        output_root=f"D:/synthetic/card-acceptance-successor/{stage}",
    )


def test_stage_requests_have_exact_disjoint_authority_and_resource_maps():
    control = _control()
    expected_enabled = {
        "inventory": {
            "cohort_materialization",
            "repository_evidence_read",
            "seed_discovery",
        },
        "inventory-verification": {
            "repository_evidence_read",
            "seed_discovery",
        },
        "training": {
            "checkpoint_publication",
            "environment_construction",
            "evidence_publication",
            "experiment_model_loading",
            "model_fitting",
            "native_loading",
            "seed_access",
            "training",
        },
        "canary": {
            "environment_construction",
            "evaluation",
            "evidence_publication",
            "experiment_model_loading",
            "native_loading",
            "seed_access",
            "shadow_optimizer_step",
        },
        "holdout": {
            "environment_construction",
            "evaluation",
            "evidence_publication",
            "experiment_model_loading",
            "native_loading",
            "seed_access",
        },
    }

    for stage in (
        "inventory",
        "inventory-verification",
        "training",
        "canary",
        "holdout",
    ):
        request = _stage_request(control, stage)
        assert control.validate_stage_request(request) == request
        assert request["stage"] == stage
        assert set(request["downstream_authority"].values()) == {False}
        assert {
            name for name, enabled in request["execution_authority"].items() if enabled
        } == expected_enabled[stage]
        assert request["request_sha256"] == control.canonical_json_sha256(
            {key: value for key, value in request.items() if key != "request_sha256"}
        )

    assert _stage_request(control, "training")["resources"] == {
        "max_charged_seconds": 28_800.0,
        "max_environment_accesses": 1_024,
        "max_optimizer_steps": 16,
        "max_pairs": 512,
    }
    assert _stage_request(control, "inventory-verification")["resources"] == {
        "max_cli_completion_bytes": 2_048,
        "max_inventory_bytes": 64 * 1024 * 1024,
    }
    assert _stage_request(control, "canary")["resources"] == {
        "max_environment_accesses": 512,
        "max_pairs": 128,
        "max_shadow_optimizer_steps": 1,
    }
    assert _stage_request(control, "holdout")["resources"] == {
        "bootstrap_resamples": 10_000,
        "max_environment_accesses": 1_024,
        "max_pairs": 512,
    }


def test_stage_request_validation_rejects_cross_stage_or_authority_mutation():
    control = _control()
    request = _stage_request(control, "canary")

    changed = json.loads(json.dumps(request))
    changed["execution_authority"]["training"] = True
    changed["request_sha256"] = control.canonical_json_sha256(
        {key: value for key, value in changed.items() if key != "request_sha256"}
    )
    with pytest.raises(control.SuccessorControlError, match="request|authority"):
        control.validate_stage_request(changed)

    changed = json.loads(json.dumps(request))
    changed["prerequisite_bindings"].pop("frozen_seal_sha256")
    changed["request_sha256"] = control.canonical_json_sha256(
        {key: value for key, value in changed.items() if key != "request_sha256"}
    )
    with pytest.raises(control.SuccessorControlError, match="prerequisite|request"):
        control.validate_stage_request(changed)


def test_inventory_verification_request_rejects_broadened_authority():
    control = _control()
    request = _stage_request(control, "inventory-verification")
    changed = json.loads(json.dumps(request))
    changed["execution_authority"]["model_loading"] = True
    changed["request_sha256"] = control.canonical_json_sha256(
        {key: value for key, value in changed.items() if key != "request_sha256"}
    )

    with pytest.raises(control.SuccessorControlError, match="request|authority"):
        control.validate_stage_request(changed)


def test_stage_authorization_binds_exact_reviewed_request_and_approval_record():
    control = _control()
    request = _stage_request(control, "training")

    authorization = control.build_stage_authorization(
        request=request,
        authorization_id="card-acceptance-20260809-training-authorization-v1",
        request_review_sha256="1" * 64,
        approval_record_sha256="2" * 64,
    )

    assert control.validate_stage_authorization(authorization, request) == (
        authorization
    )
    assert authorization["request_sha256"] == request["request_sha256"]
    assert authorization["execution_authority"] == request["execution_authority"]
    assert set(authorization["downstream_authority"].values()) == {False}
    changed = json.loads(json.dumps(authorization))
    changed["request_sha256"] = "3" * 64
    changed["authorization_sha256"] = control.canonical_json_sha256(
        {
            key: value
            for key, value in changed.items()
            if key != "authorization_sha256"
        }
    )
    with pytest.raises(control.SuccessorControlError, match="authorization|request"):
        control.validate_stage_authorization(changed, request)


def test_request_and_authorization_cli_render_and_validate_canonical_bytes(
    tmp_path, capsys
):
    control = _control()
    definition = {
        "configuration_identity": control.experiment_configuration_identity(),
        "output_root": "D:/synthetic/card-acceptance-successor/inventory",
        "prerequisite_bindings": {},
        "request_id": "card-acceptance-20260809-inventory-request-v1",
        "source_commit": "a" * 40,
        "source_inventory_sha256": "b" * 64,
        "stage": "inventory",
    }
    definition_path = tmp_path / "request-definition.json"
    definition_path.write_text(json.dumps(definition), encoding="utf-8")

    assert control.main(["render-request", "--definition", str(definition_path)]) == 0
    request_bytes = capsys.readouterr().out.encode("ascii")
    request = json.loads(request_bytes)
    assert request_bytes == control.canonical_json_bytes(request)
    request_path = tmp_path / "request.json"
    request_path.write_bytes(request_bytes)
    assert control.main(["validate-request", "--request", str(request_path)]) == 0
    assert capsys.readouterr().out.encode("ascii") == request_bytes

    authorization_definition = {
        "approval_record_sha256": "2" * 64,
        "authorization_id": (
            "card-acceptance-20260809-inventory-authorization-v1"
        ),
        "request_review_sha256": "1" * 64,
    }
    authorization_definition_path = tmp_path / "authorization-definition.json"
    authorization_definition_path.write_text(
        json.dumps(authorization_definition), encoding="utf-8"
    )
    assert control.main(
        [
            "render-authorization",
            "--request",
            str(request_path),
            "--definition",
            str(authorization_definition_path),
        ]
    ) == 0
    authorization_bytes = capsys.readouterr().out.encode("ascii")
    authorization_path = tmp_path / "authorization.json"
    authorization_path.write_bytes(authorization_bytes)
    assert control.main(
        [
            "validate-authorization",
            "--request",
            str(request_path),
            "--authorization",
            str(authorization_path),
        ]
    ) == 0
    assert capsys.readouterr().out.encode("ascii") == authorization_bytes


def test_private_execution_context_validates_once_and_owns_immutable_values():
    control = _control()
    registration_body = {
        "registration_id": "card-acceptance-20260809-registration-v1",
        "schema_version": "synthetic-registration-v1",
    }
    registration = {
        **registration_body,
        "registration_sha256": control.canonical_json_sha256(registration_body),
    }
    request = control.build_stage_request(
        stage="training",
        request_id="card-acceptance-20260809-training-request-v1",
        source_commit="a" * 40,
        source_inventory_sha256="b" * 64,
        configuration_identity=control.experiment_configuration_identity(),
        prerequisite_bindings={
            "registration_sha256": registration["registration_sha256"]
        },
        output_root="D:/synthetic/card-acceptance-successor/training",
    )
    authorization = control.build_stage_authorization(
        request=request,
        authorization_id="card-acceptance-20260809-training-authorization-v1",
        request_review_sha256="1" * 64,
        approval_record_sha256="2" * 64,
    )
    validations = []

    def validate_registration(value):
        validations.append(value)
        assert value["registration_sha256"] == control.canonical_json_sha256(
            {
                key: item
                for key, item in value.items()
                if key != "registration_sha256"
            }
        )
        return copy.deepcopy(dict(value))

    context = control._build_validated_execution_context(
        registration=registration,
        request=request,
        authorization=authorization,
        registration_validator=validate_registration,
    )
    registration["registration_id"] = "mutated"
    request["request_id"] = "mutated"
    authorization["authorization_id"] = "mutated"

    assert len(validations) == 1
    assert control._require_execution_context(context) is context
    assert context.registration is context.registration
    assert context.request is context.request
    assert context.authorization is context.authorization
    for operation in (
        "journal",
        "resource",
        "checkpoint",
        "stage",
        "rollback",
        "terminal",
    ):
        assert control._execution_context_for_operation(context, operation) is context
    assert len(validations) == 1
    assert context.registration["registration_id"] == (
        "card-acceptance-20260809-registration-v1"
    )
    assert context.request["request_id"].endswith("-training-request-v1")
    assert context.authorization["authorization_id"].endswith(
        "-training-authorization-v1"
    )
    with pytest.raises(TypeError, match="immutable"):
        context.registration["registration_id"] = "changed"
    with pytest.raises(TypeError, match="immutable"):
        context.request["execution_authority"]["training"] = False
    with pytest.raises(TypeError, match="immutable"):
        context.stage = "holdout"


def test_execution_context_rejects_rewrap_and_registration_binding_mismatch():
    control = _control()
    registration = {
        "registration_id": "card-acceptance-20260809-registration-v1",
        "registration_sha256": "9" * 64,
    }
    request = _stage_request(control, "training")
    authorization = control.build_stage_authorization(
        request=request,
        authorization_id="card-acceptance-20260809-training-authorization-v1",
        request_review_sha256="1" * 64,
        approval_record_sha256="2" * 64,
    )

    with pytest.raises(control.SuccessorControlError, match="registration"):
        control._build_validated_execution_context(
            registration=registration,
            request=request,
            authorization=authorization,
            registration_validator=lambda value: copy.deepcopy(dict(value)),
        )

    bound_registration = {
        **registration,
        "registration_sha256": request["prerequisite_bindings"][
            "registration_sha256"
        ],
    }
    context = control._build_validated_execution_context(
        registration=bound_registration,
        request=request,
        authorization=authorization,
        registration_validator=lambda value: copy.deepcopy(dict(value)),
    )
    with pytest.raises(control.SuccessorControlError, match="raw|context"):
        control._build_validated_execution_context(
            registration=context,
            request=request,
            authorization=authorization,
            registration_validator=lambda value: value,
        )


def _empirical_context(control, stage, *, registration_fields=None):
    registration = {
        "registration_id": "card-acceptance-20260809-registration-v1",
        "registration_sha256": "c" * 64,
    }
    if registration_fields is not None:
        registration.update(copy.deepcopy(dict(registration_fields)))
    request = _stage_request(control, stage)
    authorization = control.build_stage_authorization(
        request=request,
        authorization_id=f"card-acceptance-20260809-{stage}-authorization-v1",
        request_review_sha256="1" * 64,
        approval_record_sha256="2" * 64,
    )
    return control._build_validated_execution_context(
        registration=registration,
        request=request,
        authorization=authorization,
        registration_validator=lambda value: copy.deepcopy(dict(value)),
    )


def _training_context(control, *, registration_fields=None):
    return _empirical_context(
        control,
        "training",
        registration_fields=registration_fields,
    )


def test_execution_lease_binds_live_child_and_requires_dead_owner_recovery(tmp_path):
    control = _control()
    context = _training_context(control)
    output = tmp_path / "execution"
    observed_pids = []

    def alive(process_id):
        observed_pids.append(process_id)
        return process_id == 4242

    with control.ExecutionLease(
        output,
        context=context,
        child_process_id=4242,
        process_alive=alive,
    ) as lease:
        assert lease.held is True
        assert lease.owner["child_process_id"] == 4242
        with pytest.raises(control.SuccessorControlError, match="lease"):
            with control.ExecutionLease(
                output,
                context=context,
                child_process_id=4242,
                process_alive=alive,
            ):
                pass

    assert observed_pids == [4242]
    with pytest.raises(control.SuccessorControlError, match="recovery|lease"):
        with control.ExecutionLease(
            output,
            context=context,
            child_process_id=4243,
            process_alive=lambda _pid: False,
        ):
            pass
    with control.ExecutionLease(
        output,
        context=context,
        child_process_id=4243,
        process_alive=lambda process_id: process_id == 4243,
        allow_stale_reclaim=True,
    ) as reclaimed:
        assert reclaimed.reclaimed_owner["child_process_id"] == 4242


def test_journal_is_write_ahead_resources_are_monotonic_and_markers_write_once(
    tmp_path,
):
    control = _control()
    context = _training_context(control)
    output = tmp_path / "execution"
    clock_values = iter((100.0, 101.5, 102.0))

    with control.ExecutionLease(
        output,
        context=context,
        child_process_id=5150,
        process_alive=lambda process_id: process_id == 5150,
        clock=lambda: next(clock_values),
    ) as lease:
        control.initialize_access_journal(context, lease)
        control.initialize_resource_ledger(context, lease)
        observed = []

        def access():
            journal = control.load_access_journal(context, lease)
            observed.append(journal["debited_accesses"])
            return "episode-result"

        assert control.perform_journaled_environment_access(
            context,
            lease,
            seed=71_664,
            arm="candidate",
            purpose="training",
            access=access,
        ) == "episode-result"
        assert observed == [1]
        ledger = control.reconcile_resource_ledger(context, lease)
        assert ledger["resources"] == {
            "charged_seconds": 1.5,
            "environment_accesses": 1,
            "optimizer_steps": 0,
            "shadow_optimizer_steps": 0,
        }
        with pytest.raises(RuntimeError, match="synthetic access failure"):
            control.perform_journaled_environment_access(
                context,
                lease,
                seed=71_665,
                arm="control",
                purpose="training",
                access=lambda: (_ for _ in ()).throw(
                    RuntimeError("synthetic access failure")
                ),
            )
        assert control.load_access_journal(context, lease)["debited_accesses"] == 2
        assert control.reconcile_resource_ledger(context, lease)["resources"] == {
            "charged_seconds": 2.0,
            "environment_accesses": 2,
            "optimizer_steps": 0,
            "shadow_optimizer_steps": 0,
        }
        with pytest.raises(control.SuccessorControlError, match="monotonic"):
            control.advance_resource_ledger(
                context,
                lease,
                charged_seconds=1.0,
                environment_accesses=1,
                optimizer_steps=0,
                shadow_optimizer_steps=0,
                reason="invalid-decrease",
            )

        bootstrap = {"checkpoint_sha256": "4" * 64}
        first = control.publish_write_once_marker(
            context,
            lease,
            kind="bootstrap",
            payload=bootstrap,
        )
        assert control.publish_write_once_marker(
            context,
            lease,
            kind="bootstrap",
            payload=bootstrap,
        ) == first
        control.publish_write_once_marker(
            context,
            lease,
            kind="stage",
            payload={"stage": "training", "status": "started"},
        )
        with pytest.raises(control.SuccessorControlError, match="write-once|drift"):
            control.publish_write_once_marker(
                context,
                lease,
                kind="stage",
                payload={"stage": "training", "status": "changed"},
            )


def _complete_checkpoint_binding(chunk_index: int = 1):
    return {
        "checkpoint_sha256": "4" * 64,
        "completed_pairs": chunk_index * 64,
        "component_sha256": {
            "candidate_card_generator": "5" * 64,
            "candidate_model": "6" * 64,
            "candidate_noncard_generator": "7" * 64,
            "candidate_optimizer": "8" * 64,
            "control_card_generator": "9" * 64,
            "control_model": "a" * 64,
            "control_noncard_generator": "b" * 64,
            "control_optimizer": "c" * 64,
        },
        "next_chunk_index": chunk_index,
        "training_environment_accesses": chunk_index * 128,
        "training_optimizer_steps": chunk_index * 2,
    }


def _debit_complete_training_chunk(control, context, lease, start_seed=80_000):
    for seed in range(start_seed, start_seed + 64):
        for arm in ("candidate", "control"):
            control.perform_journaled_environment_access(
                context,
                lease,
                seed=seed,
                arm=arm,
                purpose="training",
                access=lambda: None,
            )


def test_pre_seed_setup_can_reopen_repeatedly_under_same_identity(tmp_path):
    control = _control()
    context = _training_context(control)
    with control.ExecutionLease(
        tmp_path / "execution",
        context=context,
        child_process_id=6100,
        process_alive=lambda process_id: process_id == 6100,
    ) as lease:
        control.initialize_access_journal(context, lease)
        control.initialize_resource_ledger(context, lease)

        first = control.classify_execution_reopen(context, lease)
        second = control.classify_execution_reopen(context, lease)

        assert first == second
        assert first["verdict"] == "pre_seed_setup_reopen"
        assert first["debited_accesses"] == 0


def test_only_one_complete_checkpoint_training_continuation_is_authorized(tmp_path):
    control = _control()
    context = _training_context(control)
    output = tmp_path / "execution"
    with control.ExecutionLease(
        output,
        context=context,
        child_process_id=6101,
        process_alive=lambda process_id: process_id == 6101,
    ) as lease:
        control.initialize_access_journal(context, lease)
        control.initialize_resource_ledger(context, lease)
        _debit_complete_training_chunk(control, context, lease)
        control.advance_resource_ledger(
            context,
            lease,
            charged_seconds=10.0,
            environment_accesses=128,
            optimizer_steps=2,
            shadow_optimizer_steps=0,
            reason="complete-training-chunk",
        )
        checkpoint = control.publish_complete_training_checkpoint(
            context,
            lease,
            binding=_complete_checkpoint_binding(),
        )

        eligibility = control.classify_execution_reopen(context, lease)
        continuation = control.authorize_training_continuation(
            context,
            lease,
        )

        assert eligibility["verdict"] == "complete_checkpoint_continuation"
        assert eligibility["checkpoint_sha256"] == checkpoint["binding"][
            "checkpoint_sha256"
        ]
        assert continuation["checkpoint_sha256"] == eligibility[
            "checkpoint_sha256"
        ]
        with pytest.raises(control.SuccessorControlError, match="continuation|used"):
            control.authorize_training_continuation(context, lease)


def test_partial_chunk_and_post_canary_reopen_fail_closed(tmp_path):
    control = _control()
    context = _training_context(control)
    partial_output = tmp_path / "partial"
    with control.ExecutionLease(
        partial_output,
        context=context,
        child_process_id=6102,
        process_alive=lambda process_id: process_id == 6102,
    ) as lease:
        control.initialize_access_journal(context, lease)
        control.initialize_resource_ledger(context, lease)
        for arm in ("candidate", "control"):
            control.perform_journaled_environment_access(
                context,
                lease,
                seed=90_000,
                arm=arm,
                purpose="training",
                access=lambda: None,
            )
        with pytest.raises(control.SuccessorControlError, match="partial|checkpoint"):
            control.classify_execution_reopen(context, lease)

    canary_output = tmp_path / "post-canary"
    with control.ExecutionLease(
        canary_output,
        context=context,
        child_process_id=6103,
        process_alive=lambda process_id: process_id == 6103,
    ) as lease:
        control.initialize_access_journal(context, lease)
        control.initialize_resource_ledger(context, lease)
        (canary_output / "stages").mkdir()
        (canary_output / "stages" / "canary.json").write_bytes(b"started\n")
        with pytest.raises(control.SuccessorControlError, match="canary|post"):
            control.classify_execution_reopen(context, lease)


def test_artifact_terminal_intent_terminal_and_manifest_close_in_order(tmp_path):
    control = _control()
    context = _training_context(control)
    output = tmp_path / "execution"
    clock_values = iter((100.0, 102.5))

    with control.ExecutionLease(
        output,
        context=context,
        child_process_id=6200,
        process_alive=lambda process_id: process_id == 6200,
        clock=lambda: next(clock_values),
    ) as lease:
        control.initialize_access_journal(context, lease)
        control.initialize_resource_ledger(context, lease)
        artifact = control.publish_managed_artifact(
            context,
            lease,
            relative_path="evidence/summary.json",
            payload=control.canonical_json_bytes({"synthetic": True}),
        )

        intent = control.publish_terminal_intent(
            context,
            lease,
            verdict="training_completed",
            details={"reason": "synthetic-source-only-test"},
        )
        prefix_paths = [
            row["path"] for row in intent["artifact_prefix"]["artifacts"]
        ]
        assert prefix_paths == sorted(prefix_paths)
        assert artifact in intent["artifact_prefix"]["artifacts"]
        assert control.ACCESS_JOURNAL_FILENAME in prefix_paths
        assert control.RESOURCE_LEDGER_FILENAME in prefix_paths
        assert intent["resource_prefix"]["resources"]["charged_seconds"] == 2.5
        with pytest.raises(control.SuccessorControlError, match="terminal|closed"):
            control.publish_managed_artifact(
                context,
                lease,
                relative_path="evidence/late.json",
                payload=b"late\n",
            )

        terminal = control.publish_terminal_document(
            context,
            lease,
            terminal_intent=intent,
        )
        manifest = control.publish_artifact_manifest(
            context,
            lease,
            terminal_document=terminal,
        )

        assert terminal["terminal_intent_sha256"] == intent[
            "terminal_intent_sha256"
        ]
        assert manifest["terminal_sha256"] == terminal["terminal_sha256"]
        manifest_paths = [
            row["path"] for row in manifest["artifact_inventory"]["artifacts"]
        ]
        assert control.TERMINAL_INTENT_FILENAME in manifest_paths
        assert control.TERMINAL_FILENAME in manifest_paths
        assert control.MANIFEST_FILENAME not in manifest_paths
        assert (output / control.MANIFEST_FILENAME).read_bytes() == (
            control.canonical_json_bytes(manifest)
        )


def test_terminal_publication_rejects_incomplete_order_and_prefix_drift(tmp_path):
    control = _control()
    context = _training_context(control)
    output = tmp_path / "execution"
    clock_values = iter((200.0, 201.0))

    with control.ExecutionLease(
        output,
        context=context,
        child_process_id=6201,
        process_alive=lambda process_id: process_id == 6201,
        clock=lambda: next(clock_values),
    ) as lease:
        control.initialize_access_journal(context, lease)
        control.initialize_resource_ledger(context, lease)
        artifact_path = output / "evidence" / "summary.json"
        control.publish_managed_artifact(
            context,
            lease,
            relative_path="evidence/summary.json",
            payload=b'{"value":1}\n',
        )

        with pytest.raises(control.SuccessorControlError, match="intent|order"):
            control.publish_terminal_document(context, lease)
        assert not (output / control.TERMINAL_FILENAME).exists()

        intent = control.publish_terminal_intent(
            context,
            lease,
            verdict="training_failed",
            details={"reason": "synthetic"},
        )
        with pytest.raises(control.SuccessorControlError, match="terminal|order"):
            control.publish_artifact_manifest(context, lease)
        assert not (output / control.MANIFEST_FILENAME).exists()

        artifact_path.write_bytes(b'{"value":2}\n')
        with pytest.raises(control.SuccessorControlError, match="prefix|drift"):
            control.publish_terminal_document(
                context,
                lease,
                terminal_intent=intent,
            )
        assert artifact_path.read_bytes() == b'{"value":2}\n'
        assert not (output / control.TERMINAL_FILENAME).exists()


def test_existing_drift_and_ambiguous_staging_fail_without_repair(tmp_path):
    control = _control()
    context = _training_context(control)
    output = tmp_path / "execution"

    with control.ExecutionLease(
        output,
        context=context,
        child_process_id=6202,
        process_alive=lambda process_id: process_id == 6202,
    ) as lease:
        control.initialize_access_journal(context, lease)
        control.initialize_resource_ledger(context, lease)
        artifact_path = output / "evidence" / "summary.bin"
        artifact_path.parent.mkdir()
        artifact_path.write_bytes(b"original")

        with pytest.raises(control.SuccessorControlError, match="drift"):
            control.publish_managed_artifact(
                context,
                lease,
                relative_path="evidence/summary.bin",
                payload=b"replacement",
            )
        assert artifact_path.read_bytes() == b"original"

        staging = artifact_path.with_name(f".{artifact_path.name}.tmp")
        staging.write_bytes(b"ambiguous")
        with pytest.raises(control.SuccessorControlError, match="ambiguous staging"):
            control.publish_managed_artifact(
                context,
                lease,
                relative_path="evidence/summary.bin",
                payload=b"original",
            )
        assert artifact_path.read_bytes() == b"original"
        assert staging.read_bytes() == b"ambiguous"

        absent_path = output / "evidence" / "absent.bin"
        absent_staging = absent_path.with_name(f".{absent_path.name}.tmp")
        absent_staging.write_bytes(b"unowned")
        with pytest.raises(control.SuccessorControlError, match="ambiguous staging"):
            control.publish_managed_artifact(
                context,
                lease,
                relative_path="evidence/absent.bin",
                payload=b"new",
            )
        assert not absent_path.exists()
        assert absent_staging.read_bytes() == b"unowned"


def test_float64_evidence_is_deterministic_little_endian_gzip_metadata_only():
    control = _control()
    rows = ((1.0, -2.5), (3.25, 4.0))

    first, first_stored = control.encode_float64_evidence_artifact(
        relative_path="evidence/vectors.f64.gz",
        rows=rows,
    )
    second, second_stored = control.encode_float64_evidence_artifact(
        relative_path="evidence/vectors.f64.gz",
        rows=rows,
    )

    canonical = struct.pack("<dddd", 1.0, -2.5, 3.25, 4.0)
    assert first == second
    assert first_stored == second_stored
    assert first_stored[4:8] == b"\x00\x00\x00\x00"
    assert gzip.decompress(first_stored) == canonical
    assert first == {
        "artifact": {
            "encoding": "deterministic-gzip-v1",
            "path": "evidence/vectors.f64.gz",
            "stored_sha256": hashlib.sha256(first_stored).hexdigest(),
            "stored_size_bytes": len(first_stored),
            "uncompressed_sha256": hashlib.sha256(canonical).hexdigest(),
            "uncompressed_size_bytes": len(canonical),
        },
        "dtype": "float64",
        "element_count": 4,
        "endian": "little",
        "row_order": "row-major",
        "schema_version": (
            "noncombat-card-acceptance-empirical-successor-float64-evidence-v1"
        ),
        "shape": [2, 2],
    }
    assert "rows" not in first and "values" not in first


@pytest.mark.parametrize(
    "rows, message",
    (
        (((1.0,), (2.0, 3.0)), "rectangular"),
        (((float("nan"),),), "finite"),
        (((),), "column"),
    ),
)
def test_float64_evidence_rejects_invalid_geometry_and_values(rows, message):
    control = _control()

    with pytest.raises(control.SuccessorControlError, match=message):
        control.encode_float64_evidence_artifact(
            relative_path="evidence/invalid.f64.gz",
            rows=rows,
        )


def _budget_artifact(index, *, stored_size, uncompressed_size):
    return {
        "encoding": "deterministic-gzip-v1",
        "path": f"evidence/chunk-{index:02d}.bin.gz",
        "stored_sha256": f"{index + 1:064x}",
        "stored_size_bytes": stored_size,
        "uncompressed_sha256": f"{index + 101:064x}",
        "uncompressed_size_bytes": uncompressed_size,
    }


def _complete_budget_kwargs():
    mib = 1024 * 1024
    return {
        "artifacts": tuple(
            _budget_artifact(index, stored_size=32 * mib, uncompressed_size=64 * mib)
            for index in range(8)
        ),
        "decisions_per_episode": (500,) * 2_560,
        "training_environment_accesses": 1_024,
        "canary_environment_accesses": 512,
        "holdout_environment_accesses": 1_024,
        "candidate_optimizer_updates": 8,
        "control_optimizer_updates": 8,
        "shadow_optimizer_steps": 1,
        "charged_seconds": 28_800.0,
    }


def test_complete_resource_and_evidence_budget_accepts_exact_ceilings():
    control = _control()

    budget = control.validate_resource_and_evidence_budget(
        **_complete_budget_kwargs()
    )

    assert budget["artifact_count"] == 8
    assert budget["stored_size_bytes"] == 256 * 1024 * 1024
    assert budget["uncompressed_size_bytes"] == 512 * 1024 * 1024
    assert budget["total_environment_accesses"] == 2_560
    assert budget["training_optimizer_steps"] == 16
    assert budget["episode_count"] == 2_560


@pytest.mark.parametrize(
    "mutation, message",
    (
        ("artifact", "artifact"),
        ("stored", "stored"),
        ("uncompressed", "uncompressed"),
        ("decision", "decision"),
        ("training_access", "training environment"),
        ("canary_access", "canary environment"),
        ("holdout_access", "holdout environment"),
        ("candidate_update", "candidate optimizer"),
        ("control_update", "control optimizer"),
        ("shadow_update", "shadow optimizer"),
        ("charged_seconds", "charged seconds"),
    ),
)
def test_resource_and_evidence_budget_rejects_each_ceiling_plus_one(
    mutation,
    message,
):
    control = _control()
    kwargs = _complete_budget_kwargs()
    mib = 1024 * 1024
    if mutation == "artifact":
        kwargs["artifacts"] = (
            _budget_artifact(0, stored_size=64 * mib + 1, uncompressed_size=1),
        )
        kwargs["decisions_per_episode"] = ()
        kwargs["training_environment_accesses"] = 0
        kwargs["canary_environment_accesses"] = 0
        kwargs["holdout_environment_accesses"] = 0
    elif mutation == "stored":
        kwargs["artifacts"] = tuple(
            _budget_artifact(index, stored_size=64 * mib, uncompressed_size=1)
            for index in range(4)
        ) + (_budget_artifact(4, stored_size=1, uncompressed_size=1),)
    elif mutation == "uncompressed":
        kwargs["artifacts"] = tuple(
            _budget_artifact(index, stored_size=1, uncompressed_size=64 * mib)
            for index in range(8)
        ) + (_budget_artifact(8, stored_size=1, uncompressed_size=1),)
    elif mutation == "decision":
        kwargs["decisions_per_episode"] = (501,) + (500,) * 2_559
    elif mutation == "training_access":
        kwargs["training_environment_accesses"] += 1
        kwargs["decisions_per_episode"] += (1,)
    elif mutation == "canary_access":
        kwargs["canary_environment_accesses"] += 1
        kwargs["decisions_per_episode"] += (1,)
    elif mutation == "holdout_access":
        kwargs["holdout_environment_accesses"] += 1
        kwargs["decisions_per_episode"] += (1,)
    elif mutation == "candidate_update":
        kwargs["candidate_optimizer_updates"] += 1
    elif mutation == "control_update":
        kwargs["control_optimizer_updates"] += 1
    elif mutation == "shadow_update":
        kwargs["shadow_optimizer_steps"] += 1
    else:
        kwargs["charged_seconds"] += 0.001

    with pytest.raises(control.SuccessorControlError, match=message):
        control.validate_resource_and_evidence_budget(**kwargs)


def test_managed_artifact_byte_bounds_fail_before_publication(tmp_path, monkeypatch):
    control = _control()
    context = _training_context(control)
    output = tmp_path / "execution"

    with control.ExecutionLease(
        output,
        context=context,
        child_process_id=6204,
        process_alive=lambda process_id: process_id == 6204,
    ) as lease:
        monkeypatch.setattr(
            control,
            "_publication_byte_limits",
            lambda: {
                "max_artifact_bytes": 4,
                "max_stored_bytes": 4,
                "max_uncompressed_bytes": 4,
            },
        )
        with pytest.raises(control.SuccessorControlError, match="artifact"):
            control.publish_managed_artifact(
                context,
                lease,
                relative_path="evidence/oversized.bin",
                payload=b"12345",
            )
        assert not (output / "evidence" / "oversized.bin").exists()

        control.publish_managed_artifact(
            context,
            lease,
            relative_path="evidence/exact.bin",
            payload=b"1234",
        )
        with pytest.raises(control.SuccessorControlError, match="stored"):
            control.publish_managed_artifact(
                context,
                lease,
                relative_path="evidence/extra.bin",
                payload=b"5",
            )
        assert not (output / "evidence" / "extra.bin").exists()


def test_environment_access_ceiling_fails_before_debit_and_callback(
    tmp_path,
    monkeypatch,
):
    control = _control()
    context = _training_context(control)
    original_limits = control._resource_limits
    monkeypatch.setattr(
        control,
        "_resource_limits",
        lambda value: {
            **original_limits(value),
            "environment_accesses": 1,
        },
    )
    output = tmp_path / "execution"
    callbacks = []

    with control.ExecutionLease(
        output,
        context=context,
        child_process_id=6205,
        process_alive=lambda process_id: process_id == 6205,
    ) as lease:
        control.initialize_access_journal(context, lease)
        control.perform_journaled_environment_access(
            context,
            lease,
            seed=80_000,
            arm="candidate",
            purpose="training",
            access=lambda: callbacks.append("first"),
        )
        with pytest.raises(control.SuccessorControlError, match="environment access"):
            control.perform_journaled_environment_access(
                context,
                lease,
                seed=80_001,
                arm="control",
                purpose="training",
                access=lambda: callbacks.append("second"),
            )

        assert callbacks == ["first"]
        assert control.load_access_journal(context, lease)["debited_accesses"] == 1


def test_checkpoint_republication_rejects_ambiguous_staging(tmp_path):
    control = _control()
    context = _training_context(control)
    output = tmp_path / "execution"

    with control.ExecutionLease(
        output,
        context=context,
        child_process_id=6203,
        process_alive=lambda process_id: process_id == 6203,
    ) as lease:
        control.initialize_access_journal(context, lease)
        control.initialize_resource_ledger(context, lease)
        _debit_complete_training_chunk(control, context, lease)
        control.advance_resource_ledger(
            context,
            lease,
            charged_seconds=10.0,
            environment_accesses=128,
            optimizer_steps=2,
            shadow_optimizer_steps=0,
            reason="complete-training-chunk",
        )
        marker = control.publish_complete_training_checkpoint(
            context,
            lease,
            binding=_complete_checkpoint_binding(),
        )
        checkpoint = output / "checkpoints" / "chunk_0001.json"
        staging = checkpoint.with_name(f".{checkpoint.name}.tmp")
        staging.write_bytes(b"ambiguous")

        with pytest.raises(control.SuccessorControlError, match="ambiguous staging"):
            control.publish_complete_training_checkpoint(
                context,
                lease,
                binding=_complete_checkpoint_binding(),
            )
        assert checkpoint.read_bytes() == control.canonical_json_bytes(marker)
        assert staging.read_bytes() == b"ambiguous"


def _rollback_authority(control, tmp_path):
    control_checkpoint = tmp_path / "experiment" / "control-checkpoint.bin"
    control_configuration = tmp_path / "experiment" / "control-config.json"
    production_config = tmp_path / "production" / "config.properties"
    production_checkpoints = tmp_path / "production" / "checkpoints"
    control_checkpoint.parent.mkdir(parents=True)
    production_checkpoints.mkdir(parents=True)
    control_checkpoint.write_bytes(b"registered-control-checkpoint")
    control_configuration.write_bytes(b'{"arm":"control"}\n')
    production_config.parent.mkdir(parents=True, exist_ok=True)
    production_config.write_bytes(b'command="production"\n')
    (production_checkpoints / "production.bin").write_bytes(
        b"registered-production-checkpoint"
    )
    authority = control.build_rollback_authority(
        target_relative_path="experiment_target.json",
        control_checkpoint=control.external_file_binding(control_checkpoint),
        control_configuration=control.external_file_binding(control_configuration),
        production_isolation=control.build_isolation_identity(
            communication_mod_config=production_config,
            production_checkpoint_root=production_checkpoints,
        ),
    )
    paths = {
        "control_checkpoint": control_checkpoint,
        "control_configuration": control_configuration,
        "production_config": production_config,
        "production_checkpoints": production_checkpoints,
    }
    return authority, paths


ROLLBACK_FAILURE_PATHS = {
    "grant_failure": "authority",
    "revocation_failure": "authority",
    "approval_failure": "authority",
    "authorization_failure": "authority",
    "stage_authority_failure": "authority",
    "source_identity_failure": "identity",
    "checkpoint_identity_failure": "identity",
    "config_identity_failure": "identity",
    "cohort_identity_failure": "identity",
    "target_identity_failure": "identity",
    "production_identity_failure": "identity",
    "child_identity_failure": "identity",
    "process_identity_failure": "identity",
    "lease_identity_failure": "identity",
    "candidate_legality_failure": "legality",
    "action_legality_failure": "legality",
    "schema_failure": "legality",
    "finiteness_failure": "legality",
    "objective_support_failure": "legality",
    "zero_card_reward_chunk": "legality",
    "interpreter_preflight_failure": "preflight",
    "native_preflight_failure": "preflight",
    "isolation_preflight_failure": "preflight",
    "output_preflight_failure": "preflight",
    "dependency_preflight_failure": "preflight",
    "setup_preflight_failure": "preflight",
    "training_family_saturation": "canary",
    "canary_gate_failure": "canary",
    "canary_failure": "canary",
    "holdout_gate_failure": "holdout",
    "holdout_access_failure": "holdout",
    "holdout_evaluation_failure": "holdout",
    "holdout_classification_failure": "holdout",
    "resource_accounting_failure": "publication",
    "time_accounting_failure": "publication",
    "access_accounting_failure": "publication",
    "partial_chunk_failure": "publication",
    "journal_failure": "publication",
    "evidence_failure": "publication",
    "byte_bound_failure": "publication",
    "staging_failure": "publication",
    "checkpoint_publication_failure": "publication",
    "terminal_publication_failure": "publication",
    "manifest_publication_failure": "publication",
}


@pytest.mark.parametrize(
    ("failure_path", "trigger_class"),
    tuple(ROLLBACK_FAILURE_PATHS.items()),
)
def test_every_registered_failure_path_maps_to_one_rollback_trigger(
    failure_path,
    trigger_class,
):
    control = _control()

    result = control.classify_terminal_closeout(failure_paths=[failure_path])

    assert result == {
        "closeout_kind": "rollback_failure",
        "failure_paths": [failure_path],
        "outcome_class": None,
        "rollback_required": True,
        "trigger_class": trigger_class,
    }


def test_rollback_failure_mapping_uses_fixed_precedence_and_canonical_order():
    control = _control()

    result = control.classify_terminal_closeout(
        failure_paths=[
            "manifest_publication_failure",
            "source_identity_failure",
            "approval_failure",
        ]
    )

    assert result["failure_paths"] == [
        "approval_failure",
        "source_identity_failure",
        "manifest_publication_failure",
    ]
    assert result["trigger_class"] == "authority"


@pytest.mark.parametrize(
    "failure_paths",
    (
        [],
        ["unknown_failure"],
        ["canary_failure", "canary_failure"],
    ),
)
def test_rollback_failure_mapping_rejects_empty_unmapped_or_duplicate_paths(
    failure_paths,
):
    control = _control()

    with pytest.raises(control.SuccessorControlError, match="failure|path|duplicate"):
        control.classify_terminal_closeout(failure_paths=failure_paths)


@pytest.mark.parametrize(
    "outcome_class",
    (
        "victory_and_floor_signal",
        "floor_only_signal",
        "victory_only_signal",
        "no_learning_signal",
    ),
)
def test_complete_holdout_outcomes_are_normal_closeout_without_trigger(
    outcome_class,
):
    control = _control()

    result = control.classify_terminal_closeout(outcome_class=outcome_class)

    assert result == {
        "closeout_kind": "normal_holdout",
        "failure_paths": [],
        "outcome_class": outcome_class,
        "rollback_required": False,
        "trigger_class": None,
    }


def test_terminal_closeout_rejects_failure_plus_outcome_or_unknown_outcome():
    control = _control()

    with pytest.raises(control.SuccessorControlError, match="failure|outcome"):
        control.classify_terminal_closeout(
            failure_paths=["canary_failure"],
            outcome_class="no_learning_signal",
        )
    with pytest.raises(control.SuccessorControlError, match="outcome"):
        control.classify_terminal_closeout(outcome_class="unknown_signal")


@pytest.mark.parametrize(
    "outcome_class",
    (
        "victory_and_floor_signal",
        "floor_only_signal",
        "victory_only_signal",
        "no_learning_signal",
    ),
)
def test_registered_normal_closeout_restores_control_for_every_holdout_outcome(
    tmp_path,
    outcome_class,
):
    control = _control()
    authority, paths = _rollback_authority(control, tmp_path)
    context = _empirical_context(
        control,
        "holdout",
        registration_fields={
            "rollback_authority_sha256": authority["rollback_authority_sha256"]
        },
    )
    output = tmp_path / "execution"
    original_production = paths["production_config"].read_bytes()

    with control.ExecutionLease(
        output,
        context=context,
        child_process_id=6_400,
        process_alive=lambda process_id: process_id == 6_400,
    ) as lease:
        target = output / authority["target_relative_path"]
        target.write_bytes(b'{"candidate_enabled":true}\n')

        observation = control.execute_registered_normal_closeout(
            context,
            lease,
            rollback_authority=authority,
            outcome_class=outcome_class,
        )

        assert observation["status"] == "normal_closeout_verified"
        assert observation["closeout_kind"] == "normal_holdout"
        assert observation["failure_paths"] == []
        assert observation["outcome_class"] == outcome_class
        assert observation["trigger_class"] is None
        assert json.loads(target.read_bytes()) == authority["control_target"]
    assert paths["production_config"].read_bytes() == original_production


def test_registered_rollback_restores_control_target_and_verifies_isolation(
    tmp_path,
):
    control = _control()
    authority, paths = _rollback_authority(control, tmp_path)
    context = _training_context(
        control,
        registration_fields={
            "rollback_authority_sha256": authority["rollback_authority_sha256"]
        },
    )
    output = tmp_path / "execution"
    original_bytes = {
        name: path.read_bytes() for name, path in paths.items() if path.is_file()
    }

    with control.ExecutionLease(
        output,
        context=context,
        child_process_id=6300,
        process_alive=lambda process_id: process_id == 6300,
    ) as lease:
        control.initialize_access_journal(context, lease)
        control.initialize_resource_ledger(context, lease)
        target = output / authority["target_relative_path"]
        target.write_bytes(
            control.canonical_json_bytes(
                {
                    "candidate_enabled": True,
                    "selected_arm": "candidate",
                }
            )
        )
        observation = control.execute_registered_rollback(
            context,
            lease,
            rollback_authority=authority,
            failure_paths=["canary_failure"],
        )

        assert observation["status"] == "rollback_verified"
        assert observation["candidate_enabled"] is False
        assert observation["control_target_verified"] is True
        assert observation["production_isolation_verified"] is True
        assert observation["production_isolation_before"]["matches_registered"] is True
        assert observation["production_isolation_after"]["matches_registered"] is True
        assert json.loads(target.read_bytes()) == authority["control_target"]
        assert (output / control.ROLLBACK_OBSERVATION_FILENAME).read_bytes() == (
            control.canonical_json_bytes(observation)
        )
        intent = control.publish_terminal_intent(
            context,
            lease,
            verdict="rollback_completed",
            details={"rollback_observation_sha256": observation[
                "rollback_observation_sha256"
            ]},
        )
        prefix_paths = {
            row["path"] for row in intent["artifact_prefix"]["artifacts"]
        }
        assert authority["target_relative_path"] in prefix_paths
        assert control.ROLLBACK_OBSERVATION_FILENAME in prefix_paths

    assert {
        name: path.read_bytes() for name, path in paths.items() if path.is_file()
    } == original_bytes


def test_rollback_records_external_production_drift_without_repair(tmp_path):
    control = _control()
    authority, paths = _rollback_authority(control, tmp_path)
    context = _training_context(
        control,
        registration_fields={
            "rollback_authority_sha256": authority["rollback_authority_sha256"]
        },
    )
    drifted_config = b'command="externally-drifted"\n'
    paths["production_config"].write_bytes(drifted_config)
    (paths["production_checkpoints"] / "external.bin").write_bytes(b"external")
    output = tmp_path / "execution"

    with control.ExecutionLease(
        output,
        context=context,
        child_process_id=6301,
        process_alive=lambda process_id: process_id == 6301,
    ) as lease:
        target = output / authority["target_relative_path"]
        target.write_bytes(b'{"candidate_enabled":true}\n')
        observation = control.execute_registered_rollback(
            context,
            lease,
            rollback_authority=authority,
            failure_paths=["production_identity_failure"],
        )

        assert observation["status"] == "rollback_isolation_failure"
        assert observation["candidate_enabled"] is False
        assert observation["control_target_verified"] is True
        assert observation["production_isolation_verified"] is False
        assert observation["production_isolation_before"]["matches_registered"] is False
        assert observation["production_isolation_after"]["matches_registered"] is False
        assert json.loads(target.read_bytes()) == authority["control_target"]

    assert paths["production_config"].read_bytes() == drifted_config
    assert (paths["production_checkpoints"] / "external.bin").read_bytes() == b"external"


def test_rollback_rejects_unregistered_authority_and_ambiguous_target_staging(
    tmp_path,
):
    control = _control()
    authority, _paths = _rollback_authority(control, tmp_path)
    unregistered = _training_context(control)
    unregistered_output = tmp_path / "unregistered"
    with control.ExecutionLease(
        unregistered_output,
        context=unregistered,
        child_process_id=6302,
        process_alive=lambda process_id: process_id == 6302,
    ) as lease:
        with pytest.raises(control.SuccessorControlError, match="registered|authority"):
            control.execute_registered_rollback(
                unregistered,
                lease,
                rollback_authority=authority,
                failure_paths=["canary_failure"],
            )
        assert not (unregistered_output / authority["target_relative_path"]).exists()

    registered = _training_context(
        control,
        registration_fields={
            "rollback_authority_sha256": authority["rollback_authority_sha256"]
        },
    )
    output = tmp_path / "ambiguous"
    with control.ExecutionLease(
        output,
        context=registered,
        child_process_id=6303,
        process_alive=lambda process_id: process_id == 6303,
    ) as lease:
        target = output / authority["target_relative_path"]
        candidate_bytes = b'{"candidate_enabled":true}\n'
        target.write_bytes(candidate_bytes)
        staging = target.with_name(
            f".{target.name}{control.ROLLBACK_TARGET_STAGING_SUFFIX}"
        )
        staging.write_bytes(b"ambiguous")

        with pytest.raises(control.SuccessorControlError, match="ambiguous staging"):
            control.execute_registered_rollback(
                registered,
                lease,
                rollback_authority=authority,
                failure_paths=["canary_failure"],
            )
        assert target.read_bytes() == candidate_bytes
        assert staging.read_bytes() == b"ambiguous"
        assert not (output / control.ROLLBACK_OBSERVATION_FILENAME).exists()


def _standing_delegation(control):
    body = {
        "exclusions": list(control.STANDING_DELEGATION_EXCLUSIONS),
        "grant": copy.deepcopy(control.STANDING_DELEGATION_GRANT),
        "revocation": control.STANDING_DELEGATION_REVOCATION,
        "schema_version": control.STANDING_DELEGATION_SCHEMA_VERSION,
        "scope": {
            "pushed_remote_ref": "origin/master",
            "registration_id_prefix": control.DELEGATED_REGISTRATION_ID_PREFIX,
            "request_class": control.DELEGATED_REQUEST_CLASS,
        },
    }
    return {**body, "delegation_sha256": control.canonical_json_sha256(body)}


def test_standing_delegation_grant_matches_preserved_external_record():
    control = _control()
    source = control.STANDING_DELEGATION_GRANT_SOURCE
    payload = (ROOT / source["path"]).read_bytes()
    preserved = json.loads(payload)

    assert hashlib.sha256(payload).hexdigest() == source["file_sha256"]
    assert preserved["delegation_sha256"] == source["delegation_sha256"]
    assert preserved["grant"] == control.STANDING_DELEGATION_GRANT


def _revocation_observation(
    control,
    request,
    delegation,
    *,
    phase,
    checked_at,
    message_timestamp,
    available=True,
    revoked=False,
    task_id=None,
):
    if task_id is None:
        task_id = delegation["grant"]["provenance"]["task_id"]
    watermark = {
        "message_id": f"latest-human-{phase}",
        "message_timestamp": message_timestamp,
        "task_id": task_id,
    }
    body = {
        "authoritative_state_available": available,
        "authority_mode": "standing-delegation",
        "checked_at": checked_at,
        "delegation_sha256": delegation["delegation_sha256"],
        "latest_human_message_watermark": watermark,
        "phase": phase,
        "request_sha256": request["request_sha256"],
        "revocation_message_watermark": watermark if revoked else None,
        "revocation_observed": revoked,
        "schema_version": control.REVOCATION_OBSERVATION_SCHEMA_VERSION,
        "stage": request["stage"],
    }
    return {
        **body,
        "observation_sha256": control.canonical_json_sha256(body),
    }


@pytest.mark.parametrize(
    "stage",
    ("inventory", "inventory-verification", "training", "canary", "holdout"),
)
def test_standing_delegation_binds_exact_stage_and_fresh_launch_observation(stage):
    control = _control()
    request = _stage_request(control, stage)
    delegation = _standing_delegation(control)
    approval_observation = _revocation_observation(
        control,
        request,
        delegation,
        phase="approval",
        checked_at="2026-08-09T10:00:00+00:00",
        message_timestamp="2026-08-09T09:59:59+00:00",
    )

    approval = control.bind_delegated_approval(
        request=request,
        request_review_sha256="d" * 64,
        delegation=delegation,
        approval_observation=approval_observation,
        resolved_at="2026-08-09T10:00:00+00:00",
    )
    assert control.validate_standing_delegation(delegation) == delegation
    assert control.validate_delegated_approval(approval, request) == approval
    assert approval["approved_request_sha256"] == request["request_sha256"]
    assert approval["request_review_sha256"] == "d" * 64
    assert approval["approval_observation"] == approval_observation
    assert "verbatim_approval_text" not in approval
    authorization = control.build_stage_authorization(
        request=request,
        authorization_id=(
            f"card-acceptance-20260809-{stage}-authorization-v1"
        ),
        request_review_sha256="d" * 64,
        approval_record_sha256=approval["approval_sha256"],
    )
    launch_observation = _revocation_observation(
        control,
        request,
        delegation,
        phase="launch",
        checked_at="2026-08-09T10:01:00+00:00",
        message_timestamp="2026-08-09T10:00:59+00:00",
    )

    assert control.validate_delegated_stage_launch(
        request=request,
        authorization=authorization,
        delegated_approval=approval,
        launch_observation=launch_observation,
    ) == launch_observation
    if stage not in {"inventory", "inventory-verification"}:
        registration = {
            "registration_id": "card-acceptance-20260809-registration-v1",
            "registration_sha256": request["prerequisite_bindings"][
                "registration_sha256"
            ],
        }
        context = control._build_delegated_execution_context(
            registration=registration,
            request=request,
            authorization=authorization,
            delegated_approval=approval,
            launch_observation=launch_observation,
            registration_validator=lambda value: copy.deepcopy(dict(value)),
        )
        assert context.authority_observation == launch_observation
        assert control._context_identity(context)["launch_authority_sha256"] == (
            launch_observation["observation_sha256"]
        )
        with pytest.raises(TypeError, match="immutable"):
            context.authority_observation["phase"] = "approval"


def test_delegated_approval_rejects_unavailable_or_revoked_conversation_state():
    control = _control()
    request = _stage_request(control, "training")
    delegation = _standing_delegation(control)

    unavailable = _revocation_observation(
        control,
        request,
        delegation,
        phase="approval",
        checked_at="2026-08-09T10:00:00+00:00",
        message_timestamp="2026-08-09T09:59:59+00:00",
        available=False,
    )
    with pytest.raises(control.SuccessorControlError, match="authoritative|available"):
        control.bind_delegated_approval(
            request=request,
            request_review_sha256="d" * 64,
            delegation=delegation,
            approval_observation=unavailable,
            resolved_at="2026-08-09T10:00:00+00:00",
        )

    revoked = _revocation_observation(
        control,
        request,
        delegation,
        phase="approval",
        checked_at="2026-08-09T10:00:00+00:00",
        message_timestamp="2026-08-09T09:59:59+00:00",
        revoked=True,
    )
    with pytest.raises(control.SuccessorControlError, match="revocation|revoked"):
        control.bind_delegated_approval(
            request=request,
            request_review_sha256="d" * 64,
            delegation=delegation,
            approval_observation=revoked,
            resolved_at="2026-08-09T10:00:00+00:00",
        )


def test_delegated_launch_rejects_revocation_stale_watermark_and_wrong_task():
    control = _control()
    request = _stage_request(control, "canary")
    delegation = _standing_delegation(control)
    approval_observation = _revocation_observation(
        control,
        request,
        delegation,
        phase="approval",
        checked_at="2026-08-09T10:00:00+00:00",
        message_timestamp="2026-08-09T09:59:59+00:00",
    )
    approval = control.bind_delegated_approval(
        request=request,
        request_review_sha256="d" * 64,
        delegation=delegation,
        approval_observation=approval_observation,
        resolved_at="2026-08-09T10:00:00+00:00",
    )
    authorization = control.build_stage_authorization(
        request=request,
        authorization_id="card-acceptance-20260809-canary-authorization-v1",
        request_review_sha256="d" * 64,
        approval_record_sha256=approval["approval_sha256"],
    )

    revoked = _revocation_observation(
        control,
        request,
        delegation,
        phase="launch",
        checked_at="2026-08-09T10:01:00+00:00",
        message_timestamp="2026-08-09T10:00:59+00:00",
        revoked=True,
    )
    with pytest.raises(control.SuccessorControlError, match="revocation|revoked"):
        control.validate_delegated_stage_launch(
            request=request,
            authorization=authorization,
            delegated_approval=approval,
            launch_observation=revoked,
        )

    stale = _revocation_observation(
        control,
        request,
        delegation,
        phase="launch",
        checked_at="2026-08-09T10:01:00+00:00",
        message_timestamp="2026-08-09T09:59:58+00:00",
    )
    with pytest.raises(control.SuccessorControlError, match="watermark|stale"):
        control.validate_delegated_stage_launch(
            request=request,
            authorization=authorization,
            delegated_approval=approval,
            launch_observation=stale,
        )

    wrong_task = _revocation_observation(
        control,
        request,
        delegation,
        phase="launch",
        checked_at="2026-08-09T10:01:00+00:00",
        message_timestamp="2026-08-09T10:00:59+00:00",
        task_id="different-task",
    )
    with pytest.raises(control.SuccessorControlError, match="task|provenance"):
        control.validate_delegated_stage_launch(
            request=request,
            authorization=authorization,
            delegated_approval=approval,
            launch_observation=wrong_task,
        )


def test_standing_delegation_rejects_generated_scope_and_grant_tampering():
    control = _control()
    delegation = _standing_delegation(control)

    generated = copy.deepcopy(delegation)
    generated["grant"]["provenance"]["source"] = "generated"
    generated_body = {
        key: value for key, value in generated.items() if key != "delegation_sha256"
    }
    generated["delegation_sha256"] = control.canonical_json_sha256(generated_body)
    with pytest.raises(control.SuccessorControlError, match="external human"):
        control.validate_standing_delegation(generated)

    wrong_scope = copy.deepcopy(delegation)
    wrong_scope["scope"]["request_class"] = "unbound-request"
    wrong_scope_body = {
        key: value
        for key, value in wrong_scope.items()
        if key != "delegation_sha256"
    }
    wrong_scope["delegation_sha256"] = control.canonical_json_sha256(
        wrong_scope_body
    )
    with pytest.raises(control.SuccessorControlError, match="scope"):
        control.validate_standing_delegation(wrong_scope)

    changed_text = copy.deepcopy(delegation)
    changed_text["grant"]["verbatim_text"] = "changed"
    with pytest.raises(control.SuccessorControlError, match="immutable|grant"):
        control.validate_standing_delegation(changed_text)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("verbatim_text", "A different but still nonempty human grant."),
        ("granted_at", "2026-08-08T09:46:48Z"),
        ("message_id", "item-forged"),
        ("task_id", "task-forged"),
    ),
)
def test_standing_delegation_rejects_rehashed_grant_substitution(field, value):
    control = _control()
    delegation = _standing_delegation(control)
    if field in {"message_id", "task_id"}:
        delegation["grant"]["provenance"][field] = value
    else:
        delegation["grant"][field] = value
    body = {
        key: item
        for key, item in delegation.items()
        if key != "delegation_sha256"
    }
    delegation["delegation_sha256"] = control.canonical_json_sha256(body)

    with pytest.raises(control.SuccessorControlError, match="immutable|grant"):
        control.validate_standing_delegation(delegation)


def _external_approval_message(
    control,
    *,
    approval_text,
    approved_at,
    source="external-human-message",
):
    body = {
        "approved_at": approved_at,
        "provenance": {
            "message_id": "exact-external-approval-message",
            "source": source,
            "task_id": "external-approval-test-task",
        },
        "schema_version": control.EXTERNAL_APPROVAL_MESSAGE_SCHEMA_VERSION,
        "verbatim_approval_text": approval_text,
    }
    return {
        **body,
        "approval_message_sha256": control.canonical_json_sha256(body),
    }


def _external_revocation_observation(
    control,
    request,
    approval_message,
    *,
    phase,
    checked_at,
    message_timestamp,
    available=True,
    revoked=False,
):
    watermark = {
        "message_id": f"external-latest-human-{phase}",
        "message_timestamp": message_timestamp,
        "task_id": "external-approval-test-task",
    }
    body = {
        "approval_message_sha256": approval_message["approval_message_sha256"],
        "authoritative_state_available": available,
        "authority_mode": "external-human-approval",
        "checked_at": checked_at,
        "latest_human_message_watermark": watermark,
        "phase": phase,
        "request_sha256": request["request_sha256"],
        "revocation_message_watermark": watermark if revoked else None,
        "revocation_observed": revoked,
        "schema_version": control.EXTERNAL_REVOCATION_OBSERVATION_SCHEMA_VERSION,
        "stage": request["stage"],
    }
    return {
        **body,
        "observation_sha256": control.canonical_json_sha256(body),
    }


@pytest.mark.parametrize(
    "stage",
    ("inventory", "inventory-verification", "training", "canary", "holdout"),
)
def test_exact_external_human_approval_binds_one_stage_and_fresh_launch(stage):
    control = _control()
    request = _stage_request(control, stage)
    approval_text = f"I approve exact request {request['request_sha256']}."
    approval_message = _external_approval_message(
        control,
        approval_text=approval_text,
        approved_at="2026-08-09T11:01:00+00:00",
    )
    approval_observation = _external_revocation_observation(
        control,
        request,
        approval_message,
        phase="approval",
        checked_at="2026-08-09T11:02:00+00:00",
        message_timestamp="2026-08-09T11:01:59+00:00",
    )

    approval = control.bind_external_human_approval(
        request=request,
        request_review_sha256="e" * 64,
        request_published_at="2026-08-09T11:00:00+00:00",
        approval_text=approval_text,
        approved_at="2026-08-09T11:01:00+00:00",
        provenance=approval_message["provenance"],
        approval_observation=approval_observation,
    )
    assert control.validate_external_human_approval(approval, request) == approval
    assert approval["approved_request_sha256"] == request["request_sha256"]
    assert approval["approval_message"] == approval_message
    assert approval["bound_request_terms"]["resources"] == request["resources"]
    assert approval["bound_request_terms"]["exclusions"] == request["exclusions"]
    assert set(
        approval["bound_request_terms"]["downstream_authority"].values()
    ) == {False}
    authorization = control.build_stage_authorization(
        request=request,
        authorization_id=(
            f"card-acceptance-20260809-{stage}-authorization-v1"
        ),
        request_review_sha256="e" * 64,
        approval_record_sha256=approval["approval_sha256"],
    )
    launch_observation = _external_revocation_observation(
        control,
        request,
        approval_message,
        phase="launch",
        checked_at="2026-08-09T11:03:00+00:00",
        message_timestamp="2026-08-09T11:02:59+00:00",
    )
    assert control.validate_external_human_stage_launch(
        request=request,
        authorization=authorization,
        external_approval=approval,
        launch_observation=launch_observation,
    ) == launch_observation
    if stage not in {"inventory", "inventory-verification"}:
        registration = {
            "registration_id": "card-acceptance-20260809-registration-v1",
            "registration_sha256": request["prerequisite_bindings"][
                "registration_sha256"
            ],
        }
        context = control._build_external_human_execution_context(
            registration=registration,
            request=request,
            authorization=authorization,
            external_approval=approval,
            launch_observation=launch_observation,
            registration_validator=lambda value: copy.deepcopy(dict(value)),
        )
        assert context.authority_observation == launch_observation
        assert control._context_identity(context)["launch_authority_sha256"] == (
            launch_observation["observation_sha256"]
        )


def test_external_human_approval_rejects_generated_inferred_broad_or_predated():
    control = _control()
    request = _stage_request(control, "training")

    for source in ("generated", "agent-inference"):
        text = f"I approve exact request {request['request_sha256']}."
        message = _external_approval_message(
            control,
            approval_text=text,
            approved_at="2026-08-09T11:01:00+00:00",
            source=source,
        )
        observation = _external_revocation_observation(
            control,
            request,
            message,
            phase="approval",
            checked_at="2026-08-09T11:02:00+00:00",
            message_timestamp="2026-08-09T11:01:59+00:00",
        )
        with pytest.raises(control.SuccessorControlError, match="external human"):
            control.bind_external_human_approval(
                request=request,
                request_review_sha256="e" * 64,
                request_published_at="2026-08-09T11:00:00+00:00",
                approval_text=text,
                approved_at="2026-08-09T11:01:00+00:00",
                provenance=message["provenance"],
                approval_observation=observation,
            )

    broad_text = "I broadly approve future work in this repository."
    broad_message = _external_approval_message(
        control,
        approval_text=broad_text,
        approved_at="2026-08-09T11:01:00+00:00",
    )
    broad_observation = _external_revocation_observation(
        control,
        request,
        broad_message,
        phase="approval",
        checked_at="2026-08-09T11:02:00+00:00",
        message_timestamp="2026-08-09T11:01:59+00:00",
    )
    with pytest.raises(control.SuccessorControlError, match="request digest|exact"):
        control.bind_external_human_approval(
            request=request,
            request_review_sha256="e" * 64,
            request_published_at="2026-08-09T11:00:00+00:00",
            approval_text=broad_text,
            approved_at="2026-08-09T11:01:00+00:00",
            provenance=broad_message["provenance"],
            approval_observation=broad_observation,
        )

    exact_text = f"I approve exact request {request['request_sha256']}."
    predated_message = _external_approval_message(
        control,
        approval_text=exact_text,
        approved_at="2026-08-09T10:59:59+00:00",
    )
    predated_observation = _external_revocation_observation(
        control,
        request,
        predated_message,
        phase="approval",
        checked_at="2026-08-09T11:02:00+00:00",
        message_timestamp="2026-08-09T11:01:59+00:00",
    )
    with pytest.raises(control.SuccessorControlError, match="postdate|published"):
        control.bind_external_human_approval(
            request=request,
            request_review_sha256="e" * 64,
            request_published_at="2026-08-09T11:00:00+00:00",
            approval_text=exact_text,
            approved_at="2026-08-09T10:59:59+00:00",
            provenance=predated_message["provenance"],
            approval_observation=predated_observation,
        )


def test_external_approval_rejects_modified_terms_and_missing_conversation_state():
    control = _control()
    request = _stage_request(control, "training")
    approval_text = f"I approve exact request {request['request_sha256']}."
    message = _external_approval_message(
        control,
        approval_text=approval_text,
        approved_at="2026-08-09T11:01:00+00:00",
    )
    unavailable = _external_revocation_observation(
        control,
        request,
        message,
        phase="approval",
        checked_at="2026-08-09T11:02:00+00:00",
        message_timestamp="2026-08-09T11:01:59+00:00",
        available=False,
    )
    with pytest.raises(control.SuccessorControlError, match="authoritative|available"):
        control.bind_external_human_approval(
            request=request,
            request_review_sha256="e" * 64,
            request_published_at="2026-08-09T11:00:00+00:00",
            approval_text=approval_text,
            approved_at="2026-08-09T11:01:00+00:00",
            provenance=message["provenance"],
            approval_observation=unavailable,
        )

    valid_observation = _external_revocation_observation(
        control,
        request,
        message,
        phase="approval",
        checked_at="2026-08-09T11:02:00+00:00",
        message_timestamp="2026-08-09T11:01:59+00:00",
    )
    approval = control.bind_external_human_approval(
        request=request,
        request_review_sha256="e" * 64,
        request_published_at="2026-08-09T11:00:00+00:00",
        approval_text=approval_text,
        approved_at="2026-08-09T11:01:00+00:00",
        provenance=message["provenance"],
        approval_observation=valid_observation,
    )
    changed = copy.deepcopy(approval)
    changed["bound_request_terms"]["resources"]["max_pairs"] = 1
    changed_body = {
        key: value for key, value in changed.items() if key != "approval_sha256"
    }
    changed["approval_sha256"] = control.canonical_json_sha256(changed_body)
    with pytest.raises(control.SuccessorControlError, match="binding|terms"):
        control.validate_external_human_approval(changed, request)


def test_external_launch_rejects_later_revocation_and_stale_watermark():
    control = _control()
    request = _stage_request(control, "holdout")
    approval_text = f"I approve exact request {request['request_sha256']}."
    message = _external_approval_message(
        control,
        approval_text=approval_text,
        approved_at="2026-08-09T11:01:00+00:00",
    )
    approval_observation = _external_revocation_observation(
        control,
        request,
        message,
        phase="approval",
        checked_at="2026-08-09T11:02:00+00:00",
        message_timestamp="2026-08-09T11:01:59+00:00",
    )
    approval = control.bind_external_human_approval(
        request=request,
        request_review_sha256="e" * 64,
        request_published_at="2026-08-09T11:00:00+00:00",
        approval_text=approval_text,
        approved_at="2026-08-09T11:01:00+00:00",
        provenance=message["provenance"],
        approval_observation=approval_observation,
    )
    authorization = control.build_stage_authorization(
        request=request,
        authorization_id="card-acceptance-20260809-holdout-authorization-v1",
        request_review_sha256="e" * 64,
        approval_record_sha256=approval["approval_sha256"],
    )
    revoked = _external_revocation_observation(
        control,
        request,
        message,
        phase="launch",
        checked_at="2026-08-09T11:03:00+00:00",
        message_timestamp="2026-08-09T11:02:59+00:00",
        revoked=True,
    )
    with pytest.raises(control.SuccessorControlError, match="revocation|revoked"):
        control.validate_external_human_stage_launch(
            request=request,
            authorization=authorization,
            external_approval=approval,
            launch_observation=revoked,
        )

    stale = _external_revocation_observation(
        control,
        request,
        message,
        phase="launch",
        checked_at="2026-08-09T11:03:00+00:00",
        message_timestamp="2026-08-09T11:01:58+00:00",
    )
    with pytest.raises(control.SuccessorControlError, match="watermark|stale"):
        control.validate_external_human_stage_launch(
            request=request,
            authorization=authorization,
            external_approval=approval,
            launch_observation=stale,
        )
