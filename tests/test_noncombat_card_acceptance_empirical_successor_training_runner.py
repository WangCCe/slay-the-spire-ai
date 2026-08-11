from __future__ import annotations

import builtins
import copy
import hashlib
import importlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


RUNNER_MODULE = (
    "analysis_scripts.noncombat_card_acceptance_empirical_successor_training_runner"
)
CONTROL_MODULE = (
    "analysis_scripts.noncombat_card_acceptance_empirical_successor_experiment"
)
FORBIDDEN_IMPORTS = (
    "torch",
    "sts_lightspeed_noncombat_adapter",
    "analysis_scripts.noncombat_card_acceptance_empirical_successor_runtime",
    "analysis_scripts.noncombat_simulator_adapter",
)
ARTIFACT_NAMES = (
    "control_source",
    "registration",
    "registration_request",
    "registration_verifier_source",
    "runner_source",
    "runner_verifier_source",
    "runtime_source",
    "training_request",
    "training_request_review",
)


def _runner():
    return importlib.import_module(RUNNER_MODULE)


def _control():
    return importlib.import_module(CONTROL_MODULE)


def _binding(path: str, payload: bytes) -> dict:
    return {
        "path": path,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _external_binding(path: str, digest: str) -> dict:
    return {"path": path, "sha256": digest, "size_bytes": 1}


def _rollback_authority(root: str) -> dict:
    control = _control()
    return control.build_rollback_authority(
        target_relative_path="control/selected-arm.json",
        control_checkpoint=_external_binding(
            f"{root}/control/checkpoint.bin", "a" * 64
        ),
        control_configuration=_external_binding(
            f"{root}/control/configuration.json", "b" * 64
        ),
        production_isolation={
            "communication_mod_config": _external_binding(
                f"{root}/production/config.properties", "c" * 64
            ),
            "production_checkpoints": {
                "file_count": 1,
                "root": f"{root}/production/checkpoints",
                "sha256": "d" * 64,
                "size_bytes": 1,
            },
        },
    )


def _fixture(root: str = "D:/synthetic/card-acceptance-runner"):
    runner = _runner()
    control = _control()
    runner_commit = "1" * 40
    registered_commit = "2" * 40
    source_inventory_sha256 = "3" * 64
    registration_sha256 = "4" * 64
    output_root = f"{root}/output/training"
    source_inventory = {
        "path": f"{root}/inventory/seed_inventory.json",
        "sha256": "5" * 64,
        "size_bytes": 255_499,
    }
    request = control.build_stage_request(
        stage="training",
        request_id="card-acceptance-20260811-r6-training-request-v1",
        source_commit=registered_commit,
        source_inventory_sha256=source_inventory_sha256,
        configuration_identity=control.experiment_configuration_identity(),
        prerequisite_bindings={"registration_sha256": registration_sha256},
        output_root=output_root,
    )
    registration_request = {
        "input_bindings": {
            "inventory": {"content_kind": "canonical_json", **source_inventory}
        },
        "request_id": "synthetic-r6-registration-request-v1",
    }
    payloads = {
        "control_source": b"# synthetic control\n",
        "registration": runner.canonical_json_bytes(
            {"registration_sha256": registration_sha256}
        ),
        "registration_request": runner.canonical_json_bytes(
            registration_request
        ),
        "registration_verifier_source": b"# synthetic registration verifier\n",
        "runner_source": b"# synthetic runner\n",
        "runner_verifier_source": b"# synthetic runner verifier\n",
        "runtime_source": b"# synthetic runtime\n",
        "training_request": control.canonical_json_bytes(request),
        "training_request_review": b"reviewed: no findings\n",
    }
    artifacts = {
        name: _binding(f"synthetic/{name}.bin", payloads[name])
        for name in ARTIFACT_NAMES
    }
    interpreter = f"{root}/python/python.exe"
    runner_path = f"{root}/{artifacts['runner_source']['path']}"
    manifest_path = f"{root}/authority/launch_manifest.json"
    common_inputs = [
        "--manifest",
        manifest_path,
        "--envelope",
        f"{root}/authority/envelope.json",
        "--authorization",
        f"{root}/authority/authorization.json",
        "--approval",
        f"{root}/authority/approval.json",
        "--launch-observation",
        f"{root}/authority/launch_observation.json",
    ]
    definition = {
        "artifacts": artifacts,
        "commands": {
            "preflight": [
                interpreter,
                "-I",
                runner_path,
                "preflight",
                "--manifest",
                manifest_path,
            ],
            "run_training": [
                interpreter,
                "-I",
                runner_path,
                "run-training",
                *common_inputs,
            ],
            "terminalize_dead_owner": [
                interpreter,
                "-I",
                runner_path,
                "terminalize-dead-owner",
                *common_inputs,
            ],
        },
        "denied_operations": [
            "communication_mod",
            "gameplay",
            "ope",
            "production_model_loading",
            "promotion",
            "qualification",
        ],
        "downstream_authority": copy.deepcopy(request["downstream_authority"]),
        "empirical_operations": {
            "communication_mod": False,
            "environment_construction": False,
            "evaluation": False,
            "model_fitting": False,
            "model_loading": False,
            "native_loading": False,
            "ope": False,
            "runtime_fitting": False,
            "seed_access": False,
            "training": False,
        },
        "interpreter": interpreter,
        "launch_id": "card-acceptance-r6-training-launch-manifest-v1",
        "manifest_path": manifest_path,
        "output_root": output_root,
        "pushed_ref": "origin/master",
        "repository_root": root,
        "request_contract": {
            "downstream_authority": copy.deepcopy(
                request["downstream_authority"]
            ),
            "execution_authority": copy.deepcopy(request["execution_authority"]),
            "output_root": output_root,
            "registration_sha256": registration_sha256,
            "request_sha256": request["request_sha256"],
            "resources": copy.deepcopy(request["resources"]),
            "source_commit": registered_commit,
            "source_inventory_sha256": source_inventory_sha256,
        },
        "resources": copy.deepcopy(request["resources"]),
        "rollback_authority": _rollback_authority(root),
        "runner_source_commit": runner_commit,
        "source_inventory": source_inventory,
        "terminalization_guard": f"{root}/output/.training.terminalization.guard",
        "registered_source": {
            "source_commit": registered_commit,
            "source_inventory_sha256": source_inventory_sha256,
        },
    }
    return runner, definition, payloads


def _manifest(root: str = "D:/synthetic/card-acceptance-runner"):
    runner, definition, payloads = _fixture(root)
    return runner, runner.build_launch_manifest(definition), payloads


def _control_observation(request_sha256: str) -> dict:
    body = {
        "observation_sha256": "6" * 64,
        "request_sha256": request_sha256,
        "stage": "training",
    }
    return body


def _run_envelope(runner, manifest):
    composite = runner.build_runner_composite(manifest, "run-training")
    observation = runner.build_runner_launch_observation(
        composite,
        "run-training",
        _control_observation(composite["request_sha256"]),
        authority_mode="standing-delegation",
        composite_binding_text=(
            runner.STANDING_COMPOSITE_BINDING_PREFIX
            + composite["composite_sha256"]
        ),
    )
    return runner.build_command_envelope(
        command="run-training",
        composite=composite,
        stage_authorization_sha256="7" * 64,
        authority_mode="standing-delegation",
        approval_sha256="8" * 64,
        runner_launch_observation=observation,
        envelope_id="card-acceptance-r6-run-training-envelope-v1",
    )


def test_training_runner_import_is_source_only(monkeypatch):
    sys.modules.pop(RUNNER_MODULE, None)
    original = builtins.__import__

    def guarded(name, *args, **kwargs):
        if any(name == item or name.startswith(item + ".") for item in FORBIDDEN_IMPORTS):
            raise AssertionError(f"forbidden import: {name}")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)
    assert importlib.import_module(RUNNER_MODULE).__name__ == RUNNER_MODULE


def test_launch_manifest_is_canonical_repeatable_and_self_digested():
    runner, definition, _payloads = _fixture()
    original = copy.deepcopy(definition)

    first = runner.build_launch_manifest(definition)
    second = runner.build_launch_manifest(copy.deepcopy(definition))

    assert definition == original
    assert first == second
    assert first["manifest_sha256"] == runner.canonical_json_sha256(
        {key: value for key, value in first.items() if key != "manifest_sha256"}
    )
    assert runner.validate_launch_manifest(first) == first


def test_launch_manifest_parser_rejects_duplicate_unknown_and_noncanonical_bytes():
    runner, manifest, _payloads = _manifest()
    canonical = runner.canonical_json_bytes(manifest)
    duplicate = b'{"launch_id":"duplicate",' + canonical[1:]
    unknown = copy.deepcopy(manifest)
    unknown["unexpected"] = False
    unknown["manifest_sha256"] = runner.canonical_json_sha256(
        {key: value for key, value in unknown.items() if key != "manifest_sha256"}
    )

    with pytest.raises(runner.TrainingRunnerBlocked, match="duplicate"):
        runner.parse_launch_manifest_bytes(duplicate)
    with pytest.raises(runner.TrainingRunnerBlocked, match="fields"):
        runner.parse_launch_manifest_bytes(runner.canonical_json_bytes(unknown))
    with pytest.raises(runner.TrainingRunnerBlocked, match="canonical"):
        runner.parse_launch_manifest_bytes(canonical.removesuffix(b"\n"))


@pytest.mark.parametrize("mutation", ("command", "downstream", "rollback"))
def test_launch_manifest_rejects_rehashed_semantic_drift(mutation):
    runner, manifest, _payloads = _manifest()
    changed = copy.deepcopy(manifest)
    if mutation == "command":
        changed["commands"]["run_training"].append("--extra")
    elif mutation == "downstream":
        changed["downstream_authority"]["training"] = True
    else:
        changed["rollback_authority"]["target_relative_path"] = "changed.json"
    changed["manifest_sha256"] = runner.canonical_json_sha256(
        {key: value for key, value in changed.items() if key != "manifest_sha256"}
    )

    with pytest.raises(runner.TrainingRunnerBlocked):
        runner.validate_launch_manifest(changed)


def test_composites_are_command_specific_and_terminalization_is_subordinate():
    runner, manifest, _payloads = _manifest()

    run = runner.build_runner_composite(manifest, "run-training")
    terminal = runner.build_runner_composite(manifest, "terminalize-dead-owner")

    assert run["composite_sha256"] != terminal["composite_sha256"]
    assert run["execution_operations"] == sorted(
        name
        for name, enabled in manifest["request_contract"][
            "execution_authority"
        ].items()
        if enabled
    )
    assert terminal["execution_operations"] == ["evidence_publication"]
    with pytest.raises(runner.TrainingRunnerBlocked, match="command"):
        runner.build_runner_composite(manifest, "holdout")


