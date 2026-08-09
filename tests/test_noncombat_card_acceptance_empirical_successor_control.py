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


def _training_context(control, *, registration_fields=None):
    registration = {
        "registration_id": "card-acceptance-20260809-registration-v1",
        "registration_sha256": "c" * 64,
    }
    if registration_fields is not None:
        registration.update(copy.deepcopy(dict(registration_fields)))
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
            trigger_class="canary",
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
            trigger_class="identity",
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
                trigger_class="canary",
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
                trigger_class="canary",
            )
        assert target.read_bytes() == candidate_bytes
        assert staging.read_bytes() == b"ambiguous"
        assert not (output / control.ROLLBACK_OBSERVATION_FILENAME).exists()


def _standing_delegation(control):
    body = {
        "exclusions": list(control.STANDING_DELEGATION_EXCLUSIONS),
        "grant": {
            "granted_at": "2026-08-08T09:46:47+00:00",
            "provenance": {
                "message_id": "external-human-grant-message",
                "source": "external-human-message",
                "task_id": "successor-control-test-task",
            },
            "verbatim_text": (
                "This repository is solely maintained by me; you may represent me."
            ),
        },
        "revocation": control.STANDING_DELEGATION_REVOCATION,
        "schema_version": control.STANDING_DELEGATION_SCHEMA_VERSION,
        "scope": {
            "pushed_remote_ref": "origin/master",
            "registration_id_prefix": control.DELEGATED_REGISTRATION_ID_PREFIX,
            "request_class": control.DELEGATED_REQUEST_CLASS,
        },
    }
    return {**body, "delegation_sha256": control.canonical_json_sha256(body)}


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
    task_id="successor-control-test-task",
):
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


@pytest.mark.parametrize("stage", ("inventory", "training", "canary", "holdout"))
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
    if stage != "inventory":
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
    with pytest.raises(control.SuccessorControlError, match="identity|digest"):
        control.validate_standing_delegation(changed_text)


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


@pytest.mark.parametrize("stage", ("inventory", "training", "canary", "holdout"))
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
    if stage != "inventory":
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
