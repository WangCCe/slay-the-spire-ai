from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

import scripts.run_test_gate as test_gate_runner
from scripts.run_test_gate import (
    FullOnlyTarget,
    ManifestError,
    TestGateManifest,
    TestProfile,
    _configured_test_paths,
    load_manifest,
)


VALID_MANIFEST = {
    "schema_version": 1,
    "full_only": [
        {"path": "tests/test_slow.py", "reason": "measured subprocess replay"}
    ],
    "profiles": {
        "commit": {
            "description": "routine pre-commit validation",
            "mode": "default-minus-full-only",
            "targets": [],
        },
        "protocol": {
            "description": "communication protocol validation",
            "mode": "targets",
            "targets": ["tests/test_fast.py::test_fast"],
        },
        "gameplay": {
            "description": "gameplay policy validation",
            "mode": "targets",
            "targets": ["tests/test_fast.py"],
        },
        "noncombat-evidence": {
            "description": "non-combat evidence validation",
            "mode": "targets",
            "targets": ["tests/test_fast.py"],
        },
        "full": {
            "description": "complete repository validation",
            "mode": "default",
            "targets": [],
        },
    },
}
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def temporary_repo(tmp_path: Path) -> Path:
    (tmp_path / "pytest.ini").write_text("[pytest]\ntestpaths = tests\n", encoding="utf-8")
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_fast.py").write_text("def test_fast():\n    pass\n", encoding="utf-8")
    (tests_dir / "test_slow.py").write_text("def test_slow():\n    pass\n", encoding="utf-8")
    (tmp_path / "outside_test.py").write_text("def test_outside():\n    pass\n", encoding="utf-8")
    return tmp_path


def _write_manifest(repo_root: Path, manifest: object) -> Path:
    path = repo_root / "test_gate_manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def test_load_manifest_returns_typed_validated_contract(temporary_repo: Path) -> None:
    manifest = load_manifest(_write_manifest(temporary_repo, VALID_MANIFEST), temporary_repo)

    assert manifest == TestGateManifest(
        schema_version=1,
        full_only=(
            FullOnlyTarget(
                path="tests/test_slow.py", reason="measured subprocess replay"
            ),
        ),
        profiles={
            "commit": TestProfile(
                description="routine pre-commit validation",
                mode="default-minus-full-only",
                targets=(),
            ),
            "protocol": TestProfile(
                description="communication protocol validation",
                mode="targets",
                targets=("tests/test_fast.py::test_fast",),
            ),
            "gameplay": TestProfile(
                description="gameplay policy validation",
                mode="targets",
                targets=("tests/test_fast.py",),
            ),
            "noncombat-evidence": TestProfile(
                description="non-combat evidence validation",
                mode="targets",
                targets=("tests/test_fast.py",),
            ),
            "full": TestProfile(
                description="complete repository validation", mode="default", targets=()
            ),
        },
    )


def test_configured_test_paths_resolve_pytest_ini_entries(temporary_repo: Path) -> None:
    assert _configured_test_paths(temporary_repo) == (temporary_repo / "tests",)


def test_repository_manifest_is_valid() -> None:
    manifest = load_manifest(
        REPOSITORY_ROOT / "tests" / "test_gate_manifest.json", REPOSITORY_ROOT
    )

    assert manifest.schema_version == 1
    assert len(manifest.full_only) == 2


def test_load_manifest_rejects_duplicate_json_key(temporary_repo: Path) -> None:
    path = temporary_repo / "test_gate_manifest.json"
    path.write_text(
        '{"schema_version": 1, "schema_version": 1, "full_only": [], "profiles": {}}',
        encoding="utf-8",
    )

    with pytest.raises(ManifestError, match="duplicate JSON key"):
        load_manifest(path, temporary_repo)


def test_load_manifest_rejects_invalid_utf8(temporary_repo: Path) -> None:
    path = temporary_repo / "test_gate_manifest.json"
    path.write_bytes(b"\xff")

    with pytest.raises(ManifestError, match="UTF-8"):
        load_manifest(path, temporary_repo)


def test_load_manifest_rejects_malformed_pytest_ini(temporary_repo: Path) -> None:
    (temporary_repo / "pytest.ini").write_text("[pytest", encoding="utf-8")

    with pytest.raises(ManifestError, match="pytest.ini"):
        load_manifest(_write_manifest(temporary_repo, VALID_MANIFEST), temporary_repo)


