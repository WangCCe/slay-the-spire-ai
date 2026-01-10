import argparse
import os
import sys
import logging
from logging.handlers import RotatingFileHandler

from spirecomm.communication.coordinator import Coordinator
from spirecomm.ai.agent import SimpleAgent, OptimizedAgent, OPTIMIZED_AI_AVAILABLE
from spirecomm.spire.character import PlayerClass

# Import RL agent (optional)
try:
    from spirecomm.ai.rl import RLAgent, create_agent as create_rl_agent, RL_AVAILABLE
except ImportError:
    RL_AVAILABLE = False
    RLAgent = None
    create_rl_agent = None

# Setup logging to file with rotation (all logs go to ai_debug.log)
# Note: We don't use StreamHandler because Communication Mod uses stdout for commands
# Log rotation: 10MB per file, keep 5 backup files (60MB total)
# Python 3.7 compatibility: force parameter not available, check if already configured
if not logging.getLogger().hasHandlers():
    handler = RotatingFileHandler(
        'ai_debug.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,  # Keep 5 backups
        encoding='utf-8',
        mode='a'
    )
    logging.basicConfig(
        level=logging.DEBUG,  # TEMPORARY: Set to DEBUG to see defense analysis logs
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            handler,
        ],
    )
else:
    # Logging already configured, just add our rotating file handler if not present
    logger = logging.getLogger()
    has_rotating_handler = any(isinstance(h, RotatingFileHandler) for h in logger.handlers)
    if not has_rotating_handler:
        rotating_handler = RotatingFileHandler(
            'ai_debug.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,  # Keep 5 backups
            encoding='utf-8',
            mode='a'
        )
        logger.addHandler(rotating_handler)

# Import statistics components
try:
    # Temporarily disable stats due to git command hanging on Windows
    # from spirecomm.ai.statistics import GameStatistics
    STATISTICS_AVAILABLE = False
    logging.warning("Statistics tracking temporarily disabled due to git subprocess issue")
except ImportError:
    STATISTICS_AVAILABLE = False
    logging.warning("Statistics tracking not available")


def create_agent(agent_type="auto", use_optimized=None, player_class=None, training=False, model_path=None):
    """
    Create an agent instance.

    Args:
        agent_type: Type of agent ("simple", "optimized", "rl", "auto")
        use_optimized: DEPRECATED - Use agent_type instead
        player_class: Player class (required for RL agent, optional for others)
        training: Whether RL agent should be in training mode
        model_path: Path to pre-trained RL model checkpoint

    Returns:
        Agent instance (SimpleAgent, OptimizedAgent, or RLAgent)
    """
    # Handle legacy use_optimized parameter
    if agent_type == "auto" and use_optimized is not None:
        agent_type = "optimized" if use_optimized else "simple"

    # Auto-detect: use optimized for Ironclad, simple for others
    if agent_type == "auto":
        if player_class == PlayerClass.IRONCLAD:
            agent_type = "optimized"
            logging.info("Auto-enabling OptimizedAgent for Ironclad")
        else:
            agent_type = "simple"

    # Create RL agent
    if agent_type == "rl":
        if not RL_AVAILABLE:
            logging.error("RL agent requested but PyTorch/RL components not available")
            logging.error("Please install: pip install torch numpy")
            logging.error("Falling back to SimpleAgent")
            return SimpleAgent(chosen_class=player_class) if player_class else SimpleAgent()

        if player_class is None:
            logging.warning("RL agent requires player_class, defaulting to IRONCLAD")
            player_class = PlayerClass.IRONCLAD

        if player_class != PlayerClass.IRONCLAD:
            logging.warning(f"RL agent only supports IRONCLAD, got {player_class}")
            logging.warning("Falling back to SimpleAgent")
            return SimpleAgent(chosen_class=player_class)

        try:
            logging.info(f"Creating RL Agent (training={training})")
            agent = create_rl_agent(training=training, model_path=model_path)
            logging.info(f"RL Agent created successfully")
            logging.info(f"  State dim: {agent.state_encoder.feature_dim}, Action dim: {agent.action_encoder.MAX_ACTIONS}")
            logging.info(f"  Training mode: {training}")
            if model_path:
                logging.info(f"  Loaded model: {model_path}")
            return agent
        except Exception as e:
            logging.error(f"Failed to create RL agent: {e}")
            logging.error("Falling back to SimpleAgent")
            import traceback
            logging.debug(traceback.format_exc())
            return SimpleAgent(chosen_class=player_class)

    # Create OptimizedAgent
    if agent_type == "optimized":
        if not OPTIMIZED_AI_AVAILABLE:
            logging.warning("OptimizedAgent requested but components not available")
            logging.warning("Falling back to SimpleAgent")
            return SimpleAgent(chosen_class=player_class) if player_class else SimpleAgent()

        class_name = player_class.name if player_class else "Unknown"
        logging.info(f"Using OptimizedAgent with enhanced AI for {class_name}")
        return OptimizedAgent(chosen_class=player_class) if player_class else OptimizedAgent()

    # Create SimpleAgent (default)
    class_name = player_class.name if player_class else "Unknown"
    logging.info(f"Using SimpleAgent (legacy AI) for {class_name}")
    return SimpleAgent(chosen_class=player_class) if player_class else SimpleAgent()


