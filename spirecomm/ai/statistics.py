"""
Statistics aggregation and storage for AI performance analysis.

This module provides the GameStatistics class which aggregates data across
multiple games and saves to JSONL and CSV formats.
"""

import json
import os
import subprocess
from typing import List, Dict, Any
from spirecomm.ai.tracker import GameTracker


def get_ai_version() -> str:
    """Get AI version from git tags or fallback to default.
    
    Uses git tag if available, otherwise returns default version.
    This avoids manual version updates and ensures version matches git tag.
    Now works from any directory by executing git commands in the script's directory.
    """
    try:
        # Get the directory of this script file
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # Try to get the most recent tag
        tag = subprocess.check_output(
            ['git', 'describe', '--tags', '--abbrev=0'],
            cwd=script_dir,
            stderr=subprocess.DEVNULL,
            timeout=5
        ).decode('utf-8').strip()
        
        # If tag exists, use it
        if tag:
            return tag
    except:
        pass
    
    # Fallback to default version if git tag not available
    # Version 3.0: Phase 1-6 beam search optimization complete
    # Version 3.1: Added group-based card limits + AOE scoring fix
    # Version 3.1.1: Added defense logging (DAMAGE_FALLBACK, OVER_DEFENSE, DEFENSE_ANALYSIS)
    # Version 3.1.2: Enabled DEBUG logging for defense analysis
    return "3.1.2-beam-optimized"


def get_git_commit() -> str:
    """Get current git commit hash for version tracking.

    Enhanced to handle more edge cases and provide better error information.
    Now works from any directory by executing git commands in the script's directory.
    Uses caching to avoid repeated slow git calls.

    DISABLED: Git calls are too slow in WSL/Windows cross-filesystem environment.
    """
    # Temporarily disabled - always return cached/unknown value
    import logging
    logging.info("[STATS] get_git_commit() - git calls disabled, using default")
    return "unknown (git disabled)"

    # Original code below is disabled
    return None  # Unreachable


# Auto-detect AI version from git tags
AI_VERSION = get_ai_version()


