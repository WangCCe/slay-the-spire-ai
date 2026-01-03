"""
Command-line tool for analyzing AI game statistics.

Provides various analysis modes for evaluating AI performance.
"""

import argparse
import sys
from typing import List
from spirecomm.ai.statistics import GameStatistics


def analyze_recent(stats: GameStatistics, n: int):
    """
    Show statistics for recent N games.

    Args:
        stats: GameStatistics instance
        n: Number of recent games to analyze
    """
    games = stats.get_recent_games(n)

    if not games:
        print(f"No games found in history.")
        return

    print(f"\n{'=' * 80}")
    print(f"RECENT {n} GAMES")
    print(f"{'=' * 80}\n")

    wins = sum(1 for g in games if g['victory'])
    win_rate = (wins / len(games)) * 100

    print(f"Total Games: {len(games)}")
    print(f"Wins: {wins}")
    print(f"Win Rate: {win_rate:.1f}%")
    print(f"Avg Floor: {sum(g['final_floor'] for g in games) / len(games):.1f}")

    # Show individual games
    print(f"\n{'Game':<6} {'Result':<8} {'Act':<4} {'Floor':<6} {'Cause':<10} {'HP%':<6} {'Turns':<6}")
    print("-" * 80)

    for i, game in enumerate(reversed(games), 1):
        result = "WIN" if game['victory'] else "LOSS"
        cause = game['death_cause'] or "N/A"
        hp_pct = game['hp_pct'] * 100

        print(f"{i:<6} {result:<8} {game['final_act']:<4} {game['final_floor']:<6} "
              f"{cause:<10} {hp_pct:<5.0f}% {game['avg_turns_per_combat']:<6.1f}")

    print()


