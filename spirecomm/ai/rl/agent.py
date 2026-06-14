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
from .checkpoint_io import load_torch_checkpoint
from spirecomm.spire.game import Game
from spirecomm.communication.action import Action
from spirecomm.ai.incoming_damage import (
    known_unknown_move_has_no_immediate_damage,
    known_unknown_move_immediate_damage,
)
from spirecomm.ai.heuristics.card_costs import effective_card_cost
from spirecomm.ai.heuristics.card_exhaust import card_exhausts_itself
from spirecomm.ai.heuristics.card_hits import fixed_attack_hit_count, strike_card_count
from spirecomm.ai.heuristics.card_upgrades import (
    card_upgrade_count,
    known_block_upgrade_bonus,
    known_damage_upgrade_bonus,
    perfected_strike_bonus_per_strike,
)
from spirecomm.ai.heuristics.card_types import (
    COMMON_AOE_ATTACK_NAMES,
    card_play_conditions_allow,
    card_requires_target,
    card_type_name,
    is_attack_card,
)
from spirecomm.ai.heuristics.combat_state import (
    card_play_key,
    draw_pile_count,
    player_debuff_stacks,
    player_has_power,
    player_power_amount,
)
from spirecomm.data.loader import game_data_loader
from spirecomm.ai.heuristics.potions import (
    game_potion_available,
    game_real_potions,
    potion_can_use,
    potion_is_exhaust_hand_select,
)
from spirecomm.ai.intent_utils import intent_is_unknown, monster_intends_attack
from spirecomm.spire.character import PlayerClass
from spirecomm.spire.identifiers import potion_id
from spirecomm.spire.numeric import coerce_int

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

            # Log action mask stats for debugging
            if screen_type not in (None, ScreenType.NONE):
                valid_count = int(action_mask.sum())
                valid_indices = np.where(action_mask)[0].tolist()[:20]
                logger.info(f"[RLAgent] action_mask: total_valid={valid_count}, sample_indices={valid_indices}")

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
                num_required = self._safe_int(num_required, default=0)
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
                    card = None
                    card_name = None
                    played_card_type = None
                    card_cost = None
                    if last_action_name == "PlayCardAction":
                        try:
                            if hasattr(last_action_obj, "card") and last_action_obj.card is not None:
                                card = last_action_obj.card
                            elif hasattr(last_action_obj, "card_index"):
                                idx = int(last_action_obj.card_index)
                                hand = getattr(last_game_for_reward, "hand", []) or []
                                if 0 <= idx < len(hand):
                                    card = hand[idx]
                            if card is not None:
                                card_name = getattr(card, "name", None) or getattr(card, "card_id", None)
                                played_card_type = card_type_name(card) or None
                                card_cost = getattr(card, "cost_for_turn", None)
                                if card_cost is None:
                                    card_cost = getattr(card, "cost", None)
                        except Exception:
                            card = None
                    reward = self.reward_calculator.calculate_step_reward(
                        current_game=game,
                        last_game=last_game_for_reward,
                        action_type="combat",
                        debug_info=reward_info,
                        action_context={
                            "action_name": last_action_name,
                            "had_play_options": had_play_options,
                            "played_card_type": played_card_type,
                        },
                    )
                    if reward_info:
                        action_detail = ""
                        if last_action_name == "PlayCardAction":
                            if card_name is not None:
                                action_detail = f" card={card_name} type={played_card_type} cost={card_cost}"
                        logger.info(
                            "[RL_REWARD] floor=%s turn=%s action_idx=%s action=%s"
                            "%s reward=%.4f combat=%.4f dmg=%s hp_lost=%s turn_end=%s "
                            "energy_spent=%s block_delta=%s hp_delta=%s "
                            "progress=%.4f acquisition=%.4f card_choice=%.4f terminal=%.4f "
                            "action_bonus=%.4f end_turn_penalty=%.4f "
                            "enemy_str=%s enemy_str_penalty=%.4f",
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
                            reward_info.get("enemy_strength_gained", 0),
                            reward_info.get("enemy_strength_gain_penalty", 0.0),
                        )

                    # Check for game over
                    done = self._is_terminal(game)
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

    @staticmethod
    def _is_terminal(game: Game) -> bool:
        if "GAME_OVER" in str(getattr(game, "screen_type", "")):
            return True
        player = getattr(game, "player", None)
        current_hp = RLAgent._safe_int(
            getattr(player, "current_hp", 1) if player is not None else 1,
            default=1,
        )
        return player is not None and current_hp <= 0

    @staticmethod
    def _safe_int(value, default: int = 0) -> int:
        return coerce_int(value, default)

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
        checkpoint = load_torch_checkpoint(model_path, map_location=self.device)
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
            checkpoint = load_torch_checkpoint(model_path, map_location="cpu")
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



