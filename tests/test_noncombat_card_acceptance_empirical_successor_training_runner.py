from __future__ import annotations

import builtins
import copy
import hashlib
import importlib
import json
from pathlib import Path
import sys

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
    control = _control()
    request = json.loads(payloads["training_request"])
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

    result = runner.validate_authorized_command_envelope(
        envelope=envelope,
        manifest=manifest,
        request=request,
        authorization=authorization,
        approval=approval,
    )

    assert result["validated"] is True
    assert result["authority_mode"] == authority_mode
    assert result["command"] == "run-training"


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
