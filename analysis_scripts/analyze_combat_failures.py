#!/usr/bin/env python3
"""
Analyze combat failure patterns from Slay the Spire .run files.

This script is intentionally .run-first: it works even when ai_debug.log only
has partial action traces. Optional log parsing adds coarse action hints.
"""

import argparse
import bisect
import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional


DEFAULT_RUNS_DIR = Path(r"D:\SteamLibrary\steamapps\common\SlayTheSpire\runs")
DEFAULT_LOG_PATH = Path(r"D:\SteamLibrary\steamapps\common\SlayTheSpire\ai_debug.log")
ACT1_ELITES = {"Gremlin Nob", "Lagavulin", "3 Sentries"}
ACT1_BOSSES = {"Slime Boss", "Hexaghost", "The Guardian"}
STARTER_CARDS = {
    "Strike_R",
    "Defend_R",
    "Bash",
    "Survivor",
    "Neutralize",
    "Zap",
    "Dualcast",
    "Eruption",
    "Vigilance",
}


@dataclass
class CombatEntry:
    run_file: str
    run_mtime: float
    floor: int
    enemies: str
    damage: int
    turns: int
    lethal: bool
    victory: bool
    killed_by: str
    run_floor: int


@dataclass
class RunFailure:
    run_file: str
    run_mtime: float
    victory: bool
    floor_reached: int
    killed_by: str
    combats: int
    total_damage: int
    total_turns: int
    lethal_damage: int
    lethal_turns: int
    deck_size: int
    nonstarter_cards: int
    relic_count: int
    potions_obtained: int
    potions_used: int
    items_purchased: int
    purges: int
    act1_elites: int
    boss_reached: bool


