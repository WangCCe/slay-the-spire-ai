from __future__ import annotations

import ast
import copy
import gzip
import hashlib
import io
import json
import os
import platform
import subprocess
import sys
import types
from pathlib import Path

import pytest

import analysis_scripts.noncombat_cross_fitted_hierarchical_learning_experiment as experiment
from analysis_scripts import (
    noncombat_cross_fitted_hierarchical_learning_seed_inventory as seed_inventory,
)


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def source_inventory():
    return experiment.build_source_inventory(ROOT)


def _runtime_identity():
    return {
        "device": "cpu",
        "python_executable": Path(sys.executable).resolve().as_posix(),
        "python_version": "3.10.synthetic",
        "torch_version": "2.synthetic",
    }


def _native_identity():
    return {
        "adapter_api_version": "sts-lightspeed-noncombat-adapter-v3",
        "dll_directories": ["D:/synthetic-native/bin"],
        "module": {
            "path": "D:/synthetic-native/sts_lightspeed.pyd",
            "sha256": "b" * 64,
            "size_bytes": 123,
        },
    }


def _native_provenance():
    return {
        "adapter_commit": "1" * 40,
        "adapter_source_sha256": "2" * 64,
        "build": {
            "adapter_api_version": "sts-lightspeed-noncombat-adapter-v3",
            "compiler": "synthetic-compiler",
            "cpp_standard": "20",
            "python": platform.python_version(),
        },
        "module_sha256": "b" * 64,
        "simulator_commit": "3" * 40,
        "simulator_source_sha256": "4" * 64,
        "submodules": {"json": "5" * 40, "pybind11": "6" * 40},
    }


def _hardened_native_identity():
    provenance = _native_provenance()
    return {
        **_native_identity(),
        "provenance": provenance,
        "provenance_sha256": hashlib.sha256(
            experiment.canonical_json_bytes(provenance)
        ).hexdigest(),
    }


def _isolation_identity():
    return {
        "communication_mod_config": {
            "path": "D:/synthetic/CommunicationMod/config.properties",
            "sha256": "c" * 64,
            "size_bytes": 321,
        },
        "production_checkpoints": {
            "file_count": 2,
            "root": "D:/synthetic/SlayTheSpire/checkpoints",
            "sha256": "d" * 64,
            "size_bytes": 654,
        },
    }


def _seed_inventory(repository_commit="a" * 40):
    reserved = list(range(71152, 71664))
    return seed_inventory.validate_seed_inventory(
        {
            "canonical_search_start": 0,
            "excluded_seed_count": len(reserved),
            "excluded_seeds": reserved,
            "repository_commit": repository_commit,
            "reserved_seed_ranges": [
                {
                    "end_inclusive": 71663,
                    "name": "previous_untouched_holdout",
                    "start_inclusive": 71152,
                }
            ],
            "row_count": 0,
            "rows": [],
            "schema_version": seed_inventory.SEED_INVENTORY_SCHEMA_VERSION,
            "source_bindings": [],
            "source_count": 0,
        }
    )


def _readiness_authority():
    return {
        name: False
        for name in (
            "causal_claim",
            "communication_mod",
            "empirical_registration",
            "evaluation",
            "execution_authorization",
            "execution_request",
            "external_approval",
            "formal_rl",
            "gameplay",
            "model_fitting",
            "model_loading",
            "native_loading",
            "ope",
            "policy_quality",
            "promotion",
            "qualification",
            "seed_access",
            "training",
        )
    }


def _deterministic_gzip(payload):
    buffer = io.BytesIO()
    with gzip.GzipFile(
        fileobj=buffer, mode="wb", filename="", mtime=0
    ) as handle:
        handle.write(payload)
    return buffer.getvalue()


def _compact_readiness_fixture(source_inventory):
    source_commit = "a" * 40
    pushed_head = "b" * 40
    publication_commit = "c" * 40
    report_path = "reports/synthetic-readiness/readiness_report.json"
    candidate_path = "reports/synthetic-readiness/candidate_seed_inventory.json.gz"
    receipt_path = (
        "reports/noncombat_cross_fitted_empirical_successor_readiness_attempts/"
        f"{source_commit}/attempt_verified.json"
    )
    inventory = _seed_inventory(source_commit)
    schedule = seed_inventory.materialize_fresh_schedule(inventory)
    consumed_seeds = list(range(10_000, 10_512))
    consumed_path = (
        "reports/noncombat_cross_fitted_hierarchical_learning_"
        "successor_20260806_r1/registration.json"
    )
    consumed_payload = b"synthetic consumed registration\n"
    candidate = {
        "authority": _readiness_authority(),
        "candidate_schedule": schedule,
        "consumed_cohort": {
            "registration_binding": {
                "path": consumed_path,
                "sha256": hashlib.sha256(consumed_payload).hexdigest(),
                "size_bytes": len(consumed_payload),
            },
            "registration_id": "consumed-registration",
            "seed_count": 512,
            "seeds": consumed_seeds,
            "seeds_sha256": hashlib.sha256(
                experiment.canonical_json_bytes(consumed_seeds)
            ).hexdigest(),
        },
        "disjointness": {
            "collision_count": 0,
            "collisions": [],
            "status": "passed",
        },
        "historical_seed_inventory": inventory,
        "schema_version": (
            "noncombat-cross-fitted-empirical-successor-readiness-candidate-v1"
        ),
        "source_commit": source_commit,
    }
    candidate_canonical = experiment.canonical_json_bytes(candidate)
    candidate_stored = _deterministic_gzip(candidate_canonical)
    report_candidate_binding = {
        "canonical_sha256": hashlib.sha256(candidate_canonical).hexdigest(),
        "canonical_size_bytes": len(candidate_canonical),
        "encoding": "gzip-mtime-zero-v1",
        "path": "candidate_seed_inventory.json.gz",
        "sha256": hashlib.sha256(candidate_stored).hexdigest(),
        "size_bytes": len(candidate_stored),
    }

    rows = {
        row["name"]: row
        for section in ("modules", "public_dependencies")
        for row in source_inventory[section]
    }
    successor_path = (
        "openspec/specs/noncombat-cross-fitted-hierarchical-learning-successor/"
        "spec.md"
    )
    successor_payload = (ROOT / successor_path).read_bytes()
    role_rows = [
        ("seed_inventory_source", rows["seed_inventory"]),
        ("control_plane_source", rows["control_plane"]),
        ("terminal_verifier_source", rows["independent_verifier"]),
        (
            "successor_contract",
            {
                "path": successor_path,
                "sha256": hashlib.sha256(successor_payload).hexdigest(),
                "size_bytes": len(successor_payload),
            },
        ),
        (
            "consumed_registration",
            {
                "path": consumed_path,
                "sha256": hashlib.sha256(consumed_payload).hexdigest(),
                "size_bytes": len(consumed_payload),
            },
        ),
    ]
    readiness_bindings = [
        {
            "path": row["path"],
            "role": role,
            "sha256": row["sha256"],
            "size_bytes": row["size_bytes"],
        }
        for role, row in role_rows
    ]
    source_binding = {
        "bindings": readiness_bindings,
        "bindings_sha256": hashlib.sha256(
            experiment.canonical_json_bytes(readiness_bindings)
        ).hexdigest(),
        "head_commit": source_commit,
        "origin_master_commit": source_commit,
        "source_commit": source_commit,
        "status": "passed",
        "tracked_clean": True,
    }
    report_body = {
        "audit_id": "synthetic-readiness",
        "authority": _readiness_authority(),
        "budget": {},
        "candidate_artifact_binding": report_candidate_binding,
        "cohort": {
            "candidate_seed_count": 512,
            "candidate_seeds_sha256": hashlib.sha256(
                experiment.canonical_json_bytes(schedule["seeds"])
            ).hexdigest(),
            "collision_count": 0,
            "collisions": [],
            "consumed_seed_count": 512,
            "consumed_seeds_sha256": hashlib.sha256(
                experiment.canonical_json_bytes(consumed_seeds)
            ).hexdigest(),
            "status": "passed",
        },
        "decision": {"failed_gates": [], "reason": "go", "status": "go"},
        "eligibility": {"empirical_successor_registration_proposal_eligible": True},
        "gates": {
            name: "passed"
            for name in (
                "artifact_binding",
                "budget_binding",
                "cohort_not_fresh",
                "control_plane_scaling",
                "rehearsal_boundary",
                "source_binding",
            )
        },
        "limitations": [],
        "rehearsal": {},
        "schema_version": (
            "noncombat-cross-fitted-empirical-successor-readiness-report-v1"
        ),
        "source_binding": source_binding,
        "source_commit": source_commit,
    }
    report = {
        **report_body,
        "readiness_identity_sha256": hashlib.sha256(
            experiment.canonical_json_bytes(report_body)
        ).hexdigest(),
    }
    report_payload = experiment.canonical_json_bytes(report)
    receipt_body = {
        "attempt_sha256": "2" * 64,
        "intended_output_dir": "D:\\synthetic-readiness",
        "publication_bindings": {
            "candidate_seed_inventory.json.gz": {
                "sha256": hashlib.sha256(candidate_stored).hexdigest(),
                "size_bytes": len(candidate_stored),
            },
            "readiness_report.json": {
                "sha256": hashlib.sha256(report_payload).hexdigest(),
                "size_bytes": len(report_payload),
            },
            "readiness_report.md": {"sha256": "3" * 64, "size_bytes": 1},
        },
        "schema_version": (
            "noncombat-cross-fitted-empirical-successor-readiness-attempt-"
            "verified-v1"
        ),
        "source_commit": source_commit,
        "staging_dir": "D:\\synthetic-readiness.staging",
        "status": "staging_independently_verified",
        "verification": {
            "candidate_inventory_sha256": hashlib.sha256(
                candidate_stored
            ).hexdigest(),
            "decision": "go",
            "independent_inventory_sha256": schedule["inventory_sha256"],
            "proposal_eligible": True,
            "readiness_identity_sha256": report["readiness_identity_sha256"],
            "source_commit": source_commit,
            "status": "verified",
        },
    }
    receipt = {
        **receipt_body,
        "verification_receipt_sha256": hashlib.sha256(
            experiment.canonical_json_bytes(receipt_body)
        ).hexdigest(),
    }
    receipt_payload = experiment.canonical_json_bytes(receipt)
    path_payloads = {
        (publication_commit, candidate_path): candidate_stored,
        (publication_commit, report_path): report_payload,
        (publication_commit, receipt_path): receipt_payload,
        (source_commit, consumed_path): consumed_payload,
        (source_commit, successor_path): successor_payload,
    }
    for row in rows.values():
        path_payloads[(source_commit, row["path"])] = (ROOT / row["path"]).read_bytes()

    def git_text(_root, *args):
        if args == ("rev-parse", "HEAD"):
            return pushed_head
        if args == ("rev-parse", "origin/master"):
            return pushed_head
        if args == ("status", "--porcelain", "--untracked-files=no"):
            return ""
        if args in {
            ("merge-base", "--is-ancestor", source_commit, pushed_head),
            ("merge-base", "--is-ancestor", source_commit, publication_commit),
            ("merge-base", "--is-ancestor", publication_commit, pushed_head),
        }:
            return ""
        raise AssertionError(f"unexpected Git query: {args!r}")

    def git_path_observer(_root, ref, path):
        try:
            return path_payloads[(ref, path)]
        except KeyError as exc:
            raise AssertionError(f"unexpected Git blob: {ref}:{path}") from exc

    return {
        "candidate": candidate,
        "candidate_path": candidate_path,
        "git_path_observer": git_path_observer,
        "git_text": git_text,
        "publication_commit": publication_commit,
        "pushed_head": pushed_head,
        "receipt": receipt,
        "receipt_path": receipt_path,
        "report": report,
        "report_path": report_path,
        "source_commit": source_commit,
    }


def _hardened_registration(
    source_inventory, *, output_root="D:/synthetic/cross-fitted-output"
):
    historical_source = copy.deepcopy(source_inventory)
    declared = experiment.module_dependency_inventory(
        experiment.REGISTRATION_SCHEMA_VERSION
    )
    for row, expected in zip(
        historical_source["public_dependencies"],
        declared["public_dependencies"],
        strict=True,
    ):
        row["public_symbols"] = expected["public_symbols"]
    source_body = {
        key: historical_source[key]
        for key in ("modules", "public_dependencies", "schema_version")
    }
    historical_source["inventory_sha256"] = hashlib.sha256(
        experiment.canonical_json_bytes(source_body)
    ).hexdigest()
    inventory = _seed_inventory()
    fresh = seed_inventory.materialize_fresh_schedule(inventory)
    seeds = list(fresh["seeds"])
    registration = {
        "authority": experiment.registration_authority(),
        "contract": experiment.experiment_contract(),
        "isolation_identity": _isolation_identity(),
        "native_identity": _hardened_native_identity(),
        "output_inventory": experiment.registered_output_inventory(),
        "output_root": output_root,
        "pushed_remote_ref": "origin/master",
        "registration_id": "cross-fitted-source-test",
        "repository_commit": "a" * 40,
        "runtime_identity": _runtime_identity(),
        "schedule": {
            "canonical_search_start": fresh["canonical_search_start"],
            "chunk_count": 8,
            "chunks": [
                seeds[index : index + 64]
                for index in range(0, len(seeds), 64)
            ],
            "episodes_per_chunk": 64,
            "inventory_sha256": fresh["inventory_sha256"],
            "seeds": seeds,
            "seeds_sha256": hashlib.sha256(
                experiment.canonical_json_bytes(seeds)
            ).hexdigest(),
            "selection_schema_version": fresh["schema_version"],
        },
        "schema_version": experiment.REGISTRATION_SCHEMA_VERSION,
        "seed_inventory": inventory,
        "source_inventory": historical_source,
    }
    return experiment.validate_registration(registration)


def _compact_registration(
    source_inventory, *, output_root="D:/synthetic/cross-fitted-output"
):
    fixture = _compact_readiness_fixture(source_inventory)
    registration = experiment.build_readiness_bound_registration(
        registration_id="cross-fitted-compact-source-test",
        repository_commit=fixture["source_commit"],
        source_inventory=source_inventory,
        runtime_identity=_runtime_identity(),
        native_identity=_hardened_native_identity(),
        isolation_identity=_isolation_identity(),
        output_root=output_root,
        repo_root=ROOT,
        publication_commit=fixture["publication_commit"],
        readiness_report_path=fixture["report_path"],
        candidate_artifact_path=fixture["candidate_path"],
        verification_receipt_path=fixture["receipt_path"],
        git_text=fixture["git_text"],
        git_path_observer=fixture["git_path_observer"],
    )
    return registration, fixture


