import builtins
import sys
from pathlib import Path
from types import ModuleType

import main
from main import (
    create_ready_coordinator,
    initialize_noncombat_exploration_if_configured,
    initialize_pre_agent_runtime,
    initialize_study_handshake_if_configured,
    is_study_handshake_configured,
    is_unrecoverable_run_error,
)
from spirecomm.communication import study_handshake


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
