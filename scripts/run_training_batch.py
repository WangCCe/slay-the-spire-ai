#!/usr/bin/env python3
"""
Launch a bounded RL training batch with curriculum defaults.

This script is safe to use as a Communication Mod command wrapper because all
wrapper messages go to stderr and the child process inherits stdin/stdout.

Examples:
  python scripts/run_training_batch.py --dry-run
  python scripts/run_training_batch.py --max-games 100 --phase conservative
  python scripts/run_training_batch.py --phase aggressive --seed-pool analysis_scripts/seed_pool.txt
"""

import argparse
import glob
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


DEFAULT_WINDOWS_PYTHON = r"D:\anaconda\envs\stsai\python.exe"
DEFAULT_GAME_DIR = r"D:\SteamLibrary\steamapps\common\SlayTheSpire"


PHASES = {
    "conservative": {
        "elite_route": "conservative",
        "description": "Safer Act 1 route curriculum for recovering from early elite walls.",
    },
    "mixed": {
        "elite_route": "conservative",
        "description": "Reserved transition phase; starts conservative until promotion metrics are met.",
    },
    "aggressive": {
        "elite_route": "aggressive",
        "description": "High-risk route curriculum for elite exposure after checkpoint promotion.",
    },
}


def build_main_command(args):
    repo_root = Path(__file__).resolve().parents[1]
    main_path = repo_root / "main.py"
    phase = PHASES[args.phase]
    eval_mode = bool(getattr(args, "eval", False))

    cmd = [
        args.python,
        str(main_path),
        "--agent",
        args.agent,
        "--elite-route",
        phase["elite_route"],
        "--max-games",
        str(args.max_games),
        "--ascension",
        str(args.ascension),
    ]

    is_rl_agent = args.agent in {"rl", "combat_rl"}
    if is_rl_agent:
        cmd.extend(["--rl-version", args.rl_version])
        if eval_mode:
            cmd.append("--eval")
        else:
            cmd.append("--train")

        epsilon = getattr(args, "epsilon", None)
        if epsilon is not None:
            cmd.extend(["--epsilon", str(epsilon)])
        if args.model:
            cmd.extend(["--model", args.model])
    if args.seed:
        cmd.extend(["--seed", args.seed])
    if args.seed_pool:
        cmd.extend(["--seed-pool", args.seed_pool])
    if is_rl_agent and args.expert_mix and not eval_mode:
        cmd.append("--expert-mix")
    if is_rl_agent and args.expert_mix_prob is not None and not eval_mode:
        cmd.extend(["--expert-mix-prob", str(args.expert_mix_prob)])
    if is_rl_agent and args.expert_mix_warmup is not None and not eval_mode:
        cmd.extend(["--expert-mix-warmup", str(args.expert_mix_warmup)])
    anchor_weight = getattr(args, "parent_policy_anchor_weight", None)
    if is_rl_agent and anchor_weight is not None and not eval_mode:
        cmd.extend(["--parent-policy-anchor-weight", str(anchor_weight)])

    return cmd


def build_child_env(args):
    env = os.environ.copy()
    if getattr(args, "skip_decision_trace", False):
        env.pop("STS_DECISION_TRACE_FILE", None)
    else:
        trace_path = getattr(args, "decision_trace_path", None)
        if not trace_path:
            trace_path = str(Path(args.game_dir) / "ai_decision_trace.jsonl")
        env["STS_DECISION_TRACE_FILE"] = trace_path

    if getattr(args, "skip_sim_divergence_trace", False):
        env.pop("STS_SIM_DIVERGENCE_TRACE_FILE", None)
    else:
        sim_trace_path = getattr(args, "sim_divergence_trace_path", None)
        if not sim_trace_path:
            sim_trace_path = str(Path(args.game_dir) / "sim_divergence_trace.jsonl")
        env["STS_SIM_DIVERGENCE_TRACE_FILE"] = sim_trace_path
    exploration_config = getattr(args, "noncombat_exploration_config", None)
    if exploration_config:
        env["STS_NONCOMBAT_EXPLORATION_CONFIG"] = str(exploration_config)
    card_shadow_config = getattr(args, "card_uplift_shadow_config", None)
    card_canary_config = getattr(args, "card_uplift_canary_config", None)
    card_evaluation_config = getattr(args, "card_uplift_evaluation_config", None)
    configured = (
        card_shadow_config,
        card_canary_config,
        card_evaluation_config,
    )
    if sum(bool(value) for value in configured) > 1:
        raise ValueError("card uplift configs are mutually exclusive")
    if card_shadow_config:
        env["STS_CARD_UPLIFT_SHADOW_CONFIG"] = str(card_shadow_config)
    if card_canary_config:
        env["STS_CARD_UPLIFT_CANARY_CONFIG"] = str(card_canary_config)
    if card_evaluation_config:
        env["STS_CARD_UPLIFT_EVALUATION_CONFIG"] = str(card_evaluation_config)
    return env