def test_run_and_terminalization_envelopes_cannot_substitute():
    runner, manifest, _payloads = _manifest()
    run = _run_envelope(runner, manifest)
    terminal_composite = runner.build_runner_composite(
        manifest, "terminalize-dead-owner"
    )
    terminal_observation = runner.build_runner_launch_observation(
        terminal_composite,
        "terminalize-dead-owner",
        _control_observation(terminal_composite["request_sha256"]),
        authority_mode="standing-delegation",
        composite_binding_text=(
            runner.STANDING_COMPOSITE_BINDING_PREFIX
            + terminal_composite["composite_sha256"]
        ),
    )
    terminal = runner.build_command_envelope(
        command="terminalize-dead-owner",
        composite=terminal_composite,
        stage_authorization_sha256="7" * 64,
        authority_mode="standing-delegation",
        approval_sha256="8" * 64,
        runner_launch_observation=terminal_observation,
        envelope_id="card-acceptance-r6-terminalize-envelope-v1",
        terminalization_binding={
            "closure_guard": manifest["terminalization_guard"],
            "failure_paths": ["process_identity_failure"],
            "lease_sha256": "9" * 64,
            "owner": {"child_process_id": 71_001},
            "prefix_sha256": "a" * 64,
            "run_envelope_sha256": run["envelope_sha256"],
        },
    )

    assert runner.validate_command_envelope(run, manifest) == run
    assert runner.validate_command_envelope(terminal, manifest) == terminal
    assert run["envelope_sha256"] != terminal["envelope_sha256"]
    with pytest.raises(runner.TrainingRunnerBlocked, match="terminalization"):
        runner.build_command_envelope(
            command="run-training",
            composite=run["composite"],
            stage_authorization_sha256="7" * 64,
            authority_mode="standing-delegation",
            approval_sha256="8" * 64,
            runner_launch_observation=run["runner_launch_observation"],
            envelope_id="bad-run-envelope-v1",
            terminalization_binding=terminal["terminalization_binding"],
        )


def test_command_envelope_parser_rejects_duplicate_unknown_and_noncanonical_bytes():
    runner, manifest, _payloads = _manifest()
    envelope = _run_envelope(runner, manifest)
    canonical = runner.canonical_json_bytes(envelope)
    duplicate = b'{"envelope_id":"duplicate",' + canonical[1:]
    unknown = copy.deepcopy(envelope)
    unknown["unexpected"] = False
    unknown["envelope_sha256"] = runner.canonical_json_sha256(
        {key: value for key, value in unknown.items() if key != "envelope_sha256"}
    )

    assert runner.parse_command_envelope_bytes(canonical, manifest) == envelope
    with pytest.raises(runner.TrainingRunnerBlocked, match="duplicate"):
        runner.parse_command_envelope_bytes(duplicate, manifest)
    with pytest.raises(runner.TrainingRunnerBlocked, match="fields"):
        runner.parse_command_envelope_bytes(
            runner.canonical_json_bytes(unknown), manifest
        )
    with pytest.raises(runner.TrainingRunnerBlocked, match="canonical"):
        runner.parse_command_envelope_bytes(canonical.removesuffix(b"\n"), manifest)


def test_parser_exposes_only_the_three_registered_commands():
    runner = _runner()
    parser = runner.build_parser()
    shared = [
        "--manifest",
        "D:/synthetic/manifest.json",
        "--envelope",
        "D:/synthetic/envelope.json",
        "--authorization",
        "D:/synthetic/authorization.json",
        "--approval",
        "D:/synthetic/approval.json",
        "--launch-observation",
        "D:/synthetic/observation.json",
    ]

    assert parser.parse_args(
        ["preflight", "--manifest", "D:/synthetic/manifest.json"]
    ).command == "preflight"
    assert parser.parse_args(["run-training", *shared]).command == "run-training"
    assert parser.parse_args(
        ["terminalize-dead-owner", *shared]
    ).command == "terminalize-dead-owner"
    with pytest.raises(SystemExit):
        parser.parse_args(["holdout", *shared])


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


def _delegated_observation(control, request, delegation, *, phase, checked_at):
    watermark = {
        "message_id": f"runner-latest-human-{phase}",
        "message_timestamp": checked_at,
        "task_id": delegation["grant"]["provenance"]["task_id"],
    }
    body = {
        "authoritative_state_available": True,
        "authority_mode": "standing-delegation",
        "checked_at": checked_at,
        "delegation_sha256": delegation["delegation_sha256"],
        "latest_human_message_watermark": watermark,
        "phase": phase,
        "request_sha256": request["request_sha256"],
        "revocation_message_watermark": None,
        "revocation_observed": False,
        "schema_version": control.REVOCATION_OBSERVATION_SCHEMA_VERSION,
        "stage": request["stage"],
    }
    return {**body, "observation_sha256": control.canonical_json_sha256(body)}


def _external_approval_message(
    control, request_sha256, composite_sha256, *, include_composite=True
):
    approval_text = f"I approve exact request {request_sha256}."
    if include_composite:
        approval_text = (
            f"I approve exact request {request_sha256} and exact runner composite "
            f"{composite_sha256}."
        )
    body = {
        "approved_at": "2026-08-11T02:01:00+00:00",
        "provenance": {
            "message_id": "exact-runner-approval-message",
            "source": "external-human-message",
            "task_id": "exact-runner-approval-task",
        },
        "schema_version": control.EXTERNAL_APPROVAL_MESSAGE_SCHEMA_VERSION,
        "verbatim_approval_text": approval_text,
    }
    return {**body, "approval_message_sha256": control.canonical_json_sha256(body)}


def _external_observation(control, request, message, *, phase, checked_at):
    watermark = {
        "message_id": f"exact-runner-latest-{phase}",
        "message_timestamp": checked_at,
        "task_id": message["provenance"]["task_id"],
    }
    body = {
        "approval_message_sha256": message["approval_message_sha256"],
        "authoritative_state_available": True,
        "authority_mode": "external-human-approval",
        "checked_at": checked_at,
        "latest_human_message_watermark": watermark,
        "phase": phase,
        "request_sha256": request["request_sha256"],
        "revocation_message_watermark": None,
        "revocation_observed": False,
        "schema_version": control.EXTERNAL_REVOCATION_OBSERVATION_SCHEMA_VERSION,
        "stage": request["stage"],
    }
    return {**body, "observation_sha256": control.canonical_json_sha256(body)}


@pytest.mark.parametrize(
    "authority_mode", ("standing-delegation", "external-human-approval")
)
def test_authorized_runner_envelope_resolves_exact_composite(authority_mode):
    runner, manifest, payloads = _manifest()
    request = json.loads(payloads["training_request"])
    documents = _authorized_runner_documents(
        runner, manifest, request, authority_mode
    )

    assert documents["authority"]["validated"] is True
    assert documents["authority"]["authority_mode"] == authority_mode
    assert documents["authority"]["command"] == "run-training"


def _authorized_runner_documents(runner, manifest, request, authority_mode):
    control = _control()
    composite = runner.build_runner_composite(manifest, "run-training")
    review_sha256 = manifest["artifacts"]["training_request_review"]["sha256"]

    if authority_mode == "standing-delegation":
        delegation = _standing_delegation(control)
        approval_observation = _delegated_observation(
            control,
            request,
            delegation,
            phase="approval",
            checked_at="2026-08-11T02:00:00+00:00",
        )
        approval = control.bind_delegated_approval(
            request=request,
            request_review_sha256=review_sha256,
            delegation=delegation,
            approval_observation=approval_observation,
            resolved_at=approval_observation["checked_at"],
        )
        control_observation = _delegated_observation(
            control,
            request,
            delegation,
            phase="launch",
            checked_at="2026-08-11T02:02:00+00:00",
        )
        binding_text = (
            runner.STANDING_COMPOSITE_BINDING_PREFIX
            + composite["composite_sha256"]
        )
    else:
        message = _external_approval_message(
            control, request["request_sha256"], composite["composite_sha256"]
        )
        approval_observation = _external_observation(
            control,
            request,
            message,
            phase="approval",
            checked_at="2026-08-11T02:02:00+00:00",
        )
        approval = control.bind_external_human_approval(
            request=request,
            request_review_sha256=review_sha256,
            request_published_at="2026-08-11T02:00:00+00:00",
            approval_text=message["verbatim_approval_text"],
            approved_at=message["approved_at"],
            provenance=message["provenance"],
            approval_observation=approval_observation,
        )
        control_observation = _external_observation(
            control,
            request,
            message,
            phase="launch",
            checked_at="2026-08-11T02:03:00+00:00",
        )
        binding_text = (
            "Fresh exact-human runner observation names composite "
            + composite["composite_sha256"]
            + "."
        )

    authorization = control.build_stage_authorization(
        request=request,
        authorization_id=(
            f"card-acceptance-r6-{authority_mode}-training-authorization-v1"
        ),
        request_review_sha256=review_sha256,
        approval_record_sha256=approval["approval_sha256"],
    )
    runner_observation = runner.build_runner_launch_observation(
        composite,
        "run-training",
        control_observation,
        authority_mode=authority_mode,
        composite_binding_text=binding_text,
    )
    envelope = runner.build_command_envelope(
        command="run-training",
        composite=composite,
        stage_authorization_sha256=authorization["authorization_sha256"],
        authority_mode=authority_mode,
        approval_sha256=approval["approval_sha256"],
        runner_launch_observation=runner_observation,
        envelope_id=f"card-acceptance-r6-{authority_mode}-run-envelope-v1",
    )

    authority = runner.validate_authorized_command_envelope(
        envelope=envelope,
        manifest=manifest,
        request=request,
        authorization=authorization,
        approval=approval,
    )
    return {
        "approval": approval,
        "authority": authority,
        "authorization": authorization,
        "envelope": envelope,
        "request": request,
    }


@pytest.mark.parametrize(
    "authority_mode", ("standing-delegation", "external-human-approval")
)
def test_authorized_training_context_freezes_exact_execution_registration(
    authority_mode,
):
    (
        runner,
        _inventory,
        _inventory_payload,
        registration,
        _registration_payload,
        manifest,
        _composite,
        request,
    ) = _registered_input_fixture(include_request=True)
    control = _control()
    documents = _authorized_runner_documents(
        runner, manifest, request, authority_mode
    )
    execution_registration = {
        **copy.deepcopy(registration),
        "rollback_authority_sha256": manifest["rollback_authority"][
            "rollback_authority_sha256"
        ],
    }

    context = runner._build_authorized_training_context(
        control_api=control,
        launch_manifest=manifest,
        command_envelope=documents["envelope"],
        authority=documents["authority"],
        original_registration=registration,
        execution_registration=execution_registration,
        request=request,
        authorization=documents["authorization"],
        approval=documents["approval"],
    )

    assert context.registration == execution_registration
    assert context.request == request
    assert context.authorization == documents["authorization"]
    assert control._context_identity(context) == {
        "authorization_sha256": documents["authorization"][
            "authorization_sha256"
        ],
        "launch_authority_sha256": documents["envelope"][
            "runner_launch_observation"
        ]["control_observation"]["observation_sha256"],
        "registration_sha256": registration["registration_sha256"],
        "request_sha256": request["request_sha256"],
        "stage": "training",
    }
    with pytest.raises(TypeError, match="immutable"):
        context.registration["rollback_authority_sha256"] = "0" * 64


def test_authorized_training_context_rejects_authority_and_registration_drift():
    (
        runner,
        _inventory,
        _inventory_payload,
        registration,
        _registration_payload,
        manifest,
        _composite,
        request,
    ) = _registered_input_fixture(include_request=True)
    documents = _authorized_runner_documents(
        runner, manifest, request, "standing-delegation"
    )
    execution_registration = {
        **copy.deepcopy(registration),
        "rollback_authority_sha256": manifest["rollback_authority"][
            "rollback_authority_sha256"
        ],
    }
    base = {
        "control_api": _control(),
        "launch_manifest": manifest,
        "command_envelope": documents["envelope"],
        "authority": documents["authority"],
        "original_registration": registration,
        "execution_registration": execution_registration,
        "request": request,
        "authorization": documents["authorization"],
        "approval": documents["approval"],
    }
    mutations = []
    drifted_authority = copy.deepcopy(documents["authority"])
    drifted_authority["envelope_sha256"] = "0" * 64
    mutations.append({"authority": drifted_authority})
    drifted_original = copy.deepcopy(registration)
    drifted_original["registration_id"] = "drifted-registration"
    mutations.append({"original_registration": drifted_original})
    drifted_execution = copy.deepcopy(execution_registration)
    drifted_execution["rollback_authority_sha256"] = "0" * 64
    mutations.append({"execution_registration": drifted_execution})
    extra_execution = copy.deepcopy(execution_registration)
    extra_execution["unexpected"] = True
    mutations.append({"execution_registration": extra_execution})
    drifted_envelope = copy.deepcopy(documents["envelope"])
    drifted_envelope["runner_launch_observation"]["control_observation"][
        "checked_at"
    ] = "2026-08-11T02:04:00+00:00"
    mutations.append({"command_envelope": drifted_envelope})

    for mutation in mutations:
        arguments = {**base, **mutation}
        with pytest.raises(runner.TrainingRunnerBlocked):
            runner._build_authorized_training_context(**arguments)


