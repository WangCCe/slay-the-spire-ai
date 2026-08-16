import sys
from types import SimpleNamespace

from scripts import run_training_batch
from scripts.run_training_batch import (
    PHASES,
    build_child_env,
    build_main_command,
    truncate_trace_files,
)


class Args:
    python = r"D:\anaconda\envs\stsai\python.exe"
    max_games = 25
    phase = "conservative"
    agent = "combat_rl"
    rl_version = "v2"
    ascension = 0
    eval = False
    epsilon = None
    model = None
    seed = None
    seed_pool = None
    expert_mix = False
    expert_mix_prob = None
    expert_mix_warmup = None
    parent_policy_anchor_weight = None
    game_dir = r"D:\SteamLibrary\steamapps\common\SlayTheSpire"
    decision_trace_path = None
    skip_decision_trace = False
    sim_divergence_trace_path = None
    skip_sim_divergence_trace = False
    noncombat_exploration_config = None


def test_conservative_batch_command_defaults_to_safe_route():
    cmd = build_main_command(Args)

    assert cmd[0] == Args.python
    assert "--agent" in cmd
    assert cmd[cmd.index("--agent") + 1] == "combat_rl"
    assert "--rl-version" in cmd
    assert cmd[cmd.index("--rl-version") + 1] == "v2"
    assert "--elite-route" in cmd
    assert cmd[cmd.index("--elite-route") + 1] == "conservative"
    assert "--max-games" in cmd
    assert cmd[cmd.index("--max-games") + 1] == "25"
    assert "--train" in cmd
    assert "--eval" not in cmd


def test_aggressive_phase_maps_to_aggressive_route():
    args = Args()
    args.phase = "aggressive"

    cmd = build_main_command(args)

    assert PHASES["aggressive"]["elite_route"] == "aggressive"
    assert cmd[cmd.index("--elite-route") + 1] == "aggressive"


def test_eval_batch_command_forwards_eval_without_train():
    args = Args()
    args.eval = True
    args.epsilon = 0.05

    cmd = build_main_command(args)

    assert "--eval" in cmd
    assert "--train" not in cmd
    assert "--epsilon" in cmd
    assert cmd[cmd.index("--epsilon") + 1] == "0.05"


def test_training_batch_forwards_parent_policy_anchor_weight():
    args = Args()
    args.model = "checkpoints/parent.pth"
    args.parent_policy_anchor_weight = 0.25

    cmd = build_main_command(args)

    assert "--parent-policy-anchor-weight" in cmd
    assert cmd[cmd.index("--parent-policy-anchor-weight") + 1] == "0.25"


def test_eval_batch_does_not_forward_parent_policy_anchor_weight():
    args = Args()
    args.eval = True
    args.model = "checkpoints/parent.pth"
    args.parent_policy_anchor_weight = 0.25

    cmd = build_main_command(args)

    assert "--parent-policy-anchor-weight" not in cmd


def test_optimized_exploration_batch_never_enables_training_or_rl_loading_flags():
    args = Args()
    args.agent = "optimized"
    args.eval = False
    args.model = "checkpoints/should-not-load.pth"
    args.epsilon = 0.5

    cmd = build_main_command(args)

    assert cmd[cmd.index("--agent") + 1] == "optimized"
    assert "--train" not in cmd
    assert "--eval" not in cmd
    assert "--rl-version" not in cmd
    assert "--model" not in cmd
    assert "--epsilon" not in cmd


def test_batch_child_env_enables_default_decision_trace(monkeypatch):
    monkeypatch.delenv("STS_DECISION_TRACE_FILE", raising=False)
    args = Args()

    env = build_child_env(args)

    assert env["STS_DECISION_TRACE_FILE"].endswith("ai_decision_trace.jsonl")


def test_batch_child_env_can_skip_decision_trace(monkeypatch):
    monkeypatch.setenv("STS_DECISION_TRACE_FILE", "existing.jsonl")
    args = Args()
    args.skip_decision_trace = True

    env = build_child_env(args)

    assert "STS_DECISION_TRACE_FILE" not in env