class MapRLAgent:
    """
    Minimal RL agent for MAP screen decisions only.

    Uses the same StateEncoder/ActionEncoder and DQNTrainer but only acts on
    ScreenType.MAP and learns from map transitions.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        training: bool = False,
        device: str = "cuda" if torch.cuda.is_available() else "cpu",
        epsilon: float = 0.1,
    ):
        self.device = device
        self.training_mode = training
        self.network_type = "dueling"
        self.state_encoder = StateEncoder()
        self.action_encoder = ActionEncoder()

        if model_path is not None:
            self.network_type = self._infer_network_type(model_path)

        if training:
            self.trainer = DQNTrainer(
                state_dim=self.state_encoder.feature_dim,
                device=device,
                network_type=self.network_type,
            )
        else:
            self.trainer = None

        if model_path is not None:
            self.load_model(model_path)
        else:
            self.network = create_dqn(
                self.network_type,
                state_dim=self.state_encoder.feature_dim,
                device=device,
            )
            self.network.eval()

        self.epsilon = epsilon
        self.last_state = None
        self.pending_action = None
        self.pending_game = None
        self.pending_action_mask = None
        self.episode_steps = 0

    def observe_game(self, game: Game) -> None:
        """Update replay buffer based on the last MAP action."""
        if not self.training_mode or self.trainer is None:
            return
        if (
            self.pending_action is None
            or self.last_state is None
            or self.pending_game is None
        ):
            return

        try:
            reward = self._compute_reward(game, self.pending_game)
            done = self._is_terminal(game)
            next_state = self.state_encoder.encode(game)
            next_mask = np.array(self.action_encoder.get_action_mask(game), dtype=bool)

            self.trainer.store_transition(
                self.last_state,
                self.pending_action,
                reward,
                next_state,
                done,
                action_mask=self.pending_action_mask,
                next_action_mask=next_mask,
            )

            loss = self.trainer.train_step()
            if loss is not None:
                self.episode_steps += 1
        except Exception as e:
            logger.warning(f"[MAP_RL] observe_game failed: {e}")
            import traceback

            logger.debug(traceback.format_exc())
        finally:
            self.last_state = None
            self.pending_action = None
            self.pending_game = None
            self.pending_action_mask = None

    def get_next_action_in_game(self, game: Game) -> Optional[Action]:
        from spirecomm.spire.screen import ScreenType

        if getattr(game, "screen_type", None) != ScreenType.MAP:
            return None

        state = self.state_encoder.encode(game)
        action_mask = np.array(self.action_encoder.get_action_mask(game), dtype=bool)
        if not action_mask.any():
            return None

        if self.training_mode and self.trainer is not None:
            action_idx = self.trainer.select_action(
                state,
                action_mask,
                training=True,
            )
        else:
            if np.random.random() < self.epsilon:
                valid_actions = np.where(action_mask)[0]
                action_idx = (
                    np.random.choice(valid_actions) if len(valid_actions) > 0 else 0
                )
            else:
                state_tensor = torch.from_numpy(state).float().unsqueeze(0).to(
                    self.device
                )
                mask_tensor = (
                    torch.from_numpy(action_mask).unsqueeze(0).to(self.device)
                )
                with torch.no_grad():
                    action_idx = (
                        self.network.get_best_action(state_tensor, mask_tensor).item()
                    )

        action = self.action_encoder.decode_action(action_idx, game)

        self.last_state = state
        self.pending_action = action_idx
        self.pending_game = game
        self.pending_action_mask = action_mask
        return action

    def reset(self) -> None:
        self.last_state = None
        self.pending_action = None
        self.pending_game = None
        self.pending_action_mask = None
        self.episode_steps = 0
        if self.training_mode and self.trainer is not None:
            self.trainer.update_episode_count()

    def save_model(self, model_path: str, episode: int = 0) -> None:
        if self.training_mode and self.trainer is not None:
            self.trainer.save_checkpoint(model_path, episode)
        else:
            checkpoint = {
                "online_network_state_dict": self.network.state_dict(),
                "episode": episode,
            }
            torch.save(checkpoint, model_path)

    def load_model(self, model_path: str) -> None:
        checkpoint = load_torch_checkpoint(model_path, map_location=self.device)
        detected_type = detect_network_type_from_checkpoint(checkpoint)
        if detected_type != self.network_type:
            self.network_type = detected_type
        if not hasattr(self, "network") or self.network is None:
            self.network = create_dqn(
                self.network_type,
                state_dim=self.state_encoder.feature_dim,
                device=self.device,
            )
        state_dict_key = (
            "online_network_state_dict"
            if "online_network_state_dict" in checkpoint
            else None
        )
        state_dict = checkpoint[state_dict_key] if state_dict_key else checkpoint
        state_dict, updated = align_state_dict_input(state_dict, self.network)
        self.network.load_state_dict(state_dict, strict=not updated)
        self.network.eval()

    def _infer_network_type(self, model_path: str) -> str:
        try:
            checkpoint = load_torch_checkpoint(model_path, map_location="cpu")
            return detect_network_type_from_checkpoint(checkpoint)
        except Exception:
            return "dueling"

    def _is_terminal(self, game: Game) -> bool:
        return "GAME_OVER" in str(getattr(game, "screen_type", ""))

    def _compute_reward(self, current_game: Game, last_game: Game) -> float:
        current_floor = getattr(current_game, "floor", 0) or 0
        last_floor = getattr(last_game, "floor", 0) or 0
        floor_delta = max(0, current_floor - last_floor)

        current_act = getattr(current_game, "act", 1) or 1
        last_act = getattr(last_game, "act", 1) or 1

        current_hp = getattr(current_game, "current_hp", None)
        current_max = getattr(current_game, "max_hp", None)
        if current_hp is None and getattr(current_game, "player", None) is not None:
            current_hp = getattr(current_game.player, "current_hp", None)
        if current_max is None and getattr(current_game, "player", None) is not None:
            current_max = getattr(current_game.player, "max_hp", None)

        last_hp = getattr(last_game, "current_hp", None)
        last_max = getattr(last_game, "max_hp", None)
        if last_hp is None and getattr(last_game, "player", None) is not None:
            last_hp = getattr(last_game.player, "current_hp", None)
        if last_max is None and getattr(last_game, "player", None) is not None:
            last_max = getattr(last_game.player, "max_hp", None)

        reward = 0.0
        reward += 0.05 * float(floor_delta)
        if current_act > last_act:
            reward += 1.0

        if current_hp is not None and last_hp is not None:
            max_hp = max(float(last_max or current_max or 1), 1.0)
            hp_loss = max(0.0, float(last_hp) - float(current_hp))
            reward -= 0.2 * (hp_loss / max_hp)

        if self._is_terminal(current_game):
            reward -= 1.0

        return reward


# Convenience function for creating agents
def create_agent(
    model_path: Optional[str] = None,
    training: bool = False,
    device: str = "cuda" if torch.cuda.is_available() else "cpu",
    epsilon: float = 0.0,
    rl_version: Optional[str] = None,
    expert_mix_enabled: Optional[bool] = None,
    expert_mix_prob: Optional[float] = None,
    expert_warmup_steps: Optional[int] = None,
) -> RLAgent:
    """
    Create RL agent with specified configuration.

    Args:
        model_path: Path to saved model
        training: Whether in training mode
        device: Device for neural network
        epsilon: Exploration rate for inference mode
        rl_version: RL space version ("v1" or "v2"); defaults to STS_RL_VERSION or "v1"

    Returns:
        Initialized RL agent
    """
    if rl_version is None:
        import os

        rl_version = os.environ.get("STS_RL_VERSION", "v1")

    if str(rl_version).lower() == "v2":
        from .v2.agent import RLAgentV2

        return RLAgentV2(
            model_path=model_path,
            training=training,
            device=device,
            epsilon=epsilon,
            expert_mix_enabled=expert_mix_enabled,
            expert_mix_prob=expert_mix_prob,
            expert_warmup_steps=expert_warmup_steps,
        )

    return RLAgent(
        model_path=model_path,
        training=training,
        device=device,
        epsilon=epsilon,
    )


class CombatRLAgent:
    """
    Combat-only RL agent with OptimizedAgent fallback.

    Delegates non-combat decisions to OptimizedAgent, uses RL only for
    main combat loop (playing cards/potions/ending turn).

    Architecture:
    - RLAgent handles: main combat loop (play cards, use potions, end turn)
    - MapRLAgent handles: MAP routing decisions
    - OptimizedAgent handles: everything else (shop, events, rewards)

    Fallback: If RL fails, immediately falls back to OptimizedAgent for all decisions.
    """

    ACT1_BOSS_IDENTIFIERS = frozenset({"slimeboss", "hexaghost", "theguardian"})
    GREMLIN_LEADER_IDENTIFIERS = frozenset({"gremlinleader"})
    GUARDIAN_PRESSURE_INCOMING = 24
    GUARDIAN_SHARP_HIDE_DAMAGE = 3
    GUARDIAN_SHARP_HIDE_ASCENSION_19_DAMAGE = 4
    GUARDIAN_SHARP_HIDE_MOVE_IDS = frozenset({5, 6})
    GUARDIAN_SHARP_HIDE_INTENTS = frozenset({"attackbuff", "intentattackbuff"})
    ACT1_BOSS_PRESSURE_HP_RATIO = 0.60
    ACT1_BOSS_PRESSURE_MIN_HP = 20
    ACT1_BOSS_PRESSURE_DAMAGE_RATIO = 0.40
    ACT1_BOSS_PRESSURE_MIN_DAMAGE = 8
    GUARDIAN_PRESSURE_WEAK_ATTACKS = frozenset(
        {
            "clothesline",
            "shockwave",
            "uppercut",
        }
    )
    HEXAGHOST_SETUP_PRIORITY = (
        "shockwave",
        "corruption",
        "darkembrace",
        "firebreathing",
        "inflame",
        "demonform",
        "feelnopain",
        "evolve",
        "metallicize",
        "carnage",
    )
    HEXAGHOST_LOW_VALUE_SETUP_CARDS = frozenset(
        {
            "bash",
            "defend",
            "truegrit",
            "shrugitoff",
            "flamebarrier",
            "ghostlyarmor",
            "powerthrough",
            "impervious",
            "secondwind",
        }
    )
    SLIME_BOSS_VULNERABLE_SETUP_PRIORITY = (
        "thunderclap",
        "bash",
        "uppercut",
        "shockwave",
    )
    SLIME_BOSS_LOW_VALUE_BEFORE_VULNERABLE = frozenset(
        {
            "strike",
            "defend",
            "ironwave",
            "dropkick",
            "cleave",
        }
    )
    ACT1_BOSS_SETUP_POTION_EFFECTS = frozenset(
        {
            "artifact",
            "buff_strength",
            "card_choice_attack",
            "card_choice_power",
            "debuff_vulnerable",
            "debuff_weak",
            "duplicate_next_card",
            "ritual",
            "temp_strength",
            "upgrade_hand",
        }
    )
    ACT1_BOSS_SETUP_POTION_IDS = frozenset(
        {
            "ancientpotion",
            "attackpotion",
            "blessingoftheforge",
            "duplicationpotion",
            "fearpotion",
            "flexpotion",
            "powerpotion",
            "steroidpotion",
            "strengthpotion",
            "weakpotion",
        }
    )
    LOW_VALUE_STATUS_CARDS = frozenset({"slimed"})
    URGENT_ETHEREAL_ATTACKS = frozenset({"carnage"})
    LOW_VALUE_BEFORE_URGENT_ETHEREAL = frozenset(
        {
            "strike",
            "defend",
            "armaments",
            "truegrit",
            "shrugitoff",
        }
    )
    SURVIVAL_BLOCK_CARD_VALUES = {
        "defend": ("Defend", 5),
        "shrugitoff": ("Shrug It Off", 8),
        "flamebarrier": ("Flame Barrier", 12),
        "powerthrough": ("Power Through", 15),
        "truegrit": ("True Grit", 7),
        "ghostlyarmor": ("Ghostly Armor", 10),
        "impervious": ("Impervious", 30),
        "armaments": ("Armaments", 5),
        "ironwave": ("Iron Wave", 5),
        "sentinel": ("Sentinel", 5),
        "goodinstincts": ("Good Instincts", 6),
        "finesse": ("Finesse", 2),
        "safety": ("Safety", 12),
    }
    SURVIVAL_ATTACK_DAMAGE_VALUES = {
        "anger": ("Anger", 6),
        "bash": ("Bash", 8),
        "carnage": ("Carnage", 20),
        "clash": ("Clash", 14),
        "clothesline": ("Clothesline", 12),
        "headbutt": ("Headbutt", 9),
        "hemokinesis": ("Hemokinesis", 15),
        "ironwave": ("Iron Wave", 5),
        "perfectedstrike": ("Perfected Strike", 6),
        "pommelstrike": ("Pommel Strike", 9),
        "pummel": ("Pummel", 2),
        "recklesscharge": ("Reckless Charge", 7),
        "strike": ("Strike", 6),
        "twinstrike": ("Twin Strike", 5),
        "wildstrike": ("Wild Strike", 12),
    }
    CARD_HP_LOSS_VALUES = {
        "bloodletting": 3,
        "offering": 6,
        "hemokinesis": 2,
    }
    SELF_VULNERABLE_CARDS = frozenset({"berserk"})

    def __init__(
        self,
        player_class: PlayerClass = PlayerClass.IRONCLAD,
        training: bool = False,
        model_path: Optional[str] = None,
        device: str = "cuda" if torch.cuda.is_available() else "cpu",
        epsilon: float = 0.0,
        elite_mode: Optional[str] = None,
        rl_version: Optional[str] = None,
        expert_mix_enabled: Optional[bool] = None,
        expert_mix_prob: Optional[float] = None,
        expert_warmup_steps: Optional[int] = None,
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
            rl_version: RL space version ("v1" or "v2")
        """
        self.player_class = player_class
        self.use_rl_for_combat = True
        self.rl_failure_count = 0
        self.max_rl_failures = 3
        self.reward_screen_wait = 0.2
        self._reward_screen_key = None
        self._reward_screen_waited = False
        self._fallback_turn_key = None

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

        if rl_version is None:
            import os

            rl_version = os.environ.get("STS_RL_VERSION", "v1")

        # Initialize RL agent
        if str(rl_version).lower() == "v2":
            from .v2.agent import RLAgentV2

            self.rl_agent = RLAgentV2(
                model_path=model_path,
                training=training,
                device=device,
                epsilon=epsilon,
                expert_mix_enabled=expert_mix_enabled,
                expert_mix_prob=expert_mix_prob,
                expert_warmup_steps=expert_warmup_steps,
            )
        else:
            self.rl_agent = RLAgent(
                model_path=model_path,
                training=training,
                device=device,
                epsilon=epsilon,
            )

        # MAP routing currently handled by fallback agent
        self.map_rl_agent = None

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
        try:
            from spirecomm.ai.sim_divergence import observe_next_state

            observe_next_state(game)
        except Exception as exc:
            logger.debug("sim divergence observation failed: %s", exc)

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

        if (
            self._should_end_reviving_combat_transition(game)
            and self._has_half_dead_awakened_one(game)
        ):
            from spirecomm.communication.action import EndTurnAction

            self._fallback_turn_key = None
            logger.info(
                "[POST_COMBAT_GUARD] Awakened One revive transition; ending turn to advance revive"
            )
            return self._with_combat_action_context(EndTurnAction(), game)

        if self._is_finished_combat_transition(game):
            from spirecomm.communication.action import EndTurnAction, WaitAction

            self._fallback_turn_key = None
            if self._should_end_reviving_combat_transition(game):
                logger.info(
                    "[POST_COMBAT_GUARD] half-dead monster transition; ending turn to advance revive"
                )
                return self._with_combat_action_context(EndTurnAction(), game)
            logger.info(
                "[POST_COMBAT_GUARD] in_combat still true but no monsters alive; waiting for reward transition"
            )
            return WaitAction(timeout=1)

        if self._should_use_fallback_turn_takeover(game):
            logger.info(
                "[ENERGY_GUARD] Continuing fallback turn takeover floor=%s turn=%s",
                getattr(game, "floor", None),
                getattr(game, "turn", None),
            )
            replacement = self._get_slime_split_aoe_survival_replacement(game)
            if replacement is not None:
                logger.info(
                    "[SLIME_SPLIT_SURVIVAL_GUARD] Continuing takeover with %s",
                    self._describe_combat_action(replacement, game),
                )
                return self._with_combat_action_context(replacement, game)

            replacement = self._get_slime_split_weak_pressure_replacement(game)
            if replacement is not None:
                logger.info(
                    "[SLIME_SPLIT_PRESSURE_GUARD] Continuing takeover with %s",
                    self._describe_combat_action(replacement, game),
                )
                return self._with_combat_action_context(replacement, game)

            replacement = self._get_single_card_lethal_attack_replacement(game)
            if replacement is not None:
                logger.info(
                    "[LETHAL_GUARD] Continuing takeover with %s",
                    self._describe_combat_action(replacement, game),
                )
                return self._with_combat_action_context(replacement, game)

            replacement = self._get_survival_block_replacement(game)
            if replacement is not None:
                logger.info(
                    "[SURVIVAL_GUARD] Continuing takeover with %s",
                    self._describe_combat_action(replacement, game),
                )
                return self._with_combat_action_context(replacement, game)

            fallback_action = self.fallback_agent.get_next_action_in_game(game)
            from spirecomm.communication.action import EndTurnAction, PotionAction

            if isinstance(fallback_action, EndTurnAction):
                replacement = self._get_non_end_turn_fallback(game)
                if replacement is not None:
                    logger.info(
                        "[ENERGY_GUARD] Replacing takeover EndTurnAction with %s",
                        self._describe_combat_action(replacement, game),
                    )
                    return self._with_combat_action_context(replacement, game)
                return self._with_combat_action_context(fallback_action, game)

            if isinstance(fallback_action, PotionAction):
                replacement = self._get_energy_guard_takeover_potion_replacement(game)
                if replacement is not None:
                    logger.info(
                        "[ENERGY_GUARD] Replacing takeover PotionAction with %s",
                        self._describe_combat_action(replacement, game),
                    )
                    return self._with_combat_action_context(replacement, game)
                logger.info("[ENERGY_GUARD] Suppressing takeover PotionAction; ending turn")
                return self._with_combat_action_context(EndTurnAction(), game)
            act1_boss_pressure_replacement = self._get_act1_boss_pressure_action_replacement(
                fallback_action,
                game,
            )
            if act1_boss_pressure_replacement is not None:
                logger.info(
                    "[ACT1_BOSS_PRESSURE_GUARD] Replacing takeover action with %s",
                    self._describe_combat_action(
                        act1_boss_pressure_replacement,
                        game,
                    ),
                )
                return self._with_combat_action_context(
                    act1_boss_pressure_replacement,
                    game,
                )
            guardian_pressure_replacement = self._get_guardian_pressure_action_replacement(
                fallback_action,
                game,
            )
            if guardian_pressure_replacement is not None:
                logger.info(
                    "[GUARDIAN_PRESSURE_GUARD] Replacing takeover action with %s",
                    self._describe_combat_action(
                        guardian_pressure_replacement,
                        game,
                    ),
                )
                return self._with_combat_action_context(
                    guardian_pressure_replacement,
                    game,
                )
            if self._is_self_lethal_card_action(fallback_action, game):
                logger.info(
                    "[ENERGY_GUARD] Suppressing takeover self-lethal action %s; ending turn",
                    self._describe_combat_action(fallback_action, game),
                )
                return self._with_combat_action_context(EndTurnAction(), game)
            if self._is_pressure_unsafe_hp_loss_card_action(fallback_action, game):
                logger.info(
                    "[ENERGY_GUARD] Suppressing takeover pressure-unsafe HP-loss action %s; ending turn",
                    self._describe_combat_action(fallback_action, game),
                )
                return self._with_combat_action_context(EndTurnAction(), game)
            self_vulnerable_replacement = self._get_self_vulnerable_pressure_action_replacement(
                fallback_action,
                game,
            )
            if self_vulnerable_replacement is not None:
                if not isinstance(self_vulnerable_replacement, EndTurnAction):
                    self._fallback_turn_key = self._combat_turn_key(game)
                logger.info(
                    "[SELF_VULN_GUARD] Replacing takeover action with %s",
                    self._describe_combat_action(
                        self_vulnerable_replacement,
                        game,
                    ),
                )
                return self._with_combat_action_context(
                    self_vulnerable_replacement,
                    game,
                )
            if not self._is_current_combat_action_playable(fallback_action, game):
                self._fallback_turn_key = None
                replacement = self._repair_current_play_card_target(
                    fallback_action,
                    game,
                )
                if replacement is None:
                    replacement = self._first_playable_card_action(
                        game,
                        avoid_self_lethal=True,
                        avoid_pressure_hp_loss=True,
                        avoid_low_hp_hp_loss_filler=True,
                    )
                if replacement is not None:
                    guarded_replacement = self._get_act1_boss_pressure_action_replacement(
                        replacement,
                        game,
                    )
                    if guarded_replacement is None:
                        guarded_replacement = self._get_gremlin_leader_minion_attack_replacement(
                            replacement,
                            game,
                        )
                    if guarded_replacement is None:
                        guarded_replacement = self._get_guardian_sharp_hide_action_replacement(
                            replacement,
                            game,
                        )
                    if guarded_replacement is None:
                        guarded_replacement = self._get_guardian_pressure_action_replacement(
                            replacement,
                            game,
                        )
                    if guarded_replacement is not None:
                        replacement = guarded_replacement
                    logger.info(
                        "[ENERGY_GUARD] Replacing takeover unplayable action %s with %s",
                        self._describe_combat_action(fallback_action, game),
                        self._describe_combat_action(replacement, game),
                    )
                    return self._with_combat_action_context(replacement, game)
                logger.info(
                    "[ENERGY_GUARD] Suppressing takeover unplayable action %s; ending turn",
                    self._describe_combat_action(fallback_action, game),
                )
                return self._with_combat_action_context(EndTurnAction(), game)
            return self._with_combat_action_context(
                fallback_action, game
            )

        if self.use_rl_for_combat and self._is_rl_context(game):
            potion_action = self._maybe_use_potion_guard(game)
            if potion_action is not None:
                return self._with_combat_action_context(potion_action, game)

            logger.info(f"[CombatRLAgent] Calling RL agent for decision")
            try:
                action = self.rl_agent.get_next_action_in_game(game)

                logger.info("[CombatRLAgent] RL returned: %s", self._describe_combat_action(action, game))

                # Check if RL returned None
                if action is None:
                    logger.warning("RL agent returned None, falling back to OptimizedAgent")
                    self.rl_failure_count += 1
                elif (replacement := self._get_slime_split_aoe_survival_replacement(game)) is not None:
                    self.rl_failure_count = 0
                    self._fallback_turn_key = self._combat_turn_key(game)
                    logger.info(
                        "[SLIME_SPLIT_SURVIVAL_GUARD] Replacing RL action with %s on floor=%s turn=%s",
                        self._describe_combat_action(replacement, game),
                        getattr(game, "floor", None),
                        getattr(game, "turn", None),
                    )
                    return self._with_combat_action_context(replacement, game)
                elif (replacement := self._get_slime_split_weak_pressure_replacement(game)) is not None:
                    self.rl_failure_count = 0
                    self._fallback_turn_key = self._combat_turn_key(game)
                    logger.info(
                        "[SLIME_SPLIT_PRESSURE_GUARD] Replacing RL action with %s on floor=%s turn=%s",
                        self._describe_combat_action(replacement, game),
                        getattr(game, "floor", None),
                        getattr(game, "turn", None),
                    )
                    return self._with_combat_action_context(replacement, game)
                elif (replacement := self._get_slime_split_survival_attack_replacement(action, game)) is not None:
                    self.rl_failure_count = 0
                    self._fallback_turn_key = self._combat_turn_key(game)
                    logger.info(
                        "[SLIME_SPLIT_SURVIVAL_GUARD] Replacing RL action with %s on floor=%s turn=%s",
                        self._describe_combat_action(replacement, game),
                        getattr(game, "floor", None),
                        getattr(game, "turn", None),
                    )
                    return self._with_combat_action_context(replacement, game)
                elif (replacement := self._get_single_card_lethal_attack_replacement(game)) is not None:
                    self.rl_failure_count = 0
                    self._fallback_turn_key = self._combat_turn_key(game)
                    logger.info(
                        "[LETHAL_GUARD] Replacing RL action with %s on floor=%s turn=%s",
                        self._describe_combat_action(replacement, game),
                        getattr(game, "floor", None),
                        getattr(game, "turn", None),
                    )
                    return self._with_combat_action_context(replacement, game)
                elif (replacement := self._get_survival_action_replacement(action, game)) is not None:
                    self.rl_failure_count = 0
                    self._fallback_turn_key = self._combat_turn_key(game)
                    logger.info(
                        "[SURVIVAL_GUARD] Replacing RL action with %s on floor=%s turn=%s",
                        self._describe_combat_action(replacement, game),
                        getattr(game, "floor", None),
                        getattr(game, "turn", None),
                    )
                    return self._with_combat_action_context(replacement, game)
                elif (replacement := self._get_act1_boss_pressure_action_replacement(action, game)) is not None:
                    self.rl_failure_count = 0
                    self._fallback_turn_key = self._combat_turn_key(game)
                    logger.info(
                        "[ACT1_BOSS_PRESSURE_GUARD] Replacing RL action with %s on floor=%s turn=%s",
                        self._describe_combat_action(replacement, game),
                        getattr(game, "floor", None),
                        getattr(game, "turn", None),
                    )
                    return self._with_combat_action_context(replacement, game)
                elif (replacement := self._get_gremlin_leader_minion_attack_replacement(action, game)) is not None:
                    self.rl_failure_count = 0
                    self._fallback_turn_key = self._combat_turn_key(game)
                    logger.info(
                        "[GREMLIN_LEADER_MINION_GUARD] Replacing RL action with %s on floor=%s turn=%s",
                        self._describe_combat_action(replacement, game),
                        getattr(game, "floor", None),
                        getattr(game, "turn", None),
                    )
                    return self._with_combat_action_context(replacement, game)
                elif (replacement := self._get_guardian_sharp_hide_action_replacement(action, game)) is not None:
                    self.rl_failure_count = 0
                    self._fallback_turn_key = self._combat_turn_key(game)
                    logger.info(
                        "[GUARDIAN_SHARP_HIDE_GUARD] Replacing RL action with %s on floor=%s turn=%s",
                        self._describe_combat_action(replacement, game),
                        getattr(game, "floor", None),
                        getattr(game, "turn", None),
                    )
                    return self._with_combat_action_context(replacement, game)
                elif (replacement := self._get_guardian_pressure_action_replacement(action, game)) is not None:
                    self.rl_failure_count = 0
                    self._fallback_turn_key = self._combat_turn_key(game)
                    logger.info(
                        "[GUARDIAN_PRESSURE_GUARD] Replacing RL action with %s on floor=%s turn=%s",
                        self._describe_combat_action(replacement, game),
                        getattr(game, "floor", None),
                        getattr(game, "turn", None),
                    )
                    return self._with_combat_action_context(replacement, game)
                elif (replacement := self._get_self_vulnerable_pressure_action_replacement(action, game)) is not None:
                    from spirecomm.communication.action import EndTurnAction

                    self.rl_failure_count = 0
                    if not isinstance(replacement, EndTurnAction):
                        self._fallback_turn_key = self._combat_turn_key(game)
                    logger.info(
                        "[SELF_VULN_GUARD] Replacing RL action with %s on floor=%s turn=%s",
                        self._describe_combat_action(replacement, game),
                        getattr(game, "floor", None),
                        getattr(game, "turn", None),
                    )
                    return self._with_combat_action_context(replacement, game)
                elif self._should_override_wasteful_end_turn(action, game):
                    replacement = self._get_non_end_turn_fallback(game)
                    if replacement is not None:
                        self._fallback_turn_key = self._combat_turn_key(game)
                        logger.info(
                            "[ENERGY_GUARD] Replacing EndTurnAction with %s and handing off rest of turn",
                            type(replacement).__name__,
                        )
                        return self._with_combat_action_context(replacement, game)
                    logger.info("[ENERGY_GUARD] No safe replacement found; allowing EndTurnAction")
                    return self._with_combat_action_context(action, game)
                elif self._should_override_awakened_one_power(action, game):
                    replacement = self._get_awakened_one_safe_replacement(game)
                    if replacement is not None:
                        from spirecomm.communication.action import EndTurnAction

                        if not isinstance(replacement, EndTurnAction):
                            self._fallback_turn_key = self._combat_turn_key(game)
                        logger.info(
                            "[AWAKENED_POWER_GUARD] Replacing RL power with %s on floor=%s turn=%s",
                            type(replacement).__name__,
                            getattr(game, "floor", None),
                            getattr(game, "turn", None),
                        )
                        return self._with_combat_action_context(replacement, game)
                    logger.info("[AWAKENED_POWER_GUARD] No replacement found; ending turn")
                    from spirecomm.communication.action import EndTurnAction

                    return self._with_combat_action_context(EndTurnAction(), game)
                elif self._should_override_hexaghost_setup_action(action, game):
                    replacement = self._get_hexaghost_setup_replacement(game)
                    if replacement is not None:
                        self.rl_failure_count = 0
                        self._fallback_turn_key = self._combat_turn_key(game)
                        logger.info(
                            "[HEXAGHOST_SETUP_GUARD] Replacing RL setup-window action with %s on floor=%s turn=%s",
                            self._describe_combat_action(replacement, game),
                            getattr(game, "floor", None),
                            getattr(game, "turn", None),
                        )
                        return self._with_combat_action_context(replacement, game)
                    self.rl_failure_count = 0
                    logger.info("[HEXAGHOST_SETUP_GUARD] No setup replacement found; allowing action")
                    return self._with_combat_action_context(action, game)
                elif self._should_override_slime_boss_vulnerable_setup_action(action, game):
                    replacement = self._get_slime_boss_vulnerable_setup_replacement(game)
                    if replacement is not None:
                        self.rl_failure_count = 0
                        self._fallback_turn_key = self._combat_turn_key(game)
                        logger.info(
                            "[SLIME_VULN_GUARD] Replacing RL pre-vulnerable action with %s on floor=%s turn=%s",
                            self._describe_combat_action(replacement, game),
                            getattr(game, "floor", None),
                            getattr(game, "turn", None),
                        )
                        return self._with_combat_action_context(replacement, game)
                    self.rl_failure_count = 0
                    logger.info("[SLIME_VULN_GUARD] No vulnerable setup replacement found; allowing action")
                    return self._with_combat_action_context(action, game)
                elif self._should_override_urgent_ethereal_attack(action, game):
                    replacement = self._get_urgent_ethereal_attack_replacement(game, action)
                    if replacement is not None:
                        self.rl_failure_count = 0
                        self._fallback_turn_key = self._combat_turn_key(game)
                        logger.info(
                            "[ETHEREAL_ATTACK_GUARD] Replacing low-value action with %s on floor=%s turn=%s",
                            self._describe_combat_action(replacement, game),
                            getattr(game, "floor", None),
                            getattr(game, "turn", None),
                        )
                        return self._with_combat_action_context(replacement, game)
                    self.rl_failure_count = 0
                    logger.info("[ETHEREAL_ATTACK_GUARD] No urgent ethereal replacement found; allowing action")
                    return self._with_combat_action_context(action, game)
                elif self._should_override_unproductive_double_tap(action, game):
                    replacement = self._get_double_tap_safe_replacement(game)
                    if replacement is not None:
                        from spirecomm.communication.action import EndTurnAction

                        self.rl_failure_count = 0
                        if not isinstance(replacement, EndTurnAction):
                            self._fallback_turn_key = self._combat_turn_key(game)
                        logger.info(
                            "[DOUBLE_TAP_GUARD] Replacing unproductive Double Tap with %s on floor=%s turn=%s",
                            self._describe_combat_action(replacement, game),
                            getattr(game, "floor", None),
                            getattr(game, "turn", None),
                        )
                        return self._with_combat_action_context(replacement, game)
                    self.rl_failure_count = 0
                    logger.info("[DOUBLE_TAP_GUARD] No safe replacement found; allowing action")
                    return self._with_combat_action_context(action, game)
                elif self._should_override_risky_havoc(action, game):
                    replacement = self._get_havoc_safe_replacement(game)
                    if replacement is not None:
                        from spirecomm.communication.action import EndTurnAction

                        self.rl_failure_count = 0
                        if not isinstance(replacement, EndTurnAction):
                            self._fallback_turn_key = self._combat_turn_key(game)
                        logger.info(
                            "[HAVOC_GUARD] Replacing RL Havoc with %s on floor=%s turn=%s",
                            self._describe_combat_action(replacement, game),
                            getattr(game, "floor", None),
                            getattr(game, "turn", None),
                        )
                        return self._with_combat_action_context(replacement, game)
                    self.rl_failure_count = 0
                    logger.info("[HAVOC_GUARD] No safe replacement found; allowing Havoc")
                    return self._with_combat_action_context(action, game)
                elif self._should_override_low_value_status_card(action, game):
                    replacement = self._get_status_card_safe_replacement(game)
                    if replacement is not None:
                        from spirecomm.communication.action import EndTurnAction

                        self.rl_failure_count = 0
                        if not isinstance(replacement, EndTurnAction):
                            self._fallback_turn_key = self._combat_turn_key(game)
                        logger.info(
                            "[STATUS_CARD_GUARD] Replacing low-value status card with %s on floor=%s turn=%s",
                            self._describe_combat_action(replacement, game),
                            getattr(game, "floor", None),
                            getattr(game, "turn", None),
                        )
                        return self._with_combat_action_context(replacement, game)
                    self.rl_failure_count = 0
                    logger.info("[STATUS_CARD_GUARD] No safe replacement found; allowing status card")
                    return self._with_combat_action_context(action, game)
                elif self._should_override_low_value_potion(action, game):
                    replacement = self._get_non_potion_fallback(game)
                    if replacement is not None:
                        from spirecomm.communication.action import EndTurnAction

                        self.rl_failure_count = 0
                        if not isinstance(replacement, EndTurnAction):
                            self._fallback_turn_key = self._combat_turn_key(game)
                        logger.info(
                            "[POTION_SAVE_GUARD] Replacing low-value RL potion with %s on floor=%s turn=%s",
                            self._describe_combat_action(replacement, game),
                            getattr(game, "floor", None),
                            getattr(game, "turn", None),
                        )
                        return self._with_combat_action_context(replacement, game)
                    self.rl_failure_count = 0
                    logger.info("[POTION_SAVE_GUARD] No replacement found; allowing PotionAction")
                    return self._with_combat_action_context(action, game)
                elif self._is_self_lethal_card_action(action, game):
                    from spirecomm.communication.action import EndTurnAction

                    self.rl_failure_count = 0
                    replacement = self._first_playable_card_action(
                        game,
                        avoid_self_lethal=True,
                        avoid_pressure_hp_loss=True,
                        avoid_low_hp_hp_loss_filler=True,
                    )
                    if replacement is not None:
                        self._fallback_turn_key = self._combat_turn_key(game)
                        logger.info(
                            "[ENERGY_GUARD] Replacing RL self-lethal action %s with %s on floor=%s turn=%s",
                            self._describe_combat_action(action, game),
                            self._describe_combat_action(replacement, game),
                            getattr(game, "floor", None),
                            getattr(game, "turn", None),
                        )
                        return self._with_combat_action_context(replacement, game)
                    logger.info(
                        "[ENERGY_GUARD] Suppressing RL self-lethal action %s; ending turn",
                        self._describe_combat_action(action, game),
                    )
                    return self._with_combat_action_context(EndTurnAction(), game)
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
                    return self._with_combat_action_context(action, game)
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
        return self._with_combat_action_context(
            self.fallback_agent.get_next_action_in_game(game), game
        )

    @staticmethod
    def _with_combat_action_context(action: Optional[Action], game: Game) -> Optional[Action]:
        from spirecomm.communication.action import EndTurnAction
        from spirecomm.ai.decision_trace import write_decision_trace_event

        if isinstance(action, EndTurnAction):
            action.expected_floor = getattr(game, "floor", None)
            action.expected_turn = getattr(game, "turn", None)
        if action is not None and not getattr(action, "_decision_trace_written", False):
            if write_decision_trace_event(action, game, source="combat_rl"):
                action._decision_trace_written = True
        if action is not None:
            try:
                from spirecomm.ai.sim_divergence import record_expected_action

                record_expected_action(action, game)
            except Exception as exc:
                logger.debug("sim divergence expected-state record failed: %s", exc)
        return action

    def _maybe_use_potion_guard(self, game: Game) -> Optional[Action]:
        """Use a potion in dangerous combat states before high-exploration RL acts."""
        from spirecomm.communication.action import PotionAction
        from spirecomm.spire.screen import ScreenType

        if getattr(game, "screen_type", None) not in (None, ScreenType.NONE):
            return None
        if not getattr(game, "in_combat", False) or not game_potion_available(game):
            return None

        potions = [
            potion
            for potion in game_real_potions(game)
            if potion_can_use(potion)
        ]
        if not potions:
            return None

        alive_monsters = self._alive_monsters(game)
        if not alive_monsters:
            return None

        incoming = self._incoming_damage(game)
        current_hp = max(self._safe_int(getattr(game, "current_hp", 0), default=0), 1)
        max_hp = max(
            self._safe_int(getattr(game, "max_hp", current_hp), default=current_hp),
            1,
        )
        hp_pct = current_hp / max_hp
        room_type = str(getattr(game, "room_type", "") or "")
        is_elite = "Elite" in room_type
        is_boss = self._is_boss_combat(game, alive_monsters)
        high_danger = (
            incoming >= current_hp
            or incoming >= max(18, current_hp * 0.45)
            or (hp_pct <= 0.45 and incoming > 0)
            or is_elite
            or is_boss
            or (len(alive_monsters) >= 2 and incoming >= 10)
        )
        if not high_danger:
            return None

        scored = []
        for index, potion in enumerate(potions):
            if self._should_save_act1_boss_setup_potion(
                potion,
                game,
                incoming,
                current_hp,
                hp_pct,
                is_elite,
                is_boss,
            ):
                logger.info(
                    "[POTION_GUARD] Saving %s for Act 1 boss: incoming=%s hp=%s/%s room=%s monsters=%s",
                    getattr(potion, "name", "UNKNOWN"),
                    incoming,
                    current_hp,
                    max_hp,
                    room_type,
                    len(alive_monsters),
                )
                continue
            score = self._score_potion_for_guard(
                potion,
                incoming,
                current_hp,
                hp_pct,
                is_elite,
                is_boss,
                len(alive_monsters),
            )
            if score > 0:
                scored.append((score, index, potion))

        if not scored:
            return None

        _, _, potion = max(scored, key=lambda item: item[0])
        target_index = self._potion_target_index(potion, alive_monsters, game)
        logger.info(
            "[POTION_GUARD] Using %s: incoming=%s hp=%s/%s room=%s monsters=%s target=%s",
            getattr(potion, "name", "UNKNOWN"),
            incoming,
            current_hp,
            max_hp,
            room_type,
            len(alive_monsters),
            target_index,
        )
        if getattr(potion, "requires_target", False):
            return PotionAction(True, potion=potion, target_index=target_index)
        return PotionAction(True, potion=potion)

    @classmethod
    def _should_save_act1_boss_setup_potion(
        cls,
        potion,
        game: Game,
        incoming: int,
        current_hp: int,
        hp_pct: float,
        is_elite: bool,
        is_boss: bool,
    ) -> bool:
        if is_elite or is_boss:
            return False

        act = cls._safe_int(getattr(game, "act", 1), default=1)
        floor = cls._safe_int(getattr(game, "floor", 0), default=0)
        if act != 1 or floor <= 0 or floor >= 16:
            return False

        if incoming >= current_hp:
            return False
        if hp_pct <= 0.45 and incoming > 0:
            return False
        if hp_pct < 0.70:
            return False
        if incoming >= max(24, current_hp * 0.45):
            return False

        effect_type = str(getattr(potion, "effect_type", "") or "")
        identifiers = {
            cls._normalize_identifier(getattr(potion, "potion_id", "")),
            cls._normalize_identifier(getattr(potion, "name", "")),
            cls._normalize_identifier(potion_id(potion)),
        }
        return (
            effect_type in cls.ACT1_BOSS_SETUP_POTION_EFFECTS
            or bool(identifiers & cls.ACT1_BOSS_SETUP_POTION_IDS)
        )

    @staticmethod
    def _score_potion_for_guard(potion, incoming, current_hp, hp_pct, is_elite, is_boss, monster_count) -> int:
        effect_type = str(getattr(potion, "effect_type", "") or "")
        name = str(getattr(potion, "name", "") or "").lower()
        score = 0
        if potion_is_exhaust_hand_select(potion):
            return 0
        utility_choice_effects = {
            "add_miracle",
            "add_shiv",
            "card_choice_attack",
            "card_choice_colorless",
            "card_choice_power",
            "card_choice_skill",
            "discard_draw",
            "duplicate_next_card",
            "fill_potion_slots",
            "play_top_cards",
            "return_discard_card",
            "stance_choice",
            "upgrade_hand",
        }
        if effect_type in utility_choice_effects:
            return 35 if incoming >= 18 else 0
        if (
            effect_type in ("heal", "heal_percent", "regen", "fairy", "max_hp")
            or "heal" in name
            or "regen" in name
            or "fairy" in name
        ):
            if (
                incoming >= current_hp
                or (hp_pct <= 0.45 and (incoming > 0 or is_elite or is_boss))
                or (is_boss and hp_pct <= 0.55 and incoming >= 8)
            ):
                score = 80
        elif effect_type in (
            "block",
            "plated_armor",
            "metallicize",
            "buff_dexterity",
            "temp_dexterity",
            "intangible",
        ) or "block" in name:
            if incoming >= 12:
                score = 70
        elif (
            effect_type.startswith("buff")
            or effect_type.startswith("debuff")
            or effect_type in ("temp_strength", "thorns", "ritual", "artifact")
        ):
            if is_elite or is_boss or incoming >= 16:
                score = 60
        elif effect_type in ("damage", "poison") or "fire" in name or "explosive" in name:
            if is_elite or is_boss or monster_count >= 2 or incoming >= 12:
                score = 65
        elif (
            effect_type in ("energy", "draw", "draw_randomize_cost")
            or "energy" in name
            or "swift" in name
        ):
            if incoming >= 12:
                score = 45
        else:
            if incoming >= 18 or is_elite or is_boss:
                score = 35
        return score

    def _should_override_low_value_potion(self, action: Action, game: Game) -> bool:
        from spirecomm.communication.action import PotionAction
        from spirecomm.spire.screen import ScreenType

        if not isinstance(action, PotionAction):
            return False
        if getattr(game, "screen_type", None) not in (None, ScreenType.NONE):
            return False
        if not getattr(game, "in_combat", False):
            return False
        potion = self._potion_for_action(action, game)
        if potion_is_exhaust_hand_select(potion):
            return True

        room_type = str(getattr(game, "room_type", "") or "")
        if "Boss" in room_type or "Elite" in room_type:
            return False

        floor = self._safe_int(getattr(game, "floor", 0), default=0)
        act = self._safe_int(getattr(game, "act", 1), default=1)
        if act != 1 or floor <= 0 or floor >= 16:
            return False

        alive_monsters = self._alive_monsters(game)
        if not alive_monsters:
            return False

        incoming = self._incoming_damage(game)
        current_hp = max(self._safe_int(getattr(game, "current_hp", 0), default=0), 1)
        max_hp = max(
            self._safe_int(getattr(game, "max_hp", current_hp), default=current_hp),
            1,
        )
        hp_pct = current_hp / max_hp
        if self._should_save_act1_boss_setup_potion(
            potion,
            game,
            incoming,
            current_hp,
            hp_pct,
            is_elite=False,
            is_boss=False,
        ):
            return True

        high_danger = (
            incoming >= current_hp
            or incoming >= max(18, current_hp * 0.45)
            or (hp_pct <= 0.45 and incoming > 0)
            or (len(alive_monsters) >= 2 and incoming >= 10)
        )
        return not high_danger

    def _should_override_wasteful_end_turn(self, action: Action, game: Game) -> bool:
        from spirecomm.communication.action import EndTurnAction
        from spirecomm.spire.screen import ScreenType

        if not isinstance(action, EndTurnAction):
            return False
        if getattr(game, "screen_type", None) not in (None, ScreenType.NONE):
            return False
        if not getattr(game, "play_available", False):
            return False
        energy = self._player_energy(game)
        if energy <= 0:
            return False
        playable = self._playable_cards(game, energy)
        if not playable:
            return False
        incoming = self._incoming_damage(game)
        logger.info(
            "[ENERGY_GUARD] RL ended turn with energy=%s playable=%s incoming=%s floor=%s turn=%s",
            energy,
            len(playable),
            incoming,
            getattr(game, "floor", None),
            getattr(game, "turn", None),
        )
        return True

    def _combat_turn_key(self, game: Game):
        from spirecomm.spire.screen import ScreenType

        if not getattr(game, "in_combat", False):
            return None
        if getattr(game, "screen_type", None) not in (None, ScreenType.NONE):
            return None
        return (getattr(game, "floor", None), getattr(game, "turn", None))

    def _should_use_fallback_turn_takeover(self, game: Game) -> bool:
        active_key = getattr(self, "_fallback_turn_key", None)
        if active_key is None:
            return False

        current_key = self._combat_turn_key(game)
        if current_key != active_key:
            self._fallback_turn_key = None
            return False

        return True

    def _get_non_end_turn_fallback(self, game: Game) -> Optional[Action]:
        from spirecomm.communication.action import EndTurnAction, PlayCardAction, PotionAction

        replacement = self._get_slime_split_aoe_survival_replacement(game)
        if replacement is not None:
            return replacement

        replacement = self._get_slime_split_weak_pressure_replacement(game)
        if replacement is not None:
            return replacement

        replacement = self._get_survival_block_replacement(game)
        if replacement is not None:
            return replacement

        replacement = self._get_act1_boss_pressure_weak_replacement(game)
        if replacement is not None:
            return replacement

        guardian_pressure_replacement = self._get_guardian_pressure_block_replacement(game)

        if self._is_hexaghost_opening_setup_window(game):
            replacement = self._get_hexaghost_setup_replacement(game)
            if replacement is not None:
                return replacement

        try:
            fallback_action = self.fallback_agent.get_next_action_in_game(game)
            if (
                fallback_action is not None
                and not isinstance(fallback_action, (EndTurnAction, PotionAction))
            ):
                if (
                    isinstance(fallback_action, PlayCardAction)
                    and not self._is_current_combat_action_playable(fallback_action, game)
                ):
                    repaired_action = self._repair_current_play_card_target(
                        fallback_action,
                        game,
                    )
                    if repaired_action is not None:
                        logger.info(
                            "[ENERGY_GUARD] Repaired fallback action %s to %s",
                            self._describe_combat_action(fallback_action, game),
                            self._describe_combat_action(repaired_action, game),
                        )
                        fallback_action = repaired_action
                guarded_action = self._get_guardian_sharp_hide_action_replacement(
                    fallback_action,
                    game,
                )
                if guarded_action is not None:
                    return guarded_action
                guarded_action = self._get_gremlin_leader_minion_attack_replacement(
                    fallback_action,
                    game,
                )
                if guarded_action is not None:
                    return guarded_action
                if guardian_pressure_replacement is not None:
                    guarded_action = self._get_guardian_pressure_action_replacement(
                        fallback_action,
                        game,
                    )
                    if guarded_action is not None:
                        return guarded_action
                if self._is_self_lethal_card_action(fallback_action, game):
                    logger.info(
                        "[ENERGY_GUARD] Skipping fallback self-lethal action %s",
                        self._describe_combat_action(fallback_action, game),
                    )
                elif self._is_pressure_unsafe_hp_loss_card_action(fallback_action, game):
                    logger.info(
                        "[ENERGY_GUARD] Skipping fallback pressure-unsafe HP-loss action %s",
                        self._describe_combat_action(fallback_action, game),
                    )
                elif not self._is_current_combat_action_playable(fallback_action, game):
                    logger.info(
                        "[ENERGY_GUARD] Skipping fallback unplayable action %s",
                        self._describe_combat_action(fallback_action, game),
                    )
                else:
                    return fallback_action
        except Exception as exc:
            logger.debug("[ENERGY_GUARD] Fallback action failed: %s", exc)

        if guardian_pressure_replacement is not None:
            return guardian_pressure_replacement

        return self._first_playable_card_action(
            game,
            avoid_self_lethal=True,
            avoid_pressure_hp_loss=True,
            avoid_low_hp_hp_loss_filler=True,
        )

    @classmethod
    def _matching_hand_card_index(cls, wanted_card, hand) -> int:
        if wanted_card is None:
            return -1

        for index, card in enumerate(hand):
            if card is wanted_card:
                return index

        wanted_uuid = getattr(wanted_card, "uuid", None)
        if wanted_uuid is not None:
            for index, card in enumerate(hand):
                if getattr(card, "uuid", None) == wanted_uuid:
                    return index

        wanted_keys = cls._card_match_keys(wanted_card)
        if not wanted_keys:
            return -1
        wanted_upgrades = cls._card_upgrade_count(wanted_card)
        wanted_has_upgrade_attr = cls._has_card_upgrade_attr(wanted_card)

        for index, card in enumerate(hand):
            if not (wanted_keys & cls._card_match_keys(card)):
                continue
            if (
                wanted_has_upgrade_attr
                and cls._has_card_upgrade_attr(card)
                and cls._card_upgrade_count(card) != wanted_upgrades
            ):
                continue
            return index

        return -1

    @classmethod
    def _card_match_keys(cls, card) -> set:
        keys = set()
        for attr in ("card_id", "id", "name"):
            value = getattr(card, attr, None)
            if value is None:
                continue
            normalized = cls._normalize_identifier(value)
            if normalized:
                keys.add(normalized)
        return keys

    @classmethod
    def _has_card_upgrade_attr(cls, card) -> bool:
        return any(hasattr(card, attr) for attr in ("upgrades", "upgrade"))

    @classmethod
    def _card_upgrade_count(cls, card) -> int:
        return cls._safe_int(
            getattr(card, "upgrades", getattr(card, "upgrade", 0)),
            default=0,
        )

    @classmethod
    def _valid_monster_target_index(cls, game: Game, target_index: int) -> bool:
        monsters = getattr(game, "monsters", []) or []
        if target_index < 0 or target_index >= len(monsters):
            return False
        target = monsters[target_index]
        return (
            cls._safe_int(getattr(target, "current_hp", 0), default=0) > 0
            and not getattr(target, "is_gone", False)
            and not getattr(target, "half_dead", False)
        )

    @classmethod
    def _target_index_for_play_card_action(cls, action: Action, game: Game) -> Optional[int]:
        raw_target_index = getattr(action, "target_index", None)
        if raw_target_index is not None:
            target_index = cls._safe_int(raw_target_index, default=-1)
            if cls._valid_monster_target_index(game, target_index):
                return target_index

        target_monster = getattr(action, "target_monster", None)
        if target_monster is None:
            return None

        target_index = cls._safe_int(
            getattr(target_monster, "monster_index", -1),
            default=-1,
        )
        if cls._valid_monster_target_index(game, target_index):
            return target_index

        for index, monster in enumerate(getattr(game, "monsters", []) or []):
            if monster is target_monster and cls._valid_monster_target_index(game, index):
                return index

        return None

    def _repair_current_play_card_target(self, action: Action, game: Game) -> Optional[Action]:
        from spirecomm.communication.action import PlayCardAction

        if not isinstance(action, PlayCardAction):
            return None

        hand = getattr(game, "hand", []) or []
        card_index = self._safe_int(
            getattr(action, "card_index", -1),
            default=-1,
        )
        if card_index < 0:
            card_index = self._matching_hand_card_index(
                getattr(action, "card", None),
                hand,
            )
        if card_index < 0 or card_index >= len(hand):
            return None

        card = hand[card_index]
        if card_requires_target(card):
            target_index = self._target_index_for_play_card_action(action, game)
            if target_index is None:
                target_index = self._best_monster_index(game)
            if target_index is None:
                return None
            repaired = PlayCardAction(
                card_index=card_index,
                target_index=target_index,
            )
        else:
            repaired = PlayCardAction(card_index=card_index)

        if self._is_current_combat_action_playable(repaired, game):
            return repaired
        return None

    def _get_single_card_lethal_attack_replacement(self, game: Game) -> Optional[Action]:
        from spirecomm.communication.action import PlayCardAction
        from spirecomm.spire.screen import ScreenType

        if getattr(game, "screen_type", None) not in (None, ScreenType.NONE):
            return None
        if not getattr(game, "in_combat", False):
            return None

        alive_monsters = self._alive_monsters(game)
        if len(alive_monsters) != 1:
            return None

        monster = alive_monsters[0]
        target_index = getattr(monster, "monster_index", None)
        if target_index is None:
            for index, candidate in enumerate(getattr(game, "monsters", []) or []):
                if candidate is monster:
                    target_index = index
                    break

        effective_hp = (
            self._safe_int(getattr(monster, "current_hp", 0), default=0)
            + self._safe_int(getattr(monster, "block", 0), default=0)
        )
        if effective_hp <= 0:
            return None

        energy = self._player_energy(game)
        best_candidate = None
        for card_index, card in self._playable_cards(game, energy):
            if not is_attack_card(card):
                continue
            if self._would_single_card_lethal_attack_self_kill(card, game):
                continue
            if card_requires_target(card) and target_index is None:
                continue

            source_damage = self._survival_attack_damage_before_player_weak(card, game)
            if source_damage <= 0:
                continue
            attack_damage = self._apply_survival_attack_target_modifiers(
                source_damage,
                game,
                monster,
                hit_count=self._survival_attack_hit_count(card),
            )
            if attack_damage < effective_hp:
                continue

            effective_cost = effective_card_cost(card, energy)
            score = (-effective_cost, attack_damage, -card_index)
            action = (
                PlayCardAction(card_index=card_index, target_index=target_index)
                if card_requires_target(card)
                else PlayCardAction(card_index=card_index)
            )
            if best_candidate is None or score > best_candidate[0]:
                best_candidate = (score, action, card, attack_damage, effective_hp)

        if best_candidate is None:
            return None

        _, action, card, attack_damage, effective_hp = best_candidate
        logger.info(
            "[LETHAL_GUARD] Selecting %s damage=%s effective_hp=%s hp=%s target_block=%s player_hp=%s sharp_hide=%s",
            self._card_label(card),
            attack_damage,
            effective_hp,
            getattr(monster, "current_hp", None),
            getattr(monster, "block", None),
            getattr(game, "current_hp", None),
            self._guardian_sharp_hide_damage(game),
        )
        return action

    def _would_single_card_lethal_attack_self_kill(self, card, game: Game) -> bool:
        hp_loss = self._card_player_hp_loss(card, game)
        current_hp = self._safe_int(getattr(game, "current_hp", 0), default=0)
        if current_hp <= 0:
            return True
        if hp_loss >= current_hp:
            return True

        sharp_hide_damage = self._guardian_sharp_hide_damage(game)
        if sharp_hide_damage <= 0:
            return False

        current_block = self._player_block(game)
        unblocked_sharp_hide = max(0, sharp_hide_damage - current_block)
        return current_hp - hp_loss <= unblocked_sharp_hide

    def _get_survival_action_replacement(self, action: Action, game: Game) -> Optional[Action]:
        from spirecomm.communication.action import PlayCardAction
        from spirecomm.spire.screen import ScreenType

        if not isinstance(action, PlayCardAction):
            return None
        if getattr(game, "screen_type", None) not in (None, ScreenType.NONE):
            return None
        if not getattr(game, "in_combat", False):
            return None

        replacement = self._get_survival_block_replacement(game)
        if not isinstance(replacement, PlayCardAction):
            return None

        current_card = self._card_for_action(action, game)
        replacement_card = self._card_for_action(replacement, game)
        if self._survival_block_value_for_game(
            replacement_card,
            game,
        ) <= self._survival_block_value_for_game(current_card, game):
            return None
        return replacement

    def _get_slime_split_survival_attack_replacement(self, action: Action, game: Game) -> Optional[Action]:
        from spirecomm.communication.action import PlayCardAction
        from spirecomm.spire.screen import ScreenType

        if not isinstance(action, PlayCardAction):
            return None
        if getattr(game, "screen_type", None) not in (None, ScreenType.NONE):
            return None
        if not getattr(game, "in_combat", False):
            return None
        if not self._is_slime_boss_split_phase(game):
            return None

        current_hp = self._safe_int(getattr(game, "current_hp", 0), default=0)
        if current_hp <= 0:
            return None
        current_block = self._player_block(game)
        incoming = self._incoming_damage(game)
        if incoming - current_block < current_hp:
            return None

        card = self._card_for_action(action, game)
        if card is None or not is_attack_card(card) or not card_requires_target(card):
            return None
        card_index = self._safe_int(getattr(action, "card_index", -1), default=-1)
        if card_index < 0:
            return None
        energy = self._player_energy(game)
        if effective_card_cost(card, energy) > energy:
            return None

        source_attack_damage = self._survival_attack_damage_before_player_weak(card, game)
        if source_attack_damage <= 0:
            return None
        source_attack_hits = self._survival_attack_hit_count(card)

        current_target = self._safe_int(getattr(action, "target_index", -1), default=-1)
        best_candidate = None
        for monster_index, monster in enumerate(getattr(game, "monsters", []) or []):
            if not self._is_targetable_monster(monster):
                continue
            if not monster_intends_attack(monster):
                continue
            effective_hp = (
                self._safe_int(getattr(monster, "current_hp", 0), default=0)
                + self._safe_int(getattr(monster, "block", 0), default=0)
            )
            attack_damage = self._apply_survival_attack_target_modifiers(
                source_attack_damage,
                game,
                monster,
                hit_count=source_attack_hits,
            )
            if attack_damage < effective_hp:
                continue
            removed_incoming = self._monster_incoming_damage(monster)
            if removed_incoming <= 0:
                continue
            remaining_damage = max(0, incoming - removed_incoming - current_block)
            if remaining_damage >= current_hp:
                continue
            survival_margin = current_hp - remaining_damage
            score = (survival_margin, removed_incoming, -effective_hp, -monster_index)
            if best_candidate is None or score > best_candidate[0]:
                best_candidate = (
                    score,
                    monster_index,
                    monster,
                    removed_incoming,
                    effective_hp,
                )

        if best_candidate is not None:
            _, target_index, target, removed_incoming, effective_hp = best_candidate
            if current_target == target_index:
                return None

            logger.info(
                "[SLIME_SPLIT_SURVIVAL_GUARD] Retargeting %s to %s index=%s hp=%s removed_incoming=%s",
                self._card_label(card),
                getattr(target, "name", getattr(target, "monster_id", "UNKNOWN")),
                target_index,
                effective_hp,
                removed_incoming,
            )
            return PlayCardAction(card_index=card_index, target_index=target_index)

        best_alternate = None
        for alternate_card_index, alternate_card in self._playable_cards(game, energy):
            if alternate_card_index == card_index:
                continue
            if not is_attack_card(alternate_card) or not card_requires_target(alternate_card):
                continue
            if self._would_play_self_lethal_card(alternate_card, game):
                continue
            effective_cost = effective_card_cost(alternate_card, energy)
            if effective_cost > energy:
                continue

            alternate_damage = self._survival_attack_damage_before_player_weak(
                alternate_card,
                game,
            )
            if alternate_damage <= 0:
                continue
            alternate_hits = self._survival_attack_hit_count(alternate_card)

            for monster_index, monster in enumerate(getattr(game, "monsters", []) or []):
                if not self._is_targetable_monster(monster):
                    continue
                if not monster_intends_attack(monster):
                    continue
                effective_hp = (
                    self._safe_int(getattr(monster, "current_hp", 0), default=0)
                    + self._safe_int(getattr(monster, "block", 0), default=0)
                )
                attack_damage = self._apply_survival_attack_target_modifiers(
                    alternate_damage,
                    game,
                    monster,
                    hit_count=alternate_hits,
                )
                if attack_damage < effective_hp:
                    continue
                removed_incoming = self._monster_incoming_damage(monster)
                if removed_incoming <= 0:
                    continue
                remaining_damage = max(0, incoming - removed_incoming - current_block)
                if remaining_damage >= current_hp:
                    continue
                survival_margin = current_hp - remaining_damage
                score = (
                    survival_margin,
                    removed_incoming,
                    attack_damage,
                    -effective_cost,
                    -alternate_card_index,
                    -monster_index,
                )
                if best_alternate is None or score > best_alternate[0]:
                    best_alternate = (
                        score,
                        alternate_card_index,
                        alternate_card,
                        monster_index,
                        monster,
                        removed_incoming,
                        effective_hp,
                    )

        if best_alternate is None:
            return None

        _, alternate_card_index, alternate_card, target_index, target, removed_incoming, effective_hp = (
            best_alternate
        )
        logger.info(
            "[SLIME_SPLIT_SURVIVAL_GUARD] Replacing %s with %s targeting %s index=%s hp=%s removed_incoming=%s",
            self._card_label(card),
            self._card_label(alternate_card),
            getattr(target, "name", getattr(target, "monster_id", "UNKNOWN")),
            target_index,
            effective_hp,
            removed_incoming,
        )
        return PlayCardAction(card_index=alternate_card_index, target_index=target_index)

    def _get_gremlin_leader_minion_attack_replacement(self, action: Action, game: Game) -> Optional[Action]:
        from spirecomm.communication.action import PlayCardAction
        from spirecomm.spire.screen import ScreenType

        if not isinstance(action, PlayCardAction):
            return None
        if getattr(game, "screen_type", None) not in (None, ScreenType.NONE):
            return None
        if not getattr(game, "in_combat", False):
            return None
        if not self._is_gremlin_leader_combat(game):
            return None

        current_hp = self._safe_int(getattr(game, "current_hp", 0), default=0)
        if current_hp <= 0:
            return None

        incoming = self._incoming_damage(game)
        if incoming <= 0:
            return None
        max_hp = max(
            self._safe_int(getattr(game, "max_hp", current_hp), default=current_hp),
            1,
        )
        current_block = self._player_block(game)
        status_blockable_damage, status_hp_loss = self._end_turn_status_damage(game)
        current_damage = self._end_turn_aggregate_damage_after_block(
            incoming + status_blockable_damage,
            status_hp_loss,
            self._end_turn_block_for_game(game, current_block),
            game,
        )
        if (
            current_damage < max(18, current_hp * 0.45)
            and current_hp / max_hp > 0.45
        ):
            return None

        card = self._card_for_action(action, game)
        if card is None or not is_attack_card(card) or not card_requires_target(card):
            return None
        if self._would_play_self_lethal_card(card, game):
            return None
        card_index = self._safe_int(getattr(action, "card_index", -1), default=-1)
        if card_index < 0:
            return None
        energy = self._player_energy(game)
        if effective_card_cost(card, energy) > energy:
            return None

        source_attack_damage = self._survival_attack_damage_before_player_weak(card, game)
        if source_attack_damage <= 0:
            return None
        source_attack_hits = self._survival_attack_hit_count(card)

        current_target = self._safe_int(getattr(action, "target_index", -1), default=-1)
        best_candidate = None
        for monster_index, monster in enumerate(getattr(game, "monsters", []) or []):
            if not self._is_targetable_monster(monster):
                continue
            if self._is_gremlin_leader_monster(monster):
                continue
            removed_incoming = self._monster_incoming_damage(monster)
            if removed_incoming <= 0:
                continue

            effective_hp = (
                self._safe_int(getattr(monster, "current_hp", 0), default=0)
                + self._safe_int(getattr(monster, "block", 0), default=0)
            )
            attack_damage = self._apply_survival_attack_target_modifiers(
                source_attack_damage,
                game,
                monster,
                hit_count=source_attack_hits,
            )
            if attack_damage < effective_hp:
                continue

            damage_after_candidate = self._end_turn_aggregate_damage_after_block(
                incoming - removed_incoming + status_blockable_damage,
                status_hp_loss,
                self._end_turn_block_for_game(game, current_block),
                game,
            )
            if damage_after_candidate >= current_damage:
                continue

            damage_reduced = current_damage - damage_after_candidate
            survival_margin = current_hp - damage_after_candidate
            score = (
                damage_reduced,
                removed_incoming,
                survival_margin,
                -effective_hp,
                -monster_index,
            )
            if best_candidate is None or score > best_candidate[0]:
                best_candidate = (
                    score,
                    monster_index,
                    monster,
                    removed_incoming,
                    effective_hp,
                )

        if best_candidate is None:
            return None
        _, target_index, target, removed_incoming, effective_hp = best_candidate
        if current_target == target_index:
            return None

        logger.info(
            "[GREMLIN_LEADER_MINION_GUARD] Retargeting %s to %s index=%s hp=%s removed_incoming=%s",
            self._card_label(card),
            getattr(target, "name", getattr(target, "monster_id", "UNKNOWN")),
            target_index,
            effective_hp,
            removed_incoming,
        )
        return PlayCardAction(card_index=card_index, target_index=target_index)

    def _get_guardian_sharp_hide_action_replacement(self, action: Action, game: Game) -> Optional[Action]:
        from spirecomm.communication.action import EndTurnAction, PlayCardAction
        from spirecomm.spire.screen import ScreenType

        if not isinstance(action, PlayCardAction):
            return None
        if getattr(game, "screen_type", None) not in (None, ScreenType.NONE):
            return None
        if not getattr(game, "in_combat", False):
            return None

        current_card = self._card_for_action(action, game)
        if not is_attack_card(current_card):
            return None

        sharp_hide_damage = self._guardian_sharp_hide_damage(game)
        if sharp_hide_damage <= 0:
            return None

        current_hp = self._safe_int(getattr(game, "current_hp", 0), default=0)
        if current_hp <= 0:
            return None

        incoming = self._incoming_damage(game)
        status_blockable_damage, status_hp_loss = self._end_turn_status_damage(game)
        current_block = self._player_block(game)
        damage_without_attack = self._end_turn_damage_after_block(
            incoming + status_blockable_damage,
            status_hp_loss,
            current_block,
            game,
        )
        immediate_sharp_hide_damage = max(0, sharp_hide_damage - current_block)
        if damage_without_attack >= current_hp and immediate_sharp_hide_damage >= current_hp:
            logger.info(
                "[GUARDIAN_SHARP_HIDE_GUARD] Ending turn to avoid immediate lethal Sharp Hide attack hp=%s incoming=%s status_blockable_damage=%s status_hp_loss=%s sharp_hide=%s current_block=%s",
                current_hp,
                incoming,
                status_blockable_damage,
                status_hp_loss,
                sharp_hide_damage,
                current_block,
            )
            return EndTurnAction()
        if damage_without_attack >= current_hp:
            return None

        damage_with_attack = self._end_turn_damage_after_block(
            incoming + sharp_hide_damage + status_blockable_damage,
            status_hp_loss,
            current_block,
            game,
        )
        max_hp = self._safe_int(getattr(game, "max_hp", 0), default=0)
        low_hp_sharp_hide_pressure = (
            incoming > 0
            and current_hp <= max(16, max_hp // 4)
            and damage_with_attack > damage_without_attack
        )
        low_margin_after_attack = (
            incoming > 0
            and damage_with_attack < current_hp
            and current_hp - damage_with_attack <= sharp_hide_damage * 2
        )
        if (
            damage_with_attack < current_hp
            and not low_margin_after_attack
            and not low_hp_sharp_hide_pressure
        ):
            return None

        candidate = self._best_block_action_candidate(game)
        if candidate is not None:
            replacement, card, block_value = candidate
            damage_with_block = self._end_turn_damage_after_block(
                incoming + status_blockable_damage,
                status_hp_loss,
                current_block + block_value,
                game,
            )
            if (
                block_value > self._survival_block_value(current_card)
                and (
                    not low_hp_sharp_hide_pressure
                    or damage_with_block < damage_with_attack
                )
            ):
                logger.info(
                    "[GUARDIAN_SHARP_HIDE_GUARD] Selecting %s for block=%s hp=%s incoming=%s status_blockable_damage=%s status_hp_loss=%s sharp_hide=%s current_block=%s",
                    self._card_label(card),
                    block_value,
                    current_hp,
                    incoming,
                    status_blockable_damage,
                    status_hp_loss,
                    sharp_hide_damage,
                    current_block,
                )
                return replacement

        if low_margin_after_attack:
            if low_hp_sharp_hide_pressure and damage_with_attack > damage_without_attack:
                logger.info(
                    "[GUARDIAN_SHARP_HIDE_GUARD] Ending turn to preserve low-HP Sharp Hide margin hp=%s incoming=%s status_blockable_damage=%s status_hp_loss=%s sharp_hide=%s current_block=%s damage_without_attack=%s damage_with_attack=%s",
                    current_hp,
                    incoming,
                    status_blockable_damage,
                    status_hp_loss,
                    sharp_hide_damage,
                    current_block,
                    damage_without_attack,
                    damage_with_attack,
                )
                return EndTurnAction()
            return None

        logger.info(
            "[GUARDIAN_SHARP_HIDE_GUARD] Ending turn to avoid lethal Sharp Hide attack hp=%s incoming=%s status_blockable_damage=%s status_hp_loss=%s sharp_hide=%s current_block=%s",
            current_hp,
            incoming,
            status_blockable_damage,
            status_hp_loss,
            sharp_hide_damage,
            current_block,
        )
        return EndTurnAction()

    def _get_guardian_pressure_action_replacement(self, action: Action, game: Game) -> Optional[Action]:
        from spirecomm.communication.action import PlayCardAction
        from spirecomm.spire.screen import ScreenType

        if not isinstance(action, PlayCardAction):
            return None
        if getattr(game, "screen_type", None) not in (None, ScreenType.NONE):
            return None
        if not getattr(game, "in_combat", False):
            return None

        current_card = self._card_for_action(action, game)
        if self._card_matches_normalized_names(current_card, self.GUARDIAN_PRESSURE_WEAK_ATTACKS):
            return None

        replacement = self._get_guardian_pressure_block_replacement(game)
        if not isinstance(replacement, PlayCardAction):
            return None

        replacement_card = self._card_for_action(replacement, game)
        if self._survival_block_value_for_game(
            replacement_card,
            game,
        ) <= self._survival_block_value_for_game(current_card, game):
            return None
        return replacement

    def _get_act1_boss_pressure_action_replacement(self, action: Action, game: Game) -> Optional[Action]:
        from spirecomm.communication.action import PlayCardAction
        from spirecomm.spire.screen import ScreenType

        if not isinstance(action, PlayCardAction):
            return None
        if getattr(game, "screen_type", None) not in (None, ScreenType.NONE):
            return None
        if not getattr(game, "in_combat", False):
            return None

        current_card = self._card_for_action(action, game)
        if self._card_matches_normalized_names(current_card, self.GUARDIAN_PRESSURE_WEAK_ATTACKS):
            return None

        replacement = self._get_act1_boss_pressure_weak_replacement(game)
        if isinstance(replacement, PlayCardAction):
            return replacement

        replacement = self._get_act1_boss_pressure_block_replacement(game)
        if not isinstance(replacement, PlayCardAction):
            return None

        replacement_card = self._card_for_action(replacement, game)
        if self._survival_block_value_for_game(
            replacement_card,
            game,
        ) <= self._survival_block_value_for_game(current_card, game):
            return None
        return replacement

    def _get_non_potion_fallback(self, game: Game) -> Optional[Action]:
        from spirecomm.communication.action import EndTurnAction, PotionAction

        replacement = self._get_act1_boss_pressure_weak_replacement(game)
        if replacement is not None:
            return replacement

        replacement = self._get_slime_split_aoe_survival_replacement(game)
        if replacement is not None:
            return replacement

        replacement = self._get_slime_split_weak_pressure_replacement(game)
        if replacement is not None:
            return replacement

        replacement = self._get_survival_block_replacement(game)
        if replacement is not None:
            return replacement

        replacement = self._get_act1_boss_pressure_block_replacement(game)
        if replacement is not None:
            return replacement

        replacement = self._get_guardian_pressure_block_replacement(game)
        if replacement is not None:
            return replacement

        try:
            fallback_action = self.fallback_agent.get_next_action_in_game(game)
            if (
                fallback_action is not None
                and not isinstance(fallback_action, PotionAction)
                and self._is_valid_combat_action(fallback_action, game)
            ):
                return fallback_action
        except Exception as exc:
            logger.debug("[POTION_SAVE_GUARD] Fallback action failed: %s", exc)

        replacement = self._first_playable_card_action(game)
        if replacement is not None:
            return replacement
        return EndTurnAction()

    def _get_energy_guard_takeover_potion_replacement(self, game: Game) -> Optional[Action]:
        replacement = self._get_slime_split_aoe_survival_replacement(game)
        if replacement is not None:
            return replacement

        replacement = self._get_slime_split_weak_pressure_replacement(game)
        if replacement is not None:
            return replacement

        replacement = self._get_survival_block_replacement(game)
        if replacement is not None:
            return replacement

        replacement = self._get_act1_boss_pressure_weak_replacement(game)
        if replacement is not None:
            return replacement

        replacement = self._get_act1_boss_pressure_block_replacement(game)
        if replacement is not None:
            return replacement

        replacement = self._get_guardian_pressure_block_replacement(game)
        if replacement is not None:
            return replacement

        if self._is_hexaghost_opening_setup_window(game):
            replacement = self._get_hexaghost_setup_replacement(game)
            if replacement is not None:
                return replacement

        return self._first_playable_card_action(
            game,
            avoid_self_lethal=True,
            avoid_pressure_hp_loss=True,
            avoid_low_hp_hp_loss_filler=True,
        )

    def _get_slime_split_aoe_survival_replacement(self, game: Game) -> Optional[Action]:
        from spirecomm.communication.action import PlayCardAction
        from spirecomm.spire.screen import ScreenType

        if getattr(game, "screen_type", None) not in (None, ScreenType.NONE):
            return None
        if not getattr(game, "in_combat", False):
            return None
        if not self._is_slime_boss_split_phase(game):
            return None

        current_hp = self._safe_int(getattr(game, "current_hp", 0), default=0)
        if current_hp <= 0:
            return None

        current_block = self._player_block(game)
        status_blockable_damage, status_hp_loss = self._end_turn_status_damage(game)
        incoming = self._incoming_damage(game)
        current_damage = self._end_turn_damage_after_block(
            incoming + status_blockable_damage,
            status_hp_loss,
            self._end_turn_block_for_game(game, current_block),
            game,
        )
        if current_damage < current_hp:
            return None

        energy = self._player_energy(game)
        aoe_names = {self._normalize_identifier(name) for name in COMMON_AOE_ATTACK_NAMES}
        best_candidate = None
        for card_index, card in self._playable_cards(game, energy):
            if card_requires_target(card):
                continue
            if not is_attack_card(card):
                continue
            if not self._card_matches_normalized_names(card, aoe_names):
                continue
            if self._would_play_self_lethal_card(card, game):
                continue
            effective_cost = effective_card_cost(card, energy)
            if effective_cost > energy:
                continue

            source_attack_damage = self._survival_attack_damage_before_player_weak(card, game)
            if source_attack_damage <= 0:
                continue

            source_attack_hits = self._survival_attack_hit_count(card)
            removed_incoming = 0
            killed_attackers = 0
            remaining_incoming = 0
            for monster in getattr(game, "monsters", []) or []:
                monster_incoming = self._monster_incoming_damage(monster)
                if monster_incoming <= 0:
                    continue
                if not self._is_targetable_monster(monster):
                    continue

                effective_hp = (
                    self._safe_int(getattr(monster, "current_hp", 0), default=0)
                    + self._safe_int(getattr(monster, "block", 0), default=0)
                )
                attack_damage = self._apply_survival_attack_target_modifiers(
                    source_attack_damage,
                    game,
                    monster,
                    hit_count=source_attack_hits,
                )
                if attack_damage >= effective_hp:
                    removed_incoming += monster_incoming
                    killed_attackers += 1
                else:
                    remaining_incoming += monster_incoming

            if removed_incoming <= 0:
                continue

            candidate_block = current_block + self._survival_block_value_for_game(card, game)
            damage_after_candidate = self._end_turn_aggregate_damage_after_block(
                remaining_incoming + status_blockable_damage,
                status_hp_loss,
                self._end_turn_block_for_game(game, candidate_block),
                game,
            )
            if damage_after_candidate >= current_hp:
                continue

            survival_margin = current_hp - damage_after_candidate
            score = (
                survival_margin,
                removed_incoming,
                killed_attackers,
                source_attack_damage,
                -effective_cost,
                -card_index,
            )
            if best_candidate is None or score > best_candidate[0]:
                best_candidate = (
                    score,
                    card_index,
                    card,
                    removed_incoming,
                    damage_after_candidate,
                )

        if best_candidate is None:
            return None

        _, card_index, card, removed_incoming, damage_after_candidate = best_candidate
        logger.info(
            "[SLIME_SPLIT_SURVIVAL_GUARD] Selecting %s to remove incoming=%s hp=%s current_damage=%s damage_after=%s",
            self._card_label(card),
            removed_incoming,
            current_hp,
            current_damage,
            damage_after_candidate,
        )
        return PlayCardAction(card_index=card_index)

    def _get_slime_split_weak_pressure_replacement(self, game: Game) -> Optional[Action]:
        from spirecomm.communication.action import PlayCardAction
        from spirecomm.spire.screen import ScreenType

        if getattr(game, "screen_type", None) not in (None, ScreenType.NONE):
            return None
        if not getattr(game, "in_combat", False):
            return None
        if not self._is_slime_boss_split_phase(game):
            return None

        current_hp = self._safe_int(getattr(game, "current_hp", 0), default=0)
        if current_hp <= 0:
            return None
        max_hp = max(
            self._safe_int(getattr(game, "max_hp", current_hp), default=current_hp),
            1,
        )

        incoming_events = self._incoming_damage_events(game)
        incoming = sum(incoming_events)
        if incoming <= 0:
            return None

        current_block = self._player_block(game)
        status_blockable_events = self._end_turn_status_blockable_damage_events(game)
        status_hp_loss_events = self._end_turn_status_hp_loss_events(game)
        current_damage = self._end_turn_damage_events_after_block(
            status_blockable_events + incoming_events,
            status_hp_loss_events,
            self._end_turn_block_for_game(game, current_block),
            game,
        )
        if current_damage <= 0:
            return None

        low_hp_pressure = current_hp <= max(20, max_hp * 0.25)
        if (
            current_damage < current_hp
            and not low_hp_pressure
            and current_hp - current_damage > 4
        ):
            return None

        weak_incoming_events = self._incoming_damage_events_after_aoe_weak(game)
        if weak_incoming_events is None:
            return None
        weak_incoming = sum(weak_incoming_events)
        if weak_incoming >= incoming:
            return None

        energy = self._player_energy(game)
        best_candidate = None
        for card_index, card in self._playable_cards(game, energy):
            if card_requires_target(card):
                continue
            if not self._card_matches_normalized_names(
                card,
                self.GUARDIAN_PRESSURE_WEAK_ATTACKS,
            ):
                continue
            if self._would_play_self_lethal_card(card, game):
                continue

            effective_cost = effective_card_cost(card, energy)
            remaining_energy = energy - effective_cost
            if remaining_energy < 0:
                continue

            best_followup_block = 0
            for other_index, other_card in self._playable_cards(game, remaining_energy):
                if other_index == card_index:
                    continue
                best_followup_block = max(
                    best_followup_block,
                    self._survival_block_value_for_game(other_card, game),
                )

            projected_block = (
                current_block
                + self._survival_block_value_for_game(card, game)
                + best_followup_block
            )
            projected_damage = self._end_turn_damage_events_after_block(
                status_blockable_events + weak_incoming_events,
                status_hp_loss_events,
                self._end_turn_block_for_game(game, projected_block),
                game,
            )
            if projected_damage >= current_damage:
                continue
            if projected_damage >= current_hp:
                continue

            damage_reduced = current_damage - projected_damage
            lethal_save = current_damage >= current_hp
            narrow_margin = current_hp - current_damage <= 4 and damage_reduced >= 2
            low_hp_use = low_hp_pressure and damage_reduced >= 3
            if not (lethal_save or narrow_margin or low_hp_use):
                continue

            normalized = {
                self._normalize_identifier(getattr(card, "name", None)),
                self._normalize_identifier(getattr(card, "card_id", None)),
            }
            priority = 3 if any(value.startswith("shockwave") for value in normalized) else 1
            survival_margin = current_hp - projected_damage
            score = (
                survival_margin,
                damage_reduced,
                priority,
                best_followup_block,
                -effective_cost,
                -card_index,
            )
            if best_candidate is None or score > best_candidate[0]:
                best_candidate = (
                    score,
                    card_index,
                    card,
                    damage_reduced,
                    projected_damage,
                )

        if best_candidate is None:
            return None

        _, card_index, card, damage_reduced, projected_damage = best_candidate
        logger.info(
            "[SLIME_SPLIT_PRESSURE_GUARD] Selecting %s hp=%s incoming=%s current_damage=%s damage_reduced=%s projected_damage=%s",
            self._card_label(card),
            current_hp,
            incoming,
            current_damage,
            damage_reduced,
            projected_damage,
        )
        return PlayCardAction(card_index=card_index)

    def _get_act1_boss_pressure_weak_replacement(self, game: Game) -> Optional[Action]:
        from spirecomm.communication.action import PlayCardAction

        if not self._is_act1_boss_pressure_combat(game):
            return None

        current_hp = self._safe_int(getattr(game, "current_hp", 0), default=0)
        if current_hp <= 0:
            return None

        incoming = self._incoming_damage(game)
        current_block = self._player_block(game)
        if incoming <= current_block:
            return None

        status_blockable_damage, status_hp_loss = self._end_turn_status_damage(game)
        damage_after_block = self._end_turn_damage_after_block(
            incoming + status_blockable_damage,
            status_hp_loss,
            self._end_turn_block_for_game(game, current_block),
            game,
        )
        if damage_after_block <= 0:
            return None

        immediate_lethal_pressure = damage_after_block >= current_hp
        if not immediate_lethal_pressure:
            if incoming < max(24, current_hp * 0.35) and damage_after_block < max(
                18,
                current_hp * 0.30,
            ):
                return None

        target_index = self._best_monster_index(game)
        best_candidate = None
        energy = self._player_energy(game)
        for card_index, card in self._playable_cards(game, energy):
            if not self._card_matches_normalized_names(
                card,
                self.GUARDIAN_PRESSURE_WEAK_ATTACKS,
            ):
                continue
            if self._would_play_self_lethal_card(card, game):
                continue
            if card_requires_target(card) and target_index is None:
                continue

            effective_cost = effective_card_cost(card, energy)
            survival_margin = None
            if immediate_lethal_pressure:
                survival_margin = self._act1_boss_weak_survival_margin_after_card(
                    card_index,
                    card,
                    game,
                    current_hp,
                    current_block,
                    status_blockable_damage,
                    status_hp_loss,
                    energy,
                )
                if survival_margin is None:
                    continue

            normalized = {
                self._normalize_identifier(getattr(card, "name", None)),
                self._normalize_identifier(getattr(card, "card_id", None)),
            }
            if any(value.startswith("shockwave") for value in normalized):
                priority = 3
            elif any(value.startswith("uppercut") for value in normalized):
                priority = 2
            else:
                priority = 1
            score = (
                survival_margin if survival_margin is not None else 0,
                priority,
                -effective_cost,
                -card_index,
            )
            action = (
                PlayCardAction(card_index=card_index, target_index=target_index)
                if card_requires_target(card)
                else PlayCardAction(card_index=card_index)
            )
            if best_candidate is None or score > best_candidate[0]:
                best_candidate = (score, action, card)

        if best_candidate is None:
            return None

        _, action, card = best_candidate
        logger.info(
            "[ACT1_BOSS_WEAK_GUARD] Selecting %s before large boss hit hp=%s incoming=%s damage_after_block=%s current_block=%s",
            self._card_label(card),
            current_hp,
            incoming,
            damage_after_block,
            current_block,
        )
        return action

    def _act1_boss_weak_survival_margin_after_card(
        self,
        card_index: int,
        card,
        game: Game,
        current_hp: int,
        current_block: int,
        status_blockable_damage: int,
        status_hp_loss: int,
        energy: int,
    ) -> Optional[int]:
        weak_incoming = self._incoming_damage_after_single_target_weak(game)
        if weak_incoming is None:
            return None

        effective_cost = effective_card_cost(card, energy)
        remaining_energy = energy - effective_cost
        if remaining_energy < 0:
            return None

        best_followup_block = 0
        for other_index, other_card in self._playable_cards(game, remaining_energy):
            if other_index == card_index:
                continue
            best_followup_block = max(
                best_followup_block,
                self._survival_block_value_for_game(other_card, game),
            )

        projected_block = (
            current_block
            + self._survival_block_value_for_game(card, game)
            + best_followup_block
        )
        projected_damage = self._end_turn_aggregate_damage_after_block(
            weak_incoming + status_blockable_damage,
            status_hp_loss,
            self._end_turn_block_for_game(game, projected_block),
            game,
        )
        if projected_damage >= current_hp:
            return None
        return current_hp - projected_damage

    def _get_survival_block_replacement(self, game: Game) -> Optional[Action]:
        from spirecomm.communication.action import PlayCardAction

        current_hp = self._safe_int(getattr(game, "current_hp", 0), default=0)
        if current_hp <= 0:
            return None

        incoming = self._incoming_damage(game)
        status_blockable_damage, status_hp_loss = self._end_turn_status_damage(game)
        current_block = self._player_block(game)
        damage_after_block = self._end_turn_damage_after_block(
            incoming + status_blockable_damage,
            status_hp_loss,
            self._end_turn_block_for_game(game, current_block),
            game,
        )
        if damage_after_block < current_hp:
            return None

        energy = self._player_energy(game)
        best_candidate = None
        target_index = self._best_monster_index(game)
        for card_index, card in self._playable_cards(game, energy):
            block_value = self._survival_block_value_for_game(card, game)
            if block_value <= 0:
                continue
            if card_requires_target(card) and target_index is None:
                continue

            effective_cost = effective_card_cost(card, energy)
            score = (block_value, -effective_cost, -card_index)
            if best_candidate is None or score > best_candidate[0]:
                action = (
                    PlayCardAction(card_index=card_index, target_index=target_index)
                    if card_requires_target(card)
                    else PlayCardAction(card_index=card_index)
                )
                best_candidate = (score, action, card, block_value)

        if best_candidate is None:
            return None

        _, action, card, block_value = best_candidate
        logger.info(
            "[SURVIVAL_GUARD] Selecting %s for block=%s hp=%s incoming=%s status_blockable_damage=%s status_hp_loss=%s current_block=%s",
            self._card_label(card),
            block_value,
            current_hp,
            incoming,
            status_blockable_damage,
            status_hp_loss,
            current_block,
        )
        return action

    def _get_guardian_pressure_block_replacement(self, game: Game) -> Optional[Action]:
        from spirecomm.communication.action import PlayCardAction

        if not self._has_guardian(game):
            return None

        current_hp = self._safe_int(getattr(game, "current_hp", 0), default=0)
        if current_hp <= 0:
            return None

        incoming = self._incoming_damage(game)
        current_block = self._player_block(game)
        damage_after_block = max(0, incoming - current_block)
        if damage_after_block <= 0:
            return None
        if damage_after_block >= current_hp:
            return None
        max_hp = max(
            self._safe_int(getattr(game, "max_hp", current_hp), default=current_hp),
            1,
        )
        low_hp_pressure = (
            current_hp <= max(16, max_hp * 0.25)
            and damage_after_block >= max(5, current_hp * 0.45)
        )
        if incoming < self.GUARDIAN_PRESSURE_INCOMING and not low_hp_pressure:
            return None

        candidate = self._best_block_action_candidate(game)
        if candidate is None:
            return None

        action, card, block_value = candidate
        logger.info(
            "[GUARDIAN_PRESSURE_GUARD] Selecting %s for block=%s hp=%s incoming=%s current_block=%s",
            self._card_label(card),
            block_value,
            current_hp,
            incoming,
            current_block,
        )
        return action

    def _get_act1_boss_pressure_block_replacement(self, game: Game) -> Optional[Action]:
        if not self._is_act1_boss_pressure_combat(game):
            return None

        current_hp = self._safe_int(getattr(game, "current_hp", 0), default=0)
        if current_hp <= 0:
            return None

        incoming = self._incoming_damage(game)
        status_blockable_damage, status_hp_loss = self._end_turn_status_damage(game)
        current_block = self._player_block(game)
        if incoming <= current_block:
            return None
        damage_after_block = self._end_turn_damage_after_block(
            incoming + status_blockable_damage,
            status_hp_loss,
            self._end_turn_block_for_game(game, current_block),
            game,
        )
        if damage_after_block <= 0:
            return None
        if damage_after_block >= current_hp:
            return None

        max_hp = max(
            self._safe_int(getattr(game, "max_hp", current_hp), default=current_hp),
            1,
        )
        if current_hp > max(
            self.ACT1_BOSS_PRESSURE_MIN_HP,
            max_hp * self.ACT1_BOSS_PRESSURE_HP_RATIO,
        ):
            return None
        if damage_after_block < max(
            self.ACT1_BOSS_PRESSURE_MIN_DAMAGE,
            current_hp * self.ACT1_BOSS_PRESSURE_DAMAGE_RATIO,
        ):
            return None

        candidate = self._best_block_action_candidate(game)
        if candidate is None:
            return None

        action, card, block_value = candidate
        logger.info(
            "[ACT1_BOSS_PRESSURE_GUARD] Selecting %s for block=%s hp=%s incoming=%s status_blockable_damage=%s status_hp_loss=%s current_block=%s",
            self._card_label(card),
            block_value,
            current_hp,
            incoming,
            status_blockable_damage,
            status_hp_loss,
            current_block,
        )
        return action

    def _best_block_action_candidate(self, game: Game):
        from spirecomm.communication.action import PlayCardAction

        energy = self._player_energy(game)
        best_candidate = None
        target_index = self._best_monster_index(game)
        for card_index, card in self._playable_cards(game, energy):
            block_value = self._survival_block_value_for_game(card, game)
            if block_value <= 0:
                continue
            if card_requires_target(card) and target_index is None:
                continue

            effective_cost = effective_card_cost(card, energy)
            score = (block_value, -effective_cost, -card_index)
            if best_candidate is None or score > best_candidate[0]:
                action = (
                    PlayCardAction(card_index=card_index, target_index=target_index)
                    if card_requires_target(card)
                    else PlayCardAction(card_index=card_index)
                )
                best_candidate = (score, action, card, block_value)

        if best_candidate is None:
            return None

        _, action, card, block_value = best_candidate
        return action, card, block_value

    def _first_playable_card_action(
        self,
        game: Game,
        allow_power: bool = True,
        excluded_card_names=None,
        avoid_self_lethal: bool = False,
        avoid_pressure_hp_loss: bool = False,
        avoid_low_hp_hp_loss_filler: bool = False,
    ) -> Optional[Action]:
        from spirecomm.communication.action import PlayCardAction

        energy = self._player_energy(game)
        playable = self._playable_cards(game, energy)
        if not playable:
            return None

        excluded = {
            self._normalize_identifier(name)
            for name in (excluded_card_names or [])
        }
        target_index = self._best_monster_index(game)
        candidates = []
        for card_index, card in playable:
            if not allow_power and self._is_power_card(card):
                continue
            if excluded and self._card_matches_normalized_names(card, excluded):
                continue
            if avoid_self_lethal and self._would_play_self_lethal_card(card, game):
                logger.info(
                    "[ENERGY_GUARD] Skipping self-lethal fallback card=%s hp=%s hp_loss=%s",
                    self._card_label(card),
                    getattr(game, "current_hp", None),
                    self._card_player_hp_loss(card, game),
                )
                continue
            if avoid_pressure_hp_loss and self._would_hp_loss_expose_lethal_end_turn_damage(card, game):
                logger.info(
                    "[ENERGY_GUARD] Skipping pressure-unsafe HP-loss fallback card=%s hp=%s hp_loss=%s",
                    self._card_label(card),
                    getattr(game, "current_hp", None),
                    self._card_player_hp_loss(card, game),
                )
                continue
            if (
                avoid_low_hp_hp_loss_filler
                and self._would_low_hp_hp_loss_be_filler_without_pressure(card, game)
            ):
                logger.info(
                    "[ENERGY_GUARD] Skipping low-HP HP-loss filler card=%s hp=%s hp_loss=%s",
                    self._card_label(card),
                    getattr(game, "current_hp", None),
                    self._card_player_hp_loss(card, game),
                )
                continue
            if card_requires_target(card):
                if target_index is None:
                    continue
                action = PlayCardAction(card_index=card_index, target_index=target_index)
            else:
                action = PlayCardAction(card_index=card_index)
            is_low_value_status = self._card_matches_normalized_names(
                card,
                self.LOW_VALUE_STATUS_CARDS,
            )
            candidates.append((is_low_value_status, action))

        for is_low_value_status, action in candidates:
            if not is_low_value_status:
                return action
        return candidates[0][1] if candidates else None

    def _is_self_lethal_card_action(self, action: Action, game: Game) -> bool:
        from spirecomm.communication.action import PlayCardAction

        if not isinstance(action, PlayCardAction):
            return False
        return self._would_play_self_lethal_card(
            self._card_for_action(action, game),
            game,
        )

    def _is_pressure_unsafe_hp_loss_card_action(self, action: Action, game: Game) -> bool:
        from spirecomm.communication.action import PlayCardAction

        if not isinstance(action, PlayCardAction):
            return False
        return self._would_hp_loss_expose_lethal_end_turn_damage(
            self._card_for_action(action, game),
            game,
        )

    def _get_self_vulnerable_pressure_action_replacement(
        self,
        action: Action,
        game: Game,
    ) -> Optional[Action]:
        from spirecomm.communication.action import EndTurnAction, PlayCardAction
        from spirecomm.spire.screen import ScreenType

        if not isinstance(action, PlayCardAction):
            return None
        if getattr(game, "screen_type", None) not in (None, ScreenType.NONE):
            return None
        if not getattr(game, "in_combat", False):
            return None

        current_card = self._card_for_action(action, game)
        if not self._would_self_vulnerable_expose_pressure_damage(current_card, game):
            return None

        candidate = self._best_block_action_candidate(game)
        if candidate is not None:
            replacement, card, block_value = candidate
            if block_value > self._survival_block_value_for_game(current_card, game):
                logger.info(
                    "[SELF_VULN_GUARD] Selecting %s to avoid self-Vulnerable pressure hp=%s incoming=%s block=%s",
                    self._card_label(card),
                    getattr(game, "current_hp", None),
                    self._incoming_damage(game),
                    self._player_block(game),
                )
                return replacement

        replacement = self._first_playable_card_action(
            game,
            excluded_card_names=self.SELF_VULNERABLE_CARDS,
            avoid_self_lethal=True,
            avoid_pressure_hp_loss=True,
            avoid_low_hp_hp_loss_filler=True,
        )
        if replacement is not None:
            return replacement
        return EndTurnAction()

    @classmethod
    def _would_self_vulnerable_expose_pressure_damage(cls, card, game: Game) -> bool:
        if not cls._card_matches_normalized_names(card, cls.SELF_VULNERABLE_CARDS):
            return False
        if player_debuff_stacks(game, "Vulnerable") > 0 or player_has_power(game, "Vulnerable"):
            return False

        incoming_events = cls._incoming_damage_events(game)
        if not incoming_events:
            return False

        current_hp = cls._safe_int(getattr(game, "current_hp", 0), default=0)
        if current_hp <= 0:
            return False

        current_block = cls._player_block(game)
        status_blockable_damage, status_hp_loss = cls._end_turn_status_damage(game)
        end_turn_block = cls._end_turn_block_for_game(game, current_block)
        current_damage = cls._end_turn_damage_after_block(
            sum(incoming_events) + status_blockable_damage,
            status_hp_loss,
            end_turn_block,
            game,
        )
        vulnerable_damage = cls._end_turn_damage_after_block(
            sum(event * 3 // 2 for event in incoming_events) + status_blockable_damage,
            status_hp_loss,
            end_turn_block,
            game,
        )
        extra_damage = vulnerable_damage - current_damage
        if extra_damage <= 0:
            return False
        if vulnerable_damage >= current_hp:
            return True
        return (
            current_damage > 0
            and (
                vulnerable_damage >= max(18, current_hp * 0.45)
                or extra_damage >= max(6, current_hp * 0.15)
            )
        )

    @classmethod
    def _would_play_self_lethal_card(cls, card, game: Game) -> bool:
        hp_loss = cls._card_player_hp_loss(card, game)
        if hp_loss <= 0:
            return False
        current_hp = cls._safe_int(getattr(game, "current_hp", 0), default=0)
        return current_hp > 0 and current_hp <= hp_loss

    @classmethod
    def _would_hp_loss_expose_lethal_end_turn_damage(cls, card, game: Game) -> bool:
        hp_loss = cls._card_player_hp_loss(card, game)
        if hp_loss <= 0:
            return False

        current_hp = cls._safe_int(getattr(game, "current_hp", 0), default=0)
        if current_hp <= hp_loss:
            return True

        current_block = cls._player_block(game)
        status_blockable_damage, status_hp_loss = cls._end_turn_status_damage(game)
        current_damage = cls._end_turn_damage_after_block(
            cls._incoming_damage(game) + status_blockable_damage,
            status_hp_loss,
            cls._end_turn_block_for_game(game, current_block),
            game,
        )
        return current_damage > 0 and current_damage >= current_hp - hp_loss

    @classmethod
    def _would_low_hp_hp_loss_be_filler_without_pressure(cls, card, game: Game) -> bool:
        hp_loss = cls._card_player_hp_loss(card, game)
        if hp_loss <= 0:
            return False
        if is_attack_card(card):
            return False

        current_hp = cls._safe_int(getattr(game, "current_hp", 0), default=0)
        max_hp = max(
            cls._safe_int(getattr(game, "max_hp", current_hp), default=current_hp),
            1,
        )
        if current_hp <= 0 or current_hp > max(16, max_hp * 0.25):
            return False

        current_block = cls._player_block(game)
        status_blockable_damage, status_hp_loss = cls._end_turn_status_damage(game)
        current_damage = cls._end_turn_damage_after_block(
            cls._incoming_damage(game) + status_blockable_damage,
            status_hp_loss,
            cls._end_turn_block_for_game(game, current_block),
            game,
        )
        return current_damage <= 0

    @classmethod
    def _card_player_hp_loss(cls, card, game: Game) -> int:
        if card is None:
            return 0
        total = 0
        for normalized_name, hp_loss in cls.CARD_HP_LOSS_VALUES.items():
            if cls._card_matches_normalized_names(card, {normalized_name}):
                total += cls._prevented_hp_loss(hp_loss, game)
                break
        for hp_loss in cls._pain_card_play_hp_loss_events(card, game):
            total += cls._prevented_hp_loss(hp_loss, game)
        return total

    @classmethod
    def _pain_card_play_hp_loss_events(cls, card, game: Game) -> list[int]:
        hand = list(getattr(game, "hand", []) or [])
        played_index = cls._matching_hand_card_index(card, hand)
        events = []
        for index, hand_card in enumerate(hand):
            if index == played_index or hand_card is card:
                continue
            if cls._card_matches_normalized_names(hand_card, {"pain"}):
                events.append(1)
        return events

    def _get_awakened_one_safe_replacement(self, game: Game) -> Optional[Action]:
        from spirecomm.communication.action import EndTurnAction

        replacement = self._first_playable_card_action(game, allow_power=False)
        if replacement is not None:
            return replacement
        return EndTurnAction()

    def _should_override_awakened_one_power(self, action: Action, game: Game) -> bool:
        from spirecomm.communication.action import PlayCardAction
        from spirecomm.spire.screen import ScreenType

        if not isinstance(action, PlayCardAction):
            return False
        if getattr(game, "screen_type", None) not in (None, ScreenType.NONE):
            return False
        if not self._has_awakened_one(game):
            return False

        card = self._card_for_action(action, game)
        return self._is_power_card(card)

    def _should_override_hexaghost_setup_action(self, action: Action, game: Game) -> bool:
        from spirecomm.communication.action import PlayCardAction
        from spirecomm.spire.screen import ScreenType

        if not isinstance(action, PlayCardAction):
            return False
        if getattr(game, "screen_type", None) not in (None, ScreenType.NONE):
            return False
        if not self._is_hexaghost_opening_setup_window(game):
            return False

        card = self._card_for_action(action, game)
        if not self._is_low_value_hexaghost_setup_card(card):
            return False
        return self._get_hexaghost_setup_replacement(game) is not None

    def _get_hexaghost_setup_replacement(self, game: Game) -> Optional[Action]:
        from spirecomm.communication.action import PlayCardAction

        energy = self._player_energy(game)
        playable = self._playable_cards(game, energy)
        if not playable:
            return None

        target_index = self._best_monster_index(game)
        for setup_name in self.HEXAGHOST_SETUP_PRIORITY:
            for card_index, card in playable:
                if not self._card_matches_normalized_names(card, {setup_name}):
                    continue
                if card_requires_target(card):
                    if target_index is None:
                        continue
                    return PlayCardAction(card_index=card_index, target_index=target_index)
                return PlayCardAction(card_index=card_index)
        for card_index, card in playable:
            if not is_attack_card(card):
                continue
            if self._would_play_self_lethal_card(card, game):
                continue
            if card_requires_target(card):
                if target_index is None:
                    continue
                return PlayCardAction(card_index=card_index, target_index=target_index)
            return PlayCardAction(card_index=card_index)
        return None

    def _is_hexaghost_opening_setup_window(self, game: Game) -> bool:
        if self._safe_int(getattr(game, "turn", 0), default=0) != 1:
            return False
        if not self._has_hexaghost(game):
            return False
        if not self._is_boss_combat(game):
            return False
        return self._incoming_damage(game) <= 0

    def _is_low_value_hexaghost_setup_card(self, card) -> bool:
        return self._card_matches_normalized_names(
            card,
            self.HEXAGHOST_LOW_VALUE_SETUP_CARDS,
        )

    def _should_override_slime_boss_vulnerable_setup_action(self, action: Action, game: Game) -> bool:
        from spirecomm.communication.action import PlayCardAction
        from spirecomm.spire.screen import ScreenType

        if not isinstance(action, PlayCardAction):
            return False
        if getattr(game, "screen_type", None) not in (None, ScreenType.NONE):
            return False
        if not self._is_slime_boss_vulnerable_setup_window(game):
            return False

        card = self._card_for_action(action, game)
        if not self._card_matches_normalized_names(
            card,
            self.SLIME_BOSS_LOW_VALUE_BEFORE_VULNERABLE,
        ):
            return False
        return self._get_slime_boss_vulnerable_setup_replacement(game) is not None

    def _get_slime_boss_vulnerable_setup_replacement(self, game: Game) -> Optional[Action]:
        from spirecomm.communication.action import PlayCardAction

        energy = self._player_energy(game)
        playable = self._playable_cards(game, energy)
        if not playable:
            return None

        target_index = self._best_monster_index(game)
        for setup_name in self.SLIME_BOSS_VULNERABLE_SETUP_PRIORITY:
            for card_index, card in playable:
                if not self._card_matches_normalized_names(card, {setup_name}):
                    continue
                if card_requires_target(card):
                    if target_index is None:
                        continue
                    return PlayCardAction(card_index=card_index, target_index=target_index)
                return PlayCardAction(card_index=card_index)
        return None

    def _is_slime_boss_vulnerable_setup_window(self, game: Game) -> bool:
        if self._safe_int(getattr(game, "turn", 0), default=0) > 3:
            return False
        if not self._has_slime_boss(game):
            return False
        if not self._is_boss_combat(game):
            return False

        target_index = self._best_monster_index(game)
        monsters = getattr(game, "monsters", []) or []
        if target_index is None or target_index >= len(monsters):
            return False
        return self._monster_vulnerable_stacks(monsters[target_index]) <= 0

    def _should_override_urgent_ethereal_attack(self, action: Action, game: Game) -> bool:
        from spirecomm.communication.action import PlayCardAction
        from spirecomm.spire.screen import ScreenType

        if not isinstance(action, PlayCardAction):
            return False
        if getattr(game, "screen_type", None) not in (None, ScreenType.NONE):
            return False
        if not getattr(game, "in_combat", False):
            return False
        if not self._is_boss_combat(game):
            return False
        if self._is_urgent_ethereal_attack_action(action, game):
            return False

        card = self._card_for_action(action, game)
        if not self._card_matches_normalized_names(
            card,
            self.LOW_VALUE_BEFORE_URGENT_ETHEREAL,
        ):
            return False
        return self._get_urgent_ethereal_attack_replacement(game, action) is not None

    def _get_urgent_ethereal_attack_replacement(
        self,
        game: Game,
        current_action: Optional[Action] = None,
    ) -> Optional[Action]:
        from spirecomm.communication.action import PlayCardAction

        energy = self._player_energy(game)
        playable = self._playable_cards(game, energy)
        if not playable:
            return None

        target_index = self._best_monster_index(game)
        current_card = self._card_for_action(current_action, game) if current_action else None
        current_cost = effective_card_cost(current_card, energy) if current_card is not None else 0
        for card_index, card in playable:
            if not self._card_matches_normalized_names(card, self.URGENT_ETHEREAL_ATTACKS):
                continue
            ethereal_cost = effective_card_cost(card, energy)
            remaining_energy = energy - ethereal_cost
            if current_card is not None and current_cost > remaining_energy:
                continue
            if card_requires_target(card):
                if target_index is None:
                    continue
                return PlayCardAction(card_index=card_index, target_index=target_index)
            return PlayCardAction(card_index=card_index)
        return None

    def _is_urgent_ethereal_attack_action(self, action: Action, game: Game) -> bool:
        from spirecomm.communication.action import PlayCardAction

        if not isinstance(action, PlayCardAction):
            return False
        return self._card_matches_normalized_names(
            self._card_for_action(action, game),
            self.URGENT_ETHEREAL_ATTACKS,
        )

    def _should_override_unproductive_double_tap(self, action: Action, game: Game) -> bool:
        from spirecomm.communication.action import PlayCardAction
        from spirecomm.spire.screen import ScreenType

        if not isinstance(action, PlayCardAction):
            return False
        if getattr(game, "screen_type", None) not in (None, ScreenType.NONE):
            return False
        if not getattr(game, "in_combat", False):
            return False

        card = self._card_for_action(action, game)
        if not self._card_matches_normalized_names(card, {"doubletap"}):
            return False

        energy = self._player_energy(game)
        remaining_energy = energy - effective_card_cost(card, energy)
        if remaining_energy < 0:
            return False

        action_index = self._safe_int(getattr(action, "card_index", -1), default=-1)
        if self._has_playable_attack_after_double_tap(game, remaining_energy, action_index):
            return False
        return self._get_double_tap_safe_replacement(game) is not None

    def _has_playable_attack_after_double_tap(
        self,
        game: Game,
        remaining_energy: int,
        double_tap_index: int,
    ) -> bool:
        target_index = self._best_monster_index(game)
        for card_index, card in enumerate(getattr(game, "hand", []) or []):
            if card_index == double_tap_index:
                continue
            if hasattr(card, "is_playable") and not getattr(card, "is_playable", False):
                continue
            if card_type_name(card) != "ATTACK":
                continue
            if effective_card_cost(card, remaining_energy) > remaining_energy:
                continue
            if card_requires_target(card) and target_index is None:
                continue
            return True
        return False

    def _get_double_tap_safe_replacement(self, game: Game) -> Optional[Action]:
        from spirecomm.communication.action import EndTurnAction

        try:
            fallback_action = self.fallback_agent.get_next_action_in_game(game)
            if (
                fallback_action is not None
                and not isinstance(fallback_action, EndTurnAction)
                and not self._is_double_tap_action(fallback_action, game)
                and self._is_valid_combat_action(fallback_action, game)
            ):
                return fallback_action
        except Exception as exc:
            logger.debug("[DOUBLE_TAP_GUARD] Fallback action failed: %s", exc)

        replacement = self._first_playable_card_action(
            game,
            excluded_card_names={"doubletap"},
        )
        if replacement is not None:
            return replacement
        return EndTurnAction()

    def _is_double_tap_action(self, action: Action, game: Game) -> bool:
        from spirecomm.communication.action import PlayCardAction

        if not isinstance(action, PlayCardAction):
            return False
        return self._card_matches_normalized_names(
            self._card_for_action(action, game),
            {"doubletap"},
        )

    def _should_override_risky_havoc(self, action: Action, game: Game) -> bool:
        from spirecomm.communication.action import PlayCardAction
        from spirecomm.spire.screen import ScreenType

        if not isinstance(action, PlayCardAction):
            return False
        if getattr(game, "screen_type", None) not in (None, ScreenType.NONE):
            return False
        if not self._is_havoc_action(action, game):
            return False
        havoc_card = self._card_for_action(action, game)
        if self._havoc_visible_top_attack_is_deterministic(game, havoc_card):
            return False

        energy = self._player_energy(game)
        for _, card in self._playable_cards(game, energy):
            if not self._card_matches_normalized_names(card, {"havoc"}):
                return True
        return False

    @classmethod
    def _havoc_visible_top_attack_is_deterministic(
        cls,
        game: Game,
        source_card=None,
    ) -> bool:
        if cls._player_entangled(game):
            return False

        top_card = cls._draw_pile_top_card(game)
        if top_card is None or not is_attack_card(top_card):
            return False
        if not card_play_conditions_allow(
            top_card,
            cls._remaining_hand_cards_after_effect_source(game, source_card),
        ):
            return False

        alive_count = len(cls._alive_monsters(game))
        if alive_count == 1:
            return True

        aoe_names = {cls._normalize_identifier(name) for name in COMMON_AOE_ATTACK_NAMES}
        return cls._card_matches_normalized_names(top_card, aoe_names)

    @staticmethod
    def _draw_pile_top_card(game: Game):
        draw_pile = getattr(game, "draw_pile", None)
        if not isinstance(draw_pile, list) or not draw_pile:
            return None
        return draw_pile[-1]

    @classmethod
    def _remaining_hand_cards_after_effect_source(cls, game: Game, source_card=None):
        source_key = card_play_key(source_card)
        return tuple(
            hand_card
            for hand_card in getattr(game, "hand", []) or []
            if hand_card is not source_card
            and (source_key is None or card_play_key(hand_card) != source_key)
        )

    def _get_havoc_safe_replacement(self, game: Game) -> Optional[Action]:
        from spirecomm.communication.action import EndTurnAction

        try:
            fallback_action = self.fallback_agent.get_next_action_in_game(game)
            if (
                fallback_action is not None
                and not isinstance(fallback_action, EndTurnAction)
                and self._is_valid_combat_action(fallback_action, game)
                and not self._is_havoc_action(fallback_action, game)
            ):
                return fallback_action
        except Exception as exc:
            logger.debug("[HAVOC_GUARD] Fallback action failed: %s", exc)

        return self._first_playable_card_action(game, excluded_card_names={"havoc"})

    def _is_havoc_action(self, action: Action, game: Game) -> bool:
        from spirecomm.communication.action import PlayCardAction

        if not isinstance(action, PlayCardAction):
            return False
        return self._card_matches_normalized_names(self._card_for_action(action, game), {"havoc"})

    def _should_override_low_value_status_card(self, action: Action, game: Game) -> bool:
        from spirecomm.communication.action import PlayCardAction
        from spirecomm.spire.screen import ScreenType

        if not isinstance(action, PlayCardAction):
            return False
        if getattr(game, "screen_type", None) not in (None, ScreenType.NONE):
            return False
        if not getattr(game, "in_combat", False):
            return False
        if not self._is_low_value_status_action(action, game):
            return False
        return self._has_non_status_playable_card(game)

    def _get_status_card_safe_replacement(self, game: Game) -> Optional[Action]:
        from spirecomm.communication.action import EndTurnAction, PlayCardAction

        try:
            fallback_action = self.fallback_agent.get_next_action_in_game(game)
            if (
                isinstance(fallback_action, PlayCardAction)
                and not self._is_low_value_status_action(fallback_action, game)
                and self._is_valid_combat_action(fallback_action, game)
            ):
                return fallback_action
        except Exception as exc:
            logger.debug("[STATUS_CARD_GUARD] Fallback action failed: %s", exc)

        replacement = self._first_playable_card_action(
            game,
            excluded_card_names=self.LOW_VALUE_STATUS_CARDS,
        )
        if replacement is not None:
            return replacement
        return EndTurnAction()

    def _is_low_value_status_action(self, action: Action, game: Game) -> bool:
        from spirecomm.communication.action import PlayCardAction

        if not isinstance(action, PlayCardAction):
            return False
        return self._card_matches_normalized_names(
            self._card_for_action(action, game),
            self.LOW_VALUE_STATUS_CARDS,
        )

    def _has_non_status_playable_card(self, game: Game) -> bool:
        energy = self._player_energy(game)
        for _, card in self._playable_cards(game, energy):
            if not self._card_matches_normalized_names(
                card,
                self.LOW_VALUE_STATUS_CARDS,
            ):
                return True
        return False

    def _describe_combat_action(self, action: Action, game: Game) -> str:
        from spirecomm.communication.action import PlayCardAction, PotionAction

        if action is None:
            return "None"

        parts = [type(action).__name__]
        if isinstance(action, PlayCardAction):
            card = self._card_for_action(action, game)
            parts.append(f"card_index={getattr(action, 'card_index', None)}")
            if card is not None:
                parts.append(f"card={self._card_label(card)}")
                card_id = getattr(card, "card_id", None)
                if card_id:
                    parts.append(f"card_id={card_id}")
                cost = getattr(card, "cost_for_turn", None)
                if cost is None:
                    cost = getattr(card, "cost", None)
                parts.append(f"cost={cost}")
            parts.append(f"target_index={getattr(action, 'target_index', None)}")
        elif isinstance(action, PotionAction):
            potion = self._potion_for_action(action, game)
            if potion is not None:
                parts.append(f"potion={getattr(potion, 'name', getattr(potion, 'potion_id', None))}")
            parts.append(f"potion_index={getattr(action, 'potion_index', None)}")
            parts.append(f"target_index={getattr(action, 'target_index', None)}")

        hand = ", ".join(
            self._card_label(card)
            for card in (getattr(game, "hand", []) or [])
        )
        parts.append(f"floor={getattr(game, 'floor', None)}")
        parts.append(f"turn={getattr(game, 'turn', None)}")
        parts.append(f"energy={self._player_energy(game)}")
        parts.append(f"hand=[{hand}]")
        return " ".join(parts)

    @classmethod
    def _potion_for_action(cls, action: Action, game: Game):
        potion = getattr(action, "potion", None)
        if potion is not None:
            return potion

        potion_index = cls._safe_int(getattr(action, "potion_index", -1), default=-1)
        if potion_index < 0:
            return None

        raw_potions = getattr(game, "potions", None)
        potions = raw_potions if raw_potions is not None else game_real_potions(game)
        potions = potions or []
        if potion_index >= len(potions):
            return None
        return potions[potion_index]

    @staticmethod
    def _card_for_action(action: Action, game: Game):
        card = getattr(action, "card", None)
        if card is not None:
            return card

        card_index = CombatRLAgent._safe_int(
            getattr(action, "card_index", -1),
            default=-1,
        )
        if card_index < 0:
            return None
        hand = getattr(game, "hand", []) or []
        if 0 <= card_index < len(hand):
            return hand[card_index]
        return None

    @staticmethod
    def _card_label(card) -> str:
        if card is None:
            return "UNKNOWN"
        return str(
            getattr(card, "name", None)
            or getattr(card, "card_id", None)
            or "UNKNOWN"
        )

    @staticmethod
    def _normalize_identifier(value) -> str:
        return "".join(ch for ch in str(value).lower() if ch.isalnum())

    @classmethod
    def _card_matches_normalized_names(cls, card, normalized_names) -> bool:
        if card is None:
            return False
        for value in (getattr(card, "name", None), getattr(card, "card_id", None)):
            normalized = cls._normalize_identifier(value)
            if not normalized:
                continue
            if normalized in normalized_names:
                return True
            if any(normalized.startswith(name) for name in normalized_names):
                return True
        return False

    @classmethod
    def _is_boss_combat(cls, game: Game, alive_monsters=None) -> bool:
        room_type = str(getattr(game, "room_type", "") or "")
        if "Boss" in room_type:
            return True

        floor = cls._safe_int(getattr(game, "floor", 0), default=0)
        if floor != 16:
            return False

        monsters = alive_monsters if alive_monsters is not None else cls._alive_monsters(game)
        for monster in monsters:
            for value in (
                getattr(monster, "monster_id", None),
                getattr(monster, "name", None),
            ):
                if cls._normalize_identifier(value) in cls.ACT1_BOSS_IDENTIFIERS:
                    return True
        return False

    @classmethod
    def _is_act1_boss_pressure_combat(cls, game: Game) -> bool:
        if cls._has_guardian(game):
            return False

        act = cls._safe_int(getattr(game, "act", 1), default=1)
        floor = cls._safe_int(getattr(game, "floor", 0), default=0)
        if act != 1 and floor != 16:
            return False
        if not cls._is_boss_combat(game):
            return False

        return (
            cls._has_hexaghost(game)
            or cls._has_slime_boss(game)
            or cls._is_slime_boss_split_pressure_phase(game)
        )

    @classmethod
    def _is_slime_boss_split_phase(cls, game: Game) -> bool:
        if cls._safe_int(getattr(game, "floor", 0), default=0) != 16:
            return False
        if not cls._is_boss_combat(game):
            return False

        has_dead_slime_boss = False
        alive_split_slimes = 0
        for monster in getattr(game, "monsters", []) or []:
            normalized = {
                cls._normalize_identifier(getattr(monster, "monster_id", None)),
                cls._normalize_identifier(getattr(monster, "name", None)),
            }
            is_slime_boss = any("slimeboss" in value for value in normalized)
            if is_slime_boss:
                if not cls._is_targetable_monster(monster):
                    has_dead_slime_boss = True
                continue
            if cls._is_targetable_monster(monster) and any("slime" in value for value in normalized):
                alive_split_slimes += 1

        return has_dead_slime_boss and alive_split_slimes >= 2

    @classmethod
    def _is_slime_boss_split_pressure_phase(cls, game: Game) -> bool:
        if cls._is_slime_boss_split_phase(game):
            return True
        if cls._safe_int(getattr(game, "floor", 0), default=0) != 16:
            return False
        if not cls._is_boss_combat(game):
            return False

        alive_split_slimes = 0
        for monster in cls._alive_monsters(game):
            normalized = {
                cls._normalize_identifier(getattr(monster, "monster_id", None)),
                cls._normalize_identifier(getattr(monster, "name", None)),
            }
            if any("slimeboss" in value for value in normalized):
                return False
            if any("slime" in value for value in normalized):
                alive_split_slimes += 1

        return alive_split_slimes >= 2

    @classmethod
    def _is_gremlin_leader_combat(cls, game: Game) -> bool:
        return any(
            cls._is_gremlin_leader_monster(monster)
            for monster in cls._alive_monsters(game)
        )

    @classmethod
    def _is_gremlin_leader_monster(cls, monster) -> bool:
        for value in (
            getattr(monster, "monster_id", None),
            getattr(monster, "name", None),
        ):
            if cls._normalize_identifier(value) in cls.GREMLIN_LEADER_IDENTIFIERS:
                return True
        return False

    @classmethod
    def _has_guardian(cls, game: Game) -> bool:
        for monster in cls._alive_monsters(game):
            for value in (
                getattr(monster, "monster_id", None),
                getattr(monster, "name", None),
            ):
                if cls._normalize_identifier(value) == "theguardian":
                    return True
        return False

    @classmethod
    def _guardian_sharp_hide_damage(cls, game: Game) -> int:
        sharp_hide_damage = 0
        for monster in cls._alive_monsters(game):
            is_guardian = False
            for value in (
                getattr(monster, "monster_id", None),
                getattr(monster, "name", None),
            ):
                if cls._normalize_identifier(value) == "theguardian":
                    is_guardian = True
                    break
            if not is_guardian:
                continue

            for power in getattr(monster, "powers", []) or []:
                identifiers = (
                    getattr(power, "power_id", None),
                    getattr(power, "power_name", None),
                    getattr(power, "name", None),
                )
                if not any(
                    cls._normalize_identifier(value) in {"sharphide", "thorns"}
                    for value in identifiers
                ):
                    continue
                sharp_hide_damage = max(
                    sharp_hide_damage,
                        cls._safe_int(getattr(power, "amount", 0), default=0),
                )
            if sharp_hide_damage <= 0:
                move_id = cls._safe_int(getattr(monster, "move_id", -1), default=-1)
                intent = cls._normalize_identifier(getattr(monster, "intent", ""))
                if (
                    move_id in cls.GUARDIAN_SHARP_HIDE_MOVE_IDS
                    or intent in cls.GUARDIAN_SHARP_HIDE_INTENTS
                ):
                    ascension = cls._safe_int(getattr(game, "ascension_level", 0), default=0)
                    sharp_hide_damage = max(
                        sharp_hide_damage,
                        (
                            cls.GUARDIAN_SHARP_HIDE_ASCENSION_19_DAMAGE
                            if ascension >= 19
                            else cls.GUARDIAN_SHARP_HIDE_DAMAGE
                        ),
                    )
        return sharp_hide_damage

    @staticmethod
    def _is_power_card(card) -> bool:
        if card is None:
            return False

        return card_type_name(card) == "POWER"

    @staticmethod
    def _safe_int(value, default: int = 0) -> int:
        return coerce_int(value, default)

    @staticmethod
    def _alive_monsters(game: Game):
        return [
            monster
            for monster in (getattr(game, "monsters", []) or [])
            if CombatRLAgent._is_targetable_monster(monster)
        ]

    @classmethod
    def _is_targetable_monster(cls, monster) -> bool:
        return (
            cls._safe_int(getattr(monster, "current_hp", 0), default=0) > 0
            and not getattr(monster, "is_gone", False)
            and not getattr(monster, "half_dead", False)
        )

    @classmethod
    def _is_finished_combat_transition(cls, game: Game) -> bool:
        from spirecomm.spire.screen import ScreenType

        if not getattr(game, "in_combat", False):
            return False
        if getattr(game, "screen_type", None) not in (None, ScreenType.NONE):
            return False
        return not cls._alive_monsters(game)

    @classmethod
    def _should_end_reviving_combat_transition(cls, game: Game) -> bool:
        available_commands = getattr(game, "available_commands", None)
        if available_commands is not None:
            if "end" not in available_commands:
                return False
        elif not getattr(game, "end_available", False):
            return False
        return any(
            getattr(monster, "half_dead", False)
            for monster in (getattr(game, "monsters", []) or [])
        )

    @classmethod
    def _has_half_dead_awakened_one(cls, game: Game) -> bool:
        for monster in (getattr(game, "monsters", []) or []):
            if not getattr(monster, "half_dead", False):
                continue
            for value in (
                getattr(monster, "monster_id", None),
                getattr(monster, "name", None),
            ):
                if cls._normalize_identifier(value) == "awakenedone":
                    return True
        return False

    @staticmethod
    def _incoming_damage(game: Game) -> int:
        total = 0
        for monster in CombatRLAgent._alive_monsters(game):
            if intent_is_unknown(getattr(monster, "intent", None)):
                known_damage = known_unknown_move_immediate_damage(monster)
                if known_damage > 0:
                    total += known_damage
                    continue
                if known_unknown_move_has_no_immediate_damage(monster):
                    continue
                total += 5 * getattr(game, "act", 1)
                continue
            if not monster_intends_attack(monster):
                continue
            damage = getattr(monster, "move_adjusted_damage", None)
            if damage is None:
                damage = getattr(monster, "move_base_damage", 0) or 0
            hits = max(
                1,
                CombatRLAgent._safe_int(getattr(monster, "move_hits", 1), default=1),
            )
            total += max(0, CombatRLAgent._safe_int(damage, default=0)) * hits
        return total

    @classmethod
    def _incoming_damage_events(cls, game: Game) -> list[int]:
        events = []
        for monster in cls._alive_monsters(game):
            if intent_is_unknown(getattr(monster, "intent", None)):
                known_damage = known_unknown_move_immediate_damage(monster)
                if known_damage > 0:
                    events.append(max(0, cls._safe_int(known_damage, default=0)))
                    continue
                if known_unknown_move_has_no_immediate_damage(monster):
                    continue
                events.append(max(0, 5 * cls._safe_int(getattr(game, "act", 1), default=1)))
                continue
            if not monster_intends_attack(monster):
                continue
            damage = getattr(monster, "move_adjusted_damage", None)
            if damage is None:
                damage = getattr(monster, "move_base_damage", 0) or 0
            hits = max(1, cls._safe_int(getattr(monster, "move_hits", 1), default=1))
            events.extend([max(0, cls._safe_int(damage, default=0))] * hits)
        return [event for event in events if event > 0]

    @classmethod
    def _monster_incoming_damage(cls, monster) -> int:
        if intent_is_unknown(getattr(monster, "intent", None)):
            known_damage = known_unknown_move_immediate_damage(monster)
            if known_damage > 0:
                return known_damage
            return 0
        if not monster_intends_attack(monster):
            return 0
        damage = getattr(monster, "move_adjusted_damage", None)
        if damage is None:
            damage = getattr(monster, "move_base_damage", 0) or 0
        hits = max(1, cls._safe_int(getattr(monster, "move_hits", 1), default=1))
        return max(0, cls._safe_int(damage, default=0)) * hits

    @staticmethod
    def _player_block(game: Game) -> int:
        player = getattr(game, "player", None)
        block = getattr(player, "block", None)
        if block is None:
            block = getattr(game, "block", 0)
        return max(0, CombatRLAgent._safe_int(block, default=0))

    @classmethod
    def _end_turn_status_hp_loss(cls, game: Game) -> int:
        _, hp_loss = cls._end_turn_status_damage(game)
        return hp_loss

    @classmethod
    def _end_turn_status_damage(cls, game: Game) -> tuple[int, int]:
        return (
            sum(cls._end_turn_status_blockable_damage_events(game)),
            sum(cls._end_turn_status_hp_loss_events(game)),
        )

    @classmethod
    def _end_turn_status_blockable_damage_events(cls, game: Game) -> list[int]:
        events = []
        for card in getattr(game, "hand", []) or []:
            if cls._card_matches_normalized_names(card, {"burn"}):
                events.append(4 if card_upgrade_count(card) > 0 else 2)
            if cls._card_matches_normalized_names(card, {"decay"}):
                events.append(2)
        return events

    @classmethod
    def _end_turn_status_hp_loss_events(cls, game: Game) -> list[int]:
        events = []
        hand = list(getattr(game, "hand", []) or [])
        hand_size = len(hand)
        for card in hand:
            if cls._card_matches_normalized_names(card, {"regret"}) and hand_size > 0:
                events.append(hand_size)
        return events

    @classmethod
    def _end_turn_damage_after_block(
        cls,
        blockable_damage: int,
        status_hp_loss: int,
        current_block: int,
        game: Optional[Game] = None,
    ) -> int:
        if game is None:
            return cls._end_turn_aggregate_damage_after_block(
                blockable_damage,
                status_hp_loss,
                current_block,
                game,
            )

        blockable_events = (
            cls._end_turn_status_blockable_damage_events(game)
            + cls._incoming_damage_events(game)
        )
        known_blockable_damage = sum(blockable_events)
        extra_blockable_damage = max(0, blockable_damage - known_blockable_damage)
        if extra_blockable_damage > 0:
            blockable_events.append(extra_blockable_damage)

        hp_loss_events = cls._end_turn_status_hp_loss_events(game)
        known_status_hp_loss = sum(hp_loss_events)
        extra_status_hp_loss = max(0, status_hp_loss - known_status_hp_loss)
        if extra_status_hp_loss > 0:
            hp_loss_events.append(extra_status_hp_loss)

        return cls._end_turn_damage_events_after_block(
            blockable_events,
            hp_loss_events,
            current_block,
            game,
        )

    @classmethod
    def _end_turn_aggregate_damage_after_block(
        cls,
        blockable_damage: int,
        status_hp_loss: int,
        current_block: int,
        game: Optional[Game] = None,
    ) -> int:
        blockable_hp_loss = max(0, blockable_damage - current_block)
        unblocked_status_hp_loss = max(0, status_hp_loss)
        return cls._prevented_hp_loss(
            blockable_hp_loss,
            game,
        ) + cls._prevented_hp_loss(
            unblocked_status_hp_loss,
            game,
        )

    @classmethod
    def _end_turn_damage_events_after_block(
        cls,
        blockable_events: list[int],
        hp_loss_events: list[int],
        current_block: int,
        game: Optional[Game],
    ) -> int:
        remaining_block = max(0, current_block)
        buffer_charges = cls._player_buffer_charges(game) if game is not None else 0
        total_hp_loss = 0
        for event_damage in blockable_events:
            damage = max(0, cls._safe_int(event_damage, default=0))
            if remaining_block > 0:
                blocked = min(remaining_block, damage)
                remaining_block -= blocked
                damage -= blocked
            if damage <= 0:
                continue
            damage = cls._prevented_hp_loss(damage, game)
            if damage <= 0:
                continue
            if buffer_charges > 0:
                buffer_charges -= 1
                continue
            total_hp_loss += damage

        for event_damage in hp_loss_events:
            damage = cls._prevented_hp_loss(event_damage, game)
            if damage <= 0:
                continue
            if buffer_charges > 0:
                buffer_charges -= 1
                continue
            total_hp_loss += damage
        return total_hp_loss

    @classmethod
    def _prevented_hp_loss(cls, amount: int, game: Optional[Game]) -> int:
        hp_loss = max(0, cls._safe_int(amount, default=0))
        if hp_loss > 1 and game is not None and cls._player_intangible_charges(game) > 0:
            hp_loss = 1
        if hp_loss > 0 and game is not None and cls._relic_counter(game, "Tungsten Rod") is not None:
            hp_loss = max(0, hp_loss - 1)
        return hp_loss

    @classmethod
    def _player_intangible_charges(cls, game: Game) -> int:
        return max(
            cls._player_power_amount(game, "IntangiblePlayer"),
            cls._player_power_amount(game, "Intangible"),
        )

    @classmethod
    def _player_buffer_charges(cls, game: Game) -> int:
        return max(
            cls._player_power_amount(game, "Buffer"),
            cls._player_power_amount(game, "BufferPower"),
        )

    @classmethod
    def _player_power_amount(cls, game: Game, power_name: str) -> int:
        wanted = cls._normalize_identifier(power_name)
        player = getattr(game, "player", None)
        for power in getattr(player, "powers", []) or []:
            identifiers = (
                getattr(power, "power_id", None),
                getattr(power, "power_name", None),
                getattr(power, "id", None),
                getattr(power, "name", None),
            )
            if any(cls._normalize_identifier(identifier) == wanted for identifier in identifiers):
                return max(0, cls._safe_int(getattr(power, "amount", 1), default=1))
        return 0

    @classmethod
    def _end_turn_block_for_game(cls, game: Game, current_block: int) -> int:
        block = max(0, current_block)
        if block > 0:
            return block
        if cls._relic_counter(game, "Orichalcum") is not None:
            return 6
        return block

    @classmethod
    def _survival_block_value(cls, card) -> int:
        explicit_block = max(
            0,
            cls._safe_int(getattr(card, "block", 0), default=0),
        )
        if explicit_block > 0:
            return explicit_block

        for normalized_name, (card_name, base_block) in cls.SURVIVAL_BLOCK_CARD_VALUES.items():
            if cls._card_matches_normalized_names(card, {normalized_name}):
                return base_block + known_block_upgrade_bonus(card, card_name)
        return 0

    @classmethod
    def _survival_block_value_for_game(cls, card, game: Optional[Game] = None) -> int:
        block_value = cls._survival_block_value(card)
        if game is not None:
            block_value += cls._ornamental_fan_block_for_card(card, game)
            if card_exhausts_itself(card, game_data_loader):
                block_value += cls._feel_no_pain_block_per_exhaust(game)
            block_value += cls._second_wind_block_value_for_game(card, game)
        if game is None or not cls._card_matches_normalized_names(card, {"havoc"}):
            return block_value

        top_card = cls._draw_pile_top_card(game)
        if top_card is None:
            return block_value

        top_attack_blocked = is_attack_card(top_card) and (
            cls._player_entangled(game)
            or not card_play_conditions_allow(
                top_card,
                cls._remaining_hand_cards_after_effect_source(game, card),
            )
        )
        top_card_block = 0 if top_attack_blocked else cls._survival_block_value(top_card)
        top_card_fan_block = (
            0
            if top_attack_blocked
            else cls._ornamental_fan_block_for_card(top_card, game)
        )
        feel_no_pain_block = cls._feel_no_pain_block_per_exhaust(game)
        return block_value + top_card_block + top_card_fan_block + feel_no_pain_block

    @classmethod
    def _second_wind_block_value_for_game(cls, card, game: Optional[Game]) -> int:
        if game is None or not cls._card_matches_normalized_names(card, {"secondwind"}):
            return 0

        exhausted_count = sum(
            1
            for hand_card in cls._remaining_hand_cards_after_effect_source(game, card)
            if not is_attack_card(hand_card)
        )
        if exhausted_count <= 0:
            return 0

        block_per_exhaust = 7 if card_upgrade_count(card) > 0 else 5
        block_per_exhaust += cls._feel_no_pain_block_per_exhaust(game)
        return exhausted_count * block_per_exhaust

    @classmethod
    def _player_entangled(cls, game: Game) -> bool:
        return player_debuff_stacks(game, "Entangled") > 0 or player_has_power(game, "Entangled")

    @classmethod
    def _feel_no_pain_block_per_exhaust(cls, game: Game) -> int:
        block = max(0, player_power_amount(game, "Feel No Pain"))
        if block <= 0 and player_has_power(game, "Feel No Pain"):
            return 3
        return block

    @classmethod
    def _ornamental_fan_block_for_card(cls, card, game: Game) -> int:
        if not is_attack_card(card):
            return 0
        counter = cls._relic_counter(game, "Ornamental Fan")
        if counter is None:
            return 0
        return 4 if (max(0, counter) + 1) % 3 == 0 else 0

    @classmethod
    def _relic_counter(cls, game: Game, relic_name: str) -> Optional[int]:
        wanted = cls._normalize_identifier(relic_name)
        for relic in getattr(game, "relics", []) or []:
            identifiers = [
                getattr(relic, "relic_id", None),
                getattr(relic, "name", None),
                getattr(relic, "id", None),
            ]
            if isinstance(relic, str):
                identifiers.append(relic)
            if any(cls._normalize_identifier(identifier) == wanted for identifier in identifiers):
                return cls._safe_int(getattr(relic, "counter", 0), default=0)
        return None

    @classmethod
    def _survival_attack_damage(cls, card, game: Optional[Game] = None) -> int:
        damage = cls._survival_attack_damage_before_player_weak(card, game)
        hit_count = cls._survival_attack_hit_count(card)
        return cls._apply_player_weak_to_survival_attack_damage(
            damage,
            game,
            hit_count=hit_count,
        )

    @classmethod
    def _survival_attack_hit_count(cls, card) -> int:
        hit_count = fixed_attack_hit_count(card)
        if hit_count is None:
            return 1
        return max(1, cls._safe_int(hit_count, default=1))

    @classmethod
    def _survival_attack_damage_before_player_weak(cls, card, game: Optional[Game] = None) -> int:
        explicit_damage = max(
            0,
            cls._safe_int(getattr(card, "damage", 0), default=0),
        )
        if explicit_damage > 0:
            return explicit_damage

        if game is not None and cls._card_matches_normalized_names(card, {"mindblast"}):
            return draw_pile_count(game) + player_power_amount(game, "Strength")

        for normalized_name, (card_name, base_damage) in cls.SURVIVAL_ATTACK_DAMAGE_VALUES.items():
            if cls._card_matches_normalized_names(card, {normalized_name}):
                damage = base_damage + known_damage_upgrade_bonus(card, card_name)
                if game is not None:
                    if card_name == "Perfected Strike":
                        damage += (
                            strike_card_count(game)
                            * perfected_strike_bonus_per_strike(card)
                        )
                    damage += player_power_amount(game, "Strength")
                return max(0, damage)
        return 0

    @classmethod
    def _apply_survival_attack_target_modifiers(
        cls,
        damage: int,
        game: Game,
        monster,
        hit_count: int = 1,
    ) -> int:
        damage = max(0, cls._safe_int(damage, default=0))
        hit_count = max(1, cls._safe_int(hit_count, default=1))
        if damage <= 0:
            return 0
        player_weak = player_debuff_stacks(game, "Weak") > 0
        target_vulnerable = cls._monster_vulnerable_stacks(monster) > 0
        if player_weak and target_vulnerable:
            numerator, denominator = (
                (21, 16)
                if cls._has_relic(game, "paperphrog")
                else (9, 8)
            )
            return (damage * numerator // denominator) * hit_count
        if player_weak:
            return (damage * 3 // 4) * hit_count
        if target_vulnerable:
            numerator, denominator = (
                (7, 4)
                if cls._has_relic(game, "paperphrog")
                else (3, 2)
            )
            return (damage * numerator // denominator) * hit_count
        return damage * hit_count

    @classmethod
    def _apply_player_weak_to_survival_attack_damage(
        cls,
        damage: int,
        game: Optional[Game],
        hit_count: int = 1,
    ) -> int:
        damage = max(0, cls._safe_int(damage, default=0))
        hit_count = max(1, cls._safe_int(hit_count, default=1))
        if game is None or player_debuff_stacks(game, "Weak") <= 0:
            return damage * hit_count
        return (damage * 3 // 4) * hit_count

    @classmethod
    def _has_relic(cls, game: Game, normalized_relic_name: str) -> bool:
        target = cls._normalize_identifier(normalized_relic_name)
        for relic in getattr(game, "relics", []) or []:
            for attr in ("name", "relic_id", "id"):
                if cls._normalize_identifier(getattr(relic, attr, None)) == target:
                    return True
        return False

    @classmethod
    def _has_awakened_one(cls, game: Game) -> bool:
        for monster in cls._alive_monsters(game):
            identifiers = [
                getattr(monster, "monster_id", ""),
                getattr(monster, "name", ""),
            ]
            for identifier in identifiers:
                normalized = "".join(
                    ch for ch in str(identifier).lower() if ch.isalnum()
                )
                if "awakenedone" in normalized:
                    return True
        return False

    @classmethod
    def _has_hexaghost(cls, game: Game) -> bool:
        for monster in cls._alive_monsters(game):
            for identifier in (
                getattr(monster, "monster_id", ""),
                getattr(monster, "name", ""),
            ):
                if "hexaghost" in cls._normalize_identifier(identifier):
                    return True
        return False

    @classmethod
    def _has_slime_boss(cls, game: Game) -> bool:
        for monster in cls._alive_monsters(game):
            for identifier in (
                getattr(monster, "monster_id", ""),
                getattr(monster, "name", ""),
            ):
                if "slimeboss" in cls._normalize_identifier(identifier):
                    return True
        return False

    @classmethod
    def _monster_vulnerable_stacks(cls, monster) -> int:
        for power in getattr(monster, "powers", []) or []:
            identifiers = (
                getattr(power, "power_id", None),
                getattr(power, "power_name", None),
                getattr(power, "name", None),
            )
            if not any("vulnerable" in cls._normalize_identifier(value) for value in identifiers):
                continue
            return cls._safe_int(getattr(power, "amount", 0), default=0)
        return 0

    @classmethod
    def _monster_weak_stacks(cls, monster) -> int:
        for power in getattr(monster, "powers", []) or []:
            identifiers = (
                getattr(power, "power_id", None),
                getattr(power, "power_name", None),
                getattr(power, "name", None),
            )
            if not any("weak" in cls._normalize_identifier(value) for value in identifiers):
                continue
            return cls._safe_int(getattr(power, "amount", 0), default=0)
        return 0

    @classmethod
    def _incoming_damage_after_single_target_weak(cls, game: Game) -> Optional[int]:
        attackers = [
            monster
            for monster in cls._alive_monsters(game)
            if cls._monster_incoming_damage(monster) > 0
        ]
        if len(attackers) != 1:
            return None

        monster = attackers[0]
        if cls._monster_weak_stacks(monster) > 0:
            return None
        if intent_is_unknown(getattr(monster, "intent", None)):
            known_damage = known_unknown_move_immediate_damage(monster)
            if known_damage <= 0:
                return None
            return max(0, cls._safe_int(known_damage, default=0) * 3 // 4)
        if not monster_intends_attack(monster):
            return None

        damage = getattr(monster, "move_adjusted_damage", None)
        if damage is None:
            damage = getattr(monster, "move_base_damage", 0) or 0
        hits = max(1, cls._safe_int(getattr(monster, "move_hits", 1), default=1))
        return max(0, cls._safe_int(damage, default=0) * 3 // 4) * hits

    @classmethod
    def _incoming_damage_events_after_aoe_weak(cls, game: Game) -> Optional[list[int]]:
        events = []
        changed = False
        for monster in cls._alive_monsters(game):
            if intent_is_unknown(getattr(monster, "intent", None)):
                known_damage = known_unknown_move_immediate_damage(monster)
                if known_damage > 0:
                    damage = max(0, cls._safe_int(known_damage, default=0))
                    if cls._monster_weak_stacks(monster) <= 0:
                        damage = damage * 3 // 4
                        changed = True
                    if damage > 0:
                        events.append(damage)
                    continue
                if known_unknown_move_has_no_immediate_damage(monster):
                    continue
                damage = max(
                    0,
                    5 * cls._safe_int(getattr(game, "act", 1), default=1),
                )
                if cls._monster_weak_stacks(monster) <= 0:
                    damage = damage * 3 // 4
                    changed = True
                if damage > 0:
                    events.append(damage)
                continue

            if not monster_intends_attack(monster):
                continue
            damage = getattr(monster, "move_adjusted_damage", None)
            if damage is None:
                damage = getattr(monster, "move_base_damage", 0) or 0
            damage = max(0, cls._safe_int(damage, default=0))
            if cls._monster_weak_stacks(monster) <= 0:
                damage = damage * 3 // 4
                changed = True
            hits = max(1, cls._safe_int(getattr(monster, "move_hits", 1), default=1))
            events.extend([damage] * hits)

        if not changed:
            return None
        return [event for event in events if event > 0]

    @staticmethod
    def _player_energy(game: Game) -> int:
        player = getattr(game, "player", None)
        energy = getattr(player, "energy", None)
        if energy is None:
            energy = getattr(game, "energy", 0)
        return CombatRLAgent._safe_int(energy, default=0)

    @staticmethod
    def _playable_cards(game: Game, energy: int):
        playable = []
        for index, card in enumerate(getattr(game, "hand", []) or []):
            if hasattr(card, "is_playable") and not getattr(card, "is_playable", False):
                continue
            effective_cost = effective_card_cost(card, energy)
            if effective_cost > energy:
                continue
            playable.append((index, card))
        return playable

    @staticmethod
    def _best_monster_index(game: Game) -> Optional[int]:
        monsters = getattr(game, "monsters", []) or []
        candidates = [
            (index, monster)
            for index, monster in enumerate(monsters)
            if (
                CombatRLAgent._safe_int(
                    getattr(monster, "current_hp", 0),
                    default=0,
                )
                > 0
                and not getattr(monster, "is_gone", False)
                and not getattr(monster, "half_dead", False)
            )
        ]
        if not candidates:
            return None
        return max(
            candidates,
            key=lambda item: CombatRLAgent._safe_int(
                getattr(item[1], "current_hp", 0),
                default=0,
            ),
        )[0]

    @staticmethod
    def _potion_target_index(
        potion,
        alive_monsters,
        game: Optional[Game] = None,
    ) -> Optional[int]:
        if not alive_monsters:
            return None
        if str(getattr(potion, "effect_type", "") or "") in ("damage", "debuff_weak", "debuff_vulnerable"):
            target = max(
                alive_monsters,
                key=lambda monster: CombatRLAgent._safe_int(
                    getattr(monster, "current_hp", 0),
                    default=0,
                ),
            )
        else:
            target = min(
                alive_monsters,
                key=lambda monster: CombatRLAgent._safe_int(
                    getattr(monster, "current_hp", 0),
                    default=0,
                ),
            )
        target_index = getattr(target, "monster_index", None)
        if target_index is not None:
            return target_index
        if game is not None:
            for index, monster in enumerate(getattr(game, "monsters", []) or []):
                if monster is target:
                    return index
        try:
            return alive_monsters.index(target)
        except ValueError:
            return None

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
        Detect if we're in the main combat action loop.

        Uses game.in_combat together with the screen type to gate combat RL.
        Selection popups such as GRID and HAND_SELECT need deterministic
        screen handlers even when they appear during combat.
        """
        from spirecomm.spire.screen import ScreenType

        if not getattr(game, "in_combat", False):
            return False

        screen_type = getattr(game, "screen_type", None)
        return screen_type in (
            None,
            ScreenType.NONE,
        )

    def _is_rl_context(self, game: Game) -> bool:
        """
        Use RL only for live main-combat decisions.
        """
        in_combat = self._is_in_combat_context(game)
        screen_type = getattr(game, 'screen_type', None)

        logger.info(f"[RL_CONTEXT] in_combat={in_combat}, screen_type={screen_type}")

        if in_combat:
            logger.info(f"[RL_CONTEXT] Returning True (in combat)")
            return True

        logger.info("[RL_CONTEXT] Returning False (non-combat screen)")
        return False

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
            if isinstance(action, PlayCardAction):
                return self._is_current_combat_action_playable(action, game)
            return isinstance(action, (PotionAction, EndTurnAction))

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

    def _is_current_combat_action_playable(self, action: Action, game: Game) -> bool:
        from spirecomm.communication.action import PlayCardAction
        from spirecomm.spire.screen import ScreenType

        if not isinstance(action, PlayCardAction):
            return True
        if getattr(game, "screen_type", None) not in (None, ScreenType.NONE):
            return False
        if not getattr(game, "play_available", False):
            return False

        card = self._card_for_action(action, game)
        if card is None:
            return False
        if hasattr(card, "is_playable") and not getattr(card, "is_playable", False):
            return False
        if not card_play_conditions_allow(card, game):
            return False

        energy = self._player_energy(game)
        if effective_card_cost(card, energy) > energy:
            return False

        target_index = getattr(action, "target_index", None)
        if card_requires_target(card):
            if target_index is None:
                return False
            try:
                target_index = int(target_index)
            except (TypeError, ValueError):
                return False
            monsters = getattr(game, "monsters", []) or []
            if target_index < 0 or target_index >= len(monsters):
                return False
            target = monsters[target_index]
            if (
                self._safe_int(getattr(target, "current_hp", 0), default=0) <= 0
                or getattr(target, "is_gone", False)
                or getattr(target, "half_dead", False)
            ):
                return False
        elif target_index is not None:
            return False

        return True

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
        self._fallback_turn_key = None
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
