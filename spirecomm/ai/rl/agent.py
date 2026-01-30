"""
RL Agent for Slay the Spire.

Integrates StateEncoder, ActionEncoder, RewardCalculator, and DQNTrainer
into a complete RL agent compatible with Communication Mod.
"""

import numpy as np
import torch
import logging
from typing import Optional

from .state_encoder import StateEncoder
from .action_encoder import ActionEncoder
from .reward import RewardCalculator
from .trainer import DQNTrainer
from .network import (
    create_dqn,
    align_state_dict_input,
    detect_network_type_from_checkpoint,
)
from spirecomm.spire.game import Game
from spirecomm.communication.action import Action
from spirecomm.spire.character import PlayerClass

logger = logging.getLogger(__name__)


class RLAgent:
    """
    Reinforcement Learning Agent for Slay the Spire.

    Uses DQN to learn to play the game autonomously.
    Compatible with existing Communication Mod integration.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        training: bool = False,
        device: str = "cuda" if torch.cuda.is_available() else "cpu",
        epsilon: float = 0.0  # Exploration rate (0 = greedy, higher = more random)
    ):
        """
        Initialize RL agent.

        Args:
            model_path: Path to saved model checkpoint (if loading)
            training: Whether agent is in training mode
            device: Device for neural network ("cuda" or "cpu")
            epsilon: Exploration rate for inference-time exploration
        """
        self.device = device
        self.training_mode = training
        self.chosen_class = PlayerClass.IRONCLAD  # Default to Ironclad
        self.network_type = "dueling"

        logger.info("Initializing StateEncoder...")
        # Initialize components
        self.state_encoder = StateEncoder()
        logger.info("StateEncoder initialized")

        logger.info("Initializing ActionEncoder...")
        self.action_encoder = ActionEncoder()
        logger.info("ActionEncoder initialized")

        logger.info("Initializing RewardCalculator...")
        self.reward_calculator = RewardCalculator()
        logger.info("RewardCalculator initialized")

        if model_path is not None:
            self.network_type = self._infer_network_type(model_path)

        # Initialize trainer with correct state dimension
        if training:
            logger.info(f"Initializing DQNTrainer (device={device})...")
            self.trainer = DQNTrainer(
                state_dim=self.state_encoder.feature_dim,
                device=device,
                network_type=self.network_type,
            )
            logger.info("DQNTrainer initialized")
        else:
            self.trainer = None
            logger.info("No trainer (inference mode)")

        # Load model or create new network
        if model_path is not None:
            logger.info(f"Loading model from {model_path}...")
            if self.training_mode and self.trainer is not None:
                try:
                    checkpoint = self.trainer.load_checkpoint(model_path)
                    self.network = self.trainer.online_network
                    self.network.eval()
                    logger.info(
                        "Loaded trainer checkpoint: episode=%s epsilon=%.3f steps=%s",
                        checkpoint.get("episode"),
                        self.trainer.epsilon,
                        self.trainer.total_steps,
                    )
                except Exception as e:
                    logger.warning(
                        "Trainer checkpoint load failed, falling back to weights-only: %s",
                        e,
                    )
                    self.load_model(model_path)
                    logger.info(f"Loaded model weights from {model_path}")
            else:
                self.load_model(model_path)
                logger.info(f"Loaded model weights from {model_path}")
        else:
            # Create network for inference with correct state dimension
            logger.info(f"Creating new network (device={device})...")
            self.network = create_dqn(self.network_type, state_dim=self.state_encoder.feature_dim, device=device)
            self.network.eval()
            logger.info("Network initialized")

        self.epsilon = epsilon
        self.last_state = None
        self.last_action = None
        self.last_action_mask = None
        self.last_game = None  # Track previous game state for reward calculation
        self.boss_min_epsilon = 0.3
        self.last_logged_turn = None
        self.pending_reward_action = None
        self.pending_reward_mask = None
        self.pending_reward_game = None

        # Episode tracking
        self.episode_reward = 0.0
        self.episode_steps = 0

        # Failed action tracking to prevent action loops
        self.failed_actions = set()  # Set of action indices that failed recently
        self.consecutive_failures = {}  # action_index -> failure count
        self.max_consecutive_failures = 3  # Disable action after 3 consecutive failures
        self.last_state_key = None  # Track state changes to clear failures appropriately

    def get_next_action_in_game(self, game: Game) -> Action:
        """
        Get next action for current game state.

        Main entry point for Communication Mod integration.

        Args:
            game: Current game state

        Returns:
            Action object to execute
        """
        from spirecomm.spire.screen import ScreenType
        screen_type = getattr(game, 'screen_type', None)
        in_combat = getattr(game, 'in_combat', False)

        logger.info(f"[RLAgent] get_next_action_in_game called: screen={screen_type}, in_combat={in_combat}")

        try:
            # Check if state has changed significantly (floor, screen)
            # Don't clear on turn changes - we want to persist failures across a combat
            # Only clear when floor changes or screen type changes (combat -> reward -> map)
            current_state_key = (
                getattr(game, 'floor', 0),
                str(getattr(game, 'screen_type', None))
            )

            if self.last_state_key != current_state_key:
                if self.failed_actions:
                    logger.debug(f"State changed from {self.last_state_key} to {current_state_key}, clearing {len(self.failed_actions)} failed actions")
                    self.failed_actions.clear()
                    self.consecutive_failures.clear()
                self.last_state_key = current_state_key

            # Encode current state
            state = self.state_encoder.encode(game)

            # Get action mask and exclude recently failed actions
            action_mask = np.array(self.action_encoder.get_action_mask(game), dtype=bool)

            # Exclude actions that have failed repeatedly
            for failed_idx in self.failed_actions:
                if failed_idx < len(action_mask):
                    action_mask[failed_idx] = False

            # Ensure at least one action is valid
            if not action_mask.any():
                logger.warning(f"All actions masked, clearing failed actions set")
                self.failed_actions.clear()
                self.consecutive_failures.clear()
                action_mask = np.array(self.action_encoder.get_action_mask(game), dtype=bool)

            # If a HAND_SELECT screen is ready to confirm, bypass RL to avoid loops.
            from spirecomm.spire.screen import ScreenType
            if getattr(game, "screen_type", None) == ScreenType.HAND_SELECT:
                screen = getattr(game, "screen", None)
                selected_cards = getattr(screen, "selected_cards", []) if screen else []
                num_required = getattr(screen, "num_cards", 0) if screen else 0
                can_pick_zero = getattr(screen, "can_pick_zero", False) if screen else False
                confirm_ready = can_pick_zero or (
                    num_required > 0 and len(selected_cards) >= num_required
                )
                confirm_idx = getattr(self.action_encoder, "CONFIRM_ACTION", None)
                if confirm_ready and confirm_idx is not None and confirm_idx < len(action_mask):
                    if action_mask[confirm_idx]:
                        from spirecomm.communication.action import ConfirmAction

                        return ConfirmAction()

            # Log action mask stats once per combat turn.
            if getattr(game, "screen_type", None) in (None, ScreenType.NONE) and getattr(game, "in_combat", False):
                turn_id = (getattr(game, "floor", 0), getattr(game, "turn", 0))
                if self.last_logged_turn != turn_id:
                    self.last_logged_turn = turn_id
                    valid_actions = int(action_mask.sum())
                    play_actions = int(action_mask[: self.action_encoder.USE_POTION_OFFSET].sum())
                    end_turn_valid = bool(action_mask[self.action_encoder.END_TURN_ACTION]) if self.action_encoder.END_TURN_ACTION < len(action_mask) else False
                    logger.info(
                        "[RL_MASK] floor=%s turn=%s valid=%s play=%s end_turn=%s",
                        getattr(game, "floor", 0),
                        getattr(game, "turn", 0),
                        valid_actions,
                        play_actions,
                        end_turn_valid,
                    )

            # Select action
            if self.training_mode and self.trainer is not None:
                action_idx = self.trainer.select_action(
                    state,
                    action_mask,
                    training=True,
                    epsilon_override=self._get_training_epsilon(game),
                )
            else:
                # Inference mode with optional exploration
                if np.random.random() < self.epsilon:
                    # Exploration
                    valid_actions = np.where(action_mask)[0]
                    action_idx = np.random.choice(valid_actions) if len(valid_actions) > 0 else 0
                else:
                    # Exploitation
                    state_tensor = torch.from_numpy(state).float().unsqueeze(0).to(self.device)
                    mask_tensor = torch.from_numpy(action_mask).unsqueeze(0).to(self.device)

                    with torch.no_grad():
                        action_idx = self.network.get_best_action(state_tensor, mask_tensor).item()

            # Clear failure record for this action (we're trying it again)
            if action_idx in self.failed_actions:
                logger.debug(f"Retrying previously failed action {action_idx}")
                self.failed_actions.discard(action_idx)
                self.consecutive_failures.pop(action_idx, None)

            # Decode action to Action object
            action = self.action_encoder.decode_action(action_idx, game)

            # Log RL choice for all screen types, not just combat
            if getattr(game, "screen_type", None) in (None, ScreenType.NONE) and getattr(game, "in_combat", False):
                # Main combat loop - log with turn info
                logger.info(
                    "[RL_CHOICE] floor=%s turn=%s action_idx=%s action=%s",
                    getattr(game, "floor", 0),
                    getattr(game, "turn", 0),
                    action_idx,
                    type(action).__name__,
                )
            else:
                # Non-combat screens - log with screen type
                logger.info(
                    "[RL_CHOICE_NON_COMBAT] screen=%s floor=%s action_idx=%s action=%s",
                    screen_type,
                    getattr(game, "floor", 0),
                    action_idx,
                    type(action).__name__,
                )

            # Track state and action for training
            if self.training_mode and self.trainer is not None:
                # Calculate reward using RewardCalculator
                if self.pending_reward_action is not None and self.pending_reward_game is not None:
                    # Use RewardCalculator to compare game states and calculate reward
                    reward_info = {}
                    last_action_idx = self.pending_reward_action
                    last_action_name = "Unknown"
                    last_game_for_reward = self.pending_reward_game
                    last_action_mask = self.pending_reward_mask
                    had_play_options = False
                    if last_action_mask is not None:
                        try:
                            had_play_options = bool(
                                last_action_mask[: self.action_encoder.USE_POTION_OFFSET].any()
                            )
                        except Exception:
                            had_play_options = False
                    try:
                        last_action_obj = self.action_encoder.decode_action(
                            last_action_idx, last_game_for_reward
                        )
                        last_action_name = type(last_action_obj).__name__
                    except Exception:
                        last_action_name = "DecodeError"
                    reward = self.reward_calculator.calculate_step_reward(
                        current_game=game,
                        last_game=last_game_for_reward,
                        action_type="combat",
                        debug_info=reward_info,
                        action_context={
                            "action_name": last_action_name,
                            "had_play_options": had_play_options,
                        },
                    )
                    if reward_info:
                        action_detail = ""
                        if last_action_name == "PlayCardAction":
                            try:
                                card = None
                                if hasattr(last_action_obj, "card") and last_action_obj.card is not None:
                                    card = last_action_obj.card
                                elif hasattr(last_action_obj, "card_index"):
                                    idx = int(last_action_obj.card_index)
                                    hand = getattr(last_game_for_reward, "hand", []) or []
                                    if 0 <= idx < len(hand):
                                        card = hand[idx]
                                if card is not None:
                                    card_name = getattr(card, "name", None) or getattr(card, "card_id", None)
                                    card_type = getattr(getattr(card, "type", None), "name", None)
                                    cost = getattr(card, "cost_for_turn", None)
                                    if cost is None:
                                        cost = getattr(card, "cost", None)
                                    action_detail = f" card={card_name} type={card_type} cost={cost}"
                            except Exception:
                                action_detail = ""
                        logger.info(
                            "[RL_REWARD] floor=%s turn=%s action_idx=%s action=%s"
                            "%s reward=%.4f combat=%.4f dmg=%s hp_lost=%s turn_end=%s "
                            "energy_spent=%s block_delta=%s hp_delta=%s "
                            "progress=%.4f acquisition=%.4f card_choice=%.4f terminal=%.4f "
                            "action_bonus=%.4f end_turn_penalty=%.4f",
                            getattr(last_game_for_reward, "floor", 0),
                            getattr(last_game_for_reward, "turn", 0),
                            last_action_idx,
                            last_action_name,
                            action_detail,
                            reward_info.get("reward_total", reward),
                            reward_info.get("combat_reward", 0.0),
                            reward_info.get("damage_dealt", 0),
                            reward_info.get("hp_lost", 0),
                            reward_info.get("turn_ended", False),
                            reward_info.get("energy_spent", 0),
                            reward_info.get("block_delta", 0),
                            reward_info.get("total_monster_hp_delta", 0),
                            reward_info.get("progress_reward", 0.0),
                            reward_info.get("acquisition_reward", 0.0),
                            reward_info.get("card_choice_reward", 0.0),
                            reward_info.get("terminal_reward", 0.0),
                            reward_info.get("action_bonus", 0.0),
                            reward_info.get("end_turn_penalty", 0.0),
                        )

                    # Check for game over
                    done = "GAME_OVER" in str(game.screen_type) or (
                        hasattr(game, 'player') and game.player is not None and
                        hasattr(game.player, 'current_hp') and game.player.current_hp <= 0
                    )
                else:
                    # First action, no reward yet
                    reward = 0.0
                    done = False

                # Store transition (if we have a last_state)
                if self.last_state is not None and self.pending_reward_action is not None:
                    self.trainer.store_transition(
                        self.last_state,
                        self.pending_reward_action,
                        reward,
                        state,
                        done,
                        action_mask=self.pending_reward_mask,
                        next_action_mask=action_mask,
                    )

                # Train periodically (every step if buffer is ready and train_freq allows)
                try:
                    loss = self.trainer.train_step()
                    if loss is not None:
                        self.episode_reward += reward
                        self.episode_steps += 1
                        logger.debug(f"Training step {self.trainer.total_steps}, loss: {loss:.4f}, reward: {reward:.2f}")
                except Exception as e:
                    # Training error should not block decision making
                    logger.warning(f"Training step failed (continuing with inference): {e}")
                    import traceback
                    logger.debug(traceback.format_exc())

            # Update last state, action, and game
            self.last_state = state
            self.last_action = action_idx
            self.last_action_mask = action_mask
            self.last_game = game
            if self.training_mode and self.trainer is not None:
                self.pending_reward_action = action_idx
                self.pending_reward_mask = action_mask
                self.pending_reward_game = game

            return action

        except Exception as e:
            import traceback
            logger.error(f"Error in get_next_action_in_game: {e}\n" + "".join(traceback.format_exc()))
            # Return safe fallback action
            from spirecomm.communication.action import EndTurnAction
            return EndTurnAction()

    def reset(self) -> None:
        """Reset agent state for new episode."""
        self.last_state = None
        self.last_action = None
        self.last_action_mask = None
        self.last_game = None  # Reset game state tracking
        self.episode_reward = 0.0
        self.episode_steps = 0
        self.pending_reward_action = None
        self.pending_reward_mask = None
        self.pending_reward_game = None

        # Clear failed action tracking for new episode
        self.failed_actions.clear()
        self.consecutive_failures.clear()

        if self.training_mode and self.trainer is not None:
            self.trainer.update_episode_count()
            # Reset reward calculator tracking for new episode
            self.reward_calculator.reset()
            # NOTE: Don't clear replay buffer - we need to accumulate experience across episodes
            # Only clear if buffer has mixed dimension data (shouldn't happen after fixes)

    def _get_training_epsilon(self, game: Game) -> float:
        base_epsilon = self.trainer.epsilon if self.trainer is not None else 0.0
        room_type = str(getattr(game, 'room_type', '') or '').lower()
        is_boss = "boss" in room_type

        if is_boss:
            return min(1.0, max(base_epsilon, self.boss_min_epsilon))

        return base_epsilon

    def handle_error(self, error):
        """
        Handle errors from Communication Mod.

        Logs the error, tracks failed actions to prevent loops, and returns a safe action.
        """
        logger.error(f"RL Agent error: {error}")

        # Track failed action to prevent repeated failures
        if hasattr(self, 'last_action') and self.last_action is not None:
            action_idx = self.last_action
            self.consecutive_failures[action_idx] = self.consecutive_failures.get(action_idx, 0) + 1

            # If action has failed too many times, add to blocked set
            if self.consecutive_failures[action_idx] >= self.max_consecutive_failures:
                if action_idx not in self.failed_actions:
                    logger.warning(f"Action {action_idx} failed {self.consecutive_failures[action_idx]} times, disabling temporarily")
                self.failed_actions.add(action_idx)

        # Import StateAction to get current state instead of raising
        from spirecomm.communication.action import StateAction
        return StateAction()

    def get_next_action_out_of_game(self):
        """
        Handle out-of-game states (main menu, character select, etc.).

        Always returns StartGameAction to start a new game with the chosen character.
        """
        from spirecomm.communication.action import StartGameAction
        return StartGameAction(self.chosen_class)

    def load_model(self, model_path: str) -> None:
        """Load model from checkpoint file."""
        checkpoint = torch.load(model_path, map_location=self.device)
        detected_type = detect_network_type_from_checkpoint(checkpoint)
        if detected_type != self.network_type:
            logger.warning(
                "Checkpoint network type %s differs from current %s; switching.",
                detected_type,
                self.network_type,
            )
            self.network_type = detected_type

        # Create network if needed
        if not hasattr(self, 'network') or self.network is None:
            self.network = create_dqn(self.network_type, state_dim=self.state_encoder.feature_dim, device=self.device)
        else:
            current_type = self.network.__class__.__name__
            expected_type = "DuelingDQNetwork" if self.network_type == "dueling" else "DQNetwork"
            if current_type != expected_type:
                self.network = create_dqn(self.network_type, state_dim=self.state_encoder.feature_dim, device=self.device)

        # Load state dict
        if 'online_network_state_dict' in checkpoint:
            # Full checkpoint from trainer
            state_dict, updated = align_state_dict_input(checkpoint['online_network_state_dict'], self.network)
            if updated:
                logger.warning("Checkpoint input dim mismatch; aligning weights to current model.")
            self.network.load_state_dict(state_dict, strict=not updated)
            self.network.eval()
        else:
            # Network state dict only
            state_dict, updated = align_state_dict_input(checkpoint, self.network)
            if updated:
                logger.warning("Checkpoint input dim mismatch; aligning weights to current model.")
            self.network.load_state_dict(state_dict, strict=not updated)
            self.network.eval()

    def _infer_network_type(self, model_path: str) -> str:
        try:
            checkpoint = torch.load(model_path, map_location="cpu")
            return detect_network_type_from_checkpoint(checkpoint)
        except Exception as e:
            logger.warning("Failed to infer network type, defaulting to dueling: %s", e)
            return "dueling"

        logger.info(f"Loaded model from {model_path}")

    def save_model(self, model_path: str, episode: int = 0) -> None:
        """
        Save current model to checkpoint file with atomic write operation.

        Uses a temporary file and atomic rename to prevent corruption if the
        process crashes during writing.
        """
        import os
        import shutil
        import tempfile

        if self.training_mode and self.trainer is not None:
            self.trainer.save_checkpoint(model_path, episode)
        else:
            # Save just the network (inference mode)
            checkpoint = {
                'online_network_state_dict': self.network.state_dict(),
                'episode': episode,
            }

            # Atomic write: save to temporary file first, then rename
            temp_fd, temp_path = tempfile.mkstemp(
                dir=os.path.dirname(model_path),
                prefix=os.path.basename(model_path) + '.tmp_'
            )

            try:
                # Close the file descriptor (torch.save will handle opening)
                os.close(temp_fd)

                # Save to temporary file
                torch.save(checkpoint, temp_path)

                # Atomic rename (overwrites existing file if present)
                shutil.move(temp_path, model_path)

                logger.info(f"Saved model to {model_path}")

            except Exception as e:
                # Clean up temporary file if something went wrong
                try:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                except:
                    pass
                raise



# Convenience function for creating agents
def create_agent(
    model_path: Optional[str] = None,
    training: bool = False,
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
) -> RLAgent:
    """
    Create RL agent with specified configuration.

    Args:
        model_path: Path to saved model
        training: Whether in training mode
        device: Device for neural network

    Returns:
        Initialized RLAgent
    """
    return RLAgent(
        model_path=model_path,
        training=training,
        device=device
    )


class CombatRLAgent:
    """
    Combat-only RL agent with OptimizedAgent fallback.

    Delegates non-combat decisions to OptimizedAgent, uses RL only for
    main combat loop (playing cards/potions/ending turn).

    Architecture:
    - RLAgent handles: main combat loop (play cards, use potions, end turn)
    - OptimizedAgent handles: everything else (map, shop, events, rewards)

    Fallback: If RL fails, immediately falls back to OptimizedAgent for all decisions.
    """

    def __init__(
        self,
        player_class: PlayerClass = PlayerClass.IRONCLAD,
        training: bool = False,
        model_path: Optional[str] = None,
        device: str = "cuda" if torch.cuda.is_available() else "cpu",
        epsilon: float = 0.0,
        elite_mode: Optional[str] = None,
    ):
        """
        Initialize CombatRLAgent with RL and OptimizedAgent instances.

        Args:
            player_class: Character to play
            training: Enable RL training mode
            model_path: Path to pretrained RL model
            device: Torch device
            epsilon: Exploration rate (0.0 = greedy, 1.0 = full random)
            elite_mode: Elite routing mode ("conservative" or "aggressive")
        """
        self.player_class = player_class
        self.use_rl_for_combat = True
        self.rl_failure_count = 0
        self.max_rl_failures = 3
        self.reward_screen_wait = 0.2
        self._reward_screen_key = None
        self._reward_screen_waited = False

        # Import OptimizedAgent
        try:
            from spirecomm.ai.agent import OptimizedAgent, OPTIMIZED_AI_AVAILABLE
            if OPTIMIZED_AI_AVAILABLE:
                self.fallback_agent = OptimizedAgent(chosen_class=player_class, elite_mode=elite_mode)
            else:
                from spirecomm.ai.agent import SimpleAgent
                self.fallback_agent = SimpleAgent(chosen_class=player_class, elite_mode=elite_mode)
                logger.warning("OptimizedAgent not available, using SimpleAgent for fallback")
        except ImportError as e:
            logger.error(f"Failed to import OptimizedAgent: {e}")
            from spirecomm.ai.agent import SimpleAgent
            self.fallback_agent = SimpleAgent(chosen_class=player_class, elite_mode=elite_mode)

        # Initialize RL agent
        self.rl_agent = RLAgent(
            model_path=model_path,
            training=training,
            device=device,
            epsilon=epsilon
        )

        logger.info(f"CombatRLAgent initialized: player_class={player_class}, training={training}")

    def get_next_action_in_game(self, game: Game) -> Action:
        """
        Route decision to RL or OptimizedAgent based on game state.

        Routing logic:
        1. If in main combat loop → RLAgent (if enabled and not failed)
        2. All other cases → OptimizedAgent

        Args:
            game: Current game state

        Returns:
            Action to execute
        """
        # Run tracking logic from fallback_agent before any decision
        # This ensures statistics are collected even when RL is used
        if hasattr(self.fallback_agent, '_track_game_state'):
            try:
                self.fallback_agent._track_game_state(game)
            except Exception as e:
                logger.debug(f"Tracking failed: {e}")

        debounce_action = self._maybe_debounce_reward_screen(game)
        if debounce_action is not None:
            return debounce_action

        # Check if we should use RL for any in-combat screen
        from spirecomm.spire.screen import ScreenType
        current_screen = getattr(game, 'screen_type', None)
        logger.info(f"[CombatRLAgent] screen={current_screen}, use_rl_for_combat={self.use_rl_for_combat}, rl_failure_count={self.rl_failure_count}")

        if self.use_rl_for_combat and self._is_rl_context(game):
            logger.info(f"[CombatRLAgent] Calling RL agent for decision")
            try:
                action = self.rl_agent.get_next_action_in_game(game)

                logger.info(f"[CombatRLAgent] RL returned: {type(action).__name__} - {action}")

                # Check if RL returned None
                if action is None:
                    logger.warning("RL agent returned None, falling back to OptimizedAgent")
                    self.rl_failure_count += 1
                elif self._is_valid_combat_action(action, game):
                    logger.info(f"[CombatRLAgent] RL action validated, returning it")
                    # Valid action for current combat context
                    self.rl_failure_count = 0  # Reset on success
                    from spirecomm.spire.screen import ScreenType

                    if getattr(game, "screen_type", None) == ScreenType.CARD_REWARD:
                        from spirecomm.communication.action import CancelAction

                        if isinstance(action, CancelAction) and hasattr(
                            self.fallback_agent, "skipped_cards"
                        ):
                            self.fallback_agent.skipped_cards = True
                    return action
                else:
                    # Invalid action type
                    logger.warning(f"RL agent returned non-combat action during combat, falling back to OptimizedAgent")
                    self.rl_failure_count += 1
            except Exception as e:
                logger.error(f"RL agent failed: {e}, falling back to OptimizedAgent")
                import traceback
                logger.debug(traceback.format_exc())
                self.rl_failure_count += 1

            # Disable RL after too many failures
            if self.rl_failure_count >= self.max_rl_failures:
                logger.warning(f"RL agent failed {self.rl_failure_count} times, disabling for rest of game")
                self.use_rl_for_combat = False

        # Fallback to OptimizedAgent
        return self.fallback_agent.get_next_action_in_game(game)

    def _maybe_debounce_reward_screen(self, game: Game) -> Optional[Action]:
        from spirecomm.spire.screen import ScreenType

        screen_type = getattr(game, "screen_type", None)
        if screen_type not in (ScreenType.COMBAT_REWARD, ScreenType.CARD_REWARD):
            self._reward_screen_key = None
            self._reward_screen_waited = False
            return None

        reward_count = 0
        screen = getattr(game, "screen", None)
        if screen_type == ScreenType.COMBAT_REWARD:
            rewards = getattr(screen, "rewards", None) or []
            reward_count = len(rewards) if rewards else len(getattr(game, "choice_list", []) or [])
        elif screen_type == ScreenType.CARD_REWARD:
            cards = getattr(screen, "cards", None) or []
            reward_count = len(cards) if cards else len(getattr(game, "choice_list", []) or [])

        key = (getattr(game, "floor", None), str(screen_type), reward_count)
        if key != self._reward_screen_key:
            self._reward_screen_key = key
            self._reward_screen_waited = False

        if not self._reward_screen_waited:
            self._reward_screen_waited = True
            import time

            time.sleep(self.reward_screen_wait)
            return None

        return None

    def _is_in_combat_context(self, game: Game) -> bool:
        """
        Detect if we're in combat (main loop or combat popups).

        Uses game.in_combat to gate combat-only RL usage. This allows the RL
        agent to handle in-combat popup screens like HAND_SELECT/GRID.
        """
        return hasattr(game, 'in_combat') and game.in_combat

    def _is_rl_context(self, game: Game) -> bool:
        """
        Extend RL usage beyond combat to include card rewards.
        """
        from spirecomm.spire.screen import ScreenType

        in_combat = self._is_in_combat_context(game)
        screen_type = getattr(game, 'screen_type', None)

        logger.info(f"[RL_CONTEXT] in_combat={in_combat}, screen_type={screen_type}")

        if in_combat:
            logger.info(f"[RL_CONTEXT] Returning True (in combat)")
            return True

        result = screen_type == ScreenType.CARD_REWARD
        logger.info(f"[RL_CONTEXT] CARD_REWARD check: {result} (expected True for card rewards)")
        return result

    def _is_valid_combat_action(self, action: Action, game: Game) -> bool:
        """
        Validate that RL returned an action appropriate for current combat context.
        """
        from spirecomm.communication.action import (
            PlayCardAction,
            PotionAction,
            EndTurnAction,
            ChooseAction,
            ProceedAction,
            ConfirmAction,
            CancelAction,
            ClickAction,
            KeyAction,
            CombatRewardAction,
            CardRewardAction,
        )
        from spirecomm.spire.screen import ScreenType

        # Main combat loop expects combat actions
        if getattr(game, 'screen_type', None) in (None, ScreenType.NONE):
            return isinstance(action, (PlayCardAction, PotionAction, EndTurnAction))

        # Combat popups accept selection/proceed actions
        return isinstance(
            action,
            (
                ChooseAction,
                ProceedAction,
                ConfirmAction,
                CancelAction,
                ClickAction,
                KeyAction,
                CombatRewardAction,
                CardRewardAction,
            ),
        )

    def get_next_action_out_of_game(self) -> Action:
        """Delegate out-of-game decisions to OptimizedAgent."""
        return self.fallback_agent.get_next_action_out_of_game()

    def handle_error(self, error):
        """
        Handle errors by routing to OptimizedAgent.

        If RL agent fails, increment failure counter and potentially disable RL.

        Args:
            error: Error from Communication Mod

        Returns:
            Safe action to take
        """
        logger.error(f"CombatRLAgent error: {error}")

        # Increment RL failure count
        if self.use_rl_for_combat:
            self.rl_failure_count += 1
            if self.rl_failure_count >= self.max_rl_failures:
                logger.warning(f"RL agent failed {self.rl_failure_count} times, disabling")
                self.use_rl_for_combat = False

        # Route to fallback agent
        return self.fallback_agent.handle_error(error)

    def reset(self) -> None:
        """Reset both RL and OptimizedAgent for new episode."""
        self.rl_agent.reset()

        # Reset RL failure tracking for new game
        self.use_rl_for_combat = True
        self.rl_failure_count = 0
        self._reward_screen_key = None
        self._reward_screen_waited = False

        # Reset OptimizedAgent game tracker if available
        if hasattr(self.fallback_agent, 'game_tracker'):
            try:
                from spirecomm.ai.tracker import GameTracker
                self.fallback_agent.game_tracker = GameTracker()
                self.fallback_agent.game_tracker.player_class = str(self.player_class).replace('PlayerClass.', '')
            except Exception as e:
                logger.warning(f"Failed to reset game tracker: {e}")

    def save_model(self, model_path: str, episode: int = 0) -> None:
        """Save RL model checkpoint."""
        self.rl_agent.save_model(model_path, episode)
