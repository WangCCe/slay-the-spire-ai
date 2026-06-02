"""
RL v2 agent implementation with embedding-based observations.
"""

from dataclasses import dataclass
import logging
import os
from typing import Optional

import numpy as np
import torch

from spirecomm.communication.action import EndTurnAction, StartGameAction, StateAction
from spirecomm.spire.character import PlayerClass
from spirecomm.spire.game import Game
from spirecomm.spire.numeric import coerce_int

from spirecomm.ai.heuristics.card_types import card_type_name
from spirecomm.ai.rl.reward import RewardCalculator
from spirecomm.ai.rl.checkpoint_io import load_torch_checkpoint

from .action_encoder import ActionEncoderV2
from .action_space import ACTION_DIM, PLAY_CARD_COUNT
from .id_mapping import IdMapper, load_default_id_mapper
from .network import create_dqn_v2
from .state_encoder import StateEncoderV2
from .trainer import DQNTrainerV2

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CheckpointMetadata:
    rl_space_version: str
    network_type: str
    continuous_dim: int
    action_dim: int
    card_vocab: int
    potion_vocab: int
    relic_vocab: int
    card_slots: int
    potion_slots: int
    relic_slots: int

    def as_dict(self) -> dict:
        return {
            "rl_space_version": self.rl_space_version,
            "network_type": self.network_type,
            "continuous_dim": self.continuous_dim,
            "action_dim": self.action_dim,
            "card_vocab": self.card_vocab,
            "potion_vocab": self.potion_vocab,
            "relic_vocab": self.relic_vocab,
            "card_slots": self.card_slots,
            "potion_slots": self.potion_slots,
            "relic_slots": self.relic_slots,
        }


@dataclass
class PendingTransition:
    continuous: np.ndarray
    card_ids: np.ndarray
    potion_ids: np.ndarray
    relic_ids: np.ndarray
    action_index: int
    action_mask: np.ndarray
    game: Game