def test_load_manifest_rejects_pytest_ini_interpolation_error(
    temporary_repo: Path,
) -> None:
    (temporary_repo / "pytest.ini").write_text(
        "[pytest]\ntestpaths = %(missing)s\n", encoding="utf-8"
    )

    with pytest.raises(ManifestError, match="pytest.ini"):
        load_manifest(_write_manifest(temporary_repo, VALID_MANIFEST), temporary_repo)


def test_load_manifest_rejects_invalid_utf8_pytest_ini(temporary_repo: Path) -> None:
    (temporary_repo / "pytest.ini").write_bytes(b"\xff")

    with pytest.raises(ManifestError, match="pytest.ini"):
        load_manifest(_write_manifest(temporary_repo, VALID_MANIFEST), temporary_repo)


@pytest.mark.parametrize(
    ("name", "mutate", "message"),
    [
        (
            "unsupported schema version",
            lambda manifest: manifest.__setitem__("schema_version", 2),
            "unsupported schema version",
        ),
        (
            "unknown top level key",
            lambda manifest: manifest.__setitem__("unexpected", True),
            "unknown top-level key",
        ),
        (
            "unknown profile key",
            lambda manifest: manifest["profiles"]["commit"].__setitem__(
                "unexpected", True
            ),
            "unknown profile key",
        ),
        (
            "missing required profile",
            lambda manifest: manifest["profiles"].pop("full"),
            "missing required profile",
        ),
        (
            "malformed list",
            lambda manifest: manifest.__setitem__("full_only", {}),
            "must be a list",
        ),
        (
            "blank description",
            lambda manifest: manifest["profiles"]["commit"].__setitem__(
                "description", " "
            ),
            "description must not be blank",
        ),
        (
            "blank rationale",
            lambda manifest: manifest["full_only"][0].__setitem__("reason", " "),
            "reason must not be blank",
        ),
        (
            "duplicate target",
            lambda manifest: manifest["profiles"]["protocol"].__setitem__(
                "targets", ["tests/test_fast.py", "tests/test_fast.py"]
            ),
            "duplicate target",
        ),
        (
            "nonexistent file",
            lambda manifest: manifest["profiles"]["protocol"].__setitem__(
                "targets", ["tests/test_missing.py"]
            ),
            "does not exist",
        ),
        (
            "empty positive profile",
            lambda manifest: manifest["profiles"]["protocol"].__setitem__(
                "targets", []
            ),
            "requires at least one target",
        ),
        (
            "node id in full only",
            lambda manifest: manifest["full_only"][0].__setitem__(
                "path", "tests/test_slow.py::test_slow"
            ),
            "must not contain a node ID",
        ),
        (
            "full only outside configured paths",
            lambda manifest: manifest["full_only"][0].__setitem__(
                "path", "outside_test.py"
            ),
            "outside configured test paths",
        ),
    ],
)
def test_load_manifest_rejects_invalid_configuration(
    temporary_repo: Path, name: str, mutate: object, message: str
) -> None:
    manifest = copy.deepcopy(VALID_MANIFEST)
    mutate(manifest)

    with pytest.raises(ManifestError, match=message):
        load_manifest(_write_manifest(temporary_repo, manifest), temporary_repo)


@pytest.mark.parametrize(
    "profile_name",
    ("commit", "protocol", "gameplay", "noncombat-evidence", "full"),
)
def test_build_pytest_command_uses_shared_pytest_options_and_profile_basetemp(
    temporary_repo: Path, profile_name: str
) -> None:
    manifest = load_manifest(_write_manifest(temporary_repo, VALID_MANIFEST), temporary_repo)

    command = test_gate_runner.build_pytest_command(
        profile_name,
        manifest,
        temporary_repo,
        temporary_repo / ".pytest_gates",
    )

    assert command[:5] == [sys.executable, "-m", "pytest", "-q", "-p"]
    assert command[5:7] == ["no:cacheprovider", "--basetemp"]
    assert command[7] == str(temporary_repo / ".pytest_gates" / profile_name)