def test_external_authority_requires_composite_in_approval_and_observation():
    runner, manifest, payloads = _manifest()
    control = _control()
    request = json.loads(payloads["training_request"])
    composite = runner.build_runner_composite(manifest, "run-training")

    with pytest.raises(runner.TrainingRunnerBlocked, match="exactly once"):
        runner.build_runner_launch_observation(
            composite,
            "run-training",
            _control_observation(composite["request_sha256"]),
            authority_mode="external-human-approval",
            composite_binding_text="This text omits the exact runner identity.",
        )

    message = _external_approval_message(
        control,
        request["request_sha256"],
        composite["composite_sha256"],
        include_composite=False,
    )
    approval_observation = _external_observation(
        control,
        request,
        message,
        phase="approval",
        checked_at="2026-08-11T02:02:00+00:00",
    )
    review_sha256 = manifest["artifacts"]["training_request_review"]["sha256"]
    approval = control.bind_external_human_approval(
        request=request,
        request_review_sha256=review_sha256,
        request_published_at="2026-08-11T02:00:00+00:00",
        approval_text=message["verbatim_approval_text"],
        approved_at=message["approved_at"],
        provenance=message["provenance"],
        approval_observation=approval_observation,
    )
    authorization = control.build_stage_authorization(
        request=request,
        authorization_id="card-acceptance-r6-missing-composite-training-authorization-v1",
        request_review_sha256=review_sha256,
        approval_record_sha256=approval["approval_sha256"],
    )
    control_observation = _external_observation(
        control,
        request,
        message,
        phase="launch",
        checked_at="2026-08-11T02:03:00+00:00",
    )
    runner_observation = runner.build_runner_launch_observation(
        composite,
        "run-training",
        control_observation,
        authority_mode="external-human-approval",
        composite_binding_text=(
            "Fresh exact-human runner observation names composite "
            + composite["composite_sha256"]
            + "."
        ),
    )
    envelope = runner.build_command_envelope(
        command="run-training",
        composite=composite,
        stage_authorization_sha256=authorization["authorization_sha256"],
        authority_mode="external-human-approval",
        approval_sha256=approval["approval_sha256"],
        runner_launch_observation=runner_observation,
        envelope_id="card-acceptance-r6-missing-composite-run-envelope-v1",
    )

    with pytest.raises(runner.TrainingRunnerBlocked, match="does not name"):
        runner.validate_authorized_command_envelope(
            envelope=envelope,
            manifest=manifest,
            request=request,
            authorization=authorization,
            approval=approval,
        )


def _fake_runtime_checkpoint(runner, chunk_index: int, *, stopped=False) -> bytes:
    return runner.canonical_json_bytes(
        {
            "bootstrap": {
                "architecture": {"hidden_dim": 64},
                "generators": {
                    "candidate_card": {"chunk": chunk_index, "slot": 1},
                    "candidate_noncard": {"chunk": chunk_index, "slot": 2},
                    "control_card": {"chunk": chunk_index, "slot": 3},
                    "control_noncard": {"chunk": chunk_index, "slot": 4},
                },
                "models": {
                    "candidate": {"chunk": chunk_index, "weights": [1, 2]},
                    "control": {"chunk": chunk_index, "weights": [3, 4]},
                },
                "schema_version": "synthetic-bootstrap-v1",
            },
            "completed_chunk_summaries": [
                {"chunk_index": index} for index in range(chunk_index)
            ],
            "coordinates": {
                "candidate_optimizer_updates": chunk_index,
                "completed_decisions": chunk_index * 10,
                "completed_pairs": chunk_index * 64,
                "control_optimizer_updates": chunk_index,
                "next_chunk_index": chunk_index,
                "training_environment_accesses": chunk_index * 128,
                "training_optimizer_steps": chunk_index * 2,
            },
            "optimizers": {
                "candidate": {"chunk": chunk_index, "state": "candidate"},
                "control": {"chunk": chunk_index, "state": "control"},
            },
            "schema_version": "synthetic-training-checkpoint-v1",
            "stopped_for_family_saturation": stopped,
        }
    )


class _FakeTrainingRuntimeApi:
    def __init__(self, runner, *, saturation_chunk=None, fail_after_debits=None):
        self.runner = runner
        self.saturation_chunk = saturation_chunk
        self.fail_after_debits = fail_after_debits
        self.debits_seen = 0
        self.chunk_calls = []

    def encode_paired_training_checkpoint(self, state):
        return _fake_runtime_checkpoint(
            self.runner,
            state["chunk_index"],
            stopped=state.get("stopped", False),
        )

    def initialize_paired_training_runtime(self):
        return {"chunk_index": 0}

    def restore_paired_training_checkpoint(self, payload):
        parsed = json.loads(payload)
        return {"chunk_index": parsed["coordinates"]["next_chunk_index"]}

    def collect_and_complete_paired_training_chunk(
        self,
        state,
        *,
        environment_factory,
        seeds,
        chunk_index,
        before_environment,
        after_environment,
        deadline,
        clock,
    ):
        assert tuple(seeds) == tuple(range(chunk_index * 64, (chunk_index + 1) * 64))
        assert deadline == 100.0
        assert clock() == 0.0
        self.chunk_calls.append((chunk_index, tuple(seeds)))
        for seed in seeds:
            for arm in ("candidate", "control"):
                before_environment(arm, seed)
                self.debits_seen += 1
                if self.fail_after_debits == self.debits_seen:
                    raise RuntimeError("synthetic partial chunk failure")
                environment_factory(seed)
                after_environment(arm, seed)
        state["chunk_index"] += 1
        stop = state["chunk_index"] == self.saturation_chunk
        state["stopped"] = stop
        checkpoint = self.encode_paired_training_checkpoint(state)
        return SimpleNamespace(
            checkpoint=checkpoint,
            saturation={"stop": stop},
            seeds=tuple(seeds),
        )

    def training_progress_verdict(self, state):
        if state["chunk_index"] == self.saturation_chunk:
            return "experiment_stopped_during_training_for_family_saturation"
        if state["chunk_index"] == 8:
            return "training_completed_without_family_saturation"
        return "training_incomplete"


class _FakeTrainingControlApi:
    def __init__(self, runner):
        self.runner = runner
        self.debits = []
        self.environments = []
        self.artifacts = []
        self.resource_advances = []
        self.complete_checkpoints = []

    def publish_managed_artifact(
        self, _context, _lease, *, relative_path, payload
    ):
        for existing_path, existing_payload, existing_binding in self.artifacts:
            if existing_path == relative_path:
                if existing_payload != payload:
                    raise self.runner.TrainingRunnerBlocked(
                        "synthetic managed artifact collision"
                    )
                return existing_binding
        binding = {
            "path": relative_path,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        }
        self.artifacts.append((relative_path, payload, binding))
        return binding

    def perform_journaled_environment_access(
        self, _context, _lease, *, seed, arm, purpose, access
    ):
        assert purpose == "training"
        self.debits.append((arm, seed))
        return access()

    def reconcile_resource_ledger(self, _context, _lease):
        return {
            "resources": {
                "charged_seconds": len(self.debits) / 10.0,
                "environment_accesses": len(self.debits),
                "optimizer_steps": len(self.complete_checkpoints) * 2,
                "shadow_optimizer_steps": 0,
            }
        }

    def advance_resource_ledger(self, _context, _lease, **resources):
        self.resource_advances.append(copy.deepcopy(resources))
        return {"resources": copy.deepcopy(resources)}

    def publish_complete_training_checkpoint(
        self, _context, _lease, *, binding
    ):
        self.complete_checkpoints.append(copy.deepcopy(binding))
        return {"binding": copy.deepcopy(binding)}


def _run_fake_training_schedule(
    *, saturation_chunk=None, fail_after_debits=None, start_chunk=0
):
    runner = _runner()
    control = _FakeTrainingControlApi(runner)
    runtime = _FakeTrainingRuntimeApi(
        runner,
        saturation_chunk=saturation_chunk,
        fail_after_debits=fail_after_debits,
    )
    state = {"chunk_index": start_chunk}
    closeouts = []
    result = runner._run_training_schedule(
        control_api=control,
        runtime_api=runtime,
        context=object(),
        lease=object(),
        runtime_state=state,
        training_seeds=tuple(range(512)),
        environment_factory=lambda seed: control.environments.append(seed),
        deadline=100.0,
        clock=lambda: 0.0,
        closeout=lambda verdict, snapshot: closeouts.append(
            (verdict, copy.deepcopy(snapshot))
        ),
    )
    return runner, control, runtime, state, closeouts, result


def test_training_schedule_publishes_zero_checkpoint_and_eight_linked_chunks():
    runner, control, runtime, state, closeouts, result = _run_fake_training_schedule()

    assert state["chunk_index"] == 8
    assert len(runtime.chunk_calls) == 8
    assert control.debits == [
        (arm, seed) for seed in range(512) for arm in ("candidate", "control")
    ]
    assert control.environments == [seed for seed in range(512) for _ in range(2)]
    assert len(control.complete_checkpoints) == 8
    assert closeouts[0][0] == "training_completed_without_family_saturation"
    assert result["completed_chunks"] == 8
    assert result["environment_debits"] == 1024

    artifacts = {path: payload for path, payload, _binding in control.artifacts}
    assert "runtime_checkpoints/chunk_0000.json" in artifacts
    assert "checkpoint_chains/initial.json" in artifacts
    predecessor = artifacts["runtime_checkpoints/chunk_0000.json"]
    for index in range(1, 9):
        checkpoint = artifacts[f"runtime_checkpoints/chunk_{index:04d}.json"]
        chain = json.loads(artifacts[f"checkpoint_chains/chunk_{index:04d}.json"])
        assert chain["chunk_index"] == index - 1
        assert chain["seeds"] == list(range((index - 1) * 64, index * 64))
        assert chain["initial"]["checkpoint_sha256"] == hashlib.sha256(
            predecessor
        ).hexdigest()
        assert chain["final"]["checkpoint_sha256"] == hashlib.sha256(
            checkpoint
        ).hexdigest()
        predecessor = checkpoint
    assert set(control.complete_checkpoints[-1]["component_sha256"]) == {
        "candidate_card_generator",
        "candidate_model",
        "candidate_noncard_generator",
        "candidate_optimizer",
        "control_card_generator",
        "control_model",
        "control_noncard_generator",
        "control_optimizer",
    }
    final_checkpoint = json.loads(predecessor)
    assert control.complete_checkpoints[-1]["component_sha256"][
        "candidate_model"
    ] == runner.canonical_json_sha256(
        final_checkpoint["bootstrap"]["models"]["candidate"]
    )