def test_batch_child_env_enables_default_sim_divergence_trace(monkeypatch):
    monkeypatch.delenv("STS_SIM_DIVERGENCE_TRACE_FILE", raising=False)
    args = Args()

    env = build_child_env(args)

    assert env["STS_SIM_DIVERGENCE_TRACE_FILE"].endswith("sim_divergence_trace.jsonl")


def test_batch_child_env_can_override_sim_divergence_trace_path(monkeypatch):
    monkeypatch.delenv("STS_SIM_DIVERGENCE_TRACE_FILE", raising=False)
    args = Args()
    args.sim_divergence_trace_path = r"D:\tmp\sim_trace.jsonl"

    env = build_child_env(args)

    assert env["STS_SIM_DIVERGENCE_TRACE_FILE"] == r"D:\tmp\sim_trace.jsonl"


def test_batch_child_env_can_skip_sim_divergence_trace(monkeypatch):
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", "existing_sim.jsonl")
    args = Args()
    args.skip_sim_divergence_trace = True

    env = build_child_env(args)

    assert "STS_SIM_DIVERGENCE_TRACE_FILE" not in env


def test_batch_child_env_forwards_explicit_noncombat_exploration_config(
    monkeypatch,
):
    monkeypatch.delenv("STS_NONCOMBAT_EXPLORATION_CONFIG", raising=False)
    args = Args()
    args.noncombat_exploration_config = r"D:\tmp\noncombat-exploration.json"

    env = build_child_env(args)

    assert (
        env["STS_NONCOMBAT_EXPLORATION_CONFIG"]
        == r"D:\tmp\noncombat-exploration.json"
    )


def test_run_main_command_explicitly_inherits_stdio(monkeypatch):
    captured = {}

    def fake_call(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return 0

    monkeypatch.setattr(run_training_batch.subprocess, "call", fake_call)

    result = run_training_batch.run_main_command(["python", "main.py"], {"A": "B"})

    assert result == 0
    assert captured["command"] == ["python", "main.py"]
    assert captured["kwargs"]["env"] == {"A": "B"}
    assert captured["kwargs"]["stdin"] is sys.stdin
    assert captured["kwargs"]["stdout"] is sys.stdout
    assert captured["kwargs"]["stderr"] is sys.stderr


def test_truncate_trace_files_clears_enabled_trace_paths(tmp_path):
    decision = tmp_path / "decision.jsonl"
    divergence = tmp_path / "divergence.jsonl"
    decision.write_text("decision\n", encoding="utf-8")
    divergence.write_text("divergence\n", encoding="utf-8")
    args = SimpleNamespace(truncate_traces_at_start=True, dry_run=False)

    result = truncate_trace_files(
        args,
        {
            "STS_DECISION_TRACE_FILE": str(decision),
            "STS_SIM_DIVERGENCE_TRACE_FILE": str(divergence),
        },
    )

    assert result == 0
    assert decision.read_text(encoding="utf-8") == ""
    assert divergence.read_text(encoding="utf-8") == ""


def test_truncate_trace_files_dry_run_preserves_contents(tmp_path):
    decision = tmp_path / "decision.jsonl"
    decision.write_text("decision\n", encoding="utf-8")
    args = SimpleNamespace(truncate_traces_at_start=True, dry_run=True)

    truncate_trace_files(args, {"STS_DECISION_TRACE_FILE": str(decision)})

    assert decision.read_text(encoding="utf-8") == "decision\n"


def test_truncate_trace_files_is_noop_without_explicit_flag(tmp_path):
    decision = tmp_path / "decision.jsonl"
    decision.write_text("decision\n", encoding="utf-8")
    args = SimpleNamespace(truncate_traces_at_start=False, dry_run=False)

    truncate_trace_files(args, {"STS_DECISION_TRACE_FILE": str(decision)})

    assert decision.read_text(encoding="utf-8") == "decision\n"
