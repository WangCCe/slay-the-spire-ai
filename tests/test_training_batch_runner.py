from scripts.run_training_batch import build_child_env, build_main_command, PHASES


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
    game_dir = r"D:\SteamLibrary\steamapps\common\SlayTheSpire"
    decision_trace_path = None
    skip_decision_trace = False
    sim_divergence_trace_path = None
    skip_sim_divergence_trace = False


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
