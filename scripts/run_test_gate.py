from __future__ import annotations

import argparse
import configparser
import json
import math
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence
from uuid import uuid4


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
_TIMING_REPORT_SCHEMA_VERSION = 1
_TIMING_SLOW_TEST_LIMIT = 100


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
    basetemp: Path,
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
        str(basetemp),
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


def _unique_basetemp_path(profile_name: str, repo_root: Path) -> Path:
    return repo_root.resolve() / ".pytest_gates" / f"{profile_name}-{uuid4().hex}"


def _configuration_error(error: ManifestError) -> int:
    print(f"test gate configuration error: {error}", file=sys.stderr)
    return 2


def _resolve_timing_report_path(value: Path, repo_root: Path) -> Path:
    resolved_root = repo_root.resolve()
    candidate = value if value.is_absolute() else resolved_root / value
    resolved = candidate.resolve()
    if not resolved.is_relative_to(resolved_root):
        raise ManifestError(f"timing report escapes repository: {value}")
    if resolved.exists():
        raise ManifestError(f"timing report already exists: {resolved}")
    return resolved


def _timing_junit_path(basetemp: Path) -> Path:
    return basetemp.parent / f"{basetemp.name}.junit.xml"


def _with_timing_options(command: list[str], junit_path: Path) -> list[str]:
    return [
        *command,
        "--junitxml",
        str(junit_path),
        "-o",
        "junit_family=legacy",
    ]


def _xml_local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _declared_test_count(root: ET.Element) -> int:
    root_name = _xml_local_name(root.tag)
    suites = (
        [root]
        if root_name == "testsuite"
        else [
            child
            for child in root
            if _xml_local_name(child.tag) == "testsuite"
        ]
        if root_name == "testsuites"
        else []
    )
    if not suites:
        raise ManifestError("timing JUnit has no test suite")
    try:
        counts = [int(suite.attrib["tests"]) for suite in suites]
    except (KeyError, TypeError, ValueError) as error:
        raise ManifestError("timing JUnit test count is invalid") from error
    if any(count < 0 for count in counts):
        raise ManifestError("timing JUnit test count is invalid")
    return sum(counts)


def _testcase_outcome(testcase: ET.Element) -> str:
    child_names = {_xml_local_name(child.tag) for child in testcase}
    if "error" in child_names:
        return "error"
    if "failure" in child_names:
        return "failed"
    if "skipped" in child_names:
        return "skipped"
    return "passed"


def _normalized_test_file(raw_file: object, repo_root: Path) -> str:
    if not isinstance(raw_file, str) or not raw_file.strip():
        raise ManifestError("timing JUnit testcase file is missing")
    normalized_input = raw_file.replace("\\", "/")
    relative = Path(normalized_input)
    resolved_root = repo_root.resolve()
    resolved = (resolved_root / relative).resolve()
    if relative.is_absolute() or not resolved.is_relative_to(resolved_root):
        raise ManifestError(f"timing JUnit testcase escapes repository: {raw_file}")
    if not resolved.is_file():
        raise ManifestError(f"timing JUnit testcase file does not exist: {raw_file}")
    return resolved.relative_to(resolved_root).as_posix()


def _parse_test_duration(raw_duration: object) -> float:
    try:
        duration = float(raw_duration)
    except (TypeError, ValueError) as error:
        raise ManifestError("timing JUnit testcase duration is invalid") from error
    if not math.isfinite(duration) or duration < 0:
        raise ManifestError("timing JUnit testcase duration is invalid")
    return round(duration, 6)


