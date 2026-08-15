import builtins
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import main
import pytest
from main import (
    create_ready_coordinator,
    initialize_noncombat_exploration_if_configured,
    initialize_pre_agent_runtime,
    initialize_study_handshake_if_configured,
    is_study_handshake_configured,
    is_unrecoverable_run_error,
)
from spirecomm.communication import study_handshake


def _create_directory_junction(link_path, target_path):
    completed = subprocess.run(
        ["cmd.exe", "/c", "mklink", "/J", str(link_path), str(target_path)],
        capture_output=True,
        check=False,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout


def _qualification_environment(tmp_path):
    config_path = (tmp_path / "qualification-config.json").resolve()
    config_path.write_text("{}\n", encoding="utf-8", newline="")
    paths = study_handshake.HandshakePaths(
        attempt=(tmp_path / "qualification-attempt.json").resolve(),
        ready=(tmp_path / "qualification-ready.json").resolve(),
        release=(tmp_path / "qualification-release.json").resolve(),
    )
    attempt = study_handshake.build_attempt_record(
        study_id="qualification-r4",
        registration_hash="a" * 64,
        run_lock_hash="0" * 64,
        slot_number=1,
        session_id="qualification-r4-s01",
        config_path=config_path,
        config_sha256=hashlib.sha256(config_path.read_bytes()).hexdigest(),
        marker_start_count=0,
        paths=paths,
        readiness_timeout_seconds=120,
        release_timeout_seconds=10,
        created_unix_ns=1,
    )
    study_handshake.publish_record_once(paths.attempt, attempt)
    return {
        study_handshake.HANDSHAKE_ATTEMPT_ENV: str(paths.attempt),
        main.QUALIFICATION_ATTEMPT_HASH_ENV: attempt["attempt_hash"],
    }, attempt


def test_stuck_game_error_is_unrecoverable():
    assert is_unrecoverable_run_error(
        Exception(
            "Game appears stuck (no state update for 20 seconds). "
            "Last action may have caused the game to hang."
        )
    )


def test_communication_timeout_error_is_unrecoverable():
    assert is_unrecoverable_run_error(
        Exception("Communication Mod not responding (timeout after 10 attempts)")
    )


def test_generic_run_error_can_continue():
    assert not is_unrecoverable_run_error(Exception("temporary reward parsing issue"))


def test_rl_ready_coordinator_defers_stdin_reader(monkeypatch):
    calls = []

    class FakeCoordinator:
        def __init__(self, *, start_input_thread=True):
            calls.append(("init", start_input_thread))

        def signal_ready(self):
            calls.append(("ready", None))

    monkeypatch.setattr(main, "Coordinator", FakeCoordinator)

    coordinator, input_thread_deferred = create_ready_coordinator("combat_rl")

    assert isinstance(coordinator, FakeCoordinator)
    assert input_thread_deferred is True
    assert calls == [("init", False), ("ready", None)]


def test_non_rl_ready_coordinator_starts_stdin_reader_immediately(monkeypatch):
    calls = []

    class FakeCoordinator:
        def __init__(self, *, start_input_thread=True):
            calls.append(("init", start_input_thread))

        def signal_ready(self):
            calls.append(("ready", None))

    monkeypatch.setattr(main, "Coordinator", FakeCoordinator)

    _coordinator, input_thread_deferred = create_ready_coordinator("optimized")

    assert input_thread_deferred is False
    assert calls == [("init", True), ("ready", None)]


def test_rl_ready_coordinator_can_force_stdin_for_study_handshake(monkeypatch):
    calls = []

    class FakeCoordinator:
        def __init__(self, *, start_input_thread=True):
            calls.append(("init", start_input_thread))

        def signal_ready(self):
            calls.append(("ready", None))

    monkeypatch.setattr(main, "Coordinator", FakeCoordinator)

    coordinator, input_thread_deferred = create_ready_coordinator(
        "combat_rl",
        force_input_thread=True,
    )

    assert isinstance(coordinator, FakeCoordinator)
    assert input_thread_deferred is False
    assert calls == [("init", True), ("ready", None)]


def test_study_handshake_configuration_uses_environment_key_presence():
    key = study_handshake.HANDSHAKE_ATTEMPT_ENV

    assert is_study_handshake_configured({}) is False
    assert is_study_handshake_configured({key: ""}) is True
    assert is_study_handshake_configured({key: "C:\\attempt.json"}) is True


def test_study_handshake_initializer_delegates_with_same_environment(monkeypatch):
    captured = {}
    sentinel = object()
    coordinator = object()
    environ = {study_handshake.HANDSHAKE_ATTEMPT_ENV: "C:\\attempt.json"}

    def fake_perform(received_coordinator, *, environ):
        captured["coordinator"] = received_coordinator
        captured["environ"] = environ
        return sentinel

    monkeypatch.setattr(
        study_handshake,
        "perform_child_handshake_if_configured",
        fake_perform,
    )

    assert (
        initialize_study_handshake_if_configured(
            coordinator,
            environ=environ,
        )
        is sentinel
    )
    assert captured == {"coordinator": coordinator, "environ": environ}


def test_pre_agent_runtime_keeps_normal_startup_order():
    events = []
    coordinator = object()

    def initialize_exploration(**kwargs):
        events.append(("exploration", kwargs["environ"]))
        return "runtime"

    def create_coordinator(agent_type, *, force_input_thread):
        events.append(("coordinator", agent_type, force_input_thread))
        return coordinator, True

    def initialize_handshake(*args, **kwargs):
        raise AssertionError("normal startup entered study handshake")

    result = initialize_pre_agent_runtime(
        agent_type="combat_rl",
        environ={},
        exploration_kwargs={"training": False},
        exploration_initializer=initialize_exploration,
        coordinator_factory=create_coordinator,
        handshake_initializer=initialize_handshake,
    )

    assert result == (coordinator, True, "runtime")
    assert events == [
        ("exploration", {}),
        ("coordinator", "combat_rl", False),
    ]


def test_pre_agent_runtime_gates_study_before_exploration():
    events = []
    coordinator = object()
    key = study_handshake.HANDSHAKE_ATTEMPT_ENV
    environ = {key: "C:\\attempt.json"}

    def create_coordinator(agent_type, *, force_input_thread):
        events.append(("coordinator", agent_type, force_input_thread))
        return coordinator, False

    def initialize_handshake(received_coordinator, *, environ):
        assert received_coordinator is coordinator
        events.append(("handshake", environ))
        return True

    def initialize_exploration(**kwargs):
        events.append(("exploration", kwargs["environ"]))
        return "runtime"

    result = initialize_pre_agent_runtime(
        agent_type="combat_rl",
        environ=environ,
        exploration_kwargs={"training": False},
        exploration_initializer=initialize_exploration,
        coordinator_factory=create_coordinator,
        handshake_initializer=initialize_handshake,
    )

    assert result == (coordinator, False, "runtime")
    assert events == [
        ("coordinator", "combat_rl", True),
        ("handshake", environ),
        ("exploration", environ),
    ]


def test_qualification_child_exits_after_release_before_exploration(tmp_path):
    environ, _attempt = _qualification_environment(tmp_path)
    events = []
    coordinator = object()

    def create_coordinator(agent_type, *, force_input_thread):
        events.append(("coordinator", agent_type, force_input_thread))
        return coordinator, False

    def initialize_handshake(received_coordinator, *, environ):
        assert received_coordinator is coordinator
        events.append(("handshake", environ))
        return True

    def initialize_exploration(**_kwargs):
        pytest.fail("qualification initialized exploration")

    with pytest.raises(main.QualificationChildComplete):
        initialize_pre_agent_runtime(
            agent_type="combat_rl",
            environ=environ,
            exploration_kwargs={"training": False},
            exploration_initializer=initialize_exploration,
            coordinator_factory=create_coordinator,
            handshake_initializer=initialize_handshake,
        )

    assert events == [
        ("coordinator", "combat_rl", True),
        ("handshake", environ),
    ]


def test_qualification_attempt_hash_must_match_loaded_attempt(tmp_path):
    environ, _attempt = _qualification_environment(tmp_path)
    environ[main.QUALIFICATION_ATTEMPT_HASH_ENV] = "f" * 64

    with pytest.raises(ValueError, match="attempt-hash binding mismatch"):
        main.qualification_exit_requested(environ=environ)


def test_qualification_attempt_rejects_ancestor_junction_before_load(tmp_path):
    attempt_target = tmp_path / "attempt-target"
    attempt_target.mkdir()
    environ, _attempt = _qualification_environment(attempt_target)
    attempt_alias = tmp_path / "attempt-alias"
    _create_directory_junction(attempt_alias, attempt_target)
    environ[study_handshake.HANDSHAKE_ATTEMPT_ENV] = str(
        attempt_alias / "qualification-attempt.json"
    )

    try:
        with pytest.raises(ValueError, match="symbolic link|reparse"):
            main.qualification_exit_requested(environ=environ)
    finally:
        os.rmdir(attempt_alias)


def test_qualification_attempt_guard_precedes_runtime_handshake(tmp_path):
    attempt_target = tmp_path / "attempt-target"
    attempt_target.mkdir()
    environ, _attempt = _qualification_environment(attempt_target)
    attempt_alias = tmp_path / "attempt-alias"
    _create_directory_junction(attempt_alias, attempt_target)
    environ[study_handshake.HANDSHAKE_ATTEMPT_ENV] = str(
        attempt_alias / "qualification-attempt.json"
    )
    events = []

    def create_coordinator(*_args, **_kwargs):
        events.append("coordinator")
        return object(), False

    def initialize_handshake(*_args, **_kwargs):
        pytest.fail("shared handshake ran before qualification path guard")

    try:
        with pytest.raises(ValueError, match="symbolic link|reparse"):
            initialize_pre_agent_runtime(
                agent_type="combat_rl",
                environ=environ,
                exploration_initializer=lambda **_kwargs: pytest.fail(
                    "qualification initialized exploration"
                ),
                coordinator_factory=create_coordinator,
                handshake_initializer=initialize_handshake,
            )
    finally:
        os.rmdir(attempt_alias)

    assert events == []


def test_qualification_attempt_rejects_unc_before_filesystem_probe(monkeypatch):
    monkeypatch.setattr(
        Path,
        "lstat",
        lambda _path: pytest.fail("qualification attempted a UNC probe"),
    )

    with pytest.raises(ValueError, match="UNC|local drive"):
        main._qualification_require_no_follow_file(
            r"\\qualification.invalid\share\attempt.json"
        )


def test_qualification_attempt_rejects_ads_before_filesystem_probe(
    tmp_path,
    monkeypatch,
):
    attempt_path = tmp_path / "qualification-attempt.json"
    monkeypatch.setattr(
        Path,
        "lstat",
        lambda _path: pytest.fail("qualification attempted an ADS probe"),
    )

    with pytest.raises(ValueError, match="alternate data stream"):
        main._qualification_require_no_follow_file(
            f"{attempt_path}:qualification-attempt"
        )


@pytest.mark.parametrize("suffix", [".", " "])
def test_qualification_attempt_rejects_win32_alias_before_filesystem_probe(
    tmp_path,
    monkeypatch,
    suffix,
):
    attempt_path = tmp_path / f"qualification-attempt.json{suffix}"
    monkeypatch.setattr(
        Path,
        "lstat",
        lambda _path: pytest.fail("qualification attempted an alias probe"),
    )

    with pytest.raises(ValueError, match="Win32 alias"):
        main._qualification_require_no_follow_file(str(attempt_path))


def test_qualification_token_without_handshake_fails_closed():
    with pytest.raises(ValueError, match="requires a study handshake"):
        main.qualification_exit_requested(
            environ={main.QUALIFICATION_ATTEMPT_HASH_ENV: "a" * 64}
        )


def test_entrypoint_rejects_qualification_token_before_exploration_dry_run(
    tmp_path,
):
    log_path = (tmp_path / "qualification-entrypoint.log").resolve()
    environment = os.environ.copy()
    environment[main.QUALIFICATION_ATTEMPT_HASH_ENV] = "a" * 64
    environment["STS_AI_LOG_FILE"] = str(log_path)
    environment.pop(study_handshake.HANDSHAKE_ATTEMPT_ENV, None)
    environment.pop("STS_NONCOMBAT_EXPLORATION_CONFIG", None)

    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            "-S",
            str(Path(main.__file__).resolve()),
            "--noncombat-exploration-dry-run",
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 2
    log = log_path.read_text(encoding="utf-8")
    assert "qualification exit requires a study handshake" in log
    assert "requires STS_NONCOMBAT_EXPLORATION_CONFIG" not in log


def test_main_supports_isolated_interpreter_startup(tmp_path):
    completed = subprocess.run(
        [sys.executable, "-I", str(Path(main.__file__).resolve()), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "usage:" in completed.stdout.lower()


def test_main_help_exposes_adaptive_elite_route_without_changing_default(tmp_path):
    completed = subprocess.run(
        [sys.executable, "-I", str(Path(main.__file__).resolve()), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "{conservative,aggressive,adaptive}" in completed.stdout
    assert "default: aggressive" in completed.stdout


def test_create_agent_rejects_full_rl_adaptive_before_any_side_effect(
    monkeypatch,
):
    expected_error = (
        "--elite-route adaptive is unsupported for --agent rl; "
        "adaptive routing requires a heuristic map owner"
    )

    def forbidden(name):
        return lambda *args, **kwargs: pytest.fail(f"{name} was called")

    monkeypatch.setattr(main, "_load_rl_components", forbidden("RL loader"))
    monkeypatch.setattr(
        main,
        "find_latest_checkpoint",
        forbidden("checkpoint lookup"),
    )
    monkeypatch.setattr(main, "create_rl_agent", forbidden("RL factory"))
    monkeypatch.setattr(main, "SimpleAgent", forbidden("SimpleAgent fallback"))

    with pytest.raises(ValueError) as error:
        main.create_agent(
            agent_type="rl",
            player_class=main.PlayerClass.IRONCLAD,
            training=True,
            elite_mode="adaptive",
        )

    assert str(error.value) == expected_error


@pytest.mark.parametrize("agent_type", ("simple", "optimized", "auto"))
def test_heuristic_agent_types_preserve_adaptive_route_mode(
    monkeypatch,
    agent_type,
):
    class StubHeuristicAgent:
        def __init__(self, chosen_class=None, elite_mode=None):
            self.chosen_class = chosen_class
            self.elite_mode = elite_mode

    monkeypatch.setattr(main, "SimpleAgent", StubHeuristicAgent)
    monkeypatch.setattr(main, "OptimizedAgent", StubHeuristicAgent)
    monkeypatch.setattr(main, "OPTIMIZED_AI_AVAILABLE", True)

    agent = main.create_agent(
        agent_type=agent_type,
        player_class=main.PlayerClass.IRONCLAD,
        elite_mode="adaptive",
    )

    assert agent.chosen_class == main.PlayerClass.IRONCLAD
    assert agent.elite_mode == "adaptive"


def test_combat_rl_preserves_adaptive_heuristic_route_mode(monkeypatch):
    class StubCombatRLAgent:
        def __init__(self, *, elite_mode=None, **_kwargs):
            self.elite_mode = elite_mode
            self.rl_agent = SimpleNamespace(
                state_encoder=SimpleNamespace(feature_dim=1),
                action_encoder=SimpleNamespace(MAX_ACTIONS=1),
            )

    monkeypatch.setattr(main, "_load_rl_components", lambda: None)
    monkeypatch.setattr(main, "RL_AVAILABLE", True)
    monkeypatch.setattr(main, "RL_V2_AVAILABLE", True)
    monkeypatch.setattr(main, "CombatRLAgent", StubCombatRLAgent)

    agent = main.create_agent(
        agent_type="combat_rl",
        player_class=main.PlayerClass.IRONCLAD,
        elite_mode="adaptive",
    )

    assert agent.elite_mode == "adaptive"


def test_create_combat_rl_forwards_parent_policy_anchor_weight(monkeypatch):
    calls = []

    class StubCombatRLAgent:
        def __init__(self, **kwargs):
            calls.append(kwargs)
            self.rl_agent = SimpleNamespace(
                state_encoder=SimpleNamespace(feature_dim=1),
                action_encoder=SimpleNamespace(MAX_ACTIONS=1),
            )

    monkeypatch.setattr(main, "_load_rl_components", lambda: None)
    monkeypatch.setattr(main, "RL_AVAILABLE", True)
    monkeypatch.setattr(main, "RL_V2_AVAILABLE", True)
    monkeypatch.setattr(main, "CombatRLAgent", StubCombatRLAgent)

    main.create_agent(
        agent_type="combat_rl",
        player_class=main.PlayerClass.IRONCLAD,
        training=True,
        model_path="checkpoints/parent.pth",
        rl_version="v2",
        parent_policy_anchor_weight=0.25,
    )

    assert calls[0]["parent_policy_anchor_weight"] == pytest.approx(0.25)


@pytest.mark.parametrize("elite_mode", ("conservative", "aggressive"))
def test_full_rl_legacy_route_mode_keeps_learned_map_factory(
    monkeypatch,
    elite_mode,
):
    factory_calls = []

    def stub_rl_factory(**kwargs):
        factory_calls.append(kwargs)
        return SimpleNamespace(
            state_encoder=SimpleNamespace(feature_dim=1),
            action_encoder=SimpleNamespace(MAX_ACTIONS=1),
        )

    monkeypatch.setattr(main, "_load_rl_components", lambda: None)
    monkeypatch.setattr(main, "RL_AVAILABLE", True)
    monkeypatch.setattr(main, "RL_V2_AVAILABLE", True)
    monkeypatch.setattr(main, "create_rl_agent", stub_rl_factory)

    agent = main.create_agent(
        agent_type="rl",
        player_class=main.PlayerClass.IRONCLAD,
        elite_mode=elite_mode,
    )

    assert agent is not None
    assert len(factory_calls) == 1
    assert "elite_mode" not in factory_calls[0]


def test_entrypoint_rejects_full_rl_adaptive_before_pre_agent_startup(tmp_path):
    expected_error = (
        "--elite-route adaptive is unsupported for --agent rl; "
        "adaptive routing requires a heuristic map owner"
    )
    log_path = (tmp_path / "adaptive-full-rl-entrypoint.log").resolve()
    environment = os.environ.copy()
    environment["STS_AI_LOG_FILE"] = str(log_path)
    probe = """
import runpy
import sys
from pathlib import Path

main_path = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(main_path.parent))
import spirecomm.communication.coordinator as coordinator_module

class ForbiddenCoordinator:
    def __init__(self, *args, **kwargs):
        raise RuntimeError("coordinator startup reached")

coordinator_module.Coordinator = ForbiddenCoordinator
sys.argv = [
    str(main_path),
    "--agent", "rl",
    "--elite-route", "adaptive",
    "--eval",
]
runpy.run_path(str(main_path), run_name="__main__")
"""

    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            probe,
            str(Path(main.__file__).resolve()),
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 2
    assert expected_error in completed.stderr
    log = log_path.read_text(encoding="utf-8")
    assert "Creating CommunicationMod coordinator" not in log
    assert "Creating RL Agent" not in log
    assert "Evaluation mode auto-loading latest checkpoint" not in log
    assert "Evaluation mode requested but no checkpoint was found" not in log
    assert "Falling back" not in log


def test_qualification_child_rejects_site_enabled_isolated_startup(tmp_path):
    probe = "import runpy,sys; runpy.run_path(sys.argv[1], run_name='probe')"
    environment = os.environ.copy()
    environment[main.QUALIFICATION_ATTEMPT_HASH_ENV] = "a" * 64

    completed = subprocess.run(
        [sys.executable, "-I", "-c", probe, str(Path(main.__file__).resolve())],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 2
    assert "no-site" in completed.stderr.lower()


@pytest.mark.parametrize(
    ("qualification_requested", "expected_write_disabled", "expected_prefix"),
    (
        (True, True, os.path.join(os.devnull, "sts-qualification-pycache")),
        (False, False, None),
    ),
)
def test_main_limits_isolated_bytecode_cache_suppression_to_qualification(
    tmp_path,
    qualification_requested,
    expected_write_disabled,
    expected_prefix,
):
    probe = (
        "import json,runpy,sys; "
        "runpy.run_path(sys.argv[1], run_name='qualification_import_probe'); "
        "print(json.dumps([sys.dont_write_bytecode, sys.pycache_prefix]))"
    )

    environment = os.environ.copy()
    environment.pop(main.QUALIFICATION_ATTEMPT_HASH_ENV, None)
    if qualification_requested:
        environment[main.QUALIFICATION_ATTEMPT_HASH_ENV] = "a" * 64

    command = [sys.executable, "-I"]
    if qualification_requested:
        command.append("-S")
    command.extend(("-c", probe, str(Path(main.__file__).resolve())))

    completed = subprocess.run(
        command,
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == [
        expected_write_disabled,
        expected_prefix,
    ]


@pytest.mark.parametrize("token", ("", "a" * 63, "A" * 64, "g" * 64))
def test_qualification_attempt_hash_rejects_malformed_value(tmp_path, token):
    environ, _attempt = _qualification_environment(tmp_path)
    environ[main.QUALIFICATION_ATTEMPT_HASH_ENV] = token

    with pytest.raises(ValueError, match="attempt-hash binding is invalid"):
        main.qualification_exit_requested(environ=environ)


def test_absent_noncombat_config_skips_runtime_import(monkeypatch, tmp_path):
    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == "spirecomm.ai.noncombat_exploration_runtime":
            raise AssertionError("default startup imported exploration runtime")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    result = initialize_noncombat_exploration_if_configured(
        environ={},
        repo_root=tmp_path,
        command=[sys.executable, "main.py"],
        python_executable=sys.executable,
        training=False,
        agent_type="optimized",
    )

    assert result is None


def test_explicit_noncombat_config_delegates_to_runtime_initializer(
    monkeypatch, tmp_path
):
    captured = {}
    sentinel = object()
    fake_module = ModuleType("spirecomm.ai.noncombat_exploration_runtime")

    def fake_initialize(**kwargs):
        captured.update(kwargs)
        return sentinel

    fake_module.initialize_noncombat_exploration_runtime = fake_initialize
    monkeypatch.setitem(
        sys.modules,
        "spirecomm.ai.noncombat_exploration_runtime",
        fake_module,
    )
    environ = {"STS_NONCOMBAT_EXPLORATION_CONFIG": str(tmp_path / "config.json")}

    result = initialize_noncombat_exploration_if_configured(
        environ=environ,
        repo_root=tmp_path,
        command=[sys.executable, "main.py", "--agent", "optimized"],
        python_executable=sys.executable,
        training=False,
        agent_type="optimized",
        isolation_hashes={"sentinel": "hash"},
    )

    assert result is sentinel
    assert captured["environ"] is environ
    assert captured["repo_root"] == Path(tmp_path)
    assert captured["training"] is False
    assert captured["agent_type"] == "optimized"
    assert captured["isolation_hashes"] == {"sentinel": "hash"}
