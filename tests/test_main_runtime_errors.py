import builtins
import sys
from pathlib import Path
from types import ModuleType

import main
from main import (
    initialize_noncombat_exploration_if_configured,
    is_unrecoverable_run_error,
)


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