def _build_timing_report(
    *,
    junit_path: Path,
    profile_name: str,
    pytest_exit_code: int,
    elapsed_seconds: float,
    repo_root: Path,
) -> dict[str, Any]:
    try:
        root = ET.parse(junit_path).getroot()
    except (OSError, ET.ParseError) as error:
        raise ManifestError(f"unable to read timing JUnit: {junit_path}") from error

    testcases = [
        element
        for element in root.iter()
        if _xml_local_name(element.tag) == "testcase"
    ]
    declared_count = _declared_test_count(root)
    if declared_count != len(testcases):
        raise ManifestError(
            "timing JUnit testcase count mismatch: "
            f"declared {declared_count}, observed {len(testcases)}"
        )

    outcome_counts = {name: 0 for name in ("error", "failed", "passed", "skipped")}
    file_rows: dict[str, dict[str, Any]] = {}
    test_rows = []
    for testcase in testcases:
        file_name = _normalized_test_file(testcase.attrib.get("file"), repo_root)
        name = testcase.attrib.get("name")
        classname = testcase.attrib.get("classname")
        if not isinstance(name, str) or not name or not isinstance(classname, str):
            raise ManifestError("timing JUnit testcase identity is incomplete")
        duration = _parse_test_duration(testcase.attrib.get("time"))
        outcome = _testcase_outcome(testcase)
        outcome_counts[outcome] += 1
        test_rows.append(
            {
                "classname": classname,
                "duration_seconds": duration,
                "file": file_name,
                "name": name,
                "outcome": outcome,
            }
        )
        file_row = file_rows.setdefault(
            file_name,
            {
                "duration_seconds": 0.0,
                "file": file_name,
                "outcome_counts": {
                    key: 0 for key in ("error", "failed", "passed", "skipped")
                },
                "test_count": 0,
            },
        )
        file_row["duration_seconds"] += duration
        file_row["outcome_counts"][outcome] += 1
        file_row["test_count"] += 1

    per_file = list(file_rows.values())
    for file_row in per_file:
        file_row["duration_seconds"] = round(file_row["duration_seconds"], 6)
    per_file.sort(key=lambda row: (-row["duration_seconds"], row["file"]))
    test_rows.sort(
        key=lambda row: (
            -row["duration_seconds"],
            row["file"],
            row["classname"],
            row["name"],
        )
    )
    return {
        "outcome_counts": outcome_counts,
        "per_file": per_file,
        "profile": profile_name,
        "pytest_exit_code": pytest_exit_code,
        "runner_elapsed_seconds": round(elapsed_seconds, 6),
        "schema_version": _TIMING_REPORT_SCHEMA_VERSION,
        "slow_tests": test_rows[:_TIMING_SLOW_TEST_LIMIT],
        "test_count": len(test_rows),
    }


def _publish_timing_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    try:
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
    except OSError as error:
        raise ManifestError(f"unable to publish timing report: {path}") from error


def run_profile(
    profile_name: str,
    manifest_path: Path,
    repo_root: Path,
    dry_run: bool = False,
    timing_report: Path | None = None,
    executor: Callable[..., subprocess.CompletedProcess[Any]] = subprocess.run,
    clock: Callable[[], float] = time.perf_counter,
) -> int:
    try:
        manifest = load_manifest(manifest_path, repo_root)
    except ManifestError as error:
        return _configuration_error(error)

    try:
        resolved_timing_report = (
            _resolve_timing_report_path(timing_report, repo_root)
            if timing_report is not None
            else None
        )
    except ManifestError as error:
        return _configuration_error(error)

    basetemp = _unique_basetemp_path(profile_name, repo_root)
    command = build_pytest_command(profile_name, manifest, repo_root, basetemp)
    junit_path = None
    if resolved_timing_report is not None:
        junit_path = _timing_junit_path(basetemp)
        command = _with_timing_options(command, junit_path)
    mode = "dry-run" if dry_run else "run"
    print(f"test gate {mode} profile: {profile_name}", flush=True)
    print(f"pytest command: {subprocess.list2cmdline(command)}", flush=True)
    if dry_run:
        return 0

    basetemp.parent.mkdir(parents=True, exist_ok=True)
    started_at = clock()
    result = executor(command, cwd=repo_root, check=False)
    elapsed = clock() - started_at
    print(f"test gate {profile_name}: {elapsed:.2f}s (exit code {result.returncode})")
    if resolved_timing_report is not None and junit_path is not None:
        try:
            timing_payload = _build_timing_report(
                junit_path=junit_path,
                profile_name=profile_name,
                pytest_exit_code=result.returncode,
                elapsed_seconds=elapsed,
                repo_root=repo_root,
            )
            _publish_timing_report(resolved_timing_report, timing_payload)
        except ManifestError as error:
            _configuration_error(error)
            return result.returncode if result.returncode != 0 else 2
        print(f"timing report: {resolved_timing_report}")
    return result.returncode


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a validated pytest gate profile.")
    parser.add_argument("profile", nargs="?", default="commit", choices=_REQUIRED_PROFILES)
    parser.add_argument("--list", action="store_true", help="list available profiles")
    parser.add_argument(
        "--dry-run", action="store_true", help="print the pytest command without running it"
    )
    parser.add_argument(
        "--timing-report",
        type=Path,
        help="write deterministic JUnit-derived timing evidence to a new repo path",
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
        timing_report=arguments.timing_report,
    )


if __name__ == "__main__":
    raise SystemExit(main())
