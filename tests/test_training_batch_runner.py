from scripts.run_training_batch import build_main_command, PHASES


class Args:
    python = r"D:\anaconda\envs\stsai\python.exe"
    max_games = 25
    phase = "conservative"
    agent = "combat_rl"
    rl_version = "v2"
    ascension = 0
    model = None
    seed = None
    seed_pool = None
    expert_mix = False
    expert_mix_prob = None
    expert_mix_warmup = None


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


def test_aggressive_phase_maps_to_aggressive_route():
    args = Args()
    args.phase = "aggressive"

    cmd = build_main_command(args)

    assert PHASES["aggressive"]["elite_route"] == "aggressive"
    assert cmd[cmd.index("--elite-route") + 1] == "aggressive"
