from __future__ import annotations

import argparse
import configparser
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence


_REQUIRED_PROFILES = (
    "commit",
    "protocol",
    "gameplay",
    "noncombat-evidence",
    "full",
)
_DOMAIN_PROFILES = ("protocol", "gameplay", "noncombat-evidence")
_DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_MANIFEST_PATH = _DEFAULT_REPO_ROOT / "tests" / "test_gate_manifest.json"


class ManifestError(ValueError):
    """Raised when the test gate manifest is not safe to execute."""


@dataclass(frozen=True)
class FullOnlyTarget:
    path: str
    reason: str


@dataclass(frozen=True)
class TestProfile:
    description: str
    mode: str
    targets: tuple[str, ...]


@dataclass(frozen=True)
class TestGateManifest:
    schema_version: int
    full_only: tuple[FullOnlyTarget, ...]
    profiles: dict[str, TestProfile]


TestProfile.__test__ = False
TestGateManifest.__test__ = False


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ManifestError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _configured_test_paths(repo_root: Path) -> tuple[Path, ...]:
    config_path = repo_root / "pytest.ini"
    parser = configparser.ConfigParser()
    try:
        read_paths = parser.read(config_path, encoding="utf-8")
        if read_paths and parser.has_option("pytest", "testpaths"):
            configured_paths = parser.get("pytest", "testpaths").split()
    except (UnicodeDecodeError, configparser.Error) as error:
        raise ManifestError(f"unable to read pytest.ini: {config_path}") from error
    if not read_paths:
        raise ManifestError(f"pytest configuration does not exist: {config_path}")
    if not parser.has_option("pytest", "testpaths"):
        raise ManifestError("pytest.ini must configure testpaths")

    if not configured_paths:
        raise ManifestError("pytest.ini testpaths must not be empty")

    resolved_paths: list[Path] = []
    resolved_root = repo_root.resolve()
    for configured_path in configured_paths:
        candidate = (resolved_root / configured_path).resolve()
        if not candidate.is_relative_to(resolved_root):
            raise ManifestError(f"pytest test path escapes repository: {configured_path}")
        if not candidate.exists():
            raise ManifestError(f"configured test path does not exist: {configured_path}")
        resolved_paths.append(candidate)
    return tuple(resolved_paths)


def _target_file(target: str) -> str:
    return target.split("::", 1)[0]


def _is_under_test_paths(path: Path, test_paths: tuple[Path, ...]) -> bool:
    for test_path in test_paths:
        if test_path.is_file() and path == test_path:
            return True
        if test_path.is_dir() and path.is_relative_to(test_path):
            return True
    return False