def load_run(path: Path) -> Optional[dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def collect_run_files(runs_dir: Path, character: str, count: int) -> List[Path]:
    run_root = runs_dir / character
    files = sorted(run_root.glob("*.run"), key=lambda item: item.stat().st_mtime, reverse=True)
    selected = files[:count] if count > 0 else files
    return sorted(selected, key=lambda item: item.stat().st_mtime)


def as_int(value, default: int = 0) -> int:
    try:
        return int(value or default)
    except Exception:
        return default


def potion_use_count(run: dict) -> int:
    usage = run.get("potions_floor_usage")
    if usage is None:
        usage = run.get("potion_use_per_floor")
    usage = usage or []
    if isinstance(usage, list):
        return len(usage)
    return 0


def parse_trace_potion_usage(trace_path: Path, run_files: List[Path]) -> Dict[str, int]:
    if not trace_path.exists() or not run_files:
        return {}

    starts = []
    names = []
    for run_file in sorted(run_files, key=lambda item: int(item.stem)):
        try:
            starts.append(int(run_file.stem))
            names.append(run_file.name)
        except ValueError:
            continue
    if not starts:
        return {}

    usage: Dict[str, int] = defaultdict(int)
    with trace_path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            if '"PotionAction"' not in line or '"unix_time"' not in line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            action = row.get("action") or {}
            if action.get("type") != "PotionAction":
                continue
            unix_time = row.get("unix_time")
            try:
                unix_time = float(unix_time)
            except Exception:
                continue
            if unix_time < starts[0]:
                continue
            index = bisect.bisect_right(starts, unix_time) - 1
            if index >= 0:
                usage[names[index]] += 1
    return dict(usage)


def summarize_run(path: Path, run: dict, *, trace_potions_used: int = 0) -> RunFailure:
    damage_entries = run.get("damage_taken") or []
    total_damage = sum(as_int(entry.get("damage")) for entry in damage_entries)
    total_turns = sum(as_int(entry.get("turns")) for entry in damage_entries)
    killed_by = str(run.get("killed_by") or "UNKNOWN")
    floor_reached = as_int(run.get("floor_reached"))
    victory = bool(run.get("victory", False))

    lethal = find_lethal_combat(run)
    deck = run.get("master_deck") or []
    nonstarter_cards = sum(1 for card in deck if str(card) not in STARTER_CARDS)
    path_taken = [str(symbol) for symbol in (run.get("path_taken") or [])]

    return RunFailure(
        run_file=path.name,
        run_mtime=path.stat().st_mtime,
        victory=victory,
        floor_reached=floor_reached,
        killed_by=killed_by,
        combats=len(damage_entries),
        total_damage=total_damage,
        total_turns=total_turns,
        lethal_damage=as_int(lethal.get("damage")) if lethal else 0,
        lethal_turns=as_int(lethal.get("turns")) if lethal else 0,
        deck_size=len(deck),
        nonstarter_cards=nonstarter_cards,
        relic_count=len(run.get("relics") or []),
        potions_obtained=len(run.get("potions_obtained") or []),
        potions_used=max(potion_use_count(run), trace_potions_used),
        items_purchased=len(run.get("items_purchased") or []),
        purges=len(run.get("items_purged") or []),
        act1_elites=sum(1 for symbol in path_taken[:16] if symbol == "E"),
        boss_reached=floor_reached >= 16 or killed_by in ACT1_BOSSES,
    )


def find_lethal_combat(run: dict) -> Optional[dict]:
    entries = run.get("damage_taken") or []
    if not entries or run.get("victory"):
        return None

    killed_by = str(run.get("killed_by") or "")
    floor_reached = as_int(run.get("floor_reached"))
    for entry in reversed(entries):
        enemies = str(entry.get("enemies") or "")
        floor = as_int(entry.get("floor"))
        if enemies == killed_by or floor == floor_reached:
            return entry
    return entries[-1]


def iter_combats(path: Path, run: dict) -> Iterable[CombatEntry]:
    lethal = find_lethal_combat(run)
    killed_by = str(run.get("killed_by") or "UNKNOWN")
    run_floor = as_int(run.get("floor_reached"))
    victory = bool(run.get("victory", False))
    for entry in run.get("damage_taken") or []:
        yield CombatEntry(
            run_file=path.name,
            run_mtime=path.stat().st_mtime,
            floor=as_int(entry.get("floor")),
            enemies=str(entry.get("enemies") or "UNKNOWN"),
            damage=as_int(entry.get("damage")),
            turns=as_int(entry.get("turns")),
            lethal=(entry is lethal),
            victory=victory,
            killed_by=killed_by,
            run_floor=run_floor,
        )


def rate(numerator: int, denominator: int) -> float:
    return (numerator / denominator * 100.0) if denominator else 0.0


def avg(values: Iterable[int]) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def parse_log_action_hints(log_path: Path, tail_lines: int) -> Dict[str, int]:
    if tail_lines <= 0 or not log_path.exists():
        return {"log_found": 0}

    try:
        lines = log_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return {"log_found": 0}

    lines = lines[-tail_lines:]
    patterns = {
        "play_card_actions": re.compile(r"Got action: PlayCardAction|RL returned: PlayCardAction"),
        "end_turn_actions": re.compile(r"Got action: EndTurnAction|RL returned: EndTurnAction"),
        "potion_actions": re.compile(r"Got action: PotionAction|RL returned: PotionAction"),
        "turn_ends_with_energy": re.compile(r"\[TURN_END\].*energy_remaining=[1-9]"),
        "invalid_commands": re.compile(r"Invalid command|command error|Game error", re.IGNORECASE),
        "rl_fallbacks": re.compile(r"falling back|RL agent failed", re.IGNORECASE),
    }
    counts = {"log_found": 1, "lines_analyzed": len(lines)}
    for name, pattern in patterns.items():
        counts[name] = sum(1 for line in lines if pattern.search(line))
    return counts


def make_report(run_failures: List[RunFailure], combats: List[CombatEntry], log_hints: Dict[str, int]) -> dict:
    deaths = [run for run in run_failures if not run.victory]
    lethal_combats = [combat for combat in combats if combat.lethal]
    total = len(run_failures)
    enemy_stats = defaultdict(lambda: {"combats": 0, "deaths": 0, "damage": 0, "turns": 0})

    for combat in combats:
        stat = enemy_stats[combat.enemies]
        stat["combats"] += 1
        stat["damage"] += combat.damage
        stat["turns"] += combat.turns
        if combat.lethal:
            stat["deaths"] += 1

    top_enemies = []
    for enemy, stat in enemy_stats.items():
        top_enemies.append(
            {
                "enemy": enemy,
                "combats": stat["combats"],
                "deaths": stat["deaths"],
                "avg_damage": stat["damage"] / stat["combats"] if stat["combats"] else 0.0,
                "avg_turns": stat["turns"] / stat["combats"] if stat["combats"] else 0.0,
            }
        )
    top_enemies.sort(key=lambda item: (item["deaths"], item["avg_damage"]), reverse=True)

    potionless_deaths = sum(1 for run in deaths if run.potions_obtained > 0 and run.potions_used == 0)
    low_growth_deaths = sum(1 for run in deaths if run.floor_reached >= 8 and run.nonstarter_cards <= 2)
    boss_deaths = sum(1 for run in deaths if run.killed_by in ACT1_BOSSES)
    elite_deaths = sum(1 for run in deaths if run.killed_by in ACT1_ELITES)

    return {
        "overall": {
            "runs": total,
            "wins": sum(1 for run in run_failures if run.victory),
            "win_rate": rate(sum(1 for run in run_failures if run.victory), total),
            "avg_floor": avg(run.floor_reached for run in run_failures),
            "max_floor": max((run.floor_reached for run in run_failures), default=0),
            "boss_reach_rate": rate(sum(1 for run in run_failures if run.boss_reached), total),
            "avg_combats": avg(run.combats for run in run_failures),
            "avg_damage_per_run": avg(run.total_damage for run in run_failures),
            "avg_turns_per_run": avg(run.total_turns for run in run_failures),
        },
        "death_profile": {
            "top_killed_by": Counter(run.killed_by for run in deaths).most_common(12),
            "boss_deaths": boss_deaths,
            "elite_deaths": elite_deaths,
            "normal_deaths": len(deaths) - boss_deaths - elite_deaths,
            "avg_lethal_damage": avg(run.lethal_damage for run in deaths),
            "avg_lethal_turns": avg(run.lethal_turns for run in deaths),
            "potionless_deaths_after_obtaining_potions": potionless_deaths,
            "low_growth_deaths_floor8_plus": low_growth_deaths,
        },
        "growth_profile": {
            "avg_deck_size_at_end": avg(run.deck_size for run in run_failures),
            "avg_nonstarter_cards": avg(run.nonstarter_cards for run in run_failures),
            "avg_relics": avg(run.relic_count for run in run_failures),
            "avg_potions_obtained": avg(run.potions_obtained for run in run_failures),
            "avg_potions_used": avg(run.potions_used for run in run_failures),
            "avg_items_purchased": avg(run.items_purchased for run in run_failures),
            "avg_purges": avg(run.purges for run in run_failures),
            "avg_act1_elites": avg(run.act1_elites for run in run_failures),
        },
        "enemy_profile": top_enemies[:20],
        "lethal_combats": [asdict(combat) for combat in lethal_combats[-20:]],
        "log_action_hints": log_hints,
    }


def print_report(report: dict) -> None:
    overall = report["overall"]
    death = report["death_profile"]
    growth = report["growth_profile"]

    print("=" * 88)
    print("COMBAT FAILURE DIAGNOSTICS")
    print("=" * 88)
    print(
        "Runs={runs} Wins={wins} WinRate={win_rate:.1f}% "
        "AvgFloor={avg_floor:.2f} MaxFloor={max_floor} BossReach={boss_reach_rate:.1f}%".format(
            **overall
        )
    )
    print(
        "AvgCombats={avg_combats:.2f} AvgDamageRun={avg_damage_per_run:.1f} "
        "AvgTurnsRun={avg_turns_per_run:.1f}".format(**overall)
    )

    print("\nDeath Profile")
    print("-" * 88)
    print(
        f"Normal={death['normal_deaths']} Elite={death['elite_deaths']} Boss={death['boss_deaths']} "
        f"AvgLethalDamage={death['avg_lethal_damage']:.1f} AvgLethalTurns={death['avg_lethal_turns']:.1f}"
    )
    print(
        "Potionless deaths after obtaining potions: "
        f"{death['potionless_deaths_after_obtaining_potions']}"
    )
    print(f"Low-growth deaths floor>=8 (<=2 nonstarter cards): {death['low_growth_deaths_floor8_plus']}")
    for name, count in death["top_killed_by"]:
        print(f"  {name}: {count}")

    print("\nGrowth Profile")
    print("-" * 88)
    print(
        "Deck={avg_deck_size_at_end:.1f} NonStarter={avg_nonstarter_cards:.1f} "
        "Relics={avg_relics:.1f} PotionsUsed={avg_potions_used:.2f}/Obtained={avg_potions_obtained:.2f} "
        "Purchases={avg_items_purchased:.2f} Purges={avg_purges:.2f} Act1Elites={avg_act1_elites:.2f}".format(
            **growth
        )
    )

    print("\nEnemy Profile")
    print("-" * 88)
    print(f"{'Enemy':<24} {'Combats':>7} {'Deaths':>6} {'AvgDmg':>8} {'AvgTurns':>8}")
    for item in report["enemy_profile"][:12]:
        print(
            f"{item['enemy']:<24} {item['combats']:>7} {item['deaths']:>6} "
            f"{item['avg_damage']:>8.1f} {item['avg_turns']:>8.1f}"
        )

    hints = report.get("log_action_hints") or {}
    if hints.get("log_found"):
        print("\nLog Action Hints")
        print("-" * 88)
        for key in (
            "lines_analyzed",
            "play_card_actions",
            "end_turn_actions",
            "potion_actions",
            "turn_ends_with_energy",
            "invalid_commands",
            "rl_fallbacks",
        ):
            print(f"  {key}: {hints.get(key, 0)}")
    print("=" * 88)


def write_csv(path: Path, run_failures: List[RunFailure], combats: List[CombatEntry]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["kind"] + list(asdict(run_failures[0]).keys()) if run_failures else ["kind"],
            extrasaction="ignore",
        )
        writer.writeheader()
        for run in run_failures:
            row = {"kind": "run"}
            row.update(asdict(run))
            writer.writerow(row)

    combat_path = path.with_name(path.stem + "_combats.csv")
    with combat_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(combats[0]).keys()) if combats else ["run_file"])
        writer.writeheader()
        for combat in combats:
            writer.writerow(asdict(combat))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze combat failure patterns from .run files.")
    parser.add_argument("--runs-dir", default=str(DEFAULT_RUNS_DIR), help="Path to runs directory.")
    parser.add_argument("--character", default="IRONCLAD", help="Character folder under runs/.")
    parser.add_argument("--count", type=int, default=100, help="Most recent run files to include; 0 = all.")
    parser.add_argument("--log-path", default=str(DEFAULT_LOG_PATH), help="Optional ai_debug.log path.")
    parser.add_argument("--tail-lines", type=int, default=200000, help="Log tail lines for action hints.")
    parser.add_argument("--no-log", action="store_true", help="Skip ai_debug.log parsing.")
    parser.add_argument(
        "--decision-trace",
        help="Optional ai_decision_trace_clean.jsonl path used to backfill PotionAction counts.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON report.")
    parser.add_argument("--csv-out", help="Write run and combat CSV files with this base path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_files = collect_run_files(Path(args.runs_dir), args.character, args.count)
    if not run_files:
        print("No run files found.")
        return 1

    run_failures: List[RunFailure] = []
    combats: List[CombatEntry] = []
    trace_potion_usage = (
        parse_trace_potion_usage(Path(args.decision_trace), run_files)
        if args.decision_trace
        else {}
    )
    for run_file in run_files:
        data = load_run(run_file)
        if not data:
            continue
        run_failures.append(
            summarize_run(
                run_file,
                data,
                trace_potions_used=trace_potion_usage.get(run_file.name, 0),
            )
        )
        combats.extend(iter_combats(run_file, data))

    log_hints = {"log_found": 0} if args.no_log else parse_log_action_hints(Path(args.log_path), args.tail_lines)
    report = make_report(run_failures, combats, log_hints)

    if args.csv_out:
        write_csv(Path(args.csv_out), run_failures, combats)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
