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

    cmd = [
        args.python,
        str(main_path),
        "--agent",
        args.agent,
        "--train",
        "--rl-version",
        args.rl_version,
        "--elite-route",
        phase["elite_route"],
        "--max-games",
        str(args.max_games),
        "--ascension",
        str(args.ascension),
    ]

    if args.model:
        cmd.extend(["--model", args.model])
    if args.seed:
        cmd.extend(["--seed", args.seed])
    if args.seed_pool:
        cmd.extend(["--seed-pool", args.seed_pool])
    if args.expert_mix:
        cmd.append("--expert-mix")
    if args.expert_mix_prob is not None:
        cmd.extend(["--expert-mix-prob", str(args.expert_mix_prob)])
    if args.expert_mix_warmup is not None:
        cmd.extend(["--expert-mix-warmup", str(args.expert_mix_warmup)])

    return cmd


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
        choices=["rl", "combat_rl"],
        default="combat_rl",
        help="Training agent type.",
    )
    parser.add_argument(
        "--rl-version",
        choices=["v1", "v2"],
        default="v2",
        help="RL action/observation space version.",
    )
    parser.add_argument("--ascension", "-a", type=int, default=0)
    parser.add_argument("--model", help="Optional checkpoint path.")
    parser.add_argument("--seed", help="Optional fixed seed.")
    parser.add_argument("--seed-pool", help="Optional seed pool path.")
    parser.add_argument("--expert-mix", action="store_true")
    parser.add_argument("--expert-mix-prob", type=float, default=None)
    parser.add_argument("--expert-mix-warmup", type=int, default=None)

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
        "--truncate-log-after-backup",
        action="store_true",
        help="Clear the active log after copying it. Use only between batches.",
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
    print_restart_guidance(args)

    if args.dry_run:
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

    result = subprocess.call(main_command)

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