def _drifted_readiness_report(registration, fixture, case):
    changed = copy.deepcopy(registration)
    report = copy.deepcopy(fixture["report"])
    if case == "authority":
        report["authority"]["training"] = True
    elif case == "authority_zero":
        report["authority"]["training"] = 0
    elif case == "decision":
        report["decision"] = {
            "failed_gates": ["source_binding"],
            "reason": "no_go_source_binding",
            "status": "no_go",
        }
    elif case == "eligibility":
        report["eligibility"] = {
            "empirical_successor_registration_proposal_eligible": False
        }
    elif case == "eligibility_one":
        report["eligibility"] = {
            "empirical_successor_registration_proposal_eligible": 1
        }
    else:  # pragma: no cover - caller owns the cases.
        raise AssertionError(case)
    report_body = {
        key: value
        for key, value in report.items()
        if key != "readiness_identity_sha256"
    }
    report["readiness_identity_sha256"] = hashlib.sha256(
        experiment.canonical_json_bytes(report_body)
    ).hexdigest()
    report_payload = experiment.canonical_json_bytes(report)
    changed["readiness_evidence"]["readiness_report"].update(
        {
            "readiness_identity_sha256": report["readiness_identity_sha256"],
            "sha256": hashlib.sha256(report_payload).hexdigest(),
            "size_bytes": len(report_payload),
        }
    )

    receipt = copy.deepcopy(fixture["receipt"])
    receipt["publication_bindings"]["readiness_report.json"] = {
        "sha256": hashlib.sha256(report_payload).hexdigest(),
        "size_bytes": len(report_payload),
    }
    receipt["verification"].update(
        {
            "decision": report["decision"]["status"],
            "proposal_eligible": report["eligibility"][
                "empirical_successor_registration_proposal_eligible"
            ],
            "readiness_identity_sha256": report["readiness_identity_sha256"],
        }
    )
    receipt_body = {
        key: value
        for key, value in receipt.items()
        if key != "verification_receipt_sha256"
    }
    receipt["verification_receipt_sha256"] = hashlib.sha256(
        experiment.canonical_json_bytes(receipt_body)
    ).hexdigest()
    receipt_payload = experiment.canonical_json_bytes(receipt)
    changed["readiness_evidence"]["verification_receipt"].update(
        {
            "sha256": hashlib.sha256(receipt_payload).hexdigest(),
            "size_bytes": len(receipt_payload),
            "verification_receipt_sha256": receipt[
                "verification_receipt_sha256"
            ],
        }
    )

    def git_path_observer(root, ref, path):
        if ref == fixture["publication_commit"]:
            if path == fixture["report_path"]:
                return report_payload
            if path == fixture["receipt_path"]:
                return receipt_payload
        return fixture["git_path_observer"](root, ref, path)

    return changed, git_path_observer


def _hardened_authorized_values(source_inventory):
    registration = _hardened_registration(source_inventory)
    request = experiment.build_exact_execution_request(registration)
    approval = _approval(registration, request)
    authorization = experiment.build_execution_authorization(
        registration, request, approval
    )
    return registration, request, approval, authorization


def _preflight_injections(source_inventory, registration):
    commit = registration["repository_commit"]
    pushed_head = "b" * 40

    def git_text(_root, *args):
        if args == ("rev-parse", "HEAD"):
            return pushed_head
        if args == ("rev-parse", "origin/master"):
            return pushed_head
        if args == ("merge-base", "--is-ancestor", commit, pushed_head):
            return ""
        if args == ("status", "--porcelain", "--untracked-files=no"):
            return ""
        raise AssertionError(f"unexpected Git query: {args!r}")

    external = {
        registration["native_identity"]["module"]["path"]: registration[
            "native_identity"
        ]["module"],
        registration["isolation_identity"]["communication_mod_config"]["path"]:
            registration["isolation_identity"]["communication_mod_config"],
    }

    return {
        "checkpoint_snapshot_observer": lambda _root: copy.deepcopy(
            registration["isolation_identity"]["production_checkpoints"]
        ),
        "external_binding_observer": lambda path: copy.deepcopy(
            external[Path(path).resolve().as_posix()]
            if Path(path).exists()
            else external[str(path).replace("\\", "/")]
        ),
        "git_text": git_text,
        "runtime_identity_observer": lambda: copy.deepcopy(
            registration["runtime_identity"]
        ),
        "source_inventory_observer": lambda _root: copy.deepcopy(
            registration["source_inventory"]
        ),
        "tracked_blob_observer": lambda _root, ref, _payload: ref == pushed_head,
    }


def _registration(source_inventory, *, output_root="D:/synthetic/cross-fitted-output"):
    return _hardened_registration(source_inventory, output_root=output_root)


def _approval(registration, request):
    digest = request["request_sha256"]
    return experiment.bind_external_approval(
        registration,
        request,
        approved_request_sha256=digest,
        approval_text=(
            "I explicitly approve exact request "
            f"{digest} and every bound cohort and resource limit."
        ),
        approved_at="2026-08-06T12:00:00+08:00",
        provenance={
            "message_id": "human-message-1",
            "source": "external-human-message",
            "task_id": "control-plane-source-test",
        },
    )


def _authorized_values(source_inventory, *, output_root="D:/synthetic/cross-fitted-output"):
    registration = _registration(source_inventory, output_root=output_root)
    request = experiment.build_exact_execution_request(registration)
    approval = _approval(registration, request)
    authorization = experiment.build_execution_authorization(
        registration, request, approval
    )
    identity = experiment.execution_identity(
        registration, request, authorization, approval
    )
    return registration, request, approval, authorization, identity


def _authorized_output_values(source_inventory, output):
    return _authorized_values(
        source_inventory,
        output_root=Path(output).resolve().as_posix(),
    )


def _initialize_lifecycle(output, registration, identity, lease):
    experiment.initialize_access_journal(
        output,
        registration=registration,
        identity=identity,
        lease=lease,
    )
    experiment.initialize_resource_ledger(
        output,
        registration=registration,
        identity=identity,
        lease=lease,
    )
    return experiment.publish_bootstrap(
        output,
        registration=registration,
        identity=identity,
        lease=lease,
        runtime_checkpoint_payload={
            "model": "synthetic-bootstrap",
            "optimizer_step": 0,
        },
    )


def _complete_access(
    output,
    registration,
    identity,
    lease,
    *,
    chunk_index,
    seed,
    attempt_ordinal,
    status="completed",
):
    experiment.begin_environment_access(
        output,
        registration=registration,
        identity=identity,
        lease=lease,
        chunk_index=chunk_index,
        seed=seed,
        attempt_ordinal=attempt_ordinal,
    )
    return experiment.complete_environment_access(
        output,
        registration=registration,
        identity=identity,
        lease=lease,
        status=status,
    )


def _complete_chunk(
    output,
    registration,
    identity,
    lease,
    *,
    chunk_index,
    attempt_ordinal,
):
    journal_path = output / experiment.ACCESS_JOURNAL_FILENAME
    payload = journal_path.read_bytes()
    journal = experiment.load_access_journal(
        output, registration=registration, identity=identity
    )
    event_index = len(journal["events"])
    access_ordinal = journal["debited_accesses"] + 1
    for seed in registration["schedule"]["chunks"][chunk_index]:
        coordinate = {
            "access_ordinal": access_ordinal,
            "attempt_ordinal": attempt_ordinal,
            "chunk_index": chunk_index,
            "seed": seed,
        }
        debit = {
            **coordinate,
            "event_index": event_index,
            "kind": "access_debited",
            "schema_version": experiment.ACCESS_JOURNAL_SCHEMA_VERSION,
            "status": "debited",
        }
        terminal = {
            **coordinate,
            "event_index": event_index + 1,
            "kind": "access_terminal",
            "schema_version": experiment.ACCESS_JOURNAL_SCHEMA_VERSION,
            "status": "completed",
        }
        payload += experiment.canonical_json_bytes(debit)
        payload += experiment.canonical_json_bytes(terminal)
        event_index += 2
        access_ordinal += 1
    experiment.validate_access_journal_bytes(
        payload, registration=registration, identity=identity
    )
    journal_path.write_bytes(payload)
    experiment.reconcile_resource_ledger_from_journal(
        output,
        registration=registration,
        identity=identity,
        lease=lease,
    )


def _checkpoint_resources(output, identity, *, optimizer_updates):
    resources = dict(
        experiment.load_resource_ledger(output, identity=identity)["resources"]
    )
    resources["charged_seconds"] += 1.0
    resources["optimizer_updates"] = optimizer_updates
    resources["retained_decisions"] += 64
    resources["stored_bytes"] += 1_000_000
    resources["uncompressed_bytes"] += 1_000_000
    return resources


class _SyntheticRuntimeBlocked(ValueError):
    pass


