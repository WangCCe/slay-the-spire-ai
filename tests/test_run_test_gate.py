from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

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
EXPECTED_REPOSITORY_FULL_ONLY = {
    "tests/test_adaptive_route_opportunity_audit.py": (
        "adaptive-route source-only artifact and replay coverage in the "
        "320.32s measured lifecycle group"
    ),
    "tests/test_audit_card_acceptance_conditional_choice.py": (
        "card acceptance source-only import isolation and deterministic "
        "publication coverage measured at 7.39s for 46 tests"
    ),
    "tests/test_audit_hierarchical_card_reward_credit_assignment.py": (
        "owns hierarchical card-reward credit audit publication and Git binding; "
        "measured 13.597s for 28 tests on 2026-08-28"
    ),
    "tests/test_noncombat_card_acceptance_empirical_successor_control.py": (
        "owns empirical-successor control isolation and publication lifecycle; "
        "measured 29.781s for 143 tests on 2026-08-28"
    ),
    "tests/test_noncombat_card_acceptance_empirical_successor_runtime.py": (
        "owns empirical-successor runtime fitting and checkpoint lifecycle; "
        "measured 117.800s for 70 tests on 2026-08-28"
    ),
    "tests/test_noncombat_card_acceptance_empirical_successor_seed_inventory.py": (
        "owns empirical-successor seed inventory subprocess and source binding; "
        "measured 87.089s for 83 tests on 2026-08-28"
    ),
    "tests/test_noncombat_card_acceptance_empirical_successor_training_runner.py": (
        "owns empirical-successor training runner isolation and execution lifecycle; "
        "measured 18.891s for 160 tests on 2026-08-28"
    ),
    "tests/test_noncombat_card_acceptance_empirical_successor_training_runner_verifier.py": (
        "owns training-runner verifier replay and immutable-bundle checks; "
        "measured 60.528s for 68 tests on 2026-08-28"
    ),
    "tests/test_noncombat_card_acceptance_empirical_successor_verifier.py": (
        "owns empirical-successor verifier replay and terminal publication; "
        "measured 53.070s for 71 tests on 2026-08-28"
    ),
    "tests/test_noncombat_card_counterfactual_ranking_training.py": (
        "owns card counterfactual ranking fitting and checkpoint behavior; "
        "measured 25.200s for 13 tests on 2026-08-28"
    ),
    "tests/test_noncombat_card_only_baseline_clipping_ablation.py": (
        "owns baseline-clipping ablation fitting and restoration lifecycle; "
        "measured 53.333s for 5 tests on 2026-08-28"
    ),
    "tests/test_noncombat_card_only_behavior_sensitivity_training.py": (
        "owns card-only behavior-sensitivity fitting and checkpoint lifecycle; "
        "measured 83.010s for 5 tests on 2026-08-28"
    ),
    "tests/test_noncombat_card_only_native_baseline_rl_pilot.py": (
        "owns native-baseline pilot fitting and checkpoint lifecycle; measured "
        "143.227s for 26 tests on 2026-08-28"
    ),
    "tests/test_noncombat_card_scorer_optimizer_replay_ablation.py": (
        "owns scorer-optimizer replay ablation fitting and restoration; measured "
        "23.364s for 2 tests on 2026-08-28"
    ),
    "tests/test_noncombat_cross_fitted_empirical_successor_readiness.py": (
        "readiness source binding, subprocess rehearsal, and Git replay in the "
        "320.32s measured lifecycle group"
    ),
    "tests/test_noncombat_cross_fitted_hierarchical_learning_control.py": (
        "execution lifecycle, real registration, crash recovery, and checkpoint "
        "coverage in the 320.32s measured lifecycle group"
    ),
    "tests/test_noncombat_cross_fitted_hierarchical_learning_runtime.py": (
        "Torch rollout, update, checkpoint, and deadline coverage measured at "
        "16.14s for 24 tests after the deadline repair"
    ),
    "tests/test_noncombat_cross_fitted_hierarchical_learning_seed_inventory.py": (
        "owns cross-fitted seed inventory generation and readiness binding; "
        "measured 11.512s for 31 tests on 2026-08-28"
    ),
    "tests/test_noncombat_cross_fitted_hierarchical_learning_verifier.py": (
        "independent terminal and immutable bundle replay measured at about "
        "422.8s after subtracting the 1.01s paired audit file"
    ),
    "tests/test_noncombat_current_baseline_evidence_study.py": (
        "historical seed and Git replay with a measured 138.28s overlap "
        "rejection node"
    ),
    "tests/test_noncombat_current_baseline_replication.py": (
        "owns final baseline replication history replay and publication lifecycle; "
        "measured 11.643s for 33 tests on 2026-08-28"
    ),
    "tests/test_noncombat_current_policy_simulator_bridge.py": (
        "source-only bridge lifecycle and subprocess coverage in the 320.32s "
        "measured lifecycle group"
    ),
    "tests/test_noncombat_expanded_shop_ensemble_retraining.py": (
        "owns expanded shop-ensemble retraining and delegated ranker checks; "
        "measured 11.143s for 3 tests on 2026-08-28"
    ),
    "tests/test_noncombat_family_preserving_conditional_card_ranking.py": (
        "owns family-preserving conditional ranker fitting and checkpoint lifecycle; "
        "measured 57.955s for 7 tests on 2026-08-28"
    ),
    "tests/test_noncombat_hierarchical_advantage_attribution.py": (
        "fresh-process rendering and import-isolation coverage with a measured "
        "10.37s deterministic-rendering node"
    ),
    "tests/test_noncombat_hierarchical_policy_objective.py": (
        "fresh-process objective import-isolation coverage with a measured "
        "16.16s bidirectional-isolation node"
    ),
    "tests/test_noncombat_hierarchical_simulator_learning_experiment.py": (
        "hierarchical source-only lifecycle and historical Git replay in the "
        "320.32s measured lifecycle group"
    ),
    "tests/test_noncombat_hierarchical_simulator_learning_runtime.py": (
        "owns hierarchical runtime rollout, update, and verification lifecycle; "
        "measured 15.700s for 35 tests on 2026-08-28"
    ),
    "tests/test_noncombat_large_corpus_state_conditioned_card_ranking.py": (
        "owns large-corpus state-conditioned ranker fitting and checkpoints; "
        "measured 69.575s for 7 tests on 2026-08-28"
    ),
    "tests/test_noncombat_ope_estimate_verifier.py": (
        "owns OPE estimate bundle replay and independent verification; measured "
        "22.085s for 11 tests on 2026-08-28"
    ),
    "tests/test_noncombat_outcome_evidence_expansion.py": (
        "owns outcome-evidence expansion subprocess, publication, and Git replay; "
        "measured 14.719s for 37 tests on 2026-08-28"
    ),
    "tests/test_noncombat_outcome_evidence_runner.py": (
        "subprocess, crash-recovery, and temporary Git replay matrix"
    ),
    "tests/test_noncombat_outcome_evidence_verifier.py": (
        "independent verifier subprocess and historical Git replay matrix"
    ),
    "tests/test_noncombat_route_card_residual_ranker_poc.py": (
        "deterministic synthetic primary replay with a measured 18.78s node"
    ),
    "tests/test_noncombat_simulator_baseline_warm_start.py": (
        "hash-closed warm-start artifact lifecycle with a measured 14.49s "
        "publication node"
    ),
    "tests/test_noncombat_simulator_rl_experiment.py": (
        "simulator RL terminal publication and checkpoint lifecycle in the "
        "320.32s measured lifecycle group"
    ),
    "tests/test_noncombat_state_conditioned_simulator_learning_experiment.py": (
        "state-conditioned lifecycle, recovery, and independent verification "
        "in the 320.32s measured lifecycle group"
    ),
}


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


