#!/usr/bin/env python3
"""
Archive old Slay the Spire run files to reduce runs/ directory size.

Usage:
  python analysis_scripts/archive_old_runs.py
  python analysis_scripts/archive_old_runs.py --keep 2000
  python analysis_scripts/archive_old_runs.py --character IRONCLAD
  python analysis_scripts/archive_old_runs.py --dry-run
"""

import argparse
import os
import shutil
from pathlib import Path


DEFAULT_GAME_DIR = r"D:\SteamLibrary\steamapps\common\SlayTheSpire"


def gather_run_files(runs_dir: Path, keep: int):
    run_files = sorted(runs_dir.glob("*.run"), key=lambda p: p.stat().st_mtime)
    if keep <= 0:
        return run_files, []
    if len(run_files) <= keep:
        return [], run_files
    return run_files[:-keep], run_files[-keep:]


def archive_runs(runs_dir: Path, archive_dir: Path, keep: int, dry_run: bool):
    to_archive, to_keep = gather_run_files(runs_dir, keep)
    archived = 0
    skipped = 0
    total_bytes = 0

    if not to_archive:
        return archived, skipped, total_bytes, len(to_keep)

    if not dry_run:
        archive_dir.mkdir(parents=True, exist_ok=True)

    for path in to_archive:
        try:
            size = path.stat().st_size
            if dry_run:
                archived += 1
                total_bytes += size
                continue
            dest = archive_dir / path.name
            shutil.move(str(path), str(dest))
            archived += 1
            total_bytes += size
        except Exception:
            skipped += 1

    return archived, skipped, total_bytes, len(to_keep)


def main():
    parser = argparse.ArgumentParser(
        description="Archive old run files to reduce runs/ directory size."
    )
    parser.add_argument(
        "--game-dir",
        default=DEFAULT_GAME_DIR,
        help="Slay the Spire game directory",
    )
    parser.add_argument(
        "--character",
        default="ALL",
        help="Character folder to archive (IRONCLAD/THE_SILENT/DEFECT/WATCHER/DAILY) or ALL",
    )
    parser.add_argument(
        "--keep",
        type=int,
        default=3000,
        help="Keep newest N runs per character (default: 3000)",
    )
    parser.add_argument(
        "--archive-dir",
        default=None,
        help="Archive directory (default: <game-dir>/runs_archive)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be archived without moving files",
    )
    args = parser.parse_args()

    runs_root = Path(args.game_dir) / "runs"
    if not runs_root.exists():
        raise FileNotFoundError(f"Runs directory not found: {runs_root}")

    archive_root = (
        Path(args.archive_dir) if args.archive_dir else Path(args.game_dir) / "runs_archive"
    )

    if args.character.upper() == "ALL":
        characters = [
            p.name for p in runs_root.iterdir() if p.is_dir()
        ]
    else:
        characters = [args.character]

    total_archived = 0
    total_skipped = 0
    total_bytes = 0

    print(f"Runs root: {runs_root}")
    print(f"Archive root: {archive_root}")
    print(f"Keep per character: {args.keep}")
    print(f"Dry run: {args.dry_run}")
    print("-" * 60)

    for character in characters:
        runs_dir = runs_root / character
        if not runs_dir.exists():
            print(f"[SKIP] {character}: directory not found")
            continue

        archive_dir = archive_root / character
        archived, skipped, bytes_moved, kept = archive_runs(
            runs_dir, archive_dir, args.keep, args.dry_run
        )
        total_archived += archived
        total_skipped += skipped
        total_bytes += bytes_moved
        print(
            f"[{character}] archived={archived} skipped={skipped} kept={kept} bytes={bytes_moved}"
        )

    print("-" * 60)
    print(
        f"Total archived={total_archived} skipped={total_skipped} bytes={total_bytes}"
    )


if __name__ == "__main__":
    main()