class GameStatistics:
    """
    Aggregate statistics across multiple games.

    Manages:
    - In-memory game history
    - JSONL file logging (append-only)
    - CSV file export
    - Loading historical data
    """

    CSV_HEADER = ','.join([
        'game_id',
        'player_class',
        'ascension',
        'victory',
        'final_floor',
        'final_act',
        'death_cause',
        'hp_pct',
        'combats',
        'elite_kills',
        'boss_kills',
        'avg_turns_per_combat',
        'total_hp_lost',
        'cards_obtained',
        'cards_skipped',
        'relics',
        'potions_used',
        'total_decisions',
        'avg_confidence',
        'fallback_count',
        'ai_version',
        'git_commit',
        'timestamp'
    ])

    def __init__(self, log_file: str = "ai_game_stats.jsonl"):
        """
        Initialize statistics manager.

        Args:
            log_file: Path to JSONL log file
        """
        self.log_file = log_file
        self.csv_file = log_file.replace('.jsonl', '.csv')
        self.games: List[Dict[str, Any]] = []

        # Create CSV with header if it doesn't exist
        self._initialize_csv()

        # Load existing history
        self.load_history()

    def _initialize_csv(self):
        """Create CSV file with header if it doesn't exist."""
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, 'w', encoding='utf-8') as f:
                f.write(self.CSV_HEADER + '\n')
        else:
            # Check if file needs version columns added (backward compatibility)
            try:
                with open(self.csv_file, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                    if 'ai_version' not in first_line:
                        # Old format detected - add version info to header
                        # Backup and recreate with new header
                        import shutil
                        backup_file = self.csv_file + '.backup'
                        shutil.copy2(self.csv_file, backup_file)

                        # Read existing data (excluding old header)
                        with open(backup_file, 'r', encoding='utf-8') as f:
                            old_lines = f.readlines()
                            # Skip old header, keep data rows
                            lines = old_lines[1:] if len(old_lines) > 1 else []

                        # Write new file with updated header
                        with open(self.csv_file, 'w', encoding='utf-8') as f:
                            f.write(self.CSV_HEADER + '\n')
                            # Add empty version columns to existing rows
                            for line in lines:
                                if line.strip():
                                    f.write(line.strip() + ',,\n')
            except Exception:
                # If check fails, just use existing file
                pass

    def load_history(self):
        """Load game history from JSONL file."""
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                game_data = json.loads(line)
                                self.games.append(game_data)
                            except json.JSONDecodeError:
                                # Skip malformed lines
                                continue
            except Exception as e:
                # If loading fails, start fresh
                self.games = []

    def record_game(self, tracker: GameTracker):
        """
        Record a completed game.

        Saves to:
        - In-memory list
        - JSONL file (append)
        - CSV file (append)

        Args:
            tracker: GameTracker with completed game data
        """
        import logging
        logging.info("[STATS] record_game() called")

        game_data = tracker.to_dict()
        logging.info("[STATS] tracker.to_dict() completed")

        # Add to in-memory list
        self.games.append(game_data)
        logging.info("[STATS] Added to in-memory list")

        # Save to JSONL
        logging.info("[STATS] About to save to JSONL...")
        self._save_to_jsonl(game_data)
        logging.info("[STATS] JSONL save completed")

        # Save to CSV
        logging.info("[STATS] About to save to CSV...")
        self._save_to_csv(game_data)
        logging.info("[STATS] CSV save completed")

    def _save_to_jsonl(self, game_data: Dict[str, Any]):
        """
        Append game data to JSONL file.

        Args:
            game_data: Game data dictionary
        """
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                json.dump(game_data, f, ensure_ascii=False)
                f.write('\n')
        except Exception as e:
            # Silently fail if can't write
            pass

    def _save_to_csv(self, game_data: Dict[str, Any]):
        """
        Append game data to CSV file.

        Args:
            game_data: Game data dictionary
        """
        import logging
        logging.info("[STATS] _save_to_csv() started")

        try:
            # Extract and format values
            logging.info("[STATS] Extracting card/relic strings...")
            cards_str = ';'.join(game_data['cards_obtained']) if game_data['cards_obtained'] else ''
            relics_str = ';'.join(game_data['relics']) if game_data['relics'] else ''

            logging.info("[STATS] Building values list...")
            values = [
                str(game_data['game_id']),
                game_data['player_class'] or '',
                str(game_data['ascension']),
                str(game_data['victory']),
                str(game_data['final_floor']),
                str(game_data['final_act']),
                game_data['death_cause'] or '',
                str(game_data['hp_pct']),
                str(game_data['combats']),
                str(game_data['elite_kills']),
                str(game_data['boss_kills']),
                str(game_data['avg_turns_per_combat']),
                str(game_data['total_hp_lost']),
                f'"{cards_str}"',
                str(game_data['cards_skipped']),
                f'"{relics_str}"',
                str(game_data['potions_used']),
                str(game_data['total_decisions']),
                str(game_data['avg_confidence']),
                str(game_data['fallback_count']),
                AI_VERSION,
                get_git_commit(),
                game_data['timestamp']
            ]

            row = ','.join(values)
            logging.info("[STATS] Row built, about to write to CSV...")

            with open(self.csv_file, 'a', encoding='utf-8') as f:
                f.write(row + '\n')
            logging.info("[STATS] CSV write completed successfully")
        except Exception as e:
            import logging
            logging.error(f"[STATS] Error in _save_to_csv: {e}")
            pass

    def get_recent_games(self, n: int = 10) -> List[Dict[str, Any]]:
        """
        Get the most recent N games.

        Args:
            n: Number of recent games to return

        Returns:
            List of recent game data
        """
        return self.games[-n:] if self.games else []

    def get_win_rate(self, last_n: int = None) -> float:
        """
        Calculate win rate.

        Args:
            last_n: Only consider last N games (None for all)

        Returns:
            Win rate as percentage (0-100)
        """
        games = self.games[-last_n:] if last_n else self.games
        if not games:
            return 0.0

        wins = sum(1 for g in games if g['victory'])
        return (wins / len(games)) * 100

    def get_avg_floor(self, last_n: int = None) -> float:
        """
        Calculate average floor reached.

        Args:
            last_n: Only consider last N games (None for all)

        Returns:
            Average floor number
        """
        games = self.games[-last_n:] if last_n else self.games
        if not games:
            return 0.0

        return sum(g['final_floor'] for g in games) / len(games)

    def get_death_distribution(self, last_n: int = None) -> Dict[str, int]:
        """
        Get distribution of death causes.

        Args:
            last_n: Only consider last N games (None for all)

        Returns:
            Dictionary mapping death cause to count
        """
        games = self.games[-last_n:] if last_n else self.games
        distribution = {}

        for game in games:
            if not game['victory']:
                cause = game['death_cause'] or 'unknown'
                distribution[cause] = distribution.get(cause, 0) + 1

        return distribution

    def get_summary(self, last_n: int = None) -> Dict[str, Any]:
        """
        Get comprehensive summary statistics.

        Args:
            last_n: Only consider last N games (None for all)

        Returns:
            Dictionary with summary statistics
        """
        games = self.games[-last_n:] if last_n else self.games

        if not games:
            return {
                'total_games': 0,
                'win_rate': 0.0,
                'avg_floor': 0.0,
                'death_distribution': {},
                'recent_performance': []
            }

        return {
            'total_games': len(games),
            'win_rate': self.get_win_rate(last_n),
            'avg_floor': self.get_avg_floor(last_n),
            'death_distribution': self.get_death_distribution(last_n),
            'recent_performance': self._get_recent_performance(10),
            'avg_confidence': sum(g['avg_confidence'] for g in games) / len(games),
            'avg_turns': sum(g['avg_turns_per_combat'] for g in games) / len(games),
            'total_elite_kills': sum(g['elite_kills'] for g in games),
            'total_boss_kills': sum(g['boss_kills'] for g in games)
        }

    def _get_recent_performance(self, n: int) -> List[str]:
        """
        Get recent game results as W/L list.

        Args:
            n: Number of recent games

        Returns:
            List of 'W' or 'L' strings
        """
        games = self.games[-n:] if self.games else []
        return ['W' if g['victory'] else 'L' for g in games]

    def print_summary(self, last_n: int = None):
        """
        Print formatted summary to console.

        Args:
            last_n: Only consider last N games (None for all)
        """
        summary = self.get_summary(last_n)

        print("\n" + "=" * 60)
        print("AI PERFORMANCE SUMMARY")
        print("=" * 60)

        games_label = f"Last {last_n}" if last_n else "All"
        print(f"\nGames: {summary['total_games']} ({games_label})")
        print(f"Win Rate: {summary['win_rate']:.1f}%")
        print(f"Avg Floor: {summary['avg_floor']:.1f}")
        print(f"Avg Confidence: {summary['avg_confidence']:.2f}")
        print(f"Avg Turns/Combat: {summary['avg_turns']:.1f}")
        print(f"Elite Kills: {summary['total_elite_kills']}")
        print(f"Boss Kills: {summary['total_boss_kills']}")

        if summary['death_distribution']:
            print("\nDeath Distribution:")
            for cause, count in sorted(summary['death_distribution'].items(),
                                       key=lambda x: x[1], reverse=True):
                print(f"  {cause}: {count}")

        if summary['recent_performance']:
            recent_str = ' '.join(summary['recent_performance'])
            wins = summary['recent_performance'].count('W')
            print(f"\nRecent: {recent_str} ({wins}/{len(summary['recent_performance'])} wins)")

        print("=" * 60 + "\n")