def run_maintenance(args):
    repo_root = Path(__file__).resolve().parents[1]
    archive_script = repo_root / "analysis_scripts" / "archive_old_runs.py"
    command = [
        args.python,
        str(archive_script),
        "--game-dir",
        args.game_dir,
        "--character",
        args.character,
        "--keep",
        str(args.keep_runs),
    ]
    if args.dry_run:
        command.append("--dry-run")

    print("[training-batch] maintenance:", " ".join(command), file=sys.stderr)
    if args.dry_run:
        return 0
    return subprocess.call(command)


def backup_latest_checkpoints(args):
    checkpoint_dir = Path(args.checkpoint_dir)
    backup_dir = Path(args.checkpoint_backup_dir)
    patterns = ["rl_combat_model_ep*.pth", "rl_model_ep*.pth"]
    copied = 0

    for pattern in patterns:
        matches = sorted(
            glob.glob(str(checkpoint_dir / pattern)),
            key=lambda path: Path(path).stat().st_mtime,
            reverse=True,
        )
        if not matches:
            continue

        source = Path(matches[0])
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        destination = backup_dir / f"{source.name}.{timestamp}.bak"
        print(f"[training-batch] checkpoint backup: {source} -> {destination}", file=sys.stderr)
        if not args.dry_run:
            backup_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(source), str(destination))
        copied += 1

    if copied == 0:
        print("[training-batch] checkpoint backup: no checkpoints found", file=sys.stderr)
    return 0


def backup_log_file(args):
    log_path = Path(args.log_path)
    if not log_path.exists():
        print(f"[training-batch] log backup: log not found: {log_path}", file=sys.stderr)
        return 0

    backup_dir = Path(args.log_backup_dir)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    destination = backup_dir / f"{log_path.name}.{timestamp}.bak"
    print(f"[training-batch] log backup: {log_path} -> {destination}", file=sys.stderr)
    if not args.dry_run:
        backup_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(log_path), str(destination))
        if args.truncate_log_after_backup:
            log_path.write_text("", encoding="utf-8")
            print(f"[training-batch] log rotation: truncated {log_path}", file=sys.stderr)
    return 0


def truncate_trace_files(args, child_env):
    """Start a bounded batch with fresh trace files when explicitly requested."""
    if not args.truncate_traces_at_start:
        return 0

    trace_paths = (
        ("decision", child_env.get("STS_DECISION_TRACE_FILE")),
        ("sim divergence", child_env.get("STS_SIM_DIVERGENCE_TRACE_FILE")),
    )
    seen = set()
    for label, raw_path in trace_paths:
        if not raw_path:
            continue
        path = Path(raw_path)
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if not path.exists():
            print(f"[training-batch] {label} trace reset: not found: {path}", file=sys.stderr)
            continue
        size = path.stat().st_size
        print(
            f"[training-batch] {label} trace reset: {path} ({size} bytes)",
            file=sys.stderr,
        )
        if not args.dry_run:
            path.write_text("", encoding="utf-8")
    return 0


def run_post_analysis(args):
    repo_root = Path(__file__).resolve().parents[1]
    analysis_script = repo_root / "analysis_scripts" / "analyze_training_plateau.py"
    runs_dir = str(Path(args.game_dir) / "runs")
    command = [
        args.python,
        str(analysis_script),
        "--runs-dir",
        runs_dir,
        "--character",
        args.character,
        "--count",
        str(args.analysis_count),
        "--bucket",
        str(args.analysis_bucket),
    ]

    print("[training-batch] post-analysis:", " ".join(command), file=sys.stderr)
    if args.dry_run:
        return 0
    return subprocess.call(command)


