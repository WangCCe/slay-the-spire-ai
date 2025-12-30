import argparse
import os
import sys

from spirecomm.communication.coordinator import Coordinator
from spirecomm.ai.agent import SimpleAgent, OptimizedAgent, OPTIMIZED_AI_AVAILABLE
from spirecomm.spire.character import PlayerClass

# Import statistics components
try:
    from spirecomm.ai.statistics import GameStatistics
    STATISTICS_AVAILABLE = True
except ImportError:
    STATISTICS_AVAILABLE = False
    sys.stderr.write("Warning: Statistics tracking not available\n")


def create_agent(use_optimized=None, player_class=None):
    """
    Create an agent instance.

    Args:
        use_optimized: Force use of optimized agent (True), simple agent (False),
                      or auto-detect (None)
        player_class: Player class to determine if optimized AI should be used

    Returns:
        Agent instance (SimpleAgent or OptimizedAgent)
    """
    # Auto-enable optimized AI for Ironclad
    if use_optimized is None:
        if player_class == PlayerClass.IRONCLAD:
            use_optimized = True
            sys.stderr.write("Auto-enabling OptimizedAgent for Ironclad\n")
        else:
            use_optimized = os.getenv("USE_OPTIMIZED_AI", "false").lower() == "true"

    # Try to use OptimizedAgent if requested
    if use_optimized:
        if OPTIMIZED_AI_AVAILABLE:
            class_name = player_class.name if player_class else "Unknown"
            sys.stderr.write(f"Using OptimizedAgent with enhanced AI for {class_name}\n")
            return OptimizedAgent(chosen_class=player_class) if player_class else OptimizedAgent()
        else:
            sys.stderr.write("Warning: OptimizedAgent requested but components not available\n")
            sys.stderr.write("Falling back to SimpleAgent\n")
            return SimpleAgent(chosen_class=player_class) if player_class else SimpleAgent()
    else:
        class_name = player_class.name if player_class else "Unknown"
        sys.stderr.write(f"Using SimpleAgent (legacy AI) for {class_name}\n")
        return SimpleAgent(chosen_class=player_class) if player_class else SimpleAgent()