def _junit_path(command: list[str]) -> Path:
    return Path(command[command.index("--junitxml") + 1])


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
    assert {target.path: target.reason for target in manifest.full_only} == (
        EXPECTED_REPOSITORY_FULL_ONLY
    )


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
def test_build_pytest_command_uses_shared_pytest_options_and_resolved_basetemp(
    temporary_repo: Path, profile_name: str
) -> None:
    manifest = load_manifest(_write_manifest(temporary_repo, VALID_MANIFEST), temporary_repo)
    basetemp = temporary_repo / ".pytest_gates" / f"{profile_name}-deterministic"

    command = test_gate_runner.build_pytest_command(
        profile_name,
        manifest,
        temporary_repo,
        basetemp,
    )

    assert command[:5] == [sys.executable, "-m", "pytest", "-q", "-p"]
    assert command[5:7] == ["no:cacheprovider", "--basetemp"]
    assert command[7] == str(basetemp)


def test_build_pytest_command_commit_excludes_only_full_only_targets(
    temporary_repo: Path,
) -> None:
    manifest = load_manifest(_write_manifest(temporary_repo, VALID_MANIFEST), temporary_repo)

    command = test_gate_runner.build_pytest_command(
        "commit",
        manifest,
        temporary_repo,
        temporary_repo / ".pytest_gates" / "commit-deterministic",
    )

    assert command[8:] == ["--ignore=tests/test_slow.py"]