def test_build_pytest_command_commit_excludes_only_full_only_targets(
    temporary_repo: Path,
) -> None:
    manifest = load_manifest(_write_manifest(temporary_repo, VALID_MANIFEST), temporary_repo)

    command = test_gate_runner.build_pytest_command(
        "commit", manifest, temporary_repo, temporary_repo / ".pytest_gates"
    )

    assert command[8:] == ["--ignore=tests/test_slow.py"]


def test_build_pytest_command_full_has_no_ignores_or_positive_targets(
    temporary_repo: Path,
) -> None:
    manifest = load_manifest(_write_manifest(temporary_repo, VALID_MANIFEST), temporary_repo)

    command = test_gate_runner.build_pytest_command(
        "full", manifest, temporary_repo, temporary_repo / ".pytest_gates"
    )

    assert command[8:] == []


@pytest.mark.parametrize("profile_name", ("protocol", "gameplay", "noncombat-evidence"))
def test_build_pytest_command_appends_domain_targets(
    temporary_repo: Path, profile_name: str
) -> None:
    manifest = load_manifest(_write_manifest(temporary_repo, VALID_MANIFEST), temporary_repo)

    command = test_gate_runner.build_pytest_command(
        profile_name,
        manifest,
        temporary_repo,
        temporary_repo / ".pytest_gates",
    )

    assert command[8:] == list(manifest.profiles[profile_name].targets)


def test_main_list_prints_profiles_without_running_them(
    temporary_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest_path = _write_manifest(temporary_repo, VALID_MANIFEST)
    monkeypatch.setattr(test_gate_runner, "_DEFAULT_REPO_ROOT", temporary_repo)
    monkeypatch.setattr(test_gate_runner, "_DEFAULT_MANIFEST_PATH", manifest_path)
    monkeypatch.setattr(
        test_gate_runner,
        "run_profile",
        lambda *args, **kwargs: pytest.fail("--list must not run pytest"),
    )

    assert test_gate_runner.main(["--list"]) == 0

    output = capsys.readouterr().out
    for profile_name, profile in VALID_MANIFEST["profiles"].items():
        assert profile_name in output
        assert profile["description"] in output


def test_run_profile_dry_run_prints_windows_safe_command_without_executor(
    temporary_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest_path = _write_manifest(temporary_repo, VALID_MANIFEST)

    def executor(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        pytest.fail("--dry-run must not run pytest")

    assert test_gate_runner.run_profile(
        "commit", manifest_path, temporary_repo, dry_run=True, executor=executor
    ) == 0

    command = test_gate_runner.build_pytest_command(
        "commit",
        load_manifest(manifest_path, temporary_repo),
        temporary_repo,
        temporary_repo / ".pytest_gates",
    )
    assert subprocess.list2cmdline(command) in capsys.readouterr().out


def test_run_profile_propagates_pytest_exit_code_and_reports_elapsed_time(
    temporary_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest_path = _write_manifest(temporary_repo, VALID_MANIFEST)
    received: dict[str, object] = {}

    def executor(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        received.update(kwargs)
        received["command"] = args[0]
        return subprocess.CompletedProcess(args[0], 7)

    clock_values = iter((10.0, 12.5))

    assert test_gate_runner.run_profile(
        "protocol",
        manifest_path,
        temporary_repo,
        executor=executor,
        clock=lambda: next(clock_values),
    ) == 7

    assert received["cwd"] == temporary_repo
    assert received["check"] is False
    assert received["command"] == test_gate_runner.build_pytest_command(
        "protocol",
        load_manifest(manifest_path, temporary_repo),
        temporary_repo,
        temporary_repo / ".pytest_gates",
    )
    assert "2.50s" in capsys.readouterr().out


def test_run_profile_returns_configuration_error_without_running_executor(
    temporary_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    def executor(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        pytest.fail("invalid manifests must not run pytest")

    assert test_gate_runner.run_profile(
        "commit", temporary_repo / "missing.json", temporary_repo, executor=executor
    ) == 2

    assert "test gate configuration error:" in capsys.readouterr().err


def test_main_returns_configuration_error_code(
    temporary_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(test_gate_runner, "_DEFAULT_REPO_ROOT", temporary_repo)
    monkeypatch.setattr(
        test_gate_runner, "_DEFAULT_MANIFEST_PATH", temporary_repo / "missing.json"
    )

    assert test_gate_runner.main(["--list"]) == 2

    assert "test gate configuration error:" in capsys.readouterr().err