def _require_mapping(value: object, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ManifestError(f"{context} must be an object")
    return value


def _require_exact_keys(value: dict[str, Any], expected: set[str], context: str) -> None:
    unknown_keys = set(value) - expected
    if unknown_keys:
        raise ManifestError(f"unknown {context} key: {sorted(unknown_keys)[0]}")
    missing_keys = expected - set(value)
    if missing_keys:
        raise ManifestError(f"missing {context} key: {sorted(missing_keys)[0]}")


def _require_non_blank_string(value: object, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ManifestError(f"{context} must not be blank")
    return value


def _resolve_target_file(
    target: str, repo_root: Path, test_paths: tuple[Path, ...]
) -> Path:
    target_file = _target_file(target)
    if not target_file:
        raise ManifestError("target file must not be blank")

    resolved_root = repo_root.resolve()
    resolved_path = (resolved_root / target_file).resolve()
    if not resolved_path.is_relative_to(resolved_root):
        raise ManifestError(f"target escapes repository: {target}")
    if not resolved_path.is_file():
        raise ManifestError(f"target file does not exist: {target_file}")
    if not _is_under_test_paths(resolved_path, test_paths):
        raise ManifestError(f"target is outside configured test paths: {target}")
    return resolved_path


def _parse_full_only(
    value: object, repo_root: Path, test_paths: tuple[Path, ...]
) -> tuple[FullOnlyTarget, ...]:
    if not isinstance(value, list):
        raise ManifestError("full_only must be a list")

    parsed_targets: list[FullOnlyTarget] = []
    paths: set[str] = set()
    for index, entry in enumerate(value):
        target = _require_mapping(entry, f"full_only[{index}]")
        _require_exact_keys(target, {"path", "reason"}, f"full_only[{index}]")
        path = _require_non_blank_string(target["path"], f"full_only[{index}].path")
        reason = _require_non_blank_string(target["reason"], "reason")
        if "::" in path:
            raise ManifestError("full_only path must not contain a node ID")
        if path in paths:
            raise ManifestError(f"duplicate target: {path}")
        paths.add(path)
        _resolve_target_file(path, repo_root, test_paths)
        parsed_targets.append(FullOnlyTarget(path=path, reason=reason))
    return tuple(parsed_targets)


def _parse_profile(
    name: str,
    value: object,
    repo_root: Path,
    test_paths: tuple[Path, ...],
) -> TestProfile:
    profile = _require_mapping(value, f"profile {name}")
    _require_exact_keys(profile, {"description", "mode", "targets"}, "profile")
    description = _require_non_blank_string(profile["description"], "description")
    mode = _require_non_blank_string(profile["mode"], "mode")
    targets = profile["targets"]
    if not isinstance(targets, list):
        raise ManifestError(f"profile {name} targets must be a list")

    expected_mode = (
        "default-minus-full-only"
        if name == "commit"
        else "default"
        if name == "full"
        else "targets"
    )
    if mode != expected_mode:
        raise ManifestError(f"profile {name} mode must be {expected_mode}")
    if name in _DOMAIN_PROFILES and not targets:
        raise ManifestError(f"profile {name} requires at least one target")
    if name in {"commit", "full"} and targets:
        raise ManifestError(f"profile {name} must not define targets")

    parsed_targets: list[str] = []
    seen_targets: set[str] = set()
    for index, target in enumerate(targets):
        target = _require_non_blank_string(target, f"profile {name} targets[{index}]")
        if target in seen_targets:
            raise ManifestError(f"duplicate target: {target}")
        seen_targets.add(target)
        _resolve_target_file(target, repo_root, test_paths)
        parsed_targets.append(target)
    return TestProfile(description=description, mode=mode, targets=tuple(parsed_targets))


def load_manifest(path: Path, repo_root: Path) -> TestGateManifest:
    try:
        raw_manifest = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except UnicodeDecodeError as error:
        raise ManifestError(f"manifest is not valid UTF-8: {path}") from error
    except (OSError, json.JSONDecodeError) as error:
        raise ManifestError(f"unable to read manifest: {path}") from error

    manifest = _require_mapping(raw_manifest, "manifest")
    _require_exact_keys(manifest, {"schema_version", "full_only", "profiles"}, "top-level")
    schema_version = manifest["schema_version"]
    if type(schema_version) is not int or schema_version != 1:
        raise ManifestError(f"unsupported schema version: {schema_version!r}")

    test_paths = _configured_test_paths(repo_root)
    full_only = _parse_full_only(manifest["full_only"], repo_root, test_paths)
    profiles = _require_mapping(manifest["profiles"], "profiles")
    unknown_profiles = set(profiles) - set(_REQUIRED_PROFILES)
    if unknown_profiles:
        raise ManifestError(f"unknown profile: {sorted(unknown_profiles)[0]}")
    missing_profiles = set(_REQUIRED_PROFILES) - set(profiles)
    if missing_profiles:
        raise ManifestError(f"missing required profile: {sorted(missing_profiles)[0]}")

    return TestGateManifest(
        schema_version=schema_version,
        full_only=full_only,
        profiles={
            name: _parse_profile(name, profiles[name], repo_root, test_paths)
            for name in _REQUIRED_PROFILES
        },
    )


def _repository_relative_argument(value: str, repo_root: Path) -> str:
    target_file, separator, node_id = value.partition("::")
    relative_file = (repo_root / target_file).resolve().relative_to(repo_root.resolve())
    argument = relative_file.as_posix()
    return f"{argument}{separator}{node_id}" if separator else argument


def build_pytest_command(
    profile_name: str,
    manifest: TestGateManifest,
    repo_root: Path,
    basetemp_root: Path,
) -> list[str]:
    profile = manifest.profiles[profile_name]
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
        "--basetemp",
        str(basetemp_root / profile_name),
    ]
    if profile.mode == "default-minus-full-only":
        command.extend(
            f"--ignore={_repository_relative_argument(target.path, repo_root)}"
            for target in manifest.full_only
        )
    elif profile.mode == "targets":
        command.extend(
            _repository_relative_argument(target, repo_root) for target in profile.targets
        )
    return command


def _configuration_error(error: ManifestError) -> int:
    print(f"test gate configuration error: {error}", file=sys.stderr)
    return 2


def run_profile(
    profile_name: str,
    manifest_path: Path,
    repo_root: Path,
    dry_run: bool = False,
    executor: Callable[..., subprocess.CompletedProcess[Any]] = subprocess.run,
    clock: Callable[[], float] = time.perf_counter,
) -> int:
    try:
        manifest = load_manifest(manifest_path, repo_root)
    except ManifestError as error:
        return _configuration_error(error)

    command = build_pytest_command(
        profile_name, manifest, repo_root, repo_root / ".pytest_gates"
    )
    if dry_run:
        print(f"dry-run: {subprocess.list2cmdline(command)}")
        return 0

    started_at = clock()
    result = executor(command, cwd=repo_root, check=False)
    elapsed = clock() - started_at
    print(f"test gate {profile_name}: {elapsed:.2f}s (exit code {result.returncode})")
    return result.returncode


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a validated pytest gate profile.")
    parser.add_argument("profile", nargs="?", default="commit", choices=_REQUIRED_PROFILES)
    parser.add_argument("--list", action="store_true", help="list available profiles")
    parser.add_argument(
        "--dry-run", action="store_true", help="print the pytest command without running it"
    )
    arguments = parser.parse_args(argv)

    if arguments.list:
        try:
            manifest = load_manifest(_DEFAULT_MANIFEST_PATH, _DEFAULT_REPO_ROOT)
        except ManifestError as error:
            return _configuration_error(error)
        for name in _REQUIRED_PROFILES:
            print(f"{name}: {manifest.profiles[name].description}")
        return 0

    return run_profile(
        arguments.profile,
        _DEFAULT_MANIFEST_PATH,
        _DEFAULT_REPO_ROOT,
        dry_run=arguments.dry_run,
    )


if __name__ == "__main__":
    raise SystemExit(main())
