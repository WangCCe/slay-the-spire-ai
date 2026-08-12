from __future__ import annotations

import copy
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest


VERIFIER_MODULE = (
    "analysis_scripts."
    "verify_noncombat_card_acceptance_empirical_successor_training_runner"
)
BASE_VERIFIER_MODULE = (
    "analysis_scripts.verify_noncombat_card_acceptance_empirical_successor"
)
FORBIDDEN_IMPORTS = (
    BASE_VERIFIER_MODULE,
    "analysis_scripts.noncombat_card_acceptance_empirical_successor_experiment",
    "analysis_scripts.noncombat_card_acceptance_empirical_successor_runtime",
    "analysis_scripts.noncombat_simulator_adapter",
    "sts_lightspeed_noncombat_adapter",
    "torch",
)


def _verifier():
    return importlib.import_module(VERIFIER_MODULE)


def _canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
        + b"\n"
    )


def _self_digest(value: dict, field: str) -> dict:
    body = {key: item for key, item in value.items() if key != field}
    return {**body, field: hashlib.sha256(_canonical(body)).hexdigest()}


def _binding(path: str, payload: bytes) -> dict:
    return {
        "path": path,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _runner_test_support():
    return importlib.import_module(
        "test_noncombat_card_acceptance_empirical_successor_training_runner"
    )


def _source_observation(fixture):
    def observe(_manifest, _paths, observed_bindings):
        return {
            "clean": True,
            "head": fixture.runner_source_commit,
            "head_bindings": copy.deepcopy(observed_bindings),
            "pushed": fixture.runner_source_commit,
            "pushed_bindings": copy.deepcopy(observed_bindings),
            "runner_ancestor": True,
            "source_commit_bound": True,
            "tracked": True,
        }

    return observe


def _source_payloads(repo_root: Path) -> dict[str, tuple[str, bytes]]:
    source_root = Path(__file__).resolve().parents[1]
    source_paths = {
        "control_source": (
            "analysis_scripts/noncombat_card_acceptance_empirical_successor_experiment.py"
        ),
        "registration_producer_source": (
            "analysis_scripts/noncombat_card_acceptance_empirical_successor_seed_inventory.py"
        ),
        "registration_verifier_source": (
            "analysis_scripts/verify_noncombat_card_acceptance_empirical_successor.py"
        ),
        "runner_source": (
            "analysis_scripts/noncombat_card_acceptance_empirical_successor_training_runner.py"
        ),
        "runner_verifier_source": (
            "analysis_scripts/verify_noncombat_card_acceptance_empirical_successor_training_runner.py"
        ),
        "runtime_source": (
            "analysis_scripts/noncombat_card_acceptance_empirical_successor_runtime.py"
        ),
    }
    result = {}
    for name, relative in source_paths.items():
        payload = (source_root / relative).read_bytes()
        _write(repo_root / relative, payload)
        result[name] = (relative, payload)
    return result


def _terminalized_fixture(
    tmp_path: Path,
    *,
    partial_events: tuple[tuple[int, str], ...] = (),
    checkpoint_publication: str | None = None,
    bootstrap_publication: str | None = None,
):
    if checkpoint_publication not in {None, "resource", "runtime", "chain", "marker"}:
        raise ValueError("unknown synthetic checkpoint publication stage")
    if checkpoint_publication is not None and partial_events:
        raise ValueError("checkpoint publication fixture owns its journal events")
    if bootstrap_publication not in {None, "none", "runtime", "complete"}:
        raise ValueError("unknown synthetic bootstrap publication stage")
    resolved_bootstrap_publication = bootstrap_publication
    if resolved_bootstrap_publication is None:
        resolved_bootstrap_publication = (
            "complete"
            if checkpoint_publication is not None or partial_events
            else "none"
        )
    if checkpoint_publication is not None and resolved_bootstrap_publication != "complete":
        raise ValueError("chunk publication requires a complete bootstrap prefix")
    support = _runner_test_support()
    runner = support._runner()
    control = support._control()
    root = tmp_path.resolve()
    output = root / "output" / "training"

    checkpoint = root / "external" / "control-checkpoint.bin"
    configuration = root / "external" / "control-configuration.json"
    communication = root / "external" / "config.properties"
    production = root / "external" / "production-checkpoints"
    _write(checkpoint, b"control-checkpoint\n")
    _write(configuration, b"{}\n")
    _write(communication, b"command=production\n")
    _write(production / "production.bin", b"production\n")
    rollback = control.build_rollback_authority(
        target_relative_path="control/selected-arm.json",
        control_checkpoint=control.external_file_binding(checkpoint),
        control_configuration=control.external_file_binding(configuration),
        production_isolation={
            "communication_mod_config": control.external_file_binding(
                communication
            ),
            "production_checkpoints": control.snapshot_directory_tree(production),
        },
    )

    registered_commit = "2" * 40
    source_inventory_sha256 = "3" * 64
    training_cohort = list(range(512))
    cohorts = {
        "training": training_cohort,
        "canary": list(range(1_000, 1_128)),
        "holdout": list(range(2_000, 2_512)),
    }
    registration_body = {
        "approval_sha256": "a" * 64,
        "authority": {name: False for name in control._AUTHORITY_NAMES},
        "authorization_sha256": "b" * 64,
        "cohorts": cohorts,
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
        "inventory_sha256": "c" * 64,
        "launch_observation_sha256": "d" * 64,
        "output_root": (root / "inventory-registration").as_posix(),
        "receipt_sha256": "e" * 64,
        "registration_id": (
            "noncombat-card-acceptance-empirical-successor-"
            "20260811-r6-registration-v1"
        ),
        "request_sha256": "f" * 64,
        "role_sha256": {
            role: hashlib.sha256(_canonical(seeds)).hexdigest()
            for role, seeds in cohorts.items()
        },
        "schema_version": (
            "noncombat-card-acceptance-empirical-successor-registration-v1"
        ),
        "source_commit": registered_commit,
        "source_inventory_sha256": source_inventory_sha256,
    }
    registration = {
        **registration_body,
        "registration_sha256": control.canonical_json_sha256(registration_body),
    }
    request = control.build_stage_request(
        stage="training",
        request_id="synthetic-runner-verifier-training-request-v1",
        source_commit=registered_commit,
        source_inventory_sha256=source_inventory_sha256,
        configuration_identity=control.experiment_configuration_identity(),
        prerequisite_bindings={
            "registration_sha256": registration["registration_sha256"]
        },
        output_root=output.as_posix(),
    )
    source_inventory = {
        "path": (root / "inventory" / "never-open-seed_inventory-r4.json").as_posix(),
        "sha256": "5" * 64,
        "size_bytes": 255_499,
    }
    registration_request = {
        "input_bindings": {
            "inventory": {"content_kind": "canonical_json", **source_inventory}
        },
        "request_id": "synthetic-runner-verifier-registration-request-v1",
    }
    payloads = {
        "registration": control.canonical_json_bytes(registration),
        "registration_request": control.canonical_json_bytes(registration_request),
        "training_request": control.canonical_json_bytes(request),
        "training_request_review": b"reviewed: synthetic runner verifier fixture\n",
    }
    paths = {
        "registration": "authority/registration.json",
        "registration_request": "authority/registration_request.json",
        "training_request": "authority/training_request.json",
        "training_request_review": "authority/training_request_review.md",
    }
    source_payloads = _source_payloads(root)
    for name, (relative, payload) in source_payloads.items():
        paths[name] = relative
        payloads[name] = payload
    for name in (
        "registration",
        "registration_request",
        "training_request",
        "training_request_review",
    ):
        _write(root / paths[name], payloads[name])

    runner_source_commit = "1" * 40
    manifest_path = root / "authority" / "launch_manifest.json"
    interpreter = (root / "python" / "python.exe").as_posix()
    _write(Path(interpreter), b"synthetic interpreter\n")
    runner_path = (root / paths["runner_source"]).as_posix()
    run_inputs = [
        "--manifest",
        manifest_path.as_posix(),
        "--envelope",
        (root / "authority" / "run_envelope.json").as_posix(),
        "--authorization",
        (root / "authority" / "run_authorization.json").as_posix(),
        "--approval",
        (root / "authority" / "run_approval.json").as_posix(),
        "--launch-observation",
        (root / "authority" / "run_launch_observation.json").as_posix(),
    ]
    terminal_inputs = [
        "--manifest",
        manifest_path.as_posix(),
        "--envelope",
        (root / "authority" / "terminalization_envelope.json").as_posix(),
        "--authorization",
        (root / "authority" / "terminalization_authorization.json").as_posix(),
        "--approval",
        (root / "authority" / "terminalization_approval.json").as_posix(),
        "--launch-observation",
        (root / "authority" / "terminalization_launch_observation.json").as_posix(),
    ]

    native_root = root.parent / f"{root.name}-external-native"
    native_module = native_root / "sts_lightspeed_noncombat_adapter.pyd"
    native_dependency = native_root / "bin" / "synthetic-runtime.dll"
    _write(native_module, b"M")
    _write(native_dependency, b"D")
    module_binding = _binding(native_module.as_posix(), b"M")
    dependency_binding = _binding(native_dependency.as_posix(), b"D")
    provenance = {
        "build": {
            "adapter_api_version": "sts-lightspeed-noncombat-adapter-v3",
            "python": "3.synthetic",
        },
        "module_sha256": module_binding["sha256"],
        "module_size_bytes": module_binding["size_bytes"],
    }
    artifacts = {
        name: _binding(paths[name], payloads[name]) for name in support.ARTIFACT_NAMES
    }
    definition = {
        "artifacts": artifacts,
        "commands": {
            "preflight": [
                interpreter,
                "-I",
                runner_path,
                "preflight",
                "--manifest",
                manifest_path.as_posix(),
            ],
            "run_training": [
                interpreter,
                "-I",
                runner_path,
                "run-training",
                *run_inputs,
            ],
            "terminalize_dead_owner": [
                interpreter,
                "-I",
                runner_path,
                "terminalize-dead-owner",
                *terminal_inputs,
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
        "launch_id": "synthetic-runner-verifier-launch-v1",
        "manifest_path": manifest_path.as_posix(),
        "native_identity": {
            "adapter_api_version": "sts-lightspeed-noncombat-adapter-v3",
            "dependency_closure": {
                "dependencies": [dependency_binding],
                "imports": [
                    {"imports": [], "path": native_dependency.as_posix()},
                    {
                        "imports": [native_dependency.name.casefold()],
                        "path": native_module.as_posix(),
                    },
                ],
                "trusted_host_imports": [],
            },
            "dll_directories": [native_dependency.parent.as_posix()],
            "module": module_binding,
            "provenance": provenance,
            "provenance_sha256": control.canonical_json_sha256(provenance),
        },
        "output_root": output.as_posix(),
        "pushed_ref": "origin/master",
        "repository_root": root.as_posix(),
        "request_contract": {
            "downstream_authority": copy.deepcopy(request["downstream_authority"]),
            "execution_authority": copy.deepcopy(request["execution_authority"]),
            "output_root": output.as_posix(),
            "registration_sha256": registration["registration_sha256"],
            "request_sha256": request["request_sha256"],
            "resources": copy.deepcopy(request["resources"]),
            "source_commit": registered_commit,
            "source_inventory_sha256": source_inventory_sha256,
        },
        "resources": copy.deepcopy(request["resources"]),
        "rollback_authority": rollback,
        "runner_source_commit": runner_source_commit,
        "source_inventory": source_inventory,
        "terminalization_guard": (
            root / "output" / ".training.terminalization.guard"
        ).as_posix(),
        "registered_source": {
            "source_commit": registered_commit,
            "source_inventory_sha256": source_inventory_sha256,
        },
    }
    manifest = runner.build_launch_manifest(definition)
    _write(manifest_path, runner.canonical_json_bytes(manifest))

    run_documents = support._authorized_runner_documents(
        runner,
        manifest,
        request,
        "standing-delegation",
        command="run-training",
    )
    execution_registration = {
        **copy.deepcopy(registration),
        "rollback_authority_sha256": rollback["rollback_authority_sha256"],
    }
    context = runner._build_authorized_training_context(
        control_api=control,
        launch_manifest=manifest,
        command_envelope=run_documents["envelope"],
        authority=run_documents["authority"],
        original_registration=registration,
        execution_registration=execution_registration,
        request=request,
        authorization=run_documents["authorization"],
        approval=run_documents["approval"],
    )
    runner._ensure_terminalization_guard(manifest)
    old_process_id = 74_001
    runner_authority = {
        "composite_sha256": run_documents["envelope"]["composite"][
            "composite_sha256"
        ],
        "launch_manifest_sha256": manifest["manifest_sha256"],
        "rollback_authority_sha256": rollback["rollback_authority_sha256"],
        "run_envelope_sha256": run_documents["envelope"]["envelope_sha256"],
    }
    fresh = runner._observe_training_reopen_read_only(
        control_api=control,
        context=context,
        output_root=output,
        runner_authority_identity=runner_authority,
        process_alive=lambda _process_id: False,
    )
    with runner._AtomicObservedExecutionLease(
        control_api=control,
        context=context,
        output_root=output,
        observation=fresh,
        child_process_id=old_process_id,
        process_alive=lambda process_id: process_id == old_process_id,
        clock=lambda: 1.0,
    ) as lease:
        control.initialize_access_journal(context, lease)
        control.initialize_resource_ledger(context, lease)
        control.publish_managed_artifact(
            context,
            lease,
            relative_path="runner_launch.json",
            payload=runner._runner_launch_payload(
                manifest_sha256=manifest["manifest_sha256"],
                process_id=old_process_id,
                rollback_authority_sha256=rollback["rollback_authority_sha256"],
                run_envelope_sha256=run_documents["envelope"]["envelope_sha256"],
            ),
        )
        checkpoint_chain = None
        initial_checkpoint = None
        if resolved_bootstrap_publication in {"runtime", "complete"}:
            initial_checkpoint = support._fake_runtime_checkpoint(runner, 0)
            control.publish_managed_artifact(
                context,
                lease,
                relative_path="runtime_checkpoints/chunk_0000.json",
                payload=initial_checkpoint,
            )
        if resolved_bootstrap_publication == "complete":
            control.publish_managed_artifact(
                context,
                lease,
                relative_path="checkpoint_chains/initial.json",
                payload=runner.canonical_json_bytes(
                    runner._initial_checkpoint_record(initial_checkpoint)
                ),
            )
        if checkpoint_publication is not None:
            final_checkpoint = support._fake_runtime_checkpoint(runner, 1)
            checkpoint_chain = runner._checkpoint_chain_record(
                initial_payload=initial_checkpoint,
                final_payload=final_checkpoint,
                chunk_index=0,
                seeds=tuple(range(64)),
            )
            journal_events = tuple(
                (seed, arm)
                for seed in range(64)
                for arm in ("candidate", "control")
            )
        else:
            journal_events = partial_events
        for seed, arm in journal_events:
            control.perform_journaled_environment_access(
                context,
                lease,
                seed=seed,
                arm=arm,
                purpose="training",
                access=lambda: None,
            )
        if journal_events:
            control.advance_resource_ledger(
                context,
                lease,
                charged_seconds=0.0,
                environment_accesses=len(journal_events),
                optimizer_steps=2 if checkpoint_publication is not None else 0,
                shadow_optimizer_steps=0,
                reason=(
                    "synthetic-first-durable-chunk"
                    if checkpoint_publication is not None
                    else "synthetic-first-partial-chunk"
                ),
            )
        if checkpoint_publication in {"runtime", "chain", "marker"}:
            control.publish_managed_artifact(
                context,
                lease,
                relative_path="runtime_checkpoints/chunk_0001.json",
                payload=final_checkpoint,
            )
        if checkpoint_publication in {"chain", "marker"}:
            control.publish_managed_artifact(
                context,
                lease,
                relative_path="checkpoint_chains/chunk_0001.json",
                payload=runner.canonical_json_bytes(checkpoint_chain),
            )
        if checkpoint_publication == "marker":
            control.publish_complete_training_checkpoint(
                context,
                lease,
                binding=runner._checkpoint_control_binding(
                    checkpoint_chain["final"]
                ),
            )
    prefix = runner._terminalization_failure_prefix(
        control_api=control,
        context=context,
        output_root=output,
        runner_authority_identity=runner_authority,
        process_alive=lambda _process_id: False,
    )
    terminal_documents = support._authorized_runner_documents(
        runner,
        manifest,
        request,
        "standing-delegation",
        command="terminalize-dead-owner",
        terminalization_binding={
            "closure_guard": manifest["terminalization_guard"],
            "failure_paths": ["process_identity_failure"],
            "lease_sha256": prefix["lease_sha256"],
            "owner": prefix["owner"],
            "prefix_sha256": prefix["prefix_sha256"],
            "run_envelope_sha256": run_documents["envelope"]["envelope_sha256"],
        },
    )
    assert (
        terminal_documents["envelope"]["runner_launch_observation"][
            "control_observation"
        ]
        == run_documents["envelope"]["runner_launch_observation"][
            "control_observation"
        ]
    )
    runner._execute_dead_owner_terminalization(
        control_api=control,
        context=context,
        launch_manifest=manifest,
        command_envelope=terminal_documents["envelope"],
        authority=terminal_documents["authority"],
        rollback_authority=rollback,
        process_id=74_002,
        process_alive=lambda process_id: process_id == 74_002,
        clock=lambda: 2.0,
    )

    terminal_paths = dict(
        zip(
            manifest["commands"]["terminalize_dead_owner"][4::2],
            manifest["commands"]["terminalize_dead_owner"][5::2],
        )
    )
    terminal_payloads = {
        "--envelope": runner.canonical_json_bytes(terminal_documents["envelope"]),
        "--authorization": runner.canonical_json_bytes(
            terminal_documents["authorization"]
        ),
        "--approval": runner.canonical_json_bytes(terminal_documents["approval"]),
        "--launch-observation": runner.canonical_json_bytes(
            terminal_documents["envelope"]["runner_launch_observation"]
        ),
    }
    for flag, payload in terminal_payloads.items():
        _write(Path(terminal_paths[flag]), payload)
    run_paths = dict(
        zip(
            manifest["commands"]["run_training"][4::2],
            manifest["commands"]["run_training"][5::2],
        )
    )
    run_payloads = {
        "--envelope": runner.canonical_json_bytes(run_documents["envelope"]),
        "--authorization": runner.canonical_json_bytes(run_documents["authorization"]),
        "--approval": runner.canonical_json_bytes(run_documents["approval"]),
        "--launch-observation": runner.canonical_json_bytes(
            run_documents["envelope"]["runner_launch_observation"]
        ),
    }
    for flag, payload in run_payloads.items():
        _write(Path(run_paths[flag]), payload)

    return SimpleNamespace(
        approval_path=Path(terminal_paths["--approval"]),
        authorization_path=Path(terminal_paths["--authorization"]),
        control=control,
        envelope_path=Path(terminal_paths["--envelope"]),
        launch_observation_path=Path(terminal_paths["--launch-observation"]),
        manifest=manifest,
        manifest_path=manifest_path,
        native_dependency_path=native_dependency,
        native_module_path=native_module,
        output=output,
        registration=registration,
        registration_request=registration_request,
        request=request,
        runner=runner,
        runner_source_commit=runner_source_commit,
        source_inventory_path=Path(source_inventory["path"]),
        terminal_documents=terminal_documents,
        training_cohort=training_cohort,
    )


def _verify(fixture, **overrides):
    arguments = {
        "manifest_path": fixture.manifest_path,
        "envelope_path": fixture.envelope_path,
        "authorization_path": fixture.authorization_path,
        "approval_path": fixture.approval_path,
        "launch_observation_path": fixture.launch_observation_path,
        "source_observer": _source_observation(fixture),
        "owner_alive": lambda _process_id: False,
    }
    return _verifier().verify_terminalized_runner_bundle(
        **{**arguments, **overrides}
    )


def _recovery_review(
    fixture, runner_payload: bytes, verifier_payload: bytes
) -> dict:
    verifier = _verifier()
    envelope_payload = fixture.envelope_path.read_bytes()
    launch_payload = fixture.launch_observation_path.read_bytes()
    envelope = json.loads(envelope_payload)
    binding = envelope["terminalization_binding"]
    body = {
        "failed_v1_attempt": {
            "closure_artifacts_written": False,
            "envelope_sha256": "9" * 64,
            "environment_accesses": 0,
            "error": "terminalization lease identity differs",
            "failure_phase": "pre-start-validation",
            "invoked_once": True,
            "retry_same_envelope": False,
        },
        "failure_prefix": {
            "failure_paths": binding["failure_paths"],
            "lease_sha256": binding["lease_sha256"],
            "owner_child_process_id": binding["owner"]["child_process_id"],
            "prefix_sha256": binding["prefix_sha256"],
            "run_envelope_sha256": binding["run_envelope_sha256"],
        },
        "recovery_source": {
            "runner_path": fixture.manifest["artifacts"]["runner_source"][
                "path"
            ],
            "runner_sha256": hashlib.sha256(runner_payload).hexdigest(),
            "runner_size_bytes": len(runner_payload),
        },
        "recovery_verifier": {
            "verifier_path": fixture.manifest["artifacts"][
                "runner_verifier_source"
            ]["path"],
            "verifier_sha256": hashlib.sha256(verifier_payload).hexdigest(),
            "verifier_size_bytes": len(verifier_payload),
        },
        "recovery_v2": {
            "command_execution_operations": ["evidence_publication"],
            "downstream_authority_all_false": True,
            "envelope_file_sha256": hashlib.sha256(envelope_payload).hexdigest(),
            "envelope_id": envelope["envelope_id"],
            "envelope_sha256": envelope["envelope_sha256"],
            "launch_file_sha256": hashlib.sha256(launch_payload).hexdigest(),
            "launch_observation_sha256": envelope[
                "runner_launch_observation"
            ]["observation_sha256"],
            "pushed_source_validation_pending": True,
            "terminalization_invoked": False,
        },
        "reviewed_at": "2026-08-11T22:55:36+00:00",
        "schema_version": verifier.RECOVERY_REVIEW_SCHEMA_VERSION,
    }
    return _self_digest(body, "review_sha256")


def _allow_synthetic_checkpoint_semantics(monkeypatch):
    verifier = _verifier()
    original_loader = verifier._load_bound_base_verifier

    def load(manifest, payload):
        base = original_loader(manifest, payload)
        base.verify_paired_training_checkpoint_bytes = (
            lambda *_args, **_kwargs: {"verified": True}
        )
        return base

    monkeypatch.setattr(verifier, "_load_bound_base_verifier", load)


def test_runner_verifier_import_is_standard_library_only():
    repo_root = Path(__file__).resolve().parents[1]
    probe = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            "\n".join(
                (
                    "import importlib, json, pathlib, sys",
                    "root = pathlib.Path(sys.argv[1]).resolve()",
                    "sys.path.append(str(root))",
                    "module = importlib.import_module(sys.argv[2])",
                    "prefixes = json.loads(sys.argv[3])",
                    "loaded = sorted(name for name in sys.modules if any(",
                    "    name == prefix or name.startswith(prefix + '.')",
                    "    for prefix in prefixes",
                    "))",
                    "print(json.dumps({'module': module.__name__, 'loaded': loaded}))",
                )
            ),
            str(repo_root),
            VERIFIER_MODULE,
            json.dumps(FORBIDDEN_IMPORTS),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert probe.returncode == 0, probe.stderr
    assert json.loads(probe.stdout) == {
        "loaded": [],
        "module": VERIFIER_MODULE,
    }


def test_runner_verifier_rejects_runtime_checkpoint_trailing_newline():
    verifier = _verifier()
    support = _runner_test_support()
    checkpoint = support._fake_runtime_checkpoint(support._runner(), 0)

    snapshot = verifier._checkpoint_snapshot(checkpoint)

    assert snapshot["coordinates"]["next_chunk_index"] == 0
    with pytest.raises(verifier.VerificationError, match="not canonical"):
        verifier._checkpoint_snapshot(checkpoint + b"\n")


def test_standalone_verifier_reconstructs_terminalized_runner_without_seed_inventory(
    tmp_path,
    monkeypatch,
):
    fixture = _terminalized_fixture(tmp_path)
    original_read_bytes = Path.read_bytes

    def guarded_read(path):
        if path.resolve() == fixture.source_inventory_path.resolve():
            raise AssertionError("source inventory must not be opened")
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", guarded_read)

    result = _verify(fixture)

    assert result["verified"] is True
    assert result["command"] == "terminalize-dead-owner"
    assert result["verdict"] == "training_process_failure_terminalized"
    assert result["authority"] and not any(result["authority"].values())
    assert result["checkpoint_count"] == 0


def test_verifier_accepts_pushed_descendant_of_bound_runner_commit(tmp_path):
    fixture = _terminalized_fixture(tmp_path)
    descendant = "2" * 40

    def observe(_manifest, _paths, observed_bindings):
        return {
            "clean": True,
            "head": descendant,
            "head_bindings": copy.deepcopy(observed_bindings),
            "pushed": descendant,
            "pushed_bindings": copy.deepcopy(observed_bindings),
            "runner_ancestor": True,
            "source_commit_bound": True,
            "tracked": True,
        }

    result = _verify(fixture, source_observer=observe)

    assert result["verified"] is True


def test_verifier_accepts_exact_reviewed_recovery_runner_source(tmp_path):
    fixture = _terminalized_fixture(tmp_path)
    runner_path = (
        Path(fixture.manifest["repository_root"])
        / fixture.manifest["artifacts"]["runner_source"]["path"]
    )
    runner_payload = runner_path.read_bytes() + b"# reviewed recovery fix\n"
    runner_path.write_bytes(runner_payload)
    verifier_path = (
        Path(fixture.manifest["repository_root"])
        / fixture.manifest["artifacts"]["runner_verifier_source"]["path"]
    )
    verifier_payload = verifier_path.read_bytes() + b"# recovery verifier fix\n"
    verifier_path.write_bytes(verifier_payload)
    review = _recovery_review(fixture, runner_payload, verifier_payload)
    review_path = (
        Path(fixture.manifest["repository_root"])
        / _verifier().RECOVERY_REVIEW_RELATIVE_PATH
    )
    _write(review_path, _canonical(review))

    result = _verify(fixture, recovery_review_path=review_path)

    assert result["verified"] is True
    assert result["recovery_review_sha256"] == review["review_sha256"]


@pytest.mark.parametrize(
    "drift", ("runner", "verifier", "envelope", "review-digest")
)
def test_verifier_rejects_recovery_attestation_drift(tmp_path, drift):
    fixture = _terminalized_fixture(tmp_path)
    runner_path = (
        Path(fixture.manifest["repository_root"])
        / fixture.manifest["artifacts"]["runner_source"]["path"]
    )
    runner_payload = runner_path.read_bytes() + b"# reviewed recovery fix\n"
    runner_path.write_bytes(runner_payload)
    verifier_path = (
        Path(fixture.manifest["repository_root"])
        / fixture.manifest["artifacts"]["runner_verifier_source"]["path"]
    )
    verifier_payload = verifier_path.read_bytes() + b"# recovery verifier fix\n"
    verifier_path.write_bytes(verifier_payload)
    review = _recovery_review(fixture, runner_payload, verifier_payload)
    if drift == "runner":
        review["recovery_source"]["runner_sha256"] = "0" * 64
        review = _self_digest(review, "review_sha256")
    elif drift == "verifier":
        review["recovery_verifier"]["verifier_sha256"] = "0" * 64
        review = _self_digest(review, "review_sha256")
    elif drift == "envelope":
        review["recovery_v2"]["envelope_sha256"] = "0" * 64
        review = _self_digest(review, "review_sha256")
    else:
        review["review_sha256"] = "0" * 64
    review_path = (
        Path(fixture.manifest["repository_root"])
        / _verifier().RECOVERY_REVIEW_RELATIVE_PATH
    )
    _write(review_path, _canonical(review))

    with pytest.raises(
        _verifier().VerificationError,
        match="recovery|identity|bound source",
    ):
        _verify(fixture, recovery_review_path=review_path)


@pytest.mark.parametrize("source_name", ("runner", "verifier"))
def test_verifier_requires_recovery_binding_when_manifest_source_is_unchanged(
    tmp_path, source_name
):
    fixture = _terminalized_fixture(tmp_path)
    runner_path = (
        Path(fixture.manifest["repository_root"])
        / fixture.manifest["artifacts"]["runner_source"]["path"]
    )
    verifier_path = (
        Path(fixture.manifest["repository_root"])
        / fixture.manifest["artifacts"]["runner_verifier_source"]["path"]
    )
    review = _recovery_review(
        fixture, runner_path.read_bytes(), verifier_path.read_bytes()
    )
    if source_name == "runner":
        review["recovery_source"]["runner_sha256"] = "0" * 64
    else:
        review["recovery_verifier"]["verifier_sha256"] = "0" * 64
    review = _self_digest(review, "review_sha256")
    review_path = (
        Path(fixture.manifest["repository_root"])
        / _verifier().RECOVERY_REVIEW_RELATIVE_PATH
    )
    _write(review_path, _canonical(review))

    with pytest.raises(
        _verifier().VerificationError,
        match="recovery source artifact differs",
    ):
        _verify(fixture, recovery_review_path=review_path)


def test_bound_base_verifier_executes_observed_bytes_without_path_reopen(tmp_path):
    fixture = _terminalized_fixture(tmp_path)
    bound_source = (
        Path(fixture.manifest["repository_root"])
        / fixture.manifest["artifacts"]["registration_verifier_source"]["path"]
    )
    observed = _source_observation(fixture)

    def swap_after_observation(manifest, paths, observed_bindings):
        result = observed(manifest, paths, observed_bindings)
        bound_source.write_bytes(b"raise AssertionError('reopened verifier path')\n")
        return result

    result = _verify(fixture, source_observer=swap_after_observation)

    assert result["verified"] is True
    assert bound_source.read_bytes().startswith(b"raise AssertionError")


def test_repository_source_observation_excludes_external_native_bindings(
    tmp_path,
    monkeypatch,
):
    fixture = _terminalized_fixture(tmp_path)
    observed_paths = []
    observed = _source_observation(fixture)

    def capture_repository_paths(manifest, paths, observed_bindings):
        observed_paths.extend(paths)
        return observed(manifest, paths, observed_bindings)

    result = _verify(fixture, source_observer=capture_repository_paths)

    repository_root = Path(fixture.manifest["repository_root"])
    assert result["verified"] is True
    assert observed_paths
    assert all(
        Path(path).resolve().is_relative_to(repository_root)
        for path in observed_paths
    )
    assert fixture.native_module_path.as_posix() not in observed_paths
    assert fixture.native_dependency_path.as_posix() not in observed_paths

    git_calls = []
    monkeypatch.setattr(
        _verifier().subprocess,
        "run",
        lambda *args, **kwargs: git_calls.append((args, kwargs)),
    )
    with pytest.raises(
        _verifier().VerificationError,
        match="external path",
    ):
        _verifier()._default_source_observer(
            fixture.manifest,
            (fixture.native_module_path.as_posix(),),
            {},
        )
    assert git_calls == []


@pytest.mark.parametrize("drift", ("manifest", "command", "source"))
def test_runner_verifier_rejects_manifest_command_or_source_drift(tmp_path, drift):
    fixture = _terminalized_fixture(tmp_path)
    if drift == "source":
        source = (
            Path(fixture.manifest["repository_root"])
            / fixture.manifest["artifacts"]["runner_source"]["path"]
        )
        source.write_bytes(source.read_bytes() + b"# drift\n")
    else:
        manifest = copy.deepcopy(fixture.manifest)
        if drift == "manifest":
            manifest["runner_source_commit"] = "9" * 40
        else:
            manifest["commands"]["terminalize_dead_owner"].append("--unknown")
        fixture.manifest_path.write_bytes(
            _canonical(_self_digest(manifest, "manifest_sha256"))
        )

    with pytest.raises(_verifier().VerificationError, match="manifest|command|source"):
        _verify(fixture)


@pytest.mark.parametrize("drift", ("authorization", "approval", "launch"))
def test_runner_verifier_rejects_authorization_approval_or_launch_drift(
    tmp_path,
    drift,
):
    fixture = _terminalized_fixture(tmp_path)
    path = {
        "authorization": fixture.authorization_path,
        "approval": fixture.approval_path,
        "launch": fixture.launch_observation_path,
    }[drift]
    document = json.loads(path.read_bytes())
    if drift == "authorization":
        document["request_id"] += "-drift"
        document = _self_digest(document, "authorization_sha256")
    elif drift == "approval":
        document["approved_request_sha256"] = "0" * 64
        document = _self_digest(document, "approval_sha256")
    else:
        document["composite_binding_text"] += " drift"
        document = _self_digest(document, "observation_sha256")
    path.write_bytes(_canonical(document))

    with pytest.raises(
        _verifier().VerificationError,
        match="authorization|approval|launch|observation|authority",
    ):
        _verify(fixture)


@pytest.mark.parametrize("drift", ("checkpoint", "journal", "resource"))
def test_runner_verifier_rejects_checkpoint_journal_or_resource_mismatch(
    tmp_path,
    drift,
):
    fixture = _terminalized_fixture(tmp_path)
    if drift == "checkpoint":
        _write(
            fixture.output / "checkpoint_chains" / "chunk_0001.json",
            _canonical({"schema_version": "forged-checkpoint-chain-v1"}),
        )
    elif drift == "journal":
        journal = fixture.output / "access_journal.jsonl"
        journal.write_bytes(journal.read_bytes().replace(b"journal_opened", b"journal_drifted"))
    else:
        ledger = fixture.output / "resource_ledger.jsonl"
        ledger.write_bytes(ledger.read_bytes().replace(b"resource_ledger_opened", b"resource_ledger_drifted"))

    with pytest.raises(
        _verifier().VerificationError,
        match="checkpoint|journal|resource|prefix|inventory",
    ):
        _verify(fixture)


def test_runner_verifier_rejects_incomplete_terminal_publication_order(tmp_path):
    fixture = _terminalized_fixture(tmp_path)
    (fixture.output / "terminal.json").unlink()

    with pytest.raises(_verifier().VerificationError, match="terminal|order|read"):
        _verify(fixture)


@pytest.mark.parametrize(
    "relative_path",
    (
        "evidence/unknown.json",
        "stages/canary.json",
        "holdout/evidence.json",
        "checkpoint_chains/chunk_0001.json.staging",
    ),
)
def test_runner_verifier_rejects_unknown_or_prohibited_output_artifacts(
    tmp_path,
    relative_path,
):
    fixture = _terminalized_fixture(tmp_path)
    _write(fixture.output / relative_path, _canonical({"forbidden": True}))

    with pytest.raises(
        _verifier().VerificationError,
        match="unknown|canary|holdout|staging|artifact|path",
    ):
        _verify(fixture)


def test_runner_verifier_rejects_true_downstream_authority(tmp_path):
    fixture = _terminalized_fixture(tmp_path)
    intent_path = fixture.output / "terminal_intent.json"
    intent = json.loads(intent_path.read_bytes())
    intent["downstream_authority"]["qualification"] = True
    intent_path.write_bytes(_canonical(intent))

    with pytest.raises(_verifier().VerificationError, match="authority|terminal"):
        _verify(fixture)


def test_default_source_observer_binds_pre_read_bytes_to_head_and_pushed_blobs(
    tmp_path,
    monkeypatch,
):
    fixture = _terminalized_fixture(tmp_path)
    path = fixture.manifest_path.resolve().as_posix()
    payload = fixture.manifest_path.read_bytes()
    observed_bindings = {path: _binding(path, payload)}
    calls = []
    blob_payload = {"value": payload + b"assume-unchanged drift"}

    def fake_run(command, **_kwargs):
        arguments = tuple(command[3:])
        calls.append(arguments)
        if arguments[:1] == ("rev-parse",):
            return SimpleNamespace(
                returncode=0,
                stdout=(fixture.runner_source_commit + "\n").encode("ascii"),
                stderr=b"",
            )
        if arguments[:2] == ("merge-base", "--is-ancestor"):
            return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")
        if arguments[:1] == ("show",):
            return SimpleNamespace(
                returncode=0,
                stdout=blob_payload["value"],
                stderr=b"",
            )
        if arguments[:1] == ("ls-files",):
            relative = fixture.manifest_path.relative_to(
                Path(fixture.manifest["repository_root"])
            ).as_posix()
            return SimpleNamespace(
                returncode=0,
                stdout=(relative + "\n").encode("ascii"),
                stderr=b"",
            )
        raise AssertionError(f"unexpected git call: {arguments}")

    monkeypatch.setattr(_verifier().subprocess, "run", fake_run)

    with pytest.raises(_verifier().VerificationError, match="blob|bytes|binding|pushed"):
        _verifier()._default_source_observer(
            fixture.manifest,
            (path,),
            observed_bindings,
        )

    blob_payload["value"] = payload
    observation = _verifier()._default_source_observer(
        fixture.manifest,
        (path,),
        observed_bindings,
    )
    assert observation["clean"] is True
    assert observation["head_bindings"] == observed_bindings
    assert observation["pushed_bindings"] == observed_bindings
    assert not any(arguments[:1] in {("diff",), ("status",)} for arguments in calls)


def test_terminal_lease_bytes_and_owner_must_equal_closure_prefix(tmp_path):
    fixture = _terminalized_fixture(tmp_path)
    closure = json.loads(
        (fixture.output / "terminalization_closure.json").read_bytes()
    )
    lease_path = fixture.output / ".execution.lease"
    lease = json.loads(lease_path.read_bytes())
    lease["reclaimed_owner"] = copy.deepcopy(closure["failure_prefix"]["owner"])
    lease_path.write_bytes(_canonical(lease))

    with pytest.raises(_verifier().VerificationError, match="lease|prefix|closure"):
        _verify(fixture)


@pytest.mark.parametrize("drift", ("configuration_identity", "exclusions"))
def test_training_request_reconstructs_exact_configuration_and_exclusions(
    tmp_path,
    drift,
):
    fixture = _terminalized_fixture(tmp_path)
    request = copy.deepcopy(fixture.request)
    if drift == "configuration_identity":
        request["configuration_identity"]["canonical_size_bytes"] += 1
    else:
        request["exclusions"][0] = "forged-exclusion"
    request = _self_digest(request, "request_sha256")
    manifest = copy.deepcopy(fixture.manifest)
    manifest["request_contract"]["request_sha256"] = request["request_sha256"]

    with pytest.raises(
        _verifier().VerificationError,
        match="configuration|exclusion|request|terms",
    ):
        _verifier()._validate_request(manifest, _canonical(request))


@pytest.mark.parametrize("drift", ("scope", "grant", "exclusions", "revocation"))
def test_standing_delegation_reconstructs_immutable_grant_and_scope(tmp_path, drift):
    fixture = _terminalized_fixture(tmp_path)
    delegation = copy.deepcopy(
        fixture.terminal_documents["approval"]["delegation"]
    )
    if drift == "scope":
        delegation["scope"]["pushed_remote_ref"] = "origin/forged"
    elif drift == "grant":
        delegation["grant"]["verbatim_text"] += " drift"
    elif drift == "exclusions":
        delegation["exclusions"][0] = "forged-exclusion"
    else:
        delegation["revocation"] = "never-revocable"
    delegation = _self_digest(delegation, "delegation_sha256")

    with pytest.raises(
        _verifier().VerificationError,
        match="delegation|scope|grant|exclusion|revocation",
    ):
        _verifier()._validate_standing_delegation(delegation)


@pytest.mark.parametrize("drift", ("terms", "time", "request_digest_text"))
def test_external_approval_reconstructs_terms_time_and_digest_text(tmp_path, drift):
    fixture = _terminalized_fixture(tmp_path)
    support = _runner_test_support()
    documents = support._authorized_runner_documents(
        fixture.runner,
        fixture.manifest,
        fixture.request,
        "external-human-approval",
        command="terminalize-dead-owner",
        terminalization_binding=fixture.terminal_documents["envelope"][
            "terminalization_binding"
        ],
    )
    approval = copy.deepcopy(documents["approval"])
    if drift == "terms":
        approval["bound_request_terms"]["repository_id"] = "forged/repository"
    elif drift == "time":
        approval["request_published_at"] = approval["approval_message"][
            "approved_at"
        ]
    else:
        message = approval["approval_message"]
        message["verbatim_approval_text"] = message[
            "verbatim_approval_text"
        ].replace(fixture.request["request_sha256"], "0" * 64)
        approval["approval_message"] = _self_digest(
            message, "approval_message_sha256"
        )
    approval = _self_digest(approval, "approval_sha256")

    with pytest.raises(
        _verifier().VerificationError,
        match="approval|terms|timestamp|postdate|digest|request",
    ):
        _verifier()._validate_external_approval(approval, fixture.request)


@pytest.mark.parametrize("drift", ("self_digest", "contract", "inventory_binding"))
def test_registration_reconstructs_digest_contract_and_inventory_binding(
    tmp_path,
    drift,
):
    fixture = _terminalized_fixture(tmp_path)
    registration = copy.deepcopy(fixture.registration)
    registration_request = copy.deepcopy(fixture.registration_request)
    manifest = copy.deepcopy(fixture.manifest)
    if drift == "self_digest":
        registration["registration_id"] += "-forged"
    elif drift == "contract":
        manifest["request_contract"]["registration_sha256"] = "0" * 64
    else:
        registration_request["input_bindings"]["inventory"]["sha256"] = "0" * 64

    with pytest.raises(
        _verifier().VerificationError,
        match="registration|inventory|contract|digest|binding",
    ):
        _verifier()._validate_registration_sources(
            manifest,
            _canonical(registration),
            _canonical(registration_request),
        )


def test_checkpoint_seeds_are_exact_registered_training_prefix(tmp_path):
    fixture = _terminalized_fixture(tmp_path)

    assert _verifier()._validate_training_seed_prefix(
        fixture.training_cohort[:64],
        fixture.training_cohort,
    ) == fixture.training_cohort[:64]
    forged = [*fixture.training_cohort[:63], 99_999]
    with pytest.raises(_verifier().VerificationError, match="seed|cohort|prefix"):
        _verifier()._validate_training_seed_prefix(
            forged,
            fixture.training_cohort,
        )


@pytest.mark.parametrize(
    "drift",
    (
        "adapter_api",
        "provenance_build",
        "duplicate_basename",
        "unresolved_import",
        "host_allowlist",
        "unreachable",
        "cycle",
        "shadowed_resolution",
    ),
)
def test_native_identity_matches_runner_graph_and_resolution(tmp_path, drift):
    fixture = _terminalized_fixture(tmp_path)
    native = copy.deepcopy(fixture.manifest["native_identity"])
    closure = native["dependency_closure"]
    module_path = native["module"]["path"]
    dependency_path = native["dependency_closure"]["dependencies"][0]["path"]
    dependency_name = Path(dependency_path).name.casefold()
    if drift == "adapter_api":
        native["adapter_api_version"] = "forged-adapter-v1"
    elif drift == "provenance_build":
        native["provenance"]["build"]["adapter_api_version"] = "forged-v1"
        native["provenance_sha256"] = hashlib.sha256(
            _canonical(native["provenance"])
        ).hexdigest()
    elif drift == "duplicate_basename":
        duplicate = Path(module_path).parent / "duplicate" / Path(dependency_path).name
        _write(duplicate, b"duplicate")
        closure["dependencies"].append(
            _binding(duplicate.resolve().as_posix(), b"duplicate")
        )
        closure["dependencies"].sort(key=lambda item: item["path"])
        closure["imports"].append(
            {"imports": [], "path": duplicate.resolve().as_posix()}
        )
        closure["imports"].sort(key=lambda item: item["path"])
    elif drift == "unresolved_import":
        next(row for row in closure["imports"] if row["path"] == module_path)[
            "imports"
        ].append("unregistered.dll")
    elif drift == "host_allowlist":
        closure["trusted_host_imports"] = ["unregistered.dll"]
        next(row for row in closure["imports"] if row["path"] == module_path)[
            "imports"
        ].append("unregistered.dll")
    elif drift == "unreachable":
        next(row for row in closure["imports"] if row["path"] == module_path)[
            "imports"
        ] = []
    elif drift == "cycle":
        second = Path(module_path).parent / "cycle-runtime.dll"
        _write(second, b"cycle")
        closure["dependencies"].append(_binding(second.as_posix(), b"cycle"))
        closure["dependencies"].sort(key=lambda item: item["path"])
        next(row for row in closure["imports"] if row["path"] == dependency_path)[
            "imports"
        ] = [second.name.casefold()]
        closure["imports"].append(
            {"imports": [dependency_name], "path": second.as_posix()}
        )
        closure["imports"].sort(key=lambda item: item["path"])
    else:
        shadow = Path(module_path).parent / Path(dependency_path).name
        _write(shadow, b"shadow")

    with pytest.raises(
        _verifier().VerificationError,
        match="native|adapter|provenance|basename|import|host|reachable|cyclic|resolution|shadow",
    ):
        _verifier()._validate_native_identity(
            native,
            interpreter_path=fixture.manifest["interpreter"],
        )


def test_windows_liveness_is_typed_and_treats_ambiguous_results_as_non_dead(
    monkeypatch,
):
    verifier = _verifier()
    import ctypes

    class FakeFunction:
        def __init__(self, result):
            self.result = result
            self.argtypes = None
            self.restype = None

        def __call__(self, *_args):
            return self.result

    class Kernel32:
        def __init__(self):
            self.OpenProcess = FakeFunction(101)
            self.WaitForSingleObject = FakeFunction(0xFFFFFFFF)
            self.CloseHandle = FakeFunction(1)

    kernel32 = Kernel32()
    win_dll_calls = []
    monkeypatch.setattr(
        ctypes,
        "WinDLL",
        lambda name, **kwargs: win_dll_calls.append((name, kwargs)) or kernel32,
    )
    monkeypatch.setattr(
        ctypes,
        "windll",
        SimpleNamespace(kernel32=kernel32),
    )
    monkeypatch.setattr(ctypes, "get_last_error", lambda: 5)

    assert verifier._default_process_alive(81_001) is True
    kernel32.OpenProcess.result = 0
    assert verifier._default_process_alive(81_002) is True
    assert win_dll_calls == [
        ("kernel32", {"use_last_error": True}),
        ("kernel32", {"use_last_error": True}),
    ]
    for operation in (
        kernel32.OpenProcess,
        kernel32.WaitForSingleObject,
        kernel32.CloseHandle,
    ):
        assert operation.argtypes is not None
        assert operation.restype is not None


@pytest.mark.parametrize(
    "partial_events",
    (
        ((2_000, "candidate"), (2_000, "control")),
        ((99_999, "candidate"), (99_999, "control")),
        ((0, "control"), (0, "candidate")),
        ((0, "control"),),
        ((0, "candidate"), (1, "candidate"), (1, "control")),
        ((0, "candidate"), (0, "control"), (2, "candidate")),
    ),
    ids=(
        "holdout-seed",
        "arbitrary-seed",
        "arm-order",
        "unmatched-control",
        "middle-unpaired",
        "wrong-next-seed",
    ),
)
def test_first_partial_chunk_rejects_nontraining_or_malformed_pairs(
    tmp_path,
    monkeypatch,
    partial_events,
):
    fixture = _terminalized_fixture(tmp_path, partial_events=partial_events)
    _allow_synthetic_checkpoint_semantics(monkeypatch)

    with pytest.raises(
        _verifier().VerificationError,
        match="checkpoint|journal|pair|seed|cohort|prefix|order",
    ):
        _verify(fixture)


@pytest.mark.parametrize("bootstrap_publication", ("runtime", "complete"))
def test_bootstrap_publication_prefixes_are_terminalizable(
    tmp_path,
    monkeypatch,
    bootstrap_publication,
):
    fixture = _terminalized_fixture(
        tmp_path,
        bootstrap_publication=bootstrap_publication,
    )
    _allow_synthetic_checkpoint_semantics(monkeypatch)

    result = _verify(fixture)

    assert result["verified"] is True
    assert result["checkpoint_count"] == 0
    assert result["resources"]["environment_accesses"] == 0


def test_training_journal_before_bootstrap_checkpoint_is_rejected(tmp_path):
    fixture = _terminalized_fixture(
        tmp_path,
        partial_events=((0, "candidate"),),
        bootstrap_publication="none",
    )

    with pytest.raises(
        _verifier().VerificationError,
        match="bootstrap|checkpoint|training progress",
    ):
        _verify(fixture)


def test_first_partial_chunk_accepts_registered_training_prefix(
    tmp_path,
    monkeypatch,
):
    fixture = _terminalized_fixture(
        tmp_path,
        partial_events=(
            (0, "candidate"),
            (0, "control"),
            (1, "candidate"),
            (1, "control"),
        ),
    )
    _allow_synthetic_checkpoint_semantics(monkeypatch)

    result = _verify(fixture)

    assert result["verified"] is True
    assert result["checkpoint_count"] == 0
    assert result["resources"]["environment_accesses"] == 4


def test_first_partial_chunk_accepts_fully_debited_unpublished_chunk(
    tmp_path,
    monkeypatch,
):
    fixture = _terminalized_fixture(
        tmp_path,
        partial_events=tuple(
            (seed, arm)
            for seed in range(64)
            for arm in ("candidate", "control")
        ),
    )
    _allow_synthetic_checkpoint_semantics(monkeypatch)

    result = _verify(fixture)

    assert result["verified"] is True
    assert result["checkpoint_count"] == 0
    assert result["resources"]["environment_accesses"] == 128


@pytest.mark.parametrize(
    ("publication_stage", "expected_checkpoint_count"),
    (
        ("resource", 0),
        ("runtime", 0),
        ("chain", 0),
        ("marker", 1),
    ),
)
def test_first_durable_chunk_accepts_each_checkpoint_publication_prefix(
    tmp_path,
    monkeypatch,
    publication_stage,
    expected_checkpoint_count,
):
    fixture = _terminalized_fixture(
        tmp_path,
        checkpoint_publication=publication_stage,
    )
    _allow_synthetic_checkpoint_semantics(monkeypatch)

    result = _verify(fixture)

    assert result["verified"] is True
    assert result["checkpoint_count"] == expected_checkpoint_count
    assert result["resources"] == {
        "charged_seconds": 0.0,
        "environment_accesses": 128,
        "optimizer_steps": 2,
        "shadow_optimizer_steps": 0,
    }


def test_first_partial_chunk_accepts_trailing_write_ahead_candidate(
    tmp_path,
    monkeypatch,
):
    fixture = _terminalized_fixture(
        tmp_path,
        partial_events=(
            (0, "candidate"),
            (0, "control"),
            (1, "candidate"),
        ),
    )
    _allow_synthetic_checkpoint_semantics(monkeypatch)

    result = _verify(fixture)

    assert result["verified"] is True
    assert result["checkpoint_count"] == 0
    assert result["resources"]["environment_accesses"] == 3