def test_training_schedule_continues_only_after_exact_complete_predecessor():
    _runner_module, control, runtime, state, closeouts, result = (
        _run_fake_training_schedule(start_chunk=1)
    )

    assert state["chunk_index"] == 8
    assert [index for index, _seeds in runtime.chunk_calls] == list(range(1, 8))
    assert control.debits[0] == ("candidate", 64)
    assert control.debits[-1] == ("control", 511)
    assert len(control.debits) == 896
    assert len(control.complete_checkpoints) == 7
    assert closeouts[0][0] == "training_completed_without_family_saturation"
    assert result["completed_chunks"] == 8
    assert not any(
        path == "checkpoint_chains/initial.json"
        for path, _payload, _binding in control.artifacts
    )


def test_training_schedule_stops_and_closes_at_family_saturation_boundary():
    _runner_module, control, runtime, state, closeouts, result = (
        _run_fake_training_schedule(saturation_chunk=4)
    )

    assert state["chunk_index"] == 4
    assert len(runtime.chunk_calls) == 4
    assert len(control.debits) == 512
    assert len(control.complete_checkpoints) == 4
    assert closeouts[0][0] == (
        "experiment_stopped_during_training_for_family_saturation"
    )
    assert result["completed_chunks"] == 4
    assert not any(
        path.endswith("chunk_0005.json") for path, _payload, _binding in control.artifacts
    )


def test_training_schedule_preserves_partial_prefix_without_closeout_or_checkpoint():
    runner = _runner()
    control = _FakeTrainingControlApi(runner)
    runtime = _FakeTrainingRuntimeApi(runner, fail_after_debits=3)
    state = {"chunk_index": 0}
    closeouts = []

    with pytest.raises(RuntimeError, match="partial chunk"):
        runner._run_training_schedule(
            control_api=control,
            runtime_api=runtime,
            context=object(),
            lease=object(),
            runtime_state=state,
            training_seeds=tuple(range(512)),
            environment_factory=lambda seed: control.environments.append(seed),
            deadline=100.0,
            clock=lambda: 0.0,
            closeout=lambda verdict, snapshot: closeouts.append(
                (verdict, copy.deepcopy(snapshot))
            ),
        )

    assert control.debits == [("candidate", 0), ("control", 0), ("candidate", 1)]
    assert closeouts == []
    assert control.complete_checkpoints == []
    assert [path for path, _payload, _binding in control.artifacts] == [
        "runtime_checkpoints/chunk_0000.json",
        "checkpoint_chains/initial.json",
    ]


def _registered_input_fixture(*, include_request=False):
    runner = _runner()
    inventory = {
        "cohorts": {
            "canary": list(range(1_000, 1_128)),
            "holdout": list(range(2_000, 2_512)),
            "training": list(range(512)),
        },
        "inventory_sha256": "d" * 64,
    }
    inventory_payload = runner.canonical_json_bytes(inventory)
    registration_body = {
        "authority": {"training": False},
        "cohorts": copy.deepcopy(inventory["cohorts"]),
        "empirical_operations": {"training": False},
        "inventory_sha256": inventory["inventory_sha256"],
        "registration_id": "synthetic-r6-registration-v1",
        "schema_version": "synthetic-r6-registration-schema-v1",
    }
    registration = {
        **registration_body,
        "registration_sha256": runner.canonical_json_sha256(registration_body),
    }
    registration_payload = runner.canonical_json_bytes(registration)
    root = "D:/synthetic/registered-inputs"
    _base_runner, definition, payloads = _fixture(root)
    control = _control()
    source_inventory_binding = {
        "path": f"{root}/inventory/seed_inventory.json",
        "sha256": hashlib.sha256(inventory_payload).hexdigest(),
        "size_bytes": len(inventory_payload),
    }
    request = control.build_stage_request(
        stage="training",
        request_id="synthetic-r6-training-request-v1",
        source_commit=definition["registered_source"]["source_commit"],
        source_inventory_sha256=inventory["inventory_sha256"],
        configuration_identity=control.experiment_configuration_identity(),
        prerequisite_bindings={
            "registration_sha256": registration["registration_sha256"]
        },
        output_root=definition["output_root"],
    )
    payloads["registration"] = registration_payload
    payloads["training_request"] = control.canonical_json_bytes(request)
    definition["artifacts"]["registration"] = _binding(
        definition["artifacts"]["registration"]["path"], registration_payload
    )
    definition["artifacts"]["training_request"] = _binding(
        definition["artifacts"]["training_request"]["path"],
        payloads["training_request"],
    )
    definition["downstream_authority"] = copy.deepcopy(
        request["downstream_authority"]
    )
    definition["request_contract"] = {
        "downstream_authority": copy.deepcopy(request["downstream_authority"]),
        "execution_authority": copy.deepcopy(request["execution_authority"]),
        "output_root": definition["output_root"],
        "registration_sha256": registration["registration_sha256"],
        "request_sha256": request["request_sha256"],
        "resources": copy.deepcopy(request["resources"]),
        "source_commit": definition["registered_source"]["source_commit"],
        "source_inventory_sha256": inventory["inventory_sha256"],
    }
    definition["resources"] = copy.deepcopy(request["resources"])
    definition["source_inventory"] = source_inventory_binding
    definition["registered_source"]["source_inventory_sha256"] = inventory[
        "inventory_sha256"
    ]
    manifest = runner.build_launch_manifest(definition)
    composite = runner.build_runner_composite(manifest, "run-training")
    result = (
        runner,
        inventory,
        inventory_payload,
        registration,
        registration_payload,
        manifest,
        composite,
    )
    return (*result, request) if include_request else result