if __name__ == "__main__":
    # Parse command line arguments
    agent_type = "auto"
    use_optimized = None  # Deprecated but kept for compatibility
    ascension_level = 0  # Default ascension level
    run_seed = None
    training = False
    model_path = None

    parser = argparse.ArgumentParser(
        prog="python main.py",
        description="Slay the Spire AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Environment Variable:\n"
            "  USE_OPTIMIZED_AI=true  Use OptimizedAgent (deprecated, use --agent optimized)\n\n"
            "Examples:\n"
            "  python main.py                    # Auto-detect, ascension 0\n"
            "  python main.py --agent optimized  # Force optimized AI\n"
            "  python main.py --agent rl         # Use RL agent (inference mode)\n"
            "  python main.py --agent rl --train # Use RL agent in training mode\n"
            "  python main.py --agent rl --model checkpoints/model.pth  # Load trained model\n"
            "  python main.py -a 10              # Ascension level 10\n"
            "  python main.py -a 20              # Ascension level 20\n"
            "  python main.py --agent optimized -a 20  # Optimized AI A20\n"
            "  python main.py --seed 7010470200064802279  # Fixed seed run\n"
        ),
    )
    parser.add_argument(
        "--agent",
        choices=["simple", "optimized", "rl", "auto"],
        default="auto",
        help="Agent type: simple, optimized, rl, or auto-detect (default: auto)",
    )
    parser.add_argument(
        "--optimized",
        "-o",
        action="store_true",
        help="Use OptimizedAgent with enhanced AI (deprecated, use --agent optimized)",
    )
    parser.add_argument(
        "--simple",
        "-s",
        action="store_true",
        help="Use SimpleAgent (legacy AI) (deprecated, use --agent simple)",
    )
    parser.add_argument(
        "--train",
        action="store_true",
        help="Enable RL agent training mode (requires --agent rl)",
    )
    parser.add_argument(
        "--model",
        metavar="PATH",
        help="Path to pre-trained RL model checkpoint (requires --agent rl)",
    )
    parser.add_argument(
        "--ascension",
        "-a",
        default=None,
        metavar="N",
        help="Set ascension level (0-20, default: 0)",
    )
    parser.add_argument(
        "--seed",
        metavar="SEED",
        help="Set a fixed run seed (alphanumeric string)",
    )
    parser.add_argument(
        "mode",
        nargs="?",
        choices=["optimized", "simple"],
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args()

    # Handle deprecated arguments
    if args.optimized and args.simple:
        logging.error("Cannot specify both --optimized and --simple")
        sys.exit(1)

    # Determine agent type from various arguments
    if args.mode == "optimized" or args.optimized:
        agent_type = "optimized"
        logging.info("Optimized AI mode enabled via command line")
    elif args.mode == "simple" or args.simple:
        agent_type = "simple"
        logging.info("Simple AI mode enforced via command line")
    elif args.agent != "auto":
        agent_type = args.agent
        logging.info(f"Agent type set to: {agent_type}")

    # RL-specific options
    if args.train and agent_type != "rl":
        logging.warning("--train flag requires --agent rl, ignoring")
        training = False
    else:
        training = args.train

    if args.model and agent_type != "rl":
        logging.warning("--model flag requires --agent rl, ignoring")
        model_path = None
    else:
        model_path = args.model

    if training:
        logging.info("RL Agent training mode enabled")
        logging.info("  Models will be saved to: checkpoints/")

    if model_path:
        logging.info(f"Loading RL model from: {model_path}")

    if args.ascension is not None:
        try:
            ascension_level = int(args.ascension)
            if ascension_level < 0 or ascension_level > 20:
                logging.error(f"Ascension level must be 0-20, got {ascension_level}")
                sys.exit(1)
            logging.info(f"Ascension level set to {ascension_level}")
        except ValueError:
            logging.warning(f"Invalid ascension level: {args.ascension}")
            logging.warning("Ascension must be a number (0-20), ignoring and using default")

    if args.seed is not None:
        run_seed = str(args.seed).strip()
        if not run_seed:
            logging.error("Seed cannot be empty")
            sys.exit(1)
        logging.info(f"Run seed set to {run_seed}")

    # Define player class before creating agent
    chosen_class = PlayerClass.IRONCLAD  # Fixed to Ironclad for testing

    # Create agent with player class and RL-specific options
    agent = create_agent(
        agent_type=agent_type,
        player_class=chosen_class,
        training=training,
        model_path=model_path
    )

    # Setup statistics tracking if available
    statistics = None
    if STATISTICS_AVAILABLE:
        statistics = GameStatistics()
        logging.info("Statistics tracking enabled")
        logging.info(f"  Logging to: {statistics.log_file}")
        logging.info(f"  CSV export: {statistics.csv_file}")
        logging.info(f"  All logs written to: ai_debug.log")

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
        is_rl_agent = RLAgent is not None and isinstance(agent, RLAgent)

        logging.info(f"\n{'='*60}\n")
        logging.info(f"Starting game #{game_count} as {chosen_class}")
        logging.info(f"Ascension Level: {current_ascension}")
        if run_seed is not None:
            logging.info(f"Seed: {run_seed}")
        logging.info(f"Coordinator state: in_game={coordinator.in_game}, ready={coordinator.game_is_ready}")
        if is_rl_agent:
            logging.info(f"RL Agent: training={training}")
        logging.info(f"{'='*60}\n")

        # Reset game tracker for OptimizedAgent
        if isinstance(agent, OptimizedAgent) and hasattr(agent, 'game_tracker'):
            try:
                from spirecomm.ai.tracker import GameTracker
                agent.game_tracker = GameTracker()
                agent.game_tracker.player_class = str(chosen_class).replace('PlayerClass.', '')
                agent.game_tracker.ascension_level = current_ascension
            except Exception as e:
                logging.warning(f"Could not reset game tracker: {e}")

        # Change agent class for this game (only for non-RL agents)
        if not is_rl_agent and hasattr(agent, 'change_class'):
            agent.change_class(chosen_class)
        elif is_rl_agent:
            # RL agent doesn't need change_class, just reset
            agent.reset()

        # Play the game
        try:
            result = coordinator.play_one_game(
                chosen_class,
                ascension_level=current_ascension,
                seed=run_seed,
            )
        except Exception as e:
            # Handle communication errors or game crashes
            import traceback
            logging.error(f"Game #{game_count} failed: {e}\n" + "".join(traceback.format_exc()))

            # Try to restart Communication Mod connection by waiting a bit
            import time
            time.sleep(2)  # Wait for Communication Mod to recover

            # Continue to next game instead of crashing
            continue

        # Record game result if statistics available or RL agent in training
        if is_rl_agent and training:
            # RL agent training checkpoint saving
            try:
                # Create checkpoints directory if it doesn't exist
                os.makedirs("checkpoints", exist_ok=True)

                # Save checkpoint
                checkpoint_path = f"checkpoints/rl_model_ep{game_count}.pth"
                agent.save_model(checkpoint_path, episode=game_count)

                logging.info(f"RL Training checkpoint saved: {checkpoint_path}")

                # Log training metrics
                if hasattr(agent, 'trainer') and agent.trainer:
                    avg_loss = agent.trainer.get_avg_loss()
                    epsilon = agent.trainer.get_epsilon()
                    total_steps = agent.trainer.total_steps
                    logging.info(f"  Training steps: {total_steps}")
                    logging.info(f"  Avg loss: {avg_loss:.4f}")
                    logging.info(f"  Epsilon: {epsilon:.3f}")

                # Reset agent for next episode
                agent.reset()
            except Exception as e:
                logging.error(f"Error saving RL checkpoint: {e}")
                import traceback
                logging.debug(traceback.format_exc())

        if statistics:
            try:
                logging.debug("Attempting to save statistics...")
                logging.debug(f"  agent type: {type(agent).__name__}")
                logging.debug(f"  is OptimizedAgent: {isinstance(agent, OptimizedAgent)}")

                # Only OptimizedAgent has game_tracker
                if isinstance(agent, OptimizedAgent) and hasattr(agent, 'game_tracker') and agent.game_tracker:
                    logging.debug("  game_tracker found, saving...")
                    logging.debug(f"  result: {result}")
                    logging.debug(f"  coordinator has last_game_state: {hasattr(coordinator, 'last_game_state')}")

                    # Record game over state
                    if hasattr(coordinator, 'last_game_state') and coordinator.last_game_state is not None:
                        # Fix: Check if agent died in combat and end combat wasn't recorded
                        if hasattr(agent, '_in_combat') and agent._in_combat:
                            game_state = coordinator.last_game_state
                            agent.game_tracker.end_combat(
                                hp_remaining=game_state.current_hp if hasattr(game_state, 'current_hp') else 0,
                                max_hp=game_state.max_hp if hasattr(game_state, 'max_hp') else 80
                            )
                            agent._in_combat = False
                            logging.debug("  Recorded combat end (died in combat)")

                        agent.game_tracker.record_game_over(result, coordinator.last_game_state)
                        logging.debug("  Recorded game over via last_game_state")
                        try:
                            seed_played = getattr(coordinator.last_game_state, 'seed', None)
                            if seed_played is not None:
                                logging.info(f"  Seed played: {seed_played}")
                        except Exception:
                            pass
                    else:
                        # Fallback: record with minimal info
                        logging.debug("  No last_game_state, using fallback")
                        agent.game_tracker.victory = result
                        agent.game_tracker.final_floor = agent.game.floor if hasattr(agent.game, 'floor') else 0
                        agent.game_tracker.final_act = agent.game.act if hasattr(agent.game, 'act') else 1

                    # Save to statistics
                    statistics.record_game(agent.game_tracker)
                    logging.debug("  Saved to statistics")

                    # Print simple confirmation
                    result_str = "WIN" if result else "LOSS"
                    floor = agent.game_tracker.final_floor
                    act = agent.game_tracker.final_act
                    logging.info(f"Game #{game_count} saved: {result_str} at Act {act} Floor {floor}")
                else:
                    logging.debug("  No game_tracker to save (not OptimizedAgent or tracker is None)")
            except Exception as e:
                logging.error(f"Error saving statistics: {e}")
                import traceback
                logging.debug(traceback.format_exc())

        # Print summary if OptimizedAgent (to stderr)
        if isinstance(agent, OptimizedAgent):
            try:
                summary = agent.get_decision_summary()
                logging.info(f"\nGame Summary:\n")
                logging.info(f"  Total Decisions: {summary['total_decisions']}\n")
                logging.info(f"  Combat Decisions: {summary['combat_decisions']}\n")
                logging.info(f"  Card Rewards: {summary['card_rewards']}\n")
                logging.info(f"  Avg Confidence: {summary['avg_confidence']:.2f}\n")

                # Print deck stats if available
                deck_stats = agent.get_deck_stats()
                if 'error' not in deck_stats:
                    logging.info(f"\nDeck Statistics:\n")
                    logging.info(f"  Size: {deck_stats['size']}\n")
                    logging.info(f"  Archetype: {deck_stats['archetype']}\n")
                    logging.info(f"  Quality: {deck_stats['quality']:.2f}\n")
                    logging.info(f"  Upgrade Rate: {deck_stats.get('upgrade_rate', 0):.2%}\n")
            except Exception as e:
                logging.info(f"Error generating summary: {e}\n")
