from __future__ import annotations

import importlib
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
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


def _stage_prerequisites(stage: str) -> dict[str, str]:
    if stage == "inventory":
        return {}
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

    for stage in ("inventory", "training", "canary", "holdout"):
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


def _training_context(control):
    registration = {
        "registration_id": "card-acceptance-20260809-registration-v1",
        "registration_sha256": "c" * 64,
    }
    request = _stage_request(control, "training")
    authorization = control.build_stage_authorization(
        request=request,
        authorization_id="card-acceptance-20260809-training-authorization-v1",
        request_review_sha256="1" * 64,
        approval_record_sha256="2" * 64,
    )
    return control._build_validated_execution_context(
        registration=registration,
        request=request,
        authorization=authorization,
        registration_validator=lambda value: copy.deepcopy(dict(value)),
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