class RLAgentV2:
    """
    Reinforcement Learning agent using RL v2 action/observation spaces.
    """

    RL_SPACE_VERSION = "v2"

    def __init__(
        self,
        model_path: Optional[str] = None,
        training: bool = False,
        device: str = "cuda" if torch.cuda.is_available() else "cpu",
        epsilon: float = 0.0,
        id_mapper: Optional[IdMapper] = None,
        network_type: str = "dueling",
        expert_mix_enabled: Optional[bool] = None,
        expert_mix_prob: Optional[float] = None,
        expert_warmup_steps: Optional[int] = None,
    ):
        self.device = device
        self.training_mode = training
        self.training = training
        self.epsilon = epsilon
        self.network_type = network_type
        self.chosen_class = PlayerClass.IRONCLAD

        self.id_mapper = id_mapper or load_default_id_mapper()
        self.state_encoder = StateEncoderV2(self.id_mapper)
        self.action_encoder = ActionEncoderV2()
        self.reward_calculator = RewardCalculator()

        self.trainer = None
        self.network = None
        logger.info(
            "RLAgentV2 init: file=%s training=%s device=%s",
            __file__,
            training,
            device,
        )

        if training:
            self.trainer = DQNTrainerV2(
                continuous_dim=self.state_encoder.feature_dim,
                action_dim=self.action_encoder.MAX_ACTIONS,
                card_slots=self.state_encoder.CARD_SLOTS,
                potion_slots=self.state_encoder.POTION_SLOTS,
                relic_slots=self.state_encoder.RELIC_SLOTS,
                card_vocab=self.id_mapper.card_vocab_size,
                potion_vocab=self.id_mapper.potion_vocab_size,
                relic_vocab=self.id_mapper.relic_vocab_size,
                device=device,
                network_type=self.network_type,
            )
            self.network = self.trainer.online_network
        else:
            self.network = create_dqn_v2(
                network_type=self.network_type,
                continuous_dim=self.state_encoder.feature_dim,
                action_dim=self.action_encoder.MAX_ACTIONS,
                card_vocab=self.id_mapper.card_vocab_size,
                potion_vocab=self.id_mapper.potion_vocab_size,
                relic_vocab=self.id_mapper.relic_vocab_size,
                device=device,
                card_slots=self.state_encoder.CARD_SLOTS,
                potion_slots=self.state_encoder.POTION_SLOTS,
                relic_slots=self.state_encoder.RELIC_SLOTS,
            )
            self.network.eval()

        self.boss_min_epsilon = 0.3
        self.last_game: Optional[Game] = None
        self.pending_transition: Optional[PendingTransition] = None

        self.episode_reward = 0.0
        self.episode_steps = 0

        if expert_mix_enabled is None:
            expert_mix_enabled = os.environ.get("STS_RL_EXPERT_MIX", "0") != "0"
        if expert_mix_prob is None:
            expert_mix_prob = float(os.environ.get("STS_RL_EXPERT_MIX_PROB", "0.3"))
        if expert_warmup_steps is None:
            expert_warmup_steps = int(os.environ.get("STS_RL_EXPERT_WARMUP_STEPS", "5000"))
        self.expert_mix_enabled = bool(expert_mix_enabled)
        self.expert_mix_prob = float(expert_mix_prob)
        self.expert_warmup_steps = int(expert_warmup_steps)
        self.expert_agent = None
        logger.info(
            "RLAgentV2 expert mix config: enabled=%s prob=%.2f warmup_steps=%s",
            self.expert_mix_enabled,
            self.expert_mix_prob,
            self.expert_warmup_steps,
        )
        if self.training_mode and self.expert_mix_enabled:
            try:
                from spirecomm.ai.agent import OptimizedAgent, SimpleAgent, OPTIMIZED_AI_AVAILABLE

                if OPTIMIZED_AI_AVAILABLE:
                    self.expert_agent = OptimizedAgent(chosen_class=self.chosen_class)
                else:
                    self.expert_agent = SimpleAgent(chosen_class=self.chosen_class)
                logger.info(
                    "Expert mix enabled (warmup_steps=%s, prob=%.2f, expert=%s)",
                    self.expert_warmup_steps,
                    self.expert_mix_prob,
                    type(self.expert_agent).__name__,
                )
            except Exception as exc:
                logger.warning("Expert mix init failed: %s", exc)

        if model_path:
            self.load_model(model_path)

    def get_next_action_in_game(self, game: Game):
        try:
            encoded = self.state_encoder.encode(game)
            action_mask = np.array(
                self.action_encoder.get_action_mask(game), dtype=bool
            )

            if not action_mask.any():
                logger.warning("No valid actions in mask; returning StateAction.")
                return StateAction()

            expert_index = self._maybe_get_expert_action_index(game, action_mask)
            if expert_index is not None:
                action_index = expert_index
            elif self.training_mode and self.trainer is not None:
                action_index = self.trainer.select_action(
                    continuous=encoded.continuous,
                    card_ids=encoded.card_ids,
                    potion_ids=encoded.potion_ids,
                    relic_ids=encoded.relic_ids,
                    action_mask=action_mask,
                    training=True,
                    epsilon_override=self._get_training_epsilon(game),
                )
            else:
                if np.random.random() < self.epsilon:
                    valid_actions = np.where(action_mask)[0]
                    action_index = int(
                        np.random.choice(valid_actions)
                        if len(valid_actions) > 0
                        else 0
                    )
                else:
                    continuous_tensor = (
                        torch.from_numpy(encoded.continuous)
                        .float()
                        .unsqueeze(0)
                        .to(self.device)
                    )
                    card_tensor = (
                        torch.from_numpy(encoded.card_ids)
                        .long()
                        .unsqueeze(0)
                        .to(self.device)
                    )
                    potion_tensor = (
                        torch.from_numpy(encoded.potion_ids)
                        .long()
                        .unsqueeze(0)
                        .to(self.device)
                    )
                    relic_tensor = (
                        torch.from_numpy(encoded.relic_ids)
                        .long()
                        .unsqueeze(0)
                        .to(self.device)
                    )
                    mask_tensor = (
                        torch.from_numpy(action_mask)
                        .unsqueeze(0)
                        .to(self.device)
                    )
                    with torch.no_grad():
                        action_index = int(
                            self.network.get_best_action(
                                continuous=continuous_tensor,
                                card_ids=card_tensor,
                                potion_ids=potion_tensor,
                                relic_ids=relic_tensor,
                                action_mask=mask_tensor,
                            ).item()
                        )

            action = self.action_encoder.decode_action(action_index, game)

            if self.training_mode and self.trainer is not None:
                self._process_training_step(
                    game=game,
                    encoded=encoded,
                    action_index=action_index,
                    action_mask=action_mask,
                )

            self.last_game = game
            return action

        except Exception as exc:
            logger.error("RLAgentV2 failed to select action: %s", exc)
            return EndTurnAction()

    def _process_training_step(
        self,
        game: Game,
        encoded,
        action_index: int,
        action_mask: np.ndarray,
    ) -> None:
        if self.pending_transition is not None:
            reward_info = {}
            action_context = self._build_action_context(self.pending_transition)
            reward = self.reward_calculator.calculate_step_reward(
                current_game=game,
                last_game=self.pending_transition.game,
                action_type="combat",
                debug_info=reward_info,
                action_context=action_context,
            )
            done = self._is_terminal(game)

            self.trainer.store_transition(
                continuous=self.pending_transition.continuous,
                card_ids=self.pending_transition.card_ids,
                potion_ids=self.pending_transition.potion_ids,
                relic_ids=self.pending_transition.relic_ids,
                action=self.pending_transition.action_index,
                reward=reward,
                next_continuous=encoded.continuous,
                next_card_ids=encoded.card_ids,
                next_potion_ids=encoded.potion_ids,
                next_relic_ids=encoded.relic_ids,
                done=done,
                action_mask=self.pending_transition.action_mask,
                next_action_mask=action_mask,
            )

            loss = self.trainer.train_step()
            if loss is not None:
                self.episode_reward += reward
                self.episode_steps += 1

        self.pending_transition = PendingTransition(
            continuous=encoded.continuous,
            card_ids=encoded.card_ids,
            potion_ids=encoded.potion_ids,
            relic_ids=encoded.relic_ids,
            action_index=action_index,
            action_mask=action_mask,
            game=game,
        )

    def _maybe_get_expert_action_index(self, game: Game, action_mask: np.ndarray) -> Optional[int]:
        if not self.training_mode or self.expert_agent is None or self.trainer is None:
            return None

        total_steps = self.trainer.total_steps
        if total_steps < self.expert_warmup_steps:
            use_expert = True
        else:
            use_expert = np.random.random() < self.expert_mix_prob
        if not use_expert:
            logger.info(
                "Expert mix skipped: total_steps=%s warmup_steps=%s prob=%.2f",
                total_steps,
                self.expert_warmup_steps,
                self.expert_mix_prob,
            )
            return None

        try:
            expert_action = self.expert_agent.get_next_action_in_game(game)
        except Exception as exc:
            logger.info("Expert action failed: %s", exc)
            return None

        expert_index = self.action_encoder.encode_action(expert_action, game)
        if expert_index is None:
            logger.info(
                "Expert action not encodable: %s",
                type(expert_action).__name__ if expert_action is not None else "None",
            )
            return None
        if expert_index >= len(action_mask) or not action_mask[expert_index]:
            logger.info(
                "Expert action masked out: index=%s action=%s",
                expert_index,
                type(expert_action).__name__ if expert_action is not None else "None",
            )
            return None

        logger.info("Expert action selected: index=%s action=%s", expert_index, type(expert_action).__name__ if expert_action is not None else "None")
        return expert_index

    def _build_action_context(self, pending: PendingTransition) -> dict:
        action_context = {"action_name": "Unknown", "had_play_options": False, "played_card_type": None}
        try:
            action_obj = self.action_encoder.decode_action(
                pending.action_index, pending.game
            )
            action_context["action_name"] = type(action_obj).__name__
        except Exception:
            return action_context

        if pending.action_mask is not None:
            try:
                action_context["had_play_options"] = bool(
                    pending.action_mask[:PLAY_CARD_COUNT].any()
                )
            except Exception:
                action_context["had_play_options"] = False

        if action_context["action_name"] == "PlayCardAction":
            try:
                card_index = getattr(action_obj, "card_index", None)
                if card_index is None and hasattr(action_obj, "card"):
                    card_index = getattr(action_obj.card, "card_index", None)
                hand = getattr(pending.game, "hand", []) or []
                if card_index is not None and 0 <= int(card_index) < len(hand):
                    card = hand[int(card_index)]
                    action_context["played_card_type"] = card_type_name(card) or None
            except Exception:
                action_context["played_card_type"] = None

        return action_context

    def _get_training_epsilon(self, game: Game) -> float:
        base_epsilon = self.trainer.epsilon if self.trainer is not None else 0.0
        room_type = str(getattr(game, "room_type", "") or "").lower()
        if "boss" in room_type:
            return min(1.0, max(base_epsilon, self.boss_min_epsilon))
        return base_epsilon

    @staticmethod
    def _is_terminal(game: Game) -> bool:
        if "GAME_OVER" in str(getattr(game, "screen_type", "")):
            return True
        player = getattr(game, "player", None)
        current_hp = RLAgentV2._safe_int(
            getattr(player, "current_hp", 1) if player is not None else 1,
            default=1,
        )
        if player is not None and current_hp <= 0:
            return True
        return False

    @staticmethod
    def _safe_int(value, default: int = 0) -> int:
        return coerce_int(value, default)

    def reset(self) -> None:
        self.last_game = None
        self.pending_transition = None
        self.episode_reward = 0.0
        self.episode_steps = 0
        self.reward_calculator.reset()
        if self.trainer is not None:
            self.trainer.update_episode_count()
        if self.expert_agent is not None and hasattr(self.expert_agent, "game_tracker"):
            try:
                from spirecomm.ai.tracker import GameTracker

                self.expert_agent.game_tracker = GameTracker()
            except Exception:
                pass

    def get_next_action_out_of_game(self):
        return StartGameAction(self.chosen_class)

    def handle_error(self, error):
        logger.error("RLAgentV2 error: %s", error)
        return StateAction()

    def load_model(self, model_path: str) -> None:
        checkpoint = load_torch_checkpoint(model_path, map_location=self.device)
        metadata = self._extract_checkpoint_metadata(checkpoint)
        self._validate_checkpoint(metadata, model_path)

        state_dict = checkpoint.get("online_network_state_dict") or checkpoint.get("state_dict")
        if state_dict is None:
            raise ValueError(f"Checkpoint missing state dict: {model_path}")

        if self.training_mode and self.trainer is not None:
            self.trainer.online_network.load_state_dict(state_dict)
            self.trainer.target_network.load_state_dict(state_dict)
            optimizer_state = checkpoint.get("optimizer_state_dict")
            if optimizer_state is not None:
                self.trainer.optimizer.load_state_dict(optimizer_state)
            self.trainer.epsilon = checkpoint.get("epsilon", self.trainer.epsilon)
            self.trainer.total_steps = checkpoint.get("total_steps", self.trainer.total_steps)
            logger.info("Loaded v2 trainer checkpoint from %s", model_path)
        else:
            self.network.load_state_dict(state_dict)
            self.network.eval()
            logger.info("Loaded v2 model weights from %s", model_path)

    def save_model(self, model_path: str, episode: int = 0) -> None:
        metadata = self._build_metadata()
        checkpoint = {
            "metadata": metadata.as_dict(),
            "rl_space_version": metadata.rl_space_version,
            "online_network_state_dict": self.network.state_dict(),
            "episode": episode,
        }

        if self.training_mode and self.trainer is not None:
            checkpoint.update(
                {
                    "optimizer_state_dict": self.trainer.optimizer.state_dict(),
                    "epsilon": self.trainer.epsilon,
                    "total_steps": self.trainer.total_steps,
                }
            )

        torch.save(checkpoint, model_path)
        logger.info("Saved v2 checkpoint to %s", model_path)

    def _build_metadata(self) -> CheckpointMetadata:
        return CheckpointMetadata(
            rl_space_version=self.RL_SPACE_VERSION,
            network_type=self.network_type,
            continuous_dim=self.state_encoder.feature_dim,
            action_dim=self.action_encoder.MAX_ACTIONS,
            card_vocab=self.id_mapper.card_vocab_size,
            potion_vocab=self.id_mapper.potion_vocab_size,
            relic_vocab=self.id_mapper.relic_vocab_size,
            card_slots=self.state_encoder.CARD_SLOTS,
            potion_slots=self.state_encoder.POTION_SLOTS,
            relic_slots=self.state_encoder.RELIC_SLOTS,
        )

    @staticmethod
    def _extract_checkpoint_metadata(checkpoint: dict) -> CheckpointMetadata:
        metadata = checkpoint.get("metadata") if isinstance(checkpoint, dict) else None
        if metadata is None:
            metadata = checkpoint
        return CheckpointMetadata(
            rl_space_version=metadata.get("rl_space_version"),
            network_type=metadata.get("network_type"),
            continuous_dim=metadata.get("continuous_dim"),
            action_dim=metadata.get("action_dim"),
            card_vocab=metadata.get("card_vocab"),
            potion_vocab=metadata.get("potion_vocab"),
            relic_vocab=metadata.get("relic_vocab"),
            card_slots=metadata.get("card_slots"),
            potion_slots=metadata.get("potion_slots"),
            relic_slots=metadata.get("relic_slots"),
        )

    def _validate_checkpoint(self, metadata: CheckpointMetadata, path: str) -> None:
        expected = self._build_metadata()
        if metadata.rl_space_version != expected.rl_space_version:
            raise ValueError(
                f"Checkpoint version mismatch: expected {expected.rl_space_version}, "
                f"got {metadata.rl_space_version} ({path})"
            )

        mismatches = []
        for field in ("network_type", "continuous_dim", "action_dim", "card_vocab", "potion_vocab", "relic_vocab", "card_slots", "potion_slots", "relic_slots"):
            expected_value = getattr(expected, field)
            actual_value = getattr(metadata, field)
            if actual_value != expected_value:
                mismatches.append(f"{field} expected {expected_value}, got {actual_value}")

        if mismatches:
            mismatch_msg = "; ".join(mismatches)
            raise ValueError(f"Checkpoint metadata mismatch ({path}): {mismatch_msg}")


def create_agent_v2(
    model_path: Optional[str] = None,
    training: bool = False,
    device: str = "cuda" if torch.cuda.is_available() else "cpu",
    epsilon: float = 0.0,
    id_mapper: Optional[IdMapper] = None,
    expert_mix_enabled: Optional[bool] = None,
    expert_mix_prob: Optional[float] = None,
    expert_warmup_steps: Optional[int] = None,
) -> RLAgentV2:
    return RLAgentV2(
        model_path=model_path,
        training=training,
        device=device,
        epsilon=epsilon,
        id_mapper=id_mapper,
        expert_mix_enabled=expert_mix_enabled,
        expert_mix_prob=expert_mix_prob,
        expert_warmup_steps=expert_warmup_steps,
    )