if __name__ == "__main__":
    # Parse command line arguments
    use_optimized = None
    ascension_level = 0  # Default ascension level

    parser = argparse.ArgumentParser(
        prog="python main.py",
        description="Slay the Spire AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Environment Variable:\n"
            "  USE_OPTIMIZED_AI=true  Use OptimizedAgent\n\n"
            "Examples:\n"
            "  python main.py              # Auto-detect, ascension 0\n"
            "  python main.py --optimized  # Force optimized AI\n"
            "  python main.py -a 10        # Ascension level 10\n"
            "  python main.py -a 20        # Ascension level 20\n"
            "  python main.py --optimized -a 20  # Optimized AI A20\n"
        ),
    )
    parser.add_argument(
        "--optimized",
        "-o",
        action="store_true",
        help="Use OptimizedAgent with enhanced AI",
    )
    parser.add_argument(
        "--simple",
        "-s",
        action="store_true",
        help="Use SimpleAgent (legacy AI)",
    )
    parser.add_argument(
        "--ascension",
        "-a",
        default=None,
        metavar="N",
        help="Set ascension level (0-20, default: 0)",
    )
    parser.add_argument(
        "mode",
        nargs="?",
        choices=["optimized", "simple"],
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args()

    if args.optimized and args.simple:
        sys.stderr.write("Cannot specify both --optimized and --simple\n")
        sys.exit(1)

    if args.optimized or args.mode == "optimized":
        use_optimized = True
        sys.stderr.write("Optimized AI mode enabled via command line\n")
    elif args.simple or args.mode == "simple":
        use_optimized = False
        sys.stderr.write("Simple AI mode enforced via command line\n")

    if args.ascension is not None:
        try:
            ascension_level = int(args.ascension)
            if ascension_level < 0 or ascension_level > 20:
                sys.stderr.write(f"Ascension level must be 0-20, got {ascension_level}\n")
                sys.exit(1)
            sys.stderr.write(f"Ascension level set to {ascension_level}\n")
        except ValueError:
            sys.stderr.write(f"Invalid ascension level: {args.ascension}\n")
            sys.stderr.write("Ascension must be a number (0-20), ignoring and using default\n")

    # Define player class before creating agent
    chosen_class = PlayerClass.IRONCLAD  # Fixed to Ironclad for testing

    # Create agent with player class for auto-detection
    agent = create_agent(use_optimized, player_class=chosen_class)

    # Setup statistics tracking if available
    statistics = None
    debug_log = None
    if STATISTICS_AVAILABLE:
        statistics = GameStatistics()
        sys.stderr.write(f"Statistics tracking enabled\n")
        sys.stderr.write(f"  Logging to: {statistics.log_file}\n")
        sys.stderr.write(f"  CSV export: {statistics.csv_file}\n")

        # Also open debug log file
        debug_log_path = "ai_debug.log"
        debug_log = open(debug_log_path, 'a', encoding='utf-8')
        debug_log.write(f"\n{'='*60}\n")

    # Setup coordinator
    coordinator = Coordinator()
    coordinator.signal_ready()
    coordinator.register_command_error_callback(agent.handle_error)
    coordinator.register_state_change_callback(agent.get_next_action_in_game)
    coordinator.register_out_of_game_callback(agent.get_next_action_out_of_game)

    # Play games forever - IRONCLAD ONLY for testing
    game_count = 0

    # Set ascension level (default to 20 if not specified)
    current_ascension = ascension_level if ascension_level is not None else 20
    if not isinstance(current_ascension, int):
        current_ascension = 20  # Force to integer if 'auto' was passed

    while True:  # Infinite loop for Ironclad only
        game_count += 1
        sys.stderr.write(f"\n{'='*60}\n")
        sys.stderr.write(f"Starting game #{game_count} as {chosen_class}\n")
        sys.stderr.write(f"Ascension Level: {current_ascension}\n")
        sys.stderr.write(f"{'='*60}\n")

        # Reset game tracker for OptimizedAgent
        if isinstance(agent, OptimizedAgent) and hasattr(agent, 'game_tracker'):
            try:
                from spirecomm.ai.tracker import GameTracker
                agent.game_tracker = GameTracker()
                agent.game_tracker.player_class = str(chosen_class).replace('PlayerClass.', '')
                agent.game_tracker.ascension_level = current_ascension
            except Exception as e:
                sys.stderr.write(f"Warning: Could not reset game tracker: {e}\n")

        # Change agent class for this game
        agent.change_class(chosen_class)

        # Play the game
        result = coordinator.play_one_game(chosen_class, ascension_level=current_ascension)

        # Record game result if statistics available
        if statistics:
            try:
                debug_msg = f"\n[DEBUG] Attempting to save statistics...\n"
                debug_msg += f"[DEBUG] agent type: {type(agent).__name__}\n"
                debug_msg += f"[DEBUG] is OptimizedAgent: {isinstance(agent, OptimizedAgent)}\n"

                sys.stderr.write(debug_msg)
                if debug_log:
                    debug_log.write(debug_msg)
                    debug_log.flush()

                # Only OptimizedAgent has game_tracker
                if isinstance(agent, OptimizedAgent) and hasattr(agent, 'game_tracker') and agent.game_tracker:
                    debug_msg2 = f"[DEBUG] game_tracker found, saving...\n"
                    debug_msg2 += f"[DEBUG] result: {result}\n"
                    debug_msg2 += f"[DEBUG] coordinator has last_game_state: {hasattr(coordinator, 'last_game_state')}\n"

                    sys.stderr.write(debug_msg2)
                    if debug_log:
                        debug_log.write(debug_msg2)
                        debug_log.flush()

                    # Record game over state
                    if hasattr(coordinator, 'last_game_state') and coordinator.last_game_state is not None:
                        agent.game_tracker.record_game_over(result, coordinator.last_game_state)
                        if debug_log:
                            debug_log.write(f"[DEBUG] Recorded game over via last_game_state\n")
                            debug_log.flush()
                    else:
                        # Fallback: record with minimal info
                        debug_msg3 = f"[DEBUG] No last_game_state, using fallback\n"
                        sys.stderr.write(debug_msg3)
                        if debug_log:
                            debug_log.write(debug_msg3)
                            debug_log.flush()

                        agent.game_tracker.victory = result
                        agent.game_tracker.final_floor = agent.game.floor if hasattr(agent.game, 'floor') else 0
                        agent.game_tracker.final_act = agent.game.act if hasattr(agent.game, 'act') else 1

                    # Save to statistics
                    statistics.record_game(agent.game_tracker)
                    if debug_log:
                        debug_log.write(f"[DEBUG] Saved to statistics\n")
                        debug_log.flush()

                    # Print simple confirmation
                    result_str = "WIN" if result else "LOSS"
                    floor = agent.game_tracker.final_floor
                    act = agent.game_tracker.final_act
                    confirm_msg = f"\nGame #{game_count} saved: {result_str} at Act {act} Floor {floor}\n"
                    sys.stderr.write(confirm_msg)
                    if debug_log:
                        debug_log.write(confirm_msg)
                        debug_log.flush()
                else:
                    debug_msg4 = f"[DEBUG] No game_tracker to save (not OptimizedAgent or tracker is None)\n"
                    sys.stderr.write(debug_msg4)
                    if debug_log:
                        debug_log.write(debug_msg4)
                        debug_log.flush()
            except Exception as e:
                error_msg = f"Error saving statistics: {e}\n"
                sys.stderr.write(error_msg)
                if debug_log:
                    debug_log.write(error_msg)
                    debug_log.flush()
                import traceback
                traceback.print_exc()
                if debug_log:
                    traceback.print_exc(file=debug_log)

        # Print summary if OptimizedAgent (to stderr)
        if isinstance(agent, OptimizedAgent):
            try:
                summary = agent.get_decision_summary()
                sys.stderr.write(f"\nGame Summary:\n")
                sys.stderr.write(f"  Total Decisions: {summary['total_decisions']}\n")
                sys.stderr.write(f"  Combat Decisions: {summary['combat_decisions']}\n")
                sys.stderr.write(f"  Card Rewards: {summary['card_rewards']}\n")
                sys.stderr.write(f"  Avg Confidence: {summary['avg_confidence']:.2f}\n")

                # Print deck stats if available
                deck_stats = agent.get_deck_stats()
                if 'error' not in deck_stats:
                    sys.stderr.write(f"\nDeck Statistics:\n")
                    sys.stderr.write(f"  Size: {deck_stats['size']}\n")
                    sys.stderr.write(f"  Archetype: {deck_stats['archetype']}\n")
                    sys.stderr.write(f"  Quality: {deck_stats['quality']:.2f}\n")
                    sys.stderr.write(f"  Upgrade Rate: {deck_stats.get('upgrade_rate', 0):.2%}\n")
            except Exception as e:
                sys.stderr.write(f"Error generating summary: {e}\n")