def test_build_pytest_command_full_has_no_ignores_or_positive_targets(
    temporary_repo: Path,
) -> None:
    manifest = load_manifest(_write_manifest(temporary_repo, VALID_MANIFEST), temporary_repo)

    command = test_gate_runner.build_pytest_command(
        "full",
        manifest,
        temporary_repo,
        temporary_repo / ".pytest_gates" / "full-deterministic",
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
        temporary_repo / ".pytest_gates" / f"{profile_name}-deterministic",
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
    temporary_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest_path = _write_manifest(temporary_repo, VALID_MANIFEST)
    monkeypatch.setattr(
        test_gate_runner,
        "uuid4",
        lambda: SimpleNamespace(hex="dryruntoken"),
        raising=False,
    )

    def executor(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        pytest.fail("--dry-run must not run pytest")

    assert test_gate_runner.run_profile(
        "commit", manifest_path, temporary_repo, dry_run=True, executor=executor
    ) == 0

    command = test_gate_runner.build_pytest_command(
        "commit",
        load_manifest(manifest_path, temporary_repo),
        temporary_repo,
        temporary_repo / ".pytest_gates" / "commit-dryruntoken",
    )
    output = capsys.readouterr().out
    assert "test gate dry-run profile: commit" in output
    assert f"pytest command: {subprocess.list2cmdline(command)}" in output


def test_run_profile_reports_and_flushes_command_before_executor(
    temporary_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest_path = _write_manifest(temporary_repo, VALID_MANIFEST)
    monkeypatch.setattr(
        test_gate_runner,
        "uuid4",
        lambda: SimpleNamespace(hex="orderingtoken"),
        raising=False,
    )

    def executor(
        command: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        output_at_executor_call = capsys.readouterr().out
        assert "test gate run profile: protocol" in output_at_executor_call
        assert f"pytest command: {subprocess.list2cmdline(command)}" in output_at_executor_call
        return subprocess.CompletedProcess(command, 0)

    assert test_gate_runner.run_profile(
        "protocol", manifest_path, temporary_repo, executor=executor
    ) == 0


def test_run_profile_uses_unique_profile_prefixed_repository_basetemp(
    temporary_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest_path = _write_manifest(temporary_repo, VALID_MANIFEST)
    tokens = iter(("firsttoken", "secondtoken"))
    monkeypatch.setattr(
        test_gate_runner,
        "uuid4",
        lambda: SimpleNamespace(hex=next(tokens)),
        raising=False,
    )
    commands: list[list[str]] = []

    def executor(
        command: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return subprocess.CompletedProcess(command, 0)

    assert test_gate_runner.run_profile(
        "gameplay", manifest_path, temporary_repo, executor=executor
    ) == 0
    assert test_gate_runner.run_profile(
        "gameplay", manifest_path, temporary_repo, executor=executor
    ) == 0

    basetemps = [Path(command[7]) for command in commands]
    assert basetemps == [
        temporary_repo / ".pytest_gates" / "gameplay-firsttoken",
        temporary_repo / ".pytest_gates" / "gameplay-secondtoken",
    ]
    assert basetemps[0] != basetemps[1]


def test_run_profile_creates_only_basetemp_parent_before_executor(
    temporary_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest_path = _write_manifest(temporary_repo, VALID_MANIFEST)
    monkeypatch.setattr(
        test_gate_runner,
        "uuid4",
        lambda: SimpleNamespace(hex="parenttoken"),
    )
    expected_basetemp = (
        temporary_repo / ".pytest_gates" / "commit-parenttoken"
    )

    def executor(
        command: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        assert expected_basetemp.parent.is_dir()
        assert not expected_basetemp.exists()
        return subprocess.CompletedProcess(command, 0)

    assert test_gate_runner.run_profile(
        "commit", manifest_path, temporary_repo, executor=executor
    ) == 0


def test_repository_ignores_generated_pytest_gate_state() -> None:
    result = subprocess.run(
        [
            "git",
            "check-ignore",
            "--quiet",
            "--",
            ".pytest_gates/commit-deterministic/pytest-current",
        ],
        cwd=REPOSITORY_ROOT,
        check=False,
    )

    assert result.returncode == 0


def test_run_profile_propagates_pytest_exit_code_and_reports_elapsed_time(
    temporary_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest_path = _write_manifest(temporary_repo, VALID_MANIFEST)
    received: dict[str, object] = {}
    monkeypatch.setattr(
        test_gate_runner,
        "uuid4",
        lambda: SimpleNamespace(hex="exitcodetoken"),
        raising=False,
    )

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
        temporary_repo / ".pytest_gates" / "protocol-exitcodetoken",
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


@pytest.mark.parametrize("unsafe_kind", ("existing", "escaping"))
def test_timing_report_rejects_unsafe_path_without_running_pytest(
    temporary_repo: Path, unsafe_kind: str, tmp_path: Path
) -> None:
    manifest_path = _write_manifest(temporary_repo, VALID_MANIFEST)
    timing_report = (
        temporary_repo / "reports" / "timing.json"
        if unsafe_kind == "existing"
        else tmp_path.parent / "outside-timing.json"
    )
    if unsafe_kind == "existing":
        timing_report.parent.mkdir()
        timing_report.write_text("existing", encoding="utf-8")

    def executor(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        pytest.fail("unsafe timing paths must not run pytest")

    assert test_gate_runner.run_profile(
        "commit",
        manifest_path,
        temporary_repo,
        timing_report=timing_report,
        executor=executor,
    ) == 2


def test_timing_command_preserves_profile_selection_and_default_argv(
    temporary_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest_path = _write_manifest(temporary_repo, VALID_MANIFEST)
    monkeypatch.setattr(
        test_gate_runner,
        "uuid4",
        lambda: SimpleNamespace(hex="timingselectiontoken"),
    )
    observed: list[list[str]] = []

    def executor(
        command: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        observed.append(command)
        _junit_path(command).write_text(
            '<testsuites><testsuite tests="1"><testcase '
            'classname="tests.test_fast" file="tests/test_fast.py" '
            'name="test_fast" time="0.125" /></testsuite></testsuites>',
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0)

    report_path = temporary_repo / "reports" / "timing.json"
    assert test_gate_runner.run_profile(
        "commit",
        manifest_path,
        temporary_repo,
        timing_report=report_path,
        executor=executor,
        clock=iter((1.0, 1.5)).__next__,
    ) == 0

    default_command = test_gate_runner.build_pytest_command(
        "commit",
        load_manifest(manifest_path, temporary_repo),
        temporary_repo,
        temporary_repo / ".pytest_gates" / "commit-timingselectiontoken",
    )
    timed_command = observed[0]
    junit_index = timed_command.index("--junitxml")
    assert timed_command[:junit_index] == default_command
    assert timed_command[junit_index + 2 :] == ["-o", "junit_family=legacy"]


def test_timing_report_aggregates_deterministically_and_preserves_failure(
    temporary_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest_path = _write_manifest(temporary_repo, VALID_MANIFEST)
    monkeypatch.setattr(
        test_gate_runner,
        "uuid4",
        lambda: SimpleNamespace(hex="timingaggregationtoken"),
    )
    execution_count = 0

    def executor(
        command: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        nonlocal execution_count
        execution_count += 1
        _junit_path(command).write_text(
            """<testsuites><testsuite tests="4" failures="1" errors="1" skipped="1">
            <testcase classname="tests.test_fast" file="tests/test_fast.py" name="test_pass" time="0.2" />
            <testcase classname="tests.test_fast" file="tests\\test_fast.py" name="test_fail" time="0.4"><failure /></testcase>
            <testcase classname="tests.test_slow" file="tests/test_slow.py" name="test_skip" time="0.1"><skipped /></testcase>
            <testcase classname="tests.test_slow" file="tests/test_slow.py" name="test_error" time="0.5"><error /></testcase>
            </testsuite></testsuites>""",
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 7)

    report_path = temporary_repo / "reports" / "timing.json"
    assert test_gate_runner.run_profile(
        "commit",
        manifest_path,
        temporary_repo,
        timing_report=report_path,
        executor=executor,
        clock=iter((10.0, 12.5)).__next__,
    ) == 7
    assert execution_count == 1

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report == {
        "outcome_counts": {"error": 1, "failed": 1, "passed": 1, "skipped": 1},
        "per_file": [
            {
                "duration_seconds": 0.6,
                "file": "tests/test_fast.py",
                "outcome_counts": {
                    "error": 0,
                    "failed": 1,
                    "passed": 1,
                    "skipped": 0,
                },
                "test_count": 2,
            },
            {
                "duration_seconds": 0.6,
                "file": "tests/test_slow.py",
                "outcome_counts": {
                    "error": 1,
                    "failed": 0,
                    "passed": 0,
                    "skipped": 1,
                },
                "test_count": 2,
            },
        ],
        "profile": "commit",
        "pytest_exit_code": 7,
        "runner_elapsed_seconds": 2.5,
        "schema_version": 1,
        "slow_tests": [
            {
                "classname": "tests.test_slow",
                "duration_seconds": 0.5,
                "file": "tests/test_slow.py",
                "name": "test_error",
                "outcome": "error",
            },
            {
                "classname": "tests.test_fast",
                "duration_seconds": 0.4,
                "file": "tests/test_fast.py",
                "name": "test_fail",
                "outcome": "failed",
            },
            {
                "classname": "tests.test_fast",
                "duration_seconds": 0.2,
                "file": "tests/test_fast.py",
                "name": "test_pass",
                "outcome": "passed",
            },
            {
                "classname": "tests.test_slow",
                "duration_seconds": 0.1,
                "file": "tests/test_slow.py",
                "name": "test_skip",
                "outcome": "skipped",
            },
        ],
        "test_count": 4,
    }


def test_timing_report_fails_closed_on_unattributed_testcase(
    temporary_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest_path = _write_manifest(temporary_repo, VALID_MANIFEST)
    monkeypatch.setattr(
        test_gate_runner,
        "uuid4",
        lambda: SimpleNamespace(hex="timingincompletetoken"),
    )

    def executor(
        command: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        _junit_path(command).write_text(
            '<testsuites><testsuite tests="1"><testcase '
            'classname="tests.test_fast" name="test_fast" time="0.1" '
            '/></testsuite></testsuites>',
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0)

    report_path = temporary_repo / "reports" / "timing.json"
    assert test_gate_runner.run_profile(
        "commit",
        manifest_path,
        temporary_repo,
        timing_report=report_path,
        executor=executor,
    ) == 2
    assert not report_path.exists()