class _SyntheticRuntimeModule:
    RuntimeBlocked = _SyntheticRuntimeBlocked

    def __init__(self):
        self.accessed_seeds = []

    @staticmethod
    def initialize_training_runtime():
        return types.SimpleNamespace(
            completed_decisions=0,
            completed_episodes=0,
            next_chunk_index=0,
            optimizer_updates=0,
        )

    @staticmethod
    def encode_runtime_checkpoint(state):
        return {
            "coordinates": {
                "completed_decisions": state.completed_decisions,
                "completed_episodes": state.completed_episodes,
                "next_chunk_index": state.next_chunk_index,
                "optimizer_updates": state.optimizer_updates,
            },
            "schema_version": "synthetic-runtime-checkpoint-v1",
        }

    @staticmethod
    def restore_training_runtime_from_checkpoint(value):
        coordinates = value["coordinates"]
        return types.SimpleNamespace(**coordinates)

    def collect_and_update_training_chunk(
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
        assert deadline >= clock()
        assert chunk_index == state.next_chunk_index
        for seed in seeds:
            before_environment(seed)
            environment = environment_factory(seed)
            assert environment["seed"] == seed
            assert environment["ascension"] == 0
            self.accessed_seeds.append(seed)
            after_environment(seed)
        state.completed_episodes += len(seeds)
        state.completed_decisions += 2 * len(seeds)
        state.optimizer_updates += 1
        state.next_chunk_index += 1
        return types.SimpleNamespace(
            episodes=tuple(
                types.SimpleNamespace(decisions=(object(), object())) for _ in seeds
            ),
            update={"chunk_index": chunk_index},
        )

    @staticmethod
    def build_chunk_evidence(update):
        return {
            "chunk_index": update["chunk_index"],
            "decisions": [],
            "schema_version": "synthetic-chunk-evidence-v1",
        }

    @staticmethod
    def classify_family_saturation(completed_chunks):
        return {
            "category": None,
            "family": None,
            "multi_family_decisions": 0,
            "stop": False,
            "window_chunk_indices": [
                value["chunk_index"] for value in completed_chunks[-4:]
            ],
        }


class _SyntheticFailingRuntimeModule(_SyntheticRuntimeModule):
    def collect_and_update_training_chunk(
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
        del state, chunk_index, after_environment, deadline, clock
        seed = seeds[0]
        before_environment(seed)
        environment_factory(seed)
        raise self.RuntimeBlocked("synthetic algorithm failure")


class _SyntheticInterruptedRuntimeModule(_SyntheticRuntimeModule):
    def collect_and_update_training_chunk(
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
        del state, chunk_index, after_environment, deadline, clock
        seed = seeds[0]
        before_environment(seed)
        environment_factory(seed)
        raise OSError("synthetic infrastructure interruption")


class _SyntheticPreAccessInterruptedRuntimeModule(_SyntheticRuntimeModule):
    def collect_and_update_training_chunk(self, *args, **kwargs):
        del args, kwargs
        raise OSError("synthetic pre-access interruption")


class _SyntheticPreAccessFailingRuntimeModule(_SyntheticRuntimeModule):
    def collect_and_update_training_chunk(self, *args, **kwargs):
        del args, kwargs
        raise self.RuntimeBlocked("synthetic pre-access algorithm failure")


class _ControlledClock:
    def __init__(self, value):
        self.value = float(value)

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += float(seconds)


class _SyntheticTimedInterruptedRuntimeModule(_SyntheticRuntimeModule):
    def __init__(self, *, elapsed=0.0, access_seed=True):
        super().__init__()
        self.elapsed = float(elapsed)
        self.access_seed = access_seed
        self.observed_deadline = None

    def collect_and_update_training_chunk(
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
        del state, chunk_index, after_environment
        self.observed_deadline = deadline
        if self.access_seed:
            seed = seeds[0]
            before_environment(seed)
            environment_factory(seed)
        clock.advance(self.elapsed)
        raise OSError("synthetic timed infrastructure interruption")


class _SyntheticTimedFailingRuntimeModule(_SyntheticRuntimeModule):
    def __init__(self, *, elapsed, message="synthetic algorithm failure"):
        super().__init__()
        self.elapsed = float(elapsed)
        self.message = str(message)

    def collect_and_update_training_chunk(
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
        del state, chunk_index, after_environment, deadline
        seed = seeds[0]
        before_environment(seed)
        environment_factory(seed)
        clock.advance(self.elapsed)
        raise self.RuntimeBlocked(self.message)


def _synthetic_loaded_dependencies(runtime):
    native = types.SimpleNamespace(
        Environment=lambda seed, ascension: {
            "ascension": ascension,
            "seed": seed,
        }
    )
    adapter = types.SimpleNamespace(
        NativeSimulatorEnvironment=lambda environment, _provenance: environment
    )
    return {
        "adapter": adapter,
        "native_module": native,
        "provenance": {"synthetic": True},
        "runtime": runtime,
    }


def test_control_import_and_contract_command_do_not_import_runtime_torch_or_adapter():
    source = r"""
import builtins
import json
import sys

original_import = builtins.__import__
forbidden = (
    "torch",
    "analysis_scripts.noncombat_simulator_adapter",
    "analysis_scripts.noncombat_cross_fitted_hierarchical_learning_runtime",
)

def guarded_import(name, *args, **kwargs):
    if any(name == item or name.startswith(item + ".") for item in forbidden):
        raise AssertionError("forbidden import: " + name)
    return original_import(name, *args, **kwargs)

builtins.__import__ = guarded_import
import analysis_scripts.noncombat_cross_fitted_hierarchical_learning_experiment as module
assert all(name not in sys.modules for name in forbidden)
module.main(["contract"])
"""

    completed = subprocess.run(
        [sys.executable, "-c", source],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )

    contract = json.loads(completed.stdout)
    assert contract["schema_version"] == experiment.CONTRACT_SCHEMA_VERSION
    assert set(contract["authority"].values()) == {False}


def test_contract_cli_is_byte_identical_across_two_fresh_processes():
    command = [
        sys.executable,
        str(
            ROOT
            / "analysis_scripts"
            / "noncombat_cross_fitted_hierarchical_learning_experiment.py"
        ),
        "contract",
    ]
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    outputs = [
        subprocess.run(
            command,
            cwd=ROOT,
            check=True,
            capture_output=True,
            env=environment,
        ).stdout
        for _process in range(2)
    ]

    assert outputs[0] == outputs[1] == experiment.canonical_json_bytes(
        experiment.experiment_contract()
    )


def test_execute_cli_loads_bound_documents_and_routes_the_exact_runner(
    source_inventory, tmp_path, monkeypatch, capsys
):
    output = tmp_path / "execution"
    registration, request, approval, authorization, _identity = (
        _authorized_output_values(source_inventory, output)
    )
    documents = {
        "registration.json": registration,
        "execution_request.json": request,
        "external_approval.json": approval,
        "authorization.json": authorization,
    }
    paths = {}
    for filename, value in documents.items():
        path = tmp_path / filename
        path.write_bytes(experiment.canonical_json_bytes(value))
        paths[filename] = path

    observed = {}

    def execute_exact(
        loaded_registration,
        loaded_request,
        loaded_authorization,
        loaded_approval,
        *,
        repo_root,
    ):
        observed.update(
            {
                "approval": loaded_approval,
                "authorization": loaded_authorization,
                "registration": loaded_registration,
                "repo_root": repo_root,
                "request": loaded_request,
            }
        )
        return {"status": "synthetic-terminal"}

    monkeypatch.setattr(experiment, "execute_authorized_experiment", execute_exact)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(Path(experiment.__file__).resolve()),
            "execute",
            "--repo-root",
            str(ROOT),
            "--registration",
            str(paths["registration.json"]),
            "--request",
            str(paths["execution_request.json"]),
            "--approval",
            str(paths["external_approval.json"]),
            "--authorization",
            str(paths["authorization.json"]),
        ],
    )

    assert experiment.main() == 0
    assert json.loads(capsys.readouterr().out) == {"status": "synthetic-terminal"}
    assert observed == {
        "approval": approval,
        "authorization": authorization,
        "registration": registration,
        "repo_root": ROOT,
        "request": request,
    }


def test_module_dependency_inventory_binds_exact_source_bytes(source_inventory):
    declared = experiment.module_dependency_inventory()

    assert {
        row["path"]
        for section in (declared["modules"], declared["public_dependencies"])
        for row in section
    } == {
        "analysis_scripts/__init__.py",
        "analysis_scripts/noncombat_action_family_distribution.py",
        "analysis_scripts/noncombat_cross_fitted_hierarchical_learning_experiment.py",
        "analysis_scripts/noncombat_cross_fitted_hierarchical_learning_runtime.py",
        "analysis_scripts/noncombat_cross_fitted_hierarchical_learning_seed_inventory.py",
        "analysis_scripts/noncombat_formal_reward_contract.py",
        "analysis_scripts/noncombat_hierarchical_advantage_attribution.py",
        "analysis_scripts/noncombat_hierarchical_policy_objective.py",
        "analysis_scripts/noncombat_hierarchical_simulator_learning_runtime.py",
        "analysis_scripts/noncombat_policy_model.py",
        "analysis_scripts/noncombat_simulator_adapter.py",
        "analysis_scripts/noncombat_simulator_rl_experiment.py",
        "analysis_scripts/noncombat_state_conditioned_policy_input.py",
        "analysis_scripts/noncombat_state_conditioned_ranker.py",
        "analysis_scripts/verify_noncombat_cross_fitted_hierarchical_learning_experiment.py",
    }

    assert [row["path"] for row in source_inventory["modules"]] == [
        row["path"] for row in declared["modules"]
    ]
    assert [row["path"] for row in source_inventory["public_dependencies"]] == [
        row["path"] for row in declared["public_dependencies"]
    ]
    for row in declared["public_dependencies"]:
        tree = ast.parse((ROOT / row["path"]).read_text(encoding="utf-8"))
        public_names = {
            node.name
            for node in tree.body
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        }
        assert set(row["public_symbols"]) <= public_names
    assert experiment.verify_source_inventory(source_inventory, ROOT) == source_inventory

    drifted = copy.deepcopy(source_inventory)
    drifted["modules"][0]["sha256"] = "f" * 64
    body = {
        key: value
        for key, value in drifted.items()
        if key != "inventory_sha256"
    }
    drifted["inventory_sha256"] = hashlib.sha256(
        experiment.canonical_json_bytes(body)
    ).hexdigest()
    assert experiment.validate_source_inventory(drifted) == drifted
    with pytest.raises(experiment.ExperimentBlocked, match="source inventory bytes"):
        experiment.verify_source_inventory(drifted, ROOT)


def test_contract_and_registration_bind_execution_environment(source_inventory):
    registration = _hardened_registration(source_inventory)
    contract = registration["contract"]

    assert contract["environment"] == {
        "adapter_api_version": "sts-lightspeed-noncombat-adapter-v3",
        "ascension": 0,
        "device": "cpu",
    }
    assert contract["runtime_metadata"] == experiment.expected_runtime_metadata()
    assert registration["pushed_remote_ref"] == "origin/master"
    assert registration["native_identity"] == _hardened_native_identity()
    assert registration["isolation_identity"] == _isolation_identity()

    changed = copy.deepcopy(registration)
    changed["native_identity"]["provenance"]["adapter_commit"] = "9" * 40
    with pytest.raises(experiment.ExperimentBlocked, match="provenance digest"):
        experiment.validate_registration(changed)

    changed = copy.deepcopy(registration)
    changed["pushed_remote_ref"] = "origin/feature"
    with pytest.raises(experiment.ExperimentBlocked, match="pushed remote"):
        experiment.validate_registration(changed)


def test_compact_registration_binds_immutable_readiness_publication(source_inventory):
    registration, fixture = _compact_registration(source_inventory)

    assert registration["schema_version"] == experiment.REGISTRATION_V2_SCHEMA_VERSION
    assert "seed_inventory" not in registration
    assert registration["repository_commit"] == fixture["source_commit"]
    assert registration["schedule"]["seeds"] == list(range(512))
    assert registration["readiness_evidence"] == {
        "candidate_artifact": {
            **fixture["report"]["candidate_artifact_binding"],
            "path": fixture["candidate_path"],
        },
        "publication_commit": fixture["publication_commit"],
        "readiness_report": {
            "path": fixture["report_path"],
            "readiness_identity_sha256": fixture["report"][
                "readiness_identity_sha256"
            ],
            "sha256": hashlib.sha256(
                experiment.canonical_json_bytes(fixture["report"])
            ).hexdigest(),
            "size_bytes": len(experiment.canonical_json_bytes(fixture["report"])),
        },
        "verification_receipt": {
            "path": fixture["receipt_path"],
            "sha256": hashlib.sha256(
                experiment.canonical_json_bytes(fixture["receipt"])
            ).hexdigest(),
            "size_bytes": len(experiment.canonical_json_bytes(fixture["receipt"])),
            "verification_receipt_sha256": fixture["receipt"][
                "verification_receipt_sha256"
            ],
        },
    }
    assert experiment.validate_registration(registration) == registration
    assert len(experiment.canonical_json_bytes(registration)) < 64 * 1024 * 1024


def test_compact_git_blob_observer_is_bounded_before_payload_validation():
    with pytest.raises(experiment.ExperimentBlocked, match="exceeds byte ceiling"):
        experiment._call_git_path_observer(
            lambda _root, _ref, _path: b"12345",
            ROOT,
            "a" * 40,
            "reports/synthetic-readiness/readiness_report.json",
            label="synthetic readiness blob",
            max_bytes=4,
        )


def test_compact_candidate_consumed_registration_is_source_bound(source_inventory):
    _registration, fixture = _compact_registration(source_inventory)

    experiment._validate_consumed_registration_source_binding(
        fixture["candidate"], fixture["report"]
    )
    changed = copy.deepcopy(fixture["candidate"])
    changed["consumed_cohort"]["registration_binding"]["sha256"] = "0" * 64

    with pytest.raises(
        experiment.ExperimentBlocked,
        match="consumed registration source binding",
    ):
        experiment._validate_consumed_registration_source_binding(
            changed, fixture["report"]
        )


def test_compact_candidate_requires_immutable_consumed_registration_blob(
    source_inventory,
):
    registration, fixture = _compact_registration(source_inventory)
    consumed_path = fixture["candidate"]["consumed_cohort"][
        "registration_binding"
    ]["path"]

    def git_path_observer(root, ref, path):
        if ref == fixture["source_commit"] and path == consumed_path:
            raise FileNotFoundError(path)
        return fixture["git_path_observer"](root, ref, path)

    with pytest.raises(
        experiment.ExperimentBlocked,
        match="consumed_registration.*cannot be inspected|consumed registration.*blob",
    ):
        experiment.verify_readiness_bound_registration(
            ROOT,
            registration,
            pushed_head=fixture["pushed_head"],
            git_text=fixture["git_text"],
            git_path_observer=git_path_observer,
        )


def test_compact_preflight_rechecks_readiness_and_registered_source_before_import(
    source_inventory,
):
    registration, fixture = _compact_registration(source_inventory)
    request = experiment.build_exact_execution_request(registration)
    approval = _approval(registration, request)
    authorization = experiment.build_execution_authorization(
        registration, request, approval
    )
    injections = _preflight_injections(source_inventory, registration)
    injections["git_text"] = fixture["git_text"]
    injections["git_path_observer"] = fixture["git_path_observer"]

    report = experiment.source_only_preflight(
        ROOT,
        registration,
        request,
        authorization,
        approval,
        **injections,
    )

    assert report["checks"]["readiness_candidate_exact"] is True
    assert report["checks"]["readiness_publication_exact"] is True
    assert report["checks"]["readiness_source_exact"] is True
    assert report["checks"]["readiness_verification_receipt_exact"] is True

    drifted = copy.deepcopy(registration)
    control_row = next(
        row
        for row in drifted["source_inventory"]["modules"]
        if row["name"] == "control_plane"
    )
    control_row["sha256"] = "f" * 64
    source_body = {
        key: drifted["source_inventory"][key]
        for key in ("modules", "public_dependencies", "schema_version")
    }
    drifted["source_inventory"]["inventory_sha256"] = hashlib.sha256(
        experiment.canonical_json_bytes(source_body)
    ).hexdigest()

    with pytest.raises(
        experiment.ExperimentBlocked,
        match="registered source|readiness.*source|source.*commit",
    ):
        experiment.verify_readiness_bound_registration(
            ROOT,
            drifted,
            pushed_head=fixture["pushed_head"],
            git_text=fixture["git_text"],
            git_path_observer=fixture["git_path_observer"],
        )


def test_post_change_control_plane_rejects_real_r2_readiness_evidence(
    source_inventory,
):
    source_commit = "522185d06ddf48cb1be095c16efacaad299a0197"
    publication_commit = "b928eadbdace3eee8386df96bb9b7fe076a24630"
    readiness_root = (
        "reports/noncombat_cross_fitted_empirical_successor_readiness_20260808_r2"
    )
    report_path = f"{readiness_root}/readiness_report.json"
    candidate_path = f"{readiness_root}/candidate_seed_inventory.json.gz"
    receipt_path = (
        "reports/noncombat_cross_fitted_empirical_successor_readiness_attempts/"
        f"{source_commit}/attempt_verified.json"
    )
    report_payload = (ROOT / report_path).read_bytes()
    report = json.loads(report_payload)
    receipt_payload = (ROOT / receipt_path).read_bytes()
    receipt = json.loads(receipt_payload)
    registration = _hardened_registration(source_inventory)
    registration["repository_commit"] = source_commit
    registration["schema_version"] = experiment.REGISTRATION_V2_SCHEMA_VERSION
    registration["source_inventory"] = copy.deepcopy(source_inventory)
    registration.pop("seed_inventory")
    registration["readiness_evidence"] = {
        "candidate_artifact": {
            **report["candidate_artifact_binding"],
            "path": candidate_path,
        },
        "publication_commit": publication_commit,
        "readiness_report": {
            "path": report_path,
            "readiness_identity_sha256": report["readiness_identity_sha256"],
            "sha256": hashlib.sha256(report_payload).hexdigest(),
            "size_bytes": len(report_payload),
        },
        "verification_receipt": {
            "path": receipt_path,
            "sha256": hashlib.sha256(receipt_payload).hexdigest(),
            "size_bytes": len(receipt_payload),
            "verification_receipt_sha256": receipt[
                "verification_receipt_sha256"
            ],
        },
    }

    with pytest.raises(
        experiment.ExperimentBlocked,
        match="registered source|readiness source binding mismatch",
    ):
        experiment.verify_readiness_bound_registration(ROOT, registration)


def test_real_r1_registration_remains_producer_and_cli_validatable(capsys):
    registration_path = (
        ROOT
        / "reports/noncombat_cross_fitted_hierarchical_learning_successor_20260806_r1/registration.json"
    )
    payload = registration_path.read_bytes()
    registration = json.loads(payload)

    assert experiment.validate_registration(registration) == registration
    assert experiment.main(
        [
            "inspect-registration",
            "--repo-root",
            str(ROOT),
            "--registration",
            str(registration_path),
        ]
    ) == 0
    assert json.loads(capsys.readouterr().out) == registration
    assert registration_path.read_bytes() == payload


def test_compact_registration_rejects_verification_receipt_drift(source_inventory):
    registration, fixture = _compact_registration(source_inventory)
    changed = copy.deepcopy(registration)
    receipt = copy.deepcopy(fixture["receipt"])
    receipt["verification"]["decision"] = "no_go"
    receipt_body = {
        key: value
        for key, value in receipt.items()
        if key != "verification_receipt_sha256"
    }
    receipt["verification_receipt_sha256"] = hashlib.sha256(
        experiment.canonical_json_bytes(receipt_body)
    ).hexdigest()
    payload = experiment.canonical_json_bytes(receipt)
    changed["readiness_evidence"]["verification_receipt"].update(
        {
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
            "verification_receipt_sha256": receipt[
                "verification_receipt_sha256"
            ],
        }
    )

    def git_path_observer(root, ref, path):
        if (
            ref == fixture["publication_commit"]
            and path == fixture["receipt_path"]
        ):
            return payload
        return fixture["git_path_observer"](root, ref, path)

    with pytest.raises(
        experiment.ExperimentBlocked, match="verification.*summary|receipt.*verified"
    ):
        experiment.verify_readiness_bound_registration(
            ROOT,
            changed,
            pushed_head=fixture["pushed_head"],
            git_text=fixture["git_text"],
            git_path_observer=git_path_observer,
        )

    changed = copy.deepcopy(registration)
    changed["readiness_evidence"]["verification_receipt"]["path"] = (
        "reports/synthetic-readiness/attempt_verified.json"
    )
    with pytest.raises(
        experiment.ExperimentBlocked, match="verification receipt path"
    ):
        experiment.validate_registration(changed)


def test_compact_registration_rejects_unpublished_readiness_ancestry(
    source_inventory,
):
    registration, fixture = _compact_registration(source_inventory)

    def git_text(root, *args):
        if args == (
            "merge-base",
            "--is-ancestor",
            fixture["publication_commit"],
            fixture["pushed_head"],
        ):
            raise experiment.ExperimentBlocked("synthetic unpublished evidence")
        return fixture["git_text"](root, *args)

    with pytest.raises(
        experiment.ExperimentBlocked,
        match="pushed readiness publication ancestry mismatch",
    ):
        experiment.verify_readiness_bound_registration(
            ROOT,
            registration,
            pushed_head=fixture["pushed_head"],
            git_text=git_text,
            git_path_observer=fixture["git_path_observer"],
        )


@pytest.mark.parametrize(
    ("binding_name", "path_name", "error"),
    [
        ("readiness_report", "report_path", "readiness report bytes mismatch"),
        ("candidate_artifact", "candidate_path", "candidate validation failed"),
    ],
)
def test_compact_registration_rejects_readiness_blob_drift(
    binding_name, path_name, error, source_inventory
):
    registration, fixture = _compact_registration(source_inventory)
    target_path = fixture[path_name]

    def git_path_observer(root, ref, path):
        payload = fixture["git_path_observer"](root, ref, path)
        if ref == fixture["publication_commit"] and path == target_path:
            return payload + b"x"
        return payload

    with pytest.raises(experiment.ExperimentBlocked, match=error):
        experiment.verify_readiness_bound_registration(
            ROOT,
            registration,
            pushed_head=fixture["pushed_head"],
            git_text=fixture["git_text"],
            git_path_observer=git_path_observer,
        )


@pytest.mark.parametrize(
    ("case", "error"),
    [
        ("authority", "authority must remain all false"),
        ("authority_zero", "authority must remain all false"),
        ("decision", "readiness report is not go"),
        ("eligibility", "not registration eligible"),
        ("eligibility_one", "not registration eligible"),
    ],
)
def test_compact_registration_rejects_semantically_drifted_go_report(
    case, error, source_inventory
):
    registration, fixture = _compact_registration(source_inventory)
    changed, git_path_observer = _drifted_readiness_report(
        registration, fixture, case
    )

    with pytest.raises(experiment.ExperimentBlocked, match=error):
        experiment.verify_readiness_bound_registration(
            ROOT,
            changed,
            pushed_head=fixture["pushed_head"],
            git_text=fixture["git_text"],
            git_path_observer=git_path_observer,
        )


@pytest.mark.parametrize(
    ("binding_name", "path", "error"),
    [
        (
            "candidate_artifact",
            "reports/synthetic-readiness/candidate.json.gz",
            "candidate filename",
        ),
        (
            "readiness_report",
            "reports/other-readiness/readiness_report.json",
            "must be siblings",
        ),
    ],
)
def test_compact_registration_rejects_readiness_path_drift(
    binding_name, path, error, source_inventory
):
    registration, _fixture = _compact_registration(source_inventory)
    registration["readiness_evidence"][binding_name]["path"] = path

    with pytest.raises(experiment.ExperimentBlocked, match=error):
        experiment.validate_registration(registration)


@pytest.mark.parametrize("command", ["inspect-registration", "render-request"])
def test_compact_cli_replays_readiness_evidence(
    command, source_inventory, tmp_path, monkeypatch, capsys
):
    registration, _fixture = _compact_registration(source_inventory)
    registration_path = tmp_path / "registration.json"
    registration_path.write_bytes(experiment.canonical_json_bytes(registration))
    observed = []

    def verify(repo_root, value):
        observed.append((Path(repo_root).resolve(), value))
        return {"status": "passed"}

    monkeypatch.setattr(experiment, "verify_readiness_bound_registration", verify)

    assert experiment.main(
        [
            command,
            "--repo-root",
            str(ROOT),
            "--registration",
            str(registration_path),
        ]
    ) == 0
    capsys.readouterr()
    assert observed == [(ROOT.resolve(), registration)]


def test_external_file_and_complete_checkpoint_tree_bindings_are_inert(tmp_path):
    config = tmp_path / "config.properties"
    config.write_bytes(b'command="synthetic"\n')
    checkpoints = tmp_path / "checkpoints"
    (checkpoints / "nested").mkdir(parents=True)
    (checkpoints / "model-a.pth").write_bytes(b"model-a")
    (checkpoints / "nested" / "model-b.pth").write_bytes(b"model-b")

    config_binding = experiment.external_file_binding(config)
    first = experiment.snapshot_production_checkpoints(checkpoints)
    second = experiment.snapshot_production_checkpoints(checkpoints)

    assert config_binding["path"] == config.resolve().as_posix()
    assert config_binding["size_bytes"] == len(b'command="synthetic"\n')
    assert first == second
    assert first["file_count"] == 2
    assert first["size_bytes"] == len(b"model-a") + len(b"model-b")

    (checkpoints / "nested" / "model-b.pth").write_bytes(b"changed")
    assert experiment.snapshot_production_checkpoints(checkpoints) != first


def test_registration_is_exact_and_all_false(source_inventory):
    registration = _registration(source_inventory)

    assert experiment.validate_registration(registration) == registration
    assert set(registration["authority"].values()) == {False}
    assert registration["contract"] == experiment.experiment_contract()
    assert registration["schedule"]["seeds"] == list(range(512))
    assert registration["seed_inventory"] == _seed_inventory()
    assert len(registration["schedule"]["chunks"]) == 8
    assert {len(chunk) for chunk in registration["schedule"]["chunks"]} == {64}
    assert registration["output_inventory"] == experiment.registered_output_inventory()

    changed = copy.deepcopy(registration)
    changed["authority"]["seed_access"] = True
    with pytest.raises(experiment.ExperimentBlocked, match="all false"):
        experiment.validate_registration(changed)

    changed = copy.deepcopy(registration)
    changed["schedule"]["seeds"][0], changed["schedule"]["seeds"][1] = (
        changed["schedule"]["seeds"][1],
        changed["schedule"]["seeds"][0],
    )
    with pytest.raises(experiment.ExperimentBlocked, match="fixed seed inventory"):
        experiment.validate_registration(changed)


def test_new_v1_registration_builder_is_disabled(source_inventory):
    kwargs = {
        "registration_id": "cross-fitted-source-test",
        "repository_commit": "a" * 40,
        "source_inventory": source_inventory,
        "runtime_identity": _runtime_identity(),
        "native_identity": _hardened_native_identity(),
        "isolation_identity": _isolation_identity(),
        "seed_inventory": _seed_inventory(),
        "output_root": "D:/synthetic/cross-fitted-output",
    }
    with pytest.raises(
        experiment.ExperimentBlocked, match="new v1 registration.*disabled"
    ):
        experiment.build_source_only_registration(**kwargs)


def test_exact_request_is_deterministic_and_read_only(source_inventory, tmp_path):
    output = tmp_path / "future-output"
    registration = _registration(source_inventory, output_root=output.as_posix())

    first = experiment.build_exact_execution_request(registration)
    second = experiment.build_exact_execution_request(registration)

    assert first == second
    assert experiment.canonical_json_bytes(first) == experiment.canonical_json_bytes(
        second
    )
    assert output.exists() is False
    assert first["authority"] == experiment.registration_authority()
    assert set(first["authority"].values()) == {False}
    assert first["requested_execution_authority"] == experiment.execution_authority()
    assert first["schedule"]["seeds"] == registration["schedule"]["seeds"]
    assert first["resources"]["max_environment_accesses"] == 576
    assert first["resources"]["max_charged_seconds"] == 14_400.0
    assert first["resume"]["maximum_post_start_resumes"] == 1
    assert first["operations"]["optimizer_updates_maximum"] == 8
    assert experiment.validate_exact_execution_request(first, registration) == first

    changed = copy.deepcopy(first)
    changed["resources"]["max_charged_seconds"] += 1.0
    with pytest.raises(experiment.ExperimentBlocked, match="exact registration"):
        experiment.validate_exact_execution_request(changed, registration)


def test_external_approval_and_authorization_are_exact_and_fail_closed(
    source_inventory,
):
    registration, request, approval, authorization, _ = _authorized_values(
        source_inventory
    )

    assert experiment.validate_external_approval(
        approval, registration, request
    ) == approval
    assert experiment.validate_execution_authorization(
        authorization, registration, request, approval
    ) == authorization
    enabled = {name for name, enabled in authorization["authority"].items() if enabled}
    assert enabled == {
        "environment_construction",
        "execution",
        "model_fitting",
        "native_loading",
        "seed_access",
        "training",
    }
    for forbidden in (
        "communication_mod",
        "evaluation",
        "formal_rl",
        "gameplay",
        "model_loading",
        "policy_promotion",
        "qualification",
    ):
        assert authorization["authority"][forbidden] is False

    with pytest.raises(experiment.ExperimentBlocked, match="external approval"):
        experiment.validate_execution_authorization(
            authorization, registration, request
        )

    with pytest.raises(experiment.ExperimentBlocked, match="digest mismatch"):
        experiment.bind_external_approval(
            registration,
            request,
            approved_request_sha256="f" * 64,
            approval_text="I approve " + "f" * 64,
            approved_at="2026-08-06T12:00:00+08:00",
            provenance=approval["provenance"],
        )

    with pytest.raises(experiment.ExperimentBlocked, match="does not name"):
        experiment.bind_external_approval(
            registration,
            request,
            approved_request_sha256=request["request_sha256"],
            approval_text="I grant broad standing permission.",
            approved_at="2026-08-06T12:00:00+08:00",
            provenance=approval["provenance"],
        )

    changed = copy.deepcopy(authorization)
    changed["authority"]["gameplay"] = True
    with pytest.raises(experiment.ExperimentBlocked, match="binding mismatch"):
        experiment.validate_execution_authorization(
            changed, registration, request, approval
        )


def test_failed_authorization_never_reaches_lazy_runtime_import(
    source_inventory, monkeypatch
):
    registration, request, approval, authorization, _ = _authorized_values(
        source_inventory
    )
    imported = []

    def forbidden_import(name):
        imported.append(name)
        raise AssertionError("runtime importer must not be reached")

    monkeypatch.setattr(experiment.importlib, "import_module", forbidden_import)

    with pytest.raises(experiment.ExperimentBlocked, match="external approval"):
        experiment.load_authorized_runtime(
            registration, request, authorization, approval=None
        )
    assert imported == []


def test_source_only_preflight_rechecks_pushed_clean_bytes_before_import(
    source_inventory,
):
    registration, request, approval, authorization = _hardened_authorized_values(
        source_inventory
    )
    injections = _preflight_injections(source_inventory, registration)

    report = experiment.source_only_preflight(
        ROOT,
        registration,
        request,
        authorization,
        approval,
        **injections,
    )

    assert report["repository_commit"] == "a" * 40
    assert report["pushed_head_commit"] == "b" * 40
    assert set(report["checks"].values()) == {True}
    assert report["checks"] == {
        "communication_mod_unchanged": True,
        "native_module_unchanged": True,
        "production_checkpoints_unchanged": True,
        "pushed_registration_exact": True,
        "pushed_source_exact": True,
        "runtime_identity_exact": True,
        "source_inventory_exact": True,
        "tracked_authorization_exact": True,
        "tracked_worktree_clean": True,
    }

    imported = []

    def forbidden_import(name):
        imported.append(name)
        raise AssertionError("preflight drift must fail before dependency import")

    drifted = dict(injections)
    drifted["git_text"] = lambda _root, *args: (
        "f" * 40
        if args == ("rev-parse", "origin/master")
        else injections["git_text"](_root, *args)
    )
    with pytest.raises(experiment.ExperimentBlocked, match="pushed HEAD"):
        experiment.load_authorized_runtime(
            registration,
            request,
            authorization,
            approval=approval,
            repo_root=ROOT,
            module_importer=forbidden_import,
            module_registry={},
            **drifted,
        )
    assert imported == []


@pytest.mark.parametrize(
    ("missing_document", "message"),
    [
        ("registration", "pushed registration"),
        ("authorization", "tracked authorization"),
    ],
)
def test_source_only_preflight_requires_pushed_registration_and_authorization(
    source_inventory, missing_document, message
):
    registration, request, approval, authorization = _hardened_authorized_values(
        source_inventory
    )
    injections = _preflight_injections(source_inventory, registration)
    missing_payload = experiment.canonical_json_bytes(
        registration if missing_document == "registration" else authorization
    )
    injections["tracked_blob_observer"] = (
        lambda _root, _ref, payload: payload != missing_payload
    )
    imported = []

    with pytest.raises(experiment.ExperimentBlocked, match=message):
        experiment.load_authorized_runtime(
            registration,
            request,
            authorization,
            approval=approval,
            repo_root=ROOT,
            module_importer=lambda name: imported.append(name),
            module_registry={},
            **injections,
        )

    assert imported == []


def test_dependency_loader_is_native_before_torch_and_checks_full_metadata(
    source_inventory,
):
    registration, request, approval, authorization = _hardened_authorized_values(
        source_inventory
    )
    injections = _preflight_injections(source_inventory, registration)
    events = []
    registry = {}
    provenance = registration["native_identity"]["provenance"]
    native_build = copy.deepcopy(provenance["build"])
    native_build.pop("python")
    native_module = types.SimpleNamespace(
        adapter_api_version=lambda: "sts-lightspeed-noncombat-adapter-v3",
        build_info_json=lambda: json.dumps(native_build),
    )

    def load_native_module(path, *, dll_directories):
        events.append(("load_native", str(path), [str(item) for item in dll_directories]))
        registry[experiment.NATIVE_MODULE_NAME] = native_module
        return native_module

    adapter = types.SimpleNamespace(
        __file__=(ROOT / "analysis_scripts/noncombat_simulator_adapter.py").as_posix(),
        load_native_module=load_native_module,
        validate_provenance=lambda value: (
            events.append(("validate_provenance",)), copy.deepcopy(dict(value))
        )[1],
    )
    runtime = types.SimpleNamespace(
        __file__=(
            ROOT
            / "analysis_scripts/noncombat_cross_fitted_hierarchical_learning_runtime.py"
        ).as_posix(),
        runtime_metadata=lambda: (
            events.append(("runtime_metadata",)),
            copy.deepcopy(registration["contract"]["runtime_metadata"]),
        )[1],
    )

    def importer(name):
        events.append(("import", name))
        if name == experiment.ADAPTER_MODULE_NAME:
            return adapter
        if name == experiment.RUNTIME_MODULE_NAME:
            registry["torch"] = types.SimpleNamespace(__name__="torch")
            return runtime
        raise AssertionError(f"unexpected import: {name}")

    loaded = experiment.load_authorized_runtime(
        registration,
        request,
        authorization,
        approval=approval,
        repo_root=ROOT,
        module_importer=importer,
        module_registry=registry,
        **injections,
    )

    assert loaded is runtime
    assert [event[0] for event in events] == [
        "import",
        "load_native",
        "validate_provenance",
        "import",
        "runtime_metadata",
    ]
    assert events[0] == ("import", experiment.ADAPTER_MODULE_NAME)
    assert events[3] == ("import", experiment.RUNTIME_MODULE_NAME)

    for preloaded in ("torch", experiment.NATIVE_MODULE_NAME):
        imported = []
        with pytest.raises(experiment.ExperimentBlocked, match="pre-imported"):
            experiment.load_authorized_runtime(
                registration,
                request,
                authorization,
                approval=approval,
                repo_root=ROOT,
                module_importer=lambda name: imported.append(name),
                module_registry={preloaded: object()},
                **injections,
            )
        assert imported == []

    mismatched_runtime = types.SimpleNamespace(
        __file__=runtime.__file__,
        runtime_metadata=lambda: {
            **copy.deepcopy(registration["contract"]["runtime_metadata"]),
            "fold_count": 5,
        },
    )
    mismatch_registry = {}

    def mismatch_importer(name):
        if name == experiment.ADAPTER_MODULE_NAME:
            return types.SimpleNamespace(
                __file__=adapter.__file__,
                load_native_module=lambda *_args, **_kwargs: native_module,
                validate_provenance=lambda value: copy.deepcopy(dict(value)),
            )
        if name == experiment.RUNTIME_MODULE_NAME:
            return mismatched_runtime
        raise AssertionError(f"unexpected import: {name}")

    with pytest.raises(experiment.ExperimentBlocked, match="runtime metadata"):
        experiment.load_authorized_runtime(
            registration,
            request,
            authorization,
            approval=approval,
            repo_root=ROOT,
            module_importer=mismatch_importer,
            module_registry=mismatch_registry,
            **injections,
        )

    changed = copy.deepcopy(authorization)
    changed["request_sha256"] = "f" * 64
    with pytest.raises(experiment.ExperimentBlocked, match="binding mismatch"):
        experiment.load_authorized_runtime(
            registration, request, changed, approval=approval
        )
    assert imported == []


def test_execution_lease_records_owner_and_is_exclusive(
    source_inventory, tmp_path
):
    _, _, _, _, identity = _authorized_values(
        source_inventory, output_root=(tmp_path / "registered").as_posix()
    )
    output = tmp_path / "execution"

    with experiment.ExecutionLease(output, identity=identity) as lease:
        assert lease.held is True
        assert lease.owner["process_id"] == os.getpid()
        with pytest.raises(experiment.ExperimentBlocked, match="already held"):
            with experiment.ExecutionLease(output, identity=identity):
                pass
    assert lease.held is False
    payload = json.loads((output / experiment.LEASE_FILENAME).read_bytes())
    assert payload["identity"] == identity
    assert payload["owner"]["process_id"] == os.getpid()
    assert payload["owner"]["token"] == lease.owner["token"]

    changed = {**identity, "request_sha256": "f" * 64}
    with pytest.raises(experiment.ExperimentBlocked, match="identity mismatch"):
        with experiment.ExecutionLease(
            output,
            identity=changed,
            allow_stale_reclaim=True,
            owner_alive=lambda _pid: False,
        ):
            pass

    unrelated = tmp_path / "unrelated-output"
    unrelated.mkdir()
    with pytest.raises(experiment.ExperimentBlocked, match="lacks an execution lease"):
        with experiment.ExecutionLease(unrelated, identity=identity):
            pass


def test_validated_execution_context_owns_one_checked_registration(
    source_inventory, tmp_path, monkeypatch
):
    output = tmp_path / "execution"
    registration, _, _, _, identity = _authorized_output_values(
        source_inventory, output
    )
    original_output = registration["output_root"]
    original_validate = experiment.validate_registration
    calls = 0

    def counted_validate(value):
        nonlocal calls
        calls += 1
        return original_validate(value)

    monkeypatch.setattr(experiment, "validate_registration", counted_validate)
    context = experiment._build_validated_execution_context(
        registration, identity, output
    )

    assert calls == 1
    assert context["output_root"] == original_output
    assert experiment.registration_sha256(context) == identity[
        "registration_sha256"
    ]
    normalized, normalized_identity, normalized_output = (
        experiment._registration_for_output(context, identity, output)
    )
    assert normalized is context
    assert normalized_identity == identity
    assert normalized_output == output.resolve()
    assert calls == 1

    registration["output_root"] = (tmp_path / "caller-mutation").as_posix()
    assert context["output_root"] == original_output
    assert calls == 1

    with pytest.raises(TypeError, match="immutable"):
        context["contract"]["limits"]["max_charged_seconds"] = 1.0
    with pytest.raises(TypeError, match="immutable"):
        context["schedule"]["chunks"][0].append(999_999)
    assert experiment.registration_sha256(context) == identity[
        "registration_sha256"
    ]
    assert calls == 1

    corrupt = copy.deepcopy(registration)
    corrupt["registration_id"] = "wrong-registration"
    with pytest.raises(experiment.ExperimentBlocked, match="registration|identity"):
        experiment._build_validated_execution_context(corrupt, identity, output)


def test_validated_context_keeps_64_access_validation_count_constant(
    source_inventory, tmp_path, monkeypatch
):
    output = tmp_path / "execution"
    registration, _, _, _, identity = _authorized_output_values(
        source_inventory, output
    )
    original_validate = experiment.validate_registration
    calls = 0

    def counted_validate(value):
        nonlocal calls
        calls += 1
        return original_validate(value)

    monkeypatch.setattr(experiment, "validate_registration", counted_validate)
    context = experiment._build_validated_execution_context(
        registration, identity, output
    )
    boundary_calls = calls

    with experiment.ExecutionLease(output, identity=identity) as lease:
        _initialize_lifecycle(output, context, identity, lease)
        for seed in registration["schedule"]["chunks"][0]:
            _complete_access(
                output,
                context,
                identity,
                lease,
                chunk_index=0,
                seed=seed,
                attempt_ordinal=0,
            )
        assert calls == boundary_calls == 1
        journal = experiment.load_access_journal(
            output, registration=context, identity=identity
        )
        ledger = experiment.load_resource_ledger(output, identity=identity)
        assert journal["completed_accesses"] == 64
        assert ledger["resources"]["environment_accesses"] == 64

        journal_path = output / experiment.ACCESS_JOURNAL_FILENAME
        journal_path.write_bytes(journal_path.read_bytes() + b"{}\n")
        with pytest.raises(experiment.ExperimentBlocked):
            experiment.load_access_journal(
                output, registration=context, identity=identity
            )


def test_stale_lease_reclamation_requires_same_identity_and_dead_owner(
    source_inventory, tmp_path
):
    _, _, _, _, identity = _authorized_values(
        source_inventory, output_root=(tmp_path / "registered").as_posix()
    )
    output = tmp_path / "execution"
    output.mkdir()
    stale_owner = {
        "acquired_at_ns": 1,
        "process_id": 999_999,
        "token": "1" * 32,
    }
    stale = {
        "identity": identity,
        "owner": stale_owner,
        "reclaimed_owner": None,
        "schema_version": experiment.LEASE_SCHEMA_VERSION,
    }
    (output / experiment.LEASE_FILENAME).write_bytes(
        experiment.canonical_json_bytes(stale)
    )

    with pytest.raises(experiment.ExperimentBlocked, match="still alive"):
        with experiment.ExecutionLease(
            output,
            identity=identity,
            allow_stale_reclaim=True,
            owner_alive=lambda _pid: True,
        ):
            pass

    with experiment.ExecutionLease(
        output,
        identity=identity,
        allow_stale_reclaim=True,
        owner_alive=lambda _pid: False,
    ) as lease:
        assert lease.reclaimed_owner == stale_owner
        assert lease.owner["process_id"] == os.getpid()
    payload = json.loads((output / experiment.LEASE_FILENAME).read_bytes())
    assert payload["reclaimed_owner"] == stale_owner
    assert payload["owner"]["process_id"] == os.getpid()


def test_access_journal_is_write_ahead_and_prefix_preserving(
    source_inventory, tmp_path
):
    output = tmp_path / "execution"
    registration, _, _, _, identity = _authorized_output_values(
        source_inventory, output
    )

    with experiment.ExecutionLease(output, identity=identity) as lease:
        experiment.initialize_access_journal(
            output, registration=registration, identity=identity, lease=lease
        )
        experiment.initialize_resource_ledger(
            output,
            registration=registration,
            identity=identity,
            lease=lease,
        )
        journal_path = output / experiment.ACCESS_JOURNAL_FILENAME
        initial_prefix = journal_path.read_bytes()

        debit = experiment.begin_environment_access(
            output,
            registration=registration,
            identity=identity,
            lease=lease,
            chunk_index=0,
            seed=0,
            attempt_ordinal=0,
        )
        after_debit = journal_path.read_bytes()
        assert after_debit.startswith(initial_prefix)
        assert debit["status"] == "debited"
        assert debit["access_ordinal"] == 1
        assert experiment.load_resource_ledger(
            output, identity=identity
        )["resources"]["environment_accesses"] == 1

        terminal = experiment.complete_environment_access(
            output, registration=registration, identity=identity, lease=lease
        )
        after_terminal = journal_path.read_bytes()
        assert after_terminal.startswith(after_debit)
        assert terminal["status"] == "completed"
        journal = experiment.load_access_journal(
            output, registration=registration, identity=identity
        )
        assert journal["debited_accesses"] == 1
        assert journal["completed_accesses"] == 1
        assert journal["pending_access"] is None


def test_interruption_after_journal_debit_reconciles_without_resource_rollback(
    source_inventory, tmp_path, monkeypatch
):
    output = tmp_path / "execution"
    registration, _, _, _, identity = _authorized_output_values(
        source_inventory, output
    )
    original_reconcile = experiment.reconcile_resource_ledger_from_journal

    with experiment.ExecutionLease(output, identity=identity) as lease:
        _initialize_lifecycle(output, registration, identity, lease)

        def interrupt_after_debit(*_args, **_kwargs):
            raise experiment.ExperimentBlocked("synthetic interruption")

        monkeypatch.setattr(
            experiment,
            "reconcile_resource_ledger_from_journal",
            interrupt_after_debit,
        )
        with pytest.raises(experiment.ExperimentBlocked, match="synthetic interruption"):
            experiment.begin_environment_access(
                output,
                registration=registration,
                identity=identity,
                lease=lease,
                chunk_index=0,
                seed=0,
                attempt_ordinal=0,
            )

        assert experiment.load_access_journal(
            output, registration=registration, identity=identity
        )["pending_access"]["seed"] == 0
        assert experiment.load_resource_ledger(
            output, identity=identity
        )["resources"]["environment_accesses"] == 0

        monkeypatch.setattr(
            experiment,
            "reconcile_resource_ledger_from_journal",
            original_reconcile,
        )
        marker = experiment.start_incomplete_chunk_resume(
            output,
            registration=registration,
            identity=identity,
            lease=lease,
        )
        reconciled = experiment.load_resource_ledger(output, identity=identity)
        assert marker["status"] == "resume_used"
        assert reconciled["resources"]["environment_accesses"] == 1
        assert reconciled["revision"] == 1


def test_resource_ledger_is_append_only_monotonic_and_bounded(
    source_inventory, tmp_path
):
    output = tmp_path / "execution"
    registration, _, _, _, identity = _authorized_output_values(
        source_inventory, output
    )

    with experiment.ExecutionLease(output, identity=identity) as lease:
        experiment.initialize_resource_ledger(
            output,
            registration=registration,
            identity=identity,
            lease=lease,
        )
        ledger_path = output / experiment.RESOURCE_LEDGER_FILENAME
        initial_prefix = ledger_path.read_bytes()
        resources = {
            "charged_seconds": 1.5,
            "environment_accesses": 0,
            "optimizer_updates": 0,
            "retained_decisions": 5,
            "stored_bytes": 10,
            "uncompressed_bytes": 20,
        }
        advanced = experiment.advance_resource_ledger(
            output,
            registration=registration,
            identity=identity,
            lease=lease,
            resources=resources,
            reason="synthetic-evidence",
        )
        assert ledger_path.read_bytes().startswith(initial_prefix)
        assert advanced["revision"] == 1
        assert advanced["resources"] == resources

        decreased = dict(resources)
        decreased["retained_decisions"] = 4
        with pytest.raises(experiment.ExperimentBlocked, match="not monotonic"):
            experiment.advance_resource_ledger(
                output,
                registration=registration,
                identity=identity,
                lease=lease,
                resources=decreased,
                reason="rollback",
            )

        exceeded = dict(resources)
        exceeded["stored_bytes"] = 192 * 1024 * 1024 + 1
        with pytest.raises(experiment.ExperimentBlocked, match="registered limit"):
            experiment.advance_resource_ledger(
                output,
                registration=registration,
                identity=identity,
                lease=lease,
                resources=exceeded,
                reason="overflow",
            )

        assert experiment.load_resource_ledger(output, identity=identity) == advanced


def test_journal_binds_exact_schedule_and_persists_only_one_chunk_replay(
    source_inventory, tmp_path
):
    output = tmp_path / "execution"
    registration, _, _, _, identity = _authorized_output_values(
        source_inventory, output
    )

    with experiment.ExecutionLease(output, identity=identity) as lease:
        _initialize_lifecycle(output, registration, identity, lease)
        journal_path = output / experiment.ACCESS_JOURNAL_FILENAME
        initial = journal_path.read_bytes()

        for chunk_index, seed in ((0, 1), (1, 0)):
            with pytest.raises(experiment.ExperimentBlocked, match="exact chunk/seed"):
                experiment.begin_environment_access(
                    output,
                    registration=registration,
                    identity=identity,
                    lease=lease,
                    chunk_index=chunk_index,
                    seed=seed,
                    attempt_ordinal=0,
                )
            assert journal_path.read_bytes() == initial

        _complete_access(
            output,
            registration,
            identity,
            lease,
            chunk_index=0,
            seed=0,
            attempt_ordinal=0,
        )
        _complete_access(
            output,
            registration,
            identity,
            lease,
            chunk_index=0,
            seed=1,
            attempt_ordinal=0,
            status="infrastructure_interrupted",
        )
        marker = experiment.start_incomplete_chunk_resume(
            output,
            registration=registration,
            identity=identity,
            lease=lease,
        )
        assert marker == {
            "attempt_ordinal": 1,
            "chunk_index": 0,
            "event_index": 5,
            "kind": "resume_started",
            "mode": "replay_uncheckpointed_chunk",
            "schema_version": experiment.ACCESS_JOURNAL_SCHEMA_VERSION,
            "status": "resume_used",
        }
        restore = experiment.load_incomplete_chunk_resume_state(
            output, registration=registration, identity=identity
        )
        assert restore["restore_source"] == "bootstrap"
        assert restore["checkpoint_resource_use"] == {
            "charged_seconds": 0.0,
            "environment_accesses": 0,
            "optimizer_updates": 0,
            "retained_decisions": 0,
            "stored_bytes": 0,
            "uncompressed_bytes": 0,
        }
        assert restore["resource_use"]["environment_accesses"] == 2

        before_wrong_resume = journal_path.read_bytes()
        for chunk_index, seed in ((0, 1), (1, 0)):
            with pytest.raises(experiment.ExperimentBlocked, match="substitutes"):
                experiment.begin_environment_access(
                    output,
                    registration=registration,
                    identity=identity,
                    lease=lease,
                    chunk_index=chunk_index,
                    seed=seed,
                    attempt_ordinal=1,
                )
            assert journal_path.read_bytes() == before_wrong_resume

        _complete_chunk(
            output,
            registration,
            identity,
            lease,
            chunk_index=0,
            attempt_ordinal=1,
        )
        journal = experiment.load_access_journal(
            output, registration=registration, identity=identity
        )
        assert journal["resume_used"] is True
        assert journal["resume_complete"] is True
        assert journal["completed_chunk_indices"] == [0]
        assert journal["primary_next_position"] == 64

        _complete_access(
            output,
            registration,
            identity,
            lease,
            chunk_index=1,
            seed=64,
            attempt_ordinal=0,
            status="infrastructure_interrupted",
        )
        with pytest.raises(experiment.ExperimentBlocked, match="second resume"):
            experiment.start_incomplete_chunk_resume(
                output,
                registration=registration,
                identity=identity,
                lease=lease,
            )


def test_complete_primary_chunk_without_checkpoint_replays_same_chunk(
    source_inventory, tmp_path
):
    output = tmp_path / "execution"
    registration, _, _, _, identity = _authorized_output_values(
        source_inventory, output
    )

    with experiment.ExecutionLease(output, identity=identity) as lease:
        _initialize_lifecycle(output, registration, identity, lease)
        _complete_chunk(
            output,
            registration,
            identity,
            lease,
            chunk_index=0,
            attempt_ordinal=0,
        )
        marker = experiment.start_incomplete_chunk_resume(
            output,
            registration=registration,
            identity=identity,
            lease=lease,
        )
        assert marker["chunk_index"] == 0
        assert marker["mode"] == "replay_uncheckpointed_chunk"
        restore = experiment.load_incomplete_chunk_resume_state(
            output, registration=registration, identity=identity
        )
        assert restore["restore_source"] == "bootstrap"
        assert restore["resume_mode"] == "replay_uncheckpointed_chunk"

        first = registration["schedule"]["chunks"][0][0]
        _complete_access(
            output,
            registration,
            identity,
            lease,
            chunk_index=0,
            seed=first,
            attempt_ordinal=1,
        )
        with pytest.raises(experiment.ExperimentBlocked, match="replay.*incomplete"):
            experiment.publish_complete_chunk_checkpoint(
                output,
                registration=registration,
                identity=identity,
                lease=lease,
                chunk_index=0,
                resources=_checkpoint_resources(
                    output, identity, optimizer_updates=1
                ),
                runtime_checkpoint_payload={"model": "incomplete-replay"},
                chunk_evidence={"rows": 1, "tag": "incomplete-replay"},
            )


def test_checkpoint_boundary_resume_continues_next_primary_chunk(
    source_inventory, tmp_path
):
    output = tmp_path / "execution"
    registration, _, _, _, identity = _authorized_output_values(
        source_inventory, output
    )

    with experiment.ExecutionLease(output, identity=identity) as lease:
        _initialize_lifecycle(output, registration, identity, lease)
        _complete_chunk(
            output,
            registration,
            identity,
            lease,
            chunk_index=0,
            attempt_ordinal=0,
        )
        experiment.publish_complete_chunk_checkpoint(
            output,
            registration=registration,
            identity=identity,
            lease=lease,
            chunk_index=0,
            resources=_checkpoint_resources(output, identity, optimizer_updates=1),
            runtime_checkpoint_payload={"model": "after-chunk-0", "step": 1},
            chunk_evidence={"rows": 64, "tag": "chunk-0"},
        )

        marker = experiment.start_incomplete_chunk_resume(
            output,
            registration=registration,
            identity=identity,
            lease=lease,
        )
        assert marker["chunk_index"] == 1
        assert marker["mode"] == "continue_after_checkpoint"
        restore = experiment.load_incomplete_chunk_resume_state(
            output, registration=registration, identity=identity
        )
        assert restore["restore_source"] == "latest_complete_checkpoint"
        assert restore["restored_chunk_index"] == 0
        assert restore["resume_chunk_index"] == 1
        assert restore["resume_mode"] == "continue_after_checkpoint"

        first = registration["schedule"]["chunks"][1][0]
        _complete_access(
            output,
            registration,
            identity,
            lease,
            chunk_index=1,
            seed=first,
            attempt_ordinal=0,
        )
        with pytest.raises(experiment.ExperimentBlocked, match="second resume"):
            experiment.start_incomplete_chunk_resume(
                output,
                registration=registration,
                identity=identity,
                lease=lease,
            )


def test_checkpoint_chain_is_resource_first_and_resume_restores_latest_prefix(
    source_inventory, tmp_path, monkeypatch
):
    output = tmp_path / "execution"
    registration, _, _, _, identity = _authorized_output_values(
        source_inventory, output
    )

    with experiment.ExecutionLease(output, identity=identity) as lease:
        bootstrap = _initialize_lifecycle(output, registration, identity, lease)
        with pytest.raises(experiment.ExperimentBlocked, match="already exists"):
            experiment.publish_bootstrap(
                output,
                registration=registration,
                identity=identity,
                lease=lease,
                runtime_checkpoint_payload={"different": True},
            )

        _complete_chunk(
            output,
            registration,
            identity,
            lease,
            chunk_index=0,
            attempt_ordinal=0,
        )
        original_write_once = experiment._atomic_write_once
        checkpoint_writes = []

        def observe_resource_first(path, payload):
            if path.parent.name == "checkpoints":
                checkpoint_writes.append(path.name)
                ledger = experiment.load_resource_ledger(output, identity=identity)
                assert ledger["resources"]["optimizer_updates"] >= 1
            return original_write_once(path, payload)

        monkeypatch.setattr(experiment, "_atomic_write_once", observe_resource_first)
        first = experiment.publish_complete_chunk_checkpoint(
            output,
            registration=registration,
            identity=identity,
            lease=lease,
            chunk_index=0,
            resources=_checkpoint_resources(output, identity, optimizer_updates=1),
            runtime_checkpoint_payload={"model": "after-chunk-0", "step": 1},
            chunk_evidence={"rows": 64, "tag": "chunk-0"},
        )
        assert first["previous_checkpoint_sha256"] == bootstrap["bootstrap_sha256"]
        runtime_bytes = experiment.canonical_json_bytes(
            first["runtime_checkpoint"]["payload"]
        )
        assert first["runtime_checkpoint"]["sha256"] == hashlib.sha256(
            runtime_bytes
        ).hexdigest()
        assert first["runtime_checkpoint"]["size_bytes"] == len(runtime_bytes)
        first_evidence_path = output / first["chunk_evidence"]["path"]
        stored_evidence = first_evidence_path.read_bytes()
        uncompressed_evidence = gzip.decompress(stored_evidence)
        assert first["chunk_evidence"]["stored_sha256"] == hashlib.sha256(
            stored_evidence
        ).hexdigest()
        assert first["chunk_evidence"]["stored_size_bytes"] == len(stored_evidence)
        assert first["chunk_evidence"]["uncompressed_sha256"] == hashlib.sha256(
            uncompressed_evidence
        ).hexdigest()
        assert first["chunk_evidence"]["uncompressed_size_bytes"] == len(
            uncompressed_evidence
        )
        assert checkpoint_writes == [
            "chunk_0001_evidence.json.gz",
            "checkpoint_0001.json",
        ]

        ledger_path = output / experiment.RESOURCE_LEDGER_FILENAME
        ledger_bytes = ledger_path.read_bytes()
        ledger_events = [json.loads(line) for line in ledger_bytes.splitlines()]
        ledger_events[-1]["reason"] = "wrong-checkpoint-reason"
        ledger_path.write_bytes(
            b"".join(
                experiment.canonical_json_bytes(event) for event in ledger_events
            )
        )
        with pytest.raises(
            experiment.ExperimentBlocked, match="resource event reason mismatch"
        ):
            experiment.load_checkpoint_chain(
                output, registration=registration, identity=identity
            )
        ledger_path.write_bytes(ledger_bytes)

        _complete_access(
            output,
            registration,
            identity,
            lease,
            chunk_index=1,
            seed=64,
            attempt_ordinal=0,
            status="infrastructure_interrupted",
        )
        first_checkpoint_path = output / "checkpoints/checkpoint_0001.json"
        first_checkpoint_bytes = first_checkpoint_path.read_bytes()
        advanced_checkpoint = json.loads(first_checkpoint_bytes)
        advanced_checkpoint["access_journal_prefix"] = (
            experiment._journal_prefix_binding(output)
        )
        advanced_body = {
            key: value
            for key, value in advanced_checkpoint.items()
            if key != "checkpoint_sha256"
        }
        advanced_checkpoint["checkpoint_sha256"] = hashlib.sha256(
            experiment.canonical_json_bytes(advanced_body)
        ).hexdigest()
        first_checkpoint_path.write_bytes(
            experiment.canonical_json_bytes(advanced_checkpoint)
        )
        with pytest.raises(experiment.ExperimentBlocked, match="coordinate mismatch"):
            experiment.load_checkpoint_chain(
                output, registration=registration, identity=identity
            )
        first_checkpoint_path.write_bytes(first_checkpoint_bytes)

        experiment.start_incomplete_chunk_resume(
            output,
            registration=registration,
            identity=identity,
            lease=lease,
        )
        restore = experiment.load_incomplete_chunk_resume_state(
            output, registration=registration, identity=identity
        )
        assert restore["restore_source"] == "latest_complete_checkpoint"
        assert restore["restored_chunk_index"] == 0
        assert restore["runtime_checkpoint"]["payload"] == {
            "model": "after-chunk-0",
            "step": 1,
        }
        assert restore["resource_use"]["environment_accesses"] == 65
        assert restore["checkpoint_resource_use"]["environment_accesses"] == 64

        _complete_chunk(
            output,
            registration,
            identity,
            lease,
            chunk_index=1,
            attempt_ordinal=1,
        )
        second = experiment.publish_complete_chunk_checkpoint(
            output,
            registration=registration,
            identity=identity,
            lease=lease,
            chunk_index=1,
            resources=_checkpoint_resources(output, identity, optimizer_updates=2),
            runtime_checkpoint_payload={"model": "after-chunk-1", "step": 2},
            chunk_evidence={"rows": 64, "tag": "chunk-1-replay"},
        )
        chain = experiment.load_checkpoint_chain(
            output, registration=registration, identity=identity
        )
        assert len(chain) == 2
        assert second["previous_checkpoint_sha256"] == first["checkpoint_sha256"]
        assert second["resume_used"] is True
        assert chain[-1]["resource_use"]["environment_accesses"] == 129

        checkpoint_path = output / "checkpoints/checkpoint_0002.json"
        checkpoint_bytes = checkpoint_path.read_bytes()
        drifted_checkpoint = json.loads(checkpoint_bytes)
        drifted_checkpoint["resume_used"] = False
        checkpoint_body = {
            key: value
            for key, value in drifted_checkpoint.items()
            if key != "checkpoint_sha256"
        }
        drifted_checkpoint["checkpoint_sha256"] = hashlib.sha256(
            experiment.canonical_json_bytes(checkpoint_body)
        ).hexdigest()
        checkpoint_path.write_bytes(
            experiment.canonical_json_bytes(drifted_checkpoint)
        )
        with pytest.raises(
            experiment.ExperimentBlocked,
            match="access journal prefix is not complete",
        ):
            experiment.load_checkpoint_chain(
                output, registration=registration, identity=identity
            )
        checkpoint_path.write_bytes(checkpoint_bytes)

        evidence_path = output / "checkpoints/chunk_0002_evidence.json.gz"
        evidence_path.write_bytes(evidence_path.read_bytes() + b"drift")
        with pytest.raises(experiment.ExperimentBlocked, match="evidence bytes"):
            experiment.load_checkpoint_chain(
                output, registration=registration, identity=identity
            )


def test_evidence_only_checkpoint_publication_recovers_exact_envelope(
    source_inventory, tmp_path, monkeypatch
):
    output = tmp_path / "execution"
    registration, _, _, _, identity = _authorized_output_values(
        source_inventory, output
    )
    original_write_once = experiment._atomic_write_once

    with experiment.ExecutionLease(output, identity=identity) as lease:
        _initialize_lifecycle(output, registration, identity, lease)
        _complete_chunk(
            output,
            registration,
            identity,
            lease,
            chunk_index=0,
            attempt_ordinal=0,
        )

        def fail_checkpoint_envelope(path, payload):
            if path.name == "checkpoint_0001.json":
                raise OSError("synthetic checkpoint-envelope publication failure")
            return original_write_once(path, payload)

        monkeypatch.setattr(
            experiment, "_atomic_write_once", fail_checkpoint_envelope
        )
        with pytest.raises(OSError, match="checkpoint-envelope"):
            experiment.publish_complete_chunk_checkpoint(
                output,
                registration=registration,
                identity=identity,
                lease=lease,
                chunk_index=0,
                resources=_checkpoint_resources(
                    output, identity, optimizer_updates=1
                ),
                runtime_checkpoint_payload={"model": "recoverable", "step": 1},
                chunk_evidence={"rows": 64, "tag": "recoverable"},
            )
        assert (output / "checkpoints/chunk_0001_evidence.json.gz").is_file()
        assert not (output / "checkpoints/checkpoint_0001.json").exists()

    monkeypatch.setattr(experiment, "_atomic_write_once", original_write_once)
    classification = experiment.classify_output_root(
        output,
        registration=registration,
        identity=identity,
        owner_alive=lambda _pid: False,
    )
    assert classification["classification"] == "checkpoint_publication_recovery"
    with experiment.classified_execution_lease(
        output,
        registration=registration,
        identity=identity,
        owner_alive=lambda _pid: False,
    ) as lease:
        recovered = experiment.recover_checkpoint_publication(
            output,
            registration=registration,
            identity=identity,
            lease=lease,
        )
    assert recovered["chunk_index"] == 0
    assert recovered["runtime_checkpoint"]["payload"] == {
        "model": "recoverable",
        "step": 1,
    }
    assert len(
        experiment.load_checkpoint_chain(
            output, registration=registration, identity=identity
        )
    ) == 1


def test_exact_checkpoint_resources_reconciles_durable_access_journal(
    source_inventory, tmp_path
):
    output = tmp_path / "execution"
    registration, _, _, _, identity = _authorized_output_values(
        source_inventory, output
    )
    runtime = _SyntheticRuntimeModule()
    with experiment.ExecutionLease(output, identity=identity) as lease:
        _initialize_lifecycle(output, registration, identity, lease)
        _complete_chunk(
            output,
            registration,
            identity,
            lease,
            chunk_index=0,
            attempt_ordinal=0,
        )
        ledger_path = output / experiment.RESOURCE_LEDGER_FILENAME
        ledger_header = ledger_path.read_bytes().splitlines(keepends=True)[0]
        ledger_path.write_bytes(ledger_header)
        state = types.SimpleNamespace(
            completed_decisions=128,
            completed_episodes=64,
            next_chunk_index=1,
            optimizer_updates=1,
        )
        runtime_checkpoint = runtime.encode_runtime_checkpoint(state)
        evidence = runtime.build_chunk_evidence({"chunk_index": 0})
        resources = experiment._exact_checkpoint_resources(
            output,
            registration=registration,
            identity=identity,
            runtime_state=state,
            runtime_checkpoint_payload=runtime_checkpoint,
            chunk_evidence=evidence,
            chunk_index=0,
            charged_seconds=1.0,
        )
        assert resources["environment_accesses"] == 64
        experiment.publish_complete_chunk_checkpoint(
            output,
            registration=registration,
            identity=identity,
            lease=lease,
            chunk_index=0,
            resources=resources,
            runtime_checkpoint_payload=runtime_checkpoint,
            chunk_evidence=evidence,
        )


def test_output_root_classification_is_exact_and_owner_aware(
    source_inventory, tmp_path, monkeypatch
):
    prestart = tmp_path / "prestart"
    registration, _, _, _, identity = _authorized_output_values(
        source_inventory, prestart
    )

    wrong_output = tmp_path / "wrong-output"
    with pytest.raises(experiment.ExperimentBlocked, match="output root differs"):
        experiment.classify_output_root(
            wrong_output,
            registration=registration,
            identity=identity,
        )
    assert not wrong_output.exists()

    assert experiment.classify_output_root(
        prestart,
        registration=registration,
        identity=identity,
    )["classification"] == "absent_root_initial"

    with experiment.classified_execution_lease(
        prestart,
        registration=registration,
        identity=identity,
    ) as lease:
        assert lease.root_classification["classification"] == "absent_root_initial"
        _initialize_lifecycle(prestart, registration, identity, lease)

    original_inventory = experiment._output_relative_files

    def reject_active_inventory(_output):
        raise AssertionError("active output inventory must not be read")

    monkeypatch.setattr(
        experiment,
        "_output_relative_files",
        reject_active_inventory,
    )
    with pytest.raises(experiment.ExperimentBlocked, match="still alive"):
        experiment.classify_output_root(
            prestart,
            registration=registration,
            identity=identity,
            owner_alive=lambda _pid: True,
        )
    monkeypatch.setattr(
        experiment,
        "_output_relative_files",
        original_inventory,
    )
    classification = experiment.classify_output_root(
        prestart,
        registration=registration,
        identity=identity,
        owner_alive=lambda _pid: False,
    )
    assert classification["classification"] == "initialized_before_seed"
    assert classification["owner_dead"] is True

    with experiment.classified_execution_lease(
        prestart,
        registration=registration,
        identity=identity,
        owner_alive=lambda _pid: False,
    ) as lease:
        assert lease.root_classification["classification"] == (
            "initialized_before_seed"
        )

    (prestart / "unexpected.txt").write_text("drift", encoding="ascii")
    with pytest.raises(experiment.ExperimentBlocked, match="inventory mismatch"):
        experiment.classify_output_root(
            prestart,
            registration=registration,
            identity=identity,
            owner_alive=lambda _pid: False,
        )

    interrupted = tmp_path / "interrupted"
    interrupted_registration, _, _, _, interrupted_identity = (
        _authorized_output_values(source_inventory, interrupted)
    )
    with experiment.classified_execution_lease(
        interrupted,
        registration=interrupted_registration,
        identity=interrupted_identity,
    ) as lease:
        _initialize_lifecycle(
            interrupted,
            interrupted_registration,
            interrupted_identity,
            lease,
        )
        _complete_access(
            interrupted,
            interrupted_registration,
            interrupted_identity,
            lease,
            chunk_index=0,
            seed=0,
            attempt_ordinal=0,
            status="infrastructure_interrupted",
        )
    classification = experiment.classify_output_root(
        interrupted,
        registration=interrupted_registration,
        identity=interrupted_identity,
        owner_alive=lambda _pid: False,
    )
    assert classification["classification"] == "incomplete_chunk_resume"
    assert classification["resume_chunk_index"] == 0


def test_terminal_intent_and_manifest_last_keep_every_authority_false(
    source_inventory, tmp_path, monkeypatch
):
    output = tmp_path / "execution"
    registration, _, _, _, identity = _authorized_output_values(
        source_inventory, output
    )

    with experiment.ExecutionLease(output, identity=identity) as lease:
        _initialize_lifecycle(output, registration, identity, lease)
        with pytest.raises(experiment.ExperimentBlocked, match="eight complete"):
            experiment.publish_terminal_intent(
                output,
                registration=registration,
                identity=identity,
                lease=lease,
                verdict=(
                    "experiment_completed_with_cross_fitted_mechanism_evidence"
                ),
                details={},
            )

        original_write_once = experiment._atomic_write_once
        publication_order = []

        def record_publication(path, payload):
            publication_order.append(path.name)
            return original_write_once(path, payload)

        monkeypatch.setattr(experiment, "_atomic_write_once", record_publication)
        intent = experiment.publish_terminal_intent(
            output,
            registration=registration,
            identity=identity,
            lease=lease,
            verdict="experiment_blocked_before_seed_access",
            details={"reason": "synthetic source-only prestart block"},
        )
        bundle = experiment.publish_terminal_bundle(
            output,
            registration=registration,
            identity=identity,
            lease=lease,
        )
        assert publication_order == [
            experiment.TERMINAL_INTENT_FILENAME,
            experiment.TERMINAL_FILENAME,
            experiment.MANIFEST_FILENAME,
        ]
        assert intent["authority"] == experiment.registration_authority()
        assert set(bundle["terminal"]["authority"].values()) == {False}
        assert set(bundle["manifest"]["authority"].values()) == {False}
        paths = {
            row["path"]
            for row in bundle["manifest"]["artifact_inventory"]["artifacts"]
        }
        assert experiment.TERMINAL_INTENT_FILENAME in paths
        assert experiment.TERMINAL_FILENAME in paths
        assert experiment.MANIFEST_FILENAME not in paths
        assert experiment.LEASE_FILENAME not in paths
        assert experiment.validate_terminal_bundle(
            output, registration=registration, identity=identity
        ) == bundle

    assert experiment.terminal_verdicts() == (
        "experiment_blocked_before_seed_access",
        "experiment_completed_with_cross_fitted_mechanism_evidence",
        "experiment_failed_after_seed_access",
        "experiment_stopped_during_training_for_family_saturation",
    )


def test_same_process_terminal_publication_reuses_validated_context_and_intent(
    source_inventory, tmp_path, monkeypatch
):
    output = tmp_path / "execution"
    registration, _, _, _, identity = _authorized_output_values(
        source_inventory, output
    )
    original_validate = experiment.validate_registration
    calls = 0

    def counted_validate(value):
        nonlocal calls
        calls += 1
        return original_validate(value)

    monkeypatch.setattr(experiment, "validate_registration", counted_validate)
    context = experiment._build_validated_execution_context(
        registration, identity, output
    )

    with experiment.ExecutionLease(output, identity=identity) as lease:
        _initialize_lifecycle(output, context, identity, lease)
        intent = experiment.publish_terminal_intent(
            output,
            registration=context,
            identity=identity,
            lease=lease,
            verdict="experiment_blocked_before_seed_access",
            details={"reason": "synthetic source-only prestart block"},
        )

        def fail_reopen(*_args, **_kwargs):
            raise AssertionError("same-process closeout must not reopen intent")

        monkeypatch.setattr(experiment, "load_terminal_intent", fail_reopen)
        bundle = experiment.publish_terminal_bundle(
            output,
            registration=context,
            identity=identity,
            lease=lease,
            terminal_intent=intent,
        )

    assert bundle["terminal"]["terminal_intent_sha256"] == intent[
        "terminal_intent_sha256"
    ]
    assert bundle["manifest"]["terminal_sha256"] == bundle["terminal"][
        "terminal_sha256"
    ]
    assert calls == 1


def test_saturation_terminal_requires_the_exact_checkpoint_boundary():
    journal = {
        "completed_chunk_indices": list(range(4)),
        "debited_accesses": 257,
        "pending_access": None,
        "primary_next_position": 257,
        "resume_candidate_chunk_index": 4,
        "resume_complete": False,
        "resume_failed": False,
        "resume_used": False,
        "terminal_access_failure": False,
    }

    with pytest.raises(experiment.ExperimentBlocked, match="checkpoint boundary"):
        experiment._validate_terminal_state(
            "experiment_stopped_during_training_for_family_saturation",
            journal=journal,
            ledger={"resources": experiment._zero_resources()},
            chain=[{} for _chunk_index in range(4)],
        )


@pytest.mark.parametrize("terminal_written", [False, True])
def test_partial_terminal_publication_reopens_only_for_exact_closeout(
    source_inventory, tmp_path, monkeypatch, terminal_written
):
    output = tmp_path / "execution"
    registration, _, _, _, identity = _authorized_output_values(
        source_inventory, output
    )
    original_write_once = experiment._atomic_write_once
    with experiment.ExecutionLease(output, identity=identity) as lease:
        _initialize_lifecycle(output, registration, identity, lease)
        experiment.publish_terminal_intent(
            output,
            registration=registration,
            identity=identity,
            lease=lease,
            verdict="experiment_blocked_before_seed_access",
            details={"reason": "synthetic prestart closeout"},
        )
        if terminal_written:

            def fail_manifest(path, payload):
                if path.name == experiment.MANIFEST_FILENAME:
                    raise OSError("synthetic manifest publication failure")
                return original_write_once(path, payload)

            monkeypatch.setattr(experiment, "_atomic_write_once", fail_manifest)
            with pytest.raises(OSError, match="manifest publication"):
                experiment.publish_terminal_bundle(
                    output,
                    registration=registration,
                    identity=identity,
                    lease=lease,
                )

    monkeypatch.setattr(experiment, "_atomic_write_once", original_write_once)
    classification = experiment.classify_output_root(
        output,
        registration=registration,
        identity=identity,
        owner_alive=lambda _pid: False,
    )
    assert classification["classification"] == "terminal_publication_recovery"
    with experiment.classified_execution_lease(
        output,
        registration=registration,
        identity=identity,
        owner_alive=lambda _pid: False,
    ) as lease:
        bundle = experiment.publish_terminal_bundle(
            output,
            registration=registration,
            identity=identity,
            lease=lease,
        )
    assert bundle == experiment.validate_terminal_bundle(
        output, registration=registration, identity=identity
    )


def test_artifact_inventory_rejects_per_file_and_total_byte_overflow():
    oversized = 64 * 1024 * 1024 + 1
    row = {
        "encoding": "identity-bytes-v1",
        "path": "oversized.bin",
        "stored_sha256": "a" * 64,
        "stored_size_bytes": oversized,
        "uncompressed_sha256": "a" * 64,
        "uncompressed_size_bytes": oversized,
    }
    with pytest.raises(experiment.ExperimentBlocked, match="artifact exceeds"):
        experiment.validate_artifact_inventory(
            {
                "artifacts": [row],
                "stored_size_bytes": oversized,
                "uncompressed_size_bytes": oversized,
            }
        )

    rows = []
    for index in range(4):
        rows.append(
            {
                **row,
                "path": f"part-{index}.bin",
                "stored_size_bytes": 64 * 1024 * 1024,
                "uncompressed_size_bytes": 64 * 1024 * 1024,
            }
        )
    with pytest.raises(experiment.ExperimentBlocked, match="stored-byte ceiling"):
        experiment.validate_artifact_inventory(
            {
                "artifacts": rows,
                "stored_size_bytes": 256 * 1024 * 1024,
                "uncompressed_size_bytes": 256 * 1024 * 1024,
            }
        )


def test_exact_runner_executes_only_registered_training_and_closes_terminal_bundle(
    source_inventory, tmp_path, monkeypatch
):
    output = tmp_path / "execution"
    registration, request, approval, authorization, identity = (
        _authorized_output_values(source_inventory, output)
    )
    runtime = _SyntheticRuntimeModule()

    def load_dependencies_with_lease(*_args, **_kwargs):
        lease_key = os.path.normcase(
            str((output / experiment.LEASE_FILENAME).resolve())
        )
        assert lease_key in experiment._ACTIVE_EXECUTION_LEASES
        return _synthetic_loaded_dependencies(runtime)

    monkeypatch.setattr(
        experiment,
        "_load_registered_dependencies",
        load_dependencies_with_lease,
        raising=False,
    )
    resources = {
        "charged_seconds": 0.0,
        "environment_accesses": 0,
        "optimizer_updates": 0,
        "retained_decisions": 0,
        "stored_bytes": 0,
        "uncompressed_bytes": 0,
    }
    pending = {"value": False}
    checkpoints = []

    def begin_environment_access(*_args, **_kwargs):
        assert pending["value"] is False
        pending["value"] = True
        resources["environment_accesses"] += 1
        return {"status": "debited"}

    def complete_environment_access(*_args, **_kwargs):
        assert pending["value"] is True
        pending["value"] = False
        return {"status": "completed"}

    def exact_resources(*_args, runtime_state, **_kwargs):
        resources["optimizer_updates"] = runtime_state.optimizer_updates
        resources["retained_decisions"] = runtime_state.completed_decisions
        return copy.deepcopy(resources)

    def publish_checkpoint(*_args, chunk_index, resources: dict, **_kwargs):
        checkpoints.append((chunk_index, copy.deepcopy(resources)))
        return {"chunk_index": chunk_index}

    def close_terminal(
        _output,
        *,
        identity,
        verdict,
        saturation,
        failure,
        preflight,
        **_kwargs,
    ):
        assert failure is None
        return {
            "identity": copy.deepcopy(identity),
            "manifest": {"synthetic": True},
            "preflight": copy.deepcopy(preflight),
            "status": "terminal",
            "terminal": {
                "checkpoint_count": len(checkpoints),
                "completed_chunk_indices": [index for index, _ in checkpoints],
                "details": {
                    "evaluation": None,
                    "failure": None,
                    "saturation": copy.deepcopy(saturation),
                },
                "resource_use": copy.deepcopy(resources),
                "verdict": verdict,
            },
        }

    for name, replacement in {
        "begin_environment_access": begin_environment_access,
        "complete_environment_access": complete_environment_access,
        "initialize_access_journal": lambda *_args, **_kwargs: None,
        "initialize_resource_ledger": lambda *_args, **_kwargs: None,
        "publish_bootstrap": lambda *_args, **_kwargs: None,
        "load_resource_ledger": lambda *_args, **_kwargs: {
            "resources": copy.deepcopy(resources)
        },
        "_load_completed_chunk_evidence": lambda *_args, **_kwargs: [],
            "_exact_checkpoint_resources": exact_resources,
            "_charge_attempt_elapsed": lambda *_args, **_kwargs: {
                "resources": copy.deepcopy(resources)
            },
            "publish_complete_chunk_checkpoint": publish_checkpoint,
        "_close_runner_terminal": close_terminal,
    }.items():
        monkeypatch.setattr(experiment, name, replacement)

    result = experiment.execute_authorized_experiment(
        registration,
        request,
        authorization,
        approval,
        repo_root=ROOT,
        **_preflight_injections(source_inventory, registration),
    )

    assert result["status"] == "terminal"
    assert result["terminal"]["verdict"] == (
        "experiment_completed_with_cross_fitted_mechanism_evidence"
    )
    assert runtime.accessed_seeds == registration["schedule"]["seeds"]
    assert result["terminal"]["checkpoint_count"] == 8
    assert result["terminal"]["completed_chunk_indices"] == list(range(8))
    assert result["terminal"]["resource_use"]["environment_accesses"] == 512
    assert result["terminal"]["resource_use"]["optimizer_updates"] == 8
    assert result["terminal"]["resource_use"]["retained_decisions"] == 1024
    assert result["terminal"]["details"]["evaluation"] is None
    assert result["terminal"]["details"]["saturation"]["stop"] is False
    assert result["identity"] == identity

    expected_static = {
        experiment.REGISTRATION_FILENAME,
        experiment.EXECUTION_REQUEST_FILENAME,
        experiment.EXTERNAL_APPROVAL_FILENAME,
        experiment.AUTHORIZATION_FILENAME,
        experiment.SOURCE_PREFLIGHT_FILENAME,
        experiment.PRE_ISOLATION_FILENAME,
        experiment.POST_ISOLATION_FILENAME,
    }
    assert expected_static <= {path.name for path in output.iterdir()}
    assert [index for index, _resources in checkpoints] == list(range(8))


@pytest.mark.parametrize("drift", ["unexpected", "missing-static"])
def test_exact_runner_rejects_ambiguous_stale_root_before_loading_dependencies(
    source_inventory, tmp_path, monkeypatch, drift
):
    output = tmp_path / "execution"
    registration, request, approval, authorization, _identity = (
        _authorized_output_values(source_inventory, output)
    )
    interrupted_runtime = _SyntheticInterruptedRuntimeModule()
    monkeypatch.setattr(
        experiment,
        "_load_registered_dependencies",
        lambda *_args, **_kwargs: _synthetic_loaded_dependencies(
            interrupted_runtime
        ),
    )
    first = experiment.execute_authorized_experiment(
        registration,
        request,
        authorization,
        approval,
        repo_root=ROOT,
        **_preflight_injections(source_inventory, registration),
    )
    assert first["status"] == "infrastructure_interrupted"

    if drift == "unexpected":
        (output / "unexpected.txt").write_text("drift", encoding="ascii")
    else:
        (output / experiment.SOURCE_PREFLIGHT_FILENAME).unlink()

    def fail_if_dependencies_load(*_args, **_kwargs):
        raise AssertionError("ambiguous output must fail before dependency loading")

    monkeypatch.setattr(
        experiment,
        "_load_registered_dependencies",
        fail_if_dependencies_load,
    )
    with pytest.raises(experiment.ExperimentBlocked, match="inventory|missing"):
        experiment.execute_authorized_experiment(
            registration,
            request,
            authorization,
            approval,
            repo_root=ROOT,
            owner_alive=lambda _pid: False,
            **_preflight_injections(source_inventory, registration),
        )


def test_exact_runner_reopens_zero_debit_boundary_without_consuming_resume(
    source_inventory, tmp_path, monkeypatch
):
    output = tmp_path / "execution"
    registration, request, approval, authorization, identity = (
        _authorized_output_values(source_inventory, output)
    )
    monkeypatch.setattr(
        experiment,
        "_load_registered_dependencies",
        lambda *_args, **_kwargs: _synthetic_loaded_dependencies(
            _SyntheticPreAccessInterruptedRuntimeModule()
        ),
    )
    first = experiment.execute_authorized_experiment(
        registration,
        request,
        authorization,
        approval,
        repo_root=ROOT,
        **_preflight_injections(source_inventory, registration),
    )
    assert first["status"] == "infrastructure_interrupted"
    assert experiment.load_access_journal(
        output, registration=registration, identity=identity
    )["debited_accesses"] == 0

    monkeypatch.setattr(
        experiment,
        "_load_registered_dependencies",
        lambda *_args, **_kwargs: _synthetic_loaded_dependencies(
            _SyntheticInterruptedRuntimeModule()
        ),
    )
    second = experiment.execute_authorized_experiment(
        registration,
        request,
        authorization,
        approval,
        repo_root=ROOT,
        owner_alive=lambda _pid: False,
        **_preflight_injections(source_inventory, registration),
    )
    assert second["status"] == "infrastructure_interrupted"
    journal = experiment.load_access_journal(
        output, registration=registration, identity=identity
    )
    assert journal["debited_accesses"] == 1
    assert journal["resume_used"] is False


def test_exact_runner_reopens_source_bound_setup_after_dependency_failure(
    source_inventory, tmp_path, monkeypatch
):
    output = tmp_path / "execution"
    registration, request, approval, authorization, identity = (
        _authorized_output_values(source_inventory, output)
    )

    def fail_dependency_loading(*_args, **_kwargs):
        raise OSError("synthetic native dependency load failure")

    monkeypatch.setattr(
        experiment,
        "_load_registered_dependencies",
        fail_dependency_loading,
    )
    with pytest.raises(OSError, match="dependency load"):
        experiment.execute_authorized_experiment(
            registration,
            request,
            authorization,
            approval,
            repo_root=ROOT,
            **_preflight_injections(source_inventory, registration),
        )
    assert {path.name for path in output.iterdir()} == {
        experiment.LEASE_FILENAME,
        experiment.REGISTRATION_FILENAME,
        experiment.EXECUTION_REQUEST_FILENAME,
        experiment.EXTERNAL_APPROVAL_FILENAME,
        experiment.AUTHORIZATION_FILENAME,
        experiment.SOURCE_PREFLIGHT_FILENAME,
        experiment.PRE_ISOLATION_FILENAME,
    }

    monkeypatch.setattr(
        experiment,
        "_load_registered_dependencies",
        lambda *_args, **_kwargs: _synthetic_loaded_dependencies(
            _SyntheticInterruptedRuntimeModule()
        ),
    )
    resumed = experiment.execute_authorized_experiment(
        registration,
        request,
        authorization,
        approval,
        repo_root=ROOT,
        owner_alive=lambda _pid: False,
        **_preflight_injections(source_inventory, registration),
    )
    assert resumed["status"] == "infrastructure_interrupted"
    journal = experiment.load_access_journal(
        output, registration=registration, identity=identity
    )
    assert journal["debited_accesses"] == 1
    assert journal["resume_used"] is False


@pytest.mark.parametrize("drift", ["tampered", "missing", "unexpected"])
def test_exact_runner_rejects_ambiguous_source_bound_setup(
    source_inventory, tmp_path, monkeypatch, drift
):
    output = tmp_path / "execution"
    registration, request, approval, authorization, _identity = (
        _authorized_output_values(source_inventory, output)
    )

    monkeypatch.setattr(
        experiment,
        "_load_registered_dependencies",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            OSError("synthetic native dependency load failure")
        ),
    )
    with pytest.raises(OSError, match="dependency load"):
        experiment.execute_authorized_experiment(
            registration,
            request,
            authorization,
            approval,
            repo_root=ROOT,
            **_preflight_injections(source_inventory, registration),
        )

    if drift == "tampered":
        (output / experiment.SOURCE_PREFLIGHT_FILENAME).write_text(
            "{}\n", encoding="ascii"
        )
    elif drift == "missing":
        (output / experiment.SOURCE_PREFLIGHT_FILENAME).unlink()
    else:
        (output / "unexpected.txt").write_text("drift", encoding="ascii")

    def fail_if_dependencies_load(*_args, **_kwargs):
        raise AssertionError("ambiguous setup must fail before dependency loading")

    monkeypatch.setattr(
        experiment,
        "_load_registered_dependencies",
        fail_if_dependencies_load,
    )
    with pytest.raises(
        experiment.ExperimentBlocked,
        match="identity|missing|inventory|controls",
    ):
        experiment.execute_authorized_experiment(
            registration,
            request,
            authorization,
            approval,
            repo_root=ROOT,
            owner_alive=lambda _pid: False,
            **_preflight_injections(source_inventory, registration),
        )


def test_infrastructure_interruption_charges_time_and_terminalizes_failed_resume(
    source_inventory, tmp_path, monkeypatch
):
    output = tmp_path / "execution"
    registration, request, approval, authorization, identity = (
        _authorized_output_values(source_inventory, output)
    )
    clock = _ControlledClock(100.0)
    first_runtime = _SyntheticTimedInterruptedRuntimeModule(elapsed=12.0)
    monkeypatch.setattr(
        experiment,
        "_load_registered_dependencies",
        lambda *_args, **_kwargs: _synthetic_loaded_dependencies(first_runtime),
    )
    first = experiment.execute_authorized_experiment(
        registration,
        request,
        authorization,
        approval,
        repo_root=ROOT,
        clock=clock,
        **_preflight_injections(source_inventory, registration),
    )
    assert first["status"] == "infrastructure_interrupted"
    first_resources = experiment.load_resource_ledger(
        output, identity=identity
    )["resources"]
    assert first_resources["charged_seconds"] == 12.0
    assert first_resources["environment_accesses"] == 1

    clock.value = 200.0
    resumed_runtime = _SyntheticTimedInterruptedRuntimeModule(
        elapsed=0.0, access_seed=False
    )
    monkeypatch.setattr(
        experiment,
        "_load_registered_dependencies",
        lambda *_args, **_kwargs: _synthetic_loaded_dependencies(resumed_runtime),
    )
    second = experiment.execute_authorized_experiment(
        registration,
        request,
        authorization,
        approval,
        repo_root=ROOT,
        clock=clock,
        owner_alive=lambda _pid: False,
        **_preflight_injections(source_inventory, registration),
    )
    assert second["status"] == "terminal"
    assert second["terminal"]["verdict"] == "experiment_failed_after_seed_access"
    assert second["terminal"]["details"]["failure"]["infrastructure"] is True
    assert resumed_runtime.observed_deadline == (
        200.0
        + registration["contract"]["limits"]["max_charged_seconds"]
        - 12.0
    )
    journal = experiment.load_access_journal(
        output, registration=registration, identity=identity
    )
    assert journal["resume_used"] is True
    assert journal["resume_complete"] is False
    second_ledger = experiment.load_resource_ledger(output, identity=identity)
    assert second_ledger["resources"]["charged_seconds"] == 12.0
    assert second_ledger["events"][-1]["reason"] == "terminal-attempt-charge"


@pytest.mark.parametrize(
    ("elapsed", "expected_charge", "failure_message"),
    [
        (7.5, 7.5, "synthetic algorithm failure"),
        (
            14_405.0,
            14_400.0,
            "wall-time limit reached before environment construction",
        ),
    ],
)
def test_noninfrastructure_failure_charges_elapsed_before_first_checkpoint(
    source_inventory,
    tmp_path,
    monkeypatch,
    elapsed,
    expected_charge,
    failure_message,
):
    output = tmp_path / "execution"
    registration, request, approval, authorization, identity = (
        _authorized_output_values(source_inventory, output)
    )
    clock = _ControlledClock(100.0)
    runtime = _SyntheticTimedFailingRuntimeModule(
        elapsed=elapsed, message=failure_message
    )
    monkeypatch.setattr(
        experiment,
        "_load_registered_dependencies",
        lambda *_args, **_kwargs: _synthetic_loaded_dependencies(runtime),
    )

    result = experiment.execute_authorized_experiment(
        registration,
        request,
        authorization,
        approval,
        repo_root=ROOT,
        clock=clock,
        **_preflight_injections(source_inventory, registration),
    )

    assert result["status"] == "terminal"
    assert result["terminal"]["verdict"] == "experiment_failed_after_seed_access"
    assert result["terminal"]["details"]["failure"]["message"] == failure_message
    assert result["terminal"]["resource_use"]["charged_seconds"] == (
        expected_charge
    )
    ledger = experiment.load_resource_ledger(output, identity=identity)
    assert ledger["resources"]["charged_seconds"] == expected_charge
    assert ledger["events"][-1]["reason"] == "terminal-attempt-charge"


def test_terminal_attempt_charge_is_idempotent_at_the_same_clock(
    source_inventory, tmp_path
):
    output = tmp_path / "execution"
    registration, _, _, _, identity = _authorized_output_values(
        source_inventory, output
    )
    context = experiment._build_validated_execution_context(
        registration, identity, output
    )
    clock = _ControlledClock(110.0)

    with experiment.ExecutionLease(output, identity=identity) as lease:
        _initialize_lifecycle(output, context, identity, lease)
        _complete_access(
            output,
            context,
            identity,
            lease,
            chunk_index=0,
            seed=registration["schedule"]["chunks"][0][0],
            attempt_ordinal=0,
        )
        first = experiment._charge_attempt_elapsed(
            output,
            registration=context,
            identity=identity,
            lease=lease,
            attempt_started=100.0,
            charged_origin=0.0,
            clock=clock,
            reason="terminal-attempt-charge",
        )
        first_bytes = (output / experiment.RESOURCE_LEDGER_FILENAME).read_bytes()
        second = experiment._charge_attempt_elapsed(
            output,
            registration=context,
            identity=identity,
            lease=lease,
            attempt_started=100.0,
            charged_origin=0.0,
            clock=clock,
            reason="terminal-attempt-charge",
        )

    assert first["resources"]["charged_seconds"] == 10.0
    assert first["events"][-1]["reason"] == "terminal-attempt-charge"
    assert second == first
    assert (output / experiment.RESOURCE_LEDGER_FILENAME).read_bytes() == first_bytes


@pytest.mark.parametrize("post_written", [False, True])
def test_exact_runner_closes_eight_checkpoint_stale_boundary_without_seed_access(
    source_inventory, tmp_path, monkeypatch, post_written
):
    output = tmp_path / "execution"
    registration, request, approval, authorization, identity = (
        _authorized_output_values(source_inventory, output)
    )
    injections = _preflight_injections(source_inventory, registration)
    preflight = experiment.source_only_preflight(
        ROOT,
        registration,
        request,
        authorization,
        approval,
        **injections,
    )
    pre_isolation = experiment._observe_isolation(
        registration,
        phase="pre",
        external_binding_observer=injections["external_binding_observer"],
        checkpoint_snapshot_observer=injections[
            "checkpoint_snapshot_observer"
        ],
    )
    documents = experiment._static_execution_documents(
        registration=registration,
        request=request,
        approval=approval,
        authorization=authorization,
        preflight=preflight,
        pre_isolation=pre_isolation,
    )
    runtime = _SyntheticRuntimeModule()
    with experiment.ExecutionLease(output, identity=identity) as lease:
        for filename, value in documents:
            experiment._publish_or_validate_document(
                output, filename, value, allow_existing=False
            )
        _initialize_lifecycle(output, registration, identity, lease)
        for chunk_index in range(experiment.CHUNK_COUNT):
            _complete_chunk(
                output,
                registration,
                identity,
                lease,
                chunk_index=chunk_index,
                attempt_ordinal=0,
            )
            state = types.SimpleNamespace(
                completed_decisions=(chunk_index + 1) * 128,
                completed_episodes=(chunk_index + 1) * 64,
                next_chunk_index=chunk_index + 1,
                optimizer_updates=chunk_index + 1,
            )
            experiment.publish_complete_chunk_checkpoint(
                output,
                registration=registration,
                identity=identity,
                lease=lease,
                chunk_index=chunk_index,
                resources=_checkpoint_resources(
                    output,
                    identity,
                    optimizer_updates=chunk_index + 1,
                ),
                runtime_checkpoint_payload=runtime.encode_runtime_checkpoint(state),
                chunk_evidence=runtime.build_chunk_evidence(
                    {"chunk_index": chunk_index}
                ),
            )
        if post_written:
            experiment._publish_post_isolation(
                output,
                registration=registration,
                external_binding_observer=injections[
                    "external_binding_observer"
                ],
                checkpoint_snapshot_observer=injections[
                    "checkpoint_snapshot_observer"
                ],
            )

    monkeypatch.setattr(
        experiment,
        "_load_registered_dependencies",
        lambda *_args, **_kwargs: _synthetic_loaded_dependencies(runtime),
    )
    result = experiment.execute_authorized_experiment(
        registration,
        request,
        authorization,
        approval,
        repo_root=ROOT,
        owner_alive=lambda _pid: False,
        **injections,
    )
    assert result["status"] == "terminal"
    assert result["terminal"]["checkpoint_count"] == experiment.CHUNK_COUNT
    assert result["terminal"]["verdict"] == (
        "experiment_completed_with_cross_fitted_mechanism_evidence"
    )
    assert runtime.accessed_seeds == []


def test_exact_runner_finishes_partial_terminal_before_dependency_loading(
    source_inventory, tmp_path, monkeypatch
):
    output = tmp_path / "execution"
    registration, request, approval, authorization, _identity = (
        _authorized_output_values(source_inventory, output)
    )
    runtime = _SyntheticPreAccessFailingRuntimeModule()
    monkeypatch.setattr(
        experiment,
        "_load_registered_dependencies",
        lambda *_args, **_kwargs: _synthetic_loaded_dependencies(runtime),
    )
    original_write_once = experiment._atomic_write_once

    def fail_manifest(path, payload):
        if path.name == experiment.MANIFEST_FILENAME:
            raise OSError("synthetic runner manifest publication failure")
        return original_write_once(path, payload)

    monkeypatch.setattr(experiment, "_atomic_write_once", fail_manifest)
    with pytest.raises(OSError, match="runner manifest publication"):
        experiment.execute_authorized_experiment(
            registration,
            request,
            authorization,
            approval,
            repo_root=ROOT,
            **_preflight_injections(source_inventory, registration),
        )

    monkeypatch.setattr(experiment, "_atomic_write_once", original_write_once)

    def fail_if_dependencies_load(*_args, **_kwargs):
        raise AssertionError("terminal closeout must not load dependencies")

    monkeypatch.setattr(
        experiment,
        "_load_registered_dependencies",
        fail_if_dependencies_load,
    )
    result = experiment.execute_authorized_experiment(
        registration,
        request,
        authorization,
        approval,
        repo_root=ROOT,
        owner_alive=lambda _pid: False,
        **_preflight_injections(source_inventory, registration),
    )
    assert result["status"] == "terminal"
    assert result["terminal"]["verdict"] == (
        "experiment_blocked_before_seed_access"
    )


def test_algorithm_failure_preserves_unverified_root_when_post_isolation_drifts(
    source_inventory, tmp_path, monkeypatch
):
    output = tmp_path / "execution"
    registration, request, approval, authorization, _identity = (
        _authorized_output_values(source_inventory, output)
    )
    monkeypatch.setattr(
        experiment,
        "_load_registered_dependencies",
        lambda *_args, **_kwargs: _synthetic_loaded_dependencies(
            _SyntheticFailingRuntimeModule()
        ),
    )
    def publish_drifted_post(
        output_path,
        *,
        registration,
        external_binding_observer,
        checkpoint_snapshot_observer,
    ):
        del external_binding_observer, checkpoint_snapshot_observer
        observation = {
            "isolation_identity": copy.deepcopy(registration["isolation_identity"]),
            "matches_registration": False,
            "phase": "post",
            "registration_sha256": experiment.registration_sha256(registration),
            "schema_version": experiment.ISOLATION_OBSERVATION_SCHEMA_VERSION,
        }
        experiment._publish_or_validate_document(
            Path(output_path),
            experiment.POST_ISOLATION_FILENAME,
            observation,
            allow_existing=False,
        )
        return observation

    monkeypatch.setattr(
        experiment,
        "_publish_post_isolation",
        publish_drifted_post,
    )
    result = experiment.execute_authorized_experiment(
        registration,
        request,
        authorization,
        approval,
        repo_root=ROOT,
        **_preflight_injections(source_inventory, registration),
    )
    failure = json.loads((output / experiment.FAILURE_FILENAME).read_text())

    assert result["status"] == "post_isolation_mismatch"
    assert failure["message"] == "synthetic algorithm failure"
    assert json.loads(
        (output / experiment.POST_ISOLATION_FILENAME).read_text()
    )["matches_registration"] is False
    assert not (output / experiment.TERMINAL_INTENT_FILENAME).exists()
    assert not (output / experiment.TERMINAL_FILENAME).exists()
    assert not (output / experiment.MANIFEST_FILENAME).exists()