def run_main_command(command, env):
    """Run the AI child with explicit stdio inheritance for CommunicationMod pipes."""
    return subprocess.call(
        command,
        env=env,
        stdin=sys.stdin,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )


def print_restart_guidance(args):
    if not args.restart_guidance:
        return
    print("[training-batch] restart guidance:", file=sys.stderr)
    print(
        "  If the game UI becomes sluggish, close Slay the Spire and ModTheSpire, "
        "then start the next bounded batch after the game returns to the main menu.",
        file=sys.stderr,
    )
    print(
        "  Keep batches small enough to inspect plateau diagnostics before raising route risk.",
        file=sys.stderr,
    )


def parse_args():
    parser = argparse.ArgumentParser(description="Run a bounded RL training batch.")
    parser.add_argument(
        "--python",
        default=DEFAULT_WINDOWS_PYTHON,
        help="Python executable for live gameplay training.",
    )
    parser.add_argument(
        "--max-games",
        type=int,
        default=100,
        help="Stop after N games.",
    )
    parser.add_argument(
        "--phase",
        choices=sorted(PHASES),
        default="conservative",
        help="Curriculum phase.",
    )
    parser.add_argument(
        "--agent",
        choices=["optimized", "rl", "combat_rl"],
        default="combat_rl",
        help="Agent type; optimized runs a bounded no-training evaluation.",
    )
    parser.add_argument(
        "--rl-version",
        choices=["v1", "v2"],
        default="v2",
        help="RL action/observation space version.",
    )
    parser.add_argument("--ascension", "-a", type=int, default=0)
    parser.add_argument(
        "--eval",
        action="store_true",
        help="Run a bounded low-exploration validation batch instead of training.",
    )
    parser.add_argument(
        "--epsilon",
        type=float,
        default=None,
        help="Forwarded RL inference exploration probability for --eval.",
    )
    parser.add_argument("--model", help="Optional checkpoint path.")
    parser.add_argument("--seed", help="Optional fixed seed.")
    parser.add_argument("--seed-pool", help="Optional seed pool path.")
    parser.add_argument("--expert-mix", action="store_true")
    parser.add_argument("--expert-mix-prob", type=float, default=None)
    parser.add_argument("--expert-mix-warmup", type=int, default=None)
    parser.add_argument("--parent-policy-anchor-weight", type=float, default=None)

    parser.add_argument("--game-dir", default=DEFAULT_GAME_DIR)
    parser.add_argument("--character", default="IRONCLAD")
    parser.add_argument("--keep-runs", type=int, default=1000)
    parser.add_argument("--checkpoint-dir", default="checkpoints")
    parser.add_argument(
        "--checkpoint-backup-dir",
        default=str(Path("checkpoints_archive") / "training_batches"),
    )
    parser.add_argument("--skip-checkpoint-backup", action="store_true")
    parser.add_argument(
        "--log-path",
        default=str(Path(DEFAULT_GAME_DIR) / "ai_debug.log"),
        help="AI debug log to preserve before a batch.",
    )
    parser.add_argument(
        "--log-backup-dir",
        default=str(Path(DEFAULT_GAME_DIR) / "logs_archive"),
        help="Directory for copied log backups.",
    )
    parser.add_argument("--skip-log-backup", action="store_true")
    parser.add_argument(
        "--decision-trace-path",
        default=None,
        help="JSONL path for compact combat decision traces during this batch.",
    )
    parser.add_argument(
        "--skip-decision-trace",
        action="store_true",
        help="Do not enable STS_DECISION_TRACE_FILE for the child process.",
    )
    parser.add_argument(
        "--sim-divergence-trace-path",
        default=None,
        help="JSONL path for compact expected-vs-actual combat simulation divergence traces.",
    )
    parser.add_argument(
        "--skip-sim-divergence-trace",
        action="store_true",
        help="Do not enable STS_SIM_DIVERGENCE_TRACE_FILE for the child process.",
    )
    parser.add_argument(
        "--noncombat-exploration-config",
        default=None,
        help="Explicit configuration passed as STS_NONCOMBAT_EXPLORATION_CONFIG.",
    )
    parser.add_argument(
        "--card-uplift-shadow-config",
        default=None,
        help="Explicit configuration passed as STS_CARD_UPLIFT_SHADOW_CONFIG.",
    )
    parser.add_argument(
        "--card-uplift-canary-config",
        default=None,
        help="Explicit configuration passed as STS_CARD_UPLIFT_CANARY_CONFIG.",
    )
    parser.add_argument(
        "--card-uplift-evaluation-config",
        default=None,
        help="Explicit configuration passed as STS_CARD_UPLIFT_EVALUATION_CONFIG.",
    )
    parser.add_argument(
        "--truncate-log-after-backup",
        action="store_true",
        help="Clear the active log after copying it. Use only between batches.",
    )
    parser.add_argument(
        "--truncate-traces-at-start",
        action="store_true",
        help=(
            "Discard existing enabled decision/sim trace contents before the batch. "
            "Use only after preserving any required summaries."
        ),
    )
    parser.add_argument("--skip-maintenance", action="store_true")
    parser.add_argument(
        "--restart-guidance",
        action="store_true",
        help="Print manual long-session restart guidance before/after a batch.",
    )
    parser.add_argument("--skip-post-analysis", action="store_true")
    parser.add_argument("--analysis-count", type=int, default=500)
    parser.add_argument("--analysis-bucket", type=int, default=50)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without launching training or moving files.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    phase = PHASES[args.phase]
    main_command = build_main_command(args)

    print(f"[training-batch] phase={args.phase}: {phase['description']}", file=sys.stderr)
    print("[training-batch] main:", " ".join(main_command), file=sys.stderr)
    child_env = build_child_env(args)
    trace_path = child_env.get("STS_DECISION_TRACE_FILE")
    if trace_path:
        print(f"[training-batch] decision trace: {trace_path}", file=sys.stderr)
    sim_trace_path = child_env.get("STS_SIM_DIVERGENCE_TRACE_FILE")
    if sim_trace_path:
        print(f"[training-batch] sim divergence trace: {sim_trace_path}", file=sys.stderr)
    exploration_config = child_env.get("STS_NONCOMBAT_EXPLORATION_CONFIG")
    if exploration_config:
        print(
            f"[training-batch] noncombat exploration config: {exploration_config}",
            file=sys.stderr,
        )
    card_shadow_config = child_env.get("STS_CARD_UPLIFT_SHADOW_CONFIG")
    if card_shadow_config:
        print(
            f"[training-batch] card uplift shadow config: {card_shadow_config}",
            file=sys.stderr,
        )
    card_canary_config = child_env.get("STS_CARD_UPLIFT_CANARY_CONFIG")
    if card_canary_config:
        print(
            f"[training-batch] card uplift canary config: {card_canary_config}",
            file=sys.stderr,
        )
    card_evaluation_config = child_env.get("STS_CARD_UPLIFT_EVALUATION_CONFIG")
    if card_evaluation_config:
        print(
            f"[training-batch] card uplift evaluation config: {card_evaluation_config}",
            file=sys.stderr,
        )
    print_restart_guidance(args)

    if args.dry_run:
        truncate_trace_files(args, child_env)
        if not args.skip_checkpoint_backup:
            backup_latest_checkpoints(args)
        if not args.skip_log_backup:
            backup_log_file(args)
        if not args.skip_maintenance:
            run_maintenance(args)
        if not args.skip_post_analysis:
            run_post_analysis(args)
        return 0

    if not args.skip_checkpoint_backup:
        backup_latest_checkpoints(args)
    if not args.skip_log_backup:
        backup_log_file(args)
    truncate_trace_files(args, child_env)

    result = run_main_command(main_command, child_env)

    maintenance_result = 0
    if not args.skip_maintenance:
        maintenance_result = run_maintenance(args)

    analysis_result = 0
    if not args.skip_post_analysis:
        analysis_result = run_post_analysis(args)

    print_restart_guidance(args)

    if result != 0:
        return result
    if maintenance_result != 0:
        return maintenance_result
    return analysis_result


if __name__ == "__main__":
    raise SystemExit(main())