def _pre_access_receipt_binding(path, payload, calls=None):
    if calls is not None:
        calls.append("pre-access-receipt")
    return {
        "path": path.resolve().as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def test_registered_training_inputs_open_only_after_complete_authority():
    (
        runner,
        inventory,
        inventory_payload,
        registration,
        registration_payload,
        manifest,
        composite,
    ) = _registered_input_fixture()
    calls = []
    receipt_payloads = []
    rollback_sha256 = manifest["rollback_authority"]["rollback_authority_sha256"]

    result = runner._open_registered_training_inputs(
        authority_validator=lambda: (
            calls.append("authority")
            or {
                "command": "run-training",
                "composite_sha256": composite["composite_sha256"],
                "envelope_sha256": "a" * 64,
                "validated": True,
            }
        ),
        expected_envelope_sha256="a" * 64,
        expected_composite_sha256=composite["composite_sha256"],
        launch_manifest=manifest,
        output_root=Path(manifest["output_root"]),
        process_id=71_001,
        pre_access_receipt_publisher=lambda path, payload: (
            receipt_payloads.append((path, payload))
            or _pre_access_receipt_binding(path, payload, calls)
        ),
        registration_reader=lambda: (
            calls.append("registration") or registration_payload
        ),
        registration_binding=manifest["artifacts"]["registration"],
        inventory_reader=lambda: calls.append("inventory") or inventory_payload,
        inventory_binding=manifest["source_inventory"],
        inventory_parser=lambda payload: (
            calls.append("inventory-parser") or json.loads(payload)
        ),
        producer_validator=lambda value, evidence: (
            calls.append("producer")
            or (
                copy.deepcopy(value)
                if evidence == inventory
                else pytest.fail("producer received another inventory")
            )
        ),
        independent_verifier=lambda value, evidence: (
            calls.append("independent-verifier")
            or {
                "authority": copy.deepcopy(value["authority"]),
                "cohort_counts": {"canary": 128, "holdout": 512, "training": 512},
                "empirical_operations": copy.deepcopy(
                    value["empirical_operations"]
                ),
                "inventory_sha256": value["inventory_sha256"],
                "registration_id": value["registration_id"],
                "registration_sha256": value["registration_sha256"],
                "verified": evidence == inventory,
            }
        ),
        rollback_authority_sha256=rollback_sha256,
    )

    assert calls == [
        "authority",
        "pre-access-receipt",
        "registration",
        "inventory",
        "inventory-parser",
        "producer",
        "independent-verifier",
    ]
    assert result["training_seeds"] == tuple(range(512))
    assert result["registration"] == registration
    assert "rollback_authority_sha256" not in result["registration"]
    assert result["execution_registration"] == {
        **registration,
        "rollback_authority_sha256": rollback_sha256,
    }
    assert result["pre_access_receipt"]["path"].endswith(
        ".training.pre-access-71001.json"
    )
    receipt_path, receipt_payload = receipt_payloads[0]
    receipt = json.loads(receipt_payload)
    assert receipt_path.resolve().as_posix() == result["pre_access_receipt"]["path"]
    assert receipt["launch_manifest_sha256"] == manifest["manifest_sha256"]
    assert receipt["output_root"] == manifest["output_root"]
    assert receipt["process_id"] == 71_001
    assert receipt["receipt_path"] == result["pre_access_receipt"]["path"]
    assert receipt["registration"] == manifest["artifacts"]["registration"]
    assert receipt["source_inventory"] == manifest["source_inventory"]
    assert receipt["receipt_sha256"] == runner.canonical_json_sha256(
        {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    )
    assert runner.canonical_json_bytes(result["registration"]) == registration_payload


def test_registered_training_inputs_fail_before_any_protected_or_runtime_access():
    (
        runner,
        _inventory,
        inventory_payload,
        _registration,
        registration_payload,
        manifest,
        composite,
    ) = _registered_input_fixture()
    calls = []

    with pytest.raises(runner.TrainingRunnerBlocked, match="authority"):
        runner._open_registered_training_inputs(
            authority_validator=lambda: (_ for _ in ()).throw(
                runner.TrainingRunnerBlocked("synthetic authority failure")
            ),
            expected_envelope_sha256="a" * 64,
            expected_composite_sha256=composite["composite_sha256"],
            launch_manifest=manifest,
            output_root=Path(manifest["output_root"]),
            process_id=71_001,
            pre_access_receipt_publisher=lambda path, payload: _pre_access_receipt_binding(
                path, payload, calls
            ),
            registration_reader=lambda: calls.append("registration")
            or registration_payload,
            registration_binding=manifest["artifacts"]["registration"],
            inventory_reader=lambda: calls.append("inventory") or inventory_payload,
            inventory_binding=manifest["source_inventory"],
            inventory_parser=lambda payload: json.loads(payload),
            producer_validator=lambda value, evidence: value,
            independent_verifier=lambda value, evidence: {"verified": True},
            rollback_authority_sha256=manifest["rollback_authority"][
                "rollback_authority_sha256"
            ],
        )

    assert calls == []


@pytest.mark.parametrize("changed_field", ("envelope_sha256", "composite_sha256"))
def test_registered_training_inputs_reject_authorized_identity_substitution(
    changed_field,
):
    (
        runner,
        _inventory,
        inventory_payload,
        _registration,
        registration_payload,
        manifest,
        composite,
    ) = _registered_input_fixture()
    calls = []
    authority = {
        "command": "run-training",
        "composite_sha256": composite["composite_sha256"],
        "envelope_sha256": "a" * 64,
        "validated": True,
    }
    authority[changed_field] = "c" * 64

    with pytest.raises(runner.TrainingRunnerBlocked, match="authority"):
        runner._open_registered_training_inputs(
            authority_validator=lambda: authority,
            expected_envelope_sha256="a" * 64,
            expected_composite_sha256=composite["composite_sha256"],
            launch_manifest=manifest,
            output_root=Path(manifest["output_root"]),
            process_id=71_001,
            pre_access_receipt_publisher=lambda path, payload: _pre_access_receipt_binding(
                path, payload, calls
            ),
            registration_reader=lambda: calls.append("registration")
            or registration_payload,
            registration_binding=manifest["artifacts"]["registration"],
            inventory_reader=lambda: calls.append("inventory") or inventory_payload,
            inventory_binding=manifest["source_inventory"],
            inventory_parser=lambda payload: json.loads(payload),
            producer_validator=lambda value, evidence: value,
            independent_verifier=lambda value, evidence: {"verified": True},
            rollback_authority_sha256=manifest["rollback_authority"][
                "rollback_authority_sha256"
            ],
        )

    assert calls == []


@pytest.mark.parametrize(
    "changed_field", ("registration_path", "source_path", "output_root")
)
def test_registered_training_inputs_reject_manifest_binding_substitution(
    changed_field,
):
    (
        runner,
        _inventory,
        inventory_payload,
        _registration,
        registration_payload,
        manifest,
        composite,
    ) = _registered_input_fixture()
    calls = []
    registration_binding = copy.deepcopy(manifest["artifacts"]["registration"])
    inventory_binding = copy.deepcopy(manifest["source_inventory"])
    output_root = Path(manifest["output_root"])
    if changed_field == "registration_path":
        registration_binding["path"] = "synthetic/substituted-registration.bin"
    elif changed_field == "source_path":
        inventory_binding["path"] = (
            "D:/synthetic/registered-inputs/inventory/substituted.json"
        )
    else:
        output_root = output_root.parent / "substituted-training"

    with pytest.raises(runner.TrainingRunnerBlocked, match="manifest binding"):
        runner._open_registered_training_inputs(
            authority_validator=lambda: {
                "command": "run-training",
                "composite_sha256": composite["composite_sha256"],
                "envelope_sha256": "a" * 64,
                "validated": True,
            },
            expected_envelope_sha256="a" * 64,
            expected_composite_sha256=composite["composite_sha256"],
            launch_manifest=manifest,
            output_root=output_root,
            process_id=71_001,
            pre_access_receipt_publisher=lambda path, payload: (
                calls.append("pre-access-receipt")
            ),
            registration_reader=lambda: calls.append("registration")
            or registration_payload,
            registration_binding=registration_binding,
            inventory_reader=lambda: calls.append("inventory") or inventory_payload,
            inventory_binding=inventory_binding,
            inventory_parser=lambda payload: json.loads(payload),
            producer_validator=lambda value, evidence: value,
            independent_verifier=lambda value, evidence: {"verified": True},
            rollback_authority_sha256=manifest["rollback_authority"][
                "rollback_authority_sha256"
            ],
        )

    assert calls == []


def test_registered_training_inputs_reject_validator_disagreement():
    (
        runner,
        inventory,
        inventory_payload,
        registration,
        registration_payload,
        manifest,
        composite,
    ) = _registered_input_fixture()

    with pytest.raises(runner.TrainingRunnerBlocked, match="agreement"):
        runner._open_registered_training_inputs(
            authority_validator=lambda: {
                "command": "run-training",
                "composite_sha256": composite["composite_sha256"],
                "envelope_sha256": "a" * 64,
                "validated": True,
            },
            expected_envelope_sha256="a" * 64,
            expected_composite_sha256=composite["composite_sha256"],
            launch_manifest=manifest,
            output_root=Path(manifest["output_root"]),
            process_id=71_001,
            pre_access_receipt_publisher=_pre_access_receipt_binding,
            registration_reader=lambda: registration_payload,
            registration_binding=manifest["artifacts"]["registration"],
            inventory_reader=lambda: inventory_payload,
            inventory_binding=manifest["source_inventory"],
            inventory_parser=lambda payload: copy.deepcopy(inventory),
            producer_validator=lambda value, evidence: copy.deepcopy(value),
            independent_verifier=lambda value, evidence: {
                "authority": copy.deepcopy(value["authority"]),
                "cohort_counts": {"canary": 128, "holdout": 512, "training": 512},
                "empirical_operations": copy.deepcopy(
                    value["empirical_operations"]
                ),
                "inventory_sha256": value["inventory_sha256"],
                "registration_id": value["registration_id"],
                "registration_sha256": "f" * 64,
                "verified": True,
            },
            rollback_authority_sha256=manifest["rollback_authority"][
                "rollback_authority_sha256"
            ],
        )


@pytest.mark.parametrize("changed_field", ("path", "sha256"))
def test_registered_training_inputs_reject_receipt_binding_before_protected_reads(
    changed_field,
):
    (
        runner,
        _inventory,
        inventory_payload,
        _registration,
        registration_payload,
        manifest,
        composite,
    ) = _registered_input_fixture()
    calls = []

    with pytest.raises(runner.TrainingRunnerBlocked, match="receipt publication"):
        runner._open_registered_training_inputs(
            authority_validator=lambda: {
                "command": "run-training",
                "composite_sha256": composite["composite_sha256"],
                "envelope_sha256": "a" * 64,
                "validated": True,
            },
            expected_envelope_sha256="a" * 64,
            expected_composite_sha256=composite["composite_sha256"],
            launch_manifest=manifest,
            output_root=Path(manifest["output_root"]),
            process_id=71_001,
            pre_access_receipt_publisher=lambda path, payload: {
                **_pre_access_receipt_binding(path, payload, calls),
                changed_field: (
                    "D:/synthetic/wrong-pre-access-receipt.json"
                    if changed_field == "path"
                    else "f" * 64
                ),
            },
            registration_reader=lambda: calls.append("registration")
            or registration_payload,
            registration_binding=manifest["artifacts"]["registration"],
            inventory_reader=lambda: calls.append("inventory") or inventory_payload,
            inventory_binding=manifest["source_inventory"],
            inventory_parser=lambda payload: json.loads(payload),
            producer_validator=lambda value, evidence: value,
            independent_verifier=lambda value, evidence: {"verified": True},
            rollback_authority_sha256=manifest["rollback_authority"][
                "rollback_authority_sha256"
            ],
        )

    assert calls == ["pre-access-receipt"]


def test_pre_access_receipt_publisher_is_exclusive_and_durable(tmp_path):
    runner = _runner()
    path = tmp_path / ".training.pre-access-71001.json"
    payload = b"synthetic-receipt"

    binding = runner._publish_exclusive_pre_access_receipt(path, payload)

    assert path.read_bytes() == payload
    assert binding == {
        "path": path.resolve().as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }
    with pytest.raises(runner.TrainingRunnerBlocked, match="publication failed"):
        runner._publish_exclusive_pre_access_receipt(path, payload)
    assert list(path.parent.glob(f"{path.name}.*.staging")) == []


class _FakeExecutionLease:
    def __init__(self, calls, process_id, observed):
        self.calls = calls
        self.owner = {
            "acquired_monotonic": 1.0,
            "child_process_id": process_id,
            "token": f"{process_id:032x}",
        }
        recovery = observed["recovery"]
        self.acquisition_mode = recovery["mode"]
        self.acquisition_observation_sha256 = _runner().canonical_json_sha256(
            observed
        )
        self.reclaimed_owner = copy.deepcopy(recovery.get("old_owner"))
        self.reclaimed_lease_sha256 = recovery.get("lease_sha256")
        self.reclaimed_prefix_sha256 = recovery.get("prefix_sha256")

    def __enter__(self):
        self.calls.append("lease-enter")
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.calls.append("lease-exit")
        return False


class _FakeOuterTrainingControl(_FakeTrainingControlApi):
    def __init__(self, runner, calls, reopen):
        super().__init__(runner)
        self.calls = calls
        self.reopen = reopen

    def initialize_access_journal(self, _context, _lease):
        self.calls.append("journal")

    def initialize_resource_ledger(self, _context, _lease):
        self.calls.append("resource")

    def publish_managed_artifact(
        self, context, lease, *, relative_path, payload
    ):
        if relative_path == "runner_launch.json":
            self.calls.append("runner-launch-marker")
        elif relative_path.startswith("continuation_attempts/"):
            self.calls.append("continuation-attempt-marker")
        return super().publish_managed_artifact(
            context, lease, relative_path=relative_path, payload=payload
        )

    def classify_execution_reopen(self, _context, _lease):
        self.calls.append("classify-reopen")
        if isinstance(self.reopen, Exception):
            raise self.reopen
        return copy.deepcopy(self.reopen)

    def authorize_training_continuation(self, _context, _lease):
        self.calls.append("authorize-continuation")
        return copy.deepcopy(self.reopen)

    def publish_write_once_marker(self, _context, _lease, *, kind, payload):
        self.calls.append(f"{kind}-marker")
        return {"kind": kind, "payload": copy.deepcopy(payload)}


class _CollisionOuterTrainingControl(_FakeOuterTrainingControl):
    def publish_managed_artifact(
        self, context, lease, *, relative_path, payload
    ):
        if relative_path.startswith("continuation_attempts/"):
            self.calls.append("continuation-attempt-collision")
            raise self.runner.TrainingRunnerBlocked(
                "synthetic managed artifact collision"
            )
        return super().publish_managed_artifact(
            context, lease, relative_path=relative_path, payload=payload
        )


def _outer_registered_inputs(start_chunk=0):
    return {
        "authority": {
            "command": "run-training",
            "composite_sha256": "b" * 64,
            "envelope_sha256": "a" * 64,
            "validated": True,
        },
        "execution_registration": {
            "registration_sha256": "c" * 64,
            "rollback_authority_sha256": "d" * 64,
        },
        "registration": {"registration_sha256": "c" * 64},
        "training_seeds": tuple(range(512)),
        "start_chunk": start_chunk,
    }


def _setup_reopen_observation():
    return {
        "classification": {
            "debited_accesses": 0,
            "identity": {"audit_id": "synthetic-training"},
            "verdict": "pre_seed_setup_reopen",
        },
        "recovery": {"mode": "fresh_output"},
    }


def _outer_context_identity():
    return {"audit_id": "synthetic-training"}


def _synthetic_artifact_inventory(runner, runner_launch_sha256=None):
    artifacts = []
    if runner_launch_sha256 is not None:
        artifacts.append(
            {
                "encoding": "identity-bytes-v1",
                "path": "runner_launch.json",
                "stored_sha256": runner_launch_sha256,
                "stored_size_bytes": 1,
                "uncompressed_sha256": runner_launch_sha256,
                "uncompressed_size_bytes": 1,
            }
        )
    body = {
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "schema_version": runner.CONTROL_ARTIFACT_INVENTORY_SCHEMA_VERSION,
        "stored_size_bytes": len(artifacts),
        "uncompressed_size_bytes": len(artifacts),
    }
    return {
        **body,
        "artifact_inventory_sha256": runner.canonical_json_sha256(body),
    }


def _stale_setup_reopen_observation(runner, runner_launch_sha256):
    classification = _setup_reopen_observation()["classification"]
    artifact_inventory = _synthetic_artifact_inventory(
        runner, runner_launch_sha256
    )
    return {
        "classification": classification,
        "recovery": {
            "artifact_inventory": artifact_inventory,
            "lease_sha256": "7" * 64,
            "mode": "dead_owner_reclaim",
            "old_owner": {
                "acquired_monotonic": 0.0,
                "child_process_id": 70_001,
                "token": "1" * 32,
            },
            "prefix_sha256": runner.canonical_json_sha256(
                {
                    "artifact_inventory": artifact_inventory,
                    "classification": classification,
                    "context_identity": _outer_context_identity(),
                }
            ),
            "runner_launch": {
                "sha256": runner_launch_sha256,
                "state": "present",
            },
        },
    }


def _continuation_reopen_observation(
    runner, checkpoint_sha256, runner_launch_sha256="8" * 64
):
    classification = {
        "checkpoint_sha256": checkpoint_sha256,
        "completed_pairs": 64,
        "debited_accesses": 128,
        "identity": _outer_context_identity(),
        "next_chunk_index": 1,
        "verdict": "complete_checkpoint_continuation",
    }
    artifact_inventory = _synthetic_artifact_inventory(
        runner, runner_launch_sha256
    )
    return {
        "classification": classification,
        "recovery": {
            "artifact_inventory": artifact_inventory,
            "lease_sha256": "7" * 64,
            "mode": "dead_owner_reclaim",
            "old_owner": {
                "acquired_monotonic": 0.0,
                "child_process_id": 70_001,
                "token": "1" * 32,
            },
            "prefix_sha256": runner.canonical_json_sha256(
                {
                    "artifact_inventory": artifact_inventory,
                    "classification": classification,
                    "context_identity": _outer_context_identity(),
                }
            ),
            "runner_launch": {
                "sha256": runner_launch_sha256,
                "state": "present",
            },
        },
    }


def _real_training_context(control, output):
    registration_body = {
        "registration_id": "synthetic-runner-registration-v1",
        "schema_version": "synthetic-runner-registration-schema-v1",
    }
    registration = {
        **registration_body,
        "registration_sha256": control.canonical_json_sha256(registration_body),
    }
    request = control.build_stage_request(
        stage="training",
        request_id="synthetic-runner-training-request-v1",
        source_commit="a" * 40,
        source_inventory_sha256="b" * 64,
        configuration_identity=control.experiment_configuration_identity(),
        prerequisite_bindings={
            "registration_sha256": registration["registration_sha256"]
        },
        output_root=output.resolve().as_posix(),
    )
    authorization = control.build_stage_authorization(
        request=request,
        authorization_id="synthetic-runner-training-authorization-v1",
        request_review_sha256="c" * 64,
        approval_record_sha256="d" * 64,
    )
    return control._build_validated_execution_context(
        registration=registration,
        request=request,
        authorization=authorization,
        registration_validator=lambda value: copy.deepcopy(dict(value)),
    )


def test_read_only_reopen_observer_and_atomic_lease_create_fresh_output(tmp_path):
    runner = _runner()
    control = _control()
    output = tmp_path / "fresh-training"
    context = _real_training_context(control, output)

    observation = runner._observe_training_reopen_read_only(
        control_api=control,
        context=context,
        output_root=output,
        process_alive=lambda _process_id: False,
    )

    assert observation == {
        "classification": {
            "debited_accesses": 0,
            "identity": control._context_identity(context),
            "verdict": "pre_seed_setup_reopen",
        },
        "recovery": {"mode": "fresh_output"},
    }
    with runner._AtomicObservedExecutionLease(
        control_api=control,
        context=context,
        output_root=output,
        observation=observation,
        child_process_id=72_001,
        process_alive=lambda process_id: process_id == 72_001,
        clock=lambda: 1.0,
    ) as lease:
        assert lease.owner["child_process_id"] == 72_001
        assert lease.reclaimed_owner is None
        assert lease.acquisition_mode == "fresh_output"
        control.initialize_access_journal(context, lease)
        control.initialize_resource_ledger(context, lease)
        assert control.classify_execution_reopen(context, lease) == observation[
            "classification"
        ]


def _dead_zero_debit_output(runner, control, context, output, old_process_id):
    with control.ExecutionLease(
        output,
        context=context,
        child_process_id=old_process_id,
        process_alive=lambda process_id: process_id == old_process_id,
        clock=lambda: 0.0,
    ) as lease:
        control.initialize_access_journal(context, lease)
        control.initialize_resource_ledger(context, lease)
        control.publish_managed_artifact(
            context,
            lease,
            relative_path="runner_launch.json",
            payload=runner._runner_launch_payload(
                manifest_sha256="9" * 64,
                process_id=old_process_id,
                rollback_authority_sha256="d" * 64,
                run_envelope_sha256="a" * 64,
            ),
        )


def test_atomic_observed_lease_reclaims_exact_dead_zero_debit_prefix(tmp_path):
    runner = _runner()
    control = _control()
    output = tmp_path / "stale-training"
    context = _real_training_context(control, output)
    old_process_id = 72_010
    new_process_id = 72_011
    _dead_zero_debit_output(runner, control, context, output, old_process_id)
    process_alive = lambda process_id: process_id == new_process_id
    observation = runner._observe_training_reopen_read_only(
        control_api=control,
        context=context,
        output_root=output,
        process_alive=process_alive,
    )

    with runner._AtomicObservedExecutionLease(
        control_api=control,
        context=context,
        output_root=output,
        observation=observation,
        child_process_id=new_process_id,
        process_alive=process_alive,
        clock=lambda: 2.0,
    ) as lease:
        assert lease.reclaimed_owner == observation["recovery"]["old_owner"]
        assert lease.reclaimed_lease_sha256 == observation["recovery"][
            "lease_sha256"
        ]
        assert lease.reclaimed_prefix_sha256 == observation["recovery"][
            "prefix_sha256"
        ]
        assert control.classify_execution_reopen(context, lease) == observation[
            "classification"
        ]


def test_atomic_observed_lease_rejects_prefix_race_without_rewriting_lease(
    tmp_path,
):
    runner = _runner()
    control = _control()
    output = tmp_path / "raced-training"
    context = _real_training_context(control, output)
    old_process_id = 72_020
    new_process_id = 72_021
    _dead_zero_debit_output(runner, control, context, output, old_process_id)
    process_alive = lambda process_id: process_id == new_process_id
    observation = runner._observe_training_reopen_read_only(
        control_api=control,
        context=context,
        output_root=output,
        process_alive=process_alive,
    )
    lease_path = output / control.LEASE_FILENAME
    original_lease = lease_path.read_bytes()
    (output / "raced-artifact.json").write_bytes(b"{}")

    with pytest.raises(runner.TrainingRunnerBlocked, match="prefix changed"):
        with runner._AtomicObservedExecutionLease(
            control_api=control,
            context=context,
            output_root=output,
            observation=observation,
            child_process_id=new_process_id,
            process_alive=process_alive,
            clock=lambda: 2.0,
        ):
            pytest.fail("raced prefix acquired an execution lease")

    assert lease_path.read_bytes() == original_lease


def test_atomic_observed_lease_fresh_commit_failure_leaves_output_absent(
    tmp_path, monkeypatch
):
    runner = _runner()
    control = _control()
    output = tmp_path / "failed-fresh-training"
    context = _real_training_context(control, output)
    observation = runner._observe_training_reopen_read_only(
        control_api=control,
        context=context,
        output_root=output,
        process_alive=lambda _process_id: False,
    )
    monkeypatch.setattr(
        runner,
        "_move_path_write_through",
        lambda source, destination, **kwargs: (_ for _ in ()).throw(
            OSError("synthetic fresh move failure")
        ),
    )

    with pytest.raises(runner.TrainingRunnerBlocked, match="atomic execution"):
        with runner._AtomicObservedExecutionLease(
            control_api=control,
            context=context,
            output_root=output,
            observation=observation,
            child_process_id=72_031,
            process_alive=lambda process_id: process_id == 72_031,
            clock=lambda: 1.0,
        ):
            pytest.fail("failed fresh commit acquired a lease")

    assert not output.exists()
    assert list(output.parent.glob(f".{output.name}.*.staging")) == []


def test_atomic_observed_lease_stale_commit_failure_preserves_old_lease(
    tmp_path, monkeypatch
):
    runner = _runner()
    control = _control()
    output = tmp_path / "failed-stale-training"
    context = _real_training_context(control, output)
    old_process_id = 72_040
    new_process_id = 72_041
    _dead_zero_debit_output(runner, control, context, output, old_process_id)
    process_alive = lambda process_id: process_id == new_process_id
    observation = runner._observe_training_reopen_read_only(
        control_api=control,
        context=context,
        output_root=output,
        process_alive=process_alive,
    )
    lease_path = output / control.LEASE_FILENAME
    original_lease = lease_path.read_bytes()
    monkeypatch.setattr(
        runner,
        "_move_path_write_through",
        lambda source, destination, **kwargs: (_ for _ in ()).throw(
            OSError("synthetic stale move failure")
        ),
    )

    with pytest.raises(runner.TrainingRunnerBlocked, match="atomic execution"):
        with runner._AtomicObservedExecutionLease(
            control_api=control,
            context=context,
            output_root=output,
            observation=observation,
            child_process_id=new_process_id,
            process_alive=process_alive,
            clock=lambda: 2.0,
        ):
            pytest.fail("failed stale commit acquired a lease")

    assert lease_path.read_bytes() == original_lease
    assert list(
        output.parent.glob(f".{output.name}.lease.*.staging")
    ) == []


def test_atomic_stale_cleanup_failure_keeps_residue_outside_managed_output(
    tmp_path, monkeypatch
):
    runner = _runner()
    control = _control()
    output = tmp_path / "cleanup-failed-stale-training"
    context = _real_training_context(control, output)
    old_process_id = 72_050
    new_process_id = 72_051
    _dead_zero_debit_output(runner, control, context, output, old_process_id)
    process_alive = lambda process_id: process_id == new_process_id
    observation = runner._observe_training_reopen_read_only(
        control_api=control,
        context=context,
        output_root=output,
        process_alive=process_alive,
    )
    lease_path = output / control.LEASE_FILENAME
    original_lease = lease_path.read_bytes()
    monkeypatch.setattr(
        runner,
        "_move_path_write_through",
        lambda source, destination, **kwargs: (_ for _ in ()).throw(
            OSError("synthetic stale move failure")
        ),
    )
    monkeypatch.setattr(
        runner._AtomicObservedExecutionLease,
        "_cleanup_stage",
        staticmethod(lambda path: None),
    )

    with pytest.raises(runner.TrainingRunnerBlocked, match="atomic execution"):
        with runner._AtomicObservedExecutionLease(
            control_api=control,
            context=context,
            output_root=output,
            observation=observation,
            child_process_id=new_process_id,
            process_alive=process_alive,
            clock=lambda: 2.0,
        ):
            pytest.fail("cleanup-failed stale commit acquired a lease")

    residues = list(
        output.parent.glob(f".{output.name}.lease.*.staging")
    )
    assert len(residues) == 1
    assert lease_path.read_bytes() == original_lease
    assert runner._observe_training_reopen_read_only(
        control_api=control,
        context=context,
        output_root=output,
        process_alive=process_alive,
    ) == observation
    residues[0].unlink()


def test_read_only_reopen_rejects_malformed_prior_reclaimed_owner(tmp_path):
    runner = _runner()
    control = _control()
    output = tmp_path / "malformed-reclaimed-owner"
    context = _real_training_context(control, output)
    old_process_id = 72_060
    _dead_zero_debit_output(runner, control, context, output, old_process_id)
    lease_path = output / control.LEASE_FILENAME
    lease = json.loads(lease_path.read_bytes())
    lease["reclaimed_owner"] = "malformed-owner"
    lease_path.write_bytes(runner.canonical_json_bytes(lease))

    with pytest.raises(runner.TrainingRunnerBlocked, match="reclaimed lease owner"):
        runner._observe_training_reopen_read_only(
            control_api=control,
            context=context,
            output_root=output,
            process_alive=lambda _process_id: False,
        )


@pytest.mark.parametrize(
    "changed_field",
    (
        "schema_version",
        "artifact_count",
        "stored_size_bytes",
        "duplicate_path",
        "invalid_path",
        "identity_digest",
    ),
)
def test_artifact_inventory_rejects_re_self_digested_semantic_drift(
    changed_field,
):
    runner = _runner()
    inventory = _synthetic_artifact_inventory(runner, "8" * 64)
    if changed_field == "schema_version":
        inventory["schema_version"] = "substituted-schema-v1"
    elif changed_field == "artifact_count":
        inventory["artifact_count"] = 2
    elif changed_field == "stored_size_bytes":
        inventory["stored_size_bytes"] = 2
    elif changed_field == "duplicate_path":
        inventory["artifacts"].append(copy.deepcopy(inventory["artifacts"][0]))
        inventory["artifact_count"] = 2
        inventory["stored_size_bytes"] = 2
        inventory["uncompressed_size_bytes"] = 2
    elif changed_field == "invalid_path":
        inventory["artifacts"][0]["path"] = "../runner_launch.json"
    else:
        inventory["artifacts"][0]["uncompressed_sha256"] = "f" * 64
    body = {
        key: value
        for key, value in inventory.items()
        if key != "artifact_inventory_sha256"
    }
    inventory["artifact_inventory_sha256"] = runner.canonical_json_sha256(body)

    with pytest.raises(runner.TrainingRunnerBlocked):
        runner._validated_artifact_inventory(inventory)


@pytest.mark.parametrize(
    "changed_field",
    (
        "completed_pairs",
        "debited_accesses",
        "context_identity",
        "prefix_sha256",
        "old_owner_extra",
        "old_owner_token",
    ),
)
def test_read_only_continuation_observation_rejects_identity_drift(changed_field):
    runner = _runner()
    observation = _continuation_reopen_observation(runner, "6" * 64)
    if changed_field == "completed_pairs":
        observation["classification"]["completed_pairs"] = 63
    elif changed_field == "debited_accesses":
        observation["classification"]["debited_accesses"] = 127
    elif changed_field == "context_identity":
        observation["classification"]["identity"] = {"audit_id": "substituted"}
    elif changed_field == "prefix_sha256":
        observation["recovery"]["prefix_sha256"] = "f" * 64
    elif changed_field == "old_owner_extra":
        observation["recovery"]["old_owner"]["extra"] = True
    else:
        observation["recovery"]["old_owner"]["token"] = "not-a-token"

    with pytest.raises(runner.TrainingRunnerBlocked):
        runner._validated_reopen_observation(
            observation,
            expected_context_identity=_outer_context_identity(),
            process_alive=lambda _process_id: False,
        )


def test_read_only_continuation_observation_requires_dead_owner():
    runner = _runner()
    observation = _continuation_reopen_observation(runner, "6" * 64)

    with pytest.raises(runner.TrainingRunnerBlocked, match="not dead"):
        runner._validated_reopen_observation(
            observation,
            expected_context_identity=_outer_context_identity(),
            process_alive=lambda _process_id: True,
        )


@pytest.mark.parametrize(
    "changed_field",
    (
        "launch_manifest_sha256",
        "rollback_authority_sha256",
        "run_envelope_sha256",
    ),
)
def test_original_runner_launch_rejects_re_self_digested_identity_drift(
    changed_field,
):
    runner = _runner()
    launch = json.loads(
        runner._runner_launch_payload(
            manifest_sha256="9" * 64,
            process_id=70_001,
            rollback_authority_sha256="d" * 64,
            run_envelope_sha256="a" * 64,
        )
    )
    launch[changed_field] = "f" * 64
    body = {key: value for key, value in launch.items() if key != "launch_sha256"}
    launch["launch_sha256"] = runner.canonical_json_sha256(body)

    with pytest.raises(runner.TrainingRunnerBlocked, match="launch differs"):
        runner._validated_original_runner_launch(
            runner.canonical_json_bytes(launch),
            manifest_sha256="9" * 64,
            rollback_authority_sha256="d" * 64,
            run_envelope_sha256="a" * 64,
        )


def test_training_lifecycle_setup_orders_authority_lease_marker_and_lazy_loaders():
    runner = _runner()
    calls = []
    control = _FakeOuterTrainingControl(
        runner,
        calls,
        _setup_reopen_observation()["classification"],
    )
    runtime = _FakeTrainingRuntimeApi(runner)
    closeouts = []

    result = runner._execute_training_lifecycle(
        control_api=control,
        registered_inputs_loader=lambda: calls.append("registered-inputs")
        or _outer_registered_inputs(),
        context_builder=lambda execution_registration: calls.append("context")
        or copy.deepcopy(execution_registration),
        context_identity_observer=lambda context: _outer_context_identity(),
        reopen_observer=lambda output, context, process_alive: (
            calls.append("reopen-observer") or _setup_reopen_observation()
        ),
        lease_factory=lambda output, context, observed, process_id, process_alive, clock: (
            calls.append("lease-factory")
            or _FakeExecutionLease(calls, process_id, observed)
        ),
        runtime_loader=lambda: calls.append("runtime-loader") or runtime,
        environment_factory_loader=lambda: calls.append("environment-loader")
        or (lambda seed: control.environments.append(seed)),
        checkpoint_reader=lambda _path: pytest.fail("setup read a checkpoint"),
        launch_marker_reader=lambda _path: pytest.fail(
            "setup read an original launch marker"
        ),
        output_root=Path("D:/synthetic/training-output"),
        manifest_sha256="9" * 64,
        run_envelope_sha256="a" * 64,
        rollback_authority_sha256="d" * 64,
        process_id=71_001,
        process_alive=lambda process_id: process_id == 71_001,
        deadline=100.0,
        clock=lambda: 0.0,
        closeout=lambda verdict, snapshot: closeouts.append((verdict, snapshot)),
    )

    assert calls[:11] == [
        "registered-inputs",
        "context",
        "reopen-observer",
        "lease-factory",
        "lease-enter",
        "journal",
        "resource",
        "classify-reopen",
        "runner-launch-marker",
        "runtime-loader",
        "bootstrap-marker",
    ]
    assert calls.index("stage-marker") < calls.index("environment-loader")
    assert calls[-1] == "lease-exit"
    assert result["verdict"] == "training_completed_without_family_saturation"
    assert closeouts[0][0] == "training_completed_without_family_saturation"


@pytest.mark.parametrize(
    "changed_field",
    (
        "acquisition_mode",
        "acquisition_observation_sha256",
        "current_owner_process_id",
        "reclaimed_owner",
        "reclaimed_lease_sha256",
        "reclaimed_prefix_sha256",
    ),
)
def test_training_lifecycle_rejects_compare_and_acquire_drift_before_writes(
    changed_field,
):
    runner = _runner()
    calls = []
    observation = _setup_reopen_observation()
    control = _FakeOuterTrainingControl(
        runner, calls, observation["classification"]
    )

    def lease_factory(output, context, observed, process_id, process_alive, clock):
        calls.append("lease-factory")
        lease = _FakeExecutionLease(calls, process_id, observed)
        if changed_field == "current_owner_process_id":
            lease.owner["child_process_id"] = 1
        else:
            setattr(
                lease,
                changed_field,
                {"child_process_id": 1}
                if changed_field == "reclaimed_owner"
                else "f" * 64,
            )
        return lease

    with pytest.raises(runner.TrainingRunnerBlocked, match="lease"):
        runner._execute_training_lifecycle(
            control_api=control,
            registered_inputs_loader=lambda: _outer_registered_inputs(),
            context_builder=lambda execution_registration: copy.deepcopy(
                execution_registration
            ),
            context_identity_observer=lambda context: _outer_context_identity(),
            reopen_observer=lambda output, context, process_alive: copy.deepcopy(
                observation
            ),
            lease_factory=lease_factory,
            runtime_loader=lambda: calls.append("runtime-loader"),
            environment_factory_loader=lambda: calls.append("environment-loader"),
            checkpoint_reader=lambda path: calls.append("checkpoint-reader"),
            launch_marker_reader=lambda path: calls.append("launch-marker-reader"),
            output_root=Path("D:/synthetic/training-output"),
            manifest_sha256="9" * 64,
            run_envelope_sha256="a" * 64,
            rollback_authority_sha256="d" * 64,
            process_id=71_006,
            process_alive=lambda process_id: process_id == 71_006,
            deadline=100.0,
            clock=lambda: 0.0,
            closeout=lambda _verdict, _snapshot: None,
        )

    assert "lease-enter" in calls
    assert "journal" not in calls
    assert "resource" not in calls
    assert "classify-reopen" not in calls
    assert "runtime-loader" not in calls


def test_training_lifecycle_stale_setup_preserves_original_launch():
    runner = _runner()
    calls = []
    original_launch = runner._runner_launch_payload(
        manifest_sha256="9" * 64,
        process_id=70_001,
        rollback_authority_sha256="d" * 64,
        run_envelope_sha256="a" * 64,
    )
    observation = _stale_setup_reopen_observation(
        runner, hashlib.sha256(original_launch).hexdigest()
    )
    control = _FakeOuterTrainingControl(
        runner, calls, observation["classification"]
    )
    runtime = _FakeTrainingRuntimeApi(runner)

    result = runner._execute_training_lifecycle(
        control_api=control,
        registered_inputs_loader=lambda: _outer_registered_inputs(),
        context_builder=lambda execution_registration: copy.deepcopy(
            execution_registration
        ),
        context_identity_observer=lambda context: _outer_context_identity(),
        reopen_observer=lambda output, context, process_alive: copy.deepcopy(
            observation
        ),
        lease_factory=lambda output, context, observed, process_id, process_alive, clock: (
            _FakeExecutionLease(calls, process_id, observed)
        ),
        runtime_loader=lambda: calls.append("runtime-loader") or runtime,
        environment_factory_loader=lambda: (
            lambda seed: control.environments.append(seed)
        ),
        checkpoint_reader=lambda path: pytest.fail("stale setup read checkpoint"),
        launch_marker_reader=lambda path: calls.append(
            f"launch-marker-read:{path.name}"
        )
        or original_launch,
        output_root=Path("D:/synthetic/training-output"),
        manifest_sha256="9" * 64,
        run_envelope_sha256="a" * 64,
        rollback_authority_sha256="d" * 64,
        process_id=71_005,
        process_alive=lambda process_id: process_id == 71_005,
        deadline=100.0,
        clock=lambda: 0.0,
        closeout=lambda _verdict, _snapshot: None,
    )

    assert result["completed_chunks"] == 8
    assert "runner-launch-marker" not in calls
    assert calls.index("classify-reopen") < calls.index("journal")
    reopen_path, reopen_payload, _binding = next(
        artifact
        for artifact in control.artifacts
        if artifact[0].startswith("reopen_attempts/")
    )
    reopen_attempt = json.loads(reopen_payload)
    assert reopen_path == (
        f"reopen_attempts/{reopen_attempt['attempt_sha256']}.json"
    )
    assert reopen_attempt["verdict"] == "pre_seed_setup_reopen"
    assert "checkpoint_sha256" not in reopen_attempt
    assert "continuation_authorization_sha256" not in reopen_attempt


def test_training_lifecycle_continuation_restores_exact_complete_checkpoint():
    runner = _runner()
    calls = []
    checkpoint = _fake_runtime_checkpoint(runner, 1)
    checkpoint_sha256 = hashlib.sha256(checkpoint).hexdigest()
    original_launch = runner._runner_launch_payload(
        manifest_sha256="9" * 64,
        process_id=70_001,
        rollback_authority_sha256="d" * 64,
        run_envelope_sha256="a" * 64,
    )
    observation = _continuation_reopen_observation(
        runner,
        checkpoint_sha256,
        hashlib.sha256(original_launch).hexdigest(),
    )
    reopen = observation["classification"]
    control = _FakeOuterTrainingControl(runner, calls, reopen)
    runtime = _FakeTrainingRuntimeApi(runner)

    result = runner._execute_training_lifecycle(
        control_api=control,
        registered_inputs_loader=lambda: calls.append("registered-inputs")
        or _outer_registered_inputs(start_chunk=1),
        context_builder=lambda execution_registration: copy.deepcopy(
            execution_registration
        ),
        context_identity_observer=lambda context: _outer_context_identity(),
        reopen_observer=lambda output, context, process_alive: (
            calls.append("reopen-observer") or copy.deepcopy(observation)
        ),
        lease_factory=lambda output, context, observed, process_id, process_alive, clock: (
            calls.append("lease-factory")
            or _FakeExecutionLease(calls, process_id, observed)
        ),
        runtime_loader=lambda: calls.append("runtime-loader") or runtime,
        environment_factory_loader=lambda: calls.append("environment-loader")
        or (lambda seed: control.environments.append(seed)),
        checkpoint_reader=lambda path: calls.append(f"checkpoint-read:{path.name}")
        or checkpoint,
        launch_marker_reader=lambda path: calls.append(
            f"launch-marker-read:{path.name}"
        )
        or original_launch,
        output_root=Path("D:/synthetic/training-output"),
        manifest_sha256="9" * 64,
        run_envelope_sha256="a" * 64,
        rollback_authority_sha256="d" * 64,
        process_id=71_002,
        process_alive=lambda process_id: process_id == 71_002,
        deadline=100.0,
        clock=lambda: 0.0,
        closeout=lambda _verdict, _snapshot: None,
    )

    assert calls.index("authorize-continuation") < calls.index(
        "checkpoint-read:chunk_0001.json"
    )
    assert calls.index("launch-marker-read:runner_launch.json") < calls.index(
        "lease-factory"
    )
    assert "runner-launch-marker" not in calls
    assert calls.index("continuation-attempt-marker") < calls.index(
        "runtime-loader"
    )
    attempt_path, attempt_payload, attempt_binding = next(
        artifact
        for artifact in control.artifacts
        if artifact[0].startswith("continuation_attempts/")
    )
    attempt = json.loads(attempt_payload)
    attempt_body = {
        key: value for key, value in attempt.items() if key != "attempt_sha256"
    }
    assert attempt_path == f"continuation_attempts/{attempt['attempt_sha256']}.json"
    assert attempt_binding["sha256"] == hashlib.sha256(attempt_payload).hexdigest()
    assert attempt["attempt_sha256"] == runner.canonical_json_sha256(attempt_body)
    assert attempt["checkpoint_sha256"] == checkpoint_sha256
    assert attempt["continuation_authorization_sha256"] == (
        runner.canonical_json_sha256(reopen)
    )
    assert attempt["current_owner"] == {
        "acquired_monotonic": 1.0,
        "child_process_id": 71_002,
        "token": f"{71_002:032x}",
    }
    assert attempt["launch_manifest_sha256"] == "9" * 64
    assert attempt["next_chunk_index"] == 1
    assert attempt["original_launch_sha256"] == json.loads(original_launch)[
        "launch_sha256"
    ]
    assert attempt["prior_lease_sha256"] == observation["recovery"][
        "lease_sha256"
    ]
    assert attempt["prior_owner"] == observation["recovery"]["old_owner"]
    assert attempt["prior_prefix_sha256"] == observation["recovery"][
        "prefix_sha256"
    ]
    assert attempt["rollback_authority_sha256"] == "d" * 64
    assert attempt["run_envelope_sha256"] == "a" * 64
    assert control.debits[0] == ("candidate", 64)
    assert result["completed_chunks"] == 8


def test_training_lifecycle_attempt_collision_blocks_before_runtime_loading():
    runner = _runner()
    calls = []
    checkpoint = _fake_runtime_checkpoint(runner, 1)
    checkpoint_sha256 = hashlib.sha256(checkpoint).hexdigest()
    original_launch = runner._runner_launch_payload(
        manifest_sha256="9" * 64,
        process_id=70_001,
        rollback_authority_sha256="d" * 64,
        run_envelope_sha256="a" * 64,
    )
    observation = _continuation_reopen_observation(
        runner,
        checkpoint_sha256,
        hashlib.sha256(original_launch).hexdigest(),
    )
    control = _CollisionOuterTrainingControl(
        runner, calls, observation["classification"]
    )

    with pytest.raises(runner.TrainingRunnerBlocked, match="collision"):
        runner._execute_training_lifecycle(
            control_api=control,
            registered_inputs_loader=lambda: _outer_registered_inputs(start_chunk=1),
            context_builder=lambda execution_registration: copy.deepcopy(
                execution_registration
            ),
            context_identity_observer=lambda context: _outer_context_identity(),
            reopen_observer=lambda output, context, process_alive: copy.deepcopy(
                observation
            ),
            lease_factory=lambda output, context, observed, process_id, process_alive, clock: (
                _FakeExecutionLease(calls, process_id, observed)
            ),
            runtime_loader=lambda: calls.append("runtime-loader"),
            environment_factory_loader=lambda: calls.append("environment-loader"),
            checkpoint_reader=lambda path: calls.append(
                f"checkpoint-read:{path.name}"
            )
            or checkpoint,
            launch_marker_reader=lambda path: original_launch,
            output_root=Path("D:/synthetic/training-output"),
            manifest_sha256="9" * 64,
            run_envelope_sha256="a" * 64,
            rollback_authority_sha256="d" * 64,
            process_id=71_004,
            process_alive=lambda process_id: process_id == 71_004,
            deadline=100.0,
            clock=lambda: 0.0,
            closeout=lambda _verdict, _snapshot: None,
        )

    assert "continuation-attempt-collision" in calls
    assert "runtime-loader" not in calls
    assert "environment-loader" not in calls
    assert not any(call.startswith("checkpoint-read:") for call in calls)


def test_training_lifecycle_partial_reopen_blocks_before_runtime_loading():
    runner = _runner()
    calls = []
    control = _FakeOuterTrainingControl(
        runner,
        calls,
        _setup_reopen_observation()["classification"],
    )

    with pytest.raises(runner.TrainingRunnerBlocked, match="partial"):
        runner._execute_training_lifecycle(
            control_api=control,
            registered_inputs_loader=lambda: calls.append("registered-inputs")
            or _outer_registered_inputs(),
            context_builder=lambda execution_registration: copy.deepcopy(
                execution_registration
            ),
            context_identity_observer=lambda context: _outer_context_identity(),
            reopen_observer=lambda output, context, process_alive: (
                calls.append("reopen-observer")
                or (_ for _ in ()).throw(
                    runner.TrainingRunnerBlocked("partial checkpoint prefix")
                )
            ),
            lease_factory=lambda output, context, observed, process_id, process_alive, clock: (
                calls.append("lease-factory")
                or _FakeExecutionLease(calls, process_id, observed)
            ),
            runtime_loader=lambda: calls.append("runtime-loader"),
            environment_factory_loader=lambda: calls.append("environment-loader"),
            checkpoint_reader=lambda path: calls.append(f"checkpoint-read:{path.name}"),
            launch_marker_reader=lambda path: calls.append(
                f"launch-marker-read:{path.name}"
            ),
            output_root=Path("D:/synthetic/training-output"),
            manifest_sha256="9" * 64,
            run_envelope_sha256="a" * 64,
            rollback_authority_sha256="d" * 64,
            process_id=71_003,
            process_alive=lambda process_id: process_id == 71_003,
            deadline=100.0,
            clock=lambda: 0.0,
            closeout=lambda _verdict, _snapshot: None,
        )

    assert "runtime-loader" not in calls
    assert "environment-loader" not in calls
    assert "lease-factory" not in calls
    assert "journal" not in calls
    assert "resource" not in calls
    assert "runner-launch-marker" not in calls


def _preflight_fixture(tmp_path: Path):
    root = tmp_path.resolve().as_posix()
    runner, manifest, payloads = _manifest(root)
    manifest_path = Path(manifest["manifest_path"])
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_bytes(runner.canonical_json_bytes(manifest))
    payload_by_path = {
        (Path(root) / manifest["artifacts"][name]["path"]).resolve().as_posix(): payloads[name]
        for name in ARTIFACT_NAMES
    }
    return runner, manifest, manifest_path, payload_by_path


def test_source_only_preflight_is_inert_and_does_not_open_source_inventory(tmp_path):
    runner, manifest, manifest_path, payload_by_path = _preflight_fixture(tmp_path)
    reads: list[str] = []

    def reader(path: Path) -> bytes:
        normalized = path.resolve().as_posix()
        reads.append(normalized)
        if normalized == manifest_path.resolve().as_posix():
            return manifest_path.read_bytes()
        if normalized == manifest["source_inventory"]["path"]:
            raise AssertionError("source-only preflight opened seed inventory")
        return payload_by_path[normalized]

    result = runner.source_only_preflight(
        manifest_path,
        repo_observer=lambda _manifest: {
            "clean": True,
            "head": "9" * 40,
            "pushed": "9" * 40,
            "runner_ancestor": True,
            "source_commit_bound": True,
            "tracked": True,
        },
        artifact_reader=reader,
        output_exists=lambda path: path.as_posix() == "never",
        interpreter_path=manifest["interpreter"],
    )

    assert result["checks"]["source_only_preflight_passed"] is True
    assert result["checks"]["seed_inventory_accessed"] is False
    assert set(result["authority"].values()) == {False}
    assert set(result["empirical_operations"].values()) == {False}
    assert manifest["source_inventory"]["path"] not in reads
    assert not any(
        name == item or name.startswith(item + ".")
        for name in sys.modules
        for item in FORBIDDEN_IMPORTS
    )


def test_existing_output_rejects_before_any_bound_artifact_or_child_access(tmp_path):
    runner, manifest, manifest_path, _payload_by_path = _preflight_fixture(tmp_path)
    reads: list[str] = []

    def reader(path: Path) -> bytes:
        reads.append(path.resolve().as_posix())
        if path.resolve() == manifest_path.resolve():
            return manifest_path.read_bytes()
        raise AssertionError("existing-output preflight opened a bound artifact")

    with pytest.raises(runner.TrainingRunnerBlocked, match="absent output"):
        runner.source_only_preflight(
            manifest_path,
            artifact_reader=reader,
            output_exists=lambda _path: True,
            interpreter_path=manifest["interpreter"],
        )

    assert reads == [manifest_path.resolve().as_posix()]


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("tracked", False),
        ("source_commit_bound", False),
        ("runner_ancestor", False),
        ("pushed", "8" * 40),
    ),
)
def test_source_only_preflight_rejects_unpushed_or_unbound_source(
    tmp_path, field, value
):
    runner, manifest, manifest_path, payload_by_path = _preflight_fixture(tmp_path)

    def reader(path: Path) -> bytes:
        normalized = path.resolve().as_posix()
        if normalized == manifest_path.resolve().as_posix():
            return manifest_path.read_bytes()
        return payload_by_path[normalized]

    observation = {
        "clean": True,
        "head": "9" * 40,
        "pushed": "9" * 40,
        "runner_ancestor": True,
        "source_commit_bound": True,
        "tracked": True,
    }
    observation[field] = value

    with pytest.raises(runner.TrainingRunnerBlocked, match="pushed source"):
        runner.source_only_preflight(
            manifest_path,
            repo_observer=lambda _manifest: observation,
            artifact_reader=reader,
            output_exists=lambda _path: False,
            interpreter_path=manifest["interpreter"],
        )
