import sys
import os

from spirecomm.communication.coordinator import Coordinator
from spirecomm.ai.agent import SimpleAgent, OptimizedAgent, OPTIMIZED_AI_AVAILABLE
from spirecomm.spire.character import PlayerClass


def create_agent(use_optimized=None):
    """
    Create an agent instance.

    Args:
        use_optimized: Force use of optimized agent (True), simple agent (False),
                      or auto-detect (None)

    Returns:
        Agent instance (SimpleAgent or OptimizedAgent)
    """
    # Check environment variable if not specified
    if use_optimized is None:
        use_optimized = os.getenv("USE_OPTIMIZED_AI", "false").lower() == "true"

    # Try to use OptimizedAgent if requested
    if use_optimized:
        if OPTIMIZED_AI_AVAILABLE:
            sys.stderr.write("Using OptimizedAgent with enhanced AI\n")
            return OptimizedAgent()
        else:
            sys.stderr.write("Warning: OptimizedAgent requested but components not available\n")
            sys.stderr.write("Falling back to SimpleAgent\n")
            return SimpleAgent()
    else:
        sys.stderr.write("Using SimpleAgent (legacy AI)\n")
        return SimpleAgent()


if __name__ == "__main__":
    # Parse command line arguments
    use_optimized = None
    ascension_level = 0  # Default ascension level

    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ['--optimized', '-o', 'optimized']:
            use_optimized = True
            sys.stderr.write("Optimized AI mode enabled via command line\n")
        elif arg in ['--simple', '-s', 'simple']:
            use_optimized = False
            sys.stderr.write("Simple AI mode enforced via command line\n")
        elif arg in ['--help', '-h']:
            sys.stderr.write("Slay the Spire AI\n\n")
            sys.stderr.write("Usage:\n")
            sys.stderr.write("  python main.py [options]\n\n")
            sys.stderr.write("Options:\n")
            sys.stderr.write("  --optimized, -o    Use OptimizedAgent with enhanced AI\n")
            sys.stderr.write("  --simple, -s       Use SimpleAgent (legacy AI)\n")
            sys.stderr.write("  --ascension, -a N  Set ascension level (0-20, default: 20)\n")
            sys.stderr.write("  --help, -h         Show this help message\n\n")
            sys.stderr.write("Environment Variable:\n")
            sys.stderr.write("  USE_OPTIMIZED_AI=true  Use OptimizedAgent\n\n")
            sys.stderr.write("Examples:\n")
            sys.stderr.write("  python main.py              # Auto-detect, ascension 0\n")
            sys.stderr.write("  python main.py --optimized  # Force optimized AI\n")
            sys.stderr.write("  python main.py -a 10        # Ascension level 10\n")
            sys.stderr.write("  python main.py -a 20        # Ascension level 20\n")
            sys.stderr.write("  python main.py --optimized -a 20  # Optimized AI A20\n")
            sys.exit(0)

    # Parse ascension level
    if len(sys.argv) > 2:
        for i in range(1, len(sys.argv)):
            if sys.argv[i].lower() in ['--ascension', '-a']:
                if i + 1 < len(sys.argv):
                    try:
                        ascension_level = int(sys.argv[i + 1])
                        if ascension_level < 0 or ascension_level > 20:
                            sys.stderr.write(f"Ascension level must be 0-20, got {ascension_level}\n")
                            sys.exit(1)
                        sys.stderr.write(f"Ascension level set to {ascension_level}\n")
                    except ValueError:
                        sys.stderr.write(f"Invalid ascension level: {sys.argv[i + 1]}\n")
                        sys.stderr.write(f"Ascension must be a number (0-20), ignoring and using default\n")

    # Create agent
    agent = create_agent(use_optimized)

    # Setup coordinator
    coordinator = Coordinator()
    coordinator.signal_ready()
    coordinator.register_command_error_callback(agent.handle_error)
    coordinator.register_state_change_callback(agent.get_next_action_in_game)
    coordinator.register_out_of_game_callback(agent.get_next_action_out_of_game)

    # Play games forever - IRONCLAD ONLY for testing
    game_count = 0
    chosen_class = PlayerClass.IRONCLAD  # Fixed to Ironclad for testing

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

        # Change agent class for this game
        agent.change_class(chosen_class)

        # Play the game
        result = coordinator.play_one_game(chosen_class, ascension_level=current_ascension)

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