def analyze_winrate_trend(stats: GameStatistics, window: int = 10):
    """
    Show win rate trend over time.

    Args:
        stats: GameStatistics instance
        window: Window size for rolling average
    """
    games = stats.games

    if len(games) < window:
        print(f"Not enough games for trend analysis (need at least {window}).")
        return

    print(f"\n{'=' * 80}")
    print(f"WIN RATE TREND (rolling {window}-game average)")
    print(f"{'=' * 80}\n")

    # Calculate rolling win rates
    trends = []
    for i in range(window, len(games) + 1):
        window_games = games[i-window:i]
        wins = sum(1 for g in window_games if g['victory'])
        win_rate = (wins / window) * 100
        trends.append((i, win_rate))

    # Print trend
    print(f"{'Games':<10} {'Win Rate':<10} {'Trend'}")
    print("-" * 80)

    for i, (game_num, win_rate) in enumerate(trends[::max(1, len(trends)//10)]):
        bar_length = int(win_rate / 5)
        bar = "█" * bar_length + "░" * (20 - bar_length)
        print(f"{game_num:<10} {win_rate:<9.1f}% {bar}")

    # Overall trend
    if len(trends) >= 2:
        recent_rate = trends[-1][1]
        earlier_rate = trends[0][1]
        change = recent_rate - earlier_rate
        change_str = f"+{change:.1f}%" if change > 0 else f"{change:.1f}%"
        trend_str = "📈 Improving" if change > 5 else "📉 Declining" if change < -5 else "➡️ Stable"

        print(f"\nOverall Trend: {trend_str} ({change_str})")

    print()


def analyze_death_distribution(stats: GameStatistics):
    """
    Show distribution of death causes.

    Args:
        stats: GameStatistics instance
    """
    distribution = stats.get_death_distribution()

    if not distribution:
        print("\nNo deaths recorded yet.")
        return

    print(f"\n{'=' * 80}")
    print(f"DEATH DISTRIBUTION")
    print(f"{'=' * 80}\n")

    total_deaths = sum(distribution.values())

    # Sort by count
    sorted_dist = sorted(distribution.items(), key=lambda x: x[1], reverse=True)

    print(f"{'Cause':<15} {'Count':<10} {'Percentage':<12}")
    print("-" * 80)

    for cause, count in sorted_dist:
        pct = (count / total_deaths) * 100
        bar_length = int(pct / 5)
        bar = "█" * bar_length
        print(f"{cause:<15} {count:<10} {pct:<11.1f}% {bar}")

    print()


def analyze_avg_floor(stats: GameStatistics):
    """
    Show average floor reached statistics.

    Args:
        stats: GameStatistics instance
    """
    games = stats.games

    if not games:
        print("\nNo games recorded yet.")
        return

    print(f"\n{'=' * 80}")
    print(f"FLOOR STATISTICS")
    print(f"{'=' * 80}\n")

    # Overall average
    avg_floor = sum(g['final_floor'] for g in games) / len(games)
    max_floor = max(g['final_floor'] for g in games)

    print(f"Total Games: {len(games)}")
    print(f"Average Floor: {avg_floor:.1f}")
    print(f"Highest Floor Reached: {max_floor}")

    # By act
    act_counts = {}
    for game in games:
        act = game['final_act']
        act_counts[act] = act_counts.get(act, 0) + 1

    print(f"\nGames Reached Each Act:")
    for act in sorted(act_counts.keys()):
        count = act_counts[act]
        pct = (count / len(games)) * 100
        print(f"  Act {act}: {count} games ({pct:.1f}%)")

    # Floor distribution (wins vs losses)
    print(f"\nFloor Distribution (Wins vs Losses):")

    wins_by_floor = {}
    losses_by_floor = {}

    for game in games:
        floor = game['final_floor']
        if game['victory']:
            wins_by_floor[floor] = wins_by_floor.get(floor, 0) + 1
        else:
            losses_by_floor[floor] = losses_by_floor.get(floor, 0) + 1

    # Show floors where deaths occurred
    if losses_by_floor:
        print(f"\n  Deaths by Floor:")
        for floor in sorted(losses_by_floor.keys())[:20]:  # Show top 20
            count = losses_by_floor[floor]
            print(f"    Floor {floor:3d}: {count} deaths")

    print()


def analyze_card_choices(stats: GameStatistics, n: int = 20):
    """
    Show most commonly chosen cards.

    Args:
        stats: GameStatistics instance
        n: Number of top cards to show
    """
    games = stats.games

    if not games:
        print("\nNo games recorded yet.")
        return

    print(f"\n{'=' * 80}")
    print(f"CARDS OBTAINED (top {n})")
    print(f"{'=' * 80}\n")

    card_counts = {}
    for game in games:
        for card in game['cards_obtained']:
            card_counts[card] = card_counts.get(card, 0) + 1

    if not card_counts:
        print("No cards obtained yet.")
        return

    # Sort by count
    sorted_cards = sorted(card_counts.items(), key=lambda x: x[1], reverse=True)[:n]

    print(f"{'Card':<30} {'Times Obtained':<15}")
    print("-" * 80)

    for card, count in sorted_cards:
        print(f"{card:<30} {count:<15}")

    total_skipped = sum(g['cards_skipped'] for g in games)
    avg_skipped = total_skipped / len(games)
    print(f"\nAverage cards skipped per game: {avg_skipped:.1f}")
    print()


def main():
    """Main entry point for command-line tool."""
    parser = argparse.ArgumentParser(
        description="Analyze AI game statistics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python analyze_stats.py --recent 20          Show last 20 games
  python analyze_stats.py --winrate-trend      Show win rate trend
  python analyze_stats.py --death-distribution Show death distribution
  python analyze_stats.py --avg-floor          Show floor statistics
  python analyze_stats.py --cards              Show card choices
  python analyze_stats.py --summary            Show all statistics
        """
    )

    parser.add_argument(
        '--log-file',
        default='ai_game_stats.jsonl',
        help='Path to JSONL log file (default: ai_game_stats.jsonl)'
    )

    parser.add_argument(
        '--recent',
        type=int,
        metavar='N',
        help='Show last N games'
    )

    parser.add_argument(
        '--winrate-trend',
        action='store_true',
        help='Show win rate trend over time'
    )

    parser.add_argument(
        '--death-distribution',
        action='store_true',
        help='Show distribution of death causes'
    )

    parser.add_argument(
        '--avg-floor',
        action='store_true',
        help='Show average floor statistics'
    )

    parser.add_argument(
        '--cards',
        action='store_true',
        help='Show most common card choices'
    )

    parser.add_argument(
        '--summary',
        action='store_true',
        help='Show comprehensive summary'
    )

    args = parser.parse_args()

    # Load statistics
    stats = GameStatistics(args.log_file)

    if not stats.games:
        print(f"No game data found. Make sure {args.log_file} exists.")
        sys.exit(1)

    # Run requested analyses
    if args.summary:
        stats.print_summary()
    elif args.recent:
        analyze_recent(stats, args.recent)
    elif args.winrate_trend:
        analyze_winrate_trend(stats)
    elif args.death_distribution:
        analyze_death_distribution(stats)
    elif args.avg_floor:
        analyze_avg_floor(stats)
    elif args.cards:
        analyze_card_choices(stats)
    else:
        # Default to summary
        stats.print_summary()


if __name__ == "__main__":
    main()
