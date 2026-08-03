"""Validate, execute, or verify the bounded simulator-only RL experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path, PurePosixPath
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from analysis_scripts import noncombat_simulator_rl_experiment as experiment
from analysis_scripts.noncombat_simulator_adapter import (
    NativeSimulatorEnvironment,
    hash_compiled_simulator_sources,
    load_native_module,
    sha256_file,
    validate_provenance,
)


ADAPTER_SOURCE_FILES = (
    "analysis_scripts/noncombat_simulator_adapter.py",
    "simulator_adapters/sts_lightspeed/noncombat_adapter.cpp",
)


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise experiment.ExperimentBlocked(
            f"git {' '.join(args)} failed: {completed.stderr.strip()}"
        )
    return completed.stdout.strip()


def _git_bytes(repo: Path, *args: str) -> bytes:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise experiment.ExperimentBlocked(
            f"git {' '.join(args)} failed: {completed.stderr.decode('utf-8', errors='replace').strip()}"
        )
    return completed.stdout


def _hash_named_bytes(rows: Sequence[tuple[str, bytes]]) -> str:
    digest = hashlib.sha256()
    for name, payload in sorted(rows):
        encoded = name.encode("utf-8")
        digest.update(len(encoded).to_bytes(4, "big"))
        digest.update(encoded)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


def _git_source_hash(repo: Path, commit: str, source_files: Sequence[str]) -> str:
    return _hash_named_bytes(
        [
            (relative, _git_bytes(repo, "show", f"{commit}:{relative}"))
            for relative in source_files
        ]
    )


def _working_source_hash(repo: Path, source_files: Sequence[str]) -> str:
    return _hash_named_bytes(
        [(relative, (repo / PurePosixPath(relative)).read_bytes()) for relative in source_files]
    )


def _load_controls(
    registration_path: Path, authorization_path: Path
) -> tuple[dict[str, Any], bytes, dict[str, Any], bytes]:
    registration_bytes = registration_path.read_bytes()
    authorization_bytes = authorization_path.read_bytes()
    registration = experiment.validate_registration(
        experiment.load_canonical_json_bytes(registration_bytes, "registration")
    )
    authorization = experiment.validate_execution_authorization(
        experiment.load_canonical_json_bytes(authorization_bytes, "authorization"),
        registration=registration,
        registration_bytes=registration_bytes,
    )
    return registration, registration_bytes, authorization, authorization_bytes


def validate_controls(
    registration_path: Path, authorization_path: Path
) -> dict[str, Any]:
    registration, registration_bytes, authorization, authorization_bytes = _load_controls(
        registration_path, authorization_path
    )
    return {
        "authorization_sha256": hashlib.sha256(authorization_bytes).hexdigest(),
        "execution_authorized": authorization["authority"]["experiment_execution"],
        "formal_readiness_verdict": experiment.FORMAL_READINESS_VERDICT,
        "logical_execution_id": authorization["logical_execution_id"],
        "registration_sha256": hashlib.sha256(registration_bytes).hexdigest(),
        "source_commit": registration["identity"]["implementation"]["commit"],
        "validated": True,
    }


def _verify_binding(repo: Path, binding: dict[str, Any], label: str) -> None:
    actual = experiment.file_binding(repo, binding["path"])
    if actual != binding:
        raise experiment.ExperimentBlocked(f"{label} binding mismatch")


def _repo_relative_path(repo: Path, path: Path, label: str) -> str:
    try:
        relative = path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError as exc:
        raise experiment.ExperimentBlocked(f"{label} is outside the repository") from exc
    if not relative or relative.startswith("../"):
        raise experiment.ExperimentBlocked(f"{label} is not repository-relative")
    return relative


def source_only_preflight(
    *,
    repo_root: Path,
    registration_path: Path,
    authorization_path: Path,
    output_dir: Path,
    simulator_repo: Path,
    module_path: Path,
) -> dict[str, Any]:
    """Check every identity available before native loading or environment use."""
    repo = repo_root.resolve()
    registration, registration_bytes, authorization, authorization_bytes = _load_controls(
        registration_path.resolve(), authorization_path.resolve()
    )
    expected_output = repo / PurePosixPath(authorization["output_directory"])
    if output_dir.resolve() != expected_output.resolve():
        raise experiment.ExperimentBlocked("authorized output path mismatch")
    authorization_relative = _repo_relative_path(
        repo, authorization_path, "authorization path"
    )
    if not (
        authorization_relative.startswith(experiment.OUTPUT_ROOT_PREFIX)
        and authorization_relative.endswith("_authorization.json")
    ):
        raise experiment.ExperimentBlocked("authorization path is outside the contract")
    committed_authorization = _git_bytes(
        repo, "show", f"origin/master:{authorization_relative}"
    )
    if committed_authorization != authorization_bytes:
        raise experiment.ExperimentBlocked("pushed authorization bytes mismatch")
    identity = registration["identity"]
    implementation = identity["implementation"]
    source_commit = implementation["commit"]
    _git(repo, "cat-file", "-e", f"{source_commit}^{{commit}}")
    _git(repo, "merge-base", "--is-ancestor", source_commit, "origin/master")
    source_files = implementation["source_files"]
    git_hash = _git_source_hash(repo, source_commit, source_files)
    working_hash = _working_source_hash(repo, source_files)
    if git_hash != implementation["source_sha256"] or working_hash != git_hash:
        raise experiment.ExperimentBlocked("implementation source identity mismatch")

    registration_binding = authorization["registration"]
    registration_commit = registration_binding["commit"]
    _git(repo, "cat-file", "-e", f"{registration_commit}^{{commit}}")
    _git(repo, "merge-base", "--is-ancestor", registration_commit, "origin/master")
    expected_registration_path = repo / PurePosixPath(registration_binding["path"])
    if registration_path.resolve() != expected_registration_path.resolve():
        raise experiment.ExperimentBlocked("authorization registration path mismatch")
    committed_registration = _git_bytes(
        repo, "show", f"{registration_commit}:{registration_binding['path']}"
    )
    if committed_registration != registration_bytes:
        raise experiment.ExperimentBlocked("pushed registration bytes mismatch")

    for name, binding in identity["evidence"].items():
        _verify_binding(repo, binding, f"evidence.{name}")
    _verify_binding(repo, identity["seed_inventory"], "seed_inventory")

    runtime = identity["runtime"]
    executable = Path(sys.executable).resolve().as_posix()
    if executable.casefold() != str(runtime["executable"]).casefold():
        raise experiment.ExperimentBlocked("runtime executable mismatch")
    if sys.platform != runtime["platform"]:
        raise experiment.ExperimentBlocked("runtime platform mismatch")
    if platform.python_version() != runtime["python_version"]:
        raise experiment.ExperimentBlocked("runtime Python version mismatch")
    torch_version = str(experiment._torch_module().__version__)
    if torch_version != runtime["torch_version"]:
        raise experiment.ExperimentBlocked("runtime PyTorch version mismatch")

    provenance = identity["adapter_provenance"]
    if module_path.resolve().stat().st_size != provenance["module_size_bytes"]:
        raise experiment.ExperimentBlocked("native module size mismatch")
    if sha256_file(module_path) != provenance["module_sha256"]:
        raise experiment.ExperimentBlocked("native module hash mismatch")
    simulator_source_sha256, simulator_source_count = hash_compiled_simulator_sources(
        simulator_repo
    )
    if simulator_source_sha256 != provenance["simulator_source_sha256"]:
        raise experiment.ExperimentBlocked("physical simulator source hash mismatch")
    if simulator_source_count != provenance["simulator_source_file_count"]:
        raise experiment.ExperimentBlocked("physical simulator source count mismatch")
    if _git(simulator_repo, "rev-parse", "HEAD") != provenance["simulator_commit"]:
        raise experiment.ExperimentBlocked("simulator commit mismatch")
    simulator_dirty = bool(_git(simulator_repo, "status", "--porcelain=v1"))
    if simulator_dirty != provenance["simulator_dirty"]:
        raise experiment.ExperimentBlocked("simulator dirty-state mismatch")
    for name, commit in provenance["submodules"].items():
        if _git(simulator_repo / name, "rev-parse", "HEAD") != commit:
            raise experiment.ExperimentBlocked(f"simulator submodule mismatch: {name}")
    adapter_source_hash = _git_source_hash(repo, source_commit, ADAPTER_SOURCE_FILES)
    if adapter_source_hash != provenance["adapter_source_sha256"]:
        raise experiment.ExperimentBlocked("adapter source hash mismatch")
    if provenance["adapter_commit"] != source_commit:
        raise experiment.ExperimentBlocked("adapter source commit mismatch")

    if output_dir.exists():
        persisted = experiment._load_control_files(output_dir)
        if persisted[1] != registration_bytes or persisted[3] != authorization_bytes:
            raise experiment.ExperimentBlocked("resume control bytes mismatch")
        output_state = "resume"
    else:
        output_state = "absent"
    return {
        "adapter_source_sha256": adapter_source_hash,
        "authorization_sha256": hashlib.sha256(authorization_bytes).hexdigest(),
        "formal_readiness_verdict": experiment.FORMAL_READINESS_VERDICT,
        "module_sha256": provenance["module_sha256"],
        "output_state": output_state,
        "registration_sha256": hashlib.sha256(registration_bytes).hexdigest(),
        "simulator_source_sha256": simulator_source_sha256,
        "source_commit": source_commit,
        "source_only_preflight": True,
    }


def _native_provenance_after_load(
    *,
    registration: dict[str, Any],
    native_module: Any,
) -> dict[str, Any]:
    expected = registration["identity"]["adapter_provenance"]
    build = json.loads(native_module.build_info_json())
    build["python"] = platform.python_version()
    actual = dict(expected)
    actual["build"] = build
    return validate_provenance(actual)


def _verify_terminal_with_fresh_process(repo_root: Path, output_dir: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(repo_root / "analysis_scripts" / "verify_noncombat_simulator_rl_experiment.py"),
            str(output_dir),
        ],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=300,
    )
    if completed.returncode != 0:
        raise experiment.ExperimentBlocked(
            f"standalone terminal verification failed: {completed.stderr.strip()}"
        )


def _charge_failed_operation(
    runtime: experiment.TrainingRuntime, started: float | None
) -> None:
    if started is None:
        return
    elapsed = max(0.0, time.perf_counter() - started)
    runtime.cumulative_wall_seconds = min(
        experiment.MAX_WALL_SECONDS,
        runtime.cumulative_wall_seconds + elapsed,
    )


def execute_authorized_experiment(args: argparse.Namespace) -> dict[str, Any]:
    """Execute or resume the one registered logical experiment."""
    repo = args.repo_root.resolve()
    preflight = source_only_preflight(
        repo_root=repo,
        registration_path=args.registration,
        authorization_path=args.authorization,
        output_dir=args.output_dir,
        simulator_repo=args.simulator_repo,
        module_path=args.module,
    )
    registration, registration_bytes, authorization, authorization_bytes = _load_controls(
        args.registration.resolve(), args.authorization.resolve()
    )
    registration_sha256 = hashlib.sha256(registration_bytes).hexdigest()
    implementation_commit = registration["identity"]["implementation"]["commit"]
    execution_id = authorization["logical_execution_id"]
    if not args.output_dir.exists():
        experiment.initialize_experiment_output(
            args.output_dir,
            registration_bytes=registration_bytes,
            authorization_bytes=authorization_bytes,
        )

    with experiment.ExecutionLease.acquire(args.output_dir, execution_id) as lease:
        if (args.output_dir / "pending_chunk.json").exists():
            experiment.recover_pending_training_chunk(
                args.output_dir,
                registration_sha256=registration_sha256,
                implementation_commit=implementation_commit,
                logical_execution_id=execution_id,
            )
        runtime = experiment.resume_training_runtime_from_output(
            args.output_dir,
            registration_sha256=registration_sha256,
            implementation_commit=implementation_commit,
            logical_execution_id=execution_id,
            active_lease=lease,
        )
        active_operation_started: float | None = None
        try:
            active_operation_started = time.perf_counter()
            native_module = load_native_module(
                args.module, dll_directories=args.dll_directory
            )
            actual_provenance = _native_provenance_after_load(
                registration=registration, native_module=native_module
            )
            if actual_provenance != registration["identity"]["adapter_provenance"]:
                raise experiment.ExperimentBlocked("loaded native build identity mismatch")
            active_operation_started = None

            def environment_factory(seed: int) -> NativeSimulatorEnvironment:
                return NativeSimulatorEnvironment(
                    native_module.Environment(seed, 0), actual_provenance
                )

            while runtime.next_chunk_index < experiment.TRAINING_CHUNKS:
                active_operation_started = time.perf_counter()
                summary = experiment.run_registered_training_chunk(
                    runtime, environment_factory=environment_factory
                )
                active_operation_started = None
                envelope = experiment.persist_completed_training_chunk(
                    args.output_dir,
                    runtime,
                    summary,
                    registration_sha256=registration_sha256,
                    implementation_commit=implementation_commit,
                    logical_execution_id=execution_id,
                )
                if runtime.next_chunk_index == 2 and not (
                    args.output_dir / "prefix_replay.json"
                ).exists():
                    active_operation_started = time.perf_counter()
                    experiment.verify_checkpoint_prefix_replay(
                        envelope, environment_factory=environment_factory
                    )
                    replay_elapsed = time.perf_counter() - active_operation_started
                    active_operation_started = None
                    runtime.cumulative_wall_seconds += replay_elapsed
                    if runtime.cumulative_wall_seconds > experiment.MAX_WALL_SECONDS:
                        runtime.cumulative_wall_seconds = experiment.MAX_WALL_SECONDS
                        raise experiment.ExperimentBlocked(
                            "cumulative wall-time bound exceeded during prefix replay"
                        )
                    experiment.publish_prefix_replay_result(
                        args.output_dir,
                        envelope,
                        replay_wall_seconds=replay_elapsed,
                        cumulative_wall_seconds=runtime.cumulative_wall_seconds,
                    )
            experiment.validate_prefix_replay_result(args.output_dir)

            initial_model = experiment.initialize_training_runtime().model
            active_operation_started = time.perf_counter()
            remaining = experiment.MAX_WALL_SECONDS - runtime.cumulative_wall_seconds
            if remaining <= 0.0:
                raise experiment.ExperimentBlocked(
                    "cumulative wall-time bound exhausted before evaluation"
                )
            evaluation = experiment.run_conditional_evaluation(
                initial_model,
                runtime.model,
                environment_factory=environment_factory,
                deadline=active_operation_started + remaining,
            )
            evaluation_elapsed = time.perf_counter() - active_operation_started
            active_operation_started = None
            runtime.cumulative_wall_seconds += evaluation_elapsed
            if runtime.cumulative_wall_seconds > experiment.MAX_WALL_SECONDS:
                runtime.cumulative_wall_seconds = experiment.MAX_WALL_SECONDS
                raise experiment.ExperimentBlocked(
                    "cumulative wall-time bound exceeded during evaluation"
                )
        except Exception as exc:
            if (args.output_dir / "pending_chunk.json").exists():
                raise
            _charge_failed_operation(runtime, active_operation_started)
            prefix_replay_verified = False
            if (args.output_dir / "prefix_replay.json").exists():
                experiment.validate_prefix_replay_result(args.output_dir)
                prefix_replay_verified = True
            manifest = experiment.publish_terminal_artifacts(
                args.output_dir,
                runtime=runtime,
                blocked_reason=f"{type(exc).__name__}: {exc}",
                prefix_replay_verified=prefix_replay_verified,
            )
        else:
            manifest = experiment.publish_terminal_artifacts(
                args.output_dir,
                runtime=runtime,
                evaluation=evaluation,
                prefix_replay_verified=True,
            )
    _verify_terminal_with_fresh_process(repo, args.output_dir)
    return {"manifest": manifest, "preflight": preflight}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    controls = subparsers.add_parser("validate-controls")
    controls.add_argument("--registration", type=Path, required=True)
    controls.add_argument("--authorization", type=Path, required=True)

    preflight = subparsers.add_parser("preflight")
    execute = subparsers.add_parser("execute")
    for command in (preflight, execute):
        command.add_argument("--repo-root", type=Path, required=True)
        command.add_argument("--registration", type=Path, required=True)
        command.add_argument("--authorization", type=Path, required=True)
        command.add_argument("--output-dir", type=Path, required=True)
        command.add_argument("--simulator-repo", type=Path, required=True)
        command.add_argument("--module", type=Path, required=True)
    execute.add_argument("--dll-directory", type=Path, action="append", default=[])

    verify = subparsers.add_parser("verify")
    verify.add_argument("--repo-root", type=Path, required=True)
    verify.add_argument("--output-dir", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "validate-controls":
            result = validate_controls(args.registration, args.authorization)
        elif args.command == "preflight":
            result = source_only_preflight(
                repo_root=args.repo_root,
                registration_path=args.registration,
                authorization_path=args.authorization,
                output_dir=args.output_dir,
                simulator_repo=args.simulator_repo,
                module_path=args.module,
            )
        elif args.command == "execute":
            result = execute_authorized_experiment(args)
        else:
            _verify_terminal_with_fresh_process(
                args.repo_root.resolve(), args.output_dir.resolve()
            )
            result = {"verification": "verified"}
    except (OSError, ValueError, experiment.ExperimentBlocked) as exc:
        print(json.dumps({"error": str(exc), "status": "blocked"}, sort_keys=True), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    if (
        args.command == "execute"
        and result.get("manifest", {}).get("verdict") == "experiment_blocked"
    ):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
