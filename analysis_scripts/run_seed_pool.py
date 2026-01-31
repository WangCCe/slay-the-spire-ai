#!/usr/bin/env python3
"""
Run main.py with a rotating seed pool and optional max games.

Example:
  python analysis_scripts/run_seed_pool.py --seed-pool analysis_scripts/seed_pool.txt --agent combat_rl --train
"""

import argparse
import subprocess
import sys
from pathlib import Path


def load_seed_pool(seed_pool_path):
    path = Path(seed_pool_path)
    if not path.exists():
        raise FileNotFoundError(f"Seed pool file not found: {path}")

    seeds = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        if "#" in line:
            line = line.split("#", 1)[0].strip()
        if not line:
            continue
        seeds.append(line)
    return seeds


def main():
    default_seed_pool = Path(__file__).with_name("seed_pool.txt")
    parser = argparse.ArgumentParser(description="Run training with a rotating seed pool.")
    parser.add_argument(
        "--seed-pool",
        default=str(default_seed_pool),
        help="Path to seed pool file (default: analysis_scripts/seed_pool.txt)",
    )
    parser.add_argument(
        "--max-games",
        type=int,
        default=None,
        help="Stop after N games (default: size of seed pool)",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable to run main.py (default: current python)",
    )
    parser.add_argument(
        "--agent",
        choices=["simple", "optimized", "rl", "combat_rl", "auto"],
        default="auto",
        help="Agent type to pass to main.py",
    )
    parser.add_argument(
        "--train",
        action="store_true",
        help="Enable training mode (passed to main.py)",
    )
    parser.add_argument(
        "--model",
        metavar="PATH",
        help="Model checkpoint path (passed to main.py)",
    )
    parser.add_argument(
        "--ascension",
        "-a",
        default=None,
        help="Ascension level (passed to main.py)",
    )
    parser.add_argument(
        "--elite-route",
        choices=["conservative", "aggressive"],
        default="aggressive",
        help="Elite routing mode (passed to main.py)",
    )
    parser.add_argument(
        "extra_args",
        nargs=argparse.REMAINDER,
        help="Extra args passed to main.py (prefix with --)",
    )
    args = parser.parse_args()

    seeds = load_seed_pool(args.seed_pool)
    if not seeds:
        raise SystemExit(f"Seed pool is empty: {args.seed_pool}")

    max_games = args.max_games if args.max_games is not None else len(seeds)

    main_path = Path(__file__).resolve().parents[1] / "main.py"
    cmd = [
        args.python,
        str(main_path),
        "--seed-pool",
        str(args.seed_pool),
        "--max-games",
        str(max_games),
        "--agent",
        args.agent,
        "--elite-route",
        args.elite_route,
    ]
    if args.train:
        cmd.append("--train")
    if args.model:
        cmd.extend(["--model", args.model])
    if args.ascension is not None:
        cmd.extend(["--ascension", str(args.ascension)])
    if args.extra_args:
        cmd.extend(args.extra_args)

    print("Running:", " ".join(cmd))
    raise SystemExit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
